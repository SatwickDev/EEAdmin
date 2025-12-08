"""
MT700 Generator Module
======================

Generates SWIFT MT700 (Issue of a Documentary Credit) messages.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

from .constants import (
    SWIFT_FIELD_LIMITS,
    DEFAULT_SWIFT_CONFIG,
    LC_TYPE_MAPPING,
    PAYMENT_TERMS_MAPPING,
    CHARGES_OPTIONS
)
from .formatters import (
    format_address_field,
    format_bank_field,
    format_date_to_swift
)

logger = logging.getLogger(__name__)


def generate_mt700_message(lc_data: Dict[str, Any]) -> str:
    """
    Generate SWIFT MT700 message from LC data.
    
    Creates a complete MT700 (Issue of a Documentary Credit) message
    following SWIFT standards.
    
    Args:
        lc_data: Dictionary containing LC details:
            - lcNumber: Documentary credit number
            - lcType: Type of LC (irrevocable, etc.)
            - issueDate: Date of issue (YYYY-MM-DD)
            - expiryDate: Expiry date (YYYY-MM-DD)
            - applicant: Applicant name
            - applicantAddress: Applicant address (optional)
            - beneficiary: Beneficiary name
            - beneficiaryAccountNumber: Beneficiary account (optional)
            - issuingBank: Issuing bank name/SWIFT code
            - advisingBank: Advising bank name/SWIFT code (optional)
            - currency: Currency code (USD, EUR, etc.)
            - amount: Credit amount
            - tolerancePercent: Amount tolerance percentage (optional)
            - paymentTerms: Payment terms
            - latestShipmentDate: Latest shipment date (YYYY-MM-DD)
            - portOfLoading: Port of loading (optional)
            - portOfDischarge: Port of discharge (optional)
            - placeOfTaking: Place of taking in charge (optional)
            - finalDestination: Final destination (optional)
            - partialShipment: allowed/not allowed
            - transhipment: allowed/not allowed
            - goodsDescription: Description of goods
            - documents: List of required documents
            - documentsRequired: Additional documents text (optional)
            - additionalConditions: Additional conditions (optional)
            - charges: Charge allocation (beneficiary/applicant)
            
    Returns:
        Complete MT700 message as formatted string
    """
    try:
        # Format currency and amount for SWIFT
        currency = lc_data.get('currency', 'USD')
        # Convert amount to float for formatting
        amount_value = float(lc_data['amount']) if isinstance(lc_data['amount'], str) else lc_data['amount']
        amount = "{:.2f}".format(amount_value).replace('.', ',')

        # Format dates for SWIFT (YYMMDD)
        issue_date = format_date_to_swift(lc_data['issueDate'])
        expiry_date = format_date_to_swift(lc_data['expiryDate'])
        shipment_date = format_date_to_swift(lc_data.get('latestShipmentDate', ''))

        # Build SWIFT MT700 message
        swift_lines = [
            "{1:F01" + DEFAULT_SWIFT_CONFIG['sender_bic'] + DEFAULT_SWIFT_CONFIG['sender_reference'] + "}",
            "{2:I700" + DEFAULT_SWIFT_CONFIG['receiver_bic'] + DEFAULT_SWIFT_CONFIG['message_priority'] + "}",
            "{3:{108:MT700}}",
            "{4:",
            ":20:" + lc_data['lcNumber'],  # Documentary Credit Number
            ":23:" + _format_lc_type(lc_data.get('lcType', 'irrevocable')),
            ":27:" + lc_data.get('sequenceOfTotal', '1/1'),  # Sequence of Total
            ":31C:" + issue_date,  # Date of Issue
            ":40A:IRREVOCABLE",  # Form of Documentary Credit
            # Place of Expiry
            _format_expiry_field(expiry_date, lc_data),
            # Applicant (Field 50)
            _format_applicant_field(lc_data),
            # Beneficiary (Field 59)
            ":59:" + format_address_field(lc_data['beneficiary']),
        ]

        # Beneficiary Account Number (if present)
        if lc_data.get('beneficiaryAccountNumber'):
            swift_lines.append(":59A:" + lc_data['beneficiaryAccountNumber'])

        # Currency Code, Amount (Field 32B)
        swift_lines.append(":32B:" + currency + amount)

        # Payment Terms (if present)
        payment_terms_field = _format_payment_terms(lc_data.get('paymentTerms'))
        if payment_terms_field:
            swift_lines.append(payment_terms_field)

        # Confirmation Party Details (if present)
        if lc_data.get('confirmationPartyDetails'):
            swift_lines.append(":71D:" + lc_data['confirmationPartyDetails'])

        # Add issuing bank
        if lc_data.get('issuingBank'):
            swift_lines.append(":51A:" + format_bank_field(lc_data['issuingBank']))

        # Add advising bank if present
        if lc_data.get('advisingBank'):
            swift_lines.append(":57A:" + format_bank_field(lc_data['advisingBank']))

        # Add tolerance percentage
        if lc_data.get('tolerancePercent'):
            swift_lines.append(":39A:" + str(lc_data['tolerancePercent']))

        # Add drawee
        if lc_data.get('drawee'):
            swift_lines.append(":42A:" + format_bank_field(lc_data['drawee']))

        # Add shipment details
        if shipment_date:
            swift_lines.append(":44C:" + shipment_date)

        if lc_data.get('portOfLoading'):
            swift_lines.append(":44E:" + lc_data['portOfLoading'].upper())

        if lc_data.get('portOfDischarge'):
            swift_lines.append(":44F:" + lc_data['portOfDischarge'].upper())

        if lc_data.get('placeOfTaking'):
            swift_lines.append(":44A:" + lc_data['placeOfTaking'].upper())

        if lc_data.get('finalDestination'):
            swift_lines.append(":44B:" + lc_data['finalDestination'].upper())

        # Add partial shipment and transhipment
        swift_lines.append(":43P:" + ("ALLOWED" if lc_data.get('partialShipment') == 'allowed' else "NOT ALLOWED"))
        swift_lines.append(":43T:" + ("ALLOWED" if lc_data.get('transhipment') == 'allowed' else "NOT ALLOWED"))

        # Add description of goods
        goods_desc = lc_data.get('goodsDescription', 'GOODS DESCRIPTION NOT PROVIDED')
        max_goods_length = SWIFT_FIELD_LIMITS['goods_description']
        swift_lines.append(":45A:" + goods_desc[:max_goods_length])

        # Add documents required
        documents_text = _format_documents_required(lc_data)
        max_docs_length = SWIFT_FIELD_LIMITS['documents_required']
        swift_lines.append(":46A:" + documents_text[:max_docs_length])

        # Add additional conditions
        if lc_data.get('additionalConditions'):
            max_conditions_length = SWIFT_FIELD_LIMITS['additional_conditions']
            swift_lines.append(":47A:" + lc_data['additionalConditions'][:max_conditions_length])

        # Add period for presentation
        if lc_data.get('periodForPresentation'):
            swift_lines.append(":48:" + lc_data['periodForPresentation'])

        # Add confirmation instructions
        if lc_data.get('confirmationInstructions'):
            swift_lines.append(":49:" + lc_data['confirmationInstructions'].upper())

        # Add charges
        charges_text = _format_charges(lc_data.get('charges', 'beneficiary'))
        swift_lines.append(":71B:" + charges_text)

        # Add instructions to bank
        if lc_data.get('instructionsToBank'):
            max_instructions_length = SWIFT_FIELD_LIMITS['instructions_to_bank']
            swift_lines.append(":78:" + lc_data['instructionsToBank'][:max_instructions_length])

        # Add sender to receiver information
        if lc_data.get('senderToReceiver'):
            max_str_length = SWIFT_FIELD_LIMITS['sender_to_receiver']
            swift_lines.append(":72:" + lc_data['senderToReceiver'][:max_str_length])

        swift_lines.append("-}")

        # Filter out None values
        swift_lines = [line for line in swift_lines if line is not None]

        return "\n".join(swift_lines)

    except Exception as e:
        logger.error(f"Error generating MT700 message: {e}")
        raise ValueError(f"Failed to generate MT700 message: {str(e)}")


def _format_lc_type(lc_type: str) -> str:
    """Format LC type for SWIFT field 23."""
    return LC_TYPE_MAPPING.get(lc_type.lower(), lc_type.upper())


def _format_expiry_field(expiry_date: str, lc_data: Dict[str, Any]) -> str:
    """Format expiry date and place for SWIFT field 31D."""
    place_of_expiry = lc_data.get('placeOfExpiry', '')
    if not place_of_expiry:
        place_of_expiry = lc_data.get('finalDestination', DEFAULT_SWIFT_CONFIG['default_place_of_expiry'])
    
    return ":31D:" + expiry_date + " " + place_of_expiry.upper()


def _format_applicant_field(lc_data: Dict[str, Any]) -> str:
    """Format applicant field for SWIFT field 50."""
    applicant_name = format_address_field(lc_data.get('applicant', ''))
    applicant_address = format_address_field(lc_data.get('applicantAddress', ''))
    
    if applicant_address:
        return ":50:" + applicant_name + "\n" + applicant_address
    return ":50:" + applicant_name


def _format_payment_terms(payment_terms: Optional[str]) -> Optional[str]:
    """Format payment terms for SWIFT field 42C."""
    if not payment_terms:
        return None
    
    swift_term = PAYMENT_TERMS_MAPPING.get(payment_terms)
    if swift_term:
        return ":42C:" + swift_term
    
    return None


def _format_documents_required(lc_data: Dict[str, Any]) -> str:
    """Format documents required for SWIFT field 46A."""
    documents_text = "DOCUMENTS REQUIRED:\n"
    
    # Add document list
    for doc in lc_data.get('documents', []):
        documents_text += "- " + doc.replace('_', ' ').title() + "\n"

    # Add additional documents text if provided
    if lc_data.get('documentsRequired'):
        documents_text += lc_data['documentsRequired']
    elif lc_data.get('additionalDocuments'):
        documents_text += lc_data['additionalDocuments']
    
    return documents_text


def _format_charges(charges: str) -> str:
    """Format charges allocation for SWIFT field 71B."""
    return CHARGES_OPTIONS.get(charges, CHARGES_OPTIONS['beneficiary'])


def generate_mt700_preview(lc_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate MT700 preview with metadata.
    
    Args:
        lc_data: LC data dictionary
        
    Returns:
        Dictionary containing message and preview metadata
    """
    try:
        swift_message = generate_mt700_message(lc_data)
        
        return {
            'success': True,
            'message': swift_message,
            'lc_number': lc_data.get('lcNumber'),
            'message_type': 'MT700',
            'generated_at': datetime.utcnow().isoformat(),
            'preview': True,
            'field_count': swift_message.count(':'),
            'line_count': len(swift_message.split('\n'))
        }
    except Exception as e:
        logger.error(f"Error generating MT700 preview: {e}")
        return {
            'success': False,
            'error': str(e)
        }


def validate_lc_data_for_mt700(lc_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate LC data before generating MT700.
    
    Args:
        lc_data: LC data dictionary
        
    Returns:
        Validation result dictionary
    """
    required_fields = [
        'lcNumber', 'applicant', 'beneficiary', 'amount', 
        'currency', 'issueDate', 'expiryDate', 'goodsDescription'
    ]
    
    missing_fields = []
    for field in required_fields:
        if not lc_data.get(field):
            missing_fields.append(field)
    
    validation_result = {
        'is_valid': len(missing_fields) == 0,
        'missing_fields': missing_fields,
        'warnings': []
    }
    
    # Additional validations
    if lc_data.get('issueDate') and lc_data.get('expiryDate'):
        try:
            issue = datetime.strptime(lc_data['issueDate'], '%Y-%m-%d')
            expiry = datetime.strptime(lc_data['expiryDate'], '%Y-%m-%d')
            if expiry <= issue:
                validation_result['warnings'].append('Expiry date should be after issue date')
        except ValueError:
            validation_result['warnings'].append('Invalid date format')
    
    if lc_data.get('amount'):
        try:
            amount = float(lc_data['amount'])
            if amount <= 0:
                validation_result['warnings'].append('Amount should be positive')
        except ValueError:
            validation_result['warnings'].append('Invalid amount format')
    
    return validation_result
