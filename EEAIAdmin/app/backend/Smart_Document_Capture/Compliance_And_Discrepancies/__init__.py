"""
Compliance and Discrepancies Module
====================================

This module provides comprehensive discrepancy analysis functionality 
for trade finance document processing.

Key Components:
- LLMComplianceEngine: LLM-powered compliance checking for Tab 3 Standard Rules
- DiscrepancyRuleManager: Manages discrepancy rules with XML/JSON storage
- DiscrepancyAnalysisService: Performs LLM-powered discrepancy analysis
- DocumentEnhancementService: Enhances documents for UI display

Note: Field-level compliance analysis uses analyze_unified_compliance_fast() 
in app/utils/query_utils.py

Usage:
    from app.backend.Smart_Document_Capture.Compliance_And_Discrepancies import (
        LLMComplianceEngine,
        DiscrepancyRuleManager,
        perform_pure_llm_discrepancy_analysis,
        analyze_comprehensive_trade_finance_discrepancies
    )
"""

import logging

logger = logging.getLogger(__name__)

# Import from discrepancy_rule_manager
from .discrepancy_rule_manager import (
    DiscrepancyRuleManager,
    get_discrepancy_rule_manager,
    discrepancy_rule_manager,
    load_discrepancy_rules_from_xml,
    load_discrepancy_config,
    validate_config_structure
)

# Import from discrepancy_analysis_service
from .discrepancy_analysis_service import (
    perform_pure_llm_discrepancy_analysis,
    analyze_comprehensive_trade_finance_discrepancies,
    analyze_individual_document_discrepancies,
    apply_xml_rule_with_llm_analysis,
    extract_lc_structured_data,
    extract_enhanced_lc_data,
    extract_enhanced_swift_data,
    extract_enhanced_document_data,
    extract_swift_structured_data,
    validate_document_lc_context
)

# Import from document_enhancement_service
from .document_enhancement_service import (
    enhance_documents_for_discrepancy_analysis,
    enhance_data_for_professional_ui,
    enhance_discrepancy_for_ui,
    normalize_document_type
)

# Import from llm_compliance_engine
from .llm_compliance_engine import LLMComplianceEngine

# Import from field_level_compliance (for document classification compliance)
from .field_level_compliance import (
    FieldLevelComplianceAnalyzer,
    get_unified_compliance_result,
    clear_unified_compliance_result,
    analyze_field_level_compliance
)

# Import route registration
from .discrepancy_routes import register_discrepancy_routes
from .compliance_routes import register_compliance_routes

__all__ = [
    # LLM Compliance Engine (for Tab 3 Standard Rules)
    'LLMComplianceEngine',
    
    # Field-Level Compliance (for document classification)
    'FieldLevelComplianceAnalyzer',
    'get_unified_compliance_result',
    'clear_unified_compliance_result',
    'analyze_field_level_compliance',
    
    # Discrepancy Rules
    'DiscrepancyRuleManager',
    'get_discrepancy_rule_manager',
    'discrepancy_rule_manager',
    'load_discrepancy_rules_from_xml',
    'load_discrepancy_config',
    'validate_config_structure',
    
    # Discrepancy Analysis
    'perform_pure_llm_discrepancy_analysis',
    'analyze_comprehensive_trade_finance_discrepancies',
    'analyze_individual_document_discrepancies',
    'apply_xml_rule_with_llm_analysis',
    'extract_lc_structured_data',
    'extract_enhanced_lc_data',
    'extract_enhanced_swift_data',
    'extract_enhanced_document_data',
    'extract_swift_structured_data',
    'validate_document_lc_context',
    
    # Document Enhancement
    'enhance_documents_for_discrepancy_analysis',
    'enhance_data_for_professional_ui',
    'enhance_discrepancy_for_ui',
    'normalize_document_type',
    
    # Route Registration
    'register_discrepancy_routes',
    'register_compliance_routes'
]
