#!/usr/bin/env python3
"""
Test script for per-customer Chroma DB management.

This script demonstrates and tests enabling/disabling Chroma for different customers.

Usage:
    python test_chroma_customer_management.py
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_imports():
    """Test that all required modules can be imported."""
    logger.info("=" * 60)
    logger.info("TEST 1: Verifying imports...")
    logger.info("=" * 60)
    try:
        from pymongo import MongoClient
        logger.info("✓ PyMongo imported successfully")
        
        from app.utils.chroma_manager import (
            get_request_customer_id,
            is_chroma_enabled_for_customer,
            get_chroma_client_for_customer
        )
        logger.info("✓ Chroma manager functions imported successfully")
        return True
    except ImportError as e:
        logger.error(f"✗ Import failed: {e}")
        return False


def setup_mongodb():
    """Connect to MongoDB and return db object."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 2: MongoDB Connection...")
    logger.info("=" * 60)
    try:
        from app.utils.mongodb_manager import get_mongo_client, get_database
        client = get_mongo_client()
        if client is None:
            logger.error("✗ MongoDB connection failed (may be disabled)")
            return None
        db = get_database(client)
        if db is None:
            logger.error("✗ Could not get database")
            return None
        logger.info(f"✓ Connected to MongoDB successfully")
        logger.info(f"✓ Using database: {db.name}")
        return db
    except Exception as e:
        logger.error(f"✗ MongoDB connection failed: {e}")
        return None


def setup_default_config(db):
    """Create or update default Chroma configuration."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 3: Setting Up Default Configuration...")
    logger.info("=" * 60)
    try:
        config = {
            "type": "chromadb",
            "host": "localhost",
            "port": 8000,
            "is_active": True,
            "enabled_for_all": True,
            "customers": [],
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        result = db.repository_config.update_one(
            {"type": "chromadb"},
            {"$set": config},
            upsert=True
        )
        logger.info(f"✓ Default config created/updated")
        logger.info(f"  Matched: {result.matched_count}, Upserted: {result.upserted_id is not None}")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to setup config: {e}")
        return False


def test_chroma_enabled_for_all(db):
    """Test: Enable Chroma for all customers."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 4: Enable Chroma for ALL Customers")
    logger.info("=" * 60)
    try:
        from app.utils.chroma_manager import is_chroma_enabled_for_customer
        
        # Update config to enable for all
        db.repository_config.update_one(
            {"type": "chromadb"},
            {
                "$set": {
                    "is_active": True,
                    "enabled_for_all": True,
                    "customers": []
                }
            }
        )
        logger.info("Configuration: enabled_for_all=True")
        
        # Test various customers
        test_customers = ["bank1", "bank2", "bank3", "universal_customer"]
        all_enabled = True
        for cust in test_customers:
            enabled = is_chroma_enabled_for_customer(cust, db)
            status = "✓" if enabled else "✗"
            logger.info(f"  {status} Customer '{cust}': {'ENABLED' if enabled else 'DISABLED'}")
            all_enabled = all_enabled and enabled
        
        if all_enabled:
            logger.info("✓ All customers can access Chroma")
            return True
        else:
            logger.error("✗ Some customers cannot access Chroma")
            return False
    except Exception as e:
        logger.error(f"✗ Test failed: {e}")
        return False


def test_chroma_disabled_for_specific(db):
    """Test: Disable Chroma for specific customer."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 5: Enable Chroma ONLY for Specific Customers")
    logger.info("=" * 60)
    try:
        from app.utils.chroma_manager import is_chroma_enabled_for_customer
        
        # Allow only bank1 and bank2
        allowed = ["bank1", "bank2"]
        db.repository_config.update_one(
            {"type": "chromadb"},
            {
                "$set": {
                    "is_active": True,
                    "enabled_for_all": False,
                    "customers": allowed
                }
            }
        )
        logger.info(f"Configuration: customers={allowed}")
        
        # Test
        test_cases = [
            ("bank1", True),
            ("bank2", True),
            ("bank3", False),
            ("bank4", False),
        ]
        
        all_passed = True
        for cust, expected in test_cases:
            enabled = is_chroma_enabled_for_customer(cust, db)
            passed = enabled == expected
            status = "✓" if passed else "✗"
            logger.info(f"  {status} Customer '{cust}': {'ENABLED' if enabled else 'DISABLED'} (expected: {'ENABLED' if expected else 'DISABLED'})")
            all_passed = all_passed and passed
        
        if all_passed:
            logger.info("✓ Access control working correctly")
            return True
        else:
            logger.error("✗ Access control test failed")
            return False
    except Exception as e:
        logger.error(f"✗ Test failed: {e}")
        return False


def test_chroma_disabled_globally(db):
    """Test: Disable Chroma globally."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 6: Disable Chroma GLOBALLY")
    logger.info("=" * 60)
    try:
        from app.utils.chroma_manager import is_chroma_enabled_for_customer
        
        # Disable globally
        db.repository_config.update_one(
            {"type": "chromadb"},
            {
                "$set": {
                    "is_active": False,
                    "enabled_for_all": False,
                    "customers": []
                }
            }
        )
        logger.info("Configuration: is_active=False")
        
        # Test - all should be disabled
        test_customers = ["bank1", "bank2", "bank3"]
        all_disabled = True
        for cust in test_customers:
            enabled = is_chroma_enabled_for_customer(cust, db)
            status = "✓" if not enabled else "✗"
            logger.info(f"  {status} Customer '{cust}': {'ENABLED' if enabled else 'DISABLED'}")
            all_disabled = all_disabled and (not enabled)
        
        if all_disabled:
            logger.info("✓ Chroma successfully disabled for all")
            return True
        else:
            logger.error("✗ Chroma disable failed")
            return False
    except Exception as e:
        logger.error(f"✗ Test failed: {e}")
        return False


def test_get_chroma_client(db):
    """Test: Get Chroma client for customers."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 7: Get Chroma Client for Customers")
    logger.info("=" * 60)
    try:
        from app.utils.chroma_manager import get_chroma_client_for_customer
        
        # Re-enable for bank1 only
        db.repository_config.update_one(
            {"type": "chromadb"},
            {
                "$set": {
                    "is_active": True,
                    "enabled_for_all": False,
                    "customers": ["bank1"],
                    "host": "localhost",
                    "port": 8000
                }
            }
        )
        
        logger.info("Configuration: customers=['bank1'], host='localhost:8000'")
        
        # Note: Chroma server may not be running, so we test the logic
        logger.info("\nTesting client resolution (Chroma server may not be running):")
        
        client = get_chroma_client_for_customer("bank1", db)
        if client is not None:
            logger.info("  ✓ Client created for bank1")
        else:
            logger.info("  ℹ Client is None (Chroma server not running or config issue)")
        
        client = get_chroma_client_for_customer("bank2", db)
        if client is None:
            logger.info("  ✓ Client is None for bank2 (not in allowlist)")
        else:
            logger.error("  ✗ Client should be None for bank2")
            return False
        
        logger.info("✓ Client resolution works correctly")
        return True
    except Exception as e:
        logger.error(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config_retrieval(db):
    """Test: Retrieve current configuration."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 8: Retrieve Current Configuration")
    logger.info("=" * 60)
    try:
        config = db.repository_config.find_one({"type": "chromadb"})
        if config:
            logger.info("✓ Configuration found:")
            # Remove ObjectId for cleaner display
            config_copy = dict(config)
            config_copy['_id'] = str(config_copy['_id'])
            config_copy['created_at'] = str(config_copy.get('created_at', 'N/A'))
            config_copy['updated_at'] = str(config_copy.get('updated_at', 'N/A'))
            for key, value in config_copy.items():
                logger.info(f"    {key}: {value}")
            return True
        else:
            logger.error("✗ No configuration found")
            return False
    except Exception as e:
        logger.error(f"✗ Test failed: {e}")
        return False


def test_admin_endpoint_simulation(db):
    """Test: Simulate admin endpoint behavior."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 9: Admin Endpoint Simulation (Config Update)")
    logger.info("=" * 60)
    try:
        # Simulate admin API request to update config
        payload = {
            "type": "chromadb",
            "host": "chroma-prod.example.com",
            "port": 9000,
            "is_active": True,
            "enabled_for_all": False,
            "customers": ["bank1", "bank2", "bank3"]
        }
        
        logger.info("Simulating admin API request with payload:")
        logger.info(f"  {json.dumps(payload, indent=2)}")
        
        # Deactivate other configs of same type
        db.repository_config.update_many(
            {"type": "chromadb"},
            {"$set": {"is_active": False}}
        )
        
        # Upsert the new config
        result = db.repository_config.update_one(
            {"type": "chromadb"},
            {"$set": payload},
            upsert=True
        )
        
        logger.info(f"✓ Configuration updated (matched: {result.matched_count})")
        
        # Verify
        updated_config = db.repository_config.find_one({"type": "chromadb"})
        if updated_config and updated_config.get("host") == "chroma-prod.example.com":
            logger.info("✓ Configuration update verified")
            return True
        else:
            logger.error("✗ Configuration update verification failed")
            return False
    except Exception as e:
        logger.error(f"✗ Test failed: {e}")
        return False


def run_all_tests():
    """Run all tests."""
    logger.info("\n")
    logger.info("╔" + "=" * 58 + "╗")
    logger.info("║" + " " * 58 + "║")
    logger.info("║" + "  Per-Customer Chroma DB Management Test Suite".center(58) + "║")
    logger.info("║" + " " * 58 + "║")
    logger.info("╚" + "=" * 58 + "╝")
    
    results = {}
    
    # Test 1: Imports
    if not test_imports():
        logger.error("Cannot proceed without imports")
        return False
    results["imports"] = True
    
    # Test 2: MongoDB
    db = setup_mongodb()
    if not db:
        logger.error("Cannot proceed without MongoDB")
        return False
    results["mongodb"] = True
    
    # Test 3: Setup
    results["setup"] = setup_default_config(db)
    
    # Test 4-9: Functional tests
    results["enable_all"] = test_chroma_enabled_for_all(db)
    results["enable_specific"] = test_chroma_disabled_for_specific(db)
    results["disable_global"] = test_chroma_disabled_globally(db)
    results["get_client"] = test_get_chroma_client(db)
    results["config_retrieval"] = test_config_retrieval(db)
    results["admin_endpoint"] = test_admin_endpoint_simulation(db)
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    failed = total - passed
    
    for test_name, passed_flag in results.items():
        status = "✓ PASS" if passed_flag else "✗ FAIL"
        logger.info(f"  {status}: {test_name}")
    
    logger.info("=" * 60)
    logger.info(f"Total: {total} | Passed: {passed} | Failed: {failed}")
    logger.info("=" * 60)
    
    if failed == 0:
        logger.info("\n✓ All tests passed!")
        return True
    else:
        logger.error(f"\n✗ {failed} test(s) failed")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
