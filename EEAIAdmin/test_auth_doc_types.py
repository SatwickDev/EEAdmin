#!/usr/bin/env python3
"""
Test script for authentication and document types management.
Tests the simplified authentication without admin roles.
"""

import requests
import json
import sys

# Base URL for the API
BASE_URL = "http://localhost:5000"

# Test credentials (allowed users)
TEST_USERS = [
    {"email": "ravi@finstack-tech.com", "password": "test123", "firstName": "Ravi", "lastName": "User"},
    {"email": "ilyashussain9@gmail.com", "password": "test123", "firstName": "Ilyas", "lastName": "Hussain"},
    {"email": "admin@finstack-tech.com", "password": "test123", "firstName": "Admin", "lastName": "User"}
]

def test_register_user(user_data):
    """Test user registration"""
    print(f"\n🔹 Testing registration for {user_data['email']}...")
    
    response = requests.post(
        f"{BASE_URL}/auth/register",
        json=user_data,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 201:
        print(f"   ✅ User registered successfully")
        return True
    elif response.status_code == 400 and "already exists" in response.json().get("message", ""):
        print(f"   ℹ️  User already exists")
        return True
    else:
        print(f"   ❌ Registration failed: {response.json().get('message', 'Unknown error')}")
        return False

def test_login(email, password):
    """Test user login"""
    print(f"\n🔹 Testing login for {email}...")
    
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": email, "password": password},
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Login successful")
        print(f"   User: {data['user']['firstName']} {data['user']['lastName']}")
        print(f"   Allowed: {data['user'].get('isAllowed', False)}")
        return response.cookies
    else:
        print(f"   ❌ Login failed: {response.json().get('message', 'Unknown error')}")
        return None

def test_get_current_user(cookies):
    """Test getting current user info"""
    print(f"\n🔹 Testing get current user...")
    
    response = requests.get(
        f"{BASE_URL}/auth/current-user",
        cookies=cookies
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Current user retrieved")
        print(f"   Email: {data['user']['email']}")
        print(f"   Allowed: {data['user'].get('isAllowed', False)}")
        return True
    else:
        print(f"   ❌ Failed to get current user: {response.json().get('message', 'Unknown error')}")
        return False

def test_document_types_api(cookies):
    """Test document types management API"""
    print(f"\n🔹 Testing document types API...")
    
    # Test GET document types
    response = requests.get(
        f"{BASE_URL}/api/document-types",
        cookies=cookies
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Retrieved document types")
        if data.get('document_types'):
            for doc_type in data['document_types'][:3]:  # Show first 3
                print(f"      - {doc_type.get('name', 'Unknown')}: {len(doc_type.get('fields', []))} fields")
        return True
    elif response.status_code == 403:
        print(f"   ❌ Access denied (user not in allowed list)")
        return False
    else:
        print(f"   ❌ Failed to get document types: {response.status_code}")
        return False

def test_create_document_type(cookies):
    """Test creating a new document type"""
    print(f"\n🔹 Testing create document type...")
    
    new_doc_type = {
        "name": "Test_Document",
        "fields": [
            {"name": "field1", "type": "text", "required": True},
            {"name": "field2", "type": "number", "required": False}
        ]
    }
    
    response = requests.post(
        f"{BASE_URL}/api/document-types",
        json=new_doc_type,
        cookies=cookies,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 201:
        print(f"   ✅ Document type created successfully")
        return True
    elif response.status_code == 403:
        print(f"   ❌ Access denied (user not in allowed list)")
        return False
    else:
        print(f"   ❌ Failed to create document type: {response.json().get('message', 'Unknown error')}")
        return False

def main():
    print("=" * 60)
    print("🧪 Testing Authentication and Document Types Management")
    print("=" * 60)
    
    # Test with first allowed user
    test_user = TEST_USERS[0]
    
    # Register user
    if not test_register_user(test_user):
        print("\n⚠️  Continuing with existing user...")
    
    # Login
    cookies = test_login(test_user["email"], test_user["password"])
    if not cookies:
        print("\n❌ Cannot proceed without authentication")
        return 1
    
    # Get current user
    test_get_current_user(cookies)
    
    # Test document types API
    test_document_types_api(cookies)
    
    # Test creating a document type
    test_create_document_type(cookies)
    
    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("=" * 60)
    
    # Test with non-allowed user
    print("\n🔹 Testing with non-allowed user...")
    non_allowed_user = {
        "email": "notallowed@example.com",
        "password": "test123",
        "firstName": "Not",
        "lastName": "Allowed"
    }
    
    # Register non-allowed user
    test_register_user(non_allowed_user)
    
    # Login as non-allowed user
    cookies = test_login(non_allowed_user["email"], non_allowed_user["password"])
    if cookies:
        # Try to access document types (should be denied)
        test_document_types_api(cookies)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())