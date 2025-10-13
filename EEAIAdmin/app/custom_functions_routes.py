"""
Custom Functions Management Routes
Allows users to create custom business functions with document requirements and LLM prompts
"""

import json
import os
import logging
from datetime import datetime
from flask import request, jsonify, render_template
from pathlib import Path

logger = logging.getLogger(__name__)

def register_custom_functions_routes(app):
    """Register all custom functions routes"""
    logger.info("Registering custom functions routes...")

    CUSTOM_FUNCTIONS_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'custom_functions.json')

    def _load_custom_functions():
        """Load custom functions from JSON file"""
        try:
            if os.path.exists(CUSTOM_FUNCTIONS_FILE):
                with open(CUSTOM_FUNCTIONS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                default_data = {'functions': []}
                os.makedirs(os.path.dirname(CUSTOM_FUNCTIONS_FILE), exist_ok=True)
                with open(CUSTOM_FUNCTIONS_FILE, 'w', encoding='utf-8') as f:
                    json.dump(default_data, f, indent=2)
                return default_data
        except Exception as e:
            logger.error(f"Error loading custom functions: {e}")
            return {'functions': []}

    def _save_custom_functions(data):
        """Save custom functions to JSON file"""
        try:
            os.makedirs(os.path.dirname(CUSTOM_FUNCTIONS_FILE), exist_ok=True)
            with open(CUSTOM_FUNCTIONS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Error saving custom functions: {e}")
            return False

    # ============================================================================
    # FRONTEND ROUTES
    # ============================================================================

    @app.route('/custom_functions')
    def custom_functions_page():
        """Render custom functions management page"""
        return render_template('custom_functions.html')

    @app.route('/custom_function_builder')
    def custom_function_builder():
        """Render custom function builder/editor page"""
        return render_template('custom_function_builder.html')

    @app.route('/api/document_types_list', methods=['GET'])
    def get_document_types_list():
        """Get list of all available document types from document_entities directory"""
        try:
            entities_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'document_entities')
            document_types = []

            if os.path.exists(entities_dir):
                for filename in os.listdir(entities_dir):
                    if filename.endswith('.json'):
                        filepath = os.path.join(entities_dir, filename)
                        with open(filepath, 'r', encoding='utf-8') as f:
                            doc_data = json.load(f)
                            document_types.append({
                                'documentId': doc_data.get('documentId'),
                                'documentName': doc_data.get('documentName'),
                                'fieldCount': len(doc_data.get('mappings', []))
                            })

            # Sort by name
            document_types.sort(key=lambda x: x['documentName'])

            return jsonify({'success': True, 'documentTypes': document_types}), 200
        except Exception as e:
            logger.error(f"Error getting document types list: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/document_entities/<document_id>', methods=['GET'])
    def get_document_entities(document_id):
        """Get all entities/fields for a specific document type"""
        try:
            entities_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'document_entities')
            filepath = os.path.join(entities_dir, f'{document_id}.json')

            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    doc_data = json.load(f)
                    return jsonify({
                        'success': True,
                        'documentId': doc_data.get('documentId'),
                        'documentName': doc_data.get('documentName'),
                        'entities': doc_data.get('mappings', [])
                    }), 200
            else:
                return jsonify({'success': False, 'message': 'Document type not found'}), 404

        except Exception as e:
            logger.error(f"Error getting document entities for {document_id}: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    # ============================================================================
    # API ROUTES
    # ============================================================================

    @app.route('/api/custom_functions', methods=['GET'])
    def get_all_custom_functions():
        """Get all custom functions"""
        try:
            data = _load_custom_functions()
            functions = data.get('functions', [])

            # Optional: Filter by category or active status
            category = request.args.get('category')
            active_only = request.args.get('active', 'false').lower() == 'true'

            if category:
                functions = [f for f in functions if f.get('category') == category]

            if active_only:
                functions = [f for f in functions if f.get('isActive', True)]

            return jsonify({'success': True, 'functions': functions}), 200
        except Exception as e:
            logger.error(f"Error getting custom functions: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/custom_functions/<function_id>', methods=['GET'])
    def get_custom_function(function_id):
        """Get a single custom function by ID"""
        try:
            data = _load_custom_functions()
            functions = data.get('functions', [])

            function = next((f for f in functions if f.get('id') == function_id), None)

            if function:
                return jsonify({'success': True, 'function': function}), 200
            else:
                return jsonify({'success': False, 'message': 'Function not found'}), 404
        except Exception as e:
            logger.error(f"Error getting custom function {function_id}: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/custom_functions', methods=['POST'])
    def create_custom_function():
        """Create a new custom function"""
        try:
            function_data = request.get_json()

            # Validate required fields
            required_fields = ['name', 'description', 'category']
            for field in required_fields:
                if not function_data.get(field):
                    return jsonify({'success': False, 'message': f'Missing required field: {field}'}), 400

            data = _load_custom_functions()

            # Generate new ID
            existing_ids = [int(f['id']) for f in data.get('functions', []) if f.get('id', '').isdigit()]
            new_id = str(max(existing_ids, default=0) + 1)

            # Create new function
            new_function = {
                'id': new_id,
                'name': function_data.get('name'),
                'description': function_data.get('description'),
                'category': function_data.get('category'),
                'documentRequirements': function_data.get('documentRequirements', []),
                'llmPrompts': function_data.get('llmPrompts', {
                    'classificationPrompt': '',
                    'extractionPrompt': '',
                    'validationPrompt': ''
                }),
                'workflowSteps': function_data.get('workflowSteps', []),
                'createdBy': function_data.get('createdBy', 'system'),
                'createdAt': datetime.utcnow().isoformat() + 'Z',
                'updatedAt': datetime.utcnow().isoformat() + 'Z',
                'isActive': function_data.get('isActive', True)
            }

            if 'functions' not in data:
                data['functions'] = []

            data['functions'].append(new_function)

            if _save_custom_functions(data):
                return jsonify({'success': True, 'function': new_function}), 201
            else:
                return jsonify({'success': False, 'message': 'Failed to save function'}), 500

        except Exception as e:
            logger.error(f"Error creating custom function: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/custom_functions/<function_id>', methods=['PUT'])
    def update_custom_function(function_id):
        """Update an existing custom function"""
        try:
            function_data = request.get_json()
            data = _load_custom_functions()

            # Find and update function
            found = False
            for i, function in enumerate(data.get('functions', [])):
                if function.get('id') == function_id:
                    # Preserve creation metadata
                    created_by = function.get('createdBy', 'system')
                    created_at = function.get('createdAt', datetime.utcnow().isoformat() + 'Z')

                    data['functions'][i] = {
                        'id': function_id,
                        'name': function_data.get('name'),
                        'description': function_data.get('description'),
                        'category': function_data.get('category'),
                        'documentRequirements': function_data.get('documentRequirements', []),
                        'llmPrompts': function_data.get('llmPrompts', {}),
                        'workflowSteps': function_data.get('workflowSteps', []),
                        'createdBy': created_by,
                        'createdAt': created_at,
                        'updatedAt': datetime.utcnow().isoformat() + 'Z',
                        'isActive': function_data.get('isActive', True)
                    }
                    found = True

                    if _save_custom_functions(data):
                        return jsonify({'success': True, 'function': data['functions'][i]}), 200
                    else:
                        return jsonify({'success': False, 'message': 'Failed to save function'}), 500

            if not found:
                return jsonify({'success': False, 'message': 'Function not found'}), 404

        except Exception as e:
            logger.error(f"Error updating custom function {function_id}: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/custom_functions/<function_id>', methods=['DELETE'])
    def delete_custom_function(function_id):
        """Delete a custom function"""
        try:
            data = _load_custom_functions()

            # Find and remove function
            original_length = len(data.get('functions', []))
            data['functions'] = [f for f in data.get('functions', []) if f.get('id') != function_id]

            if len(data['functions']) < original_length:
                if _save_custom_functions(data):
                    return jsonify({'success': True, 'message': 'Function deleted successfully'}), 200
                else:
                    return jsonify({'success': False, 'message': 'Failed to save changes'}), 500
            else:
                return jsonify({'success': False, 'message': 'Function not found'}), 404

        except Exception as e:
            logger.error(f"Error deleting custom function {function_id}: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/custom_functions/<function_id>/toggle', methods=['POST'])
    def toggle_custom_function(function_id):
        """Toggle active/inactive status of a custom function"""
        try:
            data = _load_custom_functions()

            for function in data.get('functions', []):
                if function.get('id') == function_id:
                    function['isActive'] = not function.get('isActive', True)
                    function['updatedAt'] = datetime.utcnow().isoformat() + 'Z'

                    if _save_custom_functions(data):
                        return jsonify({'success': True, 'function': function}), 200
                    else:
                        return jsonify({'success': False, 'message': 'Failed to save changes'}), 500

            return jsonify({'success': False, 'message': 'Function not found'}), 404

        except Exception as e:
            logger.error(f"Error toggling custom function {function_id}: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    logger.info("Custom functions routes registered successfully")
