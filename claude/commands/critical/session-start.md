---
description: Load context at session start (filesystem API) - primes memory with active goals, health checks, discovers operations
argument-hint: Optional project name to focus on specific project
---

# Session Initialization (Filesystem API Edition)

Load and display session context using filesystem API paradigm - discover, execute locally, return summaries.

This command primes your memory at session start by:
1. **Discovering** available operations across memory layers
2. **Executing** health checks, goal status, cognitive load (all locally)
3. **Returning summaries** only (not full data)
4. **Identifying** critical gaps or blockers
5. **Recommending** optimal session focus

## How It Works

### Step 1: Discover Operations
- List available operations across all layers
- Show what's available (semantic, episodic, prospective, meta)
- Progressive disclosure - only load what's needed

### Step 2: Execute Initialization Sequence
- Health check (cross-layer operation)
- Goal status (prospective layer)
- Cognitive load (meta layer)
- Memory quality (meta layer)
- Recent critical memories (episodic layer)

All execution happens locally in sandbox - no full data in context.

### Step 3: Return Summaries
Return only summary metrics:
- Goal count, priority, progress percentages
- Memory quality score (not full data)
- Cognitive load capacity (not working memory contents)
- Gap count and types (not detailed analysis)
- Alert count by severity (not full alerts)

### Step 4: Recommend Action
Based on summaries, recommend session focus and priorities.

## Output (Summary Only)

```json
{
  "session_status": "ready",
  "execution_method": "filesystem_api",
  "execution_time_ms": 234,

  "goals": {
    "total": 12,
    "active": 8,
    "blocked": 2,
    "high_priority_count": 3,
    "completion_progress": {
      "in_progress": 5,
      "on_track": 6,
      "at_risk": 2,
      "blocked": 2
    }
  },

  "memory_health": {
    "overall_score": 0.87,
    "quality": {
      "semantic": 0.89,
      "episodic": 0.85,
      "procedural": 0.91,
      "graph": 0.83
    },
    "database_size_mb": 37,
    "database_efficiency": 0.78
  },

  "cognitive_load": {
    "current_usage": 6,
    "capacity": 9,
    "utilization_percent": 67,
    "status": "healthy"
  },

  "gaps_and_alerts": {
    "knowledge_gaps_count": 3,
    "contradictions": 1,
    "critical_alerts": 0,
    "warnings": 2
  },

  "recommendations": [
    "Consolidate episodic events (overdue, 200+ pending)",
    "Resolve 1 contradiction in authentication approach",
    "Review 2 at-risk goals (architecture redesign, performance)"
  ]
}
```

## Token Efficiency

**Old Pattern**: Load full goals, memories, metrics = 15K+ tokens
**New Pattern**: Summary metrics only = <300 tokens
**Savings**: 99%+ token reduction

## Implementation Notes

The session-initializer agent uses this by:
1. Calling this command at session start
2. Analyzing summary metrics for critical issues
3. If detail needed, calling `adapter.get_detail()` for specific IDs only
4. Setting session focus based on summaries and recommendations

This keeps session initialization efficient while providing all necessary context.
