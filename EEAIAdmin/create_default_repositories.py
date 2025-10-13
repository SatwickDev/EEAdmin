#!/usr/bin/env python3
"""
Create default repositories for EEAI system:
- Trade Finance
- Treasury
- Cash Management
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
        
        print("=== Creating Default Repositories ===")
        print(f"Connected to database: {DB_NAME}")
        print()
        
        # Check if repositories already exist
        existing_count = repositories_collection.count_documents({})
        if existing_count > 0:
            print(f"Found {existing_count} existing repositories.")
            response = input("Do you want to replace them? (yes/no): ").strip().lower()
            if response != 'yes':
                print("Aborted. No changes made.")
                return
            
            # Clear existing repositories
            repositories_collection.delete_many({})
            print("Cleared existing repositories.")
        
        # Insert default repositories
        result = repositories_collection.insert_many(DEFAULT_REPOSITORIES)
        print(f"\n✓ Created {len(result.inserted_ids)} repositories:")
        
        for repo in DEFAULT_REPOSITORIES:
            print(f"  - {repo['name']} ({repo['id']})")
            print(f"    Collections: {len(repo['collections'])}")
            for col in repo['collections']:
                print(f"      • {col['name']}")
        
        print("\n✓ Default repositories created successfully!")
        print("\nAdmins can now connect to these repositories from the AI Chat interface.")
        
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
            print(f"    Connected: {repo['connected']}")
            print(f"    Collections: {len(repo['collections'])}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error verifying repositories: {str(e)}")
        return False
    finally:
        if 'client' in locals():
            client.close()

if __name__ == "__main__":
    print("EEAI Default Repository Setup")
    print("=============================")
    print()
    print("This script will create the following repositories:")
    print("1. Trade Finance - For LC, Bank Guarantees, and trade documents")
    print("2. Treasury - For FX, investments, and risk management")
    print("3. Cash Management - For cash flow, liquidity, and payments")
    print()
    
    response = input("Continue? (yes/no): ").strip().lower()
    if response == 'yes':
        create_repositories()
        verify_repositories()
    else:
        print("Setup cancelled.")