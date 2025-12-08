"""
Document Entity Mapping Manager
===============================

Handles CRUD operations for document-entity field mappings.
These mappings define which entities (fields) are expected in each document type.

Author: Modularized from routes.py
"""

import os
import json
import logging

logger = logging.getLogger(__name__)


class DocumentEntityMappingManager:
    """
    Manager class for Document-Entity Mapping CRUD operations.
    
    Mappings connect:
    - Document types (e.g., Commercial Invoice, Bill of Lading)
    - Entities (e.g., Invoice Number, Amount, Date)
    - Data categories (e.g., References, Amounts)
    - Field types (mandatory, optional, conditional)
    """

    def __init__(self, data_dir: str = None):
        """
        Initialize the Document Entity Mapping Manager.
        
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
        
        # Directory for individual document entity files
        self.entities_dir = os.path.join(self.data_dir, 'document_entities')
        os.makedirs(self.entities_dir, exist_ok=True)
        
        # Main maintenance file
        self.maintenance_filepath = os.path.join(self.data_dir, 'document_entity_maintenance.json')
        
        logger.info(f"🔧 DocumentEntityMappingManager initialized")
        logger.info(f"   - data_dir: {self.data_dir}")
        logger.info(f"   - entities_dir: {self.entities_dir}")

    # ==================== Loading Functions ====================

    def load_all_mappings(self) -> dict:
        """
        Load all document entity mappings from separate JSON files.
        
        Returns:
            dict: Dictionary with 'mappings' list containing all mappings
        """
        try:
            all_mappings = []
            
            if os.path.exists(self.entities_dir):
                for filename in os.listdir(self.entities_dir):
                    if filename.endswith('.json'):
                        filepath = os.path.join(self.entities_dir, filename)
                        with open(filepath, 'r', encoding='utf-8') as f:
                            doc_data = json.load(f)
                            all_mappings.extend(doc_data.get('mappings', []))
            
            logger.debug(f"Loaded {len(all_mappings)} total mappings")
            return {'mappings': all_mappings}
        except Exception as e:
            logger.error(f"Error loading document entity mappings: {e}")
            return {'mappings': []}

    def load_mappings_by_document(self, document_id: str) -> dict:
        """
        Load entity mappings for a specific document.
        
        Args:
            document_id: The document type ID
            
        Returns:
            dict: Document data with 'mappings' list
        """
        filepath = os.path.join(self.entities_dir, f'{document_id}.json')
        
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # Return default empty structure
                return {
                    'documentId': document_id,
                    'documentName': document_id.replace('_', ' ').title(),
                    'mappings': []
                }
        except Exception as e:
            logger.error(f"Error loading mappings for document {document_id}: {e}")
            return {'documentId': document_id, 'documentName': '', 'mappings': []}

    def load_maintenance_mappings(self) -> dict:
        """
        Load all mappings from the main maintenance JSON file.
        
        Returns:
            dict: Dictionary with 'mappings' list
        """
        try:
            if os.path.exists(self.maintenance_filepath):
                with open(self.maintenance_filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return {'mappings': data.get('mappings', [])}
            else:
                return {'mappings': []}
        except Exception as e:
            logger.error(f"Error loading maintenance mappings: {e}")
            return {'mappings': []}

    # ==================== Saving Functions ====================

    def save_mappings_by_document(self, document_id: str, doc_data: dict) -> bool:
        """
        Save entity mappings for a specific document.
        
        Args:
            document_id: The document type ID
            doc_data: Dictionary with document data and mappings
            
        Returns:
            bool: True if successful
        """
        filepath = os.path.join(self.entities_dir, f'{document_id}.json')
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(doc_data, f, indent=2, ensure_ascii=False)
            logger.debug(f"Saved mappings for document {document_id}")
            return True
        except Exception as e:
            logger.error(f"Error saving mappings for document {document_id}: {e}")
            return False

    def save_maintenance_mappings(self, doc_data: dict) -> bool:
        """
        Save mappings to the main maintenance file.
        
        Args:
            doc_data: Dictionary with mappings data
            
        Returns:
            bool: True if successful
        """
        try:
            with open(self.maintenance_filepath, 'w', encoding='utf-8') as f:
                json.dump(doc_data, f, indent=2, ensure_ascii=False)
            logger.debug("Saved maintenance mappings")
            return True
        except Exception as e:
            logger.error(f"Error saving maintenance mappings: {e}")
            return False

    def update_common_mapping(self, mapping_data: dict, operation: str = 'update') -> bool:
        """
        Update or delete a record in the common maintenance JSON.
        
        Args:
            mapping_data: The mapping data to update/delete
            operation: 'update' or 'delete'
            
        Returns:
            bool: True if successful
        """
        try:
            # Load current data
            if os.path.exists(self.maintenance_filepath):
                with open(self.maintenance_filepath, 'r', encoding='utf-8') as f:
                    common_data = json.load(f)
            else:
                common_data = {"mappings": []}
            
            mappings = common_data.get('mappings', [])
            updated = False
            
            if operation == 'delete':
                new_mappings = []
                for cm in mappings:
                    if not (
                        cm.get('documentId') == mapping_data.get('documentId') and
                        cm.get('entityId') == mapping_data.get('entityId') and
                        cm.get('documentCategoryId') == mapping_data.get('documentCategoryId') and
                        cm.get('dataCategoryId') == mapping_data.get('dataCategoryId')
                    ):
                        new_mappings.append(cm)
                common_data['mappings'] = new_mappings
                updated = True
                
            elif operation == 'update':
                for cm in mappings:
                    if (
                        cm.get('documentId') == mapping_data.get('documentId') and
                        cm.get('entityId') == mapping_data.get('entityId') and
                        cm.get('documentCategoryId') == mapping_data.get('documentCategoryId') and
                        cm.get('dataCategoryId') == mapping_data.get('dataCategoryId')
                    ):
                        cm.update(mapping_data)
                        updated = True
                        break
                
                if not updated:
                    common_data['mappings'].append(mapping_data)
                    updated = True
            
            if updated:
                with open(self.maintenance_filepath, 'w', encoding='utf-8') as f:
                    json.dump(common_data, f, indent=2, ensure_ascii=False)
                logger.info(f"Common JSON {operation} successful for entityId={mapping_data.get('entityId')}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error during common JSON {operation}: {e}")
            return False

    # ==================== CRUD Operations ====================

    def get_all(self) -> list:
        """
        Get all document entity mappings.
        
        Returns:
            list: List of all mappings
        """
        data = self.load_all_mappings()
        return data.get('mappings', [])

    def get_by_document(self, document_id: str) -> list:
        """
        Get all mappings for a specific document type.
        
        Args:
            document_id: The document type ID
            
        Returns:
            list: List of mappings for the document
        """
        doc_data = self.load_mappings_by_document(document_id)
        return doc_data.get('mappings', [])

    def get_by_id(self, mapping_id: str) -> dict:
        """
        Get a specific mapping by ID.
        
        Args:
            mapping_id: The mapping ID
            
        Returns:
            dict: The mapping if found, None otherwise
        """
        all_mappings = self.get_all()
        for mapping in all_mappings:
            if mapping.get('id') == mapping_id:
                return mapping
        return None

    def create(self, mapping_data: dict) -> dict:
        """
        Create a new document entity mapping.
        
        Args:
            mapping_data: Dictionary with mapping fields
            
        Returns:
            dict: Result with created mapping or error
        """
        try:
            # Validate required fields
            required_fields = ['documentId', 'documentCategoryId', 'entityId', 'dataCategoryId', 'fieldType']
            missing = [f for f in required_fields if not mapping_data.get(f)]
            if missing:
                return {'success': False, 'message': f"Missing required fields: {', '.join(missing)}"}
            
            document_id = mapping_data['documentId']
            
            # Load existing data
            doc_data = self.load_mappings_by_document(document_id)
            maintenance_data = self.load_maintenance_mappings()
            
            # Generate new IDs
            all_mappings = self.get_all()
            existing_ids = [int(m['id']) for m in all_mappings if str(m.get('id', '')).isdigit()]
            new_id = str(max(existing_ids, default=0) + 1)
            
            maintenance_ids = [int(m['id']) for m in maintenance_data.get('mappings', []) if str(m.get('id', '')).isdigit()]
            new_maintenance_id = str(max(maintenance_ids, default=0) + 1)
            
            # Build mapping
            base_mapping = {
                'documentId': mapping_data['documentId'],
                'documentName': mapping_data.get('documentName', ''),
                'documentCategoryId': mapping_data['documentCategoryId'],
                'documentCategoryName': mapping_data.get('documentCategoryName', ''),
                'entityId': mapping_data['entityId'],
                'entityName': mapping_data.get('entityName', ''),
                'mappingFormField': mapping_data.get('mappingFormField', ''),
                'mappingFormDescription': mapping_data.get('mappingFormDescription', ''),
                'dataCategoryId': mapping_data['dataCategoryId'],
                'dataCategoryValue': mapping_data.get('dataCategoryValue', ''),
                'fieldType': mapping_data['fieldType']
            }
            
            new_mapping = dict(base_mapping, id=new_id)
            new_maintenance_mapping = dict(base_mapping, id=new_maintenance_id)
            
            # Update document name if not set
            if not doc_data.get('documentName'):
                doc_data['documentName'] = mapping_data.get('documentName', '')
            
            # Add mappings
            doc_data.setdefault('mappings', []).append(new_mapping)
            maintenance_data.setdefault('mappings', []).append(new_maintenance_mapping)
            
            # Save both
            if self.save_mappings_by_document(document_id, doc_data) and \
               self.save_maintenance_mappings(maintenance_data):
                logger.info(f"✅ Created mapping: {new_maintenance_id} for document {document_id}")
                return {'success': True, 'mapping': new_maintenance_mapping}
            
            return {'success': False, 'message': 'Failed to save mapping'}
            
        except Exception as e:
            logger.error(f"Error creating document entity mapping: {e}")
            return {'success': False, 'message': str(e)}

    def update(self, mapping_id: str, mapping_data: dict) -> dict:
        """
        Update an existing document entity mapping.
        
        Args:
            mapping_id: The ID of the mapping to update
            mapping_data: Dictionary with updated fields
            
        Returns:
            dict: Result with success status
        """
        try:
            document_id = mapping_data.get('documentId')
            if not document_id:
                return {'success': False, 'message': 'Missing documentId'}
            
            # Load the document-specific file
            doc_data = self.load_mappings_by_document(document_id)
            
            found = False
            for i, mapping in enumerate(doc_data.get('mappings', [])):
                if mapping.get('id') == mapping_id:
                    updated_mapping = {
                        'id': mapping_id,
                        'documentId': mapping_data.get('documentId'),
                        'documentName': mapping_data.get('documentName', ''),
                        'documentCategoryId': mapping_data.get('documentCategoryId'),
                        'documentCategoryName': mapping_data.get('documentCategoryName', ''),
                        'entityId': mapping_data.get('entityId'),
                        'entityName': mapping_data.get('entityName', ''),
                        'mappingFormField': mapping_data.get('mappingFormField', ''),
                        'mappingFormDescription': mapping_data.get('mappingFormDescription', ''),
                        'dataCategoryId': mapping_data.get('dataCategoryId'),
                        'dataCategoryValue': mapping_data.get('dataCategoryValue', ''),
                        'fieldType': mapping_data.get('fieldType')
                    }
                    
                    doc_data['mappings'][i] = updated_mapping
                    found = True
                    
                    # Save document JSON
                    if not self.save_mappings_by_document(document_id, doc_data):
                        return {'success': False, 'message': 'Failed to save mapping'}
                    
                    # Update common JSON
                    self.update_common_mapping(updated_mapping, operation='update')
                    
                    logger.info(f"✅ Updated mapping: {mapping_id}")
                    return {'success': True, 'mapping': updated_mapping}
            
            if not found:
                return {'success': False, 'message': f'Mapping ID {mapping_id} not found'}
                
        except Exception as e:
            logger.error(f"Error updating document entity mapping {mapping_id}: {e}")
            return {'success': False, 'message': str(e)}

    def delete(self, mapping_id: str) -> dict:
        """
        Delete a document entity mapping.
        
        Args:
            mapping_id: The ID of the mapping to delete
            
        Returns:
            dict: Result with success status
        """
        try:
            # Find which document this mapping belongs to
            all_data = self.load_all_mappings()
            document_id = None
            mapping_to_delete = None
            
            for mapping in all_data.get('mappings', []):
                if mapping.get('id') == mapping_id:
                    document_id = mapping.get('documentId')
                    mapping_to_delete = mapping
                    break
            
            if not document_id:
                return {'success': False, 'message': 'Mapping not found'}
            
            # Load the specific document JSON
            doc_data = self.load_mappings_by_document(document_id)
            
            # Remove the mapping
            original_length = len(doc_data.get('mappings', []))
            doc_data['mappings'] = [m for m in doc_data.get('mappings', []) if m.get('id') != mapping_id]
            
            if len(doc_data['mappings']) < original_length:
                if self.save_mappings_by_document(document_id, doc_data):
                    # Delete from common JSON
                    if mapping_to_delete:
                        self.update_common_mapping(mapping_to_delete, operation='delete')
                    
                    logger.info(f"✅ Deleted mapping: {mapping_id}")
                    return {'success': True, 'message': 'Mapping deleted successfully'}
                else:
                    return {'success': False, 'message': 'Failed to save changes'}
            else:
                return {'success': False, 'message': 'Mapping not found'}
                
        except Exception as e:
            logger.error(f"Error deleting document entity mapping {mapping_id}: {e}")
            return {'success': False, 'message': str(e)}

    # ==================== Document Types Operations ====================

    def get_document_types(self) -> list:
        """
        Get all unique document types from mappings.
        
        Returns:
            list: List of document type info dictionaries
        """
        try:
            data = self.load_all_mappings()
            mappings = data.get('mappings', [])
            
            # Get unique document types
            document_types = {}
            for mapping in mappings:
                doc_id = mapping.get('documentId')
                if doc_id and doc_id not in document_types:
                    document_types[doc_id] = {
                        'documentId': doc_id,
                        'documentName': mapping.get('documentName'),
                        'documentCategoryId': mapping.get('documentCategoryId'),
                        'documentCategoryName': mapping.get('documentCategoryName'),
                        'fieldCount': 0
                    }
                
                if doc_id:
                    document_types[doc_id]['fieldCount'] += 1
            
            # Convert to sorted list
            doc_list = list(document_types.values())
            doc_list.sort(key=lambda x: x.get('documentName', ''))
            
            return doc_list
            
        except Exception as e:
            logger.error(f"Error getting document types: {e}")
            return []

    def get_document_type(self, document_id: str) -> dict:
        """
        Get a specific document type with its fields.
        
        Args:
            document_id: The document type ID
            
        Returns:
            dict: Document type info with fields, or None if not found
        """
        try:
            data = self.load_all_mappings()
            mappings = data.get('mappings', [])
            
            # Find all mappings for this document
            doc_mappings = [m for m in mappings if m.get('documentId') == document_id]
            
            if not doc_mappings:
                return None
            
            # Get document info from first mapping
            return {
                'documentId': document_id,
                'documentName': doc_mappings[0].get('documentName'),
                'documentCategoryId': doc_mappings[0].get('documentCategoryId'),
                'documentCategoryName': doc_mappings[0].get('documentCategoryName'),
                'fields': doc_mappings
            }
            
        except Exception as e:
            logger.error(f"Error getting document type {document_id}: {e}")
            return None


# Singleton instance for convenience
_document_entity_mapping_manager = None


def get_document_entity_mapping_manager() -> DocumentEntityMappingManager:
    """Get or create the singleton DocumentEntityMappingManager instance."""
    global _document_entity_mapping_manager
    if _document_entity_mapping_manager is None:
        _document_entity_mapping_manager = DocumentEntityMappingManager()
    return _document_entity_mapping_manager
