"""
User Manuals and Knowledge Sources Routes
Handles user manuals upload, training, preview, testing, and knowledge source management.
"""

import os
import json
import uuid
import mimetypes
import tempfile
import logging
from datetime import datetime
from typing import Dict, Any, List

from flask import Flask, request, jsonify, session

logger = logging.getLogger(__name__)


def register_user_manuals_routes(
    app: Flask,
    timing_aspect,
    login_required,
    db,
    users_collection,
    kc_documents_collection,
    kc_pages_collection,
    kc_qa_pairs_collection,
    kc_embeddings_collection,
    user_manual_collection,
    chroma_client,
    get_chromadb_client,
    extract_text_from_file,
    read_pdf,
    split_text,
    get_embedding_azureRAG,
    openai_client,
    deployment_name,
    ALLOWED_EMAILS,
    ALLOWED_FILE_TYPES,
    UserRepository
):
    """
    Register user manuals and knowledge sources routes with the Flask app.
    
    Routes registered:
    - Admin Manual Upload: /api/admin/upload-manual (POST)
    - Admin Connect Repository: /api/admin/connect-repository (POST)
    - Admin Get Manuals: /api/admin/manuals (GET)
    - Repository Status: /api/repository-status (GET)
    - User Manuals: /api/user-manuals (GET), /api/user-manuals/<file_name> (DELETE)
    - Train User Manuals: /api/trainuser-manuals (POST)
    - Knowledge Sources: /api/knowledge-sources/all, /stats, /search
    - Manual Preview: /api/user-manual/preview (POST)
    - Manual Test Question: /api/user-manual/test-question (POST)
    - Manual Confirm Training: /api/user-manual/confirm-training (POST)
    
    Args:
        app: Flask application instance
        timing_aspect: Decorator for timing/logging
        login_required: Authentication decorator
        db: MongoDB database instance
        users_collection: Users MongoDB collection
        kc_documents_collection: Knowledge Corpus documents collection
        kc_pages_collection: Knowledge Corpus pages collection
        kc_qa_pairs_collection: Knowledge Corpus Q&A pairs collection
        kc_embeddings_collection: Knowledge Corpus embeddings collection
        user_manual_collection: ChromaDB user manual collection
        chroma_client: ChromaDB client instance
        get_chromadb_client: Function to get ChromaDB client
        extract_text_from_file: Function to extract text from files
        read_pdf: Function to read PDF files
        split_text: Function to split text into chunks
        get_embedding_azureRAG: Function to generate embeddings
        openai_client: OpenAI client for AI analysis
        deployment_name: OpenAI deployment name
        ALLOWED_EMAILS: List of admin emails
        ALLOWED_FILE_TYPES: List of allowed file types
        UserRepository: User repository for user lookups
    """

    # ==========================================================================
    # HELPER FUNCTIONS
    # ==========================================================================

    def get_user_manuals(user_id: str) -> Dict[str, Any]:
        """Get list of documents from Knowledge Corpus (MongoDB)."""
        try:
            documents = list(kc_documents_collection.find({
                "status": "published"
            }).sort("created_at", -1))

            manuals = []
            for doc in documents:
                doc.pop('_id', None)
                display_name = doc.get('file_name', 'Untitled Document')
                if 'synopsis' in doc and 'title' in doc['synopsis']:
                    display_name = doc['synopsis']['title']

                manuals.append({
                    'name': display_name,
                    'file_name': doc.get('file_name', ''),
                    'document_id': doc.get('document_id', ''),
                    'document_type': doc.get('synopsis', {}).get('document_type', 'Document'),
                    'created_at': doc.get('created_at', ''),
                    'uploaded_by': doc.get('uploaded_by', ''),
                    'total_pages': doc.get('total_pages', 0),
                    'word_count': doc.get('word_count', 0)
                })

            return {
                "success": True,
                "manuals": manuals,
                "count": len(manuals)
            }
        except Exception as e:
            logger.error(f"Error getting user manuals from Knowledge Corpus: {str(e)}")
            return {"success": False, "message": f"Error retrieving manuals: {str(e)}", "manuals": [], "count": 0}

    def delete_user_manual(user_id: str, file_name: str) -> Dict[str, Any]:
        """Delete a specific document from Knowledge Corpus (admin only)."""
        try:
            user = UserRepository.get_user_by_id(user_id) if user_id else None
            if not user:
                return {"success": False, "message": "User not found"}

            if user.get("email", "").lower() not in [e.lower() for e in ALLOWED_EMAILS]:
                return {"success": False, "message": "Access denied"}

            document = kc_documents_collection.find_one({"file_name": file_name})

            if document:
                document_id = document.get('document_id')
                kc_documents_collection.delete_one({"document_id": document_id})
                kc_pages_collection.delete_many({"document_id": document_id})
                kc_qa_pairs_collection.delete_many({"document_id": document_id})
                kc_embeddings_collection.delete_many({"document_id": document_id})

                logger.info(f"Deleted document '{file_name}' (ID: {document_id}) for user {user_id}")
                return {"success": True, "message": f"Manual '{file_name}' deleted successfully."}
            else:
                return {"success": False, "message": f"Manual '{file_name}' not found."}

        except Exception as e:
            logger.error(f"Error deleting user manual: {str(e)}")
            return {"success": False, "message": f"Error deleting manual: {str(e)}"}

    def analyze_document_with_ai(text: str, file_name: str) -> Dict[str, Any]:
        """Generate AI-powered analysis of the document"""
        try:
            analysis_prompt = f"""
            Analyze the following document content and provide a comprehensive analysis:

            Document: {file_name}
            Content: {text[:5000]}...

            Please provide:
            1. **Document Summary** (2-3 sentences)
            2. **Key Topics** (bullet points of main subjects)
            3. **Document Type** (manual, guide, policy, etc.)
            4. **Target Audience** (who would use this document)
            5. **Content Quality** (structure, completeness, clarity rating 1-10)
            6. **Recommended Use Cases** (when/how to use this document)

            Format your response as JSON:
            {{
                "summary": "Brief summary...",
                "key_topics": ["Topic 1", "Topic 2", "Topic 3"],
                "document_type": "User Manual",
                "target_audience": "End users, administrators",
                "quality_rating": 8,
                "quality_notes": "Well structured with clear sections",
                "use_cases": ["User onboarding", "Troubleshooting", "Reference"],
                "word_count": {len(text.split())},
                "estimated_chunks": {len(split_text(text, 500))},
                "chunk_size": 500,
                "total_characters": {len(text)},
                "processing_complexity": "Simple/Medium/Complex based on content structure"
            }}
            """

            response = openai_client.ChatCompletion.create(
                engine=deployment_name,
                messages=[
                    {"role": "system", "content": "You are a document analysis expert. Provide detailed, accurate analysis of documents."},
                    {"role": "user", "content": analysis_prompt}
                ],
                temperature=0.1,
                seed=12345,
                top_p=0.1,
                frequency_penalty=0,
                presence_penalty=0,
                response_format={"type": "json_object"}
            )

            result = response.choices[0].message.content.strip()

            try:
                analysis = json.loads(result)
            except json.JSONDecodeError:
                words = text.split()
                actual_chunks = split_text(text, 500)
                analysis = {
                    "summary": "Document analysis completed",
                    "key_topics": ["General content"],
                    "document_type": "Document",
                    "target_audience": "Users",
                    "quality_rating": 7,
                    "quality_notes": "Analysis completed",
                    "use_cases": ["Reference"],
                    "word_count": len(words),
                    "estimated_chunks": len(actual_chunks),
                    "chunk_size": 500,
                    "total_characters": len(text)
                }

            return analysis

        except Exception as e:
            logger.error(f"Error in AI analysis: {e}")
            if text:
                words = text.split()
                actual_chunks = split_text(text, 500)
                return {
                    "summary": "Unable to generate AI analysis",
                    "key_topics": ["Content analysis unavailable"],
                    "document_type": "Unknown",
                    "target_audience": "Users",
                    "quality_rating": 5,
                    "quality_notes": f"Analysis error: {str(e)}",
                    "use_cases": ["Reference"],
                    "word_count": len(words),
                    "estimated_chunks": len(actual_chunks),
                    "chunk_size": 500,
                    "total_characters": len(text)
                }
            else:
                return {
                    "summary": "Unable to generate AI analysis",
                    "key_topics": ["Content analysis unavailable"],
                    "document_type": "Unknown",
                    "target_audience": "Users",
                    "quality_rating": 5,
                    "quality_notes": f"Analysis error: {str(e)}",
                    "use_cases": ["Reference"],
                    "word_count": 0,
                    "estimated_chunks": 0,
                    "chunk_size": 500,
                    "total_characters": 0
                }

    def generate_test_questions(text: str, file_name: str, num_questions: int = 5) -> List[Dict[str, str]]:
        """Generate test questions based on document content"""
        try:
            questions_prompt = f"""
            Based on the following document content, generate {num_questions} relevant questions that users might ask:

            Document: {file_name}
            Content: {text[:3000]}...

            Generate questions that:
            1. Test understanding of key concepts
            2. Cover different sections of the document
            3. Include both specific and general queries
            4. Are practical for real users

            Format as JSON array:
            [
                {{"question": "How do I...?", "category": "How-to", "difficulty": "Basic"}},
                {{"question": "What is...?", "category": "Definition", "difficulty": "Basic"}},
                ...
            ]
            """

            response = openai_client.ChatCompletion.create(
                engine=deployment_name,
                messages=[
                    {"role": "system", "content": "You are an expert at creating relevant test questions for documents."},
                    {"role": "user", "content": questions_prompt}
                ],
                temperature=0.3,
                seed=12345,
                top_p=0.1,
                frequency_penalty=0,
                presence_penalty=0,
                response_format={"type": "json_object"}
            )

            result = response.choices[0].message.content.strip()

            try:
                questions = json.loads(result)
                if isinstance(questions, list):
                    return questions[:num_questions]
            except json.JSONDecodeError:
                pass

            return [
                {"question": f"What is the main purpose of {file_name}?", "category": "Overview", "difficulty": "Basic"},
                {"question": f"How can I use the information in {file_name}?", "category": "Usage", "difficulty": "Basic"},
                {"question": f"What are the key sections covered in {file_name}?", "category": "Structure", "difficulty": "Basic"}
            ]

        except Exception as e:
            logger.error(f"Error generating test questions: {e}")
            return [
                {"question": "What does this document cover?", "category": "General", "difficulty": "Basic"},
                {"question": "How can I use this information?", "category": "Usage", "difficulty": "Basic"}
            ]

    # ==========================================================================
    # ADMIN MANUAL UPLOAD ROUTES
    # ==========================================================================

    @app.route('/api/admin/upload-manual', methods=['POST'])
    @login_required
    @timing_aspect
    def admin_upload_manual():
        """Upload user manuals (admin only)"""
        try:
            user_id = session.get('user_id')
            user = users_collection.find_one({'_id': user_id})

            email = user.get('email', '') if user else ''
            if email.lower() not in [e.lower() for e in ALLOWED_EMAILS]:
                return jsonify({'success': False, 'message': 'Access denied'}), 403

            if 'file' not in request.files:
                return jsonify({'success': False, 'message': 'No file provided'}), 400

            file = request.files['file']
            if file.filename == '':
                return jsonify({'success': False, 'message': 'No file selected'}), 400

            manual_name = file.filename
            manual_type = request.form.get('type', 'general')

            manuals_dir = os.path.join('app', 'manuals')
            os.makedirs(manuals_dir, exist_ok=True)

            file_path = os.path.join(manuals_dir, manual_name)
            file.save(file_path)

            if chroma_client:
                try:
                    text_data = extract_text_from_file(file_path, mimetypes.guess_type(file_path)[0])
                    collection = chroma_client.get_or_create_collection(name="user_manuals")
                    collection.add(
                        documents=[text_data.get('text_data', '')],
                        metadatas=[{
                            'filename': manual_name,
                            'type': manual_type,
                            'uploaded_by': user.get('email', ''),
                            'uploaded_at': datetime.utcnow().isoformat()
                        }],
                        ids=[f"manual_{uuid.uuid4().hex}"]
                    )
                    logger.info(f"Manual {manual_name} indexed in ChromaDB")
                except Exception as e:
                    logger.error(f"Error indexing manual in ChromaDB: {e}")

            db.manuals.insert_one({
                'name': manual_name,
                'type': manual_type,
                'path': file_path,
                'uploaded_by': user_id,
                'uploaded_at': datetime.utcnow(),
                'is_active': True
            })

            return jsonify({
                'success': True,
                'message': 'Manual uploaded successfully',
                'manual': {'name': manual_name, 'type': manual_type}
            }), 200

        except Exception as e:
            logger.error(f"Error uploading manual: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/admin/connect-repository', methods=['POST'])
    @login_required
    @timing_aspect
    def admin_connect_repository():
        """Connect to external repository (admin only)"""
        try:
            user_id = session.get('user_id')
            user = users_collection.find_one({'_id': user_id})

            email = user.get('email', '') if user else ''
            if email.lower() not in [e.lower() for e in ALLOWED_EMAILS]:
                return jsonify({'success': False, 'message': 'Access denied'}), 403

            data = request.get_json()
            repo_type = data.get('type', 'chromadb')
            repo_config = data.get('config', {})

            if repo_type == 'chromadb':
                host = repo_config.get('host', 'localhost')
                port = repo_config.get('port', 8000)

                try:
                    test_client = get_chromadb_client(host=host, port=port)
                    test_client.list_collections()

                    db.repository_config.update_one(
                        {'type': repo_type},
                        {
                            '$set': {
                                'host': host,
                                'port': port,
                                'connected_by': user_id,
                                'connected_at': datetime.utcnow(),
                                'is_active': True
                            }
                        },
                        upsert=True
                    )

                    return jsonify({
                        'success': True,
                        'message': f'Successfully connected to {repo_type} repository',
                        'repository': {'type': repo_type, 'host': host, 'port': port}
                    }), 200

                except Exception as e:
                    return jsonify({
                        'success': False,
                        'message': f'Failed to connect to repository: {str(e)}'
                    }), 400
            else:
                return jsonify({
                    'success': False,
                    'message': f'Unsupported repository type: {repo_type}'
                }), 400

        except Exception as e:
            logger.error(f"Error connecting repository: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/admin/manuals', methods=['GET'])
    @login_required
    @timing_aspect
    def get_manuals():
        """Get list of available manuals"""
        try:
            user_id = session.get('user_id')
            user = users_collection.find_one({'_id': user_id})

            is_allowed = user and user.get('email', '').lower() in [e.lower() for e in ALLOWED_EMAILS]

            query = {'is_active': True} if not is_allowed else {}
            manuals = list(db.manuals.find(query, {'_id': 0, 'path': 0}))

            for manual in manuals:
                if 'uploaded_at' in manual:
                    manual['uploaded_at'] = manual['uploaded_at'].isoformat()

            return jsonify({
                'success': True,
                'manuals': manuals,
                'is_allowed': is_allowed
            }), 200

        except Exception as e:
            logger.error(f"Error fetching manuals: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/repository-status', methods=['GET'])
    @login_required
    @timing_aspect
    def get_repository_status():
        """Get current repository connection status"""
        try:
            repo_config = db.repository_config.find_one({'is_active': True})

            if repo_config:
                return jsonify({
                    'success': True,
                    'connected': True,
                    'repository': {
                        'type': repo_config.get('type'),
                        'host': repo_config.get('host'),
                        'port': repo_config.get('port'),
                        'connected_at': repo_config.get('connected_at').isoformat() if repo_config.get('connected_at') else None
                    }
                }), 200
            else:
                return jsonify({
                    'success': True,
                    'connected': False,
                    'repository': None
                }), 200

        except Exception as e:
            logger.error(f"Error getting repository status: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    # ==========================================================================
    # USER MANUALS API ROUTES
    # ==========================================================================

    @app.route('/api/user-manuals', methods=['GET'])
    def api_get_user_manuals():
        """API endpoint to get list of user manuals."""
        user_id = session.get('user_id') or request.args.get('user_id')
        if not user_id:
            return jsonify({"success": False, "message": "User not authenticated", "manuals": [], "count": 0}), 401
        result = get_user_manuals(user_id)
        return jsonify(result), 200 if result["success"] else 500

    @app.route('/api/user-manuals/<file_name>', methods=['DELETE'])
    def api_delete_user_manual(file_name):
        """API endpoint to delete a user manual."""
        user_id = session.get('user_id') or request.args.get('user_id')

        if not user_id and request.is_json:
            data = request.get_json()
            user_id = data.get('user_id') if data else None

        if not user_id:
            return jsonify({"success": False, "message": "User not authenticated"}), 401

        result = delete_user_manual(user_id, file_name)
        return jsonify(result), 200 if result["success"] else 404

    # ==========================================================================
    # KNOWLEDGE SOURCES API ROUTES
    # ==========================================================================

    @app.route('/api/knowledge-sources/all', methods=['GET'])
    def api_get_all_knowledge_sources():
        """Get ALL knowledge sources (Knowledge Corpus + User Manuals)."""
        try:
            from app.utils.unified_knowledge_sources import get_all_knowledge_sources

            user_id = session.get('user_id') or request.args.get('user_id') or 'dev-user'
            result = get_all_knowledge_sources(user_id)

            return jsonify(result), 200

        except Exception as e:
            logger.error(f"Error in api_get_all_knowledge_sources: {e}")
            return jsonify({
                "success": False,
                "error": str(e),
                "sources": [],
                "knowledge_corpus": {"count": 0, "documents": []},
                "user_manuals": {"count": 0, "files": []}
            }), 500

    @app.route('/api/knowledge-sources/stats', methods=['GET'])
    def api_get_knowledge_source_stats():
        """Get statistics for all knowledge sources."""
        try:
            from app.utils.unified_knowledge_sources import get_knowledge_source_stats

            stats = get_knowledge_source_stats()
            return jsonify(stats), 200

        except Exception as e:
            logger.error(f"Error in api_get_knowledge_source_stats: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/api/knowledge-sources/search', methods=['POST'])
    def api_search_knowledge_sources():
        """Search across ALL knowledge sources (KC + Manuals)."""
        try:
            from app.utils.unified_knowledge_sources import search_all_knowledge_sources

            data = request.get_json()
            query = data.get('query', '')
            user_id = session.get('user_id') or data.get('user_id', 'dev-user')
            source_types = data.get('source_types')
            limit = data.get('limit', 10)

            if not query:
                return jsonify({"success": False, "error": "Query is required"}), 400

            result = search_all_knowledge_sources(query, user_id, source_types, limit)
            return jsonify(result), 200

        except Exception as e:
            logger.error(f"Error in api_search_knowledge_sources: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    # ==========================================================================
    # MANUAL PREVIEW AND TRAINING ROUTES
    # ==========================================================================

    @app.route('/api/user-manual/preview', methods=['POST'])
    def preview_user_manual():
        """Preview and analyze uploaded document before training"""
        try:
            is_development = app.debug
            user_id = session.get('user_id') or request.form.get('user_id') or 'dev-user'

            if not is_development:
                if not user_id or user_id == 'dev-user':
                    return jsonify({"success": False, "message": "Authentication required"}), 401

                user = UserRepository.get_user_by_id(user_id)
                if not user:
                    return jsonify({"success": False, "message": "User not found"}), 404

                if user.get("email", "").lower() not in [e.lower() for e in ALLOWED_EMAILS]:
                    return jsonify({"success": False, "message": "Admin access required"}), 403

            uploaded_file = request.files.get('file')
            if not uploaded_file:
                return jsonify({"success": False, "message": "No file uploaded"}), 400

            file_type = uploaded_file.content_type
            file_name = uploaded_file.filename

            if file_type not in ALLOWED_FILE_TYPES:
                return jsonify({
                    "success": False,
                    "message": f"Unsupported file type: {file_type}"
                }), 400

            temp_file_path = None
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_name.split('.')[-1]}") as temp_file:
                    temp_file_path = temp_file.name
                    uploaded_file.save(temp_file_path)

                text = None
                if file_type == "application/pdf":
                    text = read_pdf(temp_file_path)
                    if text is None:
                        extracted_data = extract_text_from_file(temp_file_path, "application/pdf")
                        text = " ".join([entry["text"] for entry in extracted_data.get("text_data", [])])
                else:
                    extracted_data = extract_text_from_file(temp_file_path, file_type)
                    text = " ".join([entry["text"] for entry in extracted_data.get("text_data", [])])

                if not text or not text.strip():
                    return jsonify({
                        "success": False,
                        "message": "No text extracted from file. File may be encrypted or image-based."
                    }), 400

                ai_analysis = analyze_document_with_ai(text, file_name)
                test_questions = generate_test_questions(text, file_name)

                text_preview = text[:1000] + "..." if len(text) > 1000 else text
                words = text.split()
                word_count = len(words)
                character_count = len(text)

                chunk_size = 500
                actual_chunks = split_text(text, chunk_size)
                actual_chunk_count = len(actual_chunks)

                chunk_stats = []
                for i, chunk in enumerate(actual_chunks):
                    chunk_words = len(chunk.split())
                    chunk_chars = len(chunk)
                    chunk_stats.append({
                        "chunk_number": i + 1,
                        "word_count": chunk_words,
                        "character_count": chunk_chars,
                        "preview": chunk[:100] + "..." if len(chunk) > 100 else chunk
                    })

                estimated_storage_mb = character_count / (1024 * 1024)

                response_data = {
                    "success": True,
                    "preview": {
                        "file_name": file_name,
                        "file_type": file_type,
                        "file_size_bytes": character_count,
                        "file_size_mb": round(estimated_storage_mb, 3),
                        "text_preview": text_preview,
                        "full_text": text,
                        "word_count": word_count,
                        "character_count": character_count,
                        "estimated_chunks": actual_chunk_count,
                        "chunk_size_words": chunk_size,
                        "chunking_details": {
                            "total_chunks": actual_chunk_count,
                            "words_per_chunk": chunk_size,
                            "average_chars_per_chunk": character_count // actual_chunk_count if actual_chunk_count > 0 else 0,
                            "chunk_breakdown": chunk_stats[:5] if len(chunk_stats) > 5 else chunk_stats,
                            "total_chunks_shown": min(5, len(chunk_stats)),
                            "remaining_chunks": max(0, len(chunk_stats) - 5)
                        },
                        "extracted_successfully": True
                    },
                    "ai_analysis": ai_analysis,
                    "test_questions": test_questions,
                    "ready_for_training": True
                }

                logger.info(f"Document preview generated for {file_name} by user {user_id}")
                return jsonify(response_data)

            finally:
                if temp_file_path and os.path.exists(temp_file_path):
                    try:
                        os.unlink(temp_file_path)
                    except OSError:
                        pass

        except Exception as e:
            logger.error(f"Error in document preview: {e}")
            return jsonify({
                "success": False,
                "message": f"Error processing document: {str(e)}"
            }), 500

    @app.route('/api/user-manual/test-question', methods=['POST'])
    def test_manual_question():
        """Test a question against the document content before training"""
        try:
            data = request.get_json()
            question = data.get('question', '').strip()
            document_text = data.get('document_text', '')

            if not question or not document_text:
                return jsonify({
                    "success": False,
                    "message": "Question and document text are required"
                }), 400

            content_length = len(document_text)
            content_to_use = document_text[:16000] if content_length > 16000 else document_text

            logger.info(f"Testing question: '{question}' against document with {content_length} characters")

            answer_prompt = f"""
            You are an expert document analyst. Analyze the provided document content and answer the user's question.

            DOCUMENT CONTENT ({content_length} total characters, showing first {len(content_to_use)}):
            {content_to_use}
            {"..." if content_length > 16000 else ""}

            USER QUESTION: {question}

            ANALYSIS INSTRUCTIONS:
            1. Carefully search through the entire provided document content
            2. Look for direct mentions, related concepts, or contextual clues
            3. If you find relevant information, provide a comprehensive answer with specific details
            4. If you find partial information, mention what you found and note what's missing
            5. Only say "This information is not available in the document" if you genuinely cannot find ANY related content
            6. Include specific quotes or references from the document when possible

            ANSWER:
            """

            response = openai_client.ChatCompletion.create(
                engine=deployment_name,
                messages=[
                    {"role": "system", "content": "You are an expert document analyst specializing in finding and extracting information from documents."},
                    {"role": "user", "content": answer_prompt}
                ],
                temperature=0.0,
                seed=12345,
                top_p=0.1,
                frequency_penalty=0,
                presence_penalty=0,
            )

            answer = response.choices[0].message.content.strip()

            return jsonify({
                "success": True,
                "question": question,
                "answer": answer,
                "source": "Document preview (not yet trained)",
                "debug_info": {
                    "content_length": content_length,
                    "content_used": len(content_to_use),
                    "question_length": len(question)
                }
            })

        except Exception as e:
            logger.error(f"Error testing question: {e}")
            return jsonify({
                "success": False,
                "message": f"Error processing question: {str(e)}"
            }), 500

    @app.route('/api/user-manual/confirm-training', methods=['POST'])
    def confirm_manual_training():
        """Confirm and proceed with manual training after preview"""
        try:
            data = request.get_json()
            file_name = data.get('file_name')
            confirmed = data.get('confirmed', False)

            if not confirmed:
                return jsonify({
                    "success": False,
                    "message": "User confirmation required"
                }), 400

            is_development = app.debug
            user_id = session.get('user_id') or 'dev-user'

            if not is_development:
                if not user_id or user_id == 'dev-user':
                    return jsonify({"success": False, "message": "Authentication required"}), 401

            document_text = data.get('document_text', '')
            ai_analysis = data.get('ai_analysis', {})

            if not document_text:
                return jsonify({
                    "success": False,
                    "message": "Document text is required for training"
                }), 400

            logger.info(f"Starting actual training for {file_name} by user {user_id}")

            try:
                text_chunks = split_text(document_text, chunk_size=500)
                if not text_chunks:
                    return jsonify({
                        "success": False,
                        "message": "No valid text chunks extracted for storage"
                    }), 400

                chunk_ids = [f"global_{file_name}_{i}" for i in range(len(text_chunks))]
                metadata = [{
                    "file_name": file_name,
                    "chunk_index": i,
                    "is_global": True,
                    "uploaded_by": user_id,
                    "uploaded_by_admin": True,
                    "training_date": str(datetime.now()),
                    "document_type": ai_analysis.get('document_type', 'Document'),
                    "quality_rating": ai_analysis.get('quality_rating', 8)
                } for i in range(len(text_chunks))]

                embeddings = []
                for chunk in text_chunks:
                    embedding = get_embedding_azureRAG(chunk)
                    embeddings.append(embedding)

                user_manual_collection.add(
                    documents=text_chunks,
                    metadatas=metadata,
                    embeddings=embeddings,
                    ids=chunk_ids
                )

                actual_chunk_count = len(text_chunks)
                word_count = len(document_text.split())
                character_count = len(document_text)

                logger.info(f"Successfully trained user manual '{file_name}' with {actual_chunk_count} chunks in ChromaDB")

                return jsonify({
                    "success": True,
                    "message": f"Manual '{file_name}' has been successfully trained and stored!",
                    "training_status": "completed",
                    "storage_location": "ChromaDB Collection: 'user_manual'",
                    "storage_details": {
                        "database": "ChromaDB",
                        "collection": "user_manual",
                        "host": "localhost:8000",
                        "chunks_stored": actual_chunk_count,
                        "embeddings_generated": len(embeddings),
                        "storage_type": "global_access"
                    },
                    "training_summary": {
                        "document": file_name,
                        "document_type": ai_analysis.get('document_type', 'Document'),
                        "quality_rating": f"{ai_analysis.get('quality_rating', 8)}/10",
                        "total_chunks": actual_chunk_count,
                        "chunk_size": "500 words per chunk",
                        "chunk_size_words": 500,
                        "total_words": word_count,
                        "total_characters": character_count,
                        "processing_details": {
                            "chunks_created": actual_chunk_count,
                            "words_per_chunk": 500,
                            "average_chunk_size": f"{character_count // actual_chunk_count if actual_chunk_count > 0 else 0} characters",
                            "processing_completed": True,
                            "embeddings_stored": len(embeddings)
                        }
                    }
                })

            except Exception as storage_error:
                logger.error(f"Error storing manual in ChromaDB: {storage_error}")
                return jsonify({
                    "success": False,
                    "message": f"Error storing manual: {str(storage_error)}"
                }), 500

        except Exception as e:
            logger.error(f"Error in confirm training: {e}")
            return jsonify({
                "success": False,
                "message": f"Error confirming training: {str(e)}"
            }), 500

    # ==========================================================================
    # TRADE DOCUMENTS ROUTE
    # ==========================================================================

    # Global variable for trade document elements
    trade_document_elements = None

    def load_trade_document_elements():
        """Load the trade document data elements mapping from JSON file"""
        nonlocal trade_document_elements
        try:
            elements_path = os.path.join(app.root_path, 'prompts', 'trade_document_data_elements.json')
            with open(elements_path, 'r', encoding='utf-8') as f:
                trade_document_elements = json.load(f)
            logger.info("SUCCESS: Trade document data elements mapping loaded successfully")
            return trade_document_elements
        except Exception as e:
            logger.error(f"ERROR: Error loading trade document data elements: {str(e)}")
            return None

    @app.route('/api/trade-documents', methods=['GET'])
    @timing_aspect
    def get_trade_documents():
        """Get list of all available trade document types"""
        nonlocal trade_document_elements
        try:
            logger.info("📋 Trade documents API called")

            # Try to load trade document elements
            if not trade_document_elements:
                logger.info("📋 Loading trade document elements...")
                load_trade_document_elements()

            if not trade_document_elements:
                logger.warning("📋 Trade document elements not loaded, returning fallback data")
                # Return fallback data if the JSON file is not available
                fallback_documents = [
                    {
                        "name": "Commercial Invoice",
                        "code": "INV",
                        "description": "Commercial invoice document"
                    },
                    {
                        "name": "Letter of Credit",
                        "code": "LC",
                        "description": "Letter of credit document"
                    },
                    {
                        "name": "Bill of Lading",
                        "code": "BL",
                        "description": "Bill of lading document"
                    }
                ]
                return jsonify({
                    'success': True,
                    'documents': fallback_documents,
                    'count': len(fallback_documents),
                    'message': 'Using fallback document data'
                }), 200

            documents = trade_document_elements.get('documents', [])
            logger.info(f"📋 Returning {len(documents)} trade documents")
            return jsonify({
                'success': True,
                'documents': documents,
                'count': len(documents)
            }), 200

        except Exception as e:
            logger.error(f"Error getting trade documents: {e}")
            # Return fallback even on error
            fallback_documents = [
                {
                    "name": "Document Classification",
                    "code": "DOC",
                    "description": "Generic document for classification"
                }
            ]
            return jsonify({
                'success': True,
                'documents': fallback_documents,
                'count': len(fallback_documents),
                'error': str(e),
                'message': 'Using fallback due to error'
            }), 200

    logger.info("✅ User Manuals and Knowledge Sources routes registered successfully")
