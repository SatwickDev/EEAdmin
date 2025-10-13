#!/usr/bin/env python3
"""
Add new admin users and implement extended role system
No frontend or route changes required - database operations only
"""

import os
import sys
from datetime import datetime
from pymongo import MongoClient
from werkzeug.security import generate_password_hash
import getpass

# MongoDB connection
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
DB_NAME = os.getenv('DB_NAME', 'trade_finance_db')

# Extended role definitions
ROLES = {
    'super_admin': {
        'name': 'Super Administrator',
        'description': 'Full system access, can manage all users and system settings',
        'permissions': [
            'manage_all_users',
            'manage_repositories',
            'upload_documents',
            'delete_documents',
            'system_configuration',
            'view_all_analytics',
            'manage_roles'
        ]
    },
    'admin': {
        'name': 'Administrator',
        'description': 'Can manage repositories and documents',
        'permissions': [
            'manage_repositories',
            'upload_documents',
            'delete_documents',
            'view_analytics',
            'manage_basic_users'
        ]
    },
    'manager': {
        'name': 'Manager',
        'description': 'Can upload documents and view extended analytics',
        'permissions': [
            'upload_documents',
            'view_analytics',
            'view_all_repositories',
            'export_data'
        ]
    },
    'analyst': {
        'name': 'Analyst',
        'description': 'Can query and analyze data across repositories',
        'permissions': [
            'query_all_repositories',
            'view_analytics',
            'export_data',
            'create_reports'
        ]
    },
    'user': {
        'name': 'Standard User',
        'description': 'Basic query access to connected repositories',
        'permissions': [
            'query_connected_repository',
            'view_own_history'
        ]
    },
    'viewer': {
        'name': 'Viewer',
        'description': 'Read-only access to specific data',
        'permissions': [
            'view_public_data',
            'view_limited_analytics'
        ]
    }
}

def create_roles_collection():
    """Create roles collection with predefined roles"""
    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        roles_collection = db.roles
        
        print("\n=== Creating Roles Collection ===")
        
        # Check if roles already exist
        if roles_collection.count_documents({}) > 0:
            print("Roles collection already exists. Updating...")
        
        # Insert or update roles
        for role_id, role_data in ROLES.items():
            role_doc = {
                'role_id': role_id,
                'name': role_data['name'],
                'description': role_data['description'],
                'permissions': role_data['permissions'],
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            
            # Update or insert
            roles_collection.update_one(
                {'role_id': role_id},
                {'$set': role_doc},
                upsert=True
            )
            print(f"✓ Created/Updated role: {role_data['name']} ({role_id})")
        
        print(f"\n✓ Total roles configured: {len(ROLES)}")
        return True
        
    except Exception as e:
        print(f"✗ Error creating roles: {str(e)}")
        return False
    finally:
        if 'client' in locals():
            client.close()

def add_admin_user():
    """Add a new admin user interactively"""
    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        users_collection = db.users
        
        print("\n=== Add New Admin User ===")
        
        # Get user details
        first_name = input("First Name: ").strip()
        last_name = input("Last Name: ").strip()
        email = input("Email: ").strip().lower()
        password = getpass.getpass("Password: ")
        
        # Show available roles
        print("\nAvailable roles:")
        for i, (role_id, role_data) in enumerate(ROLES.items(), 1):
            print(f"{i}. {role_id} - {role_data['name']}")
        
        role_choice = input("\nSelect role (1-6) or type role name: ").strip()
        
        # Determine role
        if role_choice.isdigit():
            role_index = int(role_choice) - 1
            role = list(ROLES.keys())[role_index] if 0 <= role_index < len(ROLES) else 'user'
        else:
            role = role_choice if role_choice in ROLES else 'user'
        
        # Validate required fields
        if not all([first_name, last_name, email, password]):
            print("✗ All fields are required!")
            return False
        
        # Check if user already exists
        if users_collection.find_one({'email': email}):
            print(f"✗ User with email {email} already exists!")
            update = input("Do you want to update their role? (yes/no): ").lower()
            if update == 'yes':
                users_collection.update_one(
                    {'email': email},
                    {'$set': {'role': role, 'updated_at': datetime.utcnow()}}
                )
                print(f"✓ Updated {email} to role: {role}")
                return True
            return False
        
        # Create new user
        user_doc = {
            'firstName': first_name,
            'lastName': last_name,
            'email': email,
            'passwordHash': generate_password_hash(password),
            'role': role,
            'createdAt': datetime.utcnow(),
            'lastLogin': None,
            'isActive': True,
            'permissions': ROLES[role]['permissions']  # Store permissions directly
        }
        
        result = users_collection.insert_one(user_doc)
        
        print(f"\n✓ Admin user created successfully!")
        print(f"  Name: {first_name} {last_name}")
        print(f"  Email: {email}")
        print(f"  Role: {role} ({ROLES[role]['name']})")
        print(f"  ID: {result.inserted_id}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error creating admin user: {str(e)}")
        return False
    finally:
        if 'client' in locals():
            client.close()

def bulk_add_admins():
    """Add multiple admin users from predefined list"""
    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        users_collection = db.users
        
        print("\n=== Bulk Add Admin Users ===")
        
        # Predefined admin users
        admin_users = [
            {
                'firstName': 'Super',
                'lastName': 'Admin',
                'email': 'superadmin@eeai.com',
                'password': 'SuperAdmin@123',
                'role': 'super_admin'
            },
            {
                'firstName': 'Trade',
                'lastName': 'Admin',
                'email': 'trade.admin@eeai.com',
                'password': 'TradeAdmin@123',
                'role': 'admin'
            },
            {
                'firstName': 'Treasury',
                'lastName': 'Manager',
                'email': 'treasury.manager@eeai.com',
                'password': 'TreasuryMgr@123',
                'role': 'manager'
            },
            {
                'firstName': 'Cash',
                'lastName': 'Analyst',
                'email': 'cash.analyst@eeai.com',
                'password': 'CashAnalyst@123',
                'role': 'analyst'
            }
        ]
        
        created_count = 0
        for user in admin_users:
            # Check if user exists
            if users_collection.find_one({'email': user['email']}):
                print(f"⚠️  User {user['email']} already exists, skipping...")
                continue
            
            # Create user document
            user_doc = {
                'firstName': user['firstName'],
                'lastName': user['lastName'],
                'email': user['email'],
                'passwordHash': generate_password_hash(user['password']),
                'role': user['role'],
                'createdAt': datetime.utcnow(),
                'lastLogin': None,
                'isActive': True,
                'permissions': ROLES[user['role']]['permissions']
            }
            
            users_collection.insert_one(user_doc)
            created_count += 1
            print(f"✓ Created: {user['email']} ({user['role']})")
        
        print(f"\n✓ Created {created_count} new admin users")
        
        # Display all admin users
        print("\n=== All Admin/Manager Users ===")
        admin_roles = ['super_admin', 'admin', 'manager']
        admins = users_collection.find({'role': {'$in': admin_roles}})
        
        for admin in admins:
            print(f"  - {admin['email']} ({admin['role']})")
        
        return True
        
    except Exception as e:
        print(f"✗ Error in bulk creation: {str(e)}")
        return False
    finally:
        if 'client' in locals():
            client.close()

def update_existing_users_permissions():
    """Update all existing users with their role permissions"""
    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        users_collection = db.users
        
        print("\n=== Updating Existing Users with Permissions ===")
        
        users = users_collection.find({})
        updated_count = 0
        
        for user in users:
            role = user.get('role', 'user')
            if role not in ROLES:
                role = 'user'  # Default to user if role not found
            
            # Update user with permissions
            users_collection.update_one(
                {'_id': user['_id']},
                {
                    '$set': {
                        'role': role,
                        'permissions': ROLES[role]['permissions'],
                        'updated_at': datetime.utcnow()
                    }
                }
            )
            updated_count += 1
            print(f"✓ Updated {user['email']} with {role} permissions")
        
        print(f"\n✓ Updated {updated_count} users with permissions")
        return True
        
    except Exception as e:
        print(f"✗ Error updating users: {str(e)}")
        return False
    finally:
        if 'client' in locals():
            client.close()

def display_role_hierarchy():
    """Display the role hierarchy and permissions"""
    print("\n=== EEAI Role Hierarchy ===")
    print("=" * 60)
    
    for role_id, role_data in ROLES.items():
        print(f"\n{role_id.upper()} - {role_data['name']}")
        print(f"Description: {role_data['description']}")
        print("Permissions:")
        for perm in role_data['permissions']:
            print(f"  • {perm}")
    
    print("\n" + "=" * 60)

def main():
    """Main menu for admin and role management"""
    while True:
        print("\n=== EEAI Admin & Role Management ===")
        print("1. Display role hierarchy")
        print("2. Create roles collection")
        print("3. Add single admin user")
        print("4. Bulk add predefined admins")
        print("5. Update existing users with permissions")
        print("6. Add all (roles + bulk admins + update)")
        print("7. Exit")
        
        choice = input("\nSelect option (1-7): ").strip()
        
        if choice == '1':
            display_role_hierarchy()
        elif choice == '2':
            create_roles_collection()
        elif choice == '3':
            add_admin_user()
        elif choice == '4':
            bulk_add_admins()
        elif choice == '5':
            update_existing_users_permissions()
        elif choice == '6':
            # Do everything
            print("\n=== Complete Setup ===")
            create_roles_collection()
            bulk_add_admins()
            update_existing_users_permissions()
            print("\n✓ Complete setup finished!")
        elif choice == '7':
            print("Exiting...")
            break
        else:
            print("Invalid choice!")

if __name__ == "__main__":
    # Check if running with command line argument
    if len(sys.argv) > 1:
        if sys.argv[1] == '--auto':
            # Automatic setup
            print("Running automatic setup...")
            create_roles_collection()
            bulk_add_admins()
            update_existing_users_permissions()
            display_role_hierarchy()
        elif sys.argv[1] == '--roles':
            display_role_hierarchy()
        elif sys.argv[1] == '--add-admin':
            add_admin_user()
    else:
        # Interactive mode
        main()