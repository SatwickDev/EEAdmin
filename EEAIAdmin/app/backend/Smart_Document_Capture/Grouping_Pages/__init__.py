"""
Step 5: Page Grouping Module

This module provides functionality for grouping classified pages by document type,
handling continuation pages, and generating page range strings.

Exports:
    - PageGroupingService: Main service class for page grouping
    - GroupingResult: Data class for grouping results
    - DocumentGroup: Data class for a single document group
    - group_pages_by_document_type: Function to group pages
    - generate_page_range: Function to generate page range strings
"""

from .grouping_service import (
    PageGroupingService,
    GroupingResult,
    DocumentGroup,
    group_pages_by_document_type,
    generate_page_range,
    merge_continuation_page
)

__all__ = [
    'PageGroupingService',
    'GroupingResult',
    'DocumentGroup',
    'group_pages_by_document_type',
    'generate_page_range',
    'merge_continuation_page'
]
