# Intent Classification Enhancement - Implementation Summary

## Overview
Enhanced the intent classification system to use LLM-based classification with repository context awareness. This resolves the issue where repository queries were being incorrectly classified as "User Manual" intent.

## Changes Made

### 1. Added LLM-based Intent Classification Function
**File**: `/app/utils/gpt_utils.py`
- Added `classify_query_intent_with_llm()` function that:
  - Uses OpenAI to classify query intents
  - Takes repository context into account
  - Prioritizes data-related intents when a repository is connected
  - Returns intent, output format, and confidence score

### 2. Updated Query Processing Logic
**File**: `/app/utils/query_utils.py`
- Modified `process_user_query()` to:
  - Accept `active_repository` parameter
  - Use LLM classification when repository is active
  - Override intent for data queries with confidence > 75%
  - Return repository-aware responses

### 3. Enhanced Route Handler
**File**: `/app/routes.py`
- Updated the query route to:
  - Pass active repository to query processing
  - Already had logic to check active repository and force Table Request for data keywords
  - Now integrates with the enhanced LLM classification

## How It Works

1. **When a repository is connected** (Treasury, Cash Management, or Trade Finance):
   - The system knows which data collections to query
   - LLM classifier is given repository context
   - Data-related queries are prioritized as "Table Request" or "Report"
   - User Manual intent is only used for actual help/documentation queries

2. **Intent Classification Priority**:
   - If repository is active AND query contains data keywords → Table Request
   - If query explicitly asks for help/guidance → User Manual
   - Otherwise → Use standard LLM classification

3. **Confidence-based Override**:
   - LLM returns a confidence score (0-100)
   - If confidence > 75% and repository is active, use LLM's classification
   - This prevents false User Manual classifications for data queries

## Example Scenarios

### Before Enhancement:
- User connects to Treasury repository
- Query: "show forex transactions"
- Result: Incorrectly classified as "User Manual"

### After Enhancement:
- User connects to Treasury repository
- Query: "show forex transactions"
- Result: Correctly classified as "Table Request"
- System queries forex_transactions collection

## Benefits

1. **Improved Accuracy**: Repository context ensures data queries are handled correctly
2. **Better UX**: Users get data results instead of help documentation
3. **Flexible Classification**: LLM adapts to various query phrasings
4. **Confidence Scoring**: System can gauge reliability of classification

## Testing

Created test scripts to verify:
- Intent classification logic works correctly
- Repository context overrides manual intent for data queries
- Various query patterns are handled appropriately

## Next Steps

1. Monitor classification accuracy in production
2. Fine-tune confidence thresholds if needed
3. Add more repository-specific keywords if required
4. Consider caching common query patterns for performance