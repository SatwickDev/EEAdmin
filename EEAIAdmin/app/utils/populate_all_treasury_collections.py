"""
Populate all Treasury collections with comprehensive sample data
"""

import logging
import chromadb
from datetime import datetime, timedelta
import random
from app.utils.file_utils import get_embedding_azureRAG

logger = logging.getLogger(__name__)

def populate_all_treasury_collections():
    """Populate all 5 Treasury collections with sample data"""
    try:
        client = chromadb.HttpClient(host="localhost", port=8000)
        
        # 1. FOREX TRANSACTIONS
        logger.info("Populating forex_transactions collection...")
        forex_collection = client.get_or_create_collection(
            name="forex_transactions",
            metadata={"description": "Foreign Exchange transactions including spot, forward, and swap deals"}
        )
        
        forex_data = [
            # EUR Transactions
            {"transaction_id": "FX2024001001", "transaction_date": "2024-01-15", "value_date": "2024-01-17", "currency_pair": "EUR/USD", "buy_currency": "EUR", "sell_currency": "USD", "buy_amount": 5000000.00, "sell_amount": 5442500.00, "exchange_rate": 1.0885, "transaction_type": "SPOT", "client_name": "European Investment Fund", "status": "CONFIRMED"},
            {"transaction_id": "FX2024001002", "transaction_date": "2024-01-20", "value_date": "2024-04-20", "currency_pair": "EUR/GBP", "buy_currency": "EUR", "sell_currency": "GBP", "buy_amount": 3000000.00, "sell_amount": 2562600.00, "exchange_rate": 0.8542, "transaction_type": "FORWARD", "client_name": "Deutsche Bank", "status": "CONFIRMED"},
            {"transaction_id": "FX2024001003", "transaction_date": "2024-02-01", "value_date": "2024-02-03", "currency_pair": "EUR/CHF", "buy_currency": "EUR", "sell_currency": "CHF", "buy_amount": 2500000.00, "sell_amount": 2353000.00, "exchange_rate": 0.9412, "transaction_type": "SPOT", "client_name": "BNP Paribas", "status": "SETTLED"},
            {"transaction_id": "FX2024001004", "transaction_date": "2024-02-10", "value_date": "2024-02-12", "currency_pair": "EUR/JPY", "buy_currency": "EUR", "sell_currency": "JPY", "buy_amount": 4000000.00, "sell_amount": 636800000.00, "exchange_rate": 159.20, "transaction_type": "SPOT", "client_name": "Credit Agricole", "status": "CONFIRMED"},
            {"transaction_id": "FX2024001005", "transaction_date": "2024-02-15", "value_date": "2024-02-15", "currency_pair": "EUR/USD", "buy_currency": "EUR", "sell_currency": "USD", "buy_amount": 7500000.00, "sell_amount": 8156250.00, "exchange_rate": 1.0875, "transaction_type": "SWAP", "client_name": "European Central Bank", "status": "CONFIRMED"},
            
            # USD Transactions
            {"transaction_id": "FX2024002001", "transaction_date": "2024-01-10", "value_date": "2024-01-12", "currency_pair": "USD/AED", "buy_currency": "USD", "sell_currency": "AED", "buy_amount": 10000000.00, "sell_amount": 36730000.00, "exchange_rate": 3.673, "transaction_type": "SPOT", "client_name": "JP Morgan", "status": "SETTLED"},
            {"transaction_id": "FX2024002002", "transaction_date": "2024-01-25", "value_date": "2024-07-25", "currency_pair": "USD/EUR", "buy_currency": "USD", "sell_currency": "EUR", "buy_amount": 5000000.00, "sell_amount": 4595000.00, "exchange_rate": 0.919, "transaction_type": "FORWARD", "client_name": "Goldman Sachs", "status": "CONFIRMED"},
            {"transaction_id": "FX2024002003", "transaction_date": "2024-02-05", "value_date": "2024-02-07", "currency_pair": "USD/GBP", "buy_currency": "USD", "sell_currency": "GBP", "buy_amount": 8000000.00, "sell_amount": 6320000.00, "exchange_rate": 0.79, "transaction_type": "SPOT", "client_name": "Bank of America", "status": "CONFIRMED"},
            
            # GBP Transactions
            {"transaction_id": "FX2024003001", "transaction_date": "2024-01-18", "value_date": "2024-01-20", "currency_pair": "GBP/USD", "buy_currency": "GBP", "sell_currency": "USD", "buy_amount": 2000000.00, "sell_amount": 2540000.00, "exchange_rate": 1.27, "transaction_type": "SPOT", "client_name": "Barclays", "status": "SETTLED"},
            {"transaction_id": "FX2024003002", "transaction_date": "2024-02-08", "value_date": "2024-02-10", "currency_pair": "GBP/EUR", "buy_currency": "GBP", "sell_currency": "EUR", "buy_amount": 3500000.00, "sell_amount": 4095000.00, "exchange_rate": 1.17, "transaction_type": "SPOT", "client_name": "HSBC", "status": "CONFIRMED"},
        ]
        
        add_documents_to_collection(forex_collection, forex_data, "forex")
        
        # 2. MONEY MARKET
        logger.info("Populating money_market collection...")
        mm_collection = client.get_or_create_collection(
            name="money_market",
            metadata={"description": "Money market instruments and deals"}
        )
        
        money_market_data = [
            {"deal_id": "MM2024001001", "deal_date": "2024-01-10", "start_date": "2024-01-12", "maturity_date": "2024-07-12", "deal_type": "TERM_DEPOSIT", "counterparty": "First National Bank", "principal_amount": 50000000.00, "currency": "USD", "interest_rate": 5.25, "interest_basis": "ACT/360", "status": "ACTIVE"},
            {"deal_id": "MM2024001002", "deal_date": "2024-01-15", "start_date": "2024-01-15", "maturity_date": "2024-01-22", "deal_type": "CALL_DEPOSIT", "counterparty": "Central Bank", "principal_amount": 100000000.00, "currency": "EUR", "interest_rate": 4.15, "interest_basis": "ACT/365", "status": "ACTIVE"},
            {"deal_id": "MM2024001003", "deal_date": "2024-01-20", "start_date": "2024-01-22", "maturity_date": "2024-04-22", "deal_type": "COMMERCIAL_PAPER", "counterparty": "Corporate ABC", "principal_amount": 25000000.00, "currency": "GBP", "interest_rate": 5.50, "interest_basis": "30/360", "status": "ACTIVE"},
            {"deal_id": "MM2024001004", "deal_date": "2024-02-01", "start_date": "2024-02-01", "maturity_date": "2024-02-08", "deal_type": "REPO", "counterparty": "Investment Bank XYZ", "principal_amount": 75000000.00, "currency": "EUR", "interest_rate": 4.00, "collateral": "Government Bonds", "status": "ACTIVE"},
            {"deal_id": "MM2024001005", "deal_date": "2024-02-05", "start_date": "2024-02-07", "maturity_date": "2024-08-07", "deal_type": "TERM_DEPOSIT", "counterparty": "Deutsche Bank", "principal_amount": 30000000.00, "currency": "EUR", "interest_rate": 4.85, "interest_basis": "ACT/360", "status": "ACTIVE"},
            {"deal_id": "MM2024001006", "deal_date": "2024-02-10", "start_date": "2024-02-12", "maturity_date": "2024-05-12", "deal_type": "CERTIFICATE_OF_DEPOSIT", "counterparty": "Bank of Tokyo", "principal_amount": 40000000.00, "currency": "JPY", "interest_rate": 0.25, "interest_basis": "ACT/365", "status": "ACTIVE"},
        ]
        
        add_documents_to_collection(mm_collection, money_market_data, "money_market")
        
        # 3. DERIVATIVES
        logger.info("Populating derivatives collection...")
        deriv_collection = client.get_or_create_collection(
            name="derivatives",
            metadata={"description": "Derivative instruments for hedging and trading"}
        )
        
        derivatives_data = [
            {"trade_id": "DER2024000501", "trade_date": "2024-01-08", "product_type": "FX_OPTION", "underlying_asset": "EUR/USD", "notional_amount": 10000000.00, "currency": "EUR", "strike_price": 1.10, "expiry_date": "2024-03-08", "option_type": "CALL", "premium": 125000.00, "counterparty": "Investment Bank ABC", "trader": "Michael Chen", "status": "OPEN"},
            {"trade_id": "DER2024000502", "trade_date": "2024-01-15", "product_type": "INTEREST_RATE_SWAP", "underlying_asset": "EURIBOR_3M", "notional_amount": 100000000.00, "currency": "EUR", "fixed_rate": 3.75, "floating_rate": "EURIBOR_3M", "maturity_date": "2029-01-15", "counterparty": "Hedge Fund XYZ", "trader": "Emily Wang", "status": "ACTIVE"},
            {"trade_id": "DER2024000503", "trade_date": "2024-01-20", "product_type": "CURRENCY_SWAP", "underlying_asset": "EUR/GBP", "notional_amount": 50000000.00, "currency": "EUR", "exchange_rate": 0.86, "maturity_date": "2026-01-20", "counterparty": "Bank of London", "trader": "James Smith", "status": "ACTIVE"},
            {"trade_id": "DER2024000504", "trade_date": "2024-02-01", "product_type": "FX_FORWARD", "underlying_asset": "EUR/CHF", "notional_amount": 25000000.00, "currency": "EUR", "forward_rate": 0.95, "value_date": "2024-08-01", "counterparty": "Swiss Bank Corp", "trader": "Sophie Mueller", "status": "OPEN"},
            {"trade_id": "DER2024000505", "trade_date": "2024-02-10", "product_type": "FX_OPTION", "underlying_asset": "GBP/USD", "notional_amount": 15000000.00, "currency": "GBP", "strike_price": 1.28, "expiry_date": "2024-05-10", "option_type": "PUT", "premium": 185000.00, "counterparty": "Options Trading LLC", "trader": "David Brown", "status": "OPEN"},
        ]
        
        add_documents_to_collection(deriv_collection, derivatives_data, "derivatives")
        
        # 4. INVESTMENTS
        logger.info("Populating investments collection...")
        inv_collection = client.get_or_create_collection(
            name="investments",
            metadata={"description": "Investment portfolio holdings"}
        )
        
        investments_data = [
            # EUR Denominated Investments
            {"investment_id": "INV2024000101", "isin": "XS1234567890", "security_name": "European Investment Bank Bond 2029", "asset_class": "GOVERNMENT_BOND", "issuer": "European Investment Bank", "purchase_date": "2023-06-15", "maturity_date": "2029-06-15", "face_value": 10000000.00, "currency": "EUR", "coupon_rate": 2.75, "rating": "AAA", "portfolio": "HTM"},
            {"investment_id": "INV2024000102", "isin": "DE0001102309", "security_name": "German Bund 10Y", "asset_class": "SOVEREIGN_BOND", "issuer": "Federal Republic of Germany", "purchase_date": "2023-09-20", "maturity_date": "2034-02-15", "face_value": 20000000.00, "currency": "EUR", "coupon_rate": 2.50, "rating": "AAA", "portfolio": "AFS"},
            {"investment_id": "INV2024000103", "isin": "FR0013234333", "security_name": "French OAT 2030", "asset_class": "GOVERNMENT_BOND", "issuer": "Republic of France", "purchase_date": "2023-11-10", "maturity_date": "2030-05-25", "face_value": 15000000.00, "currency": "EUR", "coupon_rate": 3.00, "rating": "AA", "portfolio": "HTM"},
            {"investment_id": "INV2024000104", "isin": "IT0005438004", "security_name": "Italian BTP 2028", "asset_class": "GOVERNMENT_BOND", "issuer": "Republic of Italy", "purchase_date": "2024-01-05", "maturity_date": "2028-12-01", "face_value": 8000000.00, "currency": "EUR", "coupon_rate": 3.85, "rating": "BBB", "portfolio": "TRADING"},
            {"investment_id": "INV2024000105", "isin": "ES0000012932", "security_name": "Spanish Bonos 2032", "asset_class": "GOVERNMENT_BOND", "issuer": "Kingdom of Spain", "purchase_date": "2024-01-15", "maturity_date": "2032-10-31", "face_value": 12000000.00, "currency": "EUR", "coupon_rate": 3.45, "rating": "A", "portfolio": "AFS"},
            
            # USD Investments
            {"investment_id": "INV2024000201", "isin": "US912828XY01", "security_name": "US Treasury Note 5Y", "asset_class": "GOVERNMENT_BOND", "issuer": "US Treasury", "purchase_date": "2023-09-20", "maturity_date": "2028-09-20", "face_value": 25000000.00, "currency": "USD", "coupon_rate": 4.25, "rating": "AAA", "portfolio": "AFS"},
            {"investment_id": "INV2024000202", "isin": "US594918BP35", "security_name": "Microsoft Corp Bond 2027", "asset_class": "CORPORATE_BOND", "issuer": "Microsoft Corporation", "purchase_date": "2024-01-10", "maturity_date": "2027-02-12", "face_value": 5000000.00, "currency": "USD", "coupon_rate": 3.95, "rating": "AAA", "portfolio": "HTM"},
            
            # GBP Investment
            {"investment_id": "INV2024000301", "isin": "GB00B7Z53659", "security_name": "UK Gilt 2030", "asset_class": "GOVERNMENT_BOND", "issuer": "UK Treasury", "purchase_date": "2023-12-01", "maturity_date": "2030-01-31", "face_value": 10000000.00, "currency": "GBP", "coupon_rate": 4.75, "rating": "AA", "portfolio": "AFS"},
        ]
        
        add_documents_to_collection(inv_collection, investments_data, "investments")
        
        # 5. HEDGING INSTRUMENTS
        logger.info("Populating hedging_instruments collection...")
        hedge_collection = client.get_or_create_collection(
            name="hedging_instruments",
            metadata={"description": "Risk management hedging positions"}
        )
        
        hedging_data = [
            {"hedge_id": "HDG2024000201", "hedge_type": "FAIR_VALUE_HEDGE", "hedged_item": "EUR Fixed Rate Bond Portfolio", "hedge_instrument": "EUR Interest Rate Swap", "hedge_ratio": 0.95, "notional_amount": 50000000.00, "currency": "EUR", "start_date": "2024-01-01", "end_date": "2024-12-31", "hedge_effectiveness": 98.5, "status": "EFFECTIVE"},
            {"hedge_id": "HDG2024000202", "hedge_type": "CASH_FLOW_HEDGE", "hedged_item": "Forecasted EUR Sales Q2-Q4", "hedge_instrument": "EUR/USD Forward Contracts", "hedge_ratio": 0.85, "notional_amount": 30000000.00, "currency": "EUR", "start_date": "2024-01-15", "end_date": "2024-12-31", "hedge_effectiveness": 92.3, "status": "EFFECTIVE"},
            {"hedge_id": "HDG2024000203", "hedge_type": "NET_INVESTMENT_HEDGE", "hedged_item": "UK Subsidiary Net Assets", "hedge_instrument": "GBP/EUR Cross Currency Swap", "hedge_ratio": 1.00, "notional_amount": 25000000.00, "currency": "GBP", "start_date": "2024-02-01", "end_date": "2029-02-01", "hedge_effectiveness": 99.2, "status": "EFFECTIVE"},
            {"hedge_id": "HDG2024000204", "hedge_type": "FAIR_VALUE_HEDGE", "hedged_item": "USD Corporate Bond Holdings", "hedge_instrument": "USD Interest Rate Futures", "hedge_ratio": 0.90, "notional_amount": 40000000.00, "currency": "USD", "start_date": "2024-01-20", "end_date": "2024-07-20", "hedge_effectiveness": 95.7, "status": "EFFECTIVE"},
        ]
        
        add_documents_to_collection(hedge_collection, hedging_data, "hedging")
        
        logger.info("✅ All Treasury collections populated successfully!")
        
        # Return summary
        summary = {
            "forex_transactions": len(forex_data),
            "money_market": len(money_market_data),
            "derivatives": len(derivatives_data),
            "investments": len(investments_data),
            "hedging_instruments": len(hedging_data)
        }
        
        return True, summary
        
    except Exception as e:
        logger.error(f"Error populating Treasury collections: {e}")
        return False, str(e)

def add_documents_to_collection(collection, data_list, collection_type):
    """Helper function to add documents to a ChromaDB collection"""
    documents = []
    metadatas = []
    ids = []
    embeddings = []
    
    for i, record in enumerate(data_list):
        # Create document text
        doc_text = ""
        for field, value in record.items():
            doc_text += f"{field}: {value}\n"
        
        documents.append(doc_text)
        
        # Create metadata
        metadata = {
            "source": "treasury",
            "type": collection_type,
            "date": record.get("transaction_date", record.get("deal_date", record.get("trade_date", record.get("purchase_date", str(datetime.now().date())))))
        }
        
        # Add currency if present
        if "currency" in record:
            metadata["currency"] = record["currency"]
        if "status" in record:
            metadata["status"] = record["status"]
        if "asset_class" in record:
            metadata["asset_class"] = record["asset_class"]
            
        metadatas.append(metadata)
        
        # Create unique ID
        ids.append(f"{collection_type}_{i+1:04d}")
        
        # Generate embedding
        embedding = get_embedding_azureRAG(doc_text)
        embeddings.append(embedding)
    
    # Add all documents to collection
    if documents:
        collection.add(
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
            ids=ids
        )
        logger.info(f"Added {len(documents)} documents to {collection_type} collection")