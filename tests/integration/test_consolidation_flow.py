"""Integration tests for episodic→semantic consolidation pipeline.

This test suite validates the core consolidation system that transforms
episodic events into generalized semantic patterns - the signature feature
that distinguishes this system from all production memory systems.

Based on: Larimar (ICML 2024), Complementary Learning Systems Theory
"""

import pytest
from datetime import datetime, timedelta
from typing import List

from athena.consolidation.pipeline import (
    consolidate_episodic_to_semantic,
    ConsolidationReport,
)
from athena.consolidation.clustering import cluster_events_by_context
from athena.consolidation.pattern_extraction import extract_patterns
from athena.core.database import Database
from athena.episodic.models import EpisodicEvent, EventType, EventContext
from athena.episodic.store import EpisodicStore
from athena.memory.store import MemoryStore
from athena.projects.manager import ProjectManager


@pytest.fixture
def test_db():
    """Create in-memory test database."""
    db = Database(":memory:")
    yield db
    db.close()


@pytest.fixture
def project_manager(test_db):
    """Initialize project manager with test database."""
    return ProjectManager(test_db)


@pytest.fixture
def episodic_store(test_db):
    """Initialize episodic store for testing."""
    return EpisodicStore(test_db)


@pytest.fixture
def semantic_store():
    """Initialize semantic store for testing."""
    return MemoryStore(":memory:")


@pytest.fixture
def test_project(project_manager):
    """Create test project."""
    return project_manager.get_or_create_project(name="test-project")


class TestConsolidationBasics:
    """Test basic consolidation functionality."""

    def test_consolidation_extracts_patterns_from_authentication_workflow(
        self,
        episodic_store,
        semantic_store,
        test_project
    ):
        """
        CRITICAL TEST: Consolidation must extract patterns from episodic events.

        Given: A sequence of events representing authentication work
        When: Consolidation runs
        Then: A semantic pattern about "authentication workflow" is created
        """
        session_id = "test_session_001"
        base_time = datetime.now() - timedelta(hours=3)

        # Create realistic sequence of authentication-related events
        events = [
            EpisodicEvent(
                project_id=test_project.id,
                session_id=session_id,
                event_type=EventType.FILE_CHANGE,
                content="Modified authentication middleware to add JWT validation",
                context=EventContext(
                    cwd="/home/user/projects/test-project/src/auth",
                    files=["middleware/auth.py"],
                    task="Implement JWT authentication",
                    phase="authentication-refactor"
                ),
                timestamp=base_time,
                outcome="success"
            ),
            EpisodicEvent(
                project_id=test_project.id,
                session_id=session_id,
                event_type=EventType.ACTION,
                content="Added JWT token validation with 24h expiry",
                context=EventContext(
                    cwd="/home/user/projects/test-project/src/auth",
                    files=["utils/jwt_handler.py"],
                    task="Implement JWT authentication",
                    phase="authentication-refactor"
                ),
                timestamp=base_time + timedelta(minutes=15),
                outcome="success"
            ),
            EpisodicEvent(
                project_id=test_project.id,
                session_id=session_id,
                event_type=EventType.TEST_RUN,
                content="All authentication tests passing (12/12)",
                context=EventContext(
                    cwd="/home/user/projects/test-project/tests",
                    files=["test_auth.py"],
                    task="Implement JWT authentication",
                    phase="authentication-refactor"
                ),
                timestamp=base_time + timedelta(minutes=30),
                outcome="success",
                files_changed=2,
                lines_added=45,
                lines_deleted=12
            ),
            EpisodicEvent(
                project_id=test_project.id,
                session_id=session_id,
                event_type=EventType.DECISION,
                content="Chose JWT over session cookies for better scalability",
                context=EventContext(
                    cwd="/home/user/projects/test-project",
                    task="Implement JWT authentication",
                    phase="authentication-refactor"
                ),
                timestamp=base_time + timedelta(minutes=45),
                outcome="success"
            )
        ]

        # Store events and capture IDs
        event_ids = []
        for event in events:
            event_id = episodic_store.record_event(event)
            event_ids.append(event_id)

        # Get baseline: No semantic patterns yet
        semantic_memories_before = semantic_store.list_memories(test_project.id, limit=1000)
        assert len(semantic_memories_before) == 0, "Should start with no semantic memories"

        # ACT: Run consolidation
        report = consolidate_episodic_to_semantic(
            project_id=test_project.id,
            episodic_store=episodic_store,
            semantic_store=semantic_store,
            time_window_hours=24
        )

        # ASSERT: Pattern extracted
        assert isinstance(report, ConsolidationReport)
        assert report.patterns_extracted >= 1, (
            f"Should extract at least 1 pattern from authentication workflow, "
            f"but got {report.patterns_extracted}"
        )
        assert report.events_consolidated == 4, "Should consolidate all 4 events"
        assert report.quality_improvement is not None

        # ASSERT: Semantic memory created
        semantic_memories_after = semantic_store.list_memories(test_project.id, limit=1000)
        assert len(semantic_memories_after) >= 1, "Should create semantic memories"

        # ASSERT: Content is about authentication
        auth_related = [
            m for m in semantic_memories_after
            if any(keyword in m.content.lower() for keyword in ['auth', 'jwt', 'token'])
        ]
        assert len(auth_related) >= 1, (
            f"Should have authentication-related memory, got: "
            f"{[m.content for m in semantic_memories_after]}"
        )

        # ASSERT: Events marked as consolidated
        for event_id in event_ids:
            refreshed = episodic_store.get_event(event_id)
            assert refreshed.consolidation_status == 'consolidated', (
                f"Event {event_id} should be marked as consolidated"
            )

    def test_consolidation_handles_empty_events(
        self,
        episodic_store,
        semantic_store,
        test_project
    ):
        """Consolidation should handle projects with no events gracefully."""
        report = consolidate_episodic_to_semantic(
            project_id=test_project.id,
            episodic_store=episodic_store,
            semantic_store=semantic_store,
            time_window_hours=24
        )

        assert report.patterns_extracted == 0
        assert report.events_consolidated == 0
        assert report.quality_improvement == 0.0


class TestEventClustering:
    """Test event clustering by session and spatial context."""

    def test_clusters_events_by_session_id(
        self,
        episodic_store,
        test_project
    ):
        """Events in same session should cluster together."""
        session_1 = "session_001"
        session_2 = "session_002"

        events_s1 = [
            create_test_event(test_project.id, session_1, "Event 1A"),
            create_test_event(test_project.id, session_1, "Event 1B"),
        ]
        events_s2 = [
            create_test_event(test_project.id, session_2, "Event 2A"),
        ]

        all_events = events_s1 + events_s2
        for event in all_events:
            episodic_store.record_event(event)

        # Cluster
        clusters = cluster_events_by_context(all_events)

        assert len(clusters) == 2, "Should create 2 clusters for 2 sessions"
        assert len(clusters[0]) == 2, "First cluster should have 2 events"
        assert len(clusters[1]) == 1, "Second cluster should have 1 event"

    def test_clusters_events_by_spatial_proximity(
        self,
        episodic_store,
        test_project
    ):
        """Events in same directory should cluster together."""
        session_id = "session_001"

        events = [
            create_test_event(
                test_project.id,
                session_id,
                "Auth work",
                cwd="/project/src/auth"
            ),
            create_test_event(
                test_project.id,
                session_id,
                "More auth work",
                cwd="/project/src/auth"
            ),
            create_test_event(
                test_project.id,
                session_id,
                "Database work",
                cwd="/project/src/database"
            ),
        ]

        for event in events:
            episodic_store.record_event(event)

        # Use max_time_gap_minutes=0 and higher spatial threshold
        # to prevent temporal merging and ensure spatial separation
        clusters = cluster_events_by_context(
            events,
            max_time_gap_minutes=0,
            spatial_similarity_threshold=0.8  # Higher threshold to separate /auth from /database
        )

        # Should create clusters based on spatial proximity
        # Events 1 and 2 in /auth should cluster, event 3 separate
        assert len(clusters) >= 2, "Should separate spatially distant events"


class TestPatternExtraction:
    """Test LLM-based pattern extraction from event clusters."""

    @pytest.mark.integration
    @pytest.mark.llm
    def test_extracts_workflow_pattern_from_tdd_sequence(self):
        """
        Test pattern extraction using LLM.

        Given: A sequence showing test-driven development
        When: Pattern extraction runs
        Then: Identifies "TDD workflow" pattern
        """
        events = [
            create_test_event(1, "sess1", "Wrote failing test for feature X"),
            create_test_event(1, "sess1", "Implemented feature X"),
            create_test_event(1, "sess1", "All tests passing"),
        ]

        patterns = extract_patterns(
            event_cluster=events,
            use_llm=True  # Use actual Claude API
        )

        assert len(patterns) >= 1, "Should extract at least 1 pattern"

        # Check pattern quality
        pattern = patterns[0]
        assert pattern.type in ['pattern', 'workflow', 'decision']
        assert pattern.confidence > 0.5
        assert len(pattern.description) > 20  # Substantive description
        assert 'test' in pattern.description.lower() or 'tdd' in pattern.description.lower()


class TestConsolidationQuality:
    """Test consolidation quality metrics."""

    def test_quality_improvement_calculation(
        self,
        episodic_store,
        semantic_store,
        test_project
    ):
        """Consolidation should measure quality improvement."""
        # Create events
        events = create_authentication_workflow_events(test_project.id)
        for event in events:
            episodic_store.record_event(event)

        report = consolidate_episodic_to_semantic(
            project_id=test_project.id,
            episodic_store=episodic_store,
            semantic_store=semantic_store,
            time_window_hours=24
        )

        # Quality improvement should be positive when patterns extracted
        if report.patterns_extracted > 0:
            assert report.quality_improvement > 0, (
                "Quality should improve when patterns are extracted"
            )


# Helper functions

def create_test_event(
    project_id: int,
    session_id: str,
    content: str,
    cwd: str = "/project/src",
    event_type: EventType = EventType.ACTION
) -> EpisodicEvent:
    """Create a test episodic event."""
    return EpisodicEvent(
        project_id=project_id,
        session_id=session_id,
        event_type=event_type,
        content=content,
        context=EventContext(cwd=cwd),
        timestamp=datetime.now(),
        outcome="success"
    )


def create_authentication_workflow_events(project_id: int) -> List[EpisodicEvent]:
    """Create realistic authentication workflow events for testing."""
    session_id = "auth_work_session"
    base_time = datetime.now() - timedelta(hours=2)

    return [
        EpisodicEvent(
            project_id=project_id,
            session_id=session_id,
            event_type=EventType.FILE_CHANGE,
            content="Modified authentication middleware",
            context=EventContext(cwd="/project/src/auth"),
            timestamp=base_time,
            outcome="success"
        ),
        EpisodicEvent(
            project_id=project_id,
            session_id=session_id,
            event_type=EventType.ACTION,
            content="Added JWT token validation",
            context=EventContext(cwd="/project/src/auth"),
            timestamp=base_time + timedelta(minutes=10),
            outcome="success"
        ),
        EpisodicEvent(
            project_id=project_id,
            session_id=session_id,
            event_type=EventType.TEST_RUN,
            content="All auth tests passing",
            context=EventContext(cwd="/project/tests"),
            timestamp=base_time + timedelta(minutes=20),
            outcome="success"
        ),
    ]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
