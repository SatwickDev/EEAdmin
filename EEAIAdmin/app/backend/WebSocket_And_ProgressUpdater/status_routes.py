"""
Status Routes for Job/Task Progress Tracking
============================================

This module provides API endpoints for checking the status of
background jobs, processing tasks, and compliance checks.

Endpoints:
- /api/enhanced/processing_status/<request_id> - Enhanced processing status
- /api/compliance/llm-standard-rules/status/<request_id> - LLM compliance status
- /api/document/compliance-status/<file_hash> - Document compliance status

Author: Modularized from routes.py
"""

import logging
from datetime import datetime
from flask import jsonify

logger = logging.getLogger(__name__)

# Global trackers for status management
# These will be shared with routes.py
llm_compliance_tracker = {}
compliance_status_tracker = {}


def get_llm_compliance_tracker():
    """Get the LLM compliance tracker dictionary"""
    return llm_compliance_tracker


def get_compliance_status_tracker():
    """Get the compliance status tracker dictionary"""
    return compliance_status_tracker


def set_llm_compliance_status(request_id: str, status: str, progress: str = None, 
                               results: dict = None, error: str = None):
    """
    Update LLM compliance check status
    
    Args:
        request_id: Unique request identifier
        status: Status string ('queued', 'processing', 'completed', 'failed')
        progress: Progress message
        results: Results dictionary (for completed status)
        error: Error message (for failed status)
    """
    llm_compliance_tracker[request_id] = {
        'status': status,
        'progress': progress or '',
        'results': results,
        'error': error
    }
    logger.info(f"✅ Updated LLM compliance status for {request_id}: {status}")


def set_compliance_status(file_hash: str, status: str, result: dict = None, error: str = None):
    """
    Update document compliance check status
    
    Args:
        file_hash: File hash identifier
        status: Status string ('processing', 'completed', 'error')
        result: Result dictionary (for completed status)
        error: Error message (for error status)
    """
    compliance_status_tracker[file_hash] = {
        'status': status,
        'result': result,
        'error': error,
        'timestamp': datetime.now()
    }
    logger.info(f"✅ Updated compliance status for {file_hash}: {status}")


def register_status_routes(app, enhanced_features_available=False, 
                           get_realtime_logger=None, get_parallel_analyzer=None):
    """
    Register all status-related routes with the Flask app
    
    Args:
        app: Flask application instance
        enhanced_features_available: Whether enhanced features are available
        get_realtime_logger: Function to get realtime logger instance
        get_parallel_analyzer: Function to get parallel analyzer instance
    """
    
    logger.info("🔧 Registering status routes...")

    @app.route('/api/enhanced/processing_status/<request_id>', methods=['GET'])
    def get_processing_status(request_id):
        """
        Get detailed processing status for a specific request
        """
        try:
            if not enhanced_features_available:
                return jsonify({
                    'error': 'Enhanced features not available'
                }), 500

            if get_realtime_logger is None or get_parallel_analyzer is None:
                return jsonify({
                    'error': 'Required services not available'
                }), 500

            rt_logger = get_realtime_logger()

            # Get processing steps for this request
            processing_steps = rt_logger.get_processing_steps(request_id)

            # Get parallel analyzer status
            parallel_analyzer = get_parallel_analyzer()
            analyzer_status = parallel_analyzer.get_status()

            response = {
                'status': 'success',
                'request_id': request_id,
                'processing_steps': processing_steps,
                'analyzer_status': analyzer_status,
                'timestamp': datetime.now().isoformat()
            }

            return jsonify(response)

        except Exception as e:
            logger.error(f"❌ Error getting processing status: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e),
                'request_id': request_id
            }), 500

    @app.route('/api/compliance/llm-standard-rules/status/<request_id>', methods=['GET'])
    def llm_compliance_status(request_id):
        """
        Check status of LLM compliance check
        """
        try:
            if request_id not in llm_compliance_tracker:
                return jsonify({
                    'success': False,
                    'error': 'Request ID not found'
                }), 404
            
            status_info = llm_compliance_tracker[request_id]
            
            response = {
                'success': True,
                'request_id': request_id,
                'status': status_info['status'],
                'progress': status_info['progress']
            }
            
            # Include results if completed
            if status_info['status'] == 'completed':
                response['results'] = status_info['results']
            
            # Include error if failed
            if status_info['status'] == 'failed':
                response['error'] = status_info['error']
            
            return jsonify(response), 200
            
        except Exception as e:
            logger.error(f"❌ Error checking LLM compliance status: {str(e)}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/document/compliance-status/<file_hash>', methods=['GET'])
    def check_compliance_status(file_hash):
        """
        Check the status of background compliance check.
        Returns status and result if completed.
        """
        try:
            logger.info(f"📊 Checking compliance status for hash: {file_hash}")
            logger.info(f"📋 Available hashes in tracker: {list(compliance_status_tracker.keys())}")

            if file_hash not in compliance_status_tracker:
                logger.warning(f"❌ Hash {file_hash} not found in tracker")
                return jsonify({
                    "status": "not_found",
                    "message": "No compliance check found for this file"
                }), 404

            tracker_data = compliance_status_tracker[file_hash]
            status = tracker_data.get('status', 'unknown')

            logger.info(f"📊 Status for {file_hash}: {status}")

            if status == 'completed':
                result_data = tracker_data.get('result', {})
                logger.info(f"✅ Compliance completed for {file_hash} - {len(result_data)} fields")
                return jsonify({
                    "status": "completed",
                    "compliance_ready": True,
                    "result": result_data,
                    "timestamp": tracker_data.get('timestamp').isoformat() if tracker_data.get('timestamp') else None
                })
            elif status == 'processing':
                logger.info(f"⏳ Compliance still processing for {file_hash}")
                return jsonify({
                    "status": "processing",
                    "compliance_ready": False,
                    "message": "Compliance check is still running"
                })
            elif status == 'error':
                logger.error(f"❌ Compliance error for {file_hash}: {tracker_data.get('error')}")
                return jsonify({
                    "status": "error",
                    "compliance_ready": False,
                    "error": tracker_data.get('error', 'Unknown error'),
                    "timestamp": tracker_data.get('timestamp').isoformat() if tracker_data.get('timestamp') else None
                })
            else:
                logger.warning(f"⚠️ Unknown status for {file_hash}: {status}")
                return jsonify({
                    "status": "unknown",
                    "compliance_ready": False
                })

        except Exception as e:
            logger.error(f"❌ Error checking compliance status: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return jsonify({
                "status": "error",
                "error": str(e)
            }), 500

    logger.info("✅ Status routes registered successfully")
