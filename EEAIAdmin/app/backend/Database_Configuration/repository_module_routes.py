"""
Repository and Module Management Routes
Contains routes for managing user connections to repositories and database modules
"""

from flask import request, jsonify, session


def register_repository_module_routes(app, logger, active_user_repositories, active_user_modules, get_chromadb_client):
    """
    Register repository and module management routes
    
    Args:
        app: Flask application instance
        logger: Logger instance
        active_user_repositories: Dict tracking active user repository connections
        active_user_modules: Dict tracking active user module connections
        get_chromadb_client: Function to get ChromaDB client
    """

    # =============================================
    # REPOSITORY API ENDPOINTS
    # =============================================

    @app.route('/api/repositories', methods=['GET'])
    def get_repositories():
        """Get all available repositories for the chatbot"""
        try:
            user_id = request.args.get('user_id', 'default_user')

            # Define available repositories
            repositories = [
                {
                    'id': 'trade_finance_repo',
                    'name': 'Trade Finance Repository',
                    'type': 'trade_finance',
                    'description': 'Repository for Letters of Credit, Bank Guarantees, and Export Documentation',
                    'icon': 'fa-file-invoice-dollar',
                    'collections': [
                        {'name': 'Letters of Credit', 'count': 245, 'status': 'active'},
                        {'name': 'Bank Guarantees', 'count': 189, 'status': 'active'},
                        {'name': 'Export Documents', 'count': 312, 'status': 'active'},
                        {'name': 'SWIFT Messages', 'count': 567, 'status': 'active'}
                    ],
                    'total_documents': 1313,
                    'status': 'active'
                },
                {
                    'id': 'treasury_repo',
                    'name': 'Treasury Repository',
                    'type': 'treasury',
                    'description': 'Repository for treasury operations and FX management',
                    'icon': 'fa-chart-line',
                    'collections': [
                        {'name': 'FX Hedging', 'count': 158, 'status': 'active'},
                        {'name': 'Interest Rate Swaps', 'count': 124, 'status': 'active'},
                        {'name': 'Treasury Policies', 'count': 67, 'status': 'active'},
                        {'name': 'Risk Management', 'count': 203, 'status': 'active'}
                    ],
                    'total_documents': 552,
                    'status': 'active'
                },
                {
                    'id': 'cash_mgmt_repo',
                    'name': 'Cash Management Repository',
                    'type': 'cash_management',
                    'description': 'Repository for cash management and liquidity optimization',
                    'icon': 'fa-money-bill-wave',
                    'collections': [
                        {'name': 'Cash Pooling', 'count': 89, 'status': 'active'},
                        {'name': 'Working Capital', 'count': 142, 'status': 'active'},
                        {'name': 'Payment Processing', 'count': 176, 'status': 'active'},
                        {'name': 'Liquidity Management', 'count': 95, 'status': 'active'}
                    ],
                    'total_documents': 502,
                    'status': 'active'
                }
            ]

            # Check if user has an active repository
            active_repo = active_user_repositories.get(user_id)

            return jsonify({
                'success': True,
                'repositories': repositories,
                'active_repository': active_repo,
                'user_id': user_id
            }), 200

        except Exception as e:
            logger.error(f"Error fetching repositories: {e}")
            return jsonify({
                'success': False,
                'error': str(e),
                'repositories': []
            }), 500

    @app.route('/api/repositories/active', methods=['GET', 'POST'])
    def manage_active_repository():
        """Get or set the active repository for a user"""

        if request.method == 'GET':
            # Get current active repository
            user_id = request.args.get('user_id', 'default_user')
            active_repo = active_user_repositories.get(user_id)

            return jsonify({
                'success': True,
                'active_repository': active_repo,
                'user_id': user_id
            }), 200

        elif request.method == 'POST':
            # Set active repository
            try:
                data = request.get_json()
                active_repo = data.get('active_repository')
                user_id = data.get('user_id', 'default_user')

                if active_repo:
                    active_user_repositories[user_id] = active_repo
                    logger.info(f"User {user_id} connected to repository: {active_repo}")
                else:
                    # Disconnect - remove user from active repositories
                    if user_id in active_user_repositories:
                        del active_user_repositories[user_id]
                        logger.info(f"User {user_id} disconnected from all repositories")

                return jsonify({
                    'success': True,
                    'active_repository': active_repo,
                    'message': f'Repository state updated: {active_repo or "disconnected"}'
                }), 200

            except Exception as e:
                logger.error(f"Error setting active repository: {e}")
                return jsonify({"error": str(e)}), 500

    @app.route('/api/repositories/<repo_id>/connect', methods=['POST'])
    def connect_repository(repo_id):
        """Connect user to a repository"""
        try:
            data = request.get_json() or {}
            user_id = data.get('user_id', 'default_user')

            # Map repository ID to name for the active_user_repositories
            repo_mapping = {
                'trade_finance_repo': 'Trade Finance Repository',
                'treasury_repo': 'Treasury Repository',
                'cash_mgmt_repo': 'Cash Management Repository'
            }

            repo_name = repo_mapping.get(repo_id)
            if not repo_name:
                return jsonify({
                    'success': False,
                    'error': 'Invalid repository ID'
                }), 400

            # Set as active repository
            active_user_repositories[user_id] = repo_name
            logger.info(f"User {user_id} connected to repository: {repo_name}")

            return jsonify({
                'success': True,
                'message': f'Connected to {repo_name}',
                'active_repository': repo_name
            }), 200

        except Exception as e:
            logger.error(f"Error connecting to repository: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/repositories/<repo_id>/disconnect', methods=['POST'])
    def disconnect_repository(repo_id):
        """Disconnect user from a repository"""
        try:
            data = request.get_json() or {}
            user_id = data.get('user_id', 'default_user')

            # Remove from active repositories
            if user_id in active_user_repositories:
                repo_name = active_user_repositories[user_id]
                del active_user_repositories[user_id]
                logger.info(f"User {user_id} disconnected from repository: {repo_name}")

                return jsonify({
                    'success': True,
                    'message': f'Disconnected from {repo_name}'
                }), 200
            else:
                return jsonify({
                    'success': True,
                    'message': 'No active repository connection'
                }), 200

        except Exception as e:
            logger.error(f"Error disconnecting from repository: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/repositories/<repo_name>/collections', methods=['GET'])
    def get_repository_collections(repo_name):
        """Get collections for a specific repository"""
        try:
            import chromadb

            # Map repository names to ChromaDB collections
            repo_mappings = {
                'trade_finance': ['trade_finance_records', 'letter_of_credit', 'bank_guarantees',
                                  'export_documents', 'import_documents', 'ucp600_rules',
                                  'swift_rules', 'urdg758_rules'],
                'treasury': ['forex_transactions', 'money_market', 'derivatives',
                             'investments', 'hedging_instruments'],
                'cash': ['cash_transactions', 'liquidity_reports', 'cash_forecasts',
                         'payment_orders', 'cash_pooling']
            }

            if repo_name not in repo_mappings:
                return jsonify({"error": "Invalid repository name"}), 400

            try:
                # Connect to ChromaDB
                client = get_chromadb_client(host="localhost", port=8000)

                # Get all collections
                all_collections = client.list_collections()
                collection_names = [col.name for col in all_collections]

                # Filter collections for this repository
                repo_collections = []
                for collection_name in repo_mappings[repo_name]:
                    if collection_name in collection_names:
                        # Get collection to fetch count
                        collection = client.get_collection(collection_name)
                        count = collection.count()

                        repo_collections.append({
                            'name': collection_name,
                            'count': count,
                            'type': 'chromadb',
                            'status': 'active'
                        })
                    else:
                        # Collection doesn't exist yet
                        repo_collections.append({
                            'name': collection_name,
                            'count': 0,
                            'type': 'chromadb',
                            'status': 'not_created'
                        })

                return jsonify({
                    'success': True,
                    'repository': repo_name,
                    'collections': repo_collections,
                    'total_collections': len(repo_collections)
                }), 200

            except Exception as e:
                logger.error(f"Error connecting to ChromaDB: {e}")
                return jsonify({
                    'success': False,
                    'error': 'Failed to connect to ChromaDB',
                    'details': str(e)
                }), 500

        except Exception as e:
            logger.error(f"Error getting repository collections: {e}")
            return jsonify({"error": str(e)}), 500

    # =============================================
    # MODULE API ENDPOINTS (Database Configuration Based)
    # =============================================

    @app.route('/api/modules', methods=['GET'])
    def get_user_modules():
        """Get all available modules from database configuration"""
        try:
            user_id = request.args.get('user_id', 'default_user')

            from app.utils.db_config_query_executor import get_db_config_executor
            executor = get_db_config_executor()

            # Get modules from database configuration
            modules = executor.get_modules()

            # Check if user has an active module
            active_module = active_user_modules.get(user_id)

            # Add connection status and recipe count to each module
            for module in modules:
                module['connected'] = (module['id'] == active_module) if active_module else False

                # Count recipes for this module
                module_recipes = [
                    recipe for recipe_id, recipe in executor.recipes.items()
                    if recipe.get('base') in module.get('entry_tables', [])
                ]
                module['recipe_count'] = len(module_recipes)

            return jsonify({
                'success': True,
                'modules': modules,
                'active_module': active_module,
                'user_id': user_id
            }), 200

        except Exception as e:
            logger.error(f"Error fetching modules: {e}")
            return jsonify({
                'success': False,
                'error': str(e),
                'modules': []
            }), 500

    @app.route('/api/modules/<module_id>/connect', methods=['POST'])
    def connect_module(module_id):
        """Connect user to a module"""
        try:
            data = request.get_json() or {}
            user_id = data.get('user_id', 'default_user')

            from app.utils.db_config_query_executor import get_db_config_executor
            executor = get_db_config_executor()

            # Verify module exists
            module = executor.get_module_by_id(module_id)
            if not module:
                return jsonify({
                    'success': False,
                    'error': f'Module not found: {module_id}'
                }), 404

            # Set as active module
            active_user_modules[user_id] = module_id
            # Also update the old repository structure for backward compatibility
            active_user_repositories[user_id] = module.get('name')

            logger.info(f"User {user_id} connected to module: {module.get('name')}")

            return jsonify({
                'success': True,
                'message': f"Connected to {module.get('name')}",
                'active_module': module_id,
                'module_name': module.get('name')
            }), 200

        except Exception as e:
            logger.error(f"Error connecting to module: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/modules/<module_id>/disconnect', methods=['POST'])
    def disconnect_module(module_id):
        """Disconnect user from a module"""
        try:
            data = request.get_json() or {}
            user_id = data.get('user_id', 'default_user')

            # Remove from active modules
            if user_id in active_user_modules:
                module_id_removed = active_user_modules[user_id]
                del active_user_modules[user_id]

                # Also remove from old repository structure
                if user_id in active_user_repositories:
                    del active_user_repositories[user_id]

                logger.info(f"User {user_id} disconnected from module: {module_id_removed}")

                return jsonify({
                    'success': True,
                    'message': 'Module disconnected'
                }), 200
            else:
                return jsonify({
                    'success': True,
                    'message': 'No active module connection'
                }), 200

        except Exception as e:
            logger.error(f"Error disconnecting from module: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/modules/<module_id>/recipes', methods=['GET'])
    def get_module_recipes(module_id):
        """Get available recipes for a specific module"""
        try:
            from app.utils.db_config_query_executor import get_db_config_executor
            executor = get_db_config_executor()

            # Verify module exists
            module = executor.get_module_by_id(module_id)
            if not module:
                return jsonify({
                    'success': False,
                    'error': f'Module not found: {module_id}'
                }), 404

            # Get recipe suggestions for this module
            suggestions = executor.get_recipe_suggestions(module_id)

            return jsonify({
                'success': True,
                'module_id': module_id,
                'module_name': module.get('name'),
                'recipes': suggestions,
                'total_recipes': len(suggestions)
            }), 200

        except Exception as e:
            logger.error(f"Error getting module recipes: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    logger.info("Repository and Module management routes registered successfully")
