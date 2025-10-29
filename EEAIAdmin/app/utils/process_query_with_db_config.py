"""
Enhanced Process User Query
Uses Database Configuration first, then falls back to LLM
Priority: DB Config Recipes > Knowledge Corpus > LLM Generation
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


def process_user_query_with_db_config(
    user_query: str,
    user_id: str,
    context: Optional[List[Dict[str, str]]] = None,
    active_module: str = None,
    active_repository: str = None
) -> Dict[str, Any]:
    """
    Enhanced query processing with Database Configuration priority
    
    Flow:
    1. Try to match query to database configuration recipe
    2. If matched, execute recipe and return results
    3. If no match, check Knowledge Corpus
    4. If still no match, fall back to LLM query generation
    
    Args:
        user_query: User's natural language query
        user_id: User identifier
        context: Conversation context
        active_module: Active module ID (from database configuration)
        active_repository: Active repository name (legacy, for backward compatibility)
        
    Returns:
        Response dictionary with intent, answer, and data
    """
    try:
        logger.info(f"Processing query with DB config: user={user_id}, module={active_module}, query={user_query[:50]}...")
        
        # Import required utilities
        from app.utils.db_config_query_executor import get_db_config_executor
        from app.utils.integrated_knowledge_query import query_hybrid_knowledge
        
        executor = get_db_config_executor()
        
        # ===== STEP 1: Try to match query to database configuration recipe =====
        recipe_match = executor.match_query_to_recipe(user_query, active_module)
        
        if recipe_match and recipe_match.get('score', 0) >= 5:
            # Good match found! Execute the recipe
            recipe_id = recipe_match['recipe_id']
            recipe = recipe_match['recipe']
            
            logger.info(f"✅ Matched query to recipe: {recipe_id} (score: {recipe_match['score']})")
            
            # Extract filters from user query (e.g., "show me expired LC" -> status=expired)
            filters = _extract_filters_from_query(user_query, recipe)
            
            # Execute the recipe
            success, result = executor.execute_recipe(recipe_id, filters)
            
            if success and result.get('success'):
                # Format the response
                return _format_recipe_response(result, recipe, user_query)
            else:
                logger.warning(f"Recipe execution failed: {result}")
                # Fall through to Knowledge Corpus
        
        # ===== STEP 2: Check Knowledge Corpus =====
        logger.info("No recipe match or execution failed, checking Knowledge Corpus...")
        
        # Use active_repository for KC query (backward compatibility)
        kc_result = query_hybrid_knowledge(user_query, user_id, active_repository or active_module)
        
        if kc_result.get('success'):
            logger.info(f"✅ Found answer in Knowledge Corpus")
            return {
                'intent': 'Knowledge Query',
                'answer': kc_result.get('response', ''),
                'html': kc_result.get('html', ''),
                'sources': kc_result.get('knowledge_corpus', {}).get('sources', []),
                'source': 'knowledge_corpus'
            }
        
        # ===== STEP 3: Fall back to LLM query generation =====
        logger.info("No Knowledge Corpus match, falling back to LLM...")
        
        # Import the original process_user_query
        from app.utils.query_utils import process_user_query as original_process_query
        
        # Call original LLM-based processing
        return original_process_query(user_query, user_id, context, active_repository)
        
    except Exception as e:
        logger.error(f"Error in process_user_query_with_db_config: {e}")
        import traceback
        traceback.print_exc()
        
        # Ultimate fallback
        return {
            'intent': 'error',
            'answer': f"I encountered an error processing your request. Please try rephrasing your question.",
            'error': str(e)
        }


def _extract_filters_from_query(user_query: str, recipe: Dict) -> Dict:
    """
    Extract filter values from user query based on recipe's allowed filters
    
    Examples:
        "show me expired LC" -> {'status': 'expired'}
        "list top 10 LCs" -> {'limit': 10}
        "find pending applications" -> {'status': 'pending'}
    """
    filters = {}
    user_query_lower = user_query.lower()
    
    # Common status keywords
    status_keywords = {
        'expired': 'expired',
        'pending': 'pending',
        'active': 'active',
        'completed': 'completed',
        'approved': 'approved',
        'rejected': 'rejected',
        'draft': 'draft',
        'submitted': 'submitted'
    }
    
    for keyword, status_value in status_keywords.items():
        if keyword in user_query_lower:
            filters['status'] = status_value
            break
    
    # Extract limit
    import re
    
    # Match patterns like "top 10", "first 5", "limit 20"
    limit_patterns = [
        r'top\s+(\d+)',
        r'first\s+(\d+)',
        r'limit\s+(\d+)',
        r'show\s+(\d+)'
    ]
    
    for pattern in limit_patterns:
        match = re.search(pattern, user_query_lower)
        if match:
            filters['limit'] = int(match.group(1))
            break
    
    # Extract date-related filters
    if 'today' in user_query_lower:
        filters['date_filter'] = 'today'
    elif 'yesterday' in user_query_lower:
        filters['date_filter'] = 'yesterday'
    elif 'this week' in user_query_lower or 'last 7 days' in user_query_lower:
        filters['date_filter'] = 'week'
    elif 'this month' in user_query_lower:
        filters['date_filter'] = 'month'
    
    logger.info(f"Extracted filters from query: {filters}")
    return filters


def _format_recipe_response(result: Dict, recipe: Dict, user_query: str) -> Dict:
    """
    Format recipe execution result into a user-friendly response
    
    Args:
        result: Query result from executor
        recipe: Recipe configuration
        user_query: Original user query
        
    Returns:
        Formatted response dictionary
    """
    data = result.get('data', [])
    count = result.get('count', 0)
    
    # Create a natural language response
    recipe_name = recipe.get('name', 'query')
    
    if count == 0:
        answer = f"I couldn't find any results for '{user_query}'. "
        answer += "Try adjusting your search criteria or ask me to show you what's available."
    elif count == 1:
        answer = f"I found 1 record matching '{user_query}'."
    else:
        answer = f"I found {count} records matching '{user_query}'."
    
    # Add recipe description if available
    if recipe.get('description'):
        answer += f"\n\n{recipe.get('description')}"
    
    # Create HTML table for the results
    html_table = _create_html_table(data, recipe)
    
    return {
        'intent': 'Table Request',
        'output_format': 'table',
        'answer': answer,
        'html': html_table,
        'data': data,
        'count': count,
        'recipe_id': result.get('recipe_id'),
        'recipe_name': recipe_name,
        'base_table': result.get('base_table'),
        'query': result.get('query'),
        'source': 'database_config_recipe',
        'success': True
    }


def _create_html_table(data: List[Dict], recipe: Dict) -> str:
    """
    Create an HTML table from query results
    
    Args:
        data: List of result records
        recipe: Recipe configuration
        
    Returns:
        HTML table string
    """
    if not data:
        return '<div class="no-data">No results found</div>'
    
    # Get columns from recipe or from first data item
    columns = recipe.get('columns', [])
    if not columns or columns == ['*']:
        # Use keys from first record
        columns = list(data[0].keys())
    
    # Remove _id from display
    display_columns = [col for col in columns if not col.startswith('_')]
    
    # Build HTML table
    html = '<div class="table-container">'
    html += '<table class="data-table">'
    
    # Header
    html += '<thead><tr>'
    for col in display_columns:
        # Clean column name for display
        col_display = col.replace('_', ' ').title()
        html += f'<th>{col_display}</th>'
    html += '</tr></thead>'
    
    # Body
    html += '<tbody>'
    for row in data:
        html += '<tr>'
        for col in display_columns:
            value = row.get(col, '')
            
            # Format dates
            if isinstance(value, datetime):
                value = value.strftime('%Y-%m-%d %H:%M')
            elif value is None:
                value = ''
            
            html += f'<td>{value}</td>'
        html += '</tr>'
    html += '</tbody>'
    
    html += '</table></div>'
    
    return html
