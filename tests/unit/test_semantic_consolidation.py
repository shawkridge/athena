"""Tests for memory consolidation and reconsolidation logic."""

import pytest
from datetime import datetime, timedelta
from athena.core.models import Memory, MemoryType, ConsolidationState


class TestConsolidationStates:
    """Test consolidation state transitions."""

    def test_unconsolidated_state(self):
        """Test unconsolidated memory."""
        memory = Memory(
            project_id=1,
            content="New memory",
            memory_type=MemoryType.FACT,
            consolidation_state=ConsolidationState.UNCONSOLIDATED,
        )
        assert memory.consolidation_state == ConsolidationState.UNCONSOLIDATED

    def test_consolidating_state(self):
        """Test consolidating memory."""
        memory = Memory(
            project_id=1,
            content="Being consolidated",
            memory_type=MemoryType.FACT,
            consolidation_state=ConsolidationState.CONSOLIDATING,
        )
        assert memory.consolidation_state == ConsolidationState.CONSOLIDATING

    def test_consolidated_state(self):
        """Test consolidated memory (default)."""
        memory = Memory(
            project_id=1,
            content="Stable memory",
            memory_type=MemoryType.FACT,
        )
        assert memory.consolidation_state == ConsolidationState.CONSOLIDATED

    def test_labile_state(self):
        """Test labile memory (retrieved, open for modification)."""
        memory = Memory(
            project_id=1,
            content="Retrieved memory",
            memory_type=MemoryType.FACT,
            consolidation_state=ConsolidationState.LABILE,
        )
        assert memory.consolidation_state == ConsolidationState.LABILE

    def test_reconsolidating_state(self):
        """Test reconsolidating memory."""
        memory = Memory(
            project_id=1,
            content="Being updated",
            memory_type=MemoryType.FACT,
            consolidation_state=ConsolidationState.RECONSOLIDATING,
        )
        assert memory.consolidation_state == ConsolidationState.RECONSOLIDATING

    def test_superseded_state(self):
        """Test superseded memory (replaced by newer version)."""
        memory = Memory(
            project_id=1,
            content="Old version",
            memory_type=MemoryType.FACT,
            consolidation_state=ConsolidationState.SUPERSEDED,
            superseded_by=2,
        )
        assert memory.consolidation_state == ConsolidationState.SUPERSEDED
        assert memory.superseded_by == 2


class TestMemoryVersion:
    """Test memory versioning."""

    def test_version_tracking(self):
        """Test version field."""
        memory = Memory(
            project_id=1,
            content="Test",
            memory_type=MemoryType.FACT,
            version=1,
        )
        assert memory.version == 1

    def test_version_increment(self):
        """Test version incrementing on update."""
        v1 = Memory(
            id=1,
            project_id=1,
            content="Original",
            memory_type=MemoryType.FACT,
            version=1,
        )
        # Simulating update
        v2 = Memory(
            id=1,
            project_id=1,
            content="Updated",
            memory_type=MemoryType.FACT,
            version=2,
            superseded_by=None,
        )
        assert v2.version == v1.version + 1

    def test_superseded_by_reference(self):
        """Test superseded_by points to newer version."""
        old_memory = Memory(
            id=1,
            project_id=1,
            content="Old",
            memory_type=MemoryType.FACT,
            consolidation_state=ConsolidationState.SUPERSEDED,
            superseded_by=2,
            version=1,
        )
        new_memory = Memory(
            id=2,
            project_id=1,
            content="New",
            memory_type=MemoryType.FACT,
            version=2,
        )
        assert old_memory.superseded_by == new_memory.id


class TestReconsolidationWindow:
    """Test reconsolidation window logic."""

    def test_last_retrieved_tracking(self):
        """Test last_retrieved timestamp."""
        now = datetime.now()
        memory = Memory(
            project_id=1,
            content="Test",
            memory_type=MemoryType.FACT,
            last_retrieved=now,
        )
        assert memory.last_retrieved == now

    def test_reconsolidation_window_calculation(self):
        """Test reconsolidation window window_minutes."""
        now = datetime.now()
        retrieved_3_min_ago = now - timedelta(minutes=3)
        retrieved_10_min_ago = now - timedelta(minutes=10)

        memory = Memory(
            project_id=1,
            content="Test",
            memory_type=MemoryType.FACT,
            last_retrieved=retrieved_3_min_ago,
        )

        # Within 5 minute window
        window_minutes = 5
        time_elapsed = (now - memory.last_retrieved).total_seconds() / 60
        in_window = time_elapsed < window_minutes
        assert in_window

        # Update to 10 minutes ago
        memory.last_retrieved = retrieved_10_min_ago
        time_elapsed = (now - memory.last_retrieved).total_seconds() / 60
        in_window = time_elapsed < window_minutes
        assert not in_window

    def test_window_duration_variations(self):
        """Test different window durations."""
        now = datetime.now()

        for minutes_ago in [1, 5, 10, 30, 60]:
            retrieved = now - timedelta(minutes=minutes_ago)
            memory = Memory(
                project_id=1,
                content="Test",
                memory_type=MemoryType.FACT,
                last_retrieved=retrieved,
            )

            # Test 5 minute window
            time_elapsed = (now - memory.last_retrieved).total_seconds() / 60
            in_5min_window = time_elapsed < 5
            assert in_5min_window == (minutes_ago < 5)


class TestAccessTracking:
    """Test memory access tracking."""

    def test_access_count(self):
        """Test access_count field."""
        memory = Memory(
            project_id=1,
            content="Test",
            memory_type=MemoryType.FACT,
            access_count=0,
        )
        assert memory.access_count == 0

    def test_access_count_increments(self):
        """Test access count increments on retrieval."""
        memory = Memory(
            project_id=1,
            content="Test",
            memory_type=MemoryType.FACT,
            access_count=5,
        )
        # Simulate increment
        memory.access_count += 1
        assert memory.access_count == 6

    def test_last_accessed_timestamp(self):
        """Test last_accessed tracking."""
        now = datetime.now()
        memory = Memory(
            project_id=1,
            content="Test",
            memory_type=MemoryType.FACT,
            last_accessed=now,
        )
        assert memory.last_accessed == now


class TestUsefulnessScoring:
    """Test memory usefulness scoring."""

    def test_usefulness_score_range(self):
        """Test usefulness score is normalized."""
        for score in [0.0, 0.5, 1.0]:
            memory = Memory(
                project_id=1,
                content="Test",
                memory_type=MemoryType.FACT,
                usefulness_score=score,
            )
            assert 0.0 <= memory.usefulness_score <= 1.0

    def test_usefulness_score_defaults_to_zero(self):
        """Test usefulness score defaults to 0."""
        memory = Memory(
            project_id=1,
            content="Test",
            memory_type=MemoryType.FACT,
        )
        assert memory.usefulness_score == 0.0

    def test_usefulness_based_on_access(self):
        """Test usefulness could relate to access patterns."""
        # High access count
        frequent = Memory(
            project_id=1,
            content="Frequently used",
            memory_type=MemoryType.FACT,
            access_count=50,
            usefulness_score=0.8,
        )

        # Low access count
        infrequent = Memory(
            project_id=1,
            content="Rarely used",
            memory_type=MemoryType.FACT,
            access_count=2,
            usefulness_score=0.2,
        )

        assert frequent.usefulness_score > infrequent.usefulness_score
