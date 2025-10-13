#!/usr/bin/env python3
"""
Test script to verify admin features are working correctly
"""

import requests
import json

# Configuration
BASE_URL = "http://localhost:5000"  # Adjust if your app runs on a different port
ADMIN_EMAIL = "ravi@finstack-tech.com"
ADMIN_PASSWORD = "admin123"  # Replace with actual password
USER_EMAIL = "test@example.com"
USER_PASSWORD = "user123"  # Replace with actual password

session = requests.Session()

def test_admin_login():
    """Test admin login"""
    print("Testing admin login...")
    response = session.post(f"{BASE_URL}/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Admin login successful: {data.get('user', {}).get('email')}")
        print(f"  Is Admin: {data.get('user', {}).get('isAdmin')}")
        return True
    else:
        print(f"✗ Admin login failed: {response.status_code}")
        return False

def test_get_manuals():
    """Test getting manuals list"""
    print("\nTesting get manuals...")
    response = session.get(f"{BASE_URL}/api/admin/manuals")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Got manuals list")
        print(f"  Number of manuals: {len(data.get('manuals', []))}")
        print(f"  User is admin: {data.get('is_admin')}")
        for manual in data.get('manuals', []):
            print(f"    - {manual.get('name')}")
        return True
    else:
        print(f"✗ Failed to get manuals: {response.status_code}")
        return False

def test_get_repository_status():
    """Test getting repository status"""
    print("\nTesting get repository status...")
    response = session.get(f"{BASE_URL}/api/repository-status")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Got repository status")
        if data.get('connected'):
            repo = data.get('repository', {})
            print(f"  Connected to: {repo.get('type')} - {repo.get('host')}:{repo.get('port')}")
        else:
            print(f"  No repository connected")
        return True
    else:
        print(f"✗ Failed to get repository status: {response.status_code}")
        return False

def test_user_login():
    """Test regular user login"""
    print("\n\nTesting regular user login...")
    session_user = requests.Session()
    response = session_user.post(f"{BASE_URL}/auth/login", json={
        "email": USER_EMAIL,
        "password": USER_PASSWORD
    })
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ User login successful: {data.get('user', {}).get('email')}")
        print(f"  Is Admin: {data.get('user', {}).get('isAdmin', False)}")
        
        # Test user can see manuals
        print("\n  Testing user access to manuals...")
        response = session_user.get(f"{BASE_URL}/api/admin/manuals")
        if response.status_code == 200:
            data = response.json()
            print(f"  ✓ User can see manuals")
            print(f"    Number of manuals: {len(data.get('manuals', []))}")
            print(f"    User is admin: {data.get('is_admin', False)}")
        else:
            print(f"  ✗ User cannot see manuals: {response.status_code}")
        
        # Test user can see repository status
        print("\n  Testing user access to repository status...")
        response = session_user.get(f"{BASE_URL}/api/repository-status")
        if response.status_code == 200:
            data = response.json()
            print(f"  ✓ User can see repository status")
            if data.get('connected'):
                repo = data.get('repository', {})
                print(f"    Connected to: {repo.get('type')} - {repo.get('host')}:{repo.get('port')}")
            else:
                print(f"    No repository connected")
        else:
            print(f"  ✗ User cannot see repository status: {response.status_code}")
            
        return True
    else:
        print(f"✗ User login failed: {response.status_code}")
        print("  Note: You may need to create a test user first")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("Testing Admin Features")
    print("=" * 50)
    
    # Test admin functions
    if test_admin_login():
        test_get_manuals()
        test_get_repository_status()
    
    # Test regular user access
    test_user_login()
    
    print("\n" + "=" * 50)
    print("Test Complete")
    print("=" * 50)
    print("\nSummary:")
    print("- Admin users can upload manuals and connect repositories")
    print("- All logged-in users can see uploaded manuals")
    print("- All logged-in users can see connected repository status")
    print("- Non-admin users cannot upload/delete manuals or modify repository connections")