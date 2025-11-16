# Task Pattern Learning System - Schema Design

## Overview
This document outlines the schema and data model for PROJECT 2: Task Learning & Analytics.

The system learns patterns from completed tasks to improve future planning accuracy and execution success rates.

---

## Core Data Structures

### 1. TaskPattern (Main Entity)

Stores learned patterns about task execution and success factors.

```python
class TaskPattern(BaseModel):
    """Learned pattern from task analysis."""

    id: Optional[int] = None
    project_id: Optional[int] = None  # NULL for cross-project patterns

    # Pattern Identity
    pattern_name: str  # e.g., "long_planning_improves_success"
    pattern_type: str  # duration|success_rate|phase_correlation|property_correlation
    description: str  # Human-readable description

    # Pattern Conditions (extracted rule)
    condition_json: str  # JSON: {"phase": "planning", "min_duration_minutes": 120, "priority": "high"}
    prediction: str  # What the pattern predicts (e.g., "90% success rate")

    # Validation Metrics
    sample_size: int  # Number of tasks used to extract pattern
    confidence_score: float  # 0.0-1.0 (System 1: statistical OR System 2: LLM validated)
    success_rate: float  # Observed success rate when pattern applies (0.0-1.0)
    failure_count: int  # Tasks that violated pattern

    # Pattern Lifecycle
    status: str  # active|deprecated|archived
    extraction_method: str  # statistical|llm_validated|manual
    system_2_validated: bool  # Has LLM reviewed this pattern?
    validation_notes: Optional[str]

    # Metadata
    created_at: datetime
    updated_at: datetime
    last_validated_at: Optional[datetime]

    # Relationships
    learned_from_tasks: list[int] = []  # Task IDs that contributed to pattern
    related_patterns: list[int] = []    # Other patterns this relates to
```

### 2. TaskExecutionMetrics (Tracking)

Tracks actual vs estimated metrics for each completed task.

```python
class TaskExecutionMetrics(BaseModel):
    """Execution metrics for a completed task."""

    id: Optional[int] = None
    task_id: int  # FK to prospective_tasks

    # Time Estimates vs Actual
    estimated_total_minutes: int  # From plan.estimated_duration_minutes
    actual_total_minutes: float
    estimation_error_percent: float  # (actual - estimated) / estimated * 100

    # Phase Breakdown
    planning_phase_minutes: float
    plan_ready_phase_minutes: float
    executing_phase_minutes: float
    verifying_phase_minutes: float

    # Success Metrics
    success: bool  # Was task completed successfully?
    failure_mode: Optional[str]  # Why it failed (if failed)

    # Task Properties (snapshot at completion)
    priority: str  # low|medium|high|critical
    complexity_estimate: Optional[int]  # 1-5 scale (if tracked)
    dependencies_count: int  # How many dependencies
    has_blockers: bool

    # Execution Quality
    retries_count: int  # How many times replanned
    external_blockers: bool  # Blocked by external factor
    scope_change: bool  # Did scope change during execution

    # Metadata
    completed_at: datetime
    created_at: datetime = Field(default_factory=datetime.now)
```

### 3. TaskPropertyCorrelation (Analysis)

Statistical correlation between task properties and success.

```python
class TaskPropertyCorrelation(BaseModel):
    """Correlation between property value and success."""

    id: Optional[int] = None
    project_id: Optional[int] = None

    # Property Being Analyzed
    property_name: str  # priority|complexity|dependencies_count|assignee_type|phase_duration
    property_value: str  # Specific value (e.g., "high", "claude", "3-5")

    # Correlation Metrics
    total_tasks: int  # Tasks with this property
    successful_tasks: int
    failed_tasks: int
    success_rate: float  # successful / total

    # Statistical Significance
    sample_size: int
    confidence_level: float  # 0.0-1.0 (95%+ = statistically significant)
    p_value: Optional[float]  # Statistical p-value

    # Time Correlation
    avg_estimated_minutes: float
    avg_actual_minutes: float
    estimation_accuracy_percent: float

    # Metadata
    created_at: datetime
    updated_at: datetime
    last_analyzed: datetime
```

---

## PostgreSQL Schema

### Table: task_patterns

```sql
CREATE TABLE IF NOT EXISTS task_patterns (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,

    -- Pattern Identity
    pattern_name VARCHAR(255) NOT NULL,
    pattern_type VARCHAR(50) NOT NULL,  -- duration|success_rate|phase_correlation|property_correlation
    description TEXT NOT NULL,

    -- Pattern Extraction
    condition_json JSONB NOT NULL,  -- Extracted rule conditions
    prediction TEXT NOT NULL,       -- What pattern predicts

    -- Validation
    sample_size INTEGER DEFAULT 1,
    confidence_score REAL NOT NULL,  -- 0.0-1.0
    success_rate REAL NOT NULL,      -- 0.0-1.0
    failure_count INTEGER DEFAULT 0,

    -- Lifecycle
    status VARCHAR(20) DEFAULT 'active',  -- active|deprecated|archived
    extraction_method VARCHAR(50) NOT NULL,  -- statistical|llm_validated|manual
    system_2_validated BOOLEAN DEFAULT FALSE,
    validation_notes TEXT,

    -- Metadata
    created_at BIGINT NOT NULL,  -- Unix timestamp
    updated_at BIGINT NOT NULL,
    last_validated_at BIGINT,

    -- Relationships (JSON arrays for flexibility)
    learned_from_tasks JSONB DEFAULT '[]',  -- [task_id1, task_id2, ...]
    related_patterns JSONB DEFAULT '[]',    -- [pattern_id1, pattern_id2, ...]

    -- Indexes
    CONSTRAINT pattern_type_check CHECK (pattern_type IN ('duration', 'success_rate', 'phase_correlation', 'property_correlation')),
    CONSTRAINT status_check CHECK (status IN ('active', 'deprecated', 'archived'))
);

CREATE INDEX idx_task_patterns_project ON task_patterns(project_id);
CREATE INDEX idx_task_patterns_status ON task_patterns(status);
CREATE INDEX idx_task_patterns_confidence ON task_patterns(confidence_score DESC);
CREATE INDEX idx_task_patterns_type ON task_patterns(pattern_type);
```

### Table: task_execution_metrics

```sql
CREATE TABLE IF NOT EXISTS task_execution_metrics (
    id SERIAL PRIMARY KEY,
    task_id INTEGER NOT NULL REFERENCES prospective_tasks(id) ON DELETE CASCADE,

    -- Time Tracking
    estimated_total_minutes INTEGER NOT NULL,
    actual_total_minutes REAL NOT NULL,
    estimation_error_percent REAL,

    -- Phase Breakdown
    planning_phase_minutes REAL DEFAULT 0,
    plan_ready_phase_minutes REAL DEFAULT 0,
    executing_phase_minutes REAL DEFAULT 0,
    verifying_phase_minutes REAL DEFAULT 0,

    -- Success
    success BOOLEAN NOT NULL DEFAULT TRUE,
    failure_mode TEXT,

    -- Task Properties (snapshot)
    priority VARCHAR(20),  -- low|medium|high|critical
    complexity_estimate INTEGER,  -- 1-5
    dependencies_count INTEGER DEFAULT 0,
    has_blockers BOOLEAN DEFAULT FALSE,

    -- Execution Quality
    retries_count INTEGER DEFAULT 0,
    external_blockers BOOLEAN DEFAULT FALSE,
    scope_change BOOLEAN DEFAULT FALSE,

    -- Metadata
    completed_at BIGINT NOT NULL,
    created_at BIGINT NOT NULL,

    -- Indexes
    CONSTRAINT priority_check CHECK (priority IN ('low', 'medium', 'high', 'critical'))
);

CREATE INDEX idx_task_execution_metrics_task ON task_execution_metrics(task_id);
CREATE INDEX idx_task_execution_metrics_success ON task_execution_metrics(success);
CREATE INDEX idx_task_execution_metrics_priority ON task_execution_metrics(priority);
CREATE INDEX idx_task_execution_metrics_completed ON task_execution_metrics(completed_at DESC);
```

### Table: task_property_correlations

```sql
CREATE TABLE IF NOT EXISTS task_property_correlations (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,

    -- Property Analysis
    property_name VARCHAR(100) NOT NULL,
    property_value VARCHAR(255) NOT NULL,

    -- Metrics
    total_tasks INTEGER NOT NULL DEFAULT 1,
    successful_tasks INTEGER NOT NULL DEFAULT 0,
    failed_tasks INTEGER NOT NULL DEFAULT 0,
    success_rate REAL NOT NULL,

    -- Statistics
    sample_size INTEGER NOT NULL DEFAULT 1,
    confidence_level REAL,  -- 0.0-1.0
    p_value REAL,

    -- Time Correlation
    avg_estimated_minutes REAL DEFAULT 0,
    avg_actual_minutes REAL DEFAULT 0,
    estimation_accuracy_percent REAL DEFAULT 0,

    -- Metadata
    created_at BIGINT NOT NULL,
    updated_at BIGINT NOT NULL,
    last_analyzed BIGINT NOT NULL,

    -- Indexes
    UNIQUE (project_id, property_name, property_value)
);

CREATE INDEX idx_task_property_correlations_project ON task_property_correlations(project_id);
CREATE INDEX idx_task_property_correlations_property ON task_property_correlations(property_name);
CREATE INDEX idx_task_property_correlations_success ON task_property_correlations(success_rate DESC);
```

---

## Data Flow

### 1. Task Completion → Metrics Capture
```
ProspectiveTask (completed)
  ↓
Extract execution metrics (duration, phases, success/failure)
  ↓
Store in task_execution_metrics table
```

### 2. Metrics → Pattern Extraction (System 1)
```
task_execution_metrics (batch of completed tasks)
  ↓
System 1: Statistical clustering & heuristic extraction
  ├─ Find common properties in successful tasks
  ├─ Identify phase duration patterns
  ├─ Extract property correlations
  ↓
Create task_patterns with confidence_score (statistical)
```

### 3. Patterns → Validation (System 2)
```
task_patterns (high uncertainty or important patterns)
  ↓
System 2: LLM validation (if confidence < threshold OR manual trigger)
  ├─ Semantic validation: Does pattern make sense?
  ├─ Generalization check: Is it too specific?
  ├─ Conflict resolution: Does it contradict other patterns?
  ↓
Update system_2_validated flag + validation_notes
```

### 4. Patterns → Planning Improvement
```
task_patterns (active, high confidence)
  ↓
Passed to planning.goal_decomposition
  ├─ Adjust effort estimates using historical patterns
  ├─ Identify risky task properties
  ├─ Recommend phase preparation based on patterns
```

---

## Key Design Decisions

### 1. Why JSON for Arrays?
- `learned_from_tasks` and `related_patterns` are sparse
- Avoids junction tables for simple references
- Simplifies queries (no JOIN for read-only relationships)
- Can grow/shrink without schema migrations

### 2. Why JSONB for Conditions?
- Flexible schema: patterns have different condition types
- Queryable: Can use PostgreSQL JSON operators
- Supports complex expressions: `{"AND": [{"phase": "planning"}, {"min_duration": 120}]}`

### 3. Unix Timestamps
- Consistent with episodic layer
- Easier to calculate durations (subtract timestamps)
- Matches consolidation system expectations

### 4. Confidence Score Instead of p-value
- Simpler for agents to reason about (0.0-1.0)
- Can represent both statistical confidence AND semantic confidence
- Enables easy filtering: `WHERE confidence_score > 0.8`

### 5. Status Field
- `active`: Currently used for planning
- `deprecated`: Old pattern, kept for history
- `archived`: Superseded by new pattern

---

## Estimated Size

**Per 1,000 completed tasks:**
- task_patterns: ~50-100 patterns @ ~500 bytes = 50KB
- task_execution_metrics: 1,000 rows @ ~300 bytes = 300KB
- task_property_correlations: ~100-200 rows @ ~400 bytes = 80KB

**Total per 1,000 tasks: ~430KB**

For 100K tasks (realistic after months of use):
- ~43MB (negligible compared to 8,128 episodic events @ 5MB)

---

## Next Steps

1. ✅ **Design** (this document)
2. **Implement** task_patterns table with migration
3. **Create** TaskPatternStore class (CRUD + analysis)
4. **Build** pattern extraction pipeline (System 1 + System 2)
5. **Hook** prospective store to trigger extraction on completion
6. **Integrate** with planning layer for better estimates

