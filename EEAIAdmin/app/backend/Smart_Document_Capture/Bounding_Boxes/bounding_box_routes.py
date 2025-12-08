"""
Bounding Box Routes Module
==========================

This module provides Flask route handlers for bounding box related endpoints.

Author: EEAdmin Team
Version: 1.0.0
"""

import os
import json
import pickle
import tempfile
import time
import base64
import logging
from io import BytesIO
from typing import Dict, List, Optional, Any

from flask import request, jsonify, session

# Import from sibling modules
from .search_service import search_text_in_ocr
from .refinement_service import process_coordinate_response

logger = logging.getLogger(__name__)


def register_routes(app):
    """
    Register bounding box related routes with the Flask app.
    
    Args:
        app: Flask application instance
    """
    
    @app.route('/api/test_coordinates', methods=['GET'])
    def test_coordinates():
        """Simple test route to verify route registration works"""
        return jsonify({
            'success': True,
            'message': 'Test route is working!',
            'timestamp': str(time.time())
        })
    
    @app.route('/api/search_field_coordinates', methods=['POST'])
    def search_field_coordinates():
        """Search for field coordinates in existing OCR data with absolute accuracy"""
        try:
            logger.info("SEARCH: === COORDINATE SEARCH API CALLED ===")
            
            data = request.get_json()
            field_value = data.get('exact_text')
            if not field_value:  
                field_value = data.get('field_value', '').strip()
            search_mode = data.get('search_mode', 'exact').lower()
            bounding_page = data.get('boundingpage', None)

            logger.info(f" Payload bounding_page: {bounding_page}")
            logger.info(f"data payload: {data}")

            # Normalize current_page to a list of ints
            if bounding_page is None:
                current_page = []
            elif isinstance(bounding_page, list):
                current_page = [int(p) for p in bounding_page if isinstance(p, (int, str)) and str(p).isdigit()]
            else:
                current_page = [int(bounding_page)] if str(bounding_page).isdigit() else []
            
            if current_page:
                logger.info(f" Page-specific search requested: Page {current_page}")
            else:
                logger.info(f"Multi-page search (all pages)")

            # Get OCR data from session
            ocr_data = session.get('current_ocr_data', [])
            logger.info(f" Session OCR data check: Found {len(ocr_data) if ocr_data else 0} entries")

            session_keys = list(session.keys())
            logger.info(f" Available session keys: {session_keys}")

            # Log page distribution
            if ocr_data:
                page_counts = {}
                for entry in ocr_data:
                    page = entry.get('bounding_page', 'unknown')
                    page_counts[page] = page_counts.get(page, 0) + 1
                logger.info(f"ANALYTICS: OCR data page distribution: {dict(sorted(page_counts.items()))}")
            
            if not ocr_data:
                # Try alternative session keys
                alt_ocr_data = session.get('ocr_data', [])
                logger.info(f"SEARCH: Checking alternative 'ocr_data' key: Found {len(alt_ocr_data) if alt_ocr_data else 0} entries")

                if alt_ocr_data:
                    ocr_data = alt_ocr_data
                    logger.info("SUCCESS:Using alternative OCR data from 'ocr_data' session key")
                else:
                    # Try loading from temporary file
                    ocr_session_id = session.get('ocr_session_id')
                    logger.info(f"SEARCH: Looking for OCR session ID: {ocr_session_id}")

                    if ocr_session_id:
                        ocr_temp_file = os.path.join(tempfile.gettempdir(), f"ocr_data_{ocr_session_id}.pkl")

                        try:
                            if os.path.exists(ocr_temp_file):
                                with open(ocr_temp_file, 'rb') as f:
                                    ocr_data = pickle.load(f)
                                logger.info(f"SUCCESS:Loaded OCR data from temp file: {len(ocr_data)} entries")
                            else:
                                logger.warning(f"ERROR: OCR temp file not found: {ocr_temp_file}")
                        except Exception as e:
                            logger.error(f"ERROR: Failed to load OCR data from temp file: {e}")
                    else:
                        # Fallback: Try to find the most recent OCR temp file
                        logger.info("SEARCH: No OCR session ID found, searching for recent OCR temp files...")
                        import glob

                        try:
                            temp_dir = tempfile.gettempdir()
                            ocr_files = glob.glob(os.path.join(temp_dir, "ocr_data_*.pkl"))

                            if ocr_files:
                                ocr_files.sort(key=lambda x: os.path.getctime(x), reverse=True)
                                most_recent_file = ocr_files[0]

                                file_age = time.time() - os.path.getctime(most_recent_file)
                                if file_age < 600:  # 10 minutes
                                    logger.info(f"SEARCH: Trying most recent OCR file: {most_recent_file}")

                                    with open(most_recent_file, 'rb') as f:
                                        ocr_data = pickle.load(f)
                                    logger.info(f"SUCCESS:Loaded OCR data from recent temp file: {len(ocr_data)} entries")
                                else:
                                    logger.warning(f"ERROR: Most recent OCR file is too old: {file_age:.1f}s")
                            else:
                                logger.warning("ERROR: No OCR temp files found")
                        except Exception as e:
                            logger.error(f"ERROR: Failed to search for recent OCR temp files: {e}")

                    if not ocr_data:
                        logger.warning("ERROR: No OCR data found in session under any key")
                        return jsonify({
                            'success': False,
                            'message': 'No OCR data available. Please process a document first.',
                            'matches': [],
                            'debug_info': {
                                'session_keys': session_keys,
                                'current_ocr_data_length': len(session.get('current_ocr_data', [])),
                                'ocr_data_length': len(session.get('ocr_data', [])),
                                'ocr_session_id': session.get('ocr_session_id', 'Not found'),
                                'temp_file_attempted': ocr_session_id is not None
                            }
                        }), 400

            # Apply page filtering
            if current_page and ocr_data:
                original_count = len(ocr_data)
                ocr_data = [
                    entry for entry in ocr_data
                    if int(entry.get('bounding_page', 0)) in current_page
                ]
                logger.info(f"SEARCH: Page filtering: {original_count} -> {len(ocr_data)} entries (Pages {current_page})")
            
            # Run search
            matches = search_text_in_ocr(field_value, ocr_data, search_mode)
            logger.info(f"SAVE: Search complete: Found {len(matches)} matches")
            
            best_match = matches[0] if matches else None

            # Load word data
            word_ocr_data = session.get('word_ocr_data', [])
            if not word_ocr_data:
                ocr_session_id = session.get('ocr_session_id')
                temp_dir = tempfile.gettempdir()

                if ocr_session_id:
                    word_temp_file = os.path.join(temp_dir, f"word_data_{ocr_session_id}.pkl")
                    if os.path.exists(word_temp_file):
                        try:
                            with open(word_temp_file, 'rb') as f:
                                word_ocr_data = pickle.load(f)
                            logger.info(f"Loaded words: {len(word_ocr_data)}")
                        except Exception as e:
                            logger.error(f"Load words error: {e}")

                if not word_ocr_data:
                    try:
                        word_files = [f for f in os.listdir(temp_dir) if f.startswith("word_data_") and f.endswith(".pkl")]
                        if word_files:
                            word_files = [os.path.join(temp_dir, f) for f in word_files]
                            word_files.sort(key=os.path.getctime, reverse=True)
                            recent_file = word_files[0]
                            if time.time() - os.path.getctime(recent_file) < 600:
                                with open(recent_file, 'rb') as f:
                                    word_ocr_data = pickle.load(f)
                                logger.info(f"Loaded recent words: {len(word_ocr_data)}")
                    except Exception as e:
                        logger.error(f"Load recent words error: {e}")
            
            # Apply page filtering for word_data
            if current_page and word_ocr_data:
                original_word_count = len(word_ocr_data)
                word_ocr_data = [
                    entry for entry in word_ocr_data
                    if int(entry.get('bounding_page', 0)) in current_page
                ]
                logger.info(f"SEARCH: Page filtering (word_ocr_data): {original_word_count} -> {len(word_ocr_data)} entries")
            
            response = {
                'success': True,
                'message': f'Found {len(matches)} matches for "{field_value}"',
                'field_value': field_value,
                'search_mode': search_mode,
                'matches': matches,
                'best_match': best_match,
                'total_matches': len(matches),
                'total_ocr_entries': len(ocr_data)
            }
            
            refined_response = process_coordinate_response(response, word_ocr_data, current_page)
            
            return jsonify(refined_response)
             
        except Exception as e:
            logger.error(f"ERROR: Error in coordinate search API: {e}")
            return jsonify({
                'success': False,
                'message': f'Search error: {str(e)}',
                'matches': []
            }), 500

    @app.route('/api/document/extract-region', methods=['POST'])
    def extract_text_from_region():
        """Extract text from a specific region of a document image"""
        try:
            # Import required modules
            import numpy as np
            from PIL import Image
            import openai
            
            data = request.get_json()

            # Get parameters
            image_base64 = data.get('image')
            region = data.get('region')  # {x, y, width, height, page}
            document_id = data.get('document_id')

            if not image_base64 or not region:
                return jsonify({
                    'success': False,
                    'error': 'Missing required parameters'
                }), 400

            # Decode base64 image
            image_data = base64.b64decode(image_base64.split(',')[1] if ',' in image_base64 else image_base64)
            image = Image.open(BytesIO(image_data))

            # Convert PIL image to numpy array
            img_array = np.array(image)

            # Extract region coordinates
            x = int(region['x'])
            y = int(region['y'])
            width = int(region['width'])
            height = int(region['height'])

            # Crop the image to the selected region
            cropped = img_array[y:y+height, x:x+width]

            try:
                # Convert cropped image back to base64
                cropped_pil = Image.fromarray(cropped)
                buffered = BytesIO()
                cropped_pil.save(buffered, format="PNG")
                cropped_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

                # Use GPT-4 Vision to extract text
                prompt = """Extract all text visible in this image region. 
                Return only the extracted text, no additional formatting or explanation."""

                messages = [
                    {
                        "role": "system",
                        "content": "You are a text extraction assistant. Extract and return only the text visible in the image."
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{cropped_base64}"}}
                        ]
                    }
                ]

                # Get deployment name from app config
                deployment_name = app.config.get('AZURE_DEPLOYMENT_NAME', 'gpt-4o')
                
                response = openai.ChatCompletion.create(
                    engine=deployment_name,
                    messages=messages,
                    temperature=0.0,
                    max_tokens=500,
                    seed=12345,
                    top_p=0.1,
                    frequency_penalty=0,
                    presence_penalty=0,
                )

                extracted_text = response.choices[0].message.content.strip()

                return jsonify({
                    'success': True,
                    'extracted_text': extracted_text,
                    'region': region
                })

            except Exception as ocr_error:
                logger.error(f"OCR extraction error: {str(ocr_error)}")

                # Fallback: return placeholder text
                return jsonify({
                    'success': True,
                    'extracted_text': 'Selected text content',
                    'region': region,
                    'warning': 'OCR service unavailable, using placeholder'
                })

        except Exception as e:
            logger.error(f"Error extracting text from region: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    logger.info("✅ Bounding box routes registered")
