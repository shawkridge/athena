# Phase 7 Detailed Architecture & Implementation Guide

## System Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                   PHASE 7: EXECUTION INTELLIGENCE                │
│                (Real-Time Monitoring & Adaptation)               │
└──────────────────────────────────────────────────────────────────┘
                                │
                ┌───────────────┼───────────────┐
                │               │               │
                ▼               ▼               ▼
        ┌────────────┐   ┌────────────┐   ┌─────────────┐
        │  Execution │   │ Assumption │   │  Adaptive   │
        │  Monitor   │   │ Validator  │   │ Replanning  │
        └──────┬─────┘   └──────┬─────┘   └──────┬──────┘
               │                │               │
        ┌──────▼────────────────▼───────────────▼─────┐
        │         Execution Learning Engine            │
        │  (Pattern Extraction & Recommendations)      │
        └──────────────┬──────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
   ┌─────────┐  ┌─────────┐  ┌──────────────┐
   │ Phase 6 │  │ Memory  │  │ PostgreSQL   │
   │ Orch.   │  │ Layer   │  │ Persistence  │
   └─────────┘  └─────────┘  └──────────────┘
```

## Component Dependencies

```
External Systems (inputs)
    │
    ├─ Task Tracking System (task events)
    ├─ Resource Monitor (CPU, memory, disk)
    ├─ Issue Tracker (blocker detection)
    ├─ Time Tracking (team availability)
    ├─ Network Monitor (connectivity)
    └─ Code Repo (file changes)
    │
    ▼
┌─────────────────────────────────────┐
│   EXECUTION INTELLIGENCE LAYER      │
│                                     │
│  1. ExecutionMonitor                │
│     ├─ Track task start/completion  │
│     ├─ Record resource usage        │
│     ├─ Calculate deviations         │
│     └─ Predict completion time      │
│                                     │
│  2. AssumptionValidator             │
│     ├─ Check assumption hold        │
│     ├─ Predict violations           │
│     ├─ Track validation history     │
│     └─ Schedule checks              │
│                                     │
│  3. AdaptiveReplanningEngine        │
│     ├─ Evaluate replanning need     │
│     ├─ Generate LOCAL adjustment    │
│     ├─ Generate SEGMENT replan      │
│     ├─ Generate FULL replan         │
│     └─ Score options                │
│                                     │
│  4. ExecutionLearner                │
│     ├─ Extract patterns             │
│     ├─ Compute accuracy metrics     │
│     ├─ Identify bottlenecks         │
│     └─ Generate recommendations     │
│                                     │
└────────┬────────────────────────────┘
         │
         ├─ Uses Phase 6 Orchestrator (replanning)
         ├─ Uses Memory Layer (storage)
         └─ Uses PostgreSQL (persistence)
         │
         ▼
Real-Time Execution Dashboard
   (for human monitoring & decisions)
```

## Data Flow Diagrams

### 1. Task Execution Flow

```
External Task Event
(Task starts, completes, fails)
    │
    ▼
ExecutionMonitor.record_task_*()
    │
    ├─ Parse event metadata
    ├─ Compare to planned values
    ├─ Calculate deviation
    └─ Store in task_records
    │
    ▼
Monitor.get_plan_deviation()
    │
    ├─ Aggregate all task deviations
    ├─ Calculate time_deviation
    ├─ Calculate resource_deviation
    ├─ Identify tasks_at_risk
    └─ Return PlanDeviation
    │
    ▼
Decision Point: Is deviation acceptable?
    │
    ├─ No → Evaluate replanning
    └─ Yes → Continue monitoring
```

### 2. Assumption Validation Flow

```
Scheduled Assumption Check Time
    │
    ▼
AssumptionValidator.check_assumption()
    │
    ├─ Get validation data from source
    │  (time tracking, issue tracker, etc.)
    │
    ├─ Compare to expected value
    │
    ├─ Calculate confidence
    │
    └─ Store validation result
    │
    ▼
Get violated assumptions:
Validator.get_violated_assumptions()
    │
    ├─ Filter to confidence < 0.5
    ├─ Sort by severity
    └─ Return violation list
    │
    ▼
Decision Point: Any critical violations?
    │
    ├─ Yes → Trigger replanning evaluation
    └─ No → Continue execution
```

### 3. Replanning Decision Flow

```
Trigger (Deviation OR Violation)
    │
    ▼
AdaptiveReplanningEngine.evaluate_replanning_need()
    │
    ├─ Analyze deviations
    ├─ Analyze violations
    ├─ Assess time remaining
    ├─ Assess effort to replan
    │
    └─ Select strategy:
        ├─ NONE: Continue as is
        ├─ LOCAL: Adjust current task
        ├─ SEGMENT: Replan 3-5 tasks
        ├─ FULL: Replan everything
        └─ ABORT: Stop execution
    │
    ▼
ReplanningEvaluation returned
    │
    ▼
User/System Decision:
    │
    ├─ AUTO: Use recommended strategy
    ├─ MANUAL: User selects option
    └─ ABORT: Stop here
    │
    ▼
Execute replanning strategy:
    │
    ├─ LOCAL: modify_current_task()
    ├─ SEGMENT: replan_segment()
    └─ FULL: full_replan()
    │
    ▼
Verify new plan (Phase 6 Orchestrator)
    │
    ├─ Check formal properties
    ├─ Simulate scenarios
    └─ Validate rules
    │
    ▼
Plan verified?
    │
    ├─ Yes → Execute new plan
    └─ No → Generate alternatives
```

### 4. Learning Flow

```
Plan Execution Complete
    │
    ▼
ExecutionLearner.extract_execution_patterns()
    │
    ├─ Group tasks by type
    ├─ Compare planned vs. actual
    ├─ Identify trends
    └─ Extract patterns
    │
    ▼
Patterns identified:
    │
    ├─ "Task type X takes 20% longer"
    ├─ "Resource Y gets exhausted on tasks {Z}"
    ├─ "Assumption A violated 30% of time"
    └─ etc.
    │
    ▼
ExecutionLearner.compute_estimation_accuracy()
    │
    ├─ Calculate avg duration error
    ├─ Calculate resource error
    ├─ Analyze assumption validity
    └─ Compute trend
    │
    ▼
ExecutionLearner.identify_bottlenecks()
    │
    ├─ Find critical path delays
    ├─ Identify resource contention
    ├─ Identify dependency chains
    └─ Find external blockers
    │
    ▼
ExecutionLearner.generate_recommendations()
    │
    ├─ "Add X% buffer to duration estimates"
    ├─ "Pre-allocate resources for Y tasks"
    ├─ "Parallelize Z and W tasks"
    └─ "Validate assumption A earlier"
    │
    ▼
Store in Memory Layer:
    │
    ├─ ExecutionPattern → semantic memory
    ├─ Recommendation → procedural memory
    └─ Lesson → episodic memory
    │
    ▼
Use for future plan generation (Phase 6)
```

## Class Hierarchy

```
ExecutionComponent (Abstract Base)
├── ExecutionMonitor
│   ├── record_task_start()
│   ├── record_task_completion()
│   ├── get_plan_deviation()
│   ├── predict_completion_time()
│   └── get_critical_path()
│
├── AssumptionValidator
│   ├── check_assumption()
│   ├── predict_assumption_failure()
│   ├── get_violated_assumptions()
│   └── schedule_assumption_checks()
│
├── AdaptiveReplanningEngine
│   ├── evaluate_replanning_need()
│   ├── generate_local_adjustment()
│   ├── replan_segment()
│   ├── full_replan()
│   └── get_replanning_options()
│
└── ExecutionLearner
    ├── extract_execution_patterns()
    ├── compute_estimation_accuracy()
    ├── identify_bottlenecks()
    ├── generate_recommendations()
    └── store_execution_outcome()
```

## State Machine: Execution Lifecycle

```
                    ┌─────────────┐
                    │ PLAN_READY  │
                    │ (from Phase 6)
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────────┐
                    │ EXECUTION_START │
                    │ Init monitor    │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
        ┌──────────→│ EXECUTING       │◄───────┐
        │           │ Tasks running   │        │
        │           └────────┬────────┘        │
        │                    │                 │
        │           ┌────────▼────────┐        │
        │           │ CHECK_DEVIATION │        │
        │           └────────┬────────┘        │
        │                    │                 │
        │    ┌───────────────┴────────────────┐│
        │    │                                 ││
        │ (small)                          (large)
        │    │                                 ││
        │    ▼                                 ▼▼
        │ CONTINUE            ┌──────────────────────┐
        │    │                │ EVAL_REPLANNING     │
        │    │                └──────────┬───────────┘
        │    │                           │
        │    │         ┌─────────────────┼──────────────┐
        │    │         │                 │              │
        │    │      (needed)        (not needed)     (abort)
        │    │         │                 │              │
        │    │         ▼                 │              │
        │    │ ┌────────────────┐        │              │
        │    └→│ REPLANNING     │        │              │
        │      │ Generate plan  │        │              │
        │      └────────┬───────┘        │              │
        │               │                │              │
        │         ┌─────▼──────┐         │              │
        │         │ VERIFY_NEW │         │              │
        │         │ (Phase 6)  │         │              │
        │         └─────┬──────┘         │              │
        │               │                │              │
        │          ┌────┴────┐           │              │
        │          │          │          │              │
        │     (valid)   (invalid)        │              │
        │          │          │          │              │
        │          │          └──→ Try alt│              │
        │          │                    │              │
        │          └────────────┬───────┘              │
        │                       │                     │
        └─────────────────────────────────────────────┘
                                │
                                ▼
                    ┌─────────────────────┐
                    │ EXECUTION_COMPLETE  │
                    │ Plan finished       │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ LEARNING_PHASE      │
                    │ Extract patterns    │
                    │ Generate lessons    │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ COMPLETE            │
                    └─────────────────────┘
```

## Execution Timeline Example

```
Time    Task        Plan    Actual  Deviation   Decision
────────────────────────────────────────────────────────
09:00   START       -       09:00   ✓           Monitor
09:00   Unit Tests  1h      09:05   -5m (early) ✓
09:05   Code Review 2h      09:05   ✓ start
10:00   -           -       10:00   ✓ complete, 55min vs 2h planned!
        Assumption: "Code review takes 2h"
        Violation: Code review done in 55 min
        Decision: Continue (favorable deviation)

11:00   Integration 3h      11:10   +10m late   WARN
        Resource usage: CPU 95%, Memory 7.5/8GB

11:30   Check Deviation:
        - Unit Tests: On time (early!)
        - Code Review: 27% faster (good)
        - Integration: 10% late, high resource use
        - Assumption: "No blocking bugs" - VIOLATED

        Decision: SEGMENT replanning
        - Reduce Integration scope
        - Parallelize QA tasks
        - New completion: 18:30 (30 min late)

18:30   Execution Complete

Learning:
        - Code reviews faster than expected
        - Integration tests need more resources
        - Blocking bugs assumption false
        Recommendation: Pre-check code quality,
                       Increase integration test resources by 20%
```

## Error Handling & Recovery

```
Task Execution Event
    │
    ▼
Try: Record event
    │
    ├─ Event parsing fails
    │  └─ Log error, skip, continue monitoring
    │
    ├─ Task record creation fails
    │  └─ Retry with backoff, escalate if persistent
    │
    ├─ Deviation calculation fails
    │  └─ Use cached value, recalculate later
    │
    └─ Success: Process event
    │
    ▼
Check decision point
    │
    ├─ Replanning evaluation fails
    │  └─ Conservative: assume replanning needed
    │
    ├─ Replanning generation fails
    │  └─ Try simpler strategy (LOCAL → SEGMENT → FULL)
    │
    ├─ Verification fails
    │  └─ Generate alternative options, present to user
    │
    └─ Execute successfully
    │
    ▼
Continue monitoring
```

## Performance Optimization

### Calculation Optimization

```
DEVIATION CALCULATION (O(n) where n = tasks)
Before: Recalculate all tasks every check → O(n) per check
After:  Incremental update of recent tasks → O(1) per task

ASSUMPTION VALIDATION (O(m) where m = assumptions)
Before: Check all assumptions every interval → O(m)
After:  Check on schedule, cache results → varies by frequency

REPLANNING GENERATION (O(k) where k = unexecuted tasks)
Before: Full Phase 6 orchestration → O(k) expensive
After:  Incremental refinement when possible → O(k) reduced
```

### Caching Strategy

```
Cache Level 1: Task Records (in-memory)
├─ Contains: Recent task execution records
├─ TTL: Session duration
└─ Use: Fast deviation calculation

Cache Level 2: Deviation Metrics (in-memory)
├─ Contains: Last calculated deviation
├─ TTL: 1 minute
└─ Use: Avoid recalculation if queried multiple times

Cache Level 3: Assumption Validation (database)
├─ Contains: Validation results
├─ TTL: Per validation_frequency
└─ Use: Historical tracking, learning
```

### Parallelization Opportunities

```
During Execution:
├─ Monitor (task events) - thread 1
├─ Validator (assumption checks) - thread 2 (scheduled)
├─ Learning (background) - thread 3 (low priority)
└─ Main execution loop - main thread

Replanning Preparation:
├─ Generate options (parallel) - threads N
├─ Verify each option - threads N
└─ Score and rank - main thread
```

## Integration with Existing Layers

### Memory Layer Integration

```
ExecutionMonitor
    │
    └─ Record as episodic event:
       {
           type: "task_completed",
           task_id: "unit_tests",
           duration: 1.5h,
           resources: {cpu: 3.8, mem: 7.2},
           outcome: "success"
       }

AssumptionValidator
    │
    └─ Record as episodic event:
       {
           type: "assumption_validated",
           assumption_id: "team_available",
           valid: true,
           confidence: 0.95
       }

ExecutionLearner
    │
    ├─ Store patterns in semantic memory
    ├─ Store recommendations in procedural memory
    └─ Link to planning decisions in knowledge graph
```

### Phase 6 Integration

```
When replanning triggered:
    │
    ├─ Phase6Orchestrator.orchestrate_planning()
    │  with constraints from current execution
    │
    ├─ Use current deviation as context
    ├─ Use failed assumptions as constraints
    └─ Return new plan

New plan:
    │
    ├─ Store in planning_decisions table
    ├─ Update replanning_events table
    └─ Link to original plan
```

## Testing Strategy

### Unit Test Coverage

```python
# Test ExecutionMonitor
test_record_task_start()
test_record_task_completion()
test_calculate_deviation()
test_predict_completion_time()
test_identify_at_risk_tasks()

# Test AssumptionValidator
test_check_assumption()
test_predict_assumption_failure()
test_get_violated_assumptions()
test_schedule_checks()

# Test AdaptiveReplanningEngine
test_evaluate_replanning_need()
test_generate_local_adjustment()
test_replan_segment()
test_full_replan()
test_score_options()

# Test ExecutionLearner
test_extract_patterns()
test_compute_accuracy()
test_identify_bottlenecks()
test_generate_recommendations()
```

### Integration Test Scenarios

```
Scenario 1: Nominal Execution
├─ All tasks on time
├─ All assumptions hold
└─ No replanning needed

Scenario 2: Minor Delays
├─ Some tasks delayed < 10%
├─ Most assumptions hold
└─ Monitor and continue

Scenario 3: Major Deviation
├─ Critical path delayed > 20%
├─ Multiple assumptions violated
└─ Trigger SEGMENT replanning

Scenario 4: Plan Invalidation
├─ Blocker task fails
├─ Core assumption violated
└─ Trigger FULL replanning

Scenario 5: Learning Validation
├─ Complete execution
├─ Extract patterns
├─ Validate accuracy
└─ Store recommendations
```

---

## Conclusion

Phase 7 provides the final piece of the Athena system: **real-time execution intelligence** that monitors plans, detects issues, adapts intelligently, and learns from outcomes.

This transforms Athena from a "batch planning system" into a "continuous self-improving execution engine."
