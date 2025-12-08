#!/usr/bin/env python3
"""
MongoDB configuration checker and diagnostics tool.

Usage:
    python setup_mongodb_config.py --show-env    # Display environment variables
    python setup_mongodb_config.py --test        # Test MongoDB connection
    python setup_mongodb_config.py --info        # Show connection info
"""

import os
import sys
import argparse
import json
from datetime import datetime


def display_env_vars():
    """Display current MongoDB-related environment variables."""
    print("\n" + "="*70)
    print("CURRENT MONGODB ENVIRONMENT VARIABLES")
    print("="*70)
    
    env_vars = {
        "MONGO_MODE": os.environ.get("MONGO_MODE", "(not set)"),
        "MONGO_URI": os.environ.get("MONGO_URI", "(not set)"),
        "MONGO_HOST": os.environ.get("MONGO_HOST", "(not set)"),
        "MONGO_PORT": os.environ.get("MONGO_PORT", "(not set)"),
        "MONGO_USERNAME": os.environ.get("MONGO_USERNAME", "(not set)"),
        "MONGO_PASSWORD": "****" if os.environ.get("MONGO_PASSWORD") else "(not set)",
        "DATABASE_NAME": os.environ.get("DATABASE_NAME", "(not set)"),
        "MONGO_AUTH_SOURCE": os.environ.get("MONGO_AUTH_SOURCE", "(not set)"),
        "MONGO_REPLICA_SET": os.environ.get("MONGO_REPLICA_SET", "(not set)"),
        "MONGO_SSL": os.environ.get("MONGO_SSL", "(not set)"),
    }
    
    for key, value in env_vars.items():
        status = "[SET]" if value != "(not set)" else "[NOT SET]"
        print(f"  {status:12} {key:25} = {value}")
    
    # Check if any env vars are set
    any_set = any(v != "(not set)" and k != "MONGO_PASSWORD" for k, v in env_vars.items())
    
    if any_set:
        print("\n[INFO] Environment variables are configured.")
        print("       MongoDB manager will use these settings.")
    else:
        print("\n[INFO] No environment variables set - using defaults.")
        print("       Default: mongodb://localhost:27017/ (database: finai_chatbot)")
    
    print("="*70 + "\n")
    return any_set


def test_connection():
    """Test MongoDB connection using current configuration."""
    print("\n" + "="*70)
    print("TESTING MONGODB CONNECTION")
    print("="*70 + "\n")
    
    try:
        from app.utils.mongodb_manager import (
            get_mongo_client, 
            get_database, 
            get_connection_info,
            is_mongo_enabled
        )
        
        # Check if MongoDB is enabled
        if not is_mongo_enabled():
            print("[WARNING] MongoDB is DISABLED via MONGO_MODE=disabled")
            print("          Set MONGO_MODE=enabled to enable MongoDB")
            return False
        
        print("Attempting to connect...")
        client = get_mongo_client()
        
        if client is None:
            print("[ERROR] Failed to create MongoDB client")
            return False
        
        print("[OK] Client created successfully")
        
        # Test connection
        client.server_info()
        print("[OK] Server responded to ping")
        
        # Get database
        db = get_database(client)
        if db is None:
            print("[ERROR] Could not get database")
            return False
        
        print(f"[OK] Connected to database: {db.name}")
        
        # List collections
        collections = db.list_collection_names()
        print(f"[OK] Found {len(collections)} collections")
        if collections:
            print(f"     Sample collections: {', '.join(collections[:5])}")
        
        print("\n[SUCCESS] MongoDB connection test passed!")
        return True
        
    except ImportError as e:
        print(f"[ERROR] Import failed: {e}")
        print("       Make sure you're running from the project root")
        return False
    except Exception as e:
        print(f"[ERROR] Connection test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        print("\n" + "="*70 + "\n")


def show_connection_info():
    """Display detailed connection information."""
    print("\n" + "="*70)
    print("MONGODB CONNECTION INFORMATION")
    print("="*70 + "\n")
    
    try:
        from app.utils.mongodb_manager import get_connection_info, is_mongo_enabled
        
        # Check if enabled
        enabled = is_mongo_enabled()
        print(f"Status: {'ENABLED' if enabled else 'DISABLED'}")
        
        if not enabled:
            print("\n[WARNING] MongoDB is disabled via MONGO_MODE=disabled")
            return
        
        # Get connection info
        info = get_connection_info()
        
        print(f"\nConnection Details:")
        print(f"  Mode:         {info['mode']}")
        print(f"  URI:          {info['uri']}")
        print(f"  Host:         {info['host']}")
        print(f"  Port:         {info['port']}")
        print(f"  Database:     {info['database_name']}")
        print(f"  Username:     {info['username']}")
        print(f"  Auth Source:  {info['auth_source']}")
        print(f"  Replica Set:  {info['replica_set']}")
        print(f"  SSL:          {info['ssl']}")
        print(f"  Using ENV:    {info['use_env']}")
        
        if info['use_env']:
            print("\n[INFO] Configuration source: ENVIRONMENT VARIABLES")
        else:
            print("\n[INFO] Configuration source: DEFAULT VALUES")
        
    except Exception as e:
        print(f"[ERROR] Could not get connection info: {e}")
    finally:
        print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="MongoDB configuration checker and diagnostics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show environment variables
  python setup_mongodb_config.py --show-env

  # Test MongoDB connection
  python setup_mongodb_config.py --test

  # Show connection information
  python setup_mongodb_config.py --info
        """
    )
    
    parser.add_argument(
        "--show-env",
        action="store_true",
        help="Display current MongoDB environment variables"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Test MongoDB connection"
    )
    parser.add_argument(
        "--info",
        action="store_true",
        help="Show detailed connection information"
    )
    
    args = parser.parse_args()
    
    if not any([args.show_env, args.test, args.info]):
        parser.print_help()
        sys.exit(1)
    
    success = True
    
    if args.show_env:
        display_env_vars()
    
    if args.test:
        success = test_connection() and success
    
    if args.info:
        show_connection_info()
    
    sys.exit(0 if success else 1)
