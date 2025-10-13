import logging
from typing import Dict, List, Any, Optional
from app.utils.query_utils import process_user_query as original_process_user_query
from app.utils.file_utils import get_embedding_azureRAG

logger = logging.getLogger(__name__)

def process_user_query_with_repositories(
    user_query: str, 
    user_id: str, 
    context: Optional[List[Dict[str, str]]] = None,
    repository_rag = None,
    repository_manager = None
) -> Dict[str, Any]:
    """Enhanced query processor that uses connected repositories for RAG"""
    
    # First, get the original intent and processing
    original_response = original_process_user_query(user_query, user_id, context)
    intent = original_response.get("intent", "unknown")
    
    # If repository_rag is available and user has connected repositories, enhance the response
    if repository_rag and repository_manager:
        try:
            # Check if user has connected repositories
            connected_repos = repository_manager.get_user_connections(user_id)
            
            if connected_repos:
                logger.info(f"User {user_id} has {len(connected_repos)} connected repositories")
                
                # Perform repository-aware RAG query
                rag_results = repository_rag.query_with_repositories(
                    user_query, 
                    user_id, 
                    n_results=5,
                    include_user_manuals=True
                )
                
                if rag_results.get("success") and rag_results.get("results"):
                    # Format RAG context
                    rag_context = repository_rag.format_rag_context(rag_results)
                    
                    # Enhance the response with RAG context
                    enhanced_prompt = f"""You are a trade finance expert assistant. Based on the following context from our knowledge repositories and the user's question, provide a comprehensive and accurate answer.

Repository Context:
{rag_context}

User Question: {user_query}

Previous Response (if any): {original_response.get('answer', '')}

Instructions:
1. If the repository context contains relevant information, use it to provide a detailed answer
2. If the previous response is adequate and the context doesn't add value, keep the original response
3. Always cite which repository/collection the information comes from when using RAG context
4. If the context contradicts the previous response, prioritize the repository context
5. Be specific and include relevant details from the context"""

                    try:
                        # Use GPT to generate enhanced response
                        from app.utils.gpt_utils import get_gpt_response
                        enhanced_response = get_gpt_response(enhanced_prompt)
                        
                        # Update the response with enhanced content
                        original_response["answer"] = enhanced_response
                        original_response["response"] = enhanced_response
                        
                        # Add RAG metadata
                        original_response["rag_enhanced"] = True
                        original_response["rag_stats"] = {
                            "total_results": rag_results["total_results"],
                            "collections_searched": rag_results["collections_searched"],
                            "repositories_used": len(connected_repos)
                        }
                        
                        # Add sources
                        if rag_results.get("results"):
                            original_response["sources"] = [
                                {
                                    "collection": r["collection_name"],
                                    "relevance": r["relevance_score"],
                                    "preview": r["document"][:200] + "..." if len(r["document"]) > 200 else r["document"]
                                }
                                for r in rag_results["results"][:3]
                            ]
                        
                        logger.info(f"Enhanced response with RAG from {rag_results['collections_searched']} collections")
                        
                    except Exception as e:
                        logger.error(f"Error enhancing response with GPT: {e}")
                        # Keep original response if enhancement fails
                else:
                    logger.info("No relevant RAG results found for enhancement")
            else:
                logger.info(f"User {user_id} has no connected repositories")
                
                # Add a suggestion to connect repositories
                if "follow_up_questions" not in original_response:
                    original_response["follow_up_questions"] = []
                    
                original_response["follow_up_questions"].append(
                    "Would you like to connect to knowledge repositories for enhanced answers?"
                )
                
        except Exception as e:
            logger.error(f"Error in repository-aware query processing: {e}")
            # Return original response if enhancement fails
    
    return original_response