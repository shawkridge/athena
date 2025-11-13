# Installation Guide

## System Requirements

- **Python**: 3.10 or higher
- **Database**: PostgreSQL 12+ (local or remote)
- **OS**: Linux, macOS, or Windows
- **Memory**: 2GB minimum (4GB+ recommended)
- **Disk Space**: 500MB for dependencies + database

## Installation Steps

### 1. Clone the Repository

```bash
git clone https://github.com/anthropics/athena.git
cd athena
```

### 2. Create Virtual Environment

```bash
# Using venv (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Or using conda
conda create -n athena python=3.10
conda activate athena
```

### 3. Install Dependencies

```bash
# Development installation (includes testing tools)
pip install -e ".[dev]"

# Production installation (minimal dependencies)
pip install -e .

# For specific extras
pip install -e ".[rag]"        # Include RAG components
pip install -e ".[planning]"   # Include planning features
```

### 4. Configure Database

#### Option A: Local PostgreSQL (Default)

```bash
# Create database (if using local PostgreSQL)
createdb athena

# Set environment variables
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=athena
export DB_USER=postgres
export DB_PASSWORD=postgres
```

#### Option B: Remote Database

```bash
export DB_HOST=your-db-host.example.com
export DB_PORT=5432
export DB_NAME=athena
export DB_USER=your-user
export DB_PASSWORD=your-password
```

#### Option C: Environment File

Create `.env` in project root:

```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=athena
DB_USER=postgres
DB_PASSWORD=postgres
DB_MIN_POOL_SIZE=2
DB_MAX_POOL_SIZE=10
```

### 5. Verify Installation

```bash
# Run tests to verify everything works
pytest tests/unit/ -v -m "not benchmark" -k "test_" --co

# Run actual tests
pytest tests/unit/test_episodic_store.py -v
```

## Troubleshooting Installation

### PostgreSQL Connection Error

**Error**: `psycopg2.OperationalError: could not translate host name`

**Solution**:
```bash
# Verify PostgreSQL is running
pg_isready -h localhost -p 5432

# Check your connection settings
echo $DB_HOST $DB_PORT $DB_NAME $DB_USER
```

### ImportError: No module named 'athena'

**Error**: `ModuleNotFoundError: No module named 'athena'`

**Solution**:
```bash
# Reinstall in development mode
pip install -e .

# Verify PYTHONPATH if needed
export PYTHONPATH=/path/to/athena/src:$PYTHONPATH
```

### Version Conflicts

**Error**: `ERROR: pip's dependency resolver does not currently take into account all the packages...`

**Solution**:
```bash
# Update pip and setuptools
pip install --upgrade pip setuptools wheel

# Reinstall dependencies
pip install -e ".[dev]"
```

### Database Schema Issues

**Error**: Table or schema doesn't exist

**Solution**:
```bash
# Schemas are created automatically on first use
# If issues persist, verify database connection and permissions

# Check database exists
psql -l | grep athena

# Drop and recreate if needed (development only!)
dropdb athena
createdb athena
```

## Optional: Embedding Models

### Using Ollama (Local)

```bash
# Install Ollama from https://ollama.ai
ollama pull nomic-embed-text  # Or another embedding model

# Set environment variable
export EMBEDDING_PROVIDER=ollama
export OLLAMA_HOST=http://localhost:11434
```

### Using Anthropic (Cloud)

```bash
export EMBEDDING_PROVIDER=anthropic
export ANTHROPIC_API_KEY=your-api-key
```

### Using Mock (Development/Testing)

```bash
# Default for tests (no external dependencies)
export EMBEDDING_PROVIDER=mock
```

## Next Steps

1. **Read the Quick Start**: See [README.md](./README.md)
2. **Try a Tutorial**: Start with [tutorials/getting-started.md](./tutorials/getting-started.md)
3. **Explore the Architecture**: Read [ARCHITECTURE.md](./ARCHITECTURE.md)
4. **Run Tests**: `pytest tests/unit/ -v`

## Getting Help

- Check [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for common issues
- Review [DEVELOPMENT_GUIDE.md](./DEVELOPMENT_GUIDE.md) for development setup
- Open an issue on GitHub
- See [CONTRIBUTING.md](./CONTRIBUTING.md) for support channels

---

See [CONFIGURATION.md](./CONFIGURATION.md) for advanced configuration options.
