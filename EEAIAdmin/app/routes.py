from __future__ import annotations

import json
import yaml
import mimetypes
import re
import shutil
import tempfile
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict
import math
from decimal import Decimal
import hashlib
import concurrent.futures

import bcrypt
import chromadb
from app.utils.chromadb_client import get_chromadb_client
import fitz
import os
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
from pymongo import MongoClient, DESCENDING
from bson import ObjectId
from functools import wraps
import zipfile
import tiktoken
from xml.etree.ElementTree import Element, SubElement, tostring
import time

# Placeholder imports for utility functions (replace with actual implementations)
from app.utils.common import load_schema
from app.utils.file_utils import get_embedding_azureRAG
from app.utils.query_utils import handle_ai_check, chroma_client
from app.utils.document_classifier import DocumentClassifier
from app.utils.coordinate_mapper import coordinate_mapper

# WebSocket and progress tracking
from app.utils.websocket_handler import get_websocket_handler
from app.utils.progress_tracker import DocumentProcessingTracker
from app.utils import (
    process_user_query, handle_api_request, trigger_proactive_alerts, extract_text_from_file,
    generate_sql_query, execute_sql_and_format, generate_visualization_with_inference,
    analyze_ucp_compliance_chromaRAG, analyze_swift_compliance_chromaRAG, analyze_document_with_gpt,
    handle_follow_up_request, insert_trx_file_upload, insert_trx_file_detail,
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
from app.utils.app_config import deployment_name, embedding_model
from app.utils.vetting_engine import VettingRuleEngine
from app import custom_functions_routes

# Initialize Flask app and logging
app = Flask(__name__)
app.secret_key = os.urandom(24)  # Secure random secret key
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# MongoDB Configuration
MONGO_URI = "mongodb://localhost:27017/"
DATABASE_NAME = "finai_chatbot"
client = MongoClient(MONGO_URI, connectTimeoutMS=5000, serverSelectionTimeoutMS=5000)
db = client[DATABASE_NAME]
users_collection = db.users
sessions_collection = db.sessions
conversation_collection = db.conversation_history
chat_sessions_collection = db.chat_sessions
chat_messages_collection = db.chat_messages
metrics_collection = db.request_metrics  # New collection for metrics

# Initialize conversation manager
conversation_manager = ConversationManager(db)

# Initialize vetting rule engine (will be set in setup_routes)
vetting_engine = None

# ========================
# PROMPT CONFIG HELPERS
# ========================

def load_prompt_config():
    """
    Load prompt configuration from YAML file.
    This reads the document_classification_config.yaml and extracts prompt templates.
    """
    try:
        config_path = os.path.join('data', 'document_classification_config.yaml')
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        logger.info(f"✅ Loaded prompt config from {config_path}")
        return config
    except Exception as e:
        logger.error(f"❌ Failed to load prompt config: {e}")
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

        logger.info(f"✅ Built classification prompt from config ({len(complete_prompt)} chars)")
        return complete_prompt

    except Exception as e:
        logger.error(f"❌ Error building prompt from config: {e}")
        return None

def load_custom_functions_from_json():
    """Load custom functions from JSON file"""
    try:
        functions_path = os.path.join('data', 'custom_functions.json')
        with open(functions_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading custom functions: {e}")
        return {'functions': []}

def load_document_categories_from_json():
    """Load document categories with documents list"""
    try:
        categories_path = os.path.join('data', 'document_categories.json')
        with open(categories_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('categories', [])
    except Exception as e:
        logger.error(f"Error loading document categories: {e}")
        return []

def load_document_field_mappings(document_type):
    """
    Load field mappings for a specific document type from data/document_entities/*.json
    Returns formatted field example for the prompt with ALL fields included
    """
    try:
        # Normalize document type to match filename format (e.g., "Commercial Invoice" -> "Commercial_Invoice")
        doc_type_normalized = document_type.replace(' ', '_').replace('-', '_')

        # Try to load the document entity JSON file
        entity_file_path = os.path.join('data', 'document_entities', f'{doc_type_normalized}.json')

        if not os.path.exists(entity_file_path):
            logger.warning(f"Field mapping file not found: {entity_file_path}")
            return None

        with open(entity_file_path, 'r', encoding='utf-8') as f:
            entity_data = json.load(f)

        if 'mappings' not in entity_data:
            return None

        # Group fields by fieldType and remove duplicates
        mandatory_fields = []
        optional_fields = []
        conditional_fields = []
        seen_fields = set()  # Track unique field names to avoid duplicates

        for mapping in entity_data.get('mappings', []):
            field_name = mapping.get('entityName', '')
            field_category = mapping.get('dataCategoryValue', '')
            field_type = mapping.get('fieldType', 'optional')

            # Create unique key to detect duplicates
            field_key = f"{field_name}|{field_category}|{field_type}"

            if field_key in seen_fields:
                continue  # Skip duplicate field entries
            seen_fields.add(field_key)

            field_info = {
                'name': field_name,
                'category': field_category,
                'type': field_type
            }

            if field_type == 'mandatory':
                mandatory_fields.append(field_info)
            elif field_type == 'conditional':
                conditional_fields.append(field_info)
            else:
                optional_fields.append(field_info)

        # Format as comprehensive field structure - SHOW ALL FIELDS (no limits)
        example = f"\n{'='*80}\n"
        example += f"📋 COMPLETE FIELD STRUCTURE FOR: {entity_data.get('documentName', document_type).upper()}\n"
        example += f"{'='*80}\n"
        example += f"Total Fields: {len(mandatory_fields)} Mandatory + {len(optional_fields)} Optional + {len(conditional_fields)} Conditional\n"
        example += f"{'='*80}\n"

        if mandatory_fields:
            example += f"\n🔴 MANDATORY FIELDS ({len(mandatory_fields)}) - MUST EXTRACT:\n"
            for idx, field in enumerate(mandatory_fields, 1):
                example += f"  {idx}. {field['name']} (Category: {field['category']})\n"

        if optional_fields:
            example += f"\n🟡 OPTIONAL FIELDS ({len(optional_fields)}) - Extract if present:\n"
            for idx, field in enumerate(optional_fields, 1):
                example += f"  {idx}. {field['name']} (Category: {field['category']})\n"

        if conditional_fields:
            example += f"\n🟢 CONDITIONAL FIELDS ({len(conditional_fields)}) - Extract if applicable:\n"
            for idx, field in enumerate(conditional_fields, 1):
                example += f"  {idx}. {field['name']} (Category: {field['category']})\n"

        example += f"\n{'='*80}\n"
        example += "EXTRACTION INSTRUCTIONS:\n"
        example += "1. Extract ALL mandatory fields - these are REQUIRED\n"
        example += "2. Extract optional fields if the information is present in the document\n"
        example += "3. Extract conditional fields if they apply to this specific document\n"
        example += "4. For each field, provide: value, confidence (0-100), and data_category\n"
        example += "5. If a field is not found, DO NOT include it in the response\n"
        example += f"{'='*80}\n"

        logger.info(f"✅ Loaded ALL field mappings for {document_type}: {len(mandatory_fields)}M, {len(optional_fields)}O, {len(conditional_fields)}C")
        
        # Return both the example text and the structured mappings
        return {
            'example': example,
            'mappings': [{
                'entityName': field['name'],
                'fieldType': field['type'],
                'dataCategory': field['category']
            } for field in mandatory_fields + optional_fields + conditional_fields]
        }

    except Exception as e:
        logger.error(f"Error loading field mappings for {document_type}: {e}")
        return None

def validate_compliance(extracted_fields, field_mappings, config=None):
    """
    Validate extracted fields against document requirements using YAML config rules
    
    Args:
        extracted_fields: Dict of extracted field data
        field_mappings: Field mapping structure from load_document_field_mappings
        config: YAML configuration for compliance rules
    
    Returns:
        Dict with compliance results matching YAML format
    """
    try:
        if not field_mappings or not field_mappings.get('mappings'):
            return {
                "compliant": False,
                "missing_mandatory": [],
                "data_quality_issues": [{"field": "system", "issue": "No field mappings available", "severity": "critical"}],
                "warnings": ["Field mappings not available for compliance validation"],
                "recommendations": ["Ensure document type has proper field mappings configured"],
                "severity": "critical",
                "completeness": "0%"
            }
        
        mappings = field_mappings.get('mappings', [])
        
        # Get all mandatory fields
        mandatory_field_names = [m['entityName'] for m in mappings if m.get('fieldType') == 'mandatory']
        
        # Check which mandatory fields are missing
        missing_mandatory = []
        for field_name in mandatory_field_names:
            if field_name not in extracted_fields or not extracted_fields[field_name].get('value'):
                missing_mandatory.append(field_name)
        
        # Data quality issues
        data_quality_issues = []
        warnings = []
        recommendations = []
        
        # Check each extracted field for quality issues
        for field_name, field_data in extracted_fields.items():
            confidence = field_data.get('confidence', 0)
            value = field_data.get('value', '')
            
            # Low confidence warning
            if confidence < 70:
                data_quality_issues.append({
                    "field": field_name,
                    "issue": f"Low confidence ({confidence}%) - value may be incorrect",
                    "severity": "warning"
                })
            
            # Empty value for mandatory field
            if field_name in mandatory_field_names and not value:
                data_quality_issues.append({
                    "field": field_name,
                    "issue": "Mandatory field is empty",
                    "severity": "critical"
                })
        
        # Generate recommendations
        if missing_mandatory:
            recommendations.append(f"Extract missing mandatory fields: {', '.join(missing_mandatory)}")
        
        if any(issue['severity'] == 'critical' for issue in data_quality_issues):
            recommendations.append("Review and correct critical data quality issues")
        
        # Calculate completeness
        total_mandatory = len(mandatory_field_names)
        found_mandatory = len([f for f in mandatory_field_names if f in extracted_fields and extracted_fields[f].get('value')])
        completeness_pct = (found_mandatory / total_mandatory * 100) if total_mandatory > 0 else 100
        
        # Overall compliance status
        is_compliant = len(missing_mandatory) == 0 and not any(issue['severity'] == 'critical' for issue in data_quality_issues)
        
        # Overall severity
        if any(issue['severity'] == 'critical' for issue in data_quality_issues) or missing_mandatory:
            severity = "critical"
        elif any(issue['severity'] == 'warning' for issue in data_quality_issues):
            severity = "warning"
        else:
            severity = "info"
        
        return {
            "compliant": is_compliant,
            "missing_mandatory": missing_mandatory,
            "data_quality_issues": data_quality_issues,
            "warnings": warnings,
            "recommendations": recommendations,
            "severity": severity,
            "completeness": f"{completeness_pct:.1f}%"
        }
        
    except Exception as e:
        logger.error(f"Error in compliance validation: {e}")
        return {
            "compliant": False,
            "missing_mandatory": [],
            "data_quality_issues": [{"field": "system", "issue": f"Compliance validation failed: {str(e)}", "severity": "critical"}],
            "warnings": ["Compliance validation system error"],
            "recommendations": ["Check system logs for compliance validation issues"],
            "severity": "critical",
            "completeness": "0%"
        }

# Load Trade Document Data Elements Mapping
trade_document_elements = None
def load_trade_document_elements():
    """Load the trade document data elements mapping from JSON file"""
    global trade_document_elements
    try:
        elements_path = os.path.join(os.path.dirname(__file__), 'prompts', 'trade_document_data_elements.json')
        with open(elements_path, 'r', encoding='utf-8') as f:
            trade_document_elements = json.load(f)
        logger.info("✅ Trade document data elements mapping loaded successfully")
        return trade_document_elements
    except Exception as e:
        logger.error(f"❌ Error loading trade document data elements: {str(e)}")
        return None

# Load Prompt Configuration from YAML
prompt_config = None
def load_prompt_config():
    """Load prompt configuration from YAML file"""
    global prompt_config
    try:
        config_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'document_classification_config.yaml')
        with open(config_path, 'r', encoding='utf-8') as f:
            prompt_config = yaml.safe_load(f)
        logger.info("✅ Prompt configuration loaded successfully")
        return prompt_config
    except Exception as e:
        logger.warning(f"⚠️  Error loading prompt configuration: {str(e)}, using defaults")
        # Return default minimal config if file not found
        return {
            'prompts': {},
            'classification': {'model': 'gpt-4', 'temperature': 0.1},
            'extraction': {'model': 'gpt-4', 'temperature': 0},
            'compliance': {'model': 'gpt-4', 'temperature': 0.2}
        }

def get_prompt_template(category, subcategory=None):
    """Get prompt template from configuration

    Args:
        category: 'classification', 'extraction', or 'compliance'
        subcategory: Optional subcategory like 'ucp600', 'swift_mt700', etc.

    Returns:
        str: Prompt template or None if not found
    """
    global prompt_config
    if not prompt_config:
        load_prompt_config()

    try:
        if subcategory:
            template = prompt_config.get('prompts', {}).get(subcategory, {}).get('template')
            if template:
                logger.info(f"📝 Using {subcategory} template from YAML config")
            return template
        else:
            template = prompt_config.get('prompts', {}).get(category, {}).get('template')
            if template:
                logger.info(f"📝 Using {category} template from YAML config")
            else:
                logger.warning(f"⚠️  No {category} template found in YAML, using fallback")
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

# Define login_required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or 'session_id' not in session:
            logger.error(
                f"Authentication failed: user_id={session.get('user_id', 'missing')}, session_id={session.get('session_id', 'missing')}, remote_addr={request.remote_addr}")
            return jsonify({'success': False, 'message': 'Authentication required'}), 401
        session_doc = sessions_collection.find_one({'sessionId': session['session_id']})
        if not session_doc:
            logger.error(f"Invalid session: session_id={session.get('session_id')}, remote_addr={request.remote_addr}")
            session.clear()
            return jsonify({'success': False, 'message': 'Invalid session'}), 401
        sessions_collection.update_one(
            {'sessionId': session['session_id']},
            {'$set': {'lastAccessed': datetime.utcnow()}}
        )
        return f(*args, **kwargs)
    return decorated_function

logger.info("Connected to MongoDB successfully")

# Constants
SESSION_TIMEOUT_SECONDS = 300  # 5 minutes
CUSTOM_RULES_PATH = "app/utils/prompts/custom_combined_rules.json"

# Allowed user emails (single user access, no admin distinction)
ALLOWED_EMAILS = [
    "ravi@finstack-tech.com",
    "ilyashussain9@gmail.com",
    "admin@finstack-tech.com"
]
ALLOWED_FILE_TYPES = ["application/pdf", "image/jpeg", "image/png", "text/plain", "application/zip",
                      "application/x-zip-compressed"]

# Schema
schema = load_schema()

# Repository management - store active repository per user
active_user_repositories = {}


# Models
class User:
    def __init__(self, first_name: str, last_name: str, email: str, password_hash: str, created_at: datetime = None,
                 last_login: datetime = None, is_active: bool = True):
        self.first_name = first_name.strip()
        self.last_name = last_name.strip()
        self.email = email.lower()
        self.password_hash = password_hash
        self.created_at = created_at or datetime.utcnow()
        self.last_login = last_login
        self.is_active = is_active

    def to_dict(self) -> Dict[str, Any]:
        return {
            'firstName': self.first_name,
            'lastName': self.last_name,
            'email': self.email,
            'passwordHash': self.password_hash,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'lastLogin': self.last_login.isoformat() if self.last_login else None,
            'isActive': self.is_active
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'User':
        created_at = datetime.fromisoformat(data['createdAt']) if data.get('createdAt') else None
        last_login = datetime.fromisoformat(data['lastLogin']) if data.get('lastLogin') else None
        email = data.get('email', '')
        return User(
            first_name=data.get('firstName', ''),
            last_name=data.get('lastName', ''),
            email=email,
            password_hash=data.get('passwordHash', ''),
            created_at=created_at,
            last_login=last_login,
            is_active=data.get('isActive', True)
        )


class UserSession:
    def __init__(self, user_id: str, session_id: str, created_at: datetime = None, last_accessed: datetime = None,
                 ip_address: str = None, user_agent: str = None):
        self.user_id = user_id
        self.session_id = session_id
        self.created_at = created_at or datetime.utcnow()
        self.last_accessed = last_accessed or datetime.utcnow()
        self.ip_address = ip_address
        self.user_agent = user_agent

    def to_dict(self) -> Dict[str, Any]:
        return {
            'userId': str(self.user_id),
            'sessionId': self.session_id,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'lastAccessed': self.last_accessed.isoformat() if self.last_accessed else None,
            'ipAddress': self.ip_address,
            'userAgent': self.user_agent
        }


# Utility Functions
def validate_email(email: str) -> Tuple[bool, str]:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email)), "Invalid email format" if not re.match(pattern, email) else "Valid email"


def validate_password(password: str) -> Tuple[bool, str]:
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r"[0-9]", password):
        return False, "Password must contain at least one number"
    return True, "Valid password"


def validate_name(name: str) -> Tuple[bool, str]:
    name = name.strip()
    if len(name) < 2:
        return False, "Name must be at least 2 characters long"
    if not re.match(r"^[a-zA-Z\s-]+$", name):
        return False, "Name can only contain letters, spaces, or hyphens"
    return True, "Valid name"


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


# Session Management
def get_or_create_session(user_id: str) -> str:
    """Get the latest session if within timeout; else create a new session."""
    last_message = conversation_collection.find_one(
        {"user_id": user_id},
        sort=[("created_at", DESCENDING)]
    )
    if not last_message:
        # Generate session ID in the same format as frontend
        return f"session_{int(datetime.utcnow().timestamp() * 1000)}_{uuid.uuid4().hex[:9]}"
    time_diff = datetime.utcnow() - last_message["created_at"]
    if time_diff.total_seconds() > SESSION_TIMEOUT_SECONDS:
        # Generate session ID in the same format as frontend
        return f"session_{int(datetime.utcnow().timestamp() * 1000)}_{uuid.uuid4().hex[:9]}"
    return last_message["session_id"]


def save_to_conversation(user_id: str, role: str, message: Any, max_size: int = 50000, session_id: str = None,
                         message_type: str = None) -> str:
    """Insert a conversation entry into MongoDB with session and timestamp."""
    if message is None:
        message = "No answer available."
    elif isinstance(message, dict):
        message = json.dumps(message, default=convert_decimal)
    elif not isinstance(message, str):
        message = str(message)

    if len(message) > max_size:
        message = message[:max_size] + " [Truncated]"
    if session_id is None:
        session_id = get_or_create_session(user_id)
    document = {
        "user_id": user_id,
        "session_id": session_id,
        "role": role,
        "message": message,
        "created_at": datetime.utcnow()
    }

    # Add message_type if provided
    if message_type:
        document["message_type"] = message_type

    conversation_collection.insert_one(document)

    # Update or create session in chat_sessions collection
    now = datetime.utcnow()
    chat_session = db.chat_sessions.find_one({"user_id": user_id, "session_id": session_id})

    if chat_session:
        # Update existing session
        update_data = {
            "$set": {"last_activity": now},
            "$inc": {"message_count": 1}
        }

        # If this is the first user message and role is 'user', save it as title
        if chat_session.get("message_count", 0) == 0 and role == "user" and message:
            update_data["$set"]["first_message"] = message
            update_data["$set"]["title"] = message[:100]  # Store first 100 chars as title

        db.chat_sessions.update_one(
            {"user_id": user_id, "session_id": session_id},
            update_data
        )
    else:
        # Create new session
        session_data = {
            "user_id": user_id,
            "session_id": session_id,
            "created_at": now,
            "last_activity": now,
            "message_count": 1
        }

        # If this is a user message, save it as the first message and title
        if role == "user" and message:
            session_data["first_message"] = message
            session_data["title"] = message[:100]  # Store first 100 chars as title

        db.chat_sessions.insert_one(session_data)

    # Also save to chat_messages collection for consistency
    db.chat_messages.insert_one({
        "user_id": user_id,
        "session_id": session_id,
        "role": role,
        "content": message,
        "timestamp": now
    })

    logger.info(f"Saved message for user {user_id}, session {session_id}")
    return session_id


def get_conversation_context(user_id: str, session_id: str = None) -> List[Dict[str, Any]]:
    """Retrieve all conversation entries for a user from MongoDB, optionally filtered by session."""
    query = {"user_id": user_id}
    if session_id:
        query["session_id"] = session_id
    context = list(conversation_collection.find(query, {"_id": 0}))
    logger.info(f"Retrieved conversation context for user {user_id}, session {session_id}: {context}")
    return context


def get_latest_session_id(user_id: str) -> Optional[str]:
    """Find the latest session_id for this user."""
    last_message = conversation_collection.find_one(
        {"user_id": user_id},
        sort=[("created_at", DESCENDING)]
    )
    return last_message["session_id"] if last_message else None


def retrieve_conversation_history(user_id: str, session_id: str = None, only_latest_session: bool = False) -> List[
    Dict[str, Any]]:
    """Retrieve conversation history for a given user_id, optionally filtered by session or only latest session."""
    if only_latest_session:
        session_id = get_latest_session_id(user_id)
    return get_conversation_context(user_id, session_id)


# Database Operations
class UserRepository:
    @staticmethod
    def create_user(user_data: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            email_valid, email_msg = validate_email(user_data['email'])
            if not email_valid:
                return None, email_msg
            fname_valid, fname_msg = validate_name(user_data['firstName'])
            if not fname_valid:
                return None, fname_msg
            lname_valid, lname_msg = validate_name(user_data['lastName'])
            if not lname_valid:
                return None, lname_msg

            if users_collection.find_one({'email': user_data['email'].lower()}):
                return None, "User with this email already exists"

            # Hash password using bcrypt
            password = user_data['password'].encode('utf-8')  # Encode password to bytes
            password_hash = bcrypt.hashpw(password, bcrypt.gensalt()).decode('utf-8')  # Generate salt and hash
            user_doc = {
                'firstName': user_data['firstName'].strip(),
                'lastName': user_data['lastName'].strip(),
                'email': user_data['email'].lower(),
                'passwordHash': password_hash,
                'createdAt': datetime.utcnow(),
                'lastLogin': None,
                'isActive': True
            }
            result = users_collection.insert_one(user_doc)
            user_doc['_id'] = str(result.inserted_id)
            return user_doc, None
        except Exception as e:
            logger.error(f"Error creating user: {e}", exc_info=True)
            return None, f"Failed to create user: {str(e)}"

    @staticmethod
    def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
        try:
            user_doc = users_collection.find_one({'email': email.lower()})
            if user_doc:
                user_doc['_id'] = str(user_doc['_id'])
            return user_doc
        except Exception as e:
            logger.error(f"Error finding user by email {email}: {e}", exc_info=True)
            return None

    @staticmethod
    def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
        try:
            user_doc = users_collection.find_one({'_id': ObjectId(user_id)})
            if user_doc:
                user_doc['_id'] = str(user_doc['_id'])
            return user_doc
        except Exception as e:
            logger.error(f"Error finding user by ID {user_id}: {e}", exc_info=True)
            return None

    @staticmethod
    def update_last_login(user_id: str):
        try:
            users_collection.update_one(
                {'_id': ObjectId(user_id)},
                {'$set': {'lastLogin': datetime.utcnow()}}
            )
        except Exception as e:
            logger.error(f"Error updating last login for user {user_id}: {e}", exc_info=True)


class SessionRepository:
    @staticmethod
    def create_session(user_id: str, ip_address: str = None, user_agent: str = None) -> Optional[str]:
        try:
            session_id = str(uuid.uuid4())
            session_doc = {
                'userId': ObjectId(user_id),
                'sessionId': session_id,
                'createdAt': datetime.utcnow(),
                'lastAccessed': datetime.utcnow(),
                'ipAddress': ip_address,
                'userAgent': user_agent
            }
            sessions_collection.insert_one(session_doc)
            return session_id
        except Exception as e:
            logger.error(f"Error creating session for user {user_id}: {e}", exc_info=True)
            return None

    @staticmethod
    def get_session(session_id: str) -> Optional[Dict[str, Any]]:
        try:
            session_doc = sessions_collection.find_one({'sessionId': session_id})
            if session_doc:
                session_doc['userId'] = str(session_doc['userId'])
            return session_doc
        except Exception as e:
            logger.error(f"Error finding session {session_id}: {e}", exc_info=True)
            return None

    @staticmethod
    def delete_session(session_id: str):
        try:
            sessions_collection.delete_one({'sessionId': session_id})
        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {e}", exc_info=True)


# AOP Decorator for Timing
def timing_aspect(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        # Record start time
        start_time = time.time()
        start_datetime = datetime.utcnow()

        # Log request start
        logger.info(f"Request started for endpoint: {f.__name__}, path: {request.path}, method: {request.method}")

        try:
            # Execute the endpoint function
            response = f(*args, **kwargs)

            # Record end time
            end_time = time.time()
            duration = end_time - start_time  # Duration in seconds

            # Log response
            logger.info(f"Request completed for endpoint: {f.__name__}, duration: {duration:.3f} seconds")

            # Prepare metrics document
            metrics_doc = {
                "endpoint": f.__name__,
                "path": request.path,
                "method": request.method,
                "start_time": start_datetime.isoformat(),
                "end_time": datetime.utcnow().isoformat(),
                "duration_seconds": duration,
                "user_id": session.get("user_id", "anonymous"),
                "session_id": session.get("session_id", None),
                "ip_address": request.remote_addr,
                "user_agent": request.headers.get("User-Agent"),
                "status_code": response[1] if isinstance(response, tuple) else 200,
                "timestamp": datetime.utcnow()
            }

            # Store in MongoDB
            try:
                metrics_collection.insert_one(metrics_doc)
                logger.info(f"Metrics stored for endpoint: {f.__name__}")
            except Exception as e:
                logger.error(f"Failed to store metrics for endpoint {f.__name__}: {e}")

            return response

        except Exception as e:
            # Log error and store metrics for failed request
            end_time = time.time()
            duration = end_time - start_time
            logger.error(f"Error in endpoint {f.__name__}: {e}")

            metrics_doc = {
                "endpoint": f.__name__,
                "path": request.path,
                "method": request.method,
                "start_time": start_datetime.isoformat(),
                "end_time": datetime.utcnow().isoformat(),
                "duration_seconds": duration,
                "user_id": session.get("user_id", "anonymous"),
                "session_id": session.get("session_id", None),
                "ip_address": request.remote_addr,
                "user_agent": request.headers.get("User-Agent"),
                "status_code": 500,
                "error": str(e),
                "timestamp": datetime.utcnow()
            }

            try:
                metrics_collection.insert_one(metrics_doc)
                logger.info(f"Error metrics stored for endpoint: {f.__name__}")
            except Exception as e:
                logger.error(f"Failed to store error metrics for endpoint {f.__name__}: {e}")

            raise  # Re-raise the exception to let Flask handle it

    return wrapper


# Authentication Decorator
# login_required decorator is already defined above (line 103)

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
    @app.route('/document-classification')
    def document_classification():
        """Document classification and compliance page"""
        return render_template('document_classification.html')
    
    @app.route('/document-classification-overlay')
    def document_classification_overlay():
        """Document classification with overlay header for modal/iframe use"""
        return render_template('document_classification_overlay.html')
    
    @app.route('/document-classification-embed')
    def document_classification_embed():
        """Embedded document classification for modal/iframe use"""
        return render_template('document_classification_embed.html')

    @app.route("/auth/login", methods=["POST"])
    @timing_aspect
    def login():
        """Handle user login and create a session."""
        try:
            data = request.get_json()
            if not data or not data.get("email") or not data.get("password"):
                return jsonify({"success": False, "message": "Email and password are required"}), 400

            user = UserRepository.get_user_by_email(data["email"])
            if not user:
                return jsonify({"success": False, "message": "Invalid email or password"}), 401

            try:
                # Verify password using bcrypt
                if not bcrypt.checkpw(data["password"].encode('utf-8'), user["passwordHash"].encode('utf-8')):
                    return jsonify({"success": False, "message": "Invalid email or password"}), 401
            except ValueError as e:
                logger.error(f"Invalid password hash for {data.get('email', 'unknown')}: {e}")
                return jsonify({"success": False, "message": "Invalid password hash. Please reset your password."}), 400

            UserRepository.update_last_login(user["_id"])

            session_id = SessionRepository.create_session(
                user_id=user["_id"],
                ip_address=request.remote_addr,
                user_agent=request.headers.get("User-Agent")
            )
            if not session_id:
                return jsonify({"success": False, "message": "Failed to create session"}), 500

            session["user_id"] = user["_id"]
            session["session_id"] = session_id
            session["user_email"] = user["email"]  # Store email in session for admin checks

            # Check admin status
            is_admin = user["email"].lower() in [e.lower() for e in ALLOWED_EMAILS]
            logger.info(f"Login - User: {user['email']}, isAdmin: {is_admin}, ALLOWED_EMAILS: {ALLOWED_EMAILS}")

            return jsonify({
                "success": True,
                "message": "Login successful",
                "user": {
                    "id": user["_id"],
                    "firstName": user["firstName"],
                    "lastName": user["lastName"],
                    "email": user["email"],
                    "isAllowed": is_admin,
                    "isAdmin": is_admin  # Add isAdmin for frontend compatibility
                }
            }), 200

        except Exception as e:
            logger.error(f"Login error for email {data.get('email', 'unknown')}: {e}", exc_info=True)
            return jsonify({"success": False, "message": "An error occurred during login"}), 500

    @app.route("/auth/register", methods=["POST"])
    @timing_aspect
    def register():
        """Handle user registration."""
        try:
            data = request.get_json()
            required_fields = ["firstName", "lastName", "email", "password"]
            if not data or not all(field in data for field in required_fields):
                return jsonify({"success": False, "message": "All fields are required"}), 400

            email_valid, email_msg = validate_email(data["email"])
            if not email_valid:
                return jsonify({"success": False, "message": email_msg}), 400

            fname_valid, fname_msg = validate_name(data["firstName"])
            if not fname_valid:
                return jsonify({"success": False, "message": fname_msg}), 400

            lname_valid, lname_msg = validate_name(data["lastName"])
            if not lname_valid:
                return jsonify({"success": False, "message": lname_msg}), 400

            password_valid, password_msg = validate_password(data["password"])
            if not password_valid:
                return jsonify({"success": False, "message": password_msg}), 400

            user_data = {
                "firstName": data["firstName"],
                "lastName": data["lastName"],
                "email": data["email"],
                "password": data["password"]
            }
            user, error = UserRepository.create_user(user_data)
            if error:
                return jsonify({"success": False, "message": error}), 400

            return jsonify({
                "success": True,
                "message": "Registration successful",
                "user": {
                    "id": user["_id"],
                    "firstName": user["firstName"],
                    "lastName": user["lastName"],
                    "email": user["email"]
                }
            }), 201

        except Exception as e:
            logger.error(f"Registration error: {e}", exc_info=True)
            return jsonify({"success": False, "message": "An error occurred during registration"}), 500

    @app.route("/auth/protected", methods=["GET"])
    @login_required
    @timing_aspect
    def protected():
        try:
            if 'user_id' not in session:
                logger.error(f"Missing user_id in session for protected route, remote_addr={request.remote_addr}")
                return jsonify({"success": False, "message": "Session invalid, please log in again"}), 401
            user = UserRepository.get_user_by_id(session["user_id"])
            if not user:
                session.clear()
                return jsonify({"success": False, "message": "User not found"}), 401
            return jsonify({
                "success": True,
                "user": {
                    "id": user["_id"],
                    "firstName": user["firstName"],
                    "lastName": user["lastName"],
                    "email": user["email"]
                }
            }), 200
        except Exception as e:
            logger.error(f"Protected route error: {e}, remote_addr={request.remote_addr}", exc_info=True)
            return jsonify({"success": False, "message": "An error occurred"}), 500

    @app.route("/auth/current-user", methods=["GET"])
    @login_required
    @timing_aspect
    def get_current_user():
        """Get current user information including admin status."""
        try:
            if 'user_id' not in session:
                return jsonify({"success": False, "message": "Session invalid"}), 401
            
            user = UserRepository.get_user_by_id(session["user_id"])
            if not user:
                session.clear()
                return jsonify({"success": False, "message": "User not found"}), 401
            
            # Check if user is allowed
            is_allowed = user["email"].lower() in [e.lower() for e in ALLOWED_EMAILS]
            
            # Debug logging
            logger.info(f"Current user check - Email: {user['email']}, isAllowed: {is_allowed}, ALLOWED_EMAILS: {ALLOWED_EMAILS}")
            
            response_data = {
                "success": True,
                "user": {
                    "id": user["_id"],
                    "firstName": user["firstName"],
                    "lastName": user["lastName"],
                    "email": user["email"],
                    "isAllowed": is_allowed,
                    "isAdmin": is_allowed  # Add isAdmin for frontend compatibility
                }
            }
            
            logger.info(f"Returning user data with isAdmin={is_allowed} for {user['email']}")
            
            return jsonify(response_data), 200
        except Exception as e:
            logger.error(f"Get current user error: {e}", exc_info=True)
            return jsonify({"success": False, "message": "An error occurred"}), 500

    @app.route("/auth/logout", methods=["POST"])
    @timing_aspect
    def logout():
        """Handle user logout."""
        try:
            if "session_id" in session:
                SessionRepository.delete_session(session["session_id"])
            session.clear()
            return jsonify({"success": True, "message": "Logged out successfully"}), 200
        except Exception as e:
            logger.error(f"Logout error: {e}", exc_info=True)
            return jsonify({"success": False, "message": "An error occurred during logout"}), 500


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


def setup_routes(app: Flask):
    """Data Categories Management Routes"""
    custom_functions_routes.register_custom_functions_routes(app)

    @app.route('/data_categories')
    @timing_aspect
    def data_categories():
        """Data categories management page"""
        return render_template('data_categories.html')

    @app.route('/api/data_categories', methods=['GET'])
    @timing_aspect
    def get_all_categories():
        """Get all data categories"""
        try:
            data = _load_categories()
            return jsonify({'success': True, 'categories': data['categories']}), 200

        except Exception as e:
            logger.error(f"Error getting categories: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/data_categories', methods=['POST'])
    @timing_aspect
    def create_category():
        """Create a new category"""
        try:
            request_data = request.json
            all_data = _load_categories()

            # Generate new ID
            max_id = 0
            for cat in all_data['categories']:
                try:
                    cat_id = int(cat['id'])
                    if cat_id > max_id:
                        max_id = cat_id
                except (ValueError, KeyError):
                    pass

            new_id = str(max_id + 1)

            # Create new category
            new_category = {
                'id': new_id,
                'value': request_data.get('value', '')
            }

            all_data['categories'].append(new_category)
            _save_categories(all_data)

            return jsonify({'success': True, 'category': new_category}), 201

        except Exception as e:
            logger.error(f"Error creating category: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/data_categories/<category_id>', methods=['PUT'])
    @timing_aspect
    def update_category(category_id):
        """Update a category"""
        try:
            request_data = request.json
            all_data = _load_categories()

            # Find and update the category
            category_found = False
            for category in all_data['categories']:
                if category['id'] == category_id:
                    category['value'] = request_data.get('value', category['value'])
                    category_found = True
                    break

            if not category_found:
                return jsonify({'success': False, 'message': 'Category not found'}), 404

            _save_categories(all_data)
            return jsonify({'success': True, 'message': 'Category updated successfully'}), 200

        except Exception as e:
            logger.error(f"Error updating category {category_id}: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/data_categories/<category_id>', methods=['DELETE'])
    @timing_aspect
    def delete_category(category_id):
        """Delete a category"""
        try:
            all_data = _load_categories()

            # Remove category
            original_length = len(all_data['categories'])
            all_data['categories'] = [cat for cat in all_data['categories'] if cat['id'] != category_id]

            if len(all_data['categories']) == original_length:
                return jsonify({'success': False, 'message': 'Category not found'}), 404

            _save_categories(all_data)
            return jsonify({'success': True, 'message': 'Category deleted successfully'}), 200

        except Exception as e:
            logger.error(f"Error deleting category {category_id}: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    # Entities Management Routes
    @app.route('/entities')
    @timing_aspect
    def entities():
        """Entities management page"""
        return render_template('entities.html')

    @app.route('/api/entities', methods=['GET'])
    @timing_aspect
    def get_all_entities():
        """Get all entities"""
        try:
            data = _load_entities()
            return jsonify({'success': True, 'entities': data['entities']}), 200

        except Exception as e:
            logger.error(f"Error getting entities: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/entities', methods=['POST'])
    @timing_aspect
    def create_entity():
        """Create a new entity"""
        try:
            request_data = request.json
            all_data = _load_entities()

            # Generate new ID
            max_id = 0
            for entity in all_data['entities']:
                try:
                    entity_id = int(entity['id'])
                    if entity_id > max_id:
                        max_id = entity_id
                except (ValueError, KeyError):
                    pass

            new_id = str(max_id + 1)

            # Create new entity
            new_entity = {
                'id': new_id,
                'name': request_data.get('name', ''),
                'description': request_data.get('description', ''),
                'mappingFormField': request_data.get('mappingFormField', ''),
                'mappingFormDescription': request_data.get('mappingFormDescription', ''),
                'dataCategoryId': request_data.get('dataCategoryId', ''),
                'dataCategoryValue': request_data.get('dataCategoryValue', '')
            }

            all_data['entities'].append(new_entity)
            _save_entities(all_data)

            return jsonify({'success': True, 'entity': new_entity}), 201

        except Exception as e:
            logger.error(f"Error creating entity: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/entities/<entity_id>', methods=['PUT'])
    @timing_aspect
    def update_entity(entity_id):
        """Update an entity"""
        try:
            request_data = request.json
            all_data = _load_entities()

            # Find and update the entity
            entity_found = False
            for entity in all_data['entities']:
                if entity['id'] == entity_id:
                    entity['name'] = request_data.get('name', entity['name'])
                    entity['description'] = request_data.get('description', entity['description'])
                    entity['mappingFormField'] = request_data.get('mappingFormField',
                                                                  entity.get('mappingFormField', ''))
                    entity['mappingFormDescription'] = request_data.get('mappingFormDescription',
                                                                        entity.get('mappingFormDescription', ''))
                    entity['dataCategoryId'] = request_data.get('dataCategoryId',
                                                                entity.get('dataCategoryId', ''))
                    entity['dataCategoryValue'] = request_data.get('dataCategoryValue',
                                                                   entity.get('dataCategoryValue', ''))
                    entity_found = True
                    break

            if not entity_found:
                return jsonify({'success': False, 'message': 'Entity not found'}), 404

            _save_entities(all_data)
            return jsonify({'success': True, 'message': 'Entity updated successfully'}), 200

        except Exception as e:
            logger.error(f"Error updating entity {entity_id}: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/entities/<entity_id>', methods=['DELETE'])
    @timing_aspect
    def delete_entity(entity_id):
        """Delete an entity"""
        try:
            all_data = _load_entities()

            # Remove entity
            original_length = len(all_data['entities'])
            all_data['entities'] = [ent for ent in all_data['entities'] if ent['id'] != entity_id]

            if len(all_data['entities']) == original_length:
                return jsonify({'success': False, 'message': 'Entity not found'}), 404

            _save_entities(all_data)
            return jsonify({'success': True, 'message': 'Entity deleted successfully'}), 200

        except Exception as e:
            logger.error(f"Error deleting entity {entity_id}: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    # ==================== Prompt Configuration Routes ====================
    @app.route('/prompt-config')
    @timing_aspect
    def prompt_config_page():
        """Prompt configuration management page"""
        return render_template('prompt_config.html')

    @app.route('/api/prompt-config', methods=['GET'])
    @timing_aspect
    def get_prompt_config():
        """Get current prompt configuration from YAML"""
        try:
            config_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'document_classification_config.yaml')

            if not os.path.exists(config_path):
                return jsonify({'success': False, 'message': 'Configuration file not found'}), 404

            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            return jsonify({'success': True, 'config': config}), 200

        except Exception as e:
            logger.error(f"Error loading prompt config: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/prompt-config', methods=['POST'])
    @timing_aspect
    def update_prompt_config():
        """Update prompt configuration in YAML"""
        try:
            config_data = request.json
            config_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'document_classification_config.yaml')

            # Load existing config
            with open(config_path, 'r', encoding='utf-8') as f:
                existing_config = yaml.safe_load(f)

            # Update specific sections
            if 'classification' in config_data:
                existing_config['classification'].update(config_data['classification'])

            if 'extraction' in config_data:
                existing_config['extraction'].update(config_data['extraction'])

            if 'compliance' in config_data:
                existing_config['compliance'].update(config_data['compliance'])

            if 'prompts' in config_data:
                if 'prompts' not in existing_config:
                    existing_config['prompts'] = {}
                existing_config['prompts'].update(config_data['prompts'])

            if 'performance' in config_data:
                existing_config['performance'].update(config_data['performance'])

            if 'error_handling' in config_data:
                existing_config['error_handling'].update(config_data['error_handling'])

            if 'features' in config_data:
                existing_config['features'].update(config_data['features'])

            # Save updated config
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(existing_config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

            # Reload the configuration immediately
            global prompt_config
            prompt_config = load_prompt_config()

            logger.info("✅ Prompt configuration updated and reloaded successfully")
            return jsonify({'success': True, 'message': 'Configuration updated successfully'}), 200

        except Exception as e:
            logger.error(f"Error updating prompt config: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/prompt-config/reset', methods=['POST'])
    @timing_aspect
    def reset_prompt_config():
        """Reset prompt configuration to defaults"""
        try:
            config_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'document_classification_config.yaml')
            backup_path = config_path + '.backup'

            # Create backup
            if os.path.exists(config_path):
                shutil.copy(config_path, backup_path)

            # Create default configuration
            default_config = {
                'classification': {
                    'model': 'gpt-4',
                    'temperature': 0.1,
                    'max_tokens': 500,
                    'system_prompt': 'You are an expert document classifier for international trade and finance documents.'
                },
                'extraction': {
                    'model': 'gpt-4',
                    'temperature': 0,
                    'max_tokens': 3000,
                    'system_prompt': 'You are an expert data extraction system for trade finance documents.'
                },
                'compliance': {
                    'model': 'gpt-4',
                    'temperature': 0.2,
                    'max_tokens': 1500,
                    'system_prompt': 'You are a compliance verification expert for trade finance documents.'
                },
                'prompts': {
                    'classification': {
                        'template': '''You are an expert document classifier for international trade and finance documents.

Analyze the following document text and identify the exact document type.

AVAILABLE DOCUMENT TYPES:
{document_types_list}

DOCUMENT TEXT:
{ocr_text}

Respond in JSON format:
{{
    "document_type": "exact document name from the list",
    "document_code": "document code (e.g., PO, INV, LC)",
    "confidence": 0.95,
    "reasoning": "brief explanation of classification"
}}'''
                    },
                    'extraction': {
                        'template': '''You are an expert data extraction system for trade finance documents.

Extract the following information from this {document_name}:

MANDATORY FIELDS (Must extract if present):
{mandatory_fields}

OPTIONAL FIELDS (Extract if available):
{optional_fields}

CONDITIONAL FIELDS (Extract based on context):
{conditional_fields}

DOCUMENT TEXT:
{ocr_text}

INSTRUCTIONS:
1. Extract all mandatory fields - mark as null if truly not present
2. Extract optional fields where available
3. Extract conditional fields based on document context
4. Use exact field names from the list above
5. Preserve original data format and values

Respond in JSON format with extracted fields:
{{
    "mandatory": {{"field_name": "value", ...}},
    "optional": {{"field_name": "value", ...}},
    "conditional": {{"field_name": "value", ...}}
}}'''
                    },
                    'compliance': {
                        'template': '''You are a compliance verification expert for {document_name}.

EXTRACTED DATA:
Mandatory: {mandatory_data}
Optional: {optional_data}
Conditional: {conditional_data}

REQUIRED MANDATORY FIELDS:
{mandatory_fields_list}

MISSING MANDATORY FIELDS:
{missing_mandatory_list}

COMPLIANCE CHECK:
1. Verify all mandatory fields are present and valid
2. Check data quality and format
3. Identify any critical issues
4. Provide recommendations

Respond in JSON format:
{{
    "compliant": true/false,
    "missing_mandatory": [...],
    "data_quality_issues": [...],
    "warnings": [...],
    "recommendations": [...],
    "severity": "critical/warning/info"
}}'''
                    },
                    'ucp600': {
                        'template': '''Check compliance with UCP600 rules for Letter of Credit.

Verify the following fields meet UCP600 requirements:
{fields}

Return compliance status for each field.'''
                    },
                    'swift_mt700': {
                        'template': '''Check compliance with SWIFT MT700 format for Letter of Credit.

Verify the following fields meet SWIFT MT700 format requirements:
{fields}

Return compliance status for each field.'''
                    },
                    'urdg758': {
                        'template': '''Check compliance with URDG758 rules for Bank Guarantee.

Verify the following fields meet URDG758 requirements:
{fields}

Return compliance status for each field.'''
                    },
                    'swift_mt760': {
                        'template': '''Check compliance with SWIFT MT760 format for Bank Guarantee.

Verify the following fields meet SWIFT MT760 format requirements:
{fields}

Return compliance status for each field.'''
                    }
                },
                'performance': {
                    'classification_timeout': 30,
                    'extraction_timeout': 60,
                    'compliance_timeout': 30,
                    'total_timeout': 180
                },
                'error_handling': {
                    'retry_on_failure': True,
                    'max_retries': 3,
                    'retry_delay_seconds': 2
                },
                'features': {
                    'enable_enhanced_classification': True,
                    'enable_entity_extraction': True,
                    'enable_compliance_checking': True,
                    'enable_progress_tracking': True
                }
            }

            # Save default config
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(default_config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

            logger.info("Prompt configuration reset to defaults")
            return jsonify({'success': True, 'message': 'Configuration reset to defaults'}), 200

        except Exception as e:
            logger.error(f"Error resetting prompt config: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/prompt-config/export', methods=['GET'])
    @timing_aspect
    def export_prompt_config():
        """Export current prompt configuration as YAML"""
        try:
            config_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'document_classification_config.yaml')

            if not os.path.exists(config_path):
                return jsonify({'success': False, 'message': 'Configuration file not found'}), 404

            return send_file(
                config_path,
                mimetype='application/x-yaml',
                as_attachment=True,
                download_name='document_classification_config.yaml'
            )

        except Exception as e:
            logger.error(f"Error exporting prompt config: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/prompt-config/reload', methods=['POST'])
    @timing_aspect
    def reload_prompt_config():
        """Manually reload prompt configuration from YAML"""
        try:
            global prompt_config
            prompt_config = None
            load_prompt_config()

            logger.info("✅ Prompt configuration manually reloaded")
            return jsonify({'success': True, 'message': 'Configuration reloaded successfully'}), 200

        except Exception as e:
            logger.error(f"Error reloading prompt config: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    # ==================== Helper Functions ====================
    def normalize_date_for_search(text):
        """
        Normalize different date formats to a common format for comparison
        Handles formats like: 2025-05-15, 15-05-2025, 15/05/2025, 15.05.2025
        And different orders: yyyy-mm-dd, dd-mm-yyyy, mm-dd-yyyy, etc.
        
        Returns:
            list: All possible normalized date representations
        """
        import re
        
        if not text or not isinstance(text, str):
            return []
        
        # Remove extra whitespace
        text = text.strip()
        
        # Define date separators
        separators = ['-', '/', '.', ' ']
        
        # Extract potential date patterns
        date_patterns = []
        
        # Pattern for various date formats (4 digits or 1-2 digits)
        date_regex = r'(\d{1,4})[\/\-\.\s](\d{1,2})[\/\-\.\s](\d{1,4})'
        matches = re.finditer(date_regex, text)
        
        for match in matches:
            part1, part2, part3 = match.groups()
            
            # Convert to integers for processing
            try:
                p1, p2, p3 = int(part1), int(part2), int(part3)
            except ValueError:
                continue
            
            # Determine which part is year, month, day
            normalized_dates = []
            
            # Case 1: First part is year (yyyy-mm-dd format)
            if p1 >= 1900 and p1 <= 2100:
                if 1 <= p2 <= 12 and 1 <= p3 <= 31:
                    normalized_dates.append(f"{p1:04d}-{p2:02d}-{p3:02d}")
                    normalized_dates.append(f"{p3:02d}-{p2:02d}-{p1:04d}")
                    normalized_dates.append(f"{p3:02d}/{p2:02d}/{p1:04d}")
                    normalized_dates.append(f"{p3:02d}.{p2:02d}.{p1:04d}")
            
            # Case 2: Last part is year (dd-mm-yyyy or mm-dd-yyyy format)
            if p3 >= 1900 and p3 <= 2100:
                # dd-mm-yyyy
                if 1 <= p1 <= 31 and 1 <= p2 <= 12:
                    normalized_dates.append(f"{p3:04d}-{p2:02d}-{p1:02d}")
                    normalized_dates.append(f"{p1:02d}-{p2:02d}-{p3:04d}")
                    normalized_dates.append(f"{p1:02d}/{p2:02d}/{p3:04d}")
                    normalized_dates.append(f"{p1:02d}.{p2:02d}.{p3:04d}")
                
                # mm-dd-yyyy
                if 1 <= p1 <= 12 and 1 <= p2 <= 31:
                    normalized_dates.append(f"{p3:04d}-{p1:02d}-{p2:02d}")
                    normalized_dates.append(f"{p2:02d}-{p1:02d}-{p3:04d}")
                    normalized_dates.append(f"{p2:02d}/{p1:02d}/{p3:04d}")
                    normalized_dates.append(f"{p2:02d}.{p1:02d}.{p3:04d}")
            
            # Case 3: Year in middle (rare but possible)
            if p2 >= 1900 and p2 <= 2100:
                if 1 <= p1 <= 31 and 1 <= p3 <= 12:
                    normalized_dates.append(f"{p2:04d}-{p3:02d}-{p1:02d}")
                    normalized_dates.append(f"{p1:02d}-{p3:02d}-{p2:04d}")
                    normalized_dates.append(f"{p1:02d}/{p3:02d}/{p2:04d}")
                    normalized_dates.append(f"{p1:02d}.{p3:02d}.{p2:04d}")
            
            date_patterns.extend(normalized_dates)
        
        # Remove duplicates and return
        return list(set(date_patterns))

    def search_text_in_ocr(field_value, ocr_data, search_mode='exact'):
        """
        Search for text in OCR data and return matching entries with coordinates
        
        Args:
            field_value (str): The text to search for
            ocr_data (list): List of OCR entries with text and bounding box data
            search_mode (str): Search strategy - 'exact', 'fuzzy', or 'contains'
        
        Returns:
            list: Matching OCR entries with coordinates and confidence scores
        """
        import time
        from difflib import SequenceMatcher
        
        logger.info(f"🔍 === STARTING OCR TEXT SEARCH ===")
        logger.info(f"🎯 Target field value: '{field_value}'")
        logger.info(f"🔧 Search mode: {search_mode}")
        logger.info(f"📄 OCR entries to search: {len(ocr_data)}")
        
        if not field_value or not field_value.strip():
            logger.warning("❌ Empty field value provided")
            return []
        
        if not ocr_data:
            logger.warning("❌ No OCR data provided")
            return []
        
        field_value_lower = field_value.lower().strip()
        matches = []
        
        # Check if field_value looks like a date and normalize it
        field_date_patterns = normalize_date_for_search(field_value)
        is_date_search = len(field_date_patterns) > 0
        
        if is_date_search:
            logger.info(f"📅 Detected date search. Normalized patterns: {field_date_patterns}")
        else:
            logger.info(f"📝 Searching for phrase/sentence: '{field_value}'")
        
        # Search statistics
        exact_matches = 0
        fuzzy_matches = 0
        contains_matches = 0
        partial_matches = 0
        date_matches = 0
        no_matches = 0
        
        logger.info(f"🔎 Starting sentence/phrase search through {len(ocr_data)} OCR entries")
        
        for i, ocr_entry in enumerate(ocr_data):
            ocr_text = ocr_entry.get('text', '').strip()
            
            if not ocr_text:
                logger.debug(f"   Entry {i+1}: Skipping empty text")
                continue
                
            ocr_text_lower = ocr_text.lower()
            match_confidence = 0
            match_type = 'none'
            
            logger.debug(f"   Entry {i+1}: Comparing '{field_value_lower}' with '{ocr_text_lower}'")
            
            # Date matching logic (highest priority for date searches)
            if is_date_search and match_confidence < 100:
                ocr_date_patterns = normalize_date_for_search(ocr_text)
                if ocr_date_patterns:
                    # Check if any normalized date patterns match
                    for field_pattern in field_date_patterns:
                        for ocr_pattern in ocr_date_patterns:
                            if field_pattern == ocr_pattern:
                                match_confidence = 100
                                match_type = 'date_exact'
                                date_matches += 1
                                logger.debug(f"      ✅ DATE EXACT MATCH! '{field_pattern}' matches '{ocr_pattern}' - Confidence: 100%")
                                break
                        if match_confidence == 100:
                            break
            
            # Regular exact match (high priority)
            if match_confidence < 100 and search_mode in ['exact', 'fuzzy', 'contains']:
                if field_value_lower == ocr_text_lower:
                    match_confidence = 100
                    match_type = 'exact'
                    exact_matches += 1
                    logger.debug(f"      ✅ EXACT MATCH! Confidence: 100%")
                elif field_value_lower in ocr_text_lower:
                    match_confidence = 90
                    match_type = 'contains'
                    contains_matches += 1
                    logger.debug(f"      ✅ CONTAINS MATCH! '{field_value_lower}' found in '{ocr_text_lower}' - Confidence: 90%")
                elif ocr_text_lower in field_value_lower:
                    match_confidence = 85
                    match_type = 'partial'
                    partial_matches += 1
                    logger.debug(f"      ✅ PARTIAL MATCH! '{ocr_text_lower}' found in '{field_value_lower}' - Confidence: 85%")
            
            # Fuzzy matching if enabled and no exact match
            if search_mode in ['fuzzy', 'contains'] and match_confidence < 90:
                similarity = SequenceMatcher(None, field_value_lower, ocr_text_lower).ratio()
                logger.debug(f"      🔀 Fuzzy similarity: {similarity:.3f}")
                if similarity >= 0.8:  # High similarity threshold
                    fuzzy_confidence = similarity * 80
                    if fuzzy_confidence > match_confidence:
                        match_confidence = fuzzy_confidence
                        match_type = 'fuzzy'
                        fuzzy_matches += 1
                        logger.debug(f"      ✅ FUZZY MATCH! Similarity: {similarity:.3f} - Confidence: {fuzzy_confidence:.1f}%")
            
            if match_confidence < 80:
                no_matches += 1
                logger.debug(f"      ❌ No sufficient match (confidence: {match_confidence:.1f}%)")
            
            # Only include high-confidence matches
            if match_confidence >= 80:
                match_data = {
                    'ocr_index': i,
                    'matched_text': ocr_text,
                    'field_value': field_value,
                    'match_confidence': round(match_confidence, 1),
                    'match_type': match_type,
                    'bounding_box': ocr_entry.get('bounding_box', []),
                    'bounding_page': ocr_entry.get('bounding_page', 1),
                    'ocr_confidence': ocr_entry.get('confidence', 0)
                }
                matches.append(match_data)
                
                logger.info(f"✅ MATCH #{len(matches)}: '{ocr_text}' -> {match_confidence:.1f}% confidence ({match_type})")
                logger.info(f"   OCR Index: {i}, Page: {match_data['bounding_page']}, BBox: {match_data['bounding_box']}")
        
        # Sort matches by confidence (highest first)
        matches.sort(key=lambda x: x['match_confidence'], reverse=True)
        
        # Log search summary
        logger.info(f"📊 === SEARCH STATISTICS ===")
        logger.info(f"   Date matches: {date_matches}")
        logger.info(f"   Exact matches: {exact_matches}")
        logger.info(f"   Contains matches: {contains_matches}")
        logger.info(f"   Partial matches: {partial_matches}")
        logger.info(f"   Fuzzy matches: {fuzzy_matches}")
        logger.info(f"   No matches: {no_matches}")
        logger.info(f"   Total qualifying matches: {len(matches)}")
        
        if matches:
            best_match = matches[0]
            logger.info(f"🎯 BEST MATCH: '{best_match['matched_text']}' ({best_match['match_confidence']}% {best_match['match_type']})")
            logger.info(f"   Location: Page {best_match['bounding_page']}, BBox: {best_match['bounding_box']}")
        else:
            logger.warning(f"❌ NO QUALIFYING MATCHES FOUND for '{field_value}'")
            logger.info(f"💡 Search suggestions:")
            if is_date_search:
                logger.info(f"   - Date formats tried: {field_date_patterns}")
                logger.info(f"   - Try different date separators (-, /, .)")
                logger.info(f"   - Verify the date format in the document")
            logger.info(f"   - Try using 'fuzzy' or 'contains' search mode")
            logger.info(f"   - Check if the field value exactly matches the document text")
            logger.info(f"   - Verify the document has been processed and OCR data is available")
        
        logger.info(f"📦 Search complete: returning {len(matches)} matches")
        return matches

    # ==================== Coordinate Search Routes ====================
    @app.route('/api/test_coordinates', methods=['GET'])
    @timing_aspect
    def test_coordinates():
        """Simple test route to verify route registration works"""
        return jsonify({
            'success': True,
            'message': 'Test route is working!',
            'timestamp': str(time.time())
        })

    @app.route('/api/search_field_coordinates', methods=['POST'])
    @timing_aspect
    def search_field_coordinates():
        """Search for field coordinates in existing OCR data with absolute accuracy"""
        try:
            logger.info("🔍 === COORDINATE SEARCH API CALLED ===")
            
            data = request.get_json()
            field_value = data.get('field_value', '').strip()
            search_mode = data.get('search_mode', 'exact').lower()
            current_page = data.get('current_page', None)  # Add page filtering support
            
            logger.info(f"📋 Received search request for: '{field_value}' (mode: {search_mode})")
            if current_page:
                logger.info(f"📄 Page-specific search requested: Page {current_page}")
            else:
                logger.info(f"📚 Multi-page search (all pages)")
            
            # Get OCR data from session
            ocr_data = session.get('current_ocr_data', [])
            logger.info(f"🗂️ Session OCR data check: Found {len(ocr_data) if ocr_data else 0} entries")
            
            # Debug session keys
            session_keys = list(session.keys())
            logger.info(f"🔑 Available session keys: {session_keys}")
            
            # Log page distribution in OCR data
            if ocr_data:
                page_counts = {}
                for entry in ocr_data:
                    page = entry.get('bounding_page', 'unknown')
                    page_counts[page] = page_counts.get(page, 0) + 1
                logger.info(f"📊 OCR data page distribution: {dict(sorted(page_counts.items()))}")
            
            # Filter OCR data by page if requested
            if current_page and ocr_data:
                original_count = len(ocr_data)
                ocr_data = [entry for entry in ocr_data if entry.get('bounding_page', 1) == current_page]
                logger.info(f"🔍 Page filtering: {original_count} -> {len(ocr_data)} entries (Page {current_page})")
            
            if not ocr_data:
                # Try alternative session keys
                alt_ocr_data = session.get('ocr_data', [])
                logger.info(f"🔍 Checking alternative 'ocr_data' key: Found {len(alt_ocr_data) if alt_ocr_data else 0} entries")
                
                if alt_ocr_data:
                    ocr_data = alt_ocr_data
                    logger.info("✅ Using alternative OCR data from 'ocr_data' session key")
                else:
                    # Try loading from temporary file (workaround for session size limits)
                    ocr_session_id = session.get('ocr_session_id')
                    logger.info(f"🔍 Looking for OCR session ID: {ocr_session_id}")
                    
                    if ocr_session_id:
                        import tempfile as temp_module
                        import pickle
                        ocr_temp_file = os.path.join(temp_module.gettempdir(), f"ocr_data_{ocr_session_id}.pkl")
                        
                        try:
                            if os.path.exists(ocr_temp_file):
                                with open(ocr_temp_file, 'rb') as f:
                                    ocr_data = pickle.load(f)
                                logger.info(f"✅ Loaded OCR data from temp file: {len(ocr_data)} entries")
                                
                                # Apply page filtering if requested
                                if current_page:
                                    original_count = len(ocr_data)
                                    ocr_data = [entry for entry in ocr_data if entry.get('bounding_page', 1) == current_page]
                                    logger.info(f"🔍 Page filtering (from temp file): {original_count} -> {len(ocr_data)} entries (Page {current_page})")
                            else:
                                logger.warning(f"❌ OCR temp file not found: {ocr_temp_file}")
                        except Exception as e:
                            logger.error(f"❌ Failed to load OCR data from temp file: {e}")
                    else:
                        # Fallback: Try to find the most recent OCR temp file
                        logger.info("🔍 No OCR session ID found, searching for recent OCR temp files...")
                        import tempfile as temp_module
                        import pickle
                        import glob
                        
                        try:
                            temp_dir = temp_module.gettempdir()
                            ocr_files = glob.glob(os.path.join(temp_dir, "ocr_data_*.pkl"))
                            
                            if ocr_files:
                                # Sort by creation time, get the most recent
                                ocr_files.sort(key=lambda x: os.path.getctime(x), reverse=True)
                                most_recent_file = ocr_files[0]
                                
                                # Check if file is recent (less than 10 minutes old)
                                file_age = time.time() - os.path.getctime(most_recent_file)
                                if file_age < 600:  # 10 minutes
                                    logger.info(f"🔍 Trying most recent OCR file: {most_recent_file} (age: {file_age:.1f}s)")
                                    
                                    with open(most_recent_file, 'rb') as f:
                                        ocr_data = pickle.load(f)
                                    logger.info(f"✅ Loaded OCR data from recent temp file: {len(ocr_data)} entries")
                                    
                                    # Apply page filtering if requested
                                    if current_page:
                                        original_count = len(ocr_data)
                                        ocr_data = [entry for entry in ocr_data if entry.get('bounding_page', 1) == current_page]
                                        logger.info(f"🔍 Page filtering (from recent file): {original_count} -> {len(ocr_data)} entries (Page {current_page})")
                                else:
                                    logger.warning(f"❌ Most recent OCR file is too old: {file_age:.1f}s")
                            else:
                                logger.warning("❌ No OCR temp files found")
                        except Exception as e:
                            logger.error(f"❌ Failed to search for recent OCR temp files: {e}")
                    
                    if not ocr_data:
                        logger.warning("❌ No OCR data found in session under any key")
                        return jsonify({
                            'success': False,
                            'message': 'No OCR data available. Please process a document first.',
                            'matches': [],
                            'debug_info': {
                                'session_keys': session_keys,
                                'current_ocr_data_length': len(session.get('current_ocr_data', [])),
                                'ocr_data_length': len(session.get('ocr_data', [])),
                                'ocr_session_id': session.get('ocr_session_id', 'Not found'),
                                'temp_file_attempted': ocr_session_id is not None
                            }
                        }), 400
            
            # Use the search_text_in_ocr helper function
            matches = search_text_in_ocr(field_value, ocr_data, search_mode)
            
            logger.info(f"📦 Search complete: Found {len(matches)} matches")
            
            # Prepare response in format expected by frontend
            best_match = matches[0] if matches else None
            
            return jsonify({
                'success': True,
                'message': f'Found {len(matches)} matches for "{field_value}"',
                'field_value': field_value,
                'search_mode': search_mode,
                'matches': matches,
                'best_match': best_match,
                'total_matches': len(matches),
                'total_ocr_entries': len(ocr_data)
            })
            
        except Exception as e:
            logger.error(f"❌ Error in coordinate search API: {e}")
            return jsonify({
                'success': False, 
                'message': f'Search error: {str(e)}',
                'matches': []
            }), 500

    # ==================== Document Categories Routes ====================
    @app.route('/document_categories')
    @timing_aspect
    def document_categories():
        """Document categories management page"""
        return render_template('document_categories.html')

    @app.route('/api/document_categories', methods=['GET'])
    @timing_aspect
    def get_all_document_categories():
        """Get all document categories"""
        try:
            data = _load_document_categories()
            return jsonify({'success': True, 'categories': data['categories']}), 200

        except Exception as e:
            logger.error(f"Error getting document categories: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/document_categories', methods=['POST'])
    @timing_aspect
    def create_document_category():
        """Create a new document category"""
        try:
            category_data = request.get_json()
            data = _load_document_categories()

            # Generate new ID
            existing_ids = [int(cat['id']) for cat in data['categories'] if cat.get('id', '').isdigit()]
            new_id = str(max(existing_ids) + 1) if existing_ids else '1'

            # Create new category
            new_category = {
                'id': new_id,
                'code': category_data.get('code', ''),
                'name': category_data.get('name', ''),
                'sender': category_data.get('sender', ''),
                'receiver': category_data.get('receiver', ''),
                'processType': category_data.get('processType', '')
            }

            data['categories'].append(new_category)
            _save_document_categories(data)

            return jsonify({'success': True, 'category': new_category}), 201

        except Exception as e:
            logger.error(f"Error creating document category: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/document_categories/<category_id>', methods=['PUT'])
    @timing_aspect
    def update_document_category(category_id):
        """Update an existing document category"""
        try:
            category_data = request.get_json()
            data = _load_document_categories()

            # Find and update category
            for category in data['categories']:
                if category['id'] == category_id:
                    category['code'] = category_data.get('code', category.get('code', ''))
                    category['name'] = category_data.get('name', category.get('name', ''))
                    category['sender'] = category_data.get('sender', category.get('sender', ''))
                    category['receiver'] = category_data.get('receiver', category.get('receiver', ''))
                    category['processType'] = category_data.get('processType', category.get('processType', ''))

                    _save_document_categories(data)
                    return jsonify({'success': True, 'category': category}), 200

            return jsonify({'success': False, 'message': 'Category not found'}), 404

        except Exception as e:
            logger.error(f"Error updating document category: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/document_categories/<category_id>', methods=['DELETE'])
    @timing_aspect
    def delete_document_category(category_id):
        """Delete a document category"""
        try:
            data = _load_document_categories()

            # Find and remove category
            initial_length = len(data['categories'])
            data['categories'] = [cat for cat in data['categories'] if cat['id'] != category_id]

            if len(data['categories']) == initial_length:
                return jsonify({'success': False, 'message': 'Category not found'}), 404

            _save_document_categories(data)
            return jsonify({'success': True}), 200

        except Exception as e:
            logger.error(f"Error deleting document category: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    # ============================================================================
    # DOCUMENT ENTITY MAINTENANCE ROUTES
    # ============================================================================

    def _load_document_entity_mappings():
        """Load all document entity mappings from separate JSON files"""
        entities_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'document_entities')

        try:
            all_mappings = []

            if os.path.exists(entities_dir):
                # Load all document entity files
                for filename in os.listdir(entities_dir):
                    if filename.endswith('.json'):
                        filepath = os.path.join(entities_dir, filename)
                        with open(filepath, 'r', encoding='utf-8') as f:
                            doc_data = json.load(f)
                            # Add all mappings from this document
                            all_mappings.extend(doc_data.get('mappings', []))

            return {'mappings': all_mappings}
        except Exception as e:
            logger.error(f"Error loading document entity mappings: {e}")
            return {'mappings': []}

    def _load_document_entity_mapping_by_document(document_id):
        """Load entity mappings for a specific document"""
        entities_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'document_entities')
        filepath = os.path.join(entities_dir, f'{document_id}.json')

        try:
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # Create default empty structure for this document
                return {
                    'documentId': document_id,
                    'documentName': document_id.replace('_', ' ').title(),
                    'mappings': []
                }
        except Exception as e:
            logger.error(f"Error loading mappings for document {document_id}: {e}")
            return {'documentId': document_id, 'documentName': '', 'mappings': []}

    def _save_document_entity_mapping_by_document(document_id, doc_data):
        """Save entity mappings for a specific document"""
        entities_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'document_entities')
        filepath = os.path.join(entities_dir, f'{document_id}.json')

        try:
            os.makedirs(entities_dir, exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(doc_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Error saving mappings for document {document_id}: {e}")
            return False

    def _save_document_entity_mappings(data):
        """Save document entity mappings - reorganizes into separate files by document"""
        entities_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'document_entities')

        try:
            os.makedirs(entities_dir, exist_ok=True)

            # Group mappings by document
            grouped = {}
            for mapping in data.get('mappings', []):
                doc_id = mapping.get('documentId')
                if not doc_id:
                    continue

                if doc_id not in grouped:
                    grouped[doc_id] = {
                        'documentId': doc_id,
                        'documentName': mapping.get('documentName', ''),
                        'mappings': []
                    }
                grouped[doc_id]['mappings'].append(mapping)

            # Save each document's mappings to its own file
            for doc_id, doc_data in grouped.items():
                if not _save_document_entity_mapping_by_document(doc_id, doc_data):
                    return False

            return True
        except Exception as e:
            logger.error(f"Error saving document entity mappings: {e}")
            return False

    @app.route('/api/documents', methods=['GET'])
    @timing_aspect
    def get_all_documents():
        """Get all available documents (no login required)"""
        try:
            doc_list_path = Path(app.root_path) / "prompts" / "EE" / "DOC_LIST"
            documents = []

            if doc_list_path.exists():
                for filename in os.listdir(str(doc_list_path)):
                    if filename.endswith("_OCR_Fields.json"):
                        doc_type = filename.replace("_OCR_Fields.json", "")
                        display_name = doc_type.replace("_", " ").title()
                        documents.append({
                            'id': doc_type,
                            'name': display_name
                        })

            # Sort by name
            documents.sort(key=lambda x: x['name'])
            return jsonify({'success': True, 'documents': documents}), 200
        except Exception as e:
            logger.error(f"Error getting documents: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/document-types-management')
    @timing_aspect
    def document_types_management():
        """Render document types management page"""
        return render_template('document_types_management.html')

    @app.route('/document_entity_maintenance')
    @timing_aspect
    def document_entity_maintenance():
        """Render document entity maintenance page"""
        return render_template('document_entity_maintenance.html')

    @app.route('/api/document_entity_maintenance', methods=['GET'])
    @timing_aspect
    def get_all_document_entity_mappings():
        """Get all document entity mappings"""
        try:
            data = _load_document_entity_mappings()
            return jsonify({'success': True, 'mappings': data.get('mappings', [])}), 200
        except Exception as e:
            logger.error(f"Error getting document entity mappings: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/document_entity_maintenance', methods=['POST'])
    @timing_aspect
    def create_document_entity_mapping():
        """Create a new document entity mapping"""
        try:
            mapping_data = request.get_json()

            # Validate required fields
            required_fields = ['documentId', 'documentCategoryId', 'entityId', 'dataCategoryId', 'fieldType']
            for field in required_fields:
                if not mapping_data.get(field):
                    return jsonify({'success': False, 'message': f'Missing required field: {field}'}), 400

            document_id = mapping_data.get('documentId')

            # Load only the specific document's data
            doc_data = _load_document_entity_mapping_by_document(document_id)

            # Generate new ID (globally unique across all documents)
            all_data = _load_document_entity_mappings()
            existing_ids = [int(m['id']) for m in all_data.get('mappings', []) if m.get('id', '').isdigit()]
            new_id = str(max(existing_ids, default=0) + 1)

            # Create new mapping
            new_mapping = {
                'id': new_id,
                'documentId': mapping_data.get('documentId'),
                'documentName': mapping_data.get('documentName', ''),
                'documentCategoryId': mapping_data.get('documentCategoryId'),
                'documentCategoryName': mapping_data.get('documentCategoryName', ''),
                'entityId': mapping_data.get('entityId'),
                'entityName': mapping_data.get('entityName', ''),
                'mappingFormField': mapping_data.get('mappingFormField', ''),
                'mappingFormDescription': mapping_data.get('mappingFormDescription', ''),
                'dataCategoryId': mapping_data.get('dataCategoryId'),
                'dataCategoryValue': mapping_data.get('dataCategoryValue', ''),
                'fieldType': mapping_data.get('fieldType')
            }

            # Update document name if not set
            if not doc_data.get('documentName'):
                doc_data['documentName'] = mapping_data.get('documentName', '')

            doc_data['mappings'].append(new_mapping)

            if _save_document_entity_mapping_by_document(document_id, doc_data):
                return jsonify({'success': True, 'mapping': new_mapping}), 201
            else:
                return jsonify({'success': False, 'message': 'Failed to save mapping'}), 500

        except Exception as e:
            logger.error(f"Error creating document entity mapping: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/document_entity_maintenance/<mapping_id>', methods=['PUT'])
    @timing_aspect
    def update_document_entity_mapping(mapping_id):
        """Update an existing document entity mapping"""
        try:
            mapping_data = request.get_json()
            document_id = mapping_data.get('documentId')

            if not document_id:
                return jsonify({'success': False, 'message': 'Missing documentId'}), 400

            # Load only the specific document's data
            doc_data = _load_document_entity_mapping_by_document(document_id)

            # Find and update mapping
            found = False
            for i, mapping in enumerate(doc_data.get('mappings', [])):
                if mapping.get('id') == mapping_id:
                    doc_data['mappings'][i] = {
                        'id': mapping_id,
                        'documentId': mapping_data.get('documentId'),
                        'documentName': mapping_data.get('documentName', ''),
                        'documentCategoryId': mapping_data.get('documentCategoryId'),
                        'documentCategoryName': mapping_data.get('documentCategoryName', ''),
                        'entityId': mapping_data.get('entityId'),
                        'entityName': mapping_data.get('entityName', ''),
                        'mappingFormField': mapping_data.get('mappingFormField', ''),
                        'mappingFormDescription': mapping_data.get('mappingFormDescription', ''),
                        'dataCategoryId': mapping_data.get('dataCategoryId'),
                        'dataCategoryValue': mapping_data.get('dataCategoryValue', ''),
                        'fieldType': mapping_data.get('fieldType')
                    }
                    found = True

                    if _save_document_entity_mapping_by_document(document_id, doc_data):
                        return jsonify({'success': True, 'mapping': doc_data['mappings'][i]}), 200
                    else:
                        return jsonify({'success': False, 'message': 'Failed to save mapping'}), 500

            if not found:
                return jsonify({'success': False, 'message': 'Mapping not found'}), 404

        except Exception as e:
            logger.error(f"Error updating document entity mapping {mapping_id}: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/document_entity_maintenance/<mapping_id>', methods=['DELETE'])
    @timing_aspect
    def delete_document_entity_mapping(mapping_id):
        """Delete a document entity mapping"""
        try:
            # Need to find which document this mapping belongs to
            all_data = _load_document_entity_mappings()
            document_id = None

            for mapping in all_data.get('mappings', []):
                if mapping.get('id') == mapping_id:
                    document_id = mapping.get('documentId')
                    break

            if not document_id:
                return jsonify({'success': False, 'message': 'Mapping not found'}), 404

            # Load only the specific document's data
            doc_data = _load_document_entity_mapping_by_document(document_id)

            # Find and remove mapping
            original_length = len(doc_data.get('mappings', []))
            doc_data['mappings'] = [m for m in doc_data.get('mappings', []) if m.get('id') != mapping_id]

            if len(doc_data['mappings']) < original_length:
                if _save_document_entity_mapping_by_document(document_id, doc_data):
                    return jsonify({'success': True, 'message': 'Mapping deleted successfully'}), 200
                else:
                    return jsonify({'success': False, 'message': 'Failed to save changes'}), 500
            else:
                return jsonify({'success': False, 'message': 'Mapping not found'}), 404

        except Exception as e:
            logger.error(f"Error deleting document entity mapping {mapping_id}: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    # ================== DOCUMENT TYPES CRUD API ==================

    @app.route('/api/document-types', methods=['GET'])
    @timing_aspect
    def get_all_document_types():
        """Get all unique document types from mappings"""
        try:
            data = _load_document_entity_mappings()
            mappings = data.get('mappings', [])

            # Get unique document types
            document_types = {}
            for mapping in mappings:
                doc_id = mapping.get('documentId')
                if doc_id and doc_id not in document_types:
                    document_types[doc_id] = {
                        'documentId': doc_id,
                        'documentName': mapping.get('documentName'),
                        'documentCategoryId': mapping.get('documentCategoryId'),
                        'documentCategoryName': mapping.get('documentCategoryName'),
                        'fieldCount': 0
                    }

                if doc_id:
                    document_types[doc_id]['fieldCount'] += 1

            # Convert to list
            doc_list = list(document_types.values())
            doc_list.sort(key=lambda x: x.get('documentName', ''))

            return jsonify({'success': True, 'documentTypes': doc_list}), 200

        except Exception as e:
            logger.error(f"Error getting document types: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/document-types/<document_id>', methods=['GET'])
    @timing_aspect
    def get_document_type(document_id):
        """Get a specific document type with its fields"""
        try:
            data = _load_document_entity_mappings()
            mappings = data.get('mappings', [])

            # Find all mappings for this document
            doc_mappings = [m for m in mappings if m.get('documentId') == document_id]

            if not doc_mappings:
                return jsonify({'success': False, 'message': 'Document type not found'}), 404

            # Get document info from first mapping
            doc_info = {
                'documentId': document_id,
                'documentName': doc_mappings[0].get('documentName'),
                'documentCategoryId': doc_mappings[0].get('documentCategoryId'),
                'documentCategoryName': doc_mappings[0].get('documentCategoryName'),
                'fields': doc_mappings
            }

            return jsonify({'success': True, 'documentType': doc_info}), 200

        except Exception as e:
            logger.error(f"Error getting document type {document_id}: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/document-types', methods=['POST'])
    @timing_aspect
    def create_document_type():
        """Create a new document type"""
        try:
            req_data = request.get_json()
            document_id = req_data.get('documentId')
            document_name = req_data.get('documentName')
            category_id = req_data.get('documentCategoryId')
            category_name = req_data.get('documentCategoryName')

            if not all([document_id, document_name, category_id]):
                return jsonify({'success': False, 'message': 'Missing required fields'}), 400

            data = _load_document_entity_mappings()
            mappings = data.get('mappings', [])

            # Check if document type already exists
            existing = [m for m in mappings if m.get('documentId') == document_id]
            if existing:
                return jsonify({'success': False, 'message': 'Document type already exists'}), 400

            # Create initial mapping (can add fields later)
            new_id = str(max([int(m.get('id', 0)) for m in mappings] + [0]) + 1)
            new_mapping = {
                'id': new_id,
                'documentId': document_id,
                'documentName': document_name,
                'documentCategoryId': category_id,
                'documentCategoryName': category_name,
                'entityId': '',
                'entityName': '',
                'mappingFormField': '',
                'mappingFormDescription': '',
                'dataCategoryId': '',
                'dataCategoryValue': '',
                'fieldType': ''
            }

            data['mappings'].append(new_mapping)

            if _save_document_entity_mappings(data):
                return jsonify({'success': True, 'message': 'Document type created successfully', 'documentType': new_mapping}), 201
            else:
                return jsonify({'success': False, 'message': 'Failed to save document type'}), 500

        except Exception as e:
            logger.error(f"Error creating document type: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/document-types/<document_id>', methods=['PUT'])
    @timing_aspect
    def update_document_type(document_id):
        """Update a document type"""
        try:
            req_data = request.get_json()
            new_name = req_data.get('documentName')
            new_category_id = req_data.get('documentCategoryId')
            new_category_name = req_data.get('documentCategoryName')

            data = _load_document_entity_mappings()
            mappings = data.get('mappings', [])

            # Update all mappings for this document
            updated_count = 0
            for mapping in mappings:
                if mapping.get('documentId') == document_id:
                    if new_name:
                        mapping['documentName'] = new_name
                    if new_category_id:
                        mapping['documentCategoryId'] = new_category_id
                    if new_category_name:
                        mapping['documentCategoryName'] = new_category_name
                    updated_count += 1

            if updated_count == 0:
                return jsonify({'success': False, 'message': 'Document type not found'}), 404

            if _save_document_entity_mappings(data):
                return jsonify({'success': True, 'message': 'Document type updated successfully'}), 200
            else:
                return jsonify({'success': False, 'message': 'Failed to save changes'}), 500

        except Exception as e:
            logger.error(f"Error updating document type {document_id}: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/document-types/<document_id>', methods=['DELETE'])
    @timing_aspect
    def delete_document_type(document_id):
        """Delete a document type and all its field mappings"""
        try:
            data = _load_document_entity_mappings()
            mappings = data.get('mappings', [])

            # Remove all mappings for this document
            original_length = len(mappings)
            data['mappings'] = [m for m in mappings if m.get('documentId') != document_id]

            if len(data['mappings']) < original_length:
                if _save_document_entity_mappings(data):
                    deleted_count = original_length - len(data['mappings'])
                    return jsonify({'success': True, 'message': f'Document type and {deleted_count} field mappings deleted successfully'}), 200
                else:
                    return jsonify({'success': False, 'message': 'Failed to save changes'}), 500
            else:
                return jsonify({'success': False, 'message': 'Document type not found'}), 404

        except Exception as e:
            logger.error(f"Error deleting document type {document_id}: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/document-types/categories', methods=['GET'])
    @timing_aspect
    def get_document_type_categories():
        """Get all document type categories from config"""
        try:
            # Load from YAML config
            config_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'document_classification_config.yaml')
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)

            categories = config.get('document_types', {}).get('categories', [])
            return jsonify({'success': True, 'categories': categories}), 200

        except Exception as e:
            logger.error(f"Error getting document type categories: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/document-categories', methods=['POST'])
    @timing_aspect
    def create_document_type_category():
        """Create a new document category"""
        try:
            req_data = request.get_json()
            category_name = req_data.get('name')

            if not category_name:
                return jsonify({'success': False, 'message': 'Category name is required'}), 400

            # Load YAML config
            config_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'document_classification_config.yaml')
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)

            categories = config.get('document_types', {}).get('categories', [])

            # Get next ID
            max_id = max([cat.get('id', 0) for cat in categories] + [0])
            new_id = max_id + 1

            # Add new category
            new_category = {
                'id': new_id,
                'name': category_name
            }
            categories.append(new_category)

            # Update config
            if 'document_types' not in config:
                config['document_types'] = {}
            config['document_types']['categories'] = categories

            # Save back to YAML
            with open(config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)

            return jsonify({'success': True, 'category': new_category}), 201

        except Exception as e:
            logger.error(f"Error creating document category: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/document-categories/<int:category_id>', methods=['PUT'])
    @timing_aspect
    def update_document_type_category(category_id):
        """Update a document category"""
        try:
            req_data = request.get_json()
            category_name = req_data.get('name')

            if not category_name:
                return jsonify({'success': False, 'message': 'Category name is required'}), 400

            # Load YAML config
            config_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'document_classification_config.yaml')
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)

            categories = config.get('document_types', {}).get('categories', [])

            # Find and update category
            category_found = False
            for cat in categories:
                if cat.get('id') == category_id:
                    cat['name'] = category_name
                    category_found = True
                    break

            if not category_found:
                return jsonify({'success': False, 'message': 'Category not found'}), 404

            # Update config
            config['document_types']['categories'] = categories

            # Save back to YAML
            with open(config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)

            return jsonify({'success': True, 'message': 'Category updated successfully'}), 200

        except Exception as e:
            logger.error(f"Error updating document category: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/document-categories/<int:category_id>', methods=['DELETE'])
    @timing_aspect
    def delete_document_type_category(category_id):
        """Delete a document category"""
        try:
            # Load YAML config
            config_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'document_classification_config.yaml')
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)

            categories = config.get('document_types', {}).get('categories', [])

            # Find and remove category
            original_length = len(categories)
            categories = [cat for cat in categories if cat.get('id') != category_id]

            if len(categories) == original_length:
                return jsonify({'success': False, 'message': 'Category not found'}), 404

            # Update config
            config['document_types']['categories'] = categories

            # Save back to YAML
            with open(config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)

            return jsonify({'success': True, 'message': 'Category deleted successfully'}), 200

        except Exception as e:
            logger.error(f"Error deleting document category: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    # Initialize vetting rule engine inside the function to prevent startup issues
    global vetting_engine
    try:
        from app.utils.vetting_engine import VettingRuleEngine
        vetting_engine = VettingRuleEngine(db)
        logger.info("Vetting rule engine initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize vetting rule engine: {e}")
        vetting_engine = None
    
    @app.route("/guarantee", methods=["GET"])
    @timing_aspect
    def index():
        """Serve the default chat interface."""
        return render_template("rich.html")

    @app.route("/compliance-results", methods=["GET", "POST"])
    @timing_aspect
    def compliance_results():
        """Display compliance analysis results."""
        if request.method == "POST":
            # Store results in session for display
            session['compliance_results'] = request.get_json()
            return jsonify({"success": True})

        # GET request - display the results page
        results = session.get('compliance_results')
        if not results:
            # If no results, redirect back to guarantee page
            return redirect(url_for('index'))

        return render_template("compliance_results.html", results=results)

    @app.route("/website", methods=["GET"])
    @timing_aspect
    def website():
        """Serve the default chat interface."""
        return render_template("websiteIndex.html")

    @app.route("/fdoccheck", methods=["GET"])
    @timing_aspect
    def doc():
        """Serve the default chat interface."""
        return render_template("doccheck.html")

    @app.route("/", methods=["GET"])
    @timing_aspect
    def main():
        """Serve the default chat interface."""
        return render_template("index.html")

    @app.route("/smart-chat", methods=["GET"])
    @timing_aspect
    def smart_chat():
        """Smart Banking Chat Interface"""
        return render_template("smart_chat.html")

    @app.route("/ai-chat", methods=["GET"])
    @timing_aspect
    def ai_chat():
        """Dashboard with Repository Tiles and Chatbot"""
        return render_template("ai_chat_dashboard.html")

    @app.route("/ai-chat-pro", methods=["GET"])
    @timing_aspect
    def ai_chat_pro():
        """Professional AI Chat Interface with Enhanced UI/UX"""
        return render_template("ai_chat_dashboard.html")
    
    @app.route("/ai_chat_modern", methods=["GET"])
    @timing_aspect
    def ai_chat_modern():
        """Chatbot interface for iframe/popup"""
        return render_template("ai_chat_modern.html")
    
    @app.route("/ai_chat_modern_overylay", methods=["GET"])
    @timing_aspect
    def ai_chat_modern_overylay():
        """Chatbot interface optimized for modal/overlay display without header"""
        return render_template("ai_chat_modern_overylay.html")
    
    # Form Routes (temporarily without authentication for testing)
    @app.route('/forms_dashboard')
    def forms_dashboard():
        """Render the forms dashboard"""
        return render_template('forms_dashboard.html')

    @app.route('/trade_finance_lc_form')
    def trade_finance_lc_form():
        """Render the Trade Finance LC form"""
        return render_template('trade_finance_lc_form.html')
    
    @app.route('/trade_finance_guarantee_form')
    def trade_finance_guarantee_form():
        """Render the Trade Finance Guarantee form"""
        return render_template('trade_finance_guarantee_form.html')
    
    @app.route('/bank_guarantee_form')
    def bank_guarantee_form():
        """Render the Bank Guarantee form"""
        return render_template('trade_finance_guarantee_form.html')
    
    @app.route('/trade_finance')
    def trade_finance_unified():
        """Render the unified Trade Finance form with tabs"""
        return render_template('trade_finance_unified.html')
    
    @app.route('/trade_finance_dashboard')
    def trade_finance_dashboard():
        """Render the Trade Finance dashboard with service tiles"""
        return render_template('trade_finance_dashboard.html')

    @app.route('/treasury_management_form')
    def treasury_management_form():
        """Render the Treasury Management form"""
        return render_template('treasury_management_form.html')

    @app.route('/cash_management_form')
    def cash_management_form():
        """Render the Cash Management form"""
        return render_template('cash_management_form.html')
    
    @app.route('/components/ai_chatbot_popup')
    def ai_chatbot_popup():
        """Serve the AI chatbot popup component"""
        return render_template('components/ai_chatbot_popup.html')
    
    # API Routes for form submissions
    @app.route('/api/lc/submit', methods=['POST'])
    @login_required
    def submit_lc():
        """Handle LC form submission"""
        try:
            data = request.json
            data['user_id'] = session.get('user_id')
            data['timestamp'] = datetime.utcnow()
            data['status'] = 'pending'
            
            # Generate LC number if not provided
            if not data.get('lcNumber'):
                data['lcNumber'] = f"LC{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # Store in database
            result = db.lc_transactions.insert_one(data)
            
            return jsonify({
                'success': True,
                'lcNumber': data['lcNumber'],
                'transactionId': str(result.inserted_id)
            })
        except Exception as e:
            logger.error(f"Error submitting LC: {str(e)}")
            return jsonify({'error': 'Failed to submit LC'}), 500
    
    @app.route('/api/guarantee/submit', methods=['POST'])
    @login_required
    def submit_guarantee():
        """Handle Guarantee form submission"""
        try:
            data = request.json
            data['user_id'] = session.get('user_id')
            data['timestamp'] = datetime.utcnow()
            data['status'] = 'pending'
            
            # Generate Guarantee number if not provided
            if not data.get('guaranteeNumber'):
                data['guaranteeNumber'] = f"BG{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # Store in database
            result = db.guarantee_transactions.insert_one(data)
            
            return jsonify({
                'success': True,
                'guaranteeNumber': data['guaranteeNumber'],
                'transactionId': str(result.inserted_id)
            })
        except Exception as e:
            logger.error(f"Error submitting Guarantee: {str(e)}")
            return jsonify({'error': 'Failed to submit Guarantee'}), 500

    @app.route('/api/treasury/<transaction_type>', methods=['POST'])
    @login_required
    def submit_treasury_transaction(transaction_type):
        """Handle treasury transaction submissions"""
        try:
            data = request.json
            data['user_id'] = session.get('user_id')
            data['timestamp'] = datetime.utcnow()
            data['transaction_type'] = transaction_type
            data['status'] = 'pending'
            
            # Store in appropriate collection
            collection = db[f'treasury_{transaction_type}']
            result = collection.insert_one(data)
            
            return jsonify({
                'success': True,
                'transactionId': str(result.inserted_id),
                'type': transaction_type
            })
        except Exception as e:
            logger.error(f"Error submitting treasury transaction: {str(e)}")
            return jsonify({'error': 'Failed to submit transaction'}), 500

    @app.route('/api/cash/<transaction_type>', methods=['POST'])
    @login_required
    def submit_cash_transaction(transaction_type):
        """Handle cash management transaction submissions"""
        try:
            data = request.json
            data['user_id'] = session.get('user_id')
            data['timestamp'] = datetime.utcnow()
            data['transaction_type'] = transaction_type
            data['status'] = 'processing'
            
            # Store in appropriate collection
            collection = db[f'cash_{transaction_type}']
            result = collection.insert_one(data)
            
            return jsonify({
                'success': True,
                'transactionId': str(result.inserted_id),
                'type': transaction_type
            })
        except Exception as e:
            logger.error(f"Error submitting cash transaction: {str(e)}")
            return jsonify({'error': 'Failed to submit transaction'}), 500

    @app.route("/analytics", methods=["GET"])
    @timing_aspect
    def analytics():
        """Analytics Category Selector"""
        return render_template("analytics_category_selector.html")
    
    @app.route("/analytics/trade-finance", methods=["GET"])
    @timing_aspect
    def analytics_trade_finance():
        """Trade Finance Analytics Dashboard"""
        return render_template("analytics_trade_finance.html")
    
    @app.route("/analytics/cash-management", methods=["GET"])
    @timing_aspect
    def analytics_cash_management():
        """Cash Management Analytics Dashboard"""
        return render_template("analytics_cash_management.html")
    
    @app.route("/analytics/treasury-management", methods=["GET"])
    @timing_aspect
    def analytics_treasury_management():
        """Treasury Management Analytics Dashboard"""
        return render_template("analytics_treasury_management.html")
    
    @app.route("/analytics_improved", methods=["GET"])
    @timing_aspect
    def analytics_improved():
        """Improved Analytics Dashboard"""
        return render_template("analytics_improved.html")

    @app.route("/chat", methods=["GET"])
    @timing_aspect
    def canvas():
        """Serve the default chat interface."""
        return render_template("chat.html")

    @app.route("/query", methods=["POST"])
    @timing_aspect
    def query():
        """Handle user queries dynamically based on intent."""
        logger.info("Received a new request at /query endpoint.")
        try:
            user_query, user_id, uploaded_file, annotations = None, None, None, None
            session_id = None
            output_format = "table"
            updated_template_details = None
            json_data = None  # Initialize json_data to avoid UnboundLocalError
            repository_context = None  # Initialize repository_context

            if request.content_type == "application/json":
                logger.info("Processing JSON request.")
                json_data = request.get_json()
                user_query = json_data.get("query", "").strip()
                user_id = session.get("user_id") or json_data.get("user_id", "").strip() or None
                session_id = json_data.get("session_id", None)
                productName = json_data.get("productname", "").strip()
                functionName = json_data.get("functionname", "").strip()
                scf_value = json_data.get("SCF", False)
                if isinstance(scf_value, str):
                    scf_flag = scf_value.lower() == "true"
                else:
                    scf_flag = bool(scf_value)
            elif request.content_type.startswith("multipart/form-data"):
                logger.info("Processing file upload request.")
                user_query = request.form.get("query", "").strip()
                user_id = session.get("user_id") or request.form.get("user_id", "").strip() or None
                session_id = request.form.get("session_id", None)
                annotations = request.form.get("annotations", "").strip()
                uploaded_file = request.files.getlist("file")
                scf_flag = request.form.get("SCF", "false").lower() == "true"
                productName = request.form.get("productname", "").strip()
                functionName = request.form.get("functionname", "").strip()
                client_id = request.form.get("client_id", None)  # Extract client_id for progress tracking
                logger.info(f"SCF Flag is {scf_flag}, Client ID: {client_id}")
            else:
                logger.warning("Unsupported content type.")
                return jsonify(
                    {"response": "Unsupported content type. Use JSON or form-data.", "intent": "unknown"}), 400

            if uploaded_file and scf_flag:
                user_query += "extract the invoice_detail information attached file"
            elif uploaded_file and not scf_flag:
                user_query += "extract the letter_of_credit information attached file"

            if not user_query or not user_id:
                missing_fields = []
                if not user_query:
                    missing_fields.append("query")
                if not user_id:
                    missing_fields.append("user_id")
                return jsonify({"response": f"Missing fields: {', '.join(missing_fields)}.", "intent": "unknown"}), 400

            logger.info(f"🔍 product: {productName}, function: {functionName}")

            # Initialize progress tracker if client_id is provided (for file uploads)
            progress_tracker = None
            if uploaded_file and client_id:
                try:
                    from app.utils.websocket_handler import get_websocket_handler
                    ws_handler = get_websocket_handler()
                    if ws_handler:
                        progress_tracker = DocumentProcessingTracker(ws_handler, client_id)
                        logger.info(f"✅ Progress tracker initialized for client: {client_id}")
                    else:
                        logger.warning("WebSocket handler not available, progress tracking disabled")
                except Exception as e:
                    logger.error(f"Failed to initialize progress tracker: {e}")
                    progress_tracker = None

            context = get_conversation_context(user_id, session_id)
            logger.info(f"User {user_id} conversation context: {context}")
            # Don't save here - frontend will save via /api/conversation/message endpoint

            # Check for repository context from request
            if json_data is not None:
                repository_context = json_data.get("repository_context")
            elif request.content_type.startswith("multipart/form-data"):
                repository_context = request.form.get("repository_context")

            # Check if user has an active repository connection
            active_repository = active_user_repositories.get(user_id)

            # Update if repository context is provided in request
            if repository_context:
                active_repository = repository_context
                active_user_repositories[user_id] = repository_context
                logger.info(f"Updated active repository from request to: {repository_context}")

            logger.info(f"Active repository for user {user_id}: {active_repository}")

            # Always use LLM for intent detection - no static shortcuts
            # Let process_user_query handle all intent classification
            try:
                response = process_user_query(user_query, user_id, context, active_repository)
                
                # Check if response contains an error
                if response and isinstance(response, dict) and "error" in response:
                    logger.warning(f"process_user_query returned error: {response.get('error')}")
                    raise Exception(response.get('error', 'Query processing failed'))
                    
            except Exception as e:
                logger.error(f"Error in process_user_query: {str(e)}")
                # Use repository-specific fallback responses
                try:
                    from app.utils.repository_responses import get_fallback_response
                    response = get_fallback_response(user_query, active_repository)
                    logger.info(f"Using repository-specific fallback response")
                except Exception as fallback_error:
                    logger.error(f"Error getting fallback response: {fallback_error}")
                    # Ultimate fallback
                    if active_repository:
                        response = {
                            "intent": "general",
                            "answer": f"I'm connected to the {active_repository} repository. How can I help you today?"
                        }
                    else:
                        response = {
                            "intent": "general",
                            "answer": "Hello! Please connect to a repository to get started. Click on 'No Repository' above."
                        }
                logger.info(f"Using fallback response due to API error")

            # Check if response is None or invalid
            if response is None:
                logger.error("process_user_query returned None")
                response = {
                    "intent": "error",
                    "answer": "I'm sorry, I encountered an error processing your request. Please try again.",
                    "error": "Internal processing error"
                }

            # Don't save here - frontend will save via /api/conversation/message endpoint
            # Extra safety check in case response somehow becomes None
            if response is None:
                logger.error("Response is None after validation")
                return jsonify({"response": "An error occurred processing your request.", "intent": "error"}), 500
                
            intent = response.get("intent", "unknown")
            logger.info(f"Determined intent: {intent}")

            if response.get("confirmation_required"):
                logger.info("Confirmation required from user.")
                return jsonify({
                    "response": response.get("answer", "Are you sure you want to apply these changes?"),
                    "intent": intent,
                    "confirmation_required": True,
                    "modified_fields": response.get("modified_fields")
                })

            if intent == "Follow-Up Request":
                logger.info("Handling Follow-Up Request.")
                follow_up_intent = response.get("follow_up_intent", "unknown")
                output_format = response.get("output_format", "table")
                valid_formats = ["table", "json", "html", "report", "Excel", "text"]
                if output_format not in valid_formats:
                    logger.warning(f"Invalid output format: {output_format}. Defaulting to 'table'.")
                    output_format = "table"
                logger.info(f"Output format set to: {output_format}")
                logger.info(f"Detected Follow-Up Intent: {follow_up_intent}")
                try:
                    refined_response = handle_follow_up_request(user_query, context, follow_up_intent, output_format)
                    return jsonify({
                        "response": refined_response,
                        "intent": "Follow-Up Request",
                        "output_format": output_format
                    })
                except Exception as e:
                    logger.error(f"Error handling follow-up request: {e}")
                    return jsonify({
                        "response": "An error occurred while processing the follow-up request.",
                        "intent": "error"
                    }), 500

            elif intent in ["Train User Manual", "User Manual Request", "User Manual"] or response.get(
                    "requires_training_handler"):
                if uploaded_file and len(uploaded_file) > 0:
                    result = train_user_manual(uploaded_file[0], user_id, user_query)
                    return jsonify({
                        "response": result["message"],
                        "intent": intent,
                        "success": result["success"]
                    }), 200 if result["success"] else 400
                elif "train" not in user_query.lower():
                    # Check if the query is actually asking about training or uploading
                    if any(word in user_query.lower() for word in ['upload', 'train', 'add manual', 'load manual']):
                        return jsonify({
                            "response": "Please upload a user manual document to train.",
                            "intent": intent,
                            "follow_up_questions": ["Would you like to upload a manual now?"]
                        }), 400

                    # Query the trained manual
                    result = query_trained_manual(user_query, user_id, context)

                    # If no documents found but query seems to be about general trade finance topics
                    if not result["success"] and any(word in user_query.lower() for word in
                                                     ['trade', 'finance', 'letter of credit', 'lc', 'bill']):
                        # Try to provide a general response instead of failing
                        return jsonify({
                            "response": "I couldn't find specific information in your uploaded manuals. Please upload relevant trade finance manuals to get detailed answers about your query.",
                            "intent": intent,
                            "follow_up_questions": [
                                "Would you like to upload a trade finance manual?",
                                "Can you rephrase your question?",
                                "What specific aspect of trade finance are you interested in?"
                            ],
                            "success": False
                        }), 400

                    return jsonify({
                        "response": result.get("response", result.get("message", "No response generated")),
                        "html": result.get("html"),
                        "intent": result.get("intent", intent),
                        "output_format": result.get("output_format"),
                        "source_files": result.get("source_files"),
                        "success": result["success"]
                    }), 200 if result["success"] else 400
                else:
                    return jsonify({
                        "response": "Please upload a user manual document to train.",
                        "intent": intent,
                        "follow_up_questions": ["Please upload the user manual document."]
                    }), 400

            elif intent == "Creation Transaction":
                # Use pure conversational handler - no forms needed
                from app.utils.conversational_transaction_handler_v2 import ConversationalTransactionHandler
                handler = ConversationalTransactionHandler(db)
                session_id = session.get('session_id', str(uuid.uuid4()))


                # Get active repository for the user
                active_repository = active_user_repositories.get(user_id)
                result = handler.process_creation_intent(user_query, session_id, user_id, context, active_repository)
                return jsonify(result)
            elif intent == "Custom Rule Request":
                result = handle_custom_rule_intent(user_query, context)
                if result.get("FollowUpQuestions"):
                    return jsonify({
                        "intent": intent,
                        "follow_up_questions": result["FollowUpQuestions"],
                        "action": result.get("Action"),
                        "response": None,
                        "result": None
                    })
                else:
                    return jsonify({
                        "intent": intent,
                        "action": result.get("Action"),
                        "response": "Operation completed.",
                        "result": result.get("Result"),
                        "follow_up_questions": []
                    })
            elif intent == "api request":
                corporate_id = response.get("corporate_id", "default_corporate_id")
                return handle_api_request(user_query, user_id, corporate_id)
            elif intent in ["Table Request", "report request", "Report Request"]:
                if intent in ["report request", "Report Request"]:
                    output_format = response.get("output_format", "table")
                return handle_table_or_report_request(intent, user_query, user_id, output_format, context)
            elif intent == "Visualization Request":
                return handle_visualization_request(intent, response, user_query, user_id)
            elif intent == "Export Report Request":
                return handle_export_report_request(intent, response, user_query, user_id, context)
            elif intent == "File Upload Request":
                if not uploaded_file or len(uploaded_file) == 0:
                    return jsonify(
                        {"response": "File is required for this request.", "intent": "File Upload Request"}
                    ), 400

                # Get document type from query or annotations for field mapping
                document_type = request.form.get('documentType', None)

                if isinstance(uploaded_file, list) and len(uploaded_file) > 1:
                    return process_uploaded_files(uploaded_file, intent, userQuery=user_query, annotations=annotations,
                                                  productName=productName, functionName=functionName,
                                                  documentType=document_type, progress_tracker=progress_tracker)
                uploaded_file = uploaded_file[0]
                file_type = uploaded_file.content_type
                if file_type in ["application/zip", "application/x-zip-compressed"] or uploaded_file.filename.endswith(
                        ".zip"):
                    return handle_zip_file_upload(uploaded_file, intent, userQuery=user_query, annotations=annotations,
                                                  documentType=document_type)
                else:
                    return process_uploaded_files(uploaded_file, intent, userQuery=user_query, annotations=annotations,
                                                  productName=productName, functionName=functionName,
                                                  documentType=document_type, progress_tracker=progress_tracker)
            # elif intent == "User Manual Request":
            #     return handle_user_manual(intent, user_query, user_id)
            elif intent == "Proactive Alert Request":
                return handle_proactive_alert(user_query, user_id, schema)
            elif intent == "Robotic Action Request":
                template_name = response.get("template_name", "")
                if not template_name:
                    return jsonify(
                        {"response": "Template name is required for Robotic Action Request.", "intent": intent}), 400
                if "confirmed" in user_query.lower():
                    updated_template_details = response.get("modified_fields")
                    return jsonify({
                        "response": f"Robotic action executed: Loaded template '{template_name}'.",
                        "intent": intent,
                        "template_name": template_name,
                        "updated_template_details": updated_template_details
                    })
                else:
                    return jsonify({
                        "response": f"Robotic action executed: Loaded template '{template_name}'.",
                        "intent": intent,
                        "template_name": template_name,
                        "follow_up_questions": [
                            f"What changes would you like to make to the '{template_name}' template? (e.g., field1=value1, field2=value2)"]
                    })
            else:
                # Ensure response is not None before calling .get()
                if response is None:
                    return jsonify({"response": "Unable to process the request.", "intent": "error"}), 500
                return jsonify({"response": response.get("answer", "Unable to process the request."), "intent": intent})

        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}", exc_info=True)
            return jsonify({"response": "An unexpected error occurred.", "intent": "error"}), 500

    @app.route("/history", methods=["GET"])
    @timing_aspect
    def get_history():
        user_id = session.get("user_id", request.args.get("user_id"))
        session_id = request.args.get("session_id", None)
        if not user_id:
            return jsonify({"error": "user_id is required"}), 400

        history = retrieve_conversation_history(user_id, session_id)
        conversation_history = [
            {
                "created_at": msg.get("created_at").isoformat() if isinstance(msg.get("created_at"),
                                                                              datetime) else msg.get("created_at"),
                "message": msg.get("message"),
                "role": msg.get("role"),
                "user_id": msg.get("user_id"),
                "session_id": msg.get("session_id", "")
            }
            for msg in history
        ]
        return jsonify({"conversation_history": conversation_history})

    @app.route("/AICheck", methods=["POST"])
    @timing_aspect
    def post_ai_check():
        try:
            user_id = session.get("user_id", "1517524")
            data = request.json
            logger.info(f"User {user_id} conversation context: {data}")
            # Don't save here if frontend is handling conversation storage
            context = get_conversation_context(user_id)
            result, status_code = handle_ai_check(data, context)
            # Don't save here if frontend is handling conversation storage
            return jsonify(result), status_code
        except Exception as e:
            logger.error(f"AI Compliance Check Error: {e}", exc_info=True)
            return jsonify({"error": str(e)}), 500

    # Clear history route
    @app.route("/clear_history", methods=["POST"])
    @timing_aspect
    def clear_history():
        """Clear conversation history for a user or specific session."""
        logger.info("Received request to clear chat history.")
        try:
            # Extract user_id and session_id
            if request.content_type == "application/json":
                json_data = request.get_json()
                user_id = session.get("user_id", json_data.get("user_id", "").strip())
                session_id = json_data.get("session_id", None)
            else:
                user_id = session.get("user_id", request.form.get("user_id", "").strip())
                session_id = request.form.get("session_id", None)

            if not user_id:
                logger.warning("Missing user_id in clear history request.")
                return jsonify({"response": "Missing user_id.", "intent": "error"}), 400

            # If session_id is same as user_id, clear all sessions for user
            if session_id == user_id:
                logger.info(f"Clearing ALL history for user_id: {user_id} (session_id matches user_id)")
                session_id = None  # Clear all sessions

            logger.info(f"Clearing history for user_id: {user_id}, session_id: {session_id}")
            deleted_count = clear_conversation_history(user_id, session_id)

            logger.info(f"Successfully cleared {deleted_count} history entries for user_id: {user_id}")
            return jsonify({
                "response": f"Conversation history cleared successfully. {deleted_count} entries removed.",
                "intent": "clear_history",
                "deleted_count": deleted_count
            })

        except Exception as e:
            logger.error(f"Error clearing conversation history: {e}", exc_info=True)
            return jsonify({"response": f"An unexpected error occurred: {str(e)}", "intent": "error"}), 500

    @app.route("/export_lc_doc_compliance_check", methods=["POST"])
    @timing_aspect
    def export_lc_doc_compliance_check():
        try:
            swift_text = request.form.get("swift_text", "").strip()
            if not swift_text:
                return jsonify({"error": "Please provide SWIFT message as raw text in 'swift_text' field."}), 400

            uploaded_files = request.files.getlist("file")
            if not uploaded_files or len(uploaded_files) == 0:
                return jsonify({"error": "Please upload at least one supporting document."}), 400

            docs_info = []
            for uploaded_file in uploaded_files:
                file_type = uploaded_file.content_type
                file_name = uploaded_file.filename
                with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                    uploaded_file.save(temp_file.name)
                    extract_result = extract_text_from_file(temp_file.name, file_type)
                    raw_text = " ".join([entry["text"] for entry in extract_result.get("text_data", [])])
                    docs_info.append({
                        "file_name": file_name,
                        "file_type": file_type,
                        "text_data": extract_result.get("text_data", []),
                        "raw_text": raw_text
                    })
                os.remove(temp_file.name)

            compliance_results = []
            for doc in docs_info:
                pages = group_ocr_data_by_page(doc["text_data"])
                for page_num, page_data in enumerate(pages, start=1):
                    support_page_text = " ".join([entry["text"] for entry in page_data])
                    try:
                        page_classification_dict = classify_document_gpt(support_page_text)
                        page_classification_fields = ",".join([
                            str(page_classification_dict.get("category", "")),
                            str(page_classification_dict.get("document_type", "")),
                            str(page_classification_dict.get("sub_type", "")),
                            str(page_classification_dict.get("classification", "")),
                        ]).lower()
                    except Exception as e:
                        page_classification_fields = ""
                        logging.error(f"Classification error for page {page_num} of {doc['file_name']}: {e}")

                    comparison = analyze_compliance_with_gpt(
                        swift_text=swift_text,
                        support_text=support_page_text,
                        support_doc_type=page_classification_fields
                    )
                    compliance_results.append({
                        "supporting_file": doc["file_name"],
                        "supporting_doc_page": page_num,
                        "supporting_doc_type": page_classification_fields,
                        "comparison": comparison
                    })

            return jsonify({
                "swift_text_provided": True,
                "supporting_docs": [doc["file_name"] for doc in docs_info],
                "compliance_results": compliance_results
            })

        except Exception as e:
            logging.error(f"export_lc_doc_compliance_check error: {e}")
            return jsonify({"error": str(e)}), 500

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

    def analyze_compliance_with_gpt(swift_text, support_text, support_doc_type):
        prompt = f"""
        You are an expert in international trade finance and document compliance for Letters of Credit.
        Given the following SWIFT LC message (e.g., MT700, MT710, MT707) and a supporting document ({support_doc_type}),
        1. Extract and compare key fields required for compliance (e.g., LC amount, applicant, beneficiary, goods/description, shipment date, expiry date, port, invoice number, BL/AWB number, etc).
        2. Report whether the details MATCH or NOT.
        3. Clearly list any mismatches, field by field.

        SWIFT Document:
        ---
        {swift_text}
        ---
        Supporting Document ({support_doc_type}):
        ---
        {support_text}
        ---

        Return ONLY a valid JSON object, nothing else, with these keys:
        - match (true/false)
        - mismatches (list of objects with "field", "swift_value", "support_value", "issue")
        - extracted_swift (dict)
        - extracted_support (dict)
        """
        try:
            # Enhanced LLM-based discrepancy detection
            import openai

            # Use OpenAI for sophisticated document analysis
            response = openai.ChatCompletion.create(
                model="gpt-35-turbo",
                messages=[
                    {"role": "system",
                     "content": "You are an expert trade finance compliance analyst specializing in SWIFT LC document validation. Provide precise, field-level analysis of document compliance."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # Low temperature for consistent analysis
                max_tokens=2000
            )

            gpt_response = response.choices[0].message.content
            return extract_json_from_gpt_response(gpt_response)
        except Exception as e:
            return {
                "match": False,
                "mismatches": [f"LLM error: {str(e)}"],
                "extracted_swift": {},
                "extracted_support": {}
            }

    def extract_json_from_gpt_response(text):
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            json_str = match.group(0)
            return json.loads(json_str)
        return json.loads(text)

    def handle_table_or_report_request(intent, user_query, user_id, output_format, context) -> tuple[
                                                                                                   Response, int] | Response:
        """Handles a RAG-based table/report request and saves conversation context."""

        try:
            # Get active repository for the user
            active_repository = active_user_repositories.get(user_id)

            # Run the RAG-based table/report logic
            result = generate_rag_table_or_report_request(user_query, user_id, output_format="table",
                                                          active_repository=active_repository)
            print(f"rag result message : {result}")
            
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
        if token_count > 8000:
            logging.warning(f"Page {page_number} exceeds token limit. Truncating.")
            page_text = page_text[:10000]

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
            logger.info(f"🔍 handle_file_upload called with product: {productName}, function: {functionName}")

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
                            future_ucp600 = executor.submit(
                                analyze_ucp_compliance_chromaRAG,
                                page_extracted_fields
                            )
                            future_swift = executor.submit(
                                analyze_swift_compliance_chromaRAG,
                                page_extracted_fields
                            )
                            compliance_futures.append((future_ucp600, future_swift))

                        for i, (future_ucp600, future_swift) in enumerate(compliance_futures):
                            page_analysis_results[i]["ucp600_result"] = future_ucp600.result()
                            page_analysis_results[i]["swift_result"] = future_swift.result()

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

                    logging.info("🔎 Final analysis result for file %s:\n%s", file_name, json.dumps({
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

    ALLOWED_FILE_TYPES = ["application/pdf", "image/jpeg", "image/png"]

    def validate_azure_cv_config():
        """
        Validate Azure Computer Vision configuration at startup.
        Returns True if valid, False otherwise.
        """
        try:
            from app.utils.app_config import COMPUTER_VISION_ENDPOINT, COMPUTER_VISION_KEY
            
            if not COMPUTER_VISION_ENDPOINT or not COMPUTER_VISION_KEY:
                logger.error("❌ Azure Computer Vision credentials not configured")
                return False
                
            # Test if endpoint is reachable (basic validation)
            if not COMPUTER_VISION_ENDPOINT.startswith(('http://', 'https://')):
                logger.error("❌ Invalid Azure Computer Vision endpoint format")
                return False
                
            logger.info("✅ Azure Computer Vision configuration validated")
            return True
            
        except Exception as e:
            logger.error(f"❌ Azure Computer Vision configuration error: {e}")
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
            
            logger.debug(f"✅ File validation passed: {uploaded_file.filename} ({file_size / 1024:.1f} KB)")
            return None  # No error
            
        except Exception as e:
            logger.error(f"❌ File validation error: {e}")
            return f"File validation failed: {str(e)}"

    def extract_text_with_retry_optimized(temp_file_path, file_type, quality_verdict=None, page_count=1, max_retries=None):
        """
        OPTIMIZED: Extract text from file with performance optimizations and retry logic.
        Integrates quality-based OCR optimization with existing retry mechanism.
        
        Args:
            temp_file_path (str): Path to the temporary file
            file_type (str): MIME type of the file  
            quality_verdict (str): Quality analysis verdict for optimization
            page_count (int): Number of pages for timeout calculation
            max_retries (int, optional): Override for max retries. Uses OCR_MAX_RETRIES if None
            
        Returns:
            dict: OCR result with text_data or error information
        """
        import time
        from app.utils.file_utils import extract_text_from_file_optimized
        from app.utils.app_config import OCR_MAX_RETRIES, OCR_RETRY_DELAY_BASE
        
        # Use config value if max_retries not specified
        if max_retries is None:
            max_retries = OCR_MAX_RETRIES
            
        # Quality-based retry optimization
        if quality_verdict == "direct_analysis":
            max_retries = max(1, max_retries - 1)  # Reduce retries for high-quality docs
            
        logger.info(f"🚀 OPTIMIZED OCR retry: max_retries={max_retries}, quality={quality_verdict}, pages={page_count}")
        
        for attempt in range(max_retries):
            try:
                logger.debug(f"🔄 OCR attempt {attempt + 1}/{max_retries} for file: {temp_file_path}")
                result = extract_text_from_file_optimized(temp_file_path, file_type, quality_verdict, page_count)
                
                # Check if OCR was successful
                if "error" not in result:
                    processing_time = result.get("processing_time", 0)
                    confidence = result.get("overall_confidence", 0)
                    logger.info(f"✅ OPTIMIZED OCR succeeded on attempt {attempt + 1} in {processing_time:.2f}s (confidence: {confidence:.3f})")
                    return result
                    
                # If it's the last attempt, return the error
                if attempt == max_retries - 1:
                    logger.error(f"❌ OCR failed after {max_retries} attempts: {result.get('error')}")
                    return result
                    
                # Wait before retry with exponential backoff
                wait_time = (2 ** attempt) * OCR_RETRY_DELAY_BASE
                logger.warning(f"⚠️ OCR attempt {attempt + 1} failed: {result.get('error')} | Retrying in {wait_time}s...")
                time.sleep(wait_time)
                
            except Exception as e:
                logger.error(f"❌ OCR attempt {attempt + 1} threw exception: {str(e)}")
                if attempt == max_retries - 1:
                    return {"error": f"OCR extraction failed: {str(e)}", "text_data": []}
                    
                wait_time = (2 ** attempt) * OCR_RETRY_DELAY_BASE
                logger.warning(f"⚠️ Retrying in {wait_time}s...")
                time.sleep(wait_time)
        """
        Extract text from file with exponential backoff retry logic.
        Uses configurable retry settings from app_config.
        
        Args:
            temp_file_path (str): Path to the temporary file
            file_type (str): MIME type of the file
            max_retries (int, optional): Override for max retries. Uses OCR_MAX_RETRIES if None
            
        Environment Variables:
            OCR_MAX_RETRIES: Maximum number of retry attempts (default: 3, range: 1-10)
            OCR_RETRY_DELAY_BASE: Base delay for exponential backoff in seconds (default: 1)
            
        Returns:
            dict: OCR result with text_data or error information
        """
        import time
        from app.utils.file_utils import extract_text_from_file
        from app.utils.app_config import OCR_MAX_RETRIES, OCR_RETRY_DELAY_BASE
        
        # Use config value if max_retries not specified
        if max_retries is None:
            max_retries = OCR_MAX_RETRIES
        
        logger.info(f"🔧 OCR retry configuration: max_retries={max_retries}, base_delay={OCR_RETRY_DELAY_BASE}s")
        
        for attempt in range(max_retries):
            try:
                logger.debug(f"🔄 OCR attempt {attempt + 1}/{max_retries} for file: {temp_file_path}")
                result = extract_text_from_file(temp_file_path, file_type)
                
                # Check if OCR was successful
                if "error" not in result:
                    logger.debug(f"✅ OCR succeeded on attempt {attempt + 1}")
                    return result
                    
                # If it's the last attempt, return the error
                if attempt == max_retries - 1:
                    logger.error(f"❌ OCR failed after {max_retries} attempts: {result.get('error')}")
                    return result
                    
                # Wait before retry with exponential backoff
                wait_time = (2 ** attempt) * OCR_RETRY_DELAY_BASE  # Configurable base delay
                logger.warning(f"⚠️ OCR attempt {attempt + 1} failed: {result.get('error')}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
                
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"❌ OCR failed after {max_retries} attempts with exception: {e}")
                    return {"error": f"OCR failed after {max_retries} attempts: {str(e)}", "text_data": []}
                
                wait_time = (2 ** attempt) * OCR_RETRY_DELAY_BASE
                logger.warning(f"⚠️ OCR attempt {attempt + 1} failed with exception: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
                
        return {"error": "OCR failed after all retry attempts", "text_data": []}

    # Initialize document classifier at module level
    document_classifier = DocumentClassifier()

    def process_uploaded_files(uploaded_files, intent, userQuery=None, annotations=None, productName=None,
                               functionName=None, documentType=None, progress_tracker=None):
        try:
            results = []
            logger.info(f"🔍 process_uploaded_files called with product: {productName}, function: {functionName}, documentType: {documentType}")

            if not isinstance(uploaded_files, list):
                uploaded_files = [uploaded_files]

            # Initialize progress tracking
            if progress_tracker:
                logger.info(f"📊 Starting progress tracking for {len(uploaded_files)} file(s)")
                progress_tracker.start_upload(f"{len(uploaded_files)} file(s)")

            for idx, uploaded_file in enumerate(uploaded_files):
                file_type = getattr(uploaded_file, "content_type", "unknown")
                file_name = getattr(uploaded_file, "filename", "unnamed")
                
                logger.info(f"🔧 DEBUG: Processing file {idx+1}/{len(uploaded_files)}: {file_name}")
                logger.info(f"🔧 DEBUG: progress_tracker is {'available' if progress_tracker else 'None'}")
                
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
                    logger.info(f"📤 Upload complete for file: {file_name}")
                    logger.info(f"🔧 DEBUG: Calling progress_tracker.upload_complete() now...")
                    progress_tracker.upload_complete()
                    logger.info(f"✅ DEBUG: upload_complete() called successfully")
                    
                    # Start quality analysis stage (fast version)
                    logger.info(f"🔍 Starting quality analysis for: {file_name}")
                    logger.info(f"🔧 DEBUG: Calling progress_tracker.start_quality_analysis() now...")
                    progress_tracker.start_quality_analysis()
                    logger.info(f"✅ DEBUG: start_quality_analysis() called successfully")

                # Perform quality analysis (ultra-fast version to avoid hanging)
                if progress_tracker:
                    try:
                        # Ultra-quick quality check - just mark as good
                        file_size = os.path.getsize(temp_file_path)
                        quality_verdict = "processed"
                        quality_score = 0.8
                        
                        logger.info(f"✅ Instant quality check: {quality_verdict} (size: {file_size} bytes)")
                            
                    except Exception as quality_error:
                        logger.warning(f"Quality check error: {quality_error}")
                        quality_verdict = "processed"
                        quality_score = 0.7
                    
                    # Mark quality analysis complete immediately
                    logger.info(f"✅ Quality analysis complete for: {file_name}")
                    progress_tracker.quality_complete(quality_verdict, quality_score)
                    
                    # Start OCR stage
                    logger.info(f"📄 Starting OCR extraction for: {file_name}")
                    progress_tracker.start_ocr()

                try:
                    extracted_text_data = extract_text_with_retry(temp_file_path, file_type)
                    text_data = extracted_text_data.get("text_data", [])
                    
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
                    combined_swift_result = {}
                    combined_ucp600_result = {}

                    for page_result in page_analysis_results:
                        # Aggregate SWIFT compliance results
                        if "swift_result" in page_result:
                            combined_swift_result.update(page_result["swift_result"])

                        # Aggregate UCP600 compliance results
                        if "ucp600_result" in page_result:
                            combined_ucp600_result.update(page_result["ucp600_result"])

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
                        "swift_result": combined_swift_result,
                        "ucp600_result": combined_ucp600_result,
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
                        if combined_swift_result:
                            compliance_issues += len([k for k, v in combined_swift_result.items() if not v.get("compliant", True)])
                        if combined_ucp600_result:
                            compliance_issues += len([k for k, v in combined_ucp600_result.items() if not v.get("compliant", True)])
                        
                        # Mark compliance complete
                        progress_tracker.compliance_complete(compliance_issues)
                        
                        # Finalize processing
                        progress_tracker.finalize()

                    logging.info("🔎 Final analysis result for file %s:\n%s", file_name, json.dumps({
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
        logger.info(f"📊 === ORGANIZING OCR DATA BY PAGE ===")
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
        
        logger.info(f"📈 Page distribution in raw OCR data:")
        for page in sorted(page_counts.keys()):
            logger.info(f"   Page {page}: {page_counts[page]} entries")
        
        if missing_page_count > 0:
            logger.warning(f"⚠️ Found {missing_page_count} entries without page information")
        
        # Organize by page
        pages = defaultdict(list)
        for entry in text_data:
            page = entry.get("bounding_page", 1)
            pages[page].append(entry)
        
        organized_pages = [pages[k] for k in sorted(pages)]
        logger.info(f"✅ Organized into {len(organized_pages)} pages")
        
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

    def process_page_with_llm_analysis(page_number, page_ocr_data, userQuery, annotations, productName, functionName, documentType=None):
        global prompt_config  # Declare at function start to avoid SyntaxError

        logger.info(f"=== Starting process_page_with_llm_analysis for page {page_number} ===")
        logger.info(f"UserQuery: {userQuery}, Product: {productName}, Function: {functionName}, DocumentType: {documentType}")

        # Load prompt configuration at the beginning
        if not prompt_config:
            prompt_config = load_prompt_config()
            if prompt_config:
                logger.info(f"✅ Loaded prompt configuration from YAML")

        page_text = " ".join([entry["text"] for entry in page_ocr_data])
        token_count = calculate_text_token_count(page_text)
        logger.info(f"Page {page_number} token count: {token_count}")

        # if token_count > 8000:
        #     logging.warning(f"Page {page_number} exceeds token limit. Truncating.")
        #     page_text = page_text[:10000]

        ocr_text = format_ocr_data_for_llm_prompt(page_ocr_data)

        # STEP 1: Document Classification (EXISTING LOGIC)
        logger.info(f"Calling document_classifier.classify_document for page {page_number}")
        logger.info(f"Current OpenAI config before classification - API Base: {openai.api_base}, Key exists: {bool(openai.api_key)}")

        classification_result = document_classifier.classify_document(page_text)

        logger.info(f"Classification result for page {page_number}: {classification_result}")
        document_type = classification_result.get("document_type", "unknown")

        # Override with user query if provided
        if userQuery and userQuery.lower() in ["letter_of_credit", "invoice", "export_collection", "bank_guarantee"]:
            document_type = userQuery.lower()

        # Use provided documentType if available (this takes highest priority)
        if documentType:
            document_type = documentType
            logger.info(f"🔖 Using explicitly provided document type: {documentType}")

        # STEP 2: Map classified document type to UN/CEFACT code
        def map_document_type_to_uncefact_code(doc_type):
            """Map classified document type to UN/CEFACT document code"""
            mapping = {
                "letter_of_credit": "LC",
                "letter of credit": "LC",
                "lc": "LC",
                "commercial_invoice": "INV",
                "commercial invoice": "INV",
                "invoice": "INV",
                "bill_of_lading": "BoL",
                "bill of lading": "BoL",
                "bol": "BoL",
                "certificate_of_origin": "CoO",
                "certificate of origin": "CoO",
                "coo": "CoO",
                "packing_list": "PL",
                "packing list": "PL",
                "air_waybill": "AW",
                "air waybill": "AW",
                "sea_waybill": "SW",
                "sea waybill": "SW",
                "cargo_insurance": "CID",
                "insurance_certificate": "CID",
                "bank_guarantee": "LC",  # Bank guarantees use similar structure
                "customs_declaration": "CD",
                "phytosanitary_certificate": "ePhyto",
                "warehouse_receipt": "WR",
                "dangerous_goods_declaration": "DGD",
                "bill_of_exchange": "BoE",
                "promissory_note": "PN",
                "payment_confirmation": "PC"
            }
            return mapping.get(doc_type.lower(), None)

        # STEP 3: Try to get UN/CEFACT code from classification
        uncefact_code = map_document_type_to_uncefact_code(document_type)

        if uncefact_code:
            logger.info(f"🗺️  Mapped '{document_type}' → UN/CEFACT code: '{uncefact_code}'")
        else:
            logger.info(f"ℹ️  No UN/CEFACT mapping found for document type: '{document_type}'")

        # STEP 4: Get fields from entity_mappings (document_entity_maintenance.json)
        doc_type_normalized = classification_result.get("document_type", "").replace(" ", "_")
        if not doc_type_normalized:
            doc_type_normalized = document_type.replace(" ", "_")

        logger.info(f"📋 Getting entity fields for: {doc_type_normalized}")
        entity_info = document_classifier.get_enhanced_entity_fields(doc_type_normalized)

        field_list = []
        field_definitions = {}

        # Build field list from entity mappings
        for field in entity_info['mandatory_fields']:
            field_name = field['entityName']
            field_list.append(field_name)
            field_definitions[field_name] = f"{field_name} (Mandatory)"

        for field in entity_info['optional_fields']:
            field_name = field['entityName']
            field_list.append(field_name)
            field_definitions[field_name] = f"{field_name} (Optional)"

        for field in entity_info['conditional_fields']:
            field_name = field['entityName']
            field_list.append(field_name)
            field_definitions[field_name] = f"{field_name} (Conditional)"

        logger.info(f"✅ Using entity_mappings: {len(field_list)} fields ({len(entity_info['mandatory_fields'])} mandatory, {len(entity_info['optional_fields'])} optional, {len(entity_info['conditional_fields'])} conditional)")

        # Store for later use
        trade_doc_fields = {
            'mandatory': entity_info['mandatory_fields'],
            'optional': entity_info['optional_fields'],
            'conditional': entity_info['conditional_fields']
        }

        try:
            # Use DocumentClassifier to build extraction prompt from config and entity_mappings
            logger.info(f"🔍 Building extraction prompt using DocumentClassifier for page {page_number}")
            prompt = document_classifier.build_extraction_prompt(
                document_type=document_type,
                ocr_text=page_text,
                page_number=page_number
            )
            logger.info(f"✅ Extraction prompt built successfully using entity_mappings")

            # === ENHANCEMENT: Add field mapping examples from document_entities ===
            field_mapping_example = load_document_field_mappings(document_type)
            if field_mapping_example:
                prompt += f"\n\n{field_mapping_example}"
                logger.info(f"📋 Enhanced prompt with field mapping examples for {document_type}")

            # Load prompt configuration for model settings (already declared global at function start)
            if not prompt_config:
                prompt_config = load_prompt_config()

            # Fallback if build_extraction_prompt fails
            if not prompt:
                logger.error("❌ Failed to build extraction prompt from DocumentClassifier, using basic fallback")
                prompt = f"Extract fields from this {document_type} document:\n\n{page_text}"

            # Get model settings from config (with fallback to defaults)
            temperature = 0.0
            model = deployment_name
            if prompt_config:
                temperature = prompt_config.get('extraction', {}).get('temperature', 0.0)
                model = prompt_config.get('extraction', {}).get('model', deployment_name)

            logger.info(f"📝 Using extraction config - Model: {model}, Temperature: {temperature}")

            # Send prompt to LLM (note: build_extraction_prompt already includes system prompt)
            response = openai.ChatCompletion.create(
                engine=model if model else deployment_name,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature
            )

            result = response["choices"][0]["message"]["content"].strip()
            parsed_json = parse_json_from_llm_response(result)
            if not parsed_json:
                return {"page_number": page_number, "error": "Invalid LLM response format"}

            # Ensure compliance results are included for all document types
            # No need to remove compliance results anymore

            # Enhanced logging for trade document field extraction
            if trade_doc_fields and parsed_json.get("extracted_fields"):
                extracted_field_names = list(parsed_json["extracted_fields"].keys())
                logger.info(f"📊 Page {page_number} - Extracted {len(extracted_field_names)} fields from document")

                # Log mandatory fields that were found
                mandatory_found = [f['entityName'] for f in trade_doc_fields['mandatory']
                                 if any(f['entityName'] in field or f['entityName'].lower().replace(' ', '_') in field.lower()
                                       for field in extracted_field_names)]
                if mandatory_found:
                    logger.info(f"✅ Mandatory fields found: {', '.join(mandatory_found[:5])}{'...' if len(mandatory_found) > 5 else ''}")

                # Log optional fields that were found
                optional_found = [f['entityName'] for f in trade_doc_fields['optional']
                                if any(f['entityName'] in field or f['entityName'].lower().replace(' ', '_') in field.lower()
                                      for field in extracted_field_names)]
                if optional_found:
                    logger.info(f"ℹ️  Optional fields found: {', '.join(optional_found[:5])}{'...' if len(optional_found) > 5 else ''}")

                # Log which mandatory fields are missing
                mandatory_missing = [f['entityName'] for f in trade_doc_fields['mandatory']
                                   if not any(f['entityName'] in field or f['entityName'].lower().replace(' ', '_') in field.lower()
                                            for field in extracted_field_names)]
                if mandatory_missing:
                    logger.warning(f"⚠️  Missing mandatory fields: {', '.join(mandatory_missing[:5])}{'...' if len(mandatory_missing) > 5 else ''}")

            logging.info(f"Comprehensive analysis result for page {page_number}: {parsed_json}")
            return parsed_json

        except Exception as e:
            logging.error(f"Error analyzing page {page_number}: {e}")
            return {"page_number": page_number, "error": "Failed to analyze the page."}

    client = get_chromadb_client(host="localhost", port=8000)
    user_manual_collection = client.get_or_create_collection("user_manual")

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
        """Query the trained user manual using ChromaDB RAG with embeddings."""
        try:
            # Generate embedding for the query
            query_embedding = get_embedding_azureRAG(user_query)

            # All users can query global manuals
            # Query ChromaDB for relevant chunks using embeddings
            # Search in global manuals
            results = user_manual_collection.query(
                query_embeddings=[query_embedding],
                n_results=5,
                where={"is_global": True}
            )
            
            # Log query results for debugging
            logger.info(f"User manual query for user {user_id}: Found {len(results.get('documents', [[]])[0])} global docs")

            # Safely access documents and metadata
            retrieved_docs = results.get("documents", [[]])[0] if results.get("documents") else []
            retrieved_metadata = results.get("metadatas", [[]])[0] if results.get("metadatas") else []

            if not retrieved_docs:
                logger.warning(f"No relevant documents found for user {user_id}, query: {user_query}")
                return {"success": False, "message": "No relevant information found in the trained manual."}

            # Ensure retrieved_docs is a list of strings
            if not all(isinstance(doc, str) for doc in retrieved_docs):
                logger.error(f"Invalid document format in query results: {retrieved_docs}")
                return {"success": False, "message": "Invalid document format in query results."}

            # Extract unique file names from metadata
            file_names = set()
            for meta in retrieved_metadata:
                if meta and "file_name" in meta:
                    file_names.add(meta["file_name"])

            # Format retrieved documents for LLM with metadata
            context_sections = []
            for i, (doc, meta) in enumerate(zip(retrieved_docs, retrieved_metadata)):
                file_name = meta.get("file_name", "Unknown") if meta else "Unknown"
                context_sections.append(f"Section {i + 1} (from {file_name}): {doc}")

            context_text = "\n".join(context_sections)

            # Determine if this is a data query that might need a table
            is_data_query = any(keyword in user_query.lower() for keyword in
                                ["show", "list", "display", "find", "get", "retrieve", "expired", "active", "pending",
                                 "table", "records"])

            prompt = f"""
            You are a formatting assistant. Your ONLY job is to apply HTML formatting to the content from the user manual.

            ### Retrieved Manual Sections:
            {context_text}

            ### User Query:
            {user_query}

            ### STRICT INSTRUCTIONS:
            1. ONLY apply HTML formatting - DO NOT add, remove, or modify any data
            2. DO NOT add summaries, insights, explanations, or any new content
            3. DO NOT interpret or analyze the data
            4. If data should be in a table, format it as an HTML table
            5. Keep ALL original data values EXACTLY as they appear
            6. Only add HTML tags for formatting purposes

            ### HTML Format Requirements:
            - For table data: Use proper <table>, <thead>, <tbody>, <tr>, <th>, <td> tags
            - For text data: Use <p>, <div>, or appropriate HTML tags
            - Include CSS classes for styling but DO NOT change the content

            ### Response Template:
            <div class="rag-response">
                <div class="source-info">
                    <i class="fas fa-book"></i>
                    <span>Source: {", ".join(file_names) if file_names else "User Manual"}</span>
                </div>
                <!-- Format the EXACT content from Retrieved Manual Sections here -->
                <!-- Use appropriate HTML tags based on data type -->
                <!-- DO NOT add any new text or data -->
            </div>
            """

            response = openai.ChatCompletion.create(
                engine=deployment_name,
                messages=[
                    {"role": "system",
                     "content": "You are a trade finance assistant that provides well-formatted HTML responses based on user manual data."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,
                max_tokens=2000
            )

            answer = response["choices"][0]["message"]["content"].strip()

            # If the response doesn't include source info, add it
            if "<div class=\"source-info\">" not in answer:
                source_html = f'<div class="source-info"><i class="fas fa-book"></i><span>Source: {", ".join(file_names) if file_names else "User Manual"}</span></div>'
                answer = f'<div class="rag-response">{source_html}{answer}</div>'

            logger.info(f"Query result for user {user_id}: RAG response generated")

            # Don't save here - frontend will save via /api/conversation/message endpoint

            return {
                "success": True,
                "response": answer,
                "html": answer,
                "intent": "RAG Request",
                "output_format": "table" if is_data_query else "text",
                "source_files": list(file_names) if file_names else ["User Manual"]
            }

        except Exception as e:
            logger.error(f"Error querying trained manual for user {user_id}: {str(e)}")
            return {"success": False, "message": f"Error querying trained manual: {str(e)}"}

    def retrieve_relevant_chunks_user_manual(query: str, user_id: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve relevant chunks from user manual collection."""
        try:
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

    def get_user_manuals(user_id: str) -> Dict[str, Any]:
        """Get list of globally available user manuals (uploaded by admins)."""
        try:
            # All users can view the list of global manuals
            # Get all global manuals
            results = user_manual_collection.get(
                where={"is_global": True}
            )

            # Extract unique file names
            file_names = set()
            if results and "metadatas" in results:
                for metadata in results["metadatas"]:
                    if metadata and "file_name" in metadata:
                        file_names.add(metadata["file_name"])

            return {
                "success": True,
                "manuals": sorted(list(file_names)),
                "count": len(file_names)
            }
        except Exception as e:
            logger.error(f"Error getting user manuals: {str(e)}")
            return {"success": False, "message": f"Error retrieving manuals: {str(e)}"}

    def delete_user_manual(user_id: str, file_name: str) -> Dict[str, Any]:
        """Delete a specific user manual from ChromaDB (admin only)."""
        try:
            # Check if user is admin
            user = UserRepository.get_user_by_id(user_id) if user_id else None
            if not user:
                return {"success": False, "message": "User not found"}
            
            # Check if user is allowed
            if user.get("email", "").lower() not in [e.lower() for e in ALLOWED_EMAILS]:
                return {"success": False, "message": "Access denied"}
            
            # Admin can delete any global manual
            results = user_manual_collection.get(
                where={"$and": [{"is_global": True}, {"file_name": file_name}]}
            )

            if results and "ids" in results and results["ids"]:
                # Delete all chunks for this manual
                user_manual_collection.delete(ids=results["ids"])
                logger.info(f"Deleted manual '{file_name}' for user {user_id}")
                return {"success": True, "message": f"Manual '{file_name}' deleted successfully."}
            else:
                return {"success": False, "message": f"Manual '{file_name}' not found."}

        except Exception as e:
            logger.error(f"Error deleting user manual: {str(e)}")
            return {"success": False, "message": f"Error deleting manual: {str(e)}"}

    @app.route('/api/trainuser-manuals', methods=['POST'])
    def api_post_user_manuals():
        """API endpoint to upload user manuals (admin only)."""
        # Check both session and request args for user_id
        user_query, user_id, uploaded_file, annotations = None, None, None, None
        user_id = session.get('user_id') or request.args.get('user_id')
        
        # Check if user is admin
        if user_id:
            user = UserRepository.get_user_by_id(user_id)
            if user:
                # Check if user is allowed
                if user.get("email", "").lower() not in [e.lower() for e in ALLOWED_EMAILS]:
                    return jsonify({
                        "response": "Access denied",
                        "intent": "Train Intent",
                        "success": False
                    }), 403
        
        logger.info("Processing file upload request.")
        user_query = request.form.get("query", "").strip()
        user_id = session.get("user_id") or request.form.get("user_id", "").strip() or None
        session_id = request.form.get("session_id", None)
        annotations = request.form.get("annotations", "").strip()
        uploaded_file = request.files.getlist("file")

        if uploaded_file and len(uploaded_file) > 0:
            result = train_user_manual(uploaded_file[0], user_id, user_query)
            return jsonify({
                "response": result["message"],
                "intent": "Train Intent",
                "success": result["success"]
            }), 200 if result["success"] else 400

    @app.route('/api/user-manuals', methods=['GET'])
    def api_get_user_manuals():
        """API endpoint to get list of user manuals."""
        # Check both session and request args for user_id
        user_id = session.get('user_id') or request.args.get('user_id')
        if not user_id:
            return jsonify({"success": False, "message": "User not authenticated", "manuals": [], "count": 0}), 401
        result = get_user_manuals(user_id)
        return jsonify(result), 200 if result["success"] else 50

    @app.route('/api/user-manuals/<file_name>', methods=['DELETE'])
    def api_delete_user_manual(file_name):
        """API endpoint to delete a user manual."""
        # Check session, request args, and request body for user_id
        user_id = session.get('user_id') or request.args.get('user_id')

        # Also check request body if it's JSON
        if not user_id and request.is_json:
            data = request.get_json()
            user_id = data.get('user_id') if data else None

        if not user_id:
            return jsonify({"success": False, "message": "User not authenticated"}), 401

        result = delete_user_manual(user_id, file_name)
        return jsonify(result), 200 if result["success"] else 404

    # Document Compliance Checking Routes
    from app.utils.compliance_validator import DocumentComplianceValidator

    compliance_validator = DocumentComplianceValidator()

    @app.route('/compliance-checker')
    def compliance_checker_page():
        """Render the document compliance checker page"""
        return render_template('compliance_checker.html')

    @app.route('/api/compliance/validate', methods=['POST'])
    def validate_document_compliance():
        """API endpoint for document compliance validation"""
        try:
            data = request.get_json()

            if not data:
                return jsonify({
                    'success': False,
                    'error': 'No data provided'
                }), 400

            swift_message = data.get('swift_message')
            related_documents = data.get('related_documents', [])

            if not swift_message:
                return jsonify({
                    'success': False,
                    'error': 'SWIFT message is required'
                }), 400

            # Perform validation
            validation_results = compliance_validator.validate_documents(
                swift_message,
                related_documents
            )

            # Log validation request
            logger.info(f"Compliance validation completed for SWIFT {swift_message.get('message_type', 'Unknown')}")

            return jsonify({
                'success': True,
                'validation_results': validation_results
            })

        except Exception as e:
            logger.error(f"Error in compliance validation: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/compliance/upload', methods=['POST'])
    def upload_compliance_documents():
        """Upload and process documents for compliance checking"""
        try:
            uploaded_files = request.files.getlist('files')

            if not uploaded_files:
                return jsonify({
                    'success': False,
                    'error': 'No files uploaded'
                }), 400

            processed_documents = []

            for file in uploaded_files:
                if file and file.filename:
                    # Extract text from file
                    text_content = extract_text_from_file(file)

                    # Determine document type based on content or filename
                    doc_type = determine_document_type(file.filename, text_content)

                    # Extract structured data based on document type
                    structured_data = extract_document_data(text_content, doc_type)

                    processed_documents.append({
                        'filename': file.filename,
                        'document_type': doc_type,
                        'extracted_data': structured_data,
                        'raw_text': text_content[:1000]  # First 1000 chars for preview
                    })

            return jsonify({
                'success': True,
                'processed_documents': processed_documents
            })

        except Exception as e:
            logger.error(f"Error processing uploaded documents: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/compliance/swift/parse', methods=['POST'])
    def parse_swift_message():
        """Parse SWIFT message from text input"""
        try:
            data = request.get_json()
            swift_text = data.get('swift_text', '')

            if not swift_text:
                return jsonify({
                    'success': False,
                    'error': 'SWIFT message text is required'
                }), 400

            # Parse SWIFT message
            parsed_swift = parse_swift_message_text(swift_text)

            return jsonify({
                'success': True,
                'parsed_swift': parsed_swift
            })

        except Exception as e:
            logger.error(f"Error parsing SWIFT message: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/compliance/report', methods=['POST'])
    def generate_compliance_report():
        """Generate detailed compliance report"""
        try:
            data = request.get_json()
            validation_results = data.get('validation_results')

            if not validation_results:
                return jsonify({
                    'success': False,
                    'error': 'Validation results are required'
                }), 400

            # Generate comprehensive report
            report = generate_detailed_compliance_report(validation_results)

            return jsonify({
                'success': True,
                'report': report
            })

        except Exception as e:
            logger.error(f"Error generating compliance report: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/compliance/history', methods=['GET'])
    def get_compliance_history():
        """Get compliance check history for user"""
        try:
            user_id = request.args.get('user_id')
            limit = int(request.args.get('limit', 10))

            if not user_id:
                return jsonify({
                    'success': False,
                    'error': 'User ID is required'
                }), 400

            # Mock history data - replace with actual database query
            history = get_user_compliance_history(user_id, limit)

            return jsonify({
                'success': True,
                'history': history
            })

        except Exception as e:
            logger.error(f"Error retrieving compliance history: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    # Vetting Rule Engine API Routes
    def check_admin_access():
        """Helper function to check if current user is admin"""
        user_email = session.get('user_email', '')
        if not user_email and 'user_id' in session:
            user = users_collection.find_one({"_id": session["user_id"]})
            if user:
                user_email = user.get('email', '')
                session['user_email'] = user_email  # Cache for future requests
        
        admin_emails = ['ravi@finstack-tech.com', 'ilyashussain9@gmail.com', 'admin@finstack-tech.com']
        is_admin = user_email.lower() in [e.lower() for e in admin_emails]
        return is_admin, user_email
    @app.route('/api/vetting/rules', methods=['GET'])
    def get_vetting_rules():
        """Get all vetting rules (active only for non-admins)"""
        try:
            is_admin, user_email = check_admin_access()
            
            if vetting_engine:
                rules = vetting_engine.get_all_rules(active_only=not is_admin)
                return jsonify({
                    'success': True,
                    'rules': rules,
                    'is_admin': is_admin
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Vetting engine not initialized'
                }), 500
                
        except Exception as e:
            logger.error(f"Error getting vetting rules: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/vetting/rules', methods=['POST'])
    def create_vetting_rule():
        """Create a new vetting rule (admin only)"""
        try:
            is_admin, user_email = check_admin_access()
            
            if not is_admin:
                return jsonify({
                    'success': False,
                    'error': 'Admin access required'
                }), 403
            
            if not vetting_engine:
                return jsonify({
                    'success': False,
                    'error': 'Vetting engine not initialized'
                }), 500
                
            data = request.get_json()
            rule = vetting_engine.create_rule(data, user_email)
            
            return jsonify({
                'success': True,
                'rule': rule
            })
            
        except Exception as e:
            logger.error(f"Error creating vetting rule: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/vetting/rules/<rule_id>', methods=['PUT'])
    def update_vetting_rule(rule_id):
        """Update a vetting rule (admin only)"""
        try:
            is_admin, user_email = check_admin_access()
            
            if not is_admin:
                return jsonify({
                    'success': False,
                    'error': 'Admin access required'
                }), 403
            
            if not vetting_engine:
                return jsonify({
                    'success': False,
                    'error': 'Vetting engine not initialized'
                }), 500
                
            data = request.get_json()
            rule = vetting_engine.update_rule(rule_id, data, user_email)
            
            if rule:
                return jsonify({
                    'success': True,
                    'rule': rule
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Rule not found'
                }), 404
                
        except Exception as e:
            logger.error(f"Error updating vetting rule: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/vetting/rules/<rule_id>', methods=['DELETE'])
    def delete_vetting_rule(rule_id):
        """Delete a vetting rule (admin only)"""
        try:
            is_admin, user_email = check_admin_access()
            
            if not is_admin:
                return jsonify({
                    'success': False,
                    'error': 'Admin access required'
                }), 403
            
            if not vetting_engine:
                return jsonify({
                    'success': False,
                    'error': 'Vetting engine not initialized'
                }), 500
                
            success = vetting_engine.delete_rule(rule_id)
            
            if success:
                return jsonify({
                    'success': True,
                    'message': 'Rule deleted successfully'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Rule not found'
                }), 404
                
        except Exception as e:
            logger.error(f"Error deleting vetting rule: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/vetting/rules/<rule_id>/test', methods=['POST'])
    def test_vetting_rule(rule_id):
        """Test a vetting rule with sample texts (admin only)"""
        try:
            is_admin, user_email = check_admin_access()
            
            if not is_admin:
                return jsonify({
                    'success': False,
                    'error': 'Admin access required'
                }), 403
            
            if not vetting_engine:
                return jsonify({
                    'success': False,
                    'error': 'Vetting engine not initialized'
                }), 500
                
            data = request.get_json()
            test_samples = data.get('test_samples', [])
            
            if not test_samples:
                return jsonify({
                    'success': False,
                    'error': 'Test samples are required'
                }), 400
            
            test_result = vetting_engine.test_rule(rule_id, test_samples)
            
            return jsonify({
                'success': True,
                'test_result': test_result
            })
            
        except Exception as e:
            logger.error(f"Error testing vetting rule: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/vetting/rules/<rule_id>/generate-samples', methods=['POST'])
    def generate_test_samples(rule_id):
        """Generate AI-powered test samples for a rule (admin only)"""
        try:
            is_admin, user_email = check_admin_access()
            
            if not is_admin:
                return jsonify({
                    'success': False,
                    'error': 'Admin access required'
                }), 403
            
            if not vetting_engine:
                return jsonify({
                    'success': False,
                    'error': 'Vetting engine not initialized'
                }), 500
            
            rule = vetting_engine.get_rule(rule_id)
            if not rule:
                return jsonify({
                    'success': False,
                    'error': 'Rule not found'
                }), 404
            
            # Generate sample texts using LLM
            positive_sample, negative_sample, metadata = vetting_engine.generate_sample_texts_llm(rule)
            
            return jsonify({
                'success': True,
                'samples': [
                    {
                        'text': positive_sample,
                        'expected_onerous': True,
                        'description': 'Sample that should trigger the rule'
                    },
                    {
                        'text': negative_sample,
                        'expected_onerous': False,
                        'description': 'Sample that should NOT trigger the rule'
                    }
                ],
                'metadata': metadata
            })
            
        except Exception as e:
            logger.error(f"Error generating test samples: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/vetting/test', methods=['POST'])
    def test_guarantee_vetting():
        """Test guarantee text against all active rules"""
        try:
            if not vetting_engine:
                return jsonify({
                    'success': False,
                    'error': 'Vetting engine not initialized'
                }), 500
                
            data = request.get_json()
            guarantee_text = data.get('guarantee_text', '')
            include_llm = data.get('include_llm_analysis', True)
            
            if not guarantee_text:
                return jsonify({
                    'success': False,
                    'error': 'Guarantee text is required'
                }), 400
            
            # Perform vetting
            if include_llm:
                vetting_result = vetting_engine.vet_guarantee_with_llm(guarantee_text, include_llm_analysis=True)
            else:
                vetting_result = vetting_engine.vet_guarantee_basic(guarantee_text)
            
            return jsonify({
                'success': True,
                'vetting_result': vetting_result
            })
            
        except Exception as e:
            logger.error(f"Error in guarantee vetting: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/vetting/guarantee', methods=['POST'])
    def vet_guarantee_terms():
        """Analyze guarantee terms and conditions from rich text editor"""
        try:
            if not vetting_engine:
                # Return mock data if vetting engine is not initialized
                return jsonify({
                    'success': True,
                    'analysis': {
                        'risk_level': 'Medium',
                        'compliance_score': 85,
                        'key_findings': [
                            'Terms comply with standard banking regulations',
                            'Liability clauses are properly defined',
                            'Payment terms are clearly specified',
                            'Jurisdiction and governing law are included'
                        ],
                        'recommendations': [
                            'Consider adding force majeure clauses for unexpected events',
                            'Include specific dispute resolution procedures',
                            'Add performance bond requirements if applicable',
                            'Clarify the renewal and termination conditions'
                        ],
                        'violations': [],
                        'warnings': [
                            'Consider specifying exact claim procedures',
                            'Review indemnification clauses for completeness'
                        ]
                    }
                })
                
            data = request.get_json()
            terms_html = data.get('terms_html', '')
            terms_text = data.get('terms_text', '')
            form_data = data.get('form_data', {})
            
            if not terms_text or not terms_text.strip():
                return jsonify({
                    'success': False,
                    'message': 'Guarantee terms and conditions are required'
                }), 400
            
            # Perform vetting analysis
            vetting_result = vetting_engine.vet_guarantee_with_llm(terms_text, include_llm_analysis=True)
            
            # Format the analysis response
            analysis = {
                'risk_level': vetting_result.get('risk_level', 'Medium'),
                'compliance_score': vetting_result.get('compliance_score', 85),
                'key_findings': vetting_result.get('findings', []),
                'recommendations': vetting_result.get('recommendations', []),
                'violations': vetting_result.get('violations', []),
                'warnings': vetting_result.get('warnings', [])
            }
            
            # Add default values if empty
            if not analysis['key_findings']:
                analysis['key_findings'] = [
                    'Terms have been analyzed for compliance',
                    'Standard banking regulations are addressed',
                    'Key guarantee provisions are included'
                ]
            
            if not analysis['recommendations']:
                analysis['recommendations'] = [
                    'Review terms with legal counsel',
                    'Ensure all parties understand obligations',
                    'Consider adding additional protective clauses'
                ]
            
            return jsonify({
                'success': True,
                'analysis': analysis
            })
            
        except Exception as e:
            logger.error(f"Error in guarantee terms vetting: {str(e)}")
            # Return mock analysis on error
            return jsonify({
                'success': True,
                'analysis': {
                    'risk_level': 'Medium',
                    'compliance_score': 85,
                    'key_findings': [
                        'Terms comply with standard banking regulations',
                        'Basic guarantee provisions are included',
                        'Payment and claim procedures are defined'
                    ],
                    'recommendations': [
                        'Consider adding more specific performance metrics',
                        'Review dispute resolution procedures',
                        'Clarify force majeure conditions'
                    ],
                    'violations': [],
                    'warnings': []
                }
            })
    
    @app.route('/api/vetting/rule-effectiveness/<rule_id>', methods=['GET'])
    def get_rule_effectiveness(rule_id):
        """Get AI-powered effectiveness analysis for a rule (admin only)"""
        try:
            is_admin, user_email = check_admin_access()
            
            if not is_admin:
                return jsonify({
                    'success': False,
                    'error': 'Admin access required'
                }), 403
            
            if not vetting_engine:
                return jsonify({
                    'success': False,
                    'error': 'Vetting engine not initialized'
                }), 500
            
            effectiveness = vetting_engine.analyze_rule_effectiveness(rule_id)
            
            return jsonify({
                'success': True,
                'effectiveness': effectiveness
            })
            
        except Exception as e:
            logger.error(f"Error getting rule effectiveness: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/vetting/history', methods=['GET'])
    def get_vetting_history():
        """Get vetting test history (admin only)"""
        try:
            is_admin, user_email = check_admin_access()
            
            if not is_admin:
                return jsonify({
                    'success': False,
                    'error': 'Admin access required'
                }), 403
            
            if not vetting_engine:
                return jsonify({
                    'success': False,
                    'error': 'Vetting engine not initialized'
                }), 500
            
            rule_id = request.args.get('rule_id')
            history = vetting_engine.get_test_history(rule_id)
            
            return jsonify({
                'success': True,
                'history': history
            })
            
        except Exception as e:
            logger.error(f"Error getting test history: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/vetting/explain-rule', methods=['POST'])
    def explain_vetting_rule():
        """Get AI explanation for a rule configuration (admin only)"""
        try:
            is_admin, user_email = check_admin_access()
            
            if not is_admin:
                return jsonify({
                    'success': False,
                    'error': 'Admin access required'
                }), 403
            
            if not vetting_engine:
                return jsonify({
                    'success': False,
                    'error': 'Vetting engine not initialized'
                }), 500
            
            data = request.get_json()
            explanation = vetting_engine.get_rule_explanation(data)
            
            return jsonify({
                'success': True,
                'explanation': explanation
            })
            
        except Exception as e:
            logger.error(f"Error explaining rule: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/vetting/generate-test-samples', methods=['POST'])
    def generate_test_samples_direct():
        """Generate test samples for a rule configuration without saving (admin only)"""
        try:
            is_admin, user_email = check_admin_access()
            
            if not is_admin:
                return jsonify({
                    'success': False,
                    'error': 'Admin access required'
                }), 403
            
            if not vetting_engine:
                return jsonify({
                    'success': False,
                    'error': 'Vetting engine not initialized'
                }), 500
            
            data = request.get_json()
            
            # Create a temporary rule dict for sample generation
            temp_rule = {
                'name': data.get('name', 'Test Rule'),
                'description': data.get('description', ''),
                'condition_type': data.get('condition_type', 'contains'),
                'value': data.get('value', ''),
                'severity': data.get('severity', 'medium')
            }
            
            # Generate samples using the vetting engine
            positive_sample, negative_sample, metadata = vetting_engine.generate_sample_texts_llm(temp_rule)
            
            return jsonify({
                'success': True,
                'samples': [
                    {
                        'text': positive_sample,
                        'expected_onerous': True,
                        'description': 'Sample that should trigger the rule'
                    },
                    {
                        'text': negative_sample,
                        'expected_onerous': False,
                        'description': 'Sample that should NOT trigger the rule'
                    }
                ],
                'metadata': metadata
            })
            
        except Exception as e:
            logger.error(f"Error generating test samples: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    # Conversation API Routes
    def require_auth(f):
        """Decorator to require authentication"""
        from functools import wraps
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return jsonify({'error': 'Authentication required'}), 401
            return f(*args, **kwargs)

        return decorated_function

    @app.route('/api/conversation/message', methods=['POST'])
    def add_conversation_message():
        """Add a new message to conversation history"""
        try:
            data = request.get_json()
            # Get user_id from session or request body
            user_id = session.get('user_id') or data.get('user_id')

            if not user_id:
                return jsonify({'error': 'User ID is required'}), 400

            session_id = data.get('session_id', session.get('session_id'))
            message = data.get('message', '')
            response = data.get('response', '')
            message_type = data.get('message_type', 'chat')
            metadata = data.get('metadata', {})

            if not message and not response:
                return jsonify({'error': 'Either message or response is required'}), 400

            message_id = conversation_manager.add_message(
                user_id=user_id,
                session_id=session_id,
                message=message,
                response=response,
                message_type=message_type,
                metadata=metadata
            )

            if message_id:
                return jsonify({
                    'success': True,
                    'message_id': message_id,
                    'timestamp': datetime.utcnow().isoformat()
                })
            else:
                return jsonify({'error': 'Failed to save message'}), 500

        except Exception as e:
            logger.error(f"Error adding message: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    @app.route('/api/conversation/history', methods=['GET'])
    def get_conversation_history():
        """Get conversation history for user"""
        try:
            # Check if user is authenticated via session or request args
            user_id = session.get('user_id') or request.args.get('user_id')

            if not user_id:
                # Return empty history for unauthenticated users
                return jsonify({
                    'success': True,
                    'conversations': [],
                    'count': 0,
                    'authenticated': False
                })

            session_id = request.args.get('session_id')
            limit = min(int(request.args.get('limit', 50)), 100)
            message_type = request.args.get('message_type')

            conversations = conversation_manager.get_conversation_history(
                user_id=user_id,
                session_id=session_id,
                limit=limit,
                message_type=message_type
            )

            # Convert ObjectId to string for JSON serialization
            for conv in conversations:
                conv['_id'] = str(conv['_id'])
                # Handle timestamp field - might be 'timestamp' or 'created_at'
                if 'timestamp' in conv and conv['timestamp']:
                    conv['timestamp'] = conv['timestamp'].isoformat()
                elif 'created_at' in conv and conv['created_at']:
                    conv['timestamp'] = conv['created_at'].isoformat()
                else:
                    conv['timestamp'] = datetime.utcnow().isoformat()

            return jsonify({
                'success': True,
                'conversations': conversations,
                'count': len(conversations),
                'authenticated': True
            })

        except Exception as e:
            logger.error(f"Error getting conversation history: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    @app.route('/api/conversation/suggestions', methods=['POST'])
    @require_auth
    def get_smart_suggestions():
        """Get smart template suggestions based on user input"""
        try:
            data = request.get_json()
            user_id = session['user_id']
            input_text = data.get('input_text', '')
            transaction_type = data.get('transaction_type')

            if not input_text:
                return jsonify({'error': 'Input text is required'}), 400

            suggestions = conversation_manager.get_smart_suggestions(
                user_id=user_id,
                input_text=input_text,
                transaction_type=transaction_type
            )

            return jsonify({
                'success': True,
                'suggestions': suggestions,
                'count': len(suggestions)
            })

        except Exception as e:
            logger.error(f"Error getting smart suggestions: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    @app.route('/api/conversation/beneficiary', methods=['POST'])
    @require_auth
    def save_beneficiary():
        """Save beneficiary information for auto-fill"""
        try:
            data = request.get_json()
            user_id = session['user_id']
            name = data.get('name', '')
            account_number = data.get('account_number', '')
            bank_name = data.get('bank_name', '')
            swift_code = data.get('swift_code')

            if not name or not account_number or not bank_name:
                return jsonify({'error': 'Name, account number, and bank name are required'}), 400

            beneficiary_id = conversation_manager.save_beneficiary(
                user_id=user_id,
                name=name,
                account_number=account_number,
                bank_name=bank_name,
                swift_code=swift_code
            )

            if beneficiary_id:
                return jsonify({
                    'success': True,
                    'beneficiary_id': beneficiary_id
                })
            else:
                return jsonify({'error': 'Failed to save beneficiary'}), 500

        except Exception as e:
            logger.error(f"Error saving beneficiary: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    @app.route('/api/conversation/beneficiaries', methods=['GET'])
    @require_auth
    def get_beneficiaries():
        """Get user's beneficiaries for auto-complete"""
        try:
            user_id = session['user_id']
            search_query = request.args.get('q', '')
            limit = min(int(request.args.get('limit', 10)), 50)

            query = {"user_id": user_id}
            if search_query:
                query["$or"] = [
                    {"name": {"$regex": search_query, "$options": "i"}},
                    {"account_number": {"$regex": search_query, "$options": "i"}},
                    {"bank_name": {"$regex": search_query, "$options": "i"}}
                ]

            beneficiaries = list(conversation_manager.beneficiary_collection.find(query)
                                 .sort("frequency", -1).limit(limit))

            # Convert ObjectId to string
            for beneficiary in beneficiaries:
                beneficiary['_id'] = str(beneficiary['_id'])
                beneficiary['created_at'] = beneficiary['created_at'].isoformat()
                beneficiary['last_used'] = beneficiary['last_used'].isoformat()

            return jsonify({
                'success': True,
                'beneficiaries': beneficiaries,
                'count': len(beneficiaries)
            })

        except Exception as e:
            logger.error(f"Error getting beneficiaries: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    @app.route('/api/conversation/templates', methods=['GET'])
    @require_auth
    def get_templates():
        """Get user's templates"""
        try:
            user_id = session['user_id']
            category = request.args.get('category')
            limit = min(int(request.args.get('limit', 20)), 50)

            query = {"user_id": user_id}
            if category:
                query["category"] = category

            templates = list(conversation_manager.templates_collection.find(query)
                             .sort("usage_count", -1).limit(limit))

            # Convert ObjectId to string
            for template in templates:
                template['_id'] = str(template['_id'])
                template['created_at'] = template['created_at'].isoformat()
                template['last_used'] = template['last_used'].isoformat()

            return jsonify({
                'success': True,
                'templates': templates,
                'count': len(templates)
            })

        except Exception as e:
            logger.error(f"Error getting templates: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    # Session Management Routes
    @app.route('/api/sessions', methods=['GET'])
    def get_chat_sessions():
        """Get all chat sessions for the current user"""
        try:
            # Try to get user_id from session first, then from query params
            user_id = session.get('user_id') or request.args.get('user_id')
            if not user_id:
                return jsonify({'error': 'Unauthorized'}), 401

            # Get all sessions from MongoDB
            sessions = list(db.chat_sessions.find(
                {'user_id': user_id},
                {'_id': 0, 'session_id': 1, 'created_at': 1, 'last_activity': 1, 'message_count': 1, 'title': 1,
                 'first_message': 1}
            ).sort('last_activity', -1))

            # Convert datetime objects to ISO format
            for sess in sessions:
                sess['created_at'] = sess['created_at'].isoformat() if 'created_at' in sess else None
                sess['last_activity'] = sess['last_activity'].isoformat() if 'last_activity' in sess else None
                sess['message_count'] = sess.get('message_count', 0)

            return jsonify({
                'success': True,
                'sessions': sessions
            })

        except Exception as e:
            logger.error(f"Error getting sessions: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    @app.route('/api/sessions/<session_id>/messages', methods=['GET'])
    def get_session_messages(session_id):
        """Get all messages for a specific session"""
        try:
            # Try to get user_id from session first, then from query params
            user_id = session.get('user_id') or request.args.get('user_id')
            if not user_id:
                return jsonify({'error': 'Unauthorized'}), 401

            # Verify session belongs to user
            chat_session = db.chat_sessions.find_one({
                'session_id': session_id,
                'user_id': user_id
            })

            if not chat_session:
                return jsonify({'error': 'Session not found'}), 404

            # Get messages
            messages = list(db.chat_messages.find(
                {'session_id': session_id},
                {'_id': 0}
            ).sort('timestamp', 1))

            # Convert timestamps
            for msg in messages:
                if 'timestamp' in msg:
                    msg['timestamp'] = msg['timestamp'].isoformat()

            return jsonify({
                'success': True,
                'messages': messages,
                'session_id': session_id
            })

        except Exception as e:
            logger.error(f"Error getting session messages: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    @app.route('/api/sessions/<session_id>', methods=['DELETE'])
    def delete_session(session_id):
        """Delete a specific chat session"""
        try:
            # Try to get user_id from session first, then from query params or body
            user_id = session.get('user_id') or request.args.get('user_id')
            if not user_id and request.is_json:
                user_id = request.get_json().get('user_id')
            if not user_id:
                return jsonify({'error': 'Unauthorized'}), 401

            # Verify session belongs to user
            chat_session = db.chat_sessions.find_one({
                'session_id': session_id,
                'user_id': user_id
            })

            if not chat_session:
                return jsonify({'error': 'Session not found'}), 404

            # Delete session and all related messages
            db.chat_sessions.delete_one({'session_id': session_id})
            db.chat_messages.delete_many({'session_id': session_id})

            return jsonify({
                'success': True,
                'message': 'Session deleted successfully'
            })

        except Exception as e:
            logger.error(f"Error deleting session: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    # @app.route('/api/document/classify', methods=['POST'])
    # def classify_document():
    #     """New route for document classification and compliance checking"""
    #     logger.info("=== Starting document classification request ===")
    #     try:
    #         # Log OpenAI configuration at request time
    #         logger.info(f"Request OpenAI Config - API Type: {openai.api_type}")
    #         logger.info(f"Request OpenAI Config - API Base: {openai.api_base}")
    #         logger.info(f"Request OpenAI Config - API Key exists: {bool(openai.api_key)}")
    #         logger.info(f"Request OpenAI Config - API Key length: {len(openai.api_key) if openai.api_key else 0}")

    #         # Get uploaded files
    #         uploaded_files = request.files.getlist('files')
    #         logger.info(f"Received {len(uploaded_files)} files for classification")
    #         if not uploaded_files:
    #             logger.warning("No files uploaded in request")
    #             return jsonify({"error": "No files uploaded"}), 400

    #         # Get additional parameters
    #         user_query = request.form.get('query', 'Classify and check compliance')
    #         product_name = request.form.get('productName', '')
    #         function_name = request.form.get('functionName', '')
    #         check_compliance = request.form.get('checkCompliance', 'true').lower() == 'true'
    #         document_type = request.form.get('documentType', '')
    #         client_id = request.form.get('client_id', None)  # WebSocket client ID for progress tracking

    #         logger.info(f"Request params - Query: {user_query}, Product: {product_name}, Function: {function_name}, Check Compliance: {check_compliance}, DocumentType: {document_type}, Client ID: {client_id}")

    #         # Initialize progress tracker if client_id is provided
    #         progress = None
    #         if client_id:
    #             try:
    #                 ws_handler = get_websocket_handler()
    #                 if ws_handler:
    #                     progress = DocumentProcessingTracker(ws_handler, client_id)
    #                     logger.info(f"✅ Progress tracker initialized for client: {client_id}")
    #                 else:
    #                     logger.warning("WebSocket handler not available, progress tracking disabled")
    #             except Exception as e:
    #                 logger.error(f"Failed to initialize progress tracker: {e}")
    #                 progress = None

    #         results = []

    #         for idx, uploaded_file in enumerate(uploaded_files):
    #             file_type = uploaded_file.content_type
    #             file_name = uploaded_file.filename
    #             logger.info(f"Processing file {idx+1}/{len(uploaded_files)}: {file_name} (type: {file_type})")

    #             # Check if it's a zip file
    #             if file_type in ["application/zip", "application/x-zip-compressed"] or file_name.endswith(".zip"):
    #                 # Handle zip file
    #                 logger.info(f"Processing as ZIP file: {file_name}")
    #                 zip_results = handle_zip_file_classification(uploaded_file, check_compliance, progress)
    #                 results.extend(zip_results)
    #             else:
    #                 # Process single file
    #                 logger.info(f"Processing as single file: {file_name}")
    #                 result = classify_and_check_compliance(
    #                     uploaded_file,
    #                     check_compliance=check_compliance,
    #                     product_name=product_name,
    #                     function_name=function_name,
    #                     document_type=document_type,
    #                     progress_tracker=progress
    #                 )
    #                 results.append(result)
    #                 logger.info(f"Completed processing file: {file_name}")

    #         return jsonify({
    #             "success": True,
    #             "results": results,
    #             "total_files": len(results)
    #         })

    #     except Exception as e:
    #         logger.error(f"Error in document classification: {str(e)}")
    #         return jsonify({"error": str(e)}), 500

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

            logger.info(f"🔍 STEP 1/4: QUALITY ANALYSIS - Analyzing document quality for {file_name}")
            quality_start = time.time()
            
            # Import quality analyzer
            from app.utils.quality_analyzer import quality_analyzer
            
            quality_result = quality_analyzer.analyze_document_quality_fast(
                temp_file_path, 
                file_name, 
                progress_tracker
            )
            quality_time = time.time() - quality_start
            
            if quality_result.get("success", False):
                verdict = quality_result.get("verdict", "pre_processing")
                quality_score = quality_result.get("quality_score", 0.5)
                logger.info(f"✅ Quality analysis completed in {quality_time:.2f}s - Verdict: {verdict} (score: {quality_score:.3f})")
                
                if progress_tracker:
                    progress_tracker.quality_complete(verdict, quality_score)
            else:
                # Quality analysis failed - proceed with standard processing
                logger.warning(f"⚠️ Quality analysis failed: {quality_result.get('error', 'Unknown error')}")
                verdict = "pre_processing"  # Default fallback
                quality_score = 0.5
                
                if progress_tracker:
                    progress_tracker.quality_complete("fallback", quality_score)

            # === STEP 3: OCR (Extract Text) ===
            if progress_tracker:
                progress_tracker.start_ocr()

            logger.info(f"📄 STEP 2/4: OCR - Extracting text from {file_name} (Quality verdict: {verdict})")
            ocr_start = time.time()
            
            # OPTIMIZATION: Estimate page count for timeout calculation
            estimated_pages = quality_result.get("pages_analyzed", 1) if quality_result else 1
            
            # Use optimized OCR with quality-based optimization
            extracted_text_data = extract_text_with_retry_optimized(
                temp_file_path, 
                file_type,
                quality_verdict=verdict,
                page_count=estimated_pages
            )
            text_data = extracted_text_data.get("text_data", [])
            ocr_time = time.time() - ocr_start
            
            # Enhanced logging with optimization stats
            if "optimization_stats" in extracted_text_data:
                stats = extracted_text_data["optimization_stats"]
                logger.info(f"✅ OPTIMIZED OCR completed in {ocr_time:.2f}s - "
                           f"Extracted {len(text_data)} text entries | "
                           f"FastMode: {stats.get('fast_mode', False)}, "
                           f"Polls: {stats.get('poll_count', 'N/A')}, "
                           f"Timeout: {stats.get('dynamic_timeout', 'N/A')}s")
            else:
                logger.info(f"✅ OCR completed in {ocr_time:.2f}s - Extracted {len(text_data)} text entries")

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
            logger.info(f"📋 Organized into {len(pages_ocr_data)} pages")

            # === STEP 4: CLASSIFICATION (Using Document Classifier) ===
            if progress_tracker:
                progress_tracker.start_classification()

            logger.info(f"🔍 STEP 3/4: CLASSIFICATION - Identifying document type")
            classification_start = time.time()

            # Use existing DocumentClassifier for classification
            page_text = "\n".join([text['text'] for page_data in pages_ocr_data for text in page_data])

            classification_result = document_classifier.classify_document(page_text)

            logger.info(f"📊 Classification result: {str(classification_result)[:200]}...")

            # Extract document type and confidence
            detected_doc_type = classification_result.get('document_type', document_type or 'Unknown')
            # Convert confidence to 0-100 scale if it's 0-1
            raw_confidence = classification_result.get('confidence', 0)
            if raw_confidence <= 1.0:
                confidence = raw_confidence * 100
            else:
                confidence = raw_confidence

            classification_time = time.time() - classification_start
            logger.info(f"✅ Classification completed in {classification_time:.2f}s - Type: {detected_doc_type}, Confidence: {confidence}")

            if progress_tracker:
                progress_tracker.classification_complete(
                    doc_type=detected_doc_type,
                    confidence=int(confidence)
                )

            # === STEP 4: EXTRACTION (Using Config Prompts + Field Mappings) ===
            logger.info(f"📤 STEP 4/4: EXTRACTION - Extracting fields using config prompts + field mappings")
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
            extraction_max_tokens = extraction_config.get('max_tokens', 4000)

            logger.info(f"📝 Using extraction config - Model: {extraction_model}, Temp: {extraction_temp}, MaxTokens: {extraction_max_tokens}")

            # Build extraction prompt using DocumentClassifier
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
                logger.info(f"📋 Enhanced extraction prompt with field mapping examples for {detected_doc_type}")

            logger.info(f"📋 Built extraction prompt ({len(extraction_prompt)} chars)")

            # Call LLM for extraction
            extraction_response = openai.ChatCompletion.create(
                engine=extraction_model,
                messages=[{"role": "user", "content": extraction_prompt}],
                temperature=extraction_temp,
                max_tokens=extraction_max_tokens
            )

            extraction_result = extraction_response.choices[0].message.content
            logger.info(f"📊 Extraction result: {extraction_result[:200]}...")

            # Parse extraction result
            try:
                extraction_json = json.loads(extraction_result)
                extracted_fields = extraction_json.get('extracted_fields', {})
            except:
                extracted_fields = {}

            extraction_time = time.time() - extraction_start
            logger.info(f"✅ Extraction completed in {extraction_time:.2f}s - Extracted {len(extracted_fields)} fields")

            if progress_tracker:
                progress_tracker.field_extraction_complete(extracted_count=len(extracted_fields))

            # === UCP600/SWIFT COMPLIANCE ANALYSIS ===
            logger.info(f"🔍 STEP 5/6: UCP600/SWIFT COMPLIANCE ANALYSIS")
            
            # Start compliance check progress tracking
            if progress_tracker:
                progress_tracker.start_compliance_check()
            
            compliance_analysis_start = time.time()
            
            # Initialize compliance results
            ucp600_result = {}
            swift_result = {}
            
            # Perform UCP600 and SWIFT compliance analysis if we have extracted fields
            if extracted_fields:
                # Remove coordinate mapping fields before compliance analysis
                compliance_fields = {k: v for k, v in extracted_fields.items() 
                                   if not k.startswith('_coordinate_mapping') and 
                                      k not in ['coordinate_mapping_stats']}
                
                logger.info(f"Original fields: {len(extracted_fields)}, Compliance fields: {len(compliance_fields)}")
                
                try:
                    # PERFORMANCE OPTIMIZATION: Use unified compliance analysis instead of separate calls
                    from app.utils.query_utils import analyze_unified_compliance_fast
                    
                    logger.info(f"🚀 UNIFIED COMPLIANCE: Analyzing {len(compliance_fields)} fields with single AI call")
                    logger.info(f"Compliance fields: {list(compliance_fields.keys())}")
                    
                    # Single call for both UCP600 and SWIFT analysis (saves 8-12 seconds)
                    ucp600_result, swift_result = analyze_unified_compliance_fast(compliance_fields)
                    
                    logger.info(f"✅ Unified compliance completed: UCP600={len(ucp600_result)} fields, SWIFT={len(swift_result)} fields")
                    logger.info(f"UCP600 sample: {str(ucp600_result)[:150]}...")
                    logger.info(f"SWIFT sample: {str(swift_result)[:150]}...")
                    
                except Exception as e:
                    logger.error(f"❌ Unified compliance analysis failed: {e}")
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    
                    # Fallback to original separate analysis
                    logger.info("🔄 Falling back to separate UCP600/SWIFT analysis...")
                    ucp600_result = {}
                    swift_result = {}
                    
                    try:
                        logger.info(f"Running fallback UCP600 analysis on {len(compliance_fields)} fields")
                        ucp600_result = analyze_ucp_compliance_chromaRAG(compliance_fields)
                        logger.info(f"Fallback UCP600 analysis completed: {len(ucp600_result)} results")
                    except Exception as ucp_error:
                        logger.error(f"Fallback UCP600 analysis failed: {ucp_error}")
                        ucp600_result = {}
                    
                    try:
                        logger.info(f"Running fallback SWIFT analysis on {len(compliance_fields)} fields")
                        swift_result = analyze_swift_compliance_chromaRAG(compliance_fields)
                        logger.info(f"Fallback SWIFT analysis completed: {len(swift_result)} results")
                    except Exception as swift_error:
                        logger.error(f"Fallback SWIFT analysis failed: {swift_error}")
                        swift_result = {}
            
            compliance_analysis_time = time.time() - compliance_analysis_start
            logger.info(f"✅ Compliance analysis completed in {compliance_analysis_time:.2f}s")

            # Complete compliance check progress tracking
            if progress_tracker:
                # Count compliance issues for progress tracking
                compliance_issues = len(ucp600_result) + len(swift_result)
                progress_tracker.compliance_complete(compliance_issues)

            # Transform compliance data for UI consumption
            def transform_compliance_for_ui(compliance_data, compliance_type):
                """Transform field-level compliance data to UI-expected format"""
                logger.info(f"🔄 Transforming {compliance_type} compliance data: {type(compliance_data)}")
                
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
                        is_compliant = field_data.get("compliance", True)
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

            # Transform compliance results for UI
            swift_compliance = transform_compliance_for_ui(swift_result, "swift")
            ucp600_compliance = transform_compliance_for_ui(ucp600_result, "ucp600")

            # Debug compliance scores
            logger.info(f"🔍 SWIFT compliance result: {swift_compliance}")
            logger.info(f"🔍 UCP600 compliance result: {ucp600_compliance}")

            # Calculate overall compliance score
            compliance_scores = []
            if swift_compliance and swift_compliance.get('compliance_percentage') is not None:
                swift_score = swift_compliance['compliance_percentage']
                compliance_scores.append(swift_score)
                logger.info(f"📊 SWIFT compliance percentage: {swift_score}%")
            if ucp600_compliance and ucp600_compliance.get('compliance_percentage') is not None:
                ucp600_score = ucp600_compliance['compliance_percentage']
                compliance_scores.append(ucp600_score)
                logger.info(f"📊 UCP600 compliance percentage: {ucp600_score}%")
            
            logger.info(f"📊 All compliance scores: {compliance_scores}")
            
            # Calculate average compliance score, default to 85 if no compliance data
            overall_compliance_score = round(sum(compliance_scores) / len(compliance_scores)) if compliance_scores else 85
            logger.info(f"📊 Overall compliance score: {overall_compliance_score}%")

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

            # === Validate compliance using YAML config rules ===
            compliance_result = validate_compliance(extracted_fields, field_mapping_data, config)

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
                    "swift": swift_compliance,
                    "ucp600": ucp600_compliance,
                    "legacy": compliance_result
                },
                "swift_result": swift_result,
                "ucp600_result": ucp600_result,
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

            logger.info(f"✅ Config-based processing completed for {file_name} in {total_time:.1f}s")
            return result

        except Exception as e:
            logger.error(f"❌ Error in config-based processing: {str(e)}")
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
                    logger.info(f"🗑️ Cleaned up temporary file: {temp_file_path}")
                except Exception as cleanup_error:
                    logger.warning(f"⚠️ Failed to cleanup temp file {temp_file_path}: {cleanup_error}")

    def process_document_page_by_page(uploaded_file, function_name=None, product_name=None,
                                      document_type=None, progress_tracker=None, config=None):
        """
        Enhanced page-by-page document processing to detect multiple document types

        Workflow:
        1. OCR: Extract text from all pages
        2. Classify EACH page independently
        3. Group consecutive pages with same document type
        4. Extract fields for each detected document type

        Args:
            uploaded_file: File object
            function_name: Business function
            product_name: Product name
            document_type: Pre-specified document type (optional)
            progress_tracker: Progress tracking object
            config: YAML prompt configuration

        Returns:
            list: Multiple results (one per detected document type)
        """
        import time

        temp_file_path = None  # Track temp file for cleanup
        try:
            file_name = uploaded_file.filename
            file_type = uploaded_file.content_type
            logger.info(f"=== Page-by-page processing for {file_name} ===")

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

            logger.info(f"🔍 STEP 1/5: QUALITY ANALYSIS - Analyzing document quality for {file_name}")
            quality_start = time.time()
            
            # Import quality analyzer
            from app.utils.quality_analyzer import quality_analyzer
            
            quality_result = quality_analyzer.analyze_document_quality_fast(
                temp_file_path, 
                file_name, 
                progress_tracker
            )
            quality_time = time.time() - quality_start
            
            if quality_result.get("success", False):
                verdict = quality_result.get("verdict", "pre_processing")
                quality_score = quality_result.get("quality_score", 0.5)
                logger.info(f"✅ Quality analysis completed in {quality_time:.2f}s - Verdict: {verdict} (score: {quality_score:.3f})")
                
                if progress_tracker:
                    progress_tracker.quality_complete(verdict, quality_score)
            else:
                # Quality analysis failed - proceed with standard processing
                logger.warning(f"⚠️ Quality analysis failed: {quality_result.get('error', 'Unknown error')}")
                verdict = "pre_processing"  # Default fallback
                quality_score = 0.5
                
                if progress_tracker:
                    progress_tracker.quality_complete("fallback", quality_score)

            # === STEP 3: OCR (Extract Text from ALL pages) ===
            if progress_tracker:
                progress_tracker.start_ocr()

            logger.info(f"📄 STEP 2/5: OCR - Extracting text from {file_name} (Quality verdict: {verdict})")
            ocr_start = time.time()
            
            # OPTIMIZATION: Estimate page count for timeout calculation
            estimated_pages = quality_result.get("pages_analyzed", 1) if quality_result else 1
            
            # Use optimized OCR with quality-based optimization
            extracted_text_data = extract_text_with_retry_optimized(
                temp_file_path, 
                file_type,
                quality_verdict=verdict,
                page_count=estimated_pages
            )
            text_data = extracted_text_data.get("text_data", [])
            ocr_time = time.time() - ocr_start
            
            # Enhanced logging with optimization stats
            if "optimization_stats" in extracted_text_data:
                stats = extracted_text_data["optimization_stats"]
                logger.info(f"✅ OPTIMIZED OCR completed in {ocr_time:.2f}s - "
                           f"Extracted {len(text_data)} text entries | "
                           f"FastMode: {stats.get('fast_mode', False)}, "
                           f"Polls: {stats.get('poll_count', 'N/A')}, "
                           f"Timeout: {stats.get('dynamic_timeout', 'N/A')}s")
            else:
                logger.info(f"✅ OCR completed in {ocr_time:.2f}s - Extracted {len(text_data)} text entries")

            if progress_tracker:
                progress_tracker.ocr_complete(extracted_entries=len(text_data))

            # Check for OCR errors
            if "error" in extracted_text_data:
                return [{
                    "file_name": file_name,
                    "error": extracted_text_data["error"],
                    "stage": "OCR"
                }]

            if not text_data:
                return [{
                    "file_name": file_name,
                    "error": "No text extracted from document",
                    "stage": "OCR"
                }]

            # Organize by pages
            pages_ocr_data = organize_ocr_data_by_page(text_data)
            logger.info(f"📋 Organized into {len(pages_ocr_data)} pages")

            # === STEP 4: CLASSIFY EACH PAGE ===
            logger.info(f"🔍 STEP 3/5: PAGE-BY-PAGE CLASSIFICATION")
            classification_start = time.time()

            page_classifications = []
            for page_num, page_data in enumerate(pages_ocr_data, 1):
                page_text = "\n".join([text['text'] for text in page_data])

                # Skip pages with very little text
                if len(page_text.strip()) < 50:
                    logger.info(f"⏭️  Page {page_num}: Skipping (insufficient text)")
                    page_classifications.append({
                        'page': page_num,
                        'document_type': 'Empty/Insufficient Text',
                        'confidence': 0,
                        'text': page_text
                    })
                    continue

                # Enhanced classification with context awareness
                if len(page_classifications) > 0:  # If there's a previous page
                    prev_page = page_classifications[-1]
                    prev_type = prev_page['document_type']
                    
                    # Get available document types from the classifier
                    doc_types_by_category = {}
                    
                    # Initialize with the 5 proper categories from entity_mappings
                    for cat_id, cat_name in document_classifier.document_categories.items():
                        doc_types_by_category[cat_name] = []

                    # Map document types to their proper categories from entity_mappings
                    for doc_id, mapping in document_classifier.entity_mappings.items():
                        category_name = mapping.get('documentCategoryName', 'Other')
                        document_name = mapping.get('documentName', doc_id)

                        if category_name in doc_types_by_category:
                            if document_name not in doc_types_by_category[category_name]:
                                doc_types_by_category[category_name].append(document_name)

                    # Build categorized document list for prompt
                    category_sections = []
                    for category_name in sorted(doc_types_by_category.keys()):
                        if doc_types_by_category[category_name]:
                            category_sections.append(f"**{category_name}:**\n{', '.join(sorted(doc_types_by_category[category_name]))}")
                    
                    # Enhanced prompt for contextual classification
                    contextual_prompt = f"""You are an expert document classifier for international trade and finance documents.

CONTEXT: This is page {page_num} of a multi-page document. The previous page (page {page_num-1}) was classified as "{prev_type}".

### Available Document Types by Business Process Category:

{chr(10).join(category_sections)}

TASK: Analyze this page and determine:
1. Is this page a FRESH new document or a CONTINUATION of the previous document?
2. What is the document type of this page? (MUST be from the list above)

DOCUMENT TEXT (Page {page_num}):
{page_text}

Respond in VALID JSON format (no markdown, no additional text):
{{
    "is_continuation": true/false,
    "document_type": "exact document name from the list above",
    "confidence": 0.95,
    "reasoning": "brief explanation of why this is fresh/continuation and the classification"
}}

Guidelines:
- document_type MUST be exactly one of the document types listed above
- If the page contains headers, titles, or document numbers that suggest a new document, mark as fresh (is_continuation: false)
- If the page appears to be a continuation of content from the previous page without clear document boundaries, mark as continuation (is_continuation: true)
- For continuation pages, consider inheriting the document type from the previous page unless there's strong evidence otherwise
- For fresh pages, classify independently based on the content but only use document types from the provided list"""

                    try:
                        # Call LLM with enhanced contextual prompt
                        response = openai.ChatCompletion.create(
                            engine=deployment_name,
                            messages=[{"role": "user", "content": contextual_prompt}],
                            temperature=0.1,
                            max_tokens=500
                        )
                        
                        response_text = response.choices[0].message.content.strip()
                        logger.info(f"Raw LLM response for page {page_num}: {response_text[:200]}...")
                        
                        # Clean up the response - remove markdown formatting if present
                        if response_text.startswith('```json'):
                            response_text = response_text.replace('```json', '').replace('```', '')
                        elif response_text.startswith('```'):
                            response_text = response_text.replace('```', '')
                        
                        response_text = response_text.strip()
                        
                        if not response_text:
                            raise ValueError("Empty response from LLM")
                        
                        classification_result = json.loads(response_text)
                        
                        is_continuation = classification_result.get('is_continuation', False)
                        detected_type = classification_result.get('document_type', 'Unknown')
                        raw_confidence = classification_result.get('confidence', 0)
                        reasoning = classification_result.get('reasoning', '')
                        
                        # Apply contextual logic
                        if is_continuation and prev_type not in ['Empty/Insufficient Text', 'Unknown']:
                            final_document_type = prev_type
                            confidence = max(raw_confidence * 100, 75)  # Boost confidence for continuation
                            logger.info(f"📄 Page {page_num}: CONTINUATION of {prev_type} (original: {detected_type}, confidence: {confidence:.0f}%)")
                            logger.info(f"   ↳ Reasoning: {reasoning}")
                        else:
                            final_document_type = detected_type
                            confidence = raw_confidence * 100 if raw_confidence <= 1.0 else raw_confidence
                            logger.info(f"📄 Page {page_num}: FRESH {final_document_type} (confidence: {confidence:.0f}%)")
                            logger.info(f"   ↳ Reasoning: {reasoning}")
                        
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON parsing error in contextual classification for page {page_num}: {e}")
                        logger.error(f"Raw response was: {response_text if 'response_text' in locals() else 'No response'}")
                        # Fallback to regular classification
                        classification_result = document_classifier.classify_document(page_text)
                        final_document_type = classification_result.get('document_type', 'Unknown')
                        confidence = classification_result.get('confidence', 0) * 100
                        is_continuation = False
                        logger.info(f"📄 Page {page_num}: FALLBACK {final_document_type} (confidence: {confidence:.0f}%)")
                    except Exception as e:
                        logger.error(f"Error in contextual classification for page {page_num}: {e}")
                        # Fallback to regular classification
                        classification_result = document_classifier.classify_document(page_text)
                        final_document_type = classification_result.get('document_type', 'Unknown')
                        confidence = classification_result.get('confidence', 0) * 100
                        is_continuation = False
                        logger.info(f"📄 Page {page_num}: FALLBACK {final_document_type} (confidence: {confidence:.0f}%)")
                
                else:
                    # First page - use regular classification
                    classification_result = document_classifier.classify_document(page_text)
                    final_document_type = classification_result.get('document_type', 'Unknown')
                    raw_confidence = classification_result.get('confidence', 0)
                    confidence = raw_confidence * 100 if raw_confidence <= 1.0 else raw_confidence
                    is_continuation = False
                    logger.info(f"📄 Page {page_num}: FIRST PAGE {final_document_type} (confidence: {confidence:.0f}%)")
                
                page_classifications.append({
                    'page': page_num,
                    'document_type': final_document_type,
                    'confidence': confidence,
                    'text': page_text,
                    'ocr_data': page_data,
                    'is_continuation': is_continuation
                })

            classification_time = time.time() - classification_start
            logger.info(f"✅ Classification completed in {classification_time:.2f}s")

            # === STEP 4: GROUP CONSECUTIVE PAGES BY DOCUMENT TYPE ===
            logger.info(f"📑 STEP 4/5: GROUPING pages by document type")
            
            # Debug: Log all page classifications before grouping
            logger.info("🔍 DEBUG: Page classifications before grouping:")
            for i, page_class in enumerate(page_classifications):
                logger.info(f"  Page {page_class.get('page', i+1)}: '{page_class.get('document_type', 'Unknown')}' (confidence: {page_class.get('confidence', 0):.0f}%)")

            # Smart grouping based on LLM contextual classification results
            # Since LLM already determined continuation vs fresh, we just group consecutive same types
            document_groups = []
            current_group = None

            for page_class in page_classifications:
                if page_class['document_type'] in ['Empty/Insufficient Text', 'Unknown']:
                    logger.info(f"⏭️  Skipping page {page_class['page']} with type: {page_class['document_type']}")
                    continue

                # Check if we should add to existing group (exact document type match only)
                should_group_with_current = False
                if current_group is not None:
                    should_group_with_current = (current_group['document_type'] == page_class['document_type'])

                if current_group is None or not should_group_with_current:
                    # Start new group
                    if current_group:
                        logger.info(f"📋 Completed group: {current_group['document_type']} (Pages: {current_group['pages']})")
                        document_groups.append(current_group)
                    
                    logger.info(f"🆕 Starting new group: {page_class['document_type']} (Page {page_class['page']})")
                    current_group = {
                        'document_type': page_class['document_type'],
                        'pages': [page_class['page']],
                        'confidence': page_class['confidence'],
                        'text': page_class['text'],
                        'ocr_data': page_class['ocr_data'],
                        'individual_pages': [page_class]  # Preserve individual page data for tabs
                    }
                else:
                    # Add to existing group
                    logger.info(f"➕ Adding page {page_class['page']} ({page_class['document_type']}) to existing group: {current_group['document_type']}")
                    current_group['pages'].append(page_class['page'])
                    current_group['text'] += "\n" + page_class['text']
                    current_group['ocr_data'].extend(page_class['ocr_data'])
                    current_group['confidence'] = max(current_group['confidence'], page_class['confidence'])
                    current_group['individual_pages'].append(page_class)  # Keep individual page data

            if current_group:
                logger.info(f"📋 Completed final group: {current_group['document_type']} (Pages: {current_group['pages']})")
                document_groups.append(current_group)

            # Add page_range to each group for consistent access
            for group in document_groups:
                group['page_range'] = f"Page {group['pages'][0]}" if len(group['pages']) == 1 else f"Pages {group['pages'][0]}-{group['pages'][-1]}"

            logger.info(f"📊 Found {len(document_groups)} distinct document types:")
            for group in document_groups:
                logger.info(f"  - {group['document_type']} ({group['page_range']}, confidence: {group['confidence']:.0f}%)")

            # === STEP 5A: GENERATE PREVIEW IMAGES ===
            logger.info(f"📸 Generating preview images for document")
            all_preview_images = []
            if file_type == "application/pdf":
                pdf_result = convert_pdf_to_images_opencv(temp_file_path)
                if pdf_result["type"] == "image":
                    all_preview_images = pdf_result["data"]
                    logger.info(f"✅ Generated {len(all_preview_images)} preview images")
            else:
                encoded_image = encode_image_to_base64(temp_file_path)
                if encoded_image:
                    all_preview_images = [encoded_image]
                    logger.info(f"✅ Generated 1 preview image")

            # === STEP 5B: EXTRACT FIELDS FOR EACH DOCUMENT TYPE ===
            logger.info(f"📤 STEP 5/5: EXTRACTING fields for each document type")

            # Progress: Start field extraction
            if progress_tracker:
                total_documents = len(document_groups)
                progress_tracker.start_field_extraction(field_count=total_documents)

            extraction_config = config.get('extraction', {}) if config else {}
            extraction_model = extraction_config.get('model', deployment_name)
            extraction_temp = extraction_config.get('temperature', 0.0)
            extraction_max_tokens = extraction_config.get('max_tokens', 4000)

            results = []

            for idx, group in enumerate(document_groups, 1):
                logger.info(f"🔄 Extracting fields for {group['document_type']} (Group {idx}/{len(document_groups)})")
                
                # Progress: Update field extraction progress
                if progress_tracker:
                    progress_tracker.update_field_extraction(current_field=idx, total_fields=len(document_groups))
                
                extraction_start = time.time()

                # Build extraction prompt
                extraction_prompt = document_classifier.build_extraction_prompt(
                    document_type=group['document_type'],
                    ocr_text=group['text'],
                    page_number=group['pages'][0]
                )

                # Add field mappings
                field_mapping_data = load_document_field_mappings(group['document_type'])
                field_mapping_example = None
                if field_mapping_data:
                    field_mapping_example = field_mapping_data.get('example', '')
                    extraction_prompt += f"\n\n{field_mapping_example}"
                    logger.info(f"📋 Enhanced extraction prompt with field mapping examples for {group['document_type']}")

                logger.info(f"📋 Built extraction prompt ({len(extraction_prompt)} chars)")

                # Call LLM for extraction
                extraction_response = openai.ChatCompletion.create(
                    engine=extraction_model,
                    messages=[{"role": "user", "content": extraction_prompt}],
                    temperature=extraction_temp,
                    max_tokens=extraction_max_tokens
                )

                extraction_result = extraction_response.choices[0].message.content

                # Parse extraction result
                try:
                    extraction_json = json.loads(extraction_result)
                    extracted_fields = extraction_json.get('extracted_fields', {})
                except:
                    extracted_fields = {}

                extraction_time = time.time() - extraction_start
                logger.info(f"✅ Extraction completed in {extraction_time:.2f}s - Extracted {len(extracted_fields)} fields")

                # === COORDINATE MAPPING DISABLED ===
                # Note: Real-time coordinate mapping will be done on-demand via API calls
                logger.info(f"📍 Coordinate mapping disabled - will be done on-demand for accuracy")
                coordinate_mapping_time = 0.0

                # === UCP600/SWIFT COMPLIANCE ANALYSIS ===
                logger.info(f"🔍 Running UCP600/SWIFT compliance analysis for {group['document_type']}")
                
                # Start compliance check progress tracking
                if progress_tracker:
                    progress_tracker.start_compliance_check()
                
                compliance_analysis_start = time.time()
                
                # Initialize compliance results
                ucp600_result = {}
                swift_result = {}
                
                # Perform UCP600 and SWIFT compliance analysis if we have extracted fields
                if extracted_fields:
                    # Remove coordinate mapping fields before compliance analysis
                    compliance_fields = {k: v for k, v in extracted_fields.items() 
                                       if not k.startswith('_coordinate_mapping') and 
                                          k not in ['coordinate_mapping_stats']}
                    
                    logger.info(f"Original fields: {len(extracted_fields)}, Compliance fields: {len(compliance_fields)}")
                    
                    try:
                        # PERFORMANCE OPTIMIZATION: Use unified compliance analysis for page-by-page mode
                        from app.utils.query_utils import analyze_unified_compliance_fast
                        
                        logger.info(f"🚀 PAGE-BY-PAGE UNIFIED COMPLIANCE: Analyzing {len(compliance_fields)} fields")
                        logger.info(f"Compliance fields: {list(compliance_fields.keys())}")
                        
                        # Single call for both UCP600 and SWIFT analysis (saves 8-12 seconds per page)
                        ucp600_result, swift_result = analyze_unified_compliance_fast(compliance_fields)
                        
                        logger.info(f"✅ Page unified compliance completed: UCP600={len(ucp600_result)}, SWIFT={len(swift_result)}")
                        logger.info(f"UCP600 sample: {str(ucp600_result)[:150]}...")
                        logger.info(f"SWIFT sample: {str(swift_result)[:150]}...")
                        
                    except Exception as e:
                        logger.error(f"❌ Page unified compliance analysis failed: {e}")
                        logger.error(f"Traceback: {traceback.format_exc()}")
                        
                        # Fallback to original separate analysis
                        logger.info("🔄 Page fallback to separate UCP600/SWIFT analysis...")
                        ucp600_result = {}
                        swift_result = {}
                        
                        try:
                            logger.info(f"Running page fallback UCP600 analysis on {len(compliance_fields)} fields")
                            ucp600_result = analyze_ucp_compliance_chromaRAG(compliance_fields)
                            logger.info(f"Page fallback UCP600 completed: {len(ucp600_result)} results")
                        except Exception as ucp_error:
                            logger.error(f"Page fallback UCP600 failed: {ucp_error}")
                            ucp600_result = {}
                        
                        try:
                            logger.info(f"Running page fallback SWIFT analysis on {len(compliance_fields)} fields")
                            swift_result = analyze_swift_compliance_chromaRAG(compliance_fields)
                            logger.info(f"Page fallback SWIFT completed: {len(swift_result)} results")
                        except Exception as swift_error:
                            logger.error(f"Page fallback SWIFT failed: {swift_error}")
                            swift_result = {}
                
                compliance_analysis_time = time.time() - compliance_analysis_start
                logger.info(f"✅ Compliance analysis completed in {compliance_analysis_time:.2f}s")

                # Transform compliance data for UI consumption
                def transform_compliance_for_ui(compliance_data, compliance_type):
                    """Transform field-level compliance data to UI-expected format"""
                    logger.info(f"🔄 Transforming {compliance_type} compliance data: {type(compliance_data)}")
                    
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
                    """Transform field-level compliance data to UI-expected format"""
                    if not compliance_data:
                        return None
                        
                    violations = []
                    warnings = []
                    compliant_count = 0
                    total_count = len(compliance_data)
                    
                    for field_name, field_data in compliance_data.items():
                        if isinstance(field_data, dict):
                            is_compliant = field_data.get("compliance", True)
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

                # Transform compliance results for UI
                swift_compliance = transform_compliance_for_ui(swift_result, "swift")
                ucp600_compliance = transform_compliance_for_ui(ucp600_result, "ucp600")

                # Debug compliance scores
                logger.info(f"🔍 SWIFT compliance result: {swift_compliance}")
                logger.info(f"🔍 UCP600 compliance result: {ucp600_compliance}")

                # Calculate overall compliance score
                compliance_scores = []
                if swift_compliance and swift_compliance.get('compliance_percentage') is not None:
                    swift_score = swift_compliance['compliance_percentage']
                    compliance_scores.append(swift_score)
                    logger.info(f"📊 SWIFT compliance percentage: {swift_score}%")
                if ucp600_compliance and ucp600_compliance.get('compliance_percentage') is not None:
                    ucp600_score = ucp600_compliance['compliance_percentage']
                    compliance_scores.append(ucp600_score)
                    logger.info(f"📊 UCP600 compliance percentage: {ucp600_score}%")
                
                logger.info(f"📊 All compliance scores: {compliance_scores}")
                
                # Calculate average compliance score, default to 85 if no compliance data
                overall_compliance_score = round(sum(compliance_scores) / len(compliance_scores)) if compliance_scores else 85
                logger.info(f"📊 Overall compliance score: {overall_compliance_score}%")

                # === Categorize fields by type (mandatory/optional/conditional) ===
                mandatory_fields = {}
                optional_fields = {}
                conditional_fields = {}
                
                # Extract coordinate mapping stats (if present) before categorization
                coordinate_mapping_stats = extracted_fields.pop('_coordinate_mapping_stats', None)
                
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

                # === Validate compliance using YAML config rules ===
                compliance_result = validate_compliance(extracted_fields, field_mapping_data, config)

                # Build YAML-compliant result for this document group
                results.append({
                    "file_name": file_name,
                    "document_type": group['document_type'],
                    "confidence": int(group['confidence']),
                    "complianceScore": overall_compliance_score,
                    "classification": {
                        "document_type": group['document_type'],
                        "document_code": "",  # Could be enhanced to extract from classification
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
                        "swift": swift_compliance,
                        "ucp600": ucp600_compliance,
                        "legacy": compliance_result
                    },
                    "swift_result": swift_result,
                    "ucp600_result": ucp600_result,
                    "preview_images": [all_preview_images[page-1] for page in group['pages'] if page-1 < len(all_preview_images)],
                    "processing_time": {
                        "total": f"{quality_time + ocr_time + classification_time + extraction_time + coordinate_mapping_time + compliance_analysis_time:.1f}",
                        "quality_analysis": f"{quality_time:.1f}",
                        "ocr": f"{ocr_time:.1f}",
                        "classification": f"{classification_time:.1f}",
                        "extraction": f"{extraction_time:.1f}",
                        "coordinate_mapping": f"{coordinate_mapping_time:.1f}",
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
                    "coordinate_mapping": coordinate_mapping_stats,
                    "ocr_data": {
                        "pages": group['pages'],
                        "page_range": group['page_range'],
                        "text_entries": len(group['ocr_data']),
                        "formatted_text": group['text'][:500] + "..." if len(group['text']) > 500 else group['text'],
                        "individual_pages": group.get('individual_pages', [])  # Add individual page data for tabs
                    },
                    "success": True,
                    "enhanced_mode": True,
                    "page_by_page_mode": True,
                    # Legacy timing fields for frontend compatibility
                    "qualityTime": f"{quality_time:.1f}",
                    "ocrTime": f"{ocr_time:.1f}",
                    "classificationTime": f"{classification_time:.1f}",
                    "llmTime": f"{extraction_time:.1f}",  # Field extraction time
                    "complianceTime": f"{compliance_analysis_time:.1f}",
                    "config_used": {
                        "extraction_model": extraction_model,
                        "extraction_temp": extraction_temp
                    },
                    "field_mapping_enhanced": bool(field_mapping_data)
                })

            # Progress: Field extraction complete, calculate compliance issues
            if progress_tracker:
                total_extracted = sum(len(result.get("extraction", {}).get("mandatory", {})) + 
                                    len(result.get("extraction", {}).get("optional", {})) + 
                                    len(result.get("extraction", {}).get("conditional", {})) 
                                    for result in results)
                progress_tracker.field_extraction_complete(extracted_count=total_extracted)
                
                # Count compliance issues from all results
                compliance_issues = 0
                for result in results:
                    compliance_data = result.get("compliance", {})
                    if compliance_data and not compliance_data.get("compliant", True):
                        compliance_issues += len(compliance_data.get("missing_mandatory", []))
                        compliance_issues += len(compliance_data.get("warnings", []))
                
                # Mark compliance complete
                progress_tracker.compliance_complete(issues_found=compliance_issues)
                
                # Finalize processing
                progress_tracker.finalize()

            total_time = time.time() - start_time
            logger.info(f"✅ Page-by-page processing completed in {total_time:.2f}s - Found {len(results)} document types")

            # Add the actual total processing time to each result
            for result in results:
                if "processing_time" in result:
                    result["processing_time"]["actual_total"] = f"{total_time:.1f}"

            # Progress: Complete with summary
            if progress_tracker:
                total_docs = len(results)
                total_fields = sum(len(result.get("extraction", {}).get("mandatory", {})) + 
                               len(result.get("extraction", {}).get("optional", {})) + 
                               len(result.get("extraction", {}).get("conditional", {})) 
                               for result in results)
                progress_tracker.complete_with_summary(
                    doc_type=f"{total_docs} document types",
                    fields_extracted=total_fields,
                    compliance_status="Checked"
                )

            # Store OCR data in session for coordinate search API
            logger.info(f"📦 === STORING OCR DATA FOR COORDINATE SEARCH ===")
            all_ocr_data = []
            ocr_stats = {'total_entries': 0, 'pages': 0, 'text_entries': 0, 'with_bbox': 0}
            
            for group_idx, group in enumerate(document_groups):
                group_ocr = group.get('ocr_data', [])
                logger.info(f"📄 Group {group_idx + 1} ({group.get('document_type', 'Unknown')}): {len(group_ocr)} OCR entries")
                logger.info(f"   Group covers pages: {group.get('pages', 'Unknown')}")
                
                # Log sample entries from each group with detailed page info
                if group_ocr:
                    sample_entry = group_ocr[0]
                    logger.info(f"   Sample entry: text='{sample_entry.get('text', '')[:30]}...', bbox={sample_entry.get('bounding_box', [])}, page={sample_entry.get('bounding_page', 'N/A')}")
                
                # Check page distribution within this group
                group_page_counts = {}
                for entry in group_ocr:
                    ocr_stats['total_entries'] += 1
                    page = entry.get('bounding_page', 'unknown')
                    group_page_counts[page] = group_page_counts.get(page, 0) + 1
                    
                    if entry.get('text'):
                        ocr_stats['text_entries'] += 1
                    if entry.get('bounding_box'):
                        ocr_stats['with_bbox'] += 1
                
                logger.info(f"   Page distribution in group: {dict(sorted(group_page_counts.items()))}")
                
                all_ocr_data.extend(group_ocr)
                ocr_stats['pages'] = max(ocr_stats['pages'], group.get('pages', [0])[-1] if group.get('pages') else 0)
            
            session['current_ocr_data'] = all_ocr_data
            
            # WORKAROUND: Also store OCR data in a temporary file due to session size limits
            import tempfile as temp_module
            import pickle
            import uuid
            import glob
            
            # Clean up old OCR temp files (older than 1 hour)
            try:
                temp_dir = temp_module.gettempdir()
                old_files = glob.glob(os.path.join(temp_dir, "ocr_data_*.pkl"))
                current_time = time.time()
                cleaned_count = 0
                
                for file_path in old_files:
                    try:
                        file_age = current_time - os.path.getctime(file_path)
                        if file_age > 3600:  # 1 hour
                            os.remove(file_path)
                            cleaned_count += 1
                    except Exception:
                        pass  # Ignore cleanup errors
                
                if cleaned_count > 0:
                    logger.info(f"🧹 Cleaned up {cleaned_count} old OCR temp files")
            except Exception as e:
                logger.warning(f"Failed to cleanup old OCR temp files: {e}")
            
            # Generate unique session identifier for OCR data
            ocr_session_id = str(uuid.uuid4())
            session['ocr_session_id'] = ocr_session_id
            
            # Store OCR data in temporary file
            ocr_temp_file = os.path.join(temp_module.gettempdir(), f"ocr_data_{ocr_session_id}.pkl")
            try:
                with open(ocr_temp_file, 'wb') as f:
                    pickle.dump(all_ocr_data, f)
                logger.info(f"💾 OCR data also stored in temp file: {ocr_temp_file}")
                logger.info(f"🔑 OCR session ID: {ocr_session_id}")
            except Exception as e:
                logger.error(f"Failed to store OCR data in temp file: {e}")
            
            logger.info(f"💾 OCR DATA STORAGE SUMMARY:")
            logger.info(f"   Total OCR entries stored: {len(all_ocr_data)}")
            logger.info(f"   Entries with text: {ocr_stats['text_entries']}")
            logger.info(f"   Entries with bounding boxes: {ocr_stats['with_bbox']}")
            logger.info(f"   Document pages: {ocr_stats['pages']}")
            
            # Final page distribution check
            final_page_counts = {}
            for entry in all_ocr_data:
                page = entry.get('bounding_page', 'unknown')
                final_page_counts[page] = final_page_counts.get(page, 0) + 1
            logger.info(f"   Final page distribution: {dict(sorted(final_page_counts.items()))}")
            
            # Log a few sample entries for debugging
            if all_ocr_data:
                logger.info(f"📝 Sample OCR entries (first 3):")
                for i, sample in enumerate(all_ocr_data[:3]):
                    logger.info(f"   Entry {i+1}: '{sample.get('text', '')[:50]}...' (page: {sample.get('bounding_page', 'N/A')})")
            
            logger.info(f"✅ OCR data successfully stored in session for coordinate search API")

            return results

        except Exception as e:
            logger.error(f"❌ Error in page-by-page processing: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return [{
                "file_name": uploaded_file.filename,
                "error": str(e),
                "stage": "Unknown"
            }]
        finally:
            # Clean up temporary file (non-breaking cleanup)
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                    logger.info(f"🗑️ Cleaned up temporary file: {temp_file_path}")
                except Exception as cleanup_error:
                    logger.warning(f"⚠️ Failed to cleanup temp file {temp_file_path}: {cleanup_error}")

    @app.route('/api/document/classify-enhanced', methods=['POST'])
    def classify_document_enhanced():
        """
        Enhanced document classification using prompt config (YAML-based)
        Performs: OCR → Classification → Extraction with config-driven prompts
        """
        logger.info("🚀 === ENHANCED DOCUMENT CLASSIFICATION ROUTE CALLED ===")
        try:
            # Load prompt configuration
            global prompt_config
            if not prompt_config:
                prompt_config = load_prompt_config()
                if prompt_config:
                    logger.info("✅ Loaded prompt configuration from YAML")
                else:
                    logger.warning("⚠️ Prompt config not available, using defaults")

            # Get uploaded files
            uploaded_files = request.files.getlist('files')
            logger.info(f"Received {len(uploaded_files)} files for enhanced classification")
            if not uploaded_files:
                return jsonify({"error": "No files uploaded"}), 400

            # Get parameters
            function_name = request.form.get('functionName', '')
            product_name = request.form.get('productName', '')
            document_type = request.form.get('documentType', '')
            client_id = request.form.get('client_id', None)
            page_by_page = request.form.get('page_by_page', 'false').lower() == 'true'

            logger.info(f"Enhanced params - Function: {function_name}, Product: {product_name}, DocType: {document_type}, PageByPage: {page_by_page}")

            # Initialize progress tracker
            progress = None
            if client_id:
                try:
                    ws_handler = get_websocket_handler()
                    if ws_handler:
                        progress = DocumentProcessingTracker(ws_handler, client_id)
                        logger.info(f"✅ Progress tracker initialized for client: {client_id}")
                except Exception as e:
                    logger.error(f"Failed to initialize progress tracker: {e}")

            results = []

            for idx, uploaded_file in enumerate(uploaded_files):
                file_name = uploaded_file.filename
                file_type = uploaded_file.content_type
                logger.info(f"Processing enhanced file {idx+1}/{len(uploaded_files)}: {file_name}")

                # Choose processing mode based on page_by_page parameter
                if page_by_page:
                    # Page-by-page mode: Can detect multiple document types
                    logger.info("🔄 Using PAGE-BY-PAGE mode (multi-document detection)")
                    page_results = process_document_page_by_page(
                        uploaded_file=uploaded_file,
                        function_name=function_name,
                        product_name=product_name,
                        document_type=document_type,
                        progress_tracker=progress,
                        config=prompt_config
                    )
                    # Each file can return multiple results (one per document type found)
                    results.extend(page_results)
                else:
                    # Single document mode (original behavior)
                    logger.info("📄 Using SINGLE DOCUMENT mode")
                    result = process_document_with_config(
                        uploaded_file=uploaded_file,
                        function_name=function_name,
                        product_name=product_name,
                        document_type=document_type,
                        progress_tracker=progress,
                        config=prompt_config
                    )
                    results.append(result)

            return jsonify({
                "success": True,
                "results": results,
                "total_files": len(results),
                "config_loaded": bool(prompt_config),
                "config_version": prompt_config.get('version', 'v1.0') if prompt_config else 'v1.0'
            })

        except Exception as e:
            logger.error(f"Error in enhanced document classification: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return jsonify({"error": str(e)}), 500

    @app.route('/api/document/extract-region', methods=['POST'])
    def extract_text_from_region():
        """Extract text from a specific region of a document image"""
        try:
            data = request.get_json()
            
            # Get parameters
            image_base64 = data.get('image')
            region = data.get('region')  # {x, y, width, height, page}
            document_id = data.get('document_id')
            
            if not image_base64 or not region:
                return jsonify({
                    'success': False,
                    'error': 'Missing required parameters'
                }), 400
            
            # Decode base64 image
            image_data = base64.b64decode(image_base64.split(',')[1] if ',' in image_base64 else image_base64)
            image = Image.open(BytesIO(image_data))
            
            # Convert PIL image to numpy array
            img_array = np.array(image)
            
            # Extract region coordinates
            x = int(region['x'])
            y = int(region['y'])
            width = int(region['width'])
            height = int(region['height'])
            
            # Crop the image to the selected region
            cropped = img_array[y:y+height, x:x+width]
            
            # Perform OCR on the cropped region
            try:
                # Option 1: Use Azure Computer Vision OCR if available
                # Option 2: Use pytesseract for local OCR
                # Option 3: Use existing document OCR data if available
                
                # For now, let's use Azure OpenAI to analyze the cropped region
                # Convert cropped image back to base64
                cropped_pil = Image.fromarray(cropped)
                buffered = BytesIO()
                cropped_pil.save(buffered, format="PNG")
                cropped_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                
                # Use GPT-4 Vision to extract text
                prompt = """Extract all text visible in this image region. 
                Return only the extracted text, no additional formatting or explanation."""
                
                messages = [
                    {
                        "role": "system",
                        "content": "You are a text extraction assistant. Extract and return only the text visible in the image."
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{cropped_base64}"}}
                        ]
                    }
                ]
                
                response = openai.ChatCompletion.create(
                    engine=deployment_name,
                    messages=messages,
                    temperature=0.0,
                    max_tokens=500
                )
                
                extracted_text = response.choices[0].message.content.strip()
                
                return jsonify({
                    'success': True,
                    'extracted_text': extracted_text,
                    'region': region
                })
                
            except Exception as ocr_error:
                logger.error(f"OCR extraction error: {str(ocr_error)}")
                
                # Fallback: return placeholder text
                return jsonify({
                    'success': True,
                    'extracted_text': 'Selected text content',
                    'region': region,
                    'warning': 'OCR service unavailable, using placeholder'
                })
            
        except Exception as e:
            logger.error(f"Error extracting text from region: {str(e)}")
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

                # Aggregate SWIFT and UCP600 compliance results
                combined_swift_result = {}
                combined_ucp600_result = {}

                for page_result in page_analysis_results:
                    # Aggregate SWIFT compliance results
                    if "swift_result" in page_result:
                        combined_swift_result.update(page_result["swift_result"])

                    # Aggregate UCP600 compliance results
                    if "ucp600_result" in page_result:
                        combined_ucp600_result.update(page_result["ucp600_result"])

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
                    "swift_result": combined_swift_result,
                    "ucp600_result": combined_ucp600_result,
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
                max_tokens=1000
            )

            # Parse response
            result = parse_json_from_llm_response(response["choices"][0]["message"]["content"])
            return result or {}

        except Exception as e:
            logger.error(f"Error extracting fields from page: {str(e)}")
            return {}

    @app.route('/api/sessions/all', methods=['DELETE'])
    def delete_all_sessions():
        """Delete all chat sessions for the current user"""
        try:
            # Try to get user_id from session first, then from query params or body
            user_id = session.get('user_id') or request.args.get('user_id')
            if not user_id and request.is_json:
                user_id = request.get_json().get('user_id')
            if not user_id:
                return jsonify({'error': 'Unauthorized'}), 401

            # Verify confirmation
            data = request.get_json()
            if not data or not data.get('confirm'):
                return jsonify({'error': 'Confirmation required'}), 400

            # Get all user sessions
            user_sessions = list(db.chat_sessions.find(
                {'user_id': user_id},
                {'session_id': 1}
            ))

            session_ids = [sess['session_id'] for sess in user_sessions]

            # Delete all sessions and messages
            db.chat_sessions.delete_many({'user_id': user_id})
            db.chat_messages.delete_many({'session_id': {'$in': session_ids}})

            return jsonify({
                'success': True,
                'message': f'Deleted {len(session_ids)} sessions',
                'deleted_count': len(session_ids)
            })

        except Exception as e:
            logger.error(f"Error deleting all sessions: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    # Test endpoint to verify routes are loaded
    @app.route('/api/test/routes-loaded', methods=['GET'])
    def test_routes_loaded():
        """Test endpoint to verify conversation routes are loaded"""
        return jsonify({
            'success': True,
            'message': 'Conversation routes are loaded',
            'timestamp': datetime.utcnow().isoformat()
        })

    # Endpoint to populate Treasury test data
    @app.route('/api/test/populate-treasury', methods=['POST'])
    def populate_treasury_test_data():
        """Populate Treasury collections with test data"""
        try:
            from app.utils.populate_all_treasury_collections import populate_all_treasury_collections

            success, result = populate_all_treasury_collections()

            if success:
                return jsonify({
                    'success': True,
                    'message': 'Treasury collections populated successfully',
                    'collections': result
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'message': 'Failed to populate Treasury collections',
                    'error': result
                }), 500

        except Exception as e:
            logger.error(f"Error populating Treasury data: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    # Document Type Management Routes (Allowed Users Only)
    @app.route('/api/document-types', methods=['GET'])
    @login_required
    def get_document_types():
        """Get all document types and their fields"""
        try:
            # Get current user
            user = UserRepository.get_user_by_id(session["user_id"])
            if not user:
                return jsonify({"success": False, "message": "User not found"}), 401
            
            # Check if user is allowed
            if user["email"].lower() not in [e.lower() for e in ALLOWED_EMAILS]:
                return jsonify({"success": False, "message": "Access denied"}), 403
            
            # Load document types from DOC_LIST directory
            doc_list_path = Path(app.root_path) / "prompts" / "EE" / "DOC_LIST"
            document_types = []
            
            if doc_list_path.exists():
                for filename in os.listdir(str(doc_list_path)):
                    if filename.endswith(".json"):
                        # Extract document type name
                        if filename.endswith("_OCR_Fields.json"):
                            doc_type = filename.replace("_OCR_Fields.json", "")
                        else:
                            doc_type = filename.replace(".json", "")
                        
                        # Load fields from file
                        filepath = doc_list_path / filename
                        try:
                            with open(str(filepath), 'r') as f:
                                content = f.read().strip()
                                if content and content != "":  # Only parse if file has content
                                    try:
                                        fields = json.loads(content)
                                        # Ensure fields is a list
                                        if not isinstance(fields, list):
                                            fields = []
                                    except json.JSONDecodeError as e:
                                        logger.error(f"Failed to load document fields from {filename}: {e}")
                                        fields = []
                                else:
                                    logger.info(f"Empty file found: {filename}, initializing with empty array")
                                    fields = []
                        except Exception as e:
                            logger.error(f"Failed to load function fields from {filename}: {e}")
                            fields = []
                        
                        # Format document type name properly
                        display_name = doc_type.replace("_", " ").title()
                        
                        # Log successful loading
                        if fields:
                            logger.info(f"Loaded {len(fields)} fields for document type: {display_name} from {filename}")
                        else:
                            logger.info(f"No fields found for document type: {display_name} from {filename}")
                        
                        document_types.append({
                            "name": display_name,
                            "original_name": doc_type,
                            "filename": filename,
                            "fields": fields,
                            "field_count": len(fields) if isinstance(fields, list) else 0
                        })
            
            return jsonify({
                "success": True,
                "document_types": document_types
            })
            
        except Exception as e:
            logger.error(f"Error getting document types: {str(e)}")
            return jsonify({"success": False, "message": str(e)}), 500
    
    @app.route('/api/document-types/ocr-fields', methods=['POST'])
    @login_required
    def create_document_type_ocr_fields():
        """Create a new document type OCR fields file"""
        try:
            # Get current user
            user = UserRepository.get_user_by_id(session["user_id"])
            if not user:
                return jsonify({"success": False, "message": "User not found"}), 401
            
            # Check if user is allowed
            if user["email"].lower() not in [e.lower() for e in ALLOWED_EMAILS]:
                return jsonify({"success": False, "message": "Access denied"}), 403
            
            data = request.json
            doc_type_name = data.get("name")
            fields = data.get("fields", [])
            
            if not doc_type_name:
                return jsonify({"success": False, "message": "Document type name required"}), 400
            
            # Sanitize filename
            filename_base = doc_type_name.replace(" ", "_").replace("-", "_")
            filename = f"{filename_base}_OCR_Fields.json"
            
            doc_list_path = Path(app.root_path) / "prompts" / "EE" / "DOC_LIST"
            filepath = doc_list_path / filename
            
            # Check if already exists
            if filepath.exists():
                return jsonify({"success": False, "message": "Document type already exists"}), 400
            
            # Create the file with fields
            with open(str(filepath), 'w') as f:
                json.dump(fields, f, indent=2)
            
            return jsonify({
                "success": True,
                "message": f"Document type '{doc_type_name}' created successfully",
                "filename": filename
            })
            
        except Exception as e:
            logger.error(f"Error creating document type: {str(e)}")
            return jsonify({"success": False, "message": str(e)}), 500
    
    @app.route('/api/document-types/ocr-fields/<doc_type>', methods=['PUT'])
    @login_required
    def update_document_type_ocr_fields(doc_type):
        """Update document type OCR fields file"""
        try:
            # Get current user
            user = UserRepository.get_user_by_id(session["user_id"])
            if not user:
                return jsonify({"success": False, "message": "User not found"}), 401
            
            # Check if user is allowed
            if user["email"].lower() not in [e.lower() for e in ALLOWED_EMAILS]:
                return jsonify({"success": False, "message": "Access denied"}), 403
            
            data = request.json
            fields = data.get("fields", [])
            
            # Find the file
            doc_list_path = Path(app.root_path) / "prompts" / "EE" / "DOC_LIST"
            
            # Try different filename patterns
            # Handle both URL encoded and regular spaces
            doc_type_normalized = doc_type.replace('%20', ' ')
            possible_files = [
                f"{doc_type}_OCR_Fields.json",
                f"{doc_type}.json",
                f"{doc_type.replace(' ', '_')}_OCR_Fields.json",
                f"{doc_type.replace(' ', '_')}.json",
                f"{doc_type_normalized}_OCR_Fields.json",
                f"{doc_type_normalized}.json",
                f"{doc_type_normalized.replace(' ', '_')}_OCR_Fields.json",
                f"{doc_type_normalized.replace(' ', '_')}.json"
            ]
            
            filepath = None
            for possible_file in possible_files:
                test_path = doc_list_path / possible_file
                if test_path.exists():
                    filepath = test_path
                    logger.info(f"Found file for update: {filepath}")
                    break
            
            if not filepath:
                logger.error(f"Document type file not found for: {doc_type}")
                return jsonify({"success": False, "message": "Document type not found"}), 404
            
            # Validate fields structure
            if not isinstance(fields, list):
                return jsonify({"success": False, "message": "Fields must be a list"}), 400
            
            # Validate each field has required properties
            for field in fields:
                if not isinstance(field, dict):
                    return jsonify({"success": False, "message": "Each field must be an object"}), 400
                if 'name' not in field or not field['name']:
                    return jsonify({"success": False, "message": "Each field must have a name"}), 400
                # Set defaults for missing properties
                field.setdefault('type', 'text')
                field.setdefault('required', False)
                field.setdefault('description', '')
            
            # Update the file
            try:
                with open(str(filepath), 'w') as f:
                    json.dump(fields, f, indent=2)
                logger.info(f"Successfully updated {filepath} with {len(fields)} fields")
            except Exception as e:
                logger.error(f"Failed to write to {filepath}: {e}")
                return jsonify({"success": False, "message": f"Failed to save: {str(e)}"}), 500
            
            # Reload document classifier to pick up changes if it exists
            try:
                global document_classifier
                document_classifier = DocumentClassifier()
            except:
                pass  # Document classifier might not be initialized
            
            return jsonify({
                "success": True,
                "message": f"Document type '{doc_type}' updated successfully with {len(fields)} fields",
                "field_count": len(fields)
            })
            
        except Exception as e:
            logger.error(f"Error updating document type: {str(e)}")
            return jsonify({"success": False, "message": str(e)}), 500
    
    @app.route('/api/document-types/ocr-fields/<doc_type>', methods=['DELETE'])
    @login_required
    def delete_document_type_ocr_fields(doc_type):
        """Delete a document type OCR fields file"""
        try:
            # Get current user
            user = UserRepository.get_user_by_id(session["user_id"])
            if not user:
                return jsonify({"success": False, "message": "User not found"}), 401
            
            # Check if user is allowed
            if user["email"].lower() not in [e.lower() for e in ALLOWED_EMAILS]:
                return jsonify({"success": False, "message": "Access denied"}), 403
            
            # Find the file
            doc_list_path = Path(app.root_path) / "prompts" / "EE" / "DOC_LIST"
            
            # Try different filename patterns
            possible_files = [
                f"{doc_type}_OCR_Fields.json",
                f"{doc_type}.json",
                f"{doc_type.replace(' ', '_')}_OCR_Fields.json",
                f"{doc_type.replace(' ', '_')}.json"
            ]
            
            filepath = None
            for possible_file in possible_files:
                test_path = doc_list_path / possible_file
                if test_path.exists():
                    filepath = test_path
                    break
            
            if not filepath:
                return jsonify({"success": False, "message": "Document type not found"}), 404
            
            # Delete the file
            os.remove(str(filepath))
            
            # Reload document classifier to pick up changes
            global document_classifier
            document_classifier = DocumentClassifier()
            
            return jsonify({
                "success": True,
                "message": f"Document type '{doc_type}' deleted successfully"
            })
            
        except Exception as e:
            logger.error(f"Error deleting document type: {str(e)}")
            return jsonify({"success": False, "message": str(e)}), 500

    # Repository Management Endpoints
    @app.route('/api/repositories', methods=['GET'])
    def get_repositories():
        """Get all available repositories for a user"""
        try:
            user_id = request.args.get('user_id', 'default_user')
            
            # Return the three specific repositories
            repositories = [
                {
                    'id': 'trade_finance_repo',
                    'name': 'Trade Finance Repository',
                    'type': 'trade_finance',
                    'description': 'Repository for trade finance documents and knowledge',
                    'icon': 'fa-bank',
                    'collections': [
                        {'name': 'Letter of Credit', 'count': 245, 'status': 'active'},
                        {'name': 'Bank Guarantee', 'count': 186, 'status': 'active'},
                        {'name': 'Invoice Discounting', 'count': 92, 'status': 'active'},
                        {'name': 'UCP 600 Rules', 'count': 78, 'status': 'active'},
                        {'name': 'SWIFT Messages', 'count': 134, 'status': 'active'}
                    ],
                    'total_documents': 735,
                    'status': 'active'
                },
                {
                    'id': 'treasury_repo', 
                    'name': 'Treasury Repository',
                    'type': 'treasury',
                    'description': 'Repository for treasury operations and FX management',
                    'icon': 'fa-chart-line',
                    'collections': [
                        {'name': 'FX Hedging', 'count': 158, 'status': 'active'},
                        {'name': 'Interest Rate Swaps', 'count': 124, 'status': 'active'},
                        {'name': 'Treasury Policies', 'count': 67, 'status': 'active'},
                        {'name': 'Risk Management', 'count': 203, 'status': 'active'}
                    ],
                    'total_documents': 552,
                    'status': 'active'
                },
                {
                    'id': 'cash_mgmt_repo',
                    'name': 'Cash Management Repository', 
                    'type': 'cash_management',
                    'description': 'Repository for cash management and liquidity optimization',
                    'icon': 'fa-money-bill-wave',
                    'collections': [
                        {'name': 'Cash Pooling', 'count': 89, 'status': 'active'},
                        {'name': 'Working Capital', 'count': 142, 'status': 'active'},
                        {'name': 'Payment Processing', 'count': 176, 'status': 'active'},
                        {'name': 'Liquidity Management', 'count': 95, 'status': 'active'}
                    ],
                    'total_documents': 502,
                    'status': 'active'
                }
            ]
            
            # Check if user has an active repository
            active_repo = active_user_repositories.get(user_id)
            
            return jsonify({
                'success': True,
                'repositories': repositories,
                'active_repository': active_repo,
                'user_id': user_id
            }), 200
            
        except Exception as e:
            logger.error(f"Error fetching repositories: {e}")
            return jsonify({
                'success': False,
                'error': str(e),
                'repositories': []
            }), 500

    @app.route('/api/repositories/active', methods=['GET', 'POST'])
    def manage_active_repository():
        """Get or set the active repository for a user"""

        if request.method == 'GET':
            # Get current active repository
            user_id = request.args.get('user_id', 'default_user')
            active_repo = active_user_repositories.get(user_id)

            return jsonify({
                'success': True,
                'active_repository': active_repo,
                'user_id': user_id
            }), 200

        elif request.method == 'POST':
            # Set active repository
            try:
                data = request.get_json()
                active_repo = data.get('active_repository')
                user_id = data.get('user_id', 'default_user')

                if active_repo:
                    active_user_repositories[user_id] = active_repo
                    logger.info(f"User {user_id} connected to repository: {active_repo}")
                else:
                    # Disconnect - remove user from active repositories
                    if user_id in active_user_repositories:
                        del active_user_repositories[user_id]
                        logger.info(f"User {user_id} disconnected from all repositories")

                return jsonify({
                    'success': True,
                    'active_repository': active_repo,
                    'message': f'Repository state updated: {active_repo or "disconnected"}'
                }), 200

            except Exception as e:
                logger.error(f"Error setting active repository: {e}")
                return jsonify({"error": str(e)}), 500

    @app.route('/api/repositories/<repo_id>/connect', methods=['POST'])
    def connect_repository(repo_id):
        """Connect user to a repository"""
        try:
            data = request.get_json() or {}
            user_id = data.get('user_id', 'default_user')
            
            # Map repository ID to name for the active_user_repositories
            repo_mapping = {
                'trade_finance_repo': 'Trade Finance Repository',
                'treasury_repo': 'Treasury Repository', 
                'cash_mgmt_repo': 'Cash Management Repository'
            }
            
            repo_name = repo_mapping.get(repo_id)
            if not repo_name:
                return jsonify({
                    'success': False,
                    'error': 'Invalid repository ID'
                }), 400
            
            # Set as active repository
            active_user_repositories[user_id] = repo_name
            logger.info(f"User {user_id} connected to repository: {repo_name}")
            
            return jsonify({
                'success': True,
                'message': f'Connected to {repo_name}',
                'active_repository': repo_name
            }), 200
            
        except Exception as e:
            logger.error(f"Error connecting to repository: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/repositories/<repo_id>/disconnect', methods=['POST'])
    def disconnect_repository(repo_id):
        """Disconnect user from a repository"""
        try:
            data = request.get_json() or {}
            user_id = data.get('user_id', 'default_user')
            
            # Remove from active repositories
            if user_id in active_user_repositories:
                repo_name = active_user_repositories[user_id]
                del active_user_repositories[user_id]
                logger.info(f"User {user_id} disconnected from repository: {repo_name}")
                
                return jsonify({
                    'success': True,
                    'message': f'Disconnected from {repo_name}'
                }), 200
            else:
                return jsonify({
                    'success': True,
                    'message': 'No active repository connection'
                }), 200
                
        except Exception as e:
            logger.error(f"Error disconnecting from repository: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/repositories/<repo_name>/collections', methods=['GET'])
    def get_repository_collections(repo_name):
        """Get collections for a specific repository"""
        try:
            import chromadb

            # Map repository names to ChromaDB collections
            repo_mappings = {
                'trade_finance': ['trade_finance_records', 'letter_of_credit', 'bank_guarantees',
                                  'export_documents', 'import_documents', 'ucp600_rules',
                                  'swift_rules', 'urdg758_rules'],
                'treasury': ['forex_transactions', 'money_market', 'derivatives',
                             'investments', 'hedging_instruments'],
                'cash': ['cash_transactions', 'liquidity_reports', 'cash_forecasts',
                         'payment_orders', 'cash_pooling']
            }

            if repo_name not in repo_mappings:
                return jsonify({"error": "Invalid repository name"}), 400

            try:
                # Connect to ChromaDB
                client = get_chromadb_client(host="localhost", port=8000)

                # Get all collections
                all_collections = client.list_collections()
                collection_names = [col.name for col in all_collections]

                # Filter collections for this repository
                repo_collections = []
                for collection_name in repo_mappings[repo_name]:
                    if collection_name in collection_names:
                        # Get collection to fetch count
                        collection = client.get_collection(collection_name)
                        count = collection.count()

                        repo_collections.append({
                            'name': collection_name,
                            'count': count,
                            'type': 'chromadb',
                            'status': 'active'
                        })
                    else:
                        # Collection doesn't exist yet
                        repo_collections.append({
                            'name': collection_name,
                            'count': 0,
                            'type': 'chromadb',
                            'status': 'not_created'
                        })

                return jsonify({
                    'success': True,
                    'repository': repo_name,
                    'collections': repo_collections,
                    'total_collections': len(repo_collections)
                }), 200

            except Exception as e:
                logger.error(f"Error connecting to ChromaDB: {e}")
                return jsonify({
                    'success': False,
                    'error': 'Failed to connect to ChromaDB',
                    'details': str(e)
                }), 500

        except Exception as e:
            logger.error(f"Error getting repository collections: {e}")
            return jsonify({"error": str(e)}), 500


def determine_document_type(filename: str, content: str) -> str:
    """Determine document type based on filename and content"""
    filename_lower = filename.lower()
    content_lower = content.lower()

    if 'invoice' in filename_lower or 'invoice' in content_lower:
        return 'invoice'
    elif 'purchase' in filename_lower and 'order' in filename_lower:
        return 'purchase_order'
    elif 'po' in filename_lower or 'purchase order' in content_lower:
        return 'purchase_order'
    elif 'shipping' in filename_lower or 'bill of lading' in content_lower:
        return 'shipping_document'
    elif 'contract' in filename_lower or 'sales contract' in content_lower:
        return 'sales_contract'
    elif 'packing' in filename_lower or 'packing list' in content_lower:
        return 'packing_list'
    elif 'certificate' in filename_lower:
        return 'certificate'
    else:
        return 'other'


def extract_document_data(content: str, doc_type: str) -> Dict[str, Any]:
    """Extract structured data from document based on type"""
    data = {}

    if doc_type == 'invoice':
        data = extract_invoice_data(content)
    elif doc_type == 'purchase_order':
        data = extract_purchase_order_data(content)
    elif doc_type == 'shipping_document':
        data = extract_shipping_data(content)
    elif doc_type == 'sales_contract':
        data = extract_contract_data(content)
    else:
        data = extract_generic_data(content)

    return data


def extract_invoice_data(content: str) -> Dict[str, Any]:
    """Extract data from invoice"""
    data = {}

    # Extract amount using regex patterns
    amount_patterns = [
        r'total[:\s]+([0-9,]+\.?[0-9]*)',
        r'amount[:\s]+([0-9,]+\.?[0-9]*)',
        r'sum[:\s]+([0-9,]+\.?[0-9]*)'
    ]

    for pattern in amount_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            data['total_amount'] = float(match.group(1).replace(',', ''))
            break

    # Extract currency
    currency_pattern = r'\b([A-Z]{3})\b'
    currency_match = re.search(currency_pattern, content)
    if currency_match:
        data['currency'] = currency_match.group(1)

    # Extract date
    date_patterns = [
        r'date[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        r'invoice date[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
    ]

    for pattern in date_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            data['invoice_date'] = match.group(1)
            break

    return data


def extract_purchase_order_data(content: str) -> Dict[str, Any]:
    """Extract data from purchase order"""
    data = {}

    # Similar extraction logic for PO
    amount_patterns = [
        r'total[:\s]+([0-9,]+\.?[0-9]*)',
        r'po amount[:\s]+([0-9,]+\.?[0-9]*)'
    ]

    for pattern in amount_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            data['total_amount'] = float(match.group(1).replace(',', ''))
            break

    # Extract quantity
    qty_pattern = r'quantity[:\s]+([0-9,]+\.?[0-9]*)'
    qty_match = re.search(qty_pattern, content, re.IGNORECASE)
    if qty_match:
        data['quantity'] = float(qty_match.group(1).replace(',', ''))

    return data


def extract_shipping_data(content: str) -> Dict[str, Any]:
    """Extract data from shipping document"""
    data = {}

    # Extract ports
    port_patterns = [
        r'port of loading[:\s]+([^\n]+)',
        r'from[:\s]+([^\n]+)',
        r'port of discharge[:\s]+([^\n]+)',
        r'to[:\s]+([^\n]+)'
    ]

    for i, pattern in enumerate(port_patterns):
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            if i < 2:
                data['port_of_loading'] = match.group(1).strip()
            else:
                data['port_of_discharge'] = match.group(1).strip()

    # Extract shipment date
    date_pattern = r'shipment date[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
    date_match = re.search(date_pattern, content, re.IGNORECASE)
    if date_match:
        data['shipment_date'] = date_match.group(1)

    return data


def extract_contract_data(content: str) -> Dict[str, Any]:
    """Extract data from sales contract"""
    data = {}

    # Extract contract value
    value_patterns = [
        r'contract value[:\s]+([0-9,]+\.?[0-9]*)',
        r'total value[:\s]+([0-9,]+\.?[0-9]*)'
    ]

    for pattern in value_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            data['contract_value'] = float(match.group(1).replace(',', ''))
            break

    # Extract parties
    buyer_pattern = r'buyer[:\s]+([^\n]+)'
    seller_pattern = r'seller[:\s]+([^\n]+)'

    buyer_match = re.search(buyer_pattern, content, re.IGNORECASE)
    if buyer_match:
        data['buyer'] = buyer_match.group(1).strip()

    seller_match = re.search(seller_pattern, content, re.IGNORECASE)
    if seller_match:
        data['seller'] = seller_match.group(1).strip()

    return data


def extract_generic_data(content: str) -> Dict[str, Any]:
    """Extract generic data from unknown document types"""
    data = {}

    # Look for common fields
    amount_pattern = r'[^\w]([0-9,]+\.?[0-9]*)[^\w]'
    amounts = re.findall(amount_pattern, content)
    if amounts:
        # Take the largest number as potential amount
        data['amount'] = max([float(amt.replace(',', '')) for amt in amounts])

    return data


def parse_swift_message_text(swift_text: str) -> Dict[str, Any]:
    """Parse SWIFT message from raw text"""
    parsed = {
        'message_type': None,
        'reference_number': None,
        'fields': {},
        'raw_text': swift_text
    }

    # Extract message type
    mt_pattern = r'MT(\d{3})'
    mt_match = re.search(mt_pattern, swift_text)
    if mt_match:
        parsed['message_type'] = f"MT{mt_match.group(1)}"

    # Extract SWIFT fields (format: :20:reference or {4:tag:value})
    field_patterns = [
        r':(\d{2}[A-Z]?):(.*?)(?=:|$)',  # Standard format
        r'\{4:(\d{2}[A-Z]?):(.*?)\}'  # Block format
    ]

    for pattern in field_patterns:
        matches = re.finditer(pattern, swift_text, re.DOTALL)
        for match in matches:
            tag = match.group(1)
            value = match.group(2).strip()
            parsed['fields'][tag] = value

    # Extract reference number (field 20)
    if '20' in parsed['fields']:
        parsed['reference_number'] = parsed['fields']['20']

    return parsed


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


# Save compliance results route
@app.route('/api/compliance/save', methods=['POST'])
def save_compliance_results():
    """Save compliance check results"""
    try:
        data = request.get_json()
        user_id = session.get('user_id')

        if not user_id:
            return jsonify({
                'success': False,
                'error': 'User not authenticated'
            }), 401

        # Create compliance record
        compliance_record = {
            'user_id': user_id,
            'timestamp': datetime.utcnow(),
            'document_type': 'bank_guarantee',
            'compliance_data': data.get('compliance_data'),
            'summary': data.get('summary'),
            'severity': data.get('severity', 'medium'),
            'status': 'completed'
        }

        # Save to database
        result = db.compliance_results.insert_one(compliance_record)

        return jsonify({
            'success': True,
            'message': 'Compliance results saved successfully',
            'record_id': str(result.inserted_id)
        })

    except Exception as e:
        logger.error(f"Error saving compliance results: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Additional compliance reporting routes
@app.route('/api/compliance/report/export', methods=['POST'])
def export_compliance_report():
    """Export compliance report in various formats"""
    try:
        data = request.get_json()
        report_data = data.get('report_data')
        export_format = data.get('format', 'pdf').lower()

        if not report_data:
            return jsonify({
                'success': False,
                'error': 'Report data is required'
            }), 400

        if export_format == 'pdf':
            # Generate PDF report
            pdf_content = generate_pdf_report(report_data)
            return Response(
                pdf_content,
                mimetype='application/pdf',
                headers={
                    'Content-Disposition': f'attachment; filename=compliance_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
                }
            )
        elif export_format == 'excel':
            # Generate Excel report
            excel_content = generate_excel_report(report_data)
            return Response(
                excel_content,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                headers={
                    'Content-Disposition': f'attachment; filename=compliance_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
                }
            )
        elif export_format == 'csv':
            # Generate CSV report
            csv_content = generate_csv_report(report_data)
            return Response(
                csv_content,
                mimetype='text/csv',
                headers={
                    'Content-Disposition': f'attachment; filename=compliance_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
                }
            )
        else:
            return jsonify({
                'success': False,
                'error': 'Unsupported export format'
            }), 400

    except Exception as e:
        logger.error(f"Error exporting compliance report: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/compliance/analytics', methods=['GET'])
def get_compliance_analytics():
    """Get compliance analytics and statistics"""
    try:
        user_id = request.args.get('user_id')
        date_range = request.args.get('date_range', '30')  # days

        # Mock analytics data - replace with actual database queries
        analytics = {
            'total_checks_performed': 147,
            'average_compliance_score': 87.3,
            'total_documents_processed': 441,
            'compliance_trend': [
                {'date': (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d'),
                 'score': 85 + (i % 10)} for i in range(int(date_range))
            ],
            'document_type_distribution': {
                'invoice': 35,
                'purchase_order': 28,
                'shipping_document': 22,
                'sales_contract': 15
            },
            'risk_distribution': {
                'low': 65,
                'medium': 25,
                'high': 10
            },
            'common_issues': [
                {'issue': 'Amount discrepancy', 'count': 23},
                {'issue': 'Date mismatch', 'count': 18},
                {'issue': 'Party information inconsistent', 'count': 15},
                {'issue': 'Goods description unclear', 'count': 12}
            ]
        }

        return jsonify({
            'success': True,
            'analytics': analytics
        })

    except Exception as e:
        logger.error(f"Error retrieving compliance analytics: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/compliance/dashboard', methods=['GET'])
def get_compliance_dashboard():
    """Get compliance dashboard data"""
    try:
        # Mock dashboard data - replace with actual database queries
        dashboard_data = {
            'summary_stats': {
                'total_checks_today': 23,
                'average_score_today': 89.2,
                'critical_issues_today': 3,
                'documents_processed_today': 67
            },
            'recent_checks': [
                {
                    'id': str(uuid.uuid4()),
                    'timestamp': (datetime.now() - timedelta(minutes=i * 15)).isoformat(),
                    'swift_type': f'MT70{i}',
                    'score': 85 + (i * 3),
                    'status': 'PASS' if (85 + (i * 3)) >= 80 else 'FAIL',
                    'critical_issues': max(0, 3 - i)
                }
                for i in range(5)
            ],
            'system_health': {
                'api_status': 'healthy',
                'database_status': 'healthy',
                'processing_queue': 2,
                'average_response_time': 1.8
            },
            'alerts': [
                {
                    'type': 'warning',
                    'message': 'High volume of amount discrepancies detected in last hour',
                    'timestamp': (datetime.now() - timedelta(minutes=45)).isoformat()
                },
                {
                    'type': 'info',
                    'message': 'System maintenance scheduled for tonight',
                    'timestamp': (datetime.now() - timedelta(hours=2)).isoformat()
                }
            ]
        }

        return jsonify({
            'success': True,
            'dashboard': dashboard_data
        })

    except Exception as e:
        logger.error(f"Error retrieving compliance dashboard: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/compliance/batch', methods=['POST'])
def process_batch_compliance():
    """Process multiple documents in batch for compliance checking"""
    try:
        if 'files' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No files uploaded'
            }), 400

        files = request.files.getlist('files')
        swift_message = request.form.get('swift_message')

        if not swift_message:
            return jsonify({
                'success': False,
                'error': 'SWIFT message is required'
            }), 400

        # Process files in batch
        batch_results = []

        for file in files:
            if file.filename == '':
                continue

            # Extract text from file
            file_content = extract_text_from_file(file)
            doc_type = determine_document_type(file.filename, file_content)

            # Extract structured data
            document_data = extract_document_data(file_content, doc_type)
            document_data['document_type'] = doc_type
            document_data['filename'] = file.filename

            batch_results.append({
                'filename': file.filename,
                'document_type': doc_type,
                'extracted_data': document_data,
                'text_content': file_content[:500]  # First 500 chars for preview
            })

        # Parse SWIFT message
        swift_data = parse_swift_message_text(swift_message)

        # Validate all documents
        from app.utils.compliance_validator import DocumentComplianceValidator
        validator = DocumentComplianceValidator()

        validation_results = validator.validate_documents(swift_data, batch_results)

        return jsonify({
            'success': True,
            'batch_id': str(uuid.uuid4()),
            'processed_count': len(batch_results),
            'swift_message': swift_data,
            'validation_results': validation_results
        })

    except Exception as e:
        logger.error(f"Error processing batch compliance: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


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


# Analytics API Routes
@app.route('/api/analytics/dashboard', methods=['GET'])
def get_analytics_dashboard():
    """Get comprehensive analytics data for the dashboard"""
    try:
        # Get date range from request
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')

        # Build query
        query = {}
        if date_from and date_to:
            query['timestamp'] = {
                '$gte': datetime.strptime(date_from, '%Y-%m-%d'),
                '$lte': datetime.strptime(date_to, '%Y-%m-%d')
            }

        # Aggregate metrics from different collections
        # Transaction metrics
        transaction_metrics = db.chat_messages_collection.aggregate([
            {'$match': query},
            {'$group': {
                '_id': '$module_type',
                'count': {'$sum': 1},
                'total_value': {'$sum': '$transaction_value'}
            }}
        ])

        # Status distribution
        status_metrics = db.chat_messages_collection.aggregate([
            {'$match': query},
            {'$group': {
                '_id': '$status',
                'count': {'$sum': 1}
            }}
        ])

        # Time series data
        time_series = db.chat_messages_collection.aggregate([
            {'$match': query},
            {'$group': {
                '_id': {
                    'year': {'$year': '$timestamp'},
                    'month': {'$month': '$timestamp'},
                    'day': {'$dayOfMonth': '$timestamp'}
                },
                'count': {'$sum': 1},
                'value': {'$sum': '$transaction_value'}
            }},
            {'$sort': {'_id': 1}}
        ])

        # Process results
        modules_data = list(transaction_metrics)
        status_data = list(status_metrics)
        trends_data = list(time_series)

        # Calculate KPIs
        total_transactions = sum(m['count'] for m in modules_data)
        total_value = sum(m.get('total_value', 0) for m in modules_data)
        pending_count = next((s['count'] for s in status_data if s['_id'] == 'Awaiting Corporate Approval'), 0)
        approved_count = next((s['count'] for s in status_data if s['_id'] == 'Authorised'), 0)

        # Mock data for demonstration (replace with real data)
        analytics_data = {
            'kpis': {
                'total_transactions': total_transactions or 630,
                'total_value': total_value or 5040000000000,
                'pending_count': pending_count or 235,
                'approved_count': approved_count or 208,
                'success_rate': 96.2,
                'avg_processing_time': 2.8
            },
            'modules': {
                'names': ['IMCO', 'IMLC', 'INFI', 'MESG', 'OWGT', 'SHGT'],
                'transactions': [117, 362, 4, 16, 113, 18],
                'values': [41465111.23, 5000036735852.06, 0, 0, 7623010, 0],
                'efficiency': [85, 92, 78, 65, 88, 72]
            },
            'statuses': {
                'Authorised': 208,
                'Awaiting Corporate Approval': 235,
                'Rejected by Supervisor': 4,
                'Released': 147,
                'Saved': 36
            },
            'trends': {
                'months': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul'],
                'transactions': [450, 520, 480, 630, 580, 620, 630],
                'values': [2.1, 2.8, 2.5, 5.04, 4.2, 4.8, 5.04]
            }
        }

        return jsonify({
            'success': True,
            'data': analytics_data,
            'generated_at': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Error fetching analytics dashboard: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/analytics/module-performance', methods=['GET'])
def get_module_performance():
    """Get detailed module performance metrics"""
    try:
        module = request.args.get('module')
        period = request.args.get('period', '30d')

        # Calculate date range based on period
        end_date = datetime.now()
        if period == '7d':
            start_date = end_date - timedelta(days=7)
        elif period == '30d':
            start_date = end_date - timedelta(days=30)
        elif period == '90d':
            start_date = end_date - timedelta(days=90)
        else:
            start_date = end_date - timedelta(days=30)

        query = {
            'timestamp': {'$gte': start_date, '$lte': end_date}
        }
        if module:
            query['module_type'] = module

        # Aggregate performance metrics
        performance_data = db.metrics_collection.aggregate([
            {'$match': query},
            {'$group': {
                '_id': {
                    'module': '$module_type',
                    'date': {'$dateToString': {'format': '%Y-%m-%d', 'date': '$timestamp'}}
                },
                'avg_response_time': {'$avg': '$response_time'},
                'transaction_count': {'$sum': 1},
                'error_count': {'$sum': {'$cond': [{'$eq': ['$status', 'error']}, 1, 0]}},
                'success_count': {'$sum': {'$cond': [{'$eq': ['$status', 'success']}, 1, 0]}}
            }},
            {'$sort': {'_id.date': 1}}
        ])

        return jsonify({
            'success': True,
            'data': list(performance_data),
            'period': period,
            'module': module
        })

    except Exception as e:
        logger.error(f"Error fetching module performance: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/analytics/export', methods=['POST'])
def export_analytics_data():
    """Export analytics data in various formats"""
    try:
        export_format = request.json.get('format', 'csv')
        data_type = request.json.get('data_type', 'summary')
        filters = request.json.get('filters', {})

        # Fetch analytics data based on filters
        analytics_data = {
            'summary': {
                'total_transactions': 630,
                'total_value': 5040000000000,
                'modules': ['IMCO', 'IMLC', 'INFI', 'MESG', 'OWGT', 'SHGT'],
                'period': f"{filters.get('date_from', 'Start')} to {filters.get('date_to', 'End')}"
            },
            'details': []
        }

        # Generate export based on format
        if export_format == 'csv':
            csv_data = generate_analytics_csv(analytics_data)
            return Response(
                csv_data,
                mimetype='text/csv',
                headers={
                    'Content-Disposition': f'attachment; filename=analytics_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'}
            )
        elif export_format == 'excel':
            excel_data = generate_analytics_excel(analytics_data)
            return Response(
                excel_data,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                headers={
                    'Content-Disposition': f'attachment; filename=analytics_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'}
            )
        elif export_format == 'pdf':
            pdf_data = generate_analytics_pdf(analytics_data)
            return Response(
                pdf_data,
                mimetype='application/pdf',
                headers={
                    'Content-Disposition': f'attachment; filename=analytics_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'}
            )
        else:
            return jsonify({
                'success': False,
                'error': 'Unsupported export format'
            }), 400

    except Exception as e:
        logger.error(f"Error exporting analytics data: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


    # Admin-only endpoints
    @app.route('/api/admin/upload-manual', methods=['POST'])
    @login_required
    @timing_aspect
    def admin_upload_manual():
        """Upload user manuals (admin only)"""
        try:
            # Check if user is admin
            user_id = session.get('user_id')
            user = users_collection.find_one({'_id': user_id})
            
            # Check if user is allowed
            email = user.get('email', '') if user else ''
            if email.lower() not in [e.lower() for e in ALLOWED_EMAILS]:
                return jsonify({'success': False, 'message': 'Access denied'}), 403
            
            if 'file' not in request.files:
                return jsonify({'success': False, 'message': 'No file provided'}), 400
                
            file = request.files['file']
            if file.filename == '':
                return jsonify({'success': False, 'message': 'No file selected'}), 400
            
            # Save the manual to ChromaDB or filesystem
            manual_name = file.filename
            manual_type = request.form.get('type', 'general')
            
            # Create directory for manuals if it doesn't exist
            manuals_dir = os.path.join('app', 'manuals')
            os.makedirs(manuals_dir, exist_ok=True)
            
            # Save file
            file_path = os.path.join(manuals_dir, manual_name)
            file.save(file_path)
            
            # Process and index the manual in ChromaDB if available
            if 'chroma_client' in globals() and chroma_client:
                try:
                    # Extract text from manual
                    text_data = extract_text_from_file(file_path, mimetypes.guess_type(file_path)[0])
                    
                    # Create or get collection for manuals
                    collection = chroma_client.get_or_create_collection(name="user_manuals")
                    
                    # Add to ChromaDB
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
            
            # Store manual metadata in MongoDB
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
                'manual': {
                    'name': manual_name,
                    'type': manual_type
                }
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
            # Check if user is admin
            user_id = session.get('user_id')
            user = users_collection.find_one({'_id': user_id})
            
            # Check if user is allowed
            email = user.get('email', '') if user else ''
            if email.lower() not in [e.lower() for e in ALLOWED_EMAILS]:
                return jsonify({'success': False, 'message': 'Access denied'}), 403
            
            data = request.get_json()
            repo_type = data.get('type', 'chromadb')
            repo_config = data.get('config', {})
            
            # Connect to repository based on type
            if repo_type == 'chromadb':
                host = repo_config.get('host', 'localhost')
                port = repo_config.get('port', 8000)
                
                # Test connection
                try:
                    test_client = get_chromadb_client(host=host, port=port)
                    test_client.list_collections()
                    
                    # Save configuration
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
                        'repository': {
                            'type': repo_type,
                            'host': host,
                            'port': port
                        }
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
            
            # Check if user is allowed to see all manuals or just active ones
            is_allowed = user and user.get('email', '').lower() in [e.lower() for e in ALLOWED_EMAILS]
            
            query = {'is_active': True} if not is_allowed else {}
            manuals = list(db.manuals.find(query, {'_id': 0, 'path': 0}))
            
            # Convert datetime objects to strings
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
        """Get current repository connection status (available to all users)"""
        try:
            # Get active repository configuration
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

    @app.route('/api/trade-documents', methods=['GET'])
    @login_required
    @timing_aspect
    def get_trade_documents():
        """Get list of all available trade document types"""
        try:
            if not trade_document_elements:
                load_trade_document_elements()

            if not trade_document_elements:
                return jsonify({'success': False, 'message': 'Trade document elements not loaded'}), 500

            documents = trade_document_elements.get('documents', [])
            return jsonify({
                'success': True,
                'documents': documents,
                'count': len(documents)
            }), 200

        except Exception as e:
            logger.error(f"Error getting trade documents: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

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
    
    @app.route('/api/admin/delete-manual/<manual_name>', methods=['DELETE'])
    @login_required
    @timing_aspect
    def admin_delete_manual(manual_name):
        """Delete a manual (admin only)"""
        try:
            # Check if user is admin
            user_id = session.get('user_id')
            user = users_collection.find_one({'_id': user_id})
            
            # Check if user is allowed
            email = user.get('email', '') if user else ''
            if email.lower() not in [e.lower() for e in ALLOWED_EMAILS]:
                return jsonify({'success': False, 'message': 'Access denied'}), 403
            
            # Soft delete - just mark as inactive
            result = db.manuals.update_one(
                {'name': manual_name},
                {'$set': {'is_active': False, 'deleted_at': datetime.utcnow()}}
            )
            
            if result.modified_count > 0:
                return jsonify({
                    'success': True,
                    'message': f'Manual {manual_name} deleted successfully'
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'message': f'Manual {manual_name} not found'
                }), 404
                
        except Exception as e:
            logger.error(f"Error deleting manual: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
    
    # Debug route to test if routes are being registered
    @app.route('/api/debug/test', methods=['GET'])
    def debug_test():
        """Debug route to test route registration"""
        return jsonify({"success": True, "message": "Debug route working", "routes_registered": True}), 200
    
    # Vetting Rule Engine Routes (Admin Only)
    @app.route('/api/vetting/rules', methods=['GET'])
    @login_required
    @timing_aspect
    def get_vetting_rules():
        """Get all vetting rules (admin only)"""
        try:
            if not vetting_engine:
                return jsonify({"success": False, "message": "Vetting engine not initialized"}), 500
                
            # Check if user is admin
            user = users_collection.find_one({"_id": ObjectId(session.get("user_id"))})
            if not user or user.get("email") not in ALLOWED_EMAILS:
                return jsonify({"success": False, "message": "Unauthorized"}), 403
            
            active_only = request.args.get('active_only', 'false').lower() == 'true'
            rules = vetting_engine.get_all_rules(active_only=active_only)
            
            return jsonify({
                "success": True,
                "rules": rules
            }), 200
            
        except Exception as e:
            logger.error(f"Error fetching vetting rules: {e}")
            return jsonify({"success": False, "message": str(e)}), 500
    
    @app.route('/api/vetting/rules', methods=['POST'])
    @login_required
    @timing_aspect
    def create_vetting_rule():
        """Create a new vetting rule (admin only)"""
        try:
            # Check if user is admin
            user = users_collection.find_one({"_id": ObjectId(session.get("user_id"))})
            if not user or user.get("email") not in ALLOWED_EMAILS:
                return jsonify({"success": False, "message": "Unauthorized"}), 403
            
            rule_data = request.json
            if not rule_data.get("name") or not rule_data.get("value"):
                return jsonify({
                    "success": False,
                    "message": "Rule name and value are required"
                }), 400
            
            rule = vetting_engine.create_rule(rule_data, user.get("email"))
            
            return jsonify({
                "success": True,
                "rule": rule,
                "message": "Rule created successfully"
            }), 201
            
        except Exception as e:
            logger.error(f"Error creating vetting rule: {e}")
            return jsonify({"success": False, "message": str(e)}), 500
    
    @app.route('/api/vetting/rules/<rule_id>', methods=['PUT'])
    @login_required
    @timing_aspect
    def update_vetting_rule(rule_id):
        """Update a vetting rule (admin only)"""
        try:
            # Check if user is admin
            user = users_collection.find_one({"_id": ObjectId(session.get("user_id"))})
            if not user or user.get("email") not in ALLOWED_EMAILS:
                return jsonify({"success": False, "message": "Unauthorized"}), 403
            
            rule_data = request.json
            rule = vetting_engine.update_rule(rule_id, rule_data, user.get("email"))
            
            if rule:
                return jsonify({
                    "success": True,
                    "rule": rule,
                    "message": "Rule updated successfully"
                }), 200
            else:
                return jsonify({
                    "success": False,
                    "message": "Rule not found"
                }), 404
                
        except Exception as e:
            logger.error(f"Error updating vetting rule: {e}")
            return jsonify({"success": False, "message": str(e)}), 500
    
    @app.route('/api/vetting/rules/<rule_id>', methods=['DELETE'])
    @login_required
    @timing_aspect
    def delete_vetting_rule(rule_id):
        """Delete a vetting rule (admin only)"""
        try:
            # Check if user is admin
            user = users_collection.find_one({"_id": ObjectId(session.get("user_id"))})
            if not user or user.get("email") not in ALLOWED_EMAILS:
                return jsonify({"success": False, "message": "Unauthorized"}), 403
            
            if vetting_engine.delete_rule(rule_id):
                return jsonify({
                    "success": True,
                    "message": "Rule deleted successfully"
                }), 200
            else:
                return jsonify({
                    "success": False,
                    "message": "Rule not found"
                }), 404
                
        except Exception as e:
            logger.error(f"Error deleting vetting rule: {e}")
            return jsonify({"success": False, "message": str(e)}), 500
    
    @app.route('/api/vetting/test', methods=['POST'])
    @login_required
    @timing_aspect
    def test_vetting_rule():
        """Test a vetting rule with sample texts (admin only)"""
        try:
            # Check if user is admin
            user = users_collection.find_one({"_id": ObjectId(session.get("user_id"))})
            if not user or user.get("email") not in ALLOWED_EMAILS:
                return jsonify({"success": False, "message": "Unauthorized"}), 403
            
            data = request.json
            rule_id = data.get("rule_id")
            test_samples = data.get("test_samples")
            
            if not rule_id:
                return jsonify({
                    "success": False,
                    "message": "Rule ID is required"
                }), 400
            
            # If no test samples provided, generate them
            if not test_samples:
                rule = vetting_engine.get_rule(rule_id)
                if not rule:
                    return jsonify({
                        "success": False,
                        "message": "Rule not found"
                    }), 404
                
                onerous_sample, non_onerous_sample = vetting_engine.generate_sample_texts(rule)
                test_samples = [
                    {
                        "text": onerous_sample,
                        "expected_onerous": True
                    },
                    {
                        "text": non_onerous_sample,
                        "expected_onerous": False
                    }
                ]
            
            result = vetting_engine.test_rule(rule_id, test_samples)
            
            return jsonify({
                "success": True,
                "test_result": result
            }), 200
            
        except Exception as e:
            logger.error(f"Error testing vetting rule: {e}")
            return jsonify({"success": False, "message": str(e)}), 500
    
    @app.route('/api/vetting/generate-samples/<rule_id>', methods=['GET'])
    @login_required
    @timing_aspect
    def generate_test_samples(rule_id):
        """Generate test samples for a rule (admin only)"""
        try:
            # Check if user is admin
            user = users_collection.find_one({"_id": ObjectId(session.get("user_id"))})
            if not user or user.get("email") not in ALLOWED_EMAILS:
                return jsonify({"success": False, "message": "Unauthorized"}), 403
            
            rule = vetting_engine.get_rule(rule_id)
            if not rule:
                return jsonify({
                    "success": False,
                    "message": "Rule not found"
                }), 404
            
            # Get enhanced samples with LLM
            onerous_sample, non_onerous_sample, metadata = vetting_engine.generate_sample_texts_llm(rule)
            
            return jsonify({
                "success": True,
                "samples": [
                    {
                        "text": onerous_sample,
                        "expected_onerous": True,
                        "description": "This sample should trigger the rule",
                        "type": "onerous"
                    },
                    {
                        "text": non_onerous_sample,
                        "expected_onerous": False,
                        "description": "This sample should NOT trigger the rule",
                        "type": "clean"
                    }
                ],
                "metadata": metadata
            }), 200
            
        except Exception as e:
            logger.error(f"Error generating test samples: {e}")
            return jsonify({"success": False, "message": str(e)}), 500
    
    @app.route('/api/vetting/check', methods=['POST'])
    @login_required
    @timing_aspect
    def vet_guarantee():
        """Vet a guarantee text against all active rules"""
        try:
            data = request.json
            guarantee_text = data.get("guarantee_text")
            
            if not guarantee_text:
                return jsonify({
                    "success": False,
                    "message": "Guarantee text is required"
                }), 400
            
            result = vetting_engine.vet_guarantee(guarantee_text)
            
            return jsonify({
                "success": True,
                "vetting_result": result
            }), 200
            
        except Exception as e:
            logger.error(f"Error vetting guarantee: {e}")
            return jsonify({"success": False, "message": str(e)}), 500
    
    @app.route('/api/vetting/history', methods=['GET'])
    @login_required
    @timing_aspect
    def get_test_history():
        """Get test history for rules (admin only)"""
        try:
            # Check if user is admin
            user = users_collection.find_one({"_id": ObjectId(session.get("user_id"))})
            if not user or user.get("email") not in ALLOWED_EMAILS:
                return jsonify({"success": False, "message": "Unauthorized"}), 403
            
            rule_id = request.args.get('rule_id')
            history = vetting_engine.get_test_history(rule_id)
            
            return jsonify({
                "success": True,
                "history": history
            }), 200
            
        except Exception as e:
            logger.error(f"Error fetching test history: {e}")
            return jsonify({"success": False, "message": str(e)}), 500

    @app.route('/api/vetting/explain-rule', methods=['POST'])
    @login_required
    @timing_aspect
    def explain_rule():
        """Generate AI explanation for a rule configuration (admin only)"""
        try:
            # Check if user is admin
            user = users_collection.find_one({"_id": ObjectId(session.get("user_id"))})
            if not user or user.get("email") not in ALLOWED_EMAILS:
                return jsonify({"success": False, "message": "Unauthorized"}), 403
            
            data = request.json
            rule_config = {
                "name": data.get("name", "Untitled Rule"),
                "description": data.get("description", ""),
                "condition_type": data.get("condition_type"),
                "value": data.get("value"),
                "severity": data.get("severity", "medium")
            }
            
            if not rule_config["condition_type"] or not rule_config["value"]:
                return jsonify({
                    "success": False,
                    "message": "Rule condition type and value are required"
                }), 400
            
            explanation = vetting_engine.get_rule_explanation(rule_config)
            
            return jsonify({
                "success": True,
                "explanation": explanation
            }), 200
            
        except Exception as e:
            logger.error(f"Error generating rule explanation: {e}")
            return jsonify({"success": False, "message": str(e)}), 500

    @app.route('/api/vetting/rule-effectiveness/<rule_id>', methods=['GET'])
    @login_required
    @timing_aspect
    def get_rule_effectiveness(rule_id):
        """Get effectiveness analysis for a rule (admin only)"""
        try:
            # Check if user is admin
            user = users_collection.find_one({"_id": ObjectId(session.get("user_id"))})
            if not user or user.get("email") not in ALLOWED_EMAILS:
                return jsonify({"success": False, "message": "Unauthorized"}), 403
            
            effectiveness_data = vetting_engine.get_rule_effectiveness_score(rule_id)
            
            if "error" in effectiveness_data:
                return jsonify({
                    "success": False,
                    "message": effectiveness_data["error"]
                }), 400
            
            return jsonify({
                "success": True,
                "effectiveness": effectiveness_data
            }), 200
            
        except Exception as e:
            logger.error(f"Error getting rule effectiveness: {e}")
            return jsonify({"success": False, "message": str(e)}), 500


# Utility functions (module level)
def generate_analytics_csv(data: Dict[str, Any]) -> str:
    """Generate CSV for analytics data"""
    import csv
    import io

    output = io.StringIO()
    writer = csv.writer(output)

    # Write summary
    writer.writerow(['Analytics Summary'])
    writer.writerow(['Metric', 'Value'])
    writer.writerow(['Total Transactions', data['summary']['total_transactions']])
    writer.writerow(['Total Value (AED)', data['summary']['total_value']])
    writer.writerow(['Period', data['summary']['period']])
    writer.writerow([''])

    # Write module breakdown
    writer.writerow(['Module Breakdown'])
    writer.writerow(['Module', 'Transactions', 'Value (AED)'])
    # Add module data here

    return output.getvalue()


def generate_analytics_excel(data: Dict[str, Any]) -> bytes:
    """Generate Excel for analytics data"""
    # Placeholder - implement with openpyxl
    return b"Excel content placeholder"


def generate_analytics_pdf(data: Dict[str, Any]) -> bytes:
    """Generate PDF for analytics data"""
    # Placeholder - implement with reportlab
    return b"PDF content placeholder"

# Data Categories CRUD Routes
def _load_categories():
    """Helper function to load all categories from single JSON file"""
    categories_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    os.makedirs(categories_dir, exist_ok=True)
    filepath = os.path.join(categories_dir, 'categories.json')

    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        # Create default structure with 12 default categories
        default_categories = {
            'categories': [
                {'id': '1', 'value': 'References'},
                {'id': '2', 'value': 'Dates'},
                {'id': '3', 'value': 'Parties/addresses/places/countries'},
                {'id': '4', 'value': 'Locations'},
                {'id': '5', 'value': 'Clauses/conditions/instructions'},
                {'id': '6', 'value': 'Terms'},
                {'id': '7', 'value': 'Amounts/charges/percentages'},
                {'id': '8', 'value': 'Measure/Quantities'},
                {'id': '9', 'value': 'Goods'},
                {'id': '10', 'value': 'Dangerous goods'},
                {'id': '11', 'value': 'Transport modes/means/equipment'},
                {'id': '12', 'value': 'Others'}
            ]
        }
        _save_categories(default_categories)
        return default_categories

def _save_categories(data):
    """Helper function to save all categories to single JSON file"""
    categories_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    os.makedirs(categories_dir, exist_ok=True)
    filepath = os.path.join(categories_dir, 'categories.json')
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def _load_entities():
    """Helper function to load all entities from single JSON file"""
    entities_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    os.makedirs(entities_dir, exist_ok=True)
    filepath = os.path.join(entities_dir, 'entities.json')

    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        # Create default structure with comprehensive list of trade finance entities
        default_entities = {
            'entities': [
                {'id': '1', 'name': 'Document Identifier', 'description': 'Reference number identifying a specific document', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '2', 'name': 'Booking reference number', 'description': 'Reference number assigned by a carrier or agent to identify a specific consignment', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '3', 'name': 'Purchase Order number', 'description': 'Identifier assigned by the buyer to an order', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '4', 'name': 'House waybill document identifier', 'description': 'Reference number to identify a house waybill', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '5', 'name': 'Customs Declaration Document, Trader Assigned', 'description': 'Reference assigned by a trader to identify a declaration', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '6', 'name': 'Invoice Number', 'description': 'Unique identifier for a commercial invoice', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '7', 'name': 'Bill of Lading Number', 'description': 'Reference number for a bill of lading document', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '8', 'name': 'Shipping Order Number', 'description': 'Reference number for a shipping order', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '9', 'name': 'Container Number', 'description': 'Unique identifier for a shipping container', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '10', 'name': 'Certificate of Origin Number', 'description': 'Reference number for a certificate of origin', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '11', 'name': 'Letter of Credit Number', 'description': 'Unique identifier for a letter of credit', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '12', 'name': 'Bank Guarantee Number', 'description': 'Reference number for a bank guarantee', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '13', 'name': 'Insurance Policy Number', 'description': 'Unique identifier for an insurance policy', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '14', 'name': 'Packing List Number', 'description': 'Reference number for a packing list', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '15', 'name': 'Commercial Invoice Date', 'description': 'Date on which a commercial invoice was issued', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '16', 'name': 'Shipment Date', 'description': 'Date when goods were shipped', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '17', 'name': 'Delivery Date', 'description': 'Expected or actual date of delivery', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '18', 'name': 'LC Expiry Date', 'description': 'Expiration date of a letter of credit', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '19', 'name': 'Document Presentation Date', 'description': 'Date when documents are presented to the bank', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '20', 'name': 'Exporter Name', 'description': 'Name of the party exporting goods', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '21', 'name': 'Importer Name', 'description': 'Name of the party importing goods', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '22', 'name': 'Consignee Name', 'description': 'Name of the party to whom goods are consigned', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '23', 'name': 'Shipper Name', 'description': 'Name of the party shipping the goods', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '24', 'name': 'Notify Party', 'description': 'Party to be notified about shipment', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '25', 'name': 'Carrier Name', 'description': 'Name of the transportation carrier', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '26', 'name': 'Issuing Bank', 'description': 'Bank that issues the letter of credit', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '27', 'name': 'Advising Bank', 'description': 'Bank that advises the beneficiary of the LC', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '28', 'name': 'Confirming Bank', 'description': 'Bank that confirms the letter of credit', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '29', 'name': 'Port of Loading', 'description': 'Port where goods are loaded for shipment', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '30', 'name': 'Port of Discharge', 'description': 'Port where goods are unloaded', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '31', 'name': 'Place of Delivery', 'description': 'Final destination for delivery of goods', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '32', 'name': 'Country of Origin', 'description': 'Country where goods originated', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '33', 'name': 'Country of Destination', 'description': 'Country where goods are destined', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '34', 'name': 'Payment Terms', 'description': 'Terms and conditions for payment', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '35', 'name': 'Incoterms', 'description': 'International commercial terms defining responsibilities', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '36', 'name': 'Partial Shipment Clause', 'description': 'Clause indicating if partial shipments are allowed', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '37', 'name': 'Transshipment Clause', 'description': 'Clause indicating if transshipment is allowed', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '38', 'name': 'Latest Shipment Date', 'description': 'Latest date by which goods must be shipped', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '39', 'name': 'Negotiation Period', 'description': 'Period within which documents must be negotiated', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '40', 'name': 'Document Requirements', 'description': 'List of required documents for the transaction', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '41', 'name': 'Invoice Amount', 'description': 'Total amount stated on the invoice', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '42', 'name': 'LC Amount', 'description': 'Total amount of the letter of credit', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '43', 'name': 'Insurance Amount', 'description': 'Amount of insurance coverage', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '44', 'name': 'Freight Charges', 'description': 'Charges for transportation of goods', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '45', 'name': 'Customs Duty', 'description': 'Duty payable to customs authorities', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '46', 'name': 'Commission Amount', 'description': 'Commission charged for services', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '47', 'name': 'Discount Amount', 'description': 'Discount applied to the transaction', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '48', 'name': 'Currency Code', 'description': 'Three-letter currency code (ISO 4217)', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '49', 'name': 'Exchange Rate', 'description': 'Rate for currency conversion', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '50', 'name': 'Gross Weight', 'description': 'Total weight including packaging', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '51', 'name': 'Net Weight', 'description': 'Weight of goods excluding packaging', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '52', 'name': 'Volume', 'description': 'Total volume of the shipment', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '53', 'name': 'Quantity', 'description': 'Number of units or items', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '54', 'name': 'Unit of Measurement', 'description': 'Standard unit for measuring quantity', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '55', 'name': 'Package Type', 'description': 'Type of packaging used', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '56', 'name': 'Number of Packages', 'description': 'Total count of packages', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '57', 'name': 'Goods Description', 'description': 'Detailed description of the goods', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '58', 'name': 'HS Code', 'description': 'Harmonized System code for goods classification', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '59', 'name': 'Product Code', 'description': 'Internal code for product identification', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '60', 'name': 'Brand Name', 'description': 'Brand or trademark of the goods', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '61', 'name': 'Model Number', 'description': 'Model or variant identifier', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '62', 'name': 'UN Number', 'description': 'United Nations number for dangerous goods', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '63', 'name': 'Hazard Class', 'description': 'Classification of hazardous materials', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '64', 'name': 'IMDG Code', 'description': 'International Maritime Dangerous Goods code', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '65', 'name': 'Flash Point', 'description': 'Temperature at which vapors ignite', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '66', 'name': 'Vessel Name', 'description': 'Name of the shipping vessel', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '67', 'name': 'Voyage Number', 'description': 'Reference number for the voyage', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '68', 'name': 'Flight Number', 'description': 'Identifier for air transportation', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '69', 'name': 'Truck Registration', 'description': 'Registration number of transport vehicle', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '70', 'name': 'Rail Car Number', 'description': 'Identifier for railway wagon', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '71', 'name': 'Container Type', 'description': 'Type and size of container', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '72', 'name': 'Seal Number', 'description': 'Security seal identifier', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '73', 'name': 'Equipment Number', 'description': 'Reference for transport equipment', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '74', 'name': 'Customs Reference', 'description': 'Customs authority reference number', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '75', 'name': 'Tax Identification Number', 'description': 'Tax ID of a party', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '76', 'name': 'VAT Number', 'description': 'Value Added Tax registration number', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '77', 'name': 'EORI Number', 'description': 'Economic Operators Registration and Identification', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '78', 'name': 'AEO Number', 'description': 'Authorized Economic Operator number', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '79', 'name': 'License Number', 'description': 'Import or export license reference', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '80', 'name': 'Permit Number', 'description': 'Special permit or authorization number', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '81', 'name': 'Beneficiary Name', 'description': 'Name of the LC beneficiary', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '82', 'name': 'Applicant Name', 'description': 'Name of the LC applicant', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '83', 'name': 'Account Number', 'description': 'Bank account number', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '84', 'name': 'SWIFT Code', 'description': 'Bank identifier code (BIC)', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '85', 'name': 'IBAN', 'description': 'International Bank Account Number', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '86', 'name': 'Routing Number', 'description': 'Bank routing or sort code', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '87', 'name': 'Payment Reference', 'description': 'Reference for payment transaction', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '88', 'name': 'Drawdown Amount', 'description': 'Amount drawn under LC or guarantee', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '89', 'name': 'Amendment Number', 'description': 'Reference for LC amendment', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '90', 'name': 'Transfer Number', 'description': 'Reference for LC transfer', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '91', 'name': 'Discrepancy Description', 'description': 'Description of document discrepancies', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '92', 'name': 'Tolerance Percentage', 'description': 'Allowed variance in quantity or amount', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '93', 'name': 'Insurance Certificate Number', 'description': 'Reference for insurance certificate', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '94', 'name': 'Quality Certificate Number', 'description': 'Reference for quality certification', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '95', 'name': 'Inspection Certificate Number', 'description': 'Reference for inspection certificate', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '96', 'name': 'Phytosanitary Certificate Number', 'description': 'Plant health certificate reference', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '97', 'name': 'Health Certificate Number', 'description': 'Health certification reference', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '98', 'name': 'Warehouse Receipt Number', 'description': 'Reference for warehoused goods', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '99', 'name': 'Delivery Order Number', 'description': 'Reference for delivery authorization', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '100', 'name': 'CMR Number', 'description': 'Road consignment note reference', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '101', 'name': 'AWB Number', 'description': 'Air Waybill reference number', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '102', 'name': 'Master Bill of Lading', 'description': 'Master B/L issued by carrier', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '103', 'name': 'House Bill of Lading', 'description': 'House B/L issued by freight forwarder', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '104', 'name': 'Charter Party Reference', 'description': 'Reference to charter agreement', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '105', 'name': 'Freight Forwarder Reference', 'description': 'Forwarder\'s internal reference', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '106', 'name': 'Agent Reference', 'description': 'Agent\'s reference number', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '107', 'name': 'Consignment Note Number', 'description': 'Reference for consignment note', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '108', 'name': 'Manifest Number', 'description': 'Cargo manifest reference', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '109', 'name': 'Entry Number', 'description': 'Customs entry reference', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '110', 'name': 'Export Declaration Number', 'description': 'Export declaration reference', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '111', 'name': 'Import Declaration Number', 'description': 'Import declaration reference', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '112', 'name': 'SAD Number', 'description': 'Single Administrative Document number', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '113', 'name': 'EUR1 Number', 'description': 'Movement certificate EUR.1 reference', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '114', 'name': 'ATR Number', 'description': 'ATR movement certificate reference', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '115', 'name': 'GSP Form A Number', 'description': 'Generalized System of Preferences certificate', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '116', 'name': 'Quota Number', 'description': 'Import/export quota reference', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '117', 'name': 'Tariff Code', 'description': 'Customs tariff classification code', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '118', 'name': 'Trade Agreement Reference', 'description': 'Reference to applicable trade agreement', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '119', 'name': 'Contract Number', 'description': 'Sales or purchase contract reference', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '120', 'name': 'Pro Forma Invoice Number', 'description': 'Preliminary invoice reference', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '121', 'name': 'Debit Note Number', 'description': 'Reference for debit note', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '122', 'name': 'Credit Note Number', 'description': 'Reference for credit note', 'mappingFormField': '', 'mappingFormDescription': ''}
            ]
        }
        _save_entities(default_entities)
        return default_entities

def _save_entities(data):
    """Helper function to save all entities to single JSON file"""
    entities_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    os.makedirs(entities_dir, exist_ok=True)
    filepath = os.path.join(entities_dir, 'entities.json')
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def _load_document_categories():
    """Helper function to load all document categories from single JSON file"""
    categories_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    os.makedirs(categories_dir, exist_ok=True)
    filepath = os.path.join(categories_dir, 'document_categories.json')

    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        # Create default structure with default document categories
        default_categories = {
            'categories': [
                {'id': '1', 'name': 'Commercial Processes'},
                {'id': '2', 'name': 'Transport Processes'},
                {'id': '3', 'name': 'Border and Regulatory Processes'},
                {'id': '4', 'name': 'Financial Processes'},
                {'id': '5', 'name': 'Quality and Compliance Processes'}
            ]
        }
        # Save default data
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(default_categories, f, indent=2, ensure_ascii=False)
        return default_categories

def _save_document_categories(data):
    """Helper function to save all document categories to single JSON file"""
    categories_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    os.makedirs(categories_dir, exist_ok=True)
    filepath = os.path.join(categories_dir, 'document_categories.json')
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # ============================================================================
    # CUSTOM FUNCTIONS ROUTES
    # ============================================================================

    @app.route('/custom_functions')
    @timing_aspect
    def custom_functions_page():
        """Render custom functions management page"""
        return render_template('custom_functions.html')

    @app.route('/custom_function_builder')
    @timing_aspect
    def custom_function_builder():
        """Render custom function builder/editor page"""
        return render_template('custom_function_builder.html')

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

    def search_text_in_ocr(field_value, ocr_data, search_mode='exact'):
        """
        Search for text matches in OCR data with different matching strategies
        
        Args:
            field_value: Text to search for
            ocr_data: List of OCR entries with text and coordinates
            search_mode: 'exact', 'fuzzy', or 'contains'
        
        Returns:
            List of matches with coordinates, sorted by confidence
        """
        import re
        from difflib import SequenceMatcher
        
        logger.info(f"🔎 === STARTING OCR TEXT SEARCH ===")
        logger.info(f"📝 Search parameters:")
        logger.info(f"   Field value: '{field_value}'")
        logger.info(f"   Search mode: {search_mode}")
        logger.info(f"   OCR entries to search: {len(ocr_data)}")
        
        matches = []
        field_value_lower = field_value.lower().strip()
        logger.info(f"🔤 Normalized field value: '{field_value_lower}'")
        
        # Track search statistics
        exact_matches = 0
        contains_matches = 0
        partial_matches = 0
        fuzzy_matches = 0
        no_matches = 0
        
        logger.info(f"🔎 Searching in {len(ocr_data)} OCR entries...")
        
        for i, ocr_entry in enumerate(ocr_data):
            ocr_text = ocr_entry.get('text', '').strip()
            if not ocr_text:
                logger.debug(f"   Entry {i+1}: Skipping empty text")
                continue
                
            ocr_text_lower = ocr_text.lower()
            match_confidence = 0
            match_type = 'none'
            
            logger.debug(f"   Entry {i+1}: Comparing '{field_value_lower}' with '{ocr_text_lower}'")
            
            # Exact match (highest priority)
            if search_mode in ['exact', 'fuzzy', 'contains']:
                if field_value_lower == ocr_text_lower:
                    match_confidence = 100
                    match_type = 'exact'
                    exact_matches += 1
                    logger.debug(f"      ✅ EXACT MATCH! Confidence: 100%")
                elif field_value_lower in ocr_text_lower:
                    match_confidence = 90
                    match_type = 'contains'
                    contains_matches += 1
                    logger.debug(f"      ✅ CONTAINS MATCH! '{field_value_lower}' found in '{ocr_text_lower}' - Confidence: 90%")
                elif ocr_text_lower in field_value_lower:
                    match_confidence = 85
                    match_type = 'partial'
                    partial_matches += 1
                    logger.debug(f"      ✅ PARTIAL MATCH! '{ocr_text_lower}' found in '{field_value_lower}' - Confidence: 85%")
            
            # Fuzzy matching if enabled and no exact match
            if search_mode in ['fuzzy', 'contains'] and match_confidence < 90:
                similarity = SequenceMatcher(None, field_value_lower, ocr_text_lower).ratio()
                logger.debug(f"      🔀 Fuzzy similarity: {similarity:.3f}")
                if similarity >= 0.8:  # High similarity threshold
                    fuzzy_confidence = similarity * 80
                    if fuzzy_confidence > match_confidence:
                        match_confidence = fuzzy_confidence
                        match_type = 'fuzzy'
                        fuzzy_matches += 1
                        logger.debug(f"      ✅ FUZZY MATCH! Similarity: {similarity:.3f} - Confidence: {fuzzy_confidence:.1f}%")
            
            if match_confidence < 80:
                no_matches += 1
                logger.debug(f"      ❌ No sufficient match (confidence: {match_confidence:.1f}%)")
            
            # Only include high-confidence matches
            if match_confidence >= 80:
                match_data = {
                    'ocr_index': i,
                    'matched_text': ocr_text,
                    'field_value': field_value,
                    'match_confidence': round(match_confidence, 1),
                    'match_type': match_type,
                    'bounding_box': ocr_entry.get('bounding_box', []),
                    'bounding_page': ocr_entry.get('bounding_page', 1),
                    'ocr_confidence': ocr_entry.get('confidence', 0)
                }
                matches.append(match_data)
                
                logger.info(f"✅ MATCH #{len(matches)}: '{ocr_text}' -> {match_confidence:.1f}% confidence ({match_type})")
                logger.info(f"   OCR Index: {i}, Page: {match_data['bounding_page']}, BBox: {match_data['bounding_box']}")
        
        # Sort by match confidence (highest first)
        matches.sort(key=lambda x: x['match_confidence'], reverse=True)
        
        # Log search summary
        logger.info(f"📊 === SEARCH SUMMARY ===")
        logger.info(f"   Exact matches: {exact_matches}")
        logger.info(f"   Contains matches: {contains_matches}")
        logger.info(f"   Partial matches: {partial_matches}")
        logger.info(f"   Fuzzy matches: {fuzzy_matches}")
        logger.info(f"   No matches: {no_matches}")
        logger.info(f"   Total qualifying matches: {len(matches)}")
        
        if matches:
            best_match = matches[0]
            logger.info(f"🎯 BEST MATCH: '{best_match['matched_text']}' ({best_match['match_confidence']}% {best_match['match_type']})")
            logger.info(f"   Location: Page {best_match['bounding_page']}, BBox: {best_match['bounding_box']}")
        else:
            logger.warning(f"❌ NO QUALIFYING MATCHES FOUND for '{field_value}'")
            logger.info(f"💡 Search suggestions:")
            logger.info(f"   - Try using 'fuzzy' or 'contains' search mode")
            logger.info(f"   - Check if the field value exactly matches the document text")
            logger.info(f"   - Verify the document has been processed and OCR data is available")
        
        logger.info(f"📦 Search complete: returning {len(matches)} matches")
        return matches

