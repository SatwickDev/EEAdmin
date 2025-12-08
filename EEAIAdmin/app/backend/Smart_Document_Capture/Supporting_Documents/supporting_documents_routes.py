"""
Supporting Documents Routes
============================

API routes for managing supporting documents upload, retrieval, and deletion.
"""

import os
import uuid
import logging
from datetime import datetime
from werkzeug.utils import secure_filename

from flask import request, jsonify, session, send_file

from app.utils.timing_aspect import timing_aspect

logger = logging.getLogger(__name__)


def register_supporting_documents_routes(app):
    """Register all supporting documents routes."""

    @app.route('/api/supporting-documents/upload', methods=['POST'])
    def upload_supporting_documents():
        """Upload supporting documents with automatic document type detection"""
        try:
            logger.info("📁 Supporting documents upload initiated")

            # Get uploaded files
            uploaded_files = request.files.getlist('documents')

            if not uploaded_files or len(uploaded_files) == 0:
                return jsonify({
                    'success': False,
                    'error': 'No documents uploaded',
                    'message': 'Please select at least one document to upload'
                }), 400

            # Create uploads directory if it doesn't exist
            upload_dir = os.path.join(os.path.dirname(app.root_path), 'app', 'uploads')
            os.makedirs(upload_dir, exist_ok=True)

            processed_documents = []
            successful_uploads = 0
            failed_uploads = []

            for file in uploaded_files:
                if file and file.filename:
                    try:
                        logger.info(f"📄 Processing document: {file.filename}")

                        # Generate unique filename
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"{timestamp}_{secure_filename(file.filename)}"
                        file_path = os.path.join(upload_dir, filename)

                        # Save file
                        file.save(file_path)
                        file_size = os.path.getsize(file_path)

                        # Get file extension for validation
                        file_extension = os.path.splitext(filename)[1].lower()
                        allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.tif', '.doc', '.docx']

                        if file_extension not in allowed_extensions:
                            failed_uploads.append({
                                'filename': file.filename,
                                'error': f'Unsupported file type: {file_extension}',
                                'reason': 'Only PDF, image, and Word documents are supported'
                            })
                            # Remove the uploaded file
                            if os.path.exists(file_path):
                                os.remove(file_path)
                            continue

                        # Simple document storage - no complex processing
                        logger.info(f"📦 Storing document: {filename}")

                        # Simple document data
                        document_data = {
                            'id': str(uuid.uuid4()),
                            'original_filename': file.filename,
                            'stored_filename': filename,
                            'file_path': file_path,
                            'file_size': file_size,
                            'file_extension': file_extension,
                            'upload_timestamp': datetime.now().isoformat(),
                            'status': 'uploaded'
                        }

                        processed_documents.append(document_data)
                        successful_uploads += 1

                    except Exception as e:
                        logger.error(f"Error processing file {file.filename}: {e}")
                        failed_uploads.append({
                            'filename': file.filename,
                            'error': str(e),
                            'reason': 'File processing error'
                        })
                else:
                    failed_uploads.append({
                        'filename': 'Unknown',
                        'error': 'Invalid file',
                        'reason': 'File has no name or is empty'
                    })

            # Store documents for discrepancy checking
            if processed_documents:
                session['uploaded_documents'] = processed_documents
                logger.info(f"✅ Stored {len(processed_documents)} documents for discrepancy checking")

            # Prepare response
            response_data = {
                'success': True,
                'message': f'Successfully uploaded {successful_uploads} documents',
                'summary': {
                    'total_uploaded': len(uploaded_files),
                    'successful': successful_uploads,
                    'failed': len(failed_uploads)
                },
                'documents': processed_documents
            }

            if failed_uploads:
                response_data['failed_uploads'] = failed_uploads
                response_data['warning'] = f'{len(failed_uploads)} documents failed to process'

            logger.info(f"📊 Upload summary: {successful_uploads} successful, {len(failed_uploads)} failed")

            return jsonify(response_data)

        except Exception as e:
            logger.error(f"Error in supporting documents upload: {e}")
            return jsonify({
                'success': False,
                'error': str(e),
                'message': 'Failed to upload documents'
            }), 500

    @app.route('/api/supporting-documents', methods=['GET'])
    def get_uploaded_supporting_documents():
        """Get list of uploaded supporting documents"""
        try:
            upload_dir = os.path.join(os.path.dirname(app.root_path), 'app', 'uploads')

            if not os.path.exists(upload_dir):
                return jsonify({
                    'success': True,
                    'documents': [],
                    'message': 'No documents uploaded yet'
                })

            documents = []
            for filename in os.listdir(upload_dir):
                file_path = os.path.join(upload_dir, filename)
                if os.path.isfile(file_path):
                    # Get file stats
                    stat_info = os.stat(file_path)

                    documents.append({
                        'filename': filename,
                        'size': stat_info.st_size,
                        'upload_date': datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                        'file_path': file_path
                    })

            # Sort by upload date (newest first)
            documents.sort(key=lambda x: x['upload_date'], reverse=True)

            return jsonify({
                'success': True,
                'documents': documents,
                'total_count': len(documents)
            })

        except Exception as e:
            logger.error(f"Error getting uploaded documents: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/supporting-documents/<document_id>', methods=['DELETE'])
    def delete_supporting_document(document_id):
        """Delete a specific supporting document"""
        try:
            upload_dir = os.path.join(os.path.dirname(app.root_path), 'app', 'uploads')

            # Find file by ID (document_id could be filename or partial match)
            target_file = None
            for filename in os.listdir(upload_dir):
                if document_id in filename or filename.startswith(document_id):
                    target_file = filename
                    break

            if not target_file:
                return jsonify({
                    'success': False,
                    'error': 'Document not found'
                }), 404

            file_path = os.path.join(upload_dir, target_file)

            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"🗑️ Deleted document: {target_file}")

                return jsonify({
                    'success': True,
                    'message': f'Document {target_file} deleted successfully'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Document file not found'
                }), 404

        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/supporting-documents/download/<filename>')
    def download_supporting_document(filename):
        """Download a specific supporting document"""
        try:
            upload_dir = os.path.join(os.path.dirname(app.root_path), 'app', 'uploads')
            file_path = os.path.join(upload_dir, filename)

            if os.path.exists(file_path):
                return send_file(file_path, as_attachment=True, download_name=filename)
            else:
                return jsonify({
                    'success': False,
                    'error': 'File not found'
                }), 404

        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
