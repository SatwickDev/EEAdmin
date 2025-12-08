"""
Database Configuration Module

Provides database configuration management, query generation, and LLM-based SQL creation.

Components:
- database_config_routes.py: Flask routes for database configuration
- llm_query_generator.py: LLM-based SQL query generation helpers

Endpoints:
    Page Routes:
        GET  /database_configuration                    - Configuration page

    Config API Routes:
        GET  /api/database-config                       - Get full configuration
        POST /api/database-config/save                  - Save configuration
        POST /api/database-config/validate              - Validate configuration

    Module CRUD:
        GET  /api/database-config/modules               - List all modules
        GET  /api/database-config/modules/<id>          - Get module details
        POST /api/database-config/modules               - Create module
        PUT  /api/database-config/modules/<id>          - Update module
        DELETE /api/database-config/modules/<id>        - Delete module

    Table CRUD:
        GET  /api/database-config/tables                - List all tables
        POST /api/database-config/tables                - Create table
        PUT  /api/database-config/tables/<id>           - Update table
        DELETE /api/database-config/tables/<id>         - Delete table

    Recipe CRUD:
        GET  /api/database-config/recipes               - List all recipes
        GET  /api/database-config/recipes/<id>          - Get recipe details
        POST /api/database-config/recipes               - Create recipe
        PUT  /api/database-config/recipes/<id>          - Update recipe
        DELETE /api/database-config/recipes/<id>        - Delete recipe

    Query API Routes:
        POST /api/database-query/classify               - Classify natural language query
        POST /api/database-query/generate               - Generate SQL from recipe
        POST /api/database-query/execute                - Execute query (read-only)
        POST /api/database-query/generate-with-llm      - Generate SQL with LLM
        POST /api/database-config/generate-query-ai     - Generate recipe with AI

Author: Trade Finance AI Team
Version: 1.0.0
"""

from .database_config_routes import register_database_config_routes
from .repository_module_routes import register_repository_module_routes

__all__ = ['register_database_config_routes', 'register_repository_module_routes']
