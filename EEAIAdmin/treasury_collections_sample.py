"""
Treasury Collections Structure and Sample Data
"""

# Treasury Collections Configuration
TREASURY_COLLECTIONS = {
    "forex_transactions": {
        "description": "Foreign Exchange transactions including spot, forward, and swap deals",
        "fields": [
            "transaction_id", "transaction_date", "value_date", "currency_pair",
            "buy_currency", "sell_currency", "buy_amount", "sell_amount",
            "exchange_rate", "transaction_type", "client_name", "client_id",
            "dealer_name", "status", "settlement_instructions", "purpose_code"
        ],
        "sample_data": [
            {
                "transaction_id": "FX2024001234",
                "transaction_date": "2024-01-15",
                "value_date": "2024-01-17",
                "currency_pair": "USD/AED",
                "buy_currency": "USD",
                "sell_currency": "AED",
                "buy_amount": 1000000.00,
                "sell_amount": 3673000.00,
                "exchange_rate": 3.673,
                "transaction_type": "SPOT",
                "client_name": "ABC Trading LLC",
                "client_id": "CL123456",
                "dealer_name": "John Smith",
                "status": "CONFIRMED",
                "settlement_instructions": "NOSTRO: JPM NY, VOSTRO: NBD Dubai",
                "purpose_code": "TRADE"
            },
            {
                "transaction_id": "FX2024001235",
                "transaction_date": "2024-01-15",
                "value_date": "2024-04-15",
                "currency_pair": "EUR/USD",
                "buy_currency": "EUR",
                "sell_currency": "USD",
                "buy_amount": 500000.00,
                "sell_amount": 545000.00,
                "exchange_rate": 1.09,
                "transaction_type": "FORWARD",
                "client_name": "XYZ Manufacturing",
                "client_id": "CL789012",
                "dealer_name": "Sarah Johnson",
                "status": "CONFIRMED",
                "settlement_instructions": "NOSTRO: DB Frankfurt, VOSTRO: Citi NY",
                "purpose_code": "HEDGE"
            }
        ]
    },
    
    "money_market": {
        "description": "Money market deals including deposits, loans, and commercial papers",
        "fields": [
            "deal_id", "deal_date", "start_date", "maturity_date", "deal_type",
            "counterparty", "principal_amount", "currency", "interest_rate",
            "interest_basis", "interest_amount", "maturity_amount", "status",
            "collateral_type", "collateral_value"
        ],
        "sample_data": [
            {
                "deal_id": "MM2024001001",
                "deal_date": "2024-01-10",
                "start_date": "2024-01-12",
                "maturity_date": "2024-07-12",
                "deal_type": "TERM_DEPOSIT",
                "counterparty": "First National Bank",
                "principal_amount": 50000000.00,
                "currency": "USD",
                "interest_rate": 5.25,
                "interest_basis": "ACT/360",
                "interest_amount": 1312500.00,
                "maturity_amount": 51312500.00,
                "status": "ACTIVE",
                "collateral_type": "UNSECURED",
                "collateral_value": 0
            },
            {
                "deal_id": "MM2024001002",
                "deal_date": "2024-01-11",
                "start_date": "2024-01-11",
                "maturity_date": "2024-01-18",
                "deal_type": "CALL_DEPOSIT",
                "counterparty": "Central Bank",
                "principal_amount": 100000000.00,
                "currency": "AED",
                "interest_rate": 4.75,
                "interest_basis": "ACT/365",
                "interest_amount": 90958.90,
                "maturity_amount": 100090958.90,
                "status": "ACTIVE",
                "collateral_type": "GOVERNMENT_SECURITIES",
                "collateral_value": 102000000.00
            }
        ]
    },
    
    "derivatives": {
        "description": "Derivative instruments including options, futures, and swaps",
        "fields": [
            "trade_id", "trade_date", "product_type", "underlying_asset",
            "notional_amount", "currency", "strike_price", "expiry_date",
            "option_type", "premium", "counterparty", "trader", "status",
            "mark_to_market", "delta", "gamma", "vega"
        ],
        "sample_data": [
            {
                "trade_id": "DER2024000501",
                "trade_date": "2024-01-08",
                "product_type": "FX_OPTION",
                "underlying_asset": "EUR/USD",
                "notional_amount": 10000000.00,
                "currency": "EUR",
                "strike_price": 1.10,
                "expiry_date": "2024-03-08",
                "option_type": "CALL",
                "premium": 125000.00,
                "counterparty": "Investment Bank ABC",
                "trader": "Michael Chen",
                "status": "OPEN",
                "mark_to_market": 145000.00,
                "delta": 0.65,
                "gamma": 0.02,
                "vega": 0.15
            },
            {
                "trade_id": "DER2024000502",
                "trade_date": "2024-01-09",
                "product_type": "INTEREST_RATE_SWAP",
                "underlying_asset": "USD_LIBOR_3M",
                "notional_amount": 100000000.00,
                "currency": "USD",
                "strike_price": 0,
                "expiry_date": "2029-01-09",
                "option_type": "NA",
                "premium": 0,
                "counterparty": "Hedge Fund XYZ",
                "trader": "Emily Wang",
                "status": "ACTIVE",
                "mark_to_market": -250000.00,
                "delta": 0,
                "gamma": 0,
                "vega": 0
            }
        ]
    },
    
    "investments": {
        "description": "Investment portfolio including bonds, securities, and funds",
        "fields": [
            "investment_id", "isin", "security_name", "asset_class", "issuer",
            "purchase_date", "maturity_date", "face_value", "purchase_price",
            "current_price", "currency", "coupon_rate", "rating", "portfolio",
            "unrealized_pnl", "accrued_interest"
        ],
        "sample_data": [
            {
                "investment_id": "INV2024000101",
                "isin": "XS1234567890",
                "security_name": "UAE Government Bond 2029",
                "asset_class": "GOVERNMENT_BOND",
                "issuer": "UAE Ministry of Finance",
                "purchase_date": "2023-06-15",
                "maturity_date": "2029-06-15",
                "face_value": 10000000.00,
                "purchase_price": 9850000.00,
                "current_price": 9950000.00,
                "currency": "USD",
                "coupon_rate": 3.75,
                "rating": "AA",
                "portfolio": "HTM",
                "unrealized_pnl": 100000.00,
                "accrued_interest": 156250.00
            },
            {
                "investment_id": "INV2024000102",
                "isin": "US912828XY01",
                "security_name": "US Treasury Note 5Y",
                "asset_class": "GOVERNMENT_BOND",
                "issuer": "US Treasury",
                "purchase_date": "2023-09-20",
                "maturity_date": "2028-09-20",
                "face_value": 20000000.00,
                "purchase_price": 19750000.00,
                "current_price": 19900000.00,
                "currency": "USD",
                "coupon_rate": 4.25,
                "rating": "AAA",
                "portfolio": "AFS",
                "unrealized_pnl": 150000.00,
                "accrued_interest": 283333.33
            }
        ]
    },
    
    "hedging_instruments": {
        "description": "Hedging instruments for risk management",
        "fields": [
            "hedge_id", "hedge_type", "hedged_item", "hedge_ratio",
            "notional_amount", "currency", "start_date", "end_date",
            "hedge_effectiveness", "fair_value", "hedge_documentation",
            "accounting_treatment", "status"
        ],
        "sample_data": [
            {
                "hedge_id": "HDG2024000201",
                "hedge_type": "FAIR_VALUE_HEDGE",
                "hedged_item": "Fixed Rate Bond Portfolio",
                "hedge_ratio": 0.95,
                "notional_amount": 50000000.00,
                "currency": "USD",
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "hedge_effectiveness": 98.5,
                "fair_value": -125000.00,
                "hedge_documentation": "Q1_2024_IR_HEDGE_DOC",
                "accounting_treatment": "FAIR_VALUE",
                "status": "EFFECTIVE"
            }
        ]
    }
}

# Sample Test Queries for Treasury
TREASURY_TEST_CASES = [
    {
        "query": "Show me all forex transactions for USD/AED in January 2024",
        "expected_collection": "forex_transactions",
        "expected_fields": ["transaction_id", "currency_pair", "exchange_rate", "status"]
    },
    {
        "query": "What are the active money market deposits with interest rate above 5%?",
        "expected_collection": "money_market",
        "expected_fields": ["deal_id", "counterparty", "interest_rate", "maturity_amount"]
    },
    {
        "query": "List all FX options expiring in Q1 2024",
        "expected_collection": "derivatives",
        "expected_fields": ["trade_id", "product_type", "expiry_date", "premium"]
    },
    {
        "query": "Show me government bonds in our investment portfolio",
        "expected_collection": "investments",
        "expected_fields": ["isin", "security_name", "rating", "unrealized_pnl"]
    },
    {
        "query": "What is the total notional amount of active interest rate swaps?",
        "expected_collection": "derivatives",
        "expected_fields": ["trade_id", "product_type", "notional_amount", "mark_to_market"]
    },
    {
        "query": "Show hedge effectiveness for Q1 2024",
        "expected_collection": "hedging_instruments",
        "expected_fields": ["hedge_id", "hedge_type", "hedge_effectiveness", "status"]
    },
    {
        "query": "List all forward forex deals with value date in April 2024",
        "expected_collection": "forex_transactions",
        "expected_fields": ["transaction_id", "transaction_type", "value_date", "currency_pair"]
    },
    {
        "query": "What are our term deposits maturing in July 2024?",
        "expected_collection": "money_market",
        "expected_fields": ["deal_id", "deal_type", "maturity_date", "maturity_amount"]
    },
    {
        "query": "Show all EUR denominated investments",
        "expected_collection": "investments",
        "expected_fields": ["investment_id", "security_name", "currency", "current_price"]
    },
    {
        "query": "List derivatives trades by trader Emily Wang",
        "expected_collection": "derivatives",
        "expected_fields": ["trade_id", "trader", "product_type", "status"]
    }
]