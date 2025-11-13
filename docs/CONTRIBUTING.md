# Contributing to Athena

Thank you for your interest in contributing to Athena! This guide will help you get started.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Code Style](#code-style)

## Code of Conduct

We are committed to providing a welcoming and inclusive environment for all contributors. Please be respectful and constructive in all interactions.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally
3. **Create a feature branch** from `develop`
4. **Make your changes** following the guidelines below
5. **Submit a pull request** to the `develop` branch

## Development Setup

### Prerequisites

- Python 3.10 or higher
- PostgreSQL (local or remote)
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/athena.git
cd athena

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"

# Verify installation
pytest tests/unit/ -v -m "not benchmark" --co
```

### Database Setup

Athena uses PostgreSQL. Configure your local connection:

```bash
# Set environment variables (or use defaults)
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=athena
export DB_USER=postgres
export DB_PASSWORD=postgres

# Or create .env file in project root
DB_HOST=localhost
DB_PORT=5432
DB_NAME=athena
DB_USER=postgres
DB_PASSWORD=postgres
```

## Making Changes

### Code Organization

Familiarize yourself with the project structure:

- `src/athena/` - Core source code (8 memory layers)
- `tests/` - Test suite (unit, integration, performance)
- `docs/` - Documentation
- `docs/tmp/` - Temporary working documents
- `docs/archive/` - Historical documentation

### Creating a Feature

1. **Create a branch** with a descriptive name:
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/your-feature-name
   ```

2. **Implement your changes** following the design patterns in ARCHITECTURE.md

3. **Update documentation** if your changes affect public APIs

4. **Add tests** for new functionality

### Refactoring

When refactoring existing code:

1. **Preserve backward compatibility** unless explicitly discussing breaking changes
2. **Update tests** to verify refactoring doesn't break functionality
3. **Document changes** in commit messages

## Testing

### Running Tests

```bash
# Fast feedback (skip benchmarks)
pytest tests/unit/ tests/integration/ -v -m "not benchmark"

# Full test suite
pytest tests/ -v --timeout=300

# Single test file
pytest tests/unit/test_episodic_store.py -v

# With coverage
pytest tests/ --cov=src/athena --cov-report=html

# Watch mode (requires pytest-watch)
ptw tests/unit/ -- -v -m "not benchmark"
```

### Writing Tests

Follow the pattern in existing tests:

```python
import pytest
from athena.core.database import Database
from athena.episodic.store import EpisodicStore

@pytest.fixture
def db(tmp_path):
    """Create test database."""
    db_path = tmp_path / "test.db"
    return Database(str(db_path))

@pytest.fixture
def episodic_store(db):
    """Create episodic store."""
    return EpisodicStore(db)

class TestEpisodicStore:
    def test_store_event(self, episodic_store):
        """Test storing an event."""
        event_id = episodic_store.store_event(...)
        assert event_id is not None

        event = episodic_store.get_event(event_id)
        assert event is not None
```

### Test Coverage

Target coverage:
- **Core layers** (`episodic/`, `semantic/`, etc.): ≥90%
- **Overall project**: ≥65%

Run coverage report:
```bash
pytest tests/ --cov=src/athena --cov-report=html
open htmlcov/index.html  # Or open in your browser
```

## Submitting Changes

### Before You Submit

1. **Ensure tests pass**:
   ```bash
   pytest tests/unit/ tests/integration/ -v -m "not benchmark"
   ```

2. **Check code style**:
   ```bash
   black src/ tests/
   ruff check --fix src/ tests/
   mypy src/athena
   ```

3. **Update CHANGELOG.md** with your changes

4. **Commit with clear messages**:
   ```bash
   git commit -m "feat: Add new feature

   Description of what this feature does and why it's needed.

   Fixes #123  # Reference related issue
   ```

### Pull Request Process

1. **Push your branch**:
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Open a PR** on GitHub with:
   - Clear title and description
   - Reference to related issues
   - Summary of changes
   - Test coverage details

3. **Respond to feedback** promptly

4. **Wait for approval** from a maintainer

## Code Style

### Python Style Guide

We follow PEP 8 with some customizations:

- **Line length**: 100 characters (black default)
- **Quotes**: Double quotes for strings
- **Imports**: Organized by type (stdlib, third-party, local)

### Enforced Tools

```bash
# Auto-format code
black src/ tests/

# Check and fix linting issues
ruff check --fix src/ tests/

# Type checking (strict mode)
mypy src/athena

# All at once
black src/ tests/ && ruff check --fix src/ tests/ && mypy src/athena
```

### Naming Conventions

- **Classes**: `PascalCase` (e.g., `EpisodicStore`)
- **Functions/Methods**: `snake_case` (e.g., `store_event`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `MAX_BUFFER_SIZE`)
- **Private methods**: Leading underscore (e.g., `_init_schema`)

### Documentation

Document your code:

```python
def store_event(self, event: EpisodicEvent) -> int:
    """Store an event to episodic memory.

    Args:
        event: The event to store.

    Returns:
        The ID of the stored event.

    Raises:
        ValueError: If event is invalid.
    """
```

## Questions?

- Check the [Architecture Guide](./ARCHITECTURE.md)
- Review [Development Guide](./DEVELOPMENT_GUIDE.md)
- Open an issue with your question
- Reach out to maintainers

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.

---

**Thank you for contributing to Athena!**
