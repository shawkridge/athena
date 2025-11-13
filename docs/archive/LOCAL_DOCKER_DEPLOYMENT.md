# Athena Local Docker Deployment Guide

**Version**: 1.0
**Status**: Production Ready
**Last Updated**: November 10, 2025
**Platform**: Linux, macOS, Windows (Docker Desktop)

---

## Overview

This guide provides step-by-step instructions for deploying the Athena 8-layer memory system locally using Docker Compose. All services (PostgreSQL, Ollama, Redis, Athena MCP) run in containers with persistent volumes.

### What You Get

```
├── Athena MCP Server (8,000)       - 27 tools, 300+ operations
├── PostgreSQL 18 + pgvector (5432) - 8-layer memory storage
├── Ollama (11,434)                 - Local embeddings & LLM
├── Redis (6,379)                   - Optional caching
└── PgAdmin (5,050)                 - Database browser (optional)
```

---

## Prerequisites

### System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| RAM | 4GB | 8GB+ |
| CPU | 2 cores | 8+ cores |
| Disk | 2GB | 10GB+ |
| Docker | 20.10+ | Latest |
| Docker Compose | 1.29+ | 2.0+ |

### Software Prerequisites

**Required:**
- Docker Desktop or Docker Engine 20.10+
- Docker Compose 1.29+
- Git (for cloning repository)

**Optional:**
- `curl` (for health checks)
- Text editor (for .env customization)

### Installation

**macOS (Intel/Apple Silicon):**
```bash
# Install Docker Desktop
brew install --cask docker

# Or visit: https://www.docker.com/products/docker-desktop
```

**Linux (Ubuntu/Debian):**
```bash
# Install Docker
sudo apt-get update
sudo apt-get install -y docker.io docker-compose

# Add user to docker group (avoid sudo)
sudo usermod -aG docker $USER
newgrp docker
```

**Windows:**
- Download Docker Desktop from https://www.docker.com/products/docker-desktop
- Enable WSL 2 backend for best performance
- Allocate adequate RAM/CPU in Docker settings

**Verify Installation:**
```bash
docker --version
docker-compose --version
docker ps  # Should show no containers
```

---

## Quick Start (5 Minutes)

### 1. Clone and Navigate

```bash
git clone https://github.com/anthropics/athena.git
cd athena
```

### 2. Create Environment

```bash
# Copy example configuration
cp .env.example .env

# Create data directories
mkdir -p ~/.athena/{models,logs}
mkdir -p ~/.ollama
```

### 3. Start Services

```bash
# Make script executable
chmod +x docker-up.sh

# Start all services
./docker-up.sh

# Or use docker-compose directly
docker-compose up -d
```

### 4. Verify Deployment

```bash
# Check service status
./docker-up.sh status

# Check health
./docker-up.sh health

# Or manually check
curl http://localhost:8000/health
```

### 5. Access Services

- **Athena MCP**: http://localhost:8000
- **Metrics**: http://localhost:9000
- **PostgreSQL**: `localhost:5432`
- **Ollama**: http://localhost:11434

### 6. Run Tests

```bash
# In container
docker-compose exec athena pytest tests/mcp/ -v

# Or from host
docker-compose exec athena python -m pytest tests/ -v
```

---

## Detailed Setup

### Step 1: Clone Repository

```bash
git clone https://github.com/anthropics/athena.git
cd athena
```

### Step 2: Configure Environment

Copy the example .env file:
```bash
cp .env.example .env
```

Review and adjust `.env` as needed:

```bash
# Edit with your preferred editor
nano .env
# or
vim .env
```

**Key Settings to Review:**
- `POSTGRES_PASSWORD` - Change for production!
- `OLLAMA_NUM_THREAD` - Adjust to your CPU cores
- `EMBEDDING_PROVIDER` - Keep as `ollama` for local-only
- `CACHE_SIZE_MB` - Adjust based on available RAM
- `ENVIRONMENT` - Set to `development` or `production`

### Step 3: Create Data Directories

```bash
# Create directories for persistent data
mkdir -p ~/.athena/models      # LLM model storage
mkdir -p ~/.athena/logs        # Application logs
mkdir -p ~/.ollama             # Ollama cache
```

### Step 4: Start Services

**Option A: Using Quick Start Script (Recommended)**

```bash
chmod +x docker-up.sh

# Production mode
./docker-up.sh

# Development mode (with hot-reload)
./docker-up.sh dev

# Debug mode (with pgAdmin, dev-tools)
./docker-up.sh debug

# View logs
./docker-up.sh logs

# Stop services
./docker-up.sh down
```

**Option B: Using Docker Compose Directly**

```bash
# Start services in background
docker-compose up -d

# Start with development config
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Step 5: Wait for Services to Start

Services have health checks. First startup takes 30-60 seconds:

```bash
# Watch service startup
docker-compose logs -f

# Expected sequence:
# 1. PostgreSQL - ready in 10-15 seconds
# 2. Ollama - starts immediately, downloads models on first use
# 3. Athena MCP - starts when PostgreSQL is ready
```

### Step 6: Verify Deployment

**Check Service Status:**
```bash
./docker-up.sh status
# or
docker-compose ps
```

Expected output:
```
NAME                COMMAND             SERVICE             STATUS
athena-mcp          python -m athena... athena              Up 2m (healthy)
athena-postgres     postgres            postgres            Up 2m (healthy)
athena-ollama       ollama serve        ollama              Up 2m (healthy)
```

**Test Endpoints:**
```bash
# Athena health check
curl http://localhost:8000/health

# Expected response:
# {"status": "healthy", "timestamp": "...", "components": {...}}

# Ollama health check
curl http://localhost:11434/api/tags

# PostgreSQL connection
psql -h localhost -U athena -d athena -c "SELECT 1"
# Enter password: athena_dev
```

---

## Configuration

### Environment Variables

See `.env.example` for complete list. Key categories:

**Database:**
```bash
POSTGRES_DB=athena              # Database name
POSTGRES_USER=athena            # Database user
POSTGRES_PASSWORD=athena_dev    # Change for production!
POSTGRES_PORT=5432
```

**Embeddings:**
```bash
EMBEDDING_PROVIDER=ollama       # or 'anthropic', 'mock'
OLLAMA_HOST=http://ollama:11434 # Ollama server URL
OLLAMA_NUM_THREAD=8             # CPU threads
```

**Performance:**
```bash
CONSOLIDATION_BATCH_SIZE=1000   # Events per batch
CACHE_SIZE_MB=512               # Vector cache size
MAX_WORKERS=4                   # Async worker threads
```

**Logging:**
```bash
LOG_LEVEL=INFO                  # DEBUG, INFO, WARNING, ERROR
LOG_FILE=/var/log/athena/athena.log
DEBUG=0                         # Set to 1 for verbose output
```

### Profiles

Use Docker Compose profiles to enable optional services:

```bash
# Production (default)
docker-compose up -d

# Development with hot-reload + debug tools
docker-compose --profile debug -f docker-compose.yml -f docker-compose.dev.yml up -d

# Full stack with Redis caching
docker-compose --profile full up -d

# Debug mode (pgAdmin + dev-tools)
docker-compose --profile debug up -d
```

**Available Profiles:**
- `default` - Production (Athena + PostgreSQL + Ollama)
- `full` - Add Redis caching
- `debug` - Add PgAdmin + development tools

---

## Service Details

### PostgreSQL 18 + pgvector

**Container Name:** `athena-postgres`
**Port:** 5432
**Volumes:** `postgres_data:/var/lib/postgresql/data`

Features:
- pgvector extension for vector similarity search
- Pre-configured with optimal settings
- Auto-initialization with schema

**Connect:**
```bash
# From host
psql -h localhost -U athena -d athena

# From container
docker-compose exec postgres psql -U athena -d athena
```

### Ollama

**Container Name:** `athena-ollama`
**Port:** 11434
**Volumes:** `ollama_data:/root/.ollama`, `~/.athena/models:/root/.ollama/models`

**First Run:**
On first startup, Ollama will pull default models. This can take 5-10 minutes depending on your connection.

**Pre-load Models:**
```bash
# Before starting Athena (optional)
ollama pull nomic-embed-text    # Embedding model
ollama pull mistral:7b          # Chat model
ollama pull neural-chat         # Alternative chat model

# Or let Docker handle it
docker-compose exec ollama ollama pull nomic-embed-text
```

**Available Models:**
- `nomic-embed-text` - Text embeddings (4.1GB)
- `mistral` - Chat model (4.1GB)
- `neural-chat` - Smaller chat model (2.2GB)
- `llama2` - Meta's LLaMA 2 (7GB)

### Athena MCP Server

**Container Name:** `athena-mcp`
**Port:** 8000 (API)
**Port:** 9000 (Prometheus metrics)

**Volumes:**
- `/app` - Application code
- `~/.athena` - Persistent data
- `/var/log/athena` - Application logs

**Commands:**
```bash
# View logs
docker-compose logs -f athena

# Execute commands in container
docker-compose exec athena python -c "import athena; print('OK')"

# Run tests
docker-compose exec athena pytest tests/ -v

# Interactive shell
docker-compose exec athena bash
```

### Redis (Optional)

**Container Name:** `athena-redis`
**Port:** 6379
**Enable with:** `docker-compose --profile full up`

Used for optional caching layer. Not required for basic operation.

### PgAdmin (Optional)

**Container Name:** `athena-pgadmin`
**URL:** http://localhost:5050
**Enable with:** `docker-compose --profile debug up`

Database GUI for visualization and management.

**Default Credentials:**
- Email: admin@athena.local
- Password: athena

---

## Common Operations

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f athena
docker-compose logs -f postgres
docker-compose logs -f ollama

# Last N lines
docker-compose logs --tail=100 athena

# Timestamps
docker-compose logs -f --timestamps athena
```

### Check Health

```bash
# Quick health check
./docker-up.sh health

# Detailed Athena health
curl -s http://localhost:8000/health | jq .

# Database health
docker-compose exec postgres pg_isready -U athena

# Ollama health
curl http://localhost:11434/api/tags
```

### Run Tests

```bash
# All tests
docker-compose exec athena pytest tests/ -v

# Specific test file
docker-compose exec athena pytest tests/mcp/test_handlers_integration.py -v

# With coverage
docker-compose exec athena pytest tests/ --cov=src/athena --cov-report=html

# Specific test
docker-compose exec athena pytest tests/unit/test_episodic_store.py::TestEpisodicStore::test_store_event -v
```

### Database Queries

```bash
# Interactive SQL
docker-compose exec postgres psql -U athena -d athena

# Execute SQL file
docker-compose exec postgres psql -U athena -d athena < backup.sql

# Query from host
psql -h localhost -U athena -d athena << 'EOF'
SELECT * FROM episodic_events LIMIT 5;
EOF
```

### Backup and Restore

```bash
# Backup PostgreSQL
docker-compose exec postgres pg_dump -U athena athena | gzip > backup.sql.gz

# Restore from backup
gunzip < backup.sql.gz | docker-compose exec -T postgres psql -U athena athena

# Backup volume data
docker run --rm -v postgres_data:/data -v $(pwd):/backup \
  ubuntu tar czf /backup/postgres_backup.tar.gz -C /data .
```

### Performance Monitoring

```bash
# CPU and memory usage
docker stats

# Network traffic
docker-compose logs --follow

# Prometheus metrics
curl http://localhost:9000/metrics

# Database size
docker-compose exec postgres psql -U athena -d athena -c \
  "SELECT pg_size_pretty(pg_database_size('athena'))"
```

---

## Troubleshooting

### Services Won't Start

**Symptom:** Containers exit immediately or hang

**Solutions:**
```bash
# 1. Check logs
docker-compose logs

# 2. Remove and retry
docker-compose down -v
docker-compose up -d

# 3. Check Docker resources
docker stats

# 4. Verify ports aren't in use
lsof -i :8000  # Athena
lsof -i :5432  # PostgreSQL
lsof -i :11434 # Ollama
```

### PostgreSQL Connection Issues

**Symptom:** "connection refused" or "role does not exist"

**Solutions:**
```bash
# 1. Check if container is running
docker-compose ps postgres

# 2. Check container logs
docker-compose logs postgres

# 3. Verify credentials in .env
grep POSTGRES .env

# 4. Wait longer (first startup takes 30+ seconds)
sleep 30
docker-compose logs postgres

# 5. Reinitialize
docker-compose down -v postgres
docker-compose up postgres
```

### Ollama Model Download Hangs

**Symptom:** Ollama container starts but doesn't respond

**Solutions:**
```bash
# 1. Check download progress
docker-compose logs ollama

# 2. Give it time (first pull can take 10+ minutes)
sleep 600  # Wait 10 minutes
curl http://localhost:11434/api/tags

# 3. Pre-download models
ollama pull nomic-embed-text  # Run on host

# 4. Configure firewall
# Ensure port 11434 is accessible
```

### Athena Server Crashes

**Symptom:** Container exits or keeps restarting

**Solutions:**
```bash
# 1. Check logs
docker-compose logs athena

# 2. Verify PostgreSQL is ready
docker-compose logs postgres | grep "ready to accept"

# 3. Verify Ollama is responding
curl http://localhost:11434/api/tags

# 4. Increase startup timeout
# Edit docker-compose.yml: start_period: 60s

# 5. Check memory
docker stats athena
```

### High Memory Usage

**Symptom:** Container memory exceeds available RAM

**Solutions:**
```bash
# 1. Reduce cache size
# In .env: CACHE_SIZE_MB=256

# 2. Reduce worker threads
# In .env: MAX_WORKERS=2

# 3. Monitor memory
docker stats

# 4. Reduce batch size
# In .env: CONSOLIDATION_BATCH_SIZE=500
```

### Slow Performance

**Symptom:** High latency for queries/operations

**Solutions:**
```bash
# 1. Check service resources
docker stats

# 2. Check database queries
docker-compose exec postgres psql -U athena -d athena \
  -c "SELECT query, calls, total_time FROM pg_stat_statements ORDER BY total_time DESC LIMIT 5"

# 3. Increase allocated resources
# Docker Desktop → Preferences → Resources → increase CPU/RAM

# 4. Check network connectivity
docker network inspect athena-network

# 5. Optimize cache settings
# Increase CACHE_SIZE_MB and MAX_WORKERS in .env
```

### Port Already in Use

**Symptom:** "port is already allocated" error

**Solutions:**
```bash
# 1. Find what's using the port
lsof -i :8000   # Athena port
lsof -i :5432   # PostgreSQL port
lsof -i :11434  # Ollama port

# 2. Change ports in .env
ATHENA_PORT=8001
POSTGRES_PORT=5433
OLLAMA_PORT=11435

# 3. Stop conflicting service
# Use system tools to stop process using the port

# 4. Use different port
docker-compose -f docker-compose.yml -e "ATHENA_PORT=8001" up -d
```

### Database Schema Not Created

**Symptom:** "relation does not exist" errors

**Solutions:**
```bash
# 1. Check if init script ran
docker-compose logs postgres | grep "01-init.sql"

# 2. Reinitialize database
docker-compose down -v
docker-compose up postgres

# 3. Manual schema creation
docker-compose exec postgres psql -U athena -d athena < scripts/init_postgres.sql

# 4. Verify schema
docker-compose exec postgres psql -U athena -d athena -c "\dt"
```

---

## Production Deployment

### Security Checklist

- [ ] Change `POSTGRES_PASSWORD` to strong password
- [ ] Set `ENVIRONMENT=production`
- [ ] Set `DEBUG=0`
- [ ] Enable SSL for PostgreSQL (if exposed)
- [ ] Use secrets management (AWS Secrets Manager, etc.)
- [ ] Enable audit logging
- [ ] Configure backups
- [ ] Set up monitoring and alerting

### Performance Optimization

```bash
# In .env:
ENVIRONMENT=production
DEBUG=0
LOG_LEVEL=WARNING  # Less logging = faster

# Increase resources
CONSOLIDATION_BATCH_SIZE=2000
CACHE_SIZE_MB=2048
MAX_WORKERS=8
ATHENA_POSTGRES_MAX_SIZE=50

# PostgreSQL tuning
POSTGRES_INITDB_ARGS="-c shared_buffers=1GB -c effective_cache_size=4GB"
```

### Scaling

```bash
# Horizontal scaling (multiple Athena instances)
docker-compose up -d --scale athena=3

# Load balancing with reverse proxy (Nginx example)
# Configure Nginx to route to localhost:8000

# Separate database server
# Set ATHENA_POSTGRES_HOST=external-postgres-server
```

### Backup Strategy

```bash
# Daily backups
0 2 * * * docker-compose exec postgres pg_dump -U athena athena | gzip > ~/backups/athena-$(date +\%Y\%m\%d).sql.gz

# Upload to S3
aws s3 cp ~/backups/athena-latest.sql.gz s3://my-backups/athena/

# Test restore monthly
gunzip < ~/backups/athena-latest.sql.gz | psql -h localhost -U athena athena
```

---

## Maintenance

### Daily

```bash
# Check health
./docker-up.sh health

# Monitor logs
docker-compose logs --tail=100

# Database optimization (if needed)
docker-compose exec postgres psql -U athena -d athena -c "VACUUM ANALYZE;"
```

### Weekly

```bash
# Full test suite
docker-compose exec athena pytest tests/ -v

# Database maintenance
docker-compose exec postgres psql -U athena -d athena << 'EOF'
VACUUM ANALYZE;
REINDEX DATABASE athena;
EOF

# Backup database
docker-compose exec postgres pg_dump -U athena athena | gzip > backup-weekly.sql.gz
```

### Monthly

```bash
# Update Docker images
docker-compose pull
docker-compose up -d

# Review logs and metrics
docker-compose logs --tail=1000 | grep ERROR

# Clean up unused volumes
docker volume prune

# Update Ollama models
docker-compose exec ollama ollama pull --latest nomic-embed-text
```

---

## Advanced Topics

### Custom Dockerfile Build

To build a custom Docker image with your changes:

```bash
# Build image
docker build -f docker/Dockerfile -t athena:custom .

# Run custom image
docker run -d \
  --name athena-custom \
  --network athena-network \
  -e ATHENA_POSTGRES_HOST=postgres \
  -e EMBEDDING_PROVIDER=ollama \
  athena:custom
```

### Docker Swarm Deployment

For multi-host production deployment:

```bash
# Initialize swarm
docker swarm init

# Deploy with stack
docker stack deploy -c docker-compose.yml athena

# Scale service
docker service scale athena_athena=3

# Check status
docker service ls
docker service ps athena_athena
```

### Kubernetes Deployment

For Kubernetes clusters:

```bash
# Convert docker-compose to Kubernetes manifests
kompose convert -f docker-compose.yml -o k8s/

# Deploy to Kubernetes
kubectl apply -f k8s/

# Scale deployment
kubectl scale deployment athena --replicas=3

# View logs
kubectl logs deployment/athena
```

### Environment-Specific Configs

```bash
# Create environment-specific compose files
docker-compose.prod.yml
docker-compose.staging.yml

# Use with override
docker-compose -f docker-compose.yml \
  -f docker-compose.prod.yml \
  up -d
```

---

## Support & Resources

### Documentation

- **Main README**: `/README.md` - Project overview
- **Architecture Guide**: `/ARCHITECTURE.md` - System design
- **Development Guide**: `/CLAUDE.md` - Development instructions
- **API Reference**: `/API_REFERENCE.md` - Complete tool documentation
- **Deployment Guide**: `/DEPLOYMENT.md` - Full deployment reference

### Troubleshooting Resources

1. Check logs: `docker-compose logs -f`
2. Review `.env` configuration
3. Verify Docker is running: `docker ps`
4. Check system resources: `docker stats`
5. Test endpoints: `curl http://localhost:8000/health`

### Getting Help

If you encounter issues:

1. **Check logs first**: `docker-compose logs | head -100`
2. **Verify prerequisites**: Docker, Docker Compose version
3. **Test each service**: PostgreSQL, Ollama, Athena
4. **Review configuration**: `.env` settings
5. **Check ports**: `lsof -i :8000` (no conflicts)

### Community & Support

- GitHub Issues: https://github.com/anthropics/athena/issues
- Documentation: https://docs.claude.com
- Discord Community: [Link if available]

---

## Next Steps

After successful deployment:

1. **Run Tests**: `./docker-up.sh` → `docker-compose exec athena pytest tests/mcp/ -v`
2. **Explore API**: Visit http://localhost:8000 for interactive documentation
3. **Review Logs**: `docker-compose logs -f` to understand system behavior
4. **Set Up Monitoring**: Configure Prometheus/Grafana for production
5. **Schedule Backups**: Set up automated PostgreSQL backups
6. **Customize Configuration**: Adjust `.env` for your use case

---

## Quick Reference

### Quick Start Commands

```bash
# First time setup
git clone https://github.com/anthropics/athena.git && cd athena
cp .env.example .env
mkdir -p ~/.athena/{models,logs}
./docker-up.sh

# Daily usage
./docker-up.sh              # Start
./docker-up.sh logs         # View logs
./docker-up.sh health       # Check health
./docker-up.sh down         # Stop

# Development
./docker-up.sh dev          # With hot-reload
docker-compose exec athena pytest tests/ -v

# Debugging
./docker-up.sh debug        # With pgAdmin
curl http://localhost:5050  # pgAdmin UI
```

### Important Files

- `.env` - Configuration (create from .env.example)
- `docker-compose.yml` - Service definitions
- `docker-compose.dev.yml` - Development overrides
- `docker/Dockerfile` - Athena image definition
- `scripts/init_postgres.sql` - Database schema initialization

### Key Ports

| Service | Port | URL |
|---------|------|-----|
| Athena API | 8000 | http://localhost:8000 |
| Metrics | 9000 | http://localhost:9000 |
| PostgreSQL | 5432 | localhost:5432 |
| Ollama | 11434 | http://localhost:11434 |
| Redis | 6379 | localhost:6379 |
| PgAdmin | 5050 | http://localhost:5050 |

---

**Last Updated**: November 10, 2025
**Version**: 1.0 (Production Ready)
**Maintainer**: Athena Development Team
