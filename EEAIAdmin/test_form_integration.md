# Trade Finance Form and Chatbot Integration Test Guide

## Overview
This guide describes how to test the bidirectional data flow between the Trade Finance LC Form and the AI Chatbot.

## Test Scenarios

### Scenario 1: Chatbot to Form Population (Transaction Confirmation)

1. **Open the Trade Finance LC Form**
   - Navigate to `/trade_finance_lc_form`
   - The form should load with empty fields

2. **Open the AI Chatbot**
   - Click the chatbot icon in the bottom right corner
   - The chatbot should open in an overlay

3. **Request Transaction Creation**
   - Type: "show me expired import lc transaction"
   - Wait for the response showing expired transactions
   - Type: "create similar transaction"
   - If multiple LCs are shown, select one (e.g., "LC2023002")

4. **Modify Transaction Data**
   - Type: "change the bene name to ilyas and currency 100000000"
   - The chatbot should show updated transaction summary

5. **Confirm Transaction**
   - Type: "yes" or "confirm"
   - Expected Result:
     - Chatbot responds with success message
     - Form fields automatically populate with the transaction data
     - Fields highlight briefly in blue
     - Success message appears on the form

### Scenario 2: Form to Chatbot Context (Reading Form Data)

1. **Fill Some Form Fields**
   - Enter data in various form fields:
     - LC Number: TEST123
     - Applicant: Test Company
     - Beneficiary: Test Supplier
     - Amount: 50000
     - Currency: USD

2. **Open the Chatbot**
   - Click the chatbot icon
   - The chatbot should receive the form context
   - Look for "Form data available (X fields)" indicator

3. **Ask About Form Data**
   - Type: "what is the current beneficiary in the form?"
   - Expected: Chatbot should respond with "Test Supplier"
   - Type: "what's the amount and currency?"
   - Expected: Chatbot should respond with "50000 USD"

### Scenario 3: Smart Capture Integration

1. **Use Smart Capture**
   - Click "Start Smart Capture" button on the form
   - Upload a document with LC information
   - Process the document

2. **Verify Form Population**
   - Fields should populate from the document
   - Success message should appear

### Scenario 4: Error Handling

1. **Test Invalid Confirmation**
   - In chatbot, try to confirm without transaction data
   - Type: "yes"
   - Expected: Appropriate error or guidance message

2. **Test Incomplete Data**
   - Create a transaction with missing required fields
   - Try to confirm
   - Expected: Request for missing information

## Implementation Details

### Key Components Modified

1. **Frontend (JavaScript)**
   - `ai-chat.js`: Added `populateTradeFinanceForm()` function and form context handling
   - `trade_finance_lc_form.html`: Added message handlers and form data extraction

2. **Backend (Python)**
   - `conversational_transaction_handler_v2.py`: Modified to return form data on confirmation

### Data Flow

#### Chatbot → Form
1. User confirms transaction in chatbot
2. Backend returns `form_data` in response
3. `ai-chat.js` detects `form_data` and calls `populateTradeFinanceForm()`
4. Function sends PostMessage to parent window
5. Form receives message and populates fields

#### Form → Chatbot
1. Form sends current data via PostMessage when chatbot opens
2. `ai-chat.js` receives and stores form context
3. Context included in API requests to backend
4. Backend can reference form data in responses

## Troubleshooting

### Form Not Populating
- Check browser console for errors
- Verify PostMessage is being sent (console.log statements)
- Ensure form field IDs match the mapping

### Chatbot Not Reading Form Data
- Verify form context is being sent (check console)
- Ensure sessionStorage contains form data
- Check if form_context is included in API request

### Field Mapping Issues
- Review field mapping in `populateFormFromTransaction()`
- Ensure backend sends correct field names
- Check date format conversion for date fields

## Future Enhancements

1. **Real-time Sync**: Update chatbot when form fields change
2. **Validation Feedback**: Show validation errors in chatbot
3. **Multi-form Support**: Extend to other trade finance forms
4. **Draft Recovery**: Restore incomplete transactions
5. **Audit Trail**: Track all form interactions via chatbot