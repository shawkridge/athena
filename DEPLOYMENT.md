# Athena Deployment Guide

**Version**: 1.0
**Status**: Production Ready
**Last Updated**: November 10, 2025

## Overview

Complete deployment guide for Athena in development, staging, and production environments.

## Quick Start

### Local Development (5 minutes)
```bash
# 1. Clone and install
git clone <repo>
cd athena
pip install -e .

# 2. Run tests (optional)
pytest tests/mcp/ -v

# 3. Start using
python
>>> from src.athena.mcp.handlers import MemoryMCPServer
>>> server = MemoryMCPServer()
```

### Docker Compose (10 minutes)
```bash
# 1. Start services
docker-compose up -d

# 2. Verify services running
docker-compose ps

# 3. Check health
curl http://localhost:5432  # PostgreSQL
curl http://localhost:11434/api/tags  # Ollama
```

---

## Architecture

```
┌─────────────────────────────────────────┐
│         Athena MCP Server               │
│  (27 tools, 300+ operations)            │
└─────────────────────────────────────────┘
                 ↓
    ┌────────────┬────────────┐
    ↓            ↓            ↓
┌─────────┐  ┌────────┐  ┌─────────┐
│ Memory  │  │Semantic│  │Knowledge│
│ Store   │  │ Search │  │ Graph   │
└─────────┘  └────────┘  └─────────┘
    ↓            ↓            ↓
┌──────────────────────────────────────┐
│    PostgreSQL + pgvector             │
│    (8 memory layers + vector DB)     │
└──────────────────────────────────────┘
```

---

## Environment Setup

### Prerequisites

- Python 3.10+ (tested with 3.13)
- PostgreSQL 14+ (or SQLite for dev)
- Docker & Docker Compose (recommended)
- 4GB RAM minimum (8GB recommended)
- Disk space: 2GB for models + data

### Installation

```bash
# 1. Install Python dependencies
pip install -e ".[dev]"

# Optional: Install GPU support
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# 2. Create directories
mkdir -p ~/.athena/models ~/.athena/logs

# 3. Verify installation
python -c "import athena; print('✓ Athena installed')"
```

---

## Development Environment

### Setup

```bash
# 1. Create .env file
cat > .env << 'EOF'
ENVIRONMENT=development
DEBUG=1
ATHENA_DB_PATH=~/.athena/memory.db
EMBEDDING_PROVIDER=ollama
OLLAMA_HOST=http://localhost:11434
EOF

# 2. Load environment
source .env

# 3. Initialize database (auto-creates tables)
pytest tests/mcp/test_handlers_integration.py::TestRememberOperation::test_remember_fact_memory -v
```

### Running Tests

```bash
# Quick tests (unit + integration)
pytest tests/unit/ tests/integration/ -v -m "not benchmark"

# Full test suite
pytest tests/ -v --timeout=300

# MCP integration tests (55 tests, 100% pass rate)
pytest tests/mcp/test_handlers_integration.py -v
```

### Using in Development

```python
# Start server
from src.athena.mcp.handlers import MemoryMCPServer

server = MemoryMCPServer(enable_advanced_rag=False)

# Use operations
result = await server._handle_remember({
    "project_id": "1",
    "content": "Python is awesome",
    "memory_type": "fact"
})
```

---

## Docker Deployment

### Docker Compose (All-in-one)

```bash
# Start all services
docker-compose up -d

# Verify
docker-compose ps
docker-compose logs -f postgres

# Stop
docker-compose down
```

**Services Included:**
- PostgreSQL 18 + pgvector
- Ollama (embeddings + LLM)
- Redis (caching)
- pgAdmin (database UI - optional)

### Docker Build

```bash
# Build custom image
docker build -f docker/Dockerfile -t athena:latest .

# Run container
docker run -d \
  --name athena \
  -e ATHENA_POSTGRES_HOST=postgres \
  -e EMBEDDING_PROVIDER=ollama \
  -v ~/.athena:/root/.athena \
  --network athena-network \
  athena:latest
```

---

## PostgreSQL Deployment

### Managed Service (AWS RDS, Azure, GCP)

```bash
# 1. Create PostgreSQL instance
# - Engine: PostgreSQL 15+
# - Extensions: pgvector
# - Storage: 100GB (adjust based on load)

# 2. Create database
psql -h your-instance.rds.amazonaws.com -U postgres << 'EOF'
CREATE DATABASE athena;
CREATE EXTENSION IF NOT EXISTS pgvector;
GRANT ALL PRIVILEGES ON DATABASE athena TO athena_user;
EOF

# 3. Set environment variables
export ATHENA_POSTGRES_HOST=your-instance.rds.amazonaws.com
export ATHENA_POSTGRES_PORT=5432
export ATHENA_POSTGRES_DB=athena
export ATHENA_POSTGRES_USER=athena_user
export ATHENA_POSTGRES_PASSWORD=$(aws secretsmanager ...)
```

### Self-Hosted PostgreSQL

```bash
# Option 1: Docker
docker run -d \
  --name athena-postgres \
  -e POSTGRES_DB=athena \
  -e POSTGRES_USER=athena \
  -e POSTGRES_PASSWORD=$(openssl rand -base64 32) \
  -v postgres_data:/var/lib/postgresql/data \
  -p 5432:5432 \
  pgvector/pgvector:0.8.1-pg18-trixie

# Option 2: Kubernetes
kubectl apply -f k8s/postgres-deployment.yaml

# Option 3: System package
sudo apt-get install postgresql postgresql-contrib
sudo -u postgres psql << 'EOF'
CREATE DATABASE athena;
CREATE EXTENSION pgvector;
CREATE USER athena WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE athena TO athena;
EOF
```

---

## Embedding Service Deployment

### Option A: Ollama (Recommended)

```bash
# Docker
docker run -d \
  --name athena-ollama \
  -v ~/.ollama:/root/.ollama \
  -p 11434:11434 \
  ollama/ollama:latest

# Pull models
ollama pull nomic-embed-text
ollama pull qwen2.5:latest

# Verify
curl http://localhost:11434/api/tags
```

### Option B: Anthropic API

```bash
# Set environment
export EMBEDDING_PROVIDER=anthropic
export ANTHROPIC_API_KEY=sk-ant-...

# Cost: ~$0.02 per 1M tokens
```

### Option C: LiteLLM (Multi-provider)

```bash
# Configuration
export EMBEDDING_PROVIDER=litellm
export LITELLM_MODEL=ollama/nomic-embed-text

# Supports: Ollama, OpenAI, Anthropic, Cohere, etc.
```

---

## Production Checklist

### Pre-Deployment
- [ ] All 55 tests passing: `pytest tests/mcp/ -v`
- [ ] PostgreSQL database created with pgvector
- [ ] Ollama models pulled (embedding + LLM)
- [ ] Environment variables set for production
- [ ] Secrets stored in AWS Secrets Manager
- [ ] Monitoring/logging configured
- [ ] Backup strategy defined

### Deployment Steps

```bash
# 1. Pull latest code
git pull origin main

# 2. Install dependencies
pip install -e .

# 3. Set production environment
source /etc/athena/production.env

# 4. Run migrations (if needed)
python -m athena.migrations.runner ~/.athena/memory.db

# 5. Start service
systemctl start athena

# 6. Verify
curl http://localhost:3000/health
```

### Post-Deployment
- [ ] Verify all services running
- [ ] Check database connectivity
- [ ] Test API endpoints
- [ ] Monitor logs for errors
- [ ] Set up alerting

---

## Monitoring & Health Checks

### Health Endpoint

```bash
# Check system health
curl http://localhost:3000/health

# Response:
{
  "status": "healthy",
  "timestamp": "2025-11-10T12:00:00Z",
  "components": {
    "database": "healthy",
    "embeddings": "healthy",
    "cache": "healthy"
  },
  "metrics": {
    "memory_usage_mb": 256,
    "active_connections": 5,
    "requests_per_minute": 45
  }
}
```

### Logging

```bash
# View logs
tail -f ~/.athena/logs/athena.log

# Enable debug logging
export DEBUG=1
export LOG_LEVEL=DEBUG

# Log to file
export LOG_FILE=~/.athena/logs/athena.log
```

### Monitoring Stack (Optional)

```bash
# Deploy Prometheus + Grafana
docker-compose -f docker-compose.monitoring.yml up -d

# Metrics exported at:
curl http://localhost:9090/metrics
```

---

## Scaling

### Horizontal Scaling (Multiple Instances)

```yaml
# Kubernetes deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: athena
spec:
  replicas: 3
  selector:
    matchLabels:
      app: athena
  template:
    metadata:
      labels:
        app: athena
    spec:
      containers:
      - name: athena
        image: athena:latest
        env:
        - name: ATHENA_POSTGRES_HOST
          value: postgres.default.svc
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
```

### Vertical Scaling (Single Instance)

```bash
# Increase connection pool
export ATHENA_POSTGRES_MAX_SIZE=50

# Increase cache size
export CACHE_SIZE_MB=2048

# Increase workers
export MAX_WORKERS=8
```

---

## Backup & Recovery

### Database Backup

```bash
# PostgreSQL backup
pg_dump -h $ATHENA_POSTGRES_HOST -U $ATHENA_POSTGRES_USER athena \
  | gzip > ~/backups/athena-$(date +%Y%m%d).sql.gz

# Automated backup (cron)
0 2 * * * pg_dump -h localhost -U athena athena | gzip > ~/backups/athena-$(date +\%Y\%m\%d).sql.gz

# Restore
gunzip < ~/backups/athena-20251110.sql.gz | psql -h localhost -U athena
```

### S3 Backup (AWS)

```bash
# Upload backup
aws s3 cp ~/backups/athena-latest.sql.gz s3://my-backups/athena/

# Restore from S3
aws s3 cp s3://my-backups/athena/athena-latest.sql.gz - | gunzip | psql ...
```

---

## Troubleshooting

### Database Connection Issues
```bash
# Test connection
psql -h $ATHENA_POSTGRES_HOST -U $ATHENA_POSTGRES_USER -d athena -c "SELECT 1"

# Check pool status
curl http://localhost:3000/pool-status

# Increase timeout
export ATHENA_POSTGRES_POOL_TIMEOUT=60
```

### Memory Issues
```bash
# Monitor usage
watch -n1 'free -h'

# Check Athena memory
curl http://localhost:3000/health | jq .metrics.memory_usage_mb

# Reduce cache
export CACHE_SIZE_MB=512
```

### Slow Queries
```bash
# Enable slow query logging
psql ... -c "ALTER SYSTEM SET log_min_duration_statement = 1000;"

# Analyze indexes
ANALYZE;

# Check execution plans
EXPLAIN ANALYZE SELECT ...;
```

---

## Rollback Procedure

```bash
# 1. Stop service
systemctl stop athena

# 2. Checkout previous version
git checkout v1.0.0

# 3. Reinstall
pip install -e .

# 4. Restore database backup (if needed)
gunzip < ~/backups/athena-pre-upgrade.sql.gz | psql ...

# 5. Restart
systemctl start athena

# 6. Verify
curl http://localhost:3000/health
```

---

## Security Hardening

```bash
# 1. Strong database password
export ATHENA_POSTGRES_PASSWORD=$(openssl rand -base64 32)

# 2. Enable SSL
export ATHENA_POSTGRES_SSLMODE=require

# 3. Set restrictive permissions
chmod 600 ~/.athena/config.json
chmod 700 ~/.athena/

# 4. Enable audit logging
export AUDIT_LOGGING_ENABLED=true
export AUDIT_LOG_FILE=~/.athena/logs/audit.log

# 5. Use secrets management
export ATHENA_POSTGRES_PASSWORD=$(aws secretsmanager get-secret-value ...)
```

---

## Performance Tuning

### Database
```bash
# Connection pooling
export ATHENA_POSTGRES_MIN_SIZE=5
export ATHENA_POSTGRES_MAX_SIZE=20

# Query cache
export CACHE_SIZE_MB=2048
export CACHE_TTL_SECONDS=3600

# Index optimization
ANALYZE;
VACUUM ANALYZE;
```

### Application
```bash
# Worker threads
export MAX_WORKERS=8

# Batch operations
export BATCH_SIZE=64

# Consolidation
export CONSOLIDATION_BATCH_SIZE=1000
export CONSOLIDATION_SCHEDULE="0 2 * * *"  # Daily at 2am
```

---

## Maintenance

### Regular Tasks
```bash
# Daily: Check health
curl http://localhost:3000/health

# Weekly: Database maintenance
psql ... << 'EOF'
VACUUM ANALYZE;
REINDEX DATABASE athena;
EOF

# Monthly: Review logs and metrics
tail -100 ~/.athena/logs/athena.log
curl http://localhost:3000/metrics | grep requests_total

# Quarterly: Major version update
git pull origin main
pytest tests/mcp/ -v
```

---

## Support & Escalation

**Level 1**: Review logs and check health endpoint
**Level 2**: Consult TROUBLESHOOTING.md and ENVIRONMENT_CONFIG.md
**Level 3**: Contact support with:
- Output of `curl http://localhost:3000/health`
- Last 100 lines of logs
- Recent changes/deployments
- Environment details

---

**Next Steps:**
1. Start with [Quick Start](#quick-start) section
2. Run [production checklist](#production-checklist)
3. Set up [monitoring](#monitoring--health-checks)
4. Schedule regular [maintenance](#maintenance)

**Maintainer**: Athena Development Team
**Last Updated**: November 10, 2025
