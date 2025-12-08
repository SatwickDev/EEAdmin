"""
Guarantee Vetting Rules Helper Functions

This module contains helper functions for loading and saving guarantee vetting rules.
"""

import os
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def load_guarantee_vetting_rules():
    """Load guarantee vetting rules from both whitelist and blacklist JSON files"""
    all_rules = []
    
    # Get the app directory path
    app_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # Load whitelist rules from root data folder
    whitelist_filepath = os.path.join(app_dir, '..', 'data', 'whitelist_vetting_rules.json')
    try:
        if os.path.exists(whitelist_filepath):
            with open(whitelist_filepath, 'r', encoding='utf-8') as f:
                whitelist_data = json.load(f)
                whitelist_rules = whitelist_data.get('whitelist_rules', [])
                # Map fields to match frontend expectations
                for rule in whitelist_rules:
                    rule['rule_type'] = 'whitelist'
                    rule['rule_name'] = rule.get('description', '')
                    rule['rule_ref'] = rule.get('id', '')
                    rule['severity'] = rule.get('priority', 'medium').title()
                    rule['basics'] = rule.get('category', 'custom').lower().replace(' ', '_')
                    rule['detection_hint'] = rule.get('rule', '')
                    rule['why_onerous_or_no_urdg'] = rule.get('compliance_requirement', '')
                    rule['suggested_wording'] = f"Approved: {rule.get('rule', '')}"
                all_rules.extend(whitelist_rules)
                logger.info(f"Loaded {len(whitelist_rules)} whitelist rules")
        else:
            logger.warning(f"Whitelist file not found: {whitelist_filepath}")
    except Exception as e:
        logger.error(f"Error loading whitelist rules: {e}")

    # Load blacklist rules from root data folder
    blacklist_filepath = os.path.join(app_dir, '..', 'data', 'blacklist_vetting_rules.json')
    try:
        if os.path.exists(blacklist_filepath):
            with open(blacklist_filepath, 'r', encoding='utf-8') as f:
                blacklist_data = json.load(f)
                blacklist_rules = blacklist_data.get('blacklist_rules', [])
                # Map fields to match frontend expectations
                for rule in blacklist_rules:
                    rule['rule_type'] = 'blacklist'
                    rule['rule_name'] = rule.get('description', '')
                    rule['rule_ref'] = rule.get('id', '')
                    rule['severity'] = rule.get('priority', 'medium').title()
                    rule['basics'] = rule.get('category', 'custom').lower().replace(' ', '_')
                    rule['detection_hint'] = rule.get('rule', '')
                    rule['why_onerous_or_no_urdg'] = rule.get('compliance_requirement', '')
                    rule['suggested_wording'] = f"Action: {rule.get('action', 'review')}"
                all_rules.extend(blacklist_rules)
                logger.info(f"Loaded {len(blacklist_rules)} blacklist rules")
        else:
            logger.warning(f"Blacklist file not found: {blacklist_filepath}")
    except Exception as e:
        logger.error(f"Error loading blacklist rules: {e}")

    # Return combined data
    return {
        'rules': all_rules,
        'metadata': {
            'version': '1.0',
            'last_updated': datetime.utcnow().strftime('%Y-%m-%d'),
            'description': 'Combined guarantee vetting rules (whitelist and blacklist)',
            'total_rules': len(all_rules),
            'whitelist_count': len([r for r in all_rules if r.get('rule_type') == 'whitelist']),
            'blacklist_count': len([r for r in all_rules if r.get('rule_type') == 'blacklist'])
        }
    }


def save_guarantee_vetting_rules(data):
    """Save guarantee vetting rules to JSON file"""
    # Get the app directory path
    app_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    filepath = os.path.join(app_dir, '..', 'data', 'guarantee_vetting_rules.json')

    try:
        # Update metadata timestamp
        if 'metadata' not in data:
            data['metadata'] = {}
        data['metadata']['last_updated'] = datetime.utcnow().strftime('%Y-%m-%d')

        # Ensure directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Error saving guarantee vetting rules: {e}")
        return False


def generate_enhanced_fallback_preview(rule_description, rule_type, sample_scenario=""):
    """Generate enhanced rule preview when OpenAI is unavailable"""

    # Enhanced examples based on common rule patterns
    enhanced_examples = {
        "beneficiary country not in central africa": {
            "explanation": "This blacklist rule flags transactions where the beneficiary is located in countries outside the approved Central Africa region.",
            "example_scenarios": [
                "Transaction flagged: Beneficiary bank in Morocco (North Africa) - outside Central Africa region",
                "Transaction flagged: Payment to beneficiary in Egypt - not part of Central Africa list",
                "Transaction approved: Beneficiary in Chad (Central Africa) - meets regional requirements"
            ],
            "detection_criteria": "Geographic location of beneficiary country compared to approved Central Africa list (Chad, CAR, Cameroon, etc.)",
            "recommended_action": "Verify beneficiary's actual registration country and confirm regional compliance requirements"
        },
        "guarantee issuing bank": {
            "explanation": "This rule evaluates the creditworthiness and approval status of banks issuing guarantees.",
            "example_scenarios": [
                "Bank with AA+ rating: Approved - meets minimum credit requirements",
                "Regional bank with B+ rating: Flagged - below minimum AA threshold",
                "Unknown bank rating: Flagged - requires credit assessment"
            ],
            "detection_criteria": "Bank credit rating (minimum AA), regulatory approval status, and institutional reputation",
            "recommended_action": "Verify bank's current credit rating and regulatory standing before approval"
        },
        "expiry date": {
            "explanation": "This rule ensures guarantee expiry dates meet regulatory and business requirements.",
            "example_scenarios": [
                "Expiry > 2 years: Flagged - exceeds standard guarantee period",
                "No expiry date specified: Flagged - indefinite guarantee not allowed",
                "Expiry in 18 months: Approved - within acceptable timeframe"
            ],
            "detection_criteria": "Guarantee duration limits, explicit expiry requirements, and risk management policies",
            "recommended_action": "Confirm expiry date aligns with underlying contract and risk appetite"
        }
    }

    # Find matching pattern or use generic template
    rule_key = rule_description.lower()
    matching_example = None

    for key, example in enhanced_examples.items():
        if key in rule_key:
            matching_example = example
            break

    if matching_example:
        if sample_scenario:
            custom_result = f"Analysis of '{sample_scenario}': {matching_example['example_scenarios'][0]}"
        else:
            custom_result = matching_example['example_scenarios'][0]

        return {
            'explanation': matching_example['explanation'],
            'example_result': custom_result,
            'example_scenarios': matching_example['example_scenarios'],
            'detection_criteria': matching_example['detection_criteria'],
            'recommended_action': matching_example['recommended_action']
        }
    else:
        # Generic fallback
        if sample_scenario:
            example_result = f"Based on your rule '{rule_description}', analyzing scenario: {sample_scenario}. The transaction would be evaluated against your specified criteria and flagged if non-compliant."
        else:
            example_result = f"This {rule_type} rule will automatically evaluate transactions against: {rule_description}. Non-compliant cases will be flagged for review."

        scenarios = [
            f"Transaction meets criteria: Approved - complies with {rule_description}",
            f"Transaction fails check: Flagged - violates {rule_description} requirements",
            f"Unclear case: Manual review needed - requires human assessment"
        ]

        return {
            'explanation': f'This {rule_type} rule automatically monitors transactions for: {rule_description}',
            'example_result': example_result,
            'example_scenarios': scenarios,
            'detection_criteria': f'Key evaluation points: {rule_description}',
            'recommended_action': 'Review flagged transactions and confirm compliance with business policies'
        }


def generate_mock_analysis(sample_text, analysis_mode, include_whitelist, include_blacklist):
    """Generate a mock analysis result for preview purposes"""
    import re

    # Simple document type detection
    document_type = "Unknown Document"
    if "guarantee" in sample_text.lower():
        document_type = "Bank Guarantee"
    elif "standby" in sample_text.lower() or "sblc" in sample_text.lower():
        document_type = "Standby Letter of Credit"
    elif "letter of credit" in sample_text.lower():
        document_type = "Letter of Credit"

    # Extract amount if present
    amount_match = re.search(r'(USD|EUR|GBP)\s*([\d,]+\.?\d*)', sample_text, re.IGNORECASE)
    amount = amount_match.group(0) if amount_match else "Not specified"

    # Basic risk assessment
    risk_indicators = []
    risk_level = "low"

    if "sanctions" in sample_text.lower():
        risk_indicators.append("Sanctions-related content detected")
        risk_level = "high"

    if amount_match:
        amount_value = float(amount_match.group(2).replace(',', ''))
        if amount_value > 10000000:  # 10M
            risk_indicators.append("High value guarantee (>10M)")
            risk_level = "high"

    # Compliance assessment
    compliance_status = "compliant"
    compliance_issues = []

    if "urdg" not in sample_text.lower():
        compliance_issues.append("URDG 758 reference not found")
        compliance_status = "needs_review"

    # Mock analysis based on mode
    if analysis_mode == "detailed":
        findings = [
            f"Document identified as: {document_type}",
            f"Guarantee amount: {amount}",
            "URDG 758 compliance check performed",
            "Beneficiary and guarantor details reviewed",
            "Expiry date and claim conditions analyzed"
        ]
    elif analysis_mode == "compliance":
        findings = [
            "URDG 758 compliance verification completed",
            "Mandatory fields presence check performed",
            "Legal framework validation conducted"
        ]
    elif analysis_mode == "risk_assessment":
        findings = [
            "Country risk assessment performed",
            "Counterparty risk evaluation completed",
            "Operational risk factors identified"
        ]
    else:  # basic
        findings = [
            f"Document type: {document_type}",
            f"Amount: {amount}",
            "Basic compliance check completed"
        ]

    # Add rule-specific findings
    if include_whitelist:
        findings.append("Whitelist compliance verification performed")
    if include_blacklist:
        findings.append("Blacklist screening completed")

    return {
        "document_type": document_type,
        "compliance_status": compliance_status,
        "risk_level": risk_level,
        "key_findings": findings,
        "amount_detected": amount,
        "whitelist_compliance": "No violations found" if include_whitelist else "Not checked",
        "blacklist_violations": "None detected" if include_blacklist else "Not screened",
        "recommendations": [
            "Proceed with standard verification procedures",
            "Confirm beneficiary details",
            "Verify expiry date alignment with contract terms"
        ] if compliance_status == "compliant" else [
            "Address compliance issues before proceeding",
            "Consider additional due diligence",
            "Seek legal review if necessary"
        ],
        "confidence_score": 0.87,
        "analysis_timestamp": datetime.utcnow().isoformat() + 'Z',
        "rules_applied": {
            "whitelist_checked": include_whitelist,
            "blacklist_checked": include_blacklist,
            "analysis_mode": analysis_mode
        }
    }
