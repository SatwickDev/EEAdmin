"""
Step 4: Document Validation Module

This module provides document type validation against predefined lists,
alias mapping, and duplicate filtering functionality.

Exports:
    - DocumentValidationService: Main service class for validation
    - ValidationResult: Data class for validation results
    - validate_document_types: Function to validate document types
    - filter_duplicate_documents: Function to filter duplicate document types
"""

from .validation_service import (
    DocumentValidationService,
    ValidationResult,
    validate_document_types,
    filter_duplicate_documents,
    get_document_type_aliases,
    get_valid_document_types
)

__all__ = [
    'DocumentValidationService',
    'ValidationResult',
    'validate_document_types',
    'filter_duplicate_documents',
    'get_document_type_aliases',
    'get_valid_document_types'
]
