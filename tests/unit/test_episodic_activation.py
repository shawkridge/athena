"""Tests for episodic memory activation system (ACT-R decay)."""

import pytest
import math
from datetime import datetime, timedelta
from athena.episodic.models import EpisodicEvent, EventType, EventOutcome
from athena.episodic.activation import compute_activation


class TestActivationDecay:
    """Test ACT-R activation decay calculations."""

    @pytest.fixture
    def base_event(self):
        """Create a base test event."""
        return EpisodicEvent(
            project_id=1,
            session_id="test",
            content="Test event",
            event_type=EventType.ACTION,
            outcome=EventOutcome.SUCCESS,
            lifecycle_status="active",
        )

    def test_activation_consolidated_event_is_zero(self, base_event):
        """Test that consolidated events have zero activation."""
        base_event.lifecycle_status = "consolidated"
        activation = compute_activation(base_event)
        assert activation == 0.0

    def test_activation_archived_event_is_zero(self, base_event):
        """Test that archived events have zero activation."""
        base_event.lifecycle_status = "archived"
        activation = compute_activation(base_event)
        assert activation == 0.0

    def test_activation_active_event_positive(self, base_event):
        """Test that active recent events have positive activation."""
        base_event.lifecycle_status = "active"
        base_event.last_activation = datetime.now()
        activation = compute_activation(base_event)
        assert activation > 0.0

    def test_activation_decays_with_time(self, base_event):
        """Test that activation decays as time passes."""
        base_event.lifecycle_status = "active"

        # Recent event
        base_event.last_activation = datetime.now()
        recent_activation = compute_activation(base_event)

        # Old event (1 day ago)
        base_event.last_activation = datetime.now() - timedelta(hours=24)
        old_activation = compute_activation(base_event)

        # Old event should have lower activation
        assert recent_activation > old_activation

    def test_activation_with_importance_boost(self, base_event):
        """Test that high-importance events get boost."""
        base_event.lifecycle_status = "active"
        base_event.last_activation = datetime.now()

        # Low importance
        base_event.importance_score = 0.3
        low_importance_activation = compute_activation(base_event)

        # High importance
        base_event.importance_score = 0.9
        high_importance_activation = compute_activation(base_event)

        # High importance should have higher activation
        assert high_importance_activation > low_importance_activation

    def test_activation_with_actionability_boost(self, base_event):
        """Test that actionable events get boost."""
        base_event.lifecycle_status = "active"
        base_event.last_activation = datetime.now()

        # Not actionable
        base_event.has_next_step = False
        base_event.actionability_score = 0.3
        non_actionable = compute_activation(base_event)

        # Actionable with next step
        base_event.has_next_step = True
        base_event.actionability_score = 0.9
        actionable = compute_activation(base_event)

        # Actionable should have higher activation
        assert actionable > non_actionable

    def test_activation_with_consolidation_boost(self, base_event):
        """Test that consolidated patterns get activation boost."""
        base_event.lifecycle_status = "active"
        base_event.last_activation = datetime.now()

        # No consolidation score
        base_event.consolidation_score = 0.0
        unconsolidated = compute_activation(base_event)

        # High consolidation score (pattern extracted)
        base_event.consolidation_score = 0.9
        consolidated = compute_activation(base_event)

        # Consolidated patterns should have higher activation
        assert consolidated > unconsolidated

    def test_activation_with_frequency_bonus(self, base_event):
        """Test that frequently accessed events get bonus."""
        base_event.lifecycle_status = "active"
        base_event.last_activation = datetime.now()

        # No prior accesses
        base_event.activation_count = 0
        zero_access = compute_activation(base_event)

        # Many prior accesses
        base_event.activation_count = 10
        many_access = compute_activation(base_event)

        # Frequently accessed should have higher activation
        assert many_access > zero_access

    def test_activation_with_custom_decay_rate(self, base_event):
        """Test that decay rate parameter affects activation."""
        base_event.lifecycle_status = "active"
        base_event.last_activation = datetime.now() - timedelta(hours=2)

        # Slower decay (lower rate)
        activation_slow = compute_activation(base_event, decay_rate=0.3)

        # Faster decay (higher rate)
        activation_fast = compute_activation(base_event, decay_rate=0.7)

        # Slower decay should have higher activation
        assert activation_slow > activation_fast

    def test_activation_prevents_zero_log(self, base_event):
        """Test that very recent events don't cause log(0) error."""
        base_event.lifecycle_status = "active"
        # Just now
        base_event.last_activation = datetime.now()

        # Should not raise
        activation = compute_activation(base_event)
        assert isinstance(activation, (int, float))
        assert activation >= 0

    def test_activation_very_recent_vs_slightly_old(self, base_event):
        """Test activation for very recent events."""
        base_event.lifecycle_status = "active"

        # Current time
        base_event.last_activation = datetime.now()
        very_recent = compute_activation(base_event)

        # 1 second ago
        base_event.last_activation = datetime.now() - timedelta(seconds=1)
        slightly_old = compute_activation(base_event)

        # Very recent should be similar to slightly old (no cliff)
        assert abs(very_recent - slightly_old) < 0.5

    def test_activation_combines_all_boosts(self, base_event):
        """Test that all boosts combine properly."""
        base_event.lifecycle_status = "active"
        base_event.last_activation = datetime.now()
        base_event.importance_score = 0.9
        base_event.has_next_step = True
        base_event.consolidation_score = 0.8
        base_event.activation_count = 5

        activation = compute_activation(base_event)

        # Should be positive and reasonably high
        assert activation > 0.0
        # With all boosts, should be significant
        assert activation > 2.0

    def test_activation_reference_time_parameter(self, base_event):
        """Test that reference time parameter is used."""
        base_event.lifecycle_status = "active"
        base_event.last_activation = datetime(2024, 1, 1, 12, 0, 0)

        # Reference time just after
        ref_time = datetime(2024, 1, 1, 13, 0, 0)
        activation_1hour = compute_activation(base_event, current_time=ref_time)

        # Reference time much later
        ref_time_later = datetime(2024, 1, 2, 13, 0, 0)
        activation_25hours = compute_activation(base_event, current_time=ref_time_later)

        # More decay with later reference time
        assert activation_1hour > activation_25hours

    def test_activation_edge_case_zero_importance(self, base_event):
        """Test activation with zero importance."""
        base_event.lifecycle_status = "active"
        base_event.last_activation = datetime.now()
        base_event.importance_score = 0.0

        activation = compute_activation(base_event)
        # Should still be positive (has base level decay)
        assert activation >= 0.0

    def test_activation_edge_case_all_zeros(self, base_event):
        """Test activation with all zero values."""
        base_event.lifecycle_status = "active"
        base_event.last_activation = datetime.now()
        base_event.importance_score = 0.0
        base_event.actionability_score = 0.0
        base_event.consolidation_score = 0.0
        base_event.activation_count = 0

        activation = compute_activation(base_event)
        # Should still be valid and non-negative
        assert isinstance(activation, (int, float))
        assert activation >= 0.0
