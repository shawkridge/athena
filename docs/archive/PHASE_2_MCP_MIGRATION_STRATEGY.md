# Phase 2 MCP Migration Strategy
**Handlers.py Refactoring & Incremental Rollout Plan**

**Date Created**: November 10, 2025
**Owner**: Senior Engineer
**Status**: Ready for Week 1 Execution

---

## Executive Summary

This document defines the strategy for incrementally migrating the monolithic MCP server (`handlers.py` + 26 handler files, ~5,800 lines) to use the new modular ToolRegistry while maintaining 100% backward compatibility.

**Key Strategy**: Parallel routing system with feature flag allows gradual rollout with instant rollback capability.

**Timeline**: 2 weeks of implementation (Week 2) + 3 weeks of migration (Weeks 3-5) with continuous validation.

**Risk Mitigation**: Legacy handlers remain active as fallback. Zero downtime migration.

---

## Current Architecture Analysis

### Monolithic Handler Structure

```
src/athena/mcp/
├─ handlers.py              (~1,200 lines, base server class)
├─ handlers_agentic.py      (~400 lines, agentic tools)
├─ handlers_confidence.py   (~250 lines, confidence tools)
├─ handlers_learning.py     (~380 lines, learning tools)
├─ handlers_library_analysis.py (~310 lines, library tools)
├─ handlers_orchestration.py (~500 lines, orchestration tools)
├─ handlers_prototyping.py (~370 lines, prototyping tools)
├─ handlers_review.py       (~300 lines, review tools)
├─ handlers_synthesis.py    (~420 lines, synthesis tools)
├─ handlers_web_research.py (~270 lines, research tools)
└─ [16 more handler files]  (~2,000+ lines)
```

**Total**: ~5,800 lines across 26 files
**Coupling**: Handlers tightly coupled to MCP server class
**Routing**: Magic method dispatch in handlers.py (complex routing logic)
**State**: Shared dependencies on UnifiedMemoryManager and database

### Pain Points Identified

1. **Monolithic Handler Registration**: All tools defined in `@server.tool()` decorators
2. **Tight Coupling**: Handlers access server state directly (`self.server`, `self.db`)
3. **Complex Routing**: Tool dispatch logic scattered across files
4. **No Discovery**: Tools not discoverable from registry - must be hardcoded
5. **Testing Difficulty**: Hard to test handlers in isolation
6. **Migration Risk**: Changing routing could break existing integrations

---

## New Architecture Design

### Target State: Dual Routing

```
MCP Client Request
    ↓
┌───────────────────────────────┐
│    MemoryMCPServer            │
│    (handlers.py)              │
└───────────┬───────────────────┘
            ↓
      ┌─────────────┐
      │ ToolRouter  │  (NEW)
      │ (routing.py)│
      └──────┬──────┘
             ↓
      ┌──────────────┐
      │ Feature Flag │
      │ USE_NEW_*    │
      └──┬───────┬──┘
         │       │
    ┌────▼────┐  ┌────────────┐
    │  NEW    │  │   LEGACY   │
    │ Registry│  │  Handlers  │
    │ (modern)│  │(fallback)  │
    └────┬────┘  └────────────┘
         │
         ▼
    UNIFIED RESULT
```

### New Routing Layer

**File**: `src/athena/mcp/routing.py` (NEW)

```python
class ToolRouter:
    """Routes tool calls to new or legacy implementation."""

    def __init__(self, registry: ToolRegistry, legacy_handlers: dict):
        self.registry = registry
        self.legacy_handlers = legacy_handlers
        self.use_new_routing = self._should_use_new_routing()
        self.log_routing = os.getenv("LOG_ROUTING", "false") == "true"

    def _should_use_new_routing(self) -> bool:
        """Determine which routing to use."""
        # Priority 1: Explicit flag for specific tool
        # Priority 2: Global feature flag
        # Priority 3: Default to legacy
        return os.getenv("USE_NEW_ROUTING", "false") == "true"

    async def execute(self, tool_name: str, params: dict) -> dict:
        """Execute tool via new or legacy path."""
        if self.use_new_routing:
            return await self._execute_new(tool_name, params)
        else:
            return self._execute_legacy(tool_name, params)

    async def _execute_new(self, tool_name: str, params: dict) -> dict:
        """Route to new modular tool."""
        try:
            tool = self.registry.get(tool_name)
            if not tool:
                # Fallback to legacy if tool not found
                return self._execute_legacy(tool_name, params)

            if self.log_routing:
                logger.info(f"Routing to NEW tool: {tool_name}")

            result = await tool.execute(**params)
            return result

        except Exception as e:
            logger.error(f"New routing failed for {tool_name}: {e}")
            # Automatic fallback to legacy
            return self._execute_legacy(tool_name, params)

    def _execute_legacy(self, tool_name: str, params: dict) -> dict:
        """Route to legacy handler."""
        handler = self.legacy_handlers.get(tool_name)
        if not handler:
            return {"error": f"Handler '{tool_name}' not found", "status": "error"}

        if self.log_routing:
            logger.info(f"Routing to LEGACY handler: {tool_name}")

        try:
            return handler(**params)
        except Exception as e:
            logger.error(f"Legacy handler failed for {tool_name}: {e}")
            return {"error": str(e), "status": "error"}

    def get_tool_metadata(self, tool_name: str) -> dict:
        """Get metadata for tool (works with both routing paths)."""
        # First try new registry
        try:
            tool = self.registry.get(tool_name)
            if tool:
                return tool.metadata.model_dump()
        except:
            pass

        # Fallback: return minimal metadata for legacy tool
        return {
            "name": tool_name,
            "description": "Legacy handler (no detailed metadata)",
            "status": "legacy"
        }

    def list_tools(self) -> list[dict]:
        """List all available tools (new + legacy)."""
        tools = []

        # Add new tools from registry
        for tool in self.registry.list_tools():
            tools.append({
                "name": tool.name,
                "category": tool.category,
                "description": tool.description,
                "routing": "new"
            })

        # Add legacy tools not in registry
        for handler_name in self.legacy_handlers:
            if not any(t["name"] == handler_name for t in tools):
                tools.append({
                    "name": handler_name,
                    "category": "legacy",
                    "description": "Legacy handler",
                    "routing": "legacy"
                })

        return tools
```

---

## Integration Points

### 1. Update handlers.py (Main Server)

**Before**:
```python
# handlers.py (OLD)
class MemoryMCPServer:
    @self.server.tool()
    async def memory_recall(self, query: str, ...) -> dict:
        """Recall/search memories."""
        # Implementation inline
        pass

    @self.server.tool()
    async def memory_store(self, content: str, ...) -> dict:
        """Store memory."""
        # Implementation inline
        pass
```

**After**:
```python
# handlers.py (NEW)
class MemoryMCPServer:
    def __init__(self):
        # Initialize tool registry
        self.tool_registry = ToolRegistry()

        # Initialize router
        self.tool_router = ToolRouter(
            registry=self.tool_registry,
            legacy_handlers=self._get_legacy_handlers()
        )

    def _get_legacy_handlers(self) -> dict:
        """Get dictionary of legacy handler functions."""
        return {
            "memory_recall": self._legacy_memory_recall,
            "memory_store": self._legacy_memory_store,
            # ... all legacy handlers
        }

    @self.server.tool()
    async def tool_execute(self, tool_name: str, params: dict) -> dict:
        """Generic tool execution endpoint."""
        return await self.tool_router.execute(tool_name, params)

    @self.server.tool()
    async def list_tools(self) -> dict:
        """Discover available tools."""
        return {
            "tools": self.tool_router.list_tools(),
            "total": len(self.tool_router.list_tools())
        }

    # Legacy handlers kept for fallback
    async def _legacy_memory_recall(self, **params) -> dict:
        """LEGACY: Recall memories."""
        # Original implementation from handlers.py
        pass

    async def _legacy_memory_store(self, **params) -> dict:
        """LEGACY: Store memory."""
        # Original implementation from handlers.py
        pass

    # ... keep all legacy handler methods
```

### 2. Feature Flag Configuration

**File**: `config/feature_flags.yaml` (NEW)

```yaml
routing:
  use_new_routing: false

  # Per-tool feature flags (optional)
  per_tool_override:
    memory_recall: true      # Use new for memory recall
    memory_store: true       # Use new for memory store
    # ... add new tools here as they're migrated

  # Canary rollout settings
  canary:
    enabled: false
    percentage: 0            # Start with 0% new routing
    ramp_per_day: 10         # Increase by 10% per day

  # Fallback settings
  fallback:
    enabled: true            # Fallback to legacy if new fails
    log_fallback: true       # Log when fallback occurs

  # Monitoring
  monitoring:
    log_routing_decisions: true
    track_latency: true
    track_error_rate: true
```

### 3. Environment Variables

```bash
# Global flag - enables new routing for all tools
export USE_NEW_ROUTING=false  # Set to true to enable new routing

# Per-tool flags (override global)
export USE_NEW_ROUTING_MEMORY_RECALL=true
export USE_NEW_ROUTING_MEMORY_STORE=true

# Logging
export LOG_ROUTING=false      # Log routing decisions
export LOG_ROUTING_LEVEL=info

# Canary rollout
export ROUTING_CANARY_ENABLED=false
export ROUTING_CANARY_PERCENTAGE=0
```

---

## Implementation Phases

### Phase 2.2a: Week 2 - Routing Layer Setup (Senior Engineer)

**Days 1-2: Design & Core Implementation**
```
1. Create src/athena/mcp/routing.py (ToolRouter class)
2. Implement dual routing logic (new vs legacy)
3. Add feature flag system
4. Write unit tests for routing logic
5. Create integration test fixtures
```

**Deliverable**: ToolRouter class with tests, feature flag system ready

---

**Days 3-4: MCP Server Integration**
```
1. Refactor handlers.py to use ToolRouter
2. Move handler implementations to _legacy_* methods
3. Add list_tools() endpoint
4. Add get_tool_metadata() endpoint
5. Test routing equivalence (new vs legacy)
```

**Deliverable**: handlers.py updated, routing integrated, equivalence tests passing

---

**Day 5: Monitoring & Docs**
```
1. Add routing decision logging
2. Add performance metrics collection
3. Document feature flags
4. Write rollout procedure
5. Create dashboard for monitoring routing stats
```

**Deliverable**: Phase 2.2a complete, ready for migration waves

---

### Phase 2.3a: Weeks 3-5 - Tool Migration (Mid-Level Engineer + Senior Reviews)

**Per-Tool Process**:
1. Create new tool class in `src/athena/mcp/tools/`
2. Migrate logic from legacy handler
3. Write comprehensive unit tests
4. Write integration tests (vs legacy handler)
5. Register in ToolRegistry
6. Update backward compat wrapper
7. Enable feature flag for this tool
8. Verify equivalence (new vs legacy output)
9. Code review + merge to main
10. Monitor for regressions

**Example: Migrating memory_recall**

```python
# Step 1: Create new tool class
# src/athena/mcp/tools/memory/recall_new.py
class RecallMemoryToolNew(BaseTool):
    name = "memory_recall"
    category = "memory"
    description = "Recall/search memories..."

    async def execute(self, query: str, ...) -> dict:
        # Migrated logic from _legacy_memory_recall
        pass

# Step 2: Register
TOOL_REGISTRY.register("memory_recall", RecallMemoryToolNew)

# Step 3: Feature flag
# Feature flag in config: per_tool_override.memory_recall: true

# Step 4: Enable routing
# New router: if use_new_routing or tool_specific_flags[tool_name]:
#     return await new_tool.execute()
# else:
#     return legacy_handler()

# Step 5: Verify equivalence
def test_recall_equivalence():
    """Verify new and legacy produce same results."""
    params = {"query": "test", ...}
    new_result = new_tool.execute(**params)
    legacy_result = legacy_handler(**params)
    assert new_result == legacy_result
```

---

## Rollout Strategy

### Phase 1: Blue-Green Deployment (Week 2-3)

**Week 2**: Deploy routing layer
- Feature flag OFF (use legacy)
- New tools deployed but not active
- All traffic goes to legacy handlers
- Zero production impact

**Week 3**: Begin canary rollout
- Start with memory/consolidation tools (Phase 1 tools already done)
- Increment tool-by-tool as migrations complete
- Feature flags control which tools use new routing
- Monitor closely for any issues

```
Week 3:
  Phase 1 tools (10): 100% new routing
  Phase 2 tools (0): 0% new routing (starting migration)
  Legacy handlers (53): Fully active as fallback

Week 4:
  Phase 1 + Wave 1 (25): 100% new routing
  Phase 2 Wave 2 (0): 0% new routing
  Legacy handlers (38): Fallback for unmigrated tools

Week 5:
  Phase 1 + Wave 1-2 (43): 100% new routing
  Phase 2 Wave 3 (20): 0-50% new routing (in progress)
  Legacy handlers (20): Fallback for remaining tools

Week 6:
  All 63 tools: 100% new routing (if confident)
  OR maintained dual routing: 100% new, legacy as safety net
```

### Phase 2: Gradual Canary (Weeks 4-5)

**Rollout Procedure**:
1. Enable feature flag for new tool in non-production first
2. Run for 24 hours, monitor errors
3. Compare outputs with legacy handler
4. If good, enable in staging for 24 hours
5. If good, enable in production
6. Monitor for 48 hours

**Rollback Procedure** (instant):
1. Flip feature flag to false
2. Requests immediately use legacy handler
3. No code deployment needed
4. Investigate and fix issue
5. Re-enable when ready

---

## Interface Contracts

### Tool Execution Contract

**Request Format** (same for new and legacy):
```python
{
    "tool_name": "memory_recall",
    "params": {
        "query": "test memory",
        "limit": 10,
        "query_type": "auto"
    }
}
```

**Response Format** (must be identical):
```python
{
    "status": "success" | "error",
    "results": [
        {
            "id": "mem_123",
            "content": "...",
            "score": 0.95,
            "metadata": {...}
        }
    ],
    "count": 5,
    "execution_time_ms": 45
}
```

**Error Response** (same format):
```python
{
    "status": "error",
    "error": "Memory not found",
    "error_code": "NOT_FOUND",
    "execution_time_ms": 2
}
```

### Tool Metadata Contract

**Format** (both routing paths must provide):
```python
{
    "name": "memory_recall",
    "category": "memory",
    "description": "Recall/search memories...",
    "parameters": {
        "query": {
            "type": "string",
            "required": true,
            "description": "Search query"
        },
        ...
    },
    "returns": {
        "status": "success | error",
        "results": "array of memories"
    }
}
```

---

## Equivalence Testing Strategy

### Test Types

#### 1. Output Equivalence
```python
def test_tool_output_equivalence(tool_name, test_params):
    """Verify new and legacy produce identical outputs."""
    new_result = router.execute_new(tool_name, test_params)
    legacy_result = router.execute_legacy(tool_name, test_params)

    assert new_result == legacy_result
    assert new_result["status"] == legacy_result["status"]
    assert new_result["results"] == legacy_result["results"]
```

#### 2. Error Equivalence
```python
def test_error_handling_equivalence(tool_name):
    """Verify error responses identical for invalid input."""
    invalid_params = {"invalid": "parameter"}

    new_error = router.execute_new(tool_name, invalid_params)
    legacy_error = router.execute_legacy(tool_name, invalid_params)

    assert new_error["status"] == "error"
    assert legacy_error["status"] == "error"
    assert type(new_error["error"]) == type(legacy_error["error"])
```

#### 3. Performance Equivalence
```python
def test_performance_equivalence(tool_name, test_params):
    """Verify new routing has acceptable performance."""
    new_time = benchmark(router.execute_new, tool_name, test_params)
    legacy_time = benchmark(router.execute_legacy, tool_name, test_params)

    # New should be within 10% of legacy
    assert new_time < legacy_time * 1.10
```

### Test Data

**Use Real-World Scenarios**:
- Memory tools: Use actual memories from database
- Task tools: Use real task workflows
- Agent tools: Use real agent states
- Learning tools: Use real code samples

**Test Coverage Target**: 95%+ of tool logic tested with equivalence

---

## Rollback Procedures

### Quick Rollback (Emergency)

```bash
# If new routing causing issues in production:
export USE_NEW_ROUTING=false

# This immediately routes all traffic to legacy handlers
# No deployment, no downtime, instant effect
```

### Targeted Rollback (Specific Tool)

```bash
# If only one tool having issues:
export USE_NEW_ROUTING_MEMORY_RECALL=false

# All other tools continue with new routing
# Only memory_recall reverts to legacy
```

### Full Rollback (To Pre-Phase 2.2)

```bash
# Step 1: Disable new routing globally
export USE_NEW_ROUTING=false

# Step 2: Disable per-tool flags
unset USE_NEW_ROUTING_*

# Step 3: Verify legacy handlers working
curl http://localhost:5000/health
curl http://localhost:5000/list_tools

# Step 4: Investigate issue
# - Check logs for errors
# - Compare new vs legacy implementations
# - Fix issue in new tool
# - Test fix with equivalence tests
# - Re-enable feature flag

# Step 5: Re-enable when ready
export USE_NEW_ROUTING=true
```

---

## Monitoring & Metrics

### Metrics to Track

**1. Routing Distribution**
```
Percentage of requests using:
  - New routing: 0% → 100% (over Weeks 3-6)
  - Legacy routing: 100% → 0%
  - Fallback count: Should be near 0
```

**2. Error Rates**
```
Errors per tool:
  - New routing error rate vs legacy
  - Fallback count (automatic fallbacks)
  - Unhandled exceptions
```

**3. Performance**
```
Latency per tool:
  - New routing: Should be within 10% of legacy
  - p50, p95, p99 latencies
  - Outliers tracked
```

**4. Equivalence**
```
Output equivalence:
  - Percentage of requests producing identical output
  - Differences logged and investigated
  - Regressions flagged
```

### Dashboard

**Create Grafana Dashboard**:
- Routing distribution pie chart
- Error rate trend line (new vs legacy)
- Latency comparison (new vs legacy)
- Equivalence percentage
- Tool-by-tool metrics

---

## Documentation & Communication

### For Developers

**What's Changing**:
1. New tools in `src/athena/mcp/tools/` directory
2. ToolRouter handles routing decisions
3. Feature flags control which path is used
4. Legacy handlers remain as fallback

**How to Migrate a Tool**:
1. Create new tool class inheriting BaseTool
2. Migrate logic from legacy handler
3. Write tests (equivalence with legacy)
4. Register in ToolRegistry
5. Enable feature flag
6. Monitor for issues

### For Operations

**Monitoring Checklist**:
- [ ] Is routing distribution as expected?
- [ ] Are error rates acceptable?
- [ ] Are latencies within tolerance?
- [ ] Are there any fallbacks occurring?

**Rollback Procedure**:
1. Flip feature flag if issue detected
2. Monitor to confirm issue resolved
3. Alert team for investigation
4. Fix issue in code
5. Re-enable feature flag

---

## Timeline & Milestones

### Week 2 (Phase 2.2a) - Routing Setup
- Mon-Tue: Design and implement ToolRouter
- Wed-Thu: Integrate with handlers.py
- Fri: Monitoring and documentation

**Milestone**: Phase 2.2a complete, ready to start migrations

### Weeks 3-5 (Phase 2.3) - Tool Migration
- Each migration follows per-tool process
- Equivalence tests validate each tool
- Feature flags enable incremental rollout

**Milestone Week 3**: Wave 1 tools migrated (15 tools)
**Milestone Week 4**: Wave 2 tools migrated (18 tools, 33 total)
**Milestone Week 5**: Wave 3 tools migrated (20 tools, 53 total)

### Week 6+ (Phase 2.4-2.5) - Hardening
- Monitor equivalence and performance
- Gradually increase new routing percentage
- Complete switch to new routing (optional)
- Keep legacy as permanent fallback for safety

---

## Risk Mitigation Summary

| Risk | Mitigation | Owner |
|------|-----------|-------|
| Breaking existing integrations | Feature flags, legacy fallback, equivalence tests | Senior Eng |
| Performance regression | Baseline metrics, continuous monitoring, rollback | QA |
| Undetected bugs in new tools | Comprehensive testing, staged rollout, monitoring | Mid-level + QA |
| Data loss/corruption | Atomic operations, transaction support, backups | Senior Eng |
| Incomplete migration | Clear per-tool process, team alignment, checklists | Mid-level |

---

## Success Criteria

- ✅ Phase 2.2a complete: ToolRouter implemented, integrated, tested
- ✅ All tools migrated with feature flags enabled
- ✅ 100% output equivalence with legacy handlers
- ✅ <5% performance overhead for new routing
- ✅ Zero regressions detected in production
- ✅ Team confident in new system
- ✅ Legacy handlers can be deprecated (optional)

---

**Status**: Ready for Week 1 Implementation
**Next Step**: Begin Week 1 Phase 2.1 (Advanced Framework)

---

*This strategy enables zero-downtime migration with instant rollback capability. Feature flags provide confidence to move incrementally. Equivalence testing ensures quality. Monitoring catches issues early.*
