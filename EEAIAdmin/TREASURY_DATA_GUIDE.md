# Treasury Collections Data Guide

## Overview
The Treasury repository contains 5 collections with comprehensive financial data:

## 1. **forex_transactions** (10 documents)
Foreign exchange spot, forward, and swap transactions

### Sample Records:
- **EUR Transactions**: 5 records (EUR/USD, EUR/GBP, EUR/CHF, EUR/JPY)
- **USD Transactions**: 3 records (USD/AED, USD/EUR, USD/GBP)
- **GBP Transactions**: 2 records (GBP/USD, GBP/EUR)

### Key Fields:
- `transaction_id`, `currency_pair`, `exchange_rate`, `transaction_type` (SPOT/FORWARD/SWAP)
- `buy_amount`, `sell_amount`, `status` (CONFIRMED/SETTLED)

### Example Queries:
```
- "Show all EUR forex transactions"
- "List forward contracts"
- "Display USD/AED spot deals"
```

## 2. **money_market** (6 documents)
Short-term borrowing and lending instruments

### Instrument Types:
- Term Deposits (USD, EUR)
- Call Deposits (EUR)
- Commercial Paper (GBP)
- Repo Agreements (EUR)
- Certificates of Deposit (JPY)

### Key Fields:
- `deal_id`, `deal_type`, `principal_amount`, `interest_rate`
- `maturity_date`, `currency`, `status` (ACTIVE)

### Example Queries:
```
- "Show active term deposits"
- "List money market deals in EUR"
- "Display deals with interest rate above 5%"
```

## 3. **derivatives** (5 documents)
Options, swaps, and forward contracts

### Product Types:
- FX Options (EUR/USD Call, GBP/USD Put)
- Interest Rate Swap (EUR 100M)
- Currency Swap (EUR/GBP)
- FX Forward (EUR/CHF)

### Key Fields:
- `trade_id`, `product_type`, `notional_amount`, `expiry_date`
- `strike_price` (for options), `status` (OPEN/ACTIVE)

### Example Queries:
```
- "Show all FX options"
- "List derivatives expiring in 2024"
- "Display EUR denominated derivatives"
```

## 4. **investments** (8 documents)
Bond and security holdings

### EUR Investments (5):
- European Investment Bank Bond 2029
- German Bund 10Y
- French OAT 2030
- Italian BTP 2028
- Spanish Bonos 2032

### Other Currency Investments:
- US Treasury Note 5Y (USD)
- Microsoft Corp Bond 2027 (USD)
- UK Gilt 2030 (GBP)

### Key Fields:
- `investment_id`, `isin`, `security_name`, `asset_class`
- `face_value`, `currency`, `rating`, `maturity_date`

### Example Queries:
```
- "Show all EUR denominated investments"
- "List government bonds"
- "Display investments with AAA rating"
```

## 5. **hedging_instruments** (4 documents)
Risk management positions

### Hedge Types:
- Fair Value Hedge (EUR Bond Portfolio, USD Corporate Bonds)
- Cash Flow Hedge (EUR/USD Sales Forecast)
- Net Investment Hedge (UK Subsidiary)

### Key Fields:
- `hedge_id`, `hedge_type`, `hedged_item`, `notional_amount`
- `hedge_effectiveness` (%), `status` (EFFECTIVE)

### Example Queries:
```
- "Show all active hedges"
- "List EUR hedging instruments"
- "Display hedge effectiveness above 95%"
```

## How to Populate Data

1. **Via Browser Console**:
```javascript
// Copy and paste this into browser console
fetch('/api/test/populate-treasury', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'}
})
.then(response => response.json())
.then(data => console.log('Treasury data populated:', data));
```

2. **Using the Script**:
```javascript
// Load and run the population script
populateTreasuryData();
```

## Testing Treasury Queries

After populating data:

1. Connect to Treasury repository
2. Try these queries:
   - "Show all EUR denominated investments" → Should return 5 bonds
   - "List forex transactions" → Should return 10 FX deals
   - "Display money market deposits" → Should return 6 MM instruments
   - "Show derivatives portfolio" → Should return 5 derivative trades
   - "List active hedges" → Should return 4 hedging instruments

## Data Highlights

- **Total Documents**: 33 across all collections
- **Currencies**: EUR, USD, GBP, JPY, CHF, AED
- **Date Range**: 2023-2024 historical, up to 2034 for maturities
- **EUR Focus**: Heavy emphasis on EUR instruments per request
- **Status**: Mix of ACTIVE, CONFIRMED, SETTLED, OPEN positions