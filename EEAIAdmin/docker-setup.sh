#!/bin/bash
# Quick Docker Setup Script for EEAIAdmin

echo "================================================"
echo "EEAIAdmin Docker Setup"
echo "================================================"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "ERROR: Docker is not running. Please start Docker Desktop."
    exit 1
fi

echo "✓ Docker is running"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "WARNING: .env file not found!"
    echo "Creating .env from .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "✓ .env file created. Please edit it with your configuration."
        echo ""
        read -p "Press Enter to continue or Ctrl+C to exit and configure .env first..."
    else
        echo "ERROR: .env.example not found. Cannot proceed."
        exit 1
    fi
fi

echo "✓ .env file exists"
echo ""

# Build the Docker image
echo "Building Docker image (this may take 5-10 minutes)..."
docker-compose build

if [ $? -ne 0 ]; then
    echo "ERROR: Build failed. Check the error messages above."
    exit 1
fi

echo "✓ Build successful"
echo ""

# Start all services
echo "Starting all services..."
docker-compose up -d

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to start services. Check the error messages above."
    exit 1
fi

echo "✓ Services started"
echo ""

# Wait for services to be healthy
echo "Waiting for services to be healthy..."
sleep 10

# Check service status
echo ""
echo "Service Status:"
docker-compose ps

echo ""
echo "================================================"
echo "Setup Complete!"
echo "================================================"
echo ""
echo "Access your application at:"
echo "  - HTTP:  http://localhost"
echo "  - HTTPS: https://localhost"
echo ""
echo "Service URLs:"
echo "  - ChromaDB: http://localhost:8000"
echo "  - MongoDB:  localhost:27017"
echo "  - Redis:    localhost:6379"
echo ""
echo "Useful Commands:"
echo "  - View logs:     docker-compose logs -f"
echo "  - Stop services: docker-compose down"
echo "  - Restart:       docker-compose restart"
echo ""
echo "For more information, see DOCKER_SETUP_GUIDE.md"
echo ""
