# Claude Code Hook System

Complete hook implementation for autonomous agent orchestration, episodic event recording, and cognitive load management.

**Status**: ✅ Ready for Integration
**Version**: 1.0.0
**Last Updated**: November 6, 2025

---

## Overview

The hook system provides silent background automation that makes the memory/agent/skill system fully autonomous and intelligent.

### What Hooks Do

- ✅ **Auto-invoke agents** at strategic moments (session-start, pre-execution, session-end)
- ✅ **Record episodic events** as work happens (every tool use)
- ✅ **Manage cognitive load** proactively (7±2 working memory model)
- ✅ **Trigger consolidation** at optimal moments (session-end)
- ✅ **Detect issues** and surface alerts (gaps, conflicts, risks)
- ✅ **Learn from patterns** (procedures, heuristics, best practices)

---

## Architecture

### Hook Points (6 Total)

| Hook | Trigger | Agents | Duration | Purpose |
|------|---------|--------|----------|---------|
| **session-start** | Session begins | session-initializer | <500ms | Load context & prime memory |
| **user-prompt-submit** | User submits query | gap-detector, attention-manager, procedure-suggester | <300ms | Analyze input, detect gaps, suggest procedures |
| **post-tool-use** | Every tool executes | (every 10: attention-optimizer) | <100ms/op | Record events, manage load |
| **pre-execution** | Before major work | plan-validator, goal-orchestrator, strategy-selector | <300ms | Validate plans, check goals, assess risk |
| **session-end** | Session ends | consolidation-engine, workflow-learner, quality-auditor | 2-5s | Extract patterns, create procedures, assess quality |
| **post-task-completion** | Task finishes | goal-orchestrator, workflow-learner, execution-monitor | <500ms | Record outcomes, extract learnings |

### Agent Invocation Matrix

```
Hook Point             Agents Invoked                          Priority
─────────────────────────────────────────────────────────────────────────
SessionStart           session-initializer                      100
UserPromptSubmit       gap-detector (90)
                       attention-manager (85)
                       procedure-suggester (80)
PostToolUse (every10)  attention-optimizer (70)
PreExecution           plan-validator (95)
                       goal-orchestrator (90)
                       strategy-selector (80)
SessionEnd             consolidation-engine (100)
                       workflow-learner (95)
                       quality-auditor (90)
PostTaskCompletion     execution-monitor (95)
                       goal-orchestrator (90)
                       workflow-learner (85)
```

---

## Hook Implementations

### NEW: smart-context-injection.sh (HIGHEST PRIORITY)

**Purpose**: Automatically inject relevant memory context into user queries

**What it does**:
- Analyzes query for intent and domain
- Searches memory using optimal RAG strategy
- Ranks results by relevance (0.0-1.0)
- Injects top 3-5 findings into context
- Makes response generation memory-aware

**Agents**:
- rag-specialist (priority 100, runs FIRST)
- research-coordinator (priority 99)

**Skills**:
- memory-retrieval
- semantic-search
- graph-navigation

**Performance**: <400ms (transparent to user)
**Non-blocking**: Yes (pre-processing)

**Example Output**:
```
[SMART-CONTEXT] Analyzing prompt for context retrieval...
[FOUND] Authentication patterns (3 implementations)
[FOUND] JWT vs OAuth discussion (1 decision record)
[FOUND] Common auth pitfalls (2 procedures)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 CONTEXT LOADED FROM MEMORY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Found 3 relevant items:
  • 2 past implementations
  • 1 decision record
  • 1 procedure pattern

These will be available in your response:
  ✓ Similar approaches from past work
  ✓ Known pitfalls and solutions
  ✓ Proven patterns and best practices
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Key Feature**: Makes memory **invisible but always available**

Users don't have to remember what they've learned before. The system remembers for them.

---

### 1. session-start.sh

**Purpose**: Load context at session initialization

**What it does**:
- Invokes session-initializer agent
- Loads active goals and priorities
- Checks memory health (target ≥0.85)
- Displays critical alerts
- Establishes cognitive load baseline

**Example Output**:
```
[SESSION-START] Initializing session context...
[SESSION-START] ✓ Session context loaded
[SESSION-START] ✓ Active goals primed (3 goals)
[SESSION-START] ✓ Memory health checked (0.82 - WARNING)
[SESSION-START] ✓ Cognitive load baseline established (3/7 items)
```

**Duration**: <500ms
**Non-blocking**: Yes

---

### 2. user-prompt-submit.sh

**Purpose**: Analyze user input for gaps, conflicts, and procedures

**What it does**:
- Analyzes query for complexity indicators
- Invokes gap-detector if asking about knowledge
- Checks cognitive load (triggers consolidation if 6/7)
- Suggests applicable procedures
- Identifies strategy needs

**Example Output**:
```
[USER-PROMPT-SUBMIT] Analyzing user prompt...
[USER-PROMPT-SUBMIT INFO] Potential contradiction detected
[USER-PROMPT-SUBMIT INFO] Complex task detected - strategy analysis available
[USER-PROMPT-SUBMIT] ✓ Pre-analysis complete (silent unless alerts)
```

**Duration**: <300ms
**Non-blocking**: Yes (silent unless alerts)

---

### 3. post-tool-use.sh

**Purpose**: Record episodic events and manage cognitive load

**What it does**:
- Records every tool execution as episodic event
- Tracks operation counter
- Checks for anomalies/errors
- Every 10 operations: triggers attention-optimizer
- Attention-optimizer checks load and triggers consolidation if needed

**Example Output**:
```
[POST-TOOL-USE] Recording episodic event: analyze-code (success)
[POST-TOOL-USE] Batch complete (10 operations) - Triggering attention-optimizer
[POST-TOOL-USE] ✓ Attention optimization check complete
```

**Duration**: <100ms per operation
**Batch Duration**: <1s per 10-op batch
**Non-blocking**: Yes

---

### 4. pre-execution.sh

**Purpose**: Validate plans before major work execution

**What it does**:
- Checks for active goal conflicts
- Validates plan (structure, feasibility, rules)
- Runs Q* property verification
- Assesses change risk and safety
- Identifies resource availability

**Example Output**:
```
[PRE-EXECUTION] Pre-execution validation for task: feature-oauth
[PRE-EXECUTION] ✓ No active goal conflicts
[PRE-EXECUTION] ✓ Plan structure valid
[PRE-EXECUTION] ✓ Q* properties verified (score: 0.82, GOOD)
[PRE-EXECUTION] ✓ Risk level: MEDIUM (acceptable)
[PRE-EXECUTION] Status: READY TO EXECUTE
```

**Duration**: <300ms
**Non-blocking**: Yes

---

### 5. session-end.sh

**Purpose**: Extract patterns and consolidate episodic events

**What it does**:
- Runs consolidation with balanced strategy
  - System 1: Fast statistical clustering (~100ms)
  - System 2: LLM validation where uncertainty >0.5 (~1-5s)
- Extracts new procedures from multi-step patterns
- Strengthens memory associations (Hebbian learning)
- Assesses memory quality (compression, recall, consistency, density)
- Updates learning effectiveness metrics

**Example Output**:
```
[SESSION-END] === Session End Consolidation Starting ===
[SESSION-END] Phase 1: Running consolidation (System 1 + selective System 2)...
[SESSION-END]   ✓ Events clustered by temporal/semantic proximity
[SESSION-END]   ✓ Patterns extracted (System 1 baseline)
[SESSION-END]   ✓ High-uncertainty patterns validated (System 2)
[SESSION-END] Phase 2: Extracting reusable procedures...
[SESSION-END]   ✓ Procedures extracted: 2
[SESSION-END] Phase 3: Strengthening memory associations...
[SESSION-END]   ✓ Associations strengthened: 12
[SESSION-END] === Session End Consolidation Complete ===
```

**Duration**: 2-5 seconds (allow time for deep learning)
**Non-blocking**: Yes (runs at session end)

---

### 6. post-task-completion.sh

**Purpose**: Record task outcomes and extract learnings

**What it does**:
- Records task completion with status and metrics
- Updates goal progress
- Records execution metrics (time, quality, resources)
- Extracts reusable procedures from task
- Updates memory associations
- Learns from failures (if applicable)

**Example Output**:
```
[POST-TASK-COMPLETION] Recording task completion: api-endpoints
[POST-TASK-COMPLETION INFO] Status: success
[POST-TASK-COMPLETION] ✓ Progress recorded (40/50 steps complete)
[POST-TASK-COMPLETION] ✓ Time estimation accuracy: +5%
[POST-TASK-COMPLETION] ✓ Procedure extracted: 'API-Endpoint-Implementation'
[POST-TASK-COMPLETION] Status: LEARNING RECORDED
```

**Duration**: <500ms
**Non-blocking**: Yes

---

## Supporting Libraries

### EventRecorder (`lib/event_recorder.py`)

Records episodic events for memory consolidation.

**Methods**:
- `record_tool_execution()` - Log tool execution with status, duration, parameters
- `record_task_start()` - Log task start with estimated duration
- `record_task_completion()` - Log task completion with metrics
- `record_goal_progress()` - Log goal progress updates
- `record_memory_consolidation()` - Log consolidation results
- `get_session_events()` - Retrieve events from a session

**Usage**:
```python
from lib.event_recorder import EventRecorder

recorder = EventRecorder()
recorder.record_tool_execution(
    tool_name="analyze-code",
    status="success",
    duration_ms=1250,
    parameters={"focus_area": "auth"},
)
```

---

### AgentInvoker (`lib/agent_invoker.py`)

Manages autonomous agent invocation based on hook triggers.

**Methods**:
- `get_agents_for_trigger()` - Get agents for a trigger point
- `invoke_agent()` - Invoke specific agent asynchronously
- `invoke_agents_for_trigger()` - Invoke all agents for a trigger
- `get_invoked_agents()` - Get list of agents invoked this session
- `list_all_agents()` - List all registered agents

**Usage**:
```python
from lib.agent_invoker import AgentInvoker

invoker = AgentInvoker()
agents = invoker.get_agents_for_trigger("session_start")
for agent in agents:
    invoker.invoke_agent(agent, context={})
```

---

### LoadMonitor (`lib/load_monitor.py`)

Monitor cognitive load using 7±2 working memory model.

**Zones**:
- **OPTIMAL** (2-4/7): Best performance
- **NORMAL** (4-5/7): Good zone
- **CAUTION** (5/7): Early warning
- **NEAR_CAPACITY** (6/7): Auto-consolidate
- **OVERFLOW** (7/7): Emergency

**Methods**:
- `add_item()` - Add item to working memory
- `access_item()` - Access item (track usage)
- `get_current_load()` - Get current load (N/7)
- `get_load_zone()` - Get zone name
- `get_status()` - Get complete status
- `consolidate()` - Consolidate items to semantic memory
- `get_items_for_archiving()` - Get items ready for consolidation

**Usage**:
```python
from lib.load_monitor import LoadMonitor

monitor = LoadMonitor()
monitor.add_item("feature-oauth", "Add OAuth2 support", importance=0.8)

status = monitor.get_status()
if status["should_consolidate"]:
    items = monitor.get_items_for_archiving()
    monitor.consolidate([item["id"] for item in items])
```

---

## Integration with Commands, Agents, Skills

### Hook → Command → Agent → Skill Flow

```
Hook triggers
    ↓
Invokes slash command (e.g., /session-start)
    ↓
User sees output
    ↓
Command triggers agent invocation
    ↓
Agent uses tools (operations)
    ↓
Tools may activate skills
    ↓
Skills provide domain expertise
    ↓
Results recorded as episodic events
```

### Example: Session End Workflow

```
session-end hook fires
    ↓
/consolidate --strategy balanced command invoked
    ↓
consolidation-engine agent activated
    ↓
Uses consolidation_tools to:
    - Extract patterns (System 1)
    - Validate high-uncertainty patterns (System 2)
    - Create procedures
    ↓
pattern-extraction skill activates
    ↓
Provides dual-process reasoning expertise
    ↓
Result: New semantic memories stored
    ↓
Event recorded for next session consolidation
```

---

## Configuration

### Hook Enable/Disable

To disable a hook temporarily (edit respective file):

```bash
# Disable hook by exiting early
if [ "$HOOKS_DISABLED" = "true" ]; then
    exit 0
fi
```

### Verbosity Control

Set verbosity level:

```bash
# Silent mode (errors only)
HOOK_VERBOSITY=silent

# Minimal mode (critical alerts only)
HOOK_VERBOSITY=minimal

# Verbose mode (all logging)
HOOK_VERBOSITY=verbose
```

### Timeout Configuration

Adjust timeouts in hook files:

```bash
# SessionStart: 500ms max
# UserPromptSubmit: 300ms max
# PostToolUse: 100ms max per operation
# PreExecution: 300ms max
# SessionEnd: 5000ms (allow consolidation time)
```

---

## File Structure

```
.claude/hooks/
├── session-start.sh                 (Core: Context loading)
├── user-prompt-submit.sh            (Core: Gap detection)
├── post-tool-use.sh                 (Core: Event recording)
├── session-end.sh                   (Core: Consolidation)
├── pre-execution.sh                 (Strategic: Plan validation)
├── post-task-completion.sh          (Strategic: Outcome recording)
├── lib/
│   ├── __init__.py
│   ├── event_recorder.py            (Episodic event storage)
│   ├── agent_invoker.py             (Agent orchestration)
│   └── load_monitor.py              (Cognitive load tracking)
├── logs/                            (Event logs directory)
│   └── events-YYYY-MM-DD.jsonl     (Daily event journal)
├── .working-memory                  (Working memory state)
└── README.md                        (This file)
```

---

## Performance Characteristics

### Execution Times

| Hook | Target | Typical | Notes |
|------|--------|---------|-------|
| session-start | <500ms | 200-300ms | Context loading |
| user-prompt-submit | <300ms | 100-200ms | Silent unless alerts |
| post-tool-use | <100ms/op | 50-80ms | Per operation |
| post-tool-use (batch) | <1s/10ops | 500-800ms | Every 10 operations |
| pre-execution | <300ms | 200-250ms | Plan validation |
| session-end | 2-5s | 3-4s | Allow consolidation time |
| post-task-completion | <500ms | 250-350ms | Outcome recording |

### Cognitive Load Impact

- **SessionStart**: +1 item (session context)
- **UserPromptSubmit**: May consolidate if at 6/7
- **PostToolUse**: Continuous monitoring
- **SessionEnd**: Consolidate 2-4 items
- **PostTaskCompletion**: Archive task-related items

---

## Troubleshooting

### Hook Not Firing

1. Check hook file exists: `ls -la .claude/hooks/`
2. Check hook is executable: `chmod +x .claude/hooks/hook-name.sh`
3. Check for errors: `bash -x .claude/hooks/hook-name.sh`

### High CPU Usage

1. Check post-tool-use batch frequency (every 10 ops by default)
2. Reduce verbosity: Set `HOOK_VERBOSITY=silent`
3. Check for infinite loops in agent invocation

### Lost Events

1. Check logs directory: `ls -la .claude/hooks/logs/`
2. Verify EventRecorder is writing files
3. Check disk space availability

### Cognitive Load Issues

1. Check working memory: `cat .claude/hooks/.working-memory`
2. Manual consolidation: `/consolidate`
3. Clear working memory if corrupted: `rm .claude/hooks/.working-memory`

---

## Future Enhancements

- [ ] Parallel hook execution (currently sequential)
- [ ] Hook performance profiling
- [ ] Event analytics dashboard
- [ ] Configurable hook triggers
- [ ] Hook testing framework
- [ ] Integration tests with all agents

---

## References

- **Commands**: See `/home/user/.claude/commands/`
- **Agents**: See `/home/user/.claude/agents/`
- **Skills**: See `/home/user/.claude/skills/`
- **Design**: See `/home/user/.work/athena/HOOK_STRATEGY_ANALYSIS.md`

---

**Version**: 1.0.0
**Status**: Ready for Production
**Last Updated**: November 6, 2025
