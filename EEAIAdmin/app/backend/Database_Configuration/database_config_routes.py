"""
Database Configuration Routes

Flask routes for database configuration management, query generation, and LLM-based SQL.
"""

import os
import json
import logging
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from flask_login import login_required

from .llm_query_generator import (
    generate_sql_with_openai,
    generate_sql_with_anthropic,
    generate_query_recipe_with_ai
)

logger = logging.getLogger(__name__)

# Will be set during registration
timing_aspect = None
openai_client = None


def register_database_config_routes(app: Flask, decorators: dict = None, openai_module=None):
    """
    Register all database configuration routes with the Flask app.
    
    Args:
        app: Flask application instance
        decorators: Dictionary containing decorator functions (e.g., {'timing_aspect': timing_aspect})
        openai_module: OpenAI module for Azure OpenAI calls
    """
    global timing_aspect, openai_client
    
    # Set up decorators
    if decorators:
        timing_aspect = decorators.get('timing_aspect')
    
    # Set up OpenAI client
    if openai_module:
        openai_client = openai_module
    
    # Default timing aspect if not provided
    if timing_aspect is None:
        def timing_aspect(f):
            return f
    
    logger.info("Registering Database Configuration routes...")

    # ========== PAGE ROUTES ==========

    @app.route('/database_configuration')
    @timing_aspect
    def database_configuration():
        """Render database configuration page"""
        return render_template('database_configuration.html')

    # ========== CONFIG API ROUTES ==========

    @app.route('/api/database-config', methods=['GET'])
    @timing_aspect
    def get_database_config():
        """Get full database configuration"""
        try:
            from app.utils.query_generator import QueryGenerator
            qgen = QueryGenerator()

            return jsonify({
                'success': True,
                'config': qgen.config
            }), 200
        except Exception as e:
            logger.error(f"Error loading database config: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/database-config/modules', methods=['GET'])
    @login_required
    @timing_aspect
    def get_modules():
        """Get all available modules"""
        try:
            from app.utils.query_generator import QueryGenerator
            qgen = QueryGenerator()
            modules = qgen.get_available_modules()

            return jsonify({
                'success': True,
                'modules': modules
            }), 200
        except Exception as e:
            logger.error(f"Error getting modules: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/database-config/modules/<module_id>', methods=['GET'])
    @timing_aspect
    def get_module_detail(module_id):
        """Get detailed module information including intents"""
        try:
            from app.utils.query_generator import QueryGenerator
            qgen = QueryGenerator()

            module = qgen.modules.get(module_id)
            if not module:
                return jsonify({
                    'success': False,
                    'error': f'Module not found: {module_id}'
                }), 404

            intents = qgen.get_module_intents(module_id)

            return jsonify({
                'success': True,
                'module': {
                    'id': module_id,
                    'name': module.get('name'),
                    'description': module.get('description'),
                    'icon': module.get('icon'),
                    'entry_tables': module.get('entry_tables', []),
                    'intents': intents
                }
            }), 200
        except Exception as e:
            logger.error(f"Error getting module {module_id}: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/database-config/tables', methods=['GET'])
    @timing_aspect
    def get_tables():
        """Get all tables configuration"""
        try:
            from app.utils.query_generator import QueryGenerator
            qgen = QueryGenerator()

            tables = [
                {
                    'id': table_id,
                    'name': table_data.get('name'),
                    'description': table_data.get('description'),
                    'pk': table_data.get('pk'),
                    'columns': table_data.get('columns', []),
                    'rbac': table_data.get('rbac', {})
                }
                for table_id, table_data in qgen.tables.items()
            ]

            return jsonify({
                'success': True,
                'tables': tables
            }), 200
        except Exception as e:
            logger.error(f"Error getting tables: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/database-config/recipes', methods=['GET'])
    @login_required
    @timing_aspect
    def get_recipes():
        """Get all query recipes"""
        try:
            from app.utils.query_generator import QueryGenerator
            qgen = QueryGenerator()

            recipes = [
                qgen.get_recipe_info(recipe_id)
                for recipe_id in qgen.recipes.keys()
            ]

            return jsonify({
                'success': True,
                'recipes': recipes
            }), 200
        except Exception as e:
            logger.error(f"Error getting recipes: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/database-config/recipes/<recipe_id>', methods=['GET'])
    @login_required
    @timing_aspect
    def get_recipe_detail(recipe_id):
        """Get detailed recipe information"""
        try:
            from app.utils.query_generator import QueryGenerator
            qgen = QueryGenerator()

            recipe = qgen.get_recipe_info(recipe_id)
            if not recipe:
                return jsonify({
                    'success': False,
                    'error': f'Recipe not found: {recipe_id}'
                }), 404

            return jsonify({
                'success': True,
                'recipe': recipe
            }), 200
        except Exception as e:
            logger.error(f"Error getting recipe {recipe_id}: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/database-config/save', methods=['POST'])
    @timing_aspect
    def save_database_config():
        """Save updated database configuration to JSON file"""
        try:
            data = request.get_json()
            config_updates = data.get('config')

            if not config_updates:
                return jsonify({
                    'success': False,
                    'error': 'Configuration data is required'
                }), 400

            # Update timestamp
            if 'metadata' in config_updates:
                config_updates['metadata']['lastUpdated'] = datetime.now().isoformat()

            # Save to file
            config_path = 'app/config/database_query_config.json'
            with open(config_path, 'w') as f:
                json.dump(config_updates, f, indent=2)

            logger.info("Database configuration saved successfully")

            return jsonify({
                'success': True,
                'message': 'Configuration saved successfully'
            }), 200

        except Exception as e:
            logger.error(f"Error saving database config: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/database-config/validate', methods=['POST'])
    @login_required
    @timing_aspect
    def validate_database_config():
        """Validate database configuration structure"""
        try:
            data = request.get_json()
            config = data.get('config')

            if not config:
                return jsonify({
                    'success': False,
                    'error': 'Configuration data is required'
                }), 400

            errors = []
            warnings = []

            # Validate required sections
            required_sections = ['modules', 'tables', 'recipes', 'query_settings']
            for section in required_sections:
                if section not in config:
                    errors.append(f"Missing required section: {section}")

            # Validate modules
            for mod_id, mod_data in config.get('modules', {}).items():
                if 'name' not in mod_data:
                    errors.append(f"Module {mod_id} missing 'name'")
                if 'intents' not in mod_data or not mod_data['intents']:
                    warnings.append(f"Module {mod_id} has no intents defined")

            # Validate recipes reference valid tables
            tables = config.get('tables', {})
            for recipe_id, recipe_data in config.get('recipes', {}).items():
                base_table = recipe_data.get('base')
                if base_table and base_table not in tables:
                    errors.append(f"Recipe {recipe_id} references unknown table: {base_table}")

            # Validate RBAC roles
            if 'rbac_roles' in config and not config['rbac_roles']:
                warnings.append("No RBAC roles defined")

            is_valid = len(errors) == 0

            return jsonify({
                'success': True,
                'valid': is_valid,
                'errors': errors,
                'warnings': warnings
            }), 200

        except Exception as e:
            logger.error(f"Error validating config: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    # ========== MODULE CRUD ==========

    @app.route('/api/database-config/modules', methods=['POST'])
    @timing_aspect
    def create_module():
        """Create a new module"""
        try:
            data = request.get_json()
            module_id = data.get('id')
            module_data = data.get('data')

            if not module_id or not module_data:
                return jsonify({
                    'success': False,
                    'error': 'module id and data are required'
                }), 400

            config_path = 'app/config/database_query_config.json'
            with open(config_path, 'r') as f:
                config = json.load(f)

            if module_id in config.get('modules', {}):
                return jsonify({
                    'success': False,
                    'error': f'Module {module_id} already exists'
                }), 400

            if 'modules' not in config:
                config['modules'] = {}
            config['modules'][module_id] = module_data

            if 'metadata' not in config:
                config['metadata'] = {}
            config['metadata']['lastUpdated'] = datetime.now().isoformat()

            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)

            logger.info(f"Created module: {module_id}")

            return jsonify({
                'success': True,
                'message': f'Module {module_id} created successfully'
            }), 201

        except Exception as e:
            logger.error(f"Error creating module: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/database-config/modules/<module_id>', methods=['PUT'])
    @timing_aspect
    def update_module(module_id):
        """Update an existing module"""
        try:
            data = request.get_json()
            module_data = data.get('data')

            if not module_data:
                return jsonify({
                    'success': False,
                    'error': 'module data is required'
                }), 400

            config_path = 'app/config/database_query_config.json'
            with open(config_path, 'r') as f:
                config = json.load(f)

            if module_id not in config.get('modules', {}):
                return jsonify({
                    'success': False,
                    'error': f'Module {module_id} not found'
                }), 404

            config['modules'][module_id] = module_data

            if 'metadata' not in config:
                config['metadata'] = {}
            config['metadata']['lastUpdated'] = datetime.now().isoformat()

            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)

            logger.info(f"Updated module: {module_id}")

            return jsonify({
                'success': True,
                'message': f'Module {module_id} updated successfully'
            }), 200

        except Exception as e:
            logger.error(f"Error updating module: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/database-config/modules/<module_id>', methods=['DELETE'])
    @timing_aspect
    def delete_module(module_id):
        """Delete a module"""
        try:
            config_path = 'app/config/database_query_config.json'
            with open(config_path, 'r') as f:
                config = json.load(f)

            if module_id not in config.get('modules', {}):
                return jsonify({
                    'success': False,
                    'error': f'Module {module_id} not found'
                }), 404

            module_intents = config['modules'][module_id].get('intents', {})
            used_recipes = [intent.get('recipe') for intent in module_intents.values() if intent.get('recipe')]

            if used_recipes:
                return jsonify({
                    'success': False,
                    'error': f'Cannot delete module {module_id}: used by recipes {", ".join(used_recipes)}'
                }), 400

            del config['modules'][module_id]

            if 'metadata' not in config:
                config['metadata'] = {}
            config['metadata']['lastUpdated'] = datetime.now().isoformat()

            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)

            logger.info(f"Deleted module: {module_id}")

            return jsonify({
                'success': True,
                'message': f'Module {module_id} deleted successfully'
            }), 200

        except Exception as e:
            logger.error(f"Error deleting module: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    # ========== TABLE CRUD ==========

    @app.route('/api/database-config/tables', methods=['POST'])
    @timing_aspect
    def create_table():
        """Create a new table definition"""
        try:
            data = request.get_json()
            table_id = data.get('id')
            table_data = data.get('data')

            if not table_id or not table_data:
                return jsonify({
                    'success': False,
                    'error': 'table id and data are required'
                }), 400

            config_path = 'app/config/database_query_config.json'
            with open(config_path, 'r') as f:
                config = json.load(f)

            if table_id in config.get('tables', {}):
                return jsonify({
                    'success': False,
                    'error': f'Table {table_id} already exists'
                }), 400

            if 'tables' not in config:
                config['tables'] = {}
            config['tables'][table_id] = table_data

            if 'metadata' not in config:
                config['metadata'] = {}
            config['metadata']['lastUpdated'] = datetime.now().isoformat()

            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)

            logger.info(f"Created table: {table_id}")

            return jsonify({
                'success': True,
                'message': f'Table {table_id} created successfully'
            }), 201

        except Exception as e:
            logger.error(f"Error creating table: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/database-config/tables/<table_id>', methods=['PUT'])
    @timing_aspect
    def update_table(table_id):
        """Update an existing table definition"""
        try:
            data = request.get_json()
            table_data = data.get('data')

            if not table_data:
                return jsonify({
                    'success': False,
                    'error': 'table data is required'
                }), 400

            config_path = 'app/config/database_query_config.json'
            with open(config_path, 'r') as f:
                config = json.load(f)

            if table_id not in config.get('tables', {}):
                return jsonify({
                    'success': False,
                    'error': f'Table {table_id} not found'
                }), 404

            config['tables'][table_id] = table_data

            if 'metadata' not in config:
                config['metadata'] = {}
            config['metadata']['lastUpdated'] = datetime.now().isoformat()

            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)

            logger.info(f"Updated table: {table_id}")

            return jsonify({
                'success': True,
                'message': f'Table {table_id} updated successfully'
            }), 200

        except Exception as e:
            logger.error(f"Error updating table: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/database-config/tables/<table_id>', methods=['DELETE'])
    @timing_aspect
    def delete_table(table_id):
        """Delete a table definition"""
        try:
            config_path = 'app/config/database_query_config.json'
            with open(config_path, 'r') as f:
                config = json.load(f)

            if table_id not in config.get('tables', {}):
                return jsonify({
                    'success': False,
                    'error': f'Table {table_id} not found'
                }), 404

            dependent_recipes = []
            for recipe_id, recipe_data in config.get('recipes', {}).items():
                if recipe_data.get('base') == table_id:
                    dependent_recipes.append(recipe_id)
                for join in recipe_data.get('joins', []):
                    if join.get('table') == table_id:
                        dependent_recipes.append(recipe_id)

            if dependent_recipes:
                return jsonify({
                    'success': False,
                    'error': f'Cannot delete table {table_id}: used by recipes {", ".join(set(dependent_recipes))}'
                }), 400

            del config['tables'][table_id]

            if 'metadata' not in config:
                config['metadata'] = {}
            config['metadata']['lastUpdated'] = datetime.now().isoformat()

            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)

            logger.info(f"Deleted table: {table_id}")

            return jsonify({
                'success': True,
                'message': f'Table {table_id} deleted successfully'
            }), 200

        except Exception as e:
            logger.error(f"Error deleting table: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    # ========== RECIPE CRUD ==========

    @app.route('/api/database-config/recipes', methods=['POST'])
    @timing_aspect
    def create_recipe():
        """Create a new query recipe"""
        try:
            data = request.get_json()
            recipe_id = data.get('id')
            recipe_data = data.get('data')

            if not recipe_id or not recipe_data:
                return jsonify({
                    'success': False,
                    'error': 'recipe id and data are required'
                }), 400

            config_path = 'app/config/database_query_config.json'
            with open(config_path, 'r') as f:
                config = json.load(f)

            if recipe_id in config.get('recipes', {}):
                return jsonify({
                    'success': False,
                    'error': f'Recipe {recipe_id} already exists'
                }), 400

            base_table = recipe_data.get('base')
            if base_table and base_table not in config.get('tables', {}):
                return jsonify({
                    'success': False,
                    'error': f'Base table {base_table} not found'
                }), 400

            if 'recipes' not in config:
                config['recipes'] = {}
            config['recipes'][recipe_id] = recipe_data

            if 'metadata' not in config:
                config['metadata'] = {}
            config['metadata']['lastUpdated'] = datetime.now().isoformat()

            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)

            logger.info(f"Created recipe: {recipe_id}")

            return jsonify({
                'success': True,
                'message': f'Recipe {recipe_id} created successfully'
            }), 201

        except Exception as e:
            logger.error(f"Error creating recipe: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/database-config/recipes/<recipe_id>', methods=['PUT'])
    @timing_aspect
    def update_recipe(recipe_id):
        """Update an existing query recipe"""
        try:
            data = request.get_json()
            recipe_data = data.get('data')

            if not recipe_data:
                return jsonify({
                    'success': False,
                    'error': 'recipe data is required'
                }), 400

            config_path = 'app/config/database_query_config.json'
            with open(config_path, 'r') as f:
                config = json.load(f)

            if recipe_id not in config.get('recipes', {}):
                return jsonify({
                    'success': False,
                    'error': f'Recipe {recipe_id} not found'
                }), 404

            base_table = recipe_data.get('base')
            if base_table and base_table not in config.get('tables', {}):
                return jsonify({
                    'success': False,
                    'error': f'Base table {base_table} not found'
                }), 400

            config['recipes'][recipe_id] = recipe_data

            if 'metadata' not in config:
                config['metadata'] = {}
            config['metadata']['lastUpdated'] = datetime.now().isoformat()

            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)

            logger.info(f"Updated recipe: {recipe_id}")

            return jsonify({
                'success': True,
                'message': f'Recipe {recipe_id} updated successfully'
            }), 200

        except Exception as e:
            logger.error(f"Error updating recipe: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/database-config/recipes/<recipe_id>', methods=['DELETE'])
    @timing_aspect
    def delete_recipe(recipe_id):
        """Delete a query recipe"""
        try:
            config_path = 'app/config/database_query_config.json'
            with open(config_path, 'r') as f:
                config = json.load(f)

            if recipe_id not in config.get('recipes', {}):
                return jsonify({
                    'success': False,
                    'error': f'Recipe {recipe_id} not found'
                }), 404

            dependent_modules = []
            for module_id, module_data in config.get('modules', {}).items():
                for intent_id, intent_data in module_data.get('intents', {}).items():
                    if intent_data.get('recipe') == recipe_id:
                        dependent_modules.append(f"{module_id}.{intent_id}")

            if dependent_modules:
                return jsonify({
                    'success': False,
                    'error': f'Cannot delete recipe {recipe_id}: used by module intents {", ".join(dependent_modules)}'
                }), 400

            del config['recipes'][recipe_id]

            if 'metadata' not in config:
                config['metadata'] = {}
            config['metadata']['lastUpdated'] = datetime.now().isoformat()

            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)

            logger.info(f"Deleted recipe: {recipe_id}")

            return jsonify({
                'success': True,
                'message': f'Recipe {recipe_id} deleted successfully'
            }), 200

        except Exception as e:
            logger.error(f"Error deleting recipe: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    # ========== QUERY API ROUTES ==========

    @app.route('/api/database-query/classify', methods=['POST'])
    @timing_aspect
    def classify_database_query():
        """Classify natural language query and generate plan"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'error': 'No JSON data provided'
                }), 400

            user_query = data.get('query', '')
            module_hint = data.get('module')

            if not user_query:
                return jsonify({
                    'success': False,
                    'error': 'Query text is required'
                }), 400

            from app.utils.query_generator import QueryGenerator
            try:
                qgen = QueryGenerator()
            except Exception as init_error:
                logger.error(f"Failed to initialize QueryGenerator: {init_error}")
                return jsonify({
                    'success': False,
                    'error': f'Configuration error: {str(init_error)}'
                }), 500

            try:
                plan = qgen.classify_user_query(user_query, module_hint)
            except Exception as classify_error:
                logger.error(f"Failed to classify query: {classify_error}")
                return jsonify({
                    'success': False,
                    'error': f'Classification error: {str(classify_error)}'
                }), 400

            try:
                recipe_info = qgen.get_recipe_info(plan['recipe_name'])
            except Exception as recipe_error:
                logger.warning(f"Failed to get recipe info: {recipe_error}")
                recipe_info = None

            return jsonify({
                'success': True,
                'plan': plan,
                'recipe': recipe_info
            }), 200

        except Exception as e:
            logger.error(f"Unexpected error in classify_database_query: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': f'Internal server error: {str(e)}'
            }), 500

    @app.route('/api/database-query/generate', methods=['POST'])
    @timing_aspect
    def generate_database_query():
        """Generate SQL query from recipe and filters"""
        try:
            data = request.get_json()
            recipe_name = data.get('recipe_name')
            filters = data.get('filters', [])
            tenant_id = data.get('tenant_id', 1)
            user_role = data.get('user_role', 'ops_analyst')
            limit = data.get('limit')
            offset = data.get('offset', 0)
            order_by = data.get('order_by')

            if not recipe_name:
                return jsonify({
                    'success': False,
                    'error': 'recipe_name is required'
                }), 400

            from app.utils.query_generator import QueryGenerator
            qgen = QueryGenerator()

            sql, params = qgen.generate_query(
                recipe_name=recipe_name,
                filters=filters,
                tenant_id=tenant_id,
                user_role=user_role,
                limit=limit,
                offset=offset,
                order_by=order_by
            )

            return jsonify({
                'success': True,
                'sql': sql,
                'parameters': params,
                'explanation': f"Generated query for recipe '{recipe_name}' with {len(filters)} filters"
            }), 200

        except Exception as e:
            logger.error(f"Error generating query: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/database-query/execute', methods=['POST'])
    @timing_aspect
    def execute_database_query():
        """Execute a generated query (read-only)"""
        try:
            data = request.get_json()
            sql = data.get('sql')
            parameters = data.get('parameters', {})

            if not sql:
                return jsonify({
                    'success': False,
                    'error': 'SQL query is required'
                }), 400

            # Mock data for now - in production, connect to actual database
            mock_results = [
                {
                    'lc_id': 1001,
                    'applicant_ref': 'LC-2025-001',
                    'currency': 'USD',
                    'amount': 250000.00,
                    'status': 'issued',
                    'issue_date': '2025-01-15',
                    'expiry_date': '2025-12-31',
                    'applicant_name': 'Emirates Steel Industries',
                    'applicant_country': 'AE',
                    'beneficiary_name': 'Global Trading Corp',
                    'beneficiary_country': 'US'
                },
                {
                    'lc_id': 1002,
                    'applicant_ref': 'LC-2025-002',
                    'currency': 'EUR',
                    'amount': 180000.00,
                    'status': 'approved',
                    'issue_date': '2025-02-01',
                    'expiry_date': '2025-11-30',
                    'applicant_name': 'Dubai Exports LLC',
                    'applicant_country': 'AE',
                    'beneficiary_name': 'European Import GmbH',
                    'beneficiary_country': 'DE'
                }
            ]

            return jsonify({
                'success': True,
                'results': mock_results,
                'row_count': len(mock_results),
                'execution_time_ms': 45
            }), 200

        except Exception as e:
            logger.error(f"Error executing query: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/database-query/generate-with-llm', methods=['POST'])
    @timing_aspect
    def generate_sql_with_llm_route():
        """Generate SQL query using LLM (OpenAI/Anthropic) from natural language"""
        try:
            data = request.get_json()
            user_query = data.get('query', '')
            schema_context = data.get('schema_context', '')
            provider = data.get('provider', 'openai')

            if not user_query:
                return jsonify({
                    'success': False,
                    'error': 'Query text is required'
                }), 400

            if provider == 'openai':
                api_key = os.getenv('OPENAI_API_KEY')
                if not api_key:
                    return jsonify({
                        'success': False,
                        'error': 'OpenAI API key not configured. Set OPENAI_API_KEY environment variable.'
                    }), 500
            elif provider == 'anthropic':
                api_key = os.getenv('ANTHROPIC_API_KEY')
                if not api_key:
                    return jsonify({
                        'success': False,
                        'error': 'Anthropic API key not configured. Set ANTHROPIC_API_KEY environment variable.'
                    }), 500
            else:
                return jsonify({
                    'success': False,
                    'error': f'Unknown provider: {provider}. Use "openai" or "anthropic"'
                }), 400

            # Load database schema for context
            from app.utils.query_generator import QueryGenerator
            try:
                qgen = QueryGenerator()
                if not schema_context:
                    schema_info = []
                    for table_id, table in qgen.tables.items():
                        columns = table.get('columns', [])
                        col_defs = [f"{col['name']} ({col['type']})" for col in columns]
                        schema_info.append(f"Table: {table_id}\n  Columns: {', '.join(col_defs)}")
                    schema_context = "\n\n".join(schema_info)
            except Exception as config_error:
                logger.warning(f"Could not load schema context: {config_error}")
                schema_context = "No schema information available"

            # Call LLM to generate SQL
            if provider == 'openai':
                sql_query = generate_sql_with_openai(user_query, schema_context, api_key)
            else:
                sql_query = generate_sql_with_anthropic(user_query, schema_context, api_key)

            return jsonify({
                'success': True,
                'sql': sql_query,
                'provider': provider,
                'explanation': f'SQL generated using {provider.upper()} from: "{user_query}"'
            }), 200

        except Exception as e:
            logger.error(f"Error generating SQL with LLM: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/database-config/generate-query-ai', methods=['POST'])
    @timing_aspect
    def generate_query_ai_route():
        """Generate SQL query recipe using AI from natural language description"""
        try:
            data = request.get_json()

            prompt = data.get('prompt', '').strip()
            module = data.get('module', '').strip()
            module_name = data.get('moduleName', '').strip()
            tables = data.get('tables', [])

            if not prompt or not module:
                return jsonify({
                    'success': False,
                    'error': 'Missing required fields: prompt and module'
                }), 400

            azure_key = os.getenv('AZURE_OPENAI_API_KEY')
            if not azure_key:
                return jsonify({
                    'success': False,
                    'error': 'Azure OpenAI API key not configured. Set AZURE_OPENAI_API_KEY environment variable.'
                }), 500

            deployment_name = os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-4o-mini')

            result = generate_query_recipe_with_ai(
                prompt=prompt,
                module=module,
                module_name=module_name,
                tables=tables,
                openai_client=openai_client,
                deployment_name=deployment_name
            )

            return jsonify({
                'success': True,
                'recipe': result.get('recipe', {}),
                'explanation': result.get('explanation', 'Query generated successfully')
            }), 200

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            return jsonify({
                'success': False,
                'error': f'Failed to parse AI response: {str(e)}'
            }), 500
        except Exception as e:
            logger.error(f"Error generating AI query: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    logger.info("✅ Database Configuration routes registered successfully")
    logger.info("   - Page route: /database_configuration")
    logger.info("   - Config APIs: /api/database-config/*")
    logger.info("   - Query APIs: /api/database-query/*")
