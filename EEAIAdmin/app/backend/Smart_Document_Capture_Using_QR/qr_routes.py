"""
QR Routes Module

This module provides Flask route registration for QR code endpoints.
Import and call register_qr_routes(app) in your main routes.py to add these routes.
"""

import json
import logging
from datetime import datetime
from flask import request, jsonify

from .qr_service import qr_service
from .qr_extractor import extract_qr_from_pdf, extract_qr_from_word, extract_qr_from_image

logger = logging.getLogger(__name__)

# Try to import timing_aspect decorator
try:
    from app.routes import timing_aspect
except ImportError:
    # Fallback: create a no-op decorator
    def timing_aspect(f):
        return f

# Try to import user_logger
try:
    from app.utils.user_logger import UserLogger
    user_logger = UserLogger()
except ImportError:
    user_logger = logger

# Try to import websocket handler
try:
    from app.websocket_handler import get_websocket_handler
except ImportError:
    def get_websocket_handler():
        return None


def register_qr_routes(app):
    """
    Register all QR-related routes with the Flask app.
    
    Args:
        app: Flask application instance
    """
    logger.info("🔷 Registering QR routes...")
    
    @app.route('/api/qr/parse', methods=['POST'])
    @timing_aspect
    def parse_qr_code():
        """
        Parse QR code data and extract trade finance information using AI/LLM processing
        """
        try:
            logger.info("="*60)
            logger.info("🔷 QR ROUTE: /api/qr/parse - Parse QR Code Data")
            logger.info("="*60)
            user_logger.info("API Request: /api/qr/parse - Parsing QR code data")

            data = request.get_json()
            if not data or 'qr_data' not in data:
                return jsonify({
                    'success': False,
                    'message': 'QR data is required'
                }), 400

            qr_raw_data = data['qr_data']
            logger.info(f"📥 QR data received: {len(qr_raw_data)} characters")
            logger.info(f"📥 QR data preview: {qr_raw_data[:200]}..." if len(qr_raw_data) > 200 else f"📥 QR data: {qr_raw_data}")
            
            result = qr_service.parse_qr_data(qr_raw_data)
            
            if result['success']:
                logger.info(f"✅ QR parsing successful - Method: {result.get('parsing_method', 'unknown')}")
                logger.info(f"✅ Parsed fields: {len(result.get('parsed_data', {}))}")
                return jsonify(result)
            else:
                logger.warning(f"⚠️ QR parsing returned failure: {result.get('message', 'Unknown')}")
                return jsonify(result), 400

        except Exception as e:
            logger.error(f"❌ QR parsing failed: {str(e)}", exc_info=True)
            user_logger.error(f"QR parsing failed: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Error parsing QR code: {str(e)}'
            }), 500

    @app.route('/api/qr/generate', methods=['POST'])
    @timing_aspect
    def generate_qr_code():
        """
        Generate QR code from current form data
        """
        try:
            logger.info("="*60)
            logger.info("🔷 QR ROUTE: /api/qr/generate - Generate QR Code")
            logger.info("="*60)
            user_logger.info("API Request: /api/qr/generate - Generating QR code")

            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'message': 'Form data is required'
                }), 400

            form_data = data.get('form_data', {})
            qr_options = data.get('options', {})

            result = qr_service.generate_qr_code(form_data, qr_options)
            
            if result['success']:
                return jsonify(result)
            else:
                return jsonify(result), 503

        except Exception as e:
            user_logger.error(f"QR generation failed: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Error generating QR code: {str(e)}'
            }), 500

    @app.route('/api/qr/process-file', methods=['POST'])
    @timing_aspect
    def process_qr_file():
        """
        Process uploaded files (PDF, DOC, DOCX, images) to extract QR codes
        """
        try:
            logger.info("="*60)
            logger.info("🔷 QR ROUTE: /api/qr/process-file - Process File for QR Codes")
            logger.info("="*60)
            user_logger.info("API Request: /api/qr/process-file - Processing file for QR codes")

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

            client_id = request.form.get('client_id', None)
            filename = file.filename.lower()
            file_type = file.content_type

            logger.info(f"📄 File details:")
            logger.info(f"   - Filename: {filename}")
            logger.info(f"   - Content-Type: {file_type}")
            logger.info(f"   - Client ID: {client_id or 'None'}")
            user_logger.info(f"Processing file: {filename}", {'file_type': file_type})

            # WebSocket progress updates
            def emit_progress(step, message, progress=None):
                if client_id:
                    try:
                        ws_handler = get_websocket_handler()
                        if ws_handler:
                            ws_handler.emit_message(client_id, 'qr_processing_progress', {
                                'step': step,
                                'message': message,
                                'progress': progress,
                                'filename': file.filename,
                                'timestamp': datetime.utcnow().isoformat()
                            })
                    except Exception as e:
                        logger.warning(f"WebSocket progress update failed: {e}")

            emit_progress('upload', 'File uploaded successfully', 10)

            try:
                emit_progress('detect', 'Detecting QR codes...', 30)

                qr_codes = []
                if filename.endswith('.pdf'):
                    emit_progress('processing', 'Processing PDF document...', 50)
                    qr_codes = extract_qr_from_pdf(file)
                elif filename.endswith(('.doc', '.docx')):
                    emit_progress('processing', 'Processing Word document...', 50)
                    qr_codes = extract_qr_from_word(file)
                elif file_type and file_type.startswith('image/'):
                    emit_progress('processing', 'Processing image...', 50)
                    qr_codes = extract_qr_from_image(file)
                else:
                    emit_progress('error', f'Unsupported file type: {file_type or "unknown"}')
                    return jsonify({
                        'success': False,
                        'message': f'Unsupported file type: {file_type or "unknown"}'
                    }), 400

                emit_progress('parsing', 'Parsing QR code data...', 70)

                if qr_codes:
                    emit_progress('complete', f'Found {len(qr_codes)} QR codes!', 100)
                    logger.info(f"✅ SUCCESS: Found {len(qr_codes)} QR code(s) in file")
                    for i, qr in enumerate(qr_codes):
                        logger.info(f"   QR #{i+1}: Method={qr.get('method', 'unknown')}, Confidence={qr.get('confidence', 0):.2f}")
                        logger.info(f"   QR #{i+1} Data Preview: {str(qr.get('data', ''))[:100]}...")
                    user_logger.info(f"Found {len(qr_codes)} QR codes in file")
                    return jsonify({
                        'success': True,
                        'qr_codes': qr_codes,
                        'message': f'Found {len(qr_codes)} QR code(s)'
                    })
                else:
                    emit_progress('complete', 'No QR codes found', 100)
                    logger.info("⚠️ No QR codes found in the file")
                    return jsonify({
                        'success': False,
                        'qr_codes': [],
                        'message': 'No QR codes found in the file'
                    })

            except Exception as processing_error:
                emit_progress('error', f'Processing error: {str(processing_error)}')
                return jsonify({
                    'success': False,
                    'message': f'Error processing file: {str(processing_error)}'
                }), 500

        except Exception as e:
            user_logger.error(f"File upload processing failed: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Error processing upload: {str(e)}'
            }), 500

    @app.route('/api/qr/process', methods=['POST'])
    @timing_aspect
    def process_qr_code():
        """
        Process QR code image and extract document URL or data
        Returns document URL/data for Smart Capture to handle classification
        """
        try:
            logger.info("="*60)
            logger.info("🔷 QR ROUTE: /api/qr/process - Process QR Code Image")
            logger.info("="*60)

            if 'file' not in request.files:
                return jsonify({
                    'success': False,
                    'error': 'No file uploaded'
                }), 400

            qr_file = request.files['file']
            if not qr_file or qr_file.filename == '':
                return jsonify({
                    'success': False,
                    'error': 'No file selected'
                }), 400

            repository_id = request.form.get('repository_id', 'trade_finance')
            logger.info(f"📄 QR file: {qr_file.filename}")
            logger.info(f"📁 Repository: {repository_id}")

            result = qr_service.process_qr_image(qr_file, repository_id)
            
            if result['success']:
                logger.info(f"✅ QR processing successful")
                logger.info(f"   - QR Data Type: {result.get('qr_data_type', 'unknown')}")
                logger.info(f"   - Has URL: {'url' in result}")
                return jsonify(result), 200
            else:
                logger.warning(f"⚠️ QR processing failed: {result.get('error', 'Unknown')}")
                return jsonify(result), 400

        except Exception as e:
            logger.error(f"❌ Error processing QR code: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': f'Error processing QR code: {str(e)}'
            }), 500

    logger.info("✅ QR routes registered successfully")
