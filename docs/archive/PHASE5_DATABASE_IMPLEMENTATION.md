# Phase 5: PostgreSQL Database Implementation

**Status**: Database Layer Complete ✅
**Date**: November 8, 2025
**Component**: `src/athena/core/database_postgres.py` + `database_factory.py`

---

## Overview

Phase 5 Part 1 implements the PostgreSQL database layer, providing:
- **Unified database** for all 3 domains (Memory, Planning, Code Analysis)
- **Async/await support** via psycopg3 (modern PostgreSQL driver)
- **Connection pooling** for production use (configurable min/max connections)
- **Native hybrid search** combining semantic + full-text + relational in SQL
- **Backward compatibility** with Phase 4 SQLite via factory pattern
- **Comprehensive tests** for all CRUD operations and search functionality

---

## Architecture: Database Abstraction Layer

```
Application Layer (70+ memory operations)
    ↓
Database Factory (auto-detect backend)
    ↓
Database Interface (unified API)
    ├─ SQLiteDatabase (Phase 4, local development)
    └─ PostgresDatabase (Phase 5, production)
    ↓
Backend-Specific Implementation
    ├─ SQLite + sqlite-vec
    └─ PostgreSQL + pgvector (with psycopg connection pool)
```

### Key Design Decisions

1. **Async/Await**: All operations are async-first using psycopg3 for:
   - Non-blocking I/O for concurrent operations
   - Better resource utilization in multi-client scenarios
   - Compatible with Python async frameworks

2. **Connection Pooling**: Configurable pool (default 2-10 connections)
   - Auto-scales based on demand
   - Reuses connections to reduce overhead
   - Handles disconnections gracefully

3. **Factory Pattern**: DatabaseFactory allows automatic backend selection
   - Environment-driven configuration
   - No code changes to switch backends
   - Fallback support (use SQLite if PostgreSQL unavailable)

4. **Idempotent Schema**: All CREATE TABLE IF NOT EXISTS
   - Safe to initialize multiple times
   - Graceful schema updates for existing databases

---

## Module Structure

### `database_postgres.py` (520 lines)

The core PostgreSQL database implementation with:

**Classes**:
- `PostgresDatabase`: Main database manager with async operations

**Key Methods**:

#### Initialization
```python
db = PostgresDatabase(
    host="localhost",
    port=5432,
    dbname="athena",
    user="athena",
    password="athena_dev",
)
await db.initialize()  # Create schema, initialize pool
```

#### Project Operations
```python
# Create project
project = await db.create_project(
    name="my_project",
    path="/home/user/project",
    language="python",
)

# Get project
project = await db.get_project_by_path("/home/user/project")

# Update access
await db.update_project_access(project.id)
```

#### Memory Vector Operations
```python
# Store memory with vector
memory_id = await db.store_memory(
    project_id=1,
    content="Learned about pgvector",
    embedding=[0.1, 0.2, ..., 0.768],  # 768D
    memory_type="fact",
    domain="memory",
    tags=["learning", "optimization"],
)

# Get memory
memory = await db.get_memory(memory_id)
# Returns: {id, project_id, content, quality_score, ...}

# Delete memory
await db.delete_memory(memory_id)

# Update access stats (for consolidation tracking)
await db.update_access_stats(memory_id)
```

#### Hybrid Search (Native SQL)
```python
# Combined semantic + full-text + relational search
results = await db.hybrid_search(
    project_id=1,
    embedding=[0.1, 0.2, ..., 0.768],  # Query embedding
    query_text="optimization techniques",  # Keyword search
    limit=10,
    semantic_weight=0.7,
    keyword_weight=0.3,
    consolidation_state="consolidated",
)
# Returns: [
#   {id, content, memory_type, semantic_similarity, keyword_rank, hybrid_score},
#   ...
# ]
```

The hybrid search SQL query:
```sql
SELECT ...
FROM memory_vectors m
WHERE project_id = ? AND consolidation_state = ?
  AND (semantic_similarity > 0.3 OR keyword_rank > 0)
ORDER BY (0.7 * semantic_score + 0.3 * keyword_rank) DESC
LIMIT 10
```

#### Semantic Search (Vector-only)
```python
results = await db.semantic_search(
    project_id=1,
    embedding=query_embedding,
    limit=10,
    threshold=0.3,  # Cosine similarity
)
# Returns: [{id, content, semantic_similarity}, ...]
```

#### Consolidation Operations
```python
# Transition through consolidation states
await db.update_consolidation_state(
    memory_id=42,
    state="consolidated",  # unconsolidated → consolidated
)

# Get memories in reconsolidation window (labile within 1 hour)
labile_memories = await db.get_reconsolidation_window(
    project_id=1,
    window_minutes=60,
)
# Returns: [{id, content, seconds_since_retrieval}, ...]
```

#### Task & Goal Operations
```python
# Create task
task_id = await db.create_task(
    project_id=1,
    title="Optimize search latency",
    priority=8,
    status="in_progress",
)

# Create goal
goal_id = await db.create_goal(
    project_id=1,
    name="Achieve <50ms search latency",
    priority=9,
)
```

#### Episodic Event Operations
```python
# Store temporal event with spatial context
event_id = await db.store_episodic_event(
    project_id=1,
    session_id="session_20251108_001",
    timestamp=1730987654000,  # Unix ms
    event_type="learning",
    content="Tested pgvector hybrid search",
    context_cwd="/home/user/athena",
    context_files=["search.py", "database.py"],
    learned="Hybrid search 3x faster than app-level fusion",
    confidence=0.95,
)
```

#### Code Metadata Operations
```python
# Store code entity with semantic hash
code_id = await db.store_code_entity(
    project_id=1,
    memory_vector_id=42,
    file_path="src/search.py",
    entity_name="hybrid_search",
    entity_type="function",
    language="python",
    signature="async def hybrid_search(...) -> List[Result]",
    semantic_hash="sha256_hash_of_content",
    cyclomatic_complexity=5,
    lines_of_code=47,
)
```

#### Transaction Support
```python
# Atomic multi-operation transactions
async with db.transaction() as conn:
    # Multiple operations as atomic unit
    await conn.execute("INSERT INTO ...")
    await conn.execute("UPDATE ...")
    # Automatic commit on success, rollback on exception
```

#### Connection Management
```python
# Get raw connection from pool
async with db.get_connection() as conn:
    result = await conn.execute("SELECT ...")
    row = await result.fetchone()

# Close pool (cleanup)
await db.close()
```

### `database_factory.py` (240 lines)

Factory for automatic backend selection with environment-driven configuration:

**Classes**:
- `DatabaseFactory`: Static factory for database creation

**Configuration Priority**:
1. `ATHENA_DB_TYPE` environment variable (`sqlite` or `postgres`)
2. `ATHENA_POSTGRES_HOST` (if set, uses PostgreSQL)
3. Default: SQLite

**PostgreSQL Configuration** (Environment Variables):
```bash
# PostgreSQL backend settings
export ATHENA_POSTGRES_HOST=localhost
export ATHENA_POSTGRES_PORT=5432
export ATHENA_POSTGRES_DBNAME=athena
export ATHENA_POSTGRES_USER=athena
export ATHENA_POSTGRES_PASSWORD=athena_dev
export ATHENA_POSTGRES_MIN_SIZE=2
export ATHENA_POSTGRES_MAX_SIZE=10

# Or force backend selection
export ATHENA_DB_TYPE=postgres
```

**SQLite Configuration** (Environment Variables):
```bash
# SQLite path (Phase 4 compatibility)
export ATHENA_DB_PATH=~/.athena/memory.db
```

**Usage**:
```python
from athena.core.database_factory import get_database, DatabaseFactory

# Auto-detect backend from environment
db = get_database()

# Force PostgreSQL
db = get_database(backend='postgres')

# Force SQLite
db = get_database(backend='sqlite')

# Custom configuration
db = get_database(
    backend='postgres',
    host='db.example.com',
    port=5432,
    dbname='production_athena',
    user='athena_prod',
    password='secure_password',
)

# Check available backends
available = DatabaseFactory.get_available_backends()
print(f"Available: {available}")  # ['sqlite', 'postgres']
```

---

## Installation & Setup

### Prerequisites

**PostgreSQL 16+ with pgvector**:
```bash
# Using docker-compose (recommended)
docker-compose up -d postgres llamacpp

# Or install locally
# macOS: brew install postgresql
# Ubuntu: sudo apt install postgresql
# Windows: https://www.postgresql.org/download/windows/

# Install pgvector extension
CREATE EXTENSION vector;
```

### Python Dependencies

```bash
# Install psycopg3 (async PostgreSQL driver)
pip install "psycopg[binary]"

# Or with all optional deps
pip install "psycopg[binary,json,shapely]"
```

Update `requirements.txt`:
```
psycopg[binary]>=3.1.0,<4.0
# Existing deps...
```

### Database Initialization

```python
# Async initialization in application startup
import asyncio
from athena.core.database_factory import get_database

async def main():
    # Auto-detects backend from environment
    db = get_database()

    # Creates schema (idempotent)
    await db.initialize()

    # Use database
    project = await db.create_project(
        name="my_project",
        path="/home/user/project",
    )

    # Cleanup
    await db.close()

asyncio.run(main())
```

---

## Testing

### Run All PostgreSQL Tests

```bash
# With PostgreSQL running (docker-compose up -d)
pytest tests/integration/test_postgres_database.py -v

# With specific markers
pytest tests/integration/test_postgres_database.py -v -m asyncio

# With output capture
pytest tests/integration/test_postgres_database.py -v -s
```

### Test Coverage

Tests in `test_postgres_database.py`:

1. **Setup Tests** (3 tests)
   - Database initialization
   - Connection pool
   - Schema creation

2. **Project Operations** (3 tests)
   - Create project
   - Get project by path
   - Update access time

3. **Memory Vector Operations** (4 tests)
   - Store memory with embedding
   - Retrieve memory
   - Delete memory
   - Track access statistics

4. **Hybrid Search** (2 tests)
   - Semantic search (vector-only)
   - Hybrid search (semantic + keyword)

5. **Consolidation** (2 tests)
   - State transitions (unconsolidated → consolidated)
   - Reconsolidation window queries

6. **Tasks & Goals** (2 tests)
   - Create task
   - Create goal

7. **Episodic Events** (1 test)
   - Store event with context

8. **Code Metadata** (1 test)
   - Store code entity with dependencies

9. **Transactions** (1 test)
   - Atomic multi-operation support

**Total**: 19 comprehensive tests covering all major operations

---

## Performance Characteristics

### Expected Latencies (PostgreSQL + pgvector)

| Operation | Latency | Notes |
|-----------|---------|-------|
| `store_memory` | 5-15ms | Single vector insert |
| `get_memory` | 1-5ms | Direct lookup by ID |
| `delete_memory` | 2-5ms | Single delete |
| `semantic_search` (10K vectors) | 10-20ms | Vector index search |
| `hybrid_search` (10K vectors) | 20-40ms | Combined scoring |
| `store_episodic_event` | 5-10ms | Event insert |
| `create_task` | 2-5ms | Task creation |
| Transaction overhead | <1ms | Per operation |

### Throughput

- **Sequential inserts**: 500-1000 ops/sec
- **Concurrent operations**: 100-200 ops/sec (with 10-connection pool)
- **Searches**: 50-100 searches/sec (with caching)

### Resource Usage

- **Connections**: 2-10 (configurable pool)
- **Memory per connection**: ~5MB
- **Query execution memory**: <100MB for 100K vector search

---

## Backward Compatibility

The database layer maintains compatibility with Phase 4 SQLite:

```python
# Phase 4 code works unchanged
db = get_database()  # Auto-detects SQLite or PostgreSQL

# Store memory (same API)
memory_id = await db.store_memory(
    project_id=1,
    content="Learning",
    embedding=[...],
    memory_type="fact",
)

# Search (same API)
results = await db.hybrid_search(
    project_id=1,
    embedding=[...],
    query_text="optimization",
)
```

### Migration Path

1. **Phase 4 (SQLite)**: `get_database()` returns SQLiteDatabase
2. **Phase 5 (PostgreSQL)**: Set `ATHENA_POSTGRES_HOST` or `ATHENA_DB_TYPE=postgres`
3. **Fallback**: If PostgreSQL unavailable, automatically uses SQLite

No code changes required to use new backend!

---

## Error Handling

### Connection Errors

```python
try:
    db = get_database()
    await db.initialize()
except Exception as e:
    print(f"Database connection failed: {e}")
    # Fallback to SQLite
    db = get_database(backend='sqlite')
```

### Transaction Rollback

```python
async with db.transaction() as conn:
    try:
        await conn.execute("INSERT ...")
        # On exception, automatic rollback
    except Exception as e:
        print(f"Operation failed: {e}")
        # Transaction automatically rolled back
```

### Query Errors

```python
try:
    results = await db.hybrid_search(...)
except Exception as e:
    print(f"Search failed: {e}")
    # Handle gracefully, maybe retry or use fallback
```

---

## Monitoring & Diagnostics

### Check Connection Pool

```python
db = PostgresDatabase()
await db.initialize()

# Pool size
print(f"Pool size: {db._pool.get_size()}")

# Available connections
print(f"Available: {db._pool.get_idle_count()}")
```

### Log Database Queries

```bash
# Enable PostgreSQL query logging
export PGLOGGING=1

# View logs in container
docker logs athena-postgres
```

### Performance Monitoring

```python
import time

async def timed_search(db, query_embedding):
    start = time.time()
    results = await db.hybrid_search(
        project_id=1,
        embedding=query_embedding,
        query_text="optimization",
    )
    elapsed = time.time() - start
    print(f"Search took {elapsed*1000:.1f}ms, found {len(results)} results")
    return results
```

---

## Next Steps

### 1. Integration with Memory Layer

Update `src/athena/semantic/search.py` to use PostgreSQL hybrid search:

```python
from athena.core.database_factory import get_database

async def search(query_text, query_embedding, limit=10):
    db = get_database()
    return await db.hybrid_search(
        project_id=current_project_id,
        embedding=query_embedding,
        query_text=query_text,
        limit=limit,
    )
```

### 2. Consolidation Workflow

Update consolidation to use PostgreSQL operations:

```python
# Get unconsolidated memories
async def get_consolidation_queue(project_id):
    db = get_database()
    return await db.semantic_search(
        project_id=project_id,
        embedding=[0]*768,  # Match all
        # Add filter for consolidation_state
    )

# Consolidate and update state
async def consolidate_memory(memory_id, patterns):
    db = get_database()
    await db.update_consolidation_state(memory_id, "consolidated")
```

### 3. MCP Handler Updates

Update `src/athena/mcp/handlers.py` to use PostgreSQL:

```python
async def recall(query: str, limit: int = 10):
    db = get_database()
    embedding = await generate_embedding(query)
    results = await db.hybrid_search(
        project_id=current_project,
        embedding=embedding,
        query_text=query,
        limit=limit,
    )
    return results
```

---

## Troubleshooting

### "psycopg module not found"

```bash
pip install "psycopg[binary]"
```

### "Connection refused" to PostgreSQL

```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Check connection settings
export ATHENA_POSTGRES_HOST=localhost
export ATHENA_POSTGRES_PORT=5432

# Test connection
psql -h localhost -U athena -d athena
```

### "pgvector extension not found"

```bash
# Schema initialization should create it
# Or manually:
docker exec athena-postgres psql -U athena -d athena -c "CREATE EXTENSION vector"
```

### Pool exhausted (too many connections)

```bash
# Increase pool size
export ATHENA_POSTGRES_MAX_SIZE=20

# Or check for connection leaks
await db.close()  # Always cleanup
```

---

## Summary

The PostgreSQL database layer provides:

✅ **Unified Database**: All 3 domains in single ACID source
✅ **Native Hybrid Search**: SQL-native combining semantic + keyword + relational
✅ **Production Ready**: Connection pooling, error handling, transactions
✅ **Backward Compatible**: Phase 4 code works unchanged
✅ **Async/Await**: Non-blocking I/O for concurrent operations
✅ **Comprehensive Tests**: 19 tests covering all operations
✅ **Factory Pattern**: Auto-detect backend from environment

**Ready for Phase 5 Part 2**: Integrating with memory layers and consolidation workflow.

