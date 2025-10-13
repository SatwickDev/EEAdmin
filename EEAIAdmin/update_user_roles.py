#!/usr/bin/env python3
"""
Script to update existing users with default 'user' role.
Run this once to migrate existing users to the new role-based system.
"""

import os
from pymongo import MongoClient
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# MongoDB connection
MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
DB_NAME = os.environ.get('DB_NAME', 'trade_finance_db')

def update_user_roles():
    """Update all existing users without a role to have 'user' role."""
    try:
        # Connect to MongoDB
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        users_collection = db.users
        
        # Find all users without a role field
        users_without_role = users_collection.find({'role': {'$exists': False}})
        
        update_count = 0
        for user in users_without_role:
            # Update user with default 'user' role
            result = users_collection.update_one(
                {'_id': user['_id']},
                {
                    '$set': {
                        'role': 'user',
                        'roleUpdatedAt': datetime.utcnow()
                    }
                }
            )
            if result.modified_count > 0:
                update_count += 1
                logger.info(f"Updated user {user.get('email', 'unknown')} with 'user' role")
        
        logger.info(f"Successfully updated {update_count} users with default role")
        
        # Show statistics
        total_users = users_collection.count_documents({})
        admin_count = users_collection.count_documents({'role': 'admin'})
        user_count = users_collection.count_documents({'role': 'user'})
        
        logger.info(f"\nUser statistics:")
        logger.info(f"Total users: {total_users}")
        logger.info(f"Admin users: {admin_count}")
        logger.info(f"Regular users: {user_count}")
        
    except Exception as e:
        logger.error(f"Error updating user roles: {e}")
        raise
    finally:
        client.close()

if __name__ == "__main__":
    logger.info("Starting user role migration...")
    update_user_roles()
    logger.info("User role migration completed.")