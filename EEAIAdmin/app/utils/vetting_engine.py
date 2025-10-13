import json
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from pymongo import MongoClient
from bson import ObjectId
import logging
import openai
from .azure_openai_helper import get_openai_client

logger = logging.getLogger(__name__)

class VettingRuleEngine:
    """Custom rule engine for guarantee vetting"""
    
    def __init__(self, db):
        self.db = db
        self.rules_collection = db.vetting_rules
        self.test_results_collection = db.vetting_test_results
        self.llm_analyses_collection = db.vetting_llm_analyses
        
        # Create indexes
        self.rules_collection.create_index("created_by")
        self.rules_collection.create_index("is_active")
        self.test_results_collection.create_index("rule_id")
        self.llm_analyses_collection.create_index("rule_id")
        
        # Initialize OpenAI client with error handling
        try:
            self.openai_client = get_openai_client()
        except Exception as e:
            logger.warning(f"Failed to initialize OpenAI client: {e}")
            self.openai_client = None
        
    def create_rule(self, rule_data: Dict, user_email: str) -> Dict:
        """Create a new vetting rule"""
        rule = {
            "name": rule_data.get("name"),
            "description": rule_data.get("description"),
            "condition_type": rule_data.get("condition_type"),  # "contains", "not_contains", "equals", "regex", etc.
            "field": rule_data.get("field", "guarantee_text"),  # Field to check
            "value": rule_data.get("value"),  # Value to check against
            "severity": rule_data.get("severity", "medium"),  # low, medium, high
            "is_active": rule_data.get("is_active", True),
            "created_by": user_email,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "test_samples": rule_data.get("test_samples", {})
        }
        
        result = self.rules_collection.insert_one(rule)
        rule["_id"] = str(result.inserted_id)
        return rule
    
    def update_rule(self, rule_id: str, rule_data: Dict, user_email: str) -> Dict:
        """Update an existing rule"""
        update_data = {
            "updated_at": datetime.utcnow(),
            "updated_by": user_email
        }
        
        # Update allowed fields
        allowed_fields = ["name", "description", "condition_type", "field", "value", "severity", "is_active", "test_samples"]
        for field in allowed_fields:
            if field in rule_data:
                update_data[field] = rule_data[field]
        
        result = self.rules_collection.update_one(
            {"_id": ObjectId(rule_id)},
            {"$set": update_data}
        )
        
        if result.modified_count > 0:
            return self.get_rule(rule_id)
        return None
    
    def delete_rule(self, rule_id: str) -> bool:
        """Delete a rule"""
        result = self.rules_collection.delete_one({"_id": ObjectId(rule_id)})
        return result.deleted_count > 0
    
    def get_rule(self, rule_id: str) -> Dict:
        """Get a single rule"""
        rule = self.rules_collection.find_one({"_id": ObjectId(rule_id)})
        if rule:
            rule["_id"] = str(rule["_id"])
        return rule
    
    def get_all_rules(self, active_only: bool = False) -> List[Dict]:
        """Get all rules"""
        query = {"is_active": True} if active_only else {}
        rules = list(self.rules_collection.find(query))
        for rule in rules:
            rule["_id"] = str(rule["_id"])
        return rules
    
    def evaluate_condition(self, text: str, rule: Dict) -> bool:
        """Evaluate if a text matches a rule condition"""
        field_value = text  # For now, we're checking the entire text
        condition_type = rule.get("condition_type", "contains")
        check_value = rule.get("value", "")
        
        # Convert to lowercase for case-insensitive comparison
        field_value_lower = field_value.lower()
        check_value_lower = check_value.lower()
        
        if condition_type == "contains":
            return check_value_lower in field_value_lower
        elif condition_type == "not_contains":
            return check_value_lower not in field_value_lower
        elif condition_type == "equals":
            return field_value_lower == check_value_lower
        elif condition_type == "not_equals":
            return field_value_lower != check_value_lower
        elif condition_type == "starts_with":
            return field_value_lower.startswith(check_value_lower)
        elif condition_type == "ends_with":
            return field_value_lower.endswith(check_value_lower)
        elif condition_type == "regex":
            try:
                pattern = re.compile(check_value, re.IGNORECASE)
                return bool(pattern.search(field_value))
            except re.error:
                logger.error(f"Invalid regex pattern: {check_value}")
                return False
        elif condition_type == "greater_than":
            # For numeric comparisons
            try:
                return float(field_value) > float(check_value)
            except (ValueError, TypeError):
                return False
        elif condition_type == "less_than":
            try:
                return float(field_value) < float(check_value)
            except (ValueError, TypeError):
                return False
        
        return False
    
    def test_rule(self, rule_id: str, test_samples: List[Dict]) -> Dict:
        """Test a rule against sample texts"""
        rule = self.get_rule(rule_id)
        if not rule:
            return {"error": "Rule not found"}
        
        results = []
        for sample in test_samples:
            sample_text = sample.get("text", "")
            expected_result = sample.get("expected_onerous", False)
            
            # Evaluate the rule
            is_onerous = self.evaluate_condition(sample_text, rule)
            
            # Check if the result matches expected
            is_correct = is_onerous == expected_result
            
            results.append({
                "sample_text": sample_text[:200] + "..." if len(sample_text) > 200 else sample_text,
                "expected_onerous": expected_result,
                "actual_onerous": is_onerous,
                "is_correct": is_correct,
                "rule_triggered": is_onerous
            })
        
        # Store test results
        test_result = {
            "rule_id": rule_id,
            "rule_name": rule.get("name"),
            "test_date": datetime.utcnow(),
            "samples_tested": len(test_samples),
            "passed": all(r["is_correct"] for r in results),
            "results": results
        }
        
        self.test_results_collection.insert_one(test_result)
        
        return {
            "rule_id": rule_id,
            "rule_name": rule.get("name"),
            "test_passed": test_result["passed"],
            "results": results
        }
    
    def vet_guarantee_with_llm(self, guarantee_text: str, include_llm_analysis: bool = True) -> Dict:
        """Enhanced guarantee vetting with LLM analysis"""
        # First run rule-based vetting
        rule_based_result = self.vet_guarantee_basic(guarantee_text)
        
        if not include_llm_analysis:
            return rule_based_result
        
        try:
            # Get LLM analysis for additional insights
            llm_analysis = self.get_llm_vetting_analysis(guarantee_text, rule_based_result["triggered_rules"])
            
            # Combine results
            enhanced_result = {
                **rule_based_result,
                "llm_analysis": llm_analysis,
                "enhanced_with_llm": True
            }
            
            # Update severity based on LLM insights if needed
            if llm_analysis.get("suggested_severity") and llm_analysis.get("confidence", 0) > 0.7:
                suggested_severity = llm_analysis["suggested_severity"]
                severity_order = {"low": 0, "medium": 1, "high": 2}
                
                current_severity_score = severity_order.get(rule_based_result.get("overall_severity", "low"), 0)
                suggested_severity_score = severity_order.get(suggested_severity, 0)
                
                if suggested_severity_score > current_severity_score:
                    enhanced_result["overall_severity"] = suggested_severity
                    enhanced_result["severity_upgraded_by_llm"] = True
            
            return enhanced_result
            
        except Exception as e:
            logger.error(f"Error in LLM analysis: {e}")
            # Return rule-based result if LLM fails
            rule_based_result["llm_analysis_error"] = str(e)
            return rule_based_result
    
    def vet_guarantee_basic(self, guarantee_text: str) -> Dict:
        """Basic rule-based guarantee vetting"""
        active_rules = self.get_all_rules(active_only=True)
        
        triggered_rules = []
        overall_severity = "low"
        severity_order = {"low": 0, "medium": 1, "high": 2}
        
        for rule in active_rules:
            if self.evaluate_condition(guarantee_text, rule):
                triggered_rules.append({
                    "rule_id": str(rule["_id"]),
                    "rule_name": rule.get("name"),
                    "description": rule.get("description"),
                    "severity": rule.get("severity", "medium"),
                    "field": rule.get("field"),
                    "condition": f"{rule.get('condition_type')} '{rule.get('value')}'"
                })
                
                # Update overall severity
                rule_severity = rule.get("severity", "medium")
                if severity_order.get(rule_severity, 0) > severity_order.get(overall_severity, 0):
                    overall_severity = rule_severity
        
        is_onerous = len(triggered_rules) > 0
        
        return {
            "is_onerous": is_onerous,
            "overall_severity": overall_severity if is_onerous else None,
            "triggered_rules": triggered_rules,
            "total_rules_checked": len(active_rules),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def vet_guarantee(self, guarantee_text: str) -> Dict:
        """Vet a guarantee text against all active rules (with LLM enhancement)"""
        return self.vet_guarantee_with_llm(guarantee_text, include_llm_analysis=True)
    
    def get_llm_vetting_analysis(self, guarantee_text: str, triggered_rules: List[Dict]) -> Dict:
        """Get LLM analysis of guarantee text and triggered rules"""
        try:
            if not self.openai_client:
                return {
                    "error": "OpenAI client not available",
                    "overall_assessment": "AI analysis unavailable due to configuration issues",
                    "confidence": 0.0
                }
            rules_summary = "\n".join([
                f"- {rule['rule_name']}: {rule['description']} (Severity: {rule['severity']})"
                for rule in triggered_rules
            ]) if triggered_rules else "No rules triggered"
            
            prompt = f"""
            You are an expert in trade finance and guarantee analysis. Please analyze the following guarantee text for potential onerous conditions.

            GUARANTEE TEXT:
            {guarantee_text}

            TRIGGERED RULES:
            {rules_summary}

            Please provide your analysis in JSON format:
            {{
                "overall_assessment": "brief overall assessment of the guarantee",
                "onerous_conditions_found": ["list of specific onerous conditions you identify"],
                "risk_factors": ["list of risk factors beyond the triggered rules"],
                "suggested_severity": "low/medium/high",
                "confidence": 0.0-1.0,
                "recommendations": ["list of recommendations for handling this guarantee"],
                "additional_concerns": "any other concerns not covered by existing rules",
                "business_impact": "potential impact on business operations"
            }}

            Consider factors like:
            - Unusual payment conditions
            - Excessive liability provisions
            - Jurisdictional risks
            - Performance requirements
            - Financial exposure
            - Compliance implications
            """

            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,  # Lower temperature for more consistent analysis
                max_tokens=800
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Store the analysis
            analysis_record = {
                "guarantee_text_hash": str(hash(guarantee_text)),
                "analysis_type": "guarantee_vetting",
                "timestamp": datetime.utcnow(),
                "triggered_rules_count": len(triggered_rules),
                "llm_analysis": result,
                "model_used": "gpt-4"
            }
            self.llm_analyses_collection.insert_one(analysis_record)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in LLM vetting analysis: {e}")
            return {
                "error": str(e),
                "overall_assessment": "Analysis unavailable due to error",
                "confidence": 0.0
            }
    
    def generate_sample_texts_llm(self, rule: Dict) -> Tuple[str, str, Dict]:
        """Generate intelligent sample texts using LLM for testing a rule"""
        try:
            if not self.openai_client:
                logger.warning("OpenAI client not available, falling back to basic generation")
                return self.generate_sample_texts_basic(rule)
            prompt = f"""
            You are an expert in trade finance and guarantee vetting. Generate two realistic guarantee text samples for testing a vetting rule.

            Rule Details:
            - Name: {rule.get('name', 'Unnamed rule')}
            - Description: {rule.get('description', 'No description')}
            - Condition: {rule.get('condition_type', 'contains')} "{rule.get('value', '')}"
            - Severity: {rule.get('severity', 'medium')}

            Generate:
            1. ONEROUS SAMPLE: A guarantee text that SHOULD trigger this rule (be flagged as onerous)
            2. CLEAN SAMPLE: A guarantee text that should NOT trigger this rule (be considered acceptable)

            Requirements:
            - Each sample should be 100-200 words
            - Use realistic guarantee language and terminology
            - Include typical guarantee elements (amount, validity, conditions)
            - Make samples contextually appropriate for the rule being tested
            - Ensure the onerous sample clearly demonstrates why the rule would trigger
            - Ensure the clean sample is a proper guarantee that avoids the onerous condition

            Return your response in JSON format:
            {{
                "onerous_sample": "text that should trigger the rule...",
                "clean_sample": "text that should not trigger the rule...",
                "explanation": "brief explanation of why these samples test the rule effectively",
                "confidence": "high/medium/low"
            }}
            """

            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=1000
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Store the LLM analysis
            analysis = {
                "rule_id": str(rule.get("_id")),
                "rule_name": rule.get("name"),
                "analysis_type": "sample_generation",
                "timestamp": datetime.utcnow(),
                "prompt": prompt,
                "llm_response": result,
                "model_used": "gpt-4"
            }
            self.llm_analyses_collection.insert_one(analysis)
            
            return result["onerous_sample"], result["clean_sample"], {
                "explanation": result.get("explanation", ""),
                "confidence": result.get("confidence", "medium"),
                "llm_generated": True
            }
            
        except Exception as e:
            logger.error(f"Error generating LLM samples: {e}")
            # Fallback to basic generation
            return self.generate_sample_texts_basic(rule)
    
    def generate_sample_texts_basic(self, rule: Dict) -> Tuple[str, str, Dict]:
        """Generate basic sample texts (fallback method)"""
        condition_type = rule.get("condition_type", "contains")
        value = rule.get("value", "")
        
        # Generate onerous sample (should trigger the rule)
        if condition_type == "contains":
            onerous_sample = f"We hereby unconditionally guarantee to pay up to USD 1,000,000. This guarantee shall not be valid for beneficiaries from {value}. Payment shall be made upon first demand with your written statement."
        elif condition_type == "not_contains":
            onerous_sample = "We hereby guarantee payment up to USD 500,000. This guarantee is subject to standard terms and conditions without special restrictions."
        elif condition_type == "starts_with":
            onerous_sample = f"{value} We hereby issue this unconditional guarantee for USD 750,000 in favor of the beneficiary as security for contract performance."
        elif condition_type == "ends_with":
            onerous_sample = f"We unconditionally guarantee payment up to USD 1,200,000 upon first demand. This guarantee remains valid until contract completion {value}"
        else:
            onerous_sample = f"This bank guarantee includes the following condition: {value}. Amount guaranteed is USD 800,000."
        
        # Generate non-onerous sample (should NOT trigger the rule)
        if condition_type == "contains":
            non_onerous_sample = "We hereby unconditionally and irrevocably guarantee payment up to USD 1,000,000 to any eligible beneficiary worldwide, subject to standard international banking practices."
        elif condition_type == "not_contains":
            non_onerous_sample = f"This guarantee specifically acknowledges that {value} and shall be governed accordingly. Amount: USD 600,000."
        elif condition_type == "starts_with":
            non_onerous_sample = f"This unconditional guarantee covers USD 900,000. Important note: {value} applies to this guarantee as specified in the underlying contract."
        elif condition_type == "ends_with":
            non_onerous_sample = f"We guarantee payment of USD 1,100,000 upon presentation of compliant documents. Please note that {value} is referenced in clause 3 above."
        else:
            non_onerous_sample = "We hereby issue this unconditional bank guarantee for USD 1,000,000 in favor of the beneficiary, valid until contract completion."
        
        return onerous_sample, non_onerous_sample, {
            "explanation": "Basic samples generated using template patterns",
            "confidence": "medium",
            "llm_generated": False
        }

    def generate_sample_texts(self, rule: Dict) -> Tuple[str, str]:
        """Generate sample texts for testing a rule (backward compatibility)"""
        onerous, clean, _ = self.generate_sample_texts_llm(rule)
        return onerous, clean
    
    def get_test_history(self, rule_id: str = None) -> List[Dict]:
        """Get test history for a rule or all rules"""
        query = {"rule_id": rule_id} if rule_id else {}
        results = list(self.test_results_collection.find(query).sort("test_date", -1).limit(50))
        
        for result in results:
            result["_id"] = str(result["_id"])
        
        return results
    
    def get_rule_explanation(self, rule_config: Dict) -> str:
        """Generate AI explanation for a rule configuration"""
        try:
            if not self.openai_client:
                return "This rule will help identify specific conditions in guarantee texts based on your configuration. The AI explanation service is temporarily unavailable."
            condition_type = rule_config.get("condition_type", "")
            value = rule_config.get("value", "")
            severity = rule_config.get("severity", "medium")
            name = rule_config.get("name", "")
            description = rule_config.get("description", "")
            
            prompt = f"""
            You are an expert in trade finance and guarantee vetting. Provide a clear, concise explanation of this vetting rule configuration.

            Rule Configuration:
            - Name: {name}
            - Description: {description}
            - Condition: {condition_type} "{value}"
            - Severity: {severity}

            Please explain:
            1. What this rule does and why it's important in guarantee vetting
            2. What specific risks or issues this rule helps identify
            3. How effective this rule configuration might be
            4. Any potential limitations or considerations

            Keep your explanation under 150 words, professional, and focused on practical implications for trade finance professionals.
            """

            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=200
            )
            
            explanation = response.choices[0].message.content.strip()
            
            # Store the explanation for analytics
            explanation_record = {
                "rule_config": rule_config,
                "explanation_type": "rule_configuration",
                "timestamp": datetime.utcnow(),
                "explanation": explanation,
                "model_used": "gpt-4"
            }
            self.llm_analyses_collection.insert_one(explanation_record)
            
            return explanation
            
        except Exception as e:
            logger.error(f"Error generating rule explanation: {e}")
            return "This rule will help identify specific conditions in guarantee texts based on your configuration. The AI explanation service is temporarily unavailable."
    
    def get_rule_effectiveness_score(self, rule_id: str) -> Dict:
        """Analyze rule effectiveness using LLM insights"""
        try:
            if not self.openai_client:
                return {
                    "error": "OpenAI client not available",
                    "effectiveness_score": 0.5,
                    "confidence": 0.0,
                    "analysis": "AI effectiveness analysis unavailable due to configuration issues"
                }
            rule = self.get_rule(rule_id)
            if not rule:
                return {"error": "Rule not found"}
            
            # Get test history for this rule
            test_history = self.get_test_history(rule_id)
            
            # Calculate basic metrics
            total_tests = len(test_history)
            if total_tests == 0:
                return {
                    "effectiveness_score": 0.0,
                    "confidence": 0.0,
                    "analysis": "No test data available for analysis"
                }
            
            passed_tests = sum(1 for test in test_history if test.get("passed", False))
            accuracy_rate = passed_tests / total_tests if total_tests > 0 else 0
            
            # Get LLM analysis of rule effectiveness
            prompt = f"""
            You are an expert in trade finance and guarantee vetting. Analyze the effectiveness of this vetting rule based on its configuration and test results.

            Rule Details:
            - Name: {rule.get('name')}
            - Description: {rule.get('description')}
            - Condition: {rule.get('condition_type')} "{rule.get('value')}"
            - Severity: {rule.get('severity')}
            - Created: {rule.get('created_at')}

            Test Results Summary:
            - Total tests conducted: {total_tests}
            - Tests passed: {passed_tests}
            - Accuracy rate: {accuracy_rate:.1%}

            Please provide your analysis in JSON format:
            {{
                "effectiveness_score": 0.0-1.0,
                "confidence": 0.0-1.0,
                "strengths": ["list of rule strengths"],
                "weaknesses": ["list of rule weaknesses"],
                "improvement_suggestions": ["list of suggestions"],
                "risk_coverage": "assessment of what risks this rule covers",
                "overall_assessment": "brief overall assessment"
            }}

            Consider:
            - How well the rule condition captures the intended risk
            - Appropriateness of severity level
            - Potential for false positives/negatives
            - Coverage of edge cases
            - Alignment with trade finance best practices
            """

            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=600
            )
            
            llm_analysis = json.loads(response.choices[0].message.content)
            
            # Combine basic metrics with LLM analysis
            effectiveness_data = {
                "rule_id": rule_id,
                "rule_name": rule.get("name"),
                "basic_metrics": {
                    "total_tests": total_tests,
                    "passed_tests": passed_tests,
                    "accuracy_rate": accuracy_rate
                },
                "llm_analysis": llm_analysis,
                "combined_score": (accuracy_rate + llm_analysis.get("effectiveness_score", 0.5)) / 2,
                "timestamp": datetime.utcnow()
            }
            
            # Store the effectiveness analysis
            effectiveness_record = {
                "rule_id": rule_id,
                "analysis_type": "effectiveness_scoring",
                "timestamp": datetime.utcnow(),
                "effectiveness_data": effectiveness_data,
                "model_used": "gpt-4"
            }
            self.llm_analyses_collection.insert_one(effectiveness_record)
            
            return effectiveness_data
            
        except Exception as e:
            logger.error(f"Error analyzing rule effectiveness: {e}")
            return {
                "error": str(e),
                "effectiveness_score": 0.5,
                "confidence": 0.0,
                "analysis": "Unable to analyze rule effectiveness at this time"
            }
    
    def analyze_rule_effectiveness(self, rule_id: str) -> Dict:
        """Analyze rule effectiveness - alias for get_rule_effectiveness_score for backward compatibility"""
        return self.get_rule_effectiveness_score(rule_id)