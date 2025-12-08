"""
Smart Document Capture Using QR

This module provides QR code processing functionality for trade finance documents.
It includes:
- QR code detection from images, PDFs, and Word documents
- Multi-fallback detection using OpenCV, Azure Vision, OpenAI Vision, and pattern analysis
- QR data parsing (JSON, structured text, LLM-based)
- Trade finance data validation and structuring
- QR code generation
"""

from .qr_service import QRService
from .qr_detector import (
    detect_qr_with_multi_fallback,
    detect_qr_with_azure,
    detect_qr_with_openai,
    detect_qr_with_patterns,
    analyze_text_for_qr_patterns,
    looks_like_trade_finance_data
)
from .qr_extractor import (
    extract_qr_from_pdf,
    extract_qr_from_word,
    extract_qr_from_image
)
from .qr_parser import (
    parse_structured_qr_text,
    parse_qr_with_llm,
    validate_and_structure_qr_data
)

__all__ = [
    'QRService',
    'detect_qr_with_multi_fallback',
    'detect_qr_with_azure',
    'detect_qr_with_openai',
    'detect_qr_with_patterns',
    'analyze_text_for_qr_patterns',
    'looks_like_trade_finance_data',
    'extract_qr_from_pdf',
    'extract_qr_from_word',
    'extract_qr_from_image',
    'parse_structured_qr_text',
    'parse_qr_with_llm',
    'validate_and_structure_qr_data'
]
