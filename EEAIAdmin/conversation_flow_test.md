# Complete Conversational Transaction Flow - Test Guide

## Overview
This guide explains the complete conversation-based flow for creating transactions through the chatbot with proper user confirmation before form population.

## Key Changes Implemented

### 1. **No Auto-Population on Confirmation**
- When user confirms a transaction with "yes", the form is NOT automatically populated
- Instead, the chatbot asks if the user wants to populate the form
- Only when user explicitly requests (e.g., "populate form", "fill form"), the data is populated

### 2. **Bidirectional Data Sync**
- Form automatically sends its current data to chatbot when:
  - Chatbot window opens
  - User changes form fields (with 1-second debounce)
  - User leaves a field (blur event)
- Chatbot can reference current form data in responses

## Complete Conversation Flow

### Step 1: Request Expired Transactions
**User:** "show me expired import lc transaction"

**Chatbot Response:** 
- Shows table with expired LC transactions
- Displays LC2023002, LC2024002, etc.

### Step 2: Create Similar Transaction
**User:** "create similar transaction"

**Chatbot Response:**
- If multiple LCs shown: "There are multiple expired Import LCs available. Please specify which LC you would like to create a similar transaction for: LC2023002 or LC2024002."
- If single LC: Proceeds to next step

### Step 3: Select Specific Transaction
**User:** "LC2023002"

**Chatbot Response:**
- Shows transaction summary with all details
- "✅ Ready to submit? Reply with 'Yes' to confirm or 'No' to cancel."

### Step 4: Modify Transaction (Optional)
**User:** "change the bene name to ilyas and amount to 100000000"

**Chatbot Response:**
- Updates the transaction summary with new values
- Shows updated summary
- "✅ Ready to submit? Reply with 'Yes' to confirm or 'No' to cancel."

### Step 5: Confirm Transaction
**User:** "yes" or "confirm"

**Chatbot Response:**
- "✅ **Transaction confirmed successfully!**
  
  The transaction has been created. Would you like to populate this data into the form?
  
  Reply 'populate' or 'fill form' to auto-fill the form fields."

### Step 6: Request Form Population
**User:** "populate" or "fill form" or "yes"

**Chatbot Response:**
- "✅ **Transaction successfully created!**
  
  The form has been populated with the transaction data."

**Form Behavior:**
- Fields automatically populate with transaction data
- Fields highlight briefly in blue
- Success message appears at top of form
- Page scrolls to top

## Alternative Flows

### Skip Form Population
After Step 5, if user says:
**User:** "no" or "skip" or "later"

**Chatbot Response:**
- "Transaction saved. You can continue with other tasks."
- Form remains unchanged

### Direct Form Field Query
With form partially filled:
**User:** "what is the current beneficiary in the form?"

**Chatbot Response:**
- Reads the current form data
- "The current beneficiary in the form is: [actual value from form]"

## Backend Implementation Details

### Session Management
- Transaction data stored in session after confirmation
- `awaiting_population` flag tracks if user needs to decide on population
- Session cleared after population decision

### Process Flow
1. User confirms → `awaiting_population = True`
2. User requests population → `awaiting_population = False`, form data returned
3. User skips population → `awaiting_population = False`, no form data

## Frontend Implementation Details

### Form → Chatbot Sync
- `getCurrentFormData()`: Extracts all form field values
- `sendFormContextToChatbot()`: Sends data via PostMessage
- Automatic sync on field changes (debounced)

### Chatbot → Form Population
- Only populates when `data.form_data` present AND `!data.awaiting_form_population`
- Uses field mapping for proper population
- Visual feedback with highlighting

## Testing Checklist

### Conversation Flow Test
- [ ] Request expired transactions
- [ ] Select specific transaction
- [ ] Modify transaction data
- [ ] Confirm transaction (check NO auto-population)
- [ ] Explicitly request form population
- [ ] Verify form populates correctly

### Form Sync Test
- [ ] Fill form fields manually
- [ ] Open chatbot
- [ ] Ask about current form values
- [ ] Verify chatbot reads correct values

### Edge Cases
- [ ] Confirm without transaction data
- [ ] Skip form population after confirmation
- [ ] Multiple confirmation requests
- [ ] Change form while chatbot is open

## Troubleshooting

### Form Not Populating
1. Check console for "User requested form population" log
2. Verify `awaiting_form_population` is false
3. Check field mapping matches form field IDs

### Chatbot Not Reading Form
1. Verify `sendFormContextToChatbot()` is called
2. Check console for "Form context sent" log
3. Ensure chatbot iframe is loaded

### Session Issues
1. Check MongoDB for session data
2. Verify session_id consistency
3. Check `_save_transaction_session()` calls

## Benefits of This Approach

1. **User Control**: User explicitly controls when form is populated
2. **Conversation Continuity**: Natural conversation flow without surprises
3. **Data Verification**: User can review before populating
4. **Flexibility**: Can continue conversation without affecting form
5. **Bidirectional Sync**: Chatbot aware of form state at all times