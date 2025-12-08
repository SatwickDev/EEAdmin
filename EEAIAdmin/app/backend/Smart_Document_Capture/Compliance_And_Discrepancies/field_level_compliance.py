"""
Field-Level Compliance Analyzer
================================

RULE-BASED COMPLIANCE VALIDATION during document classification.
Uses document-specific discrepancy rules from discrepancy_rules.json
to perform comprehensive field-level compliance analysis.

This is different from LLMComplianceEngine which handles Tab 3 Standard Rules
(document-to-LC comparison and cross-document checks).

This module:
- Validates individual extracted fields
- Loads prompts and settings from document_classification_config.yaml
- Uses document-type specific rule application
- Returns unified compliance result for UI display

Author: Field-Level Compliance System
Date: December 2025
"""

import os
import json
import time
import logging
import yaml
import openai

from app.utils.app_config import deployment_name

logger = logging.getLogger(__name__)

# Global storage for unified compliance result
_unified_compliance_result = {}


class FieldLevelComplianceAnalyzer:
    """
    Analyzer for field-level compliance validation during document classification.
    
    Uses discrepancy rules and GPT-4o to validate extracted fields
    against document-specific compliance requirements.
    """
    
    def __init__(self):
        """Initialize the analyzer and load configuration."""
        self.config = self._load_config()
        self.deployment_name = deployment_name
        
    def _load_config(self):
        """Load compliance configuration from YAML."""
        config_path = os.path.join(
            os.path.dirname(__file__), 
            '..', '..', '..', 'data', 
            'document_classification_config.yaml'
        )
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    full_config = yaml.safe_load(f)
                    config = full_config.get('compliance', {})
                    logger.info("SUCCESS: Loaded compliance config from YAML")
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
            'max_tokens': 8000,
            'check_mandatory_fields': True,
            'check_conditional_fields': True,
            'check_data_quality': True,
            'check_format_validity': True,
            'severity_levels': ['critical', 'warning', 'info'],
            'system_prompt': 'You are an expert trade finance compliance analyst. Focus on identifying actual discrepancies against the provided rules.'
        }
    
    def _load_discrepancy_rules(self, document_type: str) -> list:
        """Load discrepancy rules for the specified document type."""
        rules_path = os.path.join(
            os.path.dirname(__file__),
            '..', '..', '..', 'data',
            'discrepancy_rules.json'
        )
        
        try:
            if not os.path.exists(rules_path):
                logger.warning(f"Discrepancy rules file not found at {rules_path}")
                return []
            
            with open(rules_path, 'r', encoding='utf-8') as f:
                rules_data = json.load(f)
            
            # Handle nested structure - rules might be under 'rules' key
            if isinstance(rules_data, dict):
                all_rules = rules_data.get('rules', [])
            elif isinstance(rules_data, list):
                all_rules = rules_data
            else:
                logger.warning(f"Unexpected rules format: {type(rules_data)}")
                return []
            
            # Filter rules for the document type
            if not document_type:
                return []
            
            document_type_lower = document_type.lower()
            document_rules = []
            
            for rule in all_rules:
                # Skip if rule is not a dict
                if not isinstance(rule, dict):
                    continue
                    
                rule_doc_types = rule.get('documentType', [])
                if isinstance(rule_doc_types, str):
                    rule_doc_types = [rule_doc_types]
                
                for rule_type in rule_doc_types:
                    if rule_type.lower() in document_type_lower or document_type_lower in rule_type.lower():
                        document_rules.append(rule)
                        break
            
            logger.info(f"RULES: Loaded {len(document_rules)} rules for document type: {document_type}")
            return document_rules
            
        except Exception as e:
            logger.error(f"ERROR: Failed to load discrepancy rules: {e}")
            return []
    
    def analyze(self, fields: dict, document_type: str = None) -> dict:
        """
        Analyze extracted fields for compliance violations.
        
        Args:
            fields: Dictionary of extracted fields to analyze
            document_type: The classified document type for loading specific rules
            
        Returns:
            Dictionary with field-level compliance results
        """
        global _unified_compliance_result
        
        start_time = time.time()
        
        logger.info("")
        logger.info(f"{'='*80}")
        logger.info("📋 FIELD-LEVEL COMPLIANCE ANALYSIS - USING MODULAR ANALYZER")
        logger.info(f"{'='*80}")
        logger.info(f"📊 Document Type: {document_type}")
        logger.info(f"📊 Fields to analyze: {len(fields)}")
        logger.info(f"🔧 Using: FieldLevelComplianceAnalyzer from Compliance_And_Discrepancies module")
        
        try:
            # Extract config values
            model = self.config.get('model', self.deployment_name)
            temperature = self.config.get('temperature', 0.1)
            system_prompt = self.config.get('system_prompt', '')
            check_mandatory = self.config.get('check_mandatory_fields', True)
            check_conditional = self.config.get('check_conditional_fields', True)
            check_data_quality = self.config.get('check_data_quality', True)
            check_format = self.config.get('check_format_validity', True)
            severity_levels = self.config.get('severity_levels', ['critical', 'warning', 'info'])
            
            logger.info(f"📋 Config: model={model}, temperature={temperature}")
            logger.info(f"📋 Checks: mandatory={check_mandatory}, data_quality={check_data_quality}")
            
            # Load document-specific rules
            document_rules = []
            if document_type:
                document_rules = self._load_discrepancy_rules(document_type)
            
            # Prepare fields for analysis
            field_entries = [{"field": key, "value": info.get("value", "")} for key, info in fields.items()]
            
            # Build rules context
            rules_context = ""
            if document_rules:
                rules_context = f"\n\nAPPLICABLE COMPLIANCE RULES FOR {document_type.upper()}:\n"
                for idx, rule in enumerate(document_rules[:25], 1):
                    rules_context += f"{idx}. {rule.get('code', 'N/A')}: {rule.get('description', '')}\n"
                    rules_context += f"   Basis: {rule.get('basis', 'N/A')} | Priority: {rule.get('priority', 'N/A')}\n"
            else:
                rules_context = "\n\nUsing standard trade finance compliance guidelines."
            
            # Build validation instructions
            validation_instructions = []
            if check_mandatory:
                validation_instructions.append("- Check ALL mandatory fields are present and complete")
            if check_conditional:
                validation_instructions.append("- Verify conditional fields based on document context")
            if check_data_quality:
                validation_instructions.append("- Assess data quality (dates in YYYY-MM-DD, amounts with currency)")
            if check_format:
                validation_instructions.append("- Validate format consistency (reference numbers, names/addresses)")
            
            validation_text = "\n".join(validation_instructions) if validation_instructions else "- Perform standard compliance checks"
            severity_map = f"Use severity levels: {', '.join(severity_levels)}" if severity_levels else "Use 'high', 'medium', 'low' severity levels"
            
            # Build the prompt
            unified_prompt = f"""Analyze these {len(field_entries)} fields for compliance violations based on the specific rules provided.

DOCUMENT TYPE: {document_type or 'Unknown'}

EXTRACTED FIELDS:
{json.dumps(field_entries, separators=(',', ':'))}
{rules_context}

VALIDATION CHECKS TO PERFORM:
{validation_text}

INSTRUCTIONS:
1. Check each field against the applicable rules above
2. Identify any compliance violations or discrepancies
3. Reference specific rule codes and bases when violations are found
4. {severity_map}
5. Provide a single unified compliance result
6. For each field, if it matches any rule from the rules list above, always include the "rule_code" from that rule, even if compliant.

Return JSON only:
{{"results":[{{"field":"<field_name>","value":"<field_value>",
"compliance":true/false,"severity":"critical/warning/info",
"reason":"Detailed explanation with specific rule reference if violated",
"rule_code":"<rule_code_if_violated>"}}]}}"""

            logger.info(f"UNIFIED COMPLIANCE: Analyzing {len(field_entries)} fields with {len(document_rules)} rules for {document_type}")
            
            # Make the API call - use max_tokens from config
            max_tokens = self.config.get('max_tokens', 8000)
            response = openai.ChatCompletion.create(
                engine=model if model else self.deployment_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": unified_prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=0.9
            )
            
            reply = response.choices[0].message["content"].strip()
            logger.info(f"SUCCESS: Unified compliance reply received: {len(reply)} chars")
            
            # Clean the response
            if reply.startswith("```json"):
                reply = reply[7:]
            if reply.endswith("```"):
                reply = reply[:-3]
            reply = reply.strip()
            
            # Parse unified response
            parsed_response = json.loads(reply)
            analysis_results = parsed_response.get("results", parsed_response.get("analysis_results", []))
            
            # Build the result dictionary
            _unified_compliance_result = {}
            
            for item in analysis_results:
                field_key = item["field"]
                rule_code = item.get("rule_code", "")
                
                # Find the complete rule information
                rule_info = None
                if rule_code and document_rules:
                    for rule in document_rules:
                        if rule.get("code") == rule_code:
                            rule_info = rule
                            break
                
                # Build comprehensive compliance data
                _unified_compliance_result[field_key] = {
                    "field": field_key,
                    "value": item["value"],
                    "compliance": item.get("compliance", True),
                    "severity": item.get("severity", "low"),
                    "reason": item.get("reason", "No issues found"),
                    "rule_code": rule_code,
                    "basis": rule_info.get("basis", "Standard Practice") if rule_info else "Standard Practice",
                    "priority": rule_info.get("priority", "Optional") if rule_info else "Optional",
                    "rule_description": rule_info.get("description", "") if rule_info else "",
                    "rule_id": rule_info.get("id", "") if rule_info else "",
                    "status": "compliant" if item.get("compliance", True) else "non-compliant",
                    "category": "compliance_check"
                }
            
            processing_time = time.time() - start_time
            logger.info(f"SUCCESS: UNIFIED COMPLIANCE completed in {processing_time:.2f}s")
            logger.info(f"RESULTS: {len(_unified_compliance_result)} fields analyzed using {len(document_rules)} rules")
            logger.info(f"{'='*80}")
            logger.info("")
            
            return _unified_compliance_result
            
        except json.JSONDecodeError as e:
            logger.error(f"ERROR: Unified compliance JSON parse error: {e}")
            _unified_compliance_result = {}
            return {}
            
        except Exception as e:
            logger.error(f"ERROR: Unified compliance error: {e}")
            _unified_compliance_result = {}
            return {}


def get_unified_compliance_result() -> dict:
    """Get the current unified compliance result."""
    global _unified_compliance_result
    return _unified_compliance_result


def clear_unified_compliance_result():
    """Clear the unified compliance result."""
    global _unified_compliance_result
    _unified_compliance_result = {}


def analyze_field_level_compliance(fields: dict, document_type: str = None) -> tuple:
    """
    Convenience function for field-level compliance analysis.
    
    Args:
        fields: Dictionary of extracted fields
        document_type: Document type for rule loading
        
    Returns:
        Tuple of ({}, {}) for backward compatibility with UCP600/SWIFT results
    """
    analyzer = FieldLevelComplianceAnalyzer()
    analyzer.analyze(fields, document_type)
    return {}, {}
