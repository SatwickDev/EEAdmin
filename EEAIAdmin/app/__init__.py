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

# Initialize daily logging system
from app.utils.daily_logger import setup_application_logging

# Load environment variables
load_dotenv()
json_data_cache = {}

# Setup application-wide logging to daily files
app_logger = setup_application_logging()
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

    from app.utils.daily_logger import log_system
    log_system("APP_CREATION_START",
               message="Flask application creation started")

    app = Flask(__name__)

    # Session configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', os.urandom(24).hex())
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SECURE'] = os.getenv('FLASK_ENV') == 'production'
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

    # Document upload configuration
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')

    # Create upload directory if it doesn't exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

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

    # --- ✅ NEW: Automatic JSON reload hook ---
    @app.after_request
    def auto_reload_on_modify(response):
        """Automatically reload JSONs after successful POST/PUT/DELETE."""
        from flask import request
        import logging
        logger = logging.getLogger(__name__)

        try:
            if request.method in ['POST', 'PUT', 'DELETE'] and response.status_code in [200, 201]:
                from app.utils.reload_helper import reload_all_jsons
                reload_all_jsons()
                logger.info("✅ Auto JSON reload triggered after data change")
        except Exception as e:
            logger.warning(f"⚠️ Auto reload failed: {e}")
        return response

    # -----------------------------------------

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
        from app.document_routes import document_bp
        from app.database_routes import database_bp
        setup_auth_routes(app)
        setup_routes(app)

        # Register document verification blueprint
        app.register_blueprint(document_bp)
        logger.info("Document verification blueprint registered successfully.")

        # Register database connection management blueprint
        app.register_blueprint(database_bp)
        logger.info("Database connection management blueprint registered successfully.")
    except Exception as e:
        logger.error(f"Failed to setup routes: {e}")
        raise

    # Initialize Flask-SocketIO
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
    logger.info("SUCCESS: Flask-SocketIO initialized")

    # Initialize WebSocket handler
    try:
        init_websocket_handler(socketio)
        logger.info("SUCCESS: WebSocket handler initialized successfully.")
    except Exception as e:
        logger.error(f"ERROR: Failed to initialize WebSocket handler: {e}")
        # Continue without WebSocket handler
        pass

    # Store socketio instance in app config for later use
    app.config['SOCKETIO'] = socketio

    logger.info("Flask application initialized successfully.")
    log_system("APP_CREATION_COMPLETE",
               message="Flask application with SocketIO initialized")
    return app, socketio