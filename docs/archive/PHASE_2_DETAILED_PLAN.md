# Phase 2: Detailed Execution Plan
**Athena MCP Modularization - Advanced Framework & Full Integration**

**Timeline**: 6-8 weeks (November 11 - December 27, 2025)
**Status**: Ready for execution
**Last Updated**: November 10, 2025

---

## Overview

Phase 2 will complete the MCP modularization by:
1. Building advanced framework features (dependencies, validation, lifecycle)
2. Integrating new modular tools with MCP server
3. Migrating remaining 17 tools from monolithic handlers.py
4. Hardening for production (monitoring, error handling, documentation)
5. Comprehensive QA and verification

**Key Change from Original Plan**: Extended timeline from 4-6 weeks to **6-8 weeks** to account for MCP integration complexity discovered during Phase 1.

---

## Week-by-Week Breakdown

### WEEK 0 (Nov 10-14): Planning Sprint (Pre-Execution)
**Goal**: Finalize execution plan and remove blockers

#### Monday, Nov 10: Kickoff & Alignment (4 hours)
- **Morning (9am-12pm)**:
  - Review Phase 1 verification document (30 min)
  - Team standup: Discuss findings, answer questions (60 min)
  - Review Phase 1 deliverables in code (30 min)

- **Afternoon (1pm-5pm)**:
  - Align on 6-8 week timeline and resource allocation
  - Assign roles: Senior lead, mid-level, QA
  - Set up communication channels (Slack, standups, demos)
  - Create Phase 2 dashboard for progress tracking

**Deliverable**: Team alignment, communication plan ready

**Owner**: Senior Engineer
**Participants**: Entire Phase 2 team

---

#### Tuesday, Nov 11: Dependency Analysis (6 hours)
- **Morning (9am-12pm)**:
  - Analyze remaining 17 tools and their dependencies
  - Create tool import graph (identify cross-dependencies)
  - Flag high-risk tools with complex interactions

- **Afternoon (1pm-5pm)**:
  - Create migration order (bottom-up by dependencies)
  - Document critical path and blocking dependencies
  - Create visual dependency diagram
  - Update: `PHASE_2_DEPENDENCY_ANALYSIS.md`

**Code Review**:
```bash
cd /home/user/.work/athena
# Analyze tools
grep -r "from athena.mcp" src/athena/mcp/handlers*.py | sort -u > /tmp/imports.txt
grep -r "import " src/athena/mcp/handlers*.py | grep -v "^import" | sort -u > /tmp/imports2.txt

# Count tools
grep "@server.tool" src/athena/mcp/handlers*.py | wc -l
# Expected: 27 tools (10 done, 17 remaining)

# Identify tool categories
grep "@server.tool" src/athena/mcp/handlers*.py | sed 's/.*def //' | sed 's/(.*)//' | sort
```

**Deliverable**: `PHASE_2_DEPENDENCY_ANALYSIS.md` with:
- List of all 27 tools and status
- Dependency graph (visual diagram in Mermaid format)
- Migration order (which tools to migrate first/last)
- High-risk tools identified and flagged

**Owner**: Mid-Level Engineer
**Participants**: Senior Engineer (review)

---

#### Wednesday, Nov 12: MCP Migration Strategy (6 hours)
- **Morning (9am-12pm)**:
  - Design routing layer for MCP server
  - Define interface contracts (ToolResult, ToolMetadata)
  - Create feature flag system for gradual rollout

- **Afternoon (1pm-5pm)**:
  - Create rollback plan (how to revert if issues)
  - Design integration test strategy
  - Document in: `PHASE_2_MCP_MIGRATION_STRATEGY.md`
  - Set up feature flag configuration

**Design Decisions to Document**:
1. **Routing Pattern**: How new ToolRegistry integrates with handlers.py
2. **Feature Flag**: `USE_NEW_ROUTING` env var for gradual rollout
3. **Fallback Strategy**: Legacy handlers used if new routing fails
4. **Compatibility Layer**: Ensure old MCP interfaces still work
5. **Rollback Procedure**: How to quickly revert to old system if critical issue

**Code Structure**:
```python
# handlers.py (new structure)
if os.getenv("USE_NEW_ROUTING") == "true":
    # Use new modular routing
    result = new_router.execute(tool_name, params)
else:
    # Use legacy routing
    result = legacy_handler(tool_name, params)

# Feature flag allows:
# - Incremental rollout (test with 10% traffic)
# - Quick rollback (flip flag to false)
# - A/B testing (compare results)
```

**Deliverable**: `PHASE_2_MCP_MIGRATION_STRATEGY.md` with:
- Architecture diagram (old vs new routing)
- Interface contracts (tool input/output formats)
- Feature flag implementation plan
- Rollback procedure (step-by-step)
- Integration test strategy

**Owner**: Senior Engineer
**Participants**: Mid-Level Engineer (review)

---

#### Friday, Nov 14: Planning Review & Finalization (2 hours)
- **10am-12pm**:
  - Review all Week 0 deliverables
  - Identify any gaps or concerns
  - Finalize `PHASE_2_EXECUTION_PLAN.md`
  - Confirm Week 1 tasks and assignments
  - Generate dependency visualization

**Deliverable**: Signed-off execution plan, ready for Week 1 start

**Owner**: Senior Engineer
**Participants**: Team + stakeholders

---

**End of Week 0**: All planning complete, team ready for Week 1 execution

---

### WEEK 1 (Nov 17-21): Phase 2.1 - Advanced Framework
**Goal**: Implement lifecycle hooks, dependency validation, async support

#### Overview
- Senior Engineer: Prepare MCP routing (Phase 2.2a prep)
- Mid-Level Engineer: Implement advanced framework features
- QA Engineer: Set up performance baseline and regression suite

#### Daily Tasks

##### Monday, Nov 17: Project Setup & Performance Baseline
**Task Owner**: Mid-Level Engineer (framework) + Senior Engineer (routing prep) + QA (benchmarking)

**Mid-Level Engineer**:
- [ ] Create `src/athena/mcp/tools/lifecycle.py` (lifecycle hook base class)
- [ ] Create `src/athena/mcp/tools/dependencies.py` (dependency validation)
- [ ] Extend `BaseTool` with lifecycle hooks
- [ ] Write initial tests (target 95%+ coverage)

**Senior Engineer**:
- [ ] Create `src/athena/mcp/routing.py` (new routing layer design)
- [ ] Design routing interfaces and contracts
- [ ] Set up feature flag system
- [ ] Create mock MCP server for testing

**QA Engineer**:
- [ ] Establish performance baseline (Week 1, before changes)
  - Measure current tool execution time
  - Measure memory usage
  - Measure token usage
  - Store baseline in `performance_baseline.json`
- [ ] Set up pytest-benchmark for continuous measurement
- [ ] Create regression test suite

**Acceptance Criteria**:
- [ ] `lifecycle.py` implemented with hooks (onLoad, onExecute, onError, onUnload)
- [ ] `dependencies.py` validates tool dependencies
- [ ] Baseline performance metrics captured
- [ ] Regression suite configured

---

##### Tuesday, Nov 18: Async Execution Support
**Task Owner**: Mid-Level Engineer

- [ ] Implement async execution in `BaseTool`
- [ ] Add `execute_async()` method
- [ ] Create `AsyncToolExecutor` wrapper
- [ ] Write async/await tests
- [ ] Test with concurrent tool execution (pytest-asyncio)

**Code Example**:
```python
# src/athena/mcp/tools/async_executor.py
class AsyncToolExecutor:
    async def execute(self, tool: BaseTool, params: dict) -> ToolResult:
        """Execute tool with lifecycle hooks."""
        # onLoad hook
        await tool.on_load()

        # Execute
        try:
            result = await tool.execute(params)
        except Exception as e:
            # onError hook
            await tool.on_error(e)
            raise

        # onUnload hook
        await tool.on_unload()

        return result
```

**Acceptance Criteria**:
- [ ] All async tests passing
- [ ] Concurrent execution verified (pytest-asyncio)
- [ ] No deadlocks detected

---

##### Wednesday, Nov 19: Dependency Validation System
**Task Owner**: Mid-Level Engineer

- [ ] Implement dependency graph in `dependencies.py`
- [ ] Detect circular dependencies
- [ ] Validate dependency resolution order
- [ ] Add dependency injection to ToolRegistry
- [ ] Write comprehensive dependency tests

**Features**:
- Load tool only when dependencies ready
- Detect circular dependencies (fail fast)
- Validate migration order from Phase 0 planning
- Support optional dependencies

**Acceptance Criteria**:
- [ ] Tool can specify dependencies
- [ ] Circular dependency detection working
- [ ] All dependency tests passing (95%+ coverage)

---

##### Thursday, Nov 20: Integration Testing
**Task Owner**: Mid-Level Engineer + QA Engineer

**Mid-Level Engineer**:
- [ ] Write integration tests for lifecycle hooks
- [ ] Test tool interactions with dependencies
- [ ] Create test fixtures for complex scenarios

**QA Engineer**:
- [ ] Run full regression suite
- [ ] Check for performance regressions (baseline vs current)
- [ ] Document any anomalies in performance report
- [ ] Update Phase 2 dashboard

**Code Example**:
```python
# tests/mcp/tools/test_integration_lifecycle.py
@pytest.mark.asyncio
async def test_lifecycle_hooks_called_in_order():
    """Verify lifecycle hooks called in correct order."""
    call_order = []

    class TrackedTool(BaseTool):
        async def on_load(self):
            call_order.append("load")

        async def execute(self, params):
            call_order.append("execute")
            return {"result": "success"}

        async def on_unload(self):
            call_order.append("unload")

    tool = TrackedTool(manager)
    result = await tool.execute({})

    assert call_order == ["load", "execute", "unload"]
```

**Acceptance Criteria**:
- [ ] All integration tests passing
- [ ] No performance regression (≤5% delta from baseline)
- [ ] Performance report generated

---

##### Friday, Nov 21: Documentation & Code Review
**Task Owner**: Mid-Level Engineer + Senior Engineer

**Mid-Level Engineer**:
- [ ] Write API reference for new lifecycle hooks
- [ ] Document dependency system
- [ ] Add code examples
- [ ] Update CLAUDE.md with new patterns

**Senior Engineer**:
- [ ] Review all code submissions
- [ ] Check type safety (mypy strict)
- [ ] Verify test coverage (>95%)
- [ ] Approve for merge to main

**Deliverable**: Merged code, API documentation updated

---

**End of Week 1 Milestone**:
- ✅ Advanced framework fully implemented
- ✅ Lifecycle hooks working
- ✅ Dependency validation system ready
- ✅ Performance baseline established
- ✅ All tests passing (126+ tests)
- ✅ Zero regressions detected

**Success Metrics**:
- Test pass rate: 100%
- Code coverage: >95%
- Performance delta: <5%
- Blocker count: 0

---

### WEEK 2 (Nov 24-28): Phase 2.2a - MCP Routing Layer
**Goal**: Integrate new ToolRegistry with MCP server routing

**Parallel Work**: While mid-level continues with tool implementations (background work), senior engineer leads MCP routing integration.

#### Daily Tasks

##### Monday, Nov 24: Routing Layer Design & Setup

**Senior Engineer**:
- [ ] Create `src/athena/mcp/routing.py` (main routing class)
- [ ] Design ToolRouter interface
- [ ] Implement feature flag system
- [ ] Create mock MCP server for testing

**Code Structure**:
```python
# src/athena/mcp/routing.py
class ToolRouter:
    def __init__(self, registry: ToolRegistry, legacy_handlers: dict):
        self.registry = registry
        self.legacy_handlers = legacy_handlers
        self.use_new_routing = os.getenv("USE_NEW_ROUTING", "false") == "true"

    async def execute(self, tool_name: str, params: dict) -> dict:
        """Route to new or legacy implementation."""
        if self.use_new_routing:
            return await self._execute_new(tool_name, params)
        else:
            return self._execute_legacy(tool_name, params)

    async def _execute_new(self, tool_name: str, params: dict) -> dict:
        """Execute via new modular tools."""
        tool = self.registry.get(tool_name)
        if not tool:
            return {"error": f"Tool '{tool_name}' not found", "status": "error"}

        result = await tool.execute(**params)
        return result

    def _execute_legacy(self, tool_name: str, params: dict) -> dict:
        """Execute via legacy handlers."""
        handler = self.legacy_handlers.get(tool_name)
        if not handler:
            return {"error": f"Handler '{tool_name}' not found", "status": "error"}

        return handler(**params)
```

**Acceptance Criteria**:
- [ ] ToolRouter class implemented
- [ ] Feature flag working (USE_NEW_ROUTING env var)
- [ ] Fallback to legacy handlers functioning
- [ ] Unit tests passing

---

##### Tuesday, Nov 25: MCP Server Integration

**Senior Engineer**:
- [ ] Integrate ToolRouter into handlers.py
- [ ] Add tool discovery endpoint (lists available tools)
- [ ] Add routing logic for tool execution
- [ ] Set up feature flag configuration

**Code Integration Point**:
```python
# src/athena/mcp/handlers.py (updated)

class MemoryMCPServer:
    def __init__(self):
        # ... existing initialization
        self.tool_registry = ToolRegistry()
        self.tool_router = ToolRouter(
            registry=self.tool_registry,
            legacy_handlers=self._legacy_handlers()
        )

    async def _handle_tool_call(self, tool_name: str, params: dict):
        """Route tool calls via new router."""
        return await self.tool_router.execute(tool_name, params)

    @self.server.tool()
    async def discover_tools(self) -> dict:
        """Discover available tools."""
        tools = self.tool_registry.list_tools()
        return {
            "tools": [t.metadata for t in tools],
            "total": len(tools)
        }
```

**Acceptance Criteria**:
- [ ] handlers.py updated with new routing
- [ ] Tool discovery endpoint working
- [ ] Feature flag integration complete
- [ ] Backward compatibility maintained

---

##### Wednesday, Nov 26: Regression Testing

**Senior Engineer** + **QA Engineer**:
- [ ] Compare new vs legacy routing (output equivalence)
- [ ] Test all 27 tools with both routing modes
- [ ] Verify output consistency
- [ ] Check performance impact

**Test Strategy**:
```python
# tests/mcp/test_routing_equivalence.py
@pytest.mark.parametrize("tool_name,params", ALL_TOOLS_AND_PARAMS)
async def test_new_routing_matches_legacy(tool_name, params):
    """Verify new routing produces same results as legacy."""
    router = ToolRouter(registry, legacy_handlers)

    # Execute via new routing
    router.use_new_routing = True
    new_result = await router.execute(tool_name, params)

    # Execute via legacy routing
    router.use_new_routing = False
    legacy_result = router.execute(tool_name, params)

    # Compare
    assert new_result == legacy_result
```

**Acceptance Criteria**:
- [ ] All 27 tools tested for equivalence
- [ ] Output consistency verified
- [ ] Performance impact <5%
- [ ] All tests passing

---

##### Thursday, Nov 27: Feature Flag & Monitoring
**Senior Engineer**:
- [ ] Set up feature flag configuration file
- [ ] Add monitoring for routing decisions
- [ ] Log tool execution path (new vs legacy)
- [ ] Create dashboard for routing stats

**Feature Flag Config**:
```yaml
# config/feature_flags.yaml
routing:
  use_new_routing: false  # Enable via env var: USE_NEW_ROUTING=true
  legacy_fallback: true   # Fall back to legacy if new routing fails
  log_routing_path: true  # Log which path tools take
  canary_percentage: 0    # Start with 0% traffic on new routing
```

**Acceptance Criteria**:
- [ ] Feature flag configurable
- [ ] Monitoring logging tool routing paths
- [ ] Dashboard showing routing stats
- [ ] Ready for canary deployment

---

##### Friday, Nov 28: Integration Review & Documentation
**Senior Engineer** + **Mid-Level Engineer**:
- [ ] Code review of all routing changes
- [ ] Type checking (mypy strict)
- [ ] Update documentation
- [ ] Prepare for Week 3 tool migration

**Deliverable**: Phase 2.2a complete, MCP routing integrated

---

**End of Week 2 Milestone**:
- ✅ MCP routing layer implemented
- ✅ Tool discovery endpoint working
- ✅ Feature flag system ready
- ✅ Legacy fallback verified
- ✅ Equivalence tests passing
- ✅ Monitoring in place

**Success Metrics**:
- New routing equivalence: 100%
- Performance impact: <5%
- Blocker count: 0

---

### WEEKS 3-5 (Dec 1-19): Phase 2.3 - Tool Migration
**Goal**: Migrate remaining 17 tools from handlers.py

**Strategy**: 3 waves of migration based on dependency analysis

#### Wave 1 (Week 3): Core System Tools (5 tools)
**Tools to Migrate**:
1. [From Phase 0 dependency analysis - core tools first]
2. [Tools with no dependencies on other handlers]
3. [Low-risk tools for early wins]

**Process per Tool**:
1. Extract tool from handlers.py
2. Create new ToolClass inheriting from BaseTool
3. Write unit tests (target 90%+ coverage)
4. Write integration tests
5. Verify backward compatibility wrapper
6. Register in ToolRegistry
7. Test via new routing with feature flag
8. Merge to main

**Code Example** (repeat for each of 5 tools):
```python
# src/athena/mcp/tools/new_tool.py
class NewToolName(BaseTool):
    name = "new_tool_name"
    category = "category"
    description = "Tool description"

    def __init__(self, manager: UnifiedMemoryManager):
        self.manager = manager

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name=self.name,
            category=self.category,
            description=self.description,
            parameters={...},
            returns={...}
        )

    async def execute(self, **kwargs) -> dict:
        """Execute tool logic."""
        # Implementation from old handlers.py
        pass

    def validate_input(self, **kwargs) -> None:
        """Validate input parameters."""
        pass

# Register
TOOL_REGISTRY.register("new_tool_name", NewToolName)

# Backward compat wrapper
def new_tool_name(**params):
    """Legacy wrapper for backward compatibility."""
    tool = TOOL_REGISTRY.get("new_tool_name")
    return asyncio.run(tool.execute(**params))
```

**Weekly Deliverable**: 5 tools migrated, 126+ tests still passing, zero regressions

---

#### Wave 2 (Week 4): System & Monitoring Tools (7 tools)
**Tools to Migrate**: Medium-complexity tools with some dependencies

**Process**: Same as Wave 1, plus:
- Verify dependencies work correctly
- Test interaction with Wave 1 tools
- Add integration tests for cross-tool calls

**Weekly Deliverable**: 7 more tools migrated (total 12), all tests passing

---

#### Wave 3 (Week 5): Advanced & Utility Tools (15 tools)
**Tools to Migrate**: High-complexity tools with multiple dependencies

**Process**: Same as Wave 1-2, plus:
- Extra care with dependency resolution
- Comprehensive integration testing
- Performance profiling
- Documentation updates

**Weekly Deliverable**: All 27 tools migrated, comprehensive regression suite passing

---

**End of Week 5 Milestone**:
- ✅ All 27 tools migrated from handlers.py
- ✅ Zero functionality loss
- ✅ All backward compat wrappers working
- ✅ Performance parity with legacy (±10%)
- ✅ Comprehensive regression tests passing

**Success Metrics**:
- Tools migrated: 27/27 (100%)
- Test pass rate: 100%
- Regressions: 0
- Performance delta: ±10% (acceptable)

---

### WEEK 6 (Dec 22-26): Phase 2.4 - Production Hardening
**Goal**: Add monitoring, error handling, API docs

#### Key Tasks
- [ ] Add comprehensive error handling
- [ ] Implement tool execution monitoring
- [ ] Add detailed logging
- [ ] Generate API reference documentation
- [ ] Security audit
- [ ] Add deployment automation scripts

**Deliverable**: Production-ready code with monitoring and docs

---

### WEEKS 7-8 (Dec 29-Jan 9): Phase 2.5 - QA & Verification
**Goal**: Comprehensive testing and sign-off

#### Tasks
- [ ] Full regression test suite (all 27 tools)
- [ ] Load testing (1000+ concurrent)
- [ ] Performance benchmarking
- [ ] Integration test suite
- [ ] Security validation
- [ ] Final deployment plan

**Deliverable**: Production sign-off, ready for deployment

---

## Dependencies & Prerequisites

### Before Week 1 Can Start
- ✅ Week 0 planning complete
- ✅ Dependency analysis finished
- ✅ MCP migration strategy documented
- ✅ Team roles assigned
- ✅ Communication channels set up

### Before Week 2 Can Start
- ✅ Week 1 advanced framework complete
- ✅ All lifecycle tests passing
- ✅ Performance baseline established
- ✅ Dependency validation working

### Before Week 3 Can Start
- ✅ Week 2 MCP routing complete
- ✅ Tool discovery endpoint working
- ✅ Feature flag system tested
- ✅ Equivalence tests passing

---

## Risk Mitigation Timeline

| Week | Risk | Mitigation |
|------|------|-----------|
| 0 | MCP complexity | Planning, strategy documentation |
| 1 | Performance regression | Baseline measurement, continuous testing |
| 2 | Integration issues | Feature flag, equivalence tests, fallback |
| 3-5 | Tool dependencies | Migration order, integration tests |
| 6-8 | Production issues | Hardening, monitoring, load testing |

---

## Resource Allocation

| Person | Role | Allocation | Focus Areas |
|--------|------|-----------|------------|
| Senior Engineer | Lead | 100% (full-time) | Architecture, MCP integration, reviews |
| Mid-Level Engineer | Implementation | 75% | Tool implementation, testing |
| QA Engineer | Quality | 50% (Weeks 5-8: 100%) | Regression, benchmarking, hardening |

---

## Definition of Done

### Per Week
- [ ] All planned tasks completed
- [ ] Code reviewed and merged to main
- [ ] All tests passing (100%)
- [ ] Performance within acceptable range (<5% regression)
- [ ] Documentation updated
- [ ] Risk register updated
- [ ] Weekly demo to stakeholders

### Per Phase (2.1-2.5)
- [ ] All features implemented
- [ ] 95%+ test coverage
- [ ] Zero critical bugs
- [ ] Performance baselines met
- [ ] Documentation complete
- [ ] Team trained on new features

### Phase 2 Completion
- [ ] All 27 tools migrated
- [ ] 100% backward compatibility
- [ ] Production hardening complete
- [ ] Comprehensive QA passed
- [ ] Go-live approval granted

---

## Success Metrics Dashboard

**Track Weekly**:

| Metric | Week 0 | Week 1 | Week 2 | Week 3-5 | Week 6-8 |
|--------|--------|--------|--------|----------|----------|
| Test Pass Rate | - | 100% | 100% | 100% | 100% |
| MCP Integration % | 0% | 0% | 50% | 100% | 100% |
| Tools Migrated | 0 | 0 | 0 | 17 | 27 |
| Performance Delta | - | <5% | <5% | ±10% | <5% |
| Blocker Count | - | 0 | 0 | 0 | 0 |

---

## Escalation & Approval Points

- **End of Week 0**: Planning approval (sign-off on strategy)
- **End of Week 1**: Framework approval (sign-off on lifecycle/dependency systems)
- **End of Week 2**: Routing approval (feature flag ready for canary)
- **End of Week 5**: Tool migration approval (all tools migrated, tested)
- **End of Week 6**: Hardening approval (production-ready features)
- **End of Week 8**: Final approval (ready for deployment)

---

## Communication Plan

- **Daily**: 10am standup (15 min) - blockers, progress
- **Weekly**: Friday demo (1 hour) - show progress to stakeholders
- **Bi-weekly**: Risk review (30 min) - update risk register
- **End of phase**: Retrospective (1 hour) - lessons learned

---

## Document References

- **Phase 1 Completion**: `PHASE_1_WEEK_1_COMPLETION_REPORT.md`
- **Verification & Assessment**: `PHASE_1_VERIFICATION_AND_PHASE_2_ASSESSMENT.md`
- **Go/No-Go Decision**: `PHASE_2_GO_NO_GO_DECISION.md`
- **Quick Start**: `PHASE_2_QUICK_START.md`
- **Risk Register**: `PHASE_2_RISK_REGISTER.md`
- **Dependency Analysis**: `PHASE_2_DEPENDENCY_ANALYSIS.md` (to be created Week 0)
- **MCP Migration Strategy**: `PHASE_2_MCP_MIGRATION_STRATEGY.md` (to be created Week 0)

---

**Status**: Ready for execution starting Week 0 (Nov 10-14)
**Next Step**: Week 0 Day 1 kickoff meeting

---

*This detailed plan provides day-by-day guidance for Phase 2 execution. Review weekly and adjust based on progress and learnings.*
