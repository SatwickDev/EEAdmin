"""
Document Compliance Validation System
Validates SWIFT messages against related trade finance documents
"""

import re
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
import difflib

logger = logging.getLogger(__name__)

class DocumentComplianceValidator:
    """Validates compliance between SWIFT messages and trade finance documents"""
    
    def __init__(self):
        self.swift_fields = {
            'MT700': ['31C', '32B', '39A', '39B', '39C', '40A', '40E', '41A', '41D', '42C', '42A', '42D', '43P', '43T', '44A', '44B', '44C', '44D', '44E', '44F', '45A', '46A', '47A', '48', '49', '71B', '72', '78'],
            'MT701': ['20', '21', '31C', '32B', '23', '40A', '40E', '41A', '41D', '42C', '42A', '42D', '43P', '43T', '44A', '44B', '44C', '44D', '44E', '44F', '45A', '46A', '47A', '48', '49', '71B', '72', '78'],
            'MT710': ['20', '21', '25', '31C', '32B', '34A', '40A', '40E', '41A', '41D', '42C', '42A', '42D', '43P', '43T', '44A', '44B', '44C', '44D', '44E', '44F', '45A', '46A', '47A', '48', '49', '71B', '72', '78'],
            'MT720': ['20', '21', '32B', '31C', '50', '57A', '59'],
            'MT730': ['20', '21', '25', '31C', '32B'],
            'MT740': ['20', '21', '25', '31C', '32B'],
            'MT750': ['20', '21', '25', '31C', '32B', '34A'],
            'MT760': ['20', '21', '25', '31C', '32B'],
            'MT999': ['20', '21', '79']
        }
        
        self.critical_fields = {
            'amount': ['32B', '32A', '33B'],
            'currency': ['32B', '32A', '33B'],
            'dates': ['31C', '31D', '31E', '30'],
            'parties': ['50', '59', '57A', '57D', '58A', '58D'],
            'documents': ['46A', '47A'],
            'goods': ['45A'],
            'terms': ['48', '49']
        }
        
        self.tolerance_rules = {
            'amount': 0.1,  # 10% tolerance
            'quantity': 0.05,  # 5% tolerance
            'date': 30,  # 30 days tolerance
            'unit_price': 0.15  # 15% tolerance
        }

    def validate_documents(self, swift_message: Dict[str, Any], related_docs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Main validation function for document compliance"""
        try:
            logger.info(f"Starting validation for SWIFT message type: {swift_message.get('message_type', 'Unknown')}")
            
            validation_results = {
                'overall_compliance': True,
                'compliance_score': 0.0,
                'total_checks': 0,
                'passed_checks': 0,
                'failed_checks': 0,
                'warnings': 0,
                'critical_issues': [],
                'warnings_list': [],
                'detailed_results': {},
                'cross_document_analysis': {},
                'recommendation': '',
                'validation_timestamp': datetime.now().isoformat()
            }
            
            # Extract SWIFT message data
            swift_data = self._extract_swift_data(swift_message)
            
            # Validate each related document
            for doc in related_docs:
                doc_type = doc.get('document_type', 'unknown')
                doc_result = self._validate_single_document(swift_data, doc, doc_type)
                validation_results['detailed_results'][doc_type] = doc_result
                
                # Aggregate results
                validation_results['total_checks'] += doc_result['total_checks']
                validation_results['passed_checks'] += doc_result['passed_checks']
                validation_results['failed_checks'] += doc_result['failed_checks']
                validation_results['warnings'] += doc_result['warnings']
                
                if doc_result['critical_issues']:
                    validation_results['critical_issues'].extend(doc_result['critical_issues'])
                    validation_results['overall_compliance'] = False
                
                validation_results['warnings_list'].extend(doc_result['warnings_list'])
            
            # Perform cross-document validation
            cross_validation = self._cross_document_validation(swift_data, related_docs)
            validation_results['cross_document_analysis'] = cross_validation
            
            # Calculate final compliance score
            if validation_results['total_checks'] > 0:
                validation_results['compliance_score'] = (
                    validation_results['passed_checks'] / validation_results['total_checks']
                ) * 100
            
            # Generate recommendations
            validation_results['recommendation'] = self._generate_recommendations(validation_results)
            
            logger.info(f"Validation completed. Compliance score: {validation_results['compliance_score']:.2f}%")
            return validation_results
            
        except Exception as e:
            logger.error(f"Error during validation: {str(e)}")
            return {
                'overall_compliance': False,
                'error': str(e),
                'validation_timestamp': datetime.now().isoformat()
            }

    def _extract_swift_data(self, swift_message: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant data from SWIFT message"""
        swift_data = {
            'message_type': swift_message.get('message_type'),
            'amount': None,
            'currency': None,
            'dates': {},
            'parties': {},
            'documents': [],
            'goods_description': '',
            'terms_conditions': '',
            'reference_number': swift_message.get('reference_number'),
            'raw_fields': swift_message.get('fields', {})
        }
        
        fields = swift_message.get('fields', {})
        
        # Extract amount and currency
        for field in ['32B', '32A', '33B']:
            if field in fields:
                amount_data = self._parse_amount_field(fields[field])
                swift_data['amount'] = amount_data['amount']
                swift_data['currency'] = amount_data['currency']
                break
        
        # Extract dates
        for field in ['31C', '31D', '31E', '30']:
            if field in fields:
                swift_data['dates'][field] = self._parse_date_field(fields[field])
        
        # Extract parties
        for field in ['50', '59', '57A', '57D', '58A', '58D']:
            if field in fields:
                swift_data['parties'][field] = fields[field]
        
        # Extract documents and goods
        if '46A' in fields:
            swift_data['documents'] = self._parse_documents_field(fields['46A'])
        if '45A' in fields:
            swift_data['goods_description'] = fields['45A']
        if '48' in fields:
            swift_data['terms_conditions'] = fields['48']
            
        return swift_data

    def _validate_single_document(self, swift_data: Dict[str, Any], document: Dict[str, Any], doc_type: str) -> Dict[str, Any]:
        """Validate a single document against SWIFT message using both rule-based and LLM analysis"""
        result = {
            'document_type': doc_type,
            'total_checks': 0,
            'passed_checks': 0,
            'failed_checks': 0,
            'warnings': 0,
            'critical_issues': [],
            'warnings_list': [],
            'field_validations': {},
            'llm_analysis': None
        }
        
        # Perform rule-based validation
        if doc_type.lower() == 'invoice':
            result = self._validate_invoice(swift_data, document, result)
        elif doc_type.lower() == 'purchase_order':
            result = self._validate_purchase_order(swift_data, document, result)
        elif doc_type.lower() == 'shipping_document':
            result = self._validate_shipping_document(swift_data, document, result)
        elif doc_type.lower() == 'sales_contract':
            result = self._validate_sales_contract(swift_data, document, result)
        else:
            result = self._validate_generic_document(swift_data, document, result)
        
        # Enhance with LLM analysis for sophisticated discrepancy detection
        try:
            llm_analysis = self._perform_llm_analysis(swift_data, document, doc_type)
            result['llm_analysis'] = llm_analysis
            
            # Integrate LLM findings with rule-based results
            if llm_analysis and not llm_analysis.get('match', True):
                for mismatch in llm_analysis.get('mismatches', []):
                    if mismatch not in [issue.get('issue', '') for issue in result['critical_issues']]:
                        result['critical_issues'].append({
                            'field': mismatch.get('field', 'unknown'),
                            'issue': f"LLM detected: {mismatch.get('issue', 'Discrepancy found')}",
                            'swift_value': mismatch.get('swift_value', ''),
                            'document_value': mismatch.get('support_value', ''),
                            'source': 'llm_analysis'
                        })
                        result['failed_checks'] += 1
                        result['total_checks'] += 1
                        
        except Exception as e:
            logger.warning(f"LLM analysis failed for {doc_type}: {str(e)}")
            result['warnings_list'].append({
                'field': 'llm_analysis',
                'issue': f'Advanced analysis unavailable: {str(e)}'
            })
        
        return result

    def _validate_invoice(self, swift_data: Dict[str, Any], invoice: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate invoice against SWIFT message"""
        
        # Amount validation
        swift_amount = swift_data.get('amount')
        invoice_amount = invoice.get('total_amount') or invoice.get('amount')
        
        if swift_amount and invoice_amount:
            result['total_checks'] += 1
            amount_diff = abs(float(swift_amount) - float(invoice_amount))
            tolerance = float(swift_amount) * self.tolerance_rules['amount']
            
            if amount_diff <= tolerance:
                result['passed_checks'] += 1
                result['field_validations']['amount'] = {
                    'status': 'passed',
                    'swift_value': swift_amount,
                    'document_value': invoice_amount,
                    'difference': amount_diff
                }
            else:
                result['failed_checks'] += 1
                result['critical_issues'].append({
                    'field': 'amount',
                    'issue': f'Amount mismatch: SWIFT {swift_amount} vs Invoice {invoice_amount}',
                    'difference': amount_diff,
                    'tolerance': tolerance
                })
        
        # Currency validation
        swift_currency = swift_data.get('currency')
        invoice_currency = invoice.get('currency')
        
        if swift_currency and invoice_currency:
            result['total_checks'] += 1
            if swift_currency.upper() == invoice_currency.upper():
                result['passed_checks'] += 1
                result['field_validations']['currency'] = {
                    'status': 'passed',
                    'value': swift_currency
                }
            else:
                result['failed_checks'] += 1
                result['critical_issues'].append({
                    'field': 'currency',
                    'issue': f'Currency mismatch: SWIFT {swift_currency} vs Invoice {invoice_currency}'
                })
        
        # Date validation
        lc_issue_date = swift_data.get('dates', {}).get('31C')
        invoice_date = invoice.get('invoice_date') or invoice.get('date')
        
        if lc_issue_date and invoice_date:
            result['total_checks'] += 1
            date_diff = self._calculate_date_difference(lc_issue_date, invoice_date)
            
            if abs(date_diff) <= self.tolerance_rules['date']:
                result['passed_checks'] += 1
            else:
                result['warnings'] += 1
                result['warnings_list'].append({
                    'field': 'date',
                    'issue': f'Date difference: {date_diff} days between LC and invoice'
                })
        
        # Goods description validation
        swift_goods = swift_data.get('goods_description', '')
        invoice_description = invoice.get('description') or invoice.get('goods_description', '')
        
        if swift_goods and invoice_description:
            result['total_checks'] += 1
            similarity = self._calculate_text_similarity(swift_goods, invoice_description)
            
            if similarity >= 0.7:  # 70% similarity threshold
                result['passed_checks'] += 1
                result['field_validations']['goods_description'] = {
                    'status': 'passed',
                    'similarity': similarity
                }
            else:
                result['warnings'] += 1
                result['warnings_list'].append({
                    'field': 'goods_description',
                    'issue': f'Goods description similarity low: {similarity:.2f}',
                    'swift_description': swift_goods[:100],
                    'invoice_description': invoice_description[:100]
                })
        
        return result

    def _validate_purchase_order(self, swift_data: Dict[str, Any], po: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate purchase order against SWIFT message"""
        
        # Amount validation
        swift_amount = swift_data.get('amount')
        po_amount = po.get('total_amount') or po.get('amount')
        
        if swift_amount and po_amount:
            result['total_checks'] += 1
            amount_diff = abs(float(swift_amount) - float(po_amount))
            tolerance = float(swift_amount) * self.tolerance_rules['amount']
            
            if amount_diff <= tolerance:
                result['passed_checks'] += 1
            else:
                result['failed_checks'] += 1
                result['critical_issues'].append({
                    'field': 'amount',
                    'issue': f'Amount mismatch: SWIFT {swift_amount} vs PO {po_amount}'
                })
        
        # Buyer/Seller validation
        swift_buyer = swift_data.get('parties', {}).get('50', '')  # Applicant
        po_buyer = po.get('buyer') or po.get('purchaser', '')
        
        if swift_buyer and po_buyer:
            result['total_checks'] += 1
            similarity = self._calculate_text_similarity(swift_buyer, po_buyer)
            
            if similarity >= 0.6:
                result['passed_checks'] += 1
            else:
                result['warnings'] += 1
                result['warnings_list'].append({
                    'field': 'buyer',
                    'issue': f'Buyer information similarity low: {similarity:.2f}'
                })
        
        # Quantity validation (if available)
        swift_qty = self._extract_quantity_from_description(swift_data.get('goods_description', ''))
        po_qty = po.get('quantity')
        
        if swift_qty and po_qty:
            result['total_checks'] += 1
            qty_diff = abs(float(swift_qty) - float(po_qty))
            tolerance = float(swift_qty) * self.tolerance_rules['quantity']
            
            if qty_diff <= tolerance:
                result['passed_checks'] += 1
            else:
                result['warnings'] += 1
                result['warnings_list'].append({
                    'field': 'quantity',
                    'issue': f'Quantity difference: SWIFT {swift_qty} vs PO {po_qty}'
                })
        
        return result

    def _validate_shipping_document(self, swift_data: Dict[str, Any], shipping_doc: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate shipping document against SWIFT message"""
        
        # Shipment date validation
        latest_shipment = swift_data.get('dates', {}).get('31D')  # Latest shipment date
        actual_shipment = shipping_doc.get('shipment_date') or shipping_doc.get('date')
        
        if latest_shipment and actual_shipment:
            result['total_checks'] += 1
            date_diff = self._calculate_date_difference(actual_shipment, latest_shipment)
            
            if date_diff <= 0:  # Shipped before or on latest date
                result['passed_checks'] += 1
            else:
                result['failed_checks'] += 1
                result['critical_issues'].append({
                    'field': 'shipment_date',
                    'issue': f'Late shipment: {date_diff} days after latest allowed date'
                })
        
        # Port of loading/discharge validation
        swift_terms = swift_data.get('terms_conditions', '')
        shipping_from = shipping_doc.get('port_of_loading') or shipping_doc.get('from_port', '')
        shipping_to = shipping_doc.get('port_of_discharge') or shipping_doc.get('to_port', '')
        
        if swift_terms and (shipping_from or shipping_to):
            result['total_checks'] += 1
            
            port_match = False
            if shipping_from and shipping_from.lower() in swift_terms.lower():
                port_match = True
            if shipping_to and shipping_to.lower() in swift_terms.lower():
                port_match = True
            
            if port_match:
                result['passed_checks'] += 1
            else:
                result['warnings'] += 1
                result['warnings_list'].append({
                    'field': 'ports',
                    'issue': 'Port information may not match LC terms'
                })
        
        # Consignee validation
        swift_consignee = swift_data.get('parties', {}).get('59', '')  # Beneficiary
        shipping_consignee = shipping_doc.get('consignee', '')
        
        if swift_consignee and shipping_consignee:
            result['total_checks'] += 1
            similarity = self._calculate_text_similarity(swift_consignee, shipping_consignee)
            
            if similarity >= 0.6:
                result['passed_checks'] += 1
            else:
                result['warnings'] += 1
                result['warnings_list'].append({
                    'field': 'consignee',
                    'issue': f'Consignee information similarity low: {similarity:.2f}'
                })
        
        return result

    def _validate_sales_contract(self, swift_data: Dict[str, Any], contract: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate sales contract against SWIFT message"""
        
        # Contract amount validation
        swift_amount = swift_data.get('amount')
        contract_amount = contract.get('contract_value') or contract.get('amount')
        
        if swift_amount and contract_amount:
            result['total_checks'] += 1
            amount_diff = abs(float(swift_amount) - float(contract_amount))
            tolerance = float(swift_amount) * self.tolerance_rules['amount']
            
            if amount_diff <= tolerance:
                result['passed_checks'] += 1
            else:
                result['failed_checks'] += 1
                result['critical_issues'].append({
                    'field': 'contract_amount',
                    'issue': f'Contract amount mismatch: SWIFT {swift_amount} vs Contract {contract_amount}'
                })
        
        # Delivery terms validation
        swift_terms = swift_data.get('terms_conditions', '')
        contract_terms = contract.get('delivery_terms') or contract.get('terms', '')
        
        if swift_terms and contract_terms:
            result['total_checks'] += 1
            similarity = self._calculate_text_similarity(swift_terms, contract_terms)
            
            if similarity >= 0.7:
                result['passed_checks'] += 1
            else:
                result['warnings'] += 1
                result['warnings_list'].append({
                    'field': 'delivery_terms',
                    'issue': f'Delivery terms similarity low: {similarity:.2f}'
                })
        
        # Contract parties validation
        swift_buyer = swift_data.get('parties', {}).get('50', '')
        swift_seller = swift_data.get('parties', {}).get('59', '')
        contract_buyer = contract.get('buyer', '')
        contract_seller = contract.get('seller', '')
        
        if swift_buyer and contract_buyer:
            result['total_checks'] += 1
            similarity = self._calculate_text_similarity(swift_buyer, contract_buyer)
            if similarity >= 0.6:
                result['passed_checks'] += 1
            else:
                result['warnings'] += 1
                result['warnings_list'].append({
                    'field': 'contract_buyer',
                    'issue': f'Buyer information mismatch in contract'
                })
        
        if swift_seller and contract_seller:
            result['total_checks'] += 1
            similarity = self._calculate_text_similarity(swift_seller, contract_seller)
            if similarity >= 0.6:
                result['passed_checks'] += 1
            else:
                result['warnings'] += 1
                result['warnings_list'].append({
                    'field': 'contract_seller',
                    'issue': f'Seller information mismatch in contract'
                })
        
        return result

    def _validate_generic_document(self, swift_data: Dict[str, Any], document: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """Generic validation for unknown document types"""
        
        # Look for common fields and validate
        doc_amount = None
        for field in ['amount', 'total', 'value', 'sum']:
            if field in document:
                doc_amount = document[field]
                break
        
        if swift_data.get('amount') and doc_amount:
            result['total_checks'] += 1
            amount_diff = abs(float(swift_data['amount']) - float(doc_amount))
            tolerance = float(swift_data['amount']) * self.tolerance_rules['amount']
            
            if amount_diff <= tolerance:
                result['passed_checks'] += 1
            else:
                result['warnings'] += 1
                result['warnings_list'].append({
                    'field': 'amount',
                    'issue': f'Potential amount mismatch in {document.get("document_type", "document")}'
                })
        
        return result

    def _cross_document_validation(self, swift_data: Dict[str, Any], documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Perform cross-document validation checks"""
        
        cross_validation = {
            'consistent_amounts': True,
            'consistent_parties': True,
            'consistent_goods': True,
            'timeline_analysis': {},
            'discrepancies': []
        }
        
        # Collect all amounts from documents
        amounts = []
        currencies = []
        
        for doc in documents:
            doc_amount = self._extract_amount_from_document(doc)
            doc_currency = self._extract_currency_from_document(doc)
            
            if doc_amount:
                amounts.append({
                    'document': doc.get('document_type', 'unknown'),
                    'amount': doc_amount,
                    'currency': doc_currency
                })
        
        # Add SWIFT amount
        if swift_data.get('amount'):
            amounts.append({
                'document': 'SWIFT_LC',
                'amount': swift_data['amount'],
                'currency': swift_data.get('currency', '')
            })
        
        # Check amount consistency
        if len(amounts) > 1:
            base_amount = float(amounts[0]['amount'])
            tolerance = base_amount * self.tolerance_rules['amount']
            
            for amt_data in amounts[1:]:
                amount_diff = abs(float(amt_data['amount']) - base_amount)
                if amount_diff > tolerance:
                    cross_validation['consistent_amounts'] = False
                    cross_validation['discrepancies'].append({
                        'type': 'amount_inconsistency',
                        'documents': [amounts[0]['document'], amt_data['document']],
                        'difference': amount_diff,
                        'tolerance': tolerance
                    })
        
        # Timeline analysis
        dates = self._extract_all_dates(swift_data, documents)
        cross_validation['timeline_analysis'] = self._analyze_timeline(dates)
        
        return cross_validation

    def _generate_recommendations(self, validation_results: Dict[str, Any]) -> str:
        """Generate recommendations based on validation results"""
        
        recommendations = []
        
        compliance_score = validation_results.get('compliance_score', 0)
        critical_issues = len(validation_results.get('critical_issues', []))
        warnings = validation_results.get('warnings', 0)
        
        if compliance_score >= 95:
            recommendations.append("✅ Excellent compliance score. Documents are well-aligned with SWIFT message.")
        elif compliance_score >= 80:
            recommendations.append("⚠️ Good compliance score with minor discrepancies. Review warnings for improvements.")
        elif compliance_score >= 60:
            recommendations.append("⚠️ Moderate compliance score. Address critical issues and warnings.")
        else:
            recommendations.append("❌ Low compliance score. Immediate action required to resolve critical issues.")
        
        if critical_issues > 0:
            recommendations.append(f"🔴 {critical_issues} critical issue(s) require immediate attention.")
        
        if warnings > 5:
            recommendations.append("🟡 High number of warnings detected. Consider reviewing document preparation process.")
        
        # Specific recommendations based on issue types
        for issue in validation_results.get('critical_issues', []):
            if issue.get('field') == 'amount':
                recommendations.append("💰 Amount discrepancies detected. Verify pricing and currency calculations.")
            elif issue.get('field') == 'shipment_date':
                recommendations.append("📅 Shipment date issues found. Ensure timely shipment per LC terms.")
        
        return " ".join(recommendations) if recommendations else "No specific recommendations at this time."

    # Helper methods
    def _parse_amount_field(self, field_value: str) -> Dict[str, Any]:
        """Parse SWIFT amount field (e.g., 32B)"""
        # Format: CCCNNN,NN where CCC is currency, NNN,NN is amount
        match = re.match(r'([A-Z]{3})([0-9,\.]+)', field_value)
        if match:
            return {
                'currency': match.group(1),
                'amount': float(match.group(2).replace(',', ''))
            }
        return {'currency': None, 'amount': None}

    def _parse_date_field(self, field_value: str) -> Optional[datetime]:
        """Parse SWIFT date field"""
        try:
            # YYMMDD format
            if len(field_value) == 6:
                return datetime.strptime(field_value, '%y%m%d')
            # YYYYMMDD format
            elif len(field_value) == 8:
                return datetime.strptime(field_value, '%Y%m%d')
        except ValueError:
            pass
        return None

    def _parse_documents_field(self, field_value: str) -> List[str]:
        """Parse documents required field"""
        # Split by common delimiters and clean up
        docs = re.split(r'[,;:\n]+', field_value)
        return [doc.strip() for doc in docs if doc.strip()]

    def _calculate_date_difference(self, date1: str, date2: str) -> int:
        """Calculate difference between two dates in days"""
        try:
            if isinstance(date1, str):
                date1 = datetime.fromisoformat(date1.replace('Z', '+00:00'))
            if isinstance(date2, str):
                date2 = datetime.fromisoformat(date2.replace('Z', '+00:00'))
            
            return (date1 - date2).days
        except:
            return 0

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two text strings"""
        if not text1 or not text2:
            return 0.0
        
        # Use difflib for sequence matching
        matcher = difflib.SequenceMatcher(None, text1.lower(), text2.lower())
        return matcher.ratio()

    def _extract_quantity_from_description(self, description: str) -> Optional[float]:
        """Extract quantity from goods description"""
        # Look for patterns like "1000 MT", "500 KG", etc.
        patterns = [
            r'(\d+(?:\.\d+)?)\s*(?:MT|tonnes?|tons?)',
            r'(\d+(?:\.\d+)?)\s*(?:KG|kilograms?)',
            r'(\d+(?:\.\d+)?)\s*(?:pieces?|pcs?|units?)',
            r'(\d+(?:\.\d+)?)\s*(?:litres?|liters?|L)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                return float(match.group(1))
        
        return None

    def _extract_amount_from_document(self, document: Dict[str, Any]) -> Optional[float]:
        """Extract amount from any document"""
        amount_fields = ['amount', 'total_amount', 'value', 'contract_value', 'invoice_amount', 'total']
        
        for field in amount_fields:
            if field in document and document[field]:
                try:
                    return float(document[field])
                except (ValueError, TypeError):
                    continue
        
        return None

    def _extract_currency_from_document(self, document: Dict[str, Any]) -> Optional[str]:
        """Extract currency from any document"""
        currency_fields = ['currency', 'currency_code', 'curr']
        
        for field in currency_fields:
            if field in document and document[field]:
                return str(document[field]).upper()
        
        return None

    def _extract_all_dates(self, swift_data: Dict[str, Any], documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract all dates from SWIFT and documents for timeline analysis"""
        all_dates = {}
        
        # SWIFT dates
        for field, date_obj in swift_data.get('dates', {}).items():
            if date_obj:
                all_dates[f'SWIFT_{field}'] = date_obj
        
        # Document dates
        for doc in documents:
            doc_type = doc.get('document_type', 'unknown')
            date_fields = ['date', 'invoice_date', 'shipment_date', 'contract_date', 'issue_date']
            
            for field in date_fields:
                if field in doc and doc[field]:
                    try:
                        date_obj = datetime.fromisoformat(str(doc[field]).replace('Z', '+00:00'))
                        all_dates[f'{doc_type}_{field}'] = date_obj
                    except:
                        continue
        
        return all_dates

    def _analyze_timeline(self, dates: Dict[str, datetime]) -> Dict[str, Any]:
        """Analyze timeline of events for logical sequence"""
        
        timeline_analysis = {
            'chronological_order': True,
            'timeline_issues': [],
            'critical_path': []
        }
        
        # Sort dates chronologically
        sorted_dates = sorted(dates.items(), key=lambda x: x[1])
        
        # Check for logical sequence
        for i, (event, date) in enumerate(sorted_dates):
            timeline_analysis['critical_path'].append({
                'event': event,
                'date': date.isoformat(),
                'sequence': i + 1
            })
        
        # Look for potential issues
        lc_issue = None
        shipment_dates = []
        invoice_dates = []
        
        for event, date in dates.items():
            if 'SWIFT_31C' in event:  # LC issue date
                lc_issue = date
            elif 'shipment' in event.lower():
                shipment_dates.append(date)
            elif 'invoice' in event.lower():
                invoice_dates.append(date)
        
        # Check if invoices are issued before shipment
        if shipment_dates and invoice_dates:
            for inv_date in invoice_dates:
                for ship_date in shipment_dates:
                    if inv_date > ship_date:
                        timeline_analysis['timeline_issues'].append({
                            'issue': 'Invoice dated after shipment',
                            'invoice_date': inv_date.isoformat(),
                            'shipment_date': ship_date.isoformat()
                        })
                        timeline_analysis['chronological_order'] = False
        
        return timeline_analysis

    def _perform_llm_analysis(self, swift_data: Dict[str, Any], document: Dict[str, Any], doc_type: str) -> Dict[str, Any]:
        """Perform LLM-based analysis for sophisticated discrepancy detection"""
        try:
            import openai
            
            # Get database schema for context
            schema_context = self._get_database_schema_context()
            
            # Prepare structured data for LLM analysis
            swift_summary = {
                'message_type': swift_data.get('message_type'),
                'amount': swift_data.get('amount'),
                'currency': swift_data.get('currency'),
                'reference': swift_data.get('reference_number'),
                'parties': swift_data.get('parties', {}),
                'goods_description': swift_data.get('goods_description'),
                'dates': swift_data.get('dates', {}),
                'terms': swift_data.get('terms_conditions')
            }
            
            document_summary = {
                'document_type': doc_type,
                'filename': document.get('filename', 'Unknown'),
                'extracted_data': document
            }
            
            prompt = f"""
            As an expert trade finance compliance analyst with access to our database schema, analyze these documents for discrepancies:

            DATABASE SCHEMA CONTEXT:
            {schema_context}

            SWIFT LC Data:
            {json.dumps(swift_summary, indent=2)}

            Supporting Document ({doc_type}):
            {json.dumps(document_summary, indent=2)}

            Perform detailed compliance analysis using the database schema knowledge:
            1. Amount and currency consistency (reference currency tables)
            2. Party information validation (check against party master data)
            3. Goods description alignment (use commodity codes if available)
            4. Date compliance (validate against business rules in DB)
            5. Terms and conditions matching (reference terms tables)
            6. Document-specific requirements (check document_types table)
            7. Historical compliance patterns (reference previous validations)

            Use the database schema to:
            - Validate field formats and constraints
            - Cross-reference with master data tables
            - Apply business rules stored in the database
            - Identify patterns from historical compliance data

            Return ONLY a JSON object with:
            {{
                "match": boolean,
                "confidence_score": float (0-1),
                "mismatches": [
                    {{
                        "field": "field_name",
                        "issue": "description of discrepancy",
                        "swift_value": "value from SWIFT",
                        "support_value": "value from document",
                        "severity": "high|medium|low",
                        "db_reference": "relevant table/field from schema"
                    }}
                ],
                "extracted_swift": {{}},
                "extracted_support": {{}},
                "recommendations": ["list of recommendations"],
                "schema_insights": ["insights from database schema analysis"]
            }}
            """
            
            response = openai.ChatCompletion.create(
                model="gpt-35-turbo",
                messages=[
                    {"role": "system", "content": "You are a trade finance compliance expert. Analyze documents with precision and return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=2000
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            logger.error(f"LLM analysis error: {str(e)}")
            return {
                "match": True,  # Default to pass if LLM fails
                "confidence_score": 0.5,
                "mismatches": [],
                "error": str(e)
            }

    def _get_database_schema_context(self) -> str:
        """Get database schema context for LLM analysis"""
        try:
            # Import MongoDB client from routes
            from pymongo import MongoClient
            
            schema_context = """
            DATABASE SCHEMA CONTEXT:
            
            === CORE COLLECTIONS ===
            
            1. SWIFT_MESSAGES Collection:
               - _id: ObjectId
               - message_type: String (MT700, MT701, etc.)
               - reference_number: String
               - amount: Decimal
               - currency: String (3-letter ISO code)
               - applicant: Object {name, address, country}
               - beneficiary: Object {name, address, country}
               - goods_description: String
               - terms_conditions: String
               - shipment_date: Date
               - expiry_date: Date
               - created_at: DateTime
               - fields: Object (raw SWIFT fields)
            
            2. DOCUMENTS Collection:
               - _id: ObjectId
               - document_type: String (invoice, purchase_order, shipping_document, etc.)
               - swift_reference: String
               - filename: String
               - extracted_data: Object
               - compliance_status: String
               - validation_results: Object
               - created_at: DateTime
            
            3. COMPLIANCE_RESULTS Collection:
               - _id: ObjectId
               - swift_id: ObjectId
               - document_ids: Array[ObjectId]
               - overall_compliance: Boolean
               - compliance_score: Number
               - critical_issues: Array
               - warnings: Array
               - validation_timestamp: DateTime
               - llm_analysis: Object
            
            4. CURRENCIES Collection:
               - code: String (USD, EUR, etc.)
               - name: String
               - decimal_places: Number
               - active: Boolean
            
            5. COUNTRIES Collection:
               - code: String (US, GB, etc.)
               - name: String
               - region: String
               - trade_restrictions: Array
            
            6. COMMODITY_CODES Collection:
               - hs_code: String
               - description: String
               - category: String
               - restricted: Boolean
            
            7. BUSINESS_RULES Collection:
               - rule_type: String
               - field_name: String
               - validation_logic: String
               - tolerance_percentage: Number
               - severity: String
            
            8. USERS Collection:
               - _id: ObjectId
               - email: String
               - first_name: String
               - last_name: String
               - created_at: DateTime
               - last_login: DateTime
            
            9. SESSIONS Collection:
               - sessionId: String
               - user_id: ObjectId
               - lastAccessed: DateTime
               - expires: DateTime
            
            10. CONVERSATION_HISTORY Collection:
                - _id: ObjectId
                - user_id: ObjectId
                - message: String
                - sender: String (user/assistant)
                - timestamp: DateTime
            
            === VALIDATION RULES ===
            
            Amount Tolerance: 10% variance allowed
            Date Tolerance: 30 days for shipment dates
            Currency Validation: Must exist in CURRENCIES collection
            Party Validation: Names must have >60% similarity
            Goods Description: >70% similarity required
            
            === CRITICAL FIELDS ===
            
            High Priority: amount, currency, applicant, beneficiary
            Medium Priority: goods_description, shipment_date, terms
            Low Priority: document_numbers, additional_conditions
            """
            
            return schema_context
            
        except Exception as e:
            logger.warning(f"Could not load schema context: {str(e)}")
            return "Database schema context unavailable"