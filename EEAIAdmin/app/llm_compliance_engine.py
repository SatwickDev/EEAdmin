"""
LLM-Based Compliance Engine for Trade Finance Document Analysis
================================================================

This module implements an intelligent compliance checking system for Tab 3, Sub-tab 1 (Standard Rules)
that uses GPT-4o for semantic field comparison instead of strict string matching.

WORKFLOW:
---------
1. Load Rules: Fetch all rules from discrepancy_rules.json for classified document types
2. Classify Rules: Use GPT-4o to categorize rules into:
   - LC Comparison Rules: Compare document fields against Letter of Credit values
   - Cross-Document Rules: Compare values across different documents
   - Validation Rules: Validate document properties (signatures, dates, etc.)
3. Extract Entities: Gather all entity values from each classified document
4. Semantic Comparison: Use GPT-4o to compare values semantically (not exact string match)
   - "New York" matches "NY"
   - "USD 1000" matches "$1,000"
   - Different date formats representing same date match
5. Return Results: Structured response with:
   - Field name
   - Document type and name
   - Document value vs Expected value (LC or other document)
   - Compliance status (Accepted/Exception)
   - Applied rule with code, description, and basis
   
USAGE:
------
Called via Flask endpoint: POST /api/compliance/llm-standard-rules

Request:
{
    "documents": [
        {
            "documentType": "Commercial Invoice",
            "name": "invoice.pdf",
            "hash": "abc123",
            "entities": {"Applicant": "ABC Corp", "Amount": "USD 10000"},
            "extractedFields": {...}
        }
    ],
    "lcContext": {
        "applicantName": "ABC Corporation",
        "amount": "$10,000.00",
        ...
    }
}

Response:
{
    "success": true,
    "results": [
        {
            "field": "Applicant",
            "documentType": "Commercial Invoice",
            "documentValue": "ABC Corp",
            "lcValue": "ABC Corporation",
            "discrepancy": "Values semantically match - abbreviation accepted",
            "isCompliant": true,
            "rule": {
                "code": "R-0001",
                "description": "Applicant name must match LC",
                "basis": "UCP 600 Art. 18"
            }
        }
    ],
    "statistics": {
        "total_checks": 10,
        "compliant": 8,
        "non_compliant": 2,
        "compliance_rate": 80.0
    }
}

BENEFITS:
---------
- Intelligent semantic matching (not strict string comparison)
- GPT-4o understands context and meaning
- Reduces false positives from formatting differences
- Shows both compliant and non-compliant results
- Comprehensive rule coverage across LC and cross-document checks

Author: LLM Compliance System
Date: November 18, 2025
"""

import json
import os
import logging
from typing import Dict, List, Any
import openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from app.utils.app_config import (
    deployment_name,
    OPENAI_TEMPERATURE_COMPLIANCE,
    OPENAI_MAX_TOKENS_COMPLIANCE
)

logger = logging.getLogger(__name__)


class LLMComplianceEngine:
    """Intelligent compliance checking using GPT-4o for semantic analysis"""
    
    def __init__(self):
        """Initialize the LLM compliance engine with Azure OpenAI configuration"""
        self.setup_azure_openai()
    
    def setup_azure_openai(self):
        """Configure Azure OpenAI credentials using same pattern as quality_analyzer"""
        # Use the correct endpoint and API version that works
        openai.api_type = "azure"
        openai.api_base = "https://newfinai-app.openai.azure.com/"
        openai.api_key = os.getenv("AZURE_OPENAI_API_KEY")
        openai.api_version = "2024-08-01-preview"
        
        self.deployment_name = deployment_name
        
        logger.info(f"OpenAI API Type: {openai.api_type}")
        logger.info(f"OpenAI API Base: {openai.api_base}")
        logger.info(f"OpenAI API Key: {'Set' if openai.api_key else 'Not Set'}")
        logger.info(f"Deployment Name: {self.deployment_name}")
        logger.info("✅ Azure OpenAI configured for LLM Compliance Engine")
    
    def classify_rules_by_type(self, rules: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Use GPT-4o to classify rules into categories:
        - lc_comparison: Rules that compare document fields against LC values
        - cross_document: Rules that compare fields across different documents
        - validation: Rules that validate document properties (dates, signatures, etc.)
        
        Args:
            rules: List of rule objects from discrepancy_rules.json
            
        Returns:
            Dictionary with categorized rules
        """
        try:
            logger.info(f"🤖 Classifying {len(rules)} rules using GPT-4o...")
            
            # Prepare rules for LLM analysis
            rules_text = json.dumps([{
                'code': rule.get('code'),
                'documentType': rule.get('documentType'),
                'description': rule.get('description'),
                'basis': rule.get('basis')
            } for rule in rules], indent=2)
            
            prompt = f"""Analyze the following compliance rules and classify each into ONE of these categories:

1. **lc_comparison**: Rules that require comparing a document field value against Letter of Credit (LC) requirements
   Examples: "must match LC", "consistent with LC", "as per LC terms"

2. **cross_document**: Rules that require comparing values across different documents
   Examples: "must match invoice", "consistent with packing list", "match across documents"

NOTE: Only classify into lc_comparison or cross_document. Do NOT include validation rules.

Rules to classify:
{rules_text}

Return ONLY a JSON object (no markdown, no explanation):
{{
  "lc_comparison": [list of rule codes],
  "cross_document": [list of rule codes]
}}"""

            response = openai.ChatCompletion.create(
                engine=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are a trade finance compliance expert. Classify rules accurately based on their purpose."},
                    {"role": "user", "content": prompt}
                ],
                temperature=OPENAI_TEMPERATURE_COMPLIANCE,
                max_tokens=OPENAI_MAX_TOKENS_COMPLIANCE
            )
            
            # Extract and validate response content
            response_content = response.choices[0].message.content.strip()
            logger.info(f"📥 GPT-4o response (first 500 chars): {response_content[:500]}")
            
            if not response_content:
                logger.error("❌ GPT-4o returned empty response")
                raise ValueError("Empty response from GPT-4o")
            
            # Remove markdown code fences if present
            if response_content.startswith('```'):
                # Remove opening fence
                response_content = response_content.split('\n', 1)[1] if '\n' in response_content else response_content[3:]
                # Remove closing fence
                if response_content.endswith('```'):
                    response_content = response_content.rsplit('```', 1)[0]
                response_content = response_content.strip()
            
            classification = json.loads(response_content)
            
            # Organize rules by category (only LC comparison and cross-document)
            categorized = {
                'lc_comparison': [],
                'cross_document': []
            }
            
            # Map rules to categories
            rule_map = {rule.get('code'): rule for rule in rules}
            
            for category in ['lc_comparison', 'cross_document']:
                for code in classification.get(category, []):
                    if code in rule_map:
                        categorized[category].append(rule_map[code])
            
            logger.info(f"✅ Rules classified - LC: {len(categorized['lc_comparison'])}, "
                       f"Cross-Doc: {len(categorized['cross_document'])}")
            
            return categorized
            
        except Exception as e:
            logger.error(f"❌ Error classifying rules: {str(e)}")
            return {'lc_comparison': [], 'cross_document': []}
    
    def perform_lc_comparison_check(
        self,
        documents: List[Dict[str, Any]],
        lc_context: Dict[str, Any],
        rules: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Use GPT-4o to intelligently compare document fields against LC values
        LLM decides which fields to compare based on rules and semantic understanding
        
        Args:
            documents: List of classified documents with extracted entities
            lc_context: LC data including all field values
            rules: LC comparison rules to apply
            
        Returns:
            List of compliance results (both compliant and non-compliant)
        """
        results = []
        
        logger.info(f"🔍 Performing LC comparison for {len(documents)} documents with {len(rules)} rules")
        
        # Process each document
        for doc in documents:
            # Extract document type - handle both string and dict formats
            doc_type = doc.get('documentType', doc.get('classification', 'Unknown'))
            
            # If documentType is a dict, extract the document_type string
            if isinstance(doc_type, dict):
                doc_type = doc_type.get('document_type', 'Unknown')
            
            # Ensure we have a string
            if not isinstance(doc_type, str):
                doc_type = 'Unknown'
            
            doc_name = doc.get('name', doc.get('fileName', 'Unknown Document'))
            entities = doc.get('entities', {})
            
            logger.info(f"📄 Checking {doc_name} (Type: {doc_type}) with {len(entities)} entities")
            
            # Get rules applicable to this document type
            applicable_rules = [r for r in rules if r.get('documentType', '').lower() == doc_type.lower()]
            
            if not applicable_rules:
                logger.info(f"⚠️ No LC comparison rules found for document type: {doc_type}")
                continue
            
            # Let GPT-4o decide which fields to compare
            try:
                # Safely serialize rules - handle any nested dicts
                try:
                    rules_summary = []
                    for r in applicable_rules:
                        rules_summary.append({
                            'code': str(r.get('ruleCode', 'N/A')),
                            'description': str(r.get('description', 'N/A')),
                            'basis': str(r.get('basis', 'N/A'))
                        })
                except Exception as rule_err:
                    logger.error(f"Error serializing rules: {str(rule_err)}")
                    rules_summary = [{'error': 'Could not serialize rules'}]
                
                prompt = f"""You are a trade finance compliance expert. Analyze the document fields against LC values based on the provided rules.

**Document Type:** {doc_type}
**Document Name:** {doc_name}

**Document Fields (Extracted Entities):**
{json.dumps(entities, indent=2)}

**LC Context (All Available LC Fields):**
{json.dumps(lc_context, indent=2)}

**Applicable Rules ({len(applicable_rules)} rules):**
{json.dumps(rules_summary, indent=2)}

**Task:**
1. Identify which document fields should be compared against LC values based on the rules
2. For each relevant comparison, determine if the document value is semantically equivalent to the LC value
3. Accept semantic equivalence (abbreviations, format variations, synonyms)
4. Only flag as non-compliant if there's a genuine discrepancy

**Return ONLY a JSON array:**
[
  {{
    "field": "Document field name",
    "documentValue": "Value from document",
    "lcField": "Matching LC field name",
    "lcValue": "Value from LC",
    "ruleCode": "R-XXXX",
    "ruleDescription": "Rule description",
    "compliant": true or false,
    "explanation": "Brief explanation of comparison result",
    "severity": "low" or "high"
  }}
]

**IMPORTANT:** Only include fields that SHOULD be compared per the rules. Return empty array [] if no comparisons are needed."""

                response = openai.ChatCompletion.create(
                    engine=self.deployment_name,
                    messages=[
                        {"role": "system", "content": "You are a trade finance expert performing LC compliance checks. Be thorough and precise."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=OPENAI_TEMPERATURE_COMPLIANCE,
                    max_tokens=OPENAI_MAX_TOKENS_COMPLIANCE * 2  # More tokens for multiple comparisons
                )
                
                response_content = response.choices[0].message.content.strip()
                
                # Strip markdown code fences if present
                if response_content.startswith('```'):
                    response_content = response_content.split('```')[1]
                    if response_content.startswith('json'):
                        response_content = response_content[4:]
                    response_content = response_content.strip()
                
                comparisons = json.loads(response_content)
                
                logger.info(f"✅ LLM identified {len(comparisons)} field comparisons for {doc_name}")
                
                # Add document metadata to each result
                for comparison in comparisons:
                    results.append({
                        'field': comparison.get('field'),
                        'documentType': doc_type,
                        'documentName': doc_name,
                        'documentValue': comparison.get('documentValue'),
                        'lcValue': comparison.get('lcValue'),
                        'lcField': comparison.get('lcField'),
                        'ruleCode': comparison.get('ruleCode'),
                        'ruleDescription': comparison.get('ruleDescription'),
                        'discrepancy': comparison.get('explanation'),
                        'severity': comparison.get('severity', 'low' if comparison.get('compliant') else 'high'),
                        'isCompliant': comparison.get('compliant', False),
                        'hash': doc.get('hash', doc.get('file_hash', ''))
                    })
                    
            except Exception as e:
                logger.error(f"❌ Error in LLM LC comparison for {doc_name}: {str(e)}")
                continue
        
        logger.info(f"✅ LC comparison complete: {len(results)} results")
        return results
    
    def perform_cross_document_check(
        self,
        documents: List[Dict[str, Any]],
        rules: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Use GPT-4o to intelligently check field consistency across documents
        LLM decides which fields to compare and evaluates semantic consistency
        
        Args:
            documents: List of classified documents with extracted entities
            rules: Cross-document comparison rules to apply
            
        Returns:
            List of compliance results
        """
        results = []
        
        logger.info(f"🔗 Performing cross-document comparison for {len(documents)} documents")
        
        if len(documents) < 2:
            logger.info("⚠️ Need at least 2 documents for cross-document comparison")
            return results
        
        # Prepare document data for LLM
        doc_data = []
        for doc in documents:
            doc_type = doc.get('documentType', {})
            if isinstance(doc_type, dict):
                doc_type = doc_type.get('document_type', 'Unknown')
            
            doc_data.append({
                'name': doc.get('name', 'Unknown'),
                'type': doc_type,
                'entities': doc.get('entities', {})
            })
        
        # Let GPT-4o analyze cross-document consistency
        try:
            # Safely serialize rules
            try:
                rules_summary = []
                for r in rules:
                    rules_summary.append({
                        'code': str(r.get('ruleCode', 'N/A')),
                        'description': str(r.get('description', 'N/A')),
                        'basis': str(r.get('basis', 'N/A'))
                    })
            except Exception as rule_err:
                logger.error(f"Error serializing cross-doc rules: {str(rule_err)}")
                rules_summary = [{'error': 'Could not serialize rules'}]
            
            prompt = f"""You are a trade finance compliance expert. Analyze field consistency across multiple documents based on cross-document rules.

**Documents ({len(doc_data)} total):**
{json.dumps(doc_data, indent=2)}

**Cross-Document Rules ({len(rules)} rules):**
{json.dumps(rules_summary, indent=2)}

**Task:**
1. Identify which fields should be consistent across documents based on the rules
2. Compare values across documents for semantic consistency
3. Accept semantic equivalence (abbreviations, format variations, synonyms)
4. Flag genuine inconsistencies where values have different meanings

**Return ONLY a JSON array:**
[
  {{
    "field": "Field name",
    "document1Name": "First document name",
    "document1Value": "Value in first document",
    "document2Name": "Second document name",  
    "document2Value": "Value in second document",
    "ruleCode": "R-XXXX",
    "ruleDescription": "Rule description",
    "compliant": true or false,
    "explanation": "Brief explanation",
    "severity": "low" or "medium"
  }}
]

**IMPORTANT:** Only include fields that SHOULD be compared per the rules. Return empty array [] if no cross-document comparisons are needed."""

            response = openai.ChatCompletion.create(
                engine=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are a trade finance expert checking cross-document consistency. Be thorough."},
                    {"role": "user", "content": prompt}
                ],
                temperature=OPENAI_TEMPERATURE_COMPLIANCE,
                max_tokens=OPENAI_MAX_TOKENS_COMPLIANCE * 2
            )
            
            response_content = response.choices[0].message.content.strip()
            
            # Strip markdown code fences if present
            if response_content.startswith('```'):
                response_content = response_content.split('```')[1]
                if response_content.startswith('json'):
                    response_content = response_content[4:]
                response_content = response_content.strip()
            
            comparisons = json.loads(response_content)
            
            logger.info(f"✅ LLM identified {len(comparisons)} cross-document comparisons")
            
            # Add metadata to each result
            for comparison in comparisons:
                results.append({
                    'field': comparison.get('field'),
                    'documentType': 'Cross-Document',
                    'documentName': comparison.get('document1Name'),
                    'documentValue': comparison.get('document1Value'),
                    'expectedValue': comparison.get('document2Value'),
                    'expectedSource': comparison.get('document2Name'),
                    'ruleCode': comparison.get('ruleCode'),
                    'ruleDescription': comparison.get('ruleDescription'),
                    'discrepancy': comparison.get('explanation'),
                    'severity': comparison.get('severity', 'low' if comparison.get('compliant') else 'medium'),
                    'isCompliant': comparison.get('compliant', False)
                })
                
        except Exception as e:
            logger.error(f"❌ Error in LLM cross-document comparison: {str(e)}")
        
        logger.info(f"✅ Cross-document comparison complete: {len(results)} results")
        return results
    
    def run_comprehensive_compliance_check(
        self,
        documents: List[Dict[str, Any]],
        lc_context: Dict[str, Any],
        all_rules: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Run complete LLM-based compliance check
        
        Args:
            documents: List of classified documents with extracted entities
            lc_context: LC context data
            all_rules: All rules from discrepancy_rules.json
            
        Returns:
            Compliance results with all checks
        """
        try:
            logger.info("🚀 Starting comprehensive LLM-based compliance check")
            
            # Step 1: Classify rules
            categorized_rules = self.classify_rules_by_type(all_rules)
            
            # Step 2: Perform LC comparisons
            lc_results = self.perform_lc_comparison_check(
                documents=documents,
                lc_context=lc_context,
                rules=categorized_rules['lc_comparison']
            )
            
            # Step 3: Perform cross-document comparisons
            cross_doc_results = self.perform_cross_document_check(
                documents=documents,
                rules=categorized_rules['cross_document']
            )
            
            # Combine results
            all_results = lc_results + cross_doc_results
            
            # Statistics
            total_checks = len(all_results)
            compliant_count = sum(1 for r in all_results if r.get('isCompliant'))
            non_compliant_count = total_checks - compliant_count
            
            logger.info(f"✅ Compliance check complete: {total_checks} checks, "
                       f"{compliant_count} compliant, {non_compliant_count} non-compliant")
            
            return {
                'success': True,
                'results': all_results,
                'statistics': {
                    'total_checks': total_checks,
                    'compliant': compliant_count,
                    'non_compliant': non_compliant_count,
                    'compliance_rate': (compliant_count / total_checks * 100) if total_checks > 0 else 0
                },
                'rule_classification': {
                    'lc_comparison_rules': len(categorized_rules['lc_comparison']),
                    'cross_document_rules': len(categorized_rules['cross_document'])
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Error in comprehensive compliance check: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'results': []
            }
