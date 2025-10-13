#!/usr/bin/env python3
"""
Script to populate sample fields for document types in the DOC_LIST directory.
This will help test the document type management functionality.
"""

import json
import os
from pathlib import Path

# Sample field definitions for different document types
SAMPLE_FIELDS = {
    "Air_Waybill": [
        {"name": "AWB Number", "type": "text", "required": True, "description": "Air Waybill tracking number"},
        {"name": "Shipper Name", "type": "text", "required": True, "description": "Name of the shipping party"},
        {"name": "Consignee Name", "type": "text", "required": True, "description": "Name of the receiving party"},
        {"name": "Origin Airport", "type": "text", "required": True, "description": "Airport of departure"},
        {"name": "Destination Airport", "type": "text", "required": True, "description": "Airport of arrival"},
        {"name": "Flight Number", "type": "text", "required": False, "description": "Flight identification"},
        {"name": "Date of Shipment", "type": "date", "required": True, "description": "Date when goods were shipped"},
        {"name": "Number of Pieces", "type": "number", "required": True, "description": "Total number of packages"},
        {"name": "Gross Weight", "type": "number", "required": True, "description": "Total weight in kg"},
        {"name": "Chargeable Weight", "type": "number", "required": False, "description": "Weight used for charge calculation"}
    ],
    "Bill_of_Lading": [
        {"name": "B/L Number", "type": "text", "required": True, "description": "Bill of Lading number"},
        {"name": "Shipper", "type": "text", "required": True, "description": "Party shipping the goods"},
        {"name": "Consignee", "type": "text", "required": True, "description": "Party receiving the goods"},
        {"name": "Notify Party", "type": "text", "required": False, "description": "Party to be notified"},
        {"name": "Vessel Name", "type": "text", "required": True, "description": "Name of the ship"},
        {"name": "Voyage Number", "type": "text", "required": False, "description": "Voyage identification"},
        {"name": "Port of Loading", "type": "text", "required": True, "description": "Port where goods are loaded"},
        {"name": "Port of Discharge", "type": "text", "required": True, "description": "Port where goods are unloaded"},
        {"name": "Container Number", "type": "text", "required": False, "description": "Container identification"},
        {"name": "Seal Number", "type": "text", "required": False, "description": "Security seal number"}
    ],
    "Commercial_Invoice": [
        {"name": "Invoice Number", "type": "text", "required": True, "description": "Unique invoice identifier"},
        {"name": "Invoice Date", "type": "date", "required": True, "description": "Date of invoice issue"},
        {"name": "Seller Name", "type": "text", "required": True, "description": "Name of the selling party"},
        {"name": "Buyer Name", "type": "text", "required": True, "description": "Name of the buying party"},
        {"name": "Currency", "type": "text", "required": True, "description": "Currency code (USD, EUR, etc.)"},
        {"name": "Total Amount", "type": "number", "required": True, "description": "Total invoice value"},
        {"name": "Payment Terms", "type": "text", "required": True, "description": "Terms of payment"},
        {"name": "Incoterms", "type": "text", "required": False, "description": "International commercial terms"},
        {"name": "Country of Origin", "type": "text", "required": False, "description": "Country where goods originated"},
        {"name": "HS Code", "type": "text", "required": False, "description": "Harmonized System code"}
    ],
    "Letter_of_Credit": [
        {"name": "LC Number", "type": "text", "required": True, "description": "Letter of Credit number"},
        {"name": "Issue Date", "type": "date", "required": True, "description": "Date of LC issuance"},
        {"name": "Expiry Date", "type": "date", "required": True, "description": "Date of LC expiry"},
        {"name": "Applicant", "type": "text", "required": True, "description": "Party applying for LC"},
        {"name": "Beneficiary", "type": "text", "required": True, "description": "Party receiving payment"},
        {"name": "Issuing Bank", "type": "text", "required": True, "description": "Bank issuing the LC"},
        {"name": "Advising Bank", "type": "text", "required": False, "description": "Bank advising the LC"},
        {"name": "Currency", "type": "text", "required": True, "description": "LC currency"},
        {"name": "Amount", "type": "number", "required": True, "description": "LC amount"},
        {"name": "Type", "type": "text", "required": True, "description": "LC type (Irrevocable, Confirmed, etc.)"}
    ],
    "Packing_List": [
        {"name": "Packing List Number", "type": "text", "required": True, "description": "Unique packing list ID"},
        {"name": "Date", "type": "date", "required": True, "description": "Date of packing list"},
        {"name": "Shipper", "type": "text", "required": True, "description": "Party shipping goods"},
        {"name": "Consignee", "type": "text", "required": True, "description": "Party receiving goods"},
        {"name": "Number of Packages", "type": "number", "required": True, "description": "Total package count"},
        {"name": "Total Gross Weight", "type": "number", "required": True, "description": "Total weight with packaging"},
        {"name": "Total Net Weight", "type": "number", "required": True, "description": "Total weight without packaging"},
        {"name": "Package Type", "type": "text", "required": False, "description": "Type of packaging used"},
        {"name": "Marks and Numbers", "type": "text", "required": False, "description": "Package identification marks"}
    ]
}

def populate_document_fields():
    """Populate sample fields for document types"""
    
    # Path to DOC_LIST directory
    doc_list_path = Path("/mnt/c/Users/AIAdmin/Desktop/EEAIAdmin/app/prompts/EE/DOC_LIST")
    
    if not doc_list_path.exists():
        print(f"❌ Directory not found: {doc_list_path}")
        return
    
    print(f"📁 Working in directory: {doc_list_path}")
    print("=" * 60)
    
    # Process each document type
    for doc_type, fields in SAMPLE_FIELDS.items():
        filename = f"{doc_type}_OCR_Fields.json"
        filepath = doc_list_path / filename
        
        print(f"\n📄 Processing: {filename}")
        
        # Check if file exists
        if filepath.exists():
            # Read existing content
            try:
                with open(filepath, 'r') as f:
                    content = f.read().strip()
                    if content:
                        existing = json.loads(content)
                        print(f"   ℹ️  File has {len(existing)} existing fields")
                    else:
                        existing = []
                        print(f"   ⚠️  File is empty")
            except Exception as e:
                print(f"   ❌ Error reading file: {e}")
                existing = []
            
            # Write new fields
            try:
                with open(filepath, 'w') as f:
                    json.dump(fields, f, indent=2)
                print(f"   ✅ Updated with {len(fields)} sample fields")
            except Exception as e:
                print(f"   ❌ Error writing file: {e}")
        else:
            print(f"   ⚠️  File not found, skipping")
    
    # Also initialize empty files with empty arrays
    print("\n" + "=" * 60)
    print("🔧 Initializing empty files...")
    
    for filename in os.listdir(doc_list_path):
        if filename.endswith("_OCR_Fields.json"):
            filepath = doc_list_path / filename
            try:
                with open(filepath, 'r') as f:
                    content = f.read().strip()
                    if not content:
                        # Initialize with empty array
                        with open(filepath, 'w') as f:
                            json.dump([], f)
                        print(f"   ✅ Initialized empty file: {filename}")
            except Exception as e:
                print(f"   ❌ Error processing {filename}: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Document fields population complete!")

if __name__ == "__main__":
    populate_document_fields()