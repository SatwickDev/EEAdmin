#!/usr/bin/env python3
"""Test script for transaction confirmation and form population flow"""

import requests
import json
import time

# Base URL for the API
BASE_URL = "http://localhost:5001"

# Test session and user
session_id = "test-session-123"
user_id = "test-user"

def send_chat_message(message, context=None):
    """Send a message to the chatbot API"""
    payload = {
        "message": message,
        "session_id": session_id,
        "user_id": user_id,
        "context": context or [],
        "repository": "trade_finance"
    }
    
    response = requests.post(f"{BASE_URL}/api/chat", json=payload)
    return response.json()

def test_transaction_flow():
    """Test the complete transaction flow"""
    print("=" * 60)
    print("Testing Transaction Confirmation and Form Population Flow")
    print("=" * 60)
    
    context = []
    
    # Step 1: Start with a transaction request
    print("\n1. Requesting to create a similar LC...")
    message1 = "I want to create a similar LC to LC2023002"
    response1 = send_chat_message(message1, context)
    print(f"Response: {json.dumps(response1, indent=2)}")
    
    # Add to context
    context.append({
        "message": message1,
        "response": response1.get("response", "")
    })
    
    time.sleep(1)
    
    # Step 2: Provide LC details (simulate having LC data in context)
    print("\n2. Simulating LC data in context...")
    lc_data_context = {
        "message": "Show me LC2023002 details",
        "response": """Here are the details for LC2023002:
        
        <table>
        <tr><td>LC Number</td><td>LC2023002</td></tr>
        <tr><td>Applicant</td><td>ABC Trading Ltd</td></tr>
        <tr><td>Beneficiary</td><td>XYZ Exports Inc</td></tr>
        <tr><td>Amount</td><td>50000</td></tr>
        <tr><td>Currency</td><td>USD</td></tr>
        <tr><td>Issue Date</td><td>2023-06-15</td></tr>
        <tr><td>Expiry Date</td><td>2025-12-31</td></tr>
        <tr><td>Country</td><td>USA</td></tr>
        <tr><td>Product Type</td><td>Electronics</td></tr>
        <tr><td>Status</td><td>Active</td></tr>
        </table>"""
    }
    context.append(lc_data_context)
    
    # Step 3: Request to create similar with the data
    print("\n3. Requesting to create similar LC with data...")
    message3 = "Create a similar LC with this data"
    response3 = send_chat_message(message3, context)
    print(f"Response: {json.dumps(response3, indent=2)}")
    
    # Add to context
    context.append({
        "message": message3,
        "response": response3.get("response", "")
    })
    
    time.sleep(1)
    
    # Step 4: Confirm the transaction
    print("\n4. Confirming the transaction...")
    message4 = "yes confirm"
    response4 = send_chat_message(message4, context)
    print(f"Response Intent: {response4.get('intent')}")
    print(f"Response Action: {response4.get('action')}")
    
    # Check if we got form population data
    if response4.get("intent") == "Form Population":
        print("\n✅ SUCCESS: Form population intent detected!")
        print(f"Form Type: {response4.get('form_type')}")
        print(f"Form Data: {json.dumps(response4.get('form_data', {}), indent=2)}")
        
        if response4.get("action_buttons"):
            print("\nAction buttons available:")
            for button in response4["action_buttons"]:
                print(f"  - {button['label']}: {button['action']}")
    else:
        print(f"\n❌ FAILURE: Expected 'Form Population' intent but got '{response4.get('intent')}'")
    
    print("\n" + "=" * 60)
    print("Test completed")
    print("=" * 60)

if __name__ == "__main__":
    try:
        # Wait a moment for server to be ready
        time.sleep(2)
        test_transaction_flow()
    except requests.exceptions.ConnectionError:
        print("Error: Cannot connect to Flask server at http://localhost:5001")
        print("Please ensure the Flask app is running (python run.py)")
    except Exception as e:
        print(f"Error: {e}")