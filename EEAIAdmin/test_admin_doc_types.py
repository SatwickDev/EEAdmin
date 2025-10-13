#!/usr/bin/env python3
"""
Test script for document type management admin functionality
"""

import requests
import json
from typing import Dict, List

# Configuration
BASE_URL = "http://localhost:5000"
ADMIN_EMAIL = "admin@finstack-tech.com"
ADMIN_PASSWORD = "admin123"  # Update with actual password

class DocumentTypeAdminTester:
    def __init__(self):
        self.session = requests.Session()
        self.authenticated = False
    
    def login(self):
        """Login as admin user"""
        print("Logging in as admin...")
        response = self.session.post(
            f"{BASE_URL}/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.ok:
            data = response.json()
            if data.get("success"):
                self.authenticated = True
                print(f"✓ Logged in successfully as {ADMIN_EMAIL}")
                return True
        print("✗ Login failed")
        return False
    
    def test_get_document_types(self):
        """Test getting all document types"""
        print("\nTesting GET /api/document-types...")
        response = self.session.get(f"{BASE_URL}/api/document-types")
        
        if response.ok:
            data = response.json()
            if data.get("success"):
                doc_types = data.get("document_types", [])
                print(f"✓ Retrieved {len(doc_types)} document types")
                for dt in doc_types[:5]:  # Show first 5
                    print(f"  - {dt['name']}: {dt.get('field_count', 0)} fields")
                return True
        print(f"✗ Failed to get document types: {response.status_code}")
        return False
    
    def test_create_document_type(self):
        """Test creating a new document type"""
        print("\nTesting POST /api/document-types...")
        
        new_doc_type = {
            "name": "Test Purchase Order",
            "fields": [
                {"name": "PO Number", "type": "text", "required": True},
                {"name": "Vendor Name", "type": "text", "required": True},
                {"name": "Total Amount", "type": "currency", "required": True},
                {"name": "Order Date", "type": "date", "required": False}
            ]
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/document-types",
            json=new_doc_type
        )
        
        if response.ok:
            data = response.json()
            if data.get("success"):
                print(f"✓ Created document type: {new_doc_type['name']}")
                return True
        print(f"✗ Failed to create document type: {response.text}")
        return False
    
    def test_update_document_type(self):
        """Test updating a document type"""
        print("\nTesting PUT /api/document-types/<name>...")
        
        updated_fields = [
            {"name": "PO Number", "type": "text", "required": True},
            {"name": "Vendor Name", "type": "text", "required": True},
            {"name": "Total Amount", "type": "currency", "required": True},
            {"name": "Order Date", "type": "date", "required": True},
            {"name": "Delivery Date", "type": "date", "required": False}
        ]
        
        response = self.session.put(
            f"{BASE_URL}/api/document-types/Test%20Purchase%20Order",
            json={"fields": updated_fields}
        )
        
        if response.ok:
            data = response.json()
            if data.get("success"):
                print("✓ Updated document type successfully")
                return True
        print(f"✗ Failed to update document type: {response.text}")
        return False
    
    def test_delete_document_type(self):
        """Test deleting a document type"""
        print("\nTesting DELETE /api/document-types/<name>...")
        
        response = self.session.delete(
            f"{BASE_URL}/api/document-types/Test%20Purchase%20Order"
        )
        
        if response.ok:
            data = response.json()
            if data.get("success"):
                print("✓ Deleted document type successfully")
                return True
        print(f"✗ Failed to delete document type: {response.text}")
        return False
    
    def test_non_admin_access(self):
        """Test that non-admin users cannot access these endpoints"""
        print("\nTesting non-admin access restriction...")
        
        # Logout first
        self.session.post(f"{BASE_URL}/auth/logout")
        
        # Try to access without authentication
        response = self.session.get(f"{BASE_URL}/api/document-types")
        
        if response.status_code in [401, 403]:
            print("✓ Non-admin access properly restricted")
            return True
        print("✗ Security issue: Non-admin could access admin endpoint")
        return False
    
    def run_all_tests(self):
        """Run all tests"""
        print("=" * 50)
        print("Document Type Admin Functionality Test Suite")
        print("=" * 50)
        
        if not self.login():
            print("\nCannot proceed without admin login")
            return
        
        tests = [
            self.test_get_document_types,
            self.test_create_document_type,
            self.test_update_document_type,
            self.test_delete_document_type,
            self.test_non_admin_access
        ]
        
        passed = 0
        failed = 0
        
        for test in tests:
            try:
                if test():
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"✗ Test failed with error: {e}")
                failed += 1
        
        print("\n" + "=" * 50)
        print(f"Test Results: {passed} passed, {failed} failed")
        print("=" * 50)

if __name__ == "__main__":
    tester = DocumentTypeAdminTester()
    tester.run_all_tests()
    
    print("\n" + "=" * 50)
    print("UI Testing Instructions:")
    print("=" * 50)
    print("1. Login as admin user:")
    print(f"   - Email: {ADMIN_EMAIL}")
    print("   - Password: [your admin password]")
    print("\n2. Navigate to: http://localhost:5000/document-classification")
    print("\n3. Admin features to test:")
    print("   - 'Admin: Manage Document Types' button should be visible")
    print("   - Click button to expand admin panel")
    print("   - Test adding new document types")
    print("   - Test adding/removing fields from document types")
    print("   - Test marking fields as required/optional")
    print("   - Test saving changes to document types")
    print("   - Test deleting document types")
    print("\n4. Non-admin testing:")
    print("   - Login as a non-admin user")
    print("   - Admin button should NOT be visible")
    print("   - Document classification should work normally")