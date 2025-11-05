# strategy-selector

Auto-triggered skill to auto-select best decomposition strategy from 9 options.

## Purpose

Intelligently selects optimal decomposition strategy from 9 patterns based on:
- Task complexity and characteristics
- Resource constraints
- Timeline pressures
- Team capabilities
- Risk factors

## When Auto-Triggered

Automatically activates when:
- New complex task created
- Goal activation requires decomposition
- User invokes `/decompose-with-strategy --auto-select`
- Planning-orchestrator requests guidance
- Previous strategy underperforms

## Capabilities

### Task Analysis
- Analyzes task characteristics
- Assesses complexity (LOW, MEDIUM, HIGH, CRITICAL)
- Evaluates uncertainty level
- Estimates risk factors
- Checks resource constraints

### Strategy Scoring
- Scores all 9 strategies (0-10)
- Weights by task characteristics
- Ranks by fit
- Provides confidence score
- Lists trade-offs

### Strategy Patterns

1. **HIERARCHICAL** - For architectural/design tasks
   - Characteristics: Complex architecture, clear structure
   - Best for: System design, framework selection
   - Score boost: +2 if complex architecture

2. **ITERATIVE** - For MVP-first, incremental approach
   - Characteristics: Unclear requirements, tight timeline
   - Best for: Startups, MVPs, user research first
   - Score boost: +2 if uncertain requirements

3. **SPIKE** - For research/prototype-dominant work
   - Characteristics: High uncertainty, technical unknown
   - Best for: New technologies, POC, research
   - Score boost: +3 if high uncertainty

4. **PARALLEL** - For independent components
   - Characteristics: Multiple independent modules
   - Best for: Multi-team work, modular systems
   - Score boost: +2 if >2 independent components

5. **SEQUENTIAL** - For strict linear dependencies
   - Characteristics: Strong dependencies, ordered
   - Best for: Step-by-step processes
   - Score boost: +1 if clear ordering

6. **DEADLINE_DRIVEN** - For time-critical work
   - Characteristics: Very tight deadline
   - Best for: Emergency fixes, P0 issues
   - Score boost: +3 if deadline < 2 days

7. **QUALITY_FIRST** - For safety/security critical
   - Characteristics: Security/reliability critical
   - Best for: Authentication, payments, healthcare
   - Score boost: +3 if security/safety critical

8. **COLLABORATIVE** - For team-coordinated work
   - Characteristics: Large team, coordination critical
   - Best for: Team projects, distributed work
   - Score boost: +2 if >3 team members

9. **EXPLORATORY** - For innovation/experimentation
   - Characteristics: Innovation desired, multiple approaches
   - Best for: R&D, new markets, experimentation
   - Score boost: +2 if innovation goal

## Auto-Triggers

```yaml
strategy_selector:
  # Trigger on decomposition request
  on_decompose_request:
    enabled: true
    condition: "task_complexity > 5"  # Only for complex tasks
    action: auto_select_strategy

  # Trigger when strategy underperforms
  on_strategy_underperformance:
    enabled: true
    condition: "health < 0.6 AND execution_time > 1.5x planned"
    action: suggest_strategy_change

  # Trigger on resource change
  on_resource_change:
    enabled: true
    condition: "available_resources changed OR timeline changed"
    action: reevaluate_strategy
```

## Output

When activated, strategy-selector produces:

### Strategy Recommendation
- Selected strategy with confidence
- Score breakdown
- Reasoning and rationale
- Key characteristics matched
- Risk assessment

### Alternative Strategies
- Top 3 alternatives ranked
- Why they're secondary
- When to use each

### Implementation Plan
- Phases with strategy guidance
- Milestones aligned to strategy
- Quality gates specific to strategy
- Resource allocation

## Example Output

```
[strategy-selector] Task: "Implement real-time collaboration"

🎯 Strategy Analysis
───────────────────
Complexity: HIGH (real-time, WebSocket, sync)
Uncertainty: MEDIUM (some WebSocket unknowns)
Timeline: 14 days
Team: 2 senior engineers
Risk: MEDIUM (reliability critical)

Strategy Scores:
───────────────
🥇 PARALLEL (Score: 8.7/10) ← RECOMMENDED
   Rationale: 4 independent components
   - WebSocket layer
   - State sync
   - Conflict resolution
   - UI integration
   → Can work in parallel (2 engineers)

🥈 SPIKE (Score: 7.2/10)
   Alternative: Research WebSocket frameworks first
   → Consider if high technical uncertainty

🥉 HIERARCHICAL (Score: 6.8/10)
   Alternative: Design-first approach
   → Lower risk, but slower to MVP

Confidence: 8.7/10 (High)

Implementation Plan:
───────────────────
Phase 1: Setup & Spike (2 days) [Both together]
  - Architecture review
  - Framework selection
  → Milestone: "Architecture Decided"

Phase 2: Parallel Implementation (7 days) [SPLIT]
  - Engineer A: WebSocket + Event stream
  - Engineer B: State sync + Conflict resolution
  → Milestone: "Core Features Working"

Phase 3: Integration (3 days) [Both]
  - Merge components
  - Integration testing
  → Milestone: "Integration Complete"

Phase 4: Quality (2 days) [Both]
  - Load testing
  - Reliability testing
  → Milestone: "Production Ready"
```

## Integration with Other Components

**With strategy-orchestrator (agent)**:
- Skill provides automatic selection
- Agent provides explicit reasoning

**With goal-orchestrator**:
- Receives goal context
- Provides strategy for decomposition

**With learning-monitor**:
- Reports strategy outcomes
- Feeds back to selection model

## MCP Tools Used

- `decompose_with_strategy()` - Execute strategy
- `check_goal_conflicts()` - Validate constraints
- `get_workflow_status()` - Check resources

## Configuration

```yaml
strategy_selector:
  enabled: true
  auto_select: true            # Auto-pick best strategy
  min_complexity_threshold: 5  # Only complex tasks
  show_alternatives: true      # Show top 3
  learning_enabled: true       # Learns from outcomes
  effectiveness_weights:       # Strategy learning weights
    quality: 0.5
    speed: 0.3
    team_morale: 0.2
```

## Related Skills

- **strategy-orchestrator** (agent version with reasoning)
- **goal-state-tracker** - Monitors strategy effectiveness
- **priority-calculator** - Ranks by urgency (affects strategy)
- **workflow-monitor** - Tracks execution

## See Also

- Phase 3 Executive Functions: Task Decomposition
- `/decompose-with-strategy` command
- strategy-orchestrator agent
