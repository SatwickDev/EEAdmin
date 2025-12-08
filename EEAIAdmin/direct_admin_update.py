#!/usr/bin/env python3
"""
Direct MongoDB update to create admin user
Works even if Flask server is not accessible
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from werkzeug.security import generate_password_hash
from app.utils.mongodb_manager import get_mongo_client, get_database
import logging

logger = logging.getLogger(__name__)

def update_user_to_admin(email):
    """Update existing user to admin role"""
    try:
        client = get_mongo_client()
        if client is None:
            logger.error("Failed to connect to MongoDB - client is None")
            return False
        
        db = get_database(client, 'trade_finance_db')
        if db is None:
            logger.error("Failed to get database")
            return False
            
        users = db.users
        
        # Update user role
        result = users.update_one(
            {'email': email},
            {'$set': {
                'role': 'admin',
                'permissions': [
                    'manage_repositories',
                    'upload_documents',
                    'delete_documents',
                    'view_analytics',
                    'manage_basic_users'
                ]
            }}
        )
        
        if result.matched_count > 0:
            print(f"✓ Successfully updated {email} to admin role!")
            print("  You can now login with your existing password")
            return True
        else:
            print(f"✗ User {email} not found!")
            return False
            
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False
    finally:
        if client:
            client.close()

def create_admin_user():
    """Create a new admin user"""
    try:
        client = get_mongo_client()
        if client is None:
            print("✗ Failed to connect to MongoDB")
            return False
        
        db = get_database(client, 'trade_finance_db')
        if db is None:
            print("✗ Failed to get database")
            return False
            
        users = db.users
        
        # Check if admin already exists
        if users.find_one({'email': 'admin@eeai.com'}):
            print("✓ Admin user already exists!")
            print("  Email: admin@eeai.com")
            print("  Password: admin123")
            return True
        
        # Create admin user
        admin_doc = {
            'firstName': 'Admin',
            'lastName': 'User',
            'email': 'admin@eeai.com',
            'passwordHash': generate_password_hash('admin123'),
            'role': 'admin',
            'isActive': True,
            'permissions': [
                'manage_repositories',
                'upload_documents',
                'delete_documents',
                'view_analytics',
                'manage_basic_users'
            ]
        }
        
        users.insert_one(admin_doc)
        print("✓ Admin user created successfully!")
        print("  Email: admin@eeai.com")
        print("  Password: admin123")
        print("\n⚠️  Change this password in production!")
        return True
        
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False
    finally:
        if client:
            client.close()

if __name__ == "__main__":
    print("=== Direct Admin Setup ===")
    print("1. Update existing user to admin")
    print("2. Create new admin user (admin@eeai.com)")
    
    choice = input("\nChoose option (1-2): ").strip()
    
    if choice == '1':
        email = input("Enter user email to make admin: ").strip()
        update_user_to_admin(email)
    elif choice == '2':
        create_admin_user()
    else:
        print("Invalid choice!")
        
    print("\n✓ Done! You can now login at http://localhost:5000/")