#!/usr/bin/env python3
"""
Test Environment Variable Managers Directly
Avoids app imports that trigger ChromaDB connections
"""

import os
import sys
from typing import Dict

# Test Results
test_results = []

def print_section(title: str):
    """Print formatted section header"""
    print(f"\n{'='*70}")
    print(f"{title:^70}")
    print(f"{'='*70}\n")

def print_test(name: str, passed: bool, message: str = ""):
    """Print test result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status:8} | {name}")
    if message:
        print(f"{'':8} | → {message}")
    test_results.append((name, passed, message))

def save_env_vars() -> Dict[str, str]:
    """Save current environment variables"""
    saved = {}
    for key in list(os.environ.keys()):
        if any(key.startswith(prefix) for prefix in ['MONGO_', 'CHROMA_', 'AZURE_OPENAI_', 'OPENAI_', 'ANTHROPIC_']):
            saved[key] = os.environ[key]
    return saved

def restore_env_vars(saved: Dict[str, str]):
    """Restore environment variables"""
    # Clear all
    for key in list(os.environ.keys()):
        if any(key.startswith(prefix) for prefix in ['MONGO_', 'CHROMA_', 'AZURE_OPENAI_', 'OPENAI_', 'ANTHROPIC_']):
            os.environ.pop(key, None)
    # Restore saved
    for key, value in saved.items():
        os.environ[key] = value

def clear_all_env_vars():
    """Clear all test environment variables"""
    for key in list(os.environ.keys()):
        if any(key.startswith(prefix) for prefix in ['MONGO_', 'CHROMA_', 'AZURE_OPENAI_', 'OPENAI_', 'ANTHROPIC_']):
            os.environ.pop(key, None)

# =============================================================================
# TEST 1: MongoDB Manager Tests
# =============================================================================

def test_mongodb_manager_import():
    """Test MongoDB manager can be imported"""
    try:
        from app.utils.mongodb_manager import get_mongo_env_config
        print_test("MongoDB manager import", True, "Successfully imported")
        return True
    except Exception as e:
        print_test("MongoDB manager import", False, str(e))
        return False

def test_mongodb_default_config():
    """Test MongoDB default configuration"""
    try:
        clear_all_env_vars()
        from app.utils.mongodb_manager import get_mongo_env_config
        
        config = get_mongo_env_config()
        
        checks = [
            config['mode'] == 'enabled',
            config['host'] == 'localhost',
            config['port'] == 27017,
            config['database_name'] in ['finai_chatbot', 'EEAI_DB']  # Accept either default
        ]
        
        if all(checks):
            print_test("MongoDB default config", True, f"localhost:27017/{config['database_name']}")
            return True
        else:
            print_test("MongoDB default config", False, f"Config: {config}")
            return False
    except Exception as e:
        print_test("MongoDB default config", False, str(e))
        return False

def test_mongodb_disabled_mode():
    """Test MongoDB disabled mode"""
    try:
        clear_all_env_vars()
        os.environ['MONGO_MODE'] = 'disabled'
        
        from app.utils.mongodb_manager import get_mongo_env_config, is_mongo_enabled
        
        config = get_mongo_env_config()
        enabled = is_mongo_enabled()
        
        if config['mode'] == 'disabled' and not enabled:
            print_test("MongoDB disabled mode", True, "MONGO_MODE=disabled works")
            return True
        else:
            print_test("MongoDB disabled mode", False, f"mode={config['mode']}, enabled={enabled}")
            return False
    except Exception as e:
        print_test("MongoDB disabled mode", False, str(e))
        return False
    finally:
        os.environ.pop('MONGO_MODE', None)

def test_mongodb_custom_uri():
    """Test MongoDB custom URI"""
    try:
        clear_all_env_vars()
        custom_uri = "mongodb://customhost:27018/customdb"
        os.environ['MONGO_URI'] = custom_uri
        
        from app.utils.mongodb_manager import get_mongo_env_config
        
        config = get_mongo_env_config()
        
        if config['uri'] == custom_uri:
            print_test("MongoDB custom URI", True, f"Uses {custom_uri}")
            return True
        else:
            print_test("MongoDB custom URI", False, f"Expected {custom_uri}, got {config['uri']}")
            return False
    except Exception as e:
        print_test("MongoDB custom URI", False, str(e))
        return False
    finally:
        os.environ.pop('MONGO_URI', None)

def test_mongodb_uri_precedence():
    """Test MongoDB URI takes precedence over components"""
    try:
        clear_all_env_vars()
        os.environ['MONGO_URI'] = "mongodb://uri-host:27019/db"
        os.environ['MONGO_HOST'] = "component-host"
        os.environ['MONGO_PORT'] = "27020"
        
        from app.utils.mongodb_manager import get_mongo_env_config
        
        config = get_mongo_env_config()
        
        if config['uri'] == "mongodb://uri-host:27019/db":
            print_test("MongoDB URI precedence", True, "MONGO_URI overrides components")
            return True
        else:
            print_test("MongoDB URI precedence", False, f"URI: {config['uri']}")
            return False
    except Exception as e:
        print_test("MongoDB URI precedence", False, str(e))
        return False
    finally:
        os.environ.pop('MONGO_URI', None)
        os.environ.pop('MONGO_HOST', None)
        os.environ.pop('MONGO_PORT', None)

def test_mongodb_component_config():
    """Test MongoDB component-based configuration"""
    try:
        clear_all_env_vars()
        os.environ['MONGO_HOST'] = 'custom-mongo.example.com'
        os.environ['MONGO_PORT'] = '27018'
        os.environ['MONGO_USERNAME'] = 'admin'
        os.environ['MONGO_PASSWORD'] = 'secret'
        os.environ['DATABASE_NAME'] = 'CustomDB'
        
        from app.utils.mongodb_manager import get_mongo_env_config
        
        config = get_mongo_env_config()
        
        checks = [
            config['host'] == 'custom-mongo.example.com',
            config['port'] == 27018,
            config['username'] == 'admin',
            config['password'] == 'secret',
            config['database_name'] == 'CustomDB',
            'custom-mongo.example.com:27018' in config['uri']
        ]
        
        if all(checks):
            print_test("MongoDB component config", True, "All components configured correctly")
            return True
        else:
            print_test("MongoDB component config", False, f"Config: {config}")
            return False
    except Exception as e:
        print_test("MongoDB component config", False, str(e))
        return False
    finally:
        for key in ['MONGO_HOST', 'MONGO_PORT', 'MONGO_USERNAME', 'MONGO_PASSWORD', 'DATABASE_NAME']:
            os.environ.pop(key, None)

# =============================================================================
# TEST 2: ChromaDB Manager Tests
# =============================================================================

def test_chromadb_manager_import():
    """Test ChromaDB manager can be imported"""
    try:
        from app.utils.chroma_manager import get_chroma_env_config
        print_test("ChromaDB manager import", True, "Successfully imported")
        return True
    except Exception as e:
        print_test("ChromaDB manager import", False, str(e))
        return False

def test_chromadb_default_config():
    """Test ChromaDB default configuration"""
    try:
        clear_all_env_vars()
        from app.utils.chroma_manager import get_chroma_env_config
        
        config = get_chroma_env_config()
        
        if config['mode'] == 'enabled' and len(config['customers']) == 0:
            print_test("ChromaDB default config", True, "Enabled with no customers (backward compatible)")
            return True
        else:
            print_test("ChromaDB default config", False, f"mode={config['mode']}, customers={config['customers']}")
            return False
    except Exception as e:
        print_test("ChromaDB default config", False, str(e))
        return False

def test_chromadb_multi_tenant():
    """Test ChromaDB multi-tenant configuration"""
    try:
        clear_all_env_vars()
        os.environ['CHROMA_MODE'] = 'enabled'
        os.environ['CHROMA_CUSTOMERS'] = 'bank_a,bank_b,bank_c'
        os.environ['CHROMA_HOST_bank_a'] = 'chroma1.example.com'
        os.environ['CHROMA_PORT_bank_a'] = '8001'
        os.environ['CHROMA_HOST_bank_b'] = 'chroma2.example.com'
        os.environ['CHROMA_PORT_bank_b'] = '8002'
        os.environ['CHROMA_HOST_bank_c'] = 'chroma3.example.com'
        os.environ['CHROMA_PORT_bank_c'] = '8003'
        
        from app.utils.chroma_manager import get_chroma_env_config
        
        config = get_chroma_env_config()
        
        checks = [
            len(config['customers']) == 3,
            'bank_a' in config['customers'],
            'bank_b' in config['customers'],
            'bank_c' in config['customers'],
            config['per_customer_config']['bank_a']['host'] == 'chroma1.example.com',
            config['per_customer_config']['bank_a']['port'] == 8001,
            config['per_customer_config']['bank_b']['host'] == 'chroma2.example.com',
            config['per_customer_config']['bank_b']['port'] == 8002
        ]
        
        if all(checks):
            print_test("ChromaDB multi-tenant", True, "3 customers configured correctly")
            return True
        else:
            print_test("ChromaDB multi-tenant", False, f"Config: {config}")
            return False
    except Exception as e:
        print_test("ChromaDB multi-tenant", False, str(e))
        return False
    finally:
        for key in list(os.environ.keys()):
            if key.startswith('CHROMA_'):
                os.environ.pop(key, None)

def test_chromadb_disabled_mode():
    """Test ChromaDB disabled mode"""
    try:
        clear_all_env_vars()
        os.environ['CHROMA_MODE'] = 'disabled'
        
        from app.utils.chroma_manager import get_chroma_env_config
        
        config = get_chroma_env_config()
        
        if config['mode'] == 'disabled':
            print_test("ChromaDB disabled mode", True, "CHROMA_MODE=disabled works")
            return True
        else:
            print_test("ChromaDB disabled mode", False, f"mode should be disabled, got {config['mode']}")
            return False
    except Exception as e:
        print_test("ChromaDB disabled mode", False, str(e))
        return False
    finally:
        os.environ.pop('CHROMA_MODE', None)

# =============================================================================
# TEST 3: API Configuration Manager Tests
# =============================================================================

def test_api_manager_import():
    """Test API manager can be imported"""
    try:
        from app.utils.api_config_manager import get_api_env_config
        print_test("API manager import", True, "Successfully imported")
        return True
    except Exception as e:
        print_test("API manager import", False, str(e))
        return False

def test_azure_openai_default_enabled():
    """Test Azure OpenAI enabled by default"""
    try:
        clear_all_env_vars()
        from app.utils.api_config_manager import is_azure_openai_enabled
        
        if is_azure_openai_enabled():
            print_test("Azure OpenAI default enabled", True, "Enabled by default (backward compatible)")
            return True
        else:
            print_test("Azure OpenAI default enabled", False, "Should be enabled by default")
            return False
    except Exception as e:
        print_test("Azure OpenAI default enabled", False, str(e))
        return False

def test_azure_openai_disabled():
    """Test Azure OpenAI can be disabled"""
    try:
        clear_all_env_vars()
        os.environ['AZURE_OPENAI_ENABLED'] = 'false'
        
        from app.utils.api_config_manager import is_azure_openai_enabled, get_azure_openai_config
        
        enabled = is_azure_openai_enabled()
        config = get_azure_openai_config()
        
        if not enabled and config is None:
            print_test("Azure OpenAI disabled", True, "AZURE_OPENAI_ENABLED=false works")
            return True
        else:
            print_test("Azure OpenAI disabled", False, f"enabled={enabled}, config={config}")
            return False
    except Exception as e:
        print_test("Azure OpenAI disabled", False, str(e))
        return False
    finally:
        os.environ.pop('AZURE_OPENAI_ENABLED', None)

def test_api_validation():
    """Test API validation detects missing keys"""
    try:
        clear_all_env_vars()
        os.environ['AZURE_OPENAI_ENABLED'] = 'true'
        # Don't set API key
        
        from app.utils.api_config_manager import validate_api_config
        
        is_valid, error_msg = validate_api_config('azure_openai')
        
        if not is_valid and 'AZURE_OPENAI_API_KEY' in error_msg:
            print_test("API validation", True, "Detects missing API key")
            return True
        else:
            print_test("API validation", False, f"is_valid={is_valid}, msg={error_msg}")
            return False
    except Exception as e:
        print_test("API validation", False, str(e))
        return False
    finally:
        os.environ.pop('AZURE_OPENAI_ENABLED', None)

def test_multiple_api_providers():
    """Test multiple API providers can be configured"""
    try:
        clear_all_env_vars()
        os.environ['AZURE_OPENAI_ENABLED'] = 'true'
        os.environ['OPENAI_ENABLED'] = 'true'
        os.environ['ANTHROPIC_ENABLED'] = 'false'
        
        from app.utils.api_config_manager import is_azure_openai_enabled, is_openai_enabled, is_anthropic_enabled
        
        azure = is_azure_openai_enabled()
        openai = is_openai_enabled()
        anthropic = is_anthropic_enabled()
        
        if azure and openai and not anthropic:
            print_test("Multiple API providers", True, "Azure=on, OpenAI=on, Anthropic=off")
            return True
        else:
            print_test("Multiple API providers", False, f"azure={azure}, openai={openai}, anthropic={anthropic}")
            return False
    except Exception as e:
        print_test("Multiple API providers", False, str(e))
        return False
    finally:
        for key in ['AZURE_OPENAI_ENABLED', 'OPENAI_ENABLED', 'ANTHROPIC_ENABLED']:
            os.environ.pop(key, None)

def test_azure_openai_configuration():
    """Test Azure OpenAI full configuration"""
    try:
        clear_all_env_vars()
        os.environ['AZURE_OPENAI_ENABLED'] = 'true'
        os.environ['AZURE_OPENAI_API_KEY'] = 'test-key-123'
        os.environ['AZURE_OPENAI_API_BASE'] = 'https://test.openai.azure.com/'
        os.environ['AZURE_OPENAI_API_VERSION'] = '2024-02-15'
        os.environ['AZURE_OPENAI_DEPLOYMENT_NAME'] = 'gpt-4-test'
        
        from app.utils.api_config_manager import get_azure_openai_config
        
        config = get_azure_openai_config()
        
        checks = [
            config is not None,
            config.get('api_key') == 'test-key-123',
            config.get('api_base') == 'https://test.openai.azure.com/',
            config.get('api_version') == '2024-02-15',
            config.get('deployment_name') == 'gpt-4-test'
        ]
        
        if all(checks):
            print_test("Azure OpenAI configuration", True, "All config values set correctly")
            return True
        else:
            print_test("Azure OpenAI configuration", False, f"Config: {config}")
            return False
    except Exception as e:
        print_test("Azure OpenAI configuration", False, str(e))
        return False
    finally:
        for key in ['AZURE_OPENAI_ENABLED', 'AZURE_OPENAI_API_KEY', 'AZURE_OPENAI_API_BASE', 'AZURE_OPENAI_API_VERSION', 'AZURE_OPENAI_DEPLOYMENT_NAME']:
            os.environ.pop(key, None)

# =============================================================================
# Main Test Runner
# =============================================================================

def run_all_tests():
    """Run all test suites"""
    print_section("ENVIRONMENT VARIABLE MANAGERS TEST SUITE")
    
    saved_env = save_env_vars()
    
    try:
        # MongoDB Tests
        print_section("MongoDB Manager Tests")
        test_mongodb_manager_import()
        test_mongodb_default_config()
        test_mongodb_disabled_mode()
        test_mongodb_custom_uri()
        test_mongodb_uri_precedence()
        test_mongodb_component_config()
        
        # ChromaDB Tests
        print_section("ChromaDB Manager Tests")
        test_chromadb_manager_import()
        test_chromadb_default_config()
        test_chromadb_multi_tenant()
        test_chromadb_disabled_mode()
        
        # API Tests
        print_section("API Configuration Manager Tests")
        test_api_manager_import()
        test_azure_openai_default_enabled()
        test_azure_openai_disabled()
        test_api_validation()
        test_multiple_api_providers()
        test_azure_openai_configuration()
        
    finally:
        restore_env_vars(saved_env)
    
    # Print Summary
    print_section("TEST RESULTS SUMMARY")
    
    total_tests = len(test_results)
    passed_tests = sum(1 for _, passed, _ in test_results if passed)
    failed_tests = total_tests - passed_tests
    
    print(f"Total Tests:  {total_tests}")
    print(f"Passed:       {passed_tests} ✅")
    print(f"Failed:       {failed_tests} ❌")
    print(f"Success Rate: {(passed_tests/total_tests*100):.1f}%\n")
    
    if failed_tests > 0:
        print("\n❌ Failed Tests:")
        for name, passed, message in test_results:
            if not passed:
                print(f"  • {name}")
                if message:
                    print(f"    → {message}")
    else:
        print("✅ All tests passed!")
    
    print(f"\n{'='*70}\n")
    
    return failed_tests == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
