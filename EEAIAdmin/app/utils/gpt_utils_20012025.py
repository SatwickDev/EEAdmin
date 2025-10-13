import logging
import openai
import json
import re

from app.utils.app_config import deployment_name

# Importing OpenAI configuration
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

def analyze_document_with_gpt(extracted_text, userQuery=None, annotations=None):
    """
    Analyze and classify the document content using GPT.

    Args:
        extracted_text (str): The extracted text from a document.

    Returns:
        dict: The analysis results, including the document type and extracted details.
    """
    prompt = f"""
        You are an intelligent assistant for document analysis. 
        Analyze the following text to classify the document and extract key details:

        Text:
        {extracted_text}

        Classify the document into one of the following types:
        - 'invoice': Contains details like Invoice Number, Amount, Vendor Name, etc.
        - 'export_collection': Includes transaction details, drawee information, etc.
        - 'letter_of_credit': Contains LC numbers, beneficiary names, issuing bank, etc.
        - 'bank_guarantee': Includes guarantee amount, expiry date, etc.
        - 'unknown': Identify the type of document , extract information based on user query {userQuery} and annotations {annotations}

        Based on the classification, extract relevant fields:
        - For 'invoice': Invoice Number, Invoice Date, Due Date, Total Amount, Tax Amount, Vendor Name, Customer Name.
        - For 'export_collection': Transaction Date, Type of Collection, Customer Number, Exporter Reference, Drawer Name, Drawee Name.
        - For 'letter_of_credit': LC Number, Beneficiary Name, Issuing Bank, Expiry Date, Amount, Currency.
        - For 'bank_guarantee': Guarantee Number, Amount, Expiry Date, Beneficiary, Issuing Bank.
        - For 'unknown': extract information based on user query {userQuery} and annotations {annotations}

        Provide the result in JSON format:
        {{
            "document_type": "type",
            "extracted_fields": {{}},
            "confidence_score": confidence_percentage
        }}
        """
    try:
        response = openai.ChatCompletion.create(
            engine=deployment_name,
            messages=[
                {"role": "system", "content": "You are a document analysis assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=2000
        )
        result = response["choices"][0]["message"]["content"].strip()
        logger.info(f"Document Analysis Result: {result}")

        # Extract JSON portion from response
        import re
        json_match = re.search(r"({.*})", result, re.DOTALL)  # Regex to find the JSON part
        if json_match:
            json_text = json_match.group(1)
            return json.loads(json_text)
        else:
            logger.error("Failed to find JSON in GPT response.")
            return {"error": "Invalid response format from GPT."}
    except Exception as e:
        logger.error(f"Error analyzing document with GPT: {e}")
        return {"error": "Failed to analyze the document."}


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
