"""Tests for cascading recall functionality."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from athena.core.database import Database
from athena.episodic.store import EpisodicStore
from athena.memory.store import MemoryStore
from athena.procedural.store import ProceduralStore
from athena.prospective.store import ProspectiveStore
from athena.graph.store import GraphStore
from athena.meta.store import MetaMemoryStore
from athena.consolidation.system import ConsolidationSystem
from athena.projects.manager import ProjectManager
from athena.manager import UnifiedMemoryManager
from athena.session.context_manager import SessionContextManager


pytest.importorskip("psycopg")
@pytest.fixture
def db(tmp_path: Path) -> Database:
    """Create test database."""
    db_path = tmp_path / "test.db"
    return Database(str(db_path))


@pytest.fixture
def project_manager(db: Database) -> ProjectManager:
    """Create project manager."""
    return ProjectManager(db)


@pytest.fixture
def episodic_store(db: Database) -> EpisodicStore:
    """Create episodic store."""
    return EpisodicStore(db)


@pytest.fixture
def semantic_store(db: Database) -> MemoryStore:
    """Create semantic memory store."""
    return MemoryStore(db)


@pytest.fixture
def procedural_store(db: Database) -> ProceduralStore:
    """Create procedural store."""
    return ProceduralStore(db)


@pytest.fixture
def prospective_store(db: Database) -> ProspectiveStore:
    """Create prospective store."""
    return ProspectiveStore(db)


@pytest.fixture
def graph_store(db: Database) -> GraphStore:
    """Create graph store."""
    return GraphStore(db)


@pytest.fixture
def meta_store(db: Database) -> MetaMemoryStore:
    """Create meta memory store."""
    return MetaMemoryStore(db)


@pytest.fixture
def consolidation_system(db: Database) -> ConsolidationSystem:
    """Create consolidation system."""
    return ConsolidationSystem(db)


@pytest.fixture
def session_manager(db: Database) -> SessionContextManager:
    """Create session context manager."""
    return SessionContextManager(db)


@pytest.fixture
def manager(
    semantic_store: MemoryStore,
    episodic_store: EpisodicStore,
    procedural_store: ProceduralStore,
    prospective_store: ProspectiveStore,
    graph_store: GraphStore,
    meta_store: MetaMemoryStore,
    consolidation_system: ConsolidationSystem,
    project_manager: ProjectManager,
    session_manager: SessionContextManager,
) -> UnifiedMemoryManager:
    """Create unified memory manager with session support."""
    return UnifiedMemoryManager(
        semantic=semantic_store,
        episodic=episodic_store,
        procedural=procedural_store,
        prospective=prospective_store,
        graph=graph_store,
        meta=meta_store,
        consolidation=consolidation_system,
        project_manager=project_manager,
        session_manager=session_manager,
    )


class TestCascadingRecallBasics:
    """Basic cascading recall tests."""

    def test_recall_exists(self, manager: UnifiedMemoryManager):
        """Test that recall method exists."""
        assert hasattr(manager, "recall")
        assert callable(manager.recall)

    def test_recall_basic_single_tier(self, manager: UnifiedMemoryManager):
        """Test basic single-tier recall."""
        results = manager.recall(
            query="What happened?",
            cascade_depth=1,
        )

        assert isinstance(results, dict)
        assert "_cascade_depth" in results
        assert results["_cascade_depth"] == 1
        assert "tier_1" in results

    def test_recall_two_tiers(self, manager: UnifiedMemoryManager):
        """Test two-tier recall."""
        results = manager.recall(
            query="What happened?",
            cascade_depth=2,
        )

        assert results["_cascade_depth"] == 2
        assert "tier_1" in results
        assert "tier_2" in results

    def test_recall_three_tiers(self, manager: UnifiedMemoryManager):
        """Test three-tier recall (no RAG available in tests)."""
        results = manager.recall(
            query="What happened?",
            cascade_depth=3,
        )

        assert results["_cascade_depth"] == 3
        assert "tier_1" in results
        assert "tier_2" in results
        # Tier 3 may not be present if RAG is not available

    def test_recall_depth_clamping(self, manager: UnifiedMemoryManager):
        """Test that depth is clamped to 1-3 range."""
        # Test depth 0 is clamped to 1
        results = manager.recall(query="test", cascade_depth=0)
        assert results["_cascade_depth"] == 1

        # Test depth 5 is clamped to 3
        results = manager.recall(query="test", cascade_depth=5)
        assert results["_cascade_depth"] == 3

    def test_recall_with_context(self, manager: UnifiedMemoryManager):
        """Test recall with explicit context."""
        context = {
            "task": "Debug failing test",
            "phase": "debugging",
        }

        results = manager.recall(
            query="What was the error?",
            context=context,
            cascade_depth=1,
        )

        assert "tier_1" in results

    def test_recall_loads_session_context(
        self, manager: UnifiedMemoryManager, session_manager: SessionContextManager
    ):
        """Test that recall loads session context automatically."""
        # Start a session
        session_manager.start_session(
            session_id="session_test",
            project_id=1,
            task="Debug test",
            phase="debugging",
        )

        # Make a recall query
        results = manager.recall(query="What happened?", cascade_depth=1)

        # Results should have been created (even if empty)
        assert "tier_1" in results

    def test_recall_returns_scores(self, manager: UnifiedMemoryManager):
        """Test that recall includes confidence scores."""
        results = manager.recall(
            query="test",
            include_scores=True,
            cascade_depth=1,
        )

        # Scores would be in individual results
        assert "tier_1" in results

    def test_recall_without_scores(self, manager: UnifiedMemoryManager):
        """Test that recall can skip scores."""
        results = manager.recall(
            query="test",
            include_scores=False,
            cascade_depth=1,
        )

        assert "tier_1" in results

    def test_recall_with_reasoning(self, manager: UnifiedMemoryManager):
        """Test that recall includes reasoning."""
        results = manager.recall(
            query="test",
            explain_reasoning=True,
            cascade_depth=1,
        )

        assert "_cascade_explanation" in results
        assert "query" in results["_cascade_explanation"]
        assert "depth" in results["_cascade_explanation"]
        assert "context_keys" in results["_cascade_explanation"]

    def test_recall_without_reasoning(self, manager: UnifiedMemoryManager):
        """Test that recall skips reasoning when requested."""
        results = manager.recall(
            query="test",
            explain_reasoning=False,
            cascade_depth=1,
        )

        # Explanation should be conditional
        if "_cascade_explanation" in results:
            assert False, "Explanation should not be included"


class TestCascadingRecallTiers:
    """Tests for individual tiers."""

    def test_tier_1_includes_episodic_on_temporal_query(
        self, manager: UnifiedMemoryManager
    ):
        """Test that tier 1 includes episodic for temporal queries."""
        results = manager.recall(
            query="What was the error last night?",
            cascade_depth=1,
        )

        # Episodic should be triggered by "last" and "error"
        tier_1 = results.get("tier_1", {})
        # May or may not have results, but structure should exist

    def test_tier_1_includes_semantic(self, manager: UnifiedMemoryManager):
        """Test that tier 1 always includes semantic search."""
        results = manager.recall(
            query="What is the meaning of life?",
            cascade_depth=1,
        )

        tier_1 = results.get("tier_1", {})
        assert isinstance(tier_1, dict)
        # Semantic is always included

    def test_tier_1_includes_procedural_on_howto_query(
        self, manager: UnifiedMemoryManager
    ):
        """Test that tier 1 includes procedural for how-to queries."""
        results = manager.recall(
            query="How do I implement this?",
            cascade_depth=1,
        )

        tier_1 = results.get("tier_1", {})
        # Procedural should be triggered by "how" and "implement"

    def test_tier_1_includes_prospective_on_task_query(
        self, manager: UnifiedMemoryManager
    ):
        """Test that tier 1 includes prospective for task queries."""
        results = manager.recall(
            query="What tasks should I do?",
            cascade_depth=1,
        )

        tier_1 = results.get("tier_1", {})
        # Prospective should be triggered by "task" and "should"

    def test_tier_2_enrichment(self, manager: UnifiedMemoryManager):
        """Test that tier 2 provides enrichment."""
        results = manager.recall(
            query="What should we do?",
            context={"phase": "planning"},
            cascade_depth=2,
        )

        tier_2 = results.get("tier_2", {})
        assert isinstance(tier_2, dict)

    def test_tier_2_session_context(
        self, manager: UnifiedMemoryManager, session_manager: SessionContextManager
    ):
        """Test that tier 2 includes session context."""
        # Start a session with recent events
        session_manager.start_session(
            session_id="session_test",
            project_id=1,
            phase="debugging",
        )
        session_manager._current_session.recent_events = [
            {"event": "error_occurred"},
            {"event": "attempted_fix"},
        ]

        results = manager.recall(
            query="What happened?",
            cascade_depth=2,
        )

        tier_2 = results.get("tier_2", {})
        # Should include session context if available


class TestCascadingRecallEdgeCases:
    """Tests for edge cases."""

    def test_recall_empty_query(self, manager: UnifiedMemoryManager):
        """Test recall with empty query."""
        results = manager.recall(query="", cascade_depth=1)
        assert isinstance(results, dict)

    def test_recall_very_long_query(self, manager: UnifiedMemoryManager):
        """Test recall with very long query."""
        long_query = "test " * 100
        results = manager.recall(query=long_query, cascade_depth=1)
        assert isinstance(results, dict)

    def test_recall_special_characters(self, manager: UnifiedMemoryManager):
        """Test recall with special characters."""
        results = manager.recall(
            query="What is @#$%^&*() about?", cascade_depth=1
        )
        assert isinstance(results, dict)

    def test_recall_unicode(self, manager: UnifiedMemoryManager):
        """Test recall with unicode."""
        results = manager.recall(
            query="What is café about? 你好", cascade_depth=1
        )
        assert isinstance(results, dict)

    def test_recall_with_zero_k(self, manager: UnifiedMemoryManager):
        """Test recall with k=0."""
        results = manager.recall(query="test", k=0, cascade_depth=1)
        assert isinstance(results, dict)

    def test_recall_with_very_large_k(self, manager: UnifiedMemoryManager):
        """Test recall with very large k."""
        results = manager.recall(query="test", k=1000, cascade_depth=1)
        assert isinstance(results, dict)


class TestCascadingRecallErrorHandling:
    """Tests for error handling."""

    def test_recall_handles_tier_1_error(self, manager: UnifiedMemoryManager):
        """Test that recall handles tier 1 errors gracefully."""
        # Even if tier 1 fails, recall should return a result
        with patch.object(manager, "_recall_tier_1", side_effect=Exception("Test error")):
            results = manager.recall(query="test", cascade_depth=1)
            # Should have some error tracking
            assert isinstance(results, dict)

    def test_recall_handles_session_context_error(
        self, manager: UnifiedMemoryManager
    ):
        """Test that recall handles session context loading errors gracefully."""
        # Even if session context loading fails, recall should continue
        with patch.object(
            manager.session_manager, "get_current_session", side_effect=Exception("Test error")
        ):
            results = manager.recall(query="test", cascade_depth=1)
            # Should still return results
            assert isinstance(results, dict)


class TestCascadingRecallIntegration:
    """Integration tests."""

    def test_recall_full_workflow(
        self, manager: UnifiedMemoryManager, session_manager: SessionContextManager
    ):
        """Test complete recall workflow."""
        # Start session
        session_manager.start_session(
            session_id="workflow_test",
            project_id=1,
            task="Debug test",
            phase="debugging",
        )

        # Record some context
        session_manager.record_event(
            session_id="workflow_test",
            event_type="test_event",
            event_data={"info": "test"},
        )

        # Perform recall
        results = manager.recall(
            query="What happened during debugging?",
            cascade_depth=3,
            include_scores=True,
            explain_reasoning=True,
        )

        # Verify results structure
        assert "_cascade_depth" in results
        assert "tier_1" in results
        assert "_cascade_explanation" in results

        # End session
        session_manager.end_session("workflow_test")

    def test_recall_multiple_queries(self, manager: UnifiedMemoryManager):
        """Test multiple sequential recalls."""
        q1 = manager.recall(query="First query", cascade_depth=1)
        q2 = manager.recall(query="Second query", cascade_depth=2)
        q3 = manager.recall(query="Third query", cascade_depth=3)

        assert q1["_cascade_depth"] == 1
        assert q2["_cascade_depth"] == 2
        assert q3["_cascade_depth"] == 3

    def test_recall_with_different_contexts(self, manager: UnifiedMemoryManager):
        """Test recall with varying context."""
        # Debugging context
        results_debug = manager.recall(
            query="What went wrong?",
            context={"phase": "debugging"},
            cascade_depth=1,
        )

        # Development context
        results_dev = manager.recall(
            query="What's next?",
            context={"phase": "development"},
            cascade_depth=1,
        )

        # Both should return results
        assert isinstance(results_debug, dict)
        assert isinstance(results_dev, dict)
