"""
Input Validators for Auth_And_User_Management module
"""

import re
from typing import Tuple


def validate_email(email: str) -> Tuple[bool, str]:
    """
    Validate email format.
    
    Args:
        email: Email address to validate
        
    Returns:
        Tuple of (is_valid, message)
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    is_valid = bool(re.match(pattern, email))
    message = "Valid email" if is_valid else "Invalid email format"
    return is_valid, message


def validate_password(password: str) -> Tuple[bool, str]:
    """
    Validate password strength.
    
    Requirements:
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one number
    
    Args:
        password: Password to validate
        
    Returns:
        Tuple of (is_valid, message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r"[0-9]", password):
        return False, "Password must contain at least one number"
    return True, "Valid password"


def validate_name(name: str) -> Tuple[bool, str]:
    """
    Validate name format.
    
    Requirements:
    - At least 2 characters
    - Only letters, spaces, or hyphens
    
    Args:
        name: Name to validate
        
    Returns:
        Tuple of (is_valid, message)
    """
    name = name.strip()
    if len(name) < 2:
        return False, "Name must be at least 2 characters long"
    if not re.match(r"^[a-zA-Z\s-]+$", name):
        return False, "Name can only contain letters, spaces, or hyphens"
    return True, "Valid name"
