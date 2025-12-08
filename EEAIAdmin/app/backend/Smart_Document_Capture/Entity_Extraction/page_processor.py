"""
Page Processor - Process pages with LLM analysis for entity extraction

This module handles the complete page processing workflow:
1. Document Classification
2. Entity field loading from mappings
3. Prompt building with field definitions
4. LLM-based extraction (single or chunk-based)
5. Field filtering and validation
"""

import json
import logging
from typing import Dict, Any, List, Optional

import openai

from app.utils.app_config import deployment_name
from app.backend.Smart_Document_Capture.Document_Classification import DocumentClassifier
from .helpers import parse_json_from_llm_response, load_prompt_config, calculate_text_token_count, format_ocr_data_for_llm_prompt
from .extraction_service import extract_entities_in_chunks
from .field_filter import filter_extracted_fields_by_type
from .field_mappings import load_document_field_mappings

logger = logging.getLogger(__name__)

# Global prompt config - loaded on first use
prompt_config = None

# Module-level singleton instance of DocumentClassifier
_document_classifier_instance = None

def get_document_classifier():
    """Get or create the singleton DocumentClassifier instance."""
    global _document_classifier_instance
    if _document_classifier_instance is None:
        _document_classifier_instance = DocumentClassifier()
        logger.info("✅ Created DocumentClassifier instance for page processor")
    return _document_classifier_instance


def process_page_with_llm_analysis(
    page_number: int,
    page_ocr_data: List[Dict],
    userQuery: str,
    annotations: Any,
    productName: str,
    functionName: str,
    documentType: Optional[str] = None
) -> Dict[str, Any]:
    """
    Process a page with LLM analysis for entity extraction.
    
    Args:
        page_number: Page number being processed
        page_ocr_data: OCR data for the page (list of word entries)
        userQuery: User's query string
        annotations: Page annotations (if any)
        productName: Product name context
        functionName: Function name context
        documentType: Optional pre-determined document type
        
    Returns:
        Dictionary with extracted fields and metadata
    """
    global prompt_config  # Declare at function start to avoid SyntaxError

    logger.info(f"=== Starting process_page_with_llm_analysis for page {page_number} ===")
    logger.info(f"UserQuery: {userQuery}, Product: {productName}, Function: {functionName}, DocumentType: {documentType}")

    # Load prompt configuration at the beginning
    if not prompt_config:
        prompt_config = load_prompt_config()
        if prompt_config:
            logger.info(f"SUCCESS:Loaded prompt configuration from YAML")

    page_text = " ".join([entry["text"] for entry in page_ocr_data])
    token_count = calculate_text_token_count(page_text)
    logger.info(f"Page {page_number} token count: {token_count}")

    ocr_text = format_ocr_data_for_llm_prompt(page_ocr_data)

    # Get DocumentClassifier instance for this function
    classifier = get_document_classifier()

    # STEP 1: Document Classification (EXISTING LOGIC)
    logger.info(f"Calling classifier.classify_document for page {page_number}")
    logger.info(f"Current OpenAI config before classification - API Base: {openai.api_base}, Key exists: {bool(openai.api_key)}")

    classification_result = classifier.classify_document(page_text)

    logger.info(f"Classification result for page {page_number}: {classification_result}")
    document_type = classification_result.get("document_type", "unknown")

    # Override with user query if provided
    if userQuery and userQuery.lower() in ["letter_of_credit", "invoice", "export_collection", "bank_guarantee"]:
        document_type = userQuery.lower()

    # Use provided documentType if available (this takes highest priority)
    if documentType:
        document_type = documentType
        logger.info(f" Using explicitly provided document type: {documentType}")

    # STEP 2: Map classified document type to UN/CEFACT code
    uncefact_code = _map_document_type_to_uncefact_code(document_type)

    if uncefact_code:
        logger.info(f"Mapped '{document_type}' → UN/CEFACT code: '{uncefact_code}'")
    else:
        logger.info(f"No UN/CEFACT mapping found for document type: '{document_type}'")

    # STEP 3: Get fields from entity_mappings (document_entity_maintenance.json)
    doc_type_normalized = classification_result.get("document_type", "").replace(" ", "_")
    if not doc_type_normalized:
        doc_type_normalized = document_type.replace(" ", "_")

    logger.info(f" Getting entity fields for: {doc_type_normalized}")
    entity_info = classifier.get_enhanced_entity_fields(doc_type_normalized)

    field_list = []
    field_definitions = {}

    # Build field list from entity mappings with enhanced descriptions
    for field in entity_info['mandatory_fields']:
        field_name = field['entityName']
        field_desc = field.get('description', '')
        field_list.append(field_name)
        if field_desc:
            field_definitions[field_name] = f"{field_name} (Mandatory) - {field_desc}"
        else:
            field_definitions[field_name] = f"{field_name} (Mandatory)"

    for field in entity_info['optional_fields']:
        field_name = field['entityName']
        field_desc = field.get('description', '')
        field_list.append(field_name)
        if field_desc:
            field_definitions[field_name] = f"{field_name} (Optional) - {field_desc}"
        else:
            field_definitions[field_name] = f"{field_name} (Optional)"

    for field in entity_info['conditional_fields']:
        field_name = field['entityName']
        field_desc = field.get('description', '')
        field_list.append(field_name)
        if field_desc:
            field_definitions[field_name] = f"{field_name} (Conditional) - {field_desc}"
        else:
            field_definitions[field_name] = f"{field_name} (Conditional)"

    logger.info(f"SUCCESS:Using entity_mappings with descriptions: {len(field_list)} fields ({len(entity_info['mandatory_fields'])} mandatory, {len(entity_info['optional_fields'])} optional, {len(entity_info['conditional_fields'])} conditional)")

    # Log sample field with description for verification
    if field_list:
        sample_field_name = field_list[0]
        sample_field_def = field_definitions.get(sample_field_name, '')
        logger.info(f"ANALYTICS: Sample field with description: {sample_field_def}")

    # Store for later use
    trade_doc_fields = {
        'mandatory': entity_info['mandatory_fields'],
        'optional': entity_info['optional_fields'],
        'conditional': entity_info['conditional_fields']
    }

    try:
        # Use DocumentClassifier to build extraction prompt from config and entity_mappings
        logger.info(f"")
        logger.info(f"{'='*100}")
        logger.info(f"🔍 STEP 1: PRIMARY ENTITY DEFINITION (from document_entity_maintenance.json)")
        logger.info(f"{'='*100}")
        logger.info(f"📄 Document Type: {document_type}")
        logger.info(f"📝 Page Number: {page_number}")
        logger.info(f"🏗️ Building extraction prompt using DocumentClassifier...")
        
        prompt = classifier.build_extraction_prompt(
            document_type=document_type,
            ocr_text=page_text,
            page_number=page_number
        )
        
        logger.info(f"✅ STEP 1 COMPLETE: Extraction prompt built successfully from primary entity definitions")
        logger.info(f"📊 Primary Prompt Length: {len(prompt)} characters")
        logger.info(f"📋 PRIMARY EXTRACTION PROMPT (COMPLETE - NO TRUNCATION):\n{prompt}")
        logger.info(f"{'='*100}")
        logger.info(f"")

        # === ENHANCEMENT: Add field mapping examples from document_entities ===
        original_prompt_length = len(prompt)
        field_mapping_example = load_document_field_mappings(document_type)
        
        if field_mapping_example:
            prompt += f"\n\n{field_mapping_example}"
            enhancement_length = len(str(field_mapping_example))
            logger.info(f"")
            logger.info(f"{'='*100}")
            logger.info(f"🔗 PROMPT ENHANCEMENT: Combining Step 1 + Step 2")
            logger.info(f"{'='*100}")
            logger.info(f"📊 Original Prompt (Step 1): {original_prompt_length} characters")
            logger.info(f"➕ Enhancement Text (Step 2): {enhancement_length} characters")
            logger.info(f"📋 Combined Prompt Total: {len(prompt)} characters")
            logger.info(f"✅ Prompt enhanced with field mapping examples for {document_type}")
            logger.info(f"📋 FINAL COMBINED PROMPT (COMPLETE - NO TRUNCATION):\n{prompt}")
            logger.info(f"{'='*100}")
            logger.info(f"")
        else:
            logger.info(f"")
            logger.info(f"{'='*100}")
            logger.info(f"ℹ️ NO ENHANCEMENT: Using only Step 1 (primary entity definitions)")
            logger.info(f"{'='*100}")
            logger.info(f"📊 Final Prompt Length: {len(prompt)} characters (no enhancement added)")
            logger.info(f"📋 FINAL PROMPT (COMPLETE - NO TRUNCATION):\n{prompt}")
            logger.info(f"{'='*100}")
            logger.info(f"")

        # Fallback if build_extraction_prompt fails
        if not prompt:
            logger.error("ERROR: Failed to build extraction prompt from DocumentClassifier, using basic fallback")
            prompt = f"Extract fields from this {document_type} document:\n\n{page_text}"

        # Get model settings from config (with fallback to defaults)
        temperature = 0.0
        model = deployment_name
        if prompt_config:
            temperature = prompt_config.get('extraction', {}).get('temperature', 0.0)
            model = prompt_config.get('extraction', {}).get('model', deployment_name)

        logger.info(f"PARAMETERS: Using extraction config - Model: {model}, Temperature: {temperature}")

        # Check if parallel extraction is enabled
        extraction_config = prompt_config.get('extraction', {}) if prompt_config else {}
        enable_parallel = extraction_config.get('enable_parallel_extraction', False)
        parallel_attempts = extraction_config.get('parallel_extraction_attempts', 3)
        aggregation_strategy = extraction_config.get('aggregation_strategy', 'union')
        confidence_threshold = extraction_config.get('confidence_threshold', 70)

        if enable_parallel and parallel_attempts > 1:
            # ======= NEW: CHUNK-BASED EXTRACTION MODE =======
            logger.info(f"🧩 Chunk-based extraction ENABLED: Processing entities in logical chunks")

            # Use new chunk-based extraction instead of redundant parallel calls
            extraction_results = extract_entities_in_chunks(
                entity_info=entity_info,
                ocr_text=page_text,
                model=model if model else deployment_name,
                page_number=page_number,
                document_type=document_type
            )

            # Merge results from all chunks
            merged_results = {"extracted_fields": {}}
            total_fields_extracted = 0
            
            for result in extraction_results:
                if result and 'extracted_fields' in result:
                    merged_results["extracted_fields"].update(result["extracted_fields"])
                    total_fields_extracted += len(result["extracted_fields"])

            # ======= FILTER FIELDS BY TYPE: Keep mandatory always, optional/conditional only if they have values =======
            filtered_fields = filter_extracted_fields_by_type(
                extracted_fields=merged_results["extracted_fields"],
                entity_info=entity_info
            )
            merged_results["extracted_fields"] = filtered_fields

            # Set merged result as final parsed_json
            parsed_json = merged_results
            parsed_json["page_number"] = page_number
            parsed_json["confidence_score"] = 85  # Default confidence for chunk-based extraction
            
            # Add statistics (updated after filtering)
            parsed_json["mandatory_fields_found"] = sum(1 for field_name in parsed_json["extracted_fields"].keys() 
                                                     if any(field_name.lower() == mf['entityName'].lower() 
                                                           for mf in entity_info['mandatory_fields']))
            parsed_json["total_mandatory_fields"] = len(entity_info['mandatory_fields'])
            parsed_json["total_fields_extracted"] = len(filtered_fields)  # Updated count after filtering
            parsed_json["extraction_method"] = "chunk_based"

            logger.info(f"✅ Chunk-based extraction successful: {len(filtered_fields)} filtered fields from {len(extraction_results)} chunks (was {total_fields_extracted} before filtering)")

            if not parsed_json or 'extracted_fields' not in parsed_json:
                logger.error("❌ Chunk-based extraction failed, no valid results")
                return {"page_number": page_number, "error": "Chunk-based extraction failed"}

        else:
            # ======= SINGLE EXTRACTION MODE (Original) =======
            logger.info(f"📤 Single extraction mode (parallel disabled or attempts=1)")

            # Send prompt to LLM (note: build_extraction_prompt already includes system prompt)
            response = openai.ChatCompletion.create(
                engine=model if model else deployment_name,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                seed=12345,  # ✅ Reproducibility
                top_p=0.1,  # ✅ NOT 1.0 (reduces randomness)
                frequency_penalty=0,
                presence_penalty=0,
                response_format={"type": "json_object"}
            )

            result = response["choices"][0]["message"]["content"].strip()
            parsed_json = parse_json_from_llm_response(result)
            if not parsed_json:
                return {"page_number": page_number, "error": "Invalid LLM response format"}

            # ======= FILTER FIELDS BY TYPE (Single Extraction) =======
            if parsed_json.get('extracted_fields') and entity_info:
                filtered_fields = filter_extracted_fields_by_type(
                    extracted_fields=parsed_json["extracted_fields"],
                    entity_info=entity_info
                )
                parsed_json["extracted_fields"] = filtered_fields
                logger.info(f"📋 Single extraction: Applied field filtering (mandatory always shown, optional/conditional only if populated)")

        # Enhanced logging for trade document field extraction
        if trade_doc_fields and parsed_json.get("extracted_fields"):
            extracted_field_names = list(parsed_json["extracted_fields"].keys())
            logger.info(f"ANALYTICS: Page {page_number} - Extracted {len(extracted_field_names)} fields from document")

            # Log mandatory fields that were found
            mandatory_found = [f['entityName'] for f in trade_doc_fields['mandatory']
                             if any(f['entityName'] in field or f['entityName'].lower().replace(' ', '_') in field.lower()
                                   for field in extracted_field_names)]
            if mandatory_found:
                logger.info(f"SUCCESS:Mandatory fields found: {', '.join(mandatory_found[:5])}{'...' if len(mandatory_found) > 5 else ''}")

            # Log optional fields that were found
            optional_found = [f['entityName'] for f in trade_doc_fields['optional']
                            if any(f['entityName'] in field or f['entityName'].lower().replace(' ', '_') in field.lower()
                                  for field in extracted_field_names)]
            if optional_found:
                logger.info(f"Optional fields found: {', '.join(optional_found[:5])}{'...' if len(optional_found) > 5 else ''}")

            # Log which mandatory fields are missing
            mandatory_missing = [f['entityName'] for f in trade_doc_fields['mandatory']
                               if not any(f['entityName'] in field or f['entityName'].lower().replace(' ', '_') in field.lower()
                                        for field in extracted_field_names)]
            if mandatory_missing:
                logger.warning(f"WARNINGS:  Missing mandatory fields: {', '.join(mandatory_missing[:5])}{'...' if len(mandatory_missing) > 5 else ''}")

        logger.info(f"Comprehensive analysis result for page {page_number}: {parsed_json}")
        return parsed_json

    except Exception as e:
        logger.error(f"Error analyzing page {page_number}: {e}")
        return {"page_number": page_number, "error": "Failed to analyze the page."}


def _map_document_type_to_uncefact_code(doc_type: str) -> Optional[str]:
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
