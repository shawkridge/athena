# Phase 3c: Predictive Analytics Tools

Filesystem-discoverable tools for learning from estimation accuracy and predicting effort for new tasks.

## Overview

Phase 3c learns from completed tasks to discover estimation bias patterns and predict effort for new tasks with adjustment factors.

## Available Tools (7)

### Estimation Learning

- **`get_accuracy_stats`** - Get accuracy statistics for a task type
  - Returns: Accuracy percent, bias factor, variance, sample count, recommendation
  - When to use: To understand how well you estimate a particular task type
  - Prerequisites: Complete 5+ tasks of the same type

- **`get_bias_recommendations`** - Get adjustment recommendations based on bias
  - Returns: Bias factor, confidence level, and suggested adjustment
  - When to use: To learn if you systematically over/under-estimate
  - Example: "Multiply estimates by 1.15x to account for 15% underestimation"

- **`analyze_high_variance_tasks`** - Identify hardest-to-estimate task types
  - Returns: List of task types ranked by estimation difficulty (variance)
  - When to use: To identify which task types need better decomposition
  - Recommendation: Break high-variance tasks into smaller, more predictable subtasks

### Effort Prediction

- **`predict_effort`** - Predict effort for a new task based on historical patterns
  - Args: task_type (str), base_estimate (int minutes)
  - Returns: Adjusted estimate, range (optimistic/expected/pessimistic), confidence, explanation
  - When to use: Before starting a new task, to get better estimate
  - Example output: "Based on 25 similar 'feature' tasks, you consistently underestimate by 15%. Adjusted: 138 minutes."

- **`get_prediction_range`** - Get low/medium/high estimate ranges
  - Args: task_type, base_estimate
  - Returns: Optimistic, expected, pessimistic estimates
  - When to use: To plan with uncertainty (best/worst case scenarios)

- **`get_estimation_confidence`** - Get confidence level for estimates of a type
  - Args: task_type
  - Returns: Confidence level (low/medium/high) with explanation
  - When to use: To assess reliability of predictions
  - Levels:
    - Low: <5 similar tasks (need more data)
    - Medium: 5-15 similar tasks (reasonable data)
    - High: >15 similar tasks (strong historical base)

### Trend Analysis

- **`get_estimation_trends`** - Get estimation accuracy trends over time
  - Args: task_type, days_back (default: 90)
  - Returns: Trend direction (improving/stable/degrading), improvement percent
  - When to use: To track if you're getting better at estimation over time
  - Example: "Feature estimates improving! 12% better over last 90 days."

## Discovery Pattern

```bash
# 1. Explore Phase 3c tools
$ ls /athena/tools/predictive/

# 2. Read tool definition
$ cat /athena/tools/predictive/predict_effort.py

# 3. Use in code
from athena.predictive.estimator import PredictiveEstimator
from athena.core.database import Database

db = Database()
estimator = PredictiveEstimator(db)
prediction = estimator.predict_effort(project_id=1, task_type='feature', base_estimate=120)
```

## Usage Examples

### Example 1: Predict Effort for New Task

```python
from athena.predictive.estimator import PredictiveEstimator
from athena.core.database import Database

db = Database()
estimator = PredictiveEstimator(db)

# User estimates: "120 minutes" for a feature
prediction = estimator.predict_effort(
    project_id=1,
    task_type='feature',
    base_estimate=120
)

# Returns:
# {
#   "predicted_effort": 138,
#   "base_estimate": 120,
#   "bias_factor": 1.15,
#   "confidence": "high",
#   "explanation": "Based on 25 similar features, you consistently "
#                  "underestimate by 15%. Adjusted: 138 minutes.",
#   "range": {
#     "optimistic": 120,
#     "expected": 138,
#     "pessimistic": 160
#   }
# }
```

### Example 2: Get Accuracy Statistics

```python
from athena.predictive.accuracy import EstimateAccuracyStore

store = EstimateAccuracyStore(db)
stats = store.get_type_accuracy_stats(project_id=1, task_type='feature')

# Returns:
# {
#   "task_type": "feature",
#   "sample_count": 25,
#   "accuracy_percent": 87.0,
#   "bias_factor": 1.15,
#   "variance": 0.12,
#   "confidence": "high",
#   "recommendation": "Multiply estimates by 1.15x to account for 15% underestimation"
# }
```

### Example 3: Get Estimation Trends

```python
trends = estimator.get_estimation_trends(
    project_id=1,
    task_type='feature',
    days_back=90
)

# Returns:
# {
#   "task_type": "feature",
#   "trend": "improving",
#   "accuracy_90days_ago": 0.75,
#   "accuracy_today": 0.87,
#   "improvement": 0.12,
#   "message": "Great! Your improving by 12%. Keep refining estimates."
# }
```

### Example 4: Find High-Variance Tasks

```python
from athena.predictive.accuracy import EstimateAccuracyStore

store = EstimateAccuracyStore(db)
all_stats = store.get_all_type_stats(project_id=1)

# Filter for high variance (>0.2)
high_variance = [s for s in all_stats if s.get("variance", 0) > 0.2]

for task in high_variance:
    print(f"{task['task_type']}: variance={task['variance']}")
    print("  → Recommendation: Break into smaller, more predictable subtasks")
```

## Core Algorithms

### Accuracy Calculation

```
Accuracy = min(estimate, actual) / max(estimate, actual) × 100%

Examples:
- Estimate 100m, actual 100m → 100% accuracy
- Estimate 100m, actual 150m → 67% accuracy
- Estimate 100m, actual 50m  → 50% accuracy
```

### Bias Factor

```
Bias Factor = average(actual / estimate)

>1.0 = systematically underestimate
<1.0 = systematically overestimate
=1.0 = well-calibrated

Example:
- 20 features: avg estimate 100m, avg actual 115m
- Bias factor = 115/100 = 1.15 (15% underestimation)
- Recommendation: Multiply estimates by 1.15
```

### Confidence Levels

```
Low confidence:   <5 similar tasks
Medium confidence: 5-15 similar tasks (or high variance)
High confidence:  >15 similar tasks with low variance
```

## Database Schema

Phase 3c uses two tables:

```sql
-- Tracks estimate accuracy per task type
CREATE TABLE estimate_accuracy (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL,
    task_type VARCHAR(50),
    accuracy_percent FLOAT,
    bias_factor FLOAT,
    variance FLOAT,
    sample_count INTEGER,
    avg_estimate INTEGER,
    avg_actual INTEGER,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id),
    UNIQUE(project_id, task_type)
);

-- Tracks estimation accuracy trends over time
CREATE TABLE estimation_trends (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL,
    task_type VARCHAR(50),
    date DATE,
    accuracy FLOAT,
    sample_count INTEGER,
    created_at TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);
```

## Integration with Phases 3a & 3b

**Phase 3a**: Metadata & Dependencies
- Task estimates and actuals
- Task effort tracking

**Phase 3b**: Workflow Patterns
- Task type classification
- Task sequences

**Phase 3c**: Predictive Analytics (NEW)
- Learn estimation accuracy by type
- Detect systematic biases
- Predict effort for new tasks
- Provide adjustment recommendations
- Track improvement over time

Together: **Complete Intelligent Task Management**
- What CAN I do next? (3a: dependencies)
- What SHOULD I do next? (3b: patterns)
- How long will it take? (3c: predictions)

## Metrics Phase 3c Provides

### Per-Task-Type
- **Average Accuracy**: How well do we estimate? (%)
- **Bias Factor**: Over/under-estimate systematically? (×1.2 = 20% underestimate)
- **Variance**: How consistent are estimates? (low=predictable, high=variable)
- **Sample Size**: How many similar tasks have we completed?
- **Confidence**: How much can we trust the prediction?
- **Recommendation**: What should we adjust?

### Project-Level
- **Overall Accuracy**: Average across all task types
- **Estimation Trend**: Getting better or worse over time?
- **High-Variance Types**: Which tasks are hardest to estimate?
- **Learning Rate**: How quickly are we improving?

## Next: Record Completions

Phase 3c needs data from completed tasks. To populate accuracy statistics:

1. **Complete a task** with estimate and actual duration
2. **Record completion**: Call `EstimateAccuracyStore.record_completion()`
3. **System learns**: Bias factors and accuracy stats auto-update
4. **Predictions improve**: Each completion makes predictions more accurate

```python
# Record task completion
store = EstimateAccuracyStore(db)
store.record_completion(
    project_id=1,
    task_type='feature',
    estimate_minutes=120,
    actual_minutes=138
)

# System updates:
# - accuracy_percent: (min/max) × 100 = 87%
# - bias_factor: actual/estimate = 1.15
# - sample_count: 1 → 2 → 3...
# - confidence: gradually moves from "low" to "high"
```

---

**Status**: 🟢 Production-Ready
**Reliability**: ✅ Accuracy-Based Learning
**Quality**: ✅ Confidence-Scored Predictions
