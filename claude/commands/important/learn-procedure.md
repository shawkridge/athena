---
description: Create reusable procedures from completed work - learns best practices and success patterns
argument-hint: "$1 = procedure name, $2 = optional description"
---

# Learn Procedure

Extract and create a reusable procedure from completed multi-step work.

Usage:
- `/learn-procedure "database-optimization"` - Extract from recent work
- `/learn-procedure "auth-flow" "JWT-based authentication with refresh tokens"`

The workflow-learner agent will:
1. **Identify** multi-step pattern from recent work
2. **Extract** key success factors and decision points
3. **Generalize** to remove task-specific details
4. **Document** with examples and edge cases
5. **Validate** effectiveness and applicability

Procedures capture:
- **Steps**: Sequential or conditional tasks
- **Inputs**: What's needed to start
- **Outputs**: Expected results
- **Decision Points**: Where choices are made
- **Success Criteria**: How to verify completion
- **Edge Cases**: Special handling for variations
- **Metrics**: Effectiveness and quality measures

Returns:
- New procedure created (stored in procedural memory)
- Applicability score (0.0-1.0, how often reusable)
- Estimated time savings when reused
- Execution history and success rate
- Recommendations for improvement
- Similar existing procedures for comparison

Example procedure:
```
Name: database-schema-migration
Applicability: 0.87 (highly reusable)
Steps:
  1. Plan: Analyze schema changes, impact assessment
  2. Backup: Create full database backup
  3. Test: Run migration on test database
  4. Deploy: Execute migration on production
  5. Verify: Run sanity checks and rollback plan

Success Rate: 95% (19 of 20 executions)
Avg Duration: 45 minutes (±10 minutes)
Recent Improvement: Added automated rollback capability
```

The system learns from both successful and failed executions to improve future recommendations.
