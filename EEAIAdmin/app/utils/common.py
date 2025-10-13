# common.py
import logging
import json

# Initialize logger
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load schema from the external JSON file
def load_schema(file_path="schema_info.json"):
    """
    Load a JSON schema from the specified file path.

    Args:
        file_path (str): Path to the JSON file containing the schema.

    Returns:
        dict: The loaded schema or a default schema if the file is not found or invalid.
    """
    try:
        with open(file_path, "r") as file:
            schema = json.load(file)
            logger.info(f"Schema successfully loaded from {file_path}.")
            return schema
    except FileNotFoundError:
        logger.error(f"Error: The file {file_path} was not found.")
        # Provide a default schema as a fallback
        default_schema = {
            "imis_master": {
                "columns": {
                    "APPL_ID": "VARCHAR2 - Application ID",
                    "C_TRX_STATUS": "VARCHAR2 - Transaction status",
                    "LC_AMT": "NUMBER - Letter of credit amount",
                    "LC_CCY": "VARCHAR2 - Letter of credit currency"
                },
                "description": "Default schema for IMIS Master table."
            },
            "gtee_master": {
                "columns": {
                    "APPL_ID": "VARCHAR2 - Application ID",
                    "C_TRX_STATUS": "VARCHAR2 - Transaction status",
                    "GTEE_AMT": "NUMBER - Guarantee amount",
                    "GTEE_CCY": "VARCHAR2 - Guarantee currency"
                },
                "description": "Default schema for Guarantee Master table."
            },
        }
        logger.info("Using default schema as a fallback.")
        return default_schema
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON: {e}")
        raise ValueError("Invalid JSON format in the schema file.") from e
