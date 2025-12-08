"""
Authentication Decorators for Auth_And_User_Management module
"""

import logging
import time
from functools import wraps
from datetime import datetime

from flask import session, request, jsonify

logger = logging.getLogger(__name__)

# Reference to sessions collection - will be set during initialization
_sessions_collection = None


def initialize_sessions_collection(sessions_collection):
    """
    Initialize the sessions collection reference.
    Called from routes.py during app setup.
    """
    global _sessions_collection
    _sessions_collection = sessions_collection
    logger.info("Auth decorators: Sessions collection initialized")


def login_required(f):
    """
    Decorator to require authentication for a route.
    
    Checks:
    1. user_id and session_id are in the session
    2. The session exists in the database
    3. Updates last accessed timestamp
    
    Usage:
        @app.route('/protected')
        @login_required
        def protected_route():
            return jsonify({'message': 'You are authenticated'})
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user_id and session_id are in session
        if 'user_id' not in session or 'session_id' not in session:
            logger.error(
                f"Authentication failed: user_id={session.get('user_id', 'missing')}, "
                f"session_id={session.get('session_id', 'missing')}, "
                f"remote_addr={request.remote_addr}"
            )
            return jsonify({'success': False, 'message': 'Authentication required'}), 401
        
        # Validate session in database
        if _sessions_collection is not None:
            session_doc = _sessions_collection.find_one({'sessionId': session['session_id']})
            if not session_doc:
                logger.error(
                    f"Invalid session: session_id={session.get('session_id')}, "
                    f"remote_addr={request.remote_addr}"
                )
                session.clear()
                return jsonify({'success': False, 'message': 'Invalid session'}), 401
            
            # Update last accessed timestamp
            _sessions_collection.update_one(
                {'sessionId': session['session_id']},
                {'$set': {'lastAccessed': datetime.utcnow()}}
            )
        
        return f(*args, **kwargs)
    return decorated_function


def timing_aspect(f):
    """
    Decorator to measure and log execution time of a function.
    
    Usage:
        @app.route('/api/endpoint')
        @timing_aspect
        def endpoint():
            return jsonify({'message': 'success'})
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = time.time()
        result = f(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        
        logger.info(
            f"Request completed for endpoint: {f.__name__}, "
            f"duration: {execution_time:.3f} seconds"
        )
        
        return result
    return decorated_function


def admin_required(f):
    """
    Decorator to require admin privileges for a route.
    Must be used after @login_required.
    
    Usage:
        @app.route('/admin/settings')
        @login_required
        @admin_required
        def admin_settings():
            return jsonify({'message': 'Admin access granted'})
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from .constants import ALLOWED_EMAILS
        
        user_email = session.get('user_email', '').lower()
        allowed_emails_lower = [e.lower() for e in ALLOWED_EMAILS]
        
        if user_email not in allowed_emails_lower:
            logger.warning(
                f"Admin access denied for user: {user_email}, "
                f"remote_addr={request.remote_addr}"
            )
            return jsonify({
                'success': False, 
                'message': 'Admin privileges required'
            }), 403
        
        return f(*args, **kwargs)
    return decorated_function
