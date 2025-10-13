"""
Pure LLM-Driven Conversational Transaction Handler - No Static Logic
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
    """Fully LLM-driven transaction handler"""
    
    def __init__(self, db):
        self.db = db
    
    def process_creation_intent(self, user_query: str, session_id: str, 
                               user_id: str, context: List[Dict], 
                               repository: str = None) -> Dict[str, Any]:
        """
        Process transaction using LLM for all decisions
        """
        try:
            # Get session
            session = self._get_transaction_session(session_id, user_id)
            
            # Check if user wants to populate form after confirmation
            query_lower = user_query.lower()
            logger.info(f"Checking session status: {session.get('status', 'none')}, awaiting_population: {session.get('awaiting_population', False)}")
            
            if session.get('awaiting_population') or session.get('status') == 'confirmed_awaiting_population':
                logger.info(f"Session is awaiting population decision. User query: {query_lower}")
                
                if any(word in query_lower for word in ['populate', 'fill', 'form', 'yes', 'load']):
                    # User wants to populate the form
                    transaction_data = session.get('confirmed_transaction', {})
                    transaction_type = session.get('transaction_type', 'import_lc')
                    
                    logger.info(f"User requested form population. Transaction data: {transaction_data}")
                    
                    # Clear the awaiting flag
                    session['awaiting_population'] = False
                    session['status'] = 'populated'
                    self._save_transaction_session(session_id, session)
                    
                    # Return with form data for population
                    return self._execute_transaction(transaction_type, transaction_data, user_id)
                elif any(word in query_lower for word in ['no', 'cancel', 'skip', 'later']):
                    # User doesn't want to populate
                    session['awaiting_population'] = False
                    session['status'] = 'completed_no_population'
                    self._save_transaction_session(session_id, session)
                    return {
                        'response': "Transaction saved. You can continue with other tasks.",
                        'intent': 'Creation Transaction'
                    }
            
            # Build context for LLM
            context_text = self._build_context(context)
            
            # Let LLM handle everything
            prompt = f"""
            You are a transaction processing assistant. Analyze the conversation and determine what to do.
            
            User Query: {user_query}
            Repository: {repository or 'Not specified'}
            Current Session Data: {json.dumps(sanitize_for_json(session))}
            
            Conversation History:
            {context_text}
            
            IMPORTANT RULES:
            1. Check if user is confirming a transaction (words like: yes, confirm, proceed, submit, ok, approved)
            2. If confirming AND there's transaction data ready, set action to "execute"
            3. Look for the most recent transaction summary in conversation history
            4. If user modifies data after showing summary, update and show new confirmation
            
            Analyze and return JSON with one of these actions:
            
            1. If user wants to create a similar transaction:
               - Find the exact LC data from HTML tables in conversation
               - If LC number specified (like LC2023002), extract that row's data
               - If no LC specified but multiple available, ask which one
               
            2. Extract transaction data from tables:
               - Find exact values from HTML table rows
               - Don't generate new data
               - Update expired dates to future dates
               
            3. If user confirms (yes/confirm/proceed/submit) and transaction data exists:
               - Set action to "execute"
               - Include all transaction data from the most recent summary
               
            4. Handle the request appropriately
            
            Return JSON in this format:
            {{
                "action": "collect_data|ask_confirmation|ask_which_lc|execute|need_info",
                "transaction_type": "import_lc|payment|forex",
                "data": {{extracted fields from most recent transaction summary}},
                "message": "response to user",
                "missing_fields": ["list of missing required fields"],
                "lc_options": ["LC2023002", "LC2024002"] // if multiple LCs available
            }}
            """
            
            response = openai.ChatCompletion.create(
                engine=deployment_name,
                messages=[
                    {"role": "system", "content": "You are a transaction assistant. Analyze and return structured JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1000
            )
            
            # Check if response exists and has content
            if not response or not response.choices or not response.choices[0].message.content:
                logger.warning("Empty response from OpenAI")
                return {
                    'response': 'I need more information to help you create a transaction. Could you specify what type of transaction you want to create?',
                    'intent': 'Creation Transaction'
                }
            
            response_content = response.choices[0].message.content.strip()
            
            # Try to extract JSON from the response
            try:
                # Handle cases where response might have markdown code blocks
                if '```json' in response_content:
                    response_content = response_content.split('```json')[1].split('```')[0].strip()
                elif '```' in response_content:
                    response_content = response_content.split('```')[1].split('```')[0].strip()
                
                result = json.loads(response_content)
            except json.JSONDecodeError as json_error:
                logger.error(f"JSON parsing error: {json_error}, Response: {response_content[:500]}")
                # Fallback response when JSON parsing fails
                return {
                    'response': 'I understand you want to create a transaction. Could you specify:\n1. Transaction type (Import LC, Export LC, Bank Guarantee, etc.)\n2. Key details like amount, parties involved, and dates?',
                    'intent': 'Creation Transaction',
                    'parse_error': str(json_error)
                }
            
            # Handle based on LLM decision
            if result['action'] == 'ask_which_lc':
                return {
                    'response': result.get('message', 'Which LC would you like to use?'),
                    'intent': 'Creation Transaction',
                    'lc_options': result.get('lc_options', [])
                }
            
            elif result['action'] == 'collect_data':
                # Update session with collected data
                session['transaction_type'] = result.get('transaction_type', 'import_lc')
                session['collected_data'] = {
                    **session.get('collected_data', {}),
                    **result.get('data', {})
                }
                self._save_transaction_session(session_id, session)
                
                # Check if we need more info
                if result.get('missing_fields'):
                    return {
                        'response': result.get('message', f"Please provide: {', '.join(result['missing_fields'])}"),
                        'intent': 'Creation Transaction',
                        'missing_fields': result['missing_fields']
                    }
                else:
                    # All data collected, ask confirmation
                    return self._format_confirmation(session['transaction_type'], session['collected_data'])
            
            elif result['action'] == 'ask_confirmation':
                return self._format_confirmation(
                    result.get('transaction_type', 'import_lc'),
                    result.get('data', {})
                )
            
            elif result['action'] == 'execute':
                # User confirmed - don't auto-populate, ask explicitly
                transaction_data = result.get('data', session.get('collected_data', {}))
                
                # Store confirmed transaction for later population
                session['confirmed_transaction'] = transaction_data
                session['transaction_type'] = result.get('transaction_type', 'import_lc')
                session['awaiting_population'] = True
                session['status'] = 'confirmed_awaiting_population'
                self._save_transaction_session(session_id, session)
                
                logger.info(f"Transaction confirmed, awaiting population request. Session: {session_id}")
                
                # Return confirmation without auto-population
                return {
                    'response': "✅ **Transaction confirmed successfully!**\n\nThe transaction has been created. Would you like to populate this data into the form?\n\nReply 'populate' or 'fill form' to auto-fill the form fields.",
                    'intent': 'Creation Transaction',
                    'success': True,
                    'transaction_confirmed': True,
                    'awaiting_form_population': True
                }
            
            else:
                return {
                    'response': result.get('message', 'How can I help you with your transaction?'),
                    'intent': 'Creation Transaction'
                }
                
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            return {
                'response': 'I encountered an error. Please try again.',
                'error': str(e)
            }
    
    def _build_context(self, context: List[Dict]) -> str:
        """Build context string from conversation history"""
        context_text = ""
        for ctx in reversed(context[-5:] if context else []):
            if 'message' in ctx:
                context_text += f"User: {ctx['message']}\n"
            if 'response' in ctx:
                # Include full response for table data
                context_text += f"Assistant: {ctx['response']}\n"
        return context_text
    
    def _format_confirmation(self, transaction_type: str, data: Dict) -> Dict[str, Any]:
        """Format confirmation message"""
        summary = f"**{transaction_type.replace('_', ' ').title()} Transaction Summary:**\n\n"
        
        for key, value in data.items():
            readable_key = key.replace('_', ' ').title()
            if isinstance(value, (int, float)) and 'amount' in key:
                value = f"{value:,.2f}"
            summary += f"• **{readable_key}:** {value}\n"
        
        summary += "\n✅ **Ready to submit?**\n\nReply with 'Yes' to confirm or 'No' to cancel."
        
        return {
            'response': summary,
            'intent': 'Creation Transaction',
            'awaiting': 'confirmation',
            'transaction_data': data,
            'action_buttons': [
                {'label': '✅ Confirm', 'action': 'confirm_transaction'},
                {'label': '❌ Cancel', 'action': 'cancel_transaction'}
            ]
        }
    
    def _execute_transaction(self, transaction_type: str, data: Dict, user_id: str) -> Dict[str, Any]:
        """Return form population data instead of executing in database"""
        try:
            logger.info(f"Executing transaction with data: {data}")
            
            # Add metadata for form population
            data['transaction_type'] = transaction_type
            data['created_by'] = user_id
            data['created_at'] = datetime.utcnow().isoformat()
            
            # Generate a temporary transaction ID for reference
            transaction_id = f"{transaction_type.upper()}{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # Keep the original field names for form population
            # The frontend will handle the mapping
            form_data = {
                'lc_number': data.get('lc_number', data.get('Lc Number', '')),
                'applicant': data.get('applicant', data.get('Applicant', '')),
                'beneficiary': data.get('beneficiary', data.get('Beneficiary', '')),
                'amount': str(data.get('amount', data.get('Amount', ''))),
                'currency': data.get('currency', data.get('Currency', '')),
                'issue_date': data.get('issue_date', data.get('Issue Date', '')),
                'expiry_date': data.get('expiry_date', data.get('Expiry Date', '')),
                'country': data.get('country', data.get('Country', '')),
                'product_type': data.get('product_type', data.get('Product Type', '')),
                'status': data.get('status', data.get('Status', ''))
            }
            
            # Remove empty values
            form_data = {k: v for k, v in form_data.items() if v}
            
            logger.info(f"Form data prepared: {form_data}")
            
            return {
                'response': f"✅ **Transaction successfully created!**\n\nThe form has been populated with the transaction data.",
                'intent': 'Creation Transaction',
                'form_data': form_data,
                'success': True,
                'transaction_id': transaction_id,
                'transaction_type': transaction_type
            }
            
        except Exception as e:
            logger.error(f"Form population error: {str(e)}")
            return {
                'response': f'Failed to prepare form data: {str(e)}',
                'intent': 'Creation Transaction',
                'success': False
            }
    
    def _get_transaction_session(self, session_id: str, user_id: str) -> Dict:
        """Get or create session"""
        session = self.db.transaction_sessions.find_one({
            'session_id': session_id
        })
        if session and 'data' in session:
            logger.info(f"Retrieved session for {session_id}: {session.get('data', {}).get('status', 'no status')}")
            return session.get('data', {})
        return {}
    
    def _save_transaction_session(self, session_id: str, data: Dict):
        """Save session"""
        # If data is wrapped in 'data' key, unwrap it
        if 'data' in data and isinstance(data['data'], dict):
            session_data = data['data']
        else:
            session_data = data
            
        logger.info(f"Saving session {session_id} with status: {session_data.get('status', 'no status')}")
        
        self.db.transaction_sessions.update_one(
            {'session_id': session_id},
            {'$set': {
                'data': session_data,
                'updated_at': datetime.utcnow().isoformat()
            }},
            upsert=True
        )