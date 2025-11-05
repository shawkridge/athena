# Comprehensive Migration Guide: memory-mcp → Athena

**Date**: November 5, 2025
**Status**: ✅ Core Fixes Complete (Documentation & References Remaining)
**Scope**: Complete path migration from `~/.work/claude/memory-mcp` to `~/.work/athena`

---

## Executive Summary

This guide documents the complete migration process from the old `memory-mcp` project structure to the new unified `Athena` project. The migration includes:

1. ✅ **Critical Path Fixes** (Primary execution paths)
2. ⏳ **Documentation Updates** (References in comments/docs)
3. ⏳ **Test Updates** (Test database paths)
4. ⏳ **Script Updates** (Migration and utility scripts)

**Current Status**: All critical execution paths fixed. Testing and documentation updates in progress.

---

## Part 1: Critical Path Fixes ✅ COMPLETE

These are the files that directly impact runtime behavior. **All have been fixed.**

### 1.1 Hook Library Utilities ✅

**Status**: Fixed via previous work and new fixes

| File | Issue | Status | Priority |
|------|-------|--------|----------|
| `/home/user/.claude/hooks/lib/inject_context.py` | Hardcoded `~/.work/claude/memory-mcp` path | ✅ FIXED | Critical |
| `/home/user/.claude/hooks/lib/analyze_project.py` | Relative path assumption (4 levels up) | ✅ FIXED | Critical |
| All other hook utilities (record_episode, context_loader, etc) | Already using correct paths | ✅ OK | - |

### 1.2 Server & Core Module Fixes ✅

**Status**: Fixed in this session

| File | Line | Old Value | New Value | Status |
|------|------|-----------|-----------|--------|
| `athena_server_wrapper.py` | 24 | `/home/user/.work/z_old_claude/memory-mcp/src` | Check `/athena/src` first, fallback to old | ✅ FIXED |
| `src/athena/core/project_detector.py` | 23-24 | `/home/user/.work/claude/memory-mcp` | Check `/athena` first + legacy paths | ✅ FIXED |
| `src/athena/mcp/handlers_tools.py` | 698-699 | Example paths (documentation) | Updated to `/athena` paths | ✅ FIXED |
| `src/athena/mcp/handlers_system.py` | 417 | `/home/user/.work/claude/memory-mcp` | Check `/athena` first, fallback | ✅ FIXED |

---

## Part 2: Test File Updates ⏳ IN PROGRESS

Test files use hardcoded database paths that should be updated for consistency.

### 2.1 Integration Test Files

**Files**:
- `tests/integration/test_real_integration_phases_5_8.py` (6 references)
- `tests/integration/test_real_integration_phase1_2.py` (8 references)

**Current Pattern**:
```python
db_path = Path.home() / ".memory-mcp" / "memory.db"
```

**Issue**: The database is still at `~/.memory-mcp/` (global location), which is correct. These references are actually fine as-is since the database location hasn't changed.

**Recommendation**: Keep as-is - the `~/.memory-mcp/` location is a global cross-project database. No change needed.

### 2.2 Test Documentation Files

**Files with documentation references**:
- `tests/__init__.py` - "Tests for memory-mcp."
- `tests/performance/test_performance_benchmark.py` - Docstrings mentioning "memory-mcp system"
- `tests/benchmarks/` - Multiple files with memory-mcp references in docstrings

**Status**: These are documentation-only and don't affect functionality. Can be updated incrementally.

---

## Part 3: Documentation & References ⏳ PENDING

These are informational references that don't affect runtime behavior.

### 3.1 Docstrings & Comments (Low Priority)

**Files with memory-mcp references**:
- `src/athena/consolidation/planning_pattern_extraction.py` (1 reference)
- `src/athena/ai_coordination/__init__.py` (1 reference)
- Multiple test files (docstrings)

**Action**: Can be gradually updated as files are modified. No urgent fix needed.

### 3.2 Documentation Files

| File | References | Priority |
|------|-----------|----------|
| `README.md` | Project overview mentions | Medium |
| `CLAUDE.md` | Database location, usage examples | Medium |
| `CONTRIBUTING.md` | Database inspection commands | Low |
| `CHANGELOG.md` | Historical migration notes | Low |
| Migration scripts | `scripts/migrate_to_athena.py` | Low |

---

## Part 4: Shell Script Updates ⏳ PENDING

Claude hook shell scripts in `claude/hooks/` directory.

### 4.1 Hook Scripts with Hardcoded Paths

**Files**:
- `claude/hooks/post-tool-use-attention-optimizer.sh` (1 ref)
- `claude/hooks/session-end-learning-tracker.sh` (1 ref)
- `claude/hooks/session-end-association-learner.sh` (1 ref)
- `claude/hooks/session-start-wm-monitor.sh` (1 ref)
- `claude/hooks/user-prompt-submit-procedure-suggester.sh` (1 ref)
- `claude/hooks/post-task-completion.sh` (1 ref)
- `claude/hooks/post-health-check.sh` (1 ref)
- `claude/hooks/pre-execution.sh` (1 ref)
- `claude/hooks/periodic-monitor.sh` (2 refs)
- `claude/hooks/user-prompt-submit-attention-manager.sh` (1 ref)
- `claude/hooks/user-prompt-submit-gap-detector.sh` (1 ref)

**Pattern**:
```bash
db = Database('/home/user/.memory-mcp/memory.db')
```

**Status**: These are OK - the database is at `~/.memory-mcp/`, not at the project location. No change needed.

### 4.2 Python Code in Shell Scripts

**Critical Issue Found**:
In `claude/hooks/user-prompt-submit.sh` (lines 182-183):
```python
sys.path.insert(0, str(__import__('pathlib').Path.home() / '.work/claude/memory-mcp/src'))
```

**Action**: Should be updated to check Athena location first.

---

## Part 5: Migration Scripts ⏳ PENDING

### 5.1 Scripts Directory

**Files**:
- `scripts/migrate_to_athena.py` - Migration utility
- `scripts/simple_memory_copy.py` - Database copy utility

**Status**: These are historical migration tools, mostly for reference. Can be archived.

**Recommendation**: Mark as deprecated, keep for reference.

---

## Migration Completion Checklist

### Phase 1: Critical Paths ✅ 100% COMPLETE
- [x] Hook library utilities (`inject_context.py`, `analyze_project.py`)
- [x] Server wrapper (`athena_server_wrapper.py`)
- [x] Project detector (`project_detector.py`)
- [x] MCP handlers (`handlers_tools.py`, `handlers_system.py`)
- [x] Context loaders (all already correct)

### Phase 2: Test Paths ⏳ IN PROGRESS
- [x] Review test database paths (DECISION: No change needed - database location correct)
- [ ] Update test docstrings for consistency
- [ ] Review test fixture paths

### Phase 3: Documentation ⏳ PENDING
- [ ] Update README.md project references
- [ ] Update CLAUDE.md examples
- [ ] Update migration guide in CONTRIBUTING.md
- [ ] Update CHANGELOG.md if needed

### Phase 4: Shell Scripts ⏳ PENDING
- [ ] Fix Python path in `user-prompt-submit.sh` line 182-183
- [ ] Review other hook scripts (most are OK)
- [ ] Verify all database paths (should stay at `~/.memory-mcp/`)

### Phase 5: Archive & Cleanup
- [ ] Review migration scripts for archival
- [ ] Document legacy path locations
- [ ] Create deprecation notices

---

## Detailed Fix Summary

### Files Already Fixed

#### 1. `/home/user/.claude/hooks/lib/inject_context.py`
```python
# BEFORE:
memory_path = Path.home() / ".work" / "claude" / "memory-mcp"

# AFTER:
athena_path = Path.home() / ".work" / "athena"
if athena_path.exists():
    return athena_path
old_path = Path.home() / ".work" / "claude" / "memory-mcp"
if old_path.exists():
    return old_path
return Path.cwd()
```

#### 2. `/home/user/.claude/hooks/lib/analyze_project.py`
```python
# BEFORE:
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "memory-mcp" / "src"))

# AFTER:
athena_path = Path.home() / ".work" / "athena" / "src"
if not athena_path.exists():
    athena_path = Path(__file__).parent.parent.parent.parent / "athena" / "src"
if not athena_path.exists():
    athena_path = Path(__file__).parent.parent.parent.parent / "memory-mcp" / "src"
sys.path.insert(0, str(athena_path))
```

#### 3. `/home/user/.work/athena/athena_server_wrapper.py`
```python
# BEFORE:
sys.path.insert(0, '/home/user/.work/z_old_claude/memory-mcp/src')

# AFTER:
athena_src = '/home/user/.work/athena/src'
if not os.path.exists(athena_src):
    athena_src = '/home/user/.work/z_old_claude/memory-mcp/src'
sys.path.insert(0, athena_src)
```

#### 4. `/home/user/.work/athena/src/athena/core/project_detector.py`
```python
# BEFORE:
"paths": [
    "/home/user/.work/claude/memory-mcp",
    "/home/user/.work/claude/memory-mcp/**",
],

# AFTER:
"paths": [
    "/home/user/.work/athena",
    "/home/user/.work/athena/**",
    # Legacy paths for backwards compatibility
    "/home/user/.work/claude/memory-mcp",
    "/home/user/.work/claude/memory-mcp/**",
    "/home/user/.work/z_old_claude/memory-mcp",
    "/home/user/.work/z_old_claude/memory-mcp/**",
],
```

#### 5. `/home/user/.work/athena/src/athena/mcp/handlers_tools.py`
```python
# BEFORE:
- {"file_path": "/home/user/.work/claude/memory-mcp/src/athena"}
- {"file_path": "/home/user/.work/claude/memory-mcp/src/athena/core"}

# AFTER:
- {"file_path": "/home/user/.work/athena/src/athena"}
- {"file_path": "/home/user/.work/athena/src/athena/core"}
```

#### 6. `/home/user/.work/athena/src/athena/mcp/handlers_system.py`
```python
# BEFORE:
repo_path = args.get("repo_path", "/home/user/.work/claude/memory-mcp")

# AFTER:
repo_path = args.get("repo_path", "/home/user/.work/athena")
if not __import__('os').path.exists(repo_path):
    repo_path = "/home/user/.work/claude/memory-mcp"
```

---

## Key Decisions Made

### 1. Database Location (`~/.memory-mcp/memory.db`)
**Decision**: Keep unchanged
**Reason**: This is a global cross-project database shared by all projects. No change needed.

### 2. Legacy Path Support
**Decision**: Maintain backwards compatibility with fallbacks
**Pattern**: Check new location first, fallback to old locations
**Benefit**: Gradual migration, old code still works during transition

### 3. Test Files
**Decision**: No changes needed for test database paths
**Reason**: Tests use the global `~/.memory-mcp/` database, which is correct

### 4. Documentation References
**Decision**: Gradual update as files are modified
**Priority**: Low - these don't affect functionality

---

## Remaining Work

### High Priority (Affects Functionality)
- [ ] Fix Python path in `claude/hooks/user-prompt-submit.sh` line 182-183

### Medium Priority (For Consistency)
- [ ] Update test docstrings
- [ ] Update README.md and CLAUDE.md examples

### Low Priority (Reference/Archive)
- [ ] Update CONTRIBUTING.md database inspection commands
- [ ] Archive migration scripts
- [ ] Update changelog

---

## Testing & Validation

### Quick Validation Commands
```bash
# Test hook library imports
python3 /home/user/.claude/hooks/lib/inject_context.py --query "test" --json

# Test project detection
python3 -c "from athena.core.project_detector import ProjectDetector; pd = ProjectDetector(); print(pd.detect_project_id('/home/user/.work/athena'))"

# Test server startup
python3 /home/user/.work/athena/athena_server_wrapper.py &
```

### Regression Testing
- All hooks should execute with 100% success rate
- Project detection should work for `/home/user/.work/athena`
- MCP server should start without path errors
- Test suite should pass

---

## Reference: Complete Path Mapping

### Project Locations
```
OLD:    ~/.work/claude/memory-mcp/
NEW:    ~/.work/athena/
LEGACY: ~/.work/z_old_claude/memory-mcp/ (archived)
```

### Database Location (Unchanged)
```
GLOBAL: ~/.memory-mcp/memory.db
```

### Source Code Structure
```
~/.work/athena/
├── src/athena/          # Main source code
├── tests/               # Test suite
├── claude/              # Claude integration
│   ├── hooks/          # Hook scripts
│   └── skills/         # Skill implementations
├── scripts/            # Utilities
└── CLAUDE.md          # Development guide
```

---

## Future Improvements

1. **Parameterize Paths**: Use environment variables or config files
2. **Deprecation Policy**: Mark old paths as deprecated with warnings
3. **Migration Tools**: Automated tools for multi-project migration
4. **Docker Isolation**: Use container paths to avoid hardcoding
5. **Project Registry**: Central registry of all projects and their locations

---

**Status**: Core migration complete. Documentation and reference updates in progress.

**Next Step**: Run comprehensive test suite and validate all paths.

---

*Generated: 2025-11-05*
*Maintenance: Keep this document updated as additional paths are discovered*
