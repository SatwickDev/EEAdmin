#!/usr/bin/env python3
"""
Test script for the enhanced document classification system
"""
import json
import sys
import os

# Mock the deployment_name before imports
class MockConfig:
    deployment_name = "gpt-35-turbo"

sys.modules['app.utils.app_config'] = MockConfig()

sys.path.append('/mnt/c/Users/AIAdmin/Desktop/EEAI')

from app.utils.document_classifier import DocumentClassifier

def test_document_classification():
    classifier = DocumentClassifier()
    
    # Test samples
    test_documents = [
        {
            "name": "Letter of Credit",
            "text": """
            LETTER OF CREDIT
            LC Number: 12345ABC
            Date of Issue: 2024-01-15
            Issuing Bank: ABC Bank Ltd.
            Beneficiary: XYZ Corporation
            Amount: USD 100,000
            Expiry Date: 2024-06-30
            """
        },
        {
            "name": "Bank Guarantee",
            "text": """
            BANK GUARANTEE
            Guarantee Number: BG/2024/001
            We hereby issue our irrevocable guarantee for USD 50,000
            in favor of DEF Company as beneficiary
            Valid until: December 31, 2024
            Type: Performance Guarantee
            """
        },
        {
            "name": "Bill of Lading",
            "text": """
            BILL OF LADING
            B/L No: MOLU123456789
            Shipper: Global Exports Ltd
            Consignee: Import Solutions Inc
            Port of Loading: Shanghai
            Port of Discharge: Los Angeles
            Vessel: MV Ocean Star
            """
        },
        {
            "name": "Commercial Invoice",
            "text": """
            COMMERCIAL INVOICE
            Invoice No: INV-2024-001
            Date: January 15, 2024
            Seller: Manufacturing Co Ltd
            Buyer: Trading International
            Total Amount: USD 25,000
            Terms: FOB Shanghai
            """
        }
    ]
    
    print("="*80)
    print("TESTING DOCUMENT CLASSIFICATION")
    print("="*80)
    
    for doc in test_documents:
        print(f"\nTesting: {doc['name']}")
        print("-" * 40)
        
        # Classify document
        classification = classifier.classify_document(doc['text'])
        print(f"Classification Result:")
        print(json.dumps(classification, indent=2))
        
        # Get fields for the document type
        doc_type = classification.get('document_type', 'unknown')
        field_list, field_definitions = classifier.get_document_fields(doc_type)
        
        print(f"\nExtracted Field Definitions ({len(field_list)} fields):")
        if field_definitions:
            for i, (field, desc) in enumerate(list(field_definitions.items())[:5]):
                print(f"  {i+1}. {field}: {desc}")
            if len(field_definitions) > 5:
                print(f"  ... and {len(field_definitions) - 5} more fields")
        else:
            print("  No field definitions found")
        
        print("-" * 40)

def test_function_specific_fields():
    classifier = DocumentClassifier()
    
    print("\n" + "="*80)
    print("TESTING FUNCTION-SPECIFIC FIELD LOADING")
    print("="*80)
    
    test_cases = [
        ("EE", "register_import_lc"),
        ("EE", "issue_import_lc"),
        ("EE", "register_guarantee"),
        ("CE", "register_import_lc")
    ]
    
    for product, function in test_cases:
        print(f"\nProduct: {product}, Function: {function}")
        print("-" * 40)
        
        field_list, field_definitions = classifier.get_document_fields(
            "letter_of_credit", product, function
        )
        
        print(f"Found {len(field_list)} fields:")
        for i, (field, desc) in enumerate(list(field_definitions.items())[:5]):
            print(f"  {i+1}. {field}: {desc}")
        if len(field_definitions) > 5:
            print(f"  ... and {len(field_definitions) - 5} more fields")

if __name__ == "__main__":
    try:
        print("Starting document classifier tests...\n")
        test_document_classification()
        test_function_specific_fields()
        print("\n✅ All tests completed successfully!")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()