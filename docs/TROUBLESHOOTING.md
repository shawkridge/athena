# Troubleshooting Guide

Solutions for common issues in Athena.

## Table of Contents

- [Installation Issues](#installation-issues)
- [Database Issues](#database-issues)
- [Embedding Issues](#embedding-issues)
- [Memory Operations](#memory-operations)
- [Search Issues](#search-issues)
- [Consolidation Issues](#consolidation-issues)
- [Performance Issues](#performance-issues)
- [Development Issues](#development-issues)

---

## Installation Issues

### ImportError: No module named 'athena'

**Problem**: Python can't find the athena package.

**Solution**:
```bash
# Reinstall in development mode
pip install -e .

# Or set PYTHONPATH manually
export PYTHONPATH=/path/to/athena/src:$PYTHONPATH

# Verify installation
python -c "import athena; print(athena.__version__)"
```

### ModuleNotFoundError: No module named 'psycopg2'

**Problem**: PostgreSQL driver not installed.

**Solution**:
```bash
# Install PostgreSQL dependencies
pip install -e ".[dev]"  # All dependencies

# Or just database dependencies
pip install psycopg2-binary asyncpg
```

### Virtual Environment Issues

**Problem**: Dependencies not found after creating venv.

**Solution**:
```bash
# Recreate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Reinstall
pip install -e ".[dev]"
```

---

## Database Issues

### PostgreSQL Connection Error

**Error**: `psycopg2.OperationalError: could not translate host name`

**Solutions**:

1. **Verify PostgreSQL is running**:
```bash
pg_isready -h localhost -p 5432
# Should output: accepting connections
```

2. **Check credentials**:
```bash
psql -h localhost -U postgres -d athena
# Should connect successfully
```

3. **Check environment variables**:
```bash
echo "Host: $DB_HOST"
echo "Port: $DB_PORT"
echo "User: $DB_USER"
echo "Database: $DB_NAME"
```

4. **Verify firewall**:
```bash
# Check if port 5432 is accessible
nc -zv localhost 5432
```

### Database Table Already Exists

**Error**: `ProgrammingError: relation already exists`

**Solution**:
```bash
# For testing - drop and recreate
dropdb athena_test
createdb athena_test

# For production - migration needed
# Tables are created automatically on first use
# Just drop tables, don't drop database
psql -d athena -c "DROP TABLE IF EXISTS episodic_events CASCADE;"
```

### Connection Pool Exhausted

**Error**: `QueuePool overflow: The pool size has been exceeded`

**Solutions**:
```bash
# Increase pool size
export DB_MAX_POOL_SIZE=20

# Or reduce concurrent connections
# Check active connections:
psql -d athena -c "SELECT count(*) FROM pg_stat_activity;"

# Kill idle connections:
psql -d athena -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state='idle';"
```

### Timeout During Query

**Error**: `asyncio.TimeoutError` or `DatabaseError: query timeout`

**Solutions**:
```bash
# Increase timeout
export DB_QUERY_TIMEOUT=60

# Or optimize the query
# Check slow queries
psql -d athena -c "SELECT query, calls, total_time FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;"

# Create indexes if missing
psql -d athena -c "CREATE INDEX ON episodic_events(tags);"
```

---

## Embedding Issues

### Ollama Connection Failed

**Error**: `ConnectionError: Failed to connect to http://localhost:11434`

**Solutions**:

1. **Start Ollama**:
```bash
ollama serve
# Should output: Serving on http://localhost:11434
```

2. **Check Ollama is running**:
```bash
curl http://localhost:11434/api/tags
# Should return JSON with available models
```

3. **Verify model exists**:
```bash
ollama list
# Should show models like nomic-embed-text

# If missing, download it
ollama pull nomic-embed-text
```

4. **Check network**:
```bash
# Verify Ollama is accessible
nc -zv localhost 11434
```

### Anthropic API Key Invalid

**Error**: `AuthenticationError: Invalid API key`

**Solutions**:
```bash
# Verify API key format
echo $ANTHROPIC_API_KEY | head -c 20
# Should start with: sk-ant-v0-

# Test API key
python -c "
import anthropic
client = anthropic.Anthropic(api_key='$ANTHROPIC_API_KEY')
try:
    client.messages.create(model='claude-3-5-sonnet', messages=[{'role': 'user', 'content': 'test'}])
    print('✅ API key valid')
except Exception as e:
    print(f'❌ Error: {e}')
"

# Check for invalid characters
# API key should not contain quotes or special chars
```

### Embedding Dimension Mismatch

**Error**: `ValueError: Vector dimension mismatch`

**Solution**:
```bash
# Embeddings must have consistent dimensions
# Ollama: typically 768 or 1024
# Anthropic: typically 1024

# Check current embeddings
python -c "
from athena.semantic.embeddings import EmbeddingManager
em = EmbeddingManager()
test_embedding = em.embed('test')
print(f'Embedding dimension: {len(test_embedding)}')
"

# If changing providers, need to re-embed all memories
```

---

## Memory Operations

### Event Not Found

**Error**: `ValueError: Event {id} not found`

**Solutions**:
```bash
# Verify event exists
python -c "
from athena.episodic.store import EpisodicStore
from athena.core.database import Database
db = Database()
store = EpisodicStore(db)
event = store.get_event(123)
if event:
    print(f'Event found: {event.title}')
else:
    print('Event not found - check ID')
"

# List events to find valid IDs
# python -c "from athena.episodic.store import EpisodicStore; store = EpisodicStore(); events = store.search_by_tag('test'); print([e.id for e in events])"
```

### Memory Not Stored

**Error**: `ValueError: Failed to store memory`

**Solutions**:
```bash
# Check database connection
python -c "
from athena.core.database import Database
db = Database()
health = db.get_health()
print(f'Database health: {health}')
"

# Verify required fields
# - content (required)
# - domain (optional)
# - importance (optional, 0-1)

# Try storing directly
python -c "
from athena.semantic.store import SemanticStore
from athena.core.database import Database
store = SemanticStore(Database())
try:
    id = store.store_memory('Test content', domain='test', importance=0.5)
    print(f'✅ Memory stored: {id}')
except Exception as e:
    print(f'❌ Error: {e}')
"
```

---

## Search Issues

### No Search Results

**Problem**: Search returns empty results for valid queries.

**Solutions**:

1. **Check memories exist**:
```bash
python -c "
from athena.semantic.store import SemanticStore
from athena.core.database import Database
store = SemanticStore(Database())
count = store.count_memories()
print(f'Total memories: {count}')
"
```

2. **Try broader search**:
```bash
# Original query: too specific
results = store.search('consolidation algorithm')

# Broader query: should match more
results = store.search('consolidation')  # Just the main word

# With higher limit
results = store.search('consolidation', limit=100)
```

3. **Check domain filter**:
```bash
# If using domain filter, make sure it matches
results = store.search('consolidation', domain='learning')
# vs
results = store.search('consolidation', domain=None)  # No filter
```

4. **Verify embeddings are working**:
```bash
python -c "
from athena.semantic.embeddings import EmbeddingManager
em = EmbeddingManager()
embedding = em.embed('test query')
print(f'Embedding length: {len(embedding)}')
print(f'First 5 values: {embedding[:5]}')
"
```

### Search Very Slow

**Problem**: Search taking >1 second.

**Solutions**:

1. **Check cache status**:
```bash
python -c "
from athena.semantic.cache import SearchCache
cache = SearchCache()
stats = cache.stats()
print(f'Cache hit rate: {stats[\"hit_rate\"]}')
print(f'Cache size: {stats[\"size\"]}')
"
```

2. **Add database indexes**:
```bash
psql -d athena -c "
CREATE INDEX ON semantic_memories(domain);
CREATE INDEX ON semantic_memories(importance);
"
```

3. **Optimize embeddings**:
```bash
# If using Anthropic, might be slow
# Try Ollama locally instead
export EMBEDDING_PROVIDER=ollama
```

---

## Consolidation Issues

### Consolidation Hangs

**Error**: Consolidation takes forever without completing.

**Solutions**:

1. **Check process**:
```bash
# See if consolidation is running
ps aux | grep consolidation

# Check database for locks
psql -d athena -c "SELECT * FROM pg_locks WHERE NOT granted;"
```

2. **Use speed strategy**:
```bash
python -c "
from athena.consolidation.consolidator import Consolidator
from athena.core.database import Database
c = Consolidator(Database())
patterns = c.consolidate(strategy='speed')
print(f'Extracted {len(patterns)} patterns')
"
```

3. **Reduce event range**:
```bash
# Original: last 30 days
patterns = c.consolidate(days_back=30)

# Faster: last 7 days
patterns = c.consolidate(days_back=7)

# Test: last 1 day
patterns = c.consolidate(days_back=1)
```

### Low Quality Patterns

**Problem**: Extracted patterns are obvious or low-quality.

**Solutions**:

1. **Use quality strategy**:
```bash
python -c "
from athena.consolidation.consolidator import Consolidator
c = Consolidator()
# Instead of 'balanced', use 'quality'
patterns = c.consolidate(strategy='quality')
"
```

2. **Increase cluster size**:
```bash
# Original: min 2 events per cluster
patterns = c.consolidate(min_cluster_size=2)

# Stricter: min 5 events per cluster
patterns = c.consolidate(min_cluster_size=5)
```

3. **Use LLM validation**:
```bash
# Consolidator automatically validates uncertain patterns with LLM
# Make sure LLM provider is configured
export LLM_PROVIDER=anthropic
export ANTHROPIC_API_KEY=sk-ant-v0-xxxxx
```

---

## Performance Issues

### High Memory Usage

**Problem**: Python process using excessive memory.

**Solutions**:

1. **Clear cache**:
```bash
python -c "
from athena.semantic.cache import SearchCache
cache = SearchCache()
cache.clear()
print('Cache cleared')
"
```

2. **Reduce cache size**:
```bash
export CACHE_SIZE=100  # Instead of default 1000
```

3. **Check for memory leaks**:
```bash
# Monitor memory over time
import psutil
import time

process = psutil.Process()
for _ in range(10):
    from athena.semantic.store import SemanticStore
    store = SemanticStore()
    store.search('test')
    print(f'Memory: {process.memory_info().rss / 1024 / 1024:.1f} MB')
    time.sleep(1)
```

### Slow Database Queries

**Problem**: Database operations taking >100ms.

**Solutions**:

1. **Enable query logging**:
```bash
export LOG_SQL=1
export LOG_LEVEL=DEBUG

# See which queries are slow
python -c "
from athena.core.database import Database
db = Database()
# Run your operation
# Check logs for slow queries
"
```

2. **Analyze query plan**:
```bash
psql -d athena -c "EXPLAIN ANALYZE SELECT * FROM episodic_events WHERE tags @> '{learning}';"
```

3. **Add missing indexes**:
```bash
psql -d athena -c "
CREATE INDEX ON episodic_events(tags);
CREATE INDEX ON episodic_events(timestamp);
CREATE INDEX ON semantic_memories(domain);
"
```

---

## Development Issues

### Tests Failing

**Error**: `AssertionError` or `FAILED` in test output.

**Solutions**:

1. **Check fresh database**:
```bash
# Tests should use isolated database
pytest tests/unit/test_something.py -v --tb=short

# If needed, clear test database
dropdb athena_test 2>/dev/null || true
createdb athena_test
```

2. **Check Python version**:
```bash
python --version  # Should be 3.10+
# If older, upgrade: python3.10 or higher required
```

3. **Run with debug output**:
```bash
pytest tests/unit/test_something.py -v -s --tb=long
```

### Import Errors in Tests

**Error**: `ModuleNotFoundError` when running tests.

**Solution**:
```bash
# Make sure package is installed
pip install -e .

# Set PYTHONPATH if needed
export PYTHONPATH=/path/to/athena/src:$PYTHONPATH

# Run tests with correct path
python -m pytest tests/unit/
```

### Linting Errors

**Problem**: `black` or `ruff` complains about code.

**Solutions**:
```bash
# Auto-fix most issues
black src/ tests/
ruff check --fix src/ tests/

# Check remaining issues
ruff check src/ tests/
mypy src/athena
```

---

## Getting Help

### Debug Information to Collect

When reporting an issue, include:

1. **Version info**:
```bash
python --version
pip show athena | grep Version
psql --version
```

2. **Configuration**:
```bash
echo "DB_HOST=$DB_HOST"
echo "EMBEDDING_PROVIDER=$EMBEDDING_PROVIDER"
echo "LOG_LEVEL=$LOG_LEVEL"
```

3. **Error log**:
```bash
# Run with debug logging
DEBUG=1 python your_script.py 2>&1 | tee error.log
```

4. **System info**:
```bash
uname -a
```

### Support Resources

- **Documentation**: See [INDEX.md](./INDEX.md) for all docs
- **Examples**: Check [EXAMPLES.md](./EXAMPLES.md) for code samples
- **API Reference**: See [API_REFERENCE.md](./API_REFERENCE.md) for all operations
- **Issues**: Report bugs on GitHub with debug info above

---

**Version**: 1.0
**Last Updated**: November 13, 2025
**Status**: Comprehensive Guide
