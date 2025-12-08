"""
Field Mappings - Document field mapping loader for prompt enhancement

This module loads field mappings from document_entities/*.json files
to enhance extraction prompts with field structure information.
"""

import json
import logging
import os
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)


def load_document_field_mappings(document_type: str) -> Optional[Dict[str, Any]]:
    """
    Load field mappings for a specific document type from data/document_entities/*.json
    Returns formatted field example for the prompt with ALL fields included
    
    Args:
        document_type: The document type to load mappings for (e.g., "Commercial Invoice")
        
    Returns:
        Dictionary with 'example' text and 'mappings' list, or None if not found
    """
    try:
        logger.info(f"")
        logger.info(f"{'='*100}")
        logger.info(f"🔧 STEP 2: OPTIONAL ENTITY ENHANCEMENT (Field Examples from document_entities/*.json)")
        logger.info(f"{'='*100}")
        logger.info(f"📄 Document Type: {document_type}")
        
        # Normalize document type to match filename format (e.g., "Commercial Invoice" -> "Commercial_Invoice")
        doc_type_normalized = document_type.replace(' ', '_').replace('-', '_')
        logger.info(f"📝 Normalized Type: {doc_type_normalized}")

        # Try to load the document entity JSON file
        entity_file_path = os.path.join('data', 'document_entities', f'{doc_type_normalized}.json')
        logger.info(f"📁 Looking for enhancement file: {entity_file_path}")
        logger.info(f"📂 Absolute Path: {os.path.abspath(entity_file_path)}")

        if not os.path.exists(entity_file_path):
            logger.warning(f"⚠️ Enhancement file NOT FOUND: {entity_file_path}")
            logger.info(f"ℹ️ Proceeding WITHOUT optional field examples (using only primary entity definitions)")
            logger.info(f"{'='*100}")
            logger.info(f"")
            return None

        logger.info(f"✅ Enhancement file found, loading field examples...")
        with open(entity_file_path, 'r', encoding='utf-8') as f:
            entity_data = json.load(f)
        
        logger.info(f"📊 File loaded successfully, size: {len(json.dumps(entity_data))} characters")

        if 'mappings' not in entity_data:
            logger.warning(f"⚠️ No 'mappings' key found in enhancement file")
            logger.info(f"{'='*100}")
            logger.info(f"")
            return None

        mappings_count = len(entity_data.get('mappings', []))
        logger.info(f"📋 Total mapping entries in file: {mappings_count}")

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

        # Log field breakdown
        total_fields = len(mandatory_fields) + len(optional_fields) + len(conditional_fields)
        logger.info(f"📊 Field Examples Breakdown:")
        logger.info(f"   ✅ Mandatory: {len(mandatory_fields)}")
        logger.info(f"   🔸 Optional: {len(optional_fields)}")
        logger.info(f"   🔶 Conditional: {len(conditional_fields)}")
        logger.info(f"   📋 Total: {total_fields}")
        
        # Log all field names for transparency
        if mandatory_fields:
            logger.info(f"   ✅ Mandatory field examples: {', '.join([f['name'] for f in mandatory_fields])}")
        if optional_fields:
            logger.info(f"   🔸 Optional field examples: {', '.join([f['name'] for f in optional_fields])}")
        if conditional_fields:
            logger.info(f"   🔶 Conditional field examples: {', '.join([f['name'] for f in conditional_fields])}")

        # Format as comprehensive field structure - SHOW ALL FIELDS (no limits)
        example = f"\n{'='*80}\n"
        doc_name = entity_data.get('documentName', document_type).upper()
        example += f"STRUCTURE: COMPLETE FIELD STRUCTURE FOR: {doc_name}\n"
        example += f"{'='*80}\n"
        example += f"Total Fields: {len(mandatory_fields)} Mandatory + {len(optional_fields)} Optional + {len(conditional_fields)} Conditional\n"
        example += f"{'='*80}\n"

        if mandatory_fields:
            mandatory_count = len(mandatory_fields)
            example += f"\nMANDATORY FIELDS ({mandatory_count}) - MUST EXTRACT:\n"
            for idx, field in enumerate(mandatory_fields, 1):
                example += f"  {idx}. {field['name']} (Category: {field['category']})\n"

        if optional_fields:
            optional_count = len(optional_fields)
            example += f"\nOPTIONAL FIELDS ({optional_count}) - Extract if present:\n"
            for idx, field in enumerate(optional_fields, 1):
                example += f"  {idx}. {field['name']} (Category: {field['category']})\n"

        if conditional_fields:
            conditional_count = len(conditional_fields)
            example += f"\nCONDITIONAL FIELDS ({conditional_count}) - Extract if applicable:\n"
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

        m_count = len(mandatory_fields)
        o_count = len(optional_fields)
        c_count = len(conditional_fields)
        mapping_info = f"{m_count}M, {o_count}O, {c_count}C"
        logger.info(f"SUCCESS: Loaded ALL field mappings for {document_type}: {mapping_info}")
        
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
