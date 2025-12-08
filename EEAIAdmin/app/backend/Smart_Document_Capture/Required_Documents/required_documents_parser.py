"""
Required Documents Parser
=========================

LLM-based parser for extracting and structuring required documents
from Letter of Credit and trade finance documents.

This module loads configuration from document_classification_config.yaml
and uses Azure OpenAI for intelligent document parsing.
"""

import os
import json
import re
import logging
import yaml
import openai

from app.utils.app_config import deployment_name

logger = logging.getLogger(__name__)


class RequiredDocumentsParser:
    """
    Parser for extracting required documents from LC text using LLM.
    
    Loads configuration from YAML and provides methods for:
    - Parsing required documents text with LLM
    - Simple text-based parsing for SWIFT field 46A
    - Document categorization and prioritization
    """
    
    def __init__(self):
        """Initialize the parser and load configuration."""
        self.config = self._load_config()
        self._setup_openai()
        
    def _load_config(self):
        """Load required documents configuration from YAML."""
        # Path: Required_Documents -> Smart_Document_Capture -> backend -> app -> EEAIAdmin -> data
        config_path = os.path.join(
            os.path.dirname(__file__), 
            '..', '..', '..', '..', 'data', 
            'document_classification_config.yaml'
        )
        logger.info(f"📁 Looking for config at: {config_path}")
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    full_config = yaml.safe_load(f)
                    config = full_config.get('required_documents', {})
                    logger.info("SUCCESS: Loaded required_documents config from YAML")
                    return config
            else:
                logger.warning(f"Config file not found at {config_path}, using defaults")
                return self._get_default_config()
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return self._get_default_config()
    
    def _get_default_config(self):
        """Return default configuration values."""
        return {
            'model': 'gpt-4o',
            'temperature': 0.1,
            'max_tokens': 2000,
            'seed': 12345,
            'top_p': 0.1,
            'frequency_penalty': 0,
            'presence_penalty': 0,
            'system_prompt': 'You are a trade finance expert. Extract ALL documents from the text.',
            'user_prompt_template': 'Parse the following required documents text: {required_documents_text}',
            'response_format': 'json_object',
            'fallback_json_extraction': True,
            'default_priority': 'Mandatory',
            'default_category': 'other',
            'categories': ['trade', 'financial', 'certification', 'shipping', 'other']
        }
    
    def _setup_openai(self):
        """Setup Azure OpenAI credentials."""
        # Azure OpenAI is configured via environment variables
        # This matches the pattern used in routes.py
        pass
    
    def parse_documents(self, required_documents_text: str, document_type: str = 'Unknown') -> dict:
        """
        Parse required documents text using LLM.
        
        Args:
            required_documents_text: Raw text containing document requirements
            document_type: Type of source document (e.g., 'Letter of Credit')
            
        Returns:
            Dictionary with 'success', 'documents', and 'count' keys
        """
        if not required_documents_text or required_documents_text.strip() == '':
            return {
                'success': False,
                'error': 'No required documents text provided',
                'documents': [],
                'count': 0
            }
        
        logger.info(f"{'='*80}")
        logger.info("📄 REQUIRED DOCUMENTS PARSING - LLM REQUEST")
        logger.info(f"{'='*80}")
        logger.info(f"📋 Document Type: {document_type}")
        logger.info(f"📊 Input Text Length: {len(required_documents_text)} characters")
        logger.info(f"📝 FULL INPUT TEXT TO LLM (NO TRUNCATION):")
        logger.info(f"{'='*40} START {'='*40}")
        logger.info(required_documents_text)
        logger.info(f"{'='*40} END {'='*40}")
        
        # Extract config values
        model = self.config.get('model', deployment_name)
        temperature = self.config.get('temperature', 0.1)
        max_tokens = self.config.get('max_tokens', 2000)
        seed = self.config.get('seed', 12345)
        top_p = self.config.get('top_p', 0.1)
        frequency_penalty = self.config.get('frequency_penalty', 0)
        presence_penalty = self.config.get('presence_penalty', 0)
        system_prompt = self.config.get('system_prompt', '')
        user_prompt_template = self.config.get('user_prompt_template', '')
        response_format_type = self.config.get('response_format', 'json_object')
        fallback_json = self.config.get('fallback_json_extraction', True)
        default_priority = self.config.get('default_priority', 'Mandatory')
        default_category = self.config.get('default_category', 'other')
        
        logger.info(f"📋 Config: model={model}, temperature={temperature}, max_tokens={max_tokens}")
        logger.info(f"📝 User Prompt Template Length: {len(user_prompt_template)} chars")
        
        try:
            # Build prompt from template
            prompt = user_prompt_template.format(
                required_documents_text=required_documents_text
            )
            
            # Ensure prompt contains 'json' for response_format requirement
            if 'json' not in prompt.lower() and 'json' not in system_prompt.lower():
                prompt = prompt + "\n\nReturn your response as valid JSON."
            
            logger.info(f"📝 Prompt Length: {len(prompt)} characters")
            
            # Call OpenAI
            response = openai.ChatCompletion.create(
                engine=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                seed=seed,
                top_p=top_p,
                frequency_penalty=frequency_penalty,
                presence_penalty=presence_penalty,
                response_format={"type": response_format_type}
            )
            
            response_text = response["choices"][0]["message"]["content"].strip()
            logger.info(f"✅ Response received: {len(response_text)} characters")
            logger.info(f"📄 FULL LLM RESPONSE (NO TRUNCATION):")
            logger.info(f"{'='*40} START OF RESPONSE {'='*40}")
            logger.info(response_text)
            logger.info(f"{'='*40} END OF RESPONSE {'='*40}")
            
            # Parse JSON response
            parsed_documents = self._parse_response(response_text, fallback_json)
            
            # Clean and standardize documents
            cleaned_documents = self._clean_documents(
                parsed_documents, 
                default_priority, 
                default_category
            )
            
            logger.info(f"✅ Successfully parsed {len(cleaned_documents)} documents")
            
            return {
                'success': True,
                'documents': cleaned_documents,
                'count': len(cleaned_documents)
            }
            
        except Exception as e:
            logger.error(f"❌ Error parsing required documents: {e}")
            return {
                'success': False,
                'error': str(e),
                'documents': [],
                'count': 0
            }
    
    def _parse_response(self, response_text: str, fallback_enabled: bool = True) -> list:
        """Parse LLM response into document list."""
        try:
            parsed_response = json.loads(response_text)
            
            # Handle different response formats
            if isinstance(parsed_response, list):
                return parsed_response
            elif isinstance(parsed_response, dict):
                if 'documents' in parsed_response:
                    return parsed_response['documents']
                elif 'required_documents' in parsed_response:
                    return parsed_response['required_documents']
                elif 'items' in parsed_response:
                    return parsed_response['items']
                else:
                    return [parsed_response]
            else:
                logger.warning(f"Unexpected response format: {type(parsed_response)}")
                return []
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            
            if fallback_enabled:
                return self._fallback_json_extraction(response_text)
            return []
    
    def _fallback_json_extraction(self, text: str) -> list:
        """Attempt to extract JSON from text when direct parsing fails."""
        try:
            json_match = re.search(r'[\[{].*[\]}]', text, re.DOTALL)
            if json_match:
                fallback_response = json.loads(json_match.group(0))
                if isinstance(fallback_response, list):
                    logger.info(f"✅ Fallback extraction successful: {len(fallback_response)} documents")
                    return fallback_response
                elif isinstance(fallback_response, dict):
                    return [fallback_response]
        except Exception as e:
            logger.error(f"Fallback extraction failed: {e}")
        
        return []
    
    def _clean_documents(self, documents: list, default_priority: str, default_category: str) -> list:
        """Clean and standardize document entries."""
        cleaned = []
        
        for doc in documents:
            if isinstance(doc, dict) and doc.get('name'):
                cleaned_doc = {
                    'name': doc.get('name', '').strip(),
                    'description': doc.get('description', '').strip(),
                    'priority': doc.get('priority', default_priority),
                    'category': doc.get('category', default_category),
                    'mandatory': doc.get('priority', default_priority).lower() == 'mandatory'
                }
                cleaned.append(cleaned_doc)
            else:
                logger.warning(f"Skipped invalid document: {doc}")
        
        return cleaned


def parse_required_documents_from_text(required_documents_text: str, document_type: str = 'Unknown') -> dict:
    """
    Convenience function to parse required documents using LLM.
    
    Args:
        required_documents_text: Raw text containing document requirements
        document_type: Type of source document
        
    Returns:
        Dictionary with parsed documents
    """
    parser = RequiredDocumentsParser()
    return parser.parse_documents(required_documents_text, document_type)


def parse_required_documents_simple(docs_text: str) -> list:
    """
    Simple text-based parsing for SWIFT field 46A.
    
    This is a lightweight parser that uses keyword matching
    rather than LLM for basic document detection.
    
    Args:
        docs_text: Text from SWIFT field 46A or similar
        
    Returns:
        List of detected document type identifiers
    """
    required = []
    text_lower = docs_text.lower()
    
    # Document patterns to detect
    document_patterns = {
        'commercial_invoice': ['commercial invoice', 'invoice'],
        'packing_list': ['packing list', 'packing note'],
        'bill_of_lading': ['bill of lading', 'b/l', 'bl'],
        'certificate_of_origin': ['certificate of origin', 'c/o', 'origin certificate'],
        'insurance_policy': ['insurance policy', 'insurance certificate', 'marine insurance'],
        'inspection_certificate': ['inspection certificate', 'inspection report'],
        'weight_list': ['weight list', 'weight note'],
        'beneficiary_certificate': ['beneficiary certificate'],
        'draft': ['draft', 'sight draft', 'usance draft'],
        'airway_bill': ['airway bill', 'air waybill', 'awb'],
        'phytosanitary_certificate': ['phytosanitary', 'sanitary certificate'],
        'fumigation_certificate': ['fumigation certificate'],
        'quality_certificate': ['quality certificate', 'quality report'],
        'analysis_certificate': ['analysis certificate', 'certificate of analysis']
    }
    
    for doc_id, patterns in document_patterns.items():
        for pattern in patterns:
            if pattern in text_lower:
                if doc_id not in required:
                    required.append(doc_id)
                break
    
    return required
