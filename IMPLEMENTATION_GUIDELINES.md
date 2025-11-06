# Hook/Agent/Command/Skill Implementation Guidelines

Based on official Claude Code documentation and existing implementations in this codebase.

## 1. HOOKS (Bash Scripts)

### Location
- Global: `~/.claude/hooks/[hook-name].sh`
- Project: `.claude/hooks/[hook-name].sh` (shared via git)

### Supported Hook Events
```
- session-start         (session begins)
- user-prompt-submit    (user submits query)
- post-tool-use         (after tool execution)
- pre-execution         (before major work)
- session-end           (session ends)
- post-task-completion  (task finishes)
```

### Hook Structure
```bash
#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Logging functions
log() {
    echo -e "${GREEN}[HOOK-NAME]${NC} $1" >&2
}

log_warn() {
    echo -e "${YELLOW}[HOOK-NAME WARNING]${NC} $1" >&2
}

# Get hook input from environment
PARAM_NAME="${PARAM_NAME:-default}"

# Do actual work
log "Starting hook..."

# Call MCP tools as needed
# Example: mcp__athena__memory_tools recall_events "query"

log "Hook completed successfully"
exit 0
```

### Exit Codes
- **0**: Success (output shown in transcript mode)
- **2**: Blocking error (stderr fed to Claude, halts execution)
- **Other**: Non-blocking error (logged but doesn't interrupt)

### Key Constraints
- **Timeout**: Different by hook type:
  - SessionStart: <500ms
  - UserPromptSubmit: <300ms
  - PostToolUse: <100ms per operation
  - PreExecution: <300ms
  - SessionEnd: 2-5s (allow consolidation time)
  - PostTaskCompletion: <500ms
- **Non-blocking**: Should always exit 0 (never throw)
- **Graceful degradation**: Always have fallback if MCP unavailable

### Calling MCP Tools from Hooks

**Option 1: Direct MCP Tool Call** (Recommended)
```bash
# Call MCP tool function directly
# Format: mcp__<server>__<tool> <operation> [params]

# Example: Record episodic event
mcp__athena__episodic_tools record_event \
  "tool_execution" \
  "Tool: analyze-code, Status: success, Duration: 1250ms" \
  "success"
```

**Option 2: Invoke Slash Command** (For user-visible commands)
```bash
# Use SlashCommand tool to invoke slash command
# This invokes `/consolidate --strategy balanced`
```

**Option 3: Via Library Python Scripts**
```bash
# Call Python library helpers
python3 /home/user/.claude/hooks/lib/event_recorder.py --record-event \
  --tool-name "analyze-code" \
  --status "success" \
  --duration 1250
```

### Invoking Agents from Hooks

**Method 1: Via SlashCommand** (Preferred)
```bash
# Invoke agent through slash command
# /consolidate invokes consolidation-engine agent
# /memory-query invokes rag-specialist agent
```

**Method 2: Via AgentInvoker Library** (Direct)
```bash
# Use agent_invoker.py to invoke agents
python3 /home/user/.claude/hooks/lib/agent_invoker.py \
  --invoke-agent "consolidation-engine" \
  --context '{"strategy": "balanced"}'
```

**Method 3: Via Task Tool** (For complex orchestration)
```bash
# Use the Task tool (invokes specialized agents)
# This is available within Claude Code environment
```

### Handling Timeouts

```bash
# Use timeout command to prevent hook from blocking
timeout 300ms python3 /path/to/script.py
RESULT=$?

if [ $RESULT -eq 124 ]; then
    log_warn "Operation timed out - skipping (non-blocking)"
    exit 0  # Don't block execution
elif [ $RESULT -ne 0 ]; then
    log_warn "Operation failed with code $RESULT"
    exit 0  # Still non-blocking
fi
```

---

## 2. AGENTS (Markdown with YAML)

### Location
- Global: `~/.claude/agents/[agent-name].md`
- Project: `.claude/agents/[agent-name].md`

### File Format

```markdown
---
name: agent-name
description: |
  Brief description of what the agent does.
  When to use it and what it's specialized in.

  Multiple paragraphs okay.
tools: tool1, tool2, tool3
model: sonnet  # or haiku for quick tasks
---

# Agent Name

Detailed instructions for the agent.

## Core Responsibilities

1. Responsibility one
2. Responsibility two

## Output Format

What the agent should return/produce.

## Examples

Good and bad examples.

## Avoid

What the agent should NOT do.
```

### Key Fields

| Field | Required | Purpose |
|-------|----------|---------|
| `name` | Yes | Agent identifier (lowercase, hyphens) |
| `description` | Yes | When/why to use (determines auto-invocation) |
| `tools` | Yes | Comma-separated list of MCP tools available |
| `model` | No | Claude model to use (default: sonnet) |

### Design Principles

1. **Single Focus**: One agent = one specialized capability
2. **Tool Declarations**: List ALL tools agent needs access to
3. **Clear Instructions**: Explicit expectations and output format
4. **Examples**: Show what good output looks like
5. **Constraints**: Document any limitations

### Examples of Well-Designed Agents

**consolidation-engine.md**:
- Specialized in pattern extraction
- Uses: consolidation_tools, memory_tools, procedural_tools
- Documented: System 1 vs System 2 reasoning
- Output: Quality metrics, procedures, patterns

**rag-specialist.md**:
- Specialized in semantic retrieval
- Uses: rag_tools, memory_tools
- Documented: 4 strategies with auto-selection
- Output: Ranked results, confidence scores

---

## 3. COMMANDS (Slash Commands)

### Two Types of Commands

#### Built-in Commands
Pre-existing in Claude Code (e.g., `/help`)

#### Custom Commands (Defined Locally)

**Location**: `.claude/commands/[command-name].md` (in project)

**File Format**:
```markdown
---
command: /command-name
description: What the command does
---

# Command Title

Detailed explanation of what the command does when invoked.

## Usage

/command-name [options]

## Parameters

...

## Examples

...
```

### Relating Commands to Agents

```
Command invoked by user
  ↓
Triggers agent(s) with matching description
  ↓
Agent uses declared tools
  ↓
Results returned to user
```

Example: `/consolidate` command
- User types: `/consolidate --strategy balanced`
- Matches: consolidation-engine agent (description mentions consolidation)
- Agent invokes: consolidation_tools operations
- Returns: Quality metrics, new procedures, patterns extracted

---

## 4. SKILLS (Directory-Based)

### Location
- Global: `~/.claude/skills/[skill-name]/`
- Project: `.claude/skills/[skill-name]/`

### Directory Structure

```
skills/memory-retrieval/
├── SKILL.md                 (Required: skill definition)
├── supporting-doc.md        (Optional: additional docs)
├── template.txt            (Optional: templates)
└── helper.py               (Optional: helper scripts)
```

### SKILL.md Format

```markdown
---
name: skill-name
description: |
  What this skill does.
  When Claude should use it (triggers auto-invocation).
  One paragraph is fine but can be longer.
---

# Skill Name

Detailed instructions for using this skill.

## When to Use

Specific scenarios where this skill excels.

## How It Works

Explanation of the skill's mechanism.

## What You Get

Expected outputs.

## Examples

Usage examples.

## Best Practices

Tips for getting best results.
```

### Key Principles

1. **Model-Invoked**: Claude decides when to use (based on description)
2. **Discoverable**: Description is critical for auto-invocation
3. **Focused**: One skill = one capability
4. **Reusable**: Can be used across multiple projects
5. **Testable**: Should work independently

### Skill vs Agent Distinction

| Aspect | Skill | Agent |
|--------|-------|-------|
| Invocation | Auto (by Claude) | Triggered by hooks/commands |
| Scope | Single capability | Multi-step orchestration |
| Tools | Flexible | Declared upfront |
| Complexity | Simple-moderate | Complex |
| Examples | memory-retrieval, semantic-search | consolidation-engine, goal-orchestrator |

---

## IMPLEMENTATION APPROACH FOR THIS PROJECT

### Critical Path (Hooks Must Work First)

1. **agent_invoker.py**: Core infrastructure - enables all agent invocations
2. **post-tool-use.sh**: Record episodic events - enables data capture
3. **session-end.sh**: Consolidation - converts episodic to semantic
4. **session-start.sh**: Context loading - uses semantic memories
5. **pre-execution.sh**: Plan validation - safety before execution
6. **post-task-completion.sh**: Outcome recording - goal tracking

### Integration Points

```
Hook fires
  ↓
Calls MCP tools OR invokes agent/command
  ↓
Agent/Command uses Skills for specialized work
  ↓
Results recorded as episodic events
  ↓
Session-end consolidation creates semantic memories
  ↓
Next session: context loaded from semantic memories
```

### Proper MCP Tool Invocation

From hooks, you can call MCP tools directly:

```bash
# Pattern: mcp__<server>__<operation> with params

# Record episodic event
mcp__athena__episodic_tools record_event \
  --event-type "tool_execution" \
  --content '{"tool": "analyze-code", "status": "success"}' \
  --outcome "success"

# Retrieve semantic memories
mcp__athena__rag_tools retrieve_smart \
  --query "authentication patterns" \
  --limit 5

# Update working memory
mcp__athena__memory_tools update_working_memory \
  --content "current task context" \
  --importance 0.8
```

### Proper Agent Invocation

From hooks, invoke agents via:

**Method A: Via SlashCommand Tool** (Cleanest)
```bash
# Invoke slash command that triggers agent
# Example: /consolidate → triggers consolidation-engine agent
```

**Method B: Via agent_invoker.py** (Direct)
```python
from lib.agent_invoker import AgentInvoker

invoker = AgentInvoker()
agents = invoker.get_agents_for_trigger("session_end")
for agent in agents:
    invoker.invoke_agent(agent, context={...})
```

**Method C: Via Task Tool** (Within Claude Code)
```python
# Use Task tool to invoke specialized agents
# Available within Claude Code environment only
```

---

## TESTING YOUR IMPLEMENTATIONS

### Hook Testing

```bash
# Test hook directly
bash /path/to/hook.sh

# With input
PARAM_NAME="value" bash /path/to/hook.sh

# Check for syntax errors
bash -n /path/to/hook.sh
```

### Agent Testing

1. Create test markdown with same format
2. Invoke manually: `/consolidate` or `/memory-query`
3. Check agent is being called correctly
4. Verify tools are accessible

### Integration Testing

1. Run hook in simulated environment
2. Verify MCP tools are called
3. Check for side effects (database updates, etc.)
4. Measure execution time

---

## DOCUMENTATION REQUIREMENTS

### For Each Hook
- [ ] Describe what it does
- [ ] List agents it invokes
- [ ] Show expected output
- [ ] Document timeout budget
- [ ] Error handling approach

### For Each Agent
- [ ] Clear description with triggers
- [ ] List all tools it needs
- [ ] Expected output format
- [ ] Examples of usage
- [ ] Constraints/limitations

### For Each Command
- [ ] Usage syntax
- [ ] What it does (user-facing)
- [ ] Which agent it activates
- [ ] Example output

### For Each Skill
- [ ] When to use (discovery triggers)
- [ ] What it provides
- [ ] Best practices
- [ ] Examples

---

## COMMON PATTERNS

### Pattern 1: Hook → Agent → Tools

```bash
# In hook
log "Invoking consolidation-engine..."
/consolidate --strategy balanced

# This:
# 1. Activates consolidation-engine agent (description matches)
# 2. Agent uses consolidation_tools operations
# 3. Results recorded as episodic events
```

### Pattern 2: Episodic Event Recording

```bash
# Record what happened
mcp__athena__episodic_tools record_event \
  --event-type "tool_execution" \
  --content "Tool executed: $TOOL_NAME" \
  --outcome "$STATUS"
```

### Pattern 3: Cognitive Load Management

```bash
# Check if consolidation needed
if [ $COUNTER -ge 6 ]; then
    log "Cognitive load HIGH - triggering consolidation"
    /consolidate --strategy speed
fi
```

### Pattern 4: Error Handling

```bash
# Always exit 0 unless blocking error
if some_error_occurred; then
    log_warn "Error: $ERROR_MESSAGE"
    # Don't exit 2 (blocking) - log only
    exit 0
fi
```

---

## QUICK REFERENCE

### Hook Event Triggers
```
SessionStart      → Load context, prime memory
UserPromptSubmit  → Analyze, detect gaps, suggest
PostToolUse       → Record events, manage load
PreExecution      → Validate plans, check goals
SessionEnd        → Consolidate, extract patterns
PostTaskCompletion→ Record outcomes, learn
```

### Agent Invocation Methods
```
1. /command-name              (via SlashCommand)
2. agent_invoker.py           (direct Python)
3. Task tool                  (within Claude Code)
```

### MCP Tool Categories
```
memory_tools       - Core memory operations
episodic_tools     - Event recording
rag_tools          - Semantic retrieval
consolidation_tools - Pattern extraction
planning_tools     - Plan validation/optimization
task_management    - Goal and task tracking
```

---

**Version**: 1.0
**Date**: 2025-11-06
**Status**: Complete Implementation Guide
