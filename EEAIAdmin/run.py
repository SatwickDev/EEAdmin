from app import create_app

if __name__ == "__main__":
    app, socketio = create_app()   # unpack both
    # Production deployment on port 80 (standard HTTP port for external access)
    socketio.run(app, host="0.0.0.0", port=80, debug=True, allow_unsafe_werkzeug=True)
    # Development/local testing on port 5002 (uncomment line below and comment line above)
    # socketio.run(app, host="0.0.0.0", port=5002, debug=True, allow_unsafe_werkzeug=True)
