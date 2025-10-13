"""
LangChain Tools for Intent-Based Microservices
Each tool represents a specialized microservice for handling specific intents
"""

from .data_query_tool import DataQueryTool
from .transaction_tool import TransactionTool
from .compliance_tool import ComplianceTool
from .document_analysis_tool import DocumentAnalysisTool
from .trade_finance_tool import TradeFinanceTool
from .treasury_tool import TreasuryTool
from .cash_management_tool import CashManagementTool
from .rag_tool import RAGTool

__all__ = [
    'DataQueryTool',
    'TransactionTool', 
    'ComplianceTool',
    'DocumentAnalysisTool',
    'TradeFinanceTool',
    'TreasuryTool',
    'CashManagementTool',
    'RAGTool'
]

# Tool registry for dynamic tool selection
TOOL_REGISTRY = {
    'data_query': DataQueryTool,
    'transaction': TransactionTool,
    'compliance': ComplianceTool,
    'document_analysis': DocumentAnalysisTool,
    'trade_finance': TradeFinanceTool,
    'treasury': TreasuryTool,
    'cash_management': CashManagementTool,
    'rag_search': RAGTool
}