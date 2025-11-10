# Phase 7: Advanced Execution & Real-Time Plan Monitoring

## Executive Summary

Phase 7 focuses on **runtime intelligence** - transforming the Athena system from a planning tool into an **adaptive execution engine** that monitors, validates, and adjusts plans in real-time.

**Current State** (End of Phase 6):
- Plans are generated and formally verified
- Scenarios are simulated for robustness
- Quality metrics are computed
- System is "ready to execute"

**Phase 7 Goal**:
- Monitor actual vs. planned execution
- Detect assumption violations in real-time
- Validate assumptions as execution progresses
- Trigger intelligent replanning when needed
- Learn from execution outcomes

**Impact**: Transforms Athena from "planning system" to "self-adapting execution platform"

---

## Phase 7 Architecture

### Core Components

```
┌─────────────────────────────────────────────────┐
│         Phase 7: Execution Intelligence          │
│  (Real-Time Monitoring, Validation, Adaptation) │
└──────────────────┬──────────────────────────────┘
                   │
        ┌──────────┴──────────┐
        │                     │
        ▼                     ▼
   Real-Time            Assumption
   Execution            Validation
   Monitor              Engine
        │                     │
        ├─ Task Tracking     ├─ Assumption Checking
        ├─ Progress Monitoring├─ Violation Detection
        ├─ Resource Tracking ├─ Risk Assessment
        └─ Timeline Tracking └─ Confidence Scoring
        │                     │
        └──────────┬──────────┘
                   │
        ┌──────────▼──────────┐
        │ Adaptive Replanning │
        │      Engine         │
        └──────────┬──────────┘
                   │
    ┌──────────────┼──────────────┐
    │              │              │
    ▼              ▼              ▼
 Local         Segment          Full
Adjustment    Replanning      Replanning
```

### 1. Real-Time Execution Monitor

**Purpose**: Track actual execution against planned execution

**Key Operations**:

```python
class ExecutionMonitor:
    """Tracks actual vs. planned execution in real-time."""

    def __init__(self, plan: Plan, execution_context: ExecutionContext):
        """Initialize monitoring for a plan."""

    def record_task_start(
        self,
        task_id: str,
        actual_start_time: datetime,
        resources_allocated: Dict[str, float],
    ) -> TaskExecutionRecord:
        """Record when a task actually starts."""
        # Compare to planned start time
        # Check resource availability
        # Flag early/late starts

    def record_task_completion(
        self,
        task_id: str,
        actual_completion_time: datetime,
        actual_duration: float,
        resources_used: Dict[str, float],
        outcome: TaskOutcome,  # success, failure, partial, blocked
    ) -> TaskExecutionRecord:
        """Record task completion with actual metrics."""
        # Compare to planned duration
        # Identify deviations
        # Calculate completion confidence

    def get_plan_deviation(self) -> PlanDeviation:
        """Calculate overall plan deviation metrics."""
        # Time deviation: actual vs. planned
        # Resource deviation: used vs. allocated
        # Completion rate: tasks done vs. planned
        # Confidence: likelihood of on-time completion

    def predict_completion_time(self) -> Tuple[datetime, float]:
        """Predict actual completion time based on progress."""
        # Extrapolate based on current velocity
        # Account for remaining tasks
        # Consider resource constraints
        # Return (estimated_time, confidence_score)

    def get_critical_path(self) -> List[Task]:
        """Get updated critical path based on actual progress."""
        # Identify bottleneck tasks
        # Calculate slack time for non-critical tasks
        # Flag at-risk tasks
```

**Data Structures**:

```python
@dataclass
class TaskExecutionRecord:
    """Record of actual task execution."""
    task_id: str
    planned_start: datetime
    actual_start: datetime
    planned_duration: timedelta
    actual_duration: timedelta
    outcome: TaskOutcome  # success, failure, partial, blocked
    resources_planned: Dict[str, float]
    resources_used: Dict[str, float]
    deviation: float  # -1.0 to 1.0 (negative=early, positive=late)
    confidence: float  # 0.0 to 1.0 (certainty in outcome)

@dataclass
class PlanDeviation:
    """Overall plan deviation from original schedule."""
    time_deviation: timedelta
    time_deviation_percent: float  # % over/under
    resource_deviation: Dict[str, float]  # Over-usage per resource
    completion_rate: float  # 0.0 to 1.0
    completed_tasks: int
    total_tasks: int
    tasks_at_risk: List[str]
    critical_path: List[str]
    estimated_completion: datetime
    confidence: float
    deviation_severity: str  # low, medium, high, critical
```

**Example Usage**:

```python
monitor = ExecutionMonitor(plan, context)

# Start task
monitor.record_task_start(
    task_id="unit_tests",
    actual_start_time=datetime.now(),
    resources_allocated={"cpu": 4, "memory": 8}
)

# Task completes
monitor.record_task_completion(
    task_id="unit_tests",
    actual_completion_time=datetime.now(),
    actual_duration=timedelta(hours=1.5),
    resources_used={"cpu": 3.8, "memory": 7.2},
    outcome=TaskOutcome.SUCCESS
)

# Check deviation
deviation = monitor.get_plan_deviation()
if deviation.deviation_severity == "critical":
    trigger_replanning()
```

### 2. Assumption Validation Engine

**Purpose**: Verify assumptions hold during execution

**Key Operations**:

```python
class AssumptionValidator:
    """Validates plan assumptions during execution."""

    def __init__(self, plan: Plan, execution_monitor: ExecutionMonitor):
        """Initialize validator with plan and monitor."""

    def check_assumption(
        self,
        assumption_id: str,
        validation_data: Dict[str, Any],
        validation_method: str = "auto",  # auto, manual, sensor, external
    ) -> AssumptionValidationResult:
        """Check if an assumption still holds."""
        # Examples:
        # - "Team available full-time" → Check team calendar
        # - "No blocking bugs" → Check issue tracker
        # - "Network available" → Check connectivity
        # - "Requirements stable" → Check change log

    def predict_assumption_failure(
        self,
        assumption_id: str,
    ) -> Tuple[float, str]:
        """Predict likelihood of assumption failure."""
        # failure_probability: 0.0 to 1.0
        # reason: explanation of why it might fail

    def get_violated_assumptions(self) -> List[AssumptionViolation]:
        """Get all assumptions that have been violated."""
        # Filter to only violations (probability > 0.5)
        # Sort by impact (severity)

    def get_assumption_timeline(self) -> Dict[str, List[Tuple[datetime, bool]]]:
        """Get validation history for each assumption."""
        # Shows when assumption was last checked
        # Shows validation result over time

    def schedule_assumption_checks(self) -> ScheduledChecks:
        """Determine when to check each assumption."""
        # Some checks needed every 5 minutes
        # Some checks needed every hour
        # Some checks only at milestones
```

**Data Structures**:

```python
@dataclass
class Assumption:
    """A plan assumption to be validated."""
    assumption_id: str
    description: str  # "Team available full-time"
    criticality: str  # low, medium, high, critical
    validation_method: str  # how to check: manual, sensor, external, auto
    validation_frequency: timedelta  # how often to check
    expected_value: Any  # what we expect to see
    tolerance: float  # how much deviation acceptable

@dataclass
class AssumptionValidationResult:
    """Result of validating an assumption."""
    assumption_id: str
    valid: bool  # True if assumption still holds
    validation_time: datetime
    actual_value: Any
    confidence: float  # 0.0 to 1.0
    error_margin: float  # if applicable
    notes: str

@dataclass
class AssumptionViolation:
    """An assumption that has been violated."""
    assumption_id: str
    violation_time: datetime
    severity: str  # low, medium, high, critical
    impact: str  # What goes wrong if violated
    mitigation: str  # How to recover
    replanning_required: bool
    affected_tasks: List[str]  # Tasks that depend on this assumption
```

**Example Usage**:

```python
validator = AssumptionValidator(plan, monitor)

# Check specific assumption
result = validator.check_assumption(
    assumption_id="team_available",
    validation_data={"team_capacity": 0.95},  # 95% available
    validation_method="external"  # From time tracking system
)

if not result.valid:
    violations = validator.get_violated_assumptions()
    for violation in violations:
        if violation.replanning_required:
            trigger_adaptive_replanning(violation)

# Schedule future checks
checks = validator.schedule_assumption_checks()
for assumption_id, interval in checks.items():
    scheduler.schedule(
        lambda: validator.check_assumption(assumption_id),
        interval=interval
    )
```

### 3. Adaptive Replanning Engine

**Purpose**: Intelligently replan when deviations/violations detected

**Key Operations**:

```python
class AdaptiveReplanningEngine:
    """Generates new plans based on execution deviations."""

    def __init__(
        self,
        monitor: ExecutionMonitor,
        validator: AssumptionValidator,
        orchestrator: Phase6Orchestrator,
    ):
        """Initialize replanning engine with monitoring and orchestration."""

    def evaluate_replanning_need(
        self,
        deviations: PlanDeviation,
        violations: List[AssumptionViolation],
    ) -> ReplanningEvaluation:
        """Determine if replanning is needed and which strategy."""
        # Analysis:
        # - How bad is the deviation?
        # - How many tasks are at risk?
        # - How much time is remaining?
        # - Can we recover without replanning?
        # - Is it too late to replan?

    def generate_local_adjustment(
        self,
        current_task_id: str,
        deviation: PlanDeviation,
    ) -> AdjustedPlan:
        """Adjust parameters of current task (LOCAL strategy)."""
        # Modify:
        # - Task duration (extend deadline)
        # - Resource allocation (add resources)
        # - Success criteria (relax constraints)
        # - Dependencies (parallelize where possible)

    def replan_segment(
        self,
        segment_start_task: str,
        num_tasks: int,
        constraints: Dict[str, Any],
    ) -> ReplanResult:
        """Replan next N tasks (SEGMENT strategy)."""
        # Use Phase 6 orchestrator to verify new segment
        # Ensure segment integrates with rest of plan
        # Return new execution schedule

    def full_replan(
        self,
        reason: str,
        constraints: Dict[str, Any],
    ) -> ReplanResult:
        """Generate complete new plan (FULL strategy)."""
        # Use Phase 6 orchestrator
        # Use accumulated knowledge from execution so far
        # Incorporate lessons learned

    def get_replanning_options(
        self,
        deviations: PlanDeviation,
        violations: List[AssumptionViolation],
    ) -> List[ReplanningOption]:
        """Generate multiple replanning options with tradeoffs."""
        # Option 1: Extend timeline by X hours
        # Option 2: Add Y resources, complete on time
        # Option 3: Reduce scope, deliver subset by deadline
        # Option 4: Abort and escalate
        # Present costs, benefits, risks of each
```

**Data Structures**:

```python
@dataclass
class ReplanningEvaluation:
    """Evaluation of whether replanning is needed."""
    replanning_needed: bool
    strategy: AdaptiveReplanning  # NONE, LOCAL, SEGMENT, FULL, ABORT
    confidence: float  # 0.0 to 1.0
    rationale: str
    affected_tasks: List[str]
    estimated_time_impact: timedelta
    estimated_cost_impact: float
    risk_level: str  # low, medium, high
    recommended_option: int  # Index into options list

@dataclass
class ReplanningOption:
    """A possible way to recover from deviations."""
    option_id: int
    title: str  # "Add 2 resources to QA"
    description: str
    timeline_impact: timedelta  # negative = earlier, positive = later
    cost_impact: float  # negative = cheaper, positive = more expensive
    resource_impact: Dict[str, float]
    success_probability: float
    implementation_effort: str  # trivial, easy, moderate, hard
    risks: List[str]
    benefits: List[str]

@dataclass
class ReplanResult:
    """Result of replanning."""
    original_plan: Plan
    new_plan: Plan
    changes: List[str]  # What changed
    verification_passed: bool
    confidence: float
    implementation_time: timedelta
    learning: Dict[str, Any]  # Patterns observed
```

**Example Usage**:

```python
replan_engine = AdaptiveReplanningEngine(monitor, validator, orchestrator)

# Monitor execution...
monitor.record_task_completion(task_id, completion_time, duration, outcome)

# Check if replanning needed
deviations = monitor.get_plan_deviation()
violations = validator.get_violated_assumptions()

evaluation = replan_engine.evaluate_replanning_need(deviations, violations)

if evaluation.replanning_needed:
    # Get options
    options = replan_engine.get_replanning_options(deviations, violations)

    # Show to user or auto-select
    selected_option = options[evaluation.recommended_option]

    # Generate new plan
    if evaluation.strategy == AdaptiveReplanning.LOCAL:
        result = replan_engine.generate_local_adjustment(
            current_task_id,
            deviations
        )
    elif evaluation.strategy == AdaptiveReplanning.SEGMENT:
        result = replan_engine.replan_segment(
            segment_start_task=deviations.tasks_at_risk[0],
            num_tasks=5,
            constraints={}
        )
    elif evaluation.strategy == AdaptiveReplanning.FULL:
        result = replan_engine.full_replan(
            reason=str(violations[0]),
            constraints={}
        )

    # Execute new plan
    execute_plan(result.new_plan)
```

### 4. Learning & Feedback Loop

**Purpose**: Extract insights from execution outcomes

**Key Operations**:

```python
class ExecutionLearner:
    """Extracts patterns and insights from execution."""

    def __init__(self, memory_layer, consolidation_engine):
        """Initialize learner with memory and consolidation."""

    def extract_execution_patterns(
        self,
        execution_history: List[TaskExecutionRecord],
    ) -> List[ExecutionPattern]:
        """Extract patterns from execution history."""
        # Patterns:
        # - "QA tasks always take 20% longer than estimated"
        # - "Integration tests fail if run in parallel"
        # - "Code reviews take 30 min per 100 lines"

    def compute_estimation_accuracy(self) -> EstimationMetrics:
        """Compute how accurate our estimates were."""
        # Planned vs. actual for:
        # - Task duration
        # - Resource usage
        # - Dependencies
        # - Assumption validity

    def identify_bottlenecks(
        self,
        execution_history: List[TaskExecutionRecord],
    ) -> List[Bottleneck]:
        """Identify what slowed down the plan."""
        # Bottlenecks:
        # - Resource contention
        # - Dependency chains
        # - External blockers
        # - Estimation errors

    def generate_recommendations(
        self,
        execution_history: List[TaskExecutionRecord],
        project_context: Dict[str, Any],
    ) -> List[Recommendation]:
        """Generate recommendations for future plans."""
        # Recommendations:
        # - "Add 20% buffer to QA estimates"
        # - "Parallelize code review and unit tests"
        # - "Pre-allocate integration test environment"

    def store_execution_outcome(
        self,
        plan_id: int,
        execution_history: List[TaskExecutionRecord],
        patterns: List[ExecutionPattern],
        lessons: List[str],
    ) -> int:
        """Store execution outcome in memory layer."""
        # For learning and pattern extraction
```

**Data Structures**:

```python
@dataclass
class ExecutionPattern:
    """A pattern observed during execution."""
    pattern_id: str
    description: str
    confidence: float  # How sure are we?
    frequency: int  # How many times observed?
    affected_tasks: List[str]
    impact: float  # -1.0 (negative) to 1.0 (positive)
    actionable: bool  # Can we do something about it?

@dataclass
class EstimationMetrics:
    """Metrics about estimation accuracy."""
    tasks_analyzed: int
    avg_duration_error: float  # % error
    duration_error_std: float  # Standard deviation
    resource_usage_accuracy: Dict[str, float]
    assumption_validity_rate: float
    trend: str  # improving, stable, degrading

@dataclass
class Bottleneck:
    """Identifies what slowed the plan."""
    bottleneck_id: str
    type: str  # resource, dependency, external, estimation
    description: str
    impact_duration: timedelta
    affected_tasks: List[str]
    root_cause: str
    mitigation: str

@dataclass
class Recommendation:
    """Recommendation for future plans."""
    recommendation_id: str
    area: str  # estimation, parallelization, resources, dependencies
    suggestion: str
    rationale: str
    potential_benefit: str  # "10% faster", "20% less resources"
    implementation_effort: str
    confidence: float
```

---

## Phase 7 Workflow

### Execution Lifecycle

```
Plan Created (Phase 6)
    │
    ▼
┌─────────────────────────────────┐
│  1. EXECUTION STARTS            │
│     - Initialize monitor        │
│     - Schedule assumption checks│
│     - Start tracking            │
└──────────┬──────────────────────┘
           │
    ┌──────┴──────┐
    │             │
    ▼             ▼
Task Starts  Assumption Check
Record       Record Status
    │             │
    └──────┬──────┘
           │
           ▼
    ┌─────────────────┐
    │  Check Deviation│
    │  & Violations   │
    └────────┬────────┘
             │
        ┌────┴────┐
        │          │
    Small       Large/
    Deviation   Violation
        │          │
        ▼          ▼
    Continue   Evaluate
    Plan      Replanning
        │          │
        └────┬─────┘
             │
        ┌────┴────┐
        │          │
    Continue   Trigger
    Plan      Replanning
        │          │
        │          ▼
        │     Replan Segment
        │     or Full
        │          │
        │          ▼
        │     Execute New Plan
        │          │
        └────┬─────┘
             │
        ┌────▼──────┐
        │ Task Complete
        │ Record Outcome
        └────┬───────┘
             │
        More Tasks?
        ├─ Yes → Task Starts
        └─ No  → Plan Complete
             │
             ▼
    ┌────────────────────┐
    │ 2. LEARNING PHASE  │
    │ - Extract patterns │
    │ - Compute accuracy │
    │ - Generate lessons │
    │ - Store in memory  │
    └────────────────────┘
```

---

## Phase 7 Implementation Details

### 1. Real-Time Monitoring

```python
# src/athena/execution/monitor.py

class ExecutionMonitor:
    """Real-time execution monitoring."""

    def __init__(self, plan: Plan, context: ExecutionContext):
        self.plan = plan
        self.context = context
        self.task_records: Dict[str, TaskExecutionRecord] = {}
        self.start_time = datetime.now()

    def record_task_start(self, task_id, actual_start, resources):
        """Record task start."""
        task = self.plan.get_task(task_id)
        record = TaskExecutionRecord(
            task_id=task_id,
            planned_start=task.planned_start,
            actual_start=actual_start,
            deviation=(actual_start - task.planned_start).total_seconds()
        )
        self.task_records[task_id] = record

    def get_plan_deviation(self):
        """Calculate deviation metrics."""
        completed = [r for r in self.task_records.values()
                     if r.outcome in [TaskOutcome.SUCCESS, TaskOutcome.FAILURE]]

        time_dev = sum(r.actual_duration - r.planned_duration
                       for r in completed)

        return PlanDeviation(
            time_deviation=time_dev,
            completion_rate=len(completed) / len(self.plan.tasks),
            tasks_at_risk=self._identify_at_risk_tasks()
        )

    def predict_completion_time(self):
        """Predict completion time."""
        completed = [r for r in self.task_records.values()
                     if r.outcome is not None]

        if not completed:
            return self.plan.planned_completion_time

        # Calculate velocity
        elapsed = sum(r.actual_duration for r in completed)
        expected = sum(r.planned_duration for r in completed)
        velocity = elapsed / expected if expected > 0 else 1.0

        # Project remaining
        remaining = sum(t.planned_duration for t in self.plan.tasks
                       if t.task_id not in self.task_records)

        return datetime.now() + (remaining * velocity)
```

### 2. Assumption Validation

```python
# src/athena/execution/validator.py

class AssumptionValidator:
    """Validates plan assumptions."""

    def __init__(self, plan: Plan, monitor: ExecutionMonitor):
        self.plan = plan
        self.monitor = monitor
        self.validation_results: Dict[str, AssumptionValidationResult] = {}

    def check_assumption(self, assumption_id, validation_data, method):
        """Validate single assumption."""
        assumption = self.plan.get_assumption(assumption_id)

        # Different validation methods
        if method == "auto":
            valid = self._auto_validate(assumption, validation_data)
        elif method == "sensor":
            valid = self._sensor_validate(assumption, validation_data)
        elif method == "external":
            valid = self._external_validate(assumption, validation_data)
        else:
            valid = self._manual_validate(assumption, validation_data)

        result = AssumptionValidationResult(
            assumption_id=assumption_id,
            valid=valid,
            validation_time=datetime.now(),
            actual_value=validation_data
        )

        self.validation_results[assumption_id] = result
        return result

    def get_violated_assumptions(self):
        """Get all violated assumptions."""
        return [v for v in self.validation_results.values()
                if not v.valid]
```

### 3. Adaptive Replanning

```python
# src/athena/execution/adaptive_replanning.py

class AdaptiveReplanningEngine:
    """Generates plans adapting to deviations."""

    def evaluate_replanning_need(self, deviations, violations):
        """Determine if replanning needed."""
        time_dev_pct = deviations.time_deviation_percent
        violation_count = len(violations)
        at_risk_count = len(deviations.tasks_at_risk)

        # Decision logic
        if violation_count >= 3 or at_risk_count > 0.5 * len(self.plan.tasks):
            strategy = AdaptiveReplanning.FULL
        elif at_risk_count > 0 and time_dev_pct > 0.15:
            strategy = AdaptiveReplanning.SEGMENT
        elif time_dev_pct > 0.1:
            strategy = AdaptiveReplanning.LOCAL
        else:
            strategy = AdaptiveReplanning.NONE

        return ReplanningEvaluation(
            replanning_needed=strategy != AdaptiveReplanning.NONE,
            strategy=strategy
        )

    def generate_local_adjustment(self, task_id, deviations):
        """Adjust current task parameters."""
        # Modify current task
        # Return adjusted plan segment

    def replan_segment(self, start_task, num_tasks, constraints):
        """Replan task segment."""
        # Extract unexecuted tasks
        # Use Phase 6 orchestrator
        # Return new segment plan

    def full_replan(self, reason, constraints):
        """Generate complete new plan."""
        # Use Phase 6 orchestrator
        # Incorporate lessons from execution so far
        # Return new plan
```

### 4. Learning Engine

```python
# src/athena/execution/learning.py

class ExecutionLearner:
    """Extracts insights from execution."""

    def extract_execution_patterns(self, history):
        """Extract patterns from execution."""
        patterns = []

        # Pattern 1: Task duration estimates
        for task_id, records in self._group_by_task(history).items():
            avg_planned = sum(r.planned_duration for r in records) / len(records)
            avg_actual = sum(r.actual_duration for r in records) / len(records)
            if avg_actual > avg_planned * 1.2:  # 20% slower
                patterns.append(ExecutionPattern(
                    description=f"Task {task_id} takes 20% longer than estimated"
                ))

        return patterns

    def compute_estimation_accuracy(self):
        """Compute estimation accuracy metrics."""
        # Compare planned vs. actual
        # Return metrics

    def identify_bottlenecks(self, history):
        """Identify bottlenecks."""
        # Analyze critical path
        # Find delays
        # Return bottleneck list

    def generate_recommendations(self, history, context):
        """Generate actionable recommendations."""
        # Based on patterns and bottlenecks
        # Return recommendation list
```

---

## Phase 7 Integration Points

### With Phase 6
- Uses Phase6Orchestrator for replanning
- Stores planning decisions from replanning
- Updates decision validation status

### With Memory Layer
- Stores execution patterns in semantic memory
- Uses consolidation for pattern extraction
- Links execution outcomes to planning decisions

### With Code Search
- Analyzes code execution patterns
- Identifies code-related bottlenecks
- Suggests code optimizations

### With PostgreSQL
- Persists execution records
- Stores validation results
- Maintains execution history for learning

---

## Phase 7 Data Models

### Core Tables

```sql
-- src/athena/core/database_postgres.py (additions)

-- Execution tracking
CREATE TABLE IF NOT EXISTS execution_records (
    id BIGSERIAL PRIMARY KEY,
    plan_id BIGINT NOT NULL REFERENCES planning_decisions(id),
    task_id VARCHAR(255) NOT NULL,
    planned_start TIMESTAMP,
    actual_start TIMESTAMP,
    planned_duration INTERVAL,
    actual_duration INTERVAL,
    outcome VARCHAR(50),  -- success, failure, partial, blocked
    resources_planned JSONB,
    resources_used JSONB,
    deviation FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Assumption validation
CREATE TABLE IF NOT EXISTS assumption_validations (
    id BIGSERIAL PRIMARY KEY,
    plan_id BIGINT NOT NULL REFERENCES planning_decisions(id),
    assumption_id VARCHAR(255) NOT NULL,
    validation_time TIMESTAMP,
    valid BOOLEAN,
    confidence FLOAT,
    validation_data JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Execution patterns
CREATE TABLE IF NOT EXISTS execution_patterns (
    id BIGSERIAL PRIMARY KEY,
    plan_id BIGINT,
    pattern_type VARCHAR(50),  -- duration, resource, dependency
    description TEXT,
    frequency INT,
    confidence FLOAT,
    actionable BOOLEAN,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Replanning events
CREATE TABLE IF NOT EXISTS replanning_events (
    id BIGSERIAL PRIMARY KEY,
    original_plan_id BIGINT NOT NULL REFERENCES planning_decisions(id),
    new_plan_id BIGINT NOT NULL REFERENCES planning_decisions(id),
    trigger_reason VARCHAR(255),
    strategy VARCHAR(50),  -- local, segment, full, abort
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## Phase 7 MCP Tools

### New Tools to Expose

```python
# src/athena/mcp/handlers_execution.py

@server.tool()
def start_execution_monitoring(plan_id: int) -> dict:
    """Start monitoring plan execution."""

@server.tool()
def record_task_event(
    plan_id: int,
    task_id: str,
    event_type: str,  # start, complete
    actual_duration: Optional[float],
    outcome: Optional[str],
    resources_used: Optional[dict]
) -> dict:
    """Record a task execution event."""

@server.tool()
def get_plan_deviation() -> dict:
    """Get current plan deviation metrics."""

@server.tool()
def validate_assumption(
    plan_id: int,
    assumption_id: str,
    validation_data: dict,
    validation_method: str
) -> dict:
    """Validate a specific assumption."""

@server.tool()
def check_replanning_need(plan_id: int) -> dict:
    """Check if replanning is needed."""

@server.tool()
def generate_replanning_options(
    plan_id: int,
    strategy: Optional[str] = None
) -> dict:
    """Generate replanning options."""

@server.tool()
def execute_replan(
    plan_id: int,
    strategy: str,
    option_id: int
) -> dict:
    """Execute a replanning decision."""

@server.tool()
def get_execution_patterns(plan_id: int) -> dict:
    """Get patterns from execution history."""

@server.tool()
def get_estimation_accuracy() -> dict:
    """Get estimation accuracy metrics."""

@server.tool()
def get_execution_recommendations() -> dict:
    """Get recommendations based on execution."""
```

---

## Phase 7 Test Strategy

### Unit Tests
- ExecutionMonitor: Task recording, deviation calculation
- AssumptionValidator: Assumption checking, violation detection
- AdaptiveReplanningEngine: Strategy selection, plan generation
- ExecutionLearner: Pattern extraction, metric computation

### Integration Tests
- Full execution workflow with monitoring
- Assumption violation → replanning → execution
- Learning from execution outcomes
- PostgreSQL persistence of execution records

### Scenario Tests
- Nominal execution (all on time)
- Task delays (various magnitudes)
- Resource shortages
- Assumption violations
- Multiple simultaneous deviations

### Performance Tests
- Monitoring overhead (< 5% impact)
- Deviation calculation (< 100ms)
- Replanning generation (< 2s)
- Learning extraction (< 500ms)

---

## Phase 7 Success Criteria

| Criteria | Target | Method |
|----------|--------|--------|
| Execution Tracking | 100% | Record all task events |
| Assumption Validation | 95%+ | Validate vs. external sources |
| Replanning Accuracy | 80%+ | Plans meet new constraints |
| Learning Extraction | 90%+ | Patterns reflect reality |
| System Performance | < 5% overhead | Monitor impact on execution |
| Test Coverage | 85%+ | Unit + integration tests |

---

## Phase 7 Timeline Estimate

| Activity | Duration | Effort |
|----------|----------|--------|
| ExecutionMonitor impl | 6-8 hours | Implementation + testing |
| AssumptionValidator impl | 6-8 hours | Implementation + testing |
| AdaptiveReplanning impl | 8-10 hours | Complex strategy selection |
| ExecutionLearner impl | 6-8 hours | Pattern extraction |
| MCP Tool Integration | 4-6 hours | Tool definitions + handlers |
| Testing | 8-10 hours | Comprehensive test suite |
| Documentation | 4-6 hours | API docs + examples |
| **Total** | **42-56 hours** | **1-2 weeks** |

---

## Phase 7 Dependencies

### Required (Completed)
- ✅ Phase 6: Advanced Planning Orchestrator
- ✅ Phase 5 Part 3: PostgreSQL integration
- ✅ Memory Layer: Storage and consolidation

### External
- Execution environment (where plans are executed)
- Task tracking system (to record task events)
- Resource monitoring (to track resource usage)
- Assumption validators (time tracking, issue tracker, etc.)

---

## Success Scenarios

### Scenario 1: Nominal Execution
```
Plan: 5 tasks, 10 hours, 4 CPU, 8GB RAM
Execution:
- Task 1: On time, on budget
- Task 2: On time, on budget
- Task 3: 10% late, 90% resource use
- Task 4: On time, on budget
- Task 5: On time, on budget

Outcome: 2% overall delay, execute as planned
Learning: Task 3 should have 11% buffer
```

### Scenario 2: Mid-Execution Adjustment
```
Plan: 8 tasks, 24 hours
Execution at 50%:
- Task 4: 30% over time
- Resource shortfall detected
- Assumption violated: "Resources available"

Action: SEGMENT replanning
- Extend duration: 24h → 27h
- Add resource buffer
- Parallelize where possible

Outcome: Complete within new timeline
Learning: Resource estimate needs improvement
```

### Scenario 3: Critical Deviation
```
Plan: 10 tasks, 40 hours
Execution at 25%:
- Task 3: Failed (requirement change)
- Multiple assumptions violated
- Critical path blocked

Action: FULL replanning
- Generate new plan from scratch
- Incorporate lessons learned
- Restart Phase 6 verification

Outcome: New plan generated and verified
Learning: Requirement stability assumption invalid
```

---

## Conclusion

Phase 7 transforms Athena from a **planning system** into a **self-adapting execution platform**. By:

1. **Monitoring** execution in real-time
2. **Validating** assumptions as they're tested
3. **Detecting** deviations early
4. **Replanning** intelligently based on situation
5. **Learning** from outcomes for future plans

The system becomes a complete **end-to-end planning and execution** solution.

---

**Status**: Phase 7 PLANNED (Ready for implementation after Phase 6 completion)

**Next**: Phase 5 Part 4 (MCP Integration) or Phase 7 (Execution Intelligence)

**Estimated Duration**: 1-2 weeks for full implementation

**Impact**: Transforms system from "plan generator" to "adaptive execution engine"
