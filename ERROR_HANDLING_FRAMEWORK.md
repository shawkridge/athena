# Error Handling Framework - Implementation Guide

## Status: Phase 1 Complete ✅

**Created**: Comprehensive exception hierarchy + fixed first 6 bare except handlers
**Next**: Systematic replacement of remaining 116+ broad exception handlers

---

## Architecture Overview

### Exception Hierarchy

```
AthenaError (base class)
├── StorageError
│   ├── DatabaseError (query failures)
│   ├── ConnectionError (connection failures)
│   └── SchemaError (schema issues)
├── DataError
│   ├── ParseError (JSON, CSV, AST, etc.)
│   ├── ValidationError (data validation)
│   └── EncodingError (text encoding/decoding)
├── OperationError
│   ├── QueryError (query execution)
│   ├── TransactionError (commit/rollback)
│   └── TimeoutError (operation timeout)
├── LayerError
│   ├── EpisodicError (Layer 1)
│   ├── SemanticError (Layer 2)
│   ├── ProceduralError (Layer 3)
│   ├── ProspectiveError (Layer 4)
│   ├── GraphError (Layer 5)
│   ├── MetaError (Layer 6)
│   └── ConsolidationError (Layer 7)
├── IntegrationError
│   ├── BridgeError (adapter failures)
│   └── LayerCommunicationError (inter-layer communication)
└── SystemError
    ├── ConfigurationError (config issues)
    ├── ResourceError (resource unavailability)
    └── StateError (invalid state)
```

### Key Features

**1. Rich Context**
```python
try:
    cursor.execute(sql)
except DatabaseError as e:
    e.with_context(
        table="episodic_events",
        operation="count_records",
        project_id=project_id
    )
    raise
```

**2. Error Codes & Timestamps**
- Automatic error codes (e.g., `DB_OPERATION_FAILED`, `PARSE_FAILED`)
- Timestamp tracking for when errors occurred
- Original exception preservation for debugging

**3. Handler Utilities**
```python
# Graceful degradation
except DatabaseError as e:
    handle_database_error(e, operation="count_events", context={"table": "episodic_events"})

except ParseError as e:
    handle_parse_error(e, data_type="json")

except OSError as e:
    handle_io_error(e, operation="read_config")
```

**4. Logging Integration**
```python
from athena.core.exceptions import ignore_error, log_and_continue

# Silent graceful degradation with debug logging
except DatabaseError as e:
    ignore_error(e, logger=logger, operation="table_count")

# Return default value with warning
except ParseError as e:
    config = log_and_continue(e, default_value={}, logger=logger, operation="load_config")
```

---

## Implementation Progress

### Phase 1: Foundation (COMPLETE) ✅

**Created**:
- `src/athena/core/exceptions.py` (443 lines)
  - 20+ custom exception types
  - ErrorContext builder
  - Handler utilities
  - Error code system

**Fixed**: 6 bare except handlers
- `src/athena/tools/memory/health.py:207-256`
  - All database table checks now use `(DatabaseError, Exception)`
  - Added debug logging for graceful degradation

**Commits**: 1 (086f3c6)

---

### Phase 2: Critical Bare Excepts (15 remaining)

**Priority Files & Pattern**:

#### A. Database Health Checks (9 instances)
- `src/athena/monitoring/layer_health_dashboard.py:285,334,380`
  - Pattern: Count queries with graceful fallback
  - Fix: Use `(DatabaseError, Exception)`
  - Files: 3 methods, 3 bare excepts

#### B. File I/O Operations (4 instances)
- `src/athena/code_artifact/manager.py:317,503`
  - Pattern: AST parsing + file reading
  - Fix: Use `SyntaxError` for AST, `(OSError, IOError)` for files
  - Files: 2 locations, 2 bare excepts
- `src/athena/ide_context/manager.py:59`
  - Pattern: File size/line count detection
  - Fix: Use `(OSError, IOError, UnicodeDecodeError)`
  - Files: 1 location, 1 bare except
- `src/athena/code_search/code_caching.py:1`
  - Pattern: Cache operation fallback
  - Fix: Use specific I/O exceptions
  - Files: 1 location, 1 bare except

#### C. Transaction Cleanup (2 instances)
- `src/athena/performance/batch_operations.py:189,331`
  - Pattern: ROLLBACK failure handling
  - Fix: Use `DatabaseError` with debug logging
  - Files: 2 locations, 2 bare excepts

---

### Phase 3: Except Exception Replacement (95+ instances)

**Approach**: Systematic replacement by layer and operation type

**Top Priority Files** (5 files with 16-29 instances each):
1. `working_memory/saliency.py`: 6 instances → Replace with `(ValueError, TypeError, KeyError)`
2. `planning/store.py`: 5 instances → Replace with `(ValueError, TypeError, KeyError)`
3. `analysis/project_analyzer.py`: 5 instances → Replace with `(SyntaxError, ValueError)`
4. `symbols/symbol_parser.py`: 4 instances → Replace with `(SyntaxError, ValueError)`
5. `ide_context/git_tracker.py`: 4 instances → Replace with `ProcessError` (custom)

**Strategy**: Fix top 5 files first (28 instances), then iterate by layer

---

## Pattern Examples

### Pattern 1: Database Table Checks
```python
# ❌ BEFORE
try:
    cursor.execute("SELECT COUNT(*) FROM episodic_events")
    count = cursor.fetchone()[0]
except:
    count = 0

# ✅ AFTER
try:
    cursor.execute("SELECT COUNT(*) FROM episodic_events")
    count = cursor.fetchone()[0]
except (DatabaseError, Exception) as e:
    logger.debug(f"Table episodic_events not accessible: {e}")
    count = 0
```

### Pattern 2: JSON Parsing
```python
# ❌ BEFORE
try:
    data = json.loads(json_str)
except:
    data = {}

# ✅ AFTER
try:
    data = json.loads(json_str)
except json.JSONDecodeError as e:
    logger.debug(f"JSON parsing failed: {e}")
    data = {}
```

### Pattern 3: AST Parsing
```python
# ❌ BEFORE
try:
    tree = ast.parse(code)
except:
    return None

# ✅ AFTER
try:
    tree = ast.parse(code)
except SyntaxError as e:
    logger.debug(f"Code syntax error: {e}")
    return None
```

### Pattern 4: File I/O
```python
# ❌ BEFORE
try:
    with open(path) as f:
        content = f.read()
except:
    content = None

# ✅ AFTER
try:
    with open(path) as f:
        content = f.read()
except (OSError, IOError, UnicodeDecodeError) as e:
    logger.debug(f"File read failed: {e}")
    content = None
```

---

## Testing & Validation

### Unit Tests to Add

```python
def test_database_error_with_context():
    """Test DatabaseError context injection."""
    e = DatabaseError("Query failed", context={"table": "events"})
    e.with_context(operation="count")
    assert e.context["table"] == "events"
    assert e.context["operation"] == "count"

def test_handle_database_error():
    """Test error handler conversion."""
    try:
        raise psycopg.DatabaseError("Connection lost")
    except Exception as e:
        ae = handle_database_error(e, operation="select")
        assert isinstance(ae, DatabaseError)
        assert ae.error_code == "DB_OPERATION_FAILED"
```

### Integration Tests

1. Verify all 21 bare excepts → specific exceptions
2. Verify all exception handlers preserve error context
3. Verify logging is working correctly
4. Verify graceful degradation still functions

---

## Rollout Plan

**Week 1**: Phases 1-2 (21 bare except handlers)
- Commit 1: Exception framework (done ✅)
- Commit 2: Fix 3 monitoring dashboard handlers
- Commit 3: Fix 4 file I/O handlers
- Commit 4: Fix 2 ROLLBACK handlers

**Week 2**: Phase 3 (95+ except Exception handlers)
- Commit 5-9: Top 5 files (28 instances)
- Commit 10-15: Next 10 files (35+ instances)
- Commit 16+: Remaining files by layer

**Week 3**: Testing & validation
- Unit tests for exception hierarchy
- Integration tests for error handling
- Verify all patterns applied correctly
- Performance impact analysis

---

## Benefits

1. **Debuggability**: Specific exceptions show exactly what failed
2. **Maintainability**: Clear exception types make code self-documenting
3. **Reliability**: Eliminates hidden failures from bare excepts
4. **Context**: Rich error information for troubleshooting
5. **Consistency**: Unified error handling across all layers

---

## Files Modified

- ✅ `src/athena/core/exceptions.py` (new)
- ✅ `src/athena/tools/memory/health.py` (6 fixes)
- 🔲 `src/athena/monitoring/layer_health_dashboard.py` (3 pending)
- 🔲 `src/athena/code_artifact/manager.py` (2 pending)
- 🔲 `src/athena/ide_context/manager.py` (1 pending)
- 🔲 `src/athena/code_search/code_caching.py` (1 pending)
- 🔲 `src/athena/performance/batch_operations.py` (2 pending)
- 🔲 95+ files with `except Exception:` handlers (Phase 3)

---

## References

- **Exception Hierarchy**: `src/athena/core/exceptions.py` (lines 1-50)
- **Handler Utilities**: `src/athena/core/exceptions.py` (lines 285-380)
- **Graceful Degradation**: `src/athena/core/exceptions.py` (lines 383-410)
- **First Implementation**: `src/athena/tools/memory/health.py:1-11` (imports)

