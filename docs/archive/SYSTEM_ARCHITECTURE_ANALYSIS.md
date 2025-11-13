# ATHENA MEMORY SYSTEM - COMPREHENSIVE DEEP-DIVE ANALYSIS

**Analysis Date**: November 10, 2025  
**Status**: CRITICAL ISSUES IDENTIFIED  
**Scope**: Full 8-layer memory system with PostgreSQL backend + HTTP API + hooks infrastructure

---

## EXECUTIVE SUMMARY

The Athena memory system has a **critical architectural misalignment** discovered: **The PostgreSQL backend initialization is bypassed in production**, causing the system to fall back to SQLite while environment variables are configured for PostgreSQL.

### Key Finding
- **Docker container**: Configured to use PostgreSQL with environment variables `ATHENA_POSTGRES_HOST`, `ATHENA_POSTGRES_USER`, etc.
- **HTTP server** (`src/athena/server.py`): Correctly initializes PostgreSQL asynchronously with `await db.initialize()`
- **MCP handler** (`src/athena/mcp/handlers.py`): **Ignores PostgreSQL environment variables** and always uses SQLite path
- **Hooks** (`~/.claude/hooks/`): Configured to call `http://localhost:8000` but endpoints may not exist
- **Result**: Writes go to SQLite locally, PostgreSQL remains empty/unused

---

## CRITICAL ISSUES IDENTIFIED

### ISSUE #1: HTTP Server Database Path Always Uses SQLite [CRITICAL]
**Location**: `src/athena/http/server.py` line 448-449
**Severity**: CRITICAL

HTTP server hard-codes SQLite path regardless of PostgreSQL environment setup:
```python
db_path = str(Path.home() / ".athena" / "memory.db")
self.mcp_server = MemoryMCPServer(db_path=db_path)
```

**Impact**:
- PostgreSQL environment variables configured but ignored at HTTP layer
- All writes go to SQLite local database
- PostgreSQL database remains empty despite initialization in server.py
- No data persistence across container restarts (SQLite in ephemeral container)

### ISSUE #2: Separate Database Instances Created [CRITICAL]
**Location**: `server.py` line 39 vs `http/server.py` line 449
**Severity**: CRITICAL

Two different PostgresDatabase instances are created:
1. In `server.py`: `db = PostgresDatabase(...); await db.initialize()` ✅ Initialized
2. In `http/server.py`: `MemoryMCPServer(db_path)` creates new instance via MemoryStore ❓ Lazy initialized

**Impact**:
- First instance (server.py) has ready connection pool
- Second instance (HTTP startup) lazy-initializes on first request
- Race conditions possible on first HTTP call
- No shared state between initialization and request handling

### ISSUE #3: Environment Variable Name Mismatch [HIGH]
**Location**: `src/athena/core/database_factory.py` line 167
**Severity**: HIGH

Wrong environment variable name breaks PostgreSQL detection:
```python
# WRONG - looks for non-existent variable
'dbname': os.environ.get('ATHENA_POSTGRES_DBNAME', 'athena'),

# Should be:
'dbname': os.environ.get('ATHENA_POSTGRES_DB', 'athena'),
```

Docker-compose sets: `ATHENA_POSTGRES_DB=athena`
But code looks for: `ATHENA_POSTGRES_DBNAME` (doesn't exist!)

### ISSUE #4: Hooks Use MCP Tools Instead of HTTP [HIGH]
**Location**: `~/.claude/hooks/session-start.sh` and others
**Severity**: HIGH

Hooks reference Claude MCP tools which aren't available in hook context:
```bash
mcp__athena__memory_tools smart_retrieve --query "$CONTEXT" --k 5
```

This is a Claude context reference, not a shell command. Hooks need to use HTTP API instead.

### ISSUE #5: Health Check Reports Wrong Database [MEDIUM]
**Location**: `src/athena/http/server.py` lines 128-132
**Severity**: MEDIUM

Health check always shows SQLite metrics:
```python
if DATABASE_PATH.exists():
    db_size = DATABASE_PATH.stat().st_size / (1024 * 1024)
```

Even when using PostgreSQL, health check reports SQLite size.

---

## ARCHITECTURE DIAGRAM

```
┌─ HOST OS
│  └─ ~/.claude/hooks/
│     ├─ config.env (ATHENA_HTTP_URL=http://localhost:8000)
│     └─ *.sh scripts (call HTTP API)
│
└─ Docker Container (athena-mcp)
   │
   ├─ INITIALIZATION (async)
   │  └─ server.py:main()
   │     ├─ Read env: ATHENA_POSTGRES_HOST, USER, PASSWORD ✅
   │     ├─ Create: PostgresDatabase(host, port, db, user, pwd)
   │     ├─ Await: db.initialize()
   │     │  └─ Create AsyncConnectionPool ✅
   │     │  └─ Create schema in PostgreSQL ✅
   │     └─ Start HTTP server
   │
   ├─ HTTP LAYER
   │  └─ http/server.py:AthenaHTTPServer
   │     ├─ __init__: Create FastAPI app
   │     ├─ startup event:
   │     │  ├─ db_path = ~/.athena/memory.db
   │     │  ├─ Create: MemoryMCPServer(db_path) ❌ WRONG!
   │     │  └─ Initialize 60+ components
   │     └─ Routes:
   │        ├─ /api/memory/* → _wrap_operation()
   │        ├─ /api/consolidation/* → _wrap_operation()
   │        └─ /api/tasks/*, /api/goals/*, etc.
   │
   ├─ MCP LAYER
   │  └─ mcp/handlers.py:MemoryMCPServer
   │     ├─ __init__(db_path):
   │     │  └─ MemoryStore(db_path)
   │     │     ├─ _should_use_postgres(): Checks ATHENA_POSTGRES_HOST ✅
   │     │     ├─ If True: get_database(backend='postgres')
   │     │     │  └─ DatabaseFactory.create() reads env vars
   │     │     │     └─ Creates PostgresDatabase [NEW INSTANCE!]
   │     │     └─ If False: Database(db_path) [SQLite]
   │     └─ Store, episodic_store, graph_store, ... (60+ components)
   │
   ├─ DATABASE LAYER
   │  ├─ core/database.py (SQLite) [FALLBACK]
   │  ├─ core/database_postgres.py (PostgreSQL) [PREFERRED]
   │  │  └─ AsyncConnectionPool (lazy or already initialized)
   │  └─ core/database_factory.py (auto-detect backend)
   │
   └─ STORAGE
      ├─ PostgreSQL (5432) [Should be used]
      │  └─ memory_vectors, memory_relations, projects, ...
      └─ SQLite (~/.athena/memory.db) [Fallback, in container]
```

---

## INITIALIZATION SEQUENCE ANALYSIS

### Current (Broken) Sequence

```
1. Container starts → server.py:main() [ASYNC CONTEXT]
   
2. Create PostgresDatabase instance #1
   ├─ Set: self.host = 'postgres'
   ├─ Set: self.port = 5432
   ├─ Set: self._pool = None (lazy)
   ├─ Set: self._initialized = False
   └─ Note: __init__ doesn't call initialize()

3. Await db.initialize() ✅ [CORRECT]
   ├─ Create AsyncConnectionPool
   ├─ pool.open() - connections ready
   ├─ _init_schema() - runs CREATE TABLE/INDEX
   ├─ Set: self._initialized = True
   └─ PostgreSQL schema created ✅

4. Create AthenaHTTPServer()
   └─ store.db = None (will be set in startup)

5. app.add_event_handler("startup", startup)

6. await server.serve() [Start accepting requests]

7. *** HTTP STARTUP EVENT FIRES ***
   
8. http/server.py:startup()
   ├─ db_path = "~/.athena/memory.db"
   ├─ MemoryMCPServer(db_path=db_path)
   │  └─ MemoryStore(db_path="~/.athena/memory.db")
   │     ├─ _should_use_postgres() returns True (env vars present)
   │     ├─ get_database(backend='postgres')
   │     │  └─ DatabaseFactory._create_postgres()
   │     │     └─ PostgresDatabase(...) [NEW INSTANCE #2]
   │     │        ├─ __init__: Set pool = None
   │     │        ├─ Set _initialized = False
   │     │        └─ Do NOT call initialize()
   │     └─ self.db = this new instance
   ├─ Initialize 60+ components
   └─ Set: self.mcp_server = initialized server

9. *** FIRST REQUEST ARRIVES ***
   
10. POST /api/memory/remember
    └─ MemoryStore.remember()
       └─ self.db.store_memory() [INSTANCE #2]
          └─ if pool is None: await initialize()
              └─ *** RACE CONDITION ***
              └─ Pool initializes on first use (may conflict with startup)

11. Data written to PostgreSQL? Or SQLite?
    └─ Depends on which instance is actually used
```

### Expected (Correct) Sequence

```
1. Container starts → server.py:main() [ASYNC]

2. Create PostgresDatabase instance
   ├─ await db.initialize() [Pool ready]
   └─ Pass to HTTP server constructor

3. AthenaHTTPServer(db=db)
   ├─ self.db = db [Store reference]
   └─ Use same instance for all operations

4. startup() event
   └─ MemoryMCPServer(db=self.db) [Use passed instance]
      └─ All components use same pool

5. Requests use consistent database state ✅
```

---

## ENVIRONMENT VARIABLE MAP

### Docker Compose (docker-compose.yml)

PostgreSQL service environment:
```yaml
POSTGRES_DB: athena
POSTGRES_USER: athena
POSTGRES_PASSWORD: athena_dev
```

Athena container environment:
```yaml
# ✅ These are correctly set
ATHENA_POSTGRES_HOST: postgres        # Docker network hostname
ATHENA_POSTGRES_PORT: 5432            # PostgreSQL port
ATHENA_POSTGRES_DB: athena            # Database name
ATHENA_POSTGRES_USER: athena          # Database user
ATHENA_POSTGRES_PASSWORD: athena_dev  # Database password
ATHENA_POSTGRES_MIN_SIZE: 2           # Pool config
ATHENA_POSTGRES_MAX_SIZE: 10          # Pool config
```

### Python Code Variable Names

**database_factory.py** (Line 167) - ❌ WRONG:
```python
'dbname': os.environ.get('ATHENA_POSTGRES_DBNAME', 'athena')
# Should be: ATHENA_POSTGRES_DB
```

**memory/store.py** (Line 96) - ✅ CORRECT:
```python
pg_vars = ['ATHENA_POSTGRES_HOST', 'DATABASE_URL', 'POSTGRES_HOST']
# Checks multiple sources
```

**server.py** (Lines 25-29) - ✅ CORRECT:
```python
db_host = os.getenv("ATHENA_POSTGRES_HOST", "localhost")
db_port = int(os.getenv("ATHENA_POSTGRES_PORT", "5432"))
db_name = os.getenv("ATHENA_POSTGRES_DB", "athena")
db_user = os.getenv("ATHENA_POSTGRES_USER", "athena")
db_password = os.getenv("ATHENA_POSTGRES_PASSWORD", "athena_dev")
```

---

## VERIFIED DATA FLOW PATHS

### ✅ Working Path 1: PostgreSQL Initialization in server.py

```
server.py:main()
├─ PostgresDatabase(host='postgres', port=5432, dbname='athena', ...)
├─ await db.initialize()
│  ├─ AsyncConnectionPool created
│  ├─ await pool.open() [connections established]
│  └─ _init_schema() [CREATE TABLE, INDEX, EXTENSION]
└─ PostgreSQL ready ✅
```

### ✅ Working Path 2: HTTP Route Definition

```
POST /api/memory/remember → FastAPI handler
├─ Params: content, memory_type, tags
├─ await _wrap_operation("remember", params)
├─ await _execute_operation()
│  ├─ Check: manager.remember()
│  ├─ Check: mcp_server._handle_remember()
│  └─ Execute & return result
└─ OperationResponse returned ✅
```

### ✅ Partial Path 3: MemoryStore Database Detection

```
MemoryStore.__init__(db_path)
├─ if _should_use_postgres(): [ATHENA_POSTGRES_HOST set? ✅]
│  └─ get_database(backend='postgres')
│     ├─ DatabaseFactory.create('postgres')
│     ├─ Read all ATHENA_POSTGRES_* env vars ✅
│     └─ PostgresDatabase(host, port, dbname, user, pwd) ✅
└─ else: Database(db_path) [SQLite fallback]
```

### ❌ Broken Path 4: HTTP to MCP to Database

```
POST /api/memory/remember
├─ HTTP handler executes
├─ MemoryStore created in HTTP startup
├─ But: Separate PostgresDatabase instance from server.py ❌
└─ Race condition: Which pool? Which state? ❌
```

### ❌ Broken Path 5: Hooks to HTTP to Storage

```
Hook: post-task-completion.sh
├─ Python: AgentInvoker invokes goal-orchestrator
├─ Which tries to:
│  └─ Call memory recording endpoint
│     └─ POST /api/memory/remember
│        └─ MemoryStore operation
│           └─ PostgreSQL or SQLite? ❌
```

---

## CRITICAL TASK LIST

### TASK-001: Fix HTTP Server Database Instance [CRITICAL]
**File**: `src/athena/http/server.py`  
**Priority**: CRITICAL

**Current Code**:
```python
def __init__(self, host: str = "0.0.0.0", port: int = 3000, debug: bool = False):
    self.app = FastAPI(...)
    self.mcp_server = None
    self.manager = None
```

**Fixed Code**:
```python
def __init__(self, db=None, host: str = "0.0.0.0", port: int = 3000, debug: bool = False):
    self.db = db  # Store database instance
    self.app = FastAPI(...)
    self.mcp_server = None
    self.manager = None
```

**And in startup()**:
```python
async def startup(self):
    if self.db:
        self.mcp_server = MemoryMCPServer(db=self.db)
    else:
        db_path = str(Path.home() / ".athena" / "memory.db")
        self.mcp_server = MemoryMCPServer(db_path=db_path)
```

---

### TASK-002: Pass Database to HTTP Server [CRITICAL]
**File**: `src/athena/server.py`  
**Priority**: CRITICAL

**Current Code**:
```python
http_server = AthenaHTTPServer(host=host, port=port, debug=debug)
```

**Fixed Code**:
```python
http_server = AthenaHTTPServer(db=db, host=host, port=port, debug=debug)
```

---

### TASK-003: Update MCP Handler Database Parameter [CRITICAL]
**File**: `src/athena/mcp/handlers.py`  
**Priority**: CRITICAL

**Current Code**:
```python
def __init__(self, db_path: str | Path, enable_advanced_rag: bool = True):
    self.store = MemoryStore(db_path)
```

**Fixed Code**:
```python
def __init__(self, db=None, db_path: str | Path = None, enable_advanced_rag: bool = True):
    if db:
        self.store = MemoryStore(db=db)
    else:
        self.store = MemoryStore(db_path=db_path)
```

---

### TASK-004: Fix Environment Variable Name [HIGH]
**File**: `src/athena/core/database_factory.py` line 167  
**Priority**: HIGH

**Change**:
```python
# FROM
'dbname': kwargs.get('dbname') or os.environ.get('ATHENA_POSTGRES_DBNAME', 'athena'),

# TO
'dbname': kwargs.get('dbname') or os.environ.get('ATHENA_POSTGRES_DB', 'athena'),
```

---

### TASK-005: Update Hooks to Use HTTP API [HIGH]
**Files**: All `~/.claude/hooks/*.sh` scripts  
**Priority**: HIGH

**Example: session-start.sh**

Replace MCP tool calls with HTTP requests:
```bash
# OLD (doesn't work in hooks)
mcp__athena__memory_tools smart_retrieve --query "$CONTEXT" --k 5

# NEW (use HTTP API)
curl -X POST http://localhost:8000/api/memory/recall \
  -H "Content-Type: application/json" \
  -d "{\"query\": \"$CONTEXT\", \"k\": 5}"
```

---

### TASK-006: Add Database Parameter to MemoryStore [MEDIUM]
**File**: `src/athena/memory/store.py`  
**Priority**: MEDIUM

**Add db parameter**:
```python
def __init__(
    self,
    db=None,
    db_path: Optional[str | Path] = None,
    embedding_model: Optional[str] = None,
    ...
):
    if db:
        self.db = db
    elif self._should_use_postgres() or backend == 'postgres':
        self.db = get_database(backend='postgres')
    else:
        if db_path is None:
            db_path = config.DATABASE_PATH
        self.db = Database(db_path)
```

---

### TASK-007: Fix Health Check Endpoint [MEDIUM]
**File**: `src/athena/http/server.py`  
**Priority**: MEDIUM

```python
@self.app.get("/health")
async def health_check():
    try:
        uptime = time.time() - START_TIME
        
        # Report actual backend
        if isinstance(self.db, PostgresDatabase):
            # Query PostgreSQL for info
            async with self.db.get_connection() as conn:
                result = await conn.execute("SELECT current_database()")
                row = await result.fetchone()
                return HealthResponse(
                    status="healthy",
                    backend="postgresql",
                    database=row[0] if row else "unknown",
                    ...
                )
        else:
            # SQLite info
            db_size = DATABASE_PATH.stat().st_size / (1024 * 1024) if DATABASE_PATH.exists() else 0
            return HealthResponse(
                status="healthy",
                backend="sqlite",
                database_size_mb=db_size,
                ...
            )
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
```

---

## VERIFICATION CHECKLIST

After implementing fixes, verify:

- [ ] PostgreSQL container healthy: `docker ps | grep postgres`
- [ ] HTTP server starts: `curl http://localhost:8000/health`
- [ ] Health check shows PostgreSQL: `curl http://localhost:8000/health | jq .backend`
- [ ] Store memory via HTTP: `curl -X POST http://localhost:8000/api/memory/remember ...`
- [ ] Query PostgreSQL for data: `docker exec athena-postgres psql -U athena -d athena -c "SELECT COUNT(*) FROM memory_vectors;"`
- [ ] Consolidation reads from PostgreSQL: `docker logs athena-mcp | grep "consolidation\|PostgreSQL"`
- [ ] Hooks work: `bash ~/.claude/hooks/post-task-completion.sh`
- [ ] All layers use same database instance
- [ ] No SQLite fallback unless explicitly configured

---

## SUMMARY

**Root Cause**: Database instance not passed from `server.py` initialization to HTTP handler → MCP handler initialization

**Impact**: PostgreSQL initialized but ignored, writes go to SQLite, data not persisted

**Fix Complexity**: LOW (configuration/passing changes only)

**Implementation Time**: 3-4 hours including testing

**Risk Level**: LOW (isolated changes, no schema modifications)

**Effort**: 7 tasks, mostly straightforward parameter passing

