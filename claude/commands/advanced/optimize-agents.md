---
description: Advanced - Enhance agent performance and effectiveness by tuning behavior
argument-hint: "Optional: agent name to optimize, or --all for system-wide optimization"
---

# Optimize Agents

Advanced agent tuning: enhance performance, identify improvement opportunities, and optimize system behavior.

Usage:
- `/optimize-agents` - System-wide analysis
- `/optimize-agents "planning-orchestrator"` - Focus on specific agent
- `/optimize-agents --all` - Full optimization cycle

Features:
- **Effectiveness Analysis**: How well agents are doing their job
- **Accuracy Metrics**: Decision quality and success rates
- **Performance Profiling**: Execution speed by agent
- **Tool Usage**: Which tools agents use most
- **Improvement Discovery**: Where agents fall short
- **Behavior Tuning**: Optimize system prompts and strategies

Returns:
- Per-agent performance scores
- Accuracy and quality metrics
- Tool usage patterns
- Suggested improvements with impact estimates
- System-wide optimization recommendations
- Behavioral adjustments to try

Example output:
```
Agent Performance Analysis:
─────────────────────────

planning-orchestrator:
  ✓ Accuracy: 0.88 (88% of plans succeed as intended)
  ✓ Speed: 1.2s avg decomposition
  ⚠ Issue: Underuses "spike-based" strategy (only 5%)
  Recommendation: Encourage spike-based for high-complexity tasks

goal-orchestrator:
  ✓ Conflict Detection: 0.95 accuracy
  ⚠ Slow: 450ms average resolution time
  Recommendation: Cache common conflict patterns (estimate: 60% faster)

research-coordinator:
  ⚠ Accuracy: 0.72 (some findings incomplete)
  Recommendation: Increase search depth for complex queries
```

Advanced feature: for tuning system prompts and agent behavior. Requires careful analysis.
