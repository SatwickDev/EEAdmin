"""
Page Routes Module
Contains all HTML page rendering routes for:
- Main application pages
- Trade Finance forms
- Document processing pages
- AI Chat interfaces
- Dashboard pages
- Utility pages
"""

from flask import render_template, request, redirect, url_for, session
from datetime import datetime, timedelta


def register_page_routes(app, timing_aspect, logger):
    """
    Register all page rendering routes
    
    Args:
        app: Flask application instance
        timing_aspect: Timing decorator for performance monitoring
        logger: Logger instance
    """

    # ==================== Main Application Pages ====================

    @app.route("/", methods=["GET"])
    @timing_aspect
    def main():
        """Serve the default chat interface."""
        return render_template("index.html")

    @app.route("/guarantee", methods=["GET"])
    @timing_aspect
    def index():
        """Serve the guarantee/rich chat interface."""
        return render_template("rich.html")

    @app.route("/website", methods=["GET"])
    @timing_aspect
    def website():
        """Serve the website index page."""
        return render_template("websiteIndex.html")

    @app.route("/fdoccheck", methods=["GET"])
    @timing_aspect
    def doc():
        """Serve the document check interface."""
        return render_template("doccheck.html")

    # ==================== AI Chat Interfaces ====================

    @app.route("/smart-chat", methods=["GET"])
    @timing_aspect
    def smart_chat():
        """Smart Banking Chat Interface"""
        return render_template("smart_chat.html")

    @app.route("/ai-chat", methods=["GET"])
    @timing_aspect
    def ai_chat():
        """Dashboard with Repository Tiles and Chatbot"""
        return render_template("ai_chat_dashboard.html")

    @app.route("/ai-chat-pro", methods=["GET"])
    @timing_aspect
    def ai_chat_pro():
        """Professional AI Chat Interface with Enhanced UI/UX"""
        return render_template("ai_chat_dashboard.html")

    @app.route("/ai_chat_modern", methods=["GET"])
    @timing_aspect
    def ai_chat_modern():
        """Chatbot interface for iframe/popup"""
        return render_template("ai_chat_modern.html")

    @app.route("/ai_chat_modern_overylay", methods=["GET"])
    @timing_aspect
    def ai_chat_modern_overylay():
        """Chatbot interface optimized for modal/overlay display without header"""
        return render_template("ai_chat_modern_overylay.html")

    @app.route('/components/ai_chatbot_popup')
    def ai_chatbot_popup():
        """Serve the AI chatbot popup component"""
        return render_template('components/ai_chatbot_popup.html')

    # ==================== Document Classification Pages ====================

    @app.route('/document-classification')
    def document_classification():
        """Document classification and compliance page"""
        return render_template('document_classification.html')

    @app.route('/document-classification-overlay')
    def document_classification_overlay():
        """Document classification with overlay header for modal/iframe use"""
        return render_template('document_classification_overlay.html')

    @app.route('/document-classification-embed')
    def document_classification_embed():
        """Embedded document classification for modal/iframe use"""
        return render_template('document_classification_embed.html')

    # ==================== Trade Finance Form Pages ====================

    @app.route('/forms_dashboard')
    def forms_dashboard():
        """Render the forms dashboard"""
        return render_template('forms_dashboard.html')

    @app.route('/trade_finance_guarantee_form')
    def trade_finance_guarantee_form():
        """Render the Trade Finance Guarantee form"""
        return render_template('trade_finance_guarantee_form.html')

    @app.route('/bank_guarantee_form')
    def bank_guarantee_form():
        """Render the Bank Guarantee form"""
        return render_template('trade_finance_guarantee_form.html')

    @app.route('/trade_finance')
    def trade_finance_unified():
        """Render the unified Trade Finance form with tabs"""
        return render_template('trade_finance_unified.html')

    @app.route('/trade_finance_dashboard')
    def trade_finance_dashboard():
        """Render the Trade Finance dashboard with service tiles"""
        return render_template('trade_finance_dashboard.html')

    @app.route('/treasury_management_form')
    def treasury_management_form():
        """Render the Treasury Management form"""
        return render_template('treasury_management_form.html')

    @app.route('/cash_management_form')
    def cash_management_form():
        """Render the Cash Management form"""
        return render_template('cash_management_form.html')

    # ==================== LC (Letter of Credit) Pages ====================

    @app.route('/lc_test_page')
    def lc_test_page():
        """Render the LC workflow test page"""
        return render_template('lc_test_page.html')

    @app.route('/lc_demo')
    def lc_demo():
        """Render the LC success page implementation demo"""
        return render_template('lc_demo.html')

    @app.route('/lc_success')
    def lc_success():
        """Render the LC submission success page"""
        # Get data from URL parameters
        lc_number = request.args.get('lcNumber')
        transaction_id = request.args.get('transactionId')
        return render_template('lc_success.html', lcNumber=lc_number, transactionId=transaction_id)

    @app.route('/load_template_demo')
    def load_template_demo():
        """Render the Load Template Sample button implementation demo"""
        return render_template('load_template_demo.html')

    # ==================== Guarantee Pages ====================

    @app.route('/guarantee_success')
    def guarantee_success():
        """Render the Guarantee submission success page"""
        # Get data from URL parameters
        guarantee_number = request.args.get('guaranteeNumber')
        transaction_id = request.args.get('transactionId')
        return render_template('guarantee_success.html', guaranteeNumber=guarantee_number, transactionId=transaction_id)

    # ==================== Compliance Pages ====================

    @app.route("/compliance-results", methods=["GET", "POST"])
    @timing_aspect
    def compliance_results():
        """Display compliance analysis results."""
        if request.method == "POST":
            # Store results in session for display
            from flask import jsonify
            session['compliance_results'] = request.get_json()
            return jsonify({"success": True})

        # GET request - display the results page
        results = session.get('compliance_results')
        if not results:
            # If no results, redirect back to guarantee page
            return redirect(url_for('index'))

        return render_template("compliance_results.html", results=results)

    @app.route('/compliance-checker')
    def compliance_checker_page():
        """Render the document compliance checker page"""
        return render_template('compliance_checker.html')

    # ==================== User Manual & Training Pages ====================

    @app.route('/train-user-manual')
    def train_user_manual_page():
        """Render the enhanced user manual training page"""
        return render_template('train_user_manual.html')

    # ==================== Custom Functions Pages ====================
    # Note: Custom functions page routes are registered in custom_functions_routes.py

    @app.route("/chat", methods=["GET"])
    @timing_aspect
    def canvas():
        """Serve the default chat interface."""
        return render_template("chat.html")

    # ==================== Document Register Pages ====================

    @app.route('/document-register')
    def document_register_page():
        """Document registration page with supporting documents upload"""
        return render_template('document_register.html')

    @app.route('/document_register', methods=['GET'])
    def document_register():
        """Render the document registration page (alternate route)"""
        try:
            # Get registration context from query params or session
            from flask import request
            registration_id = request.args.get('registrationId', '')
            lc_number = request.args.get('lcNumber', '')
            
            return render_template('document_register.html', 
                                 registration_id=registration_id,
                                 lc_number=lc_number)
        except Exception as e:
            logger.error(f"Error rendering document_register page: {str(e)}")
            return render_template('document_register.html')

    @app.route('/register_lc_docs', methods=['GET', 'POST'])
    def register_lc_docs():
        """Handle LC document registration continuation flow"""
        from flask import request, session
        from datetime import datetime
        
        if request.method == 'POST':
            try:
                # This route needs db access - import jsonify for JSON responses
                from flask import jsonify
                
                # Get form data with confirmed LC information
                form_data = request.form.to_dict()
                user_id = session.get('user_id', 'anonymous')
                current_timestamp = datetime.utcnow()
                
                lc_number = form_data.get('lcNumber')
                
                # Note: This POST handler requires database access
                # The actual database operation should be handled via API call
                # For now, return success and let frontend handle the redirect
                
                logger.info(f"LC {lc_number} registration request received")
                
                # Return success response and redirect to document_register
                return jsonify({
                    'success': True,
                    'message': 'LC registration confirmed. Proceeding to document upload.',
                    'registrationId': lc_number,
                    'redirectUrl': '/document_register'
                }), 200
                
            except Exception as e:
                logger.error(f"Error submitting LC registration: {str(e)}")
                from flask import jsonify
                return jsonify({
                    'success': False,
                    'message': f'Error submitting registration: {str(e)}'
                }), 500
        else:
            # Handle GET request - render the register LC docs page
            return render_template('register_lc_docs.html')

    logger.info("Page routes registered successfully")
