"""
LC Conditions Parser
====================

LLM-based parser for extracting structured validation rules from
LC Additional Conditions text.

This module loads configuration from document_classification_config.yaml
and uses Azure OpenAI to parse conditions into atomic validation rules.
"""

import os
import json
import re
import logging
import yaml
import openai

from app.utils.app_config import deployment_name

logger = logging.getLogger(__name__)


class LCConditionsParser:
    """
    Parser for extracting validation rules from LC Additional Conditions text.
    
    Loads configuration from YAML and provides methods for:
    - Parsing additional conditions into structured rules
    - Breaking down complex conditions into atomic requirements
    - Categorizing rules by validation type
    """
    
    def __init__(self):
        """Initialize the parser and load configuration."""
        self.config = self._load_config()
        
    def _load_config(self):
        """Load LC conditions parse configuration from YAML."""
        # Path: Additional_Conditions -> Smart_Document_Capture -> backend -> app -> EEAIAdmin -> data
        config_path = os.path.join(
            os.path.dirname(__file__), 
            '..', '..', '..', '..', 'data', 
            'document_classification_config.yaml'
        )
        logger.info(f"📁 LCConditionsParser: Looking for config at: {config_path}")
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    full_config = yaml.safe_load(f)
                    config = full_config.get('lc_conditions_parse', {})
                    logger.info("✅ SUCCESS: Loaded lc_conditions_parse config from YAML")
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
            'max_tokens': 15000,
            'seed': 12345,
            'top_p': 0.1,
            'frequency_penalty': 0,
            'presence_penalty': 0,
            'system_prompt': 'You are an expert LC conditions parser. Extract ALL validation rules from the text. Return a JSON ARRAY.',
            'user_prompt_template': 'Parse the following LC conditions into validation rules:\n\n{additional_conditions_text}',
            'response_format': 'text',
            'expected_rules_min': 15,
            'expected_rules_max': 30
        }
    
    def parse_conditions(self, additional_conditions_text: str, lc_number: str = 'Unknown') -> dict:
        """
        Parse LC Additional Conditions text into structured validation rules.
        
        Args:
            additional_conditions_text: Raw text containing LC additional conditions
            lc_number: LC number for reference in rules
            
        Returns:
            Dictionary with 'success', 'rules', 'count', and 'lc_number' keys
        """
        if not additional_conditions_text or additional_conditions_text.strip() == '':
            logger.error("❌ No additional conditions text provided")
            return {
                'success': False,
                'error': 'No additional conditions text provided',
                'rules': [],
                'count': 0,
                'lc_number': lc_number
            }
        
        logger.info("")
        logger.info(f"{'='*100}")
        logger.info("📋 LC CONDITIONS PARSING - Using: LCConditionsParser")
        logger.info(f"{'='*100}")
        logger.info(f"📋 LC Number: {lc_number}")
        logger.info(f"📊 Input Text Length: {len(additional_conditions_text)} characters")
        logger.info(f"📊 Input Text Lines: {len(additional_conditions_text.splitlines())} lines")
        
        # Log line-by-line analysis
        lines = additional_conditions_text.splitlines()
        logger.info(f"📋 Line-by-line analysis:")
        for i, line in enumerate(lines, 1):
            if line.strip():
                logger.info(f"   Line {i:2d}: {line.strip()}")
        
        # Extract config values
        model = self.config.get('model', deployment_name)
        temperature = self.config.get('temperature', 0.1)
        max_tokens = self.config.get('max_tokens', 15000)
        seed = self.config.get('seed', 12345)
        top_p = self.config.get('top_p', 0.1)
        frequency_penalty = self.config.get('frequency_penalty', 0)
        presence_penalty = self.config.get('presence_penalty', 0)
        system_prompt = self.config.get('system_prompt', '')
        user_prompt_template = self.config.get('user_prompt_template', '')
        
        logger.info("")
        logger.info(f"{'='*100}")
        logger.info("🔧 LC CONDITIONS PARSING - CONFIGURATION")
        logger.info(f"{'='*100}")
        logger.info(f"   Model: {model}")
        logger.info(f"   Temperature: {temperature}")
        logger.info(f"   Max Tokens: {max_tokens}")
        logger.info(f"   Seed: {seed}")
        logger.info(f"   Top P: {top_p}")
        logger.info(f"🌐 Endpoint: {openai.api_base}")
        logger.info(f"{'='*100}")
        
        try:
            # Build prompt from template
            prompt = user_prompt_template.format(
                lc_number=lc_number,
                additional_conditions_text=additional_conditions_text
            )
            
            logger.info("")
            logger.info(f"{'='*100}")
            logger.info("📤 LC CONDITIONS PARSING - CALLING AZURE OPENAI")
            logger.info(f"{'='*100}")
            logger.info(f"📊 Prompt Length: {len(prompt)} characters")
            logger.info(f"💬 System Message: {system_prompt[:200]}...")
            logger.info(f"{'='*100}")
            
            # Call OpenAI - don't use response_format to allow JSON arrays
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
                presence_penalty=presence_penalty
            )
            
            response_text = response["choices"][0]["message"]["content"].strip()
            
            logger.info("")
            logger.info(f"{'='*100}")
            logger.info("✅ LC CONDITIONS PARSING - RESPONSE RECEIVED")
            logger.info(f"{'='*100}")
            logger.info(f"📊 Response Length: {len(response_text)} characters")
            
            # Extract and parse JSON
            parsed_rules = self._extract_json_array(response_text)
            
            if parsed_rules is None:
                return {
                    'success': False,
                    'error': 'Failed to parse LLM response as JSON',
                    'raw_response': response_text[:500],
                    'rules': [],
                    'count': 0,
                    'lc_number': lc_number
                }
            
            # Clean and normalize rules
            cleaned_rules = self._clean_rules(parsed_rules, lc_number)
            
            logger.info("")
            logger.info(f"{'='*100}")
            logger.info("🎉 LC CONDITIONS PARSING - COMPLETE")
            logger.info(f"{'='*100}")
            logger.info(f"✅ Success: True")
            logger.info(f"📊 Total rules: {len(cleaned_rules)}")
            logger.info(f"🏷️ LC Number: {lc_number}")
            logger.info(f"{'='*100}")
            
            return {
                'success': True,
                'rules': cleaned_rules,
                'count': len(cleaned_rules),
                'lc_number': lc_number
            }
            
        except Exception as e:
            logger.error("")
            logger.error(f"{'='*100}")
            logger.error("❌ LC CONDITIONS PARSING - ERROR")
            logger.error(f"{'='*100}")
            logger.error(f"❌ Error Type: {type(e).__name__}")
            logger.error(f"❌ Error Message: {str(e)}")
            logger.exception("❌ Full traceback:")
            logger.error(f"{'='*100}")
            
            return {
                'success': False,
                'error': str(e),
                'rules': [],
                'count': 0,
                'lc_number': lc_number
            }
    
    def _extract_json_array(self, response_text: str) -> list:
        """
        Extract JSON array from LLM response.
        
        Handles markdown code blocks and various JSON formats.
        """
        logger.info("")
        logger.info(f"{'='*80}")
        logger.info("🔍 EXTRACTING JSON FROM RESPONSE")
        logger.info(f"{'='*80}")
        
        original_response = response_text
        
        # Remove markdown code blocks
        if '```json' in response_text:
            response_text = response_text.split('```json')[1].split('```')[0].strip()
            logger.info("📝 Extracted JSON from markdown code block")
        elif '```' in response_text:
            response_text = response_text.split('```')[1].split('```')[0].strip()
            logger.info("📝 Extracted JSON from code block")
        
        # Look for JSON array pattern
        json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
        if json_match:
            response_text = json_match.group(0)
            logger.info("🔍 Found JSON array in response")
        else:
            # Check for single object and wrap in array
            object_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if object_match:
                response_text = '[' + object_match.group(0) + ']'
                logger.info("🔍 Found single JSON object, wrapping in array")
            else:
                logger.error("❌ No valid JSON found in response")
                return None
        
        logger.info(f"📊 Cleaned JSON Length: {len(response_text)} characters")
        
        # Parse JSON
        try:
            parsed_rules = json.loads(response_text)
            logger.info(f"✅ JSON parsing successful")
            logger.info(f"📊 Parsed rules type: {type(parsed_rules).__name__}")
            
            # Ensure it's a list
            if not isinstance(parsed_rules, list):
                logger.warning(f"⚠️ Expected list, got {type(parsed_rules).__name__}. Converting.")
                parsed_rules = [parsed_rules] if isinstance(parsed_rules, dict) else []
            
            logger.info(f"📊 Rules count: {len(parsed_rules)}")
            return parsed_rules
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON parsing failed: {e}")
            return None
    
    def _clean_rules(self, parsed_rules: list, lc_number: str) -> list:
        """
        Clean and normalize parsed rules.
        
        Ensures all rules have required fields with proper defaults.
        """
        logger.info("")
        logger.info(f"{'='*80}")
        logger.info("🧹 CLEANING PARSED RULES")
        logger.info(f"{'='*80}")
        logger.info(f"📊 Total rules to clean: {len(parsed_rules)}")
        
        cleaned_rules = []
        
        for idx, rule in enumerate(parsed_rules):
            if isinstance(rule, dict):
                cleaned_rule = {
                    'id': rule.get('id', f'lc-cond-{idx+1:03d}'),
                    'code': rule.get('code', f'LC-COND-{idx+1:03d}'),
                    'category': rule.get('category', 'general'),
                    'description': rule.get('description', '').strip(),
                    'field_affected': rule.get('field_affected', 'all_documents'),
                    'validation_type': rule.get('validation_type', 'general_check'),
                    'expected_value': rule.get('expected_value', ''),
                    'severity': rule.get('severity', 'high'),
                    'actionable': rule.get('actionable', True),
                    'source': 'lc_conditions',
                    'lc_number': lc_number
                }
                cleaned_rules.append(cleaned_rule)
                logger.info(f"   ✅ Rule {idx + 1}: {cleaned_rule['code']} - {cleaned_rule['description'][:60]}...")
            else:
                logger.warning(f"   ⚠️ Skipping non-dict rule {idx + 1}: {type(rule).__name__}")
        
        logger.info(f"✅ Successfully cleaned: {len(cleaned_rules)}/{len(parsed_rules)} rules")
        return cleaned_rules
