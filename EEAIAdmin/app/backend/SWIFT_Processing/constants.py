"""
SWIFT Processing Constants
==========================

Defines constants for SWIFT message types, field definitions, and configuration.
"""

# SWIFT Message Types used in Trade Finance
MT_MESSAGE_TYPES = {
    'MT700': {
        'name': 'Issue of a Documentary Credit',
        'description': 'Sent by the issuing bank to the advising bank to issue a documentary credit',
        'category': 'Documentary Credits'
    },
    'MT701': {
        'name': 'Amendment to a Documentary Credit',
        'description': 'Sent to advise amendments to a documentary credit',
        'category': 'Documentary Credits'
    },
    'MT705': {
        'name': 'Pre-Advice of a Documentary Credit',
        'description': 'Sent to pre-advise the advising bank about the imminent issuance of a documentary credit',
        'category': 'Documentary Credits'
    },
    'MT707': {
        'name': 'Amendment to a Documentary Credit',
        'description': 'Sent by the issuing bank or advising bank to amend a documentary credit',
        'category': 'Documentary Credits'
    },
    'MT710': {
        'name': 'Advice of a Third Bank\'s Documentary Credit',
        'description': 'Sent by the advising bank to another bank',
        'category': 'Documentary Credits'
    },
    'MT720': {
        'name': 'Transfer of a Documentary Credit',
        'description': 'Sent to advise the transfer of a documentary credit',
        'category': 'Documentary Credits'
    },
    'MT730': {
        'name': 'Acknowledgement',
        'description': 'Sent to acknowledge receipt of a documentary credit',
        'category': 'Documentary Credits'
    },
    'MT740': {
        'name': 'Authorisation to Reimburse',
        'description': 'Sent by the issuing bank to the reimbursing bank',
        'category': 'Documentary Credits'
    },
    'MT750': {
        'name': 'Advice of Discrepancy',
        'description': 'Sent to advise of discrepancies in documents presented',
        'category': 'Documentary Credits'
    },
    'MT760': {
        'name': 'Guarantee / Standby Letter of Credit',
        'description': 'Sent to issue a guarantee or standby letter of credit',
        'category': 'Guarantees'
    }
}

# MT700 Field Definitions
MT700_FIELD_DEFINITIONS = {
    '20': {
        'name': 'Documentary Credit Number',
        'mandatory': True,
        'max_length': 16,
        'description': 'Unique reference assigned by the issuing bank'
    },
    '23': {
        'name': 'Reference to Pre-Advice',
        'mandatory': False,
        'max_length': 16,
        'description': 'Reference number of a pre-advice message'
    },
    '27': {
        'name': 'Sequence of Total',
        'mandatory': True,
        'max_length': 5,
        'description': 'Sequence number (e.g., 1/1, 1/2)',
        'format': 'n/n'
    },
    '31C': {
        'name': 'Date of Issue',
        'mandatory': True,
        'max_length': 6,
        'description': 'Date when the documentary credit is issued',
        'format': 'YYMMDD'
    },
    '31D': {
        'name': 'Date and Place of Expiry',
        'mandatory': True,
        'max_length': 35,
        'description': 'Expiry date and location',
        'format': 'YYMMDD + Place'
    },
    '32B': {
        'name': 'Currency Code, Amount',
        'mandatory': True,
        'max_length': 18,
        'description': 'Currency and amount of the documentary credit',
        'format': 'CCY + Amount'
    },
    '39A': {
        'name': 'Percentage Credit Amount Tolerance',
        'mandatory': False,
        'max_length': 5,
        'description': 'Credit amount tolerance percentage'
    },
    '40A': {
        'name': 'Form of Documentary Credit',
        'mandatory': True,
        'max_length': 24,
        'description': 'Type of documentary credit (IRREVOCABLE, etc.)'
    },
    '41A': {
        'name': 'Available With...By...',
        'mandatory': True,
        'max_length': 35,
        'description': 'Bank where credit is available and method'
    },
    '42A': {
        'name': 'Drawee',
        'mandatory': False,
        'max_length': 35,
        'description': 'Drawee bank identification'
    },
    '42C': {
        'name': 'Drafts at...',
        'mandatory': False,
        'max_length': 105,
        'description': 'Tenor of drafts (BY PAYMENT, DEFERRED, etc.)'
    },
    '42P': {
        'name': 'Drawee',
        'mandatory': False,
        'max_length': 140,
        'description': 'Drawee name and address'
    },
    '43P': {
        'name': 'Partial Shipments',
        'mandatory': True,
        'max_length': 11,
        'description': 'ALLOWED or NOT ALLOWED'
    },
    '43T': {
        'name': 'Transhipment',
        'mandatory': True,
        'max_length': 11,
        'description': 'ALLOWED or NOT ALLOWED'
    },
    '44A': {
        'name': 'Place of Taking in Charge/Dispatch from',
        'mandatory': False,
        'max_length': 65,
        'description': 'Origin location for goods'
    },
    '44B': {
        'name': 'Place of Final Destination/For Transportation to',
        'mandatory': False,
        'max_length': 65,
        'description': 'Final destination for goods'
    },
    '44C': {
        'name': 'Latest Date of Shipment',
        'mandatory': False,
        'max_length': 6,
        'description': 'Latest shipment date',
        'format': 'YYMMDD'
    },
    '44E': {
        'name': 'Port of Loading/Airport of Departure',
        'mandatory': False,
        'max_length': 65,
        'description': 'Loading port or departure airport'
    },
    '44F': {
        'name': 'Port of Discharge/Airport of Destination',
        'mandatory': False,
        'max_length': 65,
        'description': 'Discharge port or destination airport'
    },
    '45A': {
        'name': 'Description of Goods and/or Services',
        'mandatory': True,
        'max_length': 10000,
        'description': 'Detailed description of goods',
        'multiline': True
    },
    '46A': {
        'name': 'Documents Required',
        'mandatory': True,
        'max_length': 10000,
        'description': 'List of required documents',
        'multiline': True
    },
    '47A': {
        'name': 'Additional Conditions',
        'mandatory': False,
        'max_length': 10000,
        'description': 'Additional terms and conditions',
        'multiline': True
    },
    '48': {
        'name': 'Period for Presentation',
        'mandatory': False,
        'max_length': 35,
        'description': 'Days within which documents must be presented'
    },
    '49': {
        'name': 'Confirmation Instructions',
        'mandatory': True,
        'max_length': 10,
        'description': 'CONFIRM, MAY ADD, WITHOUT'
    },
    '50': {
        'name': 'Applicant',
        'mandatory': True,
        'max_length': 140,
        'description': 'Applicant name and address',
        'multiline': True
    },
    '51A': {
        'name': 'Issuing Bank',
        'mandatory': False,
        'max_length': 35,
        'description': 'Issuing bank BIC/SWIFT code'
    },
    '52A': {
        'name': 'Issuing Bank',
        'mandatory': False,
        'max_length': 140,
        'description': 'Issuing bank name and address'
    },
    '57A': {
        'name': 'Advising Bank',
        'mandatory': False,
        'max_length': 35,
        'description': 'Advising bank BIC/SWIFT code'
    },
    '59': {
        'name': 'Beneficiary',
        'mandatory': True,
        'max_length': 140,
        'description': 'Beneficiary name and address',
        'multiline': True
    },
    '71B': {
        'name': 'Charges',
        'mandatory': True,
        'max_length': 105,
        'description': 'Charges allocation'
    },
    '72': {
        'name': 'Sender to Receiver Information',
        'mandatory': False,
        'max_length': 4200,
        'description': 'Free-format information',
        'multiline': True
    },
    '78': {
        'name': 'Instructions to Paying/Accepting/Negotiating Bank',
        'mandatory': False,
        'max_length': 3500,
        'description': 'Instructions for the bank',
        'multiline': True
    }
}

# SWIFT Date Format
SWIFT_DATE_FORMAT = '%y%m%d'  # YYMMDD format used in SWIFT messages

# Common ISO 4217 Currency Codes
SWIFT_CURRENCY_CODES = {
    'USD': 'US Dollar',
    'EUR': 'Euro',
    'GBP': 'British Pound',
    'JPY': 'Japanese Yen',
    'CHF': 'Swiss Franc',
    'CNY': 'Chinese Yuan',
    'AED': 'UAE Dirham',
    'SAR': 'Saudi Riyal',
    'INR': 'Indian Rupee',
    'SGD': 'Singapore Dollar',
    'HKD': 'Hong Kong Dollar',
    'AUD': 'Australian Dollar',
    'CAD': 'Canadian Dollar',
    'KWD': 'Kuwaiti Dinar',
    'BHD': 'Bahraini Dinar'
}

# SWIFT Field Character Limits
SWIFT_FIELD_LIMITS = {
    'address_line': 35,  # Max characters per address line
    'address_lines': 4,   # Max number of address lines
    'goods_description': 1000,  # Field 45A limit for preview
    'documents_required': 6000,  # Field 46A limit
    'additional_conditions': 8500,  # Field 47A limit
    'instructions_to_bank': 3500,  # Field 78 limit
    'sender_to_receiver': 4200,  # Field 72 limit
    'reference_number': 16,  # Field 20 limit
    'swift_code': 11  # BIC/SWIFT code length
}

# Default SWIFT Configuration
DEFAULT_SWIFT_CONFIG = {
    'sender_bic': 'BANKGB2LAXXX',
    'sender_reference': '0000000000',
    'receiver_bic': 'BANKUS33XXXX',
    'message_priority': 'N',  # Normal priority
    'default_place_of_expiry': 'ANY BANK',
    'default_form': 'IRREVOCABLE'
}

# LC Type to SWIFT Format Mapping
LC_TYPE_MAPPING = {
    'irrevocable': 'IRREVOCABLE',
    'revocable': 'REVOCABLE',
    'transferable': 'IRREVOCABLE TRANSFERABLE',
    'confirmed': 'IRREVOCABLE CONFIRMED',
    'standby': 'STANDBY',
    'revolving': 'REVOLVING'
}

# Payment Terms to SWIFT Format Mapping
PAYMENT_TERMS_MAPPING = {
    'By Payment': 'BY PAYMENT',
    'deferred': 'DEFERRED PAYMENT',
    'mixedpayment': 'MIXED PAYMENT',
    'acceptance': 'BY ACCEPTANCE',
    'negotiation': 'BY NEGOTIATION'
}

# Shipment Terms Mapping
SHIPMENT_TERMS = {
    'allowed': 'ALLOWED',
    'not_allowed': 'NOT ALLOWED',
    'conditional': 'CONDITIONAL'
}

# Charges Allocation Options
CHARGES_OPTIONS = {
    'beneficiary': "ALL CHARGES OUTSIDE OPENING BANK'S COUNTRY FOR BENEFICIARY'S ACCOUNT",
    'applicant': "ALL CHARGES FOR APPLICANT'S ACCOUNT",
    'shared': "CHARGES SHARED EQUALLY"
}
