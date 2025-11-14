---
description: Create, activate, or complete goals with conflict detection and lifecycle tracking - manages prospective memory layer
argument-hint: "$1 = goal name, $2 = action (create|list|update|complete), $3 = details"
---

# Manage Goal - Goal Lifecycle Management

Creates, lists, updates, and completes goals with conflict detection and priority tracking.

## How It Works

1. **Discover** - Count existing goals, detect conflicts
2. **Execute** - Perform goal operation (CRUD)
3. **Summarize** - Return goal state and recommendations

## Implementation

```bash
#!/bin/bash
# Manage Goal Command
# Usage: /critical:manage-goal create "goal name" [--details "description"]
#        /critical:manage-goal list
#        /critical:manage-goal update "goal name" [--details "new details"]
#        /critical:manage-goal complete "goal name"

ACTION="${1:-list}"
GOAL_NAME="${2:-}"
DETAILS="${3:-}"

cd /home/user/.work/athena
PYTHONPATH=/home/user/.work/athena/src python3 -m athena.cli --json manage-goal "$ACTION" ${GOAL_NAME:+--name "$GOAL_NAME"} ${DETAILS:+--details "$DETAILS"}
```

## Examples

```bash
# List all active goals
/critical:manage-goal list

# Create new goal
/critical:manage-goal create "Implement context injection" --details "Make slash commands work with real data"

# Update goal details
/critical:manage-goal update "Implement context injection" --details "Updated details here"

# Complete goal
/critical:manage-goal complete "Implement context injection"
```

## Response Format

### List Response
```json
{
  "status": "success",
  "action": "list",
  "goal_count": 3,
  "goals": [
    {
      "id": 42,
      "title": "Implement context injection",
      "status": "in_progress",
      "priority": 1
    },
    {
      "id": 43,
      "title": "Add memory search CLI",
      "status": "active",
      "priority": 2
    }
  ],
  "execution_time_ms": 20
}
```

### Create Response
```json
{
  "status": "success",
  "action": "create",
  "goal_name": "Implement context injection",
  "goal_id": 44,
  "message": "Goal created: Implement context injection (ID: 44)",
  "execution_time_ms": 15
}
```

## Actions

- **list**: List all active goals
- **create**: Create new goal
- **update**: Update goal details
- **complete**: Mark goal as complete

## Goal States

- **active**: Goal is active but not in progress
- **in_progress**: Goal is currently being worked on
- **completed**: Goal has been completed
- **blocked**: Goal is blocked by dependencies

## Priority Levels

- **1** (Urgent): Critical for project success
- **2** (High): Important, should be done soon
- **3** (Medium): Should be done when possible
- **4** (Low): Nice to have, optional

## Pattern Details

### Phase 1: Discover
- Gets existing goals from prospective_tasks table
- Counts goals by status
- Detects conflicts/dependencies
- Returns: goal_count + status_breakdown

### Phase 2: Execute
- Performs goal CRUD operation
- Updates goal status/details
- Manages dependencies
- Returns: operation_result

### Phase 3: Summarize
- Formats goal state
- Lists active goals
- Returns recommendations
- Returns structured JSON (<300 tokens)
