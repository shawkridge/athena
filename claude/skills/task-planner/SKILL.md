---
category: skill
description: Autonomously decompose complex tasks and validate plans against project timeline
trigger: Model detects complex work or planning needed, or user runs /task-create or /plan-validate
confidence: 0.89
---

# Task Planner Skill

Automatically breaks down complex work into manageable 30-min chunks and validates against project plans.

## When I Invoke This

I detect:
- Complex task (multi-step, unclear scope)
- User creates task with ambiguous description
- Plan validation requested
- Work spans multiple phases or days
- Dependencies between tasks

## What I Do

```
1. Analyze work
   → Complexity: 1-10 scale
   → Scope: Identify sub-tasks
   → Dependencies: Map relationships
   → Effort: Estimate hours

2. Decompose hierarchically
   → Call: decompose_hierarchically()
   → Create 30-min chunks (optimal cognitive load)
   → Group related subtasks
   → Identify critical path
   → Flag high-risk areas

3. Validate plan
   → Call: validate_plan()
   → Check: Structural integrity (dependencies, ordering)
   → Check: Feasibility (timeline, resources)
   → Check: Rule compliance (standards, gates)

4. Suggest strategy
   → Call: suggest_planning_strategy()
   → Recommend: Parallel vs sequential work
   → Recommend: Risk mitigation
   → Recommend: Resource allocation

5. Create tasks
   → Call: create_task() for each subtask
   → Link to parent goal
   → Set triggers and deadlines
   → Assign to team/self
```

## MCP Tools Used

- `decompose_hierarchically` - Break down tasks
- `validate_plan` - 3-level validation
- `suggest_planning_strategy` - Strategy recommendation
- `create_task` - Create subtasks
- `set_goal` - Link to goals
- `record_execution` - Track planning

## Example Invocation

```
You: /task-create "Implement authentication system"

Task Planner analyzing complexity...
→ Complexity: 9/10 (high)
→ Estimated effort: 40h
→ Recommended chunks: 30-min tasks

Decomposing into phases...
Phase 1: Design (8h)
  ├─ Design document (2h)
  ├─ Security review (2h)
  ├─ Database schema (2h)
  └─ API contract (2h)

Phase 2: Implementation (24h)
  ├─ JWT signing (4h)
  ├─ Token validation (4h)
  ├─ Refresh logic (4h)
  ├─ Error handling (4h)
  ├─ Middleware (4h)
  └─ Utils (4h)

Phase 3: Testing (8h)
  ├─ Unit tests (3h)
  ├─ Integration tests (3h)
  └─ Performance (2h)

Validating plan...
✓ Timeline: 40h / 8h per day = 5 days (realistic)
✓ Dependencies: Ordered correctly
⚠ Risk: Database migration untested
  → Recommendation: Add pre-prod validation (1h)

Tasks created: 15 subtasks, all linked to parent
Status: Ready to work
```

## Success Criteria

✓ Complex tasks decomposed to 30-min chunks
✓ Plan validates successfully
✓ All subtasks created and linked
✓ Effort estimates reasonable
✓ Dependencies clear

## Related Commands

- `/task-create` - Create tasks
- `/plan-validate` - Validate plans
- `/project-status` - See plan in context

