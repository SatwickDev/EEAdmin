import threading
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from pymongo import MongoClient, DESCENDING
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)

class RepositoryManager:
    """Manages repository connections and RAG collections for Trade Finance, Treasury, and Cash Management"""
    
    def __init__(self, db_client):
        self.db = db_client
        self.repositories_collection = db_client.repositories
        self.rag_collections_collection = db_client.rag_collections
        self.user_connections_collection = db_client.user_repository_connections
        self.lock = threading.Lock()
        
        # Initialize default repositories
        self._initialize_default_repositories()
        
        # Create indexes for performance
        self._create_indexes()
    
    def _create_indexes(self):
        """Create database indexes for optimal performance"""
        try:
            self.repositories_collection.create_index([("name", 1)], unique=True)
            self.repositories_collection.create_index([("type", 1)])
            self.rag_collections_collection.create_index([("repository_id", 1)])
            self.rag_collections_collection.create_index([("collection_name", 1)])
            self.user_connections_collection.create_index([("user_id", 1), ("repository_id", 1)], unique=True)
            logger.info("Repository manager indexes created successfully")
        except Exception as e:
            logger.error(f"Error creating indexes: {e}")
    
    def _initialize_default_repositories(self):
        """Initialize default repositories if they don't exist"""
        default_repos = [
            {
                "name": "Trade Finance Repository",
                "type": "trade_finance",
                "description": "Repository for trade finance documents and knowledge",
                "icon": "fa-bank",
                "collections": [
                    {"name": "Letter of Credit", "count": 0, "status": "active"},
                    {"name": "Bank Guarantee", "count": 0, "status": "active"},
                    {"name": "Invoice Discounting", "count": 0, "status": "active"},
                    {"name": "UCP 600 Rules", "count": 0, "status": "active"},
                    {"name": "SWIFT Messages", "count": 0, "status": "active"}
                ]
            },
            {
                "name": "Treasury Repository",
                "type": "treasury",
                "description": "Repository for treasury operations and FX management",
                "icon": "fa-chart-line",
                "collections": [
                    {"name": "FX Hedging", "count": 0, "status": "active"},
                    {"name": "Interest Rate Swaps", "count": 0, "status": "active"},
                    {"name": "Treasury Policies", "count": 0, "status": "active"},
                    {"name": "Risk Management", "count": 0, "status": "active"}
                ]
            },
            {
                "name": "Cash Management Repository",
                "type": "cash_management",
                "description": "Repository for cash management and liquidity optimization",
                "icon": "fa-money-bill-wave",
                "collections": [
                    {"name": "Cash Pooling", "count": 0, "status": "active"},
                    {"name": "Working Capital", "count": 0, "status": "active"},
                    {"name": "Payment Processing", "count": 0, "status": "active"},
                    {"name": "Liquidity Management", "count": 0, "status": "active"}
                ]
            }
        ]
        
        with self.lock:
            for repo in default_repos:
                try:
                    existing = self.repositories_collection.find_one({"name": repo["name"]})
                    if not existing:
                        repo["created_at"] = datetime.utcnow()
                        repo["updated_at"] = datetime.utcnow()
                        repo["status"] = "active"
                        result = self.repositories_collection.insert_one(repo)
                        
                        # Create RAG collections for this repository
                        for collection in repo.get("collections", []):
                            self.rag_collections_collection.insert_one({
                                "repository_id": result.inserted_id,
                                "repository_name": repo["name"],
                                "collection_name": collection["name"],
                                "document_count": collection["count"],
                                "status": collection["status"],
                                "created_at": datetime.utcnow(),
                                "updated_at": datetime.utcnow()
                            })
                        
                        logger.info(f"Initialized repository: {repo['name']}")
                except Exception as e:
                    logger.error(f"Error initializing repository {repo['name']}: {e}")
    
    def get_all_repositories(self) -> List[Dict]:
        """Get all available repositories"""
        try:
            repositories = list(self.repositories_collection.find(
                {"status": "active"},
                {"_id": 1, "name": 1, "type": 1, "description": 1, "icon": 1}
            ))
            
            # Convert ObjectId to string
            for repo in repositories:
                repo["_id"] = str(repo["_id"])
            
            return repositories
        except Exception as e:
            logger.error(f"Error fetching repositories: {e}")
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
    
    def get_repository_collections(self, repository_id: str) -> List[Dict]:
        """Get RAG collections for a specific repository"""
        try:
            collections = list(self.rag_collections_collection.find(
                {"repository_id": ObjectId(repository_id), "status": "active"},
                {"_id": 1, "collection_name": 1, "document_count": 1, "updated_at": 1}
            ))
            
            # Convert ObjectId to string and format dates
            for coll in collections:
                coll["_id"] = str(coll["_id"])
                coll["updated_at"] = coll["updated_at"].isoformat() if coll.get("updated_at") else None
            
            return collections
        except Exception as e:
            logger.error(f"Error fetching repository collections: {e}")
            return []
    
    def get_repository_details(self, repository_id: str) -> Optional[Dict]:
        """Get detailed information about a repository"""
        try:
            repo = self.repositories_collection.find_one({"_id": ObjectId(repository_id)})
            if repo:
                repo["_id"] = str(repo["_id"])
                # Get collection count
                collections = self.rag_collections_collection.count_documents({
                    "repository_id": ObjectId(repository_id),
                    "status": "active"
                })
                repo["collection_count"] = collections
                
                # Get total document count
                pipeline = [
                    {"$match": {"repository_id": ObjectId(repository_id), "status": "active"}},
                    {"$group": {"_id": None, "total": {"$sum": "$document_count"}}}
                ]
                result = list(self.rag_collections_collection.aggregate(pipeline))
                repo["total_documents"] = result[0]["total"] if result else 0
                
                return repo
            return None
        except Exception as e:
            logger.error(f"Error fetching repository details: {e}")
            return None
    
    def update_collection_count(self, collection_id: str, increment: int = 1) -> bool:
        """Update document count for a RAG collection"""
        try:
            result = self.rag_collections_collection.update_one(
                {"_id": ObjectId(collection_id)},
                {
                    "$inc": {"document_count": increment},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating collection count: {e}")
            return False
    
    def search_collections(self, query: str, repository_ids: List[str] = None) -> List[Dict]:
        """Search RAG collections across repositories"""
        try:
            filter_query = {
                "collection_name": {"$regex": query, "$options": "i"},
                "status": "active"
            }
            
            if repository_ids:
                filter_query["repository_id"] = {"$in": [ObjectId(rid) for rid in repository_ids]}
            
            collections = list(self.rag_collections_collection.find(
                filter_query,
                {"_id": 1, "collection_name": 1, "repository_name": 1, "document_count": 1}
            ).limit(10))
            
            for coll in collections:
                coll["_id"] = str(coll["_id"])
            
            return collections
        except Exception as e:
            logger.error(f"Error searching collections: {e}")
            return []