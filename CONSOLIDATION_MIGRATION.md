# Consolidation System Migration Guide

## Overview

This document describes the one-time migration from the old consolidation system (`consolidation_status`, `consolidated_at`) to the new lifecycle system (`lifecycle_status`, `consolidation_score`, `last_activation`, `activation_count`).

**Status**: Migration code complete and tested. Ready for execution.

## Why Migrate?

The old system had limitations:
- Boolean-like status ('consolidated' or 'unconsolidated') doesn't capture nuance
- `consolidated_at` is a single timestamp, doesn't track access patterns
- Hard to distinguish between "freshly consolidated" and "old, stale consolidation"

The new system provides:
- **lifecycle_status**: Clear semantic states (active, consolidated, archived)
- **consolidation_score**: Confidence score (0.0-1.0) that pattern was extracted
- **last_activation**: When memory was last accessed/retrieved
- **activation_count**: How many times memory has been accessed

## Migration Process

### Phase 1: Backfill New Fields

For each event in the database:
```sql
IF consolidation_status = 'consolidated':
  SET lifecycle_status = 'consolidated'
  SET consolidation_score = 1.0
  SET last_activation = consolidated_at (or NOW())
  SET activation_count = 1
ELSE:
  SET lifecycle_status = 'active'
  SET consolidation_score = 0.0
  SET activation_count = 0
```

**Result**: All events have both old and new fields properly populated.

### Phase 2: Update Code to Use New System

✅ **Already completed**:
- Consolidation pipeline: Uses `lifecycle_status="active"` instead of `consolidation_status="unconsolidated"`
- Store methods: Updated to read/write new fields
- Model: Removed deprecated fields from Python dataclass

### Phase 3: Execute Migration

```python
from athena.migrations import migrate_consolidation_system
from athena.core.database import get_database

# Get database instance
db = await initialize_database()

# Run migration
report = await migrate_consolidation_system(db)

# Check results
print(f"Migrated {report['migrated_events']} events")
print(f"Verification: {report['verification']}")
```

### Phase 4: Cleanup (After Verification)

Once migration is verified as successful (compare event counts and sample data):

1. Remove deprecated fields from schema:
```sql
ALTER TABLE episodic_events DROP COLUMN consolidation_status;
ALTER TABLE episodic_events DROP COLUMN consolidated_at;
```

2. Remove backward compatibility code from `store.py`:
- Remove fallback to `consolidation_status` in `get_events_by_timeframe()`
- Simplify `mark_event_consolidated()` to only update new fields

3. Update any remaining code that references deprecated fields

## Execution Plan

### Prerequisites
- All 49 tests passing ✅
- Database connection available
- Backup of PostgreSQL database (recommended)

### Step 1: Execute Migration

```bash
cd /home/user/.work/athena
python -c "
import asyncio
from athena.migrations import migrate_consolidation_system
from athena.core.database import initialize_database

async def main():
    db = await initialize_database()
    report = await migrate_consolidation_system(db)
    print('Migration complete:')
    print(f'  Total events: {report[\"total_events\"]}')
    print(f'  Migrated events: {report[\"migrated_events\"]}')
    print(f'  Verification: {report[\"verification\"]}')
    if report['errors']:
        print(f'  Errors: {report[\"errors\"]}')

asyncio.run(main())
"
```

### Step 2: Verify Migration

Check that:
1. All events have `lifecycle_status` set
2. Consolidated events have `consolidation_score = 1.0`
3. Active events have `consolidation_score = 0.0`
4. `activation_count` is set correctly

```sql
SELECT
  COUNT(*) as total,
  SUM(CASE WHEN lifecycle_status = 'consolidated' THEN 1 ELSE 0 END) as consolidated,
  SUM(CASE WHEN lifecycle_status = 'active' THEN 1 ELSE 0 END) as active,
  SUM(CASE WHEN lifecycle_status = 'archived' THEN 1 ELSE 0 END) as archived,
  MIN(consolidation_score) as min_score,
  MAX(consolidation_score) as max_score,
  AVG(activation_count) as avg_activation_count
FROM episodic_events;
```

### Step 3: Run Tests

```bash
pytest claude/hooks/lib/test_*.py -v
```

Should still show 49/49 passing.

### Step 4: Cleanup (Optional)

After verifying migration is successful and stable (1-2 weeks recommended):

1. Run schema cleanup:
```sql
ALTER TABLE episodic_events DROP COLUMN consolidation_status;
ALTER TABLE episodic_events DROP COLUMN consolidated_at;
DROP INDEX IF EXISTS idx_events_consolidation;
```

2. Remove backward compatibility code from `src/athena/episodic/store.py`:
   - Simplify `get_events_by_timeframe()` to only check `lifecycle_status`
   - Remove old system fallback
   - Simplify `mark_event_consolidated()` to only update new fields

3. Update any documentation or comments that reference old system

## Rollback Plan

If migration causes issues:

```python
from athena.migrations import rollback_migration
from athena.core.database import get_database

db = get_database()
report = await rollback_migration(db)
print(f"Rolled back: {report['rolled_back']}")
if report['error']:
    print(f"Error: {report['error']}")
```

This will:
- Restore `consolidation_status` from `lifecycle_status`
- Restore `consolidated_at` from `last_activation`
- Leave new fields intact for re-migration later

## Testing After Migration

The consolidation pipeline should continue to work seamlessly:

```bash
# Test consolidation
python -c "
import asyncio
from athena.consolidation.pipeline import consolidate_episodic_to_semantic
from athena.core.database import get_database
from athena.episodic.store import EpisodicStore
from athena.semantic.store import SemanticStore

async def test_consolidation():
    db = get_database()
    episodic_store = EpisodicStore(db)
    semantic_store = SemanticStore(db)

    # Run consolidation
    report = consolidate_episodic_to_semantic(
        project_id=1,
        episodic_store=episodic_store,
        semantic_store=semantic_store,
        dry_run=True  # Don't actually consolidate
    )

    print(f'Would consolidate {report.events_consolidated} events')
    print(f'Would extract {report.patterns_extracted} patterns')

asyncio.run(test_consolidation())
"
```

## Field Mapping Reference

### Old System → New System

| Old Field | Old Values | New Field | New Values |
|-----------|-----------|-----------|-----------|
| `consolidation_status` | 'unconsolidated', 'consolidated', NULL | `lifecycle_status` | 'active', 'consolidated', 'archived' |
| `consolidated_at` | TIMESTAMP (when consolidated) | `last_activation` | TIMESTAMP (last access) |
| - | - | `consolidation_score` | 0.0-1.0 (confidence) |
| - | - | `activation_count` | INT (access count) |

### Mapping Rules

1. **Unconsolidated events**:
   - `consolidation_status = NULL or 'unconsolidated'`
   - → `lifecycle_status = 'active'`
   - → `consolidation_score = 0.0`
   - → `activation_count = 0`

2. **Consolidated events**:
   - `consolidation_status = 'consolidated'`
   - → `lifecycle_status = 'consolidated'`
   - → `consolidation_score = 1.0`
   - → `last_activation = consolidated_at`
   - → `activation_count = 1`

3. **Archived events** (new):
   - `lifecycle_status = 'archived'` (manual designation)
   - → Events no longer actively used
   - → Excluded from consolidation queries

## Performance Impact

**Before Migration**:
- Consolidation queries: `WHERE consolidation_status = 'unconsolidated'`
- Index: `idx_events_consolidation (project_id, consolidation_status)`

**After Migration**:
- Consolidation queries: `WHERE lifecycle_status = 'active'`
- Index: `idx_events_lifecycle (project_id, lifecycle_status)` (auto-created if needed)

**Expected**:
- Same or slightly better query performance
- Index size same or slightly smaller
- Memory usage reduced (removed client-side filtering)

## FAQ

### Q: Can I run the migration on a live system?
**A**: Yes. The migration is read-heavy and uses transactions, so it's safe on a live system. Recommended to run during low-traffic hours.

### Q: What if migration fails midway?
**A**: Use the `rollback_migration()` function to restore the old system. The migration is idempotent, so you can re-run it.

### Q: Do I need to update my code?
**A**: No. Code changes are already complete. The migration just syncs the database.

### Q: When should I clean up the deprecated fields?
**A**: After 1-2 weeks of successful production operation. This gives time to catch any edge cases.

### Q: What about events created after migration starts?
**A**: New events will have both old and new fields set by `mark_event_consolidated()`. This is handled automatically.

## References

- **Migration Script**: `src/athena/migrations/migrate_consolidation_system.py`
- **Consolidation Pipeline**: `src/athena/consolidation/pipeline.py`
- **Episodic Store**: `src/athena/episodic/store.py`
- **Database Schema**: `src/athena/core/database_postgres.py`
- **Tests**: `claude/hooks/lib/test_*.py` (49 tests)

## Timeline

1. **Immediate**: Run migration script
2. **Day 1**: Verify data integrity
3. **Week 1-2**: Monitor consolidation pipeline
4. **After verification**: Clean up deprecated fields

---

**Version**: 1.0
**Created**: November 19, 2025
**Status**: Ready for production migration
