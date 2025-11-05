# next-goal

Get AI recommendation for next goal to focus on.

## Usage

```bash
/next-goal
/next-goal --project-id 1
/next-goal --strategy context-switching
/next-goal --consider-load
```

## Description

Analyzes current goals and provides AI-powered recommendation for the next goal to activate, considering:
- Priority scores and deadlines
- Current cognitive load
- Context switching costs
- Goal dependencies
- Risk of missing deadlines
- Team availability

Internally calls the `recommend_next_goal` MCP tool from Phase 3 Executive Functions.

## Options

- `--project-id` (optional) - Project to analyze (default: current)
- `--strategy` (optional) - Recommendation strategy: priority, balanced, risk-min, deadline
- `--consider-load` (optional) - Factor in cognitive load
- `--exclude-goals` (optional) - Ignore specific goals
- `--reasoning` (optional) - Show full reasoning

## Output

- Recommended goal
- Reasoning/justification
- Priority score
- Estimated impact
- Alternative suggestions
- Risks if not done

## Example

```
> /next-goal --reasoning
🎯 AI Recommendation: Next Goal to Focus On

Recommended: Goal #2 "Fix critical API bug"
Confidence: 9.2/10
Priority Score: 9.1/10

Reasoning:
  ├─ CRITICAL: Bug affects 15% of users (P0 severity)
  ├─ DEADLINE: 2 days until customer escalation (HIGH URGENCY)
  ├─ RISK: Missing deadline → $10k revenue impact
  ├─ DEPENDENCIES: Unblocks Goal #4 "API optimization"
  ├─ CONTEXT: Low switching cost from current (Goal #1 paused)
  └─ LOAD: Within cognitive load limits (45% utilized)

Alternatives (if not available):
  2. Goal #4 "API optimization" (Score: 7.2/10)
     - Lower priority but related to bug fix
     - Could be done in parallel with Goal #2

  3. Goal #5 "Documentation" (Score: 4.1/10)
     - Lower priority, can wait

Risk Analysis:
  If you skip Goal #2:
  ⚠️  Customer escalation likely (2 days)
  ⚠️  Revenue impact: ~$10k
  ⚠️  Timeline delay: +5 days for rework
  ✓ Goal #4 stays blocked

Recommendation Confidence: 92% (high)
```

## Related Commands

- `/activate-goal` - Activate the recommended goal
- `/priorities` - See all goal rankings
- `/progress` - Track the goal once started
- `/workflow-status` - View all active goals

## See Also

- Memory MCP Phase 3: Executive Functions
