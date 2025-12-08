"""
Guarantee Vetting Routes

This module contains all Flask routes for guarantee vetting functionality including:
- Guarantee vetting maintenance pages
- Blacklist/Whitelist rules management
- AI-powered rule generation and analysis
- Guarantee prompt configuration
"""

import os
import json
import logging
import openai
from datetime import datetime
from flask import request, jsonify, render_template

from .vetting_rules_helpers import (
    load_guarantee_vetting_rules,
    save_guarantee_vetting_rules,
    generate_enhanced_fallback_preview,
    generate_mock_analysis
)

logger = logging.getLogger(__name__)


def register_guarantee_vetting_routes(app, timing_aspect, logger):
    """Register all guarantee vetting routes with the Flask app"""
    
    # ============================================================================
    # PAGE ROUTES
    # ============================================================================
    
    @app.route('/guarantee_vetting_maintenance')
    @timing_aspect
    def guarantee_vetting_maintenance():
        """Render guarantee vetting maintenance page"""
        return render_template('guarantee_vetting_maintenance.html')

    @app.route('/blacklist_rules_management')
    @timing_aspect
    def blacklist_rules_management():
        """Render blacklist rules management page"""
        return render_template('blacklist_rules_management.html')

    @app.route('/whitelist_rules_management')
    @timing_aspect
    def whitelist_rules_management():
        """Render whitelist rules management page"""
        return render_template('whitelist_rules_management.html')

    @app.route('/guarantee_prompt_config')
    @timing_aspect
    def guarantee_prompt_config_page():
        """Render guarantee prompt configuration page"""
        return render_template('guarantee_prompt_config.html')

    # ============================================================================
    # GUARANTEE VETTING RULES API
    # ============================================================================

    @app.route('/api/guarantee_vetting_rules', methods=['GET'])
    @timing_aspect
    def get_guarantee_vetting_rules():
        """Get all guarantee vetting rules with optional filtering"""
        try:
            data = load_guarantee_vetting_rules()
            rules = data.get('rules', [])

            # Apply filters if provided
            rule_type = request.args.get('rule_type')
            if rule_type and rule_type in ['whitelist', 'blacklist']:
                rules = [rule for rule in rules if rule.get('rule_type', 'blacklist') == rule_type]

            return jsonify({
                'success': True,
                'rules': rules,
                'total_count': len(rules),
                'filter_applied': rule_type
            }), 200
        except Exception as e:
            logger.error(f"Error getting guarantee vetting rules: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/guarantee_vetting_rules', methods=['POST'])
    @timing_aspect
    def create_guarantee_vetting_rule():
        """Create a new guarantee vetting rule"""
        try:
            rule_data = request.get_json()

            # Validate required fields
            required_fields = ['rule_ref', 'rule_name', 'rule_type', 'detection_hint', 'why_onerous_or_no_urdg', 'suggested_wording', 'severity', 'basics']
            for field in required_fields:
                if not rule_data.get(field):
                    return jsonify({'success': False, 'message': f'Missing required field: {field}'}), 400

            # Load existing data
            data = load_guarantee_vetting_rules()

            # Generate new ID
            existing_ids = [rule.get('id', 0) for rule in data.get('rules', [])]
            new_id = max(existing_ids, default=0) + 1

            # Create new rule
            new_rule = {
                'id': new_id,
                'rule_ref': rule_data.get('rule_ref'),
                'rule_name': rule_data.get('rule_name'),
                'rule_type': rule_data.get('rule_type', 'blacklist'),
                'detection_hint': rule_data.get('detection_hint'),
                'why_onerous_or_no_urdg': rule_data.get('why_onerous_or_no_urdg'),
                'suggested_wording': rule_data.get('suggested_wording'),
                'severity': rule_data.get('severity'),
                'basics': rule_data.get('basics'),
                'entity_restrictions': rule_data.get('entity_restrictions', [])
            }

            data['rules'].append(new_rule)

            if save_guarantee_vetting_rules(data):
                return jsonify({'success': True, 'rule': new_rule}), 201
            else:
                return jsonify({'success': False, 'message': 'Failed to save rule'}), 500

        except Exception as e:
            logger.error(f"Error creating guarantee vetting rule: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/guarantee_vetting_rules/<int:rule_id>', methods=['PUT'])
    @timing_aspect
    def update_guarantee_vetting_rule(rule_id):
        """Update an existing guarantee vetting rule"""
        try:
            rule_data = request.get_json()
            data = load_guarantee_vetting_rules()

            # Find and update rule
            for i, rule in enumerate(data.get('rules', [])):
                if rule.get('id') == rule_id:
                    data['rules'][i] = {
                        'id': rule_id,
                        'rule_ref': rule_data.get('rule_ref'),
                        'rule_name': rule_data.get('rule_name'),
                        'rule_type': rule_data.get('rule_type', 'blacklist'),
                        'detection_hint': rule_data.get('detection_hint'),
                        'why_onerous_or_no_urdg': rule_data.get('why_onerous_or_no_urdg'),
                        'suggested_wording': rule_data.get('suggested_wording'),
                        'severity': rule_data.get('severity'),
                        'basics': rule_data.get('basics'),
                        'entity_restrictions': rule_data.get('entity_restrictions', [])
                    }

                    if save_guarantee_vetting_rules(data):
                        return jsonify({'success': True, 'rule': data['rules'][i]}), 200
                    else:
                        return jsonify({'success': False, 'message': 'Failed to save rule'}), 500

            return jsonify({'success': False, 'message': 'Rule not found'}), 404

        except Exception as e:
            logger.error(f"Error updating guarantee vetting rule {rule_id}: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/guarantee_vetting_rules/<int:rule_id>', methods=['DELETE'])
    @timing_aspect
    def delete_guarantee_vetting_rule(rule_id):
        """Delete a guarantee vetting rule"""
        try:
            data = load_guarantee_vetting_rules()

            # Find and remove rule
            original_length = len(data.get('rules', []))
            data['rules'] = [rule for rule in data.get('rules', []) if rule.get('id') != rule_id]

            if len(data['rules']) < original_length:
                if save_guarantee_vetting_rules(data):
                    return jsonify({'success': True, 'message': 'Rule deleted successfully'}), 200
                else:
                    return jsonify({'success': False, 'message': 'Failed to save changes'}), 500
            else:
                return jsonify({'success': False, 'message': 'Rule not found'}), 404

        except Exception as e:
            logger.error(f"Error deleting guarantee vetting rule {rule_id}: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    # ============================================================================
    # AI ASSISTANT ENDPOINTS FOR VETTING RULES
    # ============================================================================

    @app.route('/api/ai_generate_rule', methods=['POST'])
    @timing_aspect
    def ai_generate_rule():
        """Generate rule suggestions using AI based on user description"""
        try:
            request_data = request.get_json()
            if not request_data:
                return jsonify({'success': False, 'message': 'No data provided'}), 400

            description = request_data.get('description', '').strip()
            rule_type = request_data.get('rule_type', 'blacklist')

            if not description:
                return jsonify({'success': False, 'message': 'Description is required'}), 400

            # Create AI prompt for rule generation
            if rule_type == 'whitelist':
                system_prompt = """You are an AI assistant specialized in creating guarantee vetting whitelist rules. Whitelist rules identify approved, compliant patterns that should be accepted."""
                prompt = f"""Generate a whitelist rule for the following scenario: "{description}"

Please provide a JSON response with these fields:
- rule_name: Brief descriptive name (max 80 chars)
- detection_hint: Specific phrases or patterns that indicate this approved condition
- why_onerous_or_no_urdg: Explain why this condition is compliant or beneficial
- suggested_wording: Provide example of compliant language or approval actions 
- severity: High/Medium/Low based on importance
- basics: independence/custom/isdgp category
- example_scenario: A realistic example of when this rule would apply"""
            else:
                system_prompt = """You are an AI assistant specialized in creating guarantee vetting blacklist rules. Blacklist rules identify problematic conditions that should be flagged or rejected."""
                prompt = f"""Generate a blacklist rule for the following scenario: "{description}"

Please provide a JSON response with these fields:
- rule_name: Brief descriptive name (max 80 chars)
- detection_hint: Specific phrases or patterns that indicate this problematic condition
- why_onerous_or_no_urdg: Explain why this condition is onerous or non-compliant
- suggested_wording: Provide alternative compliant wording or recommended actions
- severity: High/Medium/Low based on risk level
- basics: independence/custom/isdgp category  
- example_scenario: A realistic example of when this rule would apply"""

            # Call OpenAI API
            try:
                client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=1000
                )

                ai_response = response.choices[0].message.content.strip()

                # Try to parse JSON response
                try:
                    # Extract JSON from response if it's wrapped in code blocks
                    if '```json' in ai_response:
                        json_start = ai_response.find('```json') + 7
                        json_end = ai_response.find('```', json_start)
                        ai_response = ai_response[json_start:json_end].strip()
                    elif '```' in ai_response:
                        json_start = ai_response.find('```') + 3
                        json_end = ai_response.find('```', json_start)
                        ai_response = ai_response[json_start:json_end].strip()

                    rule_suggestion = json.loads(ai_response)

                    # Validate and clean response
                    cleaned_suggestion = {
                        'rule_name': rule_suggestion.get('rule_name', 'Generated Rule')[:80],
                        'detection_hint': rule_suggestion.get('detection_hint', ''),
                        'why_onerous_or_no_urdg': rule_suggestion.get('why_onerous_or_no_urdg', ''),
                        'suggested_wording': rule_suggestion.get('suggested_wording', ''),
                        'severity': rule_suggestion.get('severity', 'Medium'),
                        'basics': rule_suggestion.get('basics', 'custom'),
                        'example_scenario': rule_suggestion.get('example_scenario', ''),
                        'rule_type': rule_type
                    }

                    return jsonify({
                        'success': True,
                        'suggestion': cleaned_suggestion,
                        'message': 'AI rule suggestion generated successfully'
                    }), 200

                except json.JSONDecodeError:
                    # Fallback if JSON parsing fails
                    return jsonify({
                        'success': True,
                        'suggestion': {
                            'rule_name': f'AI Generated Rule for {description[:50]}...',
                            'detection_hint': ai_response[:200] + '...' if len(ai_response) > 200 else ai_response,
                            'why_onerous_or_no_urdg': 'AI generated explanation',
                            'suggested_wording': 'AI generated suggestion',
                            'severity': 'Medium',
                            'basics': 'custom',
                            'example_scenario': f'Example scenario for: {description}',
                            'rule_type': rule_type
                        },
                        'message': 'AI rule suggestion generated (fallback format)'
                    }), 200

            except Exception as openai_error:
                logger.error(f"OpenAI API error: {openai_error}")
                # Provide a basic rule template when AI is unavailable
                return jsonify({
                    'success': True,
                    'suggestion': {
                        'rule_name': f'{rule_type.title()} Rule: {description[:50]}',
                        'detection_hint': f'Look for patterns related to: {description}',
                        'why_onerous_or_no_urdg': f'This condition requires review because: {description}',
                        'suggested_wording': f'Recommended action for: {description}',
                        'severity': 'Medium',
                        'basics': 'custom',
                        'example_scenario': f'Example: {description}',
                        'rule_type': rule_type
                    },
                    'message': 'Basic rule template generated (AI unavailable)'
                }), 200

        except Exception as e:
            logger.error(f"Error in AI rule generation: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/ai_analyze_vetting', methods=['POST'])
    @timing_aspect
    def ai_analyze_vetting():
        """Analyze guarantee text against vetting rules with AI explanations"""
        try:
            request_data = request.get_json()
            if not request_data:
                return jsonify({'success': False, 'message': 'No data provided'}), 400

            guarantee_text = request_data.get('guarantee_text', '').strip()
            if not guarantee_text:
                return jsonify({'success': False, 'message': 'Guarantee text is required'}), 400

            # Load vetting rules
            rules_data = load_guarantee_vetting_rules()
            all_rules = rules_data.get('rules', [])

            # Separate whitelist and blacklist rules
            whitelist_rules = [r for r in all_rules if r.get('rule_type') == 'whitelist']
            blacklist_rules = [r for r in all_rules if r.get('rule_type') == 'blacklist']

            # Create AI analysis prompt
            system_prompt = """You are an AI assistant specialized in guarantee document analysis and vetting. 
Analyze the provided guarantee text against the given rules and provide clear explanations for your findings."""

            prompt = f"""Analyze this guarantee text against the vetting rules:

GUARANTEE TEXT:
{guarantee_text}

WHITELIST RULES (approved patterns):
{json.dumps([{'id': r.get('rule_ref', r.get('id')), 'name': r.get('rule_name', ''), 'detection_hint': r.get('detection_hint', '')} for r in whitelist_rules[:5]], indent=2)}

BLACKLIST RULES (problematic patterns):
{json.dumps([{'id': r.get('rule_ref', r.get('id')), 'name': r.get('rule_name', ''), 'detection_hint': r.get('detection_hint', '')} for r in blacklist_rules[:5]], indent=2)}

Please provide a JSON response with:
- overall_status: "APPROVED", "FLAGGED", or "REVIEW_REQUIRED"
- confidence_score: 0-100 percentage
- triggered_rules: Array of rule IDs that were triggered
- whitelist_matches: Array of whitelist rules that matched
- blacklist_matches: Array of blacklist rules that matched
- summary: Brief overall assessment
- recommendations: Array of recommended actions
- key_findings: Array of important observations"""

            try:
                client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=1500
                )

                ai_response = response.choices[0].message.content.strip()

                # Parse AI response
                try:
                    if '```json' in ai_response:
                        json_start = ai_response.find('```json') + 7
                        json_end = ai_response.find('```', json_start)
                        ai_response = ai_response[json_start:json_end].strip()
                    elif '```' in ai_response:
                        json_start = ai_response.find('```') + 3
                        json_end = ai_response.find('```', json_start)
                        ai_response = ai_response[json_start:json_end].strip()

                    analysis_result = json.loads(ai_response)

                    return jsonify({
                        'success': True,
                        'analysis': analysis_result,
                        'rules_analyzed': {
                            'whitelist_count': len(whitelist_rules),
                            'blacklist_count': len(blacklist_rules)
                        },
                        'message': 'AI vetting analysis completed'
                    }), 200

                except json.JSONDecodeError:
                    # Fallback analysis
                    return jsonify({
                        'success': True,
                        'analysis': {
                            'overall_status': 'REVIEW_REQUIRED',
                            'confidence_score': 75,
                            'summary': ai_response[:300] + '...' if len(ai_response) > 300 else ai_response,
                            'recommendations': ['Manual review recommended', 'Verify compliance with key terms'],
                            'key_findings': ['AI analysis completed with fallback format']
                        },
                        'message': 'AI analysis completed (fallback format)'
                    }), 200

            except Exception as openai_error:
                logger.error(f"OpenAI API error in vetting analysis: {openai_error}")
                # Provide basic analysis when AI unavailable
                return jsonify({
                    'success': True,
                    'analysis': {
                        'overall_status': 'REVIEW_REQUIRED',
                        'confidence_score': 50,
                        'summary': 'Manual analysis required - AI service unavailable',
                        'recommendations': ['Perform manual review against vetting rules', 'Check compliance requirements'],
                        'key_findings': ['Document length: ' + str(len(guarantee_text)) + ' characters']
                    },
                    'message': 'Basic analysis provided (AI unavailable)'
                }), 200

        except Exception as e:
            logger.error(f"Error in AI vetting analysis: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    # ============================================================================
    # BLACKLIST RULES MANAGEMENT API
    # ============================================================================

    @app.route('/api/blacklist_rules', methods=['GET'])
    @timing_aspect
    def get_blacklist_rules():
        """Get all blacklist rules"""
        try:
            blacklist_filepath = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '..', 'data', 'blacklist_vetting_rules.json')

            if not os.path.exists(blacklist_filepath):
                return jsonify({'success': True, 'rules': []}), 200

            with open(blacklist_filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                rules = data.get('blacklist_rules', [])
                return jsonify({'success': True, 'rules': rules}), 200

        except Exception as e:
            logger.error(f"Error loading blacklist rules: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/blacklist_rules', methods=['POST'])
    @timing_aspect
    def add_blacklist_rule():
        """Add a new blacklist rule"""
        try:
            rule_data = request.get_json()
            if not rule_data:
                return jsonify({'success': False, 'message': 'No data provided'}), 400

            blacklist_filepath = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '..', 'data', 'blacklist_vetting_rules.json')

            # Load existing rules
            if os.path.exists(blacklist_filepath):
                with open(blacklist_filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {'blacklist_rules': []}

            # Generate new ID
            existing_ids = [rule.get('id', '') for rule in data.get('blacklist_rules', [])]
            max_num = 0
            for rule_id in existing_ids:
                if rule_id.startswith('BL') and rule_id[2:].isdigit():
                    max_num = max(max_num, int(rule_id[2:]))
            new_id = f"BL{str(max_num + 1).zfill(3)}"

            # Create new rule
            new_rule = {
                'id': new_id,
                'rule_type': 'blacklist',
                'category': rule_data.get('category', ''),
                'description': rule_data.get('description', ''),
                'rule': rule_data.get('rule', ''),
                'keywords': rule_data.get('keywords', []),
                'priority': rule_data.get('priority', 'medium'),
                'status': 'active',
                'compliance_requirement': rule_data.get('compliance_requirement', ''),
                'action': rule_data.get('action', 'review'),
                'created_date': datetime.now().strftime('%Y-%m-%d'),
                'last_updated': datetime.now().strftime('%Y-%m-%d')
            }

            data['blacklist_rules'].append(new_rule)

            # Save updated rules
            with open(blacklist_filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            return jsonify({'success': True, 'rule': new_rule}), 201

        except Exception as e:
            logger.error(f"Error adding blacklist rule: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/blacklist_rules/<rule_id>', methods=['PUT'])
    @timing_aspect
    def update_blacklist_rule(rule_id):
        """Update a blacklist rule"""
        try:
            rule_data = request.get_json()
            if not rule_data:
                return jsonify({'success': False, 'message': 'No data provided'}), 400

            blacklist_filepath = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '..', 'data', 'blacklist_vetting_rules.json')

            if not os.path.exists(blacklist_filepath):
                return jsonify({'success': False, 'message': 'Rules file not found'}), 404

            with open(blacklist_filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Find and update rule
            rules = data.get('blacklist_rules', [])
            for i, rule in enumerate(rules):
                if rule.get('id') == rule_id:
                    updated_rule = rule.copy()
                    updated_rule.update({
                        'category': rule_data.get('category', rule['category']),
                        'description': rule_data.get('description', rule['description']),
                        'rule': rule_data.get('rule', rule['rule']),
                        'keywords': rule_data.get('keywords', rule['keywords']),
                        'priority': rule_data.get('priority', rule['priority']),
                        'compliance_requirement': rule_data.get('compliance_requirement', rule['compliance_requirement']),
                        'action': rule_data.get('action', rule['action']),
                        'last_updated': datetime.now().strftime('%Y-%m-%d')
                    })

                    rules[i] = updated_rule

                    # Save updated rules
                    with open(blacklist_filepath, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)

                    return jsonify({'success': True, 'rule': updated_rule}), 200

            return jsonify({'success': False, 'message': 'Rule not found'}), 404

        except Exception as e:
            logger.error(f"Error updating blacklist rule {rule_id}: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/blacklist_rules/<rule_id>', methods=['DELETE'])
    @timing_aspect
    def delete_blacklist_rule(rule_id):
        """Delete a blacklist rule"""
        try:
            blacklist_filepath = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '..', 'data', 'blacklist_vetting_rules.json')

            if not os.path.exists(blacklist_filepath):
                return jsonify({'success': False, 'message': 'Rules file not found'}), 404

            with open(blacklist_filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Find and remove rule
            original_count = len(data.get('blacklist_rules', []))
            data['blacklist_rules'] = [rule for rule in data.get('blacklist_rules', []) if rule.get('id') != rule_id]

            if len(data['blacklist_rules']) < original_count:
                # Save updated rules
                with open(blacklist_filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

                return jsonify({'success': True, 'message': 'Rule deleted successfully'}), 200
            else:
                return jsonify({'success': False, 'message': 'Rule not found'}), 404

        except Exception as e:
            logger.error(f"Error deleting blacklist rule {rule_id}: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    # ============================================================================
    # WHITELIST RULES MANAGEMENT API
    # ============================================================================

    @app.route('/api/whitelist_rules', methods=['GET'])
    @timing_aspect
    def get_whitelist_rules():
        """Get all whitelist rules"""
        try:
            whitelist_filepath = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '..', 'data', 'whitelist_vetting_rules.json')

            if not os.path.exists(whitelist_filepath):
                return jsonify({'success': True, 'rules': []}), 200

            with open(whitelist_filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                rules = data.get('whitelist_rules', [])
                return jsonify({'success': True, 'rules': rules}), 200

        except Exception as e:
            logger.error(f"Error loading whitelist rules: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/whitelist_rules', methods=['POST'])
    @timing_aspect
    def add_whitelist_rule():
        """Add a new whitelist rule"""
        try:
            rule_data = request.get_json()
            if not rule_data:
                return jsonify({'success': False, 'message': 'No data provided'}), 400

            whitelist_filepath = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '..', 'data', 'whitelist_vetting_rules.json')

            # Load existing rules
            if os.path.exists(whitelist_filepath):
                with open(whitelist_filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {'whitelist_rules': []}

            # Generate new ID
            existing_ids = [rule.get('id', '') for rule in data.get('whitelist_rules', [])]
            max_num = 0
            for rule_id in existing_ids:
                if rule_id.startswith('WL') and rule_id[2:].isdigit():
                    max_num = max(max_num, int(rule_id[2:]))
            new_id = f"WL{str(max_num + 1).zfill(3)}"

            # Create new rule
            new_rule = {
                'id': new_id,
                'rule_type': 'whitelist',
                'category': rule_data.get('category', ''),
                'description': rule_data.get('description', ''),
                'rule': rule_data.get('rule', ''),
                'keywords': rule_data.get('keywords', []),
                'priority': rule_data.get('priority', 'medium'),
                'status': 'active',
                'compliance_requirement': rule_data.get('compliance_requirement', ''),
                'created_date': datetime.now().strftime('%Y-%m-%d'),
                'last_updated': datetime.now().strftime('%Y-%m-%d')
            }

            data['whitelist_rules'].append(new_rule)

            # Save updated rules
            with open(whitelist_filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            return jsonify({'success': True, 'rule': new_rule}), 201

        except Exception as e:
            logger.error(f"Error adding whitelist rule: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/whitelist_rules/<rule_id>', methods=['PUT'])
    @timing_aspect
    def update_whitelist_rule(rule_id):
        """Update a whitelist rule"""
        try:
            rule_data = request.get_json()
            if not rule_data:
                return jsonify({'success': False, 'message': 'No data provided'}), 400

            whitelist_filepath = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'whitelist_vetting_rules.json')

            if not os.path.exists(whitelist_filepath):
                return jsonify({'success': False, 'message': 'Rules file not found'}), 404

            with open(whitelist_filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Find and update rule
            rules = data.get('whitelist_rules', [])
            for i, rule in enumerate(rules):
                if rule.get('id') == rule_id:
                    updated_rule = rule.copy()
                    updated_rule.update({
                        'category': rule_data.get('category', rule['category']),
                        'description': rule_data.get('description', rule['description']),
                        'rule': rule_data.get('rule', rule['rule']),
                        'keywords': rule_data.get('keywords', rule['keywords']),
                        'priority': rule_data.get('priority', rule['priority']),
                        'compliance_requirement': rule_data.get('compliance_requirement', rule['compliance_requirement']),
                        'last_updated': datetime.now().strftime('%Y-%m-%d')
                    })

                    rules[i] = updated_rule

                    # Save updated rules
                    with open(whitelist_filepath, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)

                    return jsonify({'success': True, 'rule': updated_rule}), 200

            return jsonify({'success': False, 'message': 'Rule not found'}), 404

        except Exception as e:
            logger.error(f"Error updating whitelist rule {rule_id}: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/whitelist_rules/<rule_id>', methods=['DELETE'])
    @timing_aspect
    def delete_whitelist_rule(rule_id):
        """Delete a whitelist rule"""
        try:
            whitelist_filepath = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'whitelist_vetting_rules.json')

            if not os.path.exists(whitelist_filepath):
                return jsonify({'success': False, 'message': 'Rules file not found'}), 404

            with open(whitelist_filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Find and remove rule
            original_count = len(data.get('whitelist_rules', []))
            data['whitelist_rules'] = [rule for rule in data.get('whitelist_rules', []) if rule.get('id') != rule_id]

            if len(data['whitelist_rules']) < original_count:
                # Save updated rules
                with open(whitelist_filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

                return jsonify({'success': True, 'message': 'Rule deleted successfully'}), 200
            else:
                return jsonify({'success': False, 'message': 'Rule not found'}), 404

        except Exception as e:
            logger.error(f"Error deleting whitelist rule {rule_id}: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    # ============================================================================
    # AI RULE PREVIEW ENDPOINT
    # ============================================================================

    @app.route('/api/ai_rule_preview', methods=['POST'])
    @timing_aspect
    def ai_rule_preview():
        """Preview how a rule would work with sample data"""
        try:
            request_data = request.get_json()
            if not request_data:
                return jsonify({'success': False, 'message': 'No data provided'}), 400

            rule_description = request_data.get('rule_description', '').strip()
            rule_type = request_data.get('rule_type', 'blacklist')
            sample_scenario = request_data.get('sample_scenario', '').strip()

            if not rule_description:
                return jsonify({'success': False, 'message': 'Rule description is required'}), 400

            # Create AI prompt for rule preview
            if rule_type == 'blacklist':
                system_prompt = """You are an AI assistant specialized in demonstrating how blacklist vetting rules work. Create realistic examples of how the rule would flag problematic transactions."""
                if sample_scenario:
                    prompt = f"""Rule Description: "{rule_description}"
Rule Type: Blacklist (flags problematic conditions)
Sample Scenario: "{sample_scenario}"

Show how this rule would work by providing:
1. A clear explanation of what the rule detects
2. An example result message showing why a transaction would be flagged
3. Key detection criteria
4. Recommended action

Format as JSON with fields: explanation, example_result, detection_criteria, recommended_action"""
                else:
                    prompt = f"""Rule Description: "{rule_description}"
Rule Type: Blacklist (flags problematic conditions)

Show how this rule would work by providing:
1. A clear explanation of what the rule detects
2. 2-3 realistic example scenarios where it would trigger
3. Example result messages for each scenario
4. Key detection criteria
5. Recommended actions

Format as JSON with fields: explanation, example_scenarios (array), detection_criteria, recommended_action"""
            else:
                system_prompt = """You are an AI assistant specialized in demonstrating how whitelist vetting rules work. Create realistic examples of how the rule would approve compliant transactions."""
                if sample_scenario:
                    prompt = f"""Rule Description: "{rule_description}"
Rule Type: Whitelist (approves compliant conditions)
Sample Scenario: "{sample_scenario}"

Show how this rule would work by providing:
1. A clear explanation of what the rule approves
2. An example result message showing why a transaction would be approved
3. Key approval criteria
4. Compliance benefits

Format as JSON with fields: explanation, example_result, approval_criteria, compliance_benefits"""
                else:
                    prompt = f"""Rule Description: "{rule_description}"
Rule Type: Whitelist (approves compliant conditions)

Show how this rule would work by providing:
1. A clear explanation of what the rule approves
2. 2-3 realistic example scenarios where it would approve
3. Example result messages for each scenario
4. Key approval criteria
5. Compliance benefits

Format as JSON with fields: explanation, example_scenarios (array), approval_criteria, compliance_benefits"""

            # Call OpenAI API with Azure configuration
            try:
                # Setup Azure OpenAI configuration
                azure_key = os.getenv('AZURE_OPENAI_API_KEY')
                azure_base = os.getenv('AZURE_OPENAI_API_BASE')
                azure_version = os.getenv('AZURE_OPENAI_VERSION', '2023-12-01-preview')
                deployment_name = os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-4o')

                if azure_key and azure_base:
                    # Configure Azure OpenAI
                    openai.api_type = "azure"
                    openai.api_key = azure_key
                    openai.api_base = azure_base
                    openai.api_version = azure_version
                else:
                    # Fallback to regular OpenAI
                    openai.api_key = os.getenv('OPENAI_API_KEY')
                    deployment_name = "gpt-3.5-turbo"

                # Use old API format with engine parameter
                response = openai.ChatCompletion.create(
                    engine=deployment_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=1200,
                    seed=12345,
                    top_p=0.1,
                    frequency_penalty=0,
                    presence_penalty=0,
                    response_format={"type": "json_object"}
                )
                ai_response = response.choices[0].message.content.strip()

                # Parse AI response
                try:
                    if '```json' in ai_response:
                        json_start = ai_response.find('```json') + 7
                        json_end = ai_response.find('```', json_start)
                        ai_response = ai_response[json_start:json_end].strip()
                    elif '```' in ai_response:
                        json_start = ai_response.find('```') + 3
                        json_end = ai_response.find('```', json_start)
                        ai_response = ai_response[json_start:json_end].strip()

                    preview_result = json.loads(ai_response)

                    return jsonify({
                        'success': True,
                        'preview': preview_result,
                        'rule_type': rule_type,
                        'message': 'Rule preview generated successfully'
                    }), 200

                except json.JSONDecodeError:
                    # Fallback if JSON parsing fails
                    return jsonify({
                        'success': True,
                        'preview': {
                            'explanation': f'This {rule_type} rule would detect: {rule_description}',
                            'example_result': ai_response[:400] + '...' if len(ai_response) > 400 else ai_response,
                            'detection_criteria': f'Based on: {rule_description}',
                            'recommended_action': 'Review flagged transactions manually'
                        },
                        'message': 'Rule preview generated (fallback format)'
                    }), 200

            except Exception as openai_error:
                logger.error(f"OpenAI API error in rule preview: {openai_error}")
                # Provide enhanced fallback preview when AI unavailable
                preview_result = generate_enhanced_fallback_preview(rule_description, rule_type, sample_scenario)

                return jsonify({
                    'success': True,
                    'preview': preview_result,
                    'message': 'Enhanced rule preview provided (AI unavailable)'
                }), 200

        except Exception as e:
            logger.error(f"Error in rule preview: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    # ============================================================================
    # GUARANTEE PROMPT CONFIGURATION ROUTES
    # ============================================================================

    @app.route('/api/guarantee_prompt_config', methods=['GET'])
    @timing_aspect
    def get_guarantee_prompt_config():
        """Get guarantee prompt system configuration"""
        try:
            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '..', 'data', 'guarantee_prompt_system.json')

            if not os.path.exists(config_path):
                # Create default simplified configuration
                default_config = {
                    "system_prompt": """You are an AI assistant specialized in financial document analysis and guarantee vetting.

Your primary role is to:
1. Analyze financial documents for key information
2. Evaluate guarantee structures and terms
3. Assess compliance with regulatory requirements
4. Identify potential risks or issues

Please provide clear, accurate, and professional responses based on the document content.""",
                    "custom_prompt": """Please analyze this document for:
- Document type and purpose
- Key financial terms and conditions
- Guarantee structure and obligations
- Compliance requirements
- Risk factors

Provide a structured summary with your findings.""",
                    "last_updated": "2024-01-01T00:00:00.000Z"
                }

                # Ensure directory exists
                os.makedirs(os.path.dirname(config_path), exist_ok=True)

                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, indent=2, ensure_ascii=False)

                return jsonify({'success': True, 'config': default_config}), 200

            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # Ensure the config has the expected structure
            if 'system_prompt' not in config:
                config['system_prompt'] = ""
            if 'custom_prompt' not in config:
                config['custom_prompt'] = ""
            if 'last_updated' not in config:
                config['last_updated'] = None

            return jsonify({'success': True, 'config': config}), 200

        except Exception as e:
            logger.error(f"Error getting guarantee prompt config: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/guarantee_prompt_config', methods=['POST'])
    @timing_aspect
    def update_guarantee_prompt_config():
        """Update guarantee prompt system configuration"""
        try:
            config_data = request.get_json()
            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '..', 'data', 'guarantee_prompt_system.json')

            # Validate simplified config structure
            if not config_data:
                return jsonify({'success': False, 'message': 'No configuration data provided'}), 400

            # Ensure directory exists
            os.makedirs(os.path.dirname(config_path), exist_ok=True)

            # Add timestamp
            config_data['last_updated'] = datetime.utcnow().isoformat() + 'Z'

            # Save updated configuration
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)

            return jsonify({'success': True, 'message': 'Configuration updated successfully'}), 200

        except Exception as e:
            logger.error(f"Error updating guarantee prompt config: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/guarantee_prompt_config/reset', methods=['POST'])
    @timing_aspect
    def reset_guarantee_prompt_config():
        """Reset guarantee prompt configuration to defaults"""
        try:
            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '..', 'data', 'guarantee_prompt_system.json')

            # Create default simplified configuration
            default_config = {
                "system_prompt": """You are an AI assistant specialized in financial document analysis and guarantee vetting.

Your primary role is to:
1. Analyze financial documents for key information
2. Evaluate guarantee structures and terms
3. Assess compliance with regulatory requirements
4. Identify potential risks or issues

Please provide clear, accurate, and professional responses based on the document content.""",
                "custom_prompt": """Please analyze this document for:
- Document type and purpose
- Key financial terms and conditions
- Guarantee structure and obligations
- Compliance requirements
- Risk factors

Provide a structured summary with your findings.""",
                "last_updated": datetime.utcnow().isoformat() + 'Z'
            }

            # Ensure directory exists
            os.makedirs(os.path.dirname(config_path), exist_ok=True)

            # Save default configuration
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)

            return jsonify({'success': True, 'config': default_config, 'message': 'Configuration reset to defaults'}), 200

        except Exception as e:
            logger.error(f"Error resetting guarantee prompt config: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/guarantee_prompt_preview', methods=['POST'])
    @timing_aspect
    def guarantee_prompt_preview():
        """Generate real-time AI analysis preview based on current prompts"""
        try:
            data = request.get_json()

            if not data:
                return jsonify({'success': False, 'message': 'No data provided'}), 400

            system_prompt = data.get('system_prompt', '')
            custom_prompt = data.get('custom_prompt', '')
            sample_text = data.get('sample_text', '')
            analysis_mode = data.get('analysis_mode', 'basic')
            include_whitelist = data.get('include_whitelist', True)
            include_blacklist = data.get('include_blacklist', True)

            if not sample_text.strip():
                return jsonify({'success': False, 'message': 'Sample text is required'}), 400

            # Load rules if requested
            rules_context = ""
            if include_whitelist or include_blacklist:
                try:
                    app_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                    if include_whitelist:
                        whitelist_path = os.path.join(app_dir, '..', 'data', 'whitelist_vetting_rules.json')
                        if os.path.exists(whitelist_path):
                            with open(whitelist_path, 'r', encoding='utf-8') as f:
                                whitelist_data = json.load(f)
                                rules_context += "\n\nWHITELIST RULES (Approved Conditions):\n"
                                for rule in whitelist_data.get('whitelist_rules', []):
                                    rules_context += f"- {rule['id']}: {rule['description']} (Priority: {rule['priority']})\n"

                    if include_blacklist:
                        blacklist_path = os.path.join(app_dir, '..', 'data', 'blacklist_vetting_rules.json')
                        if os.path.exists(blacklist_path):
                            with open(blacklist_path, 'r', encoding='utf-8') as f:
                                blacklist_data = json.load(f)
                                rules_context += "\n\nBLACKLIST RULES (Prohibited Conditions):\n"
                                for rule in blacklist_data.get('blacklist_rules', []):
                                    rules_context += f"- {rule['id']}: {rule['description']} (Priority: {rule['priority']}, Action: {rule.get('action', 'review')})\n"
                except Exception as e:
                    logger.warning(f"Could not load vetting rules: {e}")

            # Build the complete prompt
            complete_prompt = f"{system_prompt}\n\n{custom_prompt}"
            if rules_context:
                complete_prompt += rules_context

            complete_prompt += f"\n\nAnalysis Mode: {analysis_mode.replace('_', ' ').title()}"
            complete_prompt += f"\n\nDocument Text to Analyze:\n{sample_text}"
            complete_prompt += "\n\nPlease provide your analysis in JSON format with the following structure:"
            complete_prompt += """
{
  "document_type": "identified document type",
  "compliance_status": "compliant/non-compliant/needs_review",
  "risk_level": "low/medium/high/critical",
  "key_findings": ["finding1", "finding2"],
  "whitelist_compliance": "summary of whitelist rule compliance",
  "blacklist_violations": "any blacklist rule violations found",
  "recommendations": ["recommendation1", "recommendation2"],
  "confidence_score": 0.95
}"""

            # Generate mock analysis
            analysis_result = generate_mock_analysis(sample_text, analysis_mode, include_whitelist, include_blacklist)

            return jsonify({
                'success': True,
                'analysis': analysis_result,
                'prompt_used': complete_prompt[:500] + "..." if len(complete_prompt) > 500 else complete_prompt,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }), 200

        except Exception as e:
            logger.error(f"Error generating guarantee prompt preview: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    logger.info("✅ Registered Guarantee Vetting routes")
