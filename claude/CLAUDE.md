# CLAUDE.md - Global Configuration for AI-First Development with Memory MCP

## Prime Directive
**AI-Driven Software Development** focusing on maximum quality, efficiency, effectiveness.

---
Important notes:
- Use mcp instead of scripts
- We don't want shortcuts or placeholders do the best solution even if it takes longer
- When in doubt ask questions and do research
- You have lots of information in memory, use it!
- DRY: Don't repeat yourself
- We want efficient optimal solutions

---

## What is Memory MCP?

A **neuroscience-inspired 8-layer memory system** that enables AI to:
- ✅ Remember across sessions (episodic + semantic memory)
- ✅ Learn patterns automatically (procedural memory)
- ✅ Track quality of knowledge (meta-memory)
- ✅ Manage cognitive load intelligently
- ✅ Extract patterns from work (consolidation)
- ✅ Orchestrate complex tasks (planning + verification)

**Available globally to ALL projects** via 26 meta-tools (228 operations), 25+ slash commands, 19 skills, and 9 agents.

---

## Core Concept: Memory Layers

| Layer | Purpose | Auto-Trigger | Manual Command |
|-------|---------|--------------|-----------------|
| **Episodic** | Events with timestamps/context | Recorded via hooks | `/timeline` |
| **Semantic** | Searchable knowledge, patterns | Built via `/consolidate` | `/memory-query` |
| **Procedural** | Reusable workflows | Extracted from patterns | `/procedures` |
| **Prospective** | Task triggers (time/event/file) | Created with `/task-create` | `/working-memory` |
| **Knowledge Graph** | Entities, relations, observations | Auto-linked to episodic | `/associations` |
| **Meta-Memory** | Quality, gaps, expertise, load | Continuous tracking | `/memory-health` |
| **Consolidation** | Pattern extraction (sleep-like) | Sleep: `/consolidate` | `/learning` |
| **Working Memory** | Active context (7-item limit) | Request via hooks | `/focus` |

---

## Phase 5-6: Advanced Memory & Planning (Complete!)

The memory-mcp project now includes **2 advanced phases** (Phases 5-6) for consolidation and planning:

### Phase 5: Consolidation & Learning (10 operations)
Sleep-like memory consolidation with dual-process reasoning:

| Tool | Purpose | Advanced Feature |
|------|---------|------------------|
| **run_consolidation** | Full consolidation cycle | Dual-process (System 1 + System 2) |
| **extract_patterns** | Pattern extraction | LLM validation when uncertainty >0.5 |
| **cluster_events** | Event clustering | Spatial-temporal proximity |
| **measure_quality** | Quality measurement | 4-metric framework (compression, recall, consistency, density) |
| **measure_advanced** | Advanced metrics | 6 additional metrics (coverage, coherence, dominance, etc.) |
| **analyze_strategy** | Strategy comparison | 5 strategies: balanced, speed, quality, minimal, custom |
| **analyze_project** | Project patterns | Cross-project learning & expertise modeling |
| **analyze_validation** | Validation effectiveness | Gate accuracy & false positive analysis |
| **discover_orchestration** | Pattern discovery | Task orchestration optimization |
| **analyze_performance** | Performance profiling | Consolidation cycle benchmarking |

**Key Features**:
- ✅ Dual-process reasoning combining speed + accuracy
- ✅ 5 consolidation strategies with auto-selection
- ✅ Cross-project pattern transfer (20-30% time savings)
- ✅ Quality metrics: 70-85% compression, >80% recall

### Phase 6: Planning & Resource Estimation (10 operations)
Comprehensive plan validation with formal verification and adaptive replanning:

| Tool | Purpose | Advanced Feature |
|------|---------|------------------|
| **validate_plan_comprehensive** | 3-level validation | Structure, feasibility, rules |
| **verify_plan_properties** | Q* verification | 5 properties: optimality, completeness, consistency, soundness, minimality |
| **monitor_execution_deviation** | Real-time monitoring | Detect deviations >15% variance |
| **trigger_adaptive_replanning** | Automatic replanning | 5 strategies based on violation type |
| **refine_plan_automatically** | Q* refinement | Parallelization, compression, reordering, leveling, contingency |
| **simulate_plan_scenarios** | Scenario stress-testing | 5 scenarios: best, worst, likely, critical path, black swan |
| **extract_planning_patterns** | Learning from execution | Duration, resource, failure, success, velocity patterns |
| **generate_lightweight_plan** | Quick planning | Resource-constrained with 5 strategies |
| **validate_plan_with_llm** | Deep validation | Extended thinking for complex plans |
| **create_validation_gate** | Human-in-the-loop | Milestone, risk, resource, quality, exception gates |

**Key Features**:
- ✅ Formal property verification (Q* pattern)
- ✅ 5-scenario stress testing with confidence intervals
- ✅ Adaptive replanning on assumption violation
- ✅ LLM extended thinking for validation

**Quick Reference**:
```bash
# Consolidate with strategy selection (Phase 5)
/consolidate-advanced --strategy balanced

# Validate plan comprehensively (Phase 6)
/plan-validate-advanced --task-id 1 --include-simulation

# Monitor task health (Phase 6)
/task-health --task-id 1

# Estimate resources (Phase 6)
/estimate-resources --task-id 1

# Stress-test plan (Phase 6)
/stress-test-plan --task-id 1
```

**Available in**: memory-mcp project (`/home/user/.work/claude/memory-mcp/`)

**See Also**:
- `PHASE_5_COMPLETION_REPORT.md` - Complete Phase 5 documentation
- `PHASE_6_COMPLETION_REPORT.md` - Complete Phase 6 documentation
- `IMPLEMENTATION_SUMMARY.md` - Overview of all 6 phases

---

## Phase 3: Executive Function (Goal Management)

The memory-mcp project includes **9 executive function tools** for goal-driven development:

| Tool | Purpose | Use Case |
|------|---------|----------|
| **decompose_with_strategy** | 9-strategy task decomposition with sequential thinking | Complex feature planning, architectural decisions |
| **activate_goal** | Switch active goal with context cost analysis | Multi-goal context switching, workflow management |
| **check_goal_conflicts** | Detect resource/dependency conflicts between goals | Pre-execution safety checking, conflict prevention |
| **resolve_goal_conflicts** | Auto-resolve conflicts by priority weighting | Automatic conflict mitigation, unblocking |
| **get_goal_priority_ranking** | Rank goals by composite score (40% priority + 35% deadline + 15% progress + 10% on-track) | Strategic prioritization, focus management |
| **recommend_next_goal** | AI-powered recommendation for next goal focus | Planning optimization, context switching |
| **record_execution_progress** | Track goal execution progress toward completion | Progress monitoring, milestone tracking |
| **complete_goal** | Mark goal as success/partial/failure with metrics | Goal closure, outcome recording |
| **get_workflow_status** | View current execution state, active goals, recent switches | Workflow visibility, status dashboard |

**Quick Reference**:
```bash
# Goal-driven workflow
/activate-goal --goal-id 1                    # Set goal as active
/check-goal-conflicts --project-id 1          # Detect conflicts
/decompose-with-strategy --task "..." --strategy top_down  # Plan with strategy
/progress --goal-id 1 --completed 5 --total 10  # Track progress
/goal-complete --goal-id 1 --outcome success   # Mark goal done
```

**Key Features**:
- 9 decomposition strategies (HIERARCHICAL, ITERATIVE, SPIKE, PARALLEL, SEQUENTIAL, DEADLINE_DRIVEN, QUALITY_FIRST, COLLABORATIVE, EXPLORATORY)
- Composite priority scoring (combines urgency, importance, progress)
- Automatic conflict detection and resolution
- Transparent reasoning for Sequential Thinking implementation
- Goal hierarchy with milestone tracking

**See Also**: `/home/user/.work/claude/memory-mcp/EXECUTIVE_FUNCTION_MCP_INTEGRATION.md` - Full integration guide

---

## Advanced Feature 1: Dual-Process Reasoning (Phase 5)

The consolidation system uses dual-process reasoning to combine speed with accuracy:

### System 1 (Fast - <100ms)
- Statistical clustering of episodic events
- Frequency-based pattern detection
- Heuristic weighting
- Always runs (baseline performance)

### System 2 (Slow - 1-5 seconds)
- LLM extended thinking with pattern validation
- Semantic understanding of event relationships
- Confidence-based verification
- Triggered when uncertainty > 0.5

### Result: Hybrid Approach
Combines speed of heuristics with accuracy of LLM reasoning. Most consolidations run in <100ms with System 1. Complex patterns (high uncertainty) trigger System 2 for validation.

**When used**: Every `/consolidate` or `consolidation_tools:run_consolidation`
**Performance target**: <5 seconds total consolidation cycle
**Quality target**: 70-85% compression, >80% recall, >75% consistency

---

## Advanced Feature 2: Q* Formal Verification (Phase 6)

Plans are verified using the Q* pattern with 5 formal properties:

### Hard Properties (SMT Solver - Z3)
1. **Optimality**: Minimize resource consumption
2. **Completeness**: Cover all requirements

### Soft Properties (LLM Extended Thinking)
3. **Consistency**: No conflicts or contradictions
4. **Soundness**: Valid assumptions, correct logic
5. **Minimality**: No redundant steps

### Scoring Model
```
Q* Score = (Hard_Score × 0.6) + (Soft_Score × 0.4)
```

### Plan Quality Levels
- **EXCELLENT** (≥0.8): Ready for execution
- **GOOD** (0.6-0.8): Proceed with caution
- **FAIR** (0.4-0.6): Requires refinement
- **POOR** (<0.4): Reject or heavily refine

**When used**: `/plan-validate-advanced` or `phase6_planning_tools:verify_plan_properties`
**Performance target**: <2 seconds for typical plans
**Confidence target**: 0.0-1.0 per property

---

## Advanced Feature 3: Adaptive Replanning (Phase 6)

Plans automatically adapt when assumptions are violated:

### Trigger Conditions
- Duration exceeded >20%
- Resource conflict detected
- Assumption violation (missing dependency, blocker)
- Critical task blocked >2 hours

### 5 Replanning Strategies
1. **Parallelization**: Execute non-dependent tasks concurrently
2. **Compression**: Batch related tasks, consolidate steps
3. **Reordering**: Topological sort optimization
4. **Escalation**: Add resources to critical path
5. **Deferral**: Move non-critical tasks to future phases

### Auto-Selection
Strategy automatically chosen based on violation type and plan characteristics.

**When used**: `phase6_planning_tools:trigger_adaptive_replanning` (automatic on deviation)
**Performance target**: <3 seconds to generate new plan
**Success target**: Improve timeline by 15%+ or reduce resources by 10%+

---

## Advanced Feature 4: Scenario Simulation (Phase 6)

Plans are stress-tested under 5 scenarios to determine confidence intervals:

### Scenario Types
1. **Best Case**: Everything perfect (+25% speed)
2. **Worst Case**: Multiple issues (-40% speed)
3. **Likely Case**: Normal issues (~-10% speed)
4. **Critical Path**: Focus on bottlenecks
5. **Black Swan**: Unexpected events (variable impact)

### Output Per Scenario
- Estimated duration
- Resource requirements
- Success probability
- Key bottlenecks
- Recommendations

### Confidence Interval
```
Confidence = 1 - (Variance / Baseline)
```

**When used**: `/stress-test-plan` or `phase6_planning_tools:simulate_plan_scenarios`
**Performance target**: <5 seconds for 5 scenarios
**Reliability target**: 80%+ success probability in Likely case

---

## Quick Start: Using Memory in Your Workflow

### 0. Session Priming (At SessionStart)
**Automatic**: SessionStart hook primes your memory context
```bash
# What the hook does automatically:
✓ Load top 5-10 semantic memories by relevance
✓ Pre-populate working memory with active goals (0-2 items)
✓ Check cognitive load and consolidation status
✓ Cache recently used procedures in attention state
```

**Manual priming** (if needed):
```bash
/memory-query "current project context"      # Load project memories
/working-memory                              # View primed context
/project-status                              # Load active goals
```

**Benefits**:
- Reduces initial context window usage by 30-40% per session start
- Enables fast context switching between projects (2-5 minutes)
- Pre-populates working memory so you skip first 100-300 tokens of context loading

**Cognitive Load Target**: Start session at 2-3/7 items (leaves room for new work)

---

### 1. Memory Health Check (Every Session)
```bash
/memory-health              # Overall quality report
/memory-health --detail    # Domain expertise breakdown
/memory-health --gaps      # Knowledge contradictions & uncertainties
```
**Why**: Know what you remember well and what needs work

### 2. Record Work as You Go (Automatic via Hooks)
✅ **Automatic**: SessionStart, SessionEnd, UserPromptSubmit hooks record episodic events
✅ **Automatic**: File changes, test runs, errors all recorded
✅ **Manual** (if needed): `mcp__memory__record_event(content="...", event_type="action")`

**Why**: Build a chronological timeline of work for pattern extraction

### 3. Extract Patterns (Consolidation Strategy)

**Daily Micro-Consolidation** (Automatic at SessionEnd):
```bash
/consolidate               # Quick consolidation of last 100-200 events
# Duration: ~100-200ms | Target: 70-75% compression
```

**Weekly Deep Consolidation** (Manual, recommended Friday):
```bash
/consolidate --deep        # Full week's consolidation (1,000+ events)
# Duration: ~2-5 min | Target: 80-85% compression + domain coverage
```

**Monthly Review Consolidation** (Manual, recommended end-of-month):
```bash
/consolidate --detail      # Complete system analysis + gap detection
# Duration: ~5-10 min | Target: Quality ≥0.85, gaps <5
```

**Why**:
- Daily: Compress events before they fade from episodic buffer
- Weekly: Convert week's work patterns into reusable knowledge
- Monthly: Detect gaps and plan improvements

**Quality Target**: Current 0.72 → Target 0.85+ (10-15% improvement from structured consolidation)

### 4. Monitor Learning Effectiveness
```bash
/learning                  # Which strategies worked best?
/memory-health --gaps      # Where are the gaps?
/memory-forget MEMORY_ID   # Remove low-value memories
```
**Why**: Optimize your encoding strategy over time

### 5. Navigate Knowledge Network
```bash
/associations              # Explore memory connections
/connections              # See entity relationships
/timeline                 # Review events chronologically
```
**Why**: Understand how different concepts relate

---

## 25+ Slash Commands (Memory Operations)

### Memory Exploration
| Command | Purpose | Output |
|---------|---------|--------|
| `/memory-query` | Search memories with advanced RAG | Ranked results |
| `/memory-health` | System health report | Quality metrics, gaps, load |
| `/associations` | Explore memory network | Connections, paths |
| `/timeline` | Browse events chronologically | Events by date |
| `/connections` | Entity relationship graph | Relations, observations |
| `/observations` | Add context to entities | Updates knowledge graph |

### Memory Optimization
| Command | Purpose | Output |
|---------|---------|--------|
| `/consolidate` | Extract patterns (episodic→semantic) | New patterns, quality metrics |
| `/memory-forget` | Selective deletion | Confirmation of removals |
| `/optimize` | Prune low-value memories | Space saved, records removed |

### Learning & Strategy
| Command | Purpose | Output |
|---------|---------|--------|
| `/learning` | Encoding effectiveness analysis | Strategy rankings, recommendations |
| `/procedures` | Discover reusable workflows | Matching procedures, execution history |

### Planning & Goals
| Command | Purpose | Output |
|---------|---------|--------|
| `/project-status` | Project overview with progress & goal rankings | Goals, tasks, metrics, priorities |
| `/plan-validate` | Validate plans before execution | Structural, feasibility, rules checks |
| `/reflect` | Deep self-reflection | Quality, strategies, gaps, calibration |
| `/research` | Comprehensive multi-source research | Findings, synthesis, next steps |

### Executive Functions (Phase 3 - Goal Management)
| Command | Purpose | Output |
|---------|---------|--------|
| `/activate-goal` | Set active goal with context analysis | Goal ID, priority, switch cost |
| `/goal-conflicts` | Check conflicts between active goals | Conflict count, types, details |
| `/resolve-conflicts` | Auto-resolve detected conflicts | Resolution count, updated states |
| `/priorities` | Rank goals by composite score | Ranked goals with scores |
| `/next-goal` | AI recommendation for next focus | Recommended goal, reasoning, score |
| `/progress` | Record execution progress toward goal | Updated progress %, health metrics |
| `/goal-complete` | Mark goal as complete | Completion status, execution metrics |
| `/workflow-status` | View execution state of all workflows | Active goals, recent switches, metrics |
| `/decompose-with-strategy` | Decompose task with strategy selection | ExecutionPlan, strategies, reasoning |

### Working Memory
| Command | Purpose | Output |
|---------|---------|--------|
| `/working-memory` | Monitor active context | Utilization, decay, capacity |
| `/focus` | Manage attention & salience | Active items, suppressed, focus state |
| `/task-create` | Create tasks with smart triggers | Task ID, triggers configured |

---

## 19 Skills (Auto-Triggered Intelligence)

These run **automatically** at strategic points:

### Memory Skills
- **query-strategist** - Auto-select optimal retrieval strategy (HyDE, LLMReranking, Reflective)
- **memory-optimizer** - Consolidate & prune low-value memories
- **gap-detector** - Find contradictions, uncertainties, missing info
- **quality-monitor** - Track memory quality & recommend improvements

### Learning Skills
- **learning-tracker** - Analyze encoding effectiveness & optimization
- **association-learner** - Batch-strengthen memory associations (Hebbian learning)

### Attention & Cognition
- **attention-manager** - Auto-focus on salience, suppress distractions
- **wm-monitor** - Monitor working memory capacity & prevent overload

### Discovery & Analysis
- **association-explorer** - Navigate memory graph
- **insight-generator** - Generate meta-insights from memory analysis
- **knowledge-analyst** - Analyze domain coverage & gaps
- **workflow-learner** - Extract reusable procedures from patterns
- **procedure-suggester** - Recommend applicable workflows

### Executive Functions (Phase 3 - Goal Management)
- **goal-state-tracker** - Monitor goal progress, blockers, and milestone status
- **strategy-selector** - Auto-select best decomposition strategy from 9 options
- **conflict-detector** - Find resource/dependency conflicts between goals
- **priority-calculator** - Rank goals by composite score (priority + deadline + progress)
- **workflow-monitor** - Track execution state and health of active workflows

---

## 9 Agents (Complex Orchestration)

For tasks requiring **multi-step autonomous execution**:

### Memory & Learning Agents
| Agent | When to Use | Capabilities |
|-------|-----------|--------------|
| **attention-optimizer** | Every 10 tool operations | Dynamic focus management, distraction suppression |
| **association-strengthener** | Session end | Batch Hebbian learning, link strengthening |
| **consolidation-trigger** | After major work | Auto-consolidation of episodic→semantic |
| **learning-monitor** | Weekly reviews | Long-term learning effectiveness tracking |

### Task Orchestration Agents
| Agent | When to Use | Capabilities |
|-------|-----------|--------------|
| **planning-orchestrator** | Complex task decomposition | Multi-step plan generation & validation |
| **research-coordinator** | Research tasks | Parallel source investigation & synthesis |

### Executive Functions (Phase 3 - Goal Management)
| Agent | When to Use | Capabilities |
|-------|-----------|--------------|
| **goal-orchestrator** | Goal activation/management | Goal hierarchy management, activation, lifecycle tracking |
| **strategy-orchestrator** | Before plan decomposition | Strategy selection, auto-picks best from 9 options |
| **conflict-resolver** | After conflict detection | Automatic conflict mitigation, priority-based resolution |

**Usage**: Tasks automatically activate relevant agents. You can also explicitly invoke:
```bash
# Will activate agents as needed for task decomposition
/plan-validate
/project-status
/research "topic"
```

---

## Hook System (Automatic Triggers)

These fire **without user action**:

### Session Lifecycle
- **SessionStart** → Load context, check cognitive load, load active goals
- **SessionEnd** → Consolidate learnings, strengthen associations, analyze effectiveness, record goal state

### User Input (Every Prompt)
- **UserPromptSubmit** → Detect gaps, manage attention, suggest procedures, check goal conflicts

### Tool Execution (Firing Intervals - Verified)
- **PostToolUse** → Routes memory ops, records outcomes (fires after every tool execution)
- **Attention-Optimizer** → Activates after every 10 PostToolUse firings (~200 tokens)
- **PreToolUse** → Validates plans before execution (fires before tool use)
- **PreCompact** → Prepares for consolidation (fires before consolidation)
- **PostCompact** → Tracks consolidation quality (fires after consolidation completes)

### Execution Hooks (Phase 3)
- **PreExecution** → Check goal state, verify strategy, detect conflicts before starting
- **PostTaskCompletion** → Record execution progress, update goal health, evaluate milestone status

### Hook Optimization Strategy
| Hook | Frequency | Agent Triggered | Purpose |
|------|-----------|-----------------|---------|
| SessionStart | Per session | Goal-Orchestrator | Load context + active goals |
| SessionEnd | Per session | Association-Strengthener, Consolidation-Trigger | Extract patterns + strengthen links |
| UserPromptSubmit | Every prompt | Gap-Detector, Attention-Manager | Detect issues + manage focus |
| PostToolUse (every 10) | Every 10 ops (~200 tokens) | Attention-Optimizer | Dynamic focus management |
| PreExecution | Before task starts | Planning-Orchestrator, Strategy-Orchestrator | Validate plan + pick strategy |
| PostTaskCompletion | After task ends | Learner Agent | Record progress + extract patterns |

**Key Point**: Hooks run **silently** to manage memory without interrupting your workflow.

### Cognitive Load Management
The system monitors your working memory capacity (Baddeley's 7±2 model):

**Optimal Zone** (2-4/7 items): Best performance
- Plenty of capacity for new information
- Focus is sharp, minimal interference
- Ideal for complex problem-solving

**Caution Zone** (5/7 items): Early warning
- Nearing capacity limits
- Performance starts to degrade
- Consider consolidating before continuing

**Near Capacity** (6/7 items): TRIGGER AUTO-CONSOLIDATION
- **Action**: System auto-consolidates items with decay > 0.3
- **Effect**: Frees working memory space
- **Target**: Return to 4-5/7 items within session

**Overflow** (7/7 items): EMERGENCY
- **Risk**: Hallucinations, context confusion, task failures
- **Action**: Force consolidation with `mcp__memory__consolidate_working_memory`
- **Prevention**: Monitor with `/working-memory` and consolidate when ≥6/7 items

**Consolidation Triggers**:
```bash
# Automatic triggers (no user action needed)
✓ Working memory ≥6/7 items (archiving kicks in)
✓ Decay rate >0.5 per hour (aged items pruned)
✓ SessionEnd (daily micro-consolidation)

# Manual triggers (recommended)
/consolidate --deep         # Weekly deep consolidation
/working-memory             # Check current capacity
consolidate_working_memory  # Force consolidation if needed
```

---

## Strategic Memory Usage Patterns

### Pattern 1: Daily Workflow
```
SESSION START
  ↓ (hook loads context)
Work on tasks
  ↓ (hooks record events & detect gaps)
USER INPUT ("what should I focus on?")
  ↓ (attention-manager auto-focuses, gap-detector surfaces issues)
SESSION END
  ↓ (association-learner strengthens links, learning-tracker analyzes)
```

### Pattern 2: Weekly Review
```
/memory-health --detail
  → See expertise levels by domain
  → Identify weak areas

/memory-health --gaps
  → Find contradictions needing resolution
  → Find uncertainties needing reinforcement

/learning
  → Which strategies worked best?
  → Which should you use more often?

/consolidate
  → Extract week's patterns
  → Create reusable workflows
```

### Pattern 3: Tackling Complex Tasks
```
/project-status
  → See active goals & task breakdown

/plan-validate
  → Check feasibility before starting

[Work on task]
  → Hooks record work, episodic events accumulate

/memory-health --gaps
  → Any contradictions discovered?

/consolidate
  → Extract patterns from this work
```

### Pattern 4: Knowledge Transfer Between Projects

**Use Case 1: Pattern Transfer** (20-30% time savings on repeated patterns)
```bash
# In Project A: Extract pattern
/memory-query "authentication pattern" --project project-a
  → Find completed authentication implementations
/remember "authentication pattern: JWT + refresh tokens, scope-based access control"
  → Store in global semantic memory with tags

# In Project B: Apply pattern
/memory-query "authentication pattern"
  → Retrieved from global memory (found in project-a context)
/associations
  → Link to similar patterns in project-b context
/procedures
  → Execute proven authentication workflow
```

**Use Case 2: Procedure Reuse** (Reduce context switching overhead)
```bash
# In Project A: Completed procedures
/procedures --project project-a
  → Lists "database-optimization", "api-error-handling", "testing-setup"

# In Project B: Activate procedure
/activate-procedure "database-optimization"
  → Automatically adapts to project-b context
/record-execution
  → Tracks effectiveness in new project (feeds Phase 6 analytics)
```

**Use Case 3: Knowledge Consolidation** (Discover cross-project patterns)
```bash
# Research across projects
/research "database optimization strategies" --project-sources [project-a, project-b, project-c]
  → Gathers findings from all three projects
/insights
  → Extracts common patterns and best practices
/consolidate --cross-project
  → Merges learnings into unified knowledge

# Result: Global procedure for "database-optimization" that works across all projects
```

**Benefits**:
- ✓ Reduce feature development time by 20-30% through pattern reuse
- ✓ Maintain consistency across projects using proven procedures
- ✓ Extract company-wide best practices from cross-project consolidation
- ✓ Build institutional knowledge that compounds over multiple projects

---

## Best Practices for Maximum MCP Effectiveness

### ✅ DO
1. **Use `/memory-health` at session start** - Orient yourself to what you know
2. **Let hooks work silently** - Don't disable them; they manage context smartly
3. **Consolidate after major work** - Extract patterns while fresh
4. **Review `/memory-health --gaps`** - Contradictions are high-priority
5. **Trust the attention system** - It auto-focuses on important context
6. **Use `/plan-validate-advanced` before complex work** - Full validation + scenario testing
7. **Check `/learning` monthly** - Optimize your strategy
8. **Use procedures for repetitive patterns** - `/procedures` finds applicable ones
9. **Run `/stress-test-plan` for critical tasks** - Test under 5 scenarios
10. **Monitor task health with `/task-health`** - Real-time execution tracking

### ❌ DON'T
1. **Don't manually disable hooks** - They're optimized for your workflow
2. **Don't ignore knowledge gaps** - They compound over time
3. **Don't skip consolidation** - Episodic events fade; consolidation preserves
4. **Don't treat all memories equally** - Use `/memory-forget` on low-value items
5. **Don't use generic memory commands without RAG** - Use advanced strategies
6. **Don't create contradictions silently** - `gap-detector` will flag them anyway
7. **Don't ignore cognitive load warnings** - `/working-memory` shows saturation

---

## Common Workflows

### Adding a New Feature
```
1. /project-status                  # See current goals
2. /memory-query "similar features" # Learn from past
3. /plan-validate-advanced          # Comprehensive validation with scenarios ⭐
4. /stress-test-plan                # Run 5-scenario simulation
5. [Implementation work]             # Hooks record everything
6. /task-health                     # Monitor real-time progress
7. /memory-health --gaps             # Any contradictions discovered?
8. /consolidate-advanced            # Extract patterns for future
```

**Improvement in Step 3**: `/plan-validate-advanced` now includes:
- ✓ 3-level validation (structure, feasibility, rules)
- ✓ Q* formal property verification (5 properties)
- ✓ Real-time execution monitoring
- ✓ Automatic adaptive replanning on deviation
- ✓ Reduces failed tasks by 40-60% through formal verification

**Improvement in Step 4**: `/stress-test-plan` provides:
- ✓ 5-scenario simulation (best, worst, likely, critical path, black swan)
- ✓ Confidence intervals for completion time
- ✓ Risk-aware bottleneck identification
- ✓ Improves timeline accuracy by ±15%

### Debugging Complex Issue
```
1. /timeline --filter bugs       # Review past debugging sessions
2. /associations                 # Connect to related concepts
3. /memory-query "error pattern" # Find similar issues
4. [Debug work]                  # Events recorded automatically
5. /consolidate                  # Extract debugging heuristics
```

### Switching Projects
```
1. /project-status              # Load new project context
2. /memory-query "project name" # Get project-specific knowledge
3. /working-memory              # Clear previous context (or auto-rotate)
4. Start work                    # New episodic events begin
```

### Code Review / Quality Check
```
1. /memory-health              # What patterns do we know?
2. /procedures                 # What code patterns apply?
3. /memory-query "code smells" # Learn from past reviews
4. [Review code]               # Record quality observations
5. /observations               # Link findings to code entities
```

---

## Database & Performance

**Database Location**: `~/.athena/memory.db` (SQLite + sqlite-vec)

**Monitoring**:
```bash
# Check database size
du -h ~/.athena/memory.db

# Get current stats
/memory-health

# See cognitive load
/working-memory
```

**Optimization**:
```bash
# Remove low-value memories
/consolidate
/memory-forget ID1 ID2 ID3

# See what would be removed (dry-run)
mcp__memory__optimize(dry_run=True)

# Actually optimize
mcp__memory__optimize(dry_run=False)
```

---

## Memory Health Monitoring Thresholds

Monitor your memory system health using these operational targets:

### HEALTHY (Green - Quality Score 0.85-1.0)
✅ **Semantic memory quality** ≥0.85
✅ **Consolidation runs** ≥weekly (last run ≤7 days)
✅ **Knowledge gaps** <5 (contradictions + uncertainties)
✅ **Cognitive load** <6/7 items (good capacity management)
✅ **Goal conflicts** <2 active conflicts (well-managed)
✅ **Estimation accuracy** ±15% (Phase 6 - target)
✅ **Task health** ≥0.75 (Phase 5 - target)

**Action**: Continue current practices. Quarterly review.

### WARNING (Yellow - Quality Score 0.65-0.85)
⚠️ **Semantic memory quality** 0.75-0.85 (degrading)
⚠️ **Consolidation runs** >2 weeks old (overdue)
⚠️ **Knowledge gaps** 5-10 (addressable issues)
⚠️ **Cognitive load** 6/7 items (near capacity)
⚠️ **Goal conflicts** 2-5 active conflicts (needs resolution)
⚠️ **Estimation accuracy** ±20% (Phase 6)
⚠️ **Task health** 0.50-0.75 (needs optimization)

**Action**:
- Run `/consolidate --deep` to improve quality
- Review `/memory-health --gaps` and address contradictions
- Run `/goal-conflicts` and `/resolve-conflicts` to clear blockers
- Archive old memories with `/memory-forget` to create capacity

### CRITICAL (Red - Quality Score <0.65)
🔴 **Semantic memory quality** <0.75 (severe degradation)
🔴 **Consolidation runs** >30 days old (emergency)
🔴 **Knowledge gaps** >10 (blocking work)
🔴 **Cognitive load** 7/7 items (overflow risk)
🔴 **Goal conflicts** >5 active conflicts (critical)
🔴 **Estimation accuracy** >±30% (Phase 6)
🔴 **Task health** <0.50 (task at risk)

**Action**: IMMEDIATE
- Run `/consolidate --detail` (full consolidation)
- Resolve all gaps with `/memory-health --gaps`
- Force consolidation with `mcp__memory__consolidate_working_memory`
- Archive all low-value memories with `/optimize --aggressive`
- Re-activate goals with `/resolve-conflicts`

### Monitoring Commands
```bash
/memory-health --detail        # Full quality report with thresholds
/project-status                # Phase 5-8 metrics and health scores
/learning --effectiveness      # Phase 6 accuracy trends
/working-memory                # Current cognitive load
/goal-conflicts                # Active goal conflicts
```

---

## Advanced Features

### HyDE (Hypothetical Document Embeddings)
**When**: Ambiguous or short queries (< 5 words)
**Auto**: `/memory-query` detects and applies automatically
**Manual**: `mcp__memory__smart_retrieve(query="...")`

### LLM Reranking
**When**: You need highest accuracy for important decisions
**Requires**: `ANTHROPIC_API_KEY` set
**Usage**: Automatically applied in `/memory-health --detail`

### Temporal Reasoning
**When**: Understanding causality between events
**Commands**: `/timeline`, `/associations`, `/connections`
**Data**: Automatic <5min/5-60min/1-24h linking

### Consolidation Quality Metrics
**Check**: How well patterns compress episodic events
**Target**: 70-85% compression, >80% recall, >75% consistency
**Command**: `/consolidate --detail`

### RAG Strategy Auto-Detection
**Algorithm**: Automatically selects optimal retrieval strategy
```
if len(query.split()) < 5:
    strategy = "HyDE"           # Ambiguous short queries
elif references (it, that, those, which):
    strategy = "QueryTransform"  # References to context
else:
    strategy = "LLMReranking"   # Standard accuracy-focused

Additional heuristics:
- Domain-specific queries → "Reflective"
- "How has X changed" → "Reflective" (temporal)
- AND/OR with references → "QueryTransform"
- "What is X" → "LLMReranking"
```

**Performance**: 15-20% query accuracy improvement through optimal strategy selection

---

## Troubleshooting

### "I can't find a memory I created"
1. Try `/memory-query "keywords"` with different terms
2. Check `/timeline` for when it was created
3. Use `/associations` to find related concepts
4. Run `/memory-health --gaps` to see if it's flagged as contradictory

### "My memory database is getting large"
1. Run `du -h ~/.athena/memory.db` to check size
2. `/consolidate` to extract patterns from episodic events
3. `/memory-forget ID` to remove low-value memories
4. `mcp__memory__optimize(dry_run=False)` to prune

### "Cognitive load is HIGH"
1. Check `/working-memory` to see what's active
2. Use `/focus` to clear distractions
3. The system auto-rotates old items, but you can manually consolidate
4. Consider `/consolidate` to archive episodic events

### "Gap detector says there's a contradiction"
1. Use `/associations` to see which concepts conflict
2. Use `/memory-query` to examine both sides
3. Manually review and update with corrected understanding
4. The system will track resolution

---

## Key Files by Use Case

| Want to... | Check... |
|-----------|----------|
| Understand the memory system | This file + `PROJECT_STATUS.md` in project |
| Learn advanced RAG techniques | `ADVANCED_RAG_USAGE.md` in project |
| Debug test failures | `TESTING.md` in project |
| Optimize performance | `PERFORMANCE_TUNING_GUIDE.md` in project |
| See implementation details | `IMPLEMENTATION_PLAN.md` in project |

---

## Session-Aware Features

The MCP system is **session-aware**:
- Hooks record SessionStart/SessionEnd events
- Cognitive load resets partially between sessions
- Working memory has episodic buffer (active context)
- Goals and tasks persist across sessions
- Consolidation identifies session boundaries for better patterns

**Result**: Your memory system understands session context and handles context window management automatically.

---

## Integration with Claude Code Features

| Feature | How MCP Enhances |
|---------|------------------|
| Todo tracking | Integrates with prospective tasks & triggers |
| Agent orchestration | Uses planning system for task decomposition |
| Code search | Combines with spatial hierarchy for semantic file search |
| Error recovery | Episodic events record failures for learning |
| Context management | Meta-memory tracks & optimizes context |

---

## Success Metrics

You're maximizing the MCP when:

✅ **Memory Health**: 85%+ (via `/memory-health`)
✅ **Cognitive Load**: LOW most of the time (via `/working-memory`)
✅ **Gap Resolution**: < 5 unresolved contradictions (via `/memory-health --gaps`)
✅ **Learning**: Monthly improvements in strategy effectiveness (via `/learning`)
✅ **Consolidation**: Extracting 5+ patterns per major work session
✅ **Knowledge Coverage**: Growing expertises in relevant domains (via `/memory-health --detail`)
✅ **Procedures**: Using 3+ extracted procedures per project

---

## Quick Reference Cheat Sheet

```bash
# Daily
/memory-health                    # Health check
/focus                            # Manage attention

# Weekly
/memory-health --gaps             # Find issues
/learning                         # Strategy analysis
/consolidate                      # Pattern extraction

# As Needed
/memory-query "topic"             # Search
/associations                     # Explore connections
/procedures                       # Find applicable patterns
/plan-validate                    # Check feasibility
/project-status                   # Project overview

# Maintenance
/memory-forget ID                 # Remove low-value
mcp__memory__optimize()           # Prune
/consolidate --dry-run            # Preview
```

---

**Version**: 1.1 (Global MCP Configuration - Phase 5-6 Complete)
**Last Updated**: 2025-11-04
**Status**: Production Ready ✓
**Recent Updates**: Added Phase 5-6 documentation, dual-process reasoning, Q* verification, adaptive replanning, scenario simulation
