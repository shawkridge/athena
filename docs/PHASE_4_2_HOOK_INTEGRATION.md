# Phase 4.2: Hook Integration for Specialized Agents

**Status**: Design & Implementation
**Timeline**: Current session
**Objective**: Wire Phase 4.1 agents (CodeAnalyzer, ResearchCoordinator, WorkflowOrchestrator, Metacognition) into the Claude Code session lifecycle via hooks.

---

## Architecture Overview

Phase 4.2 activates the four specialized agents at critical points in the session lifecycle:

```
Session Lifecycle with Agent Activation
├── SessionStart Hook
│   ├── Load working memory from previous sessions
│   └── Activate ResearchCoordinatorAgent (proactive research planning)
│
├── PostToolUse Hook
│   ├── Record tool execution to episodic memory
│   ├── Activate CodeAnalyzerAgent (analyze tool output)
│   └── Activate WorkflowOrchestratorAgent (route next action)
│
└── SessionEnd Hook
    ├── Extract patterns from session events
    ├── Activate MetacognitionAgent (health check & introspection)
    └── Consolidate learnings into semantic memory
```

---

## Phase 4.1 Agents (Implemented)

### 1. CodeAnalyzerAgent
- **Purpose**: Analyze tool outputs and code for anti-patterns, quality issues, security vulnerabilities
- **Activation**: PostToolUse hook
- **Methods**:
  - `analyze_tool_output()` - Examine tool execution results
  - `detect_anti_patterns()` - Find problematic patterns (10+ anti-patterns)
  - `compute_quality_metrics()` - Calculate code quality scores

### 2. ResearchCoordinatorAgent
- **Purpose**: Plan and coordinate multi-level research workflows
- **Activation**: SessionStart hook
- **Methods**:
  - `plan_research()` - Create 5-level research strategy
  - `execute_research_level()` - Run research at specific depth
  - `synthesize_findings()` - Combine research results

### 3. WorkflowOrchestratorAgent
- **Purpose**: Route tasks, balance load, manage agent coordination
- **Activation**: PostToolUse hook
- **Methods**:
  - `route_task()` - Determine next action
  - `balance_load()` - Distribute work across agents
  - `track_workflow_state()` - Monitor overall flow

### 4. MetacognitionAgent
- **Purpose**: Monitor system health, detect degradation, adapt behavior
- **Activation**: SessionEnd hook
- **Methods**:
  - `health_check()` - Assess system state
  - `detect_degradation()` - Find performance issues
  - `suggest_adaptations()` - Recommend improvements

---

## Hook Integration Points

### 1. SessionStart Hook (`~/.claude/hooks/session-start.sh`)

**Current behavior**:
- Load working memory (7±2 items)
- Inject as "## Working Memory" section
- Restore context from previous sessions

**Phase 4.2 addition**:
```python
# In session-start.sh via agent_bridge.py

# Initialize ResearchCoordinatorAgent
research_agent = ResearchCoordinatorAgent()

# Plan research based on user context
user_intent = extract_intent_from_context()
research_plan = await research_agent.plan_research(user_intent, depth=3)

# Store plan in memory for subsequent tool use
await remember_event(
    content=f"Research plan: {research_plan}",
    tags=["research", "planning"],
    importance=0.9
)
```

**Expected output**: Extended working memory with research context

### 2. PostToolUse Hook (`~/.claude/hooks/post-tool-use.sh`)

**Current behavior**:
- Record tool execution to episodic memory
- Update working memory
- Track metrics

**Phase 4.2 additions**:
```python
# In post-tool-use.sh via agent_bridge.py

# Activate CodeAnalyzerAgent
code_agent = CodeAnalyzerAgent()
tool_output = extract_tool_output()
analysis = await code_agent.analyze_tool_output(tool_output)

# Store analysis findings
if analysis.anti_patterns:
    await remember_event(
        content=f"Anti-patterns detected: {analysis.anti_patterns}",
        tags=["quality", "code-analysis"],
        importance=analysis.avg_severity
    )

# Activate WorkflowOrchestratorAgent
orchestrator = WorkflowOrchestratorAgent()
next_action = await orchestrator.route_task(
    current_state=get_session_state(),
    tool_results=analysis,
    research_plan=retrieve_research_plan()
)

# Store routing decision
await remember_event(
    content=f"Workflow routed to: {next_action.target_agent}",
    tags=["workflow", "routing"],
    importance=0.8
)
```

**Expected output**: Tool output + analysis + routing decision

### 3. SessionEnd Hook (`~/.claude/hooks/session-end.sh`)

**Current behavior**:
- Extract patterns from session
- Consolidate learnings
- Update semantic memory

**Phase 4.2 addition**:
```python
# In session-end.sh via agent_bridge.py

# Activate MetacognitionAgent
metacognition = MetacognitionAgent()

# Assess system health
health_report = await metacognition.health_check(
    session_events=get_session_events(),
    performance_metrics=get_metrics()
)

# Detect degradation
degradation = await metacognition.detect_degradation(health_report)

# Suggest adaptations
if degradation:
    adaptations = await metacognition.suggest_adaptations(degradation)
    await store_fact(
        content=f"Suggested adaptations: {adaptations}",
        topics=["metacognition", "system-health"],
        confidence=0.8
    )
```

**Expected output**: Health report + adaptations for next session

---

## Implementation Strategy

### Phase 4.2a: Agent Bridge (Sync Wrapper)

Create `src/athena/agents/agent_bridge.py` - synchronous wrapper for hook calls:

```python
"""Synchronous bridge for calling async agents from hooks.

Hooks are shell scripts that need to call Python async code.
This bridge wraps async agent methods for use in synchronous contexts.
"""

class AgentBridge:
    """Synchronous wrapper for agent operations."""

    @staticmethod
    def activate_research_coordinator(context: Dict) -> Dict:
        """Activate ResearchCoordinatorAgent (SessionStart hook)."""
        # Run async agent in new event loop
        agent = ResearchCoordinatorAgent()
        plan = run_async(agent.plan_research(context))
        return {"plan": plan, "status": "success"}

    @staticmethod
    def activate_code_analyzer(tool_output: str) -> Dict:
        """Activate CodeAnalyzerAgent (PostToolUse hook)."""
        agent = CodeAnalyzerAgent()
        analysis = run_async(agent.analyze_tool_output(tool_output))
        return {"analysis": analysis, "status": "success"}

    @staticmethod
    def activate_workflow_orchestrator(state: Dict) -> Dict:
        """Activate WorkflowOrchestratorAgent (PostToolUse hook)."""
        agent = WorkflowOrchestratorAgent()
        routing = run_async(agent.route_task(state))
        return {"routing": routing, "status": "success"}

    @staticmethod
    def activate_metacognition(metrics: Dict) -> Dict:
        """Activate MetacognitionAgent (SessionEnd hook)."""
        agent = MetacognitionAgent()
        health = run_async(agent.health_check(metrics))
        return {"health": health, "status": "success"}
```

### Phase 4.2b: Hook Updates

Update three hooks to call agent bridge:

**session-start.sh**: Call `activate_research_coordinator()`
**post-tool-use.sh**: Call `activate_code_analyzer()` + `activate_workflow_orchestrator()`
**session-end.sh**: Call `activate_metacognition()`

### Phase 4.2c: Integration Tests

Create `tests/integration/test_phase4_2_hooks.py`:

```python
class TestPhase4_2HookIntegration:
    """Test Phase 4.2 hook integration."""

    async def test_session_start_activates_research_coordinator(self):
        """SessionStart hook activates ResearchCoordinatorAgent."""
        # Simulate SessionStart event
        # Verify ResearchCoordinatorAgent initialized
        # Verify plan stored in memory
        pass

    async def test_post_tool_use_activates_code_analyzer(self):
        """PostToolUse hook activates CodeAnalyzerAgent."""
        # Simulate tool execution
        # Verify CodeAnalyzerAgent analyzed output
        # Verify anti-patterns recorded
        pass

    async def test_post_tool_use_activates_orchestrator(self):
        """PostToolUse hook activates WorkflowOrchestratorAgent."""
        # Simulate tool execution
        # Verify routing decision made
        # Verify next action queued
        pass

    async def test_session_end_activates_metacognition(self):
        """SessionEnd hook activates MetacognitionAgent."""
        # Simulate session end
        # Verify health check completed
        # Verify adaptations suggested
        pass
```

---

## Data Flow

### SessionStart Flow
```
Hook triggered
  ↓
Load session context
  ↓
ResearchCoordinatorAgent.plan_research(context)
  ↓
Store plan in episodic memory
  ↓
Inject plan into working memory
  ↓
Claude sees research context at session start
```

### PostToolUse Flow
```
Tool execution completes
  ↓
Hook extracts output
  ↓
CodeAnalyzerAgent.analyze_tool_output()
  ↓
Store findings in episodic memory
  ↓
WorkflowOrchestratorAgent.route_task()
  ↓
Store routing decision
  ↓
Claude sees analysis + routing context
```

### SessionEnd Flow
```
Session concludes
  ↓
Collect session events
  ↓
MetacognitionAgent.health_check()
  ↓
Detect degradation & suggest adaptations
  ↓
Store in semantic memory
  ↓
Next session loads adaptations
```

---

## Dependencies

### Required Files
- `src/athena/agents/agent_bridge.py` (new)
- `src/athena/agents/code_analyzer.py` (exists - Phase 4.1)
- `src/athena/agents/research_coordinator.py` (exists - Phase 4.1)
- `src/athena/agents/workflow_orchestrator.py` (exists - Phase 4.1)
- `src/athena/agents/metacognition.py` (exists - Phase 4.1)

### Hook Updates
- `~/.claude/hooks/session-start.sh` (modify)
- `~/.claude/hooks/post-tool-use.sh` (modify)
- `~/.claude/hooks/session-end.sh` (modify)

### Library Functions
- `athena.episodic.operations.remember()` (exists)
- `athena.memory.operations.store()` (exists)
- `athena.core.async_utils.run_async()` (create if missing)

---

## Success Criteria

✅ **Phase 4.2a Complete**:
- [ ] `agent_bridge.py` created with all 4 agent activators
- [ ] Each activator handles async→sync conversion
- [ ] Error handling for agent failures
- [ ] Integration tests verify bridge works

✅ **Phase 4.2b Complete**:
- [ ] SessionStart hook calls research coordinator
- [ ] PostToolUse hook calls code analyzer + orchestrator
- [ ] SessionEnd hook calls metacognition agent
- [ ] All hooks log activation events

✅ **Phase 4.2c Complete**:
- [ ] 4 integration tests (one per agent)
- [ ] All tests verify agent activation + memory storage
- [ ] Tests pass with 100% coverage
- [ ] No silent failures

---

## Phase 4.3 Preview

Once Phase 4.2 is complete, Phase 4.3 will:
1. **Advanced Coordination**: Implement inter-agent communication (research → analysis → orchestration)
2. **Adaptive Learning**: Agents learn from success/failure and adapt strategies
3. **Distributed Reasoning**: Multiple agents reason in parallel about complex problems
4. **Self-Improvement**: System improves its own prompts and strategies over time

---

## Notes

- All agent methods already exist from Phase 4.1
- Hook integration is primarily about *activation timing* and *data plumbing*
- Agent outputs stored in memory make them available to subsequent tools/agents
- MetacognitionAgent provides feedback loop for continuous improvement

---

**Version**: 1.0
**Last Updated**: Nov 17, 2025
