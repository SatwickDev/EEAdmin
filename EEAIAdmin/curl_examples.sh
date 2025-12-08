#!/bin/bash
# Curl Examples for Chroma Per-Customer Management API
# 
# These examples show how to use the admin endpoints to manage Chroma configuration.
# Update BASE_URL and AUTH_TOKEN to match your environment.

BASE_URL="http://localhost:5000"
AUTH_TOKEN="your-admin-token-here"

# ============================================================================
# 1. GET CURRENT CHROMA CONFIGURATION
# ============================================================================
echo "1. Get current Chroma configuration"
curl -X GET "$BASE_URL/api/admin/repository_config" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" | jq .

# ============================================================================
# 2. ENABLE CHROMA FOR ALL CUSTOMERS
# ============================================================================
echo -e "\n\n2. Enable Chroma for ALL customers"
curl -X POST "$BASE_URL/api/admin/repository_config" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "chromadb",
    "host": "localhost",
    "port": 8000,
    "is_active": true,
    "enabled_for_all": true,
    "customers": []
  }' | jq .

# ============================================================================
# 3. ENABLE CHROMA FOR SPECIFIC CUSTOMERS ONLY
# ============================================================================
echo -e "\n\n3. Enable Chroma for specific customers: bank1, bank2, bank3"
curl -X POST "$BASE_URL/api/admin/repository_config" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "chromadb",
    "host": "localhost",
    "port": 8000,
    "is_active": true,
    "enabled_for_all": false,
    "customers": ["bank1", "bank2", "bank3"]
  }' | jq .

# ============================================================================
# 4. DISABLE SPECIFIC CUSTOMER (remove from allowlist)
# ============================================================================
echo -e "\n\n4. Disable Chroma for bank2 (keep only bank1, bank3)"
curl -X POST "$BASE_URL/api/admin/repository_config" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "chromadb",
    "is_active": true,
    "enabled_for_all": false,
    "customers": ["bank1", "bank3"]
  }' | jq .

# ============================================================================
# 5. DISABLE CHROMA GLOBALLY
# ============================================================================
echo -e "\n\n5. Disable Chroma globally for all customers"
curl -X POST "$BASE_URL/api/admin/repository_config" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "chromadb",
    "is_active": false
  }' | jq .

# ============================================================================
# 6. SWITCH CHROMA TO DIFFERENT HOST/PORT
# ============================================================================
echo -e "\n\n6. Switch Chroma to production server"
curl -X POST "$BASE_URL/api/admin/repository_config" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "chromadb",
    "host": "chroma-prod.example.com",
    "port": 9000,
    "is_active": true,
    "enabled_for_all": true
  }' | jq .

# ============================================================================
# 7. ADD NEW CUSTOMER TO ALLOWLIST
# ============================================================================
echo -e "\n\n7. Add new customer 'bank4' to allowlist"
curl -X POST "$BASE_URL/api/admin/repository_config" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "chromadb",
    "is_active": true,
    "enabled_for_all": false,
    "customers": ["bank1", "bank2", "bank3", "bank4"]
  }' | jq .

# ============================================================================
# 8. REVERT TO DEFAULTS (ALL ENABLED)
# ============================================================================
echo -e "\n\n8. Revert to default: Enable for all customers"
curl -X POST "$BASE_URL/api/admin/repository_config" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "chromadb",
    "host": "localhost",
    "port": 8000,
    "is_active": true,
    "enabled_for_all": true,
    "customers": []
  }' | jq .

# ============================================================================
# PYTHON EXAMPLES (using requests library)
# ============================================================================
cat > curl_examples_python.py << 'PYTHON_EOF'
#!/usr/bin/env python3
"""
Python examples for Chroma Per-Customer Management API
"""

import requests
import json

BASE_URL = "http://localhost:5000"
AUTH_TOKEN = "your-admin-token-here"

headers = {
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "Content-Type": "application/json"
}

def get_config():
    """Get current Chroma configuration"""
    print("Getting current configuration...")
    response = requests.get(f"{BASE_URL}/api/admin/repository_config", headers=headers)
    print(json.dumps(response.json(), indent=2, default=str))
    return response.json()

def enable_all():
    """Enable Chroma for all customers"""
    print("Enabling Chroma for all customers...")
    payload = {
        "type": "chromadb",
        "host": "localhost",
        "port": 8000,
        "is_active": True,
        "enabled_for_all": True,
        "customers": []
    }
    response = requests.post(f"{BASE_URL}/api/admin/repository_config", 
                           json=payload, headers=headers)
    print(json.dumps(response.json(), indent=2))
    return response.json()

def enable_specific(customer_list):
    """Enable Chroma for specific customers"""
    print(f"Enabling Chroma for: {', '.join(customer_list)}")
    payload = {
        "type": "chromadb",
        "host": "localhost",
        "port": 8000,
        "is_active": True,
        "enabled_for_all": False,
        "customers": customer_list
    }
    response = requests.post(f"{BASE_URL}/api/admin/repository_config", 
                           json=payload, headers=headers)
    print(json.dumps(response.json(), indent=2))
    return response.json()

def disable_globally():
    """Disable Chroma globally"""
    print("Disabling Chroma globally...")
    payload = {
        "type": "chromadb",
        "is_active": False
    }
    response = requests.post(f"{BASE_URL}/api/admin/repository_config", 
                           json=payload, headers=headers)
    print(json.dumps(response.json(), indent=2))
    return response.json()

if __name__ == "__main__":
    # Example usage
    print("=" * 60)
    print("Example 1: Get current configuration")
    print("=" * 60)
    config = get_config()
    
    print("\n" + "=" * 60)
    print("Example 2: Enable for all customers")
    print("=" * 60)
    enable_all()
    
    print("\n" + "=" * 60)
    print("Example 3: Enable for specific customers")
    print("=" * 60)
    enable_specific(["bank1", "bank2", "bank3"])
    
    print("\n" + "=" * 60)
    print("Example 4: Disable globally")
    print("=" * 60)
    disable_globally()
PYTHON_EOF

chmod +x curl_examples_python.py

echo -e "\n\nℹ️  Python script saved to curl_examples_python.py"
