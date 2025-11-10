"""Integration tests for Phase 1 orchestration layer.

Tests the full workflow: task creation → routing → assignment → execution.
"""

import pytest
from datetime import datetime

from athena.core.database import Database
from athena.episodic.store import EpisodicStore
from athena.graph.store import GraphStore
from athena.meta.store import MetaMemoryStore
from athena.orchestration import (
    TaskQueue,
    AgentRegistry,
    CapabilityRouter,
    Task,
    TaskStatus,
)


@pytest.fixture
def db(tmp_path):
    """Create test database."""
    db_path = tmp_path / "test_orchestration.db"
    return Database(str(db_path))


@pytest.fixture
def episodic_store(db):
    """Create episodic store with schema."""
    return EpisodicStore(db)


@pytest.fixture
def graph_store(db):
    """Create graph store."""
    return GraphStore(db)


@pytest.fixture
def meta_store(db):
    """Create meta-memory store."""
    return MetaMemoryStore(db)


@pytest.fixture
def task_queue(episodic_store, graph_store):
    """Create task queue."""
    return TaskQueue(episodic_store, graph_store)


@pytest.fixture
def agent_registry(graph_store, meta_store):
    """Create agent registry."""
    return AgentRegistry(graph_store, meta_store)


@pytest.fixture
def router(agent_registry):
    """Create capability router."""
    return CapabilityRouter(agent_registry)


class TestTaskQueueBasic:
    """Test TaskQueue basic operations."""

    def test_create_task_returns_id(self, task_queue):
        """Task creation returns task_id."""
        task_id = task_queue.create_task(
            "Research Python async",
            task_type="research",
            priority="high",
            requirements=["python"],
        )

        assert task_id is not None
        assert isinstance(task_id, str)
        assert len(task_id) > 0

    def test_get_task_status(self, task_queue):
        """Can retrieve task status."""
        task_id = task_queue.create_task("Test task", "research")
        task = task_queue.get_task_status(task_id)

        assert task is not None
        assert task.id == task_id
        assert task.status == TaskStatus.PENDING

    def test_poll_pending_tasks(self, task_queue):
        """Can poll for pending tasks."""
        # Create 3 tasks
        ids = [task_queue.create_task(f"Task {i}", "research") for i in range(3)]

        # Poll
        pending = task_queue.poll_tasks(status="pending", limit=10)

        assert len(pending) == 3
        assert all(t.id in ids for t in pending)

    def test_assign_task(self, task_queue):
        """Can assign task to agent."""
        task_id = task_queue.create_task("Research task", "research")

        task_queue.assign_task(task_id, "researcher_bot")

        task = task_queue.get_task_status(task_id)
        assert task.status == TaskStatus.ASSIGNED
        assert task.assigned_to == "researcher_bot"

    def test_complete_task(self, task_queue):
        """Can complete task with result."""
        task_id = task_queue.create_task("Research task", "research")
        task_queue.assign_task(task_id, "researcher_bot")
        task_queue.start_task(task_id)

        task_queue.complete_task(
            task_id, "Found 5 async patterns", metrics={"duration_ms": 1200}
        )

        task = task_queue.get_task_status(task_id)
        assert task.status == TaskStatus.COMPLETED
        assert task.execution_duration_ms == 1200

    def test_fail_task_with_retry(self, task_queue):
        """Failed task with retry resets to pending."""
        task_id = task_queue.create_task("Research task", "research")
        task_queue.assign_task(task_id, "researcher_bot")
        task_queue.start_task(task_id)

        task_queue.fail_task(task_id, "Network timeout", should_retry=True)

        task = task_queue.get_task_status(task_id)
        assert task.status == TaskStatus.PENDING
        assert task.retry_count == 1
        assert task.assigned_to is None

    def test_fail_task_no_retry(self, task_queue):
        """Failed task without retry stays failed."""
        task_id = task_queue.create_task("Research task", "research")
        task_queue.assign_task(task_id, "researcher_bot")

        task_queue.fail_task(task_id, "Agent crashed", should_retry=False)

        task = task_queue.get_task_status(task_id)
        assert task.status == TaskStatus.FAILED
        assert task.error == "Agent crashed"


class TestTaskQueueAdvanced:
    """Test TaskQueue advanced features."""

    def test_task_dependencies(self, task_queue):
        """Tasks can have dependencies."""
        task1 = task_queue.create_task("Research", "research")
        task2 = task_queue.create_task(
            "Analyze", "analysis", dependencies=[task1]
        )

        t2 = task_queue.get_task_status(task2)
        assert task1 in t2.dependencies

    def test_task_priority_sorting(self, task_queue):
        """Tasks polled in priority order."""
        # Create tasks with different priorities
        low_id = task_queue.create_task("Low priority", "research", priority="low")
        high_id = task_queue.create_task("High priority", "research", priority="high")
        med_id = task_queue.create_task("Medium priority", "research", priority="medium")

        # Poll should return high priority first
        pending = task_queue.poll_tasks(status="pending", limit=10)

        assert pending[0].id == high_id
        assert pending[1].id == med_id
        assert pending[2].id == low_id

    def test_query_tasks_with_filters(self, task_queue):
        """Can query tasks with complex filters."""
        # Create tasks
        task1 = task_queue.create_task("Research", "research", priority="high")
        task2 = task_queue.create_task("Analysis", "analysis", priority="low")

        # Query by type
        research_tasks = task_queue.query_tasks({"task_type": "research"})
        assert len(research_tasks) == 1
        assert research_tasks[0].id == task1

        # Query by priority
        high_tasks = task_queue.query_tasks({"priority": "high"})
        assert len(high_tasks) == 1
        assert high_tasks[0].id == task1

    def test_queue_statistics(self, task_queue, agent_registry, router):
        """Can retrieve queue statistics."""
        # Create and process some tasks
        task1 = task_queue.create_task("Task 1", "research", requirements=["python"])
        task2 = task_queue.create_task("Task 2", "research", requirements=["python"])

        agent_registry.register_agent("bot1", ["python"])

        # Assign and complete
        task_queue.assign_task(task1, "bot1")
        task_queue.start_task(task1)
        task_queue.complete_task(task1, "Done", metrics={"duration_ms": 1000})

        stats = task_queue.get_queue_statistics()
        assert stats.completed_count == 1
        assert stats.pending_count == 1
        assert stats.success_rate == 1.0


class TestAgentRegistry:
    """Test AgentRegistry operations."""

    def test_register_agent(self, agent_registry):
        """Can register agent with capabilities."""
        agent_registry.register_agent(
            "researcher_bot",
            ["python", "research", "web"],
            {"max_concurrent_tasks": 10},
        )

        capabilities = agent_registry.get_agent_capability("researcher_bot")
        assert "python" in capabilities
        assert "research" in capabilities

    def test_find_agents_by_capability(self, agent_registry):
        """Can find agents by capability."""
        agent_registry.register_agent("bot1", ["python", "debugging"])
        agent_registry.register_agent("bot2", ["javascript", "testing"])
        agent_registry.register_agent("bot3", ["python", "testing"])

        # Find agents with python
        python_agents = agent_registry.get_agents_by_capability(["python"])
        assert set(python_agents) == {"bot1", "bot3"}

        # Find agents with both python and testing
        both = agent_registry.get_agents_by_capability(["python", "testing"])
        assert both == ["bot3"]

    def test_agent_health(self, agent_registry):
        """Can get agent health metrics."""
        agent_registry.register_agent("bot1", ["python"])

        # Initial health
        health = agent_registry.get_agent_health("bot1")
        assert health["success_rate"] == 1.0
        assert health["total_completed"] == 0

        # Update with task completion
        agent_registry.update_agent_performance("bot1", success=True, duration_ms=1000)

        health = agent_registry.get_agent_health("bot1")
        assert health["success_rate"] == 1.0
        assert health["total_completed"] == 1
        assert health["avg_completion_ms"] == 1000

    def test_agent_performance_tracking(self, agent_registry):
        """Track agent performance across multiple tasks."""
        agent_registry.register_agent("bot1", ["python"])

        # Task 1: Success (1000ms)
        agent_registry.update_agent_performance("bot1", success=True, duration_ms=1000)

        # Task 2: Success (1200ms)
        agent_registry.update_agent_performance("bot1", success=True, duration_ms=1200)

        # Task 3: Failure
        agent_registry.update_agent_performance("bot1", success=False, duration_ms=500)

        health = agent_registry.get_agent_health("bot1")
        assert health["total_completed"] == 2
        assert health["total_failed"] == 1
        assert health["success_rate"] == 2 / 3
        assert abs(health["avg_completion_ms"] - 1100) < 1  # (1000+1200)/2

    def test_learn_new_capability(self, agent_registry):
        """Agent can learn new capabilities."""
        agent_registry.register_agent("bot1", ["python"])

        assert "javascript" not in agent_registry.get_agent_capability("bot1")

        agent_registry.learn_new_capability("bot1", "javascript", confidence=0.9)

        assert "javascript" in agent_registry.get_agent_capability("bot1")

    def test_deregister_agent(self, agent_registry):
        """Can deregister agent."""
        agent_registry.register_agent("bot1", ["python"])
        agent_registry.deregister_agent("bot1")

        health = agent_registry.get_agent_health("bot1")
        assert health["status"] == "not_found"

    def test_agent_statistics(self, agent_registry):
        """Can retrieve agent statistics."""
        agent_registry.register_agent("bot1", ["python", "javascript"])
        agent_registry.register_agent("bot2", ["python", "testing"])
        agent_registry.register_agent("bot3", ["rust"])

        stats = agent_registry.get_agent_statistics()
        assert stats.total_agents == 3
        assert stats.skill_distribution.get("python") == 2
        assert stats.skill_distribution.get("javascript") == 1


class TestCapabilityRouter:
    """Test CapabilityRouter operations."""

    def test_route_task_to_capable_agent(self, agent_registry, router, task_queue):
        """Routes task to capable agent."""
        agent_registry.register_agent("bot_python", ["python", "web"])
        agent_registry.register_agent("bot_rust", ["rust"])

        # Create task requiring python
        task = task_queue.create_task(
            "Debug async code", "research", requirements=["python"]
        )
        task_obj = task_queue.get_task_status(task)

        # Route should select bot_python
        routed_agent = router.route_task(task_obj)
        assert routed_agent == "bot_python"

    def test_route_task_no_capable_agent(self, agent_registry, router, task_queue):
        """Returns None when no capable agent."""
        agent_registry.register_agent("bot1", ["rust"])

        task = task_queue.create_task(
            "Python task", "research", requirements=["python"]
        )
        task_obj = task_queue.get_task_status(task)

        routed = router.route_task(task_obj)
        assert routed is None

    def test_rank_candidates_by_success_rate(self, agent_registry, router):
        """Ranks agents by success rate."""
        agent_registry.register_agent("bot1", ["python"])
        agent_registry.register_agent("bot2", ["python"])

        # bot1: 100% success
        agent_registry.update_agent_performance("bot1", success=True, duration_ms=1000)
        agent_registry.update_agent_performance("bot1", success=True, duration_ms=1000)

        # bot2: 50% success
        agent_registry.update_agent_performance("bot2", success=True, duration_ms=1000)
        agent_registry.update_agent_performance("bot2", success=False, duration_ms=1000)

        # bot1 should rank higher
        ranked = router.rank_candidates(["bot1", "bot2"])
        assert ranked[0][0] == "bot1"  # bot1 has higher score

    def test_exclude_agents_from_routing(self, agent_registry, router, task_queue):
        """Can exclude agents from routing."""
        agent_registry.register_agent("bot1", ["python"])
        agent_registry.register_agent("bot2", ["python"])

        task = task_queue.create_task(
            "Python task", "research", requirements=["python"]
        )
        task_obj = task_queue.get_task_status(task)

        # Route excluding bot1 should select bot2
        routed = router.route_task(task_obj, exclude_agents=["bot1"])
        assert routed == "bot2"


class TestEndToEndWorkflow:
    """Test complete orchestration workflow."""

    def test_research_workflow(self, task_queue, agent_registry, router):
        """Complete research workflow: create → route → execute → complete."""
        # Register researcher agent
        agent_registry.register_agent(
            "research_bot",
            ["python", "web", "research"],
            {"max_concurrent_tasks": 5},
        )

        # Create research task
        task_id = task_queue.create_task(
            "Find asyncio patterns",
            task_type="research",
            priority="high",
            requirements=["python"],
        )

        # Verify task created
        task = task_queue.get_task_status(task_id)
        assert task.status == TaskStatus.PENDING

        # Route to agent
        agent = router.route_task(task)
        assert agent == "research_bot"

        # Assign task
        task_queue.assign_task(task_id, agent)
        task = task_queue.get_task_status(task_id)
        assert task.status == TaskStatus.ASSIGNED

        # Agent starts task
        task_queue.start_task(task_id)
        task = task_queue.get_task_status(task_id)
        assert task.status == TaskStatus.RUNNING

        # Agent completes task
        result = "Found 5 async patterns with examples"
        task_queue.complete_task(
            task_id,
            result,
            metrics={"duration_ms": 2500, "rows_processed": 100},
        )

        task = task_queue.get_task_status(task_id)
        assert task.status == TaskStatus.COMPLETED
        assert task.execution_duration_ms == 2500

        # Update agent metrics
        agent_registry.update_agent_performance(
            agent, success=True, duration_ms=2500
        )

        health = agent_registry.get_agent_health(agent)
        assert health["success_rate"] == 1.0

    def test_multi_task_workflow(self, task_queue, agent_registry, router):
        """Multiple tasks with routing and load balancing."""
        # Register 2 agents
        agent_registry.register_agent("bot1", ["python", "research"])
        agent_registry.register_agent("bot2", ["python", "research"])

        # Create 3 research tasks
        task_ids = [
            task_queue.create_task(
                f"Research {i}", "research", requirements=["python"]
            )
            for i in range(3)
        ]

        # Route each task
        routed_agents = []
        for task_id in task_ids:
            task = task_queue.get_task_status(task_id)
            agent = router.route_task(task)
            routed_agents.append(agent)
            task_queue.assign_task(task_id, agent)

        # All tasks should be assigned
        assert all(a is not None for a in routed_agents)
        assert len(routed_agents) == 3

        # Verify queue state
        stats = task_queue.get_queue_statistics()
        assert stats.assigned_count == 3
        assert stats.pending_count == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
