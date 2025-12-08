# Environment Variables Integration Guide
**Project:** EEAIAdmin - Enterprise AI Administration Platform  
**Date:** December 8, 2025  
**Author:** Development Team  

---

## 📋 Table of Contents

1. [Executive Summary](#executive-summary)
2. [What Has Been Implemented](#what-has-been-implemented)
3. [Integration Checklist](#integration-checklist)
4. [Step-by-Step Integration Process](#step-by-step-integration-process)
5. [Configuration Files Overview](#configuration-files-overview)
6. [Environment Variable Reference](#environment-variable-reference)
7. [Testing Your Integration](#testing-your-integration)
8. [Troubleshooting](#troubleshooting)
9. [Deployment Scenarios](#deployment-scenarios)

---

## 🎯 Executive Summary

### What This Integration Achieves

✅ **All hardcoded values removed** - No sensitive data in source code  
✅ **Centralized configuration** - All settings in `.env` file  
✅ **Environment-specific deployments** - Easy dev/staging/prod setup  
✅ **Security enhanced** - Credentials managed via environment variables  
✅ **Docker-ready** - Full containerization support  
✅ **Azure Container Apps ready** - Cloud deployment prepared  

### Key Components Now Using Environment Variables

1. **ChromaDB Configuration** - Host, port, mode, customer allowlist
2. **MongoDB Configuration** - URI, host, port, database, authentication
3. **Azure OpenAI** - API keys, endpoints, deployment names, versions
4. **Azure Embedding** - Embedding models and keys
5. **Azure Computer Vision** - OCR endpoints and keys
6. **OpenAI (non-Azure)** - Direct OpenAI API support
7. **Anthropic Claude** - Claude API integration
8. **Server Configuration** - SSL/TLS, ports, host settings
9. **Branding** - Logo visibility, custom branding
10. **Feature Flags** - Admin configuration enable/disable

---

## ✅ What Has Been Implemented

### 1. Configuration Manager Files

#### `app/utils/api_config_manager.py`
**Status:** ✅ Fully Implemented

**Features:**
- Azure OpenAI configuration (API base, key, deployment, version)
- OpenAI (non-Azure) configuration
- Anthropic Claude configuration
- API behavior settings (timeout, retries, temperature)
- Provider enable/disable switches
- Centralized configuration functions

**Key Functions:**
```python
get_api_config()                    # Get all API configurations
is_azure_openai_enabled()           # Check if Azure OpenAI is enabled
configure_azure_openai(openai)      # Configure OpenAI client
get_azure_openai_key()              # Get Azure OpenAI API key
get_azure_openai_endpoint()         # Get Azure endpoint
get_azure_deployment_name()         # Get deployment name
get_azure_api_version()             # Get API version
get_embedding_model()               # Get embedding model name
get_embedding_key()                 # Get embedding API key
```

#### `app/utils/mongodb_manager.py`
**Status:** ✅ Fully Implemented

**Features:**
- MongoDB connection management
- URI-based and component-based configuration
- Multi-tenant support (enable/disable per customer)
- Connection pooling
- Retry logic and error handling
- Mode-based control (enabled/disabled)

**Key Functions:**
```python
get_mongo_config()                  # Get MongoDB configuration
get_mongo_client()                  # Get MongoDB client
get_mongo_database(customer_id)     # Get database for customer
is_mongodb_enabled_for_customer()   # Check customer access
```

**Configuration Modes:**
- `MONGO_MODE=enabled` - All customers have access (default)
- `MONGO_MODE=disabled` - MongoDB completely disabled

#### `app/utils/chromadb_repository_manager.py`
**Status:** ✅ Fully Implemented

**Features:**
- ChromaDB connection management
- Multi-tenant configuration
- Customer-specific access control
- Mode-based operation (enabled/disabled/allowlist)
- Dynamic client creation
- Per-customer host/port configuration

**Key Functions:**
```python
get_chromadb_config()               # Get ChromaDB configuration
is_chromadb_enabled_for_customer()  # Check customer access
get_chroma_client_for_customer()    # Get client for customer
get_chroma_settings()               # Get ChromaDB settings
```

**Configuration Modes:**
- `CHROMA_MODE=enabled` - All customers have access
- `CHROMA_MODE=disabled` - ChromaDB completely disabled
- `CHROMA_MODE=allowlist` - Only specific customers (CHROMA_CUSTOMERS)

#### `run.py`
**Status:** ✅ Fully Implemented

**Features:**
- SSL/TLS configuration from environment variables
- Dynamic port configuration (HTTP/HTTPS)
- Server host configuration
- Debug mode control
- Werkzeug safety settings

**Environment Variables Used:**
```python
SSL_ENABLED                         # Enable/disable SSL
SSL_CERT_PATH                       # Path to SSL certificate
SSL_KEY_PATH                        # Path to SSL private key
SERVER_HOST                         # Server bind address
HTTPS_PORT                          # HTTPS port (default: 443)
HTTP_PORT                           # HTTP port (default: 80)
DEBUG_MODE                          # Enable debug mode
ALLOW_UNSAFE_WERKZEUG              # Allow Werkzeug in production
```

### 2. Application Integration

#### `app/routes.py`
**Status:** ✅ Integrated

**Features:**
- Context processor for branding configuration
- Admin configuration protection
- ChromaDB host/port from environment
- Azure OpenAI configuration usage
- Dynamic logo and feature visibility

**Key Integrations:**
```python
# Branding context processor (Lines 2213-2229)
@app.context_processor
def inject_branding_config()

# Admin configuration protection (Multiple routes)
enable_admin = os.getenv('ENABLE_ADMIN_CONFIG', 'true')

# ChromaDB from environment (Lines 389-390)
host = os.getenv('CHROMADB_HOST', 'localhost')
port = int(os.getenv('CHROMADB_PORT', 8000))
```

#### `app/utils/app_config.py`
**Status:** ✅ Integrated

**Features:**
- Uses api_config_manager for Azure OpenAI
- Computer Vision from environment
- OCR configuration from environment
- OpenAI parameters from environment
- Database credentials from environment (deprecated for MongoDB)

### 3. Docker and Deployment

#### `Dockerfile`
**Status:** ✅ Updated

**Changes:**
- ✅ Removed Oracle Instant Client installation
- ✅ Removed Oracle dependencies
- ✅ Optimized for environment variables
- ✅ Multi-stage build for smaller image
- ✅ Health check configuration

#### `docker-compose.yml`
**Status:** ⚠️ Needs Update (if exists)

**Required:**
- Environment variables section
- Volume mounts for .env file
- Network configuration
- Service dependencies

#### `.env`
**Status:** ✅ Comprehensive Template

**Sections:**
1. ~~Oracle Database~~ (Removed)
2. ChromaDB Configuration
3. MongoDB Configuration
4. Azure OpenAI Configuration
5. Azure Embedding Configuration
6. Azure Computer Vision Configuration
7. OpenAI (non-Azure) Configuration
8. Anthropic Configuration
9. API Behavior Settings
10. Application Configuration
11. Branding Configuration
12. Feature Flags
13. Server Configuration

---

## 📝 Integration Checklist

Use this checklist to ensure complete integration in your updated project:

### Phase 1: Configuration Files
- [ ] Copy `.env` file to your updated project root
- [ ] Copy `app/utils/api_config_manager.py` to your project
- [ ] Copy `app/utils/mongodb_manager.py` to your project
- [ ] Copy `app/utils/chromadb_repository_manager.py` to your project
- [ ] Update `run.py` with environment variable logic
- [ ] Update `.gitignore` to exclude `.env` file

### Phase 2: Code Integration
- [ ] Replace hardcoded Azure OpenAI keys with `get_azure_openai_key()`
- [ ] Replace hardcoded Azure endpoints with `get_azure_openai_endpoint()`
- [ ] Replace hardcoded MongoDB URIs with `get_mongo_config()`
- [ ] Replace hardcoded ChromaDB hosts with `get_chromadb_config()`
- [ ] Update all API calls to use `api_config_manager` functions
- [ ] Add branding context processor to `app/routes.py`

### Phase 3: Template Integration
- [ ] Update templates to use `show_logo` variable
- [ ] Update templates to use `enable_admin_config` variable
- [ ] Update navigation menus with conditional rendering
- [ ] Update login/register pages with branding variables

### Phase 4: Testing
- [ ] Test with all services enabled
- [ ] Test with ChromaDB disabled
- [ ] Test with MongoDB disabled
- [ ] Test with different branding settings
- [ ] Test with admin features disabled
- [ ] Test API connectivity with all providers

### Phase 5: Deployment
- [ ] Create `.env.example` for reference
- [ ] Document all environment variables
- [ ] Set up environment variables in deployment platform
- [ ] Test deployment with environment variables
- [ ] Verify SSL/TLS configuration
- [ ] Validate port configuration

---

## 🔧 Step-by-Step Integration Process

### Step 1: Backup Your Current Project

```powershell
# Create a backup of your project
cd C:\Users\saipr\Documents\GitHub
Copy-Item -Path "YourUpdatedProject" -Destination "YourUpdatedProject_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')" -Recurse
```

### Step 2: Copy Configuration Files

```powershell
# Navigate to your updated project
cd C:\Users\saipr\Documents\GitHub\YourUpdatedProject

# Copy .env file
Copy-Item -Path "..\EEAIAdmin\.env" -Destination "." -Force

# Copy manager files
Copy-Item -Path "..\EEAIAdmin\app\utils\api_config_manager.py" -Destination "app\utils\" -Force
Copy-Item -Path "..\EEAIAdmin\app\utils\mongodb_manager.py" -Destination "app\utils\" -Force
Copy-Item -Path "..\EEAIAdmin\app\utils\chromadb_repository_manager.py" -Destination "app\utils\" -Force

# Copy documentation
Copy-Item -Path "..\EEAIAdmin\ENVIRONMENT_VARIABLES_DOCUMENTATION.md" -Destination "." -Force
```

### Step 3: Update .gitignore

Add to your `.gitignore` file:
```gitignore
# Environment variables
.env
.env.local
.env.*.local
.env.backup

# IDE
.vscode/
.idea/

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python

# Logs
Logs/
*.log
```

### Step 4: Update run.py

Replace the server startup section in `run.py`:

```python
import os
from app import create_app
from app.utils.daily_logger import log_system

if __name__ == "__main__":
    log_system("APPLICATION_STARTUP", message="Application startup initiated")
    
    app, socketio = create_app()

    # Get configuration from environment variables
    ssl_enabled = os.environ.get('SSL_ENABLED', 'true').lower() in ('true', '1', 'yes')
    ssl_cert_path = os.environ.get('SSL_CERT_PATH', os.path.join('ssl', 'cert.pem'))
    ssl_key_path = os.environ.get('SSL_KEY_PATH', os.path.join('ssl', 'key.pem'))
    
    server_host = os.environ.get('SERVER_HOST', '0.0.0.0')
    https_port = int(os.environ.get('HTTPS_PORT', '443'))
    http_port = int(os.environ.get('HTTP_PORT', '80'))
    debug_mode = os.environ.get('DEBUG_MODE', 'true').lower() in ('true', '1', 'yes')
    allow_unsafe_werkzeug = os.environ.get('ALLOW_UNSAFE_WERKZEUG', 'true').lower() in ('true', '1', 'yes')

    if allow_unsafe_werkzeug:
        os.environ['WERKZEUG_RUN_MAIN'] = 'true'

    log_system("SERVER_CONFIG", message=f"SSL Enabled: {ssl_enabled}")
    log_system("SERVER_CONFIG", message=f"Host: {server_host}")
    log_system("SERVER_CONFIG", message=f"HTTPS Port: {https_port}" if ssl_enabled else f"HTTP Port: {http_port}")
    log_system("SERVER_CONFIG", message=f"Debug Mode: {debug_mode}")

    if ssl_enabled:
        if os.path.exists(ssl_cert_path) and os.path.exists(ssl_key_path):
            log_system("SSL_CONFIG", message=f"Using SSL certificates: {ssl_cert_path}, {ssl_key_path}")
            socketio.run(app, host=server_host, port=https_port, debug=debug_mode,
                        allow_unsafe_werkzeug=allow_unsafe_werkzeug,
                        ssl_context=(ssl_cert_path, ssl_key_path))
        else:
            log_system("SSL_WARNING", message=f"SSL certificates not found. Falling back to HTTP on port {http_port}")
            socketio.run(app, host=server_host, port=http_port, debug=debug_mode,
                        allow_unsafe_werkzeug=allow_unsafe_werkzeug)
    else:
        log_system("SERVER_INFO", message=f"SSL disabled. Running on HTTP port {http_port}")
        socketio.run(app, host=server_host, port=http_port, debug=debug_mode,
                    allow_unsafe_werkzeug=allow_unsafe_werkzeug)
```

### Step 5: Update app_config.py

Replace Azure OpenAI configuration section:

```python
import os
from dotenv import load_dotenv
import openai

from app.utils.api_config_manager import (
    configure_azure_openai,
    get_azure_deployment_name,
    get_azure_api_version,
    get_embedding_model,
    get_embedding_key,
    is_azure_openai_enabled
)

# Load environment variables
load_dotenv()

# OpenAI Configuration using centralized manager
try:
    logger.info("Starting Azure OpenAI configuration...")
    
    if not is_azure_openai_enabled():
        logger.warning("Azure OpenAI is disabled via AZURE_OPENAI_ENABLED=false")
        deployment_name = None
        embedding_model = None
        embedding_key = None
    else:
        success, deployment_name, error_msg = configure_azure_openai(openai)
        
        if not success:
            logger.error(f"Failed to configure Azure OpenAI: {error_msg}")
            raise ValueError(error_msg)
        
        embedding_model = get_embedding_model()
        embedding_key = get_embedding_key()
        
        logger.info(f"Azure OpenAI configured successfully")
        logger.info(f"Deployment: {deployment_name}")
        logger.info(f"Embedding Model: {embedding_model}")
        
except Exception as e:
    logger.error(f"Error configuring OpenAI: {e}")
    raise

# Azure Computer Vision Configuration
COMPUTER_VISION_ENDPOINT = os.getenv("AZURE_CV_ENDPOINT")
COMPUTER_VISION_KEY = os.getenv("AZURE_CV_KEY")

if not COMPUTER_VISION_ENDPOINT or not COMPUTER_VISION_KEY:
    logger.warning("Azure Computer Vision not configured")
```

### Step 6: Update Routes with Branding Context

Add this context processor to your `app/routes.py` (or wherever you initialize Flask):

```python
@app.context_processor
def inject_branding_config():
    """Inject branding configuration into all templates"""
    show_logo = os.getenv('SHOW_FINSTACK_LOGO', 'true').lower() in ('true', '1', 'yes')
    logo_filename = os.getenv('LOGO_FILENAME', 'finstack.png')
    enable_admin = os.getenv('ENABLE_ADMIN_CONFIG', 'true').lower() in ('true', '1', 'yes')
    
    # Extract brand title from logo filename (e.g., 'finstack.png' -> 'Finstack')
    brand_title = logo_filename.split('.')[0].title() if show_logo else 'Platform'
    
    return dict(
        show_logo=show_logo,
        logo_filename=logo_filename,
        enable_admin_config=enable_admin,
        brand_title=brand_title
    )
```

### Step 7: Update MongoDB Usage

Replace MongoDB connections:

**Before:**
```python
from pymongo import MongoClient
client = MongoClient("mongodb://localhost:27017/")
db = client["database_name"]
```

**After:**
```python
from app.utils.mongodb_manager import get_mongo_database

db = get_mongo_database("customer_id")  # or None for default
if db:
    # Use database
    collection = db["collection_name"]
else:
    # MongoDB not available
    logger.error("MongoDB not configured")
```

### Step 8: Update ChromaDB Usage

Replace ChromaDB connections:

**Before:**
```python
import chromadb
client = chromadb.HttpClient(host="localhost", port=8000)
```

**After:**
```python
from app.utils.chromadb_repository_manager import ChromaDBRepositoryManager

chroma_manager = ChromaDBRepositoryManager()
if chroma_manager.is_chromadb_enabled_for_customer("customer_id"):
    client = chroma_manager.get_chroma_client_for_customer("customer_id")
    # Use client
else:
    logger.warning("ChromaDB not available for this customer")
```

### Step 9: Update Azure OpenAI API Calls

Replace Azure OpenAI calls:

**Before:**
```python
import openai
openai.api_type = "azure"
openai.api_base = "https://your-resource.openai.azure.com/"
openai.api_key = "your-api-key"
openai.api_version = "2024-02-01"

response = openai.ChatCompletion.create(
    engine="gpt-4o",
    messages=[...]
)
```

**After:**
```python
from app.utils.api_config_manager import (
    configure_azure_openai,
    get_azure_deployment_name
)
import openai

# Configure once at startup (already done in app_config.py)
# Just use it:
deployment_name = get_azure_deployment_name()

response = openai.ChatCompletion.create(
    engine=deployment_name,
    messages=[...]
)
```

### Step 10: Update Templates

**✅ ALREADY IMPLEMENTED IN YOUR PROJECT!**

Your templates have already been updated with branding variables. Here's what's already in place:

#### **Files Already Updated:**

1. **`app/templates/index.html`** ✅
   - Logo display with `show_logo` check (lines 484, 489)
   - Brand title with conditional rendering (lines 489-491)
   - Admin Configuration link with `enable_admin_config` check (lines 682-688)

2. **`app/templates/components/floating_header.html`** ✅
   - Logo container with conditional rendering (line 9)
   - Brand title with `show_logo` check (line 19)
   - Admin Configuration navigation link with `enable_admin_config` check (lines 37-43)

#### **Route-Level Admin Protection:**

The following routes check `ENABLE_ADMIN_CONFIG` and return 403 if disabled:

```python
# Line 12393 - Page render
@app.route('/document_entity_maintenance')
def document_entity_maintenance():
    enable_admin = os.getenv('ENABLE_ADMIN_CONFIG', 'true').lower() in ('true', '1', 'yes')
    if not enable_admin:
        return jsonify({'error': 'Admin configuration is disabled'}), 403
    return render_template('document_entity_maintenance.html')

# Line 12402 - GET mappings
@app.route('/api/document_entity_maintenance', methods=['GET'])
def get_all_document_entity_mappings():
    enable_admin = os.getenv('ENABLE_ADMIN_CONFIG', 'true').lower() in ('true', '1', 'yes')
    if not enable_admin:
        return jsonify({'error': 'Admin configuration is disabled'}), 403

# Line 12416 - POST new mapping
@app.route('/api/document_entity_maintenance', methods=['POST'])
def create_document_entity_mapping():
    enable_admin = os.getenv('ENABLE_ADMIN_CONFIG', 'true').lower() in ('true', '1', 'yes')
    if not enable_admin:
        return jsonify({'error': 'Admin configuration is disabled'}), 403

# Line 12540 - DELETE mapping
@app.route('/api/document_entity_maintenance/<mapping_id>', methods=['DELETE'])
def delete_document_entity_mapping(mapping_id):
    enable_admin = os.getenv('ENABLE_ADMIN_CONFIG', 'true').lower() in ('true', '1', 'yes')
    if not enable_admin:
        return jsonify({'error': 'Admin configuration is disabled'}), 403
```

#### **Example Template Code (Already Implemented):**

**Header/Navigation Template:**
```html
<!-- Logo (from index.html line 484) -->
{% if show_logo %}
<img src="{{ url_for('static', filename='img/' + logo_filename) }}" 
     alt="{{ brand_title }} Logo" 
     style="width: 120px; height: auto; margin-bottom: 16px;">
{% endif %}

<!-- Brand Title (from index.html line 489) -->
{% if show_logo %}
<h2 class="text-h4 font-weight-bold">{{ brand_title }}</h2>
{% endif %}

<!-- Admin Link (from index.html line 682) -->
{% if enable_admin_config %}
<a href="/document_entity_maintenance" class="nav-pill">
    <i class="mdi mdi-cog-outline"></i>
    <span>Admin Configuration</span>
</a>
{% endif %}
```

**Floating Header Component (from floating_header.html):**
```html
<!-- Logo (line 9) -->
{% if show_logo %}
<div class="logo-container">
    <div class="modern-logo">
        <img src="{{ url_for('static', filename='img/' + logo_filename) }}" 
             alt="{{ brand_title }} Logo" 
             style="width: 40px; height: auto;">
    </div>
</div>
{% endif %}

<!-- Brand Info (line 19) -->
{% if show_logo %}
<h1 class="brand-title">{{ brand_title }}</h1>
{% endif %}

<!-- Admin Navigation (line 37) -->
{% if enable_admin_config %}
<a href="/document_entity_maintenance" class="nav-pill" data-page="ai-Admin">
    <i class="mdi mdi-cog-outline"></i>
    <span>Admin Configuration</span>
</a>
{% endif %}
```

#### **How It Works:**

1. **Branding Context Processor** (in `setup_routes()` at line 2216):
   ```python
   @app.context_processor
   def inject_branding_config():
       show_logo = os.getenv('SHOW_FINSTACK_LOGO', 'true').lower() in ('true', '1', 'yes')
       logo_filename = os.getenv('LOGO_FILENAME', 'finstack.png')
       enable_admin = os.getenv('ENABLE_ADMIN_CONFIG', 'true').lower() in ('true', '1', 'yes')
       brand_title = logo_filename.split('.')[0].title() if show_logo else 'Platform'
       
       return dict(
           show_logo=show_logo,
           logo_filename=logo_filename,
           enable_admin_config=enable_admin,
           brand_title=brand_title
       )
   ```

2. **Environment Variables Control:**
   - `SHOW_FINSTACK_LOGO=false` → Hides logo and brand title across all pages
   - `LOGO_FILENAME=custom.png` → Changes logo to custom image
   - `ENABLE_ADMIN_CONFIG=false` → Hides admin links AND blocks admin routes (403 Forbidden)

3. **Security Layers:**
   - **UI Layer:** Links hidden when `enable_admin_config=false`
   - **Route Layer:** API endpoints return 403 when `ENABLE_ADMIN_CONFIG=false`
   - **Double Protection:** Even if user knows URL, they can't access admin features

#### **Testing Your Branding Configuration:**

```powershell
# Test 1: Hide logo and branding
# In .env file:
SHOW_FINSTACK_LOGO=false

# Result: No logo or brand title visible, only "Enterprise Financial Platform" subtitle

# Test 2: Custom branding
SHOW_FINSTACK_LOGO=true
LOGO_FILENAME=mycompany.png

# Result: Shows mycompany.png as logo, "Mycompany" as brand title

# Test 3: Disable admin features
ENABLE_ADMIN_CONFIG=false

# Result: 
# - Admin Configuration link hidden in navigation
# - Direct access to /document_entity_maintenance returns 403
# - All admin API endpoints return 403
```

#### **✅ Your Templates Are Already Complete!**

No additional template changes are needed. Your project already has:
- ✅ Conditional logo rendering
- ✅ Conditional brand title rendering  
- ✅ Conditional admin link rendering
- ✅ Route-level admin protection
- ✅ Context processor injecting variables
- ✅ Multiple templates using branding variables

**Next Step:** Just configure your `.env` file with your preferred branding settings!

---

## 📁 Configuration Files Overview

### 1. `.env` File Structure

```dotenv
# =============================================================================
# CHROMADB CONFIGURATION
# =============================================================================
CHROMA_MODE=enabled
CHROMA_CUSTOMERS=
CHROMA_HOST=localhost
CHROMA_PORT=8000

# =============================================================================
# MONGODB CONFIGURATION
# =============================================================================
MONGO_MODE=enabled
MONGO_URI=mongodb://localhost:27017/
DATABASE_NAME=finai_chatbot

# =============================================================================
# AZURE OPENAI CONFIGURATION
# =============================================================================
AZURE_OPENAI_ENABLED=true
AZURE_OPENAI_API_BASE=https://your-resource.openai.azure.com
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
AZURE_OPENAI_API_VERSION=2024-10-01-preview

# =============================================================================
# AZURE EMBEDDING CONFIGURATION
# =============================================================================
AZURE_EMBEDDING_MODEL=text-embedding-3-large
AZURE_EMBEDDING_KEY=your-embedding-key

# =============================================================================
# AZURE COMPUTER VISION CONFIGURATION
# =============================================================================
AZURE_CV_ENDPOINT=https://your-cv.cognitiveservices.azure.com/
AZURE_CV_KEY=your-cv-key

# =============================================================================
# BRANDING CONFIGURATION
# =============================================================================
SHOW_FINSTACK_LOGO=true
LOGO_FILENAME=finstack.png

# =============================================================================
# FEATURE FLAGS
# =============================================================================
ENABLE_ADMIN_CONFIG=true

# =============================================================================
# SERVER CONFIGURATION
# =============================================================================
SSL_ENABLED=true
SSL_CERT_PATH=ssl/cert.pem
SSL_KEY_PATH=ssl/key.pem
SERVER_HOST=0.0.0.0
HTTPS_PORT=443
HTTP_PORT=80
DEBUG_MODE=true
```

### 2. Create `.env.example`

Create a template without sensitive data:

```dotenv
# Copy this file to .env and fill in your actual values

# ChromaDB Configuration
CHROMA_MODE=enabled
CHROMA_HOST=localhost
CHROMA_PORT=8000

# MongoDB Configuration
MONGO_MODE=enabled
MONGO_URI=mongodb://localhost:27017/
DATABASE_NAME=your_database_name

# Azure OpenAI Configuration
AZURE_OPENAI_ENABLED=true
AZURE_OPENAI_API_BASE=https://your-resource.openai.azure.com
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o

# Azure Computer Vision
AZURE_CV_ENDPOINT=https://your-cv.cognitiveservices.azure.com/
AZURE_CV_KEY=your-cv-key-here

# Server Configuration
SSL_ENABLED=true
HTTPS_PORT=443
HTTP_PORT=80
```

---

## 📚 Environment Variable Reference

### ChromaDB Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `CHROMA_MODE` | Operation mode: enabled, disabled, allowlist | `enabled` | No |
| `CHROMA_CUSTOMERS` | Comma-separated customer IDs for allowlist mode | `""` | No |
| `CHROMA_HOST` | ChromaDB server hostname | `localhost` | No |
| `CHROMA_PORT` | ChromaDB server port | `8000` | No |

### MongoDB Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `MONGO_MODE` | Operation mode: enabled, disabled | `enabled` | No |
| `MONGO_URI` | MongoDB connection URI | `mongodb://localhost:27017/` | No |
| `MONGO_HOST` | MongoDB hostname (if not using URI) | `localhost` | No |
| `MONGO_PORT` | MongoDB port | `27017` | No |
| `DATABASE_NAME` | Database name | `finai_chatbot` | No |

### Azure OpenAI Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `AZURE_OPENAI_ENABLED` | Enable/disable Azure OpenAI | `true` | No |
| `AZURE_OPENAI_API_BASE` | Azure OpenAI endpoint URL | - | Yes* |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key | - | Yes* |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | Model deployment name | `gpt-4o` | No |
| `AZURE_OPENAI_API_VERSION` | API version | `2024-10-01-preview` | No |

*Required when AZURE_OPENAI_ENABLED=true

### Azure Embedding Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `AZURE_EMBEDDING_MODEL` | Embedding model name | `text-embedding-ada-002` | No |
| `AZURE_EMBEDDING_KEY` | Embedding API key | (uses OpenAI key) | No |

### Azure Computer Vision Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `AZURE_CV_ENDPOINT` | Computer Vision endpoint | - | Yes |
| `AZURE_CV_KEY` | Computer Vision API key | - | Yes |

### Branding Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `SHOW_FINSTACK_LOGO` | Show/hide logo and brand title | `true` | No |
| `LOGO_FILENAME` | Logo filename (in static/img/) | `finstack.png` | No |
| `ENABLE_ADMIN_CONFIG` | Enable/disable admin features | `true` | No |

### Server Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `SSL_ENABLED` | Enable/disable SSL | `true` | No |
| `SSL_CERT_PATH` | SSL certificate path | `ssl/cert.pem` | No |
| `SSL_KEY_PATH` | SSL private key path | `ssl/key.pem` | No |
| `SERVER_HOST` | Server bind address | `0.0.0.0` | No |
| `HTTPS_PORT` | HTTPS port | `443` | No |
| `HTTP_PORT` | HTTP port | `80` | No |
| `DEBUG_MODE` | Enable debug mode | `true` | No |

---

## 🧪 Testing Your Integration

### Test 1: Configuration Loading

Create `test_config.py`:

```python
import os
from dotenv import load_dotenv

load_dotenv()

def test_configuration():
    """Test that all environment variables are loaded"""
    
    print("=" * 60)
    print("CONFIGURATION TEST")
    print("=" * 60)
    
    # ChromaDB
    print("\n📦 ChromaDB Configuration:")
    print(f"  Mode: {os.getenv('CHROMA_MODE', 'not set')}")
    print(f"  Host: {os.getenv('CHROMA_HOST', 'not set')}")
    print(f"  Port: {os.getenv('CHROMA_PORT', 'not set')}")
    
    # MongoDB
    print("\n🍃 MongoDB Configuration:")
    print(f"  Mode: {os.getenv('MONGO_MODE', 'not set')}")
    print(f"  URI: {os.getenv('MONGO_URI', 'not set')}")
    print(f"  Database: {os.getenv('DATABASE_NAME', 'not set')}")
    
    # Azure OpenAI
    print("\n🤖 Azure OpenAI Configuration:")
    print(f"  Enabled: {os.getenv('AZURE_OPENAI_ENABLED', 'not set')}")
    print(f"  Base: {os.getenv('AZURE_OPENAI_API_BASE', 'not set')}")
    print(f"  Key Present: {'Yes' if os.getenv('AZURE_OPENAI_API_KEY') else 'No'}")
    print(f"  Deployment: {os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME', 'not set')}")
    
    # Branding
    print("\n🎨 Branding Configuration:")
    print(f"  Show Logo: {os.getenv('SHOW_FINSTACK_LOGO', 'not set')}")
    print(f"  Logo File: {os.getenv('LOGO_FILENAME', 'not set')}")
    print(f"  Admin Enabled: {os.getenv('ENABLE_ADMIN_CONFIG', 'not set')}")
    
    # Server
    print("\n🌐 Server Configuration:")
    print(f"  SSL Enabled: {os.getenv('SSL_ENABLED', 'not set')}")
    print(f"  Host: {os.getenv('SERVER_HOST', 'not set')}")
    print(f"  HTTPS Port: {os.getenv('HTTPS_PORT', 'not set')}")
    print(f"  HTTP Port: {os.getenv('HTTP_PORT', 'not set')}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    test_configuration()
```

Run it:
```powershell
python test_config.py
```

### Test 2: Manager Functions

Create `test_managers.py`:

```python
from app.utils.api_config_manager import get_api_config, is_azure_openai_enabled
from app.utils.mongodb_manager import get_mongo_config
from app.utils.chromadb_repository_manager import ChromaDBRepositoryManager

def test_managers():
    print("\n" + "=" * 60)
    print("MANAGER TESTS")
    print("=" * 60)
    
    # API Config Manager
    print("\n🔧 API Config Manager:")
    try:
        api_config = get_api_config()
        print(f"  ✅ Azure OpenAI Enabled: {api_config['azure_openai']['enabled']}")
        print(f"  ✅ Deployment: {api_config['azure_openai']['deployment_name']}")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    # MongoDB Manager
    print("\n🍃 MongoDB Manager:")
    try:
        mongo_config = get_mongo_config()
        print(f"  ✅ Mode: {mongo_config['mode']}")
        print(f"  ✅ URI Present: {'Yes' if mongo_config['uri'] else 'No'}")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    # ChromaDB Manager
    print("\n📦 ChromaDB Manager:")
    try:
        chroma_manager = ChromaDBRepositoryManager()
        chroma_config = chroma_manager.get_chromadb_config()
        print(f"  ✅ Mode: {chroma_config['mode']}")
        print(f"  ✅ Host: {chroma_config['host']}")
        print(f"  ✅ Port: {chroma_config['port']}")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    test_managers()
```

Run it:
```powershell
python test_managers.py
```

### Test 3: Application Startup

```powershell
# Start the application
python run.py

# Check logs for configuration messages
```

Expected log output:
```
[INFO] Azure OpenAI configured successfully
[INFO] MongoDB connected successfully
[INFO] ChromaDB mode: enabled
[INFO] Server listening on https://0.0.0.0:443
```

---

## 🔧 Troubleshooting

### Issue 1: Environment Variables Not Loading

**Symptoms:**
- Application uses default values
- "Environment variable not set" warnings

**Solutions:**
1. Verify `.env` file exists in project root
2. Check file has no BOM (Byte Order Mark)
3. Ensure `load_dotenv()` is called before accessing variables
4. Check for typos in variable names (case-sensitive)

```python
from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()

# Verify loading
print("MONGO_URI:", os.getenv('MONGO_URI'))
```

### Issue 2: Import Errors for Manager Files

**Symptoms:**
- `ModuleNotFoundError: No module named 'app.utils.api_config_manager'`

**Solutions:**
1. Ensure manager files are in `app/utils/` directory
2. Check `__init__.py` exists in `app/utils/`
3. Verify Python path includes project root

```python
import sys
sys.path.append('C:/Users/saipr/Documents/GitHub/YourProject')
```

### Issue 3: MongoDB Connection Failed

**Symptoms:**
- `ServerSelectionTimeoutError`
- Can't connect to database

**Solutions:**
1. Verify MongoDB is running:
```powershell
# Check MongoDB status
Get-Service MongoDB
```

2. Test connection string:
```python
from pymongo import MongoClient
try:
    client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=5000)
    client.server_info()
    print("MongoDB connected!")
except Exception as e:
    print(f"Connection failed: {e}")
```

3. Check firewall settings
4. Verify URI format in `.env`

### Issue 4: Azure OpenAI Authentication Failed

**Symptoms:**
- `InvalidAuthenticationToken`
- 401 Unauthorized

**Solutions:**
1. Verify API key in `.env`:
```python
import os
from dotenv import load_dotenv

load_dotenv()
key = os.getenv('AZURE_OPENAI_API_KEY')
print(f"Key length: {len(key) if key else 0}")
print(f"Key starts with: {key[:10] if key else 'None'}")
```

2. Check endpoint URL (must end with `/`)
3. Verify deployment name matches Azure portal
4. Test with curl:
```powershell
$headers = @{
    "api-key" = "YOUR_API_KEY"
    "Content-Type" = "application/json"
}
Invoke-WebRequest -Uri "https://your-resource.openai.azure.com/openai/deployments/gpt-4o/chat/completions?api-version=2024-10-01-preview" -Method POST -Headers $headers
```

### Issue 5: SSL Certificate Errors

**Symptoms:**
- Certificate not found
- SSL handshake failed

**Solutions:**
1. Generate self-signed certificates:
```powershell
python generate_cert.py
```

2. Verify certificate paths in `.env`
3. Check file permissions
4. For development, disable SSL:
```dotenv
SSL_ENABLED=false
```

---

## 🚀 Deployment Scenarios

### Scenario 1: Local Development

**.env configuration:**
```dotenv
# Development settings
DEBUG_MODE=true
SSL_ENABLED=false
HTTP_PORT=5000

# Local services
MONGO_URI=mongodb://localhost:27017/
CHROMA_HOST=localhost
CHROMA_PORT=8000

# Development Azure keys
AZURE_OPENAI_ENABLED=true
AZURE_OPENAI_API_BASE=https://dev-resource.openai.azure.com
```

### Scenario 2: Staging Environment

**.env configuration:**
```dotenv
# Staging settings
DEBUG_MODE=true
SSL_ENABLED=true
HTTPS_PORT=443

# Staging MongoDB (Atlas)
MONGO_URI=mongodb+srv://staging-user:password@staging-cluster.mongodb.net/
DATABASE_NAME=finstack_staging

# Staging Azure resources
AZURE_OPENAI_API_BASE=https://staging-resource.openai.azure.com
```

### Scenario 3: Production Deployment

**.env configuration:**
```dotenv
# Production settings
DEBUG_MODE=false
SSL_ENABLED=true
HTTPS_PORT=443
ALLOW_UNSAFE_WERKZEUG=false

# Production MongoDB
MONGO_URI=mongodb+srv://prod-user:secure-password@prod-cluster.mongodb.net/?retryWrites=true&w=majority
DATABASE_NAME=finstack_prod

# Production Azure (use secure key management)
AZURE_OPENAI_API_BASE=https://prod-resource.openai.azure.com

# Branding
SHOW_FINSTACK_LOGO=true
ENABLE_ADMIN_CONFIG=true
```

### Scenario 4: Azure Container Apps

**Environment variables in Azure Portal:**
```
MONGO_URI=mongodb+srv://...
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_API_BASE=...
SSL_ENABLED=false  # Azure handles SSL
HTTP_PORT=8080     # Non-privileged port
DEBUG_MODE=false
```

**Deployment command:**
```powershell
az containerapp update `
  --name your-app `
  --resource-group your-rg `
  --set-env-vars `
    "MONGO_URI=$env:MONGO_URI" `
    "AZURE_OPENAI_API_KEY=$env:AZURE_OPENAI_API_KEY" `
    "AZURE_OPENAI_API_BASE=$env:AZURE_OPENAI_API_BASE" `
    "SSL_ENABLED=false" `
    "HTTP_PORT=8080" `
    "DEBUG_MODE=false"
```

### Scenario 5: Docker Compose

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "443:443"
      - "80:80"
    environment:
      - MONGO_URI=${MONGO_URI}
      - AZURE_OPENAI_API_KEY=${AZURE_OPENAI_API_KEY}
      - AZURE_OPENAI_API_BASE=${AZURE_OPENAI_API_BASE}
      - SSL_ENABLED=true
      - DEBUG_MODE=false
    env_file:
      - .env
    volumes:
      - ./ssl:/app/ssl
      - ./Logs:/app/Logs
    networks:
      - finstack-network

  mongodb:
    image: mongo:latest
    ports:
      - "27017:27017"
    volumes:
      - mongodb-data:/data/db
    networks:
      - finstack-network

  chromadb:
    image: chromadb/chroma:latest
    ports:
      - "8000:8000"
    volumes:
      - chromadb-data:/chroma/chroma
    networks:
      - finstack-network

networks:
  finstack-network:
    driver: bridge

volumes:
  mongodb-data:
  chromadb-data:
```

---

## 📞 Support and Next Steps

### Next Steps After Integration

1. **Test Locally:**
   - Run all test scripts
   - Verify each service connects
   - Test all features

2. **Update Documentation:**
   - Document your specific configuration
   - Create deployment runbooks
   - Update team wiki

3. **Set Up CI/CD:**
   - Add environment variables to CI/CD pipeline
   - Create deployment scripts
   - Set up automated testing

4. **Security Audit:**
   - Review .gitignore
   - Verify no secrets in code
   - Set up secrets management

5. **Deploy:**
   - Deploy to staging first
   - Run integration tests
   - Deploy to production

### Additional Resources

- **Environment Variables Documentation:** `ENVIRONMENT_VARIABLES_DOCUMENTATION.md`
- **API Config Manager:** `app/utils/api_config_manager.py`
- **MongoDB Manager:** `app/utils/mongodb_manager.py`
- **ChromaDB Manager:** `app/utils/chromadb_repository_manager.py`

### Getting Help

If you encounter issues during integration:

1. Check the troubleshooting section above
2. Review log files in `Logs/` directory
3. Run test scripts to isolate the problem
4. Check environment variable values with test_config.py

---

**Document Version:** 1.0  
**Last Updated:** December 8, 2025  
**Status:** Ready for Integration  

---

## ✅ Quick Start Commands

```powershell
# 1. Navigate to your updated project
cd C:\Users\saipr\Documents\GitHub\YourUpdatedProject

# 2. Copy all configuration files
Copy-Item -Path "..\EEAIAdmin\.env" -Destination "."
Copy-Item -Path "..\EEAIAdmin\app\utils\api_config_manager.py" -Destination "app\utils\"
Copy-Item -Path "..\EEAIAdmin\app\utils\mongodb_manager.py" -Destination "app\utils\"
Copy-Item -Path "..\EEAIAdmin\app\utils\chromadb_repository_manager.py" -Destination "app\utils\"

# 3. Test configuration
python test_config.py

# 4. Test managers
python test_managers.py

# 5. Start application
python run.py
```

Good luck with your integration! 🚀
