"""
Repository-specific response handlers for chatbot
Provides fallback responses when AI API is unavailable
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Repository-specific responses
REPOSITORY_RESPONSES = {
    "Trade Finance Repository": {
        "greeting": "Welcome to Trade Finance! I can help you with import/export letters of credit, bank guarantees, and trade documents.",
        "capabilities": [
            "Create and manage Letters of Credit (LC)",
            "Process import and export documentation",
            "Handle bank guarantees",
            "Track SWIFT messages",
            "Generate compliance reports"
        ],
        "common_queries": {
            "create lc": "To create a new Letter of Credit, please provide:\n• Applicant details\n• Beneficiary information\n• LC amount and currency\n• Expiry date\n• Required documents",
            "check status": "I can help you check the status of your LC. Please provide the LC reference number.",
            "documents": "Required documents typically include:\n• Commercial Invoice\n• Bill of Lading\n• Packing List\n• Certificate of Origin\n• Insurance Documents",
            "swift": "I can help with SWIFT MT700 (LC Issuance), MT707 (Amendment), and MT799 (Free Format) messages."
        }
    },
    "Treasury Repository": {
        "greeting": "Welcome to Treasury Management! I can assist with foreign exchange, investments, derivatives, and risk management.",
        "capabilities": [
            "Execute foreign exchange trades",
            "Manage investment portfolios",
            "Handle derivatives and hedging",
            "Monitor market rates",
            "Assess and manage risk"
        ],
        "common_queries": {
            "forex": "For forex transactions, I need:\n• Currency pair (e.g., USD/EUR)\n• Transaction type (Spot/Forward/Swap)\n• Amount\n• Value date",
            "rates": "Current indicative rates:\n• USD/INR: 83.25\n• EUR/INR: 90.15\n• GBP/INR: 105.50\n(Note: These are sample rates. Please check with your dealer for live rates)",
            "investment": "Investment options include:\n• Fixed Deposits\n• Treasury Bills\n• Government Securities\n• Corporate Bonds\n• Money Market Instruments",
            "risk": "Risk management services:\n• Value at Risk (VaR) calculation\n• Sensitivity analysis\n• Hedge effectiveness testing\n• Exposure monitoring"
        }
    },
    "Cash Management Repository": {
        "greeting": "Welcome to Cash Management! I can help you optimize liquidity, manage payments, and forecast cash flows.",
        "capabilities": [
            "Monitor cash positions and liquidity",
            "Process payments and collections",
            "Manage cash pooling structures",
            "Generate cash flow forecasts",
            "Optimize working capital"
        ],
        "common_queries": {
            "balance": "I can show you current account balances and available liquidity. Which accounts would you like to view?",
            "payment": "To process a payment, please provide:\n• Beneficiary details\n• Amount and currency\n• Payment type (Wire/ACH/Check)\n• Value date",
            "forecast": "Cash flow forecasting options:\n• Daily cash position\n• Weekly forecast\n• Monthly projections\n• Scenario analysis",
            "pooling": "Cash pooling structures:\n• Zero balancing\n• Target balancing\n• Notional pooling\n• Cross-border pooling"
        }
    }
}

def get_repository_response(query: str, repository_name: str) -> Dict[str, Any]:
    """
    Get a response based on the query and connected repository
    
    Args:
        query: User's query text
        repository_name: Name of the connected repository
        
    Returns:
        Response dictionary with intent and answer
    """
    query_lower = query.lower()
    
    # Get repository-specific data
    repo_data = REPOSITORY_RESPONSES.get(repository_name, {})
    
    # Check for greeting
    if any(word in query_lower for word in ['hello', 'hi', 'hey', 'start', 'help']):
        capabilities = "\n• ".join(repo_data.get("capabilities", []))
        return {
            "intent": "greeting",
            "answer": f"{repo_data.get('greeting', 'Welcome!')}\n\nI can help you with:\n• {capabilities}\n\nWhat would you like to do today?"
        }
    
    # Check for common queries
    common_queries = repo_data.get("common_queries", {})
    for key, response in common_queries.items():
        if key in query_lower:
            return {
                "intent": "information",
                "answer": response
            }
    
    # Check for capability questions
    if any(word in query_lower for word in ['can you', 'what can', 'capabilities', 'features']):
        capabilities = "\n• ".join(repo_data.get("capabilities", []))
        return {
            "intent": "capabilities",
            "answer": f"With {repository_name}, I can help you:\n• {capabilities}"
        }
    
    # Default response for the repository
    return {
        "intent": "general",
        "answer": f"I'm connected to {repository_name}. {repo_data.get('greeting', '')}\n\nPlease tell me what you'd like to do, and I'll assist you accordingly."
    }

def get_fallback_response(query: str, repository_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Get a fallback response when AI API is unavailable
    
    Args:
        query: User's query text
        repository_name: Name of the connected repository (optional)
        
    Returns:
        Response dictionary with intent and answer
    """
    if repository_name:
        return get_repository_response(query, repository_name)
    else:
        # No repository connected
        return {
            "intent": "no_repository",
            "answer": "Welcome! I'm your AI assistant for financial operations.\n\n" +
                     "To get started, please connect to one of these repositories:\n\n" +
                     "🏦 **Trade Finance** - Import/Export Letters of Credit, Bank Guarantees\n" +
                     "💱 **Treasury** - Foreign Exchange, Investments, Risk Management\n" +
                     "💰 **Cash Management** - Liquidity, Payments, Cash Forecasting\n\n" +
                     "Click on 'No Repository' above to select and connect to a repository."
        }