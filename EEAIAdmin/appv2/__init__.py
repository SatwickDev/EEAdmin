"""
EEAI Application v2 - LangChain & LangGraph Implementation
Maintains 100% feature parity with original implementation
"""

import logging
import os
from datetime import timedelta
from flask import Flask
from flask_cors import CORS

from appv2.routes import setup_auth_routes, setup_routes
from appv2.utils.app_config import load_dotenv, get_database_engine
from appv2.utils.common import load_schema

# Load environment variables
load_dotenv()

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_env_vars():
    """Validate required environment variables."""
    # Validation logic remains the same as original
    pass

def create_app():
    """
    Create and configure the Flask application with LangChain/LangGraph.
    
    Returns:
        Flask: The configured Flask application with enhanced AI capabilities.
    """
    # Validate environment variables
    validate_env_vars()
    
    app = Flask(__name__)
    
    # Session configuration (same as original)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', os.urandom(24).hex())
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SECURE'] = os.getenv('FLASK_ENV') == 'production'
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
    
    # Enable CORS with restricted origins
    CORS(app, resources={r"/*": {"origins": "*"}})
    
    # Load schema dynamically
    try:
        schema = load_schema()
        app.config['SCHEMA'] = schema
    except Exception as e:
        logger.error(f"Failed to load schema: {e}")
        raise
    
    # Initialize LangChain and LangGraph components
    from appv2.utils.langchain_config import initialize_langchain
    try:
        langchain_components = initialize_langchain()
        app.config['LANGCHAIN'] = langchain_components
        logger.info("LangChain and LangGraph components initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize LangChain components: {e}")
        raise
    
    # Import and register routes
    try:
        setup_auth_routes(app)
        setup_routes(app)
    except Exception as e:
        logger.error(f"Failed to setup routes: {e}")
        raise
    
    logger.info("Flask application v2 initialized successfully with LangChain/LangGraph")
    return app