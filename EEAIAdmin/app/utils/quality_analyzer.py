"""import os
import logging
import json
import time
import base64
import fitz  # PyMuPDF
from typing import Dict, List, Optional
import openai
from PIL import Image
import io

logger = logging.getLogger(__name__)ty Analyzer using GPT-4o Vision API
"""

import os
import logging
import json
import time
import base64
import tempfile
import fitz  # PyMuPDF
from typing import Dict, List, Optional
import openai
from PIL import Image
import io
from .progress_tracker import ProcessingStage

logger = logging.getLogger(__name__)

class DocumentQualityAnalyzer:
    """
    Analyzes document quality using GPT-4o Vision API for determining 
    optimal processing approach before OCR extraction.
    """
    
    def __init__(self):
        """Initialize the quality analyzer with Azure OpenAI configuration."""
        # Azure OpenAI Configuration from provided config
        self.azure_config = {
            "api_key": "GPbELdmNOZA6LlMHgYyjcOPWeU9VIEYh0jo1hggpB4urTfDoJMijJQQJ99BAACYeBjFXJ3w3AAABACOGDMQ4",
            "endpoint": "https://newfinaiapp.openai.azure.com/",
            "api_version": "2024-12-01-preview",
            "deployment_name": "gpt-4o"
        }
        
        # Set OpenAI configuration
        openai.api_type = "azure"
        openai.api_base = self.azure_config["endpoint"]
        openai.api_key = self.azure_config["api_key"]
        openai.api_version = self.azure_config["api_version"]
        
        # GPT-4o Vision configuration from provided config
        self.vision_config = {
            "model": "gpt-4o",
            "max_tokens": 4000,
            "temperature": 0.1,
            "top_p": 0.95,
            "frequency_penalty": 0,
            "presence_penalty": 0,
            "image_quality": "high",
            "system_prompt": """You are an expert document quality analyst. 
            Analyze the provided document image for quality assessment including 
            clarity, readability, completeness, formatting, and overall document 
            integrity. Provide a comprehensive quality score and detailed analysis."""
        }
        
        # Quality thresholds from provided config
        self.thresholds = {
            "direct_analysis": 0.80,  # High quality - proceed directly
            "pre_processing": 0.50,   # Medium quality - needs enhancement
            "azure_analysis": 0.30,   # Low quality - use Azure Document Intelligence
            "reupload": 0.30          # Very poor quality - recommend reupload
        }
        
        # Quality metric thresholds from provided config
        self.quality_metrics = {
            "blur_score": {
                "excellent": 2200, "good": 1300, "medium": 600, "low": 0
            },
            "contrast_score": {
                "excellent": 0.28, "good": 0.20, "medium": 0.13, "low": 0
            },
            "noise_level": {
                "excellent": 0.05, "good": 0.12, "medium": 0.25, "low": 1.0
            },
            "sharpness_score": {
                "excellent": 0.45, "good": 0.25, "medium": 0.10, "low": 0
            },
            "brightness_score": {
                "excellent": 0.70, "good": 0.50, "medium": 0.30, "low": 0
            },
            "confidence_score": {
                "excellent": 0.95, "good": 0.8, "medium": 0.6, "low": 0.4
            }
        }
        
        # Processing recommendations from provided config
        self.recommendations = {
            "excellent": {
                "method": "direct_analysis",
                "confidence": 0.95,
                "preprocessing": False,
                "suggested_enhancement": None
            },
            "good": {
                "method": "direct_analysis", 
                "confidence": 0.85,
                "preprocessing": False,
                "suggested_enhancement": "Optional brightness adjustment"
            },
            "medium": {
                "method": "pre_processing",
                "confidence": 0.65,
                "preprocessing": True,
                "suggested_enhancement": "Image enhancement required"
            },
            "low": {
                "method": "azure_analysis",
                "confidence": 0.45,
                "preprocessing": True,
                "suggested_enhancement": "Significant enhancement needed"
            },
            "very_low": {
                "method": "reupload",
                "confidence": 0.20,
                "preprocessing": False,
                "suggested_enhancement": "Document reupload recommended"
            }
        }

    def analyze_document_quality(self, file_path: str, file_name: str, progress_tracker=None) -> Dict:
        """
        Analyze document quality using GPT-4o Vision API.
        
        Args:
            file_path: Path to the document file
            file_name: Original filename for logging
            progress_tracker: Optional progress tracker for WebSocket updates
            
        Returns:
            Dictionary containing quality analysis results
        """
        start_time = time.time()
        
        try:
            logger.info(f"🔍 Starting quality analysis for: {file_name}")
            
            if progress_tracker:
                progress_tracker.update_stage(ProcessingStage.QUALITY_ANALYSIS, "Analyzing document quality...", 10)
            
            # Determine file type from original filename and convert to images
            file_extension = os.path.splitext(file_name)[1].lower()
            logger.info(f"📄 Processing file with extension: {file_extension}")
            
            if file_extension == '.pdf':
                logger.info("🔄 Converting PDF to images for quality analysis")
                page_images = self._convert_pdf_to_images(file_path)
            elif file_extension in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']:
                logger.info("🖼️ Processing image file directly")
                page_images = [self._load_image_file(file_path)]
            else:
                logger.warning(f"⚠️ Unsupported file type: {file_extension}")
                return self._create_error_result(f"Unsupported file type: {file_extension}", file_name)
            
            if not page_images:
                return self._create_error_result("Failed to load document images", file_name)
            
            logger.info(f"📄 Processing {len(page_images)} pages for quality analysis")
            
            # Analyze each page
            page_results = []
            total_score = 0.0
            valid_pages = 0
            
            for page_num, img_base64 in enumerate(page_images, 1):
                if progress_tracker:
                    progress = 10 + (page_num / len(page_images)) * 80  # 10-90% of quality stage
                    progress_tracker.update_stage(
                        ProcessingStage.QUALITY_ANALYSIS, 
                        f"Analyzing page {page_num}/{len(page_images)}...", 
                        int(progress)
                    )
                
                page_result = self._analyze_page_quality(img_base64, page_num)
                
                if page_result:
                    page_results.append(page_result)
                    total_score += page_result.get("score", 0.5)
                    valid_pages += 1
                else:
                    # Add fallback result for failed pages
                    page_results.append(self._create_fallback_page_result(page_num))
                    total_score += 0.5
                    valid_pages += 1
            
            # Calculate overall results
            overall_score = total_score / valid_pages if valid_pages > 0 else 0.0
            verdict = self._determine_verdict(overall_score)
            
            processing_time = time.time() - start_time
            
            result = {
                "success": True,
                "quality_score": round(overall_score, 3),
                "verdict": verdict,
                "analysis_type": "gpt4o_vision",
                "pages_analyzed": valid_pages,
                "page_results": page_results,
                "file_name": file_name,
                "processing_time": round(processing_time, 2),
                "recommendations": self._get_processing_recommendations(verdict, overall_score)
            }
            
            logger.info(f"✅ Quality analysis completed: {verdict} (score: {overall_score:.3f}) in {processing_time:.2f}s")
            
            if progress_tracker:
                progress_tracker.update_stage(ProcessingStage.QUALITY_ANALYSIS, f"Quality analysis complete: {verdict}", 100)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Quality analysis failed for {file_name}: {str(e)}")
            return self._create_error_result(str(e), file_name)

    def _convert_pdf_to_images(self, pdf_path: str) -> List[str]:
        """Convert PDF pages to base64 encoded images."""
        images = []
        try:
            doc = fitz.open(pdf_path)
            
            for page_num in range(min(len(doc), 10)):  # Limit to first 10 pages
                page = doc[page_num]
                # Use higher resolution for better quality analysis
                mat = fitz.Matrix(2.0, 2.0)  # 2x scale factor
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("png")
                
                # Convert to base64
                img_base64 = base64.b64encode(img_data).decode('utf-8')
                images.append(img_base64)
            
            doc.close()
            return images
            
        except Exception as e:
            logger.error(f"❌ Failed to convert PDF to images: {str(e)}")
            return []

    def _load_image_file(self, image_path: str) -> Optional[str]:
        """Load and convert image file to base64."""
        try:
            # Check if file exists
            if not os.path.exists(image_path):
                logger.error(f"❌ Image file not found: {image_path}")
                return None
                
            with open(image_path, 'rb') as img_file:
                img_data = img_file.read()
            
            # Verify it's a valid image by trying to open it
            try:
                img = Image.open(io.BytesIO(img_data))
                img.verify()  # Verify the image is not corrupted
            except Exception as verify_error:
                logger.error(f"❌ Invalid image file {image_path}: {str(verify_error)}")
                return None
            
            # Re-open for processing (verify() closes the image)
            img = Image.open(io.BytesIO(img_data))
            
            # Optionally resize large images for API efficiency
            if img.width > 2048 or img.height > 2048:
                logger.info(f"📏 Resizing large image from {img.width}x{img.height} to fit 2048x2048")
                img.thumbnail((2048, 2048), Image.Resampling.LANCZOS)
                output = io.BytesIO()
                img.save(output, format='PNG')
                img_data = output.getvalue()
            
            return base64.b64encode(img_data).decode('utf-8')
            
        except Exception as e:
            logger.error(f"❌ Failed to load image file: {str(e)}")
            return None

    def _analyze_page_quality(self, img_base64: str, page_num: int) -> Optional[Dict]:
        """Analyze quality of a single page using GPT-4o Vision."""
        try:
            # Prepare quality analysis prompt
            prompt = '''Analyze this document page image for quality metrics and return ONLY a JSON response with these exact metrics:

{
    "blur_score": 0-100,
    "resolution_quality": 0.0-1.0,
    "skew_angle": -45 to 45,
    "contrast_score": 0.0-1.0,
    "noise_level": 0.0-1.0,
    "sharpness_score": 0.0-1.0,
    "brightness_score": 0.0-1.0,
    "shadow_glare_score": 0.0-1.0,
    "text_clarity": 0.0-1.0,
    "edge_quality": 0.0-1.0,
    "overall_readability": 0.0-1.0
}

Quality Guidelines:
- blur_score: 0-30=very blurry, 30-50=poor focus, 50-70=moderate, 70-85=good, 85-100=excellent
- All other scores: 0.0=very poor, 0.3=poor, 0.5=fair, 0.7=good, 0.9=excellent, 1.0=perfect
- noise_level: LOWER is better (0.0=no noise, 1.0=very noisy)
- Focus on text readability and OCR suitability
- Return ONLY valid JSON, no explanations or markdown'''
            
            # Call GPT-4o Vision API with Azure configuration
            response = openai.ChatCompletion.create(
                engine=self.azure_config["deployment_name"],
                messages=[
                    {
                        "role": "system",
                        "content": self.vision_config["system_prompt"]
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{img_base64}",
                                    "detail": self.vision_config["image_quality"]
                                }
                            }
                        ]
                    }
                ],
                max_tokens=self.vision_config["max_tokens"],
                temperature=self.vision_config["temperature"],
                top_p=self.vision_config["top_p"],
                frequency_penalty=self.vision_config["frequency_penalty"],
                presence_penalty=self.vision_config["presence_penalty"]
            )
            
            # Parse response
            content = response.choices[0].message.content.strip()
            metrics_data = self._parse_gpt_response(content)
            
            if not metrics_data:
                return None
            
            # Calculate overall page score
            page_score = self._calculate_page_score(metrics_data)
            
            return {
                "page": page_num,
                "score": round(page_score, 3),
                "metrics": metrics_data,
                "verdict": self._determine_page_verdict(page_score)
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to analyze page {page_num}: {str(e)}")
            return None

    def _parse_gpt_response(self, content: str) -> Optional[Dict]:
        """Parse GPT-4o JSON response, handling markdown formatting."""
        try:
            # Clean content - remove markdown code blocks if present
            clean_content = content.strip()
            if clean_content.startswith("```json"):
                clean_content = clean_content[7:]
            elif clean_content.startswith("```"):
                clean_content = clean_content[3:]
            if clean_content.endswith("```"):
                clean_content = clean_content[:-3]
            clean_content = clean_content.strip()
            
            return json.loads(clean_content)
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse GPT response: {e}")
            logger.error(f"Response content: {content}")
            return None

    def _calculate_page_score(self, metrics: Dict) -> float:
        """Calculate overall quality score for a page based on metrics."""
        # Normalize blur_score from 0-100 to 0-1 range
        normalized_blur = metrics.get("blur_score", 50) / 100.0
        
        # Weight key metrics for OCR quality
        weighted_metrics = {
            "blur_score": normalized_blur * 0.25,           # Focus is critical
            "text_clarity": metrics.get("text_clarity", 0.5) * 0.20,      # Text readability
            "contrast_score": metrics.get("contrast_score", 0.5) * 0.15,   # Contrast helps OCR
            "sharpness_score": metrics.get("sharpness_score", 0.5) * 0.15,  # Sharpness
            "overall_readability": metrics.get("overall_readability", 0.5) * 0.15, # General readability
            "brightness_score": metrics.get("brightness_score", 0.5) * 0.10    # Brightness
        }
        
        # Calculate weighted average
        total_score = sum(weighted_metrics.values())
        
        # Apply penalties for high noise
        noise_penalty = metrics.get("noise_level", 0.5) * 0.1
        total_score = max(0.0, total_score - noise_penalty)
        
        return min(1.0, total_score)

    def _determine_verdict(self, overall_score: float) -> str:
        """Determine processing verdict based on overall quality score."""
        if overall_score >= self.thresholds["direct_analysis"]:
            return "direct_analysis"
        elif overall_score >= self.thresholds["pre_processing"]:
            return "pre_processing"
        elif overall_score >= self.thresholds["azure_analysis"]:
            return "azure_analysis"
        else:
            return "reupload"

    def _determine_page_verdict(self, page_score: float) -> str:
        """Determine verdict for individual page."""
        return self._determine_verdict(page_score)

    def _get_processing_recommendations(self, verdict: str, score: float) -> List[str]:
        """Get processing recommendations based on verdict."""
        recommendations = []
        
        if verdict == "direct_analysis":
            recommendations.append("✅ Excellent quality - proceed with standard OCR processing")
            recommendations.append("📝 Document is suitable for high-accuracy text extraction")
            
        elif verdict == "pre_processing":
            recommendations.append("⚡ Apply image enhancement before OCR")
            recommendations.append("🔧 Consider contrast/brightness adjustments")
            recommendations.append("📐 Check for skew correction needs")
            
        elif verdict == "azure_analysis":
            recommendations.append("🔍 Use Azure Document Intelligence for better results")
            recommendations.append("📄 Document quality requires advanced OCR capabilities")
            recommendations.append("⚠️ Standard OCR may produce lower accuracy")
            
        else:  # reupload
            recommendations.append("❌ Poor quality detected - recommend document reupload")
            recommendations.append("📸 Try rescanning with better lighting/focus")
            recommendations.append("🔄 Current quality may result in poor text extraction")
            
        return recommendations

    def _create_fallback_page_result(self, page_num: int) -> Dict:
        """Create fallback result for failed page analysis."""
        return {
            "page": page_num,
            "score": 0.5,
            "metrics": {
                "blur_score": 50.0,
                "resolution_quality": 0.5,
                "skew_angle": 0.0,
                "contrast_score": 0.5,
                "noise_level": 0.5,
                "sharpness_score": 0.5,
                "brightness_score": 0.5,
                "shadow_glare_score": 0.5,
                "text_clarity": 0.5,
                "edge_quality": 0.5,
                "overall_readability": 0.5
            },
            "verdict": "pre_processing"
        }

    def _create_error_result(self, error_message: str, file_name: str) -> Dict:
        """Create error result structure."""
        return {
            "success": False,
            "error": error_message,
            "file_name": file_name,
            "quality_score": 0.0,
            "verdict": "error",
            "analysis_type": "gpt4o_vision",
            "pages_analyzed": 0,
            "page_results": [],
            "processing_time": 0.0,
            "recommendations": ["❌ Quality analysis failed - proceeding with standard processing"]
        }


# Global instance for easy import
quality_analyzer = DocumentQualityAnalyzer()