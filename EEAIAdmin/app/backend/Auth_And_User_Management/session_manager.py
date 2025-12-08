"""
Session Manager for Auth_And_User_Management module
Handles conversation sessions and message storage.
"""

import json
import uuid
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pymongo import DESCENDING

from .constants import SESSION_TIMEOUT_SECONDS
from app.utils import mongodb_manager

logger = logging.getLogger(__name__)

# MongoDB collections - will be initialized when module is imported
_db = None
_conversation_collection = None


def initialize_collections(db, conversation_collection):
    """
    Initialize database collections from external source.
    Called from routes.py during app setup.
    """
    global _db, _conversation_collection
    _db = db
    _conversation_collection = conversation_collection
    logger.info("Session Manager: Database collections initialized")


def _get_collections():
    """Get MongoDB collections, initializing if needed."""
    global _db, _conversation_collection
    if _conversation_collection is None:
        try:
            # Use mongodb_manager for environment-aware connection
            client = mongodb_manager.get_mongo_client()
            if client is None:
                raise Exception("MongoDB is not available or disabled")
            
            db_name = mongodb_manager.get_database_name()
            _db = client[db_name]
            _conversation_collection = _db["conversation_history"]
        except Exception as e:
            logger.error(f"Failed to initialize MongoDB collections: {e}")
            raise
    return _db, _conversation_collection


def _convert_decimal(obj: Any) -> Any:
    """Convert Decimal to float for JSON serialization."""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def get_or_create_session(user_id: str) -> str:
    """
    Get the latest session if within timeout; else create a new session.
    
    Args:
        user_id: The user's ID
        
    Returns:
        Session ID (existing or newly created)
    """
    db, conversation_collection = _get_collections()
    
    last_message = conversation_collection.find_one(
        {"user_id": user_id},
        sort=[("created_at", DESCENDING)]
    )
    
    if not last_message:
        # No existing session, create new one
        return f"session_{int(datetime.utcnow().timestamp() * 1000)}_{uuid.uuid4().hex[:9]}"
    
    time_diff = datetime.utcnow() - last_message["created_at"]
    if time_diff.total_seconds() > SESSION_TIMEOUT_SECONDS:
        # Session timed out, create new one
        return f"session_{int(datetime.utcnow().timestamp() * 1000)}_{uuid.uuid4().hex[:9]}"
    
    # Return existing session
    return last_message["session_id"]


def save_to_conversation(
    user_id: str,
    role: str,
    message: Any,
    max_size: int = 50000,
    session_id: str = None,
    message_type: str = None
) -> str:
    """
    Insert a conversation entry into MongoDB with session and timestamp.
    
    Args:
        user_id: The user's ID
        role: Message role ('user' or 'assistant')
        message: The message content
        max_size: Maximum message size before truncation
        session_id: Optional session ID (will be created if not provided)
        message_type: Optional message type classification
        
    Returns:
        Session ID used for the message
    """
    db, conversation_collection = _get_collections()
    
    # Handle message content
    if message is None:
        message = "No answer available."
    elif isinstance(message, dict):
        message = json.dumps(message, default=_convert_decimal)
    elif not isinstance(message, str):
        message = str(message)

    # Truncate if too long
    if len(message) > max_size:
        message = message[:max_size] + " [Truncated]"
    
    # Get or create session
    if session_id is None:
        session_id = get_or_create_session(user_id)
    
    # Create conversation document
    document = {
        "user_id": user_id,
        "session_id": session_id,
        "role": role,
        "message": message,
        "created_at": datetime.utcnow()
    }

    # Add message_type if provided
    if message_type:
        document["message_type"] = message_type

    conversation_collection.insert_one(document)

    # Update or create session in chat_sessions collection
    now = datetime.utcnow()
    chat_session = db.chat_sessions.find_one({"user_id": user_id, "session_id": session_id})

    if chat_session:
        # Update existing session
        update_data = {
            "$set": {"last_activity": now},
            "$inc": {"message_count": 1}
        }

        # If this is the first user message, save it as title
        if chat_session.get("message_count", 0) == 0 and role == "user" and message:
            update_data["$set"]["first_message"] = message
            update_data["$set"]["title"] = message[:100]

        db.chat_sessions.update_one(
            {"user_id": user_id, "session_id": session_id},
            update_data
        )
    else:
        # Create new session
        session_data = {
            "user_id": user_id,
            "session_id": session_id,
            "created_at": now,
            "last_activity": now,
            "message_count": 1
        }

        # If this is a user message, save it as the first message and title
        if role == "user" and message:
            session_data["first_message"] = message
            session_data["title"] = message[:100]

        db.chat_sessions.insert_one(session_data)

    # Also save to chat_messages collection for consistency
    db.chat_messages.insert_one({
        "user_id": user_id,
        "session_id": session_id,
        "role": role,
        "content": message,
        "timestamp": now
    })

    logger.info(f"Saved message for user {user_id}, session {session_id}")
    return session_id


def get_conversation_context(user_id: str, session_id: str = None) -> List[Dict[str, Any]]:
    """
    Retrieve all conversation entries for a user from MongoDB.
    
    Args:
        user_id: The user's ID
        session_id: Optional session ID to filter by
        
    Returns:
        List of conversation entries
    """
    _, conversation_collection = _get_collections()
    
    query = {"user_id": user_id}
    if session_id:
        query["session_id"] = session_id
    
    context = list(conversation_collection.find(query, {"_id": 0}))
    logger.info(f"Retrieved conversation context for user {user_id}, session {session_id}: {len(context)} messages")
    return context


def get_latest_session_id(user_id: str) -> Optional[str]:
    """
    Find the latest session_id for a user.
    
    Args:
        user_id: The user's ID
        
    Returns:
        Latest session ID or None if no sessions exist
    """
    _, conversation_collection = _get_collections()
    
    last_message = conversation_collection.find_one(
        {"user_id": user_id},
        sort=[("created_at", DESCENDING)]
    )
    return last_message["session_id"] if last_message else None


def retrieve_conversation_history(
    user_id: str,
    session_id: str = None,
    only_latest_session: bool = False
) -> List[Dict[str, Any]]:
    """
    Retrieve conversation history for a user.
    
    Args:
        user_id: The user's ID
        session_id: Optional session ID to filter by
        only_latest_session: If True, only retrieve the latest session
        
    Returns:
        List of conversation entries
    """
    if only_latest_session:
        session_id = get_latest_session_id(user_id)
    return get_conversation_context(user_id, session_id)


def clear_session_history(user_id: str, session_id: str = None):
    """
    Clear conversation history for a user.
    
    Args:
        user_id: The user's ID
        session_id: Optional session ID (if None, clears all sessions)
    """
    db, conversation_collection = _get_collections()
    
    query = {"user_id": user_id}
    if session_id:
        query["session_id"] = session_id
    
    result = conversation_collection.delete_many(query)
    logger.info(f"Cleared {result.deleted_count} messages for user {user_id}, session {session_id}")
    
    # Also clear from chat_messages
    db.chat_messages.delete_many(query)
