#!/usr/bin/env python3
"""Direct test of conversational transaction handler logic"""

import json
from datetime import datetime

# Mock database for testing
class MockDB:
    def __init__(self):
        self.transaction_sessions = self
        self.data = {}
    
    def find_one(self, query):
        session_id = query.get('session_id')
        if session_id in self.data:
            return {'data': self.data[session_id]}
        return None
    
    def update_one(self, query, update, upsert=False):
        session_id = query.get('session_id')
        if '$set' in update:
            self.data[session_id] = update['$set']['data']

# Test the handler
def test_confirmation_flow():
    from app.utils.conversational_transaction_handler_v2 import ConversationalTransactionHandler
    
    db = MockDB()
    handler = ConversationalTransactionHandler(db)
    
    print("Testing Transaction Confirmation Flow")
    print("=" * 50)
    
    # Test context with LC data and confirmation
    context = [
        {
            "message": "Show me LC2023002",
            "response": """
            <table>
            <tr><td>LC Number</td><td>LC2023002</td></tr>
            <tr><td>Applicant</td><td>ABC Trading Ltd</td></tr>
            <tr><td>Beneficiary</td><td>XYZ Exports Inc</td></tr>
            <tr><td>Amount</td><td>50000</td></tr>
            <tr><td>Currency</td><td>USD</td></tr>
            </table>
            """
        },
        {
            "message": "Create similar LC",
            "response": """**Import Lc Transaction Summary:**

• **Lc Number:** LC2023002
• **Applicant:** ABC Trading Ltd  
• **Beneficiary:** XYZ Exports Inc
• **Amount:** 50,000.00
• **Currency:** USD

✅ **Ready to submit?**

Reply with 'Yes' to confirm or 'No' to cancel."""
        }
    ]
    
    # Test confirmation with "yes"
    print("\n1. Testing with 'yes' confirmation:")
    result = handler.process_creation_intent(
        user_query="yes confirm",
        session_id="test-session",
        user_id="test-user",
        context=context,
        repository="trade_finance"
    )
    
    print(f"Intent: {result.get('intent')}")
    print(f"Action: {result.get('action')}")
    
    if result.get('intent') == 'Form Population':
        print("SUCCESS: Form population intent detected")
        print(f"Form Data Keys: {list(result.get('form_data', {}).keys())}")
    else:
        print(f"FAILURE: Got intent '{result.get('intent')}' instead of 'Form Population'")
    
    # Test with different confirmation words
    confirmations = ["proceed", "submit", "confirm and submit", "yes proceed"]
    
    for confirm_word in confirmations:
        print(f"\n2. Testing with '{confirm_word}':")
        result = handler.process_creation_intent(
            user_query=confirm_word,
            session_id=f"test-session-{confirm_word}",
            user_id="test-user",
            context=context,
            repository="trade_finance"
        )
        
        if result.get('intent') == 'Form Population':
            print(f"  [SUCCESS] '{confirm_word}' -> Form Population")
        else:
            print(f"  [FAILURE] '{confirm_word}' -> {result.get('intent')}")

if __name__ == "__main__":
    test_confirmation_flow()