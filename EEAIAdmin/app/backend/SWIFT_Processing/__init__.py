"""
SWIFT Processing Module
=======================

This module handles all SWIFT message generation, parsing, and processing
for MT700 (Letter of Credit Issuance) and related message types.

Components:
-----------
- constants: SWIFT field definitions, MT message types, validation rules
- formatters: Functions to format data for SWIFT fields
- parsers: Functions to parse SWIFT messages
- mt700_generator: MT700 message generation
- swift_routes: Flask routes for SWIFT operations

Usage:
------
    from app.backend.SWIFT_Processing import (
        generate_mt700_message,
        parse_swift_message_text,
        parse_swift_message_for_ui,
        format_swift_date,
        format_address_field,
        format_bank_field,
        extract_beneficiary_from_swift,
        extract_applicant_from_swift,
        register_swift_routes
    )
"""

# Import constants
from .constants import (
    MT_MESSAGE_TYPES,
    MT700_FIELD_DEFINITIONS,
    SWIFT_DATE_FORMAT,
    SWIFT_CURRENCY_CODES,
    SWIFT_FIELD_LIMITS,
    DEFAULT_SWIFT_CONFIG
)

# Import formatters
from .formatters import (
    format_swift_date,
    format_address_field,
    format_bank_field
)

# Import parsers
from .parsers import (
    parse_swift_message_text,
    parse_swift_message_for_ui,
    extract_beneficiary_from_swift,
    extract_applicant_from_swift,
    extract_currency_from_amount
)

# Import MT700 generator
from .mt700_generator import generate_mt700_message

# Import route registration
from .swift_routes import register_swift_routes

__all__ = [
    # Constants
    'MT_MESSAGE_TYPES',
    'MT700_FIELD_DEFINITIONS',
    'SWIFT_DATE_FORMAT',
    'SWIFT_CURRENCY_CODES',
    'SWIFT_FIELD_LIMITS',
    'DEFAULT_SWIFT_CONFIG',
    # Formatters
    'format_swift_date',
    'format_address_field',
    'format_bank_field',
    # Parsers
    'parse_swift_message_text',
    'parse_swift_message_for_ui',
    'extract_beneficiary_from_swift',
    'extract_applicant_from_swift',
    'extract_currency_from_amount',
    # Generator
    'generate_mt700_message',
    # Routes
    'register_swift_routes'
]

__version__ = '1.0.0'
__author__ = 'EEAIAdmin'
