# Phase 3b: Workflow Patterns Design

**Phase**: 3b - Task Intelligence (Advanced)
**Focus**: Mining patterns from completed workflows
**Foundation**: Phase 3a (Dependencies + Metadata)
**Status**: Design Phase

---

## 🎯 Vision

Learn from completed tasks to suggest optimal workflow ordering.

Example output:
```
Pattern: "implement" → "test"
  Confidence: 92% (23 of 25 times)
  Average gap: 1 day
  Task types: feature → testing

Suggestion: "You just completed 'implement feature'.
             Based on 92% of past workflows,
             'write tests' should come next."
```

---

## 🔍 Core Insight

**Tasks don't exist in isolation. They form patterns.**

- 90% of "feature implementation" → "testing"
- 85% of "code review" → "merge to main"
- 95% of "bug discovery" → "root cause analysis"

Phase 3b **discovers these patterns** from historical data and uses them to:
1. Suggest next tasks intelligently
2. Warn of unusual workflows
3. Optimize team processes
4. Predict task effort by type

---

## 🏗️ Architecture: Three Components

### Component 1: WorkflowPatternStore

**What it does**: Mines completed task sequences from database

**Key methods**:
- `find_predecessor_patterns(task_id)` - What usually comes before this?
- `find_successor_patterns(task_id)` - What usually comes after this?
- `get_pattern_confidence(from_type, to_type)` - How often does X → Y?
- `get_typical_sequence(task_type)` - What's the standard workflow for this type?

**Database**:
```sql
-- New table: workflow_patterns
task_from_type VARCHAR (e.g., "implement", "test", "review")
task_to_type VARCHAR (e.g., "test", "review", "deploy")
frequency INT (how many times A → B)
confidence FLOAT (frequency / all_As, e.g., 0.92)
avg_duration_hours FLOAT (typical gap between tasks)
created_at TIMESTAMP
```

### Component 2: TaskSequenceAnalyzer

**What it does**: Analyzes task metadata to learn patterns

**Key methods**:
- `extract_task_type_from_content(task_content)` - Classify task (feature/bug/refactor/review)
- `analyze_completed_sequences()` - Mine all completed task chains
- `calculate_pattern_strength(pattern)` - Score a pattern's reliability
- `find_anomalies()` - Find unusual workflow patterns

**Algorithms**:
1. **Sequence Mining**: Graph of completed tasks → find common paths
2. **Confidence Scoring**: count(A→B) / count(A) = confidence
3. **Type Classification**: Use tags + content to classify task type
4. **Anomaly Detection**: Paths < 10% frequency flagged as unusual

### Component 3: Pattern-Aware Suggestion Engine

**What it does**: Suggests next tasks using patterns

**Key methods**:
- `suggest_next_task_with_patterns(current_task)` - Suggest based on patterns
- `get_workflow_for_type(task_type)` - Get standard workflow for task type
- `confidence_sorted_suggestions(task_id)` - Get suggestions ranked by confidence

**Algorithm**:
```
1. Get completed task
2. Find its type (from tags/content)
3. Query workflow_patterns: "What usually follows this type?"
4. Sort by confidence
5. Filter out already-completed tasks
6. Return top 5 suggestions with confidence %
```

---

## 📊 Data Flow

```
Completed Tasks (from Phase 3a)
    ↓
WorkflowPatternStore.analyze_completed_sequences()
    ├── Extract task types
    ├── Build dependency graph
    ├── Calculate transition frequencies
    └── Compute confidence scores
    ↓
workflow_patterns table
    ├── implement → test (92% confidence)
    ├── test → review (85% confidence)
    ├── review → merge (78% confidence)
    └── [all patterns discovered]
    ↓
Pattern-Aware Suggestion Engine
    └── "Next tasks for 'implement' type: test (92%), review (40%)"
    ↓
Claude Code
    └── "Based on 92 similar workflows, 'test' should come next"
```

---

## 💡 Example Patterns to Discover

### Pattern 1: Feature Workflow
```
Tasks Completed:
1. Design feature (tag: feature, planning)
2. Implement feature (tag: feature, implementation)
3. Write tests (tag: feature, testing)
4. Code review (tag: feature, review)
5. Merge to main (tag: feature, merge)

Pattern Discovered:
  design → implement (100%, 5/5)
  implement → test (100%, 5/5)
  test → review (100%, 5/5)
  review → merge (100%, 5/5)

Output:
  "Feature workflow: design → implement → test → review → merge"
  "Average duration: 2 weeks"
```

### Pattern 2: Bug Fix Workflow
```
Tasks Completed:
1. Bug reported (bug, discovery)
2. Reproduce bug (bug, analysis)
3. Root cause analysis (bug, diagnosis)
4. Implement fix (bug, implementation)
5. Test fix (bug, testing)
6. Deploy (bug, deployment)

Pattern Discovered:
  discovery → analysis (98%, 49/50)
  analysis → diagnosis (95%, 47/50)
  diagnosis → implementation (92%, 46/50)
  implementation → testing (100%, 50/50)
  testing → deployment (88%, 44/50)

Output:
  "Bug fix workflow: discovery → analysis → diagnosis → fix → test → deploy"
  "Most critical: diagnosis (directly affects fix quality)"
```

### Pattern 3: Review Process
```
Pattern Discovered:
  code_review → approval (75%, 30/40)
  code_review → revisions (20%, 8/40)
  revisions → code_review (95%, 9/9)  [minor revisions, back to review]
  approval → merge (100%, 30/30)

Output:
  "Code review: 75% approved directly, 20% need revisions"
  "If revisions needed: re-review takes avg 1 day"
```

---

## 🧮 Algorithms

### Algorithm 1: Sequence Mining

```python
def analyze_completed_sequences(project_id):
    # Get all completed tasks in order
    completed = query(
        "SELECT id, completed_at, tags, content
         FROM prospective_tasks
         WHERE status='completed' AND project_id=?
         ORDER BY completed_at"
    )

    # Build task graph
    for i, task in enumerate(completed[:-1]):
        next_task = completed[i+1]

        from_type = extract_type(task)
        to_type = extract_type(next_task)

        # Record transition
        store_pattern(from_type, to_type, task.id, next_task.id)

    # Calculate confidence for each edge
    for pattern in all_patterns:
        confidence = pattern.frequency / count_of_type(pattern.from_type)
        pattern.confidence = confidence
```

### Algorithm 2: Confidence Scoring

```python
def calculate_confidence(from_type, to_type):
    # How often does "from" transition to "to"?
    transitions = count_transitions(from_type, to_type)
    total = count_all_transitions_from(from_type)

    if total == 0:
        return 0.0

    confidence = transitions / total

    # High confidence: 0.7+
    # Medium confidence: 0.4-0.7
    # Low confidence: <0.4

    return confidence
```

### Algorithm 3: Anomaly Detection

```python
def find_anomalies(project_id):
    patterns = query_patterns(project_id)
    anomalies = []

    for pattern in patterns:
        if pattern.confidence < 0.1:  # Less than 10%
            anomalies.append({
                'from': pattern.from_type,
                'to': pattern.to_type,
                'confidence': pattern.confidence,
                'count': pattern.frequency,
                'risk': 'unusual workflow'
            })

    return anomalies
```

---

## 📈 Metrics Phase 3b Provides

### Per-Pattern Metrics
- **Confidence**: How often does X → Y? (0.0-1.0)
- **Frequency**: How many times has this pattern occurred?
- **Duration**: Average days between X and Y completion
- **Deviation**: Std dev of duration (consistency)

### Per-Task-Type Metrics
- **Typical Workflow**: Standard sequence for this type
- **Success Rate**: % of tasks following standard workflow
- **Average Duration**: How long tasks of this type typically take
- **Deviation Rate**: How much variation exists

### Project-Level Metrics
- **Process Consistency**: % of tasks following discovered patterns
- **Process Maturity**: How well-defined are workflows?
- **Risk Workflows**: Anomalies flagged as potential issues

---

## 🔌 Integration with Phase 3a

Phase 3a provides the foundation:
- **Task completion**: Marks tasks complete (Phase 3a)
- **Metadata**: Task effort, complexity, tags (Phase 3a)
- **Dependencies**: Explicit ordering (Phase 3a)

Phase 3b learns from it:
- **Implicit patterns**: "These usually go together"
- **Workflow sequences**: "This is the standard process"
- **Predictions**: "Next task should be..."

Together they create **intelligent task management**:
- Phase 3a: Explicit (create dependencies, set effort)
- Phase 3b: Implicit (learn patterns, suggest workflows)

---

## 📚 Phase 3b MCP Tools

Phase 3b will expose:

1. **`analyze_workflow_patterns`** - Run pattern mining analysis
2. **`get_typical_workflow`** - Get standard workflow for task type
3. **`get_pattern_confidence`** - Get confidence for X → Y transition
4. **`find_workflow_anomalies`** - Find unusual task sequences
5. **`suggest_next_with_patterns`** - Suggest next task using patterns
6. **`get_pattern_metrics`** - Get metrics for a pattern
7. **`export_workflow_diagram`** - Export workflow as ASCII diagram

---

## 🚀 Usage Examples

### Example 1: Suggest Next Task

```python
from athena.workflow.patterns import PatternSuggestionEngine

engine = PatternSuggestionEngine(db)

# Current task just completed
suggestions = engine.suggest_next_with_patterns(
    project_id=1,
    completed_task_id=42,
    limit=5
)

# Returns:
# [
#   {task_type: 'test', confidence: 0.92, count: 23},
#   {task_type: 'review', confidence: 0.40, count: 8},
#   {task_type: 'deploy', confidence: 0.12, count: 3},
# ]
```

### Example 2: Get Typical Workflow

```python
analyzer = TaskSequenceAnalyzer(db)

workflow = analyzer.get_typical_sequence(
    task_type='feature',
    confidence_threshold=0.7
)

# Returns:
# [
#   {step: 1, type: 'design', confidence: 0.95},
#   {step: 2, type: 'implement', confidence: 0.92},
#   {step: 3, type: 'test', confidence: 0.94},
#   {step: 4, type: 'review', confidence: 0.88},
#   {step: 5, type: 'deploy', confidence: 0.85},
# ]
```

### Example 3: Detect Process Issues

```python
analyzer = TaskSequenceAnalyzer(db)

anomalies = analyzer.find_anomalies(project_id=1)

# Returns unusual patterns:
# [
#   {
#     from: 'implement',
#     to: 'deploy',
#     confidence: 0.05,
#     count: 2,
#     message: '95% of deploys follow testing, this is unusual'
#   }
# ]
```

---

## 🧪 Test Strategy

**Phase 3b Tests** (20+ test cases):

1. **Pattern Mining**
   - ✓ Extract task types correctly
   - ✓ Build dependency graph
   - ✓ Calculate transition frequencies
   - ✓ Compute confidence scores

2. **Confidence Scoring**
   - ✓ Confidence = frequency / total
   - ✓ High confidence (0.7+) identified
   - ✓ Low confidence (<0.1) identified
   - ✓ Edge cases (no transitions, single task)

3. **Workflow Analysis**
   - ✓ Typical sequence extracted
   - ✓ Steps ordered correctly
   - ✓ Confidence scores propagated
   - ✓ High-confidence paths prioritized

4. **Anomaly Detection**
   - ✓ Unusual patterns (<10% frequency) flagged
   - ✓ Explanation provided
   - ✓ Risk level assessed

5. **Suggestions**
   - ✓ Next task suggested by confidence
   - ✓ Multiple options ranked
   - ✓ Explanation includes confidence %

---

## 📊 Database Schema

```sql
-- New table: workflow_patterns
CREATE TABLE workflow_patterns (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL,
    from_task_type VARCHAR(50),
    to_task_type VARCHAR(50),
    frequency INTEGER DEFAULT 1,
    confidence FLOAT,
    avg_duration_hours FLOAT,
    std_dev_duration FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id),
    UNIQUE(project_id, from_task_type, to_task_type)
);

-- New table: task_type_workflows
CREATE TABLE task_type_workflows (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL,
    task_type VARCHAR(50),
    workflow_sequence TEXT,  -- JSON: [step1, step2, ...]
    confidence_avg FLOAT,
    avg_total_duration_hours FLOAT,
    task_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id),
    UNIQUE(project_id, task_type)
);
```

---

## 📝 Files to Create (Phase 3b)

1. **`src/athena/workflow/patterns.py`** (350 lines)
   - `WorkflowPatternStore` - Mine and store patterns
   - `PatternSuggestionEngine` - Suggest based on patterns

2. **`src/athena/workflow/analyzer.py`** (280 lines)
   - `TaskSequenceAnalyzer` - Analyze completed sequences
   - `TaskTypeClassifier` - Classify task types

3. **`src/athena/mcp/handlers_phase3b.py`** (300 lines)
   - MCP handlers for Phase 3b operations

4. **`src/athena/tools/workflow_patterns/`** (7 tool files)
   - Filesystem-discoverable Phase 3b tools

5. **`tests/phase3b_integration_test.py`** (400 lines)
   - 20+ comprehensive tests

6. **`PHASE3B_COMPLETION_SUMMARY.md`**
   - Final documentation

---

## ✅ Phase 3b Completion Criteria

- ✅ Pattern mining algorithm working
- ✅ Confidence scoring accurate
- ✅ Workflow sequences discoverable
- ✅ Suggestions ranked by confidence
- ✅ Anomalies detected and reported
- ✅ 20+ tests passing
- ✅ MCP handlers exposed
- ✅ Tools filesystem-discoverable
- ✅ Documentation complete

---

## 🎓 Why Phase 3b Matters

**Current State (Phase 3a)**:
- Explicit dependencies: "Task A blocks Task B"
- Effort tracking: "This took 150 minutes"
- Smart suggestions: "Tasks that aren't blocked"

**With Phase 3b**:
- **Pattern learning**: "90% of features follow this workflow"
- **Predictive suggestions**: "Based on patterns, test should be next"
- **Process insights**: "How is our team actually working?"
- **Continuous improvement**: "Track whether patterns improve over time"

Phase 3b turns **task data into process intelligence**.

---

**Status**: 🟡 Design Complete, Ready for Implementation
**Estimated Effort**: 200-300 lines per module
**Dependencies**: Phase 3a (fully operational)
**Next**: Begin implementation

