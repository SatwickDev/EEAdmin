"""
Autocomplete API Routes
Provides intelligent suggestions with KC-first priority and LLM fallback
"""
from flask import Blueprint, request, jsonify, session
from app.routes import logger, kc_qa_pairs_collection, active_user_repositories
from app.utils.app_config import deployment_name
import openai
import time
import re
from typing import List, Dict, Tuple
import numpy as np

autocomplete_bp = Blueprint('autocomplete', __name__)


def calculate_similarity(text1: str, text2: str) -> float:
    """Calculate simple word overlap similarity"""
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    
    if not words1 or not words2:
        return 0.0
    
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    
    return len(intersection) / len(union)


def search_knowledge_corpus(query: str, limit: int = 5) -> List[Dict]:
    """
    Search Knowledge Corpus for matching questions (KC-first approach)
    
    Returns:
        List of matching questions with confidence scores
    """
    try:
        # Get approved Q&A pairs from Knowledge Corpus
        kc_results = list(kc_qa_pairs_collection.find(
            {
                'approved': True,
                '$or': [
                    {'canonical_question': {'$regex': query, '$options': 'i'}},
                    {'variants': {'$elemMatch': {'$regex': query, '$options': 'i'}}}
                ]
            },
            {
                'canonical_question': 1,
                'variants': 1,
                'tags': 1,
                'usage_count': 1
            }
        ).limit(limit * 2))
        
        suggestions = []
        seen = set()
        
        for kc_item in kc_results:
            # Add canonical question
            canonical = kc_item.get('canonical_question', '')
            if canonical and canonical not in seen:
                confidence = calculate_similarity(query, canonical)
                suggestions.append({
                    'text': canonical,
                    'source': 'KC',
                    'confidence': min(confidence + 0.2, 1.0),  # Boost KC suggestions
                    'tags': kc_item.get('tags', []),
                    'usage_count': kc_item.get('usage_count', 0)
                })
                seen.add(canonical)
            
            # Add variants
            for variant in kc_item.get('variants', [])[:3]:
                if variant and variant not in seen:
                    confidence = calculate_similarity(query, variant)
                    suggestions.append({
                        'text': variant,
                        'source': 'KC',
                        'confidence': min(confidence + 0.15, 1.0),
                        'tags': kc_item.get('tags', []),
                        'usage_count': kc_item.get('usage_count', 0)
                    })
                    seen.add(variant)
        
        # Sort by confidence and usage
        suggestions.sort(key=lambda x: (x['confidence'], x.get('usage_count', 0)), reverse=True)
        
        return suggestions[:limit]
        
    except Exception as e:
        logger.error(f"Error searching Knowledge Corpus: {e}")
        return []


def generate_llm_suggestions(query: str, num_suggestions: int = 3) -> Tuple[List[Dict], int]:
    """
    Generate suggestions using LLM (fallback when KC has insufficient matches)
    
    Returns:
        Tuple of (suggestions list, tokens_used)
    """
    try:
        prompt = f"""
You are an AI assistant for a trade finance system. Complete the user's query with relevant suggestions.

User is typing: "{query}"

Generate {num_suggestions} relevant query completions. Focus on:
- Letter of Credit (LC) queries
- Trade finance transactions
- Status checks (expired, active, pending, completed)
- Date-based queries
- Amendment and negotiation queries

Return ONLY a JSON array of strings (no extra text):
["suggestion 1", "suggestion 2", "suggestion 3"]

Examples:
- "show me expired LC"
- "list all active LCs"
- "find LCs expiring next week"
"""

        response = openai.ChatCompletion.create(
            engine=deployment_name,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that completes trade finance queries."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=150
        )
        
        content = response['choices'][0]['message']['content'].strip()
        tokens_used = response['usage']['total_tokens']
        
        # Parse JSON response
        import json
        try:
            suggestions_list = json.loads(content)
            
            suggestions = [
                {
                    'text': sug,
                    'source': 'LLM',
                    'confidence': 0.7 - (i * 0.1),  # Decreasing confidence
                    'tags': []
                }
                for i, sug in enumerate(suggestions_list[:num_suggestions])
            ]
            
            return suggestions, tokens_used
            
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse LLM response: {content}")
            return [], tokens_used
        
    except Exception as e:
        logger.error(f"Error generating LLM suggestions: {e}")
        return [], 0


@autocomplete_bp.route('/api/autocomplete/suggest', methods=['GET'])
def autocomplete_suggest():
    """
    Autocomplete endpoint with KC-first strategy
    
    Query params:
        q: The search query
        limit: Maximum number of suggestions (default: 8)
    """
    start_time = time.time()
    
    query = request.args.get('q', '').strip()
    limit = min(int(request.args.get('limit', 8)), 20)
    
    if not query or len(query) < 2:
        return jsonify({
            'suggestions': [],
            'latency_ms': 0,
            'used_llm': False,
            'tokens_used': 0
        })
    
    # Step 1: Search Knowledge Corpus (KC-first)
    kc_suggestions = search_knowledge_corpus(query, limit=limit)
    
    # Step 2: Determine if LLM is needed
    used_llm = False
    tokens_used = 0
    llm_suggestions = []
    
    # Use LLM only if KC has < 5 suggestions with confidence > 0.5
    high_confidence_kc = [s for s in kc_suggestions if s['confidence'] > 0.5]
    
    if len(high_confidence_kc) < 5:
        needed = limit - len(kc_suggestions)
        if needed > 0:
            llm_suggestions, tokens_used = generate_llm_suggestions(query, num_suggestions=needed)
            used_llm = True
    
    # Step 3: Combine and sort suggestions
    all_suggestions = kc_suggestions + llm_suggestions
    
    # Sort by source priority (KC first) then confidence
    all_suggestions.sort(
        key=lambda x: (x['source'] != 'KC', -x['confidence'])
    )
    
    # Limit to requested number
    final_suggestions = all_suggestions[:limit]
    
    latency_ms = int((time.time() - start_time) * 1000)
    
    logger.info(f"Autocomplete: '{query}' -> {len(final_suggestions)} suggestions "
                f"({len(kc_suggestions)} KC, {len(llm_suggestions)} LLM) in {latency_ms}ms")
    
    return jsonify({
        'suggestions': final_suggestions,
        'latency_ms': latency_ms,
        'used_llm': used_llm,
        'tokens_used': tokens_used,
        'kc_count': len(kc_suggestions),
        'llm_count': len(llm_suggestions)
    })


@autocomplete_bp.route('/api/autocomplete/next-word', methods=['POST'])
def next_word_prediction():
    """
    Predict next word(s) based on current query
    Uses simple n-gram matching from KC + LLM for complex cases
    """
    data = request.get_json()
    query = data.get('query', '').strip()
    
    if not query:
        return jsonify({'nextWords': []})
    
    # Simple next word suggestions based on common patterns
    words = query.lower().split()
    last_word = words[-1] if words else ''
    
    next_word_map = {
        'show': ['me', 'all', 'expired', 'active', 'pending'],
        'list': ['all', 'expired', 'active', 'pending', 'completed'],
        'find': ['LC', 'LCs', 'expired', 'active', 'overdue'],
        'me': ['expired', 'active', 'all', 'pending', 'completed'],
        'expired': ['LC', 'LCs', 'letters', 'transactions'],
        'active': ['LC', 'LCs', 'letters', 'transactions'],
        'all': ['LC', 'LCs', 'active', 'expired', 'pending'],
        'pending': ['LC', 'LCs', 'transactions', 'approvals'],
    }
    
    suggestions = next_word_map.get(last_word, [])
    
    next_words = [
        {'word': word, 'confidence': 0.8 - (i * 0.1)}
        for i, word in enumerate(suggestions[:5])
    ]
    
    return jsonify({'nextWords': next_words})


@autocomplete_bp.route('/api/autocomplete/trending', methods=['GET'])
def get_trending_queries():
    """
    Get trending/popular queries from user query history
    """
    try:
        from app.routes import kc_user_queries_collection
        
        # Get most common queries from the last 30 days
        from datetime import datetime, timedelta
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        pipeline = [
            {'$match': {'query_timestamp': {'$gte': thirty_days_ago}}},
            {'$group': {
                '_id': '$query_text',
                'count': {'$sum': 1}
            }},
            {'$sort': {'count': -1}},
            {'$limit': 10}
        ]
        
        trending = list(kc_user_queries_collection.aggregate(pipeline))
        
        trending_queries = [
            {
                'text': item['_id'],
                'type': 'trending',
                'count': item['count']
            }
            for item in trending
        ]
        
        return jsonify({'trending': trending_queries})
        
    except Exception as e:
        logger.error(f"Error fetching trending queries: {e}")
        
        # Fallback to default trending queries
        default_trending = [
            {'text': 'show me expired LC', 'type': 'trending'},
            {'text': 'list all active LCs', 'type': 'trending'},
            {'text': 'show LC amendments this month', 'type': 'trending'},
            {'text': 'find overdue payments', 'type': 'trending'}
        ]
        
        return jsonify({'trending': default_trending})
