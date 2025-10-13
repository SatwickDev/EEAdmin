"""
Centralized ChromaDB client initialization with telemetry disabled
"""
import os
import chromadb
from chromadb.config import Settings
import logging

logger = logging.getLogger(__name__)

# Disable telemetry to avoid the error
os.environ["ANONYMIZED_TELEMETRY"] = "False"

def get_chromadb_client(host="localhost", port=8000):
    """
    Get a ChromaDB HTTP client with telemetry disabled.
    
    Args:
        host: ChromaDB server host
        port: ChromaDB server port
        
    Returns:
        ChromaDB HttpClient instance
    """
    try:
        client = chromadb.HttpClient(
            host=host,
            port=port,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        return client
    except Exception as e:
        logger.error(f"Failed to create ChromaDB client: {e}")
        # Return a client anyway, it might work without the settings
        try:
            return chromadb.HttpClient(host=host, port=port)
        except:
            raise

def get_chromadb_persistent_client(persist_directory):
    """
    Get a ChromaDB persistent client with telemetry disabled.
    
    Args:
        persist_directory: Directory for persistent storage
        
    Returns:
        ChromaDB Client instance
    """
    try:
        client = chromadb.Client(
            Settings(
                persist_directory=persist_directory,
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        return client
    except Exception as e:
        logger.error(f"Failed to create ChromaDB persistent client: {e}")
        # Return a client anyway, it might work without the settings
        try:
            return chromadb.Client(Settings(persist_directory=persist_directory))
        except:
            raise