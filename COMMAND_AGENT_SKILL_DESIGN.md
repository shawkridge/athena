# Command, Agent & Skill Redesign - Official Structure

**Date**: November 6, 2025
**Based on**: Official Claude Code documentation + MCP Operation Clusters
**Status**: Design Phase (Ready for Implementation)

---

## Part 1: Official Structure Requirements

### Slash Commands (User-Invoked)
- **Location**: `.claude/commands/[subdirectory/]command-name.md`
- **Format**: Markdown with optional YAML frontmatter
- **Invocation**: `/command-name [arguments]`
- **Features**:
  - `$ARGUMENTS` for all args or `$1`, `$2` for individual args
  - `allowed-tools` to restrict tools (e.g., Bash)
  - `argument-hint` for autocomplete
  - Optional extended thinking

### Agents (Auto-Delegated)
- **Location**: `.claude/agents/agent-name.md`
- **Format**: Markdown with YAML frontmatter (required)
- **Activation**: Claude autonomously delegates OR user invokes via Task tool
- **Configuration**:
  ```yaml
  ---
  name: lowercase-with-hyphens
  description: When/why to use this agent (critical for auto-delegation)
  tools: tool1, tool2 (optional - omit to inherit all)
  model: sonnet|opus|haiku (optional)
  ---
  [System prompt describing agent's role]
  ```

### Skills (Model-Invoked)
- **Location**: `.claude/skills/skill-name/SKILL.md`
- **Format**: YAML frontmatter + Markdown content
- **Activation**: Claude autonomously activates based on description match
- **Structure**:
  ```
  skill-name/
  ├── SKILL.md (required)
  ├── reference.md (optional)
  ├── examples.md (optional)
  └── supporting-files/
  ```

---

## Part 2: MCP Operation Cluster Mapping

### 20 Operation Clusters → Command/Agent/Skill Structure

#### CRITICAL TIER (6 clusters)

| Cluster | Operations | Command(s) | Agent | Skill |
|---------|-----------|-----------|-------|-------|
| **Session Priming** | get_project_status, get_memory_quality_summary, get_working_memory, get_active_goals | `/session-start` | session-initializer | (Skills auto-invoked) |
| **Memory Search** | recall, smart_retrieve, search_projects, recall_events, get_associations | `/memory-search` | research-coordinator | memory-retrieval |
| **Task Planning** | decompose_with_strategy, generate_task_plan, estimate_resources | `/plan-task` | planning-orchestrator | task-decomposition |
| **Goal Management** | set_goal, activate_goal, record_execution_progress, complete_goal | `/manage-goal` | goal-orchestrator | goal-lifecycle |
| **Plan Validation** | validate_plan_comprehensive, verify_plan_properties, simulate_plan_scenarios | `/validate-plan` | plan-validator | plan-verification |
| **Execution Monitoring** | get_task_health, monitor_execution_deviation, trigger_adaptive_replanning | `/monitor-task` | execution-monitor | execution-tracking |

#### IMPORTANT TIER (6 clusters)

| Cluster | Command(s) | Agent | Skill |
|---------|-----------|-------|-------|
| **Consolidation** | `/consolidate` | consolidation-engine | pattern-extraction |
| **Graph Navigation** | `/explore-graph` | knowledge-explorer | graph-navigation |
| **Cognitive Load** | `/check-workload` | attention-manager | load-management |
| **Memory Quality** | `/assess-memory` | quality-auditor | quality-evaluation |
| **Procedural Learning** | `/learn-procedure` | workflow-learner | procedure-creation |
| **Strategy Optimization** | `/optimize-strategy` | strategy-selector | strategy-analysis |

#### USEFUL TIER (6 clusters)

| Cluster | Command(s) | Agent | Skill |
|---------|-----------|-------|-------|
| **Advanced RAG** | `/retrieve-smart` | rag-specialist | semantic-search |
| **Automation** | `/setup-automation` | automation-engine | event-triggering |
| **Code Analysis** | `/analyze-code` | code-analyzer | codebase-understanding |
| **Safety** | `/evaluate-safety` | safety-auditor | change-safety |
| **Cost Planning** | `/budget-task` | resource-optimizer | cost-estimation |
| **System Health** | `/system-health` | system-monitor | performance-monitoring |

#### NICE-TO-HAVE TIER (2 clusters)

| Cluster | Command(s) | Agent | Skill |
|---------|-----------|-------|-------|
| **Agent Optimization** | `/optimize-agents` | meta-optimizer | agent-enhancement |
| **Community Detection** | `/find-communities` | community-detector | connection-discovery |

---

## Part 3: Command Design (User-Invoked)

### Command Naming Convention
Format: `/[tier]-[cluster]-[operation]`
Examples: `/critical-memory-search`, `/important-consolidate`, `/useful-safety-check`

### 20 Recommended Commands

#### CRITICAL Commands (6)
```
/session-start         - Load context at session start
/memory-search         - Find and recall information (with $ARGUMENTS)
/plan-task            - Decompose complex task with strategy ($1 = task description)
/manage-goal          - Create/activate/complete goals ($1 = goal, $2 = action)
/validate-plan        - Comprehensive plan validation with scenarios
/monitor-task         - Real-time execution monitoring ($1 = task_id)
```

#### IMPORTANT Commands (6)
```
/consolidate          - Extract patterns from work (optional: --strategy)
/explore-graph        - Navigate knowledge graph relationships
/check-workload       - Assess cognitive load and capacity
/assess-memory        - Evaluate memory quality and find gaps
/learn-procedure      - Create reusable workflow from experience ($1 = name)
/optimize-strategy    - Analyze and recommend optimal strategies
```

#### USEFUL Commands (6)
```
/retrieve-smart       - Advanced semantic search ($ARGUMENTS = query)
/setup-automation     - Create event-driven automation ($1 = trigger)
/analyze-code         - Deep codebase analysis ($1 = focus_area)
/evaluate-safety      - Assess change safety and risk ($1 = change_description)
/budget-task          - Estimate costs and resources ($1 = task_description)
/system-health        - Check system performance and health
```

#### NICE-TO-HAVE Commands (2)
```
/optimize-agents      - Enhance agent performance (advanced)
/find-communities     - Discover knowledge graph communities (advanced)
```

**Total**: 20 commands mapping to 20 operation clusters

---

## Part 4: Agent Design (Auto-Delegated)

### Agent Naming Convention
Format: `{cluster-name}-{role}`
Examples: `session-initializer`, `planning-orchestrator`, `consolidation-engine`

### 21 Agents (CRITICAL + IMPORTANT + USEFUL)

#### Orchestration Agents
```yaml
---
name: planning-orchestrator
description: |
  Autonomous task planning and decomposition. Use when breaking down
  complex features or projects into executable steps. Selects optimal
  strategy from 9 options and validates plans with Q* verification.
tools: planning_tools, task_management_tools, memory_tools
model: sonnet
---
[System prompt about planning expertise]
```

```yaml
---
name: goal-orchestrator
description: |
  Goal lifecycle management with conflict detection and resolution.
  Use when managing multiple concurrent goals or switching between
  projects. Tracks progress, detects blockers, and updates goal state.
tools: task_management_tools, planning_tools, memory_tools
---
```

```yaml
---
name: consolidation-engine
description: |
  Pattern extraction using dual-process reasoning (fast heuristics + LLM).
  Use after completing work sessions to extract learnings, create procedures,
  and improve semantic memory quality. Target: 70-85% compression, >80% recall.
tools: consolidation_tools, memory_tools, procedural_tools
---
```

#### Execution Agents
```yaml
---
name: execution-monitor
description: |
  Real-time execution tracking with adaptive replanning. Use during active
  work to monitor progress, detect deviations, and automatically adjust
  plans when assumptions are violated. Triggers 5 replanning strategies.
tools: monitoring_tools, planning_tools, task_management_tools
---
```

```yaml
---
name: research-coordinator
description: |
  Multi-source research and knowledge synthesis. Use for complex research
  tasks requiring parallel investigation across multiple knowledge sources.
  Orchestrates and synthesizes findings with confidence levels.
tools: memory_tools, graph_tools, rag_tools
---
```

#### Quality Agents
```yaml
---
name: quality-auditor
description: |
  Memory quality assessment and gap detection. Use to evaluate semantic
  memory health, find contradictions/uncertainties, and guide consolidation.
  Provides 4-metric quality framework (compression, recall, consistency, density).
tools: memory_tools, consolidation_tools
---
```

```yaml
---
name: strategy-selector
description: |
  Optimal strategy recommendation from 9+ options (hierarchical, iterative,
  parallel, sequential, etc.). Use before complex planning to identify the
  best decomposition strategy for your task characteristics.
tools: planning_tools, ml_integration_tools
---
```

#### Analysis Agents
```yaml
---
name: code-analyzer
description: |
  Deep codebase analysis with spatial hierarchy and dependency detection.
  Use when understanding code structure, finding impact of changes, or
  planning refactoring. Provides file structure, import chains, relationships.
tools: spatial_tools, graph_tools, analysis_tools
---
```

```yaml
---
name: knowledge-explorer
description: |
  Knowledge graph navigation and relationship discovery. Use to understand
  how concepts connect, find indirect dependencies, and explore entity
  relationships. Supports Leiden clustering for community detection.
tools: graph_tools, graphrag_tools
---
```

```yaml
---
name: attention-manager
description: |
  Cognitive load management using 7±2 working memory model. Use to manage
  focus, suppress distractions, and maintain optimal working memory capacity.
  Auto-triggers consolidation when near capacity.
tools: memory_tools, metacognition_tools
---
```

#### System Agents
```yaml
---
name: plan-validator
description: |
  Comprehensive plan validation with Q* formal verification and 5-scenario
  stress testing. Use before committing to complex plans. Checks structure,
  feasibility, consistency, and provides confidence intervals.
tools: phase6_planning_tools, planning_tools
---
```

```yaml
---
name: system-monitor
description: |
  System health tracking and performance monitoring. Use to detect bottlenecks,
  analyze critical paths, and identify resource conflicts. Provides health
  scores and optimization recommendations.
tools: monitoring_tools, coordination_tools
---
```

```yaml
---
name: safety-auditor
description: |
  Change safety evaluation and risk assessment. Use before making critical
  changes to assess impact, identify affected components, and evaluate risk
  levels. Recommends approval gates and testing requirements.
tools: safety_tools, code_artifact_tools
---
```

#### Automation & Learning
```yaml
---
name: automation-engine
description: |
  Event-driven automation setup and orchestration. Use to create smart
  triggers (time-based, event-based, file-based) and automate repetitive
  workflows. Learns from execution patterns.
tools: automation_tools, procedural_tools
---
```

```yaml
---
name: workflow-learner
description: |
  Automatic procedure extraction from completed work. Use after finishing
  multi-step tasks to create reusable procedures. Learns best practices
  and success patterns for future similar work.
tools: procedural_tools, consolidation_tools
---
```

#### RAG & Search
```yaml
---
name: rag-specialist
description: |
  Advanced semantic retrieval with 4 strategies (HyDE, reranking, query
  transform, reflective). Use for complex search where you need maximum
  retrieval accuracy. Auto-selects optimal strategy by query type.
tools: rag_tools, memory_tools
---
```

#### Resource Management
```yaml
---
name: resource-optimizer
description: |
  Cost estimation and resource planning. Use for budget tracking, resource
  allocation, and cost optimization across tasks. Identifies cost anomalies
  and suggests optimizations.
tools: financial_tools, coordination_tools
---
```

#### Advanced (Nice-to-have)
```yaml
---
name: meta-optimizer
description: |
  Agent and skill performance optimization. Advanced: tunes agent behavior,
  identifies improvement opportunities, and optimizes system performance.
  Use when fine-tuning the autonomous system.
tools: agent_optimization_tools, skill_optimization_tools
---
```

```yaml
---
name: community-detector
description: |
  GraphRAG community detection and analysis. Advanced: discovers natural
  communities in knowledge graphs, identifies bridge entities, and suggests
  connection optimizations.
tools: graphrag_tools, graph_tools
---
```

```yaml
---
name: session-initializer
description: |
  Session startup context priming. Auto-invoked at session start to load
  relevant context, check cognitive load, and pre-populate working memory
  with active goals. Completes in <500ms.
tools: memory_tools, task_management_tools
---
```

**Total**: 21 agents providing autonomous orchestration across all operation clusters

---

## Part 5: Skill Design (Model-Invoked)

### Skill Naming Convention
Format: `{domain}-{capability}`
Examples: `memory-retrieval`, `task-decomposition`, `pattern-extraction`

### 15 Recommended Skills

Directory structure:
```
.claude/skills/
├── memory-retrieval/
│   ├── SKILL.md
│   ├── strategies.md
│   └── examples.md
├── task-decomposition/
│   ├── SKILL.md
│   ├── strategies.md
│   └── templates.md
[... 13 more skills ...]
```

#### Memory & Knowledge Skills (3)
```yaml
# .claude/skills/memory-retrieval/SKILL.md
---
name: memory-retrieval
description: |
  Retrieve relevant information from memory using advanced RAG strategies.
  Use when you need to find similar past solutions, understand patterns,
  or recall previous implementations. Automatically selects optimal search
  strategy (HyDE for ambiguous queries, LLM reranking for precision, etc.)
allowed-tools: []
---
```

```yaml
# .claude/skills/graph-navigation/SKILL.md
---
name: graph-navigation
description: |
  Navigate knowledge graph relationships to understand dependencies and
  connections. Use when analyzing code impact, finding related concepts,
  or exploring entity relationships. Provides community detection and
  semantic paths between entities.
allowed-tools: []
---
```

```yaml
# .claude/skills/semantic-search/SKILL.md
---
name: semantic-search
description: |
  Advanced semantic search with 4 retrieval strategies. Use for complex
  domain-specific searches where traditional keyword search fails. Handles
  concept-level queries and provides ranked results with confidence.
allowed-tools: []
---
```

#### Planning & Execution Skills (3)
```yaml
# .claude/skills/task-decomposition/SKILL.md
---
name: task-decomposition
description: |
  Break down complex tasks using 9 decomposition strategies (hierarchical,
  iterative, spike-based, parallel, sequential, deadline-driven, quality-first,
  collaborative, exploratory). Use when planning features, bug fixes, or
  architectural changes. Provides structured execution plan with dependencies.
allowed-tools: []
---
```

```yaml
# .claude/skills/plan-verification/SKILL.md
---
name: plan-verification
description: |
  Verify plans using Q* formal verification and 5-scenario stress testing.
  Use before committing to plans for high-risk changes. Checks 5 properties
  (optimality, completeness, consistency, soundness, minimality) and
  simulates best/worst/likely/critical/black-swan scenarios.
allowed-tools: []
---
```

```yaml
# .claude/skills/execution-tracking/SKILL.md
---
name: execution-tracking
description: |
  Track real-time execution with adaptive replanning. Use during work to
  monitor progress, detect deviations, and trigger automatic plan adjustments.
  Monitors deviation from 5 replanning strategies when assumptions violated.
allowed-tools: []
---
```

#### Quality & Learning Skills (3)
```yaml
# .claude/skills/pattern-extraction/SKILL.md
---
name: pattern-extraction
description: |
  Extract patterns using dual-process reasoning (fast statistical clustering
  + slow LLM validation). Use after completing work to consolidate episodic
  events into semantic knowledge. Target: 70-85% compression, >80% recall,
  >75% consistency. Learns when uncertainty warrants LLM validation.
allowed-tools: []
---
```

```yaml
# .claude/skills/quality-evaluation/SKILL.md
---
name: quality-evaluation
description: |
  Evaluate memory quality and identify gaps. Use to assess semantic memory
  health, find contradictions/uncertainties, and guide consolidation.
  Provides 4-metric framework (compression, recall, consistency, density).
allowed-tools: []
---
```

```yaml
# .claude/skills/procedure-creation/SKILL.md
---
name: procedure-creation
description: |
  Create reusable procedures from completed work. Use after finishing
  multi-step tasks to extract learnings as automated procedures.
  Learns best practices, success patterns, and failure recovery steps.
allowed-tools: []
---
```

#### Analysis & Optimization Skills (3)
```yaml
# .claude/skills/codebase-understanding/SKILL.md
---
name: codebase-understanding
description: |
  Analyze codebase structure with spatial hierarchies and dependency graphs.
  Use when understanding code organization, finding change impacts, or
  planning refactoring. Provides file structure, import chains, relationships.
  Works with class, function, module-level analysis.
allowed-tools: []
---
```

```yaml
# .claude/skills/change-safety/SKILL.md
---
name: change-safety
description: |
  Assess change safety and risk. Use before making critical changes to
  evaluate impact, identify affected components, determine risk levels.
  Recommends approval gates, testing requirements, and rollback plans.
allowed-tools: []
---
```

```yaml
# .claude/skills/strategy-analysis/SKILL.md
---
name: strategy-analysis
description: |
  Analyze and recommend optimal strategies from 9+ options. Use when planning
  complex work to identify the best approach. Selects strategy based on task
  characteristics, team size, timeline, and quality requirements.
allowed-tools: []
---
```

#### System & Domain Skills (3)
```yaml
# .claude/skills/load-management/SKILL.md
---
name: load-management
description: |
  Manage cognitive load using 7±2 working memory model. Use to optimize
  focus and manage attention. Auto-consolidates when capacity near maximum.
  Tracks decay rates, interference, and consolidation quality.
allowed-tools: []
---
```

```yaml
# .claude/skills/cost-estimation/SKILL.md
---
name: cost-estimation
description: |
  Estimate task costs and resource requirements. Use for budget tracking,
  resource allocation, and cost optimization. Detects budget anomalies
  and suggests improvements.
allowed-tools: []
---
```

```yaml
# .claude/skills/event-triggering/SKILL.md
---
name: event-triggering
description: |
  Create smart event-driven automation. Use to automate workflows with
  triggers (time-based, event-based, file-based). Learns from execution
  patterns and improves trigger accuracy over time.
allowed-tools: []
---
```

**Total**: 15 skills providing domain expertise across memory, planning, quality, analysis, and system management

---

## Part 6: Integration Matrix

### Command → Agent → Skill Flow

```
User invokes /command
    ↓
Command provides prompt/parameters
    ↓
Claude may auto-invoke relevant Agent
    ↓
Agent uses specific tools from operation clusters
    ↓
Claude may auto-activate relevant Skill
    ↓
Skill provides domain expertise for optimal execution
    ↓
Tools execute MCP operations
    ↓
Results returned to user
```

### Example Workflow: Adding a Feature

```
User: /plan-task "Add authentication system with JWT tokens"
    ↓
planning-orchestrator agent auto-invokes
    ↓
task-decomposition skill auto-activates
    ↓
Decompose with one of 9 strategies selected by strategy-selector agent
    ↓
validate-plan agent invokes for Q* verification
    ↓
plan-verification skill validates structure, feasibility, consistency
    ↓
simulate_plan_scenarios creates 5 scenarios
    ↓
Returns validated plan with confidence level
    ↓
User: /monitor-task <plan_id>
    ↓
execution-monitor agent tracks real-time progress
    ↓
execution-tracking skill detects deviations
    ↓
trigger_adaptive_replanning with 5 strategies as needed
    ↓
Returns task health + adjustments in real-time
```

---

## Part 7: Implementation Checklist

### File Creation Checklist

**Commands** (20 files):
- [ ] `.claude/commands/critical/session-start.md`
- [ ] `.claude/commands/critical/memory-search.md`
- [ ] `.claude/commands/critical/plan-task.md`
- [ ] `.claude/commands/critical/manage-goal.md`
- [ ] `.claude/commands/critical/validate-plan.md`
- [ ] `.claude/commands/critical/monitor-task.md`
- [ ] `.claude/commands/important/consolidate.md`
- [ ] `.claude/commands/important/explore-graph.md`
- [ ] `.claude/commands/important/check-workload.md`
- [ ] `.claude/commands/important/assess-memory.md`
- [ ] `.claude/commands/important/learn-procedure.md`
- [ ] `.claude/commands/important/optimize-strategy.md`
- [ ] `.claude/commands/useful/retrieve-smart.md`
- [ ] `.claude/commands/useful/setup-automation.md`
- [ ] `.claude/commands/useful/analyze-code.md`
- [ ] `.claude/commands/useful/evaluate-safety.md`
- [ ] `.claude/commands/useful/budget-task.md`
- [ ] `.claude/commands/useful/system-health.md`
- [ ] `.claude/commands/advanced/optimize-agents.md`
- [ ] `.claude/commands/advanced/find-communities.md`

**Agents** (21 files):
- [ ] `.claude/agents/planning-orchestrator.md`
- [ ] `.claude/agents/goal-orchestrator.md`
- [ ] `.claude/agents/consolidation-engine.md`
- [ ] `.claude/agents/execution-monitor.md`
- [ ] `.claude/agents/research-coordinator.md`
- [ ] `.claude/agents/quality-auditor.md`
- [ ] `.claude/agents/strategy-selector.md`
- [ ] `.claude/agents/code-analyzer.md`
- [ ] `.claude/agents/knowledge-explorer.md`
- [ ] `.claude/agents/attention-manager.md`
- [ ] `.claude/agents/plan-validator.md`
- [ ] `.claude/agents/system-monitor.md`
- [ ] `.claude/agents/safety-auditor.md`
- [ ] `.claude/agents/automation-engine.md`
- [ ] `.claude/agents/workflow-learner.md`
- [ ] `.claude/agents/rag-specialist.md`
- [ ] `.claude/agents/resource-optimizer.md`
- [ ] `.claude/agents/meta-optimizer.md`
- [ ] `.claude/agents/community-detector.md`
- [ ] `.claude/agents/session-initializer.md`
- [ ] `.claude/agents/error-handler.md`

**Skills** (15 directories):
- [ ] `.claude/skills/memory-retrieval/SKILL.md` + supporting files
- [ ] `.claude/skills/graph-navigation/SKILL.md` + supporting files
- [ ] `.claude/skills/semantic-search/SKILL.md` + supporting files
- [ ] `.claude/skills/task-decomposition/SKILL.md` + supporting files
- [ ] `.claude/skills/plan-verification/SKILL.md` + supporting files
- [ ] `.claude/skills/execution-tracking/SKILL.md` + supporting files
- [ ] `.claude/skills/pattern-extraction/SKILL.md` + supporting files
- [ ] `.claude/skills/quality-evaluation/SKILL.md` + supporting files
- [ ] `.claude/skills/procedure-creation/SKILL.md` + supporting files
- [ ] `.claude/skills/codebase-understanding/SKILL.md` + supporting files
- [ ] `.claude/skills/change-safety/SKILL.md` + supporting files
- [ ] `.claude/skills/strategy-analysis/SKILL.md` + supporting files
- [ ] `.claude/skills/load-management/SKILL.md` + supporting files
- [ ] `.claude/skills/cost-estimation/SKILL.md` + supporting files
- [ ] `.claude/skills/event-triggering/SKILL.md` + supporting files

---

## Part 8: Design Principles

### For Commands
1. **Single operation**: Each command maps to 1-3 related operations from same cluster
2. **User-friendly**: Clear purpose, intuitive naming, good argument handling
3. **Quick feedback**: Return results in <2 seconds for critical commands
4. **Discoverable**: Include argument-hint for autocomplete

### For Agents
1. **Autonomous**: Strong description so Claude auto-delegates appropriately
2. **Focused**: Single clear responsibility (not multipurpose)
3. **Specialized**: Minimal but sufficient tools for the domain
4. **Context-aware**: System prompt includes examples and edge cases

### For Skills
1. **Model-invoked**: Description critical for Claude to discover when to use
2. **Single capability**: One focused skill per domain (not broad catch-alls)
3. **Trigger-rich**: Description includes specific keywords, examples, use cases
4. **Progressive disclosure**: Supporting files loaded only when needed

---

## Summary Statistics

| Type | Count | Mapping | Status |
|------|-------|---------|--------|
| Commands | 20 | 20 operation clusters | Ready for implementation |
| Agents | 21 | Cross-cluster orchestration + error handling | Ready for implementation |
| Skills | 15 | Domain expertise coverage | Ready for implementation |
| **TOTAL** | **56** | **254 MCP operations** | **Comprehensive coverage** |

**Next Step**: Implement all 56 files following official specifications

