"""
QR Code Extraction Module

This module provides QR code extraction from various file types:
- PDF documents
- Word documents (DOC, DOCX)
- Image files (JPG, PNG, etc.)
"""

import os
import uuid
import logging
import cv2
import numpy as np

from .qr_detector import detect_qr_with_multi_fallback

logger = logging.getLogger(__name__)

# Try to import user_logger, fallback to standard logger
try:
    from app.utils.user_logger import UserLogger
    user_logger = UserLogger()
except ImportError:
    user_logger = logger

# Try to import PyMuPDF
try:
    import fitz
    FITZ_AVAILABLE = True
except ImportError:
    fitz = None
    FITZ_AVAILABLE = False
    logger.warning("PyMuPDF (fitz) not available - PDF QR extraction may be limited")

# Try to import python-docx
try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    Document = None
    DOCX_AVAILABLE = False
    logger.warning("python-docx not available - Word document QR extraction disabled")


def extract_qr_from_pdf(file):
    """
    Extract QR codes from PDF file
    
    Args:
        file: Uploaded file object (Flask FileStorage)
        
    Returns:
        list: List of detected QR codes with data, type, page, and position
    """
    logger.info("📄 EXTRACT QR FROM PDF: Starting...")
    logger.info(f"   - Filename: {file.filename}")
    qr_codes = []
    
    # Determine temp directory based on OS
    import tempfile
    temp_dir = tempfile.gettempdir()

    try:
        # Save uploaded file temporarily
        temp_path = os.path.join(temp_dir, f"qr_pdf_{uuid.uuid4().hex}.pdf")
        file.save(temp_path)
        logger.info(f"   - Saved to temp: {temp_path}")

        try:
            # Use PyMuPDF if available, fallback to other methods
            if FITZ_AVAILABLE and fitz:
                doc = fitz.open(temp_path)
                total_pages = len(doc)
                logger.info(f"   - PDF opened: {total_pages} pages")
                
                for page_num in range(total_pages):
                    logger.info(f"   - Processing page {page_num + 1}/{total_pages}")
                    page = doc.load_page(page_num)
                    pix = page.get_pixmap()
                    img_data = pix.tobytes("png")

                    # Convert to OpenCV format
                    nparr = np.frombuffer(img_data, np.uint8)
                    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                    # Detect QR codes using multi-fallback system
                    detected_qr = detect_qr_with_multi_fallback(img)
                    if detected_qr:
                        logger.info(f"   - ✅ Found {len(detected_qr)} QR code(s) on page {page_num + 1}")
                    for qr in detected_qr:
                        qr_codes.append({
                            'data': qr['data'],
                            'type': qr['type'],
                            'page': page_num + 1,
                            'position': qr['position'],
                            'method': qr.get('method', 'unknown'),
                            'confidence': qr.get('confidence', 0.0)
                        })
                doc.close()
                logger.info(f"   - PDF processing complete: {len(qr_codes)} total QR codes found")
            else:
                # Fallback method using PIL and PyPDF2 (less reliable)
                user_logger.warning("PyMuPDF not available, using fallback PDF processing")
                # Could implement alternative PDF processing here

        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)

    except Exception as e:
        logger.error(f"❌ Error extracting QR from PDF: {str(e)}", exc_info=True)
        user_logger.error(f"Error extracting QR from PDF: {str(e)}")
        raise

    logger.info(f"📄 EXTRACT QR FROM PDF: Complete - {len(qr_codes)} QR codes")
    return qr_codes


def extract_qr_from_word(file):
    """
    Extract QR codes from Word document
    
    Args:
        file: Uploaded file object (Flask FileStorage)
        
    Returns:
        list: List of detected QR codes with data, type, source, and position
    """
    logger.info("📄 EXTRACT QR FROM WORD: Starting...")
    logger.info(f"   - Filename: {file.filename}")
    qr_codes = []

    if not DOCX_AVAILABLE or Document is None:
        logger.error("❌ python-docx not available - cannot process Word documents")
        user_logger.error("python-docx not available - cannot process Word documents")
        raise ImportError("python-docx module is required for Word document processing")

    # Determine temp directory based on OS
    import tempfile
    temp_dir = tempfile.gettempdir()

    try:
        # Save uploaded file temporarily
        temp_path = os.path.join(temp_dir, f"qr_word_{uuid.uuid4().hex}.docx")
        file.save(temp_path)

        try:
            doc = Document(temp_path)

            # Extract images from document
            for rel in doc.part.rels.values():
                if "image" in rel.target_ref:
                    try:
                        image_data = rel.target_part.blob

                        # Convert to OpenCV format
                        nparr = np.frombuffer(image_data, np.uint8)
                        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                        if img is not None:
                            # Detect QR codes using multi-fallback system
                            detected_qr = detect_qr_with_multi_fallback(img)
                            for qr in detected_qr:
                                qr_codes.append({
                                    'data': qr['data'],
                                    'type': qr['type'],
                                    'source': 'word_document_image',
                                    'position': qr['position'],
                                    'method': qr.get('method', 'unknown'),
                                    'confidence': qr.get('confidence', 0.0)
                                })
                    except Exception as img_error:
                        user_logger.warning(f"Error processing image in Word doc: {str(img_error)}")
                        continue

        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)

    except Exception as e:
        logger.error(f"❌ Error extracting QR from Word document: {str(e)}", exc_info=True)
        user_logger.error(f"Error extracting QR from Word document: {str(e)}")
        raise

    logger.info(f"📄 EXTRACT QR FROM WORD: Complete - {len(qr_codes)} QR codes")
    return qr_codes


def extract_qr_from_image(file):
    """
    Extract QR codes from image file
    
    Args:
        file: Uploaded file object (Flask FileStorage)
        
    Returns:
        list: List of detected QR codes with data, type, source, and position
    """
    logger.info("🖼️ EXTRACT QR FROM IMAGE: Starting...")
    logger.info(f"   - Filename: {file.filename}")
    qr_codes = []

    try:
        # Read image data directly from uploaded file
        img_data = file.read()
        logger.info(f"   - Image size: {len(img_data)} bytes")
        file.seek(0)  # Reset file pointer

        # Convert to OpenCV format
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is not None:
            logger.info(f"   - Image decoded: {img.shape[1]}x{img.shape[0]} pixels")
            # Detect QR codes using multi-fallback system
            detected_qr = detect_qr_with_multi_fallback(img)
            if detected_qr:
                logger.info(f"   - ✅ Found {len(detected_qr)} QR code(s)")
            else:
                logger.info("   - ⚠️ No QR codes detected in image")
            for qr in detected_qr:
                qr_codes.append({
                    'data': qr['data'],
                    'type': qr['type'],
                    'source': 'image_file',
                    'position': qr['position'],
                    'method': qr.get('method', 'unknown'),
                    'confidence': qr.get('confidence', 0.0)
                })
        else:
            logger.error("❌ Failed to decode image file")
            user_logger.error("Failed to decode image file")

    except Exception as e:
        logger.error(f"❌ Error extracting QR from image: {str(e)}", exc_info=True)
        user_logger.error(f"Error extracting QR from image: {str(e)}")
        raise

    logger.info(f"🖼️ EXTRACT QR FROM IMAGE: Complete - {len(qr_codes)} QR codes")
    return qr_codes
