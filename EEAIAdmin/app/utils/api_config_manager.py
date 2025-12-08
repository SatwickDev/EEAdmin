"""
API Configuration Manager
Centralized API configuration using environment variables
Supports Azure OpenAI, OpenAI, Anthropic, and other external APIs
"""

import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def get_api_env_config() -> Dict[str, Any]:
    """
    Parse API-related environment variables
    Returns a dictionary with all API configuration
    """
    config = {
        # Azure OpenAI Configuration
        'azure_openai': {
            'enabled': os.getenv('AZURE_OPENAI_ENABLED', 'true').lower() == 'true',
            'api_type': 'azure',
            'api_base': os.getenv('AZURE_OPENAI_API_BASE'),
            'api_key': os.getenv('AZURE_OPENAI_API_KEY'),
            'api_version': os.getenv('AZURE_OPENAI_API_VERSION', '2024-10-01-preview'),
            'deployment_name': os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-4o'),
            'embedding_model': os.getenv('AZURE_EMBEDDING_MODEL', 'text-embedding-ada-002'),
            'embedding_key': os.getenv('AZURE_EMBEDDING_KEY'),
        },
        
        # OpenAI Configuration (non-Azure)
        'openai': {
            'enabled': os.getenv('OPENAI_ENABLED', 'false').lower() == 'true',
            'api_key': os.getenv('OPENAI_API_KEY'),
            'org_id': os.getenv('OPENAI_ORG_ID'),
            'model': os.getenv('OPENAI_MODEL', 'gpt-4'),
        },
        
        # Anthropic Configuration
        'anthropic': {
            'enabled': os.getenv('ANTHROPIC_ENABLED', 'false').lower() == 'true',
            'api_key': os.getenv('ANTHROPIC_API_KEY'),
            'model': os.getenv('ANTHROPIC_MODEL', 'claude-3-5-sonnet-20241022'),
        },
        
        # API Behavior Settings
        'settings': {
            'default_timeout': int(os.getenv('API_TIMEOUT', '30')),
            'max_retries': int(os.getenv('API_MAX_RETRIES', '3')),
            'retry_delay': int(os.getenv('API_RETRY_DELAY', '1')),
            'temperature': float(os.getenv('API_TEMPERATURE', '0.7')),
            'max_tokens': int(os.getenv('API_MAX_TOKENS', '4000')),
        }
    }
    
    return config


def is_azure_openai_enabled() -> bool:
    """Check if Azure OpenAI is enabled"""
    return os.getenv('AZURE_OPENAI_ENABLED', 'true').lower() == 'true'


def is_openai_enabled() -> bool:
    """Check if OpenAI (non-Azure) is enabled"""
    return os.getenv('OPENAI_ENABLED', 'false').lower() == 'true'


def is_anthropic_enabled() -> bool:
    """Check if Anthropic is enabled"""
    return os.getenv('ANTHROPIC_ENABLED', 'false').lower() == 'true'


def get_azure_openai_config() -> Optional[Dict[str, Any]]:
    """
    Get Azure OpenAI configuration
    Returns None if Azure OpenAI is disabled
    """
    if not is_azure_openai_enabled():
        logger.warning("Azure OpenAI is disabled via AZURE_OPENAI_ENABLED environment variable")
        return None
    
    config = {
        'api_type': 'azure',
        'api_base': os.getenv('AZURE_OPENAI_API_BASE'),
        'api_key': os.getenv('AZURE_OPENAI_API_KEY'),
        'api_version': os.getenv('AZURE_OPENAI_API_VERSION', '2024-10-01-preview'),
        'deployment_name': os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-4o'),
        'embedding_model': os.getenv('AZURE_EMBEDDING_MODEL', 'text-embedding-ada-002'),
        'embedding_key': os.getenv('AZURE_EMBEDDING_KEY'),
    }
    
    # Validate required fields
    if not config['api_base']:
        logger.warning("AZURE_OPENAI_API_BASE not set, using default or None")
    
    if not config['api_key']:
        logger.warning("AZURE_OPENAI_API_KEY not set")
    
    return config


def get_openai_config() -> Optional[Dict[str, Any]]:
    """
    Get OpenAI (non-Azure) configuration
    Returns None if OpenAI is disabled
    """
    if not is_openai_enabled():
        logger.info("OpenAI (non-Azure) is disabled")
        return None
    
    config = {
        'api_key': os.getenv('OPENAI_API_KEY'),
        'org_id': os.getenv('OPENAI_ORG_ID'),
        'model': os.getenv('OPENAI_MODEL', 'gpt-4'),
    }
    
    if not config['api_key']:
        logger.warning("OPENAI_API_KEY not set")
    
    return config


def get_anthropic_config() -> Optional[Dict[str, Any]]:
    """
    Get Anthropic configuration
    Returns None if Anthropic is disabled
    """
    if not is_anthropic_enabled():
        logger.info("Anthropic is disabled")
        return None
    
    config = {
        'api_key': os.getenv('ANTHROPIC_API_KEY'),
        'model': os.getenv('ANTHROPIC_MODEL', 'claude-3-5-sonnet-20241022'),
    }
    
    if not config['api_key']:
        logger.warning("ANTHROPIC_API_KEY not set")
    
    return config


def get_api_settings() -> Dict[str, Any]:
    """Get API behavior settings (timeout, retries, etc.)"""
    return {
        'default_timeout': int(os.getenv('API_TIMEOUT', '30')),
        'max_retries': int(os.getenv('API_MAX_RETRIES', '3')),
        'retry_delay': int(os.getenv('API_RETRY_DELAY', '1')),
        'temperature': float(os.getenv('API_TEMPERATURE', '0.7')),
        'max_tokens': int(os.getenv('API_MAX_TOKENS', '4000')),
    }


def configure_azure_openai(openai_module):
    """
    Configure the openai module for Azure
    
    Args:
        openai_module: The openai module to configure
    
    Returns:
        tuple: (success: bool, deployment_name: str, error_message: str)
    """
    if not is_azure_openai_enabled():
        return False, None, "Azure OpenAI is disabled via AZURE_OPENAI_ENABLED=false"
    
    config = get_azure_openai_config()
    if not config:
        return False, None, "Failed to get Azure OpenAI configuration"
    
    # Validate required fields
    missing = []
    if not config['api_base']:
        missing.append('AZURE_OPENAI_API_BASE')
    if not config['api_key']:
        missing.append('AZURE_OPENAI_API_KEY')
    if not config['deployment_name']:
        missing.append('AZURE_OPENAI_DEPLOYMENT_NAME')
    
    if missing:
        error_msg = f"Missing required Azure OpenAI environment variables: {', '.join(missing)}"
        logger.error(error_msg)
        return False, None, error_msg
    
    try:
        # Configure the openai module
        openai_module.api_type = config['api_type']
        openai_module.api_base = config['api_base']
        openai_module.api_key = config['api_key']
        openai_module.api_version = config['api_version']
        
        logger.info(f"Azure OpenAI configured successfully - Base: {config['api_base']}, Deployment: {config['deployment_name']}")
        return True, config['deployment_name'], None
        
    except Exception as e:
        error_msg = f"Error configuring Azure OpenAI: {str(e)}"
        logger.error(error_msg)
        return False, None, error_msg


def get_config_info(mask_secrets=True) -> Dict[str, Any]:
    """
    Get current API configuration for diagnostics
    
    Args:
        mask_secrets: If True, mask API keys (default: True)
    
    Returns:
        Dictionary with configuration information
    """
    config = get_api_env_config()
    
    if mask_secrets:
        # Mask API keys
        if config['azure_openai']['api_key']:
            config['azure_openai']['api_key'] = '*' * 8
        if config['azure_openai']['embedding_key']:
            config['azure_openai']['embedding_key'] = '*' * 8
        if config['openai']['api_key']:
            config['openai']['api_key'] = '*' * 8
        if config['anthropic']['api_key']:
            config['anthropic']['api_key'] = '*' * 8
    
    return config


def validate_api_config(provider='azure_openai') -> tuple[bool, str]:
    """
    Validate API configuration for a specific provider
    
    Args:
        provider: 'azure_openai', 'openai', or 'anthropic'
    
    Returns:
        tuple: (is_valid: bool, error_message: str)
    """
    if provider == 'azure_openai':
        if not is_azure_openai_enabled():
            return False, "Azure OpenAI is disabled"
        
        config = get_azure_openai_config()
        if not config:
            return False, "Failed to get Azure OpenAI configuration"
        
        missing = []
        if not config['api_base']:
            missing.append('AZURE_OPENAI_API_BASE')
        if not config['api_key']:
            missing.append('AZURE_OPENAI_API_KEY')
        if not config['deployment_name']:
            missing.append('AZURE_OPENAI_DEPLOYMENT_NAME')
        
        if missing:
            return False, f"Missing required fields: {', '.join(missing)}"
        
        return True, "Azure OpenAI configuration is valid"
    
    elif provider == 'openai':
        if not is_openai_enabled():
            return False, "OpenAI is disabled"
        
        config = get_openai_config()
        if not config or not config['api_key']:
            return False, "OPENAI_API_KEY not set"
        
        return True, "OpenAI configuration is valid"
    
    elif provider == 'anthropic':
        if not is_anthropic_enabled():
            return False, "Anthropic is disabled"
        
        config = get_anthropic_config()
        if not config or not config['api_key']:
            return False, "ANTHROPIC_API_KEY not set"
        
        return True, "Anthropic configuration is valid"
    
    else:
        return False, f"Unknown provider: {provider}"


# Convenience functions for backward compatibility
def get_azure_api_key() -> Optional[str]:
    """Get Azure OpenAI API key"""
    return os.getenv('AZURE_OPENAI_API_KEY')


def get_azure_api_base() -> Optional[str]:
    """Get Azure OpenAI API base URL"""
    return os.getenv('AZURE_OPENAI_API_BASE')


def get_azure_deployment_name() -> str:
    """Get Azure OpenAI deployment name"""
    return os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-4o')


def get_azure_api_version() -> str:
    """Get Azure OpenAI API version"""
    return os.getenv('AZURE_OPENAI_API_VERSION', '2024-10-01-preview')


def get_embedding_model() -> str:
    """Get embedding model name"""
    return os.getenv('AZURE_EMBEDDING_MODEL', 'text-embedding-ada-002')


def get_embedding_key() -> Optional[str]:
    """Get embedding API key"""
    return os.getenv('AZURE_EMBEDDING_KEY') or os.getenv('AZURE_OPENAI_API_KEY')
