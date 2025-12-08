"""
Required Documents Routes
=========================

API routes for parsing required documents from LC text.
"""

from flask import request, jsonify
import logging

from .required_documents_parser import RequiredDocumentsParser

logger = logging.getLogger(__name__)


def register_required_documents_routes(app, timing_aspect):
    """Register all required documents parsing routes."""

    @app.route('/api/parse-required-documents', methods=['POST'])
    @timing_aspect
    def parse_required_documents():
        """
        Parse required documents text into a structured checklist using LLM.
        Uses the modularized RequiredDocumentsParser from Required_Documents module.
        """
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'No data provided'}), 400

            required_documents_text = data.get('required_documents_text', '')
            document_type = data.get('document_type', 'Unknown')

            if not required_documents_text or required_documents_text.strip() == '':
                return jsonify({'success': False, 'error': 'No required documents text provided'}), 400

            logger.info("")
            logger.info(f"{'='*80}")
            logger.info("📄 REQUIRED DOCUMENTS PARSING - USING MODULAR PARSER")
            logger.info(f"{'='*80}")
            logger.info(f"📋 Document Type: {document_type}")
            logger.info(f"📊 Input Text Length: {len(required_documents_text)} characters")
            logger.info(f"📝 FULL INPUT TEXT (NO TRUNCATION):")
            logger.info(f"{'='*40} START OF INPUT {'='*40}")
            logger.info(required_documents_text)
            logger.info(f"{'='*40} END OF INPUT {'='*40}")
            logger.info(f"🔧 Using: RequiredDocumentsParser from Required_Documents module")
            
            # Use the modularized parser
            parser = RequiredDocumentsParser()
            result = parser.parse_documents(required_documents_text, document_type)
            
            logger.info(f"✅ Parser result: success={result.get('success')}, count={result.get('count')}")
            logger.info(f"{'='*80}")
            logger.info("")

            if result.get('success'):
                return jsonify({
                    'success': True,
                    'documents': result.get('documents', []),
                    'count': result.get('count', 0)
                })
            else:
                return jsonify({
                    'success': False,
                    'error': result.get('error', 'Unknown error'),
                    'documents': [],
                    'count': 0
                }), 400

        except Exception as e:
            logger.error(f"❌ Error parsing required documents: {e}")
            logger.exception("Full traceback:")
            return jsonify({'success': False, 'error': str(e)}), 500
