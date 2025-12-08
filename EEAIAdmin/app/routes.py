from __future__ import annotations

import json
import yaml
import mimetypes
import re
import shutil
import tempfile
import uuid
import threading
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict
import math
from decimal import Decimal
import hashlib
import concurrent.futures
from difflib import SequenceMatcher
LINE_HEIGHT_THRESHOLD = 0.5  # More lenient for same-line check
MAX_LINE_LENGTH = 80  # Skip refinement if any line > 80 chars
import bcrypt
import chromadb

try:
    from app.utils.chromadb_client import get_chromadb_client
except ImportError:
    # Fallback chromadb client if utils not available
    def get_chromadb_client(host=None, port=None):
        host = host or os.getenv('CHROMADB_HOST', 'localhost')
        port = port or int(os.getenv('CHROMADB_PORT', 8000))
        return chromadb.HttpClient(host=host, port=port)
try:
    import fitz
except ImportError:
    fitz = None
    

import fitz
import os
import sys
from pathlib import Path
import logging
import numpy as np
import cv2
import openai
import pandas as pd
from PIL import Image
from io import BytesIO
import base64
import zipfile

from PyPDF2 import PdfReader
from chromadb.utils import embedding_functions
from flask import Flask, render_template, request, send_file, jsonify, session, Response, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash as checkpw

# Import enhanced analysis systems
try:
    from app.utils.parallel_analyzer import get_parallel_analyzer, analyze_documents_parallel, get_analysis_results
    from app.utils.enhanced_document_preview import get_document_preview, preview_document_with_fields
    from app.utils.realtime_logger import get_realtime_logger, log_request, log_processing_step, log_info, log_error_msg

    ENHANCED_FEATURES_AVAILABLE = True
    from app.utils.daily_logger import log_system
    log_system("ENHANCED_FEATURES", message="Enhanced analysis features loaded successfully")
except ImportError as e:
    from app.utils.daily_logger import log_error
    log_error(f"Enhanced features not available: {e}",
              context="system_startup", 
              features=["parallel_analyzer", "document_preview", "realtime_logger"])
    ENHANCED_FEATURES_AVAILABLE = False


    # Create fallback decorators
    def log_request(func):
        """Fallback decorator when real-time logging not available"""
        return func


    def log_processing_step(message, details=None):
        """Fallback function when real-time logging not available"""
        pass


    def log_info(message, details=None):
        """Fallback function when real-time logging not available"""
        pass


    def log_error_msg(message, details=None):
        """Fallback function when real-time logging not available"""
        pass

from pymongo import MongoClient, DESCENDING
from bson import ObjectId
from functools import wraps
import zipfile
import cv2
from docx import Document
import tiktoken
from xml.etree.ElementTree import Element, SubElement, tostring
import time

# Optional QR code support
try:
    import qrcode
    QRCODE_AVAILABLE = True
    from app.utils.daily_logger import log_system
    log_system("QR_MODULE", message="QR code generation module loaded successfully")
except ImportError:
    from app.utils.daily_logger import log_error
    log_error("QR code generation not available: 'qrcode' module not installed",
              context="system_startup", 
              solution="Install with: pip install qrcode[pil]")
    QRCODE_AVAILABLE = False
    qrcode = None

# Placeholder imports for utility functions (replace with actual implementations)
from app.utils.common import load_schema
from app.utils.file_utils import get_embedding_azureRAG
from app.utils.query_utils import handle_ai_check,handle_guarantee_vetting_check, chroma_client

# Bounding Boxes Module (Separated Business Logic)
from app.backend.Smart_Document_Capture.Bounding_Boxes import (
    coordinate_mapper,
    FieldCoordinateMapper,
    normalize_date_for_search,
    normalize_amount_for_search,
    is_amount_field,
    is_date_in_valid_context,
    calculate_match_priority_score,
    search_text_in_ocr,
    fuzzy_match,
    strip_punctuation,
    merge_bboxes,
    get_bbox_center,
    calculate_distance,
    are_words_on_same_line,
    are_words_on_same_line_rotated,
    sort_words_left_to_right,
    sort_words_for_rotated_page,
    sort_words_reading_order,
    detect_page_rotation,
    is_standalone_punctuation,
    smart_sort_words,
    find_all_candidates_for_line,
    find_best_spatial_cluster,
    score_cluster,
    fallback_rotated_page_search,
    fallback_fuzzy_search,
    fallback_expand_existing_match,
    split_long_line_smart,
    refine_coordinate_response,
    process_coordinate_response
)

# WebSocket and Progress Tracking (Separated Business Logic)
from app.backend.WebSocket_And_ProgressUpdater import (
    get_websocket_handler,
    DocumentProcessingTracker,
    register_status_routes,
    get_llm_compliance_tracker,
    get_compliance_status_tracker,
    set_llm_compliance_status,
    set_compliance_status,
    llm_compliance_tracker,
    compliance_status_tracker
)

# Step-1 Quality Analysis Service (Separated Business Logic)
from app.backend.Smart_Document_Capture.Quality_Analysis import (
    QualityAnalysisService, 
    DocumentQualityAnalyzer
)
# Step-2 OCR Extraction Service (Separated Business Logic)
from app.backend.Smart_Document_Capture.Optical_Character_Recognition import (
    OCRExtractionService,
    OCRExtractionResult
)
# Step-3 Classification Service (Separated Business Logic)
from app.backend.Smart_Document_Capture.Document_Classification import (
    ClassificationService,
    ClassificationResult,
    PageClassification,
    DocumentClassifier
)
# Step-4 Document Validation Service (Separated Business Logic)
from app.backend.Smart_Document_Capture.Document_Validation import (
    DocumentValidationService,
    ValidationResult,
    validate_document_types,
    filter_duplicate_documents
)
# Step-5 Page Grouping Service (Separated Business Logic)
from app.backend.Smart_Document_Capture.Grouping_Pages import (
    PageGroupingService,
    GroupingResult,
    DocumentGroup,
    group_pages_by_document_type,
    generate_page_range
)
# Step-6 Entity Extraction Service (Separated Business Logic)
from app.backend.Smart_Document_Capture.Entity_Extraction import (
    extract_entities_in_chunks,
    extract_entities_parallel,
    filter_extracted_fields_by_type,
    load_document_field_mappings,
    process_page_with_llm_analysis
)
# Step-7 Compliance and Discrepancies Service (Separated Business Logic)
from app.backend.Smart_Document_Capture.Compliance_And_Discrepancies import (
    DiscrepancyRuleManager,
    get_discrepancy_rule_manager,
    load_discrepancy_rules_from_xml,
    load_discrepancy_config,
    perform_pure_llm_discrepancy_analysis,
    analyze_comprehensive_trade_finance_discrepancies,
    analyze_individual_document_discrepancies,
    extract_lc_structured_data,
    extract_enhanced_lc_data,
    extract_enhanced_swift_data,
    extract_enhanced_document_data,
    enhance_documents_for_discrepancy_analysis,
    enhance_data_for_professional_ui,
    LLMComplianceEngine,
    # Field-Level Compliance Analysis (for document classification)
    FieldLevelComplianceAnalyzer,
    get_unified_compliance_result as get_module_compliance_result,
    clear_unified_compliance_result as clear_module_compliance_result,
    analyze_field_level_compliance
)
# Step-8 Required Documents Parsing (Separated Business Logic)
from app.backend.Smart_Document_Capture.Required_Documents import (
    RequiredDocumentsParser,
    parse_required_documents_from_text,
    parse_required_documents_simple
)
# Step-9 LC Additional Conditions Parsing & Validation (Separated Business Logic)
from app.backend.Smart_Document_Capture.Additional_Conditions import (
    LCConditionsParser,
    LCConditionsValidator
)
# Smart Document Capture Using QR (Separated Business Logic)
from app.backend.Smart_Document_Capture_Using_QR import (
    QRService,
    detect_qr_with_multi_fallback,
    detect_qr_with_azure,
    detect_qr_with_openai,
    detect_qr_with_patterns,
    analyze_text_for_qr_patterns,
    looks_like_trade_finance_data,
    extract_qr_from_pdf,
    extract_qr_from_word,
    extract_qr_from_image,
    parse_structured_qr_text,
    parse_qr_with_llm,
    validate_and_structure_qr_data
)
from app.backend.Smart_Document_Capture_Using_QR.qr_routes import register_qr_routes
# Auth And User Management Module (Separated Business Logic)
from app.backend.Auth_And_User_Management import (
    # Models
    User, UserSession,
    # Validators
    validate_email, validate_password, validate_name,
    # Repositories
    UserRepository, SessionRepository,
    # Decorators
    login_required, timing_aspect,
    # Session Management Functions
    get_or_create_session, save_to_conversation, get_conversation_context,
    get_latest_session_id, retrieve_conversation_history,
    # Constants
    SESSION_TIMEOUT_SECONDS, ALLOWED_EMAILS,
    # Route Registration
    register_auth_routes
)
# Session Manager initialization function
from app.backend.Auth_And_User_Management.session_manager import initialize_collections as init_session_manager

# SWIFT Processing Module (Separated Business Logic)
from app.backend.SWIFT_Processing import (
    # Formatters
    format_swift_date,
    format_address_field,
    format_bank_field,
    # Parsers
    parse_swift_message_text,
    parse_swift_message_for_ui,
    extract_beneficiary_from_swift,
    extract_applicant_from_swift,
    extract_currency_from_amount,
    # Generator
    generate_mt700_message,
    # Routes
    register_swift_routes
)

# Admin Configuration Module (Separated Business Logic)
from app.backend.Admin_Configuraton import (
    DataCategoryManager,
    EntityManager,
    DocumentCategoryManager,
    DocumentTypeCategoryManager,
    DocumentEntityMappingManager,
    PromptConfigManager
)
from app.utils import (
    process_user_query, handle_api_request, trigger_proactive_alerts,
    generate_sql_query, execute_sql_and_format, generate_visualization_with_inference,
    analyze_document_with_gpt, handle_follow_up_request, insert_trx_file_upload, insert_trx_file_detail,
    insert_trx_sub_files, insert_faef_em_inv, handle_creation_transaction_request,
    generate_rag_table_or_report_request, load_faiss_index, generate_response,
    classify_document_gpt
)
from app.utils.query_utils import (
    extract_exportable_data_from_context, retrieve_export_data_from_rag,
    combine_conversation_and_rag_data, generate_export_file,
    generate_export_follow_up_questions, analyze_unified_compliance_fast
)
from app.utils.conversation_manager import ConversationManager
from app.utils.app_config import deployment_name, embedding_model, COMPUTER_VISION_ENDPOINT, COMPUTER_VISION_KEY
from app.utils.vetting_engine import VettingRuleEngine
from app import custom_functions_routes

# Initialize Flask app and logging
app = Flask(__name__)
app.secret_key = os.urandom(24)  # Secure random secret key
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# =====================================================
# BACKWARD COMPATIBILITY: extract_text_from_file wrapper
# BACKWARD COMPATIBILITY: extract_text_from_file wrapper
# This function wraps OCRExtractionService to maintain backward compatibility
# with existing code that calls extract_text_from_file directly.
# =====================================================
def extract_text_from_file(file_path, file_type):
    """
    Backward-compatible wrapper for OCR extraction.
    Delegates to OCRExtractionService while maintaining the old interface.
    
    Args:
        file_path (str): Path to the file to process.
        file_type (str): MIME type of the file.
    
    Returns:
        dict: A dictionary containing extracted text data or error information.
    """
    try:
        ocr_service = OCRExtractionService()
        result = ocr_service.extract(
            temp_file_path=file_path,
            file_type=file_type
        )
        
        if result.success:
            return {
                "text_data": result.text_data,
                "processing_time": result.processing_time,
                "overall_confidence": result.overall_confidence
            }
        else:
            return {"error": result.error, "text_data": []}
    except Exception as e:
        logger.error(f"extract_text_from_file wrapper error: {e}")
        return {"error": str(e), "text_data": []}


# User-friendly logging helpers
class UserLogger:
    """User-friendly logging helper class"""

    @staticmethod
    def start_process(process_name, details=""):
        """Log the start of a process"""
        msg = f"🚀 Starting: {process_name}"
        if details:
            msg += f" | {details}"
        logger.info(msg)

    @staticmethod
    def complete_process(process_name, duration=None, result_count=None):
        """Log the completion of a process"""
        msg = f"✅ Completed: {process_name}"
        if duration:
            msg += f" | Duration: {duration:.2f}s"
        if result_count is not None:
            msg += f" | Results: {result_count}"
        logger.info(msg)

    @staticmethod
    def processing_step(step_name, status="in progress"):
        """Log a processing step"""
        if status.lower() == "complete":
            logger.info(f"   ✓ {step_name}")
        elif status.lower() == "failed":
            logger.error(f"   ✗ {step_name}")
        else:
            logger.info(f"   🔄 {step_name}")

    @staticmethod
    def data_info(data_type, count, additional_info=""):
        """Log data information"""
        msg = f"📊 {data_type}: {count}"
        if additional_info:
            msg += f" | {additional_info}"
        logger.info(msg)

    @staticmethod
    def api_call(service_name, endpoint="", status="starting"):
        """Log API call information"""
        if status.lower() == "starting":
            msg = f"🌐 API Call: {service_name}"
            if endpoint:
                msg += f" | Endpoint: {endpoint}"
            logger.info(msg)
        elif status.lower() == "success":
            logger.info(f"   ✅ {service_name} - Success")
        elif status.lower() == "failed":
            logger.error(f"   ❌ {service_name} - Failed")

    @staticmethod
    def file_operation(operation, file_path, status="starting"):
        """Log file operations"""
        file_name = os.path.basename(file_path)
        if status.lower() == "starting":
            logger.info(f"📁 {operation}: {file_name}")
        elif status.lower() == "success":
            logger.info(f"   ✅ {file_name} - {operation} successful")
        elif status.lower() == "failed":
            logger.error(f"   ❌ {file_name} - {operation} failed")

    @staticmethod
    def user_action(action, user_info="", additional_context=""):
        """Log user actions"""
        msg = f"👤 User Action: {action}"
        if user_info:
            msg += f" | User: {user_info}"
        if additional_context:
            msg += f" | {additional_context}"
        logger.info(msg)

    @staticmethod
    def warning(message, suggestion=""):
        """Log warnings with suggestions"""
        msg = f"⚠️ Warning: {message}"
        if suggestion:
            msg += f" | Suggestion: {suggestion}"
        logger.warning(msg)

    @staticmethod
    def error(error_message, context="", suggestion=""):
        """Log errors with context and suggestions"""
        msg = f"❌ Error: {error_message}"
        if context:
            msg += f" | Context: {context}"
        if suggestion:
            msg += f" | Suggestion: {suggestion}"
        logger.error(msg)

    @staticmethod
    def api_request(endpoint, description=""):
        """Log API request information"""
        msg = f"🌐 API Request: {endpoint}"
        if description:
            msg += f" | {description}"
        logger.info(msg)

    @staticmethod
    def success(message, details=None):
        """Log success messages with optional details"""
        msg = f"✅ {message}"
        if details:
            if isinstance(details, dict):
                detail_str = ", ".join([f"{k}: {v}" for k, v in details.items()])
                msg += f" | {detail_str}"
            else:
                msg += f" | {details}"
        logger.info(msg)

    @staticmethod
    def info(message, details=None):
        """Log info messages with optional details"""
        msg = f"ℹ️  {message}"
        if details:
            if isinstance(details, dict):
                detail_str = ", ".join([f"{k}: {v}" for k, v in details.items()])
                msg += f" | {detail_str}"
            else:
                msg += f" | {details}"
        logger.info(msg)


# Create global instance for easy access
try:
    user_logger = UserLogger()
except Exception as e:
    # Fallback to basic logger wrapper if UserLogger fails
    class BasicUserLogger:
        @staticmethod
        def start_process(process_name, details=""):
            logger.info(f"Starting: {process_name} {details}")

        @staticmethod
        def complete_process(process_name, duration=None, result_count=None):
            logger.info(f"Completed: {process_name}")
        # Add other basic methods as needed


    user_logger = BasicUserLogger()
    logger.warning(f"UserLogger setup failed, using basic fallback: {e}")
    
    
# MongoDB Configuration - Using centralized manager
from app.utils.mongodb_manager import get_mongo_client, get_database

client = get_mongo_client()
db = get_database(client)

# Collections
users_collection = db.users if db is not None else None
sessions_collection = db.sessions if db is not None else None
conversation_collection = db.conversation_history if db is not None else None
chat_sessions_collection = db.chat_sessions if db is not None else None
chat_messages_collection = db.chat_messages if db is not None else None
metrics_collection = db.request_metrics if db is not None else None  # New collection for metrics

# Knowledge Corpus collections
kc_documents_collection = db.knowledge_corpus_documents
kc_pages_collection = db.knowledge_corpus_pages
kc_qa_pairs_collection = db.knowledge_corpus_qa_pairs
kc_embeddings_collection = db.knowledge_corpus_embeddings
kc_user_queries_collection = db.knowledge_corpus_user_queries
kc_audit_log_collection = db.knowledge_corpus_audit_log

# Initialize Auth_And_User_Management module with database connections
init_session_manager(db, conversation_collection)
from app.backend.Auth_And_User_Management.repositories import initialize_db as init_auth_db
init_auth_db(db, users_collection, sessions_collection)
logger.info("✅ Auth_And_User_Management module initialized with database connections")

# Initialize conversation manager
conversation_manager = ConversationManager(db)


# ------------------------------
# ChromaDB per-customer manager
# ------------------------------
def get_request_customer_id() -> Optional[str]:
    """Try to determine customer id for current request/session.

    Order of checks:
    - session['customer_id']
    - current user record -> user.get('customer_id')
    - request header 'X-Customer-Id'
    - request.args 'customer_id'
    Returns None if not found.
    """
    try:
        cid = None
        cid = session.get('customer_id') if session is not None else None
        if not cid:
            user_id = session.get('user_id') if session is not None else None
            if user_id:
                user = users_collection.find_one({'_id': user_id})
                cid = user.get('customer_id') if user and user.get('customer_id') else None

        # Check headers and query params as fallback
        if not cid:
            cid = request.headers.get('X-Customer-Id') or request.args.get('customer_id')

        return cid
    except Exception:
        return None


def is_chroma_enabled_for_customer(customer_id: Optional[str]) -> bool:
    """Return True if ChromaDB is enabled for given customer.

    This checks the `repository_config` collection for an active chromadb entry.
    The repository document may use either:
      - 'enabled_for_all': True/False
      - 'customers': [list of customer ids]
    If no repository config exists, returns False.
    """
    try:
        repo = db.repository_config.find_one({'type': 'chromadb', 'is_active': True})
        if not repo:
            return False
        if repo.get('enabled_for_all'):
            return True
        customers = repo.get('customers', []) or repo.get('allowed_customers', [])
        if customer_id and customers and isinstance(customers, list):
            return customer_id in customers
        return False
    except Exception:
        return False


def get_chroma_client_for_customer(customer_id: Optional[str] = None):
    """Return a ChromaDB client when configured and allowed for the customer, else None."""
    try:
        # Determine whether Chroma is enabled for this customer
        if not is_chroma_enabled_for_customer(customer_id):
            return None

        # Read repository config for connection details
        repo = db.repository_config.find_one({'type': 'chromadb', 'is_active': True})
        if not repo:
            return None

        host = repo.get('host') or os.getenv('CHROMADB_HOST', 'localhost')
        port = int(repo.get('port') or os.getenv('CHROMADB_PORT', 8000))

        # Use existing helper if available
        try:
            client = get_chromadb_client(host=host, port=port)
            return client
        except Exception:
            # Best-effort fallback to chromadb.HttpClient if available
            try:
                import chromadb
                return chromadb.HttpClient(host=host, port=port)
            except Exception:
                logger.warning('ChromaDB client could not be created for host=%s port=%s', host, port)
                return None

    except Exception as e:
        logger.error(f"Error creating Chroma client for customer {customer_id}: {e}")
        return None

# Initialize vetting rule engine (will be set in setup_routes)
vetting_engine = None

def load_prompt_config():
    """
    Load prompt configuration from YAML file.
    This reads the document_classification_config.yaml and extracts prompt templates.
    """
    try:
        config_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'document_classification_config.yaml')
        user_logger.file_operation("Loading", config_path, "starting")
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        user_logger.file_operation("Loading", config_path, "success")
        user_logger.data_info("Configuration entries", len(config) if config else 0)
        return config
    except Exception as e:
        user_logger.file_operation("Loading", config_path, "failed")
        user_logger.error("Failed to load prompt config", str(e), "Check file path and YAML syntax")
        return None

def build_classification_prompt_from_config(ocr_text, function_description=None):
    """
    Build classification prompt using config templates and replace {{placeholders}}.

    Args:
        ocr_text: OCR text to classify
        function_description: Optional custom function description

    Returns:
        Complete prompt string with all placeholders replaced
    """
    try:
        # Load config
        config = load_prompt_config()
        if not config:
            return None

        # Get unified prompts section
        unified_prompts = config.get('prompts', {}).get('unified', {})
        system_prompt_template = unified_prompts.get('system_prompt_config', '')
        functionality_template = unified_prompts.get('functionality_prompt', '')
        response_template = unified_prompts.get('response_prompt', '')

        # === STEP 1: Replace {{comprehensive_list_of_documents}} ===
        # Load actual document types from your database/JSON
        doc_categories_data = load_document_categories_from_json()  # Your existing function

        # Format document list
        doc_list_formatted = ""
        for category in doc_categories_data:
            cat_name = category.get('category_name', 'Unknown')
            doc_list_formatted += f"\n{cat_name}:\n"
            for doc in category.get('documents', []):
                doc_list_formatted += f"  - {doc.get('document_name', 'Unknown')}\n"

        # Replace placeholder in system prompt
        system_prompt = system_prompt_template.replace(
            '{{comprehensive_list_of_documents}}',
            doc_list_formatted
        )

        # === STEP 2: Replace {{function_description}} ===
        func_desc = function_description or "general document processing"
        functionality_prompt = functionality_template.replace(
            '{{function_description}}',
            func_desc
        )

        # === STEP 3: Replace {{function_and_document_json}} with enhanced field mappings ===
        # Load custom function details if function_description provided
        function_json = "{}"
        field_mapping_examples = ""

        if function_description:
            try:
                custom_functions_data = load_custom_functions_from_json()
                for func in custom_functions_data.get('functions', []):
                    if func.get('name') == function_description:
                        function_json = json.dumps(func, indent=2)

                        # Load field mapping examples for required documents
                        doc_requirements = func.get('documentRequirements', [])
                        if doc_requirements:
                            field_mapping_examples += "\n\n=== Field Mapping Examples for Required Documents ===\n"
                            for req in doc_requirements[:3]:  # Limit to first 3 documents
                                doc_name = req.get('documentName', '')
                                if doc_name:
                                    field_example = load_document_field_mappings(doc_name)
                                    if field_example:
                                        field_mapping_examples += field_example
                        break
            except Exception as e:
                logger.warning(f"Error loading function details: {e}")

        # Combine function JSON with field mapping examples
        enhanced_function_context = function_json + field_mapping_examples

        functionality_prompt = functionality_prompt.replace(
            '{{function_and_document_json}}',
            enhanced_function_context
        )

        # === STEP 4: Build complete prompt ===
        complete_prompt = f"""
{system_prompt}

{functionality_prompt}

OCR Text to Classify:
\"\"\"{ocr_text[:5000]}\"\"\"

{response_template}
"""

        prompt_chars = len(complete_prompt)
        logger.info(f"SUCCESS: Built classification prompt from config ({prompt_chars} chars)")
        return complete_prompt

    except Exception as e:
        logger.error(f"ERROR: Error building prompt from config: {e}")
        return None

def load_custom_functions_from_json():
    """Load custom functions from JSON file"""
    try:
        functions_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'custom_functions.json')
        with open(functions_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading custom functions: {e}")
        return {'functions': []}

def load_document_categories_from_json():
    """Load document categories with documents list"""
    try:
        categories_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'document_categories.json')
        with open(categories_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('categories', [])
    except Exception as e:
        logger.error(f"Error loading document categories: {e}")
        return []

# NOTE: load_document_field_mappings is now imported from Step6_Entity_Extraction module

# Load Trade Document Data Elements Mapping
trade_document_elements = None
def load_trade_document_elements():
    """Load the trade document data elements mapping from JSON file"""
    global trade_document_elements
    try:
        elements_path = os.path.join(os.path.dirname(__file__), 'prompts', 'trade_document_data_elements.json')
        with open(elements_path, 'r', encoding='utf-8') as f:
            trade_document_elements = json.load(f)
        logger.info("SUCCESS: Trade document data elements mapping loaded successfully")
        return trade_document_elements
    except Exception as e:
        logger.error(f"ERROR: Error loading trade document data elements: {str(e)}")
        return None

# Get Prompt Template Helper
def get_prompt_template(category, subcategory=None):
    """Get prompt template from configuration

    Args:
        category: 'classification', 'extraction', or 'compliance'
        subcategory: Optional subcategory like 'ucp600', 'swift_mt700', etc.

    Returns:
        str: Prompt template or None if not found
    """
    prompt_config = load_prompt_config()
    if not prompt_config:
        return None

    try:
        if subcategory:
            template = prompt_config.get('prompts', {}).get(subcategory, {}).get('template')
            if template:
                logger.info(f"INFO: Using {subcategory} template from YAML config")
            return template
        else:
            template = prompt_config.get('prompts', {}).get(category, {}).get('template')
            if template:
                logger.info(f"INFO: Using {category} template from YAML config")
            else:
                logger.warning(f"WARNING: No {category} template found in YAML, using fallback")
            return template
    except Exception as e:
        logger.error(f"Error getting prompt template for {category}/{subcategory}: {e}")
        return None

def get_required_fields_for_document(document_code):
    """Get mandatory and optional fields for a specific document type"""
    if not trade_document_elements:
        load_trade_document_elements()

    if not trade_document_elements:
        return {"mandatory": [], "optional": [], "conditional": []}

    required_fields = {"mandatory": [], "optional": [], "conditional": []}

    # Search through all data element categories
    for category_name, elements in trade_document_elements.get("data_elements", {}).items():
        for element in elements:
            requirements = element.get("requirements", {})
            if document_code in requirements:
                field_info = {
                    "uid": element.get("uid"),
                    "name": element.get("name"),
                    "description": element.get("description"),
                    "category": category_name
                }

                requirement_type = requirements[document_code]
                if requirement_type == "M":
                    required_fields["mandatory"].append(field_info)
                elif requirement_type == "O":
                    required_fields["optional"].append(field_info)
                elif requirement_type == "C":
                    required_fields["conditional"].append(field_info)

    return required_fields

def get_document_info_by_code(document_code):
    """Get document metadata by document code"""
    if not trade_document_elements:
        load_trade_document_elements()

    if not trade_document_elements:
        return None

    for doc in trade_document_elements.get("documents", []):
        if doc.get("code") == document_code:
            return doc
    return None

# Create indexes
users_collection.create_index("email", unique=True)
sessions_collection.create_index("sessionId", unique=True)
sessions_collection.create_index("lastAccessed", expireAfterSeconds=24 * 60 * 60)
metrics_collection.create_index([("timestamp", DESCENDING)])  # Index for metrics

# Create indexes for chat collections
chat_sessions_collection.create_index([("user_id", 1), ("session_id", 1)], unique=True)
chat_sessions_collection.create_index("last_activity", expireAfterSeconds=30 * 24 * 60 * 60)  # 30 days
chat_messages_collection.create_index([("session_id", 1), ("timestamp", 1)])
chat_messages_collection.create_index("user_id")

# Create indexes for Knowledge Corpus collections
kc_documents_collection.create_index("document_id", unique=True)
kc_documents_collection.create_index("status")
kc_documents_collection.create_index("uploaded_by")
kc_documents_collection.create_index([("created_at", DESCENDING)])
kc_documents_collection.create_index("tags")

kc_pages_collection.create_index("page_id", unique=True)
kc_pages_collection.create_index([("document_id", 1), ("page_number", 1)])

kc_qa_pairs_collection.create_index("qa_id", unique=True)
kc_qa_pairs_collection.create_index("document_id")
kc_qa_pairs_collection.create_index("page_id")
kc_qa_pairs_collection.create_index("approved")
kc_qa_pairs_collection.create_index([("canonical_question", "text")])

kc_embeddings_collection.create_index("embedding_id", unique=True)
kc_embeddings_collection.create_index("document_id")
kc_embeddings_collection.create_index("qa_id")
kc_embeddings_collection.create_index("enabled")

kc_user_queries_collection.create_index("query_id", unique=True)
kc_user_queries_collection.create_index("user_id")
kc_user_queries_collection.create_index("matched_qa_id")
kc_user_queries_collection.create_index([("query_timestamp", DESCENDING)])
kc_user_queries_collection.create_index("user_feedback")

kc_audit_log_collection.create_index("log_id", unique=True)
kc_audit_log_collection.create_index([("entity_type", 1), ("entity_id", 1)])
kc_audit_log_collection.create_index("user_id")
kc_audit_log_collection.create_index([("timestamp", DESCENDING)])



# login_required decorator is now imported from app.backend.Auth_And_User_Management

logger.info("Connected to MongoDB successfully")

# Constants - SESSION_TIMEOUT_SECONDS and ALLOWED_EMAILS are imported from Auth_And_User_Management
CUSTOM_RULES_PATH = "app/utils/prompts/custom_combined_rules.json"

ALLOWED_FILE_TYPES = ["application/pdf", "image/jpeg", "image/png", "text/plain", "application/zip",
                      "application/x-zip-compressed"]

# Schema
schema = load_schema()

# Repository management - store active repository per user
active_user_repositories = {}
active_user_modules = {}

def convert_decimal(obj: Any) -> Any:
    """Convert Decimal to float for JSON serialization."""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def safe_json(data: Any) -> Any:
    """Sanitize data for JSON serialization."""
    if isinstance(data, dict):
        return {k: safe_json(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [safe_json(v) for v in data]
    elif isinstance(data, float):
        if math.isnan(data) or math.isinf(data):
            return None
        return data
    elif isinstance(data, Decimal):
        if data.is_nan() or data.is_infinite():
            return None
        return float(data)
    return data


def serialize_enriched_schema(obj: Any) -> Any:
    """Custom serializer for datetime and Decimal objects."""
    if isinstance(obj, datetime):
        return obj.strftime('%Y-%m-%d')
    elif isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Type {type(obj)} not serializable")


def format_llm_answer(text: str) -> str:
    if not text:
        return ""

    # Headings
    text = re.sub(r'(?m)^### (.+)', r'<h3>\1</h3>', text)
    text = re.sub(r'(?m)^## (.+)', r'<h2>\1</h2>', text)
    text = re.sub(r'(?m)^# (.+)', r'<h1>\1</h1>', text)

    # Bold / Italic
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)

    lines = text.splitlines()
    html = []
    in_ul = False
    in_ol = False

    for line in lines:
        line = line.strip()

        # Numbered list
        if re.match(r'^\d+\.\s+', line):
            if in_ul:
                html.append("</ul>")
                in_ul = False
            if not in_ol:
                html.append('<ul style="color: black; font-size: inherit; padding-left: 1.2rem;">')
                in_ol = True
            content = re.sub(r'^\d+\.\s+', '', line)
            html.append(f'<li style="color: black; font-size: inherit;">{content}</li>')

        # Bullet list
        elif re.match(r'^[-*+]\s+', line):
            if in_ol:
                html.append("</ul>")
                in_ol = False
            if not in_ul:
                html.append('<ul style="color: black; font-size: inherit; padding-left: 1.2rem;">')
                in_ul = True
            content = re.sub(r'^[-*+]\s+', '', line)
            html.append(f'<li style="color: black; font-size: inherit;">{content}</li>')

        elif line:
            if in_ul:
                html.append("</ul>")
                in_ul = False
            if in_ol:
                html.append("</ul>")
                in_ol = False
            html.append(f'<p>{line}</p>')

    if in_ul:
        html.append("</ul>")
    if in_ol:
        html.append("</ul>")

    return "\n".join(html)


def setup_auth_routes(app: Flask):
    """Data Categories Management Routes"""
    # custom_functions_routes.register_custom_functions_routes(app)
def _calculate_average_metrics(page_results):
    """
    Calculate average metrics across all analyzed pages for frontend visualization.
    
    Args:
        page_results: List of page analysis results from quality analyzer
        
    Returns:
        Dictionary with averaged metrics suitable for charts/graphs
    """
    if not page_results:
        return {}
    
    # Initialize metrics accumulator
    metrics_sum = {}
    valid_pages = 0
    
    for page_result in page_results:
        metrics = page_result.get("metrics", {})
        if not metrics:
            continue
            
        valid_pages += 1
        
        # Accumulate all numeric metrics
        for metric_name, metric_value in metrics.items():
            if isinstance(metric_value, (int, float)):
                if metric_name not in metrics_sum:
                    metrics_sum[metric_name] = 0
                metrics_sum[metric_name] += metric_value
    
    if valid_pages == 0:
        return {}
    
    # Calculate averages and format for frontend consumption
    averaged_metrics = {}
    for metric_name, total_value in metrics_sum.items():
        avg_value = total_value / valid_pages
        averaged_metrics[metric_name] = {
            "value": round(avg_value, 3),
            "percentage": round(avg_value * 100, 1) if avg_value <= 1.0 else round(avg_value, 1),
            "label": metric_name.replace("_", " ").title(),
            "chart_category": _get_metric_chart_category(metric_name)
        }
    
    # Add summary statistics for frontend
    averaged_metrics["_summary"] = {
        "total_pages_analyzed": valid_pages,
        "overall_quality_rating": _get_quality_rating(averaged_metrics),
        "chart_ready": True,
        "visualization_recommendations": _get_visualization_recommendations(averaged_metrics)
    }
    
    return averaged_metrics


def _get_metric_chart_category(metric_name):
    """Categorize metrics for different chart types in frontend."""
    quality_metrics = ["blur_score", "sharpness_score", "text_clarity", "overall_readability"]
    technical_metrics = ["resolution_quality", "contrast_score", "brightness_score"]
    detection_metrics = ["noise_level", "shadow_glare_score", "edge_quality", "skew_angle"]
    
    if metric_name in quality_metrics:
        return "quality"
    elif metric_name in technical_metrics:
        return "technical"
    elif metric_name in detection_metrics:
        return "detection"
    else:
        return "other"


def _get_quality_rating(averaged_metrics):
    """Calculate overall quality rating for frontend display."""
    if not averaged_metrics:
        return "unknown"
    
    # Key quality indicators
    key_metrics = ["text_clarity", "overall_readability", "sharpness_score"]
    total_score = 0
    valid_metrics = 0
    
    for metric_name in key_metrics:
        if metric_name in averaged_metrics:
            total_score += averaged_metrics[metric_name]["value"]
            valid_metrics += 1
    
    if valid_metrics == 0:
        return "unknown"
    
    avg_quality = total_score / valid_metrics
    
    if avg_quality >= 0.8:
        return "excellent"
    elif avg_quality >= 0.6:
        return "good"
    elif avg_quality >= 0.4:
        return "medium"
    else:
        return "poor"


def _get_visualization_recommendations(averaged_metrics):
    """Provide recommendations for frontend visualization."""
    if not averaged_metrics:
        return []
    
    recommendations = []
    
    # Check for specific metric patterns
    if "text_clarity" in averaged_metrics:
        clarity_val = averaged_metrics["text_clarity"]["value"]
        if clarity_val < 0.5:
            recommendations.append({
                "type": "alert",
                "message": "Low text clarity detected - consider document reupload",
                "chart_highlight": "text_clarity"
            })
    
    if "blur_score" in averaged_metrics:
        blur_val = averaged_metrics["blur_score"]["value"]
        if blur_val > 0.7:  # High blur score is bad
            recommendations.append({
                "type": "warning", 
                "message": "Document blur detected - may affect OCR accuracy",
                "chart_highlight": "blur_score"
            })
    
    if "skew_angle" in averaged_metrics:
        skew_val = abs(averaged_metrics["skew_angle"]["value"])
        if skew_val > 5.0:  # More than 5 degrees
            recommendations.append({
                "type": "info",
                "message": "Document skew detected - consider rotation correction",
                "chart_highlight": "skew_angle"
            })
    
    return recommendations

# ============================================================================
# Utility Functions for Knowledge Corpus
# ============================================================================

def split_text(text: str, chunk_size: int = 500) -> List[str]:
    """Split text into chunks for processing."""
    words = text.split()
    return [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]


def read_pdf(file_path: str) -> str:
    """Read PDF content with proper file handle closure and encryption handling."""
    try:
        with open(file_path, 'rb') as file:
            reader = PdfReader(file)

            # Check if PDF is encrypted
            if reader.is_encrypted:
                # Try to decrypt with empty password (common for read-protected PDFs)
                try:
                    reader.decrypt('')
                except:
                    logger.warning(f"PDF {file_path} is encrypted and cannot be decrypted with empty password")
                    # Fall back to OCR for encrypted PDFs
                    return None

            # Extract text from all pages
            text_parts = []
            for page_num, page in enumerate(reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                except Exception as page_error:
                    logger.warning(f"Error extracting text from page {page_num}: {page_error}")
                    continue

            text = "\n".join(text_parts)

            # If no text extracted, return None to trigger OCR fallback
            if not text.strip():
                logger.warning(f"No text extracted from PDF {file_path} using PyPDF2")
                return None

            return text

    except Exception as e:
        logger.error(f"Error reading PDF {file_path}: {e}")
        # Return None instead of empty string to signal OCR fallback needed
        return None


def setup_routes(app: Flask):
    """Data Categories Management Routes"""
    
    # Add context processor for branding and feature flags
    @app.context_processor
    def inject_branding_config():
        """Inject branding configuration into all templates"""
        show_logo = os.getenv('SHOW_FINSTACK_LOGO', 'true').lower() in ('true', '1', 'yes')
        logo_filename = os.getenv('LOGO_FILENAME', 'finstack.png')
        enable_admin = os.getenv('ENABLE_ADMIN_CONFIG', 'true').lower() in ('true', '1', 'yes')
        
        # Extract brand title from logo filename (e.g., 'finstack.png' -> 'Finstack')
        brand_title = logo_filename.split('.')[0].title() if show_logo else 'Platform'
        
        return dict(
            show_logo=show_logo,
            logo_filename=logo_filename,
            enable_admin_config=enable_admin,
            brand_title=brand_title
        )
    
    # Initialize ChromaDB client and collections early
    customer_id = get_request_customer_id()
    chroma_client = get_chroma_client_for_customer(customer_id)
    
    # Only create collection if ChromaDB is enabled
    user_manual_collection = None
    if chroma_client:
        try:
            user_manual_collection = chroma_client.get_or_create_collection("user_manual")
        except Exception as e:
            logger.warning(f"Failed to create user_manual collection: {e}")
            user_manual_collection = None
    
    # Define helper functions needed by route registrations
    def clear_conversation_history(user_id, session_id=None):
        """
        Clear conversation history for a user or specific session from MongoDB.

        Args:
            user_id (str): The ID of the user whose history is to be cleared.
            session_id (str, optional): The specific session ID to clear.
        """
        try:
            collection = db.conversation_history
            query = {"user_id": user_id}
            if session_id:
                query["session_id"] = session_id

            result = collection.delete_many(query)
            deleted_count = result.deleted_count
            logger.info(
                f"Cleared {deleted_count} conversation history entries for user_id: {user_id}, "
                f"session_id: {session_id or 'all'}"
            )
            return deleted_count
        except Exception as e:
            logger.error(f"Failed to clear conversation history: {e}")
            raise
    
    custom_functions_routes.register_custom_functions_routes(app)

    # Initialize autocomplete routes
    from app.autocomplete_routes import autocomplete_bp
    app.register_blueprint(autocomplete_bp)
    logger.info("✅ Registered autocomplete routes")

    # Initialize QR Code routes (Smart Document Capture Using QR)
    register_qr_routes(app)
    logger.info("✅ Registered QR code routes")

    # Initialize Bounding Box routes (Smart Document Capture - Field Coordinates)
    from app.backend.Smart_Document_Capture.Bounding_Boxes import register_bounding_box_routes
    register_bounding_box_routes(app)
    logger.info("✅ Registered Bounding Box routes")

    # Initialize Required Documents routes (Smart Document Capture)
    from app.backend.Smart_Document_Capture.Required_Documents import register_required_documents_routes
    register_required_documents_routes(app, timing_aspect)
    logger.info("✅ Registered Required Documents routes")

    # Initialize Additional Conditions routes (Smart Document Capture)
    from app.backend.Smart_Document_Capture.Additional_Conditions import register_additional_conditions_routes
    register_additional_conditions_routes(app, timing_aspect)
    logger.info("✅ Registered Additional Conditions routes")

    # Initialize SWIFT Processing routes
    register_swift_routes(app, db)
    logger.info("✅ Registered SWIFT processing routes")

    # Initialize WebSocket and Progress Status routes
    register_status_routes(app, ENHANCED_FEATURES_AVAILABLE, 
                          get_realtime_logger if ENHANCED_FEATURES_AVAILABLE else None,
                          get_parallel_analyzer if ENHANCED_FEATURES_AVAILABLE else None)
    logger.info("✅ Registered status and progress tracking routes")

    # Initialize Knowledge Corpus routes
    from app import knowledge_corpus_routes
    knowledge_corpus_collections = {
        'documents': kc_documents_collection,
        'pages': kc_pages_collection,
        'qa_pairs': kc_qa_pairs_collection,
        'embeddings': kc_embeddings_collection,
        'user_queries': kc_user_queries_collection,
        'audit_log': kc_audit_log_collection
    }
    knowledge_corpus_utils = {
        'get_embedding': get_embedding_azureRAG,
        'extract_text': extract_text_from_file,
        'read_pdf': read_pdf,
        'split_text': split_text,
        'deployment_name': deployment_name,
        'logger': logger,
        'allowed_emails': ALLOWED_EMAILS
    }
    knowledge_corpus_routes.init_knowledge_corpus_routes(app, knowledge_corpus_collections, knowledge_corpus_utils)

    # Initialize Database Configuration routes
    from app.backend.Database_Configuration import register_database_config_routes, register_repository_module_routes
    register_database_config_routes(app, {'timing_aspect': timing_aspect})
    logger.info("✅ Registered Database Configuration routes")

    # Initialize Repository and Module Management routes
    register_repository_module_routes(
        app=app,
        logger=logger,
        active_user_repositories=active_user_repositories,
        active_user_modules=active_user_modules,
        get_chromadb_client=get_chromadb_client
    )
    logger.info("✅ Registered Repository and Module Management routes")

    # Initialize Guarantee Vetting routes (JSON-based rules)
    from app.backend.Guarantee_Vetting import register_guarantee_vetting_routes
    register_guarantee_vetting_routes(app, timing_aspect, logger)
    logger.info("✅ Registered Guarantee Vetting routes")

    # Initialize Vetting Rule Engine routes (MongoDB-based rules via VettingRuleEngine)
    from app.backend.Guarantee_Vetting import register_vetting_rule_engine_routes
    register_vetting_rule_engine_routes(app, vetting_engine, users_collection, timing_aspect, logger)
    logger.info("✅ Registered Vetting Rule Engine routes")

    # Initialize Guarantee Submission routes (form submission and AI vetting check)
    from app.backend.Guarantee_Vetting import register_guarantee_submission_routes
    register_guarantee_submission_routes(
        app=app,
        timing_aspect=timing_aspect,
        login_required=login_required,
        logger=logger,
        db=db,
        get_conversation_context=get_conversation_context,
        handle_guarantee_vetting_check=handle_guarantee_vetting_check
    )
    logger.info("✅ Registered Guarantee Submission routes")

    # Initialize Auth and User Management routes
    register_auth_routes(app)
    logger.info("✅ Registered Auth and User Management routes")

    # Initialize Discrepancy Rules routes (Compliance_And_Discrepancies module)
    from app.backend.Smart_Document_Capture.Compliance_And_Discrepancies import register_discrepancy_routes
    register_discrepancy_routes(app, timing_aspect, logger)
    logger.info("✅ Registered Discrepancy Rules routes")

    # Define LLM compliance background worker (needed by Compliance routes)
    def run_llm_compliance_in_background(request_id, documents, lc_context, relevant_rules):
        """Background worker for LLM compliance check"""
        try:
            # Update status to processing using helper function
            set_llm_compliance_status(request_id, 'processing', 
                                       progress='Classifying rules using GPT-4o...')
            
            logger.info(f"🚀 Background LLM compliance check started for request: {request_id}")
            
            # Initialize LLM compliance engine (imported from Compliance_And_Discrepancies module)
            engine = LLMComplianceEngine()
            
            # Update progress - use the imported tracker directly for updates
            llm_compliance_tracker[request_id]['progress'] = 'Performing LC comparison...'
            
            # Run comprehensive compliance check
            result = engine.run_comprehensive_compliance_check(
                documents=documents,
                lc_context=lc_context,
                all_rules=relevant_rules
            )
            
            # Update with results using helper function
            set_llm_compliance_status(request_id, 'completed', 
                                       progress='Compliance check complete',
                                       results=result)
            
            logger.info(f"✅ Background LLM compliance check completed for request: {request_id}")
            
        except Exception as e:
            logger.error(f"❌ Background LLM compliance check failed for {request_id}: {str(e)}", exc_info=True)
            set_llm_compliance_status(request_id, 'failed', 
                                       progress='Error occurred',
                                       error=str(e))

    # Initialize Compliance routes (Compliance_And_Discrepancies module)
    from app.backend.Smart_Document_Capture.Compliance_And_Discrepancies import register_compliance_routes
    from app.utils.compliance_validator import DocumentComplianceValidator
    compliance_validator = DocumentComplianceValidator()
    register_compliance_routes(app, timing_aspect, logger, compliance_validator, 
                               extract_text_from_file, parse_swift_message_text, db,
                               set_llm_compliance_status, run_llm_compliance_in_background)
    logger.info("✅ Registered 8 Compliance routes")

    # Initialize Admin Configuration routes (Data Categories, Entities, Prompt Config, Document Config)
    from app.backend.Admin_Configuraton import register_admin_config_routes
    register_admin_config_routes(app, timing_aspect, load_prompt_config, login_required, db, users_collection, ALLOWED_EMAILS)
    logger.info("✅ Registered Admin Configuration routes")

    # Initialize User Manuals and Knowledge Sources routes
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
    logger.info("✅ Registered User Manuals and Knowledge Sources routes")

    # Initialize Conversation & Sessions routes (Chatbot history, session management, beneficiaries, templates)
    from app.backend.Conversation_And_Sessions import register_conversation_routes, register_chat_routes
    register_conversation_routes(
        app=app,
        logger=logger,
        db=db,
        conversation_manager=conversation_manager
    )
    register_chat_routes(
        app=app,
        timing_aspect=timing_aspect,
        logger=logger,
        db=db,
        get_conversation_context=get_conversation_context,
        retrieve_conversation_history=retrieve_conversation_history,
        clear_conversation_history=clear_conversation_history,
        handle_ai_check=handle_ai_check,
        active_user_repositories=active_user_repositories,
        active_user_modules=active_user_modules
    )
    logger.info("✅ Registered Conversation & Sessions routes")

    # Initialize Page Routes (HTML page rendering for all UI pages)
    from app.backend.Page_Routes import register_page_routes
    register_page_routes(
        app=app,
        timing_aspect=timing_aspect,
        logger=logger
    )
    logger.info("✅ Registered Page Routes")

    # Initialize Analytics routes (dashboards, compliance analytics, module performance, export)
    from app.backend.Analytics import register_analytics_routes
    register_analytics_routes(
        app=app,
        timing_aspect=timing_aspect,
        logger=logger,
        db=db
    )
    logger.info("✅ Registered Analytics routes")

    # ==========================================================================
    # ADMIN CONFIGURATION ROUTES (Data Categories, Entities, Prompt Config)
    # Using modular Admin_Configuraton module
    # ==========================================================================
    
    # Initialize managers
    data_category_manager = DataCategoryManager()
    entity_manager = EntityManager()
    prompt_config_manager = PromptConfigManager()

    # ==========================================================================
    # DOCUMENT ENTITY MAINTENANCE ROUTES (Admin Protected)
    # ==========================================================================
    
    # Helper function to get base directory for JSON files
    def _get_base_dir():
        """Get the base directory for JSON configuration files"""
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Helper function to generate next ID
    def _next_id(loader_func):
        """Generate next sequential ID"""
        try:
            data = loader_func()
            mappings = data.get('mappings', [])
            if not mappings:
                return '1'
            existing_ids = [int(m['id']) for m in mappings if m.get('id', '').isdigit()]
            return str(max(existing_ids) + 1) if existing_ids else '1'
        except Exception:
            return '1'
    
    def _load_document_entity_mappings():
        """Load all document entity mappings from common JSON file"""
        try:
            base_dir = _get_base_dir()
            filepath = os.path.join(base_dir, 'document_entity_maintenance.json')
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {'mappings': []}
        except Exception as e:
            logger.error(f"Error loading document entity mappings: {e}")
            return {'mappings': []}
    
    def _load_document_entity_mapping_by_document(document_id):
        """Load document entity mappings for specific document"""
        try:
            base_dir = _get_base_dir()
            filepath = os.path.join(base_dir, 'document_entity_maintenance.json')
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Filter mappings for this document
                    doc_mappings = [m for m in data.get('mappings', []) if m.get('documentId') == document_id]
                    return {'mappings': doc_mappings}
            return {'mappings': []}
        except Exception as e:
            logger.error(f"Error loading document entity mappings for {document_id}: {e}")
            return {'mappings': []}
    
    def _save_document_entity_mappings(data):
        """Save all document entity mappings to common JSON file"""
        try:
            base_dir = _get_base_dir()
            filepath = os.path.join(base_dir, 'document_entity_maintenance.json')
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Error saving document entity mappings: {e}")
            return False
    
    def _save_document_entity_mapping_by_document(document_id, doc_data):
        """Save document entity mappings for specific document to common JSON"""
        try:
            # Load all mappings
            all_data = _load_document_entity_mappings()
            
            # Remove old mappings for this document
            all_data['mappings'] = [m for m in all_data.get('mappings', []) if m.get('documentId') != document_id]
            
            # Add new mappings for this document
            all_data['mappings'].extend(doc_data.get('mappings', []))
            
            # Save back
            return _save_document_entity_mappings(all_data)
        except Exception as e:
            logger.error(f"Error saving document entity mappings for {document_id}: {e}")
            return False

    # ==========================================================================
    # DOCUMENT ENTITY MAINTENANCE ROUTES - Handled by admin_config_routes.py
    # ==========================================================================
    # These routes are registered via register_admin_config_routes()
    # Do not duplicate them here

    # ==========================================================================
    # END DOCUMENT ENTITY MAINTENANCE ROUTES
    # ==========================================================================

    @app.route('/api/enhanced/analyze_documents', methods=['POST'])
    @log_request
    def enhanced_analyze_documents():
        """
        Enhanced document analysis with parallel processing, cross-validation, and anomaly detection
        """
        try:
            if not ENHANCED_FEATURES_AVAILABLE:
                return jsonify({
                    'error': 'Enhanced features not available',
                    'message': 'Please install required dependencies'
                }), 500

            rt_logger = get_realtime_logger()
            request_id = request.headers.get('X-Request-ID', str(uuid.uuid4())[:8])

            log_info(f"Starting enhanced document analysis", {'request_id': request_id})

            # Extract request data
            data = request.get_json()
            lc_data = data.get('lc_data', {})
            swift_data = data.get('swift_data', {})
            additional_documents = data.get('additional_documents', {})
            analysis_options = data.get('options', {
                'parallel_processing': True,
                'cross_validation': True,
                'anomaly_detection': True,
                'detailed_logging': True
            })

            step_id = rt_logger.log_processing_step(request_id, "Document Analysis Setup")

            # Submit parallel analysis tasks
            if analysis_options.get('parallel_processing', True):
                task_ids = analyze_documents_parallel(lc_data, swift_data, additional_documents)
                rt_logger.log_processing_step_end(step_id, 'COMPLETED', {
                    'task_ids': task_ids,
                    'parallel_tasks': len(task_ids)
                })

                # Wait for results with timeout
                max_wait_time = 30  # 30 seconds timeout
                start_time = time.time()

                while time.time() - start_time < max_wait_time:
                    results = get_analysis_results(list(task_ids.values()))

                    if len(results) == len(task_ids):
                        break

                    time.sleep(0.5)

                # Collect final results
                final_results = get_analysis_results(list(task_ids.values()))
                completion_rate = len(final_results) / len(task_ids) * 100

                response = {
                    'status': 'success',
                    'request_id': request_id,
                    'analysis_type': 'enhanced_parallel',
                    'completion_rate': completion_rate,
                    'task_ids': task_ids,
                    'results': final_results,
                    'processing_summary': {
                        'total_tasks': len(task_ids),
                        'completed_tasks': len(final_results),
                        'processing_time': time.time() - start_time,
                        'parallel_processing': True
                    }
                }

            else:
                # Sequential processing fallback
                step_id = rt_logger.log_processing_step(request_id, "Sequential Analysis")

                # Regular inconsistency analysis
                inconsistency_results = analyze_field_inconsistencies(lc_data, swift_data)

                rt_logger.log_processing_step_end(step_id, 'COMPLETED', {
                    'inconsistencies_found': len(inconsistency_results)
                })

                response = {
                    'status': 'success',
                    'request_id': request_id,
                    'analysis_type': 'enhanced_sequential',
                    'results': {
                        'inconsistency': {
                            'status': 'success',
                            'result': inconsistency_results
                        }
                    },
                    'processing_summary': {
                        'total_tasks': 1,
                        'completed_tasks': 1,
                        'parallel_processing': False
                    }
                }

            log_info(f"Enhanced document analysis completed", {
                'request_id': request_id,
                'completion_rate': response.get('completion_rate', 100),
                'total_inconsistencies': len(response.get('results', {}).get('inconsistency', {}).get('result', []))
            })

            return jsonify(response)

        except Exception as e:
            rt_logger = get_realtime_logger()
            rt_logger.log_error(e, 'enhanced_analyze_documents', request_id)

            return jsonify({
                'status': 'error',
                'message': str(e),
                'request_id': request_id
            }), 500

    @app.route('/api/enhanced/document_preview', methods=['POST'])
    @log_request
    def enhanced_document_preview():
        """
        Enhanced document preview with accurate page navigation and field highlighting
        """
        try:
            if not ENHANCED_FEATURES_AVAILABLE:
                return jsonify({
                    'error': 'Enhanced features not available'
                }), 500

            rt_logger = get_realtime_logger()
            request_id = request.headers.get('X-Request-ID', str(uuid.uuid4())[:8])

            data = request.get_json()
            document_path = data.get('document_path')
            highlighted_fields = data.get('highlighted_fields', [])
            page_number = data.get('page_number')

            if not document_path:
                return jsonify({'error': 'document_path is required'}), 400

            step_id = rt_logger.log_processing_step(request_id, "Document Preview Generation")

            # Generate enhanced preview
            preview_data = preview_document_with_fields(document_path, highlighted_fields)

            # Filter by page if specified
            if page_number:
                preview_pages = [p for p in preview_data.get('pages', [])
                                 if p['page_number'] == page_number]
                preview_data['pages'] = preview_pages
                preview_data['filtered_by_page'] = page_number

            rt_logger.log_processing_step_end(step_id, 'COMPLETED', {
                'document_path': document_path,
                'total_pages': preview_data.get('total_pages', 0),
                'highlighted_fields_count': len(highlighted_fields),
                'extracted_fields_count': len(preview_data.get('extracted_fields', {}))
            })

            response = {
                'status': 'success',
                'request_id': request_id,
                'preview_data': preview_data,
                'metadata': {
                    'document_type': preview_data.get('document_type', 'unknown'),
                    'total_pages': preview_data.get('total_pages', 0),
                    'highlighted_fields': highlighted_fields,
                    'processing_timestamp': datetime.now().isoformat()
                }
            }

            return jsonify(response)

        except Exception as e:
            rt_logger = get_realtime_logger()
            rt_logger.log_error(e, 'enhanced_document_preview', request_id)

            return jsonify({
                'status': 'error',
                'message': str(e),
                'request_id': request_id
            }), 500

    @app.route('/api/enhanced/realtime_logs', methods=['GET'])
    def get_realtime_logs():
        """
        Get real-time backend logs and activity
        """
        try:
            if not ENHANCED_FEATURES_AVAILABLE:
                return jsonify({
                    'error': 'Enhanced features not available'
                }), 500

            rt_logger = get_realtime_logger()

            # Get query parameters
            limit = int(request.args.get('limit', 50))
            category = request.args.get('category')
            level = request.args.get('level')

            # Get logs and statistics
            logs = rt_logger.get_recent_logs(limit, category, level)
            active_requests = rt_logger.get_active_requests()
            statistics = rt_logger.get_statistics()

            response = {
                'status': 'success',
                'timestamp': datetime.now().isoformat(),
                'logs': logs,
                'active_requests': active_requests,
                'statistics': statistics,
                'filters': {
                    'limit': limit,
                    'category': category,
                    'level': level
                }
            }

            return jsonify(response)

        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500

    # NOTE: /api/enhanced/processing_status/<request_id> route is now registered via register_status_routes()
    # See: app/backend/WebSocket_And_ProgressUpdater/status_routes.py

    @app.route('/api/enhanced/cross_validation', methods=['POST'])
    @log_request
    def cross_document_validation():
        """
        Cross-document validation with SWIFT message against trade documents
        """
        try:
            if not ENHANCED_FEATURES_AVAILABLE:
                return jsonify({
                    'error': 'Enhanced features not available'
                }), 500

            rt_logger = get_realtime_logger()
            request_id = request.headers.get('X-Request-ID', str(uuid.uuid4())[:8])

            data = request.get_json()
            documents = data.get('documents', {})
            swift_data = data.get('swift_data', {})

            step_id = rt_logger.log_processing_step(request_id, "Cross-Document Validation")

            # Submit cross-validation task
            parallel_analyzer = get_parallel_analyzer()
            task_id = parallel_analyzer.submit_cross_validation(documents, swift_data)

            # Wait for result
            max_wait = 15  # 15 seconds
            start_time = time.time()

            while time.time() - start_time < max_wait:
                result = parallel_analyzer.get_result(task_id)
                if result:
                    break
                time.sleep(0.5)

            if result and result.status == 'success':
                rt_logger.log_processing_step_end(step_id, 'COMPLETED', {
                    'validation_results': len(result.result.get('cross_document_validation', [])),
                    'processing_time': result.processing_time
                })

                response = {
                    'status': 'success',
                    'request_id': request_id,
                    'task_id': task_id,
                    'validation_results': result.result,
                    'processing_time': result.processing_time
                }
            else:
                rt_logger.log_processing_step_end(step_id, 'FAILED',
                                                  error_message='Validation timeout or failed')

                response = {
                    'status': 'timeout',
                    'request_id': request_id,
                    'task_id': task_id,
                    'message': 'Cross-validation did not complete within timeout period'
                }

            return jsonify(response)

        except Exception as e:
            rt_logger = get_realtime_logger()
            rt_logger.log_error(e, 'cross_document_validation', request_id)

            return jsonify({
                'status': 'error',
                'message': str(e),
                'request_id': request_id
            }), 500

    @app.route("/metrics", methods=["GET"])
    @login_required
    @timing_aspect
    def get_metrics():
        """Retrieve performance metrics for endpoints."""
        try:
            endpoint = request.args.get("endpoint")
            start_date = request.args.get("start_date")  # Format: YYYY-MM-DD
            end_date = request.args.get("end_date")  # Format: YYYY-MM-DD

            query = {}
            if endpoint:
                query["endpoint"] = endpoint
            if start_date and end_date:
                query["timestamp"] = {
                    "$gte": datetime.strptime(start_date, "%Y-%m-%d"),
                    "$lte": datetime.strptime(end_date, "%Y-%m-%d")
                }

            metrics = list(metrics_collection.find(query, {"_id": 0}).sort("timestamp", DESCENDING))
            return jsonify({"metrics": metrics}), 200
        except Exception as e:
            logger.error(f"Error retrieving metrics: {e}")
            return jsonify({"error": str(e)}), 500

    def extract_json_from_gpt_response(text):
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            json_str = match.group(0)
            return json.loads(json_str)
        return json.loads(text)

    def handle_table_or_report_request(intent, user_query, user_id, output_format, context) -> tuple[
                                                                                                   Response, int] | Response:
        """
        ✨ ENHANCED: Handles table/report requests using Database Configuration first

        New Flow:
        1. Check if query matches a database configuration recipe
        2. If matched, execute recipe directly
        3. If no match, fall back to RAG-based query generation

        This removes the dependency on repository-database mapper and uses
        the database configuration directly for better performance and accuracy.
        """

        try:
            # Get active module (new) and repository (legacy)
            active_module = active_user_modules.get(user_id)
            active_repository = active_user_repositories.get(user_id)

            logger.info(f"Table request - Module: {active_module}, Repository: {active_repository}")

            # ✨ NEW APPROACH: Try database configuration recipe first
            if active_module:
                try:
                    from app.utils.db_config_query_executor import get_db_config_executor
                    executor = get_db_config_executor()

                    # Try to match query to a recipe
                    recipe_match = executor.match_query_to_recipe(user_query, active_module)

                    if recipe_match and recipe_match.get('score', 0) >= 5:
                        logger.info(
                            f"✅ Recipe match found: {recipe_match['recipe_id']} (score: {recipe_match['score']})")

                        # Extract filters from query
                        from app.utils.process_query_with_db_config import _extract_filters_from_query, \
                            _format_recipe_response

                        recipe = recipe_match['recipe']
                        filters = _extract_filters_from_query(user_query, recipe)

                        # Execute recipe
                        success, result = executor.execute_recipe(recipe_match['recipe_id'], filters)

                        if success and result.get('success'):
                            # Format response
                            formatted_response = _format_recipe_response(result, recipe, user_query)
                            return jsonify(formatted_response), 200
                        else:
                            logger.warning(f"Recipe execution failed: {result}")
                            # Fall through to RAG approach
                    else:
                        logger.info(
                            f"No strong recipe match (score: {recipe_match.get('score', 0) if recipe_match else 0}), using RAG...")

                except Exception as recipe_error:
                    logger.error(f"Error in recipe matching/execution: {recipe_error}")
                    import traceback
                    traceback.print_exc()
                    # Fall through to RAG approach

            # FALLBACK: Use traditional RAG-based approach
            logger.info("Using RAG-based table generation as fallback...")

            # Get database info from module or repository
            active_database = None
            database_collections = []

            if active_module:
                # Get database info from module configuration
                try:
                    from app.utils.db_config_query_executor import get_db_config_executor
                    executor = get_db_config_executor()
                    module = executor.get_module_by_id(active_module)

                    if module:
                        # Get entry tables for this module
                        entry_tables = module.get('entry_tables', [])
                        database_collections = [
                            executor.tables.get(table_id, {}).get('collection', table_id)
                            for table_id in entry_tables
                        ]
                        active_database = executor.config.get('connection', {}).get('database', 'eeai_db')

                        logger.info(
                            f"Module '{module.get('name')}' using database '{active_database}' with collections: {database_collections}")
                except Exception as e:
                    logger.warning(f"Failed to get module database info: {e}")

            elif active_repository:
                # Legacy: Use repository-database mapper
                try:
                    from app.utils.repository_database_mapper import (
                        get_repository_database,
                        get_repository_collections,
                        get_repository_info
                    )

                    active_database = get_repository_database(active_repository)
                    database_collections = get_repository_collections(active_repository)

                    logger.info(
                        f"Repository '{active_repository}' mapped to database '{active_database}' with {len(database_collections)} collections")

                except Exception as mapper_error:
                    logger.warning(f"Failed to map repository to database: {mapper_error}. Using default MongoDB.")
                    active_database = None

            # Run the RAG-based table/report logic
            result = generate_rag_table_or_report_request(
                user_query,
                user_id,
                output_format="table",
                active_repository=active_repository or active_module,
                active_database=active_database,
                database_collections=database_collections
            )
            from app.utils.daily_logger import log_api
            log_api("RAG_GENERATION", "completed", 200,
                   user_id=user_id, query=user_query, output_format="table",
                   active_repository=active_repository or active_module)

            # Check if result is a tuple (error case)
            if isinstance(result, tuple):
                if result[1] == 204:
                    # No data case
                    return result
                elif result[1] >= 400:
                    # Error case - provide fallback response for repository queries
                    logger.warning(f"RAG request failed with status {result[1]}, using fallback")
                    if active_repository:
                        fallback_response = {
                            "response": f"I understand you want to query {active_repository} data.\n\n" +
                                        "Due to a temporary issue with the AI service, I cannot process complex queries right now.\n\n" +
                                        "However, you can still:\n" +
                                        "• View your repository data directly\n" +
                                        "• Create new transactions\n" +
                                        "• Check specific records by ID\n\n" +
                                        "Please try a simpler query or contact support if you need advanced analysis.",
                            "intent": "Table Request",
                            "output_format": "text"
                        }
                        return jsonify(fallback_response), 200
                    return result

            # If result is a Response object, try to get JSON
            if hasattr(result, 'get_json'):
                response_data = result.get_json()
                if response_data:
                    # Don't save here - frontend will save via /api/conversation/message endpoint
                    pass

            return result

        except Exception as e:
            logger.error(f"Error in handle_table_or_report_request: {e}")
            # Provide a helpful fallback for table requests
            if active_repository:
                return jsonify({
                    "response": f"I encountered an issue querying {active_repository}.\n\nPlease try:\n• Simplifying your query\n• Specifying exact fields or dates\n• Using keywords like 'show', 'list', or 'find'",
                    "intent": "error"
                }), 200
            return jsonify({"response": "An error occurred while processing your request.", "intent": "error"}), 500

    def handle_visualization_request(intent, response, user_query, user_id):
        try:
            context = get_conversation_context(user_id)

            # Generate visualization directly from user query without data dependency
            visualization_result = generate_visualization_with_inference(
                user_query=user_query,
                context=context,
                user_id=user_id
            )

            if isinstance(visualization_result, dict) and "chart_path" in visualization_result:
                chart_path = visualization_result["chart_path"]
                return send_file(
                    chart_path,
                    mimetype="image/png",
                    as_attachment=False
                ), 200

            logger.error("Visualization generation failed.")
            return jsonify({"response": "Failed to generate visualization.", "intent": "error"}), 500

        except Exception as e:
            logger.error(f"Error during visualization generation: {e}")
            return jsonify({"response": "An error occurred during visualization generation.", "intent": "error"}), 500

    def handle_export_report_request(intent, response, user_query, user_id, context):
        """Handle export report requests with conversation context checking and RAG fallback."""
        try:
            logger.info(f"Processing export report request for user {user_id}")

            # Extract requested format from query or response
            export_format = response.get("output_format", "excel").lower()
            if export_format not in ["excel", "csv", "pdf", "json"]:
                export_format = "excel"

            # Step 1: Check conversation context for existing data
            conversation_data = extract_exportable_data_from_context(context)

            if conversation_data and conversation_data.get("data"):
                logger.info("Found sufficient data in conversation context")
                # Generate export file
                export_result = generate_export_file(conversation_data, export_format, user_query, user_id)

                if export_result and export_result.get("success"):
                    return send_file(
                        export_result["file_path"],
                        mimetype=export_result["mimetype"],
                        as_attachment=True,
                        download_name=export_result["filename"]
                    )
                else:
                    return jsonify({
                        "response": "Failed to generate export file.",
                        "intent": "error"
                    }), 500

            # Step 2: If insufficient data, use RAG to retrieve additional information
            logger.info("Insufficient data in conversation, checking RAG")
            rag_data = retrieve_export_data_from_rag(user_query, user_id)

            if rag_data and rag_data.get("data"):
                logger.info("Found data through RAG retrieval")
                # Combine conversation data with RAG data
                combined_data = combine_conversation_and_rag_data(conversation_data, rag_data)

                export_result = generate_export_file(combined_data, export_format, user_query, user_id)

                if export_result and export_result.get("success"):
                    return send_file(
                        export_result["file_path"],
                        mimetype=export_result["mimetype"],
                        as_attachment=True,
                        download_name=export_result["filename"]
                    )
                else:
                    return jsonify({
                        "response": "Failed to generate export file with RAG data.",
                        "intent": "error"
                    }), 500

            # Step 3: If still insufficient, ask specific follow-up questions
            logger.info("Insufficient data for export, requesting more information")
            follow_up_questions = generate_export_follow_up_questions(user_query, conversation_data, rag_data)

            return jsonify({
                "response": "I need more information to generate the export report. Please provide the following details:",
                "intent": "Export Report Request",
                "follow_up_questions": follow_up_questions,
                "data_status": "insufficient"
            })

        except Exception as e:
            logger.error(f"Error handling export report request: {e}")
            return jsonify({
                "response": "An error occurred while processing the export report request.",
                "intent": "error"
            }), 500

    def convert_to_dataframe(data):
        if isinstance(data, dict) and "table" in data:
            return pd.DataFrame(data["table"])
        elif isinstance(data, pd.DataFrame):
            return data
        else:
            logger.error("Invalid data format.")
            raise ValueError("Data is not in a valid format for visualization.")

    def extract_data_from_context(context):
        data = None
        sql_query = None
        for entry in reversed(context):
            if 'role' in entry and entry["role"] == "assistant" and isinstance(entry.get("message"), dict):
                if "data_reference" in entry["message"]:
                    data_reference = entry["message"]["data_reference"]
                    logger.info(f"Found data reference: {data_reference}")
                    if os.path.exists(data_reference):
                        try:
                            with open(data_reference, "r") as file:
                                raw_data = file.read()
                                data = eval(raw_data.replace("nan", "None"))
                        except Exception as e:
                            logger.error(f"Error reading data reference file: {e}")
                elif "data" in entry["message"]:
                    data = entry["message"]["data"]
                if "sql_query" in entry["message"]:
                    sql_query = entry["message"]["sql_query"]
        return data, sql_query

    def group_ocr_data_by_page(text_data):
        pages = defaultdict(list)
        for entry in text_data:
            page = entry.get("bounding_page", 1)
            pages[page].append(entry)
        return [pages[k] for k in sorted(pages)]

    def count_tokens(text, model_name=deployment_name):
        enc = tiktoken.encoding_for_model(model_name)
        return len(enc.encode(text))

    def analyze_page_with_gpt(page_number, page_ocr_data, userQuery, annotations, productName, functionName):
        page_text = " ".join([entry["text"] for entry in page_ocr_data])
        token_count = count_tokens(page_text)
        if token_count > 16000:
            logging.warning(f"Page {page_number} exceeds token limit. Truncating.")
            page_text = page_text[:20000]

        result = analyze_document_with_gpt(
            extracted_text=page_text,
            ocr_data=page_ocr_data,
            userQuery=userQuery,
            annotations=annotations,
            productName=productName,
            functionName=functionName
        )
        result["page_number"] = page_number
        return result

    def handle_file_upload(uploaded_files, intent, userQuery=None, annotations=None, productName=None,
                           functionName=None):
        try:
            results = []
            logger.info(f"SEARCH: handle_file_upload called with product: {productName}, function: {functionName}")

            if not isinstance(uploaded_files, list):
                uploaded_files = [uploaded_files]

            for uploaded_file in uploaded_files:
                file_type = getattr(uploaded_file, "content_type", "unknown")
                file_name = getattr(uploaded_file, "filename", "unnamed")
                if file_type not in ALLOWED_FILE_TYPES:
                    results.append({
                        "file_name": file_name,
                        "error": f"Unsupported file type: {file_type}"
                    })
                    continue

                with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                    temp_file_path = temp_file.name
                    uploaded_file.save(temp_file_path)

                try:
                    extracted_text_data = extract_text_from_file(temp_file_path, file_type)
                    text_data = extracted_text_data.get("text_data", [])
                    if not text_data:
                        logging.warning(f"No text data extracted from {file_name}. Skipping.")
                        results.append({
                            "file_name": file_name,
                            "error": "No text data extracted"
                        })
                        continue

                    original_text = " ".join([entry["text"] for entry in text_data])
                    pages_ocr_data = group_ocr_data_by_page(text_data)

                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        page_analysis_results = list(executor.map(
                            lambda args: analyze_page_with_gpt(*args),
                            [(page_number, page_data, userQuery, annotations, productName, functionName)
                             for page_number, page_data in enumerate(pages_ocr_data, start=1)]
                        ))

                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        compliance_futures = []
                        for i, page_result in enumerate(page_analysis_results):
                            page_extracted_fields = page_result.get("extracted_fields", {})
                            page_original_text = page_result.get(
                                "original_text",
                                " ".join([entry["text"] for entry in pages_ocr_data[i]])
                            )
                            future_unified = executor.submit(
                                analyze_unified_compliance_fast,
                                page_extracted_fields,
                                document_type
                            )
                            compliance_futures.append(future_unified)

                        for i, future_unified in enumerate(compliance_futures):
                            page_analysis_results[i]["unified_compliance"] = future_unified.result()

                    def classify_page_task(page_tuple):
                        page_number, page_data = page_tuple
                        page_text = " ".join([entry["text"] for entry in page_data])
                        classification = classify_document_gpt(page_text)
                        classification["page_number"] = page_number
                        return classification

                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        page_classifications = list(executor.map(
                            classify_page_task,
                            [(page_number, page_data) for page_number, page_data in enumerate(pages_ocr_data, start=1)]
                        ))

                    # PDF/Image preview
                    annotated_image_base64 = None
                    if file_type.startswith("image/"):
                        annotated_image_base64 = encode_image_to_base64(temp_file_path)
                    elif file_type == "application/pdf":
                        pdf_result = convert_pdf_to_images_opencv(temp_file_path)
                        if pdf_result["type"] == "error":
                            logging.error(f"Failed to process {file_name}: {pdf_result['error']}")
                        else:
                            annotated_image_base64 = pdf_result["data"]

                    results.append({
                        "file_name": file_name,
                        "page_classifications": page_classifications,
                        "analysis_result": {
                            "per_page": page_analysis_results
                        },
                        "annotated_image": annotated_image_base64,
                        "annotated_filetype": file_type
                    })

                    logging.info("SEARCH Final analysis result for file %s:\n%s", file_name, json.dumps({
                        "file_name": file_name,
                        "page_classifications": page_classifications,
                        "analysis_result": {
                            "per_page": page_analysis_results
                        },
                        "annotated_image": "<base64-truncated>",
                        "annotated_filetype": file_type
                    }, indent=2))

                except Exception as e:
                    logging.error(f"Error processing file {file_name}: {e}")
                    results.append({
                        "file_name": file_name,
                        "error": str(e)
                    })
                finally:
                    if os.path.exists(temp_file_path):
                        os.remove(temp_file_path)

            return jsonify({"response": results, "intent": intent})

        except Exception as e:
            logging.error(f"Error processing file upload: {e}")
            return jsonify({"response": "An error occurred while processing the files.", "intent": "error"}), 500

    def convert_pdf_to_images_opencv(pdf_path):
        images_base64 = []
        try:
            if not os.path.exists(pdf_path):
                logging.error(f"File not found: {pdf_path}")
                return {"error": "File not found", "type": "error"}

            doc = fitz.Document(pdf_path)  # Use fitz.Document, not fitz.open
            for page_num in range(len(doc)):
                pix = doc[page_num].get_pixmap()
                img_np = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.h, pix.w, pix.n))
                if pix.n == 4:
                    img_np = cv2.cvtColor(img_np, cv2.COLOR_RGBA2RGB)
                elif pix.n == 3:
                    img_np = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
                img_pil = Image.fromarray(img_np)
                buffered = BytesIO()
                img_pil.save(buffered, format="JPEG")
                img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
                images_base64.append(img_base64)
            doc.close()
            if not images_base64:
                return {"error": "No images extracted", "type": "error"}
            return {"type": "image", "data": images_base64}
        except Exception as e:
            logging.error(f"Failed to process PDF: {str(e)}")
            return {"error": f"Failed to process PDF: {str(e)}", "type": "error"}

    def encode_image_to_base64(image_path):
        """Convert an image (JPEG/PNG) to base64 encoding."""
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode("utf-8")
        except Exception as e:
            logging.error(f"Error encoding image: {e}")
            return None

    def generate_scf_xml(file_index, analysis_result):
        try:
            root = Element("SCF79")
            extracted_fields = analysis_result
            msg_info = SubElement(root, "MsgInfo")
            SubElement(msg_info, "SenderCode").text = ""
            SubElement(msg_info, "ReceiverCode").text = ""
            SubElement(msg_info, "CreatedBy").text = "C007503MCM1"
            SubElement(msg_info, "SequenceNr").text = ""
            SubElement(msg_info, "MsgType").text = "SCF79"
            SubElement(msg_info, "FileIndex").text = file_index
            SubElement(msg_info, "SubFileIndex").text = ""
            SubElement(msg_info, "DateTime").text = datetime.now().isoformat()
            SubElement(msg_info, "Status").text = ""
            SubElement(msg_info, "Error").text = ""

            customer = SubElement(root, "Customer")
            SubElement(customer, "CustomerCompanyRegNr").text = "C007503"
            SubElement(customer, "CustomerNr").text = "C007503"
            SubElement(customer, "CustomerName").text = "Anchor Buyer"
            SubElement(customer, "UnitCode").text = "CSBANK"
            SubElement(customer, "BusiType").text = "PF"

            inv_details = SubElement(root, "InvCreditNoteDetails")
            SubElement(inv_details, "CounterpartyCompanyRegNr").text = "C007497"
            SubElement(inv_details, "CounterpartyName").text = "C007497 NM"
            SubElement(inv_details, "DocType").text = "1"
            SubElement(inv_details, "SBRRef").text = "PFCSBANK240208494SBR"
            SubElement(inv_details, "DocNr").text = extracted_fields.get("invoice_number", "N/A")
            SubElement(inv_details, "DocDate").text = extracted_fields.get("invoice_date", "N/A")
            SubElement(inv_details, "InvoiceCurrency").text = extracted_fields.get("currency", "N/A")
            SubElement(inv_details, "DocAmt").text = str(extracted_fields.get("total_amount", "0.00"))
            SubElement(inv_details, "DocValDate").text = extracted_fields.get("invoice_date", "N/A")
            SubElement(inv_details, "DocDueDate").text = extracted_fields.get("due_date", "N/A")
            SubElement(inv_details, "PORefNr").text = extracted_fields.get("po_number", "N/A")

            control_tot = SubElement(root, "ControlTot")
            SubElement(control_tot, "TotNrInvoices").text = "1"

            xml_string = tostring(root, encoding="utf-8", method="xml").decode("utf-8")
            logger.info(f"Generated SCF XML: {xml_string}")
            return xml_string
        except Exception as e:
            logger.error(f"Error generating SCF XML for file_index {file_index}: {e}", exc_info=True)
            return None

    def generate_md5_code(file_path):
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest().upper()
        except Exception as e:
            raise ValueError(f"Error generating MD5 hash: {e}")

    def handle_zip_file_upload(uploaded_file, intent, userQuery=None, annotations=None, documentType=None):
        try:
            file_type = uploaded_file.content_type
            if file_type not in ["application/zip", "application/x-zip-compressed"]:
                return jsonify({
                    "response": f"Unsupported file type: {file_type}. Only zip files are allowed.",
                    "intent": intent
                }), 400

            with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as temp_zip_file:
                temp_zip_file_path = temp_zip_file.name
                uploaded_file.save(temp_zip_file_path)

            extracted_results = []
            try:
                with zipfile.ZipFile(temp_zip_file_path, 'r') as zip_ref:
                    extract_dir = tempfile.mkdtemp()
                    zip_ref.extractall(extract_dir)

                    for root, _, files in os.walk(extract_dir):
                        for file_name in files:
                            file_path = os.path.join(root, file_name)
                            file_type = mimetypes.guess_type(file_path)[0]
                            if file_type:
                                try:
                                    extracted_text = extract_text_from_file(file_path, file_type)
                                    analysis_result = analyze_file(extracted_text.get("text", ""), file_type, userQuery)
                                    if isinstance(analysis_result, dict):
                                        if analysis_result.get("document_type") == "invoice":
                                            confidence_score = analysis_result.get("confidence_score", 0)
                                            if confidence_score >= 0.9:
                                                records = analysis_result.get("extracted_fields", [])
                                                file_index = str(uuid.uuid4()).replace('-', '').upper()
                                                scf_xml = generate_scf_xml(file_index, records)
                                                md5_code = generate_md5_code(file_path)
                                                insert_trx_file_upload(file_index, file_name, "CSBANK", md5_code)
                                                with open(file_path, "rb") as f:
                                                    file_content = f.read()
                                                insert_trx_file_detail(file_index, file_name, scf_xml,
                                                                       len(file_content))
                                                insert_trx_sub_files(file_index, file_name, "Invoice")
                                                insert_faef_em_inv(file_index, analysis_result.get("main_ref"))
                                        extracted_results.append({
                                            "file_name": file_name,
                                            "extracted_text": extracted_text.get("text"),
                                            "ocr_confidence": extracted_text.get("ocr_confidence"),
                                            "analysis_result": analysis_result
                                        })
                                    else:
                                        extracted_results.append({
                                            "file_name": file_name,
                                            "error": "Analysis result is not in the expected format."
                                        })
                                except Exception as e:
                                    logger.error(f"Error processing file {file_name}: {e}")
                                    extracted_results.append({
                                        "file_name": file_name,
                                        "error": f"Failed to process the file: {str(e)}"
                                    })
                            else:
                                extracted_results.append({
                                    "file_name": file_name,
                                    "error": "Unsupported or unknown file type."
                                })
            finally:
                if os.path.exists(temp_zip_file_path):
                    os.remove(temp_zip_file_path)
                if os.path.exists(extract_dir):
                    shutil.rmtree(extract_dir)
            return jsonify({"response": extracted_results, "intent": intent})
        except zipfile.BadZipFile:
            logger.error("Uploaded file is not a valid zip archive.")
            return jsonify({
                "response": "The uploaded file is not a valid zip archive.",
                "intent": "error"
            }), 400
        except Exception as e:
            logger.error(f"Error processing zip file upload: {e}")
            return jsonify({
                "response": "An error occurred while processing the zip file upload.",
                "intent": "error",
                "details": str(e)
            }), 500

    def analyze_file(extracted_text, file_type, userQuery):
        try:
            analysis_result = analyze_document_with_gpt(extracted_text, userQuery=userQuery, annotations="")
            return analysis_result
        except Exception as e:
            logger.error(f"Error analyzing file: {e}")
            return {"error": "An error occurred during file analysis."}

    def handle_proactive_alert(user_query, user_id, schema=None):
        try:
            context = get_conversation_context(user_id)
            llm_response = trigger_proactive_alerts(user_query=user_query, context=context, schema=schema)
            # Don't save intermediate steps - frontend will save final response
            sql_query = generate_sql_query(llm_response, user_id, schema)
            if not sql_query:
                return jsonify(
                    {"response": "Failed to generate SQL query for the alert condition.", "intent": "error"}), 500
            # Don't save intermediate steps - frontend will save final response
            results, insights = execute_sql_and_format(sql_query, output_format="table", use_llm=True,
                                                       user_query=user_query)
            if results:
                # Don't save here - frontend will save via /api/conversation/message endpoint
                return jsonify({
                    "response": results,
                    "insights": insights,
                    "intent": "proactive alert request"
                })
            # Don't save here - frontend will save via /api/conversation/message endpoint
            return jsonify({
                "response": "No data found for the specified alert condition.",
                "intent": "proactive alert request"
            }), 204
        except Exception as e:
            logger.error(f"Error generating proactive alerts: {e}", exc_info=True)
            # Don't save here - frontend will save via /api/conversation/message endpoint
            return jsonify(
                {"response": "An unexpected error occurred while processing proactive alerts.", "intent": "error"}), 500

    def handle_user_manual(intent, user_query, user_id):
        save_directory = "app/utils/output"
        csv_path = os.path.join(save_directory, "pdf_text_with_embeddings.csv")
        if not os.path.exists(csv_path):
            return jsonify({"response": "Error: Preprocessed CSV file not found.", "intent": intent}), 500
        df = pd.read_csv(csv_path)
        faiss_index_path = os.path.join(save_directory, "faiss_index.idx")
        index = load_faiss_index(faiss_index_path)
        if not index:
            return jsonify({"response": "Error loading FAISS index.", "intent": intent}), 500
        context = get_conversation_context(user_id)
        # Don't save here - frontend will save via /api/conversation/message endpoint
        answer = generate_response(user_query, df, index, user_id, context)
        # Don't save here - frontend will save via /api/conversation/message endpoint
        return jsonify({"response": answer, "intent": intent, "conversation_history": context})

    def load_custom_rules(path=CUSTOM_RULES_PATH):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load custom rules: {e}")
            return []

    def save_custom_rules(rules, path=CUSTOM_RULES_PATH):
        if not isinstance(rules, list):
            raise ValueError("Attempted to save non-list of rules!")
        with open(path, "w") as f:
            json.dump(rules, f, indent=2)

    def handle_custom_rule_intent(user_query, conversation_history=None):
        current_rules = load_custom_rules()
        prompt = f"""
        You are an expert assistant for trade finance custom compliance rules.
        Current custom rules as JSON:
        {json.dumps(current_rules, indent=2)}
        User Query:
        \"{user_query}\"
        Conversation History:
        {conversation_history if conversation_history else ""}
        Instructions:
        - Analyze what the user wants to do: view, add, update, or delete a rule.
        - If you have all needed info:
            - For 'view': set 'Result' as a valid HTML snippet (table, card, or div/list).
            - For 'add', 'update', or 'delete':
                - 'Result' is an HTML snippet for UI display.
                - Include 'UpdatedRules' as a JSON array of rule objects (id and description only).
        - If no rules or no match for view/delete/update, return appropriate HTML in 'Result' and current rules in 'UpdatedRules'.
        - If info is missing, return follow-up questions in 'FollowUpQuestions'.
        - Return ONLY this JSON structure:
        {{
          "Action": "<view|add|update|delete|unknown>",
          "FollowUpQuestions": ["..."],
          "Result": <null or HTML string>,
          "UpdatedRules": <null or array of rule objects>
        }}
        """
        try:
            # Placeholder for actual GPT call
            response = {"Action": "unknown", "FollowUpQuestions": [], "Result": None, "UpdatedRules": current_rules}
            reply = json.loads(json.dumps(response))
            if reply.get("Action") in ("add", "update", "delete") and reply.get("UpdatedRules"):
                save_custom_rules(reply["UpdatedRules"])
            return reply
        except Exception as e:
            logger.error(f"Error in custom rule LLM handler: {e}")
            return {"error": str(e)}

    def validate_azure_cv_config():
        """
        Validate Azure Computer Vision configuration at startup.
        Returns True if valid, False otherwise.
        Uses COMPUTER_VISION_ENDPOINT and COMPUTER_VISION_KEY from app_config imports.
        """
        try:
            if not COMPUTER_VISION_ENDPOINT or not COMPUTER_VISION_KEY:
                logger.error("ERROR: Azure Computer Vision credentials not configured in environment variables")
                return False

            # Test if endpoint is reachable (basic validation)
            if not COMPUTER_VISION_ENDPOINT.startswith(('http://', 'https://')):
                logger.error("ERROR: Invalid Azure Computer Vision endpoint format")
                return False

            logger.info("SUCCESS:Azure Computer Vision configuration validated")
            return True

        except Exception as e:
            logger.error(f"ERROR: Azure Computer Vision configuration error: {e}")
            return False

    def validate_uploaded_file(uploaded_file, file_type):
        """
        Validate uploaded file for size, type, and basic integrity.
        Returns error message if invalid, None if valid.
        """
        try:
            # File type validation
            if file_type not in ALLOWED_FILE_TYPES:
                return f"Unsupported file type: {file_type}. Allowed types: {', '.join(ALLOWED_FILE_TYPES)}"

            # File size validation (50MB limit)
            MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB in bytes
            uploaded_file.seek(0, 2)  # Seek to end
            file_size = uploaded_file.tell()
            uploaded_file.seek(0)  # Reset to beginning

            if file_size > MAX_FILE_SIZE:
                return f"File too large: {file_size / (1024*1024):.1f}MB. Maximum allowed: 50MB"

            if file_size == 0:
                return "File is empty"

            # Basic file content validation
            if not uploaded_file.filename:
                return "Filename is required"

            # Check for valid file extension
            allowed_extensions = {'.pdf', '.jpg', '.jpeg', '.png'}
            file_ext = Path(uploaded_file.filename).suffix.lower()
            if file_ext not in allowed_extensions:
                return f"Invalid file extension: {file_ext}. Allowed: {', '.join(allowed_extensions)}"

            logger.debug(f"SUCCESS:File validation passed: {uploaded_file.filename} ({file_size / 1024:.1f} KB)")
            return None  # No error

        except Exception as e:
            logger.error(f"ERROR: File validation error: {e}")
            return f"File validation failed: {str(e)}"

    # Initialize document classifier at module level
    document_classifier = DocumentClassifier()

    def process_uploaded_files(uploaded_files, intent, userQuery=None, annotations=None, productName=None,
                               functionName=None, documentType=None, progress_tracker=None):
        try:
            results = []
            logger.info(f"SEARCH: process_uploaded_files called with product: {productName}, function: {functionName}, documentType: {documentType}")

            if not isinstance(uploaded_files, list):
                uploaded_files = [uploaded_files]

            # Initialize progress tracking
            if progress_tracker:
                logger.info(f"ANALYTICS: Starting progress tracking for {len(uploaded_files)} file(s)")
                progress_tracker.start_upload(f"{len(uploaded_files)} file(s)")

            for idx, uploaded_file in enumerate(uploaded_files):
                file_type = getattr(uploaded_file, "content_type", "unknown")
                file_name = getattr(uploaded_file, "filename", "unnamed")

                logger.info(f"DEBUG: Processing file {idx+1}/{len(uploaded_files)}: {file_name}")
                logger.info(f"DEBUG: progress_tracker is {'available' if progress_tracker else 'None'}")

                # Update upload progress for multiple files
                if progress_tracker and len(uploaded_files) > 1:
                    upload_progress = int(((idx + 1) / len(uploaded_files)) * 10)  # Upload is 0-10%
                    progress_tracker.set_progress(upload_progress, f"Uploading {file_name} ({idx+1}/{len(uploaded_files)})")

                if file_type not in ALLOWED_FILE_TYPES:
                    results.append({
                        "file_name": file_name,
                        "error": f"Unsupported file type: {file_type}"
                    })
                    continue

                with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                    temp_file_path = temp_file.name
                    uploaded_file.save(temp_file_path)

                # Mark upload complete for this file IMMEDIATELY after saving
                if progress_tracker:
                    logger.info(f"UPLOAD: Upload complete for file: {file_name}")
                    logger.info(f"DEBUG: Calling progress_tracker.upload_complete() now...")
                    progress_tracker.upload_complete()
                    logger.info(f"SUCCESS:DEBUG: upload_complete() called successfully")

                    # Start quality analysis stage (fast version)
                    logger.info(f"SEARCH: Starting quality analysis for: {file_name}")
                    logger.info(f"DEBUG: Calling progress_tracker.start_quality_analysis() now...")
                    progress_tracker.start_quality_analysis()
                    logger.info(f"SUCCESS:DEBUG: start_quality_analysis() called successfully")

                # Perform quality analysis (ultra-fast version to avoid hanging)
                if progress_tracker:
                    try:
                        # Ultra-quick quality check - just mark as good
                        file_size = os.path.getsize(temp_file_path)
                        quality_verdict = "processed"
                        quality_score = 0.8

                        logger.info(f"SUCCESS:Instant quality check: {quality_verdict} (size: {file_size} bytes)")

                    except Exception as quality_error:
                        logger.warning(f"Quality check error: {quality_error}")
                        quality_verdict = "processed"
                        quality_score = 0.7

                    # Mark quality analysis complete immediately
                    logger.info(f"SUCCESS:Quality analysis complete for: {file_name}")
                    progress_tracker.quality_complete(quality_verdict, quality_score)

                    # Start OCR stage
                    logger.info(f" Starting OCR extraction for: {file_name}")
                    progress_tracker.start_ocr()

                try:
                    logger.info(f"📋 OCR REQUEST: File={file_name}, Type={file_type}, Path={temp_file_path}")
                    logger.info(f"🔧 OCR Config: Quality={quality_verdict if 'quality_verdict' in locals() else 'N/A'}, FileSize={os.path.getsize(temp_file_path)} bytes")
                    
                    # Use OCRExtractionService instead of file_utils
                    ocr_service = OCRExtractionService()
                    ocr_result = ocr_service.extract(
                        temp_file_path=temp_file_path,
                        file_type=file_type,
                        quality_verdict=quality_verdict if 'quality_verdict' in locals() else None,
                        progress_tracker=progress_tracker
                    )
                    
                    if ocr_result.success:
                        extracted_text_data = {
                            "text_data": ocr_result.text_data,
                            "processing_time": ocr_result.processing_time,
                            "overall_confidence": ocr_result.overall_confidence
                        }
                    else:
                        extracted_text_data = {"error": ocr_result.error, "text_data": []}
                    
                    logger.info(f"📊 OCR RESPONSE: Success={ocr_result.success}, Lines={len(ocr_result.text_data)}, Confidence={ocr_result.overall_confidence:.3f}")
                    logger.info(f"⏱️ OCR Processing Time: {ocr_result.processing_time:.2f}s")
                    
                    text_data = ocr_result.text_data

                    # Mark OCR complete
                    if progress_tracker:
                        progress_tracker.ocr_complete(extracted_entries=len(text_data))

                    if not text_data:
                        logging.warning(f"No text data extracted from {file_name}. Skipping.")
                        results.append({
                            "file_name": file_name,
                            "error": "No text data extracted"
                        })
                        continue

                    original_text = " ".join([entry["text"] for entry in text_data])
                    pages_ocr_data = organize_ocr_data_by_page(text_data)

                    # Start classification
                    if progress_tracker:
                        progress_tracker.start_classification()

                    # Process all pages concurrently with a single LLM call per page
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        page_analysis_results = list(executor.map(
                            lambda args: process_page_with_llm_analysis(*args),
                            [(page_number, page_data, userQuery, annotations, productName, functionName, documentType)
                             for page_number, page_data in enumerate(pages_ocr_data, start=1)]
                        ))

                    # Classification complete - estimate document type from first page
                    if progress_tracker and page_analysis_results:
                        first_page = page_analysis_results[0] if page_analysis_results else {}
                        doc_type = first_page.get("document_type", "unknown")
                        confidence = first_page.get("classification_confidence", 0)
                        progress_tracker.classification_complete(doc_type, int(confidence))

                        # Start field extraction
                        total_fields = sum(len(page.get("extracted_fields", {})) for page in page_analysis_results)
                        progress_tracker.start_field_extraction(field_count=total_fields)

                    # Aggregate compliance results
                    combined_unified_result = {}

                    for page_result in page_analysis_results:
                        # Aggregate unified compliance results
                        if "unified_compliance" in page_result:
                            combined_unified_result.update(page_result["unified_compliance"])

                    # PDF/Image preview
                    annotated_image_base64 = None
                    if file_type.startswith("image/"):
                        annotated_image_base64 = encode_image_to_base64(temp_file_path)
                    elif file_type == "application/pdf":
                        pdf_result = convert_pdf_to_images_opencv(temp_file_path)
                        if pdf_result["type"] == "error":
                            logging.error(f"Failed to process {file_name}: {pdf_result['error']}")
                        else:
                            annotated_image_base64 = pdf_result["data"]

                    results.append({
                        "file_name": file_name,
                        "page_classifications": [
                            {"page_number": pr["page_number"], **pr["classification"]}
                            for pr in page_analysis_results
                        ],
                        "compliance": {
                            "unified": combined_unified_result
                        },
                        "analysis_result": {
                            "per_page": page_analysis_results
                        },
                        "annotated_image": annotated_image_base64,
                        "annotated_filetype": file_type
                    })

                    # Mark field extraction complete and start compliance check
                    if progress_tracker:
                        total_extracted = sum(len(page.get("extracted_fields", {})) for page in page_analysis_results)
                        progress_tracker.field_extraction_complete(extracted_count=total_extracted)

                        # Start compliance checking
                        progress_tracker.start_compliance_check()

                        # Count compliance issues
                        compliance_issues = 0
                        if combined_unified_result:
                            compliance_issues += len([k for k, v in combined_unified_result.items() if not v.get("compliant", True)])

                        # Mark compliance complete
                        progress_tracker.compliance_complete(compliance_issues)

                        # Finalize processing
                        progress_tracker.finalize()

                    logging.info("SEARCH Final analysis result for file %s:\n%s", file_name, json.dumps({
                        "file_name": file_name,
                        "page_classifications": results[-1]["page_classifications"],
                        "analysis_result": {
                            "per_page": page_analysis_results
                        },
                        "annotated_image": "<base64-truncated>",
                        "annotated_filetype": file_type
                    }, indent=2))

                except Exception as e:
                    logging.error(f"Error processing file {file_name}: {e}")
                    results.append({
                        "file_name": file_name,
                        "error": str(e)
                    })
                finally:
                    if os.path.exists(temp_file_path):
                        os.remove(temp_file_path)

            return jsonify({"response": results, "intent": intent})

        except Exception as e:
            logging.error(f"Error processing file upload: {e}")
            return jsonify({"response": "An error occurred while processing the files.", "intent": "error"}), 500

    def extract_ocr_text_from_file(file_path, file_type):
        # Placeholder for Azure OCR logic (unchanged for brevity)
        try:
            if file_type not in ALLOWED_FILE_TYPES:
                return {"error": f"Unsupported file type: {file_type}", "text_data": []}
            # Implement Azure OCR logic here
            # Return format: {"text_data": [{"text": str, "bounding_box": list, "bounding_page": int, "confidence": float}, ...]}
            return {"text_data": []}
        except Exception as e:
            logging.error(f"Unexpected error in OCR extraction: {e}")
            return {"error": str(e), "text_data": []}

    def organize_ocr_data_by_page(text_data):
        """Organize OCR data by page number with enhanced debugging"""
        logger.info(f"ANALYTICS: === ORGANIZING OCR DATA BY PAGE ===")
        logger.info(f"Input: {len(text_data)} OCR entries")

        # Debug: Check page distribution in raw data
        page_counts = {}
        missing_page_count = 0

        for i, entry in enumerate(text_data):
            page = entry.get("bounding_page", None)
            if page is None:
                missing_page_count += 1
                logger.warning(f"Entry {i}: Missing bounding_page field - {entry.get('text', '')[:30]}...")
                page = 1  # Default fallback

            page_counts[page] = page_counts.get(page, 0) + 1

        logger.info(f"ANALYTICS: Page distribution in raw OCR data:")
        for page in sorted(page_counts.keys()):
            logger.info(f"   Page {page}: {page_counts[page]} entries")

        if missing_page_count > 0:
            logger.warning(f"WARNINGS: Found {missing_page_count} entries without page information")

        # Organize by page
        pages = defaultdict(list)
        for entry in text_data:
            page = entry.get("bounding_page", 1)
            pages[page].append(entry)

        organized_pages = [pages[k] for k in sorted(pages)]
        logger.info(f"SUCCESS:Organized into {len(organized_pages)} pages")

        # Debug: Log sample from each page
        for page_idx, page_data in enumerate(organized_pages):
            actual_page = page_idx + 1
            logger.info(f"   Page {actual_page}: {len(page_data)} entries")
            if page_data:
                sample_text = page_data[0].get('text', '')[:30]
                logger.info(f"      Sample: '{sample_text}...'")

        return organized_pages

    def calculate_text_token_count(text, model_name="gpt-3.5-turbo"):
        enc = tiktoken.encoding_for_model(model_name)
        return len(enc.encode(text))

    def format_ocr_data_for_llm_prompt(ocr_data):
        formatted = ""
        for i, entry in enumerate(ocr_data):
            text = entry.get("text", "").replace("\n", " ")
            box = entry.get("bounding_box", [])
            page = entry.get("bounding_page", 0)
            formatted += f"{i + 1}. Text: \"{text}\"\n   Box: {box}, Page: {page}\n"
        return formatted

    def parse_json_from_llm_response(text):
        try:
            json_str = re.search(r'\{[\s\S]+\}', text).group()
            return json.loads(json_str)
        except Exception as e:
            logging.error(f"Could not parse JSON from LLM response: {e}")
            return None

    def identify_document_type(extracted_text):
        # Use the new document classifier for better accuracy
        classification = document_classifier.classify_document(extracted_text)
        doc_type = classification.get("document_type", "unknown").lower().replace(" ", "_")
        # Map to expected format
        if "guarantee" in doc_type:
            return "bank_guarantee"
        elif "letter" in doc_type and "credit" in doc_type:
            return "letter_of_credit"
        return doc_type

    def load_document_analysis_prompt(document_type, extracted_text, product_name=None, function_name=None):
        # Use document classifier to get fields dynamically
        field_list, field_definitions = document_classifier.get_document_fields(
            document_type, product_name, function_name
        )

        # If we have function-specific fields, use those; otherwise use document fields
        if field_definitions:
            # Format fields with descriptions
            formatted_fields = "\n".join([
                f"- {field}: {desc}" for field, desc in field_definitions.items()
            ])
        else:
            # Fallback to simple field list
            formatted_fields = "\n".join([f"- {field}" for field in field_list])
        return f"""
    Analyze the following OCR-extracted text and extract key details for a {document_type} document.

    OCR Text:
    {extracted_text}

    Extract the following details:
    {formatted_fields}

    ### Extraction Rules:
    - For letter_of_credit: Do not return "null" for missing fields; omit them or leave value empty.
    - For bank_guarantee: Return "null" for missing field values.
    - Format all dates as "YYYY-MM-DD".
    - Return numeric values for amounts/currency (no symbols).
    - Assign a confidence score (0–100%) for each field based on OCR clarity and keyword proximity.
    - Include bounding_box and bounding_page if available.

    ### Expected JSON Output:
    {{
      "document_type": "{document_type}",
      "extracted_fields": {{
        "<Field Name>": {{
          "value": "<extracted_value>",
          "desc": "<field description>",
          "confidence": <score>,
          "bounding_box": [<x1>, <y1>, <x2>, <y2>],
          "bounding_page": <page_number>
        }}
      }},
      "confidence_score": <overall_score>
    }}
    """

    def aggregate_extracted_fields(extraction_results: List[Dict], strategy: str = "union", confidence_threshold: int = 70) -> Dict:
        """
        Aggregate multiple extraction results into a single consolidated result.

        Args:
            extraction_results: List of extraction result dictionaries from parallel calls
            strategy: Aggregation strategy - "union", "intersection", or "majority"
            confidence_threshold: Minimum confidence to include a field

        Returns:
            Aggregated extraction result with merged fields
        """
        logger.info(f"🔀 Aggregating {len(extraction_results)} extraction results using '{strategy}' strategy")

        if not extraction_results:
            return {}

        # Initialize aggregated result with first successful result as base
        aggregated = None
        for result in extraction_results:
            if result and 'extracted_fields' in result:
                aggregated = {
                    'page_number': result.get('page_number', 1),
                    'classification': result.get('classification', {}),
                    'extracted_fields': {},
                    'confidence_score': 0,
                    'mandatory_fields_found': 0,
                    'total_mandatory_fields': result.get('total_mandatory_fields', 0),
                    'extraction_completeness': 0,
                    'aggregation_metadata': {
                        'total_attempts': len(extraction_results),
                        'successful_attempts': sum(1 for r in extraction_results if r and 'extracted_fields' in r),
                        'strategy': strategy,
                        'confidence_threshold': confidence_threshold
                    }
                }
                break

        if not aggregated:
            logger.error("❌ No valid extraction results to aggregate")
            return {}

        # Collect all fields from all results
        field_occurrences = {}  # {field_name: [{'value': val, 'confidence': conf, 'bounding_box': box}, ...]}

        for result in extraction_results:
            if not result or 'extracted_fields' not in result:
                continue

            for field_name, field_data in result['extracted_fields'].items():
                if not isinstance(field_data, dict):
                    continue

                confidence = field_data.get('confidence', 0)
                value = field_data.get('value', '')

                # Skip if below confidence threshold or empty value
                if confidence < confidence_threshold or not value:
                    continue

                if field_name not in field_occurrences:
                    field_occurrences[field_name] = []

                field_occurrences[field_name].append({
                    'value': value,
                    'confidence': confidence,
                    'bounding_box': field_data.get('bounding_box', [0, 0, 0, 0]),
                    'bounding_page': field_data.get('bounding_page', 1)
                })

        logger.info(f"📊 Found {len(field_occurrences)} unique fields across all attempts")

        # Apply aggregation strategy
        if strategy == "union":
            # Union: Include all fields found in any attempt (take highest confidence occurrence)
            for field_name, occurrences in field_occurrences.items():
                # Sort by confidence and take the highest
                best_occurrence = max(occurrences, key=lambda x: x['confidence'])
                aggregated['extracted_fields'][field_name] = best_occurrence
                logger.debug(f"   ✓ {field_name}: {len(occurrences)} occurrences, using highest confidence")

        elif strategy == "intersection":
            # Intersection: Only include fields found in ALL attempts
            required_count = aggregated['aggregation_metadata']['successful_attempts']
            for field_name, occurrences in field_occurrences.items():
                if len(occurrences) >= required_count:
                    # Take the occurrence with highest confidence
                    best_occurrence = max(occurrences, key=lambda x: x['confidence'])
                    aggregated['extracted_fields'][field_name] = best_occurrence
                    logger.debug(f"   ✓ {field_name}: Found in all {required_count} attempts")
                else:
                    logger.debug(f"   ✗ {field_name}: Only in {len(occurrences)}/{required_count} attempts (skipped)")

        elif strategy == "majority":
            # Majority: Include fields found in 50%+ of attempts
            required_count = aggregated['aggregation_metadata']['successful_attempts'] / 2
            for field_name, occurrences in field_occurrences.items():
                if len(occurrences) >= required_count:
                    # For majority voting, we could:
                    # Option 1: Take highest confidence
                    # Option 2: Take most common value
                    # Let's use Option 1 for now
                    best_occurrence = max(occurrences, key=lambda x: x['confidence'])
                    aggregated['extracted_fields'][field_name] = best_occurrence
                    logger.debug(f"   ✓ {field_name}: Found in {len(occurrences)} attempts (majority)")
                else:
                    logger.debug(f"   ✗ {field_name}: Only in {len(occurrences)} attempts (below majority)")

        # Calculate aggregate metrics
        total_fields = len(aggregated['extracted_fields'])
        aggregated['confidence_score'] = (
            sum(f['confidence'] for f in aggregated['extracted_fields'].values()) / total_fields
            if total_fields > 0 else 0
        )

        # Count mandatory fields (assuming fields with high confidence or specific naming pattern)
        aggregated['mandatory_fields_found'] = sum(
            1 for f in aggregated['extracted_fields'].values()
            if f.get('confidence', 0) >= 85
        )

        if aggregated['total_mandatory_fields'] > 0:
            aggregated['extraction_completeness'] = int(
                (aggregated['mandatory_fields_found'] / aggregated['total_mandatory_fields']) * 100
            )

        logger.info(f"✅ Aggregation complete: {total_fields} fields, avg confidence: {aggregated['confidence_score']:.1f}")
        return aggregated

    # NOTE: filter_extracted_fields_by_type, extract_entities_in_chunks, extract_entities_parallel, 
    # and process_page_with_llm_analysis are now imported from Entity_Extraction module

    def train_user_manual(uploaded_file, user_id: str, user_query: str) -> Dict[str, Any]:
        """Train a user manual by extracting text from a file and storing embeddings in ChromaDB (admin only)."""
        temp_file_path = None
        try:
            # Check if user is admin
            user = UserRepository.get_user_by_id(user_id) if user_id else None
            if not user:
                return {"success": False, "message": "User not found"}

            # Check if user is allowed
            if user.get("email", "").lower() not in [e.lower() for e in ALLOWED_EMAILS]:
                return {"success": False, "message": "Access denied"}

            file_type = uploaded_file.content_type
            file_name = uploaded_file.filename
            if file_type not in ALLOWED_FILE_TYPES:
                return {"success": False, "message": f"Unsupported file type: {file_type}"}

            # Save file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_name.split('.')[-1]}") as temp_file:
                temp_file_path = temp_file.name
                uploaded_file.save(temp_file_path)

            # Extract text based on file type
            text = None

            if file_type == "application/pdf":
                # First try standard PDF text extraction
                text = read_pdf(temp_file_path)

                # If standard extraction fails (returns None), use OCR
                if text is None:
                    logger.info(f"Standard PDF extraction failed for {file_name}, falling back to OCR")
                    try:
                        extracted_data = extract_text_from_file(temp_file_path, "application/pdf")
                        if extracted_data.get("text_data"):
                            text = " ".join([entry["text"] for entry in extracted_data.get("text_data", [])])
                            logger.info(f"OCR extraction successful for {file_name}, extracted {len(text)} characters")
                        else:
                            logger.warning(f"OCR extraction returned no text for {file_name}")
                    except Exception as ocr_error:
                        logger.error(f"OCR extraction failed for {file_name}: {ocr_error}")
                        text = ""
            else:
                # For non-PDF files, use OCR directly
                extracted_data = extract_text_from_file(temp_file_path, file_type)
                text = " ".join([entry["text"] for entry in extracted_data.get("text_data", [])])

            if not text or not text.strip():
                return {"success": False, "message": "No text data extracted from the file. The file may be an image-based PDF or encrypted."}

            # Split text into chunks
            text_chunks = split_text(text, chunk_size=500)
            if not text_chunks:
                return {"success": False, "message": "No valid text chunks extracted"}

            # Store manuals as global (accessible to all users)
            # Generate embeddings and store in ChromaDB
            chunk_ids = [f"global_{file_name}_{i}" for i in range(len(text_chunks))]
            metadata = [{
                "file_name": file_name,
                "chunk_index": i,
                "is_global": True,  # Mark as globally accessible
                "uploaded_by": user_id,  # Track which admin uploaded it
                "uploaded_by_admin": True  # Mark that it was uploaded by admin
            } for i in range(len(text_chunks))]

            # Generate embeddings for all chunks
            embeddings = []
            for chunk in text_chunks:
                embedding = get_embedding_azureRAG(chunk)
                embeddings.append(embedding)

            if not user_manual_collection:
                return {"success": False, "message": "ChromaDB is not enabled for this customer."}

            user_manual_collection.add(
                documents=text_chunks,
                metadatas=metadata,
                embeddings=embeddings,
                ids=chunk_ids
            )

            logger.info(f"Trained global user manual by admin {user_id}, file: {file_name}")
            # Don't save here - frontend will save via /api/conversation/message endpoint
            return {"success": True, "message": f"User manual '{file_name}' trained successfully."}

        except Exception as e:
            logger.error(f"Error training user manual: {e}")
            return {"success": False, "message": f"Error training user manual: {str(e)}"}
        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except OSError as e:
                    logger.warning(f"Failed to delete temporary file {temp_file_path}: {e}")

    def query_trained_manual(user_query: str, user_id: str, context: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Query using HYBRID approach: Knowledge Corpus (approved Q&A) + User Manuals (ChromaDB).

        This provides intelligent query routing:
        1. First checks Knowledge Corpus for approved Q&A pairs (highest priority)
        2. Then queries User Manuals for PDF content chunks
        3. Combines results with confidence scoring
        4. Returns beautifully formatted HTML response
        """
        try:
            from app.utils.integrated_knowledge_query import query_hybrid_knowledge

            # Get active repository from session (if available)
            active_repository = session.get('active_repository', 'trade_finance_repo')

            logger.info(f"Hybrid query for user {user_id}, repository: {active_repository}, query: {user_query}")

            # Perform hybrid query across Knowledge Corpus AND User Manuals
            result = query_hybrid_knowledge(user_query, user_id, active_repository)

            if not result.get("success"):
                logger.warning(f"Hybrid query returned no results for user {user_id}")
                return {
                    "success": False,
                    "message": "No relevant information found in Knowledge Base or User Manuals.",
                    "response": result.get("response", ""),
                    "html": result.get("html", "")
                }

            # Extract source information
            source_files = []

            # Add Knowledge Corpus sources
            kc_sources = result.get("knowledge_corpus", {}).get("sources", [])
            for source in kc_sources:
                if source.get("document_name"):
                    source_files.append(f"KB: {source['document_name']}")

            # Add User Manual sources
            manual_files = result.get("user_manuals", {}).get("files", [])
            source_files.extend([f"Manual: {f}" for f in manual_files])

            logger.info(
                f"Hybrid query success for user {user_id}: KC matches={len(kc_sources)}, Manual matches={len(manual_files)}")

            return {
                "success": True,
                "response": result.get("response", ""),
                "html": result.get("html", ""),
                "intent": result.get("intent", "Hybrid Knowledge Query"),
                "output_format": "html",  # Always HTML for formatted responses
                "source_files": source_files,
                "sources": {
                    "knowledge_corpus": {
                        "count": len(kc_sources),
                        "matches": result.get("knowledge_corpus", {}).get("matches", [])
                    },
                    "user_manuals": {
                        "count": len(manual_files),
                        "files": manual_files
                    }
                },
                "confidence": result.get("confidence", 0.0),
                "query_type": result.get("query_type", "hybrid")
            }

        except Exception as e:
            logger.error(f"Error in hybrid query for user {user_id}: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "message": f"Error querying knowledge sources: {str(e)}",
                "response": "An error occurred while searching the knowledge base.",
                "html": f'<div class="error-message"><i class="fas fa-exclamation-triangle"></i> Error: {str(e)}</div>'
            }

    def retrieve_relevant_chunks_user_manual(query: str, user_id: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve relevant chunks from user manual collection."""
        try:
            if not user_manual_collection:
                logger.warning("ChromaDB user_manual_collection not available")
                return []
            
            # All users can query global manuals
            embedding = get_embedding_azureRAG(query)
            # Search in global manuals
            results = user_manual_collection.query(
                query_embeddings=[embedding],
                n_results=top_k,
                where={"is_global": True}
            )

            return [
                {
                    "file_name": meta.get("file_name", "unknown"),
                    "text": doc,
                    "chunk_index": meta.get("chunk_index", "N/A")
                }
                for doc, meta in zip(results["documents"][0], results["metadatas"][0])
            ]
        except Exception as e:
            logger.error(f"Error retrieving chunks: {str(e)}")
            return []

    # Initialize Query routes (main /query and /query/stream endpoints)
    from app.backend.Conversation_And_Sessions import register_query_routes
    register_query_routes(
        app=app,
        timing_aspect=timing_aspect,
        logger=logger,
        db=db,
        get_conversation_context=get_conversation_context,
        active_user_repositories=active_user_repositories,
        active_user_modules=active_user_modules,
        handle_follow_up_request=handle_follow_up_request,
        train_user_manual=train_user_manual,
        query_trained_manual=query_trained_manual,
        handle_custom_rule_intent=handle_custom_rule_intent,
        handle_api_request=handle_api_request,
        handle_table_or_report_request=handle_table_or_report_request,
        handle_visualization_request=handle_visualization_request,
        handle_export_report_request=handle_export_report_request,
        process_uploaded_files=process_uploaded_files,
        handle_zip_file_upload=handle_zip_file_upload,
        handle_proactive_alert=handle_proactive_alert,
        schema=schema
    )
    logger.info("✅ Registered Query routes (/query, /query/stream)")

    # Document Compliance Checking Routes
    # compliance_validator already initialized earlier
    # run_llm_compliance_in_background already defined before compliance routes registration

    def run_compliance_check_background(file_hash, extracted_fields, document_type):
        """
        Run compliance check in background thread.
        Updates compliance_status_tracker when complete.
        Uses FieldLevelComplianceAnalyzer from Compliance_And_Discrepancies module.
        """
        # Use the imported compliance_status_tracker from WebSocket_And_ProgressUpdater module

        try:
            logger.info(f"🔄 Background compliance check started for hash: {file_hash}")
            logger.info(f"📋 REQUEST: Background Compliance - Hash: {file_hash}, Document Type: {document_type}, Fields Count: {len(extracted_fields)}")
            logger.info(f"🔧 Using: FieldLevelComplianceAnalyzer from Compliance_And_Discrepancies module")

            set_compliance_status(file_hash, 'processing')

            logger.info(f"✅ Added {file_hash} to tracker with status 'processing'")

            # Initialize unified compliance result
            unified_compliance = {}

            # Perform compliance analysis if we have extracted fields
            if extracted_fields:
                # Remove coordinate mapping fields before compliance analysis
                compliance_fields = {k: v for k, v in extracted_fields.items()
                                   if not k.startswith('_coordinate_mapping') and
                                      k not in ['coordinate_mapping_stats']}

                logger.info(f"📋 Compliance fields after filtering: {len(compliance_fields)} (removed coordinate mappings)")

                try:
                    # RULE-BASED UNIFIED COMPLIANCE using modular analyzer
                    logger.info(f"🔄 Clearing previous unified compliance results")
                    clear_module_compliance_result()

                    logger.info(f"📋 Starting FieldLevelComplianceAnalyzer for {document_type}")
                    logger.info(f"🔄 Calling analyzer.analyze() with {len(compliance_fields)} fields")

                    # Use the modular analyzer
                    analyzer = FieldLevelComplianceAnalyzer()
                    unified_compliance = analyzer.analyze(compliance_fields, document_type)

                    logger.info(f"✅ Compliance analysis returned: {len(unified_compliance)} fields")
                    logger.info(f"📊 RESPONSE: Compliance Analysis Complete - {len(unified_compliance)} fields checked")
                    logger.info(f"📊 Sample compliance data: {str(list(unified_compliance.keys())[:5])}")

                except Exception as e:
                    logger.error(f"❌ Background compliance analysis failed: {e}")
                    logger.error(f"❌ Compliance Error Details: Document Type={document_type}, Fields Count={len(compliance_fields)}")
                    import traceback
                    logger.error(traceback.format_exc())
                    unified_compliance = {}
            else:
                logger.warning(f"⚠️ No extracted fields provided for compliance check")

            # Update tracker with completed result
            set_compliance_status(file_hash, 'completed', result=unified_compliance)

            logger.info(f"✅ Updated tracker for {file_hash} - status: completed, fields: {len(unified_compliance)}")
            logger.info(f"✅ FINAL: Background Compliance Complete - Hash={file_hash}, Status=completed, Fields={len(unified_compliance)}")
            logger.info(f"📋 Current tracker keys: {list(compliance_status_tracker.keys())}")

        except Exception as e:
            logger.error(f"❌ Error in background compliance for {file_hash}: {e}")
            logger.error(f"❌ Critical Compliance Failure: Hash={file_hash}, Error={str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            set_compliance_status(file_hash, 'error', error=str(e))
            logger.error(f"❌ Tracker updated with error status for {file_hash}")

    def process_document_with_config(uploaded_file, function_name=None, product_name=None,
                                     document_type=None, progress_tracker=None, config=None):
        """
        Enhanced document processing with config-driven OCR, Classification, and Extraction

        Workflow:
        1. OCR: Extract text from document
        2. Classification: Identify document type using config prompts
        3. Extraction: Extract fields using config-based prompts with field mappings

        Args:
            uploaded_file: File object
            function_name: Business function (e.g., "Register LC")
            product_name: Product name
            document_type: Pre-specified document type (optional)
            progress_tracker: Progress tracking object
            config: YAML prompt configuration

        Returns:
            dict: Processing results with OCR, classification, and extraction data
        """
        import time
        import traceback

        temp_file_path = None  # Track temp file for cleanup
        try:
            file_name = uploaded_file.filename
            file_type = uploaded_file.content_type
            logger.info(f"=== Config-based processing for {file_name} ===")

            # Validate Azure Computer Vision configuration before processing
            if not validate_azure_cv_config():
                return {
                    "file_name": file_name,
                    "error": "Azure Computer Vision not properly configured. Please check credentials and endpoint.",
                    "stage": "Configuration"
                }

            # Validate file before processing
            file_validation_error = validate_uploaded_file(uploaded_file, file_type)
            if file_validation_error:
                return {
                    "file_name": file_name,
                    "error": file_validation_error,
                    "stage": "File Validation"
                }

            start_time = time.time()

            # === STEP 1: Upload File ===
            if progress_tracker:
                progress_tracker.start_upload(file_name)

            # Create temp file with proper extension for quality analysis
            file_extension = os.path.splitext(file_name)[1] if file_name else ''
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
                temp_file_path = temp_file.name
                uploaded_file.save(temp_file_path)

            if progress_tracker:
                progress_tracker.upload_complete()

            # === STEP 2: Quality Analysis ===
            if progress_tracker:
                progress_tracker.start_quality_analysis()

            logger.info(f"SEARCH: STEP 1/4: QUALITY ANALYSIS - Analyzing document quality for {file_name}")
            logger.info(f"📋 REQUEST: Quality Analysis - File: {file_name}, Type: {file_type}, Path: {temp_file_path}")
            quality_start = time.time()

            # Import quality analyzer from Quality_Analysis module
            from app.backend.AI_Document_Processor.Quality_Analysis import DocumentQualityAnalyzer
            quality_analyzer = DocumentQualityAnalyzer()

            logger.info(f"🔄 Calling quality_analyzer.analyze_document_quality_fast()")
            quality_result = quality_analyzer.analyze_document_quality_fast(
                temp_file_path,
                file_name,
                progress_tracker
            )
            quality_time = time.time() - quality_start

            logger.info(f"📊 RESPONSE: Quality Analysis Result - Success: {quality_result.get('success', False)}, Time: {quality_time:.2f}s")
            logger.info(f"📊 Quality Result Details: {quality_result}")

            if quality_result.get("success", False):
                verdict = quality_result.get("verdict", "pre_processing")
                quality_score = quality_result.get("quality_score", 0.5)
                pages_analyzed = quality_result.get("pages_analyzed", 0)
                logger.info(f"SUCCESS:Quality analysis completed in {quality_time:.2f}s - Verdict: {verdict} (score: {quality_score:.3f})")
                logger.info(f"✅ Quality Metrics: Verdict={verdict}, Score={quality_score:.3f}, Pages={pages_analyzed}")

                if progress_tracker:
                    progress_tracker.quality_complete(verdict, quality_score)
            else:
                # Quality analysis failed - proceed with standard processing
                error_msg = quality_result.get('error', 'Unknown error')
                logger.warning(f"WARNINGS: Quality analysis failed: {error_msg}")
                logger.warning(f"⚠️ Quality Analysis Error Details: {quality_result}")
                verdict = "pre_processing"  # Default fallback
                quality_score = 0.5

                if progress_tracker:
                    progress_tracker.quality_complete("fallback", quality_score)

            # === STEP 3: OCR (Extract Text) ===
            if progress_tracker:
                progress_tracker.start_ocr()

            logger.info(f" STEP 2/4: OCR - Extracting text from {file_name} (Quality verdict: {verdict})")
            logger.info(f"📋 REQUEST: OCR Extraction - File: {file_name}, Quality Verdict: {verdict}, Estimated Pages: {quality_result.get('pages_analyzed', 1) if quality_result else 1}")
            ocr_start = time.time()

            # OPTIMIZATION: Estimate page count for timeout calculation
            estimated_pages = quality_result.get("pages_analyzed", 1) if quality_result else 1

            logger.info(f"🔄 Using OCRExtractionService with quality_verdict={verdict}, page_count={estimated_pages}")
            # Use OCRExtractionService instead of file_utils
            ocr_service = OCRExtractionService()
            ocr_result = ocr_service.extract(
                temp_file_path=temp_file_path,
                file_type=file_type,
                quality_verdict=verdict,
                estimated_pages=estimated_pages,
                progress_tracker=progress_tracker
            )
            
            if ocr_result.success:
                extracted_text_data = {
                    "text_data": ocr_result.text_data,
                    "processing_time": ocr_result.processing_time,
                    "overall_confidence": ocr_result.overall_confidence,
                    "optimization_stats": ocr_result.optimization_stats
                }
                text_data = ocr_result.text_data
            else:
                extracted_text_data = {"error": ocr_result.error, "text_data": []}
                text_data = []
            ocr_time = time.time() - ocr_start

            logger.info(f"📊 RESPONSE: OCR Extraction Complete - Extracted {len(text_data)} text entries in {ocr_time:.2f}s")

            # Enhanced logging with optimization stats
            if "optimization_stats" in extracted_text_data:
                stats = extracted_text_data["optimization_stats"]
                logger.info(f"SUCCESS:OPTIMIZED OCR completed in {ocr_time:.2f}s - "
                           f"Extracted {len(text_data)} text entries | "
                           f"FastMode: {stats.get('fast_mode', False)}, "
                           f"PollingInterval: {stats.get('polling_interval', 0):.2f}s, "
                           f"Polls: {stats.get('poll_count', 'N/A')}, "
                           f"Timeout: {stats.get('dynamic_timeout', 'N/A')}s")
                logger.info(f"✅ OCR Optimization Stats: {stats}")
            else:
                logger.info(f"SUCCESS:OCR completed in {ocr_time:.2f}s - Extracted {len(text_data)} text entries")

            if progress_tracker:
                progress_tracker.ocr_complete(extracted_entries=len(text_data))

            # Check for OCR errors
            if "error" in extracted_text_data:
                error_msg = extracted_text_data["error"]
                enhanced_error = f"OCR processing failed: {error_msg}"

                # Add specific troubleshooting context
                if "timeout" in error_msg.lower():
                    enhanced_error += " | Suggestion: Try a smaller file or check Azure OCR service status"
                elif "credentials" in error_msg.lower() or "authentication" in error_msg.lower():
                    enhanced_error += " | Suggestion: Verify Azure Computer Vision credentials and endpoint"
                elif "unsupported" in error_msg.lower():
                    enhanced_error += f" | Suggestion: Use supported formats: {', '.join(ALLOWED_FILE_TYPES)}"
                elif "network" in error_msg.lower() or "connection" in error_msg.lower():
                    enhanced_error += " | Suggestion: Check internet connection and Azure service availability"
                else:
                    enhanced_error += " | Suggestion: Ensure file is not corrupted and retry the operation"

                return {
                    "file_name": file_name,
                    "error": enhanced_error,
                    "stage": "OCR",
                    "original_error": error_msg,
                    "troubleshooting": {
                        "file_type": file_type,
                        "file_name": file_name,
                        "stage_completed": "File validation passed, OCR failed"
                    }
                }

            if not text_data:
                return {
                    "file_name": file_name,
                    "error": "No text content detected in the document",
                    "stage": "OCR",
                    "troubleshooting": {
                        "possible_causes": [
                            "Document contains only images without text",
                            "Document is scanned at very low resolution",
                            "Document contains handwritten text (not supported)",
                            "Document is password protected or corrupted"
                        ],
                        "suggestions": [
                            "Ensure document contains readable printed text",
                            "Try a higher resolution scan (300+ DPI recommended)",
                            "Verify document opens correctly in other applications"
                        ],
                        "file_type": file_type,
                        "ocr_processing_time": f"{ocr_time:.2f}s"
                    }
                }

            # Organize by pages
            pages_ocr_data = organize_ocr_data_by_page(text_data)
            logger.info(f" Organized into {len(pages_ocr_data)} pages")

            # === STEP 4: CLASSIFICATION (Using Document Classifier) ===
            if progress_tracker:
                progress_tracker.start_classification()

            logger.info(f"SEARCH: STEP 3/4: CLASSIFICATION - Identifying document type")
            logger.info(f"📋 REQUEST: Document Classification - File: {file_name}, Pages: {len(pages_ocr_data)}")
            classification_start = time.time()

            # Use existing DocumentClassifier for classification
            page_text = "\n".join([text['text'] for page_data in pages_ocr_data for text in page_data])
            logger.info(f"🔄 Calling document_classifier.classify_document() with {len(page_text)} characters of text")

            classification_result = document_classifier.classify_document(page_text)

            logger.info(f"ANALYTICS: Classification result: {str(classification_result)[:200]}...")
            logger.info(f"📊 RESPONSE: Classification Result - {classification_result}")

            # Extract document type and confidence
            detected_doc_type = classification_result.get('document_type', document_type or 'Unknown')
            # Convert confidence to 0-100 scale if it's 0-1
            raw_confidence = classification_result.get('confidence', 0)
            if raw_confidence <= 1.0:
                confidence = raw_confidence * 100
            else:
                confidence = raw_confidence

            classification_time = time.time() - classification_start
            logger.info(f"SUCCESS:Classification completed in {classification_time:.2f}s - Type: {detected_doc_type}, Confidence: {confidence}")
            logger.info(f"✅ Classification Complete: Type={detected_doc_type}, Confidence={confidence:.2f}%, Time={classification_time:.2f}s")

            if progress_tracker:
                progress_tracker.classification_complete(
                    doc_type=detected_doc_type,
                    confidence=int(confidence)
                )

            # === STEP 4: EXTRACTION (Using Config Prompts + Field Mappings) ===
            logger.info(f"UPLOAD: STEP 4/4: EXTRACTION - Extracting fields using config prompts + field mappings")
            logger.info(f"📋 REQUEST: Entity Extraction - Document Type: {detected_doc_type}")
            extraction_start = time.time()

            if progress_tracker:
                progress_tracker.start_field_extraction(field_count=0)

            # Get config settings for both classification and extraction
            classification_config = config.get('classification', {}) if config else {}
            classification_model = classification_config.get('model', deployment_name)
            classification_temp = classification_config.get('temperature', 0.1)

            extraction_config = config.get('extraction', {}) if config else {}
            extraction_model = extraction_config.get('model', deployment_name)
            extraction_temp = extraction_config.get('temperature', 0.0)
            extraction_max_tokens = extraction_config.get('max_tokens', 16000)  # Increased for 46 fields with full descriptions

            logger.info(f"PARAMETERS: Using extraction config - Model: {extraction_model}, Temp: {extraction_temp}, MaxTokens: {extraction_max_tokens}")

            # Build extraction prompt using DocumentClassifier
            logger.info(f"🔄 Building extraction prompt for document type: {detected_doc_type}")
            extraction_prompt = document_classifier.build_extraction_prompt(
                document_type=detected_doc_type,
                ocr_text=page_text,
                page_number=1
            )

            # === ENHANCEMENT: Add field mapping examples ===
            field_mapping_data = load_document_field_mappings(detected_doc_type)
            field_mapping_example = None
            if field_mapping_data:
                field_mapping_example = field_mapping_data.get('example', '')
                extraction_prompt += f"\n\n{field_mapping_example}"
                logger.info(f" Enhanced extraction prompt with field mapping examples for {detected_doc_type}")

            logger.info(f" Built extraction prompt ({len(extraction_prompt)} chars)")

            # Call LLM for extraction
            logger.info(f"🔄 Calling OpenAI API for entity extraction - Model: {extraction_model}")
            extraction_response = openai.ChatCompletion.create(
                engine=extraction_model,
                messages=[{"role": "user", "content": extraction_prompt}],
                temperature=extraction_temp,
                max_tokens=extraction_max_tokens,
                seed=12345,  # ✅ Reproducibility
                top_p=0.1,  # ✅ NOT 1.0 (reduces randomness)
                frequency_penalty=0,
                presence_penalty=0,
                response_format={"type": "json_object"}
            )

            extraction_result = extraction_response.choices[0].message.content
            logger.info(f"ANALYTICS: Extraction result: {extraction_result[:200]}...")
            logger.info(f"📊 RESPONSE: Entity Extraction - Received {len(extraction_result)} characters from LLM")

            # Parse extraction result
            try:
                extraction_json = json.loads(extraction_result)
                extracted_fields = extraction_json.get('extracted_fields', {})
                logger.info(f"✅ Successfully parsed extraction JSON - {len(extracted_fields)} fields extracted")
            except Exception as parse_error:
                logger.error(f"❌ Failed to parse extraction JSON: {parse_error}")
                extracted_fields = {}

            extraction_time = time.time() - extraction_start
            logger.info(f"SUCCESS:Extraction completed in {extraction_time:.2f}s - Extracted {len(extracted_fields)} fields")
            logger.info(f"✅ Entity Extraction Complete: Fields={len(extracted_fields)}, Time={extraction_time:.2f}s")

            if progress_tracker:
                progress_tracker.field_extraction_complete(extracted_count=len(extracted_fields))

            # === BACKGROUND COMPLIANCE ANALYSIS ===
            # Create file hash for tracking compliance status
            file_content_hash = hashlib.md5(f"{file_name}_{datetime.now().isoformat()}".encode()).hexdigest()

            logger.info(f"🚀 Starting background compliance check for {file_content_hash}")
            logger.info(f"📋 REQUEST: Compliance Analysis - File Hash: {file_content_hash}, Document Type: {detected_doc_type}, Fields: {len(extracted_fields)}")

            # Start compliance check in background thread (non-blocking)
            logger.info(f"🔄 Starting background compliance thread")
            compliance_thread = threading.Thread(
                target=run_compliance_check_background,
                args=(file_content_hash, extracted_fields, detected_doc_type),
                daemon=True
            )
            compliance_thread.start()

            # Set placeholder compliance result (will be updated by background thread)
            unified_compliance = {}
            compliance_analysis_time = 0.0  # Background processing time not counted

            logger.info(f"✅ Compliance check running in background (hash: {file_content_hash})")
            logger.info(f"✅ Background Compliance Thread Started: Hash={file_content_hash}, Thread={compliance_thread.name}")

            # Transform compliance data for UI consumption
            def transform_compliance_for_ui(compliance_data, compliance_type):
                """Transform field-level compliance data to UI-expected format"""
                logger.info(f"MODE: Transforming {compliance_type} compliance data: {type(compliance_data)}")

                if not compliance_data:
                    logger.warning(f"No {compliance_type} compliance data to transform")
                    return None

                # Handle case where compliance_data is a string (JSON error case)
                if isinstance(compliance_data, str):
                    logger.warning(f"{compliance_type} compliance data is string (likely JSON error): {compliance_data[:100]}...")
                    return {
                        "status": "error",
                        "violations": [{"field": "analysis", "description": f"Compliance analysis error: {compliance_data}", "severity": "high"}],
                        "warnings": [],
                        "compliance_percentage": 0,
                        "total_fields_checked": 0,
                        "compliant_fields": 0
                    }

                # Handle case where compliance_data is not a dict
                if not isinstance(compliance_data, dict):
                    logger.warning(f"{compliance_type} compliance data is not dict: {type(compliance_data)}")
                    return {
                        "status": "error",
                        "violations": [{"field": "analysis", "description": f"Invalid compliance data format", "severity": "high"}],
                        "warnings": [],
                        "compliance_percentage": 0,
                        "total_fields_checked": 0,
                        "compliant_fields": 0
                    }

                violations = []
                warnings = []
                compliant_count = 0
                total_count = len(compliance_data)

                logger.info(f"Processing {total_count} {compliance_type} compliance fields")

                for field_name, field_data in compliance_data.items():
                    if isinstance(field_data, dict):
                        is_compliant = field_data.get("compliant", True)
                        severity = field_data.get("severity", "medium")
                        reason = field_data.get("reason", "Compliance check completed")

                        if is_compliant:
                            compliant_count += 1
                        else:
                            issue = {
                                "field": field_name,
                                "description": reason,
                                "severity": severity
                            }

                            if severity == "high":
                                violations.append(issue)
                            else:
                                warnings.append(issue)

                # Determine overall status
                overall_status = "compliant" if len(violations) == 0 else "non-compliant"

                return {
                    "status": overall_status,
                    "violations": violations,
                    "warnings": warnings,
                    "compliance_percentage": round((compliant_count / total_count * 100) if total_count > 0 else 100),
                    "total_fields_checked": total_count,
                    "compliant_fields": compliant_count
                }

            # Calculate overall compliance score from unified compliance
            overall_compliance_score = 85  # Default score
            if unified_compliance:
                compliant_count = 0
                total_count = len(unified_compliance)

                for field_data in unified_compliance.values():
                    if isinstance(field_data, dict) and field_data.get("compliant", True):
                        compliant_count += 1

                if total_count > 0:
                    overall_compliance_score = round((compliant_count / total_count) * 100)
                    logger.info(f"ANALYTICS: Unified compliance: {compliant_count}/{total_count} fields compliant = {overall_compliance_score}%")
                else:
                    logger.info(f"ANALYTICS: No unified compliance data, using default score: {overall_compliance_score}%")
            else:
                logger.info(f"ANALYTICS: No unified compliance result, using default score: {overall_compliance_score}%")

            # === Generate preview images ===
            preview_images = []
            if file_type == "application/pdf":
                pdf_result = convert_pdf_to_images_opencv(temp_file_path)
                if pdf_result["type"] == "image":
                    preview_images = pdf_result["data"]
            else:
                encoded_image = encode_image_to_base64(temp_file_path)
                if encoded_image:
                    preview_images = [encoded_image]

            # Calculate total time
            total_time = time.time() - start_time

            # === Build result using YAML config format ===
            # Separate extracted fields into mandatory, optional, conditional
            mandatory_fields = {}
            optional_fields = {}
            conditional_fields = {}

            # If we have field mappings, categorize the extracted fields
            if field_mapping_data:
                field_mappings = field_mapping_data.get('mappings', [])
                for field_name, field_data in extracted_fields.items():
                    # Find the field type from mappings
                    field_type = None
                    for mapping in field_mappings:
                        if mapping.get('entityName') == field_name:
                            field_type = mapping.get('fieldType', 'optional')
                            break

                    # Categorize based on field type
                    if field_type == 'mandatory':
                        mandatory_fields[field_name] = field_data
                    elif field_type == 'conditional':
                        conditional_fields[field_name] = field_data
                    else:
                        optional_fields[field_name] = field_data
            else:
                # If no field mappings, put all in optional
                optional_fields = extracted_fields

            # Get document code from classification result if available
            document_code = classification_result.get('document_code', '')
            document_id = classification_result.get('document_id', '')
            reasoning = classification_result.get('reasoning', f'Classified as {detected_doc_type} with {confidence}% confidence')

            # Build YAML-compliant result structure
            result = {
                "file_name": file_name,
                "document_type": detected_doc_type,
                "confidence": confidence,
                "complianceScore": overall_compliance_score,
                "classification": {
                    "document_type": detected_doc_type,
                    "document_code": document_code,
                    "document_id": document_id,
                    "confidence": confidence,
                    "reasoning": reasoning
                },
                "extraction": {
                    "mandatory": mandatory_fields,
                    "optional": optional_fields,
                    "conditional": conditional_fields,
                    "schema": {
                        "total_fields": len(extracted_fields),
                        "mandatory_count": len(mandatory_fields),
                        "optional_count": len(optional_fields),
                        "conditional_count": len(conditional_fields)
                    },
                    "document_id": document_id or detected_doc_type
                },
                "compliance": {
                    "unified": unified_compliance   # Unified rule-based compliance
                },
                "preview_images": preview_images,
                "processing_time": {
                    "total": f"{total_time:.1f}",
                    "quality_analysis": f"{quality_time:.1f}",
                    "ocr": f"{ocr_time:.1f}",
                    "classification": f"{classification_time:.1f}",
                    "extraction": f"{extraction_time:.1f}",
                    "compliance_analysis": f"{compliance_analysis_time:.1f}"
                },
                "quality_analysis": {
                    "verdict": verdict,
                    "score": quality_score,
                    "recommendations": quality_result.get("recommendations", []),
                    "detailed_metrics": quality_result.get("page_results", []),
                    "processing_time": quality_result.get("processing_time", 0),
                    "page_count": len(quality_result.get("page_results", [])),
                    "average_metrics": _calculate_average_metrics(quality_result.get("page_results", []))
                },
                "ocr_data": {
                    "total_pages": len(pages_ocr_data),
                    "total_text_entries": len(text_data),
                    "pages": [{"page_number": i+1, "text_entries": len(page_data)} for i, page_data in enumerate(pages_ocr_data)],
                    "formatted_text": page_text[:500] + "..." if len(page_text) > 500 else page_text
                },
                "success": True,
                "enhanced_mode": True,
                "compliance_hash": file_content_hash,  # Hash for tracking background compliance
                "compliance_status": "processing",  # Initial status
                # Legacy timing fields for frontend compatibility
                "qualityTime": f"{quality_time:.1f}",
                "ocrTime": f"{ocr_time:.1f}",
                "classificationTime": f"{classification_time:.1f}",
                "llmTime": f"{extraction_time:.1f}",  # Field extraction time
                "complianceTime": f"{compliance_analysis_time:.3f}",
                "config_used": {
                    "classification_model": classification_model,
                    "classification_temp": classification_temp,
                    "extraction_model": extraction_model,
                    "extraction_temp": extraction_temp
                },
                "field_mapping_enhanced": bool(field_mapping_data)
            }

            logger.info(f"SUCCESS:Config-based processing completed for {file_name} in {total_time:.1f}s")
            return result

        except Exception as e:
            logger.error(f"ERROR: Error in config-based processing: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())

            # Enhanced error context
            error_context = {
                "error_type": type(e).__name__,
                "file_name": getattr(uploaded_file, 'filename', 'Unknown'),
                "file_type": getattr(uploaded_file, 'content_type', 'Unknown'),
                "stage": "Processing",
                "timestamp": datetime.now().isoformat(),
                "suggestions": []
            }

            # Add specific suggestions based on error type
            error_str = str(e).lower()
            if "memory" in error_str or "out of memory" in error_str:
                error_context["suggestions"].append("Try processing a smaller file or reduce image resolution")
            elif "timeout" in error_str:
                error_context["suggestions"].append("File processing took too long - try a smaller file")
            elif "permission" in error_str or "access" in error_str:
                error_context["suggestions"].append("Check file permissions and ensure file is not locked")
            elif "json" in error_str or "parse" in error_str:
                error_context["suggestions"].append("Internal processing error - please try again or contact support")
            else:
                error_context["suggestions"].append("Unexpected error occurred - please try again or contact support")

            return {
                "file_name": getattr(uploaded_file, 'filename', 'Unknown'),
                "error": f"Processing failed: {str(e)}",
                "stage": "Unknown",
                "error_context": error_context,
                "success": False
            }
        finally:
            # Clean up temporary file (non-breaking cleanup)
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                    logger.info(f"Cleaned up temporary file: {temp_file_path}")
                except Exception as cleanup_error:
                    logger.warning(f"WARNINGS: Failed to cleanup temp file {temp_file_path}: {cleanup_error}")

    def extract_fields_parallel(document_groups, document_classifier, extraction_model,
                               extraction_temp, extraction_max_tokens, file_name,
                               all_preview_images, quality_time, ocr_time, classification_time,
                               quality_result, progress_tracker):
        """
        OPTIMIZED: Extract fields from multiple document groups in PARALLEL using threading.
        This reduces total extraction time from (N × time_per_extraction) to max(time_per_extraction).

        For 8 document groups: Sequential = 8×8s = 64s, Parallel = ~8-10s (85% faster!)

        Args:
            document_groups: List of document groups to extract from
            document_classifier: DocumentClassifier instance
            extraction_model: Model name for extraction
            extraction_temp: Temperature for extraction
            extraction_max_tokens: Max tokens for extraction
            file_name: Original filename
            all_preview_images: List of preview images
            quality_time: Quality analysis time
            ocr_time: OCR time
            classification_time: Classification time
            quality_result: Quality analysis result
            progress_tracker: Progress tracking object

        Returns:
            list: Extraction results for all document groups
        """
        import threading
        import queue
        import time

        results_queue = queue.Queue()
        threads = []

        def extract_single_group(idx, group):
            """Extract fields for a single document group (runs in separate thread)"""
            try:
                logger.info(f"🧵 Thread {idx}: Extracting {group['document_type']} using chunk-based approach")
                extraction_start = time.time()

                # Load entity info for chunk-based extraction
                doc_type_normalized = group['document_type'].replace(" ", "_")
                logger.info(f"🔍 Thread {idx}: Getting entity fields for: {doc_type_normalized}")
                entity_info = document_classifier.get_enhanced_entity_fields(doc_type_normalized)
                
                if not entity_info or not any([entity_info.get('mandatory_fields', []), entity_info.get('optional_fields', []), entity_info.get('conditional_fields', [])]):
                    logger.error(f"❌ Thread {idx}: No entity info found for {group['document_type']} (normalized: {doc_type_normalized})")
                    extracted_fields = {}
                else:
                    # Use chunk-based extraction
                    total_entities = len(entity_info['mandatory_fields']) + len(entity_info['optional_fields']) + len(entity_info['conditional_fields'])
                    logger.info(f"📝 Thread {idx}: Starting chunk-based extraction for {total_entities} entities (Mandatory: {len(entity_info['mandatory_fields'])}, Optional: {len(entity_info['optional_fields'])}, Conditional: {len(entity_info['conditional_fields'])})")
                    
                    extraction_results = extract_entities_in_chunks(
                        entity_info=entity_info,
                        ocr_text=group['text'],
                        model=extraction_model,
                        page_number=group['pages'][0] if group['pages'] else 1,
                        document_type=group['document_type']
                    )
                    
                    # Merge results from all chunks
                    merged_results = {"extracted_fields": {}}
                    total_fields_extracted = 0
                    
                    for result in extraction_results:
                        if result and 'extracted_fields' in result:
                            merged_results["extracted_fields"].update(result["extracted_fields"])
                            total_fields_extracted += len(result["extracted_fields"])
                    
                    # Apply field filtering to remove empty optional/conditional fields
                    logger.info(f"🔍 Thread {idx}: Filtering extracted fields (before: {len(merged_results['extracted_fields'])} fields)")
                    filtered_fields = filter_extracted_fields_by_type(
                        extracted_fields=merged_results["extracted_fields"],
                        entity_info=entity_info
                    )
                    extracted_fields = filtered_fields
                    logger.info(f"✅ Thread {idx}: After filtering: {len(extracted_fields)} fields")

                extraction_time = time.time() - extraction_start
                logger.info(f"✅ Thread {idx}: Extracted {len(extracted_fields)} fields in {extraction_time:.2f}s")

                # Load field mapping data for result building
                field_mapping_data = load_document_field_mappings(group['document_type'])

                # Start background compliance check
                file_content_hash = hashlib.md5(f"{file_name}_{group['document_type']}_{datetime.now().isoformat()}".encode()).hexdigest()
                compliance_thread = threading.Thread(
                    target=run_compliance_check_background,
                    args=(file_content_hash, extracted_fields, group['document_type']),
                    daemon=True
                )
                compliance_thread.start()

                # Build result object (simplified - no transform_compliance_for_ui)
                result = build_extraction_result(
                    group, extracted_fields, field_mapping_data, file_name,
                    all_preview_images, quality_time, ocr_time, classification_time,
                    extraction_time, quality_result, extraction_model, extraction_temp,
                    file_content_hash
                )

                # Put result in queue with index for proper ordering
                results_queue.put((idx, result))

                # Update progress
                if progress_tracker:
                    progress_tracker.update_field_extraction(current_field=idx, total_fields=len(document_groups))

            except Exception as e:
                logger.error(f"❌ Thread {idx} error: {e}")
                import traceback
                logger.error(traceback.format_exc())
                results_queue.put((idx, None))

        # Start all extraction threads with rate limiting (30s buffer every 3 documents)
        for idx, group in enumerate(document_groups, 1):
            thread = threading.Thread(target=extract_single_group, args=(idx, group), daemon=False)
            thread.start()
            threads.append(thread)
            
            # Add 15-second buffer after every 3 documents to prevent token limit
            if idx % 3 == 0 and idx < len(document_groups):
                logger.info(f"⏸️ Processed {idx} documents - Adding 15-second buffer to prevent rate limits...")
                time.sleep(15)
                logger.info(f"▶️ Resuming extraction for next batch...")
        
        logger.info(f"⏳ Waiting for all {len(threads)} extraction threads to complete...")

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Collect results in correct order
        results_dict = {}
        while not results_queue.empty():
            idx, result = results_queue.get()
            if result:
                results_dict[idx] = result

        # Return results in order
        results = [results_dict[i] for i in sorted(results_dict.keys()) if i in results_dict]

        logger.info(f"✅ Parallel extraction complete: {len(results)} document groups processed")
        
        # Add 15-second buffer after entity extraction before returning to next step
        logger.info(f"⏸️ Entity extraction complete - Adding 15-second buffer before proceeding...")
        time.sleep(15)
        logger.info(f"▶️ Proceeding to next processing step...")
        
        return results

    def build_extraction_result(group, extracted_fields, field_mapping_data, file_name,
                                all_preview_images, quality_time, ocr_time, classification_time,
                                extraction_time, quality_result, extraction_model, extraction_temp,
                                file_content_hash):
        """
        Build the result object for a single extraction (simplified and optimized).
        Removed dead code (unused transform functions) and simplified field categorization.
        """
        # === Categorize fields in a SINGLE PASS (optimization) ===
        mandatory_fields = {}
        optional_fields = {}
        conditional_fields = {}

        # Extract coordinate mapping stats before categorization
        coordinate_mapping_stats = extracted_fields.pop('_coordinate_mapping_stats', None)

        # Single-pass categorization
        if field_mapping_data:
            # Build field type lookup for O(1) access
            field_type_map = {}
            for mapping in field_mapping_data.get('mappings', []):
                entity_name = mapping.get('entityName')
                field_type = mapping.get('fieldType', 'optional')
                if entity_name:
                    field_type_map[entity_name] = field_type

            # Single loop through extracted fields
            for field_name, field_data in extracted_fields.items():
                field_type = field_type_map.get(field_name, 'optional')

                if field_type == 'mandatory':
                    mandatory_fields[field_name] = field_data
                elif field_type == 'conditional':
                    conditional_fields[field_name] = field_data
                else:
                    optional_fields[field_name] = field_data
        else:
            # No mappings - all optional
            optional_fields = extracted_fields

        # Calculate verdict from quality result
        verdict = quality_result.get("verdict", "pre_processing") if quality_result else "pre_processing"
        quality_score = quality_result.get("quality_score", 0.5) if quality_result else 0.5

        # Build result
        result = {
            "file_name": file_name,
            "document_type": group['document_type'],
            "confidence": int(group['confidence']),
            "complianceScore": 85,  # Default, will be updated by background compliance
            "classification": {
                "document_type": group['document_type'],
                "document_code": "",
                "document_id": "",
                "confidence": int(group['confidence']),
                "reasoning": f"Classified as {group['document_type']} with {group['confidence']:.0f}% confidence on {group['page_range']}"
            },
            "extraction": {
                "mandatory": mandatory_fields,
                "optional": optional_fields,
                "conditional": conditional_fields,
                "schema": {
                    "total_fields": len(extracted_fields),
                    "mandatory_count": len(mandatory_fields),
                    "optional_count": len(optional_fields),
                    "conditional_count": len(conditional_fields)
                },
                "document_id": group['document_type']
            },
            "compliance": {
                "unified": {}  # Will be populated by background thread
            },
            "preview_images": [all_preview_images[page-1] for page in group['pages'] if page-1 < len(all_preview_images)],
            "processing_time": {
                "total": f"{quality_time + ocr_time + classification_time + extraction_time:.1f}",
                "quality_analysis": f"{quality_time:.1f}",
                "ocr": f"{ocr_time:.1f}",
                "classification": f"{classification_time:.1f}",
                "extraction": f"{extraction_time:.1f}",
                "coordinate_mapping": "0.0",
                "compliance_analysis": "0.0"
            },
            "quality_analysis": {
                "verdict": verdict,
                "score": quality_score,
                "recommendations": quality_result.get("recommendations", []) if quality_result else [],
                "detailed_metrics": quality_result.get("page_results", []) if quality_result else [],
                "processing_time": quality_result.get("processing_time", 0) if quality_result else 0,
                "page_count": len(quality_result.get("page_results", [])) if quality_result else 0,
                "average_metrics": _calculate_average_metrics(quality_result.get("page_results", [])) if quality_result else {}
            },
            "coordinate_mapping": coordinate_mapping_stats,
            "ocr_data": {
                "pages": group['pages'],
                "page_range": group['page_range'],
                "text_entries": len(group['ocr_data']),
                "formatted_text": group['text'][:500] + "..." if len(group['text']) > 500 else group['text'],
                "individual_pages": group.get('individual_pages', [])
            },
            "success": True,
            "enhanced_mode": True,
            "page_by_page_mode": True,
            "compliance_hash": file_content_hash,
            "compliance_status": "processing",
            "qualityTime": f"{quality_time:.1f}",
            "ocrTime": f"{ocr_time:.1f}",
            "classificationTime": f"{classification_time:.1f}",
            "llmTime": f"{extraction_time:.1f}",
            "complianceTime": "0.0",
            "config_used": {
                "extraction_model": extraction_model,
                "extraction_temp": extraction_temp
            },
            "field_mapping_enhanced": bool(field_mapping_data)
        }

        return result

    def process_document_page_by_page(uploaded_file, function_name=None, product_name=None,
                                      document_type=None, progress_tracker=None, config=None,
                                      pause_after_classification=False):
        import pickle
# ================================================================= STEP 1: QUALITY ANALYSIS (Using Separated Service) ============================================================================
        quality_service = QualityAnalysisService()
        step1_result = quality_service.analyze(uploaded_file, progress_tracker)
        if not step1_result.success:
            logger.error(f"❌ Quality analysis failed: {step1_result.error}")
            return [{
                "file_name": uploaded_file.filename,
                "error": step1_result.error,
                "stage": "quality_analysis"
            }]
        try:
            logger.info(
                f"=== Page-by-page processing for {step1_result.file_name} (pause_after_classification={pause_after_classification}) ===")
            start_time = time.time()
            logger.info(f"✅ Step 1 (Quality Analysis) completed via QualityAnalysisService")
            logger.info(f"   - Verdict: {step1_result.verdict}, Score: {step1_result.quality_score:.3f}, Time: {step1_result.processing_time:.2f}s")
# ================================================================== STEP 2: OCR EXTRACTION (Using Separated Service) ============================================================================
            ocr_service = OCRExtractionService()
            step2_result = ocr_service.extract(
                temp_file_path=step1_result.temp_file_path,
                file_type=step1_result.file_type,
                quality_verdict=step1_result.verdict,
                estimated_pages=step1_result.quality_result.get("pages_analyzed", 1),
                progress_tracker=progress_tracker
            )
            if not step2_result.success:
                logger.error(f"❌ OCR extraction failed: {step2_result.error}")
                return [{
                    "file_name": step1_result.file_name,
                    "error": step2_result.error,
                    "stage": "OCR"
                }]
            # Extract results from step2_result
            text_data = step2_result.text_data
            word_data = step2_result.word_data
            pages_ocr_data = step2_result.pages_ocr_data
            ocr_time = step2_result.processing_time
            logger.info(f"✅ Step 2 (OCR Extraction) completed via OCRExtractionService")
            logger.info(f"   - Pages: {step2_result.page_count}, Entries: {len(text_data)}, Time: {ocr_time:.2f}s")
#================================================================== STEP 3: PAGE CLASSIFICATION (Using Separated Service) ========================================================================
            classification_service = ClassificationService(document_classifier)
            step3_result = classification_service.classify(
                pages_ocr_data=pages_ocr_data,
                progress_tracker=progress_tracker
            )
            if not step3_result.success:
                logger.error(f"❌ Classification failed: {step3_result.error}")
                return [{
                    "file_name": step1_result.file_name,
                    "error": step3_result.error,
                    "stage": "classification"
                }]
            # Convert PageClassification objects to dictionaries for backward compatibility
            page_classifications = [pc.to_dict() for pc in step3_result.page_classifications]
            classification_time = step3_result.processing_time
            logger.info(f"✅ Step 3 (Classification) completed via ClassificationService")
            logger.info(f"   - Pages: {len(page_classifications)}, Unique Types: {len(step3_result.unique_document_types)}, Time: {classification_time:.2f}s")
#================================================================= STEP 4: VALIDATE DOCUMENT TYPES (Using Separated Service) =====================================================================
            # Initialize validation service with entity mappings from document classifier
            validation_service = DocumentValidationService(document_classifier.entity_mappings)
            # Run validation (includes Step 4.1 validation and Step 4.2 duplicate filtering)
            validation_result = validation_service.validate(
                page_classifications=page_classifications,
                filter_duplicates=True,
                high_confidence_threshold=99.0
            )
            # Update page_classifications with validated results
            page_classifications = validation_result.validated_classifications
            validation_time = validation_result.processing_time
            logger.info(f"✅ Step 4 (Validation) completed via DocumentValidationService")
            logger.info(f"   - Valid: {validation_result.valid_count}, Mapped: {validation_result.mapped_count}, Invalid: {validation_result.invalid_count}")
            logger.info(f"   - Duplicates filtered: {validation_result.duplicate_count}, Time: {validation_time:.2f}s")
#======================================================== STEP 5: GROUPING CONSECUTIVE PAGES =====================================================================================
            # Use PageGroupingService for Step 5 (Separated Business Logic)
            grouping_service = PageGroupingService()
            grouping_result = grouping_service.group(page_classifications)
            # Convert DocumentGroup objects to dictionaries for compatibility with downstream code
            document_groups = grouping_result.get_groups_as_dicts()
            logger.info(f"✅ Step 5 (Grouping) completed via PageGroupingService")
            logger.info(f"   - Groups created: {len(document_groups)}, Skipped: {grouping_result.pages_skipped}, Continuation merged: {grouping_result.continuation_pages_merged}")
            # === STORE OCR DATA TEMPORARILY (for reuse during revalidation) ===
            temp_dir = tempfile.gettempdir()
            ocr_session_id = str(uuid.uuid4())
            ocr_temp_file = os.path.join(temp_dir, f"ocr_data_{ocr_session_id}.pkl")

            ocr_context = {
                "word_data":word_data,
                "ocr_data": text_data,
                "pages_ocr_data": pages_ocr_data,
                "quality_result": step1_result.quality_result,
                "file_name": step1_result.file_name,
                "file_type": step1_result.file_type,
                "temp_file_path": step1_result.temp_file_path,
                "quality_time": step1_result.processing_time,
                "ocr_time": ocr_time,
                "classification_time": classification_time
            }

            with open(ocr_temp_file, 'wb') as f:
                pickle.dump(ocr_context, f)

            logger.info(f"💾 OCR context saved: {ocr_temp_file}")
            logger.info(f"🔑 Session ID: {ocr_session_id}")

            # === GET AVAILABLE DOCUMENT TYPES FOR DROPDOWN ===
            try:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                field_mappings_dir = os.path.join(base_dir, 'field_mappings')

                available_document_types = []

                if os.path.exists(field_mappings_dir):
                    json_files = glob.glob(os.path.join(field_mappings_dir, "*.json"))
                    for json_file in json_files:
                        doc_type = os.path.splitext(os.path.basename(json_file))[0]
                        # Convert snake_case to Title Case
                        readable_type = doc_type.replace('_', ' ').title()
                        available_document_types.append(readable_type)
                    available_document_types = sorted(available_document_types)
                    logger.info(f"📋 Found {len(available_document_types)} document types from field mappings")

                if not available_document_types:
                    logger.info("📋 Using fallback document types list")
                    available_document_types = [
                        "Airway Bill",
                        "Bill of Lading",
                        "Certificate of Origin",
                        "Commercial Invoice",
                        "Credit Note",
                        "Customs Declaration",
                        "Debit Note",
                        "Delivery Note",
                        "Insurance Certificate",
                        "Invoice",
                        "Packing List",
                        "Proforma Invoice",
                        "Purchase Order",
                        "Quotation",
                        "Receipt",
                        "Shipping Instruction"
                    ]

                logger.info(f"📋 Available document types: {len(available_document_types)}")

            except Exception as e:
                logger.error(f"❌ Error loading document types: {e}")
                available_document_types = [
                    "Bill of Lading",
                    "Commercial Invoice",
                    "Invoice",
                    "Packing List",
                    "Purchase Order"
                ]

            # === EARLY RETURN (PAUSE) FOR USER REVIEW ===
            if pause_after_classification:
                logger.info(f"⏸️ Pausing after classification for user review")
                total_time = time.time() - start_time

                # Generate preview images
                preview_images = []
                if step1_result.file_type == "application/pdf":
                    pdf_result = convert_pdf_to_images_opencv(step1_result.temp_file_path)
                    if pdf_result.get("type") == "image":
                        preview_images = pdf_result.get("data", [])
                        logger.info(f"🖼️ Generated {len(preview_images)} preview images")
                else:
                    encoded_image = encode_image_to_base64(step1_result.temp_file_path)
                    if encoded_image:
                        preview_images = [encoded_image]
                        logger.info(f"🖼️ Generated 1 preview image")

                # Send pause notification via progress tracker
                if progress_tracker:
                    try:
                        progress_tracker.send_progress({
                            "stage": "paused",
                            "status": "paused_for_review",
                            "message": "Classification complete - Awaiting user confirmation",
                            "progress": 60,
                            "timestamp": time.time()
                        })
                        logger.info("📢 Sent pause notification to frontend")
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to send pause notification: {e}")

                return {
                    "success": True,
                    "stage": "classification_review",
                    "ocr_session_id": ocr_session_id,
                    "file_name": step1_result.file_name,
                    "document_groups": [
                        {
                            "group_id": idx,
                            "document_type": group['document_type'],
                            "page_range": group['page_range'],
                            "pages": group['pages'],
                            "confidence": round(group['confidence'], 2),
                            "text_preview": (group['text'][:200] + "...") if len(group['text']) > 200 else group['text'],
                            "file_name": step1_result.file_name,
                            "fileName": step1_result.file_name
                        }
                        for idx, group in enumerate(document_groups)
                    ],
                    "available_document_types": available_document_types,
                    "preview_images": preview_images,
                    "processing_time": {
                        "total": f"{total_time:.2f}",
                        "quality_analysis": f"{step1_result.processing_time:.2f}",
                        "ocr": f"{ocr_time:.2f}",
                        "classification": f"{classification_time:.2f}"
                    },
                    "config_version": config.get('version', 'v1.0') if config else 'v1.0',
                    "metadata": {
                        "total_pages": len(pages_ocr_data),
                        "total_groups": len(document_groups),
                        "quality_verdict": step1_result.verdict,
                        "quality_score": round(step1_result.quality_score, 3)
                    }
                }

        except Exception as e:
            logger.error(f"❌ Error in page-by-page processing: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return [{
                "file_name": uploaded_file.filename,
                "error": str(e),
                "stage": "processing"
            }]
        finally:
            # Only cleanup if NOT paused (Stage 2 needs the temp file)
            if not pause_after_classification:
                # Use QualityAnalysisService's cleanup method
                QualityAnalysisService.cleanup_temp_file(step1_result.temp_file_path)

    @app.route('/api/document/classify-initial', methods=['POST'])
    def classify_document_initial():
        """
        Stage 1: Perform OCR + Classification + Grouping
        Pause for user classification correction (no extraction yet)
        """
        logger.info("=== API CALL: /api/document/classify-initial (Stage 1) ===")
        from app.utils.reload_helper import reload_all_jsons
        reload_all_jsons()
        try:
            # === INPUT VALIDATION ===
            uploaded_files = request.files.getlist('files')
            if not uploaded_files:
                return jsonify({"error": "No files uploaded"}), 400

            if len(uploaded_files) > 1:
                return jsonify({"error": "Stage 1 supports single file only"}), 400

            uploaded_file = uploaded_files[0]
            file_name = uploaded_file.filename

            # Get parameters
            function_name = request.form.get('functionName', '')
            product_name = request.form.get('productName', '')
            document_type = request.form.get('documentType', '')
            client_id = request.form.get('client_id', None)
            page_by_page = request.form.get('page_by_page', 'false').lower() == 'true'

            logger.info(f"📄 Starting initial classification for {file_name}")
            logger.info(f"   Function: {function_name}, Product: {product_name}, DocType: {document_type}")
            logger.info(f"   Client ID: {client_id}, Page-by-page: {page_by_page}")

            # === INITIALIZE PROGRESS TRACKER ===
            progress_tracker = None
            if client_id:
                try:
                    ws_handler = get_websocket_handler()
                    if ws_handler:
                        progress_tracker = DocumentProcessingTracker(ws_handler, client_id)
                        logger.info(f"✅ Progress tracker initialized for client: {client_id}")
                except Exception as e:
                    logger.error(f"❌ Failed to initialize progress tracker: {e}")

            # === LOAD PROMPT CONFIG ===
            prompt_config = load_prompt_config()
            if not prompt_config:
                logger.warning("⚠️ Prompt config not loaded, using defaults")
                prompt_config = {}

            # === CALL PROCESSING FUNCTION WITH PAUSE FLAG ===
            result = process_document_page_by_page(
                uploaded_file=uploaded_file,
                function_name=function_name,
                product_name=product_name,
                document_type=document_type,
                progress_tracker=progress_tracker,
                config=prompt_config,
                pause_after_classification=True
            )

            logger.info(f"✅ Stage 1 completed - Returning classification results")

            return jsonify(result)

        except Exception as e:
            logger.error(f"❌ Error in /api/document/classify-initial: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return jsonify({
                "success": False,
                "error": str(e),
                "stage": "initialization"
            }), 500

    @app.route('/api/document/revalidate-entities', methods=['POST'])
    def revalidate_entities_after_classification():
        """
        Stage 2: Revalidate extraction + compliance after user confirms/changes classifications
        Uses the COMPLETE extraction logic from process_document_page_by_page
        """
        logger.info("=== API CALL: /api/document/revalidate-entities (Stage 2) ===")

        import pickle
        import tempfile
        import os
        import time
        import hashlib
        import threading
        import json
        from datetime import datetime

        # from app.utils.reload_helper import reload_all_jsons
        # reload_all_jsons()
        try:
            # === INPUT VALIDATION ===
            data = request.get_json()

            ocr_session_id = data.get('ocr_session_id')
            confirmed_groups = data.get('confirmed_groups', [])
            client_id = data.get('client_id', None)

            if not ocr_session_id:
                return jsonify({"error": "Missing ocr_session_id"}), 400

            if not confirmed_groups:
                return jsonify({"error": "Missing confirmed_groups"}), 400

            logger.info(f"🔄 Stage 2 - Revalidating {len(confirmed_groups)} document groups")
            logger.info(f"🔑 Session ID: {ocr_session_id}")

            # === LOAD PROMPT CONFIG ===
            prompt_config = load_prompt_config()
            if not prompt_config:
                logger.warning("⚠️ Prompt config not loaded, using defaults")
                prompt_config = {}

            config_version = 'v1.0'
            if prompt_config and isinstance(prompt_config, dict):
                config_version = prompt_config.get('version', 'v1.0')

            # === INITIALIZE PROGRESS TRACKER ===
            progress_tracker = None
            if client_id:
                try:
                    ws_handler = get_websocket_handler()
                    if ws_handler:
                        progress_tracker = DocumentProcessingTracker(ws_handler, client_id)
                        logger.info(f"✅ Progress tracker initialized for client: {client_id}")
                except Exception as e:
                    logger.error(f"❌ Failed to initialize progress tracker: {e}")

            # === LOAD OCR CONTEXT FROM TEMP FILE ===
            temp_dir = tempfile.gettempdir()
            ocr_temp_file = os.path.join(temp_dir, f"ocr_data_{ocr_session_id}.pkl")

            if not os.path.exists(ocr_temp_file):
                logger.error(f"❌ OCR session data not found: {ocr_temp_file}")
                return jsonify({
                    "success": False,
                    "error": "OCR session data not found or expired"
                }), 404

            logger.info(f"📂 Loading OCR context from: {ocr_temp_file}")

            with open(ocr_temp_file, 'rb') as f:
                ocr_context = pickle.load(f)

            # Extract context data
            word_data = ocr_context.get("word_data",[])
            pages_ocr_data = ocr_context.get("pages_ocr_data", [])
            quality_result = ocr_context.get("quality_result", {})
            file_name = ocr_context.get("file_name", "Unknown")
            file_type = ocr_context.get("file_type", "application/pdf")
            temp_file_path = ocr_context.get("temp_file_path", "")
            quality_time = ocr_context.get("quality_time", 0.0)
            ocr_time = ocr_context.get("ocr_time", 0.0)
            classification_time = ocr_context.get("classification_time", 0.0)

            logger.info(f"✅ OCR context loaded for: {file_name}")
            logger.info(f"📄 Pages: {len(pages_ocr_data)}")

            # === RECONSTRUCT DOCUMENT GROUPS FROM USER CONFIRMATION ===
            logger.info(f"🔄 Reconstructing document groups from user input")

            document_groups = []
            for group_data in confirmed_groups:
                document_type = group_data.get('document_type')
                pages = group_data.get('pages', [])

                if not document_type or not pages:
                    logger.warning(f"⚠️ Skipping incomplete group: {group_data}")
                    continue

                # Rebuild OCR data for this group's pages
                group_ocr_data = []
                group_text = ""
                individual_pages = []

                for page_num in pages:
                    page_idx = page_num - 1
                    if 0 <= page_idx < len(pages_ocr_data):
                        page_data = pages_ocr_data[page_idx]
                        group_ocr_data.extend(page_data)
                        page_text = "\n".join([text['text'] for text in page_data])
                        group_text += "\n" + page_text

                        individual_pages.append({
                            'page': page_num,
                            'document_type': document_type,
                            'confidence': group_data.get('confidence', 100),
                            'text': page_text,
                            'ocr_data': page_data,
                            'is_continuation': False
                        })

                reconstructed_group = {
                    'document_type': document_type,
                    'pages': pages,
                    'page_range': (f"Page {pages[0]}" if len(pages) == 1
                                   else f"Pages {pages[0]}-{pages[-1]}"),
                    'text': group_text.strip(),
                    'ocr_data': group_ocr_data,
                    'confidence': group_data.get('confidence', 100),
                    'individual_pages': individual_pages
                }

                document_groups.append(reconstructed_group)
                logger.info(f"✅ Reconstructed: {document_type} ({reconstructed_group['page_range']})")

            if not document_groups:
                return jsonify({
                    "success": False,
                    "error": "No valid document groups to process"
                }), 400

            # === REGENERATE PREVIEW IMAGES ===
            all_preview_images = []
            if temp_file_path and os.path.exists(temp_file_path):
                logger.info(f"🖼️ Generating preview images")
                if file_type == "application/pdf":
                    pdf_result = convert_pdf_to_images_opencv(temp_file_path)
                    if pdf_result.get("type") == "image":
                        all_preview_images = pdf_result.get("data", [])
                        logger.info(f"✅ Generated {len(all_preview_images)} preview images")
                else:
                    encoded_image = encode_image_to_base64(temp_file_path)
                    if encoded_image:
                        all_preview_images = [encoded_image]

            # === LOAD EXTRACTION SETTINGS ===
            extraction_config = prompt_config.get('extraction', {}) if prompt_config else {}
            extraction_model = extraction_config.get('model', deployment_name)
            extraction_temp = extraction_config.get('temperature', 0.0)
            extraction_max_tokens = extraction_config.get('max_tokens', 16000)

            logger.info(
                f"⚙️ Extraction: model={extraction_model}, temp={extraction_temp}, max_tokens={extraction_max_tokens}")

            # === START FIELD EXTRACTION ===
            if progress_tracker:
                progress_tracker.start_field_extraction(field_count=len(document_groups))

            logger.info(f"🚀 STEP 5/5: EXTRACTING FIELDS")
            start_time = time.time()

            use_parallel_extraction = len(document_groups) > 1

            if use_parallel_extraction:
                logger.info(f"⚡ Using PARALLEL extraction for {len(document_groups)} groups")
                results = extract_fields_parallel(
                    document_groups,
                    document_classifier,
                    extraction_model,
                    extraction_temp,
                    extraction_max_tokens,
                    file_name,
                    all_preview_images,
                    quality_time,
                    ocr_time,
                    classification_time,
                    quality_result,
                    progress_tracker
                )
            else:
                # === SEQUENTIAL EXTRACTION (FULL LOGIC FROM DOCUMENT 7) ===
                logger.info(f"📄 Using SEQUENTIAL extraction for {len(document_groups)} group(s)")
                results = []

                for idx, group in enumerate(document_groups, 1):
                    logger.info(
                        f"📝 Extracting fields for {group['document_type']} (Group {idx}/{len(document_groups)})")

                    if progress_tracker:
                        progress_tracker.update_field_extraction(current_field=idx, total_fields=len(document_groups))

                    extraction_start = time.time()

                    # Build extraction prompt
                    extraction_prompt = document_classifier.build_extraction_prompt(
                        document_type=group['document_type'],
                        ocr_text=group['text'],
                        page_number=group['pages'][0]
                    )
                    logger.info(f"📝 Built extraction prompt ({len(extraction_prompt)} chars)")

                    # Add field mappings
                    field_mapping_data = load_document_field_mappings(group['document_type'])
                    field_mapping_example = None
                    if field_mapping_data:
                        field_mapping_example = field_mapping_data.get('example', '')
                        extraction_prompt += f"\n\n{field_mapping_example}"
                        logger.info(f"📝 Added field mapping examples ({len(field_mapping_example)} chars)")

                    logger.info(f"🤖 Calling LLM API (model: {extraction_model}, temp: {extraction_temp})")

                    # Check if parallel extraction is enabled for individual documents
                    enable_parallel = extraction_config.get('enable_parallel_extraction', False)
                    parallel_attempts = extraction_config.get('parallel_extraction_attempts', 3)
                    aggregation_strategy = extraction_config.get('aggregation_strategy', 'union')
                    confidence_threshold = extraction_config.get('confidence_threshold', 70)

                    if enable_parallel and parallel_attempts > 1:
                        # ======= NEW: CHUNK-BASED EXTRACTION FOR REVALIDATE-ENTITIES =======
                        logger.info(f"🧩 Chunk-based extraction ENABLED for revalidate-entities: Processing entities in logical chunks")

                        # Get entity information for chunk-based processing
                        doc_type_normalized = group['document_type'].replace(' ', '_').lower()
                        entity_info = document_classifier.get_enhanced_entity_fields(doc_type_normalized)
                        
                        if entity_info and entity_info.get('mandatory_fields'):
                            logger.info(f"📋 Entity info loaded for {group['document_type']}: {len(entity_info['mandatory_fields'])} mandatory, {len(entity_info['optional_fields'])} optional")
                            
                            # Log document type being passed
                            logger.info(f"🔍 Passing document_type to extraction: '{group['document_type']}'")
                            
                            # Use new chunk-based extraction instead of redundant parallel calls
                            extraction_results = extract_entities_in_chunks(
                                entity_info=entity_info,
                                ocr_text=group['text'],
                                model=extraction_model,
                                page_number=group['pages'][0],  # Use first page number
                                document_type=group['document_type']
                            )
                          
                            # Merge results from all chunks
                            extracted_fields = {}
                            total_fields_extracted = 0
                            
                            for result in extraction_results:
                                if result and 'extracted_fields' in result:
                                    extracted_fields.update(result["extracted_fields"])
                                    total_fields_extracted += len(result["extracted_fields"])

                            # ======= FILTER FIELDS BY TYPE: Keep mandatory always, optional/conditional only if they have values =======
                            filtered_fields = filter_extracted_fields_by_type(
                                extracted_fields=extracted_fields,
                                entity_info=entity_info
                            )

                            # Create extraction_json in expected format
                            extraction_json = {
                                "extracted_fields": filtered_fields,
                                "confidence_score": 85,  # Default confidence for chunk-based extraction
                                "extraction_method": "chunk_based"
                            }

                            logger.info(f"✅ Chunk-based extraction successful: {len(filtered_fields)} filtered fields from {len(extraction_results)} chunks (was {total_fields_extracted} before filtering)")
                            
                        else:
                            logger.error(f"❌ Could not load entity info for document type: {group['document_type']}")
                            # Fallback to single extraction
                            enable_parallel = False

                    else:
                        # SINGLE EXTRACTION (Original)
                        logger.info(f"📤 Using single extraction call")

                        import openai
                        extraction_response = openai.ChatCompletion.create(
                            engine=extraction_model,
                            messages=[{"role": "user", "content": extraction_prompt}],
                            temperature=0,
                            max_tokens=extraction_max_tokens,
                            seed=12345,
                            top_p=0.1,
                            frequency_penalty=0,
                            presence_penalty=0,
                            response_format={"type": "json_object"}
                        )
                        extraction_result = extraction_response.choices[0].message.content

                        logger.info(f"✅ Received LLM response ({len(extraction_result)} chars)")

                        # Parse extraction result
                        try:
                            logger.info(f"🔍 Raw response (first 500 chars): {extraction_result[:500]}")

                            # Extract JSON from markdown if present
                            if '```json' in extraction_result:
                                json_start = extraction_result.find('```json') + 7
                                json_end = extraction_result.find('```', json_start)
                                extraction_result = extraction_result[json_start:json_end].strip()
                                logger.info("🔍 Extracted JSON from markdown")
                            elif '```' in extraction_result:
                                json_start = extraction_result.find('```') + 3
                                json_end = extraction_result.find('```', json_start)
                                extraction_result = extraction_result[json_start:json_end].strip()

                            extraction_json = json.loads(extraction_result)
                            extracted_fields = extraction_json.get('extracted_fields', {})
                            logger.info(f"✅ Parsed {len(extracted_fields)} fields")
                        except json.JSONDecodeError as e:
                            logger.error(f"❌ JSON parsing failed: {e}")
                            logger.error(f"❌ Response: {extraction_result[:1000]}")
                            extracted_fields = {}
                        except Exception as e:
                            logger.error(f"❌ Unexpected error: {e}")
                            extracted_fields = {}

                    # ======= FILTER FIELDS BY TYPE (Single Extraction in Revalidate) =======
                    doc_type_normalized = group['document_type'].replace(' ', '_').lower()
                    entity_info_for_filtering = document_classifier.get_enhanced_entity_fields(doc_type_normalized)
                    
                    if entity_info_for_filtering and extracted_fields:
                        filtered_fields = filter_extracted_fields_by_type(
                            extracted_fields=extracted_fields,
                            entity_info=entity_info_for_filtering
                        )
                        extracted_fields = filtered_fields
                        logger.info(f"📋 Single extraction (revalidate): Applied field filtering (mandatory always shown, optional/conditional only if populated)")

                    extraction_time = time.time() - extraction_start
                    logger.info(f"✅ Extraction completed in {extraction_time:.2f}s - {len(extracted_fields)} fields")

                    # === BACKGROUND COMPLIANCE ANALYSIS ===
                    file_content_hash = hashlib.md5(
                        f"{file_name}_{group['document_type']}_{datetime.now().isoformat()}".encode()
                    ).hexdigest()
                    logger.info(f"🚀 Starting background compliance check for {file_content_hash}")

                    compliance_thread = threading.Thread(
                        target=run_compliance_check_background,
                        args=(file_content_hash, extracted_fields, group['document_type']),
                        daemon=True
                    )
                    compliance_thread.start()
                    logger.info(f"✅ Compliance check running in background")

                    # Build result using helper function
                    result = build_extraction_result(
                        group, extracted_fields, field_mapping_data, file_name,
                        all_preview_images, quality_time, ocr_time, classification_time,
                        extraction_time, quality_result, extraction_model, extraction_temp,
                        file_content_hash
                    )
                    results.append(result)
            extraction_total_time = time.time() - start_time
            logger.info(f"✅ All extractions completed in {extraction_total_time:.2f}s")

            # === MARK FIELD EXTRACTION COMPLETE ===
            if progress_tracker:
                total_extracted = sum(
                    len(result.get("extraction", {}).get("mandatory", {})) +
                    len(result.get("extraction", {}).get("optional", {})) +
                    len(result.get("extraction", {}).get("conditional", {}))
                    for result in results
                )
                progress_tracker.field_extraction_complete(extracted_count=total_extracted)
                logger.info(f"✅ {total_extracted} total fields extracted")

            # === CALCULATE TOTAL PROCESSING TIME ===
            total_time = sum(
                float(result["processing_time"]["total"])
                for result in results
                if "processing_time" in result and "total" in result["processing_time"]
            )
            logger.info(f"⏱️ Total time: {total_time:.2f}s")

            # Add actual_total to each result
            for result in results:
                if "processing_time" in result:
                    result["processing_time"]["actual_total"] = f"{total_time:.1f}"

            # === COMPLETE PROGRESS ===
            if progress_tracker:
                total_docs = len(results)
                total_fields = sum(
                    len(result.get("extraction", {}).get("mandatory", {})) +
                    len(result.get("extraction", {}).get("optional", {})) +
                    len(result.get("extraction", {}).get("conditional", {}))
                    for result in results
                )
                progress_tracker.complete_with_summary(
                    doc_type=f"{total_docs} document types",
                    fields_extracted=total_fields,
                    compliance_status="Checked"
                )

            # === STORE OCR DATA FOR COORDINATE SEARCH (FROM DOCUMENT 7) ===
            logger.info(f"💾 === STORING OCR DATA FOR COORDINATE SEARCH ===")
            all_ocr_data = []
            ocr_stats = {'total_entries': 0, 'pages': 0, 'text_entries': 0, 'with_bbox': 0}

            for group_idx, group in enumerate(document_groups):
                group_ocr = group.get('ocr_data', [])
                logger.info(f"📊 Group {group_idx + 1} ({group.get('document_type')}): {len(group_ocr)} OCR entries")

                for entry in group_ocr:
                    ocr_stats['total_entries'] += 1
                    if entry.get('text'):
                        ocr_stats['text_entries'] += 1
                    if entry.get('bounding_box'):
                        ocr_stats['with_bbox'] += 1

                all_ocr_data.extend(group_ocr)

            # Generate unique session ID for OCR data
            import uuid
            final_ocr_session_id = str(uuid.uuid4())

            # Store OCR data in temporary file
            final_ocr_temp_file = os.path.join(temp_dir, f"ocr_data_{final_ocr_session_id}.pkl")
            word_temp_file = os.path.join(temp_dir, f"word_data_{final_ocr_session_id}.pkl")
            try:
                with open(final_ocr_temp_file, 'wb') as f:
                    pickle.dump(all_ocr_data, f)
                with open(word_temp_file, "wb") as f:
                    pickle.dump(word_data, f)
                logger.info(f"💾 OCR data stored: {final_ocr_temp_file}")
                logger.info(f"🔑 New OCR session ID: {final_ocr_session_id}")

                # Store in session for coordinate search
                from flask import session
                session['ocr_session_id'] = final_ocr_session_id

            except Exception as e:
                logger.error(f"❌ Failed to store OCR data: {e}")

            logger.info(f"📊 OCR STORAGE SUMMARY:")
            logger.info(f"   Total entries: {len(all_ocr_data)}")
            logger.info(f"   With text: {ocr_stats['text_entries']}")
            logger.info(f"   With bounding boxes: {ocr_stats['with_bbox']}")

            # === CLEANUP TEMP FILES ===
            try:
                if temp_file_path and os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
                    logger.info(f"🗑️ Cleaned up temp file")

                if os.path.exists(ocr_temp_file):
                    os.remove(ocr_temp_file)
                    logger.info(f"🗑️ Cleaned up OCR context file")
            except Exception as cleanup_error:
                logger.warning(f"⚠️ Cleanup failed: {cleanup_error}")

            # === RETURN FINAL RESULTS ===
            logger.info(f"✅ Stage 2 completed - Returning {len(results)} results")
            # with open("wtesting.json", "w") as file:
            #     json.dump(results, file, indent=4)
            return jsonify({
                "success": True,
                "results": results,
                "total_files": len(results),
                "config_loaded": bool(prompt_config),
                "config_version": config_version
            })

        except Exception as e:
            logger.error(f"❌ Error in /api/document/revalidate-entities: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())

            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    # NOTE: /api/document/extract-region route is registered in Bounding_Boxes module

    @app.route('/api/document/sync-with-classification', methods=['POST'])
    @timing_aspect
    def sync_with_classification():
        """Sync classification results with document register for Smart Capture"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'error': 'No data provided'
                }), 400

            extracted_fields = data.get('extracted_fields', {})
            document_type = data.get('document_type', '')
            file_name = data.get('file_name', '')

            logger.info(f"🔄 Syncing classification data for {file_name}")
            logger.info(f"   Document Type: {document_type}")
            logger.info(f"   Fields: {len(extracted_fields)} extracted")

            # Create a prefill URL with classification data
            base_url = '/document_register'

            # Build query parameters for prefilling the form
            params = []
            if document_type:
                params.append(f'documentType={document_type}')
            if file_name:
                params.append(f'fileName={file_name}')

            # Add key extracted fields as query parameters
            field_mapping = {
                'invoice_number': 'invoiceNumber',
                'lc_number': 'lcNumber',
                'amount': 'amount',
                'currency': 'currency',
                'date': 'date',
                'description': 'description',
                'applicant': 'applicant',
                'beneficiary': 'beneficiary'
            }

            for field_name, value in extracted_fields.items():
                if field_name in field_mapping and value:
                    # Handle different field value structures
                    field_value = value
                    if isinstance(value, dict):
                        field_value = value.get('value', value.get('text', ''))

                    if field_value:
                        params.append(f'{field_mapping[field_name]}={field_value}')

            # Build final URL with prefill data
            register_url = base_url
            if params:
                register_url += '?' + '&'.join(params)

            logger.info(f"✅ Created prefill URL: {register_url}")

            return jsonify({
                'success': True,
                'register_url': register_url,
                'prefill_data': {
                    'document_type': document_type,
                    'file_name': file_name,
                    'extracted_fields': extracted_fields
                }
            })

        except Exception as e:
            logger.error(f"❌ Error in sync-with-classification: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500


    def classify_and_check_compliance(uploaded_file, check_compliance=True, product_name=None, function_name=None, document_type=None, progress_tracker=None):
        """Classify document and check compliance with progress tracking"""
        import time

        try:
            file_name = uploaded_file.filename
            file_type = uploaded_file.content_type
            logger.info(f"=== Starting classify_and_check_compliance for {file_name} ===")
            logger.info(f"File type: {file_type}, Check compliance: {check_compliance}")
            logger.info(f"Product: {product_name}, Function: {function_name}, DocumentType: {document_type}")

            # Initialize timing
            start_time = time.time()
            ocr_start = time.time()

            # Progress: Start upload
            if progress_tracker:
                progress_tracker.start_upload(file_name)

            # Save to temporary file
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_file_path = temp_file.name
                uploaded_file.save(temp_file_path)
                logger.info(f"Saved file to temporary path: {temp_file_path}")

            # Progress: Upload complete
            if progress_tracker:
                progress_tracker.upload_complete()

            try:
                # Progress: Start OCR
                if progress_tracker:
                    progress_tracker.start_ocr()

                # Extract text (OCR process)
                logger.info(f"Starting OCR extraction for {file_name}")
                extracted_text_data = extract_text_from_file(temp_file_path, file_type)
                text_data = extracted_text_data.get("text_data", [])
                ocr_time = time.time() - ocr_start
                logger.info(f"OCR extraction completed in {ocr_time:.2f}s, extracted {len(text_data)} text entries")

                # Progress: OCR complete
                if progress_tracker:
                    progress_tracker.ocr_complete(extracted_entries=len(text_data))

                if not text_data:
                    logger.warning(f"No text extracted from file: {file_name}")
                    return {
                        "file_name": file_name,
                        "error": "No text could be extracted from the file"
                    }

                # Organize pages and process with LLM (similar to process_uploaded_files)
                pages_ocr_data = organize_ocr_data_by_page(text_data)
                logger.info(f"Organized text into {len(pages_ocr_data)} pages")

                # Start LLM analysis timing
                llm_start = time.time()

                # Progress: Start classification
                if progress_tracker:
                    progress_tracker.start_classification()

                # Process all pages concurrently
                logger.info(f"Starting concurrent LLM analysis for {len(pages_ocr_data)} pages")
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    page_analysis_results = list(executor.map(
                        lambda args: process_page_with_llm_analysis(*args),
                        [(page_number, page_data, None, None, product_name, function_name, document_type)
                         for page_number, page_data in enumerate(pages_ocr_data, start=1)]
                    ))
                logger.info(f"Completed LLM analysis for all pages")

                llm_time = time.time() - llm_start

                # Aggregate unified compliance results
                combined_unified_result = {}

                for page_result in page_analysis_results:
                    # Aggregate unified compliance results
                    if "unified_compliance" in page_result:
                        combined_unified_result.update(page_result["unified_compliance"])

                # Start classification timing
                classification_start = time.time()

                # Get document type and confidence from first page
                document_type = "Unknown"
                confidence = 0
                if page_analysis_results:
                    first_page_classification = page_analysis_results[0].get("classification", {})
                    document_type = first_page_classification.get("document_type", "Unknown")
                    confidence = page_analysis_results[0].get("confidence_score", 0) / 100.0

                classification_time = time.time() - classification_start

                # Progress: Classification complete
                if progress_tracker:
                    progress_tracker.classification_complete(
                        doc_type=document_type,
                        confidence=int(confidence * 100)
                    )

                # Progress: Start field extraction
                if progress_tracker:
                    # Count fields from first page
                    field_count = 0
                    if page_analysis_results and len(page_analysis_results) > 0:
                        field_count = len(page_analysis_results[0].get("extracted_fields", {}))
                    progress_tracker.start_field_extraction(field_count=field_count)

                # Progress: Field extraction complete
                if progress_tracker:
                    # Count extracted fields from first page
                    extracted_count = 0
                    if page_analysis_results and len(page_analysis_results) > 0:
                        extracted_count = len(page_analysis_results[0].get("extracted_fields", {}))
                    progress_tracker.field_extraction_complete(extracted_count=extracted_count)

                # Build page classifications with error handling
                page_classifications = []
                for pr in page_analysis_results:
                    if "classification" in pr:
                        page_classifications.append({
                            "page_number": pr["page_number"],
                            **pr["classification"]
                        })
                    elif "error" in pr:
                        logger.warning(f"Page {pr.get('page_number', 'unknown')} analysis failed: {pr['error']}")
                        # Include page with error info
                        page_classifications.append({
                            "page_number": pr.get("page_number", "unknown"),
                            "error": pr["error"]
                        })

                # Convert PDF to images for display
                preview_images = []
                if file_type == "application/pdf":
                    pdf_result = convert_pdf_to_images_opencv(temp_file_path)
                    if pdf_result["type"] == "image":
                        preview_images = pdf_result["data"]
                    elif pdf_result["type"] == "error":
                        logger.error(f"Failed to convert PDF to images: {pdf_result.get('error', 'Unknown error')}")
                else:
                    # For images, encode as base64
                    encoded_image = encode_image_to_base64(temp_file_path)
                    if encoded_image:
                        preview_images = [encoded_image]
                    else:
                        logger.error(f"Failed to encode image to base64: {file_name}")

                # Calculate total processing time
                total_time = time.time() - start_time

                result = {
                    "file_name": file_name,
                    "document_type": document_type,
                    "confidence": confidence,
                    "preview_images": preview_images,
                    "page_classifications": page_classifications,
                    "compliance": {
                        "unified": combined_unified_result
                    },
                    "analysis_result": {
                        "per_page": page_analysis_results
                    },
                    "processing_time": {
                        "total": f"{total_time:.1f}",
                        "classification": f"{classification_time:.1f}",
                        "ocr": f"{ocr_time:.1f}",
                        "llm_analysis": f"{llm_time:.1f}"
                    }
                }

                # Check compliance if requested
                issues_found = 0
                if check_compliance and document_type != "Unknown":
                    # Progress: Start compliance check
                    if progress_tracker:
                        progress_tracker.start_compliance_check()

                    # Get extracted fields from first page for compliance check
                    extracted_fields_for_compliance = {}
                    if page_analysis_results and len(page_analysis_results) > 0:
                        extracted_fields_for_compliance = page_analysis_results[0].get("extracted_fields", {})

                    compliance_result = check_document_compliance(
                        document_type,
                        extracted_fields_for_compliance,
                        " ".join([entry["text"] for entry in text_data])
                    )
                    result["compliance"] = compliance_result

                    # Progress: Compliance complete
                    if progress_tracker:
                        # Count issues from compliance result
                        if compliance_result and isinstance(compliance_result, dict):
                            if "issues" in compliance_result:
                                issues_found = len(compliance_result["issues"])
                        progress_tracker.compliance_complete(issues_found=issues_found)

                # Progress: Finalize
                if progress_tracker:
                    # Count total extracted fields from first page
                    fields_count = 0
                    if page_analysis_results and len(page_analysis_results) > 0:
                        fields_count = len(page_analysis_results[0].get("extracted_fields", {}))

                    progress_tracker.finalize()
                    progress_tracker.complete_with_summary(
                        doc_type=document_type,
                        fields_extracted=fields_count,
                        compliance_status="Passed" if check_compliance and issues_found == 0 else ("Issues Found" if check_compliance else "Not Checked")
                    )

                return result

            finally:
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)

        except Exception as e:
            logger.error(f"Error processing file {file_name}: {str(e)}")

            # Progress: Error
            if progress_tracker:
                progress_tracker.error(str(e), {'file_name': file_name})

            return {
                "file_name": file_name,
                "error": str(e)
            }

    def handle_zip_file_classification(zip_file, check_compliance=True, progress_tracker=None):
        """Handle zip file containing multiple documents"""
        results = []

        with tempfile.NamedTemporaryFile(delete=False) as temp_zip:
            temp_zip_path = temp_zip.name
            zip_file.save(temp_zip_path)

        try:
            with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
                for file_info in zip_ref.namelist():
                    if file_info.endswith(('.pdf', '.jpg', '.jpeg', '.png')):
                        with zip_ref.open(file_info) as file_in_zip:
                            # Create a file-like object
                            file_content = file_in_zip.read()
                            file_obj = BytesIO(file_content)

                            # Determine content type
                            if file_info.lower().endswith('.pdf'):
                                content_type = 'application/pdf'
                            elif file_info.lower().endswith(('.jpg', '.jpeg')):
                                content_type = 'image/jpeg'
                            else:
                                content_type = 'image/png'

                            # Create a werkzeug FileStorage object
                            from werkzeug.datastructures import FileStorage
                            file_storage = FileStorage(
                                stream=file_obj,
                                filename=file_info,
                                content_type=content_type
                            )

                            # Process the file
                            result = classify_and_check_compliance(
                                file_storage,
                                check_compliance=check_compliance,
                                progress_tracker=progress_tracker
                            )
                            results.append(result)

        finally:
            if os.path.exists(temp_zip_path):
                os.remove(temp_zip_path)

        return results

    def check_document_compliance(document_type, extracted_fields, full_text):
        """Check document compliance based on type and content"""
        try:
            # Load compliance rules based on document type
            compliance_rules = load_compliance_rules(document_type)

            violations = []
            warnings = []
            passed_checks = []

            # Check each compliance rule
            for rule in compliance_rules:
                rule_id = rule.get("id", "")
                rule_desc = rule.get("description", "")
                field_name = rule.get("field", "")
                condition = rule.get("condition", "")

                if field_name in extracted_fields:
                    field_value = extracted_fields[field_name]

                    # Evaluate condition
                    if evaluate_compliance_condition(field_value, condition, extracted_fields):
                        passed_checks.append({
                            "rule_id": rule_id,
                            "description": rule_desc,
                            "status": "passed"
                        })
                    else:
                        violations.append({
                            "rule_id": rule_id,
                            "description": rule_desc,
                            "field": field_name,
                            "value": field_value,
                            "expected": condition,
                            "severity": rule.get("severity", "medium")
                        })

            # Additional checks based on document type
            if document_type.lower() == "letter of credit":
                lc_compliance = check_lc_specific_compliance(extracted_fields, full_text)
                violations.extend(lc_compliance.get("violations", []))
                warnings.extend(lc_compliance.get("warnings", []))

            return {
                "status": "compliant" if not violations else "non-compliant",
                "violations": violations,
                "warnings": warnings,
                "passed_checks": passed_checks,
                "total_checks": len(compliance_rules),
                "compliance_score": (len(passed_checks) / len(compliance_rules) * 100) if compliance_rules else 100
            }

        except Exception as e:
            logger.error(f"Error checking compliance: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }

    def load_compliance_rules(document_type):
        """Load compliance rules for a specific document type"""
        try:
            # Map document types to rule files
            rule_files = {
                "letter of credit": "ucp600_rules.json",
                "bank guarantee": "urdg758_custom_rules.json",
                "bill of lading": "custom_combined_rules.json",
                "invoice": "compliance_rules.json"
            }

            rule_file = rule_files.get(document_type.lower(), "compliance_rules.json")
            rule_path = os.path.join(app.root_path, "prompts", rule_file)

            if os.path.exists(rule_path):
                with open(rule_path, 'r') as f:
                    rules = json.load(f)
                    return rules.get("rules", [])

            return []

        except Exception as e:
            logger.error(f"Error loading compliance rules: {str(e)}")
            return []

    def evaluate_compliance_condition(field_value, condition, all_fields):
        """Evaluate a compliance condition against a field value"""
        try:
            # Simple condition evaluation
            if "required" in condition.lower():
                return bool(field_value and str(field_value).strip())

            if "date" in condition.lower() and "after" in condition.lower():
                # Date comparison logic
                return True  # Simplified for now

            if "amount" in condition.lower():
                # Amount validation logic
                return True  # Simplified for now

            return True

        except Exception as e:
            logger.error(f"Error evaluating condition: {str(e)}")
            return False

    def check_lc_specific_compliance(fields, full_text):
        """Check Letter of Credit specific compliance rules"""
        violations = []
        warnings = []

        # Check for required LC fields
        required_fields = [
            "lc_number", "applicant", "beneficiary",
            "amount", "currency", "expiry_date"
        ]

        for field in required_fields:
            if field not in fields or not fields[field]:
                violations.append({
                    "rule_id": f"LC_{field.upper()}_REQUIRED",
                    "description": f"{field.replace('_', ' ').title()} is required",
                    "field": field,
                    "severity": "high"
                })

        # Check for SWIFT code format
        if "swift_code" in fields and fields["swift_code"]:
            swift = fields["swift_code"]
            if not re.match(r'^[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?$', swift):
                warnings.append({
                    "rule_id": "LC_SWIFT_FORMAT",
                    "description": "SWIFT code format appears incorrect",
                    "field": "swift_code",
                    "value": swift
                })

        return {"violations": violations, "warnings": warnings}

    def extract_fields_from_page(page_data, field_definitions, document_type, page_num):
        """Extract fields from a page using LLM"""
        try:
            # Format OCR data for prompt
            ocr_text = format_ocr_data_for_llm_prompt(page_data)

            # Create extraction prompt
            prompt = f"""
            Extract the following fields from this {document_type} document (Page {page_num}):

            Fields to extract:
            {json.dumps(field_definitions, indent=2)}

            OCR Text:
            {ocr_text}

            Return a JSON object with the extracted field values.
            """

            # Call LLM
            response = openai.ChatCompletion.create(
                engine=deployment_name,
                messages=[
                    {"role": "system", "content": "You are a document field extraction assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,
                max_tokens=1000,
                seed=12345,  # ✅ Reproducibility
                top_p=0.1,  # ✅ NOT 1.0 (reduces randomness)
                frequency_penalty=0,
                presence_penalty=0,
                response_format={"type": "json_object"}
            )

            # Parse response
            result = parse_json_from_llm_response(response["choices"][0]["message"]["content"])
            return result or {}

        except Exception as e:
            logger.error(f"Error extracting fields from page: {str(e)}")
            return {}

def organize_ocr_data_by_page(text_data):
    """Organize OCR text data by page number"""
    from collections import defaultdict
    pages = defaultdict(list)
    for entry in text_data:
        page = entry.get("bounding_page", 1)
        pages[page].append(entry)
    return [pages[k] for k in sorted(pages)]

def generate_detailed_compliance_report(validation_results: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a detailed compliance report"""

    report = {
        'report_id': str(uuid.uuid4()),
        'generated_at': datetime.now().isoformat(),
        'executive_summary': {},
        'detailed_findings': {},
        'recommendations': [],
        'compliance_matrix': {},
        'risk_assessment': {}
    }

    # Executive summary
    compliance_score = validation_results.get('compliance_score', 0)
    total_checks = validation_results.get('total_checks', 0)
    critical_issues = len(validation_results.get('critical_issues', []))

    report['executive_summary'] = {
        'overall_compliance_score': compliance_score,
        'total_validation_checks': total_checks,
        'critical_issues_count': critical_issues,
        'warning_count': validation_results.get('warnings', 0),
        'compliance_status': 'PASS' if compliance_score >= 80 else 'FAIL',
        'risk_level': 'HIGH' if critical_issues > 3 else 'MEDIUM' if critical_issues > 0 else 'LOW'
    }

    # Detailed findings by document type
    for doc_type, doc_result in validation_results.get('detailed_results', {}).items():
        report['detailed_findings'][doc_type] = {
            'compliance_score': (doc_result['passed_checks'] / max(doc_result['total_checks'], 1)) * 100,
            'critical_issues': doc_result.get('critical_issues', []),
            'warnings': doc_result.get('warnings_list', []),
            'field_validations': doc_result.get('field_validations', {})
        }

    # Risk assessment
    report['risk_assessment'] = {
        'financial_risk': 'HIGH' if any(
            'amount' in issue.get('field', '') for issue in validation_results.get('critical_issues', [])) else 'LOW',
        'operational_risk': 'HIGH' if any(
            'date' in issue.get('field', '') for issue in validation_results.get('critical_issues', [])) else 'LOW',
        'compliance_risk': 'HIGH' if compliance_score < 70 else 'MEDIUM' if compliance_score < 90 else 'LOW'
    }

    return report


def get_user_compliance_history(user_id: str, limit: int) -> List[Dict[str, Any]]:
    """Get compliance check history for user (mock implementation)"""
    # This would typically query a database
    # For now, return mock data
    return [
        {
            'id': str(uuid.uuid4()),
            'timestamp': (datetime.now() - timedelta(days=i)).isoformat(),
            'swift_message_type': f'MT70{i}',
            'document_count': 3 + i,
            'compliance_score': 85 + (i * 2),
            'status': 'PASS' if (85 + (i * 2)) >= 80 else 'FAIL'
        }
        for i in range(limit)
    ]


def generate_pdf_report(report_data: Dict[str, Any]) -> bytes:
    """Generate PDF compliance report"""
    # Mock PDF generation - replace with actual PDF library like reportlab
    pdf_content = f"""
    COMPLIANCE REPORT
    Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

    Executive Summary:
    - Overall Compliance Score: {report_data.get('executive_summary', {}).get('overall_compliance_score', 0)}%
    - Total Validation Checks: {report_data.get('executive_summary', {}).get('total_validation_checks', 0)}
    - Critical Issues: {report_data.get('executive_summary', {}).get('critical_issues_count', 0)}
    - Risk Level: {report_data.get('executive_summary', {}).get('risk_level', 'UNKNOWN')}

    Detailed Findings:
    {json.dumps(report_data.get('detailed_findings', {}), indent=2)}
    """

    return pdf_content.encode('utf-8')


def generate_excel_report(report_data: Dict[str, Any]) -> bytes:
    """Generate Excel compliance report"""
    # Mock Excel generation - replace with actual Excel library like openpyxl
    import io
    output = io.BytesIO()

    # Create mock Excel content
    excel_content = f"""Compliance Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Summary:
Score: {report_data.get('executive_summary', {}).get('overall_compliance_score', 0)}%
Checks: {report_data.get('executive_summary', {}).get('total_validation_checks', 0)}
Issues: {report_data.get('executive_summary', {}).get('critical_issues_count', 0)}
"""

    output.write(excel_content.encode('utf-8'))
    output.seek(0)
    return output.read()


def generate_csv_report(report_data: Dict[str, Any]) -> str:
    """Generate CSV compliance report"""
    import csv
    import io

    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow(['Metric', 'Value'])

    # Write executive summary
    exec_summary = report_data.get('executive_summary', {})
    writer.writerow(['Overall Compliance Score', f"{exec_summary.get('overall_compliance_score', 0)}%"])
    writer.writerow(['Total Validation Checks', exec_summary.get('total_validation_checks', 0)])
    writer.writerow(['Critical Issues Count', exec_summary.get('critical_issues_count', 0)])
    writer.writerow(['Risk Level', exec_summary.get('risk_level', 'UNKNOWN')])

    # Write detailed findings
    writer.writerow(['', ''])  # Empty row
    writer.writerow(['Document Type', 'Compliance Score', 'Critical Issues', 'Warnings'])

    for doc_type, findings in report_data.get('detailed_findings', {}).items():
        writer.writerow([
            doc_type,
            f"{findings.get('compliance_score', 0):.1f}%",
            len(findings.get('critical_issues', [])),
            len(findings.get('warnings', []))
        ])

    return output.getvalue()

    @app.route('/api/trade-documents', methods=['GET'])
    # NOTE: /api/trade-documents route removed - deprecated functionality

    @app.route('/api/trade-documents/<document_code>/fields', methods=['GET'])
    @login_required
    @timing_aspect
    def get_document_fields_api(document_code):
        """Get required fields for a specific document type"""
        try:
            doc_info = get_document_info_by_code(document_code)
            if not doc_info:
                return jsonify({
                    'success': False,
                    'message': f'Document type {document_code} not found'
                }), 404

            fields = get_required_fields_for_document(document_code)

            return jsonify({
                'success': True,
                'document': doc_info,
                'fields': fields,
                'statistics': {
                    'mandatory': len(fields['mandatory']),
                    'optional': len(fields['optional']),
                    'conditional': len(fields['conditional']),
                    'total': len(fields['mandatory']) + len(fields['optional']) + len(fields['conditional'])
                }
            }), 200

        except Exception as e:
            logger.error(f"Error getting document fields: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/custom_functions', methods=['GET'])
@timing_aspect
def get_all_custom_functions():
    """Get all custom functions"""
    try:
        functions_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'custom_functions.json')

        if os.path.exists(functions_file):
            with open(functions_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {'functions': []}

        functions = data.get('functions', [])

        # Optional filters
        category = request.args.get('category')
        active_only = request.args.get('active', 'false').lower() == 'true'

        if category:
            functions = [f for f in functions if f.get('category') == category]

        if active_only:
            functions = [f for f in functions if f.get('isActive', True)]

        return jsonify({'success': True, 'functions': functions}), 200
    except Exception as e:
        logger.error(f"Error getting custom functions: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/custom_functions/<function_id>', methods=['GET'])
@timing_aspect
def get_custom_function(function_id):
    """Get a single custom function by ID"""
    try:
        functions_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'custom_functions.json')

        if os.path.exists(functions_file):
            with open(functions_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                functions = data.get('functions', [])
                function = next((f for f in functions if f.get('id') == function_id), None)

                if function:
                    return jsonify({'success': True, 'function': function}), 200
                else:
                    return jsonify({'success': False, 'message': 'Function not found'}), 404
        else:
            return jsonify({'success': False, 'message': 'No functions found'}), 404

    except Exception as e:
        logger.error(f"Error getting custom function {function_id}: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

def secure_filename(filename):
    """Make filename secure for storage"""
    import re
    # Remove any directory path
    filename = os.path.basename(filename)
    # Replace spaces and special characters
    filename = re.sub(r'[^\w\-_\.]', '_', filename)
    # Remove multiple underscores
    filename = re.sub(r'_+', '_', filename)
    return filename

def analyze_document_requirement_discrepancies(lc_data, swift_data, document_data):
    """Analyze document requirements vs submitted documents"""
    discrepancies = []

    # Enhanced document requirements analysis would include:
    # - Required vs submitted documents
    # - Document format requirements
    # - Copy requirements (originals vs copies)
    # - Specific document content requirements

    return discrepancies

def analyze_enhanced_compliance_discrepancies(lc_data, swift_data, document_data):
    """Enhanced compliance analysis for UCP 600, URDG 758, and regulatory requirements"""
    discrepancies = []

    # Enhanced compliance analysis would include:
    # - UCP 600 article compliance
    # - URDG 758 compliance (for guarantees)
    # - Country-specific regulatory requirements
    # - Industry-specific compliance rules

    return discrepancies


def analyze_missing_mandatory_fields(lc_data, swift_data):
    """Enhanced analysis of missing mandatory fields with comprehensive coverage"""
    missing_fields = []

    # COMPREHENSIVE mandatory fields for trade finance
    mandatory_checks = [
        # Critical Core Fields
        ('applicant', '50', 'Applicant Name', 'LC Application Form', 'CRITICAL'),
        ('applicant_address', '50', 'Applicant Address', 'LC Application Form', 'HIGH'),
        ('beneficiary', '59', 'Beneficiary Name', 'LC Application Form', 'CRITICAL'),
        ('beneficiary_address', '59', 'Beneficiary Address', 'LC Application Form', 'HIGH'),
        ('amount', '32B', 'LC Amount', 'LC Application Form', 'CRITICAL'),
        ('currency', '32B', 'Currency', 'LC Application Form', 'CRITICAL'),
        ('lc_number', '20', 'LC Number', 'SWIFT MT700', 'CRITICAL'),

        # Important Date Fields
        ('issue_date', '31C', 'Issue Date', 'LC Application Form', 'HIGH'),
        ('expiry_date', '31D', 'Expiry Date', 'LC Application Form', 'CRITICAL'),
        ('latest_shipment_date', '44C', 'Latest Shipment Date', 'LC Application Form', 'HIGH'),

        # Banking Information
        ('issuing_bank', '51A', 'Issuing Bank', 'LC Application Form', 'CRITICAL'),
        ('advising_bank', '53A', 'Advising Bank', 'LC Application Form', 'HIGH'),

        # Trade Details
        ('goods_description', '45A', 'Description of Goods', 'LC Application Form', 'CRITICAL'),
        ('port_of_loading', '44E', 'Port of Loading', 'LC Application Form', 'HIGH'),
        ('port_of_discharge', '44F', 'Port of Discharge', 'LC Application Form', 'HIGH'),
        ('incoterms', '45A', 'Incoterms', 'LC Application Form', 'HIGH'),

        # Document Requirements
        ('documents_required', '46A', 'Documents Required', 'LC Application Form', 'HIGH'),
        ('payment_terms', '42C', 'Payment Terms', 'LC Application Form', 'HIGH'),

        # Optional but Important
        ('partial_shipment', '43P', 'Partial Shipment Allowed', 'LC Application Form', 'MEDIUM'),
        ('transhipment', '43T', 'Transhipment Allowed', 'LC Application Form', 'MEDIUM'),
        ('charges', '71B', 'Charges', 'LC Application Form', 'MEDIUM'),

        # Commercial References
        ('purchase_order', '45A', 'Purchase Order Number', 'Commercial Documents', 'MEDIUM'),
        ('contract_number', '45A', 'Contract Number', 'Commercial Documents', 'MEDIUM')
    ]

    logger.info(f"🔍 Analyzing {len(mandatory_checks)} mandatory field requirements")

    for lc_field, swift_field, display_name, document, severity in mandatory_checks:
        lc_value = extract_field_value(lc_data, lc_field)
        swift_value = extract_field_value(swift_data, swift_field)

        # Enhanced missing field logic
        if not lc_value and not swift_value:
            # Completely missing field
            missing_fields.append({
                'field': display_name,
                'document_name': document,
                'expected_value': get_expected_field_format(lc_field),
                'observed_value': 'Not provided',
                'issue': f'{display_name} is mandatory but completely missing from all documents',
                'severity': severity,
                'recommendation': generate_missing_field_recommendation(display_name, lc_field, document),
                'business_impact': assess_missing_field_impact(lc_field, severity),
                'category': 'missing_field',
                'confidence': 1.0,
                'swift_reference': swift_field
            })

        elif not lc_value and swift_value:
            # Missing from LC but present in SWIFT
            missing_fields.append({
                'field': display_name,
                'document_name': document,
                'expected_value': f'Should match SWIFT: "{swift_value}"',
                'observed_value': 'Missing from LC application',
                'issue': f'{display_name} is specified in SWIFT MT700 but missing from LC application',
                'severity': 'HIGH' if severity == 'CRITICAL' else severity,
                'recommendation': f'Add {display_name} to LC application form to match SWIFT MT700 field {swift_field}',
                'business_impact': 'High: Inconsistency between LC application and SWIFT may cause processing delays',
                'category': 'missing_field',
                'confidence': 0.95,
                'swift_reference': swift_field
            })

        elif lc_value and not swift_value and severity in ['CRITICAL', 'HIGH']:
            # Present in LC but missing from SWIFT (for important fields)
            missing_fields.append({
                'field': display_name,
                'document_name': 'SWIFT MT700',
                'expected_value': f'Should include: "{lc_value}"',
                'observed_value': 'Missing from SWIFT message',
                'issue': f'{display_name} is in LC application but not reflected in SWIFT MT700',
                'severity': 'MEDIUM',
                'recommendation': f'Ensure {display_name} from LC application is included in SWIFT MT700 field {swift_field}',
                'business_impact': 'Medium: SWIFT message should reflect all LC application details',
                'category': 'missing_field',
                'confidence': 0.85,
                'swift_reference': swift_field
            })

    # Check for missing supporting documents
    document_missing_fields = analyze_missing_document_fields(lc_data, swift_data)
    missing_fields.extend(document_missing_fields)

    logger.info(f"✅ Missing field analysis complete: {len(missing_fields)} missing fields found")
    return missing_fields


def get_expected_field_format(field_name):
    """Get expected format description for missing fields"""
    format_descriptions = {
        'applicant': 'Company name and full address',
        'beneficiary': 'Company name and full address',
        'amount': 'Numeric amount (e.g., 100000.00)',
        'currency': 'ISO currency code (e.g., USD, EUR)',
        'lc_number': 'Unique LC reference number',
        'issue_date': 'Date in YYYY-MM-DD format',
        'expiry_date': 'Date in YYYY-MM-DD format',
        'goods_description': 'Detailed description of goods/services',
        'issuing_bank': 'Bank name and SWIFT code',
        'port_of_loading': 'Port or place name',
        'port_of_discharge': 'Port or place name',
        'incoterms': 'Standard Incoterm (e.g., FOB, CIF, CFR)',
        'payment_terms': 'Payment instruction (e.g., at sight, 90 days)',
        'documents_required': 'List of required documents'
    }

    return format_descriptions.get(field_name, 'Required field value')


def generate_missing_field_recommendation(display_name, field_name, document):
    """Generate specific recommendations for missing fields"""
    if field_name in ['applicant', 'beneficiary']:
        return f"Provide complete {display_name} including company name, address, and contact details as required for LC processing"
    elif field_name == 'amount':
        return f"Specify exact LC amount in numbers. This is critical for payment processing"
    elif field_name == 'currency':
        return f"Specify currency using standard ISO codes (USD, EUR, GBP, etc.)"
    elif 'date' in field_name:
        return f"Provide {display_name} in clear date format. Ensure compliance with UCP 600 requirements"
    elif field_name == 'goods_description':
        return f"Provide detailed description of goods/services. Must match commercial invoice and other documents"
    elif field_name in ['issuing_bank', 'advising_bank']:
        return f"Provide complete {display_name} name and SWIFT BIC code for proper routing"
    else:
        return f"Complete {display_name} field in {document} - this information is required for LC processing"


def assess_missing_field_impact(field_name, severity):
    """Assess business impact of missing fields"""
    impact_descriptions = {
        'CRITICAL': {
            'applicant': 'Critical: LC cannot be issued without complete applicant information',
            'beneficiary': 'Critical: Documents cannot be presented without correct beneficiary details',
            'amount': 'Critical: LC amount is mandatory for all LC transactions',
            'currency': 'Critical: Currency must be specified for payment processing',
            'lc_number': 'Critical: LC number is required for all references and amendments',
            'expiry_date': 'Critical: LC must have clear expiry date per UCP 600',
            'issuing_bank': 'Critical: Issuing bank details required for LC validity',
            'goods_description': 'Critical: Goods description required for customs and document examination',
            'default': 'Critical: This field is mandatory for LC processing and cannot be omitted'
        },
        'HIGH': {
            'issue_date': 'High: Issue date affects document presentation timeline',
            'latest_shipment_date': 'High: Missing shipment date may cause shipping delays',
            'port_of_loading': 'High: Loading port must be specified for shipping documents',
            'port_of_discharge': 'High: Discharge port required for bill of lading',
            'advising_bank': 'High: Advising bank details needed for document handling',
            'documents_required': 'High: Document requirements must be clearly specified',
            'payment_terms': 'High: Payment terms affect when and how payment is made',
            'incoterms': 'High: Incoterms determine shipping and insurance responsibilities',
            'default': 'High: Missing field may cause processing delays and require clarification'
        },
        'MEDIUM': {
            'default': 'Medium: Field should be provided but may not prevent LC processing'
        }
    }

    severity_impacts = impact_descriptions.get(severity, impact_descriptions['MEDIUM'])
    return severity_impacts.get(field_name, severity_impacts['default'])

def analyze_missing_document_fields(lc_data, swift_data):
    """Analyze missing fields specific to document requirements"""
    missing_doc_fields = []

    # Check if required documents are specified
    documents_required = swift_data.get('46A', '') or lc_data.get('documents_required', '')

    if not documents_required:
        missing_doc_fields.append({
            'field': 'Required Documents List',
            'document_name': 'LC Application Form',
            'expected_value': 'List of documents required for negotiation (e.g., Commercial Invoice, Bill of Lading, etc.)',
            'observed_value': 'Not specified',
            'issue': 'No document requirements specified - this is mandatory for LC processing',
            'severity': 'HIGH',
            'recommendation': 'Specify all required documents according to trade terms and regulatory requirements',
            'business_impact': 'High: Beneficiary will not know which documents to present for negotiation',
            'category': 'missing_field',
            'confidence': 1.0,
            'swift_reference': '46A'
        })

    return missing_doc_fields

def categorize_discrepancies_for_tabs(discrepancy_results):
    """Categorize discrepancies for the 4-tab system with clean structure"""
    try:
        # Group discrepancies by their tab categories
        categorized = {
            'inconsistency_discrepancy': [],
            'missing_fields': [],
            'compliance_issues': [],
            'document_issues': []
        }

        for discrepancy in discrepancy_results:
            tab_category = discrepancy.get('tab_category', 'inconsistency_discrepancy')
            category = discrepancy.get('category', 'general')

            # Enhanced discrepancy structure for Professional UI
            enhanced_discrepancy = {
                'field': discrepancy.get('field', 'Unknown Field'),
                'source_document': discrepancy.get('source_document',
                                                   discrepancy.get('document_name', 'Unknown Document')),
                'target_document': discrepancy.get('target_document', 'Target Document'),
                'source_value': discrepancy.get('source_value', discrepancy.get('observed_value', 'Not provided')),
                'target_value': discrepancy.get('target_value', discrepancy.get('expected_value', 'Not specified')),
                'required_value': discrepancy.get('required_value', discrepancy.get('expected_value', 'Not specified')),
                'issue': discrepancy.get('issue', discrepancy.get('description', 'No description')),
                'severity': discrepancy.get('severity', 'MEDIUM').upper(),
                'recommendation': discrepancy.get('recommendation',
                                                  generate_recommendation_for_discrepancy(discrepancy)),
                'business_impact': discrepancy.get('business_impact', assess_business_impact(discrepancy)),
                'confidence': discrepancy.get('confidence', 0.8),
                'swift_reference': discrepancy.get('swift_reference',
                                                   get_swift_reference_for_field(discrepancy.get('field', ''))),
                'category': category
            }

            # Assign to appropriate tab based on category
            if category in ['missing_field']:
                categorized['missing_fields'].append(enhanced_discrepancy)
            elif category in ['best_practice', 'ucp_compliance', 'regulatory']:
                categorized['compliance_issues'].append(enhanced_discrepancy)
            elif category in ['extra_document', 'insufficient_copies', 'document_missing']:
                categorized['document_issues'].append(enhanced_discrepancy)
            else:
                categorized['inconsistency_discrepancy'].append(enhanced_discrepancy)

        # Return flat list for backward compatibility but preserve tab info
        all_categorized = []
        for tab, items in categorized.items():
            for item in items:
                item['tab_category'] = tab
                all_categorized.append(item)

        return all_categorized

    except Exception as e:
        logger.error(f"Error categorizing discrepancies: {e}")
        return discrepancy_results


def categorize_discrepancies_for_tabs_enhanced(discrepancy_results, xml_rules, uploaded_documents, lc_context):
    """Enhanced categorization with XML rule integration and smarter tab assignment"""
    try:
        # Group discrepancies by their tab categories with enhanced logic
        categorized = {
            'inconsistency_discrepancy': [],
            'missing_fields': [],
            'compliance_issues': [],
            'document_issues': []
        }

        for discrepancy in discrepancy_results:
            category = discrepancy.get('category', 'general')

            # Enhanced discrepancy structure for Professional UI with XML rule support
            enhanced_discrepancy = {
                'field': discrepancy.get('field', 'Unknown Field'),
                'source_document': discrepancy.get('source_document',
                                                   discrepancy.get('document_name', 'Unknown Document')),
                'target_document': discrepancy.get('target_document', 'Target Document'),
                'source_value': discrepancy.get('source_value', discrepancy.get('observed_value', 'Not provided')),
                'target_value': discrepancy.get('target_value', discrepancy.get('expected_value', 'Not specified')),
                'required_value': discrepancy.get('required_value', discrepancy.get('expected_value', 'Not specified')),
                'issue': discrepancy.get('issue', discrepancy.get('description', 'No description')),
                'severity': discrepancy.get('severity', 'MEDIUM').upper(),
                'recommendation': discrepancy.get('recommendation',
                                                  generate_recommendation_for_discrepancy(discrepancy)),
                'business_impact': discrepancy.get('business_impact', assess_business_impact(discrepancy)),
                'confidence': discrepancy.get('confidence', 0.8),
                'swift_reference': discrepancy.get('swift_reference',
                                                   get_swift_reference_for_field(discrepancy.get('field', ''))),
                'category': category,
                'rule_based': discrepancy.get('rule_based', False),
                'xml_rule_id': discrepancy.get('xml_rule_id'),
                'rule_code': discrepancy.get('rule_code'),
                'regulatory_basis': discrepancy.get('basis', ''),
                'field_type': determine_field_type(discrepancy.get('field', ''))
            }

            # Enhanced tab assignment logic with XML rule support
            tab_category = determine_enhanced_tab_category(enhanced_discrepancy, xml_rules)
            enhanced_discrepancy['tab_category'] = tab_category
            categorized[tab_category].append(enhanced_discrepancy)

        # Return flat list for backward compatibility but preserve tab info
        all_categorized = []
        for tab, items in categorized.items():
            for item in items:
                all_categorized.append(item)

        return all_categorized

    except Exception as e:
        logger.error(f"Error in enhanced categorization: {e}")
        return categorize_discrepancies_for_tabs(discrepancy_results)  # Fallback to basic

def determine_enhanced_tab_category(discrepancy, xml_rules):
    """Determine the most appropriate tab category using enhanced logic"""
    try:
        category = discrepancy.get('category', 'general')
        field = discrepancy.get('field', '').lower()
        issue = discrepancy.get('issue', '').lower()
        rule_based = discrepancy.get('rule_based', False)

        # Rule-based priority assignment
        if rule_based and discrepancy.get('regulatory_basis'):
            basis = discrepancy.get('regulatory_basis', '').lower()
            if any(term in basis for term in ['ucp', 'isbp', 'regulatory', 'law']):
                return 'compliance_issues'

        # Missing field detection
        if any(term in issue for term in ['missing', 'not found', 'absent', 'lacking']):
            return 'missing_fields'

        # Document-level issues
        if any(term in issue for term in ['document', 'copy', 'original', 'duplicate']):
            return 'document_issues'

        # Compliance-related terms
        if any(term in issue for term in ['comply', 'regulation', 'standard', 'requirement', 'mandate']):
            return 'compliance_issues'

        # Field-level inconsistencies (default)
        return 'inconsistency_discrepancy'

    except Exception as e:
        logger.error(f"Error determining tab category: {e}")
        return 'inconsistency_discrepancy'

def determine_field_type(field_name):
    """Determine the type of field for better categorization"""
    field_lower = field_name.lower()

    if any(term in field_lower for term in ['date', 'time', 'expiry', 'issue']):
        return 'date'
    elif any(term in field_lower for term in ['amount', 'value', 'price', 'cost']):
        return 'monetary'
    elif any(term in field_lower for term in ['description', 'goods', 'product']):
        return 'descriptive'
    elif any(term in field_lower for term in ['port', 'destination', 'loading', 'discharge']):
        return 'location'
    elif any(term in field_lower for term in ['applicant', 'beneficiary', 'consignee', 'name']):
        return 'party'
    elif any(term in field_lower for term in ['reference', 'number', 'id']):
        return 'identifier'
    else:
        return 'general'

def get_rule_coverage_by_document(uploaded_documents, xml_rules):
    """Calculate rule coverage percentage for each document type"""
    coverage = {}

    for doc in uploaded_documents:
        doc_type = doc.get('document_type', doc.get('classification', 'Unknown')).strip()
        if doc_type not in coverage:
            relevant_rules = [rule for rule in xml_rules if rule.get('documentType', '').lower() == doc_type.lower()]
            total_rules = len(relevant_rules)
            mandatory_rules = len([rule for rule in relevant_rules if rule.get('priority') == 'Mandatory'])

            coverage[doc_type] = {
                'total_rules': total_rules,
                'mandatory_rules': mandatory_rules,
                'advisory_rules': total_rules - mandatory_rules,
                'coverage_percentage': min(100.0, (total_rules / 10.0) * 100) if total_rules > 0 else 0
            }

    return coverage

def get_top_violated_rules(rule_based_discrepancies):
    """Get the most frequently violated XML rules"""
    rule_violations = {}

    for discrepancy in rule_based_discrepancies:
        rule_code = discrepancy.get('rule_code')
        if rule_code:
            if rule_code not in rule_violations:
                rule_violations[rule_code] = {
                    'count': 0,
                    'severity': discrepancy.get('severity', 'MEDIUM'),
                    'description': discrepancy.get('issue', ''),
                    'basis': discrepancy.get('regulatory_basis', '')
                }
            rule_violations[rule_code]['count'] += 1

    # Sort by violation count and return top 5
    sorted_violations = sorted(rule_violations.items(), key=lambda x: x[1]['count'], reverse=True)
    return dict(sorted_violations[:5])

def calculate_compliance_score(discrepancies):
    """Calculate overall compliance score based on discrepancies"""
    if not discrepancies:
        return 100.0

    total_weight = 0
    penalty_weight = 0

    for discrepancy in discrepancies:
        severity = discrepancy.get('severity', 'MEDIUM').upper()
        rule_based = discrepancy.get('rule_based', False)

        # Weight based on severity and source
        if severity == 'HIGH':
            weight = 3
        elif severity == 'MEDIUM':
            weight = 2
        else:
            weight = 1

        # Add extra weight for rule-based discrepancies
        if rule_based:
            weight *= 1.5

        total_weight += weight
        penalty_weight += weight

    # Calculate score (higher penalties = lower score)
    if total_weight == 0:
        return 100.0

    # Base score calculation with logarithmic penalty scaling
    import math
    max_expected_weight = len(discrepancies) * 2  # Expected average weight
    penalty_ratio = min(1.0, penalty_weight / max_expected_weight)
    compliance_score = 100.0 * (1 - penalty_ratio)

    return max(0.0, min(100.0, compliance_score))

def get_swift_reference_for_field(field_name):
    """Map field names to SWIFT MT700 references"""
    field_mapping = {
        'lc_number': '20',
        'reference': '20',
        'amount': '32B',
        'currency': '32B',
        'issue_date': '31C',
        'expiry_date': '31D',
        'goods_description': '45A',
        'documents_required': '46A',
        'latest_shipment_date': '44C',
        'port_of_loading': '44E',
        'port_of_discharge': '44F',
        'additional_conditions': '47A'
    }

    field_lower = field_name.lower().replace(' ', '_')
    return field_mapping.get(field_lower, 'N/A')

def generate_recommendation_for_discrepancy(discrepancy):
    """Generate recommendation based on discrepancy type"""
    severity = discrepancy.get('severity', 'medium').upper()
    field = discrepancy.get('field', '')

    if severity == 'HIGH' or severity == 'CRITICAL':
        return f"Immediate attention required for {field}. Contact issuing bank for amendment."
    elif severity == 'MEDIUM':
        return f"Review {field} discrepancy. Consider requesting clarification or amendment."
    else:
        return f"Minor discrepancy in {field}. Monitor for compliance."

def assess_business_impact(discrepancy):
    """Assess business impact of discrepancy"""
    severity = discrepancy.get('severity', 'medium').upper()

    if severity == 'HIGH' or severity == 'CRITICAL':
        return "High risk of document rejection and payment delays"
    elif severity == 'MEDIUM':
        return "Moderate risk of processing delays"
    else:
        return "Low impact on transaction processing"

def categorize_discrepancy_type(discrepancy):
    """Categorize discrepancy type for analysis"""
    issue = discrepancy.get('issue', '').lower()
    field = discrepancy.get('field', '').lower()

    if 'missing' in issue or 'not provided' in issue:
        return 'missing_field'
    elif 'mismatch' in issue or 'different' in issue:
        return 'value_mismatch'
    elif 'date' in issue or 'expiry' in issue:
        return 'date_issue'
    else:
        return 'other'

def apply_xml_rule_to_document(rule, document, lc_context, swift_message):
    """Apply a single XML rule to a document and return discrepancy if found"""
    try:
        rule_code = rule.get('code', 'UNKNOWN')
        rule_description = rule.get('description', 'No description')
        rule_priority = rule.get('priority', 'Advisory')
        rule_basis = rule.get('basis', 'General')
        doc_type = rule.get('documentType', 'Unknown')

        # Extract document content and fields
        doc_content = document.get('content', '')
        extracted_fields = document.get('extracted_fields', {})
        doc_name = document.get('file_name', 'Unknown Document')

        # Apply rule-specific logic based on common trade finance discrepancy patterns
        discrepancy = None

        # Rule pattern matching - this is a simplified implementation
        # In production, this would be more sophisticated with NLP/ML
        rule_desc_lower = rule_description.lower()

        # Check for signature/authorization requirements
        if 'signed' in rule_desc_lower or 'authorized signatory' in rule_desc_lower:
            if not check_signature_in_document(doc_content, extracted_fields):
                discrepancy = create_rule_discrepancy(
                    rule, doc_name, 'signature_missing',
                    'Required signature or authorization not found',
                    rule_priority
                )

        # Check for reference number consistency
        elif 'reference' in rule_desc_lower and 'invoice' in rule_desc_lower:
            if not check_reference_consistency(extracted_fields, lc_context):
                discrepancy = create_rule_discrepancy(
                    rule, doc_name, 'reference_inconsistent',
                    'Document reference numbers are inconsistent with LC',
                    rule_priority
                )

        # Check for currency consistency
        elif 'currency must match' in rule_desc_lower:
            if not check_currency_consistency(extracted_fields, lc_context):
                discrepancy = create_rule_discrepancy(
                    rule, doc_name, 'currency_mismatch',
                    'Document currency does not match LC currency',
                    rule_priority
                )

        # Check for date requirements
        elif 'dated within' in rule_desc_lower or 'validity period' in rule_desc_lower:
            if not check_date_validity(extracted_fields, lc_context):
                discrepancy = create_rule_discrepancy(
                    rule, doc_name, 'date_invalid',
                    'Document date is outside LC validity period',
                    rule_priority
                )

        # Check for description matching
        elif 'description' in rule_desc_lower and 'match' in rule_desc_lower:
            if not check_description_consistency(extracted_fields, lc_context):
                discrepancy = create_rule_discrepancy(
                    rule, doc_name, 'description_mismatch',
                    'Goods description does not match LC requirements',
                    rule_priority
                )

        # Check for port/destination requirements
        elif 'port' in rule_desc_lower or 'destination' in rule_desc_lower:
            if not check_port_consistency(extracted_fields, lc_context):
                discrepancy = create_rule_discrepancy(
                    rule, doc_name, 'port_mismatch',
                    'Port information does not match LC requirements',
                    rule_priority
                )

        # Check for consignee requirements
        elif 'consignee' in rule_desc_lower:
            if not check_consignee_consistency(extracted_fields, lc_context):
                discrepancy = create_rule_discrepancy(
                    rule, doc_name, 'consignee_mismatch',
                    'Consignee information does not match LC terms',
                    rule_priority
                )

        # Check for insurance coverage
        elif 'insurance' in rule_desc_lower and '110%' in rule_desc_lower:
            if not check_insurance_coverage(extracted_fields, lc_context):
                discrepancy = create_rule_discrepancy(
                    rule, doc_name, 'insurance_insufficient',
                    'Insurance coverage less than required 110% of invoice value',
                    rule_priority
                )

        return discrepancy

    except Exception as e:
        logger.error(f"Error applying XML rule {rule.get('code', 'UNKNOWN')}: {e}")
        return None


def create_rule_discrepancy(rule, doc_name, discrepancy_type, description, priority):
    """Create a standardized discrepancy object from XML rule"""
    severity = 'HIGH' if priority == 'Mandatory' else 'MEDIUM'
    category = 'compliance' if priority == 'Mandatory' else 'advisory'

    return {
        'rule_code': rule.get('code', 'UNKNOWN'),
        'field': discrepancy_type.replace('_', ' ').title(),
        'source_document': doc_name,
        'target_document': 'LC Requirements',
        'source_value': 'Not compliant',
        'target_value': rule.get('description', 'Compliance required'),
        'issue': description,
        'severity': severity,
        'category': category,
        'basis': rule.get('basis', 'General'),
        'recommendation': f"Review document against {rule.get('basis', 'requirements')} - {rule.get('description', '')}",
        'business_impact': 'HIGH' if priority == 'Mandatory' else 'MEDIUM',
        'confidence': 0.7,  # Rule-based confidence
        'rule_based': True,
        'xml_rule_id': rule.get('id', 'unknown')
    }


# Helper functions for rule validation (simplified implementations)
def check_signature_in_document(content, fields):
    """Check if document contains signature or authorization"""
    content_lower = content.lower()
    return any(keyword in content_lower for keyword in ['signed', 'signature', 'authorized', 'signatory'])


def check_reference_consistency(fields, lc_context):
    """Check if document references are consistent with LC"""
    doc_ref = fields.get('reference', '').strip()
    lc_ref = lc_context.get('lcNumber', '').strip()
    return bool(doc_ref and lc_ref and doc_ref in lc_ref)


def check_currency_consistency(fields, lc_context):
    """Check if document currency matches LC currency"""
    doc_currency = fields.get('currency', '').strip().upper()
    lc_currency = lc_context.get('currency', lc_context.get('formData', {}).get('lcCurrency', '')).strip().upper()
    return bool(doc_currency and lc_currency and doc_currency == lc_currency)


def check_date_validity(fields, lc_context):
    """Check if document dates are within LC validity"""
    # Simplified date check - in production would use proper date parsing
    doc_date = fields.get('date', fields.get('issue_date', ''))
    return bool(doc_date)  # Basic existence check


def check_description_consistency(fields, lc_context):
    """Check if goods description is consistent"""
    doc_desc = fields.get('description', fields.get('goods_description', '')).lower()
    lc_desc = lc_context.get('goodsDescription', lc_context.get('formData', {}).get('goodsDescription', '')).lower()
    return bool(doc_desc and lc_desc and any(word in lc_desc for word in doc_desc.split()[:3]))


def check_port_consistency(fields, lc_context):
    """Check port information consistency"""
    doc_port = fields.get('port_of_loading', fields.get('port_of_discharge', '')).lower()
    lc_port_loading = lc_context.get('portOfLoading', lc_context.get('formData', {}).get('portOfLoading', '')).lower()
    lc_port_discharge = lc_context.get('portOfDischarge',
                                       lc_context.get('formData', {}).get('portOfDischarge', '')).lower()
    return bool(doc_port and (doc_port in lc_port_loading or doc_port in lc_port_discharge))


def check_consignee_consistency(fields, lc_context):
    """Check consignee information consistency"""
    doc_consignee = fields.get('consignee', '').lower()
    lc_beneficiary = lc_context.get('beneficiaryName',
                                    lc_context.get('formData', {}).get('beneficiaryName', '')).lower()
    return bool(doc_consignee and lc_beneficiary and doc_consignee in lc_beneficiary)


def check_insurance_coverage(fields, lc_context):
    """Check insurance coverage percentage"""
    try:
        insurance_amount = float(fields.get('insurance_amount', 0))
        invoice_amount = float(
            fields.get('amount', lc_context.get('lcAmount', lc_context.get('formData', {}).get('lcAmount', 0))))
        if invoice_amount > 0:
            coverage_ratio = insurance_amount / invoice_amount
            return coverage_ratio >= 1.1  # 110% coverage required
        return False
    except (ValueError, TypeError):
        return False

def analyze_individual_document_discrepancies(document_data, lc_context, swift_message):
    """
    Analyze a single document for compliance discrepancies using XML rules
    """
    try:
        logger.info(
            f"🔍 Starting individual document discrepancy analysis for {document_data.get('file_name', 'Unknown')}")

        # Load XML rules from discrepancy_rules.xml
        xml_rules = load_discrepancy_rules_from_xml()
        if not xml_rules:
            logger.warning("⚠️ No XML rules loaded for individual analysis")
            return {
                'success': False,
                'error': 'No discrepancy rules loaded'
            }

        logger.info(f"📋 Loaded {len(xml_rules)} XML rules for individual analysis")

        # Extract data
        lc_data = extract_enhanced_lc_data(lc_context)
        swift_data = extract_enhanced_swift_data(swift_message)

        document_type = document_data.get('document_type', '').strip()
        file_name = document_data.get('file_name', 'Unknown')

        logger.info(f"📊 Analyzing {document_type} document: {file_name}")
        logger.info(f"   - LC data: {len(lc_data)} fields")
        logger.info(f"   - SWIFT data: {len(swift_data)} fields")

        # Initialize results
        discrepancies = []

        # Filter rules for this document type
        relevant_rules = [rule for rule in xml_rules
                          if rule.get('documentType', '').lower() == document_type.lower()]

        logger.info(f"📋 Found {len(relevant_rules)} relevant XML rules for {document_type}")

        # Apply each relevant rule
        for rule in relevant_rules:
            try:
                rule_result = apply_xml_rule_with_llm_analysis(rule, document_data, lc_data, swift_data)
                if rule_result:
                    # Format the discrepancy for frontend display
                    discrepancy = {
                        'field_name': rule_result.get('field_name', 'Unknown Field'),
                        'severity': rule_result.get('severity', 'MEDIUM').upper(),
                        'confidence': rule_result.get('confidence', 70),
                        'source_value': rule_result.get('source_value', 'Not specified'),
                        'compared_value': rule_result.get('expected_value', 'Not specified'),
                        'rule_id': rule_result.get('rule_code', 'Unknown'),
                        'rule_name': rule_result.get('description', 'Compliance Rule'),
                        'discrepancy_type': rule_result.get('type', 'compliance_discrepancy'),
                        'business_impact': rule_result.get('business_impact', 'Review required'),
                        'recommendation': rule_result.get('recommendation', 'Please review and correct'),
                        'source_document': file_name,
                        'rule_basis': rule_result.get('rule_basis', 'XML Rule'),
                        'comparison_type': rule_result.get('comparison_type', 'LC vs Document')
                    }
                    discrepancies.append(discrepancy)

            except Exception as rule_error:
                logger.error(f"❌ Error applying rule {rule.get('code', 'Unknown')}: {rule_error}")
                continue

        # Calculate summary statistics
        total_discrepancies = len(discrepancies)
        critical_count = len([d for d in discrepancies if d.get('severity') == 'CRITICAL'])
        high_count = len([d for d in discrepancies if d.get('severity') == 'HIGH'])
        medium_count = len([d for d in discrepancies if d.get('severity') == 'MEDIUM'])
        low_count = len([d for d in discrepancies if d.get('severity') == 'LOW'])

        # Determine compliance status
        compliance_status = 'COMPLIANT' if total_discrepancies == 0 else 'NON_COMPLIANT'

        results = {
            'success': True,
            'results': {
                'discrepancies': discrepancies,
                'analysis_method': 'xml_rule_based_individual',
                'compliance_status': compliance_status,
                'summary': {
                    'total': total_discrepancies,
                    'critical': critical_count,
                    'high': high_count,
                    'medium': medium_count,
                    'low': low_count
                },
                'document_analysis': {
                    'file_name': file_name,
                    'document_type': document_type,
                    'rules_applied': len(relevant_rules),
                    'fields_analyzed': len(document_data.get('extracted_fields', {}))
                }
            }
        }

        logger.info(f"✅ Individual analysis completed: {total_discrepancies} discrepancies found")
        logger.info(f"   - Critical: {critical_count}, High: {high_count}, Medium: {medium_count}, Low: {low_count}")

        return results

    except Exception as e:
        logger.error(f"❌ Error in individual document discrepancy analysis: {e}")
        return {
            'success': False,
            'error': str(e)
        }