"""
Clean routes module with manual functionality removed and session deletion added
"""
from flask import Blueprint, jsonify, request, session
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import logging
from bson import ObjectId
from pymongo import MongoClient

logger = logging.getLogger(__name__)

# Create Blueprint
clean_routes_bp = Blueprint('clean_routes', __name__)

# MongoDB setup - matching the main routes.py configuration
MONGO_URI = "mongodb://localhost:27017/"
DATABASE_NAME = "finai_chatbot"
client = MongoClient(MONGO_URI, connectTimeoutMS=5000, serverSelectionTimeoutMS=5000)
db = client[DATABASE_NAME]
conversation_collection = db.conversation_history
sessions_collection = db.sessions


class SessionManager:
    """Manages chat sessions without manual functionality"""
    
    @staticmethod
    def get_user_sessions(user_id: str) -> List[Dict[str, Any]]:
        """Get all sessions for a user"""
        try:
            sessions = list(conversation_collection.aggregate([
                {"$match": {"user_id": user_id}},
                {"$group": {
                    "_id": "$session_id",
                    "first_message": {"$first": "$timestamp"},
                    "last_message": {"$last": "$timestamp"},
                    "message_count": {"$sum": 1}
                }},
                {"$sort": {"last_message": -1}}
            ]))
            
            # Format sessions for frontend
            formatted_sessions = []
            for session in sessions:
                formatted_sessions.append({
                    "session_id": session["_id"],
                    "created_at": session["first_message"],
                    "last_activity": session["last_message"],
                    "message_count": session["message_count"]
                })
            
            return formatted_sessions
        except Exception as e:
            logger.error(f"Error getting user sessions: {e}")
            return []
    
    @staticmethod
    def delete_session(user_id: str, session_id: str) -> bool:
        """Delete a specific chat session and all its messages"""
        try:
            # Delete all messages in the session
            result = conversation_collection.delete_many({
                "user_id": user_id,
                "session_id": session_id
            })
            
            # Delete session record if exists
            sessions_collection.delete_one({
                "user_id": user_id,
                "session_id": session_id
            })
            
            logger.info(f"Deleted session {session_id} for user {user_id}. Removed {result.deleted_count} messages.")
            return result.deleted_count > 0
            
        except Exception as e:
            logger.error(f"Error deleting session: {e}")
            return False
    
    @staticmethod
    def delete_all_sessions(user_id: str) -> int:
        """Delete all sessions for a user"""
        try:
            # Delete all conversation messages
            result = conversation_collection.delete_many({"user_id": user_id})
            
            # Delete all session records
            sessions_collection.delete_many({"user_id": user_id})
            
            logger.info(f"Deleted all sessions for user {user_id}. Removed {result.deleted_count} messages.")
            return result.deleted_count
            
        except Exception as e:
            logger.error(f"Error deleting all sessions: {e}")
            return 0


# API Routes for session management
@clean_routes_bp.route("/api/sessions", methods=["GET"])
def get_sessions():
    """Get all chat sessions for the current user"""
    if "user_id" not in session:
        return jsonify({"error": "User not authenticated"}), 401
    
    user_id = session["user_id"]
    sessions = SessionManager.get_user_sessions(user_id)
    
    return jsonify({
        "success": True,
        "sessions": sessions,
        "count": len(sessions)
    })


@clean_routes_bp.route("/api/sessions/<session_id>", methods=["DELETE"])
def delete_session(session_id):
    """Delete a specific chat session"""
    if "user_id" not in session:
        return jsonify({"error": "User not authenticated"}), 401
    
    user_id = session["user_id"]
    
    # Validate session belongs to user
    session_exists = conversation_collection.find_one({
        "user_id": user_id,
        "session_id": session_id
    })
    
    if not session_exists:
        return jsonify({
            "success": False,
            "error": "Session not found or unauthorized"
        }), 404
    
    # Delete the session
    success = SessionManager.delete_session(user_id, session_id)
    
    if success:
        return jsonify({
            "success": True,
            "message": f"Session {session_id} deleted successfully"
        })
    else:
        return jsonify({
            "success": False,
            "error": "Failed to delete session"
        }), 500


@clean_routes_bp.route("/api/sessions/all", methods=["DELETE"])
def delete_all_sessions():
    """Delete all sessions for the current user"""
    if "user_id" not in session:
        return jsonify({"error": "User not authenticated"}), 401
    
    user_id = session["user_id"]
    
    # Confirm action with parameter
    if not request.json or not request.json.get("confirm", False):
        return jsonify({
            "success": False,
            "error": "Confirmation required"
        }), 400
    
    deleted_count = SessionManager.delete_all_sessions(user_id)
    
    return jsonify({
        "success": True,
        "message": f"Deleted all sessions successfully",
        "deleted_count": deleted_count
    })


@clean_routes_bp.route("/api/sessions/<session_id>/messages", methods=["GET"])
def get_session_messages(session_id):
    """Get all messages for a specific session"""
    if "user_id" not in session:
        return jsonify({"error": "User not authenticated"}), 401
    
    user_id = session["user_id"]
    
    try:
        # Get messages for the session
        messages = list(conversation_collection.find(
            {"user_id": user_id, "session_id": session_id},
            {"_id": 0, "role": 1, "message": 1, "timestamp": 1}
        ).sort("timestamp", 1))
        
        return jsonify({
            "success": True,
            "session_id": session_id,
            "messages": messages,
            "count": len(messages)
        })
        
    except Exception as e:
        logger.error(f"Error retrieving session messages: {e}")
        return jsonify({
            "success": False,
            "error": "Failed to retrieve messages"
        }), 500


# Intent handlers without manual functionality
def handle_intent_without_manuals(intent: str, user_query: str, user_id: str, session_id: str) -> Dict[str, Any]:
    """
    Handle intents with manual-related functionality removed
    """
    
    # Map of intents to their handlers (excluding manual-related intents)
    intent_handlers = {
        "Session Management": handle_session_management,
        "General Query": handle_general_query,
        # Add other non-manual intents here
    }
    
    handler = intent_handlers.get(intent, handle_general_query)
    return handler(user_query, user_id, session_id)


def handle_session_management(query: str, user_id: str, session_id: str) -> Dict[str, Any]:
    """Handle session management queries"""
    query_lower = query.lower()
    
    if "delete" in query_lower and "session" in query_lower:
        if "all" in query_lower:
            return {
                "type": "session_action",
                "action": "delete_all",
                "message": "Are you sure you want to delete all your chat sessions? This cannot be undone."
            }
        else:
            return {
                "type": "session_action", 
                "action": "delete_single",
                "message": "Which session would you like to delete?",
                "sessions": SessionManager.get_user_sessions(user_id)
            }
    
    elif "list" in query_lower or "show" in query_lower:
        sessions = SessionManager.get_user_sessions(user_id)
        return {
            "type": "session_list",
            "sessions": sessions,
            "message": f"You have {len(sessions)} chat sessions."
        }
    
    return {
        "type": "info",
        "message": "I can help you manage your chat sessions. You can ask me to list, delete, or view your sessions."
    }


def handle_general_query(query: str, user_id: str, session_id: str) -> Dict[str, Any]:
    """Handle general queries without manual functionality"""
    return {
        "type": "general",
        "message": "Processing your query...",
        "requires_llm": True
    }


# Classification function without manual intents
def classify_intent_clean(user_query: str) -> str:
    """
    Classify user intent without manual-related intents
    """
    query_lower = user_query.lower()
    
    # Session management keywords
    if any(word in query_lower for word in ["session", "chat history", "conversation"]):
        if any(action in query_lower for action in ["delete", "remove", "clear"]):
            return "Session Management"
        elif any(action in query_lower for action in ["list", "show", "view"]):
            return "Session Management"
    
    # Default to general query
    return "General Query"


# Export the blueprint
__all__ = ['clean_routes_bp', 'SessionManager', 'classify_intent_clean', 'handle_intent_without_manuals']