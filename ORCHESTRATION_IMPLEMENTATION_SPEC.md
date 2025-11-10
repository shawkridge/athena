# Orchestration Implementation Specification

**Quick Reference for Development**
**Companion to**: OPTIMAL_ORCHESTRATION_DESIGN.md
**For**: Phase 1 Implementation (Weeks 1-3)

---

## Phase 1 Scope

### What We're Building
1. **TaskQueue** - Episodic-backed task management
2. **AgentRegistry** - Knowledge graph-backed agent capabilities
3. **CapabilityRouter** - Intelligent task-to-agent routing
4. **MCP Tools** - Expose operations via protocol
5. **Integration Tests** - 60+ test cases

### What We're NOT Building (Phase 2+)
- Event-driven pub-sub (Phase 2)
- Consolidation integration (Phase 3)
- Hierarchical teams (Phase 4)
- Learning-based routing (Phase 4)

---

## File Structure

```
src/athena/orchestration/
├── __init__.py                          # Module exports
├── task_queue.py                        # TaskQueue class (~300 LOC)
├── agent_registry.py                    # AgentRegistry class (~250 LOC)
├── capability_router.py                 # CapabilityRouter class (~200 LOC)
├── models.py                            # Data models (Task, Agent, etc.) (~150 LOC)
└── exceptions.py                        # Custom exceptions (~50 LOC)

src/athena/mcp/
├── handlers_orchestration.py            # MCP tool definitions (~400 LOC)
└── (existing handlers files)            # Update operation_router

tests/integration/
├── test_orchestration.py                # Integration tests (~600 LOC)
├── test_task_queue.py                   # Unit tests for TaskQueue (~400 LOC)
├── test_agent_registry.py               # Unit tests for AgentRegistry (~350 LOC)
└── test_capability_router.py            # Unit tests for CapabilityRouter (~250 LOC)
```

---

## Database Schema Changes

### Add to episodic schema initialization

```python
# src/athena/core/database.py _init_schema() method
# Add after existing episodic_events creation

cursor.execute("""
    ALTER TABLE episodic_events ADD COLUMN IF NOT EXISTS (
        task_id TEXT UNIQUE,
        task_type TEXT,
        task_status TEXT DEFAULT 'pending',
        assigned_to TEXT,
        assigned_at INTEGER,
        requirements TEXT,
        dependencies TEXT,
        started_at INTEGER,
        completed_at INTEGER,
        priority TEXT DEFAULT 'medium',
        result_task_id INTEGER,
        error_message TEXT,
        retry_count INTEGER DEFAULT 0,
        retry_until INTEGER,
        execution_duration_ms INTEGER,
        estimated_duration_ms INTEGER,
        success BOOLEAN,
        task_batch_id TEXT
    )
""")

# Create indexes
cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_task_status
    ON episodic_events(task_status)
""")

cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_assigned_to
    ON episodic_events(assigned_to)
""")

cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_task_type
    ON episodic_events(task_type)
""")

# For event subscriptions (Phase 2)
cursor.execute("""
    CREATE TABLE IF NOT EXISTS event_subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agent_id TEXT NOT NULL,
        event_pattern TEXT NOT NULL,
        handler_url TEXT,
        pattern_type TEXT DEFAULT 'regex',
        is_active BOOLEAN DEFAULT 1,
        created_at INTEGER NOT NULL,
        last_triggered INTEGER,
        trigger_count INTEGER DEFAULT 0,
        UNIQUE(agent_id, event_pattern)
    )
""")

self.conn.commit()
```

---

## Data Models

### src/athena/orchestration/models.py

```python
"""Data models for orchestration layer."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any


class TaskStatus(str, Enum):
    """Task lifecycle states."""
    PENDING = "pending"        # Created, waiting for assignment
    ASSIGNED = "assigned"      # Assigned to agent, waiting to start
    RUNNING = "running"        # Agent executing
    COMPLETED = "completed"    # Finished successfully
    FAILED = "failed"          # Failed, not retrying
    BLOCKED = "blocked"        # Blocked by dependency failure


@dataclass
class Task:
    """Task definition."""
    id: Optional[str] = None                    # UUID
    content: str = ""                           # Description
    task_type: str = ""                         # research, analysis, etc.
    status: TaskStatus = TaskStatus.PENDING
    priority: str = "medium"                    # low, medium, high
    requirements: List[str] = field(default_factory=list)  # Required skills
    dependencies: List[str] = field(default_factory=list)  # Task IDs
    assigned_to: Optional[str] = None           # Agent ID
    created_at: Optional[datetime] = None
    assigned_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[str] = None
    error: Optional[str] = None
    retry_count: int = 0
    execution_duration_ms: Optional[int] = None


@dataclass
class Agent:
    """Agent definition."""
    id: str                                     # Unique ID
    capabilities: List[str] = field(default_factory=list)
    max_concurrent_tasks: int = 5
    success_rate: float = 1.0
    avg_completion_ms: float = 0.0
    current_load: int = 0                       # Running tasks
    total_completed: int = 0
    total_failed: int = 0
    last_updated: Optional[datetime] = None


@dataclass
class RoutingDecision:
    """Result of routing algorithm."""
    selected_agent: Optional[str]               # Agent ID or None
    candidates: List[str] = field(default_factory=list)
    scores: Dict[str, float] = field(default_factory=dict)
    reason: str = ""
```

---

## Component Implementation Template

### TaskQueue Implementation Skeleton

```python
# src/athena/orchestration/task_queue.py

"""Task queue backed by episodic memory."""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any

from ..core.database import Database
from ..episodic.store import EpisodicStore
from ..episodic.models import EpisodicEvent, EventType, EventOutcome
from ..graph.store import GraphStore
from .models import Task, TaskStatus


class TaskQueue:
    """Manage task lifecycle in episodic memory."""

    def __init__(self, episodic_store: EpisodicStore, graph_store: GraphStore):
        self.episodic = episodic_store
        self.graph = graph_store
        self.db = episodic_store.db

    def create_task(self,
                   content: str,
                   task_type: str,
                   priority: str = "medium",
                   requirements: Optional[List[str]] = None,
                   dependencies: Optional[List[str]] = None) -> str:
        """
        Create task, return task_id.

        Args:
            content: Task description
            task_type: Type of task (research, analysis, etc.)
            priority: low, medium, high
            requirements: Required capabilities
            dependencies: Task IDs this depends on

        Returns:
            task_id (UUID string)
        """
        task_id = str(uuid.uuid4())

        event = EpisodicEvent(
            project_id=0,  # TODO: Get from context
            session_id="system",
            event_type=EventType.ACTION,
            content=content,
            outcome=EventOutcome.ONGOING,
            # Task-specific fields
            **{
                'task_id': task_id,
                'task_type': task_type,
                'task_status': 'pending',
                'priority': priority,
                'requirements': str(requirements or []),
                'dependencies': str(dependencies or []),
                'created_at': int(datetime.now().timestamp()),
            }
        )

        # Store in episodic memory
        stored_id = self.episodic.store_event(event)

        return task_id

    def poll_tasks(self,
                  agent_id: Optional[str] = None,
                  status: str = "pending",
                  limit: int = 10) -> List[Task]:
        """
        Get pending/assigned tasks for agent.

        Args:
            agent_id: If specified, only tasks assigned to this agent
            status: pending, assigned, running
            limit: Max tasks to return

        Returns:
            List of Task objects
        """
        # Query episodic_events for tasks with given status
        cursor = self.db.conn.cursor()

        query = """
            SELECT * FROM episodic_events
            WHERE task_status = ?
        """
        params = [status]

        if agent_id:
            query += " AND assigned_to = ?"
            params.append(agent_id)

        query += f" LIMIT {limit}"

        cursor.execute(query, params)
        rows = cursor.fetchall()

        return [self._row_to_task(row) for row in rows]

    def assign_task(self, task_id: str, agent_id: str) -> None:
        """
        Assign task to agent.

        Args:
            task_id: Task UUID
            agent_id: Agent ID
        """
        cursor = self.db.conn.cursor()

        cursor.execute("""
            UPDATE episodic_events
            SET task_status = 'assigned',
                assigned_to = ?,
                assigned_at = ?
            WHERE task_id = ?
        """, [agent_id, int(datetime.now().timestamp()), task_id])

        self.db.conn.commit()

    def start_task(self, task_id: str) -> None:
        """Mark task as running."""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            UPDATE episodic_events
            SET task_status = 'running', started_at = ?
            WHERE task_id = ?
        """, [int(datetime.now().timestamp()), task_id])
        self.db.conn.commit()

    def complete_task(self, task_id: str, result: str,
                     metrics: Optional[Dict[str, Any]] = None) -> None:
        """
        Mark task complete with result.

        Args:
            task_id: Task UUID
            result: Result content
            metrics: Execution metrics {duration_ms, ...}
        """
        cursor = self.db.conn.cursor()

        metrics = metrics or {}
        duration = metrics.get('duration_ms', 0)

        cursor.execute("""
            UPDATE episodic_events
            SET task_status = 'completed',
                completed_at = ?,
                execution_duration_ms = ?,
                success = 1
            WHERE task_id = ?
        """, [int(datetime.now().timestamp()), duration, task_id])

        self.db.conn.commit()

        # TODO: Store result as separate event linked to task
        # TODO: Publish task_completed event for subscribers

    def fail_task(self, task_id: str, error: str,
                 should_retry: bool = True) -> None:
        """
        Mark task failed, optionally retry.

        Args:
            task_id: Task UUID
            error: Error message
            should_retry: Whether to schedule retry
        """
        cursor = self.db.conn.cursor()

        if should_retry:
            # Retry: reset status, increment counter
            cursor.execute("""
                UPDATE episodic_events
                SET task_status = 'pending',
                    assigned_to = NULL,
                    retry_count = retry_count + 1,
                    error_message = NULL
                WHERE task_id = ?
            """, [task_id])
        else:
            # No retry: mark failed
            cursor.execute("""
                UPDATE episodic_events
                SET task_status = 'failed',
                    error_message = ?,
                    completed_at = ?
                WHERE task_id = ?
            """, [error, int(datetime.now().timestamp()), task_id])

        self.db.conn.commit()

        # TODO: Publish task_failed event for subscribers

    def get_task_status(self, task_id: str) -> Optional[Task]:
        """Get current task state."""
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT * FROM episodic_events WHERE task_id = ?",
                      [task_id])
        row = cursor.fetchone()
        return self._row_to_task(row) if row else None

    def query_tasks(self, filters: Dict[str, Any]) -> List[Task]:
        """
        Complex query with multiple filters.

        Filters:
            status: pending, assigned, running, completed, failed
            agent_id: assigned to agent
            task_type: specific task type
            priority: low, medium, high
            created_after: timestamp
        """
        cursor = self.db.conn.cursor()

        query = "SELECT * FROM episodic_events WHERE 1=1"
        params = []

        if 'status' in filters:
            query += " AND task_status = ?"
            params.append(filters['status'])

        if 'agent_id' in filters:
            query += " AND assigned_to = ?"
            params.append(filters['agent_id'])

        if 'task_type' in filters:
            query += " AND task_type = ?"
            params.append(filters['task_type'])

        if 'priority' in filters:
            query += " AND priority = ?"
            params.append(filters['priority'])

        if 'created_after' in filters:
            query += " AND created_at > ?"
            params.append(filters['created_after'])

        cursor.execute(query, params)
        return [self._row_to_task(row) for row in cursor.fetchall()]

    # Private helpers
    def _row_to_task(self, row: Any) -> Task:
        """Convert database row to Task object."""
        return Task(
            id=row['task_id'],
            content=row['content'],
            task_type=row['task_type'] or '',
            status=TaskStatus(row['task_status']),
            priority=row['priority'] or 'medium',
            requirements=eval(row['requirements'] or '[]'),  # JSON parse
            dependencies=eval(row['dependencies'] or '[]'),
            assigned_to=row['assigned_to'],
            created_at=datetime.fromtimestamp(row['created_at']),
            # ... other fields
        )
```

---

## Testing Template

### Phase 1 Test Coverage

```python
# tests/integration/test_orchestration.py

"""Integration tests for orchestration layer."""

import pytest
from datetime import datetime

from athena.orchestration.task_queue import TaskQueue
from athena.orchestration.agent_registry import AgentRegistry
from athena.orchestration.capability_router import CapabilityRouter
from athena.orchestration.models import TaskStatus


class TestTaskQueueIntegration:
    """End-to-end task queue tests."""

    @pytest.fixture
    def task_queue(self, episodic_store, graph_store):
        return TaskQueue(episodic_store, graph_store)

    @pytest.fixture
    def agent_registry(self, graph_store, meta_store):
        return AgentRegistry(graph_store, meta_store)

    @pytest.fixture
    def router(self, agent_registry, meta_store):
        return CapabilityRouter(agent_registry, meta_store)

    def test_create_task_returns_id(self, task_queue):
        """Task creation returns task_id."""
        task_id = task_queue.create_task(
            "Research framework",
            task_type="research",
            priority="high",
            requirements=["python", "web"]
        )

        assert task_id is not None
        assert isinstance(task_id, str)
        assert len(task_id) > 0

    def test_task_lifecycle(self, task_queue, agent_registry, router):
        """Full task lifecycle: create → assign → complete."""
        # Register agent
        agent_registry.register_agent("research_bot", ["python", "web"])

        # Create task
        task_id = task_queue.create_task(
            "Find Python async patterns",
            task_type="research",
            requirements=["python"]
        )

        # Route to agent
        agent = router.route_task({"requirements": ["python"]})
        assert agent == "research_bot"

        # Assign
        task_queue.assign_task(task_id, agent)
        task = task_queue.get_task_status(task_id)
        assert task.status == TaskStatus.ASSIGNED

        # Start
        task_queue.start_task(task_id)
        task = task_queue.get_task_status(task_id)
        assert task.status == TaskStatus.RUNNING

        # Complete
        task_queue.complete_task(task_id, "Found 5 patterns",
                                metrics={"duration_ms": 1200})
        task = task_queue.get_task_status(task_id)
        assert task.status == TaskStatus.COMPLETED
        assert task.execution_duration_ms == 1200

    def test_poll_pending_tasks(self, task_queue):
        """Poll for pending tasks."""
        # Create 3 tasks
        ids = [
            task_queue.create_task(f"Task {i}", "research")
            for i in range(3)
        ]

        # Poll
        pending = task_queue.poll_tasks(status="pending", limit=5)
        assert len(pending) == 3

    def test_task_dependencies(self, task_queue):
        """Tasks with dependencies."""
        task1 = task_queue.create_task("Research", "research")
        task2 = task_queue.create_task(
            "Analyze",
            "analysis",
            dependencies=[task1]
        )

        # task2 depends on task1
        task = task_queue.get_task_status(task2)
        assert task1 in task.dependencies

    # ... More tests (30+ total for Phase 1)
```

---

## MCP Tool Integration

### Handlers Setup

```python
# src/athena/mcp/handlers_orchestration.py

"""Orchestration MCP tools."""

from typing import Optional, List, Dict, Any

from ..orchestration.task_queue import TaskQueue
from ..orchestration.agent_registry import AgentRegistry
from ..orchestration.capability_router import CapabilityRouter


class OrchestrationHandlers:
    """MCP handlers for orchestration operations."""

    def __init__(self, task_queue: TaskQueue, registry: AgentRegistry,
                router: CapabilityRouter):
        self.queue = task_queue
        self.registry = registry
        self.router = router

    def register_tools(self, server):
        """Register all orchestration tools with MCP server."""

        @server.tool()
        def orchestration_create_task(
            content: str,
            task_type: str,
            priority: str = "medium",
            requirements: Optional[List[str]] = None,
            dependencies: Optional[List[str]] = None
        ) -> Dict[str, Any]:
            """Create a new task in the queue."""
            task_id = self.queue.create_task(
                content, task_type, priority, requirements, dependencies
            )
            return {
                "task_id": task_id,
                "status": "pending",
                "created": True
            }

        @server.tool()
        def orchestration_poll_tasks(
            agent_id: Optional[str] = None,
            status: str = "pending",
            limit: int = 10
        ) -> List[Dict]:
            """Poll for pending/assigned tasks."""
            tasks = self.queue.poll_tasks(agent_id, status, limit)
            return [
                {
                    "id": t.id,
                    "content": t.content,
                    "type": t.task_type,
                    "priority": t.priority,
                    "requirements": t.requirements,
                }
                for t in tasks
            ]

        @server.tool()
        def orchestration_register_agent(
            agent_id: str,
            capabilities: List[str],
            max_concurrent: int = 5
        ) -> Dict:
            """Register agent with capabilities."""
            self.registry.register_agent(
                agent_id, capabilities,
                {"max_concurrent_tasks": max_concurrent}
            )
            return {"agent_id": agent_id, "registered": True}

        @server.tool()
        def orchestration_find_capable_agents(
            requirements: List[str]
        ) -> List[Dict]:
            """Find agents with required capabilities."""
            agents = self.registry.get_agents_by_capability(requirements)
            return [
                {
                    "id": agent_id,
                    "success_rate": self.registry.get_agent_health(
                        agent_id
                    ).get("success_rate", 0)
                }
                for agent_id in agents
            ]

        # ... More tools (15+ total)
```

---

## Phase 1 Checklist

- [ ] **Schema**: Update database.py with task fields
- [ ] **Models**: Create orchestration/models.py (Task, Agent, RoutingDecision)
- [ ] **TaskQueue**: Implement task_queue.py (6 methods, ~300 LOC)
- [ ] **AgentRegistry**: Implement agent_registry.py (8 methods, ~250 LOC)
- [ ] **Router**: Implement capability_router.py (5 methods, ~200 LOC)
- [ ] **Exceptions**: Create exceptions.py (custom exceptions)
- [ ] **Tests**: Write test_task_queue.py (10+ tests, ~400 LOC)
- [ ] **Tests**: Write test_agent_registry.py (10+ tests, ~350 LOC)
- [ ] **Tests**: Write test_capability_router.py (8+ tests, ~250 LOC)
- [ ] **Tests**: Write test_orchestration.py (20+ integration tests, ~600 LOC)
- [ ] **MCP**: Create handlers_orchestration.py (~400 LOC)
- [ ] **Integration**: Update manager.py to expose OrchestrationManager
- [ ] **Documentation**: Create usage examples (3+ examples)
- [ ] **Testing**: Run full suite, achieve 80%+ coverage

**Total LOC**: ~3,500-4,000
**Total Tests**: 60+
**Timeline**: 2-3 weeks

---

**Next Phase**: Event-Driven Pub-Sub (Weeks 4-5)

