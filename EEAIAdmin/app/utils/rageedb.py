import json
import openai
import cx_Oracle
import chromadb
from chromadb.config import Settings
from pathlib import Path
import os
from datetime import datetime, timedelta
import tiktoken

# ✅ Azure OpenAI Configuration
openai.api_type = "azure"
openai.api_base = "https://newfinaiapp.openai.azure.com"
openai.api_version = "2024-10-01-preview"
openai.api_key = "GPbELdmNOZA6LlMHgYyjcOPWeU9VIEYh0jo1hggpB4urTfDoJMijJQQJ99BAACYeBjFXJ3w3AAABACOGDMQ4"

EMBEDDING_MODEL = "text-embedding-3-large"
CHAT_MODEL = "gpt-4o"

# ✅ Oracle DB Configuration
ORACLE_CLIENT_LIB_DIR = r"C:\Users\vijayan\Downloads\instantclient-basic-windows.x64-23.6.0.24.10\instantclient_23_6"
USERNAME = "EXIMTRX"
PASSWORD = "EXIMTRX"
HOST = "ADIBV6"
PORT = "1521"
SERVICE = "DADIB"

cx_Oracle.init_oracle_client(lib_dir=ORACLE_CLIENT_LIB_DIR)

# ✅ Paths
EMBEDDED_JSON_PATH = Path(r"C:\Users\vijayan\PycharmProjects\PythonProject_Copy\app\utils\adibv6ee_eximtrx_chroma.json")
CHROMA_DB_PATH = r"C:\Users\vijayan\PycharmProjects\PythonProject_Copy\app\utils\adibv6ee_eximtrx_chromdb"

# ✅ Table Descriptions
TABLE_HINTS = {
    "EXIMTRX.IPLC_MASTER": "Master record for Import LC under EXIMTRX module.",
    "EXIMTRX.IPLC_LEDGER": "Ledger entries tracking lifecycle of Import LCs in EXIMTRX module.",
    "EXIMTRX.IPLC_EM_ISSU": "Issuance details for Import LCs in EXIMTRX module.",
    "EXIMTRX.IPLC_EM_AMD": "Amendment records for Import LCs in EXIMTRX module.",
    "EXIMTRX.IPLC_EM_NEGO": "Negotiation entries for Import LCs in EXIMTRX module."
}
COLUMN_HINTS = {
    "C_MAIN_REF": "Main reference number for the LC transaction.",
    "C_UNIT_CODE": "Code representing the unit or branch processing the LC.",
    "TRX_DT": "Date of transaction.",
    "LC_AMT": "Total amount of the Letter of Credit.",
    "LC_CCY": "Currency in which the LC is issued.",
    "ACCOUNT_NUMBER": "Customer account number associated with the LC.",
    "LC_BAL": "Outstanding balance on the LC.",
    "EXPIRY_DT": "Date on which the LC expires.",
    "EXPIRY_PLC": "Location where the LC expires.",
    "FORM_OF_LC": "Form or type of LC (e.g. irrevocable, confirmed).",
    "APPL_NM": "Applicant’s name.",
    "APPL_ADD1": "Applicant’s address line 1.",
    "APPL_EMAIL": "Applicant's email address.",
    "BENE_NM": "Beneficiary’s name.",
    "BENE_ADD1": "Beneficiary address line 1.",
    "BENE_BK_NM": "Beneficiary bank name.",
    "BENE_BK_SW_ADD": "Beneficiary bank SWIFT address.",
    "NEGO_BK_NM": "Negotiating bank name.",
    "ISSUE_DT": "Date the LC was issued.",
    "ISSUE_BK_NM": "Issuing bank name.",
    "CUST_ID": "Internal customer ID.",
    "GOODS_DESC": "Description of goods covered by the LC.",
    "SHIP_PRD": "Shipment period for the goods.",
    "INCOTERMS": "International commercial terms (e.g., FOB, CIF).",
    "INCOTERMS_PLACE": "Place associated with the Incoterms (e.g., port).",
    "TENOR_DAYS": "Number of days for payment after sight or shipment.",
    "LIMIT_AMT1": "Primary limit amount allowed under LC.",
    "LIMIT_EXP1": "Expiry date of the primary credit limit.",
    "MARGIN_DEPOSIT": "Margin deposit held against this LC.",
    "INSU_POLICY_NO": "Insurance policy number for covered goods.",
    "INSU_EXPIRY_DT": "Expiry date of the insurance policy.",
    "DRAFT": "Draft terms under the LC (e.g., at sight).",
    "PARTIAL_SHIP": "Indicates if partial shipments are allowed.",
    "VESSEL_CERT": "Vessel certificate reference or content.",
}


# 🔹 Format a record with table and description
def format_record_with_table(table: str, record: dict) -> str:
    hint = TABLE_HINTS.get(table, "Transaction-related record.")
    content_lines = []
    for k, v in record.items():
        if v and v != 'NULL':
            col_hint = COLUMN_HINTS.get(k, "")
            if col_hint:
                content_lines.append(f"{k} ({col_hint}): {v}")
            else:
                content_lines.append(f"{k}: {v}")
    content = "\n".join(content_lines)
    return f"{hint}\nTable: {table}\n{content}"

# 🔹 Token-safe truncation using tiktoken
def truncate_by_tokens(text, max_tokens=7500):
    enc = tiktoken.encoding_for_model(EMBEDDING_MODEL)
    tokens = enc.encode(text)
    truncated = enc.decode(tokens[:max_tokens])
    return truncated

# 🔹 Generate embedding
def get_embedding(text: str):
    safe_text = truncate_by_tokens(text)
    response = openai.Embedding.create(
        input=[safe_text],
        engine=EMBEDDING_MODEL
    )
    return response["data"][0]["embedding"]

# 🔹 Compute cutoff date (2 years)
cutoff_date = (datetime.today() - timedelta(days=100)).strftime('%Y-%m-%d')

# 🔹 Get all EXIMTRX reference IDs
def get_all_refs():
    print("🔍 Fetching EXIMTRX reference IDs...")
    #conn = cx_Oracle.connect(USERNAME, PASSWORD, f"{HOST}:{PORT}:{SERVICE}")
    dsn = cx_Oracle.makedsn("ADIBV6", 1521, sid="DADIB")  # or your actual values
    conn = cx_Oracle.connect("EXIMTRX", "EXIMTRX", dsn)
    cursor = conn.cursor()

    cursor.execute(f"""
        SELECT DISTINCT C_MAIN_REF FROM EXIMTRX.IPLC_MASTER
        WHERE C_MAIN_REF IS NOT NULL AND TRX_DT >= TO_DATE('{cutoff_date}', 'YYYY-MM-DD')
    """)
    exim_refs = [row[0] for row in cursor.fetchall()]
    print(f"⚙️ Found {len(exim_refs)} EXIMTRX references.")

    conn.close()
    return {"EXIMTRX": exim_refs}

# 🔹 Fetch EXIMTRX records for each reference
def fetch_eximtrx_records(c_main_ref: str):
    print(f"🔍 Fetching EXIMTRX records for C_MAIN_REF = {c_main_ref}...")
    dsn = cx_Oracle.makedsn("ADIBV6", 1521, sid="DADIB")  # or your actual values
    conn = cx_Oracle.connect("EXIMTRX", "EXIMTRX", dsn)
    cursor = conn.cursor()

    tables_queries = {
        "EXIMTRX.IPLC_MASTER": f"""
            SELECT * FROM EXIMTRX.IPLC_MASTER 
            WHERE C_MAIN_REF = '{c_main_ref}' 
        """,
        "EXIMTRX.IPLC_LEDGER": f"""
            SELECT * FROM EXIMTRX.IPLC_LEDGER 
            WHERE C_MAIN_REF = '{c_main_ref}' 
        """,
        "EXIMTRX.IPLC_EM_ISSU": f"""
            SELECT * FROM EXIMTRX.IPLC_EM_ISSU 
            WHERE C_MAIN_REF = '{c_main_ref}' 
        """,
        "EXIMTRX.IPLC_EM_AMD": f"""
            SELECT * FROM EXIMTRX.IPLC_EM_AMD 
            WHERE C_MAIN_REF = '{c_main_ref}' 
        """,
        "EXIMTRX.IPLC_EM_NEGO": f"""
            SELECT * FROM EXIMTRX.IPLC_EM_NEGO 
            WHERE C_MAIN_REF = '{c_main_ref}' 
        """
    }

    records = []
    for table_name, query in tables_queries.items():
        try:
            cursor.execute(query)
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            print(f"⚙️ Found {len(rows)} records in {table_name}.")
            for row in rows:
                converted = [val.read() if isinstance(val, cx_Oracle.LOB) else val for val in row]
                record = dict(zip(columns, converted))
                records.append({
                    "table": table_name,
                    "key": c_main_ref,
                    "record": record
                })
        except cx_Oracle.DatabaseError as e:
            print(f"⚠️ Error fetching from {table_name}: {e}")

    conn.close()
    return records

# ✅ Load or generate embeddings
if EMBEDDED_JSON_PATH.exists():
    print("📄 Loading cached embeddings...")
    docs = json.loads(EMBEDDED_JSON_PATH.read_text())
else:
    print("🛢 Generating embeddings for EXIMTRX records...")
    refs = get_all_refs()
    docs = []

    for ref in refs["EXIMTRX"]:
        records = fetch_eximtrx_records(ref)
        for i, entry in enumerate(records):
            text = format_record_with_table(entry["table"], entry["record"])
            if text.strip():
                try:
                    emb = get_embedding(text)
                    doc_id = f"eximtrx_{ref}_{entry['table'].lower()}_{i}"
                    docs.append({
                        "id": doc_id,
                        "text": text,
                        "embedding": emb
                    })
                except Exception as e:
                    print(f"⚠️ Embedding failed: {e}")

    EMBEDDED_JSON_PATH.write_text(json.dumps(docs, indent=2))
    print(f"✅ Embedded {len(docs)} records.")

# ✅ Store in ChromaDB using bulk insert
print("📦 Storing embedded records in ChromaDB...")
client = chromadb.HttpClient(host="localhost", port=8000)
COLLECTION_NAME = "adibv6ee_eximtrx_lc_records"
collection = client.get_or_create_collection(COLLECTION_NAME)

batch_size = 50
for i in range(0, len(docs), batch_size):
    batch = docs[i:i + batch_size]
    print(f"💾 Inserting batch {i // batch_size + 1} ({len(batch)} docs)...")
    try:
        collection.add(
            ids=[doc["id"] for doc in batch],
            documents=[doc["text"] for doc in batch],
            embeddings=[doc["embedding"] for doc in batch]
        )
    except Exception as e:
        print(f"❌ Failed to insert batch {i // batch_size + 1}: {e}")

print("✅ All EXIMTRX records stored in ChromaDB.")
print(f"✅ ChromaDB path: {CHROMA_DB_PATH}")
