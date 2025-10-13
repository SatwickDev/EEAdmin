"""
Test script to verify the conversation flow works correctly
"""
import requests
import json
import time

# Configuration
BASE_URL = "http://localhost:5001"
USER_ID = "test_user_123"
SESSION_ID = f"test_session_{int(time.time())}"

def send_query(query, session_id=SESSION_ID, user_id=USER_ID):
    """Send a query to the chatbot"""
    url = f"{BASE_URL}/query"
    payload = {
        "query": query,
        "session_id": session_id,
        "user_id": user_id,
        "repository_context": "Trade Finance Repository"
    }
    
    print(f"\n[USER]: {query}")
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        data = response.json()
        print(f"[BOT]: {data.get('response', 'No response')[:200]}...")
        if data.get('awaiting_form_population'):
            print("[STATUS]: Awaiting form population decision")
        if data.get('form_data'):
            print(f"[FORM DATA]: {json.dumps(data.get('form_data'), indent=2)}")
        return data
    else:
        print(f"[ERROR]: {response.status_code} - {response.text}")
        return None

def test_conversation_flow():
    """Test the complete conversation flow"""
    print("=" * 60)
    print("Testing Conversation Flow for Transaction Creation")
    print("=" * 60)
    
    # Step 1: Request expired transactions
    print("\nStep 1: Requesting expired transactions...")
    response = send_query("show me expired import lc transaction")
    time.sleep(1)
    
    # Step 2: Create similar transaction
    print("\nStep 2: Creating similar transaction...")
    response = send_query("create similar transaction")
    time.sleep(1)
    
    # Step 3: Select specific LC
    print("\nStep 3: Selecting LC2024002...")
    response = send_query("LC2024002")
    time.sleep(1)
    
    # Step 4: Confirm transaction
    print("\nStep 4: Confirming transaction...")
    response = send_query("yes")
    time.sleep(1)
    
    # Check if we got the awaiting_form_population flag
    if response and response.get('awaiting_form_population'):
        print("\n✓ Correctly waiting for population request (not auto-populating)")
        
        # Step 5: Request form population
        print("\nStep 5: Requesting form population...")
        response = send_query("populate")
        
        # Check if form data was returned
        if response and response.get('form_data'):
            print("\n✓ Form data returned successfully!")
            print("Form would be populated with this data.")
        else:
            print("\n✗ No form data returned")
    else:
        print("\n✗ Transaction was auto-populated (should wait for explicit request)")
    
    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60)

if __name__ == "__main__":
    # Wait a moment for server to be ready
    print("Starting test in 2 seconds...")
    time.sleep(2)
    
    try:
        test_conversation_flow()
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()