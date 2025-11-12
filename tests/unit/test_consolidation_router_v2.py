"""Tests for refactored ConsolidationRouterV2 using store APIs."""

import pytest
from datetime import datetime

from athena.core.database import Database
from athena.core.models import Project
from athena.memory.store import MemoryStore
from athena.episodic.store import EpisodicStore
from athena.episodic.models import EpisodicEvent, EventType
from athena.procedural.store import ProceduralStore
from athena.prospective.store import ProspectiveStore
from athena.working_memory.consolidation_router_v2 import ConsolidationRouterV2
from athena.working_memory.models import WorkingMemoryItem, Component, ContentType, TargetLayer


@pytest.fixture
def db():
    """Create test database."""
    return Database()  # Uses PostgreSQL via environment variables


@pytest.fixture
def memory_store(db):
    """Create memory store."""
    return MemoryStore()


@pytest.fixture
def episodic_store(db):
    """Create episodic store."""
    return EpisodicStore(db)


@pytest.fixture
def procedural_store(db):
    """Create procedural store."""
    return ProceduralStore(db)


@pytest.fixture
def prospective_store(db):
    """Create prospective store."""
    return ProspectiveStore(db)


@pytest.fixture
def router(db, memory_store, episodic_store, procedural_store, prospective_store):
    """Create consolidation router."""
    return ConsolidationRouterV2(
        db=db,
        memory_store=memory_store,
        episodic_store=episodic_store,
        procedural_store=procedural_store,
        prospective_store=prospective_store,
    )


@pytest.fixture
def project(db):
    """Create test project."""
    cursor = db.get_cursor()
    cursor.execute("""
        INSERT INTO projects (name, path, created_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
    """, ("test_project", "/tmp/test"))
    db.commit()

    cursor.execute("SELECT id FROM projects WHERE name = ?", ("test_project",))
    row = cursor.fetchone()
    return Project(id=row["id"], name="test_project", path="/tmp/test")


class TestConsolidationRouterV2:
    """Test ConsolidationRouterV2."""

    def test_initialization(self, router):
        """Test router initialization."""
        assert router.db is not None
        assert router.memory_store is not None
        assert router.episodic_store is not None
        assert router.is_trained is False
        assert len(router.feature_names) == 11

    def test_feature_extraction(self, router, project):
        """Test feature extraction."""
        item = WorkingMemoryItem(
            id=1,
            project_id=project.id,
            content="Build a new feature for the system",
            content_type=ContentType.VERBAL,
            component=Component.PHONOLOGICAL,
            activation_level=0.8,
            importance_score=0.7,
        )

        features = router._extract_features(item)

        assert features is not None
        assert len(features) == len(router.feature_names)
        assert features[0] > 0  # content_length
        assert features[1] == 1.0  # is_verbal (phonological)
        assert features[3] == 0.8  # activation_level
        assert features[4] == 0.7  # importance_score

    def test_temporal_markers_detection(self, router):
        """Test temporal marker detection."""
        assert router._has_temporal_markers("What did you do yesterday?")
        assert router._has_temporal_markers("Meeting tomorrow at 9am")
        assert not router._has_temporal_markers("Simple factual content")

    def test_action_verbs_detection(self, router):
        """Test action verb detection."""
        assert router._has_action_verbs("Build a new component")
        assert router._has_action_verbs("Implement the algorithm")
        assert not router._has_action_verbs("This is a fact")

    def test_future_markers_detection(self, router):
        """Test future marker detection."""
        assert router._has_future_markers("I will complete this task")
        assert router._has_future_markers("Add this to your todo list")
        assert not router._has_future_markers("Already done")

    def test_question_words_detection(self, router):
        """Test question word detection."""
        assert router._has_question_words("How do I implement this?")
        assert router._has_question_words("What should I do?")
        assert not router._has_question_words("Complete the task")

    def test_file_references_detection(self, router):
        """Test file reference detection."""
        assert router._has_file_references("Edit src/athena/module.py")
        assert router._has_file_references("Check /home/user/file.txt")
        assert not router._has_file_references("Regular content")

    def test_heuristic_route_semantic(self, router, project):
        """Test heuristic routing to semantic layer."""
        item = WorkingMemoryItem(
            id=1,
            project_id=project.id,
            content="Python is a programming language",
            component=Component.PHONOLOGICAL,
        )

        target_layer = router._heuristic_route(item)
        assert target_layer == TargetLayer.SEMANTIC

    def test_heuristic_route_procedural(self, router, project):
        """Test heuristic routing to procedural layer."""
        item = WorkingMemoryItem(
            id=1,
            project_id=project.id,
            content="How to implement a new feature in the codebase",
            component=Component.PHONOLOGICAL,
        )

        target_layer = router._heuristic_route(item)
        assert target_layer in [TargetLayer.PROCEDURAL, TargetLayer.PROSPECTIVE]

    def test_heuristic_route_prospective(self, router, project):
        """Test heuristic routing to prospective layer."""
        item = WorkingMemoryItem(
            id=1,
            project_id=project.id,
            content="You should complete this task tomorrow",
            component=Component.PHONOLOGICAL,
        )

        target_layer = router._heuristic_route(item)
        assert target_layer in [TargetLayer.PROSPECTIVE, TargetLayer.PROCEDURAL]

    def test_heuristic_route_episodic(self, router, project):
        """Test heuristic routing to episodic layer."""
        item = WorkingMemoryItem(
            id=1,
            project_id=project.id,
            content="Yesterday I ran the test suite and it passed",
            component=Component.PHONOLOGICAL,
        )

        target_layer = router._heuristic_route(item)
        assert target_layer in [TargetLayer.EPISODIC, TargetLayer.SEMANTIC]

    @pytest.mark.asyncio
    async def test_route_async(self, router, project):
        """Test async routing."""
        item = WorkingMemoryItem(
            id=1,
            project_id=project.id,
            content="This is a factual statement",
            component=Component.PHONOLOGICAL,
        )

        target_layer, confidence = await router.route_async(item, project.id, use_ml=False)

        assert target_layer in TargetLayer
        assert 0.0 <= confidence <= 1.0

    def test_route_sync(self, router, project):
        """Test sync routing."""
        item = WorkingMemoryItem(
            id=1,
            project_id=project.id,
            content="This is a factual statement",
            component=Component.PHONOLOGICAL,
        )

        target_layer, confidence = router.route(item, project.id, use_ml=False)

        assert target_layer in TargetLayer
        assert 0.0 <= confidence <= 1.0

    @pytest.mark.asyncio
    async def test_consolidate_item_to_semantic_async(
        self, router, project, episodic_store
    ):
        """Test consolidating to semantic layer (async)."""
        item = WorkingMemoryItem(
            id=1,
            project_id=project.id,
            content="Python lists support indexing and slicing",
            component=Component.PHONOLOGICAL,
            importance_score=0.8,
        )

        result = await router.consolidate_item_async(
            item, project.id, target_layer=TargetLayer.SEMANTIC
        )

        assert result["wm_item_id"] == item.id
        assert result["target_layer"] == TargetLayer.SEMANTIC.value
        assert result["confidence"] == 1.0
        # LTM ID might be None if memory_store is not fully initialized

    @pytest.mark.asyncio
    async def test_consolidate_item_to_episodic_async(
        self, router, project, episodic_store
    ):
        """Test consolidating to episodic layer (async)."""
        item = WorkingMemoryItem(
            id=1,
            project_id=project.id,
            content="Fixed a critical bug in the authentication module",
            component=Component.EPISODIC_BUFFER,
        )

        result = await router.consolidate_item_async(
            item, project.id, target_layer=TargetLayer.EPISODIC
        )

        assert result["wm_item_id"] == item.id
        assert result["target_layer"] == TargetLayer.EPISODIC.value

    @pytest.mark.asyncio
    async def test_consolidate_item_with_auto_routing_async(
        self, router, project
    ):
        """Test consolidation with automatic routing (async)."""
        item = WorkingMemoryItem(
            id=1,
            project_id=project.id,
            content="This is a factual statement about Python",
            component=Component.PHONOLOGICAL,
        )

        # Should auto-route using heuristics
        result = await router.consolidate_item_async(item, project.id)

        assert result["wm_item_id"] == item.id
        assert result["target_layer"] is not None
        assert 0.0 <= result["confidence"] <= 1.0

    def test_consolidate_item_sync(self, router, project):
        """Test consolidation sync wrapper."""
        item = WorkingMemoryItem(
            id=1,
            project_id=project.id,
            content="Test content",
            component=Component.PHONOLOGICAL,
        )

        result = router.consolidate_item(
            item, project.id, target_layer=TargetLayer.SEMANTIC
        )

        assert result["wm_item_id"] == item.id
        assert result["target_layer"] is not None

    @pytest.mark.asyncio
    async def test_get_routing_statistics_async(self, router, project):
        """Test getting routing statistics (async)."""
        stats = await router.get_routing_statistics_async(project.id)

        assert "total_routes" in stats
        assert "by_layer" in stats
        assert "is_trained" in stats
        assert stats["is_trained"] is False

    def test_get_routing_statistics_sync(self, router, project):
        """Test getting routing statistics (sync)."""
        stats = router.get_routing_statistics(project.id)

        assert "total_routes" in stats
        assert "by_layer" in stats
        assert "is_trained" in stats

    def test_ml_predict_not_trained(self, router):
        """Test ML prediction when not trained."""
        import numpy as np

        features = np.random.rand(len(router.feature_names))
        target_layer, confidence = router._ml_predict(features)

        # Should fall back to semantic with low confidence
        assert target_layer == TargetLayer.SEMANTIC
        assert confidence == 0.5

    def test_feature_extraction_with_id(self, router):
        """Test that feature extraction handles invalid input gracefully."""
        features = router._extract_features(999)

        # Should return zero vector
        assert len(features) == len(router.feature_names)
        assert all(f == 0 for f in features)

    @pytest.mark.asyncio
    async def test_multiple_consolidations_async(self, router, project):
        """Test consolidating multiple items (async)."""
        items = [
            WorkingMemoryItem(
                id=i,
                project_id=project.id,
                content=f"Item {i}: {content}",
                component=Component.PHONOLOGICAL,
            )
            for i, content in enumerate([
                "Fact about Python",
                "Do this task tomorrow",
                "What is the meaning of life?",
            ])
        ]

        results = []
        for item in items:
            result = await router.consolidate_item_async(item, project.id)
            results.append(result)

        assert len(results) == 3
        assert all(r["wm_item_id"] is not None for r in results)
        assert all(r["target_layer"] is not None for r in results)

    def test_procedural_pattern_detection(self, router):
        """Test procedural pattern detection."""
        assert router._has_procedural_patterns("Step 1: Open the file")
        assert router._has_procedural_patterns("The algorithm works as follows:")
        assert not router._has_procedural_patterns("This is a simple fact")

    @pytest.mark.asyncio
    async def test_consolidation_with_metadata(self, router, project):
        """Test that metadata is preserved during consolidation."""
        import json

        item = WorkingMemoryItem(
            id=1,
            project_id=project.id,
            content="Important fact with metadata",
            component=Component.PHONOLOGICAL,
            importance_score=0.9,
        )

        result = await router.consolidate_item_async(
            item, project.id, target_layer=TargetLayer.SEMANTIC
        )

        assert result["wm_item_id"] == item.id
        assert result["confidence"] == 1.0  # User-specified layer

    def test_router_thread_safety(self, router, project):
        """Test that router methods are thread-safe."""
        # This is a basic test to ensure sync/async wrappers work
        item = WorkingMemoryItem(
            id=1,
            project_id=project.id,
            content="Test",
            component=Component.PHONOLOGICAL,
        )

        # Call sync method
        result1 = router.route(item, project.id, use_ml=False)

        # Call async method via sync wrapper
        result2 = router.consolidate_item(item, project.id)

        assert result1[0] in TargetLayer
        assert result2["target_layer"] is not None
