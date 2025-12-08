"""
QR Code Parser Module

This module provides parsing functionality for QR code data:
- JSON parsing
- Structured text parsing (key-value pairs)
- LLM-based intelligent parsing
- Trade finance data validation and structuring
"""

import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def parse_structured_qr_text(qr_text):
    """
    Parse structured text QR codes (key-value pairs, etc.)
    
    Args:
        qr_text: Raw QR code text content
        
    Returns:
        dict: Parsed key-value data, or None if parsing fails
    """
    try:
        parsed_data = {}

        # Split by lines and parse key-value pairs
        lines = qr_text.strip().split('\n')

        for line in lines:
            line = line.strip()
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower().replace(' ', '_')
                value = value.strip()
                parsed_data[key] = value
            elif '=' in line:
                key, value = line.split('=', 1)
                key = key.strip().lower().replace(' ', '_')
                value = value.strip()
                parsed_data[key] = value

        return parsed_data if parsed_data else None

    except Exception as e:
        logger.error(f"Error parsing structured QR text: {e}")
        return None


def parse_qr_with_llm(qr_text):
    """
    Use LLM to intelligently parse QR code content for trade finance information
    
    Args:
        qr_text: Raw QR code text content
        
    Returns:
        dict: Parsed trade finance data, or None if parsing fails
    """
    try:
        # Try to import the analyze_document_with_gpt function
        try:
            from app.routes import analyze_document_with_gpt
        except ImportError:
            logger.warning("analyze_document_with_gpt not available, LLM parsing disabled")
            return None

        prompt = f"""
You are an AI assistant specialized in parsing trade finance information from QR codes. 
Parse the following QR code content and extract any trade finance related information.

QR Code Content:
{qr_text}

Extract and structure any of the following trade finance fields you can identify:
- LC Number/Reference
- Applicant information  
- Beneficiary information
- Issuing Bank
- Advising Bank
- Amount and Currency
- Issue Date
- Expiry Date
- Latest Shipment Date
- Port of Loading
- Port of Discharge
- Goods Description
- Incoterms
- Partial Shipment (allowed/not allowed)
- Transhipment (allowed/not allowed)
- Required Documents
- Additional Conditions

Return the extracted information as a JSON object with standardized field names.
If no trade finance information is found, return null.

Example format:
{{
    "lc_number": "LC123456",
    "applicant": "ABC Corp",
    "beneficiary": "XYZ Ltd",
    "amount": "100000.00",
    "currency": "USD",
    "issue_date": "2024-01-15",
    "expiry_date": "2024-06-15",
    "goods_description": "Electronic components"
}}
"""

        # Use the existing LLM processing function
        response = analyze_document_with_gpt(qr_text, 'qr_code', prompt)

        if response and 'structured_data' in response:
            return response['structured_data']

        return None

    except Exception as e:
        logger.error(f"Error parsing QR with LLM: {e}")
        return None


def validate_and_structure_qr_data(raw_data):
    """
    Validate and structure QR data for trade finance form
    
    Args:
        raw_data: Raw parsed data from QR code
        
    Returns:
        dict: Structured trade finance data with confidence score
    """
    try:
        # Standard field mappings for trade finance
        field_mappings = {
            'lc_number': ['lc_number', 'lcnumber', 'lc_ref', 'reference', 'letter_of_credit_number'],
            'applicant': ['applicant', 'applicant_name', 'buyer', 'importer'],
            'beneficiary': ['beneficiary', 'beneficiary_name', 'seller', 'exporter'],
            'issuing_bank': ['issuing_bank', 'issuingbank', 'opening_bank'],
            'advising_bank': ['advising_bank', 'advisingbank', 'nominated_bank'],
            'amount': ['amount', 'lc_amount', 'value', 'total_amount'],
            'currency': ['currency', 'ccy', 'curr'],
            'issue_date': ['issue_date', 'issuedate', 'opening_date', 'date_of_issue'],
            'expiry_date': ['expiry_date', 'expirydate', 'expiration_date', 'maturity_date'],
            'latest_shipment_date': ['latest_shipment_date', 'shipment_date', 'shipping_date'],
            'port_of_loading': ['port_of_loading', 'loading_port', 'shipment_port'],
            'port_of_discharge': ['port_of_discharge', 'discharge_port', 'destination_port'],
            'goods_description': ['goods_description', 'description', 'commodity', 'merchandise'],
            'incoterms': ['incoterms', 'terms', 'trade_terms'],
            'partial_shipment': ['partial_shipment', 'partial_shipments'],
            'transhipment': ['transhipment', 'transshipment']
        }

        structured_data = {'trade_finance_fields': {}}
        confidence_score = 0.0
        total_fields = len(field_mappings)
        matched_fields = 0

        # Normalize the raw data keys
        normalized_raw = {}
        if isinstance(raw_data, dict):
            for key, value in raw_data.items():
                normalized_key = str(key).lower().replace(' ', '_').replace('-', '_')
                normalized_raw[normalized_key] = value

        # Map fields using the mappings
        for standard_field, possible_keys in field_mappings.items():
            field_value = None

            for possible_key in possible_keys:
                if possible_key in normalized_raw:
                    field_value = normalized_raw[possible_key]
                    matched_fields += 1
                    break

            if field_value:
                structured_data['trade_finance_fields'][standard_field] = field_value

        # Calculate confidence based on matched fields
        if total_fields > 0:
            confidence_score = matched_fields / total_fields

        # Additional validation and formatting
        structured_data['confidence'] = confidence_score
        structured_data['fields_matched'] = matched_fields
        structured_data['total_possible_fields'] = total_fields
        structured_data['parsing_timestamp'] = datetime.now().isoformat()

        return structured_data

    except Exception as e:
        logger.error(f"Error validating QR data: {e}")
        return {
            'trade_finance_fields': {},
            'confidence': 0.0,
            'error': str(e)
        }
