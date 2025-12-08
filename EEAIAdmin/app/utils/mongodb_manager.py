"""
MongoDB Environment Configuration Manager

Centralized MongoDB connection management with environment variable support.
Similar to chroma_manager.py but for MongoDB connections.

Supported environment variables:
  - MONGO_MODE: 'enabled' | 'disabled' (default: 'enabled')
  - MONGO_URI: Full MongoDB connection string
  - MONGO_HOST: MongoDB host (default: 'localhost')
  - MONGO_PORT: MongoDB port (default: 27017)
  - MONGO_USERNAME: MongoDB username (optional)
  - MONGO_PASSWORD: MongoDB password (optional)
  - DATABASE_NAME: Database name (default: 'finai_chatbot')
  - MONGO_AUTH_SOURCE: Authentication database (default: 'admin')
  - MONGO_REPLICA_SET: Replica set name (optional)
"""

import os
import logging
from typing import Optional, Dict
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

logger = logging.getLogger(__name__)


# ============================================================================
# Environment Variable Parsing
# ============================================================================

def _env_bool(name: str, default: bool = False) -> bool:
    """Parse environment variable as boolean."""
    v = os.environ.get(name)
    if v is None:
        return default
    return v.lower() in ("1", "true", "yes", "on", "enabled")


def get_mongo_env_config() -> Dict:
    """
    Parse MongoDB configuration from environment variables.

    Supported variables:
      - MONGO_MODE: 'enabled' | 'disabled' (default: 'enabled')
      - MONGO_URI: Full connection string (takes precedence over individual params)
      - MONGO_HOST: Host (default: 'localhost')
      - MONGO_PORT: Port (default: 27017)
      - MONGO_USERNAME: Username (optional)
      - MONGO_PASSWORD: Password (optional)
      - DATABASE_NAME: Database name (default: 'finai_chatbot')
      - MONGO_AUTH_SOURCE: Auth database (default: 'admin')
      - MONGO_REPLICA_SET: Replica set name (optional)
      - MONGO_SSL: Enable SSL (default: false)
      - MONGO_SSL_CERT_PATH: SSL certificate path (optional)

    Returns:
        dict with keys: mode, uri, host, port, username, password, database_name,
                       auth_source, replica_set, ssl, ssl_cert_path, use_env
    """
    # Determine mode
    mode = os.environ.get("MONGO_MODE", "enabled").lower()
    if mode not in ("enabled", "disabled"):
        mode = "enabled"  # Default to enabled (safer for MongoDB)
    
    # Get connection parameters
    uri = os.environ.get("MONGO_URI", "")
    host = os.environ.get("MONGO_HOST", "localhost")
    port = int(os.environ.get("MONGO_PORT", "27017"))
    username = os.environ.get("MONGO_USERNAME", "")
    password = os.environ.get("MONGO_PASSWORD", "")
    database_name = os.environ.get("DATABASE_NAME", "finai_chatbot")
    auth_source = os.environ.get("MONGO_AUTH_SOURCE", "admin")
    replica_set = os.environ.get("MONGO_REPLICA_SET", "")
    ssl = _env_bool("MONGO_SSL", False)
    ssl_cert_path = os.environ.get("MONGO_SSL_CERT_PATH", "")
    
    # Build URI if not provided
    if not uri:
        if username and password:
            uri = f"mongodb://{username}:{password}@{host}:{port}/"
        else:
            uri = f"mongodb://{host}:{port}/"
    
    # Check if any env var is explicitly set
    use_env = any(os.environ.get(k) for k in [
        "MONGO_MODE", "MONGO_URI", "MONGO_HOST", "MONGO_PORT",
        "MONGO_USERNAME", "MONGO_PASSWORD", "DATABASE_NAME",
        "MONGO_REPLICA_SET", "MONGO_SSL"
    ])
    
    return {
        "mode": mode,
        "uri": uri,
        "host": host,
        "port": port,
        "username": username,
        "password": password,
        "database_name": database_name,
        "auth_source": auth_source,
        "replica_set": replica_set,
        "ssl": ssl,
        "ssl_cert_path": ssl_cert_path,
        "use_env": use_env
    }


def is_mongo_enabled() -> bool:
    """
    Check if MongoDB is enabled via environment variables.
    
    Returns:
        True if MongoDB is enabled, False otherwise
    """
    env_cfg = get_mongo_env_config()
    if env_cfg["use_env"]:
        return env_cfg["mode"] == "enabled"
    return True  # Default to enabled if no env vars set


def get_mongo_client(timeout_ms: int = 5000) -> Optional[MongoClient]:
    """
    Create and return a MongoDB client using environment configuration.
    
    Args:
        timeout_ms: Connection and server selection timeout in milliseconds
    
    Returns:
        MongoClient instance if enabled, None if disabled
    """
    try:
        env_cfg = get_mongo_env_config()
        
        # Check if MongoDB is disabled
        if env_cfg["mode"] == "disabled":
            logger.warning("MongoDB is disabled via MONGO_MODE=disabled")
            return None
        
        uri = env_cfg["uri"]
        logger.debug(f"Connecting to MongoDB via ENV: {uri[:20]}...")
        
        # Build connection options
        options = {
            "connectTimeoutMS": timeout_ms,
            "serverSelectionTimeoutMS": timeout_ms,
        }
        
        if env_cfg["auth_source"]:
            options["authSource"] = env_cfg["auth_source"]
        
        if env_cfg["replica_set"]:
            options["replicaSet"] = env_cfg["replica_set"]
        
        if env_cfg["ssl"]:
            options["ssl"] = True
            if env_cfg["ssl_cert_path"]:
                options["ssl_certfile"] = env_cfg["ssl_cert_path"]
        
        client = MongoClient(uri, **options)
        
        # Test connection
        client.server_info()
        logger.debug("MongoDB connection successful")
        
        return client
        
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error connecting to MongoDB: {e}")
        return None


def get_database(client: Optional[MongoClient] = None, db_name: Optional[str] = None):
    """
    Get MongoDB database instance.
    
    Args:
        client: Optional MongoClient instance. If None, creates new client.
        db_name: Optional database name. If None, uses DATABASE_NAME from env.
    
    Returns:
        Database instance or None if MongoDB is disabled/unavailable
    """
    try:
        if client is None:
            client = get_mongo_client()
        
        if client is None:
            logger.warning("MongoDB client is None, cannot get database")
            return None
        
        if db_name is None:
            env_cfg = get_mongo_env_config()
            db_name = env_cfg["database_name"]
        
        return client[db_name]
        
    except Exception as e:
        logger.error(f"Failed to get database: {e}")
        return None


def get_connection_info() -> Dict:
    """
    Get current MongoDB connection information for diagnostics.
    
    Returns:
        Dict with connection details (safe for logging, passwords masked)
    """
    env_cfg = get_mongo_env_config()
    
    # Mask sensitive information
    safe_uri = env_cfg["uri"]
    if "@" in safe_uri:
        # Mask password in URI
        parts = safe_uri.split("@")
        credentials = parts[0].split("://")[1]
        if ":" in credentials:
            user = credentials.split(":")[0]
            safe_uri = safe_uri.replace(credentials, f"{user}:****")
    
    return {
        "mode": env_cfg["mode"],
        "uri": safe_uri,
        "host": env_cfg["host"],
        "port": env_cfg["port"],
        "database_name": env_cfg["database_name"],
        "username": env_cfg["username"] if env_cfg["username"] else "(none)",
        "auth_source": env_cfg["auth_source"],
        "replica_set": env_cfg["replica_set"] if env_cfg["replica_set"] else "(none)",
        "ssl": env_cfg["ssl"],
        "use_env": env_cfg["use_env"]
    }


# ============================================================================
# Backward Compatibility
# ============================================================================

def get_mongo_uri() -> str:
    """Get MongoDB URI (backward compatible)."""
    env_cfg = get_mongo_env_config()
    return env_cfg["uri"]


def get_database_name() -> str:
    """Get database name (backward compatible)."""
    env_cfg = get_mongo_env_config()
    return env_cfg["database_name"]
