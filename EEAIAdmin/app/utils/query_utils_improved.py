import json
import traceback
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from functools import lru_cache
import re

from app.utils.file_utils import get_embedding_azureRAG
from app.utils.app_config import deployment_name
import openai

logger = logging.getLogger(__name__)

# Cache for embeddings to avoid regenerating for same queries
@lru_cache(maxsize=1000)
def get_cached_embedding(query: str):
    """Cache embeddings for frequently used queries"""
    return get_embedding_azureRAG(query)

class QueryProcessor:
    """Improved query processor with better separation of concerns"""
    
    def __init__(self, user_manual_collection):
        self.user_manual_collection = user_manual_collection
        self.intent_cache = {}  # Cache intent classifications
        
    def process_user_query(self, user_query: str, user_id: str, 
                          context: Optional[List[Dict[str, str]]] = None, 
                          active_repository: str = None) -> Dict[str, Any]:
        """
        Process user query with improved logic and error handling
        """
        try:
            # Input validation
            if not self._validate_inputs(user_query, user_id):
                return {"error": "Invalid input parameters"}
            
            # Check cache first
            cache_key = f"{user_id}:{user_query}:{active_repository}"
            if cache_key in self.intent_cache:
                logger.info("Using cached intent classification")
                return self.intent_cache[cache_key]
            
            # Get conversation context
            history_context = self._build_conversation_context(context)
            
            # Get manual context if needed (skip for simple data queries with repository)
            manual_context = ""
            if not (active_repository and self._is_simple_data_query(user_query)):
                manual_context = self._get_manual_context(user_query, user_id)
            
            # Classify intent with unified approach
            result = self._classify_intent(
                user_query, user_id, history_context, 
                manual_context, active_repository
            )
            
            # Cache the result
            self.intent_cache[cache_key] = result
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            logger.debug(traceback.format_exc())
            return {
                "error": "Failed to process your query. Please try again.",
                "details": str(e)
            }
    
    def _validate_inputs(self, user_query: str, user_id: str) -> bool:
        """Validate input parameters"""
        if not user_query or not isinstance(user_query, str):
            logger.error("Invalid user_query")
            return False
        if not user_id or not isinstance(user_id, str):
            logger.error("Invalid user_id")
            return False
        return True
    
    def _is_simple_data_query(self, query: str) -> bool:
        """Check if query is a simple data request"""
        data_keywords = [
            'show', 'list', 'display', 'find', 'search', 'get', 'fetch',
            'transaction', 'forex', 'fx', 'money market', 'derivative',
            'payment', 'cash', 'liquidity', 'investment'
        ]
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in data_keywords)
    
    def _build_conversation_context(self, context: Optional[List[Dict[str, str]]]) -> str:
        """Build conversation history string"""
        if not context:
            return ""
            
        history_parts = []
        for entry in context[-10:]:  # Limit to last 10 entries for performance
            if 'role' in entry and 'message' in entry:
                history_parts.append(f"{entry['role']}: {entry['message']}")
            elif 'message' in entry and 'response' in entry:
                history_parts.append(f"user: {entry['message']}")
                if isinstance(entry['response'], str):
                    history_parts.append(f"assistant: {entry['response']}")
                elif isinstance(entry['response'], dict) and 'response' in entry['response']:
                    history_parts.append(f"assistant: {entry['response']['response']}")
        
        return "\n".join(history_parts)
    
    def _get_manual_context(self, user_query: str, user_id: str) -> str:
        """Retrieve relevant manual context from ChromaDB"""
        try:
            # Use cached embedding
            query_embedding = get_cached_embedding(user_query.strip())
            
            results = self.user_manual_collection.query(
                query_embeddings=[query_embedding],
                n_results=3,
                where={"user_id": user_id}
            )
            
            docs = results.get("documents", [[]])[0] if results.get("documents") else []
            
            if not docs:
                return ""
                
            # Validate documents
            valid_docs = [doc for doc in docs if isinstance(doc, str)]
            
            if valid_docs:
                return "\n".join([f"Section {i + 1}: {doc}" for i, doc in enumerate(valid_docs)])
            
            return ""
            
        except Exception as e:
            logger.warning(f"Failed to get manual context: {str(e)}")
            return ""
    
    def _classify_intent(self, user_query: str, user_id: str, 
                        history_context: str, manual_context: str,
                        active_repository: str = None) -> Dict[str, Any]:
        """Unified intent classification"""
        
        # Quick classification for repository data queries
        if active_repository and self._is_simple_data_query(user_query):
            return {
                "intent": "Table Request",
                "output_format": "table",
                "answer": f"Querying {active_repository.replace('_', ' ').title()} repository",
                "active_repository": active_repository,
                "confidence": 95
            }
        
        # Use LLM for complex classification
        prompt = self._build_classification_prompt(
            user_query, history_context, manual_context, active_repository
        )
        
        try:
            # Call LLM with retry logic
            response = self._call_llm_with_retry(prompt)
            
            # Parse response
            parsed = self._parse_llm_response(response)
            
            # Enhance response based on context
            return self._enhance_response(parsed, active_repository)
            
        except Exception as e:
            logger.error(f"LLM classification failed: {str(e)}")
            # Fallback to rule-based classification
            return self._fallback_classification(user_query, active_repository)
    
    def _build_classification_prompt(self, user_query: str, history_context: str,
                                   manual_context: str, active_repository: str = None) -> str:
        """Build optimized classification prompt"""
        
        repo_context = ""
        if active_repository:
            repo_descriptions = {
                "trade_finance": "Trade Finance (LC, guarantees, invoices)",
                "treasury": "Treasury (forex, derivatives, investments)",
                "cash": "Cash Management (transactions, liquidity, payments)"
            }
            repo_context = f"\nActive Repository: {repo_descriptions.get(active_repository, active_repository)}"
        
        # Shorter, more focused prompt
        prompt = f"""Classify this query into ONE intent category.

Query: "{user_query}"
{repo_context}

Categories:
1. Table Request - Show data in table format
2. Report Request - Generate downloadable report  
3. User Manual - Help, guidance, or manual queries
4. Creation Transaction - Create new transaction
5. Export Report - Export conversation data
6. Other - Doesn't fit above categories

Recent Context: {history_context[:500] if history_context else 'None'}
Manual Context: {'Available' if manual_context else 'None'}

Return JSON: {{"intent": "<category>", "output_format": "<table|report|text>", "confidence": <0-100>}}"""
        
        return prompt
    
    def _call_llm_with_retry(self, prompt: str, max_retries: int = 3) -> str:
        """Call LLM with retry logic"""
        for attempt in range(max_retries):
            try:
                response = openai.ChatCompletion.create(
                    engine=deployment_name,
                    messages=[
                        {"role": "system", "content": "You are a query classifier. Return only valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1,
                    max_tokens=150
                )
                return response["choices"][0]["message"]["content"].strip()
                
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                logger.warning(f"LLM call failed (attempt {attempt + 1}): {str(e)}")
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response with better error handling"""
        # Try to extract JSON
        json_match = re.search(r'\{[^}]+\}', response)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        # Fallback parsing
        response_clean = response.replace('```json', '').replace('```', '').strip()
        try:
            return json.loads(response_clean)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse LLM response: {response}")
            raise ValueError("Invalid LLM response format")
    
    def _enhance_response(self, parsed_response: Dict[str, Any], 
                         active_repository: str = None) -> Dict[str, Any]:
        """Enhance parsed response with additional context"""
        intent = parsed_response.get("intent", "Unknown")
        
        # Add standard fields
        response = {
            "intent": intent,
            "output_format": parsed_response.get("output_format", "text"),
            "confidence": parsed_response.get("confidence", 70),
            "answer": self._generate_answer(intent, active_repository)
        }
        
        # Add special flags based on intent
        if intent == "Creation Transaction":
            response["requires_creation_handler"] = True
        elif intent == "User Manual" and "train" in parsed_response.get("answer", "").lower():
            response["requires_training_handler"] = True
        
        if active_repository:
            response["active_repository"] = active_repository
            
        return response
    
    def _generate_answer(self, intent: str, active_repository: str = None) -> str:
        """Generate appropriate answer based on intent"""
        if active_repository and intent in ["Table Request", "Report Request"]:
            return f"Querying {active_repository.replace('_', ' ').title()} repository"
        
        answers = {
            "Table Request": "Retrieving data for your query",
            "Report Request": "Generating report based on your criteria",
            "User Manual": "Processing your request",
            "Creation Transaction": "Starting transaction creation process",
            "Export Report": "Preparing data for export"
        }
        
        return answers.get(intent, "Processing your query")
    
    def _fallback_classification(self, user_query: str, 
                                active_repository: str = None) -> Dict[str, Any]:
        """Rule-based fallback classification"""
        query_lower = user_query.lower()
        
        # Check for data queries
        if any(kw in query_lower for kw in ['show', 'list', 'display', 'find']):
            return {
                "intent": "Table Request",
                "output_format": "table",
                "answer": "Retrieving data",
                "confidence": 60
            }
        
        # Check for help queries
        if any(kw in query_lower for kw in ['how to', 'help', 'guide']):
            return {
                "intent": "User Manual",
                "output_format": "text",
                "answer": "Providing guidance",
                "confidence": 60
            }
        
        # Check for report queries
        if any(kw in query_lower for kw in ['report', 'download', 'export']):
            return {
                "intent": "Report Request",
                "output_format": "report",
                "answer": "Generating report",
                "confidence": 60
            }
        
        return {
            "intent": "Other",
            "output_format": "text", 
            "answer": "Processing your request",
            "confidence": 40
        }