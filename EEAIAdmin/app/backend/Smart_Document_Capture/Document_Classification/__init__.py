"""
Step 3: Page Classification Service

This module provides document classification functionality for the AI Document Processing pipeline.
It classifies each page of a document into predefined document types using Azure OpenAI.

Key Features:
- Batch page classification using GPT-4
- Multi-document package detection (Covering Schedule logic)
- Document type validation against predefined list
- Continuation page detection
- Document type alias normalization

Usage:
    from app.backend.AI_Document_Processor.Document_Classification import (
        ClassificationService,
        ClassificationResult,
        PageClassification
    )
    
    # Initialize service
    classifier = ClassificationService()
    
    # Classify pages
    result = classifier.classify(
        pages_ocr_data=pages_ocr_data,
        progress_tracker=progress_tracker
    )
    
    if result.success:
        for page_class in result.page_classifications:
            print(f"Page {page_class.page}: {page_class.document_type} ({page_class.confidence}%)")
"""

from .classification_service import (
    ClassificationService,
    ClassificationResult,
    PageClassification
)
from .document_classifier import (
    DocumentClassifier,
    reload_all_document_classifier_instances
)

__all__ = [
    'ClassificationService',
    'ClassificationResult',
    'PageClassification',
    'DocumentClassifier',
    'reload_all_document_classifier_instances'
]
