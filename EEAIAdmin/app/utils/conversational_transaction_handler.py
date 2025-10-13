"""
Pure Conversational Transaction Handler - No Forms Required
"""
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from flask import jsonify
import openai
from app.utils.app_config import deployment_name

logger = logging.getLogger(__name__)

def sanitize_for_json(obj):
    """Convert non-serializable objects to JSON-serializable format"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {key: sanitize_for_json(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_for_json(item) for item in obj]
    elif hasattr(obj, '__dict__'):
        return sanitize_for_json(obj.__dict__)
    else:
        return obj

class ConversationalTransactionHandler:
    """Handles complete transactions through conversation only"""
    
    def __init__(self, db):
        self.db = db
        self.transaction_schemas = {
            'import_lc': {
                'required': ['applicant', 'beneficiary', 'amount', 'currency', 'expiry_date', 'goods_description'],
                'optional': ['issuing_bank', 'advising_bank', 'shipment_date', 'documents', 'incoterms'],
                'validations': {
                    'amount': lambda x: float(x) > 0,
                    'currency': lambda x: x in ['USD', 'EUR', 'GBP', 'JPY', 'INR'],
                    'expiry_date': lambda x: self._validate_expiry_date(x)
                }
            },
            'payment': {
                'required': ['beneficiary_name', 'amount', 'currency', 'account_number'],
                'optional': ['payment_type', 'purpose', 'charges'],
                'validations': {
                    'amount': lambda x: float(x) > 0,
                    'currency': lambda x: x in ['USD', 'EUR', 'GBP', 'JPY', 'INR']
                }
            },
            'forex': {
                'required': ['buy_currency', 'sell_currency', 'amount', 'exchange_rate'],
                'optional': ['value_date', 'counterparty'],
                'validations': {
                    'amount': lambda x: float(x) > 0,
                    'exchange_rate': lambda x: float(x) > 0
                }
            }
        }
        
    def process_creation_intent(self, user_query: str, session_id: str, 
                               user_id: str, context: List[Dict], 
                               repository: str = None) -> Dict[str, Any]:
        """
        Process entire transaction through conversation without forms
        All logic handled by LLM dynamically
        """
        try:
            # Get or create transaction session
            transaction_session = self._get_transaction_session(session_id, user_id)
            
            # Store repository in session if provided
            if repository:
                transaction_session['repository'] = repository
            
            # Detect transaction type if not set
            if not transaction_session.get('transaction_type'):
                transaction_type = self._detect_transaction_type(user_query, context, repository)
                if transaction_type:
                    transaction_session['transaction_type'] = transaction_type
                    self._save_transaction_session(session_id, transaction_session)
                else:
                    return self._ask_transaction_type(repository)
            
            
            # Extract information from current query
            extracted_data = self._extract_transaction_data(
                user_query, 
                transaction_session['transaction_type'],
                transaction_session.get('collected_data', {}),
                context  # Pass context for similar transaction detection
            )
            
            # Merge with existing data
            transaction_session['collected_data'] = {
                **transaction_session.get('collected_data', {}),
                **extracted_data
            }
            
            # Add default goods_description if missing and we have product info
            if transaction_session['transaction_type'] == 'import_lc':
                if 'goods_description' not in transaction_session['collected_data']:
                    # Check if we extracted product type from table
                    if 'product_type' in extracted_data:
                        transaction_session['collected_data']['goods_description'] = extracted_data['product_type']
                    elif not transaction_session['collected_data'].get('goods_description'):
                        # Use a generic description if nothing else available
                        transaction_session['collected_data']['goods_description'] = 'General merchandise'
                
                # Check and update expiry date if it's in the past
                if 'expiry_date' in transaction_session['collected_data']:
                    try:
                        from datetime import datetime, timedelta
                        expiry = datetime.strptime(transaction_session['collected_data']['expiry_date'], '%Y-%m-%d')
                        if expiry < datetime.now():
                            # Set new expiry date to 3 months from now
                            new_expiry = datetime.now() + timedelta(days=90)
                            transaction_session['collected_data']['expiry_date'] = new_expiry.strftime('%Y-%m-%d')
                            logger.info(f"Updated expired date to future date: {transaction_session['collected_data']['expiry_date']}")
                    except:
                        pass
            
            self._save_transaction_session(session_id, transaction_session)
            
            # Check what's missing
            missing_fields = self._get_missing_fields(
                transaction_session['transaction_type'],
                transaction_session['collected_data']
            )
            
            if missing_fields:
                # Ask for missing information
                return self._ask_for_missing_fields(
                    missing_fields,
                    transaction_session['collected_data'],
                    transaction_session['transaction_type']
                )
            
            # Validate all data
            validation_errors = self._validate_transaction_data(
                transaction_session['transaction_type'],
                transaction_session['collected_data']
            )
            
            if validation_errors:
                return self._request_corrections(validation_errors, transaction_session['collected_data'])
            
            # All data collected and valid - confirm with user
            if not transaction_session.get('confirmed'):
                return self._request_confirmation(
                    transaction_session['transaction_type'],
                    transaction_session['collected_data'],
                    session_id
                )
            
            # Execute transaction
            result = self._execute_transaction(
                transaction_session['transaction_type'],
                transaction_session['collected_data'],
                user_id
            )
            
            # Clear transaction session
            self._clear_transaction_session(session_id)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in conversational transaction: {str(e)}")
            return {
                'response': 'I encountered an error processing your transaction. Let\'s start over.',
                'error': str(e)
            }
    
    def _detect_operation_type(self, query: str, context: List[Dict]) -> str:
        """Use LLM to detect CRUD operation type"""
        
        prompt = f"""
        Analyze this user request and determine what operation they want to perform.
        
        User Query: {query}
        
        Context: {json.dumps(sanitize_for_json(context[-3:] if context else []))}
        
        Operations:
        - create: User wants to create a new transaction
        - update: User wants to update/modify an existing transaction
        - delete: User wants to delete/cancel an existing transaction
        - read: User wants to view/read transaction details
        
        Keywords for detection:
        - Create: "create", "new", "add", "initiate", "start", "similar", "duplicate"
        - Update: "update", "modify", "change", "edit" (with transaction ID)
        - Delete: "delete", "remove", "cancel", "void" (with transaction ID)
        - Read: "show", "view", "display", "get", "list"
        
        Return ONLY the operation type (create/update/delete/read).
        """
        
        try:
            response = openai.ChatCompletion.create(
                engine=deployment_name,
                messages=[
                    {"role": "system", "content": "Return only the operation type."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=20
            )
            
            operation = response.choices[0].message.content.strip().lower()
            if operation in ['create', 'update', 'delete', 'read']:
                return operation
            return 'create'  # Default to create
            
        except:
            # Fallback to keyword detection
            query_lower = query.lower()
            if any(word in query_lower for word in ['delete', 'remove', 'cancel', 'void']):
                return 'delete'
            elif any(word in query_lower for word in ['update', 'modify', 'change', 'edit']) and 'LC' in query:
                return 'update'
            return 'create'
    
    def _handle_delete_operation(self, query: str, user_id: str) -> Dict[str, Any]:
        """Handle delete transaction operation"""
        
        # Extract transaction ID using LLM
        prompt = f"""
        Extract the transaction ID from this delete request.
        
        User Query: {query}
        
        Look for patterns like:
        - LC2023001
        - IMPORT_LC20231120
        - Transaction IDs mentioned
        
        Return ONLY the transaction ID or "not_found" if no ID is mentioned.
        """
        
        try:
            response = openai.ChatCompletion.create(
                engine=deployment_name,
                messages=[
                    {"role": "system", "content": "Extract and return only the transaction ID."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=50
            )
            
            transaction_id = response.choices[0].message.content.strip()
            
            if transaction_id == "not_found":
                return {
                    'response': 'Please provide the transaction ID you want to delete.',
                    'intent': 'Creation Transaction',
                    'awaiting': 'transaction_id_for_delete'
                }
            
            # Confirm deletion
            return {
                'response': f"""⚠️ **Confirm Transaction Deletion**
                
**Transaction ID:** `{transaction_id}`

Are you sure you want to delete this transaction? This action cannot be undone.

Reply with:
• **'Yes'** to confirm deletion
• **'No'** to cancel""",
                'intent': 'Creation Transaction',
                'awaiting': 'delete_confirmation',
                'transaction_id': transaction_id,
                'action_buttons': [
                    {'label': '✅ Confirm Delete', 'action': 'confirm_delete', 'data': {'id': transaction_id}},
                    {'label': '❌ Cancel', 'action': 'cancel_delete'}
                ]
            }
            
        except Exception as e:
            logger.error(f"Error handling delete operation: {str(e)}")
            return {
                'response': 'Error processing delete request. Please provide the transaction ID.',
                'intent': 'Creation Transaction',
                'error': str(e)
            }
    
    def _handle_update_operation(self, query: str, user_id: str, context: List[Dict]) -> Dict[str, Any]:
        """Handle update transaction operation"""
        
        # Extract transaction ID and modifications using LLM
        prompt = f"""
        Extract the transaction ID and what needs to be updated from this request.
        
        User Query: {query}
        Context: {json.dumps(sanitize_for_json(context[-3:] if context else []))}
        
        Return as JSON:
        {{
            "transaction_id": "LC2023001",
            "updates": {{
                "field_name": "new_value"
            }}
        }}
        
        Return ONLY valid JSON.
        """
        
        try:
            response = openai.ChatCompletion.create(
                engine=deployment_name,
                messages=[
                    {"role": "system", "content": "Extract transaction ID and updates as JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=300
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Extract JSON
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(0)
            
            update_data = json.loads(response_text)
            
            if not update_data.get('transaction_id'):
                return {
                    'response': 'Please provide the transaction ID you want to update.',
                    'intent': 'Creation Transaction',
                    'awaiting': 'transaction_id_for_update'
                }
            
            # Execute update
            return self._execute_transaction(
                'update',
                update_data,
                user_id,
                operation='update'
            )
            
        except Exception as e:
            logger.error(f"Error handling update operation: {str(e)}")
            return {
                'response': 'Error processing update request. Please provide the transaction ID and fields to update.',
                'intent': 'Creation Transaction',
                'error': str(e)
            }
    
    def _detect_transaction_type(self, query: str, context: List[Dict], repository: str = None) -> Optional[str]:
        """Use AI to detect transaction type from conversation"""
        
        # Check if user wants to create a similar transaction from context
        query_lower = query.lower()
        if any(word in query_lower for word in ['similar', 'same', 'duplicate', 'copy', 'like']):
            # Look for transaction type in recent context
            for ctx in reversed(context[-5:] if context else []):
                if 'lc' in ctx.get('message', '').lower() or 'letter of credit' in ctx.get('message', '').lower():
                    if 'import' in ctx.get('message', '').lower():
                        return 'import_lc'
                    elif 'export' in ctx.get('message', '').lower():
                        return 'export_lc'
                    else:
                        return 'import_lc'  # Default to import LC
                elif 'payment' in ctx.get('message', '').lower():
                    return 'payment'
                elif 'forex' in ctx.get('message', '').lower() or 'fx' in ctx.get('message', '').lower():
                    return 'forex'
        
        # Check repository context
        if repository:
            if 'trade finance' in repository.lower():
                if 'import' in query_lower or 'lc' in query_lower:
                    return 'import_lc'
                elif 'export' in query_lower:
                    return 'export_lc'
            elif 'treasury' in repository.lower():
                if 'forex' in query_lower or 'fx' in query_lower:
                    return 'forex'
                elif 'investment' in query_lower:
                    return 'investment'
            elif 'cash' in repository.lower():
                if 'payment' in query_lower:
                    return 'payment'
        
        prompt = f"""
        Analyze this conversation and determine what type of financial transaction the user wants to create.
        
        User Query: {query}
        
        Context: {json.dumps(sanitize_for_json(context[-5:] if context else []))}
        
        Possible transaction types:
        - import_lc: Import Letter of Credit
        - export_lc: Export Letter of Credit  
        - payment: Payment/Wire Transfer
        - collection: Collection/Receivable
        - forex: Foreign Exchange
        - investment: Investment/Fixed Deposit
        - guarantee: Bank Guarantee
        
        Return ONLY the transaction type code (e.g., 'import_lc') or 'unknown' if unclear.
        """
        
        try:
            response = openai.ChatCompletion.create(
                engine=deployment_name,
                messages=[
                    {"role": "system", "content": "You are a transaction classifier."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=50
            )
            
            transaction_type = response.choices[0].message.content.strip().lower()
            
            if transaction_type in self.transaction_schemas:
                return transaction_type
            
            return None
            
        except Exception as e:
            logger.error(f"Error detecting transaction type: {str(e)}")
            return None
    
    def _extract_transaction_data(self, query: str, transaction_type: str, 
                                 existing_data: Dict, context: List[Dict] = None) -> Dict[str, Any]:
        """Use AI to extract transaction data from natural language"""
        
        schema = self.transaction_schemas.get(transaction_type, {})
        
        # Build comprehensive context for LLM
        context_text = ""
        if context:
            # Include recent conversation context
            for ctx in reversed(context[-5:] if context else []):
                if 'message' in ctx:
                    context_text += f"User: {ctx['message']}\n"
                if 'response' in ctx:
                    context_text += f"Assistant: {ctx['response'][:500]}...\n" if len(ctx['response']) > 500 else f"Assistant: {ctx['response']}\n"
        
        prompt = f"""
        Analyze the user input and conversation context to extract transaction data.
        
        User Input: {query}
        Transaction Type: {transaction_type}
        
        Full Conversation Context:
        {context_text}
        
        Required Fields: {schema.get('required', [])}
        Optional Fields: {schema.get('optional', [])}
        Already Collected: {json.dumps(sanitize_for_json(existing_data))}
        
        Instructions:
        1. If user wants to create a "similar" transaction or mentions an LC number, find that exact transaction in the HTML tables in the context
        2. Extract the exact data from the table row - do not generate new values
        3. If multiple LCs are shown and user hasn't specified which one, ask user to specify
        4. For expired dates, update them to future dates
        5. Remove commas from amounts
        
        Return as JSON. If you need user to specify which LC, return:
        {{"need_clarification": "Which LC would you like to use?", "available_options": ["LC2023002", "LC2024002"]}}
        
        Otherwise return the extracted data as JSON.
        """
        
        try:
            response = openai.ChatCompletion.create(
                engine=deployment_name,
                messages=[
                    {"role": "system", "content": "You are a transaction data extraction expert. Extract all relevant data from conversations and return as JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=800
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(0)
            
            extracted = json.loads(response_text)
            
            # Check if LLM needs clarification
            if 'need_clarification' in extracted:
                # Return empty dict to trigger missing fields flow
                # The message will be handled by the calling function
                return {}
            
            # Post-process dates to ensure correct format
            from datetime import datetime, timedelta
            for key, value in extracted.items():
                if 'date' in key.lower() and value:
                    if isinstance(value, str):
                        if value.lower() == 'today':
                            extracted[key] = datetime.now().strftime('%Y-%m-%d')
                        elif value.lower() == 'tomorrow':
                            extracted[key] = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
                        # Check if date is in past and update if needed for expiry dates
                        elif key == 'expiry_date':
                            try:
                                date_obj = datetime.strptime(value, '%Y-%m-%d')
                                if date_obj < datetime.now():
                                    # Set to 3 months in future
                                    extracted[key] = (datetime.now() + timedelta(days=90)).strftime('%Y-%m-%d')
                            except:
                                pass
            
            logger.info(f"LLM extracted transaction data: {extracted}")
            return extracted
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {str(e)}, Response: {response_text}")
            return {}
        except Exception as e:
            logger.error(f"Error extracting data with LLM: {str(e)}")
            return {}
    
    def _get_missing_fields(self, transaction_type: str, collected_data: Dict) -> List[str]:
        """Identify missing required fields"""
        
        schema = self.transaction_schemas.get(transaction_type, {})
        required = schema.get('required', [])
        
        missing = []
        for field in required:
            if field not in collected_data or collected_data[field] is None:
                missing.append(field)
        
        return missing
    
    def _ask_transaction_type(self, repository: str = None) -> Dict[str, Any]:
        """Ask user what type of transaction they want based on repository"""
        
        # Repository-specific transaction types
        repo_options = {
            'trade_finance': """I can help you create Trade Finance transactions:
            
• **Import LC** - Import Letter of Credit
• **Export LC** - Export Letter of Credit  
• **Bank Guarantee** - Performance/Financial Guarantee
• **Collection** - Documentary Collection

Example: "Create an import LC for $50,000 to ABC Company" """,
            
            'treasury': """I can help you create Treasury transactions:
            
• **Forex** - Foreign Exchange Trade (Spot/Forward)
• **Investment** - Fixed Deposit or Securities
• **Derivatives** - Swaps, Options, Futures
• **Money Market** - Commercial Paper, T-Bills

Example: "Buy 100,000 USD against EUR at 1.0950" """,
            
            'cash_management': """I can help you create Cash Management transactions:
            
• **Payment** - Wire Transfer, ACH, RTGS
• **Collection** - Direct Debit, Receivables
• **Cash Pooling** - Liquidity Management
• **Forecast** - Cash Flow Projection

Example: "Make payment of 25,000 to XYZ Corp account 123456" """
        }
        
        # Get repository-specific message or default
        message = repo_options.get(repository, """I can help you create a transaction. What would you like to do?
            
• **Import LC** - Import Letter of Credit
• **Payment** - Wire Transfer or Payment
• **Forex** - Foreign Exchange Trade
• **Investment** - Fixed Deposit or Investment
• **Collection** - Receivables Collection
• **Guarantee** - Bank Guarantee

Just tell me what you need, for example: "I want to create an import LC for $50,000" """)
        
        return {
            'response': message,
            'intent': 'Creation Transaction',
            'awaiting': 'transaction_type',
            'repository': repository
        }
    
    def _ask_for_missing_fields(self, missing: List[str], 
                               collected: Dict, transaction_type: str) -> Dict[str, Any]:
        """Generate natural language request for missing fields"""
        
        # Make field names human-readable
        field_descriptions = {
            'applicant': 'applicant name (importer)',
            'beneficiary': 'beneficiary name (exporter)',
            'amount': 'transaction amount',
            'currency': 'currency (USD, EUR, GBP, etc.)',
            'expiry_date': 'expiry date (YYYY-MM-DD)',
            'goods_description': 'description of goods',
            'beneficiary_name': 'beneficiary name',
            'account_number': 'beneficiary account number',
            'buy_currency': 'currency to buy',
            'sell_currency': 'currency to sell',
            'exchange_rate': 'exchange rate'
        }
        
        missing_descriptions = [field_descriptions.get(f, f.replace('_', ' ')) for f in missing[:3]]
        
        # Show what we have
        collected_summary = []
        for key, value in collected.items():
            if value:
                readable_key = key.replace('_', ' ').title()
                if isinstance(value, float):
                    if 'amount' in key or 'value' in key:
                        value = f"{value:,.2f}"
                collected_summary.append(f"• {readable_key}: {value}")
        
        response = f"""I'm creating your {transaction_type.replace('_', ' ').title()}. 

**Information collected so far:**
{chr(10).join(collected_summary) if collected_summary else 'None yet'}

**I still need:**
{', '.join(missing_descriptions)}

Please provide these details. You can say something like:
"The {missing_descriptions[0]} is ..." """
        
        return {
            'response': response,
            'intent': 'Creation Transaction',
            'awaiting': 'missing_fields',
            'missing_fields': missing,
            'collected_data': collected
        }
    
    def _validate_expiry_date(self, date_str: str) -> bool:
        """Validate expiry date - must be in the future"""
        try:
            # Parse the date
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            # Check if it's a future date
            return date_obj > datetime.now()
        except:
            return False
    
    def _validate_transaction_data(self, transaction_type: str, data: Dict) -> List[str]:
        """Validate collected data using LLM for dynamic business rules"""
        
        prompt = f"""
        Validate this transaction data for business rules and compliance.
        
        Transaction Type: {transaction_type}
        Transaction Data: {json.dumps(sanitize_for_json(data))}
        
        Check for:
        1. Amount must be positive number
        2. Currency must be valid ISO code (USD, EUR, GBP, JPY, INR, AED, etc.)
        3. Expiry date must be in the future
        4. Required fields must not be empty
        5. Email addresses must be valid format
        6. Phone numbers must be valid format
        7. Bank account numbers must be valid format
        8. Any other business rule violations
        
        Return a JSON array of validation errors. If no errors, return empty array.
        
        Example response with errors:
        ["amount: must be greater than 0", "expiry_date: must be in the future", "currency: invalid ISO code"]
        
        Example response with no errors:
        []
        
        Return ONLY the JSON array.
        """
        
        try:
            response = openai.ChatCompletion.create(
                engine=deployment_name,
                messages=[
                    {"role": "system", "content": "You are a transaction validation specialist. Return only JSON array of errors."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=300
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Extract JSON array
            import re
            json_match = re.search(r'\[.*?\]', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(0)
            
            errors = json.loads(response_text)
            
            # Additional check for expiry date in code to ensure it's future
            if 'expiry_date' in data:
                try:
                    from datetime import datetime
                    expiry = datetime.strptime(data['expiry_date'], '%Y-%m-%d')
                    if expiry < datetime.now():
                        if "expiry_date" not in str(errors):
                            errors.append(f"expiry_date: must be in the future (currently {data['expiry_date']})")
                except:
                    pass
            
            logger.info(f"LLM validation errors: {errors}")
            return errors
            
        except Exception as e:
            logger.error(f"Error in LLM validation: {str(e)}")
            # Fallback to basic validation
            errors = []
            if 'amount' in data:
                try:
                    if float(data['amount']) <= 0:
                        errors.append("amount: must be greater than 0")
                except:
                    errors.append("amount: invalid number format")
            return errors
    
    def _request_corrections(self, errors: List[str], data: Dict) -> Dict[str, Any]:
        """Ask user to correct validation errors"""
        
        return {
            'response': f"""I found some issues with the data:

{chr(10).join('• ' + error for error in errors)}

Please provide the correct values.""",
            'intent': 'Creation Transaction',
            'awaiting': 'corrections',
            'validation_errors': errors,
            'current_data': data
        }
    
    def _request_confirmation(self, transaction_type: str, data: Dict, session_id: str) -> Dict[str, Any]:
        """Show transaction summary and request confirmation"""
        
        # Format transaction summary
        summary_lines = [f"**{transaction_type.replace('_', ' ').title()} Transaction Summary:**", ""]
        
        # Format each field
        for key, value in data.items():
            readable_key = key.replace('_', ' ').title()
            if isinstance(value, float):
                if 'amount' in key or 'value' in key:
                    value = f"{value:,.2f}"
            summary_lines.append(f"• **{readable_key}:** {value}")
        
        summary_lines.extend([
            "",
            "✅ **Ready to submit this transaction?**",
            "",
            "Reply with:",
            "• **'Yes'** or **'Confirm'** to submit",
            "• **'No'** or **'Cancel'** to cancel", 
            "• **'Modify'** followed by what you want to change"
        ])
        
        return {
            'response': '\n'.join(summary_lines),
            'intent': 'Creation Transaction',
            'awaiting': 'confirmation',
            'transaction_data': data,
            'session_id': session_id,
            'action_buttons': [
                {'label': '✅ Confirm', 'action': 'confirm_transaction'},
                {'label': '❌ Cancel', 'action': 'cancel_transaction'},
                {'label': '✏️ Modify', 'action': 'modify_transaction'}
            ]
        }
    
    def confirm_transaction(self, session_id: str, user_id: str) -> Dict[str, Any]:
        """Handle transaction confirmation"""
        
        transaction_session = self._get_transaction_session(session_id, user_id)
        transaction_session['confirmed'] = True
        self._save_transaction_session(session_id, transaction_session)
        
        return self.process_creation_intent("confirm", session_id, user_id, [])
    
    def _execute_transaction(self, transaction_type: str, data: Dict, user_id: str, 
                           operation: str = 'create') -> Dict[str, Any]:
        """Execute transaction operations in the database (create, update, delete)"""
        
        try:
            # Determine collection using LLM if needed
            collection_prompt = f"""
            Determine the appropriate database collection for this transaction type: {transaction_type}
            
            Available collections:
            - lc_transactions: For import/export letters of credit
            - payments: For payment and wire transfers
            - forex_transactions: For foreign exchange trades
            - investments: For fixed deposits and investments
            - guarantees: For bank guarantees
            - collections: For receivables and collections
            - transactions: Default for other transaction types
            
            Return only the collection name.
            """
            
            try:
                response = openai.ChatCompletion.create(
                    engine=deployment_name,
                    messages=[
                        {"role": "system", "content": "Return only the database collection name."},
                        {"role": "user", "content": collection_prompt}
                    ],
                    temperature=0.1,
                    max_tokens=50
                )
                collection_name = response.choices[0].message.content.strip().lower()
                
                # Validate collection name
                valid_collections = ['lc_transactions', 'payments', 'forex_transactions', 
                                   'investments', 'guarantees', 'collections', 'transactions']
                if collection_name not in valid_collections:
                    collection_name = 'transactions'
            except:
                # Fallback mapping
                collection_map = {
                    'import_lc': 'lc_transactions',
                    'export_lc': 'lc_transactions',
                    'payment': 'payments',
                    'forex': 'forex_transactions'
                }
                collection_name = collection_map.get(transaction_type, 'transactions')
            
            if operation == 'create':
                # Add metadata
                data['transaction_type'] = transaction_type
                data['created_by'] = user_id
                data['created_at'] = datetime.utcnow().isoformat()
                data['updated_at'] = datetime.utcnow().isoformat()
                data['status'] = 'pending_approval'
                data['transaction_id'] = f"{transaction_type.upper()}{datetime.now().strftime('%Y%m%d%H%M%S')}"
                
                result = self.db[collection_name].insert_one(data)
                
                return {
                    'response': f"""✅ **Transaction Successfully Created!**

**Transaction ID:** `{data['transaction_id']}`
**Status:** Pending Approval
**Reference:** {str(result.inserted_id)}

The transaction has been submitted for approval. You'll receive a notification once it's processed.

Would you like to:
• Create another transaction
• View transaction status
• Download confirmation""",
                    'intent': 'Creation Transaction',
                    'success': True,
                    'transaction_id': data['transaction_id'],
                    'reference_id': str(result.inserted_id),
                    'action_buttons': [
                        {'label': '➕ New Transaction', 'action': 'new_transaction'},
                        {'label': '📊 View Status', 'action': 'view_status', 'data': {'id': data['transaction_id']}},
                        {'label': '📥 Download', 'action': 'download_confirmation', 'data': {'id': str(result.inserted_id)}}
                    ]
                }
                
            elif operation == 'update':
                # Update existing transaction
                transaction_id = data.get('transaction_id')
                if not transaction_id:
                    return {
                        'response': 'Transaction ID required for update operation',
                        'intent': 'Creation Transaction',
                        'success': False
                    }
                
                data['updated_at'] = datetime.utcnow().isoformat()
                data['updated_by'] = user_id
                
                result = self.db[collection_name].update_one(
                    {'transaction_id': transaction_id},
                    {'$set': data}
                )
                
                return {
                    'response': f"""✅ **Transaction Updated Successfully!**

**Transaction ID:** `{transaction_id}`
**Fields Updated:** {result.modified_count}

The transaction has been updated successfully.""",
                    'intent': 'Creation Transaction',
                    'success': True,
                    'transaction_id': transaction_id
                }
                
            elif operation == 'delete':
                # Delete transaction
                transaction_id = data.get('transaction_id')
                if not transaction_id:
                    return {
                        'response': 'Transaction ID required for delete operation',
                        'intent': 'Creation Transaction',
                        'success': False
                    }
                
                result = self.db[collection_name].delete_one({'transaction_id': transaction_id})
                
                return {
                    'response': f"""✅ **Transaction Deleted Successfully!**

**Transaction ID:** `{transaction_id}`
**Deleted:** {result.deleted_count > 0}""",
                    'intent': 'Creation Transaction',
                    'success': True,
                    'transaction_id': transaction_id
                }
            
            else:
                return {
                    'response': f'Unknown operation: {operation}',
                    'intent': 'Creation Transaction',
                    'success': False
                }
            
        except Exception as e:
            logger.error(f"Error executing {operation} transaction: {str(e)}")
            return {
                'response': f'Failed to {operation} transaction: {str(e)}',
                'intent': 'Creation Transaction',
                'success': False,
                'error': str(e)
            }
    
    def _get_transaction_session(self, session_id: str, user_id: str) -> Dict:
        """Get or create transaction session"""
        
        session = self.db.transaction_sessions.find_one({
            'session_id': session_id,
            'user_id': user_id
        })
        
        if session:
            return session.get('data', {})
        
        return {}
    
    def _save_transaction_session(self, session_id: str, data: Dict):
        """Save transaction session state"""
        
        self.db.transaction_sessions.update_one(
            {'session_id': session_id},
            {'$set': {
                'data': data,
                'updated_at': datetime.utcnow().isoformat()
            }},
            upsert=True
        )
    
    def _clear_transaction_session(self, session_id: str):
        """Clear transaction session after completion"""
        
        self.db.transaction_sessions.delete_one({'session_id': session_id})
    
    def _handle_modification(self, user_query: str, session: Dict) -> Dict[str, Any]:
        """Handle user modifications to collected data using LLM"""
        
        # Use LLM to extract modification intent
        prompt = f"""
        Analyze this modification request and extract what fields need to be updated.
        
        User Request: {user_query}
        
        Current Data: {json.dumps(sanitize_for_json(session.get('collected_data', {})))}
        
        Transaction Type: {session.get('transaction_type', 'import_lc')}
        
        Extract the modifications as JSON. Supported operations:
        - update: Change existing field values
        - add: Add new fields
        - delete: Remove fields
        
        For dates, use YYYY-MM-DD format. For "today", use current date.
        For currencies like "dhiram/dirham", use "AED".
        
        Example response:
        {{
            "operation": "update",
            "fields": {{
                "beneficiary": "New Company Ltd",
                "amount": 75000,
                "expiry_date": "2024-03-15"
            }}
        }}
        
        For delete operations:
        {{
            "operation": "delete",
            "fields": ["field1", "field2"]
        }}
        
        Return ONLY valid JSON.
        """
        
        try:
            response = openai.ChatCompletion.create(
                engine=deployment_name,
                messages=[
                    {"role": "system", "content": "You are a data modification specialist. Extract modification instructions from user requests."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=300
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(0)
            
            modification_data = json.loads(response_text)
            
            # Process based on operation type
            operation = modification_data.get('operation', 'update')
            
            if operation == 'update' or operation == 'add':
                fields = modification_data.get('fields', {})
                
                # Handle date conversions
                from datetime import datetime, timedelta
                for key, value in fields.items():
                    if 'date' in key.lower():
                        if value == 'today':
                            fields[key] = datetime.now().strftime('%Y-%m-%d')
                        elif value == 'tomorrow':
                            fields[key] = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
                        elif value == 'next week':
                            fields[key] = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
                        elif value == 'next month':
                            fields[key] = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
                
                logger.info(f"LLM extracted modifications: {fields}")
                return fields
                
            elif operation == 'delete':
                # Handle field deletion
                fields_to_delete = modification_data.get('fields', [])
                current_data = session.get('collected_data', {})
                
                for field in fields_to_delete:
                    if field in current_data:
                        del current_data[field]
                
                logger.info(f"Deleted fields: {fields_to_delete}")
                return {}  # Return empty dict as deletions are handled in-place
            
            else:
                logger.warning(f"Unknown operation: {operation}")
                return {}
                
        except Exception as e:
            logger.error(f"Error in LLM modification extraction: {str(e)}")
            # Fallback to empty modifications
            return {}
    
    def _show_current_progress(self, session: Dict) -> Dict[str, Any]:
        """Show current transaction progress after modifications"""
        
        collected_data = session.get('collected_data', {})
        transaction_type = session.get('transaction_type', 'import_lc')
        
        # Format current data
        summary_lines = [f"**Transaction Updated Successfully!**", ""]
        summary_lines.append(f"**Current {transaction_type.replace('_', ' ').title()} Details:**")
        summary_lines.append("")
        
        for key, value in collected_data.items():
            readable_key = key.replace('_', ' ').title()
            if isinstance(value, float):
                if 'amount' in key:
                    value = f"{value:,.2f}"
            summary_lines.append(f"• **{readable_key}:** {value}")
        
        # Check for missing fields
        missing_fields = self._get_missing_fields(transaction_type, collected_data)
        
        if missing_fields:
            summary_lines.extend([
                "",
                "**Still need:**",
                f"{', '.join(missing_fields)}",
                "",
                "Please provide the missing information or say 'proceed' to continue."
            ])
        else:
            summary_lines.extend([
                "",
                "✅ **All required information collected!**",
                "",
                "Say:",
                "• **'Proceed'** or **'Submit'** to create the transaction",
                "• **'Change [field]'** to modify any field",
                "• **'Cancel'** to cancel the transaction"
            ])
        
        return {
            'response': '\n'.join(summary_lines),
            'intent': 'Creation Transaction',
            'awaiting': 'confirmation' if not missing_fields else 'missing_fields',
            'collected_data': collected_data,
            'missing_fields': missing_fields
        }
    
    def handle_user_confirmation(self, user_response: str, session_id: str, 
                                user_id: str) -> Dict[str, Any]:
        """Handle user's response to confirmation request"""
        
        response_lower = user_response.lower()
        
        if any(word in response_lower for word in ['yes', 'confirm', 'submit', 'ok', 'proceed']):
            return self.confirm_transaction(session_id, user_id)
        
        elif any(word in response_lower for word in ['no', 'cancel', 'stop', 'abort']):
            self._clear_transaction_session(session_id)
            return {
                'response': 'Transaction cancelled. How else can I help you?',
                'intent': 'Creation Transaction',
                'cancelled': True
            }
        
        elif 'modify' in response_lower or 'change' in response_lower or 'edit' in response_lower:
            return {
                'response': 'What would you like to modify? Just tell me the changes.',
                'intent': 'Creation Transaction',
                'awaiting': 'modifications'
            }
        
        else:
            return {
                'response': 'Please confirm with "Yes" to submit, "No" to cancel, or "Modify" to make changes.',
                'intent': 'Creation Transaction',
                'awaiting': 'confirmation'
            }