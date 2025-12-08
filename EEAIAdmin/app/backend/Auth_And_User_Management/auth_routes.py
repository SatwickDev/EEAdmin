"""
Authentication Routes for Auth_And_User_Management module
Handles login, register, logout, and user info endpoints.
"""

import logging
from datetime import datetime

from flask import Flask, request, session, jsonify

from .constants import ALLOWED_EMAILS
from .validators import validate_email, validate_password, validate_name
from .repositories import UserRepository, SessionRepository
from .decorators import login_required, timing_aspect

logger = logging.getLogger(__name__)


def register_auth_routes(app: Flask):
    """
    Register authentication routes with the Flask app.
    
    Routes registered:
    - POST /auth/login - User login
    - POST /auth/register - User registration
    - GET /auth/protected - Protected route test
    - GET /auth/current-user - Get current user info
    - GET /auth/guest-user - Get guest user info
    - POST /auth/logout - User logout
    
    Args:
        app: Flask application instance
    """
    
    @app.route("/auth/login", methods=["POST"])
    @timing_aspect
    def login():
        """Handle user login and create a session."""
        try:
            # Try to import daily logger
            try:
                from app.utils.daily_logger import log_authentication, log_error
                has_daily_logger = True
            except ImportError:
                has_daily_logger = False
            
            if has_daily_logger:
                log_authentication("LOGIN_ATTEMPT", user_id="unknown", 
                                 ip_address=request.remote_addr)
            
            data = request.get_json()
            if not data or not data.get("email") or not data.get("password"):
                if has_daily_logger:
                    log_authentication("LOGIN_FAILED", user_id="unknown", 
                                     reason="Missing credentials", ip_address=request.remote_addr)
                return jsonify({"success": False, "message": "Email and password are required"}), 400

            user = UserRepository.get_user_by_email(data["email"])
            if not user:
                if has_daily_logger:
                    log_authentication("LOGIN_FAILED", user_id="unknown", 
                                     email=data["email"], reason="User not found",
                                     ip_address=request.remote_addr)
                return jsonify({"success": False, "message": "Invalid email or password"}), 401

            # Verify password
            if not UserRepository.verify_password(user["passwordHash"], data["password"]):
                if has_daily_logger:
                    log_authentication("LOGIN_FAILED", user_id=user["_id"], 
                                     email=data["email"], reason="Invalid password",
                                     ip_address=request.remote_addr)
                return jsonify({"success": False, "message": "Invalid email or password"}), 401

            # Update last login
            UserRepository.update_last_login(user["_id"])

            # Create session
            session_id = SessionRepository.create_session(
                user_id=user["_id"],
                ip_address=request.remote_addr,
                user_agent=request.headers.get("User-Agent")
            )
            if not session_id:
                return jsonify({"success": False, "message": "Failed to create session"}), 500

            # Set session data
            session["user_id"] = user["_id"]
            session["session_id"] = session_id
            session["user_email"] = user["email"]

            # Check admin status
            is_admin = user["email"].lower() in [e.lower() for e in ALLOWED_EMAILS]
            
            if has_daily_logger:
                log_authentication("LOGIN_SUCCESS", user_id=user["_id"], 
                                 email=user["email"], is_admin=is_admin,
                                 ip_address=request.remote_addr, session_id=session_id)
            
            logger.info(f"Login - User: {user['email']}, isAdmin: {is_admin}, ALLOWED_EMAILS: {ALLOWED_EMAILS}")

            return jsonify({
                "success": True,
                "message": "Login successful",
                "user": {
                    "id": user["_id"],
                    "firstName": user["firstName"],
                    "lastName": user["lastName"],
                    "email": user["email"],
                    "isAllowed": is_admin,
                    "isAdmin": is_admin
                }
            }), 200

        except Exception as e:
            logger.error(f"Login error for email {data.get('email', 'unknown')}: {e}", exc_info=True)
            return jsonify({"success": False, "message": "An error occurred during login"}), 500

    @app.route("/auth/register", methods=["POST"])
    @timing_aspect
    def register():
        """Handle user registration."""
        try:
            data = request.get_json()
            required_fields = ["firstName", "lastName", "email", "password"]
            if not data or not all(field in data for field in required_fields):
                return jsonify({"success": False, "message": "All fields are required"}), 400

            # Validate all fields
            email_valid, email_msg = validate_email(data["email"])
            if not email_valid:
                return jsonify({"success": False, "message": email_msg}), 400

            fname_valid, fname_msg = validate_name(data["firstName"])
            if not fname_valid:
                return jsonify({"success": False, "message": fname_msg}), 400

            lname_valid, lname_msg = validate_name(data["lastName"])
            if not lname_valid:
                return jsonify({"success": False, "message": lname_msg}), 400

            password_valid, password_msg = validate_password(data["password"])
            if not password_valid:
                return jsonify({"success": False, "message": password_msg}), 400

            # Create user
            user_data = {
                "firstName": data["firstName"],
                "lastName": data["lastName"],
                "email": data["email"],
                "password": data["password"]
            }
            user, error = UserRepository.create_user(user_data)
            if error:
                return jsonify({"success": False, "message": error}), 400

            logger.info(f"New user registered: {data['email']}")

            return jsonify({
                "success": True,
                "message": "Registration successful",
                "user": {
                    "id": user["_id"],
                    "firstName": user["firstName"],
                    "lastName": user["lastName"],
                    "email": user["email"]
                }
            }), 201

        except Exception as e:
            logger.error(f"Registration error: {e}", exc_info=True)
            return jsonify({"success": False, "message": "An error occurred during registration"}), 500

    @app.route("/auth/protected", methods=["GET"])
    @login_required
    @timing_aspect
    def protected():
        """Protected route to test authentication."""
        try:
            if 'user_id' not in session:
                logger.error(f"Missing user_id in session for protected route, remote_addr={request.remote_addr}")
                return jsonify({"success": False, "message": "Session invalid, please log in again"}), 401
            
            user = UserRepository.get_user_by_id(session["user_id"])
            if not user:
                session.clear()
                return jsonify({"success": False, "message": "User not found"}), 401
            
            return jsonify({
                "success": True,
                "user": {
                    "id": user["_id"],
                    "firstName": user["firstName"],
                    "lastName": user["lastName"],
                    "email": user["email"]
                }
            }), 200
        except Exception as e:
            logger.error(f"Protected route error: {e}, remote_addr={request.remote_addr}", exc_info=True)
            return jsonify({"success": False, "message": "An error occurred"}), 500

    @app.route("/auth/current-user", methods=["GET"])
    @login_required
    @timing_aspect
    def get_current_user():
        """Get current user information including admin status."""
        try:
            if 'user_id' not in session:
                return jsonify({"success": False, "message": "Session invalid"}), 401
            
            user = UserRepository.get_user_by_id(session["user_id"])
            if not user:
                session.clear()
                return jsonify({"success": False, "message": "User not found"}), 401
            
            # Check if user is admin
            is_allowed = user["email"].lower() in [e.lower() for e in ALLOWED_EMAILS]
            
            logger.info(f"Current user check - Email: {user['email']}, isAllowed: {is_allowed}, ALLOWED_EMAILS: {ALLOWED_EMAILS}")
            
            response_data = {
                "success": True,
                "user": {
                    "id": user["_id"],
                    "firstName": user["firstName"],
                    "lastName": user["lastName"],
                    "email": user["email"],
                    "isAllowed": is_allowed,
                    "isAdmin": is_allowed
                }
            }
            
            logger.info(f"Returning user data with isAdmin={is_allowed} for {user['email']}")
            
            return jsonify(response_data), 200
        except Exception as e:
            logger.error(f"Get current user error: {e}", exc_info=True)
            return jsonify({"success": False, "message": "An error occurred"}), 500

    @app.route("/auth/guest-user", methods=["GET"])
    def get_guest_user():
        """Get guest user information for unauthenticated access."""
        try:
            response_data = {
                "success": True,
                "user": {
                    "id": "guest_user",
                    "firstName": "Guest",
                    "lastName": "User",
                    "email": "guest@example.com",
                    "isAllowed": True,
                    "isAdmin": False,
                    "isGuest": True
                }
            }

            logger.info("Returning guest user data")
            return jsonify(response_data), 200
        except Exception as e:
            logger.error(f"Get guest user error: {e}", exc_info=True)
            return jsonify({"success": False, "message": "An error occurred"}), 500

    @app.route("/auth/logout", methods=["POST"])
    @timing_aspect
    def logout():
        """Handle user logout."""
        try:
            if "session_id" in session:
                SessionRepository.delete_session(session["session_id"])
                logger.info(f"User logged out: session_id={session['session_id']}")
            session.clear()
            return jsonify({"success": True, "message": "Logged out successfully"}), 200
        except Exception as e:
            logger.error(f"Logout error: {e}", exc_info=True)
            return jsonify({"success": False, "message": "An error occurred during logout"}), 500

    logger.info("✅ Auth routes registered successfully")
