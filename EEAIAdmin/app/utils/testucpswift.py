import openai
import chromadb
from chromadb.utils import embedding_functions
import json
import os
from tqdm import tqdm
from tenacity import retry, wait_random_exponential, stop_after_attempt
import numpy as np
from azure_openai_helper import generate_records_azure_robust, validate_and_fix_data

# --- Azure OpenAI config (fill with your values or set as environment vars) ---
AZURE_OPENAI_API_BASE = os.getenv("AZURE_OPENAI_API_BASE", "https://newfinaiapp.openai.azure.com")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY",
                                 "GPbELdmNOZA6LlMHgYyjcOPWeU9VIEYh0jo1hggpB4urTfDoJMijJQQJ99BAACYeBjFXJ3w3AAABACOGDMQ4")
AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-35-turbo")
AZURE_EMBEDDING_MODEL = os.getenv("AZURE_EMBEDDING_MODEL", "text-embedding-3-large")
RECORDS = 100
CURRENT_DATE = "2025-07-29"  # Current date

openai.api_type = "azure"
openai.api_base = AZURE_OPENAI_API_BASE
openai.api_key = AZURE_OPENAI_API_KEY
openai.api_version = "2024-02-15-preview"  # Use the correct version for gpt-4o

CHROMA_HOST = "localhost"
CHROMA_PORT = 8000
COLLECTION_NAME = "trade_finance_records"

# Business case records for trade finance reports
BUSINESS_CASE_RECORDS = [
    "Buyer Credit Issued,Closed and Paid During Period",
    "Buyer Credit Outstanding",
    "Report of TF Users logged in on 29/07/2025 at (#branchName / #branchCode)",
    "Report of TF User IDs created / modified / deleted on 29/07/2025 at(#branchName / #branchCode)",
    "Report of TF User IDs inactive as on 29/07/2025 at (#branchName / #branchCode)",
    "Report of TF Users as on 29/07/2025 at (#branchName / #branchCode)",
    "Import LC Amended During Period",
    "Import LC Bill Paid During Period",
    "Import Collection bill Lodged and Paid During Period",
    "Import LC Issued During Period",
    "Import LC Bill Lodge During Period",
    "Import LC Expired Due for Closure (Paid/Unpaid)",
    "Import Collection Bill Outstanding",
    "Forward Contract Booked/Cancelled and Utlized For period",
    "Forward Contract Outstansing along with cross currency",
    "Foreign bank Gurantee Outstanding",
    "Foreign Bank Gurantee Amendment",
    "Foreign Bank Gurantee Issued During Period",
    "Outstanding Inland Bank Guarantee",
    "Foreign Bank Gurantee Invoked and Injuction Received",
    "Outstanding Inland Letter of Credit",
    "Inland LC bill Paid During Period",
    "Inland LC bill Outstanding",
    "Inland Bank Guarantee Invoked and Injuction received",
    "Inland Bank Guarantee Amendment during Period",
    "Inland LC Amendment During Period",
    "Inland Bank Guarantee Issued during Period ( Issued and Closed )",
    "Inland Bank Guarantee Advised During Period",
    "Inland Outward LC and Non LC collection bill lodged and paid during period",
    "Inland LC Issued During Period",
    "Inland Outward bill Negotiated and Paid During Period",
    "Inland LC Advised during Period",
    "Inland Inward Collection bill Lodged and Paid During Period",
    "Inland inward LC Bill Lodged During Period",
    "Inland Inward Non LC Collection bill Outstanding",
    "Import LC Outstanding",
    "Import LC bill Outstanding",
    "Inland Outward bill Auto Reversal (Succesful and Failed)",
    "Import outward Remittance for Period",
    "Inland bill Interest recovered but not due",
    "Inland Bank Guarantee expiired Due for Closure",
    "Inland Outgoing SFMS",
    "Inland LC Expired and Due for closure (Paid/Unpaid bill)",
    "Inland Bank Guarantee Outstanding",
    "Inland Outward LC and Non LC collection bill Outstanding",
    "Inland LC Outstanding",
    "Inland Outward bill Negotiated Outstanding"
]

TABLES = [
    {
        "module": "Import LC",
        "filename": "import_lc.json",
        "id_field": "LC_NUMBER",
        "columns": [
            "LC_NUMBER", "APPLICANT", "BENEFICIARY", "ISSUE_DATE", "AMOUNT",
            "CURRENCY", "STATUS", "EXPIRY_DATE", "COUNTRY", "PRODUCT_TYPE"
        ],
        "prompt": "Generate 100 synthetic, realistic records for an Import LC table with dates ranging from 2023 to 2025. Current date is 29/07/2025. Columns: LC_NUMBER, APPLICANT, BENEFICIARY, ISSUE_DATE, AMOUNT, CURRENCY, STATUS, EXPIRY_DATE, COUNTRY, PRODUCT_TYPE. Include records from 2023, 2024, and 2025. Format as a JSON array."
    },
    {
        "module": "Export LC",
        "filename": "export_lc.json",
        "id_field": "LC_NUMBER",
        "columns": [
            "LC_NUMBER", "ISSUING_BANK", "BENEFICIARY", "APPLICANT", "ISSUE_DATE",
            "AMOUNT", "CURRENCY", "STATUS", "EXPIRY_DATE", "COUNTRY", "PRODUCT_TYPE"
        ],
        "prompt": "Generate 100 synthetic, realistic records for an Export LC table with dates ranging from 2023 to 2025. Current date is 29/07/2025. Columns: LC_NUMBER, ISSUING_BANK, BENEFICIARY, APPLICANT, ISSUE_DATE, AMOUNT, CURRENCY, STATUS, EXPIRY_DATE, COUNTRY, PRODUCT_TYPE. Include records from 2023, 2024, and 2025. Format as a JSON array."
    },
    {
        "module": "Guarantee",
        "filename": "guarantee.json",
        "id_field": "GUARANTEE_NUMBER",
        "columns": [
            "GUARANTEE_NUMBER", "APPLICANT", "BENEFICIARY", "ISSUE_DATE", "AMOUNT",
            "CURRENCY", "TYPE", "STATUS", "EXPIRY_DATE", "COUNTRY", "PURPOSE"
        ],
        "prompt": "Generate 100 synthetic, realistic records for a Guarantee table with dates ranging from 2023 to 2025. Current date is 29/07/2025. Columns: GUARANTEE_NUMBER, APPLICANT, BENEFICIARY, ISSUE_DATE, AMOUNT, CURRENCY, TYPE, STATUS, EXPIRY_DATE, COUNTRY, PURPOSE. Include records from 2023, 2024, and 2025. Format as a JSON array."
    },
    {
        "module": "Collection",
        "filename": "collection.json",
        "id_field": "COLLECTION_NUMBER",
        "columns": [
            "COLLECTION_NUMBER", "REMITTER", "REMITTEE", "COLLECTION_DATE", "AMOUNT",
            "CURRENCY", "TYPE", "STATUS", "COUNTRY", "DOCUMENT_TYPE"
        ],
        "prompt": "Generate 100 synthetic, realistic records for a Collection table with dates ranging from 2023 to 2025. Current date is 29/07/2025. Columns: COLLECTION_NUMBER, REMITTER, REMITTEE, COLLECTION_DATE, AMOUNT, CURRENCY, TYPE, STATUS, COUNTRY, DOCUMENT_TYPE. Include records from 2023, 2024, and 2025. Format as a JSON array."
    },
    {
        "module": "Shipping Export LC",
        "filename": "shipping_export_lc.json",
        "id_field": "SHIPPING_LC_NUMBER",
        "columns": [
            "SHIPPING_LC_NUMBER", "EXPORTER", "IMPORTER", "SHIPMENT_DATE", "PORT_OF_LOADING",
            "PORT_OF_DISCHARGE", "CARGO_DESCRIPTION", "AMOUNT", "CURRENCY", "STATUS", "COUNTRY"
        ],
        "prompt": "Generate 100 synthetic, realistic records for a Shipping Export LC table with dates ranging from 2023 to 2025. Current date is 29/07/2025. Columns: SHIPPING_LC_NUMBER, EXPORTER, IMPORTER, SHIPMENT_DATE, PORT_OF_LOADING, PORT_OF_DISCHARGE, CARGO_DESCRIPTION, AMOUNT, CURRENCY, STATUS, COUNTRY. Include records from 2023, 2024, and 2025. Format as a JSON array."
    },
    {
        "module": "Buyer Credit",
        "filename": "buyer_credit.json",
        "id_field": "BUYER_CREDIT_NUMBER",
        "columns": [
            "BUYER_CREDIT_NUMBER", "BORROWER", "LENDER", "ISSUE_DATE", "AMOUNT",
            "CURRENCY", "STATUS", "MATURITY_DATE", "COUNTRY", "PURPOSE", "INTEREST_RATE"
        ],
        "prompt": "Generate 100 synthetic, realistic records for a Buyer Credit table with dates ranging from 2023 to 2025. Current date is 29/07/2025. Columns: BUYER_CREDIT_NUMBER, BORROWER, LENDER, ISSUE_DATE, AMOUNT, CURRENCY, STATUS, MATURITY_DATE, COUNTRY, PURPOSE, INTEREST_RATE. Include records from 2023, 2024, and 2025. Format as a JSON array."
    },
    {
        "module": "Forward Contract",
        "filename": "forward_contract.json",
        "id_field": "CONTRACT_NUMBER",
        "columns": [
            "CONTRACT_NUMBER", "CUSTOMER", "BOOKING_DATE", "VALUE_DATE", "BUY_CURRENCY",
            "SELL_CURRENCY", "AMOUNT", "RATE", "STATUS", "COUNTRY", "CONTRACT_TYPE"
        ],
        "prompt": "Generate 100 synthetic, realistic records for a Forward Contract table with dates ranging from 2023 to 2025. Current date is 29/07/2025. Columns: CONTRACT_NUMBER, CUSTOMER, BOOKING_DATE, VALUE_DATE, BUY_CURRENCY, SELL_CURRENCY, AMOUNT, RATE, STATUS, COUNTRY, CONTRACT_TYPE. Include records from 2023, 2024, and 2025. Format as a JSON array."
    }
]


# The generate_records_azure and validate_and_fix_data functions are now imported from azure_openai_helper


@retry(wait=wait_random_exponential(min=1, max=5), stop=stop_after_attempt(3))
def get_embedding(text, model=AZURE_EMBEDDING_MODEL):
    """Get embedding for text using Azure OpenAI embedding model"""
    response = openai.Embedding.create(
        engine=model,
        input=text
    )
    return response['data'][0]['embedding']


from chromadb.utils import embedding_functions


class AzureOpenAIEmbeddingFunction(embedding_functions.EmbeddingFunction):
    """Custom embedding function for ChromaDB that uses Azure OpenAI"""

    def __init__(self, model_name=AZURE_EMBEDDING_MODEL):
        self.model_name = model_name

    def __call__(self, input_texts):
        embeddings = []
        for text in input_texts:
            embedding = get_embedding(text, self.model_name)
            embeddings.append(embedding)
        return embeddings


# Initialize ChromaDB client
client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)

# Handle existing collection - delete and recreate with proper embedding function
try:
    # Try to get existing collection to check if it exists
    existing_collections = client.list_collections()
    collection_names = [col.name for col in existing_collections]
    
    if COLLECTION_NAME in collection_names:
        # Delete existing collection if it exists
        client.delete_collection(name=COLLECTION_NAME)
        print(f"Deleted existing collection: {COLLECTION_NAME}")
    else:
        print(f"Collection {COLLECTION_NAME} doesn't exist, creating new one")
except Exception as e:
    print(f"Error handling existing collection: {e}")

# Create new collection with Azure embedding function
embedding_function = AzureOpenAIEmbeddingFunction()
collection = client.create_collection(
    name=COLLECTION_NAME,
    embedding_function=embedding_function
)
print(f"Created new collection: {COLLECTION_NAME} with Azure OpenAI embeddings")

# Delete existing JSON files to force regeneration with new date ranges
print("\n--- Cleaning up old data files ---")
for tbl in TABLES:
    if os.path.exists(tbl["filename"]):
        os.remove(tbl["filename"])
        print(f"Deleted {tbl['filename']}")

# First, add business case records to the collection
print("\n--- Adding Business Case Records ---")
business_docs = []
business_ids = []
business_metadatas = []

for i, record in enumerate(BUSINESS_CASE_RECORDS):
    business_docs.append(f"Business Case: {record}")
    business_ids.append(f"business_case_{i}")
    business_metadatas.append({
        "module": "Business Cases",
        "type": "report_template",
        "category": "trade_finance_reports"
    })

print(f"Ingesting {len(business_docs)} business case records into ChromaDB...")
chunk_size = 10  # Smaller chunks for embedding API calls
for i in tqdm(range(0, len(business_docs), chunk_size)):
    collection.add(
        documents=business_docs[i:i + chunk_size],
        ids=business_ids[i:i + chunk_size],
        metadatas=business_metadatas[i:i + chunk_size]
    )

print("Business case records ingested successfully!")

# Process data tables
for tbl in TABLES:
    print(f"\n--- Generating: {tbl['module']} ---")
    if not os.path.exists(tbl["filename"]):
        # 1. Generate with Azure OpenAI
        print(f"Calling Azure OpenAI for {tbl['module']}...")
        data = generate_records_azure_robust(tbl["prompt"], AZURE_OPENAI_DEPLOYMENT_NAME, max_records=50)
        # 2. Save as JSON
        with open(tbl["filename"], "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Saved {tbl['filename']}")
    else:
        print(f"{tbl['filename']} already exists, loading...")
        with open(tbl["filename"], "r", encoding="utf-8") as f:
            data = json.load(f)

    # Validate and fix data structure
    data = validate_and_fix_data(data, tbl)

    # 3. Prepare ChromaDB ingestion
    docs, ids, metadatas = [], [], []
    for i, rec in enumerate(data):
        doc = "\n".join([f"{k}: {v}" for k, v in rec.items()])

        # Handle missing ID field gracefully
        if tbl['id_field'] in rec:
            record_id = str(rec[tbl['id_field']])
            unique_id = f"{tbl['module'].lower().replace(' ', '_')}_{record_id}"
        else:
            # Use index if ID field is missing
            record_id = f"record_{i}"
            unique_id = f"{tbl['module'].lower().replace(' ', '_')}_{record_id}"
            print(f"Warning: {tbl['id_field']} not found in {tbl['module']} record {i}, using index instead")

        ids.append(unique_id)
        docs.append(doc)
        metadatas.append({
            "module": tbl["module"],
            "type": "transaction_record",
            "id_field": tbl["id_field"],
            "record_id": record_id
        })

    # 4. Ingest to ChromaDB with embeddings
    print(f"Ingesting {len(docs)} {tbl['module']} records into ChromaDB...")
    chunk_size = 10  # Smaller chunks for embedding API calls
    for i in tqdm(range(0, len(docs), chunk_size)):
        collection.add(
            documents=docs[i:i + chunk_size],
            ids=ids[i:i + chunk_size],
            metadatas=metadatas[i:i + chunk_size]
        )
    print(f"Done with {tbl['module']}.")

print("\nAll tables and business cases ingested with Azure OpenAI embeddings!")
print("Ready for RAG demo with enhanced semantic search capabilities!")


# Example query function to demonstrate the RAG system
def query_rag_system(query_text, n_results=5):
    """Query the RAG system with semantic search"""
    print(f"\nQuerying: {query_text}")
    # Re-get the collection with the embedding function for queries
    client_query = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    embedding_function_query = AzureOpenAIEmbeddingFunction()
    collection_query = client_query.get_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_function_query
    )
    results = collection_query.query(
        query_texts=[query_text],
        n_results=n_results
    )

    print(f"Found {len(results['documents'][0])} relevant results:")
    for i, (doc, metadata) in enumerate(zip(results['documents'][0], results['metadatas'][0])):
        print(f"\n{i + 1}. Module: {metadata['module']}")
        print(f"   Type: {metadata['type']}")
        print(f"   Content: {doc[:200]}...")

    return results


# Example usage
if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("SAMPLE QUERIES")
    print("=" * 50)

    # Example queries
    sample_queries = [
        "Show me buyer credit reports",
        "Import LC outstanding bills",
        "Forward contract bookings",
        "Inland bank guarantee reports",
        "User activity reports for branches"
    ]

    for query in sample_queries:
        query_rag_system(query, n_results=3)
        print("-" * 50)