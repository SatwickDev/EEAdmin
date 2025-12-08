"""
QR Code Detection Module

This module provides multi-fallback QR code detection using various methods:
- OpenCV QR detector (primary)
- Azure Computer Vision (fallback)
- OpenAI Vision (fallback)
- Pattern-based analysis (final fallback)
"""

import os
import json
import base64
import logging
import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Try to import user_logger, fallback to standard logger
try:
    from app.utils.user_logger import UserLogger
    user_logger = UserLogger()
except ImportError:
    user_logger = logger


def detect_qr_with_multi_fallback(img):
    """
    Multi-fallback QR detection with OpenCV, Azure, OpenAI, and pattern analysis
    
    Args:
        img: OpenCV image (numpy array)
        
    Returns:
        list: List of detected QR codes with data, type, position, method, and confidence
    """
    logger.info("🔍 MULTI-FALLBACK QR DETECTION: Starting...")
    qr_codes = []

    # Method 1: OpenCV (Primary - Fast and reliable)
    logger.info("   - Method 1: Trying OpenCV QRCodeDetector...")
    try:
        if img is not None:
            qr_detector = cv2.QRCodeDetector()
            data, points, _ = qr_detector.detectAndDecode(img)

            if data:
                bbox = {}
                if points is not None and len(points) > 0:
                    points = points[0]
                    x_coords = [p[0] for p in points]
                    y_coords = [p[1] for p in points]
                    bbox = {
                        'x': int(min(x_coords)),
                        'y': int(min(y_coords)),
                        'width': int(max(x_coords) - min(x_coords)),
                        'height': int(max(y_coords) - min(y_coords))
                    }

                qr_codes.append({
                    'data': data,
                    'type': 'QRCODE',
                    'position': bbox,
                    'method': 'opencv',
                    'confidence': 0.9
                })
                logger.info(f"   - ✅ OpenCV SUCCESS: QR detected!")
                logger.info(f"   - Data preview: {data[:100]}..." if len(data) > 100 else f"   - Data: {data}")
                user_logger.info("QR detected with OpenCV (primary method)")
                return qr_codes
            else:
                logger.info("   - OpenCV: No QR code found")
    except Exception as e:
        logger.warning(f"   - ⚠️ OpenCV failed: {str(e)}")
        user_logger.warning(f"OpenCV QR detection failed: {str(e)}")

    # Method 2: Azure Computer Vision (if configured)
    azure_key = os.getenv('AZURE_CV_KEY')
    azure_endpoint = os.getenv('AZURE_CV_ENDPOINT')

    logger.info("   - Method 2: Checking Azure Computer Vision...")
    if azure_key and azure_endpoint and img is not None:
        try:
            logger.info("   - Azure CV credentials found, attempting detection...")
            user_logger.info("Trying Azure Computer Vision fallback")
            qr_codes = detect_qr_with_azure(img, azure_key, azure_endpoint)
            if qr_codes:
                logger.info(f"   - ✅ Azure CV SUCCESS: {len(qr_codes)} QR code(s) found")
                user_logger.info("QR detected with Azure Computer Vision (fallback)")
                return qr_codes
            else:
                logger.info("   - Azure CV: No QR code found")
        except Exception as e:
            logger.warning(f"   - ⚠️ Azure CV failed: {str(e)}")
            user_logger.warning(f"Azure Computer Vision failed: {str(e)}")
    else:
        logger.info("   - Azure CV: Not configured (skipping)")

    # Method 3: OpenAI Vision (if configured)
    openai_key = os.getenv('OPENAI_API_KEY')

    logger.info("   - Method 3: Checking OpenAI Vision...")
    if openai_key and img is not None:
        try:
            logger.info("   - OpenAI key found, attempting detection...")
            user_logger.info("Trying OpenAI Vision fallback")
            qr_codes = detect_qr_with_openai(img, openai_key)
            if qr_codes:
                logger.info(f"   - ✅ OpenAI Vision SUCCESS: {len(qr_codes)} QR code(s) found")
                user_logger.info("QR detected with OpenAI Vision (fallback)")
                return qr_codes
            else:
                logger.info("   - OpenAI Vision: No QR code found")
        except Exception as e:
            logger.warning(f"   - ⚠️ OpenAI Vision failed: {str(e)}")
            user_logger.warning(f"OpenAI Vision failed: {str(e)}")
    else:
        logger.info("   - OpenAI Vision: Not configured (skipping)")

    # Method 4: Pattern-based analysis (final fallback)
    logger.info("   - Method 4: Trying pattern analysis...")
    try:
        user_logger.info("Trying pattern analysis fallback")
        qr_codes = detect_qr_with_patterns(img)
        if qr_codes:
            user_logger.info("QR detected with pattern analysis (final fallback)")
            return qr_codes
    except Exception as e:
        user_logger.warning(f"Pattern analysis failed: {str(e)}")

    user_logger.warning("All QR detection methods failed")
    return qr_codes


def detect_qr_with_azure(img, api_key, endpoint):
    """
    Azure Computer Vision QR detection
    
    Args:
        img: OpenCV image (numpy array)
        api_key: Azure subscription key
        endpoint: Azure endpoint URL
        
    Returns:
        list: List of detected QR codes
    """
    import requests
    import time

    try:
        # Convert image to bytes
        _, img_encoded = cv2.imencode('.png', img)
        image_data = img_encoded.tobytes()

        headers = {
            'Ocp-Apim-Subscription-Key': api_key,
            'Content-Type': 'application/octet-stream'
        }

        # Use Read API for text extraction
        url = f"{endpoint}/vision/v3.2/read/analyze"
        response = requests.post(url, headers=headers, data=image_data, timeout=30)
        response.raise_for_status()

        # Get operation location
        operation_url = response.headers['Operation-Location']

        # Poll for results
        for _ in range(10):  # Max 10 attempts
            result = requests.get(operation_url, headers={'Ocp-Apim-Subscription-Key': api_key}, timeout=30)
            result_json = result.json()

            if result_json['status'] == 'succeeded':
                # Extract text and analyze for QR patterns
                extracted_text = ""
                for page in result_json.get('analyzeResult', {}).get('readResults', []):
                    for line in page.get('lines', []):
                        extracted_text += line['text'] + "\n"

                return analyze_text_for_qr_patterns(extracted_text, 'azure_vision')

            elif result_json['status'] == 'failed':
                break

            time.sleep(1)

        return []

    except Exception as e:
        raise Exception(f"Azure Computer Vision error: {str(e)}")


def detect_qr_with_openai(img, api_key):
    """
    OpenAI Vision QR detection
    
    Args:
        img: OpenCV image (numpy array)
        api_key: OpenAI API key
        
    Returns:
        list: List of detected QR codes
    """
    try:
        # Convert image to base64
        _, img_encoded = cv2.imencode('.png', img)
        image_data = img_encoded.tobytes()
        base64_image = base64.b64encode(image_data).decode('utf-8')

        import openai
        client = openai.OpenAI(api_key=api_key)

        response = client.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """Analyze this image for QR codes. If you find any QR codes, extract and decode their content. 
                            Look for trade finance data like applicant name, beneficiary, LC amount, currency, ports, etc.
                            Return the QR content as valid JSON. If no QR codes found, return empty."""
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=1000,
            timeout=30
        )

        content = response.choices[0].message.content

        # Try to extract JSON from the response
        import re
        json_matches = re.finditer(r'\{.*?\}', content, re.DOTALL)

        qr_codes = []
        for match in json_matches:
            try:
                json_data = json.loads(match.group())
                qr_codes.append({
                    'data': json.dumps(json_data),
                    'type': 'QRCODE',
                    'position': {'x': 0, 'y': 0, 'width': 0, 'height': 0},
                    'method': 'openai_vision',
                    'confidence': 0.8
                })
            except:
                continue

        return qr_codes

    except Exception as e:
        raise Exception(f"OpenAI Vision error: {str(e)}")


def detect_qr_with_patterns(img):
    """
    Pattern-based QR detection using OCR
    
    Args:
        img: OpenCV image (numpy array)
        
    Returns:
        list: List of detected QR codes
    """
    try:
        # Try to use pytesseract if available
        try:
            import pytesseract
            text = pytesseract.image_to_string(img)
            return analyze_text_for_qr_patterns(text, 'pattern_analysis')
        except ImportError:
            # Fallback to simple edge-based text detection
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            # This is a simplified fallback
            return []

    except Exception as e:
        raise Exception(f"Pattern analysis error: {str(e)}")


def analyze_text_for_qr_patterns(text, method):
    """
    Analyze extracted text for QR code patterns
    
    Args:
        text: Extracted text from image
        method: Detection method used
        
    Returns:
        list: List of detected QR codes
    """
    qr_codes = []

    # Look for JSON patterns
    import re
    json_matches = re.finditer(r'\{[^{}]*\}', text)

    for match in json_matches:
        try:
            json_data = json.loads(match.group())
            if looks_like_trade_finance_data(json_data):
                qr_codes.append({
                    'data': json.dumps(json_data),
                    'type': 'QRCODE',
                    'position': {'x': 0, 'y': 0, 'width': 0, 'height': 0},
                    'method': method,
                    'confidence': 0.7
                })
        except:
            continue

    # Look for key-value patterns
    if not qr_codes:
        lines = text.split('\n')
        kv_data = {}

        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower().replace(' ', '_')
                value = value.strip()

                if len(value) > 0 and len(key) > 0:
                    kv_data[key] = value

        if len(kv_data) >= 3:  # At least 3 key-value pairs
            qr_codes.append({
                'data': json.dumps(kv_data),
                'type': 'QRCODE',
                'position': {'x': 0, 'y': 0, 'width': 0, 'height': 0},
                'method': method,
                'confidence': 0.6
            })

    return qr_codes


def looks_like_trade_finance_data(data):
    """
    Check if data looks like trade finance information
    
    Args:
        data: Dictionary to check
        
    Returns:
        bool: True if data appears to be trade finance related
    """
    trade_finance_keywords = [
        'applicant', 'beneficiary', 'amount', 'currency', 'lc_amount',
        'expiry', 'port', 'loading', 'discharge', 'commodity', 'invoice'
    ]

    keys = [k.lower() for k in data.keys()]
    matches = sum(1 for keyword in trade_finance_keywords if any(keyword in k for k in keys))

    return matches >= 2  # At least 2 trade finance related fields
