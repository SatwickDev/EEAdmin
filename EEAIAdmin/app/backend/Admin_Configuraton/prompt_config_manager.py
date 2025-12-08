"""
Prompt Configuration Manager
============================

Handles CRUD operations for LLM prompt configurations.
Manages the document_classification_config.yaml file which contains:
- Classification prompts
- Extraction prompts
- Compliance checking prompts
- Performance settings
- Error handling configuration

Author: Modularized from routes.py
"""

import os
import shutil
import logging
import yaml
from datetime import datetime

logger = logging.getLogger(__name__)


class PromptConfigManager:
    """
    Manager class for LLM Prompt Configuration operations.
    
    Manages:
    - Classification settings (model, temperature, system prompt)
    - Extraction settings
    - Compliance settings
    - Prompt templates (classification, extraction, compliance, UCP600, SWIFT)
    - Performance timeouts
    - Error handling configuration
    - Feature flags
    """

    def __init__(self, data_dir: str = None):
        """
        Initialize the Prompt Configuration Manager.
        
        Args:
            data_dir: Path to the data directory. Defaults to app/data
        """
        if data_dir:
            self.data_dir = data_dir
        else:
            # Default path relative to this file
            self.data_dir = os.path.abspath(
                os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data')
            )
        
        os.makedirs(self.data_dir, exist_ok=True)
        self.config_path = os.path.join(self.data_dir, 'document_classification_config.yaml')
        self.backup_path = self.config_path + '.backup'
        
        logger.info(f"🔧 PromptConfigManager initialized with config_path: {self.config_path}")

    def _get_default_config(self) -> dict:
        """Get default prompt configuration structure."""
        return {
            'classification': {
                'model': 'gpt-4',
                'temperature': 0.1,
                'max_tokens': 500,
                'system_prompt': 'You are an expert document classifier for international trade and finance documents.'
            },
            'extraction': {
                'model': 'gpt-4',
                'temperature': 0,
                'max_tokens': 3000,
                'system_prompt': 'You are an expert data extraction system for trade finance documents.'
            },
            'compliance': {
                'model': 'gpt-4',
                'temperature': 0.2,
                'max_tokens': 1500,
                'system_prompt': 'You are a compliance verification expert for trade finance documents.'
            },
            'prompts': {
                'classification': {
                    'template': '''You are an expert document classifier for international trade and finance documents.

Analyze the following document text and identify the exact document type.

AVAILABLE DOCUMENT TYPES:
{document_types_list}

DOCUMENT TEXT:
{ocr_text}

Respond in JSON format:
{{
    "document_type": "exact document name from the list",
    "document_code": "document code (e.g., PO, INV, LC)",
    "confidence": 0.95,
    "reasoning": "brief explanation of classification"
}}'''
                },
                'extraction': {
                    'template': '''You are an expert data extraction system for trade finance documents.

Extract the following information from this {document_name}:

MANDATORY FIELDS (Must extract if present):
{mandatory_fields}

OPTIONAL FIELDS (Extract if available):
{optional_fields}

CONDITIONAL FIELDS (Extract based on context):
{conditional_fields}

DOCUMENT TEXT:
{ocr_text}

INSTRUCTIONS:
1. Extract all mandatory fields - mark as null if truly not present
2. Extract optional fields where available
3. Extract conditional fields based on document context
4. Use exact field names from the list above
5. Preserve original data format and values

Respond in JSON format with extracted fields:
{{
    "mandatory": {{"field_name": "value", ...}},
    "optional": {{"field_name": "value", ...}},
    "conditional": {{"field_name": "value", ...}}
}}'''
                },
                'compliance': {
                    'template': '''You are a compliance verification expert for {document_name}.

EXTRACTED DATA:
Mandatory: {mandatory_data}
Optional: {optional_data}
Conditional: {conditional_data}

REQUIRED MANDATORY FIELDS:
{mandatory_fields_list}

MISSING MANDATORY FIELDS:
{missing_mandatory_list}

COMPLIANCE CHECK:
1. Verify all mandatory fields are present and valid
2. Check data quality and format
3. Identify any critical issues
4. Provide recommendations

Respond in JSON format:
{{
    "compliant": true/false,
    "missing_mandatory": [...],
    "data_quality_issues": [...],
    "warnings": [...],
    "recommendations": [...],
    "severity": "critical/warning/info"
}}'''
                },
                'ucp600': {
                    'template': '''Check compliance with UCP600 rules for Letter of Credit.

Verify the following fields meet UCP600 requirements:
{fields}

Return compliance status for each field.'''
                },
                'swift_mt700': {
                    'template': '''Check compliance with SWIFT MT700 format for Letter of Credit.

Verify the following fields meet SWIFT MT700 format requirements:
{fields}

Return compliance status for each field.'''
                },
                'urdg758': {
                    'template': '''Check compliance with URDG758 rules for Bank Guarantee.

Verify the following fields meet URDG758 requirements:
{fields}

Return compliance status for each field.'''
                },
                'swift_mt760': {
                    'template': '''Check compliance with SWIFT MT760 format for Bank Guarantee.

Verify the following fields meet SWIFT MT760 format requirements:
{fields}

Return compliance status for each field.'''
                }
            },
            'performance': {
                'classification_timeout': 30,
                'extraction_timeout': 60,
                'compliance_timeout': 30,
                'total_timeout': 180
            },
            'error_handling': {
                'retry_on_failure': True,
                'max_retries': 3,
                'retry_delay_seconds': 2
            },
            'features': {
                'enable_enhanced_classification': True,
                'enable_entity_extraction': True,
                'enable_compliance_checking': True,
                'enable_progress_tracking': True
            }
        }

    def load_config(self) -> dict:
        """
        Load prompt configuration from YAML file.
        
        Returns:
            dict: Configuration dictionary, or None if error
        """
        try:
            if not os.path.exists(self.config_path):
                logger.warning(f"Config file not found: {self.config_path}")
                return None
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            logger.debug("Prompt configuration loaded successfully")
            return config
            
        except Exception as e:
            logger.error(f"Error loading prompt config: {e}")
            return None

    def save_config(self, config: dict) -> bool:
        """
        Save prompt configuration to YAML file.
        
        Args:
            config: Configuration dictionary to save
            
        Returns:
            bool: True if successful
        """
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            
            logger.debug("Prompt configuration saved successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error saving prompt config: {e}")
            return False

    def get_config(self) -> dict:
        """
        Get current prompt configuration.
        
        Returns:
            dict: Result with config or error message
        """
        try:
            config = self.load_config()
            
            if config is None:
                return {'success': False, 'message': 'Configuration file not found'}
            
            return {'success': True, 'config': config}
            
        except Exception as e:
            logger.error(f"Error getting prompt config: {e}")
            return {'success': False, 'message': str(e)}

    def update_config(self, config_data: dict) -> dict:
        """
        Update prompt configuration with provided data.
        Only updates the sections that are provided.
        
        Args:
            config_data: Dictionary with sections to update
            
        Returns:
            dict: Result with success status
        """
        try:
            # Load existing config
            existing_config = self.load_config()
            if existing_config is None:
                existing_config = self._get_default_config()
            
            # Update specific sections
            updateable_sections = [
                'classification', 'extraction', 'compliance',
                'prompts', 'performance', 'error_handling', 'features'
            ]
            
            for section in updateable_sections:
                if section in config_data:
                    if section not in existing_config:
                        existing_config[section] = {}
                    existing_config[section].update(config_data[section])
            
            # Save updated config
            if self.save_config(existing_config):
                logger.info("✅ Prompt configuration updated successfully")
                return {'success': True, 'message': 'Configuration updated successfully'}
            else:
                return {'success': False, 'message': 'Failed to save configuration'}
                
        except Exception as e:
            logger.error(f"Error updating prompt config: {e}")
            return {'success': False, 'message': str(e)}

    def reset_config(self) -> dict:
        """
        Reset prompt configuration to defaults.
        Creates a backup of current config before reset.
        
        Returns:
            dict: Result with success status
        """
        try:
            # Create backup if config exists
            if os.path.exists(self.config_path):
                shutil.copy(self.config_path, self.backup_path)
                logger.info(f"Created backup at: {self.backup_path}")
            
            # Create default configuration
            default_config = self._get_default_config()
            
            # Save default config
            if self.save_config(default_config):
                logger.info("✅ Prompt configuration reset to defaults")
                return {'success': True, 'message': 'Configuration reset to defaults'}
            else:
                return {'success': False, 'message': 'Failed to save default configuration'}
                
        except Exception as e:
            logger.error(f"Error resetting prompt config: {e}")
            return {'success': False, 'message': str(e)}

    def export_config(self) -> str:
        """
        Get the config file path for export.
        
        Returns:
            str: Path to config file, or None if not exists
        """
        if os.path.exists(self.config_path):
            return self.config_path
        return None

    def reload_config(self) -> dict:
        """
        Reload prompt configuration from file.
        Useful after external changes to the config file.
        
        Returns:
            dict: Result with success status and reloaded config
        """
        try:
            config = self.load_config()
            
            if config is None:
                return {'success': False, 'message': 'Configuration file not found'}
            
            logger.info("✅ Prompt configuration reloaded successfully")
            return {'success': True, 'message': 'Configuration reloaded successfully', 'config': config}
            
        except Exception as e:
            logger.error(f"Error reloading prompt config: {e}")
            return {'success': False, 'message': str(e)}

    # ==================== Convenience Methods ====================

    def get_classification_config(self) -> dict:
        """Get just the classification section of config."""
        config = self.load_config()
        return config.get('classification', {}) if config else {}

    def get_extraction_config(self) -> dict:
        """Get just the extraction section of config."""
        config = self.load_config()
        return config.get('extraction', {}) if config else {}

    def get_compliance_config(self) -> dict:
        """Get just the compliance section of config."""
        config = self.load_config()
        return config.get('compliance', {}) if config else {}

    def get_prompt_template(self, prompt_name: str) -> str:
        """
        Get a specific prompt template by name.
        
        Args:
            prompt_name: Name of the prompt (classification, extraction, compliance, etc.)
            
        Returns:
            str: The prompt template, or empty string if not found
        """
        config = self.load_config()
        if config and 'prompts' in config:
            prompt_data = config['prompts'].get(prompt_name, {})
            return prompt_data.get('template', '')
        return ''

    def update_prompt_template(self, prompt_name: str, template: str) -> dict:
        """
        Update a specific prompt template.
        
        Args:
            prompt_name: Name of the prompt to update
            template: New template text
            
        Returns:
            dict: Result with success status
        """
        try:
            config = self.load_config()
            if config is None:
                config = self._get_default_config()
            
            if 'prompts' not in config:
                config['prompts'] = {}
            
            if prompt_name not in config['prompts']:
                config['prompts'][prompt_name] = {}
            
            config['prompts'][prompt_name]['template'] = template
            
            if self.save_config(config):
                logger.info(f"✅ Updated prompt template: {prompt_name}")
                return {'success': True, 'message': f'Prompt template {prompt_name} updated'}
            else:
                return {'success': False, 'message': 'Failed to save configuration'}
                
        except Exception as e:
            logger.error(f"Error updating prompt template {prompt_name}: {e}")
            return {'success': False, 'message': str(e)}


# Singleton instance for convenience
_prompt_config_manager = None


def get_prompt_config_manager() -> PromptConfigManager:
    """Get or create the singleton PromptConfigManager instance."""
    global _prompt_config_manager
    if _prompt_config_manager is None:
        _prompt_config_manager = PromptConfigManager()
    return _prompt_config_manager
