"""
Document Category Manager
=========================

Handles CRUD operations for document categories.
Document categories classify documents by process type
(e.g., Commercial Processes, Transport Processes, Financial Processes, etc.)

Author: Modularized from routes.py
"""

import os
import json
import logging

logger = logging.getLogger(__name__)


class DocumentCategoryManager:
    """
    Manager class for Document Category CRUD operations.
    
    Document categories define process-based groupings:
    - Commercial Processes
    - Transport Processes
    - Border and Regulatory Processes
    - Financial Processes
    - Quality and Compliance Processes
    """

    def __init__(self, data_dir: str = None):
        """
        Initialize the Document Category Manager.
        
        Args:
            data_dir: Path to the data directory. Defaults to app/data
        """
        if data_dir:
            self.data_dir = data_dir
        else:
            # Default path relative to this file
            self.data_dir = os.path.abspath(
                os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data')
            )
        
        os.makedirs(self.data_dir, exist_ok=True)
        self.filepath = os.path.join(self.data_dir, 'document_categories.json')
        
        logger.info(f"🔧 DocumentCategoryManager initialized with data_dir: {self.data_dir}")

    def _get_default_categories(self) -> dict:
        """Get default document categories structure."""
        return {
            'categories': [
                {'id': '1', 'name': 'Commercial Processes'},
                {'id': '2', 'name': 'Transport Processes'},
                {'id': '3', 'name': 'Border and Regulatory Processes'},
                {'id': '4', 'name': 'Financial Processes'},
                {'id': '5', 'name': 'Quality and Compliance Processes'}
            ]
        }

    def load_categories(self) -> dict:
        """
        Load all document categories from the JSON file.
        
        Returns:
            dict: Dictionary containing 'categories' list
        """
        try:
            if os.path.exists(self.filepath):
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.debug(f"Loaded {len(data.get('categories', []))} document categories")
                    return data
            else:
                # Create default structure
                default_categories = self._get_default_categories()
                self.save_categories(default_categories)
                logger.info("Created default document categories file")
                return default_categories
        except Exception as e:
            logger.error(f"Error loading document categories: {e}")
            return {'categories': []}

    def save_categories(self, data: dict) -> bool:
        """
        Save all document categories to the JSON file.
        
        Args:
            data: Dictionary containing 'categories' list
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.debug("Document categories saved successfully")
            return True
        except Exception as e:
            logger.error(f"Error saving document categories: {e}")
            return False

    def get_all(self) -> list:
        """
        Get all document categories.
        
        Returns:
            list: List of category dictionaries
        """
        data = self.load_categories()
        return data.get('categories', [])

    def get_by_id(self, category_id: str) -> dict:
        """
        Get a document category by ID.
        
        Args:
            category_id: The category ID to find
            
        Returns:
            dict: The category if found, None otherwise
        """
        categories = self.get_all()
        for cat in categories:
            if cat.get('id') == category_id:
                return cat
        return None

    def create(self, category_data: dict) -> dict:
        """
        Create a new document category.
        
        Args:
            category_data: Dictionary with category fields (code, name, sender, receiver, processType)
            
        Returns:
            dict: Result with created category or error
        """
        try:
            data = self.load_categories()
            
            # Generate new ID
            existing_ids = [int(cat['id']) for cat in data['categories'] if cat.get('id', '').isdigit()]
            new_id = str(max(existing_ids) + 1) if existing_ids else '1'
            
            # Create new category
            new_category = {
                'id': new_id,
                'code': category_data.get('code', ''),
                'name': category_data.get('name', ''),
                'sender': category_data.get('sender', ''),
                'receiver': category_data.get('receiver', ''),
                'processType': category_data.get('processType', '')
            }
            
            data['categories'].append(new_category)
            
            if self.save_categories(data):
                logger.info(f"✅ Created document category: {new_id} - {new_category['name']}")
                return {'success': True, 'category': new_category}
            else:
                return {'success': False, 'message': 'Failed to save category'}
                
        except Exception as e:
            logger.error(f"Error creating document category: {e}")
            return {'success': False, 'message': str(e)}

    def update(self, category_id: str, category_data: dict) -> dict:
        """
        Update an existing document category.
        
        Args:
            category_id: The ID of the category to update
            category_data: Dictionary with updated fields
            
        Returns:
            dict: Result with success status and updated category
        """
        try:
            data = self.load_categories()
            
            # Find and update category
            for category in data['categories']:
                if category['id'] == category_id:
                    category['code'] = category_data.get('code', category.get('code', ''))
                    category['name'] = category_data.get('name', category.get('name', ''))
                    category['sender'] = category_data.get('sender', category.get('sender', ''))
                    category['receiver'] = category_data.get('receiver', category.get('receiver', ''))
                    category['processType'] = category_data.get('processType', category.get('processType', ''))
                    
                    if self.save_categories(data):
                        logger.info(f"✅ Updated document category: {category_id}")
                        return {'success': True, 'category': category}
                    else:
                        return {'success': False, 'message': 'Failed to save category'}
            
            return {'success': False, 'message': 'Category not found'}
                
        except Exception as e:
            logger.error(f"Error updating document category: {e}")
            return {'success': False, 'message': str(e)}

    def delete(self, category_id: str) -> dict:
        """
        Delete a document category by ID.
        
        Args:
            category_id: The ID of the category to delete
            
        Returns:
            dict: Result with success status
        """
        try:
            data = self.load_categories()
            
            # Find and remove category
            initial_length = len(data['categories'])
            data['categories'] = [cat for cat in data['categories'] if cat['id'] != category_id]
            
            if len(data['categories']) == initial_length:
                return {'success': False, 'message': 'Category not found'}
            
            if self.save_categories(data):
                logger.info(f"✅ Deleted document category: {category_id}")
                return {'success': True, 'message': 'Category deleted successfully'}
            else:
                return {'success': False, 'message': 'Failed to save changes'}
                
        except Exception as e:
            logger.error(f"Error deleting document category: {e}")
            return {'success': False, 'message': str(e)}


# Singleton instance for convenience
_document_category_manager = None


def get_document_category_manager() -> DocumentCategoryManager:
    """Get or create the singleton DocumentCategoryManager instance."""
    global _document_category_manager
    if _document_category_manager is None:
        _document_category_manager = DocumentCategoryManager()
    return _document_category_manager
