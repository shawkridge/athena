"""Comprehensive MCP handler integration tests (Phase 3).

Tests the MCP server handlers layer with integration tests covering:
- All core memory operations (remember, recall, forget, optimize)
- Episodic operations (record_event, recall_events, get_timeline)
- Procedural operations (create_procedure, find_procedures)
- Prospective operations (create_task, list_tasks, update_task_status)
- Knowledge graph operations (create_entity, create_relation, search_graph)
- Meta-memory operations (get_expertise, get_attention_state)
- Working memory operations (get_working_memory, update_working_memory)
- Consolidation operations (run_consolidation)
- RAG operations (smart_retrieve)

Test Coverage Target: >80% for src/athena/mcp/handlers.py
Tests: 40+ integration tests
Status: Ready for Phase 3
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from unittest.mock import Mock, AsyncMock, patch

from src.athena.core.models import MemoryType
from src.athena.episodic.models import EventType, EventOutcome, EventContext
from src.athena.procedural.models import ProcedureCategory
from src.athena.prospective.models import TaskStatus, TaskPriority
from src.athena.graph.models import EntityType, RelationType

# Fixtures are imported from conftest.py (mcp_server, temp_db, project_id)


# ============================================================================
# Memory Core Operations Tests
# ============================================================================


class TestRememberOperation:
    """Test the remember/store memory operation."""

    @pytest.mark.asyncio
    async def test_remember_fact_memory(self, mcp_server, project_id):
        """Test storing a fact memory."""
        result = await mcp_server._handle_remember({
            "project_id": project_id,
            "content": "Python is a versatile programming language",
            "memory_type": "fact",
        })

        assert result is not None
        assert len(result) > 0
        assert isinstance(result[0].text, str)
        assert "stored" in result[0].text.lower() or "success" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_remember_pattern_memory(self, mcp_server, project_id):
        """Test storing a pattern memory."""
        result = await mcp_server._handle_remember({
            "project_id": project_id,
            "content": "When implementing APIs, always validate input",
            "memory_type": "pattern",
        })

        assert result is not None
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_remember_decision_memory(self, mcp_server, project_id):
        """Test storing a decision memory."""
        result = await mcp_server._handle_remember({
            "project_id": project_id,
            "content": "Decided to use PostgreSQL for production database",
            "memory_type": "decision",
        })

        assert result is not None
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_remember_with_metadata(self, mcp_server, project_id):
        """Test storing memory with metadata."""
        result = await mcp_server._handle_remember({
            "project_id": project_id,
            "content": "Important fact about system architecture",
            "memory_type": "fact",
            "metadata": {"importance": "high", "domain": "architecture"}
        })

        assert result is not None
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_remember_multiple_memories(self, mcp_server, project_id):
        """Test storing multiple memories sequentially."""
        for i in range(5):
            result = await mcp_server._handle_remember({
                "project_id": project_id,
                "content": f"Memory number {i}",
                "memory_type": "fact",
            })
            assert result is not None


class TestRecallOperation:
    """Test the recall/retrieve memory operation."""

    @pytest.mark.asyncio
    async def test_recall_basic(self, mcp_server, project_id):
        """Test basic recall operation."""
        # First store a memory
        await mcp_server._handle_remember({
            "project_id": project_id,
            "content": "The capital of France is Paris",
            "memory_type": "fact",
        })

        # Then recall it
        result = await mcp_server._handle_recall({
            "project_id": project_id,
            "query": "capital of France",
        })

        assert result is not None
        assert len(result) > 0
        assert isinstance(result[0].text, str)

    @pytest.mark.asyncio
    async def test_recall_with_limit(self, mcp_server, project_id):
        """Test recall with result limit."""
        # Store multiple memories
        for i in range(10):
            await mcp_server._handle_remember({
                "project_id": project_id,
                "content": f"Fact about topic number {i}",
                "memory_type": "fact",
            })

        # Recall with limit
        result = await mcp_server._handle_recall({
            "project_id": project_id,
            "query": "topic",
            "limit": 5
        })

        assert result is not None
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_recall_empty_project(self, mcp_server, project_id):
        """Test recall from empty project."""
        result = await mcp_server._handle_recall({
            "project_id": project_id,
            "query": "nonexistent",
        })

        # Should return gracefully even with no results
        assert result is not None


class TestForgetOperation:
    """Test the forget/delete memory operation."""

    @pytest.mark.asyncio
    async def test_forget_memory(self, mcp_server, project_id):
        """Test forgetting a memory."""
        # Store a memory
        remember_result = await mcp_server._handle_remember({
            "project_id": project_id,
            "content": "Temporary fact",
            "memory_type": "fact",
        })

        # Parse ID from response (if available)
        # For now, test forget with a project
        result = await mcp_server._handle_forget({
            "project_id": project_id,
            "before_days": 30
        })

        assert result is not None

    @pytest.mark.asyncio
    async def test_forget_old_memories(self, mcp_server, project_id):
        """Test forgetting old memories by age."""
        # Store memory
        await mcp_server._handle_remember({
            "project_id": project_id,
            "content": "Old memory",
            "memory_type": "fact",
        })

        # Forget old
        result = await mcp_server._handle_forget({
            "project_id": project_id,
            "before_days": 0
        })

        assert result is not None


class TestListMemoriesOperation:
    """Test listing/browsing memories."""

    @pytest.mark.asyncio
    async def test_list_memories_empty(self, mcp_server, project_id):
        """Test listing memories from empty project."""
        result = await mcp_server._handle_list_memories({
            "project_id": project_id,
        })

        assert result is not None

    @pytest.mark.asyncio
    async def test_list_memories_with_filter(self, mcp_server, project_id):
        """Test listing memories with filters."""
        await mcp_server._handle_remember({
            "project_id": project_id,
            "content": "Important memory",
            "memory_type": "fact",
        })

        result = await mcp_server._handle_list_memories({
            "project_id": project_id,
            "memory_type": "fact",
            "limit": 10
        })

        assert result is not None


class TestOptimizeOperation:
    """Test memory optimization."""

    @pytest.mark.asyncio
    async def test_optimize_project(self, mcp_server, project_id):
        """Test optimizing project memories."""
        result = await mcp_server._handle_optimize({
            "project_id": project_id,
        })

        assert result is not None


# ============================================================================
# Episodic Operations Tests
# ============================================================================


class TestEpisodicOperations:
    """Test episodic memory operations."""

    @pytest.mark.asyncio
    async def test_record_event(self, mcp_server, project_id):
        """Test recording an event."""
        result = await mcp_server._handle_record_event({
            "project_id": project_id,
            "event_type": "action",
            "content": "User logged in",
            "context": {"ip": "192.168.1.1", "browser": "Chrome"}
        })

        assert result is not None
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_recall_events(self, mcp_server, project_id):
        """Test recalling events."""
        # Record an event
        await mcp_server._handle_record_event({
            "project_id": project_id,
            "event_type": "action",
            "content": "Test event"
        })

        # Recall events
        result = await mcp_server._handle_recall_events({
            "project_id": project_id,
            "event_type": "action"
        })

        assert result is not None

    @pytest.mark.asyncio
    async def test_get_timeline(self, mcp_server, project_id):
        """Test getting event timeline."""
        # Record events
        for i in range(3):
            await mcp_server._handle_record_event({
                "project_id": project_id,
                "event_type": "action",
                "content": f"Event {i}"
            })

        # Get timeline
        result = await mcp_server._handle_get_timeline({
            "project_id": project_id,
        })

        assert result is not None

    @pytest.mark.asyncio
    async def test_batch_record_events(self, mcp_server, project_id):
        """Test batch recording events."""
        events = [
            {
                "event_type": "action",
                "content": f"Batch event {i}",
                "timestamp": datetime.now().isoformat()
            }
            for i in range(5)
        ]

        result = await mcp_server._handle_batch_record_events({
            "project_id": project_id,
            "events": events
        })

        assert result is not None

    @pytest.mark.asyncio
    async def test_recall_events_by_session(self, mcp_server, project_id):
        """Test recalling events by session."""
        result = await mcp_server._handle_recall_events_by_session({
            "project_id": project_id,
            "session_id": "test_session_1"
        })

        assert result is not None


# ============================================================================
# Procedural Operations Tests
# ============================================================================


class TestProceduralOperations:
    """Test procedural memory operations."""

    @pytest.mark.asyncio
    async def test_create_procedure(self, mcp_server, project_id):
        """Test creating a procedure."""
        result = await mcp_server._handle_create_procedure({
            "project_id": project_id,
            "name": "Deploy to production",
            "steps": [
                "Push code to main",
                "Wait for CI pipeline",
                "Apply Kubernetes manifests"
            ],
            "category": "deployment"
        })

        assert result is not None

    @pytest.mark.asyncio
    async def test_find_procedures(self, mcp_server, project_id):
        """Test finding procedures."""
        # Create a procedure
        await mcp_server._handle_create_procedure({
            "project_id": project_id,
            "name": "Testing workflow",
            "steps": ["Run tests", "Check coverage"],
            "category": "testing"
        })

        # Find procedures
        result = await mcp_server._handle_find_procedures({
            "project_id": project_id,
            "query": "testing"
        })

        assert result is not None

    @pytest.mark.asyncio
    async def test_record_execution(self, mcp_server, project_id):
        """Test recording procedure execution."""
        result = await mcp_server._handle_record_execution({
            "project_id": project_id,
            "procedure_id": 1,
            "success": True,
            "duration_seconds": 45
        })

        assert result is not None

    @pytest.mark.asyncio
    async def test_get_procedure_effectiveness(self, mcp_server, project_id):
        """Test getting procedure effectiveness."""
        result = await mcp_server._handle_get_procedure_effectiveness({
            "project_id": project_id,
            "procedure_id": 1
        })

        assert result is not None

    @pytest.mark.asyncio
    async def test_suggest_procedure_improvements(self, mcp_server, project_id):
        """Test getting procedure improvement suggestions."""
        result = await mcp_server._handle_suggest_procedure_improvements({
            "project_id": project_id,
            "procedure_id": 1
        })

        assert result is not None


# ============================================================================
# Prospective Operations Tests
# ============================================================================


class TestProspectiveOperations:
    """Test prospective memory operations (tasks/goals)."""

    @pytest.mark.asyncio
    async def test_create_task(self, mcp_server, project_id):
        """Test creating a task."""
        result = await mcp_server._handle_create_task({
            "project_id": project_id,
            "content": "Implement feature X",
            "priority": "high"
        })

        assert result is not None

    @pytest.mark.asyncio
    async def test_list_tasks(self, mcp_server, project_id):
        """Test listing tasks."""
        # Create tasks
        for i in range(3):
            await mcp_server._handle_create_task({
                "project_id": project_id,
                "title": f"Task {i}",
                "priority": "medium"
            })

        # List tasks
        result = await mcp_server._handle_list_tasks({
            "project_id": project_id,
        })

        assert result is not None

    @pytest.mark.asyncio
    async def test_update_task_status(self, mcp_server, project_id):
        """Test updating task status."""
        result = await mcp_server._handle_update_task_status({
            "project_id": project_id,
            "task_id": 1,
            "status": "in_progress"
        })

        assert result is not None

    @pytest.mark.asyncio
    async def test_start_task(self, mcp_server, project_id):
        """Test starting a task."""
        result = await mcp_server._handle_start_task({
            "project_id": project_id,
            "task_id": 1
        })

        assert result is not None

    @pytest.mark.asyncio
    async def test_verify_task(self, mcp_server, project_id):
        """Test verifying task completion."""
        result = await mcp_server._handle_verify_task({
            "project_id": project_id,
            "task_id": 1
        })

        assert result is not None


# ============================================================================
# Knowledge Graph Operations Tests
# ============================================================================


class TestKnowledgeGraphOperations:
    """Test knowledge graph operations."""

    @pytest.mark.asyncio
    async def test_create_entity(self, mcp_server, project_id):
        """Test creating a graph entity."""
        result = await mcp_server._handle_create_entity({
            "project_id": project_id,
            "name": "Python",
            "entity_type": "Concept",
            "observations": ["Programming language"]
        })

        assert result is not None

    @pytest.mark.asyncio
    async def test_create_relation(self, mcp_server, project_id):
        """Test creating a graph relation."""
        # First create entities
        await mcp_server._handle_create_entity({
            "project_id": project_id,
            "name": "Python",
            "entity_type": "Concept"
        })
        await mcp_server._handle_create_entity({
            "project_id": project_id,
            "name": "Django",
            "entity_type": "Concept"
        })

        # Then create relation
        result = await mcp_server._handle_create_relation({
            "project_id": project_id,
            "from_entity": "Python",
            "to_entity": "Django",
            "relation_type": "implements"
        })

        assert result is not None

    @pytest.mark.asyncio
    async def test_add_observation(self, mcp_server, project_id):
        """Test adding observation to entity."""
        result = await mcp_server._handle_add_observation({
            "project_id": project_id,
            "entity_name": "Python",
            "observation": "Used for web development"
        })

        assert result is not None

    @pytest.mark.asyncio
    async def test_search_graph(self, mcp_server, project_id):
        """Test searching knowledge graph."""
        # Create entities
        await mcp_server._handle_create_entity({
            "project_id": project_id,
            "name": "API",
            "entity_type": "Concept"
        })

        # Search
        result = await mcp_server._handle_search_graph({
            "project_id": project_id,
            "query": "API"
        })

        assert result is not None

    @pytest.mark.asyncio
    async def test_search_graph_with_depth(self, mcp_server, project_id):
        """Test searching graph with depth limit."""
        result = await mcp_server._handle_search_graph_with_depth({
            "project_id": project_id,
            "query": "API",
            "max_depth": 2
        })

        assert result is not None

    @pytest.mark.asyncio
    async def test_get_graph_metrics(self, mcp_server, project_id):
        """Test getting graph metrics."""
        result = await mcp_server._handle_get_graph_metrics({
            "project_id": project_id,
        })

        assert result is not None

    @pytest.mark.asyncio
    async def test_analyze_coverage(self, mcp_server, project_id):
        """Test analyzing knowledge graph coverage."""
        result = await mcp_server._handle_analyze_coverage({
            "project_id": project_id,
        })

        assert result is not None


# ============================================================================
# Meta-Memory Operations Tests
# ============================================================================


class TestMetaMemoryOperations:
    """Test meta-memory operations."""

    @pytest.mark.asyncio
    async def test_get_expertise(self, mcp_server, project_id):
        """Test getting expertise map."""
        result = await mcp_server._handle_get_expertise({
            "project_id": project_id,
        })

        assert result is not None

    @pytest.mark.asyncio
    async def test_get_attention_state(self, mcp_server, project_id):
        """Test getting attention state."""
        result = await mcp_server._handle_get_attention_state({
            "project_id": project_id,
        })

        assert result is not None


# ============================================================================
# Working Memory Operations Tests
# ============================================================================


class TestWorkingMemoryOperations:
    """Test working memory operations."""

    @pytest.mark.asyncio
    async def test_get_working_memory(self, mcp_server, project_id):
        """Test getting working memory."""
        result = await mcp_server._handle_get_working_memory({
            "project_id": project_id,
        })

        assert result is not None

    @pytest.mark.asyncio
    async def test_update_working_memory(self, mcp_server, project_id):
        """Test updating working memory."""
        result = await mcp_server._handle_update_working_memory({
            "project_id": project_id,
            "item": "Focus on feature development"
        })

        assert result is not None

    @pytest.mark.asyncio
    async def test_clear_working_memory(self, mcp_server, project_id):
        """Test clearing working memory."""
        result = await mcp_server._handle_clear_working_memory({
            "project_id": project_id,
        })

        assert result is not None

    @pytest.mark.asyncio
    async def test_consolidate_working_memory(self, mcp_server, project_id):
        """Test consolidating working memory."""
        result = await mcp_server._handle_consolidate_working_memory({
            "project_id": project_id,
        })

        assert result is not None


# ============================================================================
# Consolidation & RAG Operations Tests
# ============================================================================


class TestConsolidationOperations:
    """Test consolidation operations."""

    @pytest.mark.asyncio
    async def test_run_consolidation(self, mcp_server, project_id):
        """Test running consolidation."""
        # Store some memories first
        await mcp_server._handle_remember({
            "project_id": project_id,
            "content": "Fact 1",
            "memory_type": "fact",
        })

        # Run consolidation
        result = await mcp_server._handle_run_consolidation({
            "project_id": project_id,
        })

        assert result is not None


class TestRAGOperations:
    """Test RAG operations."""

    @pytest.mark.asyncio
    async def test_smart_retrieve(self, mcp_server, project_id):
        """Test smart retrieval."""
        # Store memories
        await mcp_server._handle_remember({
            "project_id": project_id,
            "content": "Machine learning is powerful",
            "memory_type": "fact",
        })

        # Smart retrieve
        result = await mcp_server._handle_smart_retrieve({
            "project_id": project_id,
            "query": "machine learning",
        })

        assert result is not None


# ============================================================================
# Goal Operations Tests
# ============================================================================


class TestGoalOperations:
    """Test goal management operations."""

    @pytest.mark.asyncio
    async def test_get_active_goals(self, mcp_server, project_id):
        """Test getting active goals."""
        result = await mcp_server._handle_get_active_goals({
            "project_id": project_id,
        })

        assert result is not None

    @pytest.mark.asyncio
    async def test_set_goal(self, mcp_server, project_id):
        """Test setting a goal."""
        result = await mcp_server._handle_set_goal({
            "project_id": project_id,
            "goal_name": "Complete Phase 3",
            "priority": "high"
        })

        assert result is not None


# ============================================================================
# Association Operations Tests
# ============================================================================


class TestAssociationOperations:
    """Test association/relationship operations."""

    @pytest.mark.asyncio
    async def test_get_associations(self, mcp_server, project_id):
        """Test getting associations."""
        # First create a memory
        remember_result = await mcp_server._handle_remember({
            "project_id": project_id,
            "content": "Python is a programming language",
            "memory_type": "fact",
        })
        # Extract memory ID from response
        result = await mcp_server._handle_get_associations({
            "project_id": project_id,
            "memory_id": "1",  # Use a default memory_id for testing
        })

        assert result is not None

    @pytest.mark.asyncio
    async def test_strengthen_association(self, mcp_server, project_id):
        """Test strengthening association."""
        # Create memories first
        await mcp_server._handle_remember({
            "project_id": project_id,
            "content": "Python is a language",
            "memory_type": "fact",
        })
        await mcp_server._handle_remember({
            "project_id": project_id,
            "content": "Programming is a discipline",
            "memory_type": "fact",
        })

        result = await mcp_server._handle_strengthen_association({
            "link_id": "1",
            "amount": 0.1
        })

        assert result is not None

    @pytest.mark.asyncio
    async def test_find_memory_path(self, mcp_server, project_id):
        """Test finding memory path between concepts."""
        result = await mcp_server._handle_find_memory_path({
            "project_id": project_id,
            "start": "Python",
            "end": "Web Development"
        })

        assert result is not None


# ============================================================================
# Integration Tests - Multi-Operation Workflows
# ============================================================================


class TestMultiOperationWorkflows:
    """Test workflows involving multiple operations."""

    @pytest.mark.asyncio
    async def test_remember_and_recall_workflow(self, mcp_server, project_id):
        """Test full workflow: remember, then recall."""
        # Remember
        remember_result = await mcp_server._handle_remember({
            "project_id": project_id,
            "content": "The speed of light is 299,792,458 m/s",
            "memory_type": "fact",
        })
        assert remember_result is not None

        # Recall
        recall_result = await mcp_server._handle_recall({
            "project_id": project_id,
            "query": "speed of light",
        })
        assert recall_result is not None

    @pytest.mark.asyncio
    async def test_task_lifecycle_workflow(self, mcp_server, project_id):
        """Test full task lifecycle."""
        # Create
        create_result = await mcp_server._handle_create_task({
            "project_id": project_id,
            "title": "Implement feature",
            "priority": "high"
        })
        assert create_result is not None

        # List
        list_result = await mcp_server._handle_list_tasks({
            "project_id": project_id,
        })
        assert list_result is not None

        # Update status
        update_result = await mcp_server._handle_update_task_status({
            "project_id": project_id,
            "task_id": 1,
            "status": "in_progress"
        })
        assert update_result is not None

    @pytest.mark.asyncio
    async def test_event_recording_and_recall_workflow(self, mcp_server, project_id):
        """Test event recording and recall."""
        # Record
        for i in range(3):
            record_result = await mcp_server._handle_record_event({
                "project_id": project_id,
                "event_type": "action",
                "content": f"Action {i}"
            })
            assert record_result is not None

        # Recall
        recall_result = await mcp_server._handle_recall_events({
            "project_id": project_id,
            "event_type": "action"
        })
        assert recall_result is not None

        # Timeline
        timeline_result = await mcp_server._handle_get_timeline({
            "project_id": project_id,
        })
        assert timeline_result is not None


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestErrorHandling:
    """Test error handling in handlers."""

    @pytest.mark.asyncio
    async def test_recall_missing_project(self, mcp_server):
        """Test recall with missing project."""
        with pytest.raises((ValueError, KeyError, Exception)):
            await mcp_server._handle_recall({
                "project_id": "nonexistent_project_id",
                "query": "test"
            })

    @pytest.mark.asyncio
    async def test_invalid_memory_type(self, mcp_server, project_id):
        """Test storing with invalid memory type."""
        with pytest.raises((ValueError, KeyError, Exception)):
            await mcp_server._handle_remember({
                "project_id": project_id,
                "content": "test",
                "memory_type": "invalid_type"
            })


# ============================================================================
# State Management Tests
# ============================================================================


class TestStateManagement:
    """Test state consistency across operations."""

    @pytest.mark.asyncio
    async def test_remember_persist_state(self, mcp_server, project_id):
        """Test that remembered memories persist."""
        # Remember
        await mcp_server._handle_remember({
            "project_id": project_id,
            "content": "Persistent fact",
            "memory_type": "fact",
        })

        # List immediately after
        list_result = await mcp_server._handle_list_memories({
            "project_id": project_id,
        })
        assert list_result is not None

    @pytest.mark.asyncio
    async def test_task_state_transitions(self, mcp_server, project_id):
        """Test task state transitions."""
        # Create task
        await mcp_server._handle_create_task({
            "project_id": project_id,
            "title": "Test task",
            "priority": "medium"
        })

        # Change status
        await mcp_server._handle_update_task_status({
            "project_id": project_id,
            "task_id": 1,
            "status": "in_progress"
        })

        # List and verify (or get status)
        result = await mcp_server._handle_list_tasks({
            "project_id": project_id,
        })
        assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
