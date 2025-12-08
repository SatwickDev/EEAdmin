import os
import logging
from typing import Optional, Dict, List

import chromadb
from chromadb.config import Settings
from app.utils.mongodb_manager import get_mongo_client as get_mongo_client_from_manager, get_database

logger = logging.getLogger(__name__)


# ============================================================================
# Environment Variable Parsing
# ============================================================================

def _env_bool(name: str, default: bool = False) -> bool:
    """Parse environment variable as boolean."""
    v = os.environ.get(name)
    if v is None:
        return default
    return v.lower() in ("1", "true", "yes", "on")


def _env_list(name: str) -> List[str]:
    """Parse environment variable as comma-separated list."""
    v = os.environ.get(name, "")
    return [s.strip() for s in v.split(",") if s.strip()]


def get_chroma_env_config() -> Dict:
    """
    Parse Chroma configuration from environment variables.

    Supported variables:
      - CHROMA_MODE: 'enabled' | 'disabled' | 'allowlist' (default: 'enabled')
      - CHROMA_ENABLED: legacy 'true'/'false' (overrides to mode if set)
      - CHROMA_ENABLED_FOR_ALL: legacy 'true'/'false' (implies mode='enabled')
      - CHROMA_CUSTOMERS: comma-separated list for allowlist mode
      - CHROMA_HOST: Chroma server host (default: 'localhost')
      - CHROMA_PORT: Chroma server port (default: 8000)
      - CHROMA_HOST_{customer}: Per-customer host override
      - CHROMA_PORT_{customer}: Per-customer port override

    Returns:
        dict with keys: mode, customers, host, port, use_env, per_customer_config
    """
    # Determine mode from env vars
    mode = os.environ.get("CHROMA_MODE", "").lower()
    
    # Handle legacy CHROMA_ENABLED* flags
    if not mode:
        if _env_bool("CHROMA_ENABLED", False):
            if _env_bool("CHROMA_ENABLED_FOR_ALL", False):
                mode = "enabled"
            else:
                mode = "allowlist"
        else:
            # Default to enabled for backward compatibility
            mode = "enabled"
    
    # Validate mode
    if mode not in ("enabled", "disabled", "allowlist"):
        mode = "enabled"
    
    customers = _env_list("CHROMA_CUSTOMERS")
    host = os.environ.get("CHROMA_HOST", "localhost")
    port = int(os.environ.get("CHROMA_PORT", "8000"))
    
    # Per-customer configuration
    per_customer_config = {}
    for customer in customers:
        customer_host = os.environ.get(f"CHROMA_HOST_{customer}", host)
        customer_port = int(os.environ.get(f"CHROMA_PORT_{customer}", port))
        per_customer_config[customer] = {
            "host": customer_host,
            "port": customer_port
        }
    
    # Check if any env var is explicitly set (for logging purposes)
    use_env = any(os.environ.get(k) for k in [
        "CHROMA_MODE", "CHROMA_ENABLED", "CHROMA_ENABLED_FOR_ALL", 
        "CHROMA_CUSTOMERS", "CHROMA_HOST", "CHROMA_PORT"
    ])
    
    return {
        "mode": mode,
        "customers": customers,
        "host": host,
        "port": port,
        "use_env": use_env,
        "per_customer_config": per_customer_config
    }


def _get_db(db=None):
    """Return provided db object or fetch from global app context or use mongodb_manager."""
    if db is not None:
        return db
    # Try to get db from Flask app context
    try:
        from flask import current_app
        if hasattr(current_app, 'db'):
            return current_app.db
    except Exception:
        pass
    # Fallback: use mongodb_manager
    client = get_mongo_client_from_manager()
    return get_database(client)


def get_request_customer_id(request=None) -> Optional[str]:
    """Try to derive a tenant/customer id from the Flask `request` or environment.

    Checks, in order: provided `request` object, `X-Customer-ID` header, query param
    `customer_id`, session keys `customer_id` or `repository_id`.
    Returns None when not found.
    """
    try:
        if request is None:
            from flask import request as _r, session
            request = _r
        # session may be present
        try:
            customer = request.environ.get('customer_id') or request.headers.get('X-Customer-ID') or request.args.get('customer_id')
        except Exception:
            customer = None

        # session fallback
        try:
            from flask import session
            if not customer:
                customer = session.get('customer_id') or session.get('repository_id')
        except Exception:
            pass

        # final normalization
        if isinstance(customer, str) and customer.strip():
            return customer.strip()
    except Exception:
        pass
    return None


def _get_active_chroma_config(db):
    """Return the active chromadb config document from `repository_config` collection."""
    try:
        # Try explicit chromadb typed config first
        repo = db.repository_config.find_one({'type': 'chromadb', 'is_active': True})
        if not repo:
            # fallback to any active config
            repo = db.repository_config.find_one({'is_active': True})
        return repo
    except Exception:
        return None


def is_chroma_enabled_for_customer(customer_id: Optional[str] = None, db=None) -> bool:
    """Check whether Chroma is enabled for a given customer (or globally).

    Configuration precedence:
      1. Environment variables (CHROMA_MODE, CHROMA_CUSTOMERS, etc.)
      2. MongoDB repository_config collection
      3. Default: disabled

    Args:
        customer_id: Tenant/customer identifier.
        db: Optional MongoDB database object (reuses connection if provided, else creates temp).

    Returns:
        True if Chroma is enabled for the customer, False otherwise.
    """
    try:
        # First check environment variables (highest precedence)
        env_cfg = get_chroma_env_config()
        if env_cfg["use_env"]:
            mode = env_cfg["mode"]
            if mode == "enabled":
                logger.debug(f"Chroma enabled via ENV for customer {customer_id}")
                return True
            if mode == "disabled":
                logger.debug(f"Chroma disabled via ENV for customer {customer_id}")
                return False
            if mode == "allowlist":
                allowed = env_cfg["customers"]
                result = customer_id in allowed if customer_id else False
                logger.debug(f"Chroma allowlist via ENV for customer {customer_id}: {result}")
                return result
        
        # Fallback to MongoDB configuration
        db = _get_db(db)
        repo = _get_active_chroma_config(db)
        if not repo:
            logger.debug(f"No active Chroma config in DB for customer {customer_id}")
            return False
        if repo.get('enabled_for_all'):
            logger.debug(f"Chroma enabled for all (DB) for customer {customer_id}")
            return True
        allowed = repo.get('customers') or repo.get('allowed_customers') or []
        if not customer_id:
            return False
        result = str(customer_id) in [str(x) for x in allowed]
        logger.debug(f"Chroma DB allowlist for customer {customer_id}: {result}")
        return result
    except Exception as e:
        logger.debug(f"is_chroma_enabled_for_customer error: {e}")
        return False


def get_chroma_client(host: Optional[str] = None, port: Optional[int] = None) -> Optional[chromadb.HttpClient]:
    """
    Get a ChromaDB HTTP client using environment variables or provided parameters.
    
    Args:
        host: Override host (defaults to CHROMA_HOST env var or 'localhost')
        port: Override port (defaults to CHROMA_PORT env var or 8000)
    
    Returns:
        chromadb.HttpClient or None if ChromaDB is disabled
    """
    try:
        # Get environment config
        config = get_chroma_env_config()
        
        # Check if disabled
        if config['mode'] == 'disabled':
            logger.debug("ChromaDB is disabled via CHROMA_MODE=disabled")
            return None
        
        # Use provided params or fallback to env config
        use_host = host if host is not None else config['host']
        use_port = port if port is not None else config['port']
        
        client = chromadb.HttpClient(host=use_host, port=use_port)
        logger.debug(f"Created ChromaDB client for {use_host}:{use_port}")
        return client
        
    except Exception as e:
        logger.warning(f"Failed to create ChromaDB client: {e}")
        return None


def get_chroma_client_for_customer(customer_id: Optional[str] = None, db=None) -> Optional[chromadb.HttpClient]:
    """Return a chromadb.HttpClient for the active configuration if the customer is allowed.

    Configuration precedence:
      1. Environment variables (CHROMA_MODE, CHROMA_HOST, CHROMA_PORT, etc.)
      2. MongoDB repository_config collection
      3. Default: None (disabled)

    Args:
        customer_id: Tenant/customer identifier.
        db: Optional MongoDB database object (reuses connection if provided, else creates temp).

    Returns:
        chromadb.HttpClient if enabled for customer, None otherwise.
    """
    try:
        # First check environment variables (highest precedence)
        env_cfg = get_chroma_env_config()
        if env_cfg["use_env"]:
            mode = env_cfg["mode"]
            if mode == "disabled":
                logger.debug(f"Chroma disabled via ENV; no client for {customer_id}")
                return None
            
            # Check allowlist if applicable
            if mode == "allowlist":
                allowed = env_cfg["customers"]
                if not customer_id or customer_id not in allowed:
                    logger.debug(f"Customer {customer_id} not in Chroma allowlist (ENV)")
                    return None
            
            # Create client with env host/port
            host = env_cfg["host"]
            port = env_cfg["port"]
            logger.debug(f"Creating Chroma client via ENV: {host}:{port} for {customer_id}")
            os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
            settings = Settings(anonymized_telemetry=False)
            chroma_client = chromadb.HttpClient(host=host, port=port, settings=settings)
            return chroma_client
        
        # Fallback to MongoDB configuration
        db = _get_db(db)
        repo = _get_active_chroma_config(db)
        if not repo:
            logger.debug(f"No active Chroma config in DB for {customer_id}")
            return None

        # Check allowed customers
        if not repo.get('enabled_for_all'):
            allowed = repo.get('customers') or repo.get('allowed_customers') or []
            if customer_id is None:
                customer_id = None
            if allowed and (customer_id is None or str(customer_id) not in [str(x) for x in allowed]):
                logger.debug(f"Customer {customer_id} not in Chroma allowlist (DB)")
                return None

        host = repo.get('host') or repo.get('chroma_host') or 'localhost'
        port = int(repo.get('port') or repo.get('chroma_port') or 8000)

        logger.debug(f"Creating Chroma client via DB: {host}:{port} for {customer_id}")
        # Disable telemetry
        os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
        settings = Settings(anonymized_telemetry=False)
        chroma_client = chromadb.HttpClient(host=host, port=port, settings=settings)
        return chroma_client
    except Exception as e:
        logger.debug(f"Failed to create chroma client for customer {customer_id}: {e}")
        return None
