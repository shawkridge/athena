---
description: Load context at session start - initializes memory, loads active goals and recent events, checks system health
argument-hint: Optional project name to focus on specific project
---

# Session Start - Session Initialization

Loads session context from memory at startup, including active memories, goals, and recent events.

## How It Works

1. **Discover** - Count available memories, goals, and events
2. **Execute** - Load active context (7±2 cognitive limit)
3. **Summarize** - Return session state with recommendations

## Implementation

```bash
#!/bin/bash
# Session Start Command
# Usage: /critical:session-start [--project /path/to/project]

PROJECT="${1:-}"

cd /home/user/.work/athena
PYTHONPATH=/home/user/.work/athena/src python3 -m athena.cli --json session-start ${PROJECT:+--project "$PROJECT"}
```

## Examples

```bash
# Load session context for current project
/critical:session-start

# Load context for specific project
/critical:session-start --project /home/user/.work/athena

# Load context and see what's active
/critical:session-start
```

## Response Format

```json
{
  "status": "success",
  "project": "athena",
  "project_id": 2,
  "session_initialized": true,
  "active_memory": {
    "count": 7,
    "items": [
      {
        "id": 4816,
        "type": "tool_execution",
        "content": "Memory item...",
        "timestamp": 1763123149297,
        "importance": 0.9
      }
    ]
  },
  "active_goals": {
    "count": 3,
    "items": [
      {
        "id": 42,
        "title": "Implement context injection",
        "status": "in_progress",
        "priority": 1
      }
    ]
  },
  "recent_events": {
    "count": 5,
    "events": [
      {
        "id": 4816,
        "type": "tool_execution",
        "content": "Memory event...",
        "time": "2025-11-14T14:25:49Z"
      }
    ]
  },
  "ready_for_work": true,
  "execution_time_ms": 45
}
```

## Pattern Details

### Phase 1: Discover
- Gets project context from current directory
- Counts active memories (7±2)
- Counts active goals (prospective tasks)
- Counts recent events (episodic layer)
- Returns: count summary

### Phase 2: Execute
- Loads top 7 active memories by importance
- Loads active goals by priority
- Loads 5 most recent events
- Returns: detailed context

### Phase 3: Summarize
- Formats context for session display
- Indicates readiness for work
- Returns structured JSON (<500 tokens)

## Context Layers Loaded

- **Active Memory (7±2)**: High-importance recent events
- **Active Goals**: Prospective tasks (in_progress or active status)
- **Recent Events**: Last 5 episodic events for temporal context
- **Project Info**: Current project name and ID

## Cognitive Load

Session initialization respects Miller's 7±2 cognitive limit:
- Max 7 active memory items
- Max 5 active goals recommended
- Max 5 recent events for context
