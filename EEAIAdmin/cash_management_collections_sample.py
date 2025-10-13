"""
Cash Management Collections Structure and Sample Data
"""

# Cash Management Collections Configuration
CASH_MANAGEMENT_COLLECTIONS = {
    "cash_transactions": {
        "description": "Daily cash transactions including inflows and outflows",
        "fields": [
            "transaction_id", "transaction_date", "value_date", "account_number",
            "account_name", "transaction_type", "debit_amount", "credit_amount",
            "balance", "currency", "reference_number", "beneficiary_name",
            "remitter_name", "payment_method", "status", "branch_code",
            "transaction_narrative", "category"
        ],
        "sample_data": [
            {
                "transaction_id": "CSH2024100001",
                "transaction_date": "2024-01-15",
                "value_date": "2024-01-15",
                "account_number": "1234567890",
                "account_name": "ABC Corporation Operating Account",
                "transaction_type": "INCOMING_WIRE",
                "debit_amount": 0,
                "credit_amount": 2500000.00,
                "balance": 15750000.00,
                "currency": "USD",
                "reference_number": "FT24015ABC123",
                "beneficiary_name": "ABC Corporation",
                "remitter_name": "XYZ International Ltd",
                "payment_method": "SWIFT",
                "status": "COMPLETED",
                "branch_code": "DXB001",
                "transaction_narrative": "Payment for Invoice INV-2024-001",
                "category": "TRADE_RECEIPTS"
            },
            {
                "transaction_id": "CSH2024100002",
                "transaction_date": "2024-01-15",
                "value_date": "2024-01-15",
                "account_number": "1234567890",
                "account_name": "ABC Corporation Operating Account",
                "transaction_type": "OUTGOING_ACH",
                "debit_amount": 750000.00,
                "credit_amount": 0,
                "balance": 15000000.00,
                "currency": "USD",
                "reference_number": "ACH24015PAY001",
                "beneficiary_name": "Employee Payroll Account",
                "remitter_name": "ABC Corporation",
                "payment_method": "ACH",
                "status": "COMPLETED",
                "branch_code": "DXB001",
                "transaction_narrative": "Monthly Payroll - January 2024",
                "category": "PAYROLL"
            },
            {
                "transaction_id": "CSH2024100003",
                "transaction_date": "2024-01-16",
                "value_date": "2024-01-16",
                "account_number": "9876543210",
                "account_name": "ABC Corporation Collection Account",
                "transaction_type": "CHECK_DEPOSIT",
                "debit_amount": 0,
                "credit_amount": 125000.00,
                "balance": 3250000.00,
                "currency": "AED",
                "reference_number": "CHK2024016001",
                "beneficiary_name": "ABC Corporation",
                "remitter_name": "Local Customer LLC",
                "payment_method": "CHECK",
                "status": "CLEARING",
                "branch_code": "DXB002",
                "transaction_narrative": "Check deposit - Customer payment",
                "category": "COLLECTIONS"
            }
        ]
    },
    
    "liquidity_reports": {
        "description": "Daily and intraday liquidity position reports",
        "fields": [
            "report_id", "report_date", "report_time", "report_type",
            "total_cash_balance", "available_balance", "currency",
            "opening_balance", "total_inflows", "total_outflows",
            "net_position", "projected_shortfall", "credit_lines_available",
            "investments_maturing", "minimum_liquidity_requirement", "buffer_amount"
        ],
        "sample_data": [
            {
                "report_id": "LIQ2024011501",
                "report_date": "2024-01-15",
                "report_time": "09:00:00",
                "report_type": "MORNING_SNAPSHOT",
                "total_cash_balance": 125000000.00,
                "available_balance": 115000000.00,
                "currency": "USD",
                "opening_balance": 120000000.00,
                "total_inflows": 25000000.00,
                "total_outflows": 20000000.00,
                "net_position": 5000000.00,
                "projected_shortfall": 0,
                "credit_lines_available": 50000000.00,
                "investments_maturing": 10000000.00,
                "minimum_liquidity_requirement": 75000000.00,
                "buffer_amount": 40000000.00
            },
            {
                "report_id": "LIQ2024011502",
                "report_date": "2024-01-15",
                "report_time": "15:00:00",
                "report_type": "AFTERNOON_UPDATE",
                "total_cash_balance": 118000000.00,
                "available_balance": 108000000.00,
                "currency": "USD",
                "opening_balance": 125000000.00,
                "total_inflows": 8000000.00,
                "total_outflows": 15000000.00,
                "net_position": -7000000.00,
                "projected_shortfall": 0,
                "credit_lines_available": 50000000.00,
                "investments_maturing": 0,
                "minimum_liquidity_requirement": 75000000.00,
                "buffer_amount": 33000000.00
            }
        ]
    },
    
    "cash_forecasts": {
        "description": "Cash flow forecasts and projections",
        "fields": [
            "forecast_id", "forecast_date", "forecast_period", "account_number",
            "currency", "beginning_balance", "expected_receipts", "expected_payments",
            "ending_balance", "confidence_level", "variance_from_actual",
            "major_inflows", "major_outflows", "notes", "prepared_by"
        ],
        "sample_data": [
            {
                "forecast_id": "FCT2024011501",
                "forecast_date": "2024-01-15",
                "forecast_period": "WEEKLY",
                "account_number": "1234567890",
                "currency": "USD",
                "beginning_balance": 15750000.00,
                "expected_receipts": 12500000.00,
                "expected_payments": 10250000.00,
                "ending_balance": 18000000.00,
                "confidence_level": 85.5,
                "variance_from_actual": 2.3,
                "major_inflows": "Trade receipts: $8M, Investment maturity: $4.5M",
                "major_outflows": "Supplier payments: $6M, Payroll: $2.5M, Loan payment: $1.75M",
                "notes": "Includes confirmed customer payments for week ending Jan 21",
                "prepared_by": "Treasury Team"
            },
            {
                "forecast_id": "FCT2024011502",
                "forecast_date": "2024-01-15",
                "forecast_period": "MONTHLY",
                "account_number": "ALL_ACCOUNTS",
                "currency": "USD",
                "beginning_balance": 125000000.00,
                "expected_receipts": 85000000.00,
                "expected_payments": 78000000.00,
                "ending_balance": 132000000.00,
                "confidence_level": 78.0,
                "variance_from_actual": 5.1,
                "major_inflows": "Customer collections: $65M, Asset sales: $20M",
                "major_outflows": "Operating expenses: $45M, Capex: $18M, Debt service: $15M",
                "notes": "February forecast includes seasonal adjustments",
                "prepared_by": "CFO Office"
            }
        ]
    },
    
    "payment_orders": {
        "description": "Payment orders and instructions",
        "fields": [
            "order_id", "order_date", "execution_date", "payment_type",
            "ordering_account", "beneficiary_account", "beneficiary_name",
            "beneficiary_bank", "amount", "currency", "payment_purpose",
            "urgency", "charges_borne_by", "status", "swift_code",
            "reference_number", "approval_status", "approved_by"
        ],
        "sample_data": [
            {
                "order_id": "PMT2024011501",
                "order_date": "2024-01-15",
                "execution_date": "2024-01-16",
                "payment_type": "WIRE_TRANSFER",
                "ordering_account": "1234567890",
                "beneficiary_account": "GB12ABCD12345678901234",
                "beneficiary_name": "European Supplier Ltd",
                "beneficiary_bank": "HSBC London",
                "amount": 1250000.00,
                "currency": "EUR",
                "payment_purpose": "Raw material purchase - PO#2024-0123",
                "urgency": "NORMAL",
                "charges_borne_by": "SHARED",
                "status": "PENDING_APPROVAL",
                "swift_code": "HBUKGB4B",
                "reference_number": "PMT-EUR-2024-0156",
                "approval_status": "LEVEL1_APPROVED",
                "approved_by": "John.Smith"
            },
            {
                "order_id": "PMT2024011502",
                "order_date": "2024-01-15",
                "execution_date": "2024-01-15",
                "payment_type": "LOCAL_TRANSFER",
                "ordering_account": "9876543210",
                "beneficiary_account": "AE123456789012345678901",
                "beneficiary_name": "Local Services Provider",
                "beneficiary_bank": "Emirates NBD",
                "amount": 450000.00,
                "currency": "AED",
                "payment_purpose": "Monthly service contract payment",
                "urgency": "URGENT",
                "charges_borne_by": "OUR",
                "status": "EXECUTED",
                "swift_code": "EBILAEAD",
                "reference_number": "PMT-AED-2024-0489",
                "approval_status": "FULLY_APPROVED",
                "approved_by": "Sarah.Johnson,Michael.Brown"
            }
        ]
    },
    
    "cash_pooling": {
        "description": "Cash pooling and concentration structures",
        "fields": [
            "pool_id", "pool_name", "pool_type", "header_account",
            "participant_account", "participant_name", "target_balance",
            "actual_balance", "sweep_amount", "sweep_direction",
            "sweep_date", "interest_rate", "interest_amount", "status",
            "currency", "pool_limit"
        ],
        "sample_data": [
            {
                "pool_id": "POOL2024001",
                "pool_name": "USD Regional Cash Pool",
                "pool_type": "ZERO_BALANCING",
                "header_account": "1111111111",
                "participant_account": "1234567890",
                "participant_name": "ABC Corporation Operating",
                "target_balance": 0,
                "actual_balance": 5250000.00,
                "sweep_amount": 5250000.00,
                "sweep_direction": "TO_HEADER",
                "sweep_date": "2024-01-15",
                "interest_rate": 4.85,
                "interest_amount": 695.21,
                "status": "ACTIVE",
                "currency": "USD",
                "pool_limit": 25000000.00
            },
            {
                "pool_id": "POOL2024002",
                "pool_name": "AED Domestic Cash Pool",
                "pool_type": "TARGET_BALANCING",
                "header_account": "2222222222",
                "participant_account": "9876543210",
                "participant_name": "ABC Corporation Collections",
                "target_balance": 1000000.00,
                "actual_balance": 3250000.00,
                "sweep_amount": 2250000.00,
                "sweep_direction": "TO_HEADER",
                "sweep_date": "2024-01-15",
                "interest_rate": 4.25,
                "interest_amount": 261.64,
                "status": "ACTIVE",
                "currency": "AED",
                "pool_limit": 50000000.00
            }
        ]
    }
}

# Sample Test Queries for Cash Management
CASH_MANAGEMENT_TEST_CASES = [
    {
        "query": "Show me all incoming wire transfers for today",
        "expected_collection": "cash_transactions",
        "expected_fields": ["transaction_id", "transaction_type", "credit_amount", "remitter_name"]
    },
    {
        "query": "What is our current liquidity position?",
        "expected_collection": "liquidity_reports",
        "expected_fields": ["total_cash_balance", "available_balance", "buffer_amount"]
    },
    {
        "query": "Show cash forecast for next week",
        "expected_collection": "cash_forecasts",
        "expected_fields": ["forecast_period", "expected_receipts", "expected_payments", "ending_balance"]
    },
    {
        "query": "List all pending payment orders requiring approval",
        "expected_collection": "payment_orders",
        "expected_fields": ["order_id", "amount", "beneficiary_name", "approval_status"]
    },
    {
        "query": "Show cash pooling sweep activities for USD accounts",
        "expected_collection": "cash_pooling",
        "expected_fields": ["pool_name", "sweep_amount", "sweep_direction", "interest_amount"]
    },
    {
        "query": "What were the total payroll payments this month?",
        "expected_collection": "cash_transactions",
        "expected_fields": ["transaction_id", "debit_amount", "category", "transaction_narrative"]
    },
    {
        "query": "Show me checks pending clearing",
        "expected_collection": "cash_transactions",
        "expected_fields": ["transaction_id", "payment_method", "status", "credit_amount"]
    },
    {
        "query": "What is the variance between forecasted and actual cash flows?",
        "expected_collection": "cash_forecasts",
        "expected_fields": ["forecast_id", "variance_from_actual", "confidence_level"]
    },
    {
        "query": "List all urgent payment orders executed today",
        "expected_collection": "payment_orders",
        "expected_fields": ["order_id", "urgency", "status", "execution_date", "amount"]
    },
    {
        "query": "Show minimum liquidity requirements vs actual buffer",
        "expected_collection": "liquidity_reports",
        "expected_fields": ["minimum_liquidity_requirement", "buffer_amount", "available_balance"]
    },
    {
        "query": "What are the major cash inflows expected this week?",
        "expected_collection": "cash_forecasts",
        "expected_fields": ["major_inflows", "expected_receipts", "forecast_period"]
    },
    {
        "query": "Show all AED transactions above 1 million",
        "expected_collection": "cash_transactions",
        "expected_fields": ["transaction_id", "currency", "debit_amount", "credit_amount"]
    },
    {
        "query": "List accounts participating in cash pooling",
        "expected_collection": "cash_pooling",
        "expected_fields": ["participant_account", "participant_name", "pool_type", "status"]
    },
    {
        "query": "Show payment orders awaiting second level approval",
        "expected_collection": "payment_orders",
        "expected_fields": ["order_id", "approval_status", "amount", "approved_by"]
    },
    {
        "query": "What is the net cash position change since morning?",
        "expected_collection": "liquidity_reports",
        "expected_fields": ["report_type", "net_position", "total_inflows", "total_outflows"]
    }
]

# Integration Test Scenarios
INTEGRATION_TEST_SCENARIOS = [
    {
        "scenario": "End of Day Cash Position Reconciliation",
        "steps": [
            "Query all cash transactions for the day",
            "Get latest liquidity report",
            "Compare forecasted vs actual positions",
            "Check cash pooling sweeps executed"
        ],
        "collections_used": ["cash_transactions", "liquidity_reports", "cash_forecasts", "cash_pooling"]
    },
    {
        "scenario": "Payment Processing Workflow",
        "steps": [
            "Check available balance in liquidity report",
            "Review pending payment orders",
            "Verify approval status",
            "Execute approved payments",
            "Update cash forecast"
        ],
        "collections_used": ["liquidity_reports", "payment_orders", "cash_transactions", "cash_forecasts"]
    },
    {
        "scenario": "Monthly Cash Analysis",
        "steps": [
            "Aggregate all transactions by category",
            "Compare against monthly forecast",
            "Analyze variance patterns",
            "Review cash pooling efficiency"
        ],
        "collections_used": ["cash_transactions", "cash_forecasts", "cash_pooling"]
    }
]