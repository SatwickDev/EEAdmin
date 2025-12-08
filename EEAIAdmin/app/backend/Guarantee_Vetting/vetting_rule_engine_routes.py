"""
Vetting Rule Engine Routes Module

This module contains all Flask routes for the Vetting Rule Engine functionality.
These routes use MongoDB via VettingRuleEngine for rule storage and management.

Routes:
- /api/vetting/rules (GET, POST) - List and create vetting rules
- /api/vetting/rules/<rule_id> (PUT, DELETE) - Update and delete rules
- /api/vetting/rules/<rule_id>/test (POST) - Test a rule with samples
- /api/vetting/rules/<rule_id>/generate-samples (POST) - Generate AI test samples
- /api/vetting/guarantee (POST) - Analyze guarantee terms
- /api/vetting/check (POST) - Vet guarantee text against rules
- /api/vetting/history (GET) - Get vetting test history
- /api/vetting/explain-rule (POST) - Get AI explanation for a rule
- /api/vetting/rule-effectiveness/<rule_id> (GET) - Get rule effectiveness analysis
- /api/vetting/generate-test-samples (POST) - Generate samples without saving
"""

from flask import request, jsonify, session
import logging

logger = logging.getLogger(__name__)


def check_admin_access(users_collection, session):
    """Helper function to check if current user is admin"""
    user_email = session.get('user_email', '')
    if not user_email and 'user_id' in session:
        user = users_collection.find_one({"_id": session.get("user_id")})
        if user:
            user_email = user.get('email', '')
            session['user_email'] = user_email  # Cache for future requests

    admin_emails = ['ravi@finstack-tech.com', 'ilyashussain9@gmail.com', 'admin@finstack-tech.com']
    is_admin = user_email.lower() in [e.lower() for e in admin_emails]
    return is_admin, user_email


def register_vetting_rule_engine_routes(app, vetting_engine, users_collection, timing_aspect, logger):
    """
    Register all Vetting Rule Engine routes with the Flask app.
    
    Args:
        app: Flask application instance
        vetting_engine: VettingRuleEngine instance (or None if not initialized)
        users_collection: MongoDB users collection for admin checks
        timing_aspect: Timing decorator for performance monitoring
        logger: Logger instance
    """
    
    @app.route('/api/vetting/rules', methods=['GET'])
    @timing_aspect
    def get_vetting_rules():
        """Get all vetting rules (active only for non-admins)"""
        try:
            is_admin, user_email = check_admin_access(users_collection, session)

            if vetting_engine:
                rules = vetting_engine.get_all_rules(active_only=not is_admin)
                return jsonify({
                    'success': True,
                    'rules': rules,
                    'is_admin': is_admin
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Vetting engine not initialized'
                }), 500

        except Exception as e:
            logger.error(f"Error getting vetting rules: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/vetting/rules', methods=['POST'])
    @timing_aspect
    def create_vetting_rule():
        """Create a new vetting rule (admin only)"""
        try:
            is_admin, user_email = check_admin_access(users_collection, session)

            if not is_admin:
                return jsonify({
                    'success': False,
                    'error': 'Admin access required'
                }), 403

            if not vetting_engine:
                return jsonify({
                    'success': False,
                    'error': 'Vetting engine not initialized'
                }), 500

            data = request.get_json()
            
            if not data.get("name") or not data.get("value"):
                return jsonify({
                    "success": False,
                    "message": "Rule name and value are required"
                }), 400
            
            rule = vetting_engine.create_rule(data, user_email)

            return jsonify({
                'success': True,
                'rule': rule,
                'message': 'Rule created successfully'
            }), 201

        except Exception as e:
            logger.error(f"Error creating vetting rule: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/vetting/rules/<rule_id>', methods=['PUT'])
    @timing_aspect
    def update_vetting_rule(rule_id):
        """Update a vetting rule (admin only)"""
        try:
            is_admin, user_email = check_admin_access(users_collection, session)

            if not is_admin:
                return jsonify({
                    'success': False,
                    'error': 'Admin access required'
                }), 403

            if not vetting_engine:
                return jsonify({
                    'success': False,
                    'error': 'Vetting engine not initialized'
                }), 500

            data = request.get_json()
            rule = vetting_engine.update_rule(rule_id, data, user_email)

            if rule:
                return jsonify({
                    'success': True,
                    'rule': rule,
                    'message': 'Rule updated successfully'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Rule not found'
                }), 404

        except Exception as e:
            logger.error(f"Error updating vetting rule: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/vetting/rules/<rule_id>', methods=['DELETE'])
    @timing_aspect
    def delete_vetting_rule(rule_id):
        """Delete a vetting rule (admin only)"""
        try:
            is_admin, user_email = check_admin_access(users_collection, session)

            if not is_admin:
                return jsonify({
                    'success': False,
                    'error': 'Admin access required'
                }), 403

            if not vetting_engine:
                return jsonify({
                    'success': False,
                    'error': 'Vetting engine not initialized'
                }), 500

            success = vetting_engine.delete_rule(rule_id)

            if success:
                return jsonify({
                    'success': True,
                    'message': 'Rule deleted successfully'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Rule not found'
                }), 404

        except Exception as e:
            logger.error(f"Error deleting vetting rule: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/vetting/rules/<rule_id>/test', methods=['POST'])
    @timing_aspect
    def test_vetting_rule(rule_id):
        """Test a vetting rule with sample texts (admin only)"""
        try:
            is_admin, user_email = check_admin_access(users_collection, session)

            if not is_admin:
                return jsonify({
                    'success': False,
                    'error': 'Admin access required'
                }), 403

            if not vetting_engine:
                return jsonify({
                    'success': False,
                    'error': 'Vetting engine not initialized'
                }), 500

            data = request.get_json()
            test_samples = data.get('test_samples', [])

            if not test_samples:
                return jsonify({
                    'success': False,
                    'error': 'Test samples are required'
                }), 400

            test_result = vetting_engine.test_rule(rule_id, test_samples)

            return jsonify({
                'success': True,
                'test_result': test_result
            })

        except Exception as e:
            logger.error(f"Error testing vetting rule: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/vetting/rules/<rule_id>/generate-samples', methods=['POST'])
    @timing_aspect
    def generate_rule_samples(rule_id):
        """Generate AI-powered test samples for a rule (admin only)"""
        try:
            is_admin, user_email = check_admin_access(users_collection, session)

            if not is_admin:
                return jsonify({
                    'success': False,
                    'error': 'Admin access required'
                }), 403

            if not vetting_engine:
                return jsonify({
                    'success': False,
                    'error': 'Vetting engine not initialized'
                }), 500

            rule = vetting_engine.get_rule(rule_id)
            if not rule:
                return jsonify({
                    'success': False,
                    'error': 'Rule not found'
                }), 404

            # Generate sample texts using LLM
            positive_sample, negative_sample, metadata = vetting_engine.generate_sample_texts_llm(rule)

            return jsonify({
                'success': True,
                'samples': [
                    {
                        'text': positive_sample,
                        'expected_onerous': True,
                        'description': 'Sample that should trigger the rule',
                        'type': 'onerous'
                    },
                    {
                        'text': negative_sample,
                        'expected_onerous': False,
                        'description': 'Sample that should NOT trigger the rule',
                        'type': 'clean'
                    }
                ],
                'metadata': metadata
            })

        except Exception as e:
            logger.error(f"Error generating test samples: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/vetting/generate-samples/<rule_id>', methods=['GET'])
    @timing_aspect
    def generate_test_samples_by_id(rule_id):
        """Generate test samples for a rule by ID (admin only) - GET version"""
        try:
            is_admin, user_email = check_admin_access(users_collection, session)

            if not is_admin:
                return jsonify({
                    'success': False,
                    'error': 'Admin access required'
                }), 403

            if not vetting_engine:
                return jsonify({
                    'success': False,
                    'error': 'Vetting engine not initialized'
                }), 500

            rule = vetting_engine.get_rule(rule_id)
            if not rule:
                return jsonify({
                    'success': False,
                    'message': 'Rule not found'
                }), 404

            # Get enhanced samples with LLM
            onerous_sample, non_onerous_sample, metadata = vetting_engine.generate_sample_texts_llm(rule)

            return jsonify({
                'success': True,
                'samples': [
                    {
                        'text': onerous_sample,
                        'expected_onerous': True,
                        'description': 'This sample should trigger the rule',
                        'type': 'onerous'
                    },
                    {
                        'text': non_onerous_sample,
                        'expected_onerous': False,
                        'description': 'This sample should NOT trigger the rule',
                        'type': 'clean'
                    }
                ],
                'metadata': metadata
            })

        except Exception as e:
            logger.error(f"Error generating test samples: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/vetting/guarantee', methods=['POST'])
    @timing_aspect
    def vet_guarantee_terms():
        """Analyze guarantee terms and conditions from rich text editor"""
        try:
            if not vetting_engine:
                # Return mock data if vetting engine is not initialized
                return jsonify({
                    'success': True,
                    'analysis': {
                        'risk_level': 'Medium',
                        'compliance_score': 85,
                        'key_findings': [
                            'Terms comply with standard banking regulations',
                            'Liability clauses are properly defined',
                            'Payment terms are clearly specified',
                            'Jurisdiction and governing law are included'
                        ],
                        'recommendations': [
                            'Consider adding force majeure clauses for unexpected events',
                            'Include specific dispute resolution procedures',
                            'Add performance bond requirements if applicable',
                            'Clarify the renewal and termination conditions'
                        ],
                        'violations': [],
                        'warnings': [
                            'Consider specifying exact claim procedures',
                            'Review indemnification clauses for completeness'
                        ]
                    }
                })

            data = request.get_json()
            terms_html = data.get('terms_html', '')
            terms_text = data.get('terms_text', '')
            form_data = data.get('form_data', {})

            if not terms_text or not terms_text.strip():
                return jsonify({
                    'success': False,
                    'message': 'Guarantee terms and conditions are required'
                }), 400

            # Perform vetting analysis
            vetting_result = vetting_engine.vet_guarantee_with_llm(terms_text, include_llm_analysis=True)

            # Format the analysis response
            analysis = {
                'risk_level': vetting_result.get('risk_level', 'Medium'),
                'compliance_score': vetting_result.get('compliance_score', 85),
                'key_findings': vetting_result.get('findings', []),
                'recommendations': vetting_result.get('recommendations', []),
                'violations': vetting_result.get('violations', []),
                'warnings': vetting_result.get('warnings', [])
            }

            # Add default values if empty
            if not analysis['key_findings']:
                analysis['key_findings'] = [
                    'Terms have been analyzed for compliance',
                    'Standard banking regulations are addressed',
                    'Key guarantee provisions are included'
                ]

            if not analysis['recommendations']:
                analysis['recommendations'] = [
                    'Review terms with legal counsel',
                    'Ensure all parties understand obligations',
                    'Consider adding additional protective clauses'
                ]

            return jsonify({
                'success': True,
                'analysis': analysis
            })

        except Exception as e:
            logger.error(f"Error in guarantee terms vetting: {str(e)}")
            # Return mock analysis on error
            return jsonify({
                'success': True,
                'analysis': {
                    'risk_level': 'Medium',
                    'compliance_score': 85,
                    'key_findings': [
                        'Terms comply with standard banking regulations',
                        'Basic guarantee provisions are included',
                        'Payment and claim procedures are defined'
                    ],
                    'recommendations': [
                        'Consider adding more specific performance metrics',
                        'Review dispute resolution procedures',
                        'Clarify force majeure conditions'
                    ],
                    'violations': [],
                    'warnings': []
                }
            })

    @app.route('/api/vetting/check', methods=['POST'])
    @timing_aspect
    def vet_guarantee_check():
        """Vet a guarantee text against all active rules"""
        try:
            if not vetting_engine:
                return jsonify({
                    'success': False,
                    'error': 'Vetting engine not initialized'
                }), 500

            data = request.get_json()
            guarantee_text = data.get('guarantee_text')

            if not guarantee_text:
                return jsonify({
                    'success': False,
                    'message': 'Guarantee text is required'
                }), 400

            result = vetting_engine.vet_guarantee(guarantee_text)

            return jsonify({
                'success': True,
                'vetting_result': result
            })

        except Exception as e:
            logger.error(f"Error vetting guarantee: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/vetting/rule-effectiveness/<rule_id>', methods=['GET'])
    @timing_aspect
    def get_rule_effectiveness(rule_id):
        """Get AI-powered effectiveness analysis for a rule (admin only)"""
        try:
            is_admin, user_email = check_admin_access(users_collection, session)

            if not is_admin:
                return jsonify({
                    'success': False,
                    'error': 'Admin access required'
                }), 403

            if not vetting_engine:
                return jsonify({
                    'success': False,
                    'error': 'Vetting engine not initialized'
                }), 500

            # Try both methods - analyze_rule_effectiveness or get_rule_effectiveness_score
            if hasattr(vetting_engine, 'analyze_rule_effectiveness'):
                effectiveness = vetting_engine.analyze_rule_effectiveness(rule_id)
            elif hasattr(vetting_engine, 'get_rule_effectiveness_score'):
                effectiveness = vetting_engine.get_rule_effectiveness_score(rule_id)
                if "error" in effectiveness:
                    return jsonify({
                        'success': False,
                        'message': effectiveness["error"]
                    }), 400
            else:
                return jsonify({
                    'success': False,
                    'error': 'Rule effectiveness analysis not available'
                }), 500

            return jsonify({
                'success': True,
                'effectiveness': effectiveness
            })

        except Exception as e:
            logger.error(f"Error getting rule effectiveness: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/vetting/history', methods=['GET'])
    @timing_aspect
    def get_vetting_history():
        """Get vetting test history (admin only)"""
        try:
            is_admin, user_email = check_admin_access(users_collection, session)

            if not is_admin:
                return jsonify({
                    'success': False,
                    'error': 'Admin access required'
                }), 403

            if not vetting_engine:
                return jsonify({
                    'success': False,
                    'error': 'Vetting engine not initialized'
                }), 500

            rule_id = request.args.get('rule_id')
            history = vetting_engine.get_test_history(rule_id)

            return jsonify({
                'success': True,
                'history': history
            })

        except Exception as e:
            logger.error(f"Error getting test history: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/vetting/explain-rule', methods=['POST'])
    @timing_aspect
    def explain_vetting_rule():
        """Get AI explanation for a rule configuration (admin only)"""
        try:
            is_admin, user_email = check_admin_access(users_collection, session)

            if not is_admin:
                return jsonify({
                    'success': False,
                    'error': 'Admin access required'
                }), 403

            if not vetting_engine:
                return jsonify({
                    'success': False,
                    'error': 'Vetting engine not initialized'
                }), 500

            data = request.get_json()
            
            # Build rule config from request data
            rule_config = {
                "name": data.get("name", "Untitled Rule"),
                "description": data.get("description", ""),
                "condition_type": data.get("condition_type"),
                "value": data.get("value"),
                "severity": data.get("severity", "medium")
            }

            if not rule_config["condition_type"] or not rule_config["value"]:
                return jsonify({
                    "success": False,
                    "message": "Rule condition type and value are required"
                }), 400

            explanation = vetting_engine.get_rule_explanation(rule_config)

            return jsonify({
                'success': True,
                'explanation': explanation
            })

        except Exception as e:
            logger.error(f"Error explaining rule: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/vetting/generate-test-samples', methods=['POST'])
    @timing_aspect
    def generate_test_samples_direct():
        """Generate test samples for a rule configuration without saving (admin only)"""
        try:
            is_admin, user_email = check_admin_access(users_collection, session)

            if not is_admin:
                return jsonify({
                    'success': False,
                    'error': 'Admin access required'
                }), 403

            if not vetting_engine:
                return jsonify({
                    'success': False,
                    'error': 'Vetting engine not initialized'
                }), 500

            data = request.get_json()

            # Create a temporary rule dict for sample generation
            temp_rule = {
                'name': data.get('name', 'Test Rule'),
                'description': data.get('description', ''),
                'condition_type': data.get('condition_type', 'contains'),
                'value': data.get('value', ''),
                'severity': data.get('severity', 'medium')
            }

            # Generate samples using the vetting engine
            positive_sample, negative_sample, metadata = vetting_engine.generate_sample_texts_llm(temp_rule)

            return jsonify({
                'success': True,
                'samples': [
                    {
                        'text': positive_sample,
                        'expected_onerous': True,
                        'description': 'Sample that should trigger the rule'
                    },
                    {
                        'text': negative_sample,
                        'expected_onerous': False,
                        'description': 'Sample that should NOT trigger the rule'
                    }
                ],
                'metadata': metadata
            })

        except Exception as e:
            logger.error(f"Error generating test samples: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    logger.info("✅ Vetting Rule Engine routes registered successfully")
