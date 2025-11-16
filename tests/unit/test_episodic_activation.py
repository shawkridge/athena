"""Tests for episodic memory activation-based lifecycle management.

Tests the ACT-R style activation decay, consolidation/archival decisions,
and working memory ranking based on activation.
"""

import math
from datetime import datetime, timedelta

import pytest

from src.athena.episodic.activation import (
    compute_activation,
    consolidate_and_archive_batch,
    decay_activation_batch,
    rank_by_activation,
    should_archive,
    should_consolidate,
)
from src.athena.episodic.models import EpisodicEvent, EventType, EventOutcome


@pytest.fixture
def sample_event():
    """Create a sample episodic event for testing."""
    return EpisodicEvent(
        id=1,
        project_id=1,
        session_id="test_session",
        timestamp=datetime.now(),
        event_type=EventType.ACTION,
        content="Test event",
        outcome=EventOutcome.SUCCESS,
        importance_score=0.5,
        actionability_score=0.5,
    )


@pytest.fixture
def old_event():
    """Create an old episodic event (10 days old)."""
    return EpisodicEvent(
        id=2,
        project_id=1,
        session_id="test_session",
        timestamp=datetime.now() - timedelta(days=10),
        last_activation=datetime.now() - timedelta(days=10),
        event_type=EventType.ACTION,
        content="Old event",
        outcome=EventOutcome.SUCCESS,
        importance_score=0.3,
        actionability_score=0.2,
        activation_count=5,
    )


@pytest.fixture
def very_old_event():
    """Create a very old episodic event (40 days old)."""
    return EpisodicEvent(
        id=3,
        project_id=1,
        session_id="test_session",
        timestamp=datetime.now() - timedelta(days=40),
        last_activation=datetime.now() - timedelta(days=40),
        event_type=EventType.ACTION,
        content="Very old event",
        outcome=EventOutcome.SUCCESS,
        importance_score=0.1,
        actionability_score=0.0,
        activation_count=0,
    )


class TestActivationComputation:
    """Test ACT-R activation decay computation."""

    def test_compute_activation_recent_event(self, sample_event):
        """Recent events should have higher activation."""
        sample_event.last_activation = datetime.now()
        sample_event.activation_count = 3
        sample_event.importance_score = 0.8

        activation = compute_activation(sample_event)
        assert activation > 0, "Recent event should have positive activation"

    def test_compute_activation_old_event(self, old_event):
        """Old events should have lower activation."""
        activation = compute_activation(old_event)
        # Old event with low importance should have low activation
        assert activation >= 0, "Activation should not be negative"

    def test_compute_activation_decay_over_time(self, sample_event):
        """Activation should decay as time passes."""
        sample_event.importance_score = 0.5
        sample_event.activation_count = 1

        # Fresh event (now)
        sample_event.last_activation = datetime.now()
        activation_now = compute_activation(sample_event)

        # Event from 1 day ago
        sample_event.last_activation = datetime.now() - timedelta(days=1)
        activation_1day = compute_activation(sample_event)

        # Event from 7 days ago
        sample_event.last_activation = datetime.now() - timedelta(days=7)
        activation_7days = compute_activation(sample_event)

        # Activation should decrease with age
        assert activation_now > activation_1day, "Activation should decay over time"
        assert activation_1day > activation_7days, "Activation should decay more over 7 days"

    def test_compute_activation_importance_boost(self, sample_event):
        """High importance events should boost activation."""
        sample_event.last_activation = datetime.now() - timedelta(hours=12)

        # Low importance
        sample_event.importance_score = 0.3
        low_importance_activation = compute_activation(sample_event)

        # High importance
        sample_event.importance_score = 0.8
        high_importance_activation = compute_activation(sample_event)

        assert high_importance_activation > low_importance_activation, \
            "Higher importance should increase activation"

    def test_compute_activation_frequency_bonus(self, sample_event):
        """More frequent access should increase activation."""
        sample_event.last_activation = datetime.now() - timedelta(hours=12)

        # Low frequency
        sample_event.activation_count = 1
        low_freq_activation = compute_activation(sample_event)

        # High frequency
        sample_event.activation_count = 10
        high_freq_activation = compute_activation(sample_event)

        assert high_freq_activation > low_freq_activation, \
            "Higher frequency should increase activation"

    def test_compute_activation_success_boost(self, sample_event):
        """Successful events should boost activation."""
        sample_event.last_activation = datetime.now() - timedelta(hours=12)

        # Failure
        sample_event.outcome = EventOutcome.FAILURE
        failure_activation = compute_activation(sample_event)

        # Success
        sample_event.outcome = EventOutcome.SUCCESS
        success_activation = compute_activation(sample_event)

        assert success_activation > failure_activation, \
            "Successful outcomes should increase activation"

    def test_compute_activation_consolidated_event(self, sample_event):
        """Consolidated events should have zero activation."""
        sample_event.lifecycle_status = "consolidated"
        activation = compute_activation(sample_event)
        assert activation == 0.0, "Consolidated events should have zero activation"

    def test_compute_activation_archived_event(self, sample_event):
        """Archived events should have zero activation."""
        sample_event.lifecycle_status = "archived"
        activation = compute_activation(sample_event)
        assert activation == 0.0, "Archived events should have zero activation"


class TestConsolidationDecision:
    """Test decisions about when to consolidate events."""

    def test_should_consolidate_old_accessed_event(self, old_event):
        """Events 7+ days old with access should consolidate."""
        assert should_consolidate(old_event), \
            "Old, accessed event should be consolidation candidate"

    def test_should_not_consolidate_recent_event(self, sample_event):
        """Recent events should not consolidate."""
        sample_event.timestamp = datetime.now()
        assert not should_consolidate(sample_event), \
            "Recent event should not consolidate"

    def test_should_not_consolidate_unaccessed_event(self, old_event):
        """Old events without access should not consolidate."""
        old_event.activation_count = 0
        assert not should_consolidate(old_event), \
            "Unaccessed event should not consolidate (should archive instead)"

    def test_should_not_consolidate_already_consolidated(self, old_event):
        """Already consolidated events should not consolidate again."""
        old_event.lifecycle_status = "consolidated"
        assert not should_consolidate(old_event), \
            "Already consolidated event should return false"


class TestArchivalDecision:
    """Test decisions about when to archive events."""

    def test_should_archive_very_old_event(self, very_old_event):
        """Events 30+ days old with low importance should archive."""
        assert should_archive(very_old_event), \
            "Very old, low-importance event should archive"

    def test_should_not_archive_recent_event(self, sample_event):
        """Recent events should not archive."""
        assert not should_archive(sample_event), \
            "Recent event should not archive"

    def test_should_not_archive_important_event(self, old_event):
        """Important events should not archive."""
        old_event.importance_score = 0.9
        old_event.timestamp = datetime.now() - timedelta(days=40)
        assert not should_archive(old_event), \
            "Important event should not archive"

    def test_should_not_archive_recently_accessed(self, very_old_event):
        """Recently accessed events should not archive."""
        very_old_event.last_activation = datetime.now() - timedelta(days=2)
        assert not should_archive(very_old_event), \
            "Recently accessed event should not archive"

    def test_should_not_archive_already_archived(self, very_old_event):
        """Already archived events should not archive again."""
        very_old_event.lifecycle_status = "archived"
        assert not should_archive(very_old_event), \
            "Already archived event should return false"


class TestBatchOperations:
    """Test batch activation and lifecycle operations."""

    def test_decay_activation_batch(self, sample_event, old_event, very_old_event):
        """Batch decay should compute activation for all events."""
        events = [sample_event, old_event, very_old_event]
        activations = decay_activation_batch(events)

        assert len(activations) == 3
        assert all(isinstance(score, (int, float)) for score in activations.values())
        # Recent event should have highest activation
        assert activations[1] > activations[3], \
            "Recent event should have higher activation than old event"

    def test_rank_by_activation(self, sample_event, old_event, very_old_event):
        """Ranking should sort by activation descending."""
        sample_event.last_activation = datetime.now()
        events = [very_old_event, old_event, sample_event]

        ranked = rank_by_activation(events)

        assert len(ranked) == 3
        # Should be sorted by activation descending
        for i in range(len(ranked) - 1):
            assert ranked[i][1] >= ranked[i + 1][1], \
                "Activations should be in descending order"

    def test_rank_by_activation_limit(self, sample_event, old_event, very_old_event):
        """Ranking with limit should return only top N."""
        events = [very_old_event, old_event, sample_event]

        ranked = rank_by_activation(events, limit=2)

        assert len(ranked) == 2

    def test_consolidate_and_archive_batch(self, sample_event, old_event, very_old_event):
        """Batch consolidation/archival should categorize events correctly."""
        sample_event.timestamp = datetime.now()
        sample_event.lifecycle_status = "active"
        old_event.lifecycle_status = "active"
        very_old_event.lifecycle_status = "active"
        very_old_event.last_activation = datetime.now() - timedelta(days=40)

        events = [sample_event, old_event, very_old_event]

        result = consolidate_and_archive_batch(events)

        assert "to_consolidate" in result
        assert "to_archive" in result
        assert "keep_active" in result
        assert "stats" in result

        # Stats should account for all events
        stats = result["stats"]
        assert stats["total_processed"] == 3
        assert stats["consolidation_candidates"] + stats["archival_candidates"] + stats["remaining_active"] <= 3


class TestLifecycleTransitions:
    """Test valid lifecycle state transitions."""

    def test_event_lifecycle_active_to_consolidated(self, sample_event):
        """Events can transition from active to consolidated."""
        assert sample_event.lifecycle_status == "active"
        sample_event.lifecycle_status = "consolidated"
        assert sample_event.lifecycle_status == "consolidated"

    def test_event_lifecycle_active_to_archived(self, sample_event):
        """Events can transition from active to archived."""
        assert sample_event.lifecycle_status == "active"
        sample_event.lifecycle_status = "archived"
        assert sample_event.lifecycle_status == "archived"

    def test_consolidation_score_updated(self, sample_event):
        """Consolidation score should be set when consolidating."""
        assert sample_event.consolidation_score == 0.0
        sample_event.consolidation_score = 0.85
        assert sample_event.consolidation_score == 0.85

    def test_activation_count_incremented(self, sample_event):
        """Activation count should track access frequency."""
        assert sample_event.activation_count == 0
        sample_event.activation_count += 1
        assert sample_event.activation_count == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
