# Pagination Implementation Script - Quick Reference

## Overview

The `apply_pagination.py` script automatically applies the TIER 1 pagination pattern to all handler methods that return lists of items. It intelligently modifies SQL queries, adds pagination parameters, and wraps results in the standard `paginate_results()` format.

## Quick Start

### 1. Preview Changes (Recommended First Step)

```bash
# Preview what would change without modifying files
python scripts/apply_pagination.py --tier 2 --dry-run --verbose
```

### 2. Apply to TIER 2 (40 Core List Handlers)

```bash
# Apply pagination to TIER 2 handlers
python scripts/apply_pagination.py --tier 2
```

### 3. Validate Syntax

```bash
# Check Python syntax of all handler files
python scripts/apply_pagination.py --validate
```

### 4. Run Tests

```bash
# Run unit tests to verify changes
pytest tests/unit/ -v -m "not benchmark"
```

## Command Reference

### Basic Commands

| Command | Description |
|---------|-------------|
| `--dry-run` | Preview changes without modifying files |
| `--verbose` | Enable detailed logging |
| `--validate` | Check syntax of existing files only |

### Target Selection

| Command | Description | Example |
|---------|-------------|---------|
| `--tier N` | Apply to specific tier (2, 3, or 4) | `--tier 2` |
| `--file FILE` | Apply to specific file | `--file handlers_episodic.py` |
| `--all` | Apply to all handlers | `--all` |

### Example Workflows

#### Workflow 1: Safe Incremental Application

```bash
# Step 1: Preview changes for TIER 2
python scripts/apply_pagination.py --tier 2 --dry-run --verbose

# Step 2: Apply changes to TIER 2
python scripts/apply_pagination.py --tier 2

# Step 3: Validate syntax
python scripts/apply_pagination.py --validate

# Step 4: Run tests
pytest tests/unit/test_handlers_episodic.py -v
pytest tests/unit/test_handlers_prospective.py -v

# Step 5: Commit changes
git add src/athena/mcp/handlers_*.py
git commit -m "feat: Implement TIER 2 pagination for 40 core list handlers"
```

#### Workflow 2: File-by-File Application

```bash
# Apply to one file at a time for maximum control
python scripts/apply_pagination.py --file handlers_episodic.py --dry-run
python scripts/apply_pagination.py --file handlers_episodic.py
pytest tests/unit/test_handlers_episodic.py -v
git add src/athena/mcp/handlers_episodic.py
git commit -m "feat: Add pagination to episodic handlers"

# Repeat for each file
python scripts/apply_pagination.py --file handlers_prospective.py
pytest tests/unit/test_handlers_prospective.py -v
git commit -am "feat: Add pagination to prospective handlers"
```

#### Workflow 3: Bulk Application (After Validation)

```bash
# Apply to all handlers at once (use with caution)
python scripts/apply_pagination.py --all --dry-run
python scripts/apply_pagination.py --all
python scripts/apply_pagination.py --validate
pytest tests/unit/ tests/integration/ -v
```

## What the Script Does

### 1. Detects Handler Functions

Finds all `async def _handle_*` methods that return `list[TextContent]`

### 2. Checks for Existing Pagination

Skips handlers that already have:
- `paginate_results()` calls
- `limit = min(args.get("limit"` parsing

### 3. Injects Pagination Code

**a) Adds limit/offset parsing:**
```python
# Pagination
limit = min(args.get("limit", 10), 100)
offset = args.get("offset", 0)
```

**b) Modifies SQL queries:**
```python
# Original:
sql = "SELECT * FROM table ORDER BY field DESC"

# Modified:
# Get total count
count_sql = "SELECT COUNT(*) FROM table"
cursor.execute(count_sql, params)
total_count = cursor.fetchone()[0]

# Get paginated results
sql = "SELECT * FROM table ORDER BY field DESC LIMIT ? OFFSET ?"
cursor.execute(sql, (*params, limit, offset))
```

**c) Wraps return statement:**
```python
return paginate_results(
    results=formatted_results,
    args=args,
    total_count=total_count,
    operation="handler_name",
    drill_down_hint="Use get_item for full details"
).as_text_content()
```

### 4. Validates Syntax

Uses Python's `ast.parse()` to validate modified code

### 5. Creates Backups

Saves original files as `.bak` before modification

## Output Format

### Dry-Run Output

```
================================================================================
Processing TIER 2: Core List Operations (40 handlers)
================================================================================

Processing handlers_episodic.py...
  Processing _handle_recall_events_by_context...
  DEBUG: Handler found
  DEBUG: Not yet paginated
  ✓ Would inject pagination: _handle_recall_events_by_context
  ...

[DRY RUN] Would modify 6 handlers in handlers_episodic.py

================================================================================
PAGINATION INJECTION SUMMARY
================================================================================
Files Processed: 6
Handlers Modified: 40
Handlers Skipped (already paginated): 5
Syntax Errors: 0
================================================================================
```

### Actual Run Output

```
Processing handlers_episodic.py...
  ✓ Injected pagination: _handle_recall_events_by_context
  ✓ Injected pagination: _handle_recall_events_by_session
  ...
  ✓ Modified 6 handlers in handlers_episodic.py
  DEBUG: Backup created: handlers_episodic.py.bak

================================================================================
PAGINATION INJECTION SUMMARY
================================================================================
Files Processed: 6
Handlers Modified: 40
Handlers Skipped (already paginated): 5
Syntax Errors: 0
================================================================================
```

## Troubleshooting

### Issue: Syntax Errors After Modification

**Solution**: The script validates syntax automatically. If errors occur:

```bash
# Check which files have syntax errors
python scripts/apply_pagination.py --validate

# Restore from backup
cp src/athena/mcp/handlers_episodic.py.bak src/athena/mcp/handlers_episodic.py

# Try file-by-file approach
python scripts/apply_pagination.py --file handlers_episodic.py --verbose
```

### Issue: Handler Not Found

**Cause**: Handler name doesn't match pattern or doesn't exist

**Solution**: Check handler names in the file:
```bash
grep "async def _handle_" src/athena/mcp/handlers_episodic.py
```

### Issue: Script Modifies Already-Paginated Handler

**Cause**: Detection logic didn't recognize existing pagination

**Solution**: The script checks for `paginate_results(` and `limit = min(args.get("limit"`. If a handler uses a different pattern, it may not be detected. Restore from backup and add manual check.

### Issue: Tests Fail After Pagination

**Cause**: Tests may not pass pagination parameters

**Solution**: Update tests to include pagination args:
```python
# Before
result = await handler._handle_list_items({"query": "test"})

# After
result = await handler._handle_list_items({
    "query": "test",
    "limit": 10,
    "offset": 0
})
```

## Backup & Recovery

### Backups

The script creates `.bak` files before modifying:

```bash
# List backup files
ls -la src/athena/mcp/*.bak

# Restore specific file
cp src/athena/mcp/handlers_episodic.py.bak src/athena/mcp/handlers_episodic.py
```

### Full Recovery

```bash
# Restore all files from backups
for f in src/athena/mcp/*.bak; do
    cp "$f" "${f%.bak}"
done

# Or use git to reset
git checkout src/athena/mcp/handlers_*.py
```

## Testing Pagination

### Unit Test Example

```python
async def test_pagination():
    """Test handler pagination."""
    handler = EpisodicHandlersMixin()

    # Test default pagination
    result = await handler._handle_recall_events_by_context({
        "context_type": "test"
    })

    assert "limit" in result
    assert "offset" in result
    assert "total_count" in result
    assert len(result["results"]) <= 10  # Default limit

    # Test custom pagination
    result = await handler._handle_recall_events_by_context({
        "context_type": "test",
        "limit": 5,
        "offset": 10
    })

    assert len(result["results"]) <= 5
    assert result["offset"] == 10
```

### Integration Test Example

```python
async def test_pagination_across_modules():
    """Test pagination consistency."""
    # Test episodic handler
    episodic_result = await episodic._handle_list_sessions({"limit": 5})

    # Test prospective handler
    prospective_result = await prospective._handle_list_tasks({"limit": 5})

    # Both should follow same pagination pattern
    assert "results" in episodic_result
    assert "total_count" in episodic_result
    assert "results" in prospective_result
    assert "total_count" in prospective_result
```

## Performance Benchmarking

### Before/After Comparison

```python
import time

# Before pagination
start = time.time()
result = await handler._handle_list_items_old({})
time_before = time.time() - start
size_before = len(str(result))

# After pagination
start = time.time()
result = await handler._handle_list_items_new({"limit": 10})
time_after = time.time() - start
size_after = len(str(result))

print(f"Time improvement: {time_before / time_after:.2f}x faster")
print(f"Size improvement: {size_before / size_after:.2f}x smaller")
```

## Support

For issues or questions:

1. Check this README
2. Review `/home/user/.work/athena/docs/PAGINATION_IMPLEMENTATION_REPORT.md`
3. Examine script source: `scripts/apply_pagination.py`
4. Run with `--verbose` flag for detailed logging

## Next Steps

After completing pagination implementation:

1. **Run Full Test Suite**:
   ```bash
   pytest tests/ -v --timeout=300
   ```

2. **Update API Documentation**:
   - Document pagination parameters
   - Add examples with limit/offset
   - Update response format documentation

3. **Performance Benchmarking**:
   - Measure query performance improvements
   - Document token efficiency gains
   - Compare before/after metrics

4. **User Guide**:
   - Create pagination usage guide
   - Add best practices documentation
   - Include example API calls

---

**Script Version**: 1.0
**Last Updated**: November 13, 2025
**Author**: Claude Code
