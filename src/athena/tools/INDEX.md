# Athena Tools

Filesystem-discoverable tools for agent execution.

## Categories

### Consolidation (2 tools)
- `consolidate`: Extract patterns from episodic events (sleep-like consolidation)
- `get_patterns`: Retrieve learned patterns from consolidation

### Memory (3 tools)
- `recall`: Search and retrieve memories using semantic search
- `remember`: Record a new episodic event or semantic memory
- `forget`: Delete a memory by ID

### Planning (2 tools)
- `plan_task`: Decompose a task into an executable plan
- `validate_plan`: Validate a plan using formal verification and scenario testing

### Task Management - Phase 3a (7 tools)
- `create_dependency`: Create task blocking relationship (Task A blocks Task B)
- `check_task_blocked`: Check if a task is blocked by dependencies
- `get_unblocked_tasks`: Get tasks ready to work on (not blocked)
- `set_task_metadata`: Set effort estimate, complexity score, tags
- `record_task_effort`: Record actual effort spent on a task
- `get_task_metadata`: Get full metadata including accuracy
- `get_project_analytics`: Get project-wide effort and accuracy analytics

### Workflow Patterns - Phase 3b (7 tools)
- `analyze_workflow_patterns`: Mine patterns from completed task sequences
- `get_typical_workflow`: Get standard workflow sequence for a task type
- `suggest_next_task_with_patterns`: Get next task suggestions based on patterns
- `find_workflow_anomalies`: Find unusual task sequences
- `get_pattern_metrics`: Get statistics on discovered patterns
- `assess_workflow_risk`: Assess risk of a task transition
- `get_typical_workflow_steps`: Get workflow step chain

### Predictive Analytics - Phase 3c (7 tools)
- `predict_effort`: Predict effort for a task based on historical patterns
- `get_accuracy_stats`: Get accuracy statistics for a task type
- `get_estimation_confidence`: Get confidence level for estimates of a type
- `get_prediction_range`: Get low/medium/high estimate ranges
- `get_bias_recommendations`: Get adjustment recommendations based on bias
- `get_estimation_trends`: Get estimation accuracy trends over time
- `analyze_high_variance_tasks`: Identify hardest-to-estimate task types

## Usage

### Discover Tools
```bash
ls /athena/tools/              # List categories
ls /athena/tools/memory/       # List memory tools
cat /athena/tools/memory/recall.py  # Read tool definition
```

### Use a Tool
```python
from athena.tools.memory.recall import recall
results = recall('query', limit=10)
```
