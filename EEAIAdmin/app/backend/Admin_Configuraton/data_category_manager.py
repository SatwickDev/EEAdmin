"""
Data Category Manager
=====================

Handles CRUD operations for data categories.
Data categories are used to classify entity types (e.g., References, Dates, Amounts, etc.)

Author: Modularized from routes.py
"""

import os
import json
import logging

logger = logging.getLogger(__name__)


class DataCategoryManager:
    """
    Manager class for Data Categories CRUD operations.
    
    Data categories define high-level groupings for entities such as:
    - References
    - Dates
    - Parties/addresses/places/countries
    - Locations
    - Amounts/charges/percentages
    - etc.
    """

    def __init__(self, data_dir: str = None):
        """
        Initialize the Data Category Manager.
        
        Args:
            data_dir: Path to the data directory. Defaults to app/data
        """
        if data_dir:
            self.data_dir = data_dir
        else:
            # Default path relative to this file: app/backend/Admin_Configuraton -> app/data
            self.data_dir = os.path.abspath(
                os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data')
            )
        
        os.makedirs(self.data_dir, exist_ok=True)
        self.filepath = os.path.join(self.data_dir, 'categories.json')
        
        logger.info(f"🔧 DataCategoryManager initialized with data_dir: {self.data_dir}")

    def _get_default_categories(self) -> dict:
        """Get default categories structure."""
        return {
            'categories': [
                {'id': '1', 'value': 'References'},
                {'id': '2', 'value': 'Dates'},
                {'id': '3', 'value': 'Parties/addresses/places/countries'},
                {'id': '4', 'value': 'Locations'},
                {'id': '5', 'value': 'Clauses/conditions/instructions'},
                {'id': '6', 'value': 'Terms'},
                {'id': '7', 'value': 'Amounts/charges/percentages'},
                {'id': '8', 'value': 'Measure/Quantities'},
                {'id': '9', 'value': 'Goods'},
                {'id': '10', 'value': 'Dangerous goods'},
                {'id': '11', 'value': 'Transport modes/means/equipment'},
                {'id': '12', 'value': 'Others'}
            ]
        }

    def load_categories(self) -> dict:
        """
        Load all categories from the JSON file.
        
        Returns:
            dict: Dictionary containing 'categories' list
        """
        try:
            if os.path.exists(self.filepath):
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.debug(f"Loaded {len(data.get('categories', []))} categories")
                    return data
            else:
                # Create default structure
                default_categories = self._get_default_categories()
                self.save_categories(default_categories)
                logger.info("Created default categories file")
                return default_categories
        except Exception as e:
            logger.error(f"Error loading categories: {e}")
            return {'categories': []}

    def save_categories(self, data: dict) -> bool:
        """
        Save all categories to the JSON file.
        
        Args:
            data: Dictionary containing 'categories' list
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.debug("Categories saved successfully")
            return True
        except Exception as e:
            logger.error(f"Error saving categories: {e}")
            return False

    def get_all(self) -> list:
        """
        Get all categories.
        
        Returns:
            list: List of category dictionaries
        """
        data = self.load_categories()
        return data.get('categories', [])

    def get_by_id(self, category_id: str) -> dict:
        """
        Get a category by ID.
        
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
        Create a new category.
        
        Args:
            category_data: Dictionary with 'value' key
            
        Returns:
            dict: The created category with generated ID, or error dict
        """
        try:
            all_data = self.load_categories()
            
            # Generate new ID
            max_id = 0
            for cat in all_data['categories']:
                try:
                    cat_id = int(cat['id'])
                    if cat_id > max_id:
                        max_id = cat_id
                except (ValueError, KeyError):
                    pass
            
            new_id = str(max_id + 1)
            
            # Create new category
            new_category = {
                'id': new_id,
                'value': category_data.get('value', '')
            }
            
            all_data['categories'].append(new_category)
            
            if self.save_categories(all_data):
                logger.info(f"✅ Created category: {new_id} - {new_category['value']}")
                return {'success': True, 'category': new_category}
            else:
                return {'success': False, 'message': 'Failed to save category'}
                
        except Exception as e:
            logger.error(f"Error creating category: {e}")
            return {'success': False, 'message': str(e)}

    def update(self, category_id: str, category_data: dict) -> dict:
        """
        Update an existing category.
        
        Args:
            category_id: The ID of the category to update
            category_data: Dictionary with updated 'value'
            
        Returns:
            dict: Result with success status
        """
        try:
            all_data = self.load_categories()
            
            # Find and update the category
            category_found = False
            for category in all_data['categories']:
                if category['id'] == category_id:
                    category['value'] = category_data.get('value', category['value'])
                    category_found = True
                    break
            
            if not category_found:
                return {'success': False, 'message': 'Category not found'}
            
            if self.save_categories(all_data):
                logger.info(f"✅ Updated category: {category_id}")
                return {'success': True, 'message': 'Category updated successfully'}
            else:
                return {'success': False, 'message': 'Failed to save category'}
                
        except Exception as e:
            logger.error(f"Error updating category {category_id}: {e}")
            return {'success': False, 'message': str(e)}

    def delete(self, category_id: str) -> dict:
        """
        Delete a category by ID.
        
        Args:
            category_id: The ID of the category to delete
            
        Returns:
            dict: Result with success status
        """
        try:
            all_data = self.load_categories()
            
            # Remove category
            original_length = len(all_data['categories'])
            all_data['categories'] = [cat for cat in all_data['categories'] if cat['id'] != category_id]
            
            if len(all_data['categories']) == original_length:
                return {'success': False, 'message': 'Category not found'}
            
            if self.save_categories(all_data):
                logger.info(f"✅ Deleted category: {category_id}")
                return {'success': True, 'message': 'Category deleted successfully'}
            else:
                return {'success': False, 'message': 'Failed to save changes'}
                
        except Exception as e:
            logger.error(f"Error deleting category {category_id}: {e}")
            return {'success': False, 'message': str(e)}


# Singleton instance for convenience
_data_category_manager = None


def get_data_category_manager() -> DataCategoryManager:
    """Get or create the singleton DataCategoryManager instance."""
    global _data_category_manager
    if _data_category_manager is None:
        _data_category_manager = DataCategoryManager()
    return _data_category_manager
