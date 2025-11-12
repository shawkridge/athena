# Test Failure Analysis: Anthropic Alignment Tests

**Date**: November 12, 2025
**Status**: 4 tests failing, 5 passing
**Root Cause**: Multiple infrastructure and code issues

---

## Summary of Failures

```
FAILED tests/integration/test_anthropic_alignment.py::TestSkillsIntegration::test_skill_creation_and_persistence
FAILED tests/integration/test_anthropic_alignment.py::TestSkillsIntegration::test_skill_matching_and_execution
FAILED tests/integration/test_anthropic_alignment.py::TestEndToEndAlignment::test_privacy_and_efficiency_together
FAILED tests/integration/test_anthropic_alignment.py::TestEndToEndAlignment::test_complete_workflow

================== 4 failed, 5 passed in 330.14s ===================
```

---

## Issue 1: Undefined `Database` Class (Critical)

### The Problem

Lines 288, 350 in test file use `Database()` constructor:

```python
# Line 288 - test_privacy_and_efficiency_together()
db = Database(f"{tmpdir}/skills.db")  # ❌ UNDEFINED - Database class not imported

# Line 350 - test_complete_workflow()
db = Database(f"{tmpdir}/skills.db")  # ❌ UNDEFINED - Database class not imported
```

### Why It Fails

The test file **only imports** `PostgresDatabase`:
```python
from athena.core.database_postgres import PostgresDatabase  # ✅ Imported
```

But **never imports** `Database`:
```python
# Missing!
from athena.core.database import Database  # ❌ NOT IMPORTED
```

### What Actually Exists

There's **no `Database` class** in the codebase at all:
```bash
$ grep -r "^class Database" /home/user/.work/athena/src/athena/core
# Returns: Nothing
```

Only:
- `PostgresDatabase` in `database_postgres.py` (PostgreSQL-backed)
- `DatabaseFactory` in `database_factory.py` (factory pattern)

### The Error

```
AssertionError: assert False
  where False = save(Skill(authenticate, quality=0.95, used=0))
```

This happens because:
1. Test tries to use undefined `Database`
2. `SkillLibrary.save()` gets called on a non-database object
3. Database operations fail silently, return False
4. Test assertion fails

---

## Issue 2: SkillLibrary Expects SQLite, But PostgresDatabase Is Async

### The Problem

**`SkillLibrary` implementation** (library.py:60-104) uses **synchronous SQLite API**:

```python
def save(self, skill: Skill) -> bool:
    try:
        metadata_json = skill.metadata.to_json()

        cursor = self.db.get_cursor()  # ❌ Expects sync SQLite cursor
        cursor.execute("""...""")
        self.db.commit()              # ❌ Expects sync commit
        return True
    except Exception as e:
        logger.error(f"Failed to save skill {skill.id}: {e}")
        return False
```

**But test uses `PostgresDatabase`** which is **async**:

```python
# database_postgres.py - ASYNC API
class PostgresDatabase:
    async def get_cursor(self) -> AsyncConnection:
        """Get async connection"""
        async with self.pool.connection() as conn:
            yield conn
```

### The Mismatch

| Component | API Type | Problem |
|-----------|----------|---------|
| SkillLibrary | **Synchronous** | Expects `cursor.execute()` to return immediately |
| PostgresDatabase | **Asynchronous** | Returns async coroutines that need `await` |
| Test | Both | Tries to use async DB with sync code |

### The Error

```
psycopg_pool.PoolTimeout: couldn't get a connection after 30.00 sec

Is the server running locally and accepting connections on that socket?
connection to server on socket "/tmp/tmpqvpx3fmb/skills.db/.s.PGSQL.5432"
```

What actually happens:
1. Test creates temp directory: `/tmp/tmpqvpx3fmb/`
2. Tries to connect to PostgreSQL at: `/tmp/tmpqvpx3fmb/skills.db/.s.PGSQL.5432`
3. PostgreSQL is **not running** (not a valid socket path)
4. Connection pool times out after 30 seconds

---

## Issue 3: PostgreSQL Not Running in Test Environment

### The Problem

Tests expect a real PostgreSQL server running:

```python
@pytest.fixture
def postgres_db(self) -> PostgresDatabase:
    """Create PostgreSQL database instance."""
    return PostgresDatabase(
        host="localhost",
        port=5432,
        dbname="athena",
        user="athena",
        password="athena_dev",
    )
```

But PostgreSQL is **not started** in the test environment.

### Evidence

From test output:
```
WARNING  psycopg.pool:pool_async.py:690 error connecting in 'pool-4':
connection is bad: connection to server on socket
"/tmp/tmpqvpx3fmb/skills.db/.s.PGSQL.5432" failed: No such file or directory

Is the server running locally and accepting connections on that socket?
```

### The Timeline

```
Test starts (0s)
  ↓
Tries to get connection from pool
  ↓
Waits for PostgreSQL... (0-30s)
  ↓
Timeout after 30s
  ↓
Test fails with PoolTimeout
```

This happens 4 times (once per test), totaling **130+ seconds wasted**.

---

## Issue 4: Async/Sync Mismatch in SkillLibrary Design

### The Architecture Problem

**Current design** has a fundamental incompatibility:

```
SkillLibrary (SYNC)
    │
    ├─ Uses cursor.execute()        ← Blocking/sync
    ├─ Uses db.commit()             ← Blocking/sync
    └─ Expects immediate results    ← Blocking/sync
            │
            ↓
PostgresDatabase (ASYNC)
            │
            ├─ Uses async with self.pool.connection()
            ├─ All methods are async
            └─ Requires await for every operation
```

**Why it was designed this way:**
- SkillLibrary was written to support SQLite (synchronous)
- PostgresDatabase was added later (asynchronous)
- No adapter/bridge was created

---

## Passing Tests (5/9) ✅

These work because they **don't use the broken skill system**:

1. ✅ `test_pii_flow_end_to_end()` - Tests PII detection/tokenization (no DB)
2. ✅ `test_pii_deterministic_tokenization()` - Tests PII tokens (no DB)
3. ✅ `test_tools_filesystem_structure()` - Tests filesystem API (no DB)
4. ✅ `test_tools_progressive_loading()` - Tests tool loading (no DB)
5. ✅ `test_context_efficiency()` - Tests token counting (no DB)

**All passing tests are "pure" functions** with no database dependency.

---

## The Fixes Needed

### Fix 1: Create SQLite `Database` Class (Quick)

```python
# src/athena/core/database.py - ADD THIS
from sqlite3 import connect, Cursor, Connection
from typing import Optional

class Database:
    """SQLite database wrapper for testing and simple use cases."""

    def __init__(self, db_path: str):
        self.conn: Connection = connect(db_path)
        self.conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))

    def get_cursor(self) -> Cursor:
        """Get database cursor."""
        return self.conn.cursor()

    def commit(self):
        """Commit transaction."""
        self.conn.commit()

    def close(self):
        """Close database connection."""
        self.conn.close()
```

**Why**: SkillLibrary.save() expects this interface, not PostgresDatabase.

**Cost**: 20 lines of code

---

### Fix 2: Update Test Imports (Very Quick)

```python
# tests/integration/test_anthropic_alignment.py - ADD IMPORT
from athena.core.database import Database  # ← ADD THIS LINE

# Then lines 288 and 350 will work:
db = Database(f"{tmpdir}/skills.db")  # ✅ Now defined
```

**Why**: Tests refer to undefined class.

**Cost**: 1 line of code

---

### Fix 3: Add Test-Specific Async Support (Medium)

Option A: **Make SkillLibrary support both sync and async**
```python
class SkillLibrary:
    def __init__(self, db: Union[Database, PostgresDatabase]):
        self.db = db
        self.is_async = isinstance(db, PostgresDatabase)

    async def save(self, skill: Skill) -> bool:
        if self.is_async:
            async with self.db.pool.connection() as conn:
                # Async version
        else:
            cursor = self.db.get_cursor()
            # Sync version
```

Option B: **Use pytest-asyncio for async tests**
```python
@pytest.mark.asyncio
async def test_skill_creation_and_persistence(self):
    # Use async/await syntax
```

**Cost**: 30-50 lines of code

---

### Fix 4: Use SQLite for All Tests (Recommended)

**Don't use PostgresDatabase in tests at all.**

```python
# Before (BROKEN):
@pytest.fixture
def postgres_db(self) -> PostgresDatabase:
    return PostgresDatabase(...)  # ❌ Not running

# After (WORKING):
@pytest.fixture
def db(self) -> Database:
    with tempfile.TemporaryDirectory() as tmpdir:
        return Database(f"{tmpdir}/test.db")  # ✅ Works immediately
```

**Why**:
- SQLite works immediately (in-process)
- No server startup needed
- Tests run in <1 second instead of 30s
- Perfect for integration testing

**Cost**: Change 3 fixture definitions

---

## Recommended Fix Path

### Phase 1: Unblock Tests (5 minutes)
1. Create `Database` class in `src/athena/core/database.py`
2. Add import in test file: `from athena.core.database import Database`
3. Re-run tests → All 9 should pass ✅

### Phase 2: Support Both Backends (1 hour)
1. Make SkillLibrary detect sync vs async DB
2. Use SQLite for tests, PostgreSQL for production
3. Add type hints for both database types

### Phase 3: Clean Up (30 minutes)
1. Remove PostgresDatabase from test fixtures (or mark as optional)
2. Add pytest markers to skip Postgres-specific tests
3. Document which tests require what infrastructure

---

## Quick Test to Verify Fixes

After implementing Fix 1 & 2:

```bash
# Run just the alignment tests
pytest tests/integration/test_anthropic_alignment.py -v

# Should show:
# test_pii_flow_end_to_end ✅
# test_pii_deterministic_tokenization ✅
# test_tools_filesystem_structure ✅
# test_tools_progressive_loading ✅
# test_context_efficiency ✅
# test_skill_creation_and_persistence ✅  ← NOW PASSING
# test_skill_matching_and_execution ✅    ← NOW PASSING
# test_privacy_and_efficiency_together ✅  ← NOW PASSING
# test_complete_workflow ✅               ← NOW PASSING

# ==================== 9 passed in X.XXs ====================
```

---

## Summary Table

| Issue | Type | Severity | Fix Time | Impact |
|-------|------|----------|----------|--------|
| **Missing `Database` class** | Code | Critical | 5 min | Blocks all 4 skill tests |
| **Missing import in test** | Code | Critical | 1 min | Prevents even trying |
| **SkillLibrary sync/async** | Design | High | 1 hour | Long-term maintainability |
| **PostgreSQL not running** | Infra | Medium | 30 min | 130s wasted per test run |

---

## The Real Issue

The tests were written for a **future system** that doesn't exist yet:

1. Tests assume `Database` class exists ❌ (doesn't)
2. Tests assume SkillLibrary works with PostgreSQL ❌ (it's sync-only)
3. Tests assume PostgreSQL server is running ❌ (it's not)

**The solution**: Either
- **A)** Build the missing pieces (recommended for now)
- **B)** Revert to SQLite-only for MVP (simpler)

---

**Conclusion**: The alignment tests are **well-designed** but **incomplete infrastructure**. The fixes are straightforward and low-cost. All 9 tests should pass within 1 hour of work.
