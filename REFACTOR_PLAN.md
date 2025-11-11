# Athena Refactor Plan: Docker → Full Host-Based Development

## Current Status
- Deployed Phase 1-3d+ with 61 optimized handlers (TOON encoding)
- Attempted Docker setup with MCP server + llamacpp + PostgreSQL
- Hit repeated HTTP/network complexity issues with hooks → MCP communication
- Decision: Move everything to host for simpler development

## Goal
Replace Docker-based architecture with pure host-based setup for direct Python function calls from hooks.

## Components to Deploy

### 1. PostgreSQL (Host)
- Check if already installed: `psql --version`
- If not installed:
  - macOS: `brew install postgresql`
  - Linux: `apt-get install postgresql postgresql-contrib`
- Database credentials: user=`athena`, password=`athena_dev`, db=`athena`
- Initialize schema: Run `scripts/init_postgres.sql` and `scripts/init_user.sql`

### 2. Athena Python Environment (Host)
- Create venv: `python3 -m venv venv`
- Activate: `source venv/bin/activate`
- Install: `pip install -e .` (from /home/user/.work/athena/)
- Dependencies include: llama-cpp-python, psycopg, FastAPI, etc.

### 3. llamacpp Server (Host)
- Run the local llamacpp server: `python docker/llamacpp_server.py`
- Model: `~/.athena/models/nomic-embed-text-v1.5.Q4_K_M.gguf`
- Listen on: `http://localhost:8001`

### 4. Update Hooks (Host)
Replace HTTP POST calls with direct Python imports:

```bash
# OLD (HTTP):
curl -s -X POST "http://localhost:8000/api/memory/remember" \
  -H "Content-Type: application/json" \
  -d "$EVENT_PAYLOAD"

# NEW (Direct Python):
python3 << 'EOF'
from athena.memory.store import MemoryStore
store = MemoryStore(backend='postgres')
store.remember(event_type='tool_execution', content=payload)
EOF
```

### 5. Athena Services (Host - Optional)
- MCP Server: `python -m athena.server` (if needed for external clients)
- Metrics: Prometheus metrics on port 9000

## Execution Steps

1. **Verify PostgreSQL**
   - Check installation
   - Create database and user if needed
   - Run schema init scripts

2. **Setup Python Environment**
   - Create venv
   - Install Athena + dependencies
   - Verify imports work

3. **Start Local Services**
   - PostgreSQL (if not auto-running)
   - llamacpp server on 8001
   - (Optional) MCP server on 8000

4. **Update Hooks**
   - Modify `/home/user/.claude/hooks/post-tool-use.sh` to import and call directly
   - Modify `/home/user/.claude/hooks/post-task-completion.sh`
   - Modify `/home/user/.claude/hooks/session-end.sh`
   - Remove HTTP calls entirely

5. **Test End-to-End**
   - Fire a hook manually
   - Verify episodic event recorded in PostgreSQL
   - Check memory recall works

## Files to Update
- `docker-compose.yml` → Mark as deprecated or remove
- `docker/Dockerfile` → No longer used
- `/home/user/.claude/hooks/*.sh` → Switch to Python imports
- Create `.env.local` with local configuration (PostgreSQL host=localhost, etc.)

## Expected Benefits
- ✅ Direct Python function calls (no HTTP overhead)
- ✅ Hooks can import `from athena.memory import remember`
- ✅ Instant episodic memory recording
- ✅ Much easier debugging
- ✅ No Docker complexity
- ✅ Faster iteration cycles

## Previous Commits
- `ff7e6d8` - Migrate embeddings from Ollama to llama.cpp
- `e0029bf` - Fix PostgreSQL password and improve startup
- `3e49f9e` - Update hooks to use HTTP API endpoints

---

**Ready to start refactoring when context is refreshed. Start with PostgreSQL setup verification.**
