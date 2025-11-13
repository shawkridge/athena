# Athena Environment Configuration Guide

**Version**: 1.0
**Status**: Production Ready
**Last Updated**: November 10, 2025

## Overview

This guide covers configuring Athena for development, testing, and production environments.

## Quick Start

### Development (SQLite)
```bash
# No configuration needed - uses local SQLite by default
pip install -e .
pytest tests/mcp/ -v
```

### Production (PostgreSQL)
```bash
# Start PostgreSQL
docker-compose up -d postgres

# Set environment variables
export ATHENA_POSTGRES_HOST=localhost
export ATHENA_POSTGRES_PORT=5432
export ATHENA_POSTGRES_DB=athena
export ATHENA_POSTGRES_USER=athena
export ATHENA_POSTGRES_PASSWORD=your_secure_password

# Run application
python -m athena.mcp
```

---

## Environment Variables

### Database Configuration

#### SQLite (Development Default)
```bash
# Optional - SQLite database path
ATHENA_DB_PATH=~/.athena/memory.db

# Optional - Create path if not exists
ATHENA_DB_CREATE_PATH=true
```

#### PostgreSQL (Production)
```bash
# PostgreSQL Connection
ATHENA_POSTGRES_HOST=localhost
ATHENA_POSTGRES_PORT=5432
ATHENA_POSTGRES_DB=athena
ATHENA_POSTGRES_USER=athena
ATHENA_POSTGRES_PASSWORD=secure_password

# Connection Pool Settings (optional)
ATHENA_POSTGRES_MIN_SIZE=2
ATHENA_POSTGRES_MAX_SIZE=10
ATHENA_POSTGRES_POOL_TIMEOUT=30
ATHENA_POSTGRES_MAX_IDLE=300
ATHENA_POSTGRES_MAX_LIFETIME=3600
```

### Embedding Configuration

```bash
# Embedding Provider: "ollama" (local) or "anthropic" (API-based)
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=nomic-embed-text

# Ollama Settings
OLLAMA_HOST=http://localhost:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
OLLAMA_LLM_MODEL=qwen2.5:latest

# Anthropic API Settings (if using Anthropic)
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_EMBEDDING_MODEL=text-embedding-3-large
```

### Vector Database Configuration

```bash
# Qdrant Vector Database (optional)
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=athena_memories
QDRANT_EMBEDDING_DIM=768

# Or use PostgreSQL with pgvector (recommended for production)
USE_PGVECTOR=true
```

### System Configuration

```bash
# Debug Logging
DEBUG=0  # Set to 1 for verbose logging

# Performance
MAX_WORKERS=4
BATCH_SIZE=32
CONSOLIDATION_THRESHOLD=1000

# Security
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=100
AUDIT_LOGGING_ENABLED=true

# Directories
ATHENA_HOME=~/.athena
ATHENA_MODELS_DIR=~/.athena/models
ATHENA_LOGS_DIR=~/.athena/logs
```

---

## Configuration Files

### 1. `.env` File (Project Root)

Create a `.env` file for local development:

```bash
# Database
ATHENA_POSTGRES_HOST=localhost
ATHENA_POSTGRES_PORT=5432
ATHENA_POSTGRES_DB=athena
ATHENA_POSTGRES_USER=athena
ATHENA_POSTGRES_PASSWORD=athena_dev

# Embedding
EMBEDDING_PROVIDER=ollama
OLLAMA_HOST=http://localhost:11434

# Debug
DEBUG=0
```

Load it with:
```bash
source .env
```

Or use python-dotenv:
```python
from dotenv import load_dotenv
load_dotenv()
```

### 2. `~/.athena/config.json` (User Config)

Create user-level configuration:

```json
{
  "database": {
    "type": "postgres",
    "host": "localhost",
    "port": 5432,
    "name": "athena",
    "user": "athena",
    "password": "secure_password"
  },
  "embedding": {
    "provider": "ollama",
    "model": "nomic-embed-text",
    "host": "http://localhost:11434"
  },
  "system": {
    "debug": false,
    "log_level": "INFO",
    "max_workers": 4
  }
}
```

---

## Docker Deployment

### Using docker-compose (Recommended)

Start all services:
```bash
docker-compose up -d
```

Services started:
- **postgres**: PostgreSQL 18 with pgvector
- **llamacpp**: Local embeddings & LLM
- **redis**: Caching layer
- **pgadmin**: Database browser (optional)

### View Logs
```bash
docker-compose logs -f postgres
docker-compose logs -f llamacpp
```

### Stop Services
```bash
docker-compose down
```

### Persistent Data
Docker volumes are created for:
- `postgres_data`: Database persistence
- `pgadmin_data`: pgAdmin configuration

---

## Production Configuration

### 1. PostgreSQL Setup

Use a managed PostgreSQL service or deploy with:
```bash
# Docker production setup
docker run -d \
  --name athena-postgres \
  -e POSTGRES_DB=athena \
  -e POSTGRES_USER=athena \
  -e POSTGRES_PASSWORD=$(openssl rand -base64 32) \
  -v postgres_data:/var/lib/postgresql/data \
  -p 5432:5432 \
  pgvector/pgvector:0.8.1-pg18-trixie
```

### 2. Connection Pooling

For production, use connection pooling:

```bash
# PgBouncer configuration
export ATHENA_POSTGRES_MIN_SIZE=5
export ATHENA_POSTGRES_MAX_SIZE=20
export ATHENA_POSTGRES_POOL_TIMEOUT=30
```

### 3. Embeddings

For production, either:

**Option A: Local (Recommended)**
```bash
# Pull models
ollama pull nomic-embed-text
ollama pull qwen2.5:latest

# Run ollama
docker run -d \
  --name athena-ollama \
  -v ~/.ollama:/root/.ollama \
  -p 11434:11434 \
  ollama/ollama:latest
```

**Option B: Anthropic API**
```bash
export EMBEDDING_PROVIDER=anthropic
export ANTHROPIC_API_KEY=sk-ant-...
```

### 4. Security

```bash
# Enable all security features
export RATE_LIMIT_ENABLED=true
export AUDIT_LOGGING_ENABLED=true
export DEBUG=0

# Use strong passwords
export ATHENA_POSTGRES_PASSWORD=$(openssl rand -base64 32)

# Enable HTTPS (with reverse proxy like nginx)
# See DEPLOYMENT.md for full setup
```

### 5. Monitoring

```bash
# Enable comprehensive logging
export LOG_LEVEL=INFO
export AUDIT_LOGGING_ENABLED=true
export MONITORING_ENABLED=true

# View health status
curl http://localhost:3000/health
```

---

## Environment Presets

### Development
```bash
export ENVIRONMENT=development
export DEBUG=1
export LOG_LEVEL=DEBUG
export ATHENA_DB_PATH=~/.athena/memory.db
export EMBEDDING_PROVIDER=ollama
```

### Testing
```bash
export ENVIRONMENT=test
export DEBUG=0
export ATHENA_DB_PATH=:memory:  # In-memory SQLite
export EMBEDDING_PROVIDER=mock
```

### Staging
```bash
export ENVIRONMENT=staging
export DEBUG=0
export LOG_LEVEL=INFO
# Use PostgreSQL
export ATHENA_POSTGRES_HOST=staging-db.example.com
```

### Production
```bash
export ENVIRONMENT=production
export DEBUG=0
export LOG_LEVEL=WARNING
# Use PostgreSQL
export ATHENA_POSTGRES_HOST=prod-db.example.com
export ATHENA_POSTGRES_PASSWORD=$(aws secretsmanager get-secret-value ...)
```

---

## Verification

### Check Configuration
```bash
# Test database connection
python -c "from src.athena.core.database_factory import get_database; db = get_database(); print('✓ Database OK')"

# Test embeddings
python -c "from src.athena.core.embeddings import EmbeddingModel; e = EmbeddingModel(); print('✓ Embeddings OK')"

# Get system status
curl http://localhost:3000/health
```

### Run Tests
```bash
# Development tests
pytest tests/unit/ tests/integration/ -v

# Production validation
pytest tests/mcp/ -v --timeout=300
```

---

## Common Issues

### PostgreSQL Connection Failed
```
Error: could not connect to server
Solution:
1. Check PostgreSQL is running: docker-compose ps
2. Verify credentials: echo $ATHENA_POSTGRES_PASSWORD
3. Check network: docker network ls
4. Use docker logs: docker-compose logs postgres
```

### Ollama Model Not Found
```
Error: model "nomic-embed-text" not found
Solution:
1. Pull model: ollama pull nomic-embed-text
2. Verify: curl http://localhost:11434/api/tags
3. Check OLLAMA_HOST: echo $OLLAMA_HOST
```

### Memory Database Initialization
```
Error: no such table: memories
Solution:
1. This is normal on first run
2. Tables are auto-created on first use
3. Verify with: sqlite3 ~/.athena/memory.db ".tables"
```

### Rate Limiting Issues
```
Error: Rate limit exceeded
Solution:
1. Check RATE_LIMIT_PER_MINUTE setting
2. Increase for development: export RATE_LIMIT_PER_MINUTE=1000
3. Use batch operations for bulk inserts
```

---

## Best Practices

1. **Development**: Use SQLite with auto-creation enabled
2. **Testing**: Use in-memory SQLite for speed
3. **Staging**: Use PostgreSQL with same schema as production
4. **Production**: Use managed PostgreSQL + Ollama + monitoring

2. **Security**:
   - Never commit `.env` files with secrets
   - Use AWS Secrets Manager for production
   - Rotate passwords regularly
   - Enable audit logging

3. **Performance**:
   - Use connection pooling in production
   - Enable consolidation scheduling
   - Monitor memory usage
   - Use batch operations

4. **Monitoring**:
   - Check health endpoint regularly
   - Monitor database size growth
   - Track API request rates
   - Alert on consolidation failures

---

## Next Steps

1. Review DEPLOYMENT.md for production setup
2. Check TROUBLESHOOTING.md for common issues
3. Run TEST_EXECUTION.md to verify setup
4. See API_REFERENCE.md for available operations

---

**Maintainer**: Athena Development Team
**Support**: See TROUBLESHOOTING.md
