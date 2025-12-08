import json
import os
import re
import tempfile
import logging

import chromadb
import numpy as np
import pandas as pd
from PyPDF2 import PdfReader
from bs4 import BeautifulSoup

import openai  # Make sure this is the official openai package

from sentence_transformers import SentenceTransformer

from app.utils.app_config import COMPUTER_VISION_ENDPOINT, COMPUTER_VISION_KEY, embedding_model
from app.utils.app_config import (OCR_MAX_RETRIES, OCR_RETRY_DELAY_BASE, 
                                  OCR_POLLING_INTERVAL, OCR_TIMEOUT_BASE, 
                                  OCR_TIMEOUT_PER_PAGE, OCR_FAST_MODE, 
                                  OCR_ADAPTIVE_POLLING)
from app.utils.rag_clausetag import get_clause_tag_collection
from app.utils.rag_swift import get_swift_rules_collection
from app.utils.rag_ucp600 import get_ucp_rules_collection

logger = logging.getLogger(__name__)

# Initialize Azure Computer Vision client
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import ComputerVisionOcrError
from msrest.authentication import CognitiveServicesCredentials

cv_client = ComputerVisionClient(
    COMPUTER_VISION_ENDPOINT,
    CognitiveServicesCredentials(COMPUTER_VISION_KEY)
)


def save_uploaded_file(uploaded_file):
    """
    Save an uploaded file to a temporary location.

    Args:
        uploaded_file (werkzeug.datastructures.FileStorage): The uploaded file object.

    Returns:
        str: Path to the saved temporary file.
    """
    try:
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.filename)[1])
        uploaded_file.save(temp_file.name)
        logger.info(f"File saved to: {temp_file.name}")
        return temp_file.name
    except Exception as e:
        logger.error(f"Error saving uploaded file: {e}")
        return None


def extract_mandatory_fields(jsp_file_path):
    """Extracts mandatory fields from a JSP file"""
    with open(jsp_file_path, "r", encoding="utf-8") as file:
        jsp_content = file.read()

    soup = BeautifulSoup(jsp_content, 'html.parser')
    mandatory_classes = re.compile(r'CHAR_M|INT_M|FLOAT_M|AMT_M')

    rows = soup.find_all("tr")
    mandatory_fields = []

    for row in rows:
        fld_label_td = row.find("td", class_="FldLabel")
        fld_label = fld_label_td.text.strip() if fld_label_td else "N/A"

        for element in row.find_all(['input', 'select', 'textarea']):
            class_attr = element.get('class')
            if class_attr and any(mandatory_classes.match(cls) for cls in class_attr):
                field_name = element.get('name', 'N/A')
                field_title = element.get('title', fld_label)
                mandatory_fields.append((field_name, field_title))

    return mandatory_fields


import os
import numpy as np
import pandas as pd
import faiss
import pypdf

# Load Hugging Face model
HUGGINGFACE_MODEL = os.getenv("HUGGINGFACE_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
print("Loading Hugging Face Sentence Transformer model...")
hf_model = SentenceTransformer(HUGGINGFACE_MODEL)


# Function to extract text from PDF
def extract_text_from_pdf(pdf_path):
    """Extracts text from a PDF file."""
    try:
        pdf_reader = pypdf.PdfReader(pdf_path)
        text = "\n".join([page.extract_text() or "" for page in pdf_reader.pages])
        return text.strip()
    except Exception as e:
        print(f"Error reading PDF {pdf_path}: {e}")
        return ""


# Function to split text into chunks
def split_text(text, chunk_size=500):
    """Splits text into smaller chunks for better retrieval."""
    words = text.split()
    return [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]


# Function to generate embeddings
def get_embedding(text):
    """Generates embeddings using Hugging Face Sentence Transformer."""
    try:
        embedding = hf_model.encode(text, convert_to_tensor=False)
        return np.array(embedding, dtype=np.float32)  # Ensure float32 for FAISS
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return np.zeros(384, dtype=np.float32)  # Adjust if using a different model


# Function to process multiple PDFs
def process_pdfs_in_folder(pdf_folder, save_dir="output"):
    """Processes multiple PDF files in a folder and stores embeddings in FAISS."""
    os.makedirs(save_dir, exist_ok=True)

    all_text_chunks = []
    pdf_files = [f for f in os.listdir(pdf_folder) if f.endswith(".pdf")]

    if not pdf_files:
        print("No PDF files found in the folder.")
        return None

    for pdf_file in pdf_files:
        pdf_path = os.path.join(pdf_folder, pdf_file)
        print(f"Processing {pdf_file}...")

        pdf_text = extract_text_from_pdf(pdf_path)
        if not pdf_text:
            print(f"No text found in {pdf_file}. Skipping.")
            continue

        chunks = split_text(pdf_text, chunk_size=500)
        all_text_chunks.extend([(pdf_file, chunk) for chunk in chunks])

    if not all_text_chunks:
        print("No text extracted from any PDF. Exiting.")
        return None

    # Store chunks in DataFrame
    df = pd.DataFrame(all_text_chunks, columns=["file_name", "text"])
    df.to_csv(os.path.join(save_dir, "pdf_text_chunks.csv"), index=False)

    # Generate embeddings
    print("Generating embeddings...")
    df["embedding"] = df["text"].apply(lambda x: get_embedding(x))

    # Ensure embeddings are in float32 format
    embeddings = np.vstack(df["embedding"].values).astype(np.float32)

    df.to_csv(os.path.join(save_dir, "pdf_text_with_embeddings.csv"), index=False)
    np.save(os.path.join(save_dir, "embeddings.npy"), embeddings)
    print("Embeddings generated and saved.")

    # Store embeddings in FAISS
    print("Storing embeddings in FAISS...")
    dimension = embeddings.shape[1]  # Get embedding dimension
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)

    faiss.write_index(index, os.path.join(save_dir, "faiss_index.idx"))
    print(f"Stored {index.ntotal} embeddings in FAISS.")

    return df


# Function to load FAISS index
def load_faiss_index(index_path):
    """Loads FAISS index from file."""
    try:
        return faiss.read_index(index_path)
    except Exception as e:
        print(f"Error loading FAISS index from {index_path}: {e}")
        return None


# Function to retrieve relevant chunks
def retrieve_relevant_chunks(query, df, index, top_k=2):
    """Finds the most relevant chunks for a given query using FAISS."""
    query_embedding = get_embedding(query).reshape(1, -1).astype(np.float32)
    distances, indices = index.search(query_embedding, top_k)

    if len(indices) == 0 or indices[0][0] == -1:
        print("No relevant documents found.")
        return []

    return df.iloc[indices[0]][["file_name", "text"]].values.tolist()


def analyze_text_with_rules(
        text_data,
        pdf_folder=r"C:\Users\vijayan\PycharmProjects\PythonProject_Copy\pdfs",
        save_directory="app/utils/output"
):
    """Analyzes input text against UCP600 and SWIFT rules using GPT-4 and FAISS."""
    try:
        index_path = os.path.join(save_directory, "faiss_index.idx")
        csv_path = os.path.join(save_directory, "pdf_text_with_embeddings.csv")

        # Check if FAISS index and CSV exist, otherwise create them
        if not os.path.exists(index_path) or not os.path.exists(csv_path):
            print("FAISS index or CSV not found. Reprocessing PDFs...")
            process_pdfs_in_folder(pdf_folder, save_dir=save_directory)

        # Load FAISS index and text data
        faiss_index = load_faiss_index(index_path)
        if faiss_index is None:
            raise ValueError("Failed to load FAISS index.")

        df = pd.read_csv(csv_path)
        if df.empty:
            raise ValueError("Text chunks CSV is empty.")

        # Generate embedding for input text
        query_embedding = get_embedding(text_data).reshape(1, -1).astype('float32')

        # Search FAISS index
        distances, indices = faiss_index.search(query_embedding, k=5)

        # Get relevant context from PDF chunks
        context_chunks = "\n\n".join(
            [df.iloc[idx]['text'] for idx in indices[0] if idx < len(df)]
        )

        # Prepare LLM prompt
        prompt = f"""Analyze the following text against UCP600 and SWIFT rules:

                Input Text:
                {text_data}

                Relevant Regulatory Context:
                {context_chunks}

                Provide analysis in this format:
                1. UCP600 Compliance Check:
                   - [Analysis points]
                2. SWIFT Standards Verification:
                   - [Analysis points]
                3. Combined Recommendations:
                   - [Actionable items]

                Highlight any discrepancies or compliance issues.
                """

        # Call OpenAI LLM
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        ).choices[0].message.content

        return {
            "status": "success",
            "analysis": response,
            "relevant_context": context_chunks,
            "source_documents": df.iloc[indices[0]]['file_name'].unique().tolist()
        }

    except Exception as e:
        print(f"Analysis error: {e}")
        return {
            "status": "error",
            "message": str(e)

        }
def get_embedding_azureRAG(text):
    """Generate embeddings using Azure OpenAI with proper authentication"""
    try:
        # Use api_config_manager for centralized configuration
        from app.utils.api_config_manager import get_embedding_model, get_embedding_key, get_azure_api_base, get_azure_api_version
        import openai
        
        embedding_model_name = get_embedding_model()
        embedding_api_key = get_embedding_key()
        
        # Configure for Azure OpenAI embeddings
        openai.api_type = "azure"
        openai.api_base = get_azure_api_base()
        openai.api_version = get_azure_api_version()
        openai.api_key = embedding_api_key
        
        # Use the correct Azure API call format
        response = openai.Embedding.create(
            input=[text],
            engine=embedding_model_name  # For Azure, use 'engine' not 'model'
        )
        return response["data"][0]["embedding"]
    except Exception as e:
        logger.error(f"Error generating embedding: {str(e)}")
        # Return a dummy embedding as fallback
        import numpy as np
        return np.random.randn(1536).tolist()  # text-embedding-3-large has 1536 dimensions

def retrieve_relevant_chunksRAG_for_ucp(query_text, top_k=5):
    try:
        collection = get_ucp_rules_collection()
        if not collection:
            logger.warning("ChromaDB ucp_rules collection not available")
            return []
        
        embedding = get_embedding_azureRAG(query_text)
        results = collection.query(query_embeddings=[embedding], n_results=top_k)

        chunks = []
        for i in range(len(results["ids"][0])):
            chunk = {
                "id": results["ids"][0][i],
                "text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "embedding": embedding  # Optional; only needed if you update using embeddings
            }
            chunks.append(chunk)
        return chunks

    except Exception as e:
        print(f"Error retrieving UCP600 chunks: {e}")
        return []


def retrieve_relevant_chunksRAG_for_swift(query_text, top_k=5):
    try:
        collection = get_swift_rules_collection()
        if not collection:
            logger.warning("ChromaDB swift_rules collection not available")
            return []
        
        embedding = get_embedding_azureRAG(query_text)
        results = collection.query(query_embeddings=[embedding], n_results=top_k)

        chunks = []
        for i in range(len(results["ids"][0])):
            chunk = {
                "id": results["ids"][0][i],
                "text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "embedding": embedding  # Optional
            }
            chunks.append(chunk)
        return chunks

    except Exception as e:
        print(f"Error retrieving SWIFT chunks: {e}")
        return []

def retrieve_relevant_chunksRAG_for_clause_tag(query_text, top_k=5):
    try:
        collection = get_clause_tag_collection()
        if not collection:
            logger.warning("ChromaDB clause_tag collection not available")
            return []
        
        embedding = get_embedding_azureRAG(query_text)
        results = collection.query(query_embeddings=[embedding], n_results=top_k)

        chunks = []
        for i in range(len(results["ids"][0])):
            chunk = {
                "id": results["ids"][0][i],
                "text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "embedding": embedding  # Optional
            }
            chunks.append(chunk)
        return chunks

    except Exception as e:
        print(f"Error retrieving SWIFT chunks: {e}")
        return []


def load_custom_rules(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Failed to load custom rules: {e}")
        return []


# Lazy initialization of ChromaDB client and collection
_client = None
_collection_all_rules = None

def _get_chromadb_collection():
    """Lazy initialization of ChromaDB collection with environment variable support"""
    global _client, _collection_all_rules
    if _collection_all_rules is None:
        try:
            from app.utils.chroma_manager import get_chroma_client_for_customer
            _client = get_chroma_client_for_customer()
            if _client:
                _collection_all_rules = _client.get_or_create_collection("all_rules")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB collection: {e}")
    return _collection_all_rules

def retrieve_relevant_chunksRAG(query, top_k=5):
    """Retrieve relevant chunks using lazy-initialized ChromaDB collection"""
    collection = _get_chromadb_collection()
    if not collection:
        logger.warning("ChromaDB all_rules collection not available")
        return []
    
    embedding = get_embedding_azureRAG(query)
    results = collection.query(query_embeddings=[embedding], n_results=top_k)
    return [
        {
            "file_name": meta.get("source", "unknown"),
            "text": doc,
            "article": meta.get("article", "N/A")
        }
        for doc, meta in zip(results["documents"][0], results["metadatas"][0])
    ]
