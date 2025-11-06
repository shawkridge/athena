---
description: Break down complex task into executable steps using one of 9 decomposition strategies
argument-hint: "Task description to decompose"
---

# Plan Task

Decompose a complex task into executable steps using one of 9 available strategies.

Usage: `/plan-task "task description"`

The planning-orchestrator agent will:
1. **Analyze** your task characteristics (complexity, deadline, resources)
2. **Select** optimal strategy from 9 options
3. **Decompose** into structured steps with dependencies
4. **Estimate** time and resources for each step
5. **Validate** for feasibility and conflicts

Available Strategies:
- **Hierarchical**: Top-down decomposition for well-defined tasks
- **Iterative**: Incremental refinement for evolving requirements
- **Spike-based**: Investigate unknowns first, then plan
- **Parallel**: Execute independent tasks concurrently
- **Sequential**: Linear dependency chain
- **Deadline-driven**: Work backward from deadline
- **Quality-first**: Optimize for quality and testing
- **Collaborative**: Organize for team work
- **Exploratory**: Investigate multiple approaches

Returns:
- Structured execution plan with steps and dependencies
- Time estimates per step (with confidence intervals)
- Resource requirements
- Critical path and bottlenecks
- Risk assessments
- Recommended strategy reasoning

Output can be used with `/validate-plan` for comprehensive verification.
