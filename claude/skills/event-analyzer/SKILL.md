---
name: event-analyzer
description: Analyze temporal patterns and causal relationships from episodic events
trigger: SessionEnd, /timeline command, periodic analysis (daily)
confidence: 0.81
---

# Event Analyzer Skill

Analyzes episodic events chronologically, detects temporal patterns, and infers causal relationships between events.

## When I Invoke This

I detect:
- Session ending (review session events)
- User runs `/timeline` command
- Periodic daily analysis (automatic)
- Sufficient events accumulated (20+)
- Pattern detection possible (2+ similar events)

## What I Do

```
1. Retrieve episodic events
   → Call: recall_events() to get recent events
   → Filter: By date range (day, week, or session)
   → Include: All event types (action, conversation, file_change, etc.)
   → Sort: Chronologically by timestamp

2. Detect temporal patterns
   → Cluster: Similar events (e.g., 3x auth-related edits)
   → Measure: Frequency (e.g., JWT changes every 2 hours)
   → Measure: Duration (e.g., 4-hour debugging session)
   → Identify: Recurring cycles (morning patterns, end-of-day)
   → Score: Pattern significance (importance ranking)

3. Infer causal relationships
   → Check: Temporal proximity (<5min = "immediately_after")
   → Check: File overlap (same files affected)
   → Check: Semantic relatedness (related tasks)
   → Build: Causal chains (Event A → B → C)
   → Score: Causal confidence (0.0-1.0)

4. Identify insights
   → Bottlenecks: Tasks taking unexpectedly long
   → Patterns: Recurring issues or workflows
   → Trends: Changing frequency/complexity over time
   → Inefficiencies: Repeated similar activities
   → Success: What works and when

5. Generate analysis
   → Call: create_entity() for patterns found
   → Call: create_procedure() for repeated workflows
   → Call: add_observation() to document findings
   → Return: Comprehensive temporal analysis report
```

## MCP Tools Used

- `recall_events` - Get episodic events by timeframe
- `get_timeline` - Chronological event list
- `smart_retrieve` - Find related memories
- `create_entity` - Create pattern entity
- `create_procedure` - Auto-create workflows
- `add_observation` - Document findings
- `record_event` - Track analysis completion

## Configuration

```
TEMPORAL_PROXIMITY:
  immediate: <5 minutes (strongly causal)
  short_term: 5-60 minutes (likely causal)
  medium_term: 1-24 hours (possible causality)

PATTERN_THRESHOLDS:
  min_frequency: 2 occurrences to consider pattern
  significance_threshold: 0.6 (pattern importance)
  recency_weight: 0.3 (recent patterns valued more)

CAUSAL_SCORING:
  temporal_proximity: 0.5 (if events close in time)
  file_overlap: 0.3 (if same files affected)
  semantic_similarity: 0.2 (if related content)
```

## Example Invocation

```
User: /timeline --analyze

Event Analyzer processing 127 events from past 7 days...

═════════════════════════════════════════════════════════════
TEMPORAL PATTERN ANALYSIS: Past 7 Days
═════════════════════════════════════════════════════════════

📅 EVENT SUMMARY:
  Total Events: 127
  Sessions: 7 (one per day)
  Duration: Mon Oct 21 - Sun Oct 27
  Event Types: 47 file_change, 38 action, 29 conversation, 13 other

═════════════════════════════════════════════════════════════

🔄 RECURRING PATTERNS DETECTED (6 patterns):

1. Daily Morning JWT Debugging Cycle
   Frequency: 7/7 days (happens every day)
   Time: 9:00 AM - 11:30 AM
   Duration: 2.5 hours average
   Pattern:
     a) Read JWT implementation (5 min)
     b) Identify bug (15 min)
     c) Fix implementation (30 min)
     d) Run tests (20 min)
     e) Debug test failures (60 min) ⚠️ BOTTLENECK
     f) Document fix (10 min)
   Causal Chain: Auth Error → Code Review → Testing → Debugging
   Confidence: 0.94 (Very High - happens identically each day)

   Insight: Bottleneck at testing/debugging (60min)
   Recommendation: Invest in test setup optimization
   Created Procedure: jwt-daily-fix-workflow

2. Wednesday Code Review Sessions
   Frequency: 3/3 Wednesdays
   Time: 2:00 PM - 3:30 PM
   Duration: 1.5 hours
   Pattern:
     a) Read recent code changes (10 min)
     b) Comment on PRs (30 min)
     c) Document patterns (25 min)
   Causal Chain: Code Review → Documentation
   Confidence: 0.87 (High - strong weekly pattern)

   Insight: Regular code review good practice
   Recommendation: Maintain weekly review schedule

3. Friday Consolidation & Reflection
   Frequency: 2/2 Fridays
   Time: 4:00 PM - 5:30 PM
   Duration: 1.5 hours
   Pattern:
     a) Review week's events (/timeline)
     b) Extract patterns
     c) Document learnings
     d) Update procedures
   Causal Chain: Consolidation → Learning → Documentation
   Confidence: 0.91 (Very High - intentional routine)

   Insight: Weekly consolidation shows learning investment
   Recommendation: Maintain Friday consolidation routine

4. Multi-Step Authentication Implementation (Across 3 days)
   Frequency: 1 sequence (Oct 23-25)
   Total Duration: 8 hours across 3 days
   Events in Chain: 19 events, 8 related files
   Pattern:
     a) Design phase (Oct 23, 2h) → 6 conversation events
     b) Implementation (Oct 24, 4h) → 12 file changes
     c) Testing phase (Oct 25, 2h) → 8 test runs
   Causal Chain: Design → Implementation → Testing
   Confidence: 0.96 (Very High - clear dependency chain)

   Insight: Large features require multi-day implementation
   Recommendation: Plan 3-day blocks for complex features
   Created Procedure: authentication-implementation-workflow

5. Error Recovery Pattern (Performance Optimization)
   Frequency: 4 occurrences
   Duration: 45 min average
   Pattern:
     a) Notice performance issue (5 min)
     b) Profile code (15 min)
     c) Identify bottleneck (10 min)
     d) Implement optimization (25 min)
     e) Re-test (10 min)
   Causal Chain: Detection → Profiling → Optimization
   Confidence: 0.82 (High - consistent approach)

   Insight: Performance optimization has proven workflow
   Recommendation: Formalize as procedure, use for future optimizations
   Created Procedure: performance-optimization-workflow

6. Research Synthesis Sessions
   Frequency: 2 full sessions
   Duration: 3-4 hours per session
   Pattern:
     a) Parallel research (8 sources) (2h)
     b) Cross-reference findings (30 min)
     c) Create synthesis (30 min)
     d) Document insights (30 min)
   Causal Chain: Research Gathering → Cross-ref → Synthesis
   Confidence: 0.78 (Medium-High - only 2 samples)

   Insight: Research synthesis takes ~4 hours total
   Recommendation: Block 4-hour time slots for research
   Created Procedure: research-synthesis-workflow

═════════════════════════════════════════════════════════════

⏱️  TEMPORAL BOTTLENECKS (what slows progress):

1. JWT Testing/Debugging (CRITICAL) - 60 min daily
   Affected: Daily auth work
   Root Cause: Complex test setup, edge cases in validation
   Historical: Happens every single day
   Impact: Extends morning session by 1 hour
   Recommendation: Invest 2-3 hours to improve test infrastructure
   Potential Savings: -30 min/day = 3.5 hours/week

2. Code Review Setup (MODERATE) - 10 min per session
   Affected: Wednesdays
   Root Cause: Need to context-switch, load PR information
   Impact: Delays code review start
   Recommendation: Pre-load PR list, create review checklist
   Potential Savings: -5 min/week

3. Performance Profiling (MODERATE) - 15 min per occurrence
   Affected: 4 occurrences in past week
   Root Cause: Manual profiling, analysis of results
   Impact: Extends debugging sessions
   Recommendation: Create profiling script, automate analysis
   Potential Savings: -60 min/week at scale

═════════════════════════════════════════════════════════════

📈 TEMPORAL TRENDS (changing over time):

1. Session Duration Trending ↗️ UP
   Week 1: Avg 4.5 hours/day
   Week 2: Avg 5.0 hours/day (+11%)
   Trend: Increasing session length
   Analysis: Due to larger features (3-day multi-step tasks)
   Recommendation: Plan longer sessions for complex work

2. Consolidation Frequency ✅ STABLE
   Sessions with consolidation: 2/7 (29%)
   Target: 1-2/week (14-29%) ✅ On target
   Trend: Consistent consolidation practice
   Recommendation: Continue current routine

3. Context Switching Frequency ↘️ DOWN
   Week 1: 8 context switches/day
   Week 2: 5 context switches/day (-37%)
   Trend: Improving focus
   Analysis: Longer focused sessions on single features
   Recommendation: Maintain focus blocks, consolidate at end

4. Test Coverage Trending → STABLE
   Average: 85% code coverage
   Range: 78-92%
   Trend: Stable around 85%
   Recommendation: Target 90%+ on critical auth code

═════════════════════════════════════════════════════════════

🔗 CAUSAL RELATIONSHIPS INFERRED:

Strong Causality (Confidence >0.85):
  1. Design Document → Implementation (wait 1 day)
     Files: Same (auth/jwt.ts)
     Events: 6 design conversations → 12 implementation changes
     Lag: 1 day
     Confidence: 0.96

  2. Code Change → Test Run (immediate, <5 min)
     Files: Always paired changes
     Temporal: <5 min between
     Confidence: 0.98 (happens every time)

  3. Test Failure → Debugging (immediate)
     Files: Test + implementation files
     Temporal: <2 min between
     Confidence: 0.97

  4. Bug Fix → Documentation (same day)
     Files: Code + doc files
     Temporal: Same session
     Confidence: 0.87

Medium Causality (Confidence 0.70-0.85):
  1. Research Session → Consolidation (1-2 day lag)
  2. Performance Issue → Optimization (same day)
  3. Code Review → Refactoring (1-3 day lag)

═════════════════════════════════════════════════════════════

📊 ANALYSIS METRICS:

Pattern Detection Accuracy: 6 patterns found (expected 5-8)
Causal Chain Confidence: Avg 0.89 (very high)
Bottleneck Identification: 3 critical bottlenecks found
Procedure Generation: 4 new procedures created
Temporal Coverage: 100% (all events analyzed)

═════════════════════════════════════════════════════════════

✅ ANALYSIS COMPLETE

Actions Taken:
  ✓ Created 4 new procedures from patterns
  ✓ Identified 3 bottlenecks for optimization
  ✓ Documented 6 recurring patterns
  ✓ Inferred 10+ causal relationships
  ✓ Tracked temporal trends (6 metrics)

Recommendations Summary:
  HIGH PRIORITY: Fix JWT testing bottleneck (3.5h/week savings)
  MEDIUM: Optimize performance profiling (60 min/week savings)
  LOW: Pre-load code review information (5 min/week savings)

Next Analysis: Tomorrow after session ends
```

## Expected Benefits

```
Pattern Recognition: Identify recurring workflows automatically
Bottleneck Detection: Surface performance issues proactively
Causal Understanding: Understand dependencies and causality
Procedure Learning: Extract workflows from patterns
Optimization: Improve processes based on temporal data
Time Estimation: Better estimates for similar future work
```

## Performance

- Event retrieval: <500ms (via cached timeline)
- Pattern clustering: 1-3s
- Causal inference: 2-5s
- Procedure generation: 1-2s
- Total analysis: <15s

## Integration Points

- Works with: `/timeline` command (events visualization)
- Triggered by: SessionEnd hook (auto-analyze daily)
- Triggered by: `/timeline --analyze` (on-demand)
- Feeds into: workflow-learner skill (pattern → procedure)
- Feeds into: consolidation-trigger (temporal learning)

## Temporal Relationships Tracked

```
Immediate Causality (<5 min):
  - Code change → test run
  - Test failure → debugging
  - Error detection → investigation

Short-term Causality (5-60 min):
  - Problem identification → solution implementation
  - Feature design → implementation start
  - Testing → documentation

Medium-term Causality (1-24h):
  - Design session → implementation session (next day)
  - Implementation → code review
  - Feature completion → consolidation

Long-term Patterns (1-7 days):
  - Weekly review sessions
  - Daily debugging cycles
  - Multi-day feature implementation
```

## Limitations

- Requires 20+ events for meaningful analysis
- Causality is inferred, not guaranteed
- Works best with consistent work patterns
- External factors (meetings, interruptions) not detected
- Temporal patterns need 2+ samples to identify

## Related Commands

- `/timeline` - View events chronologically (with analysis)
- `/consolidate` - Consolidate findings from analysis
- `/procedures` - View/manage extracted procedures
- `/learning` - Review learning effectiveness

## Success Criteria

✓ Detects 5+ recurring patterns per week
✓ Identifies all major bottlenecks
✓ Infers causal relationships with >0.80 confidence
✓ Auto-extracts applicable procedures
✓ Tracks temporal trends accurately
✓ Provides actionable optimization recommendations
