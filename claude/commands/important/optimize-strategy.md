---
description: Analyze and recommend optimal strategies from 9+ options based on task characteristics
argument-hint: "Optional: task description or characteristics to analyze"
---

# Optimize Strategy

Analyze task characteristics and recommend the optimal strategy from 9+ decomposition and execution options.

Usage:
- `/optimize-strategy` - Analyze current task
- `/optimize-strategy "add-api-endpoints"` - Analyze specific task

**9 Decomposition Strategies**:

1. **Hierarchical**: Top-down for well-defined, stable requirements
2. **Iterative**: Incremental refinement for evolving/uncertain requirements
3. **Spike-based**: Investigate unknowns before full planning
4. **Parallel**: Execute independent tasks concurrently
5. **Sequential**: Linear dependency chain
6. **Deadline-driven**: Work backward from hard deadline
7. **Quality-first**: Optimize for quality and comprehensive testing
8. **Collaborative**: Organize for team work with minimal handoffs
9. **Exploratory**: Investigate multiple approaches, learn as you go

The strategy-selector agent will:
1. **Analyze** task characteristics:
   - Complexity level (1-10)
   - Requirements clarity (0-100%)
   - Timeline urgency (days until deadline)
   - Team size and availability
   - Quality requirements
   - Dependencies and risks

2. **Score** each strategy (0.0-1.0)
3. **Recommend** top 3 with reasoning
4. **Provide** implementation guidance

Returns:
- Top recommended strategy with score
- Alternative strategies ranked by suitability
- Analysis of task characteristics
- Strategy-specific tips and best practices
- Estimated time savings vs. baseline
- Risk mitigation for chosen strategy

Example output:
```
Task: "Implement OAuth2 authentication system"
Characteristics:
  - Complexity: 8/10 (moderate-high)
  - Requirements Clarity: 85% (mostly clear)
  - Timeline: 2 weeks (moderate pressure)
  - Team: 2 developers (small)
  - Quality: High (security-critical)

Recommended: Spike-based Decomposition (Score: 0.92)
  Reasoning: High complexity with some unknowns; spike reduces risk
  Steps:
    1. Spike 1: Research OAuth2 flows and library options (1 day)
    2. Spike 2: Prototype with leading library (1-2 days)
    3. Plan: Full design based on spike learnings
    4. Execute: Implementation using proven approach

Alternatives:
  2. Iterative (0.88): If requirements may change
  3. Quality-first (0.85): If time permits
```

The strategy-selector agent autonomously analyzes complex tasks before `/plan-task` execution.
