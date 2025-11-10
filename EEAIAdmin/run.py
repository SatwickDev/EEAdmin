import sys
import os

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

    # Check if SSL certificates exist
    ssl_cert = os.path.join('ssl', 'cert.pem')
    ssl_key = os.path.join('ssl', 'key.pem')

    local_ip = get_local_ip()

    if os.path.exists(ssl_cert) and os.path.exists(ssl_key):
        # HTTPS with SSL certificates
        log_system("SSL_ENABLED",
                   message="SSL certificates found, starting HTTPS server",
                   port=443, cert_path=ssl_cert, key_path=ssl_key)
        print("[SSL] SSL certificates found. Starting HTTPS server...")
        print("[WEB] Access at: https://localhost:443")
        print(f"[WEB] Or from network: https://{local_ip}:443")
        print("[WARN] If security warning appears, click 'Advanced' -> 'Proceed'")
        print("")

        socketio.run(
            app,
            host="0.0.0.0",  # Bind to all network interfaces
            port=443,  # Standard HTTPS port
            debug=True,
            allow_unsafe_werkzeug=True,
            ssl_context=(ssl_cert, ssl_key)
        )
    else:
        # HTTP without SSL
        log_system("SSL_DISABLED",
                   message="SSL certificates not found, using HTTP",
                   port=80, cert_path=ssl_cert, key_path=ssl_key)

        print("[WARN] SSL certificates not found. Running on HTTP...")
        print("[INFO] To enable HTTPS and camera, run: python generate_cert.py")
        print("[WEB] Access at: http://localhost:80")
        print(f"[WEB] Or from network: http://{local_ip}:80")
        print("")

        socketio.run(
            app,
            host="0.0.0.0",
            port=80,  # Standard HTTP port
            debug=True,
            allow_unsafe_werkzeug=True
        )
