"""
Admin Configuration Routes for Admin_Configuraton module
Handles CRUD operations for data categories, entities, document categories,
document types, document entity mappings, and prompt configurations.
"""

import os
import logging

from flask import Flask, request, jsonify, render_template, send_file

from .data_category_manager import DataCategoryManager
from .entity_manager import EntityManager
from .document_category_manager import DocumentCategoryManager
from .document_type_category_manager import DocumentTypeCategoryManager
from .document_entity_mapping_manager import DocumentEntityMappingManager
from .prompt_config_manager import PromptConfigManager

logger = logging.getLogger(__name__)


def register_admin_config_routes(app: Flask, timing_aspect, load_prompt_config_func=None, login_required=None, db=None, users_collection=None, ALLOWED_EMAILS=None):
    """
    Register admin configuration routes with the Flask app.
    
    Routes registered:
    - Data Categories: /api/data_categories (CRUD)
    - Entities: /api/entities (CRUD)
    - Prompt Config: /api/prompt-config (CRUD + export/reload)
    - Document Categories: /api/document_categories (CRUD)
    - Document Entity Maintenance: /api/document_entity_maintenance (CRUD)
    - Document Types: /api/document-types (CRUD)
    - Document Type Categories: /api/document-types/categories, /api/document-categories (CRUD)
    
    Args:
        app: Flask application instance
        timing_aspect: Decorator for timing/logging
        load_prompt_config_func: Optional function to reload prompt config
    """
    
    # Initialize managers
    data_category_manager = DataCategoryManager()
    entity_manager = EntityManager()
    prompt_config_manager = PromptConfigManager()
    document_category_manager = DocumentCategoryManager()
    document_type_category_manager = DocumentTypeCategoryManager()
    document_entity_mapping_manager = DocumentEntityMappingManager()

    # ==========================================================================
    # DATA CATEGORIES ROUTES
    # ==========================================================================

    @app.route('/data_categories')
    @timing_aspect
    def data_categories():
        """Data categories management page"""
        return render_template('data_categories.html')

    @app.route('/api/data_categories', methods=['GET'])
    @timing_aspect
    def get_all_categories():
        """Get all data categories"""
        try:
            categories = data_category_manager.get_all()
            return jsonify({'success': True, 'categories': categories}), 200
        except Exception as e:
            logger.error(f"Error getting categories: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/data_categories', methods=['POST'])
    @timing_aspect
    def create_category():
        """Create a new category"""
        try:
            result = data_category_manager.create(request.json)
            if result['success']:
                return jsonify(result), 201
            return jsonify(result), 400
        except Exception as e:
            logger.error(f"Error creating category: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/data_categories/<category_id>', methods=['PUT'])
    @timing_aspect
    def update_category(category_id):
        """Update a category"""
        try:
            result = data_category_manager.update(category_id, request.json)
            if result['success']:
                return jsonify(result), 200
            return jsonify(result), 404
        except Exception as e:
            logger.error(f"Error updating category {category_id}: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/data_categories/<category_id>', methods=['DELETE'])
    @timing_aspect
    def delete_category(category_id):
        """Delete a category"""
        try:
            result = data_category_manager.delete(category_id)
            if result['success']:
                return jsonify(result), 200
            return jsonify(result), 404
        except Exception as e:
            logger.error(f"Error deleting category {category_id}: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    # ==========================================================================
    # ENTITIES ROUTES
    # ==========================================================================

    @app.route('/entities')
    @timing_aspect
    def entities():
        """Entities management page"""
        return render_template('entities.html')

    @app.route('/api/entities', methods=['GET'])
    @timing_aspect
    def get_all_entities():
        """Get all entities"""
        try:
            entities_list = entity_manager.get_all()
            return jsonify({'success': True, 'entities': entities_list}), 200
        except Exception as e:
            logger.error(f"Error getting entities: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/entities', methods=['POST'])
    @timing_aspect
    def create_entity():
        """Create a new entity"""
        try:
            result = entity_manager.create(request.json)
            if result['success']:
                return jsonify(result), 201
            return jsonify(result), 400
        except Exception as e:
            logger.error(f"Error creating entity: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/entities/<entity_id>', methods=['PUT'])
    @timing_aspect
    def update_entity(entity_id):
        """Update an entity"""
        try:
            result = entity_manager.update(entity_id, request.json)
            if result['success']:
                return jsonify(result), 200
            return jsonify(result), 404
        except Exception as e:
            logger.error(f"Error updating entity {entity_id}: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/entities/<entity_id>', methods=['DELETE'])
    @timing_aspect
    def delete_entity(entity_id):
        """Delete an entity"""
        try:
            result = entity_manager.delete(entity_id)
            if result['success']:
                return jsonify(result), 200
            return jsonify(result), 404
        except Exception as e:
            logger.error(f"Error deleting entity {entity_id}: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    # ==========================================================================
    # PROMPT CONFIGURATION ROUTES
    # ==========================================================================

    @app.route('/prompt-config')
    @timing_aspect
    def prompt_config_page():
        """Prompt configuration management page"""
        return render_template('prompt_config.html')

    @app.route('/api/prompt-config', methods=['GET'])
    @timing_aspect
    def get_prompt_config():
        """Get current prompt configuration from YAML"""
        try:
            result = prompt_config_manager.get_config()
            if result['success']:
                return jsonify(result), 200
            return jsonify(result), 404
        except Exception as e:
            logger.error(f"Error loading prompt config: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/prompt-config', methods=['POST'])
    @timing_aspect
    def update_prompt_config():
        """Update prompt configuration in YAML"""
        try:
            result = prompt_config_manager.update_config(request.json)
            if result['success']:
                # Reload the configuration immediately if callback provided
                if load_prompt_config_func:
                    load_prompt_config_func()
                logger.info("SUCCESS: Prompt configuration updated and reloaded successfully")
            return jsonify(result), 200 if result['success'] else 500
        except Exception as e:
            logger.error(f"Error updating prompt config: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/prompt-config/reset', methods=['POST'])
    @timing_aspect
    def reset_prompt_config():
        """Reset prompt configuration to defaults"""
        try:
            result = prompt_config_manager.reset_config()
            if result['success']:
                logger.info("Prompt configuration reset to defaults")
            return jsonify(result), 200 if result['success'] else 500
        except Exception as e:
            logger.error(f"Error resetting prompt config: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/prompt-config/export', methods=['GET'])
    @timing_aspect
    def export_prompt_config():
        """Export current prompt configuration as YAML"""
        try:
            config_path = prompt_config_manager.export_config()
            if config_path and os.path.exists(config_path):
                return send_file(
                    config_path,
                    mimetype='application/x-yaml',
                    as_attachment=True,
                    download_name='document_classification_config.yaml'
                )
            return jsonify({'success': False, 'message': 'Configuration file not found'}), 404
        except Exception as e:
            logger.error(f"Error exporting prompt config: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/prompt-config/reload', methods=['POST'])
    @timing_aspect
    def reload_prompt_config():
        """Manually reload prompt configuration from YAML"""
        try:
            result = prompt_config_manager.reload_config()
            if result['success']:
                # Reload the configuration if callback provided
                if load_prompt_config_func:
                    load_prompt_config_func()
                logger.info("SUCCESS: Prompt configuration manually reloaded")
            return jsonify(result), 200 if result['success'] else 500
        except Exception as e:
            logger.error(f"Error reloading prompt config: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    # ==========================================================================
    # DOCUMENT CATEGORIES ROUTES
    # ==========================================================================

    @app.route('/document_categories')
    @timing_aspect
    def document_categories():
        """Document categories management page"""
        return render_template('document_categories.html')

    @app.route('/api/document_categories', methods=['GET'])
    @timing_aspect
    def get_all_document_categories():
        """Get all document categories"""
        try:
            categories = document_category_manager.get_all()
            return jsonify({'success': True, 'categories': categories}), 200
        except Exception as e:
            logger.error(f"Error getting document categories: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/document_categories', methods=['POST'])
    @timing_aspect
    def create_document_category():
        """Create a new document category"""
        try:
            result = document_category_manager.create(request.get_json())
            if result['success']:
                return jsonify(result), 201
            return jsonify(result), 400
        except Exception as e:
            logger.error(f"Error creating document category: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/document_categories/<category_id>', methods=['PUT'])
    @timing_aspect
    def update_document_category(category_id):
        """Update an existing document category"""
        try:
            result = document_category_manager.update(category_id, request.get_json())
            if result['success']:
                return jsonify(result), 200
            return jsonify(result), 404
        except Exception as e:
            logger.error(f"Error updating document category: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/document_categories/<category_id>', methods=['DELETE'])
    @timing_aspect
    def delete_document_category(category_id):
        """Delete a document category"""
        try:
            result = document_category_manager.delete(category_id)
            if result['success']:
                return jsonify(result), 200
            return jsonify(result), 404
        except Exception as e:
            logger.error(f"Error deleting document category: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    # ==========================================================================
    # DOCUMENT ENTITY MAINTENANCE ROUTES
    # ==========================================================================

    @app.route('/document_entity_maintenance')
    @timing_aspect
    def document_entity_maintenance():
        """Render document entity maintenance page"""
        return render_template('document_entity_maintenance.html')

    @app.route('/api/document_entity_maintenance', methods=['GET'])
    @timing_aspect
    def get_all_document_entity_mappings():
        """Get all document entity mappings"""
        try:
            mappings = document_entity_mapping_manager.get_all()
            return jsonify({'success': True, 'mappings': mappings}), 200
        except Exception as e:
            logger.error(f"Error getting document entity mappings: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/document_entity_maintenance', methods=['POST'])
    @timing_aspect
    def create_document_entity_mapping():
        """Create a new document entity mapping"""
        try:
            result = document_entity_mapping_manager.create(request.get_json())
            if result['success']:
                return jsonify(result), 201
            return jsonify(result), 400
        except Exception as e:
            logger.error(f"Error creating document entity mapping: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/document_entity_maintenance/<mapping_id>', methods=['PUT'])
    @timing_aspect
    def update_document_entity_mapping(mapping_id):
        """Update a document entity mapping"""
        try:
            result = document_entity_mapping_manager.update(mapping_id, request.get_json())
            if result['success']:
                return jsonify(result), 200
            return jsonify(result), 404
        except Exception as e:
            logger.error(f"Error updating document entity mapping {mapping_id}: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/document_entity_maintenance/<mapping_id>', methods=['DELETE'])
    @timing_aspect
    def delete_document_entity_mapping(mapping_id):
        """Delete a document entity mapping"""
        try:
            result = document_entity_mapping_manager.delete(mapping_id)
            if result['success']:
                return jsonify(result), 200
            return jsonify(result), 404
        except Exception as e:
            logger.error(f"Error deleting document entity mapping {mapping_id}: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    # ==========================================================================
    # DOCUMENT TYPES ROUTES
    # ==========================================================================

    @app.route('/document-types-management')
    @timing_aspect
    def document_types_management():
        """Render document types management page"""
        return render_template('document_types_management.html')

    @app.route('/api/document-types', methods=['GET'])
    @timing_aspect
    def get_all_document_types():
        """Get all unique document types from mappings"""
        try:
            document_types = document_entity_mapping_manager.get_document_types()
            return jsonify({'success': True, 'documentTypes': document_types}), 200
        except Exception as e:
            logger.error(f"Error getting document types: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/document-types/<document_id>', methods=['GET'])
    @timing_aspect
    def get_document_type(document_id):
        """Get a specific document type with its fields"""
        try:
            mappings = document_entity_mapping_manager.get_by_document(document_id)
            if not mappings:
                return jsonify({'success': False, 'message': 'Document type not found'}), 404

            doc_info = {
                'documentId': document_id,
                'documentName': mappings[0].get('documentName') if mappings else '',
                'documentCategoryId': mappings[0].get('documentCategoryId') if mappings else '',
                'documentCategoryName': mappings[0].get('documentCategoryName') if mappings else '',
                'fields': mappings
            }
            return jsonify({'success': True, 'documentType': doc_info}), 200
        except Exception as e:
            logger.error(f"Error getting document type {document_id}: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/document-types', methods=['POST'])
    @timing_aspect
    def create_document_type():
        """Create a new document type"""
        try:
            req_data = request.get_json()
            document_id = req_data.get('documentId')
            document_name = req_data.get('documentName')
            category_id = req_data.get('documentCategoryId')
            category_name = req_data.get('documentCategoryName')

            if not all([document_id, document_name, category_id]):
                return jsonify({'success': False, 'message': 'Missing required fields'}), 400

            # Check if document type already exists
            existing = document_entity_mapping_manager.get_by_document(document_id)
            if existing:
                return jsonify({'success': False, 'message': 'Document type already exists'}), 400

            # Create initial mapping for the new document type
            mapping_data = {
                'documentId': document_id,
                'documentName': document_name,
                'documentCategoryId': category_id,
                'documentCategoryName': category_name,
                'entityId': '',
                'entityName': '',
                'mappingFormField': '',
                'mappingFormDescription': '',
                'dataCategoryId': '',
                'dataCategoryValue': '',
                'fieldType': 'optional'
            }

            result = document_entity_mapping_manager.create(mapping_data)
            if result['success']:
                return jsonify({'success': True, 'message': 'Document type created successfully', 'documentType': result.get('mapping')}), 201
            return jsonify(result), 500

        except Exception as e:
            logger.error(f"Error creating document type: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/document-types/<document_id>', methods=['PUT'])
    @timing_aspect
    def update_document_type(document_id):
        """Update a document type"""
        try:
            req_data = request.get_json()
            new_name = req_data.get('documentName')
            new_category_id = req_data.get('documentCategoryId')
            new_category_name = req_data.get('documentCategoryName')

            # Get all mappings for this document
            mappings = document_entity_mapping_manager.get_by_document(document_id)
            if not mappings:
                return jsonify({'success': False, 'message': 'Document type not found'}), 404

            # Update each mapping
            updated_count = 0
            for mapping in mappings:
                update_data = {
                    'documentId': document_id,
                    'documentName': new_name or mapping.get('documentName'),
                    'documentCategoryId': new_category_id or mapping.get('documentCategoryId'),
                    'documentCategoryName': new_category_name or mapping.get('documentCategoryName'),
                    'entityId': mapping.get('entityId'),
                    'entityName': mapping.get('entityName'),
                    'mappingFormField': mapping.get('mappingFormField'),
                    'mappingFormDescription': mapping.get('mappingFormDescription'),
                    'dataCategoryId': mapping.get('dataCategoryId'),
                    'dataCategoryValue': mapping.get('dataCategoryValue'),
                    'fieldType': mapping.get('fieldType')
                }
                result = document_entity_mapping_manager.update(mapping.get('id'), update_data)
                if result['success']:
                    updated_count += 1

            return jsonify({'success': True, 'message': f'Document type updated successfully ({updated_count} mappings)'}), 200

        except Exception as e:
            logger.error(f"Error updating document type {document_id}: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/document-types/<document_id>', methods=['DELETE'])
    @timing_aspect
    def delete_document_type(document_id):
        """Delete a document type and all its field mappings"""
        try:
            # Get all mappings for this document
            mappings = document_entity_mapping_manager.get_by_document(document_id)
            if not mappings:
                return jsonify({'success': False, 'message': 'Document type not found'}), 404

            # Delete each mapping
            deleted_count = 0
            for mapping in mappings:
                result = document_entity_mapping_manager.delete(mapping.get('id'))
                if result['success']:
                    deleted_count += 1

            return jsonify({'success': True, 'message': f'Document type and {deleted_count} field mappings deleted successfully'}), 200

        except Exception as e:
            logger.error(f"Error deleting document type {document_id}: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    # ==========================================================================
    # DOCUMENT TYPE CATEGORIES ROUTES
    # ==========================================================================

    @app.route('/api/document-types/categories', methods=['GET'])
    @timing_aspect
    def get_document_type_categories():
        """Get all document type categories from config"""
        try:
            categories = document_type_category_manager.get_all()
            return jsonify({'success': True, 'categories': categories}), 200
        except Exception as e:
            logger.error(f"Error getting document type categories: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/document-categories', methods=['POST'])
    @timing_aspect
    def create_document_type_category():
        """Create a new document type category"""
        try:
            result = document_type_category_manager.create(request.get_json())
            if result['success']:
                return jsonify(result), 201
            return jsonify(result), 400
        except Exception as e:
            logger.error(f"Error creating document type category: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/document-categories/<int:category_id>', methods=['PUT'])
    @timing_aspect
    def update_document_type_category(category_id):
        """Update a document type category"""
        try:
            result = document_type_category_manager.update(category_id, request.get_json())
            if result['success']:
                return jsonify(result), 200
            return jsonify(result), 404
        except Exception as e:
            logger.error(f"Error updating document type category {category_id}: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/document-categories/<int:category_id>', methods=['DELETE'])
    @timing_aspect
    def delete_document_type_category(category_id):
        """Delete a document type category"""
        try:
            result = document_type_category_manager.delete(category_id)
            if result['success']:
                return jsonify(result), 200
            return jsonify(result), 404
        except Exception as e:
            logger.error(f"Error deleting document type category {category_id}: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    # ==========================================================================
    # DATA FILE SERVING ROUTE
    # ==========================================================================

    @app.route('/data/<path:filename>')
    def serve_data_file(filename):
        """
        Serve data files from the root data directory.
        Used for fetching configuration files, JSON data, etc.
        """
        try:
            # Root data folder is one level up from app folder
            data_dir = os.path.join(app.root_path, '..', 'data')
            return send_file(os.path.join(data_dir, filename))
        except Exception as e:
            logger.error(f"Error serving data file {filename}: {e}")
            return jsonify({"error": "File not found"}), 404

    # ==========================================================================
    # DISCREPANCY CONFIG ROUTE
    # ==========================================================================

    @app.route('/admin/discrepancy-config', methods=['GET', 'POST'])
    @timing_aspect
    def discrepancy_config_api():
        """Get or update discrepancy check configuration"""
        import json
        from datetime import datetime
        
        def load_discrepancy_config():
            """Load discrepancy config from file"""
            config_path = os.path.join(app.root_path, '..', 'data', 'discrepancy_check_config.json')
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return None
        
        def validate_config_structure(config):
            """Validate the configuration structure"""
            # Basic validation - can be enhanced
            if not isinstance(config, dict):
                return False
            return True
        
        try:
            if request.method == 'GET':
                # Return current configuration
                config = load_discrepancy_config()
                if not config:
                    return jsonify({
                        'success': False,
                        'message': 'Configuration not found'
                    }), 404

                # Remove sensitive information like API keys from response
                safe_config = config.copy()
                if 'api_keys' in safe_config:
                    del safe_config['api_keys']

                return jsonify({
                    'success': True,
                    'config': safe_config,
                    'timestamp': datetime.now().isoformat()
                }), 200

            elif request.method == 'POST':
                # Update configuration
                new_config = request.get_json()
                if not new_config:
                    return jsonify({
                        'success': False,
                        'message': 'No configuration data provided'
                    }), 400

                # Validate configuration structure
                if not validate_config_structure(new_config):
                    return jsonify({
                        'success': False,
                        'message': 'Invalid configuration structure'
                    }), 400

                # Save configuration
                config_path = os.path.join(app.root_path, '..', 'data', 'discrepancy_check_config.json')
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(new_config, f, indent=2, ensure_ascii=False)

                logger.info("✅ Discrepancy check configuration updated")

                return jsonify({
                    'success': True,
                    'message': 'Configuration updated successfully',
                    'timestamp': datetime.now().isoformat()
                }), 200

        except Exception as e:
            logger.error(f"Error in discrepancy config API: {e}")
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    # ==========================================================================
    # ADMIN MANUAL DELETION ROUTE
    # ==========================================================================

    @app.route('/api/admin/delete-manual/<manual_name>', methods=['DELETE'])
    @login_required
    @timing_aspect
    def admin_delete_manual(manual_name):
        """Delete a manual (admin only)"""
        from datetime import datetime
        from flask import session
        
        try:
            # Check if user is admin
            user_id = session.get('user_id')
            user = users_collection.find_one({'_id': user_id})

            # Check if user is allowed
            email = user.get('email', '') if user else ''
            if email.lower() not in [e.lower() for e in ALLOWED_EMAILS]:
                return jsonify({'success': False, 'message': 'Access denied'}), 403

            # Soft delete - just mark as inactive
            result = db.manuals.update_one(
                {'name': manual_name},
                {'$set': {'is_active': False, 'deleted_at': datetime.utcnow()}}
            )

            if result.modified_count > 0:
                return jsonify({
                    'success': True,
                    'message': f'Manual {manual_name} deleted successfully'
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'message': f'Manual {manual_name} not found'
                }), 404

        except Exception as e:
            logger.error(f"Error deleting manual: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    logger.info("✅ Admin Configuration routes registered successfully")
