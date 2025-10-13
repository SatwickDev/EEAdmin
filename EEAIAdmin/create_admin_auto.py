#!/usr/bin/env python3
"""
Automatically create admin user for EEAI
"""

import requests
import sys

# Configuration
BASE_URL = "http://localhost:5000"
SETUP_KEY = "EEAI-ADMIN-SETUP-2025"  # Change this in production!

def create_admin_user():
    """Create a quick admin user for testing"""
    print("\n=== EEAI Admin User Auto-Creation ===")
    print("Creating admin user with default credentials...")
    
    try:
        response = requests.post(
            f"{BASE_URL}/auth/create-admin",
            json={
                "firstName": "Admin",
                "lastName": "User",
                "email": "admin@eeai.com",
                "password": "admin123",
                "setupKey": SETUP_KEY
            }
        )
        
        if response.status_code == 201:
            data = response.json()
            print("\n✓ Admin user created successfully!")
            print("  Email: admin@eeai.com")
            print("  Password: admin123")
            print("  Role: admin")
            print(f"  ID: {data.get('user_id', 'N/A')}")
            print("\n⚠️  WARNING: Change these credentials in production!")
            print("\nYou can now login at http://localhost:5000/")
            return True
        else:
            error_data = response.json()
            if "already exists" in error_data.get('message', '').lower():
                print("\n✓ Admin user already exists!")
                print("  Email: admin@eeai.com")
                print("  Password: admin123")
                return True
            else:
                print(f"\n✗ Failed to create admin user: {error_data.get('message', 'Unknown error')}")
                return False
            
    except requests.exceptions.ConnectionError:
        print("\n✗ Error: Could not connect to the EEAI server.")
        print("  Make sure the server is running on http://localhost:5000")
        print("  Start the server with: python run.py")
        return False
    except Exception as e:
        print(f"\n✗ Error creating admin user: {str(e)}")
        return False

if __name__ == "__main__":
    create_admin_user()