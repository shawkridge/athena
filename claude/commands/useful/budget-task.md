---
description: Estimate task costs and resource requirements - budget tracking and optimization
argument-hint: "Task description or task ID to budget"
---

# Budget Task

Estimate costs and resource requirements for tasks with budget tracking and cost optimization.

Usage:
- `/budget-task "add-oauth-authentication"`
- `/budget-task <task_id>` - Budget existing task

Cost Categories:
- **Developer Time**: Estimated hours × hourly rate
- **Cloud Resources**: Compute, storage, bandwidth
- **Third-party APIs**: Service costs
- **Infrastructure**: Servers, databases
- **Testing**: QA time and tools
- **Deployment**: Ops time and tools

Returns:
- Total cost estimate with confidence interval
- Cost breakdown by category
- Resource allocation requirements
- Budget anomaly detection
- Cost optimization recommendations
- Historical comparison (similar tasks)
- Time/cost tradeoff analysis

Features:
- **Budget Tracking**: Monitor actual vs. estimated
- **Anomaly Detection**: Alert on 20%+ overruns
- **Optimization**: Suggest ways to reduce costs
- **Resource Conflicts**: Detect over-allocation
- **ROI Analysis**: Benefit vs. cost

Example output:
```
Task: "Add OAuth2 Authentication"
Total Estimated Cost: $8,500 (±$2,000)

Breakdown:
  - Developer Time: $6,000 (80 hours @ $75/hr)
  - Cloud Resources: $1,500 (additional API quota)
  - Testing & QA: $1,000 (external security audit)

Optimization Opportunities:
  - Use existing library (save 20 hours = $1,500)
  - Reduce scope to core auth (save 15 hours = $1,125)
  - Partner with vendor for testing (save $500)

Potential Savings: Up to $3,125 (37%)
```

The resource-optimizer agent uses this for project budget management.
