# app/utils/rag_query_imlc.py

import openai
import chromadb
from chromadb.config import Settings
import os

# === OpenAI Azure Config ===
openai.api_type = "azure"
openai.api_base = "https://newfinaiapp.openai.azure.com"
openai.api_version = "2024-10-01-preview"
openai.api_key = "GPbELdmNOZA6LlMHgYyjcOPWeU9VIEYh0jo1hggpB4urTfDoJMijJQQJ99BAACYeBjFXJ3w3AAABACOGDMQ4"
EMBEDDING_MODEL = "text-embedding-3-large"
CHAT_MODEL = "gpt-4o"

# === ChromaDB Config ===
CHROMA_DIR = r"C:\Users\vijayan\PycharmProjects\PythonProject\app\utils\chroma_db"
COLLECTION_NAME = "imlc_multitable"

def get_embedding(text: str):
    print("🔹 Getting embedding for query...")
    response = openai.Embedding.create(input=[text], engine=EMBEDDING_MODEL)
    return response["data"][0]["embedding"]

def run_rag_query(user_query):
    print(f"\n🔍 Query: {user_query}")
    query_emb = get_embedding(user_query)

    print("🔹 Connecting to ChromaDB...")
    client = chromadb.Client(Settings(persist_directory=CHROMA_DIR))
    collection = client.get_or_create_collection(COLLECTION_NAME)

    print("🔹 Checking total documents in ChromaDB collection...")
    count_result = collection.count()
    print(f"📦 Total documents in collection: {count_result}")

    if count_result == 0:
        print("⚠️ No documents available in ChromaDB.")
        return

    print("🔹 Querying ChromaDB for top 5 relevant chunks...")
    results = collection.query(query_embeddings=[query_emb], n_results=5)

    if not results["documents"] or not results["documents"][0]:
        print("⚠️ No matching documents found.")
        return

    context = "\n\n---\n\n".join(results["documents"][0])

    prompt = f"""
You are a trade finance assistant. Use the following context from multiple Oracle tables related to Import Letters of Credit (IMLC) to answer the question accurately.

Context:
{context}

Question:
{user_query}
"""

    print("💬 Sending prompt to GPT-4o...")
    response = openai.ChatCompletion.create(
        engine=CHAT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )

    answer = response["choices"][0]["message"]["content"]
    print("\n💡 GPT-4o Response:\n", answer)

if __name__ == "__main__":
    run_rag_query("What events happened under LC IMLC000002BUYER, and what is the current status?")
