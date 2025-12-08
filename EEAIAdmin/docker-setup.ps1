# Quick Docker Setup Script for EEAIAdmin (Windows PowerShell)

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "EEAIAdmin Docker Setup" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is running
try {
    docker info | Out-Null
    Write-Host "✓ Docker is running" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Docker is not running. Please start Docker Desktop." -ForegroundColor Red
    exit 1
}
Write-Host ""

# Check if .env file exists
if (-not (Test-Path .env)) {
    Write-Host "WARNING: .env file not found!" -ForegroundColor Yellow
    Write-Host "Creating .env from .env.example..."
    if (Test-Path .env.example) {
        Copy-Item .env.example .env
        Write-Host "✓ .env file created. Please edit it with your configuration." -ForegroundColor Green
        Write-Host ""
        Read-Host "Press Enter to continue or Ctrl+C to exit and configure .env first"
    } else {
        Write-Host "ERROR: .env.example not found. Cannot proceed." -ForegroundColor Red
        exit 1
    }
}

Write-Host "✓ .env file exists" -ForegroundColor Green
Write-Host ""

# Build the Docker image
Write-Host "Building Docker image (this may take 5-10 minutes)..." -ForegroundColor Yellow
docker-compose build

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Build failed. Check the error messages above." -ForegroundColor Red
    exit 1
}

Write-Host "✓ Build successful" -ForegroundColor Green
Write-Host ""

# Start all services
Write-Host "Starting all services..." -ForegroundColor Yellow
docker-compose up -d

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to start services. Check the error messages above." -ForegroundColor Red
    exit 1
}

Write-Host "✓ Services started" -ForegroundColor Green
Write-Host ""

# Wait for services to be healthy
Write-Host "Waiting for services to be healthy..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Check service status
Write-Host ""
Write-Host "Service Status:" -ForegroundColor Cyan
docker-compose ps

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Access your application at:" -ForegroundColor White
Write-Host "  - HTTP:  http://localhost" -ForegroundColor White
Write-Host "  - HTTPS: https://localhost" -ForegroundColor White
Write-Host ""
Write-Host "Service URLs:" -ForegroundColor White
Write-Host "  - ChromaDB: http://localhost:8000" -ForegroundColor White
Write-Host "  - MongoDB:  localhost:27017" -ForegroundColor White
Write-Host "  - Redis:    localhost:6379" -ForegroundColor White
Write-Host ""
Write-Host "Useful Commands:" -ForegroundColor Yellow
Write-Host "  - View logs:     docker-compose logs -f" -ForegroundColor White
Write-Host "  - Stop services: docker-compose down" -ForegroundColor White
Write-Host "  - Restart:       docker-compose restart" -ForegroundColor White
Write-Host ""
Write-Host "For more information, see DOCKER_SETUP_GUIDE.md" -ForegroundColor Cyan
Write-Host ""
