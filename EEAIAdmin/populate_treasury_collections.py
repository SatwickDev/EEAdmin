#!/usr/bin/env python3
"""
Populate Treasury collections in ChromaDB with sample data
"""

import chromadb
import json
import logging
from datetime import datetime, timedelta
import random

# Import the sample data
from treasury_collections_sample import TREASURY_COLLECTIONS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def populate_treasury_collections():
    """Populate Treasury collections with sample data"""
    try:
        # Connect to ChromaDB
        logger.info("Connecting to ChromaDB...")
        client = chromadb.HttpClient(host="localhost", port=8000)
        
        # Get Azure OpenAI embedding function
        from app.utils.file_utils import get_embedding_azureRAG
        
        for collection_name, collection_config in TREASURY_COLLECTIONS.items():
            logger.info(f"\nProcessing collection: {collection_name}")
            
            try:
                # Create or get collection
                collection = client.get_or_create_collection(
                    name=collection_name,
                    metadata={"description": collection_config["description"]}
                )
                
                # Check if collection already has data
                existing_count = collection.count()
                if existing_count > 0:
                    logger.info(f"Collection {collection_name} already has {existing_count} documents. Skipping...")
                    continue
                
                # Prepare documents
                documents = []
                metadatas = []
                ids = []
                embeddings = []
                
                # Process sample data
                sample_data = collection_config.get("sample_data", [])
                
                for i, record in enumerate(sample_data):
                    # Create document text from record fields
                    doc_text = ""
                    for field, value in record.items():
                        doc_text += f"{field}: {value}\n"
                    
                    documents.append(doc_text)
                    
                    # Create metadata
                    metadata = {
                        "source": "treasury",
                        "type": collection_name,
                        "date": record.get("transaction_date", record.get("deal_date", record.get("trade_date", str(datetime.now().date()))))
                    }
                    # Add key fields to metadata for filtering
                    if "currency" in record:
                        metadata["currency"] = record["currency"]
                    if "status" in record:
                        metadata["status"] = record["status"]
                    if "transaction_type" in record:
                        metadata["transaction_type"] = record["transaction_type"]
                    
                    metadatas.append(metadata)
                    
                    # Create unique ID
                    ids.append(f"{collection_name}_{i+1:04d}")
                    
                    # Generate embedding
                    logger.info(f"Generating embedding for document {i+1}/{len(sample_data)}...")
                    embedding = get_embedding_azureRAG(doc_text)
                    embeddings.append(embedding)
                
                # Add to collection
                if documents:
                    logger.info(f"Adding {len(documents)} documents to {collection_name}...")
                    collection.add(
                        documents=documents,
                        metadatas=metadatas,
                        embeddings=embeddings,
                        ids=ids
                    )
                    logger.info(f"✓ Successfully added {len(documents)} documents to {collection_name}")
                
                # Generate additional synthetic data for better testing
                if len(sample_data) < 10:
                    logger.info(f"Generating additional synthetic data for {collection_name}...")
                    synthetic_count = 20 - len(sample_data)
                    
                    for i in range(synthetic_count):
                        # Generate synthetic record based on collection type
                        if collection_name == "forex_transactions":
                            record = generate_synthetic_forex_record(i + len(sample_data))
                        elif collection_name == "money_market":
                            record = generate_synthetic_money_market_record(i + len(sample_data))
                        elif collection_name == "derivatives":
                            record = generate_synthetic_derivatives_record(i + len(sample_data))
                        elif collection_name == "investments":
                            record = generate_synthetic_investment_record(i + len(sample_data))
                        elif collection_name == "hedging_instruments":
                            record = generate_synthetic_hedge_record(i + len(sample_data))
                        else:
                            continue
                        
                        # Process synthetic record
                        doc_text = ""
                        for field, value in record.items():
                            doc_text += f"{field}: {value}\n"
                        
                        # Generate embedding and add to collection
                        embedding = get_embedding_azureRAG(doc_text)
                        
                        metadata = {
                            "source": "treasury",
                            "type": collection_name,
                            "date": str(datetime.now().date()),
                            "synthetic": True
                        }
                        
                        collection.add(
                            documents=[doc_text],
                            metadatas=[metadata],
                            embeddings=[embedding],
                            ids=[f"{collection_name}_synthetic_{i+1:04d}"]
                        )
                    
                    logger.info(f"✓ Added {synthetic_count} synthetic documents to {collection_name}")
                
            except Exception as e:
                logger.error(f"Error processing collection {collection_name}: {e}")
                continue
        
        logger.info("\n✅ Treasury collections population completed!")
        
        # Print summary
        logger.info("\nCollection Summary:")
        for collection_name in TREASURY_COLLECTIONS.keys():
            try:
                collection = client.get_collection(collection_name)
                count = collection.count()
                logger.info(f"  - {collection_name}: {count} documents")
            except:
                logger.info(f"  - {collection_name}: Not created")
                
    except Exception as e:
        logger.error(f"Failed to populate Treasury collections: {e}")
        raise

def generate_synthetic_forex_record(index):
    """Generate synthetic forex transaction record"""
    currencies = ["USD", "EUR", "GBP", "JPY", "CHF", "AUD", "CAD"]
    transaction_types = ["SPOT", "FORWARD", "SWAP"]
    
    base_currency = random.choice(currencies)
    quote_currency = random.choice([c for c in currencies if c != base_currency])
    
    return {
        "transaction_id": f"FX2024{1000 + index:06d}",
        "transaction_date": (datetime.now() - timedelta(days=random.randint(1, 90))).strftime("%Y-%m-%d"),
        "value_date": (datetime.now() + timedelta(days=random.randint(1, 180))).strftime("%Y-%m-%d"),
        "currency_pair": f"{base_currency}/{quote_currency}",
        "buy_currency": base_currency,
        "sell_currency": quote_currency,
        "buy_amount": round(random.uniform(100000, 10000000), 2),
        "sell_amount": round(random.uniform(100000, 10000000), 2),
        "exchange_rate": round(random.uniform(0.5, 2.0), 4),
        "transaction_type": random.choice(transaction_types),
        "client_name": f"Client {index}",
        "status": random.choice(["CONFIRMED", "PENDING", "SETTLED"])
    }

def generate_synthetic_money_market_record(index):
    """Generate synthetic money market record"""
    deal_types = ["TERM_DEPOSIT", "CALL_DEPOSIT", "COMMERCIAL_PAPER", "REPO"]
    currencies = ["USD", "EUR", "GBP", "AED"]
    
    return {
        "deal_id": f"MM2024{2000 + index:06d}",
        "deal_date": (datetime.now() - timedelta(days=random.randint(1, 30))).strftime("%Y-%m-%d"),
        "start_date": (datetime.now() + timedelta(days=random.randint(1, 7))).strftime("%Y-%m-%d"),
        "maturity_date": (datetime.now() + timedelta(days=random.randint(30, 365))).strftime("%Y-%m-%d"),
        "deal_type": random.choice(deal_types),
        "counterparty": f"Bank {chr(65 + index % 26)}",
        "principal_amount": round(random.uniform(1000000, 100000000), 2),
        "currency": random.choice(currencies),
        "interest_rate": round(random.uniform(2.0, 6.0), 2),
        "status": "ACTIVE"
    }

def generate_synthetic_derivatives_record(index):
    """Generate synthetic derivatives record"""
    product_types = ["FX_OPTION", "INTEREST_RATE_SWAP", "CURRENCY_SWAP", "FX_FORWARD"]
    currencies = ["USD", "EUR", "GBP", "JPY"]
    
    return {
        "trade_id": f"DER2024{3000 + index:06d}",
        "trade_date": (datetime.now() - timedelta(days=random.randint(1, 60))).strftime("%Y-%m-%d"),
        "product_type": random.choice(product_types),
        "underlying_asset": f"{random.choice(currencies)}/{random.choice(currencies)}",
        "notional_amount": round(random.uniform(1000000, 50000000), 2),
        "currency": random.choice(currencies),
        "expiry_date": (datetime.now() + timedelta(days=random.randint(30, 730))).strftime("%Y-%m-%d"),
        "counterparty": f"Institution {index}",
        "status": random.choice(["OPEN", "CLOSED", "EXPIRED"])
    }

def generate_synthetic_investment_record(index):
    """Generate synthetic investment record"""
    asset_classes = ["GOVERNMENT_BOND", "CORPORATE_BOND", "EQUITY", "MUTUAL_FUND"]
    currencies = ["USD", "EUR", "GBP", "AED"]
    ratings = ["AAA", "AA", "A", "BBB", "BB"]
    
    return {
        "investment_id": f"INV2024{4000 + index:06d}",
        "isin": f"XS{random.randint(1000000000, 9999999999)}",
        "security_name": f"{random.choice(['Government', 'Corporate'])} Bond {index}",
        "asset_class": random.choice(asset_classes),
        "issuer": f"Issuer {chr(65 + index % 26)}",
        "currency": random.choice(currencies),
        "face_value": round(random.uniform(1000000, 50000000), 2),
        "current_price": round(random.uniform(95.0, 105.0), 2),
        "rating": random.choice(ratings),
        "maturity_date": (datetime.now() + timedelta(days=random.randint(365, 3650))).strftime("%Y-%m-%d")
    }

def generate_synthetic_hedge_record(index):
    """Generate synthetic hedging record"""
    hedge_types = ["FAIR_VALUE_HEDGE", "CASH_FLOW_HEDGE", "NET_INVESTMENT_HEDGE"]
    currencies = ["USD", "EUR", "GBP"]
    
    return {
        "hedge_id": f"HDG2024{5000 + index:06d}",
        "hedge_type": random.choice(hedge_types),
        "hedged_item": f"Portfolio {index}",
        "hedge_ratio": round(random.uniform(0.8, 1.0), 2),
        "notional_amount": round(random.uniform(5000000, 100000000), 2),
        "currency": random.choice(currencies),
        "start_date": (datetime.now() - timedelta(days=random.randint(1, 90))).strftime("%Y-%m-%d"),
        "end_date": (datetime.now() + timedelta(days=random.randint(90, 730))).strftime("%Y-%m-%d"),
        "hedge_effectiveness": round(random.uniform(85.0, 99.9), 1),
        "status": "EFFECTIVE"
    }

if __name__ == "__main__":
    # Add parent directory to path
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    populate_treasury_collections()