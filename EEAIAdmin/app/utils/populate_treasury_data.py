"""
Utility to populate Treasury collections with sample data
"""

import logging
import chromadb
from datetime import datetime
from app.utils.file_utils import get_embedding_azureRAG

logger = logging.getLogger(__name__)

def populate_treasury_collections():
    """Populate Treasury collections with sample EUR investment data"""
    try:
        client = chromadb.HttpClient(host="localhost", port=8000)
        
        # Create forex_transactions collection with EUR data
        collection = client.get_or_create_collection(
            name="forex_transactions",
            metadata={"description": "Foreign Exchange transactions"}
        )
        
        # Sample EUR investment/forex data
        eur_investments = [
            {
                "transaction_id": "FX2024001001",
                "transaction_date": "2024-01-15",
                "currency_pair": "EUR/USD",
                "transaction_type": "INVESTMENT",
                "buy_currency": "EUR",
                "buy_amount": 5000000.00,
                "exchange_rate": 1.0885,
                "client_name": "European Investment Fund",
                "investment_type": "GOVERNMENT_BOND",
                "status": "CONFIRMED"
            },
            {
                "transaction_id": "FX2024001002", 
                "transaction_date": "2024-01-20",
                "currency_pair": "EUR/USD",
                "transaction_type": "INVESTMENT",
                "buy_currency": "EUR",
                "buy_amount": 3000000.00,
                "exchange_rate": 1.0890,
                "client_name": "Deutsche Bank",
                "investment_type": "CORPORATE_BOND",
                "status": "CONFIRMED"
            },
            {
                "transaction_id": "FX2024001003",
                "transaction_date": "2024-02-01", 
                "currency_pair": "EUR/GBP",
                "transaction_type": "INVESTMENT",
                "buy_currency": "EUR",
                "buy_amount": 2500000.00,
                "exchange_rate": 0.8542,
                "client_name": "BNP Paribas",
                "investment_type": "EQUITY_FUND",
                "status": "CONFIRMED"
            },
            {
                "transaction_id": "FX2024001004",
                "transaction_date": "2024-02-10",
                "currency_pair": "EUR/CHF", 
                "transaction_type": "INVESTMENT",
                "buy_currency": "EUR",
                "buy_amount": 4000000.00,
                "exchange_rate": 0.9412,
                "client_name": "Credit Suisse",
                "investment_type": "MONEY_MARKET",
                "status": "CONFIRMED"
            },
            {
                "transaction_id": "FX2024001005",
                "transaction_date": "2024-02-15",
                "currency_pair": "EUR/USD",
                "transaction_type": "INVESTMENT", 
                "buy_currency": "EUR",
                "buy_amount": 7500000.00,
                "exchange_rate": 1.0875,
                "client_name": "European Central Bank",
                "investment_type": "SOVEREIGN_BOND",
                "status": "CONFIRMED"
            }
        ]
        
        # Add documents to collection
        documents = []
        metadatas = []
        ids = []
        embeddings = []
        
        for i, record in enumerate(eur_investments):
            # Create document text
            doc_text = ""
            for field, value in record.items():
                doc_text += f"{field}: {value}\n"
            
            documents.append(doc_text)
            
            # Create metadata
            metadata = {
                "source": "treasury",
                "type": "forex_investment",
                "currency": "EUR",
                "date": record["transaction_date"],
                "status": record["status"]
            }
            metadatas.append(metadata)
            
            # Create ID
            ids.append(f"treasury_eur_{i+1:04d}")
            
            # Generate embedding
            embedding = get_embedding_azureRAG(doc_text)
            embeddings.append(embedding)
        
        # Add to collection
        collection.add(
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
            ids=ids
        )
        
        logger.info(f"Successfully added {len(documents)} EUR investment records to forex_transactions collection")
        
        # Also create investments collection
        inv_collection = client.get_or_create_collection(
            name="investments",
            metadata={"description": "Investment portfolio"}
        )
        
        # Sample investment portfolio data
        investments = [
            {
                "investment_id": "INV2024000101",
                "isin": "XS1234567890",
                "security_name": "European Investment Bank Bond 2029",
                "asset_class": "GOVERNMENT_BOND",
                "currency": "EUR",
                "face_value": 10000000.00,
                "current_price": 102.50,
                "rating": "AAA",
                "maturity_date": "2029-12-31"
            },
            {
                "investment_id": "INV2024000102",
                "isin": "DE0001102309",
                "security_name": "German Bund 10Y",
                "asset_class": "SOVEREIGN_BOND", 
                "currency": "EUR",
                "face_value": 20000000.00,
                "current_price": 98.75,
                "rating": "AAA",
                "maturity_date": "2034-02-15"
            },
            {
                "investment_id": "INV2024000103",
                "isin": "FR0013234333",
                "security_name": "French OAT 2030",
                "asset_class": "GOVERNMENT_BOND",
                "currency": "EUR", 
                "face_value": 15000000.00,
                "current_price": 99.25,
                "rating": "AA",
                "maturity_date": "2030-05-25"
            }
        ]
        
        # Add investment documents
        inv_documents = []
        inv_metadatas = []
        inv_ids = []
        inv_embeddings = []
        
        for i, record in enumerate(investments):
            doc_text = ""
            for field, value in record.items():
                doc_text += f"{field}: {value}\n"
            
            inv_documents.append(doc_text)
            inv_metadatas.append({
                "source": "treasury",
                "type": "investment",
                "currency": "EUR",
                "asset_class": record["asset_class"]
            })
            inv_ids.append(f"inv_eur_{i+1:04d}")
            inv_embeddings.append(get_embedding_azureRAG(doc_text))
        
        inv_collection.add(
            documents=inv_documents,
            metadatas=inv_metadatas,
            embeddings=inv_embeddings,
            ids=inv_ids
        )
        
        logger.info(f"Successfully added {len(inv_documents)} EUR investment portfolio records")
        
        return True
        
    except Exception as e:
        logger.error(f"Error populating Treasury collections: {e}")
        return False