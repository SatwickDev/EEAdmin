"""
Repository-Database Mapping Configuration
Maps repositories to their respective database connections and knowledge bases
"""

# Repository-Database Configuration
REPOSITORY_DATABASE_MAP = {
    "trade_finance_repo": {
        "database": "mongodb_local",  # Can be changed to any configured database
        "collections": [
            "lc_transactions",
            "guarantees", 
            "trade_documents",
            "swift_messages",
            "bills_of_lading"
        ],
        "knowledge_base": "trade_finance_kb",
        "display_name": "Trade Finance Repository",
        "description": "Repository for trade finance documents and knowledge",
        "icon": "fas fa-ship",
        "color": "#6366f1"
    },
    "treasury_repo": {
        "database": "mongodb_local",
        "collections": [
            "fx_transactions",
            "money_market",
            "derivatives",
            "investments",
            "hedging_positions"
        ],
        "knowledge_base": "treasury_kb",
        "display_name": "Treasury Repository",
        "description": "Repository for treasury operations and FX management",
        "icon": "fas fa-coins",
        "color": "#10b981"
    },
    "cash_mgmt_repo": {
        "database": "mongodb_local",
        "collections": [
            "cash_transactions",
            "liquidity_reports",
            "payment_orders",
            "cash_forecasts",
            "bank_accounts"
        ],
        "knowledge_base": "cash_mgmt_kb",
        "display_name": "Cash Management Repository",
        "description": "Repository for cash management and liquidity optimization",
        "icon": "fas fa-money-bill-wave",
        "color": "#3b82f6"
    }
}


def get_repository_database(repository_id: str) -> str:
    """
    Get database connection name for a repository
    
    Args:
        repository_id (str): Repository ID (e.g., 'trade_finance_repo')
    
    Returns:
        str: Database connection name from database_connections.json
    """
    return REPOSITORY_DATABASE_MAP.get(repository_id, {}).get('database', 'mongodb_local')


def get_repository_collections(repository_id: str) -> list:
    """
    Get collection names for a repository
    
    Args:
        repository_id (str): Repository ID
    
    Returns:
        list: List of collection names
    """
    return REPOSITORY_DATABASE_MAP.get(repository_id, {}).get('collections', [])


def get_repository_knowledge_base(repository_id: str) -> str:
    """
    Get knowledge base ID for a repository
    
    Args:
        repository_id (str): Repository ID
    
    Returns:
        str: Knowledge base identifier
    """
    return REPOSITORY_DATABASE_MAP.get(repository_id, {}).get('knowledge_base', '')


def get_repository_info(repository_id: str) -> dict:
    """
    Get full repository configuration
    
    Args:
        repository_id (str): Repository ID
    
    Returns:
        dict: Repository configuration or empty dict if not found
    """
    return REPOSITORY_DATABASE_MAP.get(repository_id, {})


def list_all_repositories() -> list:
    """
    List all configured repositories
    
    Returns:
        list: List of repository configurations with IDs
    """
    return [
        {
            'id': repo_id,
            **repo_config
        }
        for repo_id, repo_config in REPOSITORY_DATABASE_MAP.items()
    ]


def get_database_for_collection(collection_name: str) -> str:
    """
    Find which database a collection belongs to (reverse lookup)
    
    Args:
        collection_name (str): Collection name to search for
    
    Returns:
        str: Database connection name or 'mongodb_local' if not found
    """
    for repo_config in REPOSITORY_DATABASE_MAP.values():
        if collection_name in repo_config.get('collections', []):
            return repo_config.get('database', 'mongodb_local')
    return 'mongodb_local'


# Knowledge Base Type Mapping
KNOWLEDGE_BASE_TYPES = {
    "user_manuals": {
        "source": "chromadb",
        "collection": "user_manual",
        "priority": 2,  # Lower priority than knowledge corpus
        "description": "User-uploaded PDF manuals"
    },
    "knowledge_corpus": {
        "source": "mongodb",
        "collection": "knowledge_corpus_qa_pairs",
        "priority": 1,  # Highest priority - approved Q&A pairs
        "description": "Curated Q&A knowledge base"
    },
    "trade_finance_kb": {
        "source": "chromadb",
        "collection": "trade_finance_docs",
        "priority": 3,
        "description": "Trade finance specific documents"
    },
    "treasury_kb": {
        "source": "chromadb",
        "collection": "treasury_docs",
        "priority": 3,
        "description": "Treasury specific documents"
    },
    "cash_mgmt_kb": {
        "source": "chromadb",
        "collection": "cash_mgmt_docs",
        "priority": 3,
        "description": "Cash management specific documents"
    }
}


def get_knowledge_sources_for_repository(repository_id: str) -> list:
    """
    Get ordered list of knowledge sources for a repository query
    
    Args:
        repository_id (str): Repository ID
    
    Returns:
        list: Ordered list of knowledge sources (highest priority first)
    """
    sources = [
        KNOWLEDGE_BASE_TYPES["knowledge_corpus"],  # Always check approved Q&A first
        KNOWLEDGE_BASE_TYPES["user_manuals"],       # Then user manuals
    ]
    
    # Add repository-specific knowledge base if exists
    repo_kb = get_repository_knowledge_base(repository_id)
    if repo_kb and repo_kb in KNOWLEDGE_BASE_TYPES:
        sources.append(KNOWLEDGE_BASE_TYPES[repo_kb])
    
    # Sort by priority (1 = highest)
    sources.sort(key=lambda x: x.get('priority', 99))
    
    return sources


# Database Connection Type Mapping (for UI display)
DATABASE_ICONS = {
    'mongodb': {'icon': '🍃', 'color': '#00ED64', 'name': 'MongoDB'},
    'postgresql': {'icon': '🐘', 'color': '#336791', 'name': 'PostgreSQL'},
    'oracle': {'icon': '🔶', 'color': '#F80000', 'name': 'Oracle'},
    'mssql': {'icon': 'Ⓜ️', 'color': '#CC2927', 'name': 'SQL Server'},
    'mysql': {'icon': '🐬', 'color': '#4479A1', 'name': 'MySQL'},
    'sqlite': {'icon': '📄', 'color': '#003B57', 'name': 'SQLite'}
}


def get_database_icon(db_type: str) -> dict:
    """
    Get display information for database type
    
    Args:
        db_type (str): Database type (mongodb, postgresql, etc.)
    
    Returns:
        dict: Icon, color, and display name
    """
    return DATABASE_ICONS.get(db_type, {'icon': '💾', 'color': '#666666', 'name': 'Database'})
