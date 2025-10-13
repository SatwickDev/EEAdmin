"""
Enhanced query processor that maintains backward compatibility while adding optimizations
"""
import json
import traceback
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import time
from functools import wraps

# Import original functions to maintain compatibility
from app.utils.query_utils import (
    process_user_query as original_process_user_query,
    _get_cached_embedding,
    _is_simple_data_query
)

logger = logging.getLogger(__name__)

# Performance monitoring decorator
def monitor_performance(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start_time
        logger.info(f"{func.__name__} took {elapsed:.2f} seconds")
        return result
    return wrapper

@monitor_performance
def process_user_query_enhanced(user_query: str, user_id: str, 
                               context: Optional[List[Dict[str, str]]] = None, 
                               active_repository: str = None,
                               use_optimizations: bool = True) -> Dict[str, Any]:
    """
    Enhanced process_user_query with optimizations but maintains full backward compatibility
    
    Args:
        user_query (str): The user's query
        user_id (str): User identifier
        context (Optional[List[Dict[str, str]]]): Conversation history
        active_repository (str): Currently active repository (trade_finance, treasury, cash)
        use_optimizations (bool): Whether to use performance optimizations
    
    Returns:
        Dict[str, Any]: Processed query response with intent - fully compatible with original
    """
    try:
        # Input validation
        if not user_query or not isinstance(user_query, str):
            logger.error("Invalid user_query provided")
            return {"error": "Invalid query provided"}
        if not user_id or not isinstance(user_id, str):
            logger.error("Invalid user_id provided")
            return {"error": "Invalid user ID provided"}
        
        # OPTIMIZATION 1: Fast path for simple repository data queries
        if use_optimizations and active_repository and _is_simple_data_query(user_query):
            logger.info("Attempting fast path classification")
            
            # Import here to avoid circular import
            from app.utils.gpt_utils import classify_query_intent_with_llm
            
            try:
                # Quick LLM classification with timeout
                llm_result = classify_query_intent_with_llm(user_query, active_repository)
                
                # If high confidence data query, return fast result
                if (llm_result.get('confidence', 0) > 85 and 
                    llm_result.get('intent') in ['Table Request', 'Report']):
                    
                    logger.info(f"Fast path success: {llm_result.get('intent')} "
                              f"with confidence {llm_result.get('confidence')}")
                    
                    # Return complete response matching original format
                    return {
                        "intent": llm_result.get('intent'),
                        "output_format": llm_result.get('output_format', 'table'),
                        "answer": f"Querying {active_repository.replace('_', ' ').title()} repository",
                        "follow_up_questions": [],
                        "follow_up_intent": None,
                        "active_repository": active_repository,
                        "confidence": llm_result.get('confidence')
                    }
            except Exception as e:
                logger.warning(f"Fast path failed, falling back to full process: {str(e)}")
        
        # OPTIMIZATION 2: Use original with performance monitoring
        logger.info("Using full classification process")
        result = original_process_user_query(user_query, user_id, context, active_repository)
        
        # ENHANCEMENT: Add confidence score if not present
        if 'confidence' not in result and not result.get('error'):
            # Estimate confidence based on intent
            confidence_map = {
                'Table Request': 90,
                'Report Request': 90,
                'User Manual': 85,
                'Creation Transaction': 95,
                'Export Report Request': 90,
                'Follow-Up Request': 80,
                'Visualization Request': 85,
                'File Upload Request': 85,
                'Custom Rule Request': 85
            }
            result['confidence'] = confidence_map.get(result.get('intent'), 70)
        
        # ENHANCEMENT: Add active repository to result if present
        if active_repository and 'active_repository' not in result:
            result['active_repository'] = active_repository
        
        return result
        
    except Exception as e:
        logger.error(f"Unexpected error in enhanced query processor: {str(e)}")
        logger.debug(traceback.format_exc())
        
        # Fall back to original implementation
        try:
            logger.info("Falling back to original implementation")
            return original_process_user_query(user_query, user_id, context, active_repository)
        except Exception as fallback_error:
            logger.error(f"Fallback also failed: {str(fallback_error)}")
            return {
                "error": "Failed to process query",
                "details": "Both enhanced and original processors failed"
            }

def get_query_processor_stats():
    """Get statistics about query processing performance"""
    # This could be enhanced to track actual metrics
    return {
        "cache_size": len(_embedding_cache) if '_embedding_cache' in globals() else 0,
        "optimization_available": True,
        "version": "1.0.0-enhanced"
    }

# Utility functions for testing and migration
def validate_response_compatibility(original_response: Dict, enhanced_response: Dict) -> bool:
    """Validate that enhanced response has all fields from original"""
    required_fields = {'intent', 'answer'}
    optional_fields = {'output_format', 'follow_up_questions', 'follow_up_intent',
                      'requires_creation_handler', 'requires_training_handler',
                      'trained_manual_context', 'error'}
    
    # Check required fields
    for field in required_fields:
        if field in original_response and field not in enhanced_response:
            return False
    
    # Check that we don't break special handlers
    if original_response.get('requires_creation_handler') and not enhanced_response.get('requires_creation_handler'):
        return False
    if original_response.get('requires_training_handler') and not enhanced_response.get('requires_training_handler'):
        return False
    
    return True

# For easy migration: create an alias that can be swapped
process_user_query = process_user_query_enhanced  # Can switch back to original if needed