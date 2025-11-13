# Optimal Orchestration Design for Athena Memory System

**Date**: 2025-11-10
**Status**: Design Phase
**Purpose**: Define the most effective orchestration architecture for Athena
**Target Audience**: Architects, Lead Engineers, Implementation Team

---

## Executive Summary

Based on comprehensive analysis of:
1. Research on 10 orchestration patterns across 6+ frameworks
2. Athena's existing architecture (8-layer memory, MCP interface, existing coordination code)
3. Discovered existing orchestration implementations (AgentOrchestrator, SubAgentOrchestrator)

**Recommendation**: Implement a **hybrid multi-pattern orchestration system** that combines:
- **Primary**: Database-Driven orchestration (task queue in episodic memory)
- **Secondary**: Event-Driven reactive patterns (episodic events as event stream)
- **Advanced**: SubAgent pattern for parallel task execution (already implemented framework)
- **Meta**: Knowledge graph for capability-based routing and team formation

This design leverages Athena's existing strengths while avoiding redundancy with already-implemented coordinator patterns.

**Timeline**: 8-12 weeks for full implementation
**Effort**: ~3,500-5,000 LOC across 4 phases
**Complexity**: Medium-High (builds on existing framework)

---

## Part 1: Architecture Analysis

### 1.1 Athena's Existing State

#### Already Implemented
1. **AgentOrchestrator** (`src/athena/orchestration/coordinator.py`)
   - DAG-based task execution
   - Parallel execution with dependency management
   - Async execution model
   - Status tracking (PENDING → RUNNING → COMPLETED/FAILED)

2. **SubAgentOrchestrator** (`src/athena/orchestration/subagent_orchestrator.py`)
   - Specialized agents for specific tasks (clustering, validation, extraction, integration)
   - Parallel execution with feedback coordination
   - Task priority management
   - Coordination effectiveness measurement

3. **Core Memory Layers**
   - **Episodic** (Layer 1): Event storage with timestamps, context, metrics
   - **Semantic** (Layer 2): Vector + BM25 hybrid search
   - **Procedural** (Layer 3): Workflow storage, execution tracking
   - **Prospective** (Layer 4): Task/goal management with triggers
   - **Knowledge Graph** (Layer 5): Entity/relation storage, community detection
   - **Meta-Memory** (Layer 6): Quality tracking, expertise, cognitive load
   - **Consolidation** (Layer 7): Pattern extraction (clustering, validation)
   - **Supporting** (Layer 8): RAG, planning, associations

4. **Unified Memory Manager** (`manager.py`)
   - Routes queries by type (temporal, factual, relational, procedural, prospective, meta, planning)
   - Integrates all layers with confidence scoring
   - Enables graceful RAG degradation

#### Not Yet Integrated
1. **Task queue in episodic memory** - Can use EVENT types for task lifecycle
2. **Event-driven pub-sub** - Could leverage episodic events as event stream
3. **Capability-based routing** - Could use knowledge graph for agent skills
4. **Hierarchical team coordination** - Could use graph communities as teams
5. **Agent registry** - Could extend knowledge graph with agent entities

### 1.2 Architectural Constraints

**Positive Constraints** (Advantages):
- ✅ SQLite-based = natural transaction support
- ✅ Episodic events = persistent event log
- ✅ Knowledge graph = relationship tracking
- ✅ Meta-memory = quality and performance tracking
- ✅ Consolidation = automatic pattern extraction
- ✅ Working memory buffer = prevents cognitive overload
- ✅ Async execution patterns already used (SubAgentOrchestrator)

**Challenges to Manage**:
- ⚠️ SQLite write concurrency limits (~2000/sec theoretical max)
- ⚠️ Vector search latency (50-100ms typical)
- ⚠️ Consolidation is computationally expensive
- ⚠️ Large state graphs can slow community detection
- ⚠️ Need careful schema design to avoid conflicts with existing tables

---

## Part 2: Requirements Definition

### 2.1 Functional Requirements

#### FR1: Task Queue Management
- **FR1.1**: Create tasks with metadata (priority, dependencies, requirements)
- **FR1.2**: Assign tasks to agents based on capabilities
- **FR1.3**: Poll for pending/assigned tasks
- **FR1.4**: Update task status (pending → assigned → running → completed/failed)
- **FR1.5**: Store task results and error information
- **FR1.6**: Support task dependencies (topological execution order)

#### FR2: Agent Registry and Discovery
- **FR2.1**: Register agents with capabilities (skills, expertise domains)
- **FR2.2**: Query agents by capability
- **FR2.3**: Track agent performance (success rate, avg completion time)
- **FR2.4**: Dynamic capability updates (learn new skills from consolidation)
- **FR2.5**: Agent deprecation and retirement

#### FR3: Event-Driven Reactivity
- **FR3.1**: Subscribe agents to event patterns (file changes, task completion, etc.)
- **FR3.2**: Notify subscribers on matching events
- **FR3.3**: Pattern matching (regex or semantic similarity)
- **FR3.4**: Unsubscribe agents from patterns

#### FR4: Coordination and Feedback
- **FR4.1**: Pass results between dependent tasks (data flow)
- **FR4.2**: Collect feedback from agents on task quality
- **FR4.3**: Update meta-memory with performance metrics
- **FR4.4**: Trigger consolidation on completion milestones

#### FR5: Error Handling and Recovery
- **FR5.1**: Detect task failures (timeout, exception, validation failure)
- **FR5.2**: Retry with backoff strategy
- **FR5.3**: Circuit breaker pattern (stop retrying after N failures)
- **FR5.4**: Checkpoint state for recovery

#### FR6: Observability and Monitoring
- **FR6.1**: Track orchestration metrics (tasks/sec, latency, success rate)
- **FR6.2**: Monitor agent health (CPU, memory, task queue size)
- **FR6.3**: Identify bottlenecks (slow agents, high latency paths)
- **FR6.4**: Generate orchestration insights (patterns, anomalies)

### 2.2 Non-Functional Requirements

#### NFR1: Performance
- **Target throughput**: 100-200 tasks/sec (database-driven phase 1)
- **Target latency**: 50-100ms (p50) for task creation → assignment
- **Scalability**: 50-100 agents initially, 500+ with hierarchical pattern
- **Memory**: <500MB additional for orchestration state

#### NFR2: Reliability
- **Fault tolerance**: Survive single-agent failures without affecting others
- **Durability**: All task state persisted (not in-memory only)
- **Consistency**: Task state always reflects reality (no stale reads)
- **Recovery**: Restart agents and resume from last checkpoint

#### NFR3: Maintainability
- **Code organization**: Clear separation of concerns
- **Testing**: 80%+ coverage for orchestration layer
- **Documentation**: Examples for all patterns
- **Extensibility**: Easy to add new agent types, task types

#### NFR4: Integration
- **MCP tools**: All orchestration operations exposed via MCP
- **Memory layer**: Seamless integration with existing memory layers
- **Schema**: No breaking changes to existing database tables

---

## Part 3: Optimal Solution Design

### 3.1 Core Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    MCP Tools Layer                          │
│  (orchestration/*, task/*, agent/*, team/*)                 │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│              Orchestration Coordinator                       │
│  TaskQueue│AgentRegistry│EventBus│SubAgentOrchestrator      │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────┬──────────────┬──────────────┬────────────────┐
│ Episodic     │ Procedural   │ Knowledge    │ Meta-Memory    │
│ Memory       │ Memory       │ Graph        │ Store          │
│ (Task Queue) │ (Workflows)  │ (Agents,     │ (Quality,      │
│              │              │  Skills,     │  Performance)  │
│              │              │  Teams)      │                │
└──────────────┴──────────────┴──────────────┴────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                   SQLite Database                            │
│         (Local-first, transactional, persistent)            │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Component Design

#### Component 1: TaskQueue (Episodic-Backed)
**Location**: `src/athena/orchestration/task_queue.py`
**Responsibility**: Manage task lifecycle in episodic memory
**Key Methods**:
```python
class TaskQueue:
    def create_task(self, content, priority, requirements, dependencies) -> int
    def poll_tasks(self, agent_id=None, filter=None) -> List[Task]
    def assign_task(self, task_id, agent_id) -> None
    def start_task(self, task_id) -> None
    def complete_task(self, task_id, result, metrics) -> None
    def fail_task(self, task_id, error) -> None
    def query_by_status(self, status, limit) -> List[Task]
```

**Database Schema**:
```sql
-- Extend episodic_events with task-specific columns
ALTER TABLE episodic_events ADD COLUMN (
    task_type TEXT,                  -- 'research', 'analysis', 'synthesis', etc.
    assigned_to TEXT,                -- Agent ID
    priority TEXT DEFAULT 'medium',  -- 'low', 'medium', 'high'
    requirements TEXT,               -- JSON: ["skill1", "skill2"]
    dependencies TEXT,               -- JSON: [task_id_1, task_id_2]
    task_status TEXT DEFAULT 'pending', -- State machine
    metrics TEXT,                    -- JSON: {duration_ms, rows_processed, ...}
    result_event_id INT REFERENCES episodic_events(id)
);

CREATE INDEX idx_task_status ON episodic_events(task_status);
CREATE INDEX idx_assigned_to ON episodic_events(assigned_to);
CREATE INDEX idx_task_type ON episodic_events(task_type);
```

**Event Types** (reuse existing EVENT type with task_type field):
- `task_created` → (pending, unassigned)
- `task_assigned` → (assigned, waiting for start)
- `task_started` → (running, in progress)
- `task_completed` → (completed, success)
- `task_failed` → (failed, retry or escalate)

#### Component 2: AgentRegistry (Knowledge Graph-Backed)
**Location**: `src/athena/orchestration/agent_registry.py`
**Responsibility**: Manage agent capabilities and performance
**Key Methods**:
```python
class AgentRegistry:
    def register_agent(self, agent_id, capabilities, metadata) -> None
    def get_agents_by_capability(self, required_capabilities) -> List[Agent]
    def update_agent_performance(self, agent_id, task_result) -> None
    def get_agent_health(self, agent_id) -> AgentHealth
    def discover_capable_agents(self, task_requirements) -> List[Agent]
    def deregister_agent(self, agent_id) -> None
```

**Graph Schema**:
```
Entity: agent_{id}
  ├─ has_skill → skill_python
  ├─ has_skill → skill_debugging
  ├─ has_skill → skill_documentation
  ├─ belongs_to → team_backend
  └─ metadata: {success_rate: 0.95, avg_time_ms: 500, ...}

Entity: skill_{name}
  ├─ required_by → task_type_{name}
  └─ metadata: {level: 'expert', demand: 100}

Entity: team_{id}
  ├─ has_member → agent_{id}
  └─ metadata: {leader_id: agent_123, size: 5}
```

#### Component 3: EventBus (Episodic-Based Pub/Sub)
**Location**: `src/athena/orchestration/event_bus.py`
**Responsibility**: Publish events and notify subscribers
**Key Methods**:
```python
class EventBus:
    def subscribe(self, agent_id, event_pattern, handler) -> Subscription
    def unsubscribe(self, subscription_id) -> None
    def publish_event(self, event) -> None
    def get_subscribers(self, event_pattern) -> List[Subscriber]
    def match_event_pattern(self, event, pattern) -> bool
```

**Subscription Registry Table**:
```sql
CREATE TABLE IF NOT EXISTS event_subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,
    event_pattern TEXT NOT NULL,        -- Regex or semantic pattern
    handler_url TEXT,                   -- Webhook/MCP endpoint
    created_at INTEGER NOT NULL,
    last_triggered INTEGER,
    trigger_count INTEGER DEFAULT 0,
    UNIQUE(agent_id, event_pattern)
);
```

#### Component 4: CapabilityRouter (Graph-Based Routing)
**Location**: `src/athena/orchestration/capability_router.py`
**Responsibility**: Match tasks to capable agents
**Key Methods**:
```python
class CapabilityRouter:
    def route_task(self, task_requirements, exclude_agents=None) -> Optional[Agent]
    def rank_candidates(self, candidates, task_metrics) -> List[Agent]
    def should_rebalance(self) -> bool
    def get_routing_statistics(self) -> Dict
```

**Routing Algorithm**:
```
Input: task with requirements=[skill1, skill2]
1. Query graph: agents WITH all required skills
2. Filter: not in excluded_agents, not overloaded
3. Rank by: success_rate * (1 - current_load / capacity)
4. Return: top-ranked agent
```

#### Component 5: SubAgentCoordinator (Enhanced SubAgentOrchestrator)
**Location**: `src/athena/orchestration/subagent_coordinator.py`
**Responsibility**: Execute complex tasks with parallel subagents
**Key Methods**:
```python
class SubAgentCoordinator:
    async def execute_task(self, task, subagents) -> TaskResult
    def create_task_graph(self, subagents) -> TaskGraph
    def apply_feedback_loop(self, results) -> Dict
    def measure_effectiveness(self) -> float
```

**Integration Point**: Reuse existing `SubAgentOrchestrator` from code, extend with:
- Task result persistence to episodic memory
- Feedback loop to update agent registry
- Integration with TaskQueue

#### Component 6: OrchestrationManager (Unified Coordinator)
**Location**: `src/athena/orchestration/manager.py`
**Responsibility**: Coordinate all orchestration components
**Key Methods**:
```python
class OrchestrationManager:
    async def dispatch_task(self, task_description, requirements) -> TaskResult
    async def execute_workflow(self, workflow_spec) -> WorkflowResult
    async def monitor_execution(self, task_id) -> ExecutionStatus
    def get_orchestration_health(self) -> OrchestrationHealth
    async def trigger_consolidation(self, task_batch_size) -> ConsolidationResult
```

**Event Flow**:
```
1. Task Created (MCP call)
   ↓ → store in episodic_events (task_created)
   ↓ → route using CapabilityRouter
   ↓ → assign to agent (episodic_events: task_assigned)
   ↓ → notify EventBus subscribers

2. Agent Polls for Tasks
   ↓ → query TaskQueue (pending for agent_id)
   ↓ → execute task (agent-specific)
   ↓ → store result in episodic_events (task_completed/failed)
   ↓ → trigger consolidation if threshold reached

3. Consolidation Phase
   ↓ → trigger SubAgentCoordinator
   ↓ → parallel: clustering, validation, extraction, integration
   ↓ → update knowledge graph with patterns
   ↓ → update agent registry with learned skills

4. Meta-Memory Update
   ↓ → update quality metrics (success_rate, latency)
   ↓ → update expertise tracking (skill effectiveness)
   ↓ → trigger rebalancing if needed
```

### 3.3 Design Patterns

#### Pattern 1: Database-Driven Task Queue
**Why**: SQLite provides ACID transactions, natural durability
**How**: Tasks = episodic events with task-specific state machine
**Advantages**:
- ✅ Fault-tolerant (survive crashes)
- ✅ Supports complex queries (dependencies, status)
- ✅ Natural integration with existing episodic layer
- ✅ Consolidation can process task patterns

**Disadvantages**:
- ⚠️ Write throughput limited by SQLite (~2000/sec)
- ⚠️ Polling latency (agents must poll periodically)

#### Pattern 2: Event-Driven Reactivity
**Why**: Episodic events naturally form event stream
**How**: Agents subscribe to event patterns, EventBus notifies
**Advantages**:
- ✅ Real-time notifications (push, not pull)
- ✅ Decoupled agents (event-based, not direct calls)
- ✅ Natural scaling (many subscribers to few events)

**Disadvantages**:
- ⚠️ Requires pub-sub infrastructure (new subscriptions table)
- ⚠️ Pattern matching adds latency (regex or semantic)

#### Pattern 3: SubAgent Specialization
**Why**: Already implemented, proven framework
**How**: Reuse existing SubAgentOrchestrator for parallel task execution
**Advantages**:
- ✅ Parallel execution of specialized tasks
- ✅ Feedback coordination between agents
- ✅ Effectiveness measurement built-in

**Disadvantages**:
- ⚠️ Works best for known task types (not generic)

#### Pattern 4: Knowledge Graph for Relationships
**Why**: Athena already has graph layer
**How**: Agents = entities, skills = relations, teams = communities
**Advantages**:
- ✅ Natural capability discovery (graph queries)
- ✅ Hierarchical team formation (community detection)
- ✅ Relationship-based routing

**Disadvantages**:
- ⚠️ Community detection is expensive (O(n²) for large graphs)
- ⚠️ Requires careful schema to avoid conflicts

---

## Part 4: Design Alternatives and Trade-Offs

### Alternative 1: Pure Task Queue (Redis/Celery Pattern)
**Description**: Use external Redis for task queue, agents as workers
**Pros**:
- ✅ Better write throughput (Redis optimized)
- ✅ Native pub-sub (Redis subscribe/publish)
- ✅ Familiar pattern (standard in industry)

**Cons**:
- ❌ Breaks local-first philosophy (requires Redis server)
- ❌ Adds external dependency (complexity)
- ❌ Duplicates state (Redis + SQLite = sync issues)
- ❌ Not memory-driven (breaks Athena philosophy)

**Decision**: ❌ **Rejected** - Violates local-first principle and creates redundancy

---

### Alternative 2: Pure in-Memory Coordination
**Description**: Coordinators keep task queue in memory, sync to DB
**Pros**:
- ✅ Higher throughput
- ✅ Lower latency
- ✅ Simpler logic (no complex queries)

**Cons**:
- ❌ Loss of state on crash
- ❌ Distributed coordinator = consensus problem (hard)
- ❌ No audit trail (can't replay)
- ❌ Doesn't leverage episodic memory

**Decision**: ❌ **Rejected** - Poor fault tolerance, no learning capability

---

### Alternative 3: Microservices with API Gateway
**Description**: Each agent is microservice, API gateway coordinates
**Pros**:
- ✅ Language-agnostic (agents in any language)
- ✅ Horizontal scaling (add agents easily)
- ✅ Failure isolation (one agent fails, others continue)

**Cons**:
- ❌ Network overhead (API calls = latency)
- ❌ Deployment complexity (orchestrate services)
- ❌ Overkill for current use case
- ❌ Requires monitoring infrastructure

**Decision**: ❌ **Rejected** - Too complex for MVP, postpone to Phase 6 (distributed Athena)

---

### Alternative 4: Hybrid Database-Driven + Event-Driven (SELECTED)
**Description**: Task queue in database (durable) + events for notifications
**Pros**:
- ✅ Fault-tolerant (database persistent)
- ✅ Real-time capable (event notifications)
- ✅ Leverages Athena strengths (memory layers)
- ✅ Progressive enhancement (add event bus later)
- ✅ Low complexity (builds on existing)

**Cons**:
- ⚠️ Slightly higher latency than pure Redis
- ⚠️ Two systems to maintain (DB + event bus)

**Decision**: ✅ **Selected** - Best balance of reliability, learning, and implementation cost

---

## Part 5: Detailed Integration Blueprint

### 5.1 Schema Design

**Episodic Events Extension**:
```sql
ALTER TABLE episodic_events ADD COLUMN IF NOT EXISTS (
    -- Task metadata
    task_id TEXT UNIQUE,                           -- UUID for task tracking
    task_type TEXT,                                -- research, analysis, synthesis, etc.
    task_status TEXT DEFAULT 'pending',            -- pending, assigned, running, completed, failed
    assigned_to TEXT,                              -- Agent ID
    assigned_at INTEGER,                           -- Timestamp

    -- Requirements and dependencies
    requirements TEXT,                             -- JSON array: ["skill1", "skill2"]
    dependencies TEXT,                             -- JSON array: [task_id_1, task_id_2]

    -- Execution metadata
    started_at INTEGER,                            -- Actual start time
    completed_at INTEGER,                          -- Actual completion time
    priority TEXT DEFAULT 'medium',                -- low, medium, high

    -- Results and error handling
    result_task_id INT REFERENCES episodic_events(id),  -- Link to completion event
    error_message TEXT,                            -- Error details
    retry_count INTEGER DEFAULT 0,                 -- Number of retries
    retry_until INTEGER,                           -- Stop retrying after this timestamp

    -- Metrics
    execution_duration_ms INTEGER,                 -- Wall-clock time
    estimated_duration_ms INTEGER,                 -- Pre-execution estimate
    success BOOLEAN,                               -- Task succeeded?

    -- For consolidation
    task_batch_id TEXT                             -- Group related tasks
);

-- Indexes for fast queries
CREATE INDEX idx_task_status ON episodic_events(task_status);
CREATE INDEX idx_assigned_to ON episodic_events(assigned_to);
CREATE INDEX idx_task_type ON episodic_events(task_type);
CREATE INDEX idx_dependencies ON episodic_events(dependencies);
CREATE INDEX idx_created_at ON episodic_events(created_at);
```

**Event Subscriptions Table**:
```sql
CREATE TABLE IF NOT EXISTS event_subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,
    event_pattern TEXT NOT NULL,                   -- Regex pattern
    handler_url TEXT,                              -- Webhook URL (optional)
    pattern_type TEXT DEFAULT 'regex',             -- regex, semantic, exact
    is_active BOOLEAN DEFAULT 1,

    -- Metrics
    created_at INTEGER NOT NULL,
    last_triggered INTEGER,
    trigger_count INTEGER DEFAULT 0,

    -- Subscriptions table
    UNIQUE(agent_id, event_pattern),
    FOREIGN KEY (agent_id) REFERENCES entities(name)  -- Agent entity
);
```

**Knowledge Graph Extension** (for agents):
```sql
-- Agents registered as entities
INSERT INTO entities (name, entity_type, metadata)
VALUES ('agent_python_expert', 'agent', '{
    "capabilities": ["python", "debugging"],
    "max_concurrent_tasks": 5,
    "success_rate": 0.95,
    "avg_completion_ms": 1200,
    "last_updated": 1699600000
}');

-- Relations for skills
INSERT INTO entity_relations (from_entity_id, to_entity_id, relation_type, strength)
VALUES (
    (SELECT id FROM entities WHERE name='agent_python_expert'),
    (SELECT id FROM entities WHERE name='skill_python'),
    'has_skill',
    0.95
);

-- Teams as entity groups (using communities)
-- Automatically detected via Leiden algorithm
```

### 5.2 MCP Tools

**New MCP Tool Definitions**:

```python
# src/athena/mcp/handlers_orchestration.py

# Task Management
@server.tool()
def orchestration_create_task(content: str, task_type: str, priority: str,
                             requirements: List[str], dependencies: List[str]) -> Dict:
    """Create a new task in the queue."""

@server.tool()
def orchestration_poll_tasks(agent_id: Optional[str], status: Optional[str],
                            limit: int = 10) -> List[Dict]:
    """Poll for pending/assigned tasks."""

@server.tool()
def orchestration_assign_task(task_id: str, agent_id: str) -> Dict:
    """Assign task to specific agent."""

@server.tool()
def orchestration_complete_task(task_id: str, result: str, metrics: Dict) -> Dict:
    """Mark task as completed with result."""

@server.tool()
def orchestration_fail_task(task_id: str, error: str, should_retry: bool) -> Dict:
    """Mark task as failed."""

# Agent Management
@server.tool()
def orchestration_register_agent(agent_id: str, capabilities: List[str],
                                max_concurrent: int) -> Dict:
    """Register agent with capabilities."""

@server.tool()
def orchestration_update_agent_performance(agent_id: str, task_result: Dict) -> None:
    """Update agent performance metrics."""

@server.tool()
def orchestration_get_agent_health(agent_id: Optional[str]) -> Dict:
    """Get health status of agent(s)."""

@server.tool()
def orchestration_find_capable_agents(requirements: List[str]) -> List[Dict]:
    """Find agents with required capabilities."""

# Event-Driven
@server.tool()
def orchestration_subscribe_to_events(agent_id: str, event_pattern: str) -> Dict:
    """Subscribe agent to event pattern."""

@server.tool()
def orchestration_unsubscribe_from_events(subscription_id: str) -> None:
    """Unsubscribe from event pattern."""

# Workflow Management
@server.tool()
def orchestration_execute_workflow(workflow_spec: Dict) -> Dict:
    """Execute multi-step workflow with dependencies."""

@server.tool()
def orchestration_get_execution_status(task_id: str) -> Dict:
    """Get status of task execution."""

# Monitoring
@server.tool()
def orchestration_get_queue_metrics() -> Dict:
    """Get task queue metrics (size, age, distribution)."""

@server.tool()
def orchestration_get_orchestration_insights() -> Dict:
    """Get insights (bottlenecks, patterns, recommendations)."""
```

### 5.3 Class Interfaces

**TaskQueue Interface**:
```python
# src/athena/orchestration/task_queue.py

class TaskQueue:
    """Task queue backed by episodic memory."""

    def __init__(self, episodic_store: EpisodicStore, graph_store: GraphStore):
        self.episodic = episodic_store
        self.graph = graph_store

    def create_task(self,
                   content: str,
                   task_type: str,
                   priority: str = "medium",
                   requirements: List[str] = None,
                   dependencies: List[str] = None) -> str:
        """Create task, return task_id."""

    def poll_tasks(self,
                  agent_id: Optional[str] = None,
                  status: str = "pending",
                  limit: int = 10) -> List[EpisodicEvent]:
        """Get pending/assigned tasks for agent."""

    def assign_task(self, task_id: str, agent_id: str) -> None:
        """Assign task to agent."""

    def start_task(self, task_id: str) -> None:
        """Mark task as running."""

    def complete_task(self, task_id: str, result: str, metrics: Dict) -> None:
        """Mark task complete with result."""

    def fail_task(self, task_id: str, error: str, should_retry: bool = True) -> None:
        """Mark task failed, optionally retry."""

    def get_task_status(self, task_id: str) -> Dict:
        """Get current task status."""

    def get_task_dependencies(self, task_id: str) -> List[str]:
        """Get task dependencies."""

    def query_tasks(self, filters: Dict) -> List[EpisodicEvent]:
        """Complex query: status, agent, type, created_after, etc."""
```

**AgentRegistry Interface**:
```python
# src/athena/orchestration/agent_registry.py

class AgentRegistry:
    """Agent capability registry backed by knowledge graph."""

    def __init__(self, graph_store: GraphStore, meta_store: MetaMemoryStore):
        self.graph = graph_store
        self.meta = meta_store

    def register_agent(self, agent_id: str, capabilities: List[str],
                      metadata: Dict) -> None:
        """Register agent with skills."""

    def get_agents_by_capability(self, required: List[str],
                                exclude: List[str] = None) -> List[str]:
        """Find agents with ALL required capabilities."""

    def get_agent_capability(self, agent_id: str) -> List[str]:
        """List agent's capabilities."""

    def update_agent_performance(self, agent_id: str,
                                success: bool,
                                duration_ms: int,
                                task_metrics: Dict) -> None:
        """Update performance metrics from completed task."""

    def get_agent_health(self, agent_id: str) -> Dict:
        """Get health: {success_rate, avg_duration, load, status}."""

    def learn_new_capability(self, agent_id: str, capability: str,
                           confidence: float = 1.0) -> None:
        """Add new skill (from consolidation)."""

    def deregister_agent(self, agent_id: str) -> None:
        """Remove agent from registry."""

    def get_routing_statistics(self) -> Dict:
        """Get stats: agent load distribution, skill distribution, etc."""
```

**EventBus Interface**:
```python
# src/athena/orchestration/event_bus.py

class EventBus:
    """Event bus for agent subscriptions."""

    def __init__(self, episodic_store: EpisodicStore,
                 db: Database):
        self.episodic = episodic_store
        self.db = db

    def subscribe(self, agent_id: str, event_pattern: str,
                 pattern_type: str = "regex") -> str:
        """Subscribe agent to pattern, return subscription_id."""

    def unsubscribe(self, subscription_id: str) -> None:
        """Unsubscribe from pattern."""

    def publish_event(self, event: EpisodicEvent) -> None:
        """Publish event and notify subscribers."""

    def get_subscribers(self, event: EpisodicEvent) -> List[str]:
        """Find agents subscribed to this event."""

    def notify_subscribers(self, event: EpisodicEvent,
                          subscriber_ids: List[str]) -> None:
        """Send notifications to subscribers."""

    def match_pattern(self, event: EpisodicEvent,
                     pattern: str,
                     pattern_type: str) -> bool:
        """Check if event matches pattern."""

    def get_subscription_metrics(self) -> Dict:
        """Subscription stats: active subs, triggers, patterns."""
```

**CapabilityRouter Interface**:
```python
# src/athena/orchestration/capability_router.py

class CapabilityRouter:
    """Route tasks to capable agents."""

    def __init__(self, registry: AgentRegistry,
                 meta: MetaMemoryStore):
        self.registry = registry
        self.meta = meta

    def route_task(self, task: Task, exclude: List[str] = None) -> Optional[str]:
        """Select best agent for task. Returns agent_id or None."""

    def find_capable(self, requirements: List[str]) -> List[str]:
        """Find all agents with capabilities."""

    def rank_candidates(self, candidates: List[str],
                       task: Task) -> List[Tuple[str, float]]:
        """Rank candidates by: success_rate * (1 - load/capacity)."""

    def should_rebalance(self) -> bool:
        """Check if rebalancing needed (load skew > threshold)."""

    def get_load(self, agent_id: str) -> float:
        """Current load: running_tasks / max_concurrent."""

    def get_routing_stats(self) -> Dict:
        """Stats: misses, routing time, load distribution."""
```

---

## Part 6: Implementation Phases

### Phase 1: Foundation (Weeks 1-3)

**Goal**: Working task queue with basic assignment
**Effort**: ~800-1200 LOC

**Tasks**:
1. ✅ Extend episodic schema with task fields
2. ✅ Implement TaskQueue (create, poll, assign, complete, fail)
3. ✅ Implement AgentRegistry with graph-backed capabilities
4. ✅ Implement CapabilityRouter with basic ranking
5. ✅ Add MCP tools for task/agent operations
6. ✅ Integration tests (60+ test cases)

**Deliverables**:
- Task queue with full lifecycle management
- Agent registry with capability tracking
- Basic routing (capability-based)
- MCP tools for manual workflow
- Test suite with 80%+ coverage

**Success Criteria**:
- ✅ Create task → assign to capable agent → complete
- ✅ Query tasks by status, type, agent
- ✅ Agent performance tracking
- ✅ All operations via MCP tools

---

### Phase 2: Event-Driven Reactivity (Weeks 4-5)

**Goal**: Reactive agents via event subscriptions
**Effort**: ~600-900 LOC
**Depends on**: Phase 1

**Tasks**:
1. Implement EventBus with subscriptions table
2. Implement event pattern matching (regex + semantic)
3. Add pub-sub notification mechanism
4. Integrate with TaskQueue (publish on task events)
5. Add MCP tools for subscriptions
6. Test event propagation and notifications

**Deliverables**:
- Event subscription registry
- Pattern matching (regex, semantic)
- Pub-sub notification system
- MCP tools for subscribe/unsubscribe
- Test suite for event flows

**Success Criteria**:
- Agent can subscribe to "task_completed:*"
- On matching event, agent notified
- Can unsubscribe cleanly
- No duplicate notifications

---

### Phase 3: Consolidation Integration (Weeks 6-8)

**Goal**: Learning from task execution patterns
**Effort**: ~800-1200 LOC
**Depends on**: Phase 1, consolidation layer

**Tasks**:
1. Create OrchestrationManager to coordinate components
2. Trigger consolidation on task batches
3. Extract workflow patterns (clustering, extraction)
4. Learn agent skills (from task success patterns)
5. Update agent registry with learned skills
6. Add insights generation (bottleneck detection)

**Deliverables**:
- OrchestrationManager with workflow coordination
- Consolidation integration (patterns → skills)
- Workflow pattern extraction
- Insights API (bottlenecks, patterns)
- Performance monitoring

**Success Criteria**:
- ✅ 50+ tasks → consolidate
- ✅ Identify workflow pattern (research → analysis → synthesis)
- ✅ Learn agent skills from task patterns
- ✅ Suggest improvements based on patterns

---

### Phase 4: Hierarchical Teams & Optimization (Weeks 9-12)

**Goal**: Scaled orchestration with team-based coordination
**Effort**: ~1000-1500 LOC
**Depends on**: Phase 1-3

**Tasks**:
1. Community detection for agent teams
2. Team leaders and delegation
3. Learning-based routing (ML model)
4. Load balancing across teams
5. Failure recovery and retries
6. Advanced insights (anomaly detection, predictions)

**Deliverables**:
- Community-based team formation
- Hierarchical routing (top-level → communities → agents)
- ML-based routing optimization
- Failure recovery with checkpoints
- Anomaly detection and alerts
- Advanced monitoring dashboard

**Success Criteria**:
- ✅ Automatically form teams of 5-10 agents
- ✅ Delegate tasks to team leaders
- ✅ Scale to 100+ agents
- ✅ Detect and alert on anomalies
- ✅ Predict bottlenecks before they occur

---

## Part 7: Design Decisions & Rationale

### Decision 1: Store Tasks in Episodic Events
**Option A**: New dedicated `tasks` table
**Option B**: Extend `episodic_events` with task fields (SELECTED)

**Rationale**:
- ✅ Leverages existing episodic infrastructure
- ✅ Enables consolidation to extract patterns from task execution
- ✅ Natural audit trail (all task transitions are events)
- ✅ Unified query interface
- ✅ No schema conflicts

---

### Decision 2: Use Knowledge Graph for Agent Registry
**Option A**: New `agents` table
**Option B**: Use knowledge graph entities and relations (SELECTED)

**Rationale**:
- ✅ Enables relationship queries (agents with shared skills)
- ✅ Supports community detection (teams)
- ✅ Existing graph infrastructure and indexes
- ✅ Enables semantic skill discovery
- ✅ Unified with rest of knowledge graph

---

### Decision 3: Database-Driven Task Queue + Event-Driven Reactivity
**Option A**: Pure database-driven (polling)
**Option B**: Pure event-driven (pub-sub)
**Option C**: Hybrid (database + events) (SELECTED)

**Rationale**:
- ✅ Database provides durability and fault tolerance
- ✅ Events provide real-time responsiveness
- ✅ Can phase implementation (database first, events later)
- ✅ Redundancy: events fail gracefully to polling
- ✅ Leverage both Athena's strengths

---

### Decision 4: Reuse SubAgentOrchestrator for Parallel Execution
**Option A**: Design new parallel execution framework
**Option B**: Extend existing SubAgentOrchestrator (SELECTED)

**Rationale**:
- ✅ Already implemented and tested
- ✅ Proven pattern (feedback coordination)
- ✅ Reduces implementation scope
- ✅ Familiar to team
- ✅ Can incrementally extend

---

### Decision 5: Semantic + Heuristic Routing
**Option A**: Pure semantic matching (expensive)
**Option B**: Pure heuristic matching (simple, limited)
**Option C**: Hybrid (semantic for learning, heuristic for execution) (SELECTED)

**Rationale**:
- ✅ Semantic used in consolidation (learns skill patterns)
- ✅ Heuristic used in routing (fast, deterministic)
- ✅ Best of both worlds
- ✅ Can improve routing as learning improves
- ✅ Avoids expensive semantic search in hot path

---

## Part 8: Risk Analysis & Mitigation

### Risk 1: SQLite Write Bottleneck
**Risk**: SQLite limited to ~2000 writes/sec
**Impact**: Task throughput capped at 200-300 tasks/sec
**Probability**: High (fundamental SQLite limit)
**Mitigation**:
- ✅ Batch task creation (100 tasks → 1 transaction)
- ✅ Use WAL mode (Write-Ahead Logging)
- ✅ Archive old tasks (keep recent, consolidate old)
- ✅ Phase 6: Migrate to PostgreSQL for distributed Athena

**Acceptance**: ✅ Acceptable for MVP (100+ tasks/sec sufficient)

---

### Risk 2: Event Pattern Matching Latency
**Risk**: Regex matching on every event is expensive
**Impact**: Event notifications delayed (100-200ms)
**Probability**: Medium (depends on regex complexity)
**Mitigation**:
- ✅ Cache pattern compilations
- ✅ Use simple patterns first, semantic as fallback
- ✅ Async notification (non-blocking publish)
- ✅ Monitor pattern matching time, alert if > 50ms

**Acceptance**: ✅ Acceptable (agents expect async notifications)

---

### Risk 3: Knowledge Graph Community Detection Overhead
**Risk**: Leiden algorithm is O(n²) for large graphs
**Impact**: Team formation slow (30+ seconds for 500 agents)
**Probability**: Low (run infrequently, e.g., hourly)
**Mitigation**:
- ✅ Run community detection asynchronously (off-peak)
- ✅ Cache results (validity: 1 hour)
- ✅ Use level-based hierarchies (cluster first, then detect)
- ✅ Monitor execution time, alert if > 60s

**Acceptance**: ✅ Acceptable (infrequent operation)

---

### Risk 4: Task Dependency Deadlocks
**Risk**: Circular task dependencies or missing tasks could deadlock
**Impact**: System stalls, no progress
**Probability**: Low (design validates DAG)
**Mitigation**:
- ✅ Validate DAG on task creation (cycle detection)
- ✅ Timeout on stuck tasks (30+ minutes)
- ✅ Manual intervention tool to unblock
- ✅ Monitoring alert for increasing stalled task count

**Acceptance**: ✅ Acceptable (mitigations prevent)

---

### Risk 5: Agent Failure Cascades
**Risk**: Failed agent causes dependent tasks to fail
**Impact**: Task workflow broken, delays propagate
**Probability**: Medium (agents can fail)
**Mitigation**:
- ✅ Fallback routing (try next-best agent)
- ✅ Retry with exponential backoff
- ✅ Circuit breaker (stop retrying after N failures)
- ✅ Alert on agent failures for investigation

**Acceptance**: ✅ Acceptable (retries handle transient failures)

---

## Part 9: Metrics and Monitoring

### Key Performance Indicators (KPIs)

**Throughput Metrics**:
- Tasks created/sec
- Tasks completed/sec
- Average task duration
- P50, P95, P99 latencies

**Quality Metrics**:
- Task success rate
- Retry rate
- Task failure reasons (category)
- Agent success rates

**System Metrics**:
- Queue depth (pending, assigned)
- Agent utilization (load)
- Event subscription count
- Consolidation frequency

**Operational Metrics**:
- Routing accuracy (task assigned to capable agent)
- Bottleneck identification (slow agents, paths)
- Pattern discovery (new workflows learned)

### Monitoring Queries

```python
# Queue depth
SELECT COUNT(*) FROM episodic_events
WHERE task_status='pending';

# Agent workload
SELECT assigned_to, COUNT(*) as task_count
FROM episodic_events
WHERE task_status IN ('assigned', 'running')
GROUP BY assigned_to;

# Success rate
SELECT
    (SELECT COUNT(*) FROM episodic_events WHERE success=true)::float /
    (SELECT COUNT(*) FROM episodic_events WHERE task_status='completed')
as success_rate;

# Slow tasks
SELECT task_type, AVG(execution_duration_ms) as avg_duration
FROM episodic_events WHERE task_status='completed'
GROUP BY task_type
ORDER BY avg_duration DESC;
```

---

## Part 10: Testing Strategy

### Unit Tests (Phase 1)
- TaskQueue: create, assign, complete, fail, query
- AgentRegistry: register, get_by_capability, update_performance
- CapabilityRouter: route, rank, load calculation

**Target**: 80%+ coverage, 100+ test cases

### Integration Tests (Phase 2-3)
- End-to-end: create task → assign → execute → complete
- Workflow: multi-step with dependencies
- Event flow: subscribe → publish → notify
- Consolidation: extract patterns from task batch

**Target**: 50+ integration tests

### Performance Tests (Phase 3-4)
- Load: 100+ tasks/sec throughput
- Latency: <100ms p50 task assignment
- Scalability: 50-100 agents, 1000+ tasks
- Memory: <500MB overhead

**Target**: Benchmarks document performance targets

### Chaos Tests (Phase 4)
- Agent failure recovery
- Task dependency failures
- Database connection loss
- Event notification delays

**Target**: System remains operational under failures

---

## Conclusion

**Recommended Approach**: Hybrid Database-Driven + Event-Driven orchestration leveraging Athena's existing 8-layer memory system.

**Key Advantages**:
1. ✅ Leverages Athena's strengths (memory, consolidation, learning)
2. ✅ Builds on existing infrastructure (no external dependencies)
3. ✅ Progressive implementation (4 phases, each adds value)
4. ✅ Memory-driven (philosophy aligned)
5. ✅ Scalable to 100+ agents with basic pattern, 1000+ with hierarchical

**Timeline**: 8-12 weeks, 4 phases
**Effort**: ~3,500-5,000 LOC
**Complexity**: Medium-High (but manageable with phased approach)

**Next Steps**:
1. Review and approve design
2. Finalize schema design with team
3. Begin Phase 1 implementation
4. Iterate based on feedback

---

**Document Version**: 1.0
**Date**: 2025-11-10
**Status**: Ready for Implementation
