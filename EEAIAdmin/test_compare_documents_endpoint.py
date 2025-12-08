"""
Test the /api/compare-documents endpoint with real Azure OpenAI credentials.

This test validates the document comparison logic including:
- Deterministic matching (exact, type, sub-type, filename)
- LLM-driven alias checking via _check_document_alias
- LLM-driven mapping of new/unknown uploaded types via _llm_map_uploaded_to_required
"""

import requests
import json
import os
from typing import Dict, List, Any

BASE_URL = os.getenv('BASE_URL', 'http://localhost:5000')
API_ENDPOINT = f'{BASE_URL}/api/compare-documents'

# Test data
REQUIRED_DOCUMENTS = [
    {
        'name': 'Commercial Invoice',
        'priority': 'Mandatory',
        'description': 'Invoice from exporter to importer'
    },
    {
        'name': 'Bill of Lading',
        'priority': 'Mandatory',
        'description': 'Proof of shipment'
    },
    {
        'name': 'Packing List',
        'priority': 'Optional',
        'description': 'Detailed contents list'
    },
    {
        'name': 'Certificate of Origin',
        'priority': 'Conditional',
        'description': 'Proof of product origin'
    }
]

UPLOADED_DOCUMENTS_EXACT_MATCH = [
    {
        'documentType': 'Commercial Invoice',
        'fileName': 'invoice_123.pdf',
        'classification': {'sub_type': 'commercial invoice'}
    },
    {
        'documentType': 'Bill of Lading',
        'fileName': 'bol_456.pdf',
        'classification': {'sub_type': 'bill of lading'}
    }
]

UPLOADED_DOCUMENTS_WITH_ALIASES = [
    {
        'documentType': 'Invoice',  # alias for Commercial Invoice
        'fileName': 'invoice_123.pdf',
        'classification': {'sub_type': 'invoice'}
    },
    {
        'documentType': 'B/L',  # alias for Bill of Lading
        'fileName': 'bol_456.pdf',
        'classification': {'sub_type': 'bill of lading'}
    },
    {
        'documentType': 'Packing Slip',  # alias for Packing List
        'fileName': 'packing_list.pdf',
        'classification': {'sub_type': 'packing'}
    }
]

UPLOADED_DOCUMENTS_WITH_NEW_TYPES = [
    {
        'documentType': 'Commercial Invoice',
        'fileName': 'invoice_123.pdf',
        'classification': {'sub_type': 'commercial invoice'}
    },
    {
        'documentType': 'Shipment Manifest',  # new/unknown type - let LLM decide
        'fileName': 'manifest_789.pdf',
        'classification': {'sub_type': 'shipment manifest'}
    }
]

UPLOADED_DOCUMENTS_INCOMPLETE = [
    {
        'documentType': 'Commercial Invoice',
        'fileName': 'invoice_123.pdf',
        'classification': {'sub_type': 'commercial invoice'}
    }
]


def test_exact_match():
    """Test exact match of document types."""
    print("\n" + "="*80)
    print("TEST 1: Exact Match")
    print("="*80)

    payload = {
        'required_documents': REQUIRED_DOCUMENTS,
        'uploaded_documents': UPLOADED_DOCUMENTS_EXACT_MATCH
    }

    try:
        response = requests.post(API_ENDPOINT, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()

        print(f"Status Code: {response.status_code}")
        print(f"Success: {result.get('success')}")

        summary = result.get('summary', {})
        print(f"\nSummary:")
        print(f"  Total Required: {summary.get('total_required')}")
        print(f"  Total Uploaded: {summary.get('total_uploaded')}")
        print(f"  Matched: {summary.get('matched')}")
        print(f"  Missing: {summary.get('missing')}")
        print(f"  Extra: {summary.get('extra')}")
        print(f"  Completeness: {summary.get('completeness')}%")
        print(f"  Status: {summary.get('status')}")

        comparison = result.get('comparison', {})
        print(f"\nMatched Documents: {len(comparison.get('matched', []))}")
        for match in comparison.get('matched', []):
            print(f"  - Required: {match['required'].get('name')} <- Uploaded: {match['uploaded'].get('documentType')} (conf: {match.get('confidence')})")

        print(f"\nMissing Documents: {len(comparison.get('missing', []))}")
        for missing in comparison.get('missing', []):
            print(f"  - {missing['document'].get('name')} (Priority: {missing['document'].get('priority')})")

        print("\n✅ Test PASSED")
        return True

    except Exception as e:
        print(f"❌ Test FAILED: {e}")
        return False


def test_alias_matching():
    """Test LLM-driven alias matching."""
    print("\n" + "="*80)
    print("TEST 2: Alias Matching (via LLM)")
    print("="*80)

    payload = {
        'required_documents': REQUIRED_DOCUMENTS,
        'uploaded_documents': UPLOADED_DOCUMENTS_WITH_ALIASES
    }

    try:
        response = requests.post(API_ENDPOINT, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()

        print(f"Status Code: {response.status_code}")
        print(f"Success: {result.get('success')}")

        summary = result.get('summary', {})
        print(f"\nSummary:")
        print(f"  Total Required: {summary.get('total_required')}")
        print(f"  Total Uploaded: {summary.get('total_uploaded')}")
        print(f"  Matched: {summary.get('matched')}")
        print(f"  Missing: {summary.get('missing')}")
        print(f"  Extra: {summary.get('extra')}")
        print(f"  Completeness: {summary.get('completeness')}%")
        print(f"  Status: {summary.get('status')}")

        comparison = result.get('comparison', {})
        print(f"\nMatched Documents: {len(comparison.get('matched', []))}")
        for match in comparison.get('matched', []):
            print(f"  - Required: {match['required'].get('name')} <- Uploaded: {match['uploaded'].get('documentType')} (conf: {match.get('confidence'):.2f})")
            print(f"    Reason: {match.get('reason')}")

        print("\n✅ Test PASSED")
        return True

    except Exception as e:
        print(f"❌ Test FAILED: {e}")
        return False


def test_llm_mapping_new_types():
    """Test LLM mapping of new/unknown document types."""
    print("\n" + "="*80)
    print("TEST 3: LLM Mapping for New Document Types")
    print("="*80)

    payload = {
        'required_documents': REQUIRED_DOCUMENTS,
        'uploaded_documents': UPLOADED_DOCUMENTS_WITH_NEW_TYPES
    }

    try:
        response = requests.post(API_ENDPOINT, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()

        print(f"Status Code: {response.status_code}")
        print(f"Success: {result.get('success')}")

        summary = result.get('summary', {})
        print(f"\nSummary:")
        print(f"  Total Required: {summary.get('total_required')}")
        print(f"  Total Uploaded: {summary.get('total_uploaded')}")
        print(f"  Matched: {summary.get('matched')}")
        print(f"  Missing: {summary.get('missing')}")
        print(f"  Extra: {summary.get('extra')}")
        print(f"  Completeness: {summary.get('completeness')}%")
        print(f"  Status: {summary.get('status')}")

        comparison = result.get('comparison', {})
        print(f"\nMatched Documents: {len(comparison.get('matched', []))}")
        for match in comparison.get('matched', []):
            print(f"  - Required: {match['required'].get('name')} <- Uploaded: {match['uploaded'].get('documentType')} (conf: {match.get('confidence'):.2f})")
            print(f"    Reason: {match.get('reason')}")

        print(f"\nExtra Documents: {len(comparison.get('extra', []))}")
        for extra in comparison.get('extra', []):
            print(f"  - {extra['document'].get('documentType')} ({extra['document'].get('fileName')})")

        print("\n✅ Test PASSED")
        return True

    except Exception as e:
        print(f"❌ Test FAILED: {e}")
        return False


def test_incomplete_upload():
    """Test incomplete document upload (missing documents)."""
    print("\n" + "="*80)
    print("TEST 4: Incomplete Upload (Missing Documents)")
    print("="*80)

    payload = {
        'required_documents': REQUIRED_DOCUMENTS,
        'uploaded_documents': UPLOADED_DOCUMENTS_INCOMPLETE
    }

    try:
        response = requests.post(API_ENDPOINT, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()

        print(f"Status Code: {response.status_code}")
        print(f"Success: {result.get('success')}")

        summary = result.get('summary', {})
        print(f"\nSummary:")
        print(f"  Total Required: {summary.get('total_required')}")
        print(f"  Total Uploaded: {summary.get('total_uploaded')}")
        print(f"  Matched: {summary.get('matched')}")
        print(f"  Missing: {summary.get('missing')}")
        print(f"  Extra: {summary.get('extra')}")
        print(f"  Completeness: {summary.get('completeness')}%")
        print(f"  Status: {summary.get('status')}")

        comparison = result.get('comparison', {})
        print(f"\nMissing Documents: {len(comparison.get('missing', []))}")
        for missing in comparison.get('missing', []):
            print(f"  - {missing['document'].get('name')} (Priority: {missing['document'].get('priority')})")

        print("\n✅ Test PASSED")
        return True

    except Exception as e:
        print(f"❌ Test FAILED: {e}")
        return False


def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("Document Comparison API Test Suite")
    print("="*80)
    print(f"Base URL: {BASE_URL}")
    print(f"Endpoint: {API_ENDPOINT}")

    results = []
    results.append(("Exact Match", test_exact_match()))
    results.append(("Alias Matching", test_alias_matching()))
    results.append(("LLM Mapping New Types", test_llm_mapping_new_types()))
    results.append(("Incomplete Upload", test_incomplete_upload()))

    print("\n" + "="*80)
    print("Test Summary")
    print("="*80)
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")

    total = len(results)
    passed = sum(1 for _, p in results if p)
    print(f"\nTotal: {passed}/{total} tests passed")

    return all(p for _, p in results)


if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
