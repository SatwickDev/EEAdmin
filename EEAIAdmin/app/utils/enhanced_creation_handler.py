"""
Enhanced Creation Intent Handler with Form Auto-fill Support
"""
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from flask import jsonify

logger = logging.getLogger(__name__)

class EnhancedCreationHandler:
    """Handles creation intents with form auto-fill capability"""
    
    def __init__(self):
        self.form_mappings = {
            'trade_finance': {
                'import_lc': {
                    'fields': [
                        'lcNumber', 'lcType', 'issueDate', 'expiryDate',
                        'applicant', 'beneficiary', 'issuingBank', 'advisingBank',
                        'currency', 'amount', 'tolerancePercent', 'paymentTerms',
                        'placeOfTaking', 'portOfLoading', 'portOfDischarge', 'finalDestination',
                        'latestShipmentDate', 'partialShipment', 'transhipment', 'incoterms',
                        'goodsDescription', 'hsCode', 'quantity', 'documents',
                        'additionalDocuments', 'additionalConditions', 'charges'
                    ],
                    'required': [
                        'lcNumber', 'lcType', 'issueDate', 'expiryDate',
                        'applicant', 'beneficiary', 'issuingBank', 'currency',
                        'amount', 'paymentTerms', 'latestShipmentDate', 'goodsDescription'
                    ]
                },
                'bank_guarantee': {
                    'fields': [
                        'guaranteeNumber', 'guaranteeType', 'issueDate', 'expiryDate',
                        'applicant', 'beneficiary', 'amount', 'currency', 'purpose'
                    ],
                    'required': [
                        'guaranteeType', 'issueDate', 'expiryDate',
                        'applicant', 'beneficiary', 'amount', 'currency'
                    ]
                }
            },
            'treasury': {
                'forex': {
                    'fields': [
                        'transactionType', 'dealDate', 'valueDate', 'maturityDate',
                        'buyCurrency', 'buyAmount', 'sellCurrency', 'sellAmount',
                        'exchangeRate', 'counterparty'
                    ],
                    'required': [
                        'transactionType', 'dealDate', 'valueDate',
                        'buyCurrency', 'buyAmount', 'sellCurrency', 'sellAmount',
                        'exchangeRate', 'counterparty'
                    ]
                },
                'investment': {
                    'fields': [
                        'investmentType', 'investmentDate', 'maturityDateInv', 'tenor',
                        'principalAmount', 'investmentCurrency', 'interestRate',
                        'maturityValue', 'issuer', 'rating'
                    ],
                    'required': [
                        'investmentType', 'investmentDate', 'maturityDateInv',
                        'principalAmount', 'investmentCurrency', 'interestRate', 'issuer'
                    ]
                }
            },
            'cash_management': {
                'payment': {
                    'fields': [
                        'paymentType', 'paymentDate', 'valueDate', 'priority',
                        'debitAccount', 'paymentAmount', 'paymentCurrency', 'chargeBearer',
                        'beneficiaryName', 'beneficiaryAccount', 'beneficiaryBank',
                        'swiftCode', 'paymentPurpose'
                    ],
                    'required': [
                        'paymentType', 'paymentDate', 'valueDate',
                        'debitAccount', 'paymentAmount', 'paymentCurrency',
                        'beneficiaryName', 'beneficiaryAccount', 'beneficiaryBank',
                        'paymentPurpose'
                    ]
                },
                'collection': {
                    'fields': [
                        'collectionType', 'collectionDate', 'customerName',
                        'invoiceNumber', 'collectionAmount', 'collectionCurrency',
                        'creditAccount', 'collectionStatus'
                    ],
                    'required': [
                        'collectionType', 'collectionDate', 'customerName',
                        'collectionAmount', 'collectionCurrency', 'creditAccount'
                    ]
                }
            }
        }
        
    def handle_creation_request(self, user_query: str, context: List[Dict], 
                               repository: str = None) -> Dict[str, Any]:
        """
        Process creation intent and prepare form auto-fill data
        
        Args:
            user_query: User's query text
            context: Conversation context
            repository: Active repository (trade_finance, treasury, cash_management)
            
        Returns:
            Response with form data and auto-fill instructions
        """
        try:
            # Detect form type from query
            form_type = self._detect_form_type(user_query, repository)
            
            if not form_type:
                return {
                    'intent': 'Creation Transaction',
                    'response': 'Please specify what type of transaction you want to create.',
                    'suggestions': self._get_available_forms(repository)
                }
            
            # Extract data from user query
            extracted_data = self._extract_form_data(user_query, form_type, repository)
            
            # Validate required fields
            missing_fields = self._validate_required_fields(extracted_data, form_type, repository)
            
            if missing_fields:
                return {
                    'intent': 'Creation Transaction',
                    'response': f'I can help you create a {form_type}. Please provide the following information:',
                    'missing_fields': missing_fields,
                    'partial_data': extracted_data,
                    'form_type': form_type,
                    'repository': repository
                }
            
            # All required fields present - prepare for auto-fill
            return {
                'intent': 'Creation Transaction',
                'response': f'I have prepared the {form_type} form with your data. Click "Auto-fill Form" to populate the fields.',
                'form_data': extracted_data,
                'form_type': form_type,
                'repository': repository,
                'auto_fill_ready': True,
                'action_buttons': [
                    {
                        'label': 'Auto-fill Form',
                        'action': 'auto_fill',
                        'data': {
                            'form_type': form_type,
                            'form_data': extracted_data
                        }
                    },
                    {
                        'label': 'Modify Data',
                        'action': 'modify',
                        'data': extracted_data
                    }
                ]
            }
            
        except Exception as e:
            logger.error(f"Error in handle_creation_request: {str(e)}")
            return {
                'intent': 'Creation Transaction',
                'response': 'I encountered an error while processing your request. Please try again.',
                'error': str(e)
            }
    
    def _detect_form_type(self, query: str, repository: str) -> Optional[str]:
        """Detect which form type the user wants to create"""
        query_lower = query.lower()
        
        # Form type keywords
        form_keywords = {
            'import_lc': ['import lc', 'import letter of credit', 'import l/c', 'mt700'],
            'bank_guarantee': ['bank guarantee', 'bg', 'guarantee'],
            'forex': ['forex', 'foreign exchange', 'fx', 'currency exchange'],
            'investment': ['investment', 'fixed deposit', 'fd', 'treasury bill'],
            'payment': ['payment', 'wire transfer', 'ach', 'rtgs', 'neft'],
            'collection': ['collection', 'direct debit', 'receivable']
        }
        
        for form_type, keywords in form_keywords.items():
            for keyword in keywords:
                if keyword in query_lower:
                    return form_type
        
        # Default based on repository
        if repository:
            defaults = {
                'trade_finance': 'import_lc',
                'treasury': 'forex',
                'cash_management': 'payment'
            }
            return defaults.get(repository)
        
        return None
    
    def _extract_form_data(self, query: str, form_type: str, repository: str) -> Dict[str, Any]:
        """Extract form field data from user query"""
        extracted = {}
        
        # Example extraction logic (would be enhanced with NLP)
        import re
        
        # Extract amounts
        amount_pattern = r'(?:amount|value|principal).*?(\d+(?:,\d{3})*(?:\.\d{2})?)'
        amount_match = re.search(amount_pattern, query, re.IGNORECASE)
        if amount_match:
            amount_str = amount_match.group(1).replace(',', '')
            if form_type == 'import_lc':
                extracted['amount'] = float(amount_str)
            elif form_type == 'payment':
                extracted['paymentAmount'] = float(amount_str)
            elif form_type == 'investment':
                extracted['principalAmount'] = float(amount_str)
        
        # Extract currencies
        currencies = ['USD', 'EUR', 'GBP', 'JPY', 'INR', 'AED']
        for currency in currencies:
            if currency in query.upper():
                if form_type == 'import_lc':
                    extracted['currency'] = currency
                elif form_type == 'payment':
                    extracted['paymentCurrency'] = currency
                elif form_type == 'investment':
                    extracted['investmentCurrency'] = currency
        
        # Extract dates
        today = datetime.now()
        if 'today' in query.lower():
            if form_type == 'import_lc':
                extracted['issueDate'] = today.strftime('%Y-%m-%d')
            elif form_type == 'payment':
                extracted['paymentDate'] = today.strftime('%Y-%m-%d')
        
        # Extract beneficiary/applicant names
        name_pattern = r'(?:beneficiary|applicant|customer|counterparty).*?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
        name_match = re.search(name_pattern, query)
        if name_match:
            name = name_match.group(1)
            if form_type == 'import_lc':
                if 'beneficiary' in query.lower():
                    extracted['beneficiary'] = name
                else:
                    extracted['applicant'] = name
            elif form_type == 'payment':
                extracted['beneficiaryName'] = name
        
        return extracted
    
    def _validate_required_fields(self, data: Dict[str, Any], form_type: str, 
                                 repository: str) -> List[str]:
        """Check which required fields are missing"""
        if not repository or repository not in self.form_mappings:
            return []
        
        repo_forms = self.form_mappings.get(repository, {})
        form_config = repo_forms.get(form_type, {})
        required_fields = form_config.get('required', [])
        
        missing = []
        for field in required_fields:
            if field not in data or data[field] is None:
                missing.append(field)
        
        return missing
    
    def _get_available_forms(self, repository: str) -> List[Dict[str, str]]:
        """Get list of available forms for the repository"""
        forms = {
            'trade_finance': [
                {'type': 'import_lc', 'label': 'Import Letter of Credit'},
                {'type': 'bank_guarantee', 'label': 'Bank Guarantee'},
                {'type': 'export_lc', 'label': 'Export Letter of Credit'}
            ],
            'treasury': [
                {'type': 'forex', 'label': 'Foreign Exchange'},
                {'type': 'investment', 'label': 'Investment'},
                {'type': 'derivatives', 'label': 'Derivatives'}
            ],
            'cash_management': [
                {'type': 'payment', 'label': 'Payment'},
                {'type': 'collection', 'label': 'Collection'},
                {'type': 'pooling', 'label': 'Cash Pooling'}
            ]
        }
        
        return forms.get(repository, [])
    
    def process_form_modification(self, current_data: Dict[str, Any], 
                                 modifications: str) -> Dict[str, Any]:
        """Process user modifications to form data"""
        updated_data = current_data.copy()
        
        # Parse modifications and update data
        # This would use NLP to understand what fields to modify
        
        return updated_data
    
    def generate_confirmation_message(self, form_type: str, data: Dict[str, Any]) -> str:
        """Generate a confirmation message with form data summary"""
        summary_lines = [f"Here's a summary of your {form_type} transaction:"]
        
        # Format key fields for display
        key_fields = {
            'import_lc': ['lcNumber', 'applicant', 'beneficiary', 'amount', 'currency'],
            'payment': ['paymentType', 'beneficiaryName', 'paymentAmount', 'paymentCurrency'],
            'investment': ['investmentType', 'principalAmount', 'interestRate', 'maturityDateInv']
        }
        
        display_fields = key_fields.get(form_type, list(data.keys())[:5])
        
        for field in display_fields:
            if field in data:
                # Format field name for display
                display_name = field.replace('_', ' ').title()
                value = data[field]
                
                # Format currency values
                if 'amount' in field.lower() or 'value' in field.lower():
                    if isinstance(value, (int, float)):
                        value = f"{value:,.2f}"
                
                summary_lines.append(f"• {display_name}: {value}")
        
        summary_lines.append("\nWould you like to proceed with auto-filling the form?")
        
        return "\n".join(summary_lines)

# Export the handler instance
creation_handler = EnhancedCreationHandler()