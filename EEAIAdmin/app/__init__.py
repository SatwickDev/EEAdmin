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

    # Initialize per-process last-reload timestamp to the latest mtime
    # found in the monitored folders so workers don't all reload on first change.
    try:
        import time as _time
        def _max_mtime_for_folder(folder_path: str) -> float:
            folder_path = os.path.abspath(folder_path)
            max_m = 0.0
            if os.path.exists(folder_path):
                for root, _, files in os.walk(folder_path):
                    for fn in files:
                        try:
                            full = os.path.join(root, fn)
                            if os.path.isfile(full):
                                m = os.path.getmtime(full)
                                if m and m > max_m:
                                    max_m = m
                        except Exception:
                            continue
            return max_m

        app_pkg_dir = os.path.dirname(os.path.abspath(__file__))
        monitored = [
            os.path.join(app_pkg_dir, '..', 'data'),  # repo-level data folder
            os.path.join(app_pkg_dir, 'data'),         # app/data
        ]
        overall_max = 0.0
        for d in monitored:
            try:
                overall_max = max(overall_max, _max_mtime_for_folder(d))
                # also consider marker file if present
                marker = os.path.join(d, '.last_reload')
                if os.path.exists(marker):
                    try:
                        overall_max = max(overall_max, os.path.getmtime(marker))
                    except Exception:
                        pass
            except Exception:
                continue

        # Fallback to current time if nothing found to avoid 0 values
        app._last_json_reload = overall_max or _time.time()
        logger.debug(f"Initialized app._last_json_reload = {app._last_json_reload}")
    except Exception:
        logger.debug('Could not initialize app._last_json_reload at startup')

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

    # --- ✅ NEW: Automatic JSON reload hook (safer) ---
    # Use `g.data_modified` in writer endpoints to indicate a real data change.
    # Also add a lightweight per-worker marker check so workers pick up external changes.
    from flask import g, request, current_app

    from time import time
    import glob
    @app.after_request
    def auto_reload_on_modify(response):
        """
        Automatically reload JSONs after successful POST/PUT/DELETE when a writer set `g.data_modified`.
        Only reload if changes happened in data or app/data folders, and debounce reloads.
        """
        try:
            if getattr(g, 'data_modified', False) and request.method in ['POST', 'PUT', 'DELETE'] and response.status_code in (200, 201):
                now = time()
                last_reload = getattr(current_app, '_last_json_reload', 0)
                # Only reload if more than 2 seconds have passed since last reload
                if now - last_reload > 2:
                    # Check if any file in data or app/data has changed since last reload
                    data_dirs = [
                        os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data'),
                        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
                    ]
                    changed = False
                    for folder in data_dirs:
                        folder = os.path.abspath(folder)
                        for file in glob.glob(os.path.join(folder, '**'), recursive=True):
                            if os.path.isfile(file):
                                mtime = os.path.getmtime(file)
                                if last_reload == 0 or mtime > last_reload:
                                    changed = True
                                    break
                        if changed:
                            break
                    if changed:
                        try:
                            from app.utils.reload_helper import reload_all_jsons, reload_app_data
                            reload_all_jsons()
                            reload_app_data()
                            logger.info("✅ Auto JSON reload triggered after data change in monitored folders")
                            current_app._last_json_reload = now
                            g.data_modified = False
                        except Exception as e:
                            logger.warning(f"⚠️ Auto reload failed: {e}")
        except Exception:
            logger.debug('auto_reload_on_modify encountered an unexpected error')
        return response

    @app.before_request
    def _check_reload_marker():
        """Per-worker marker check: if `app/data/.last_reload` mtime is newer than the
        in-process marker, call the reload helpers so workers stay in sync.
        """
        try:
            import os
            marker = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', '.last_reload')
            try:
                mtime = os.path.getmtime(marker)
            except Exception:
                mtime = None

            last = getattr(current_app, '_last_reload_mtime', None)
            if mtime and (last is None or mtime > last):
                try:
                    from app.utils.reload_helper import reload_all_jsons, reload_app_data
                    reload_all_jsons()
                    reload_app_data()
                    current_app._last_reload_mtime = mtime
                    logger.info('✅ Per-worker reload applied from marker')
                except Exception:
                    logger.exception('Failed to apply per-worker reload from marker')
        except Exception:
            # Do not let marker checks break requests
            logger.debug('check_reload_marker failed')

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