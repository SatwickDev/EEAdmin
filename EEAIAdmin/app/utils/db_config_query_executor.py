"""
Database Configuration Query Executor
Executes queries directly from database configuration recipes
Matches user queries to pre-built recipes and executes them
"""

import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from pymongo import MongoClient
import re

logger = logging.getLogger(__name__)


class DatabaseConfigQueryExecutor:
    """
    Executes queries using database configuration recipes
    Matches user intent to pre-configured query recipes
    """
    
    def __init__(self, config_path: str = 'app/config/database_query_config.json'):
        self.config_path = config_path
        self.config = self._load_config()
        self.modules = self.config.get('modules', {})
        self.tables = self.config.get('tables', {})
        self.recipes = self.config.get('recipes', {})
        
    def _load_config(self) -> Dict:
        """Load database configuration from JSON file"""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading database config: {e}")
            return {'modules': {}, 'tables': {}, 'recipes': {}}
    
    def reload_config(self):
        """Reload configuration from file"""
        self.config = self._load_config()
        self.modules = self.config.get('modules', {})
        self.tables = self.config.get('tables', {})
        self.recipes = self.config.get('recipes', {})
    
    def get_modules(self) -> List[Dict]:
        """Get all available modules"""
        modules_list = []
        for module_id, module_data in self.modules.items():
            modules_list.append({
                'id': module_id,
                'name': module_data.get('name'),
                'description': module_data.get('description'),
                'icon': module_data.get('icon'),
                'entry_tables': module_data.get('entry_tables', []),
                'created_at': module_data.get('created_at'),
                'updated_at': module_data.get('updated_at')
            })
        return modules_list
    
    def get_module_by_id(self, module_id: str) -> Optional[Dict]:
        """Get module details by ID"""
        return self.modules.get(module_id)
    
    def match_query_to_recipe(self, user_query: str, module_id: str = None) -> Optional[Dict]:
        """
        Match user query to a recipe using keyword matching
        
        Args:
            user_query: User's natural language query
            module_id: Optional module to filter recipes
            
        Returns:
            Best matching recipe or None
        """
        user_query_lower = user_query.lower()
        
        # Get recipes to search
        recipes_to_search = {}
        if module_id and module_id in self.modules:
            # Filter recipes by module
            module = self.modules[module_id]
            entry_tables = module.get('entry_tables', [])
            
            for recipe_id, recipe_data in self.recipes.items():
                if recipe_data.get('base') in entry_tables:
                    recipes_to_search[recipe_id] = recipe_data
        else:
            recipes_to_search = self.recipes
        
        best_match = None
        best_score = 0
        
        for recipe_id, recipe_data in recipes_to_search.items():
            score = 0
            
            # Check recipe name
            recipe_name = recipe_data.get('name', '').lower()
            if recipe_name in user_query_lower:
                score += 10
            
            # Check description
            description = recipe_data.get('description', '').lower()
            if description in user_query_lower:
                score += 5
            
            # Check keywords (if available)
            keywords = recipe_data.get('keywords', [])
            for keyword in keywords:
                if keyword.lower() in user_query_lower:
                    score += 3
            
            # Check intent patterns
            intent_patterns = recipe_data.get('intent_patterns', [])
            for pattern in intent_patterns:
                if re.search(pattern, user_query_lower, re.IGNORECASE):
                    score += 8
            
            # Check base table name
            base_table = recipe_data.get('base', '')
            if base_table:
                table_data = self.tables.get(base_table, {})
                table_name = table_data.get('name', '').lower()
                if table_name in user_query_lower:
                    score += 4
            
            if score > best_score:
                best_score = score
                best_match = {
                    'recipe_id': recipe_id,
                    'recipe': recipe_data,
                    'score': score
                }
        
        # Return match if score is significant enough
        if best_match and best_score >= 3:
            logger.info(f"Matched query to recipe '{best_match['recipe_id']}' with score {best_score}")
            return best_match
        
        logger.info(f"No recipe match found for query: {user_query}")
        return None
    
    def execute_recipe(self, recipe_id: str, filters: Dict = None, 
                       connection_string: str = None) -> Tuple[bool, Any]:
        """
        Execute a recipe query
        
        Args:
            recipe_id: Recipe identifier
            filters: Dynamic filter values (e.g., {'status': 'expired', 'limit': 10})
            connection_string: MongoDB connection string
            
        Returns:
            Tuple of (success: bool, result: Dict or error message)
        """
        try:
            recipe = self.recipes.get(recipe_id)
            if not recipe:
                return False, f"Recipe '{recipe_id}' not found"
            
            # Get base table
            base_table_id = recipe.get('base')
            base_table = self.tables.get(base_table_id)
            
            if not base_table:
                return False, f"Base table '{base_table_id}' not found"
            
            # Build MongoDB query
            query_result = self._build_and_execute_query(
                recipe, base_table, filters, connection_string
            )
            
            return True, query_result
            
        except Exception as e:
            logger.error(f"Error executing recipe '{recipe_id}': {e}")
            return False, str(e)
    
    def _build_and_execute_query(self, recipe: Dict, base_table: Dict, 
                                  filters: Dict, connection_string: str) -> Dict:
        """
        Build and execute MongoDB aggregation query from recipe
        
        Args:
            recipe: Recipe configuration
            base_table: Base table configuration
            filters: Dynamic filter values
            connection_string: MongoDB connection string
            
        Returns:
            Query results with metadata
        """
        try:
            # Get database connection info
            db_name = self.config.get('connection', {}).get('database', 'eeai_db')
            collection_name = base_table.get('collection', base_table.get('id'))
            
            # Connect to MongoDB
            if connection_string:
                client = MongoClient(connection_string)
            else:
                # Use default connection
                MONGO_URI = "mongodb://localhost:27017/"
                client = MongoClient(MONGO_URI)
            
            db = client[db_name]
            collection = db[collection_name]
            
            # Build aggregation pipeline
            pipeline = []
            
            # 1. Match stage (WHERE clause)
            match_stage = {}
            
            # Add static WHERE conditions from recipe
            where_conditions = recipe.get('where', [])
            for condition in where_conditions:
                # Parse condition like "status = 'active'" or "expiry_date < NOW()"
                parsed_condition = self._parse_where_condition(condition, filters)
                if parsed_condition:
                    match_stage.update(parsed_condition)
            
            # Add dynamic filters from user
            if filters:
                for field, value in filters.items():
                    if field not in ['limit', 'offset', 'sort_by', 'sort_order']:
                        match_stage[field] = value
            
            if match_stage:
                pipeline.append({"$match": match_stage})
            
            # 2. Joins (lookup stages)
            joins = recipe.get('joins', [])
            for join in joins:
                join_table_id = join.get('table')
                join_table = self.tables.get(join_table_id)
                
                if join_table:
                    local_field = join.get('on', '').split('=')[0].strip().split('.')[-1]
                    foreign_field = join.get('on', '').split('=')[1].strip().split('.')[-1]
                    
                    pipeline.append({
                        "$lookup": {
                            "from": join_table.get('collection', join_table_id),
                            "localField": local_field,
                            "foreignField": foreign_field,
                            "as": join.get('alias', join_table_id)
                        }
                    })
                    
                    # Unwind if needed
                    if join.get('type') == 'inner':
                        pipeline.append({
                            "$unwind": f"${join.get('alias', join_table_id)}"
                        })
            
            # 3. Project stage (SELECT clause)
            columns = recipe.get('columns', [])
            if columns and columns != ['*']:
                project_stage = {}
                for col in columns:
                    # Handle aliased columns like "table.field AS alias"
                    if ' AS ' in col.upper():
                        parts = col.split(' AS ')
                        field = parts[0].strip()
                        alias = parts[1].strip()
                        project_stage[alias] = f"${field}"
                    else:
                        # Simple field
                        field_name = col.split('.')[-1]
                        project_stage[field_name] = 1
                
                pipeline.append({"$project": project_stage})
            
            # 4. Sort stage
            sort_by = filters.get('sort_by') if filters else None
            sort_order = filters.get('sort_order', 'asc') if filters else 'asc'
            
            if sort_by:
                pipeline.append({
                    "$sort": {sort_by: 1 if sort_order == 'asc' else -1}
                })
            elif recipe.get('order_by'):
                # Use recipe's default sorting
                order_by = recipe.get('order_by', [])
                if order_by:
                    sort_stage = {}
                    for order_field in order_by:
                        if 'DESC' in order_field.upper():
                            field = order_field.replace('DESC', '').strip()
                            sort_stage[field] = -1
                        else:
                            field = order_field.replace('ASC', '').strip()
                            sort_stage[field] = 1
                    if sort_stage:
                        pipeline.append({"$sort": sort_stage})
            
            # 5. Limit stage
            limit = filters.get('limit') if filters else recipe.get('default_limit', 100)
            if limit:
                pipeline.append({"$limit": int(limit)})
            
            # Execute query
            logger.info(f"Executing MongoDB pipeline: {json.dumps(pipeline, indent=2)}")
            results = list(collection.aggregate(pipeline))
            
            # Convert ObjectId to string for JSON serialization
            for result in results:
                if '_id' in result:
                    result['_id'] = str(result['_id'])
            
            return {
                'success': True,
                'data': results,
                'count': len(results),
                'recipe_id': recipe.get('id'),
                'recipe_name': recipe.get('name'),
                'base_table': base_table.get('name'),
                'collection': collection_name,
                'query': {
                    'pipeline': pipeline,
                    'filters': filters
                }
            }
            
        except Exception as e:
            logger.error(f"Error building/executing query: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'data': []
            }
    
    def _parse_where_condition(self, condition: str, filters: Dict = None) -> Dict:
        """
        Parse WHERE condition into MongoDB query
        
        Examples:
            "status = 'expired'" -> {"status": "expired"}
            "amount > 1000" -> {"amount": {"$gt": 1000}}
            "expiry_date < NOW()" -> {"expiry_date": {"$lt": datetime.now()}}
        """
        try:
            condition = condition.strip()
            
            # Handle NOW() function
            if 'NOW()' in condition.upper():
                if '<' in condition:
                    field = condition.split('<')[0].strip()
                    return {field: {"$lt": datetime.now()}}
                elif '>' in condition:
                    field = condition.split('>')[0].strip()
                    return {field: {"$gt": datetime.now()}}
            
            # Handle comparison operators
            operators = {
                '>=': '$gte',
                '<=': '$lte',
                '!=': '$ne',
                '>': '$gt',
                '<': '$lt',
                '=': None  # Equality is default
            }
            
            for op_str, mongo_op in operators.items():
                if op_str in condition:
                    parts = condition.split(op_str)
                    if len(parts) == 2:
                        field = parts[0].strip()
                        value = parts[1].strip().strip("'\"")
                        
                        # Try to convert to number
                        try:
                            value = float(value) if '.' in value else int(value)
                        except ValueError:
                            pass
                        
                        if mongo_op:
                            return {field: {mongo_op: value}}
                        else:
                            return {field: value}
            
            return {}
            
        except Exception as e:
            logger.error(f"Error parsing WHERE condition '{condition}': {e}")
            return {}
    
    def get_recipe_suggestions(self, module_id: str = None) -> List[Dict]:
        """
        Get all available recipes as suggestions
        
        Args:
            module_id: Optional module to filter recipes
            
        Returns:
            List of recipe suggestions with example queries
        """
        suggestions = []
        
        recipes_to_show = self.recipes
        if module_id and module_id in self.modules:
            module = self.modules[module_id]
            entry_tables = module.get('entry_tables', [])
            recipes_to_show = {
                rid: rdata for rid, rdata in self.recipes.items()
                if rdata.get('base') in entry_tables
            }
        
        for recipe_id, recipe_data in recipes_to_show.items():
            base_table = self.tables.get(recipe_data.get('base'), {})
            
            suggestions.append({
                'recipe_id': recipe_id,
                'name': recipe_data.get('name'),
                'description': recipe_data.get('description'),
                'example_query': recipe_data.get('example_query', 
                                                  f"Show me {recipe_data.get('name', 'data')}"),
                'base_table': base_table.get('name', ''),
                'columns': recipe_data.get('columns', []),
                'filters': recipe_data.get('allowed_filters', [])
            })
        
        return suggestions


# Global instance
_executor = None

def get_db_config_executor() -> DatabaseConfigQueryExecutor:
    """Get or create global executor instance"""
    global _executor
    if _executor is None:
        _executor = DatabaseConfigQueryExecutor()
    return _executor
