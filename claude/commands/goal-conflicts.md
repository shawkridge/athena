# goal-conflicts

Check for conflicts between active goals (resource contention, dependency issues, etc).

## Usage

```bash
/goal-conflicts
/goal-conflicts --project-id 1
/goal-conflicts --detailed
```

## Description

Analyzes the current set of goals for conflicts including:
- Resource contention (both need same person/tool)
- Dependency cycles (A depends on B, B depends on A)
- Timing conflicts (overlapping deadlines)
- Priority conflicts (high priority goals block each other)

Internally calls the `check_goal_conflicts` MCP tool from Phase 3 Executive Functions.

## Options

- `--project-id` (optional) - Project ID to check (default: current project)
- `--detailed` (optional) - Show detailed conflict analysis
- `--resolve` (optional) - Auto-resolve conflicts immediately

## Output

- Total conflict count
- Conflict types (resource_contention, dependency_cycle, timing_conflict, priority_conflict)
- Affected goals
- Severity scores
- Recommendations

## Example

```
> /goal-conflicts --detailed
⚠️  Conflicts Detected: 2

Conflict #1: RESOURCE_CONTENTION (Severity: HIGH)
  Goal #1: "Frontend implementation" (person: alice)
  Goal #3: "Bug fixing" (person: alice)
  Issue: Both require alice for 40 hours next week
  Recommendation: Move Goal #3 to following week or assign to bob

Conflict #2: DEPENDENCY_CYCLE (Severity: MEDIUM)
  Goal #4: "API design" depends on Goal #5: "Database schema"
  Goal #5: "Database schema" depends on Goal #4: "API design"
  Recommendation: Break cycle - start with database schema design
```

## Related Commands

- `/activate-goal` - Activate a goal (check conflicts first!)
- `/resolve-conflicts` - Auto-resolve detected conflicts
- `/priorities` - View goal priorities
- `/workflow-status` - See all goals and their state

## See Also

- Memory MCP Phase 3: Executive Functions
