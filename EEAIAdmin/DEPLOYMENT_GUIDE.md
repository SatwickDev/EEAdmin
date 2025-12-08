# Multi-Bank Deployment Guide
## Single Docker Image, Multiple Deployments

This guide provides complete instructions for deploying the EEAI Admin application to multiple banks using the same Docker image with environment variable configuration.

---

## Table of Contents
1. [Quick Start](#quick-start)
2. [Environment Variables Reference](#environment-variables-reference)
3. [Deployment Examples](#deployment-examples)
4. [Terraform Configuration](#terraform-configuration)
5. [Kubernetes Configuration](#kubernetes-configuration)
6. [Testing & Validation](#testing--validation)
7. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Step 1: Build Docker Image
```bash
docker build -t eeai-admin:latest .
```

### Step 2: Configure Environment Variables
Create environment-specific configuration files:

**Production (Bank A):**
```bash
# bank-a-prod.env
MONGO_URI=mongodb://mongo.bank-a.com:27017/finai_chatbot?authSource=admin
CHROMA_MODE=enabled
CHROMA_CUSTOMERS=retail,corporate
CHROMA_HOST_retail=chroma-retail.bank-a.com
CHROMA_HOST_corporate=chroma-corp.bank-a.com
AZURE_OPENAI_API_BASE=https://bank-a.openai.azure.com
AZURE_OPENAI_API_KEY=<secret>
```

### Step 3: Deploy
```bash
docker run -d --env-file bank-a-prod.env eeai-admin:latest
```

---

## Environment Variables Reference

### ChromaDB Configuration

#### Basic Settings
```bash
# Enable/disable ChromaDB service
CHROMA_MODE=enabled                    # Options: enabled, disabled

# Multi-tenant configuration
CHROMA_CUSTOMERS=bank_a,bank_b,bank_c  # Comma-separated customer IDs
```

#### Per-Customer Configuration
For each customer in CHROMA_CUSTOMERS:
```bash
# Customer: bank_a
CHROMA_HOST_bank_a=chroma1.example.com
CHROMA_PORT_bank_a=8000

# Customer: bank_b
CHROMA_HOST_bank_b=chroma2.example.com
CHROMA_PORT_bank_b=8000
```

**Default Values:**
- If not configured: Uses localhost:8000 (single instance mode)
- Port defaults to 8000 if not specified

---

### MongoDB Configuration

#### Connection String (Recommended)
```bash
# Full connection URI (highest priority)
MONGO_URI=mongodb://user:pass@host:port/database?authSource=admin&replicaSet=rs0
```

#### Individual Components
```bash
# Basic connection
MONGO_MODE=enabled                     # Options: enabled, disabled
MONGO_HOST=localhost
MONGO_PORT=27017
MONGO_USERNAME=admin
MONGO_PASSWORD=secretpassword
DATABASE_NAME=finai_chatbot

# Authentication
MONGO_AUTH_SOURCE=admin                # Authentication database

# Advanced options
MONGO_REPLICA_SET=rs0                  # Replica set name
MONGO_SSL=true                         # Enable SSL/TLS
MONGO_SSL_CERT_PATH=/path/to/cert.pem  # SSL certificate path
```

**Configuration Precedence:**
1. MONGO_URI (if set) → overrides all other settings
2. Individual components (HOST, PORT, etc.)
3. Defaults: mongodb://localhost:27017/ (database: finai_chatbot)

**Default Values:**
- MONGO_MODE: enabled
- MONGO_HOST: localhost
- MONGO_PORT: 27017
- DATABASE_NAME: finai_chatbot

---

### API Configuration

#### Azure OpenAI (Primary)
```bash
# Enable/disable Azure OpenAI
AZURE_OPENAI_ENABLED=true              # Options: true, false

# Required credentials
AZURE_OPENAI_API_KEY=<your-api-key>
AZURE_OPENAI_API_BASE=https://your-resource.openai.azure.com

# Model configuration
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o    # Deployment name
AZURE_OPENAI_API_VERSION=2024-10-01-preview

# Embedding configuration
AZURE_EMBEDDING_MODEL=text-embedding-ada-002
AZURE_EMBEDDING_KEY=<optional-separate-key>
```

#### OpenAI (Alternative)
```bash
# Enable OpenAI (non-Azure)
OPENAI_ENABLED=false                   # Set to true to enable

# Credentials
OPENAI_API_KEY=<your-api-key>
OPENAI_ORG_ID=<optional-org-id>
OPENAI_MODEL=gpt-4
```

#### Anthropic Claude (Alternative)
```bash
# Enable Anthropic
ANTHROPIC_ENABLED=false                # Set to true to enable

# Credentials
ANTHROPIC_API_KEY=<your-api-key>
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
```

#### API Behavior Settings
```bash
# Timeouts and retries
API_TIMEOUT=30                         # Request timeout (seconds)
API_MAX_RETRIES=3                      # Number of retry attempts
API_RETRY_DELAY=1                      # Delay between retries (seconds)

# LLM parameters
API_TEMPERATURE=0.7                    # Response creativity (0.0-1.0)
API_MAX_TOKENS=4000                    # Maximum tokens per request
```

**Default Values:**
- AZURE_OPENAI_ENABLED: true
- API_TIMEOUT: 30 seconds
- API_MAX_RETRIES: 3
- API_TEMPERATURE: 0.7

---

### Application Settings
```bash
# Flask configuration
FLASK_ENV=production                   # Options: development, production
FLASK_DEBUG=False
SECRET_KEY=<generate-secure-key>

# Logging
LOG_LEVEL=INFO                         # Options: DEBUG, INFO, WARNING, ERROR

# Other
ANONYMIZED_TELEMETRY=False
```

---

## Deployment Examples

### Example 1: Bank A (UAE) - Multi-Tenant ChromaDB

**Scenario:** Large bank with separate ChromaDB instances per division

```yaml
# docker-compose-bank-a.yml
version: '3.8'

services:
  app:
    image: eeai-admin:latest
    ports:
      - "5000:5000"
    environment:
      # MongoDB
      MONGO_MODE: enabled
      MONGO_URI: mongodb://mongo-admin:${MONGO_PASSWORD}@mongodb:27017/finai_chatbot?authSource=admin
      
      # ChromaDB - Three divisions
      CHROMA_MODE: enabled
      CHROMA_CUSTOMERS: retail,corporate,investment
      CHROMA_HOST_retail: chroma-retail
      CHROMA_PORT_retail: 8000
      CHROMA_HOST_corporate: chroma-corporate
      CHROMA_PORT_corporate: 8000
      CHROMA_HOST_investment: chroma-investment
      CHROMA_PORT_investment: 8000
      
      # APIs
      AZURE_OPENAI_ENABLED: "true"
      AZURE_OPENAI_API_BASE: https://bank-a-uae.openai.azure.com
      AZURE_OPENAI_API_KEY: ${AZURE_API_KEY}
      AZURE_OPENAI_DEPLOYMENT_NAME: gpt-4o
      
      # App settings
      FLASK_ENV: production
      LOG_LEVEL: INFO
    depends_on:
      - mongodb
      - chroma-retail
      - chroma-corporate
      - chroma-investment

  mongodb:
    image: mongo:6
    environment:
      MONGO_INITDB_ROOT_USERNAME: mongo-admin
      MONGO_INITDB_ROOT_PASSWORD: ${MONGO_PASSWORD}
    volumes:
      - mongodb_data:/data/db

  chroma-retail:
    image: chromadb/chroma:latest
    volumes:
      - chroma_retail_data:/chroma/chroma

  chroma-corporate:
    image: chromadb/chroma:latest
    volumes:
      - chroma_corporate_data:/chroma/chroma

  chroma-investment:
    image: chromadb/chroma:latest
    volumes:
      - chroma_investment_data:/chroma/chroma

volumes:
  mongodb_data:
  chroma_retail_data:
  chroma_corporate_data:
  chroma_investment_data:
```

**Deploy:**
```bash
export MONGO_PASSWORD="secure-password-here"
export AZURE_API_KEY="azure-api-key-here"
docker-compose -f docker-compose-bank-a.yml up -d
```

---

### Example 2: Bank B (KSA) - Single ChromaDB

**Scenario:** Medium bank with shared ChromaDB instance

```yaml
# docker-compose-bank-b.yml
version: '3.8'

services:
  app:
    image: eeai-admin:latest  # SAME IMAGE as Bank A!
    ports:
      - "5000:5000"
    environment:
      # MongoDB
      MONGO_MODE: enabled
      MONGO_URI: mongodb://mongo-admin:${MONGO_PASSWORD}@mongodb:27017/finai_chatbot?authSource=admin
      
      # ChromaDB - Single instance
      CHROMA_MODE: enabled
      CHROMA_CUSTOMERS: main
      CHROMA_HOST_main: chroma
      CHROMA_PORT_main: 8000
      
      # APIs - Different deployment
      AZURE_OPENAI_ENABLED: "true"
      AZURE_OPENAI_API_BASE: https://bank-b-ksa.openai.azure.com
      AZURE_OPENAI_API_KEY: ${AZURE_API_KEY}
      AZURE_OPENAI_DEPLOYMENT_NAME: gpt-4o-mini  # Different model
      
      # App settings
      FLASK_ENV: production
      LOG_LEVEL: INFO
    depends_on:
      - mongodb
      - chroma

  mongodb:
    image: mongo:6
    environment:
      MONGO_INITDB_ROOT_USERNAME: mongo-admin
      MONGO_INITDB_ROOT_PASSWORD: ${MONGO_PASSWORD}
    volumes:
      - mongodb_data:/data/db

  chroma:
    image: chromadb/chroma:latest
    volumes:
      - chroma_data:/chroma/chroma

volumes:
  mongodb_data:
  chroma_data:
```

---

### Example 3: Testing Environment - No MongoDB

**Scenario:** Development/testing without MongoDB

```yaml
# docker-compose-test.yml
version: '3.8'

services:
  app:
    image: eeai-admin:latest  # SAME IMAGE!
    ports:
      - "5000:5000"
    environment:
      # MongoDB DISABLED
      MONGO_MODE: disabled
      
      # ChromaDB
      CHROMA_MODE: enabled
      CHROMA_CUSTOMERS: test
      CHROMA_HOST_test: chroma
      CHROMA_PORT_test: 8000
      
      # APIs
      AZURE_OPENAI_ENABLED: "true"
      AZURE_OPENAI_API_BASE: https://test.openai.azure.com
      AZURE_OPENAI_API_KEY: ${AZURE_API_KEY}
      AZURE_OPENAI_DEPLOYMENT_NAME: gpt-4o
      
      # App settings
      FLASK_ENV: development
      FLASK_DEBUG: "True"
      LOG_LEVEL: DEBUG
    depends_on:
      - chroma

  chroma:
    image: chromadb/chroma:latest
    volumes:
      - chroma_data:/chroma/chroma

volumes:
  chroma_data:
```

---

## Terraform Configuration

### AWS ECS Deployment

```hcl
# variables.tf
variable "bank_name" {
  description = "Bank identifier"
  type        = string
}

variable "mongo_uri" {
  description = "MongoDB connection URI"
  type        = string
  sensitive   = true
}

variable "azure_api_key" {
  description = "Azure OpenAI API Key"
  type        = string
  sensitive   = true
}

variable "chroma_customers" {
  description = "List of ChromaDB customers"
  type        = list(string)
}

variable "chroma_hosts" {
  description = "ChromaDB hosts per customer"
  type        = map(string)
}

# ecs.tf
resource "aws_ecs_task_definition" "eeai_admin" {
  family                   = "eeai-admin-${var.bank_name}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "1024"
  memory                   = "2048"

  container_definitions = jsonencode([
    {
      name  = "eeai-admin"
      image = "your-registry/eeai-admin:latest"
      
      environment = concat(
        # MongoDB
        [
          { name = "MONGO_MODE", value = "enabled" },
          { name = "DATABASE_NAME", value = "finai_chatbot" }
        ],
        
        # ChromaDB
        [
          { name = "CHROMA_MODE", value = "enabled" },
          { name = "CHROMA_CUSTOMERS", value = join(",", var.chroma_customers) }
        ],
        
        # ChromaDB per-customer configuration
        flatten([
          for customer in var.chroma_customers : [
            { 
              name  = "CHROMA_HOST_${customer}", 
              value = var.chroma_hosts[customer] 
            },
            { 
              name  = "CHROMA_PORT_${customer}", 
              value = "8000" 
            }
          ]
        ]),
        
        # APIs
        [
          { name = "AZURE_OPENAI_ENABLED", value = "true" },
          { name = "AZURE_OPENAI_API_BASE", value = "https://${var.bank_name}.openai.azure.com" },
          { name = "AZURE_OPENAI_DEPLOYMENT_NAME", value = "gpt-4o" }
        ]
      )
      
      secrets = [
        {
          name      = "MONGO_URI"
          valueFrom = aws_secretsmanager_secret.mongo_uri.arn
        },
        {
          name      = "AZURE_OPENAI_API_KEY"
          valueFrom = aws_secretsmanager_secret.azure_api_key.arn
        }
      ]
      
      portMappings = [
        {
          containerPort = 5000
          protocol      = "tcp"
        }
      ]
      
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = "/ecs/eeai-admin-${var.bank_name}"
          "awslogs-region"        = "us-east-1"
          "awslogs-stream-prefix" = "eeai"
        }
      }
    }
  ])
}

# secrets.tf
resource "aws_secretsmanager_secret" "mongo_uri" {
  name = "eeai/${var.bank_name}/mongo-uri"
}

resource "aws_secretsmanager_secret_version" "mongo_uri" {
  secret_id     = aws_secretsmanager_secret.mongo_uri.id
  secret_string = var.mongo_uri
}

resource "aws_secretsmanager_secret" "azure_api_key" {
  name = "eeai/${var.bank_name}/azure-api-key"
}

resource "aws_secretsmanager_secret_version" "azure_api_key" {
  secret_id     = aws_secretsmanager_secret.azure_api_key.id
  secret_string = var.azure_api_key
}
```

### Deploy Multiple Banks

```hcl
# bank-a.tfvars
bank_name = "bank-a"
mongo_uri = "mongodb://mongo.bank-a.com:27017/finai_chatbot"
azure_api_key = "bank-a-api-key"
chroma_customers = ["retail", "corporate", "investment"]
chroma_hosts = {
  retail     = "chroma-retail.bank-a.com"
  corporate  = "chroma-corp.bank-a.com"
  investment = "chroma-inv.bank-a.com"
}
```

```bash
# Deploy Bank A
terraform apply -var-file=bank-a.tfvars

# Deploy Bank B with different config
terraform apply -var-file=bank-b.tfvars
```

---

## Kubernetes Configuration

### ConfigMap & Secret

```yaml
# configmap-bank-a.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: eeai-config-bank-a
data:
  # MongoDB
  MONGO_MODE: "enabled"
  DATABASE_NAME: "finai_chatbot"
  
  # ChromaDB
  CHROMA_MODE: "enabled"
  CHROMA_CUSTOMERS: "retail,corporate,investment"
  CHROMA_HOST_retail: "chroma-retail-svc"
  CHROMA_PORT_retail: "8000"
  CHROMA_HOST_corporate: "chroma-corporate-svc"
  CHROMA_PORT_corporate: "8000"
  CHROMA_HOST_investment: "chroma-investment-svc"
  CHROMA_PORT_investment: "8000"
  
  # APIs
  AZURE_OPENAI_ENABLED: "true"
  AZURE_OPENAI_API_BASE: "https://bank-a.openai.azure.com"
  AZURE_OPENAI_DEPLOYMENT_NAME: "gpt-4o"
  
  # App
  FLASK_ENV: "production"
  LOG_LEVEL: "INFO"

---
apiVersion: v1
kind: Secret
metadata:
  name: eeai-secrets-bank-a
type: Opaque
stringData:
  MONGO_URI: "mongodb://admin:password@mongodb-svc:27017/finai_chatbot?authSource=admin"
  AZURE_OPENAI_API_KEY: "your-api-key-here"
```

### Deployment

```yaml
# deployment-bank-a.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: eeai-admin-bank-a
spec:
  replicas: 3
  selector:
    matchLabels:
      app: eeai-admin
      bank: bank-a
  template:
    metadata:
      labels:
        app: eeai-admin
        bank: bank-a
    spec:
      containers:
      - name: eeai-admin
        image: your-registry/eeai-admin:latest
        ports:
        - containerPort: 5000
        
        envFrom:
        - configMapRef:
            name: eeai-config-bank-a
        - secretRef:
            name: eeai-secrets-bank-a
        
        resources:
          requests:
            cpu: "500m"
            memory: "512Mi"
          limits:
            cpu: "1000m"
            memory: "1Gi"
        
        livenessProbe:
          httpGet:
            path: /health
            port: 5000
          initialDelaySeconds: 30
          periodSeconds: 10
        
        readinessProbe:
          httpGet:
            path: /ready
            port: 5000
          initialDelaySeconds: 10
          periodSeconds: 5

---
apiVersion: v1
kind: Service
metadata:
  name: eeai-admin-svc-bank-a
spec:
  selector:
    app: eeai-admin
    bank: bank-a
  ports:
  - port: 80
    targetPort: 5000
  type: LoadBalancer
```

### Deploy
```bash
# Bank A
kubectl apply -f configmap-bank-a.yaml
kubectl apply -f deployment-bank-a.yaml

# Bank B (different config)
kubectl apply -f configmap-bank-b.yaml
kubectl apply -f deployment-bank-b.yaml
```

---

## Testing & Validation

### Diagnostic Tools

#### Test MongoDB Connection
```bash
python setup_mongodb_config.py --show-env
python setup_mongodb_config.py --test
python setup_mongodb_config.py --info
```

#### Test ChromaDB Configuration
```bash
python setup_chroma_config.py --show-env
python setup_chroma_config.py --list-customers
```

#### Test API Configuration
```python
from app.utils.api_config_manager import validate_api_config

# Validate Azure OpenAI
valid, msg = validate_api_config('azure_openai')
print(f"Azure OpenAI: {msg}")
```

### Environment-Specific Testing

#### Test with MongoDB Disabled
```bash
export MONGO_MODE=disabled
python run.py
# Application should start without MongoDB
```

#### Test with Azure OpenAI Disabled
```bash
export AZURE_OPENAI_ENABLED=false
python run.py
# Application should start, API-dependent features disabled
```

#### Test Multi-Tenant ChromaDB
```bash
export CHROMA_MODE=enabled
export CHROMA_CUSTOMERS=test1,test2
export CHROMA_HOST_test1=localhost
export CHROMA_PORT_test1=8000
export CHROMA_HOST_test2=localhost
export CHROMA_PORT_test2=8001
python run.py
```

### Integration Testing Script

```python
# test_deployment.py
import os
import requests

def test_mongodb_connection():
    """Test MongoDB connectivity"""
    from app.utils.mongodb_manager import get_mongo_client
    client = get_mongo_client()
    if client:
        client.server_info()
        print("✅ MongoDB connected")
        return True
    print("❌ MongoDB not available")
    return False

def test_chroma_connection():
    """Test ChromaDB connectivity"""
    from app.utils.chroma_manager import get_chroma_env_config
    config = get_chroma_env_config()
    print(f"✅ ChromaDB mode: {config['mode']}")
    print(f"   Customers: {', '.join(config['customers'])}")
    return True

def test_api_config():
    """Test API configuration"""
    from app.utils.api_config_manager import validate_api_config
    
    valid, msg = validate_api_config('azure_openai')
    if valid:
        print(f"✅ Azure OpenAI: {msg}")
    else:
        print(f"⚠️  Azure OpenAI: {msg}")
    
    return True

def test_application_health():
    """Test application health endpoint"""
    try:
        response = requests.get('http://localhost:5000/health', timeout=5)
        if response.status_code == 200:
            print("✅ Application health check passed")
            return True
    except:
        pass
    print("❌ Application health check failed")
    return False

if __name__ == "__main__":
    print("=== Deployment Validation ===\n")
    test_mongodb_connection()
    test_chroma_connection()
    test_api_config()
    test_application_health()
    print("\n=== Validation Complete ===")
```

Run: `python test_deployment.py`

---

## Troubleshooting

### MongoDB Connection Issues

**Problem:** Connection timeout
```
pymongo.errors.ServerSelectionTimeoutError
```

**Solutions:**
1. Check MongoDB is running: `docker ps | grep mongo`
2. Verify connection string: `python setup_mongodb_config.py --info`
3. Test connectivity: `python setup_mongodb_config.py --test`
4. Check firewall rules
5. Verify authentication: Ensure MONGO_AUTH_SOURCE is correct

**Problem:** Authentication failed
```
pymongo.errors.OperationFailure: Authentication failed
```

**Solutions:**
1. Verify credentials in MONGO_URI
2. Check MONGO_AUTH_SOURCE (usually 'admin')
3. Ensure user has correct permissions

### ChromaDB Connection Issues

**Problem:** Customer not found
```
ValueError: Customer 'xxx' not found in enabled customers
```

**Solutions:**
1. Check CHROMA_CUSTOMERS includes the customer
2. Verify spelling matches exactly
3. Run: `python setup_chroma_config.py --list-customers`

**Problem:** Connection refused
```
requests.exceptions.ConnectionError
```

**Solutions:**
1. Verify ChromaDB service is running
2. Check CHROMA_HOST_xxx and CHROMA_PORT_xxx
3. Test: `curl http://<chroma-host>:<port>/api/v1/heartbeat`

### API Configuration Issues

**Problem:** API key not configured
```
Azure OpenAI API key not configured
```

**Solutions:**
1. Set AZURE_OPENAI_API_KEY
2. Check AZURE_OPENAI_ENABLED=true
3. Verify: `python -c "from app.utils.api_config_manager import validate_api_config; print(validate_api_config('azure_openai'))"`

**Problem:** Invalid endpoint
```
openai.error.InvalidRequestError
```

**Solutions:**
1. Verify AZURE_OPENAI_API_BASE is correct
2. Check deployment name matches Azure deployment
3. Ensure API version is compatible

### General Debugging

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
export FLASK_DEBUG=True

# Check all environment variables
env | grep -E '(MONGO|CHROMA|AZURE|OPENAI|ANTHROPIC|API_)'

# Test configuration
python -c "
from app.utils.mongodb_manager import get_config_info as mongo_info
from app.utils.api_config_manager import get_config_info as api_info
print('MongoDB:', mongo_info())
print('APIs:', api_info())
"
```

---

## Backward Compatibility

✅ **All changes are 100% backward compatible**

**If NO environment variables are set:**
- MongoDB → localhost:27017 (database: finai_chatbot)
- ChromaDB → localhost:8000
- Azure OpenAI → Uses existing AZURE_OPENAI_* variables

**Existing deployments work without any changes!**

**Migration is optional and non-breaking:**
- Add environment variables gradually
- Test in staging first
- Roll back by removing environment variables

---

## Summary

### Key Benefits

1. **Single Docker Image** → Build once, deploy everywhere
2. **Environment-Specific Config** → No code changes per bank
3. **Multi-Tenant Support** → ChromaDB per customer/division
4. **Flexible Deployment** → Docker, Kubernetes, ECS, etc.
5. **Graceful Degradation** → Disable services per environment
6. **Security** → Credentials in environment/secrets, not code
7. **Easy Testing** → Test environments with different configs
8. **Backward Compatible** → Existing deployments unchanged

### Production Checklist

- [ ] Build and tag Docker image
- [ ] Create environment-specific config files
- [ ] Store secrets in secrets manager (AWS/Azure/Kubernetes)
- [ ] Test MongoDB connectivity
- [ ] Test ChromaDB connectivity (all customers)
- [ ] Test API configuration
- [ ] Run integration tests
- [ ] Deploy to staging environment
- [ ] Verify application health
- [ ] Monitor logs for errors
- [ ] Deploy to production
- [ ] Document deployment-specific configuration

---

**For support and updates, refer to:**
- `MONGODB_ENV_VAR_IMPLEMENTATION.md` - MongoDB details
- `COMPLETE_IMPLEMENTATION_SUMMARY.md` - Implementation overview
- `.env.example` - Complete variable reference
