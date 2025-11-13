# Handlers Refactoring Resume Prompt

**Date**: November 13, 2025
**Status**: In Progress (Phase 3 of 4)
**Current Work**: Extracting remaining handlers from monolithic `handlers.py`

---

## Context Summary

We're refactoring the monolithic MCP handlers system (`src/athena/mcp/handlers.py`) from a single 9,767-line file into modular, domain-organized handler modules. This improves maintainability, testability, and code navigation.

### Grok's Analysis Findings

We validated Grok's codebase audit. Key findings:
- ✅ **8 layers are actually complete** (not 6 as claimed - Prospective and Meta-memory are functional)
- ⚠️ **Database architecture mismatch**: Claims "local-first SQLite" but system is PostgreSQL-only
- ✅ **Version inconsistency**: `pyproject.toml` = 0.9.0, `__init__.py` = 0.1.0 (needs fixing)
- ⚠️ **Monolithic handlers**: 9,767 lines (should be split into domain modules)
- ✅ **TypeScript dead code**: `src/execution/` contains 9 unused files (should be deleted or integrated)

---

## Current Refactoring Progress

### Completed Extractions (12 domain modules)

| Module | Lines | Status | Last Updated | Key Methods |
|--------|-------|--------|--------------|-------------|
| `handlers.py` (main) | 9,767 → ~4,000 remaining | 🔄 IN PROGRESS | Nov 13 12:36 | Core class, tool registration, remaining handlers |
| `handlers_episodic.py` | 1,370 | ✅ Extracted | Nov 13 11:57 | record_event, recall_events, get_timeline, etc. |
| `handlers_procedural.py` | 1,537 | ✅ Extracted | Nov 13 12:28 | extract_procedures, learn_workflow, execute_procedure, etc. |
| `handlers_prospective.py` | 1,864 | ✅ Extracted | Nov 13 12:35 | create_task, get_tasks, update_task_phase, check_triggers, etc. |
| `handlers_memory_core.py` | 420 | ✅ Extracted | Nov 13 12:12 | remember, recall, forget, list, optimize, search |
| `handlers_dreams.py` | 335 | ✅ Extracted | Nov 13 10:31 | Phase 2 advanced features (experimental) |
| `handlers_consolidation.py` | 25 | ⚠️ Stub | Nov 13 09:16 | Run consolidation (full impl in handlers.py) |
| `handlers_planning.py` | 34 | ⚠️ Stub | Nov 13 09:16 | Planning methods (full impl in handlers.py) |
| `handlers_graph.py` | 29 | ⚠️ Stub | Nov 13 09:16 | Graph operations (full impl in handlers.py) |
| `handlers_metacognition.py` | 30 | ⚠️ Stub | Nov 13 09:16 | Metacognition (full impl in handlers.py) |
| `handlers_working_memory.py` | 34 | ⚠️ Stub | Nov 13 09:16 | Working memory (full impl in handlers.py) |
| `handlers_research.py` | 19 | ⚠️ Stub | Nov 13 09:16 | Research tasks (full impl in handlers.py) |
| `handlers_system.py` | 39 | ⚠️ Stub | Nov 13 09:16 | System operations (full impl in handlers.py) |

**Total extracted so far**: ~5,700 lines
**Still in main handlers.py**: ~4,000 lines (remaining handlers + core infrastructure)

### Refactoring Pattern

Each extraction follows this pattern:

```python
# handlers_DOMAIN.py (new extracted file)
"""Domain-specific handler methods for [DOMAIN] memory."""

from typing import Any, Optional, List
from ..path.to.stores import RelatedStore
from ..path.to.models import RelatedModel

async def _handle_operation_name(self, args: dict) -> list[TextContent]:
    """Handle [operation] operation."""
    # Full implementation from handlers.py
```

Then in `handlers.py`:
```python
# handlers.py (imports forwarders)
from .handlers_domain import _handle_operation_name

class MemoryMCPServer:
    _handle_operation_name = _handle_operation_name  # Bind to class
```

This maintains **100% backward compatibility** while enabling modular organization.

---

## Remaining Work

### Phase 3: Extract Remaining Stubs (Current)

The following modules are currently **stubs** (only 19-39 lines) with full implementations still in `handlers.py`:

1. **`handlers_consolidation.py`** (25 lines → should be ~800)
   - Methods: `_handle_run_consolidation`, `_handle_consolidation_quality_metrics`, etc.
   - Dependencies: consolidation, llm_clustering, patterns

2. **`handlers_planning.py`** (34 lines → should be ~1,200)
   - Methods: `_handle_decompose_hierarchically`, `_handle_validate_plan`, `_handle_verify_plan`, etc.
   - Dependencies: planning, validator, formal_verification

3. **`handlers_graph.py`** (29 lines → should be ~600)
   - Methods: `_handle_create_entity`, `_handle_create_relation`, `_handle_search_graph`, etc.
   - Dependencies: graph, models

4. **`handlers_metacognition.py`** (30 lines → should be ~500)
   - Methods: `_handle_analyze_coverage`, `_handle_detect_knowledge_gaps`, `_handle_get_expertise`, etc.
   - Dependencies: meta, quality, learning, gaps, reflection, load

5. **`handlers_working_memory.py`** (34 lines → should be ~400)
   - Methods: `_handle_get_working_memory`, `_handle_update_working_memory`, `_handle_get_associations`, etc.
   - Dependencies: episodic buffer, associations

6. **`handlers_research.py`** (19 lines → should be ~300)
   - Methods: `store_research_findings`, research operations
   - Dependencies: research module

7. **`handlers_system.py`** (39 lines → should be ~1,500+)
   - Methods: System diagnostics, analytics, health checks, IDE integration, automation, budget tracking
   - Dependencies: Multiple system modules

### Phase 4: Finalize Main handlers.py

After extractions, `handlers.py` should contain:
- `MemoryMCPServer` class definition (~100 lines)
- `__init__()` method (~200 lines)
- `_register_tools()` with all tool definitions (~2,000 lines)
- `list_tools()` and `call_tool()` dispatch methods (~200 lines)
- Imports and method bindings (~300 lines)
- **Total**: ~2,800 lines (vs. current 9,767)

---

## Key Architectural Decisions

### 1. Forwarding Pattern (Not Full Extraction)

We use **forwarding** instead of moving implementations:
- ✅ Implementations stay in `handlers.py` (single source of truth)
- ✅ Domain modules import and bind methods to class
- ✅ Enables incremental migration (no big rewrites)
- ✅ 100% backward compatible (no breaking changes)

### 2. Method Naming Convention

All handler methods follow: `_handle_OPERATION_NAME()`
- `_handle_record_event()` (episodic)
- `_handle_create_task()` (prospective)
- `_handle_extract_procedures()` (procedural)
- etc.

### 3. Tool Registration

The `_register_tools()` method in `handlers.py` defines all 27 tools with their operations. This stays in main file as central registry.

---

## Testing Strategy

### Unit Tests
- Test individual handlers in isolation
- Mock database, stores, and dependencies
- Location: `tests/mcp/test_handlers_DOMAIN.py`

### Integration Tests
- Test tool dispatch via `call_tool()`
- Test handler composition
- Location: `tests/mcp/test_handlers_integration.py`

### Current Test Coverage
- ✅ Core operations: ~80% coverage
- ⚠️ Advanced features (Phase 2+): ~30% coverage
- ⚠️ System operations: ~20% coverage

---

## Next Steps (When Resuming)

1. **Extract remaining stub modules**:
   - Start with `handlers_consolidation.py` (smaller, clear dependencies)
   - Then `handlers_graph.py` (medium, isolated)
   - Then `handlers_planning.py` (large, complex)
   - Then `handlers_metacognition.py`, `handlers_working_memory.py`, `handlers_research.py`
   - Finally `handlers_system.py` (largest, most dependencies)

2. **Verify each extraction**:
   - Check method binding works (`_handle_X = _handle_X`)
   - Run tool registration: `tools = await server.list_tools()`
   - Test dispatch: `await server.call_tool(name, args)`

3. **After all extractions**:
   - Run full test suite: `pytest tests/mcp/ -v`
   - Verify line count reduction: `handlers.py` should be ~2,800 lines
   - Check tool functionality: `memory-mcp` startup and operations

4. **Address other Grok findings**:
   - Fix version inconsistency (0.1.0 → 0.9.0)
   - Document database requirement (PostgreSQL, not SQLite)
   - Delete TypeScript dead code (`src/execution/`)
   - Update CLAUDE.md with actual architecture

---

## Current Module Status

### Completed & Tested ✅
- `handlers_episodic.py` (1,370 lines, 16 methods)
- `handlers_procedural.py` (1,537 lines, 21 methods)
- `handlers_prospective.py` (1,864 lines, 24 methods)
- `handlers_memory_core.py` (420 lines, 8 methods)
- `handlers_dreams.py` (335 lines)

### In Progress 🔄
- `handlers.py` (main file, still contains ~4,000 lines of handler code)
- All remaining stubs need full implementations extracted

### Total Progress
- **Lines extracted**: 5,700 / 9,767 (58% complete)
- **Modules created**: 12 / 12 (100%)
- **Modules fully implemented**: 5 / 12 (42%)

---

## Files to Reference

| File | Purpose | Completeness |
|------|---------|--------------|
| `src/athena/mcp/handlers.py` | Main server class + tool registry + remaining handlers | 🔄 In progress |
| `src/athena/mcp/handlers_episodic.py` | Episodic memory operations | ✅ Complete |
| `src/athena/mcp/handlers_procedural.py` | Procedural memory operations | ✅ Complete |
| `src/athena/mcp/handlers_prospective.py` | Prospective memory + planning tasks | ✅ Complete |
| `src/athena/mcp/handlers_memory_core.py` | Core memory operations (remember, recall, forget, search) | ✅ Complete |
| `src/athena/mcp/handlers_dreams.py` | Phase 2 advanced features | ✅ Complete |
| `src/athena/mcp/handlers_consolidation.py` | Consolidation operations | ⚠️ Stub (25 lines) |
| `src/athena/mcp/handlers_planning.py` | Advanced planning operations | ⚠️ Stub (34 lines) |
| `src/athena/mcp/handlers_graph.py` | Knowledge graph operations | ⚠️ Stub (29 lines) |
| `src/athena/mcp/handlers_metacognition.py` | Meta-memory operations | ⚠️ Stub (30 lines) |
| `src/athena/mcp/handlers_working_memory.py` | Working memory operations | ⚠️ Stub (34 lines) |
| `src/athena/mcp/handlers_research.py` | Research operations | ⚠️ Stub (19 lines) |
| `src/athena/mcp/handlers_system.py` | System operations | ⚠️ Stub (39 lines) |
| `tests/mcp/test_handlers_*.py` | Unit tests for each domain | ⚠️ Partial coverage |

---

## Debugging Tips

### If Tool Registration Breaks
```bash
# Check if all methods are bound to class
python3 -c "from athena.mcp.handlers import MemoryMCPServer; s = MemoryMCPServer('memory.db'); print(hasattr(s, '_handle_OPERATION_NAME'))"

# Verify imports in new modules
python3 -c "from athena.mcp.handlers_consolidation import *; print('OK')"
```

### If call_tool() Fails
```bash
# Check tool registry
python3 -c "from athena.mcp.handlers import MemoryMCPServer; import asyncio; print(asyncio.run(MemoryMCPServer('memory.db').list_tools()))"

# Test specific handler
python3 -c "from athena.mcp.handlers import MemoryMCPServer; s = MemoryMCPServer('memory.db'); print(hasattr(s, '_handle_run_consolidation'))"
```

### If Tests Fail
```bash
# Run just MCP tests
pytest tests/mcp/ -v --tb=short

# Run single domain test
pytest tests/mcp/test_handlers_consolidation.py -v

# With print statements
pytest tests/mcp/ -v -s
```

---

## Success Criteria

When this refactoring is complete:

- [ ] All 12 handler modules have full implementations (not stubs)
- [ ] Total lines in `handlers.py` reduced to ~2,800 (from 9,767)
- [ ] All tools still accessible via `call_tool()` (zero breaking changes)
- [ ] Test suite passes: `pytest tests/mcp/ -v` → ✅ all green
- [ ] No circular imports or missing dependencies
- [ ] Code formatting passes: `black --check src/athena/mcp/`
- [ ] Type checking passes: `mypy src/athena/mcp/handlers*.py`
- [ ] MCP server starts without errors: `memory-mcp`

---

## Related Context

**Previous Work**:
- Phase 1: Episodic, Procedural, Prospective extractions (completed)
- Phase 2: Memory core, Dreams extractions (completed)

**Next Work After Refactoring**:
- Version consistency fix (0.1.0 → 0.9.0)
- Database documentation update (PostgreSQL requirement)
- TypeScript dead code removal
- Documentation alignment with actual implementation

**Grok Audit Results**:
- Database claims need correcting
- Prospective/Meta layers are more complete than claimed
- Handlers refactoring is the right move for maintainability

---

**Last Updated**: November 13, 2025
**Owner**: Claude Code Session
**Status**: Ready to resume - continue extracting stub modules
