# Phase 5: Complete Setup Guide

**Date**: November 8, 2025
**Status**: All dependencies installed, scripts ready, tests prepared

---

## What Was Installed

### Python Dependencies

✅ **psycopg[binary] 3.2.12** - Modern PostgreSQL driver with async support
- Installed in virtual environment
- Added to `pyproject.toml` dependencies
- Provides: `AsyncConnection`, core database functionality

✅ **psycopg-pool 3.2.7** - Connection pooling for psycopg
- Installed in virtual environment
- Added to `pyproject.toml` dependencies
- Provides: `AsyncConnectionPool` for connection management

✅ **pytest-asyncio** - For async test support (already installed)

All dependencies installed via:
```bash
pip install -e ".[dev]"
```

### Module Imports

✅ All new modules import successfully:
- `athena.core.database_postgres.PostgresDatabase`
- `athena.core.database_factory.DatabaseFactory`
- `athena.core.database_factory.get_database`

---

## Setup Scripts Created

### 1. `scripts/setup_phase5.sh`

Automated setup script that:
1. Checks Python version (3.10+)
2. Creates/activates virtual environment
3. Installs dependencies
4. Checks Docker installation
5. Starts PostgreSQL and llama.cpp services
6. Waits for services to be healthy
7. Verifies Python imports

**Usage**:
```bash
chmod +x scripts/setup_phase5.sh
./scripts/setup_phase5.sh
```

### 2. `scripts/test_postgres_connection.py`

Interactive test script that verifies:
1. Database connection
2. Schema initialization
3. Project creation
4. Memory vector storage
5. Semantic search
6. Hybrid search
7. Task creation
8. Cleanup

**Usage**:
```bash
python3 scripts/test_postgres_connection.py
```

### 3. `.env.example`

Configuration template with all environment variables:
- PostgreSQL connection settings
- SQLite fallback settings
- Embedding provider configuration
- llama.cpp settings
- Vector search parameters
- Consolidation settings

**Usage**:
```bash
cp .env.example .env
# Edit .env with your settings
```

---

## Quick Start (5 minutes)

### Step 1: Automated Setup

```bash
cd /home/user/.work/athena
./scripts/setup_phase5.sh
```

This starts PostgreSQL and llama.cpp automatically.

### Step 2: Verify Connection

```bash
python3 scripts/test_postgres_connection.py
```

Expected output:
```
======================================================================
PostgreSQL Database Connection Test
======================================================================

[1] Checking available backends...
   Available backends: ['sqlite', 'postgres']

[2] Creating database instance...
   Backend: PostgresDatabase

[3] Initializing database (creating schema)...
   ✓ Schema initialized

[4] Creating test project...
   ✓ Project created: test_connection_... (ID: 1)

[5] Storing test memory vector...
   ✓ Memory stored (ID: 1)

[6] Retrieving test memory...
   ✓ Memory retrieved:
     - Content: Test memory for connection...
     - Type: fact
     - Quality: 0.50

[7] Testing semantic search...
   ✓ Search successful, found 1 memories

[8] Testing hybrid search...
   ✓ Hybrid search successful, found 1 memories

[9] Testing task creation...
   ✓ Task created (ID: 1)

[10] Closing database connection...
   ✓ Connection closed

======================================================================
✅ All tests passed! PostgreSQL is working correctly.
======================================================================
```

### Step 3: Run Integration Tests

```bash
pytest tests/integration/test_postgres_database.py -v
```

Expected: 19 tests passing

---

## Detailed Setup Instructions

### Prerequisites

1. **Docker and Docker Compose**
   ```bash
   docker --version
   docker-compose --version
   ```

2. **Python 3.10+**
   ```bash
   python3 --version
   ```

3. **Virtual Environment**
   - Already at `.venv/` in project
   - Activate with: `source .venv/bin/activate`

### Installation Steps

#### 1. Install Dependencies

```bash
cd /home/user/.work/athena

# Activate virtual environment
source .venv/bin/activate

# Install everything (including PostgreSQL driver)
pip install -e ".[dev]"
```

Verify installation:
```bash
python3 -c "import psycopg; print(f'✓ psycopg {psycopg.__version__}')"
```

#### 2. Start PostgreSQL Services

```bash
cd /home/user/.work/athena

# Start PostgreSQL and llama.cpp
docker-compose up -d postgres llamacpp

# Wait 10-15 seconds for services to be ready

# Verify they're running
docker-compose ps

# Expected output:
# NAME                COMMAND                  SERVICE      STATUS
# athena-postgres     postgres                 postgres     Up (healthy)
# athena-llamacpp     llama-server             llamacpp     Up (healthy)
```

#### 3. Verify Schema Creation

PostgreSQL schema is initialized automatically from `scripts/init_postgres.sql`.

Verify it worked:
```bash
docker-compose exec postgres psql -U athena -d athena -c "
  SELECT COUNT(*) as table_count
  FROM information_schema.tables
  WHERE table_schema = 'public';
"

# Expected output: 10 (the 10 core tables)
```

#### 4. Test Python Connection

```bash
source .venv/bin/activate
python3 scripts/test_postgres_connection.py
```

All tests should pass ✅

#### 5. Run Full Test Suite

```bash
pytest tests/integration/test_postgres_database.py -v

# Expected: 19 passed in X.XXs
```

---

## Configuration

### Option 1: Environment Variables (Recommended)

Create `.env` file in project root:
```bash
cp .env.example .env
# Edit .env with your settings
```

Then load it:
```bash
source .env
```

Or automatically load in Python:
```python
from dotenv import load_dotenv
load_dotenv()
```

### Option 2: Direct Configuration

Pass parameters to `get_database()`:
```python
from athena.core.database_factory import get_database

db = get_database(
    backend='postgres',
    host='localhost',
    port=5432,
    dbname='athena',
    user='athena',
    password='athena_dev',
)
await db.initialize()
```

### Option 3: Docker Compose Defaults

Uses default settings from docker-compose.yml:
- Host: localhost
- Port: 5432
- Database: athena
- User: athena
- Password: athena_dev

---

## Testing

### Run Specific Test Category

```bash
# Test database setup
pytest tests/integration/test_postgres_database.py::TestPostgresDatabaseSetup -v

# Test memory operations
pytest tests/integration/test_postgres_database.py::TestMemoryVectorOperations -v

# Test hybrid search
pytest tests/integration/test_postgres_database.py::TestHybridSearch -v

# Test consolidation
pytest tests/integration/test_postgres_database.py::TestConsolidationOperations -v
```

### Run with Output

```bash
pytest tests/integration/test_postgres_database.py -v -s

# -v: verbose
# -s: show print statements
```

### Run with Coverage

```bash
pytest tests/integration/test_postgres_database.py --cov=src/athena/core/database_postgres
```

---

## Troubleshooting

### "psycopg module not found"

```bash
source .venv/bin/activate
pip install "psycopg[binary]>=3.1.0"
```

### PostgreSQL won't start

```bash
# Check if port 5432 is already in use
sudo lsof -i :5432

# Kill any existing containers
docker-compose down -v

# Restart
docker-compose up -d postgres llamacpp
```

### "Connection refused" to PostgreSQL

```bash
# Verify container is running
docker-compose ps postgres

# View logs
docker-compose logs postgres

# Wait longer for startup (can take 10-15 seconds)
sleep 10
docker-compose exec postgres pg_isready -U athena
```

### Tests fail with "pgvector extension not found"

```bash
# Verify schema was initialized
docker-compose exec postgres psql -U athena -d athena -c "CREATE EXTENSION vector;"

# Or reinitialize
docker-compose down -v
docker-compose up -d postgres llamacpp
sleep 10
```

### "too many connections"

Increase connection pool:
```bash
export ATHENA_POSTGRES_MAX_SIZE=20
```

Or reduce concurrency. Default is 10 connections.

---

## Verification Checklist

- [ ] Python 3.10+ installed
- [ ] Virtual environment active
- [ ] psycopg[binary] installed
- [ ] Docker and Docker Compose running
- [ ] PostgreSQL service started (port 5432)
- [ ] llama.cpp service started (port 8000)
- [ ] Schema initialized (10 tables)
- [ ] Python imports work
- [ ] Connection test passes
- [ ] Integration tests pass (19/19)

---

## Files Created/Modified

### Code Files
- ✅ `src/athena/core/database_postgres.py` (1,151 lines)
- ✅ `src/athena/core/database_factory.py` (231 lines)

### Test Files
- ✅ `tests/integration/test_postgres_database.py` (553 lines)

### Setup Files
- ✅ `scripts/setup_phase5.sh` (automated setup)
- ✅ `scripts/test_postgres_connection.py` (connection test)
- ✅ `.env.example` (configuration template)

### Configuration
- ✅ `pyproject.toml` (updated with psycopg dependency)
- ✅ `docker-compose.yml` (PostgreSQL + llama.cpp)
- ✅ `scripts/init_postgres.sql` (schema initialization)

### Documentation
- ✅ `PHASE5_SETUP_GUIDE.md` (this file)
- ✅ `PHASE5_DATABASE_IMPLEMENTATION.md` (reference)
- ✅ `PHASE5_COMPLETION_SUMMARY.md` (overview)
- ✅ `PHASE5_PART1_COMPLETION.md` (status)
- ✅ `PHASE5_DELIVERABLES.md` (detailed list)

---

## Next Steps

### For Immediate Use

```bash
# Start services
./scripts/setup_phase5.sh

# Test connection
python3 scripts/test_postgres_connection.py

# Run tests
pytest tests/integration/test_postgres_database.py -v
```

### For Integration (Phase 5 Part 2)

1. Update `src/athena/semantic/search.py` to use hybrid search
2. Update MCP handlers to use PostgreSQL layer
3. Integrate consolidation workflow
4. Create optimization guide

### For Production Deployment

1. Set up PostgreSQL on production server
2. Configure environment variables
3. Initialize schema
4. Run performance tests
5. Monitor connection pool usage

---

## Performance Verification

After setup, verify performance meets targets:

```python
import asyncio
import time
from athena.core.database_factory import get_database

async def benchmark():
    db = get_database()
    await db.initialize()

    # Create test data
    project = await db.create_project("benchmark", "/benchmark")
    embedding = [0.1] * 768

    # Benchmark hybrid search (should be 20-40ms)
    start = time.time()
    results = await db.hybrid_search(
        project_id=project.id,
        embedding=embedding,
        query_text="test",
        limit=10,
    )
    elapsed = (time.time() - start) * 1000

    print(f"Hybrid search: {elapsed:.1f}ms")
    assert elapsed < 100, f"Search too slow: {elapsed:.1f}ms"

    await db.close()

asyncio.run(benchmark())
```

---

## Summary

Everything is now set up and ready:

✅ **Dependencies installed**: psycopg[binary] 3.2.12
✅ **Modules importable**: All imports working
✅ **Configuration available**: `.env.example` for customization
✅ **Setup automated**: `setup_phase5.sh` script
✅ **Testing ready**: 19 integration tests prepared
✅ **Verification possible**: `test_postgres_connection.py` script

**Next: Phase 5 Part 2 - Integrate with memory layers**

