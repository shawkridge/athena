# SQLite & Qdrant Removal Analysis for Athena Codebase

**Analysis Date**: 2025-11-11
**Scope**: PostgreSQL + pgvector migration (ONLY)
**Status**: 16+ files with SQLite imports, 1 file with Qdrant, multiple fallback implementations

---

## Executive Summary

The Athena codebase has **PARTIALLY migrated to PostgreSQL** but retains scattered SQLite and Qdrant references:

### Key Findings:
1. **Core Database Layer**: Already migrated to PostgreSQL (database.py, database_factory.py, database_postgres.py)
2. **Memory/Search Layers**: Mixed - semantic search uses PostgreSQL, but memory_api.py forces SQLite fallback
3. **Store Layers**: All 20+ store files import `sqlite3` but mostly for type hints (comments)
4. **Executive Functions**: Active SQLite usage in metrics.py, progress.py, conflict.py, strategy.py
5. **Qdrant Adapter**: Complete Qdrant module exists but marked as deprecated
6. **Fallback Implementations**: Multiple files have active sqlite3 usage instead of PostgreSQL

---

## FILES NEEDING REMOVAL/MODIFICATION

### PRIORITY 1: CRITICAL - Remove Active SQLite Usage (Do First)

These files have ACTIVE sqlite3 code (not just imports in comments):

#### 1. **src/athena/executive/progress.py** (CRITICAL)
- **Status**: Active sqlite3.connect() calls
- **Usage**: Direct SQLite connections for task progress tracking
- **Lines**: Multiple `sqlite3.connect()` calls throughout
- **Action**: Replace with PostgreSQL async methods
- **Dependency**: Used by executive function system

#### 2. **src/athena/executive/metrics.py** (CRITICAL)
- **Status**: Active sqlite3 usage
- **Usage**: Direct database connections for metrics
- **Action**: Migrate to PostgreSQL
- **Impact**: High - used by executive system

#### 3. **src/athena/executive/conflict.py** (CRITICAL)
- **Status**: sqlite3 import active
- **Usage**: Conflict detection and resolution
- **Action**: Migrate to PostgreSQL
- **Impact**: Executive function core

#### 4. **src/athena/executive/strategy.py** (CRITICAL)
- **Status**: sqlite3 import active
- **Usage**: Strategy selection
- **Action**: Migrate to PostgreSQL

#### 5. **src/athena/core/production.py** (CRITICAL)
- **Status**: Active sqlite3 exception handling
- **Code Examples**:
  ```python
  except sqlite3.Error:
  except sqlite3.OperationalError:
  ```
- **Action**: Replace with PostgreSQL async exception handling

#### 6. **src/athena/compression/schema.py** (HIGH)
- **Status**: Active sqlite3.connect() calls
- **Code**:
  ```python
  conn = sqlite3.connect(db_path)
  ```
- **Action**: Replace with PostgreSQL pool

#### 7. **src/athena/monitoring/health.py** (HIGH)
- **Status**: Active sqlite3 usage
- **Code**:
  ```python
  conn = sqlite3.connect(db_path, timeout=5)
  ```
- **Action**: Use PostgreSQL async health check

#### 8. **src/athena/resilience/degradation.py** (MEDIUM)
- **Status**: Exception handling for sqlite3
- **Code**:
  ```python
  sqlite3.OperationalError
  ```
- **Action**: Replace with PostgreSQL exceptions

---

### PRIORITY 2: HIGH - Remove Qdrant Implementation

#### 1. **src/athena/rag/qdrant_adapter.py** (COMPLETE REMOVAL)
- **Status**: Full Qdrant implementation (350+ lines)
- **Contains**: QdrantAdapter class, collection management, search operations
- **Action**: DELETE ENTIRE FILE
- **Reason**: Already marked as deprecated in memory/store.py
- **Impact**: LOW - Only imported in memory/search.py and memory/store.py, already wrapped with fallback

#### 2. **src/athena/memory/search.py** (MODIFY)
- **Current**: Has fallback to Qdrant when PostgreSQL fails
- **Lines with Qdrant**:
  - Line 18: `from ..rag.qdrant_adapter import QdrantAdapter`
  - Lines 31-42: Constructor accepting optional `qdrant` param
  - Lines 163-174: Qdrant fallback in recall()
  - Lines 207-213: Qdrant fallback in _recall_postgres()
  - Lines 250-258: Qdrant fallback in _recall_postgres()
  - Lines 331-383: Complete `_recall_qdrant()` method
  - Lines 441-442: Docstring mentions "Qdrant fallback"
  - Lines 515-572: Cross-project Qdrant fallback
- **Action**: Remove all Qdrant references and fallback paths
- **Remove Methods**: `_recall_qdrant()` completely
- **Update Docstrings**: Remove mentions of Qdrant fallback

#### 3. **src/athena/memory/store.py** (MODIFY)
- **Current**: Comments indicate Qdrant support is deprecated
- **Lines with Qdrant**:
  - Line 18: Comment about deprecated Qdrant
  - Lines 34-35: Unused `use_qdrant` parameter
  - Lines 45-46: Ignored Qdrant parameter
  - Lines 57-60: Deprecation warning
  - Lines 108-155: Code for dual-write to Qdrant (in remember())
  - Lines 139-155: Qdrant storage attempt with logging
  - Lines 160-174: Qdrant deletion in forget()
- **Action**: Remove Qdrant parameter and dual-write logic
- **Simplify**: Single-write to PostgreSQL only

---

### PRIORITY 3: MEDIUM - Remove SQLite Type Hints & Imports (Cleanup)

These files have sqlite3 imports but NO ACTUAL USAGE (just comments/type hints):

#### Store Files (16 files - mostly type hints in comments):
1. **src/athena/episodic/store.py** - Line 4: `import sqlite3` (only in comments)
2. **src/athena/procedural/store.py** - Line 4: `import sqlite3` (only in comments)
3. **src/athena/graph/store.py** - Line 4: `import sqlite3` (1 usage: IntegrityError catch)
4. **src/athena/prospective/store.py** - Line 3: `import sqlite3`
5. **src/athena/meta/store.py** - Line 4: `import sqlite3`
6. **src/athena/safety/store.py** - Line 4: `import sqlite3`
7. **src/athena/planning/store.py** - Line 4: `import sqlite3`
8. **src/athena/research/store.py** - sqlite3 in comments
9. **src/athena/symbols/symbol_store.py** - Line 13: `import sqlite3`
10. **src/athena/ide_context/store.py** - `import sqlite3`
11. **src/athena/rules/store.py** - `import sqlite3`
12. **src/athena/working_memory/models.py** - Type hint references
13. **src/athena/working_memory/central_executive.py** - sqlite3 in comments

**Action for each**: 
- Remove `import sqlite3` line
- Update type hints from `sqlite3.Row` to PostgreSQL Row type
- Replace exception handlers (e.g., `sqlite3.IntegrityError` → `psycopg.IntegrityError`)
- Update docstring references

---

### PRIORITY 4: MEDIUM - Problematic Forced SQLite Fallback

#### **src/athena/mcp/memory_api.py** (MODIFY)
- **Current Issue**: Lines 191-195 force SQLite backend in factory
- **Code**:
  ```python
  # Initialize database - force SQLite for synchronous operations
  database = Database(db_path) if db_path else Database()
  
  # Initialize all memory layers - force SQLite backend with use_qdrant=False
  semantic = MemoryStore(..., backend='sqlite')
  ```
- **Problem**: Hardcoded SQLite backend when trying to create test instances
- **Action**: 
  - Remove `backend='sqlite'` parameter
  - Use PostgreSQL backend (or mock for testing)
  - Fix comment "force SQLite" → "use PostgreSQL"

---

### PRIORITY 5: LOW - Comments & Documentation Cleanup

1. **src/athena/orchestration/task_queue.py** - Comment mentions "sqlite3.Row"
2. **src/athena/research/store.py** - Comments about sqlite3.Row conversion
3. **src/athena/mcp/executive_function_tools.py** - Line 287 has sqlite3 import in error handling

---

## REMOVAL STRATEGY BY PHASE

### Phase 1: Remove Critical Active SQLite Code (1-2 days)
**Files to Migrate**:
1. src/athena/executive/progress.py
2. src/athena/executive/metrics.py
3. src/athena/core/production.py
4. src/athena/compression/schema.py
5. src/athena/monitoring/health.py

**Process**:
- Replace `sqlite3.connect()` with PostgreSQL async methods
- Update exception handling to use PostgreSQL exceptions
- Add async/await where needed

### Phase 2: Remove Qdrant Entirely (1 day)
**Files to Modify**:
1. Delete src/athena/rag/qdrant_adapter.py
2. Simplify src/athena/memory/search.py (remove fallbacks)
3. Simplify src/athena/memory/store.py (remove dual-write)

**Testing**:
- Verify search still works with PostgreSQL only
- Confirm no Qdrant import errors

### Phase 3: Clean Up Store Layer Imports (2-3 hours)
**Files to Update** (16 files):
- Remove unused `import sqlite3`
- Fix type hints and exception handlers
- Replace comments referencing sqlite3

### Phase 4: Fix Fallback Implementations (2-3 hours)
**Files to Update**:
1. src/athena/mcp/memory_api.py - Remove `backend='sqlite'` forcing
2. src/athena/mcp/executive_function_tools.py - Clean up error handling

---

## QDRANT-SPECIFIC REMOVALS

### File: src/athena/rag/qdrant_adapter.py
**Status**: FULLY DEPRECATED - SAFE TO DELETE

**Content**: 320 lines
- QdrantAdapter class
- Collection management
- Search operations
- Health checks
- Memory add/delete

**Dependencies**:
```
memory/search.py:18 - TYPE_CHECKING import (can remove)
memory/store.py:19 - TYPE_CHECKING import (can remove)
```

**Fallback Plan**: None needed - PostgreSQL replaces all functionality

---

## SQLITE3 EXCEPTION HANDLING REPLACEMENTS

### Current (SQLite):
```python
try:
    # operation
except sqlite3.IntegrityError:
    # handle
except sqlite3.OperationalError:
    # handle
except sqlite3.Error:
    # handle
```

### Replacement (PostgreSQL):
```python
try:
    # operation
except psycopg.errors.IntegrityError:
    # handle
except psycopg.errors.OperationalError:
    # handle
except psycopg.Error:
    # handle
```

---

## TYPE HINT REPLACEMENTS

### Current (SQLite):
```python
def _row_to_model(self, row: sqlite3.Row) -> Model:
```

### Replacement (PostgreSQL):
```python
# No type hint needed - asyncpg returns dicts
def _row_to_model(self, row: dict) -> Model:
```

---

## VALIDATION CHECKLIST

After removal:
- [ ] No `import sqlite3` in any file
- [ ] No `import qdrant` anywhere
- [ ] No references to `sqlite3.` exceptions
- [ ] All store files use PostgreSQL exceptions
- [ ] memory/search.py has no Qdrant fallback
- [ ] memory/store.py has no dual-write logic
- [ ] qdrant_adapter.py deleted
- [ ] All tests pass with PostgreSQL only
- [ ] No commented-out SQLite code remains
- [ ] Git status clean (all removals committed)

---

## ESTIMATED EFFORT

| Phase | Task | Time | Files |
|-------|------|------|-------|
| 1 | Migrate active SQLite | 1-2 days | 5 |
| 2 | Remove Qdrant | 1 day | 3 |
| 3 | Clean store imports | 2-3 hrs | 16 |
| 4 | Fix fallback logic | 2-3 hrs | 2 |
| Testing | Verify all functionality | 1-2 days | All |
| **Total** | **Complete Migration** | **3-5 days** | **26** |

---

## CRITICAL SUCCESS FACTORS

1. **No SQLite imports remain** - Even commented-out code should be removed
2. **PostgreSQL async/await** - All database operations must be async
3. **Exception handling** - Use psycopg exceptions, not sqlite3
4. **Type hints** - Update from sqlite3.Row to dict
5. **Test coverage** - Ensure all layers work with PostgreSQL only
6. **No fallback logic** - Single path to PostgreSQL (no Qdrant fallback)

---

## NOTES FOR IMPLEMENTATION

### Order of Work:
1. **Start with memory_api.py** - Fix forced SQLite backend (quick win)
2. **Then core/production.py** - Fix exception handling (high impact)
3. **Then executive/* files** - Migrate actual SQLite code
4. **Then memory/search.py** - Remove Qdrant fallbacks
5. **Then store files** - Clean up imports
6. **Finally delete qdrant_adapter.py** - Remove deprecated module

### Testing Strategy:
- Unit tests must use PostgreSQL test database
- Integration tests verify all layers work together
- No mocking of database layer (use real PostgreSQL)
- Verify memory/search works without Qdrant fallback

### Git Hygiene:
- One commit per file modified (small, reviewable commits)
- Commit message: "Remove SQLite/Qdrant from [file]: [brief description]"
- No half-measures: all or nothing per file

