"""
Bounding Boxes Module
====================

This module contains all bounding box and coordinate mapping functionality
for document processing, including:

- FieldCoordinateMapper: Maps extracted field values to OCR coordinates
- Search utilities: Text search in OCR data with date/amount normalization
- Spatial utilities: Bounding box merging, distance calculation, etc.
- Refinement service: Word-level coordinate refinement
- Route handlers: API endpoints for coordinate operations

Author: EEAdmin Team
Version: 1.0.0
"""

import logging

# Configure module logger
logger = logging.getLogger(__name__)

# Import from submodules
from .coordinate_mapper import (
    FieldCoordinateMapper,
    coordinate_mapper
)

from .search_service import (
    normalize_date_for_search,
    normalize_amount_for_search,
    is_amount_field,
    is_date_in_valid_context,
    calculate_match_priority_score,
    search_text_in_ocr
)

from .spatial_utils import (
    fuzzy_match,
    strip_punctuation,
    merge_bboxes,
    get_bbox_center,
    calculate_distance,
    are_words_on_same_line,
    are_words_on_same_line_rotated,
    sort_words_left_to_right,
    sort_words_for_rotated_page,
    sort_words_reading_order,
    detect_page_rotation,
    is_standalone_punctuation,
    smart_sort_words
)

from .refinement_service import (
    find_all_candidates_for_line,
    find_best_spatial_cluster,
    score_cluster,
    fallback_rotated_page_search,
    fallback_fuzzy_search,
    fallback_expand_existing_match,
    split_long_line_smart,
    refine_coordinate_response,
    process_coordinate_response
)

# Define public API
__all__ = [
    # Coordinate Mapper
    'FieldCoordinateMapper',
    'coordinate_mapper',
    
    # Search Service
    'normalize_date_for_search',
    'normalize_amount_for_search',
    'is_amount_field',
    'is_date_in_valid_context',
    'calculate_match_priority_score',
    'search_text_in_ocr',
    
    # Spatial Utils
    'fuzzy_match',
    'strip_punctuation',
    'merge_bboxes',
    'get_bbox_center',
    'calculate_distance',
    'are_words_on_same_line',
    'are_words_on_same_line_rotated',
    'sort_words_left_to_right',
    'sort_words_for_rotated_page',
    'sort_words_reading_order',
    'detect_page_rotation',
    'is_standalone_punctuation',
    'smart_sort_words',
    
    # Refinement Service
    'find_all_candidates_for_line',
    'find_best_spatial_cluster',
    'score_cluster',
    'fallback_rotated_page_search',
    'fallback_fuzzy_search',
    'fallback_expand_existing_match',
    'split_long_line_smart',
    'refine_coordinate_response',
    'process_coordinate_response',
]


def register_bounding_box_routes(app):
    """
    Register bounding box related routes with the Flask app.
    
    Args:
        app: Flask application instance
    
    Returns:
        None
    """
    from .bounding_box_routes import register_routes
    register_routes(app)
    logger.info("✅ Bounding box routes registered successfully")
