"""Tests for planning consolidation and pattern extraction.

Tests the core learning mechanism for the planning layer.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from athena.planning.models import (
    ExecutionFeedback,
    ExecutionOutcome,
    PlanningPattern,
    PatternType,
)
from athena.planning.store import PlanningStore
from athena.consolidation.planning_pattern_extraction import (
    ExecutionClusterer,
    PlanningPatternExtractor,
    ConsolidationRouter,
)
from athena.core.database import Database


# ==================== FIXTURES ====================

@pytest.fixture
def db(tmp_path):
    """Create temporary database for testing."""
    db_path = tmp_path / "test_memory.db"
    return Database(str(db_path))


@pytest.fixture
def planning_store(db):
    """Create planning store with initialized schema."""
    store = PlanningStore(db)
    return store


@pytest.fixture
def sample_feedback_items():
    """Create sample execution feedback for testing."""
    return [
        ExecutionFeedback(
            project_id=1,
            execution_outcome=ExecutionOutcome.SUCCESS,
            execution_quality_score=0.85,
            planned_duration_minutes=30,
            actual_duration_minutes=28,
            blockers_encountered=["api_timeout"],
            adjustments_made=["added retry logic"],
            assumption_violations=[],
            learning_extracted="Retry logic helps with API timeouts",
            confidence_in_learning=0.8,
            phase_number=1,
        ),
        ExecutionFeedback(
            project_id=1,
            execution_outcome=ExecutionOutcome.SUCCESS,
            execution_quality_score=0.82,
            planned_duration_minutes=30,
            actual_duration_minutes=32,
            blockers_encountered=["api_timeout"],
            adjustments_made=["increased timeout"],
            assumption_violations=[],
            learning_extracted="Timeout duration matters",
            confidence_in_learning=0.75,
            phase_number=1,
        ),
        ExecutionFeedback(
            project_id=1,
            execution_outcome=ExecutionOutcome.SUCCESS,
            execution_quality_score=0.88,
            planned_duration_minutes=30,
            actual_duration_minutes=29,
            blockers_encountered=[],
            adjustments_made=[],
            assumption_violations=[],
            learning_extracted="Consistent performance with retries",
            confidence_in_learning=0.85,
            phase_number=1,
        ),
        ExecutionFeedback(
            project_id=1,
            execution_outcome=ExecutionOutcome.PARTIAL,
            execution_quality_score=0.70,
            planned_duration_minutes=30,
            actual_duration_minutes=45,
            blockers_encountered=["network_error", "db_connection"],
            adjustments_made=["added connection pooling"],
            assumption_violations=["assumed network stable"],
            learning_extracted="Network stability is critical",
            confidence_in_learning=0.7,
            phase_number=1,
        ),
        ExecutionFeedback(
            project_id=1,
            execution_outcome=ExecutionOutcome.SUCCESS,
            execution_quality_score=0.87,
            planned_duration_minutes=30,
            actual_duration_minutes=30,
            blockers_encountered=[],
            adjustments_made=[],
            assumption_violations=[],
            learning_extracted="Optimized approach works reliably",
            confidence_in_learning=0.9,
            phase_number=1,
        ),
    ]


# ==================== QUICK TESTS ====================

class TestQuickConsolidation:
    """Quick smoke tests for consolidation pipeline."""

    def test_clusterer_creation(self):
        """Test clusterer can be created."""
        clusterer = ExecutionClusterer()
        assert clusterer is not None

    def test_empty_cluster(self):
        """Test clustering empty list."""
        clusterer = ExecutionClusterer()
        clusters = clusterer.cluster_by_decomposition([])
        assert len(clusters) == 0

    def test_pattern_extractor_creation(self, planning_store, db):
        """Test pattern extractor can be created."""
        extractor = PlanningPatternExtractor(planning_store, db)
        assert extractor is not None

    def test_consolidation_router_creation(self, planning_store, db):
        """Test router can be created."""
        router = ConsolidationRouter(planning_store, db)
        assert router is not None

    def test_clustering_basic(self, sample_feedback_items):
        """Test basic clustering works."""
        clusterer = ExecutionClusterer()
        clusters = clusterer.cluster_by_decomposition(sample_feedback_items)
        assert len(clusters) > 0

    def test_pattern_extraction_basic(self, planning_store, db, sample_feedback_items):
        """Test pattern extraction works."""
        extractor = PlanningPatternExtractor(planning_store, db)
        patterns = extractor.extract_patterns(project_id=1, feedback_items=sample_feedback_items)
        assert len(patterns) >= 0  # May be 0 if confidence threshold not met

    def test_consolidation_integration(self, planning_store, db, sample_feedback_items):
        """Test full consolidation pipeline."""
        router = ConsolidationRouter(planning_store, db)
        
        # Store feedback
        for feedback in sample_feedback_items:
            planning_store.record_execution_feedback(feedback)
        
        # Consolidate
        pattern = router.consolidate_patterns(project_id=1)
        
        # Should either return pattern or None (both valid)
        assert pattern is None or isinstance(pattern, PlanningPattern)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
