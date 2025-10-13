#!/usr/bin/env python3
"""
Quick admin user creation script for EEAI
Creates an admin user with predefined credentials for testing
"""

import requests
import sys
import getpass
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:5000"
SETUP_KEY = "EEAI-ADMIN-SETUP-2025"  # Change this in production!

def create_admin_user():
    """Create an admin user via the API"""
    
    print("=== EEAI Admin User Creation ===")
    print("This will create an admin user for the EEAI system.")
    print()
    
    # Get user details
    print("Enter admin user details:")
    first_name = input("First Name: ").strip()
    last_name = input("Last Name: ").strip()
    email = input("Email: ").strip()
    password = getpass.getpass("Password: ")
    confirm_password = getpass.getpass("Confirm Password: ")
    
    # Validate password match
    if password != confirm_password:
        print("Error: Passwords do not match!")
        return False
    
    # Validate required fields
    if not all([first_name, last_name, email, password]):
        print("Error: All fields are required!")
        return False
    
    # Create the admin user
    try:
        response = requests.post(
            f"{BASE_URL}/auth/create-admin",
            json={
                "firstName": first_name,
                "lastName": last_name,
                "email": email,
                "password": password,
                "setupKey": SETUP_KEY
            }
        )
        
        if response.status_code == 201:
            data = response.json()
            print(f"\n✓ Admin user created successfully!")
            print(f"  Email: {email}")
            print(f"  Role: admin")
            print(f"  ID: {data.get('user_id', 'N/A')}")
            print("\nYou can now login with these credentials at /")
            return True
        else:
            error_data = response.json()
            print(f"\n✗ Failed to create admin user: {error_data.get('message', 'Unknown error')}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("\n✗ Error: Could not connect to the EEAI server.")
        print("  Make sure the server is running on http://localhost:5000")
        return False
    except Exception as e:
        print(f"\n✗ Error creating admin user: {str(e)}")
        return False

def create_quick_admin():
    """Create a quick admin user for testing"""
    print("\n=== Quick Admin Creation (Testing Only) ===")
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
            print("\n✓ Quick admin user created!")
            print("  Email: admin@eeai.com")
            print("  Password: admin123")
            print("  Role: admin")
            print("\n⚠️  WARNING: Change these credentials in production!")
            return True
        else:
            error_data = response.json()
            print(f"\n✗ Failed: {error_data.get('message', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        return False

if __name__ == "__main__":
    print("Choose an option:")
    print("1. Create custom admin user")
    print("2. Create quick admin user (admin@eeai.com / admin123)")
    print("3. Exit")
    
    choice = input("\nEnter your choice (1-3): ").strip()
    
    if choice == "1":
        create_admin_user()
    elif choice == "2":
        create_quick_admin()
    elif choice == "3":
        print("Exiting...")
        sys.exit(0)
    else:
        print("Invalid choice!")
        sys.exit(1)