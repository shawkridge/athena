# handlers.py Refactoring Tasks

**Status**: Planning phase ✅
**Total Tasks**: 17
**Estimated Timeline**: 4-5 hours
**Complexity**: Medium (pure refactoring, zero functional changes)
**Risk Level**: Low (safe rollback available)

---

## Executive Summary

This document outlines the complete refactoring plan for splitting `handlers.py` (12,363 lines, 313 methods) into 11 specialized files for improved maintainability and code navigation.

**Current State**:
```
handlers.py (12,363 lines)
├── 313 handler methods
├── 50+ tool definitions
├── 8 mixed concerns (memory, events, tasks, graph, planning, etc.)
└── Low discoverability
```

**Target State**:
```
handlers/ directory
├── handlers.py (core, 600 lines) - Server class, tool registration
├── handlers_memory_core.py (170 lines) - Core memory operations
├── handlers_episodic.py (310 lines) - Event recording & retrieval
├── handlers_procedural.py (620 lines) - Workflow management
├── handlers_prospective.py (690 lines) - Task management
├── handlers_graph.py (415 lines) - Knowledge graph
├── handlers_working_memory.py (540 lines) - Working memory & goals
├── handlers_metacognition.py (140 lines) - Quality & learning
├── handlers_planning.py (620 lines) - Planning & verification
├── handlers_consolidation.py (280 lines) - Pattern extraction & RAG
├── handlers_research.py (200 lines) - Research operations
├── handlers_system.py (420 lines) - System monitoring & distributed
└── handlers_helpers.py (120 lines) - Shared utilities
```

**Benefits**:
- ✅ Reduced cognitive load (12K → ~500 lines per file)
- ✅ Better code organization (domain-focused)
- ✅ Easier navigation and maintenance
- ✅ Clearer separation of concerns
- ✅ Improved Git history (fewer merge conflicts)
- ✅ Faster local file searches

---

## Task Breakdown (17 Tasks)

### Phase 1: Analysis & Preparation (Tasks 1-2)

#### Task 1: Analyze handlers.py structure
**Status**: Not started
**Priority**: High
**Estimated Time**: 30 minutes

Extract all 313 handler methods and categorize them:
- Generate list of all `async def _handle_*` methods
- Group by domain (memory, events, tasks, graph, etc.)
- Identify shared utilities and helper functions
- Create dependency map
- Document any cross-domain dependencies

**Success Criteria**:
- ✅ All 313 methods categorized
- ✅ Dependency map created
- ✅ Shared utilities identified

**Output**: Detailed analysis document with method groupings

**Next Task**: Task 2 (Create handler templates)

---

#### Task 2: Create handler file templates
**Status**: Not started
**Priority**: High
**Estimated Time**: 20 minutes

Create template files for each new handler:
1. `handlers_memory_core.py` - Template with imports + docstring
2. `handlers_episodic.py` - Template with imports + docstring
3. `handlers_procedural.py` - Template with imports + docstring
4. `handlers_prospective.py` - Template with imports + docstring
5. `handlers_graph.py` - Template with imports + docstring
6. `handlers_working_memory.py` - Template with imports + docstring
7. `handlers_metacognition.py` - Template with imports + docstring
8. `handlers_planning.py` - Template with imports + docstring
9. `handlers_consolidation.py` - Template with imports + docstring
10. `handlers_research.py` - Template with imports + docstring
11. `handlers_system.py` - Template with imports + docstring

**Success Criteria**:
- ✅ All 11 template files created
- ✅ Correct imports for each domain
- ✅ Docstring headers present
- ✅ No syntax errors

**Output**: 11 handler template files in `src/athena/mcp/`

**Next Task**: Task 3 (Extract memory_core handlers)

---

### Phase 2: Extraction (Tasks 3-13)

#### Task 3: Extract handlers_memory_core.py methods
**Status**: Not started
**Priority**: High
**Estimated Time**: 45 minutes

Move core memory operation methods from handlers.py to handlers_memory_core.py:
- `_handle_remember`
- `_handle_recall`
- `_handle_forget`
- `_handle_list_memories`
- `_handle_optimize`
- `_handle_search_projects`
- Helper methods for memory core operations

**Steps**:
1. Copy methods from handlers.py
2. Update imports (add memory-specific imports if needed)
3. Verify all dependencies included
4. Test method signatures
5. Remove from handlers.py (keep in template reference)

**Success Criteria**:
- ✅ All 8 methods extracted
- ✅ No import errors
- ✅ All dependencies resolved
- ✅ Methods maintain original signatures

**Output**: Completed `handlers_memory_core.py`

**Next Task**: Task 4 (Extract episodic handlers)

---

#### Task 4: Extract handlers_episodic.py methods
**Status**: Not started
**Priority**: High
**Estimated Time**: 1 hour

Move event recording & retrieval methods:
- `_handle_record_event`
- `_handle_recall_events`
- `_handle_get_timeline`
- `_handle_batch_record_events`
- `_handle_recall_events_by_session`
- `_handle_schedule_consolidation`
- Plus helper methods

**Success Criteria**:
- ✅ All 12-15 methods extracted
- ✅ No import errors
- ✅ All dependencies resolved

**Output**: Completed `handlers_episodic.py`

**Next Task**: Task 5 (Extract procedural handlers)

---

#### Task 5: Extract handlers_procedural.py methods
**Status**: Not started
**Priority**: High
**Estimated Time**: 1.5 hours

Move workflow management methods:
- `_handle_create_procedure`
- `_handle_find_procedures`
- `_handle_record_execution`
- `_handle_compare_procedure_versions`
- `_handle_rollback_procedure`
- `_handle_list_procedure_versions`
- `_handle_get_procedure_effectiveness`
- `_handle_suggest_procedure_improvements`
- Plus helper methods

**Success Criteria**:
- ✅ All 10-12 methods extracted
- ✅ No import errors
- ✅ All dependencies resolved

**Output**: Completed `handlers_procedural.py`

**Next Task**: Task 6 (Extract prospective handlers)

---

#### Task 6: Extract handlers_prospective.py methods
**Status**: Not started
**Priority**: High
**Estimated Time**: 1.5 hours

Move task management methods:
- `_handle_create_task`
- `_handle_list_tasks`
- `_handle_update_task_status`
- `_handle_create_task_with_planning`
- `_handle_start_task`
- `_handle_verify_task`
- `_handle_create_task_with_milestones`
- `_handle_update_milestone_progress`
- Plus helper methods

**Success Criteria**:
- ✅ All 12-15 methods extracted
- ✅ No import errors
- ✅ All dependencies resolved

**Output**: Completed `handlers_prospective.py`

**Next Task**: Task 7 (Extract graph handlers)

---

#### Task 7: Extract handlers_graph.py methods
**Status**: Not started
**Priority**: High
**Estimated Time**: 1 hour

Move knowledge graph methods:
- `_handle_create_entity`
- `_handle_create_relation`
- `_handle_add_observation`
- `_handle_search_graph`
- `_handle_search_graph_with_depth`
- `_handle_get_graph_metrics`
- `_handle_analyze_coverage`
- Plus helper methods

**Success Criteria**:
- ✅ All 8-10 methods extracted
- ✅ No import errors
- ✅ All dependencies resolved

**Output**: Completed `handlers_graph.py`

**Next Task**: Task 8 (Extract working_memory handlers)

---

#### Task 8: Extract handlers_working_memory.py methods
**Status**: Not started
**Priority**: High
**Estimated Time**: 1 hour

Move working memory & goals methods:
- `_handle_get_working_memory`
- `_handle_update_working_memory`
- `_handle_clear_working_memory`
- `_handle_consolidate_working_memory`
- `_handle_get_active_goals`
- `_handle_set_goal`
- `_handle_get_associations`
- `_handle_strengthen_association`
- `_handle_find_memory_path`
- Plus helper methods

**Success Criteria**:
- ✅ All 10-12 methods extracted
- ✅ No import errors
- ✅ All dependencies resolved

**Output**: Completed `handlers_working_memory.py`

**Next Task**: Task 9 (Extract metacognition handlers)

---

#### Task 9: Extract handlers_metacognition.py methods
**Status**: Not started
**Priority**: High
**Estimated Time**: 45 minutes

Move quality & learning methods:
- `_handle_get_quality_metrics`
- `_handle_update_quality`
- `_handle_detect_learning_opportunities`
- `_handle_assess_cognitive_load`
- `_handle_detect_knowledge_gaps`
- `_handle_get_expertise`
- Plus helper methods

**Success Criteria**:
- ✅ All 8 methods extracted
- ✅ No import errors
- ✅ All dependencies resolved

**Output**: Completed `handlers_metacognition.py`

**Next Task**: Task 10 (Extract planning handlers)

---

#### Task 10: Extract handlers_planning.py methods
**Status**: Not started
**Priority**: High
**Estimated Time**: 1.5 hours

Move planning & verification methods:
- `_handle_create_plan`
- `_handle_verify_plan`
- `_handle_validate_safety`
- `_handle_adaptive_replanning`
- `_handle_recommend_strategy`
- Plus helper methods

**Success Criteria**:
- ✅ All 8-10 methods extracted
- ✅ No import errors
- ✅ All dependencies resolved

**Output**: Completed `handlers_planning.py`

**Next Task**: Task 11 (Extract consolidation handlers)

---

#### Task 11: Extract handlers_consolidation.py methods
**Status**: Not started
**Priority**: High
**Estimated Time**: 45 minutes

Move consolidation & RAG methods:
- `_handle_run_consolidation`
- `_handle_smart_retrieve`
- Plus helper methods

**Success Criteria**:
- ✅ All 6-8 methods extracted
- ✅ No import errors
- ✅ All dependencies resolved

**Output**: Completed `handlers_consolidation.py`

**Next Task**: Task 12 (Extract research handlers)

---

#### Task 12: Extract handlers_research.py methods
**Status**: Not started
**Priority**: Medium
**Estimated Time**: 30 minutes

Move research operations methods:
- `store_research_findings`
- Plus helper methods for research operations

**Success Criteria**:
- ✅ All 4-6 methods extracted
- ✅ No import errors
- ✅ All dependencies resolved

**Output**: Completed `handlers_research.py`

**Next Task**: Task 13 (Extract system handlers)

---

#### Task 13: Extract handlers_system.py methods
**Status**: Not started
**Priority**: High
**Estimated Time**: 1.5 hours

Move system monitoring & distributed memory methods:
- System health checks
- Analytics operations
- Distributed memory operations
- Executive function tools
- Plus helper methods (15-20 methods total)

**Success Criteria**:
- ✅ All 15-20 methods extracted
- ✅ No import errors
- ✅ All dependencies resolved

**Output**: Completed `handlers_system.py`

**Next Task**: Task 14 (Refactor main handlers.py)

---

### Phase 3: Integration (Tasks 14-15)

#### Task 14: Refactor main handlers.py
**Status**: Not started
**Priority**: High
**Estimated Time**: 1.5 hours

Clean up and refactor main handlers.py:
1. Remove all extracted handler methods
2. Add imports for all handler groups (with `from .handlers_* import ...`)
3. Create mixin imports or direct method binding if needed
4. Verify server class definition
5. Verify `list_tools()` still works
6. Verify `call_tool()` routing still works
7. Check operation_router integration

**Steps**:
1. Update imports section (add handler file imports)
2. Remove ~300 handler method definitions
3. Verify class structure intact
4. Test no syntax errors
5. Verify tool registration still complete

**Success Criteria**:
- ✅ handlers.py reduced to ~600 lines
- ✅ All handler groups imported
- ✅ No circular dependencies
- ✅ Tool registration verified
- ✅ No syntax errors

**Output**: Refactored `handlers.py` with clean imports

**Next Task**: Task 15 (Update operation_router)

---

#### Task 15: Update operation_router.py
**Status**: Not started
**Priority**: Medium
**Estimated Time**: 30 minutes

Verify operation_router works with new handler structure:
1. Check all operation mappings still valid
2. Update any handler references if needed
3. Verify routing logic unchanged
4. Test no circular dependencies

**Success Criteria**:
- ✅ All operations route correctly
- ✅ No import errors
- ✅ No circular dependencies

**Output**: Verified `operation_router.py`

**Next Task**: Task 16 (Validation)

---

### Phase 4: Validation (Task 16)

#### Task 16: Run full test suite
**Status**: Not started
**Priority**: Critical
**Estimated Time**: 1.5 hours

Run comprehensive testing:
1. Unit tests: `pytest tests/unit/ -v`
2. Integration tests: `pytest tests/integration/ -v`
3. MCP tests: `pytest tests/mcp/ -v` (if available)
4. Type checking: `mypy src/athena/mcp/`
5. Linting: `ruff check src/athena/mcp/`
6. Formatting: `black --check src/athena/mcp/`

**Success Criteria**:
- ✅ All unit tests pass
- ✅ All integration tests pass
- ✅ All MCP tests pass (if applicable)
- ✅ No mypy errors
- ✅ No ruff warnings
- ✅ Code formatting correct

**Output**: Test results with 0 failures

**Troubleshooting**:
- If tests fail, identify which handler group caused issue
- Revert specific handler file if needed
- Debug and fix, then re-run tests

**Next Task**: Task 17 (Documentation & commit)

---

### Phase 5: Documentation (Task 17)

#### Task 17: Documentation & git commit
**Status**: Not started
**Priority**: High
**Estimated Time**: 30 minutes

Document refactoring and create commit:

1. **Update CLAUDE.md**:
   - Add section: "MCP Handlers Architecture (Refactored)"
   - Document new file organization
   - Add "How to Add New Handlers" guide
   - Add examples of handler placement

2. **Create HANDLERS_ARCHITECTURE.md** (optional):
   - Detailed breakdown of each handler file
   - Key responsibilities
   - Dependencies per file
   - How to extend handlers

3. **Git commit**:
   ```
   refactor: Split handlers.py into 11 specialized files

   - Extract domain-specific handlers into separate files
   - Reduce handlers.py from 12,363 → ~600 lines
   - Improve code organization and maintainability
   - No functional changes (100% pure refactoring)

   Files affected:
   - src/athena/mcp/handlers.py (refactored)
   - src/athena/mcp/handlers_*.py (11 new files)
   - src/athena/mcp/operation_router.py (verified)
   - CLAUDE.md (updated)
   ```

**Success Criteria**:
- ✅ CLAUDE.md updated with new structure
- ✅ Git commit created with detailed message
- ✅ All changes tracked in version control

**Output**: Committed refactoring with documentation

---

## Task Execution Order

```
1. Task 1: Analysis (30 min)
   ↓
2. Task 2: Templates (20 min)
   ↓
3. Tasks 3-13: Parallel extraction (7 hours total, or sequential 8-9 hours)
   ├─ Task 3: Memory core (45 min)
   ├─ Task 4: Episodic (1 hour)
   ├─ Task 5: Procedural (1.5 hours)
   ├─ Task 6: Prospective (1.5 hours)
   ├─ Task 7: Graph (1 hour)
   ├─ Task 8: Working memory (1 hour)
   ├─ Task 9: Metacognition (45 min)
   ├─ Task 10: Planning (1.5 hours)
   ├─ Task 11: Consolidation (45 min)
   ├─ Task 12: Research (30 min)
   └─ Task 13: System (1.5 hours)
   ↓
4. Task 14: Refactor main (1.5 hours)
   ↓
5. Task 15: Update router (30 min)
   ↓
6. Task 16: Validation (1.5 hours)
   ↓
7. Task 17: Documentation (30 min)

TOTAL: 4-5 hours (sequential), 2-3 hours (parallel extraction)
```

---

## Rollback Plan

If critical issues occur:

1. **Identify problem**: Check test failure message
2. **Stash changes**: `git stash`
3. **Revert handlers.py**: Check out from main
4. **Identify root cause**: Was it a specific handler group?
5. **Fix and retry**: Re-extract that group carefully

**Safety**: Since this is pure refactoring:
- ✅ No database schema changes
- ✅ No algorithm changes
- ✅ No API changes
- ✅ Rollback is 100% safe

---

## Success Metrics

After completing all tasks:

| Metric | Target | Expected |
|--------|--------|----------|
| handlers.py size | <1,000 lines | ~600 lines |
| Avg handler file size | 400-700 lines | 400-620 lines |
| Import statements | Organized | Clear organization |
| Test pass rate | 100% | 100% |
| Code coverage | Maintained | Maintained |
| Build time | <5 seconds | <5 seconds |
| Code quality | Improved | High |

---

## Questions?

If stuck or unclear:
1. Check the analysis document from Task 1
2. Review the dependency map
3. Consult the handler grouping in this document
4. Ask for clarification on specific handler

Good luck! 🚀
