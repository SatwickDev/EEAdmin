"""
Test script for the daily logging system
Creates sample log entries to verify the logging system works correctly
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.daily_logger import *

def test_logging_system():
    """Test all logging functions"""
    
    print("🧪 Testing Daily Logging System...")
    print(f"📁 Log files will be created in: {os.path.abspath('Logs')}")
    
    # Test basic logging functions
    log_info("Testing INFO level logging", component="test_script")
    log_error("Testing ERROR level logging", component="test_script", test_error=True)
    log_warning("Testing WARNING level logging", component="test_script") 
    log_debug("Testing DEBUG level logging", component="test_script")
    
    # Test application-specific logging
    log_system("SYSTEM_TEST", message="Testing system event logging")
    
    log_api("POST", "/api/test", 200, duration=1.23, user_id="test_user")
    log_api("GET", "/api/users", 200, duration=0.45, results_count=25)
    
    log_authentication("LOGIN_TEST", user_id="test_user", email="test@example.com")
    log_authentication("LOGOUT_TEST", user_id="test_user")
    
    log_database("INSERT", table="test_table", affected_rows=1)
    log_database("SELECT", table="users", affected_rows=25, query_time="0.05s")
    
    log_compliance("commercial_invoice", "compliant", discrepancies=0)
    log_compliance("bill_of_lading", "non_compliant", discrepancies=3)
    
    log_chroma("SEARCH", collection="documents", query="test search", results=5)
    log_chroma("INSERT", collection="documents", documents_added=10)
    
    log_performance("api_response_time", 234.5, unit="ms")
    log_performance("document_processing_time", 5.67, unit="s")
    
    log_document_processing("UPLOAD", document_name="test_document.pdf", file_size="2MB")
    log_document_processing("OCR_EXTRACT", document_name="test_document.pdf", pages=5)
    
    log_qr_processing("QR_SCAN", qr_data="test_qr_content", decoded=True)
    log_smart_capture("MODAL_OPEN", document_type="invoice")
    
    # Test with metadata
    log_info("Complex logging test", 
             user_id="test_user", 
             operation="test_complex",
             metadata={"key1": "value1", "key2": "value2"},
             timestamp="2025-11-07")
    
    print("✅ Logging tests completed!")
    print("📄 Check the Logs folder for the daily log file")
    print(f"📄 Expected filename: Filtered_Logs_{datetime.now().strftime('%d-%m-%Y')}.log")

if __name__ == "__main__":
    test_logging_system()