"""
QR Service Module

This module provides the main QRService class that wraps all QR functionality
and can be used as a Flask Blueprint for route registration.
"""

import os
import json
import base64
import logging
import tempfile
from datetime import datetime
from io import BytesIO

import cv2

from .qr_detector import detect_qr_with_multi_fallback
from .qr_extractor import extract_qr_from_pdf, extract_qr_from_word, extract_qr_from_image
from .qr_parser import parse_structured_qr_text, parse_qr_with_llm, validate_and_structure_qr_data

logger = logging.getLogger(__name__)

# Try to import user_logger, fallback to standard logger
try:
    from app.utils.user_logger import UserLogger
    user_logger = UserLogger()
except ImportError:
    user_logger = logger

# Try to import qrcode for generation
try:
    import qrcode
    QRCODE_AVAILABLE = True
except ImportError:
    QRCODE_AVAILABLE = False
    qrcode = None
    logger.warning("qrcode module not available - QR code generation disabled")


class QRService:
    """
    Service class for QR code processing in trade finance applications.
    
    Provides methods for:
    - Parsing QR code data
    - Generating QR codes
    - Processing files for QR codes
    - Processing QR images directly
    """
    
    def __init__(self):
        """Initialize the QR Service"""
        logger.info("QRService initialized")
        self.qrcode_available = QRCODE_AVAILABLE
    
    def parse_qr_data(self, qr_raw_data: str) -> dict:
        """
        Parse QR code data and extract trade finance information.
        
        Tries multiple parsing strategies:
        1. JSON parsing
        2. Structured text parsing
        3. LLM-based intelligent parsing
        
        Args:
            qr_raw_data: Raw string data from QR code
            
        Returns:
            dict: Parsing result with success status, data, and method used
        """
        try:
            logger.info("="*60)
            logger.info("📝 QR SERVICE: parse_qr_data")
            logger.info("="*60)
            logger.info(f"📥 Raw data length: {len(qr_raw_data)} characters")
            user_logger.info(f"Processing QR data", {'data_length': len(qr_raw_data)})

            parsed_result = None
            parsing_method = 'unknown'

            # Strategy 1: Try JSON parsing
            logger.info("🔹 Strategy 1: Attempting JSON parsing...")
            try:
                json_data = json.loads(qr_raw_data)
                parsed_result = json_data
                parsing_method = 'json'
                logger.info("✅ JSON parsing successful")
                user_logger.info("QR data parsed as JSON")
            except json.JSONDecodeError:
                logger.info("⚠️ JSON parsing failed, trying other methods")
                user_logger.info("QR data is not valid JSON, trying other methods")

            # Strategy 2: Try structured text parsing
            if parsed_result is None:
                logger.info("🔹 Strategy 2: Attempting structured text parsing...")
                structured_data = parse_structured_qr_text(qr_raw_data)
                if structured_data:
                    parsed_result = structured_data
                    parsing_method = 'structured_text'
                    logger.info(f"✅ Structured text parsing successful - {len(structured_data)} fields")
                    user_logger.info("QR data parsed as structured text")
                else:
                    logger.info("⚠️ Structured text parsing returned no data")

            # Strategy 3: Use LLM for intelligent parsing
            if parsed_result is None:
                logger.info("🔹 Strategy 3: Attempting LLM parsing...")
                llm_parsed_data = parse_qr_with_llm(qr_raw_data)
                if llm_parsed_data:
                    parsed_result = llm_parsed_data
                    parsing_method = 'llm'
                    logger.info("✅ LLM parsing successful")
                    user_logger.info("QR data parsed using LLM")
                else:
                    logger.info("⚠️ LLM parsing returned no data")

            if parsed_result is None:
                logger.warning("❌ All parsing strategies failed")
                return {
                    'success': False,
                    'message': 'Unable to parse QR code data. Please ensure it contains valid trade finance information.',
                    'raw_data': qr_raw_data[:200] + '...' if len(qr_raw_data) > 200 else qr_raw_data
                }

            # Validate and structure the parsed data
            logger.info("🔹 Validating and structuring parsed data...")
            validated_data = validate_and_structure_qr_data(parsed_result)

            fields_count = len(validated_data.get('trade_finance_fields', {}))
            logger.info(f"✅ QR parsing complete: Method={parsing_method}, Fields={fields_count}")
            user_logger.info("QR code parsing completed", {
                'method': parsing_method,
                'fields_extracted': fields_count
            })

            return {
                'success': True,
                'data': validated_data,
                'parsing_method': parsing_method,
                'confidence': validated_data.get('confidence', 0.8)
            }

        except Exception as e:
            user_logger.error(f"QR parsing failed: {str(e)}")
            return {
                'success': False,
                'message': f'Error parsing QR code: {str(e)}'
            }
    
    def generate_qr_code(self, form_data: dict, options: dict = None) -> dict:
        """
        Generate QR code from form data.
        
        Args:
            form_data: Dictionary containing form field values
            options: Optional settings for QR code generation (size, margin)
            
        Returns:
            dict: Result with success status, QR code as base64 image, and metadata
        """
        try:
            if not self.qrcode_available:
                return {
                    'success': False,
                    'message': 'QR code generation is not available. Please install the qrcode module: pip install qrcode[pil]'
                }

            options = options or {}
            
            # Create structured QR data
            qr_data = {
                'type': 'trade_finance_lc',
                'version': '1.0',
                'timestamp': datetime.now().isoformat(),
                'source': 'eai_admin_system',
                'data': form_data
            }

            # Generate QR code as base64 image
            qr_size = options.get('size', 400)
            qr_margin = options.get('margin', 2)

            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=10,
                border=qr_margin,
            )
            qr.add_data(json.dumps(qr_data))
            qr.make(fit=True)

            # Create QR code image
            qr_img = qr.make_image(fill_color="black", back_color="white")
            qr_img = qr_img.resize((qr_size, qr_size))

            # Convert to base64
            buffer = BytesIO()
            qr_img.save(buffer, format='PNG')
            qr_base64 = base64.b64encode(buffer.getvalue()).decode()

            user_logger.info("QR code generated successfully", {
                'size': qr_size,
                'fields_count': len(form_data)
            })

            return {
                'success': True,
                'qr_code': f'data:image/png;base64,{qr_base64}',
                'qr_data': qr_data,
                'metadata': {
                    'size': qr_size,
                    'format': 'PNG',
                    'fields_included': len(form_data)
                }
            }

        except Exception as e:
            user_logger.error(f"QR generation failed: {str(e)}")
            return {
                'success': False,
                'message': f'Error generating QR code: {str(e)}'
            }
    
    def process_file(self, file, client_id: str = None) -> dict:
        """
        Process uploaded file to extract QR codes.
        
        Supports:
        - PDF documents
        - Word documents (DOC, DOCX)
        - Image files (JPG, PNG, etc.)
        
        Args:
            file: Uploaded file object (Flask FileStorage)
            client_id: Optional WebSocket client ID for progress updates
            
        Returns:
            dict: Result with success status and list of extracted QR codes
        """
        try:
            filename = file.filename.lower()
            file_type = file.content_type

            user_logger.info(f"Processing file: {filename}", {'file_type': file_type})

            qr_codes = []

            if filename.endswith('.pdf'):
                qr_codes = extract_qr_from_pdf(file)
            elif filename.endswith(('.doc', '.docx')):
                qr_codes = extract_qr_from_word(file)
            elif file_type and file_type.startswith('image/'):
                qr_codes = extract_qr_from_image(file)
            else:
                return {
                    'success': False,
                    'message': f'Unsupported file type: {file_type or "unknown"}'
                }

            if qr_codes:
                user_logger.info(f"Found {len(qr_codes)} QR codes in file")
                return {
                    'success': True,
                    'qr_codes': qr_codes,
                    'message': f'Found {len(qr_codes)} QR code(s)'
                }
            else:
                user_logger.info("No QR codes found in file")
                return {
                    'success': False,
                    'qr_codes': [],
                    'message': 'No QR codes found in the file'
                }

        except Exception as e:
            user_logger.error(f"File processing failed: {str(e)}")
            return {
                'success': False,
                'message': f'Error processing file: {str(e)}'
            }
    
    def process_qr_image(self, qr_file, repository_id: str = 'trade_finance') -> dict:
        """
        Process QR code image and extract document URL or embedded data.
        
        Args:
            qr_file: Uploaded QR code image file
            repository_id: Repository context for processing
            
        Returns:
            dict: Result with document URL or embedded document data
        """
        try:
            logger.info("="*60)
            logger.info("🖼️ QR SERVICE: process_qr_image")
            logger.info("="*60)
            logger.info(f"📄 File: {qr_file.filename}")
            logger.info(f"📁 Repository: {repository_id}")

            # Save QR image temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_qr_file:
                qr_file.save(temp_qr_file.name)
                qr_image_path = temp_qr_file.name

            try:
                # Read QR code image using OpenCV
                logger.info("🔹 Reading QR image with OpenCV...")
                img = cv2.imread(qr_image_path)
                if img is None:
                    logger.error("❌ Could not read QR code image")
                    raise Exception("Could not read QR code image")
                
                logger.info(f"✅ Image loaded: {img.shape[1]}x{img.shape[0]} pixels")

                # Initialize QR detector
                qr_detector = cv2.QRCodeDetector()

                # Detect and decode QR code
                logger.info("🔹 Detecting and decoding QR code...")
                data, points, straight_qrcode = qr_detector.detectAndDecode(img)

                logger.info(f"📊 Detection result: Data present={bool(data)}, Length={len(data) if data else 0}")

                if not data or data == '':
                    logger.warning("⚠️ No QR code detected in image")
                    return {
                        'success': False,
                        'error': 'No QR code detected in the image. Please upload a clear QR code image.'
                    }

                logger.info(f"✅ QR Code decoded successfully!")
                logger.info(f"   - Data length: {len(data)} characters")
                logger.info(f"   - Data preview: {data[:150]}..." if len(data) > 150 else f"   - Data: {data}")

                # Determine if QR contains URL or embedded data
                is_url = data.startswith('http://') or data.startswith('https://')
                logger.info(f"   - Data type: {'URL' if is_url else 'Embedded Data'}")

                if is_url:
                    logger.info("🔗 Processing as URL QR code...")
                    return self._process_url_qr(data)
                else:
                    logger.info("📦 Processing as embedded data QR code...")
                    return self._process_embedded_qr(data)

            finally:
                # Cleanup QR image file
                if os.path.exists(qr_image_path):
                    os.unlink(qr_image_path)

        except Exception as e:
            logger.error(f"Error processing QR code: {e}", exc_info=True)
            return {
                'success': False,
                'error': f'Error processing QR code: {str(e)}'
            }
    
    def _process_url_qr(self, url: str) -> dict:
        """
        Process QR code containing a URL.
        
        Args:
            url: Document URL from QR code
            
        Returns:
            dict: Result with document URL and metadata
        """
        import requests
        from bs4 import BeautifulSoup
        import re
        
        logger.info(f"📌 QR contains document URL: {url}")
        
        final_document_url = url
        
        # Check if URL is already a direct PDF/document link
        is_direct_document = (
            url.lower().endswith('.pdf') or
            url.lower().endswith('.jpg') or
            url.lower().endswith('.jpeg') or
            url.lower().endswith('.png') or
            '/uploads/' in url.lower()
        )

        # Handle scan.page URLs
        if 'scan.page' in url and not is_direct_document:
            logger.info("🔍 Detected scan.page landing page URL")
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                }
                response = requests.get(url, timeout=10, allow_redirects=True, headers=headers)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, 'html.parser')

                # Look for PDF links
                pdf_link = None
                for link in soup.find_all(['a', 'iframe', 'embed', 'object']):
                    href = link.get('href') or link.get('src') or link.get('data')
                    if href and '.pdf' in href.lower():
                        if href.startswith('http'):
                            pdf_link = href
                        elif href.startswith('/'):
                            pdf_link = f"https://qr.scan.page{href}"
                        break

                # Search for PDF URLs in JavaScript
                if not pdf_link:
                    pdf_urls = re.findall(r'https?://[^\s"\')]+\.pdf[^\s"\']*', response.text)
                    if pdf_urls:
                        pdf_link = pdf_urls[0].split('"')[0].split("'")[0]

                if pdf_link:
                    final_document_url = pdf_link
                    logger.info(f"✅ Resolved to direct PDF: {final_document_url}")

            except Exception as e:
                logger.warning(f"Could not resolve scan.page URL: {e}")

        # Validate URL accessibility
        try:
            head_response = requests.head(final_document_url, timeout=10, allow_redirects=True)
            head_response.raise_for_status()
            logger.info(f"✅ Document URL is accessible!")
        except requests.RequestException as e:
            logger.warning(f"⚠️ Could not verify URL accessibility: {e}")

        return {
            'success': True,
            'document_url': final_document_url,
            'original_url': url if final_document_url != url else None,
            'qr_data_type': 'url',
            'is_scan_page': 'scan.page' in url,
            'message': 'QR code decoded successfully - contains document URL'
        }
    
    def _process_embedded_qr(self, data: str) -> dict:
        """
        Process QR code containing embedded document data.
        
        Args:
            data: Embedded data from QR code
            
        Returns:
            dict: Result with decoded document or error
        """
        logger.info("QR contains embedded data, attempting to decode...")

        try:
            if len(data) > 100:  # Reasonable size for embedded document
                decoded_data = base64.b64decode(data)

                # Detect file type
                file_extension = '.pdf'
                content_type = 'application/pdf'

                if decoded_data[:4] == b'%PDF':
                    file_extension = '.pdf'
                    content_type = 'application/pdf'
                elif decoded_data[:2] == b'\xff\xd8':
                    file_extension = '.jpg'
                    content_type = 'image/jpeg'
                elif decoded_data[:4] == b'\x89PNG':
                    file_extension = '.png'
                    content_type = 'image/png'

                document_content_base64 = base64.b64encode(decoded_data).decode('utf-8')

                logger.info(f"Successfully decoded embedded document ({len(decoded_data)} bytes)")

                return {
                    'success': True,
                    'document_file': document_content_base64,
                    'filename': f'QR_Document{file_extension}',
                    'content_type': content_type,
                    'qr_data_type': 'embedded',
                    'message': 'QR code decoded successfully - contains embedded document'
                }
            else:
                logger.warning("QR contains text data only")
                return {
                    'success': False,
                    'error': 'QR code contains text data but no document.',
                    'qr_data': data[:200]
                }

        except Exception as decode_error:
            logger.error(f"Error decoding embedded data: {decode_error}")
            return {
                'success': False,
                'error': 'Could not decode embedded document data from QR code.',
                'qr_data': data[:200]
            }


# Create singleton instance
qr_service = QRService()
