"""
User and Session Models for Auth_And_User_Management module
"""

from datetime import datetime
from typing import Any, Dict, Optional


class User:
    """User model for authentication and user management."""
    
    def __init__(
        self,
        first_name: str,
        last_name: str,
        email: str,
        password_hash: str,
        created_at: datetime = None,
        last_login: datetime = None,
        is_active: bool = True
    ):
        self.first_name = first_name.strip()
        self.last_name = last_name.strip()
        self.email = email.lower()
        self.password_hash = password_hash
        self.created_at = created_at or datetime.utcnow()
        self.last_login = last_login
        self.is_active = is_active

    def to_dict(self) -> Dict[str, Any]:
        """Convert User object to dictionary for MongoDB storage."""
        return {
            'firstName': self.first_name,
            'lastName': self.last_name,
            'email': self.email,
            'passwordHash': self.password_hash,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'lastLogin': self.last_login.isoformat() if self.last_login else None,
            'isActive': self.is_active
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'User':
        """Create User object from dictionary (MongoDB document)."""
        created_at = datetime.fromisoformat(data['createdAt']) if data.get('createdAt') else None
        last_login = datetime.fromisoformat(data['lastLogin']) if data.get('lastLogin') else None
        email = data.get('email', '')
        return User(
            first_name=data.get('firstName', ''),
            last_name=data.get('lastName', ''),
            email=email,
            password_hash=data.get('passwordHash', ''),
            created_at=created_at,
            last_login=last_login,
            is_active=data.get('isActive', True)
        )


class UserSession:
    """Session model for user session management."""
    
    def __init__(
        self,
        user_id: str,
        session_id: str,
        created_at: datetime = None,
        last_accessed: datetime = None,
        ip_address: str = None,
        user_agent: str = None
    ):
        self.user_id = user_id
        self.session_id = session_id
        self.created_at = created_at or datetime.utcnow()
        self.last_accessed = last_accessed or datetime.utcnow()
        self.ip_address = ip_address
        self.user_agent = user_agent

    def to_dict(self) -> Dict[str, Any]:
        """Convert UserSession object to dictionary for MongoDB storage."""
        return {
            'userId': str(self.user_id),
            'sessionId': self.session_id,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'lastAccessed': self.last_accessed.isoformat() if self.last_accessed else None,
            'ipAddress': self.ip_address,
            'userAgent': self.user_agent
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'UserSession':
        """Create UserSession object from dictionary (MongoDB document)."""
        created_at = datetime.fromisoformat(data['createdAt']) if data.get('createdAt') else None
        last_accessed = datetime.fromisoformat(data['lastAccessed']) if data.get('lastAccessed') else None
        return UserSession(
            user_id=data.get('userId', ''),
            session_id=data.get('sessionId', ''),
            created_at=created_at,
            last_accessed=last_accessed,
            ip_address=data.get('ipAddress'),
            user_agent=data.get('userAgent')
        )
