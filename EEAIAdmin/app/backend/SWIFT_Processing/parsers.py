"""
SWIFT Parsers Module
====================

Functions to parse SWIFT messages and extract data.
"""

import re
import logging
from typing import Dict, Any, Optional, List

from .formatters import format_swift_date

logger = logging.getLogger(__name__)


def parse_swift_message_text(swift_text: str) -> Dict[str, Any]:
    """
    Parse SWIFT message from raw text.
    
    Extracts message type, reference number, and all fields from a raw SWIFT message.
    
    Args:
        swift_text: Raw SWIFT message text
        
    Returns:
        Dictionary containing parsed message data:
        - message_type: MT type (e.g., 'MT700')
        - reference_number: Document reference
        - fields: Dictionary of field tag -> value
        - raw_text: Original message text
    """
    parsed = {
        'message_type': None,
        'reference_number': None,
        'fields': {},
        'raw_text': swift_text
    }

    if not swift_text:
        return parsed

    # Extract message type
    mt_pattern = r'MT(\d{3})'
    mt_match = re.search(mt_pattern, swift_text)
    if mt_match:
        parsed['message_type'] = f"MT{mt_match.group(1)}"

    # Extract SWIFT fields (format: :20:reference or {4:tag:value})
    field_patterns = [
        r':(\d{2}[A-Z]?):(.*?)(?=:|$)',  # Standard format
        r'\{4:(\d{2}[A-Z]?):(.*?)\}'  # Block format
    ]

    for pattern in field_patterns:
        matches = re.finditer(pattern, swift_text, re.DOTALL)
        for match in matches:
            tag = match.group(1)
            value = match.group(2).strip()
            parsed['fields'][tag] = value

    # Extract reference number (field 20)
    if '20' in parsed['fields']:
        parsed['reference_number'] = parsed['fields']['20']

    return parsed


def parse_swift_message_for_ui(swift_message: str, lc_context: Optional[Dict] = None) -> Dict[str, str]:
    """
    Parse SWIFT message for Professional UI display.
    
    Extracts key fields from MT700 message for display in the user interface.
    
    Args:
        swift_message: SWIFT message text
        lc_context: Optional LC context data
        
    Returns:
        Dictionary of field tag -> value for UI display
    """
    if not swift_message:
        return {}

    try:
        # Basic SWIFT field parsing for MT700
        swift_fields = {}
        lines = swift_message.split('\n')

        for line in lines:
            line = line.strip()
            if line.startswith(':20:'):
                swift_fields['20'] = line[4:].strip()  # Reference
            elif line.startswith(':31C:'):
                swift_fields['31C'] = line[5:].strip()  # Issue Date
            elif line.startswith(':31D:'):
                swift_fields['31D'] = line[5:].strip()  # Expiry Date
            elif line.startswith(':32B:'):
                swift_fields['32B'] = line[5:].strip()  # Amount
            elif line.startswith(':44C:'):
                swift_fields['44C'] = line[5:].strip()  # Latest Shipment
            elif line.startswith(':44E:'):
                swift_fields['44E'] = line[5:].strip()  # Port of Loading
            elif line.startswith(':44F:'):
                swift_fields['44F'] = line[5:].strip()  # Port of Discharge
            elif line.startswith(':45A:'):
                swift_fields['45A'] = line[5:].strip()  # Goods Description
            elif line.startswith(':46A:'):
                swift_fields['46A'] = line[5:].strip()  # Documents Required
            elif line.startswith(':47A:'):
                swift_fields['47A'] = line[5:].strip()  # Additional Conditions
            elif line.startswith(':50:'):
                swift_fields['50'] = line[4:].strip()  # Applicant
            elif line.startswith(':59:'):
                swift_fields['59'] = line[4:].strip()  # Beneficiary
            elif line.startswith(':40A:'):
                swift_fields['40A'] = line[5:].strip()  # Form of DC
            elif line.startswith(':42C:'):
                swift_fields['42C'] = line[5:].strip()  # Payment Terms
            elif line.startswith(':43P:'):
                swift_fields['43P'] = line[5:].strip()  # Partial Shipment
            elif line.startswith(':43T:'):
                swift_fields['43T'] = line[5:].strip()  # Transhipment
            elif line.startswith(':51A:'):
                swift_fields['51A'] = line[5:].strip()  # Issuing Bank
            elif line.startswith(':57A:'):
                swift_fields['57A'] = line[5:].strip()  # Advising Bank
            elif line.startswith(':71B:'):
                swift_fields['71B'] = line[5:].strip()  # Charges

        return swift_fields

    except Exception as e:
        logger.error(f"Error parsing SWIFT message: {e}")
        return {}


def extract_beneficiary_from_swift(swift_message: str) -> str:
    """
    Extract beneficiary from SWIFT message text.
    
    Args:
        swift_message: SWIFT message text
        
    Returns:
        Beneficiary name/details or empty string
    """
    if not swift_message:
        return ''

    # Pattern for beneficiary field (59:)
    beneficiary_match = re.search(r':59:([^\n:]+)', swift_message, re.IGNORECASE)
    if beneficiary_match:
        return beneficiary_match.group(1).strip()

    # Alternative pattern
    beneficiary_match = re.search(r'BENEFICIARY[:\s]+([^\n]+)', swift_message, re.IGNORECASE)
    if beneficiary_match:
        return beneficiary_match.group(1).strip()

    return ''


def extract_applicant_from_swift(swift_message: str) -> str:
    """
    Extract applicant from SWIFT message text.
    
    Args:
        swift_message: SWIFT message text
        
    Returns:
        Applicant name/details or empty string
    """
    if not swift_message:
        return ''

    # Pattern for applicant field (50:)
    applicant_match = re.search(r':50:([^\n:]+)', swift_message, re.IGNORECASE)
    if applicant_match:
        return applicant_match.group(1).strip()

    # Alternative pattern
    applicant_match = re.search(r'APPLICANT[:\s]+([^\n]+)', swift_message, re.IGNORECASE)
    if applicant_match:
        return applicant_match.group(1).strip()

    return ''


def extract_currency_from_amount(amount_field: str) -> str:
    """
    Extract currency code from SWIFT amount field (32B).
    
    Args:
        amount_field: Amount field value (e.g., 'USD100000,00')
        
    Returns:
        3-letter currency code or 'USD' as default
    """
    if not amount_field:
        return 'USD'

    # Extract currency code (first 3 characters)
    currency_match = re.match(r'^([A-Z]{3})', amount_field)
    return currency_match.group(1) if currency_match else 'USD'


def extract_amount_value(amount_field: str) -> float:
    """
    Extract numeric amount from SWIFT amount field (32B).
    
    Args:
        amount_field: Amount field value (e.g., 'USD100000,00')
        
    Returns:
        Numeric amount as float
    """
    if not amount_field:
        return 0.0

    try:
        # Remove currency code and convert comma to decimal point
        amount_str = re.sub(r'^[A-Z]{3}', '', amount_field)
        amount_str = amount_str.replace(',', '.')
        return float(amount_str)
    except ValueError:
        logger.warning(f"Could not parse amount: {amount_field}")
        return 0.0


def extract_date_from_field(date_field: str) -> str:
    """
    Extract and format date from SWIFT date field.
    
    Args:
        date_field: Date field value (e.g., '240315LONDON')
        
    Returns:
        Formatted date (YYYY-MM-DD) or original value
    """
    return format_swift_date(date_field)


def extract_all_fields(swift_message: str) -> Dict[str, Any]:
    """
    Extract all fields from a SWIFT message comprehensively.
    
    Args:
        swift_message: Full SWIFT message text
        
    Returns:
        Dictionary with all extracted and processed fields
    """
    if not swift_message:
        return {}
    
    # Get basic parsed fields
    parsed = parse_swift_message_text(swift_message)
    
    # Build comprehensive field dictionary
    result = {
        'message_type': parsed.get('message_type'),
        'reference_number': parsed.get('reference_number'),
        'raw_fields': parsed.get('fields', {}),
    }
    
    # Extract commonly needed values
    fields = parsed.get('fields', {})
    
    # Amount and currency
    if '32B' in fields:
        result['currency'] = extract_currency_from_amount(fields['32B'])
        result['amount'] = extract_amount_value(fields['32B'])
    
    # Dates
    if '31C' in fields:
        result['issue_date'] = extract_date_from_field(fields['31C'])
    if '31D' in fields:
        result['expiry_date'] = extract_date_from_field(fields['31D'])
    if '44C' in fields:
        result['shipment_date'] = extract_date_from_field(fields['44C'])
    
    # Parties
    result['applicant'] = extract_applicant_from_swift(swift_message)
    result['beneficiary'] = extract_beneficiary_from_swift(swift_message)
    
    # Shipment details
    result['port_of_loading'] = fields.get('44E', '')
    result['port_of_discharge'] = fields.get('44F', '')
    result['place_of_taking'] = fields.get('44A', '')
    result['final_destination'] = fields.get('44B', '')
    
    # Goods and documents
    result['goods_description'] = fields.get('45A', '')
    result['documents_required'] = fields.get('46A', '')
    result['additional_conditions'] = fields.get('47A', '')
    
    # Shipment terms
    result['partial_shipment'] = fields.get('43P', '')
    result['transhipment'] = fields.get('43T', '')
    
    return result


def validate_swift_message(swift_message: str, message_type: str = 'MT700') -> Dict[str, Any]:
    """
    Validate a SWIFT message for required fields and format.
    
    Args:
        swift_message: SWIFT message text to validate
        message_type: Expected message type (default MT700)
        
    Returns:
        Dictionary with validation results:
        - is_valid: True if message passes validation
        - errors: List of validation errors
        - warnings: List of validation warnings
    """
    result = {
        'is_valid': True,
        'errors': [],
        'warnings': []
    }
    
    if not swift_message:
        result['is_valid'] = False
        result['errors'].append('Empty SWIFT message')
        return result
    
    parsed = parse_swift_message_text(swift_message)
    
    # Check message type
    if parsed['message_type'] != message_type:
        result['warnings'].append(f"Message type is {parsed['message_type']}, expected {message_type}")
    
    # Required fields for MT700
    if message_type == 'MT700':
        required_fields = ['20', '31C', '31D', '32B', '50', '59', '45A', '46A']
        
        for field in required_fields:
            if field not in parsed['fields'] or not parsed['fields'][field]:
                result['is_valid'] = False
                result['errors'].append(f"Missing required field: {field}")
    
    # Validate field formats
    fields = parsed.get('fields', {})
    
    # Validate date format (YYMMDD)
    date_fields = ['31C', '31D', '44C']
    for date_field in date_fields:
        if date_field in fields:
            if not re.match(r'^\d{6}', fields[date_field]):
                result['warnings'].append(f"Field {date_field} may have invalid date format")
    
    # Validate amount format (CCY + amount)
    if '32B' in fields:
        if not re.match(r'^[A-Z]{3}\d', fields['32B']):
            result['warnings'].append("Field 32B may have invalid currency/amount format")
    
    return result
