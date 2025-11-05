# /activate-goal

Activate a goal and switch workflow context with comprehensive cost analysis.

## Usage

```bash
/activate-goal --goal-id 1                    # Activate goal
/activate-goal --goal-id 1 --project-id 1    # Specific project
/activate-goal --goal-id 1 --analyze-cost    # Detailed cost analysis
/activate-goal --goal-id 1 --force            # Override conflicts
```

## Description

Switches the active goal context and analyzes the context switching cost using Phase 3 Executive Functions.

**Context Switching Cost Analysis**:
- Working memory transition time
- Context loss penalty (how much knowledge disappears)
- Resume time for previous goal
- Attention reset (cold start for new goal)
- Task reordering impact

**Internally calls**:
- `task_management_tools:activate_goal` - Activate goal
- `task_management_tools:get_active_goals` - Load active goals
- `coordination_tools:detect_resource_conflicts` - Check for conflicts
- `ml_integration_tools:compute_memory_saliency` - Calculate salience

## Options

- `--goal-id` (required) - Goal ID to activate
- `--project-id` (optional) - Project ID (default: 1)
- `--analyze-cost` (optional) - Show detailed context switching cost
- `--force` (optional) - Override conflicts (not recommended)
- `--dry-run` (optional) - Preview without activating

## Output

- ✓ Confirmation of goal activation
- Goal name, priority, and progress
- Switch cost breakdown:
  - Context loss estimate (minutes)
  - Attention reset time
  - Previous goal resume recommendation
- Conflict analysis (if any)
- Next recommended step

## Example Output

```
> /activate-goal --goal-id 5 --analyze-cost

✓ Goal activated: "Implement user authentication" (Goal #5)

Status:
  Priority: HIGH (8.5/10)
  Progress: 0% (new)
  Deadline: 3 days
  Status: READY TO START

Context Switch Cost Analysis:
  ├─ Working memory transition: 2 min
  ├─ Context loss from Goal #3: 3 min
  ├─ Cold start activation: 1 min
  ├─ Attention reset: 1 min
  └─ Total: 7 minutes

Previous Goal (Goal #3: "API documentation"):
  Progress: 75% (7/10 steps)
  Status: ON TRACK
  Recommendation: Keep notes open for 30 min reference
  Resume time: ~5 min to get back up to speed

Conflicts:
  ⚠️ WARNING: Alice assigned to both Goal #5 and Goal #2
  Recommendation: Use /resolve-conflicts before proceeding

Next Step:
  1. Review Goal #5 requirements (pre-work)
  2. Prepare development environment (5 min)
  3. Start implementation (auth service setup)
  4. Use /progress to track completion
```

## Integration with Phase 3 Executive Functions

This command integrates:

**Goal Activation**:
- Load goal from database with full context
- Update active goal state
- Record activation timestamp
- Update working memory

**Context Cost Analysis**:
- Calculate memory transition penalty
- Estimate context loss (how much knowledge is lost)
- Predict resume time for previous goal
- Assess cold-start penalty for new goal

**Conflict Detection**:
- Check resource conflicts with other active goals
- Check dependency violations
- Warn if conflicting assignments

**Recommendation Engine**:
- Suggest order for goal activation
- Recommend prep work
- Estimate ramp-up time

## Related Commands

- `/goal-conflicts` - Check conflicts before activating
- `/priorities` - See priority ranking before selecting
- `/progress` - Track progress for current goal
- `/resolve-conflicts` - Fix conflicts blocking activation
- `/workflow-status` - View all active goals
- `/next-goal` - Get AI recommendation for next goal

## Tips

1. **Check conflicts first**: Run `/goal-conflicts` before activating high-impact goals
2. **Review priorities**: Use `/priorities` to understand goal ranking
3. **Analyze switching cost**: Especially important for complex goals
4. **Keep context open**: The command suggests keeping previous goal notes available
5. **Document activation**: Use timestamp to track when you switched focus

## Phase 3 Integration

This command is part of Phase 3 Executive Function tools:
- Goal activation with context cost analysis
- Composite priority scoring
- Conflict detection and resolution
- Workflow state management
- Milestone tracking

## Related Tools

- `task_management_tools:activate_goal` - Core activation
- `task_management_tools:get_active_goals` - Load current state
- `coordination_tools:detect_resource_conflicts` - Conflict detection
- `ml_integration_tools:compute_memory_saliency` - Salience calculation

## See Also

- `/project-status` - View all goals in project
- `/decompose-with-strategy` - Break down goal into tasks
- `/plan-validate-advanced` - Validate goal's plan (Phase 6)
- `/memory-health` - Check memory system health
