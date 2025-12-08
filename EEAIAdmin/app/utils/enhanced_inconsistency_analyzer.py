"""
Enhanced Inconsistency Analyzer with LLM Integration and Config-Based Rules
"""

import json
import re
import openai
import logging
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from difflib import SequenceMatcher
from datetime import datetime
import numpy as np
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class InconsistencyResult:
    """Structured inconsistency analysis result"""
    field_name: str
    inconsistency_type: str
    severity: str
    confidence_score: float
    lc_value: str
    swift_value: str
    normalized_lc_value: str
    normalized_swift_value: str
    is_inconsistency: bool
    business_impact: str
    recommendation: str
    llm_reasoning: str
    resolution_steps: List[str]
    swift_reference: str
    category: str

class EnhancedInconsistencyAnalyzer:
    """Advanced inconsistency analyzer with LLM integration and config-based rules"""
    
    def __init__(self, config_path: str = None):
        """Initialize the enhanced analyzer with configuration"""
        self.config_path = config_path or "data/inconsistency_analysis_config.json"
        self.config = self._load_config()
        self.field_mappings = self.config.get('field_mappings', [])
        self.inconsistency_types = self.config.get('inconsistency_types', {})
        self.business_rules = self.config.get('business_rules', {})
        self.llm_config = self.config.get('llm_integration', {})
        self.normalization_patterns = self.config.get('normalization_patterns', {})
        
        logger.info(f"🔧 Enhanced Inconsistency Analyzer initialized with {len(self.field_mappings)} field mappings")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            config_file = Path(self.config_path)
            if config_file.exists():
                with open(config_file, 'r') as f:
                    full_config = json.load(f)
                    return full_config.get('inconsistency_analysis_config', {})
            else:
                logger.warning(f"Config file not found: {self.config_path}. Using default config.")
                return self._get_default_config()
        except Exception as e:
            logger.error(f"Error loading config: {e}. Using default config.")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Default configuration fallback"""
        return {
            "llm_integration": {"enabled": False},
            "field_mappings": [],
            "inconsistency_types": {},
            "business_rules": {},
            "normalization_patterns": {}
        }
    
    def analyze_inconsistencies(self, lc_data: Dict[str, Any], swift_data: Dict[str, Any], 
                              document_data: List[Dict] = None) -> List[InconsistencyResult]:
        """Main entry point for enhanced inconsistency analysis"""
        logger.info("🚀 Starting enhanced inconsistency analysis with LLM integration")
        
        inconsistencies = []
        
        # 1. Field-by-field analysis with LLM enhancement
        field_inconsistencies = self._analyze_field_inconsistencies(lc_data, swift_data)
        inconsistencies.extend(field_inconsistencies)
        
        # 2. Contextual analysis using LLM
        if self.llm_config.get('enabled', False):
            contextual_inconsistencies = self._perform_contextual_analysis(lc_data, swift_data, document_data)
            inconsistencies.extend(contextual_inconsistencies)
        
        # 3. Business logic validation
        business_logic_issues = self._validate_business_logic(lc_data, swift_data)
        inconsistencies.extend(business_logic_issues)
        
        # 4. Pattern recognition and anomaly detection
        pattern_inconsistencies = self._detect_pattern_anomalies(lc_data, swift_data)
        inconsistencies.extend(pattern_inconsistencies)
        
        # 5. Cross-document validation (if documents provided)
        if document_data:
            cross_doc_inconsistencies = self._analyze_cross_document_consistency(lc_data, swift_data, document_data)
            inconsistencies.extend(cross_doc_inconsistencies)
        
        logger.info(f"✅ Enhanced analysis complete: {len(inconsistencies)} inconsistencies found")
        return self._rank_and_prioritize_inconsistencies(inconsistencies)
    
    def _analyze_field_inconsistencies(self, lc_data: Dict[str, Any], swift_data: Dict[str, Any]) -> List[InconsistencyResult]:
        """Enhanced field-by-field analysis with LLM integration"""
        inconsistencies = []
        
        for field_mapping in self.field_mappings:
            lc_field = field_mapping.get('lc_field')
            swift_field = field_mapping.get('swift_field')
            display_name = field_mapping.get('display_name')
            
            lc_value = self._extract_field_value(lc_data, lc_field)
            swift_value = self._extract_field_value(swift_data, swift_field)
            
            if lc_value and swift_value:
                # Enhanced comparison with normalization
                result = self._compare_field_values(lc_value, swift_value, field_mapping)
                
                if result.is_inconsistency:
                    # LLM enhancement for complex cases
                    if self.llm_config.get('enabled', False) and field_mapping.get('data_type') in ['entity_name', 'text_description']:
                        result = self._enhance_with_llm_analysis(result, field_mapping, lc_data, swift_data)
                    
                    inconsistencies.append(result)
                    logger.info(f"🚨 Found inconsistency in {display_name}: {result.severity} severity")
        
        return inconsistencies
    
    def _compare_field_values(self, lc_value: str, swift_value: str, field_mapping: Dict[str, Any]) -> InconsistencyResult:
        """Enhanced field value comparison with normalization and business rules"""
        display_name = field_mapping.get('display_name')
        data_type = field_mapping.get('data_type', 'text')
        similarity_threshold = field_mapping.get('similarity_threshold', 0.8)
        swift_field = field_mapping.get('swift_field', '')
        
        # Normalize values
        normalized_lc = self._normalize_field_value(lc_value, data_type, field_mapping.get('normalization_rules', []))
        normalized_swift = self._normalize_field_value(swift_value, data_type, field_mapping.get('normalization_rules', []))
        
        # Calculate similarity
        similarity_score = self._calculate_similarity(normalized_lc, normalized_swift, data_type)
        
        # Determine if this is an inconsistency
        is_inconsistency = similarity_score < similarity_threshold
        
        # Determine inconsistency type and severity
        inconsistency_type = self._classify_inconsistency_type(lc_value, swift_value, normalized_lc, normalized_swift, data_type)
        severity = self._determine_severity(inconsistency_type, field_mapping, similarity_score)
        
        # Calculate confidence score
        confidence_score = self._calculate_confidence_score(similarity_score, field_mapping, inconsistency_type)
        
        # Generate business impact and recommendations
        business_impact = self._assess_business_impact(field_mapping, inconsistency_type, severity)
        recommendation = self._generate_recommendation(field_mapping, inconsistency_type, lc_value, swift_value)
        resolution_steps = self._generate_resolution_steps(inconsistency_type, field_mapping)
        
        return InconsistencyResult(
            field_name=display_name,
            inconsistency_type=inconsistency_type,
            severity=severity,
            confidence_score=confidence_score,
            lc_value=lc_value,
            swift_value=swift_value,
            normalized_lc_value=normalized_lc,
            normalized_swift_value=normalized_swift,
            is_inconsistency=is_inconsistency,
            business_impact=business_impact,
            recommendation=recommendation,
            llm_reasoning="",  # Will be filled by LLM if enabled
            resolution_steps=resolution_steps,
            swift_reference=swift_field,
            category='field_comparison'
        )
    
    def _normalize_field_value(self, value: str, data_type: str, normalization_rules: List[str]) -> str:
        """Enhanced field value normalization"""
        if not value:
            return ""
        
        normalized = value.strip()
        
        # Apply data type specific normalization
        if data_type == 'entity_name':
            normalized = self._normalize_entity_name(normalized, normalization_rules)
        elif data_type == 'monetary_amount':
            normalized = self._normalize_monetary_amount(normalized, normalization_rules)
        elif data_type == 'date':
            normalized = self._normalize_date(normalized, normalization_rules)
        elif data_type == 'address':
            normalized = self._normalize_address(normalized, normalization_rules)
        elif data_type == 'text_description':
            normalized = self._normalize_text_description(normalized, normalization_rules)
        
        return normalized
    
    def _normalize_entity_name(self, name: str, rules: List[str]) -> str:
        """Normalize entity names (company names, bank names)"""
        normalized = name.upper().strip()
        
        if 'remove_legal_suffixes' in rules:
            suffixes = self.normalization_patterns.get('company_names', {}).get('suffixes_to_remove', [])
            for suffix in suffixes:
                pattern = rf'\b{re.escape(suffix.upper())}\b'
                normalized = re.sub(pattern, '', normalized).strip()
        
        if 'handle_abbreviations' in rules:
            abbrev_map = self.normalization_patterns.get('company_names', {}).get('abbreviation_mappings', {})
            for abbrev, full_form in abbrev_map.items():
                normalized = normalized.replace(abbrev.upper(), full_form.upper())
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized
    
    def _normalize_monetary_amount(self, amount: str, rules: List[str]) -> str:
        """Normalize monetary amounts"""
        if 'extract_numeric_value' in rules:
            # Extract numeric value and currency
            currency_match = re.search(r'[A-Z]{3}', amount)
            currency = currency_match.group() if currency_match else ''
            
            # Extract numeric value
            numeric_part = re.sub(r'[^\d.,]', '', amount)
            
            # Handle decimal separators
            if ',' in numeric_part and '.' in numeric_part:
                # Both present - assume European format (comma as decimal)
                numeric_part = numeric_part.replace(',', '')
            elif ',' in numeric_part:
                # Check if it's decimal or thousands separator
                if len(numeric_part.split(',')[-1]) <= 2:
                    numeric_part = numeric_part.replace(',', '.')
                else:
                    numeric_part = numeric_part.replace(',', '')
            
            try:
                numeric_value = float(numeric_part)
                return f"{currency}{numeric_value:.2f}" if currency else f"{numeric_value:.2f}"
            except ValueError:
                return amount
        
        return amount
    
    def _normalize_date(self, date_str: str, rules: List[str]) -> str:
        """Normalize date formats"""
        # Simple date normalization - could be enhanced with more sophisticated parsing
        date_patterns = [
            r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})',  # DD/MM/YYYY or DD-MM-YYYY
            r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})',  # YYYY/MM/DD or YYYY-MM-DD
            r'(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})',  # DD Mon YYYY
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, date_str, re.IGNORECASE)
            if match:
                try:
                    # Return standardized format YYYY-MM-DD
                    if len(match.groups()) == 3:
                        if match.group(1).isdigit() and len(match.group(1)) == 4:  # YYYY format
                            return f"{match.group(1)}-{match.group(2).zfill(2)}-{match.group(3).zfill(2)}"
                        else:  # DD/MM format
                            return f"{match.group(3)}-{match.group(2).zfill(2)}-{match.group(1).zfill(2)}"
                except:
                    pass
        
        return date_str
    
    def _normalize_address(self, address: str, rules: List[str]) -> str:
        """Normalize addresses"""
        normalized = address.upper().strip()
        
        # Replace common abbreviations
        abbreviations = {
            'STREET': 'ST', 'AVENUE': 'AVE', 'BOULEVARD': 'BLVD',
            'ROAD': 'RD', 'LANE': 'LN', 'DRIVE': 'DR'
        }
        
        for full_form, abbrev in abbreviations.items():
            normalized = normalized.replace(full_form, abbrev)
        
        return normalized
    
    def _normalize_text_description(self, text: str, rules: List[str]) -> str:
        """Normalize text descriptions"""
        normalized = text.strip()
        
        if 'standardize_product_names' in rules:
            # Could implement product name standardization logic
            pass
        
        if 'normalize_units' in rules:
            # Standardize units
            unit_mappings = {
                'kilogram': 'kg', 'kilometer': 'km', 'meter': 'm',
                'piece': 'pcs', 'pieces': 'pcs', 'unit': 'units'
            }
            for full_unit, abbrev in unit_mappings.items():
                normalized = re.sub(rf'\b{full_unit}s?\b', abbrev, normalized, flags=re.IGNORECASE)
        
        return normalized
    
    def _calculate_similarity(self, value1: str, value2: str, data_type: str) -> float:
        """Calculate similarity score between two values"""
        if not value1 or not value2:
            return 0.0
        
        if value1 == value2:
            return 1.0
        
        if data_type == 'monetary_amount':
            # For monetary amounts, extract numeric values and compare
            try:
                num1 = float(re.sub(r'[^\d.]', '', value1))
                num2 = float(re.sub(r'[^\d.]', '', value2))
                return 1.0 if abs(num1 - num2) < 0.01 else 0.0
            except ValueError:
                pass
        
        # Use sequence matcher for text similarity
        return SequenceMatcher(None, value1.lower(), value2.lower()).ratio()
    
    def _classify_inconsistency_type(self, lc_value: str, swift_value: str, 
                                   normalized_lc: str, normalized_swift: str, data_type: str) -> str:
        """Classify the type of inconsistency"""
        if normalized_lc == normalized_swift:
            return 'format_inconsistency'
        
        # Check for semantic similarity (would use LLM in real implementation)
        similarity = self._calculate_similarity(normalized_lc, normalized_swift, data_type)
        
        if similarity > 0.7:
            return 'semantic_inconsistency'
        elif data_type == 'monetary_amount':
            return 'value_mismatch'
        elif len(lc_value) > 0 and len(swift_value) > 0:
            return 'value_mismatch'
        else:
            return 'contextual_inconsistency'
    
    def _determine_severity(self, inconsistency_type: str, field_mapping: Dict[str, Any], similarity_score: float) -> str:
        """Determine severity based on inconsistency type and field importance"""
        if field_mapping.get('critical', False):
            return 'CRITICAL' if similarity_score < 0.5 else 'HIGH'
        
        type_config = self.inconsistency_types.get(inconsistency_type, {})
        severity_rules = type_config.get('severity_rules', {})
        
        if field_mapping.get('data_type') == 'monetary_amount':
            return severity_rules.get('monetary_fields', 'HIGH')
        
        return severity_rules.get('default', 'MEDIUM')
    
    def _calculate_confidence_score(self, similarity_score: float, field_mapping: Dict[str, Any], 
                                  inconsistency_type: str) -> float:
        """Calculate confidence score for the inconsistency detection"""
        base_confidence = (1 - similarity_score) * 100
        
        # Apply adjustment factors
        confidence_config = self.config.get('confidence_calculation', {})
        adjustment_factors = confidence_config.get('adjustment_factors', {})
        
        if field_mapping.get('critical', False):
            base_confidence *= adjustment_factors.get('critical_field', 1.0)
        
        return min(100.0, max(0.0, base_confidence))
    
    def _assess_business_impact(self, field_mapping: Dict[str, Any], inconsistency_type: str, severity: str) -> str:
        """Assess business impact of the inconsistency"""
        field_name = field_mapping.get('display_name', 'Unknown Field')
        
        impact_templates = {
            'CRITICAL': f"Critical inconsistency in {field_name} may cause payment delays, compliance violations, or transaction rejection.",
            'HIGH': f"High-priority inconsistency in {field_name} may cause processing delays and require manual intervention.",
            'MEDIUM': f"Medium-priority inconsistency in {field_name} should be reviewed and corrected to avoid potential issues.",
            'LOW': f"Low-priority inconsistency in {field_name} is a minor formatting issue that should be standardized."
        }
        
        return impact_templates.get(severity, f"Inconsistency in {field_name} requires review.")
    
    def _generate_recommendation(self, field_mapping: Dict[str, Any], inconsistency_type: str, 
                               lc_value: str, swift_value: str) -> str:
        """Generate specific recommendation for resolving the inconsistency"""
        field_name = field_mapping.get('display_name', 'field')
        
        if inconsistency_type == 'format_inconsistency':
            return f"Standardize {field_name} format. Use SWIFT MT700 format: '{swift_value}'"
        elif inconsistency_type == 'value_mismatch':
            return f"Verify and correct {field_name}. LC shows '{lc_value}' but SWIFT shows '{swift_value}'"
        elif inconsistency_type == 'semantic_inconsistency':
            return f"Review {field_name} for meaning consistency. Ensure both documents refer to the same entity/concept"
        else:
            return f"Review {field_name} inconsistency and align values between LC application and SWIFT message"
    
    def _generate_resolution_steps(self, inconsistency_type: str, field_mapping: Dict[str, Any]) -> List[str]:
        """Generate step-by-step resolution guide"""
        steps = [
            "1. Review the inconsistent field values in both documents",
            "2. Verify the correct value with supporting documentation",
            "3. Update the incorrect document with the verified value",
            "4. Ensure consistency across all related fields"
        ]
        
        if field_mapping.get('critical', False):
            steps.insert(1, "1.5. URGENT: This is a critical field - prioritize immediate resolution")
        
        return steps
    
    def _enhance_with_llm_analysis(self, result: InconsistencyResult, field_mapping: Dict[str, Any], 
                                 lc_data: Dict[str, Any], swift_data: Dict[str, Any]) -> InconsistencyResult:
        """Enhance analysis using LLM for complex cases"""
        try:
            prompt_config = self.config.get('llm_prompts', {}).get('field_comparison', {})
            system_prompt = prompt_config.get('system_prompt', '')
            user_prompt_template = prompt_config.get('user_prompt_template', '')
            
            # Prepare context for LLM
            context = {
                'field_name': result.field_name,
                'lc_value': result.lc_value,
                'swift_value': result.swift_value,
                'data_type': field_mapping.get('data_type', 'text'),
                'field_criticality': 'critical' if field_mapping.get('critical', False) else 'standard',
                'business_rules': ', '.join(field_mapping.get('business_rules', [])),
                'context': f"LC Application and SWIFT MT700 analysis for trade finance transaction"
            }
            
            user_prompt = user_prompt_template.format(**context)
            
            # Call LLM
            response = self._call_llm(system_prompt, user_prompt)
            
            if response:
                # Parse LLM response and enhance result
                llm_analysis = self._parse_llm_response(response)
                if llm_analysis:
                    result.llm_reasoning = llm_analysis.get('reasoning', '')
                    result.confidence_score = llm_analysis.get('confidence_score', result.confidence_score)
                    
                    # Override severity if LLM provides better assessment
                    if llm_analysis.get('severity'):
                        result.severity = llm_analysis.get('severity')
                    
                    # Enhance recommendation with LLM insights
                    if llm_analysis.get('recommendation'):
                        result.recommendation = llm_analysis.get('recommendation')
        
        except Exception as e:
            logger.error(f"LLM enhancement failed: {e}")
        
        return result
    
    def _call_llm(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        """Call LLM API for analysis"""
        try:
            from openai import OpenAI
            client = OpenAI()
            
            response = client.chat.completions.create(
                model=self.llm_config.get('model', 'gpt-4'),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.llm_config.get('temperature', 0.1),
                max_tokens=self.llm_config.get('max_tokens', 1000)
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM API call failed: {e}")
            return None
    
    def _parse_llm_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse LLM JSON response"""
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
        return None
    
    def _perform_contextual_analysis(self, lc_data: Dict[str, Any], swift_data: Dict[str, Any], 
                                   document_data: List[Dict] = None) -> List[InconsistencyResult]:
        """Perform contextual analysis using LLM"""
        # Implementation for contextual analysis
        return []
    
    def _validate_business_logic(self, lc_data: Dict[str, Any], swift_data: Dict[str, Any]) -> List[InconsistencyResult]:
        """Validate business logic rules"""
        inconsistencies = []
        
        for rule_name, rule_config in self.business_rules.items():
            violation = self._check_business_rule(rule_name, rule_config, lc_data, swift_data)
            if violation:
                inconsistencies.append(violation)
        
        return inconsistencies
    
    def _check_business_rule(self, rule_name: str, rule_config: Dict[str, Any], 
                           lc_data: Dict[str, Any], swift_data: Dict[str, Any]) -> Optional[InconsistencyResult]:
        """Check a specific business rule"""
        # Implementation for specific business rule checking
        return None
    
    def _detect_pattern_anomalies(self, lc_data: Dict[str, Any], swift_data: Dict[str, Any]) -> List[InconsistencyResult]:
        """Detect pattern anomalies and unusual data"""
        # Implementation for pattern detection
        return []
    
    def _analyze_cross_document_consistency(self, lc_data: Dict[str, Any], swift_data: Dict[str, Any], 
                                          document_data: List[Dict]) -> List[InconsistencyResult]:
        """Analyze consistency across multiple documents"""
        # Implementation for cross-document analysis
        return []
    
    def _rank_and_prioritize_inconsistencies(self, inconsistencies: List[InconsistencyResult]) -> List[InconsistencyResult]:
        """Rank and prioritize inconsistencies by severity and confidence"""
        severity_order = {'CRITICAL': 4, 'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}
        
        return sorted(inconsistencies, key=lambda x: (
            severity_order.get(x.severity, 0),
            x.confidence_score
        ), reverse=True)
    
    def _extract_field_value(self, data: Dict[str, Any], field_name: str) -> str:
        """Extract field value with fallback logic"""
        if not data or not field_name:
            return ''
        
        # Direct field lookup
        value = data.get(field_name, '').strip()
        if value:
            return value
        
        # Alternative field names based on common variations
        alternatives = {
            'applicant': ['applicant_name', 'applicant_details', 'buyer', 'orderer'],
            'beneficiary': ['beneficiary_name', 'beneficiary_details', 'seller', 'exporter'],
            'amount': ['lc_amount', 'credit_amount', 'total_amount', '32B'],
            'currency': ['lc_currency', 'credit_currency', 'ccy'],
            'goods_description': ['description_of_goods', 'merchandise_description', 'commodity']
        }
        
        for alt_field in alternatives.get(field_name, []):
            alt_value = data.get(alt_field, '').strip()
            if alt_value:
                return alt_value
        
        return ''

# Integration function for existing routes.py
def analyze_field_inconsistencies_enhanced(lc_data: Dict[str, Any], swift_data: Dict[str, Any], 
                                         document_data: List[Dict] = None) -> List[Dict[str, Any]]:
    """Enhanced inconsistency analysis function for integration with existing routes"""
    analyzer = EnhancedInconsistencyAnalyzer()
    results = analyzer.analyze_inconsistencies(lc_data, swift_data, document_data)
    
    # Convert InconsistencyResult objects to dictionaries for compatibility
    return [
        {
            'field': result.field_name,
            'source_document': 'LC Application Form',
            'target_document': 'SWIFT MT700 Message',
            'source_value': result.lc_value,
            'target_value': result.swift_value,
            'required_value': result.swift_value,
            'issue': f"{result.field_name} {result.inconsistency_type}: '{result.lc_value}' vs '{result.swift_value}'",
            'severity': result.severity,
            'recommendation': result.recommendation,
            'business_impact': result.business_impact,
            'category': result.inconsistency_type,
            'confidence': result.confidence_score,
            'swift_reference': result.swift_reference,
            'llm_reasoning': result.llm_reasoning,
            'resolution_steps': result.resolution_steps,
            'inconsistency_type': result.inconsistency_type,
            'normalized_lc_value': result.normalized_lc_value,
            'normalized_swift_value': result.normalized_swift_value
        }
        for result in results
    ]