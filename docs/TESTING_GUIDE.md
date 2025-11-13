# Testing Guide

Comprehensive guide to testing Athena's memory system.

## Overview

Athena's test suite is organized into layers:

| Layer | Tests | Location | Coverage |
|-------|-------|----------|----------|
| Unit | Individual layer validation | `tests/unit/` | 90%+ |
| Integration | Cross-layer coordination | `tests/integration/` | 70%+ |
| Performance | Benchmark operations | `tests/performance/` | Key paths |
| MCP | Tool invocation | `tests/mcp/` | 60%+ |

## Quick Start

```bash
# Run fast tests (unit + integration, no benchmarks)
pytest tests/unit/ tests/integration/ -v -m "not benchmark"

# Run full suite
pytest tests/ -v --timeout=300

# Run with coverage
pytest tests/ --cov=src/athena --cov-report=html
```

## Test Organization

### Unit Tests

Located in `tests/unit/`, organized by layer:

```
tests/unit/
├── test_episodic_store.py      # Layer 1: Episodic memory
├── test_semantic_store.py      # Layer 2: Semantic memory
├── test_procedural_store.py    # Layer 3: Procedural memory
├── test_prospective_store.py   # Layer 4: Prospective memory
├── test_graph_store.py         # Layer 5: Knowledge graph
├── test_meta_store.py          # Layer 6: Meta-memory
├── test_consolidation.py       # Layer 7: Consolidation
└── test_manager.py             # Unified memory manager
```

**What to test**:
- CRUD operations (Create, Read, Update, Delete)
- Input validation (invalid data, edge cases)
- Error handling (graceful failures)
- Schema initialization

**Example**:
```python
class TestEpisodicStore:
    def test_store_event_success(self, episodic_store):
        """Test storing valid event."""
        event = EpisodicEvent(...)
        event_id = episodic_store.store_event(event)
        assert event_id is not None

    def test_store_event_invalid_input(self, episodic_store):
        """Test storing invalid event."""
        with pytest.raises(ValueError):
            episodic_store.store_event(None)
```

### Integration Tests

Located in `tests/integration/`, tests cross-layer functionality:

```
tests/integration/
├── test_consolidation_integration.py  # Episodic → Semantic
├── test_manager_routing.py            # Query routing across layers
├── test_rag_integration.py            # RAG with all layers
└── test_e2e_workflow.py               # End-to-end scenarios
```

**What to test**:
- Layer interactions (e.g., episodic events → consolidation → semantic memory)
- Query routing (manager selecting correct layer)
- Complete workflows (remember → recall → consolidate)

**Example**:
```python
class TestConsolidationIntegration:
    async def test_consolidation_workflow(self, manager, episodic_store):
        """Test full consolidation pipeline."""
        # Store events
        for i in range(10):
            event = create_event(...)
            await episodic_store.store_event(event)

        # Consolidate
        patterns = await manager.consolidate()

        # Verify semantic memory updated
        semantic_memories = await manager.search("pattern")
        assert len(semantic_memories) > 0
```

### Performance Tests

Located in `tests/performance/`, marked with `@pytest.mark.benchmark`:

```bash
# Run only performance tests
pytest tests/performance/ -v --benchmark-only

# Compare with baseline
pytest tests/performance/ -v --benchmark-compare
```

**What to benchmark**:
- Semantic search latency (<100ms)
- Event insertion throughput (2000+ events/sec)
- Graph queries (<50ms)
- Consolidation time (1000 events <5s)

**Example**:
```python
@pytest.mark.benchmark
class TestSemanticSearchPerformance:
    def test_semantic_search_latency(self, benchmark, semantic_store):
        """Benchmark semantic search speed."""
        result = benchmark(semantic_store.search, "query", limit=10)
        assert len(result) <= 10
```

### MCP Tests

Located in `tests/mcp/`, tests MCP tool invocations:

```bash
# Run MCP tests only
pytest tests/mcp/ -v
```

**What to test**:
- Tool parameter validation
- Tool response format
- Error handling in tools
- Tool integration with layers

## Writing Tests

### Basic Structure

```python
import pytest
from athena.core.database import Database
from athena.episodic.store import EpisodicStore

@pytest.fixture
def db(tmp_path):
    """Create isolated test database."""
    return Database(str(tmp_path / "test.db"))

@pytest.fixture
def episodic_store(db):
    """Create episodic store."""
    return EpisodicStore(db)

class TestEpisodicStore:
    def test_something(self, episodic_store):
        """Test description."""
        # Arrange
        expected = ...

        # Act
        result = episodic_store.some_operation()

        # Assert
        assert result == expected
```

### Test Naming Convention

```python
# Good names
def test_store_event_with_valid_data():
def test_store_event_raises_on_invalid_data():
def test_semantic_search_returns_top_k_results():
def test_consolidation_creates_semantic_memories():

# Bad names
def test_1():
def test_something_works():
def test_func():
```

### Using Fixtures

Fixtures are defined in conftest.py or test files:

```python
@pytest.fixture
def sample_event():
    """Create sample episodic event."""
    return EpisodicEvent(
        title="Test event",
        description="Test description",
        timestamp=datetime.now(),
        tags=["test"],
    )

def test_with_fixture(episodic_store, sample_event):
    """Test using fixture."""
    event_id = episodic_store.store_event(sample_event)
    assert event_id is not None
```

### Testing Async Code

```python
@pytest.mark.asyncio
async def test_async_operation(episodic_store):
    """Test async operation."""
    result = await episodic_store.async_search("query")
    assert result is not None
```

### Testing Error Cases

```python
def test_store_event_with_none():
    """Test proper error on invalid input."""
    store = EpisodicStore(db)
    with pytest.raises(ValueError, match="Event cannot be None"):
        store.store_event(None)
```

## Running Tests

### Common Commands

```bash
# All tests
pytest tests/ -v

# Specific directory
pytest tests/unit/ -v

# Specific file
pytest tests/unit/test_episodic_store.py -v

# Specific test class
pytest tests/unit/test_episodic_store.py::TestEpisodicStore -v

# Specific test
pytest tests/unit/test_episodic_store.py::TestEpisodicStore::test_store_event -v

# With output/debugging
pytest tests/unit/ -v -s  # -s shows print statements

# Stop on first failure
pytest tests/ -v -x

# Run last failed tests
pytest tests/ -v --lf

# Run tests matching pattern
pytest tests/ -v -k "semantic"  # Only semantic-related tests

# Exclude benchmarks
pytest tests/ -v -m "not benchmark"
```

### Coverage

```bash
# Generate coverage report
pytest tests/ --cov=src/athena --cov-report=html

# View report in browser
open htmlcov/index.html

# Show coverage for specific file
pytest tests/ --cov=src/athena/episodic --cov-report=term-missing

# Set minimum coverage threshold
pytest tests/ --cov=src/athena --cov-fail-under=80
```

## Best Practices

### ✅ Do

- **Test behavior, not implementation**: Test what the function does, not how it does it
- **Use descriptive names**: `test_store_event_returns_valid_id()` not `test_1()`
- **Isolate tests**: Each test should be independent
- **Use fixtures**: Share setup code with `@pytest.fixture`
- **Test edge cases**: Empty data, None, negative numbers, etc.
- **Keep tests fast**: Unit tests should complete in <100ms each
- **Group related tests**: Use test classes to organize related tests

### ❌ Don't

- **Test private methods**: Only test public APIs
- **Hardcode paths**: Use `tmp_path` fixture for temporary files
- **Leave debugging code**: Remove `print()` and `breakpoint()` before committing
- **Create side effects**: Tests shouldn't modify global state
- **Ignore failures**: Fix failing tests immediately, don't skip them
- **Test external services**: Mock external dependencies
- **Write brittle tests**: Avoid testing implementation details

## Continuous Integration

Tests are run automatically on:
- **Pre-commit**: Local validation before committing
- **Pull Request**: Verify changes don't break existing tests
- **Main branch**: Regression testing before release

## Performance Targets

Target metrics for important operations:

| Operation | Target | Current | Status |
|-----------|--------|---------|--------|
| Semantic search | <100ms | ~50-80ms | ✅ |
| Graph query | <50ms | ~30-40ms | ✅ |
| Event insertion | 2000+ events/sec | ~1500-2000/sec | ⚠️ |
| Consolidation (1000 events) | <5s | ~2-3s | ✅ |

Monitor performance with:
```bash
pytest tests/performance/ -v --benchmark-only
```

## Debugging Test Failures

```bash
# Run with verbose output
pytest tests/unit/test_episodic_store.py -vv

# Show local variables on failure
pytest tests/unit/ -l

# Show print statements
pytest tests/unit/ -s

# Drop into debugger on failure
pytest tests/unit/ --pdb

# Show durations of slowest tests
pytest tests/unit/ --durations=10
```

## Troubleshooting

### Database Connection Issues

```bash
# Verify PostgreSQL is running
pg_isready -h localhost -p 5432

# Check DB_* environment variables
echo $DB_HOST $DB_PORT $DB_NAME $DB_USER
```

### Import Errors

```bash
# Reinstall package
pip install -e .

# Verify PYTHONPATH
export PYTHONPATH=/path/to/athena/src:$PYTHONPATH
```

### Test Timeouts

```bash
# Run with longer timeout
pytest tests/ --timeout=600

# Or mark test as slow
@pytest.mark.slow
def test_slow_operation():
    pass

# Then run without slow tests
pytest tests/ -m "not slow"
```

---

For more information, see:
- [CONTRIBUTING.md](./CONTRIBUTING.md) - Code contribution guidelines
- [DEVELOPMENT_GUIDE.md](./DEVELOPMENT_GUIDE.md) - Development setup
- [pytest documentation](https://docs.pytest.org/)
