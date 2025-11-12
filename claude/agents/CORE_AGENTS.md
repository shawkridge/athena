---
name: core-subagents
description: 8 focused subagents for explicit task delegation following Anthropic's supervised iteration model
designation: CORE SUBAGENTS
count: 8
strategy: Anthropic-aligned user-directed delegation (supervised iteration, not autonomous proactivity)
created: November 12, 2025
---

# Core Subagents Architecture

This document defines the 8 core subagents that Claude Code explicitly delegates to for focused, isolated work.

## Design Principles (Anthropic-Aligned)

1. **User-Directed**: You explicitly invoke via `Task(subagent_type=...)` when you need focused work
2. **Supervised Iteration**: Agents operate with human oversight at decision points, not autonomously
3. **Clear Boundaries**: Each agent has specific responsibilities and tool permissions
4. **Isolated Context**: Fresh 50K token context window per agent
5. **Explicit Checkpoints**: Agents pause for approval before major decisions

## The 8 Core Subagents

### Tier 1: Essential (Deploy This Week)

#### 1. CODE-ANALYZER
**Purpose**: Code structure, dependencies, change impacts
**Invocation**: When you need to understand code organization or predict change impacts
**Tools**: Bash, Read, Grep, Glob, Write
**Model**: Sonnet
**Responsibilities**:
- Map code hierarchy and spatial organization
- Track import chains and dependencies
- Predict cascade effects of changes
- Identify code hotspots and technical debt

**When to Use**:
```
Task(subagent_type="code-analyzer", prompt="Analyze the impact of changing X to Y")
Task(subagent_type="code-analyzer", prompt="Map dependencies in src/athena/")
```

---

#### 2. SAFETY-AUDITOR
**Purpose**: Security review, vulnerability detection, risk assessment
**Invocation**: When you need OWASP analysis or security clearance
**Tools**: Bash, Read, Grep, Glob
**Model**: Sonnet
**Responsibilities**:
- Detect OWASP Top 10 vulnerabilities
- Assess change safety and risk levels
- Evaluate data sensitivity and exposure
- Create audit trails and compliance records

**When to Use**:
```
Task(subagent_type="safety-auditor", prompt="Review this code for security issues")
Task(subagent_type="safety-auditor", prompt="Assess the risk of deploying X")
```

---

#### 3. SYSTEM-ARCHITECT
**Purpose**: Design decisions, architecture planning, system design
**Invocation**: When planning major features or architectural changes
**Tools**: Read, Bash, Write
**Model**: Sonnet
**Responsibilities**:
- Evaluate architectural trade-offs
- Design scalable system patterns
- Plan integration points
- Document design decisions

**When to Use**:
```
Task(subagent_type="system-architect", prompt="Design the optimal approach for X feature")
Task(subagent_type="system-architect", prompt="Evaluate: Option A vs Option B for...")
```

---

### Tier 2: Strategic (Deploy Next Phase)

#### 4. KNOWLEDGE-ARCHITECT
**Purpose**: Knowledge graph optimization, semantic structure
**Invocation**: When optimizing Athena's knowledge representation
**Tools**: Bash, Read, Grep, Write
**Model**: Sonnet
**Athena-Specific**: Yes
**Responsibilities**:
- Optimize entity relationships
- Detect graph anomalies
- Plan community structures
- Improve semantic linkage

**When to Use**:
```
Task(subagent_type="knowledge-architect", prompt="Optimize entity relationships in graph")
Task(subagent_type="knowledge-architect", prompt="Detect and fix graph inconsistencies")
```

---

#### 5. CONSOLIDATION-ANALYST
**Purpose**: Memory consolidation, pattern extraction optimization
**Invocation**: When tuning Athena's consolidation cycles
**Tools**: Bash, Read, Grep
**Model**: Sonnet
**Athena-Specific**: Yes
**Responsibilities**:
- Analyze consolidation effectiveness
- Optimize pattern extraction
- Tune clustering algorithms
- Balance speed vs quality

**When to Use**:
```
Task(subagent_type="consolidation-analyst", prompt="Optimize consolidation for 10K events")
Task(subagent_type="consolidation-analyst", prompt="Analyze pattern quality and suggest improvements")
```

---

#### 6. INTEGRATION-COORDINATOR
**Purpose**: Cross-layer coordination, system integration
**Invocation**: When coordinating work across multiple layers
**Tools**: Bash, Read, Write
**Model**: Sonnet
**Responsibilities**:
- Coordinate multi-layer changes
- Detect integration issues
- Plan staged rollouts
- Manage layer dependencies

**When to Use**:
```
Task(subagent_type="integration-coordinator", prompt="Plan integration of X feature across layers")
```

---

### Tier 3: Specialized

#### 7. FINANCIAL-ANALYST
**Purpose**: Cost tracking, ROI estimation, budget optimization
**Invocation**: When evaluating project economics or resource allocation
**Tools**: Bash, Read, Grep
**Model**: Haiku
**Responsibilities**:
- Estimate task costs
- Track budget usage
- Calculate ROI
- Identify cost savings

**When to Use**:
```
Task(subagent_type="financial-analyst", prompt="Estimate cost of implementing X")
Task(subagent_type="financial-analyst", prompt="Calculate ROI for optimization project")
```

---

#### 8. SKILL-DEVELOPER
**Purpose**: Develop and optimize new skills, capability enhancement
**Invocation**: When creating new skills or extending Claude Code capabilities
**Tools**: Write, Read, Bash
**Model**: Sonnet
**Responsibilities**:
- Design new skill structures
- Document skill capabilities
- Test skill effectiveness
- Optimize skill triggering

**When to Use**:
```
Task(subagent_type="skill-developer", prompt="Create a new skill for X capability")
Task(subagent_type="skill-developer", prompt="Optimize skill documentation and discovery")
```

---

## Tool Permission Matrix

| Agent | Bash | Read | Write | Grep | Glob | Model |
|-------|------|------|-------|------|------|-------|
| code-analyzer | ✅ | ✅ | ✅ | ✅ | ✅ | Sonnet |
| safety-auditor | ✅ | ✅ | ❌ | ✅ | ✅ | Sonnet |
| system-architect | ✅ | ✅ | ✅ | ❌ | ❌ | Sonnet |
| knowledge-architect | ✅ | ✅ | ✅ | ✅ | ❌ | Sonnet |
| consolidation-analyst | ✅ | ✅ | ❌ | ✅ | ❌ | Sonnet |
| integration-coordinator | ✅ | ✅ | ✅ | ❌ | ❌ | Sonnet |
| financial-analyst | ✅ | ✅ | ❌ | ✅ | ❌ | Haiku |
| skill-developer | ✅ | ✅ | ✅ | ❌ | ❌ | Sonnet |

**Philosophy**: Principle of least privilege - each agent gets only the tools it needs.

---

## Usage Pattern (Anthropic-Aligned)

### ✅ DO: Explicit Delegation with Context

```python
# Good: Clear task, give agent context to make good decisions
Task(
    subagent_type="code-analyzer",
    prompt="""Analyze the change impact:
    - Files modified: src/athena/memory/search.py, src/athena/semantic/store.py
    - Goal: Reduce search latency from 100ms to 50ms
    - Constraints: Must maintain API compatibility
    - Show: Affected components, test requirements, risk assessment"""
)
```

### ❌ DON'T: Expect Proactive Autonomy

```python
# Bad: Expecting agent to autonomously decide to do this
# This violates Anthropic's supervised iteration principle
# Agent shouldn't spontaneously "decide" to review code

# Agent should only operate when explicitly delegated:
Task(subagent_type="safety-auditor", prompt="Review this code")
```

### ✅ DO: Plan Before Delegating

```python
# Good: You plan, then delegate
"Here's my approach: 1) Refactor X, 2) Update tests, 3) Benchmark
 Let me delegate the impact analysis to code-analyzer..."

Task(subagent_type="code-analyzer", prompt="Analyze impact of refactor...")
```

### ✅ DO: Use Checkpoints

```python
# Good: Ask for approval before big actions
Task(subagent_type="system-architect", prompt="""
    Design approach for X
    Format as: [Problem] [Solution] [Tradeoffs]
    Don't implement yet - I'll review first
""")

# After review:
"OK architect, I approve of Option B. Now implement it..."
```

---

## Key Differences: Skills vs Subagents

| Aspect | Skills (Autonomous) | Subagents (Directed) |
|--------|-------------------|-------------------|
| **Invocation** | Claude auto-decides | You explicitly delegate |
| **Context** | Enhanced within current context | Isolated 50K token window |
| **Scope** | Narrow capability (RAG, analysis) | Full task ownership |
| **Autonomy** | None - reads docs and applies | Directed - you set scope |
| **Examples** | research-coordination, web-research | code-analyzer, safety-auditor |

---

## Delegation Decision Tree

```
You have work to do:
    ↓
"Is this a skill-level capability?"
    ├─ YES (research, analysis, planning help)
    │  └─ Let Claude autonomously use the skill
    │     (skill auto-activates when relevant)
    │
    └─ NO (implementation, deep analysis, explicit decision)
       ↓
       "Do I need a specialist in isolated context?"
       ├─ YES
       │  └─ Delegate to subagent via Task()
       │     Task(subagent_type="...", prompt="...")
       │
       └─ NO
          └─ Do it directly in main context
```

---

## Measuring Agent Effectiveness

### Tier 1 Success Metrics (This Week)
- code-analyzer: Accurately predicts change impacts 90%+ of the time
- safety-auditor: Finds real security issues, low false positives
- system-architect: Designs chosen 80%+ of the time

### Tier 2 Success Metrics (Next Week)
- knowledge-architect: Improves graph coherence measurably
- consolidation-analyst: Suggests optimizations that improve efficiency
- integration-coordinator: Prevents integration issues

### Tier 3 Success Metrics
- financial-analyst: Cost estimates within 20% accuracy
- skill-developer: Creates skills that Claude uses autonomously 50%+ of time

---

## Migration from Old Agent Model

**Old**: 22 agents, many research-oriented, expecting proactivity
**New**: 8 focused subagents + 17 autonomous skills

**Benefits**:
- ✅ Clear responsibility boundaries
- ✅ Reduced context bloat (22 agent definitions → focused 8)
- ✅ Anthropic-aligned supervision patterns
- ✅ Better skill discovery (skills are auto-invoked when relevant)
- ✅ Faster task execution (isolated specialists vs bloated main context)

---

## Next Steps

1. **This Week**: Deploy Tier 1 agents, measure effectiveness
2. **Next Week**: Deploy Tier 2 agents, optimize coordination
3. **Following Week**: Deploy Tier 3 agents, full system optimization

---

**Version**: 1.0 (Anthropic-aligned)
**Status**: Ready for deployment
**Last Updated**: November 12, 2025
