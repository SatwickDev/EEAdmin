# app/utils/rag_query.py

import json
import openai
import cx_Oracle
import chromadb
from chromadb.config import Settings
from pathlib import Path
import os

# ✅ Azure OpenAI Configuration (Hardcoded)
openai.api_type = "azure"
openai.api_base = "https://newfinaiapp.openai.azure.com"
openai.api_version = "2024-10-01-preview"
openai.api_key = "1h36ydp0nY0qVtsIR7GjIr9cbyjBYtTPUIX21BH7PN1GuoEa8Tk8JQQJ99BIACYeBjFXJ3w3AAABACOGzSgi"

# ✅ Model Deployment Names (must match Azure deployments)
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
EMBEDDED_JSON_PATH = Path(r"C:\Users\vijayan\PycharmProjects\PythonProject\app\utils\embedded_oracle_data.json")
CHROMA_DB_PATH = r"C:\Users\vijayan\PycharmProjects\PythonProject\app\utils\chroma_db"

# 🔹 Fetch Oracle data
def fetch_oracle_data():
    conn = cx_Oracle.connect(USERNAME, PASSWORD, f"{HOST}:{PORT}/{SERVICE}")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cetrx.trx_inbox WHERE C_MODULE = 'IMLC' FETCH FIRST 100 ROWS ONLY")
    columns = [col[0] for col in cursor.description]
    rows = cursor.fetchall()
    conn.close()
    return [dict(zip(columns, row)) for row in rows if any(row)]

# 🔹 Format a record
def format_record(record: dict) -> str:
    return "\n".join(f"{k}: {v}" for k, v in record.items() if v and v != 'NULL')

# 🔹 Generate embedding using Azure OpenAI
def get_embedding(text: str):
    response = openai.Embedding.create(
        input=[text],
        engine=EMBEDDING_MODEL
    )
    return response["data"][0]["embedding"]

# ✅ Step 1: Load or create embedded records
if EMBEDDED_JSON_PATH.exists():
    print("📄 Loading cached embeddings...")
    docs = json.loads(EMBEDDED_JSON_PATH.read_text())
else:
    print("🛢 Fetching from Oracle and generating embeddings...")
    records = fetch_oracle_data()
    docs = []
    for i, rec in enumerate(records):
        text = format_record(rec)
        if text:
            emb = get_embedding(text)
            docs.append({"id": f"trx_{i}", "text": text, "embedding": emb})
    EMBEDDED_JSON_PATH.write_text(json.dumps(docs, indent=2))
    print(f"✅ Saved {len(docs)} embedded records to JSON.")

# ✅ Step 2: Store in ChromaDB
client = chromadb.Client(Settings(persist_directory=CHROMA_DB_PATH))
collection = client.get_or_create_collection("trx_inbox")

for doc in docs:
    collection.add(
        ids=[doc["id"]],
        documents=[doc["text"]],
        embeddings=[doc["embedding"]]
    )

print("✅ Stored records in Chroma DB.")

# ✅ Step 3: User Query
query = "List all active LCs with amounts above 50,000 USD ?"
query_emb = get_embedding(query)
results = collection.query(query_embeddings=[query_emb], n_results=3)

if not results["documents"][0]:
    print("⚠️ No matching documents found.")
else:
    context = "\n\n---\n\n".join(results["documents"][0])
    prompt = f"""
    You are a trade finance assistant. You are given structured transaction records from the Oracle table `CETRX.TRX_INBOX`, which includes information related to Letters of Credit (LCs).

    Each record may contain:
    - LC amount (`LC_AMT`)
    - Currency (`LC_CCY`)
    - Transaction date (`TRX_DATE`)
    - Expiry date (`EXPIRY_DT`)
    - LC number (`LC_NO`)
    - Applicant and Beneficiary names (`APPL_NM`, `BENE_NM`)
    - Current and next status (`CURRNT_STATUS`, `NXT_STATUS`)
    - Business function and module (`C_FUNC_SHORT_NAME`, `C_MODULE`)
    - Reference fields (`C_MAIN_REF`, `C_UNIT_CODE`)

    Use the information in the context below to answer the user's question. If relevant fields are missing, say clearly: "The data does not contain that information."

    Context:
    {context}

    Question:
    {query}
    """

    response = openai.ChatCompletion.create(
        engine=CHAT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )

    print("\n💡 GPT-4o Response:\n", response["choices"][0]["message"]["content"])
