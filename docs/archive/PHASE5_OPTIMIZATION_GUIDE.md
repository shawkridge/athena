# Phase 5: PostgreSQL Optimization Guide

**Status**: Complete and Ready for Deployment
**Date**: November 2025
**Scope**: Production optimization strategies for PostgreSQL-based Athena

---

## Quick Start: Performance Tuning (5 minutes)

```bash
# 1. Start PostgreSQL with optimized settings
docker-compose up -d postgres

# 2. Wait for schema initialization (auto-includes indices)
sleep 10

# 3. Verify indices are created
docker-compose exec postgres psql -U athena -d athena -c "\d memories"

# 4. Test performance
python3 scripts/test_postgres_connection.py

# 5. Monitor performance
docker-compose exec postgres psql -U athena -d athena -c "
SELECT
  schemaname,
  tablename,
  idx_scan,
  idx_tup_read,
  idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;"
```

---

## 1. Index Optimization

### Current Indices (From init_postgres.sql)

All indices are automatically created during schema initialization:

```sql
-- Vector search index (IVFFlat - approximate nearest neighbor)
CREATE INDEX idx_memories_embedding
  ON memories
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);  -- Tune based on dataset size

-- Full-text search index
CREATE INDEX idx_memories_fts
  ON memories
  USING GIN (fts_content);

-- Relational queries
CREATE INDEX idx_memories_project_type
  ON memories(project_id, memory_type);

CREATE INDEX idx_memories_created
  ON memories(created_at DESC);

-- Task queries
CREATE INDEX idx_tasks_project_status
  ON tasks(project_id, status, priority DESC);
```

### Tuning IVFFlat Index

The `lists` parameter controls accuracy vs speed tradeoff:

| lists | Dataset Size | Speed | Accuracy |
|-------|--------------|-------|----------|
| 50 | <100k | 🚀 Fastest | ~85% |
| 100 | 100k-1M | ⚡ Fast | ~95% |
| 200 | 1M-10M | 🐢 Slower | ~99% |
| 400+ | >10M | 🐌 Very slow | 99%+ |

**Recommendation**: Start with `lists = 100`, adjust based on latency monitoring.

```sql
-- Rebuild index with different lists parameter
REINDEX INDEX CONCURRENTLY idx_memories_embedding;

-- Check index statistics
SELECT * FROM pg_stat_user_indexes
WHERE indexname = 'idx_memories_embedding';
```

### HNSW vs IVFFlat

PostgreSQL pgvector supports two index types:

| Aspect | IVFFlat | HNSW |
|--------|---------|------|
| Memory | Low | High |
| Build time | Fast | Slow |
| Query speed | Fast | Very fast |
| Accuracy | Good | Excellent |
| Dataset size | <10M | 10M+ |
| Recommended | Development | Production |

**Production Recommendation**: Use HNSW for >1M vectors:

```sql
-- Create HNSW index (requires pgvector >= 0.5.0)
CREATE INDEX idx_memories_embedding_hnsw
  ON memories
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);
```

### Full-Text Search Optimization

For large text-heavy workloads:

```sql
-- Create materialized view for FTS ranking
CREATE MATERIALIZED VIEW memories_fts_ranked AS
SELECT
  m.id,
  m.project_id,
  m.content,
  ts_rank(m.fts_content, websearch_to_tsquery('english', m.content)) as rank
FROM memories m;

-- Index the ranking
CREATE INDEX idx_memories_fts_ranked
  ON memories_fts_ranked(project_id, rank DESC);

-- Query using materialized view
SELECT * FROM memories_fts_ranked
WHERE project_id = $1
ORDER BY rank DESC
LIMIT 10;
```

---

## 2. Connection Pooling Configuration

### Current Configuration (docker-compose.yml)

```yaml
postgres:
  environment:
    # Connection settings
    POSTGRES_MAX_CONNECTIONS: 200
    POSTGRES_SUPERUSER_RESERVED_CONNECTIONS: 3
    POSTGRES_EFFECTIVE_CACHE_SIZE: 4GB
    POSTGRES_SHARED_BUFFERS: 1GB
    POSTGRES_WORK_MEM: 50MB
```

### Application-Level Pool Configuration

Tune based on concurrency needs:

```python
# src/athena/core/database_postgres.py
POOL_MIN_SIZE = 2      # Min connections to maintain
POOL_MAX_SIZE = 10     # Max concurrent connections

# For high-concurrency systems:
# POOL_MIN_SIZE = 10
# POOL_MAX_SIZE = 50

# Environment override
import os
min_size = int(os.environ.get('ATHENA_POSTGRES_MIN_SIZE', 2))
max_size = int(os.environ.get('ATHENA_POSTGRES_MAX_SIZE', 10))
```

### Monitoring Pool Usage

```python
# Check connection pool stats
async with db.pool.connection() as conn:
    async with conn.cursor() as cur:
        await cur.execute("""
            SELECT
              datname,
              count(*) as connections,
              max(now() - query_start) as oldest_query
            FROM pg_stat_activity
            WHERE datname = current_database()
            GROUP BY datname
        """)
        stats = await cur.fetchall()
        print(f"Pool stats: {stats}")
```

### PgBouncer for Advanced Pooling

For very high concurrency (>100 concurrent connections):

```ini
# /etc/pgbouncer/pgbouncer.ini
[databases]
athena = host=postgres port=5432 dbname=athena

[pgbouncer]
pool_mode = transaction           # Reuse connections between transactions
max_client_conn = 1000            # Total client connections
default_pool_size = 25            # Connections per database
min_pool_size = 5                 # Minimum idle connections
reserve_pool_size = 5             # Emergency reserve
reserve_pool_timeout = 3          # Timeout for reserve connections
max_idle = 600                    # Close idle after 10 min
max_lifetime = 3600               # Force reconnect after 1 hour
```

---

## 3. Query Optimization

### Analyze Slow Queries

Enable query logging in PostgreSQL:

```sql
-- Log all queries >100ms
ALTER SYSTEM SET log_min_duration_statement = 100;
SELECT pg_reload_conf();

-- Then check logs
docker-compose logs postgres | grep duration
```

### EXPLAIN ANALYZE for Debugging

Understand query execution plans:

```sql
-- Analyze a hybrid search query
EXPLAIN ANALYZE
SELECT m.id, m.content,
  (1 - (m.embedding <=> $1)) * 0.5 as semantic_score,
  ts_rank(m.fts_content, websearch_to_tsquery('english', $2)) * 0.3 as text_score,
  exp(-0.01 * (EXTRACT(EPOCH FROM now() - m.created_at) / 86400.0)) * 0.2 as recency_score
FROM memories m
WHERE m.project_id = $3
  AND m.memory_type = ANY($4::text[])
ORDER BY (semantic_score + text_score + recency_score) DESC
LIMIT 10;
```

### Common Performance Patterns

**Pattern 1: Vector Search Only (Fast)**
```sql
-- ~20ms for <1M records
SELECT id, embedding <=> $1 as distance
FROM memories
WHERE project_id = $2
ORDER BY embedding <=> $1
LIMIT 10;
```

**Pattern 2: Hybrid with Filtering (Balanced)**
```sql
-- ~30-40ms for <1M records
SELECT id,
  (1 - (embedding <=> $1)) * 0.5 +
  ts_rank(fts_content, $2) * 0.3 +
  recency_boost() * 0.2 as score
FROM memories
WHERE project_id = $3
  AND memory_type = ANY($4)
ORDER BY score DESC
LIMIT 20;
```

**Pattern 3: Full Composite (Complex)**
```sql
-- ~50-100ms for <1M records
SELECT m.id, c.name,
  (1 - (m.embedding <=> $1)) * 0.5 as semantic,
  ts_rank(m.fts_content, $2) * 0.3 as text,
  CASE m.memory_type
    WHEN 'fact' THEN 0.9
    WHEN 'procedure' THEN 0.7
    ELSE 0.5
  END * 0.1 as type_relevance,
  exp(-0.01 * (EXTRACT(EPOCH FROM now() - m.created_at) / 86400.0)) * 0.1 as recency
FROM memories m
JOIN consolidations c ON m.consolidation_id = c.id
WHERE m.project_id = $3
ORDER BY (semantic + text + type_relevance + recency) DESC
LIMIT 20;
```

---

## 4. Memory and Resource Tuning

### PostgreSQL Configuration

Optimal settings for different system sizes:

#### Small (Development)
```ini
# ~/.pgpass or docker-compose environment
POSTGRES_SHARED_BUFFERS=256MB
POSTGRES_EFFECTIVE_CACHE_SIZE=1GB
POSTGRES_MAINTENANCE_WORK_MEM=64MB
POSTGRES_WORK_MEM=16MB
```

#### Medium (Production, 4-8 cores, 16GB RAM)
```ini
POSTGRES_SHARED_BUFFERS=4GB          # 25% of system RAM
POSTGRES_EFFECTIVE_CACHE_SIZE=12GB   # 75% of system RAM
POSTGRES_MAINTENANCE_WORK_MEM=1GB
POSTGRES_WORK_MEM=40MB
POSTGRES_RANDOM_PAGE_COST=1.1        # For SSD
POSTGRES_EFFECTIVE_IO_CONCURRENCY=200
```

#### Large (Production, 16+ cores, 64GB+ RAM)
```ini
POSTGRES_SHARED_BUFFERS=16GB         # 25% of system RAM
POSTGRES_EFFECTIVE_CACHE_SIZE=48GB   # 75% of system RAM
POSTGRES_MAINTENANCE_WORK_MEM=2GB
POSTGRES_WORK_MEM=100MB
POSTGRES_RANDOM_PAGE_COST=1.0        # For SSD array
POSTGRES_EFFECTIVE_IO_CONCURRENCY=500
POSTGRES_MAX_PARALLEL_WORKERS=8
POSTGRES_MAX_PARALLEL_WORKERS_PER_GATHER=4
```

### Vector Index Memory

IVFFlat and HNSW indices consume memory:

```python
# Estimate index memory usage
vectors = 1_000_000
dimensions = 768
bytes_per_vector = dimensions * 4  # float32

# IVFFlat
ivfflat_memory = vectors * bytes_per_vector * 1.3  # 30% overhead
print(f"IVFFlat: {ivfflat_memory / (1024**3):.1f} GB")  # ~3.1 GB

# HNSW
hnsw_memory = vectors * bytes_per_vector * 2.5  # 150% overhead
print(f"HNSW: {hnsw_memory / (1024**3):.1f} GB")  # ~7.7 GB
```

---

## 5. Partitioning Strategy

### When to Partition

Partition when:
- Dataset >100M rows
- Tables >10GB
- Query performance degrading
- Need to archive old data

### Partition by Project_ID

Most effective for multi-tenant systems:

```sql
-- Create partitioned table
CREATE TABLE memories_partitioned (
  id SERIAL,
  project_id INT NOT NULL,
  content TEXT,
  embedding vector(768),
  created_at TIMESTAMP,
  PRIMARY KEY (id, project_id)
) PARTITION BY LIST (project_id);

-- Create partition for each active project
CREATE TABLE memories_project_1 PARTITION OF memories_partitioned
  FOR VALUES IN (1);

CREATE TABLE memories_project_2 PARTITION OF memories_partitioned
  FOR VALUES IN (2);

-- Default partition for new projects
CREATE TABLE memories_other PARTITION OF memories_partitioned
  DEFAULT;
```

### Partition by Date Range

For time-based archival:

```sql
-- Create date-partitioned table
CREATE TABLE memories_by_month (
  id SERIAL,
  created_at TIMESTAMP NOT NULL,
  project_id INT,
  content TEXT,
  PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (DATE_TRUNC('month', created_at));

-- Monthly partitions
CREATE TABLE memories_2025_01 PARTITION OF memories_by_month
  FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

CREATE TABLE memories_2025_02 PARTITION OF memories_by_month
  FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');
```

### Archive Strategy

```sql
-- Move old partitions to archive tablespace
ALTER TABLE memories_2024_01 SET TABLESPACE archive_disk;

-- Or delete entirely
DROP TABLE memories_2024_01;

-- Query recent data only
SELECT * FROM memories_by_month
WHERE created_at >= DATE_TRUNC('month', NOW() - INTERVAL '3 months')
```

---

## 6. Consolidation Optimization

### Fast Consolidation Queries

The consolidation system performs clustering and pattern extraction:

```sql
-- Fast clustering by session (not full matrix)
SELECT
  session_id,
  array_agg(id) as event_ids,
  COUNT(*) as event_count,
  AVG(similarity) as avg_similarity
FROM (
  SELECT
    e1.id,
    CASE WHEN ABS(EXTRACT(EPOCH FROM e1.timestamp - e2.timestamp)) < 3600
      THEN e2.session_id
      ELSE NULL
    END as session_id,
    1 - (e1.embedding <=> e2.embedding) as similarity
  FROM episodic_events e1
  CROSS JOIN LATERAL (
    SELECT * FROM episodic_events e2
    WHERE e2.project_id = e1.project_id
      AND e2.timestamp >= e1.timestamp - INTERVAL '1 hour'
      AND e2.timestamp <= e1.timestamp + INTERVAL '1 hour'
    ORDER BY e2.embedding <=> e1.embedding
    LIMIT 5  -- Only compare to 5 nearest neighbors
  ) e2
)
GROUP BY session_id;
```

### Consolidation Scheduling

```python
# Schedule consolidation during off-peak hours
import schedule
import asyncio

async def consolidate_task():
    """Run consolidation with low priority"""
    db = get_database()
    await db.consolidate(
        max_events=10000,  # Process in batches
        min_cluster_size=5,  # Only cluster if >5 events
    )

# Run at 2 AM daily
schedule.every().day.at("02:00").do(asyncio.run, consolidate_task())

# Or manually trigger
asyncio.run(consolidate_task())
```

---

## 7. Monitoring and Alerting

### Key Metrics to Monitor

```sql
-- 1. Index usage
SELECT
  schemaname, tablename, indexname,
  idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;

-- 2. Cache hit ratio (should be >99%)
SELECT
  sum(heap_blks_read) as heap_read,
  sum(heap_blks_hit) as heap_hit,
  sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read)) as hit_ratio
FROM pg_statio_user_tables;

-- 3. Table sizes
SELECT
  schemaname, tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
  pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) -
                 pg_relation_size(schemaname||'.'||tablename)) as index_size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- 4. Slow queries
SELECT
  query,
  mean_exec_time,
  calls,
  (mean_exec_time * calls) / 1000 as total_time_sec
FROM pg_stat_statements
WHERE query NOT LIKE '%pg_stat%'
ORDER BY mean_exec_time DESC
LIMIT 20;
```

### Docker Monitoring

```bash
# Monitor PostgreSQL resource usage
docker stats postgres

# View PostgreSQL logs
docker-compose logs -f postgres

# Connect to monitor
docker-compose exec postgres psql -U athena -d athena -c "\watch SELECT * FROM pg_stat_activity;"
```

---

## 8. Backup and Recovery

### Backup Strategy

```bash
# Full backup (daily)
docker-compose exec postgres pg_dump -U athena athena > backup_$(date +%Y%m%d).sql

# Compressed backup
docker-compose exec postgres pg_dump -U athena athena | gzip > backup_$(date +%Y%m%d).sql.gz

# PITR setup (point-in-time recovery)
docker-compose exec postgres psql -U athena -d athena << EOF
ALTER SYSTEM SET wal_level = replica;
ALTER SYSTEM SET max_wal_senders = 3;
ALTER SYSTEM SET max_replication_slots = 3;
SELECT pg_reload_conf();
EOF

# Test backup
docker-compose exec postgres psql -U athena -d athena < backup_20250101.sql
```

### Recovery Procedures

```bash
# 1. Stop containers
docker-compose down

# 2. Restore backup
docker-compose up -d postgres
sleep 10
docker-compose exec postgres psql -U athena < backup_20250101.sql

# 3. Verify integrity
docker-compose exec postgres psql -U athena -d athena -c "
SELECT
  COUNT(*) as total_memories,
  COUNT(DISTINCT project_id) as projects,
  MAX(created_at) as latest_memory
FROM memories;
"

# 4. Restart services
docker-compose up -d
```

---

## 9. Scaling Strategies

### Vertical Scaling (Single Large Server)

Good for: <10M vectors, <1 year data, <100 concurrent users

```sql
-- Increase resources
POSTGRES_SHARED_BUFFERS=32GB
POSTGRES_EFFECTIVE_CACHE_SIZE=96GB
POSTGRES_MAX_CONNECTIONS=500
```

### Horizontal Scaling with Read Replicas

Good for: High read load, distributed deployments

```yaml
# docker-compose.yml
postgres:
  image: postgres:16
  environment:
    POSTGRES_MAX_CONNECTIONS: 200

postgres_replica1:
  image: postgres:16
  environment:
    POSTGRES_REPLICATION_MODE: replica
    POSTGRES_REPLICATION_USER: replicator
    POSTGRES_REPLICATION_PASSWORD: secure_password
  command: postgres -c synchronous_standby_names=
```

### Sharding (Multiple Databases)

Good for: >100M vectors, multiple projects, global scale

```python
# Distribution by project_id
def get_shard_for_project(project_id: int, num_shards: int = 4) -> int:
    """Determine which shard handles this project"""
    return project_id % num_shards

# Connect to correct shard
project_id = 42
shard_id = get_shard_for_project(project_id)
db = get_database(shard=shard_id)

# Query goes to the right shard only
results = await db.hybrid_search(
    project_id=project_id,
    embedding=embedding,
    query_text=text,
)
```

---

## 10. Troubleshooting Performance Issues

### Issue: Slow Searches (>100ms)

**Diagnosis**:
```sql
-- Check index stats
SELECT * FROM pg_stat_user_indexes
WHERE tablename = 'memories'
ORDER BY idx_scan DESC;

-- Check for missing indices
SELECT * FROM pg_tables
WHERE tablename = 'memories';
```

**Solutions**:
1. Create missing indices
2. Increase `lists` parameter in IVFFlat
3. Switch to HNSW index for large datasets
4. Increase shared_buffers

### Issue: High Memory Usage

**Diagnosis**:
```bash
# Check Docker memory usage
docker stats postgres

# Check PostgreSQL processes
docker-compose exec postgres ps aux | grep postgres

# Check cache usage
docker-compose exec postgres psql -U athena -c "
SELECT
  sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read)) as cache_hit_ratio,
  sum(temp_blks_read) as temp_disk_reads
FROM pg_statio_user_tables;
"
```

**Solutions**:
1. Increase Docker memory limits
2. Reduce connection pool size
3. Enable index-only scans
4. Archive old data

### Issue: Connection Pool Exhaustion

**Diagnosis**:
```sql
-- Check active connections
SELECT
  datname, count(*) as count,
  max(query_start) as oldest_query
FROM pg_stat_activity
GROUP BY datname;
```

**Solutions**:
1. Increase POOL_MAX_SIZE
2. Use PgBouncer for connection multiplexing
3. Add connection timeout
4. Implement query cancellation

### Issue: Slow Consolidation

**Diagnosis**:
```sql
-- Check consolidation table size
SELECT
  schemaname, tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE tablename LIKE 'consolidation%';
```

**Solutions**:
1. Partition consolidation table by project_id
2. Archive old consolidations
3. Use batch processing
4. Increase work_mem

---

## 11. Production Deployment Checklist

- [ ] PostgreSQL 16+ installed
- [ ] pgvector extension installed and indexed
- [ ] Full-text search indices created
- [ ] Shared buffers configured (25% RAM)
- [ ] Connection pooling configured (min/max)
- [ ] Query logging enabled
- [ ] Backup scheduled daily
- [ ] Point-in-time recovery configured
- [ ] Monitoring and alerting setup
- [ ] Load testing completed
- [ ] Rollback procedure documented
- [ ] Team trained on operations

---

## 12. Performance Baseline Reference

Expected performance with optimized PostgreSQL:

```
Dataset: 1M vectors (768-dim), 10M memories, 100 projects
Storage: 8GB total (vectors + metadata)
Memory: 16GB system, 4GB shared_buffers
CPU: 8 cores

Operation                      Latency    Throughput
─────────────────────────────────────────────────────
Semantic search                20-30ms    1000+/sec
Hybrid search (text+vector)    25-40ms    500+/sec
Full-text search               15-25ms    2000+/sec
Cross-project search           40-60ms    100+/sec
Memory recall                  20-40ms    1000+/sec
Batch insert (1000 items)      1-2s       500+/sec
Consolidation (10k events)     2-4s       2500+/sec
Vector similarity (top-10)     18-25ms    1000+/sec
```

---

## Summary

**Phase 5 PostgreSQL is optimized for**:

✅ Development: Fast iteration, minimal setup
✅ Production: High performance, scalable architecture
✅ Multi-domain: Unified data model for Memory + Planning + Code
✅ Analytics: Rich metadata for insights and optimization

**Next steps**:
1. Implement monitoring and alerting
2. Set up backup and recovery procedures
3. Load test with real workloads
4. Monitor performance in production
5. Iteratively optimize based on metrics

