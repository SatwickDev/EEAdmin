#!/usr/bin/env python3
"""
Test minimal imports for vetting functionality
"""

import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_minimal_imports():
    """Test just the critical imports"""
    try:
        print("Testing VettingRuleEngine import...")
        
        # Mock the dependencies first
        class MockDB:
            def __init__(self):
                self.vetting_rules = MockCollection()
                self.vetting_test_results = MockCollection()
                self.vetting_llm_analyses = MockCollection()
        
        class MockCollection:
            def create_index(self, field):
                pass
        
        # Test basic imports first
        print("1. Testing basic imports...")
        import json
        import re
        from typing import Dict, List, Any, Optional, Tuple
        from datetime import datetime
        print("✓ Basic imports successful")
        
        print("2. Testing azure_openai_helper...")
        # We need to modify sys.path to import from app.utils
        sys.path.append('./app/utils')
        try:
            from azure_openai_helper import get_openai_client
            print("✓ azure_openai_helper import successful")
        except ImportError as e:
            print(f"❌ azure_openai_helper import failed: {e}")
            print("This is expected in environments without openai library")
        
        print("3. Testing vetting engine class...")
        # Import the VettingRuleEngine
        from app.utils.vetting_engine import VettingRuleEngine
        print("✓ VettingRuleEngine class import successful")
        
        print("4. Testing instantiation with mock DB...")
        mock_db = MockDB()
        engine = VettingRuleEngine(mock_db)
        print("✓ VettingRuleEngine instantiation successful")
        
        print("\n🎉 All critical imports working!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_minimal_imports()
    if success:
        print("\n✅ Minimal imports test passed!")
    else:
        print("\n❌ Minimal imports test failed!")
    sys.exit(0 if success else 1)