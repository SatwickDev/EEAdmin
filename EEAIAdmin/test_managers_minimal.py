#!/usr/bin/env python3
"""
Minimal Manager Tests - Direct testing without full app imports
"""
import os
import sys

# Test results
passed = 0
failed = 0

def test(name, condition, message=""):
    """Simple test function"""
    global passed, failed
    if condition:
        print(f"✅ PASS | {name}")
        if message:
            print(f"       | → {message}")
        passed += 1
    else:
        print(f"❌ FAIL | {name}")
        if message:
            print(f"       | → {message}")
        failed += 1

print("\n" + "="*70)
print("MINIMAL ENVIRONMENT VARIABLE MANAGER TESTS")
print("="*70 + "\n")

# Clear test env vars
for key in list(os.environ.keys()):
    if any(key.startswith(p) for p in ['MONGO_', 'CHROMA_', 'AZURE_OPENAI_', 'OPENAI_', 'ANTHROPIC_']):
        os.environ.pop(key, None)

# ============================================================================
# MongoDB Manager Tests
# ============================================================================
print("\n--- MongoDB Manager ---\n")

try:
    sys.path.insert(0, os.path.dirname(__file__))
    from app.utils.mongodb_manager import get_mongo_env_config, is_mongo_enabled
    
    # Test 1: Default config
    os.environ.pop('MONGO_MODE', None)
    config = get_mongo_env_config()
    test("MongoDB default enabled", config['mode'] == 'enabled', "Default mode is 'enabled'")
    test("MongoDB default host", config['host'] == 'localhost', "Default host is localhost")
    test("MongoDB default port", config['port'] == 27017, "Default port is 27017")
    
    # Test 2: Disabled mode
    os.environ['MONGO_MODE'] = 'disabled'
    test("MongoDB disabled mode", not is_mongo_enabled(), "MONGO_MODE=disabled works")
    os.environ.pop('MONGO_MODE', None)
    
    # Test 3: Custom URI
    os.environ['MONGO_URI'] = 'mongodb://custom:27018/db'
    config = get_mongo_env_config()
    test("MongoDB custom URI", config['uri'] == 'mongodb://custom:27018/db', "Uses MONGO_URI")
    os.environ.pop('MONGO_URI', None)
    
    # Test 4: URI precedence
    os.environ['MONGO_URI'] = 'mongodb://uri-host:27019/db'
    os.environ['MONGO_HOST'] = 'component-host'
    config = get_mongo_env_config()
    test("MongoDB URI precedence", config['uri'] == 'mongodb://uri-host:27019/db', "URI overrides components")
    os.environ.pop('MONGO_URI', None)
    os.environ.pop('MONGO_HOST', None)
    
    print(f"\nMongoDB Manager: {passed}/{passed+failed} tests passed")
    
except Exception as e:
    print(f"❌ MongoDB Manager FAILED TO IMPORT: {e}")
    failed += 4

# Reset counters for next section
mongo_passed = passed
mongo_failed = failed
passed = 0
failed = 0

# ============================================================================
# ChromaDB Manager Tests
# ============================================================================
print("\n--- ChromaDB Manager ---\n")

try:
    from app.utils.chroma_manager import get_chroma_env_config, get_chroma_client
    
    # Clear env
    for key in list(os.environ.keys()):
        if key.startswith('CHROMA_'):
            os.environ.pop(key, None)
    
    # Test 1: Default config
    config = get_chroma_env_config()
    test("ChromaDB default enabled", config['mode'] == 'enabled', "Default mode is 'enabled'")
    test("ChromaDB default customers", len(config['customers']) == 0, "No customers by default")
    test("ChromaDB per_customer_config", 'per_customer_config' in config, "Has per_customer_config key")
    
    # Test 2: Disabled mode
    os.environ['CHROMA_MODE'] = 'disabled'
    config = get_chroma_env_config()
    test("ChromaDB disabled mode", config['mode'] == 'disabled', "CHROMA_MODE=disabled works")
    os.environ.pop('CHROMA_MODE', None)
    
    # Test 3: Multi-tenant
    os.environ['CHROMA_MODE'] = 'enabled'
    os.environ['CHROMA_CUSTOMERS'] = 'bank_a,bank_b'
    os.environ['CHROMA_HOST_bank_a'] = 'chroma1.example.com'
    os.environ['CHROMA_PORT_bank_a'] = '8001'
    config = get_chroma_env_config()
    test("ChromaDB multi-tenant customers", len(config['customers']) == 2, "2 customers configured")
    test("ChromaDB multi-tenant config", 
         config['per_customer_config']['bank_a']['host'] == 'chroma1.example.com',
         "Per-customer host configured")
    
    for key in list(os.environ.keys()):
        if key.startswith('CHROMA_'):
            os.environ.pop(key, None)
    
    # Test 4: get_chroma_client function exists
    test("ChromaDB get_chroma_client", callable(get_chroma_client), "get_chroma_client function exists")
    
    print(f"\nChromaDB Manager: {passed}/{passed+failed} tests passed")
    
except Exception as e:
    print(f"❌ ChromaDB Manager FAILED TO IMPORT: {e}")
    failed += 7

chroma_passed = passed
chroma_failed = failed
passed = 0
failed = 0

# ============================================================================
# API Config Manager Tests
# ============================================================================
print("\n--- API Configuration Manager ---\n")

try:
    from app.utils.api_config_manager import (
        is_azure_openai_enabled,
        is_openai_enabled,
        is_anthropic_enabled,
        get_azure_openai_config,
        validate_api_config
    )
    
    # Clear env
    for key in list(os.environ.keys()):
        if any(key.startswith(p) for p in ['AZURE_OPENAI_', 'OPENAI_', 'ANTHROPIC_']):
            os.environ.pop(key, None)
    
    # Test 1: Azure OpenAI default enabled
    test("Azure OpenAI default enabled", is_azure_openai_enabled(), "Enabled by default")
    
    # Test 2: Azure OpenAI can be disabled
    os.environ['AZURE_OPENAI_ENABLED'] = 'false'
    test("Azure OpenAI disabled", not is_azure_openai_enabled(), "AZURE_OPENAI_ENABLED=false works")
    config = get_azure_openai_config()
    test("Azure OpenAI disabled config", config is None, "Returns None when disabled")
    os.environ.pop('AZURE_OPENAI_ENABLED', None)
    
    # Test 3: API validation
    os.environ['AZURE_OPENAI_ENABLED'] = 'true'
    is_valid, error = validate_api_config('azure_openai')
    test("API validation detects missing key", not is_valid and 'API_KEY' in error, "Detects missing API key")
    os.environ.pop('AZURE_OPENAI_ENABLED', None)
    
    # Test 4: Multiple providers
    os.environ['AZURE_OPENAI_ENABLED'] = 'true'
    os.environ['OPENAI_ENABLED'] = 'true'
    os.environ['ANTHROPIC_ENABLED'] = 'false'
    azure = is_azure_openai_enabled()
    openai_en = is_openai_enabled()
    anthropic = is_anthropic_enabled()
    test("Multiple API providers", azure and openai_en and not anthropic, "Azure=on, OpenAI=on, Anthropic=off")
    
    for key in list(os.environ.keys()):
        if any(key.startswith(p) for p in ['AZURE_OPENAI_', 'OPENAI_', 'ANTHROPIC_']):
            os.environ.pop(key, None)
    
    # Test 5: Azure OpenAI full config
    os.environ['AZURE_OPENAI_ENABLED'] = 'true'
    os.environ['AZURE_OPENAI_API_KEY'] = 'test-key'
    os.environ['AZURE_OPENAI_API_BASE'] = 'https://test.openai.azure.com/'
    config = get_azure_openai_config()
    test("Azure OpenAI configuration", 
         config is not None and config['api_key'] == 'test-key',
         "Configuration set correctly")
    
    for key in list(os.environ.keys()):
        if any(key.startswith(p) for p in ['AZURE_OPENAI_', 'OPENAI_', 'ANTHROPIC_']):
            os.environ.pop(key, None)
    
    print(f"\nAPI Config Manager: {passed}/{passed+failed} tests passed")
    
except Exception as e:
    print(f"❌ API Config Manager FAILED TO IMPORT: {e}")
    import traceback
    traceback.print_exc()
    failed += 7

api_passed = passed
api_failed = failed

# ============================================================================
# Summary
# ============================================================================
print("\n" + "="*70)
print("SUMMARY")
print("="*70)
print(f"\nMongoDB Manager:     {mongo_passed} passed, {mongo_failed} failed")
print(f"ChromaDB Manager:    {chroma_passed} passed, {chroma_failed} failed")
print(f"API Config Manager:  {api_passed} passed, {api_failed} failed")
print(f"\nTotal:               {mongo_passed + chroma_passed + api_passed} passed, {mongo_failed + chroma_failed + api_failed} failed")

success_rate = ((mongo_passed + chroma_passed + api_passed) / 
                (mongo_passed + chroma_passed + api_passed + mongo_failed + chroma_failed + api_failed) * 100)
print(f"Success Rate:        {success_rate:.1f}%\n")

if mongo_failed + chroma_failed + api_failed == 0:
    print("✅ All tests passed!\n")
    sys.exit(0)
else:
    print("❌ Some tests failed\n")
    sys.exit(1)
