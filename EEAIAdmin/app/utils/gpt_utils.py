import logging
import os

import openai
import json
import re

from app.utils.app_config import deployment_name
from app.utils.file_utils import retrieve_relevant_chunks

logger = logging.getLogger(__name__)


def generate_llm_insights(data, user_query):
    """
    Uses an LLM to generate insights or summarize query results.

    Args:
        data (list or dict): Data to analyze (e.g., query results).
        user_query (str): Original user query for context in LLM analysis.

    Returns:
        str: LLM-generated insights or summary.
    """
    prompt = f"""
    You are an intelligent assistant. The user asked: "{user_query}". 
    The application provided the following data sample:
    {json.dumps(data, indent=2)}

    Analyze the data and provide a summary. Highlight patterns, anomalies, or trends. 
    Suggest any relevant visualizations to better understand the data.
    """
    try:
        response = openai.ChatCompletion.create(
            engine=deployment_name,
            messages=[
                {"role": "system", "content": "You are a data insights assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500
        )
        insights = response["choices"][0]["message"]["content"].strip()
        logger.info(f"Generated Insights: {insights}")
        return insights
    except Exception as e:
        logger.error(f"Error generating insights: {e}")
        return "Failed to generate insights."


# def analyze_document_with_gpt(extracted_text, userQuery=None, annotations=None):
#     """
#     Analyze and classify the document content using GPT.
#
#     Args:
#         extracted_text (str): The extracted text from a document.
#
#     Returns:
#         dict: The analysis results, including the document type and extracted details.
#     """
#     prompt = f"""
#         You are an intelligent assistant for document analysis.
#         Analyze the following text to classify the document and extract key details:
#
#         Text:
#         {extracted_text}
#
#         Classify the document into one of the following types:
#         - 'invoice': Contains details like Invoice Number, Amount, Vendor Name, currency, due date , invoice date(dd/mm/yy), etc.
#         - 'export_collection': Includes transaction details, drawee information, etc.
#         - 'letter_of_credit': Contains LC numbers, beneficiary names, issuing bank, etc.
#         - 'bank_guarantee': Includes guarantee amount, expiry date, etc.
#         - 'unknown': Identify the type of document , extract information based on user query {userQuery} and annotations {annotations}
#
#         Based on the classification, extract relevant fields:
#         - For 'invoice': Invoice Number, Invoice Date(dd/mm/yy), Due Date(dd/mm/yy), Total Amount, Tax Amount, counter party, Customer Name, currency.
#         - For 'export_collection': Transaction Date, Type of Collection, Customer Number, Exporter Reference, Drawer Name, Drawee Name.
#         - For 'letter_of_credit': LC Number, Beneficiary Name, Issuing Bank, Expiry Date, Amount, Currency.
#         - For 'bank_guarantee': Guarantee Number, Amount, Expiry Date, Beneficiary, Issuing Bank.
#         - For 'unknown': extract information based on user query {userQuery} and annotations {annotations}
#
#         Provide the result in JSON format:
#         {{
#             "document_type": "type",
#             "extracted_fields": {{}},
#             "confidence_score": confidence_percentage
#         }}
#         """
#     try:
#         response = openai.ChatCompletion.create(
#             engine=deployment_name,
#             messages=[
#                 {"role": "system", "content": "You are a document analysis assistant."},
#                 {"role": "user", "content": prompt}
#             ],
#             temperature=0.3,
#             max_tokens=2000
#         )
#         result = response["choices"][0]["message"]["content"].strip()
#         logger.info(f"Document Analysis Result: {result}")
#
#         # Extract JSON portion from response
#         import re
#         json_match = re.search(r"({.*})", result, re.DOTALL)  # Regex to find the JSON part
#         if json_match:
#             json_text = json_match.group(1)
#             return json.loads(json_text)
#         else:
#             logger.error("Failed to find JSON in GPT response.")
#             return {"error": "Invalid response format from GPT."}
#     except Exception as e:
#         logger.error(f"Error analyzing document with GPT: {e}")
#         return {"error": "Failed to analyze the document."}

# def analyze_document_with_gpt(extracted_text, userQuery=None, annotations=None):
#     """
#     Analyze and classify the document content using GPT.
#
#     Args:
#         extracted_text (str): The extracted text from a document.
#
#     Returns:
#         dict: The analysis results, including the document type and extracted details.
#     """
#     prompt = f"""
#         You are an intelligent assistant for document analysis.
#         Analyze the following text to classify the document and extract key details:
#
#         Text:
#         {extracted_text}
#
#         Classify the document into one of the following types:
#         - 'invoice': Contains details like Invoice Number, Amount, Vendor Name, currency, due date, invoice date(dd/mm/yy), etc.
#         - 'export_collection': Includes transaction details, drawee information, etc.
#         - 'letter_of_credit': Contains LC numbers, beneficiary names, issuing bank, etc.
#         - 'bank_guarantee': Includes guarantee amount, expiry date, etc.
#         - 'unknown': Identify the type of document, extract information based on user query {userQuery} and annotations {annotations}
#
#         Based on the classification, extract relevant fields:
#         - For 'invoice': invoice_number, invoice_date, due_date, total_amount, tax_amount, counterparty, customer_Name, currency.
#         - For 'export_collection': Transaction Date, Type of Collection, Customer Number, Exporter Reference, Drawer Name, Drawee Name.
#         - For 'letter_of_credit': LC Number, Beneficiary Name, Issuing Bank, Expiry Date, Amount, Currency.
#         - For 'bank_guarantee': Guarantee Number, Amount, Expiry Date, Beneficiary, Issuing Bank.
#         - For 'unknown': Extract information based on user query {userQuery} and annotations {annotations}.
#
#         **Extraction Requirements**:
#             - Extract fields relevant to the classified document type.
#             - For currency symbols like `$`, `SAR`, or `AED`, infer the currency name (e.g., USD, Saudi Riyal, UAE Dirham).
#
#         Provide the result in JSON format:
#         {{
#             "document_type": "type",
#             "extracted_fields": {{}},
#             "confidence_score": confidence_score
#         }}
#     """
#     try:
#         response = openai.ChatCompletion.create(
#             engine=deployment_name,
#             messages=[
#                 {"role": "system", "content": "You are a document analysis assistant."},
#                 {"role": "user", "content": prompt}
#             ],
#             temperature=0.3,
#             max_tokens=2000
#         )
#         result = response["choices"][0]["message"]["content"].strip()
#         logger.info(f"Document Analysis Result: {result}")
#
#         # Extract JSON portion from response
#         import re
#         json_match = re.search(r"({.*})", result, re.DOTALL)  # Regex to find the JSON part
#         if json_match:
#             json_text = json_match.group(1)
#             parsed_json = json.loads(json_text)
#
#             # Standardize confidence score
#             confidence_score = parsed_json.get("confidence_score")
#             if isinstance(confidence_score, str):
#                 # Map string values to numeric ranges
#                 confidence_map = {"high": 0.9, "medium": 0.7, "low": 0.5}
#                 parsed_json["confidence_score"] = confidence_map.get(confidence_score.lower(), 0.5)
#             elif isinstance(confidence_score, float) and 0 <= confidence_score <= 1:
#                 # If it's a decimal, ensure it's within the range
#                 parsed_json["confidence_score"] = round(confidence_score, 2)
#             else:
#                 # Default to a fallback value
#                 parsed_json["confidence_score"] = 0.0
#
#             return parsed_json
#         else:
#             logger.error("Failed to find JSON in GPT response.")
#             return {"error": "Invalid response format from GPT."}
#     except Exception as e:
#         logger.error(f"Error analyzing document with GPT: {e}")
#         return {"error": "Failed to analyze the document."}

# def extract_json_from_response(response_text):
#     """Extract JSON object from GPT response."""
#     try:
#         json_match = re.search(r"({.*})", response_text, re.DOTALL)
#         if json_match:
#             return json.loads(json_match.group(1))
#         else:
#             return None
#     except Exception as e:
#         logger.error(f"Error extracting JSON: {e}")
#         return None
def extract_json_from_response(response):
    """

    Extracts and sanitizes JSON content from a GPT response.

    Args:

        response (str): The raw GPT response.

    Returns:

        dict: The extracted and cleaned JSON content.

    """

    try:

        match = re.search(r"\{.*\}", response, re.DOTALL)

        if match:

            json_content = match.group(0)

            json_content = re.sub(r'[\x00-\x1F\x7F]', '', json_content)

            return json.loads(json_content)

        else:

            raise ValueError("No JSON block found in the response.")

    except json.JSONDecodeError as e:

        print(f"Failed to decode JSON: {e}")

        raise ValueError(f"Invalid JSON format in GPT response: {e}")


def map_confidence_score(confidence_score):
    """Standardize confidence score."""
    confidence_map = {"high": 0.9, "medium": 0.7, "low": 0.5}
    if isinstance(confidence_score, str):
        return confidence_map.get(confidence_score.lower(), 0.5)
    elif isinstance(confidence_score, (int, float)) and 0 <= confidence_score <= 1:
        return round(confidence_score, 2)
    return 0.0


def load_extraction_fields(product_name, document_type):
    """
    Load required extraction fields dynamically based on product and document type.
    """
    # Full path to the correct function_fields.json
    config_path = os.path.join(
        os.path.dirname(__file__), "prompts", "EE", "function_fields.json"
    )

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"function_fields.json not found at {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    return config.get(product_name, {}).get(document_type, {})


def detect_document_type(extracted_text):
    text = extracted_text.lower()
    if "guarantee" in text or "bond" in text:
        return "bank_guarantee"
    elif "letter of credit" in text or "lc" in text:
        return "letter_of_credit"
    return None


def load_prompt(document_type, extracted_text, product_name=None, function_name=None):
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    PROMPT_DIRECTORY = os.path.join(BASE_DIR, "prompts", product_name or "")
    prompt_path = os.path.join(PROMPT_DIRECTORY, f"{document_type}.txt")

    logger.info(f"📌 Loading prompt for document type: {document_type}")
    logger.info(f"📌 Product: {product_name}, Function: {function_name}")

    if not os.path.exists(prompt_path):
        logger.warning(f"Prompt file not found for '{document_type}' at {prompt_path}")
        return ""  # Return safe fallback

    with open(prompt_path, "r", encoding="utf-8") as file:
        content = file.read()

    extracted_text_str = (
        " ".join([entry["text"] for entry in extracted_text])
        if isinstance(extracted_text, list)
        else str(extracted_text)
    )

    formatted_fields = ""
    if product_name and function_name:
        try:
            fields = load_extraction_fields(product_name, function_name)
            if isinstance(fields, dict):
                formatted_fields = "\n".join([f"- **{field}**: {desc}" for field, desc in fields.items()])
            else:
                logger.warning("Expected fields to be a dictionary.")
        except Exception as e:
            logger.warning(f"Failed to load fields: {e}")

    # Ensure fallback if fields are missing
    if not formatted_fields:
        formatted_fields = "- Field1: Description\n- Field2: Description"

    updated_content = (
        content.replace("{extracted_text}", extracted_text_str)
        .replace("{extracted_fields}", formatted_fields)
    )

    logger.info(f"✅ Loaded and updated prompt for {document_type}")
    return updated_content


# def load_prompt(document_type, extracted_text, product_name=None, function_name=None):
#     """
#     Load the prompt template from a file and dynamically insert extracted text and field descriptions.
#
#     Args:
#         document_type (str): The type of document being analyzed.
#         extracted_text (str or list): The OCR-extracted text.
#         product_name (str): The product name (e.g., "EE", "CE").
#         function_name (str): The function or operation (e.g., "register_import_lc").
#
#     Returns:
#         str: Final prompt content with placeholders replaced.
#     """
#     BASE_DIR = os.path.dirname(os.path.abspath(__file__))
#     PROMPT_DIRECTORY = os.path.join(BASE_DIR, "prompts", product_name or "")
#     prompt_path = os.path.join(PROMPT_DIRECTORY, f"{document_type}.txt")
#
#     if not os.path.exists(prompt_path):
#         logger.warning(f"Prompt file not found for '{document_type}' at {prompt_path}")
#         return None
#
#     with open(prompt_path, "r", encoding="utf-8") as file:
#         content = file.read()
#
#     # Handle extracted text
#     extracted_text_str = (
#         " ".join([entry["text"] for entry in extracted_text])
#         if isinstance(extracted_text, list)
#         else str(extracted_text)
#     )
#
#     # Load dynamic field descriptions
#     formatted_fields = ""
#     if product_name and function_name:
#         try:
#             fields = load_extraction_fields(product_name, function_name)
#             if isinstance(fields, dict):
#                 formatted_fields = "\n".join([f"- **{field}**: {desc}" for field, desc in fields.items()])
#             else:
#                 logger.warning("Expected fields to be a dictionary of {field: description}")
#         except Exception as e:
#             logger.warning(f"Failed to load fields from config: {e}")
#
#     # Replace placeholders in prompt
#     updated_content = (
#         content.replace("{extracted_text}", extracted_text_str)
#                .replace("{extracted_fields}", formatted_fields)
#     )
#
#     logger.info(f"✅ formatted_fields is  {formatted_fields}")
#
#     logger.info(f"✅ updated_content is  {updated_content}")
#
#     logger.info(f"✅ Loaded and updated prompt for {document_type}")
#     return updated_content

# def load_prompt(document_type, extracted_text):
#     """
#     Load the prompt template from a file based on the document type and replace {extracted_text}.
#     Ensures extracted_text is a string before replacement.
#     """
#     BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Get script's directory
#     PROMPT_DIRECTORY = os.path.join(BASE_DIR, "prompts")
#
#     prompt_path = os.path.join(PROMPT_DIRECTORY, f"{document_type}.txt")
#
#     if not os.path.exists(prompt_path):
#         logger.warning(f"Prompt file not found for '{document_type}'. Using default template.")
#         return None
#
#     with open(prompt_path, "r", encoding="utf-8") as file:
#         content = file.read()
#
#     # Ensure extracted_text is a string
#     extracted_text_str = extracted_text.get('text', '') if isinstance(extracted_text, dict) else str(extracted_text)
#
#     # Replace {extracted_text} placeholder dynamically
#     updated_content = content.replace("{extracted_text}", extracted_text_str)
#
#     print(f"✅ Successfully loaded and updated prompt for {document_type}:\n{updated_content}")  # Debugging
#     return updated_content


import logging
import json
import openai
import difflib  # For fuzzy matching

import logging
import json
import difflib  # For fuzzy matching

# def analyze_document_with_gpt(extracted_text, ocr_data=None, userQuery=None, annotations=None):
#     """
#     Analyze the extracted text using GPT and map extracted fields back to OCR bounding boxes.
#
#     Args:
#         extracted_text (str): The extracted text from the document.
#         ocr_data (list): List of text data with bounding boxes from OCR.
#         userQuery (str): Specific query for document analysis.
#         annotations (dict): User annotations.
#
#     Returns:
#         dict: JSON response with extracted fields and their bounding boxes.
#     """
#     if not extracted_text.strip():
#         logging.error("Extracted text is empty. Unable to analyze document.")
#         return {"error": "No text extracted from document."}
#
#     userQuery = userQuery.lower()  # Convert to lowercase for consistency
#
#     # Identify document type based on user query
#     if "letter_of_credit" in userQuery:
#         userQuery = "letter_of_credit"
#     elif "invoice" in userQuery:
#         userQuery = "invoice_details"
#     elif "export_collection" in userQuery:
#         userQuery = "export_collection"
#     elif "bank_guarantee" in userQuery:
#         userQuery = "bank_guarantee"
#     else:
#         userQuery = None  # No specific prompt found
#
#     prompt = load_prompt(userQuery, ocr_data) if userQuery else None
#
#     print(f"prompt is {prompt}")
#
#     # If document type is unknown, use a generic classification prompt
#     if not prompt:
#         prompt = f"""
#         You are an intelligent document analysis assistant.
#         Analyze the given text and classify it as one of the following document types:
#
#         - 'invoice': Contains Invoice Number, Amount, Vendor Name, currency, due date, invoice date.
#         - 'export_collection': Includes transaction details, drawee information, etc.
#         - 'letter_of_credit': Contains LC numbers, beneficiary names, issuing bank, etc.
#         - 'bank_guarantee': Includes guarantee amount, expiry date, etc.
#         - 'unknown': If document type is unclear, extract key details based on user query {userQuery} and annotations {annotations}.
#
#         Extract the relevant fields for the classified document type.
#
#         **Extraction Rules**:
#         - Dates should be in 'YYYY-MM-DD' format.
#         - Numeric values should not contain currency symbols.
#         - If a field is missing, return `null`.
#
#         **Text to Analyze**:
#         {extracted_text}
#
#         **Provide the result in JSON format**:
#         {{
#             "document_type": "type",
#             "extracted_fields": {{}},
#             "confidence_score": confidence_score
#         }}
#         """
#
#     try:
#         response = openai.ChatCompletion.create(
#             engine=deployment_name,
#             messages=[
#                 {"role": "system", "content": "You are a document analysis assistant."},
#                 {"role": "user", "content": prompt}
#             ],
#             temperature=0.2,
#             max_tokens=2000,
#         )
#
#         # Extract response content
#         result = response["choices"][0]["message"]["content"].strip()
#         logging.info(f"GPT Analysis Result: {result}")
#
#         # Parse JSON response
#         parsed_json = extract_json_from_response(result)
#
#         if parsed_json:
#             extracted_fields = parsed_json.get("extracted_fields", {})
#
#             # **Map extracted fields to OCR bounding boxes**
#             annotated_fields = {}
#             for field_name, field_value in extracted_fields.items():
#                 # **Convert numeric values to strings to prevent iteration errors**
#                 if isinstance(field_value, (int, float)):
#                     field_value = str(field_value)
#
#                 # **Fuzzy match field value to OCR text**
#                 matching_entry = find_best_ocr_match(field_value, ocr_data)
#
#                 annotated_fields[field_name] = {
#                     "value": field_value,
#                     "bounding_box": matching_entry["bounding_box"] if matching_entry else None
#                 }
#
#             parsed_json["annotated_fields"] = annotated_fields
#             return parsed_json
#
#         else:
#             logging.error("Failed to extract valid JSON from GPT response.")
#             return {"error": "Invalid GPT response format"}
#
#     except Exception as e:
#         logging.error(f"Error analyzing document with GPT: {e}")
#         return {"error": "Failed to analyze the document."}

# def analyze_document_with_gpt(extracted_text, ocr_data=None, userQuery=None, annotations=None):
#     """
#     Analyze the extracted text using GPT and map extracted fields back to OCR bounding boxes after analysis.
#
#     Args:
#         extracted_text (str): The extracted text from the document.
#         ocr_data (list): List of text data with bounding boxes from OCR.
#         userQuery (str): Specific query for document analysis.
#         annotations (dict): User annotations.
#
#     Returns:
#         dict: JSON response with extracted fields and their bounding boxes.
#     """
#     if not extracted_text.strip():
#         logging.error("Extracted text is empty. Unable to analyze document.")
#         return {"error": "No text extracted from document."}
#
#     userQuery = userQuery.lower() if userQuery else ""
#
#     # Identify document type based on user query
#     if "letter_of_credit" in userQuery:
#         userQuery = "letter_of_credit"
#     elif "invoice" in userQuery:
#         userQuery = "invoice_details"
#     elif "export_collection" in userQuery:
#         userQuery = "export_collection"
#     elif "bank_guarantee" in userQuery:
#         userQuery = "bank_guarantee"
#     else:
#         userQuery = None  # No specific prompt found
#
#     # Load the appropriate GPT prompt template
#     prompt = load_prompt(userQuery, extracted_text) if userQuery else None
#
#     print(f"Prompt being sent to GPT: {prompt}")
#
#     # If no specific document type is found, use a generic classification prompt
#     if not prompt:
#         prompt = f"""
#         You are an intelligent document analysis assistant.
#         Analyze the given text and classify it as one of the following document types:
#
#         - 'invoice': Contains Invoice Number, Amount, Vendor Name, currency, due date, invoice date.
#         - 'export_collection': Includes transaction details, drawee information, etc.
#         - 'letter_of_credit': Contains LC numbers, beneficiary names, issuing bank, etc.
#         - 'bank_guarantee': Includes guarantee amount, expiry date, etc.
#         - 'unknown': If document type is unclear, extract key details based on user query {userQuery} and annotations {annotations}.
#
#         Extract the relevant fields for the classified document type.
#
#         **Text to Analyze**:
#         {extracted_text}
#
#         **Provide the result in JSON format**:
#         {{
#             "document_type": "type",
#             "extracted_fields": {{}},
#             "confidence_score": confidence_score
#         }}
#         """
#
#     try:
#         response = openai.ChatCompletion.create(
#             engine=deployment_name,
#             messages=[
#                 {"role": "system", "content": "You are a document analysis assistant."},
#                 {"role": "user", "content": prompt}
#             ],
#             temperature=0.0,
#             max_tokens=8000,
#         )
#
#         # Extract response content
#         result = response["choices"][0]["message"]["content"].strip()
#         logging.info(f"GPT Analysis Result: {result}")
#
#         # Parse JSON response
#         parsed_json = extract_json_from_response(result)
#
#         if parsed_json:
#             extracted_fields = parsed_json.get("extracted_fields", {})
#
#             # **Ensure Bounding Boxes Are Assigned AFTER GPT Analysis**
#             if ocr_data:
#                 for field_name, field_info in extracted_fields.items():
#                     field_value = field_info.get("value")
#
#                     if field_value:
#                         # Convert numeric values to strings for safe matching
#                         if isinstance(field_value, (int, float)):
#                             field_value = str(field_value)
#
#                         # **Find the closest match for the extracted field in OCR data**
#                         print(f"field value {field_value}")
#                         print(f"field value {field_value}")
#                         matching_entry = find_best_ocr_match(field_value, ocr_data)
#
#                         # Update field with bounding box if a match is found
#                         extracted_fields[field_name]["bounding_box"] = matching_entry.get("bounding_box") if matching_entry else None
#                         extracted_fields[field_name]["bounding_page"] = matching_entry.get("bounding_page") if matching_entry else None
#
#             parsed_json["extracted_fields"] = extracted_fields
#             print(f"final JSON response is : {parsed_json}")
#             return parsed_json
#
#         else:
#             logging.error("Failed to extract valid JSON from GPT response.")
#             return {"error": "Invalid GPT response format"}
#
#     except Exception as e:
#         logging.error(f"Error analyzing document with GPT: {e}")
#         return {"error": "Failed to analyze the document."}

import re
import json
import logging
import openai


def clean_text(text):
    """Normalize text by removing special characters and extra spaces."""
    return re.sub(r'\W+', ' ', text).strip().lower()


def format_ocr_data_for_prompt(ocr_data):
    """Formats OCR data for use in GPT prompt."""
    formatted = ""
    for i, entry in enumerate(ocr_data):
        text = entry.get("text", "").replace("\n", " ")
        box = entry.get("bounding_box", [])
        page = entry.get("bounding_page", 0)
        formatted += f"{i + 1}. Text: \"{text}\"\n   Box: {box}, Page: {page}\n"
    return formatted


def extract_json_from_gpt_response(text):
    """Extracts the first valid JSON object from GPT response."""
    try:
        json_str = re.search(r'\{[\s\S]+\}', text).group()
        return json.loads(json_str)
    except Exception as e:
        logging.error(f"Could not parse JSON from GPT response: {e}")
        return None


def analyze_document_with_gpt(extracted_text, ocr_data=None, userQuery=None, annotations=None, productName=None,
                              functionName=None):
    """
    Analyze the extracted text using GPT and map extracted fields back to OCR bounding boxes in one GPT call.

    Args:
        extracted_text (str): The extracted text from the document.
        ocr_data (list): List of text data with bounding boxes from OCR.
        userQuery (str): Specific query for document analysis.
        annotations (dict): User annotations.

    Returns:
        dict: JSON response with extracted fields and their bounding boxes.
    """
    if not extracted_text.strip():
        logging.error("Extracted text is empty. Unable to analyze document.")
        return {"error": "No text extracted from document."}

    userQuery = userQuery.lower() if userQuery else ""

    # Identify document type based on user query
    if "letter_of_credit" in userQuery:
        userQuery = "letter_of_credit"
    elif "invoice" in userQuery:
        userQuery = "invoice_details"
    elif "export_collection" in userQuery:
        userQuery = "export_collection"
    elif "bank_guarantee" in userQuery:
        userQuery = "bank_guarantee"
    else:
        userQuery = None

    try:
        # Step 1: Extract fields using GPT
        if userQuery:
            prompt = load_prompt(userQuery, extracted_text, productName, functionName)
        else:
            prompt = f"""
You are a document analysis assistant.
Analyze the given document text and classify it as one of these types:
- invoice
- export_collection
- letter_of_credit
- bank_guarantee
- unknown

Extract relevant fields for the type you classify.

Text to Analyze:
{extracted_text}

Return this JSON:
{{
  "document_type": "type",
  "extracted_fields": {{
    "Field Name": {{
      "value": "field value"
      "desc": "<FIELD_DESCRIPTION>",
    }}
  }},
  "confidence_score": 0.0 - 1.0
}}
"""

        response = openai.ChatCompletion.create(
            engine=deployment_name,
            messages=[
                {"role": "system", "content": "You are a document analysis assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
        )

        result = response["choices"][0]["message"]["content"].strip()
        logging.info(f"GPT field extraction result: {result}")
        parsed_json = extract_json_from_gpt_response(result)

        if not parsed_json:
            return {"error": "Invalid GPT response format"}

        extracted_fields = parsed_json.get("extracted_fields", {})

        # Step 2: Map bounding boxes using GPT (in one call)
        if ocr_data and extracted_fields:
            field_description = "\n".join(
                [f"- {k}: {v.get('value', '')}" for k, v in extracted_fields.items()]
            )
            ocr_text = format_ocr_data_for_prompt(ocr_data)

            map_prompt = f"""
You are given the following extracted fields from a document:
{field_description}

And the OCR data from the document with text, bounding boxes, and page numbers:
{ocr_text}

### Extraction Rules:
- Assign a confidence score (0–100%) for each extracted field considering OCR clarity (legibility), keyword proximity, and completeness of the extracted value.

Match each extracted field to the best OCR entry.

Return ONLY this JSON. DO NOT include any explanation:

{{
  "extracted_fields": {{
    "Field Name": {{
      "value": "field value",
      "desc": "<FIELD_DESCRIPTION>",
      "confidence": <confidence_score>,
      "bounding_box": [...],
      "bounding_page": X
    }}
  }} 
}}

If a match can't be found, use null for bounding_box and bounding_page.
"""

            map_response = openai.ChatCompletion.create(
                engine=deployment_name,
                messages=[
                    {"role": "system", "content": "You are a document analysis assistant."},
                    {"role": "user", "content": map_prompt}
                ],
                temperature=0.3,
            )

            map_result = map_response["choices"][0]["message"]["content"].strip()
            mapped_json = extract_json_from_gpt_response(map_result)

            if mapped_json and "extracted_fields" in mapped_json:
                parsed_json["extracted_fields"] = mapped_json["extracted_fields"]
            else:
                logging.warning("Bounding box mapping returned invalid JSON. Retaining original values.")

        logging.info(f"Final JSON response: {parsed_json}")
        return parsed_json

    except Exception as e:
        logging.error(f"Error analyzing document with GPT: {e}")
        return {"error": "Failed to analyze the document."}

def classify_document_gpt(ocr_text):
    prompt = f"""
You are a document classification assistant.

Your task is to analyze unstructured OCR-extracted text and classify the document according to business categories. The classification must be based on domain understanding and real-world context.

### Instructions:

1. Identify the **main category**:
   - Transactional Document
   - Transport Document
   - Communication Message
   - Internal Document

2. Identify the **document type** within that category:
   - Commercial: Invoice, Purchase Order, Packing List, Certificate of Origin, Insurance Certificate, Contract Extract, etc.
   - Transport: Bill of Lading, Airway Bill, Courier Receipt, Shipping Bill, etc.
   - Communication: SWIFT Message, Advice, Cover Letter, etc.
   - Internal: Policy, SOP, Credit Memo, Assessment Sheet, etc.

3. If applicable, identify a **sub-type**:
   - Example: For a Guarantee, specify sub-types like Performance Guarantee, Advance Payment Guarantee, Tender/Bid Bond, etc.

OCR Text:
""{ocr_text}""

Return only this JSON:
{{
  "category": "<Main category>",
  "document_type": "<Specific document type>",
  "sub_type": "<Optional - e.g., Advance Payment Guarantee>"
}}
"""
    try:
        response = openai.ChatCompletion.create(
            engine=deployment_name,
            messages=[
                {"role": "system", "content": "You are a document classification assistant."},
                {"role": "user", "content": prompt.strip()}
            ],
            temperature=0.7,
            max_tokens=600
        )
        content = response["choices"][0]["message"]["content"]
        return extract_json_from_gpt_response(content)

    except Exception as e:
        logging.error(f"Document classification failed: {e}")
        return {
            "category": "unknown",
            "document_type": "unknown",
            "sub_type": None
        }

#
# def clean_text(text):
#     """Normalize text by removing special characters and extra spaces."""
#     return re.sub(r'\W+', ' ', text).strip().lower()
#
# def find_best_ocr_match(field_value, ocr_data):
#     """
#     Finds the best matching OCR text for a given extracted field value using fuzzy matching and substring search.
#
#     Args:
#         field_value (str): The extracted field value from GPT.
#         ocr_data (list): List of OCR-extracted text with bounding boxes.
#
#     Returns:
#         dict: Best matching OCR entry with text, bounding box, and bounding page, or None if no match is found.
#     """
#     if not field_value or not ocr_data:
#         return {}
#
#     # Normalize extracted field value
#     normalized_field_value = clean_text(str(field_value))
#
#     # Normalize OCR text data
#     ocr_entries = [{**entry, "normalized_text": clean_text(entry["text"])} for entry in ocr_data]
#
#     # Step 1: Look for exact substring matches in OCR data
#     for entry in ocr_entries:
#         if normalized_field_value in entry["normalized_text"]:
#             return {
#                 "bounding_box": entry["bounding_box"],
#                 "bounding_page": entry.get("bounding_page")
#             }
#
#     # Step 2: Use fuzzy matching if exact substring match is not found
#     ocr_texts = [entry["normalized_text"] for entry in ocr_entries]
#     best_match = difflib.get_close_matches(normalized_field_value, ocr_texts, n=1, cutoff=0.3)
#
#     if best_match:
#         for entry in ocr_entries:
#             if entry["normalized_text"] == best_match[0]:
#                 return {
#                     "bounding_box": entry["bounding_box"],
#                     "bounding_page": entry.get("bounding_page")
#                 }
#
#     return {}  # No match found


# def analyze_document_with_gpt(extracted_text, userQuery=None, annotations=None):
#     """
#     Analyze and classify the document content using GPT.
#
#     Args:
#         extracted_text (str): The extracted text from a document.
#         userQuery (str): User-specific query for unknown document types.
#         annotations (str): Additional user-provided annotations.
#
#     Returns:
#         dict: The analysis results, including the document type and extracted details.
#     """
#     userQuery = userQuery.lower()  # Convert to lowercase for consistency
#
#     # Identify document type based on user query
#     if "letter_of_credit" in userQuery:
#         userQuery = "letter_of_credit"
#     elif "invoice" in userQuery:
#         userQuery = "invoice"
#     elif "export_collection" in userQuery:
#         userQuery = "export_collection"
#     elif "bank_guarantee" in userQuery:
#         userQuery = "bank_guarantee"
#     else:
#         userQuery = None  # No specific prompt found
#
#     prompt = load_prompt(userQuery, extracted_text) if userQuery else None
#
#     print(f"prompt is {prompt}")
#     # If document type is unknown, use a generic classification prompt
#     if not prompt:
#         prompt = f"""
#             You are an intelligent assistant for document analysis.
#             Analyze the following text to classify the document and extract key details:
#
#             Text:
#             {extracted_text}
#
#             Classify the document into one of the following types:
#             - 'invoice': Contains details like Invoice Number, Amount, Vendor Name, currency, due date, invoice date (dd/mm/yy), etc.
#             - 'export_collection': Includes transaction details, drawee information, etc.
#             - 'letter_of_credit': Contains LC numbers, beneficiary names, issuing bank, etc.
#             - 'bank_guarantee': Includes guarantee amount, expiry date, etc.
#             - 'unknown': Identify the type of document, extract information based on user query {userQuery} and annotations {annotations}.
#
#             Based on the classification, extract relevant fields:
#             `- For 'invoice':
#               - `invoice_number`: Look for variations like 'Invoice #', 'Invoice Number', or just '#'.
#               - `invoice_date`: Must be converted to 'yyyy-mm-dd' format.
#               - `due_date`: Identify terms like 'Payment Due', 'Due Date', or 'Terms Due' or 'Next Billing Date' or 'Billing Date' and convert to 'yyyy-mm-dd' format.
#               - `total_amount`: Numeric only, without currency symbols.
#               - `tax_amount`: Numeric only, without currency symbols.
#               - `currency`: Infer from symbols like `$` (USD), `SAR` (Saudi Riyal), `AED` (UAE Dirham), or explicit mentions in the text.
#               - `counterparty`: The vendor or issuer of the invoice.
#               - `customer_name`: The recipient of the invoice.
#               - `po_number`: The purphase order number of the invoice.`
#
#             - For 'export_collection':
#               Extract Transaction Date, Type of Collection, Customer Number, Exporter Reference, Drawer Name, Drawee Name.
#
#             - For 'letter_of_credit':
#               [('CUST_NO', 'Our Ref Number'), ('FORM_OF_LC', 'Type of LC'), ('LC_CCY', 'LC Currency'), ('LC_AMT', 'LC Amount'), ('AVAL_BY', 'Available By'), ('BENE_NM', 'Beneficiary Name'), ('BENE_ADD1', 'Beneficiary Location'), ('BENE_BK_NM', 'Beneficiary Bank Name'), ('BENE_BK_ADD1', 'Beneficiary Bank Location'), ('EXPIRY_PLC', 'Place of Expiry'), ('PARTIAL_SHIP', 'Partial Shipments'), ('TNSHIP', 'Transhipment'), ('GOODS_DESC', 'Description of Goods'), ('INCOTERMS', 'Incoterms'), ('DOC_PRES', 'Documents to be Presented'), ('CONF_INSTR', 'Confirmation Instruction')].
#
#             - For 'bank_guarantee':
#               Extract Guarantee Number, Amount, Expiry Date, Beneficiary, and Issuing Bank.
#
#             - For 'unknown':
#               Extract information based on user query {userQuery} and annotations {annotations}.
#
#             **Extraction Requirements**:
#             - Dates must always be in 'yyyy-mm-dd' format.
#             - Total amounts and tax amounts must be numeric only, without currency symbols.
#             - If a field is not found in the document, return `null` for that field.
#             - Infer currency names from symbols like `$`, `SAR`, or `AED`. Prioritize names (e.g., USD, Saudi Riyal) if both symbol and name are present.
#
#
#             Provide the result in JSON format:
#             {{
#                 "document_type": "type",
#                 "extracted_fields": {{}},
#                 "confidence_score": confidence_score,
#                 "extracted_text" : {extracted_text}
#             }}
#         """
#     try:
#         response = openai.ChatCompletion.create(
#             engine=deployment_name,
#             messages=[
#                 {"role": "system", "content": "You are a document analysis assistant."},
#                 {"role": "user", "content": prompt}
#             ],
#             temperature=0.0,
#             max_tokens=3000,
#         )
#         result = response["choices"][0]["message"]["content"].strip()
#         logger.info(f"Document Analysis Result: {result}")
#
#         # Extract JSON portion from response
#         parsed_json = extract_json_from_response(result)
#         if parsed_json:
#             # Standardize confidence score
#             parsed_json["confidence_score"] = map_confidence_score(parsed_json.get("confidence_score"))
#             return parsed_json
#         else:
#             logger.error("Failed to find JSON in GPT response.")
#             return {"error": "Invalid response format from GPT."}
#     except Exception as e:
#         logger.error(f"Error analyzing document with GPT: {e}")
#         return {"error": "Failed to analyze the document."}


# def analyze_document_with_gpt(extracted_text):
#     """
#     Analyze and classify the document content using GPT.
#
#     Args:
#         extracted_text (str): The extracted text from a document.
#
#     Returns:
#         dict: The analysis results, including the document type and extracted details.
#     """
#     prompt = f"""
#     You are an intelligent assistant for document analysis.
#     Analyze the following text to classify the document and extract key details:
#
#     Text:
#     {extracted_text}
#
#     Classify the document into one of the following types:
#     - 'invoice': Contains details like Invoice Number, Amount, Vendor Name, etc.
#     - 'export_collection': Includes transaction details, drawee information, etc.
#     - 'letter_of_credit': Contains LC numbers, beneficiary names, issuing bank, etc.
#     - 'bank_guarantee': Includes guarantee amount, expiry date, etc.
#     - 'unknown': If the document doesn't match any of the above.
#
#     Based on the classification, extract relevant fields:
#     - For 'invoice': Invoice Number, Invoice Date, Due Date, Total Amount, Tax Amount, Vendor Name, Customer Name.
#     - For 'export_collection': Transaction Date, Type of Collection, Customer Number, Exporter Reference, Drawer Name, Drawee Name.
#     - For 'letter_of_credit': LC Number, Beneficiary Name, Issuing Bank, Expiry Date, Amount, Currency.
#     - For 'bank_guarantee': Guarantee Number, Amount, Expiry Date, Beneficiary, Issuing Bank.
#     - For 'unknown': Explain why the document couldn't be classified.
#
#     Provide the result in JSON format:
#     {{
#         "document_type": "type",
#         "extracted_fields": {{}}
#     }}
#     """
#     try:
#         response = openai.ChatCompletion.create(
#             engine=deployment_name,
#             messages=[
#                 {"role": "system", "content": "You are a document analysis assistant."},
#                 {"role": "user", "content": prompt}
#             ],
#             temperature=0.3,
#             max_tokens=1500
#         )
#         result = response["choices"][0]["message"]["content"].strip()
#         logger.info(f"Document Analysis Result: {result}")
#
#         try:
#             # Attempt to parse the result as JSON
#             analysis_result = json.loads(result)
#             return analysis_result
#         except json.JSONDecodeError as e:
#             logger.error(f"Failed to parse GPT response as JSON: {e}")
#             return {"error": "Invalid response format from GPT."}
#     except Exception as e:
#         logger.error(f"Error analyzing document with GPT: {e}")
#         return {"error": "Failed to analyze the document."}


def map_query_to_api(user_query, api_map):
    """
    Maps a user query to an API using GPT and extracts the necessary parameters.

    Args:
        user_query (str): The user's natural language query.
        api_map (dict): A dictionary containing API details from a Postman collection or similar source.

    Returns:
        dict: Mapped API details, including required parameters and missing details.
    """
    prompt = f"""
    You are an intelligent assistant for API mapping. Match the user's query to the most appropriate API from the API Map.
    - Extract the required query parameters and body fields for the API.
    - Identify missing parameters based on the API schema.
    - Provide the response in JSON format.

    User Query: "{user_query}"

    API Map:
    {json.dumps(api_map, indent=2)}

    Provide the response in JSON format:
    {{
        "API Name": "Matched API Name",
        "Query Params": {{}},
        "Headers": {{}},
        "Body": {{}},
        "Missing Params": ["list of missing parameters"]
    }}
    """
    try:
        response = openai.ChatCompletion.create(
            engine=deployment_name,
            messages=[
                {"role": "system", "content": "You are an API mapping assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1000
        )
        result = response["choices"][0]["message"]["content"].strip()
        logger.info(f"API Mapping Result: {result}")

        # Attempt to parse JSON from the response
        return extract_json_from_response(result)
    except Exception as e:
        logger.error(f"Error mapping query to API: {e}")
        return {"error": "Failed to map the query to an API."}


def extract_json_from_response(response):
    """
    Extracts JSON content from a GPT response string.

    Args:
        response (str): The raw GPT response.

    Returns:
        dict: The extracted JSON content.
    """
    try:
        # Use regex to locate JSON in the response
        match = re.search(r"\{.*\}", response, re.DOTALL)
        if match:
            json_content = match.group(0)
            return json.loads(json_content)
        else:
            raise ValueError("No JSON block found in the response.")
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode JSON: {e}")
        raise ValueError(f"Invalid JSON format in GPT response: {e}")


def generate_response(user_query, df, index, user_id, conversation_history):
    """Generates a response based on retrieved chunks using GPT-4, incorporating conversation history."""
    relevant_chunks = retrieve_relevant_chunks(user_query, df, index)

    if not relevant_chunks:
        return "I couldn't find relevant information."

    context_text = "\n\n".join([f"File: {chunk[0]}\nText: {chunk[1]}" for chunk in relevant_chunks])

    # Convert conversation history to a formatted string for context
    past_conversations = "\n".join([f"{entry['role']}: {entry['message']}" for entry in conversation_history])

    # full_prompt = f"""
    # You are an AI assistant trained on multiple user manuals. Use the provided context to answer user queries.
    #
    # ---
    #
    # ### User's Past Conversations:
    # {past_conversations}
    #
    # ---
    #
    # ### New User Query:
    # {user_query}
    #
    # ---
    #
    # ### Relevant Information:
    # {context_text}
    #
    # ---
    #
    # ### Instruction:
    # Please follow these guidelines to generate a helpful and well-structured response:
    #
    # 1. **Primary Knowledge Source**:
    #    - Use the "Relevant Information" section as your main source of truth.
    #    - Do **not** invent or assume information not found in the provided context.
    #
    # 2. **Referencing Documents**:
    #    - Clearly reference specific documents or files using the provided labels (e.g., **"File: BLv6.1 CE Import Letters of Credit.pdf"**) when relevant to the answer.
    #
    # 3. **Using Past Conversations**:
    #    - If helpful, incorporate information from "User's Past Conversations" for clarity, continuity, or context. Do this naturally, without repeating content unnecessarily.
    #
    # 4. **Response Formatting**:
    #    - Structure your answer using:
    #      - **Headings** (e.g., `### Step-by-Step Instructions`)
    #      - **Bullet points** for lists
    #      - **Bold** for emphasis or field names
    #      - Inline code (`like this`) for filenames, function names, or commands if applicable
    #    - Ensure the response is easy to scan and understand.
    #
    # 5. **Handling Missing Information**:
    #    - If the "Relevant Information" does **not** fully answer the user query, politely state this.
    #    - Do **not** guess or fabricate a response.
    #
    # 6. **Tone**:
    #    - Keep the tone clear, professional, and helpful.
    #
    # """

    # full_prompt = f"""
    # You are an AI assistant trained on multiple user manuals. Use the provided context to answer user queries.
    #
    # ---
    #
    # ### User's Past Conversations:
    # {past_conversations}
    #
    # ---
    #
    # ### New User Query:
    # {user_query}
    #
    # ---
    #
    # ### Relevant Information:
    # {context_text}
    #
    # ---
    #
    # ### Instruction:
    # Please follow these instructions when generating your response:
    #
    # 1. **Use the "Relevant Information" section as your source of truth**.
    #    - Do not make assumptions or add information not present in the context.
    #
    # 2. **Structure your response using markdown-style syntax** that can be parsed into HTML using the following rules:
    #    - Use `#`, `##`, or `###` for headings.
    #    - Use `**bold**` for field names or emphasis.
    #    - Use numbered lists (e.g., `1. Step`) for step-by-step instructions.
    #    - Use bullets (`-` or `*`) for unordered lists or notes.
    #    - Write plain text for regular paragraphs.
    #
    # 3. **Document Referencing**:
    #    - Mention the source file using the format: `**File: <filename>**` when relevant.
    #
    # 4. **Include past conversation context** naturally if useful for continuity or clarification.
    #
    # 5. **If the query cannot be answered based on the provided information**, respond politely and state that clearly.
    #
    # 6. **Maintain a professional and helpful tone**.
    #
    # ---
    #
    # Your final response should follow this example structure:
    #
    # ### Step-by-Step Instructions
    #
    # 1. **Access the Apply for Import LC Function**
    #    Navigate to the relevant system section to begin your application.
    #
    # 2. **Fill in the Required Fields**
    #    - **Date of Issuance**
    #    - **Our Ref Number**
    #    - **LC Number**, etc.
    #
    # 3. **Submit the Application**
    #
    # ---
    #
    # Only use markdown formatting (as shown). Do not use HTML or code formatting.
    # """

    full_prompt = f"""
    You are an AI assistant trained on multiple user manuals. Use the provided context to answer user queries.

    You must generate the final response **directly in clean, ready-to-render HTML format**.

    ---

    ### User's Past Conversations:
    {past_conversations}

    ---

    ### New User Query:
    {user_query}

    ---

    ### Relevant Information:
    {context_text}

    ---

    ### Instructions:

    Please strictly follow these guidelines:

    1. **Use only the "Relevant Information" section as your source of truth**.
       - Do not invent, assume, or add any information that is not present in the provided content.

    2. **Generate the response directly in valid HTML**:
       - Use `<h1>`, `<h2>`, or `<h3>` for headings.
       - Use `<strong>...</strong>` for important field names or emphasis.
       - For ordered steps (e.g., Step 1, Step 2), use `<ol style="color: black; font-size: inherit; padding-left: 1.2rem;">` and `<li style="color: black; font-size: inherit;">...</li>`.
       - For unordered lists, use `<ul style="color: black; font-size: inherit; padding-left: 1.2rem;">` and `<li style="color: black; font-size: inherit;">...</li>`.
       - Wrap regular text paragraphs inside `<p>...</p>`.
       - When mentioning a file reference, use: `<p><strong>File:</strong> filename.pdf</p>`

    3. **Response Structure Example** (follow this style):

       <h3>Step-by-Step Instructions</h3>

       <ol style="color: black; font-size: inherit; padding-left: 1.2rem;">
         <li style="color: black; font-size: inherit;"><strong>Step Title</strong><br>Step description.</li>
         ...
       </ol>

       <p><strong>File:</strong> filename.pdf</p>
    """

    try:
        response = openai.ChatCompletion.create(
            engine=deployment_name,
            messages=[
                {"role": "system",
                 "content": "You are an AI assistant specialized in answering queries based on manuals."},
                {"role": "user", "content": full_prompt}
            ],
            temperature=0.1,
            max_tokens=2000
        )
        logger.info(f"response is : {response['choices'][0]['message']['content']}")
        return response['choices'][0]['message']['content']
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        return "I couldn't process your request. Please try again."

# def generate_response(user_query, df, index):
#     """Generates a response based on retrieved chunks using GPT-4."""
#     relevant_chunks = retrieve_relevant_chunks(user_query, df, index)
#
#     if not relevant_chunks:
#         return "I couldn't find relevant information."
#
#     context = "\n\n".join([f"File: {chunk[0]}\nText: {chunk[1]}" for chunk in relevant_chunks])
#     print("Bot Response:", context)
#
#     try:
#         response = openai.ChatCompletion.create(
#             engine=deployment_name,
#             messages=[
#                 {"role": "system", "content": "You are an AI assistant trained on multiple user manuals. Use the provided context to answer user queries."},
#                 {"role": "user", "content": user_query},
#                 {"role": "assistant", "content": f"Relevant Information:\n{context}"}
#             ],
#             temperature=0.1,
#             max_tokens=2000
#         )
#         return response["choices"][0]["message"]["content"]
#     except Exception as e:
#         print(f"Error generating response: {e}")
#         return "I couldn't process your request. Please try again."


