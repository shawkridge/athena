# Hook Strategy for New Command/Agent/Skill System

**Date**: November 6, 2025
**Status**: Analysis & Recommendations

---

## Why Hooks Are Critical

Our new system has:
- **20 commands** (user-invoked, explicit)
- **21 agents** (auto-delegated, need activation)
- **15 skills** (model-invoked, need triggers)
- **254 MCP operations** (need intelligent routing)

**Hooks are the connective tissue** that makes the system autonomous and intelligent by:

1. **Auto-invoking agents** at strategic times (session-start, session-end, post-execution)
2. **Recording episodic events** as work happens (every tool use)
3. **Managing cognitive load** proactively (7±2 working memory)
4. **Triggering consolidation** at optimal moments (session-end, after major work)
5. **Detecting quality issues** and conflicts (post-execution validation)
6. **Learning from patterns** (extracting procedures, heuristics)

---

## Hook Activation Points

### Hook 1: SessionStart (~100-200ms)
**Current Purpose**: Load context
**New System Needs**:
- ✅ Invoke `session-initializer` agent
- ✅ Load top active goals
- ✅ Check memory health
- ✅ Prime working memory
- ✅ Display critical alerts

**Implementation**:
```bash
# claude/hooks/session-start.sh
/session-start
```

**Expected Output**:
- Project context loaded
- Memory quality score
- Active goals ranked
- Cognitive load baseline
- Critical blockers surfaced

---

### Hook 2: UserPromptSubmit (~300-500ms)
**Current Purpose**: Detect gaps, suggest procedures
**New System Needs**:
- ✅ Invoke `attention-manager` agent
- ✅ Check for goal conflicts
- ✅ Detect knowledge gaps
- ✅ Suggest applicable procedures
- ✅ Monitor cognitive load
- ✅ Pre-analyze query complexity

**Implementation**:
```bash
# claude/hooks/user-prompt-submit.sh
# Auto-check for conflicts and gaps
```

**Agent Triggers**:
- `gap-detector` - Find contradictions/uncertainties
- `attention-manager` - Manage focus, suppress distractions
- `procedure-suggester` - Recommend applicable workflows
- `strategy-selector` - Analyze task complexity

---

### Hook 3: PostToolUse (~immediate, every operation)
**Current Purpose**: Route memory operations
**New System Needs**:
- ✅ Record episodic events (what just happened)
- ✅ Update task progress
- ✅ Monitor tool effectiveness
- ✅ Track execution patterns
- ✅ Detect anomalies
- ✅ Fire every 10th operation: attention-optimizer

**Implementation**:
```bash
# claude/hooks/post-tool-use.sh
# Record execution, route memory ops
# Every 10 operations: trigger attention-optimizer
```

**Operations**:
- Record event (tool name, parameters, result)
- Update goal progress if task-related
- Check for errors and anomalies
- Track tool success rates

---

### Hook 4: PreExecution (~200-300ms, before major work)
**Current Purpose**: Validate plans
**New System Needs**:
- ✅ Invoke `plan-validator` agent
- ✅ Check goal state (conflicts, blockers)
- ✅ Verify strategy selected
- ✅ Alert on risks
- ✅ Ensure resources available

**Implementation**:
```bash
# claude/hooks/pre-execution.sh
# Validate before committing to work
```

**Agent Triggers**:
- `planning-orchestrator` - Strategy verification
- `strategy-selector` - Confirm optimal approach
- `goal-orchestrator` - Check conflicts/blockers
- `safety-auditor` - Risk assessment

---

### Hook 5: SessionEnd (~2-5 seconds, consolidation)
**Current Purpose**: Extract patterns, strengthen links
**New System Needs**:
- ✅ Invoke `consolidation-engine` agent
- ✅ Extract patterns from session work
- ✅ Create/update procedures
- ✅ Strengthen memory associations
- ✅ Update memory quality metrics
- ✅ Check for contradictions
- ✅ Record session summary

**Implementation**:
```bash
# claude/hooks/session-end.sh
/consolidate --strategy balanced
```

**Agent Triggers**:
- `consolidation-engine` - Pattern extraction
- `workflow-learner` - Procedure creation
- `association-learner` - Strengthen links
- `quality-auditor` - Quality assessment
- `learning-monitor` - Effectiveness tracking

---

### Hook 6: PostTaskCompletion (~500ms, after major work)
**Current Purpose**: Record progress
**New System Needs**:
- ✅ Update goal progress
- ✅ Record execution outcome
- ✅ Extract learnings
- ✅ Trigger workflow-learner for procedures
- ✅ Update task health
- ✅ Check milestone status

**Implementation**:
```bash
# claude/hooks/post-task-completion.sh
# Update goal state, extract learnings
```

**Agent Triggers**:
- `execution-monitor` - Update task health
- `goal-orchestrator` - Record progress
- `workflow-learner` - Extract procedures
- `quality-auditor` - Quality check

---

## Recommended Hook Configuration

### Tier 1: Essential Hooks (Required)

```yaml
session-start:
  agent: session-initializer
  timeout: 500ms

user-prompt-submit:
  agents: [attention-manager, gap-detector, procedure-suggester]
  timeout: 300ms

post-tool-use:
  operation: record-event + every-10-trigger-attention-optimizer
  timeout: 100ms

session-end:
  agent: consolidation-engine
  timeout: 5000ms (allow time for consolidation)
```

### Tier 2: Strategic Hooks (Highly Recommended)

```yaml
pre-execution:
  agents: [plan-validator, goal-orchestrator]
  timeout: 300ms

post-task-completion:
  agents: [goal-orchestrator, workflow-learner]
  timeout: 500ms
```

### Tier 3: Optional Hooks (Nice-to-Have)

```yaml
pre-plan-optimization:
  agent: strategy-selector
  timeout: 300ms

post-consolidation:
  agent: quality-auditor
  timeout: 500ms

periodic-health-check:
  agent: system-monitor
  interval: daily
  timeout: 1000ms
```

---

## Hook Activation Matrix

| Hook | SessionStart | PostTool | PreExec | SessionEnd | PostComplete |
|------|--------------|----------|---------|-----------|--------------|
| session-initializer | ✅ | | | | |
| attention-manager | | ✅ | | | |
| consolidation-engine | | | | ✅ | |
| execution-monitor | | ✅ | ✅ | | ✅ |
| goal-orchestrator | ✅ | | ✅ | ✅ | ✅ |
| quality-auditor | | | | ✅ | ✅ |
| workflow-learner | | | | ✅ | ✅ |
| strategy-selector | | ✅ | ✅ | | |
| error-handler | | ✅ | | | |

---

## Hook Implementation Details

### Hook 1: session-start.sh
```bash
#!/bin/bash
# Session initialization: Load context and prime memory

# Run session-initializer agent (async, non-blocking)
# - Load project status
# - Check memory health
# - Display active goals
# - Surface critical alerts

# Typical output: 2-3 lines of critical information
# Duration: <200ms
```

### Hook 2: user-prompt-submit.sh
```bash
#!/bin/bash
# Pre-analysis of user input

# Analyze query to trigger appropriate agents:
# 1. Gap-detector if asking about knowledge
# 2. Attention-manager for context management
# 3. Procedure-suggester for known patterns
# 4. Strategy-selector for complex tasks

# Silent unless critical alerts
# Duration: <300ms
```

### Hook 3: post-tool-use.sh
```bash
#!/bin/bash
# Record every tool operation

# On every tool use:
# - Record event (what happened)
# - Update progress if task-related
# - Check for anomalies

# Every 10th operation:
# - Trigger attention-optimizer
# - Check cognitive load
# - Consolidate if needed

# Duration: <100ms per operation, <1s per 10-op batch
```

### Hook 4: session-end.sh
```bash
#!/bin/bash
# Deep learning consolidation

# Run consolidation:
# /consolidate --strategy balanced

# This triggers:
# - consolidation-engine: Pattern extraction
# - workflow-learner: Procedure creation
# - association-learner: Strengthen links
# - quality-auditor: Quality assessment

# Duration: 2-5 seconds (allow time for depth)
# Output: New memories, procedures, quality metrics
```

---

## Cognitive Load Management via Hooks

### Hook Integration with 7±2 Model

**Current Capacity Check**:
- `post-tool-use` hook monitors working memory usage
- At 5/7 items: Alert user
- At 6/7 items: Auto-trigger consolidation
- At 7/7 items: Force consolidation

**Automatic Management**:
```
Hook: post-tool-use (every 10 operations)
  → attention-optimizer checks capacity
  → If 6/7 items: trigger /consolidate
  → Returns capacity to 4-5/7 (optimal zone)
```

**Result**: Users stay in optimal zone without manual action.

---

## Memory Event Recording via Hooks

### What Gets Recorded

Every tool use records:
- **Operation**: Which MCP operation ran
- **Parameters**: What it was called with
- **Result**: Success/failure
- **Duration**: How long it took
- **Context**: Active goal, project, session
- **Timestamp**: When it happened
- **Outcome**: What changed

### Why This Matters

These recorded events feed:
1. **Consolidation** - Patterns extracted from events
2. **Learning** - What works, what doesn't
3. **Analytics** - Tool effectiveness, performance trends
4. **Debugging** - Root cause analysis when things fail
5. **Optimization** - Bottleneck identification

---

## Recommended Hook Implementation Plan

### Phase 1: Core Hooks (Week 1)
```bash
✅ session-start.sh         - Load context
✅ user-prompt-submit.sh    - Analyze query
✅ post-tool-use.sh         - Record events
✅ session-end.sh           - Consolidate
```

### Phase 2: Strategic Hooks (Week 2)
```bash
✅ pre-execution.sh         - Validate plans
✅ post-task-completion.sh  - Record outcomes
```

### Phase 3: Optional Hooks (Week 3+)
```bash
⚙️ periodic-health-check    - Daily monitoring
⚙️ post-consolidation       - Quality tracking
⚙️ error-recovery           - Learning from failures
```

---

## Hook Design Principles

### Silent Operation
- Hooks run without interrupting user workflow
- Return only critical alerts (if any)
- Non-blocking (async where possible)
- <300ms execution time for most hooks

### Error Resilience
- If hook fails, continue main workflow
- Log errors for debugging
- Fall back gracefully
- Never crash user experience

### Performance
- Lightweight operations in hot paths (PostToolUse)
- Heavier operations at boundaries (SessionStart/End)
- Cache where possible
- Batch operations (every 10 tool uses)

### Transparency
- Users can see what hooks are running
- Hooks log what they're doing
- Configurable verbosity (silent/minimal/verbose)
- Override capability for privacy

---

## Hook Configuration Files

### Location: `.claude/hooks/`

**Core Hooks**:
```
.claude/hooks/
├── session-start.sh              (context loading)
├── user-prompt-submit.sh         (gap detection, procedure suggestion)
├── post-tool-use.sh              (event recording, every-10 logic)
└── session-end.sh                (consolidation)
```

**Optional Hooks**:
```
├── pre-execution.sh              (plan validation)
├── post-task-completion.sh       (outcome recording)
├── periodic-monitor.sh           (daily health checks)
└── error-recovery.sh             (failure learning)
```

**Supporting Libraries**:
```
├── lib/
│   ├── mcp_wrapper.py            (MCP operation routing)
│   ├── event_recorder.py         (episodic event storage)
│   ├── agent_invoker.py          (autonomous agent triggering)
│   ├── load_monitor.py           (cognitive load tracking)
│   └── consolidation_coordinator.py  (pattern extraction)
```

---

## Hook vs Command: When to Use Each

| Scenario | Hook | Command |
|----------|------|---------|
| User explicitly requests action | ❌ | ✅ (`/memory-search`) |
| Automatic context priming | ✅ | ❌ (session-start hook) |
| Recording work that just happened | ✅ | ❌ (post-tool-use hook) |
| User wants to search memory | ❌ | ✅ (`/memory-search`) |
| Consolidating at session end | ✅ | ❌ (session-end hook) |
| User wants to create a goal | ❌ | ✅ (`/manage-goal`) |
| Checking for memory gaps | ✅ | ❌ (user-prompt-submit hook) |
| User wants detailed memory assessment | ❌ | ✅ (`/assess-memory`) |

**Key Principle**: Hooks automate routine intelligence gathering. Commands provide explicit user control.

---

## Implementation Recommendation

### YES, We Need Hooks

**Critical hooks to implement immediately**:
1. ✅ `session-start` - Auto-invoke session-initializer
2. ✅ `user-prompt-submit` - Gap detection + procedure suggestion
3. ✅ `post-tool-use` - Record episodic events
4. ✅ `session-end` - Consolidation with consolidation-engine

**Strategic hooks to implement soon**:
5. ✅ `pre-execution` - Plan validation before major work
6. ✅ `post-task-completion` - Record outcomes and extract procedures

**Optional hooks for advanced system**:
7. ⚙️ `periodic-health-check` - Daily system monitoring
8. ⚙️ `error-recovery` - Learn from failures

### Why This Is Important

Without hooks:
- ❌ No automatic episodic event recording
- ❌ No cognitive load management
- ❌ No automatic consolidation
- ❌ No gap detection
- ❌ No procedure learning
- ❌ Users must manually invoke everything

With hooks:
- ✅ Automatic event recording enables consolidation and learning
- ✅ Automatic cognitive load management prevents overwhelm
- ✅ Automatic procedure extraction captures best practices
- ✅ Silent background intelligence gathering
- ✅ Agents auto-invoked at strategic times
- ✅ System learns and improves over time

---

## Summary

| Aspect | Impact |
|--------|--------|
| **Cognitive Load** | Hooks auto-manage via attention-optimizer |
| **Memory Learning** | Hooks enable consolidation via episodic recording |
| **Automation** | Hooks trigger agents autonomously |
| **User Experience** | Hooks silent unless critical alerts |
| **System Intelligence** | Hooks feed all learning and optimization |

**Recommendation**: Implement 4 core hooks immediately, 2 strategic hooks shortly after.

