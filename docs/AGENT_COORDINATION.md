# Agent Coordination Protocol for Athena

**Date**: November 17, 2025
**Status**: Design Phase
**Scope**: Multi-agent communication and coordination patterns

## Overview

This document defines how agents in Athena coordinate with each other using the existing memory layers as communication channels.

## Key Principle: Memory as Communication Bus

Instead of direct inter-agent calls, agents communicate via shared memory:
- **Prospective layer**: Task creation, status updates, dependencies
- **Episodic layer**: Event notifications, execution results, logs
- **Semantic layer**: Shared knowledge, facts, conclusions
- **Meta layer**: Agent quality/expertise, attention scores
- **Knowledge graph**: Entity relationships, context, communities

**Benefits**:
- ✅ Decoupled agents (no direct dependencies)
- ✅ Observable communication (fully auditable)
- ✅ Replayable (all events stored)
- ✅ Composable (agents can be added/removed)
- ✅ Stateless (agents don't hold state about each other)

## Agent Communication Patterns

### 1. Task Delegation Pattern

**When**: One agent needs another agent to complete work

**Flow**:
```
Agent A (initiator)
  ↓
  Create task in prospective layer
  with:
  - task_id
  - description
  - required_skills (agent types)
  - parameters
  - deadline (optional)
  - dependencies (list of task_ids)
  ↓
Agent B (executor)
  ↓
  Polls active_tasks
  ↓
  Checks dependencies (all completed?)
  ↓
  Executes task
  ↓
  Updates task_status
  ↓
Agent A
  ↓
  Recalls task results
  ↓
  Continues
```

**Implementation**:
```python
# Agent A: Create task
task_id = await create_task(
    description="Analyze code quality in src/athena/memory/",
    required_skills=["code-analyzer"],
    parameters={"path": "src/athena/memory/"},
    depends_on=[],  # No dependencies
)

# Agent B: Poll for work
active = await get_active_tasks(agent_type="code-analyzer")
for task in active:
    # Check dependencies
    deps = task.get("depends_on", [])
    if all(dep_satisfied(dep) for dep in deps):
        # Execute
        result = await my_analysis(task)
        # Update status
        await update_task_status(task_id, status="completed", result=result)

# Agent A: Get results
result_task = await get_task(task_id)
result = result_task["result"]
```

### 2. Event Notification Pattern

**When**: One agent needs to alert others to something that happened

**Flow**:
```
Agent A (event source)
  ↓
  Remember event in episodic layer
  with:
  - type (e.g., "pattern_extracted", "error_detected")
  - content (detailed description)
  - tags (["pattern", "memory", "learning"])
  - importance (0-1, high for critical)
  ↓
Agent B (event listener)
  ↓
  Polls for events (or subscribed via tags)
  await recall(query, tags=["pattern"])
  ↓
  Processes event
  ↓
  May create response task/event
```

**Implementation**:
```python
# Agent A: Report finding
await remember(
    content="Extracted 5 high-confidence patterns from session xyz",
    tags=["pattern", "extracted", "session:xyz"],
    importance=0.85,
    source="pattern_extractor"
)

# Agent B: Query for findings
patterns = await recall("patterns extracted from session", tags=["pattern"], limit=10)
for pattern in patterns:
    if pattern["importance"] > 0.8:
        await process_high_value_pattern(pattern)
```

### 3. Knowledge Sharing Pattern

**When**: Agents need to share learned facts

**Flow**:
```
Agent A (learner)
  ↓
  Store fact in semantic layer
  with:
  - content (the fact)
  - topics (categories)
  - confidence (0-1)
  ↓
Agent B (user)
  ↓
  Search semantic layer
  ↓
  Uses fact in decision-making
```

**Implementation**:
```python
# Agent A: Learn and share
await store(
    content="When episodic events have tool_type='bash', they have 40% higher consolidation success",
    topics=["consolidation", "episodic", "pattern"],
    confidence=0.87,
)

# Agent B: Query knowledge
facts = await search("consolidation success bash", limit=5)
confidence = facts[0].get("confidence", 0.5)
if confidence > 0.8:
    use_this_strategy()
```

### 4. Status Coordination Pattern

**When**: Agents need to understand each other's health/progress

**Flow**:
```
Agent A (status provider)
  ↓
  Update meta-memory with:
  - quality_score (0-1)
  - last_execution
  - success_rate
  - expertise_domains
  ↓
Agent B (status consumer)
  ↓
  Query meta-memory
  ↓
  Decide if Agent A is suitable for task
```

**Implementation**:
```python
# Agent A: Report status
await update_cognitive_load(
    agent_id="memory_coordinator",
    load=0.65,  # 65% busy
    queue_size=3,
)

# Agent B: Check before delegating
load = await get_cognitive_load(agent_id="memory_coordinator")
if load < 0.8:  # Not overloaded
    delegate_task()
else:
    queue_for_later()
```

### 5. Context Enrichment Pattern

**When**: Agents need background context for decision-making

**Flow**:
```
Agent A (context provider)
  ↓
  Store context in knowledge graph
  with:
  - entity (name/id)
  - relationships (connected entities)
  - communities (groups of related entities)
  ↓
Agent B (context consumer)
  ↓
  Query graph for context
  await find_related(entity_id)
  ↓
  Uses context to improve decisions
```

**Implementation**:
```python
# Agent A: Add to knowledge graph
await add_entity(
    name="project:athena",
    entity_type="project",
    properties={"status": "active", "team_size": 2}
)
await add_relationship(
    from_entity="project:athena",
    to_entity="memory:episodic",
    relationship_type="uses",
)

# Agent B: Get context
related = await find_related("project:athena")
# Returns: ["memory:episodic", "memory:semantic", ...]
context = {e["name"]: e["properties"] for e in related}
```

## Agent Types & Responsibilities

### MemoryCoordinatorAgent
- **Responsibility**: Autonomous memory management
- **Coordination**:
  - Emits events when storing memories (episodic)
  - Updates meta-memory with decisions (statistics)
  - May create consolidation tasks (prospective)
- **Consumes**:
  - Semantic layer (novelty detection)
  - Meta-memory (decision quality feedback)

### PatternExtractorAgent
- **Responsibility**: Extract procedures from events
- **Coordination**:
  - Emits events when patterns extracted (episodic)
  - Stores patterns in semantic layer
  - Creates procedural memories
  - Updates consolidation status (prospective)
- **Consumes**:
  - Episodic layer (event stream)
  - Consolidation layer (extraction config)
  - Meta-memory (success metrics)

### Future Agent Types

#### CodeAnalyzerAgent
- **Responsibility**: Analyze code structure, dependencies, impacts
- **Coordination**:
  - Reads from knowledge graph (code entities)
  - Emits findings to episodic layer
  - Stores analysis in semantic layer
  - Updates entity importance in graph

#### ResearchCoordinatorAgent
- **Responsibility**: Multi-source research synthesis
- **Coordination**:
  - Creates research tasks (prospective)
  - Reports findings (episodic + semantic)
  - Builds knowledge graph (entities, relations)
  - Manages research quality (meta)

#### ConsolidationOptimizerAgent
- **Responsibility**: Optimize consolidation parameters
- **Coordination**:
  - Monitors consolidation tasks (prospective)
  - Analyzes consolidation events (episodic)
  - Learns optimization strategies (semantic)
  - Updates consolidation config (meta)

## Coordination Scenarios

### Scenario 1: End-of-Session Learning

```
Timeline:
T=0:   SessionEnd hook fires
T=0+:  PatternExtractor starts
       - Retrieves episodic events from session
       - Runs consolidation
       - Extracts high-confidence patterns
       - Stores patterns (semantic + procedural)
       - Emits "patterns_extracted" event

T=10s: MemoryCoordinator sees "patterns_extracted" event
       - Tags new patterns for important queries
       - Updates meta-memory (learning quality)
       - May create follow-up tasks if gaps detected

T=20s: Research queries become available
       - Include consolidated patterns in context
       - Future sessions benefit from learning
```

**Code Flow**:
```python
# Hook triggers at session end
async def session_end_hook():
    # Pattern extraction
    result = await extract_session_patterns(session_id)

    # Event notification
    if result["patterns_extracted"] > 0:
        await remember(
            content=f"Extracted {result['patterns_extracted']} patterns",
            tags=["session_end", "consolidation"],
            importance=0.9,
        )

    # Status update
    stats = get_extractor().get_statistics()
    await update_cognitive_load(
        agent_id="pattern_extractor",
        load=0.1,  # Finished
        metrics=stats,
    )
```

### Scenario 2: Multi-Step Code Analysis

```
Timeline:
T=0:   User asks "Analyze impact of changing X"

T=0+:  CodeAnalyzer agent starts
       - Creates subtasks (in prospective layer):
         * Parse code structure
         * Build dependency graph
         * Simulate changes
         * Report impact

T=10s: Code structure task completes
       - Stores entities in knowledge graph
       - Emits "code_structure_available" event

T=15s: Dependency task starts (was waiting on structure)
       - Queries knowledge graph
       - Adds relationships
       - Emits "dependencies_mapped" event

T=20s: Simulation task starts (was waiting on deps)
       - Uses graph context
       - Simulates change
       - Reports impact

T=25s: Final report generated
       - Consolidates all findings
       - Stores analysis in semantic
       - User receives answer
```

**Code Flow**:
```python
async def code_analysis_task(path):
    # Create subtasks with dependencies
    structure_task = await create_task(
        description=f"Parse structure of {path}",
        required_skills=["parser"],
        depends_on=[],
    )

    deps_task = await create_task(
        description=f"Build dependency graph for {path}",
        required_skills=["dependency-analyzer"],
        depends_on=[structure_task["id"]],
    )

    # Agents pick up tasks based on dependencies
    # They coordinate via shared memory

    # Monitor progress
    while not all_done:
        active = await get_active_tasks()
        progress = len([t for t in active if t["status"] == "completed"])
        await remember(f"Progress: {progress}/3", tags=["analysis"])
```

## API for Agent Coordination

### High-Level Coordination Functions

```python
# Create work for another agent
await create_task(
    description: str,
    required_skills: List[str],
    parameters: Dict,
    depends_on: List[str] = [],
    deadline: Optional[datetime] = None,
) -> task_id

# Check what work is available
await get_active_tasks(
    agent_type: Optional[str] = None,
    tags: Optional[List[str]] = None,
) -> List[Task]

# Update task progress
await update_task_status(
    task_id: str,
    status: str,  # "started", "completed", "failed"
    result: Optional[Dict] = None,
    error: Optional[str] = None,
) -> bool

# Report important events
await remember(
    content: str,
    tags: List[str],
    importance: float,
    source: Optional[str] = None,
) -> event_id

# Query for events others have reported
await recall(
    query: str,
    tags: Optional[List[str]] = None,
    limit: int = 10,
) -> List[Event]

# Share learned facts
await store(
    content: str,
    topics: List[str],
    confidence: float,
) -> fact_id

# Query shared knowledge
await search(
    query: str,
    limit: int = 10,
) -> List[Fact]

# Get agent/system status
await get_cognitive_load(
    agent_id: str,
) -> CognitiveLoad

# Update status
await update_cognitive_load(
    agent_id: str,
    load: float,
    metrics: Optional[Dict] = None,
) -> bool
```

## Safety Considerations

### 1. Deadlock Prevention

**Risk**: Agent A waits for task created by Agent B, which waits for task created by Agent A

**Mitigation**:
- Acyclic task dependency graph (prospective layer enforces)
- Timeout on task waits (default 5 min)
- Manual intervention if deadlock detected

### 2. Information Overload

**Risk**: Too many tasks created, agents can't keep up

**Mitigation**:
- Cognitive load tracking (meta-memory)
- Task prioritization (prospective layer)
- Backpressure (agents check load before delegating)

### 3. Consistency

**Risk**: Agents see different views of shared state

**Mitigation**:
- Single source of truth (PostgreSQL)
- Consistent reads (all ops use db.initialize)
- Timestamps for ordering (all events timestamped)

### 4. Security

**Risk**: One agent corrupts data, affecting others

**Mitigation**:
- Immutable episodic events (can't edit history)
- Validation on task parameters
- Audit trail (everything logged)

## Testing Multi-Agent Coordination

### Unit Tests

```python
async def test_task_dependency_ordering():
    """Task B shouldn't run until Task A completes"""
    task_a = await create_task("A", depends_on=[])
    task_b = await create_task("B", depends_on=[task_a["id"]])

    # Get B's status - should be pending
    b = await get_task(task_b["id"])
    assert b["status"] == "pending"

    # Complete A
    await update_task_status(task_a["id"], "completed")

    # B should now be available
    b = await get_task(task_b["id"])
    assert b["status"] == "pending_execution"  # Ready to run
```

### Integration Tests

```python
async def test_coordination_scenario():
    """Full multi-agent coordination flow"""

    # Step 1: Task creation
    analysis_task = await create_task(
        description="Analyze code",
        required_skills=["analyzer"],
        depends_on=[],
    )

    # Step 2: Agent picks it up and works
    agent = CodeAnalyzer()
    result = await agent.execute(analysis_task)

    # Step 3: Update status
    await update_task_status(analysis_task["id"], "completed", result)

    # Step 4: Other agents can see completion
    task = await get_task(analysis_task["id"])
    assert task["status"] == "completed"

    # Step 5: Dependent agents can proceed
    events = await recall("analysis completed")
    assert len(events) > 0
```

## Migration Path

### Phase 1: Current State (Complete ✅)
- MemoryCoordinatorAgent + PatternExtractorAgent
- Basic memory operations
- No coordination yet

### Phase 2: Core Coordination (This Task)
- Agent task creation (prospective)
- Event notifications (episodic)
- Status tracking (meta)

### Phase 3: Multi-Agent System
- Add CodeAnalyzerAgent
- Add ResearchCoordinatorAgent
- Complex multi-step tasks

### Phase 4: Advanced Coordination
- Agent specialization/routing
- Dynamic agent spawning
- Adaptive workload distribution

## Next Steps

1. **Implement AgentCoordinator base class**
   - Standard task management
   - Event emission patterns
   - Status tracking

2. **Write coordination tests**
   - Verify task dependencies work
   - Verify event propagation
   - Verify deadlock prevention

3. **Implement first multi-agent flow**
   - End-of-session consolidation
   - Both agents working together

4. **Add agent monitoring**
   - Dashboard (optional Phase 2)
   - Metrics collection
   - Health checks

---

**Version**: 1.0 - Agent Coordination Design
**Status**: Ready for implementation
