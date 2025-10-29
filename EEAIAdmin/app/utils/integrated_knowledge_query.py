"""
Integrated Knowledge Query Handler
Combines Knowledge Corpus, User Manuals, and Database Configuration
for intelligent multi-source query processing
"""

from typing import Dict, List, Any, Optional
import logging
from datetime import datetime
import numpy as np

from app.utils.repository_database_mapper import (
    get_repository_database,
    get_repository_collections,
    get_knowledge_sources_for_repository,
    get_repository_info
)

logger = logging.getLogger(__name__)


def query_hybrid_knowledge(user_query: str, user_id: str, 
                           active_repository: str = None) -> Dict[str, Any]:
    """
    Intelligent query across Knowledge Corpus AND User Manuals
    Priority: Knowledge Corpus (approved Q&A) > User Manuals (PDF chunks)
    
    Args:
        user_query: User's question
        user_id: User identifier  
        active_repository: Currently active repository (trade_finance_repo, treasury_repo, cash_mgmt_repo)
    
    Returns:
        Combined results with formatted HTML response
    """
    try:
        from app.utils.file_utils import get_embedding_azureRAG
        from app.routes import kc_qa_pairs_collection, kc_embeddings_collection, kc_documents_collection
        from app.utils.query_utils import user_manual_collection
        
        logger.info(f"Hybrid knowledge query: user={user_id}, repo={active_repository}, query={user_query[:50]}...")
        
        results = {
            "knowledge_corpus": {"matches": [], "sources": []},
            "user_manuals": {"chunks": [], "files": []},
            "success": False,
            "response": "",
            "html": ""
        }
        
        # Generate query embedding once
        query_embedding = get_embedding_azureRAG(user_query)
        
        # ===== 1. Query Knowledge Corpus (Priority 1 - Highest confidence) =====
        try:
            pipeline = [
                {"$match": {"approved": True}},
                {
                    "$lookup": {
                        "from": "knowledge_corpus_embeddings",
                        "localField": "qa_id",
                        "foreignField": "qa_id",
                        "as": "embeddings"
                    }
                },
                {"$match": {"embeddings.enabled": True}},
                {
                    "$lookup": {
                        "from": "knowledge_corpus_documents",
                        "localField": "document_id",
                        "foreignField": "document_id",
                        "as": "document"
                    }
                }
            ]
            
            qa_pairs = list(kc_qa_pairs_collection.aggregate(pipeline))
            
            # Calculate similarities
            kc_matches = []
            for qa in qa_pairs:
                for emb in qa.get('embeddings', []):
                    if not emb.get('enabled'):
                        continue
                    
                    # Use 'embedding' field not 'embedding_vector'
                    embedding_vec = emb.get('embedding', emb.get('embedding_vector', []))
                    similarity = _cosine_similarity(query_embedding, embedding_vec)
                    
                    if similarity >= 0.70:  # 70% threshold
                        doc_info = qa.get('document', [{}])[0]
                        kc_matches.append({
                            'qa_id': qa.get('qa_id'),
                            'question': qa.get('canonical_question'),
                            'answer': qa.get('answer'),
                            'similarity': float(similarity),
                            'document_title': doc_info.get('title', 'Unknown'),
                            'document_id': qa.get('document_id'),
                            'page_number': qa.get('page_number')
                        })
            
            kc_matches.sort(key=lambda x: x['similarity'], reverse=True)
            results["knowledge_corpus"]["matches"] = kc_matches[:3]
            
            # Create source objects with document metadata (not just strings)
            source_docs = {}
            for m in kc_matches[:3]:
                doc_id = m.get('document_id')
                if doc_id and doc_id not in source_docs:
                    source_docs[doc_id] = {
                        "document_id": doc_id,
                        "document_name": m.get('document_title', 'Unknown'),
                        "document_title": m.get('document_title', 'Unknown')
                    }
            results["knowledge_corpus"]["sources"] = list(source_docs.values())
            
            logger.info(f"Knowledge Corpus: {len(kc_matches)} matches found")
            
        except Exception as e:
            logger.error(f"Knowledge Corpus query error: {e}")
        
        # ===== 2. Query Knowledge Corpus Documents (Published Documents) =====
        # This queries embeddings from published documents in MongoDB
        try:
            # Get embeddings for published documents
            published_docs = list(kc_documents_collection.find({
                "status": "published"
            }))
            
            doc_ids = [doc.get('document_id') for doc in published_docs]
            
            if doc_ids:
                # Get all embeddings for these documents
                embeddings_cursor = kc_embeddings_collection.find({
                    "document_id": {"$in": doc_ids},
                    "enabled": True
                })
                
                # Calculate similarities for document excerpts
                doc_matches = []
                for emb in embeddings_cursor:
                    # Use 'embedding' field not 'embedding_vector'
                    embedding_vec = emb.get('embedding', emb.get('embedding_vector', []))
                    similarity = _cosine_similarity(query_embedding, embedding_vec)
                    
                    if similarity >= 0.65:  # 65% threshold for document content
                        # Find the corresponding document
                        doc = next((d for d in published_docs if d.get('document_id') == emb.get('document_id')), None)
                        
                        if doc:
                            synopsis = doc.get('synopsis', {})
                            doc_matches.append({
                                'document_id': emb.get('document_id'),
                                'document_name': synopsis.get('title', doc.get('file_name', 'Unknown')),
                                'excerpt': emb.get('text_chunk', '')[:300],  # First 300 chars
                                'file_name': doc.get('file_name'),
                                'document_type': synopsis.get('document_type', 'Document'),
                                'page_count': doc.get('total_pages', 0),
                                'page_number': emb.get('page_number'),
                                'similarity': float(similarity)
                            })
                
                # Sort by similarity and take top matches
                doc_matches.sort(key=lambda x: x['similarity'], reverse=True)
                
                results["user_manuals"]["chunks"] = [m['excerpt'] for m in doc_matches[:3]]
                results["user_manuals"]["files"] = list(set([m['document_name'] for m in doc_matches[:3]]))
                results["user_manuals"]["doc_matches"] = doc_matches[:3]
                
                logger.info(f"User Manuals: {len(doc_matches)} document matches from Knowledge Corpus (MongoDB)")
            else:
                logger.info("No published documents found in Knowledge Corpus")
                
        except Exception as e:
            logger.error(f"Knowledge Corpus document query error: {e}")
            import traceback
            traceback.print_exc()
        
        # ===== 3. Format Response =====
        has_kc = len(results["knowledge_corpus"]["matches"]) > 0
        has_manual = len(results["user_manuals"]["chunks"]) > 0
        
        if has_kc and has_manual:
            # Both sources - show both
            response_html = _format_hybrid_response(
                results["knowledge_corpus"]["matches"],
                results["knowledge_corpus"]["sources"],
                results["user_manuals"]["chunks"],
                results["user_manuals"]["files"]
            )
            results["success"] = True
            results["intent"] = "Hybrid Query"
            
        elif has_kc:
            # Only Knowledge Corpus
            response_html = _format_kc_only_response(
                results["knowledge_corpus"]["matches"],
                results["knowledge_corpus"]["sources"]
            )
            results["success"] = True
            results["intent"] = "Knowledge Corpus Query"
            
        elif has_manual:
            # Only User Manuals
            response_html = _format_manual_only_response(
                results["user_manuals"]["chunks"],
                results["user_manuals"]["files"]
            )
            results["success"] = True
            results["intent"] = "User Manual Query"
            
        else:
            # No results
            response_html = _format_no_results(user_query)
            results["success"] = False
            results["intent"] = "No Results"
        
        results["response"] = response_html
        results["html"] = response_html
        
        return results
        
    except Exception as e:
        logger.error(f"Hybrid query error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "response": f"<div class='error-message'>Query error: {str(e)}</div>",
            "html": f"<div class='error-message'>Query error: {str(e)}</div>",
            "error": str(e)
        }


def _cosine_similarity(vec1: list, vec2: list) -> float:
    """Calculate cosine similarity"""
    try:
        if not vec1 or not vec2:
            return 0.0
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))
    except:
        return 0.0


def _format_hybrid_response(kc_matches: list, kc_sources: list, manual_chunks: list, manual_files: list) -> str:
    """Format response when both KC and manuals have results - Clean, muted design"""
    return f"""
<div class="hybrid-knowledge-response" style="font-family: 'Inter', -apple-system, sans-serif;">
    <div class="knowledge-section">
        <div class="section-header" style="background: #f8fafc; border-left: 3px solid #6366f1; color: #334155; padding: 12px 16px; border-radius: 6px; margin-bottom: 16px;">
            <i class="fas fa-book-open" style="color: #6366f1;"></i>
            <strong style="font-size: 14px; font-weight: 600;">Knowledge Base</strong>
        </div>
        {_format_kc_matches(kc_matches, kc_sources)}
    </div>
    
    <div class="manual-section" style="margin-top: 24px;">
        <div class="section-header" style="background: #f8fafc; border-left: 3px solid #10b981; color: #334155; padding: 12px 16px; border-radius: 6px; margin-bottom: 16px;">
            <i class="fas fa-file-pdf" style="color: #10b981;"></i>
            <strong style="font-size: 14px; font-weight: 600;">User Manuals</strong>
        </div>
        {_format_manual_chunks(manual_chunks, manual_files)}
    </div>
</div>
"""


def _format_kc_only_response(kc_matches: list, kc_sources: list) -> str:
    """Format response when only Knowledge Corpus has results - Clean design"""
    return f"""
<div class="kc-response" style="font-family: 'Inter', -apple-system, sans-serif;">
    <div class="source-info" style="background: #f8fafc; border-left: 3px solid #6366f1; padding: 12px 16px; margin-bottom: 16px; border-radius: 6px;">
        <i class="fas fa-book-open" style="color: #6366f1; margin-right: 8px;"></i>
        <span style="color: #64748b; font-size: 13px;"><strong style="color: #334155;">Source:</strong> Knowledge Base</span>
    </div>
    {_format_kc_matches(kc_matches, kc_sources)}
</div>
"""


def _format_manual_only_response(manual_chunks: list, manual_files: list) -> str:
    """Format response when only User Manuals have results - Clean design"""
    return f"""
<div class="manual-response" style="font-family: 'Inter', -apple-system, sans-serif;">
    <div class="source-info" style="background: #f8fafc; border-left: 3px solid #10b981; padding: 12px 16px; margin-bottom: 16px; border-radius: 6px;">
        <i class="fas fa-file-pdf" style="color: #10b981; margin-right: 8px;"></i>
        <span style="color: #64748b; font-size: 13px;"><strong style="color: #334155;">Source:</strong> User Manuals</span>
    </div>
    {_format_manual_chunks(manual_chunks, manual_files)}
</div>
"""


def _format_kc_matches(matches: list, sources: list) -> str:
    """Format Knowledge Corpus matches - Clean ChatGPT-style design with improved deduplication"""
    html = ""
    
    # Remove duplicates by answer content with similarity check
    unique_matches = []
    for match in matches[:5]:  # Check top 5 to find unique ones
        # Extract actual answer text from dict if present
        answer_text = ""
        if isinstance(match.get('answer'), dict):
            answer_text = match['answer'].get('draft_answer', '') or match['answer'].get('approved_answer', '') or str(match['answer'])
        else:
            answer_text = str(match.get('answer', ''))
        
        # Clean answer text - remove technical details
        if answer_text.startswith("{'"):
            try:
                import ast
                answer_dict = ast.literal_eval(answer_text)
                answer_text = answer_dict.get('draft_answer', answer_dict.get('approved_answer', answer_text))
            except:
                pass
        
        # Skip if empty
        if not answer_text or answer_text.strip() == "":
            continue
        
        # Check if this answer is too similar to existing ones
        is_duplicate = False
        answer_lower = answer_text.strip().lower()
        for existing_match, existing_text in unique_matches:
            existing_lower = existing_text.strip().lower()
            # Check for exact match or high similarity (>90% of words match)
            if answer_lower == existing_lower:
                is_duplicate = True
                break
            # Check if texts are very similar (word overlap)
            words1 = set(answer_lower.split())
            words2 = set(existing_lower.split())
            if words1 and words2:
                overlap = len(words1 & words2) / max(len(words1), len(words2))
                if overlap > 0.9:  # 90% word overlap
                    is_duplicate = True
                    break
        
        if not is_duplicate:
            unique_matches.append((match, answer_text))
            if len(unique_matches) >= 2:  # Only show top 2 unique answers
                break
    
    for i, (match, answer_text) in enumerate(unique_matches, 1):
        confidence = int(match.get('similarity', 0) * 100)
        
        html += f"""
<div class="qa-match" style="background: #ffffff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; margin-bottom: 12px;">
    <div class="match-question" style="margin-bottom: 12px; color: #1f2937; font-weight: 500; font-size: 14px; line-height: 1.6;">
        {match.get('question', 'No question available')}
    </div>
    <div class="match-answer" style="color: #374151; line-height: 1.7; font-size: 14px; padding: 12px; background: #f9fafb; border-radius: 6px; border-left: 3px solid #e5e7eb;">
        {answer_text if answer_text else 'No answer available'}
    </div>
    <div class="match-meta" style="margin-top: 12px; font-size: 12px; color: #94a3b8; display: flex; gap: 12px; align-items: center;">
        <span style="background: #f1f5f9; padding: 4px 10px; border-radius: 4px;">
            <i class="fas fa-check-circle" style="color: #6366f1;"></i> {confidence}%
        </span>
        <span><i class="fas fa-file" style="color: #94a3b8;"></i> {match.get('document_title', 'Unknown')}</span>
    </div>
</div>
"""
    
    if not unique_matches:
        html = '<div style="padding: 20px; text-align: center; color: #94a3b8;">No relevant information found</div>'
    
    return html


def _format_manual_chunks(chunks: list, files: list) -> str:
    """Format User Manual chunks - Clean design"""
    html = ""
    for i, chunk in enumerate(chunks[:3], 1):
        # Clean up empty chunks
        if not chunk or chunk.strip() == "":
            continue
            
        html += f"""
<div class="manual-chunk" style="background: #ffffff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; margin-bottom: 12px;">
    <div class="chunk-header" style="margin-bottom: 12px; padding-bottom: 10px; border-bottom: 1px solid #f1f5f9;">
        <span style="color: #64748b; font-size: 12px; font-weight: 500;">
            <i class="fas fa-file-pdf" style="color: #10b981;"></i> {files[min(i-1, len(files)-1)] if files else 'User Manual'}
        </span>
    </div>
    <div class="chunk-content" style="color: #374151; line-height: 1.7; font-size: 14px;">
        {chunk}
    </div>
</div>
"""
    
    if not html:
        html = '<div style="padding: 20px; text-align: center; color: #94a3b8;">No manual content available</div>'
    
    return html


def _format_no_results(user_query: str) -> str:
    """Format message when no results found"""
    return f"""
<div class="no-results" style="text-align: center; padding: 40px 20px; background: #fef3c7; border-radius: 12px; border: 2px dashed #f59e0b;">
    <div style="font-size: 3em; margin-bottom: 15px;">
        <i class="fas fa-search" style="color: #f59e0b;"></i>
    </div>
    <h3 style="color: #92400e; margin-bottom: 10px;">No matching information found</h3>
    <p style="color: #78350f; margin-bottom: 20px;">
        I couldn't find relevant information for: <strong>"{user_query[:100]}..."</strong>
    </p>
    <div style="background: white; padding: 20px; border-radius: 8px; text-align: left; max-width: 500px; margin: 0 auto;">
        <h4 style="color: #92400e; margin-bottom: 12px;">
            <i class="fas fa-lightbulb"></i> Try:
        </h4>
        <ul style="color: #78350f; list-style: none; padding: 0;">
            <li style="margin-bottom: 10px;">
                <i class="fas fa-upload" style="color: #10b981;"></i> Upload relevant manuals to the Knowledge Base
            </li>
            <li style="margin-bottom: 10px;">
                <i class="fas fa-edit" style="color: #3b82f6;"></i> Rephrase your question
            </li>
            <li style="margin-bottom: 10px;">
                <i class="fas fa-question-circle" style="color: #8b5cf6;"></i> Ask about specific topics covered in uploaded documents
            </li>
        </ul>
    </div>
</div>
"""
