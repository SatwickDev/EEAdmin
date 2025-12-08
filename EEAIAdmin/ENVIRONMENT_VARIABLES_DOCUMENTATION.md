# Environment Variables Configuration Guide
**EEAIAdmin Application - Configuration Management System**

---

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [Overview of Changes](#overview-of-changes)
3. [Environment Variables Structure](#environment-variables-structure)
4. [ChromaDB Configuration](#chromadb-configuration)
5. [MongoDB Configuration](#mongodb-configuration)
6. [Azure API Configuration](#azure-api-configuration)
7. [Server Configuration](#server-configuration)
8. [Branding and Feature Flags](#branding-and-feature-flags)
9. [Customer-Based Enable/Disable Features](#customer-based-enabledisable-features)
10. [Implementation Examples](#implementation-examples)
11. [Migration from Hardcoded Values](#migration-from-hardcoded-values)
12. [Testing and Validation](#testing-and-validation)
13. [Troubleshooting Guide](#troubleshooting-guide)

---

## Executive Summary

The EEAIAdmin application has been enhanced with a comprehensive environment variable configuration system that replaces all hardcoded database connections, API keys, and service endpoints. This change provides:

- **Security**: Sensitive credentials no longer exist in source code
- **Flexibility**: Easy configuration changes without code modifications
- **Multi-tenancy**: Customer-specific service enable/disable capabilities
- **Deployment**: Simplified deployment across different environments (dev, staging, production)
- **Compliance**: Better adherence to security best practices

**Key Achievement**: All hardcoded values for ChromaDB, MongoDB, and Azure APIs have been successfully converted to environment variables with backward compatibility maintained.

---

## Overview of Changes

### What Was Changed

**Before:**
```python
# Hardcoded in source code
MONGO_URI = "mongodb://localhost:27017/"
CHROMA_HOST = "localhost"
AZURE_OPENAI_KEY = "sk-1234567890abcdef..."
```

**After:**
```python
# Loaded from environment variables
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
CHROMA_HOST = os.getenv('CHROMADB_HOST', 'localhost')
AZURE_OPENAI_KEY = os.getenv('AZURE_OPENAI_API_KEY')
```

### Components Modified

1. **ChromaDB Manager** (`app/utils/chromadb_repository_manager.py`)
   - 14 environment variables added
   - Multi-tenant configuration support
   - Customer-specific enable/disable functionality

2. **MongoDB Manager** (`app/utils/mongodb_manager.py`)
   - 14 environment variables added
   - Connection pooling configuration
   - Customer-based access control

3. **API Config Manager** (`app/utils/api_config_manager.py`)
   - 20+ environment variables added
   - Multiple AI provider support (OpenAI, Azure, Anthropic)
   - Deployment-specific configuration

4. **Server Configuration** (`run.py`)
   - 8 environment variables added
   - SSL/TLS configuration
   - Port and host configuration

---

## Environment Variables Structure

### File Location
All environment variables are defined in:
- **Primary**: `.env` (not committed to version control)
- **Template**: `.env.example` (committed to version control for reference)

### Variable Naming Convention
- **Uppercase with underscores**: `MONGO_URI`, `CHROMADB_HOST`
- **Prefixes by service**: 
  - `MONGO_*` for MongoDB
  - `CHROMADB_*` or `CHROMA_*` for ChromaDB
  - `AZURE_*` for Azure services
  - `OPENAI_*` for OpenAI services
  - `ANTHROPIC_*` for Anthropic services

---

## ChromaDB Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `CHROMA_MODE` | Operation mode: `enabled`, `multi-tenant`, `disabled` | `enabled` | No |
| `CHROMA_ENABLED_CUSTOMERS` | Comma-separated list of customer IDs (for multi-tenant) | `""` | No |
| `CHROMADB_HOST` | ChromaDB server hostname | `localhost` | No |
| `CHROMADB_PORT` | ChromaDB server port | `8000` | No |
| `CHROMADB_TIMEOUT` | Connection timeout in seconds | `30` | No |
| `CHROMADB_MAX_RETRIES` | Maximum connection retry attempts | `3` | No |
| `CHROMADB_RETRY_DELAY` | Delay between retries in seconds | `1` | No |
| `CHROMADB_TENANT_ID` | Default tenant identifier | `default` | No |
| `CHROMADB_AUTH_PROVIDER` | Authentication provider | `token` | No |
| `CHROMADB_AUTH_CREDENTIALS` | Authentication credentials | `""` | No |
| `CHROMADB_SSL` | Enable SSL connection | `false` | No |
| `CHROMADB_SSL_VERIFY` | Verify SSL certificates | `true` | No |
| `CHROMADB_ALLOW_RESET` | Allow database reset operations | `false` | No |
| `CHROMADB_ANONYMIZED_TELEMETRY` | Enable telemetry | `false` | No |

### Configuration Modes

#### 1. Enabled Mode (Default)
**All customers have access to ChromaDB**
```env
CHROMA_MODE=enabled
CHROMADB_HOST=localhost
CHROMADB_PORT=8000
```

#### 2. Multi-Tenant Mode
**Only specific customers have access**
```env
CHROMA_MODE=multi-tenant
CHROMA_ENABLED_CUSTOMERS=customer1,customer2,customer3
CHROMADB_HOST=chroma-prod.example.com
CHROMADB_PORT=8000
```

#### 3. Disabled Mode
**ChromaDB completely disabled**
```env
CHROMA_MODE=disabled
```

### Customer-Specific Enable/Disable

**To enable ChromaDB for specific customers:**

1. Set multi-tenant mode:
   ```env
   CHROMA_MODE=multi-tenant
   ```

2. List allowed customers:
   ```env
   CHROMA_ENABLED_CUSTOMERS=acme_corp,globex_inc,initech
   ```

3. Configure connection details:
   ```env
   CHROMADB_HOST=chroma-server.example.com
   CHROMADB_PORT=8000
   CHROMADB_TIMEOUT=60
   ```

**To disable ChromaDB entirely:**
```env
CHROMA_MODE=disabled
```

### Code Usage Example
```python
from app.utils.chromadb_repository_manager import ChromaDBRepositoryManager

# Initialize manager
chroma_manager = ChromaDBRepositoryManager()

# Check if ChromaDB is enabled for a customer
if chroma_manager.is_chromadb_enabled_for_customer('customer_id'):
    # Get ChromaDB client for this customer
    client = chroma_manager.get_chroma_client_for_customer('customer_id')
    # Use client for operations
```

---

## MongoDB Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `MONGO_MODE` | Operation mode: `enabled`, `multi-tenant`, `disabled` | `enabled` | No |
| `MONGO_ENABLED_CUSTOMERS` | Comma-separated customer IDs | `""` | No |
| `MONGO_URI` | MongoDB connection URI | `mongodb://localhost:27017/` | No |
| `MONGO_DATABASE` | Default database name | `finstack_dev` | No |
| `MONGO_TIMEOUT` | Connection timeout (ms) | `5000` | No |
| `MONGO_SERVER_SELECTION_TIMEOUT` | Server selection timeout (ms) | `5000` | No |
| `MONGO_SOCKET_TIMEOUT` | Socket timeout (ms) | `5000` | No |
| `MONGO_CONNECT_TIMEOUT` | Connect timeout (ms) | `5000` | No |
| `MONGO_MAX_POOL_SIZE` | Maximum connection pool size | `10` | No |
| `MONGO_MIN_POOL_SIZE` | Minimum connection pool size | `1` | No |
| `MONGO_MAX_IDLE_TIME` | Max connection idle time (ms) | `60000` | No |
| `MONGO_WAIT_QUEUE_TIMEOUT` | Wait queue timeout (ms) | `5000` | No |
| `MONGO_RETRY_WRITES` | Enable retry writes | `true` | No |
| `MONGO_RETRY_READS` | Enable retry reads | `true` | No |

### Configuration Modes

#### 1. Enabled Mode (Default)
**All customers have MongoDB access**
```env
MONGO_MODE=enabled
MONGO_URI=mongodb://localhost:27017/
MONGO_DATABASE=finstack_prod
```

#### 2. Multi-Tenant Mode
**Customer-specific database access**
```env
MONGO_MODE=multi-tenant
MONGO_ENABLED_CUSTOMERS=customer1,customer2,customer3
MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/
MONGO_DATABASE=finstack_prod
```

#### 3. Disabled Mode
**MongoDB completely disabled**
```env
MONGO_MODE=disabled
```

### Connection String Examples

**Local Development:**
```env
MONGO_URI=mongodb://localhost:27017/
MONGO_DATABASE=finstack_dev
```

**Production (MongoDB Atlas):**
```env
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority
MONGO_DATABASE=finstack_prod
MONGO_TIMEOUT=10000
MONGO_MAX_POOL_SIZE=50
```

**With Authentication:**
```env
MONGO_URI=mongodb://admin:secure_password@mongo-server:27017/admin?authSource=admin
MONGO_DATABASE=finstack
```

### Customer-Specific Enable/Disable

**To enable MongoDB for specific customers:**

1. Set multi-tenant mode:
   ```env
   MONGO_MODE=multi-tenant
   ```

2. Configure allowed customers:
   ```env
   MONGO_ENABLED_CUSTOMERS=customer_a,customer_b,customer_c
   ```

3. Set connection parameters:
   ```env
   MONGO_URI=mongodb+srv://prod-user:password@cluster.mongodb.net/
   MONGO_MAX_POOL_SIZE=100
   MONGO_TIMEOUT=10000
   ```

**To disable MongoDB entirely:**
```env
MONGO_MODE=disabled
```

### Code Usage Example
```python
from app.utils.mongodb_manager import get_mongo_database

# Get database connection for a customer
db = get_mongo_database('customer_id')

if db:
    # Perform database operations
    users = db.users.find({'active': True})
else:
    # MongoDB not available for this customer
    print("MongoDB access not enabled")
```

---

## Azure API Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key | - | Yes* |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL | - | Yes* |
| `AZURE_OPENAI_API_BASE` | Azure OpenAI base URL | - | Yes* |
| `AZURE_OPENAI_API_VERSION` | API version | `2024-10-01-preview` | No |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | Model deployment name | `gpt-4o` | No |
| `AZURE_EMBEDDING_DEPLOYMENT` | Embedding model deployment | `text-embedding-3-large` | No |
| `AZURE_EMBEDDING_MODEL` | Embedding model name | `text-embedding-3-large` | No |
| `AZURE_EMBEDDING_KEY` | Embedding API key | (uses `AZURE_OPENAI_API_KEY`) | No |
| `OPENAI_API_KEY` | Direct OpenAI API key | - | Yes* |
| `OPENAI_API_BASE` | OpenAI base URL | `https://api.openai.com/v1` | No |
| `OPENAI_API_VERSION` | OpenAI API version | `2024-10-01-preview` | No |
| `OPENAI_MODEL` | OpenAI model name | `gpt-4o` | No |
| `ANTHROPIC_API_KEY` | Anthropic (Claude) API key | - | Yes* |
| `ANTHROPIC_MODEL` | Claude model version | `claude-3-5-sonnet-20241022` | No |
| `ANTHROPIC_API_VERSION` | Anthropic API version | `2023-06-01` | No |
| `DEFAULT_LLM_PROVIDER` | Default AI provider | `azure` | No |
| `LLM_TIMEOUT` | LLM request timeout (seconds) | `120` | No |
| `LLM_MAX_RETRIES` | Maximum retry attempts | `3` | No |
| `LLM_RETRY_DELAY` | Delay between retries (seconds) | `2` | No |

*At least one AI provider key is required

### Configuration Examples

#### Azure OpenAI (Recommended for Enterprise)
```env
DEFAULT_LLM_PROVIDER=azure
AZURE_OPENAI_API_KEY=your-azure-api-key-here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_BASE=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
AZURE_EMBEDDING_DEPLOYMENT=text-embedding-3-large
```

#### Direct OpenAI
```env
DEFAULT_LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-openai-key-here
OPENAI_MODEL=gpt-4o
```

#### Anthropic Claude
```env
DEFAULT_LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-your-key-here
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
```

#### Multi-Provider Setup (Fallback)
```env
DEFAULT_LLM_PROVIDER=azure
AZURE_OPENAI_API_KEY=your-azure-key
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
```

### Provider-Specific Enable/Disable

**To switch AI providers:**

1. Change default provider:
   ```env
   DEFAULT_LLM_PROVIDER=anthropic
   ```

2. Ensure provider credentials are set:
   ```env
   ANTHROPIC_API_KEY=sk-ant-your-key-here
   ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
   ```

**To disable a specific provider:**
Simply remove or comment out its API key:
```env
# OPENAI_API_KEY=  # Disabled
```

### Code Usage Example
```python
from app.utils.api_config_manager import (
    get_default_llm_provider,
    get_azure_openai_key,
    get_openai_key
)

# Get current provider
provider = get_default_llm_provider()  # Returns: 'azure', 'openai', or 'anthropic'

# Get provider-specific keys
azure_key = get_azure_openai_key()
openai_key = get_openai_key()
```

---

## Server Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `SSL_ENABLED` | Enable HTTPS/SSL | `true` | No |
| `SSL_CERT_PATH` | Path to SSL certificate | `ssl/cert.pem` | No |
| `SSL_KEY_PATH` | Path to SSL private key | `ssl/key.pem` | No |
| `SERVER_HOST` | Server bind address | `0.0.0.0` | No |
| `HTTPS_PORT` | HTTPS port number | `443` | No |
| `HTTP_PORT` | HTTP port number | `80` | No |
| `DEBUG_MODE` | Enable debug mode | `true` | No |
| `ALLOW_UNSAFE_WERKZEUG` | Allow Werkzeug in production | `true` | No |

### Configuration Examples

#### Production (HTTPS)
```env
SSL_ENABLED=true
SSL_CERT_PATH=/etc/ssl/certs/app.crt
SSL_KEY_PATH=/etc/ssl/private/app.key
SERVER_HOST=0.0.0.0
HTTPS_PORT=443
DEBUG_MODE=false
ALLOW_UNSAFE_WERKZEUG=false
```

#### Development (HTTP)
```env
SSL_ENABLED=false
SERVER_HOST=127.0.0.1
HTTP_PORT=5000
DEBUG_MODE=true
ALLOW_UNSAFE_WERKZEUG=true
```

#### Custom Ports
```env
SSL_ENABLED=true
HTTPS_PORT=8443
HTTP_PORT=8080
SERVER_HOST=0.0.0.0
```

---

## Branding and Feature Flags

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `SHOW_FINSTACK_LOGO` | Show/hide logo and brand title | `true` | No |
| `LOGO_FILENAME` | Logo image filename (relative to static/img/) | `finstack.png` | No |
| `ENABLE_ADMIN_CONFIG` | Enable/disable Admin Configuration feature | `true` | No |

### Configuration Modes

#### Logo and Brand Title Control

**Show Logo and Brand Title (Default):**
```env
SHOW_FINSTACK_LOGO=true
LOGO_FILENAME=finstack.png
```

**Hide Logo and Brand Title:**
```env
SHOW_FINSTACK_LOGO=false
```

**Custom Logo:**
```env
SHOW_FINSTACK_LOGO=true
LOGO_FILENAME=company-logo.png
# Place your logo at: app/static/img/company-logo.png
```

#### Admin Configuration Control

**Enable Admin Features (Default):**
```env
ENABLE_ADMIN_CONFIG=true
```

**Disable Admin Features:**
```env
ENABLE_ADMIN_CONFIG=false
```

### What's Affected

#### Logo Configuration (`SHOW_FINSTACK_LOGO`)

**When `SHOW_FINSTACK_LOGO=true`:**
- ✅ Logo image displays on all pages
- ✅ Brand title (derived from filename) shows in headers
- ✅ Full branding visible on login/register pages
- ✅ Brand name appears in subtitles

**When `SHOW_FINSTACK_LOGO=false`:**
- ❌ Logo completely hidden
- ❌ Brand title text hidden
- ✅ Generic subtitles remain ("Enterprise Financial Platform")
- ✅ Application remains fully functional

**Pages Affected:**
- Login page
- Register page
- Dashboard header
- All 19 pages using floating header component:
  - AI Chat Pro
  - AI Chat Dashboard
  - Document Entity Maintenance
  - Analytics pages (Trade Finance, Cash Management, Treasury)
  - Form pages (Trade Finance, Cash Management, Treasury, Bank Guarantee)
  - Document Register
  - LC Transaction Catalog
  - Compliance Results
  - And more...

#### Admin Configuration (`ENABLE_ADMIN_CONFIG`)

**When `ENABLE_ADMIN_CONFIG=true`:**
- ✅ "Admin Configuration" link visible in navigation
- ✅ All admin routes accessible
- ✅ Admin API endpoints functional
- ✅ Full system administration available

**When `ENABLE_ADMIN_CONFIG=false`:**
- ❌ "Admin Configuration" link hidden from navigation
- ❌ Admin page route returns 403 Forbidden
- ❌ All admin API endpoints blocked (return 403)
- ✅ Regular application features remain accessible

**Affected Routes:**
- `/document_entity_maintenance` → 403 when disabled
- `/api/document_entity_maintenance` (GET, POST, PUT, DELETE) → 403 when disabled

### Use Cases

#### Use Case 1: White-Label Deployment
Deploy to customers without your branding:
```env
SHOW_FINSTACK_LOGO=false
ENABLE_ADMIN_CONFIG=false
```
Result: Clean interface without logo/brand, no admin access

#### Use Case 2: Customer-Specific Branding
Deploy with customer's logo:
```env
SHOW_FINSTACK_LOGO=true
LOGO_FILENAME=customer-acme-logo.png
ENABLE_ADMIN_CONFIG=true
```
Result: ACME Corp logo and branding throughout application

#### Use Case 3: Managed Service Provider
Control admin access per customer:
```env
# Internal customer (full access)
SHOW_FINSTACK_LOGO=true
ENABLE_ADMIN_CONFIG=true

# External customer (restricted)
SHOW_FINSTACK_LOGO=false
ENABLE_ADMIN_CONFIG=false
```

#### Use Case 4: Demo/Trial Environment
Clean demo without branding confusion:
```env
SHOW_FINSTACK_LOGO=false
ENABLE_ADMIN_CONFIG=false
```
Result: Generic platform for demos without specific branding

### Implementation Details

#### Context Processor
The application uses a Flask context processor to inject branding variables into all templates:

```python
@app.context_processor
def inject_branding_config():
    """Inject branding configuration into all templates"""
    show_logo = os.getenv('SHOW_FINSTACK_LOGO', 'true').lower() in ('true', '1', 'yes')
    logo_filename = os.getenv('LOGO_FILENAME', 'finstack.png')
    enable_admin = os.getenv('ENABLE_ADMIN_CONFIG', 'true').lower() in ('true', '1', 'yes')
    
    # Extract brand title from logo filename
    brand_title = logo_filename.split('.')[0].title() if show_logo else 'Platform'
    
    return dict(
        show_logo=show_logo,
        logo_filename=logo_filename,
        enable_admin_config=enable_admin,
        brand_title=brand_title
    )
```

#### Template Usage
Templates automatically have access to these variables:

**Floating Header (shared component):**
```html
{% if show_logo %}
<div class="logo-container">
    <img src="{{ url_for('static', filename='img/' + logo_filename) }}" 
         alt="{{ brand_title }} Logo">
</div>
{% endif %}

{% if show_logo %}
<h1 class="brand-title">{{ brand_title }}</h1>
{% endif %}

{% if enable_admin_config %}
<a href="/document_entity_maintenance">Admin Configuration</a>
{% endif %}
```

#### Route Protection
Admin routes check the configuration:

```python
@app.route('/document_entity_maintenance')
def document_entity_maintenance():
    enable_admin = os.getenv('ENABLE_ADMIN_CONFIG', 'true').lower() in ('true', '1', 'yes')
    if not enable_admin:
        return jsonify({'error': 'Admin configuration is disabled'}), 403
    return render_template('document_entity_maintenance.html')
```

### Azure Deployment

#### Set Environment Variables in Azure
```powershell
# Hide logo and disable admin for customer deployment
& "C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd" containerapp update `
  --name your-app-name `
  --resource-group your-rg `
  --set-env-vars "SHOW_FINSTACK_LOGO=false" "ENABLE_ADMIN_CONFIG=false"

# Custom branding with admin access
& "C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd" containerapp update `
  --name your-app-name `
  --resource-group your-rg `
  --set-env-vars "SHOW_FINSTACK_LOGO=true" "LOGO_FILENAME=customer-logo.png" "ENABLE_ADMIN_CONFIG=true"
```

#### Docker Deployment
In `docker-compose.yml`:
```yaml
services:
  app:
    environment:
      - SHOW_FINSTACK_LOGO=false
      - ENABLE_ADMIN_CONFIG=false
```

Or in Dockerfile:
```dockerfile
ENV SHOW_FINSTACK_LOGO=false
ENV ENABLE_ADMIN_CONFIG=false
```

### Testing Scenarios

#### Test 1: Logo Visibility
1. Set `SHOW_FINSTACK_LOGO=true`
2. Restart application
3. Check login page, dashboard, and any other page
4. Verify logo and brand title are visible

#### Test 2: Logo Hidden
1. Set `SHOW_FINSTACK_LOGO=false`
2. Restart application
3. Check all pages
4. Verify no logo or brand title appears
5. Verify subtitles still display

#### Test 3: Admin Access Enabled
1. Set `ENABLE_ADMIN_CONFIG=true`
2. Restart application
3. Check navigation for "Admin Configuration" link
4. Access `/document_entity_maintenance`
5. Verify admin features work

#### Test 4: Admin Access Disabled
1. Set `ENABLE_ADMIN_CONFIG=false`
2. Restart application
3. Verify "Admin Configuration" link not in navigation
4. Try accessing `/document_entity_maintenance`
5. Should receive 403 Forbidden error
6. Try accessing `/api/document_entity_maintenance`
7. Should receive 403 Forbidden error

---

## Customer-Based Enable/Disable Features

### Overview
The application supports customer-specific feature enabling/disabling for both ChromaDB and MongoDB through a multi-tenant configuration system.

### Architecture

```
┌─────────────────────────────────────────┐
│     Environment Variables (.env)         │
│  - CHROMA_MODE=multi-tenant             │
│  - CHROMA_ENABLED_CUSTOMERS=c1,c2,c3    │
│  - MONGO_MODE=multi-tenant              │
│  - MONGO_ENABLED_CUSTOMERS=c1,c2        │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│      Configuration Managers              │
│  - ChromaDBRepositoryManager            │
│  - MongoDB Manager                       │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│      Application Routes                  │
│  - Check customer access                │
│  - Initialize services conditionally     │
└─────────────────────────────────────────┘
```

### Implementation Steps

#### Step 1: Enable Multi-Tenant Mode

**For ChromaDB:**
```env
CHROMA_MODE=multi-tenant
CHROMA_ENABLED_CUSTOMERS=customer_a,customer_b,customer_c
```

**For MongoDB:**
```env
MONGO_MODE=multi-tenant
MONGO_ENABLED_CUSTOMERS=customer_a,customer_b,customer_c
```

#### Step 2: Customer Identification
Customers are identified by their unique customer ID in the application. This ID is typically:
- Stored in session
- Passed in API requests
- Retrieved from user authentication

#### Step 3: Runtime Checks
The application automatically checks customer access:

```python
# ChromaDB check
if chroma_manager.is_chromadb_enabled_for_customer(customer_id):
    # Customer has ChromaDB access
    client = chroma_manager.get_chroma_client_for_customer(customer_id)

# MongoDB check
if mongo_manager.is_mongodb_enabled_for_customer(customer_id):
    # Customer has MongoDB access
    db = mongo_manager.get_database_for_customer(customer_id)
```

### Use Cases

#### Use Case 1: Free vs Premium Tiers
```env
# Free tier: MongoDB only
MONGO_MODE=enabled
CHROMA_MODE=multi-tenant
CHROMA_ENABLED_CUSTOMERS=premium_customer_1,premium_customer_2

# Premium customers get ChromaDB for advanced features
```

#### Use Case 2: Phased Rollout
```env
# Start with pilot customers
CHROMA_MODE=multi-tenant
CHROMA_ENABLED_CUSTOMERS=pilot_customer_1,pilot_customer_2

# After validation, add more customers
CHROMA_ENABLED_CUSTOMERS=pilot_customer_1,pilot_customer_2,new_customer_3,new_customer_4
```

#### Use Case 3: Regional Restrictions
```env
# Different database instances per region
MONGO_URI=mongodb://us-east-server:27017/
MONGO_MODE=multi-tenant
MONGO_ENABLED_CUSTOMERS=us_customer_1,us_customer_2

# Separate config for EU customers would use different connection
```

### Adding/Removing Customers

**To add a customer:**
1. Update the enabled customers list:
   ```env
   CHROMA_ENABLED_CUSTOMERS=existing1,existing2,new_customer
   ```
2. Restart the application (or reload configuration if hot-reload is enabled)

**To remove a customer:**
1. Remove from the enabled customers list:
   ```env
   CHROMA_ENABLED_CUSTOMERS=customer1,customer2
   # customer3 removed
   ```
2. Restart the application

**To enable for all customers:**
Change mode from `multi-tenant` to `enabled`:
```env
CHROMA_MODE=enabled
# No need for CHROMA_ENABLED_CUSTOMERS
```

---

## Implementation Examples

### Complete .env File Example

```env
# ============================================
# MongoDB Configuration
# ============================================
MONGO_MODE=multi-tenant
MONGO_ENABLED_CUSTOMERS=acme_corp,globex_inc,initech
MONGO_URI=mongodb+srv://admin:password@cluster.mongodb.net/?retryWrites=true&w=majority
MONGO_DATABASE=finstack_prod
MONGO_TIMEOUT=10000
MONGO_MAX_POOL_SIZE=50
MONGO_MIN_POOL_SIZE=5
MONGO_RETRY_WRITES=true
MONGO_RETRY_READS=true

# ============================================
# ChromaDB Configuration
# ============================================
CHROMA_MODE=multi-tenant
CHROMA_ENABLED_CUSTOMERS=acme_corp,globex_inc
CHROMADB_HOST=chroma-prod.example.com
CHROMADB_PORT=8000
CHROMADB_TIMEOUT=60
CHROMADB_MAX_RETRIES=3
CHROMADB_SSL=true
CHROMADB_SSL_VERIFY=true

# ============================================
# Azure OpenAI Configuration
# ============================================
DEFAULT_LLM_PROVIDER=azure
AZURE_OPENAI_API_KEY=your-azure-api-key-here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_BASE=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-10-01-preview
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
AZURE_EMBEDDING_DEPLOYMENT=text-embedding-3-large
AZURE_EMBEDDING_MODEL=text-embedding-3-large

# ============================================
# OpenAI Configuration (Fallback)
# ============================================
OPENAI_API_KEY=sk-your-openai-key-here
OPENAI_MODEL=gpt-4o

# ============================================
# Anthropic Configuration (Optional)
# ============================================
ANTHROPIC_API_KEY=sk-ant-your-key-here
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022

# ============================================
# Server Configuration
# ============================================
SSL_ENABLED=true
SSL_CERT_PATH=/etc/ssl/certs/app.crt
SSL_KEY_PATH=/etc/ssl/private/app.key
SERVER_HOST=0.0.0.0
HTTPS_PORT=443
HTTP_PORT=80
DEBUG_MODE=false
ALLOW_UNSAFE_WERKZEUG=false

# ============================================
# Branding Configuration
# ============================================
SHOW_FINSTACK_LOGO=true
LOGO_FILENAME=finstack.png

# ============================================
# Feature Flags
# ============================================
ENABLE_ADMIN_CONFIG=true

# ============================================
# LLM Configuration
# ============================================
LLM_TIMEOUT=120
LLM_MAX_RETRIES=3
LLM_RETRY_DELAY=2
```

### Application Startup Code

**run.py:**
```python
import os
from app import create_app
from app.utils.daily_logger import log_system

if __name__ == "__main__":
    log_system("APPLICATION_STARTUP", message="Application startup initiated")
    
    app, socketio = create_app()

    # Get configuration from environment variables
    ssl_enabled = os.environ.get('SSL_ENABLED', 'true').lower() in ('true', '1', 'yes')
    ssl_cert = os.environ.get('SSL_CERT_PATH', 'ssl/cert.pem')
    ssl_key = os.environ.get('SSL_KEY_PATH', 'ssl/key.pem')
    host = os.environ.get('SERVER_HOST', '0.0.0.0')
    https_port = int(os.environ.get('HTTPS_PORT', 443))
    http_port = int(os.environ.get('HTTP_PORT', 80))
    debug = os.environ.get('DEBUG_MODE', 'true').lower() in ('true', '1', 'yes')

    if ssl_enabled:
        socketio.run(app, host=host, port=https_port, debug=debug,
                    ssl_context=(ssl_cert, ssl_key))
    else:
        socketio.run(app, host=host, port=http_port, debug=debug)
```

---

## Migration from Hardcoded Values

### Step-by-Step Migration Process

#### Phase 1: Create .env File
1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Fill in your values:
   ```env
   MONGO_URI=your_actual_mongodb_uri
   AZURE_OPENAI_API_KEY=your_actual_api_key
   ```

#### Phase 2: Update Configuration
1. Review all environment variables in `.env.example`
2. Set appropriate values for your environment
3. Ensure sensitive keys are never committed to version control

#### Phase 3: Test Configuration
1. Start the application
2. Verify all services connect successfully
3. Check logs for any configuration warnings

#### Phase 4: Deploy
1. Set environment variables in your deployment environment
2. For cloud platforms (Azure, AWS, etc.), use their secrets management
3. For Docker, use docker-compose.yml or Kubernetes secrets

### Before and After Comparison

**Before (Hardcoded):**
```python
# app/utils/app_config.py
MONGO_URI = "mongodb://localhost:27017/"
CHROMA_HOST = "localhost"
AZURE_KEY = "sk-1234567890abcdef..."  # Security risk!
```

**After (Environment Variables):**
```python
# app/utils/app_config.py
import os

MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
CHROMA_HOST = os.getenv('CHROMADB_HOST', 'localhost')
AZURE_KEY = os.getenv('AZURE_OPENAI_API_KEY')  # Secure!

if not AZURE_KEY:
    raise ValueError("AZURE_OPENAI_API_KEY environment variable is required")
```

---

## Testing and Validation

### Validation Checklist

#### MongoDB Testing
```python
# Test MongoDB connection
from app.utils.mongodb_manager import get_mongo_database

db = get_mongo_database()
if db:
    print("✅ MongoDB connected successfully")
    # Test operation
    result = db.command('ping')
    print(f"✅ MongoDB ping: {result}")
else:
    print("❌ MongoDB connection failed")
```

#### ChromaDB Testing
```python
# Test ChromaDB connection
from app.utils.chromadb_repository_manager import ChromaDBRepositoryManager

manager = ChromaDBRepositoryManager()
client = manager.get_chroma_client()
if client:
    print("✅ ChromaDB connected successfully")
    # Test operation
    collections = client.list_collections()
    print(f"✅ ChromaDB collections: {len(collections)}")
else:
    print("❌ ChromaDB connection failed")
```

#### Azure API Testing
```python
# Test Azure OpenAI connection
from app.utils.api_config_manager import get_azure_openai_key, get_azure_openai_endpoint

key = get_azure_openai_key()
endpoint = get_azure_openai_endpoint()

if key and endpoint:
    print("✅ Azure OpenAI configured")
    # Test API call
    import openai
    openai.api_key = key
    openai.api_base = endpoint
    # Make test call...
else:
    print("❌ Azure OpenAI not configured")
```

### Environment Validation Script

Create a script `test_env_config.py`:
```python
import os
from app.utils.mongodb_manager import get_mongo_config
from app.utils.chromadb_repository_manager import ChromaDBRepositoryManager
from app.utils.api_config_manager import get_default_llm_provider

def validate_environment():
    """Validate all environment configuration"""
    
    issues = []
    
    # Check MongoDB
    mongo_config = get_mongo_config()
    if mongo_config['mode'] == 'enabled' or mongo_config['mode'] == 'multi-tenant':
        if not os.getenv('MONGO_URI'):
            issues.append("⚠️ MONGO_URI not set")
    
    # Check ChromaDB
    chroma_manager = ChromaDBRepositoryManager()
    chroma_config = chroma_manager.get_chromadb_config()
    if chroma_config['mode'] == 'enabled' or chroma_config['mode'] == 'multi-tenant':
        if not os.getenv('CHROMADB_HOST'):
            issues.append("⚠️ CHROMADB_HOST not set")
    
    # Check AI Provider
    provider = get_default_llm_provider()
    if provider == 'azure' and not os.getenv('AZURE_OPENAI_API_KEY'):
        issues.append("❌ AZURE_OPENAI_API_KEY required for Azure provider")
    
    if issues:
        print("Configuration Issues Found:")
        for issue in issues:
            print(f"  {issue}")
        return False
    else:
        print("✅ All environment variables configured correctly")
        return True

if __name__ == "__main__":
    validate_environment()
```

---

## Troubleshooting Guide

### Common Issues and Solutions

#### Issue 1: MongoDB Connection Failed
**Symptoms:**
- Error: "ServerSelectionTimeoutError"
- Application cannot access database

**Solutions:**
1. Check MongoDB is running:
   ```bash
   # For local MongoDB
   sudo systemctl status mongod
   ```

2. Verify connection string:
   ```env
   MONGO_URI=mongodb://localhost:27017/
   # Ensure correct host, port, credentials
   ```

3. Check network connectivity:
   ```bash
   telnet localhost 27017
   ```

4. Increase timeout:
   ```env
   MONGO_TIMEOUT=10000
   MONGO_SERVER_SELECTION_TIMEOUT=10000
   ```

#### Issue 2: ChromaDB Not Connecting
**Symptoms:**
- Error: "Connection refused"
- ChromaDB features not working

**Solutions:**
1. Verify ChromaDB server is running:
   ```bash
   # Check if ChromaDB is running
   curl http://localhost:8000/api/v1/heartbeat
   ```

2. Check configuration:
   ```env
   CHROMADB_HOST=localhost
   CHROMADB_PORT=8000
   CHROMA_MODE=enabled
   ```

3. Start ChromaDB server:
   ```bash
   chroma run --host localhost --port 8000
   ```

4. Check firewall settings

#### Issue 3: Azure API Authentication Failed
**Symptoms:**
- Error: "InvalidAuthenticationToken"
- API calls failing with 401

**Solutions:**
1. Verify API key is correct:
   ```env
   AZURE_OPENAI_API_KEY=your-actual-key
   # Remove any extra spaces or quotes
   ```

2. Check endpoint URL:
   ```env
   AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
   # Must end with trailing slash
   ```

3. Verify API version:
   ```env
   AZURE_OPENAI_API_VERSION=2024-10-01-preview
   ```

4. Test with curl:
   ```bash
   curl -X POST "https://your-resource.openai.azure.com/openai/deployments/gpt-4o/chat/completions?api-version=2024-10-01-preview" \
     -H "api-key: YOUR_API_KEY" \
     -H "Content-Type: application/json"
   ```

#### Issue 4: Environment Variables Not Loading
**Symptoms:**
- Application using default values
- Configuration changes not taking effect

**Solutions:**
1. Check .env file location:
   ```bash
   ls -la .env
   # Should be in project root
   ```

2. Verify file format:
   - No spaces around `=`
   - No quotes unless needed
   - One variable per line

3. Restart application completely

4. Check for typos in variable names

#### Issue 5: Customer Access Denied
**Symptoms:**
- Customer cannot access ChromaDB/MongoDB
- Features disabled for specific customer

**Solutions:**
1. Check multi-tenant configuration:
   ```env
   CHROMA_MODE=multi-tenant
   CHROMA_ENABLED_CUSTOMERS=customer1,customer2,customer3
   ```

2. Verify customer ID is in list (case-sensitive)

3. Check for extra spaces:
   ```env
   # Wrong:
   CHROMA_ENABLED_CUSTOMERS=customer1, customer2, customer3
   
   # Correct:
   CHROMA_ENABLED_CUSTOMERS=customer1,customer2,customer3
   ```

4. Try enabled mode for testing:
   ```env
   CHROMA_MODE=enabled
   ```

### Logging and Debugging

Enable detailed logging:
```env
DEBUG_MODE=true
```

Check application logs:
```bash
# View logs
tail -f Logs/app_YYYY-MM-DD.log

# Search for errors
grep ERROR Logs/app_*.log
```

---

## Security Best Practices

### 1. Never Commit .env File
Add to `.gitignore`:
```
.env
.env.local
.env.*.local
```

### 2. Use Strong Credentials
- Generate complex passwords
- Rotate keys regularly
- Use different keys per environment

### 3. Restrict Access
- Use principle of least privilege
- Limit MongoDB user permissions
- Restrict API key scopes

### 4. Production Deployment
- Use secrets management (Azure Key Vault, AWS Secrets Manager)
- Never log sensitive values
- Use encrypted connections (SSL/TLS)

### 5. Regular Audits
- Review environment configurations
- Check for unused variables
- Update deprecated settings

---

## Support and Maintenance

### Configuration Updates
When updating environment variables:
1. Update `.env.example` with new variables
2. Document changes in this file
3. Notify team of required configuration changes
4. Update deployment documentation

### Version Control
- Keep `.env.example` in version control
- Never commit actual `.env` file
- Document all new environment variables

### Team Communication
When adding new environment variables:
1. Send notification to team
2. Update this documentation
3. Provide migration instructions if needed
4. Test in staging before production

---

## Appendix

### A. Complete Environment Variable Reference

See sections above for detailed descriptions of:
- 14 MongoDB variables
- 14 ChromaDB variables
- 20+ Azure/API variables
- 8 Server configuration variables
- 3 Branding and feature flag variables

### B. Default Values Summary

| Component | Mode Default | Host Default | Port Default |
|-----------|--------------|--------------|--------------|
| MongoDB | `enabled` | `localhost` | `27017` |
| ChromaDB | `enabled` | `localhost` | `8000` |
| Server (HTTPS) | `true` | `0.0.0.0` | `443` |
| Server (HTTP) | - | `0.0.0.0` | `80` |

### C. Migration Timeline

1. **Phase 1** (Completed): MongoDB Manager
2. **Phase 2** (Completed): ChromaDB Manager
3. **Phase 3** (Completed): API Config Manager
4. **Phase 4** (Completed): Server Configuration
5. **Phase 5** (Completed): Branding and Feature Flags
6. **Phase 6** (Current): Documentation and Testing

---

## Conclusion

The environment variable configuration system provides:
- ✅ Enhanced security (no hardcoded credentials)
- ✅ Flexible deployment (easy environment switching)
- ✅ Multi-tenant support (customer-specific features)
- ✅ White-label capability (configurable branding)
- ✅ Feature toggles (enable/disable admin features)
- ✅ Backward compatibility (defaults for all variables)
- ✅ Easy maintenance (centralized configuration)

### Recent Enhancements (December 2025)

**Branding Control:**
- Logo visibility can be toggled via `SHOW_FINSTACK_LOGO`
- Custom logos supported via `LOGO_FILENAME`
- Brand title automatically derived from logo filename
- All 19+ pages automatically inherit branding settings

**Feature Flags:**
- Admin configuration can be disabled via `ENABLE_ADMIN_CONFIG`
- Admin routes protected with 403 when disabled
- Admin API endpoints automatically blocked when feature disabled
- Navigation links conditionally rendered

**Benefits:**
- Deploy white-label versions to customers
- Control feature access per deployment
- Support multiple branding configurations
- Easy A/B testing and gradual rollouts

For questions or issues, contact the development team.

---

**Document Version:** 2.0  
**Last Updated:** December 5, 2025  
**Maintained By:** EEAIAdmin Development Team
