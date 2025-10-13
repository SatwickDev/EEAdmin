# Repository Collections Test Guide

## Overview
This guide provides comprehensive information about Treasury and Cash Management collections, including their structure, sample data, and test cases.

## Treasury Collections

### 1. **forex_transactions**
Foreign exchange transactions including spot, forward, and swap deals.

**Key Fields:**
- `transaction_id`: Unique FX transaction identifier
- `currency_pair`: Trading pair (e.g., USD/AED)
- `transaction_type`: SPOT, FORWARD, SWAP
- `exchange_rate`: FX rate applied
- `status`: CONFIRMED, PENDING, CANCELLED

### 2. **money_market**
Money market instruments and deals.

**Key Fields:**
- `deal_id`: Unique money market deal identifier
- `deal_type`: TERM_DEPOSIT, CALL_DEPOSIT, COMMERCIAL_PAPER
- `interest_rate`: Annual interest rate
- `maturity_date`: When the deal matures
- `collateral_type`: Security provided

### 3. **derivatives**
Derivative instruments for hedging and trading.

**Key Fields:**
- `trade_id`: Unique derivative trade identifier
- `product_type`: FX_OPTION, INTEREST_RATE_SWAP, etc.
- `mark_to_market`: Current MTM value
- `delta`, `gamma`, `vega`: Greek risk measures

### 4. **investments**
Investment portfolio holdings.

**Key Fields:**
- `investment_id`: Unique investment identifier
- `isin`: International Securities Identification Number
- `asset_class`: GOVERNMENT_BOND, CORPORATE_BOND, etc.
- `unrealized_pnl`: Current profit/loss
- `rating`: Credit rating

### 5. **hedging_instruments**
Risk management hedging positions.

**Key Fields:**
- `hedge_id`: Unique hedge identifier
- `hedge_type`: FAIR_VALUE_HEDGE, CASH_FLOW_HEDGE
- `hedge_effectiveness`: Effectiveness percentage
- `accounting_treatment`: Accounting method used

## Cash Management Collections

### 1. **cash_transactions**
Daily cash movements and transactions.

**Key Fields:**
- `transaction_id`: Unique cash transaction identifier
- `transaction_type`: INCOMING_WIRE, OUTGOING_ACH, CHECK_DEPOSIT
- `debit_amount`/`credit_amount`: Transaction amounts
- `balance`: Account balance after transaction
- `category`: TRADE_RECEIPTS, PAYROLL, etc.

### 2. **liquidity_reports**
Real-time liquidity position snapshots.

**Key Fields:**
- `report_id`: Unique report identifier
- `total_cash_balance`: Total available cash
- `available_balance`: Usable balance
- `buffer_amount`: Excess over minimum requirement
- `report_type`: MORNING_SNAPSHOT, AFTERNOON_UPDATE

### 3. **cash_forecasts**
Cash flow projections and forecasts.

**Key Fields:**
- `forecast_id`: Unique forecast identifier
- `forecast_period`: DAILY, WEEKLY, MONTHLY
- `expected_receipts`/`expected_payments`: Projected flows
- `confidence_level`: Forecast accuracy percentage
- `variance_from_actual`: Historical accuracy

### 4. **payment_orders**
Payment instructions and orders.

**Key Fields:**
- `order_id`: Unique payment order identifier
- `payment_type`: WIRE_TRANSFER, LOCAL_TRANSFER
- `urgency`: NORMAL, URGENT
- `approval_status`: Workflow status
- `status`: PENDING_APPROVAL, EXECUTED, REJECTED

### 5. **cash_pooling**
Cash concentration and pooling structures.

**Key Fields:**
- `pool_id`: Unique pool identifier
- `pool_type`: ZERO_BALANCING, TARGET_BALANCING
- `sweep_amount`: Amount to be swept
- `sweep_direction`: TO_HEADER, FROM_HEADER
- `interest_rate`: Pool interest rate

## Test Cases

### Treasury Test Scenarios

1. **Forex Trading Analysis**
   ```
   Query: "Show me all forex transactions for USD/AED in January 2024"
   Expected: Returns spot and forward deals with rates and status
   ```

2. **Money Market Monitoring**
   ```
   Query: "What are the active money market deposits with interest rate above 5%?"
   Expected: Returns high-yield deposits with maturity details
   ```

3. **Derivative Risk Assessment**
   ```
   Query: "List all FX options expiring in Q1 2024"
   Expected: Returns options with strike prices and premiums
   ```

4. **Investment Portfolio Review**
   ```
   Query: "Show me government bonds in our investment portfolio"
   Expected: Returns bonds with ratings and unrealized P&L
   ```

5. **Hedge Effectiveness Check**
   ```
   Query: "Show hedge effectiveness for Q1 2024"
   Expected: Returns hedges with effectiveness percentages
   ```

### Cash Management Test Scenarios

1. **Daily Cash Position**
   ```
   Query: "What is our current liquidity position?"
   Expected: Returns latest liquidity report with balances and buffer
   ```

2. **Payment Processing**
   ```
   Query: "List all pending payment orders requiring approval"
   Expected: Returns orders with amounts and approval status
   ```

3. **Cash Forecasting**
   ```
   Query: "Show cash forecast for next week"
   Expected: Returns weekly forecast with major inflows/outflows
   ```

4. **Transaction Analysis**
   ```
   Query: "What were the total payroll payments this month?"
   Expected: Returns payroll transactions with amounts
   ```

5. **Cash Pooling Review**
   ```
   Query: "Show cash pooling sweep activities for USD accounts"
   Expected: Returns sweep amounts and interest calculations
   ```

## Integration Test Workflows

### 1. **Cross-Repository Query Test**
```
Scenario: User needs to check forex exposure and cash availability
Steps:
1. Connect to Treasury repository
2. Query: "Show all forward forex deals maturing this week"
3. Disconnect Treasury, Connect to Cash Management
4. Query: "What is our USD liquidity position?"
5. Verify only relevant repository data is returned
```

### 2. **Repository Switching Test**
```
Scenario: Verify clean repository switching
Steps:
1. Connect to Treasury
2. Run query: "Show all derivatives"
3. Switch to Cash Management (Treasury auto-disconnects)
4. Run query: "Show all derivatives"
5. Verify: Should return no results or error (derivatives only in Treasury)
```

### 3. **Collection-Specific Query Test**
```
Scenario: Test specific collection targeting
Steps:
1. Connect to Cash Management
2. Query with collection reference: "[cash:payment_orders] Show urgent payments"
3. Verify only payment_orders collection is searched
4. Query without reference: "Show urgent payments"
5. Verify it searches the appropriate collection based on context
```

## Backend Integration Points

### Query Processing Flow:
1. User connects to repository (e.g., Treasury)
2. Frontend sends repository state to `/api/repositories/active`
3. Backend stores active repository for user
4. User sends query
5. Backend checks active repository
6. `generate_rag_table_or_report_request` uses appropriate collection
7. Results returned from selected repository only

### Key Backend Functions:
- `get_collection_for_repository()`: Maps repository to collection
- `active_user_repositories`: Stores user-repository mappings
- Collection filtering in ChromaDB queries

## Validation Checklist

- [ ] Only one repository can be connected at a time
- [ ] Switching repositories disconnects the previous one
- [ ] Queries return data only from connected repository
- [ ] Collection references work correctly
- [ ] Repository state persists across page refreshes
- [ ] Context indicator shows active repository
- [ ] Disconnecting clears repository context
- [ ] Backend correctly filters ChromaDB collections
- [ ] Error handling for non-existent collections
- [ ] Performance with large result sets

## Sample ChromaDB Data Structure

```python
# For Treasury - forex_transactions
{
    "documents": [
        "transaction_id: FX2024001234\ncurrency_pair: USD/AED\nexchange_rate: 3.673\n...",
        "transaction_id: FX2024001235\ncurrency_pair: EUR/USD\nexchange_rate: 1.09\n..."
    ],
    "metadatas": [
        {"source": "treasury", "type": "forex", "date": "2024-01-15"},
        {"source": "treasury", "type": "forex", "date": "2024-01-15"}
    ],
    "ids": ["fx_001234", "fx_001235"]
}
```

## Testing Commands

### API Testing:
```bash
# Set active repository
curl -X POST http://localhost:5000/api/repositories/active \
  -H "Content-Type: application/json" \
  -d '{"active_repository": "treasury", "user_id": "test_user"}'

# Get repository collections
curl http://localhost:5000/api/repositories/treasury/collections

# Query with active repository
curl -X POST http://localhost:5000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Show all forex transactions", "user_id": "test_user"}'
```