"""
Document Verification API endpoints for trade finance document processing
"""

from flask import Blueprint, request, jsonify, render_template
from werkzeug.utils import secure_filename
import os
import uuid
import json
from datetime import datetime
import mimetypes
from PIL import Image
import PyPDF2
import io
import base64
import logging

# Import AI processing utilities
from app.backend.Smart_Document_Capture.Document_Classification import DocumentClassifier
from app.backend.Smart_Document_Capture.Bounding_Boxes import FieldCoordinateMapper

# Configure logger
logger = logging.getLogger(__name__)

# Create blueprint
document_bp = Blueprint('document', __name__)

# Configuration
UPLOAD_FOLDER = 'uploads/documents'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_info(file):
    """Extract file information"""
    return {
        'name': file.filename,
        'size': len(file.read()),
        'type': file.content_type,
        'extension': file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
    }

# Sample document templates
DOCUMENT_TEMPLATES = {
    'commercial-invoice': {
        'name': 'Commercial Invoice',
        'required_fields': [
            'invoice_number', 'invoice_date', 'seller_info', 'buyer_info',
            'item_description', 'quantity', 'unit_price', 'total_amount',
            'currency', 'terms_of_sale'
        ],
        'validation_rules': {
            'invoice_date': 'date',
            'total_amount': 'currency',
            'quantity': 'number'
        }
    },
    'bill-of-lading': {
        'name': 'Bill of Lading',
        'required_fields': [
            'bl_number', 'vessel_name', 'voyage_number', 'port_of_loading',
            'port_of_discharge', 'shipper', 'consignee', 'notify_party',
            'container_details', 'freight_terms'
        ],
        'validation_rules': {
            'bl_number': 'alphanumeric',
            'vessel_name': 'text',
            'voyage_number': 'alphanumeric'
        }
    },
    'packing-list': {
        'name': 'Packing List',
        'required_fields': [
            'packing_list_number', 'date', 'shipper', 'consignee',
            'item_details', 'package_type', 'package_count', 'net_weight',
            'gross_weight', 'dimensions'
        ],
        'validation_rules': {
            'package_count': 'number',
            'net_weight': 'number',
            'gross_weight': 'number'
        }
    },
    'certificate-origin': {
        'name': 'Certificate of Origin',
        'required_fields': [
            'certificate_number', 'issue_date', 'exporter', 'consignee',
            'country_of_origin', 'commodity_description', 'certifying_authority',
            'signature', 'stamp'
        ],
        'validation_rules': {
            'issue_date': 'date',
            'country_of_origin': 'country_code'
        }
    },
    'insurance-certificate': {
        'name': 'Insurance Certificate',
        'required_fields': [
            'policy_number', 'certificate_number', 'insured_party', 'beneficiary',
            'coverage_amount', 'currency', 'coverage_type', 'risk_covered',
            'voyage_details', 'validity_period'
        ],
        'validation_rules': {
            'coverage_amount': 'currency',
            'validity_period': 'date_range'
        }
    },
    'letter-credit': {
        'name': 'Letter of Credit',
        'required_fields': [
            'lc_number', 'issue_date', 'expiry_date', 'applicant', 'beneficiary',
            'amount', 'currency', 'credit_type', 'documents_required',
            'terms_conditions', 'issuing_bank'
        ],
        'validation_rules': {
            'issue_date': 'date',
            'expiry_date': 'date',
            'amount': 'currency'
        }
    }
}

@document_bp.route('/document-check')
def document_check():
    """Render the document verification page"""
    return render_template('document_check.html')

@document_bp.route('/api/document/upload', methods=['POST'])
def upload_document():
    """Upload and process document"""
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'message': 'No file uploaded'
            }), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'message': 'No file selected'
            }), 400

        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'message': 'File type not allowed. Please upload PDF, JPG, or PNG files.'
            }), 400

        # Reset file pointer and check size
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)  # Reset to beginning
        
        if file_size > MAX_FILE_SIZE:
            return jsonify({
                'success': False,
                'message': 'File size exceeds 10MB limit'
            }), 400

        # Generate unique filename
        file_id = str(uuid.uuid4())
        filename = secure_filename(file.filename)
        file_extension = filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{file_id}.{file_extension}"
        
        # Save file
        file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        file.save(file_path)

        # Extract basic file information
        file_info = {
            'file_id': file_id,
            'original_name': filename,
            'size': file_size,
            'type': file.content_type,
            'extension': file_extension,
            'upload_time': datetime.now().isoformat(),
            'file_path': file_path
        }

        # Basic file processing
        processing_result = process_document(file_path, file_extension)
        
        return jsonify({
            'success': True,
            'message': 'File uploaded successfully',
            'file_info': file_info,
            'processing_result': processing_result
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Upload failed: {str(e)}'
        }), 500

@document_bp.route('/api/document/analyze', methods=['POST'])
def analyze_document():
    """Analyze uploaded document using AI/ML"""
    try:
        data = request.get_json()
        file_id = data.get('file_id')
        template_type = data.get('template_type')
        verification_mode = data.get('verification_mode', 'standard')
        
        if not file_id:
            return jsonify({
                'success': False,
                'message': 'File ID is required'
            }), 400

        # Simulate document analysis process
        analysis_result = perform_document_analysis(file_id, template_type, verification_mode)
        
        return jsonify({
            'success': True,
            'message': 'Document analysis completed',
            'analysis_result': analysis_result
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Analysis failed: {str(e)}'
        }), 500

@document_bp.route('/api/document/templates', methods=['GET'])
def get_templates():
    """Get available document templates"""
    return jsonify({
        'success': True,
        'templates': DOCUMENT_TEMPLATES
    })

@document_bp.route('/api/document/template/<template_type>', methods=['GET'])
def get_template(template_type):
    """Get specific template details"""
    if template_type not in DOCUMENT_TEMPLATES:
        return jsonify({
            'success': False,
            'message': 'Template not found'
        }), 404
    
    return jsonify({
        'success': True,
        'template': DOCUMENT_TEMPLATES[template_type]
    })

@document_bp.route('/api/document/verify', methods=['POST'])
def verify_document():
    """Submit document for verification"""
    try:
        data = request.get_json()
        
        # Required fields
        required_fields = ['file_id', 'template_type', 'reference_number']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'message': f'{field} is required'
                }), 400

        # Create verification record
        verification_id = str(uuid.uuid4())
        verification_data = {
            'verification_id': verification_id,
            'file_id': data['file_id'],
            'template_type': data['template_type'],
            'reference_number': data['reference_number'],
            'priority': data.get('priority', 'standard'),
            'verification_mode': data.get('verification_mode', 'standard'),
            'additional_notes': data.get('additional_notes', ''),
            'status': 'submitted',
            'submitted_at': datetime.now().isoformat(),
            'estimated_completion': get_estimated_completion(data.get('priority', 'standard'))
        }

        # In a real implementation, you would save this to a database
        # For now, we'll simulate the process
        
        # Start background verification process
        start_verification_process(verification_data)
        
        return jsonify({
            'success': True,
            'message': 'Document submitted for verification',
            'verification_id': verification_id,
            'estimated_completion': verification_data['estimated_completion']
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Verification submission failed: {str(e)}'
        }), 500

@document_bp.route('/api/document/status/<verification_id>', methods=['GET'])
def get_verification_status(verification_id):
    """Get verification status"""
    # In a real implementation, you would fetch from database
    # For now, simulate different statuses
    
    status_data = {
        'verification_id': verification_id,
        'status': 'processing',  # submitted, processing, analyzing, validating, completed, failed
        'progress': 65,
        'current_step': 'Analysis',
        'steps_completed': ['Upload', 'Processing'],
        'steps_remaining': ['Validation', 'Complete'],
        'estimated_completion': datetime.now().isoformat(),
        'results': None
    }
    
    return jsonify({
        'success': True,
        'status_data': status_data
    })

@document_bp.route('/api/document/sample', methods=['GET'])
def load_sample_document():
    """Load a sample document for demonstration"""
    template_type = request.args.get('template_type', 'commercial-invoice')
    
    # Sample document data
    sample_data = generate_sample_template_data(template_type)
    
    return jsonify({
        'success': True,
        'message': 'Sample document loaded',
        'sample_data': sample_data
    })

# Helper functions
def process_document(file_path, file_extension):
    """Basic document processing"""
    try:
        if file_extension == 'pdf':
            return process_pdf(file_path)
        elif file_extension in ['jpg', 'jpeg', 'png']:
            return process_image(file_path)
        else:
            return {'type': 'unknown', 'pages': 0, 'text_detected': False}
    except Exception as e:
        return {'error': str(e)}

def process_pdf(file_path):
    """Process PDF document"""
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            num_pages = len(pdf_reader.pages)
            
            # Extract text from first page
            first_page_text = pdf_reader.pages[0].extract_text()
            text_detected = len(first_page_text.strip()) > 0
            
            return {
                'type': 'pdf',
                'pages': num_pages,
                'text_detected': text_detected,
                'sample_text': first_page_text[:200] + '...' if len(first_page_text) > 200 else first_page_text
            }
    except Exception as e:
        return {'error': str(e)}

def process_image(file_path):
    """Process image document"""
    try:
        with Image.open(file_path) as img:
            width, height = img.size
            format_name = img.format
            
            return {
                'type': 'image',
                'format': format_name,
                'dimensions': f"{width}x{height}",
                'text_detected': True  # Would use OCR in real implementation
            }
    except Exception as e:
        return {'error': str(e)}

def perform_document_analysis(file_id, template_type, verification_mode):
    """Simulate AI-powered document analysis"""
    # In a real implementation, this would use AI/ML models
    # For now, generate realistic sample results
    
    analysis_results = {
        'confidence_score': 0.92,
        'document_type_detected': template_type,
        'fields_extracted': generate_extracted_fields(template_type),
        'validation_results': generate_validation_results(template_type),
        'compliance_check': {
            'passed': True,
            'issues': [],
            'recommendations': []
        },
        'analysis_time': '2.3 seconds',
        'processing_mode': verification_mode
    }
    
    return analysis_results

def generate_extracted_fields(template_type):
    """Generate sample extracted fields based on template"""
    if template_type == 'commercial-invoice':
        return {
            'invoice_number': 'INV-2025-001',
            'invoice_date': '2025-10-10',
            'seller_info': 'ABC Trading Company\n123 Business Street\nNew York, NY 10001',
            'buyer_info': 'XYZ Import Ltd\n456 Commerce Ave\nLondon, UK',
            'total_amount': '50,000.00',
            'currency': 'USD',
            'items': [
                {'description': 'Electronic Components', 'quantity': 100, 'unit_price': 500.00}
            ]
        }
    elif template_type == 'bill-of-lading':
        return {
            'bl_number': 'BL20251010001',
            'vessel_name': 'Ocean Explorer',
            'voyage_number': 'V2025-45',
            'port_of_loading': 'New York',
            'port_of_discharge': 'Southampton',
            'shipper': 'ABC Trading Company',
            'consignee': 'XYZ Import Ltd'
        }
    else:
        return {'message': 'Template-specific fields would be extracted here'}

def generate_validation_results(template_type):
    """Generate sample validation results"""
    return {
        'structure_valid': True,
        'required_fields_present': True,
        'data_integrity': {
            'dates_valid': True,
            'amounts_consistent': True,
            'references_valid': True
        },
        'issues_found': [
            {
                'type': 'warning',
                'field': 'date_format',
                'message': 'Date format uses DD/MM/YYYY instead of preferred MM/DD/YYYY',
                'severity': 'low'
            }
        ]
    }

def get_estimated_completion(priority):
    """Get estimated completion time based on priority"""
    from datetime import timedelta
    
    base_time = datetime.now()
    if priority == 'urgent':
        completion_time = base_time + timedelta(hours=1)
    elif priority == 'high':
        completion_time = base_time + timedelta(hours=4)
    else:  # standard
        completion_time = base_time + timedelta(hours=24)
    
    return completion_time.isoformat()

def start_verification_process(verification_data):
    """Start background verification process"""
    # In a real implementation, this would queue the verification job
    # For now, just log the process
    print(f"Started verification process for {verification_data['verification_id']}")

def simulate_document_analysis(file_path, document_type, verification_mode='standard'):
    """Simulate AI-powered document analysis and verification"""
    try:
        # Simulate processing time
        import time
        time.sleep(0.5)  # Brief delay to simulate processing
        
        # Generate realistic analysis results
        analysis_results = {
            'analysis_id': str(uuid.uuid4()),
            'status': 'completed',
            'confidence_score': 0.95 if verification_mode == 'enhanced' else 0.88,
            'document_type_detected': document_type,
            'fields_extracted': generate_extracted_fields(document_type),
            'validation_results': generate_validation_results(document_type),
            'compliance_check': {
                'passed': True,
                'issues': [],
                'recommendations': generate_recommendations(document_type)
            },
            'analysis_time': '1.8 seconds',
            'processing_mode': verification_mode
        }
        
        return analysis_results
        
    except Exception as e:
        logger.error(f"Document analysis simulation error: {str(e)}")
        return {
            'analysis_id': str(uuid.uuid4()),
            'status': 'error',
            'error': 'Analysis failed',
            'processing_mode': verification_mode
        }

def generate_recommendations(document_type):
    """Generate document-specific recommendations"""
    recommendations = {
        'commercial-invoice': [
            'Consider adding HS codes for better customs processing',
            'Ensure all amounts match supporting documents'
        ],
        'bill-of-lading': [
            'Verify container numbers match shipping records',
            'Confirm port details are accurate'
        ],
        'packing-list': [
            'Check package weights against commercial invoice',
            'Ensure proper packaging material declarations'
        ]
    }
    
    return recommendations.get(document_type, ['Document appears complete'])

def generate_sample_template_data(template_type):
    """Generate sample data for document templates"""
    samples = {
        'commercial-invoice': {
            'reference_number': 'INV-SAMPLE-001',
            'document_type': 'commercial-invoice',
            'priority': 'high',
            'verification_mode': 'enhanced',
            'additional_notes': 'Sample commercial invoice for trade finance',
            'file_info': {
                'name': 'sample-commercial-invoice.pdf',
                'type': 'application/pdf',
                'size': '2.3 MB'
            }
        },
        'bill-of-lading': {
            'reference_number': 'BL-SAMPLE-001',
            'document_type': 'bill-of-lading',
            'priority': 'high',
            'verification_mode': 'standard',
            'additional_notes': 'Sample bill of lading for ocean freight',
            'file_info': {
                'name': 'sample-bill-of-lading.pdf',
                'type': 'application/pdf',
                'size': '1.8 MB'
            }
        }
    }
    
    return samples.get(template_type, samples['commercial-invoice'])

@document_bp.route('/document-register')
@document_bp.route('/document_register')
def document_register():
    """Display document registration page with smart capture"""
    return render_template('document_register.html')

@document_bp.route('/api/document/register', methods=['POST'])
def register_document():
    """Register a new document with metadata and files"""
    try:
        # Get uploaded files
        files = request.files.getlist('files')
        if not files or files[0].filename == '':
            return jsonify({'error': 'No files uploaded'}), 400

        # Get form data
        document_data = {
            'type': request.form.get('type'),
            'number': request.form.get('number'),
            'issue_date': request.form.get('issueDate'),
            'expiry_date': request.form.get('expiryDate'),
            'issuer': request.form.get('issuer'),
            'currency': request.form.get('currency'),
            'amount': request.form.get('amount'),
            'description': request.form.get('description'),
            'lc_reference': request.form.get('lcReference'),
            'trade_reference': request.form.get('tradeReference'),
            'beneficiary': request.form.get('beneficiary'),
            'applicant': request.form.get('applicant'),
            'country_origin': request.form.get('countryOrigin'),
            'country_destination': request.form.get('countryDestination'),
            'priority': request.form.get('priority', 'medium'),
            'verification_required': request.form.get('verificationRequired', 'standard'),
            'tags': request.form.get('tags'),
            'notes': request.form.get('notes')
        }

        # Validate required fields
        required_fields = ['type', 'number', 'issue_date', 'issuer']
        missing_fields = [field for field in required_fields if not document_data.get(field)]
        if missing_fields:
            return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400

        # Generate registration ID
        registration_id = f"REG-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
        
        # Initialize AI processing components
        classifier = DocumentClassifier()
        coordinate_mapper = FieldCoordinateMapper()
        
        # Process and save files with AI extraction
        saved_files = []
        ai_extractions = []
        
        for file in files:
            if file and file.filename:
                filename = secure_filename(file.filename)
                file_path = os.path.join(UPLOAD_FOLDER, f"{registration_id}_{filename}")
                file.save(file_path)
                
                # Get file info
                file_info = {
                    'original_name': file.filename,
                    'saved_name': f"{registration_id}_{filename}",
                    'size': os.path.getsize(file_path),
                    'type': file.content_type,
                    'path': file_path
                }
                
                # Process document with AI if it's a supported type
                ai_extraction = None
                try:
                    if file.content_type in ['application/pdf', 'image/jpeg', 'image/jpg', 'image/png']:
                        logger.info(f"Processing document with AI: {filename}")
                        
                        # Reset file pointer for AI processing
                        file.seek(0)
                        
                        # Classify and extract fields with coordinates
                        classification_result = classifier.classify_and_extract(file, document_data.get('type'))
                        
                        if classification_result:
                            # Map extracted fields to coordinates
                            mapped_fields = coordinate_mapper.map_fields_to_coordinates(
                                classification_result.get('extracted_fields', {}),
                                classification_result.get('ocr_data', {}),
                                document_data.get('type', 'unknown')
                            )
                            
                            ai_extraction = {
                                'classification': classification_result.get('document_type'),
                                'confidence': classification_result.get('confidence', 0),
                                'extracted_fields': classification_result.get('extracted_fields', {}),
                                'field_coordinates': mapped_fields,
                                'ocr_text': classification_result.get('ocr_data', {}).get('text', ''),
                                'processing_status': 'success'
                            }
                            
                            # Auto-populate document metadata from AI extraction if not provided
                            if ai_extraction['extracted_fields']:
                                for field_name, field_data in ai_extraction['extracted_fields'].items():
                                    # Map common fields to document metadata
                                    field_mapping = {
                                        'Document_Number': 'number',
                                        'Invoice_Number': 'number',
                                        'LC_Number': 'number',
                                        'Issue_Date': 'issue_date',
                                        'Expiry_Date': 'expiry_date',
                                        'Amount': 'amount',
                                        'Currency': 'currency',
                                        'Issuer': 'issuer',
                                        'Beneficiary': 'beneficiary',
                                        'Applicant': 'applicant'
                                    }
                                    
                                    mapped_field = field_mapping.get(field_name)
                                    if mapped_field and not document_data.get(mapped_field):
                                        document_data[mapped_field] = field_data.get('value', '')
                            
                            logger.info(f"AI extraction successful for {filename}")
                        else:
                            ai_extraction = {'processing_status': 'failed', 'error': 'No classification result'}
                            
                except Exception as e:
                    logger.error(f"AI processing failed for {filename}: {str(e)}")
                    ai_extraction = {'processing_status': 'error', 'error': str(e)}
                
                file_info['ai_extraction'] = ai_extraction
                saved_files.append(file_info)
                if ai_extraction:
                    ai_extractions.append(ai_extraction)

        # Create document record (in a real app, this would go to a database)
        document_record = {
            'registration_id': registration_id,
            'registered_at': datetime.now().isoformat(),
            'status': 'registered',
            'files': saved_files,
            'metadata': document_data,
            'ai_extractions': ai_extractions,
            'verification_status': 'pending',
            'created_by': 'current_user',  # In real app, get from session
            'source': 'smart_capture',
            'processing_summary': {
                'files_processed': len(saved_files),
                'ai_processed': len([f for f in saved_files if f.get('ai_extraction', {}).get('processing_status') == 'success']),
                'coordinates_mapped': len([e for e in ai_extractions if e.get('field_coordinates')])
            }
        }

        # Store record (simulate database storage)
        storage_file = os.path.join(UPLOAD_FOLDER, f"{registration_id}_record.json")
        with open(storage_file, 'w') as f:
            json.dump(document_record, f, indent=2)

        # Auto-trigger verification if required
        verification_result = None
        if document_data.get('verification_required') != 'manual':
            verification_result = simulate_document_analysis(
                saved_files[0]['path'] if saved_files else None,
                document_data.get('type', 'other'),
                document_data.get('verification_required', 'standard')
            )

        return jsonify({
            'success': True,
            'registration_id': registration_id,
            'files_processed': len(saved_files),
            'ai_processed': len([f for f in saved_files if f.get('ai_extraction', {}).get('processing_status') == 'success']),
            'coordinates_mapped': len([e for e in ai_extractions if e.get('field_coordinates')]),
            'extracted_fields': ai_extractions[0].get('extracted_fields', {}) if ai_extractions else {},
            'verification_triggered': verification_result is not None,
            'verification_result': verification_result,
            'message': 'Document registered and processed with AI extraction'
        })

    except Exception as e:
        logger.error(f"Document registration error: {str(e)}")
        return jsonify({'error': 'Registration failed. Please try again.'}), 500

@document_bp.route('/api/document/registration/<registration_id>', methods=['GET'])
def get_registration_details(registration_id):
    """Get details of a registered document"""
    try:
        storage_file = os.path.join(UPLOAD_FOLDER, f"{registration_id}_record.json")
        
        if not os.path.exists(storage_file):
            return jsonify({'error': 'Registration not found'}), 404

        with open(storage_file, 'r') as f:
            document_record = json.load(f)

        # Remove sensitive file paths from response
        safe_record = document_record.copy()
        for file_info in safe_record.get('files', []):
            file_info.pop('path', None)

        return jsonify(safe_record)

    except Exception as e:
        logger.error(f"Error retrieving registration {registration_id}: {str(e)}")
        return jsonify({'error': 'Failed to retrieve registration details'}), 500

@document_bp.route('/api/document/registrations', methods=['GET'])
def list_registrations():
    """List all document registrations with pagination"""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        status_filter = request.args.get('status')
        type_filter = request.args.get('type')

        # In a real app, this would query a database
        # For now, scan the upload folder for record files
        registration_files = [f for f in os.listdir(UPLOAD_FOLDER) if f.endswith('_record.json')]
        
        registrations = []
        for file_name in registration_files:
            try:
                with open(os.path.join(UPLOAD_FOLDER, file_name), 'r') as f:
                    record = json.load(f)
                    
                    # Apply filters
                    if status_filter and record.get('status') != status_filter:
                        continue
                    if type_filter and record.get('metadata', {}).get('type') != type_filter:
                        continue
                    
                    # Remove sensitive data
                    safe_record = {
                        'registration_id': record.get('registration_id'),
                        'registered_at': record.get('registered_at'),
                        'status': record.get('status'),
                        'document_type': record.get('metadata', {}).get('type'),
                        'document_number': record.get('metadata', {}).get('number'),
                        'issuer': record.get('metadata', {}).get('issuer'),
                        'files_count': len(record.get('files', [])),
                        'verification_status': record.get('verification_status')
                    }
                    registrations.append(safe_record)
            except Exception as e:
                logger.warning(f"Error reading registration file {file_name}: {str(e)}")
                continue

        # Sort by registration date (newest first)
        registrations.sort(key=lambda x: x.get('registered_at', ''), reverse=True)

        # Implement pagination
        total = len(registrations)
        start = (page - 1) * per_page
        end = start + per_page
        paginated_results = registrations[start:end]

        return jsonify({
            'registrations': paginated_results,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        })

    except Exception as e:
        logger.error(f"Error listing registrations: {str(e)}")
        return jsonify({'error': 'Failed to retrieve registrations'}), 500

@document_bp.route('/document-verification-status')
def document_verification_status():
    """Display document verification status page"""
    return render_template('document_verification_status.html')

# Cross-reference integration endpoints
@document_bp.route('/api/document/link-classification', methods=['POST'])
def link_classification_to_registration():
    """Link a classification result to a document registration"""
    try:
        data = request.get_json()
        registration_id = data.get('registration_id')
        classification_id = data.get('classification_id')
        classification_data = data.get('classification_data', {})
        
        if not registration_id or not classification_id:
            return jsonify({'error': 'Both registration_id and classification_id are required'}), 400
        
        # Load existing registration
        storage_file = os.path.join(UPLOAD_FOLDER, f"{registration_id}_record.json")
        if not os.path.exists(storage_file):
            return jsonify({'error': 'Registration not found'}), 404
            
        with open(storage_file, 'r') as f:
            document_record = json.load(f)
        
        # Add classification link
        document_record['linked_classification'] = {
            'classification_id': classification_id,
            'linked_at': datetime.now().isoformat(),
            'classification_data': classification_data,
            'source': 'document_classification_overlay'
        }
        
        # Update the record
        with open(storage_file, 'w') as f:
            json.dump(document_record, f, indent=2)
        
        return jsonify({
            'success': True,
            'message': 'Classification linked to registration successfully',
            'registration_id': registration_id,
            'classification_id': classification_id
        })
        
    except Exception as e:
        logger.error(f"Error linking classification: {str(e)}")
        return jsonify({'error': 'Failed to link classification'}), 500

@document_bp.route('/api/document/sync-with-classification', methods=['POST'])
def sync_with_classification():
    """Sync document register data with classification overlay results"""
    try:
        data = request.get_json()
        extracted_fields = data.get('extracted_fields', {})
        file_name = data.get('file_name', '')
        document_type = data.get('document_type', '')
        
        # Create a temporary registration with classification data
        temp_registration = {
            'type': document_type,
            'extracted_data': extracted_fields,
            'source': 'classification_overlay',
            'temp_id': f"TEMP-{datetime.now().strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:8].upper()}",
            'created_at': datetime.now().isoformat(),
            'status': 'pending_registration'
        }
        
        return jsonify({
            'success': True,
            'temp_registration': temp_registration,
            'message': 'Data prepared for registration',
            'register_url': f"/document_register?prefill=true&temp_id={temp_registration['temp_id']}"
        })
        
    except Exception as e:
        logger.error(f"Error syncing with classification: {str(e)}")
        return jsonify({'error': 'Failed to sync data'}), 500

@document_bp.route('/api/document/get-extraction-data', methods=['GET'])
def get_extraction_data():
    """Get AI extraction data for document register prefill"""
    try:
        temp_id = request.args.get('temp_id')
        if not temp_id:
            return jsonify({'error': 'temp_id required'}), 400
        
        # In a real implementation, this would retrieve from cache/database
        # For now, return a success indicator
        return jsonify({
            'success': True,
            'message': 'Extraction data available for prefill',
            'temp_id': temp_id
        })
        
    except Exception as e:
        logger.error(f"Error getting extraction data: {str(e)}")
        return jsonify({'error': 'Failed to get extraction data'}), 500