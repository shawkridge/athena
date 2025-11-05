---
category: skill
description: Autonomously extract and document reusable workflows from completed work
trigger: Model detects repeated patterns, or user runs /workflow or /consolidate
confidence: 0.86
---

# Workflow Learner Skill

Extracts reusable workflows from patterns and documents them for team use.

## When I Invoke This

I detect:
- Same steps repeated 2+ times
- Successful task completion with clear process
- Pattern consolidation with extractable workflow
- User explores procedural memories
- Team asks about common tasks

## What I Do

```
1. Find patterns
   → Call: find_procedures() to see existing
   → Call: recall_events() for completed tasks
   → Identify: Repeated steps
   → Identify: High-success sequences

2. Extract workflow
   → Analyze: Step sequence
   → Generalize: Abstract specific details
   → Document: Clear instructions
   → Create_procedure():
     - Name: Descriptive (e.g., "JWT Implementation")
     - Category: git, code_template, refactoring, debugging, deployment, testing
     - Template: Step-by-step
     - Trigger: When to use this

3. Test extraction
   → Validate: Workflow matches original
   → Estimate: Time and effort
   → Identify: Prerequisites
   → Document: Known issues

4. Store and link
   → Call: create_procedure()
   → Call: record_execution() for baseline
   → Link: To related memories
   → Share: Success rate metrics
```

## MCP Tools Used

- `find_procedures` - Find existing workflows
- `create_procedure` - Create new workflow
- `record_execution` - Track executions
- `recall_events` - Find completed tasks
- `smart_retrieve` - Search for patterns

## Example Invocation

```
Workflow Learner analyzing your recent work...

Detected repeated pattern: JWT token implementation
  → Task 1 (3 days ago): Success (8h)
  → Task 2 (2 days ago): Success (6h - improved!)
  → Task 3 (today): Success (5h - even better!)

Extracting workflow...

Workflow: JWT Token Implementation
Category: code_template
Success Rate: 3/3 (100%)

Steps:
1. Design decision: Signing algorithm (RS256 vs HS256)
2. Dependency: Add cryptography library
3. Implement: Token signing function
4. Test: Unit tests for signing
5. Implement: Token validation function
6. Test: Validation tests
7. Document: API documentation

Time Estimate: 4-8 hours (decreasing with practice)
Prerequisites:
  • Understand JWT basics
  • Know Express middleware
  • Familiar with testing framework

Known Issues:
  • RS256 key generation can be slow
  • Token rotation requires careful state management

Workflow created: ID: 789
Success Rate: 100% (3 executions)
Recommendation: Use this workflow for future auth implementations
```

## Success Criteria

✓ Workflow extracted from patterns
✓ Steps clearly documented
✓ Prerequisites identified
✓ Success rate tracked
✓ Reusable across similar tasks

## Related Commands

- `/workflow` - Search and execute workflows
- `/consolidate` - Extract patterns into workflows
- `/project-status` - Link to project tasks

