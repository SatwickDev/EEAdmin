#!/usr/bin/env python3
"""
Script to analyze JSON files in the DOC_LIST directory and validate their structure.
Expected structure: root key -> categories -> field arrays
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Tuple, Any

def check_json_structure(file_path: Path) -> Tuple[bool, str, str]:
    """
    Check if a JSON file follows the expected structure.
    Returns: (is_valid, root_key, error_message)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return False, "", f"JSON decode error: {str(e)}"
    except Exception as e:
        return False, "", f"Error reading file: {str(e)}"
    
    # Check if it's a dictionary
    if not isinstance(data, dict):
        return False, "", "Root element is not a dictionary"
    
    # Check if there's exactly one root key
    if len(data) != 1:
        return False, "", f"Expected 1 root key, found {len(data)}"
    
    root_key = list(data.keys())[0]
    root_value = data[root_key]
    
    # Check if root value is a dictionary (categories)
    if not isinstance(root_value, dict):
        return False, root_key, "Root value is not a dictionary of categories"
    
    # Check each category
    for category_name, fields in root_value.items():
        if not isinstance(fields, list):
            return False, root_key, f"Category '{category_name}' is not a list of fields"
        
        # Check if all items in the list are strings
        for i, field in enumerate(fields):
            if not isinstance(field, str):
                # Provide more detail about the actual type
                field_type = type(field).__name__
                field_preview = str(field)[:50] + "..." if len(str(field)) > 50 else str(field)
                return False, root_key, f"Field {i} in category '{category_name}' is not a string (found {field_type}: {field_preview})"
    
    return True, root_key, ""

def main():
    # Directory containing JSON files
    doc_list_dir = Path("/mnt/c/Users/AIAdmin/Desktop/EEAI/app/utils/prompts/EE/DOC_LIST")
    
    if not doc_list_dir.exists():
        print(f"Error: Directory does not exist: {doc_list_dir}")
        return
    
    # Get all JSON files
    json_files = list(doc_list_dir.glob("*.json"))
    
    if not json_files:
        print(f"No JSON files found in {doc_list_dir}")
        return
    
    print(f"Found {len(json_files)} JSON files to analyze\n")
    print("=" * 80)
    
    # Track results
    valid_files = []
    invalid_files = []
    root_keys = {}  # filename -> root_key mapping
    
    # Check each file
    for json_file in sorted(json_files):
        is_valid, root_key, error_msg = check_json_structure(json_file)
        
        if is_valid:
            valid_files.append(json_file.name)
            root_keys[json_file.name] = root_key
        else:
            invalid_files.append((json_file.name, error_msg))
            if root_key:  # If we got a root key before the error
                root_keys[json_file.name] = root_key
    
    # Report invalid files
    if invalid_files:
        print("\n❌ FILES WITH INVALID STRUCTURE:")
        print("-" * 40)
        for filename, error in invalid_files:
            print(f"  • {filename}")
            print(f"    Error: {error}")
    else:
        print("\n✓ All files have valid structure!")
    
    # Report valid files count
    print(f"\n📊 SUMMARY:")
    print(f"  • Valid files: {len(valid_files)}")
    print(f"  • Invalid files: {len(invalid_files)}")
    
    # List all root keys for consistency check
    print("\n🔑 ROOT KEYS BY FILE:")
    print("-" * 40)
    
    # Group files by root key pattern
    key_patterns = {}
    for filename, root_key in sorted(root_keys.items()):
        # Extract pattern from filename (remove _OCR_Fields.json)
        expected_key = filename.replace("_OCR_Fields.json", "").replace("_", " ")
        
        print(f"  • {filename:<40} → {root_key}")
        
        # Check if root key matches expected pattern
        if root_key.lower() != expected_key.lower():
            if root_key not in key_patterns:
                key_patterns[root_key] = []
            key_patterns[root_key].append((filename, expected_key))
    
    # Check naming consistency
    print("\n🔍 NAMING CONSISTENCY CHECK:")
    print("-" * 40)
    
    naming_issues = []
    for filename, root_key in root_keys.items():
        # Expected root key based on filename
        expected_key = filename.replace("_OCR_Fields.json", "").replace("_", " ")
        
        if root_key != expected_key:
            naming_issues.append((filename, root_key, expected_key))
    
    if naming_issues:
        print("  ⚠️  Inconsistent naming found:")
        for filename, actual, expected in naming_issues:
            print(f"    • {filename}")
            print(f"      Actual:   '{actual}'")
            print(f"      Expected: '{expected}'")
    else:
        print("  ✓ All files have consistent naming!")
    
    # Additional statistics
    print("\n📈 ADDITIONAL STATISTICS:")
    print("-" * 40)
    
    if valid_files:
        # Count categories and fields
        total_categories = 0
        total_fields = 0
        
        for json_file in sorted(doc_list_dir.glob("*.json")):
            if json_file.name in valid_files:
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        root_value = data[list(data.keys())[0]]
                        categories = len(root_value)
                        fields = sum(len(fields_list) for fields_list in root_value.values())
                        total_categories += categories
                        total_fields += fields
                        print(f"  • {json_file.name}: {categories} categories, {fields} fields")
                except:
                    pass
        
        print(f"\n  Total across all valid files:")
        print(f"    • Categories: {total_categories}")
        print(f"    • Fields: {total_fields}")
        print(f"    • Average categories per file: {total_categories / len(valid_files):.1f}")
        print(f"    • Average fields per file: {total_fields / len(valid_files):.1f}")

if __name__ == "__main__":
    main()