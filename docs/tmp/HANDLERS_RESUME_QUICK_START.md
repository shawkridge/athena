# Handlers Refactoring - Quick Start (Resume)

**Last Session**: November 13, 2025
**Current Status**: 58% complete (5,700/9,767 lines extracted)
**What's Done**: Episodic, Procedural, Prospective, Memory Core, Dreams
**What's Left**: Consolidation, Planning, Graph, Metacognition, Working Memory, Research, System

---

## 30-Second Recap

We're splitting `handlers.py` (9,767 lines) into 12 domain modules. Currently have 5 modules fully extracted (1,370-1,864 lines each), 7 are stubs (19-39 lines).

**Next**: Extract the remaining 7 stub modules from main `handlers.py`.

---

## The Pattern (Copy-Paste)

### 1. Create new module: `handlers_DOMAIN.py`

```python
"""Domain-specific handler methods for [DOMAIN] memory."""

from typing import Any
from ..mcp_tools import TextContent

# Copy relevant imports from handlers.py here
from ..path.to.stores import SomeStore
from ..path.to.models import SomeModel


async def _handle_operation_name(self, args: dict) -> list[TextContent]:
    """Handle [operation] operation.

    Args:
        args: Operation arguments

    Returns:
        List of text responses
    """
    # Copy full implementation from handlers.py
    pass


# ... repeat for each method in this domain
```

### 2. Add binding in `handlers.py`

At the top of `MemoryMCPServer` class definition:

```python
from .handlers_domain import (
    _handle_operation_name,
    # ... other methods
)

class MemoryMCPServer:
    # Bind imported methods to class
    _handle_operation_name = _handle_operation_name
    # ... bind others
```

### 3. Verify it works

```bash
# Check imports
python3 -c "from athena.mcp.handlers import MemoryMCPServer; print('OK')"

# Quick test
pytest tests/mcp/test_handlers_DOMAIN.py -v
```

---

## Current Status Dashboard

| Module | Status | Lines | Methods | What to Extract |
|--------|--------|-------|---------|-----------------|
| episodic | ✅ Done | 1,370 | 16 | record_event, recall_events, get_timeline |
| procedural | ✅ Done | 1,537 | 21 | extract_procedures, execute_procedure, learn_workflow |
| prospective | ✅ Done | 1,864 | 24 | create_task, get_tasks, check_triggers |
| memory_core | ✅ Done | 420 | 8 | remember, recall, forget, search |
| dreams | ✅ Done | 335 | - | Phase 2 features |
| **consolidation** | 🔄 TODO | ~800 | ~10 | _handle_run_consolidation, quality_metrics |
| **planning** | 🔄 TODO | ~1,200 | ~15 | validate_plan, decompose, verify, replanning |
| **graph** | 🔄 TODO | ~600 | ~8 | create_entity, create_relation, search_graph |
| **metacognition** | 🔄 TODO | ~500 | ~10 | analyze_coverage, detect_gaps, get_expertise |
| **working_memory** | 🔄 TODO | ~400 | ~8 | get_wm, update_wm, get_associations |
| **research** | 🔄 TODO | ~300 | ~4 | store_findings, research_ops |
| **system** | 🔄 TODO | ~1,500 | ~50+ | health, analytics, IDE, automation, budget |

---

## Extraction Order (Easiest to Hardest)

1. **Consolidation** (clear boundaries, medium size)
2. **Graph** (isolated, straightforward)
3. **Working Memory** (medium, well-defined)
4. **Research** (small, new domain)
5. **Metacognition** (medium, multiple components)
6. **Planning** (large, complex dependencies)
7. **System** (huge, many cross-cutting concerns)

---

## Quick Find in handlers.py

Use these grep commands to find what to extract:

```bash
# Find consolidation handlers
grep "async def _handle.*consolidat" src/athena/mcp/handlers.py

# Find planning handlers
grep "async def _handle.*plan\|async def _handle.*verif\|async def _handle.*decomp" src/athena/mcp/handlers.py

# Find graph handlers
grep "async def _handle.*graph\|async def _handle.*entity\|async def _handle.*relation" src/athena/mcp/handlers.py

# Find all methods (to see what's left)
grep "async def _handle" src/athena/mcp/handlers.py | wc -l
```

---

## Testing Quick Commands

```bash
# Run all MCP tests
pytest tests/mcp/ -v

# Run single domain test
pytest tests/mcp/test_handlers_DOMAIN.py -v -s

# Check line count reduction
wc -l src/athena/mcp/handlers*.py

# Verify imports
python3 -c "from athena.mcp.handlers import MemoryMCPServer; print('✅ Imports OK')"

# Start server (should work)
memory-mcp --help
```

---

## Common Issues & Fixes

### Issue: ImportError after extraction
**Fix**: Make sure imports in new module match what's in handlers.py

```bash
# Check what imports the method uses
grep -A 50 "async def _handle_METHOD" src/athena/mcp/handlers.py | head -20
# Add those imports to new module
```

### Issue: Method not callable after binding
**Fix**: Ensure binding happens AFTER import in class definition

```python
from .handlers_domain import _handle_operation_name

class MemoryMCPServer:
    _handle_operation_name = _handle_operation_name  # ✅ Correct

    # NOT like this:
    # async def _handle_operation_name(self, args):  # ❌ Redefines it
```

### Issue: Tests fail with "method not found"
**Fix**: Make sure `_register_tools()` still references the method correctly

```python
# In _register_tools():
("operation_name", self._handle_operation_name)  # ✅ Works
# The binding makes it accessible
```

---

## Session Checklist

- [ ] Pick one stub module to extract (start with consolidation)
- [ ] Find all `_handle_*` methods for that domain in `handlers.py`
- [ ] Create new `handlers_DOMAIN.py` with full implementations
- [ ] Add imports and bindings to top of `MemoryMCPServer` class
- [ ] Run: `python3 -c "from athena.mcp.handlers import MemoryMCPServer; print('OK')"`
- [ ] Run: `pytest tests/mcp/test_handlers_DOMAIN.py -v`
- [ ] Commit: `git add src/athena/mcp/handlers*.py && git commit -m "refactor: Extract DOMAIN handlers"`
- [ ] Check line count reduction: `wc -l src/athena/mcp/handlers*.py | tail -1`
- [ ] Repeat for next module

---

## Estimate

- Each module: **30-60 minutes** (depending on size)
- All 7 remaining: **4-7 hours total**
- Full refactoring complete: **~2-3 sessions**

After this, we tackle:
1. Version fix (0.1.0 → 0.9.0)
2. Database docs update
3. TypeScript cleanup
4. Architecture docs alignment

---

## Files You'll Edit

| File | What | Why |
|------|------|-----|
| `src/athena/mcp/handlers.py` | Remove extracted methods, add bindings | Core refactoring |
| `src/athena/mcp/handlers_DOMAIN.py` | Add full implementations | New domain modules |
| `tests/mcp/test_handlers_DOMAIN.py` | Add/update tests | Verify extraction |

**Don't edit yet**: Wait for next session start.

---

Good luck! You're 58% through the refactoring. The pattern is clear, and each module gets easier. 🚀
