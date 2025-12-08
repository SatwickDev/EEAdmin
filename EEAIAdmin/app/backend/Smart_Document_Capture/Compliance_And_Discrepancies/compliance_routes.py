"""
Compliance Routes for Compliance_And_Discrepancies module
Handles document compliance validation, upload, reporting, and batch processing.
"""

import os
import json
import logging
import uuid
import io
import csv
from datetime import datetime, timedelta
from typing import Dict, Any, List

from flask import Flask, request, jsonify, Response, session

logger = logging.getLogger(__name__)


def generate_detailed_compliance_report(validation_results: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a detailed compliance report"""

    report = {
        'report_id': str(uuid.uuid4()),
        'generated_at': datetime.now().isoformat(),
        'executive_summary': {},
        'detailed_findings': {},
        'recommendations': [],
        'compliance_matrix': {},
        'risk_assessment': {}
    }

    # Executive summary
    compliance_score = validation_results.get('compliance_score', 0)
    total_checks = validation_results.get('total_checks', 0)
    critical_issues = len(validation_results.get('critical_issues', []))

    report['executive_summary'] = {
        'overall_compliance_score': compliance_score,
        'total_validation_checks': total_checks,
        'critical_issues_count': critical_issues,
        'warning_count': validation_results.get('warnings', 0),
        'compliance_status': 'PASS' if compliance_score >= 80 else 'FAIL',
        'risk_level': 'HIGH' if critical_issues > 3 else 'MEDIUM' if critical_issues > 0 else 'LOW'
    }

    # Detailed findings by document type
    for doc_type, doc_result in validation_results.get('detailed_results', {}).items():
        report['detailed_findings'][doc_type] = {
            'compliance_score': (doc_result['passed_checks'] / max(doc_result['total_checks'], 1)) * 100,
            'critical_issues': doc_result.get('critical_issues', []),
            'warnings': doc_result.get('warnings_list', []),
            'field_validations': doc_result.get('field_validations', {})
        }

    # Risk assessment
    report['risk_assessment'] = {
        'financial_risk': 'HIGH' if any(
            'amount' in issue.get('field', '') for issue in validation_results.get('critical_issues', [])) else 'LOW',
        'operational_risk': 'HIGH' if any(
            'date' in issue.get('field', '') for issue in validation_results.get('critical_issues', [])) else 'LOW',
        'compliance_risk': 'HIGH' if compliance_score < 70 else 'MEDIUM' if compliance_score < 90 else 'LOW'
    }

    return report


def get_user_compliance_history(user_id: str, limit: int) -> List[Dict[str, Any]]:
    """Get compliance check history for user (mock implementation)"""
    # This would typically query a database
    # For now, return mock data
    return [
        {
            'id': str(uuid.uuid4()),
            'timestamp': (datetime.now() - timedelta(days=i)).isoformat(),
            'swift_message_type': f'MT70{i}',
            'document_count': 3 + i,
            'compliance_score': 85 + (i * 2),
            'status': 'PASS' if (85 + (i * 2)) >= 80 else 'FAIL'
        }
        for i in range(limit)
    ]


def generate_pdf_report(report_data: Dict[str, Any]) -> bytes:
    """Generate PDF compliance report"""
    # Mock PDF generation - replace with actual PDF library like reportlab
    pdf_content = f"""
    COMPLIANCE REPORT
    Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

    Executive Summary:
    - Overall Compliance Score: {report_data.get('executive_summary', {}).get('overall_compliance_score', 0)}%
    - Total Validation Checks: {report_data.get('executive_summary', {}).get('total_validation_checks', 0)}
    - Critical Issues: {report_data.get('executive_summary', {}).get('critical_issues_count', 0)}
    - Risk Level: {report_data.get('executive_summary', {}).get('risk_level', 'UNKNOWN')}

    Detailed Findings:
    {json.dumps(report_data.get('detailed_findings', {}), indent=2)}
    """

    return pdf_content.encode('utf-8')


def generate_excel_report(report_data: Dict[str, Any]) -> bytes:
    """Generate Excel compliance report"""
    # Mock Excel generation - replace with actual Excel library like openpyxl
    output = io.BytesIO()

    # Create mock Excel content
    excel_content = f"""Compliance Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Summary:
Score: {report_data.get('executive_summary', {}).get('overall_compliance_score', 0)}%
Checks: {report_data.get('executive_summary', {}).get('total_validation_checks', 0)}
Issues: {report_data.get('executive_summary', {}).get('critical_issues_count', 0)}
"""

    output.write(excel_content.encode('utf-8'))
    output.seek(0)
    return output.read()


def generate_csv_report(report_data: Dict[str, Any]) -> str:
    """Generate CSV compliance report"""
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow(['Metric', 'Value'])

    # Write executive summary
    exec_summary = report_data.get('executive_summary', {})
    writer.writerow(['Overall Compliance Score', f"{exec_summary.get('overall_compliance_score', 0)}%"])
    writer.writerow(['Total Validation Checks', exec_summary.get('total_validation_checks', 0)])
    writer.writerow(['Critical Issues Count', exec_summary.get('critical_issues_count', 0)])
    writer.writerow(['Risk Level', exec_summary.get('risk_level', 'UNKNOWN')])

    # Write detailed findings
    writer.writerow(['', ''])  # Empty row
    writer.writerow(['Document Type', 'Compliance Score', 'Critical Issues', 'Warnings'])

    for doc_type, findings in report_data.get('detailed_findings', {}).items():
        writer.writerow([
            doc_type,
            f"{findings.get('compliance_score', 0):.1f}%",
            len(findings.get('critical_issues', [])),
            len(findings.get('warnings', []))
        ])

    return output.getvalue()


def register_compliance_routes(app: Flask, timing_aspect, logger, compliance_validator, 
                               extract_text_from_file, parse_swift_message_text, db,
                               set_llm_compliance_status, run_llm_compliance_in_background):
    """
    Register compliance validation and reporting routes with the Flask app.
    
    Routes registered:
    - POST /api/compliance/validate - Validate document compliance
    - POST /api/compliance/upload - Upload and process compliance documents
    - POST /api/compliance/report - Generate detailed compliance report
    - GET /api/compliance/history - Get compliance check history
    - POST /api/compliance/llm-standard-rules - LLM-based standard rules check
    - POST /api/compliance/save - Save compliance results
    - POST /api/compliance/report/export - Export compliance report
    - POST /api/compliance/batch - Batch compliance processing
    
    Args:
        app: Flask application instance
        timing_aspect: Decorator for timing/logging
        logger: Logger instance
        compliance_validator: DocumentComplianceValidator instance
        extract_text_from_file: Function to extract text from files
        parse_swift_message_text: Function to parse SWIFT messages
        db: Database connection
    
    Note:
        The following functions are referenced but not defined in this module:
        - determine_document_type(filename, text_content) - Document type detection
        - extract_document_data(text_content, doc_type) - Structured data extraction
        These functions need to be imported or implemented separately.
    """
    
    @app.route('/api/compliance/validate', methods=['POST'])
    @timing_aspect
    def validate_document_compliance():
        """API endpoint for document compliance validation"""
        try:
            data = request.get_json()

            if not data:
                return jsonify({
                    'success': False,
                    'error': 'No data provided'
                }), 400

            swift_message = data.get('swift_message')
            related_documents = data.get('related_documents', [])

            if not swift_message:
                return jsonify({
                    'success': False,
                    'error': 'SWIFT message is required'
                }), 400

            # Perform validation
            validation_results = compliance_validator.validate_documents(
                swift_message,
                related_documents
            )

            # Log validation request
            logger.info(f"Compliance validation completed for SWIFT {swift_message.get('message_type', 'Unknown')}")

            return jsonify({
                'success': True,
                'validation_results': validation_results
            })

        except Exception as e:
            logger.error(f"Error in compliance validation: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/compliance/upload', methods=['POST'])
    @timing_aspect
    def upload_compliance_documents():
        """Upload and process documents for compliance checking"""
        try:
            uploaded_files = request.files.getlist('files')

            if not uploaded_files:
                return jsonify({
                    'success': False,
                    'error': 'No files uploaded'
                }), 400

            processed_documents = []

            for file in uploaded_files:
                if file and file.filename:
                    # Extract text from file
                    text_content = extract_text_from_file(file)

                    # Determine document type based on content or filename
                    # NOTE: determine_document_type is not defined - needs to be imported/implemented
                    doc_type = determine_document_type(file.filename, text_content)

                    # Extract structured data based on document type
                    # NOTE: extract_document_data is not defined - needs to be imported/implemented
                    structured_data = extract_document_data(text_content, doc_type)

                    processed_documents.append({
                        'filename': file.filename,
                        'document_type': doc_type,
                        'extracted_data': structured_data,
                        'raw_text': text_content[:1000]  # First 1000 chars for preview
                    })

            return jsonify({
                'success': True,
                'processed_documents': processed_documents
            })

        except Exception as e:
            logger.error(f"Error processing uploaded documents: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/compliance/report', methods=['POST'])
    @timing_aspect
    def generate_compliance_report():
        """Generate detailed compliance report"""
        try:
            data = request.get_json()
            validation_results = data.get('validation_results')

            if not validation_results:
                return jsonify({
                    'success': False,
                    'error': 'Validation results are required'
                }), 400

            # Generate comprehensive report
            report = generate_detailed_compliance_report(validation_results)

            return jsonify({
                'success': True,
                'report': report
            })

        except Exception as e:
            logger.error(f"Error generating compliance report: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/compliance/history', methods=['GET'])
    @timing_aspect
    def get_compliance_history():
        """Get compliance check history for user"""
        try:
            user_id = request.args.get('user_id')
            limit = int(request.args.get('limit', 10))

            if not user_id:
                return jsonify({
                    'success': False,
                    'error': 'User ID is required'
                }), 400

            # Mock history data - replace with actual database query
            history = get_user_compliance_history(user_id, limit)

            return jsonify({
                'success': True,
                'history': history
            })

        except Exception as e:
            logger.error(f"Error retrieving compliance history: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/compliance/llm-standard-rules', methods=['POST'])
    @timing_aspect
    def llm_standard_rules_check():
        """
        Start LLM-based compliance check in background for Tab 3, Sub-tab 1 (Standard Rules)
        Returns immediately with request_id for status polling
        """
        try:
            data = request.json
            logger.info("🚀 Initiating LLM-based standard rules compliance check")
            
            documents = data.get('documents', [])
            lc_context = data.get('lcContext', {})
            
            if not documents:
                return jsonify({'success': False, 'error': 'No documents provided'}), 400
            
            # Generate unique request ID
            request_id = str(uuid.uuid4())
            
            # Debug: Log first document structure
            if documents:
                logger.info(f"📝 Request {request_id} - Sample document structure: {json.dumps(documents[0], indent=2)[:500]}")
            
            if not lc_context:
                logger.warning(f"⚠️ Request {request_id} - No LC context provided")
            
            # Load rules from discrepancy_rules.json
            rules_file = os.path.join(app.root_path, '..', 'data', 'discrepancy_rules.json')
            
            if not os.path.exists(rules_file):
                logger.error(f"❌ Rules file not found: {rules_file}")
                return jsonify({'success': False, 'error': 'Rules file not found'}), 500
            
            with open(rules_file, 'r', encoding='utf-8') as f:
                rules_data = json.load(f)
                all_rules = rules_data.get('rules', [])
            
            logger.info(f"📚 Request {request_id} - Loaded {len(all_rules)} rules from discrepancy_rules.json")
            
            # Filter rules for classified document types - handle both string and dict
            document_types = set()
            for doc in documents:
                # Get document type - could be string or dict object
                doc_type = doc.get('documentType')
                
                # If documentType is a dict object, extract the document_type field
                if isinstance(doc_type, dict):
                    doc_type = doc_type.get('document_type', '')
                
                # If classification field exists and is dict, try that
                if not isinstance(doc_type, str) or not doc_type:
                    classification = doc.get('classification', '')
                    if isinstance(classification, dict):
                        doc_type = classification.get('document_type', '')
                    elif isinstance(classification, str):
                        doc_type = classification
                
                # Only add if we have a valid string
                if isinstance(doc_type, str) and doc_type.strip():
                    document_types.add(doc_type.strip())
            
            logger.info(f"📋 Request {request_id} - Document types found: {document_types}")
            
            relevant_rules = [
                rule for rule in all_rules 
                if rule.get('documentType', '').lower() in [dt.lower() for dt in document_types]
            ]
            
            logger.info(f"🔍 Request {request_id} - Found {len(relevant_rules)} rules for document types: {document_types}")
            
            # Initialize tracker using helper function
            set_llm_compliance_status(request_id, 'queued', 
                                       progress='Starting background processing...')
            
            # Start background thread
            import threading
            thread = threading.Thread(
                target=run_llm_compliance_in_background,
                args=(request_id, documents, lc_context, relevant_rules),
                daemon=True
            )
            thread.start()
            logger.info(f"✅ Request {request_id} - Background thread started")
            
            # Return immediately with request_id
            return jsonify({
                'success': True,
                'request_id': request_id,
                'message': 'LLM compliance check started in background',
                'status': 'queued'
            }), 202
            
        except Exception as e:
            logger.error(f"❌ Error initiating LLM compliance check: {str(e)}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/compliance/save', methods=['POST'])
    @timing_aspect
    def save_compliance_results():
        """Save compliance check results"""
        try:
            data = request.get_json()
            user_id = session.get('user_id')

            if not user_id:
                return jsonify({
                    'success': False,
                    'error': 'User not authenticated'
                }), 401

            # Create compliance record
            compliance_record = {
                'user_id': user_id,
                'timestamp': datetime.utcnow(),
                'document_type': 'bank_guarantee',
                'compliance_data': data.get('compliance_data'),
                'summary': data.get('summary'),
                'severity': data.get('severity', 'medium'),
                'status': 'completed'
            }

            # Save to database
            result = db.compliance_results.insert_one(compliance_record)

            return jsonify({
                'success': True,
                'message': 'Compliance results saved successfully',
                'record_id': str(result.inserted_id)
            })

        except Exception as e:
            logger.error(f"Error saving compliance results: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/compliance/report/export', methods=['POST'])
    @timing_aspect
    def export_compliance_report():
        """Export compliance report in various formats"""
        try:
            data = request.get_json()
            report_data = data.get('report_data')
            export_format = data.get('format', 'pdf').lower()

            if not report_data:
                return jsonify({
                    'success': False,
                    'error': 'Report data is required'
                }), 400

            if export_format == 'pdf':
                # Generate PDF report
                pdf_content = generate_pdf_report(report_data)
                return Response(
                    pdf_content,
                    mimetype='application/pdf',
                    headers={
                        'Content-Disposition': f'attachment; filename=compliance_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
                    }
                )
            elif export_format == 'excel':
                # Generate Excel report
                excel_content = generate_excel_report(report_data)
                return Response(
                    excel_content,
                    mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    headers={
                        'Content-Disposition': f'attachment; filename=compliance_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
                    }
                )
            elif export_format == 'csv':
                # Generate CSV report
                csv_content = generate_csv_report(report_data)
                return Response(
                    csv_content,
                    mimetype='text/csv',
                    headers={
                        'Content-Disposition': f'attachment; filename=compliance_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
                    }
                )
            else:
                return jsonify({
                    'success': False,
                    'error': 'Unsupported export format'
                }), 400

        except Exception as e:
            logger.error(f"Error exporting compliance report: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/compliance/batch', methods=['POST'])
    @timing_aspect
    def process_batch_compliance():
        """Process multiple documents in batch for compliance checking"""
        try:
            if 'files' not in request.files:
                return jsonify({
                    'success': False,
                    'error': 'No files uploaded'
                }), 400

            files = request.files.getlist('files')
            swift_message = request.form.get('swift_message')

            if not swift_message:
                return jsonify({
                    'success': False,
                    'error': 'SWIFT message is required'
                }), 400

            # Process files in batch
            batch_results = []

            for file in files:
                if file.filename == '':
                    continue

                # Extract text from file
                file_content = extract_text_from_file(file)
                
                # NOTE: determine_document_type is not defined - needs to be imported/implemented
                doc_type = determine_document_type(file.filename, file_content)

                # Extract structured data
                # NOTE: extract_document_data is not defined - needs to be imported/implemented
                document_data = extract_document_data(file_content, doc_type)
                document_data['document_type'] = doc_type
                document_data['filename'] = file.filename

                batch_results.append({
                    'filename': file.filename,
                    'document_type': doc_type,
                    'extracted_data': document_data,
                    'text_content': file_content[:500]  # First 500 chars for preview
                })

            # Parse SWIFT message
            swift_data = parse_swift_message_text(swift_message)

            # Validate all documents
            validation_results = compliance_validator.validate_documents(swift_data, batch_results)

            return jsonify({
                'success': True,
                'batch_id': str(uuid.uuid4()),
                'processed_count': len(batch_results),
                'swift_message': swift_data,
                'validation_results': validation_results
            })

        except Exception as e:
            logger.error(f"Error processing batch compliance: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    logger.info("✅ Registered 8 compliance routes in Compliance_And_Discrepancies module")
