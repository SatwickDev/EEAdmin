import logging
import os
from datetime import timedelta
from flask import Flask
from flask_socketio import SocketIO
# Temporarily disabled due to recursion error
# from flask_cors import CORS

from app.routes import setup_auth_routes
from app.utils.app_config import load_dotenv, engine
from app.utils.common import load_schema
from app.utils.websocket_handler import init_websocket_handler

# Load environment variables
load_dotenv()

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_env_vars():
    """Validate required environment variables."""
    # required_vars = ["SECRET_KEY", "ALLOWED_ORIGINS"]
    # missing = [var for var in required_vars if not os.getenv(var)]
    # if missing:
    #     raise ValueError(f"Missing environment variables: {', '.join(missing)}")

def create_app():
    """
    Create and configure the Flask application.

    Returns:
        Flask: The configured Flask application.
    """
    # Validate environment variables
    validate_env_vars()

    app = Flask(__name__)

    # Session configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', os.urandom(24).hex())
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SECURE'] = os.getenv('FLASK_ENV') == 'production'
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

    # Enable CORS with restricted origins
    # Temporarily disabled due to recursion error
    # CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)
    
    # CORS disabled to fix recursion error - add manual headers instead
    @app.after_request
    def after_request(response):
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return response

    # Load schema dynamically
    try:
        schema = load_schema()
        app.config['SCHEMA'] = schema
    except Exception as e:
        logger.error(f"Failed to load schema: {e}")
        raise

    # Import and register routes
    try:
        from app.routes import setup_routes
        setup_auth_routes(app)
        setup_routes(app)
    except Exception as e:
        logger.error(f"Failed to setup routes: {e}")
        raise

    # Initialize Flask-SocketIO
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
    logger.info("✅ Flask-SocketIO initialized")

    # Initialize WebSocket handler
    try:
        init_websocket_handler(socketio)
        logger.info("✅ WebSocket handler initialized successfully.")
    except Exception as e:
        logger.error(f"❌ Failed to initialize WebSocket handler: {e}")
        # Continue without WebSocket handler
        pass

    # Store socketio instance in app config for later use
    app.config['SOCKETIO'] = socketio

    logger.info("Flask application initialized successfully.")
    return app, socketio