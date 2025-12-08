"""
Document Enhancement Service Module
====================================

This module provides document enhancement capabilities for discrepancy analysis,
including professional UI data formatting and document preparation.

Author: EEAdmin Team
Version: 1.0.0
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


def enhance_documents_for_discrepancy_analysis(documents: List[Dict], 
                                                lc_context: Dict = None,
                                                swift_message: Any = None) -> List[Dict]:
    """
    Enhance document data for discrepancy analysis.
    
    This function prepares documents with additional metadata and 
    normalized fields for consistent analysis.
    
    Args:
        documents: List of document dictionaries
        lc_context: Optional LC context data
        swift_message: Optional SWIFT message data
        
    Returns:
        List of enhanced document dictionaries
    """
    try:
        enhanced_documents = []
        
        for idx, doc in enumerate(documents):
            enhanced_doc = {
                # Basic document info
                'id': doc.get('id', f'doc_{idx}'),
                'file_name': doc.get('file_name', doc.get('name', f'Document_{idx}')),
                'document_type': normalize_document_type(doc.get('document_type', doc.get('type', 'Unknown'))),
                'status': doc.get('status', 'pending'),
                
                # Content
                'content': doc.get('content', ''),
                'content_length': len(doc.get('content', '')),
                
                # Extracted data
                'extracted_fields': doc.get('extracted_fields', {}),
                'fields_count': len(doc.get('extracted_fields', {})),
                
                # Classification
                'classification_result': doc.get('classification_result', doc.get('classification', {})),
                'classification_confidence': get_classification_confidence(doc),
                
                # OCR data
                'ocr_data': doc.get('ocr_data', {}),
                'has_ocr_data': bool(doc.get('ocr_data')),
                
                # Analysis metadata
                'analysis_timestamp': datetime.now().isoformat(),
                'analysis_version': '2.0',
                
                # Processing flags
                'ready_for_analysis': determine_readiness(doc),
                'needs_enhancement': not doc.get('extracted_fields')
            }
            
            # Add LC context reference if provided
            if lc_context:
                enhanced_doc['lc_reference'] = lc_context.get('formData', {}).get('lcNumber', '')
            
            enhanced_documents.append(enhanced_doc)
        
        logger.info(f"✅ Enhanced {len(enhanced_documents)} documents for discrepancy analysis")
        return enhanced_documents
        
    except Exception as e:
        logger.error(f"Error enhancing documents: {e}")
        return documents


def enhance_data_for_professional_ui(analysis_results: Dict, 
                                      documents: List[Dict] = None,
                                      lc_context: Dict = None) -> Dict:
    """
    Enhance analysis results for professional UI display.
    
    Formats discrepancy analysis results with additional metadata,
    categorization, and visual indicators for the frontend.
    
    Args:
        analysis_results: Raw analysis results dictionary
        documents: Optional list of analyzed documents
        lc_context: Optional LC context data
        
    Returns:
        Enhanced results formatted for professional UI
    """
    try:
        # Extract discrepancies from results
        discrepancies = analysis_results.get('discrepancies', [])
        if not discrepancies and 'results' in analysis_results:
            discrepancies = analysis_results['results'].get('discrepancies', [])
        
        # Enhance each discrepancy
        enhanced_discrepancies = []
        for idx, disc in enumerate(discrepancies):
            enhanced_disc = enhance_discrepancy_for_ui(disc, idx)
            enhanced_discrepancies.append(enhanced_disc)
        
        # Calculate summary statistics
        summary = calculate_ui_summary(enhanced_discrepancies)
        
        # Build enhanced response
        enhanced_results = {
            'success': analysis_results.get('success', True),
            'timestamp': datetime.now().isoformat(),
            'version': '2.0_professional_ui',
            
            # Enhanced discrepancies
            'discrepancies': enhanced_discrepancies,
            
            # Summary for UI display
            'summary': summary,
            
            # Visual indicators
            'status_indicator': determine_status_indicator(summary),
            'overall_score': calculate_overall_score(summary),
            
            # Document info
            'documents_analyzed': len(documents) if documents else 0,
            
            # LC reference
            'lc_reference': lc_context.get('formData', {}).get('lcNumber', '') if lc_context else '',
            
            # UI helpers
            'severity_colors': {
                'CRITICAL': '#dc3545',
                'HIGH': '#fd7e14',
                'MEDIUM': '#ffc107',
                'LOW': '#17a2b8'
            },
            
            # Compliance status
            'compliance_status': analysis_results.get('compliance_status', 
                                  'COMPLIANT' if not enhanced_discrepancies else 'NON_COMPLIANT')
        }
        
        logger.info(f"✅ Enhanced results for professional UI: {len(enhanced_discrepancies)} discrepancies")
        return enhanced_results
        
    except Exception as e:
        logger.error(f"Error enhancing data for UI: {e}")
        return analysis_results


def enhance_discrepancy_for_ui(discrepancy: Dict, index: int) -> Dict:
    """
    Enhance a single discrepancy entry for UI display.
    
    Args:
        discrepancy: Raw discrepancy dictionary
        index: Index position for ordering
        
    Returns:
        Enhanced discrepancy dictionary
    """
    severity = discrepancy.get('severity', 'MEDIUM').upper()
    
    return {
        # Original data
        **discrepancy,
        
        # UI identifiers
        'ui_id': f'disc_{index}',
        'display_order': index,
        
        # Normalized severity
        'severity': severity,
        'severity_level': get_severity_level(severity),
        'severity_icon': get_severity_icon(severity),
        
        # Display fields
        'display_title': build_display_title(discrepancy),
        'display_description': build_display_description(discrepancy),
        
        # Action items
        'action_required': severity in ['CRITICAL', 'HIGH'],
        'action_text': get_action_text(severity),
        
        # Visual
        'badge_color': get_badge_color(severity),
        'row_class': get_row_class(severity),
        
        # Timestamps
        'detected_at': datetime.now().isoformat()
    }


def calculate_ui_summary(discrepancies: List[Dict]) -> Dict:
    """Calculate summary statistics for UI display."""
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
        'low': low,
        'action_required': critical + high,
        'review_required': medium,
        'informational': low
    }


def calculate_overall_score(summary: Dict) -> int:
    """Calculate overall compliance score based on discrepancies."""
    total_issues = summary.get('total', 0)
    if total_issues == 0:
        return 100
    
    critical = summary.get('critical', 0)
    high = summary.get('high', 0)
    medium = summary.get('medium', 0)
    low = summary.get('low', 0)
    
    # Weighted deduction
    deduction = (critical * 25) + (high * 15) + (medium * 8) + (low * 3)
    return max(0, 100 - deduction)


def determine_status_indicator(summary: Dict) -> str:
    """Determine the status indicator for UI display."""
    critical = summary.get('critical', 0)
    high = summary.get('high', 0)
    
    if critical > 0:
        return 'error'
    elif high > 0:
        return 'warning'
    elif summary.get('total', 0) > 0:
        return 'info'
    return 'success'


def normalize_document_type(doc_type: str) -> str:
    """Normalize document type string."""
    if not doc_type:
        return 'Unknown'
    
    # Clean and standardize
    doc_type = doc_type.strip().lower()
    
    # Map common variations
    type_mapping = {
        'bl': 'Bill of Lading',
        'bill_of_lading': 'Bill of Lading',
        'billoflading': 'Bill of Lading',
        'awb': 'Air Waybill',
        'air_waybill': 'Air Waybill',
        'airwaybill': 'Air Waybill',
        'invoice': 'Commercial Invoice',
        'commercial_invoice': 'Commercial Invoice',
        'commercialinvoice': 'Commercial Invoice',
        'pl': 'Packing List',
        'packing_list': 'Packing List',
        'packinglist': 'Packing List',
        'lc': 'Letter of Credit',
        'letter_of_credit': 'Letter of Credit',
        'letterofcredit': 'Letter of Credit',
        'coo': 'Certificate of Origin',
        'certificate_of_origin': 'Certificate of Origin',
        'certificateoforigin': 'Certificate of Origin'
    }
    
    return type_mapping.get(doc_type, doc_type.title())


def get_classification_confidence(doc: Dict) -> float:
    """Extract classification confidence from document."""
    classification = doc.get('classification_result', doc.get('classification', {}))
    if isinstance(classification, dict):
        return classification.get('confidence', 0.0)
    return 0.0


def determine_readiness(doc: Dict) -> bool:
    """Determine if document is ready for analysis."""
    has_content = bool(doc.get('content'))
    has_fields = bool(doc.get('extracted_fields'))
    has_type = bool(doc.get('document_type', doc.get('type')))
    
    return has_content or has_fields and has_type


def get_severity_level(severity: str) -> int:
    """Convert severity to numeric level."""
    levels = {
        'CRITICAL': 4,
        'HIGH': 3,
        'MEDIUM': 2,
        'LOW': 1
    }
    return levels.get(severity.upper(), 2)


def get_severity_icon(severity: str) -> str:
    """Get icon class for severity."""
    icons = {
        'CRITICAL': 'fas fa-exclamation-circle',
        'HIGH': 'fas fa-exclamation-triangle',
        'MEDIUM': 'fas fa-info-circle',
        'LOW': 'fas fa-check-circle'
    }
    return icons.get(severity.upper(), 'fas fa-info-circle')


def get_badge_color(severity: str) -> str:
    """Get badge color for severity."""
    colors = {
        'CRITICAL': 'danger',
        'HIGH': 'warning',
        'MEDIUM': 'info',
        'LOW': 'secondary'
    }
    return colors.get(severity.upper(), 'info')


def get_row_class(severity: str) -> str:
    """Get table row class for severity."""
    classes = {
        'CRITICAL': 'table-danger',
        'HIGH': 'table-warning',
        'MEDIUM': 'table-info',
        'LOW': 'table-light'
    }
    return classes.get(severity.upper(), '')


def get_action_text(severity: str) -> str:
    """Get action text based on severity."""
    actions = {
        'CRITICAL': 'Immediate action required',
        'HIGH': 'Action required before processing',
        'MEDIUM': 'Review recommended',
        'LOW': 'For information only'
    }
    return actions.get(severity.upper(), 'Review recommended')


def build_display_title(discrepancy: Dict) -> str:
    """Build display title for discrepancy."""
    field = discrepancy.get('field_name', discrepancy.get('field', 'Unknown'))
    disc_type = discrepancy.get('discrepancy_type', discrepancy.get('type', 'Discrepancy'))
    
    return f"{field}: {disc_type.replace('_', ' ').title()}"


def build_display_description(discrepancy: Dict) -> str:
    """Build display description for discrepancy."""
    description = discrepancy.get('description', '')
    if description:
        return description
    
    source = discrepancy.get('source_value', 'N/A')
    expected = discrepancy.get('compared_value', discrepancy.get('expected_value', 'N/A'))
    
    return f"Found: {source}, Expected: {expected}"
