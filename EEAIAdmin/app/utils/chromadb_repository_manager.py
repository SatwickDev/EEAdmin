import threading
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pymongo import MongoClient, DESCENDING
from bson import ObjectId
import logging
import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)

class ChromaDBRepositoryManager:
    """Enhanced repository manager that integrates with ChromaDB collections"""
    
    def __init__(self, db_client, chroma_host="localhost", chroma_port=8000):
        self.db = db_client
        self.repositories_collection = db_client.repositories
        self.user_connections_collection = db_client.user_repository_connections
        self.lock = threading.Lock()
        
        # Initialize ChromaDB client with telemetry disabled
        try:
            # Disable telemetry to avoid the error
            import os
            os.environ["ANONYMIZED_TELEMETRY"] = "False"
            
            self.chroma_client = chromadb.HttpClient(
                host=chroma_host, 
                port=chroma_port,
                settings=Settings(anonymized_telemetry=False)
            )
            logger.info(f"Connected to ChromaDB at {chroma_host}:{chroma_port}")
        except Exception as e:
            logger.error(f"Failed to connect to ChromaDB: {e}")
            self.chroma_client = None
        
        # Define repository configurations with their ChromaDB collections
        self.repository_configs = {
            "trade_finance": {
                "name": "Trade Finance Repository",
                "description": "Repository for trade finance documents and knowledge",
                "icon": "fa-bank",
                "collections": [
                    {
                        "name": "Letter of Credit Records",
                        "chroma_collection": "lc_records_all",
                        "description": "Complete Letter of Credit documents, templates and transaction records"
                    },
                    {
                        "name": "Bank Guarantee", 
                        "chroma_collection": "bank_guarantee_records",
                        "description": "Bank guarantee documents and templates"
                    },
                    {
                        "name": "UCP 600 Rules",
                        "chroma_collection": "ucp_rules",
                        "description": "UCP 600 compliance rules and regulations for documentary credits"
                    },
                    {
                        "name": "SWIFT Rules & Messages",
                        "chroma_collection": "swift_rules",
                        "description": "SWIFT MT700, MT760 message templates and formatting rules"
                    },
                    {
                        "name": "Trade Finance Knowledge Base",
                        "chroma_collection": "trade_finance_records",
                        "description": "General trade finance documents, procedures and best practices"
                    },
                    {
                        "name": "Combined Rules & Regulations",
                        "chroma_collection": "all_rules",
                        "description": "Comprehensive collection of UCP 600, URDG 758, SWIFT and other trade rules"
                    },
                    {
                        "name": "Import LC Multi-Table",
                        "chroma_collection": "imlc_multitable",
                        "description": "Multi-table import LC records with structured data"
                    },
                    {
                        "name": "EXIM Transaction Records",
                        "chroma_collection": "adibv6ee_eximtrx_lc_records",
                        "description": "Export-Import transaction records and LC history"
                    },
                    {
                        "name": "Transaction Inbox",
                        "chroma_collection": "trx_inbox",
                        "description": "Incoming transaction processing records and workflow data"
                    }
                ]
            },
            "treasury": {
                "name": "Treasury Repository",
                "description": "Repository for treasury operations and FX management",
                "icon": "fa-chart-line",
                "collections": [
                    {
                        "name": "FX Hedging",
                        "chroma_collection": "fx_hedging_docs",
                        "description": "Foreign exchange hedging strategies and documents"
                    },
                    {
                        "name": "Interest Rate Swaps",
                        "chroma_collection": "interest_rate_swaps",
                        "description": "Interest rate swap agreements and calculations"
                    },
                    {
                        "name": "Treasury Policies",
                        "chroma_collection": "treasury_policies",
                        "description": "Corporate treasury policies and procedures"
                    }
                ]
            },
            "cash_management": {
                "name": "Cash Management Repository",
                "description": "Repository for cash management and liquidity optimization",
                "icon": "fa-money-bill-wave",
                "collections": [
                    {
                        "name": "Cash Pooling",
                        "chroma_collection": "cash_pooling_docs",
                        "description": "Cash pooling structures and agreements"
                    },
                    {
                        "name": "Working Capital",
                        "chroma_collection": "working_capital_docs",
                        "description": "Working capital optimization strategies"
                    },
                    {
                        "name": "Payment Processing",
                        "chroma_collection": "payment_processing",
                        "description": "Payment processing procedures and templates"
                    }
                ]
            },
            "user_manuals": {
                "name": "User Manuals Repository",
                "description": "Repository for user-uploaded manuals and documents",
                "icon": "fa-book",
                "collections": [
                    {
                        "name": "User Manuals",
                        "chroma_collection": "user_manual",
                        "description": "User-uploaded manuals and reference documents"
                    }
                ]
            },
            "compliance": {
                "name": "Compliance Repository",
                "description": "Repository for compliance and regulatory documents",
                "icon": "fa-shield-alt",
                "collections": [
                    {
                        "name": "Clause Library",
                        "chroma_collection": "clause_tag",
                        "description": "Standard clauses, legal terms and compliance tagging"
                    }
                ]
            }
        }
        
        # Initialize default repositories
        self._initialize_default_repositories()
        
        # Create indexes for performance
        self._create_indexes()
    
    def _create_indexes(self):
        """Create database indexes for optimal performance"""
        try:
            self.repositories_collection.create_index([("name", 1)], unique=True)
            self.repositories_collection.create_index([("type", 1)])
            self.user_connections_collection.create_index([("user_id", 1), ("repository_id", 1)], unique=True)
            logger.info("Repository manager indexes created successfully")
        except Exception as e:
            logger.error(f"Error creating indexes: {e}")
    
    def _initialize_default_repositories(self):
        """Initialize default repositories if they don't exist"""
        with self.lock:
            for repo_type, repo_config in self.repository_configs.items():
                try:
                    existing = self.repositories_collection.find_one({"type": repo_type})
                    if not existing:
                        repo_doc = {
                            "name": repo_config["name"],
                            "type": repo_type,
                            "description": repo_config["description"],
                            "icon": repo_config["icon"],
                            "collections": repo_config["collections"],
                            "created_at": datetime.utcnow(),
                            "updated_at": datetime.utcnow(),
                            "status": "active"
                        }
                        self.repositories_collection.insert_one(repo_doc)
                        logger.info(f"Initialized repository: {repo_config['name']}")
                except Exception as e:
                    logger.error(f"Error initializing repository {repo_config['name']}: {e}")
    
    def get_chroma_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """Get information about a ChromaDB collection"""
        if not self.chroma_client:
            return {"error": "ChromaDB not connected", "count": 0}
        
        try:
            collection = self.chroma_client.get_collection(collection_name)
            count = collection.count()
            
            # Get sample metadata to understand the collection structure
            sample = collection.get(limit=1)
            metadata_keys = []
            if sample and sample.get('metadatas') and len(sample['metadatas']) > 0:
                metadata_keys = list(sample['metadatas'][0].keys())
            
            return {
                "name": collection_name,
                "count": count,
                "metadata_fields": metadata_keys,
                "exists": True
            }
        except Exception as e:
            logger.warning(f"Collection {collection_name} not found or error: {e}")
            return {
                "name": collection_name,
                "count": 0,
                "exists": False,
                "error": str(e)
            }
    
    def get_all_repositories(self) -> List[Dict]:
        """Get all available repositories with ChromaDB collection info"""
        try:
            repositories = list(self.repositories_collection.find(
                {"status": "active"},
                {"_id": 1, "name": 1, "type": 1, "description": 1, "icon": 1, "collections": 1}
            ))
            
            # Enrich with ChromaDB info
            for repo in repositories:
                repo["_id"] = str(repo["_id"])
                total_documents = 0
                active_collections = 0
                
                if "collections" in repo:
                    for collection in repo["collections"]:
                        if "chroma_collection" in collection:
                            chroma_info = self.get_chroma_collection_info(collection["chroma_collection"])
                            collection["document_count"] = chroma_info.get("count", 0)
                            collection["exists"] = chroma_info.get("exists", False)
                            if collection["exists"]:
                                active_collections += 1
                                total_documents += collection["document_count"]
                
                repo["total_documents"] = total_documents
                repo["active_collections"] = active_collections
            
            return repositories
        except Exception as e:
            logger.error(f"Error fetching repositories: {e}")
            return []
    
    def get_repository_collections(self, repository_id: str) -> List[Dict]:
        """Get ChromaDB collections for a specific repository"""
        try:
            repo = self.repositories_collection.find_one({"_id": ObjectId(repository_id)})
            if not repo or "collections" not in repo:
                return []
            
            collections = []
            for coll in repo["collections"]:
                if "chroma_collection" in coll:
                    chroma_info = self.get_chroma_collection_info(coll["chroma_collection"])
                    collections.append({
                        "_id": coll.get("chroma_collection", ""),
                        "collection_name": coll["name"],
                        "chroma_collection": coll["chroma_collection"],
                        "description": coll.get("description", ""),
                        "document_count": chroma_info.get("count", 0),
                        "exists": chroma_info.get("exists", False),
                        "metadata_fields": chroma_info.get("metadata_fields", []),
                        "updated_at": datetime.utcnow().isoformat()
                    })
            
            return collections
        except Exception as e:
            logger.error(f"Error fetching repository collections: {e}")
            return []
    
    def search_in_collection(self, collection_name: str, query: str, n_results: int = 5) -> List[Dict]:
        """Search for documents in a specific ChromaDB collection"""
        if not self.chroma_client:
            return []
        
        try:
            from app.utils.file_utils import get_embedding_azureRAG
            
            collection = self.chroma_client.get_collection(collection_name)
            
            # Generate embedding for the query
            query_embedding = get_embedding_azureRAG(query)
            
            # Query the collection
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results
            )
            
            # Format results
            formatted_results = []
            if results and results.get('documents'):
                for i, doc in enumerate(results['documents'][0]):
                    metadata = results['metadatas'][0][i] if results.get('metadatas') else {}
                    distance = results['distances'][0][i] if results.get('distances') else 0
                    
                    formatted_results.append({
                        "document": doc,
                        "metadata": metadata,
                        "relevance_score": 1 - distance,  # Convert distance to similarity
                        "collection": collection_name
                    })
            
            return formatted_results
        except Exception as e:
            logger.error(f"Error searching in collection {collection_name}: {e}")
            return []
    
    def get_collection_sample_documents(self, collection_name: str, limit: int = 5) -> List[Dict]:
        """Get sample documents from a ChromaDB collection"""
        if not self.chroma_client:
            return []
        
        try:
            collection = self.chroma_client.get_collection(collection_name)
            
            # Get sample documents
            results = collection.get(limit=limit)
            
            # Format results
            formatted_results = []
            if results and results.get('documents'):
                for i, doc in enumerate(results['documents']):
                    metadata = results['metadatas'][i] if results.get('metadatas') else {}
                    doc_id = results['ids'][i] if results.get('ids') else f"doc_{i}"
                    
                    formatted_results.append({
                        "id": doc_id,
                        "document": doc[:500] + "..." if len(doc) > 500 else doc,  # Truncate long docs
                        "metadata": metadata,
                        "collection": collection_name
                    })
            
            return formatted_results
        except Exception as e:
            logger.error(f"Error getting sample documents from {collection_name}: {e}")
            return []
    
    def get_user_connections(self, user_id: str) -> List[str]:
        """Get repository IDs connected to a user"""
        try:
            connections = list(self.user_connections_collection.find(
                {"user_id": user_id, "status": "connected"},
                {"repository_id": 1}
            ))
            return [str(conn["repository_id"]) for conn in connections]
        except Exception as e:
            logger.error(f"Error fetching user connections: {e}")
            return []
    
    def connect_repository(self, user_id: str, repository_id: str) -> Dict:
        """Connect a user to a repository"""
        with self.lock:
            try:
                # Verify repository exists
                repo = self.repositories_collection.find_one({"_id": ObjectId(repository_id)})
                if not repo:
                    return {"success": False, "error": "Repository not found"}
                
                # Check if connection already exists
                existing = self.user_connections_collection.find_one({
                    "user_id": user_id,
                    "repository_id": ObjectId(repository_id)
                })
                
                if existing:
                    # Update status to connected
                    self.user_connections_collection.update_one(
                        {"_id": existing["_id"]},
                        {
                            "$set": {
                                "status": "connected",
                                "connected_at": datetime.utcnow()
                            }
                        }
                    )
                else:
                    # Create new connection
                    self.user_connections_collection.insert_one({
                        "user_id": user_id,
                        "repository_id": ObjectId(repository_id),
                        "repository_name": repo["name"],
                        "repository_type": repo["type"],
                        "status": "connected",
                        "connected_at": datetime.utcnow(),
                        "created_at": datetime.utcnow()
                    })
                
                return {"success": True, "message": f"Connected to {repo['name']}"}
                
            except Exception as e:
                logger.error(f"Error connecting repository: {e}")
                return {"success": False, "error": str(e)}
    
    def disconnect_repository(self, user_id: str, repository_id: str) -> Dict:
        """Disconnect a user from a repository"""
        with self.lock:
            try:
                result = self.user_connections_collection.update_one(
                    {
                        "user_id": user_id,
                        "repository_id": ObjectId(repository_id)
                    },
                    {
                        "$set": {
                            "status": "disconnected",
                            "disconnected_at": datetime.utcnow()
                        }
                    }
                )
                
                if result.modified_count > 0:
                    return {"success": True, "message": "Repository disconnected"}
                else:
                    return {"success": False, "error": "Connection not found"}
                    
            except Exception as e:
                logger.error(f"Error disconnecting repository: {e}")
                return {"success": False, "error": str(e)}
    
    def get_repository_details(self, repository_id: str) -> Optional[Dict]:
        """Get detailed information about a repository including ChromaDB stats"""
        try:
            repo = self.repositories_collection.find_one({"_id": ObjectId(repository_id)})
            if not repo:
                return None
            
            repo["_id"] = str(repo["_id"])
            
            # Get collection statistics
            total_documents = 0
            active_collections = 0
            collection_details = []
            
            if "collections" in repo:
                for collection in repo["collections"]:
                    if "chroma_collection" in collection:
                        chroma_info = self.get_chroma_collection_info(collection["chroma_collection"])
                        collection_detail = {
                            "name": collection["name"],
                            "chroma_collection": collection["chroma_collection"],
                            "description": collection.get("description", ""),
                            "document_count": chroma_info.get("count", 0),
                            "exists": chroma_info.get("exists", False),
                            "metadata_fields": chroma_info.get("metadata_fields", [])
                        }
                        collection_details.append(collection_detail)
                        
                        if collection_detail["exists"]:
                            active_collections += 1
                            total_documents += collection_detail["document_count"]
            
            repo["collection_count"] = len(collection_details)
            repo["active_collections"] = active_collections
            repo["total_documents"] = total_documents
            repo["collection_details"] = collection_details
            
            return repo
        except Exception as e:
            logger.error(f"Error fetching repository details: {e}")
            return None