import logging
from typing import Dict, List, Any, Optional, Tuple
import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)

class RepositoryAwareRAG:
    """RAG query handler that uses connected repositories to search relevant ChromaDB collections"""
    
    def __init__(self, repository_manager, chroma_client):
        self.repository_manager = repository_manager
        self.chroma_client = chroma_client
        
    def get_user_accessible_collections(self, user_id: str) -> List[Tuple[str, str]]:
        """Get list of ChromaDB collections accessible to the user based on connected repositories"""
        accessible_collections = []
        
        # Get user's connected repositories
        connected_repo_ids = self.repository_manager.get_user_connections(user_id)
        
        if not connected_repo_ids:
            logger.info(f"User {user_id} has no connected repositories")
            return accessible_collections
        
        # For each connected repository, get its ChromaDB collections
        for repo_id in connected_repo_ids:
            repo_details = self.repository_manager.get_repository_details(repo_id)
            if repo_details and "collections" in repo_details:
                for collection in repo_details["collections"]:
                    if "chroma_collection" in collection and collection.get("exists", False):
                        accessible_collections.append((
                            collection["chroma_collection"],
                            collection["name"]
                        ))
        
        logger.info(f"User {user_id} has access to {len(accessible_collections)} collections")
        return accessible_collections
    
    def query_with_repositories(self, user_query: str, user_id: str, n_results: int = 5, 
                               include_user_manuals: bool = True) -> Dict[str, Any]:
        """Query ChromaDB collections based on user's connected repositories"""
        try:
            from app.utils.file_utils import get_embedding_azureRAG
            
            # Get accessible collections
            accessible_collections = self.get_user_accessible_collections(user_id)
            
            # Always include user manuals if requested
            if include_user_manuals:
                accessible_collections.append(("user_manual", "User Manuals"))
            
            if not accessible_collections:
                return {
                    "success": False,
                    "message": "No repositories connected. Please connect to repositories to access RAG data.",
                    "results": []
                }
            
            # Generate query embedding
            query_embedding = get_embedding_azureRAG(user_query)
            
            all_results = []
            collection_results = {}
            
            # Query each accessible collection
            for chroma_collection, collection_name in accessible_collections:
                try:
                    collection = self.chroma_client.get_collection(chroma_collection)
                    
                    # Special handling for user manuals - filter by user_id
                    if chroma_collection == "user_manual":
                        results = collection.query(
                            query_embeddings=[query_embedding],
                            n_results=n_results,
                            where={"user_id": user_id}
                        )
                    else:
                        results = collection.query(
                            query_embeddings=[query_embedding],
                            n_results=n_results
                        )
                    
                    if results and results.get('documents'):
                        collection_result = {
                            "collection": chroma_collection,
                            "collection_name": collection_name,
                            "documents": [],
                            "count": 0
                        }
                        
                        # Process results
                        documents = results.get('documents', [[]])[0]
                        metadatas = results.get('metadatas', [[]])[0] if results.get('metadatas') else [{}] * len(documents)
                        distances = results.get('distances', [[]])[0] if results.get('distances') else [0] * len(documents)
                        ids = results.get('ids', [[]])[0] if results.get('ids') else [f"doc_{i}" for i in range(len(documents))]
                        
                        for i, doc in enumerate(documents):
                            if doc:  # Only include non-empty documents
                                result_item = {
                                    "id": ids[i],
                                    "document": doc,
                                    "metadata": metadatas[i] if i < len(metadatas) else {},
                                    "relevance_score": 1 - distances[i] if i < len(distances) else 0,
                                    "collection": chroma_collection,
                                    "collection_name": collection_name
                                }
                                collection_result["documents"].append(result_item)
                                all_results.append(result_item)
                        
                        collection_result["count"] = len(collection_result["documents"])
                        if collection_result["count"] > 0:
                            collection_results[chroma_collection] = collection_result
                            
                except Exception as e:
                    logger.warning(f"Error querying collection {chroma_collection}: {e}")
                    continue
            
            # Sort all results by relevance score
            all_results.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
            
            # Take top results across all collections
            top_results = all_results[:n_results * 2]  # Get more results for better context
            
            return {
                "success": True,
                "results": top_results,
                "collection_results": collection_results,
                "total_results": len(all_results),
                "collections_searched": len(collection_results),
                "message": f"Found {len(all_results)} results across {len(collection_results)} collections"
            }
            
        except Exception as e:
            logger.error(f"Error in repository-aware RAG query: {e}")
            return {
                "success": False,
                "message": f"Error performing RAG query: {str(e)}",
                "results": []
            }
    
    def get_repository_specific_context(self, user_id: str, repository_type: str) -> List[Dict[str, Any]]:
        """Get context from specific repository type (e.g., 'trade_finance')"""
        try:
            # Find repository by type
            repositories = self.repository_manager.repositories_collection.find({"type": repository_type})
            
            for repo in repositories:
                repo_id = str(repo["_id"])
                
                # Check if user has access
                if repo_id in self.repository_manager.get_user_connections(user_id):
                    # Get all collections for this repository
                    collections = []
                    if "collections" in repo:
                        for coll in repo["collections"]:
                            if "chroma_collection" in coll:
                                collections.append({
                                    "name": coll["name"],
                                    "chroma_collection": coll["chroma_collection"],
                                    "description": coll.get("description", "")
                                })
                    
                    return {
                        "repository_name": repo["name"],
                        "repository_type": repository_type,
                        "collections": collections,
                        "accessible": True
                    }
            
            return {
                "repository_type": repository_type,
                "accessible": False,
                "message": f"No access to {repository_type} repository"
            }
            
        except Exception as e:
            logger.error(f"Error getting repository context: {e}")
            return {
                "repository_type": repository_type,
                "accessible": False,
                "error": str(e)
            }
    
    def format_rag_context(self, rag_results: Dict[str, Any], max_context_length: int = 3000) -> str:
        """Format RAG results into context string for LLM"""
        if not rag_results.get("success") or not rag_results.get("results"):
            return ""
        
        context_parts = []
        total_length = 0
        
        # Group by collection for better context
        collection_groups = {}
        for result in rag_results["results"]:
            collection = result.get("collection_name", "Unknown")
            if collection not in collection_groups:
                collection_groups[collection] = []
            collection_groups[collection].append(result)
        
        # Build context from each collection
        for collection_name, results in collection_groups.items():
            context_parts.append(f"\n--- From {collection_name} ---")
            
            for result in results:
                doc_text = result.get("document", "")
                relevance = result.get("relevance_score", 0)
                metadata = result.get("metadata", {})
                
                # Add metadata context if available
                meta_str = ""
                if metadata:
                    relevant_meta = {k: v for k, v in metadata.items() 
                                   if k not in ["user_id", "chunk_index"] and v}
                    if relevant_meta:
                        meta_str = f" [{', '.join(f'{k}: {v}' for k, v in relevant_meta.items())}]"
                
                # Truncate document if needed
                if len(doc_text) > 500:
                    doc_text = doc_text[:500] + "..."
                
                context_part = f"\n[Relevance: {relevance:.2f}]{meta_str}\n{doc_text}\n"
                
                if total_length + len(context_part) > max_context_length:
                    break
                    
                context_parts.append(context_part)
                total_length += len(context_part)
            
            if total_length > max_context_length:
                break
        
        return "\n".join(context_parts)