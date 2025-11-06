---
description: Create, activate, or complete goals with conflict detection and lifecycle tracking
argument-hint: "$1 = goal name, $2 = action (create|activate|update|complete), $3 = details"
---

# Manage Goal

Create, activate, and track goals with automatic conflict detection and lifecycle management.

Usage:
- `/manage-goal "Feature X" create` - Create new goal
- `/manage-goal "Feature X" activate` - Activate goal
- `/manage-goal "Feature X" update "80% complete"` - Update progress
- `/manage-goal "Feature X" complete` - Mark goal as done

Features:
- **Goal Hierarchy**: Organize goals with parent-child relationships
- **Conflict Detection**: Automatically detect resource/dependency conflicts
- **Conflict Resolution**: Auto-resolve conflicts based on priority weighting
- **Progress Tracking**: Record execution progress toward goal
- **Priority Ranking**: Composite scoring (40% priority + 35% deadline + 15% progress + 10% on-track)

Goal Lifecycle:
1. **Create**: Initialize goal with priority, deadline, parent goal
2. **Activate**: Set as active focus (limited to 2-3 concurrent)
3. **Update**: Track progress toward completion
4. **Complete**: Mark success/partial/failure with metrics

Returns:
- Goal ID and hierarchy
- Active goal list with priorities
- Any detected conflicts and resolutions
- Progress metrics and health score
- Milestone status

The goal-orchestrator agent autonomously manages goal lifecycle and conflict resolution.
