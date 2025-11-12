---
name: session-initializer
description: |
  Session initialization using filesystem API paradigm (load → check → assess → prime).
  Context priming at session startup: loads goals, checks health, assesses load.
  Executes locally, returns summaries only (99%+ token reduction).
---

# Session Initializer Agent (Filesystem API Edition)

Session startup with rapid context priming and cognitive load assessment (<500ms target).

## What This Agent Does

Initializes new sessions by parallel loading of active goals, memory quality checks, cognitive load assessment, and working memory priming, all with summarized findings returned instantly.

## When to Use

- Session startup (auto-invoked)
- Context recovery after interruption
- Beginning new task or project
- Cognitive load reset
- Goal priority reassessment

## How It Works (Filesystem API Paradigm)

### Step 1: Discover & Load
- Use `adapter.list_operations_in_layer()` for all layers
- Discover available initialization operations
- Prepare parallel load parameters

### Step 2: Execute in Parallel
- Load active goals: `adapter.execute_operation("task_management", "get_active_goals")`
- Check memory health: `adapter.execute_operation("meta", "check_health")`
- Assess cognitive load: `adapter.execute_operation("meta", "get_cognitive_load")`
- Get recent memories: `adapter.execute_operation("episodic", "get_recent")`
- All 4 operations execute concurrently in sandbox (~300-400ms)

### Step 3: Assess & Prime
- Aggregate findings from parallel operations
- Identify conflicts and blockers
- Assess current cognitive load
- Determine prime focus areas

### Step 4: Return Summary
- Session overview with key metrics
- Goal priorities ranked
- Urgent alerts and blockers
- Memory health snapshot
- Cognitive load baseline
- Recommended session focus

## Parallel Load Operations

1. **Goal Loading**: Active goals with priorities and deadlines
2. **Health Check**: Memory quality, coverage, contradictions
3. **Load Assessment**: Current cognitive load vs capacity
4. **Recent Context**: Recent memories and events
5. **Conflict Check**: Goal conflicts and blockers

## Returns (Summary Only)

```json
{
  "status": "success",
  "execution_method": "filesystem_api_parallel",
  "execution_time_ms": 387,

  "session_summary": {
    "timestamp": "2025-11-12T10:15:30Z",
    "user": "user@example.com",
    "project": "athena",
    "readiness": "ready_to_work"
  },

  "parallel_load": {
    "goals": {"status": "success", "duration_ms": 89, "count": 5},
    "memory_health": {"status": "success", "duration_ms": 112, "score": 0.82},
    "cognitive_load": {"status": "success", "duration_ms": 76, "load_level": 3},
    "recent_context": {"status": "success", "duration_ms": 110, "events": 8}
  },

  "active_goals": [
    {
      "id": 1,
      "name": "Complete Phase 3 Skills Update",
      "priority": "high",
      "deadline": "2025-11-15",
      "progress": 0.67,
      "status": "in_progress",
      "blockers": []
    },
    {
      "id": 2,
      "name": "Update Agents with Filesystem API",
      "priority": "high",
      "deadline": "2025-11-15",
      "progress": 0.40,
      "status": "in_progress",
      "blockers": []
    },
    {
      "id": 3,
      "name": "Run Tests and Validate",
      "priority": "medium",
      "deadline": "2025-11-16",
      "progress": 0.25,
      "status": "blocked",
      "blockers": ["Tests still running"]
    }
  ],

  "memory_health": {
    "overall_score": 0.82,
    "status": "healthy",
    "compression_ratio": 0.78,
    "recall_score": 0.84,
    "consistency_score": 0.79,
    "coverage_score": 0.87
  },

  "cognitive_load": {
    "current_level": 3,
    "capacity": 7,
    "utilization_percent": 43,
    "headroom": 4,
    "status": "comfortable"
  },

  "working_memory_priming": {
    "loaded_items": 5,
    "recent_events": 3,
    "active_goals": 3,
    "critical_memories": 2
  },

  "alerts_and_blockers": [
    {
      "type": "blocker",
      "severity": "medium",
      "message": "Tests in Phase 3 still running - blocking validation",
      "recommendation": "Wait for tests to complete"
    },
    {
      "type": "goal_conflict",
      "severity": "low",
      "message": "Agent update overlaps with skills update",
      "recommendation": "Parallelize both updates"
    }
  ],

  "knowledge_gaps": [
    {
      "domain": "test_coverage",
      "gap": "MCP server test coverage low",
      "severity": "medium",
      "affected_goals": 1
    }
  ],

  "recommended_focus": [
    {
      "focus_area": "Complete Phase 3 Skills and Agents",
      "priority": "high",
      "estimated_time_minutes": 90,
      "resources_needed": ["Documentation", "Example files"]
    },
    {
      "focus_area": "Verify test results",
      "priority": "medium",
      "estimated_time_minutes": 15,
      "resources_needed": ["Test runner"]
    }
  ],

  "session_recommendations": [
    "Continue Phase 3 updates - on track for deadline",
    "Cognitive load comfortable (43% utilization) - good capacity for parallel work",
    "Memory health good (0.82 score) - continue current practices",
    "Watch for blocker: Test completion needed before validation phase",
    "Consider parallelizing remaining agent updates"
  ],

  "next_actions": [
    "Continue with remaining 2 agent updates",
    "Monitor test completion",
    "Prepare validation tests",
    "Create commit for Phase 3 work"
  ],

  "note": "Call adapter.get_detail('session', 'goal', 1) for full goal details"
}
```

## Session Priming Pattern

### Parallel Initialization Flow
```
┌─────────────────┐
│ Session Start   │
└────────┬────────┘
         │
┌────────▼─────────────────┐
│ Discover Operations      │
└────────┬─────────────────┘
         │
┌────────▼──────────────────────────────────┐
│ Parallel Load Operations                  │
├──────────┬─────────────┬────────┬─────────┤
│  Goals   │Memory Health│ Load   │Recent   │
│ (89ms)   │ (112ms)     │(76ms)  │(110ms)  │
│ Goals:5  │ Score:0.82  │Load:3  │Events:8 │
├──────────┴─────────────┴────────┴─────────┤
│ Parallel: 5 ops total (slow operation)  │
│ Slowest: Memory Health Check (112ms)    │
└────────┬──────────────────────────────────┘
         │
┌────────▼──────────────────┐
│ Assess & Analyze          │
│ - Conflicts               │
│ - Blockers                │
│ - Capacity                │
└────────┬──────────────────┘
         │
┌────────▼──────────────────┐
│ Prime & Return Summary    │
│ <500ms total target       │
└───────────────────────────┘
```

## Token Efficiency
Old: 120K+ tokens | New: <400 tokens | **Savings: 99%**

## Examples

### Basic Session Initialization

```python
# Initialize session (auto-invoked at startup)
result = adapter.execute_operation(
    "session",
    "initialize",
    {"project": "athena"}
)

# Check readiness
print(f"Status: {result['session_summary']['readiness']}")
print(f"Cognitive Load: {result['cognitive_load']['current_level']}/7")

# Review top priorities
for goal in result['active_goals'][:3]:
    print(f"{goal['priority']}: {goal['name']} ({goal['progress']:.0%})")
```

### Blocker Assessment

```python
# Check for blockers before starting work
result = adapter.execute_operation(
    "session",
    "initialize",
    {"include_blockers": True}
)

blockers = [a for a in result['alerts_and_blockers'] if a['type'] == 'blocker']
if blockers:
    print(f"⚠️ {len(blockers)} blockers found")
    for b in blockers:
        print(f"  - {b['message']}")
```

### Capacity Check

```python
# Verify cognitive capacity before starting
result = adapter.execute_operation(
    "session",
    "initialize",
    {"assess_load": True}
)

load = result['cognitive_load']
if load['utilization_percent'] > 70:
    print("⚠️ High cognitive load - consider consolidation")
else:
    print(f"✓ Good headroom: {load['headroom']} items capacity available")
```

### Goal Prioritization

```python
# Get prioritized goal list
result = adapter.execute_operation(
    "session",
    "initialize"
)

print("Session Focus Areas:")
for focus in result['recommended_focus']:
    print(f"{focus['priority']}: {focus['focus_area']}")
```

## Implementation Notes

Demonstrates filesystem API paradigm for session initialization. This agent:
- Discovers session operations via filesystem
- Loads context from multiple sources in parallel
- Returns only summary metrics (goal counts, health scores, load levels)
- Supports drill-down for full goal details via `adapter.get_detail()`
- Assesses cognitive load vs capacity
- Identifies conflicts and blockers
- Primes working memory for efficient start
- Targets <500ms total initialization time
- Enables rapid session context establishment
