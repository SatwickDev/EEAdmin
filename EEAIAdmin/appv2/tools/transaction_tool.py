"""
Transaction Tool - Microservice for handling financial transactions
"""

from typing import Dict, Any, Optional
import logging
from datetime import datetime
from pydantic import Field
import json

from .base_tool import BaseIntentTool, ToolOutput, ToolInput
from appv2.chains.transaction_chain import TransactionValidationChain
from appv2.utils.app_config import get_database_engine

logger = logging.getLogger(__name__)

class TransactionInput(ToolInput):
    """Input model for transaction tool"""
    transaction_type: str = Field(description="Type of transaction (transfer, payment, LC, guarantee)")
    amount: Optional[float] = Field(default=None, description="Transaction amount")
    currency: Optional[str] = Field(default="USD", description="Currency code")
    beneficiary: Optional[Dict[str, Any]] = Field(default=None, description="Beneficiary details")
    documents: Optional[List[str]] = Field(default=None, description="Associated documents")

class TransactionTool(BaseIntentTool):
    """
    Tool/Microservice for handling financial transactions
    Supports LC, Bank Guarantees, Payments, Transfers
    """
    
    name: str = "transaction_tool"
    description: str = """Tool for processing financial transactions including:
    - Letter of Credit (LC) creation and management
    - Bank Guarantee issuance
    - Payment processing
    - Fund transfers
    Use this when users want to create, modify, or process any financial transaction."""
    args_schema = TransactionInput
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.validation_chain = TransactionValidationChain()
        self.engine = None
    
    def _get_engine(self, repository: Optional[str] = None):
        """Get appropriate database engine based on repository"""
        if not self.engine:
            self.engine = get_database_engine(repository)
        return self.engine
    
    def _process_intent(self,
                       query: str,
                       context: Optional[Dict[str, Any]],
                       user_id: str,
                       repository: Optional[str],
                       session_id: Optional[str]) -> ToolOutput:
        """
        Process transaction intent
        """
        try:
            logger.info(f"Processing transaction for user {user_id} in repository {repository}")
            
            # Extract transaction details from query using LangChain
            transaction_details = self._extract_transaction_details(query, context)
            
            # Validate transaction
            validation_result = self.validation_chain.validate(
                transaction_details,
                repository=repository
            )
            
            if not validation_result['valid']:
                return ToolOutput(
                    success=False,
                    data=None,
                    error=validation_result.get('reason', 'Transaction validation failed'),
                    metadata={'validation_errors': validation_result.get('errors', [])}
                )
            
            # Process based on transaction type
            transaction_type = transaction_details.get('transaction_type', 'payment')
            
            if transaction_type == 'lc':
                result = self._process_lc(transaction_details, user_id, repository)
            elif transaction_type == 'guarantee':
                result = self._process_guarantee(transaction_details, user_id, repository)
            elif transaction_type == 'payment':
                result = self._process_payment(transaction_details, user_id, repository)
            elif transaction_type == 'transfer':
                result = self._process_transfer(transaction_details, user_id, repository)
            else:
                return ToolOutput(
                    success=False,
                    data=None,
                    error=f"Unsupported transaction type: {transaction_type}"
                )
            
            # Log transaction for audit
            self._log_transaction(
                user_id=user_id,
                transaction_type=transaction_type,
                details=transaction_details,
                result=result,
                repository=repository
            )
            
            return ToolOutput(
                success=result.get('success', False),
                data=result,
                metadata={
                    'transaction_id': result.get('transaction_id'),
                    'timestamp': datetime.now().isoformat(),
                    'repository': repository
                }
            )
            
        except Exception as e:
            logger.error(f"Error processing transaction: {str(e)}")
            return ToolOutput(
                success=False,
                data=None,
                error=str(e)
            )
    
    def _extract_transaction_details(self, query: str, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract transaction details from query using LLM"""
        from appv2.chains.extraction_chain import TransactionExtractionChain
        
        extractor = TransactionExtractionChain()
        details = extractor.extract(query, context)
        
        # Merge with any provided context
        if context:
            details.update(context)
        
        return details
    
    def _process_lc(self, details: Dict[str, Any], user_id: str, repository: str) -> Dict[str, Any]:
        """Process Letter of Credit transaction"""
        try:
            engine = self._get_engine(repository)
            
            # Generate LC number
            lc_number = self._generate_lc_number()
            
            # Prepare LC data
            lc_data = {
                'lc_number': lc_number,
                'applicant': details.get('applicant', user_id),
                'beneficiary': json.dumps(details.get('beneficiary', {})),
                'amount': details.get('amount'),
                'currency': details.get('currency', 'USD'),
                'expiry_date': details.get('expiry_date'),
                'terms': details.get('terms', ''),
                'documents_required': json.dumps(details.get('documents', [])),
                'created_by': user_id,
                'created_at': datetime.now(),
                'status': 'DRAFT'
            }
            
            # Insert into database
            with engine.connect() as conn:
                result = conn.execute(
                    text("""
                    INSERT INTO letter_of_credit 
                    (lc_number, applicant, beneficiary, amount, currency, 
                     expiry_date, terms, documents_required, created_by, created_at, status)
                    VALUES 
                    (:lc_number, :applicant, :beneficiary, :amount, :currency,
                     :expiry_date, :terms, :documents_required, :created_by, :created_at, :status)
                    """),
                    lc_data
                )
                conn.commit()
            
            return {
                'success': True,
                'transaction_id': lc_number,
                'type': 'Letter of Credit',
                'message': f'LC {lc_number} created successfully',
                'details': lc_data
            }
            
        except Exception as e:
            logger.error(f"Error processing LC: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _process_guarantee(self, details: Dict[str, Any], user_id: str, repository: str) -> Dict[str, Any]:
        """Process Bank Guarantee transaction"""
        try:
            engine = self._get_engine(repository)
            
            # Generate guarantee number
            guarantee_number = self._generate_guarantee_number()
            
            # Prepare guarantee data
            guarantee_data = {
                'guarantee_number': guarantee_number,
                'applicant': details.get('applicant', user_id),
                'beneficiary': json.dumps(details.get('beneficiary', {})),
                'amount': details.get('amount'),
                'currency': details.get('currency', 'USD'),
                'guarantee_type': details.get('guarantee_type', 'PERFORMANCE'),
                'expiry_date': details.get('expiry_date'),
                'purpose': details.get('purpose', ''),
                'created_by': user_id,
                'created_at': datetime.now(),
                'status': 'DRAFT'
            }
            
            # Insert into database
            with engine.connect() as conn:
                result = conn.execute(
                    text("""
                    INSERT INTO bank_guarantee
                    (guarantee_number, applicant, beneficiary, amount, currency,
                     guarantee_type, expiry_date, purpose, created_by, created_at, status)
                    VALUES
                    (:guarantee_number, :applicant, :beneficiary, :amount, :currency,
                     :guarantee_type, :expiry_date, :purpose, :created_by, :created_at, :status)
                    """),
                    guarantee_data
                )
                conn.commit()
            
            return {
                'success': True,
                'transaction_id': guarantee_number,
                'type': 'Bank Guarantee',
                'message': f'Bank Guarantee {guarantee_number} created successfully',
                'details': guarantee_data
            }
            
        except Exception as e:
            logger.error(f"Error processing guarantee: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _process_payment(self, details: Dict[str, Any], user_id: str, repository: str) -> Dict[str, Any]:
        """Process payment transaction"""
        try:
            # Generate payment reference
            payment_ref = self._generate_payment_reference()
            
            payment_data = {
                'reference': payment_ref,
                'amount': details.get('amount'),
                'currency': details.get('currency', 'USD'),
                'beneficiary': details.get('beneficiary'),
                'purpose': details.get('purpose', 'Payment'),
                'status': 'PENDING',
                'initiated_by': user_id,
                'initiated_at': datetime.now().isoformat()
            }
            
            # Here you would integrate with actual payment gateway
            # For now, we'll simulate success
            
            return {
                'success': True,
                'transaction_id': payment_ref,
                'type': 'Payment',
                'message': f'Payment {payment_ref} initiated successfully',
                'details': payment_data
            }
            
        except Exception as e:
            logger.error(f"Error processing payment: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _process_transfer(self, details: Dict[str, Any], user_id: str, repository: str) -> Dict[str, Any]:
        """Process fund transfer"""
        try:
            # Generate transfer reference
            transfer_ref = self._generate_transfer_reference()
            
            transfer_data = {
                'reference': transfer_ref,
                'from_account': details.get('from_account'),
                'to_account': details.get('to_account'),
                'amount': details.get('amount'),
                'currency': details.get('currency', 'USD'),
                'purpose': details.get('purpose', 'Transfer'),
                'status': 'PENDING',
                'initiated_by': user_id,
                'initiated_at': datetime.now().isoformat()
            }
            
            # Here you would integrate with core banking system
            # For now, we'll simulate success
            
            return {
                'success': True,
                'transaction_id': transfer_ref,
                'type': 'Transfer',
                'message': f'Transfer {transfer_ref} initiated successfully',
                'details': transfer_data
            }
            
        except Exception as e:
            logger.error(f"Error processing transfer: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _generate_lc_number(self) -> str:
        """Generate unique LC number"""
        import uuid
        return f"LC{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:8].upper()}"
    
    def _generate_guarantee_number(self) -> str:
        """Generate unique guarantee number"""
        import uuid
        return f"BG{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:8].upper()}"
    
    def _generate_payment_reference(self) -> str:
        """Generate unique payment reference"""
        import uuid
        return f"PAY{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:8].upper()}"
    
    def _generate_transfer_reference(self) -> str:
        """Generate unique transfer reference"""
        import uuid
        return f"TRF{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:8].upper()}"
    
    def _log_transaction(self, user_id: str, transaction_type: str, 
                        details: Dict[str, Any], result: Dict[str, Any],
                        repository: str):
        """Log transaction for audit trail"""
        try:
            # Store in MongoDB or audit log
            audit_entry = {
                'user_id': user_id,
                'transaction_type': transaction_type,
                'details': details,
                'result': result,
                'repository': repository,
                'timestamp': datetime.now().isoformat()
            }
            
            # Here you would save to audit database
            logger.info(f"Transaction audit: {json.dumps(audit_entry)}")
            
        except Exception as e:
            logger.error(f"Failed to log transaction: {str(e)}")

# Microservice endpoint if running standalone
if __name__ == "__main__":
    tool = TransactionTool()
    # Run as microservice on port 8002
    tool.as_microservice(port=8002)