import sys
import os

# Load environment variables from .env file (optional - uncomment to use)
# from dotenv import load_dotenv
# load_dotenv()  # Load .env before anything else

# Fix Unicode encoding issues when running as Windows service
if sys.platform == 'win32':
    # Force UTF-8 encoding for the environment
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    # Set UTF-8 encoding for stdout and stderr
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        # Fallback for older Python versions
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())

from app import create_app
import socket
from app.utils.daily_logger import log_system, log_error


def get_local_ip():
    """Get the local IP address of the machine."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        log_system("NETWORK_CONFIG", message=f"Local IP detected: {local_ip}")
        return local_ip
    except Exception as e:
        log_error(f"Failed to detect local IP: {e}",
                  context="startup", fallback_used=True)
        return "your-local-ip"


if __name__ == "__main__":
    log_system("APPLICATION_STARTUP", message="Application startup initiated")
    
    app, socketio = create_app()

    # Get configuration from environment variables
    ssl_enabled = os.environ.get('SSL_ENABLED', 'true').lower() in ('true', '1', 'yes')
    ssl_cert_path = os.environ.get('SSL_CERT_PATH', os.path.join('ssl', 'cert.pem'))
    ssl_key_path = os.environ.get('SSL_KEY_PATH', os.path.join('ssl', 'key.pem'))
    
    # Server configuration
    server_host = os.environ.get('SERVER_HOST', '0.0.0.0')
    https_port = int(os.environ.get('HTTPS_PORT', '443'))
    http_port = int(os.environ.get('HTTP_PORT', '80'))
    debug_mode = os.environ.get('DEBUG_MODE', 'true').lower() in ('true', '1', 'yes')
    allow_unsafe_werkzeug = os.environ.get('ALLOW_UNSAFE_WERKZEUG', 'true').lower() in ('true', '1', 'yes')

    local_ip = get_local_ip()

    # Check if SSL should be enabled and certificates exist
    if ssl_enabled and os.path.exists(ssl_cert_path) and os.path.exists(ssl_key_path):
        # HTTPS with SSL certificates
        log_system("SSL_ENABLED",
                   message="SSL certificates found, starting HTTPS server",
                   port=https_port, cert_path=ssl_cert_path, key_path=ssl_key_path)
        print("[SSL] SSL certificates found. Starting HTTPS server...")
        print(f"[WEB] Access at: https://localhost:{https_port}")
        print(f"[WEB] Or from network: https://{local_ip}:{https_port}")
        print("[WARN] If security warning appears, click 'Advanced' -> 'Proceed'")
        print("")

        socketio.run(
            app,
            host=server_host,
            port=https_port,
            debug=debug_mode,
            allow_unsafe_werkzeug=allow_unsafe_werkzeug,
            ssl_context=(ssl_cert_path, ssl_key_path)
        )
    else:
        # HTTP without SSL
        if ssl_enabled:
            log_system("SSL_MISCONFIGURED",
                       message="SSL enabled but certificates not found, falling back to HTTP",
                       port=http_port, cert_path=ssl_cert_path, key_path=ssl_key_path)
            print("[WARN] SSL enabled but certificates not found. Falling back to HTTP...")
        else:
            log_system("SSL_DISABLED",
                       message="SSL disabled, using HTTP",
                       port=http_port)
            print("[INFO] SSL disabled. Running on HTTP...")
        
        print("[INFO] To enable HTTPS and camera, run: python generate_cert.py")
        print(f"[WEB] Access at: http://localhost:{http_port}")
        print(f"[WEB] Or from network: http://{local_ip}:{http_port}")
        print("")

        socketio.run(
            app,
            host=server_host,
            port=http_port,
            debug=debug_mode,
            allow_unsafe_werkzeug=allow_unsafe_werkzeug
        )
