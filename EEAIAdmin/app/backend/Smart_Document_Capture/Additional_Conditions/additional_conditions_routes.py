"""
Additional Conditions Routes
============================

API routes for parsing and validating LC Additional Conditions.
"""

from flask import request, jsonify
import logging

from .lc_conditions_parser import LCConditionsParser
from .lc_conditions_validator import LCConditionsValidator

logger = logging.getLogger(__name__)


def register_additional_conditions_routes(app, timing_aspect):
    """Register all LC additional conditions routes."""

    @app.route('/api/parse-additional-conditions', methods=['POST'])
    @timing_aspect
    def parse_additional_conditions():
        """
        Parse LC Additional Conditions text into structured validation rules using LLM.
        Uses the modular LCConditionsParser component.
        """
        try:
            logger.info("")
            logger.info(f"{'='*100}")
            logger.info("📋 LC CONDITIONS PARSING - PARSE ADDITIONAL CONDITIONS")
            logger.info(f"{'='*100}")
            logger.info("🤖 Using: LCConditionsParser (Modular Component)")

            data = request.get_json()
            if not data:
                logger.error("❌ No data provided in request")
                return jsonify({'success': False, 'error': 'No data provided'}), 400

            additional_conditions_text = data.get('additional_conditions_text', '')
            lc_number = data.get('lc_number', 'Unknown')

            if not additional_conditions_text or additional_conditions_text.strip() == '':
                logger.error("❌ No additional conditions text provided")
                return jsonify({'success': False, 'error': 'No additional conditions text provided'}), 400

            logger.info(f"📋 LC Number: {lc_number}")
            logger.info(f"📊 Input Text Length: {len(additional_conditions_text)} characters")
            logger.info(f"{'='*100}")

            # Use the modular LCConditionsParser
            parser = LCConditionsParser()
            result = parser.parse_conditions(
                additional_conditions_text=additional_conditions_text,
                lc_number=lc_number
            )

            if result.get('success'):
                logger.info(f"✅ LC Conditions parsed successfully: {result.get('count', 0)} rules")
                return jsonify(result)
            else:
                logger.error(f"❌ LC Conditions parsing failed: {result.get('error', 'Unknown error')}")
                return jsonify(result), 500

        except Exception as e:
            logger.error(f"❌ Error parsing LC conditions: {e}")
            logger.exception("Full traceback:")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/validate-lc-conditions', methods=['POST'])
    @timing_aspect
    def validate_lc_conditions():
        """
        LLM-based validation of documents against LC Additional Conditions.
        Uses the modular LCConditionsValidator component.
        """
        try:
            logger.info("")
            logger.info(f"{'='*100}")
            logger.info("🚀 LC CONDITIONS VALIDATION - VALIDATE LC CONDITIONS")
            logger.info(f"{'='*100}")
            logger.info("🤖 Using: LCConditionsValidator (Modular Component)")

            data = request.get_json()
            if not data:
                logger.error("❌ No data provided in request")
                return jsonify({'success': False, 'error': 'No data provided'}), 400

            rules = data.get('rules', [])
            documents = data.get('documents', [])
            lc_data = data.get('lc_data', {})

            logger.info(f"📊 Input Data:")
            logger.info(f"   📋 Rules Count: {len(rules)}")
            logger.info(f"   📄 Documents Count: {len(documents)}")
            logger.info(f"   💼 LC Number: {lc_data.get('lcNumber', 'Unknown')}")

            if not rules:
                logger.error("❌ No validation rules provided")
                return jsonify({'success': False, 'error': 'No validation rules provided'}), 400

            if not documents:
                logger.error("❌ No documents provided")
                return jsonify({'success': False, 'error': 'No documents provided'}), 400

            logger.info(f"{'='*100}")

            # Use the modular LCConditionsValidator
            validator = LCConditionsValidator()
            result = validator.validate_conditions(
                rules=rules,
                documents=documents,
                lc_data=lc_data
            )

            if result.get('success'):
                logger.info(f"✅ LC Conditions validated successfully: {result.get('count', 0)} results")
                return jsonify(result)
            else:
                logger.error(f"❌ LC Conditions validation failed: {result.get('error', 'Unknown error')}")
                return jsonify(result), 500

        except Exception as e:
            logger.error(f"❌ Error validating LC conditions: {e}")
            logger.exception("Full traceback:")
            return jsonify({'success': False, 'error': str(e)}), 500
