"""
Discrepancy Rule Manager Module
===============================

This module provides management of discrepancy rules with XML and JSON storage.
Rules define what constitutes a discrepancy in trade finance documents.

Author: EEAdmin Team
Version: 1.0.0
"""

import json
import logging
import os
import uuid
import xml.etree.ElementTree as ET
import xml.dom.minidom
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class DiscrepancyRuleManager:
    """Manages discrepancy rules with XML and JSON storage"""

    def __init__(self, data_dir: Optional[str] = None):
        """
        Initialize the DiscrepancyRuleManager.
        
        Args:
            data_dir: Optional custom data directory path. 
                     Defaults to app/data folder.
        """
        self.rules = []
        
        # Determine data directory
        if data_dir:
            self.data_dir = data_dir
        else:
            # Default to app/data folder
            current_file = Path(__file__)
            # Go up to Smart_Document_Capture, then to app, then to data
            self.data_dir = str(current_file.parent.parent.parent.parent / 'data')
        
        self.rules_xml_path = os.path.join(self.data_dir, 'discrepancy_rules.xml')
        self.rules_json_path = os.path.join(self.data_dir, 'discrepancy_rules.json')

        # Ensure data directory exists
        os.makedirs(self.data_dir, exist_ok=True)
        self.load_rules()

    def load_rules(self):
        """Load rules from XML file, fallback to JSON if XML doesn't exist"""
        try:
            if os.path.exists(self.rules_xml_path):
                self.rules = self._load_from_xml()
                logger.info(f"Loaded {len(self.rules)} discrepancy rules from XML")
            elif os.path.exists(self.rules_json_path):
                self.rules = self._load_from_json()
                logger.info(f"Loaded {len(self.rules)} discrepancy rules from JSON")
            else:
                self.rules = []
                self._create_sample_rules()
                logger.info(f"Created {len(self.rules)} sample discrepancy rules")
        except Exception as e:
            logger.error(f"Error loading discrepancy rules: {e}")
            self.rules = []

    def _load_from_xml(self) -> List[Dict]:
        """Load rules from XML file"""
        try:
            tree = ET.parse(self.rules_xml_path)
            root = tree.getroot()
            rules = []

            for rule_elem in root.findall('rule'):
                rule = {
                    'id': rule_elem.get('id', str(uuid.uuid4())),
                    'code': rule_elem.find('code').text if rule_elem.find('code') is not None else '',
                    'documentType': rule_elem.find('documentType').text if rule_elem.find(
                        'documentType') is not None else '',
                    'description': rule_elem.find('description').text if rule_elem.find(
                        'description') is not None else '',
                    'basis': rule_elem.find('basis').text if rule_elem.find('basis') is not None else '',
                    'priority': rule_elem.find('priority').text if rule_elem.find(
                        'priority') is not None else 'Mandatory',
                    'createdAt': rule_elem.find('createdAt').text if rule_elem.find(
                        'createdAt') is not None else datetime.now().isoformat(),
                    'updatedAt': rule_elem.find('updatedAt').text if rule_elem.find(
                        'updatedAt') is not None else datetime.now().isoformat()
                }
                rules.append(rule)

            return rules
        except Exception as e:
            logger.error(f"Error loading from XML: {e}")
            return []

    def _load_from_json(self) -> List[Dict]:
        """Load rules from JSON file"""
        try:
            with open(self.rules_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('rules', [])
        except Exception as e:
            logger.error(f"Error loading from JSON: {e}")
            return []

    def _create_sample_rules(self):
        """Create sample rules based on common trade finance requirements"""
        sample_rules = [
            {
                'id': str(uuid.uuid4()),
                'code': 'R-0002',
                'documentType': 'Bill of Lading',
                'description': 'must be signed by the authorized signatory',
                'basis': 'ISBP 821 A1',
                'priority': 'Mandatory',
                'createdAt': datetime.now().isoformat(),
                'updatedAt': datetime.now().isoformat()
            },
            {
                'id': str(uuid.uuid4()),
                'code': 'R-0003',
                'documentType': 'Air Waybill',
                'description': 'must be an original when originals are stipulated in the LC; additionally, named shipper must match LC.',
                'basis': 'UCP 600 Art. 18',
                'priority': 'Mandatory',
                'createdAt': datetime.now().isoformat(),
                'updatedAt': datetime.now().isoformat()
            },
            {
                'id': str(uuid.uuid4()),
                'code': 'R-0036',
                'documentType': 'Bill of Lading',
                'description': 'certificate must reference the invoice/BL number; additionally, incoterms must be consistent.',
                'basis': 'Bank Practice',
                'priority': 'Mandatory',
                'createdAt': datetime.now().isoformat(),
                'updatedAt': datetime.now().isoformat()
            },
            {
                'id': str(uuid.uuid4()),
                'code': 'R-0037',
                'documentType': 'Air Waybill',
                'description': 'document must show description matching HS code if required',
                'basis': 'Customs / LC',
                'priority': 'Mandatory',
                'createdAt': datetime.now().isoformat(),
                'updatedAt': datetime.now().isoformat()
            },
            {
                'id': str(uuid.uuid4()),
                'code': 'R-0070',
                'documentType': 'Bill of Lading',
                'description': 'notify party must match LC or be allowed by LC terms',
                'basis': 'ISBP 821',
                'priority': 'Mandatory',
                'createdAt': datetime.now().isoformat(),
                'updatedAt': datetime.now().isoformat()
            }
        ]

        self.rules = sample_rules
        self.save_rules()

    def save_rules(self):
        """Save rules to both XML and JSON formats"""
        try:
            self._save_to_xml()
            self._save_to_json()
            logger.info(f"Saved {len(self.rules)} discrepancy rules")
        except Exception as e:
            logger.error(f"Error saving rules: {e}")
            raise

    def _save_to_xml(self):
        """Save rules to XML file"""
        root = ET.Element('discrepancyRules')
        root.set('version', '1.0')
        root.set('lastUpdated', datetime.now().isoformat())

        for rule in self.rules:
            rule_elem = ET.SubElement(root, 'rule')
            rule_elem.set('id', rule['id'])

            # Add child elements
            ET.SubElement(rule_elem, 'code').text = rule['code']
            ET.SubElement(rule_elem, 'documentType').text = rule['documentType']
            ET.SubElement(rule_elem, 'description').text = rule['description']
            ET.SubElement(rule_elem, 'basis').text = rule['basis']
            ET.SubElement(rule_elem, 'priority').text = rule['priority']
            ET.SubElement(rule_elem, 'createdAt').text = rule['createdAt']
            ET.SubElement(rule_elem, 'updatedAt').text = rule['updatedAt']

        # Pretty print XML
        xml_str = ET.tostring(root, encoding='unicode')
        dom = xml.dom.minidom.parseString(xml_str)
        pretty_xml = dom.toprettyxml(indent='  ')

        # Remove empty lines
        pretty_xml = '\n'.join([line for line in pretty_xml.split('\n') if line.strip()])

        with open(self.rules_xml_path, 'w', encoding='utf-8') as f:
            f.write(pretty_xml)

    def _save_to_json(self):
        """Save rules to JSON file as backup"""
        data = {
            'version': '1.0',
            'lastUpdated': datetime.now().isoformat(),
            'rules': self.rules
        }

        with open(self.rules_json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_all_rules(self) -> List[Dict]:
        """Get all rules"""
        return self.rules

    def get_rule_by_id(self, rule_id: str) -> Optional[Dict]:
        """Get rule by ID"""
        return next((rule for rule in self.rules if rule['id'] == rule_id), None)

    def get_rules_by_document_type(self, document_type: str) -> List[Dict]:
        """Get all rules for a specific document type"""
        return [rule for rule in self.rules if rule['documentType'].lower() == document_type.lower()]

    def add_rule(self, rule_data: Dict) -> Dict:
        """Add new rule"""
        new_rule = {
            'id': str(uuid.uuid4()),
            'code': rule_data['code'],
            'documentType': rule_data['documentType'],
            'description': rule_data['description'],
            'basis': rule_data['basis'],
            'priority': rule_data['priority'],
            'createdAt': datetime.now().isoformat(),
            'updatedAt': datetime.now().isoformat()
        }

        self.rules.append(new_rule)
        self.save_rules()
        return new_rule

    def update_rule(self, rule_id: str, rule_data: Dict) -> Optional[Dict]:
        """Update existing rule"""
        rule = self.get_rule_by_id(rule_id)
        if not rule:
            return None

        rule.update({
            'code': rule_data['code'],
            'documentType': rule_data['documentType'],
            'description': rule_data['description'],
            'basis': rule_data['basis'],
            'priority': rule_data['priority'],
            'updatedAt': datetime.now().isoformat()
        })

        self.save_rules()
        return rule

    def delete_rule(self, rule_id: str) -> bool:
        """Delete rule"""
        rule = self.get_rule_by_id(rule_id)
        if not rule:
            return False

        self.rules.remove(rule)
        self.save_rules()
        return True

    def import_from_text(self, content: str) -> int:
        """
        Import rules from text format.
        
        Expected format (tab-separated):
        R-0002	Bill of Lading	must be signed...	ISBP 821 A1	Mandatory
        
        Args:
            content: Tab-separated text content
            
        Returns:
            Number of rules imported
        """
        lines = content.strip().split('\n')
        imported_count = 0

        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            parts = line.split('\t')
            if len(parts) >= 5:
                rule_data = {
                    'code': parts[0].strip(),
                    'documentType': parts[1].strip(),
                    'description': parts[2].strip(),
                    'basis': parts[3].strip(),
                    'priority': parts[4].strip()
                }

                # Check if rule with same code already exists
                existing = next((r for r in self.rules if r['code'] == rule_data['code']), None)
                if not existing:
                    self.add_rule(rule_data)
                    imported_count += 1

        return imported_count

    def export_to_xml(self) -> str:
        """Export rules to XML string"""
        root = ET.Element('discrepancyRules')
        root.set('version', '1.0')
        root.set('exportDate', datetime.now().isoformat())
        root.set('totalRules', str(len(self.rules)))

        for rule in self.rules:
            rule_elem = ET.SubElement(root, 'rule')
            rule_elem.set('id', rule['id'])
            rule_elem.set('code', rule['code'])

            ET.SubElement(rule_elem, 'documentType').text = rule['documentType']
            ET.SubElement(rule_elem, 'description').text = rule['description']
            ET.SubElement(rule_elem, 'basis').text = rule['basis']
            ET.SubElement(rule_elem, 'priority').text = rule['priority']
            ET.SubElement(rule_elem, 'createdAt').text = rule['createdAt']
            ET.SubElement(rule_elem, 'updatedAt').text = rule['updatedAt']

        # Pretty print XML
        xml_str = ET.tostring(root, encoding='unicode')
        dom = xml.dom.minidom.parseString(xml_str)
        return dom.toprettyxml(indent='  ')


# Module-level singleton instance
_discrepancy_rule_manager_instance = None


def get_discrepancy_rule_manager() -> DiscrepancyRuleManager:
    """Get or create the singleton DiscrepancyRuleManager instance."""
    global _discrepancy_rule_manager_instance
    if _discrepancy_rule_manager_instance is None:
        _discrepancy_rule_manager_instance = DiscrepancyRuleManager()
        logger.info("✅ Created DiscrepancyRuleManager singleton instance")
    return _discrepancy_rule_manager_instance


# Create singleton instance for backward compatibility
discrepancy_rule_manager = get_discrepancy_rule_manager()


def load_discrepancy_rules_from_xml(xml_path: Optional[str] = None) -> List[Dict]:
    """
    Load discrepancy rules from an XML file.
    
    Args:
        xml_path: Optional path to XML file. Uses default if not provided.
        
    Returns:
        List of rule dictionaries
    """
    manager = get_discrepancy_rule_manager()
    if xml_path and os.path.exists(xml_path):
        manager.rules_xml_path = xml_path
        manager.load_rules()
    return manager.get_all_rules()


def load_discrepancy_config(config_path: Optional[str] = None) -> Dict:
    """
    Load discrepancy configuration from file.
    
    Args:
        config_path: Optional path to config file
        
    Returns:
        Configuration dictionary
    """
    manager = get_discrepancy_rule_manager()
    return {
        'rules': manager.get_all_rules(),
        'rules_count': len(manager.rules),
        'xml_path': manager.rules_xml_path,
        'json_path': manager.rules_json_path
    }


def validate_config_structure(config: Dict) -> bool:
    """
    Validate that a configuration dictionary has the required structure.
    
    Args:
        config: Configuration dictionary to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not isinstance(config, dict):
        return False
    
    if 'rules' not in config:
        return False
    
    if not isinstance(config['rules'], list):
        return False
    
    # Validate each rule has required fields
    required_fields = ['code', 'documentType', 'description', 'basis', 'priority']
    for rule in config['rules']:
        if not isinstance(rule, dict):
            return False
        for field in required_fields:
            if field not in rule:
                return False
    
    return True
