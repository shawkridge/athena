---
description: Break down complex task into executable steps using hierarchical decomposition - returns structured plan with dependencies
argument-hint: "Task description to decompose"
---

# Plan Task - Task Decomposition

Decomposes complex tasks into executable steps using procedural knowledge and decomposition strategies.

## How It Works

1. **Discover** - Count similar procedures in database
2. **Execute** - Decompose task hierarchically (1-5 levels)
3. **Summarize** - Return structured plan with steps, timelines, dependencies

## Implementation

```bash
#!/bin/bash
# Plan Task Command
# Usage: /critical:plan-task "task description" [--levels 3]

TASK="${1:-}"
LEVELS="${2:-3}"

if [ -z "$TASK" ]; then
  echo '{"status": "error", "error": "Task description required"}'
  exit 1
fi

cd /home/user/.work/athena
PYTHONPATH=/home/user/.work/athena/src python3 -m athena.cli --json plan-task "$TASK" --levels "$LEVELS"
```

## Examples

```bash
# Simple task decomposition
/critical:plan-task "implement context injection"

# Detailed breakdown
/critical:plan-task "add memory search to CLI" --levels 5

# With strategy
/critical:plan-task "refactor consolidation layer" --levels 3
```

## Response Format

```json
{
  "status": "success",
  "task": "implement context injection",
  "decomposition_levels": 3,
  "steps_generated": 5,
  "similar_procedures_available": 2,
  "steps": [
    {
      "level": 1,
      "step": 1,
      "title": "Analyze requirements",
      "description": "Understand task scope",
      "estimated_minutes": 15,
      "dependencies": []
    },
    {
      "level": 2,
      "step": 2,
      "title": "Design solution",
      "description": "Create implementation plan",
      "estimated_minutes": 30,
      "dependencies": [1]
    }
  ],
  "estimated_duration_minutes": 155,
  "execution_time_ms": 25
}
```

## Pattern Details

### Phase 1: Discover
- Queries procedures table for similar tasks
- Uses task keywords to find applicable workflows
- Returns: similar_procedures_available

### Phase 2: Execute
- Decomposes task hierarchically (1-5 levels)
- Creates step relationships and dependencies
- Estimates time for each step
- Returns: step_count + detailed steps

### Phase 3: Summarize
- Formats steps with dependencies
- Calculates total estimated duration
- Returns structured plan (300 tokens max)

## Decomposition Levels

- **Level 1**: Main phases (what major stages needed?)
- **Level 2**: Detailed breakdown (what specific tasks in each phase?)
- **Level 3**: Granular tasks (what micro-tasks make up each task?)
- **Level 4**: Sub-tasks (further refinement if needed)
- **Level 5**: Atomic operations (lowest granularity)
