import json
import os
import logging
from typing import Dict, List, Optional, Tuple
import openai
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from app.utils.app_config import (
    deployment_name, 
    AZURE_OPENAI_API_VERSION, 
    AZURE_OPENAI_API_TYPE,
    OPENAI_TEMPERATURE_DEFAULT, 
    OPENAI_TEMPERATURE_CLASSIFICATION, 
    OPENAI_TEMPERATURE_EXTRACTION, 
    OPENAI_TEMPERATURE_COMPLIANCE,
    OPENAI_MAX_TOKENS_DEFAULT, 
    OPENAI_MAX_TOKENS_CLASSIFICATION, 
    OPENAI_MAX_TOKENS_EXTRACTION, 
    OPENAI_MAX_TOKENS_COMPLIANCE,
    OPENAI_TOP_P, 
    OPENAI_FREQUENCY_PENALTY, 
    OPENAI_PRESENCE_PENALTY, 
    OPENAI_SEED, 
    OPENAI_MAX_DELAY
)
import app.utils.app_config as app_config
from app.utils.openai_retry import retry_openai, create_websocket_retry


class DocumentClassifier:
    def __init__(self):
        logging.info("Initializing DocumentClassifier...")

        # Always load from environment variables to ensure we have the credentials
        openai.api_type = AZURE_OPENAI_API_TYPE
        openai.api_base = os.getenv("AZURE_OPENAI_API_BASE")
        openai.api_version = AZURE_OPENAI_API_VERSION
        openai.api_key = os.getenv("AZURE_OPENAI_API_KEY")

        logging.info(f"OpenAI API Type at init: {openai.api_type}")
        logging.info(f"OpenAI API Base at init: {openai.api_base}")
        logging.info(f"OpenAI API Key at init: {'Set' if openai.api_key else 'Not Set'}")
        logging.info(f"OpenAI API Key length at init: {len(openai.api_key) if openai.api_key else 0}")
        logging.info(f"Deployment Name at init: {deployment_name}")

        # Get the base directory of the current file and construct paths relative to it
        base_dir = Path(__file__).parent.parent
        project_root = base_dir.parent  # Go up one more level to project root
        self.doc_list_path = base_dir / "prompts" / "EE" / "DOC_LIST"
        self.function_fields_path = base_dir / "prompts" / "EE" / "function_fields.json"
        self.entity_maintenance_path = project_root / "data" / "document_entity_maintenance.json"
        self.entities_path = project_root / "data" / "entities.json"  # Add entities.json path

        self.document_fields_cache = {}
        self.function_fields = self._load_function_fields()
        self.entity_mappings = self._load_entity_mappings()  # Load entity maintenance data
        self.entity_descriptions = self._load_entity_descriptions()  # Load entity descriptions
        self.document_categories = self._load_document_categories()  # Load categories
        self._load_document_fields()
        logging.info("DocumentClassifier initialized successfully")
    
    def _load_function_fields(self) -> Dict:
        """Load function fields mapping from JSON file."""
        try:
            with open(str(self.function_fields_path), 'r') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Failed to load function fields: {e}")
            return {}

    def _load_entity_mappings(self) -> Dict:
        """Load document entity maintenance mappings from JSON file."""
        try:
            with open(str(self.entity_maintenance_path), 'r') as f:
                data = json.load(f)
                mappings = data.get('mappings', [])

                # Organize mappings by document type
                doc_mappings = {}
                for mapping in mappings:
                    doc_id = mapping.get('documentId')
                    if doc_id:
                        if doc_id not in doc_mappings:
                            doc_mappings[doc_id] = {
                                'documentName': mapping.get('documentName'),
                                'documentCategoryId': mapping.get('documentCategoryId'),
                                'documentCategoryName': mapping.get('documentCategoryName'),
                                'mandatory_fields': [],
                                'optional_fields': [],
                                'conditional_fields': []
                            }

                        # Add entity to appropriate field type list (avoid duplicates)
                        field_type = mapping.get('fieldType', 'optional')
                        entity_name = mapping.get('entityName')

                        entity_info = {
                            'entityId': mapping.get('entityId'),
                            'entityName': entity_name,
                            'dataCategoryId': mapping.get('dataCategoryId'),
                            'dataCategoryValue': mapping.get('dataCategoryValue')
                        }

                        # Check if entity already exists in any list to avoid duplicates
                        all_existing = (doc_mappings[doc_id]['mandatory_fields'] +
                                      doc_mappings[doc_id]['optional_fields'] +
                                      doc_mappings[doc_id]['conditional_fields'])

                        if not any(e['entityName'] == entity_name for e in all_existing):
                            if field_type == 'mandatory':
                                doc_mappings[doc_id]['mandatory_fields'].append(entity_info)
                            elif field_type == 'conditional':
                                doc_mappings[doc_id]['conditional_fields'].append(entity_info)
                            else:
                                doc_mappings[doc_id]['optional_fields'].append(entity_info)

                logging.info(f"Loaded entity mappings for {len(doc_mappings)} document types")
                return doc_mappings
        except Exception as e:
            logging.error(f"Failed to load entity mappings: {e}")
            return {}

    def _load_entity_descriptions(self) -> Dict:
        """Load entity descriptions from entities.json."""
        try:
            with open(str(self.entities_path), 'r', encoding='utf-8') as f:
                data = json.load(f)
                entities = data.get('entities', [])
                
                # Create mapping from entity name to description
                entity_desc_map = {}
                for entity in entities:
                    entity_name = entity.get('name', '')
                    entity_desc = entity.get('description', '')
                    if entity_name and entity_desc:
                        entity_desc_map[entity_name] = entity_desc
                
                logging.info(f"SUCCESS: Loaded descriptions for {len(entity_desc_map)} entities from entities.json")
                
                # Log a few sample descriptions for verification
                sample_count = min(3, len(entity_desc_map))
                sample_entities = list(entity_desc_map.items())[:sample_count]
                for entity_name, desc in sample_entities:
                    logging.info(f"SAMPLE_DESC: '{entity_name}' -> '{desc[:100]}{'...' if len(desc) > 100 else ''}'")
                
                return entity_desc_map
        except Exception as e:
            logging.error(f"Failed to load entity descriptions: {e}")
            return {}

    def _load_document_categories(self) -> Dict:
        """Load document categories from YAML config."""
        try:
            import yaml
            base_dir = Path(__file__).parent.parent
            project_root = base_dir.parent
            config_path = project_root / "data" / "document_classification_config.yaml"

            with open(str(config_path), 'r') as f:
                config = yaml.safe_load(f)

                # Store full config for use in prompts
                self.prompt_config = config

                categories = config.get('document_types', {}).get('categories', [])

                # Convert to dict for easy lookup
                cat_dict = {str(cat['id']): cat['name'] for cat in categories}
                logging.info(f"Loaded {len(cat_dict)} document categories: {cat_dict}")
                return cat_dict
        except Exception as e:
            logging.error(f"Failed to load document categories: {e}")
            # Set default config with values from app_config
            self.prompt_config = {
                'classification': {
                    'system_prompt': 'You are an expert document classifier for international trade and finance documents.',
                    'temperature': OPENAI_TEMPERATURE_CLASSIFICATION,
                    'max_tokens': OPENAI_MAX_TOKENS_CLASSIFICATION
                },
                'extraction': {
                    'system_prompt': 'You are an expert data extraction system for trade finance documents.',
                    'temperature': OPENAI_TEMPERATURE_EXTRACTION,
                    'max_tokens': OPENAI_MAX_TOKENS_EXTRACTION
                },
                'compliance': {
                    'system_prompt': 'You are a compliance verification expert for trade finance documents.',
                    'temperature': OPENAI_TEMPERATURE_COMPLIANCE,
                    'max_tokens': OPENAI_MAX_TOKENS_COMPLIANCE
                }
            }
            return {
                '1': 'Commercial Processes',
                '2': 'Transport Processes',
                '3': 'Border and Regulatory Processes',
                '4': 'Financial Processes',
                '5': 'Quality and Compliance Processes'
            }
    
    def _load_document_fields(self):
        """Load all document field definitions from DOC_LIST directory."""
        try:
            if not self.doc_list_path.exists():
                logging.error(f"DOC_LIST directory does not exist: {self.doc_list_path}")
                return
            
            for filename in os.listdir(str(self.doc_list_path)):
                if filename.endswith(".json"):
                    filepath = self.doc_list_path / filename
                    with open(str(filepath), 'r') as f:
                        data = json.load(f)

                        # Extract actual document type from JSON content if possible
                        doc_type_from_file = None
                        if isinstance(data, dict):
                            # Try common patterns
                            if "document_type" in data:
                                doc_type_from_file = data["document_type"]
                            elif "doc_type" in data:
                                doc_type_from_file = data["doc_type"]
                            # Fallback: use filename without extension
                            else:
                                doc_type_from_file = filename.replace("_OCR_Fields.json", "").replace(".json", "")

                        if not doc_type_from_file:
                            continue

                        # Use normalized version BUT DO NOT use it as a document type
                        normalized_key = doc_type_from_file.lower().replace("_", " ")
                        
                        # Store under both forms — but NEVER use cache keys as document types
                        self.document_fields_cache[normalized_key] = data
                        self.document_fields_cache[doc_type_from_file] = data

                        logging.info(f"Loaded fields for document: {doc_type_from_file} from {filename}")
        except Exception as e:
            logging.error(f"Failed to load document fields: {e}")

    def classify_document(self, ocr_text: str, websocket_handler=None, client_id=None, task_id=None) -> Dict:
        """
        Classify document using GPT with enhanced categorization based on DOC_LIST.

        Args:
            ocr_text: The OCR text to classify
            websocket_handler: Optional WebSocket handler for progress updates
            client_id: Optional client ID for WebSocket messages
            task_id: Optional task ID for tracking
        """
        # Use entity_mappings to organize documents by proper categories
        doc_types_by_category = {cat: [] for cat in self.document_categories.values()}

        # Map document types to their proper categories from entity_mappings
        for doc_id, mapping in self.entity_mappings.items():
            category_name = mapping.get('documentCategoryName', 'Other')
            document_name = mapping.get('documentName', doc_id)

            if category_name in doc_types_by_category:
                if document_name not in doc_types_by_category[category_name]:
                    doc_types_by_category[category_name].append(document_name)

        # Fallback: add any remaining documents from cache that aren't in entity_mappings
        # for doc_type in self.document_fields_cache.keys():
        #     found = False
        #     for cat_docs in doc_types_by_category.values():
        #         if doc_type.title() in cat_docs or doc_type.replace('_', ' ').title() in cat_docs:
        #             found = True
        #             break
        #     if not found:
        #         # Default to Financial Processes for LC/Guarantee type docs
        #         if any(keyword in doc_type.lower() for keyword in ["letter of credit", "bank guarantee", "lc", "guarantee"]):
        #             if "Financial Processes" in doc_types_by_category:
        #                 doc_types_by_category["Financial Processes"].append(doc_type.replace('_', ' ').title())
        #         # Default to Commercial Processes for others
        #         elif "Commercial Processes" in doc_types_by_category:
        #             doc_types_by_category["Commercial Processes"].append(doc_type.replace('_', ' ').title())

        # Build categorized document list for prompt
        category_sections = []
        for category_name in sorted(doc_types_by_category.keys()):
            if doc_types_by_category[category_name]:
                category_sections.append(f"**{category_name}:**\n{', '.join(sorted(doc_types_by_category[category_name]))}")

        # Get prompt template from config (with fallback)
        classification_config = self.prompt_config.get('classification', {})
        system_prompt = classification_config.get('system_prompt',
            'You are an expert document classifier for international trade and finance documents.')

        # Check if prompt_template exists in config, otherwise use default
        prompt_template = classification_config.get('prompt_template')

        if prompt_template:
            # Use template from YAML
            prompt = prompt_template.format(
                system_prompt=system_prompt,
                document_types_by_category=chr(10).join(category_sections),
                ocr_text=ocr_text[:25000]
            )
            logging.info("Printing the value of the prompt for the first page classification : {}".format(prompt))
        else:
            # Fallback to hardcoded template
            prompt = f"""
{system_prompt}

### Available Document Types by Business Process Category:

{chr(10).join(category_sections)}

### OCR Text to Classify:
"{ocr_text[:25000]}"

### Required Output:
Return ONLY this JSON structure (no markdown, no additional text):
{{
  "category": "<Exact category from the list above>",
  "document_type": "<Exact document type from the list above>",
  "sub_type": "<Specific sub-type if identifiable, otherwise null>",
  "confidence": <0-100>,
  "reasoning": "<Brief explanation>"
}}
"""
        try:
            # Ensure OpenAI is configured before each call (thread safety)
            if not openai.api_key:
                logging.warning("API key not set, reloading from environment")
                openai.api_type = AZURE_OPENAI_API_TYPE
                openai.api_base = os.getenv("AZURE_OPENAI_API_BASE")
                openai.api_version = AZURE_OPENAI_API_VERSION
                openai.api_key = os.getenv("AZURE_OPENAI_API_KEY")
            
            # Log API configuration for debugging
            logging.info(f"Attempting document classification with Azure OpenAI")
            logging.info(f"API Base: {openai.api_base}")
            logging.info(f"API Version: {openai.api_version}")
            logging.info(f"Deployment Name: {deployment_name}")
            logging.info(f"API Key exists: {bool(openai.api_key)}")
            logging.info(f"API Key length: {len(openai.api_key) if openai.api_key else 0}")

            # Use retry mechanism for OpenAI call with WebSocket support
            response = self._call_openai_with_retry(prompt, websocket_handler, client_id, task_id)

            logging.info(f"Document classification successful")
            content = response["choices"][0]["message"]["content"]
            result = self._extract_json_from_response(content)
            # Normalize document_type to use spaces instead of underscores
            if result and "document_type" in result:
                result["document_type"] = result["document_type"].replace("_", " ")
            return result
        except openai.error.AuthenticationError as e:
            logging.error(f"Azure OpenAI Authentication Error: {e}")
            logging.error(f"API Key: {openai.api_key[:10]}... (first 10 chars)" if openai.api_key else "API Key is None")
            logging.error(f"API Base: {openai.api_base}")
            logging.error(f"Deployment: {deployment_name}")
            return {
                "category": "unknown",
                "document_type": "unknown",
                "sub_type": None,
                "confidence": 0
            }
        except openai.error.InvalidRequestError as e:
            logging.error(f"Azure OpenAI Invalid Request Error: {e}")
            logging.error(f"This might be due to incorrect deployment name or API version")
            return {
                "category": "unknown",
                "document_type": "unknown",
                "sub_type": None,
                "confidence": 0
            }
        except Exception as e:
            logging.error(f"Document classification failed with unexpected error: {e}")
            logging.error(f"Error type: {type(e).__name__}")
            return {
                "category": "unknown",
                "document_type": "unknown",
                "sub_type": None,
                "confidence": 0
            }
    
    def get_document_fields(self, document_type: str, product_name: Optional[str] = None, 
                          function_name: Optional[str] = None) -> Tuple[List[str], Dict]:
        """
        Get fields for a document type, either from DOC_LIST or function_fields.json.
        Returns (field_list, field_definitions)
        """
        # Normalize document type
        doc_type_normalized = document_type.lower().replace(" ", "_")
        
        # First check if we have function-specific fields
        if product_name and function_name and product_name in self.function_fields:
            if function_name in self.function_fields[product_name]:
                func_fields = self.function_fields[product_name][function_name]
                return list(func_fields.keys()), func_fields
        
        # Then check DOC_LIST cache with multiple lookup strategies
        # Try different variations of the document type
        lookup_keys = [
            document_type.lower().replace("_", " "),  # bill_of_entry -> bill of entry
            document_type.lower(),                     # bill_of_entry
            document_type,                             # Bill_of_Entry (original case)
            document_type.replace("_", " "),          # Bill_of_Entry -> Bill of Entry
        ]
        
        doc_fields = None
        for key in lookup_keys:
            if key in self.document_fields_cache:
                doc_fields = self.document_fields_cache[key]
                logging.info(f"Found document fields for '{document_type}' using key '{key}'")
                break
        
        if doc_fields:
            # Handle both list and dict structures
            all_fields = []
            field_definitions = {}

            # Check if doc_fields is a list (array of field objects)
            if isinstance(doc_fields, list):
                # Extract field names and descriptions from list of objects
                for field_obj in doc_fields:
                    if isinstance(field_obj, dict) and 'name' in field_obj:
                        field_name = field_obj['name']
                        all_fields.append(field_name)
                        # Create definition from description if available
                        if 'description' in field_obj:
                            field_definitions[field_name] = field_obj['description']
                        else:
                            field_definitions[field_name] = field_name
                return all_fields, field_definitions

            # Handle nested dict structure like {"Letter of Credit (LC)": {"LC Identification": [...], ...}}
            elif isinstance(doc_fields, dict):
                for main_category, subcategories in doc_fields.items():
                    if isinstance(subcategories, dict):
                        for subcategory, fields in subcategories.items():
                            if isinstance(fields, list):
                                all_fields.extend(fields)
                                # Create field definitions with category info
                                for field in fields:
                                    field_definitions[field] = f"{field} ({subcategory})"
                            elif isinstance(fields, dict):
                                all_fields.extend(fields.keys())
                                field_definitions.update(fields)
                    elif isinstance(subcategories, list):
                        all_fields.extend(subcategories)
                        for field in subcategories:
                            field_definitions[field] = field

                return all_fields, field_definitions
        
        # Fallback to searching function_fields.json by function name
        if function_name and self.function_fields:
            # Search across all products for the function name
            for prod_name, functions in self.function_fields.items():
                if function_name in functions:
                    func_fields = functions[function_name]
                    logging.info(f"Found fields for function '{function_name}' in product '{prod_name}'")
                    return list(func_fields.keys()), func_fields
        
        # If no function name provided, try to find fields by document type pattern
        # Search for functions that might match the document type
        if self.function_fields:
            doc_type_patterns = {
                "letter_of_credit": ["register_import_lc", "issue_import_lc", "RegisterLCNew"],
                "lc": ["register_import_lc", "issue_import_lc", "RegisterLCNew"],
                "bank_guarantee": ["register_guarantee", "RegisterGuarantee"],
                "guarantee": ["register_guarantee", "RegisterGuarantee"],
                "bill_of_entry": ["register_import_lc", "issue_import_lc"],
                "be": ["register_import_lc", "issue_import_lc"]
            }
            
            if doc_type_normalized in doc_type_patterns:
                # Try to find fields from the first matching function
                for pattern_func in doc_type_patterns[doc_type_normalized]:
                    for prod_name, functions in self.function_fields.items():
                        if pattern_func in functions:
                            func_fields = functions[pattern_func]
                            logging.info(f"Found fields for document type '{document_type}' using function '{pattern_func}' from product '{prod_name}'")
                            return list(func_fields.keys()), func_fields
        
        # Final fallback to hardcoded fields if function_fields.json not available
        fallback_fields = {
            "letter_of_credit": {
                "APLB_RULE": "Applicable Rules",
                "APPL_CNTY_CD": "Applicant Country Code",
                "APPL_NM": "Applicant Name",
                "BENE_ADD1": "Beneficiary Address Line 1",
                "BENE_CNTY_CD": "Beneficiary Country Code",
                "BENE_NM": "Beneficiary Name",
                "EXPIRY_DT": "Expiry Date",
                "EXPIRY_PLC": "Place of Expiry",
                "FORM_OF_LC": "Form of LC",
                "LC_AMT": "LC Amount",
                "LC_CCY": "LC Currency"
            },
            "bank_guarantee": {
                "GUARANTEE_NUMBER": "Guarantee Number",
                "APPLICANT_NAME": "Applicant Name",
                "BENEFICIARY_NAME": "Beneficiary Name",
                "GUARANTEE_AMOUNT": "Guarantee Amount",
                "CURRENCY": "Currency",
                "ISSUE_DATE": "Issue Date",
                "EXPIRY_DATE": "Expiry Date",
                "TYPE_OF_GUARANTEE": "Type of Guarantee",
                "UNDERLYING_CONTRACT": "Underlying Contract",
                "ISSUING_BANK": "Issuing Bank"
            }
        }
        
        if doc_type_normalized in fallback_fields:
            fields = fallback_fields[doc_type_normalized]
            logging.info(f"Using hardcoded fallback fields for document type '{document_type}'")
            return list(fields.keys()), fields
        
        # Return empty if no fields found
        logging.warning(f"No field definitions found for document type: {document_type}")
        return [], {}

    def _call_openai_with_retry(self, prompt: str, websocket_handler=None, client_id=None, task_id=None) -> Dict:
        """
        Call OpenAI API with automatic retry on failures.
        Uses WebSocket-aware retry if WebSocket handler is provided.

        Args:
            prompt: The prompt to send to OpenAI
            websocket_handler: Optional WebSocket handler for progress updates
            client_id: Optional client ID for WebSocket messages
            task_id: Optional task ID for tracking

        Returns:
            OpenAI API response dictionary
        """
        # Use WebSocket-aware retry if handler is provided
        if websocket_handler and client_id:
            retry_decorator = create_websocket_retry(
                websocket_handler=websocket_handler,
                client_id=client_id,
                task_id=task_id or "document_classification",
                # max_retries=None uses admin config automatically
                max_delay=OPENAI_MAX_DELAY
            )

            @retry_decorator
            def call_api():
                return openai.ChatCompletion.create(
                    engine=deployment_name,
                    messages=[
                        {"role": "system", "content": "You are a document classification assistant."},
                        {"role": "user", "content": prompt.strip()}
                    ],
                    temperature=OPENAI_TEMPERATURE_DEFAULT
                )

            return call_api()
        else:
            # Use standard retry without WebSocket updates
            @retry_openai
            def call_api():
                return openai.ChatCompletion.create(
                    engine=deployment_name,
                    messages=[
                        {"role": "system", "content": "You are a document classification assistant."},
                        {"role": "user", "content": prompt.strip()}
                    ],
                    temperature=OPENAI_TEMPERATURE_DEFAULT
                )

            return call_api()

    def _extract_json_from_response(self, response: str) -> Dict:
        """Extract JSON from GPT response."""
        try:
            # Try to find JSON in the response
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return json.loads(response)
        except Exception as e:
            logging.error(f"Failed to extract JSON from response: {e}")
            return {
                "category": "unknown",
                "document_type": "unknown",
                "sub_type": None,
                "confidence": 0
            }

    def get_enhanced_entity_fields(self, document_id: str) -> Dict:
        """Get organized entity fields for a document type with descriptions."""
        # Try exact match first
        if document_id in self.entity_mappings:
            mapping = self.entity_mappings[document_id]
        else:
            # Try case-insensitive match
            doc_id_lower = document_id.lower()
            mapping = None
            for key in self.entity_mappings.keys():
                if key.lower() == doc_id_lower:
                    mapping = self.entity_mappings[key]
                    break

            if not mapping:
                logging.warning(f"No entity mappings found for document: {document_id}")
                return {
                    'mandatory_fields': [],
                    'optional_fields': [],
                    'conditional_fields': [],
                    'fields_by_category': {}
                }

        # Enhance fields with descriptions from entities.json
        def enhance_field_with_description(field):
            entity_name = field.get('entityName', '')
            description = self.entity_descriptions.get(entity_name, '')
            enhanced_field = field.copy()
            enhanced_field['description'] = description
            
            # Log field enhancement for debugging
            if description:
                logging.info(f"FIELD_ENHANCED: '{entity_name}' -> Description: '{description[:80]}{'...' if len(description) > 80 else ''}'")
            else:
                logging.warning(f"FIELD_NO_DESC: '{entity_name}' -> No description found in entities.json")
            
            return enhanced_field

        # Enhance all field types with descriptions
        enhanced_mandatory = [enhance_field_with_description(f) for f in mapping['mandatory_fields']]
        enhanced_optional = [enhance_field_with_description(f) for f in mapping['optional_fields']]
        enhanced_conditional = [enhance_field_with_description(f) for f in mapping['conditional_fields']]

        logging.info(f"ENHANCEMENT_COMPLETE: Enhanced {len(enhanced_mandatory)} mandatory, {len(enhanced_optional)} optional, {len(enhanced_conditional)} conditional fields with descriptions")

        # Organize fields by data category with descriptions
        fields_by_category = {}
        for field in enhanced_mandatory + enhanced_optional + enhanced_conditional:
            category = field.get('dataCategoryValue', 'Other')
            if category not in fields_by_category:
                fields_by_category[category] = []
            fields_by_category[category].append(field)

        return {
            'mandatory_fields': enhanced_mandatory,
            'optional_fields': enhanced_optional,
            'conditional_fields': enhanced_conditional,
            'fields_by_category': fields_by_category
        }

    def build_extraction_prompt(self, document_type: str, ocr_text: str, page_number: int = 1) -> str:
        """Build extraction prompt dynamically based on entity mappings."""
        # Normalize document type to match entity_mappings keys
        doc_id = document_type.replace(' ', '_')
        logging.info("Printing the document id used for building extraction prompt : {}".format(doc_id))
        logging.info("Printing the document type used for building extraction prompt : {}".format(document_type))

        # Get entity fields for this document type
        entity_info = self.get_enhanced_entity_fields(doc_id)
        logging.info(f"Entity info for {doc_id}: {entity_info}")

        # Get document category info using case-insensitive lookup
        doc_category = "Unknown"
        if doc_id in self.entity_mappings:
            doc_category = self.entity_mappings[doc_id].get('documentCategoryName', 'Unknown')
        else:
            # Try case-insensitive match
            doc_id_lower = doc_id.lower()
            for key in self.entity_mappings.keys():
                if key.lower() == doc_id_lower:
                    doc_category = self.entity_mappings[key].get('documentCategoryName', 'Unknown')
                    break

        # Get extraction config flags
        extraction_config = self.prompt_config.get('extraction', {})
        extract_mandatory = extraction_config.get('extract_mandatory', True)
        extract_optional = extraction_config.get('extract_optional', True)
        extract_conditional = extraction_config.get('extract_conditional', True)

        # Build field sections with CLEAR separation by field type
        mandatory_sections = []
        optional_sections = []
        conditional_sections = []

        total_mandatory = 0
        total_optional = 0
        total_conditional = 0

        # Build mandatory fields section if enabled
        if extract_mandatory and entity_info['mandatory_fields']:
            mandatory_by_category = {}
            for field in entity_info['mandatory_fields']:
                category = field.get('dataCategoryValue', 'Other')
                if category not in mandatory_by_category:
                    mandatory_by_category[category] = []
                
                field_name = field.get('entityName', '')
                field_desc = field.get('description', '')
                desc_text = f" - {field_desc}" if field_desc else " - No specific description available"
                mandatory_by_category[category].append(f"  - **{field_name}**{desc_text}")
            
            for category in sorted(mandatory_by_category.keys()):
                mandatory_sections.append(f"**{category}:**\n" + "\n".join(mandatory_by_category[category]))
            
            total_mandatory = len(entity_info['mandatory_fields'])

        # Build optional fields section if enabled
        if extract_optional and entity_info['optional_fields']:
            optional_by_category = {}
            for field in entity_info['optional_fields']:
                category = field.get('dataCategoryValue', 'Other')
                if category not in optional_by_category:
                    optional_by_category[category] = []
                
                field_name = field.get('entityName', '')
                field_desc = field.get('description', '')
                desc_text = f" - {field_desc}" if field_desc else " - No specific description available"
                optional_by_category[category].append(f"  - **{field_name}**{desc_text}")
            
            for category in sorted(optional_by_category.keys()):
                optional_sections.append(f"**{category}:**\n" + "\n".join(optional_by_category[category]))
            
            total_optional = len(entity_info['optional_fields'])

        # Build conditional fields section if enabled
        if extract_conditional and entity_info['conditional_fields']:
            conditional_by_category = {}
            for field in entity_info['conditional_fields']:
                category = field.get('dataCategoryValue', 'Other')
                if category not in conditional_by_category:
                    conditional_by_category[category] = []
                
                field_name = field.get('entityName', '')
                field_desc = field.get('description', '')
                desc_text = f" - {field_desc}" if field_desc else " - No specific description available"
                conditional_by_category[category].append(f"  - **{field_name}**{desc_text}")
            
            for category in sorted(conditional_by_category.keys()):
                conditional_sections.append(f"**{category}:**\n" + "\n".join(conditional_by_category[category]))
            
            total_conditional = len(entity_info['conditional_fields'])

        # Build the complete fields text with clear sections based on what's enabled
        fields_sections = []
        
        if mandatory_sections:
            mandatory_text = "\n\n".join(mandatory_sections)
            fields_sections.append(f"### MANDATORY FIELDS (REQUIRED - Must be extracted):\n{mandatory_text}")
        
        if optional_sections:
            optional_text = "\n\n".join(optional_sections)
            fields_sections.append(f"### OPTIONAL FIELDS (Extract if clearly present):\n{optional_text}")
        
        if conditional_sections:
            conditional_text = "\n\n".join(conditional_sections)
            fields_sections.append(f"### CONDITIONAL FIELDS (Extract based on document context):\n{conditional_text}")

        fields_text = "\n\n".join(fields_sections) if fields_sections else "No fields configured for extraction."
        
        # Calculate total fields to extract
        total_all_fields = total_mandatory + total_optional + total_conditional
        
        # Log sample of fields_text to show descriptions being included
        logging.info(f"PROMPT_FIELDS_PREVIEW: Extraction flags - Mandatory:{extract_mandatory}, Optional:{extract_optional}, Conditional:{extract_conditional}")
        logging.info(f"PROMPT_FIELDS_COUNTS: Total fields to extract: {total_all_fields} (M:{total_mandatory} O:{total_optional} C:{total_conditional})")
        logging.info(f"PROMPT_FIELDS_PREVIEW: Generated fields section (first 500 chars): {fields_text[:500]}{'...' if len(fields_text) > 500 else ''}")

        # Get system prompt from config
        system_prompt = extraction_config.get('system_prompt',
            'You are an expert data extraction system for trade finance documents.')

        # Check if prompt_template exists in config
        prompt_template = extraction_config.get('prompt_template')

        # Build extraction instructions based on enabled field types
        extraction_instructions = []
        if extract_mandatory:
            extraction_instructions.append(f"1. **MANDATORY fields** ({total_mandatory} fields) - These are REQUIRED and MUST be included in response. Return ALL mandatory fields even if value is empty.")
        if extract_optional:
            extraction_instructions.append(f"2. **OPTIONAL fields** ({total_optional} fields) - Include ONLY if you found a value in the document. DO NOT include optional fields with empty values.")
        if extract_conditional:
            extraction_instructions.append(f"3. **CONDITIONAL fields** ({total_conditional} fields) - Include ONLY if you found a value and field is relevant to document context. DO NOT include conditional fields with empty values.")
        
        extraction_instructions_text = "\n".join(extraction_instructions) if extraction_instructions else "No extraction instructions defined."

        if prompt_template:
            # Use template from YAML with dynamic field sections
            prompt = f"""
    {system_prompt}

    ### Document Information:
    - **Document Type**: {document_type}
    - **Category**: {doc_category} (USE THIS EXACT VALUE in response)
    - **Page**: {page_number}

    ### CRITICAL: Extract Configured Field Types

    **YOU MUST extract the following field types as configured:**
    {extraction_instructions_text}

    **Total fields to extract: {total_all_fields}**

    ### CRITICAL FORMATTING RULES (MUST FOLLOW):

    1. **Dates**: Convert ALL dates to YYYY-MM-DD format
    - "210429" → "2021-04-29"
    - "29/04/21" → "2021-04-29"
    - "Apr 29, 2021" → "2021-04-29"

    2. **Amounts**: ALWAYS include currency code
    - "60,465.00" → "USD 60,465.00" (add USD if currency not stated)
    - Use format: "CURRENCY_CODE AMOUNT"

    3. **Bounding Boxes**: Use [0, 0, 0, 0] if no OCR coordinates available
    - DO NOT fabricate coordinates like [100, 100, 200, 200]
    - Only use actual coordinates if present in OCR data

    4. **Document Type in Response**: Use EXACT format with proper spacing
    - Use "{document_type}" NOT "letter_of_credit"
    - Preserve spaces, not underscores

    5. **CRITICAL - Field Inclusion Rules**:
    - **MANDATORY fields**: MUST include ALL mandatory fields in response, even if value is empty (use "" with confidence 0)
    - **OPTIONAL fields**: Include ONLY if you found a value in the document. Skip optional fields with no value.
    - **CONDITIONAL fields**: Include ONLY if you found a value and field is relevant. Skip conditional fields with no value.
    - This selective inclusion reduces response size and improves clarity by showing only relevant optional/conditional data

    ### Fields to Extract:

    {fields_text}

    ### OCR Text (Page {page_number}):
    {ocr_text[:25000]}

    ### Required JSON Response:
    Return ONLY valid JSON (no markdown, no commentary):

    {{
    "page_number": {page_number},
    "classification": {{
        "category": "{doc_category}",
        "document_type": "{document_type}",
        "sub_type": "<specific sub-type or null>"
    }},
    "extracted_fields": {{
        "<Field_Name>": {{
        "value": "<extracted value or empty string>",
        "exact_text":"exact value that is present in the txt i sent u without anychages in space etc",
        "confidence": <0-100>,
        "bounding_box": [<x1>, <y1>, <x2>, <y2>],
        "bounding_page": {page_number},
        "field_type": "<mandatory|optional|conditional>"
        }}
    }},
    "confidence_score": <overall 0-100>,
    "mandatory_fields_found": <count of mandatory fields with values>,
    "optional_fields_found": <count of optional fields with values>,
    "conditional_fields_found": <count of conditional fields with values>,
    "total_mandatory_fields": {total_mandatory},
    "total_optional_fields": {total_optional},
    "total_conditional_fields": {total_conditional},
    "total_fields_extracted": <total count of all extracted fields with values>,
    "extraction_completeness": <percentage 0-100 based on fields found vs total configured>
    }}

    **CRITICAL REMINDER - Field Inclusion Rules:**
    - **MANDATORY fields ({total_mandatory})**: Include ALL in response, even if empty (use "" with confidence 0)
    - **OPTIONAL fields ({total_optional})**: Include ONLY if value found. Skip if empty.
    - **CONDITIONAL fields ({total_conditional})**: Include ONLY if value found and relevant. Skip if empty.
    
    **This means your extracted_fields will contain:**
    - All {total_mandatory} mandatory fields (some may be empty)
    - Only optional/conditional fields that have values
    """
        else:
            # Fallback to hardcoded template with enhanced field descriptions
            prompt = f"""
{system_prompt}

### Document Information:
- **Document Type**: {document_type}
- **Category**: {doc_category} (USE THIS EXACT VALUE in response)
- **Page**: {page_number}

### Entity Extraction Instructions:
**CRITICAL: We are providing you with enhanced field definitions that include detailed descriptions from our entity database. Each field below follows the format:**
**Field Name (Type) - Detailed Description**

**These descriptions are sourced from our entities.json database and provide precise definitions of what each field represents. Use these descriptions as your primary guide for accurate field identification and extraction.**

**CRITICAL - Field Inclusion Rules:**
- **MANDATORY fields**: Include ALL in response, even if empty (use "" with confidence 0)
- **OPTIONAL fields**: Include ONLY if value found in document. Skip if empty.
- **CONDITIONAL fields**: Include ONLY if value found and relevant. Skip if empty.

### Fields to Extract (organized by data category):

{fields_text}

### Extraction Guidelines:
1. **Entity Descriptions**: Each field above includes a detailed description from our entity database explaining exactly what information to look for in the document.
2. **Definition-Based Extraction**: Use the provided descriptions as the authoritative definition of each field. If you're unsure about a field, refer back to its description.
3. **Precision**: The descriptions help you distinguish between similar-looking fields and ensure you extract the exact data element we need.
4. **Context Matching**: Match the OCR text against the field descriptions to identify the correct business entities.
5. **Field Type Priority**: Pay attention to (REQUIRED), (conditional), and (optional) indicators along with the descriptions.

### OCR Text (Page {page_number}):
{ocr_text[:25000]}

### Required JSON Response:
Return ONLY valid JSON (no markdown, no commentary):

{{
  "page_number": {page_number},
  "classification": {{
    "category": "{doc_category}",
    "document_type": "{document_type}",
    "sub_type": "<specific sub-type or null>"
  }},
  "extracted_fields": {{
    "<Field_Name>": {{
      "value": "<extracted value or empty string>",
      "exact_text":"exact value that is present in the txt i sent u without anychages in space etc",
      "confidence": <0-100>,
      "bounding_box": [<x1>, <y1>, <x2>, <y2>],
      "bounding_page": {page_number}
    }}
  }},
  "confidence_score": <overall 0-100>,
  "mandatory_fields_found": <count>,
  "total_mandatory_fields": {len(entity_info['mandatory_fields'])},
  "extraction_completeness": <percentage 0-100>
}}
"""
        
        # Log final prompt statistics
        prompt_length = len(prompt)
        logging.info(f"PROMPT_COMPLETE: Generated extraction prompt with descriptions - Length: {prompt_length} chars, Configured fields: {total_all_fields}")
        
        return prompt

    def build_extraction_prompt_for_entities(self, field_list: List[str], 
                                            field_definitions: Dict[str, str],
                                            ocr_text: str, page_number: int, 
                                            chunk_id: int) -> str:
        """
        Build extraction prompt for a specific subset of entities (chunk-based extraction).
        
        Args:
            field_list: List of field names to extract
            field_definitions: Dictionary mapping field names to their definitions
            ocr_text: OCR text to extract from
            page_number: Page number for context
            chunk_id: Chunk identifier for logging
            
        Returns:
            String prompt for LLM
        """
        logging.info(f"Building chunk {chunk_id} extraction prompt for {len(field_list)} entities")
        
        # Get extraction config
        extraction_config = self.prompt_config.get('extraction', {})
        system_prompt = extraction_config.get('system_prompt',
            'You are an expert data extraction system for trade finance documents.')

        # Build fields section for this chunk
        fields_text = ""
        for field_name in field_list:
            field_def = field_definitions.get(field_name, f"{field_name} - No description available")
            fields_text += f"- **{field_def}**\n"

        # Build chunk-specific prompt
        prompt = f"""
{system_prompt}

### Extraction Task - Chunk {chunk_id}
You are processing a subset of entities for efficient parallel extraction.

### Critical Instructions:
1. Extract ONLY the fields listed below - do not extract any other fields
2. Focus on accuracy and precision for these specific fields
3. Use the field descriptions as your guide for identification
4. Include ALL fields in response, even if empty (use "" with confidence 0)

### Fields to Extract in This Chunk ({len(field_list)} fields):

{fields_text}

### Formatting Rules:
1. **Dates**: Convert to YYYY-MM-DD format
2. **Amounts**: Include currency code (e.g., "USD 60,465.00")
3. **Bounding Boxes**: Use [0, 0, 0, 0] if no OCR coordinates available
4. **Empty Fields**: Use empty string "" with confidence 0 if not found

### OCR Text (Page {page_number}):
{ocr_text[:16000]}

### Required JSON Response:
Return ONLY valid JSON (no markdown, no commentary):

{{
  "page_number": {page_number},
  "chunk_id": {chunk_id},
  "extracted_fields": {{
    "<Field_Name>": {{
      "value": "<extracted value or empty string>",
      "exact_text":"exact value that is present in the txt i sent u without anychages in space etc",
      "confidence": <0-100>,
      "bounding_box": [<x1>, <y1>, <x2>, <y2>],
      "bounding_page": {page_number}
    }}
  }},
  "fields_processed": {len(field_list)},
  "chunk_confidence": <overall 0-100>
}}

IMPORTANT: Extract ONLY the {len(field_list)} fields listed above. Do not include any other fields.
"""
        
        logging.info(f"Generated chunk {chunk_id} prompt: {len(prompt)} chars for {len(field_list)} fields")
        return prompt

    def check_compliance(self, document_type: str, extracted_fields: Dict) -> Dict:
        """Check compliance of extracted fields against mandatory requirements."""
        # Normalize document type
        doc_id = document_type.replace(' ', '_')

        # Get entity fields for this document type
        entity_info = self.get_enhanced_entity_fields(doc_id)

        # Initialize compliance results
        compliance_result = {
            'is_compliant': True,
            'missing_mandatory_fields': [],
            'found_mandatory_fields': [],
            'optional_fields_found': [],
            'total_mandatory': len(entity_info['mandatory_fields']),
            'mandatory_found_count': 0,
            'compliance_score': 0,
            'field_issues': []
        }

        # Check mandatory fields
        for field in entity_info['mandatory_fields']:
            field_name = field.get('entityName', '')
            field_found = False

            # Check if field exists in extracted_fields
            if extracted_fields and field_name in extracted_fields:
                field_value = extracted_fields[field_name]
                # Check if value is not empty/null/"Not Found"
                if isinstance(field_value, dict):
                    value = field_value.get('value', '')
                else:
                    value = field_value

                if value and value not in ['Not Found', 'N/A', '', None]:
                    field_found = True
                    compliance_result['found_mandatory_fields'].append(field_name)

            if not field_found:
                compliance_result['is_compliant'] = False
                compliance_result['missing_mandatory_fields'].append({
                    'field_name': field_name,
                    'category': field.get('dataCategoryValue', 'Unknown'),
                    'severity': 'critical'
                })

        # Calculate compliance metrics
        compliance_result['mandatory_found_count'] = len(compliance_result['found_mandatory_fields'])

        if compliance_result['total_mandatory'] > 0:
            compliance_result['compliance_score'] = int(
                (compliance_result['mandatory_found_count'] / compliance_result['total_mandatory']) * 100
            )
        else:
            compliance_result['compliance_score'] = 100

        # Check optional fields that were found
        for field in entity_info['optional_fields']:
            field_name = field.get('entityName', '')
            if extracted_fields and field_name in extracted_fields:
                field_value = extracted_fields[field_name]
                if isinstance(field_value, dict):
                    value = field_value.get('value', '')
                else:
                    value = field_value

                if value and value not in ['Not Found', 'N/A', '', None]:
                    compliance_result['optional_fields_found'].append(field_name)

        return compliance_result