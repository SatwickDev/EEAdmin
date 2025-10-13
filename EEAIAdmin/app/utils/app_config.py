import os
import logging
import uuid

import requests
from dotenv import load_dotenv
from sqlalchemy.engine import create_engine
import oracledb
import openai

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# OpenAI Configuration
try:
    logger.info("Starting Azure OpenAI configuration...")
    openai.api_type = "azure"
    openai.api_base = os.getenv("AZURE_OPENAI_API_BASE")
    openai.api_version = "2024-10-01-preview"
    openai.api_key = os.getenv("AZURE_OPENAI_API_KEY")
    deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
    embedding_model = os.getenv("AZURE_EMBEDDING_MODEL")
    embedding_key = os.getenv("AZURE_EMBEDDING_KEY")
    
    logger.info(f"Azure OpenAI Config - API Base: {openai.api_base}")
    logger.info(f"Azure OpenAI Config - API Version: {openai.api_version}")
    logger.info(f"Azure OpenAI Config - Deployment: {deployment_name}")
    logger.info(f"Azure OpenAI Config - API Key Present: {bool(openai.api_key)}")
    logger.info(f"Azure OpenAI Config - API Key Length: {len(openai.api_key) if openai.api_key else 0}")
    logger.info(f"Azure OpenAI Config - API Key First 10 chars: {openai.api_key[:10] if openai.api_key else 'None'}")
    logger.info(f"Azure OpenAI Config - Embedding Model: {embedding_model}")
    
    if not all([openai.api_base, openai.api_key, deployment_name]):
        missing = []
        if not openai.api_base: missing.append("AZURE_OPENAI_API_BASE")
        if not openai.api_key: missing.append("AZURE_OPENAI_API_KEY")
        if not deployment_name: missing.append("AZURE_OPENAI_DEPLOYMENT_NAME")
        logger.error(f"Missing OpenAI environment variables: {missing}")
        raise ValueError(f"Missing OpenAI environment variables: {missing}")
    logger.info("OpenAI configured successfully.")
except Exception as e:
    logger.error(f"Error configuring OpenAI: {e}")
    logger.error(f"Environment variables check - AZURE_OPENAI_API_BASE exists: {bool(os.getenv('AZURE_OPENAI_API_BASE'))}")
    logger.error(f"Environment variables check - AZURE_OPENAI_API_KEY exists: {bool(os.getenv('AZURE_OPENAI_API_KEY'))}")
    logger.error(f"Environment variables check - AZURE_OPENAI_DEPLOYMENT_NAME exists: {bool(os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME'))}")
    raise

# Database Configuration
credentials = {
    'username': os.getenv("DB_USERNAME"),
    'password': os.getenv("DB_PASSWORD"),
    'host': os.getenv("DB_HOST"),
    'port': os.getenv("DB_PORT"),
    'database': os.getenv("DB_DATABASE")
}

# Oracle Client Initialization (optional - only needed for thick mode)
# Using thin mode by default, which doesn't require Oracle Client libraries
oracle_lib_dir = os.getenv("ORACLE_CLIENT_LIB_DIR")
if oracle_lib_dir and os.path.exists(oracle_lib_dir):
    try:
        oracledb.init_oracle_client(lib_dir=oracle_lib_dir)
        logger.info("Oracle thick mode initialized successfully.")
    except Exception as e:
        logger.warning(f"Oracle thick mode initialization failed, falling back to thin mode: {e}")
else:
    logger.info("Using Oracle thin mode (no client library required).")

# Azure Computer Vision Configuration
COMPUTER_VISION_ENDPOINT = os.getenv("AZURE_CV_ENDPOINT")
COMPUTER_VISION_KEY = os.getenv("AZURE_CV_KEY")

if not COMPUTER_VISION_ENDPOINT or not COMPUTER_VISION_KEY:
    raise ValueError("Azure Computer Vision environment variables are missing.")

# OCR Retry Configuration
OCR_MAX_RETRIES = int(os.getenv("OCR_MAX_RETRIES", "3"))  # Default: 3
OCR_RETRY_DELAY_BASE = int(os.getenv("OCR_RETRY_DELAY_BASE", "1"))  # Base (s)

# Validate retry configuration
if OCR_MAX_RETRIES < 1:
    logger.warning("OCR_MAX_RETRIES must be at least 1. Setting to 3.")
    OCR_MAX_RETRIES = 3
elif OCR_MAX_RETRIES > 10:
    logger.warning("OCR_MAX_RETRIES max is 10. Setting to 10.")
    OCR_MAX_RETRIES = 10

logger.info(f"OCR retry: Max={OCR_MAX_RETRIES}, Delay={OCR_RETRY_DELAY_BASE}s")


# YAML Configuration Reader for Admin-Configurable Settings
def get_yaml_retry_config():
    """
    Load retry configuration from YAML file (set by admin via UI).
    
    Returns:
        dict: Retry configuration with max_retries, retry_delay_seconds, etc.
        
    The admin can configure these values through the web UI:
    - Document classification retry count
    - OpenAI API retry count
    - Retry delay between attempts
    """
    try:
        import yaml
        from pathlib import Path
        
        # Get config file path
        base_path = Path(__file__).parent.parent.parent
        config_path = base_path / "data" / "document_classification_config.yaml"
        
        if not config_path.exists():
            logger.warning(f"YAML config file not found: {config_path}")
            return get_default_retry_config()
            
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            
        error_handling = config.get('error_handling', {})
        
        # Extract admin-configurable retry settings
        retry_config = {
            'max_retries': error_handling.get('max_retries', 3),
            'retry_delay_seconds': error_handling.get('retry_delay_seconds', 2),
            'retry_on_failure': error_handling.get('retry_on_failure', True),
            'fallback_to_original_classifier': error_handling.get(
                'fallback_to_original_classifier', True),
            'return_partial_results': error_handling.get(
                'return_partial_results', True),
            'log_errors': error_handling.get('log_errors', True)
        }
        
        max_retries = retry_config['max_retries']
        delay = retry_config['retry_delay_seconds']
        logger.debug(f"📄 Loaded YAML retry config: max_retries={max_retries}, "
                    f"delay={delay}s")
        return retry_config
        
    except Exception as e:
        logger.warning(f"Failed to load YAML retry config: {e}, "
                      "using defaults")
        return get_default_retry_config()


def get_default_retry_config():
    """Default retry configuration when YAML loading fails."""
    return {
        'max_retries': 3,
        'retry_delay_seconds': 2,
        'retry_on_failure': True,
        'fallback_to_original_classifier': True,
        'return_partial_results': True,
        'log_errors': True
    }


# Load admin-configurable retry settings
YAML_RETRY_CONFIG = get_yaml_retry_config()
ADMIN_MAX_RETRIES = YAML_RETRY_CONFIG['max_retries']
ADMIN_RETRY_DELAY = YAML_RETRY_CONFIG['retry_delay_seconds']

logger.info(f"📋 Admin retry config: Max={ADMIN_MAX_RETRIES}, "
           f"Delay={ADMIN_RETRY_DELAY}s (configurable via UI)")

# SQLAlchemy Engine
try:
    connect_url = (
        f"oracle+oracledb://{credentials['username']}:{credentials['password']}"
        f"@{credentials['host']}:{credentials['port']}/{credentials['database']}"
    )
    engine = create_engine(connect_url)
    logger.info("Database engine created successfully.")
except Exception as e:
    logger.error(f"Error creating database engine: {e}")
    raise

# Token Cache
token_cache = {}

def get_token(corporate_id, user_id):
    """
    Retrieve or generate a JWT token.

    Args:
        corporate_id (str): Corporate ID for authentication.
        user_id (str): User ID for authentication.

    Returns:
        str: A JWT token.
    """
    try:
        cache_key = f"{corporate_id}_{user_id}_token"
        if cache_key in token_cache:
            return token_cache[cache_key]

        new_token = generate_jwt_token(corporate_id, user_id)
        token_cache[cache_key] = new_token
        return new_token
    except Exception as e:
        logger.error(f"Error generating token: {e}")
        return None


def generate_jwt_token(corporate_id, user_id):
    """
    Generate a JWT token by making an API call.

    Args:
        corporate_id (str): Corporate ID for authentication.
        user_id (str): User ID for authentication.

    Returns:
        str: A JWT token.
    """
    guid = str(uuid.uuid4())
    auth_url = os.getenv("AUTH_API_URL", "http://example.com/api/login")  # Replace with actual URL
    auth_headers = {
        "Content-Type": "application/json",
        "requestId": guid,
        "channel": "Eximbills",
        "timeStamp": "12",
        "entity": "12",
        "SecertKey": "FinMobileCS",
    }
    auth_payload = {
        "CorporateId": corporate_id,
        "Password": os.getenv("API_PASSWORD", "default_password"),  # Replace with a secure password
        "UserId": user_id,
    }

    try:
        response = requests.post(auth_url, headers=auth_headers, json=auth_payload)
        response.raise_for_status()
        token = response.json().get("Token")
        return token
    except requests.RequestException as e:
        logger.error(f"Error during login: {e}")
        return None



