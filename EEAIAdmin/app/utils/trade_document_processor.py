"""
Trade Document Processor
Enhanced document classification and extraction based on UNTDED data elements
Supports 36+ trade finance and logistics documents
"""

import json
import os
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import openai
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class TradeDocumentProcessor:
    """
    Advanced document processor using UNTDED (UN/EDIFACT Trade Data Element Directory)
    data elements for comprehensive classification, extraction, and validation
    """

    def __init__(self):
        """Initialize the trade document processor with data element mappings"""
        logger.info("Initializing TradeDocumentProcessor...")

        # Load trade document data elements
        base_dir = Path(__file__).parent.parent
        self.data_elements_path = base_dir / "prompts" / "trade_document_data_elements.json"
        self.data_elements = self._load_data_elements()

        # Set up OpenAI configuration
        openai.api_type = "azure"
        openai.api_base = os.getenv("AZURE_OPENAI_API_BASE")
        openai.api_version = "2024-10-01-preview"
        openai.api_key = os.getenv("AZURE_OPENAI_API_KEY")

        logger.info(f"Loaded {len(self.data_elements.get('documents', []))} document types")
        logger.info("TradeDocumentProcessor initialized successfully")

    def _load_data_elements(self) -> Dict:
        """Load UNTDED data elements from JSON file"""
        try:
            with open(str(self.data_elements_path), 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load trade document data elements: {e}")
            return {"documents": [], "data_elements": {}}

    def get_document_by_code(self, code: str) -> Optional[Dict]:
        """Get document definition by code (e.g., 'LC', 'INV', 'BoL')"""
        for doc in self.data_elements.get("documents", []):
            if doc.get("code") == code:
                return doc
        return None

    def get_document_by_name(self, name: str) -> Optional[Dict]:
        """Get document definition by name"""
        name_lower = name.lower()
        for doc in self.data_elements.get("documents", []):
            if doc.get("name", "").lower() == name_lower:
                return doc
        return None

    def classify_document(self, ocr_text: str, hint: Optional[str] = None) -> Dict:
        """
        Classify document type using GPT with UNTDED document types

        Args:
            ocr_text: Extracted text from document
            hint: Optional hint about document type

        Returns:
            Dictionary with classification results
        """
        try:
            # Build document types list
            doc_types_list = [
                f"{doc['code']} - {doc['name']}"
                for doc in self.data_elements.get("documents", [])
            ]

            # Create classification prompt
            prompt = f"""You are a trade finance and logistics document classification expert.
Based on the UNTDED (UN/EDIFACT Trade Data Element Directory) standards, classify the following document.

Available document types:
{chr(10).join(doc_types_list)}

Document text:
{ocr_text[:3000]}  # Limit to first 3000 characters

Analyze the document and provide:
1. Document Code (e.g., LC, INV, BoL, PO)
2. Document Name (full name)
3. Document Category (Transactional, Transport, Communication, Regulatory, or Banking)
4. Confidence Score (0-100)
5. Sub-type if applicable (e.g., for LC: import/export, for Invoice: commercial/proforma)

Respond ONLY in valid JSON format:
{{
    "code": "document_code",
    "name": "Document Full Name",
    "category": "category",
    "sub_type": "sub-type if applicable",
    "confidence": 95
}}"""

            deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")

            response = openai.ChatCompletion.create(
                engine=deployment_name,
                messages=[
                    {"role": "system", "content": "You are a trade document classification expert. Respond only with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=500
            )

            result_text = response['choices'][0]['message']['content'].strip()

            # Parse JSON response
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]

            result = json.loads(result_text.strip())

            logger.info(f"Classification result: {result}")
            return result

        except Exception as e:
            logger.error(f"Document classification failed: {e}")
            return {
                "code": "UNK",
                "name": "Unknown Document",
                "category": "Unknown",
                "confidence": 0,
                "error": str(e)
            }

    def get_required_fields(self, doc_code: str) -> Dict[str, List[Dict]]:
        """
        Get all required, optional, and conditional fields for a document type

        Args:
            doc_code: Document code (e.g., 'LC', 'INV')

        Returns:
            Dictionary with categorized fields
        """
        fields = {
            "mandatory": [],
            "optional": [],
            "conditional": []
        }

        # Get requirement codes
        req_codes = self.data_elements.get("metadata", {}).get("requirement_codes", {})

        # Check all data element categories
        for category_name, elements in self.data_elements.get("data_elements", {}).items():
            for element in elements:
                requirements = element.get("requirements", {})
                if doc_code in requirements:
                    req_type = requirements[doc_code]
                    field_info = {
                        "uid": element.get("uid"),
                        "name": element.get("name"),
                        "description": element.get("description"),
                        "category": category_name
                    }

                    if req_type == "M":
                        fields["mandatory"].append(field_info)
                    elif req_type == "O":
                        fields["optional"].append(field_info)
                    elif req_type == "C":
                        fields["conditional"].append(field_info)

        logger.info(f"Document {doc_code} has {len(fields['mandatory'])} mandatory, "
                   f"{len(fields['optional'])} optional, {len(fields['conditional'])} conditional fields")

        return fields

    def extract_fields(self, ocr_text: str, doc_code: str) -> Dict:
        """
        Extract data fields from document based on UNTDED requirements

        Args:
            ocr_text: Extracted text from document
            doc_code: Document code (e.g., 'LC', 'INV')

        Returns:
            Dictionary with extracted field values
        """
        try:
            # Get required fields for this document type
            required_fields = self.get_required_fields(doc_code)

            # Build extraction prompt
            all_fields = (
                required_fields['mandatory'] +
                required_fields['optional'] +
                required_fields['conditional']
            )

            fields_description = "\n".join([
                f"- {field['uid']} ({field['name']}): {field['description']}"
                for field in all_fields[:30]  # Limit to first 30 fields to avoid token limits
            ])

            prompt = f"""You are a trade document data extraction expert.
Extract the following data elements from the document text according to UNTDED standards.

Document Type: {doc_code}

Required Data Elements:
{fields_description}

Document Text:
{ocr_text[:4000]}

Extract all available fields and return as JSON object with field UIDs as keys.
For missing fields, use null. For dates, use ISO 8601 format (YYYY-MM-DD).

Example format:
{{
    "1004": "DOC-12345",
    "2007": "2025-01-15",
    "3002": "ABC Corporation Ltd.",
    "5444": 150000.00
}}

Respond ONLY with valid JSON."""

            deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")

            response = openai.ChatCompletion.create(
                engine=deployment_name,
                messages=[
                    {"role": "system", "content": "You are a trade document data extraction expert. Respond only with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=2000
            )

            result_text = response['choices'][0]['message']['content'].strip()

            # Parse JSON response
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]

            extracted_data = json.loads(result_text.strip())

            # Map UIDs to field names for better readability
            mapped_data = {}
            for uid, value in extracted_data.items():
                field = next((f for f in all_fields if f['uid'] == uid), None)
                if field:
                    mapped_data[field['name']] = {
                        "uid": uid,
                        "value": value,
                        "category": field['category']
                    }

            logger.info(f"Extracted {len(mapped_data)} fields from document")
            return mapped_data

        except Exception as e:
            logger.error(f"Field extraction failed: {e}")
            return {"error": str(e)}

    def validate_document(self, extracted_fields: Dict, doc_code: str) -> Dict:
        """
        Validate that all mandatory fields are present

        Args:
            extracted_fields: Extracted field values
            doc_code: Document code

        Returns:
            Validation result with missing fields and compliance status
        """
        required_fields = self.get_required_fields(doc_code)
        mandatory_fields = required_fields['mandatory']

        missing_mandatory = []
        present_mandatory = []

        for field in mandatory_fields:
            field_name = field['name']
            # Check if field exists in extracted data and has a non-null value
            if field_name in extracted_fields and extracted_fields[field_name].get('value') is not None:
                present_mandatory.append(field)
            else:
                missing_mandatory.append(field)

        compliance_score = 0
        if len(mandatory_fields) > 0:
            compliance_score = int((len(present_mandatory) / len(mandatory_fields)) * 100)

        validation_result = {
            "is_compliant": len(missing_mandatory) == 0,
            "compliance_score": compliance_score,
            "mandatory_fields_count": len(mandatory_fields),
            "present_fields_count": len(present_mandatory),
            "missing_mandatory_fields": [
                {
                    "uid": field['uid'],
                    "name": field['name'],
                    "description": field['description']
                }
                for field in missing_mandatory
            ],
            "warnings": []
        }

        # Add warnings for missing conditional fields
        conditional_fields = required_fields['conditional']
        for field in conditional_fields:
            field_name = field['name']
            if field_name not in extracted_fields or extracted_fields[field_name].get('value') is None:
                validation_result['warnings'].append(
                    f"Conditional field '{field['name']}' is missing - may be required depending on context"
                )

        logger.info(f"Validation complete: Compliance score {compliance_score}%, "
                   f"{len(missing_mandatory)} missing mandatory fields")

        return validation_result

    def process_document(self, ocr_text: str, doc_code: Optional[str] = None) -> Dict:
        """
        Complete document processing: classify, extract, and validate

        Args:
            ocr_text: Extracted text from document
            doc_code: Optional document code if already known

        Returns:
            Complete processing result
        """
        result = {
            "classification": None,
            "extraction": None,
            "validation": None,
            "status": "success"
        }

        try:
            # Step 1: Classify if doc_code not provided
            if not doc_code:
                logger.info("Step 1: Classifying document...")
                classification = self.classify_document(ocr_text)
                result["classification"] = classification
                doc_code = classification.get("code")

                if not doc_code or doc_code == "UNK":
                    result["status"] = "classification_failed"
                    return result
            else:
                result["classification"] = {
                    "code": doc_code,
                    "method": "provided"
                }

            # Step 2: Extract fields
            logger.info(f"Step 2: Extracting fields for document type {doc_code}...")
            extraction = self.extract_fields(ocr_text, doc_code)
            result["extraction"] = extraction

            if "error" in extraction:
                result["status"] = "extraction_failed"
                return result

            # Step 3: Validate
            logger.info("Step 3: Validating extracted fields...")
            validation = self.validate_document(extraction, doc_code)
            result["validation"] = validation

            # Set overall status
            if not validation["is_compliant"]:
                result["status"] = "validation_incomplete"

            return result

        except Exception as e:
            logger.error(f"Document processing failed: {e}")
            result["status"] = "error"
            result["error"] = str(e)
            return result

    def get_form_mapping(self, doc_code: str, form_type: str) -> Dict:
        """
        Map UNTDED fields to form field names

        Args:
            doc_code: Document code (e.g., 'LC')
            form_type: Form type (e.g., 'import_lc', 'bank_guarantee')

        Returns:
            Field mapping dictionary
        """
        # Define common mappings between UNTDED UIDs and form fields
        mappings = {
            "LC": {
                "import_lc": {
                    "1004": "lcNumber",
                    "1172": "lcNumber",
                    "2007": "issueDate",
                    "2211": "expiryDate",
                    "2237": "issueDate",
                    "3002": "applicant",
                    "3260": "beneficiary",
                    "3198": "applicant",
                    "5450": "amount",
                    "5444": "amount",
                    "3012": "issuingBank",
                    "3420": "issuingBank",
                    "3234": "advisingBank",
                    "3242": "advisingBank",
                    "3000": "finalDestination",
                    "3099": "portOfLoading",
                    "3356": "portOfDischarge",
                    "3238": "goodsDescription",
                    "7002": "goodsDescription",
                    "4277": "paymentTerms"
                }
            },
            "INV": {
                "commercial_invoice": {
                    "1334": "invoiceNumber",
                    "2377": "invoiceDate",
                    "3002": "buyer",
                    "3346": "seller",
                    "5444": "totalAmount",
                    "7002": "goodsDescription",
                    "3238": "originCountry",
                    "4052": "incoterms"
                }
            },
            "BoL": {
                "bill_of_lading": {
                    "1188": "blNumber",
                    "2007": "issueDate",
                    "3336": "consignor",
                    "3132": "consignee",
                    "3126": "carrier",
                    "3099": "portOfLoading",
                    "3356": "portOfDischarge",
                    "7002": "cargoDescription",
                    "6012": "grossWeight"
                }
            },
            "BG": {  # Bank Guarantee
                "bank_guarantee": {
                    "1004": "guaranteeNumber",
                    "2007": "issueDate",
                    "2211": "expiryDate",
                    "3002": "applicant",
                    "3260": "beneficiary",
                    "5004": "amount",
                    "3012": "issuingBank",
                    "3220": "originCountry",
                    "4277": "paymentTerms"
                }
            }
        }

        return mappings.get(doc_code, {}).get(form_type, {})

    def map_to_form_fields(self, extracted_fields: Dict, doc_code: str, form_type: str) -> Dict:
        """
        Map extracted UNTDED fields to form field names

        Args:
            extracted_fields: Extracted fields with UIDs
            doc_code: Document code
            form_type: Target form type

        Returns:
            Dictionary with form field names as keys
        """
        mapping = self.get_form_mapping(doc_code, form_type)
        form_data = {}

        for field_name, field_data in extracted_fields.items():
            uid = field_data.get('uid')
            value = field_data.get('value')

            if uid in mapping and value is not None:
                form_field_name = mapping[uid]
                form_data[form_field_name] = value

        logger.info(f"Mapped {len(form_data)} fields to form {form_type}")
        return form_data
