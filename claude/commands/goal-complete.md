# goal-complete

Mark a goal as completed with outcome and metrics.

## Usage

```bash
/goal-complete --goal-id 1 --outcome success
/goal-complete --goal-id 1 --outcome partial --notes "80% done, rest deferred"
/goal-complete --goal-id 1 --outcome failure --notes "Resource unavailable"
```

## Description

Records goal completion with:
- Final outcome (success, partial, failure)
- Execution metrics (time taken, errors, blockers)
- Lessons learned
- Impact on dependent goals
- Outcome feedback for strategy learning

Internally calls the `complete_goal` MCP tool from Phase 3 Executive Functions.

## Options

- `--goal-id` (required) - Goal to complete
- `--outcome` (required) - success, partial, or failure
- `--notes` (optional) - Completion notes/summary
- `--lessons` (optional) - Key lessons learned
- `--record-feedback` (optional) - Provide strategy feedback

## Output

- Completion confirmation
- Total execution time
- Final metrics (errors, blockers, progress)
- Outcome recorded
- Dependent goals affected
- Strategy effectiveness feedback

## Example

```
> /goal-complete --goal-id 1 --outcome success --notes "Completed ahead of schedule"
✓ Goal Completed: "Implement user auth"

Outcome: SUCCESS
├─ Completion Time: 4 days (planned 7 days) ⚡ 43% faster
├─ Final Progress: 100% (all 10 steps)
├─ Errors Encountered: 1 (none blocking)
├─ Blockers: 0
└─ Final Health: 0.95 (EXCELLENT)

Execution Summary:
  Started: Oct 20, 10:00 AM
  Completed: Oct 24, 3:30 PM
  Actual Duration: 4 days
  Efficiency: 143% of baseline

Impact on Dependent Goals:
  ✓ Goal #4 "API development" can now start (unblocked)
  ✓ Critical path reduced by 3 days

Strategy Learning:
  Strategy Used: TOP_DOWN decomposition
  Effectiveness: EXCELLENT (faster than planned)
  Recommendation: Use TOP_DOWN for similar features

Milestone Achievements:
  ✓ Authentication module complete
  ✓ OAuth provider integration done
  ✓ User session management tested
```

## Related Commands

- `/activate-goal` - Activate next goal
- `/progress` - Track progress before completion
- `/next-goal` - Get recommendation for next focus
- `/priorities` - See remaining goals

## See Also

- Memory MCP Phase 3: Executive Functions
