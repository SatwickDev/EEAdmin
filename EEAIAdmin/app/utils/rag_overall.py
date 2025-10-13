import os
import openai
from PyPDF2 import PdfReader
import chromadb
from app.utils.app_config import embedding_model

# Connect to ChromaDB server
client = chromadb.HttpClient(host="localhost", port=8000)
collection_ucp_rules = client.get_or_create_collection("all_rules")

def get_embedding(text):
    res = openai.Embedding.create(input=[text], engine=embedding_model)
    return res["data"][0]["embedding"]

def split_text(text, chunk_size=500):
    words = text.split()
    return [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]

def read_pdfs(folder):
    for filename in os.listdir(folder):
        if filename.endswith(".pdf"):
            path = os.path.join(folder, filename)
            reader = PdfReader(path)
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            yield filename, text

def embed_and_store():
    doc_id = 0
    for fname, content in read_pdfs("all_rules"):
        chunks = split_text(content)
        for i, chunk in enumerate(chunks):
            emb = get_embedding(chunk)
            collection_ucp_rules.add(
                documents=[chunk],
                metadatas=[{"source": fname}],
                embeddings=[emb],
                ids=[f"{fname}-{doc_id}-{i}"]
            )
        doc_id += 1
    print("✅ Embedding complete.")
#
# if __name__ == "__main__":
#    embed_and_store()
