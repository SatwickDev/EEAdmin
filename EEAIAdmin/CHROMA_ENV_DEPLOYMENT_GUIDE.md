# Chroma Environment Variables - Deployment Guide

## Quick Reference

Pass environment variables to control ChromaDB per deployment. Same code, different configs per bank.

---

## 1. Local Development

### PowerShell (Windows)
```powershell
# Set single env var
$env:CHROMA_MODE = "allowlist"
$env:CHROMA_CUSTOMERS = "bank1,bank2"

# Run app
python run.py

# Or inline (for single run)
$env:CHROMA_MODE="disabled"; python run.py
```

### Bash/Linux/Mac
```bash
# Set env var
export CHROMA_MODE=allowlist
export CHROMA_CUSTOMERS="bank1,bank2"

# Run app
python run.py

# Or inline (for single run)
CHROMA_MODE=allowlist python run.py
```

### .env file (with python-dotenv)
Create `.env` file in project root:
```bash
CHROMA_MODE=allowlist
CHROMA_CUSTOMERS=bank1,bank2,bank3
CHROMA_HOST=localhost
CHROMA_PORT=8000
```

Then in your Flask app or run script:
```python
from dotenv import load_dotenv
load_dotenv()

# Now env vars are loaded from .env
from app import create_app
app = create_app()
```

---

## 2. Docker Deployment

### Docker run (inline env vars)
```bash
# Chroma disabled globally
docker run -d \
  --name eeai-bank-a \
  -e CHROMA_MODE=disabled \
  -p 5000:5000 \
  myregistry/eeai-app:latest

# Chroma enabled for specific customers
docker run -d \
  --name eeai-bank-b \
  -e CHROMA_MODE=allowlist \
  -e CHROMA_CUSTOMERS="bank1,bank2" \
  -e CHROMA_HOST=chroma-server.internal \
  -e CHROMA_PORT=8000 \
  -p 5000:5000 \
  myregistry/eeai-app:latest

# Chroma enabled globally
docker run -d \
  --name eeai-bank-c \
  -e CHROMA_MODE=enabled \
  -p 5000:5000 \
  myregistry/eeai-app:latest
```

### Docker run with .env file
```bash
# Create bank-a.env file
cat > bank-a.env <<EOF
CHROMA_MODE=disabled
DATABASE_URL=mongodb://mongo-a:27017/finai_chatbot
EOF

# Run with env file
docker run -d \
  --name eeai-bank-a \
  --env-file bank-a.env \
  -p 5000:5000 \
  myregistry/eeai-app:latest
```

### Docker Compose (per service)
```yaml
version: '3.8'

services:
  app-bank-a:
    image: myregistry/eeai-app:latest
    container_name: eeai-bank-a
    ports:
      - "5001:5000"
    environment:
      CHROMA_MODE: disabled
      CHROMA_HOST: localhost
      CHROMA_PORT: 8000
      DATABASE_URL: mongodb://mongo-a:27017/finai_chatbot

  app-bank-b:
    image: myregistry/eeai-app:latest
    container_name: eeai-bank-b
    ports:
      - "5002:5000"
    environment:
      CHROMA_MODE: allowlist
      CHROMA_CUSTOMERS: "bank1,bank2,bank3"
      CHROMA_HOST: chroma-server
      CHROMA_PORT: 8000
      DATABASE_URL: mongodb://mongo-b:27017/finai_chatbot

  chroma-server:
    image: ghcr.io/chroma-core/chroma:latest
    ports:
      - "8000:8000"
```

Or reference external .env files:
```yaml
services:
  app-bank-a:
    image: myregistry/eeai-app:latest
    env_file:
      - ./envs/bank-a.env
      - ./envs/common.env  # shared vars
    ports:
      - "5001:5000"
```

---

## 3. Kubernetes Deployment (via Terraform)

### Basic Terraform - ConfigMap (non-secret values)

```hcl
# variables.tf
variable "chroma_mode" {
  type    = string
  default = "disabled"
}

variable "chroma_customers" {
  type    = string
  default = ""
}

variable "chroma_host" {
  type    = string
  default = "localhost"
}

variable "chroma_port" {
  type    = string
  default = "8000"
}

# main.tf
resource "kubernetes_config_map" "app_config" {
  metadata {
    name      = "eeai-app-config"
    namespace = var.namespace
  }

  data = {
    CHROMA_MODE      = var.chroma_mode
    CHROMA_CUSTOMERS = var.chroma_customers
    CHROMA_HOST      = var.chroma_host
    CHROMA_PORT      = var.chroma_port
  }
}

resource "kubernetes_deployment" "app" {
  metadata {
    name      = "eeai-app"
    namespace = var.namespace
  }

  spec {
    replicas = var.replicas

    selector {
      match_labels = {
        app = "eeai-app"
      }
    }

    template {
      metadata {
        labels = {
          app = "eeai-app"
        }
      }

      spec {
        container {
          name  = "eeai-app"
          image = var.image

          # Load all ConfigMap values as env vars
          env_from {
            config_map_ref {
              name = kubernetes_config_map.app_config.metadata[0].name
            }
          }

          port {
            container_port = 5000
          }
        }
      }
    }
  }
}
```

### Kubernetes - Using Secrets for sensitive values

```hcl
# For database credentials or API keys (not shown in ConfigMap)
resource "kubernetes_secret" "app_secrets" {
  metadata {
    name      = "eeai-app-secrets"
    namespace = var.namespace
  }

  type = "Opaque"

  data = {
    DATABASE_URL = base64encode(var.database_url)
    MONGO_URI    = base64encode(var.mongo_uri)
  }
}

resource "kubernetes_deployment" "app" {
  # ... (from above)
  spec {
    template {
      spec {
        container {
          name  = "eeai-app"
          image = var.image

          # Load ConfigMap (public config)
          env_from {
            config_map_ref {
              name = kubernetes_config_map.app_config.metadata[0].name
            }
          }

          # Load Secrets (sensitive values)
          env_from {
            secret_ref {
              name = kubernetes_secret.app_secrets.metadata[0].name
            }
          }

          port {
            container_port = 5000
          }
        }
      }
    }
  }
}
```

### Terraform variables by customer (workspaces or separate .tfvars)

```hcl
# terraform.tfvars for Bank A (disabled)
chroma_mode      = "disabled"
chroma_customers = ""
chroma_host      = "localhost"
chroma_port      = "8000"
```

```hcl
# bank-b.tfvars for Bank B (allowlist)
chroma_mode      = "allowlist"
chroma_customers = "bank1,bank2,bank3"
chroma_host      = "chroma-server.default.svc.cluster.local"
chroma_port      = "8000"
```

Apply per bank:
```bash
# Deploy Bank A (disabled)
terraform apply -var-file="bank-a.tfvars"

# Deploy Bank B (allowlist)
terraform apply -var-file="bank-b.tfvars"

# Or use workspaces
terraform workspace new bank-a
terraform apply -var-file="envs/bank-a.tfvars"

terraform workspace new bank-b
terraform apply -var-file="envs/bank-b.tfvars"
```

---

## 4. AWS ECS Task Definition (via Terraform)

```hcl
resource "aws_ecs_task_definition" "app" {
  family                   = "eeai-app"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name      = "eeai-app"
      image     = var.image
      essential = true
      portMappings = [
        {
          containerPort = 5000
          hostPort      = 5000
          protocol      = "tcp"
        }
      ]
      environment = [
        {
          name  = "CHROMA_MODE"
          value = var.chroma_mode
        },
        {
          name  = "CHROMA_CUSTOMERS"
          value = var.chroma_customers
        },
        {
          name  = "CHROMA_HOST"
          value = var.chroma_host
        },
        {
          name  = "CHROMA_PORT"
          value = tostring(var.chroma_port)
        },
      ]
      secrets = [
        {
          name      = "DATABASE_URL"
          valueFrom = aws_secretsmanager_secret.database_url.arn
        },
        {
          name      = "MONGO_URI"
          valueFrom = aws_secretsmanager_secret.mongo_uri.arn
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.app.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "app" {
  name            = "eeai-app-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.subnet_ids
    security_groups  = var.security_group_ids
    assign_public_ip = false
  }
}
```

---

## 5. AWS Lambda (Serverless)

### Via environment variables directly
```hcl
resource "aws_lambda_function" "app" {
  filename      = "lambda.zip"
  function_name = "eeai-app"
  role          = aws_iam_role.lambda_role.arn
  handler       = "app.handler"

  environment {
    variables = {
      CHROMA_MODE      = var.chroma_mode
      CHROMA_CUSTOMERS = var.chroma_customers
      CHROMA_HOST      = var.chroma_host
      CHROMA_PORT      = var.chroma_port
    }
  }
}
```

### Or via AWS Systems Manager Parameter Store
```hcl
resource "aws_ssm_parameter" "chroma_config" {
  name  = "/eeai/chroma_mode"
  type  = "String"
  value = var.chroma_mode
}

# Then in Lambda code:
import boto3
ssm = boto3.client('ssm')
chroma_mode = ssm.get_parameter(Name='/eeai/chroma_mode')['Parameter']['Value']
```

---

## 6. Dockerfile (Baking defaults into image)

### Option A: No defaults (must pass at runtime)
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . /app
RUN pip install -r requirements.txt

# No defaults set - env vars must be passed at run time
CMD ["python", "run.py"]
```

### Option B: Safe defaults (disabled)
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . /app
RUN pip install -r requirements.txt

# Default: Chroma disabled (safest)
ENV CHROMA_MODE=disabled
ENV CHROMA_HOST=localhost
ENV CHROMA_PORT=8000

CMD ["python", "run.py"]
```

### Option C: Build-time arguments (per customer builds)
```dockerfile
FROM python:3.11-slim

ARG CHROMA_MODE=disabled
ARG CHROMA_CUSTOMERS=""
ARG CHROMA_HOST=localhost
ARG CHROMA_PORT=8000

ENV CHROMA_MODE=${CHROMA_MODE}
ENV CHROMA_CUSTOMERS=${CHROMA_CUSTOMERS}
ENV CHROMA_HOST=${CHROMA_HOST}
ENV CHROMA_PORT=${CHROMA_PORT}

WORKDIR /app
COPY . /app
RUN pip install -r requirements.txt

CMD ["python", "run.py"]
```

Build per bank:
```bash
# Bank A (no Chroma)
docker build -t bank-a:latest \
  --build-arg CHROMA_MODE=disabled .

# Bank B (with Chroma)
docker build -t bank-b:latest \
  --build-arg CHROMA_MODE=allowlist \
  --build-arg CHROMA_CUSTOMERS="bank1,bank2,bank3" .
```

---

## 7. Environment Variable Summary Table

| Env Var | Type | Default | Example | Notes |
|---------|------|---------|---------|-------|
| `CHROMA_MODE` | string | `disabled` | `enabled`, `allowlist`, `disabled` | Primary control flag |
| `CHROMA_CUSTOMERS` | csv | empty | `bank1,bank2,bank3` | For allowlist mode |
| `CHROMA_HOST` | string | `localhost` | `chroma-server.internal` | Chroma server hostname |
| `CHROMA_PORT` | int | `8000` | `9999` | Chroma server port |
| `CHROMA_ENABLED` | bool | `false` | `true`, `false` | Legacy flag (use CHROMA_MODE) |
| `CHROMA_ENABLED_FOR_ALL` | bool | `false` | `true`, `false` | Legacy flag (use CHROMA_MODE) |

---

## 8. Best Practices

### ✅ DO:
- Use env vars for **per-deployment configuration** (different per bank/customer)
- Use `CHROMA_MODE=disabled` as **default** for safety
- Use **Kubernetes Secrets** or **AWS Secrets Manager** for sensitive values
- Use **ConfigMap** for non-sensitive configuration
- Document which vars each deployment uses

### ❌ DON'T:
- Hardcode secrets in Dockerfile (use secrets manager at runtime)
- Use `CHROMA_ENABLED=true` in production without specifying `CHROMA_MODE`
- Mix ConfigMap and Secrets without clear documentation
- Pass secrets via `docker run -e` (use secrets manager instead)

---

## 9. Checking Active Configuration

The app logs which configuration source is active. Check logs:

```bash
# Docker logs
docker logs eeai-bank-a

# Expected output:
# DEBUG:app.utils.chroma_manager:Chroma disabled via ENV for customer None
# or
# DEBUG:app.utils.chroma_manager:Chroma allowlist via ENV for customer bank1: True
```

Or use the admin API:
```bash
curl http://localhost:5000/api/admin/repository_config
```

---

## 10. Example: Three Banks, Different Configs

```yaml
# docker-compose.yml

version: '3.8'

services:
  # Bank A: No Chroma
  app-bank-a:
    image: myregistry/eeai:latest
    environment:
      CHROMA_MODE: disabled
    ports:
      - "5001:5000"

  # Bank B: Chroma for specific customers
  app-bank-b:
    image: myregistry/eeai:latest
    environment:
      CHROMA_MODE: allowlist
      CHROMA_CUSTOMERS: customer1,customer2
      CHROMA_HOST: chroma
      CHROMA_PORT: "8000"
    ports:
      - "5002:5000"

  # Bank C: Chroma for all customers
  app-bank-c:
    image: myregistry/eeai:latest
    environment:
      CHROMA_MODE: enabled
      CHROMA_HOST: chroma
      CHROMA_PORT: "8000"
    ports:
      - "5003:5000"

  chroma:
    image: ghcr.io/chroma-core/chroma:latest
    ports:
      - "8000:8000"
```

Run all three:
```bash
docker-compose up -d
```

Each bank has different Chroma settings, same code!

---

## 11. Terraform Workspace Example

```bash
# Create workspaces for each bank
terraform workspace new bank-a
terraform workspace new bank-b
terraform workspace new bank-c

# Deploy to Bank A (disabled)
terraform workspace select bank-a
terraform apply -var-file="vars/bank-a.tfvars"

# Deploy to Bank B (allowlist)
terraform workspace select bank-b
terraform apply -var-file="vars/bank-b.tfvars"

# Deploy to Bank C (enabled)
terraform workspace select bank-c
terraform apply -var-file="vars/bank-c.tfvars"
```

Each workspace is isolated, same Terraform code, different outputs!

---

## Quick Cheat Sheet

```bash
# Local dev: Set env var and run
export CHROMA_MODE=allowlist
export CHROMA_CUSTOMERS="bank1,bank2"
python run.py

# Docker: One-liner
docker run -e CHROMA_MODE=disabled -e CHROMA_CUSTOMERS="" myapp:latest

# Docker Compose: YAML file (see section 10)
docker-compose up -d

# Kubernetes: Terraform + tfvars
terraform apply -var-file="bank-a.tfvars"

# AWS ECS: CloudFormation or Terraform
terraform apply -var-file="ecs-bank-a.tfvars"
```
