import json
import openai
import cx_Oracle
import chromadb
from chromadb.config import Settings
from pathlib import Path
import os

# ✅ Azure OpenAI Configuration
openai.api_type = "azure"
openai.api_base = "https://newfinaiapp.openai.azure.com"
openai.api_version = "2024-10-01-preview"
openai.api_key = "GPbELdmNOZA6LlMHgYyjcOPWeU9VIEYh0jo1hggpB4urTfDoJMijJQQJ99BAACYeBjFXJ3w3AAABACOGDMQ4"

EMBEDDING_MODEL = "text-embedding-3-large"
CHAT_MODEL = "gpt-4o"

# ✅ Oracle DB Configuration
ORACLE_CLIENT_LIB_DIR = r"C:\Users\vijayan\Downloads\instantclient-basic-windows.x64-23.6.0.24.10\instantclient_23_6"
USERNAME = "CETRX"
PASSWORD = "CETRX"
HOST = "localhost"
PORT = "1521"
SERVICE = "DSCF"

cx_Oracle.init_oracle_client(lib_dir=ORACLE_CLIENT_LIB_DIR)

# ✅ Paths
EMBEDDED_JSON_PATH = Path(r"C:\Users\vijayan\PycharmProjects\PythonProject\app\utils\embedded_all_refs.json")
CHROMA_DB_PATH = r"C:\Users\vijayan\PycharmProjects\PythonProject\app\utils\chroma_db_all_refs"

# 🔹 Fetch distinct C_MAIN_REFs
def get_all_main_refs():
    conn = cx_Oracle.connect(USERNAME, PASSWORD, f"{HOST}:{PORT}/{SERVICE}")
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT C_MAIN_REF FROM CETRX.TRX_INBOX WHERE C_MAIN_REF IS NOT NULL AND C_MODULE = 'IMLC' AND LC_AMT IS NOT NULL ")
    refs = [row[0] for row in cursor.fetchall()]
    conn.close()
    return refs

# 🔹 Fetch data from multiple tables for one ref
def fetch_combined_records(c_main_ref: str):
    conn = cx_Oracle.connect(USERNAME, PASSWORD, f"{HOST}:{PORT}/{SERVICE}")
    cursor = conn.cursor()

    tables_queries = {
        "TRX_INBOX": f"SELECT * FROM CETRX.TRX_INBOX WHERE C_MAIN_REF = '{c_main_ref}'",
        "IMLC_EM_ISSUE": f"SELECT * FROM CETRX.IMLC_EM_ISSUE WHERE C_MAIN_REF = '{c_main_ref}'",
        "IMLC_LEDGER": f"SELECT * FROM CETRX.IMLC_LEDGER WHERE C_MAIN_REF = '{c_main_ref}'",
        "IMLC_MASTER": f"SELECT * FROM CETRX.IMLC_MASTER WHERE C_MAIN_REF = '{c_main_ref}'",
        "IMLC_EM_AMD": f"SELECT * FROM CETRX.IMLC_EM_AMD WHERE C_MAIN_REF = '{c_main_ref}'",
        "IMLC_EM_NEGO": f"SELECT * FROM CETRX.IMLC_EM_NEGO WHERE C_MAIN_REF = '{c_main_ref}'",
        "IMLC_AUTH": f"SELECT * FROM CETRX.IMLC_AUTH WHERE C_MAIN_REF = '{c_main_ref}'",
    }

    records = []

    for table_name, query in tables_queries.items():
        try:
            cursor.execute(query)
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()

            for row in rows:
                converted = []
                for val in row:
                    if isinstance(val, cx_Oracle.LOB):
                        converted.append(val.read())
                    else:
                        converted.append(val)
                record = dict(zip(columns, converted))
                records.append({
                    "table": table_name,
                    "c_main_ref": c_main_ref,
                    "record": record
                })

        except cx_Oracle.DatabaseError as e:
            print(f"⚠️ Error fetching from {table_name}: {e}")

    conn.close()
    return records

TABLE_HINTS = {
    "TRX_INBOX": "This is a summary record for a trade transaction.",
    "IMLC_EM_ISSUE": "This record contains issuance information for a letter of credit.",
    "IMLC_LEDGER": "This is a log of historical events and status updates for the LC.",
    "IMLC_MASTER": "This is the master record for the LC.",
    "IMLC_EM_AMD": "This record describes an amendment to the letter of credit.",
    "IMLC_EM_NEGO": "This record details negotiation events related to the LC.",
    "IMLC_AUTH": "This record captures authorization information.",
    "TRX_AUTH_LIST": "This record includes user authorization tracking details."
}


# 🔹 Format each record
def format_record_with_table(table: str, record: dict) -> str:
    hint = TABLE_HINTS.get(table, "This is a transaction-related record.")
    content = "\n".join(f"{k}: {v}" for k, v in record.items() if v and v != 'NULL')
    return f"{hint}\nTable: {table}\n{content}"

# 🔹 Generate embedding
def get_embedding(text: str):
    response = openai.Embedding.create(
        input=[text],
        engine=EMBEDDING_MODEL
    )
    return response["data"][0]["embedding"]

# ✅ Step 1: Load or create all embeddings
if EMBEDDED_JSON_PATH.exists():
    print("📄 Loading cached embeddings...")
    docs = json.loads(EMBEDDED_JSON_PATH.read_text())
else:
    print("🛢 Fetching all C_MAIN_REFs and generating embeddings...")
    all_refs = get_all_main_refs()
    docs = []

    for ref in all_refs:
        print(f"🔍 Processing {ref}")
        raw_records = fetch_combined_records(ref)
        for i, entry in enumerate(raw_records):
            text = format_record_with_table(entry["table"], entry["record"])
            if text.strip():
                emb = get_embedding(text)
                doc_id = f"{ref}_{entry['table'].lower()}_{i}"
                docs.append({"id": doc_id, "text": text, "embedding": emb})

    EMBEDDED_JSON_PATH.write_text(json.dumps(docs, indent=2))
    print(f"✅ Embedded {len(docs)} records from {len(all_refs)} references.")

# ✅ Step 2: Store in ChromaDB
client = chromadb.Client(Settings(persist_directory=CHROMA_DB_PATH))
collection = client.get_or_create_collection("lc_records_all")

for doc in docs:
    collection.add(
        ids=[doc["id"]],
        documents=[doc["text"]],
        embeddings=[doc["embedding"]]
    )

print("✅ Stored all embedded records in ChromaDB.")

# ✅ Step 3: Accept User Query
query = "show me expired transaction import letter of credit "
query_emb = get_embedding(query)
results = collection.query(query_embeddings=[query_emb], n_results=20)

if not results["documents"][0]:
    print("⚠️ No matching documents found.")
else:
    context = "\n\n---\n\n".join(results["documents"][0])
    prompt = f"""
    You are an intelligent trade finance assistant specializing in processing and analyzing transaction data related to Letters of Credit (LCs).

    You are provided with structured data retrieved from multiple Oracle database tables, all linked by the same transaction reference. These tables include:

    - **TRX_INBOX**: Transaction metadata and summary (LC amount, applicant, beneficiary, status, currency)
    - **IMLC_EM_ISSUE**: Issuance details (form of LC, expiry date, payment terms, issuing bank)
    - **IMLC_LEDGER**: Historical events or status changes for the transaction
    - **IMLC_EM_AMD**: Amendments made to the LC (amount changes, expiry changes, new terms)
    - **IMLC_EM_NEGO**: Negotiation-related events
    - **IMLC_MASTER**: Master-level information about the LC
    - **IMLC_AUTH**: Authorization records (approval status, user roles, authorization dates)

    ---

    ### Your Role

    - Answer **only using the provided context**. Do **not infer** or fabricate missing data.
    - If the answer is not explicitly available in the context, respond exactly with:  
      👉 "The data does not contain that information."
    - If the context contains multiple entries, you may summarize them in bullet points or a concise list.
    - If asked for event history or status flow, present a **chronological summary**.
    - Use clear, factual, and professional tone suitable for financial reporting.

    ---

    ### Context:
    {context}

    ---

    ### User Question:
    {query}
    """

    response = openai.ChatCompletion.create(
        engine=CHAT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )

    print("\n💡 GPT-4o Response:\n", response["choices"][0]["message"]["content"])
