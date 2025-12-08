# AI Document Processor Backend Module
# Contains all processing steps for document analysis pipeline

from .Quality_Analysis import QualityAnalysisService
from .Document_Validation import (
    DocumentValidationService,
    ValidationResult,
    validate_document_types,
    filter_duplicate_documents,
    get_document_type_aliases,
    get_valid_document_types
)
from .Grouping_Pages import (
    PageGroupingService,
    GroupingResult,
    DocumentGroup,
    group_pages_by_document_type,
    generate_page_range
)
from .Bounding_Boxes import (
    # Coordinate Mapper
    FieldCoordinateMapper,
    coordinate_mapper,
    # Search Service
    normalize_date_for_search,
    normalize_amount_for_search,
    is_amount_field,
    is_date_in_valid_context,
    calculate_match_priority_score,
    search_text_in_ocr,
    # Spatial Utils
    fuzzy_match,
    strip_punctuation,
    merge_bboxes,
    get_bbox_center,
    calculate_distance,
    are_words_on_same_line,
    sort_words_reading_order,
    detect_page_rotation,
    # Refinement Service
    refine_coordinate_response,
    process_coordinate_response,
    # Route Registration
    register_bounding_box_routes
)
from .Entity_Extraction import (
    # Extraction Service
    extract_entities_in_chunks,
    extract_entities_parallel,
    # Field Filter
    filter_extracted_fields_by_type,
    # Field Mappings
    load_document_field_mappings,
    # Page Processor
    process_page_with_llm_analysis
)

__all__ = [
    # Step 1 - Quality Analysis
    'QualityAnalysisService',
    # Step 4 - Document Validation
    'DocumentValidationService',
    'ValidationResult',
    'validate_document_types',
    'filter_duplicate_documents',
    'get_document_type_aliases',
    'get_valid_document_types',
    # Step 5 - Page Grouping
    'PageGroupingService',
    'GroupingResult',
    'DocumentGroup',
    'group_pages_by_document_type',
    'generate_page_range',
    # Bounding Boxes - Coordinate Mapper
    'FieldCoordinateMapper',
    'coordinate_mapper',
    # Bounding Boxes - Search Service
    'normalize_date_for_search',
    'normalize_amount_for_search',
    'is_amount_field',
    'is_date_in_valid_context',
    'calculate_match_priority_score',
    'search_text_in_ocr',
    # Bounding Boxes - Spatial Utils
    'fuzzy_match',
    'strip_punctuation',
    'merge_bboxes',
    'get_bbox_center',
    'calculate_distance',
    'are_words_on_same_line',
    'sort_words_reading_order',
    'detect_page_rotation',
    # Bounding Boxes - Refinement Service
    'refine_coordinate_response',
    'process_coordinate_response',
    # Bounding Boxes - Route Registration
    'register_bounding_box_routes',
    # Step 6 - Entity Extraction
    'extract_entities_in_chunks',
    'extract_entities_parallel',
    'filter_extracted_fields_by_type',
    'load_document_field_mappings',
    'process_page_with_llm_analysis'
]
