"""
OCR Extraction Service Module
==============================
Step 2 in the AI Document Processing Pipeline.

This service handles:
- Text extraction using Azure Computer Vision OCR
- Quality-based OCR optimization
- Retry logic with exponential backoff
- Anti-hallucination filtering
- Page organization of OCR results

This module contains the complete OCR logic (previously in file_utils.py).
"""

import os
import re
import time
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from collections import defaultdict

# Azure Computer Vision imports
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
from msrest.authentication import CognitiveServicesCredentials

# App configuration
from app.utils.app_config import (
    COMPUTER_VISION_ENDPOINT, 
    COMPUTER_VISION_KEY,
    OCR_MAX_RETRIES, 
    OCR_RETRY_DELAY_BASE,
    OCR_POLLING_INTERVAL, 
    OCR_TIMEOUT_BASE,
    OCR_TIMEOUT_PER_PAGE, 
    OCR_FAST_MODE,
    OCR_ADAPTIVE_POLLING
)

logger = logging.getLogger(__name__)

# Supported file types for OCR
SUPPORTED_FILE_TYPES = ["application/pdf", "image/jpeg", "image/png"]

# Anti-hallucination settings
MIN_CONFIDENCE_THRESHOLD = 0.5  # Filter out low-confidence text
MIN_WORD_LENGTH = 1  # Filter out single characters that are often noise
SUSPICIOUS_PATTERNS = [
    r'^[^a-zA-Z0-9\s]+$', 
    r'^\s*$', 
    r'^[.,;:!?\-_=+(){}\[\]"\'`~@#$%^&*/<>\\|]*$'
]


@dataclass
class OCRExtractionResult:
    """Data class representing the result of OCR extraction."""
    success: bool
    text_data: List[Dict[str, Any]]
    word_data: List[Dict[str, Any]]
    pages_ocr_data: List[List[Dict[str, Any]]]
    page_count: int
    processing_time: float
    overall_confidence: float
    optimization_stats: Dict[str, Any] = field(default_factory=dict)
    anti_hallucination_stats: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


class OCRExtractionService:
    """
    Service class for Step 2: OCR Extraction.
    
    Handles text extraction from documents using Azure Computer Vision OCR
    with quality-based optimization and retry logic.
    
    This class contains the complete OCR implementation (previously in file_utils.py).
    """
    
    def __init__(self):
        """Initialize the OCR Extraction Service with Azure CV client."""
        logger.info("OCRExtractionService initialized")
        
        # Initialize Azure Computer Vision client
        self._cv_client = ComputerVisionClient(
            COMPUTER_VISION_ENDPOINT,
            CognitiveServicesCredentials(COMPUTER_VISION_KEY)
        )
    
    def extract(
        self,
        temp_file_path: str,
        file_type: str,
        quality_verdict: str = "pre_processing",
        estimated_pages: int = 1,
        progress_tracker=None,
        max_retries: Optional[int] = None
    ) -> OCRExtractionResult:
        """
        Extract text from document using Azure Computer Vision OCR.
        
        This is the main entry point for Step 2 of the document processing pipeline.
        
        Args:
            temp_file_path: Path to the temporary file to process
            file_type: MIME type of the file (application/pdf, image/jpeg, image/png)
            quality_verdict: Quality analysis verdict from Step 1
            estimated_pages: Estimated number of pages for timeout calculation
            progress_tracker: Optional progress tracking object
            max_retries: Optional override for max retry attempts
            
        Returns:
            OCRExtractionResult containing extracted text data and metadata
        """
        logger.info(f"🔍 STEP 2: OCR Extraction Service started")
        logger.info(f"📄 File: {temp_file_path}, Type: {file_type}")
        logger.info(f"🔧 Quality Verdict: {quality_verdict}, Estimated Pages: {estimated_pages}")
        
        start_time = time.time()
        
        # Start OCR progress tracking
        if progress_tracker:
            progress_tracker.start_ocr()
        
        try:
            # Perform OCR extraction with retry logic
            extracted_result = self._extract_with_retry(
                temp_file_path=temp_file_path,
                file_type=file_type,
                quality_verdict=quality_verdict,
                page_count=estimated_pages,
                max_retries=max_retries
            )
            
            processing_time = time.time() - start_time
            
            # Check for OCR errors
            if "error" in extracted_result:
                logger.error(f"❌ OCR extraction failed: {extracted_result['error']}")
                return OCRExtractionResult(
                    success=False,
                    text_data=[],
                    word_data=[],
                    pages_ocr_data=[],
                    page_count=0,
                    processing_time=processing_time,
                    overall_confidence=0.0,
                    error=extracted_result["error"]
                )
            
            text_data = extracted_result.get("text_data", [])
            word_data = extracted_result.get("word_data", [])
            
            # Check if we got any text
            if not text_data:
                logger.warning("⚠️ OCR returned no text data")
                return OCRExtractionResult(
                    success=False,
                    text_data=[],
                    word_data=[],
                    pages_ocr_data=[],
                    page_count=0,
                    processing_time=processing_time,
                    overall_confidence=0.0,
                    error="No text extracted from document"
                )
            
            # Organize OCR data by pages
            pages_ocr_data = self._organize_by_page(text_data)
            
            # Extract stats
            optimization_stats = extracted_result.get("optimization_stats", {})
            anti_hallucination_stats = extracted_result.get("anti_hallucination_stats", {})
            overall_confidence = extracted_result.get("overall_confidence", 0.0)
            
            # Log success
            if optimization_stats:
                logger.info(
                    f"✅ OCR completed in {processing_time:.2f}s - {len(text_data)} entries | "
                    f"FastMode: {optimization_stats.get('fast_mode', False)}, "
                    f"Polls: {optimization_stats.get('poll_count', 'N/A')}"
                )
            else:
                logger.info(f"✅ OCR completed in {processing_time:.2f}s - {len(text_data)} entries")
            
            logger.info(f"📄 Organized into {len(pages_ocr_data)} pages")
            
            # Log extracted OCR text for each page
            self._log_extracted_text(pages_ocr_data)
            
            # Update progress tracker
            if progress_tracker:
                progress_tracker.ocr_complete(extracted_entries=len(text_data))
            
            return OCRExtractionResult(
                success=True,
                text_data=text_data,
                word_data=word_data,
                pages_ocr_data=pages_ocr_data,
                page_count=len(pages_ocr_data),
                processing_time=processing_time,
                overall_confidence=overall_confidence,
                optimization_stats=optimization_stats,
                anti_hallucination_stats=anti_hallucination_stats
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"❌ OCR extraction exception: {str(e)}")
            return OCRExtractionResult(
                success=False,
                text_data=[],
                word_data=[],
                pages_ocr_data=[],
                page_count=0,
                processing_time=processing_time,
                overall_confidence=0.0,
                error=str(e)
            )
    
    def _log_extracted_text(self, pages_ocr_data: List[List[Dict[str, Any]]]) -> None:
        """
        Log the extracted OCR text for each page.
        
        Args:
            pages_ocr_data: Organized OCR data by pages
        """
        logger.info("=" * 80)
        logger.info("📝 EXTRACTED OCR TEXT (Page by Page)")
        logger.info("=" * 80)
        
        for page_idx, page_data in enumerate(pages_ocr_data):
            page_num = page_idx + 1
            page_text = "\n".join([entry.get('text', '') for entry in page_data])
            
            logger.info(f"\n{'─' * 40}")
            logger.info(f"📄 PAGE {page_num} ({len(page_data)} lines)")
            logger.info(f"{'─' * 40}")
            
            # Log the full text for this page
            if page_text:
                # Split into lines and log each
                lines = page_text.split('\n')
                for line in lines:
                    if line.strip():
                        logger.info(f"   {line}")
            else:
                logger.info("   [No text extracted for this page]")
        
        logger.info("=" * 80)
        logger.info("📝 END OF EXTRACTED OCR TEXT")
        logger.info("=" * 80)
    
    def _extract_with_retry(
        self,
        temp_file_path: str,
        file_type: str,
        quality_verdict: str,
        page_count: int,
        max_retries: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Extract text with exponential backoff retry logic.
        
        Args:
            temp_file_path: Path to the temporary file
            file_type: MIME type of the file
            quality_verdict: Quality analysis verdict for optimization
            page_count: Number of pages for timeout calculation
            max_retries: Override for max retries
            
        Returns:
            dict: OCR result with text_data or error information
        """
        # Use config value if max_retries not specified
        if max_retries is None:
            max_retries = OCR_MAX_RETRIES
        
        # Quality-based retry optimization
        if quality_verdict == "direct_analysis":
            max_retries = max(1, max_retries - 1)  # Reduce retries for high-quality docs
        
        logger.info(f"SPEED: OPTIMIZED OCR retry: max_retries={max_retries}, quality={quality_verdict}, pages={page_count}")
        
        for attempt in range(max_retries):
            try:
                logger.debug(f"MODE: OCR attempt {attempt + 1}/{max_retries} for file: {temp_file_path}")
                
                # Call the actual OCR extraction
                result = self._extract_text_optimized(
                    temp_file_path, 
                    file_type, 
                    quality_verdict, 
                    page_count
                )
                
                # Check if OCR was successful
                if "error" not in result:
                    processing_time = result.get("processing_time", 0)
                    confidence = result.get("overall_confidence", 0)
                    
                    # Log anti-hallucination statistics
                    anti_hall_stats = result.get("anti_hallucination_stats", {})
                    filtered_lines = anti_hall_stats.get("filtered_lines", 0)
                    valid_lines = anti_hall_stats.get("valid_lines", 0)
                    
                    logger.info(f"SUCCESS: OPTIMIZED OCR succeeded on attempt {attempt + 1} in {processing_time:.2f}s (confidence: {confidence:.3f})")
                    if filtered_lines > 0:
                        logger.info(f"🛡️ ANTI-HALLUCINATION: {valid_lines} valid lines, {filtered_lines} suspicious lines filtered")
                    return result
                
                # If it's the last attempt, return the error
                if attempt == max_retries - 1:
                    logger.error(f"ERROR: OCR failed after {max_retries} attempts: {result.get('error')}")
                    return result
                
                # Wait before retry with exponential backoff
                wait_time = (2 ** attempt) * OCR_RETRY_DELAY_BASE
                logger.warning(f"WARNINGS: OCR attempt {attempt + 1} failed: {result.get('error')} | Retrying in {wait_time}s...")
                time.sleep(wait_time)
                
            except Exception as e:
                logger.error(f"ERROR: OCR attempt {attempt + 1} threw exception: {str(e)}")
                if attempt == max_retries - 1:
                    return {"error": f"OCR extraction failed: {str(e)}", "text_data": []}
                
                wait_time = (2 ** attempt) * OCR_RETRY_DELAY_BASE
                logger.warning(f"WARNINGS: Retrying in {wait_time}s...")
                time.sleep(wait_time)
        
        return {"error": "OCR failed after all retry attempts", "text_data": []}
    
    def _extract_text_optimized(
        self,
        file_path: str,
        file_type: str,
        quality_verdict: Optional[str] = None,
        page_count: int = 1
    ) -> Dict[str, Any]:
        """
        OPTIMIZED: Extract text using Azure Computer Vision OCR with performance optimizations.
        
        This is the core OCR logic (previously in file_utils.py extract_text_from_file_optimized).
        
        Args:
            file_path: Path to the file to process
            file_type: MIME type of the file
            quality_verdict: Quality analysis verdict (direct_analysis, pre_processing, etc.)
            page_count: Estimated number of pages for timeout calculation

        Returns:
            dict: Extracted text, confidence scores, bounding boxes, and page numbers
        """
        try:
            if file_type not in SUPPORTED_FILE_TYPES:
                logger.error(f"Unsupported file type: {file_type}")
                return {"error": f"Unsupported file type: {file_type}", "text_data": []}

            logger.info(f"📋 OCR REQUEST: Starting Azure Computer Vision OCR")
            logger.info(f"📄 File: {file_path}, Type: {file_type}")
            logger.info(f"🔧 Quality Verdict: {quality_verdict}, Estimated Pages: {page_count}")

            # OPTIMIZATION 1: Dynamic timeout calculation
            dynamic_timeout = OCR_TIMEOUT_BASE + (page_count * OCR_TIMEOUT_PER_PAGE)
            
            # OPTIMIZATION 2: Quality-based mode selection
            fast_mode = OCR_FAST_MODE and quality_verdict in ["direct_analysis", "good"]
            if fast_mode:
                dynamic_timeout = max(10, dynamic_timeout * 0.7)
                logger.info("Fast mode enabled for high-quality document")

            logger.info(f"⏱️ Dynamic timeout: {dynamic_timeout}s (base: {OCR_TIMEOUT_BASE}s + {page_count}*{OCR_TIMEOUT_PER_PAGE}s)")

            # Read file and send to Azure OCR
            file_size = os.path.getsize(file_path)
            logger.info(f"📋 COMPLETE OCR REQUEST TO AZURE COMPUTER VISION:")
            logger.info(f"  🌐 Endpoint: {COMPUTER_VISION_ENDPOINT}")
            logger.info(f"  🔑 API Key: {COMPUTER_VISION_KEY}")
            logger.info(f"  📄 Method: read_in_stream()")
            logger.info(f"  📁 File Path: {file_path}")
            logger.info(f"  📊 File Size: {file_size} bytes ({file_size/1024:.2f} KB)")
            logger.info(f"  📝 File Type: {file_type}")
            logger.info(f"  ⚙️ Parameters:")
            logger.info(f"    - raw=True (returns raw HTTP response)")
            logger.info(f"    - language: auto-detect")
            logger.info(f"    - model: latest OCR model")
            logger.info(f"  ⏱️ Expected timeout: {dynamic_timeout}s")
            logger.info(f"  🚀 Fast mode: {fast_mode}")
            logger.info(f"📤 Sending file stream to Azure OCR...")
            
            with open(file_path, "rb") as file_stream:
                read_response = self._cv_client.read_in_stream(file_stream, raw=True)
            
            logger.info(f"✅ Azure OCR API call successful, received operation location")
            logger.info(f"📋 API Response Headers: {dict(read_response.headers) if hasattr(read_response, 'headers') else 'N/A'}")

            # Extract operation ID from response headers
            operation_location = read_response.headers.get("Operation-Location")
            if not operation_location:
                logger.error("Azure OCR response missing 'Operation-Location' header.")
                return {"error": "Azure OCR response missing 'Operation-Location'", "text_data": []}

            operation_id = operation_location.split("/")[-1]

            # OPTIMIZATION 3: Adaptive polling with early termination
            start_time = time.time()
            poll_count = 0
            
            logger.info(f"⏳ Starting polling for operation ID: {operation_id}")
            
            while True:
                result = self._cv_client.get_read_result(operation_id)
                poll_count += 1
                logger.info(f"🔄 Poll #{poll_count}: Status={result.status}")
                
                # OPTIMIZATION 4: Early termination for completed operations
                if result.status not in ["notStarted", "running"]:
                    processing_time = time.time() - start_time
                    logger.info(f"✅ OCR operation completed in {processing_time:.2f}s after {poll_count} polls")
                    logger.info(f"📊 Final Status: {result.status}")
                    break

                # OPTIMIZATION 5: Timeout check
                if time.time() - start_time > dynamic_timeout:
                    logger.error(f"OCR processing timeout exceeded ({dynamic_timeout}s).")
                    return {"error": f"OCR processing took too long (>{dynamic_timeout}s)", "text_data": []}

                # OPTIMIZATION 6: Adaptive polling intervals
                if OCR_ADAPTIVE_POLLING:
                    if poll_count <= 2:
                        sleep_time = 0.1  # Very fast initial polls
                    elif poll_count <= 5:
                        sleep_time = OCR_POLLING_INTERVAL  # Standard polling
                    else:
                        sleep_time = min(1.0, OCR_POLLING_INTERVAL * 2)  # Slower for long operations
                else:
                    sleep_time = OCR_POLLING_INTERVAL
                    
                time.sleep(sleep_time)

            # Check OCR result status
            if result.status != OperationStatusCodes.succeeded:
                logger.warning(f"Azure OCR failed with status: {result.status}")
                return {
                    "error": f"Azure OCR failed. Status: {result.status}",
                    "text_data": []
                }

            # ANTI-HALLUCINATION: Extract text with confidence filtering and validation
            logger.info(f"🔍 Starting text extraction with anti-hallucination filtering...")
            text_data = []
            word_data = []
            total_confidence = 0
            line_count = 0
            filtered_out_count = 0
            
            logger.info(f"🛡️ Anti-hallucination settings: MinConfidence={MIN_CONFIDENCE_THRESHOLD}, MinWordLength={MIN_WORD_LENGTH}")
            
            total_pages = len(result.analyze_result.read_results)
            logger.info(f"📄 Processing {total_pages} pages from Azure OCR results...")
            
            for page_num, read_result in enumerate(result.analyze_result.read_results, start=1):
                page_lines = len(read_result.lines)
                logger.info(f"📄 Processing Page {page_num}/{total_pages}: {page_lines} lines detected")
                
                for line in read_result.lines:
                    words = line.words
                    
                    # OPTIMIZATION 7: Enhanced confidence calculation with validation
                    if words:
                        confidence_scores = [word.confidence for word in words if hasattr(word, "confidence")]
                        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 1.0
                        
                        # ANTI-HALLUCINATION: Filter high-confidence words only
                        valid_words = []
                        for word in words:
                            word_confidence = getattr(word, "confidence", 1.0)
                            word_text = word.text.strip()
                            
                            # Skip low-confidence words
                            if word_confidence < MIN_CONFIDENCE_THRESHOLD:
                                continue
                                
                            # Skip very short words that are often noise
                            if len(word_text) < MIN_WORD_LENGTH:
                                continue
                                
                            # Skip suspicious patterns (only symbols, empty, etc.)
                            is_suspicious = any(re.match(pattern, word_text) for pattern in SUSPICIOUS_PATTERNS)
                            if is_suspicious:
                                continue
                                
                            valid_words.append(word)
                            word_data.append({
                                "text": word_text,
                                "bounding_box": getattr(word, "bounding_box", None),
                                "bounding_page": page_num,
                                "confidence": word_confidence
                            })
                        
                        # Reconstruct line text from valid words only
                        if valid_words:
                            validated_line_text = " ".join([w.text for w in valid_words])
                            # Recalculate confidence based on valid words only
                            valid_confidences = [getattr(w, "confidence", 1.0) for w in valid_words]
                            avg_confidence = sum(valid_confidences) / len(valid_confidences) if valid_confidences else 1.0
                        else:
                            validated_line_text = ""
                            avg_confidence = 0.0
                    else:
                        validated_line_text = line.text
                        avg_confidence = 1.0

                    # ANTI-HALLUCINATION: Only include lines with sufficient confidence and content
                    if avg_confidence >= MIN_CONFIDENCE_THRESHOLD and validated_line_text.strip():
                        text_data.append({
                            "text": validated_line_text,
                            "bounding_box": line.bounding_box,
                            "bounding_page": page_num,
                            "confidence": avg_confidence
                        })
                        
                        total_confidence += avg_confidence
                        line_count += 1
                    else:
                        filtered_out_count += 1

            if not text_data:
                logger.warning("Azure OCR returned no text.")
                return {"error": "No text extracted", "text_data": []}

            # OPTIMIZATION 8: Quality metrics with anti-hallucination stats
            overall_confidence = total_confidence / line_count if line_count > 0 else 0.0
            processing_time = time.time() - start_time
            
            logger.info(f"📊 OCR RESPONSE: Extraction Complete")
            logger.info(f"✅ Valid Lines: {len(text_data)}, Total Words: {len(word_data)}")
            logger.info(f"📈 Overall Confidence: {overall_confidence:.3f}")
            logger.info(f"🛡️ Anti-hallucination: Filtered {filtered_out_count} suspicious lines (kept {len(text_data)} valid)")
            logger.info(f"⏱️ Total Processing Time: {processing_time:.2f}s")
            logger.info(f"⚡ Performance: {len(text_data)/processing_time:.1f} lines/sec, {poll_count} API polls")
            logger.info(f"🔧 Optimization Stats: FastMode={fast_mode}, AdaptivePolling={OCR_ADAPTIVE_POLLING}, Timeout={dynamic_timeout}s")
            
            return {
                "text_data": text_data,
                "processing_time": processing_time,
                "overall_confidence": overall_confidence,
                "anti_hallucination_stats": {
                    "filtered_lines": filtered_out_count,
                    "valid_lines": len(text_data),
                    "confidence_threshold": MIN_CONFIDENCE_THRESHOLD,
                    "total_words": len(word_data)
                },
                "optimization_stats": {
                    "fast_mode": fast_mode,
                    "dynamic_timeout": dynamic_timeout,
                    "poll_count": poll_count,
                    "adaptive_polling": OCR_ADAPTIVE_POLLING
                },
                "word_data": word_data
            }

        except Exception as e:
            logger.error(f"Unexpected error in optimized OCR extraction: {e}")
            return {"error": str(e), "text_data": []}
    
    def _organize_by_page(self, text_data: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        Organize OCR data by page number.
        
        Args:
            text_data: List of OCR entries with bounding_page field
            
        Returns:
            List of lists, where each inner list contains OCR entries for a page
        """
        logger.info(f"ANALYTICS: === ORGANIZING OCR DATA BY PAGE ===")
        logger.info(f"Input: {len(text_data)} OCR entries")
        
        # Debug: Check page distribution in raw data
        page_counts = {}
        missing_page_count = 0
        
        for i, entry in enumerate(text_data):
            page = entry.get("bounding_page", None)
            if page is None:
                missing_page_count += 1
                logger.warning(f"Entry {i}: Missing bounding_page field - {entry.get('text', '')[:30]}...")
                page = 1  # Default fallback
            
            page_counts[page] = page_counts.get(page, 0) + 1
        
        logger.info(f"ANALYTICS: Page distribution in raw OCR data:")
        for page in sorted(page_counts.keys()):
            logger.info(f"   Page {page}: {page_counts[page]} entries")
        
        if missing_page_count > 0:
            logger.warning(f"WARNINGS: Found {missing_page_count} entries without page information")
        
        # Organize by page
        pages = defaultdict(list)
        for entry in text_data:
            page = entry.get("bounding_page", 1)
            pages[page].append(entry)
        
        organized_pages = [pages[k] for k in sorted(pages)]
        logger.info(f"SUCCESS: Organized into {len(organized_pages)} pages")
        
        # Debug: Log sample from each page
        for page_idx, page_data in enumerate(organized_pages):
            actual_page = page_idx + 1
            logger.info(f"   Page {actual_page}: {len(page_data)} entries")
            if page_data:
                sample_text = page_data[0].get('text', '')[:30]
                logger.info(f"      Sample: '{sample_text}...'")
        
        return organized_pages
    
    @staticmethod
    def get_page_text(pages_ocr_data: List[List[Dict[str, Any]]], page_number: int) -> str:
        """
        Get concatenated text for a specific page.
        
        Args:
            pages_ocr_data: Organized OCR data by pages
            page_number: 1-indexed page number
            
        Returns:
            Concatenated text for the specified page
        """
        if page_number < 1 or page_number > len(pages_ocr_data):
            return ""
        
        page_data = pages_ocr_data[page_number - 1]
        return "\n".join([entry.get('text', '') for entry in page_data])
    
    @staticmethod
    def get_all_text(pages_ocr_data: List[List[Dict[str, Any]]]) -> str:
        """
        Get concatenated text for all pages.
        
        Args:
            pages_ocr_data: Organized OCR data by pages
            
        Returns:
            Concatenated text for all pages
        """
        all_text = []
        for page_data in pages_ocr_data:
            page_text = "\n".join([entry.get('text', '') for entry in page_data])
            all_text.append(page_text)
        return "\n\n".join(all_text)
