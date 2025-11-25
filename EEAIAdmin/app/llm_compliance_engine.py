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

# Import DocumentClassifier to access prompt config
from app.utils.document_classifier import DocumentClassifier

logger = logging.getLogger(__name__)


class LLMComplianceEngine:
    """Intelligent compliance checking using GPT-4o for semantic analysis"""
    
    def __init__(self):
        """Initialize the LLM compliance engine with Azure OpenAI configuration"""
        self.setup_azure_openai()
        # Create DocumentClassifier instance to access prompt config
        self.document_classifier = DocumentClassifier()
    
    def setup_azure_openai(self):
        """Configure Azure OpenAI credentials using same pattern as routes.py"""
        # Use environment variables - matches working code in routes.py
        azure_key = os.getenv('AZURE_OPENAI_API_KEY')
        azure_base = os.getenv('AZURE_OPENAI_API_BASE')
        azure_version = os.getenv('AZURE_OPENAI_VERSION', '2023-12-01-preview')
        
        if azure_key and azure_base:
            openai.api_type = "azure"
            openai.api_key = azure_key
            openai.api_base = azure_base
            openai.api_version = azure_version
        else:
            logger.error("Azure OpenAI credentials not found in environment")
        
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
            logger.info("")
            logger.info(f"{'='*100}")
            logger.info("🤖 COMPLIANCE ENGINE - RULE CLASSIFICATION")
            logger.info(f"{'='*100}")
            logger.info(f"📊 Total rules to classify: {len(rules)}")
            logger.info("")
            
            # Prepare rules for LLM analysis
            rules_text = json.dumps([{
                'code': rule.get('code'),
                'documentType': rule.get('documentType'),
                'description': rule.get('description'),
                'basis': rule.get('basis')
            } for rule in rules], indent=2)
            
            logger.info(f"{'='*100}")
            logger.info("📋 COMPLIANCE ENGINE - INPUT DATA")
            logger.info(f"{'='*100}")
            logger.info(f"📊 Rules count: {len(rules)}")
            logger.info(f"📋 COMPLETE RULES DATA (FULL - NO TRUNCATION):\n{rules_text}")
            logger.info(f"{'='*100}")
            logger.info("")
            
            # Load discrepancy rules classify config from YAML
            classify_config = self.document_classifier.prompt_config.get('discrepancy_rules', {}).get('classify_rules', {})
            
            model = classify_config.get('model', self.deployment_name)
            temperature = classify_config.get('temperature', OPENAI_TEMPERATURE_COMPLIANCE)
            max_tokens = classify_config.get('max_tokens', OPENAI_MAX_TOKENS_COMPLIANCE)
            system_prompt = classify_config.get('system_prompt', 'You are a trade finance compliance expert.')
            user_prompt_template = classify_config.get('user_prompt_template', '')
            
            prompt = user_prompt_template.format(
                rules_text=rules_text
            )

            logger.info("")
            logger.info(f"{'='*100}")
            logger.info("🔧 COMPLIANCE ENGINE - CONFIGURATION")
            logger.info(f"{'='*100}")
            logger.info(f"🌐 Azure OpenAI Endpoint: {openai.api_base}")
            logger.info(f"🔑 API Key: {'*' * 20 if openai.api_key else 'NOT SET'}")
            logger.info(f"📦 API Version: {openai.api_version}")
            logger.info(f"🚀 Deployment Name: {model}")
            logger.info(f"{'='*100}")
            logger.info("")
            
            logger.info("")
            logger.info(f"{'='*100}")
            logger.info("📝 COMPLIANCE ENGINE - PROMPT & API PARAMETERS")
            logger.info(f"{'='*100}")
            logger.info(f"📊 Prompt Length: {len(prompt)} characters")
            logger.info(f"📋 System Message: {system_prompt}")
            logger.info(f"📋 COMPLETE PROMPT (FULL - NO TRUNCATION):\n{prompt}")
            logger.info(f"")
            logger.info(f"🔧 API Call Parameters:")
            logger.info(f"🔢 Temperature: {temperature}")
            logger.info(f"🔢 Max Tokens: {max_tokens}")
            logger.info(f"🚀 Sending request to Azure OpenAI...")
            logger.info(f"{'='*100}")
            logger.info("")

            response = openai.ChatCompletion.create(
                engine=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # Extract and validate response content
            response_content = response.choices[0].message.content.strip()
            
            logger.info("")
            logger.info(f"{'='*100}")
            logger.info("✅ COMPLIANCE ENGINE - RULE CLASSIFICATION RESPONSE")
            logger.info(f"{'='*100}")
            logger.info(f"📊 Response Status: Success")
            logger.info(f"📊 Response Length: {len(response_content)} characters")
            logger.info(f"📋 COMPLETE RAW RESPONSE (FULL - NO TRUNCATION):\n{response_content}")
            logger.info(f"{'='*100}")
            logger.info("")
            
            if not response_content:
                logger.error("")
                logger.error(f"{'='*100}")
                logger.error("❌ COMPLIANCE ENGINE - EMPTY RESPONSE ERROR")
                logger.error(f"{'='*100}")
                logger.error("❌ GPT-4o returned empty response")
                logger.error(f"{'='*100}")
                logger.error("")
                raise ValueError("Empty response from GPT-4o")
            
            # Remove markdown code fences if present
            logger.info("")
            logger.info(f"{'='*100}")
            logger.info("🔍 COMPLIANCE ENGINE - EXTRACTING JSON")
            logger.info(f"{'='*100}")
            
            original_response = response_content
            if response_content.startswith('```'):
                # Remove opening fence
                response_content = response_content.split('\n', 1)[1] if '\n' in response_content else response_content[3:]
                # Remove closing fence
                if response_content.endswith('```'):
                    response_content = response_content.rsplit('```', 1)[0]
                response_content = response_content.strip()
                logger.info(f"📝 Removed markdown code fences")
            else:
                logger.info(f"📝 No markdown code fences found")
            
            logger.info(f"📊 Cleaned Response Length: {len(response_content)} characters")
            logger.info(f"📋 CLEANED JSON TEXT (FULL - NO TRUNCATION):\n{response_content}")
            logger.info(f"{'='*100}")
            logger.info("")
            
            logger.info("")
            logger.info(f"{'='*100}")
            logger.info("🔧 COMPLIANCE ENGINE - PARSING JSON")
            logger.info(f"{'='*100}")
            
            classification = json.loads(response_content)
            logger.info(f"✅ JSON parsing successful")
            logger.info(f"📊 Classification keys: {list(classification.keys())}")
            logger.info(f"✅ JSON parsing successful")
            logger.info(f"📊 Classification keys: {list(classification.keys())}")
            logger.info(f"📋 PARSED CLASSIFICATION (FULL - NO TRUNCATION):\n{json.dumps(classification, indent=2)}")
            logger.info(f"{'='*100}")
            logger.info("")
            
            # Organize rules by category (only LC comparison and cross-document)
            logger.info("")
            logger.info(f"{'='*100}")
            logger.info("🧹 COMPLIANCE ENGINE - ORGANIZING RULES")
            logger.info(f"{'='*100}")
            
            categorized = {
                'lc_comparison': [],
                'cross_document': []
            }
            
            # Map rules to categories
            rule_map = {rule.get('code'): rule for rule in rules}
            logger.info(f"📊 Total rules in map: {len(rule_map)}")
            
            for category in ['lc_comparison', 'cross_document']:
                codes = classification.get(category, [])
                logger.info(f"📋 {category}: {len(codes)} rule codes found")
                for code in codes:
                    if code in rule_map:
                        categorized[category].append(rule_map[code])
                        logger.info(f"   ✅ Mapped {code} to {category}")
                    else:
                        logger.warning(f"   ⚠️ Code {code} not found in rule_map")
            
            logger.info(f"")
            logger.info(f"✅ Rule categorization complete")
            logger.info(f"📊 LC Comparison Rules: {len(categorized['lc_comparison'])}")
            logger.info(f"📊 Cross-Document Rules: {len(categorized['cross_document'])}")
            logger.info(f"📋 FINAL CATEGORIZED RULES (FULL - NO TRUNCATION):\n{json.dumps(categorized, indent=2, default=str)}")
            logger.info(f"{'='*100}")
            logger.info("")
            
            return categorized
            
        except Exception as e:
            logger.error("")
            logger.error(f"{'='*100}")
            logger.error("❌ COMPLIANCE ENGINE - RULE CLASSIFICATION ERROR")
            logger.error(f"{'='*100}")
            logger.error(f"❌ Error Type: {type(e).__name__}")
            logger.error(f"❌ Error Message: {str(e)}")
            logger.exception("❌ Full traceback:")
            logger.error(f"{'='*100}")
            logger.error("")
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
                logger.info("")
                logger.info(f"{'='*100}")
                logger.info(f"🔍 COMPLIANCE ENGINE - LC COMPARISON FOR: {doc_name}")
                logger.info(f"{'='*100}")
                logger.info(f"📄 Document Type: {doc_type}")
                logger.info(f"📊 Entities Count: {len(entities)}")
                logger.info(f"📊 Applicable Rules Count: {len(applicable_rules)}")
                logger.info("")
                
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
                    logger.error(f"❌ Error serializing rules: {str(rule_err)}")
                    rules_summary = [{'error': 'Could not serialize rules'}]
                
                logger.info(f"{'='*100}")
                logger.info(f"📋 COMPLIANCE ENGINE - LC COMPARISON INPUT DATA")
                logger.info(f"{'='*100}")
                logger.info(f"📄 Document: {doc_name}")
                logger.info(f"📋 Document Type: {doc_type}")
                logger.info(f"📋 DOCUMENT ENTITIES (FULL - NO TRUNCATION):\n{json.dumps(entities, indent=2)}")
                logger.info(f"📋 LC CONTEXT (FULL - NO TRUNCATION):\n{json.dumps(lc_context, indent=2)}")
                logger.info(f"📋 APPLICABLE RULES (FULL - NO TRUNCATION):\n{json.dumps(rules_summary, indent=2)}")
                logger.info(f"{'='*100}")
                logger.info("")
                
                # Load LC comparison config from YAML
                lc_comp_config = self.document_classifier.prompt_config.get('discrepancy_rules', {}).get('lc_comparison', {})
                
                model = lc_comp_config.get('model', self.deployment_name)
                temperature = lc_comp_config.get('temperature', OPENAI_TEMPERATURE_COMPLIANCE)
                max_tokens = lc_comp_config.get('max_tokens', OPENAI_MAX_TOKENS_COMPLIANCE)
                system_prompt = lc_comp_config.get('system_prompt', 'You are a trade finance compliance expert.')
                user_prompt_template = lc_comp_config.get('user_prompt_template', '')
                
                prompt = user_prompt_template.format(
                    doc_type=doc_type,
                    doc_name=doc_name,
                    entities=json.dumps(entities, indent=2),
                    lc_context=json.dumps(lc_context, indent=2),
                    rules_count=len(applicable_rules),
                    rules_summary=json.dumps(rules_summary, indent=2)
                )

                logger.info("")
                logger.info(f"{'='*100}")
                logger.info(f"📝 COMPLIANCE ENGINE - LC COMPARISON PROMPT")
                logger.info(f"{'='*100}")
                logger.info(f"📊 Prompt Length: {len(prompt)} characters")
                logger.info(f"📋 COMPLETE PROMPT (FULL - NO TRUNCATION):\n{prompt}")
                logger.info("")
                logger.info(f"🔧 API Call Parameters:")
                logger.info(f"🔢 Temperature: {temperature}")
                logger.info(f"🔢 Max Tokens: {max_tokens}")
                logger.info(f"🚀 Model: {model}")
                logger.info(f"🚀 Sending request to Azure OpenAI...")
                logger.info(f"{'='*100}")
                logger.info("")

                response = openai.ChatCompletion.create(
                    engine=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                
                response_content = response.choices[0].message.content.strip()
                
                logger.info("")
                logger.info(f"{'='*100}")
                logger.info(f"✅ COMPLIANCE ENGINE - LC COMPARISON RESPONSE")
                logger.info(f"{'='*100}")
                logger.info(f"📊 Response Status: Success")
                logger.info(f"📊 Response Length: {len(response_content)} characters")
                logger.info(f"📋 COMPLETE RAW RESPONSE (FULL - NO TRUNCATION):\n{response_content}")
                logger.info(f"{'='*100}")
                logger.info("")
                
                # Strip markdown code fences if present
                logger.info("")
                logger.info(f"{'='*100}")
                logger.info(f"🔍 COMPLIANCE ENGINE - EXTRACTING JSON")
                logger.info(f"{'='*100}")
                
                if response_content.startswith('```'):
                    response_content = response_content.split('```')[1]
                    if response_content.startswith('json'):
                        response_content = response_content[4:]
                    response_content = response_content.strip()
                    logger.info(f"📝 Removed markdown code fences")
                else:
                    logger.info(f"📝 No markdown code fences found")
                
                logger.info(f"📊 Cleaned Response Length: {len(response_content)} characters")
                logger.info(f"📋 CLEANED JSON TEXT (FULL - NO TRUNCATION):\n{response_content}")
                logger.info(f"{'='*100}")
                logger.info("")
                
                logger.info("")
                logger.info(f"{'='*100}")
                logger.info(f"🔧 COMPLIANCE ENGINE - PARSING JSON")
                logger.info(f"{'='*100}")
                
                comparisons = json.loads(response_content)
                logger.info(f"✅ JSON parsing successful")
                logger.info(f"📊 Comparisons count: {len(comparisons)}")
                logger.info(f"📋 PARSED COMPARISONS (FULL - NO TRUNCATION):\n{json.dumps(comparisons, indent=2)}")
                logger.info(f"{'='*100}")
                logger.info("")
                
                # Add document metadata to each result
                logger.info("")
                logger.info(f"{'='*100}")
                logger.info(f"🧹 COMPLIANCE ENGINE - PROCESSING COMPARISONS")
                logger.info(f"{'='*100}")
                logger.info(f"📊 Processing {len(comparisons)} comparisons for {doc_name}")
                logger.info("")
                
                for idx, comparison in enumerate(comparisons):
                    logger.info(f"{'─'*80}")
                    logger.info(f"🔍 Processing comparison {idx + 1}/{len(comparisons)}")
                    logger.info(f"📋 Field: {comparison.get('field')}")
                    
                    doc_value = comparison.get('documentValue', '')
                    lc_value = comparison.get('lcValue', '')
                    
                    logger.info(f"📄 Document Value: {doc_value}")
                    logger.info(f"📋 LC Value: {lc_value}")
                    
                    # Check if either value is empty/None/null
                    is_doc_value_empty = not doc_value or str(doc_value).strip() == '' or str(doc_value).lower() in ['none', 'null', 'n/a', 'not found', 'not available']
                    is_lc_value_empty = not lc_value or str(lc_value).strip() == '' or str(lc_value).lower() in ['none', 'null', 'n/a', 'not found', 'not available']
                    
                    logger.info(f"🔍 Document value empty: {is_doc_value_empty}")
                    logger.info(f"🔍 LC value empty: {is_lc_value_empty}")
                    
                    # If either value is empty, mark as non-compliant (override LLM decision)
                    if is_doc_value_empty or is_lc_value_empty:
                        is_compliant = False
                        explanation = comparison.get('explanation', '')
                        
                        if is_doc_value_empty and is_lc_value_empty:
                            explanation = f"Both document value and LC value are empty/missing. Cannot perform comparison."
                            severity = 'high'
                            logger.warning(f"⚠️ Both values empty - marking as non-compliant")
                        elif is_doc_value_empty:
                            explanation = f"Document value is empty/missing (LC value: '{lc_value}'). Cannot verify compliance."
                            severity = 'high'
                            logger.warning(f"⚠️ Document value empty - marking as non-compliant")
                        else:
                            explanation = f"LC value is empty/missing (Document value: '{doc_value}'). Cannot perform comparison."
                            severity = 'high'
                            logger.warning(f"⚠️ LC value empty - marking as non-compliant")
                        
                        logger.warning(f"⚠️ Empty value detected for {comparison.get('field')}: {explanation}")
                    else:
                        # Both values present, use LLM's compliance decision
                        is_compliant = comparison.get('compliant', False)
                        explanation = comparison.get('explanation')
                        severity = comparison.get('severity', 'low' if is_compliant else 'high')
                        logger.info(f"✅ Both values present - using LLM decision: compliant={is_compliant}")
                    
                    result = {
                        'field': comparison.get('field'),
                        'documentType': doc_type,
                        'documentName': doc_name,
                        'documentValue': doc_value,
                        'lcValue': lc_value,
                        'lcField': comparison.get('lcField'),
                        'ruleCode': comparison.get('ruleCode'),
                        'ruleDescription': comparison.get('ruleDescription'),
                        'discrepancy': explanation,
                        'severity': severity,
                        'isCompliant': is_compliant,
                        'hash': doc.get('hash', doc.get('file_hash', ''))
                    }
                    
                    results.append(result)
                    logger.info(f"📝 Added result: {comparison.get('field')} - Compliant: {is_compliant}")
                
                logger.info("")
                logger.info(f"✅ Completed processing {len(comparisons)} comparisons for {doc_name}")
                logger.info(f"📊 Total results added: {len(comparisons)}")
                logger.info(f"{'='*100}")
                logger.info("")
                    
            except Exception as e:
                logger.error("")
                logger.error(f"{'='*100}")
                logger.error(f"❌ COMPLIANCE ENGINE - LC COMPARISON ERROR")
                logger.error(f"{'='*100}")
                logger.error(f"❌ Document: {doc_name}")
                logger.error(f"❌ Error Type: {type(e).__name__}")
                logger.error(f"❌ Error Message: {str(e)}")
                logger.exception("❌ Full traceback:")
                logger.error(f"{'='*100}")
                logger.error("")
                continue
        
        logger.info("")
        logger.info(f"{'='*100}")
        logger.info(f"🎉 COMPLIANCE ENGINE - LC COMPARISON COMPLETE")
        logger.info(f"{'='*100}")
        logger.info(f"📊 Total results: {len(results)}")
        logger.info(f"📋 FINAL LC COMPARISON RESULTS (FULL - NO TRUNCATION):\n{json.dumps(results, indent=2, default=str)}")
        logger.info(f"{'='*100}")
        logger.info("")
        
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
            
            logger.info("")
            logger.info(f"{'='*100}")
            logger.info(f"🔗 COMPLIANCE ENGINE - CROSS-DOCUMENT COMPARISON")
            logger.info(f"{'='*100}")
            logger.info(f"📊 Total documents: {len(doc_data)}")
            logger.info(f"📊 Total rules: {len(rules)}")
            logger.info("")
            
            logger.info(f"{'='*100}")
            logger.info(f"📋 COMPLIANCE ENGINE - CROSS-DOCUMENT INPUT DATA")
            logger.info(f"{'='*100}")
            logger.info(f"📋 DOCUMENT DATA (FULL - NO TRUNCATION):\n{json.dumps(doc_data, indent=2)}")
            logger.info(f"📋 CROSS-DOCUMENT RULES (FULL - NO TRUNCATION):\n{json.dumps(rules_summary, indent=2)}")
            logger.info(f"{'='*100}")
            logger.info("")
            
            # Load cross-document config from YAML
            cross_doc_config = self.document_classifier.prompt_config.get('discrepancy_rules', {}).get('cross_document', {})
            
            model = cross_doc_config.get('model', self.deployment_name)
            temperature = cross_doc_config.get('temperature', OPENAI_TEMPERATURE_COMPLIANCE)
            max_tokens = cross_doc_config.get('max_tokens', OPENAI_MAX_TOKENS_COMPLIANCE * 2)
            system_prompt = cross_doc_config.get('system_prompt', 'You are a trade finance expert checking cross-document consistency.')
            user_prompt_template = cross_doc_config.get('user_prompt_template', '')
            
            prompt = user_prompt_template.format(
                doc_count=len(doc_data),
                doc_data=json.dumps(doc_data, indent=2),
                rules_count=len(rules),
                rules_summary=json.dumps(rules_summary, indent=2)
            )

            logger.info("")
            logger.info(f"{'='*100}")
            logger.info(f"📝 COMPLIANCE ENGINE - CROSS-DOCUMENT PROMPT")
            logger.info(f"{'='*100}")
            logger.info(f"📊 Prompt Length: {len(prompt)} characters")
            logger.info(f"📋 COMPLETE PROMPT (FULL - NO TRUNCATION):\n{prompt}")
            logger.info("")
            logger.info(f"🔧 API Call Parameters:")
            logger.info(f"🔢 Temperature: {temperature}")
            logger.info(f"🔢 Max Tokens: {max_tokens}")
            logger.info(f"🚀 Model: {model}")
            logger.info(f"🚀 Sending request to Azure OpenAI...")
            logger.info(f"{'='*100}")
            logger.info("")

            response = openai.ChatCompletion.create(
                engine=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            response_content = response.choices[0].message.content.strip()
            
            logger.info("")
            logger.info(f"{'='*100}")
            logger.info(f"✅ COMPLIANCE ENGINE - CROSS-DOCUMENT RESPONSE")
            logger.info(f"{'='*100}")
            logger.info(f"📊 Response Status: Success")
            logger.info(f"📊 Response Length: {len(response_content)} characters")
            logger.info(f"📋 COMPLETE RAW RESPONSE (FULL - NO TRUNCATION):\n{response_content}")
            logger.info(f"{'='*100}")
            logger.info("")
            
            # Strip markdown code fences if present
            logger.info("")
            logger.info(f"{'='*100}")
            logger.info(f"🔍 COMPLIANCE ENGINE - EXTRACTING JSON")
            logger.info(f"{'='*100}")
            
            if response_content.startswith('```'):
                response_content = response_content.split('```')[1]
                if response_content.startswith('json'):
                    response_content = response_content[4:]
                response_content = response_content.strip()
                logger.info(f"📝 Removed markdown code fences")
            else:
                logger.info(f"📝 No markdown code fences found")
            
            logger.info(f"📊 Cleaned Response Length: {len(response_content)} characters")
            logger.info(f"📋 CLEANED JSON TEXT (FULL - NO TRUNCATION):\n{response_content}")
            logger.info(f"{'='*100}")
            logger.info("")
            
            logger.info("")
            logger.info(f"{'='*100}")
            logger.info(f"🔧 COMPLIANCE ENGINE - PARSING JSON")
            logger.info(f"{'='*100}")
            
            comparisons = json.loads(response_content)
            logger.info(f"✅ JSON parsing successful")
            logger.info(f"📊 Comparisons count: {len(comparisons)}")
            logger.info(f"📋 PARSED COMPARISONS (FULL - NO TRUNCATION):\n{json.dumps(comparisons, indent=2)}")
            logger.info(f"{'='*100}")
            logger.info("")
            
            # Add metadata to each result
            logger.info("")
            logger.info(f"{'='*100}")
            logger.info(f"🧹 COMPLIANCE ENGINE - PROCESSING CROSS-DOCUMENT RESULTS")
            logger.info(f"{'='*100}")
            logger.info(f"📊 Processing {len(comparisons)} comparisons")
            logger.info("")
            
            for idx, comparison in enumerate(comparisons):
                logger.info(f"{'─'*80}")
                logger.info(f"🔍 Processing comparison {idx + 1}/{len(comparisons)}")
                logger.info(f"📋 Field: {comparison.get('field')}")
                logger.info(f"📄 Document 1: {comparison.get('document1Name')} - Value: {comparison.get('document1Value')}")
                logger.info(f"📄 Document 2: {comparison.get('document2Name')} - Value: {comparison.get('document2Value')}")
                logger.info(f"✅ Compliant: {comparison.get('compliant')}")
                
                result = {
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
                }
                results.append(result)
                logger.info(f"📝 Added cross-document result: {comparison.get('field')}")
            
            logger.info("")
            logger.info(f"✅ Completed processing {len(comparisons)} cross-document comparisons")
            logger.info(f"📊 Total results added: {len(comparisons)}")
            logger.info(f"{'='*100}")
            logger.info("")
                
        except Exception as e:
            logger.error("")
            logger.error(f"{'='*100}")
            logger.error(f"❌ COMPLIANCE ENGINE - CROSS-DOCUMENT ERROR")
            logger.error(f"{'='*100}")
            logger.error(f"❌ Error Type: {type(e).__name__}")
            logger.error(f"❌ Error Message: {str(e)}")
            logger.exception("❌ Full traceback:")
            logger.error(f"{'='*100}")
            logger.error("")
        
        logger.info("")
        logger.info(f"{'='*100}")
        logger.info(f"🎉 COMPLIANCE ENGINE - CROSS-DOCUMENT COMPLETE")
        logger.info(f"{'='*100}")
        logger.info(f"📊 Total results: {len(results)}")
        logger.info(f"📋 FINAL CROSS-DOCUMENT RESULTS (FULL - NO TRUNCATION):\n{json.dumps(results, indent=2, default=str)}")
        logger.info(f"{'='*100}")
        logger.info("")
        
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
            logger.info("")
            logger.info(f"{'='*100}")
            logger.info("🚀 COMPLIANCE ENGINE - COMPREHENSIVE CHECK STARTED")
            logger.info(f"{'='*100}")
            logger.info(f"📊 Total documents: {len(documents)}")
            logger.info(f"📊 Total rules: {len(all_rules)}")
            logger.info(f"📋 LC Context fields: {list(lc_context.keys()) if lc_context else []}")
            logger.info(f"{'='*100}")
            logger.info("")
            
            # Step 1: Classify rules
            logger.info("")
            logger.info(f"{'='*100}")
            logger.info("📋 STEP 1: CLASSIFYING RULES")
            logger.info(f"{'='*100}")
            categorized_rules = self.classify_rules_by_type(all_rules)
            logger.info(f"✅ Rule classification complete")
            logger.info(f"{'='*100}")
            logger.info("")
            
            # Step 2: Perform LC comparisons
            logger.info("")
            logger.info(f"{'='*100}")
            logger.info("📋 STEP 2: LC COMPARISON CHECKS")
            logger.info(f"{'='*100}")
            lc_results = self.perform_lc_comparison_check(
                documents=documents,
                lc_context=lc_context,
                rules=categorized_rules['lc_comparison']
            )
            logger.info(f"✅ LC comparison checks complete: {len(lc_results)} results")
            logger.info(f"{'='*100}")
            logger.info("")
            
            # Step 3: Perform cross-document comparisons
            logger.info("")
            logger.info(f"{'='*100}")
            logger.info("📋 STEP 3: CROSS-DOCUMENT CHECKS")
            logger.info(f"{'='*100}")
            cross_doc_results = self.perform_cross_document_check(
                documents=documents,
                rules=categorized_rules['cross_document']
            )
            logger.info(f"✅ Cross-document checks complete: {len(cross_doc_results)} results")
            logger.info(f"{'='*100}")
            logger.info("")
            
            # Combine results
            logger.info("")
            logger.info(f"{'='*100}")
            logger.info("🔗 COMBINING RESULTS")
            logger.info(f"{'='*100}")
            all_results = lc_results + cross_doc_results
            logger.info(f"📊 LC Results: {len(lc_results)}")
            logger.info(f"📊 Cross-Document Results: {len(cross_doc_results)}")
            logger.info(f"📊 Total Combined Results: {len(all_results)}")
            logger.info(f"{'='*100}")
            logger.info("")
            
            # Statistics
            logger.info("")
            logger.info(f"{'='*100}")
            logger.info("📊 CALCULATING STATISTICS")
            logger.info(f"{'='*100}")
            total_checks = len(all_results)
            compliant_count = sum(1 for r in all_results if r.get('isCompliant'))
            non_compliant_count = total_checks - compliant_count
            compliance_rate = (compliant_count / total_checks * 100) if total_checks > 0 else 0
            
            logger.info(f"📊 Total Checks: {total_checks}")
            logger.info(f"✅ Compliant: {compliant_count}")
            logger.info(f"❌ Non-Compliant: {non_compliant_count}")
            logger.info(f"📈 Compliance Rate: {compliance_rate:.2f}%")
            logger.info(f"{'='*100}")
            logger.info("")
            
            final_response = {
                'success': True,
                'results': all_results,
                'statistics': {
                    'total_checks': total_checks,
                    'compliant': compliant_count,
                    'non_compliant': non_compliant_count,
                    'compliance_rate': compliance_rate
                },
                'rule_classification': {
                    'lc_comparison_rules': len(categorized_rules['lc_comparison']),
                    'cross_document_rules': len(categorized_rules['cross_document'])
                }
            }
            
            logger.info("")
            logger.info(f"{'='*100}")
            logger.info("🎉 COMPLIANCE ENGINE - COMPREHENSIVE CHECK COMPLETE")
            logger.info(f"{'='*100}")
            logger.info(f"✅ Success: True")
            logger.info(f"📋 FINAL RESPONSE (FULL - NO TRUNCATION):\n{json.dumps(final_response, indent=2, default=str)}")
            logger.info(f"{'='*100}")
            logger.info("")
            
            return final_response
            
        except Exception as e:
            logger.error("")
            logger.error(f"{'='*100}")
            logger.error("❌ COMPLIANCE ENGINE - COMPREHENSIVE CHECK ERROR")
            logger.error(f"{'='*100}")
            logger.error(f"❌ Error Type: {type(e).__name__}")
            logger.error(f"❌ Error Message: {str(e)}")
            logger.exception("❌ Full traceback:")
            logger.error(f"{'='*100}")
            logger.error("")
            
            error_response = {
                'success': False,
                'error': str(e),
                'results': []
            }
            logger.error(f"📋 Error Response: {json.dumps(error_response)}")
            
            return error_response

