# Docker Setup Guide for EEAIAdmin

This guide will help you build and run the EEAIAdmin application as a Docker image locally.

## Prerequisites

1. **Docker Desktop** installed and running
2. **WSL2** enabled (for Windows)
3. At least **8GB RAM** allocated to Docker
4. At least **20GB** free disk space

## Quick Start Commands

### 1. Build the Docker Image

```powershell
# Navigate to project directory
cd C:\Users\saipr\Documents\GitHub\EEAIAdmin

# Build the image (this will take 5-10 minutes first time)
docker-compose build
```

### 2. Start All Services

```powershell
# Start all services (app, ChromaDB, MongoDB, Redis)
docker-compose up -d

# View logs
docker-compose logs -f eeai-app
```

### 3. Stop All Services

```powershell
# Stop all services
docker-compose down

# Stop and remove volumes (WARNING: deletes all data)
docker-compose down -v
```

## Detailed Commands

### Building Only the Application Image

```powershell
# Build just the app image with a specific tag
docker build -t eeai-admin:latest .

# Build with no cache (clean build)
docker build --no-cache -t eeai-admin:latest .
```

### Running Individual Services

```powershell
# Start only ChromaDB
docker-compose up -d chromadb

# Start only MongoDB
docker-compose up -d mongodb

# Start only the application
docker-compose up -d eeai-app
```

### Viewing Logs

```powershell
# View all logs
docker-compose logs

# View specific service logs
docker-compose logs eeai-app
docker-compose logs chromadb
docker-compose logs mongodb

# Follow logs in real-time
docker-compose logs -f eeai-app

# View last 100 lines
docker-compose logs --tail=100 eeai-app
```

### Service Management

```powershell
# Check service status
docker-compose ps

# Restart a service
docker-compose restart eeai-app

# Stop a specific service
docker-compose stop eeai-app

# Remove stopped containers
docker-compose rm
```

### Accessing Services

Once running, access your services at:

- **Application**: http://localhost or https://localhost
- **ChromaDB**: http://localhost:8000
- **MongoDB**: localhost:27017
- **Redis**: localhost:6379

### Health Checks

```powershell
# Check if services are healthy
docker-compose ps

# Check ChromaDB health
curl http://localhost:8000/api/v1/heartbeat

# Check MongoDB health
docker-compose exec mongodb mongosh --eval "db.adminCommand('ping')"

# Check Redis health
docker-compose exec redis redis-cli ping
```

### Troubleshooting

#### View Container Details

```powershell
# List all containers
docker ps -a

# Inspect a container
docker inspect eeai-app

# View resource usage
docker stats
```

#### Access Container Shell

```powershell
# Access app container
docker-compose exec eeai-app bash

# Access MongoDB shell
docker-compose exec mongodb mongosh

# Access Redis CLI
docker-compose exec redis redis-cli
```

#### Check Logs for Errors

```powershell
# View app errors
docker-compose logs eeai-app | Select-String -Pattern "ERROR"

# View all error logs
docker-compose logs | Select-String -Pattern "ERROR"
```

#### Restart Services

```powershell
# Restart all services
docker-compose restart

# Restart only the app
docker-compose restart eeai-app
```

## Environment Variables

Create a `.env` file in the project root with your configuration:

```env
# Server Configuration
SERVER_HOST=0.0.0.0
HTTP_PORT=80
HTTPS_PORT=443
DEBUG_MODE=false
SSL_ENABLED=true

# ChromaDB Configuration
CHROMADB_HOST=chromadb
CHROMADB_PORT=8000
CHROMADB_TELEMETRY_ENABLED=false

# MongoDB Configuration
MONGODB_HOST=mongodb
MONGODB_PORT=27017
MONGODB_USERNAME=admin
MONGODB_PASSWORD=password
MONGODB_DATABASE=eeai_admin

# Azure OpenAI Configuration
AZURE_OPENAI_API_KEY=your_key_here
AZURE_OPENAI_ENDPOINT=your_endpoint_here
AZURE_OPENAI_DEPLOYMENT=your_deployment_here
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# Add other environment variables as needed
```

## Volume Management

### Backup Data

```powershell
# Backup MongoDB data
docker-compose exec mongodb mongodump --out /data/backup

# Backup ChromaDB data
docker cp eeaiadmin-chromadb-1:/chroma/chroma ./chromadb_backup
```

### Restore Data

```powershell
# Restore MongoDB data
docker-compose exec mongodb mongorestore /data/backup

# Restore ChromaDB data
docker cp ./chromadb_backup eeaiadmin-chromadb-1:/chroma/chroma
```

### Clean Up

```powershell
# Remove all stopped containers
docker container prune

# Remove all unused images
docker image prune -a

# Remove all unused volumes
docker volume prune

# Complete cleanup (WARNING: removes everything)
docker system prune -a --volumes
```

## Advanced Configuration

### Custom Network

```powershell
# Create custom network
docker network create eeai-custom-network

# Use custom network in docker-compose.yml
# Update the networks section
```

### Resource Limits

Add to `docker-compose.yml` under `eeai-app`:

```yaml
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 4G
    reservations:
      cpus: '1'
      memory: 2G
```

### Production Deployment

```powershell
# Build for production
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build

# Run in production mode
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Common Issues and Solutions

### Issue: Port Already in Use

```powershell
# Find process using port
netstat -ano | findstr :8000

# Kill the process (replace PID)
taskkill /PID <PID> /F
```

### Issue: Container Won't Start

```powershell
# Check logs
docker-compose logs eeai-app

# Rebuild image
docker-compose build --no-cache eeai-app

# Restart services
docker-compose restart
```

### Issue: Out of Disk Space

```powershell
# Check Docker disk usage
docker system df

# Clean up
docker system prune -a --volumes
```

### Issue: Slow Performance

```powershell
# Increase Docker memory in Docker Desktop settings
# Go to: Docker Desktop → Settings → Resources → Memory
# Recommended: 8GB minimum

# Check resource usage
docker stats
```

## Monitoring

### View Real-time Metrics

```powershell
# Resource usage
docker stats

# Service health
docker-compose ps

# Network connections
docker network inspect eeai-network
```

### Export Logs

```powershell
# Export all logs to file
docker-compose logs > docker-logs.txt

# Export specific service logs
docker-compose logs eeai-app > app-logs.txt
```

## Security Best Practices

1. **Never commit `.env` file** to version control
2. **Use strong passwords** for MongoDB and other services
3. **Enable SSL/TLS** in production
4. **Regularly update** Docker images
5. **Limit container resources** to prevent DoS
6. **Use secrets management** for sensitive data

## Next Steps

1. ✅ Build the image: `docker-compose build`
2. ✅ Start services: `docker-compose up -d`
3. ✅ Check logs: `docker-compose logs -f`
4. ✅ Access application: http://localhost
5. ✅ Monitor health: `docker-compose ps`

## Support

For issues or questions:
- Check logs: `docker-compose logs`
- Check status: `docker-compose ps`
- Restart services: `docker-compose restart`
- Rebuild: `docker-compose build --no-cache`
