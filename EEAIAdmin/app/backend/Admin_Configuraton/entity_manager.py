"""
Entity Manager
==============

Handles CRUD operations for entities.
Entities represent field types that can be extracted from documents
(e.g., Invoice Number, Bill of Lading Number, LC Amount, etc.)

Author: Modularized from routes.py
"""

import os
import json
import logging

logger = logging.getLogger(__name__)


class EntityManager:
    """
    Manager class for Entity CRUD operations.
    
    Entities define the types of data fields that can be extracted from documents:
    - Document Identifier
    - Invoice Number
    - Bill of Lading Number
    - LC Amount
    - Expiry Date
    - etc.
    """

    def __init__(self, data_dir: str = None):
        """
        Initialize the Entity Manager.
        
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
        self.filepath = os.path.join(self.data_dir, 'entities.json')
        
        logger.info(f"🔧 EntityManager initialized with data_dir: {self.data_dir}")

    def _get_default_entities(self) -> dict:
        """Get default entities structure with comprehensive trade finance entities."""
        return {
            'entities': [
                {'id': '1', 'name': 'Document Identifier', 'description': 'Reference number identifying a specific document', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '2', 'name': 'Booking reference number', 'description': 'Reference number assigned by a carrier or agent to identify a specific consignment', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '3', 'name': 'Purchase Order number', 'description': 'Identifier assigned by the buyer to an order', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '4', 'name': 'House waybill document identifier', 'description': 'Reference number to identify a house waybill', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '5', 'name': 'Customs Declaration Document, Trader Assigned', 'description': 'Reference assigned by a trader to identify a declaration', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '6', 'name': 'Invoice Number', 'description': 'Unique identifier for a commercial invoice', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '7', 'name': 'Bill of Lading Number', 'description': 'Reference number for a bill of lading document', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '8', 'name': 'Shipping Order Number', 'description': 'Reference number for a shipping order', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '9', 'name': 'Container Number', 'description': 'Unique identifier for a shipping container', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '10', 'name': 'Certificate of Origin Number', 'description': 'Reference number for a certificate of origin', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '11', 'name': 'Letter of Credit Number', 'description': 'Unique identifier for a letter of credit', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '12', 'name': 'Bank Guarantee Number', 'description': 'Reference number for a bank guarantee', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '13', 'name': 'Insurance Policy Number', 'description': 'Unique identifier for an insurance policy', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '14', 'name': 'Packing List Number', 'description': 'Reference number for a packing list', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '15', 'name': 'Commercial Invoice Date', 'description': 'Date on which a commercial invoice was issued', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '16', 'name': 'Shipment Date', 'description': 'Date when goods were shipped', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '17', 'name': 'Delivery Date', 'description': 'Expected or actual date of delivery', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '18', 'name': 'LC Expiry Date', 'description': 'Expiration date of a letter of credit', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '19', 'name': 'Document Presentation Date', 'description': 'Date when documents are presented to the bank', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '20', 'name': 'Exporter Name', 'description': 'Name of the party exporting goods', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '21', 'name': 'Importer Name', 'description': 'Name of the party importing goods', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '22', 'name': 'Consignee Name', 'description': 'Name of the party to whom goods are consigned', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '23', 'name': 'Shipper Name', 'description': 'Name of the party shipping the goods', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '24', 'name': 'Notify Party', 'description': 'Party to be notified about shipment', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '25', 'name': 'Carrier Name', 'description': 'Name of the transportation carrier', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '26', 'name': 'Issuing Bank', 'description': 'Bank that issues the letter of credit', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '27', 'name': 'Advising Bank', 'description': 'Bank that advises the beneficiary of the LC', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '28', 'name': 'Confirming Bank', 'description': 'Bank that confirms the letter of credit', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '29', 'name': 'Port of Loading', 'description': 'Port where goods are loaded for shipment', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '30', 'name': 'Port of Discharge', 'description': 'Port where goods are unloaded', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '31', 'name': 'Place of Delivery', 'description': 'Final destination for delivery of goods', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '32', 'name': 'Country of Origin', 'description': 'Country where goods originated', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '33', 'name': 'Country of Destination', 'description': 'Country where goods are destined', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '34', 'name': 'Payment Terms', 'description': 'Terms and conditions for payment', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '35', 'name': 'Incoterms', 'description': 'International commercial terms defining responsibilities', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '36', 'name': 'Partial Shipment Clause', 'description': 'Clause indicating if partial shipments are allowed', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '37', 'name': 'Transshipment Clause', 'description': 'Clause indicating if transshipment is allowed', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '38', 'name': 'Latest Shipment Date', 'description': 'Latest date by which goods must be shipped', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '39', 'name': 'Negotiation Period', 'description': 'Period within which documents must be negotiated', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '40', 'name': 'Document Requirements', 'description': 'List of required documents for the transaction', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '41', 'name': 'Invoice Amount', 'description': 'Total amount stated on the invoice', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '42', 'name': 'LC Amount', 'description': 'Total amount of the letter of credit', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '43', 'name': 'Insurance Amount', 'description': 'Amount of insurance coverage', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '44', 'name': 'Freight Charges', 'description': 'Charges for transportation of goods', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '45', 'name': 'Customs Duty', 'description': 'Duty payable to customs authorities', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '46', 'name': 'Commission Amount', 'description': 'Commission charged for services', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '47', 'name': 'Discount Amount', 'description': 'Discount applied to the transaction', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '48', 'name': 'Currency Code', 'description': 'Three-letter currency code (ISO 4217)', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '49', 'name': 'Exchange Rate', 'description': 'Rate for currency conversion', 'mappingFormField': '', 'mappingFormDescription': ''},
                {'id': '50', 'name': 'Gross Weight', 'description': 'Total weight including packaging', 'mappingFormField': '', 'mappingFormDescription': ''},
            ]
        }

    def load_entities(self) -> dict:
        """
        Load all entities from the JSON file.
        
        Returns:
            dict: Dictionary containing 'entities' list
        """
        try:
            if os.path.exists(self.filepath):
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.debug(f"Loaded {len(data.get('entities', []))} entities")
                    return data
            else:
                # Create default structure
                default_entities = self._get_default_entities()
                self.save_entities(default_entities)
                logger.info("Created default entities file")
                return default_entities
        except Exception as e:
            logger.error(f"Error loading entities: {e}")
            return {'entities': []}

    def save_entities(self, data: dict) -> bool:
        """
        Save all entities to the JSON file.
        
        Args:
            data: Dictionary containing 'entities' list
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.debug("Entities saved successfully")
            return True
        except Exception as e:
            logger.error(f"Error saving entities: {e}")
            return False

    def get_all(self) -> list:
        """
        Get all entities.
        
        Returns:
            list: List of entity dictionaries
        """
        data = self.load_entities()
        return data.get('entities', [])

    def get_by_id(self, entity_id: str) -> dict:
        """
        Get an entity by ID.
        
        Args:
            entity_id: The entity ID to find
            
        Returns:
            dict: The entity if found, None otherwise
        """
        entities = self.get_all()
        for ent in entities:
            if ent.get('id') == entity_id:
                return ent
        return None

    def create(self, entity_data: dict) -> dict:
        """
        Create a new entity.
        
        Args:
            entity_data: Dictionary with entity fields
            
        Returns:
            dict: Result with created entity or error
        """
        try:
            all_data = self.load_entities()
            
            # Generate new ID
            max_id = 0
            for entity in all_data['entities']:
                try:
                    entity_id = int(entity['id'])
                    if entity_id > max_id:
                        max_id = entity_id
                except (ValueError, KeyError):
                    pass
            
            new_id = str(max_id + 1)
            
            # Create new entity
            new_entity = {
                'id': new_id,
                'name': entity_data.get('name', ''),
                'description': entity_data.get('description', ''),
                'mappingFormField': entity_data.get('mappingFormField', ''),
                'mappingFormDescription': entity_data.get('mappingFormDescription', ''),
                'dataCategoryId': entity_data.get('dataCategoryId', ''),
                'dataCategoryValue': entity_data.get('dataCategoryValue', '')
            }
            
            all_data['entities'].append(new_entity)
            
            if self.save_entities(all_data):
                logger.info(f"✅ Created entity: {new_id} - {new_entity['name']}")
                return {'success': True, 'entity': new_entity}
            else:
                return {'success': False, 'message': 'Failed to save entity'}
                
        except Exception as e:
            logger.error(f"Error creating entity: {e}")
            return {'success': False, 'message': str(e)}

    def update(self, entity_id: str, entity_data: dict) -> dict:
        """
        Update an existing entity.
        
        Args:
            entity_id: The ID of the entity to update
            entity_data: Dictionary with updated fields
            
        Returns:
            dict: Result with success status
        """
        try:
            all_data = self.load_entities()
            
            # Find and update the entity
            entity_found = False
            for entity in all_data['entities']:
                if entity['id'] == entity_id:
                    entity['name'] = entity_data.get('name', entity['name'])
                    entity['description'] = entity_data.get('description', entity['description'])
                    entity['mappingFormField'] = entity_data.get('mappingFormField', entity.get('mappingFormField', ''))
                    entity['mappingFormDescription'] = entity_data.get('mappingFormDescription', entity.get('mappingFormDescription', ''))
                    entity['dataCategoryId'] = entity_data.get('dataCategoryId', entity.get('dataCategoryId', ''))
                    entity['dataCategoryValue'] = entity_data.get('dataCategoryValue', entity.get('dataCategoryValue', ''))
                    entity_found = True
                    break
            
            if not entity_found:
                return {'success': False, 'message': 'Entity not found'}
            
            if self.save_entities(all_data):
                logger.info(f"✅ Updated entity: {entity_id}")
                return {'success': True, 'message': 'Entity updated successfully'}
            else:
                return {'success': False, 'message': 'Failed to save entity'}
                
        except Exception as e:
            logger.error(f"Error updating entity {entity_id}: {e}")
            return {'success': False, 'message': str(e)}

    def delete(self, entity_id: str) -> dict:
        """
        Delete an entity by ID.
        
        Args:
            entity_id: The ID of the entity to delete
            
        Returns:
            dict: Result with success status
        """
        try:
            all_data = self.load_entities()
            
            # Remove entity
            original_length = len(all_data['entities'])
            all_data['entities'] = [ent for ent in all_data['entities'] if ent['id'] != entity_id]
            
            if len(all_data['entities']) == original_length:
                return {'success': False, 'message': 'Entity not found'}
            
            if self.save_entities(all_data):
                logger.info(f"✅ Deleted entity: {entity_id}")
                return {'success': True, 'message': 'Entity deleted successfully'}
            else:
                return {'success': False, 'message': 'Failed to save changes'}
                
        except Exception as e:
            logger.error(f"Error deleting entity {entity_id}: {e}")
            return {'success': False, 'message': str(e)}


# Singleton instance for convenience
_entity_manager = None


def get_entity_manager() -> EntityManager:
    """Get or create the singleton EntityManager instance."""
    global _entity_manager
    if _entity_manager is None:
        _entity_manager = EntityManager()
    return _entity_manager
