"""
User and Session Repositories for Auth_And_User_Management module
Handles database operations for users and sessions.
"""

import uuid
import logging
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

import bcrypt
from bson import ObjectId
from pymongo import MongoClient

from .validators import validate_email, validate_name
from app.utils import mongodb_manager

logger = logging.getLogger(__name__)

# MongoDB connection - will be initialized when module is imported
_db = None
_users_collection = None
_sessions_collection = None


def _get_db():
    """Get MongoDB database connection."""
    global _db, _users_collection, _sessions_collection
    if _db is None:
        try:
            # Use mongodb_manager for environment-aware connection
            client = mongodb_manager.get_mongo_client()
            if client is None:
                raise Exception("MongoDB is not available or disabled")
            
            db_name = mongodb_manager.get_database_name()
            _db = client[db_name]
            _users_collection = _db["users"]
            _sessions_collection = _db["sessions"]
        except Exception as e:
            logger.error(f"Failed to initialize MongoDB collections: {e}")
            raise
    return _db, _users_collection, _sessions_collection


def initialize_db(db, users_collection, sessions_collection):
    """
    Initialize database connections from external source (e.g., routes.py).
    This allows the module to use the same DB connection as the main app.
    """
    global _db, _users_collection, _sessions_collection
    _db = db
    _users_collection = users_collection
    _sessions_collection = sessions_collection
    logger.info("Auth_And_User_Management: Database connections initialized")


class UserRepository:
    """Repository for user database operations."""
    
    @staticmethod
    def create_user(user_data: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Create a new user in the database.
        
        Args:
            user_data: Dictionary containing firstName, lastName, email, password
            
        Returns:
            Tuple of (user_doc, error_message)
        """
        try:
            _, users_collection, _ = _get_db()
            
            # Validate email
            email_valid, email_msg = validate_email(user_data['email'])
            if not email_valid:
                return None, email_msg
            
            # Validate first name
            fname_valid, fname_msg = validate_name(user_data['firstName'])
            if not fname_valid:
                return None, fname_msg
            
            # Validate last name
            lname_valid, lname_msg = validate_name(user_data['lastName'])
            if not lname_valid:
                return None, lname_msg

            # Check if user already exists
            if users_collection.find_one({'email': user_data['email'].lower()}):
                return None, "User with this email already exists"

            # Hash password using bcrypt
            password = user_data['password'].encode('utf-8')
            password_hash = bcrypt.hashpw(password, bcrypt.gensalt()).decode('utf-8')
            
            user_doc = {
                'firstName': user_data['firstName'].strip(),
                'lastName': user_data['lastName'].strip(),
                'email': user_data['email'].lower(),
                'passwordHash': password_hash,
                'createdAt': datetime.utcnow(),
                'lastLogin': None,
                'isActive': True
            }
            
            result = users_collection.insert_one(user_doc)
            user_doc['_id'] = str(result.inserted_id)
            
            logger.info(f"Created new user: {user_data['email']}")
            return user_doc, None
            
        except Exception as e:
            logger.error(f"Error creating user: {e}", exc_info=True)
            return None, f"Failed to create user: {str(e)}"

    @staticmethod
    def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
        """
        Find a user by email address.
        
        Args:
            email: Email address to search for
            
        Returns:
            User document or None if not found
        """
        try:
            _, users_collection, _ = _get_db()
            user_doc = users_collection.find_one({'email': email.lower()})
            if user_doc:
                user_doc['_id'] = str(user_doc['_id'])
            return user_doc
        except Exception as e:
            logger.error(f"Error finding user by email {email}: {e}", exc_info=True)
            return None

    @staticmethod
    def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
        """
        Find a user by their ID.
        
        Args:
            user_id: User's MongoDB ObjectId as string
            
        Returns:
            User document or None if not found
        """
        try:
            _, users_collection, _ = _get_db()
            user_doc = users_collection.find_one({'_id': ObjectId(user_id)})
            if user_doc:
                user_doc['_id'] = str(user_doc['_id'])
            return user_doc
        except Exception as e:
            logger.error(f"Error finding user by ID {user_id}: {e}", exc_info=True)
            return None

    @staticmethod
    def update_last_login(user_id: str):
        """
        Update the last login timestamp for a user.
        
        Args:
            user_id: User's MongoDB ObjectId as string
        """
        try:
            _, users_collection, _ = _get_db()
            users_collection.update_one(
                {'_id': ObjectId(user_id)},
                {'$set': {'lastLogin': datetime.utcnow()}}
            )
        except Exception as e:
            logger.error(f"Error updating last login for user {user_id}: {e}", exc_info=True)

    @staticmethod
    def verify_password(stored_hash: str, password: str) -> bool:
        """
        Verify a password against a stored hash.
        
        Args:
            stored_hash: The bcrypt hash stored in the database
            password: The plaintext password to verify
            
        Returns:
            True if password matches, False otherwise
        """
        try:
            return bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8'))
        except Exception as e:
            logger.error(f"Error verifying password: {e}", exc_info=True)
            return False


class SessionRepository:
    """Repository for session database operations."""
    
    @staticmethod
    def create_session(user_id: str, ip_address: str = None, user_agent: str = None) -> Optional[str]:
        """
        Create a new session for a user.
        
        Args:
            user_id: User's MongoDB ObjectId as string
            ip_address: Client's IP address
            user_agent: Client's user agent string
            
        Returns:
            Session ID or None if creation failed
        """
        try:
            _, _, sessions_collection = _get_db()
            session_id = str(uuid.uuid4())
            session_doc = {
                'userId': ObjectId(user_id),
                'sessionId': session_id,
                'createdAt': datetime.utcnow(),
                'lastAccessed': datetime.utcnow(),
                'ipAddress': ip_address,
                'userAgent': user_agent
            }
            sessions_collection.insert_one(session_doc)
            logger.info(f"Created session {session_id} for user {user_id}")
            return session_id
        except Exception as e:
            logger.error(f"Error creating session for user {user_id}: {e}", exc_info=True)
            return None

    @staticmethod
    def get_session(session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a session by its ID.
        
        Args:
            session_id: The session ID to look up
            
        Returns:
            Session document or None if not found
        """
        try:
            _, _, sessions_collection = _get_db()
            session_doc = sessions_collection.find_one({'sessionId': session_id})
            if session_doc:
                session_doc['userId'] = str(session_doc['userId'])
            return session_doc
        except Exception as e:
            logger.error(f"Error finding session {session_id}: {e}", exc_info=True)
            return None

    @staticmethod
    def update_last_accessed(session_id: str):
        """
        Update the last accessed timestamp for a session.
        
        Args:
            session_id: The session ID to update
        """
        try:
            _, _, sessions_collection = _get_db()
            sessions_collection.update_one(
                {'sessionId': session_id},
                {'$set': {'lastAccessed': datetime.utcnow()}}
            )
        except Exception as e:
            logger.error(f"Error updating last accessed for session {session_id}: {e}", exc_info=True)

    @staticmethod
    def delete_session(session_id: str):
        """
        Delete a session.
        
        Args:
            session_id: The session ID to delete
        """
        try:
            _, _, sessions_collection = _get_db()
            sessions_collection.delete_one({'sessionId': session_id})
            logger.info(f"Deleted session {session_id}")
        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {e}", exc_info=True)

    @staticmethod
    def delete_user_sessions(user_id: str):
        """
        Delete all sessions for a user.
        
        Args:
            user_id: User's MongoDB ObjectId as string
        """
        try:
            _, _, sessions_collection = _get_db()
            result = sessions_collection.delete_many({'userId': ObjectId(user_id)})
            logger.info(f"Deleted {result.deleted_count} sessions for user {user_id}")
        except Exception as e:
            logger.error(f"Error deleting sessions for user {user_id}: {e}", exc_info=True)
