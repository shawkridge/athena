# Development Guide

Complete guide to setting up your development environment and contributing to Athena.

## Table of Contents

- [Setup](#setup)
- [Project Structure](#project-structure)
- [Development Workflow](#development-workflow)
- [Code Quality](#code-quality)
- [Testing](#testing)
- [Debugging](#debugging)

## Setup

### Prerequisites

```bash
# Check Python version (3.10+)
python --version

# Install system dependencies
# macOS
brew install postgresql

# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib

# Windows
# Download from https://www.postgresql.org/download/windows/
```

### Initial Setup

```bash
# Clone and enter directory
git clone https://github.com/anthropics/athena.git
cd athena

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate

# Install in development mode with all extras
pip install -e ".[dev]"

# Verify installation
pytest --version
black --version
ruff --version
```

### Database Setup

```bash
# Start PostgreSQL
# macOS: brew services start postgresql
# Linux: sudo systemctl start postgresql

# Create development database
createdb athena_dev

# Configure connection
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=athena_dev
export DB_USER=postgres
export DB_PASSWORD=postgres
```

## Project Structure

```
athena/
├── src/athena/           # Main source code
│   ├── episodic/         # Layer 1: Event storage
│   ├── semantic/         # Layer 2: Knowledge representation
│   ├── procedural/       # Layer 3: Workflow learning
│   ├── prospective/      # Layer 4: Task management
│   ├── graph/            # Layer 5: Knowledge graph
│   ├── meta/             # Layer 6: Meta-memory
│   ├── consolidation/    # Layer 7: Pattern extraction
│   ├── rag/              # Layer 8: Advanced retrieval
│   ├── planning/         # Planning features
│   ├── mcp/              # MCP server interface
│   └── core/             # Database, config, base classes
│
├── tests/                # Test suite
│   ├── unit/             # Unit tests for each layer
│   ├── integration/      # Cross-layer tests
│   ├── performance/      # Benchmark tests
│   ├── mcp/              # MCP server tests
│   └── fixtures/         # Shared test fixtures
│
├── docs/                 # Documentation
│   ├── tmp/              # Temporary working docs
│   ├── archive/          # Historical docs
│   └── tutorials/        # Tutorials and guides
│
└── pyproject.toml        # Project configuration
```

## Development Workflow

### Before Starting

```bash
# Update to latest develop branch
git checkout develop
git pull origin develop

# Create feature branch
git checkout -b feature/your-feature-name
```

### Making Changes

1. **Write failing test first** (TDD):
   ```bash
   pytest tests/unit/test_your_feature.py::test_new_feature -v
   ```

2. **Implement the feature**:
   ```bash
   # Edit src/athena/[layer]/your_feature.py
   vim src/athena/episodic/your_feature.py
   ```

3. **Run tests to verify**:
   ```bash
   pytest tests/unit/ -v -m "not benchmark"
   ```

4. **Check code quality**:
   ```bash
   black src/ tests/
   ruff check --fix src/ tests/
   mypy src/athena
   ```

### Committing Changes

```bash
# Stage your changes
git add src/athena/episodic/your_feature.py tests/unit/test_your_feature.py

# Create descriptive commit
git commit -m "feat: Add new feature for episodic memory

- Description of what the feature does
- Why it was needed
- Any important implementation notes

Fixes #123"
```

### Submitting a Pull Request

```bash
# Push your branch
git push origin feature/your-feature-name

# Create PR on GitHub with:
# - Clear title and description
# - Reference to related issues
# - Test coverage details
```

## Code Quality

### Formatting

```bash
# Auto-format Python code (line length: 100)
black src/ tests/

# Check what would change
black --check src/ tests/
```

### Linting

```bash
# Check and fix linting issues
ruff check --fix src/ tests/

# View issues without fixing
ruff check src/ tests/
```

### Type Checking

```bash
# Strict type checking
mypy src/athena

# Check specific file
mypy src/athena/episodic/storage.py
```

### Run All Quality Checks

```bash
# All at once
black src/ tests/ && ruff check --fix src/ tests/ && mypy src/athena

# Or use pre-commit hook
pip install pre-commit
pre-commit run --all-files
```

## Testing

### Running Tests

```bash
# Fast feedback (unit + integration, no benchmarks)
pytest tests/unit/ tests/integration/ -v -m "not benchmark"

# Full test suite (includes benchmarks)
pytest tests/ -v --timeout=300

# Single test file
pytest tests/unit/test_episodic_store.py -v

# Single test with output
pytest tests/unit/test_episodic_store.py::TestEpisodicStore::test_store_event -v -s

# With coverage report
pytest tests/ --cov=src/athena --cov-report=html
```

### Writing Tests

```python
import pytest
from athena.core.database import Database
from athena.episodic.store import EpisodicStore

@pytest.fixture
def db(tmp_path):
    """Create isolated test database."""
    db_path = tmp_path / "test.db"
    return Database(str(db_path))

@pytest.fixture
def episodic_store(db):
    """Create episodic store with schema."""
    return EpisodicStore(db)

class TestEpisodicStore:
    def test_store_event(self, episodic_store):
        """Test storing an event to episodic memory."""
        # Arrange
        event = EpisodicEvent(...)

        # Act
        event_id = episodic_store.store_event(event)

        # Assert
        assert event_id is not None
        assert episodic_store.get_event(event_id) is not None
```

### Test Organization

- **Unit tests**: Test single functions/classes in isolation
- **Integration tests**: Test interactions between layers
- **Performance tests**: Benchmark critical operations
- **MCP tests**: Test MCP tool invocations

### Coverage Goals

- **Core layers** (episodic, semantic, etc.): ≥90%
- **MCP handlers**: ≥60%
- **Overall project**: ≥65%

## Debugging

### Enable Debug Logging

```bash
# Run tests with detailed output
DEBUG=1 pytest tests/unit/ -v -s

# Or set in Python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Using Python Debugger

```python
# Add breakpoint in code
def my_function():
    x = 10
    breakpoint()  # Execution pauses here
    return x
```

```bash
# Run tests to hit breakpoint
pytest tests/unit/test_something.py -v -s
```

### Inspect Database

```python
import asyncio
from athena.core.database import Database

async def inspect():
    db = Database()
    await db.initialize()

    # List all tables
    tables = await db.execute(
        "SELECT table_name FROM information_schema.tables"
    )

    # Query specific table
    events = await db.execute(
        "SELECT * FROM episodic_events LIMIT 10"
    )

    print(events)

asyncio.run(inspect())
```

### Check Memory Health

```bash
# If MCP server is running
/memory-health --detail

# Or query directly from Python
from athena.manager import UnifiedMemoryManager
manager = UnifiedMemoryManager()
health = manager.get_health()
print(health)
```

## Quick Reference

```bash
# Start development
source venv/bin/activate
export DB_HOST=localhost DB_NAME=athena_dev

# Run fast tests
pytest tests/unit/ tests/integration/ -v -m "not benchmark"

# Format and lint
black src/ tests/ && ruff check --fix src/ tests/ && mypy src/athena

# Create commit
git add . && git commit -m "feat: Your feature"

# Push branch
git push origin feature/your-branch

# Create PR on GitHub
# - Set base branch to 'develop'
# - Add description and related issues
# - Request review from maintainers
```

---

See [CONTRIBUTING.md](./CONTRIBUTING.md) for contribution guidelines.
See [TESTING_GUIDE.md](./TESTING_GUIDE.md) for detailed testing documentation.
