"""
Cash Management Collections Population Script
Generates and populates ChromaDB collections with cash management data for 2023-2025
Current date: 29/07/2025
"""

import openai
import chromadb
from chromadb.utils import embedding_functions
import json
import os
from datetime import datetime, timedelta
from tqdm import tqdm
from tenacity import retry, wait_random_exponential, stop_after_attempt
import random
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'app', 'utils'))
from azure_openai_helper import generate_records_azure_robust, validate_and_fix_data

# --- Azure OpenAI config ---
AZURE_OPENAI_API_BASE = os.getenv("AZURE_OPENAI_API_BASE", "https://newfinaiapp.openai.azure.com")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY",
                                 "GPbELdmNOZA6LlMHgYyjcOPWeU9VIEYh0jo1hggpB4urTfDoJMijJQQJ99BAACYeBjFXJ3w3AAABACOGDMQ4")
AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-35-turbo")
AZURE_EMBEDDING_MODEL = os.getenv("AZURE_EMBEDDING_MODEL", "text-embedding-3-large")

openai.api_type = "azure"
openai.api_base = AZURE_OPENAI_API_BASE
openai.api_key = AZURE_OPENAI_API_KEY
openai.api_version = "2024-02-15-preview"

CHROMA_HOST = "localhost"
CHROMA_PORT = 8000
COLLECTION_NAME = "cash_management_records"
CURRENT_DATE = "2025-07-29"
RECORDS_PER_TABLE = 100

# Cash Management Tables Configuration
CASH_MANAGEMENT_TABLES = [
    {
        "module": "Cash Transactions",
        "filename": "cash_transactions.json",
        "id_field": "transaction_id",
        "columns": [
            "transaction_id", "transaction_date", "value_date", "account_number",
            "account_name", "transaction_type", "debit_amount", "credit_amount",
            "balance", "currency", "reference_number", "beneficiary_name",
            "remitter_name", "payment_method", "status", "branch_code",
            "transaction_narrative", "category"
        ],
        "prompt": f"""Generate {RECORDS_PER_TABLE} synthetic cash transaction records spanning from January 2023 to July 29, 2025.
        Include various transaction types: INCOMING_WIRE, OUTGOING_ACH, CHECK_DEPOSIT, INTERNAL_TRANSFER, etc.
        Mix currencies (USD, EUR, AED, GBP, JPY) and payment methods.
        Ensure realistic balance progression and transaction patterns.
        Categories should include: TRADE_RECEIPTS, PAYROLL, COLLECTIONS, OPERATIONS, INVESTMENTS, etc.
        Current date is 29/07/2025. Format as JSON array."""
    },
    {
        "module": "Liquidity Reports",
        "filename": "liquidity_reports.json",
        "id_field": "report_id",
        "columns": [
            "report_id", "report_date", "report_time", "report_type",
            "total_cash_balance", "available_balance", "currency",
            "opening_balance", "total_inflows", "total_outflows",
            "net_position", "projected_shortfall", "credit_lines_available",
            "investments_maturing", "minimum_liquidity_requirement", "buffer_amount"
        ],
        "prompt": f"""Generate {RECORDS_PER_TABLE} liquidity reports from January 2023 to July 29, 2025.
        Include multiple report types: MORNING_SNAPSHOT, AFTERNOON_UPDATE, END_OF_DAY, WEEKLY_SUMMARY.
        Show realistic cash flow patterns with seasonal variations.
        Include both normal days and stress scenarios.
        Current date is 29/07/2025. Format as JSON array."""
    },
    {
        "module": "Cash Forecasts",
        "filename": "cash_forecasts.json",
        "id_field": "forecast_id",
        "columns": [
            "forecast_id", "forecast_date", "forecast_period", "account_number",
            "currency", "beginning_balance", "expected_receipts", "expected_payments",
            "ending_balance", "confidence_level", "variance_from_actual",
            "major_inflows", "major_outflows", "notes", "prepared_by"
        ],
        "prompt": f"""Generate {RECORDS_PER_TABLE} cash forecast records from January 2023 to July 29, 2025.
        Include different forecast periods: DAILY, WEEKLY, MONTHLY, QUARTERLY.
        Show realistic confidence levels (60-95%) and variance patterns.
        Include both individual account and consolidated forecasts.
        Current date is 29/07/2025. Format as JSON array."""
    },
    {
        "module": "Payment Orders",
        "filename": "payment_orders.json",
        "id_field": "order_id",
        "columns": [
            "order_id", "order_date", "execution_date", "payment_type",
            "ordering_account", "beneficiary_account", "beneficiary_name",
            "beneficiary_bank", "amount", "currency", "payment_purpose",
            "urgency", "charges_borne_by", "status", "swift_code",
            "reference_number", "approval_status", "approved_by"
        ],
        "prompt": f"""Generate {RECORDS_PER_TABLE} payment order records from January 2023 to July 29, 2025.
        Include various payment types: WIRE_TRANSFER, LOCAL_TRANSFER, INTERNATIONAL_ACH, BOOK_TRANSFER.
        Mix urgency levels: URGENT, NORMAL, FUTURE_DATED.
        Show different approval statuses and workflows.
        Include both completed and pending orders.
        Current date is 29/07/2025. Format as JSON array."""
    },
    {
        "module": "Cash Pooling",
        "filename": "cash_pooling.json",
        "id_field": "pool_id",
        "columns": [
            "pool_id", "pool_name", "pool_type", "header_account",
            "participant_account", "participant_name", "target_balance",
            "actual_balance", "sweep_amount", "sweep_direction",
            "sweep_date", "interest_rate", "interest_amount", "status",
            "currency", "pool_limit"
        ],
        "prompt": f"""Generate {RECORDS_PER_TABLE} cash pooling records from January 2023 to July 29, 2025.
        Include different pool types: ZERO_BALANCING, TARGET_BALANCING, THRESHOLD_POOLING.
        Show both TO_HEADER and FROM_HEADER sweep directions.
        Include multiple currencies and realistic interest calculations.
        Mix active and inactive pool participants.
        Current date is 29/07/2025. Format as JSON array."""
    },
    {
        "module": "Bank Accounts",
        "filename": "bank_accounts.json",
        "id_field": "account_id",
        "columns": [
            "account_id", "account_number", "account_name", "account_type",
            "currency", "bank_name", "bank_code", "swift_code", "iban",
            "status", "opening_date", "current_balance", "available_balance",
            "overdraft_limit", "interest_rate", "last_activity_date"
        ],
        "prompt": f"""Generate {RECORDS_PER_TABLE} bank account records with activity from 2023 to July 29, 2025.
        Include various account types: OPERATING, COLLECTION, DISBURSEMENT, INVESTMENT, ESCROW.
        Mix different banks and jurisdictions.
        Show realistic balance patterns and account statuses.
        Current date is 29/07/2025. Format as JSON array."""
    },
    {
        "module": "Investment Positions",
        "filename": "investment_positions.json",
        "id_field": "position_id",
        "columns": [
            "position_id", "investment_type", "instrument_name", "isin",
            "purchase_date", "maturity_date", "principal_amount", "currency",
            "interest_rate", "current_value", "unrealized_gain_loss",
            "status", "custodian_bank", "account_number"
        ],
        "prompt": f"""Generate {RECORDS_PER_TABLE} investment position records from January 2023 to July 29, 2025.
        Include various investment types: TERM_DEPOSIT, MONEY_MARKET, TREASURY_BILLS, COMMERCIAL_PAPER.
        Show positions at different stages: active, matured, early_redemption.
        Include realistic yields and value calculations.
        Current date is 29/07/2025. Format as JSON array."""
    }
]

# Business Reports for Cash Management
CASH_MANAGEMENT_REPORTS = [
    "Daily Cash Position Report as of 29/07/2025",
    "Weekly Liquidity Analysis for week ending 28/07/2025",
    "Monthly Cash Flow Summary for July 2025",
    "Q2 2025 Treasury Performance Report",
    "Cash Forecast Accuracy Report - YTD 2025",
    "Payment Processing Statistics for July 2025",
    "Bank Fee Analysis Report - H1 2025",
    "Interest Income Report - YTD 2025",
    "Cash Pooling Efficiency Report - Q2 2025",
    "FX Exposure Report as of 29/07/2025",
    "Working Capital Analysis - July 2025",
    "Short Term Investment Performance - YTD 2025",
    "Bank Relationship Summary - 2025",
    "Intraday Liquidity Usage Report - July 2025",
    "Payment Approval Turnaround Time Analysis",
    "Cash Concentration Report - Weekly",
    "Overdraft Utilization Report - July 2025",
    "Interest Rate Benchmark Report - Q2 2025",
    "Treasury KPI Dashboard - July 2025",
    "Regulatory Liquidity Compliance Report - Q2 2025"
]

# The generate_records_azure function is now imported from azure_openai_helper as generate_records_azure_robust

@retry(wait=wait_random_exponential(min=1, max=5), stop=stop_after_attempt(3))
def get_embedding(text, model=AZURE_EMBEDDING_MODEL):
    """Get embedding for text using Azure OpenAI"""
    response = openai.Embedding.create(
        engine=model,
        input=text
    )
    return response['data'][0]['embedding']

class AzureOpenAIEmbeddingFunction(embedding_functions.EmbeddingFunction):
    """Custom embedding function for ChromaDB using Azure OpenAI"""
    
    def __init__(self, model_name=AZURE_EMBEDDING_MODEL):
        self.model_name = model_name
    
    def __call__(self, input_texts):
        embeddings = []
        for text in input_texts:
            embedding = get_embedding(text, self.model_name)
            embeddings.append(embedding)
        return embeddings

def validate_and_fix_data(data, table_config):
    """Validate and fix generated data"""
    if not data:
        return data
    
    # Ensure ID field exists
    if table_config['id_field'] not in data[0]:
        for i, record in enumerate(data):
            record[table_config['id_field']] = f"{table_config['module'].upper().replace(' ', '_')}_{i+1:04d}"
    
    return data

def main():
    """Main function to populate cash management collections"""
    print(f"=== Cash Management Collections Population Script ===")
    print(f"Current Date: {CURRENT_DATE}")
    print(f"Data Period: January 2023 - July 2025\n")
    
    # Initialize ChromaDB client
    client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    
    # Handle existing collection
    try:
        existing_collections = client.list_collections()
        collection_names = [col.name for col in existing_collections]
        
        if COLLECTION_NAME in collection_names:
            client.delete_collection(name=COLLECTION_NAME)
            print(f"Deleted existing collection: {COLLECTION_NAME}")
    except Exception as e:
        print(f"Error handling existing collection: {e}")
    
    # Create new collection
    embedding_function = AzureOpenAIEmbeddingFunction()
    collection = client.create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_function
    )
    print(f"Created new collection: {COLLECTION_NAME}\n")
    
    # Delete existing JSON files
    print("--- Cleaning up old data files ---")
    for table in CASH_MANAGEMENT_TABLES:
        if os.path.exists(table["filename"]):
            os.remove(table["filename"])
            print(f"Deleted {table['filename']}")
    print()
    
    # Add business reports
    print("--- Adding Cash Management Reports ---")
    report_docs = []
    report_ids = []
    report_metadatas = []
    
    for i, report in enumerate(CASH_MANAGEMENT_REPORTS):
        report_docs.append(f"Cash Management Report: {report}")
        report_ids.append(f"cash_report_{i}")
        report_metadatas.append({
            "module": "Cash Management Reports",
            "type": "business_report",
            "category": "treasury_reports",
            "report_date": CURRENT_DATE
        })
    
    # Ingest reports in chunks
    chunk_size = 10
    for i in tqdm(range(0, len(report_docs), chunk_size)):
        collection.add(
            documents=report_docs[i:i+chunk_size],
            ids=report_ids[i:i+chunk_size],
            metadatas=report_metadatas[i:i+chunk_size]
        )
    print("Cash management reports ingested successfully!\n")
    
    # Process each table
    for table in CASH_MANAGEMENT_TABLES:
        print(f"--- Generating: {table['module']} ---")
        
        # Generate data
        print(f"Calling Azure OpenAI for {table['module']}...")
        data = generate_records_azure_robust(table["prompt"], AZURE_OPENAI_DEPLOYMENT_NAME, max_records=50)
        
        # Save as JSON
        with open(table["filename"], "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Saved {table['filename']}")
        
        # Validate data
        data = validate_and_fix_data(data, table)
        
        # Prepare for ChromaDB
        docs, ids, metadatas = [], [], []
        for i, rec in enumerate(data):
            doc = "\n".join([f"{k}: {v}" for k, v in rec.items()])
            
            if table['id_field'] in rec:
                record_id = str(rec[table['id_field']])
            else:
                record_id = f"record_{i}"
            
            unique_id = f"{table['module'].lower().replace(' ', '_')}_{record_id}"
            
            ids.append(unique_id)
            docs.append(doc)
            metadatas.append({
                "module": table["module"],
                "type": "transaction_record",
                "id_field": table["id_field"],
                "record_id": record_id,
                "category": "cash_management"
            })
        
        # Ingest to ChromaDB
        print(f"Ingesting {len(docs)} {table['module']} records into ChromaDB...")
        for i in tqdm(range(0, len(docs), chunk_size)):
            collection.add(
                documents=docs[i:i+chunk_size],
                ids=ids[i:i+chunk_size],
                metadatas=metadatas[i:i+chunk_size]
            )
        print(f"Done with {table['module']}.\n")
    
    print("=== All cash management data ingested successfully! ===")
    print(f"Total collections: {len(CASH_MANAGEMENT_TABLES)}")
    print(f"Total business reports: {len(CASH_MANAGEMENT_REPORTS)}")
    print(f"Data period: January 2023 - July 2025")
    print(f"Current date: {CURRENT_DATE}")

def query_cash_management(query_text, n_results=5):
    """Query the cash management system"""
    client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    # Get collection with the same embedding function used during creation
    embedding_function = AzureOpenAIEmbeddingFunction()
    collection = client.get_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_function
    )
    
    print(f"\nQuerying: {query_text}")
    results = collection.query(
        query_texts=[query_text],
        n_results=n_results
    )
    
    print(f"Found {len(results['documents'][0])} relevant results:")
    for i, (doc, metadata) in enumerate(zip(results['documents'][0], results['metadatas'][0])):
        print(f"\n{i+1}. Module: {metadata['module']}")
        print(f"   Type: {metadata['type']}")
        print(f"   Content: {doc[:200]}...")
    
    return results

if __name__ == "__main__":
    main()
    
    # Test queries
    print("\n" + "="*50)
    print("SAMPLE CASH MANAGEMENT QUERIES")
    print("="*50)
    
    sample_queries = [
        "Show me today's cash position",
        "What are the pending payment orders?",
        "Cash forecast for next week",
        "Liquidity buffer analysis",
        "Investment positions maturing this month"
    ]
    
    for query in sample_queries:
        query_cash_management(query, n_results=3)
        print("-"*50)