# Athena Deployment Guide

Complete deployment procedures for development, staging, and production environments.

## Table of Contents

1. [Environment Setup](#environment-setup)
2. [Development Deployment](#development-deployment)
3. [Staging Deployment](#staging-deployment)
4. [Production Deployment](#production-deployment)
5. [Database Migrations](#database-migrations)
6. [Monitoring & Health](#monitoring--health)
7. [Backup & Recovery](#backup--recovery)
8. [Troubleshooting Deployments](#troubleshooting-deployments)

---

## Environment Setup

### System Requirements

```
CPU:              2+ cores
Memory:           4GB+ RAM
Storage:          10GB+ (1GB initial, grows with usage)
Python:           3.10+
Operating System: Linux/macOS/Windows (WSL)
```

### Network & Access

```
Port 9090: MCP Server (local only)
Ollama:    http://localhost:11434 (for local embeddings)
Claude:    Requires ANTHROPIC_API_KEY (for validation)
```

---

## Development Deployment

### Quick Start (5 minutes)

```bash
cd /home/user/.work/athena

# Create environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -q mcp ollama sqlite-vec anthropic pydantic aiofiles typing-extensions
pip install -q psutil pytest-asyncio pytest-benchmark numpy scipy scikit-learn pyyaml

# Verify installation
python3 -c "import athena; print('✓ Ready')"

# Test MCP server
python3 -m athena.server &
# Server logs will appear
```

### MCP Configuration

**File**: `~/.mcp.json`

```json
{
  "mcpServers": {
    "athena": {
      "command": "/home/user/.work/athena/.venv/bin/python3",
      "args": ["-m", "athena.server"],
      "env": {
        "MEMORY_MCP_DB_PATH": "/home/user/.work/athena/memory.db",
        "PYTHONPATH": "/home/user/.work/athena/src"
      }
    }
  }
}
```

### Verification

```bash
# Test connection
claude mcp list
# Should show: ✓ athena - Connected

# Test operations
memory recall "test query" --project 1
# Should return results or empty list
```

---

## Staging Deployment

### Environment Configuration

```bash
# Create staging database (separate from dev)
mkdir -p /var/athena/staging
chmod 750 /var/athena/staging

# Initialize database
python3 -c "
from athena.core.database import Database
db = Database('/var/athena/staging/memory.db')
db.initialize_schema()
"

# Verify
sqlite3 /var/athena/staging/memory.db ".tables"
```

### Docker Deployment (Optional)

**Dockerfile**:
```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y sqlite3 libsqlite3-dev

# Copy source
COPY src/ /app/src/
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import athena; print('healthy')"

# Run server
ENV MEMORY_MCP_DB_PATH=/data/memory.db
VOLUME ["/data"]
EXPOSE 9090

CMD ["python3", "-m", "athena.server"]
```

**Build & Run**:
```bash
# Build image
docker build -t athena:latest .

# Run container
docker run -d \
  --name athena-staging \
  -v /var/athena/staging:/data \
  -p 9090:9090 \
  athena:latest

# Check logs
docker logs -f athena-staging

# Verify
docker exec athena-staging python -c "
  from athena.core.database import Database
  db = Database('/data/memory.db')
  events = db.get_connection().execute(
    'SELECT COUNT(*) FROM episodic_events'
  ).fetchone()[0]
  print(f'Database OK: {events} events')
"
```

### Load Testing

```bash
# Install load testing tool
pip install locust

# Create load test script
cat > load_test.py << 'EOF'
from locust import HttpUser, task, between

class AthenaUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def retrieve_memories(self):
        self.client.get("/api/recall?query=test&k=5")

    @task
    def create_memory(self):
        self.client.post("/api/remember", json={
            "content": "test memory",
            "type": "semantic"
        })
EOF

# Run load test
locust -f load_test.py -u 10 -r 2 -t 5m
```

---

## Production Deployment

### Pre-Deployment Checklist

- [ ] Tests passing (94/94)
- [ ] Performance validated (<100ms semantic search)
- [ ] Database backup created
- [ ] Rollback plan documented
- [ ] Monitoring configured
- [ ] Health checks passing
- [ ] Security review completed
- [ ] Documentation updated

### Production Configuration

**Directory Structure**:
```
/opt/athena/
├── current/          → /opt/athena/releases/v1.0.0/
├── releases/
│   ├── v0.9.0/
│   ├── v1.0.0/
│   └── v1.1.0/       ← Latest
├── shared/
│   ├── logs/         ← Shared logs
│   ├── backups/      ← Database backups
│   └── cache/        ← Shared cache
└── config/
    ├── production.env
    ├── logging.yaml
    └── monitoring.yaml
```

**Production Environment** (`/opt/athena/config/production.env`):
```bash
# Database
MEMORY_MCP_DB_PATH=/var/lib/athena/memory.db
DATABASE_BACKUP_PATH=/var/lib/athena/backups

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/athena/server.log

# Performance
CONSOLIDATION_STRATEGY=balanced
MAX_BATCH_SIZE=500
SEARCH_CACHE_TTL=3600

# Security
ENABLE_RATE_LIMITING=true
RATE_LIMIT_REQUESTS_PER_MINUTE=100

# Monitoring
ENABLE_METRICS=true
METRICS_PORT=9091
ENABLE_TRACING=true
```

### Deployment Steps

```bash
# 1. Create release directory
RELEASE_DIR=/opt/athena/releases/v1.0.0
mkdir -p $RELEASE_DIR

# 2. Copy source code
cp -r /home/user/.work/athena/src $RELEASE_DIR/
cp -r /home/user/.work/athena/.venv $RELEASE_DIR/

# 3. Load configuration
cp /opt/athena/config/production.env $RELEASE_DIR/.env

# 4. Verify database
python3 << 'EOF'
import os
from athena.core.database import Database

db_path = os.getenv('MEMORY_MCP_DB_PATH')
db = Database(db_path)

# Run integrity check
result = db.get_connection().execute('PRAGMA integrity_check').fetchone()
assert result[0] == 'ok', f"Database corrupted: {result[0]}"

print(f"✓ Database integrity verified: {db_path}")
EOF

# 5. Update symlink
ln -sfn /opt/athena/releases/v1.0.0 /opt/athena/current

# 6. Reload MCP server
systemctl restart athena

# 7. Health check
sleep 5
curl -s http://localhost:9090/health || echo "Health check failed"

# 8. Verify operations
python3 << 'EOF'
from athena.core.database import Database
from athena.semantic.search import SemanticSearch

db = Database(os.getenv('MEMORY_MCP_DB_PATH'))
search = SemanticSearch(db)
results = search.retrieve("test", k=1)
print(f"✓ Operations verified: {len(results)} results")
EOF

# 9. Monitor logs
tail -f /var/log/athena/server.log &

echo "✓ Deployment complete"
```

### Rolling Deployment

For zero-downtime deployments:

```bash
#!/bin/bash

# 1. Deploy to new release
NEW_VERSION=v1.1.0
RELEASE_DIR=/opt/athena/releases/$NEW_VERSION
mkdir -p $RELEASE_DIR
cp -r /build/$NEW_VERSION/* $RELEASE_DIR/

# 2. Health check new version
cd $RELEASE_DIR
python3 -m athena.server &
SERVER_PID=$!
sleep 2

# 3. Run smoke tests
./tests/smoke_tests.sh
if [ $? -ne 0 ]; then
    kill $SERVER_PID
    echo "❌ Smoke tests failed, rollback"
    exit 1
fi

# 4. Switch traffic
systemctl stop athena
ln -sfn $RELEASE_DIR /opt/athena/current
systemctl start athena

# 5. Verify
sleep 3
curl -s http://localhost:9090/health

echo "✓ Deployment complete: $NEW_VERSION"
```

---

## Database Migrations

### Schema Version Management

```sql
CREATE TABLE schema_version (
    id INTEGER PRIMARY KEY,
    version TEXT NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

INSERT INTO schema_version (version, description)
VALUES ('1.0.0', 'Initial schema');
```

### Backup Before Migration

```bash
# Full backup
sqlite3 /var/lib/athena/memory.db << 'EOF'
.backup '/var/lib/athena/backups/memory-'$(date +%Y%m%d-%H%M%S)'.db'
EOF

# Verify backup
sqlite3 /var/lib/athena/backups/memory-*.db ".tables"
```

### Safe Migration Pattern

```python
def migrate_v1_0_to_v1_1():
    """Migrate database from v1.0 to v1.1"""
    db = Database()

    # 1. Add new column
    try:
        db.execute("""
            ALTER TABLE episodic_events
            ADD COLUMN importance_score REAL DEFAULT 0.5
        """)
        logger.info("✓ Added importance_score column")
    except Exception as e:
        if "column already exists" not in str(e):
            raise

    # 2. Create new table
    db.execute("""
        CREATE TABLE IF NOT EXISTS memory_quality (
            id INTEGER PRIMARY KEY,
            project_id INTEGER,
            layer TEXT,
            quality_score REAL,
            measured_at TIMESTAMP
        )
    """)

    # 3. Populate new data
    db.execute("""
        INSERT INTO memory_quality (project_id, layer, quality_score)
        SELECT DISTINCT project_id, 'episodic', 0.7
        FROM episodic_events
    """)

    # 4. Verify migration
    result = db.execute("""
        SELECT COUNT(*) FROM memory_quality
    """).fetchone()[0]
    assert result > 0, "Migration verification failed"

    # 5. Update schema version
    db.execute("""
        INSERT INTO schema_version (version, description)
        VALUES ('1.1.0', 'Added importance_score and quality tracking')
    """)

    logger.info("✓ Migration complete")
```

---

## Monitoring & Health

### Health Check Endpoint

```python
@app.get("/health")
async def health_check():
    """Comprehensive health check"""
    return {
        "status": "healthy",
        "database": check_database(),
        "memory_layers": check_layers(),
        "performance": check_performance(),
        "timestamp": datetime.now().isoformat()
    }

def check_database():
    db = Database()
    result = db.get_connection().execute(
        'PRAGMA integrity_check'
    ).fetchone()[0]
    return {
        "ok": result == 'ok',
        "path": db.db_path,
        "size_mb": Path(db.db_path).stat().st_size / 1024 / 1024
    }

def check_layers():
    db = Database()
    cursor = db.get_connection().cursor()
    return {
        "episodic": cursor.execute(
            "SELECT COUNT(*) FROM episodic_events"
        ).fetchone()[0],
        "semantic": cursor.execute(
            "SELECT COUNT(*) FROM semantic_memories"
        ).fetchone()[0],
        "procedures": cursor.execute(
            "SELECT COUNT(*) FROM procedures"
        ).fetchone()[0],
    }

def check_performance():
    # Measure typical query time
    start = time.time()
    search = SemanticSearch(Database())
    search.retrieve("test", k=1)
    latency_ms = (time.time() - start) * 1000
    return {
        "search_latency_ms": latency_ms,
        "status": "ok" if latency_ms < 500 else "slow"
    }
```

### Monitoring Stack

**Prometheus Metrics**:
```yaml
# /etc/prometheus/athena.yml
scrape_configs:
  - job_name: 'athena'
    static_configs:
      - targets: ['localhost:9091']

metrics:
  - athena_episodic_events_total
  - athena_semantic_search_latency_ms
  - athena_consolidation_duration_ms
  - athena_database_size_mb
  - athena_cognitive_load
```

**Alerts**:
```yaml
- alert: SearchLatencySlow
  expr: athena_semantic_search_latency_ms > 500
  for: 5m
  annotations:
    summary: "Search latency >500ms"

- alert: DatabaseGrowing
  expr: rate(athena_database_size_mb[1h]) > 100
  for: 1h
  annotations:
    summary: "Database growing >100MB/hour"

- alert: ConsolidationFailed
  expr: athena_consolidation_errors_total > 0
  for: 10m
  annotations:
    summary: "Consolidation failing"
```

### Log Aggregation

**Format** (`/var/log/athena/server.log`):
```
[2025-11-05T14:32:00.123Z] [INFO] [semantic.search] Retrieved 5 results (87ms)
[2025-11-05T14:32:05.456Z] [WARN] [consolidation] Large event set (1200 events)
[2025-11-05T14:32:10.789Z] [ERROR] [graph] Relation not found: 42 → 100
```

---

## Backup & Recovery

### Automated Backups

```bash
#!/bin/bash
# /opt/athena/scripts/backup.sh

BACKUP_DIR=/var/lib/athena/backups
RETENTION_DAYS=30

# Create backup
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE=$BACKUP_DIR/memory-$TIMESTAMP.db

sqlite3 /var/lib/athena/memory.db ".backup $BACKUP_FILE"

# Verify backup
sqlite3 $BACKUP_FILE ".tables" > /dev/null
if [ $? -eq 0 ]; then
    echo "✓ Backup created: $BACKUP_FILE"
else
    echo "❌ Backup verification failed"
    exit 1
fi

# Cleanup old backups
find $BACKUP_DIR -name "memory-*.db" -mtime +$RETENTION_DAYS -delete

# Upload to storage (optional)
aws s3 cp $BACKUP_FILE s3://athena-backups/
```

**Cron Schedule**:
```bash
# /etc/cron.d/athena-backup
0 2 * * * /opt/athena/scripts/backup.sh
```

### Recovery Procedure

```bash
# 1. Identify good backup
ls -lt /var/lib/athena/backups/memory-*.db | head -5

# 2. Stop services
systemctl stop athena

# 3. Restore backup
RESTORE_FILE=/var/lib/athena/backups/memory-20251105_020000.db
cp $RESTORE_FILE /var/lib/athena/memory.db

# 4. Verify restored database
sqlite3 /var/lib/athena/memory.db ".tables"
sqlite3 /var/lib/athena/memory.db "PRAGMA integrity_check"

# 5. Restart services
systemctl start athena

# 6. Verify operations
sleep 3
curl -s http://localhost:9090/health
```

---

## Troubleshooting Deployments

### Deployment Fails

```bash
# 1. Check logs
tail -100 /var/log/athena/server.log

# 2. Verify database
sqlite3 /var/lib/athena/memory.db "PRAGMA integrity_check"

# 3. Check permissions
ls -l /var/lib/athena/

# 4. Rollback
ln -sfn /opt/athena/releases/v0.9.0 /opt/athena/current
systemctl restart athena
```

### Performance Degradation Post-Deployment

```bash
# 1. Check new version
athena_version = "$(ls -1 /opt/athena/releases | tail -1)"

# 2. Run baseline tests
python3 tests/performance_baseline.py

# 3. Compare with previous version
git diff ${OLD_VERSION}...HEAD --stat

# 4. Revert if critical
ln -sfn /opt/athena/releases/${OLD_VERSION} /opt/athena/current
systemctl restart athena
```

---

## References

- **Performance**: [PERFORMANCE_TUNING.md](PERFORMANCE_TUNING.md)
- **Architecture**: [ARCHITECTURE.md](ARCHITECTURE.md)
- **Troubleshooting**: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
