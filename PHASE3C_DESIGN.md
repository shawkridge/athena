# Phase 3c: Predictive Analytics Design

**Phase**: 3c - Intelligent Task Management (Final)
**Focus**: Learning effort estimation accuracy and predicting effort for new tasks
**Foundation**: Phase 3a (Metadata) + Phase 3b (Patterns)
**Status**: Design Phase

---

## 🎯 Vision

Learn from past estimates to predict effort for new tasks and improve accuracy over time.

Example output:
```
Task Type: "Feature Implementation"
Historical accuracy: 76% (20 features tracked)
Bias: Systematically underestimate by 15%

New feature estimate: 120 minutes
Adjusted estimate: 138 minutes (120 × 1.15)
Confidence: Medium (based on 20 similar features)

Recommendation: "Based on 20 similar features,
add 15% buffer. You usually underestimate by this much."
```

---

## 🔍 Core Insight

**We're Bad at Estimating, But We're Consistently Bad**

```
Feature tasks:
  Average estimate: 100 minutes
  Average actual: 115 minutes
  Bias: -13% (we underestimate consistently)

Bugfix tasks:
  Average estimate: 50 minutes
  Average actual: 48 minutes
  Bias: +4% (we overestimate slightly)

Refactor tasks:
  Average estimate: 80 minutes
  Average actual: 65-140 minutes
  Bias: Variable (hard to predict)
```

Phase 3c **learns these patterns** and:
1. Predicts effort more accurately
2. Adjusts for known biases
3. Identifies high-variance task types
4. Provides confidence scores
5. Tracks improvement over time

---

## 🏗️ Architecture: Two Components

### Component 1: EstimateAccuracyStore

**What it does**: Tracks estimate accuracy per task type

**Key methods**:
- `record_completed_task(task_id, estimate, actual)` - Store completion data
- `get_type_accuracy_stats(task_type)` - Get stats for this type
  - Average accuracy
  - Bias (systematic over/under-estimation)
  - Variance (consistency of estimates)
  - Sample size (how many data points)
- `get_bias_factor(task_type)` - Get adjustment multiplier
- `calculate_confidence(task_type)` - How confident are we?

**Database**:
```sql
-- New table: estimate_accuracy
task_type VARCHAR (feature, bug, refactor, etc.)
accuracy_percent FLOAT (actual/estimate × 100)
bias_factor FLOAT (estimate/actual ratio)
variance FLOAT (std deviation)
sample_count INT (number of tasks)
last_updated TIMESTAMP
```

### Component 2: PredictiveEstimator

**What it does**: Predicts effort for new tasks

**Key methods**:
- `predict_effort(task_type, base_estimate)` - Get adjusted estimate
- `get_estimate_range(task_type, base_estimate)` - Low/medium/high scenarios
- `get_recommendation(task_type)` - Suggestions for improvement
- `calculate_prediction_confidence(task_type)` - How much do we trust this?

**Algorithm**:
```
1. Get task type
2. Look up historical accuracy for this type
3. Apply bias factor: predicted = estimate × bias_factor
4. Add confidence interval (if low confidence, wider range)
5. Return: predicted effort + range + explanation
```

---

## 📊 Data Flow

```
Completed Task (from Phase 3a)
    ├── Task type (from Phase 3b)
    ├── Estimate: 120 minutes
    └── Actual: 150 minutes
    ↓
EstimateAccuracyStore.record_completed_task()
    ├── Calculate accuracy: 150/120 = 125%
    ├── Update type stats (features: avg 115%)
    └── Update bias factor (1.15x)
    ↓
estimate_accuracy table
    ├── feature: accuracy=115%, bias=1.15x, sample=25
    ├── bugfix: accuracy=96%, bias=0.96x, sample=42
    └── refactor: accuracy=68%, bias=variable, sample=8
    ↓
New Task: "Implement feature" (estimate: 120m)
    ↓
PredictiveEstimator.predict_effort()
    ├── Get feature stats: bias=1.15x
    ├── Calculate: 120m × 1.15 = 138m
    └── Return: "138 minutes (±15% confidence)"
    ↓
Claude Code
    └── "Based on 25 similar features, add 15% buffer"
```

---

## 💡 Example Patterns to Discover

### Pattern 1: Underestimators (Features)
```
20 completed features:
  Average estimate: 120 minutes
  Average actual: 138 minutes
  Bias: -13% (consistent underestimation)

Recommendation:
  "Feature estimates should be multiplied by 1.15
   You consistently underestimate by 15%.
   New estimate: 120m × 1.15 = 138m"
```

### Pattern 2: Consistent Estimators (Bugfixes)
```
42 completed bugfixes:
  Average estimate: 50 minutes
  Average actual: 48 minutes
  Bias: +4% (slight overestimation)

Recommendation:
  "Bugfix estimates are very accurate (96%).
   Keep doing what you're doing!"
```

### Pattern 3: Unpredictable (Refactors)
```
8 completed refactors:
  Range: 65-140 minutes
  Variance: Very high
  Sample: Small

Recommendation:
  "Refactor estimates are unpredictable.
   Only 8 samples. Need more data.
   Consider: break into smaller tasks."
```

---

## 🧮 Algorithms

### Algorithm 1: Accuracy Calculation

```python
def calculate_accuracy(estimate, actual):
    # Accuracy = min(estimate, actual) / max(estimate, actual)
    # Result: 0.0-1.0 where 1.0 = perfect
    return min(estimate, actual) / max(estimate, actual)

# Examples:
# estimate=100, actual=100 → accuracy=1.0 (100%)
# estimate=100, actual=150 → accuracy=0.67 (67%)
# estimate=100, actual=50  → accuracy=0.5 (50%)
```

### Algorithm 2: Bias Factor

```python
def calculate_bias_factor(estimates, actuals):
    # Bias = average(actual / estimate)
    # >1.0 = underestimate, <1.0 = overestimate
    return sum(a/e for a, e in zip(actuals, estimates)) / len(estimates)

# Examples:
# estimate=100, actual=115 → factor=1.15 (underestimate by 15%)
# estimate=100, actual=90  → factor=0.9 (overestimate by 10%)
```

### Algorithm 3: Confidence Scoring

```python
def calculate_confidence(task_type, sample_count, variance):
    # Confidence based on:
    # - Sample size (more = confident)
    # - Variance (less variance = confident)

    if sample_count < 5:
        return "low"      # Not enough data
    elif sample_count < 15:
        return "medium"   # Reasonable sample
    else:
        return "high"     # Good sample size

    # Adjust by variance
    if variance > 0.3:
        return "low"      # High variance = unreliable
```

---

## 📈 Metrics Phase 3c Provides

### Per-Task-Type
- **Average Accuracy**: How well do we estimate? (%)
- **Bias Factor**: Over/under-estimate systematically? (×1.2 = 20% underestimate)
- **Variance**: How consistent are estimates? (low=predictable, high=variable)
- **Sample Size**: How much data do we have?
- **Confidence**: How much can we trust the prediction?
- **Recommendation**: What should we adjust?

### Project-Level
- **Overall Accuracy**: Average across all task types
- **Estimation Trend**: Getting better or worse? (over time)
- **High-Variance Types**: Which tasks are hardest to estimate?
- **Bias Trends**: Are biases systematic or random?
- **Learning Rate**: How quickly are we improving?

---

## 🔌 Phase 3c MCP Tools

Phase 3c will expose:

1. **`predict_effort`** - Predict effort for new task
2. **`get_accuracy_stats`** - Get stats for task type
3. **`get_estimate_confidence`** - How much trust?
4. **`get_prediction_range`** - Low/med/high estimates
5. **`get_bias_recommendations`** - How to improve estimates
6. **`get_estimation_trends`** - Are we improving?
7. **`analyze_high_variance_tasks`** - Hardest to estimate

---

## 📚 Usage Examples

### Example 1: Predict Effort

```python
from athena.predictive.estimator import PredictiveEstimator

estimator = PredictiveEstimator(db)

# User estimates: "120 minutes"
prediction = estimator.predict_effort(
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
#     "optimistic": 120,  # Best case
#     "expected": 138,    # Most likely
#     "pessimistic": 160  # Worst case
#   }
# }
```

### Example 2: Get Accuracy Stats

```python
stats = estimator.get_type_accuracy_stats(
    task_type='feature'
)

# Returns:
# {
#   "task_type": "feature",
#   "sample_count": 25,
#   "average_accuracy": 0.87,  # 87%
#   "bias_factor": 1.15,
#   "variance": 0.12,
#   "recommendation": "Multiply estimates by 1.15 for features",
#   "confidence": "high"
# }
```

### Example 3: Get Trends

```python
trends = estimator.get_estimation_trends(
    task_type='feature',
    time_window_days=90
)

# Returns:
# {
#   "trend": "improving",
#   "accuracy_30days_ago": 0.75,
#   "accuracy_today": 0.87,
#   "improvement": 0.12,  # 12% better
#   "message": "Feature estimates improving! Keep refining."
# }
```

---

## 🧪 Test Strategy

**Phase 3c Tests** (25+ test cases):

1. **Accuracy Calculation**
   - ✓ Accuracy = min/max formula
   - ✓ Edge cases (estimate = actual)
   - ✓ Over/under-estimates

2. **Bias Factor**
   - ✓ Underestimate detection (factor > 1.0)
   - ✓ Overestimate detection (factor < 1.0)
   - ✓ Neutral estimates (factor ≈ 1.0)

3. **Confidence Scoring**
   - ✓ Low confidence (<5 samples)
   - ✓ Medium confidence (5-15 samples)
   - ✓ High confidence (>15 samples)
   - ✓ Variance impact on confidence

4. **Predictions**
   - ✓ Apply bias factor correctly
   - ✓ Generate estimate ranges
   - ✓ Provide accurate explanations

5. **Trends**
   - ✓ Detect improvement
   - ✓ Detect degradation
   - ✓ Identify stagnation

---

## 📊 Database Schema

```sql
-- New table: estimate_accuracy
CREATE TABLE estimate_accuracy (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL,
    task_type VARCHAR(50),
    accuracy_percent FLOAT,
    bias_factor FLOAT,
    variance FLOAT,
    sample_count INTEGER DEFAULT 0,
    avg_estimate INTEGER,
    avg_actual INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id),
    UNIQUE(project_id, task_type)
);

-- New table: estimation_trends
CREATE TABLE estimation_trends (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL,
    task_type VARCHAR(50),
    date DATE,
    accuracy FLOAT,
    sample_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);
```

---

## 🚀 Complete Task Intelligence Stack

**Phase 3a**: Dependencies + Metadata
- ✅ Task blocking relationships
- ✅ Effort estimates and actuals
- ✅ Effort accuracy tracking

**Phase 3b**: Workflow Patterns
- ✅ Learn task sequence patterns
- ✅ Suggest next tasks intelligently
- ✅ Detect workflow risks

**Phase 3c**: Predictive Analytics (NEW)
- ✅ Learn estimation accuracy by type
- ✅ Detect systematic biases
- ✅ Predict effort for new tasks
- ✅ Provide adjustment recommendations
- ✅ Track improvement over time

Together: **Complete intelligent task management system**

---

## ✅ Phase 3c Completion Criteria

- ✅ Accuracy calculation algorithm working
- ✅ Bias detection accurate
- ✅ Confidence scoring implemented
- ✅ Prediction engine functional
- ✅ Trend analysis working
- ✅ 25+ tests passing
- ✅ MCP handlers exposed
- ✅ Tools filesystem-discoverable
- ✅ Documentation complete

---

**Status**: 🟡 Design Complete, Ready for Implementation
**Estimated Effort**: 200-250 lines per module
**Dependencies**: Phase 3a (fully operational)
**Next**: Begin implementation

