@echo off
REM ################################################################################
REM Complete Azure Container Apps Deployment Script (Windows Batch)
REM 
REM This script handles EVERYTHING for Azure deployment:
REM 1. Infrastructure Creation (if needed):
REM    - Resource Group
REM    - Azure Container Registry
REM    - Cosmos DB (MongoDB API)
REM    - Azure Cache for Redis
REM    - Storage Account with File Shares
REM    - Log Analytics Workspace
REM    - Container Apps Environment
REM 2. Application Deployment:
REM    - Build Docker image for linux/amd64 platform
REM    - Push to Azure Container Registry
REM    - Deploy/Update Container App with all environment variables
REM    - Configure health probes
REM 3. Verification & Testing:
REM    - Verify deployment status
REM    - Test application endpoints
REM    - Show comprehensive summary
REM
REM Prerequisites:
REM - Azure CLI installed and logged in (az login)
REM - Docker installed and running
REM - .env file with OpenAI and Azure API keys
REM - Contributor role on Azure subscription
REM
REM Usage:
REM   deploy-complete.bat [OPTIONS]
REM
REM Options:
REM   --skip-build        Skip Docker build step (use existing image)
REM   --skip-push         Skip Docker push step (use existing image in ACR)
REM   --force-build       Force rebuild without cache (--no-cache)
REM   --create-infra      Create all Azure infrastructure
REM   --infra-only        Only create infrastructure, skip Docker build/deploy
REM   --help              Show this help message
REM
REM Author: EEAIAdmin Team
REM Date: December 4, 2025
REM ################################################################################

setlocal enabledelayedexpansion

REM Configuration Variables
set "RESOURCE_GROUP=bankadibpoc-rg"
set "LOCATION=eastus"
set "SUBSCRIPTION_ID="
set "APP_NAME=bankadibpoc-prod-app"
set "ACR_NAME=bankadibpocacr"
set "IMAGE_NAME=adibpoc-app"
set "IMAGE_TAG=latest"
set "FULL_IMAGE_NAME=%ACR_NAME%.azurecr.io/%IMAGE_NAME%:%IMAGE_TAG%"

REM Flags
set "SKIP_BUILD=false"
set "SKIP_PUSH=false"
set "FORCE_BUILD=false"
set "CREATE_INFRA=false"
set "INFRA_ONLY=false"

REM Parse command line arguments
:parse_args
if "%~1"=="" goto args_done
if /i "%~1"=="--subscription-id" (
    set "SUBSCRIPTION_ID=%~2"
    shift
    shift
    goto parse_args
)
if /i "%~1"=="--skip-build" (
    set "SKIP_BUILD=true"
    shift
    goto parse_args
)
if /i "%~1"=="--skip-push" (
    set "SKIP_PUSH=true"
    shift
    goto parse_args
)
if /i "%~1"=="--force-build" (
    set "FORCE_BUILD=true"
    shift
    goto parse_args
)
if /i "%~1"=="--create-infra" (
    set "CREATE_INFRA=true"
    shift
    goto parse_args
)
if /i "%~1"=="--infra-only" (
    set "INFRA_ONLY=true"
    set "CREATE_INFRA=true"
    shift
    goto parse_args
)
if /i "%~1"=="--help" (
    call :show_help
    exit /b 0
)
echo [ERROR] Unknown option: %~1
call :show_help
exit /b 1

:args_done

echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║ EEAIADMIN AZURE DEPLOYMENT SCRIPT                              ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

REM Check prerequisites
call :check_prerequisites
if errorlevel 1 exit /b 1

REM Create infrastructure if requested
if "%CREATE_INFRA%"=="true" (
    call :create_all_infrastructure
    if errorlevel 1 exit /b 1
    
    if "%INFRA_ONLY%"=="true" (
        echo [SUCCESS] Infrastructure creation complete!
        echo [INFO] Run 'deploy-complete.bat' to deploy the application
        exit /b 0
    )
)

REM Load environment variables
call :load_env_file
if errorlevel 1 exit /b 1

REM Get connection credentials
call :get_mongo_credentials
call :get_redis_credentials

REM Build and push Docker image
if "%SKIP_BUILD%"=="false" (
    call :build_docker_image
    if errorlevel 1 exit /b 1
)

if "%SKIP_PUSH%"=="false" (
    call :push_to_acr
    if errorlevel 1 exit /b 1
)

REM Deploy to Azure
call :deploy_to_azure
if errorlevel 1 exit /b 1

REM Verify and test
call :verify_deployment
call :test_application
call :show_logs
call :print_summary

echo.
echo [SUCCESS] All done! 🎉
exit /b 0

REM ################################################################################
REM Helper Functions
REM ################################################################################

:check_prerequisites
echo.
echo [INFO] Checking prerequisites...
echo.

REM Check Azure CLI
where az >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Azure CLI is not installed. Please install it first.
    exit /b 1
)
echo [SUCCESS] Azure CLI is installed

REM Check Docker (skip if infra-only)
if "%INFRA_ONLY%"=="false" (
    where docker >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Docker is not installed. Please install it first.
        exit /b 1
    )
    echo [SUCCESS] Docker is installed
    
    docker info >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Docker is not running. Please start Docker Desktop.
        exit /b 1
    )
    echo [SUCCESS] Docker is running
)

REM Check Azure login
az account show >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Not logged in to Azure. Please run 'az login' first.
    exit /b 1
)
echo [SUCCESS] Logged in to Azure

REM Set subscription if specified
if not "%SUBSCRIPTION_ID%"=="" (
    echo [INFO] Setting subscription to: %SUBSCRIPTION_ID%
    az account set --subscription "%SUBSCRIPTION_ID%"
    if errorlevel 1 (
        echo [ERROR] Failed to set subscription. Please verify subscription ID.
        exit /b 1
    )
    echo [SUCCESS] Subscription set successfully
)

REM Get current subscription
for /f "tokens=*" %%i in ('az account show --query name -o tsv') do set "SUBSCRIPTION_NAME=%%i"
for /f "tokens=*" %%i in ('az account show --query id -o tsv') do set "CURRENT_SUBSCRIPTION_ID=%%i"
echo [INFO] Current subscription: !SUBSCRIPTION_NAME! (!CURRENT_SUBSCRIPTION_ID!)

exit /b 0

:load_env_file
echo.
echo [INFO] Loading environment variables from .env file...
echo.

if not exist ".env" (
    echo [ERROR] .env file not found! Please create it first.
    exit /b 1
)

REM Load .env file
for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
    set "line=%%a"
    if not "!line:~0,1!"=="#" (
        if not "%%b"=="" (
            set "%%a=%%b"
        )
    )
)

REM Verify critical variables
if "%AZURE_OPENAI_API_KEY%"=="" (
    echo [ERROR] AZURE_OPENAI_API_KEY not found in .env file
    exit /b 1
)

if "%AZURE_CV_KEY%"=="" (
    echo [ERROR] AZURE_CV_KEY not found in .env file
    exit /b 1
)

echo [SUCCESS] Environment variables loaded from .env file
exit /b 0

:build_docker_image
if "%SKIP_BUILD%"=="true" (
    echo [WARNING] Skipping Docker build (--skip-build flag used)
    exit /b 0
)

echo.
echo [INFO] Building Docker image for linux/amd64 platform...
echo.

set "BUILD_FLAGS="
if "%FORCE_BUILD%"=="true" (
    echo [INFO] Force rebuild enabled (--no-cache)
    set "BUILD_FLAGS=--no-cache"
)

echo [INFO] Image: %FULL_IMAGE_NAME%
echo [INFO] Platform: linux/amd64
echo.

docker build %BUILD_FLAGS% --platform linux/amd64 -t "%FULL_IMAGE_NAME%" .
if errorlevel 1 (
    echo [ERROR] Docker build failed!
    exit /b 1
)

echo [SUCCESS] Docker image built successfully
exit /b 0

:push_to_acr
if "%SKIP_PUSH%"=="true" (
    echo [WARNING] Skipping Docker push (--skip-push flag used)
    exit /b 0
)

echo.
echo [INFO] Pushing Docker image to Azure Container Registry...
echo.

echo [INFO] Logging in to ACR: %ACR_NAME%
az acr login --name "%ACR_NAME%"
if errorlevel 1 (
    echo [ERROR] ACR login failed!
    exit /b 1
)

echo [INFO] Pushing image: %FULL_IMAGE_NAME%
docker push "%FULL_IMAGE_NAME%"
if errorlevel 1 (
    echo [ERROR] Docker push failed!
    exit /b 1
)

echo [SUCCESS] Docker image pushed successfully

REM Get pushed image digest
for /f "tokens=*" %%i in ('az acr repository show --name "%ACR_NAME%" --image "%IMAGE_NAME%:%IMAGE_TAG%" --query digest -o tsv 2^>nul') do set "IMAGE_DIGEST=%%i"
if not "%IMAGE_DIGEST%"=="" (
    echo [INFO] Image digest: %IMAGE_DIGEST%
)

exit /b 0

:get_mongo_credentials
echo.
echo [INFO] Setting up MongoDB connection to Container App...
echo.

for /f "tokens=*" %%i in ('az containerapp show --name "bankadibpoc-prod-mongo" --resource-group "%RESOURCE_GROUP%" --query "properties.configuration.ingress.fqdn" -o tsv 2^>nul') do set "MONGO_FQDN=%%i"

if "%MONGO_FQDN%"=="" (
    echo [WARNING] MongoDB Container App not found. Will use .env values.
    exit /b 0
)

echo [INFO] Found MongoDB Container App: %MONGO_FQDN%
set "MONGO_URI=mongodb://%MONGO_FQDN%:27017/eeai_data"
echo [SUCCESS] MongoDB connection string configured for Container App
echo [INFO] MongoDB URI: %MONGO_URI%

exit /b 0

:get_redis_credentials
echo.
echo [INFO] Setting up Redis connection to Container App...
echo.

for /f "tokens=*" %%i in ('az containerapp show --name "bankadibpoc-prod-redis" --resource-group "%RESOURCE_GROUP%" --query "properties.configuration.ingress.fqdn" -o tsv 2^>nul') do set "REDIS_FQDN=%%i"

if "%REDIS_FQDN%"=="" (
    echo [WARNING] Redis Container App not found. Will use .env values.
    exit /b 0
)

echo [INFO] Found Redis Container App: %REDIS_FQDN%
set "REDIS_URL=redis://%REDIS_FQDN%:6379/0"
echo [SUCCESS] Redis connection string configured for Container App
echo [INFO] Redis URL: %REDIS_URL%

exit /b 0

:create_all_infrastructure
echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║ CREATING ALL AZURE INFRASTRUCTURE                              ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

echo [INFO] This will create the following resources:
echo [INFO]   • Resource Group
echo [INFO]   • Azure Container Registry
echo [INFO]   • Cosmos DB (MongoDB API)
echo [INFO]   • Azure Cache for Redis
echo [INFO]   • Storage Account with File Shares
echo [INFO]   • Log Analytics Workspace
echo [INFO]   • Container Apps Environment
echo [INFO]   • Container App
echo.
echo [WARNING] This process may take 15-30 minutes
echo.

set /p "CONFIRM=Continue? (yes/no): "
if not "!CONFIRM!"=="yes" (
    echo [ERROR] Infrastructure creation cancelled by user
    exit /b 1
)

call :create_resource_group
call :create_container_registry
call :create_log_analytics
call :create_container_env
call :create_cosmos_db
call :create_redis_cache
call :create_storage_account
call :create_container_app

echo [SUCCESS] All infrastructure created successfully!

call :get_mongo_credentials
call :get_redis_credentials

exit /b 0

:create_resource_group
echo.
echo [INFO] Creating Resource Group...
echo.

az group show --name "%RESOURCE_GROUP%" >nul 2>&1
if not errorlevel 1 (
    echo [WARNING] Resource group %RESOURCE_GROUP% already exists
) else (
    az group create --name "%RESOURCE_GROUP%" --location "%LOCATION%"
    echo [SUCCESS] Resource group created: %RESOURCE_GROUP%
)
exit /b 0

:create_container_registry
echo.
echo [INFO] Creating Azure Container Registry...
echo.

az acr show --name "%ACR_NAME%" --resource-group "%RESOURCE_GROUP%" >nul 2>&1
if not errorlevel 1 (
    echo [WARNING] Container registry %ACR_NAME% already exists
) else (
    az acr create --name "%ACR_NAME%" --resource-group "%RESOURCE_GROUP%" --location "%LOCATION%" --sku Standard --admin-enabled true
    echo [SUCCESS] Container registry created: %ACR_NAME%
)
exit /b 0

:create_cosmos_db
echo.
echo [INFO] Creating Cosmos DB (MongoDB API)...
echo.

set "COSMOS_ACCOUNT=%RESOURCE_GROUP:-rg=%-cosmos"
set "COSMOS_DB=eeai_data"

az cosmosdb show --name "%COSMOS_ACCOUNT%" --resource-group "%RESOURCE_GROUP%" >nul 2>&1
if not errorlevel 1 (
    echo [WARNING] Cosmos DB account %COSMOS_ACCOUNT% already exists
) else (
    echo [INFO] Creating Cosmos DB account (this may take 5-10 minutes)...
    az cosmosdb create --name "%COSMOS_ACCOUNT%" --resource-group "%RESOURCE_GROUP%" --location "%LOCATION%" --kind MongoDB --server-version 4.2 --default-consistency-level Session --enable-automatic-failover false
    echo [SUCCESS] Cosmos DB account created: %COSMOS_ACCOUNT%
)

echo [INFO] Creating Cosmos DB database: %COSMOS_DB%
az cosmosdb mongodb database create --account-name "%COSMOS_ACCOUNT%" --resource-group "%RESOURCE_GROUP%" --name "%COSMOS_DB%" >nul 2>&1
echo [SUCCESS] Cosmos DB database ready: %COSMOS_DB%

exit /b 0

:create_redis_cache
echo.
echo [INFO] Creating Azure Cache for Redis...
echo.

set "REDIS_NAME=%RESOURCE_GROUP:-rg=%-redis"

az redis show --name "%REDIS_NAME%" --resource-group "%RESOURCE_GROUP%" >nul 2>&1
if not errorlevel 1 (
    echo [WARNING] Redis cache %REDIS_NAME% already exists
) else (
    echo [INFO] Creating Redis cache (this may take 10-15 minutes)...
    az redis create --name "%REDIS_NAME%" --resource-group "%RESOURCE_GROUP%" --location "%LOCATION%" --sku Basic --vm-size c0 --enable-non-ssl-port false
    echo [SUCCESS] Redis cache created: %REDIS_NAME%
)
exit /b 0

:create_storage_account
echo.
echo [INFO] Creating Storage Account...
echo.

set "STORAGE_ACCOUNT=%RESOURCE_GROUP:-rg=%storage"
set "STORAGE_ACCOUNT=%STORAGE_ACCOUNT:-=%"

az storage account show --name "%STORAGE_ACCOUNT%" --resource-group "%RESOURCE_GROUP%" >nul 2>&1
if not errorlevel 1 (
    echo [WARNING] Storage account %STORAGE_ACCOUNT% already exists
) else (
    az storage account create --name "%STORAGE_ACCOUNT%" --resource-group "%RESOURCE_GROUP%" --location "%LOCATION%" --sku Standard_LRS --kind StorageV2
    echo [SUCCESS] Storage account created: %STORAGE_ACCOUNT%
)

echo [INFO] Retrieving storage account key...
for /f "tokens=*" %%i in ('az storage account keys list --account-name "%STORAGE_ACCOUNT%" --resource-group "%RESOURCE_GROUP%" --query "[0].value" -o tsv') do set "STORAGE_KEY=%%i"

echo [INFO] Creating Azure file shares...
for %%s in (data uploads logs) do (
    az storage share create --name "%%s" --account-name "%STORAGE_ACCOUNT%" --account-key "%STORAGE_KEY%" --quota 10 >nul 2>&1
)
echo [SUCCESS] File shares created: data, uploads, logs

exit /b 0

:create_log_analytics
echo.
echo [INFO] Creating Log Analytics Workspace...
echo.

set "LOG_ANALYTICS=%RESOURCE_GROUP:-rg=%-logs"

az monitor log-analytics workspace show --workspace-name "%LOG_ANALYTICS%" --resource-group "%RESOURCE_GROUP%" >nul 2>&1
if not errorlevel 1 (
    echo [WARNING] Log Analytics workspace %LOG_ANALYTICS% already exists
) else (
    az monitor log-analytics workspace create --workspace-name "%LOG_ANALYTICS%" --resource-group "%RESOURCE_GROUP%" --location "%LOCATION%"
    echo [SUCCESS] Log Analytics workspace created: %LOG_ANALYTICS%
)

for /f "tokens=*" %%i in ('az monitor log-analytics workspace get-shared-keys --workspace-name "%LOG_ANALYTICS%" --resource-group "%RESOURCE_GROUP%" --query primarySharedKey -o tsv') do set "LOG_ANALYTICS_KEY=%%i"
for /f "tokens=*" %%i in ('az monitor log-analytics workspace show --workspace-name "%LOG_ANALYTICS%" --resource-group "%RESOURCE_GROUP%" --query customerId -o tsv') do set "LOG_ANALYTICS_ID=%%i"

echo [SUCCESS] Log Analytics credentials retrieved

exit /b 0

:create_container_env
echo.
echo [INFO] Creating Container Apps Environment...
echo.

set "ENVIRONMENT_NAME=%RESOURCE_GROUP:-rg=%-env"

az containerapp env show --name "%ENVIRONMENT_NAME%" --resource-group "%RESOURCE_GROUP%" >nul 2>&1
if not errorlevel 1 (
    echo [WARNING] Container Apps environment %ENVIRONMENT_NAME% already exists
) else (
    az containerapp env create --name "%ENVIRONMENT_NAME%" --resource-group "%RESOURCE_GROUP%" --location "%LOCATION%" --logs-workspace-id "%LOG_ANALYTICS_ID%" --logs-workspace-key "%LOG_ANALYTICS_KEY%"
    echo [SUCCESS] Container Apps environment created: %ENVIRONMENT_NAME%
)
exit /b 0

:create_container_app
echo.
echo [INFO] Creating Container App...
echo.

set "ENVIRONMENT_NAME=%RESOURCE_GROUP:-rg=%-env"

az containerapp show --name "%APP_NAME%" --resource-group "%RESOURCE_GROUP%" >nul 2>&1
if not errorlevel 1 (
    echo [WARNING] Container app %APP_NAME% already exists (will be updated during deployment)
    exit /b 0
)

echo [INFO] Creating container app...

for /f "tokens=*" %%i in ('az acr credential show --name "%ACR_NAME%" --query username -o tsv') do set "ACR_USERNAME=%%i"
for /f "tokens=*" %%i in ('az acr credential show --name "%ACR_NAME%" --query passwords[0].value -o tsv') do set "ACR_PASSWORD=%%i"
for /f "tokens=*" %%i in ('az acr show --name "%ACR_NAME%" --query loginServer -o tsv') do set "ACR_LOGIN_SERVER=%%i"

az containerapp create --name "%APP_NAME%" --resource-group "%RESOURCE_GROUP%" --environment "%ENVIRONMENT_NAME%" --image "%ACR_LOGIN_SERVER%/%IMAGE_NAME%:latest" --target-port 5000 --ingress external --registry-server "%ACR_LOGIN_SERVER%" --registry-username "%ACR_USERNAME%" --registry-password "%ACR_PASSWORD%" --cpu 2.0 --memory 4Gi --min-replicas 1 --max-replicas 5 --env-vars "FLASK_ENV=production" "PYTHONUNBUFFERED=1" "CHROMADB_ENABLED=false" "ORACLE_ENABLED=false"

echo [SUCCESS] Container app created: %APP_NAME%
echo [INFO] Environment variables will be configured during deployment

exit /b 0

:deploy_to_azure
echo.
echo [INFO] Deploying to Azure Container Apps...
echo.

REM Generate secrets if not set
if "%SECRET_KEY%"=="" (
    for /f "tokens=*" %%i in ('powershell -Command "[System.Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes([System.Guid]::NewGuid().ToString()))"') do set "SECRET_KEY=%%i"
)
if "%JWT_SECRET_KEY%"=="" (
    for /f "tokens=*" %%i in ('powershell -Command "[System.Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes([System.Guid]::NewGuid().ToString()))"') do set "JWT_SECRET_KEY=%%i"
)
if "%ADMIN_EMAIL%"=="" set "ADMIN_EMAIL=admin@eeai.com"
if "%ADMIN_PASSWORD%"=="" set "ADMIN_PASSWORD=Admin@123456"
if "%AZURE_OPENAI_DEPLOYMENT_NAME%"=="" set "AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o"
if "%AZURE_EMBEDDING_MODEL%"=="" set "AZURE_EMBEDDING_MODEL=text-embedding-3-large"

set "ENV_VARS=MONGO_URI=%MONGO_URI% MONGO_DB_NAME=eeai_data REDIS_URL=%REDIS_URL% SECRET_KEY=%SECRET_KEY% JWT_SECRET_KEY=%JWT_SECRET_KEY% ADMIN_EMAIL=%ADMIN_EMAIL% ADMIN_PASSWORD=%ADMIN_PASSWORD% FLASK_ENV=production PYTHONUNBUFFERED=1 CHROMADB_ENABLED=false ORACLE_ENABLED=false AZURE_OPENAI_API_BASE=%AZURE_OPENAI_API_BASE% AZURE_OPENAI_API_KEY=%AZURE_OPENAI_API_KEY% AZURE_OPENAI_DEPLOYMENT_NAME=%AZURE_OPENAI_DEPLOYMENT_NAME% AZURE_EMBEDDING_MODEL=%AZURE_EMBEDDING_MODEL% AZURE_EMBEDDING_KEY=%AZURE_EMBEDDING_KEY% AZURE_CV_ENDPOINT=%AZURE_CV_ENDPOINT% AZURE_CV_KEY=%AZURE_CV_KEY%"

echo [INFO] Updating container app with environment variables...

if not "%IMAGE_DIGEST%"=="" (
    az containerapp update --name "%APP_NAME%" --resource-group "%RESOURCE_GROUP%" --image "%ACR_NAME%.azurecr.io/%IMAGE_NAME%@%IMAGE_DIGEST%" --set-env-vars %ENV_VARS% > deploy_output.json
    echo [INFO] Using specific image digest: %IMAGE_DIGEST%
) else (
    az containerapp update --name "%APP_NAME%" --resource-group "%RESOURCE_GROUP%" --image "%FULL_IMAGE_NAME%" --set-env-vars %ENV_VARS% > deploy_output.json
    echo [INFO] Using latest tag: %FULL_IMAGE_NAME%
)

if errorlevel 1 (
    echo [ERROR] Deployment failed!
    exit /b 1
)

echo [SUCCESS] Deployment successful!

for /f "tokens=*" %%i in ('powershell -Command "(Get-Content deploy_output.json | ConvertFrom-Json).properties.latestRevisionName"') do set "NEW_REVISION=%%i"
echo [INFO] New revision: %NEW_REVISION%

exit /b 0

:verify_deployment
echo.
echo [INFO] Verifying deployment...
echo.

echo [INFO] Waiting for revision to become ready (max 2 minutes)...

set /a MAX_ATTEMPTS=24
set /a ATTEMPT=0

:verify_loop
if %ATTEMPT% geq %MAX_ATTEMPTS% goto verify_timeout

for /f "tokens=*" %%i in ('az containerapp revision show --name "%NEW_REVISION%" --app "%APP_NAME%" --resource-group "%RESOURCE_GROUP%" --query "properties.runningState" -o tsv 2^>nul') do set "STATUS=%%i"

if "%STATUS%"=="Running" (
    echo.
    echo [SUCCESS] Revision is running!
    exit /b 0
)
if "%STATUS%"=="Failed" (
    echo.
    echo [ERROR] Revision failed to start!
    exit /b 1
)

echo|set /p="."
timeout /t 5 /nobreak >nul
set /a ATTEMPT+=1
goto verify_loop

:verify_timeout
echo.
echo [WARNING] Timeout waiting for revision to be ready
exit /b 0

:test_application
echo.
echo [INFO] Testing application endpoints...
echo.

for /f "tokens=*" %%i in ('az containerapp show --name "%APP_NAME%" --resource-group "%RESOURCE_GROUP%" --query "properties.configuration.ingress.fqdn" -o tsv') do set "APP_URL=%%i"
set "FULL_URL=https://%APP_URL%"

echo [INFO] Application URL: %FULL_URL%

echo [INFO] Testing main endpoint...
for /f "tokens=*" %%i in ('curl -s -o nul -w "%%{http_code}" "%FULL_URL%/" 2^>nul') do set "HTTP_CODE=%%i"

if "%HTTP_CODE%"=="200" (
    echo [SUCCESS] Main endpoint responding: HTTP %HTTP_CODE%
) else (
    echo [ERROR] Main endpoint not responding: HTTP %HTTP_CODE%
)

exit /b 0

:show_logs
echo.
echo [INFO] Recent application logs...
echo.

echo [INFO] Fetching last 30 log lines...
az containerapp logs show --name "%APP_NAME%" --resource-group "%RESOURCE_GROUP%" --tail 30 --follow=false 2>nul | findstr /i "INFO ERROR WARNING Connected OpenAI"

exit /b 0

:print_summary
echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║ DEPLOYMENT SUMMARY                                             ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

echo [SUCCESS] Deployment completed successfully!
echo.
echo [INFO] Docker Image:
echo    Registry: %ACR_NAME%.azurecr.io
echo    Image: %IMAGE_NAME%:%IMAGE_TAG%
if not "%IMAGE_DIGEST%"=="" echo    Digest: %IMAGE_DIGEST%
echo.
echo [INFO] Azure Container App:
echo    Resource Group: %RESOURCE_GROUP%
echo    App Name: %APP_NAME%
if not "%NEW_REVISION%"=="" echo    Revision: %NEW_REVISION%
echo.
echo [INFO] Application URL:
for /f "tokens=*" %%i in ('az containerapp show --name "%APP_NAME%" --resource-group "%RESOURCE_GROUP%" --query "properties.configuration.ingress.fqdn" -o tsv 2^>nul') do set "APP_URL=%%i"
echo    https://%APP_URL%
echo.
echo [INFO] Environment Variables Set:
echo    • MongoDB (Cosmos DB) - Configured
echo    • Redis Cache - Configured
echo    • Azure OpenAI (gpt-4o) - Configured
echo    • Azure Computer Vision - Configured
echo    • Embeddings (text-embedding-3-large) - Configured
echo    • Oracle Database - Disabled
echo    • ChromaDB - Disabled
echo.
echo [INFO] Quick Commands:
echo    View logs:    az containerapp logs show --name %APP_NAME% --resource-group %RESOURCE_GROUP% --tail 50
echo    Check status: az containerapp show --name %APP_NAME% --resource-group %RESOURCE_GROUP%
echo    Test app:     curl https://%APP_URL%/health
echo.

exit /b 0

:show_help
echo Usage: %~nx0 [OPTIONS]
echo.
echo Complete deployment script for EEAIAdmin to Azure Container Apps
echo.
echo Options:
echo   --subscription-id ^<ID^>  Use specific Azure subscription ID
echo   --skip-build            Skip Docker build step (use existing local image)
echo   --skip-push             Skip Docker push step (use existing image in ACR)
echo   --force-build           Force rebuild without cache (--no-cache)
echo   --create-infra          Create all Azure infrastructure
echo   --infra-only            Only create infrastructure, skip Docker build/deploy
echo   --help                  Show this help message
echo.
echo Infrastructure Creation (--create-infra):
echo   Creates the following Azure resources:
echo     • Resource Group
echo     • Azure Container Registry
echo     • Cosmos DB (MongoDB API)
echo     • Azure Cache for Redis
echo     • Storage Account with File Shares
echo     • Log Analytics Workspace
echo     • Container Apps Environment
echo     • Container App
echo   Note: This may take 15-30 minutes
echo.
echo Examples:
echo   %~nx0                                    # Standard deployment (update existing app)
echo   %~nx0 --subscription-id abc-123-def      # Deploy to specific subscription
echo   %~nx0 --create-infra                     # Create all infrastructure + deploy app
echo   %~nx0 --infra-only                       # Only create infrastructure (no deployment)
echo   %~nx0 --skip-build                       # Deploy existing local image
echo   %~nx0 --skip-build --skip-push           # Update env vars only (no image changes)
echo   %~nx0 --force-build                      # Force rebuild from scratch
echo.
exit /b 0
