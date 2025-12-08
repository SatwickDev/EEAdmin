"""
Guarantee Submission Routes Module
Contains routes for guarantee form submission and AI-powered guarantee vetting checks
"""

from flask import request, jsonify, session
from datetime import datetime


def register_guarantee_submission_routes(app, timing_aspect, login_required, logger, db, 
                                          get_conversation_context, handle_guarantee_vetting_check):
    """
    Register guarantee submission and AI vetting check routes
    
    Args:
        app: Flask application instance
        timing_aspect: Timing decorator for performance monitoring
        login_required: Login required decorator
        logger: Logger instance
        db: MongoDB database instance
        get_conversation_context: Function to get conversation context
        handle_guarantee_vetting_check: Function to handle guarantee vetting AI check
    """

    @app.route('/api/guarantee/submit', methods=['POST'])
    @login_required
    def submit_guarantee():
        """Handle Guarantee form submission"""
        try:
            data = request.json
            data['user_id'] = session.get('user_id')
            data['timestamp'] = datetime.utcnow()
            data['status'] = 'pending'

            # Generate Guarantee number if not provided
            if not data.get('guaranteeNumber'):
                data['guaranteeNumber'] = f"BG{datetime.now().strftime('%Y%m%d%H%M%S')}"

            # Store in database
            result = db.guarantee_transactions.insert_one(data)

            return jsonify({
                'success': True,
                'guaranteeNumber': data['guaranteeNumber'],
                'transactionId': str(result.inserted_id)
            })
        except Exception as e:
            logger.error(f"Error submitting Guarantee: {str(e)}")
            return jsonify({'error': 'Failed to submit Guarantee'}), 500

    @app.route("/AICheckGuaranteeVetting", methods=["POST"])
    @timing_aspect
    def post_ai_check_guarantee_vetting():
        """
        AI-powered guarantee vetting endpoint using:
        - blacklist_vetting_rules.json
        - guarantee_vetting_config_with_rules.yaml
        """
        try:
            user_id = session.get("user_id", "1517524")
            data = request.json
            logger.info(f"User {user_id} guarantee vetting context: {data}")

            context = get_conversation_context(user_id)
            result, status_code = handle_guarantee_vetting_check(data, context)

            return jsonify(result), status_code
        except Exception as e:
            logger.error(f"AI Guarantee Vetting Check Error: {e}", exc_info=True)
            return jsonify({"error": str(e)}), 500

    logger.info("Guarantee submission routes registered successfully")
