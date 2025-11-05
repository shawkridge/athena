# /coordinate - Multi-Project Coordination

Use Phase 8 coordination features for managing multiple projects and resource optimization.

## Usage
```
/coordinate critical <project_id>           Analyze critical path
/coordinate conflicts <project_id> [...]    Detect resource conflicts
/coordinate dep <from_id> <to_id>          Add cross-project dependency
/coordinate reorder <project_id>           Suggest task reordering
/coordinate deadline <project_id> <date>   Check deadline feasibility
```

## Examples
```
/coordinate critical 1
/coordinate conflicts 1 2 3
/coordinate dep 5 10
/coordinate reorder 1
/coordinate deadline 1 2025-11-15
```

## What It Does

### Critical Path Analysis
- Identifies longest sequence of dependent tasks
- Calculates slack time before deadline
- Determines timeline impact of task changes
- Returns: Duration, task chain, slack time availability

### Conflict Detection
- Identifies person resource overloads
- Detects tool/data contention
- Finds dependency blockers
- Returns: Conflicts, severity level, resolution suggestions

### Dependency Management
- Register cross-project task dependencies
- Types: depends_on, blocks, related_to
- Tracks transitive dependencies
- Returns: Success/failure with conflict warnings

### Task Reordering
- Suggests reordering to reduce conflicts
- Optimizes resource utilization
- Maintains dependency constraints
- Returns: Reordering suggestions with rationale

### Deadline Feasibility
- Checks if target date is achievable
- Compares to critical path duration
- Identifies slack time margins
- Returns: Risk assessment and confidence level

## Success Indicators
- Critical path identified and tracked
- Zero unresolved critical conflicts
- All dependencies documented
- Tasks executing on critical path with < 10% variance
