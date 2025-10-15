import json
import os
import re
import tempfile
import logging
import time

import chromadb
import numpy as np
import pandas as pd
from PyPDF2 import PdfReader
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
from bs4 import BeautifulSoup

import openai  # Make sure this is the official openai package

from msrest.authentication import CognitiveServicesCredentials
from pdf2image import convert_from_path
import pdfplumber
from sentence_transformers import SentenceTransformer

from app.utils.app_config import COMPUTER_VISION_ENDPOINT, COMPUTER_VISION_KEY, embedding_model
from app.utils.app_config import (OCR_MAX_RETRIES, OCR_RETRY_DELAY_BASE, 
                                  OCR_POLLING_INTERVAL, OCR_TIMEOUT_BASE, 
                                  OCR_TIMEOUT_PER_PAGE, OCR_FAST_MODE, 
                                  OCR_ADAPTIVE_POLLING)
from app.utils.rag_clausetag import collection_clause_tag
from app.utils.rag_swift import collection_swift_rules
from app.utils.rag_ucp600 import collection_ucp_rules

logger = logging.getLogger(__name__)

# Initialize Azure Computer Vision client
import os
import tempfile
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
from azure.cognitiveservices.vision.computervision.models import ComputerVisionOcrError
from msrest.authentication import CognitiveServicesCredentials
import logging

logger = logging.getLogger(__name__)

cv_client = ComputerVisionClient(
    COMPUTER_VISION_ENDPOINT,
    CognitiveServicesCredentials(COMPUTER_VISION_KEY)
)

import logging
import time
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from msrest.authentication import CognitiveServicesCredentials


def extract_text_from_file(file_path, file_type):
    """
    Extract text, bounding box locations, and page numbers from a file using Azure Computer Vision OCR.

    Args:
        file_path (str): Path to the file to process.
        file_type (str): MIME type of the file.

    Returns:
        dict: A dictionary containing extracted text, confidence scores, bounding box locations, and page numbers.
    """
    try:
        if file_type not in ["application/pdf", "image/jpeg", "image/png"]:
            logging.error(f"Unsupported file type: {file_type}")
            return {"error": f"Unsupported file type: {file_type}", "text_data": []}

        logging.info(f"Processing file: {file_path}")

        # Read file and send to Azure OCR
        with open(file_path, "rb") as file_stream:
            read_response = cv_client.read_in_stream(file_stream, raw=True)

        # Extract operation ID from response headers
        operation_location = read_response.headers.get("Operation-Location")
        if not operation_location:
            logging.error("Azure OCR response missing 'Operation-Location' header.")
            return {"error": "Azure OCR response missing 'Operation-Location'", "text_data": []}

        operation_id = operation_location.split("/")[-1]

        # **Poll for the result with a timeout**
        max_wait_time = 30  # Maximum time to wait for response (in seconds)
        start_time = time.time()

        while True:
            result = cv_client.get_read_result(operation_id)
            if result.status not in ["notStarted", "running"]:
                break

            # **Check for timeout**
            if time.time() - start_time > max_wait_time:
                logging.error("OCR processing timeout exceeded.")
                return {"error": "OCR processing took too long", "text_data": []}

            time.sleep(0.5)  # Wait before polling again

        # **Check OCR result status**
        if result.status != OperationStatusCodes.succeeded:
            logging.warning(f"Azure OCR failed with status: {result.status}")
            return {
                "error": f"Azure OCR failed. Status: {result.status}",
                "text_data": []
            }

        # **Extract text, bounding boxes, and page numbers**
        text_data = []
        for page_num, read_result in enumerate(result.analyze_result.read_results, start=1):
            for line in read_result.lines:
                words = line.words  # Extract words

                # ✅ Compute average confidence score from words
                if words:
                    confidence_scores = [word.confidence for word in words if hasattr(word, "confidence")]
                    avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 1.0
                else:
                    avg_confidence = 1.0  # Default confidence if no words are present

                text_data.append({
                    "text": line.text,
                    "bounding_box": line.bounding_box,  # Coordinates of the text
                    "bounding_page": page_num,  # Page number
                    "confidence": avg_confidence  # ✅ Use average confidence from words
                })

        if not text_data:
            logging.warning("Azure OCR returned no text.")
            return {"error": "No text extracted", "text_data": []}

        return {"text_data": text_data}

    except Exception as e:
        logging.error(f"Unexpected error in OCR extraction: {e}")
        return {"error": str(e), "text_data": []}


def extract_text_from_file_optimized(file_path, file_type, quality_verdict=None, page_count=1):
    """
    OPTIMIZED: Extract text using Azure Computer Vision OCR with performance optimizations.
    
    Args:
        file_path (str): Path to the file to process.
        file_type (str): MIME type of the file.
        quality_verdict (str): Quality analysis verdict (direct_analysis, pre_processing, etc.)
        page_count (int): Estimated number of pages for timeout calculation.

    Returns:
        dict: A dictionary containing extracted text, confidence scores, bounding box locations, and page numbers.
    """
    try:
        if file_type not in ["application/pdf", "image/jpeg", "image/png"]:
            logging.error(f"Unsupported file type: {file_type}")
            return {"error": f"Unsupported file type: {file_type}", "text_data": []}

        logging.info(f"🚀 OPTIMIZED OCR processing: {file_path}")
        logging.info(f"📊 Quality verdict: {quality_verdict}, Pages: {page_count}")

        # OPTIMIZATION 1: Dynamic timeout calculation
        dynamic_timeout = OCR_TIMEOUT_BASE + (page_count * OCR_TIMEOUT_PER_PAGE)
        
        # OPTIMIZATION 2: Quality-based mode selection
        fast_mode = OCR_FAST_MODE and quality_verdict in ["direct_analysis", "good"]
        if fast_mode:
            dynamic_timeout = max(10, dynamic_timeout * 0.7)  # Reduce timeout for high quality docs
            logging.info("⚡ Fast mode enabled for high-quality document")

        logging.info(f"⏰ Dynamic timeout: {dynamic_timeout}s (base: {OCR_TIMEOUT_BASE}s + {page_count}*{OCR_TIMEOUT_PER_PAGE}s)")

        # Read file and send to Azure OCR
        with open(file_path, "rb") as file_stream:
            read_response = cv_client.read_in_stream(file_stream, raw=True)

        # Extract operation ID from response headers
        operation_location = read_response.headers.get("Operation-Location")
        if not operation_location:
            logging.error("Azure OCR response missing 'Operation-Location' header.")
            return {"error": "Azure OCR response missing 'Operation-Location'", "text_data": []}

        operation_id = operation_location.split("/")[-1]

        # OPTIMIZATION 3: Adaptive polling with early termination
        start_time = time.time()
        poll_count = 0
        
        while True:
            result = cv_client.get_read_result(operation_id)
            poll_count += 1
            
            # OPTIMIZATION 4: Early termination for completed operations
            if result.status not in ["notStarted", "running"]:
                processing_time = time.time() - start_time
                logging.info(f"✅ OCR completed in {processing_time:.2f}s after {poll_count} polls")
                break

            # OPTIMIZATION 5: Timeout check
            if time.time() - start_time > dynamic_timeout:
                logging.error(f"OCR processing timeout exceeded ({dynamic_timeout}s).")
                return {"error": f"OCR processing took too long (>{dynamic_timeout}s)", "text_data": []}

            # OPTIMIZATION 6: Adaptive polling intervals
            if OCR_ADAPTIVE_POLLING:
                if poll_count <= 2:
                    sleep_time = 0.1  # Very fast initial polls
                elif poll_count <= 5:
                    sleep_time = OCR_POLLING_INTERVAL  # Standard polling
                else:
                    sleep_time = min(1.0, OCR_POLLING_INTERVAL * 2)  # Slower for long operations
            else:
                sleep_time = OCR_POLLING_INTERVAL
                
            time.sleep(sleep_time)

        # Check OCR result status
        if result.status != OperationStatusCodes.succeeded:
            logging.warning(f"Azure OCR failed with status: {result.status}")
            return {
                "error": f"Azure OCR failed. Status: {result.status}",
                "text_data": []
            }

        # Extract text, bounding boxes, and page numbers with optimized processing
        text_data = []
        total_confidence = 0
        line_count = 0
        
        for page_num, read_result in enumerate(result.analyze_result.read_results, start=1):
            for line in read_result.lines:
                words = line.words

                # OPTIMIZATION 7: Optimized confidence calculation
                if words:
                    confidence_scores = [word.confidence for word in words if hasattr(word, "confidence")]
                    avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 1.0
                else:
                    avg_confidence = 1.0

                text_data.append({
                    "text": line.text,
                    "bounding_box": line.bounding_box,
                    "bounding_page": page_num,
                    "confidence": avg_confidence
                })
                
                total_confidence += avg_confidence
                line_count += 1

        if not text_data:
            logging.warning("Azure OCR returned no text.")
            return {"error": "No text extracted", "text_data": []}

        # OPTIMIZATION 8: Quality metrics for performance monitoring
        overall_confidence = total_confidence / line_count if line_count > 0 else 0.0
        processing_time = time.time() - start_time
        
        logging.info(f"📊 OCR Results: {len(text_data)} lines, avg confidence: {overall_confidence:.3f}")
        logging.info(f"⚡ Total processing time: {processing_time:.2f}s")
        
        return {
            "text_data": text_data,
            "processing_time": processing_time,
            "overall_confidence": overall_confidence,
            "optimization_stats": {
                "fast_mode": fast_mode,
                "dynamic_timeout": dynamic_timeout,
                "poll_count": poll_count,
                "adaptive_polling": OCR_ADAPTIVE_POLLING
            }
        }

    except Exception as e:
        logging.error(f"Unexpected error in optimized OCR extraction: {e}")
        return {"error": str(e), "text_data": []}


#
# def extract_text_from_file(file_path, file_type):
#     """
#     Extract text and bounding box locations from a file using Azure Computer Vision OCR.
#
#     Args:
#         file_path (str): Path to the file to process.
#         file_type (str): MIME type of the file.
#
#     Returns:
#         dict: A dictionary containing extracted text, confidence scores, and bounding box locations.
#     """
#     try:
#         if file_type not in ["application/pdf", "image/jpeg", "image/png"]:
#             logging.error(f"Unsupported file type: {file_type}")
#             return {"error": f"Unsupported file type: {file_type}", "text_data": []}
#
#         logging.info(f"Processing file: {file_path}")
#
#         # Read file and send to Azure OCR
#         with open(file_path, "rb") as file_stream:
#             read_response = cv_client.read_in_stream(file_stream, raw=True)
#
#         # Extract operation ID from response headers
#         operation_location = read_response.headers.get("Operation-Location")
#         if not operation_location:
#             logging.error("Azure OCR response missing 'Operation-Location' header.")
#             return {"error": "Azure OCR response missing 'Operation-Location'", "text_data": []}
#
#         operation_id = operation_location.split("/")[-1]
#
#         # **Poll for the result with a timeout**
#         max_wait_time = 30  # Maximum time to wait for response (in seconds)
#         start_time = time.time()
#
#         while True:
#             result = cv_client.get_read_result(operation_id)
#             if result.status not in ["notStarted", "running"]:
#                 break
#
#             # **Check for timeout**
#             if time.time() - start_time > max_wait_time:
#                 logging.error("OCR processing timeout exceeded.")
#                 return {"error": "OCR processing took too long", "text_data": []}
#
#             time.sleep(2)  # Wait before polling again
#
#         # **Check OCR result status**
#         if result.status != "succeeded":
#             logging.warning("Azure OCR failed to extract text.")
#             return {"error": "Azure OCR could not process file", "text_data": []}
#
#         # **Extract text and bounding boxes**
#         text_data = []
#         for read_result in result.analyze_result.read_results:
#             for line in read_result.lines:
#                 words = line.words  # Extract words
#
#                 # ✅ Compute average confidence score from words
#                 if words:
#                     confidence_scores = [word.confidence for word in words if hasattr(word, "confidence")]
#                     avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 1.0
#                 else:
#                     avg_confidence = 1.0  # Default confidence if no words are present
#
#                 text_data.append({
#                     "text": line.text,
#                     "bounding_box": line.bounding_box,  # Coordinates of the text
#                     "confidence": avg_confidence  # ✅ Use average confidence from words
#                 })
#
#         if not text_data:
#             logging.warning("Azure OCR returned no text.")
#             return {"error": "No text extracted", "text_data": []}
#
#         return {"text_data": text_data}
#
#     except Exception as e:
#         logging.error(f"Unexpected error in OCR extraction: {e}")
#         return {"error": str(e), "text_data": []}


# def extract_text_from_file(file_path, file_type):
#     """
#     Extract text and bounding box locations from a file using Azure Computer Vision OCR.
#
#     Args:
#         file_path (str): Path to the file to process.
#         file_type (str): MIME type of the file.
#
#     Returns:
#         dict: A dictionary containing extracted text, confidence scores, and bounding box locations.
#     """
#     try:
#         if file_type not in ["application/pdf", "image/jpeg", "image/png"]:
#             logging.error(f"Unsupported file type: {file_type}")
#             return {"error": f"Unsupported file type: {file_type}", "text_data": []}
#
#         logging.info(f"Processing file: {file_path}")
#
#         # Read file and send to Azure OCR
#         with open(file_path, "rb") as file_stream:
#             read_response = cv_client.read_in_stream(file_stream, raw=True)
#
#         # Extract operation ID from response headers
#         operation_location = read_response.headers.get("Operation-Location")
#         if not operation_location:
#             logging.error("Azure OCR response missing 'Operation-Location' header.")
#             return {"error": "Azure OCR response missing 'Operation-Location'", "text_data": []}
#
#         operation_id = operation_location.split("/")[-1]
#
#         # **Poll for the result with a timeout**
#         max_wait_time = 30  # Maximum time to wait for response (in seconds)
#         start_time = time.time()
#
#         while True:
#             result = cv_client.get_read_result(operation_id)
#             if result.status not in ["notStarted", "running"]:
#                 break
#
#             # **Check for timeout**
#             if time.time() - start_time > max_wait_time:
#                 logging.error("OCR processing timeout exceeded.")
#                 return {"error": "OCR processing took too long", "text_data": []}
#
#             time.sleep(2)  # Wait before polling again
#
#         # **Check OCR result status**
#         if result.status != OperationStatusCodes.succeeded:
#             logging.warning("Azure OCR failed to extract text.")
#             return {"error": "Azure OCR could not process file", "text_data": []}
#
#         # **Extract text and bounding boxes**
#         text_data = []
#         for read_result in result.analyze_result.read_results:
#             for line in read_result.lines:
#                 text_data.append({
#                     "text": line.text,
#                     "bounding_box": line.bounding_box,  # Coordinates of the text
#                     "confidence": line.confidence
#                 })
#
#         if not text_data:
#             logging.warning("Azure OCR returned no text.")
#             return {"error": "No text extracted", "text_data": []}
#
#         return {"text_data": text_data}
#
#     except Exception as e:
#         logging.error(f"Unexpected error in OCR extraction: {e}")
#         return {"error": str(e), "text_data": []}

# lastest
# def extract_text_from_file(file_path, file_type):
#     """
#     Extract text from a file using pdfplumber for PDFs and Azure Computer Vision OCR for images.
#
#     Args:
#         file_path (str): Path to the file to process.
#         file_type (str): MIME type of the file.
#         max_retries (int): Maximum number of retries for rate-limit errors.
#
#     Returns:
#         dict: A dictionary containing extracted text and confidence score.
#     """
#     try:
#         retries = 0
#         max_retries = 3
#         while retries < max_retries:
#             try:
#                 if file_type == "application/pdf":
#                     logger.info(f"Processing PDF file: {file_path}")
#                     with open(file_path, "rb") as file_stream:
#                         read_response = cv_client.read_in_stream(file_stream, raw=True)
#
#                     # Get the operation ID for polling
#                     operation_location = read_response.headers["Operation-Location"]
#                     operation_id = operation_location.split("/")[-1]
#
#                     # Poll for the result
#                     while True:
#                         result = cv_client.get_read_result(operation_id)
#                         if result.status not in ["notStarted", "running"]:
#                             break
#
#                     if result.status == OperationStatusCodes.succeeded:
#                         lines = [
#                             line.text
#                             for read_result in result.analyze_result.read_results
#                             for line in read_result.lines
#                         ]
#                         return {
#                             "text": " ".join(lines).strip(),
#                             "ocr_confidence": 100.0 if lines else 0.0
#                         }
#                     else:
#                         logger.warning("Azure Computer Vision could not extract text from the PDF.")
#                         return {"text": None, "ocr_confidence": 0.0}
#
#                 elif file_type.startswith("image/"):
#                     logger.info(f"Processing image file: {file_path}")
#                     with open(file_path, "rb") as file_stream:
#                         read_response = cv_client.read_in_stream(file_stream, raw=True)
#
#                     # Get the operation ID for polling
#                     operation_location = read_response.headers["Operation-Location"]
#                     operation_id = operation_location.split("/")[-1]
#
#                     # Poll for the result
#                     while True:
#                         result = cv_client.get_read_result(operation_id)
#                         if result.status not in ["notStarted", "running"]:
#                             break
#
#                     if result.status == OperationStatusCodes.succeeded:
#                         lines = [
#                             line.text
#                             for read_result in result.analyze_result.read_results
#                             for line in read_result.lines
#                         ]
#                         return {
#                             "text": " ".join(lines).strip(),
#                             "ocr_confidence": 100.0 if lines else 0.0
#                         }
#                     else:
#                         logger.warning("Azure Computer Vision could not extract text from the image.")
#                         return {"text": None, "ocr_confidence": 0.0}
#
#                 else:
#                     logger.error(f"Unsupported file type: {file_type}")
#                     return {"text": None, "ocr_confidence": 0.0}
#
#             except Exception as e:
#                 if "Too Many Requests" in str(e):
#                     retries += 1
#                     wait_time = 2 ** retries
#                     logger.warning(f"Rate limit hit. Retrying in {wait_time} seconds...")
#                     time.sleep(wait_time)
#                 else:
#                     logger.error(f"Error extracting text from file: {e}")
#                     break
#
#         logger.error("Max retries reached. Extraction failed due to rate limits.")
#         return {"text": None, "ocr_confidence": 0.0}
#
#     except Exception as e:
#         logger.error(f"Unexpected error extracting text from file: {e}")
#         return {"text": None, "ocr_confidence": 0.0}


# def extract_text_from_file(file_path, file_type):
#     """
#     Extract text from a file using pdfplumber for PDFs and Azure Computer Vision OCR for images.
#
#     Args:
#         file_path (str): Path to the file to process.
#         file_type (str): MIME type of the file.
#
#     Returns:
#         dict: A dictionary containing extracted text and confidence score.
#     """
#     try:
#         if file_type == "application/pdf":
#             logger.info(f"Processing image file: {file_path}")
#             with open(file_path, "rb") as file_stream:
#                 read_response = cv_client.read_in_stream(file_stream, raw=True)
#
#             # Get the operation ID for polling
#             operation_location = read_response.headers["Operation-Location"]
#             operation_id = operation_location.split("/")[-1]
#
#             # Poll for the result
#             while True:
#                 result = cv_client.get_read_result(operation_id)
#                 if result.status not in ["notStarted", "running"]:
#                     break
#
#             if result.status == OperationStatusCodes.succeeded:
#                 # Extract text lines
#                 lines = []
#                 for read_result in result.analyze_result.read_results:
#                     for line in read_result.lines:
#                         lines.append(line.text)
#
#                 return {
#                     "text": " ".join(lines).strip(),
#                     "ocr_confidence": 100.0 if lines else 0.0
#                 }
#             else:
#                 logger.warning("Azure Computer Vision could not extract text from the image.")
#                 return {"text": None, "ocr_confidence": 0.0}
#
#         elif file_type.startswith("image/"):
#             # Process image files with Azure OCR
#             logger.info(f"Processing image file: {file_path}")
#             with open(file_path, "rb") as file_stream:
#                 read_response = cv_client.read_in_stream(file_stream, raw=True)
#
#             # Get the operation ID for polling
#             operation_location = read_response.headers["Operation-Location"]
#             operation_id = operation_location.split("/")[-1]
#
#             # Poll for the result
#             while True:
#                 result = cv_client.get_read_result(operation_id)
#                 if result.status not in ["notStarted", "running"]:
#                     break
#
#             if result.status == OperationStatusCodes.succeeded:
#                 # Extract text lines
#                 lines = []
#                 for read_result in result.analyze_result.read_results:
#                     for line in read_result.lines:
#                         lines.append(line.text)
#
#                 return {
#                     "text": " ".join(lines).strip(),
#                     "ocr_confidence": 100.0 if lines else 0.0
#                 }
#             else:
#                 logger.warning("Azure Computer Vision could not extract text from the image.")
#                 return {"text": None, "ocr_confidence": 0.0}
#
#         else:
#             logger.error(f"Unsupported file type: {file_type}")
#             return {"text": None, "ocr_confidence": 0.0}
#
#     except Exception as e:
#         logger.error(f"Error extracting text from file: {e}")
#         return {"text": None, "ocr_confidence": 0.0}


# def extract_text_from_file(file_path, file_type):
#     """
#     Extract text from a file using Azure Computer Vision, Tesseract, or PyPDF2.
#
#     Args:
#         file_path (str): Path to the file to process.
#         file_type (str): MIME type of the file (e.g., "application/pdf", "image/png").
#
#     Returns:
#         str: Extracted text content.
#     """
#     try:
#         if file_type.startswith("image/"):
#             # Process image files
#             logger.info(f"Processing image file: {file_path}")
#             with open(file_path, "rb") as file_stream:
#                 read_response = cv_client.read_in_stream(file_stream, raw=True)
#
#             # Get the operation ID for polling
#             operation_location = read_response.headers["Operation-Location"]
#             operation_id = operation_location.split("/")[-1]
#
#             # Poll for the result
#             while True:
#                 result = cv_client.get_read_result(operation_id)
#                 if result.status not in ["notStarted", "running"]:
#                     break
#
#             if result.status == OperationStatusCodes.succeeded:
#                 # Extract text lines
#                 extracted_text = " ".join(
#                     [line.text for read_result in result.analyze_result.read_results for line in read_result.lines]
#                 )
#                 return extracted_text.strip()
#             else:
#                 logger.warning("Azure Computer Vision could not extract text from the image.")
#                 return None
#
#         elif file_type == "application/pdf":
#             # Process PDF files
#             logger.info(f"Processing PDF file: {file_path}")
#             text = ""
#             with open(file_path, "rb") as f:
#                 reader = PdfReader(f)
#                 for page in reader.pages:
#                     text += page.extract_text()
#             return text.strip()
#
#         elif file_type in [
#             "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
#             "application/vnd.ms-excel"
#         ]:
#             # Process Excel files
#             logger.info(f"Processing Excel file: {file_path}")
#             df = pd.read_excel(file_path)
#             return df.to_string()
#
#         else:
#             logger.error(f"Unsupported file type: {file_type}")
#             return None
#     except Exception as e:
#         logger.error(f"Error extracting text from file: {e}")
#         return None

# def preprocess_textpreprocess_text(text):
#     """
#     Preprocess text by cleaning, normalizing, and removing stop words.
#
#     Args:
#         text (str): Input text to preprocess.
#
#     Returns:
#         str: Preprocessed text.
#     """
#
#     try:
#         nlp = spacy.load("en_core_web_sm")
#
#         # Convert to lowercase and remove special characters
#         text = text.lower()
#         text = re.sub(r"[^a-zA-Z0-9\s.,]", "", text)
#
#         # Remove extra spaces
#         text = re.sub(r"\s+", " ", text).strip()
#
#         # Remove stop words and lemmatize
#         doc = nlp(text)
#         processed_text = " ".join(
#             token.lemma_ for token in doc if not token.is_stop and not token.is_punct
#         )
#         return processed_text
#     except Exception as e:
#         logger.error(f"Error during text preprocessing: {e}")
#         return text  # Return the original text if preprocessing fails


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


# from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
#
# file_path = r"C:\Users\Ilyas\Pictures\INVOICE.jpg"
# with open(file_path, "rb") as file_stream:
#     read_response = cv_client.read_in_stream(file_stream, raw=True)
#
# operation_location = read_response.headers["Operation-Location"]
# operation_id = operation_location.split("/")[-1]
#
# while True:
#     result = cv_client.get_read_result(operation_id)
#     if result.status not in ["notStarted", "running"]:
#         break
#
# if result.status == OperationStatusCodes.succeeded:
#     extracted_text = " ".join(
#         [line.text for read_result in result.analyze_result.read_results for line in read_result.lines]
#     )
#     print("Extracted Text:", extracted_text)
# else:
#     print("Azure Computer Vision failed.")

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
        # Ensure Azure OpenAI is properly configured
        import openai
        import os
        from app.utils.app_config import embedding_model, embedding_key
        
        # Configure for Azure OpenAI embeddings
        openai.api_type = "azure"
        openai.api_base = os.getenv("AZURE_OPENAI_API_BASE")
        openai.api_version = "2024-10-01-preview"
        openai.api_key = embedding_key or os.getenv("AZURE_OPENAI_API_KEY")
        
        # Use the correct Azure API call format
        response = openai.Embedding.create(
            input=[text],
            engine=embedding_model  # For Azure, use 'engine' not 'model'
        )
        return response["data"][0]["embedding"]
    except Exception as e:
        logger.error(f"Error generating embedding: {str(e)}")
        # Return a dummy embedding as fallback
        import numpy as np
        return np.random.randn(1536).tolist()  # text-embedding-3-large has 1536 dimensions

def retrieve_relevant_chunksRAG_for_ucp(query_text, top_k=5):
    try:
        embedding = get_embedding(query_text)
        results = collection_ucp_rules.query(query_embeddings=[embedding], n_results=top_k)

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
        print(f"❌ Error retrieving UCP600 chunks: {e}")
        return []


def retrieve_relevant_chunksRAG_for_swift(query_text, top_k=5):
    try:
        embedding = get_embedding(query_text)
        results = collection_swift_rules.query(query_embeddings=[embedding], n_results=top_k)

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
        print(f"❌ Error retrieving SWIFT chunks: {e}")
        return []

def retrieve_relevant_chunksRAG_for_clause_tag(query_text, top_k=5):
    try:
        embedding = get_embedding(query_text)
        results = collection_clause_tag.query(query_embeddings=[embedding], n_results=top_k)

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
        print(f"❌ Error retrieving SWIFT chunks: {e}")
        return []


def load_custom_rules(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Failed to load custom rules: {e}")
        return []


client = chromadb.HttpClient(host="localhost", port=8000)
collection_all_rules = client.get_or_create_collection("all_rules")
def retrieve_relevant_chunksRAG(query, top_k=5):
    embedding = get_embedding_azureRAG(query)
    results = collection_all_rules.query(query_embeddings=[embedding], n_results=top_k)
    return [
        {
            "file_name": meta.get("source", "unknown"),
            "text": doc,
            "article": meta.get("article", "N/A")
        }
        for doc, meta in zip(results["documents"][0], results["metadatas"][0])
    ]



# if __name__ == "__main__":
#     # Path to the PDF file
#     pdf_path = r"C:\RiyadSCFCE5.1\apache-tomcat-9.0.37\webapps\SCFCEWeb\Default\SCRN\IMLC_ApplyImpLc.jsp"
#     result = extract_mandatory_fields(pdf_path)
#     print(f"result {resu