# Phase 3b: Workflow Pattern Tools

Filesystem-discoverable tools for workflow pattern analysis and intelligent task suggestions.

## Overview

Phase 3b learns from completed tasks to discover workflow patterns and suggest optimal next steps.

## Available Tools (7)

### Pattern Discovery

- **`analyze_workflow_patterns`** - Mine patterns from completed task sequences
  - Discovers implicit workflow patterns from historical data
  - Returns: Patterns found, statistics, process maturity assessment
  - When to use: After completing several tasks, to learn typical workflows

- **`get_pattern_metrics`** - Get statistics on discovered patterns
  - Returns: Total patterns, average confidence, anomalies count
  - When to use: To assess workflow maturity and process consistency

- **`find_workflow_anomalies`** - Find unusual task sequences
  - Identifies task transitions with low confidence (<10%)
  - Returns: List of anomalies with risk level
  - When to use: To identify process deviations or risks

### Workflow Analysis

- **`get_typical_workflow`** - Get standard workflow sequence for a task type
  - Returns: Ordered workflow steps with confidence scores
  - When to use: To understand how "feature" or "bugfix" tasks typically flow

- **`get_typical_workflow_steps`** - Get workflow step chain
  - Builds sequence of most-likely successors
  - Returns: Ordered steps with confidence for each
  - When to use: To see full workflow path for a task type

### Task Suggestions

- **`suggest_next_task_with_patterns`** - Get next task suggestions based on patterns
  - Analyzes completed task type and returns likely successors
  - Returns: Ranked suggestions with confidence % and explanation
  - When to use: To get intelligent next task after completion

- **`assess_workflow_risk`** - Assess risk of a task transition
  - Evaluates if proposed task transition is normal or unusual
  - Returns: Risk level (low/medium/high) with recommendations
  - When to use: To validate if your next step is on-track

## Discovery Pattern

```bash
# 1. Explore Phase 3b tools
$ ls /athena/tools/workflow_patterns/

# 2. Read tool definition
$ cat /athena/tools/workflow_patterns/suggest_next_task_with_patterns.py

# 3. Use in code
from athena.workflow.suggestions import PatternSuggestionEngine
engine = PatternSuggestionEngine(db)
suggestions = engine.suggest_next_task_with_patterns(project_id, task_id)
```

## Usage Examples

### Example 1: Get Next Task Suggestion

```python
from athena.workflow.suggestions import PatternSuggestionEngine
from athena.core.database import Database

db = Database()
engine = PatternSuggestionEngine(db)

# Get suggestions for task just completed
suggestions = engine.suggest_next_task_with_patterns(
    project_id=1,
    completed_task_id=42,
    limit=5
)

# Returns:
# [
#   {
#     "task_type": "test",
#     "confidence": 0.92,
#     "frequency": 23,
#     "explanation": "Based on 23 similar workflows (92% confidence)"
#   },
#   {...}
# ]
```

### Example 2: Learn Typical Workflow

```python
# Get how "feature" tasks typically flow
workflow = engine.suggest_workflow_for_type(project_id=1, task_type="feature")

# Returns:
# {
#   "task_type": "feature",
#   "workflow_sequence": ["design", "implement", "test", "review", "deploy"],
#   "confidence_avg": 0.88,
#   "avg_duration_hours": 168,  # 1 week
#   "task_count": 25
# }
```

### Example 3: Assess Workflow Risk

```python
# Check if test → deploy is unusual
risk = engine.get_risk_assessment(
    project_id=1,
    task_type="test",
    next_type="deploy"
)

# Returns:
# {
#   "risk_level": "high",
#   "confidence": 0.05,
#   "message": "test → deploy: 5% confidence",
#   "recommendation": "Consider if this is the right next step"
# }
```

## Key Insights

### High Process Maturity (90%+ confidence)
- Workflows are very consistent
- Suggested next steps have high reliability
- Good for automation and planning

### Medium Process Maturity (50-70% confidence)
- Some variation in workflows
- Suggestions helpful but not guaranteed
- Room for process improvement

### Low Process Maturity (<50% confidence)
- Highly variable workflows
- Need to establish standard processes
- Good opportunity for process optimization

## Algorithms

### Pattern Mining
1. Get all completed tasks in chronological order
2. Extract task type from content and tags
3. For each consecutive pair: record transition
4. Calculate confidence: count(A→B) / count(A)

### Anomaly Detection
- Flags patterns with <10% confidence
- High-frequency unusual patterns indicate process issues
- Used for continuous improvement

### Workflow Sequencing
- Builds most-likely successor chain
- Each step confidence must exceed threshold
- Stops when confidence drops below threshold

## Integration with Phase 3a

Phase 3a + Phase 3b together create intelligent task management:

| Capability | Phase 3a | Phase 3b |
|---|---|---|
| Task blocking | ✅ Explicit | - |
| Effort tracking | ✅ Estimates & actuals | - |
| Next task suggestion | ✅ Unblocked by priority | ✅ By pattern |
| Process learning | - | ✅ Implicit patterns |
| Workflow predictions | - | ✅ Sequence prediction |

## File Reference

| Implementation | Location |
|---|---|
| Pattern Storage | `/src/athena/workflow/patterns.py` |
| Sequence Analysis | `/src/athena/workflow/analyzer.py` |
| Suggestions | `/src/athena/workflow/suggestions.py` |
| MCP Handlers | `/src/athena/mcp/handlers_phase3b.py` |

## Next Steps

After using Phase 3b:
1. **Analyze patterns** - Run `analyze_workflow_patterns()` on completed tasks
2. **Review metrics** - Check `get_pattern_metrics()` to assess maturity
3. **Get suggestions** - Use `suggest_next_task_with_patterns()` for smart guidance
4. **Monitor for risk** - Check `find_workflow_anomalies()` for process deviations
5. **Optimize workflows** - Use insights to improve process consistency

