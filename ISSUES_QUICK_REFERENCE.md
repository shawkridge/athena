# ATHENA SYSTEM ISSUES - QUICK REFERENCE

## Critical Issues Summary

### Issue #1: HTTP Server Ignores PostgreSQL ❌
- **File**: `src/athena/http/server.py` line 448
- **Problem**: Hard-codes SQLite path: `db_path = "~/.athena/memory.db"`
- **Fix**: Accept db parameter in `__init__()`, use it in `startup()`
- **Priority**: CRITICAL

### Issue #2: Database Instances Duplicated ❌
- **Files**: `server.py` line 39 + `http/server.py` line 449
- **Problem**: Two separate PostgresDatabase instances created
- **Fix**: Pass first instance to HTTP server
- **Priority**: CRITICAL

### Issue #3: Wrong Environment Variable Name ❌
- **File**: `database_factory.py` line 167
- **Problem**: Looks for `ATHENA_POSTGRES_DBNAME` instead of `ATHENA_POSTGRES_DB`
- **Fix**: Change to correct env var name
- **Priority**: HIGH

### Issue #4: Hooks Don't Use HTTP API ❌
- **Files**: `~/.claude/hooks/*.sh`
- **Problem**: References `mcp__athena__memory_tools` (Claude MCP, not available in hooks)
- **Fix**: Replace with curl HTTP calls
- **Priority**: HIGH

### Issue #5: Health Check Shows Wrong DB ❌
- **File**: `http/server.py` lines 128-132
- **Problem**: Always reports SQLite metrics
- **Fix**: Detect backend and report accordingly
- **Priority**: MEDIUM

---

## Architecture Issues Map

```
server.py (ASYNC)
├─ PostgresDatabase instance #1 ✅
├─ await db.initialize() ✅
└─ Pass to HTTP server ❌ (NOT DONE)

http/server.py (STARTUP)
├─ Ignore passed db ❌
├─ Create PostgresDatabase instance #2 ❌
└─ Lazy initialize on first request ⚠️

Result: Two instances, inconsistent state, possible writes to SQLite ❌
```

---

## Quick Fix Checklist

- [ ] TASK-001: Add db parameter to `AthenaHTTPServer.__init__()`
- [ ] TASK-002: Pass db from `server.py` to HTTP server
- [ ] TASK-003: Update `MemoryMCPServer.__init__()` to accept db parameter
- [ ] TASK-004: Fix env var name from `ATHENA_POSTGRES_DBNAME` to `ATHENA_POSTGRES_DB`
- [ ] TASK-005: Update hooks to use HTTP API instead of MCP tools
- [ ] TASK-006: Add db parameter to `MemoryStore.__init__()`
- [ ] TASK-007: Fix health check to report correct backend

---

## Testing Verification Commands

```bash
# 1. Check PostgreSQL connection
docker exec athena-postgres pg_isready -U athena

# 2. Check HTTP server health
curl http://localhost:8000/health | jq .

# 3. Store a memory
curl -X POST http://localhost:8000/api/memory/remember \
  -H "Content-Type: application/json" \
  -d '{"content": "Test", "memory_type": "fact"}'

# 4. Verify in PostgreSQL
docker exec athena-postgres psql -U athena -d athena \
  -c "SELECT COUNT(*) FROM memory_vectors;"

# 5. Check logs for issues
docker logs athena-mcp | grep -i "error\|exception\|postgresql\|sqlite"
```

---

## File Locations Summary

| Issue | File | Line | Action |
|-------|------|------|--------|
| Hard-coded SQLite path | `src/athena/http/server.py` | 448 | Add db parameter |
| DB instance not passed | `src/athena/server.py` | 54 | Pass db to HTTP server |
| MCP handler ignores db | `src/athena/mcp/handlers.py` | 160 | Accept db parameter |
| Wrong env var name | `src/athena/core/database_factory.py` | 167 | Fix to ATHENA_POSTGRES_DB |
| Hooks use MCP tools | `~/.claude/hooks/session-start.sh` | Various | Use curl HTTP |
| Health check wrong | `src/athena/http/server.py` | 128-132 | Detect backend |

---

## Data Flow After Fixes

```
server.py
├─ PostgresDatabase(...) → await initialize() ✅
└─ Pass to HTTP server ✅

http/server.py
├─ Receive db parameter ✅
├─ Use same instance for all operations ✅
└─ MCP handler uses same db ✅

Hooks
├─ Call HTTP endpoints ✅
└─ Write to PostgreSQL ✅
```

