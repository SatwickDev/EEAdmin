from app import create_app

if __name__ == "__main__":
    app, socketio = create_app()   # ✅ unpack both
    socketio.run(app, host="0.0.0.0", port=5001, debug=True, allow_unsafe_werkzeug=True)
