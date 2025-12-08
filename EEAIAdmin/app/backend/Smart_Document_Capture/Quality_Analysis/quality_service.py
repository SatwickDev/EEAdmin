"""
Quality Analysis Service Module
================================
Step 1 in the AI Document Processing Pipeline.

This service handles:
- File upload and temporary storage
- Document quality analysis using GPT-4o Vision API
- Quality verdict determination (direct_analysis, pre_processing, azure_analysis, reupload)
- Processing recommendations based on quality score

The service abstracts the quality analysis logic from routes.py to provide
a clean, testable, and maintainable interface.
"""

import os
import time
import tempfile
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

# Import the DocumentQualityAnalyzer from the local module
from .quality_analyzer import DocumentQualityAnalyzer

logger = logging.getLogger(__name__)


@dataclass
class QualityAnalysisResult:
    """Data class representing the result of quality analysis."""
    success: bool
    quality_score: float
    verdict: str
    pages_analyzed: int
    processing_time: float
    file_name: str
    file_type: str
    temp_file_path: str
    quality_result: Dict[str, Any]
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "success": self.success,
            "quality_score": self.quality_score,
            "verdict": self.verdict,
            "pages_analyzed": self.pages_analyzed,
            "processing_time": self.processing_time,
            "file_name": self.file_name,
            "file_type": self.file_type,
            "temp_file_path": self.temp_file_path,
            "quality_result": self.quality_result,
            "error": self.error
        }


class QualityAnalysisService:
    """
    Service class for Step 1: Quality Analysis in Document Processing Pipeline.
    
    This service handles:
    1. Saving uploaded file to temporary location
    2. Analyzing document quality using GPT-4o Vision API
    3. Returning quality verdict and recommendations
    
    Usage:
        service = QualityAnalysisService()
        result = service.analyze(uploaded_file, progress_tracker)
    """

    def __init__(self):
        """Initialize the Quality Analysis Service."""
        self._quality_analyzer = DocumentQualityAnalyzer()
        logger.info("QualityAnalysisService initialized")

    def analyze(
        self,
        uploaded_file,
        progress_tracker=None
    ) -> QualityAnalysisResult:
        """
        Perform quality analysis on an uploaded document.
        
        This is the main entry point for Step 1 of document processing.
        
        Args:
            uploaded_file: Flask FileStorage object containing the uploaded file
            progress_tracker: Optional progress tracker for WebSocket updates
            
        Returns:
            QualityAnalysisResult containing quality score, verdict, and temp file path
        """
        temp_file_path = None
        
        try:
            file_name = uploaded_file.filename
            file_type = uploaded_file.content_type
            
            logger.info(f"🔍 STEP 1: Quality Analysis Service started for: {file_name}")
            start_time = time.time()
            
            # === STEP 1.1: Save file to temporary location ===
            if progress_tracker:
                progress_tracker.start_upload(file_name)
            
            temp_file_path = self._save_to_temp(uploaded_file, file_name)
            
            if progress_tracker:
                progress_tracker.upload_complete()
            
            logger.info(f"✅ File uploaded to temp: {temp_file_path}")
            
            # === STEP 1.2: Perform Quality Analysis ===
            if progress_tracker:
                progress_tracker.start_quality_analysis()
            
            logger.info(f"🔍 Performing quality analysis...")
            quality_start = time.time()
            
            quality_result = self._quality_analyzer.analyze_document_quality_fast(
                temp_file_path,
                file_name,
                progress_tracker
            )
            
            quality_time = time.time() - quality_start
            
            # Extract key metrics
            verdict = quality_result.get("verdict", "pre_processing")
            quality_score = quality_result.get("quality_score", 0.5)
            pages_analyzed = quality_result.get("pages_analyzed", 1)
            
            logger.info(
                f"✅ Quality analysis complete: {verdict} "
                f"(score: {quality_score:.3f}) in {quality_time:.2f}s"
            )
            
            if progress_tracker:
                progress_tracker.quality_complete(verdict, quality_score)
            
            total_time = time.time() - start_time
            
            return QualityAnalysisResult(
                success=True,
                quality_score=quality_score,
                verdict=verdict,
                pages_analyzed=pages_analyzed,
                processing_time=total_time,
                file_name=file_name,
                file_type=file_type,
                temp_file_path=temp_file_path,
                quality_result=quality_result,
                error=None
            )
            
        except Exception as e:
            logger.error(f"❌ Quality analysis failed: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            
            return QualityAnalysisResult(
                success=False,
                quality_score=0.0,
                verdict="error",
                pages_analyzed=0,
                processing_time=0.0,
                file_name=uploaded_file.filename if uploaded_file else "unknown",
                file_type=uploaded_file.content_type if uploaded_file else "unknown",
                temp_file_path=temp_file_path or "",
                quality_result={},
                error=str(e)
            )

    def _save_to_temp(self, uploaded_file, file_name: str) -> str:
        """
        Save uploaded file to a temporary location.
        
        Args:
            uploaded_file: Flask FileStorage object
            file_name: Original filename
            
        Returns:
            Path to the temporary file
        """
        file_extension = os.path.splitext(file_name)[1] if file_name else ''
        
        with tempfile.NamedTemporaryFile(
            delete=False, 
            suffix=file_extension
        ) as temp_file:
            temp_file_path = temp_file.name
            uploaded_file.save(temp_file_path)
        
        return temp_file_path

    def analyze_instant(
        self,
        file_path: str,
        file_name: str,
        file_type: str
    ) -> Dict[str, Any]:
        """
        Perform instant heuristic-based quality check without Vision API.
        
        This is a fast alternative (~0.1s) compared to Vision API (~40-65s).
        Uses file-based heuristics like size, type, and filename patterns.
        
        Args:
            file_path: Path to the document file
            file_name: Original filename
            file_type: MIME type of the file
            
        Returns:
            Dictionary containing quality analysis results
        """
        try:
            # Get file metadata
            file_size = os.path.getsize(file_path)
            file_size_mb = file_size / (1024 * 1024)
            
            # Estimate quality based on file characteristics
            quality_score = 0.7  # Default: good quality
            verdict = "pre_processing"  # Default verdict
            
            # Size-based heuristics
            if file_type == "application/pdf":
                if file_size_mb > 5:
                    quality_score = 0.85
                elif file_size_mb > 1:
                    quality_score = 0.75
                else:
                    quality_score = 0.7
                
                # Estimate page count (~100KB per page average)
                estimated_pages = max(1, int(file_size_mb / 0.1))
            else:
                # Image files
                if file_size_mb > 2:
                    quality_score = 0.85
                elif file_size_mb > 0.5:
                    quality_score = 0.75
                else:
                    quality_score = 0.65
                estimated_pages = 1
            
            # Filename pattern heuristics
            filename_lower = file_name.lower()
            quality_boost_keywords = ['hq', 'high', 'quality', 'export', 'digital']
            quality_reduce_keywords = ['scan', 'fax', 'copy']
            
            if any(word in filename_lower for word in quality_boost_keywords):
                quality_score = min(1.0, quality_score + 0.1)
            elif any(word in filename_lower for word in quality_reduce_keywords):
                quality_score = max(0.5, quality_score - 0.1)
            
            result = {
                "success": True,
                "quality_score": round(quality_score, 3),
                "verdict": verdict,
                "analysis_type": "instant_heuristic",
                "pages_analyzed": estimated_pages,
                "page_results": [],
                "file_name": file_name,
                "file_size_mb": round(file_size_mb, 2),
                "processing_time": 0.0,
                "recommendations": [
                    f"Estimated {estimated_pages} pages",
                    f"File size: {round(file_size_mb, 1)}MB",
                    f"Quality score: {quality_score:.2f} (heuristic-based)",
                    "Using standard OCR settings for optimal processing"
                ]
            }
            
            logger.info(
                f"⚡ INSTANT quality check: {verdict} "
                f"(score: {quality_score:.3f}, {estimated_pages} pages, "
                f"{round(file_size_mb, 1)}MB)"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Instant quality check failed: {e}")
            return {
                "success": True,
                "quality_score": 0.7,
                "verdict": "pre_processing",
                "analysis_type": "instant_heuristic_fallback",
                "pages_analyzed": 1,
                "page_results": [],
                "file_name": file_name,
                "processing_time": 0.0,
                "recommendations": ["Using default quality settings"]
            }

    @staticmethod
    def cleanup_temp_file(temp_file_path: str) -> bool:
        """
        Clean up temporary file after processing.
        
        Args:
            temp_file_path: Path to the temporary file to delete
            
        Returns:
            True if cleanup was successful, False otherwise
        """
        try:
            if temp_file_path and os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                logger.info(f"🗑️ Cleaned up temporary file: {temp_file_path}")
                return True
        except Exception as e:
            logger.warning(f"⚠️ Failed to cleanup temp file {temp_file_path}: {e}")
        return False


# Create a singleton instance for easy import
quality_service = QualityAnalysisService()
