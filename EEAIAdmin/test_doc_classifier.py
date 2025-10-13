#!/usr/bin/env python3
"""Test the DocumentClassifier to ensure it loads fields correctly."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.utils.document_classifier import DocumentClassifier

def test_document_classifier():
    print("Testing DocumentClassifier...")
    classifier = DocumentClassifier()
    
    # Test various document types
    test_cases = [
        ("bill_of_entry", "EE", "register_import_lc"),
        ("Bill of Entry", "EE", "register_import_lc"),
        ("bill of entry", "EE", "register_import_lc"),
        ("letter_of_credit", "EE", "register_import_lc"),
        ("Letter of Credit", "EE", "register_import_lc"),
    ]
    
    print(f"\nLoaded {len(classifier.document_fields_cache)} document types in cache")
    print("Cache keys:", list(classifier.document_fields_cache.keys())[:5], "...")
    
    for doc_type, product, function in test_cases:
        print(f"\nTesting: {doc_type}")
        fields, definitions = classifier.get_document_fields(doc_type, product, function)
        print(f"  Found {len(fields)} fields")
        if fields:
            print(f"  Sample fields: {fields[:3]}...")
        else:
            print(f"  WARNING: No fields found!")

if __name__ == "__main__":
    test_document_classifier()