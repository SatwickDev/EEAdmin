#!/usr/bin/env python3
"""
Check if routes are properly registered
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def check_routes():
    """Check route registration"""
    try:
        print("Creating Flask app...")
        from app import create_app
        
        app = create_app()
        print("✓ Flask app created successfully")
        
        print("\nRegistered routes:")
        for rule in app.url_map.iter_rules():
            if 'vetting' in rule.rule:
                print(f"  {rule.methods} {rule.rule} -> {rule.endpoint}")
        
        print("\nLooking for debug route...")
        debug_routes = [rule for rule in app.url_map.iter_rules() if 'debug' in rule.rule]
        if debug_routes:
            for route in debug_routes:
                print(f"  ✓ Debug route found: {route.methods} {route.rule}")
        else:
            print("  ❌ No debug route found")
        
        print("\nTotal routes registered:", len(list(app.url_map.iter_rules())))
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = check_routes()
    if success:
        print("\n✅ Route check completed")
        sys.exit(0)
    else:
        print("\n❌ Route check failed")
        sys.exit(1)