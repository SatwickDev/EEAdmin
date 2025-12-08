#!/usr/bin/env python3
"""
Environment Variable Configuration Test Suite
Tests all environment variable configurations for MongoDB, ChromaDB, and APIs
Verifies backward compatibility and graceful degradation
"""

import os
import sys
import logging
from typing import Dict, List, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

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
    return {
        key: os.environ.get(key) 
        for key in [
            'MONGO_MODE', 'MONGO_URI', 'MONGO_HOST', 'MONGO_PORT',
            'CHROMA_MODE', 'CHROMA_CUSTOMERS',
            'AZURE_OPENAI_ENABLED', 'AZURE_OPENAI_API_KEY', 'AZURE_OPENAI_API_BASE'
        ]
    }

def restore_env_vars(saved: Dict[str, str]):
    """Restore environment variables"""
    for key, value in saved.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value

# =============================================================================
# TEST 1: MongoDB Configuration Tests
# =============================================================================

def test_mongodb_default_connection():
    """Test MongoDB with default configuration (backward compatibility)"""
    try:
        from app.utils.mongodb_manager import get_mongo_client, get_database, get_connection_info
        
        # Clear environment variables to test defaults
        os.environ.pop('MONGO_MODE', None)
        os.environ.pop('MONGO_URI', None)
        
        info = get_connection_info()
        expected_uri = "mongodb://localhost:27017/"
        
        if expected_uri in info['uri']:
            print_test("MongoDB default configuration", True, "Uses localhost:27017")
            return True
        else:
            print_test("MongoDB default configuration", False, f"Expected {expected_uri}, got {info['uri']}")
            return False
    except Exception as e:
        print_test("MongoDB default configuration", False, str(e))
        return False

def test_mongodb_disabled_mode():
    """Test MongoDB with MONGO_MODE=disabled"""
    try:
        from app.utils.mongodb_manager import get_mongo_client, is_mongo_enabled
        
        # Set disabled mode
        os.environ['MONGO_MODE'] = 'disabled'
        
        if not is_mongo_enabled():
            client = get_mongo_client()
            if client is None:
                print_test("MongoDB disabled mode", True, "Returns None when disabled")
                return True
            else:
                print_test("MongoDB disabled mode", False, "Should return None")
                return False
        else:
            print_test("MongoDB disabled mode", False, "is_mongo_enabled() should return False")
            return False
    except Exception as e:
        print_test("MongoDB disabled mode", False, str(e))
        return False
    finally:
        os.environ.pop('MONGO_MODE', None)

def test_mongodb_custom_uri():
    """Test MongoDB with custom MONGO_URI"""
    try:
        from app.utils.mongodb_manager import get_connection_info
        
        custom_uri = "mongodb://customhost:27018/customdb"
        os.environ['MONGO_URI'] = custom_uri
        
        info = get_connection_info()
        
        if custom_uri in info['uri']:
            print_test("MongoDB custom URI", True, "Uses custom MONGO_URI")
            return True
        else:
            print_test("MongoDB custom URI", False, f"Expected {custom_uri}")
            return False
    except Exception as e:
        print_test("MongoDB custom URI", False, str(e))
        return False
    finally:
        os.environ.pop('MONGO_URI', None)

def test_mongodb_env_precedence():
    """Test MongoDB configuration precedence (URI > components > defaults)"""
    try:
        from app.utils.mongodb_manager import get_mongo_env_config
        
        # Set both URI and components
        os.environ['MONGO_URI'] = "mongodb://uri-host:27019/db"
        os.environ['MONGO_HOST'] = "component-host"
        os.environ['MONGO_PORT'] = "27020"
        
        config = get_mongo_env_config()
        
        # URI should take precedence
        if config['uri'] == "mongodb://uri-host:27019/db":
            print_test("MongoDB config precedence", True, "MONGO_URI takes precedence")
            return True
        else:
            print_test("MongoDB config precedence", False, "URI should override components")
            return False
    except Exception as e:
        print_test("MongoDB config precedence", False, str(e))
        return False
    finally:
        os.environ.pop('MONGO_URI', None)
        os.environ.pop('MONGO_HOST', None)
        os.environ.pop('MONGO_PORT', None)

# =============================================================================
# TEST 2: ChromaDB Configuration Tests
# =============================================================================

def test_chromadb_default_configuration():
    """Test ChromaDB with default configuration"""
    try:
        from app.utils.chroma_manager import get_chroma_env_config
        
        # Clear environment variables
        os.environ.pop('CHROMA_MODE', None)
        os.environ.pop('CHROMA_CUSTOMERS', None)
        
        config = get_chroma_env_config()
        
        if config['mode'] == 'enabled' and len(config['customers']) == 0:
            print_test("ChromaDB default config", True, "Enabled with no customers (backward compatible)")
            return True
        else:
            print_test("ChromaDB default config", False, f"Got mode={config['mode']}, customers={config['customers']}")
            return False
    except Exception as e:
        print_test("ChromaDB default config", False, str(e))
        return False

def test_chromadb_multi_tenant():
    """Test ChromaDB multi-tenant configuration"""
    try:
        from app.utils.chroma_manager import get_chroma_env_config
        
        # Configure multi-tenant
        os.environ['CHROMA_MODE'] = 'enabled'
        os.environ['CHROMA_CUSTOMERS'] = 'bank_a,bank_b,bank_c'
        os.environ['CHROMA_HOST_bank_a'] = 'chroma1.example.com'
        os.environ['CHROMA_PORT_bank_a'] = '8001'
        os.environ['CHROMA_HOST_bank_b'] = 'chroma2.example.com'
        os.environ['CHROMA_PORT_bank_b'] = '8002'
        
        config = get_chroma_env_config()
        
        if len(config['customers']) == 3 and 'bank_a' in config['customers']:
            bank_a_config = config['per_customer_config']['bank_a']
            if bank_a_config['host'] == 'chroma1.example.com' and bank_a_config['port'] == 8001:
                print_test("ChromaDB multi-tenant", True, "3 customers configured correctly")
                return True
        
        print_test("ChromaDB multi-tenant", False, "Configuration mismatch")
        return False
    except Exception as e:
        print_test("ChromaDB multi-tenant", False, str(e))
        return False
    finally:
        for key in list(os.environ.keys()):
            if key.startswith('CHROMA_'):
                os.environ.pop(key, None)

def test_chromadb_disabled_mode():
    """Test ChromaDB with CHROMA_MODE=disabled"""
    try:
        from app.utils.chroma_manager import get_chroma_env_config
        
        os.environ['CHROMA_MODE'] = 'disabled'
        
        config = get_chroma_env_config()
        
        if config['mode'] == 'disabled':
            print_test("ChromaDB disabled mode", True, "Correctly disabled")
            return True
        else:
            print_test("ChromaDB disabled mode", False, f"Mode should be disabled, got {config['mode']}")
            return False
    except Exception as e:
        print_test("ChromaDB disabled mode", False, str(e))
        return False
    finally:
        os.environ.pop('CHROMA_MODE', None)

# =============================================================================
# TEST 3: API Configuration Tests
# =============================================================================

def test_azure_openai_default_enabled():
    """Test Azure OpenAI enabled by default"""
    try:
        from app.utils.api_config_manager import is_azure_openai_enabled
        
        # Clear environment variable
        os.environ.pop('AZURE_OPENAI_ENABLED', None)
        
        if is_azure_openai_enabled():
            print_test("Azure OpenAI default enabled", True, "Enabled by default")
            return True
        else:
            print_test("Azure OpenAI default enabled", False, "Should be enabled by default")
            return False
    except Exception as e:
        print_test("Azure OpenAI default enabled", False, str(e))
        return False

def test_azure_openai_disabled_mode():
    """Test Azure OpenAI with AZURE_OPENAI_ENABLED=false"""
    try:
        from app.utils.api_config_manager import is_azure_openai_enabled, get_azure_openai_config
        
        os.environ['AZURE_OPENAI_ENABLED'] = 'false'
        
        if not is_azure_openai_enabled():
            config = get_azure_openai_config()
            if config is None:
                print_test("Azure OpenAI disabled mode", True, "Correctly disabled, returns None")
                return True
            else:
                print_test("Azure OpenAI disabled mode", False, "Should return None when disabled")
                return False
        else:
            print_test("Azure OpenAI disabled mode", False, "Should be disabled")
            return False
    except Exception as e:
        print_test("Azure OpenAI disabled mode", False, str(e))
        return False
    finally:
        os.environ.pop('AZURE_OPENAI_ENABLED', None)

def test_api_validation():
    """Test API configuration validation"""
    try:
        from app.utils.api_config_manager import validate_api_config
        
        # Test without API key
        os.environ.pop('AZURE_OPENAI_API_KEY', None)
        os.environ.pop('AZURE_OPENAI_API_BASE', None)
        os.environ['AZURE_OPENAI_ENABLED'] = 'true'
        
        is_valid, error_msg = validate_api_config('azure_openai')
        
        if not is_valid and 'AZURE_OPENAI_API_KEY' in error_msg:
            print_test("API validation", True, "Detects missing API key")
            return True
        else:
            print_test("API validation", False, "Should detect missing configuration")
            return False
    except Exception as e:
        print_test("API validation", False, str(e))
        return False
    finally:
        os.environ.pop('AZURE_OPENAI_ENABLED', None)

def test_multiple_api_providers():
    """Test multiple API provider configuration"""
    try:
        from app.utils.api_config_manager import is_azure_openai_enabled, is_openai_enabled, is_anthropic_enabled
        
        # Configure multiple providers
        os.environ['AZURE_OPENAI_ENABLED'] = 'true'
        os.environ['OPENAI_ENABLED'] = 'true'
        os.environ['ANTHROPIC_ENABLED'] = 'false'
        
        azure_enabled = is_azure_openai_enabled()
        openai_enabled = is_openai_enabled()
        anthropic_enabled = is_anthropic_enabled()
        
        if azure_enabled and openai_enabled and not anthropic_enabled:
            print_test("Multiple API providers", True, "Azure=on, OpenAI=on, Anthropic=off")
            return True
        else:
            print_test("Multiple API providers", False, "Configuration mismatch")
            return False
    except Exception as e:
        print_test("Multiple API providers", False, str(e))
        return False
    finally:
        os.environ.pop('AZURE_OPENAI_ENABLED', None)
        os.environ.pop('OPENAI_ENABLED', None)
        os.environ.pop('ANTHROPIC_ENABLED', None)

# =============================================================================
# TEST 4: Integration Tests
# =============================================================================

def test_app_config_integration():
    """Test app_config.py integrates with api_config_manager"""
    try:
        # This tests that app_config.py can import and use the manager
        from app.utils.app_config import deployment_name, embedding_model
        
        # Should not raise errors even if not fully configured
        print_test("App config integration", True, "Successfully imports and configures")
        return True
    except Exception as e:
        print_test("App config integration", False, str(e))
        return False

def test_backward_compatibility():
    """Test complete backward compatibility"""
    try:
        # Clear ALL custom environment variables
        for key in list(os.environ.keys()):
            if any(key.startswith(prefix) for prefix in ['MONGO_', 'CHROMA_', 'AZURE_OPENAI_', 'OPENAI_', 'ANTHROPIC_', 'API_']):
                os.environ.pop(key, None)
        
        # Test that everything works with defaults
        from app.utils.mongodb_manager import get_connection_info as mongo_info
        from app.utils.chroma_manager import get_chroma_env_config
        from app.utils.api_config_manager import is_azure_openai_enabled
        
        mongo_config = mongo_info()
        chroma_config = get_chroma_env_config()
        azure_enabled = is_azure_openai_enabled()
        
        # Verify defaults
        checks = [
            'localhost' in mongo_config['uri'],
            chroma_config['mode'] == 'enabled',
            azure_enabled == True
        ]
        
        if all(checks):
            print_test("Backward compatibility", True, "All defaults work correctly")
            return True
        else:
            print_test("Backward compatibility", False, "Defaults don't match expectations")
            return False
    except Exception as e:
        print_test("Backward compatibility", False, str(e))
        return False

# =============================================================================
# Main Test Runner
# =============================================================================

def run_all_tests():
    """Run all test suites"""
    print_section("ENVIRONMENT VARIABLE CONFIGURATION TEST SUITE")
    
    # Save current environment
    saved_env = save_env_vars()
    
    try:
        # MongoDB Tests
        print_section("MongoDB Configuration Tests")
        test_mongodb_default_connection()
        test_mongodb_disabled_mode()
        test_mongodb_custom_uri()
        test_mongodb_env_precedence()
        
        # ChromaDB Tests
        print_section("ChromaDB Configuration Tests")
        test_chromadb_default_configuration()
        test_chromadb_multi_tenant()
        test_chromadb_disabled_mode()
        
        # API Tests
        print_section("API Configuration Tests")
        test_azure_openai_default_enabled()
        test_azure_openai_disabled_mode()
        test_api_validation()
        test_multiple_api_providers()
        
        # Integration Tests
        print_section("Integration Tests")
        test_app_config_integration()
        test_backward_compatibility()
        
    finally:
        # Restore environment
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
        print("Failed Tests:")
        for name, passed, message in test_results:
            if not passed:
                print(f"  ❌ {name}")
                if message:
                    print(f"     → {message}")
    
    print(f"\n{'='*70}\n")
    
    return failed_tests == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
