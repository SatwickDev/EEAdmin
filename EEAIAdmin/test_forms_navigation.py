#!/usr/bin/env python3
"""Test script to verify trade finance forms navigation and chatbot popup"""

import requests
import sys

# Base URL - adjust if your server runs on a different port
BASE_URL = "http://localhost:5001"

def test_routes():
    """Test all form routes"""
    routes_to_test = [
        ("/forms_dashboard", "Forms Dashboard"),
        ("/trade_finance_lc_form", "Trade Finance - Import Letter of Credit"),
        ("/trade_finance_guarantee_form", "Trade Finance - Bank Guarantee"),
        ("/components/ai_chatbot_popup", "AI Assistant"),
    ]
    
    print("Testing Form Routes:")
    print("-" * 50)
    
    all_passed = True
    
    for route, expected_title in routes_to_test:
        try:
            response = requests.get(BASE_URL + route, timeout=5)
            if response.status_code == 200:
                if expected_title in response.text:
                    print(f"[PASS] {route} - OK (Title found)")
                else:
                    print(f"[WARN] {route} - Response OK but title not found")
                    all_passed = False
            else:
                print(f"[FAIL] {route} - Failed (Status: {response.status_code})")
                all_passed = False
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] {route} - Error: {str(e)}")
            all_passed = False
    
    print("-" * 50)
    if all_passed:
        print("[SUCCESS] All tests passed!")
    else:
        print("[WARNING] Some tests failed. Please check the routes.")
    
    return all_passed

if __name__ == "__main__":
    success = test_routes()
    sys.exit(0 if success else 1)