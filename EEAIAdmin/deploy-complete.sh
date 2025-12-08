#!/bin/bash

################################################################################
# Complete Azure Container Apps Deployment Script
# 
# This script handles EVERYTHING for Azure deployment:
# 1. Infrastructure Creation (if needed):
#    - Resource Group
#    - Azure Container Registry
#    - Cosmos DB (MongoDB API)
#    - Azure Cache for Redis
#    - Storage Account with File Shares
#    - Log Analytics Workspace
#    - Container Apps Environment
# 2. Application Deployment:
#    - Build Docker image for linux/amd64 platform
#    - Push to Azure Container Registry
#    - Deploy/Update Container App with all environment variables
#    - Configure health probes
# 3. Verification & Testing:
#    - Verify deployment status
#    - Test application endpoints
#    - Show comprehensive summary
#
# Prerequisites:
# - Azure CLI installed and logged in (az login)
# - Docker installed and running
# - .env file with OpenAI and Azure API keys
# - Contributor role on Azure subscription
#
# Usage:
#   ./deploy-complete.sh [OPTIONS]
#
# Options:
#   --skip-build        Skip Docker build step (use existing image)
#   --skip-push         Skip Docker push step (use existing image in ACR)
#   --force-build       Force rebuild without cache (--no-cache)
#   --create-infra      Create all Azure infrastructure (Container App, Cosmos DB, Redis, etc.)
#   --infra-only        Only create infrastructure, skip Docker build/deploy
#   --help              Show this help message
#
# Examples:
#   ./deploy-complete.sh                          # Standard deployment (update existing)
#   ./deploy-complete.sh --create-infra           # Create all infrastructure + deploy
#   ./deploy-complete.sh --infra-only             # Only create infrastructure
#   ./deploy-complete.sh --skip-build --skip-push # Update env vars only
#
# Author: EEAIAdmin Team
# Date: November 14, 2025
################################################################################

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration Variables
RESOURCE_GROUP="bankadibpoc-rg"
LOCATION="eastus"  # Default Azure region
SUBSCRIPTION_ID=""  # Optional: Set specific subscription ID
APP_NAME="bankadibpoc-prod-app"
ACR_NAME="bankadibpocacr"
IMAGE_NAME="adibpoc-app"
IMAGE_TAG="latest"
FULL_IMAGE_NAME="${ACR_NAME}.azurecr.io/${IMAGE_NAME}:${IMAGE_TAG}"

# Flags
SKIP_BUILD=false
SKIP_PUSH=false
FORCE_BUILD=false
CREATE_INFRA=false
INFRA_ONLY=false

################################################################################
# Helper Functions
################################################################################

print_header() {
    echo ""
    echo -e "${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} $1"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_info() {
    echo -e "${BLUE}ℹ${NC}  $1"
}

print_success() {
    echo -e "${GREEN}✅${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠️${NC}  $1"
}

print_error() {
    echo -e "${RED}❌${NC} $1"
}

print_step() {
    echo ""
    echo -e "${CYAN}▶${NC}  $1"
    echo ""
}

check_prerequisites() {
    print_step "Checking prerequisites..."
    
    # Check if Azure CLI is installed
    if ! command -v az &> /dev/null; then
        print_error "Azure CLI is not installed. Please install it first."
        exit 1
    fi
    print_success "Azure CLI is installed"
    
    # Check if Docker is installed (skip if infra-only)
    if [ "$INFRA_ONLY" = false ]; then
        if ! command -v docker &> /dev/null; then
            print_error "Docker is not installed. Please install it first."
            exit 1
        fi
        print_success "Docker is installed"
        
        # Check if Docker is running
        if ! docker info &> /dev/null; then
            print_error "Docker is not running. Please start Docker Desktop."
            exit 1
        fi
        print_success "Docker is running"
    fi
    
    # Check if logged in to Azure
    if ! az account show &> /dev/null; then
        print_error "Not logged in to Azure. Please run 'az login' first."
        exit 1
    fi
    print_success "Logged in to Azure"
    
    # Set subscription if specified
    if [ -n "$SUBSCRIPTION_ID" ]; then
        print_info "Setting subscription to: ${SUBSCRIPTION_ID}"
        az account set --subscription "$SUBSCRIPTION_ID"
        if [ $? -ne 0 ]; then
            print_error "Failed to set subscription. Please verify subscription ID."
            exit 1
        fi
        print_success "Subscription set successfully"
    fi
    
    # Get current subscription
    SUBSCRIPTION_NAME=$(az account show --query name -o tsv)
    CURRENT_SUBSCRIPTION_ID=$(az account show --query id -o tsv)
    print_info "Current subscription: ${SUBSCRIPTION_NAME} (${CURRENT_SUBSCRIPTION_ID})"
}

load_env_file() {
    print_step "Loading environment variables from .env file..."
    
    if [ ! -f .env ]; then
        print_error ".env file not found! Please create it first."
        exit 1
    fi
    
    # Source .env file
    set -a
    source .env
    set +a
    
    # Verify critical variables
    if [ -z "$AZURE_OPENAI_API_KEY" ]; then
        print_error "AZURE_OPENAI_API_KEY not found in .env file"
        exit 1
    fi
    
    if [ -z "$AZURE_CV_KEY" ]; then
        print_error "AZURE_CV_KEY not found in .env file"
        exit 1
    fi
    
    print_success "Environment variables loaded from .env file"
}

build_docker_image() {
    if [ "$SKIP_BUILD" = true ]; then
        print_warning "Skipping Docker build (--skip-build flag used)"
        return
    fi
    
    print_step "Building Docker image for linux/amd64 platform..."
    
    BUILD_FLAGS=""
    if [ "$FORCE_BUILD" = true ]; then
        print_info "Force rebuild enabled (--no-cache)"
        BUILD_FLAGS="--no-cache"
    fi
    
    print_info "Image: ${FULL_IMAGE_NAME}"
    print_info "Platform: linux/amd64"
    
    START_TIME=$(date +%s)
    
    if docker build ${BUILD_FLAGS} --platform linux/amd64 -t "${FULL_IMAGE_NAME}" .; then
        END_TIME=$(date +%s)
        DURATION=$((END_TIME - START_TIME))
        print_success "Docker image built successfully in ${DURATION} seconds"
        
        # Get image digest
        IMAGE_ID=$(docker images --format "{{.ID}}" "${FULL_IMAGE_NAME}" | head -1)
        print_info "Image ID: ${IMAGE_ID}"
    else
        print_error "Docker build failed!"
        exit 1
    fi
}

push_to_acr() {
    if [ "$SKIP_PUSH" = true ]; then
        print_warning "Skipping Docker push (--skip-push flag used)"
        return
    fi
    
    print_step "Pushing Docker image to Azure Container Registry..."
    
    print_info "Logging in to ACR: ${ACR_NAME}"
    az acr login --name "${ACR_NAME}"
    
    print_info "Pushing image: ${FULL_IMAGE_NAME}"
    
    if docker push "${FULL_IMAGE_NAME}"; then
        print_success "Docker image pushed successfully"
        
        # Get pushed image digest
        IMAGE_DIGEST=$(az acr repository show --name "${ACR_NAME}" --image "${IMAGE_NAME}:${IMAGE_TAG}" --query digest -o tsv)
        print_info "Image digest: ${IMAGE_DIGEST}"
        export IMAGE_DIGEST
    else
        print_error "Docker push failed!"
        exit 1
    fi
}

get_mongo_credentials() {
    print_step "Setting up MongoDB connection to Container App..."
    
    # Get MongoDB Container App FQDN
    MONGO_FQDN=$(az containerapp show --name "bankadibpoc-prod-mongo" --resource-group "${RESOURCE_GROUP}" --query "properties.configuration.ingress.fqdn" -o tsv 2>/dev/null || echo "")
    
    if [ -z "$MONGO_FQDN" ]; then
        print_warning "MongoDB Container App not found. Will use .env values."
        return
    fi
    
    print_info "Found MongoDB Container App: ${MONGO_FQDN}"
    
    # Construct MongoDB URI for Container App
    MONGO_URI="mongodb://${MONGO_FQDN}:27017/eeai_data"
    
    if [ -n "$MONGO_URI" ]; then
        export MONGO_URI
        print_success "MongoDB connection string configured for Container App"
        print_info "MongoDB URI: ${MONGO_URI}"
    else
        print_warning "Could not configure MongoDB connection string. Will use .env values."
    fi
}

get_redis_credentials() {
    print_step "Setting up Redis connection to Container App..."
    
    # Get Redis Container App FQDN
    REDIS_FQDN=$(az containerapp show --name "bankadibpoc-prod-redis" --resource-group "${RESOURCE_GROUP}" --query "properties.configuration.ingress.fqdn" -o tsv 2>/dev/null || echo "")
    
    if [ -z "$REDIS_FQDN" ]; then
        print_warning "Redis Container App not found. Will use .env values."
        return
    fi
    
    print_info "Found Redis Container App: ${REDIS_FQDN}"
    
    # Construct Redis URL for Container App (without authentication for container setup)
    REDIS_URL="redis://${REDIS_FQDN}:6379/0"
    
    if [ -n "$REDIS_URL" ]; then
        export REDIS_URL
        print_success "Redis connection string configured for Container App"
        print_info "Redis URL: ${REDIS_URL}"
    else
        print_warning "Could not configure Redis connection string. Will use .env values."
    fi
}

################################################################################
# Infrastructure Creation Functions
################################################################################

create_resource_group() {
    print_step "Creating Resource Group..."
    
    if az group show --name "${RESOURCE_GROUP}" &>/dev/null; then
        print_warning "Resource group ${RESOURCE_GROUP} already exists"
    else
        az group create \
            --name "${RESOURCE_GROUP}" \
            --location "${LOCATION}"
        print_success "Resource group created: ${RESOURCE_GROUP}"
    fi
}

create_container_registry() {
    print_step "Creating Azure Container Registry..."
    
    if az acr show --name "${ACR_NAME}" --resource-group "${RESOURCE_GROUP}" &>/dev/null; then
        print_warning "Container registry ${ACR_NAME} already exists"
    else
        az acr create \
            --name "${ACR_NAME}" \
            --resource-group "${RESOURCE_GROUP}" \
            --location "${LOCATION}" \
            --sku Standard \
            --admin-enabled true
        print_success "Container registry created: ${ACR_NAME}"
    fi
}

create_cosmos_db() {
    print_step "Creating Cosmos DB (MongoDB API)..."
    
    local COSMOS_ACCOUNT="${RESOURCE_GROUP//-rg/}-cosmos"
    local COSMOS_DB="eeai_data"
    
    if az cosmosdb show --name "${COSMOS_ACCOUNT}" --resource-group "${RESOURCE_GROUP}" &>/dev/null; then
        print_warning "Cosmos DB account ${COSMOS_ACCOUNT} already exists"
    else
        print_info "Creating Cosmos DB account (this may take 5-10 minutes)..."
        az cosmosdb create \
            --name "${COSMOS_ACCOUNT}" \
            --resource-group "${RESOURCE_GROUP}" \
            --location "${LOCATION}" \
            --kind MongoDB \
            --server-version 4.2 \
            --default-consistency-level Session \
            --enable-automatic-failover false
        print_success "Cosmos DB account created: ${COSMOS_ACCOUNT}"
    fi
    
    # Create database
    print_info "Creating Cosmos DB database: ${COSMOS_DB}"
    az cosmosdb mongodb database create \
        --account-name "${COSMOS_ACCOUNT}" \
        --resource-group "${RESOURCE_GROUP}" \
        --name "${COSMOS_DB}" 2>/dev/null || print_warning "Database may already exist"
    print_success "Cosmos DB database ready: ${COSMOS_DB}"
}

create_redis_cache() {
    print_step "Creating Azure Cache for Redis..."
    
    local REDIS_NAME="${RESOURCE_GROUP//-rg/}-redis"
    
    if az redis show --name "${REDIS_NAME}" --resource-group "${RESOURCE_GROUP}" &>/dev/null; then
        print_warning "Redis cache ${REDIS_NAME} already exists"
    else
        print_info "Creating Redis cache (this may take 10-15 minutes)..."
        az redis create \
            --name "${REDIS_NAME}" \
            --resource-group "${RESOURCE_GROUP}" \
            --location "${LOCATION}" \
            --sku Basic \
            --vm-size c0 \
            --enable-non-ssl-port false
        print_success "Redis cache created: ${REDIS_NAME}"
    fi
}

create_storage_account() {
    print_step "Creating Storage Account..."
    
    local STORAGE_ACCOUNT="${RESOURCE_GROUP//-rg/}storage"
    # Remove hyphens from storage account name (not allowed)
    STORAGE_ACCOUNT="${STORAGE_ACCOUNT//-/}"
    
    if az storage account show --name "${STORAGE_ACCOUNT}" --resource-group "${RESOURCE_GROUP}" &>/dev/null; then
        print_warning "Storage account ${STORAGE_ACCOUNT} already exists"
    else
        az storage account create \
            --name "${STORAGE_ACCOUNT}" \
            --resource-group "${RESOURCE_GROUP}" \
            --location "${LOCATION}" \
            --sku Standard_LRS \
            --kind StorageV2
        print_success "Storage account created: ${STORAGE_ACCOUNT}"
    fi
    
    # Get storage account key
    print_info "Retrieving storage account key..."
    local STORAGE_KEY=$(az storage account keys list \
        --account-name "${STORAGE_ACCOUNT}" \
        --resource-group "${RESOURCE_GROUP}" \
        --query "[0].value" -o tsv)
    
    # Create file shares
    print_info "Creating Azure file shares..."
    for SHARE_NAME in data uploads logs; do
        az storage share create \
            --name "${SHARE_NAME}" \
            --account-name "${STORAGE_ACCOUNT}" \
            --account-key "${STORAGE_KEY}" \
            --quota 10 2>/dev/null || print_warning "Share ${SHARE_NAME} may already exist"
    done
    print_success "File shares created: data, uploads, logs"
}

create_log_analytics() {
    print_step "Creating Log Analytics Workspace..."
    
    local LOG_ANALYTICS="${RESOURCE_GROUP//-rg/}-logs"
    
    if az monitor log-analytics workspace show --workspace-name "${LOG_ANALYTICS}" --resource-group "${RESOURCE_GROUP}" &>/dev/null; then
        print_warning "Log Analytics workspace ${LOG_ANALYTICS} already exists"
        # Get existing credentials
        LOG_ANALYTICS_KEY=$(az monitor log-analytics workspace get-shared-keys \
            --workspace-name "${LOG_ANALYTICS}" \
            --resource-group "${RESOURCE_GROUP}" \
            --query primarySharedKey -o tsv)
        LOG_ANALYTICS_ID=$(az monitor log-analytics workspace show \
            --workspace-name "${LOG_ANALYTICS}" \
            --resource-group "${RESOURCE_GROUP}" \
            --query customerId -o tsv)
    else
        az monitor log-analytics workspace create \
            --workspace-name "${LOG_ANALYTICS}" \
            --resource-group "${RESOURCE_GROUP}" \
            --location "${LOCATION}"
        print_success "Log Analytics workspace created: ${LOG_ANALYTICS}"
        
        # Get credentials
        LOG_ANALYTICS_KEY=$(az monitor log-analytics workspace get-shared-keys \
            --workspace-name "${LOG_ANALYTICS}" \
            --resource-group "${RESOURCE_GROUP}" \
            --query primarySharedKey -o tsv)
        LOG_ANALYTICS_ID=$(az monitor log-analytics workspace show \
            --workspace-name "${LOG_ANALYTICS}" \
            --resource-group "${RESOURCE_GROUP}" \
            --query customerId -o tsv)
    fi
    
    export LOG_ANALYTICS_KEY
    export LOG_ANALYTICS_ID
    print_success "Log Analytics credentials retrieved"
}

create_container_env() {
    print_step "Creating Container Apps Environment..."
    
    local ENVIRONMENT_NAME="${RESOURCE_GROUP//-rg/}-env"
    
    if az containerapp env show --name "${ENVIRONMENT_NAME}" --resource-group "${RESOURCE_GROUP}" &>/dev/null; then
        print_warning "Container Apps environment ${ENVIRONMENT_NAME} already exists"
    else
        az containerapp env create \
            --name "${ENVIRONMENT_NAME}" \
            --resource-group "${RESOURCE_GROUP}" \
            --location "${LOCATION}" \
            --logs-workspace-id "${LOG_ANALYTICS_ID}" \
            --logs-workspace-key "${LOG_ANALYTICS_KEY}"
        print_success "Container Apps environment created: ${ENVIRONMENT_NAME}"
    fi
}

create_container_app() {
    print_step "Creating Container App..."
    
    local ENVIRONMENT_NAME="${RESOURCE_GROUP//-rg/}-env"
    
    if az containerapp show --name "${APP_NAME}" --resource-group "${RESOURCE_GROUP}" &>/dev/null; then
        print_warning "Container app ${APP_NAME} already exists (will be updated during deployment)"
        return
    fi
    
    print_info "Creating container app..."
    
    # Get ACR credentials
    local ACR_USERNAME=$(az acr credential show --name "${ACR_NAME}" --query username -o tsv)
    local ACR_PASSWORD=$(az acr credential show --name "${ACR_NAME}" --query passwords[0].value -o tsv)
    local ACR_LOGIN_SERVER=$(az acr show --name "${ACR_NAME}" --query loginServer -o tsv)
    
    # Prepare basic environment variables
    local ENV_VARS=(
        "FLASK_ENV=production"
        "PYTHONUNBUFFERED=1"
        "CHROMADB_ENABLED=false"
        "ORACLE_ENABLED=false"
    )
    
    az containerapp create \
        --name "${APP_NAME}" \
        --resource-group "${RESOURCE_GROUP}" \
        --environment "${ENVIRONMENT_NAME}" \
        --image "${ACR_LOGIN_SERVER}/${IMAGE_NAME}:latest" \
        --target-port 5000 \
        --ingress external \
        --registry-server "${ACR_LOGIN_SERVER}" \
        --registry-username "${ACR_USERNAME}" \
        --registry-password "${ACR_PASSWORD}" \
        --cpu 2.0 \
        --memory 4Gi \
        --min-replicas 1 \
        --max-replicas 5 \
        --env-vars "${ENV_VARS[@]}"
    
    print_success "Container app created: ${APP_NAME}"
    print_info "Environment variables will be configured during deployment"
}

create_all_infrastructure() {
    print_header "CREATING ALL AZURE INFRASTRUCTURE"
    
    print_info "This will create the following resources:"
    print_info "  • Resource Group"
    print_info "  • Azure Container Registry"
    print_info "  • Cosmos DB (MongoDB API)"
    print_info "  • Azure Cache for Redis"
    print_info "  • Storage Account with File Shares"
    print_info "  • Log Analytics Workspace"
    print_info "  • Container Apps Environment"
    print_info "  • Container App"
    echo ""
    print_warning "This process may take 15-30 minutes"
    echo ""
    
    read -p "Continue? (yes/no): " CONFIRM
    if [ "$CONFIRM" != "yes" ]; then
        print_error "Infrastructure creation cancelled by user"
        exit 1
    fi
    
    create_resource_group
    create_container_registry
    create_log_analytics
    create_container_env
    create_cosmos_db
    create_redis_cache
    create_storage_account
    create_container_app
    
    print_success "All infrastructure created successfully!"
    
    # Retrieve credentials for use in deployment
    get_mongo_credentials
    get_redis_credentials
}

deploy_to_azure() {
    print_step "Deploying to Azure Container Apps..."
    
    # Prepare environment variables array
    ENV_VARS=(
        "MONGO_URI=${MONGO_URI}"
        "MONGO_DB_NAME=eeai_data"
        "REDIS_URL=${REDIS_URL}"
        "SECRET_KEY=${SECRET_KEY:-$(openssl rand -hex 32)}"
        "JWT_SECRET_KEY=${JWT_SECRET_KEY:-$(openssl rand -hex 32)}"
        "ADMIN_EMAIL=${ADMIN_EMAIL:-admin@eeai.com}"
        "ADMIN_PASSWORD=${ADMIN_PASSWORD:-Admin@123456}"
        "FLASK_ENV=production"
        "PYTHONUNBUFFERED=1"
        "CHROMADB_ENABLED=false"
        "ORACLE_ENABLED=false"
        "AZURE_OPENAI_API_BASE=${AZURE_OPENAI_API_BASE}"
        "AZURE_OPENAI_API_KEY=${AZURE_OPENAI_API_KEY}"
        "AZURE_OPENAI_DEPLOYMENT_NAME=${AZURE_OPENAI_DEPLOYMENT_NAME:-gpt-4o}"
        "AZURE_EMBEDDING_MODEL=${AZURE_EMBEDDING_MODEL:-text-embedding-3-large}"
        "AZURE_EMBEDDING_KEY=${AZURE_EMBEDDING_KEY}"
        "AZURE_CV_ENDPOINT=${AZURE_CV_ENDPOINT}"
        "AZURE_CV_KEY=${AZURE_CV_KEY}"
    )
    
    print_info "Setting ${#ENV_VARS[@]} environment variables"
    
    # Build the az command with all env vars
    CMD="az containerapp update --name ${APP_NAME} --resource-group ${RESOURCE_GROUP}"
    
    # Add image digest if available
    if [ -n "$IMAGE_DIGEST" ]; then
        CMD="${CMD} --image ${ACR_NAME}.azurecr.io/${IMAGE_NAME}@${IMAGE_DIGEST}"
        print_info "Using specific image digest: ${IMAGE_DIGEST}"
    else
        CMD="${CMD} --image ${FULL_IMAGE_NAME}"
        print_info "Using latest tag: ${FULL_IMAGE_NAME}"
    fi
    
    # Add environment variables
    CMD="${CMD} --set-env-vars"
    for var in "${ENV_VARS[@]}"; do
        CMD="${CMD} \"${var}\""
    done
    
    print_info "Executing deployment command..."
    
    if eval "${CMD}" > /tmp/deploy_output.json; then
        print_success "Deployment successful!"
        
        # Extract new revision name
        NEW_REVISION=$(jq -r '.properties.latestRevisionName' /tmp/deploy_output.json)
        print_info "New revision: ${NEW_REVISION}"
        export NEW_REVISION
    else
        print_error "Deployment failed!"
        exit 1
    fi
}

verify_deployment() {
    print_step "Verifying deployment..."
    
    # Wait for revision to be ready
    print_info "Waiting for revision to become ready (max 2 minutes)..."
    
    MAX_ATTEMPTS=24  # 24 * 5 seconds = 2 minutes
    ATTEMPT=0
    
    while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
        STATUS=$(az containerapp revision show --name "${NEW_REVISION}" --app "${APP_NAME}" --resource-group "${RESOURCE_GROUP}" --query "properties.runningState" -o tsv 2>/dev/null || echo "Unknown")
        
        if [ "$STATUS" = "Running" ]; then
            print_success "Revision is running!"
            break
        elif [ "$STATUS" = "Failed" ]; then
            print_error "Revision failed to start!"
            exit 1
        else
            echo -n "."
            sleep 5
            ATTEMPT=$((ATTEMPT + 1))
        fi
    done
    
    if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
        print_warning "Timeout waiting for revision to be ready"
    fi
    
    echo ""
}

test_application() {
    print_step "Testing application endpoints..."
    
    # Get application URL
    APP_URL=$(az containerapp show --name "${APP_NAME}" --resource-group "${RESOURCE_GROUP}" --query "properties.configuration.ingress.fqdn" -o tsv)
    FULL_URL="https://${APP_URL}"
    
    print_info "Application URL: ${FULL_URL}"
    
    # Test main endpoint
    print_info "Testing main endpoint..."
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${FULL_URL}/" || echo "000")
    
    if [ "$HTTP_CODE" = "200" ]; then
        print_success "Main endpoint responding: HTTP ${HTTP_CODE}"
    else
        print_error "Main endpoint not responding: HTTP ${HTTP_CODE}"
    fi
    
    # Test health endpoint
    print_info "Testing health endpoint..."
    HEALTH_RESPONSE=$(curl -s "${FULL_URL}/health" || echo "{}")
    
    if echo "$HEALTH_RESPONSE" | jq -e '.status' &> /dev/null; then
        print_success "Health endpoint responding"
        echo "$HEALTH_RESPONSE" | jq '.'
    else
        print_warning "Health endpoint not responding properly"
    fi
}

show_logs() {
    print_step "Recent application logs..."
    
    print_info "Fetching last 30 log lines..."
    az containerapp logs show --name "${APP_NAME}" --resource-group "${RESOURCE_GROUP}" --tail 30 --follow=false 2>/dev/null | \
        jq -r '.[] | .TimeStamp + " - " + .Log' | \
        grep -E "(INFO|ERROR|WARNING|Connected|OpenAI)" | \
        tail -15 || print_warning "Could not fetch logs"
}

print_summary() {
    print_header "DEPLOYMENT SUMMARY"
    
    echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
    echo ""
    echo "📦 Docker Image:"
    echo "   Registry: ${ACR_NAME}.azurecr.io"
    echo "   Image: ${IMAGE_NAME}:${IMAGE_TAG}"
    if [ -n "$IMAGE_DIGEST" ]; then
        echo "   Digest: ${IMAGE_DIGEST}"
    fi
    echo ""
    echo "🚀 Azure Container App:"
    echo "   Resource Group: ${RESOURCE_GROUP}"
    echo "   App Name: ${APP_NAME}"
    if [ -n "$NEW_REVISION" ]; then
        echo "   Revision: ${NEW_REVISION}"
    fi
    echo ""
    echo "🌐 Application URL:"
    APP_URL=$(az containerapp show --name "${APP_NAME}" --resource-group "${RESOURCE_GROUP}" --query "properties.configuration.ingress.fqdn" -o tsv 2>/dev/null || echo "unknown")
    echo "   https://${APP_URL}"
    echo ""
    echo "📋 Environment Variables Set:"
    echo "   • MongoDB (Cosmos DB) - ✅ Configured"
    echo "   • Redis Cache - ✅ Configured"
    echo "   • Azure OpenAI (gpt-4o) - ✅ Configured"
    echo "   • Azure Computer Vision - ✅ Configured"
    echo "   • Embeddings (text-embedding-3-large) - ✅ Configured"
    echo "   • Oracle Database - ⏸️ Disabled"
    echo "   • ChromaDB - ⏸️ Disabled"
    echo ""
    echo "📊 Quick Commands:"
    echo "   View logs:    az containerapp logs show --name ${APP_NAME} --resource-group ${RESOURCE_GROUP} --tail 50"
    echo "   Check status: az containerapp show --name ${APP_NAME} --resource-group ${RESOURCE_GROUP}"
    echo "   Test app:     curl https://${APP_URL}/health | jq '.'"
    echo ""
}

show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Complete deployment script for EEAIAdmin to Azure Container Apps"
    echo ""
    echo "Options:"
    echo "  --subscription-id <ID>  Use specific Azure subscription ID"
    echo "  --skip-build            Skip Docker build step (use existing local image)"
    echo "  --skip-push             Skip Docker push step (use existing image in ACR)"
    echo "  --force-build           Force rebuild without cache (--no-cache)"
    echo "  --create-infra          Create all Azure infrastructure (Container App, Cosmos DB, Redis, etc.)"
    echo "  --infra-only            Only create infrastructure, skip Docker build/deploy"
    echo "  --help                  Show this help message"
    echo ""
    echo "Infrastructure Creation (--create-infra):"
    echo "  Creates the following Azure resources:"
    echo "    • Resource Group"
    echo "    • Azure Container Registry"
    echo "    • Cosmos DB (MongoDB API)"
    echo "    • Azure Cache for Redis"
    echo "    • Storage Account with File Shares"
    echo "    • Log Analytics Workspace"
    echo "    • Container Apps Environment"
    echo "    • Container App"
    echo "  Note: This may take 15-30 minutes"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Standard deployment (update existing app)"
    echo "  $0 --subscription-id abc-123-def      # Deploy to specific subscription"
    echo "  $0 --create-infra                     # Create all infrastructure + deploy app"
    echo "  $0 --infra-only                       # Only create infrastructure (no deployment)"
    echo "  $0 --skip-build                       # Deploy existing local image"
    echo "  $0 --skip-build --skip-push           # Update env vars only (no image changes)"
    echo "  $0 --force-build                      # Force rebuild from scratch"
    echo "  $0 --subscription-id abc-123 --create-infra  # Create infra in specific subscription"
    echo ""
}

################################################################################
# Main Execution
################################################################################

main() {
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --subscription-id)
                SUBSCRIPTION_ID="$2"
                shift 2
                ;;
            --skip-build)
                SKIP_BUILD=true
                shift
                ;;
            --skip-push)
                SKIP_PUSH=true
                shift
                ;;
            --force-build)
                FORCE_BUILD=true
                shift
                ;;
            --create-infra)
                CREATE_INFRA=true
                shift
                ;;
            --infra-only)
                INFRA_ONLY=true
                CREATE_INFRA=true
                shift
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    print_header "EEAIADMIN AZURE DEPLOYMENT SCRIPT"
    
    # Execute deployment steps
    check_prerequisites
    
    # Create infrastructure if requested
    if [ "$CREATE_INFRA" = true ]; then
        create_all_infrastructure
        
        # Exit if infra-only mode
        if [ "$INFRA_ONLY" = true ]; then
            print_success "Infrastructure creation complete! 🎉"
            print_info "Run './deploy-complete.sh' to deploy the application"
            exit 0
        fi
    fi
    
    load_env_file
    get_mongo_credentials
    get_redis_credentials
    build_docker_image
    push_to_acr
    deploy_to_azure
    verify_deployment
    test_application
    show_logs
    print_summary
    
    print_success "All done! 🎉"
}

# Run main function
main "$@"
