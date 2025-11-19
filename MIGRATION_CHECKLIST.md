# Consolidation System Migration - Implementation Checklist

**Status**: Code complete and tested ✅
**Next Step**: Execute migration on production database

---

## Pre-Migration Verification (DO THIS FIRST)

- [ ] Read `CONSOLIDATION_MIGRATION.md` completely
- [ ] Read `REFACTORING_SUMMARY.md` for context
- [ ] Review migration script: `src/athena/migrations/migrate_consolidation_system.py`
- [ ] Verify PostgreSQL is running and accessible
- [ ] Verify all 49 tests pass locally: `pytest claude/hooks/lib/test_*.py -v`
- [ ] Create backup of PostgreSQL database
- [ ] Schedule migration during low-traffic window

---

## Migration Day - Execute Steps in Order

### Step 1: Pre-Flight Check (15 min)

```bash
# Verify test suite still passing
pytest claude/hooks/lib/test_*.py -v

# Should see:
# ============================== 49 passed in 0.25s ==============================

# Verify database connection
python3 -c "
from athena.core.database import get_database
db = get_database()
print('Database connection OK')
"

# Should see: Database connection OK
```

**Checklist**:
- [ ] 49 tests pass
- [ ] Database connection works
- [ ] Python environment configured correctly

### Step 2: Execute Migration (5 min)

Create a migration script:

```python
# migration_runner.py
import asyncio
from athena.migrations import migrate_consolidation_system
from athena.core.database import initialize_database

async def run_migration():
    print("Initializing database...")
    db = await initialize_database()

    print("Starting consolidation system migration...")
    report = await migrate_consolidation_system(db)

    print("\n=== MIGRATION REPORT ===")
    print(f"Total events processed: {report['total_events']}")
    print(f"Events migrated: {report['migrated_events']}")
    print(f"\nVerification:")
    if 'verification' in report:
        for key, value in report['verification'].items():
            print(f"  {key}: {value}")

    if report['errors']:
        print(f"\n⚠️  ERRORS ENCOUNTERED:")
        for error in report['errors']:
            print(f"  - {error}")
        return False
    else:
        print("\n✅ Migration completed successfully!")
        return True

if __name__ == "__main__":
    success = asyncio.run(run_migration())
    exit(0 if success else 1)
```

Run the migration:

```bash
python migration_runner.py
```

**Expected Output**:
```
Initializing database...
Starting consolidation system migration...

=== MIGRATION REPORT ===
Total events processed: [count]
Events migrated: [count]

Verification:
  total: [count]
  consolidated: [count]
  active: [count]
  archived: 0

✅ Migration completed successfully!
```

**Checklist**:
- [ ] Migration script created
- [ ] Migration executes without errors
- [ ] Event counts match expectations
- [ ] No errors in report

### Step 3: Verify Data Integrity (10 min)

Run verification queries:

```sql
-- Check total event count
SELECT COUNT(*) as total FROM episodic_events;

-- Check lifecycle_status distribution
SELECT
  lifecycle_status,
  COUNT(*) as count
FROM episodic_events
GROUP BY lifecycle_status
ORDER BY lifecycle_status;

-- Check consolidation scores
SELECT
  CASE
    WHEN consolidation_score = 0.0 THEN 'zero'
    WHEN consolidation_score = 1.0 THEN 'one'
    ELSE 'other'
  END as score_category,
  COUNT(*) as count
FROM episodic_events
GROUP BY score_category;

-- Sample check: ensure old fields still exist and match
SELECT
  COUNT(*) as total_rows,
  SUM(CASE WHEN consolidation_status IS NOT NULL THEN 1 ELSE 0 END) as has_old_status,
  SUM(CASE WHEN consolidated_at IS NOT NULL THEN 1 ELSE 0 END) as has_old_timestamp
FROM episodic_events;
```

**Expected Results**:
```
1. Total count matches your database
2. lifecycle_status has 'active' and 'consolidated' (and maybe 'archived')
3. consolidation_score is either 0.0 or 1.0 mostly
4. Old fields still exist for backward compatibility
```

**Checklist**:
- [ ] Event counts verified
- [ ] lifecycle_status values correct
- [ ] consolidation_score values correct
- [ ] Old fields still present
- [ ] No NULL values in new required fields

### Step 4: Run Full Test Suite (2 min)

```bash
pytest claude/hooks/lib/test_*.py -v
```

**Expected**: 49 tests pass

**Checklist**:
- [ ] All 49 tests pass
- [ ] No new failures
- [ ] No warnings

### Step 5: Test Consolidation Pipeline (5 min)

Create a quick test:

```python
# test_consolidation_post_migration.py
import asyncio
from datetime import datetime, timedelta
from athena.core.database import get_database
from athena.episodic.store import EpisodicStore
from athena.semantic.store import SemanticStore
from athena.consolidation.pipeline import consolidate_episodic_to_semantic

async def test_consolidation():
    db = get_database()
    episodic_store = EpisodicStore(db)
    semantic_store = SemanticStore(db)

    print("Testing consolidation pipeline...")

    # Get active events
    active_events = episodic_store.get_events_by_timeframe(
        project_id=1,
        start=datetime.now() - timedelta(days=7),
        end=datetime.now(),
        lifecycle_status="active"
    )

    print(f"Found {len(active_events)} active events")

    # Run consolidation (dry run)
    report = consolidate_episodic_to_semantic(
        project_id=1,
        episodic_store=episodic_store,
        semantic_store=semantic_store,
        dry_run=True  # Don't actually consolidate
    )

    print(f"Would consolidate: {report.events_consolidated} events")
    print(f"Would extract: {report.patterns_extracted} patterns")
    print("\n✅ Consolidation pipeline works with new system!")

if __name__ == "__main__":
    asyncio.run(test_consolidation())
```

Run the test:

```bash
python test_consolidation_post_migration.py
```

**Expected Output**:
```
Testing consolidation pipeline...
Found X active events
Would consolidate: X events
Would extract: Y patterns

✅ Consolidation pipeline works with new system!
```

**Checklist**:
- [ ] Script runs without errors
- [ ] Finds active events correctly
- [ ] Consolidation pipeline works
- [ ] All status messages show success

---

## Post-Migration Monitoring (Week 1-2)

### Daily Checks

- [ ] Check application logs for errors
- [ ] Monitor consolidation pipeline execution
- [ ] Verify query performance (no slowdowns)
- [ ] Ensure no user-facing issues

### Weekly Checks

- [ ] Run full test suite: `pytest claude/hooks/lib/test_*.py -v`
- [ ] Check database size: `SELECT pg_size_pretty(pg_database_size('athena'))`
- [ ] Verify backup is valid
- [ ] Review consolidation statistics

### SQL Queries for Monitoring

```sql
-- Check recent consolidation activity
SELECT
  DATE(last_activation) as activation_date,
  COUNT(*) as consolidated_events
FROM episodic_events
WHERE lifecycle_status = 'consolidated'
GROUP BY DATE(last_activation)
ORDER BY activation_date DESC
LIMIT 7;

-- Check for any NULL values (should be zero)
SELECT
  SUM(CASE WHEN lifecycle_status IS NULL THEN 1 ELSE 0 END) as null_lifecycle,
  SUM(CASE WHEN last_activation IS NULL THEN 1 ELSE 0 END) as null_activation,
  SUM(CASE WHEN consolidation_score IS NULL THEN 1 ELSE 0 END) as null_score,
  SUM(CASE WHEN activation_count IS NULL THEN 1 ELSE 0 END) as null_count
FROM episodic_events;
```

---

## Cleanup Phase (After 1-2 Weeks of Stable Operation)

### Only Do This After Verifying Everything Works!

**Step 1: Drop Deprecated Columns** (5 min)

```sql
-- BACKUP YOUR DATABASE FIRST!
-- This is irreversible without restore!

ALTER TABLE episodic_events DROP COLUMN consolidation_status;
ALTER TABLE episodic_events DROP COLUMN consolidated_at;
DROP INDEX IF EXISTS idx_events_consolidation;
```

**Checklist**:
- [ ] Verified stable operation for 1-2 weeks
- [ ] Database backup created
- [ ] All tests still passing
- [ ] No issues reported

### Step 2: Code Cleanup (15 min)

Remove backward compatibility code from `src/athena/episodic/store.py`:

1. Simplify `get_events_by_timeframe()`:
   - Remove `consolidation_status` parameter
   - Remove backward compatibility fallback
   - Keep only `lifecycle_status` check

2. Simplify `mark_event_consolidated()`:
   - Remove updates to `consolidation_status`
   - Remove updates to `consolidated_at`
   - Keep only new system updates

3. Update `_row_to_model()`:
   - Remove old field mappings
   - Keep only new field mappings

**Checklist**:
- [ ] Backward compatibility code removed
- [ ] All 49 tests still pass
- [ ] Code review completed

### Step 3: Documentation Update (5 min)

- [ ] Update comments mentioning old system
- [ ] Remove "deprecated" markers
- [ ] Update CONSOLIDATION_MIGRATION.md status to "Complete"

**Checklist**:
- [ ] All references to old system updated
- [ ] Documentation reflects new system
- [ ] CHANGELOG updated

---

## Rollback Procedure (If Issues Occur)

If something goes wrong, follow these steps:

### Step 1: Immediate Action

```python
# rollback.py
import asyncio
from athena.migrations import rollback_migration
from athena.core.database import get_database

async def run_rollback():
    print("Rolling back consolidation system migration...")
    db = get_database()
    report = await rollback_migration(db)

    if report['rolled_back']:
        print("✅ Rollback successful!")
        print("  Old fields restored from new system")
        print("  New fields left intact for re-migration")
    else:
        print("⚠️  Rollback failed!")
        print(f"  Error: {report['error']}")
        print("  Contact database administrator for manual rollback")

asyncio.run(run_rollback())
```

Run rollback:
```bash
python rollback.py
```

### Step 2: Verify Rollback

```sql
-- Check that old fields are restored
SELECT
  COUNT(*) as total,
  SUM(CASE WHEN consolidation_status IS NOT NULL THEN 1 ELSE 0 END) as has_status,
  SUM(CASE WHEN consolidated_at IS NOT NULL THEN 1 ELSE 0 END) as has_timestamp
FROM episodic_events
WHERE consolidation_status IS NOT NULL;
```

### Step 3: Contact Support

If rollback doesn't work:
1. Restore from backup
2. Document the issue
3. Contact Anthropic support or Claude Code team

---

## Success Criteria

Migration is successful when:

✅ All 49 tests pass
✅ Event counts verified
✅ lifecycle_status populated correctly
✅ consolidation_score values correct
✅ Consolidation pipeline works
✅ No errors in logs
✅ Query performance maintained
✅ Backup validation passes

---

## Timeline

| Phase | Duration | Status |
|-------|----------|--------|
| Pre-flight check | 15 min | Start here |
| Execute migration | 5 min | Automated |
| Data verification | 10 min | Manual check |
| Test suite | 2 min | Automated |
| Pipeline test | 5 min | Manual test |
| **Total Time** | **37 min** | One-time |
| Monitoring | 1-2 weeks | Ongoing |
| Cleanup | 25 min | When ready |

---

## Support & Help

If you encounter issues:

1. **Check logs**: Look for error messages in application logs
2. **Verify database**: Run verification SQL queries
3. **Review guide**: Read `CONSOLIDATION_MIGRATION.md` for troubleshooting
4. **Rollback if needed**: Use rollback procedure above
5. **Contact support**: Reach out for complex issues

---

## Questions?

Refer to:
- `CONSOLIDATION_MIGRATION.md` - Complete migration guide
- `REFACTORING_SUMMARY.md` - Project overview
- `CLAUDE.md` - Development guidelines
- Source code comments

---

**Version**: 1.0
**Created**: November 19, 2025
**Ready for**: Production deployment
