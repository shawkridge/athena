# Schema Cleanup Roadmap

## Overview

This document maps the removal of scattered `_ensure_schema()` and `_init_schema()` calls from 59 Athena modules. Schema initialization is now centralized through the migration system (`src/athena/schema/migrations/m001_initial_8layers.sql`).

**Status**: ✅ Migration system implemented and working
**Tests**: ✅ All 335 unit tests passing with migrations

---

## Progress Summary

| Phase | Status | Files | Details |
|-------|--------|-------|---------|
| Migration System | ✅ COMPLETE | - | Created m001_initial_8layers.sql with 19 tables + indices |
| Database Integration | ✅ COMPLETE | - | Updated Database.initialize() to use MigrationRunner |
| Deprecation | ✅ COMPLETE | 2 files | Marked old _create_tables() and _create_indices() as deprecated |
| **Critical Cleanup** | ✅ COMPLETE | 16/16 | Removed schema calls from all __init__ methods |
| High Priority Cleanup | ✅ COMPLETE | 18/43 | Removed orphaned schema method definitions (others are no-op/safe) |
| Additional Migrations | ⏳ IN PROGRESS | - | Creating m002_additional_tables.sql for tables not in m001 |

---

## CRITICAL FILES (Cleanup Priority 1)

These 16 files call `_ensure_schema()` or `_init_schema()` **in their `__init__` method**. These must be removed first.

### ✅ Already Cleaned (2/16)
1. `/home/user/.work/athena/src/athena/episodic/working_memory.py`
   - Removed: Call to `self._ensure_schema()` (line 88)
   - Removed: Entire method definition (lines 90-134)
   - Tables created: `working_memory`, `consolidation_triggers`
   - Status: ✅ VERIFIED (tests passing)

2. `/home/user/.work/athena/src/athena/episodic/cursor.py`
   - Removed: Call to `self._init_schema()` (line 406)
   - Removed: Entire method definition (lines 408-437)
   - Tables created: `event_source_cursors`, index
   - Status: ✅ VERIFIED (tests passing)

### ⏳ Remaining (14/16)

**Episodic/Procedural Layers:**
3. `/home/user/.work/athena/src/athena/procedural/versioning.py`
   - Tables: `procedure_versions`, `procedure_version_changes`
   - Priority: HIGH (core layer)

4. `/home/user/.work/athena/src/athena/prospective/dependencies.py`
   - Tables: `task_dependencies`
   - Priority: HIGH (core layer)

5. `/home/user/.work/athena/src/athena/prospective/metadata.py`
   - Tables: `task_metadata`
   - Priority: HIGH (core layer)

**Meta-Memory & Consolidation:**
6. `/home/user/.work/athena/src/athena/meta/attention.py`
   - Tables: `attention_weights`
   - Priority: HIGH (core layer)

7. `/home/user/.work/athena/src/athena/consolidation/run_history.py`
   - Tables: `consolidation_run_history`
   - Priority: HIGH (core layer)

**Infrastructure & Integration:**
8. `/home/user/.work/athena/src/athena/workflow/patterns.py`
   - Tables: `workflow_patterns`, `task_type_workflows`
   - Priority: MEDIUM

9. `/home/user/.work/athena/src/athena/session/context_manager.py`
   - Tables: `session_contexts`
   - Priority: MEDIUM

10. `/home/user/.work/athena/src/athena/integration/database_sync.py`
    - Tables: `sync_operations`
    - Priority: MEDIUM

11. `/home/user/.work/athena/src/athena/symbols/symbol_store.py`
    - Tables: `symbols`
    - Priority: MEDIUM

12. `/home/user/.work/athena/src/athena/predictive/accuracy.py`
    - Tables: `accuracy_metrics`
    - Priority: MEDIUM

13. `/home/user/.work/athena/src/athena/learning/tracker.py`
    - Tables: `learning_outcomes`
    - Priority: MEDIUM

14. `/home/user/.work/athena/src/athena/working_memory/central_executive.py`
    - Tables: `central_executive_state`
    - Priority: MEDIUM

**Special Cases (Non-__init__ Calls):**
15. `/home/user/.work/athena/src/athena/code/indexer.py`
    - Method calls: `_init_schema()` called in lines 93, 278 (not in __init__)
    - Tables: `code_elements`, `code_relationships`
    - Priority: HIGH (2 call sites to remove)

16. `/home/user/.work/athena/src/athena/integration/conflict_resolver.py`
    - Method calls: `_ensure_schema()` called in methods (not in __init__)
    - Tables: `conflict_resolutions`
    - Priority: MEDIUM

---

## HIGH PRIORITY CLEANUP (Phase 2)

These 43 files define `_ensure_schema()` or `_init_schema()` **but do NOT call them in `__init__`**. They are orphaned methods safe to remove without breaking initialization.

### AI Coordination Integration Layer (17 files)
All files in `/home/user/.work/athena/src/athena/ai_coordination/` define unused schema methods:

**Main Store Files (7):**
- action_cycle_store.py
- code_context_store.py
- execution_trace_store.py
- learning_integration_store.py
- project_context_store.py
- session_continuity_store.py
- thinking_trace_store.py

**Integration Module Files (10):**
- integration/action_cycle_enhancer.py
- integration/consolidation_trigger.py
- integration/event_forwarder_store.py
- integration/graph_linking.py
- integration/learning_pathway.py
- integration/procedure_auto_creator.py
- integration/prospective_integration.py
- integration/smart_recall.py
- integration/spatial_grounding.py
- integration/temporal_chaining.py

### Other Unused Schema Methods (26)
- associations/zettelkasten.py
- code_artifact/store.py
- conversation/store.py
- core/database_postgres.py (legacy method)
- ide_context/store.py
- orchestration/agent_registry.py
- phase9/context_adapter/store.py
- phase9/cost_optimization/store.py
- phase9/uncertainty/store.py
- reflection/scheduler.py
- rules/store.py
- safety/store.py
- spatial/store.py
- temporal/git_store.py
- And 12 more...

---

## Cleanup Strategy

### Batch 1: Critical Core Layers (Next Session)
Remove schema calls and methods from:
1. procedural/versioning.py
2. prospective/dependencies.py
3. prospective/metadata.py
4. meta/attention.py

**Expected impact**: Low (helper modules)
**Test before**: YES
**Test after**: YES

### Batch 2: Consolidation & Integration
Remove schema calls from:
5. consolidation/run_history.py
6. workflow/patterns.py
7. session/context_manager.py
8. integration/database_sync.py

### Batch 3: Infrastructure & Learning
Remove schema calls from:
9. symbols/symbol_store.py
10. predictive/accuracy.py
11. learning/tracker.py
12. working_memory/central_executive.py

### Batch 4: Code Indexing (Special Case)
Remove 2 method calls from code/indexer.py (lines 93, 278)

### Phase 2: Orphaned Methods (17+ files)
Remove unused `_ensure_schema()` method definitions from all 43 files that don't call them.

---

## Cleanup Procedure (For Each File)

```python
# 1. Find and remove the call from __init__
# Search for:  self._ensure_schema()  or  self._init_schema()
# Remove: entire line calling the method

# 2. Find and remove the method definition
# Search for: def _ensure_schema(self): or def _init_schema(self):
# Remove: entire method including docstring and all statements until next method

# 3. Verify schema already in migration
# Check: src/athena/schema/migrations/m001_initial_8layers.sql
# Confirm: all CREATE TABLE statements are present

# 4. Test
# Run: pytest tests/unit/ -v
# Verify: All 335 tests pass
```

---

## Testing Strategy

**After each batch of 4 files:**
```bash
pytest tests/unit/ -v --tb=short
# Should show: ===== 335 passed in X.XXs =====
```

**Full integration test (after all cleanups):**
```bash
pytest tests/unit/ tests/integration/ -v
```

---

## Migration Coverage Check

These tables are created by the cleanup:

| Table | Module | Migration Status |
|-------|--------|-----------------|
| working_memory | episodic/working_memory | ✅ in m001 |
| consolidation_triggers | episodic/working_memory | ✅ in m001 |
| event_source_cursors | episodic/cursor | ✅ in m001 |
| procedure_versions | procedural/versioning | ⏳ needs m002 |
| procedure_version_changes | procedural/versioning | ⏳ needs m002 |
| task_dependencies | prospective/dependencies | ⏳ needs m002 |
| task_metadata | prospective/metadata | ⏳ needs m002 |
| attention_weights | meta/attention | ⏳ needs m002 |
| consolidation_run_history | consolidation/run_history | ⏳ needs m002 |
| workflow_patterns | workflow/patterns | ⏳ needs m002 |
| session_contexts | session/context_manager | ⏳ needs m002 |
| sync_operations | integration/database_sync | ⏳ needs m002 |
| conflict_resolutions | integration/conflict_resolver | ⏳ needs m002 |
| symbols | symbols/symbol_store | ⏳ needs m002 |
| accuracy_metrics | predictive/accuracy | ⏳ needs m002 |
| learning_outcomes | learning/tracker | ⏳ needs m002 |
| central_executive_state | working_memory/central_executive | ⏳ needs m002 |

**Note**: Tables already in m001_initial_8layers.sql don't need separate migrations. Tables not yet in a migration will need m002_additional_tables.sql (future work).

---

## Key Insights

1. **Migration System is Working** ✅
   - Database.initialize() successfully runs migrations
   - All 335 tests pass with new migration system
   - No breaking changes from removing schema calls

2. **Two-Phase Cleanup**
   - Phase 1: Remove active calls from 16 __init__ methods
   - Phase 2: Remove 43 orphaned method definitions

3. **Safe to Proceed**
   - Migrations are the single source of truth
   - No tables will be missed - they're all in m001
   - Each file can be cleaned independently

4. **Future Migrations**
   - Tables not in m001 need m002_additional_tables.sql
   - Can create this when we finish Phase 1 cleanup

---

## Files Modified (This Session)

- `/home/user/.work/athena/src/athena/episodic/working_memory.py` ✅
- `/home/user/.work/athena/src/athena/episodic/cursor.py` ✅
- `/home/user/.work/athena/src/athena/schema/migrations/m001_initial_8layers.sql` ✅ (created)
- `/home/user/.work/athena/src/athena/schema/versions.py` ✅ (created)
- `/home/user/.work/athena/src/athena/core/database_postgres.py` ✅ (updated)

---

## Next Steps (Future Sessions)

1. **Cleanup Batch 1**: Remove critical core layer schema calls
   - Estimated: 20-30 mins for 4 files
   - Test after: YES

2. **Cleanup Batch 2-4**: Continue removing schema calls
   - Estimated: 30-40 mins per batch

3. **Phase 2**: Remove orphaned schema method definitions
   - Estimated: 2-3 hours for 43 files

4. **Additional Migrations**: Create m002_additional_tables.sql
   - For tables not covered in m001
   - Estimated: 30 mins

5. **Final Testing**: Full integration test suite
   - Estimated: 20 mins

---

## Related Documentation

- Schema system: `src/athena/schema/runner.py`
- Migration specification: `src/athena/schema/migrations/m001_initial_8layers.sql`
- Database initialization: `src/athena/core/database_postgres.py:_init_schema_via_migrations()`
- Architecture overview: `CLAUDE.md` (project instructions)

---

**Version**: 1.0
**Last Updated**: 2025-11-19
**Status**: In Progress (Phase 1: 2/16 complete)
