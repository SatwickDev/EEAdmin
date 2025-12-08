"""
LC Conditions Validator
=======================

LLM-based validator for checking documents against LC Additional Conditions rules.

This module loads configuration from document_classification_config.yaml
and uses Azure OpenAI for parallel validation of rules against documents.
"""

import os
import json
import re
import logging
import yaml
import openai
import concurrent.futures

from app.utils.app_config import deployment_name

logger = logging.getLogger(__name__)


class LCConditionsValidator:
    """
    Validator for checking documents against LC Additional Conditions.
    
    Loads configuration from YAML and provides methods for:
    - Validating documents against parsed LC conditions rules
    - Parallel batch processing for efficiency
    - Detailed compliance/non-compliance reporting
    """
    
    def __init__(self):
        """Initialize the validator and load configuration."""
        self.config = self._load_config()
        
    def _load_config(self):
        """Load LC conditions validate configuration from YAML."""
        # Path: Additional_Conditions -> Smart_Document_Capture -> backend -> app -> EEAIAdmin -> data
        config_path = os.path.join(
            os.path.dirname(__file__), 
            '..', '..', '..', '..', 'data', 
            'document_classification_config.yaml'
        )
        logger.info(f"📁 LCConditionsValidator: Looking for config at: {config_path}")
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    full_config = yaml.safe_load(f)
                    config = full_config.get('lc_conditions_validate', {})
                    logger.info("✅ SUCCESS: Loaded lc_conditions_validate config from YAML")
                    return config
            else:
                logger.warning(f"⚠️ Config file not found at {config_path}, using defaults")
                return self._get_default_config()
        except Exception as e:
            logger.error(f"❌ Error loading config: {e}")
            return self._get_default_config()
    
    def _get_default_config(self):
        """Return default configuration values."""
        return {
            'model': 'gpt-4o',
            'temperature': 0.1,
            'max_tokens': 8000,
            'system_prompt': 'You are a precise LC validator. Return ONLY valid JSON array. No explanations.',
            'user_prompt_template': 'Validate documents against LC conditions.',
            'batch_size': 4,
            'parallel_processing': True
        }
    
    def validate_conditions(self, rules: list, documents: list, lc_data: dict) -> dict:
        """
        Validate documents against LC conditions rules.
        
        Uses parallel processing with 1 rule per batch for maximum efficiency.
        
        Args:
            rules: List of parsed LC condition rules
            documents: List of documents with extracted fields
            lc_data: LC metadata (lcNumber, beneficiary, dates, etc.)
            
        Returns:
            Dictionary with validation results and summary
        """
        if not rules:
            logger.error("❌ No validation rules provided")
            return {
                'success': False,
                'error': 'No validation rules provided',
                'validation_results': [],
                'count': 0
            }
        
        if not documents:
            logger.error("❌ No documents provided")
            return {
                'success': False,
                'error': 'No documents provided',
                'validation_results': [],
                'count': 0
            }
        
        logger.info("")
        logger.info(f"{'='*100}")
        logger.info("🚀 LC CONDITIONS VALIDATION - Using: LCConditionsValidator")
        logger.info(f"{'='*100}")
        logger.info(f"📋 Rules Count: {len(rules)}")
        logger.info(f"📄 Documents Count: {len(documents)}")
        logger.info(f"💼 LC Number: {lc_data.get('lcNumber', 'Unknown')}")
        
        # Get config values
        model = self.config.get('model', deployment_name)
        max_workers = 18  # Maximum parallel workers
        
        logger.info(f"🔧 Model: {model}")
        logger.info(f"⚡ Max Workers: {max_workers}")
        
        try:
            # Create batches - 1 rule per batch for maximum parallelism
            rule_batches = [[rule] for rule in rules]
            logger.info(f"🔢 Created {len(rule_batches)} parallel batches (1 rule each)")
            logger.info(f"{'='*100}")
            
            # Process in parallel
            all_results = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_batch = {
                    executor.submit(
                        self._validate_rule_batch, 
                        batch, 
                        documents, 
                        lc_data, 
                        idx + 1
                    ): idx
                    for idx, batch in enumerate(rule_batches)
                }
                
                logger.info(f"✅ All {len(future_to_batch)} batch jobs submitted")
                logger.info(f"⏳ Waiting for completions...")
                
                completed = 0
                for future in concurrent.futures.as_completed(future_to_batch):
                    batch_idx = future_to_batch[future]
                    completed += 1
                    try:
                        batch_results = future.result()
                        all_results.extend(batch_results)
                        logger.info(f"✅ ({completed}/{len(rule_batches)}) Batch {batch_idx + 1}: {len(batch_results)} results")
                    except Exception as e:
                        logger.error(f"❌ ({completed}/{len(rule_batches)}) Batch {batch_idx + 1} failed: {e}")
            
            logger.info("")
            logger.info(f"{'='*100}")
            logger.info("🎉 LC CONDITIONS VALIDATION - COMPLETE")
            logger.info(f"{'='*100}")
            logger.info(f"✅ Total validation results: {len(all_results)}")
            logger.info(f"📋 Rules checked: {len(rules)}")
            logger.info(f"📄 Documents analyzed: {len(documents)}")
            logger.info(f"{'='*100}")
            
            return {
                'success': True,
                'validation_results': all_results,
                'count': len(all_results),
                'rules_checked': len(rules),
                'documents_analyzed': len(documents),
                'batches_processed': len(rule_batches)
            }
            
        except Exception as e:
            logger.error(f"❌ Error in LC conditions validation: {e}")
            logger.exception("Full traceback:")
            return {
                'success': False,
                'error': str(e),
                'validation_results': [],
                'count': 0
            }
    
    def _validate_rule_batch(self, batch_rules: list, documents: list, lc_data: dict, batch_num: int) -> list:
        """
        Process a batch of rules against all documents.
        
        Args:
            batch_rules: List of rules to validate in this batch
            documents: All documents to check
            lc_data: LC metadata
            batch_num: Batch number for logging
            
        Returns:
            List of validation results
        """
        try:
            model = self.config.get('model', deployment_name)
            temperature = self.config.get('temperature', 0.1)
            max_tokens = self.config.get('max_tokens', 8000)
            system_prompt = self.config.get('system_prompt', 'You are a precise LC validator.')
            
            logger.info("")
            logger.info(f"{'='*80}")
            logger.info(f"🔄 LC VALIDATION BATCH {batch_num}")
            logger.info(f"{'='*80}")
            logger.info(f"📋 Rules: {len(batch_rules)}")
            logger.info(f"📄 Documents: {len(documents)}")
            
            # Create focused document summaries
            doc_summaries = self._create_document_summaries(documents, lc_data)
            
            # Build validation prompt
            prompt = self._build_validation_prompt(batch_rules, doc_summaries, lc_data)
            
            logger.info(f"📊 Prompt Length: {len(prompt)} characters")
            
            # Call OpenAI
            response = openai.ChatCompletion.create(
                engine=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            response_text = response["choices"][0]["message"]["content"].strip()
            logger.info(f"📊 Response Length: {len(response_text)} characters")
            
            # Extract and parse JSON
            batch_results = self._extract_json_results(response_text)
            
            if batch_results is None:
                logger.error(f"❌ Failed to parse results for batch {batch_num}")
                return []
            
            # Clean results for frontend compatibility
            cleaned_results = self._clean_results(batch_results, batch_rules)
            
            logger.info(f"✅ Batch {batch_num}: {len(cleaned_results)} validation results")
            return cleaned_results
            
        except Exception as e:
            logger.error(f"❌ Batch {batch_num} failed: {e}")
            logger.exception("Traceback:")
            return []
    
    def _create_document_summaries(self, documents: list, lc_data: dict) -> list:
        """Create focused document summaries for validation."""
        doc_summaries = []
        lc_number = lc_data.get('lcNumber', '')
        
        for doc in documents:
            summary = {
                'documentType': doc.get('documentType', 'Unknown'),
                'fileName': doc.get('fileName', ''),
                'pages': doc.get('pages', []),
                'hasLcNumber': lc_number in str(doc.get('extractedFields', {})),
                'keyFields': list(doc.get('extractedFields', {}).keys())[:10],
                'textPreview': str(doc.get('fullText', ''))[:500]
            }
            doc_summaries.append(summary)
        
        return doc_summaries
    
    def _build_validation_prompt(self, batch_rules: list, doc_summaries: list, lc_data: dict) -> str:
        """Build the validation prompt."""
        return f"""Validate documents against LC conditions. Return ONLY valid JSON array.

LC DATA:
- LC Number: {lc_data.get('lcNumber', 'Unknown')}
- Beneficiary: {lc_data.get('beneficiary', 'Unknown')}
- Issue Date: {lc_data.get('issueDate', 'Unknown')}
- Expiry Date: {lc_data.get('expiryDate', 'Unknown')}

DOCUMENTS ({len(doc_summaries)} total):
{json.dumps(doc_summaries, indent=2)}

RULES TO VALIDATE ({len(batch_rules)} rules):
{json.dumps(batch_rules, indent=2)}

CRITICAL: Validate EACH rule against ALL {len(doc_summaries)} documents.

OUTPUT FORMAT (JSON array only, no markdown):
[
  {{
    "rule": {{"code": "LC-COND-XXX", "description": "rule text"}},
    "status": "compliant" OR "non_compliant" OR "manual_review",
    "isCompliant": true OR false OR null,
    "message": "summary for all {len(doc_summaries)} documents",
    "severity": "high",
    "category": "category_name",
    "details": {{
      "compliant": [{{
        "document": "Type", 
        "fileName": "name", 
        "pages": "Pages X", 
        "reason": "why compliant",
        "fieldValue": "actual value found",
        "fieldName": "field checked"
      }}],
      "nonCompliant": [{{
        "document": "Type", 
        "fileName": "name", 
        "pages": "Pages X", 
        "reason": "why non-compliant",
        "fieldValue": "actual problematic value",
        "expectedValue": "what was expected",
        "fieldName": "field checked"
      }}],
      "requiresManualReview": [{{
        "document": "Type", 
        "fileName": "name", 
        "pages": "Pages X", 
        "reason": "why manual review needed",
        "fieldValue": "actual value (if any)",
        "fieldName": "field checked"
      }}]
    }}
  }}
]

CRITICAL: Always include actual field values checked.
Return results for all {len(batch_rules)} rules. Check every document."""
    
    def _extract_json_results(self, response_text: str) -> list:
        """Extract JSON array from response."""
        # Remove markdown code blocks
        if '```json' in response_text:
            response_text = response_text.split('```json')[1].split('```')[0].strip()
        elif '```' in response_text:
            response_text = response_text.split('```')[1].split('```')[0].strip()
        
        # Find JSON array
        json_match = re.search(r'\[\s*\{.*\}\s*\]', response_text, re.DOTALL)
        if json_match:
            response_text = json_match.group(0)
        
        try:
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            # Try auto-fix
            response_text = response_text.replace('\n', ' ')
            response_text = re.sub(r',(\s*[}\]])', r'\1', response_text)
            try:
                return json.loads(response_text)
            except json.JSONDecodeError:
                logger.error(f"❌ JSON parsing failed: {e}")
                return None
    
    def _clean_results(self, batch_results: list, batch_rules: list) -> list:
        """Clean results for frontend compatibility."""
        cleaned_results = []
        
        for result in batch_results:
            if isinstance(result, dict):
                cleaned_result = {
                    'rule': result.get('rule', {}),
                    'status': result.get('status', 'manual_review'),
                    'isCompliant': result.get('isCompliant'),
                    'message': result.get('message', 'No message provided'),
                    'severity': result.get('severity', 'high'),
                    'category': result.get('category', 'general'),
                    'documentType': 'All Documents',
                    'note': result.get('note', ''),
                    'details': result.get('details', {}),
                    'validation_type': result.get('rule', {}).get('validation_type', 'general_check')
                }
                
                # Ensure rule has required fields
                if not cleaned_result['rule'] and batch_rules:
                    rule_ref = batch_rules[0]
                    cleaned_result['rule'] = {
                        'code': rule_ref.get('code', 'LC-COND-???'),
                        'description': rule_ref.get('description', 'Unknown condition'),
                        'validation_type': rule_ref.get('validation_type', 'general_check')
                    }
                
                cleaned_results.append(cleaned_result)
        
        return cleaned_results
