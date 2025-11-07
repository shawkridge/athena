# Semantic Code Search Backend - Setup Instructions

Complete guide for setting up and managing the Semantic Code Search Python backend.

---

## Prerequisites

- **Python**: 3.8 or later
- **pip**: Python package manager
- **Operating System**: Linux, macOS, or Windows
- **Disk Space**: ~500MB for dependencies + index
- **RAM**: 200MB+ (varies with workspace size)

### Verify Prerequisites

```bash
# Check Python version
python --version  # Should be 3.8+

# Check pip
pip --version

# Check available disk space
df -h  # Linux/macOS
fsutil volume diskfree C:  # Windows
```

---

## Installation Methods

### Method 1: Full Athena Installation (Recommended)

Install the complete Athena system with semantic code search:

```bash
# Navigate to Athena directory
cd /path/to/athena

# Install in development mode
pip install -e .

# Or install in production mode
pip install .
```

**What this includes**:
- ✅ Semantic code search backend
- ✅ All code parsers (Python, JS, TS, Java, Go)
- ✅ RAG strategies (Self-RAG, Corrective RAG, Adaptive RAG)
- ✅ MCP memory system (optional, not needed for code search)

**File size**: ~200-300MB after dependencies

### Method 2: Standalone Installation

Install just the semantic code search backend:

```bash
# Install from PyPI (when available)
pip install semantic-code-search

# Or from GitHub
pip install git+https://github.com/anthropic/semantic-code-search.git
```

**What this includes**:
- ✅ Code search backend only
- ✅ All dependencies for search
- ❌ Athena memory system (not included)

**File size**: ~150-200MB after dependencies

### Method 3: Development Installation

For contributing to the project:

```bash
# Clone repository
git clone https://github.com/anthropic/semantic-code-search.git
cd semantic-code-search

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode with test dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v
```

---

## Virtual Environment Setup (Recommended)

Isolate the backend from system Python:

### Linux/macOS

```bash
# Create virtual environment
python3.10 -m venv ~/.semantic-search/venv

# Activate it
source ~/.semantic-search/venv/bin/activate

# Install backend
pip install semantic-code-search

# Or from Athena
cd /path/to/athena
pip install -e .
```

### Windows

```bash
# Create virtual environment
python -m venv %USERPROFILE%\.semantic-search\venv

# Activate it
%USERPROFILE%\.semantic-search\venv\Scripts\activate

# Install backend
pip install semantic-code-search
```

### Make Activation Easy

Create a shell alias or batch script:

**Linux/macOS** (add to ~/.bashrc or ~/.zshrc):
```bash
alias semantic-search='source ~/.semantic-search/venv/bin/activate'
```

**Windows** (create `C:\semantic-search.bat`):
```batch
@echo off
call %USERPROFILE%\.semantic-search\venv\Scripts\activate
```

---

## Configuration

### Environment Variables

```bash
# Backend port (default: 5000)
export BACKEND_PORT=5000

# Python path (default: python)
export PYTHON_PATH=/usr/bin/python3.10

# Embedding provider: mock | ollama | anthropic
export EMBEDDING_PROVIDER=mock

# Embedding quality (dimension)
export EMBEDDING_DIMENSION=384

# Cache settings
export CACHE_SIZE=1000
export CACHE_TTL=3600  # seconds

# Logging
export DEBUG=false
export LOG_LEVEL=INFO

# Anthropic API key (if using Anthropic embeddings)
export ANTHROPIC_API_KEY=sk-...
```

### Configuration Files

**Optional**: Create `~/.semantic-search/config.json`:

```json
{
  "backend_port": 5000,
  "python_path": "/usr/bin/python3.10",
  "embedding_provider": "ollama",
  "embedding_model": "nomic-embed-text",
  "cache_size": 1000,
  "cache_ttl": 3600,
  "debug": false,
  "log_level": "INFO",
  "index_location": "~/.semantic-search/index",
  "log_file": "~/.semantic-search/backend.log"
}
```

---

## Embedding Providers Setup

### Option 1: Mock Embeddings (Default - No Setup)

Use mock embeddings for testing/development:

```bash
export EMBEDDING_PROVIDER=mock
```

**Pros**:
- ✅ Instant, no network
- ✅ Works offline
- ✅ Zero setup

**Cons**:
- ❌ All embeddings are random
- ❌ Search results not semantic

**Best for**: Testing, demos, CI/CD

---

### Option 2: Ollama (Recommended - Local)

Run a local embedding model using Ollama:

#### Install Ollama

**Linux**:
```bash
curl https://ollama.ai/install.sh | sh
```

**macOS**:
```bash
# Download from https://ollama.ai
# Or use Homebrew
brew install ollama
```

**Windows**:
- Download from https://ollama.ai
- Install like any Windows application

#### Start Ollama

```bash
# Start Ollama in background
ollama serve

# In another terminal, pull embedding model
ollama pull nomic-embed-text
```

#### Configure Backend

```bash
export EMBEDDING_PROVIDER=ollama
export OLLAMA_HOST=http://localhost:11434
export OLLAMA_MODEL=nomic-embed-text
```

**Pros**:
- ✅ Runs locally, 100% private
- ✅ Works offline after model downloaded
- ✅ High-quality embeddings
- ✅ Free

**Cons**:
- ⚠️ Requires ~2-4GB RAM
- ⚠️ ~100-500ms per embedding
- ⚠️ Model download ~500MB

**Best for**: Production with privacy requirements

---

### Option 3: Anthropic API (Cloud-Based)

Use Anthropic's embedding API for high-quality embeddings:

#### Setup

1. **Get API Key**:
   ```bash
   # Set environment variable
   export ANTHROPIC_API_KEY=sk-...
   ```

2. **Configure Backend**:
   ```bash
   export EMBEDDING_PROVIDER=anthropic
   ```

**Pros**:
- ✅ Highest quality embeddings
- ✅ Fastest (~50-200ms)
- ✅ Minimal local resources

**Cons**:
- ❌ Requires API key
- ❌ API costs (~$0.02 per 1M tokens)
- ❌ Data sent to Anthropic servers

**Best for**: Production with quality priority

---

## Starting the Backend

### Automatic Start (IDE Extensions)

The backend starts automatically when you first search in VS Code or IntelliJ.

### Manual Start

#### Option 1: Command Line

```bash
# Activate virtual environment
source ~/.semantic-search/venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate  # Windows

# Start backend
python -m semantic_search.backend

# Or using entry point (if installed)
semantic-search-backend
```

Backend will start on `http://localhost:5000`

#### Option 2: With Custom Port

```bash
export BACKEND_PORT=8000
python -m semantic_search.backend
```

Backend will start on `http://localhost:8000`

#### Option 3: Systemd Service (Linux)

Create `/etc/systemd/system/semantic-search.service`:

```ini
[Unit]
Description=Semantic Code Search Backend
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/home/youruser
Environment="PYTHONUNBUFFERED=1"
Environment="EMBEDDING_PROVIDER=ollama"
ExecStart=/home/youruser/.semantic-search/venv/bin/python -m semantic_search.backend
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable semantic-search
sudo systemctl start semantic-search
```

Check status:

```bash
sudo systemctl status semantic-search
sudo systemctl logs -f semantic-search
```

---

## Verification

### Health Check

```bash
# Check if backend is running
curl http://localhost:5000/health

# Should return:
# {"status":"ready","indexed":true,"version":"1.0.0",...}
```

### Test Search

```bash
# Test search endpoint
curl -X POST http://localhost:5000/search \
  -H "Content-Type: application/json" \
  -d '{"query":"test","limit":5}'
```

### Test with Python

```python
import requests

response = requests.get('http://localhost:5000/health')
print(response.json())
```

---

## Troubleshooting

### "Module not found" Error

```bash
# Problem: semantic_search module not found

# Solution 1: Reinstall in development mode
pip install -e /path/to/athena

# Solution 2: Check Python path
which python  # or where python on Windows
python -c "import sys; print(sys.path)"

# Solution 3: Verify installation
pip show semantic-code-search
```

### Port Already in Use

```bash
# Problem: "Port 5000 already in use"

# Solution 1: Use different port
export BACKEND_PORT=5001
python -m semantic_search.backend

# Solution 2: Kill process on port 5000
lsof -i :5000  # Find process
kill -9 <PID>  # Kill it

# Windows
netstat -ano | findstr :5000  # Find process
taskkill /PID <PID> /F  # Kill it
```

### Ollama Connection Error

```bash
# Problem: "Cannot connect to Ollama"

# Solution 1: Check Ollama is running
ollama serve  # Start Ollama

# Solution 2: Check port
export OLLAMA_HOST=http://localhost:11434

# Solution 3: Verify model
ollama list  # Check if model is downloaded
ollama pull nomic-embed-text  # Download if missing
```

### Out of Memory

```bash
# Problem: Backend crashes with out of memory

# Solutions:
# 1. Use mock embeddings instead
export EMBEDDING_PROVIDER=mock

# 2. Reduce cache size
export CACHE_SIZE=100

# 3. Use smaller workspace
# Re-index only specific directories

# 4. Increase system swap
# (OS-specific, not recommended for production)
```

### No Search Results

```bash
# Problem: Searches return no results

# Solutions:
# 1. Verify workspace is indexed
curl -X POST http://localhost:5000/index \
  -H "Content-Type: application/json" \
  -d '{"path":"/your/project"}'

# 2. Check supported file types
# Supported: .py, .js, .ts, .jsx, .tsx, .java, .go

# 3. Lower relevance threshold
# In IDE settings: Min Score = 0.1 (instead of 0.3)

# 4. Try different embedding provider
# Current: $EMBEDDING_PROVIDER
```

---

## Performance Tuning

### Cache Optimization

```bash
# Increase cache for larger projects
export CACHE_SIZE=5000  # Default: 1000

# Increase TTL for slower networks
export CACHE_TTL=7200  # Default: 3600 (1 hour)
```

### Embedding Optimization

```bash
# Reduce dimension for faster embeddings
export EMBEDDING_DIMENSION=256  # Default: 384

# Use smaller Ollama model
export OLLAMA_MODEL=all-minilm:22m  # Faster than nomic-embed-text
```

### Index Optimization

Create `.semanticsearchignore` in project root:

```
node_modules/
.git/
venv/
build/
dist/
target/
.idea/
.vscode/
__pycache__/
*.egg-info/
.pytest_cache/
.coverage/
```

---

## Updating

### Update from Source

```bash
# Pull latest changes
cd /path/to/athena
git pull

# Reinstall
pip install -e .

# Or upgrade
pip install --upgrade semantic-code-search
```

### Backup Before Update

```bash
# Backup current index
cp -r ~/.semantic-search/index ~/.semantic-search/index.backup

# Backup config
cp ~/.semantic-search/config.json ~/.semantic-search/config.json.backup
```

---

## Uninstallation

### Remove Backend

```bash
# Uninstall package
pip uninstall semantic-code-search

# Or uninstall Athena
pip uninstall athena-memory

# Remove configuration and index
rm -rf ~/.semantic-search/
```

### Remove Virtual Environment

```bash
# Deactivate
deactivate

# Remove directory
rm -rf ~/.semantic-search/venv/
```

---

## Advanced: Building from Source

```bash
# Clone repository
git clone https://github.com/anthropic/semantic-code-search.git
cd semantic-code-search

# Build distribution
python setup.py sdist bdist_wheel

# Install locally
pip install dist/semantic_code_search-1.0.0-py3-none-any.whl
```

---

## Support & Issues

### Getting Help

- **Quick Start**: [QUICK_START_GUIDE.md](./QUICK_START_GUIDE.md)
- **Full Guide**: [SEMANTIC_CODE_SEARCH.md](../SEMANTIC_CODE_SEARCH.md)
- **API Reference**: [SEARCH_API_REFERENCE.md](./SEARCH_API_REFERENCE.md)

### Report Issues

```bash
# Enable debug logging
export DEBUG=true
export LOG_LEVEL=DEBUG

# Capture logs
python -m semantic_search.backend > backend.log 2>&1

# Share logs when reporting issues
# https://github.com/anthropic/semantic-code-search/issues
```

---

**Last Updated**: November 7, 2025
**Status**: Production Ready
