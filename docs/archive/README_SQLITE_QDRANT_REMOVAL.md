# SQLite & Qdrant Removal - Complete Analysis & Implementation Guide

This directory contains comprehensive analysis and implementation guidance for removing all SQLite and Qdrant references from the Athena codebase, migrating exclusively to PostgreSQL + pgvector.

## Documents Provided

### 1. [SQLITE_QDRANT_REMOVAL_ANALYSIS.md](./SQLITE_QDRANT_REMOVAL_ANALYSIS.md)
**Primary Reference Document** - 345 lines

Complete analysis of all SQLite and Qdrant references in the codebase, organized by priority.

**Contains:**
- Executive summary of findings
- File-by-file priority breakdown (5 priorities)
- Current status of each file (imports, active usage, comments)
- Specific action items for each file
- Phase-based implementation plan
- Effort estimates (3-5 days total)
- Success criteria and validation checklist
- Critical success factors and implementation notes

**Start here if you want:** Complete understanding of scope

### 2. [SQLITE_QDRANT_CODE_EXAMPLES.md](./SQLITE_QDRANT_CODE_EXAMPLES.md)
**Implementation Reference** - 425 lines

Detailed code patterns and before/after migration examples for common scenarios.

**Contains:**
- 10 detailed migration patterns with code examples
  1. Replace sqlite3.connect() with PostgreSQL
  2. Replace sqlite3 exceptions with psycopg exceptions
  3. Remove Qdrant fallback from search
  4. Remove dual-write logic
  5. Remove sqlite3 type hints
  6. Remove Qdrant imports
  7. Update exception handling patterns
  8. Remove sqlite3.Row conversions
  9. Remove Qdrant health checks
  10. Replace direct database path usage
- Import change recommendations
- Exception handler replacements
- Type hint updates
- File-by-file checklist
- Verification scripts and tests

**Start here if you want:** Code examples and migration patterns

## Quick Reference Tables

### Files by Priority

**PRIORITY 1: CRITICAL (8 files - active sqlite3 code)**
- src/athena/executive/progress.py - sqlite3.connect() calls
- src/athena/executive/metrics.py - sqlite3.connect() calls
- src/athena/executive/conflict.py - sqlite3 usage
- src/athena/executive/strategy.py - sqlite3 usage
- src/athena/core/production.py - sqlite3 exceptions
- src/athena/compression/schema.py - sqlite3.connect() calls
- src/athena/monitoring/health.py - sqlite3.connect() calls
- src/athena/resilience/degradation.py - sqlite3 exceptions
- **Est. Time: 12-15 hours**

**PRIORITY 2: QDRANT REMOVAL (3 files)**
- src/athena/rag/qdrant_adapter.py - DELETE entire file
- src/athena/memory/search.py - Remove Qdrant fallback
- src/athena/memory/store.py - Remove dual-write
- **Est. Time: 4-5 hours**

**PRIORITY 3: IMPORT CLEANUP (16 files)**
- Store layer files: episodic/, procedural/, graph/, prospective/, meta/, safety/, planning/, research/, symbols/, ide_context/, rules/, working_memory/
- **Est. Time: 2-3 hours**

**PRIORITY 4: FALLBACK FIXES (2 files)**
- src/athena/mcp/memory_api.py - Remove backend='sqlite'
- src/athena/mcp/executive_function_tools.py - Clean up error handling
- **Est. Time: 2 hours**

**PRIORITY 5: DOCUMENTATION (minimal)**
- Comments/docstring updates
- **Est. Time: 15 minutes**

### Implementation Phases

| Phase | Files | Goal | Time |
|-------|-------|------|------|
| 1 | 8 (Priority 1) | Migrate active SQLite code | 1-2 days |
| 2 | 3 (Priority 2) | Remove Qdrant entirely | 1 day |
| 3 | 16 (Priority 3) | Clean store imports | 2-3 hrs |
| 4 | 2 (Priority 4) | Fix fallback logic | 2 hrs |
| 5 | All | Testing & validation | 1-2 days |
| **TOTAL** | **26+ files** | **Complete migration** | **3-5 days** |

## Key Statistics

- **Total files with SQLite/Qdrant references:** 26+
- **Files with active code (not just comments):** 8
- **Files with imports only (easy cleanup):** 16
- **Fallback implementations:** 2
- **Lines of code to remove:** ~2,000+

## Migration Strategy

### Phase 1: Critical SQLite Code (1-2 days)
Migrate 5 executive function files and core/production.py from sqlite3 to PostgreSQL async.

### Phase 2: Qdrant Removal (1 day)
Remove all Qdrant fallback logic and delete qdrant_adapter.py.

### Phase 3: Store Layer Cleanup (2-3 hours)
Remove unused sqlite3 imports from 16 store files.

### Phase 4: Fix Fallback Issues (2 hours)
Update forced SQLite parameters to use PostgreSQL factory.

### Phase 5: Testing & Validation (1-2 days)
Run full test suite with PostgreSQL only.

## Critical Success Criteria

After removal, verify:
- [ ] Zero `import sqlite3` statements
- [ ] Zero `import qdrant` statements
- [ ] Zero `sqlite3.` references (except in removed code)
- [ ] All exceptions use `psycopg.errors.*`
- [ ] No Qdrant fallback logic remains
- [ ] No dual-write logic in memory store
- [ ] qdrant_adapter.py deleted
- [ ] All tests pass with PostgreSQL
- [ ] No commented-out SQLite code

## Common Migration Patterns

### Exception Handling
```python
# Before (SQLite)
except sqlite3.IntegrityError:

# After (PostgreSQL)
except psycopg.errors.IntegrityError:
```

### Direct Connections
```python
# Before (SQLite)
conn = sqlite3.connect(db_path)

# After (PostgreSQL)
db = PostgresDatabase()  # Use factory/pool
```

### Type Hints
```python
# Before (SQLite)
def _row_to_model(self, row: sqlite3.Row):

# After (PostgreSQL)
def _row_to_model(self, row: Dict[str, Any]):
```

## Recommended Implementation Order

1. **memory_api.py** (quick win - 1 hour)
2. **core/production.py** (high impact - 1-2 hours)
3. **executive/progress.py** (active code - 2 hours)
4. **executive/metrics.py** (active code - 2 hours)
5. **executive/conflict.py** (active code - 1-2 hours)
6. **executive/strategy.py** (active code - 1-2 hours)
7. **compression/schema.py** (active code - 1 hour)
8. **monitoring/health.py** (active code - 1 hour)
9. **resilience/degradation.py** (exceptions - 1 hour)
10. **memory/search.py** (remove Qdrant - 2-3 hours)
11. **memory/store.py** (remove dual-write - 1-2 hours)
12. **16 store files** (cleanup - 2-3 hours, parallel)
13. **Delete qdrant_adapter.py** (final cleanup - 30 min)

## Tools & Verification

### Grep Commands to Verify Removal
```bash
# Find remaining SQLite references
grep -r "import sqlite3" src/athena/
grep -r "sqlite3\." src/athena/
grep -r "import qdrant" src/athena/

# Check that qdrant_adapter.py is deleted
ls src/athena/rag/qdrant_adapter.py

# Run tests
pytest tests/ -v --tb=short
```

### Files Already Migrated
These files are PostgreSQL-only already:
- ✓ src/athena/core/database.py
- ✓ src/athena/core/database_factory.py
- ✓ src/athena/core/database_postgres.py

## FAQ

**Q: Should I keep Qdrant as a fallback?**
A: No. Remove all fallback logic. PostgreSQL must be the only path.

**Q: Can I migrate files in parallel?**
A: No. Follow the recommended order. Some files depend on others.

**Q: Should I commit after each file?**
A: Yes. One atomic commit per file with clear message.

**Q: What about backward compatibility?**
A: None needed. Migrate to PostgreSQL only.

**Q: How do I test?**
A: Use the PostgreSQL test database. No mocking of database layer.

## More Information

For detailed information on specific files, see:
- [SQLITE_QDRANT_REMOVAL_ANALYSIS.md](./SQLITE_QDRANT_REMOVAL_ANALYSIS.md) - Complete analysis
- [SQLITE_QDRANT_CODE_EXAMPLES.md](./SQLITE_QDRANT_CODE_EXAMPLES.md) - Code examples

For questions about the analysis, refer to the priority breakdown and effort estimates in the analysis document.

---

**Status:** Analysis Complete  
**Date:** November 11, 2025  
**Effort Required:** 3-5 days (20-35 hours)  
**Impact:** Zero technical debt, single database backend
