"""
Standalone test for LLM functions - uses Flask app context to avoid import issues.
"""

import sys
import os

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Initialize Flask app first
from app import app

with app.app_context():
    from app.routes import _check_document_alias, _llm_map_uploaded_to_required

    # Test cases for _check_document_alias
    print("\n" + "="*80)
    print("LLM-Driven Alias Testing")
    print("="*80)

    alias_tests = [
        ('Commercial Invoice', 'Invoice', 'alias - should match'),
        ('Bill of Lading', 'B/L', 'alias - abbreviation'),
        ('Packing List', 'Packing Slip', 'alias - similar'),
        ('Certificate of Origin', 'Origin Certificate', 'alias - reversed'),
        ('Commercial Invoice', 'Unknown Random', 'no match'),
    ]

    print("\n1. Testing _check_document_alias:")
    for req, upl, desc in alias_tests:
        try:
            result = _check_document_alias(req, upl)
            print(f"   ✅ '{req}' vs '{upl}': {result} ({desc})")
        except Exception as e:
            print(f"   ❌ '{req}' vs '{upl}': ERROR - {str(e)[:100]}")

    # Test cases for _llm_map_uploaded_to_required
    print("\n2. Testing _llm_map_uploaded_to_required:")

    required_docs = [
        {'name': 'Commercial Invoice'},
        {'name': 'Bill of Lading'},
        {'name': 'Packing List'},
        {'name': 'Certificate of Origin'}
    ]

    mapping_tests = [
        ('Invoice', 'should map to Commercial Invoice'),
        ('Shipment Manifest', 'should map to Bill of Lading or Packing List'),
        ('Certificate of Origin', 'should map to Certificate of Origin'),
        ('B/L', 'should map to Bill of Lading'),
    ]

    for uploaded, desc in mapping_tests:
        try:
            best_match, confidence, reason = _llm_map_uploaded_to_required(uploaded, required_docs)
            print(f"   ✅ Uploaded '{uploaded}':")
            print(f"      → Matched: '{best_match}' (confidence: {confidence:.2f})")
            print(f"      → Reason: {reason} ({desc})")
        except Exception as e:
            print(f"   ❌ Uploaded '{uploaded}': ERROR - {str(e)[:100]}")

    print("\n" + "="*80)
    print("Testing complete!")
    print("="*80)
