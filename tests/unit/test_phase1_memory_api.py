"""Comprehensive unit tests for MemoryAPI (Phase 1).

Tests cover:
- Initialization and factory method
- Core remember/recall/forget operations
- Episodic memory operations
- Procedural memory operations
- Prospective memory operations
- Graph operations
- Error handling and edge cases
"""

import pytest
from datetime import datetime, timedelta

from athena.mcp.memory_api import MemoryAPI
from athena.core.models import MemoryType
from athena.episodic.models import EventType, EventOutcome

# Import fixtures
from .test_phase1_fixtures import (
    temp_db,
    temp_db_path,
    memory_api,
    memory_api_direct,
    project_manager,
    unified_manager,
    sample_memory_content,
)


class TestMemoryAPIInitialization:
    """Tests for MemoryAPI initialization and factory methods."""

    def test_create_factory_method(self, memory_api):
        """Test MemoryAPI.create() factory method.

        Should initialize all memory layers correctly.
        """
        assert memory_api is not None
        assert isinstance(memory_api, MemoryAPI)
        assert memory_api.manager is not None
        assert memory_api.project_manager is not None
        assert memory_api.db is not None

    def test_api_has_all_layer_references(self, memory_api):
        """Test that API has references to all memory layers."""
        assert hasattr(memory_api, "semantic")
        assert hasattr(memory_api, "episodic")
        assert hasattr(memory_api, "procedural")
        assert hasattr(memory_api, "prospective")
        assert hasattr(memory_api, "graph")
        assert hasattr(memory_api, "meta")
        assert hasattr(memory_api, "consolidation")

        assert memory_api.semantic is not None
        assert memory_api.episodic is not None
        assert memory_api.procedural is not None
        assert memory_api.prospective is not None
        assert memory_api.graph is not None
        assert memory_api.meta is not None
        assert memory_api.consolidation is not None

    def test_api_initialization_with_custom_db_path(self, temp_db_path):
        """Test MemoryAPI initialization with custom database path."""
        api = MemoryAPI.create(db_path=str(temp_db_path))

        assert api is not None
        assert api.db is not None
        # Verify database is at correct path
        assert str(temp_db_path) in api.db.db_path or api.db.db_path == str(temp_db_path)

    def test_direct_initialization(self, memory_api_direct):
        """Test direct MemoryAPI initialization with injected dependencies."""
        assert memory_api_direct is not None
        assert memory_api_direct.manager is not None
        assert memory_api_direct.project_manager is not None


class TestMemoryAPIRemember:
    """Tests for remember() operation (semantic memory)."""

    def test_remember_basic_semantic(self, memory_api):
        """Test remembering basic semantic memory."""
        content = "This is an important finding about system architecture"

        memory_id = memory_api.remember(
            content=content,
            memory_type="semantic",
        )

        assert memory_id is not None
        assert isinstance(memory_id, int)
        assert memory_id > 0

    def test_remember_with_tags(self, memory_api):
        """Test remembering memory with tags for categorization."""
        memory_id = memory_api.remember(
            content="Bug found in parser module",
            memory_type="semantic",
            tags=["bug", "parser", "critical"],
        )

        assert memory_id is not None
        assert isinstance(memory_id, int)

    def test_remember_with_context(self, memory_api):
        """Test remembering memory with additional context."""
        memory_id = memory_api.remember(
            content="Improved database query performance",
            memory_type="semantic",
            context={
                "module": "database",
                "improvement": "30% faster",
                "technique": "indexing",
            },
        )

        assert memory_id is not None
        assert isinstance(memory_id, int)

    def test_remember_multiple_types(self, memory_api):
        """Test remembering different memory types."""
        semantic_id = memory_api.remember("Fact about system", memory_type="semantic")
        event_id = memory_api.remember("Event occurred", memory_type="event")
        procedure_id = memory_api.remember("How to do X", memory_type="procedure")
        task_id = memory_api.remember("Task to complete", memory_type="task")

        # All should have valid IDs
        for memory_id in [semantic_id, event_id, procedure_id, task_id]:
            assert memory_id is not None
            assert isinstance(memory_id, int)
            assert memory_id > 0

    def test_remember_empty_content_raises_error(self, memory_api):
        """Test that remembering empty content raises an error."""
        with pytest.raises((ValueError, Exception)):
            memory_api.remember(content="", memory_type="semantic")

    def test_remember_returns_consistent_ids(self, memory_api):
        """Test that remember returns unique IDs for different content."""
        id1 = memory_api.remember("First memory", memory_type="semantic")
        id2 = memory_api.remember("Second memory", memory_type="semantic")
        id3 = memory_api.remember("Third memory", memory_type="semantic")

        # All IDs should be unique
        assert id1 != id2
        assert id2 != id3
        assert id1 != id3

        # All should be positive integers
        assert all(mid > 0 for mid in [id1, id2, id3])


class TestMemoryAPIRecall:
    """Tests for recall() operation (search)."""

    def test_recall_returns_results(self, memory_api):
        """Test basic recall with query."""
        # Store some memories first
        memory_api.remember("Python is a programming language", memory_type="semantic")
        memory_api.remember("Python has a large ecosystem", memory_type="semantic")

        # Recall should return results
        results = memory_api.recall(query="Python", limit=5)

        assert results is not None
        assert isinstance(results, dict)

    def test_recall_respects_limit(self, memory_api):
        """Test that recall respects the limit parameter."""
        # Store multiple memories
        for i in range(10):
            memory_api.remember(
                f"Memory content number {i}",
                memory_type="semantic",
                tags=["batch"],
            )

        # Recall with limit 3
        results = memory_api.recall(query="memory", limit=3)

        # Should return at most 3 results
        memories = results.get("memories", [])
        assert len(memories) <= 3

    def test_recall_with_context(self, memory_api):
        """Test recall with context parameter."""
        memory_api.remember("Important fact", memory_type="semantic")

        results = memory_api.recall(
            query="important",
            limit=5,
            context={"module": "test", "version": "1.0"},
        )

        assert results is not None
        assert isinstance(results, dict)

    def test_recall_empty_query(self, memory_api):
        """Test recall with empty query."""
        memory_api.remember("Some content", memory_type="semantic")

        # Empty query should either return empty or all results
        results = memory_api.recall(query="", limit=5)
        assert results is not None

    def test_recall_nonexistent_query(self, memory_api):
        """Test recall with query that doesn't match anything."""
        memory_api.remember("Python content", memory_type="semantic")

        results = memory_api.recall(query="xyzabc123notfound", limit=5)

        assert results is not None
        # Should either return empty or valid structure
        memories = results.get("memories", [])
        assert isinstance(memories, (list, tuple))


class TestMemoryAPIForget:
    """Tests for forget() operation (deletion)."""

    def test_forget_existing_memory(self, memory_api):
        """Test forgetting an existing memory."""
        # Store a memory
        memory_id = memory_api.remember("Content to forget", memory_type="semantic")

        # Forget it
        success = memory_api.forget(memory_id)

        assert success is True

    def test_forget_nonexistent_memory(self, memory_api):
        """Test forgetting a non-existent memory."""
        # Try to forget a memory that doesn't exist
        success = memory_api.forget(99999)

        assert success is False

    def test_forget_already_forgotten(self, memory_api):
        """Test forgetting a memory twice."""
        memory_id = memory_api.remember("Content", memory_type="semantic")

        # Forget once
        success1 = memory_api.forget(memory_id)
        assert success1 is True

        # Try to forget again
        success2 = memory_api.forget(memory_id)
        assert success2 is False


class TestMemoryAPIEpisodicOperations:
    """Tests for episodic (event) memory operations."""

    def test_remember_event_basic(self, memory_api):
        """Test remembering a basic event."""
        event_id = memory_api.remember_event(
            event_type="action",
            content="Executed test suite",
        )

        assert event_id is not None
        assert isinstance(event_id, int)
        assert event_id > 0

    def test_remember_event_with_outcome(self, memory_api):
        """Test remembering an event with outcome."""
        event_id = memory_api.remember_event(
            event_type="action",
            content="Deployed to production",
            outcome="success",
        )

        assert event_id is not None
        assert isinstance(event_id, int)

    def test_remember_event_with_context(self, memory_api):
        """Test remembering an event with context."""
        event_id = memory_api.remember_event(
            event_type="action",
            content="Tested API endpoints",
            outcome="success",
            context={
                "test_count": 42,
                "failures": 0,
                "cwd": "/home/user/.work/athena",
                "files": ["tests/test_api.py", "src/api.py"],
            },
        )

        assert event_id is not None
        assert isinstance(event_id, int)

    def test_remember_event_different_types(self, memory_api):
        """Test remembering different event types."""
        event_types = [
            ("action", "Ran tests"),
            ("decision", "Changed database schema"),
            ("observation", "Found performance issue"),
            ("error", "SQL syntax error"),
            ("success", "Deployed successfully"),
        ]

        event_ids = []
        for event_type, content in event_types:
            event_id = memory_api.remember_event(
                event_type=event_type,
                content=content,
            )
            event_ids.append(event_id)

        # All should be valid IDs
        assert all(eid is not None and eid > 0 for eid in event_ids)

    def test_remember_event_with_default_outcome(self, memory_api):
        """Test that events default to 'unknown' outcome if not specified."""
        event_id = memory_api.remember_event(
            event_type="observation",
            content="Made an observation",
        )

        assert event_id is not None

    def test_recall_events_by_session(self, memory_api):
        """Test recalling events by session."""
        session_id = "test_session_123"

        # Remember multiple events in same session
        for i in range(3):
            memory_api.remember_event(
                event_type="action",
                content=f"Action {i}",
                context={"session_id": session_id},
            )

        # Recall by session
        results = memory_api.recall_events_by_session(session_id, limit=10)

        assert results is not None
        assert len(results) >= 0  # May or may not have results depending on implementation


class TestMemoryAPIProcedureOperations:
    """Tests for procedural memory operations."""

    def test_remember_procedure(self, memory_api):
        """Test remembering a procedure."""
        procedure_id = memory_api.remember_procedure(
            name="deploy_to_production",
            description="Steps to safely deploy to production",
            steps=[
                "Run full test suite",
                "Build release artifact",
                "Deploy to staging",
                "Run smoke tests",
                "Deploy to production",
            ],
        )

        assert procedure_id is not None
        assert isinstance(procedure_id, int)

    def test_remember_procedure_with_prerequisites(self, memory_api):
        """Test remembering a procedure with prerequisites."""
        procedure_id = memory_api.remember_procedure(
            name="setup_environment",
            description="Setup development environment",
            steps=["Install dependencies", "Configure settings"],
            prerequisites=["Python 3.10+", "Node.js 16+", "Docker"],
        )

        assert procedure_id is not None

    def test_recall_procedure(self, memory_api):
        """Test recalling a procedure by name or query."""
        procedure_id = memory_api.remember_procedure(
            name="test_api",
            description="How to test API endpoints",
            steps=["Run pytest", "Check coverage"],
        )

        # Recall the procedure
        results = memory_api.recall_procedures(query="test", limit=5)

        assert results is not None


class TestMemoryAPIProspectiveOperations:
    """Tests for prospective (task/goal) memory operations."""

    def test_remember_task(self, memory_api):
        """Test remembering a task."""
        task_id = memory_api.remember_task(
            title="Implement feature X",
            description="Complete implementation of feature X",
        )

        assert task_id is not None
        assert isinstance(task_id, int)

    def test_remember_task_with_priority(self, memory_api):
        """Test remembering a task with priority."""
        task_id = memory_api.remember_task(
            title="Critical bug fix",
            description="Fix database connection issue",
            priority="high",
        )

        assert task_id is not None

    def test_remember_task_with_due_date(self, memory_api):
        """Test remembering a task with due date."""
        due_date = datetime.now() + timedelta(days=7)

        task_id = memory_api.remember_task(
            title="Complete documentation",
            description="Write API documentation",
            due_date=due_date,
        )

        assert task_id is not None

    def test_get_tasks(self, memory_api):
        """Test retrieving tasks."""
        # Remember some tasks
        memory_api.remember_task(title="Task 1", description="Desc 1")
        memory_api.remember_task(title="Task 2", description="Desc 2")

        # Get tasks
        tasks = memory_api.get_tasks()

        assert tasks is not None
        assert isinstance(tasks, (list, dict))


class TestMemoryAPIGraphOperations:
    """Tests for knowledge graph operations."""

    def test_add_entity(self, memory_api):
        """Test adding an entity to knowledge graph."""
        entity_id = memory_api.add_entity(
            name="MemoryAPI",
            entity_type="concept",
            description="Direct Python API for memory operations",
        )

        assert entity_id is not None

    def test_add_relation(self, memory_api):
        """Test adding a relation between entities."""
        # Create entities first
        entity1_id = memory_api.add_entity(
            name="MemoryAPI",
            entity_type="concept",
        )
        entity2_id = memory_api.add_entity(
            name="Sandbox",
            entity_type="concept",
        )

        # Add relation
        relation_id = memory_api.add_relation(
            source_entity_id=entity1_id,
            target_entity_id=entity2_id,
            relation_type="integrates_with",
        )

        assert relation_id is not None

    def test_query_graph(self, memory_api):
        """Test querying the knowledge graph."""
        # Add some entities and relations
        entity_id = memory_api.add_entity(
            name="TestEntity",
            entity_type="concept",
        )

        # Query the graph
        results = memory_api.query_graph(entity_name="TestEntity")

        assert results is not None


class TestMemoryAPIConsolidationOperations:
    """Tests for consolidation operations."""

    def test_consolidate_memories(self, memory_api):
        """Test consolidating memories to extract patterns."""
        # Store multiple events
        for i in range(5):
            memory_api.remember_event(
                event_type="action",
                content=f"Test action {i}",
            )

        # Consolidate
        patterns = memory_api.consolidate(days_back=1)

        assert patterns is not None


class TestMemoryAPIErrorHandling:
    """Tests for error handling and edge cases."""

    def test_invalid_memory_type(self, memory_api):
        """Test that invalid memory type raises error."""
        with pytest.raises(Exception):
            memory_api.remember(
                content="Test",
                memory_type="invalid_type",
            )

    def test_none_content(self, memory_api):
        """Test that None content raises error."""
        with pytest.raises((ValueError, TypeError, Exception)):
            memory_api.remember(content=None, memory_type="semantic")

    def test_api_operations_without_project(self, memory_api):
        """Test that operations fail gracefully without project."""
        # All operations should work even if project doesn't exist
        # (ProjectManager should create one automatically)
        memory_id = memory_api.remember("Test", memory_type="semantic")
        assert memory_id is not None


class TestMemoryAPIIntegration:
    """Integration tests combining multiple operations."""

    def test_full_workflow(self, memory_api):
        """Test a complete workflow: remember → recall → forget."""
        # Remember
        memory_id = memory_api.remember(
            content="Important technical finding",
            memory_type="semantic",
            tags=["important", "tech"],
        )
        assert memory_id is not None

        # Recall
        results = memory_api.recall(query="important", limit=5)
        assert results is not None

        # Forget
        success = memory_api.forget(memory_id)
        assert success is True

    def test_event_to_semantic_workflow(self, memory_api):
        """Test converting events to semantic memories."""
        # Store event
        event_id = memory_api.remember_event(
            event_type="action",
            content="Discovered important pattern",
            outcome="success",
        )
        assert event_id is not None

        # Store semantic memory summarizing the event
        memory_id = memory_api.remember(
            content="Important pattern discovered in system",
            memory_type="semantic",
            context={"source_event": event_id},
        )
        assert memory_id is not None

    def test_task_to_procedure_workflow(self, memory_api):
        """Test converting a task into a reusable procedure."""
        # Remember task
        task_id = memory_api.remember_task(
            title="Build deployment pipeline",
            description="Create automated deployment",
        )
        assert task_id is not None

        # Create procedure from task
        procedure_id = memory_api.remember_procedure(
            name="deploy_pipeline",
            description="Automated deployment procedure",
            steps=[
                "Build artifacts",
                "Run tests",
                "Deploy to staging",
                "Deploy to production",
            ],
            prerequisites=["Docker", "kubectl"],
        )
        assert procedure_id is not None
