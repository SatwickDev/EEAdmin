#!/usr/bin/env python3
"""
Focused test for the OpenAI helper function
"""

import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_openai_helper():
    """Test just the OpenAI helper function"""
    try:
        print("Testing azure_openai_helper import...")
        
        # Test the specific function import that was failing
        sys.path.append('./app/utils')
        from azure_openai_helper import get_openai_client
        print("✓ get_openai_client import successful")
        
        print("\nTesting get_openai_client function...")
        client = get_openai_client()
        print("✓ get_openai_client function works")
        print(f"  Client type: {type(client)}")
        
        # Test that the client has the expected attributes
        if hasattr(client, 'chat'):
            print("✓ Client has 'chat' attribute")
        else:
            print("❌ Client missing 'chat' attribute")
        
        if hasattr(client.chat, 'completions'):
            print("✓ Client has 'chat.completions' attribute")
        else:
            print("❌ Client missing 'chat.completions' attribute")
        
        print("\n🎉 OpenAI helper function working correctly!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ General error: {e}")
        return False

if __name__ == "__main__":
    success = test_openai_helper()
    if success:
        print("\n✅ OpenAI helper test passed!")
        sys.exit(0)
    else:
        print("\n❌ OpenAI helper test failed")
        sys.exit(1)