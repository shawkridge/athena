# Operation Cluster to Command Mapping Reference

## Quick Reference Table

| # | Operation Cluster | Primary Command | Secondary Commands | Coverage | Status |
|---|-------------------|-----------------|-------------------|----------|--------|
| 1 | EPISODIC_MEMORY | `/timeline` | - | 1 cmd | ✓ Good |
| 2 | SEMANTIC_SEARCH | `/memory-query` | - | 1 cmd | ✓ Good |
| 3 | QUALITY_HEALTH | `/memory-health` | `/reflect` | 2 cmd | ✓ Good |
| 4 | KNOWLEDGE_GRAPH | `/associations` | `/connections`, `/observations` | 3 cmd | ✓ Excellent |
| 5 | CONSOLIDATION_LEARNING | `/consolidate` | `/learning`, `/procedures` | 3 cmd | ✓ Excellent |
| 6 | WORKING_MEMORY | `/focus` | `/working-memory` | 2 cmd | ✓ Good |
| 7 | TASK_CREATION | `/task-create` | `/plan` | 2 cmd | ✓ Good |
| 8 | GOAL_ACTIVATION | `/activate-goal` | `/next-goal` | 2 cmd | ✓ Good |
| 9 | CONFLICT_RESOLUTION | `/goal-conflicts` | `/resolve-conflicts` | 2 cmd | ✓ Good |
| 10 | PROGRESS_TRACKING | `/progress` | `/goal-complete`, `/workflow-status` | 3 cmd | ✓ Excellent |
| 11 | GOAL_PRIORITIZATION | `/priorities` | - | 1 cmd | ⚠ Minimal |
| 12 | PLANNING_DECOMPOSITION | `/decompose-with-strategy` | `/plan` | 2 cmd | ✓ Good |
| 13 | PLAN_VALIDATION | `/plan-validate` | `/plan-validate-advanced` | 2 cmd | ✓ Good |
| 14 | PLAN_STRESS_TEST | `/stress-test-plan` | - | 1 cmd | ✓ Good |
| 15 | RESEARCH_SYNTHESIS | `/research` | - | 1 cmd | ✓ Good |
| 16 | MEMORY_CLEANUP | `/memory-forget` | - | 1 cmd | ✓ Good |
| 17 | WORKFLOW_PROCEDURES | `/workflow` | `/procedures` | 2 cmd | ✓ Good |
| 18 | PROJECT_STATUS | `/project-status` | `/analyze-project` | 2 cmd | ✓ Good |
| 19 | MULTI_PROJECT_COORD | `/coordinate` | - | 1 cmd | ⚠ Minimal |
| 20 | MONITORING_ANALYTICS | `/monitor` | - | 1 cmd | ⚠ Minimal |

## Detailed Command-to-Cluster Mapping

### Cluster 1: EPISODIC_MEMORY_OPERATIONS
**Purpose**: Store and retrieve episodic events (temporal events with context)
**Primary Command**: `/timeline`
```
/timeline [--days 7] [--type action] [--outcome success] [--format ascii|table]
```
**Related MCP Tools**: `mcp__memory__recall_events`, `mcp__memory__get_timeline`
**Capabilities**:
- Browse events chronologically
- Filter by type, outcome, date range
- Discover temporal patterns
- Pattern detection and causality analysis

**Status**: Well-documented, comprehensive examples

---

### Cluster 2: SEMANTIC_SEARCH_AND_RETRIEVAL
**Purpose**: Search and retrieve semantic knowledge using advanced RAG
**Primary Command**: `/memory-query`
```
/memory-query "search terms" [--domain] [--strategy hyde|reflective|lmmreranking]
```
**Related MCP Tools**: `mcp__memory__recall`, `mcp__memory__smart_retrieve`
**Capabilities**:
- Vector search with embeddings
- BM25 hybrid search
- Advanced RAG with multiple strategies
- LLM reranking for accuracy

**Status**: Well-documented, realistic examples

---

### Cluster 3: QUALITY_AND_HEALTH_MONITORING
**Purpose**: Monitor memory quality, identify gaps, track system health
**Primary Command**: `/memory-health`
**Secondary**: `/reflect`
```
/memory-health [--detail] [--gaps] [--domain DOMAIN]
/reflect [--analysis] [--confidence]
```
**Related MCP Tools**: `mcp__memory__evaluate_memory_quality`, `mcp__memory__detect_knowledge_gaps`
**Capabilities**:
- Memory quality metrics (accuracy, false positives)
- Domain coverage analysis
- Knowledge gap detection (contradictions, uncertainties)
- Cognitive load monitoring
- Self-reflection on learning strategies

**Status**: Excellent coverage with complementary commands

---

### Cluster 4: KNOWLEDGE_GRAPH_OPERATIONS
**Purpose**: Manage entity relationships and observations in knowledge graph
**Primary Commands**: `/associations`, `/connections`, `/observations`
```
/associations [--depth 2] [--strengthen]
/connections [--entity NAME] [--relation-type contains]
/observations --entity ENTITY --observation "context"
```
**Related MCP Tools**: `mcp__athena__graph_tools` (create_entity, create_relation, add_observation)
**Capabilities**:
- Entity and relation management
- Hebbian association strengthening
- Community detection
- Observation contextualization
- Knowledge graph navigation

**Status**: Excellent coverage - 3 complementary commands

---

### Cluster 5: CONSOLIDATION_AND_LEARNING
**Purpose**: Extract patterns from episodic events, learn from work, discover procedures
**Primary Commands**: `/consolidate`, `/learning`, `/procedures`
```
/consolidate [--dry-run] [--domain DOMAIN] [--detail]
/learning [--domain DOMAIN] [--confidence] [--json]
/procedures [--domain DOMAIN] [--search PATTERN]
```
**Related MCP Tools**: `mcp__athena__consolidation_tools`, `mcp__athena__skills_tools`
**Capabilities**:
- Sleep-like consolidation (episodic → semantic)
- Dual-process reasoning (fast + slow thinking)
- Learning analytics and effectiveness tracking
- Encoding rate analysis
- Procedure discovery and reuse
- Strategy optimization

**Status**: Excellent coverage - comprehensive learning ecosystem

---

### Cluster 6: WORKING_MEMORY_AND_ATTENTION
**Purpose**: Manage active context and attention within Baddeley's 7±2 limit
**Primary Commands**: `/focus`, `/working-memory`
```
/focus [--suppress-distraction] [--emphasize MEMORY_ID]
/working-memory [--capacity] [--decay] [--consolidate]
```
**Related MCP Tools**: `mcp__athena__memory_tools` (get_working_memory, update_working_memory)
**Capabilities**:
- Cognitive load monitoring (7±2 item limit)
- Dynamic attention management
- Salience tracking
- Distraction suppression
- Auto-consolidation when saturation reached
- Context rotation

**Status**: Good coverage - two complementary commands

---

### Cluster 7: TASK_AND_GOAL_CREATION
**Purpose**: Create tasks and set goals with smart triggers
**Primary Command**: `/task-create`
**Secondary**: `/plan`
```
/task-create --name "Task" --goal-id 1 [--trigger time|event|file]
/plan [--strategy STRATEGY] [--steps N]
```
**Related MCP Tools**: `mcp__athena__task_management_tools` (create_task, create_task_with_planning)
**Capabilities**:
- Smart trigger configuration (time, event, file-based)
- Goal-driven task creation
- Planning with multiple strategies
- Milestone tracking
- Task validation

**Status**: Good coverage with primary and secondary

---

### Cluster 8: GOAL_ACTIVATION_AND_CONTEXT_SWITCHING
**Purpose**: Activate goals and manage context switching with cost analysis
**Primary Commands**: `/activate-goal`, `/next-goal`
```
/activate-goal --goal-id N [--analyze-cost] [--force]
/next-goal [--recommendation]
```
**Related MCP Tools**: `mcp__athena__task_management_tools` (activate_goal), `mcp__athena__ml_integration_tools`
**Capabilities**:
- Goal activation with state tracking
- Context switching cost analysis
- Working memory transition
- Conflict detection
- AI recommendation for next goal
- Resume time estimation

**Status**: Good coverage - focused on activation and switching

---

### Cluster 9: GOAL_CONFLICT_DETECTION_AND_RESOLUTION
**Purpose**: Detect and resolve conflicts between goals
**Primary Commands**: `/goal-conflicts`, `/resolve-conflicts`
```
/goal-conflicts [--project-id N]
/resolve-conflicts [--auto-resolve] [--priority-based]
```
**Related MCP Tools**: `mcp__athena__coordination_tools`, `mcp__athena__planning_tools`
**Capabilities**:
- Resource conflict detection
- Dependency violation detection
- Priority-based conflict resolution
- Automatic mitigation
- Conflict type analysis
- Recommendation engine

**Status**: Good coverage - two complementary commands

---

### Cluster 10: GOAL_PROGRESS_AND_COMPLETION_TRACKING
**Purpose**: Track progress toward goals and record completion
**Primary Commands**: `/progress`, `/goal-complete`, `/workflow-status`
```
/progress --goal-id N --completed X --total Y
/goal-complete --goal-id N --outcome success|partial|failure
/workflow-status [--detail]
```
**Related MCP Tools**: `mcp__athena__task_management_tools` (record_execution_progress, complete_goal)
**Capabilities**:
- Progress percentage tracking
- Milestone monitoring
- Completion status recording
- Execution metrics capture
- Workflow state visibility
- Health tracking

**Status**: Excellent coverage - 3 complementary commands

---

### Cluster 11: GOAL_PRIORITIZATION_AND_RANKING
**Purpose**: Rank goals by composite score and priority
**Primary Command**: `/priorities`
```
/priorities [--composite-score] [--detail]
```
**Related MCP Tools**: `mcp__athena__task_management_tools` (get_goal_priority_ranking)
**Capabilities**:
- Composite scoring (40% priority + 35% deadline + 15% progress + 10% on-track)
- Multi-factor ranking
- Deadline analysis
- Progress weighting
- On-track assessment

**Status**: Minimal coverage - single command only

---

### Cluster 12: BASIC_PLANNING_AND_DECOMPOSITION
**Purpose**: Decompose tasks into subtasks using 9 strategies
**Primary Command**: `/decompose-with-strategy`
**Secondary**: `/plan`
```
/decompose-with-strategy --task "description" [--strategy STRATEGY]
/plan [--steps N] [--dependencies]
```
**Related MCP Tools**: `mcp__athena__planning_tools` (decompose_with_strategy)
**Capabilities**:
- 9-strategy decomposition (hierarchical, iterative, spike, parallel, etc.)
- Sequential thinking for complex tasks
- Task breakdown with dependencies
- Strategy selection
- Hierarchical task structure

**Status**: Good coverage - specialized decomposition focus

---

### Cluster 13: PLAN_VALIDATION_AND_VERIFICATION
**Purpose**: Validate and verify plans with formal properties
**Primary Commands**: `/plan-validate`, `/plan-validate-advanced`
```
/plan-validate [--strict]
/plan-validate-advanced [--q-verification] [--simulation]
```
**Related MCP Tools**: `mcp__athena__phase6_planning_tools` (verify_plan_properties, validate_plan_comprehensive)
**Capabilities**:
- 3-level validation (structure, feasibility, rules)
- Q* formal verification (5 properties: optimality, completeness, consistency, soundness, minimality)
- Structural checks
- Feasibility analysis
- Rule validation
- LLM extended thinking for complex plans

**Status**: Good coverage - basic and advanced validation

---

### Cluster 14: PLAN_STRESS_TESTING_AND_SCENARIOS
**Purpose**: Stress-test plans under 5 scenarios with confidence intervals
**Primary Command**: `/stress-test-plan`
```
/stress-test-plan [--scenarios best,worst,likely,critical,blackswan]
                  [--iterations N] [--confidence PERCENT]
```
**Related MCP Tools**: `mcp__athena__phase6_planning_tools` (simulate_plan_scenarios)
**Capabilities**:
- 5-scenario simulation (best case, worst case, likely, critical path, black swan)
- Confidence interval calculation
- Bottleneck identification
- Risk sensitivity analysis
- Monte Carlo simulation options
- Contingency buffer recommendations

**Status**: Good coverage - comprehensive stress testing

---

### Cluster 15: RESEARCH_AND_SYNTHESIS
**Purpose**: Conduct multi-source research with synthesis
**Primary Command**: `/research`
```
/research "topic" [--sources] [--synthesis] [--depth LEVEL]
```
**Related MCP Tools**: `mcp__athena__memory_tools` (research orchestration)
**Capabilities**:
- Multi-source investigation
- Parallel source analysis
- Finding synthesis
- Knowledge integration
- Cross-project pattern transfer
- Gap identification

**Status**: Good coverage - focused research command

---

### Cluster 16: MEMORY_OPTIMIZATION_AND_CLEANUP
**Purpose**: Delete low-value memories and optimize storage
**Primary Command**: `/memory-forget`
```
/memory-forget MEMORY_ID [--pattern PATTERN] [--dry-run]
```
**Related MCP Tools**: `mcp__athena__memory_tools` (forget)
**Capabilities**:
- Selective memory deletion
- Pattern-based deletion
- Low-value memory identification
- Space optimization
- Dry-run preview
- Confirmation handling

**Status**: Good coverage - focused cleanup command

---

### Cluster 17: WORKFLOW_AND_PROCEDURE_MANAGEMENT
**Purpose**: Create and track reusable workflows and procedures
**Primary Commands**: `/workflow`, `/procedures`
```
/workflow --create "name" --steps "step1;step2" [--category CATEGORY]
/procedures [--domain DOMAIN] [--search PATTERN] [--execute]
```
**Related MCP Tools**: `mcp__athena__procedural_tools` (create_procedure, find_procedures, record_execution)
**Capabilities**:
- Workflow creation and tracking
- Procedure discovery (extracted from patterns)
- Execution history
- Effectiveness measurement
- Reuse and adaptation
- Category organization

**Status**: Good coverage - creation vs. discovery focus

---

### Cluster 18: PROJECT_STATUS_AND_OVERVIEW
**Purpose**: Get project overview with goals, tasks, and metrics
**Primary Commands**: `/project-status`, `/analyze-project`
```
/project-status [--detail] [--goals] [--tasks] [--metrics]
/analyze-project [--depth LEVEL] [--patterns]
```
**Related MCP Tools**: `mcp__athena__task_management_tools` (get_project_status)
**Capabilities**:
- Project overview
- Goal and task listing
- Progress tracking
- Burn rate analysis
- Metric reporting
- Recommendation generation
- Deep pattern analysis

**Status**: Good coverage - overview vs. detailed analysis

---

### Cluster 19: MULTI_PROJECT_COORDINATION
**Purpose**: Coordinate across multiple projects
**Primary Command**: `/coordinate`
```
/coordinate [--projects PROJECT1,PROJECT2] [--dependencies]
            [--resource-conflicts] [--critical-path]
```
**Related MCP Tools**: `mcp__athena__coordination_tools`
**Capabilities**:
- Dependency management
- Cross-project analysis
- Resource conflict detection
- Critical path analysis
- Orchestration planning

**Status**: Minimal coverage - single command only

---

### Cluster 20: GENERAL_MONITORING_AND_ANALYTICS
**Purpose**: General system monitoring and analytics
**Primary Command**: `/monitor`
```
/monitor [--health] [--performance] [--trends]
```
**Related MCP Tools**: `mcp__athena__monitoring_tools`
**Capabilities**:
- System health monitoring
- Performance metrics
- Trend analysis
- Anomaly detection

**Status**: Minimal coverage - placeholder command

---

## Coverage Summary

### Excellent (3+ commands)
- Cluster 4: Knowledge Graph (3 commands)
- Cluster 5: Consolidation & Learning (3 commands)  
- Cluster 10: Progress Tracking (3 commands)

### Good (2 commands)
- Clusters 3, 6, 7, 8, 9, 12, 13, 17, 18 (9 clusters)

### Fair (1 command)
- Clusters 1, 2, 11, 14, 15, 16, 19, 20 (8 clusters)

### Under-Represented (<1 command)
- None (all clusters have at least one command)

---

## Naming Pattern by Cluster

### Prefixed Commands (Domain-Specific)
```
memory-*: /memory-query, /memory-health, /memory-forget
goal-*: /goal-conflicts, /goal-complete  
plan-*: /plan-validate, /plan-validate-advanced
task-*: /task-create
```

### Natural Nouns (No Prefix)
```
/timeline, /focus, /research, /consolidate, /learning
/procedures, /workflow, /priorities, /activate-goal
/next-goal, /progress, /resolve-conflicts, /coordinate
/monitor, /working-memory, /project-status, /analyze-project
/associations, /connections, /observations, /reflect
/decompose-with-strategy, /stress-test-plan
```

---

## Recommended Improvements by Cluster

| Cluster | Current | Recommended |
|---------|---------|------------|
| 11 | `/priorities` | Add `/goal-compare`, `/goal-rerank` |
| 19 | `/coordinate` | Add `/project-dependency`, `/resource-allocate` |
| 20 | `/monitor` | Add `/task-health`, `/system-metrics` |
| 14 | `/stress-test-plan` | Rename to `/plan-stress-test` for consistency |
| 18 | `/project-status` + `/analyze-project` | Consider merging with `--detail` flag |

---

## Command Dependency Graph

```
/timeline → /memory-query (temporal queries)
/memory-query → /associations (explore connections)
/associations → /connections (entity relations)
/consolidate → /learning (analyze extracted patterns)
/learning → /procedures (discover workflows)
/task-create → /plan → /decompose-with-strategy
/decompose-with-strategy → /plan-validate
/plan-validate → /plan-validate-advanced
/plan-validate → /stress-test-plan
/activate-goal → /goal-conflicts
/goal-conflicts → /resolve-conflicts
/activate-goal → /progress → /goal-complete
/project-status → /memory-query (lookup related memories)
/focus → /working-memory (manage context)
/memory-health → /consolidate (fix issues)
```

---

## Use Case to Command Mapping

### "I want to understand my work history"
→ `/timeline` → `/memory-query` → `/associations`

### "I want to improve my learning"
→ `/learning` → `/consolidate` → `/procedures`

### "I want to plan a complex task"
→ `/decompose-with-strategy` → `/plan-validate` → `/stress-test-plan`

### "I want to track goal progress"
→ `/project-status` → `/activate-goal` → `/progress` → `/goal-complete`

### "I need to resolve conflicts"
→ `/goal-conflicts` → `/resolve-conflicts` → `/priorities`

### "I want to optimize my memory"
→ `/memory-health` → `/memory-forget` → `/consolidate`

---

**Document Version**: 1.0
**Last Updated**: 2025-11-06
**Commands Documented**: 33
**Clusters Defined**: 20

