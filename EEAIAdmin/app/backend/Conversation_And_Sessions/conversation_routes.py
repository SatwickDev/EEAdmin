"""
Conversation & Sessions Routes Module
Contains all routes for chatbot conversation history, session management,
beneficiaries, templates, and smart suggestions
"""

from flask import request, jsonify, session
from datetime import datetime
from functools import wraps


def register_conversation_routes(app, logger, db, conversation_manager):
    """
    Register all conversation and session management routes
    
    Args:
        app: Flask application instance
        logger: Logger instance
        db: MongoDB database instance
        conversation_manager: ConversationManager instance
    """
    
    def require_auth(f):
        """Decorator to require authentication"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return jsonify({'error': 'Authentication required'}), 401
            return f(*args, **kwargs)
        return decorated_function

    # ==================== Conversation Routes ====================
    
    @app.route('/api/conversation/message', methods=['POST'])
    def add_conversation_message():
        """Add a new message to conversation history"""
        try:
            data = request.get_json()
            # Get user_id from session or request body
            user_id = session.get('user_id') or data.get('user_id')

            if not user_id:
                return jsonify({'error': 'User ID is required'}), 400

            session_id = data.get('session_id', session.get('session_id'))
            message = data.get('message', '')
            response = data.get('response', '')
            message_type = data.get('message_type', 'chat')
            metadata = data.get('metadata', {})

            if not message and not response:
                return jsonify({'error': 'Either message or response is required'}), 400

            message_id = conversation_manager.add_message(
                user_id=user_id,
                session_id=session_id,
                message=message,
                response=response,
                message_type=message_type,
                metadata=metadata
            )

            if message_id:
                return jsonify({
                    'success': True,
                    'message_id': message_id,
                    'timestamp': datetime.utcnow().isoformat()
                })
            else:
                return jsonify({'error': 'Failed to save message'}), 500

        except Exception as e:
            logger.error(f"Error adding message: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    @app.route('/api/conversation/history', methods=['GET'])
    def get_conversation_history():
        """Get conversation history for user"""
        try:
            # Check if user is authenticated via session or request args
            user_id = session.get('user_id') or request.args.get('user_id')

            if not user_id:
                # Return empty history for unauthenticated users
                return jsonify({
                    'success': True,
                    'conversations': [],
                    'count': 0,
                    'authenticated': False
                })

            session_id = request.args.get('session_id')
            limit = min(int(request.args.get('limit', 50)), 100)
            message_type = request.args.get('message_type')

            conversations = conversation_manager.get_conversation_history(
                user_id=user_id,
                session_id=session_id,
                limit=limit,
                message_type=message_type
            )

            # Convert ObjectId to string for JSON serialization
            for conv in conversations:
                conv['_id'] = str(conv['_id'])
                # Handle timestamp field - might be 'timestamp' or 'created_at'
                if 'timestamp' in conv and conv['timestamp']:
                    conv['timestamp'] = conv['timestamp'].isoformat()
                elif 'created_at' in conv and conv['created_at']:
                    conv['timestamp'] = conv['created_at'].isoformat()
                else:
                    conv['timestamp'] = datetime.utcnow().isoformat()

            return jsonify({
                'success': True,
                'conversations': conversations,
                'count': len(conversations),
                'authenticated': True
            })

        except Exception as e:
            logger.error(f"Error getting conversation history: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    @app.route('/api/conversation/suggestions', methods=['POST'])
    @require_auth
    def get_smart_suggestions():
        """Get smart template suggestions based on user input"""
        try:
            data = request.get_json()
            user_id = session['user_id']
            input_text = data.get('input_text', '')
            transaction_type = data.get('transaction_type')

            if not input_text:
                return jsonify({'error': 'Input text is required'}), 400

            suggestions = conversation_manager.get_smart_suggestions(
                user_id=user_id,
                input_text=input_text,
                transaction_type=transaction_type
            )

            return jsonify({
                'success': True,
                'suggestions': suggestions,
                'count': len(suggestions)
            })

        except Exception as e:
            logger.error(f"Error getting smart suggestions: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    # ==================== Beneficiary Routes ====================
    
    @app.route('/api/conversation/beneficiary', methods=['POST'])
    @require_auth
    def save_beneficiary():
        """Save beneficiary information for auto-fill"""
        try:
            data = request.get_json()
            user_id = session['user_id']
            name = data.get('name', '')
            account_number = data.get('account_number', '')
            bank_name = data.get('bank_name', '')
            swift_code = data.get('swift_code')

            if not name or not account_number or not bank_name:
                return jsonify({'error': 'Name, account number, and bank name are required'}), 400

            beneficiary_id = conversation_manager.save_beneficiary(
                user_id=user_id,
                name=name,
                account_number=account_number,
                bank_name=bank_name,
                swift_code=swift_code
            )

            if beneficiary_id:
                return jsonify({
                    'success': True,
                    'beneficiary_id': beneficiary_id
                })
            else:
                return jsonify({'error': 'Failed to save beneficiary'}), 500

        except Exception as e:
            logger.error(f"Error saving beneficiary: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    @app.route('/api/conversation/beneficiaries', methods=['GET'])
    @require_auth
    def get_beneficiaries():
        """Get user's beneficiaries for auto-complete"""
        try:
            user_id = session['user_id']
            search_query = request.args.get('q', '')
            limit = min(int(request.args.get('limit', 10)), 50)

            query = {"user_id": user_id}
            if search_query:
                query["$or"] = [
                    {"name": {"$regex": search_query, "$options": "i"}},
                    {"account_number": {"$regex": search_query, "$options": "i"}},
                    {"bank_name": {"$regex": search_query, "$options": "i"}}
                ]

            beneficiaries = list(conversation_manager.beneficiary_collection.find(query)
                                 .sort("frequency", -1).limit(limit))

            # Convert ObjectId to string
            for beneficiary in beneficiaries:
                beneficiary['_id'] = str(beneficiary['_id'])
                beneficiary['created_at'] = beneficiary['created_at'].isoformat()
                beneficiary['last_used'] = beneficiary['last_used'].isoformat()

            return jsonify({
                'success': True,
                'beneficiaries': beneficiaries,
                'count': len(beneficiaries)
            })

        except Exception as e:
            logger.error(f"Error getting beneficiaries: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    # ==================== Templates Routes ====================
    
    @app.route('/api/conversation/templates', methods=['GET'])
    @require_auth
    def get_templates():
        """Get user's templates"""
        try:
            user_id = session['user_id']
            category = request.args.get('category')
            limit = min(int(request.args.get('limit', 20)), 50)

            query = {"user_id": user_id}
            if category:
                query["category"] = category

            templates = list(conversation_manager.templates_collection.find(query)
                             .sort("usage_count", -1).limit(limit))

            # Convert ObjectId to string
            for template in templates:
                template['_id'] = str(template['_id'])
                template['created_at'] = template['created_at'].isoformat()
                template['last_used'] = template['last_used'].isoformat()

            return jsonify({
                'success': True,
                'templates': templates,
                'count': len(templates)
            })

        except Exception as e:
            logger.error(f"Error getting templates: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    # ==================== Session Management Routes ====================
    
    @app.route('/api/sessions', methods=['GET'])
    def get_chat_sessions():
        """Get all chat sessions for the current user"""
        try:
            # Try to get user_id from session first, then from query params
            user_id = session.get('user_id') or request.args.get('user_id')
            if not user_id:
                return jsonify({'error': 'Unauthorized'}), 401

            # Get all sessions from MongoDB
            sessions_list = list(db.chat_sessions.find(
                {'user_id': user_id},
                {'_id': 0, 'session_id': 1, 'created_at': 1, 'last_activity': 1, 'message_count': 1, 'title': 1,
                 'first_message': 1}
            ).sort('last_activity', -1))

            # Convert datetime objects to ISO format
            for sess in sessions_list:
                sess['created_at'] = sess['created_at'].isoformat() if 'created_at' in sess else None
                sess['last_activity'] = sess['last_activity'].isoformat() if 'last_activity' in sess else None
                sess['message_count'] = sess.get('message_count', 0)

            return jsonify({
                'success': True,
                'sessions': sessions_list
            })

        except Exception as e:
            logger.error(f"Error getting sessions: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    @app.route('/api/sessions/<session_id>/messages', methods=['GET'])
    def get_session_messages(session_id):
        """Get all messages for a specific session"""
        try:
            # Try to get user_id from session first, then from query params
            user_id = session.get('user_id') or request.args.get('user_id')
            if not user_id:
                return jsonify({'error': 'Unauthorized'}), 401

            # Verify session belongs to user
            chat_session = db.chat_sessions.find_one({
                'session_id': session_id,
                'user_id': user_id
            })

            if not chat_session:
                return jsonify({'error': 'Session not found'}), 404

            # Get messages
            messages = list(db.chat_messages.find(
                {'session_id': session_id},
                {'_id': 0}
            ).sort('timestamp', 1))

            # Convert timestamps
            for msg in messages:
                if 'timestamp' in msg:
                    msg['timestamp'] = msg['timestamp'].isoformat()

            return jsonify({
                'success': True,
                'messages': messages,
                'session_id': session_id
            })

        except Exception as e:
            logger.error(f"Error getting session messages: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    @app.route('/api/sessions/<session_id>', methods=['DELETE'])
    def delete_session(session_id):
        """Delete a specific chat session"""
        try:
            # Try to get user_id from session first, then from query params or body
            user_id = session.get('user_id') or request.args.get('user_id')
            if not user_id and request.is_json:
                user_id = request.get_json().get('user_id')
            if not user_id:
                return jsonify({'error': 'Unauthorized'}), 401

            # Verify session belongs to user
            chat_session = db.chat_sessions.find_one({
                'session_id': session_id,
                'user_id': user_id
            })

            if not chat_session:
                return jsonify({'error': 'Session not found'}), 404

            # Delete session and all related messages
            db.chat_sessions.delete_one({'session_id': session_id})
            db.chat_messages.delete_many({'session_id': session_id})

            return jsonify({
                'success': True,
                'message': 'Session deleted successfully'
            })

        except Exception as e:
            logger.error(f"Error deleting session: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    @app.route('/api/sessions/all', methods=['DELETE'])
    def delete_all_sessions():
        """Delete all chat sessions for the current user"""
        try:
            # Try to get user_id from session first, then from query params or body
            user_id = session.get('user_id') or request.args.get('user_id')
            if not user_id and request.is_json:
                user_id = request.get_json().get('user_id')
            if not user_id:
                return jsonify({'error': 'Unauthorized'}), 401

            # Verify confirmation
            data = request.get_json()
            if not data or not data.get('confirm'):
                return jsonify({'error': 'Confirmation required'}), 400

            # Get all user sessions
            user_sessions = list(db.chat_sessions.find(
                {'user_id': user_id},
                {'session_id': 1}
            ))

            session_ids = [sess['session_id'] for sess in user_sessions]

            # Delete all sessions and messages
            db.chat_sessions.delete_many({'user_id': user_id})
            db.chat_messages.delete_many({'session_id': {'$in': session_ids}})

            return jsonify({
                'success': True,
                'message': f'Deleted {len(session_ids)} sessions',
                'deleted_count': len(session_ids)
            })

        except Exception as e:
            logger.error(f"Error deleting all sessions: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    logger.info("Conversation & Sessions routes registered successfully")
