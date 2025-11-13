# Phase 1 Week 1: Days 3-4 - Tool Migration Execution

## Overview

Days 3-4 focus on migrating the first 10 core tools from the monolithic handlers.py to the modular tool structure. This is the critical path for achieving the 95% token efficiency improvement target.

## Core Tools to Migrate (Priority Order)

### Memory Layer Tools (3 tools)
1. **memory_recall** - Query memory system
   - Category: `memory`
   - Module: `src/athena/tools/memory/recall.py`
   - Class: `RecallMemoryTool`
   - Status: Template started ✓
   - Dependencies: UnifiedMemoryManager, RAG system
   - Expected lines: ~150-200

2. **memory_store** - Store new memories
   - Category: `memory`
   - Module: `src/athena/tools/memory/store.py`
   - Class: `StoreMemoryTool`
   - Status: To implement
   - Dependencies: All memory layers
   - Expected lines: ~150-200

3. **memory_health** - System health check
   - Category: `memory`
   - Module: `src/athena/tools/memory/health.py`
   - Class: `HealthCheckTool`
   - Status: To implement
   - Dependencies: All layers (read-only)
   - Expected lines: ~100-150

### Consolidation Tools (2 tools)
4. **consolidation_start** - Begin consolidation process
   - Category: `consolidation`
   - Module: `src/athena/tools/consolidation/start.py`
   - Class: `StartConsolidationTool`
   - Status: To implement
   - Dependencies: Consolidator
   - Expected lines: ~120-160

5. **consolidation_extract** - Extract patterns
   - Category: `consolidation`
   - Module: `src/athena/tools/consolidation/extract.py`
   - Class: `ExtractPatternsTool`
   - Status: To implement
   - Dependencies: Consolidator, pattern extraction
   - Expected lines: ~140-180

### Planning Tools (2 tools)
6. **planning_verify** - Verify plan quality
   - Category: `planning`
   - Module: `src/athena/tools/planning/verify.py`
   - Class: `VerifyPlanTool`
   - Status: To implement
   - Dependencies: Planning validator, Q* verifier
   - Expected lines: ~150-200

7. **planning_simulate** - Run scenario simulations
   - Category: `planning`
   - Module: `src/athena/tools/planning/simulate.py`
   - Class: `SimulatePlanTool`
   - Status: To implement
   - Dependencies: Scenario simulator
   - Expected lines: ~150-200

### Graph Tools (2 tools)
8. **graph_query** - Query knowledge graph
   - Category: `graph`
   - Module: `src/athena/tools/graph/query.py`
   - Class: `QueryGraphTool`
   - Status: To implement
   - Dependencies: Graph store, community detection
   - Expected lines: ~130-170

9. **graph_analyze** - Analyze entities and relationships
   - Category: `graph`
   - Module: `src/athena/tools/graph/analyze.py`
   - Class: `AnalyzeGraphTool`
   - Status: To implement
   - Dependencies: Graph store, observations
   - Expected lines: ~140-180

### Retrieval Tools (1 tool)
10. **retrieval_hybrid** - Hybrid RAG search
    - Category: `retrieval`
    - Module: `src/athena/tools/retrieval/hybrid.py`
    - Class: `HybridSearchTool`
    - Status: To implement
    - Dependencies: RAG manager, semantic store
    - Expected lines: ~150-200

## Migration Workflow for Each Tool

### Phase A: Create Tool File (30 min per tool)
```bash
# 1. Create category directory if needed
mkdir -p src/athena/tools/{category}

# 2. Use template to create tool file
# 3. Implement metadata property with:
#    - Tool name (kebab-case)
#    - Category
#    - Description
#    - Parameters with types and descriptions
#    - Return type specification

# 4. Implement validate_input() for:
#    - Required parameter checking
#    - Type validation
#    - Value range validation
```

### Phase B: Implement execute() Method (45 min per tool)
```python
# 1. Extract relevant logic from handlers.py
# 2. Call appropriate memory manager methods
# 3. Handle errors gracefully
# 4. Return structured response matching metadata
# 5. Include timing information (search_time_ms, process_time_ms)
```

### Phase C: Write Tests (45 min per tool)
```python
# 1. Create test_[tool_name].py
# 2. Test metadata structure
# 3. Test input validation
# 4. Test execute() with valid inputs
# 5. Test edge cases and errors
# 6. Aim for 80%+ code coverage
```

### Phase D: Register Tool (15 min per tool)
```python
# 1. Add to tools registry
# 2. Create backward compatibility wrapper
# 3. Verify discovery via loader
# 4. Run integration test
```

## Day 3 Schedule (5 hours = 300 minutes)

### Morning (1.5 hours)
- **9:00-9:15** (15 min): Review handlers.py tool extraction
- **9:15-10:00** (45 min): Implement memory_recall complete
- **10:00-10:30** (30 min): Create memory_store file + metadata

### Afternoon (1.5 hours)
- **14:00-14:30** (30 min): Implement memory_store execute()
- **14:30-15:00** (30 min): Implement memory_health
- **15:00-15:30** (30 min): Create and test consolidation_start

### Evening (2 hours)
- **18:00-18:30** (30 min): Complete consolidation_start implementation
- **18:30-19:00** (30 min): Implement consolidation_extract
- **19:00-20:00** (60 min): Test all 5 memory+consolidation tools

## Day 4 Schedule (5 hours = 300 minutes)

### Morning (1.5 hours)
- **9:00-9:30** (30 min): Implement planning_verify
- **9:30-10:00** (30 min): Implement planning_simulate
- **10:00-10:30** (30 min): Create tests for planning tools

### Afternoon (1.5 hours)
- **14:00-14:30** (30 min): Implement graph_query
- **14:30-15:00** (30 min): Implement graph_analyze
- **15:00-15:30** (30 min): Create tests for graph tools

### Evening (2 hours)
- **18:00-18:30** (30 min): Implement retrieval_hybrid
- **18:30-19:00** (30 min): Create tests for retrieval
- **19:00-20:00** (60 min): Integration testing + fixes

## Success Criteria

### Code Quality
- [ ] All 10 tools have comprehensive docstrings
- [ ] All tools follow BaseTool interface exactly
- [ ] No type hints warnings (mypy clean)
- [ ] Code formatted with black
- [ ] All linting passes (ruff)

### Test Coverage
- [ ] Each tool has 3-5 unit tests
- [ ] Each test covers happy path + edge cases
- [ ] All 50+ tests passing
- [ ] Code coverage >80% for tool code

### Integration
- [ ] All tools registered in ToolRegistry
- [ ] All tools discoverable via ToolLoader
- [ ] Backward compatibility wrappers created
- [ ] All tests passing in CI

### Performance
- [ ] No new performance regressions
- [ ] Tool load time <50ms per tool
- [ ] Registry lookup <1ms
- [ ] Discovery <100ms for all tools

### Documentation
- [ ] README updated with migration status
- [ ] Each tool has inline documentation
- [ ] API reference updated
- [ ] Implementation checklist marked complete

## Metrics to Track

### Size Metrics
- handlers.py reduction: 22,000 lines → ~15,000 (after 10 tools migrated)
- New tool files created: 10
- Total lines added to tools/: ~1,500-2,000
- Token efficiency: 25,600 → ~15,000 (41% improvement from baseline)

### Quality Metrics
- Test passing rate: 100% (target)
- Code coverage: >85%
- Type safety: 0 mypy errors
- Linting: 0 ruff violations

### Productivity Metrics
- Time per tool: 180 min (30+45+45+15 min phases)
- Total time for 10 tools: 1,800 min (30 hours)
- Actual Days 3-4: 10 hours → ~3 tools realistically
- Plan: Focus on quality over quantity

## Dependency Management

### Tools with External Dependencies
1. **memory_recall**: Needs `UnifiedMemoryManager.query()`
2. **consolidation_start**: Needs `Consolidator.consolidate()`
3. **planning_verify**: Needs `PlanValidator.verify()`
4. **graph_query**: Needs `GraphStore.query()`
5. **retrieval_hybrid**: Needs `RAGManager.retrieve()`

### Import Strategy
```python
# For each tool, import what it needs:
from athena.manager import UnifiedMemoryManager
from athena.consolidation import Consolidator
# etc.

# In tool's __init__:
def __init__(self, manager: Optional[UnifiedMemoryManager] = None):
    self.manager = manager or get_memory_manager()
```

## Risk Mitigation

### Risk: Breaking Existing MCP Interface
- **Mitigation**: Backward compatibility wrappers handle old calls
- **Test**: Run existing MCP server tests

### Risk: Missing Tool Dependencies
- **Mitigation**: Import lazily with graceful fallbacks
- **Test**: Test each tool in isolation

### Risk: Performance Regression
- **Mitigation**: Track load times and registry lookup speed
- **Test**: Benchmark tools before/after migration

### Risk: Incomplete Migration
- **Mitigation**: Use migration framework to track progress
- **Test**: Verify all registered tools work via loader

## Progress Tracking

### Phase Gates
- [ ] Day 3 morning: 2-3 tools complete (memory layer)
- [ ] Day 3 afternoon: 5 tools complete (+ consolidation)
- [ ] Day 3 evening: 5 tools tested
- [ ] Day 4 morning: 7-8 tools complete (+ planning)
- [ ] Day 4 afternoon: 10 tools complete (+ graph)
- [ ] Day 4 evening: All tested and integrated

### Success Indicators
1. All 10 tools have working execute() methods
2. All tools properly validate input
3. All 50+ unit tests passing
4. All tools discoverable via ToolLoader
5. Zero breaking changes to existing interface

## Files to Create

```
src/athena/tools/
├── memory/
│   ├── __init__.py
│   ├── recall.py          ✓ (started)
│   ├── store.py           (to create)
│   └── health.py          (to create)
├── consolidation/
│   ├── __init__.py
│   ├── start.py           (to create)
│   └── extract.py         (to create)
├── planning/
│   ├── __init__.py
│   ├── verify.py          (to create)
│   └── simulate.py        (to create)
├── graph/
│   ├── __init__.py
│   ├── query.py           (to create)
│   └── analyze.py         (to create)
├── retrieval/
│   ├── __init__.py
│   └── hybrid.py          (to create)

tests/unit/tools/
├── test_memory_tools.py   (to create)
├── test_consolidation_tools.py (to create)
├── test_planning_tools.py (to create)
├── test_graph_tools.py    (to create)
└── test_retrieval_tools.py (to create)
```

## Next Steps After Days 3-4

### Days 5-6: Integration & Backward Compatibility
- Verify all tools work with existing MCP server
- Create and test backward compatibility wrappers
- Run full test suite with new tools
- Track token efficiency improvements

### Day 7: Documentation & Completion
- Update README with migration status
- Document each tool's usage
- Create implementation guide for Phase 2
- Plan next 10 tools (analytics, meta-memory, etc.)
