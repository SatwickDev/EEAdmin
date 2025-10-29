"""
Knowledge Corpus API Routes
Handles document ingestion, Q&A generation, approval workflow, and semantic search.
"""
from __future__ import annotations

import os
import json
import uuid
import tempfile
from datetime import datetime
from typing import Any, Dict, List, Optional
from difflib import SequenceMatcher
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from flask import request, jsonify, session, current_app
from flask_login import login_required, current_user
from flask_socketio import emit
from werkzeug.utils import secure_filename
import openai
from PyPDF2 import PdfReader
from PIL import Image
import io
import base64

# Import MongoDB collections (will be passed from routes.py)
kc_documents_collection = None
kc_pages_collection = None
kc_qa_pairs_collection = None
kc_embeddings_collection = None
kc_user_queries_collection = None
kc_audit_log_collection = None

# Import utility functions (will be set from routes.py)
get_embedding_azureRAG = None
extract_text_from_file = None
read_pdf = None
split_text = None
deployment_name = None
logger = None
ALLOWED_EMAILS = None


def init_knowledge_corpus_routes(app, collections, utils):
    """Initialize Knowledge Corpus routes with dependencies"""
    global kc_documents_collection, kc_pages_collection, kc_qa_pairs_collection
    global kc_embeddings_collection, kc_user_queries_collection, kc_audit_log_collection
    global get_embedding_azureRAG, extract_text_from_file, read_pdf, split_text
    global deployment_name, logger, ALLOWED_EMAILS
    
    # Set collections
    kc_documents_collection = collections['documents']
    kc_pages_collection = collections['pages']
    kc_qa_pairs_collection = collections['qa_pairs']
    kc_embeddings_collection = collections['embeddings']
    kc_user_queries_collection = collections['user_queries']
    kc_audit_log_collection = collections['audit_log']
    
    # Set utility functions
    get_embedding_azureRAG = utils['get_embedding']
    extract_text_from_file = utils['extract_text']
    read_pdf = utils['read_pdf']
    split_text = utils['split_text']
    deployment_name = utils['deployment_name']
    logger = utils['logger']
    ALLOWED_EMAILS = utils['allowed_emails']
    
    # Register routes
    register_document_routes(app)
    register_qa_routes(app)
    register_search_routes(app)
    register_approval_routes(app)
    register_analytics_routes(app)


# ============================================================================
# Helper Functions
# ============================================================================

def check_admin_access(user_id):
    """Check if user has admin access"""
    from app.routes import UserRepository
    user = UserRepository.get_user_by_id(user_id)
    if not user:
        return False
    return user.get("email", "").lower() in [e.lower() for e in ALLOWED_EMAILS]


def log_audit(action_type, entity_type, entity_id, user_id, changes=None):
    """Log an audit entry"""
    try:
        from app.routes import UserRepository
        
        # Handle test_admin or invalid user IDs gracefully
        user_email = "unknown"
        if user_id and user_id != 'test_admin':
            try:
                user = UserRepository.get_user_by_id(user_id)
                user_email = user.get("email", "unknown") if user else "unknown"
            except Exception as e:
                logger.warning(f"Could not fetch user email for user_id {user_id}: {e}")
                user_email = "unknown"
        elif user_id == 'test_admin':
            user_email = "test_admin@system.local"
        
        audit_entry = {
            "log_id": str(uuid.uuid4()),
            "action_type": action_type,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "user_id": user_id,
            "user_email": user_email,
            "changes": changes or {},
            "timestamp": datetime.utcnow(),
            "ip_address": request.remote_addr,
            "user_agent": request.headers.get('User-Agent', 'unknown')
        }
        kc_audit_log_collection.insert_one(audit_entry)
    except Exception as e:
        logger.error(f"Failed to log audit: {e}")


def generate_page_thumbnail(page_content, page_number):
    """Generate thumbnail for a page (simplified version)"""
    # For now, return a placeholder. In production, use PDF rendering library
    return {
        "stored": False,
        "preview": None,
        "width": 200,
        "height": 260
    }


def extract_pdf_pages(file_path):
    """Extract text from PDF page by page"""
    pages = []
    try:
        logger.info(f"Starting PDF extraction from: {file_path}")
        reader = PdfReader(file_path)
        total_pages = len(reader.pages)
        logger.info(f"PDF has {total_pages} pages")
        
        for i, page in enumerate(reader.pages):
            try:
                page_text = page.extract_text()
                logger.info(f"Page {i+1}: Extracted {len(page_text)} characters")
                
                if page_text and page_text.strip():  # Check if text is not empty
                    pages.append({
                        "page_number": i + 1,
                        "text": page_text,
                        "word_count": len(page_text.split()),
                        "character_count": len(page_text)
                    })
                else:
                    logger.warning(f"Page {i+1}: No text extracted (might be image-only)")
            except Exception as page_error:
                logger.error(f"Error extracting page {i+1}: {page_error}")
                continue
        
        logger.info(f"Successfully extracted text from {len(pages)} out of {total_pages} pages")
    except Exception as e:
        logger.error(f"Error extracting PDF pages: {e}")
        import traceback
        traceback.print_exc()
    
    return pages


def generate_synopsis_with_ai(text, file_name):
    """Generate document synopsis using AI"""
    try:
        # Configure OpenAI for Azure
        azure_key = os.getenv('AZURE_OPENAI_API_KEY')
        azure_base = os.getenv('AZURE_OPENAI_API_BASE')
        azure_version = os.getenv('AZURE_OPENAI_VERSION', '2023-12-01-preview')
        
        if azure_key and azure_base:
            openai.api_type = "azure"
            openai.api_key = azure_key
            openai.api_base = azure_base
            openai.api_version = azure_version
        
        prompt = f"""
Analyze this document and create a comprehensive synopsis.

Document: {file_name}
Content: {text[:8000]}...

Provide a JSON response with:
{{
    "title": "Short descriptive title",
    "summary_bullets": ["4-8 key points about the document"],
    "enables_queries": "What kinds of questions users can ask (2-3 sentences)",
    "tone_setting": "professional|friendly|formal|terse",
    "document_type": "User Manual|Guide|Policy|Reference|etc",
    "target_audience": "Who would use this document",
    "key_topics": ["main", "topics", "covered"]
}}
"""
        
        response = openai.ChatCompletion.create(
            engine=deployment_name,
            messages=[
                {"role": "system", "content": "You are a document analysis expert. Provide accurate, structured synopsis in JSON format."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )
        
        result = response.choices[0].message.content.strip()
        
        # Handle markdown-wrapped JSON (```json ... ```)
        if result.startswith('```'):
            logger.info("Detected markdown-wrapped JSON response, extracting...")
            # Remove ```json or ``` at start and ``` at end
            result = result.split('```')[1]
            if result.startswith('json'):
                result = result[4:].strip()
            result = result.strip()
        
        logger.info(f"Synopsis API response (first 200 chars): {result[:200]}")
        synopsis = json.loads(result)
        return synopsis
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error in synopsis generation: {e}")
        logger.error(f"Raw response: {result if 'result' in locals() else 'No response'}")
        import traceback
        traceback.print_exc()
        return {
            "title": file_name,
            "summary_bullets": ["Document uploaded and ready for analysis"],
            "enables_queries": "Users can ask questions about the content of this document.",
            "tone_setting": "professional",
            "document_type": "Document",
            "target_audience": "General users",
            "key_topics": ["General content"]
        }
    except Exception as e:
        logger.error(f"Error generating synopsis: {e}")
        return {
            "title": file_name,
            "summary_bullets": ["Document uploaded and ready for analysis"],
            "enables_queries": "Users can ask questions about the content of this document.",
            "tone_setting": "professional",
            "document_type": "Document",
            "target_audience": "General users",
            "key_topics": ["General content"]
        }


def generate_questions_for_page(page_text, page_number, num_questions=4):
    """Generate questions for a page"""
    try:
        # Configure OpenAI for Azure
        azure_key = os.getenv('AZURE_OPENAI_API_KEY')
        azure_base = os.getenv('AZURE_OPENAI_API_BASE')
        azure_version = os.getenv('AZURE_OPENAI_VERSION', '2024-08-01-preview')
        
        if azure_key and azure_base:
            openai.api_type = "azure"
            openai.api_key = azure_key
            openai.api_base = azure_base
            openai.api_version = azure_version
            
            logger.info(f"OpenAI configured - Base: {azure_base}, Version: {azure_version}, Deployment: {deployment_name}")
            logger.info(f"API Key starts with: {azure_key[:10]}...")
        else:
            logger.error(f"Azure OpenAI config missing - Key: {bool(azure_key)}, Base: {azure_base}")
        
        prompt = f"""
Based on this page content, generate {num_questions} relevant questions that users might ask.

Page {page_number}:
{page_text[:3000]}

Generate practical questions that:
1. Cover key information on this page
2. Are clear and specific
3. Would be asked by actual users
4. Vary in complexity

Return JSON array:
[
    {{"question": "Question text here?", "difficulty": "basic|intermediate|advanced"}},
    ...
]
"""
        
        response = openai.ChatCompletion.create(
            engine=deployment_name,
            messages=[
                {"role": "system", "content": "You are an expert at creating relevant questions from document content."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        
        result = response.choices[0].message.content.strip()
        logger.info(f"Raw OpenAI response: {result[:200]}...")
        
        # Try to extract JSON if wrapped in markdown code blocks
        if result.startswith('```'):
            # Remove markdown code blocks
            result = result.split('```')[1]
            if result.startswith('json'):
                result = result[4:].strip()
        
        try:
            questions = json.loads(result)
        except json.JSONDecodeError as je:
            logger.error(f"JSON decode error: {je}")
            logger.error(f"Response was: {result}")
            # Try to create fallback questions from the text
            return []
        
        return questions[:num_questions] if isinstance(questions, list) else []
    except Exception as e:
        logger.error(f"Error generating questions: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return []


def generate_question_variants(question, num_variants=10):
    """Generate paraphrase variants for a question"""
    try:
        # Configure OpenAI for Azure
        azure_key = os.getenv('AZURE_OPENAI_API_KEY')
        azure_base = os.getenv('AZURE_OPENAI_API_BASE')
        azure_version = os.getenv('AZURE_OPENAI_VERSION', '2023-12-01-preview')
        
        if azure_key and azure_base:
            openai.api_type = "azure"
            openai.api_key = azure_key
            openai.api_base = azure_base
            openai.api_version = azure_version
        
        prompt = f"""
Generate {num_variants} natural paraphrase variants of this question:

Original: "{question}"

Requirements:
1. Keep the same meaning and intent
2. Use different wording and phrasing
3. Vary formality levels
4. Include common alternative phrasings
5. Make them sound natural

Return JSON array:
[
    {{"variant": "Paraphrase here?", "similarity_score": 0.95}},
    ...
]
"""
        
        response = openai.ChatCompletion.create(
            engine=deployment_name,
            messages=[
                {"role": "system", "content": "You are an expert at generating natural language paraphrases."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5
        )
        
        result = response.choices[0].message.content.strip()
        logger.info(f"Variants raw response: {result[:200]}...")
        
        # Try to extract JSON if wrapped in markdown code blocks
        if result.startswith('```'):
            result = result.split('```')[1]
            if result.startswith('json'):
                result = result[4:].strip()
        
        try:
            variants = json.loads(result)
        except json.JSONDecodeError as je:
            logger.error(f"JSON decode error in variants: {je}")
            logger.error(f"Response was: {result}")
            return []
        
        # Add variant IDs
        for v in variants:
            v['variant_id'] = str(uuid.uuid4())
            v['auto_generated'] = True
            v['enabled'] = True
            v['text'] = v.pop('variant', '')
            if 'similarity_score' not in v:
                v['similarity_score'] = 0.90
        
        return variants[:num_variants] if isinstance(variants, list) else []
    except Exception as e:
        logger.error(f"Error generating variants: {e}")
        return []


def generate_answer_for_question(question, page_text, document_text=None):
    """Generate answer for a question"""
    try:
        # Configure OpenAI for Azure
        azure_key = os.getenv('AZURE_OPENAI_API_KEY')
        azure_base = os.getenv('AZURE_OPENAI_API_BASE')
        azure_version = os.getenv('AZURE_OPENAI_VERSION', '2023-12-01-preview')
        
        if azure_key and azure_base:
            openai.api_type = "azure"
            openai.api_key = azure_key
            openai.api_base = azure_base
            openai.api_version = azure_version
        
        context = page_text
        if document_text:
            context = document_text[:10000]  # Use more context if available
        
        prompt = f"""
Answer this question based on the document content:

Question: {question}

Document Content:
{context}

Provide a clear, accurate answer based ONLY on the information in the document.
If the information isn't available, say so clearly.

Format your answer appropriately (paragraph, bullets, or steps).
"""
        
        response = openai.ChatCompletion.create(
            engine=deployment_name,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that answers questions based on document content."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0
        )
        
        answer = response.choices[0].message.content.strip()
        
        # Extract source snippet (simplified)
        source_snippets = [{
            "text": page_text[:200] + "...",
            "page_number": 1,  # Will be set by caller
            "character_start": 0,
            "character_end": 200
        }]
        
        return {
            "draft_answer": answer,
            "approved_answer": None,
            "format": "paragraph",
            "source_snippets": source_snippets
        }
    except Exception as e:
        logger.error(f"Error generating answer: {e}")
        return {
            "draft_answer": "Error generating answer. Please try again.",
            "approved_answer": None,
            "format": "paragraph",
            "source_snippets": []
        }


def calculate_text_similarity(text1, text2):
    """Calculate similarity between two text strings"""
    return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()


# ============================================================================
# Document Management Routes
# ============================================================================

def register_document_routes(app):
    """Register document management routes"""
    
    @app.route('/api/knowledge-corpus/documents/upload', methods=['POST'])
    def upload_document():
        """Upload and process a new document"""
        try:
            # TODO: Temporarily bypass authentication for testing
            user_id = None
            try:
                if hasattr(current_user, 'id') and current_user.is_authenticated:
                    user_id = current_user.id
                else:
                    user_id = session.get('user_id') or request.form.get('user_id', 'test_admin')
            except:
                user_id = 'test_admin'  # Fallback for testing
            
            # Skip admin check for now to test endpoint
            # if not user_id or not check_admin_access(user_id):
            #     return jsonify({"success": False, "error": "Admin access required"}), 403
            
            if 'file' not in request.files:
                return jsonify({"success": False, "error": "No file uploaded"}), 400
            
            file = request.files['file']
            if not file.filename:
                return jsonify({"success": False, "error": "No file selected"}), 400
            
            # Validate file type
            allowed_types = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain']
            if file.content_type not in allowed_types:
                return jsonify({"success": False, "error": f"Unsupported file type: {file.content_type}"}), 400
            
            # Save file temporarily
            filename = secure_filename(file.filename)
            document_id = str(uuid.uuid4())
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as temp_file:
                temp_file_path = temp_file.name
                file.save(temp_file_path)
            
            try:
                # Extract text
                full_text = ""
                pages_data = []
                
                logger.info(f"Processing file: {filename}, type: {file.content_type}, size: {os.path.getsize(temp_file_path)} bytes")
                
                if file.content_type == 'application/pdf':
                    # Extract page by page
                    logger.info("Extracting PDF pages...")
                    pages_data = extract_pdf_pages(temp_file_path)
                    logger.info(f"Extracted {len(pages_data)} pages from PDF")
                    
                    if not pages_data:
                        logger.error("No pages extracted from PDF - possibly image-based or corrupted")
                        return jsonify({
                            "success": False, 
                            "error": "Could not extract text from PDF. The PDF might be image-based or corrupted. Please try OCR or a different file."
                        }), 400
                    
                    full_text = "\n\n".join([p['text'] for p in pages_data])
                else:
                    # For other formats, extract as single block
                    logger.info("Extracting text from non-PDF file...")
                    extracted_data = extract_text_from_file(temp_file_path, file.content_type)
                    full_text = " ".join([entry["text"] for entry in extracted_data.get("text_data", [])])
                    pages_data = [{
                        "page_number": 1,
                        "text": full_text,
                        "word_count": len(full_text.split()),
                        "character_count": len(full_text)
                    }]
                
                if not full_text.strip():
                    return jsonify({"success": False, "error": "No text extracted from file"}), 400
                
                # Generate synopsis
                synopsis = generate_synopsis_with_ai(full_text, filename)
                synopsis['last_edited_by'] = user_id
                synopsis['last_edited_at'] = datetime.utcnow()
                
                # Create document record
                document = {
                    "document_id": document_id,
                    "file_name": filename,
                    "original_file_type": file.content_type,
                    "file_size_bytes": os.path.getsize(temp_file_path),
                    "upload_date": datetime.utcnow(),
                    "uploaded_by": user_id,
                    "status": "draft",
                    "approval_status": {
                        "synopsis_approved": False,
                        "pages_reviewed": 0,
                        "total_pages": len(pages_data),
                        "qa_sets_approved": 0,
                        "total_qa_sets": 0,
                        "approved_by": None,
                        "approved_at": None
                    },
                    "synopsis": synopsis,
                    "full_text": full_text,
                    "word_count": len(full_text.split()),
                    "character_count": len(full_text),
                    "total_pages": len(pages_data),
                    "formatting_profile": {
                        "response_format": "bullet_summary",
                        "reading_level": "professional",
                        "citations_enabled": True,
                        "citation_style": "page_number",
                        "safety_verbosity": "normal"
                    },
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                    "version": 1,
                    "tags": request.form.getlist('tags') if request.form.getlist('tags') else [],
                    "categories": request.form.getlist('categories') if request.form.getlist('categories') else []
                }
                
                kc_documents_collection.insert_one(document)
                
                # Create page records
                text_position = 0
                for page_data in pages_data:
                    page_id = str(uuid.uuid4())
                    page = {
                        "page_id": page_id,
                        "document_id": document_id,
                        "page_number": page_data['page_number'],
                        "page_text": page_data['text'],
                        "word_count": page_data['word_count'],
                        "character_count": page_data['character_count'],
                        "text_start_index": text_position,
                        "text_end_index": text_position + page_data['character_count'],
                        "thumbnail": generate_page_thumbnail(page_data['text'], page_data['page_number']),
                        "headings": [],  # TODO: Extract headings
                        "has_tables": False,
                        "has_images": False,
                        "has_code_blocks": False,
                        "created_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }
                    kc_pages_collection.insert_one(page)
                    text_position += page_data['character_count'] + 2  # +2 for \n\n
                
                # Log audit
                log_audit("document_uploaded", "document", document_id, user_id, {
                    "file_name": filename,
                    "total_pages": len(pages_data)
                })
                
                logger.info(f"Document uploaded: {filename} ({document_id}) by user {user_id}")
                
                return jsonify({
                    "success": True,
                    "document_id": document_id,
                    "message": "Document uploaded and processed successfully",
                    "document": {
                        "document_id": document_id,
                        "file_name": filename,
                        "total_pages": len(pages_data),
                        "word_count": document['word_count'],
                        "status": "draft"
                    }
                })
                
            finally:
                # Clean up temp file
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
        
        except Exception as e:
            logger.error(f"Error uploading document: {e}")
            return jsonify({"success": False, "error": str(e)}), 500
    
    
    @app.route('/api/knowledge-corpus/documents', methods=['GET'])
    def list_documents():
        """List all documents with filtering"""
        try:
            # TODO: For now, allow access to test the endpoint
            # Authentication will be properly implemented in production
            # Get user from session or current_user
            user_id = None
            try:
                if hasattr(current_user, 'id') and current_user.is_authenticated:
                    user_id = current_user.id
                else:
                    user_id = session.get('user_id') or request.args.get('user_id', 'test_user')
            except:
                user_id = 'test_user'  # Fallback for testing
            
            # Skip admin check for now to test endpoint
            # if not user_id or not check_admin_access(user_id):
            #     return jsonify({"success": False, "error": "Admin access required"}), 403
            
            # Get query parameters
            status = request.args.get('status')
            uploaded_by = request.args.get('uploaded_by')
            page = int(request.args.get('page', 1))
            limit = int(request.args.get('limit', 20))
            
            # Build query
            query = {}
            if status:
                query['status'] = status
            if uploaded_by:
                query['uploaded_by'] = uploaded_by
            
            # Get total count
            total = kc_documents_collection.count_documents(query)
            
            # Get documents
            documents = list(kc_documents_collection.find(query)
                           .sort("created_at", -1)
                           .skip((page - 1) * limit)
                           .limit(limit))
            
            # Remove _id and add stats
            for doc in documents:
                doc.pop('_id', None)
                doc.pop('full_text', None)  # Don't send full text in list
            
            return jsonify({
                "success": True,
                "documents": documents,
                "total": total,
                "page": page,
                "total_pages": (total + limit - 1) // limit
            })
        
        except Exception as e:
            logger.error(f"Error listing documents: {e}")
            return jsonify({"success": False, "error": str(e)}), 500
    
    
    @app.route('/api/knowledge-corpus/documents/<document_id>', methods=['GET'])
    def get_document(document_id):
        """Get document details"""
        try:
            # TODO: Temporarily bypass authentication for testing
            user_id = None
            try:
                if hasattr(current_user, 'id') and current_user.is_authenticated:
                    user_id = current_user.id
                else:
                    user_id = session.get('user_id') or request.args.get('user_id', 'test_admin')
            except:
                user_id = 'test_admin'
            
            # Skip admin check for now
            # if not user_id or not check_admin_access(user_id):
            #     return jsonify({"success": False, "error": "Admin access required"}), 403
            
            document = kc_documents_collection.find_one({"document_id": document_id})
            if not document:
                return jsonify({"success": False, "error": "Document not found"}), 404
            
            document.pop('_id', None)
            
            # Get statistics
            total_qa = kc_qa_pairs_collection.count_documents({"document_id": document_id})
            approved_qa = kc_qa_pairs_collection.count_documents({"document_id": document_id, "approved": True})
            
            document['statistics'] = {
                "total_pages": document['total_pages'],
                "total_qa_pairs": total_qa,
                "approved_qa_pairs": approved_qa,
                "completion_percentage": (approved_qa / total_qa * 100) if total_qa > 0 else 0
            }
            
            return jsonify({
                "success": True,
                "document": document
            })
        
        except Exception as e:
            logger.error(f"Error getting document: {e}")
            return jsonify({"success": False, "error": str(e)}), 500
    
    
    @app.route('/api/knowledge-corpus/documents/<document_id>', methods=['PUT'])
    def update_document(document_id):
        """Update document (status, metadata, publish, etc.)"""
        try:
            # TODO: Temporarily bypass authentication for testing
            user_id = None
            try:
                if hasattr(current_user, 'id') and current_user.is_authenticated:
                    user_id = current_user.id
                else:
                    user_id = session.get('user_id') or (request.json.get('user_id') if request.json else None) or 'test_admin'
            except:
                user_id = 'test_admin'
            
            document = kc_documents_collection.find_one({"document_id": document_id})
            if not document:
                return jsonify({"success": False, "error": "Document not found"}), 404
            
            data = request.get_json()
            update_fields = {}
            
            # Handle status change
            if 'status' in data:
                update_fields['status'] = data['status']
                
                # If publishing, generate embeddings
                if data['status'] == 'published':
                    logger.info(f"Publishing document {document_id}, generating embeddings...")
                    
                    # Get all Q&A pairs for this document
                    qa_pairs = list(kc_qa_pairs_collection.find({"document_id": document_id}))
                    
                    # Generate embeddings for each Q&A pair if not already exists
                    for qa in qa_pairs:
                        # Check if embeddings already exist
                        existing = kc_embeddings_collection.find_one({
                            "document_id": document_id,
                            "qa_id": qa['qa_id']
                        })
                        
                        if not existing:
                            # Generate embedding for canonical question
                            try:
                                from app.utils.file_utils import get_embedding_azureRAG
                                embedding = get_embedding_azureRAG(qa['canonical_question'])
                                
                                kc_embeddings_collection.insert_one({
                                    "embedding_id": str(uuid.uuid4()),
                                    "document_id": document_id,
                                    "qa_id": qa['qa_id'],
                                    "text": qa['canonical_question'],
                                    "text_type": "canonical_question",
                                    "variant_id": None,
                                    "embedding": embedding,
                                    "embedding_model": "text-embedding-ada-002",
                                    "embedding_version": "2",
                                    "enabled": True,
                                    "created_at": datetime.utcnow()
                                })
                                
                                # Generate embeddings for variants
                                for variant in qa.get('variants', []):
                                    variant_embedding = get_embedding_azureRAG(variant['text'])
                                    kc_embeddings_collection.insert_one({
                                        "embedding_id": str(uuid.uuid4()),
                                        "document_id": document_id,
                                        "qa_id": qa['qa_id'],
                                        "text": variant['text'],
                                        "text_type": "variant",
                                        "variant_id": variant['variant_id'],
                                        "embedding": variant_embedding,
                                        "embedding_model": "text-embedding-ada-002",
                                        "embedding_version": "2",
                                        "enabled": variant.get('enabled', True),
                                        "created_at": datetime.utcnow()
                                    })
                            except Exception as e:
                                logger.error(f"Error generating embeddings for qa_id {qa['qa_id']}: {e}")
            
            # Handle other metadata updates
            if 'title' in data:
                update_fields['title'] = data['title']
            if 'category' in data:
                update_fields['category'] = data['category']
            if 'description' in data:
                update_fields['description'] = data['description']
            
            update_fields['updated_at'] = datetime.utcnow()
            
            # Update document
            kc_documents_collection.update_one(
                {"document_id": document_id},
                {"$set": update_fields}
            )
            
            # Log audit event
            log_audit("document_updated", "document", document_id, user_id, update_fields)
            
            return jsonify({
                "success": True,
                "message": "Document updated successfully",
                "updated_fields": list(update_fields.keys())
            })
        
        except Exception as e:
            logger.error(f"Error updating document: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"success": False, "error": str(e)}), 500
    
    
    @app.route('/api/knowledge-corpus/documents/<document_id>', methods=['DELETE'])
    def delete_document(document_id):
        """Delete a document and all associated data"""
        try:
            # TODO: Temporarily bypass authentication for testing
            user_id = None
            try:
                if hasattr(current_user, 'id') and current_user.is_authenticated:
                    user_id = current_user.id
                else:
                    user_id = session.get('user_id') or request.args.get('user_id', 'test_admin')
            except:
                user_id = 'test_admin'
            
            # Skip admin check for now
            # if not user_id or not check_admin_access(user_id):
            #     return jsonify({"success": False, "error": "Admin access required"}), 403
            
            # Check if document exists
            document = kc_documents_collection.find_one({"document_id": document_id})
            if not document:
                return jsonify({"success": False, "error": "Document not found"}), 404
            
            # Delete in order: embeddings -> qa_pairs -> pages -> document
            logger.info(f"Deleting document {document_id} and all associated data...")
            
            # 1. Delete embeddings
            embeddings_deleted = kc_embeddings_collection.delete_many({"document_id": document_id})
            logger.info(f"Deleted {embeddings_deleted.deleted_count} embeddings")
            
            # 2. Delete Q&A pairs
            qa_deleted = kc_qa_pairs_collection.delete_many({"document_id": document_id})
            logger.info(f"Deleted {qa_deleted.deleted_count} Q&A pairs")
            
            # 3. Delete pages
            pages_deleted = kc_pages_collection.delete_many({"document_id": document_id})
            logger.info(f"Deleted {pages_deleted.deleted_count} pages")
            
            # 4. Delete document
            doc_deleted = kc_documents_collection.delete_one({"document_id": document_id})
            logger.info(f"Deleted document {document_id}")
            
            # 5. Log audit event
            kc_audit_log_collection.insert_one({
                "log_id": str(uuid.uuid4()),  # Fixed: was "audit_id"
                "action_type": "document_deleted",
                "entity_type": "document",
                "entity_id": document_id,
                "user_id": user_id,
                "user_email": session.get('user_email', 'unknown'),
                "changes": {
                    "file_name": document.get('file_name', 'Unknown'),
                    "embeddings_deleted": embeddings_deleted.deleted_count,
                    "qa_pairs_deleted": qa_deleted.deleted_count,
                    "pages_deleted": pages_deleted.deleted_count
                },
                "timestamp": datetime.utcnow(),
                "ip_address": request.remote_addr,
                "user_agent": request.headers.get('User-Agent', 'unknown')
            })
            
            return jsonify({
                "success": True,
                "message": "Document deleted successfully",
                "deleted": {
                    "embeddings": embeddings_deleted.deleted_count,
                    "qa_pairs": qa_deleted.deleted_count,
                    "pages": pages_deleted.deleted_count,
                    "documents": doc_deleted.deleted_count
                }
            })
        
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return jsonify({"success": False, "error": str(e)}), 500
    
    
    @app.route('/api/knowledge-corpus/documents/<document_id>/synopsis', methods=['GET', 'PUT'])
    def handle_synopsis(document_id):
        """Get or update document synopsis"""
        try:
            # TODO: Temporarily bypass authentication for testing
            user_id = None
            try:
                if hasattr(current_user, 'id') and current_user.is_authenticated:
                    user_id = current_user.id
                else:
                    user_id = session.get('user_id') or request.args.get('user_id') or (request.json.get('user_id') if request.json else None) or 'test_admin'
            except:
                user_id = 'test_admin'
            
            # Skip admin check for now
            # if not user_id or not check_admin_access(user_id):
            #     return jsonify({"success": False, "error": "Admin access required"}), 403
            
            document = kc_documents_collection.find_one({"document_id": document_id})
            if not document:
                return jsonify({"success": False, "error": "Document not found"}), 404
            
            if request.method == 'GET':
                return jsonify({
                    "success": True,
                    "synopsis": document.get('synopsis', {}),
                    "editable": True
                })
            
            elif request.method == 'PUT':
                data = request.get_json()
                new_synopsis = data.get('synopsis', {})
                new_synopsis['last_edited_by'] = user_id
                new_synopsis['last_edited_at'] = datetime.utcnow()
                
                kc_documents_collection.update_one(
                    {"document_id": document_id},
                    {"$set": {
                        "synopsis": new_synopsis,
                        "updated_at": datetime.utcnow()
                    }}
                )
                
                log_audit("synopsis_edited", "document", document_id, user_id, {
                    "old_synopsis": document.get('synopsis', {}),
                    "new_synopsis": new_synopsis
                })
                
                return jsonify({
                    "success": True,
                    "message": "Synopsis updated successfully",
                    "updated_at": datetime.utcnow().isoformat()
                })
        
        except Exception as e:
            logger.error(f"Error handling synopsis: {e}")
            return jsonify({"success": False, "error": str(e)}), 500
    
    
    @app.route('/api/knowledge-corpus/documents/<document_id>/synopsis/regenerate', methods=['POST'])
    def regenerate_synopsis(document_id):
        """Regenerate document synopsis using AI"""
        try:
            # TODO: Temporarily bypass authentication for testing
            user_id = None
            try:
                if hasattr(current_user, 'id') and current_user.is_authenticated:
                    user_id = current_user.id
                else:
                    user_id = session.get('user_id') or (request.json.get('user_id') if request.json else None) or 'test_admin'
            except:
                user_id = 'test_admin'
            
            document = kc_documents_collection.find_one({"document_id": document_id})
            if not document:
                return jsonify({"success": False, "error": "Document not found"}), 404
            
            # Get all pages text
            pages = list(kc_pages_collection.find({"document_id": document_id}).sort("page_number", 1))
            full_text = "\n\n".join([p.get('page_text', '') for p in pages])
            
            # Regenerate synopsis
            logger.info(f"Regenerating synopsis for document {document_id}...")
            new_synopsis = generate_synopsis_with_ai(full_text, document.get('file_name', 'Document'))
            new_synopsis['last_edited_by'] = user_id
            new_synopsis['last_edited_at'] = datetime.utcnow()
            
            # Update document
            kc_documents_collection.update_one(
                {"document_id": document_id},
                {"$set": {
                    "synopsis": new_synopsis,
                    "updated_at": datetime.utcnow()
                }}
            )
            
            log_audit("synopsis_regenerated", "document", document_id, user_id, {
                "old_synopsis": document.get('synopsis', {}),
                "new_synopsis": new_synopsis
            })
            
            return jsonify({
                "success": True,
                "message": "Synopsis regenerated successfully",
                "synopsis": new_synopsis
            })
        
        except Exception as e:
            logger.error(f"Error regenerating synopsis: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"success": False, "error": str(e)}), 500
    
    
    @app.route('/api/knowledge-corpus/documents/<document_id>/pages', methods=['GET'])
    def get_document_pages(document_id):
        """Get all pages for a document"""
        try:
            # TODO: Temporarily bypass authentication for testing
            user_id = None
            try:
                if hasattr(current_user, 'id') and current_user.is_authenticated:
                    user_id = current_user.id
                else:
                    user_id = session.get('user_id') or request.args.get('user_id', 'test_admin')
            except:
                user_id = 'test_admin'
            
            # Get pages for this document
            pages = list(kc_pages_collection.find({"document_id": document_id}).sort("page_number", 1))
            
            # Remove _id
            for page in pages:
                page.pop('_id', None)
            
            return jsonify({
                "success": True,
                "pages": pages,
                "total": len(pages)
            })
        
        except Exception as e:
            logger.error(f"Error getting pages: {e}")
            return jsonify({"success": False, "error": str(e)}), 500


# ============================================================================
# Q&A Management Routes
# ============================================================================

def register_qa_routes(app):
    """Register Q&A management routes"""
    
    @app.route('/api/knowledge-corpus/pages/<page_id>/generate-qa', methods=['POST'])
    def generate_qa_for_page(page_id):
        """Generate Q&A pairs for a page"""
        try:
            # TODO: Temporarily bypass authentication for testing
            user_id = None
            try:
                if hasattr(current_user, 'id') and current_user.is_authenticated:
                    user_id = current_user.id
                else:
                    user_id = session.get('user_id') or (request.json.get('user_id') if request.json else None) or 'test_admin'
            except:
                user_id = 'test_admin'
            
            # Skip admin check for now
            # if not user_id or not check_admin_access(user_id):
            #     return jsonify({"success": False, "error": "Admin access required"}), 403
            
            page = kc_pages_collection.find_one({"page_id": page_id})
            if not page:
                return jsonify({"success": False, "error": "Page not found"}), 404
            
            data = request.get_json()
            num_questions = data.get('num_questions', 4)
            generate_variants_flag = data.get('generate_variants', True)
            variants_per_question = data.get('variants_per_question', 10)
            
            # Get surrounding pages for context
            document_id = page['document_id']
            page_num = page['page_number']
            
            # Fetch nearby pages for enhanced context
            nearby_pages = list(kc_pages_collection.find({
                "document_id": document_id,
                "page_number": {"$gte": page_num - 1, "$lte": page_num + 1}
            }).sort("page_number", 1))
            
            # Build enhanced context
            context_parts = []
            for p in nearby_pages:
                if p['page_number'] == page_num:
                    context_parts.append(f"[Main Content - Page {page_num}]\n{p['page_text']}\n")
                else:
                    context_parts.append(f"[Context from Page {p['page_number']}]\n{p['page_text'][:1000]}\n")
            
            enhanced_context = "\n".join(context_parts)
            
            # Generate questions
            questions = generate_questions_for_page(page['page_text'], page['page_number'], num_questions)
            
            qa_pairs = []
            for q_data in questions:
                qa_id = str(uuid.uuid4())
                question = q_data.get('question', '')
                
                # Generate variants
                variants = []
                if generate_variants_flag:
                    variants = generate_question_variants(question, variants_per_question)
                
                # Generate answer with enhanced context
                answer = generate_answer_for_question(question, page['page_text'], document_text=enhanced_context)
                answer['source_snippets'][0]['page_number'] = page['page_number']
                
                qa_pair = {
                    "qa_id": qa_id,
                    "document_id": page['document_id'],
                    "page_id": page_id,
                    "canonical_question": question,
                    "question_type": "page_specific",
                    "variants": variants,
                    "answer": answer,
                    "version_history": [],
                    "approved": False,
                    "approved_by": None,
                    "approved_at": None,
                    "times_matched": 0,
                    "last_matched": None,
                    "user_feedback": {"thumbs_up": 0, "thumbs_down": 0},
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                    "created_by": "system",
                    "last_edited_by": user_id
                }
                
                kc_qa_pairs_collection.insert_one(qa_pair)
                qa_pair.pop('_id', None)
                qa_pairs.append(qa_pair)
                
                # Generate embeddings for canonical question and variants
                # Canonical question embedding
                embedding = get_embedding_azureRAG(question)
                kc_embeddings_collection.insert_one({
                    "embedding_id": str(uuid.uuid4()),
                    "document_id": page['document_id'],
                    "qa_id": qa_id,
                    "text": question,
                    "text_type": "canonical_question",
                    "variant_id": None,
                    "embedding": embedding,
                    "embedding_model": "text-embedding-ada-002",
                    "embedding_version": "2",
                    "enabled": True,
                    "created_at": datetime.utcnow()
                })
                
                # Variant embeddings
                for variant in variants:
                    variant_embedding = get_embedding_azureRAG(variant['text'])
                    kc_embeddings_collection.insert_one({
                        "embedding_id": str(uuid.uuid4()),
                        "document_id": page['document_id'],
                        "qa_id": qa_id,
                        "text": variant['text'],
                        "text_type": "variant",
                        "variant_id": variant['variant_id'],
                        "embedding": variant_embedding,
                        "embedding_model": "text-embedding-ada-002",
                        "embedding_version": "2",
                        "enabled": variant['enabled'],
                        "created_at": datetime.utcnow()
                    })
            
            # Update document total_qa_sets
            kc_documents_collection.update_one(
                {"document_id": page['document_id']},
                {"$inc": {"approval_status.total_qa_sets": len(qa_pairs)}}
            )
            
            log_audit("qa_generated", "page", page_id, user_id, {
                "num_questions": len(qa_pairs)
            })
            
            return jsonify({
                "success": True,
                "qa_pairs": qa_pairs,
                "total_generated": len(qa_pairs)
            })
        
        except Exception as e:
            logger.error(f"Error generating Q&A: {e}")
            return jsonify({"success": False, "error": str(e)}), 500
    
    
    @app.route('/api/knowledge-corpus/documents/<document_id>/generate-qa-bulk', methods=['POST'])
    def generate_qa_bulk(document_id):
        """Generate Q&A for all pages in parallel (MUCH FASTER!) with real-time WebSocket updates"""
        try:
            user_id = session.get('user_id', 'test_admin')
            
            # WORKFLOW VALIDATION: Check if synopsis is approved
            document = kc_documents_collection.find_one({"document_id": document_id})
            if not document:
                return jsonify({"success": False, "error": "Document not found"}), 404
            
            synopsis_approved = document.get('approval_status', {}).get('synopsis_approved', False)
            if not synopsis_approved:
                return jsonify({
                    "success": False,
                    "error": "Synopsis must be approved before generating Q&A pairs",
                    "workflow_error": True,
                    "required_step": "approve_synopsis"
                }), 400
            
            # Get all pages for this document
            pages = list(kc_pages_collection.find({"document_id": document_id}).sort("page_number", 1))
            if not pages:
                return jsonify({"success": False, "error": "No pages found"}), 404
            
            data = request.get_json() or {}
            num_questions = data.get('num_questions', 4)
            generate_variants_flag = data.get('generate_variants', True)
            variants_per_question = data.get('variants_per_question', 10)
            max_workers = data.get('max_workers', 4)  # Process 4 pages concurrently
            client_id = data.get('client_id')  # WebSocket client ID for real-time updates
            
            # Get socketio instance for WebSocket emissions
            socketio = current_app.config.get('SOCKETIO')
            
            logger.info(f"Starting CONCURRENT Q&A generation for {len(pages)} pages with {max_workers} workers")
            start_time = time.time()
            
            # Emit start event
            if socketio and client_id:
                socketio.emit('qa_generation_started', {
                    'document_id': document_id,
                    'total_pages': len(pages),
                    'timestamp': datetime.utcnow().isoformat()
                }, room=client_id)
            
            # Create a lookup for page text by page number for context
            pages_by_number = {p['page_number']: p for p in pages}
            
            def get_page_context(page_num, context_range=1):
                """Get text from current page + surrounding pages for better context"""
                context_parts = []
                
                # Add previous page(s)
                for i in range(page_num - context_range, page_num):
                    if i in pages_by_number:
                        context_parts.append(f"[Context from Page {i}]\n{pages_by_number[i]['page_text'][:1000]}\n")
                
                # Add current page (full text)
                if page_num in pages_by_number:
                    context_parts.append(f"[Main Content - Page {page_num}]\n{pages_by_number[page_num]['page_text']}\n")
                
                # Add next page(s)
                for i in range(page_num + 1, page_num + context_range + 1):
                    if i in pages_by_number:
                        context_parts.append(f"[Context from Page {i}]\n{pages_by_number[i]['page_text'][:1000]}\n")
                
                return "\n".join(context_parts)
            
            def process_single_page(page):
                """Process a single page (runs in thread)"""
                try:
                    page_start = time.time()
                    page_id = page['page_id']
                    page_num = page['page_number']
                    
                    logger.info(f"[Thread] Processing Page {page_num}...")
                    
                    # Get enhanced context (current page + surrounding pages)
                    enhanced_context = get_page_context(page_num, context_range=1)
                    
                    # Generate questions (use only current page)
                    questions = generate_questions_for_page(page['page_text'], page_num, num_questions)
                    
                    qa_pairs = []
                    for q_data in questions:
                        qa_id = str(uuid.uuid4())
                        question = q_data.get('question', '')
                        
                        # Generate variants
                        variants = []
                        if generate_variants_flag:
                            variants = generate_question_variants(question, variants_per_question)
                        
                        # Generate answer with enhanced context
                        answer = generate_answer_for_question(question, page['page_text'], document_text=enhanced_context)
                        answer['source_snippets'][0]['page_number'] = page_num
                        
                        qa_pair = {
                            "qa_id": qa_id,
                            "document_id": document_id,
                            "page_id": page_id,
                            "canonical_question": question,
                            "question_type": "page_specific",
                            "variants": variants,
                            "answer": answer,
                            "version_history": [],
                            "approved": False,
                            "approved_by": None,
                            "approved_at": None,
                            "times_matched": 0,
                            "last_matched": None,
                            "user_feedback": {"thumbs_up": 0, "thumbs_down": 0},
                            "created_at": datetime.utcnow(),
                            "updated_at": datetime.utcnow(),
                            "created_by": "system",
                            "last_edited_by": user_id
                        }
                        
                        kc_qa_pairs_collection.insert_one(qa_pair)
                        qa_pair.pop('_id', None)
                        qa_pairs.append(qa_pair)
                        
                        # Generate embeddings
                        embedding = get_embedding_azureRAG(question)
                        kc_embeddings_collection.insert_one({
                            "embedding_id": str(uuid.uuid4()),
                            "document_id": document_id,
                            "qa_id": qa_id,
                            "text": question,
                            "text_type": "canonical_question",
                            "variant_id": None,
                            "embedding": embedding,
                            "embedding_model": "text-embedding-ada-002",
                            "embedding_version": "2",
                            "enabled": True,
                            "created_at": datetime.utcnow()
                        })
                        
                        # Variant embeddings
                        for variant in variants:
                            variant_embedding = get_embedding_azureRAG(variant['text'])
                            kc_embeddings_collection.insert_one({
                                "embedding_id": str(uuid.uuid4()),
                                "document_id": document_id,
                                "qa_id": qa_id,
                                "text": variant['text'],
                                "text_type": "variant",
                                "variant_id": variant['variant_id'],
                                "embedding": variant_embedding,
                                "embedding_model": "text-embedding-ada-002",
                                "embedding_version": "2",
                                "enabled": variant['enabled'],
                                "created_at": datetime.utcnow()
                            })
                    
                    page_time = time.time() - page_start
                    logger.info(f"[Thread] ✓ Page {page_num}: Generated {len(qa_pairs)} Q&A pairs in {page_time:.1f}s")
                    
                    return {
                        "success": True,
                        "page_number": page_num,
                        "page_id": page_id,
                        "qa_count": len(qa_pairs),
                        "time_taken": page_time
                    }
                    
                except Exception as e:
                    logger.error(f"[Thread] ✗ Page {page.get('page_number')}: {e}")
                    return {
                        "success": False,
                        "page_number": page.get('page_number'),
                        "page_id": page.get('page_id'),
                        "error": str(e)
                    }
            
            # Process pages concurrently
            results = []
            success_count = 0
            fail_count = 0
            total_qa_generated = 0
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all pages for processing
                future_to_page = {executor.submit(process_single_page, page): page for page in pages}
                
                # Collect results as they complete
                for future in as_completed(future_to_page):
                    result = future.result()
                    results.append(result)
                    
                    if result['success']:
                        success_count += 1
                        total_qa_generated += result.get('qa_count', 0)
                        
                        # Emit real-time WebSocket event for page completion
                        if socketio and client_id:
                            socketio.emit('qa_page_completed', {
                                'document_id': document_id,
                                'page_number': result['page_number'],
                                'page_id': result['page_id'],
                                'qa_count': result.get('qa_count', 0),
                                'time_taken': round(result.get('time_taken', 0), 1),
                                'completed_pages': success_count,
                                'total_pages': len(pages),
                                'progress_percent': round((success_count + fail_count) / len(pages) * 100, 1),
                                'timestamp': datetime.utcnow().isoformat()
                            }, room=client_id)
                    else:
                        fail_count += 1
                        
                        # Emit error event for failed page
                        if socketio and client_id:
                            socketio.emit('qa_page_failed', {
                                'document_id': document_id,
                                'page_number': result.get('page_number'),
                                'page_id': result.get('page_id'),
                                'error': result.get('error'),
                                'completed_pages': success_count,
                                'failed_pages': fail_count,
                                'total_pages': len(pages),
                                'progress_percent': round((success_count + fail_count) / len(pages) * 100, 1),
                                'timestamp': datetime.utcnow().isoformat()
                            }, room=client_id)
            
            # Update document total_qa_sets
            kc_documents_collection.update_one(
                {"document_id": document_id},
                {"$inc": {"approval_status.total_qa_sets": total_qa_generated}}
            )
            
            total_time = time.time() - start_time
            
            # Emit completion event
            if socketio and client_id:
                socketio.emit('qa_generation_completed', {
                    'document_id': document_id,
                    'total_pages': len(pages),
                    'success_count': success_count,
                    'fail_count': fail_count,
                    'total_qa_generated': total_qa_generated,
                    'time_taken_seconds': round(total_time, 1),
                    'avg_time_per_page': round(total_time / len(pages), 1) if pages else 0,
                    'timestamp': datetime.utcnow().isoformat()
                }, room=client_id)
            
            log_audit("qa_bulk_generated", "document", document_id, user_id, {
                "total_pages": len(pages),
                "success_count": success_count,
                "fail_count": fail_count,
                "total_qa_generated": total_qa_generated,
                "time_taken_seconds": total_time,
                "max_workers": max_workers
            })
            
            logger.info(f"CONCURRENT Q&A Generation Complete: {success_count}/{len(pages)} pages in {total_time:.1f}s (avg {total_time/len(pages):.1f}s/page)")
            
            return jsonify({
                "success": True,
                "message": f"Generated Q&A for {success_count} pages",
                "results": results,
                "summary": {
                    "total_pages": len(pages),
                    "success_count": success_count,
                    "fail_count": fail_count,
                    "total_qa_generated": total_qa_generated,
                    "time_taken_seconds": round(total_time, 1),
                    "avg_time_per_page": round(total_time / len(pages), 1) if pages else 0
                }
            })
            
        except Exception as e:
            logger.error(f"Error in bulk Q&A generation: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"success": False, "error": str(e)}), 500
    
    
    @app.route('/api/knowledge-corpus/documents/<document_id>/qa-pairs', methods=['GET'])
    def get_qa_pairs(document_id):
        """Get Q&A pairs for a document"""
        try:
            # TODO: Temporarily bypass authentication for testing
            user_id = None
            try:
                if hasattr(current_user, 'id') and current_user.is_authenticated:
                    user_id = current_user.id
                else:
                    user_id = session.get('user_id') or request.args.get('user_id', 'test_admin')
            except:
                user_id = 'test_admin'
            
            # Skip admin check for now
            # if not user_id or not check_admin_access(user_id):
            #     return jsonify({"success": False, "error": "Admin access required"}), 403
            
            # Get query parameters
            page_id = request.args.get('page_id')
            approved_filter = request.args.get('approved')
            page = int(request.args.get('page', 1))
            limit = int(request.args.get('limit', 50))
            
            # Build query
            query = {"document_id": document_id}
            if page_id:
                query['page_id'] = page_id
            if approved_filter is not None:
                query['approved'] = approved_filter.lower() == 'true'
            
            # Get total count
            total = kc_qa_pairs_collection.count_documents(query)
            approved = kc_qa_pairs_collection.count_documents({**query, "approved": True})
            
            # Get Q&A pairs
            qa_pairs = list(kc_qa_pairs_collection.find(query)
                          .sort("created_at", 1)
                          .skip((page - 1) * limit)
                          .limit(limit))
            
            # Remove _id
            for qa in qa_pairs:
                qa.pop('_id', None)
            
            return jsonify({
                "success": True,
                "qa_pairs": qa_pairs,
                "total": total,
                "approved": approved
            })
        
        except Exception as e:
            logger.error(f"Error getting Q&A pairs: {e}")
            return jsonify({"success": False, "error": str(e)}), 500


# ============================================================================
# Search & Query Routes
# ============================================================================

def register_search_routes(app):
    """Register search and query routes"""
    
    @app.route('/api/knowledge-corpus/query-live', methods=['POST'])
    def query_knowledge_corpus_live():
        """Query published Knowledge Corpus documents (like query_trained_manual)"""
        try:
            # Get user ID
            user_id = None
            try:
                if hasattr(current_user, 'id') and current_user.is_authenticated:
                    user_id = current_user.id
                else:
                    user_id = session.get('user_id') or (request.json.get('user_id') if request.json else None) or 'test_admin'
            except:
                user_id = 'test_admin'
            
            data = request.get_json()
            query = data.get('query', '').strip()
            document_id_filter = data.get('document_id')  # Optional: filter by specific document
            
            if not query:
                return jsonify({"success": False, "error": "Query is required"}), 400
            
            logger.info(f"[KC Live Query] User {user_id} asks: {query}")
            
            # ============================================
            # TIER 1: FAST & ACCURATE SEARCH
            # ============================================
            import time
            import re
            from difflib import SequenceMatcher
            
            tier1_start = time.time()
            
            # Build query for Q&A pairs
            qa_query = {"approved": True}  # Only search approved Q&A pairs
            if document_id_filter:
                qa_query['document_id'] = document_id_filter
            
            # Normalize query for better matching
            query_lower = query.lower().strip()
            query_normalized = re.sub(r'[^\w\s]', '', query_lower)  # Remove punctuation
            query_words = set(query_normalized.split())
            
            best_match = None
            match_type = None
            
            # ──────────────────────────────────────────────
            # STEP 1: Try EXACT match (canonical question)
            # ──────────────────────────────────────────────
            exact_match = kc_qa_pairs_collection.find_one({
                **qa_query,
                "canonical_question": {"$regex": f"^{re.escape(query)}$", "$options": "i"}
            })
            
            if exact_match:
                best_match = {
                    "qa_id": exact_match['qa_id'],
                    "similarity_score": 1.0,
                    "document_id": exact_match['document_id'],
                    "matched_text": exact_match['canonical_question']
                }
                match_type = "EXACT"
                tier1_time = time.time() - tier1_start
                logger.info(f"[KC Live Query] ⚡ TIER 1 - Exact match in {tier1_time*1000:.1f}ms")
            
            # ──────────────────────────────────────────────
            # STEP 2: Try VARIANT match (search all variants)
            # ──────────────────────────────────────────────
            if not best_match:
                variant_match = kc_qa_pairs_collection.find_one({
                    **qa_query,
                    "variants.text": {"$regex": f"^{re.escape(query)}$", "$options": "i"}
                })
                
                if variant_match:
                    # Find which variant matched
                    matched_variant = next(
                        (v for v in variant_match.get('variants', []) 
                         if v['text'].lower() == query_lower),
                        None
                    )
                    
                    best_match = {
                        "qa_id": variant_match['qa_id'],
                        "similarity_score": 1.0,
                        "document_id": variant_match['document_id'],
                        "matched_text": matched_variant['text'] if matched_variant else variant_match['canonical_question']
                    }
                    match_type = "VARIANT"
                    tier1_time = time.time() - tier1_start
                    logger.info(f"[KC Live Query] ⚡ TIER 1 - Variant match in {tier1_time*1000:.1f}ms")
            
            # ──────────────────────────────────────────────
            # STEP 3: SMART FUZZY match (multiple algorithms)
            # ──────────────────────────────────────────────
            if not best_match:
                all_qa_pairs = list(kc_qa_pairs_collection.find(qa_query))
                fuzzy_matches = []
                
                for qa in all_qa_pairs:
                    # Collect all searchable text (canonical + variants)
                    searchable_texts = [qa.get('canonical_question', '')]
                    searchable_texts.extend([v['text'] for v in qa.get('variants', [])])
                    
                    best_similarity = 0
                    best_text = qa.get('canonical_question', '')
                    
                    for text in searchable_texts:
                        if not text:
                            continue
                            
                        text_lower = text.lower().strip()
                        text_normalized = re.sub(r'[^\w\s]', '', text_lower)
                        text_words = set(text_normalized.split())
                        
                        # Algorithm 1: Jaccard Similarity (word overlap)
                        if query_words and text_words:
                            intersection = len(query_words & text_words)
                            union = len(query_words | text_words)
                            jaccard_sim = intersection / union if union > 0 else 0
                        else:
                            jaccard_sim = 0
                        
                        # Algorithm 2: Sequence Matcher (character-level similarity)
                        sequence_sim = SequenceMatcher(None, query_normalized, text_normalized).ratio()
                        
                        # Algorithm 3: Substring matching boost
                        substring_boost = 0
                        if query_lower in text_lower or text_lower in query_lower:
                            substring_boost = 0.2
                        
                        # Algorithm 4: Word-in-text matching (for poor grammar queries)
                        # Check if MOST query words appear ANYWHERE in the question
                        words_found = sum(1 for word in query_words if word in text_words)
                        if query_words and words_found >= len(query_words) * 0.6:  # 60% of words match
                            word_presence_boost = 0.15
                        else:
                            word_presence_boost = 0
                        
                        # Combined similarity (weighted average + boosts)
                        combined_sim = (jaccard_sim * 0.5 + sequence_sim * 0.3 + substring_boost + word_presence_boost)
                        
                        if combined_sim > best_similarity:
                            best_similarity = combined_sim
                            best_text = text
                    
                    # LOWERED threshold from 0.4 to 0.35 for better recall
                    if best_similarity >= 0.35:
                        fuzzy_matches.append({
                            "qa_id": qa['qa_id'],
                            "similarity_score": float(best_similarity),
                            "document_id": qa['document_id'],
                            "matched_text": best_text,
                            "canonical_question": qa.get('canonical_question', ''),
                            "page_number": qa.get('page_number', 0)
                        })
                
                if fuzzy_matches:
                    # Sort by similarity, then by page number (prefer earlier pages)
                    fuzzy_matches.sort(key=lambda x: (x['similarity_score'], -x['page_number']), reverse=True)
                    best_match = fuzzy_matches[0]
                    match_type = "FUZZY"
                    tier1_time = time.time() - tier1_start
                    logger.info(f"[KC Live Query] 🔍 TIER 1 - Fuzzy match in {tier1_time*1000:.1f}ms (score: {best_match['similarity_score']:.3f})")
            
            # ============================================
            # TIER 2: AI SEMANTIC SEARCH (Smart Fallback)
            # ============================================
            if not best_match:
                tier1_time = time.time() - tier1_start
                logger.info(f"[KC Live Query] TIER 1 - No direct match in {tier1_time*1000:.1f}ms, using TIER 2 (AI semantic search)")
                
                tier2_start = time.time()
                
                # Generate embedding for query (slow but accurate)
                query_embedding = get_embedding_azureRAG(query)
                
                # Find matching Q&A pairs using embeddings
                embedding_query = {
                    "enabled": True,
                    "text_type": "canonical_question"  # Search in questions
                }
                if document_id_filter:
                    embedding_query['document_id'] = document_id_filter
                
                # Get all enabled embeddings
                embeddings = list(kc_embeddings_collection.find(embedding_query))
                
                if not embeddings:
                    logger.warning(f"[KC Live Query] No embeddings found")
                    return jsonify({
                        "success": False,
                        "message": "No knowledge base available. Please publish documents first."
                    })
                
                # Calculate similarities with enhanced scoring
                matches = []
                all_similarities = []  # For debugging
                
                for emb in embeddings:
                    # Base similarity from embeddings
                    semantic_sim = calculate_cosine_similarity(query_embedding, emb['embedding'])
                    
                    # Get Q&A pair for additional context
                    qa_pair = kc_qa_pairs_collection.find_one({"qa_id": emb['qa_id']})
                    
                    if qa_pair:
                        # Track all similarities for debugging
                        all_similarities.append({
                            "question": qa_pair.get('canonical_question', '')[:50],
                            "similarity": semantic_sim
                        })
                        
                        # LOWERED THRESHOLD: 70% instead of 80% for better recall
                        if semantic_sim >= 0.70:
                            # Boost score based on additional factors
                            boost = 0
                            
                            # 1. Boost if query words appear in question
                            question_lower = qa_pair.get('canonical_question', '').lower()
                            matching_words = sum(1 for word in query_words if word in question_lower)
                            if query_words:
                                word_match_ratio = matching_words / len(query_words)
                                boost += word_match_ratio * 0.05  # Up to 5% boost
                            
                            # 2. Boost recent approvals (fresher content)
                            if qa_pair.get('approved') or qa_pair.get('answer', {}).get('is_approved'):
                                boost += 0.02  # 2% boost for approved answers
                            
                            # 3. Prefer earlier pages (usually more important)
                            page_num = qa_pair.get('page_number', 999)
                            if page_num <= 5:
                                boost += 0.03  # 3% boost for first 5 pages
                            
                            # 4. EXTRA boost if multiple query words match
                            if matching_words >= 2:
                                boost += 0.03  # 3% extra for 2+ word matches
                            
                            final_score = min(semantic_sim + boost, 1.0)  # Cap at 100%
                            
                            matches.append({
                                "qa_id": emb['qa_id'],
                                "similarity_score": float(final_score),
                                "document_id": emb.get('document_id'),
                                "page_number": page_num,
                                "semantic_score": float(semantic_sim),
                                "boost": float(boost)
                            })
                
                # Sort by final score (similarity + boosts)
                matches.sort(key=lambda x: x['similarity_score'], reverse=True)
                
                # Enhanced logging
                if not matches:
                    # Show top 5 similarities for debugging
                    all_similarities.sort(key=lambda x: x['similarity'], reverse=True)
                    top_5 = all_similarities[:5]
                    logger.warning(f"[KC Live Query] No matches above 70% threshold for: {query}")
                    logger.warning(f"[KC Live Query] Top 5 similarities: {top_5}")
                    return jsonify({
                        "success": False,
                        "message": "No relevant information found in the knowledge base."
                    })
                
                best_match = matches[0]
                match_type = "SEMANTIC"
                tier2_time = time.time() - tier2_start
                
                # Enhanced logging with scoring details
                if 'boost' in best_match and best_match['boost'] > 0:
                    logger.info(f"[KC Live Query] 🧠 TIER 2 - AI match in {tier2_time*1000:.1f}ms "
                              f"(semantic: {best_match.get('semantic_score', 0):.3f}, "
                              f"boost: +{best_match['boost']:.3f}, "
                              f"final: {best_match['similarity_score']:.3f})")
                else:
                    logger.info(f"[KC Live Query] 🧠 TIER 2 - AI match in {tier2_time*1000:.1f}ms "
                              f"(score: {best_match['similarity_score']:.3f})")
            
            # Get Q&A pair details
            qa_pair = kc_qa_pairs_collection.find_one({"qa_id": best_match['qa_id']})
            if not qa_pair:
                return jsonify({
                    "success": False,
                    "message": "Q&A pair not found"
                })
            
            # Get document and page info
            doc = kc_documents_collection.find_one({"document_id": qa_pair['document_id']})
            page = kc_pages_collection.find_one({"page_id": qa_pair['page_id']})
            
            # Get answer (prefer approved, fallback to draft)
            answer_text = qa_pair['answer'].get('approved_answer') or qa_pair['answer'].get('draft_answer', '')
            
            # Format response with HTML (similar to query_trained_manual)
            source_name = doc.get('file_name', 'Unknown Document') if doc else 'Unknown Document'
            page_number = page.get('page_number', '?') if page else '?'
            
            # Determine match badge color and icon with enhanced descriptions
            if match_type == "EXACT":
                match_badge = '<span class="match-badge" style="background: linear-gradient(135deg, #10b981, #059669); color: white; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600;"><i class="fas fa-bolt"></i> INSTANT MATCH</span>'
                match_color = "#10b981"
                match_explanation = "Exact match found in canonical questions"
            elif match_type == "VARIANT":
                match_badge = '<span class="match-badge" style="background: linear-gradient(135deg, #10b981, #059669); color: white; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600;"><i class="fas fa-bolt"></i> INSTANT MATCH</span>'
                match_color = "#10b981"
                match_explanation = f"Matched variant: \"{best_match.get('matched_text', '')}\""
            elif match_type == "FUZZY":
                match_badge = '<span class="match-badge" style="background: linear-gradient(135deg, #3b82f6, #2563eb); color: white; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600;"><i class="fas fa-search"></i> QUICK MATCH</span>'
                match_color = "#3b82f6"
                match_explanation = "Similar wording found using smart text matching"
            else:  # SEMANTIC
                match_badge = '<span class="match-badge" style="background: linear-gradient(135deg, #8b5cf6, #7c3aed); color: white; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600;"><i class="fas fa-brain"></i> AI MATCH</span>'
                match_color = "#8b5cf6"
                if 'boost' in best_match and best_match.get('boost', 0) > 0:
                    match_explanation = f"AI semantic understanding (boosted by relevance factors: +{best_match['boost']*100:.1f}%)"
                else:
                    match_explanation = "AI semantic understanding found the best answer"
            
            # Show matched variant text if different from canonical
            matched_question = best_match.get('matched_text', qa_pair['canonical_question'])
            show_variant_note = (match_type == "VARIANT" or match_type == "FUZZY") and matched_question != qa_pair['canonical_question']
            
            formatted_response = f"""
<div class="rag-response">
    <div class="source-info">
        <i class="fas fa-book"></i>
        <span>Source: {source_name} (Page {page_number})</span>
        <span class="match-confidence" style="margin-left: 10px; color: {match_color};">
            <i class="fas fa-check-circle"></i> {best_match['similarity_score']*100:.1f}% Match
        </span>
        {match_badge}
    </div>
    
    {f'''
    <div style="margin-top: 10px; padding: 8px 12px; background: #eff6ff; border-left: 3px solid {match_color}; font-size: 13px; color: #1e40af;">
        <i class="fas fa-info-circle"></i> {match_explanation}
    </div>
    ''' if match_explanation else ''}
    
    {f'''
    <div style="margin-top: 10px; padding: 8px 12px; background: #fef3c7; border-left: 3px solid #f59e0b; font-size: 13px; color: #92400e;">
        <i class="fas fa-exchange-alt"></i> Your question matched: "<strong>{matched_question}</strong>"
    </div>
    ''' if show_variant_note else ''}
    
    <div class="answer-content" style="margin-top: 15px;">
        <h4 style="color: #2c5282; margin-bottom: 10px;">
            <i class="fas fa-question-circle"></i> {qa_pair['canonical_question']}
        </h4>
        <div class="answer-text" style="line-height: 1.6;">
            {answer_text}
        </div>
    </div>
    
    {f'''
    <div class="related-questions" style="margin-top: 20px; padding: 15px; background: #f7fafc; border-left: 4px solid #4299e1;">
        <h5 style="color: #2d3748; margin-bottom: 10px;">
            <i class="fas fa-lightbulb"></i> You might also ask:
        </h5>
        <ul style="margin: 0; padding-left: 20px;">
            {''.join([f'<li>{v["text"]}</li>' for v in qa_pair.get('variants', [])[:3]])}
        </ul>
    </div>
    ''' if qa_pair.get('variants') else ''}
    
    {f'''
    <div class="other-matches" style="margin-top: 15px; font-size: 0.9em; color: #718096;">
        <i class="fas fa-info-circle"></i> Found {len(matches)} related topics. 
        {f'Next best: {matches[1]["similarity_score"]*100:.1f}% match' if len(matches) > 1 else ''}
    </div>
    ''' if match_type == "SEMANTIC" and len(matches) > 1 else ''}
</div>
"""
            
            # Log query for analytics
            kc_user_queries_collection.insert_one({
                "query_id": str(uuid.uuid4()),
                "user_id": user_id,
                "query_text": query,
                "matched_qa_id": best_match['qa_id'],
                "similarity_score": best_match['similarity_score'],
                "match_type": match_type,  # EXACT, FUZZY, VARIANT, or SEMANTIC
                "query_timestamp": datetime.utcnow(),
                "user_feedback": None
            })
            
            # Determine total_matches based on match type
            if match_type == "SEMANTIC":
                total_matches = len(matches)
            else:
                total_matches = 1
            
            return jsonify({
                "success": True,
                "answer": formatted_response,
                "metadata": {
                    "source_document": source_name,
                    "page_number": page_number,
                    "similarity_score": best_match['similarity_score'],
                    "canonical_question": qa_pair['canonical_question'],
                    "match_type": match_type,  # Include match type in response
                    "total_matches": total_matches
                }
            })
        
        except Exception as e:
            logger.error(f"[KC Live Query] Error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return jsonify({"success": False, "error": str(e)}), 500
    
    @app.route('/api/knowledge-corpus/search', methods=['POST'])
    def search_qa():
        """Semantic search across Q&A pairs"""
        try:
            # TODO: Temporarily bypass authentication for testing
            user_id = None
            try:
                if hasattr(current_user, 'id') and current_user.is_authenticated:
                    user_id = current_user.id
                else:
                    user_id = session.get('user_id') or (request.json.get('user_id') if request.json else None) or 'test_admin'
            except:
                user_id = 'test_admin'
            
            # Skip admin check for now
            # if not user_id or not check_admin_access(user_id):
            #     return jsonify({"success": False, "error": "Admin access required"}), 403
            
            data = request.get_json()
            query = data.get('query', '').strip()
            document_id_filter = data.get('document_id')
            top_k = data.get('top_k', 5)
            min_similarity = data.get('min_similarity', 0.90)
            
            if not query:
                return jsonify({"success": False, "error": "Query is required"}), 400
            
            # Generate embedding for query
            query_embedding = get_embedding_azureRAG(query)
            
            # Get all enabled embeddings
            embedding_query = {"enabled": True}
            if document_id_filter:
                embedding_query['document_id'] = document_id_filter
            
            embeddings = list(kc_embeddings_collection.find(embedding_query))
            
            # Calculate similarities
            results = []
            for emb in embeddings:
                similarity = calculate_cosine_similarity(query_embedding, emb['embedding'])
                if similarity >= min_similarity:
                    results.append({
                        "qa_id": emb['qa_id'],
                        "similarity_score": similarity,
                        "text": emb['text'],
                        "text_type": emb['text_type']
                    })
            
            # Sort by similarity
            results.sort(key=lambda x: x['similarity_score'], reverse=True)
            results = results[:top_k]
            
            # Get Q&A details
            qa_ids = [r['qa_id'] for r in results]
            qa_pairs = {qa['qa_id']: qa for qa in kc_qa_pairs_collection.find({"qa_id": {"$in": qa_ids}})}
            
            # Enrich results
            enriched_results = []
            for r in results:
                qa = qa_pairs.get(r['qa_id'])
                if qa:
                    # Get document and page info
                    doc = kc_documents_collection.find_one({"document_id": qa['document_id']})
                    page = kc_pages_collection.find_one({"page_id": qa['page_id']})
                    
                    enriched_results.append({
                        "qa_id": r['qa_id'],
                        "canonical_question": qa['canonical_question'],
                        "similarity_score": r['similarity_score'],
                        "match_type": "semantic_high" if r['similarity_score'] >= 0.95 else "semantic_medium",
                        "answer_preview": (qa['answer'].get('approved_answer') or qa['answer'].get('draft_answer', ''))[:200] + "...",
                        "document_name": doc['file_name'] if doc else "Unknown",
                        "page_number": page['page_number'] if page else None
                    })
            
            return jsonify({
                "success": True,
                "results": enriched_results,
                "total_results": len(enriched_results)
            })
        
        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return jsonify({"success": False, "error": str(e)}), 500


def calculate_cosine_similarity(vec1, vec2):
    """Calculate cosine similarity between two vectors"""
    import numpy as np
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))


# ============================================================================
# Approval Workflow Routes
# ============================================================================

def register_approval_routes(app):
    """Register approval workflow routes"""
    
    @app.route('/api/knowledge-corpus/documents/<document_id>/approve-synopsis', methods=['POST'])
    def approve_synopsis(document_id):
        """Approve document synopsis"""
        try:
            # TODO: Temporarily bypass authentication for testing
            user_id = None
            try:
                if hasattr(current_user, 'id') and current_user.is_authenticated:
                    user_id = current_user.id
                else:
                    user_id = session.get('user_id') or (request.json.get('user_id') if request.json else None) or 'test_admin'
            except:
                user_id = 'test_admin'
            
            # Skip admin check for now
            # if not user_id or not check_admin_access(user_id):
            #     return jsonify({"success": False, "error": "Admin access required"}), 403
            
            document = kc_documents_collection.find_one({"document_id": document_id})
            if not document:
                return jsonify({"success": False, "error": "Document not found"}), 404
            
            kc_documents_collection.update_one(
                {"document_id": document_id},
                {"$set": {
                    "approval_status.synopsis_approved": True,
                    "approval_status.approved_by": user_id,
                    "approval_status.approved_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }}
            )
            
            log_audit("synopsis_approved", "document", document_id, user_id)
            
            return jsonify({
                "success": True,
                "message": "Synopsis approved",
                "approval_status": {
                    "synopsis_approved": True,
                    "approved_by": user_id,
                    "approved_at": datetime.utcnow().isoformat()
                }
            })
        
        except Exception as e:
            logger.error(f"Error approving synopsis: {e}")
            return jsonify({"success": False, "error": str(e)}), 500
    
    
    @app.route('/api/knowledge-corpus/qa-pairs/<qa_id>/approve', methods=['POST'])
    def approve_qa(qa_id):
        """Approve a Q&A pair"""
        try:
            # TODO: Temporarily bypass authentication for testing
            user_id = None
            try:
                if hasattr(current_user, 'id') and current_user.is_authenticated:
                    user_id = current_user.id
                else:
                    user_id = session.get('user_id') or (request.json.get('user_id') if request.json else None) or 'test_admin'
            except:
                user_id = 'test_admin'
            
            # Skip admin check for now
            # if not user_id or not check_admin_access(user_id):
            #     return jsonify({"success": False, "error": "Admin access required"}), 403
            
            qa_pair = kc_qa_pairs_collection.find_one({"qa_id": qa_id})
            if not qa_pair:
                return jsonify({"success": False, "error": "Q&A pair not found"}), 404
            
            kc_qa_pairs_collection.update_one(
                {"qa_id": qa_id},
                {"$set": {
                    "approved": True,
                    "approved_by": user_id,
                    "approved_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }}
            )
            
            # Update document approval count
            kc_documents_collection.update_one(
                {"document_id": qa_pair['document_id']},
                {"$inc": {"approval_status.qa_sets_approved": 1}}
            )
            
            log_audit("qa_approved", "qa_pair", qa_id, user_id)
            
            return jsonify({
                "success": True,
                "message": "Q&A pair approved"
            })
        
        except Exception as e:
            logger.error(f"Error approving Q&A: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    
    @app.route('/api/knowledge-corpus/pages/<page_id>/approve-all-qa', methods=['POST'])
    def approve_page_qa(page_id):
        """Approve all Q&A pairs for a specific page"""
        try:
            user_id = session.get('user_id', 'test_admin')
            
            # Get all Q&A pairs for this page
            qa_pairs = list(kc_qa_pairs_collection.find({"page_id": page_id}))
            if not qa_pairs:
                return jsonify({"success": False, "error": "No Q&A pairs found for this page"}), 404
            
            # Approve all Q&A pairs
            approved_count = 0
            for qa in qa_pairs:
                if not qa.get('approved'):
                    kc_qa_pairs_collection.update_one(
                        {"qa_id": qa['qa_id']},
                        {"$set": {
                            "approved": True,
                            "approved_by": user_id,
                            "approved_at": datetime.utcnow(),
                            "updated_at": datetime.utcnow()
                        }}
                    )
                    approved_count += 1
            
            # Update document approval count
            if approved_count > 0 and qa_pairs:
                kc_documents_collection.update_one(
                    {"document_id": qa_pairs[0]['document_id']},
                    {"$inc": {"approval_status.qa_sets_approved": approved_count}}
                )
            
            log_audit("page_qa_approved", "page", page_id, user_id, {
                "approved_count": approved_count,
                "total_qa_pairs": len(qa_pairs)
            })
            
            return jsonify({
                "success": True,
                "message": f"Approved {approved_count} Q&A pairs for this page",
                "approved_count": approved_count,
                "total_qa_pairs": len(qa_pairs)
            })
        
        except Exception as e:
            logger.error(f"Error approving page Q&A: {e}")
            return jsonify({"success": False, "error": str(e)}), 500
    
    
    @app.route('/api/knowledge-corpus/qa-pairs/<qa_id>/edit-question', methods=['PUT'])
    def edit_question(qa_id):
        """Edit the canonical question of a Q&A pair"""
        try:
            user_id = session.get('user_id', 'test_admin')
            data = request.get_json()
            
            if not data or 'canonical_question' not in data:
                return jsonify({"success": False, "error": "canonical_question is required"}), 400
            
            new_question = data['canonical_question'].strip()
            if not new_question:
                return jsonify({"success": False, "error": "Question cannot be empty"}), 400
            
            # Get the Q&A pair
            qa_pair = kc_qa_pairs_collection.find_one({"qa_id": qa_id})
            if not qa_pair:
                return jsonify({"success": False, "error": "Q&A pair not found"}), 404
            
            # Check for duplicate question (excluding current Q&A)
            duplicate = kc_qa_pairs_collection.find_one({
                "document_id": qa_pair['document_id'],
                "canonical_question": new_question,
                "qa_id": {"$ne": qa_id}
            })
            if duplicate:
                return jsonify({"success": False, "error": "This question already exists in the document"}), 400
            
            old_question = qa_pair.get('canonical_question', '')
            
            # Update Q&A pair with version history
            version_entry = {
                "version": len(qa_pair.get('version_history', [])) + 1,
                "old_question": old_question,
                "new_question": new_question,
                "edited_by": user_id,
                "edited_at": datetime.utcnow()
            }
            
            kc_qa_pairs_collection.update_one(
                {"qa_id": qa_id},
                {
                    "$set": {
                        "canonical_question": new_question,
                        "updated_at": datetime.utcnow(),
                        "last_edited_by": user_id
                    },
                    "$push": {"version_history": version_entry}
                }
            )
            
            # Update embedding for the new question
            new_embedding = get_embedding_azureRAG(new_question)
            kc_embeddings_collection.update_one(
                {
                    "qa_id": qa_id,
                    "text_type": "canonical_question"
                },
                {
                    "$set": {
                        "text": new_question,
                        "embedding": new_embedding,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            log_audit("question_edited", "qa_pair", qa_id, user_id, {
                "old_question": old_question,
                "new_question": new_question
            })
            
            return jsonify({
                "success": True,
                "message": "Question updated successfully",
                "canonical_question": new_question
            })
        
        except Exception as e:
            logger.error(f"Error editing question: {e}")
            return jsonify({"success": False, "error": str(e)}), 500
    
    
    @app.route('/api/knowledge-corpus/qa-pairs/<qa_id>/variants', methods=['GET'])
    def get_variants(qa_id):
        """Get all variants for a Q&A pair"""
        try:
            qa_pair = kc_qa_pairs_collection.find_one({"qa_id": qa_id})
            if not qa_pair:
                return jsonify({"success": False, "error": "Q&A pair not found"}), 404
            
            variants = qa_pair.get('variants', [])
            
            return jsonify({
                "success": True,
                "variants": variants,
                "total_variants": len(variants),
                "canonical_question": qa_pair.get('canonical_question', '')
            })
        
        except Exception as e:
            logger.error(f"Error getting variants: {e}")
            return jsonify({"success": False, "error": str(e)}), 500
    
    
    @app.route('/api/knowledge-corpus/qa-pairs/<qa_id>/variants', methods=['POST'])
    def add_variant(qa_id):
        """Add a new question variant"""
        try:
            user_id = session.get('user_id', 'test_admin')
            data = request.get_json()
            
            if not data or 'variant_text' not in data:
                return jsonify({"success": False, "error": "variant_text is required"}), 400
            
            variant_text = data['variant_text'].strip()
            if not variant_text:
                return jsonify({"success": False, "error": "Variant text cannot be empty"}), 400
            
            # Get the Q&A pair
            qa_pair = kc_qa_pairs_collection.find_one({"qa_id": qa_id})
            if not qa_pair:
                return jsonify({"success": False, "error": "Q&A pair not found"}), 404
            
            # Check variant limit (10 variants max)
            current_variants = qa_pair.get('variants', [])
            if len(current_variants) >= 10:
                return jsonify({"success": False, "error": "Maximum 10 variants allowed per question"}), 400
            
            # Check for duplicate variant
            for variant in current_variants:
                if variant['text'].lower() == variant_text.lower():
                    return jsonify({"success": False, "error": "This variant already exists"}), 400
            
            # Create new variant
            variant_id = str(uuid.uuid4())
            new_variant = {
                "variant_id": variant_id,
                "text": variant_text,
                "enabled": True,
                "created_at": datetime.utcnow(),
                "created_by": user_id
            }
            
            # Add variant to Q&A pair
            kc_qa_pairs_collection.update_one(
                {"qa_id": qa_id},
                {
                    "$push": {"variants": new_variant},
                    "$set": {
                        "updated_at": datetime.utcnow(),
                        "last_edited_by": user_id
                    }
                }
            )
            
            # Create embedding for variant
            variant_embedding = get_embedding_azureRAG(variant_text)
            kc_embeddings_collection.insert_one({
                "embedding_id": str(uuid.uuid4()),
                "document_id": qa_pair['document_id'],
                "qa_id": qa_id,
                "text": variant_text,
                "text_type": "variant",
                "variant_id": variant_id,
                "embedding": variant_embedding,
                "embedding_model": "text-embedding-ada-002",
                "embedding_version": "2",
                "enabled": True,
                "created_at": datetime.utcnow()
            })
            
            log_audit("variant_added", "qa_pair", qa_id, user_id, {
                "variant_text": variant_text,
                "variant_id": variant_id
            })
            
            return jsonify({
                "success": True,
                "message": "Variant added successfully",
                "variant": new_variant,
                "total_variants": len(current_variants) + 1
            })
        
        except Exception as e:
            logger.error(f"Error adding variant: {e}")
            return jsonify({"success": False, "error": str(e)}), 500
    
    
    @app.route('/api/knowledge-corpus/qa-pairs/<qa_id>/variants/<variant_id>', methods=['PUT'])
    def edit_variant(qa_id, variant_id):
        """Edit an existing question variant"""
        try:
            user_id = session.get('user_id', 'test_admin')
            data = request.get_json()
            
            if not data or 'variant_text' not in data:
                return jsonify({"success": False, "error": "variant_text is required"}), 400
            
            variant_text = data['variant_text'].strip()
            if not variant_text:
                return jsonify({"success": False, "error": "Variant text cannot be empty"}), 400
            
            # Get the Q&A pair
            qa_pair = kc_qa_pairs_collection.find_one({"qa_id": qa_id})
            if not qa_pair:
                return jsonify({"success": False, "error": "Q&A pair not found"}), 404
            
            # Find the variant
            variants = qa_pair.get('variants', [])
            variant_index = None
            old_text = None
            
            for i, v in enumerate(variants):
                if v['variant_id'] == variant_id:
                    variant_index = i
                    old_text = v['text']
                    break
            
            if variant_index is None:
                return jsonify({"success": False, "error": "Variant not found"}), 404
            
            # Check for duplicate (excluding current variant)
            for i, v in enumerate(variants):
                if i != variant_index and v['text'].lower() == variant_text.lower():
                    return jsonify({"success": False, "error": "This variant already exists"}), 400
            
            # Update variant in array
            variants[variant_index]['text'] = variant_text
            variants[variant_index]['updated_at'] = datetime.utcnow()
            variants[variant_index]['updated_by'] = user_id
            
            # Update Q&A pair
            kc_qa_pairs_collection.update_one(
                {"qa_id": qa_id},
                {
                    "$set": {
                        "variants": variants,
                        "updated_at": datetime.utcnow(),
                        "last_edited_by": user_id
                    }
                }
            )
            
            # Update embedding
            new_embedding = get_embedding_azureRAG(variant_text)
            kc_embeddings_collection.update_one(
                {
                    "qa_id": qa_id,
                    "variant_id": variant_id
                },
                {
                    "$set": {
                        "text": variant_text,
                        "embedding": new_embedding,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            log_audit("variant_edited", "qa_pair", qa_id, user_id, {
                "variant_id": variant_id,
                "old_text": old_text,
                "new_text": variant_text
            })
            
            return jsonify({
                "success": True,
                "message": "Variant updated successfully",
                "variant": variants[variant_index]
            })
        
        except Exception as e:
            logger.error(f"Error editing variant: {e}")
            return jsonify({"success": False, "error": str(e)}), 500
    
    
    @app.route('/api/knowledge-corpus/qa-pairs/<qa_id>/variants/<variant_id>', methods=['DELETE'])
    def delete_variant(qa_id, variant_id):
        """Delete a question variant"""
        try:
            user_id = session.get('user_id', 'test_admin')
            
            # Get the Q&A pair
            qa_pair = kc_qa_pairs_collection.find_one({"qa_id": qa_id})
            if not qa_pair:
                return jsonify({"success": False, "error": "Q&A pair not found"}), 404
            
            # Find and remove the variant
            variants = qa_pair.get('variants', [])
            variant_found = False
            deleted_text = None
            
            new_variants = []
            for v in variants:
                if v['variant_id'] == variant_id:
                    variant_found = True
                    deleted_text = v['text']
                else:
                    new_variants.append(v)
            
            if not variant_found:
                return jsonify({"success": False, "error": "Variant not found"}), 404
            
            # Update Q&A pair
            kc_qa_pairs_collection.update_one(
                {"qa_id": qa_id},
                {
                    "$set": {
                        "variants": new_variants,
                        "updated_at": datetime.utcnow(),
                        "last_edited_by": user_id
                    }
                }
            )
            
            # Delete embedding
            kc_embeddings_collection.delete_one({
                "qa_id": qa_id,
                "variant_id": variant_id
            })
            
            log_audit("variant_deleted", "qa_pair", qa_id, user_id, {
                "variant_id": variant_id,
                "deleted_text": deleted_text
            })
            
            return jsonify({
                "success": True,
                "message": "Variant deleted successfully",
                "remaining_variants": len(new_variants)
            })
        
        except Exception as e:
            logger.error(f"Error deleting variant: {e}")
            return jsonify({"success": False, "error": str(e)}), 500



# ============================================================================
# Analytics Routes
# ============================================================================

def register_analytics_routes(app):
    """Register analytics routes"""
    
    @app.route('/api/knowledge-corpus/documents/<document_id>/statistics', methods=['GET'])
    def get_document_statistics(document_id):
        """Get document usage statistics"""
        try:
            # TODO: Temporarily bypass authentication for testing
            user_id = None
            try:
                if hasattr(current_user, 'id') and current_user.is_authenticated:
                    user_id = current_user.id
                else:
                    user_id = session.get('user_id') or request.args.get('user_id', 'test_admin')
            except:
                user_id = 'test_admin'
            
            # Skip admin check for now
            # if not user_id or not check_admin_access(user_id):
            #     return jsonify({"success": False, "error": "Admin access required"}), 403
            
            # Get query statistics
            queries = list(kc_user_queries_collection.find({"matched_qa_id": {"$exists": True}}))
            
            # Filter queries for this document's Q&A pairs
            document_qa_ids = [qa['qa_id'] for qa in kc_qa_pairs_collection.find({"document_id": document_id})]
            document_queries = [q for q in queries if q.get('matched_qa_id') in document_qa_ids]
            
            # Calculate statistics
            total_queries = len(document_queries)
            exact_matches = len([q for q in document_queries if q.get('match_type') == 'exact'])
            semantic_matches = len([q for q in document_queries if q.get('match_type', '').startswith('semantic')])
            thumbs_up = len([q for q in document_queries if q.get('user_feedback') == 'thumbs_up'])
            thumbs_down = len([q for q in document_queries if q.get('user_feedback') == 'thumbs_down'])
            
            satisfaction_rate = thumbs_up / (thumbs_up + thumbs_down) if (thumbs_up + thumbs_down) > 0 else 0
            
            # Get top questions
            qa_usage = {}
            for q in document_queries:
                qa_id = q.get('matched_qa_id')
                if qa_id:
                    if qa_id not in qa_usage:
                        qa_usage[qa_id] = {"count": 0, "thumbs_up": 0}
                    qa_usage[qa_id]['count'] += 1
                    if q.get('user_feedback') == 'thumbs_up':
                        qa_usage[qa_id]['thumbs_up'] += 1
            
            top_questions = []
            for qa_id, usage in sorted(qa_usage.items(), key=lambda x: x[1]['count'], reverse=True)[:10]:
                qa = kc_qa_pairs_collection.find_one({"qa_id": qa_id})
                if qa:
                    top_questions.append({
                        "question": qa['canonical_question'],
                        "times_asked": usage['count'],
                        "thumbs_up": usage['thumbs_up']
                    })
            
            return jsonify({
                "success": True,
                "statistics": {
                    "total_queries": total_queries,
                    "exact_matches": exact_matches,
                    "semantic_matches": semantic_matches,
                    "no_matches": 0,  # TODO: Track no-match queries
                    "thumbs_up": thumbs_up,
                    "thumbs_down": thumbs_down,
                    "satisfaction_rate": satisfaction_rate,
                    "top_questions": top_questions
                }
            })
        
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return jsonify({"success": False, "error": str(e)}), 500
