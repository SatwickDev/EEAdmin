"""
Step 3: Classification Service

This module provides document page classification functionality using Azure OpenAI.
It classifies each page of a document into predefined trade finance document types.

Key Features:
- Batch page classification using GPT-4o
- Multi-document package detection (Covering Schedule logic)
- Document type validation against predefined list
- Continuation page detection
- Document type alias normalization
"""

import json
import logging
import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

import openai

from app.utils.app_config import deployment_name
from .document_classifier import DocumentClassifier

logger = logging.getLogger(__name__)


@dataclass
class PageClassification:
    """Represents a classification result for a single page."""
    page: int
    document_type: str
    confidence: float
    text: str
    ocr_data: List[Dict]
    is_continuation: bool
    reasoning: str = ""
    
    def to_dict(self) -> Dict:
        """Convert to dictionary representation."""
        return {
            'page': self.page,
            'document_type': self.document_type,
            'confidence': self.confidence,
            'text': self.text,
            'ocr_data': self.ocr_data,
            'is_continuation': self.is_continuation,
            'reasoning': self.reasoning
        }


@dataclass
class ClassificationResult:
    """Result from the classification service."""
    success: bool
    page_classifications: List[PageClassification] = field(default_factory=list)
    processing_time: float = 0.0
    error: Optional[str] = None
    package_analysis: Dict = field(default_factory=dict)
    unique_document_types: List[str] = field(default_factory=list)
    continuation_count: int = 0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary representation."""
        return {
            'success': self.success,
            'page_classifications': [pc.to_dict() for pc in self.page_classifications],
            'processing_time': self.processing_time,
            'error': self.error,
            'package_analysis': self.package_analysis,
            'unique_document_types': self.unique_document_types,
            'continuation_count': self.continuation_count
        }


class ClassificationService:
    """
    Service for classifying document pages into trade finance document types.
    
    This service uses Azure OpenAI GPT-4 to classify each page of a document
    into predefined document types used in trade finance operations.
    """
    
    # Document type aliases for normalization
    DOCUMENT_TYPE_ALIASES = {
        'Weight List': 'Certificate of Weight',
        'weight list': 'Certificate of Weight',
        'Weight Certificate': 'Certificate of Weight',
        'Weighing Certificate': 'Certificate of Weight',
        'Certificate Of Origin': 'Preferential Certificate of Origin',
        'certificate of origin': 'Preferential Certificate of Origin',
        'Certificate of Origin': 'Preferential Certificate of Origin',
        'COO': 'Preferential Certificate of Origin',
        'Origin Certificate': 'Preferential Certificate of Origin',
        'Marine Insurance policy': 'Cargo Insurance Document',
        'Marine Insurance Policy': 'Cargo Insurance Document',
        'marine insurance policy': 'Cargo Insurance Document',
        'Shipment Consignment Advice': 'Cargo Insurance Document',
        'shipment consignment advice': 'Cargo Insurance Document',
        'Insurance Consignment Advice': 'Cargo Insurance Document',
        'Insurance Advice': 'Cargo Insurance Document',
        'Certificate from Ship-Owner': 'Vessel Certificate',
        'certificate from ship-owner': 'Vessel Certificate',
        'Certificate from Ship Owner': 'Vessel Certificate',
        'CERTIFICATE FROM SHIP OWNER': 'Vessel Certificate',
        'Certificate from Ship-Owner or Vessel Agent': 'Vessel Certificate',
        'Mill Certificate': 'Certificate of Inspection for Organic Products',
        'mill certificate': 'Certificate of Inspection for Organic Products',
        'Mill Test Certificate': 'Certificate of Inspection for Organic Products',
        'Material Test Certificate': 'Certificate of Inspection for Organic Products',
        'Quality Certificate': 'Certificate of Inspection for Organic Products',
        'Test Certificate': 'Certificate of Inspection for Organic Products',
    }
    
    def __init__(self, document_classifier: Optional[DocumentClassifier] = None):
        """
        Initialize the Classification Service.
        
        Args:
            document_classifier: Optional DocumentClassifier instance. If not provided,
                                 a new instance will be created.
        """
        logger.info("ClassificationService initialized")
        self.document_classifier = document_classifier or DocumentClassifier()
        self._load_valid_document_types()
    
    def _load_valid_document_types(self):
        """Load valid document types from the document classifier."""
        self.valid_document_types = set()
        for doc_id, mapping in self.document_classifier.entity_mappings.items():
            document_name = mapping.get('documentName', doc_id)
            self.valid_document_types.add(document_name)
        self.valid_document_types.update(['Empty/Insufficient Text', 'Unknown', 'Covering Schedule'])
        logger.info(f"📋 Loaded {len(self.valid_document_types)} valid document types")
    
    def classify(
        self,
        pages_ocr_data: List[List[Dict]],
        progress_tracker=None
    ) -> ClassificationResult:
        """
        Classify all pages in a document.
        
        Args:
            pages_ocr_data: List of OCR data for each page. Each page is a list of
                           dictionaries containing 'text', 'bounding_box', etc.
            progress_tracker: Optional progress tracker for UI updates.
        
        Returns:
            ClassificationResult containing page classifications and metadata.
        """
        logger.info("=" * 80)
        logger.info("🏷️ STEP 3: PAGE CLASSIFICATION SERVICE")
        logger.info("=" * 80)
        logger.info(f"📄 Pages to classify: {len(pages_ocr_data)}")
        
        start_time = time.time()
        
        try:
            # Update progress tracker
            if progress_tracker:
                progress_tracker.start_classification()
            
            # Perform batch classification
            page_classifications = self._classify_pages_batch(pages_ocr_data)
            
            if not page_classifications:
                logger.warning("⚠️ Batch classification failed, using simple fallback")
                page_classifications = self._simple_fallback_classification(pages_ocr_data)
            
            # Validate and normalize document types
            validated_classifications = self._validate_classifications(page_classifications)
            
            # Calculate summary statistics
            unique_types = set()
            continuation_count = 0
            for pc in validated_classifications:
                if not pc.is_continuation:
                    unique_types.add(pc.document_type)
                else:
                    continuation_count += 1
            
            processing_time = time.time() - start_time
            
            # Update progress tracker with primary document type and average confidence
            if progress_tracker:
                # Find most common document type
                primary_type = list(unique_types)[0] if unique_types else "Unknown"
                # Calculate average confidence
                avg_confidence = int(sum(pc.confidence for pc in validated_classifications) / len(validated_classifications)) if validated_classifications else 0
                progress_tracker.classification_complete(
                    doc_type=primary_type,
                    confidence=avg_confidence
                )
            
            # Log summary
            logger.info("")
            logger.info("=" * 80)
            logger.info("✅ CLASSIFICATION COMPLETE")
            logger.info("=" * 80)
            logger.info(f"   Total pages: {len(validated_classifications)}")
            logger.info(f"   Unique document types: {len(unique_types)}")
            logger.info(f"   Continuation pages: {continuation_count}")
            logger.info(f"   Document types found: {', '.join(sorted(unique_types))}")
            logger.info(f"   Processing time: {processing_time:.2f}s")
            
            return ClassificationResult(
                success=True,
                page_classifications=validated_classifications,
                processing_time=processing_time,
                unique_document_types=list(unique_types),
                continuation_count=continuation_count
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"❌ Classification failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            return ClassificationResult(
                success=False,
                error=str(e),
                processing_time=processing_time
            )
    
    def _classify_pages_batch(self, pages_ocr_data: List[List[Dict]]) -> List[PageClassification]:
        """
        Classify all pages using batch GPT-4 classification.
        
        Args:
            pages_ocr_data: List of OCR data for each page.
        
        Returns:
            List of PageClassification objects.
        """
        try:
            # Build compact page summaries for batch classification
            pages_summary = self._build_pages_summary(pages_ocr_data)
            total_pages = len(pages_summary)
            
            # Detect multi-document package characteristics
            package_info = self._analyze_package(pages_summary, total_pages)
            
            # Get available document types by category
            category_sections = self._build_category_sections()
            
            # Build classification prompt
            batch_prompt = self._build_classification_prompt(
                pages_summary, 
                category_sections, 
                package_info,
                total_pages
            )
            
            # Make API call
            logger.info(f"📤 Sending batch classification request for {len(pages_summary)} pages...")
            
            system_message = self._get_system_message()
            
            logger.info(f"📋 BATCH CLASSIFICATION REQUEST TO AZURE OPENAI:")
            logger.info(f"  🚀 Deployment/Engine: {deployment_name}")
            logger.info(f"  🔧 Temperature: 0.05")
            logger.info(f"  📊 Max Tokens: 3000")
            logger.info(f"  📄 User Prompt Length: {len(batch_prompt)} chars")
            
            response = openai.ChatCompletion.create(
                engine=deployment_name,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": batch_prompt}
                ],
                temperature=0.05,
                max_tokens=3000,
                seed=12345,
                top_p=0.1,
                frequency_penalty=0,
                presence_penalty=0,
                response_format={"type": "json_object"}
            )
            
            logger.info("✅ Azure OpenAI API call successful")
            response_text = response.choices[0].message.content.strip()
            
            # Clean and parse response
            response_text = self._clean_json_response(response_text)
            batch_result = json.loads(response_text)
            
            logger.info(f"📊 BATCH CLASSIFICATION RESPONSE:")
            logger.info(f"  📚 Total Pages Classified: {len(batch_result.get('pages', []))}")
            
            # Apply post-processing rules
            pages_data = self._apply_post_processing(
                batch_result, 
                pages_summary, 
                package_info,
                total_pages
            )
            
            # Build PageClassification objects
            return self._build_page_classifications(pages_data, pages_ocr_data)
            
        except Exception as e:
            logger.error(f"❌ Batch classification failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def _build_pages_summary(self, pages_ocr_data: List[List[Dict]]) -> List[Dict]:
        """Build compact page summaries for classification."""
        pages_summary = []
        for page_num, page_data in enumerate(pages_ocr_data, 1):
            page_text = "\n".join([text['text'] for text in page_data])
            
            if len(page_text.strip()) < 50:
                pages_summary.append({
                    'page': page_num,
                    'text': '[INSUFFICIENT TEXT]',
                    'chars': len(page_text)
                })
            else:
                # Keep more text for first 2 pages
                max_length = 2500 if page_num <= 2 else 1500
                truncated_text = page_text[:max_length] + "..." if len(page_text) > max_length else page_text
                pages_summary.append({
                    'page': page_num,
                    'text': truncated_text,
                    'chars': len(page_text)
                })
        
        return pages_summary
    
    def _analyze_package(self, pages_summary: List[Dict], total_pages: int) -> Dict:
        """Analyze document package characteristics."""
        first_page_text = pages_summary[0].get('text', '').lower() if pages_summary else ''
        
        # Covering Schedule indicators
        indicators = {
            'has_schedule_title': any(term in first_page_text[:400] for term in 
                ['covering schedule', 'document schedule', 'schedule of documents', 'list of documents', 'schedule']),
            'has_tabular_headers': any(term in first_page_text for term in 
                ['document type', 's.no', 's/n', 'serial no', 'sl.no', 'ref no', 'reference no', 'description', 'remarks']),
            'multiple_doc_refs': (
                first_page_text.count('invoice') > 2 or 
                first_page_text.count('bill of lading') > 1 or
                first_page_text.count('certificate') > 2 or
                first_page_text.count('lc') > 3 or
                first_page_text.count('l/c') > 3 or
                first_page_text.count('b/l') > 1 or
                first_page_text.count('packing list') > 1
            ),
            'has_list_structure': first_page_text.count('|') > 5 or first_page_text.count('\n') > 15,
            'has_lc_narrative': (
                'terms and conditions' in first_page_text or
                'we hereby issue' in first_page_text or
                'irrevocable' in first_page_text[:500] or
                'documentary credit' in first_page_text
            )
        }
        
        cs_indicator_score = sum([v for k, v in indicators.items() if k != 'has_lc_narrative'])
        has_lc_narrative = indicators['has_lc_narrative']
        
        # Multi-document package detection
        is_multi_doc_package = total_pages >= 6
        
        # Determine if Page 1 is likely a Covering Schedule
        if is_multi_doc_package and not has_lc_narrative:
            is_likely_covering_schedule = True
            if cs_indicator_score == 0:
                cs_indicator_score = 1
        elif total_pages >= 6 and cs_indicator_score >= 1:
            is_likely_covering_schedule = True
        else:
            is_likely_covering_schedule = cs_indicator_score >= 2
        
        logger.info(f"📊 Document Package Analysis:")
        logger.info(f"   Total pages: {total_pages}")
        logger.info(f"   Covering Schedule indicators: {cs_indicator_score}/4")
        logger.info(f"   - Schedule title: {indicators['has_schedule_title']}")
        logger.info(f"   - Tabular headers: {indicators['has_tabular_headers']}")
        logger.info(f"   - Multiple doc refs: {indicators['multiple_doc_refs']}")
        logger.info(f"   - List structure: {indicators['has_list_structure']}")
        logger.info(f"   - Has LC narrative: {has_lc_narrative}")
        logger.info(f"   📌 Multi-document package: {is_multi_doc_package}")
        
        return {
            'indicators': indicators,
            'cs_indicator_score': cs_indicator_score,
            'has_lc_narrative': has_lc_narrative,
            'is_multi_doc_package': is_multi_doc_package,
            'is_likely_covering_schedule': is_likely_covering_schedule
        }
    
    def _build_category_sections(self) -> str:
        """Build categorized document list for the prompt."""
        doc_types_by_category = {}
        for cat_id, cat_name in self.document_classifier.document_categories.items():
            doc_types_by_category[cat_name] = []
        
        for doc_id, mapping in self.document_classifier.entity_mappings.items():
            category_name = mapping.get('documentCategoryName', 'Other')
            document_name = mapping.get('documentName', doc_id)
            if category_name in doc_types_by_category:
                if document_name not in doc_types_by_category[category_name]:
                    doc_types_by_category[category_name].append(document_name)
        
        category_sections = []
        for category_name in sorted(doc_types_by_category.keys()):
            if doc_types_by_category[category_name]:
                category_sections.append(f"**{category_name}:**\n{', '.join(sorted(doc_types_by_category[category_name]))}")
        
        return "\n".join(category_sections)
    
    def _build_classification_prompt(
        self, 
        pages_summary: List[Dict], 
        category_sections: str,
        package_info: Dict,
        total_pages: int
    ) -> str:
        """Build the classification prompt for GPT-4."""
        
        is_multi_doc = package_info['is_multi_doc_package']
        cs_score = package_info['cs_indicator_score']
        
        prompt = f"""You are an expert document classifier for international trade and finance documents.

TASK: Classify ALL {len(pages_summary)} pages in this document package.

### Available Document Types by Business Process Category:

{category_sections}

### CRITICAL CLASSIFICATION RULES:

**DOCUMENT PACKAGE ANALYSIS:**
- Total Pages: {total_pages}
- Multi-Document Package: {'YES' if is_multi_doc else 'NO'}
- Covering Schedule Indicators on Page 1: {cs_score}/4

**COVERING SCHEDULE DETECTION:**

{'🎯 HIGH PRIORITY: This appears to be a MULTI-DOCUMENT PACKAGE (6+ pages). Page 1 is VERY LIKELY a Covering Schedule.' if is_multi_doc else '⚠️ This appears to be a SINGLE DOCUMENT (2-5 pages). DO NOT classify as Covering Schedule unless explicit title present.'}

**Document Type Rules:**
- **Letter of Credit**: Contains credit amount, expiry date, detailed terms and conditions
- **Covering Schedule**: Summary/index listing multiple documents, tabular format
- **Bill of Lading**: Transport document with "Bill of Lading" header
- **Commercial Invoice**: Itemized goods and prices with "Commercial Invoice" header
- **Packing List**: Details packaging, cartons, dimensions
- **Certificate of Origin**: Country declaration document

### PAGES TO CLASSIFY:

{json.dumps(pages_summary, indent=2)}

### CLASSIFICATION INSTRUCTIONS:

1. Look at EXPLICIT TITLE/HEADER first for each page
2. Check for document boundaries (new title, format change)
3. Mark continuation pages with is_continuation: true
4. Use confidence scores: 95-100 for clear titles, 70-85 for inferred

Respond in VALID JSON format ONLY (no markdown):
{{
  "package_analysis": {{
    "is_multi_document": true/false,
    "covering_schedule_likely": true/false,
    "reasoning": "Brief package-level analysis"
  }},
  "pages": [
    {{
      "page": 1,
      "document_type": "exact document name from list",
      "is_continuation": false,
      "confidence": 95,
      "reasoning": "Document title: [title]. Key indicators: [indicators]."
    }}
  ]
}}"""
        
        return prompt
    
    def _get_system_message(self) -> str:
        """Get the system message for classification."""
        return """You are an expert document classification system for international trade and finance documents. 

CRITICAL RULES:
1. SINGLE DOCUMENT: If 2-4 pages appear to be ONE document, mark continuation pages appropriately.
2. MULTI-DOCUMENT PACKAGE: If 5+ pages with multiple distinct documents, Page 1 is often a Covering Schedule.
3. ALWAYS prioritize explicit document titles over content similarity.
4. Continuation pages should maintain the same document_type as the page they continue."""
    
    def _clean_json_response(self, response_text: str) -> str:
        """Clean JSON response from GPT."""
        if response_text.startswith('```json'):
            response_text = response_text.replace('```json', '').replace('```', '')
        elif response_text.startswith('```'):
            response_text = response_text.replace('```', '')
        return response_text.strip()
    
    def _apply_post_processing(
        self,
        batch_result: Dict,
        pages_summary: List[Dict],
        package_info: Dict,
        total_pages: int
    ) -> List[Dict]:
        """Apply post-processing rules to classification results."""
        
        pages_data = batch_result.get('pages', [])
        is_multi_doc = package_info['is_multi_doc_package']
        cs_score = package_info['cs_indicator_score']
        has_lc_narrative = package_info['has_lc_narrative']
        
        # Extract package analysis
        pkg_analysis = batch_result.get('package_analysis', {})
        ai_thinks_multi_doc = pkg_analysis.get('is_multi_document', is_multi_doc)
        ai_thinks_cs = pkg_analysis.get('covering_schedule_likely', False)
        
        logger.info(f"🤖 AI Analysis:")
        logger.info(f"   Multi-document: {ai_thinks_multi_doc}")
        logger.info(f"   Covering Schedule likely: {ai_thinks_cs}")
        logger.info(f"   Reasoning: {pkg_analysis.get('reasoning', 'N/A')}")
        
        # Apply override logic for multi-document packages
        if len(pages_data) > 0 and total_pages >= 5:
            first_page = pages_data[0]
            
            # Count unique document types after page 1
            unique_types_after_p1 = set()
            for page_info in pages_data[1:]:
                doc_type = page_info.get('document_type', '')
                if doc_type not in ['Empty/Insufficient Text', 'Unknown', 'Covering Schedule']:
                    unique_types_after_p1.add(doc_type)
            
            # Check if we should override to Covering Schedule
            should_override_to_cs = (
                (is_multi_doc and not has_lc_narrative) or
                (cs_score >= 2 and is_multi_doc) or
                (total_pages >= 6 and len(unique_types_after_p1) >= 2) or
                (ai_thinks_cs and cs_score >= 1) or
                (total_pages >= 7) or
                (total_pages == 6 and cs_score >= 1)
            )
            
            if should_override_to_cs and first_page.get('document_type') != 'Covering Schedule':
                original_type = first_page.get('document_type')
                logger.warning(f"🔄 OVERRIDE APPLIED: {original_type} → Covering Schedule")
                logger.warning(f"   Reason: {total_pages} pages, {len(unique_types_after_p1)} unique doc types, {cs_score} indicators")
                
                first_page['document_type'] = 'Covering Schedule'
                first_page['confidence'] = 95
                first_page['reasoning'] = f"Multi-document package ({total_pages} pages). Page 1 is Covering Schedule."
                first_page['is_continuation'] = False
        
        # Remove LC classifications from multi-doc packages
        if is_multi_doc:
            for page_info in pages_data:
                if page_info.get('document_type') == 'Letter of Credit':
                    page_num = page_info.get('page', 0)
                    if page_num == 1:
                        logger.warning(f"🔄 PAGE {page_num}: Letter of Credit → Covering Schedule")
                        page_info['document_type'] = 'Covering Schedule'
                        page_info['is_continuation'] = False
                        page_info['confidence'] = 98
                        page_info['reasoning'] = f"Multi-document package never contains LC. Page 1 is Covering Schedule."
        
        return pages_data
    
    def _build_page_classifications(
        self, 
        pages_data: List[Dict], 
        pages_ocr_data: List[List[Dict]]
    ) -> List[PageClassification]:
        """Build PageClassification objects from classification results."""
        
        classifications = []
        
        for idx, page_info in enumerate(pages_data):
            page_num = page_info.get('page', idx + 1)
            document_type = page_info.get('document_type', 'Unknown')
            is_continuation = page_info.get('is_continuation', False)
            confidence = page_info.get('confidence', 80)
            reasoning = page_info.get('reasoning', '')
            
            # Get original page text and OCR data
            if page_num - 1 < len(pages_ocr_data):
                page_data = pages_ocr_data[page_num - 1]
                page_text = "\n".join([text['text'] for text in page_data])
            else:
                page_text = ""
                page_data = []
            
            # Apply continuation logic
            if is_continuation and len(classifications) > 0:
                prev_type = classifications[-1].document_type
                if prev_type not in ['Empty/Insufficient Text', 'Unknown']:
                    document_type = prev_type
                    confidence = max(confidence if confidence > 1 else confidence * 100, 75)
                    logger.info(f"  📄 Page {page_num}: CONTINUATION of {prev_type} ({confidence:.0f}%)")
            else:
                confidence = confidence if confidence > 1 else confidence * 100
                if document_type == 'Covering Schedule':
                    logger.info(f"  📋 Page {page_num}: {document_type} ({confidence:.0f}%) ⭐")
                elif page_num == 1:
                    logger.info(f"  📄 Page {page_num}: {document_type} ({confidence:.0f}%) [FIRST PAGE]")
                else:
                    logger.info(f"  📄 Page {page_num}: {document_type} ({confidence:.0f}%)")
            
            classifications.append(PageClassification(
                page=page_num,
                document_type=document_type,
                confidence=confidence,
                text=page_text,
                ocr_data=page_data,
                is_continuation=is_continuation,
                reasoning=reasoning
            ))
        
        return classifications
    
    def _simple_fallback_classification(
        self, 
        pages_ocr_data: List[List[Dict]]
    ) -> List[PageClassification]:
        """Simple fallback classification when batch fails."""
        
        classifications = []
        
        for page_num, page_data in enumerate(pages_ocr_data, 1):
            page_text = "\n".join([text['text'] for text in page_data])
            
            if len(page_text.strip()) < 50:
                classifications.append(PageClassification(
                    page=page_num,
                    document_type='Empty/Insufficient Text',
                    confidence=0,
                    text=page_text,
                    ocr_data=page_data,
                    is_continuation=False
                ))
            else:
                result = self.document_classifier.classify_document(page_text)
                classifications.append(PageClassification(
                    page=page_num,
                    document_type=result.get('document_type', 'Unknown'),
                    confidence=result.get('confidence', 0) * 100,
                    text=page_text,
                    ocr_data=page_data,
                    is_continuation=False
                ))
        
        return classifications
    
    def _validate_classifications(
        self, 
        classifications: List[PageClassification]
    ) -> List[PageClassification]:
        """Validate and normalize document types."""
        
        validated = []
        
        for pc in classifications:
            doc_type = pc.document_type
            
            # Apply alias normalization
            if doc_type in self.DOCUMENT_TYPE_ALIASES:
                original = doc_type
                doc_type = self.DOCUMENT_TYPE_ALIASES[doc_type]
                logger.info(f"  🔄 Normalized: '{original}' → '{doc_type}'")
            
            # Check if valid document type
            if doc_type not in self.valid_document_types:
                logger.warning(f"  ⚠️ Page {pc.page}: Unknown document type '{doc_type}'")
            
            validated.append(PageClassification(
                page=pc.page,
                document_type=doc_type,
                confidence=pc.confidence,
                text=pc.text,
                ocr_data=pc.ocr_data,
                is_continuation=pc.is_continuation,
                reasoning=pc.reasoning
            ))
        
        return validated
