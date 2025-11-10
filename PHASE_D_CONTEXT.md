# Phase D Context - Docker Deployment & MCP Resolution

**Status**: In Progress
**Session**: Phase C → Phase D Continuation
**Date**: November 10, 2025
**Focus**: Complete local Docker deployment and resolve MCP import issues

---

## Current State

### ✅ Completed in Phase C

1. **Docker Infrastructure Setup**
   - ✅ Enhanced `docker-compose.yml` with 5 services (PostgreSQL, Ollama, Athena, Redis, PgAdmin)
   - ✅ Created `docker-compose.dev.yml` for development overrides
   - ✅ Created `.env.example` with 26 configuration variables
   - ✅ Created `docker-up.sh` quick-start script with 8 commands
   - ✅ Written 989-line `LOCAL_DOCKER_DEPLOYMENT.md` guide
   - ✅ Docker image builds successfully
   - ✅ PostgreSQL 18 running and healthy
   - ✅ Ollama running with nomic-embed-text model pulled
   - ✅ Redis cache operational (from previous deployment)
   - ✅ Updated `pyproject.toml` to include `psutil>=5.0.0`

2. **Services Status**
   - ✅ PostgreSQL: Connected, database initialized, schema ready
   - ✅ Ollama: Running, model downloaded (4.1GB nomic-embed-text)
   - ✅ Redis: Running, healthy
   - ✅ Docker network: Configured (`athena-network`)
   - ✅ Volumes: Persistent storage configured

### ⚠️ Current Blocker

**MCP Module Import Error**: `ModuleNotFoundError: No module named 'mcp.server'`

- **Location**: `/app/src/athena/mcp/handlers.py:10`
- **Issue**: Code imports `from mcp.server import Server` but this module doesn't exist in MCP 1.18.0
- **Root Cause**: Either (a) version mismatch, (b) MCP package API changed, or (c) compatibility adapter needed
- **Impact**: Athena server won't start; crashes on startup with restart loop

---

## What Needs to Happen in Phase D

### Priority 1: Resolve MCP Import Issue (Critical)

**Two Possible Solutions:**

#### Option A: Fix the Import
1. Check if `mcp.server` exists in a specific MCP version
   ```bash
   pip show mcp  # Currently 1.18.0
   python -c "from mcp import *; import inspect; print([x for x in dir() if 'server' in x.lower()])"
   ```

2. Look at `/app/src/athena/mcp/compat_adapter.py` - it might have compatibility helpers
   ```bash
   cat /home/user/.work/athena/src/athena/mcp/compat_adapter.py
   ```

3. Update `handlers.py` imports to use correct module path:
   ```python
   # Possibly:
   from mcp import Server  # instead of mcp.server
   # OR adapt to new API structure
   ```

#### Option B: Use HTTP Server Temporarily
1. Update Dockerfile CMD to run simple HTTP wrapper instead of MCP server
   ```bash
   # Current: CMD ["python", "-m", "athena.server"]
   # Fallback: Use existing HTTP server wrapper (check if exists)
   ```

### Priority 2: Verify Infrastructure Services

```bash
# All these should be working:
docker-compose ps  # Show service status
curl http://localhost:8000/health  # HTTP endpoint (if available)
curl http://localhost:11434/api/tags  # Ollama
psql -h localhost -U athena -d athena -c "SELECT 1"  # PostgreSQL
docker-compose logs -f  # Watch all logs
```

### Priority 3: Test Core Functionality

Once Athena starts:
```bash
# Run test suite
docker-compose exec athena pytest tests/mcp/ -v
docker-compose exec athena pytest tests/unit/ -v

# Check database connectivity
docker-compose exec athena python -c "from athena.core.database import Database; db = Database(); print('✓ DB connected')"

# Test Ollama integration
docker-compose exec athena python -c "from athena.semantic.embeddings import EmbeddingManager; em = EmbeddingManager(); print('✓ Embeddings ready')"
```

### Priority 4: Development Environment Setup

```bash
# Enable hot-reload for development
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# This will:
# - Mount src/ for live reloading
# - Enable verbose logging
# - Include pgAdmin at localhost:5050
# - Enable dev-tools container
```

### Priority 5: Documentation & Handoff

- [ ] Document the MCP import fix (solution chosen)
- [ ] Update `LOCAL_DOCKER_DEPLOYMENT.md` with fix
- [ ] Create `PHASE_E_CONTEXT.md` for next session
- [ ] Commit all changes with clear commit message

---

## Key Files to Work With

### Docker Files
- `/home/user/.work/athena/docker/Dockerfile` - Application image (needs MCP fix)
- `/home/user/.work/athena/docker-compose.yml` - Service orchestration
- `/home/user/.work/athena/docker-compose.dev.yml` - Dev overrides

### Source Code (Likely Issue)
- `/home/user/.work/athena/src/athena/mcp/handlers.py:10` - **BROKEN IMPORT**
- `/home/user/.work/athena/src/athena/mcp/compat_adapter.py` - Check for compatibility helpers
- `/home/user/.work/athena/src/athena/server.py` - Server entry point

### Configuration
- `/home/user/.work/athena/.env` - Runtime configuration
- `/home/user/.work/athena/pyproject.toml` - Dependencies (updated with psutil)

### Documentation
- `/home/user/.work/athena/LOCAL_DOCKER_DEPLOYMENT.md` - 989-line deployment guide
- `/home/user/.work/athena/DEPLOYMENT.md` - Full deployment reference
- `/home/user/.work/athena/CLAUDE.md` - Project instructions

---

## Environment Info

### Services Running
```
PostgreSQL 18:     localhost:5432 (user: athena, pass: athena_dev)
Ollama:            localhost:11434 (has nomic-embed-text model)
Athena HTTP:       localhost:8000 (currently failing)
Athena Metrics:    localhost:9000 (currently failing)
Redis:             localhost:6379 (healthy)
```

### Volumes
```
postgres_data:     Database persistence
ollama_data:       Model caching
athena_logs:       Application logs
~/.athena/:        Shared data directory
~/.ollama/:        Ollama config
```

### Docker Commands
```bash
# View status
docker-compose ps

# View logs
docker-compose logs -f
docker-compose logs -f athena  # Just Athena

# Restart services
docker-compose restart athena
docker-compose down
docker-compose up -d

# Execute commands
docker-compose exec -T athena python -c "..."
docker-compose exec postgres psql -U athena -d athena -c "..."
```

---

## Known Working Paths

1. **PostgreSQL Connection** ✅
   ```bash
   docker-compose exec -T postgres psql -U athena -d athena -c "SELECT version()"
   # Works! Returns: PostgreSQL 18.0
   ```

2. **Ollama API** ✅
   ```bash
   curl http://localhost:11434/api/tags
   # Works! Returns: {"models":[{"name":"nomic-embed-text:latest",...}]}
   ```

3. **Docker Build** ✅
   ```bash
   docker-compose up -d --build
   # Works! Image builds successfully, ~500MB
   ```

4. **Redis** ✅
   ```bash
   redis-cli -h localhost ping
   # Works! Returns: PONG
   ```

---

## Testing Strategy

Once MCP is fixed:

1. **Unit Tests** (should all pass)
   ```bash
   docker-compose exec athena pytest tests/unit/ -v -m "not benchmark"
   ```

2. **Integration Tests** (should all pass)
   ```bash
   docker-compose exec athena pytest tests/integration/ -v -m "not benchmark"
   ```

3. **MCP Server Tests** (55 tests, should pass)
   ```bash
   docker-compose exec athena pytest tests/mcp/ -v
   ```

4. **Full Test Suite** (takes 5-10 minutes)
   ```bash
   docker-compose exec athena pytest tests/ -v --timeout=300
   ```

---

## Debugging Approach

### If MCP Import Still Fails

1. **Check actual MCP package structure:**
   ```bash
   docker-compose exec -T athena python -c "import mcp; print(dir(mcp))"
   docker-compose exec -T athena python -c "import mcp.server" 2>&1  # Will show error
   ```

2. **Check what's in compat_adapter:**
   ```bash
   grep -n "mcp\|Server" /home/user/.work/athena/src/athena/mcp/compat_adapter.py | head -20
   ```

3. **Try different imports:**
   ```python
   # Test in container:
   # Try: from mcp import Server
   # Try: from mcp.types import Server
   # Try: import mcp.server as mcp_server
   ```

4. **Check MCP version compatibility:**
   ```bash
   # What version works with this code?
   pip install mcp==1.0.0  # Try older version
   ```

---

## Next Session Summary

**Session Goal**: Get Athena MCP server running and fully functional locally.

**Critical Task**: Resolve the `mcp.server` import error by either:
1. Finding the correct import path for MCP 1.18.0
2. Using an HTTP wrapper instead
3. Downgrading/upgrading MCP to compatible version

**Success Criteria**:
- [ ] Athena container starts without crashing
- [ ] `docker-compose ps` shows all services as "Up" or "healthy"
- [ ] Can connect to Athena via API (HTTP or MCP)
- [ ] All 55 MCP tests pass
- [ ] PostgreSQL, Ollama, and Redis all responding
- [ ] Development environment ready with hot-reload

**Time Estimate**: 30-45 minutes to fix MCP issue + verify all systems

---

## Commit Template for Phase D

```
feat: Phase D - Fix MCP import and complete Docker deployment

- Fix 'mcp.server' import error (use correct MCP 1.18.0 API)
- Verify all Docker services healthy (PostgreSQL, Ollama, Redis)
- Confirm MCP server starts and handles connections
- Run full test suite (55 MCP tests passing)
- Complete local Docker deployment for development

All infrastructure ready for Phase E (advanced features)
```

---

**Prepared by**: Claude Code
**For**: Next development session
**Status**: Ready to handoff
