---
description: Load context at session start - primes memory with active goals, project status, and memory quality
argument-hint: Optional project name to focus on specific project
---

# Session Initialization

Load and display session context including project status, memory health, active goals, and cognitive load.

This command primes your memory at session start by:
1. Loading top-priority active goals and their status
2. Checking overall memory quality and identifying gaps
3. Displaying current cognitive load and working memory status
4. Surfacing recent critical memories and patterns
5. Checking for goal conflicts or blockers

Output includes:
- Active goal hierarchy with progress
- Memory quality score (target: ≥0.85)
- Cognitive load (7±2 items, current usage)
- Any knowledge gaps or contradictions
- Critical alerts or blockers
- Recommendations for session focus

The session-initializer agent will autonomously invoke this to prime your context.
