#!/usr/bin/env python
"""Test script to check PDF upload functionality with enhanced error handling."""

import requests
import os
import sys

def test_pdf_upload():
    """Test uploading a PDF file to the trainuser-manuals endpoint."""
    
    # Test configuration
    base_url = "http://127.0.0.1:5001"
    endpoint = "/api/trainuser-manuals"
    user_id = "6864f72225b961c8282ce037"  # Your user ID from the logs
    
    # Find a test PDF file
    test_pdf_path = None
    pdf_candidates = [
        "BLv6.1 CE Import Collections.pdf",
        "test.pdf", 
        "sample.pdf"
    ]
    
    for pdf_name in pdf_candidates:
        if os.path.exists(pdf_name):
            test_pdf_path = pdf_name
            break
    
    if not test_pdf_path:
        print("No test PDF file found. Creating a simple test PDF...")
        # You could create a test PDF here if needed
        print("Please provide a PDF file for testing")
        return
    
    print(f"Testing with PDF: {test_pdf_path}")
    print(f"File size: {os.path.getsize(test_pdf_path)} bytes")
    
    # Prepare the request
    with open(test_pdf_path, 'rb') as f:
        files = {'file': (test_pdf_path, f, 'application/pdf')}
        data = {
            'user_id': user_id,
            'query': 'Test upload'
        }
        
        # Send the request
        try:
            response = requests.post(
                f"{base_url}{endpoint}",
                files=files,
                data=data,
                timeout=60  # 60 second timeout for large PDFs
            )
            
            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.json()}")
            
            if response.status_code == 200:
                print("✅ PDF upload successful!")
            else:
                print(f"❌ PDF upload failed with status {response.status_code}")
                
        except requests.exceptions.Timeout:
            print("❌ Request timed out. The PDF may be too large or the OCR is taking too long.")
        except Exception as e:
            print(f"❌ Error during upload: {e}")

if __name__ == "__main__":
    test_pdf_upload()