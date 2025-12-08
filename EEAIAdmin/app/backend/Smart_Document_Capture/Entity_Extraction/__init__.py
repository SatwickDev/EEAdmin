"""
Step 6: Entity Extraction Module
================================

This module handles extraction of structured fields/entities from OCR text
using LLM-based processing with support for:
- Chunk-based parallel extraction for large field sets
- Field filtering by type (mandatory/optional/conditional)
- Field mapping loading from document_entities
- Integration with DocumentClassifier for prompt building

Components:
-----------
- extraction_service: Core extraction logic with chunk-based processing
- field_filter: Field filtering by type (mandatory always, optional/conditional if populated)
- field_mappings: Document field mapping loader for prompt enhancement
- extraction_routes: Flask route handlers for extraction endpoints

Usage:
------
    from app.backend.Smart_Document_Capture.Entity_Extraction import (
        extract_entities_in_chunks,
        extract_entities_parallel,
        filter_extracted_fields_by_type,
        load_document_field_mappings,
        process_page_with_llm_analysis
    )
"""

from .extraction_service import (
    extract_entities_in_chunks,
    extract_entities_parallel
)

from .field_filter import (
    filter_extracted_fields_by_type
)

from .field_mappings import (
    load_document_field_mappings
)

from .page_processor import (
    process_page_with_llm_analysis
)

__all__ = [
    # Core extraction functions
    'extract_entities_in_chunks',
    'extract_entities_parallel',
    
    # Field filtering
    'filter_extracted_fields_by_type',
    
    # Field mappings
    'load_document_field_mappings',
    
    # Page processing
    'process_page_with_llm_analysis'
]
