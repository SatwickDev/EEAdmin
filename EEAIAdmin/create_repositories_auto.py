#!/usr/bin/env python3
"""
Automatically create default repositories for EEAI system
"""

import os
import sys
from datetime import datetime
from pymongo import MongoClient
from bson import ObjectId

# MongoDB connection
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
DB_NAME = os.getenv('DB_NAME', 'trade_finance_db')

# Default repositories
DEFAULT_REPOSITORIES = [
    {
        "_id": ObjectId(),
        "id": "trade_finance",
        "name": "Trade Finance",
        "description": "Repository for trade finance documents including Letters of Credit, Bank Guarantees, and trade compliance documents",
        "type": "trade_finance",
        "collections": [
            {
                "name": "Letters of Credit",
                "description": "LC documents and related trade finance instruments",
                "document_count": 0
            },
            {
                "name": "Bank Guarantees",
                "description": "Bank guarantee documents and compliance checks",
                "document_count": 0
            },
            {
                "name": "Trade Documents",
                "description": "Bills of Lading, Commercial Invoices, and other trade documents",
                "document_count": 0
            },
            {
                "name": "Compliance Rules",
                "description": "UCP600, SWIFT, and other compliance rule documents",
                "document_count": 0
            }
        ],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "status": "active",
        "connected": False,
        "connected_users": []
    },
    {
        "_id": ObjectId(),
        "id": "treasury",
        "name": "Treasury",
        "description": "Repository for treasury management including foreign exchange, investments, and risk management",
        "type": "treasury",
        "collections": [
            {
                "name": "FX Operations",
                "description": "Foreign exchange transactions and hedging documents",
                "document_count": 0
            },
            {
                "name": "Investment Portfolio",
                "description": "Investment policies, portfolio reports, and analytics",
                "document_count": 0
            },
            {
                "name": "Risk Management",
                "description": "Risk assessment reports and mitigation strategies",
                "document_count": 0
            },
            {
                "name": "Treasury Policies",
                "description": "Internal treasury policies and procedures",
                "document_count": 0
            }
        ],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "status": "active",
        "connected": False,
        "connected_users": []
    },
    {
        "_id": ObjectId(),
        "id": "cash_management",
        "name": "Cash Management",
        "description": "Repository for cash management operations including liquidity, cash flow, and payment processing",
        "type": "cash_management",
        "collections": [
            {
                "name": "Cash Flow Reports",
                "description": "Daily, weekly, and monthly cash flow reports",
                "document_count": 0
            },
            {
                "name": "Liquidity Management",
                "description": "Liquidity forecasts and optimization strategies",
                "document_count": 0
            },
            {
                "name": "Payment Processing",
                "description": "Payment instructions and transaction records",
                "document_count": 0
            },
            {
                "name": "Bank Accounts",
                "description": "Bank account management and reconciliation",
                "document_count": 0
            }
        ],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "status": "active",
        "connected": False,
        "connected_users": []
    }
]

def create_repositories():
    """Create default repositories in MongoDB"""
    try:
        # Connect to MongoDB
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        repositories_collection = db.repositories
        
        print("\n=== Creating Default Repositories ===")
        print(f"Connected to database: {DB_NAME}")
        
        # Check if repositories already exist
        existing_count = repositories_collection.count_documents({})
        if existing_count > 0:
            print(f"\nFound {existing_count} existing repositories. Checking if defaults exist...")
            
            # Check for each default repository
            missing_repos = []
            for repo in DEFAULT_REPOSITORIES:
                if not repositories_collection.find_one({"id": repo["id"]}):
                    missing_repos.append(repo)
            
            if not missing_repos:
                print("✓ All default repositories already exist!")
                return True
            else:
                print(f"Missing {len(missing_repos)} default repositories. Adding them...")
                result = repositories_collection.insert_many(missing_repos)
                print(f"✓ Added {len(result.inserted_ids)} missing repositories")
        else:
            # No repositories exist, create all
            result = repositories_collection.insert_many(DEFAULT_REPOSITORIES)
            print(f"✓ Created {len(result.inserted_ids)} repositories")
        
        print("\n✓ Default repositories setup complete:")
        for repo in DEFAULT_REPOSITORIES:
            existing = repositories_collection.find_one({"id": repo["id"]})
            if existing:
                print(f"  - {repo['name']} ({repo['id']})")
                print(f"    Collections: {len(repo['collections'])}")
        
        print("\n✓ Admins can now connect to these repositories from the AI Chat interface.")
        return True
        
    except Exception as e:
        print(f"\n✗ Error creating repositories: {str(e)}")
        return False
    finally:
        if 'client' in locals():
            client.close()

def verify_repositories():
    """Verify repositories were created correctly"""
    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        repositories_collection = db.repositories
        
        print("\n=== Verifying Repositories ===")
        repos = list(repositories_collection.find({}))
        
        if not repos:
            print("✗ No repositories found!")
            return False
        
        print(f"✓ Found {len(repos)} repositories:")
        for repo in repos:
            print(f"  - {repo['name']} (ID: {repo['id']})")
            print(f"    Status: {repo['status']}")
            print(f"    Collections: {len(repo.get('collections', []))}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error verifying repositories: {str(e)}")
        return False
    finally:
        if 'client' in locals():
            client.close()

if __name__ == "__main__":
    print("EEAI Default Repository Auto-Setup")
    print("==================================")
    
    if create_repositories():
        verify_repositories()
        print("\n✓ Repository setup completed successfully!")
    else:
        print("\n✗ Repository setup failed!")
        sys.exit(1)