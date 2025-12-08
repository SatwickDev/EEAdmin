"""
Required Documents Module
========================

This module handles parsing and processing of required documents from 
Letter of Credit (LC) and other trade finance documents.

Components:
- RequiredDocumentsParser: LLM-based parser for extracting document requirements
- parse_required_documents_simple: Simple text-based parsing for SWIFT field 46A
- register_required_documents_routes: Route registration function
"""

from .required_documents_parser import (
    RequiredDocumentsParser,
    parse_required_documents_from_text,
    parse_required_documents_simple
)
from .required_documents_routes import register_required_documents_routes

__all__ = [
    'RequiredDocumentsParser',
    'parse_required_documents_from_text',
    'parse_required_documents_simple',
    'register_required_documents_routes'
]
