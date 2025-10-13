import os
import uuid
import logging
import requests
import json

from app.utils.app_config import get_token

logger = logging.getLogger(__name__)

def parse_postman_collection(file_path):
    """
    Parse a Postman collection JSON file to extract API details.

    Args:
        file_path (str): Path to the Postman collection file.

    Returns:
        dict: A dictionary mapping API names to their details.
    """
    try:
        with open(file_path, "r") as f:
            collection = json.load(f)

        api_map = {}
        for item in collection.get("item", []):
            api_name = item["name"]
            request = item["request"]
            headers = {h["key"]: h["value"] for h in request.get("header", [])}
            method = request["method"]
            url = request["url"]["raw"] if "raw" in request["url"] else request["url"]
            query_params = {q["key"]: q["value"] for q in request.get("url", {}).get("query", [])}
            body = request.get("body", {}).get("raw", None)

            api_map[api_name] = {
                "url": url,
                "method": method,
                "headers": headers,
                "query_params": query_params,
                "body": body,
                "required_params": [param["key"] for param in request.get("url", {}).get("query", [])],
            }
        return api_map
    except Exception as e:
        logger.error(f"Error parsing Postman collection: {e}")
        return {}


def map_query_to_api(user_query, api_map):
    """
    Map a user query to an API using an intelligent assistant (LLM).

    Args:
        user_query (str): User's natural language query.
        api_map (dict): A dictionary containing API details.

    Returns:
        dict: Mapped API details with required parameters.
    """
    from gpt_utils import extract_json_from_response
    prompt = f"""
    You are an intelligent assistant responsible for mapping user queries to APIs. 
    Match the user's query to the most appropriate API from the API map, and provide:
    - The matched API name.
    - Any required query parameters, headers, and body fields.
    - Any missing parameters that require clarification.

    User Query: "{user_query}"

    API Map:
    {json.dumps(api_map, indent=2)}

    Respond in JSON format:
    {{
        "API Name": "Matched API Name",
        "Query Params": {{}},
        "Headers": {{}},
        "Body": {{}},
        "Missing Params": ["list of missing parameters"]
    }}
    """
    try:
        from config import openai, deployment_name
        response = openai.ChatCompletion.create(
            engine=deployment_name,
            messages=[
                {"role": "system", "content": "You are an API mapping assistant."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=500,
        )
        result = response["choices"][0]["message"]["content"].strip()
        logger.info(f"API Mapping Result: {result}")
        return extract_json_from_response(result)
    except Exception as e:
        logger.error(f"Error mapping query to API: {e}")
        return {"error": "Failed to map the query to an API."}


def execute_api(api_details, jwt_token, query_params=None, headers=None, body=None):
    """
    Execute an API call based on the provided details.

    Args:
        api_details (dict): API details (method, URL, etc.).
        jwt_token (str): Authentication token.
        query_params (dict): Query parameters for the API call.
        headers (dict): Headers for the API call.
        body (dict): Request body for the API call.

    Returns:
        dict: API response or error details.
    """
    guid = str(uuid.uuid4())
    headers = headers or {}
    headers["Authorization"] = f"Bearer {jwt_token}"
    headers["requestId"] = guid

    try:
        url = api_details["url"]
        method = api_details["method"]
        response = None

        if method == "GET":
            response = requests.get(url, headers=headers, params=query_params)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=body, params=query_params)

        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Error during API call: {e}")
        return {"error": f"API call failed: {e}"}


def handle_api_request(user_query, user_id, corporate_id):
    """
    Handle API-related requests with query mapping and execution.

    Args:
        user_query (str): User's natural language query.
        user_id (str): User ID for authentication.
        corporate_id (str): Corporate ID for authentication.

    Returns:
        dict: Response containing API results or error details.
    """
    try:
        # Load the API map from the Postman collection
        api_map = parse_postman_collection("FinMobileAPI.postman_collection.json")
        if not api_map:
            logger.error("Failed to load API map.")
            return {"response": "Unable to load API details.", "intent": "error"}

        # Map user query to API
        mapped_response = map_query_to_api(user_query, api_map)
        if "error" in mapped_response:
            logger.error(f"Error in API mapping: {mapped_response['error']}")
            return {"response": "Failed to map query to an API.", "intent": "api_request"}

        api_name = mapped_response.get("API Name")
        if not api_name or api_name not in api_map:
            logger.error(f"API name '{api_name}' not found.")
            return {"response": "No matching API found for your query.", "intent": "api_request"}

        # Get API details and required parameters
        api_details = api_map[api_name]
        query_params = mapped_response.get("Query Params", {})
        headers = mapped_response.get("Headers", {})
        body = mapped_response.get("Body", {})
        missing_params = mapped_response.get("Missing Params", [])

        if missing_params:
            logger.warning(f"Missing parameters for API '{api_name}': {missing_params}")
            return {"response": f"Missing parameters: {', '.join(missing_params)}.", "intent": "api_request"}

        # Authenticate and get JWT token
        jwt_token = get_token(corporate_id, user_id)
        if not jwt_token:
            logger.error("Failed to retrieve JWT token.")
            return {"response": "Authentication failed. Please check your credentials.", "intent": "api_request"}

        # Execute the API call
        api_response = execute_api(api_details, jwt_token, query_params, headers, body)
        if "error" in api_response:
            logger.error(f"API execution error: {api_response['error']}")
            return {"response": "An error occurred during the API call.", "intent": "api_request"}

        return {"response": api_response, "intent": "api_request"}
    except Exception as e:
        logger.error(f"Unexpected error handling API request: {e}")
        return {"response": "An unexpected error occurred.", "intent": "error"}
