"""
🔄 UNIFIED MANUAL & KNOWLEDGE CORPUS INTEGRATION
================================================

This module provides a unified interface to access both:
1. User Manuals (ChromaDB) - Global PDF uploads
2. Knowledge Corpus Documents (MongoDB) - Structured documents with Q&A pairs

The chatbot will query BOTH sources intelligently.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# ============================================================================
# UNIFIED MANUAL RETRIEVAL
# ============================================================================

def get_all_knowledge_sources(user_id: str = None) -> Dict[str, Any]:
    """
    Get ALL knowledge sources available for the chatbot:
    1. Knowledge Corpus Documents (MongoDB)
    2. User Manuals (ChromaDB)
    
    Returns unified list with source type indicators.
    """
    try:
        from app.utils.rag_clausetag import user_manual_collection
        from app.utils.app_config import kc_documents_collection
        
        all_sources = {
            "success": True,
            "sources": [],
            "knowledge_corpus": {
                "count": 0,
                "documents": [],
                "published_count": 0
            },
            "user_manuals": {
                "count": 0,
                "files": []
            }
        }
        
        # ============================================================
        # 1. GET KNOWLEDGE CORPUS DOCUMENTS
        # ============================================================
        try:
            # Query published documents from Knowledge Corpus
            kc_query = {"status": "published"}
            kc_documents = list(kc_documents_collection.find(kc_query).sort("created_at", -1))
            
            for doc in kc_documents:
                all_sources["sources"].append({
                    "type": "knowledge_corpus",
                    "id": str(doc.get("document_id", "")),
                    "name": doc.get("name", "Untitled"),
                    "file_name": doc.get("file_name", ""),
                    "status": doc.get("status", "draft"),
                    "pages": doc.get("stats", {}).get("total_pages", 0),
                    "qa_pairs": doc.get("stats", {}).get("approved_qa_count", 0),
                    "uploaded_at": doc.get("created_at", datetime.now()).isoformat(),
                    "uploaded_by": doc.get("uploaded_by", "Unknown"),
                    "icon": "📚",
                    "badge": "Knowledge Base"
                })
                
                all_sources["knowledge_corpus"]["documents"].append({
                    "document_id": str(doc.get("document_id", "")),
                    "name": doc.get("name", "Untitled"),
                    "file_name": doc.get("file_name", ""),
                    "qa_pairs": doc.get("stats", {}).get("approved_qa_count", 0)
                })
            
            all_sources["knowledge_corpus"]["count"] = len(kc_documents)
            all_sources["knowledge_corpus"]["published_count"] = len(kc_documents)
            
            logger.info(f"Found {len(kc_documents)} Knowledge Corpus documents")
            
        except Exception as e:
            logger.error(f"Error fetching Knowledge Corpus documents: {e}")
            # Continue even if KC fails
        
        # ============================================================
        # 2. GET USER MANUALS (ChromaDB)
        # ============================================================
        try:
            # Get all global manuals from ChromaDB
            results = user_manual_collection.get(
                where={"is_global": True}
            )
            
            # Extract unique file names
            file_names = set()
            if results and "metadatas" in results:
                for metadata in results["metadatas"]:
                    if metadata and "file_name" in metadata:
                        file_names.add(metadata["file_name"])
            
            for file_name in sorted(file_names):
                all_sources["sources"].append({
                    "type": "user_manual",
                    "id": file_name,
                    "name": file_name,
                    "file_name": file_name,
                    "status": "active",
                    "pages": "N/A",
                    "qa_pairs": "N/A",
                    "uploaded_at": "N/A",
                    "uploaded_by": "Admin",
                    "icon": "📄",
                    "badge": "User Manual"
                })
                
                all_sources["user_manuals"]["files"].append(file_name)
            
            all_sources["user_manuals"]["count"] = len(file_names)
            
            logger.info(f"Found {len(file_names)} User Manuals in ChromaDB")
            
        except Exception as e:
            logger.error(f"Error fetching User Manuals: {e}")
            # Continue even if manuals fail
        
        # ============================================================
        # RETURN COMBINED RESULTS
        # ============================================================
        total_sources = all_sources["knowledge_corpus"]["count"] + all_sources["user_manuals"]["count"]
        logger.info(f"Total knowledge sources: {total_sources} (KC: {all_sources['knowledge_corpus']['count']}, Manuals: {all_sources['user_manuals']['count']})")
        
        return all_sources
        
    except Exception as e:
        logger.error(f"Error in get_all_knowledge_sources: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "success": False,
            "error": str(e),
            "sources": [],
            "knowledge_corpus": {"count": 0, "documents": []},
            "user_manuals": {"count": 0, "files": []}
        }


# ============================================================================
# KNOWLEDGE SOURCE STATS FOR UI
# ============================================================================

def get_knowledge_source_stats() -> Dict[str, Any]:
    """
    Get statistics for UI display:
    - Total documents in Knowledge Corpus
    - Total Q&A pairs approved
    - Total User Manuals in ChromaDB
    """
    try:
        from app.utils.app_config import kc_documents_collection, kc_qa_pairs_collection
        from app.utils.rag_clausetag import user_manual_collection
        
        stats = {
            "success": True,
            "knowledge_corpus": {
                "total_documents": 0,
                "published_documents": 0,
                "total_qa_pairs": 0,
                "approved_qa_pairs": 0
            },
            "user_manuals": {
                "total_files": 0,
                "total_chunks": 0
            },
            "combined": {
                "total_sources": 0
            }
        }
        
        # Knowledge Corpus stats
        try:
            stats["knowledge_corpus"]["total_documents"] = kc_documents_collection.count_documents({})
            stats["knowledge_corpus"]["published_documents"] = kc_documents_collection.count_documents({"status": "published"})
            stats["knowledge_corpus"]["total_qa_pairs"] = kc_qa_pairs_collection.count_documents({})
            stats["knowledge_corpus"]["approved_qa_pairs"] = kc_qa_pairs_collection.count_documents({"status": "approved"})
        except Exception as e:
            logger.error(f"Error getting KC stats: {e}")
        
        # User Manuals stats
        try:
            results = user_manual_collection.get(where={"is_global": True})
            if results and "metadatas" in results:
                file_names = set()
                for metadata in results["metadatas"]:
                    if metadata and "file_name" in metadata:
                        file_names.add(metadata["file_name"])
                stats["user_manuals"]["total_files"] = len(file_names)
                stats["user_manuals"]["total_chunks"] = len(results["metadatas"])
        except Exception as e:
            logger.error(f"Error getting manual stats: {e}")
        
        # Combined
        stats["combined"]["total_sources"] = (
            stats["knowledge_corpus"]["published_documents"] + 
            stats["user_manuals"]["total_files"]
        )
        
        return stats
        
    except Exception as e:
        logger.error(f"Error in get_knowledge_source_stats: {e}")
        return {"success": False, "error": str(e)}


# ============================================================================
# SEARCH ACROSS ALL SOURCES
# ============================================================================

def search_all_knowledge_sources(
    query: str,
    user_id: str,
    source_types: List[str] = None,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Search across ALL knowledge sources (KC + Manuals).
    
    Args:
        query: Search query
        user_id: User identifier
        source_types: List of source types to search ['knowledge_corpus', 'user_manual']
                     If None, searches all
        limit: Max results per source
    
    Returns:
        Combined search results from all sources
    """
    from app.utils.integrated_knowledge_query import query_hybrid_knowledge
    
    # Default to all source types
    if source_types is None:
        source_types = ['knowledge_corpus', 'user_manual']
    
    # Use the hybrid query function which already searches both
    result = query_hybrid_knowledge(query, user_id, active_repository=None)
    
    # Add source type filtering if needed
    if 'knowledge_corpus' not in source_types:
        result.pop('knowledge_corpus', None)
    if 'user_manual' not in source_types:
        result.pop('user_manuals', None)
    
    return result
