"""
Auth_And_User_Management Module
================================

This module handles all authentication and user management functionality:
- User models and session models
- Input validation (email, password, name)
- User repository (CRUD operations)
- Session repository (create, get, delete sessions)
- Authentication decorators (login_required)
- Conversation/session management
- Auth route registration

Usage:
    from app.backend.Auth_And_User_Management import (
        # Models
        User,
        UserSession,
        
        # Validators
        validate_email,
        validate_password,
        validate_name,
        
        # Repositories
        UserRepository,
        SessionRepository,
        
        # Decorators
        login_required,
        
        # Session Management
        get_or_create_session,
        save_to_conversation,
        get_conversation_context,
        get_latest_session_id,
        retrieve_conversation_history,
        
        # Route Registration
        register_auth_routes,
        
        # Constants
        ALLOWED_EMAILS,
        SESSION_TIMEOUT_SECONDS
    )
"""

from .models import User, UserSession
from .validators import validate_email, validate_password, validate_name
from .repositories import UserRepository, SessionRepository
from .decorators import login_required, timing_aspect
from .session_manager import (
    get_or_create_session,
    save_to_conversation,
    get_conversation_context,
    get_latest_session_id,
    retrieve_conversation_history,
    initialize_collections as initialize_session_manager
)
from .auth_routes import register_auth_routes
from .constants import ALLOWED_EMAILS, SESSION_TIMEOUT_SECONDS

__all__ = [
    # Models
    'User',
    'UserSession',
    
    # Validators
    'validate_email',
    'validate_password',
    'validate_name',
    
    # Repositories
    'UserRepository',
    'SessionRepository',
    
    # Decorators
    'login_required',
    'timing_aspect',
    
    # Session Management
    'get_or_create_session',
    'save_to_conversation',
    'get_conversation_context',
    'get_latest_session_id',
    'retrieve_conversation_history',
    'initialize_session_manager',
    
    # Route Registration
    'register_auth_routes',
    
    # Constants
    'ALLOWED_EMAILS',
    'SESSION_TIMEOUT_SECONDS'
]
