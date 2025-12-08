"""
User Manuals and Knowledge Sources Module
==========================================

This module provides comprehensive user manual and knowledge source management
functionality including upload, training, preview, testing, and search.

Key Components:
- Admin manual upload and repository management
- User manual CRUD operations
- Knowledge sources unified API
- Manual preview and AI analysis
- Manual training with ChromaDB storage

Usage:
    from app.backend.User_Manuals_And_Knowledge import register_user_manuals_routes
    
    register_user_manuals_routes(
        app=app,
        timing_aspect=timing_aspect,
        login_required=login_required,
        db=db,
        users_collection=users_collection,
        kc_documents_collection=kc_documents_collection,
        kc_pages_collection=kc_pages_collection,
        kc_qa_pairs_collection=kc_qa_pairs_collection,
        kc_embeddings_collection=kc_embeddings_collection,
        user_manual_collection=user_manual_collection,
        chroma_client=chroma_client,
        get_chromadb_client=get_chromadb_client,
        extract_text_from_file=extract_text_from_file,
        read_pdf=read_pdf,
        split_text=split_text,
        get_embedding_azureRAG=get_embedding_azureRAG,
        openai_client=openai,
        deployment_name=deployment_name,
        ALLOWED_EMAILS=ALLOWED_EMAILS,
        ALLOWED_FILE_TYPES=ALLOWED_FILE_TYPES,
        UserRepository=UserRepository
    )
"""

import logging

logger = logging.getLogger(__name__)

# Import route registration
from .user_manuals_routes import register_user_manuals_routes

# Export all components
__all__ = [
    'register_user_manuals_routes'
]

logger.info("✅ User Manuals and Knowledge Sources module initialized")
