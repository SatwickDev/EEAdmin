#!/usr/bin/env python3
"""
Quick setup script to initialize Chroma configuration in MongoDB.

Usage:
    python setup_chroma_config.py --enable-all           # Enable for all customers
    python setup_chroma_config.py --customers bank1,bank2 # Enable for specific customers
    python setup_chroma_config.py --disable              # Disable globally
    python setup_chroma_config.py --show-env             # Display current environment variables
"""

import os
import sys
import argparse
import json
from datetime import datetime


def display_env_vars():
    """Display current Chroma-related environment variables."""
    print("\n" + "="*70)
    print("CURRENT ENVIRONMENT VARIABLES")
    print("="*70)
    
    env_vars = {
        "CHROMA_MODE": os.environ.get("CHROMA_MODE", "(not set)"),
        "CHROMA_ENABLED": os.environ.get("CHROMA_ENABLED", "(not set)"),
        "CHROMA_ENABLED_FOR_ALL": os.environ.get("CHROMA_ENABLED_FOR_ALL", "(not set)"),
        "CHROMA_CUSTOMERS": os.environ.get("CHROMA_CUSTOMERS", "(not set)"),
        "CHROMA_HOST": os.environ.get("CHROMA_HOST", "(not set)"),
        "CHROMA_PORT": os.environ.get("CHROMA_PORT", "(not set)"),
    }
    
    for key, value in env_vars.items():
        status = "[SET]" if value != "(not set)" else "[NOT SET]"
        print(f"  {status:12} {key:25} = {value}")
    
    # Check if any env vars are set
    any_set = any(v != "(not set)" for v in env_vars.values())
    
    if any_set:
        print("\n*** WARNING: Environment variables are SET and will take precedence over DB config!")
        print("    To use DB configuration instead, unset these environment variables.")
    else:
        print("\n[OK] No environment variables set - DB configuration will be used.")
    
    print("="*70 + "\n")
    return any_set

def setup_chroma_config(enable_all=False, customers=None, disable=False, show_env=False):
    """Setup Chroma configuration in MongoDB."""
    try:
        from app.utils.mongodb_manager import get_mongo_client, get_database
        
        # Display environment variables first
        env_vars_set = display_env_vars()
        
        if show_env:
            # Just show env vars and exit
            return True
        
        client = get_mongo_client()
        if client is None:
            print("[ERROR] Could not connect to MongoDB (may be disabled via MONGO_MODE)")
            return False
        
        db = get_database(client)
        if db is None:
            print("[ERROR] Could not get database")
            return False
        
        print(f"[OK] Connected to MongoDB")
        
        if env_vars_set:
            print("\n" + "*** WARNING "*9)
            print("*** Environment variables are set!")
            print("*** The DB configuration you're setting may be overridden by:")
            print("***   - CHROMA_MODE (highest priority)")
            print("***   - CHROMA_CUSTOMERS, CHROMA_HOST, CHROMA_PORT")
            print("*** To use DB config, unset environment variables first.")
            print("*** WARNING "*9 + "\n")
        
        if disable:
            config = {
                "type": "chromadb",
                "is_active": False,
                "enabled_for_all": False,
                "customers": [],
                "updated_at": datetime.now()
            }
            print("\nConfiguration to apply:")
            print(json.dumps({k: v for k, v in config.items() if k != "updated_at"}, indent=2))
        elif enable_all:
            config = {
                "type": "chromadb",
                "host": "localhost",
                "port": 8000,
                "is_active": True,
                "enabled_for_all": True,
                "customers": [],
                "updated_at": datetime.now()
            }
            print("\nConfiguration to apply:")
            print(json.dumps({k: v for k, v in config.items() if k != "updated_at"}, indent=2))
        elif customers:
            customer_list = [c.strip() for c in customers.split(",")]
            config = {
                "type": "chromadb",
                "host": "localhost",
                "port": 8000,
                "is_active": True,
                "enabled_for_all": False,
                "customers": customer_list,
                "updated_at": datetime.now()
            }
            print("\nConfiguration to apply:")
            print(json.dumps({k: v for k, v in config.items() if k != "updated_at"}, indent=2))
        else:
            print("[ERROR] Please specify --enable-all, --customers, or --disable")
            return False
        
        # Update or insert
        result = db.repository_config.update_one(
            {"type": "chromadb"},
            {"$set": config},
            upsert=True
        )
        
        print(f"\n[OK] Configuration applied successfully")
        print(f"  Matched: {result.matched_count}")
        print(f"  Upserted: {result.upserted_id is not None}")
        
        # Show current state
        current = db.repository_config.find_one({"type": "chromadb"})
        print("\n[OK] Current configuration in database:")
        display = {k: v for k, v in current.items() if k != "_id" and k != "updated_at"}
        print(json.dumps(display, indent=2, default=str))
        
        # Show effective configuration
        print("\n" + "="*70)
        print("EFFECTIVE CONFIGURATION (what the app will use)")
        print("="*70)
        
        chroma_mode = os.environ.get("CHROMA_MODE", "").lower()
        if chroma_mode:
            print(f"  Source: ENVIRONMENT VARIABLES (overrides DB)")
            print(f"  Mode: {chroma_mode}")
            print(f"  Customers: {os.environ.get('CHROMA_CUSTOMERS', '(none)')}")
            print(f"  Host: {os.environ.get('CHROMA_HOST', 'localhost')}")
            print(f"  Port: {os.environ.get('CHROMA_PORT', '8000')}")
        elif os.environ.get("CHROMA_ENABLED") or os.environ.get("CHROMA_ENABLED_FOR_ALL"):
            print(f"  Source: ENVIRONMENT VARIABLES (legacy flags)")
            print(f"  Enabled: {os.environ.get('CHROMA_ENABLED', 'false')}")
            print(f"  Enabled for all: {os.environ.get('CHROMA_ENABLED_FOR_ALL', 'false')}")
            print(f"  Customers: {os.environ.get('CHROMA_CUSTOMERS', '(none)')}")
        else:
            print(f"  Source: DATABASE CONFIGURATION")
            if current.get('is_active'):
                if current.get('enabled_for_all'):
                    print(f"  Mode: enabled (all customers)")
                else:
                    print(f"  Mode: allowlist")
                    print(f"  Customers: {', '.join(current.get('customers', []))}")
            else:
                print(f"  Mode: disabled")
            print(f"  Host: {current.get('host', 'localhost')}")
            print(f"  Port: {current.get('port', 8000)}")
        print("="*70 + "\n")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Setup Chroma configuration for per-customer management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Enable Chroma for all customers
  python setup_chroma_config.py --enable-all

  # Enable Chroma only for specific customers
  python setup_chroma_config.py --customers bank1,bank2,bank3

  # Disable Chroma globally
  python setup_chroma_config.py --disable
        """
    )
    
    parser.add_argument(
        "--enable-all",
        action="store_true",
        help="Enable Chroma for all customers"
    )
    parser.add_argument(
        "--customers",
        type=str,
        help="Comma-separated list of customer IDs to enable (e.g., bank1,bank2,bank3)"
    )
    parser.add_argument(
        "--disable",
        action="store_true",
        help="Disable Chroma globally"
    )
    parser.add_argument(
        "--show-env",
        action="store_true",
        help="Display current environment variables and exit"
    )
    
    args = parser.parse_args()
    
    if not any([args.enable_all, args.customers, args.disable, args.show_env]):
        parser.print_help()
        sys.exit(1)
    
    success = setup_chroma_config(
        enable_all=args.enable_all,
        customers=args.customers,
        disable=args.disable,
        show_env=args.show_env
    )
    
    sys.exit(0 if success else 1)
