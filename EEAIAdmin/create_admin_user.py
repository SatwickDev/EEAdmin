#!/usr/bin/env python3
"""
Script to create an admin user via the API.
This uses the /auth/create-admin endpoint with the setup key.
"""

import requests
import json
import sys
import getpass
import os

# API configuration
BASE_URL = os.environ.get('EEAI_BASE_URL', 'http://localhost:5000')
ADMIN_SETUP_KEY = os.environ.get('ADMIN_SETUP_KEY', 'EEAI-ADMIN-SETUP-2025')

def create_admin_user():
    """Create an admin user via the API."""
    print("=== EEAI Admin User Creation ===\n")
    
    # Collect user information
    print("Enter admin user details:")
    first_name = input("First Name: ").strip()
    last_name = input("Last Name: ").strip()
    email = input("Email: ").strip()
    password = getpass.getpass("Password: ")
    confirm_password = getpass.getpass("Confirm Password: ")
    
    # Validate passwords match
    if password != confirm_password:
        print("\nError: Passwords do not match!")
        return False
    
    # Validate required fields
    if not all([first_name, last_name, email, password]):
        print("\nError: All fields are required!")
        return False
    
    # Prepare request data
    data = {
        'firstName': first_name,
        'lastName': last_name,
        'email': email,
        'password': password,
        'setup_key': ADMIN_SETUP_KEY
    }
    
    # Make API request
    try:
        print(f"\nCreating admin user at {BASE_URL}/auth/create-admin...")
        response = requests.post(
            f"{BASE_URL}/auth/create-admin",
            json=data,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 201:
            result = response.json()
            print(f"\n✅ Success! Admin user created:")
            print(f"   Email: {result['user']['email']}")
            print(f"   Role: {result['user']['role']}")
            print("\nYou can now log in with these credentials.")
            return True
        else:
            error = response.json()
            print(f"\n❌ Error: {error.get('message', 'Unknown error')}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"\n❌ Error: Could not connect to {BASE_URL}")
        print("Make sure the EEAI application is running.")
        return False
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    print("This script will create an admin user for the EEAI application.")
    print(f"Using API endpoint: {BASE_URL}")
    print(f"Setup key: {'*' * len(ADMIN_SETUP_KEY)}\n")
    
    if create_admin_user():
        sys.exit(0)
    else:
        sys.exit(1)