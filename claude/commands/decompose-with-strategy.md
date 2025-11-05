# decompose-with-strategy

Decompose complex task using goal-aware strategy selection (Sequential Thinking).

## Usage

```bash
/decompose-with-strategy --task "Implement user authentication" --strategy top_down
/decompose-with-strategy --task "..." --goal-id 1
/decompose-with-strategy --task "..." --auto-select
```

## Description

Uses Phase 3 Executive Function tools to decompose a task with **transparent reasoning** across 9 strategies:

1. **HIERARCHICAL** (TOP_DOWN) - Architectural planning
2. **ITERATIVE** (BOTTOM_UP) - MVP-first approach
3. **SPIKE** (SPIKE) - Research/prototype dominant
4. **PARALLEL** (PARALLEL) - Maximize concurrent work
5. **SEQUENTIAL** (SEQUENTIAL) - Strict linear ordering
6. **DEADLINE_DRIVEN** (DEADLINE_DRIVEN) - Risk minimization
7. **QUALITY_FIRST** (QUALITY_FIRST) - Extra review phases
8. **COLLABORATIVE** (COLLABORATION) - Team coordination
9. **EXPLORATORY** (EXPERIMENTAL) - Multiple approaches

Implements Sequential Thinking from Thinking MCP research - shows explicit reasoning about decomposition approach.

Internally calls the `decompose_with_strategy` MCP tool from Phase 3 Executive Functions.

## Options

- `--task` (required) - Task description or title
- `--strategy` (optional) - Specific strategy to use (see list above)
- `--goal-id` (optional) - Goal context for decomposition
- `--auto-select` (optional) - Let AI pick best strategy
- `--show-alternatives` (optional) - Show plans for all 9 strategies
- `--reasoning` (optional) - Show transparent thinking process

## Output

- Execution plan with sequential steps
- Decomposition strategy used
- Strategy reasoning and justification
- Alternative strategies considered
- Risk assessment for strategy
- Dependency graph

## Example

```
> /decompose-with-strategy --task "Implement user authentication" --reasoning
🎯 Task Decomposition with Strategy Selection

Task: "Implement user authentication"
Strategy Selected: HIERARCHICAL (TOP_DOWN)
Confidence: 8.7/10

Thinking Process:
  ├─ Complexity: HIGH (multiple OAuth providers, session mgmt)
  ├─ Risk: MEDIUM (security-critical, external dependencies)
  ├─ Timeline: 7 days
  └─ Decision: TOP_DOWN recommended (clear architecture needed)

Generated Execution Plan:
──────────────────────────
Phase 1: Architecture (1 day)
  ├─ Step 1: Design auth flow diagram
  ├─ Step 2: Select OAuth providers
  ├─ Step 3: Define user session schema
  └─ Step 4: Document security requirements
     Milestone: "Auth Architecture Approved"

Phase 2: Core Implementation (3 days)
  ├─ Step 5: Setup OAuth client
  ├─ Step 6: Implement login endpoint
  ├─ Step 7: Implement session management
  ├─ Step 8: Implement logout
  └─ Step 9: Add token refresh logic
     Milestone: "Basic Auth Functional"

Phase 3: Quality & Integration (2 days)
  ├─ Step 10: Write unit tests (auth logic)
  ├─ Step 11: Write integration tests
  ├─ Step 12: Security review
  ├─ Step 13: Documentation
  └─ Step 14: Staging deployment
     Milestone: "Auth Ready for Production"

Phase 4: Monitoring (1 day)
  ├─ Step 15: Setup monitoring
  ├─ Step 16: Create runbook
  └─ Step 17: Team training
     Milestone: "Auth Live"

Alternative Strategies:
  🥈 ITERATIVE (Score: 7.1/10)
     - Faster to MVP (day 2)
     - Higher refactoring risk
     - Better for unclear requirements

  🥉 SPIKE (Score: 4.3/10)
     - Research dominant
     - Not ideal (requirements clear)
```

## Related Commands

- `/activate-goal` - Activate goal for this task
- `/plan-validate` - Validate the plan
- `/progress` - Track execution
- `/priorities` - See this task's priority

## See Also

- Memory MCP Phase 3: Executive Functions
- Thinking MCP Sequential Thinking pattern
