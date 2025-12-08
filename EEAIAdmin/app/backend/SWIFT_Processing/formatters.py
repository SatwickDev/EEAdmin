"""
SWIFT Formatters Module
=======================

Functions to format data for SWIFT message fields.
"""

import re
import logging
from datetime import datetime
from typing import Optional

from .constants import (
    SWIFT_DATE_FORMAT,
    SWIFT_FIELD_LIMITS
)

logger = logging.getLogger(__name__)


def format_swift_date(swift_date: str) -> str:
    """
    Format SWIFT date (YYMMDD or YYMMDDCITY) to readable format.
    
    Args:
        swift_date: Date string in SWIFT format (YYMMDD)
        
    Returns:
        Formatted date string (YYYY-MM-DD)
    """
    if not swift_date:
        return ''

    try:
        # Extract date part (first 6 digits)
        date_match = re.match(r'^(\d{6})', swift_date)
        if date_match:
            date_str = date_match.group(1)
            # Convert YYMMDD to YYYY-MM-DD
            year = int('20' + date_str[:2])
            month = int(date_str[2:4])
            day = int(date_str[4:6])
            return f"{year:04d}-{month:02d}-{day:02d}"
    except Exception as e:
        logger.warning(f"Failed to parse SWIFT date '{swift_date}': {e}")

    return swift_date


def format_date_to_swift(date_str: str, date_format: str = '%Y-%m-%d') -> str:
    """
    Format a date string to SWIFT format (YYMMDD).
    
    Args:
        date_str: Date string in the specified format
        date_format: The format of the input date string
        
    Returns:
        Date in SWIFT format (YYMMDD)
    """
    if not date_str:
        return ''
    
    try:
        date_obj = datetime.strptime(date_str, date_format)
        return date_obj.strftime(SWIFT_DATE_FORMAT)
    except ValueError as e:
        logger.warning(f"Failed to format date '{date_str}' to SWIFT format: {e}")
        return date_str


def format_address_field(address_text: str) -> str:
    """
    Format address for SWIFT field (max 4 lines of 35 chars each).
    
    SWIFT standard allows up to 4 lines of 35 characters for address fields.
    
    Args:
        address_text: Raw address text
        
    Returns:
        Formatted address string with proper line breaks
    """
    if not address_text:
        return ""

    max_line_length = SWIFT_FIELD_LIMITS['address_line']
    max_lines = SWIFT_FIELD_LIMITS['address_lines']
    
    # Split into lines and limit to 35 chars per line, max 4 lines
    lines = []
    words = address_text.split()
    current_line = ""

    for word in words:
        if len(current_line + " " + word) <= max_line_length:
            current_line = current_line + " " + word if current_line else word
        else:
            if current_line:
                lines.append(current_line)
            if len(lines) >= max_lines:
                break
            current_line = word[:max_line_length]  # Truncate long words

    if current_line and len(lines) < max_lines:
        lines.append(current_line)

    return "\n".join(lines[:max_lines])


def format_bank_field(bank_text: str) -> str:
    """
    Format bank information for SWIFT field.
    
    Extracts and returns SWIFT/BIC code if present, otherwise formats as address.
    
    Args:
        bank_text: Bank name or SWIFT code
        
    Returns:
        Formatted bank field (SWIFT code or address)
    """
    if not bank_text:
        return ""

    # Extract SWIFT code if present (8 or 11 characters)
    # Format: 4 letters (bank) + 2 letters (country) + 2 alphanumeric (location) + optional 3 alphanumeric (branch)
    swift_code_match = re.search(r'[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?', bank_text.upper())

    if swift_code_match:
        swift_code = swift_code_match.group(0)
        # Format as SWIFT code only for field 51A/57A
        return swift_code
    else:
        # Return formatted bank name
        return format_address_field(bank_text)


def format_amount_field(currency: str, amount: float) -> str:
    """
    Format currency and amount for SWIFT field 32B.
    
    Args:
        currency: 3-letter currency code (e.g., 'USD')
        amount: Numeric amount
        
    Returns:
        Formatted amount string (e.g., 'USD100000,00')
    """
    if not currency or amount is None:
        return ""
    
    # Convert to float if string
    if isinstance(amount, str):
        try:
            amount = float(amount.replace(',', ''))
        except ValueError:
            logger.warning(f"Invalid amount format: {amount}")
            return ""
    
    # Format with comma as decimal separator (SWIFT standard)
    amount_str = "{:.2f}".format(amount).replace('.', ',')
    
    return f"{currency.upper()}{amount_str}"


def format_multiline_field(text: str, max_length: int, line_length: int = 65) -> str:
    """
    Format text for multiline SWIFT fields (45A, 46A, 47A, etc.).
    
    Args:
        text: Raw text content
        max_length: Maximum total characters allowed
        line_length: Characters per line (default 65 for most fields)
        
    Returns:
        Formatted multiline text
    """
    if not text:
        return ""
    
    # Truncate to max length
    text = text[:max_length]
    
    # Split into lines of appropriate length
    lines = []
    current_line = ""
    
    for word in text.split():
        if len(current_line + " " + word) <= line_length:
            current_line = current_line + " " + word if current_line else word
        else:
            if current_line:
                lines.append(current_line)
            current_line = word[:line_length]
    
    if current_line:
        lines.append(current_line)
    
    return "\n".join(lines)


def format_reference_number(reference: str) -> str:
    """
    Format reference number for SWIFT field 20.
    
    Args:
        reference: LC or document reference number
        
    Returns:
        Formatted reference (max 16 characters, uppercase)
    """
    if not reference:
        return ""
    
    max_length = SWIFT_FIELD_LIMITS['reference_number']
    
    # Remove invalid characters and convert to uppercase
    clean_ref = re.sub(r'[^A-Za-z0-9/-]', '', reference)
    return clean_ref.upper()[:max_length]


def format_goods_description(description: str) -> str:
    """
    Format goods description for SWIFT field 45A.
    
    Args:
        description: Raw goods description
        
    Returns:
        Formatted goods description (max 1000 chars for preview)
    """
    if not description:
        return 'GOODS DESCRIPTION NOT PROVIDED'
    
    max_length = SWIFT_FIELD_LIMITS['goods_description']
    return format_multiline_field(description, max_length)


def format_documents_required(documents: list, additional_text: str = '') -> str:
    """
    Format documents required for SWIFT field 46A.
    
    Args:
        documents: List of document types
        additional_text: Additional document requirements text
        
    Returns:
        Formatted documents required string
    """
    documents_text = "DOCUMENTS REQUIRED:\n"
    
    if documents:
        for doc in documents:
            # Convert snake_case to Title Case
            formatted_doc = doc.replace('_', ' ').title()
            documents_text += f"- {formatted_doc}\n"
    
    if additional_text:
        documents_text += additional_text
    
    max_length = SWIFT_FIELD_LIMITS['documents_required']
    return documents_text[:max_length]


def validate_swift_code(swift_code: str) -> bool:
    """
    Validate a SWIFT/BIC code format.
    
    Args:
        swift_code: SWIFT/BIC code to validate
        
    Returns:
        True if valid format, False otherwise
    """
    if not swift_code:
        return False
    
    # SWIFT code is 8 or 11 characters
    # Format: BBBB CC LL (XXX)
    pattern = r'^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$'
    return bool(re.match(pattern, swift_code.upper()))
