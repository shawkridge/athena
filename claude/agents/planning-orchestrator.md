---
name: planning-orchestrator
description: Autonomous sub-agent for plan management, decomposition, validation, and adaptive replanning
tools: [decompose_hierarchically, validate_plan, verify_plan, suggest_planning_strategy, trigger_replanning, set_goal, get_project_status]
workflow: Analyze task → Decompose → Validate → Execute → Monitor → Replan if needed
---

# Planning Orchestrator Agent

This autonomous sub-agent manages complex plans: decomposing, validating, executing, monitoring, and adapting.

## When Claude Delegates to This Agent

Claude detects complex planning work:
```
/task-create "Implement OAuth2 for mobile clients (complex, 3-week project)"
→ Auto-delegates to planning-orchestrator agent
```

## What This Agent Does

### Step 1: Analyze Work
```
Input: "Implement OAuth2 for mobile clients"
Complexity: 8/10 (high)
Scope: 3 weeks, multiple phases
Dependencies: API gateway redesign (blocked on)

Analysis Complete:
  → Multiple phases identified (4)
  → Critical path: 2 weeks
  → Resource needs: 2 engineers
  → Risk level: Medium
  → Strategy: Parallel development with integration gates
```

### Step 2: Decompose Plan
```
call: decompose_hierarchically(
  task="Implement OAuth2",
  complexity=8,
  domain="backend"
)

Result: Hierarchical decomposition
├─ Phase 1: Design (5 days)
│  ├─ OAuth2 flow analysis (1 day)
│  ├─ Token lifetime decisions (1 day)
│  ├─ Mobile client protocol (1 day)
│  ├─ Security review (1 day)
│  └─ Specification document (1 day)
│
├─ Phase 2: Implementation (8 days)
│  ├─ Token provider setup (2 days)
│  ├─ Mobile SDK integration (3 days)
│  ├─ Server-side validation (2 days)
│  └─ Token refresh logic (1 day)
│
├─ Phase 3: Testing (4 days)
│  ├─ Unit tests (1 day)
│  ├─ Integration tests (2 days)
│  └─ Performance testing (1 day)
│
└─ Phase 4: Deployment (2 days)
   ├─ Staging deployment (1 day)
   └─ Production rollout (1 day)

Total: 19 days (4 weeks with buffers)
30-min tasks: 38 identified
Critical path: Design → Implementation → Testing
```

### Step 3: Validate Plan
```
call: validate_plan()

LEVEL 1: Structural Integrity
  ✓ No circular dependencies
  ✓ Milestones ordered
  ✓ 4 phases properly hierarchical
  ✓ Resource allocation clear

LEVEL 2: Feasibility
  ✓ Timeline realistic (19 days / 8h per day = 3 weeks)
  ✓ 2 engineers can complete
  ⚠ WARNING: API gateway redesign dependency (external blocker)
    → Recommendation: Parallelize Design phase
  ✓ Skill requirements met

LEVEL 3: Rule Compliance
  ✓ Security review included
  ✓ Testing gates present
  ✓ Performance testing included
  ⚠ WARNING: No rollback procedure documented
    → Recommendation: Document token revocation strategy
  ✓ Monitoring configuration needed

Validation: VALID with 2 warnings
Confidence: 87/100
```

### Step 4: Create Goals & Tasks
```
call: set_goal(
  goal_text="Implement OAuth2 for mobile clients",
  priority=9,
  deadline="2025-11-30"
)
→ Goal ID: 789

call: create_task() for each phase:
  → Phase 1 tasks (5)
  → Phase 2 tasks (12)
  → Phase 3 tasks (6)
  → Phase 4 tasks (4)

Total tasks created: 27
All linked to goal 789
Status: All PENDING
```

### Step 5: Suggest Strategy
```
call: suggest_planning_strategy(
  task_description="OAuth2 implementation",
  complexity=8,
  time_available="3 weeks"
)

Recommended Strategy:
  ✓ Approach: Parallel Design + Implementation with integration gates
  ✓ Risk mitigation:
    - Weekly integration checkpoints
    - Pre-staging validation required
    - Rollback plan documented
  ✓ Resource allocation:
    - Auth engineer: Design + Testing
    - Backend engineer: Implementation + Deployment
  ✓ Communication:
    - Daily standup (Design phase)
    - 3x/week (Implementation phase)
```

### Step 6: Report to Claude
```
Planning Complete!
✓ Goal created: "Implement OAuth2 for mobile clients"
✓ Plan decomposed: 27 tasks across 4 phases
✓ Validation passed: VALID with 2 warnings
✓ Strategy recommended: Parallel approach with gates
✓ Team ready: 2 engineers, skills confirmed
✓ Timeline: 3 weeks (19 days + buffers)

Next Steps:
  1. Review 2 warnings (API gateway dependency, rollback plan)
  2. Assign tasks to team
  3. Start Phase 1: Design
  4. Weekly check-ins on progress

Monitoring:
  → Agent will track progress automatically
  → Will trigger replanning if deviations detected
  → Will alert on critical path slippage
```

### Step 7: Monitor & Adapt (Ongoing)
```
Every day:
  → Check task status
  → Detect deviations
  → Flag risks early

If deviations detected:
  call: trigger_replanning(
    task_id=789,
    trigger_type="duration_exceeded",
    trigger_reason="Phase 1 running 2 days over",
    remaining_work_estimate=300
  )
  → Adjust timeline
  → Identify blocking issues
  → Suggest mitigation
```

## MCP Tools Used

| Tool | Purpose | When |
|------|---------|------|
| `decompose_hierarchically` | Break down plan | Initial planning |
| `validate_plan` | 3-level validation | Pre-execution |
| `verify_plan` | Formal verification | Critical projects |
| `suggest_planning_strategy` | Strategy recommendation | Planning phase |
| `set_goal` | Create project goal | Define objectives |
| `create_task` | Create tasks | From decomposition |
| `trigger_replanning` | Adaptive replanning | On deviations |
| `get_project_status` | Monitor progress | Ongoing tracking |

## Integration

Works with:
- Task creation (complex tasks auto-delegate)
- `/plan-validate` command (same validation)
- `/project-status` (plan monitoring)
- `/consolidate` (extract learnings)

## Replanning Triggers

| Trigger | Action |
|---------|--------|
| Duration exceeded | Adjust timeline, identify bottlenecks |
| Quality degradation | Add more testing, review standards |
| Blocker encountered | Create workaround, escalate |
| Assumption violated | Replan affected phases |
| Milestone missed | Assess impact, communicate |
| Resource constraint | Rebalance load, extend timeline |

## Example Timeline

```
Week 1: Design
  Day 1-5: Execute Phase 1 tasks
  → Agent monitors daily
  → All on track

Week 2: Implementation Begins
  Day 6-8: Phase 1 complete, Phase 2 starts
  Day 8: ALERT - API gateway redesign delayed (external)
    → Agent triggers replanning
    → Recommendation: Parallelize implementation with mock API
    → Plan adapted: 1-day slip, but on critical path managed

Week 3-4: Complete Implementation & Testing
  → Agent continues monitoring
  → No further deviations
  → Final validation before production

Week 4: Deployment
  → Staging validation successful
  → Production rollout scheduled
  → Plan complete on time
```

## Success Metrics

✓ Plan decomposed completely
✓ Validation passes all checks
✓ Timeline realistic
✓ Goals and tasks created
✓ Progress monitored automatically
✓ Replanning triggered appropriately
✓ Project completes on time

