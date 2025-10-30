from app import create_app
import os
import socket


def get_local_ip():
    """Get the local IP address of the machine."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "your-local-ip"


if __name__ == "__main__":
    app, socketio = create_app()

    # Check if SSL certificates exist
    ssl_cert = os.path.join('ssl', 'cert.pem')
    ssl_key = os.path.join('ssl', 'key.pem')

    local_ip = get_local_ip()

    if os.path.exists(ssl_cert) and os.path.exists(ssl_key):
        # HTTPS with SSL certificates
        print("🔐 SSL certificates found. Starting HTTPS server...")
        print("🌐 Access at: https://localhost:443")
        print(f"🌐 Or from network: https://{local_ip}:443")
        print("⚠️  If security warning appears, click 'Advanced' -> 'Proceed'")
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
        print("⚠️  SSL certificates not found. Running on HTTP...")
        print("📝 To enable HTTPS and camera, run: python generate_cert.py")
        print("🌐 Access at: http://localhost:80")
        print(f"🌐 Or from network: http://{local_ip}:80")
        print("")

        socketio.run(
            app,
            host="0.0.0.0",
            port=80,  # Standard HTTP port
            debug=True,
            allow_unsafe_werkzeug=True
        )
