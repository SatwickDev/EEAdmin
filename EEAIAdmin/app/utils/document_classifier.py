import json
import os
import logging
from typing import Dict, List, Optional, Tuple
import openai
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from app.utils.app_config import deployment_name
import app.utils.app_config as app_config
from app.utils.openai_retry import retry_openai, create_websocket_retry


class DocumentClassifier:
    def __init__(self):
        logging.info("Initializing DocumentClassifier...")

        # Always load from environment variables to ensure we have the credentials
        openai.api_type = "azure"
        openai.api_base = os.getenv("AZURE_OPENAI_API_BASE")
        openai.api_version = "2024-10-01-preview"
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

        self.document_fields_cache = {}
        self.function_fields = self._load_function_fields()
        self.entity_mappings = self._load_entity_mappings()  # Load entity maintenance data
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
            # Set default config
            self.prompt_config = {
                'classification': {
                    'system_prompt': 'You are an expert document classifier for international trade and finance documents.',
                    'temperature': 0.1,
                    'max_tokens': 500
                },
                'extraction': {
                    'system_prompt': 'You are an expert data extraction system for trade finance documents.',
                    'temperature': 0,
                    'max_tokens': 3000
                },
                'compliance': {
                    'system_prompt': 'You are a compliance verification expert for trade finance documents.',
                    'temperature': 0.2,
                    'max_tokens': 1500
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
                    # Handle both patterns: *_OCR_Fields.json and *.json
                    if filename.endswith("_OCR_Fields.json"):
                        doc_type = filename.replace("_OCR_Fields.json", "")
                    else:
                        doc_type = filename.replace(".json", "")
                    
                    # Normalize the document type (lowercase, underscores to spaces)
                    doc_type_normalized = doc_type.lower().replace("_", " ")
                    
                    filepath = self.doc_list_path / filename
                    with open(str(filepath), 'r') as f:
                        data = json.load(f)
                        self.document_fields_cache[doc_type_normalized] = data
                        
                        # Also store with original case for case-sensitive lookups
                        self.document_fields_cache[doc_type] = data
                        
                        logging.info(f"Loaded fields for document type: {doc_type_normalized} from {filename}")
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
        doc_types_by_category = {}

        # Initialize with the 5 proper categories from entity_mappings
        for cat_id, cat_name in self.document_categories.items():
            doc_types_by_category[cat_name] = []

        # Map document types to their proper categories from entity_mappings
        for doc_id, mapping in self.entity_mappings.items():
            category_name = mapping.get('documentCategoryName', 'Other')
            document_name = mapping.get('documentName', doc_id)

            if category_name in doc_types_by_category:
                if document_name not in doc_types_by_category[category_name]:
                    doc_types_by_category[category_name].append(document_name)

        # Fallback: add any remaining documents from cache that aren't in entity_mappings
        for doc_type in self.document_fields_cache.keys():
            found = False
            for cat_docs in doc_types_by_category.values():
                if doc_type.title() in cat_docs or doc_type.replace('_', ' ').title() in cat_docs:
                    found = True
                    break
            if not found:
                # Default to Financial Processes for LC/Guarantee type docs
                if any(keyword in doc_type.lower() for keyword in ["letter of credit", "bank guarantee", "lc", "guarantee"]):
                    if "Financial Processes" in doc_types_by_category:
                        doc_types_by_category["Financial Processes"].append(doc_type.replace('_', ' ').title())
                # Default to Commercial Processes for others
                elif "Commercial Processes" in doc_types_by_category:
                    doc_types_by_category["Commercial Processes"].append(doc_type.replace('_', ' ').title())
        
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
                openai.api_type = "azure"
                openai.api_base = os.getenv("AZURE_OPENAI_API_BASE")
                openai.api_version = "2024-10-01-preview"
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
                max_delay=300.0
            )

            @retry_decorator
            def call_api():
                return openai.ChatCompletion.create(
                    engine=deployment_name,
                    messages=[
                        {"role": "system", "content": "You are a document classification assistant."},
                        {"role": "user", "content": prompt.strip()}
                    ],
                    temperature=0.0
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
                    temperature=0.0
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
        """Get organized entity fields for a document type."""
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

        # Organize fields by data category
        fields_by_category = {}
        for field in mapping['mandatory_fields'] + mapping['optional_fields'] + mapping['conditional_fields']:
            category = field.get('dataCategoryValue', 'Other')
            if category not in fields_by_category:
                fields_by_category[category] = []
            fields_by_category[category].append(field)

        return {
            'mandatory_fields': mapping['mandatory_fields'],
            'optional_fields': mapping['optional_fields'],
            'conditional_fields': mapping['conditional_fields'],
            'fields_by_category': fields_by_category
        }

    def build_extraction_prompt(self, document_type: str, ocr_text: str, page_number: int = 1) -> str:
        """Build extraction prompt dynamically based on entity mappings."""
        # Normalize document type to match entity_mappings keys
        doc_id = document_type.replace(' ', '_')

        # Get entity fields for this document type
        entity_info = self.get_enhanced_entity_fields(doc_id)

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

        # Build field sections organized by category
        field_sections = []

        if entity_info['fields_by_category']:
            for category, fields in sorted(entity_info['fields_by_category'].items()):
                field_items = []
                for field in fields:
                    field_name = field.get('entityName', '')
                    # Determine field type indicator
                    if field in entity_info['mandatory_fields']:
                        field_items.append(f"  - **{field_name}** (REQUIRED)")
                    elif field in entity_info['conditional_fields']:
                        field_items.append(f"  - **{field_name}** (conditional)")
                    else:
                        field_items.append(f"  - **{field_name}** (optional)")

                if field_items:
                    field_sections.append(f"**{category}:**\n" + "\n".join(field_items))

        fields_text = "\n\n".join(field_sections) if field_sections else "No specific fields configured for this document type."

        # Build mandatory fields summary
        mandatory_summary = ""
        if entity_info['mandatory_fields']:
            mandatory_list = [f"- {f.get('entityName', '')}" for f in entity_info['mandatory_fields']]
            mandatory_summary = f"\n\n### REQUIRED Fields (MUST be extracted):\n" + "\n".join(mandatory_list)

        # Get prompt template from config (with fallback)
        extraction_config = self.prompt_config.get('extraction', {})
        system_prompt = extraction_config.get('system_prompt',
            'You are an expert data extraction system for trade finance documents.')

        # Check if prompt_template exists in config
        prompt_template = extraction_config.get('prompt_template')

        if prompt_template:
            # Use template from YAML
            prompt = prompt_template.format(
                system_prompt=system_prompt,
                document_type=document_type,
                doc_category=doc_category,
                page_number=page_number,
                fields_text=fields_text,
                mandatory_summary=mandatory_summary,
                ocr_text=ocr_text[:25000],
                total_mandatory=len(entity_info['mandatory_fields'])
            )
        else:
            # Fallback to hardcoded template
            prompt = f"""
{system_prompt}

### Document Information:
- **Document Type**: {document_type}
- **Category**: {doc_category} (USE THIS EXACT VALUE in response)
- **Page**: {page_number}

### Fields to Extract (organized by data category):

{fields_text}{mandatory_summary}

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