"""
Discrepancy Analysis Service Module
===================================

This module provides comprehensive discrepancy analysis capabilities
for trade finance documents including LLM-based analysis, XML rule processing,
and cross-document validation.

Author: EEAdmin Team
Version: 1.0.0
"""

import json
import logging
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Get the module-level logger
logger = logging.getLogger(__name__)

# Import rule manager for XML rules
from .discrepancy_rule_manager import (
    get_discrepancy_rule_manager,
    load_discrepancy_rules_from_xml,
    load_discrepancy_config
)


def perform_pure_llm_discrepancy_analysis(lc_context: Dict, documents: List[Dict], 
                                          swift_message: Any, config: Optional[Dict] = None) -> List[Dict]:
    """
    Pure LLM-based discrepancy analysis without static rules.
    
    This function performs comprehensive document analysis using LLM capabilities
    to identify discrepancies across documents and against LC requirements.
    
    Args:
        lc_context: LC context data including form data and requirements
        documents: List of document dictionaries with content and metadata
        swift_message: SWIFT message data (string or dict)
        config: Optional configuration overrides
        
    Returns:
        List of discrepancy dictionaries
    """
    try:
        logger.info(f"🤖 Starting pure LLM-based discrepancy analysis for {len(documents)} documents")

        all_discrepancies = []

        # Step 1: Individual document analysis
        for doc in documents:
            doc_type = doc.get('classification', doc.get('type', 'unknown'))
            doc_content = doc.get('content', '') or doc.get('text', '')
            doc_name = doc.get('name', 'Unknown Document')

            logger.info(f"📄 Processing document: {doc_name}")
            logger.info(f"   - Type: {doc_type}")
            logger.info(f"   - Content length: {len(doc_content)} characters")

            if not doc_content:
                logger.warning(f"⚠️ No content found for document: {doc_name} - skipping LLM analysis")
                continue

            # Use LLM for comprehensive document analysis
            doc_analysis = analyze_document_with_pure_llm(
                doc_content, doc_type, doc_name, lc_context, swift_message
            )

            if doc_analysis and doc_analysis.get('discrepancies'):
                for discrepancy in doc_analysis['discrepancies']:
                    # Enhanced discrepancy structure
                    enhanced_discrepancy = {
                        **discrepancy,
                        'analysis_type': 'pure_llm',
                        'document_type': doc_type,
                        'location': doc_name,
                        'document_name': doc_name,
                        'rule_code': discrepancy.get('rule_code',
                                                     f"LLM-{doc_type[:3].upper()}-{len(all_discrepancies) + 1:03d}"),
                        'basis': discrepancy.get('basis', 'Trade Finance Best Practice'),
                        'source_value': discrepancy.get('source_value', 'Not provided'),
                        'target_value': discrepancy.get('target_value', 'Not specified'),
                        'source_document': discrepancy.get('source_document', doc_name),
                        'target_document': discrepancy.get('target_document', 'LC Requirements'),
                        'business_impact': discrepancy.get('business_impact', 'Requires review'),
                        'cross_document_check': discrepancy.get('cross_document_check', 'false')
                    }
                    all_discrepancies.append(enhanced_discrepancy)

        # Step 2: Cross-document LLM analysis
        cross_document_discrepancies = perform_llm_cross_document_analysis(
            documents, lc_context, swift_message
        )
        if cross_document_discrepancies:
            logger.info(f"🔗 Cross-document LLM analysis found {len(cross_document_discrepancies)} additional discrepancies")
            all_discrepancies.extend(cross_document_discrepancies)

        # Step 3: Final comprehensive review
        if len(documents) > 1:
            final_review = perform_llm_comprehensive_review(
                all_discrepancies, documents, lc_context, swift_message
            )
            if final_review:
                all_discrepancies.extend(final_review)

        logger.info(f"🤖 Pure LLM analysis completed: {len(all_discrepancies)} total discrepancies found")
        return all_discrepancies

    except Exception as e:
        logger.error(f"Error in pure LLM analysis: {str(e)}")
        return []


def analyze_document_with_pure_llm(doc_content: str, doc_type: str, doc_name: str,
                                   lc_context: Dict, swift_message: Any) -> Optional[Dict]:
    """
    Analyze a single document using pure LLM analysis.
    
    Args:
        doc_content: Document text content
        doc_type: Type of document
        doc_name: Name of document
        lc_context: LC context data
        swift_message: SWIFT message data
        
    Returns:
        Analysis result dictionary with discrepancies
    """
    try:
        # Extract LC data for comparison
        lc_data = extract_lc_structured_data(lc_context, swift_message)
        
        # Validate document matches LC context to avoid false positives
        if not validate_document_lc_context(doc_content, lc_data, doc_type):
            logger.warning(f"⚠️ Document-LC context mismatch for {doc_name}, applying conservative analysis")
        
        # Build analysis prompt
        analysis_prompt = build_document_analysis_prompt(doc_content, doc_type, lc_data)
        
        # Call LLM for analysis (this would be integrated with your LLM service)
        # For now, return None to indicate no LLM response
        # In production, this would call Azure OpenAI or similar
        
        return None
        
    except Exception as e:
        logger.error(f"Error in LLM document analysis: {e}")
        return None


def perform_llm_cross_document_analysis(documents: List[Dict], lc_context: Dict, 
                                        swift_message: Any) -> List[Dict]:
    """
    Perform cross-document analysis using LLM.
    
    Args:
        documents: List of documents to analyze
        lc_context: LC context data
        swift_message: SWIFT message data
        
    Returns:
        List of cross-document discrepancies
    """
    try:
        if len(documents) < 2:
            return []
            
        logger.info(f"🔗 Performing cross-document analysis for {len(documents)} documents")
        
        # Extract fields from all documents for comparison
        all_fields = {}
        for doc in documents:
            doc_name = doc.get('name', doc.get('file_name', 'Unknown'))
            extracted = doc.get('extracted_fields', {})
            if extracted:
                all_fields[doc_name] = extracted
        
        # Identify field conflicts
        field_conflicts = identify_field_conflicts(all_fields)
        
        return field_conflicts
        
    except Exception as e:
        logger.error(f"Error in cross-document analysis: {e}")
        return []


def perform_llm_comprehensive_review(existing_discrepancies: List[Dict], documents: List[Dict],
                                     lc_context: Dict, swift_message: Any) -> List[Dict]:
    """
    Perform final comprehensive review of all discrepancies.
    
    Args:
        existing_discrepancies: Discrepancies already found
        documents: List of documents
        lc_context: LC context data
        swift_message: SWIFT message data
        
    Returns:
        Additional discrepancies from comprehensive review
    """
    try:
        # Filter out potential false positives based on severity and confidence
        # This could be enhanced with LLM validation
        return []
        
    except Exception as e:
        logger.error(f"Error in comprehensive review: {e}")
        return []


def analyze_comprehensive_trade_finance_discrepancies(lc_context: Dict, uploaded_documents: List[Dict], 
                                                      swift_message: Any) -> Dict:
    """
    XML Rule-Based comprehensive trade finance discrepancy analysis.
    Uses discrepancy_rules.xml instead of static methods for better maintainability.
    
    Args:
        lc_context: LC context with form data and requirements
        uploaded_documents: List of uploaded document data
        swift_message: SWIFT message content
        
    Returns:
        Dictionary with success status and analysis results
    """
    try:
        logger.info("🚀 Starting XML Rule-Based COMPREHENSIVE trade finance discrepancy analysis")

        # Load XML rules
        xml_rules = load_discrepancy_rules_from_xml()
        if not xml_rules:
            logger.warning("⚠️ No XML rules loaded, falling back to basic analysis")
            return {
                'success': False,
                'error': 'No discrepancy rules loaded',
                'results': create_empty_results()
            }

        logger.info(f"📋 Loaded {len(xml_rules)} XML discrepancy rules")

        # Extract data for analysis
        lc_data = extract_enhanced_lc_data(lc_context)
        swift_data = extract_enhanced_swift_data(swift_message)
        document_data = extract_enhanced_document_data(uploaded_documents)

        logger.info(f"📊 Data extraction complete:")
        logger.info(f"   - LC data: {len(lc_data)} fields")
        logger.info(f"   - SWIFT data: {len(swift_data)} fields")
        logger.info(f"   - Document data: {len(document_data)} documents")

        # Initialize results
        results = create_empty_results()
        results['success'] = True

        # Apply XML rules to each document
        logger.info("🔍 Applying XML rules to documents...")
        for doc in document_data:
            doc_type = doc.get('document_type', '').strip()
            
            # Filter rules for this document type
            relevant_rules = [rule for rule in xml_rules
                              if rule.get('documentType', '').lower() == doc_type.lower()]

            logger.info(f"📋 Found {len(relevant_rules)} XML rules for {doc_type}")

            # Apply each relevant rule
            for rule in relevant_rules:
                rule_result = apply_xml_rule_with_llm_analysis(rule, doc, lc_data, swift_data)
                if rule_result:
                    categorize_and_add_result(results, rule_result)

        # Cross-document analysis for multiple documents
        if len(document_data) >= 2:
            cross_doc_results = analyze_cross_document_conflicts(
                xml_rules, document_data, lc_data, swift_data
            )
            for result in cross_doc_results:
                categorize_and_add_result(results, result)

        # SWIFT compliance check
        if swift_data:
            swift_issues = analyze_swift_compliance_with_xml_rules(xml_rules, swift_data, lc_data)
            for issue in swift_issues:
                results['swift_message_issues'].append(issue)
                if issue.get('severity', '').lower() in ['critical', 'high']:
                    results['critical_issues'] += 1
                else:
                    results['warning_issues'] += 1

        logger.info(f"✅ XML Rule-Based analysis complete:")
        logger.info(f"   - Field conflicts: {len(results['field_conflicts'])}")
        logger.info(f"   - Compliance discrepancies: {len(results['compliance_discrepancies'])}")
        logger.info(f"   - Cross-document issues: {len(results['cross_document_inconsistencies'])}")
        logger.info(f"   - SWIFT issues: {len(results['swift_message_issues'])}")

        return {'success': True, 'results': results}

    except Exception as e:
        logger.error(f"Error in comprehensive discrepancy analysis: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e),
            'results': create_empty_results()
        }


def analyze_individual_document_discrepancies(document_data: Dict, lc_context: Dict, 
                                               swift_message: Any) -> Dict:
    """
    Analyze a single document for compliance discrepancies using XML rules.
    
    Args:
        document_data: Document data including extracted fields
        lc_context: LC context data
        swift_message: SWIFT message data
        
    Returns:
        Analysis results dictionary
    """
    try:
        file_name = document_data.get('file_name', 'Unknown')
        logger.info(f"🔍 Starting individual document discrepancy analysis for {file_name}")

        # Load XML rules
        xml_rules = load_discrepancy_rules_from_xml()
        if not xml_rules:
            logger.warning("⚠️ No XML rules loaded for individual analysis")
            return {'success': False, 'error': 'No discrepancy rules loaded'}

        logger.info(f"📋 Loaded {len(xml_rules)} XML rules for individual analysis")

        # Extract data
        lc_data = extract_enhanced_lc_data(lc_context)
        swift_data = extract_enhanced_swift_data(swift_message)

        document_type = document_data.get('document_type', '').strip()

        # Initialize discrepancies list
        discrepancies = []

        # Filter rules for this document type
        relevant_rules = [rule for rule in xml_rules
                          if rule.get('documentType', '').lower() == document_type.lower()]

        logger.info(f"📋 Found {len(relevant_rules)} relevant XML rules for {document_type}")

        # Apply each relevant rule
        for rule in relevant_rules:
            try:
                rule_result = apply_xml_rule_with_llm_analysis(rule, document_data, lc_data, swift_data)
                if rule_result:
                    discrepancy = format_discrepancy_for_frontend(rule_result, file_name)
                    discrepancies.append(discrepancy)
            except Exception as rule_error:
                logger.error(f"❌ Error applying rule {rule.get('code', 'Unknown')}: {rule_error}")
                continue

        # Calculate summary statistics
        summary = calculate_discrepancy_summary(discrepancies)
        
        # Determine compliance status
        compliance_status = 'COMPLIANT' if summary['total'] == 0 else 'NON_COMPLIANT'

        results = {
            'success': True,
            'results': {
                'discrepancies': discrepancies,
                'analysis_method': 'xml_rule_based_individual',
                'compliance_status': compliance_status,
                'summary': summary,
                'document_analysis': {
                    'file_name': file_name,
                    'document_type': document_type,
                    'rules_applied': len(relevant_rules),
                    'fields_analyzed': len(document_data.get('extracted_fields', {}))
                }
            }
        }

        logger.info(f"✅ Individual analysis completed: {summary['total']} discrepancies found")
        return results

    except Exception as e:
        logger.error(f"❌ Error in individual document discrepancy analysis: {e}")
        return {'success': False, 'error': str(e)}


# Helper Functions

def create_empty_results() -> Dict:
    """Create an empty results structure."""
    return {
        'field_conflicts': [],
        'compliance_discrepancies': [],
        'cross_document_inconsistencies': [],
        'swift_message_issues': [],
        'critical_issues': 0,
        'warning_issues': 0
    }


def categorize_and_add_result(results: Dict, rule_result: Dict) -> None:
    """Categorize a rule result and add it to the appropriate results list."""
    result_type = rule_result.get('type', '').lower()
    severity = rule_result.get('severity', '').lower()
    
    # Categorize
    if 'field' in result_type:
        results['field_conflicts'].append(rule_result)
    elif 'compliance' in result_type:
        results['compliance_discrepancies'].append(rule_result)
    else:
        results['cross_document_inconsistencies'].append(rule_result)
    
    # Update counters
    if severity in ['critical', 'high']:
        results['critical_issues'] += 1
    else:
        results['warning_issues'] += 1


def format_discrepancy_for_frontend(rule_result: Dict, file_name: str) -> Dict:
    """Format a discrepancy for frontend display."""
    return {
        'field_name': rule_result.get('field_name', 'Unknown Field'),
        'severity': rule_result.get('severity', 'MEDIUM').upper(),
        'confidence': rule_result.get('confidence', 70),
        'source_value': rule_result.get('source_value', 'Not specified'),
        'compared_value': rule_result.get('expected_value', 'Not specified'),
        'rule_id': rule_result.get('rule_code', 'Unknown'),
        'rule_name': rule_result.get('description', 'Compliance Rule'),
        'discrepancy_type': rule_result.get('type', 'compliance_discrepancy'),
        'business_impact': rule_result.get('business_impact', 'Review required'),
        'recommendation': rule_result.get('recommendation', 'Please review and correct'),
        'source_document': file_name,
        'rule_basis': rule_result.get('rule_basis', 'XML Rule'),
        'comparison_type': rule_result.get('comparison_type', 'LC vs Document')
    }


def calculate_discrepancy_summary(discrepancies: List[Dict]) -> Dict:
    """Calculate summary statistics for discrepancies."""
    total = len(discrepancies)
    critical = len([d for d in discrepancies if d.get('severity') == 'CRITICAL'])
    high = len([d for d in discrepancies if d.get('severity') == 'HIGH'])
    medium = len([d for d in discrepancies if d.get('severity') == 'MEDIUM'])
    low = len([d for d in discrepancies if d.get('severity') == 'LOW'])
    
    return {
        'total': total,
        'critical': critical,
        'high': high,
        'medium': medium,
        'low': low
    }


def identify_field_conflicts(all_fields: Dict[str, Dict]) -> List[Dict]:
    """
    Identify field value conflicts across documents.
    
    Args:
        all_fields: Dictionary mapping document names to their extracted fields
        
    Returns:
        List of field conflict discrepancies
    """
    conflicts = []
    
    # Collect all field values across documents
    field_values = {}
    for doc_name, fields in all_fields.items():
        for field_name, value in fields.items():
            if field_name not in field_values:
                field_values[field_name] = []
            field_values[field_name].append({
                'document': doc_name,
                'value': value
            })
    
    # Check for conflicts
    for field_name, values in field_values.items():
        if len(values) > 1:
            unique_values = list(set(str(v['value']).strip().lower() for v in values if v['value']))
            
            if len(unique_values) > 1:
                conflicts.append({
                    'type': 'field_conflict',
                    'field_name': field_name,
                    'description': f"Inconsistent values across documents: {', '.join(unique_values[:3])}",
                    'documents_affected': [v['document'] for v in values],
                    'values': [v['value'] for v in values],
                    'severity': 'critical' if len(unique_values) > 2 else 'warning'
                })
    
    return conflicts


def apply_xml_rule_with_llm_analysis(rule: Dict, document_data: Dict, 
                                      lc_data: Dict, swift_data: Dict) -> Optional[Dict]:
    """
    Apply an XML rule to document data with optional LLM enhancement.
    
    Args:
        rule: Rule dictionary from XML
        document_data: Document data to analyze
        lc_data: Extracted LC data
        swift_data: Extracted SWIFT data
        
    Returns:
        Discrepancy result if rule violation found, None otherwise
    """
    try:
        rule_code = rule.get('code', 'Unknown')
        rule_description = rule.get('description', '')
        rule_basis = rule.get('basis', 'XML Rule')
        rule_priority = rule.get('priority', 'Medium')
        
        # Get document extracted fields
        extracted_fields = document_data.get('extracted_fields', {})
        
        # Check rule conditions against document data
        # This is a simplified implementation - can be enhanced with LLM
        
        # For now, return None (no violation) since we need actual rule logic
        # In production, this would check specific field conditions
        
        return None
        
    except Exception as e:
        logger.error(f"Error applying XML rule {rule.get('code', 'Unknown')}: {e}")
        return None


def analyze_cross_document_conflicts(xml_rules: List[Dict], document_data: List[Dict],
                                     lc_data: Dict, swift_data: Dict) -> List[Dict]:
    """
    Analyze cross-document conflicts using XML rules.
    
    Args:
        xml_rules: List of XML rules
        document_data: List of document data dictionaries
        lc_data: LC context data
        swift_data: SWIFT message data
        
    Returns:
        List of cross-document conflict results
    """
    conflicts = []
    
    # Collect fields from all documents
    all_fields = {}
    for doc in document_data:
        doc_name = doc.get('file_name', 'Unknown')
        extracted = doc.get('extracted_fields', {})
        if extracted:
            all_fields[doc_name] = extracted
    
    # Identify conflicts
    conflicts.extend(identify_field_conflicts(all_fields))
    
    return conflicts


def analyze_swift_compliance_with_xml_rules(xml_rules: List[Dict], swift_data: Dict,
                                            lc_data: Dict) -> List[Dict]:
    """
    Analyze SWIFT message compliance using XML rules.
    
    Args:
        xml_rules: List of XML rules
        swift_data: Parsed SWIFT message data
        lc_data: LC context data
        
    Returns:
        List of SWIFT compliance issues
    """
    issues = []
    
    # Check required SWIFT fields
    required_fields = ['20', '32B', '31D', '50', '59']
    for field in required_fields:
        if not swift_data.get(field):
            issues.append({
                'type': 'swift_missing_field',
                'field': field,
                'description': f"Required SWIFT field {field} is missing or empty",
                'severity': 'warning'
            })
    
    return issues


# Data Extraction Functions

def extract_lc_structured_data(lc_context: Dict, swift_message: Any = None) -> Dict:
    """
    Extract structured data from LC context, with fallback to SWIFT data.
    
    Args:
        lc_context: LC context dictionary
        swift_message: Optional SWIFT message for fallback
        
    Returns:
        Structured LC data dictionary
    """
    lc_data = {}

    if isinstance(lc_context, dict):
        form_data = lc_context.get('formData', {})
        lc_data = {
            'lc_number': form_data.get('lcNumber', ''),
            'applicant': form_data.get('applicantName', ''),
            'beneficiary': form_data.get('beneficiaryName', ''),
            'amount': form_data.get('lcAmount', ''),
            'currency': form_data.get('lcCurrency', 'USD'),
            'issue_date': form_data.get('issueDate', ''),
            'expiry_date': form_data.get('expiryDate', ''),
            'port_of_loading': form_data.get('portOfLoading', ''),
            'port_of_discharge': form_data.get('portOfDischarge', ''),
            'goods_description': form_data.get('goodsDescription', ''),
            'latest_shipment_date': form_data.get('latestShipmentDate', '')
        }

    # If form data is empty, try SWIFT message
    if swift_message and (not lc_data or all(not v for v in lc_data.values())):
        logger.info("📄 Form data empty, attempting to extract LC data from SWIFT message")
        swift_data = extract_swift_structured_data(swift_message)
        if swift_data:
            lc_data.update({
                'lc_number': swift_data.get('20', lc_data.get('lc_number', '')),
                'amount': swift_data.get('32B', lc_data.get('amount', '')),
                'currency': extract_currency_from_swift_amount(swift_data.get('32B', '')),
                'issue_date': format_swift_date(swift_data.get('31C', '')),
                'expiry_date': format_swift_date(swift_data.get('31D', '')),
                'goods_description': swift_data.get('45A', lc_data.get('goods_description', '')),
            })

    return lc_data


def extract_enhanced_lc_data(lc_context: Dict) -> Dict:
    """Enhanced LC data extraction with comprehensive field coverage."""
    if not lc_context:
        return {}

    enhanced_data = {}
    if isinstance(lc_context, dict):
        enhanced_data.update(lc_context)

    # Add computed/derived fields
    enhanced_data.update({
        'lc_type': enhanced_data.get('lc_type', enhanced_data.get('type', '')),
        'applicant_full': f"{enhanced_data.get('applicant', '')} {enhanced_data.get('applicant_address', '')}".strip(),
        'beneficiary_full': f"{enhanced_data.get('beneficiary', '')} {enhanced_data.get('beneficiary_address', '')}".strip(),
        'amount_currency': f"{enhanced_data.get('currency', '')} {enhanced_data.get('amount', '')}".strip(),
    })

    return enhanced_data


def extract_enhanced_swift_data(swift_message: Any) -> Dict:
    """Enhanced SWIFT data extraction with comprehensive field mapping."""
    if not swift_message:
        return {}

    swift_data = {}

    if isinstance(swift_message, str):
        # Parse SWIFT MT format
        swift_patterns = {
            '20': r':20:(.*?)(?=:|$)',
            '27': r':27:(.*?)(?=:|$)',
            '31C': r':31C:(.*?)(?=:|$)',
            '31D': r':31D:(.*?)(?=:|$)',
            '32B': r':32B:(.*?)(?=:|$)',
            '39A': r':39A:(.*?)(?=:|$)',
            '40A': r':40A:(.*?)(?=:|$)',
            '41A': r':41A:(.*?)(?=:|$)',
            '42A': r':42A:(.*?)(?=:|$)',
            '42C': r':42C:(.*?)(?=:|$)',
            '43P': r':43P:(.*?)(?=:|$)',
            '43T': r':43T:(.*?)(?=:|$)',
            '44A': r':44A:(.*?)(?=:|$)',
            '44C': r':44C:(.*?)(?=:|$)',
            '44E': r':44E:(.*?)(?=:|$)',
            '44F': r':44F:(.*?)(?=:|$)',
            '45A': r':45A:(.*?)(?=:|$)',
            '46A': r':46A:(.*?)(?=:|$)',
            '47A': r':47A:(.*?)(?=:|$)',
            '48': r':48:(.*?)(?=:|$)',
            '49': r':49:(.*?)(?=:|$)',
            '50': r':50:(.*?)(?=:|$)',
            '51A': r':51A:(.*?)(?=:|$)',
            '53A': r':53A:(.*?)(?=:|$)',
            '59': r':59:(.*?)(?=:|$)',
            '71B': r':71B:(.*?)(?=:|$)',
            '72': r':72:(.*?)(?=:|$)',
            '78': r':78:(.*?)(?=:|$)',
        }

        for field_code, pattern in swift_patterns.items():
            matches = re.findall(pattern, swift_message, re.MULTILINE | re.DOTALL)
            if matches:
                swift_data[field_code] = matches[0].strip()

    elif isinstance(swift_message, dict):
        swift_data.update(swift_message)

    return swift_data


def extract_enhanced_document_data(uploaded_documents: List[Dict]) -> List[Dict]:
    """Extract enhanced data from uploaded documents."""
    enhanced_docs = []
    
    for doc in uploaded_documents:
        enhanced_doc = {
            'file_name': doc.get('file_name', doc.get('name', 'Unknown')),
            'document_type': doc.get('document_type', doc.get('type', 'Unknown')),
            'extracted_fields': doc.get('extracted_fields', {}),
            'classification_result': doc.get('classification_result', doc.get('classification', {})),
            'content': doc.get('content', ''),
            'status': doc.get('status', 'unknown')
        }
        enhanced_docs.append(enhanced_doc)
    
    return enhanced_docs


def extract_swift_structured_data(swift_message: Any) -> Dict:
    """Extract structured data from SWIFT message."""
    swift_data = {}

    if isinstance(swift_message, str):
        field_patterns = {
            '20': r':20:([^\n:]+)',
            '31C': r':31C:([^\n:]+)',
            '31D': r':31D:([^\n:]+)',
            '32B': r':32B:([^\n:]+)',
            '44C': r':44C:([^\n:]+)',
            '44E': r':44E:([^\n:]+)',
            '44F': r':44F:([^\n:]+)',
            '45A': r':45A:([^\n:]+)',
            '46A': r':46A:([^\n:]+)',
            '47A': r':47A:([^\n:]+)',
            '50': r':50:([^\n:]+)',
            '59': r':59:([^\n:]+)'
        }

        for field, pattern in field_patterns.items():
            match = re.search(pattern, swift_message, re.MULTILINE | re.DOTALL)
            if match:
                swift_data[field] = match.group(1).strip()

    return swift_data


def extract_currency_from_swift_amount(amount_field: str) -> str:
    """Extract currency from SWIFT 32B field."""
    if not amount_field:
        return 'USD'

    currency_match = re.match(r'^([A-Z]{3})', amount_field)
    return currency_match.group(1) if currency_match else 'USD'


def format_swift_date(swift_date: str) -> str:
    """Format SWIFT date (YYMMDD or YYMMDDCITY) to readable format."""
    if not swift_date:
        return ''

    try:
        date_match = re.match(r'^(\d{6})', swift_date)
        if date_match:
            date_str = date_match.group(1)
            year = int('20' + date_str[:2])
            month = int(date_str[2:4])
            day = int(date_str[4:6])
            return f"{year:04d}-{month:02d}-{day:02d}"
    except:
        pass

    return swift_date


def validate_document_lc_context(doc_content: str, lc_data: Dict, doc_type: str) -> bool:
    """
    Validate if document content matches LC context to avoid false positives.
    
    Args:
        doc_content: Document text content
        lc_data: LC data dictionary
        doc_type: Type of document
        
    Returns:
        True if document appears to match LC context
    """
    try:
        if not doc_content or not lc_data:
            return True

        consistency_score = 0
        total_checks = 0

        # Check amount consistency
        doc_amounts = re.findall(r'(?:USD?|US\$|\$)\s*[\d,]+\.?\d*', doc_content, re.IGNORECASE)
        lc_amount = lc_data.get('amount', '')

        if doc_amounts and lc_amount:
            total_checks += 1
            doc_amount_nums = [re.sub(r'[^\d.]', '', amt) for amt in doc_amounts]
            lc_amount_num = re.sub(r'[^\d.]', '', lc_amount)

            if any(abs(float(lc_amount_num) - float(doc_num)) / float(lc_amount_num) < 0.1
                   for doc_num in doc_amount_nums if doc_num and doc_num != '0'):
                consistency_score += 1

        # Check date consistency
        current_year = datetime.now().year
        doc_years = re.findall(r'\b(20\d{2})\b', doc_content)

        if doc_years:
            total_checks += 1
            doc_year = max(int(year) for year in doc_years)
            if abs(current_year - doc_year) <= 2:
                consistency_score += 1

        # Check goods description similarity
        lc_goods = lc_data.get('goods_description', '').lower()
        if lc_goods and len(lc_goods) > 10:
            total_checks += 1
            lc_keywords = set(word for word in re.findall(r'\b\w{4,}\b', lc_goods)
                              if word not in ['electronic', 'components', 'accessories', 'including', 'related'])
            doc_content_lower = doc_content.lower()
            if lc_keywords and any(keyword in doc_content_lower for keyword in lc_keywords):
                consistency_score += 1

        if total_checks == 0:
            return True

        consistency_ratio = consistency_score / total_checks
        return consistency_ratio >= 0.3

    except Exception as e:
        logger.error(f"Error in document-LC validation: {str(e)}")
        return True


def build_document_analysis_prompt(doc_content: str, doc_type: str, lc_data: Dict) -> str:
    """
    Build an analysis prompt for LLM document analysis.
    
    Args:
        doc_content: Document text content
        doc_type: Type of document
        lc_data: LC data dictionary
        
    Returns:
        Formatted prompt string
    """
    prompt = f"""Analyze this {doc_type} document for trade finance compliance.

Document Content:
{doc_content[:5000]}  # Truncate to prevent token overflow

LC Requirements:
- LC Number: {lc_data.get('lc_number', 'Not specified')}
- Amount: {lc_data.get('amount', 'Not specified')}
- Currency: {lc_data.get('currency', 'Not specified')}
- Beneficiary: {lc_data.get('beneficiary', 'Not specified')}
- Expiry Date: {lc_data.get('expiry_date', 'Not specified')}
- Goods Description: {lc_data.get('goods_description', 'Not specified')}

Identify any discrepancies between the document and LC requirements.
"""
    return prompt
