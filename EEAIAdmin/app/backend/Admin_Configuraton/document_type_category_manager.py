"""
Document Type Category Manager
==============================

Handles CRUD operations for document type categories.
These are stored in document_classification_config.yaml under document_types.categories

Document type categories classify document types by process
(e.g., Commercial Processes, Transport Processes, Financial Processes, etc.)

Author: Modularized from routes.py
"""

import os
import logging
import yaml

logger = logging.getLogger(__name__)


class DocumentTypeCategoryManager:
    """
    Manager class for Document Type Category CRUD operations.
    
    Document type categories are stored in YAML config and define process-based groupings:
    - Commercial Processes
    - Transport Processes
    - Border and Regulatory Processes
    - Financial Processes
    - Quality and Compliance Processes
    """

    def __init__(self, data_dir: str = None):
        """
        Initialize the Document Type Category Manager.
        
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
        self.config_path = os.path.join(self.data_dir, 'document_classification_config.yaml')
        
        logger.info(f"🔧 DocumentTypeCategoryManager initialized with config_path: {self.config_path}")

    def _load_config(self) -> dict:
        """Load the YAML configuration file."""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
            return {}
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {}

    def _save_config(self, config: dict) -> bool:
        """Save the YAML configuration file."""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
            return True
        except Exception as e:
            logger.error(f"Error saving config: {e}")
            return False

    def get_all(self) -> list:
        """
        Get all document type categories.
        
        Returns:
            list: List of category dictionaries with 'id' and 'name'
        """
        try:
            config = self._load_config()
            categories = config.get('document_types', {}).get('categories', [])
            logger.debug(f"Loaded {len(categories)} document type categories")
            return categories
        except Exception as e:
            logger.error(f"Error getting document type categories: {e}")
            return []

    def get_by_id(self, category_id: int) -> dict:
        """
        Get a document type category by ID.
        
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
        Create a new document type category.
        
        Args:
            category_data: Dictionary with 'name' key
            
        Returns:
            dict: Result with created category or error
        """
        try:
            category_name = category_data.get('name')
            
            if not category_name:
                return {'success': False, 'message': 'Category name is required'}
            
            config = self._load_config()
            
            # Ensure document_types structure exists
            if 'document_types' not in config:
                config['document_types'] = {}
            if 'categories' not in config['document_types']:
                config['document_types']['categories'] = []
            
            categories = config['document_types']['categories']
            
            # Generate new ID
            existing_ids = [cat.get('id', 0) for cat in categories]
            new_id = max(existing_ids + [0]) + 1
            
            # Create new category
            new_category = {
                'id': new_id,
                'name': category_name
            }
            categories.append(new_category)
            
            config['document_types']['categories'] = categories
            
            if self._save_config(config):
                logger.info(f"✅ Created document type category: {new_id} - {category_name}")
                return {'success': True, 'category': new_category}
            else:
                return {'success': False, 'message': 'Failed to save category'}
                
        except Exception as e:
            logger.error(f"Error creating document type category: {e}")
            return {'success': False, 'message': str(e)}

    def update(self, category_id: int, category_data: dict) -> dict:
        """
        Update an existing document type category.
        
        Args:
            category_id: The ID of the category to update
            category_data: Dictionary with 'name' key
            
        Returns:
            dict: Result with success status
        """
        try:
            category_name = category_data.get('name')
            
            if not category_name:
                return {'success': False, 'message': 'Category name is required'}
            
            config = self._load_config()
            categories = config.get('document_types', {}).get('categories', [])
            
            # Find and update category
            category_found = False
            for cat in categories:
                if cat.get('id') == category_id:
                    cat['name'] = category_name
                    category_found = True
                    logger.info(f"✅ Updated document type category: {category_id} - {category_name}")
                    break
            
            if not category_found:
                return {'success': False, 'message': 'Category not found'}
            
            config['document_types']['categories'] = categories
            
            if self._save_config(config):
                return {'success': True, 'message': 'Category updated successfully'}
            else:
                return {'success': False, 'message': 'Failed to save category'}
                
        except Exception as e:
            logger.error(f"Error updating document type category {category_id}: {e}")
            return {'success': False, 'message': str(e)}

    def delete(self, category_id: int) -> dict:
        """
        Delete a document type category.
        
        Args:
            category_id: The ID of the category to delete
            
        Returns:
            dict: Result with success status
        """
        try:
            config = self._load_config()
            categories = config.get('document_types', {}).get('categories', [])
            
            # Find and remove category
            original_length = len(categories)
            categories = [cat for cat in categories if cat.get('id') != category_id]
            
            if len(categories) == original_length:
                return {'success': False, 'message': 'Category not found'}
            
            config['document_types']['categories'] = categories
            
            if self._save_config(config):
                logger.info(f"✅ Deleted document type category: {category_id}")
                return {'success': True, 'message': 'Category deleted successfully'}
            else:
                return {'success': False, 'message': 'Failed to save changes'}
                
        except Exception as e:
            logger.error(f"Error deleting document type category {category_id}: {e}")
            return {'success': False, 'message': str(e)}


# Singleton instance for convenience
_document_type_category_manager = None


def get_document_type_category_manager() -> DocumentTypeCategoryManager:
    """Get or create the singleton DocumentTypeCategoryManager instance."""
    global _document_type_category_manager
    if _document_type_category_manager is None:
        _document_type_category_manager = DocumentTypeCategoryManager()
    return _document_type_category_manager
