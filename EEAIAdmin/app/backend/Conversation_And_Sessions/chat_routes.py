"""
Chat & Query Routes Module
Contains routes for query processing, history, and streaming
"""

from flask import request, jsonify, session
from datetime import datetime


def register_chat_routes(app, timing_aspect, logger, db,
                         get_conversation_context, retrieve_conversation_history,
                         clear_conversation_history, handle_ai_check,
                         active_user_repositories, active_user_modules):
    """
    Register chat history and AI check routes
    
    Args:
        app: Flask application instance
        timing_aspect: Timing decorator for performance monitoring
        logger: Logger instance
        db: MongoDB database instance
        get_conversation_context: Function to get conversation context
        retrieve_conversation_history: Function to retrieve history
        clear_conversation_history: Function to clear history
        handle_ai_check: Function for AI compliance check
        active_user_repositories: Dict of active user repositories
        active_user_modules: Dict of active user modules
    """

    @app.route("/history", methods=["GET"])
    @timing_aspect
    def get_history():
        """Get conversation history for a user"""
        user_id = session.get("user_id", request.args.get("user_id"))
        session_id = request.args.get("session_id", None)
        if not user_id:
            return jsonify({"error": "user_id is required"}), 400

        history = retrieve_conversation_history(user_id, session_id)
        conversation_history = [
            {
                "created_at": msg.get("created_at").isoformat() if isinstance(msg.get("created_at"),
                                                                              datetime) else msg.get("created_at"),
                "message": msg.get("message"),
                "role": msg.get("role"),
                "user_id": msg.get("user_id"),
                "session_id": msg.get("session_id", "")
            }
            for msg in history
        ]
        return jsonify({"conversation_history": conversation_history})

    @app.route("/AICheck", methods=["POST"])
    @timing_aspect
    def post_ai_check():
        """AI compliance check endpoint"""
        try:
            user_id = session.get("user_id", "1517524")
            data = request.json
            logger.info(f"User {user_id} conversation context: {data}")
            context = get_conversation_context(user_id)
            result, status_code = handle_ai_check(data, context)
            return jsonify(result), status_code
        except Exception as e:
            logger.error(f"AI Compliance Check Error: {e}", exc_info=True)
            return jsonify({"error": str(e)}), 500

    @app.route("/clear_history", methods=["POST"])
    @timing_aspect
    def clear_history():
        """Clear conversation history for a user or specific session."""
        logger.info("Received request to clear chat history.")
        try:
            # Extract user_id and session_id
            if request.content_type == "application/json":
                json_data = request.get_json()
                user_id = session.get("user_id", json_data.get("user_id", "").strip())
                session_id = json_data.get("session_id", None)
            else:
                user_id = session.get("user_id", request.form.get("user_id", "").strip())
                session_id = request.form.get("session_id", None)

            if not user_id:
                logger.warning("Missing user_id in clear history request.")
                return jsonify({"response": "Missing user_id.", "intent": "error"}), 400

            # If session_id is same as user_id, clear all sessions for user
            if session_id == user_id:
                logger.info(f"Clearing ALL history for user_id: {user_id} (session_id matches user_id)")
                session_id = None  # Clear all sessions

            logger.info(f"Clearing history for user_id: {user_id}, session_id: {session_id}")
            deleted_count = clear_conversation_history(user_id, session_id)

            logger.info(f"Successfully cleared {deleted_count} history entries for user_id: {user_id}")
            return jsonify({
                "response": f"Conversation history cleared successfully. {deleted_count} entries removed.",
                "intent": "clear_history",
                "deleted_count": deleted_count
            })

        except Exception as e:
            logger.error(f"Error clearing conversation history: {e}", exc_info=True)
            return jsonify({"response": f"An unexpected error occurred: {str(e)}", "intent": "error"}), 500

    logger.info("Chat routes registered successfully")
