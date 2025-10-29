"""
Safe Query Generator for Trade Finance Database
Implements secure, parameterized query generation with RBAC, allowlist validation, and AST checking.
"""

import json
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, date
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class QueryGenerationError(Exception):
    """Raised when query generation fails validation"""
    pass


class QueryGenerator:
    """
    Secure query generator that enforces:
    - Allowlist-only tables/columns/operations
    - Parameterized queries (no SQL injection)
    - RBAC-based column masking
    - Tenant isolation
    - Query budget limits
    """
    
    def __init__(self, config_path: str = 'app/config/database_query_config.json'):
        """Initialize with configuration"""
        self.config = self._load_config(config_path)
        self.modules = self.config.get('modules', {})
        self.entities = self.config.get('entities', {})
        self.tables = self.config.get('tables', {})
        self.recipes = self.config.get('recipes', {})
        self.roles = self.config.get('rbac_roles', {})
        self.query_settings = self.config.get('query_settings', {})
        
    def _load_config(self, path: str) -> Dict:
        """Load configuration from JSON file"""
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Config file not found: {path}")
            raise QueryGenerationError(f"Configuration file not found: {path}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config: {e}")
            raise QueryGenerationError(f"Invalid configuration JSON: {e}")
    
    def classify_user_query(self, user_query: str, module_hint: Optional[str] = None) -> Dict[str, Any]:
        """
        Classify user's natural language query to determine module and intent.
        Returns a plan with recipe, filters, and parameters.
        
        This is a simplified version - in production, you'd use an LLM with constrained output.
        """
        user_query_lower = user_query.lower()
        
        # Simple keyword-based classification (replace with LLM in production)
        plan = {
            'module': None,
            'intent': None,
            'recipe_name': None,
            'filters': [],
            'order_by': None,
            'limit': self.query_settings.get('default_limit', 100)
        }
        
        # Detect module
        if any(kw in user_query_lower for kw in ['lc', 'letter of credit', 'documentary credit']):
            plan['module'] = 'letters_of_credit'
        elif any(kw in user_query_lower for kw in ['guarantee', 'sblc', 'standby']):
            plan['module'] = 'guarantees'
        elif any(kw in user_query_lower for kw in ['collection', 'documentary collection']):
            plan['module'] = 'collections'
        elif any(kw in user_query_lower for kw in ['finance', 'financing', 'loan']):
            plan['module'] = 'trade_finance'
        
        if module_hint:
            plan['module'] = module_hint
            
        if not plan['module']:
            raise QueryGenerationError("Could not determine module from query. Please specify module explicitly.")
        
        module = self.modules.get(plan['module'])
        if not module:
            raise QueryGenerationError(f"Unknown module: {plan['module']}")
        
        # Detect intent
        if any(kw in user_query_lower for kw in ['pending', 'not issued', 'awaiting']):
            plan['intent'] = 'list_pending'
        elif any(kw in user_query_lower for kw in ['expiring', 'expire', 'expiration']):
            plan['intent'] = 'list_expiring'
        elif any(kw in user_query_lower for kw in ['detail', 'full', 'complete', 'show all']):
            plan['intent'] = 'detail_by_number'
        elif any(kw in user_query_lower for kw in ['amendment', 'amend', 'change']):
            plan['intent'] = 'amendments_history'
        elif any(kw in user_query_lower for kw in ['active', 'current']):
            plan['intent'] = 'list_active'
        else:
            # Default to list_pending for the module
            intents = module.get('intents', {})
            if 'list_pending' in intents:
                plan['intent'] = 'list_pending'
            elif 'list_active' in intents:
                plan['intent'] = 'list_active'
            else:
                plan['intent'] = list(intents.keys())[0] if intents else None
        
        if not plan['intent']:
            raise QueryGenerationError(f"Could not determine intent for module {plan['module']}")
        
        # Get recipe
        intent_config = module['intents'].get(plan['intent'])
        if not intent_config:
            raise QueryGenerationError(f"Unknown intent '{plan['intent']}' for module '{plan['module']}'")
        
        plan['recipe_name'] = intent_config['recipe']
        
        # Extract filters from query (simplified - use NER/LLM in production)
        plan['filters'] = self._extract_filters_from_query(user_query, plan['recipe_name'])
        
        return plan
    
    def _extract_filters_from_query(self, query: str, recipe_name: str) -> List[Dict]:
        """
        Extract filter conditions from natural language query.
        This is a simplified regex-based implementation.
        In production, use NER or LLM with structured output.
        """
        filters = []
        recipe = self.recipes.get(recipe_name, {})
        allowed_filters = {f['field']: f for f in recipe.get('allowed_filters', [])}
        
        # Extract company names (applicant/beneficiary)
        # Pattern: "for <company name>"
        company_pattern = r'for\s+([A-Z][A-Za-z0-9\s&]+?)(?:\s+in|\s+this|\s+last|$)'
        companies = re.findall(company_pattern, query, re.IGNORECASE)
        for company in companies:
            company = company.strip()
            # Try to match to applicant or beneficiary
            if 'applicant.name' in allowed_filters:
                filters.append({
                    'field': 'applicant.name',
                    'op': 'ILIKE',
                    'value': f'%{company}%'
                })
        
        # Extract date ranges
        # Pattern: "this quarter", "last 30 days", etc.
        if 'this quarter' in query.lower():
            start_date, end_date = self._get_current_quarter()
            for field, config in allowed_filters.items():
                if config['type'] == 'date':
                    filters.append({
                        'field': field,
                        'op': 'BETWEEN',
                        'value': [start_date.isoformat(), end_date.isoformat()]
                    })
                    break
        
        # Extract currency
        currency_pattern = r'\b([A-Z]{3})\b'
        currencies = re.findall(currency_pattern, query)
        for curr in currencies:
            if curr in ['USD', 'EUR', 'GBP', 'JPY', 'AED', 'SAR', 'KWD']:
                for field, config in allowed_filters.items():
                    if 'currency' in field.lower():
                        filters.append({
                            'field': field,
                            'op': '=',
                            'value': curr
                        })
                        break
        
        # Extract countries
        country_pattern = r'\bin\s+([A-Z]{2}|[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
        countries = re.findall(country_pattern, query)
        for country in countries:
            country = country.strip()
            if len(country) == 2:  # ISO code
                for field, config in allowed_filters.items():
                    if 'country' in field.lower():
                        filters.append({
                            'field': field,
                            'op': '=',
                            'value': country.upper()
                        })
                        break
        
        return filters
    
    def _get_current_quarter(self) -> Tuple[date, date]:
        """Get start and end dates of current quarter"""
        today = date.today()
        quarter = (today.month - 1) // 3 + 1
        start_month = (quarter - 1) * 3 + 1
        end_month = quarter * 3
        
        start_date = date(today.year, start_month, 1)
        
        if end_month == 12:
            end_date = date(today.year, 12, 31)
        else:
            from calendar import monthrange
            end_date = date(today.year, end_month, monthrange(today.year, end_month)[1])
        
        return start_date, end_date
    
    def generate_query(
        self,
        recipe_name: str,
        filters: List[Dict[str, Any]],
        tenant_id: int,
        user_role: str = 'ops_analyst',
        limit: Optional[int] = None,
        offset: int = 0,
        order_by: Optional[str] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Generate a safe, parameterized SQL query from recipe and filters.
        
        Returns:
            Tuple of (sql_query, parameters_dict)
        """
        recipe = self.recipes.get(recipe_name)
        if not recipe:
            raise QueryGenerationError(f"Unknown recipe: {recipe_name}")
        
        # Validate and compile filters
        validated_filters, params = self._validate_and_compile_filters(
            filters, recipe, tenant_id, user_role
        )
        
        # Get allowed columns based on RBAC
        select_columns = self._get_rbac_columns(recipe, user_role)
        
        # Build joins
        join_clauses = self._build_joins(recipe)
        
        # Build WHERE clause
        where_clauses = recipe.get('where', []).copy()
        where_clauses.extend(validated_filters)
        
        # Build ORDER BY
        if order_by:
            order_by_clause = self._validate_order_by(order_by, recipe)
        else:
            order_by_clause = ', '.join(recipe.get('order_by', ['1']))
        
        # Build LIMIT/OFFSET
        max_limit = self.query_settings.get('max_limit', 500)
        default_limit = recipe.get('default_limit', self.query_settings.get('default_limit', 100))
        final_limit = min(limit or default_limit, max_limit)
        
        params['limit'] = final_limit
        params['offset'] = offset
        
        # Assemble query
        base_table = recipe['base']
        base_alias = 't0'
        
        sql_parts = [
            "WITH base AS (",
            f"  SELECT {', '.join(select_columns)}",
            f"  FROM {base_table} {base_alias}"
        ]
        
        # Add joins
        sql_parts.extend(join_clauses)
        
        # Add WHERE
        if where_clauses:
            sql_parts.append(f"  WHERE {' AND '.join(where_clauses)}")
        
        sql_parts.extend([
            ")",
            "SELECT * FROM base",
            f"ORDER BY {order_by_clause}",
            "LIMIT :limit OFFSET :offset"
        ])
        
        sql = '\n'.join(sql_parts)
        
        # Final validation
        self._validate_sql_ast(sql)
        
        return sql, params
    
    def _validate_and_compile_filters(
        self,
        filters: List[Dict[str, Any]],
        recipe: Dict,
        tenant_id: int,
        user_role: str
    ) -> Tuple[List[str], Dict[str, Any]]:
        """
        Validate filters against allowlist and compile to SQL WHERE clauses.
        Returns (where_clause_list, parameters_dict)
        """
        allowed_filters = {f['field']: f for f in recipe.get('allowed_filters', [])}
        where_clauses = []
        params = {'tenant_id': tenant_id}
        param_counter = 0
        
        for filter_spec in filters:
            field = filter_spec.get('field')
            op = filter_spec.get('op')
            value = filter_spec.get('value')
            
            # Validate field is allowed
            if field not in allowed_filters:
                logger.warning(f"Ignoring disallowed filter field: {field}")
                continue
            
            allowed_filter = allowed_filters[field]
            
            # Validate operation
            if op not in allowed_filter.get('ops', []):
                logger.warning(f"Ignoring disallowed operation {op} for field {field}")
                continue
            
            # Type-check and convert value
            try:
                typed_value = self._typecheck_value(value, allowed_filter['type'])
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid value type for {field}: {e}")
                continue
            
            # Generate parameter name
            param_name = f"filter_{param_counter}"
            param_counter += 1
            
            # Build WHERE clause based on operation
            if op == '=':
                where_clauses.append(f"{field} = :{param_name}")
                params[param_name] = typed_value
            elif op == 'ILIKE':
                where_clauses.append(f"{field} ILIKE :{param_name}")
                params[param_name] = typed_value
            elif op == 'IN':
                # For IN, value should be a list
                if not isinstance(typed_value, list):
                    typed_value = [typed_value]
                placeholders = ', '.join([f":{param_name}_{i}" for i in range(len(typed_value))])
                where_clauses.append(f"{field} IN ({placeholders})")
                for i, v in enumerate(typed_value):
                    params[f"{param_name}_{i}"] = v
            elif op in ['>=', '<=', '>','<']:
                where_clauses.append(f"{field} {op} :{param_name}")
                params[param_name] = typed_value
            elif op == 'BETWEEN':
                # For BETWEEN, value should be [start, end]
                if not isinstance(typed_value, list) or len(typed_value) != 2:
                    logger.warning(f"BETWEEN requires [start, end] values")
                    continue
                where_clauses.append(f"{field} BETWEEN :{param_name}_start AND :{param_name}_end")
                params[f"{param_name}_start"] = typed_value[0]
                params[f"{param_name}_end"] = typed_value[1]
        
        return where_clauses, params
    
    def _typecheck_value(self, value: Any, expected_type: str) -> Any:
        """Type-check and convert value to expected type"""
        if expected_type == 'string':
            return str(value)
        elif expected_type == 'integer':
            return int(value)
        elif expected_type == 'decimal':
            return Decimal(str(value))
        elif expected_type == 'date':
            if isinstance(value, str):
                # Parse ISO date
                return datetime.fromisoformat(value).date()
            elif isinstance(value, date):
                return value
            elif isinstance(value, list):
                # For BETWEEN operations
                return [self._typecheck_value(v, 'date') for v in value]
            else:
                raise ValueError(f"Cannot convert {value} to date")
        elif expected_type == 'boolean':
            if isinstance(value, bool):
                return value
            return value.lower() in ['true', '1', 'yes']
        else:
            return value
    
    def _get_rbac_columns(self, recipe: Dict, user_role: str) -> List[str]:
        """
        Get allowed columns for SELECT based on RBAC rules.
        Apply masking for sensitive columns.
        """
        base_table_name = recipe['base']
        base_table = self.tables.get(base_table_name, {})
        select_fields = recipe.get('select', [])
        
        # Get masked columns for this role
        rbac = base_table.get('rbac', {})
        masked_columns = rbac.get('masked_columns', [])
        
        role_masks = {}
        for mask_rule in masked_columns:
            column = mask_rule['column']
            for_roles = mask_rule.get('for_roles', [])
            mask_type = mask_rule.get('mask_type', 'redact')
            
            if user_role in for_roles:
                role_masks[column] = mask_type
        
        # Apply masking to select fields
        masked_selects = []
        for field in select_fields:
            # Parse field (handle "table.column as alias")
            field_parts = field.split(' as ')
            column_expr = field_parts[0].strip()
            alias = field_parts[1].strip() if len(field_parts) > 1 else None
            
            # Check if column needs masking
            column_name = column_expr.split('.')[-1]  # Get column name without table prefix
            
            if column_name in role_masks:
                mask_type = role_masks[column_name]
                if mask_type == 'redact':
                    masked_expr = "'[REDACTED]'"
                elif mask_type == 'hash':
                    masked_expr = f"MD5({column_expr})"
                elif mask_type == 'partial':
                    # Show only first 4 characters
                    masked_expr = f"CONCAT(SUBSTRING({column_expr}, 1, 4), '****')"
                else:
                    masked_expr = 'NULL'
                
                if alias:
                    masked_selects.append(f"{masked_expr} as {alias}")
                else:
                    masked_selects.append(f"{masked_expr} as {column_name}")
            else:
                masked_selects.append(field)
        
        return masked_selects
    
    def _build_joins(self, recipe: Dict) -> List[str]:
        """Build JOIN clauses from recipe"""
        joins = []
        for join_spec in recipe.get('joins', []):
            join_type = join_spec.get('type', 'INNER').upper()
            
            # Parse from/to
            from_parts = join_spec['from'].split('.')
            to_parts = join_spec['to'].split('.')
            
            from_table = from_parts[0]
            from_column = from_parts[1]
            to_table = to_parts[0]
            to_column = to_parts[1]
            alias = join_spec.get('alias', to_table)
            
            # Validate tables exist in config
            if to_table not in self.tables:
                raise QueryGenerationError(f"Unknown table in join: {to_table}")
            
            joins.append(
                f"  {join_type} JOIN {to_table} {alias} "
                f"ON {from_table}.{from_column} = {alias}.{to_column}"
            )
        
        return joins
    
    def _validate_order_by(self, order_by: str, recipe: Dict) -> str:
        """Validate ORDER BY clause against allowlist"""
        # Extract column names from order_by
        # Simple validation: ensure it's in the select list or allowed_filters
        allowed_fields = set()
        for field in recipe.get('select', []):
            # Extract column name/alias
            if ' as ' in field:
                alias = field.split(' as ')[1].strip()
                allowed_fields.add(alias)
            else:
                allowed_fields.add(field.strip())
        
        for filter_spec in recipe.get('allowed_filters', []):
            allowed_fields.add(filter_spec['field'])
        
        # Check if order_by field is allowed
        order_field = order_by.split()[0].strip()  # Handle "field ASC/DESC"
        
        if order_field not in allowed_fields:
            logger.warning(f"Order by field {order_field} not in allowlist, using default")
            return ', '.join(recipe.get('order_by', ['1']))
        
        return order_by
    
    def _validate_sql_ast(self, sql: str):
        """
        Validate SQL AST to ensure no dangerous operations.
        This is a basic check - in production, use sqlglot or moz-sql-parser.
        """
        sql_upper = sql.upper()
        
        # Check for disallowed operations
        disallowed = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER', 
                      'EXEC', 'EXECUTE', 'xp_cmdshell', 'sp_executesql']
        
        for keyword in disallowed:
            if keyword in sql_upper:
                raise QueryGenerationError(f"Disallowed SQL operation: {keyword}")
        
        # Ensure it starts with WITH or SELECT
        if not (sql_upper.strip().startswith('WITH') or sql_upper.strip().startswith('SELECT')):
            raise QueryGenerationError("Query must start with WITH or SELECT")
        
        return True
    
    def execute_query(self, sql: str, params: Dict[str, Any], db_connection) -> List[Dict]:
        """
        Execute query with timeout and result set limits.
        
        Args:
            sql: Parameterized SQL query
            params: Query parameters
            db_connection: Database connection (e.g., SQLAlchemy engine or pymongo)
        
        Returns:
            List of result dictionaries
        """
        timeout = self.query_settings.get('statement_timeout_seconds', 30)
        
        try:
            # Set statement timeout (PostgreSQL example)
            # For other DBs, adjust accordingly
            db_connection.execute(f"SET statement_timeout = {timeout * 1000}")  # milliseconds
            
            # Execute query
            result = db_connection.execute(sql, params)
            rows = result.fetchall()
            
            # Convert to list of dicts
            columns = result.keys()
            data = [dict(zip(columns, row)) for row in rows]
            
            # Log query execution
            if self.query_settings.get('log_all_queries', True):
                logger.info(f"Executed query: {sql[:200]}... | Rows: {len(data)} | Params: {self._redact_params(params)}")
            
            return data
            
        except Exception as e:
            logger.error(f"Query execution error: {e}")
            raise QueryGenerationError(f"Query execution failed: {e}")
    
    def _redact_params(self, params: Dict) -> Dict:
        """Redact sensitive parameter values for logging"""
        redacted = params.copy()
        # Don't log full names, keep only tenant_id and filter types
        for key in list(redacted.keys()):
            if key not in ['tenant_id', 'limit', 'offset']:
                redacted[key] = '***'
        return redacted
    
    def get_available_modules(self) -> List[Dict]:
        """Get list of available modules for UI"""
        return [
            {
                'id': mod_id,
                'name': mod_data['name'],
                'description': mod_data['description'],
                'icon': mod_data.get('icon', 'mdi-table'),
                'intents': list(mod_data.get('intents', {}).keys())
            }
            for mod_id, mod_data in self.modules.items()
        ]
    
    def get_module_intents(self, module_id: str) -> List[Dict]:
        """Get available intents for a module"""
        module = self.modules.get(module_id)
        if not module:
            return []
        
        return [
            {
                'id': intent_id,
                'description': intent_data['description'],
                'recipe': intent_data['recipe']
            }
            for intent_id, intent_data in module.get('intents', {}).items()
        ]
    
    def get_recipe_info(self, recipe_id: str) -> Dict:
        """Get detailed information about a recipe including allowed filters"""
        recipe = self.recipes.get(recipe_id)
        if not recipe:
            return {}
        
        return {
            'id': recipe_id,
            'name': recipe.get('name', recipe_id),
            'description': recipe.get('description', ''),
            'module': recipe.get('module', ''),
            'allowed_filters': recipe.get('allowed_filters', []),
            'select_fields': recipe.get('select', []),
            'default_limit': recipe.get('default_limit', 100)
        }
