---
description: Browse episodic events chronologically with filtering and visualization
allowed-tools: mcp__memory__recall_events, mcp__memory__get_timeline
group: memory-management
---

# /timeline - Episodic Event Browser

## Overview

Visualize your work history as a chronological timeline of events. Filter by type, outcome, date range, or project. Discover patterns in when things happen and how different activities relate temporally.

## Usage

```
/timeline [--days 7] [--type action|error|success|decision] [--outcome success|failure|partial] [--format ascii|table|json]
```

## Commands

### View Recent Timeline (Default)
```
/timeline
```

Shows events from last 7 days in ASCII timeline format.

**Example Output:**
```
TIMELINE - Last 7 Days

2025-10-24 Wed
  16:35 ✓ Completed /consolidate command (success)
  15:22 ✓ Analyzed MCP tool coverage (success)
  14:10 ✓ Created 3 critical commands (success)
  12:00 → Reviewed research findings (action)

2025-10-23 Tue
  18:45 ✗ Test suite failed for WM module (failure)
  17:30 ✓ Fixed episodic memory schema (success)
  16:00 → Debugged consolidation pipeline (action)
  14:20 → Code review: PR #456 (action)

2025-10-22 Mon
  19:00 ✓ Memory optimization complete (success)
  15:00 → Planning session for Phase 2 (decision)
  11:30 ✗ Integration test timeout (failure)

2025-10-21 Sun
  10:00 ✓ Documentation updated (success)
```

### Filter by Type
```
/timeline --type action --days 14
```

Show only specific event types:
- `action` - Activities/work done
- `error` - Errors encountered
- `success` - Successful completions
- `decision` - Decisions made
- `test_run` - Test executions
- `file_change` - File modifications

### Filter by Outcome
```
/timeline --outcome failure --days 30
```

Show events by outcome:
- `success` - Went well
- `failure` - Didn't work
- `partial` - Partially successful
- `ongoing` - Still in progress

### Specify Date Range
```
/timeline --days 30 --start "2025-10-01" --end "2025-10-24"
```

Show events in specific date range.

### Table Format
```
/timeline --format table
```

**Output:**
```
Date       Time   Type      Outcome  Description
──────────────────────────────────────────────────────────
2025-10-24 16:35  action    success  Completed /consolidate command
2025-10-24 15:22  action    success  Analyzed MCP coverage
2025-10-24 14:10  action    success  Created 3 commands
2025-10-23 18:45  error     failure  Test suite failed
2025-10-23 17:30  action    success  Fixed episodic memory
```

### JSON Output
```
/timeline --json --days 7
```

Structured data for analysis.

## Pattern Discovery

### Find Error Patterns
```
/timeline --type error --days 30 --analyze-patterns
```

Identifies clustering of errors:
```
ERROR PATTERNS DETECTED:

Cluster 1: Memory consolidation failures
  - Frequency: 4 errors / 30 days (1.3 per week)
  - Time of day: Mostly 6-8pm
  - Context: After long sessions
  - Solution: Schedule consolidation earlier

Cluster 2: Integration test timeouts
  - Frequency: 3 errors / 30 days
  - Time of day: Spread throughout day
  - Context: When running full suite
  - Solution: Improve test parallelization
```

### Success Patterns
```
/timeline --outcome success --analyze-patterns
```

Shows what works:
```
SUCCESS PATTERNS:

Most productive times:
  - Morning sessions (6-10am): 87% success rate
  - Afternoon (2-4pm): 72% success rate
  - Evening (6pm+): 61% success rate

Most successful activities:
  1. Code review sessions: 94% success
  2. Deep research: 88% success
  3. Debugging: 82% success
  4. Refactoring: 79% success
  5. Writing tests: 71% success

Recommendation: Schedule research in morning for best results
```

## Advanced Usage

### Find Causal Chains
```
/timeline --find-chains --window 2h
```

Discover events that likely caused other events:
```
CAUSAL CHAINS DETECTED:

Chain 1: File change → Error
  2025-10-23 17:00 - Modified: memory_store.py
  2025-10-23 18:45 - Error: Test suite failed
  Lag: 105 minutes
  Probability: 0.82 (likely related)

Chain 2: Decision → Implementation
  2025-10-22 15:00 - Decision: Phase 2 planning
  2025-10-22 16:30 - Action: Started implementation
  Lag: 90 minutes
  Probability: 0.95 (very likely related)
```

### Workload Analysis
```
/timeline --analyze-workload --days 30
```

Shows activity density and patterns:
```
WORKLOAD ANALYSIS - Last 30 Days

Events per day (average): 8.3
Peak day: 2025-10-24 (14 events)
Slowest day: 2025-10-15 (2 events)

Activity distribution:
  Mon-Fri: 7.8 events/day (weekday baseline)
  Sat-Sun: 3.2 events/day (weekend)

Event types breakdown:
  Actions: 68% (typical activity)
  Successes: 18% (completion rate)
  Errors: 9% (issue rate)
  Decisions: 5% (planning rate)

Recommendation: Your pace is consistent. Consider adding 1-2 more
              decision/planning events per week.
```

### Domain Timeline
```
/timeline --domain "LLM Memory" --days 14
```

Show events specific to a domain:
```
DOMAIN TIMELINE: LLM Memory Architectures

2025-10-24 Research on consolidation algorithms (success)
2025-10-23 Wrote documentation for episodic layer (success)
2025-10-21 Integration test for memory systems (success)
2025-10-19 Debugging temporal chain formation (partial)
2025-10-17 Decision: Use SQLite for storage (decision)
2025-10-15 Initial research on memory models (action)
2025-10-14 Testing episodic event creation (success)

Domain progress: Solid progress in recent days
              5 successes, 1 partial, 1 action in last 2 weeks
```

## Temporal Insights

### Identify Productive Hours
```
/timeline --find-productive-hours
```

**Output:**
```
Your most productive hours:
  7am: 94% success rate (early riser advantage)
  8am: 91% success
  9am: 89% success
  10am: 87% success
  ...
  6pm: 62% success
  7pm: 58% success
  8pm: 45% success (declining focus)

Recommendation: Schedule deep work before 11am for best results
```

### Weekly Patterns
```
/timeline --weekly-patterns
```

Shows day-of-week effects:
```
WEEKLY PATTERNS:

Monday: 6.2 events/day (slower start)
Tuesday: 8.9 events/day (peak productivity)
Wednesday: 8.7 events/day (high)
Thursday: 7.3 events/day (declining)
Friday: 6.1 events/day (winding down)
Saturday: 2.8 events/day (weekend)
Sunday: 2.1 events/day (weekend)

Recommendation: Tuesday-Wednesday are your peak productivity days
              Front-load important decisions to these days
```

## Visualization Options

### ASCII Timeline (Default)
```
/timeline --format ascii
```

Compact, readable timeline with ASCII symbols.

### ASCII Heatmap
```
/timeline --format heatmap --days 30
```

Heat map showing activity intensity:
```
ACTIVITY HEATMAP - Last 30 Days

      Mon  Tue  Wed  Thu  Fri  Sat  Sun
Wk 1  ░░░  ███  ███  ██░  ░░░  ░░░  ░░░
Wk 2  ░░░  ███  ███  ██░  ░░░  ░░░  ░░░
Wk 3  ░░░  ███  ███  ░░░  ░░░  ░░░  ░░░
Wk 4  ░░░  ███  ███  ██░  ░░░  ░░░  ░░░

Dark = High activity, Light = Low activity
Peak activity: Tuesday-Wednesday mornings
```

### Interactive Mode (CLI only)
```
/timeline --interactive
```

Navigate timeline with keyboard (if in interactive mode).

## Tips & Best Practices

### 1. Regular Review
Check timeline weekly:
```
/timeline --days 7 --analyze-patterns
```

### 2. Find Your Peak Times
Identify when you're most productive:
```
/timeline --find-productive-hours
```

### 3. Discover Success Patterns
Learn what works:
```
/timeline --outcome success --analyze-patterns
```

### 4. Causal Analysis
Understand cause-effect in your work:
```
/timeline --find-chains --window 2h
```

### 5. Workload Monitoring
Track sustainable pace:
```
/timeline --analyze-workload --days 30
```

## Related Commands

- `/memory-query` - Search events by content
- `/consolidate` - Consolidate timeline insights
- `/memory-health` - Overall memory health
- `/learning` - Learning patterns over time

## See Also

- **Time Series Analysis:** Pattern detection in temporal data
- **Causality Inference:** Finding cause-effect relationships from timestamps
- **Circadian Patterns:** Daily and weekly work rhythm
- **Event Clustering:** Grouping related temporal events
