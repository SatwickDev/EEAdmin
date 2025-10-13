#!/usr/bin/env python3
"""
Simple test for document classifier field loading functionality
"""
import json
import os
import sys

def test_field_loading():
    # Test loading function fields
    function_fields_path = "/mnt/c/Users/AIAdmin/Desktop/EEAI/app/utils/prompts/EE/function_fields.json"
    
    print("="*80)
    print("TESTING FUNCTION FIELDS LOADING")
    print("="*80)
    
    with open(function_fields_path, 'r') as f:
        function_fields = json.load(f)
    
    for product in function_fields:
        print(f"\nProduct: {product}")
        print("-" * 40)
        for function_name, fields in function_fields[product].items():
            print(f"\n  Function: {function_name}")
            print(f"  Number of fields: {len(fields)}")
            # Show first 3 fields
            for i, (field, desc) in enumerate(list(fields.items())[:3]):
                print(f"    {i+1}. {field}: {desc}")
            if len(fields) > 3:
                print(f"    ... and {len(fields) - 3} more fields")

def test_doc_list_loading():
    doc_list_path = "/mnt/c/Users/AIAdmin/Desktop/EEAI/app/utils/prompts/EE/DOC_LIST"
    
    print("\n" + "="*80)
    print("TESTING DOC_LIST LOADING")
    print("="*80)
    
    for filename in sorted(os.listdir(doc_list_path))[:5]:  # Test first 5 files
        if filename.endswith("_OCR_Fields.json"):
            doc_type = filename.replace("_OCR_Fields.json", "")
            filepath = os.path.join(doc_list_path, filename)
            
            print(f"\nDocument Type: {doc_type}")
            print("-" * 40)
            
            with open(filepath, 'r') as f:
                doc_fields = json.load(f)
            
            # Count total fields
            total_fields = 0
            categories = []
            
            for main_category, subcategories in doc_fields.items():
                if isinstance(subcategories, dict):
                    for subcategory, fields in subcategories.items():
                        categories.append(subcategory)
                        if isinstance(fields, list):
                            total_fields += len(fields)
                        elif isinstance(fields, dict):
                            total_fields += len(fields)
                elif isinstance(subcategories, list):
                    total_fields += len(subcategories)
            
            print(f"  Total fields: {total_fields}")
            print(f"  Categories: {', '.join(categories[:3])}")
            if len(categories) > 3:
                print(f"  ... and {len(categories) - 3} more categories")

def demonstrate_usage():
    print("\n" + "="*80)
    print("USAGE DEMONSTRATION")
    print("="*80)
    
    print("""
The enhanced document classification system works as follows:

1. **Document Classification (using GPT)**:
   - Analyzes OCR text to identify document category and type
   - Returns structured classification with confidence score
   - Example: classify_document_gpt(ocr_text) returns:
     {
       "category": "Transactional Document",
       "document_type": "Letter of Credit",
       "sub_type": "Import LC",
       "confidence": 95
     }

2. **Dynamic Field Loading**:
   - Based on document type, loads appropriate fields from:
     a) function_fields.json (if product/function specified)
     b) DOC_LIST/{document_type}_OCR_Fields.json (otherwise)
   
3. **Integration in process_page_with_llm_analysis**:
   - Classifies document using enhanced classifier
   - Loads relevant fields dynamically
   - Passes fields to LLM for extraction
   - Ensures comprehensive field coverage

Benefits:
- Supports all 27 document types in DOC_LIST
- Function-specific field extraction for EE/CE products
- Better accuracy through GPT-based classification
- Scalable to new document types
""")

if __name__ == "__main__":
    try:
        print("Starting document classifier field loading tests...\n")
        test_field_loading()
        test_doc_list_loading()
        demonstrate_usage()
        print("\n✅ All tests completed successfully!")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()