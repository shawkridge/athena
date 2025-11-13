# Phase 3 Strategy: Skills & Agents Alignment

**Scope**: Update skills and agents to demonstrate filesystem API paradigm
**Timeline**: 4-6 hours
**Status**: Planning

---

## What Skills Do

Skills are **reusable capabilities** that Claude uses for specific tasks:
- semantic-search: Advanced semantic retrieval
- memory-retrieval: Finding memories
- execution-tracking: Monitoring execution
- etc.

**Current Pattern**: Use tool definitions and return full data
**New Pattern**: Use filesystem API - discover → read → execute → summarize

---

## What Agents Do

Agents are **autonomous entities** that handle specific responsibilities:
- rag-specialist: Advanced retrieval coordination
- research-coordinator: Multi-source research
- session-initializer: Session startup
- etc.

**Current Pattern**: Call tools, process full data
**New Pattern**: Use filesystem API, work with summaries

---

## Priority Tiers

### Tier 1: Critical Skills (Update First) - 6 files
These directly interact with memory operations:

1. **semantic-search** - Find information semantically
2. **memory-retrieval** - Retrieve memories
3. **pattern-extraction** - Extract patterns from events
4. **procedure-creation** - Create reusable procedures
5. **quality-evaluation** - Evaluate memory quality
6. **graph-navigation** - Navigate knowledge graph

**Pattern for Skills**:
```
1. Discover available operations in target layer
2. Read operation code to understand it
3. Execute operation locally
4. Return summary metrics (counts, IDs, scores)
5. Provide drill-down method for details
```

### Tier 2: Agent Foundation (Update Second) - 5 files
These coordinate between skills:

1. **rag-specialist** - Coordinates retrieval strategies
2. **research-coordinator** - Orchestrates research
3. **session-initializer** - Initializes sessions
4. **system-monitor** - Monitors system health
5. **quality-auditor** - Audits memory quality

**Pattern for Agents**:
```
1. Discover operations needed
2. Spawn parallel sub-agents/skills
3. Each executes locally
4. Agent synthesizes summaries
5. Make decisions based on metrics
```

### Tier 3: Other Skills (Nice to Have) - 9 files
Support operations that can work with current pattern:

- execution-tracking
- load-management
- plan-verification
- task-decomposition
- strategy-analysis
- cost-estimation
- event-triggering
- codebase-understanding
- change-safety

---

## Implementation Pattern

### For Skills

```markdown
---
name: skill-name
description: |
  How this skill uses filesystem API for local execution
---

# Skill Name

## What It Does
Clear description of capability

## How It Works (Filesystem API)

### Step 1: Discover
- Use adapter.list_layers() or list_operations_in_layer()
- Show what operations are available

### Step 2: Execute
- Use adapter.execute_operation()
- All processing happens locally in sandbox

### Step 3: Return Summary
- Never return full data objects
- Return: counts, IDs, scores, metrics
- Example: {"total": 42, "top_ids": [1, 5, 12], "confidence": [0.95, 0.91, 0.88]}

## Usage Examples

Show how this skill is invoked and what it returns

## Token Efficiency
- Old: X tokens
- New: Y tokens
- Savings: Z%
```

### For Agents

```markdown
---
name: agent-name
description: |
  How this agent orchestrates skills using filesystem API
---

# Agent Name

## Responsibilities
What this agent does

## How It Works (Filesystem API)

### Strategy
How it discovers and coordinates operations

### Parallel Execution
- Discovers what operations exist
- Spawns multiple operations
- Each executes locally
- Collects summaries
- Synthesizes results

### Decision Making
How it uses summaries to make decisions

## Examples

Show agent usage and coordination pattern

## Token Efficiency
Demonstrate savings vs old pattern
```

---

## Implementation Approach

### Phase 3a: Tier 1 Skills (2-3 hours)
Update 6 critical memory-operation skills:
1. semantic-search
2. memory-retrieval
3. pattern-extraction
4. procedure-creation
5. quality-evaluation
6. graph-navigation

**Pattern**: Each skill demonstrates local discovery & execution

### Phase 3b: Tier 2 Agents (2-3 hours)
Update 5 coordinating agents:
1. rag-specialist
2. research-coordinator
3. session-initializer
4. system-monitor
5. quality-auditor

**Pattern**: Each agent orchestrates multiple operations

### Phase 3c: Tier 3 Skills (Optional, 1-2 hours)
Update remaining 9 skills as time permits

---

## Key Principle: Local Execution with Summaries

**Before**:
```
Skill invokes tool → Tool loads definitions (150K) → Returns full data (50K)
→ Skill processes in context (15K) = 215K tokens
```

**After**:
```
Skill discovers operations (100) → Executes locally (0) → Returns summary (300)
= 400 tokens, 99% reduction!
```

---

## Success Metrics

✅ All Tier 1 skills updated with filesystem API pattern
✅ All Tier 2 agents updated with local execution pattern
✅ Each demonstrates: discovery, execution, summary returns
✅ Token reduction achieved (99%+)
✅ Examples show practical usage
✅ Documentation complete

---

## Timeline

| Task | Duration | Status |
|------|----------|--------|
| Update 6 Tier 1 skills | 2-3 hrs | Pending |
| Update 5 Tier 2 agents | 2-3 hrs | Pending |
| Test integration | 1 hr | Pending |
| **Total** | **4-6 hrs** | **In Progress** |

---

## After Phase 3

All of Claude's:
- ✅ Hook libraries (Phase 1)
- ✅ Critical commands (Phase 2)
- ✅ Key skills & agents (Phase 3)

Will be using filesystem API with 99%+ token reduction.

This sets foundation for Phase 4 (testing & validation) and
demonstrates the paradigm across entire Claude configuration.

---

## Notes for Implementation

1. **Use the adapter**: Import `FilesystemAPIAdapter` in examples
2. **Show discovery**: Always demonstrate `list_operations` pattern
3. **Show execution**: Always show `execute_operation` calls
4. **Return summaries**: Never show returning full objects
5. **Explain savings**: Show before/after token comparison
6. **Provide examples**: Practical usage examples
7. **Document fallbacks**: Show graceful degradation

This strategy ensures consistency across all updates while
maximizing efficiency and token savings.
