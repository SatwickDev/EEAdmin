#!/usr/bin/env python3
"""
Direct Manager Tests - Import managers without app package initialization
"""
import os
import sys
import importlib.util

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

def import_module_directly(module_path, module_name):
    """Import a module directly from file path without package initialization"""
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

print("\n" + "="*70)
print("DIRECT MANAGER MODULE TESTS")
print("="*70 + "\n")

# Clear test env vars
for key in list(os.environ.keys()):
    if any(key.startswith(p) for p in ['MONGO_', 'CHROMA_', 'AZURE_OPENAI_', 'OPENAI_', 'ANTHROPIC_']):
        os.environ.pop(key, None)

base_path = os.path.dirname(__file__)

# ============================================================================
# MongoDB Manager Tests
# ============================================================================
print("\n--- MongoDB Manager (Direct Import) ---\n")

try:
    mongodb_manager = import_module_directly(
        os.path.join(base_path, 'app', 'utils', 'mongodb_manager.py'),
        'mongodb_manager_test'
    )
    
    # Test 1: Default config
    os.environ.pop('MONGO_MODE', None)
    config = mongodb_manager.get_mongo_env_config()
    test("MongoDB default enabled", config['mode'] == 'enabled', "Default mode is 'enabled'")
    test("MongoDB default host", config['host'] == 'localhost', "Default host is localhost")
    test("MongoDB default port", config['port'] == 27017, "Default port is 27017")
    
    # Test 2: Disabled mode
    os.environ['MONGO_MODE'] = 'disabled'
    test("MongoDB disabled mode", not mongodb_manager.is_mongo_enabled(), "MONGO_MODE=disabled works")
    os.environ.pop('MONGO_MODE', None)
    
    # Test 3: Custom URI
    os.environ['MONGO_URI'] = 'mongodb://custom:27018/db'
    config = mongodb_manager.get_mongo_env_config()
    test("MongoDB custom URI", config['uri'] == 'mongodb://custom:27018/db', "Uses MONGO_URI")
    os.environ.pop('MONGO_URI', None)
    
    # Test 4: URI precedence
    os.environ['MONGO_URI'] = 'mongodb://uri-host:27019/db'
    os.environ['MONGO_HOST'] = 'component-host'
    config = mongodb_manager.get_mongo_env_config()
    test("MongoDB URI precedence", config['uri'] == 'mongodb://uri-host:27019/db', "URI overrides components")
    os.environ.pop('MONGO_URI', None)
    os.environ.pop('MONGO_HOST', None)
    
    # Test 5: Component config
    os.environ['MONGO_HOST'] = 'custom-mongo.example.com'
    os.environ['MONGO_PORT'] = '27018'
    os.environ['MONGO_USERNAME'] = 'admin'
    os.environ['MONGO_PASSWORD'] = 'secret'
    os.environ['DATABASE_NAME'] = 'CustomDB'
    config = mongodb_manager.get_mongo_env_config()
    test("MongoDB component config", 
         config['host'] == 'custom-mongo.example.com' and 
         config['port'] == 27018 and
         config['database_name'] == 'CustomDB',
         "Components configured correctly")
    
    for key in ['MONGO_HOST', 'MONGO_PORT', 'MONGO_USERNAME', 'MONGO_PASSWORD', 'DATABASE_NAME']:
        os.environ.pop(key, None)
    
    mongo_passed = passed
    mongo_failed = failed
    print(f"\nMongoDB Manager: {passed}/{passed+failed} tests passed")
    
except Exception as e:
    print(f"❌ MongoDB Manager FAILED: {e}")
    import traceback
    traceback.print_exc()
    mongo_passed = 0
    mongo_failed = 6

# Reset counters
passed = 0
failed = 0

# ============================================================================
# API Config Manager Tests
# ============================================================================
print("\n--- API Config Manager (Direct Import) ---\n")

try:
    api_config_manager = import_module_directly(
        os.path.join(base_path, 'app', 'utils', 'api_config_manager.py'),
        'api_config_manager_test'
    )
    
    # Clear env
    for key in list(os.environ.keys()):
        if any(key.startswith(p) for p in ['AZURE_OPENAI_', 'OPENAI_', 'ANTHROPIC_']):
            os.environ.pop(key, None)
    
    # Test 1: Azure OpenAI default enabled
    test("Azure OpenAI default enabled", api_config_manager.is_azure_openai_enabled(), "Enabled by default")
    
    # Test 2: Azure OpenAI can be disabled
    os.environ['AZURE_OPENAI_ENABLED'] = 'false'
    test("Azure OpenAI disabled", not api_config_manager.is_azure_openai_enabled(), "AZURE_OPENAI_ENABLED=false works")
    config = api_config_manager.get_azure_openai_config()
    test("Azure OpenAI disabled config", config is None, "Returns None when disabled")
    os.environ.pop('AZURE_OPENAI_ENABLED', None)
    
    # Test 3: API validation
    os.environ['AZURE_OPENAI_ENABLED'] = 'true'
    is_valid, error = api_config_manager.validate_api_config('azure_openai')
    test("API validation detects missing key", not is_valid and 'API_KEY' in error, "Detects missing API key")
    os.environ.pop('AZURE_OPENAI_ENABLED', None)
    
    # Test 4: Multiple providers
    os.environ['AZURE_OPENAI_ENABLED'] = 'true'
    os.environ['OPENAI_ENABLED'] = 'true'
    os.environ['ANTHROPIC_ENABLED'] = 'false'
    azure = api_config_manager.is_azure_openai_enabled()
    openai_en = api_config_manager.is_openai_enabled()
    anthropic = api_config_manager.is_anthropic_enabled()
    test("Multiple API providers", azure and openai_en and not anthropic, "Azure=on, OpenAI=on, Anthropic=off")
    
    for key in list(os.environ.keys()):
        if any(key.startswith(p) for p in ['AZURE_OPENAI_', 'OPENAI_', 'ANTHROPIC_']):
            os.environ.pop(key, None)
    
    # Test 5: Azure OpenAI full config
    os.environ['AZURE_OPENAI_ENABLED'] = 'true'
    os.environ['AZURE_OPENAI_API_KEY'] = 'test-key'
    os.environ['AZURE_OPENAI_API_BASE'] = 'https://test.openai.azure.com/'
    config = api_config_manager.get_azure_openai_config()
    test("Azure OpenAI configuration", 
         config is not None and config['api_key'] == 'test-key',
         "Configuration set correctly")
    
    for key in list(os.environ.keys()):
        if any(key.startswith(p) for p in ['AZURE_OPENAI_', 'OPENAI_', 'ANTHROPIC_']):
            os.environ.pop(key, None)
    
    api_passed = passed
    api_failed = failed
    print(f"\nAPI Config Manager: {passed}/{passed+failed} tests passed")
    
except Exception as e:
    print(f"❌ API Config Manager FAILED: {e}")
    import traceback
    traceback.print_exc()
    api_passed = 0
    api_failed = 6

# ============================================================================
# Summary
# ============================================================================
print("\n" + "="*70)
print("SUMMARY")
print("="*70)
print(f"\nMongoDB Manager:     {mongo_passed} passed, {mongo_failed} failed")
print(f"API Config Manager:  {api_passed} passed, {api_failed} failed")
print(f"\nTotal:               {mongo_passed + api_passed} passed, {mongo_failed + api_failed} failed")

total_tests = mongo_passed + api_passed + mongo_failed + api_failed
if total_tests > 0:
    success_rate = ((mongo_passed + api_passed) / total_tests * 100)
    print(f"Success Rate:        {success_rate:.1f}%\n")

if mongo_failed + api_failed == 0:
    print("✅ All tests passed!\n")
    sys.exit(0)
else:
    print("❌ Some tests failed\n")
    sys.exit(1)
