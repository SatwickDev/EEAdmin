#!/usr/bin/env python3
"""
Test script to verify vetting engine imports work correctly
"""

import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all vetting engine imports work"""
    try:
        print("Testing azure_openai_helper import...")
        from app.utils.azure_openai_helper import get_openai_client
        print("✓ azure_openai_helper import successful")
        
        print("\nTesting get_openai_client function...")
        client = get_openai_client()
        print("✓ get_openai_client function works")
        
        print("\nTesting vetting_engine import...")
        from app.utils.vetting_engine import VettingRuleEngine
        print("✓ vetting_engine import successful")
        
        print("\nTesting VettingRuleEngine instantiation...")
        # Mock db object for testing
        class MockDB:
            def __init__(self):
                self.vetting_rules = MockCollection()
                self.vetting_test_results = MockCollection()
                self.vetting_llm_analyses = MockCollection()
        
        class MockCollection:
            def create_index(self, field):
                pass
        
        mock_db = MockDB()
        engine = VettingRuleEngine(mock_db)
        print("✓ VettingRuleEngine instantiation successful")
        
        print("\n🎉 All imports and basic functionality working correctly!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ General error: {e}")
        return False

if __name__ == "__main__":
    success = test_imports()
    if success:
        print("\n✅ Test passed - vetting engine is ready to use!")
        sys.exit(0)
    else:
        print("\n❌ Test failed - please check the error messages above")
        sys.exit(1)