# /monitor - Task Health Dashboard

Quick access to Phase 5 health metrics.

## Usage
```
/monitor task <id>      Check specific task
/monitor project <id>   Check project overview
```

## Examples
```
/monitor task 1
/monitor project 1
```

## What It Does
- Displays real-time task health scores (0.0-1.0)
- Shows progress percentage and duration variance
- Lists active blockers and errors
- Provides project-wide health summary
- Identifies tasks in critical status (< 0.5)

## Health Status Guide
- **Healthy** (≥ 0.65): Task is progressing well
- **Warning** (0.5-0.65): Task has issues, consider optimization
- **Critical** (< 0.5): Task needs immediate intervention
