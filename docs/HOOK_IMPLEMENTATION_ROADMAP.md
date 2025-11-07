# Hook Implementation Roadmap

## Executive Summary

**Current State**: All hooks are currently **stub implementations** with placeholder comments and logging-only behavior. No actual MCP tool invocations or memory operations are happening.

**Goal**: Implement all hook functionality with real MCP tool calls, agent invocations, and memory operations.

**Total Work**: 17 tasks across 8 files
- **8 Critical** (blocks core functionality)
- **6 High** (agent invocations missing)
- **4 Medium** (improvements)

**Estimated Effort**: 60-80 hours of implementation + testing

---

## Critical Path (Must Fix First)

These 8 tasks must be completed before any other work, as they block all other functionality:

### 1. Fix `agent_invoker.py` (Core Infrastructure)
**File**: `/home/user/.claude/hooks/lib/agent_invoker.py:142`
**Issue**: Agent invocation mechanism is a placeholder - cannot invoke any agents
**Impact**: BLOCKS all agent-based functionality (attention-optimizer, goal-orchestrator, etc.)
**Task**:
- Replace placeholder with actual agent invocation mechanism
- Options:
  1. Use `Skill` tool (if agents mapped to skills)
  2. Use `SlashCommand` tool (if agents mapped to slash commands)
  3. Use direct `Task` tool invocation
  4. Use MCP tool calls directly
- Must handle async execution (hooks run in <5s timeout)
- Must have graceful failure modes

**Dependencies**: None
**Effort**: Large (2-3 hours)

### 2. Implement Episodic Event Recording
**File**: `/home/user/.claude/hooks/post-tool-use.sh:46`
**Issue**: Tool execution events not being recorded
**Impact**: NO episodic memory being captured (data loss)
**Task**:
- Replace comment with actual MCP tool call
- Call `mcp__athena__episodic_tools` with operation='record_event'
- Parameters needed:
  - event_type: "tool_execution"
  - content: tool_name, status, duration
  - outcome: "success" or "failure"
  - timestamp: current time
- Handle errors gracefully (don't block hook execution)

**Dependencies**: None
**Effort**: Small (30 minutes)

### 3. Implement Attention-Optimizer Invocation
**File**: `/home/user/.claude/hooks/post-tool-use.sh:69`
**Issue**: Cognitive load not being managed; attention not being optimized
**Impact**: Working memory will overflow; focus will be lost
**Task**:
- Trigger attention-optimizer every 10 operations
- Must call agent_invoker.invoke_agent("attention-optimizer", {cognitive_load_data})
- Pass current load metrics (working memory usage, event count)
- Must handle timeout gracefully

**Dependencies**: agent_invoker.py fix
**Effort**: Medium (1 hour)

### 4. Implement Session-Start Context Loading
**File**: `/home/user/.claude/hooks/session-start.sh:33`
**Issue**: Session context not being loaded; memory not primed
**Impact**: Session starts with empty context; no access to previous learnings
**Task**:
- Invoke SlashCommand tool with `/critical:session-start`
- OR use `task_management_tools:update_working_memory` to load context
- Must load:
  - Top 5-10 semantic memories by relevance
  - Active goals
  - Recent procedures
- Must complete in <2 seconds

**Dependencies**: None (but improves with memory storage working)
**Effort**: Small (45 minutes)

### 5. Implement Pre-Execution Plan Validation
**File**: `/home/user/.claude/hooks/pre-execution.sh:57`
**Issue**: Plans not being validated before execution
**Impact**: Invalid/unsafe plans execute; failures not prevented
**Task**:
- Call `plan-validator` agent or invoke `/critical:validate-plan`
- Pass task description and estimated parameters
- Must check:
  - Plan structure (all steps present)
  - Feasibility (resources available)
  - Consistency (no conflicts)
- Should integrate with Q* verification from Phase 6

**Dependencies**: None (benefits from planning_tools)
**Effort**: Medium (1.5 hours)

### 6. Implement Session-End Consolidation
**File**: `/home/user/.claude/hooks/session-end.sh:40`
**Issue**: Episodic events not being consolidated into semantic memory
**Impact**: NO pattern extraction; NO procedural learning; episodic events are lost
**Task**:
- Invoke consolidation with `/consolidate --strategy balanced`
- Or call `consolidation_tools:run_consolidation` directly
- Must execute dual-process consolidation:
  - System 1: Fast statistical clustering (~100ms)
  - System 2: LLM validation for high-uncertainty patterns
- Must handle session context (closing previous events)

**Dependencies**: Episode recording working
**Effort**: Large (2-3 hours)

### 7. Implement Smart-Context-Injection RAG
**File**: `/home/user/.claude/hooks/smart-context-injection.sh:60`
**Issue**: Context injection is simulated; no real memory search
**Impact**: Cannot retrieve relevant memories; context is generic
**Task**:
- Invoke RAG specialist agent or call `rag_tools:retrieve_smart` directly
- Must support 4 RAG strategies:
  - HyDE (hypothetical documents for ambiguous queries)
  - Reranking (LLM-based result ranking)
  - Query transformation (context-aware reformulation)
  - Reflective retrieval (temporal context enrichment)
- Must cache results for same session
- Must handle embedding generation (Ollama or Anthropic)

**Dependencies**: Semantic memory storage working
**Effort**: Large (2-3 hours)

### 8. Implement RAG Specialist in context_injector.py
**File**: `/home/user/.claude/hooks/lib/context_injector.py:272`
**Issue**: RAG specialist not actually being invoked
**Impact**: Cannot retrieve related context from memory
**Task**:
- Replace placeholder with actual agent invocation
- Use agent_invoker.invoke_agent("rag-specialist", {...})
- Pass query type and user context
- Must integrate with memory manager

**Dependencies**: agent_invoker.py fix, RAG functionality
**Effort**: Medium (1.5 hours)

---

## High Priority (Implement After Critical Path)

### 9. Implement Error-Handler Agent
**File**: `/home/user/.claude/hooks/post-tool-use.sh:57`
**Issue**: Tool failures not being captured and analyzed
**Impact**: Cannot learn from errors; failures not handled systematically
**Task**:
- Capture tool execution errors
- Invoke error-handler agent
- Record error patterns for learning

**Dependencies**: agent_invoker.py, episodic recording
**Effort**: Medium (1 hour)

### 10. Implement Goal-Orchestrator (Pre-Execution)
**File**: `/home/user/.claude/hooks/pre-execution.sh:43`
**Issue**: Goals not being checked before execution
**Impact**: Task execution may conflict with active goals
**Task**:
- Invoke goal-orchestrator agent
- Check current active goals
- Detect potential conflicts
- Update goal progress if task aligns

**Dependencies**: agent_invoker.py, goal management
**Effort**: Medium (1.5 hours)

### 11. Implement Safety-Auditor Agent
**File**: `/home/user/.claude/hooks/pre-execution.sh:71`
**Issue**: Changes not being evaluated for safety/risk
**Impact**: Risky changes may execute without review
**Task**:
- Invoke safety-auditor agent
- Pass change description and affected components
- Must integrate with Phase 6 safety evaluation
- Should block risky changes or require approval

**Dependencies**: agent_invoker.py, safety infrastructure
**Effort**: Medium (2 hours)

### 12. Implement Goal State Updates (Post-Task)
**File**: `/home/user/.claude/hooks/post-task-completion.sh:42`
**Issue**: Goal progress not being updated after task completion
**Impact**: Goals don't reflect actual progress; metrics inaccurate
**Task**:
- Update goal progress after task completes
- Record completion status
- Update milestone markers
- Trigger goal-orchestrator for next goal recommendation

**Dependencies**: agent_invoker.py, goal management
**Effort**: Medium (1 hour)

### 13. Implement Execution-Monitor Agent
**File**: `/home/user/.claude/hooks/post-task-completion.sh:56`
**Issue**: Task execution not being monitored in real-time
**Impact**: Cannot detect task health issues early
**Task**:
- Record execution metrics (duration vs estimate, quality)
- Invoke execution-monitor agent
- Detect deviations from plan
- Trigger replanning if needed

**Dependencies**: agent_invoker.py, execution tracking
**Effort**: Medium (1.5 hours)

### 14. Implement Session-End Agents
**File**: `/home/user/.claude/hooks/session-end.sh:55,64,73`
**Issue**: Multiple end-of-session agents not being invoked
**Impact**: No workflow learning, no association strengthening, no quality audit
**Task**:
- Invoke workflow-learner agent (extract reusable procedures)
- Invoke association-learner agent (Hebbian learning)
- Invoke quality-auditor agent (assess consolidation quality)
- Coordinate their execution in sequence

**Dependencies**: agent_invoker.py, consolidation working
**Effort**: Large (3 hours)

### 15. Implement Workflow-Learner (Post-Task)
**File**: `/home/user/.claude/hooks/post-task-completion.sh:71`
**Issue**: Multi-step patterns not being extracted as procedures
**Impact**: Cannot reuse proven workflows; repeated work
**Task**:
- After task completes, analyze steps for reusable patterns
- Extract procedures with effectiveness metrics
- Store in procedural memory
- Link to related procedures

**Dependencies**: agent_invoker.py, episodic recording
**Effort**: Medium (1.5 hours)

---

## Medium Priority (Nice to Have)

### 16. Implement Event Recording in Context-Injector
**File**: `/home/user/.claude/hooks/lib/context_injector.py`
**Issue**: Context injection events not being recorded
**Impact**: Cannot track context effectiveness
**Effort**: Small (30 minutes)

### 17. Add Integration Tests
**File**: `tests/integration/test_hooks.py`
**Issue**: No tests for hook functionality
**Impact**: Regressions go undetected
**Task**:
- Test each hook with real MCP tool calls
- Mock episodic recording
- Verify agent invocation calls
- Test error handling and timeouts

**Effort**: Large (3-4 hours)

---

## Implementation Strategy

### Phase 1: Foundation (Week 1)
1. Fix agent_invoker.py
2. Implement episodic event recording
3. Add integration tests for recording

**Deliverable**: Episodic memory recording working end-to-end

### Phase 2: Cognitive Management (Week 1)
4. Implement session-start loading
5. Implement attention-optimizer invocation
6. Implement session-end consolidation

**Deliverable**: Memory consolidation cycle working

### Phase 3: Execution Safety (Week 2)
7. Implement pre-execution validation
8. Implement safety-auditor
9. Implement error-handler

**Deliverable**: Safer task execution with error tracking

### Phase 4: Context Retrieval (Week 2)
10. Implement smart-context-injection RAG
11. Implement RAG specialist
12. Implement context caching

**Deliverable**: Smart context injection working

### Phase 5: Goal Management (Week 3)
13. Implement goal-orchestrator (pre-execution)
14. Implement goal state updates (post-task)
15. Implement execution-monitor

**Deliverable**: Goal tracking and execution monitoring

### Phase 6: Learning (Week 3)
16. Implement workflow-learner
17. Implement session-end agents
18. Add comprehensive tests

**Deliverable**: Full learning pipeline working

---

## File-by-File Implementation Order

1. `/home/user/.claude/hooks/lib/agent_invoker.py` - CRITICAL
2. `/home/user/.claude/hooks/post-tool-use.sh` - Episodes + errors
3. `/home/user/.claude/hooks/session-start.sh` - Context loading
4. `/home/user/.claude/hooks/session-end.sh` - Consolidation
5. `/home/user/.claude/hooks/pre-execution.sh` - Validation
6. `/home/user/.claude/hooks/post-task-completion.sh` - Goal/learning updates
7. `/home/user/.claude/hooks/smart-context-injection.sh` - RAG
8. `/home/user/.claude/hooks/lib/context_injector.py` - RAG specialist
9. Create `tests/integration/test_hooks.py` - Full test suite

---

## Success Criteria

### Episodic Memory
- ✅ Tool executions recorded to database
- ✅ Events have proper timestamps and context
- ✅ >2000 events recordable per session without lag

### Consolidation
- ✅ Dual-process consolidation working (System 1 + selective System 2)
- ✅ Patterns extracted with quality metrics
- ✅ Consolidation completes in <5 seconds

### Context Injection
- ✅ Memory retrieval works via RAG
- ✅ 4 strategies auto-selected based on query type
- ✅ Context injection reduces context window usage by 30%

### Agent Invocation
- ✅ All agents callable from hooks
- ✅ Proper error handling on timeout
- ✅ Non-blocking execution (hooks finish in <5s)

### Goal Management
- ✅ Goal progress tracked
- ✅ Conflicts detected pre-execution
- ✅ Execution monitoring working

### Overall
- ✅ 94+ tests passing (current: 94/94)
- ✅ Integration tests for hook functionality
- ✅ Documentation of hook execution flow
- ✅ Memory system actively learning from sessions

---

## Risk Mitigation

### Timeout Risk
**Problem**: MCP tool calls might exceed hook timeout (5s)
**Solution**:
- Use async/background execution for long operations
- Cache results from consolidation
- Queue work if needed

### Agent Invocation Failure
**Problem**: Agent invocation might fail or timeout
**Solution**:
- Graceful degradation (log but don't block)
- Retry mechanism for transient failures
- Fallback to logging-only if needed

### Memory Database Bloat
**Problem**: Recording everything might create huge database
**Solution**:
- Consolidation removes low-value events
- Sampling for high-frequency operations
- Regular vacuum/cleanup

### Hook Initialization Timing
**Problem**: Hooks might run before dependencies are ready
**Solution**:
- Lazy initialization of stores
- Dependency checks with fallback
- Clear initialization order documentation

---

## Dependencies

### Required for All Hooks
- ✅ `mcp__athena__memory_tools` (available)
- ✅ `mcp__athena__episodic_tools` (available)
- ✅ `mcp__athena__task_management_tools` (available)
- ⚠️ `agent_invoker.py` working (THIS MUST BE FIXED FIRST)

### Required for Specific Hooks
- Context loading: `mcp__athena__memory_tools` recall operations
- Consolidation: `mcp__athena__consolidation_tools`
- RAG: `mcp__athena__rag_tools` + embedding provider
- Planning: `mcp__athena__planning_tools`
- Safety: `mcp__athena__safety_tools`
- Goal management: `mcp__athena__task_management_tools`

---

## Questions Before Starting

1. Should hook implementations use MCP tools directly or via agent abstractions?
2. Should we batch MCP calls to reduce overhead?
3. What's the timeout budget per hook? (currently <5s)
4. Should we use async task queueing for long operations?
5. How should we handle MCP connection failures gracefully?

---

**Status**: Not started (all items pending)
**Last Updated**: 2025-11-06
