# Naming Conventions

**Status**: Established
**Last Updated**: November 13, 2025

---

## Principle: Descriptive Over Temporal

All code, scripts, and configuration files should have **descriptive names** that explain *what they do*, not *when they were created or used*.

---

## File Naming Guidelines

### ✅ Good Practices

**Code Files** - Describe functionality:
- `toon_handler_converter.py` - Converts handlers to TOON pattern
- `docstring_optimizer.py` - Optimizes docstring compression
- `handler_pattern_analyzer.py` - Analyzes handler patterns
- `metadata_helper_extractor.py` - Extracts metadata helpers
- `convert_all_remaining_handlers.py` - Converts all remaining handlers

**Configuration Files** - Describe purpose:
- `handlers_config.yaml` - Handler configuration
- `feature_flags.json` - Feature flags
- `test_config.py` - Test configuration

**Module Files** - Describe domain:
- `handlers.py` - Main handler definitions
- `models.py` - Data models
- `store.py` - Storage layer
- `utils.py` - Utility functions

### ❌ Bad Practices

**Temporal markers in code files** (DON'T use):
- ❌ `session5_docstring_compress.py` - References session 5
- ❌ `phase3_handler_update.py` - References phase 3
- ❌ `batch2_converter.py` - References batch 2
- ❌ `v1_optimizations.py` - References version 1

**Why temporal names are bad**:
- Becomes confusing after 1-2 weeks
- Doesn't describe what the code does
- Makes code organization unclear
- Creates false sense of version control (use git for that)
- Violates single responsibility principle

---

## Documentation File Naming

### ✅ Good Practices

**Session Reports** (temporal names are appropriate):
- `SESSION_5_ANALYSIS_REPORT.md` - Session 5 analysis
- `SESSION_4_COMPLETION_REPORT.md` - Session 4 results
- `ALIGNMENT_METRICS_FINAL.md` - Final metrics summary

**Why temporal names work for documentation**:
- Reports are inherently temporal (point-in-time snapshots)
- Session numbers provide historical traceability
- Readers know when information was generated
- Archive-friendly (old reports stay organized)

**Permanent Documentation** (descriptive names):
- `ARCHITECTURE.md` - System architecture
- `CLAUDE.md` - Claude Code guidance
- `DEVELOPMENT_GUIDE.md` - Development instructions
- `NAMING_CONVENTIONS.md` - This file

---

## Directory Structure

```
project_root/
├── src/                           # Source code
│   ├── athena/
│   │   ├── handlers/
│   │   ├── models/
│   │   ├── store/
│   │   └── utils/
│
├── tools/                         # Utility scripts (descriptive names)
│   ├── toon_handler_converter.py
│   ├── docstring_optimizer.py
│   ├── handler_pattern_analyzer.py
│   └── metadata_helper_extractor.py
│
├── tests/                         # Test suites
│   ├── unit/
│   ├── integration/
│   └── performance/
│
├── docs/                          # Documentation
│   ├── ARCHITECTURE.md
│   ├── DEVELOPMENT_GUIDE.md
│   ├── NAMING_CONVENTIONS.md      # This file
│   └── tmp/                       # Temporary/session docs (session-numbered OK)
│       ├── SESSION_5_ANALYSIS_REPORT.md
│       ├── SESSION_4_COMPLETION_REPORT.md
│       └── ALIGNMENT_METRICS_FINAL.md
│
└── README.md
```

---

## Examples

### Script Naming

| Purpose | ❌ Bad | ✅ Good |
|---------|--------|---------|
| Convert TOON | `batch2_toon_convert.py` | `toon_handler_converter.py` |
| Optimize docstrings | `session5_docstring_compress.py` | `docstring_optimizer.py` |
| Analyze patterns | `session5_pattern_extraction.py` | `handler_pattern_analyzer.py` |
| Extract helpers | `session5_metadata_helper.py` | `metadata_helper_extractor.py` |

### Module Naming

| Purpose | ❌ Bad | ✅ Good |
|---------|--------|---------|
| Handler definitions | `handlers_v2.py` | `handlers.py` |
| Data models | `models_phase3.py` | `models.py` |
| Utilities | `utils_batch1.py` | `utils.py` |
| Configuration | `config_session4.py` | `config.py` |

### Documentation Naming

| Purpose | ❌ Bad | ✅ Good |
|---------|--------|---------|
| Architecture guide | `architecture_session5.md` | `ARCHITECTURE.md` |
| Development guide | `dev_guide_v2.md` | `DEVELOPMENT_GUIDE.md` |
| Session report | `Report_5.md` | `SESSION_5_ANALYSIS_REPORT.md` |
| Metrics snapshot | `metrics_2025_11_13.md` | `ALIGNMENT_METRICS_FINAL.md` |

---

## Naming Prefixes/Suffixes

### Acceptable Patterns

**Functional prefixes** (describe what it does):
- `handler_*.py` - Handler-related utilities
- `test_*.py` - Test files
- `*_optimizer.py` - Optimization utilities
- `*_analyzer.py` - Analysis tools
- `*_converter.py` - Conversion tools

**Semantic suffixes**:
- `*_store.py` - Data storage
- `*_models.py` - Data models
- `*_utils.py` - Utility functions
- `*_config.py` - Configuration
- `*_test.py` - Tests

### Unacceptable Patterns

**Temporal markers** (DON'T use):
- ❌ `*_v1.py`, `*_v2.py` - Use git branches instead
- ❌ `session*_*.py` - Use directory structure
- ❌ `phase*_*.py` - Use git tags
- ❌ `batch*_*.py` - Use git commits
- ❌ `old_*.py`, `new_*.py` - Use git history

---

## Implementation Guidelines

### When Refactoring Names

1. Update all imports in code
2. Update references in documentation
3. Update `.gitignore` if needed
4. Create single git commit with all changes
5. Reference old names in commit message if needed

### Checking Compliance

Use this grep to find problematic files:

```bash
# Find temporal markers in filenames
find . -type f -name "*.py" \
  | grep -E "(session|batch|phase|_v[0-9])" \
  | grep -v "test" \
  | grep -v "__pycache__"

# Should return: nothing (if compliant)
```

---

## Decision Record

**Date**: November 13, 2025
**Decision**: Establish descriptive naming over temporal naming for code files
**Rationale**:
- Code maintainability improves with descriptive names
- Temporal context is captured in git history
- Documentation benefits from session numbers for traceability
- Separates concerns: code (what) vs. history (when)

**Status**: ✅ Implemented
**Violations Found**: 4 script files (now fixed)
**Follow-up**: No additional refactoring needed

---

## Exceptions

### When Temporal Names Are OK

1. **Documentation reports**
   - `SESSION_*.md` - Session summaries
   - `PHASE_*.md` - Phase completions
   - Rationale: Reports are snapshots in time

2. **Archive files**
   - Completed reports moved to `docs/archive/`
   - Rationale: Historical reference

3. **Temporary analysis**
   - Experimental scripts (prefix with `_experimental_`)
   - Rationale: Not permanent code

### When Descriptive Names Aren't Enough

Use **module docstrings** to clarify purpose:

```python
"""Handler TOON Compression Converter

This module converts MCP handlers from json.dumps() returns to
StructuredResult.success() for TOON compression pattern.

Usage:
    python toon_handler_converter.py src/athena/mcp/handlers_*.py

Results:
    - 40-60% token reduction per handler
    - Automatic TOON compression applied
    - Backward compatible (JSON fallback)
"""
```

---

## Enforcement

### Manual Checks

Before committing, verify:
- [ ] No temporal markers in code filenames
- [ ] Descriptive names match functionality
- [ ] No session/phase/batch numbers in production code

### Git Pre-Commit Hook

Could add to `.git/hooks/pre-commit` (optional):

```bash
#!/bin/bash
# Prevent committing files with temporal markers
if git diff --cached --name-only | grep -E "session|batch|phase|_v[0-9].*\.py"; then
    echo "ERROR: Temporal markers in code filenames"
    echo "Use descriptive names instead (see docs/NAMING_CONVENTIONS.md)"
    exit 1
fi
```

---

**Version**: 1.0
**Status**: Active
**Last Reviewed**: November 13, 2025
