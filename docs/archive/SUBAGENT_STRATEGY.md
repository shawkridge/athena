# Subagent Strategy & Decision Framework

**Version**: 1.0 | **Updated**: November 12, 2025 | **Status**: Verified against Claude Code best practices

This document provides comprehensive guidance on when and how to use:
1. Claude Code built-in subagents
2. Athena project skills
3. Custom SubAgentOrchestrator patterns

---

## Quick Reference: Subagent Selection

| Task Type | Best Tool | Why | Example |
|-----------|-----------|-----|---------|
| Code review | `Task(code-reviewer)` | Specialized, fresh context | Reviewing PR changes |
| Codebase analysis | `Task(code-analyzer)` | Pattern matching, dependencies | Finding unused functions |
| Research | `Task(general-purpose)` | Open-ended exploration | Understanding architecture |
| Plan validation | `Task(plan-validator)` | Q* verification, scenarios | Validating project plan |
| Memory evaluation | `skill:memory-quality-assessment` | Auto-triggered, context-aware | "How's our memory system?" |
| Code change impact | `skill:code-impact-analysis` | Auto-triggered, safety-focused | When discussing refactoring |
| Consolidation | `SubAgentOrchestrator.execute_operation()` | Internal orchestration, coordination | Nightly consolidation cycle |

---

## Layer 1: Claude Code Built-in Subagents

### When to Use Built-in Subagents

**Use `Task(subagent_type=...)` when**:
- Claude should delegate to a specialized agent (fresh context window)
- Task is complex and benefits from dedicated focus
- You want optimized model selection for the task
- The operation is "one-shot" with clear inputs/outputs

**Benefits**:
- ✅ Fresh context window (no conversation history bloat)
- ✅ Optimized model selection per subagent type
- ✅ Automatic delegation (Claude decides when to use)
- ✅ Clear input/output boundaries
- ✅ Better token efficiency than inline execution

**Drawbacks**:
- ❌ Stateless execution (each invocation starts fresh)
- ❌ No cross-task context sharing
- ❌ Latency from subprocess startup

---

### Built-in Subagent Types

#### 1. `general-purpose`
**Purpose**: Open-ended research, reasoning, complex questions

**Good for**:
- Investigating codebase patterns
- Understanding design decisions
- Research tasks with multiple steps
- Answering "how/why" questions

**Avoid for**:
- Tasks requiring state from previous steps
- Rapid back-and-forth debugging

**Example**:
```python
Task(
    subagent_type="general-purpose",
    prompt="Research how the consolidation system works. Trace through the code and explain the dual-process pattern.",
    model="sonnet"
)
```

---

#### 2. `code-analyzer`
**Purpose**: Deep codebase analysis, dependency tracking, refactoring suggestions

**Good for**:
- Finding call chains and dependencies
- Identifying dead code or unused functions
- Refactoring recommendations
- Architecture analysis

**Avoid for**:
- Simple file reads (just use Read tool directly)
- Code modifications (use skilled developers + code-reviewer)

**Example**:
```python
Task(
    subagent_type="code-analyzer",
    prompt="Analyze how the semantic search layer uses embeddings. Find all callers and dependencies.",
    model="sonnet"
)
```

---

#### 3. `code-reviewer`
**Purpose**: Code quality review, security checks, best practice feedback

**Good for**:
- Pre-commit code review
- Security analysis
- Performance optimization suggestions
- Style and convention checking

**Avoid for**:
- Automated fixing (use linters/formatters directly)
- Code generation (use developer directly)

**Example**:
```python
Task(
    subagent_type="code-reviewer",
    prompt="Review this consolidation code for correctness, performance, and memory safety.",
    model="sonnet"
)
```

---

#### 4. `debugger`
**Purpose**: Debug investigation, error root cause analysis

**Good for**:
- Investigating test failures
- Understanding error traces
- Debugging error messages
- Reproducing issues

**Avoid for**:
- Implementing fixes (separate task)
- Long-running debugging sessions (use direct interaction)

**Example**:
```python
Task(
    subagent_type="debugger",
    prompt="This test is failing with 'context mismatch error'. Debug why and suggest root cause.",
    model="sonnet"
)
```

---

#### 5. `data-scientist`
**Purpose**: Data analysis, ML work, statistical reasoning

**Good for**:
- Analyzing memory quality metrics
- Statistical pattern extraction
- Performance benchmarking
- Trend analysis

**Avoid for**:
- Real-time predictions
- Training models (typically offline work)

**Example**:
```python
Task(
    subagent_type="data-scientist",
    prompt="Analyze the consolidation metrics from the past week. Identify trends and anomalies.",
    model="sonnet"
)
```

---

#### 6. `plan-validator`
**Purpose**: Plan verification using Q* formal verification + 5-scenario stress testing

**Good for**:
- Validating project plans
- Ensuring completeness and consistency
- Stress-testing assumptions
- Risk identification

**Avoid for**:
- Quick plan checks (Skill-based validation faster)
- Informal suggestions (use general-purpose agent)

**Example**:
```python
Task(
    subagent_type="plan-validator",
    prompt="Validate this consolidation strategy plan. Check Q* properties and test 5 scenarios.",
    model="sonnet"
)
```

---

### When to Call Built-in Subagents

**Best practice pattern**:

```python
# For complex, research-heavy tasks
Task(
    subagent_type="code-analyzer",
    prompt="Analyze X in depth. Answer: [specific questions]",
    model="sonnet"  # Use Sonnet for complex analysis
)

# For review/safety tasks
Task(
    subagent_type="code-reviewer",
    prompt="Review Y for [criteria]. Recommend: [decisions]",
    model="sonnet"  # Sonnet has good judgment
)

# For quick investigations
Task(
    subagent_type="debugger",
    prompt="Why is Z failing? Root cause: [expected answer]",
    model="haiku"  # Faster, cheaper for targeted debugging
)
```

---

## Layer 2: Athena Project Skills

### When to Use Skills

**Use skills when**:
- Claude should autonomously decide to invoke capability
- Capability is reusable across projects
- Auto-triggering based on context is desirable
- Skill has progressive disclosure (doesn't bloat context)

**Benefits**:
- ✅ Auto-triggered by Claude's decision (no explicit invocation)
- ✅ Progressive disclosure (SKILL.md provides instructions)
- ✅ Reusable across projects
- ✅ Context-aware activation
- ✅ Integrated with conversation flow

**Drawbacks**:
- ❌ Requires clear description for auto-triggering
- ❌ Less explicit control (Claude decides)
- ❌ Overhead if skill rarely needed

---

### Athena Skill Catalog

#### Analysis Skills

**`memory-quality-assessment`**
- Triggers: Discussing memory quality, system optimization, learning effectiveness
- Provides: Compression, recall, consistency, expertise, cognitive load metrics
- Output: Quality scores, trends, improvement recommendations
- Tool access: Read-only (no modifications)

**`code-impact-analysis`**
- Triggers: Proposing code changes, refactoring, API updates, deployment planning
- Provides: Dependency maps, risk heatmaps, affected components, test recommendations
- Output: Safety assessment, approval gate recommendations
- Tool access: Analysis tools (Grep, Bash for queries)

**`planning-validation`**
- Triggers: Creating critical plans, planning risky operations
- Provides: Q* verification (5 properties), 5-scenario testing, risk identification
- Output: Validation report, risk analysis, mitigation strategies
- Tool access: Read-only (plan analysis, no modifications)

**`graph-analysis`**
- Triggers: Understanding knowledge structure, finding expertise clusters
- Provides: Community detection, connectivity analysis, expertise mapping
- Output: Community maps, gap analysis, bridge identification
- Tool access: Graph database queries, no modifications

**`knowledge-discovery`**
- Triggers: Exploring domains, understanding relationships, finding gaps
- Provides: Knowledge synthesis, graph traversal, community detection, learning paths
- Output: Knowledge maps, discovery insights, recommendations
- Tool access: Knowledge graph traversal, analysis

---

#### Execution Skills

**`consolidation-optimization`**
- Triggers: Running consolidation, learning from experience, memory optimization
- Provides: Strategy selection, pattern extraction, procedure generation
- Output: Consolidation report, new procedures, quality metrics
- Tool access: Full (Read, Write, Bash, Task) - privileged operation

**`procedural-engineer`**
- Triggers: Creating procedures, procedure learning, workflow extraction
- Provides: Procedure creation, testing, effectiveness tracking
- Output: Procedures, learning metrics, effectiveness scores
- Tool access: Moderate (can create, needs review for commit)

**`automation-management`**
- Triggers: Setting up automation, event-driven workflows
- Provides: Trigger creation, automation rules, execution tracking
- Output: Automation rules, monitoring, effectiveness
- Tool access: Moderate (can modify triggers, needs approval for critical)

---

### How Skills Activate

1. **Automatic Detection**: Claude reads SKILL.md descriptions
2. **Context Matching**: Claude identifies task as triggering skill use
3. **Autonomous Invocation**: Claude decides to invoke skill (no explicit prompt needed)
4. **Execution**: Skill runs with declared tool access levels
5. **Integration**: Skill results integrated into conversation naturally

**Example**:
```
User: "I want to refactor the semantic search API"

Claude's reasoning:
1. User is discussing code changes (refactoring)
2. Skill `code-impact-analysis` description mentions "refactoring"
3. Invokes skill automatically
4. Skill analyzes impact, identifies affected components
5. Claude presents findings: "Based on impact analysis, here's what would break..."
```

---

## Layer 3: Custom SubAgentOrchestrator (Internal)

### When to Use SubAgentOrchestrator

**Use `SubAgentOrchestrator` when**:
- Implementing internal Athena workflows (not user-facing)
- Operations need coordination between multiple agents
- Maintaining local state and feedback loops is critical
- Processing sensitive data locally (no context submission)

**Benefits**:
- ✅ Full control over execution flow
- ✅ Coordination between agents with feedback
- ✅ Dependency graph management
- ✅ Local state tracking
- ✅ Priority-based execution

**Drawbacks**:
- ❌ More complex to implement
- ❌ No built-in optimization (must code it)
- ❌ Requires understanding Athena internals

---

### SubAgentOrchestrator Architecture

Located in: `src/athena/orchestration/subagent_orchestrator.py`

**Built-in SubAgent Types**:
1. **CLUSTERING** - Event clustering and temporal segmentation
2. **EXTRACTION** - Pattern and knowledge extraction
3. **VALIDATION** - Pattern validation and quality checking
4. **INTEGRATION** - Knowledge graph integration
5. **OPTIMIZATION** - Performance optimization
6. **REMEDIATION** - Violation fixing
7. **LEARNING** - Learning from outcomes
8. **PLANNING** - Plan generation and verification
9. **SYNTHESIS** - Combining multiple sources

---

### SubAgentOrchestrator Usage Pattern

#### Example 1: Consolidation Workflow

```python
# From Athena consolidation system
orchestrator = SubAgentOrchestrator()

# Define tasks with dependencies
tasks = [
    SubAgentTask(
        task_id="cluster_events",
        agent_type=SubAgentType.CLUSTERING,
        operation_data={"events": episodic_events},
        priority=100
    ),
    SubAgentTask(
        task_id="extract_patterns",
        agent_type=SubAgentType.EXTRACTION,
        operation_data={"clusters": []},  # Filled by orchestrator
        dependencies=["cluster_events"],
        priority=90
    ),
    SubAgentTask(
        task_id="validate_patterns",
        agent_type=SubAgentType.VALIDATION,
        operation_data={"patterns": []},
        dependencies=["extract_patterns"],
        priority=85
    ),
    SubAgentTask(
        task_id="integrate_knowledge",
        agent_type=SubAgentType.INTEGRATION,
        operation_data={"patterns": []},
        dependencies=["validate_patterns"],
        priority=80
    )
]

# Execute with feedback loop
results = await orchestrator.execute_parallel(tasks, enable_feedback_loop=True)

# Get insights
insights = orchestrator.get_orchestration_insights()
print(f"Success rate: {insights['coordination_effectiveness']:.1%}")
```

---

#### Example 2: Simple Operation

```python
# One-off operation without complex dependencies
result = await orchestrator.execute_operation(
    "consolidate",
    {"events": events_to_consolidate},
    subagent_types=[
        SubAgentType.CLUSTERING,
        SubAgentType.EXTRACTION,
        SubAgentType.VALIDATION
    ]
)

print(f"Patterns extracted: {result['subagent_results']['extraction']['patterns_extracted']}")
```

---

## Decision Framework: Which Tool to Use?

### Decision Tree

```
┌─ Need to accomplish a task?
│
├─ Is this a BUILT-IN Claude Code capability?
│  ├─ YES → Use Task(subagent_type=...)
│  │         Examples:
│  │         - Code review needed → Task(code-reviewer)
│  │         - Architecture analysis → Task(code-analyzer)
│  │         - Research needed → Task(general-purpose)
│  │
│  └─ NO → Continue below
│
├─ Is this a REUSABLE capability for Claude's decision?
│  ├─ YES → Implement/use Skill
│  │         Examples:
│  │         - Memory quality eval → skill:memory-quality-assessment
│  │         - Code change safety → skill:code-impact-analysis
│  │         - Plan robustness → skill:planning-validation
│  │
│  └─ NO → Continue below
│
├─ Is this INTERNAL Athena operation needing coordination?
│  ├─ YES → Use SubAgentOrchestrator
│  │         Examples:
│  │         - Consolidation workflow
│  │         - Multi-step pattern learning
│  │         - Complex graph integration
│  │
│  └─ NO → Execute inline (no subagent needed)
```

---

## Token Efficiency Guidelines

### Context Management Per Layer

**Built-in Subagents**:
- Fresh context per invocation (clean slate)
- Best for complex, focused tasks
- Cost: Latency of subprocess startup
- Benefit: No context bloat in main conversation

**Skills**:
- Reads SKILL.md progressively (300 tokens max)
- Auto-triggered based on context
- Cost: Minimal (description only in context)
- Benefit: Automatic, context-aware

**Custom Orchestrator**:
- Processes data locally in Python
- Returns summaries (300 tokens) not full objects
- Cost: Memory in orchestrator process
- Benefit: Local control, no context submission

---

## Recommended Patterns by Task Type

### Pattern 1: Code Investigation
```
Task → code-analyzer (deep analysis)
Task → code-reviewer (check quality)
→ Inline execution (implement fix)
```

### Pattern 2: Plan Validation
```
Skill → planning-validation (auto-triggered)
OR
Task → plan-validator (explicit deep validation)
→ User provides feedback
```

### Pattern 3: Memory Optimization
```
Skill → memory-quality-assessment (identify issues)
→ Skill → consolidation-optimization (run consolidation)
→ Skill → memory-quality-assessment (verify improvement)
```

### Pattern 4: Safety Review
```
Skill → code-impact-analysis (auto-triggered on changes)
→ If high risk: Task → code-reviewer (explicit review)
→ Proceed with implementation
```

---

## Tool Access Levels by Skill

| Skill | Read | Grep | Write | Edit | Bash | Task |
|-------|------|------|-------|------|------|------|
| memory-quality-assessment | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| code-impact-analysis | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ |
| planning-validation | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| consolidation-optimization | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| knowledge-discovery | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| graph-analysis | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |

---

## Verification Checklist

**Before committing code using subagents**:

- [ ] Is the task using the highest-level abstraction available?
- [ ] Would a Skill work better than inline code?
- [ ] Would a built-in subagent be more efficient?
- [ ] Are tool access levels minimized (security)?
- [ ] Is context bloat minimized (only summaries)?
- [ ] Are dependencies clearly documented?

---

## Performance Targets

| Operation | Target | Measurement |
|-----------|--------|-------------|
| Built-in subagent startup | <500ms | Fresh context latency |
| Skill auto-trigger | <50ms | Context matching |
| SubAgentOrchestrator coordination | <2s | Multi-agent setup + execution |
| Local consolidation (1K events) | <5s | Full cycle with validation |

---

## References

- **Claude Code Docs**: https://code.claude.com/docs/en/sub-agents.md
- **Skills Guide**: https://code.claude.com/docs/en/skills.md
- **Anthropic MCP Pattern**: https://www.anthropic.com/engineering/code-execution-with-mcp
- **Athena CLAUDE.md**: Subagent Strategy section
- **SubAgentOrchestrator**: `src/athena/orchestration/subagent_orchestrator.py`

---

**Status**: Production-ready reference | **Last Updated**: November 12, 2025
