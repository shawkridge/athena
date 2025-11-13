# Configuration Guide

Complete guide to configuring Athena's environment, database, and services.

## Overview

Configuration is managed through a three-tier system:
1. **Environment variables** (highest priority)
2. **Configuration file** (`~/.claude/settings.local.json`)
3. **Hardcoded defaults** (lowest priority)

---

## Database Configuration

### PostgreSQL Connection

Configure your PostgreSQL database connection:

```bash
# Environment variables
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=athena
export DB_USER=postgres
export DB_PASSWORD=postgres
```

**Or** in `.env` file:

```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=athena
DB_USER=postgres
DB_PASSWORD=postgres
```

**Or** in `~/.claude/settings.local.json`:

```json
{
  "database": {
    "host": "localhost",
    "port": 5432,
    "name": "athena",
    "user": "postgres",
    "password": "postgres"
  }
}
```

### Connection Pool Settings

```bash
# Connection pool size
export DB_MIN_POOL_SIZE=2      # Minimum connections
export DB_MAX_POOL_SIZE=10     # Maximum connections

# Timeouts
export DB_CONNECT_TIMEOUT=10   # Connection timeout (seconds)
export DB_QUERY_TIMEOUT=30     # Query timeout (seconds)
```

### Remote Database

```bash
# Example: AWS RDS
export DB_HOST=mydb.abc123.us-east-1.rds.amazonaws.com
export DB_PORT=5432
export DB_NAME=athena
export DB_USER=admin
export DB_PASSWORD=$(aws secretsmanager get-secret-value --secret-id db-password --query SecretString --output text)
```

---

## Embedding Configuration

### Ollama (Local - Recommended)

Free, local embeddings without API keys:

```bash
export EMBEDDING_PROVIDER=ollama
export OLLAMA_HOST=http://localhost:11434

# Download a model
ollama pull nomic-embed-text  # Recommended
# or
ollama pull mxbai-embed-large
```

**In settings.local.json:**

```json
{
  "embeddings": {
    "provider": "ollama",
    "ollama_host": "http://localhost:11434",
    "model": "nomic-embed-text"
  }
}
```

### Anthropic (Cloud)

Use Anthropic's embedding API:

```bash
export EMBEDDING_PROVIDER=anthropic
export ANTHROPIC_API_KEY=sk-ant-v0-xxxxx
```

**In settings.local.json:**

```json
{
  "embeddings": {
    "provider": "anthropic",
    "api_key": "sk-ant-v0-xxxxx",
    "model": "claude-3-5-sonnet"
  }
}
```

### Mock (Testing)

For testing without external dependencies:

```bash
export EMBEDDING_PROVIDER=mock
```

**Dimensions**: 768 (default)
**Speed**: Instant
**Use case**: Testing, development

---

## LLM Configuration

For consolidation and validation (Layer 7):

### Anthropic Claude

```bash
export LLM_PROVIDER=anthropic
export ANTHROPIC_API_KEY=sk-ant-v0-xxxxx
export LLM_MODEL=claude-3-5-sonnet-20241022
```

### Local LLM (via Ollama)

```bash
export LLM_PROVIDER=ollama
export OLLAMA_HOST=http://localhost:11434
export LLM_MODEL=llama2:70b

# Download model
ollama pull llama2:70b
```

---

## Feature Flags

Enable/disable features:

```bash
# Enable debug mode
export DEBUG=1

# Enable RAG features
export ENABLE_RAG=1

# Enable knowledge graph
export ENABLE_GRAPH=1

# Enable consolidation
export ENABLE_CONSOLIDATION=1

# Enable planning features
export ENABLE_PLANNING=1
```

---

## Performance Tuning

### Vector Search Cache

```bash
export CACHE_ENABLED=1
export CACHE_SIZE=1000          # Number of cached searches
export CACHE_TTL=3600           # Time-to-live (seconds)
```

### Batch Operations

```bash
export BATCH_SIZE=100           # Events per batch
export BATCH_TIMEOUT=5          # Timeout between batches (seconds)
```

### Consolidation Parameters

```bash
# Consolidation strategy
export CONSOLIDATION_STRATEGY=balanced  # balanced, speed, quality

# Clustering parameters
export CONSOLIDATION_THRESHOLD=0.5     # Similarity threshold (0-1)
export MIN_CLUSTER_SIZE=2              # Minimum events per cluster

# LLM validation
export VALIDATION_THRESHOLD=0.6        # When to use LLM validation (0-1)
```

---

## Logging Configuration

### Log Level

```bash
export LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

### Log Output

```bash
# Log to file
export LOG_FILE=/var/log/athena/athena.log

# Log to stdout
export LOG_TO_STDOUT=1

# Structured logging (JSON)
export LOG_FORMAT=json
```

### Debug Logging

```bash
# Enable SQL query logging
export LOG_SQL=1

# Log embedding operations
export LOG_EMBEDDINGS=1

# Log all API calls
export LOG_API=1
```

---

## Security Configuration

### API Keys

```bash
# Anthropic API key
export ANTHROPIC_API_KEY=sk-ant-v0-xxxxx

# Other service keys stored securely
export SERVICE_API_KEY=$(aws secretsmanager get-secret-value --secret-id service-key --query SecretString --output text)
```

### Rate Limiting

```bash
export RATE_LIMIT_ENABLED=1
export RATE_LIMIT_REQUESTS_PER_MINUTE=1000
export RATE_LIMIT_SEARCH_PER_MINUTE=100
```

### Data Protection

```bash
# Enable encryption at rest
export ENCRYPTION_ENABLED=1

# Backup location
export BACKUP_PATH=/mnt/backups/athena

# Retention policy
export BACKUP_RETENTION_DAYS=30
```

---

## Integration Configuration

### MCP Server

```bash
# Server host/port
export MCP_HOST=localhost
export MCP_PORT=5000

# Enable authentication
export MCP_AUTH_ENABLED=1
export MCP_AUTH_KEY=your-secret-key
```

### Webhook Configuration

```bash
# Enable webhooks
export WEBHOOKS_ENABLED=1

# Consolidation complete webhook
export WEBHOOK_CONSOLIDATION_COMPLETE=https://your-server.com/webhooks/consolidation

# Error webhook
export WEBHOOK_ERROR=https://your-server.com/webhooks/error
```

---

## Development Configuration

### Testing

```bash
# Use test database
export DB_NAME=athena_test

# Enable test mode
export TEST_MODE=1

# Use mock embeddings
export EMBEDDING_PROVIDER=mock
```

### Development Server

```bash
# Development mode (auto-reload)
export FLASK_ENV=development
export FLASK_DEBUG=1

# Watch mode
export WATCH_MODE=1
```

---

## Environment File Example

Create `.env` in project root:

```bash
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=athena
DB_USER=postgres
DB_PASSWORD=postgres
DB_MIN_POOL_SIZE=2
DB_MAX_POOL_SIZE=10

# Embeddings
EMBEDDING_PROVIDER=ollama
OLLAMA_HOST=http://localhost:11434

# LLM
ANTHROPIC_API_KEY=sk-ant-v0-xxxxx
LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-5-sonnet-20241022

# Features
ENABLE_RAG=1
ENABLE_GRAPH=1
ENABLE_CONSOLIDATION=1

# Performance
CACHE_ENABLED=1
CACHE_SIZE=1000

# Logging
LOG_LEVEL=INFO
LOG_TO_STDOUT=1
```

---

## Configuration Validation

Check your configuration:

```bash
# Verify database connection
python -c "from athena.core.database import Database; db = Database(); print('✅ DB OK')"

# Check embeddings
python -c "from athena.semantic.embeddings import EmbeddingManager; em = EmbeddingManager(); print('✅ Embeddings OK')"

# Full health check
python -c "from athena.manager import UnifiedMemoryManager; m = UnifiedMemoryManager(); print(m.get_health())"
```

---

## Troubleshooting Configuration

### Database Connection Failed

```bash
# Check PostgreSQL is running
pg_isready -h $DB_HOST -p $DB_PORT

# Verify credentials
psql -h $DB_HOST -U $DB_USER -d $DB_NAME

# Check firewall
nc -zv $DB_HOST $DB_PORT
```

### Embedding Provider Error

```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Verify Anthropic API key
python -c "import anthropic; client = anthropic.Anthropic(api_key='$ANTHROPIC_API_KEY'); print('✅ API key valid')"
```

### Configuration Not Applied

```bash
# Check precedence (highest to lowest):
# 1. Environment variables
echo $DB_HOST

# 2. .env file
cat .env | grep DB_HOST

# 3. ~/.claude/settings.local.json
cat ~/.claude/settings.local.json | grep -A 5 database

# 4. Hardcoded defaults
grep -r "DB_HOST.*=" src/athena/core/config.py
```

---

## Production Configuration

Example production setup:

```bash
# Database - AWS RDS
export DB_HOST=prod-db.abc123.us-east-1.rds.amazonaws.com
export DB_PORT=5432
export DB_NAME=athena_prod
export DB_USER=athena_app
export DB_PASSWORD=$(aws secretsmanager get-secret-value --secret-id prod/db-password --query SecretString --output text)
export DB_MIN_POOL_SIZE=5
export DB_MAX_POOL_SIZE=20

# Embeddings - Anthropic
export EMBEDDING_PROVIDER=anthropic
export ANTHROPIC_API_KEY=$(aws secretsmanager get-secret-value --secret-id prod/anthropic-key --query SecretString --output text)

# Security
export ENCRYPTION_ENABLED=1
export RATE_LIMIT_ENABLED=1
export RATE_LIMIT_REQUESTS_PER_MINUTE=10000

# Logging
export LOG_LEVEL=WARNING
export LOG_FILE=/var/log/athena/athena.log
export LOG_FORMAT=json

# Performance
export CACHE_ENABLED=1
export CACHE_SIZE=5000
export DB_MAX_POOL_SIZE=20
```

---

## Configuration Files

| File | Purpose | Priority |
|------|---------|----------|
| Environment variables | Runtime overrides | Highest (1) |
| `.env` | Local overrides | (2) |
| `~/.claude/settings.local.json` | User settings | (3) |
| `src/athena/core/config.py` | Defaults | Lowest (4) |

---

## See Also

- [INSTALLATION.md](./INSTALLATION.md) - Initial setup
- [DEVELOPMENT_GUIDE.md](./DEVELOPMENT_GUIDE.md) - Development environment
- [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) - Production deployment
- [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) - Common configuration issues

---

**Version**: 1.0
**Last Updated**: November 13, 2025
**Status**: Production Ready
