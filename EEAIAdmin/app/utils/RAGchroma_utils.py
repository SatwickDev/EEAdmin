# app/utils/chroma_utils.py
import chromadb
from chromadb.config import Settings

client = chromadb.Client(Settings(persist_directory="./app/utils/chroma_db"))
collection = client.get_or_create_collection("trx_inbox")

def store_documents(docs):
    for doc in docs:
        collection.add(
            ids=[doc["id"]],
            documents=[doc["text"]],
            embeddings=[doc["embedding"]]
        )
    client.persist()

def query_documents(query_embedding, n_results=3):
    return collection.query(query_embeddings=[query_embedding], n_results=n_results)
