import threading
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pymongo import MongoClient, DESCENDING
from bson import ObjectId
import hashlib
import logging

logger = logging.getLogger(__name__)

class ConversationManager:
    """Enhanced conversation history manager with smart suggestions and auto-fill capabilities"""
    
    def __init__(self, db_client):
        self.db = db_client
        self.conversation_collection = db_client.conversation_history
        self.templates_collection = db_client.templates
        self.beneficiary_collection = db_client.beneficiaries
        self.transaction_patterns = db_client.transaction_patterns
        self.lock = threading.Lock()
        
        # Create indexes for performance
        self._create_indexes()
    
    def _create_indexes(self):
        """Create database indexes for optimal performance"""
        try:
            self.conversation_collection.create_index([("user_id", 1), ("timestamp", -1)])
            self.conversation_collection.create_index([("session_id", 1)])
            self.templates_collection.create_index([("user_id", 1), ("category", 1)])
            self.beneficiary_collection.create_index([("user_id", 1), ("name", 1)])
            self.transaction_patterns.create_index([("user_id", 1), ("frequency", -1)])
            logger.info("Conversation manager indexes created successfully")
        except Exception as e:
            logger.error(f"Error creating indexes: {e}")
    
    def add_message(self, user_id: str, session_id: str, message: str, 
                   response: str, message_type: str = "chat", metadata: Dict = None) -> str:
        """Add a message to conversation history with enhanced metadata"""
        with self.lock:
            try:
                now = datetime.utcnow()
                conversation_entry = {
                    "user_id": user_id,
                    "session_id": session_id,
                    "message": message,
                    "response": response,
                    "message_type": message_type,
                    "timestamp": now,
                    "metadata": metadata or {},
                    "message_id": str(ObjectId())
                }
                
                result = self.conversation_collection.insert_one(conversation_entry)
                
                # Update or create session in chat_sessions collection
                chat_session = self.db.chat_sessions.find_one({"user_id": user_id, "session_id": session_id})
                
                if chat_session:
                    # Update existing session
                    self.db.chat_sessions.update_one(
                        {"user_id": user_id, "session_id": session_id},
                        {
                            "$set": {"last_activity": now},
                            "$inc": {"message_count": 2}  # Increment by 2 for user message + assistant response
                        }
                    )
                else:
                    # Create new session
                    self.db.chat_sessions.insert_one({
                        "user_id": user_id,
                        "session_id": session_id,
                        "created_at": now,
                        "last_activity": now,
                        "message_count": 2  # Start with 2 for user message + assistant response
                    })
                
                # Also save to chat_messages collection for consistency
                # Save user message
                if message:
                    self.db.chat_messages.insert_one({
                        "user_id": user_id,
                        "session_id": session_id,
                        "role": "user",
                        "content": message,
                        "timestamp": now
                    })
                
                # Save assistant response
                if response:
                    self.db.chat_messages.insert_one({
                        "user_id": user_id,
                        "session_id": session_id,
                        "role": "assistant",
                        "content": response,
                        "timestamp": now
                    })
                
                # Update transaction patterns for smart suggestions
                if message_type in ["transaction", "payment", "transfer"]:
                    self._update_transaction_patterns(user_id, message, metadata)
                
                logger.info(f"Message added successfully for session {session_id}")
                return str(result.inserted_id)
            except Exception as e:
                logger.error(f"Error adding message: {e}")
                return None
    
    def get_conversation_history(self, user_id: str, session_id: str = None, 
                               limit: int = 50, message_type: str = None) -> List[Dict]:
        """Retrieve conversation history with filtering options"""
        try:
            query = {"user_id": user_id}
            if session_id:
                query["session_id"] = session_id
            if message_type:
                query["message_type"] = message_type
            
            cursor = self.conversation_collection.find(query).sort("timestamp", -1).limit(limit)
            return list(cursor)
        except Exception as e:
            logger.error(f"Error retrieving conversation history: {e}")
            return []
    
    def get_context_for_llm(self, user_id: str, session_id: str, 
                           context_window: int = 10) -> str:
        """Get formatted conversation context for LLM"""
        try:
            conversations = self.get_conversation_history(user_id, session_id, context_window)
            
            if not conversations:
                return ""
            
            # Format for LLM context
            context_lines = []
            for conv in reversed(conversations):  # Reverse to get chronological order
                timestamp = conv['timestamp'].strftime("%Y-%m-%d %H:%M:%S")
                context_lines.append(f"[{timestamp}] User: {conv['message']}")
                context_lines.append(f"[{timestamp}] Assistant: {conv['response']}")
            
            return "\n".join(context_lines)
        except Exception as e:
            logger.error(f"Error getting LLM context: {e}")
            return ""
    
    def get_smart_suggestions(self, user_id: str, input_text: str, 
                            transaction_type: str = None) -> List[Dict]:
        """Get smart template suggestions based on user input and history"""
        try:
            suggestions = []
            
            # Get templates based on similarity and usage frequency
            templates = self._get_relevant_templates(user_id, input_text, transaction_type)
            suggestions.extend(templates)
            
            # Get beneficiary suggestions
            beneficiaries = self._get_beneficiary_suggestions(user_id, input_text)
            suggestions.extend(beneficiaries)
            
            # Get transaction pattern suggestions
            patterns = self._get_transaction_pattern_suggestions(user_id, input_text)
            suggestions.extend(patterns)
            
            return sorted(suggestions, key=lambda x: x.get('confidence', 0), reverse=True)[:5]
        except Exception as e:
            logger.error(f"Error getting smart suggestions: {e}")
            return []
    
    def _get_relevant_templates(self, user_id: str, input_text: str, 
                              transaction_type: str = None) -> List[Dict]:
        """Get relevant templates based on input similarity"""
        try:
            query = {"user_id": user_id}
            if transaction_type:
                query["category"] = transaction_type
            
            templates = list(self.templates_collection.find(query).sort("usage_count", -1))
            
            suggestions = []
            for template in templates:
                # Simple keyword matching (can be enhanced with NLP)
                keywords = template.get('keywords', [])
                matches = sum(1 for keyword in keywords if keyword.lower() in input_text.lower())
                
                if matches > 0:
                    confidence = min(matches / len(keywords), 1.0) * 0.8
                    suggestions.append({
                        "type": "template",
                        "title": template.get('title', 'Template'),
                        "data": template.get('data', {}),
                        "confidence": confidence,
                        "description": template.get('description', '')
                    })
            
            return suggestions
        except Exception as e:
            logger.error(f"Error getting template suggestions: {e}")
            return []
    
    def _get_beneficiary_suggestions(self, user_id: str, input_text: str) -> List[Dict]:
        """Get beneficiary suggestions based on name similarity"""
        try:
            # Search for beneficiaries with similar names
            regex_pattern = {"$regex": input_text.strip(), "$options": "i"}
            beneficiaries = list(self.beneficiary_collection.find({
                "user_id": user_id,
                "$or": [
                    {"name": regex_pattern},
                    {"account_number": regex_pattern},
                    {"bank_name": regex_pattern}
                ]
            }).sort("frequency", -1).limit(5))
            
            suggestions = []
            for beneficiary in beneficiaries:
                confidence = 0.7 if input_text.lower() in beneficiary.get('name', '').lower() else 0.5
                suggestions.append({
                    "type": "beneficiary",
                    "title": f"Beneficiary: {beneficiary.get('name', 'Unknown')}",
                    "data": {
                        "name": beneficiary.get('name'),
                        "account_number": beneficiary.get('account_number'),
                        "bank_name": beneficiary.get('bank_name'),
                        "swift_code": beneficiary.get('swift_code')
                    },
                    "confidence": confidence,
                    "description": f"Frequently used beneficiary"
                })
            
            return suggestions
        except Exception as e:
            logger.error(f"Error getting beneficiary suggestions: {e}")
            return []
    
    def _get_transaction_pattern_suggestions(self, user_id: str, input_text: str) -> List[Dict]:
        """Get transaction pattern suggestions based on historical data"""
        try:
            # Get recent transaction patterns
            patterns = list(self.transaction_patterns.find({
                "user_id": user_id
            }).sort("frequency", -1).limit(10))
            
            suggestions = []
            for pattern in patterns:
                # Check if pattern keywords match input
                pattern_keywords = pattern.get('keywords', [])
                matches = sum(1 for keyword in pattern_keywords if keyword.lower() in input_text.lower())
                
                if matches > 0:
                    confidence = min(matches / len(pattern_keywords), 1.0) * 0.6
                    suggestions.append({
                        "type": "pattern",
                        "title": f"Similar to: {pattern.get('description', 'Previous transaction')}",
                        "data": pattern.get('template_data', {}),
                        "confidence": confidence,
                        "description": f"Used {pattern.get('frequency', 0)} times"
                    })
            
            return suggestions
        except Exception as e:
            logger.error(f"Error getting pattern suggestions: {e}")
            return []
    
    def _update_transaction_patterns(self, user_id: str, message: str, metadata: Dict):
        """Update transaction patterns for future suggestions"""
        try:
            # Extract keywords from message
            keywords = self._extract_keywords(message)
            
            # Create or update pattern
            pattern_id = hashlib.md5(f"{user_id}_{'-'.join(sorted(keywords))}".encode()).hexdigest()
            
            update_data = {
                "$inc": {"frequency": 1},
                "$set": {
                    "user_id": user_id,
                    "keywords": keywords,
                    "last_used": datetime.utcnow(),
                    "template_data": metadata
                },
                "$setOnInsert": {
                    "created_at": datetime.utcnow(),
                    "description": message[:100]
                }
            }
            
            self.transaction_patterns.update_one(
                {"pattern_id": pattern_id},
                update_data,
                upsert=True
            )
        except Exception as e:
            logger.error(f"Error updating transaction patterns: {e}")
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text for pattern matching"""
        # Simple keyword extraction (can be enhanced with NLP)
        import re
        
        # Remove common words and extract meaningful terms
        stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during', 'before', 'after', 'above', 'below', 'between', 'among', 'within', 'without', 'along', 'following', 'across', 'behind', 'beyond', 'plus', 'except', 'but', 'until', 'unless', 'since', 'while'}
        
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        keywords = [word for word in words if word not in stop_words]
        
        return keywords[:10]  # Limit to 10 keywords
    
    def save_template(self, user_id: str, title: str, data: Dict, 
                     category: str = "general", keywords: List[str] = None) -> str:
        """Save a template for future use"""
        try:
            template = {
                "user_id": user_id,
                "title": title,
                "data": data,
                "category": category,
                "keywords": keywords or [],
                "usage_count": 0,
                "created_at": datetime.utcnow(),
                "last_used": datetime.utcnow()
            }
            
            result = self.templates_collection.insert_one(template)
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error saving template: {e}")
            return None
    
    def save_beneficiary(self, user_id: str, name: str, account_number: str, 
                        bank_name: str, swift_code: str = None) -> str:
        """Save beneficiary information for future auto-fill"""
        try:
            beneficiary = {
                "user_id": user_id,
                "name": name,
                "account_number": account_number,
                "bank_name": bank_name,
                "swift_code": swift_code,
                "frequency": 1,
                "created_at": datetime.utcnow(),
                "last_used": datetime.utcnow()
            }
            
            # Check if beneficiary already exists
            existing = self.beneficiary_collection.find_one({
                "user_id": user_id,
                "account_number": account_number
            })
            
            if existing:
                # Update frequency
                self.beneficiary_collection.update_one(
                    {"_id": existing["_id"]},
                    {
                        "$inc": {"frequency": 1},
                        "$set": {"last_used": datetime.utcnow()}
                    }
                )
                return str(existing["_id"])
            else:
                result = self.beneficiary_collection.insert_one(beneficiary)
                return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error saving beneficiary: {e}")
            return None
    
    def get_last_transaction_context(self, user_id: str, transaction_type: str = None) -> Dict:
        """Get last transaction context for auto-fill suggestions"""
        try:
            query = {"user_id": user_id, "message_type": "transaction"}
            if transaction_type:
                query["metadata.transaction_type"] = transaction_type
            
            last_transaction = self.conversation_collection.find_one(
                query,
                sort=[("timestamp", -1)]
            )
            
            if last_transaction:
                return {
                    "timestamp": last_transaction.get("timestamp"),
                    "metadata": last_transaction.get("metadata", {}),
                    "suggestion_type": "last_transaction",
                    "description": "Based on your last transaction"
                }
            
            return {}
        except Exception as e:
            logger.error(f"Error getting last transaction context: {e}")
            return {}
    
    def cleanup_old_conversations(self, days_old: int = 30):
        """Clean up old conversations to maintain database performance"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            result = self.conversation_collection.delete_many({
                "timestamp": {"$lt": cutoff_date}
            })
            logger.info(f"Cleaned up {result.deleted_count} old conversations")
        except Exception as e:
            logger.error(f"Error cleaning up conversations: {e}")