"""
Field Filter - Filter extracted fields by type

This module provides filtering logic for extracted fields based on their type:
- Mandatory fields: Always included (even if empty)
- Optional/Conditional fields: Only included if they have actual values
"""

import logging
from typing import Dict

logger = logging.getLogger(__name__)


def filter_extracted_fields_by_type(extracted_fields: Dict, entity_info: Dict) -> Dict:
    """
    Filter extracted fields based on field type:
    - Mandatory fields: Always include (even if empty)
    - Optional/Conditional fields: Only include if they have actual values
    
    Args:
        extracted_fields: Dictionary of extracted field data
        entity_info: Dictionary with mandatory_fields, optional_fields, conditional_fields
        
    Returns:
        Filtered dictionary of extracted fields
    """
    if not extracted_fields or not entity_info:
        return extracted_fields
        
    # Create sets of field names by type for efficient lookup
    mandatory_field_names = {field['entityName'].lower() for field in entity_info.get('mandatory_fields', [])}
    optional_field_names = {field['entityName'].lower() for field in entity_info.get('optional_fields', [])}
    conditional_field_names = {field['entityName'].lower() for field in entity_info.get('conditional_fields', [])}
    
    filtered_fields = {}
    
    for field_name, field_data in extracted_fields.items():
        field_name_lower = field_name.lower()
        field_value = field_data.get('value', '') if isinstance(field_data, dict) else str(field_data)
        
        # Check if field has actual content (not empty/null/whitespace)
        has_value = field_value and str(field_value).strip() and str(field_value).strip() not in ['', 'null', 'None', 'N/A', '-']
        
        # Always include mandatory fields (even if empty)
        if field_name_lower in mandatory_field_names:
            filtered_fields[field_name] = field_data
            
        # Only include optional/conditional fields if they have values
        elif (field_name_lower in optional_field_names or field_name_lower in conditional_field_names):
            if has_value:
                filtered_fields[field_name] = field_data
            else:
                logger.debug(f"🚫 Filtered out empty optional/conditional field: {field_name}")
                
        # Include unmatched fields if they have values (fallback)
        else:
            if has_value:
                filtered_fields[field_name] = field_data
                
    logger.info(f"📋 Field filtering: {len(extracted_fields)} → {len(filtered_fields)} fields (removed {len(extracted_fields) - len(filtered_fields)} empty optional fields)")
    return filtered_fields
