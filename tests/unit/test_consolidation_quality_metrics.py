"""Unit tests for Consolidation Quality Metrics.

Tests measurement of consolidation effectiveness:
- Compression ratio (episodic → semantic)
- Retrieval recall (information preservation)
- Pattern consistency (generalization quality)
- Information density (token efficiency)
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock

from athena.consolidation.quality_metrics import ConsolidationQualityMetrics
from athena.episodic.models import EpisodicEvent, EventType, EventOutcome, EventContext


class TestConsolidationQualityMetrics:
    """Test consolidation quality metrics."""

    @pytest.fixture
    def mock_stores(self):
        """Create mock episodic and semantic stores."""
        episodic_store = MagicMock()
        semantic_store = MagicMock()
        return episodic_store, semantic_store

    @pytest.fixture
    def metrics(self, mock_stores):
        """Create ConsolidationQualityMetrics instance."""
        episodic_store, semantic_store = mock_stores
        return ConsolidationQualityMetrics(episodic_store, semantic_store)

    def test_metrics_initialization(self, metrics):
        """Test ConsolidationQualityMetrics initialization."""
        assert metrics.episodic_store is not None
        assert metrics.semantic_store is not None

    def test_measure_compression_ratio_empty_session(self, metrics, mock_stores):
        """Test compression ratio with empty session."""
        episodic_store, semantic_store = mock_stores
        episodic_store.get_events_for_session.return_value = []
        semantic_store.search.return_value = []

        ratio = metrics.measure_compression_ratio("session_1")
        assert ratio == 0.0

    def test_measure_compression_ratio_with_events(self, metrics, mock_stores):
        """Test compression ratio with episodic and semantic data."""
        episodic_store, semantic_store = mock_stores

        # Create sample episodic events
        events = [
            EpisodicEvent(
                id=1,
                project_id=1,
                session_id="session_1",
                timestamp=datetime.now(),
                event_type=EventType.ACTION,
                content="This is a long event content with many words",
                outcome=EventOutcome.SUCCESS,
                context=EventContext(cwd="/test", files=[], task="task1"),
            ),
            EpisodicEvent(
                id=2,
                project_id=1,
                session_id="session_1",
                timestamp=datetime.now(),
                event_type=EventType.ACTION,
                content="Another event with multiple tokens in the content",
                outcome=EventOutcome.SUCCESS,
                context=EventContext(cwd="/test", files=[], task="task1"),
            ),
        ]

        # Mock semantic memories (should be smaller)
        semantic_memories = [MagicMock(content="Extracted pattern A")]

        episodic_store.get_events_for_session.return_value = events
        semantic_store.search.return_value = semantic_memories

        ratio = metrics.measure_compression_ratio("session_1")

        # Expected: 1 - (2 tokens / 18 tokens) ≈ 0.89
        assert 0.0 <= ratio <= 1.0
        assert ratio > 0.8  # Should have good compression

    def test_measure_compression_ratio_clamp(self, metrics, mock_stores):
        """Test that compression ratio is clamped to [0, 1]."""
        episodic_store, semantic_store = mock_stores

        # Create event with few words
        events = [
            EpisodicEvent(
                id=1,
                project_id=1,
                session_id="session_1",
                timestamp=datetime.now(),
                event_type=EventType.ACTION,
                content="Short",
                outcome=EventOutcome.SUCCESS,
                context=EventContext(cwd="/test", files=[], task="task1"),
            ),
        ]

        # Create semantic memories with more tokens
        semantic_memories = [
            MagicMock(content="Long semantic memory content with many tokens")
        ]

        episodic_store.get_events_for_session.return_value = events
        semantic_store.search.return_value = semantic_memories

        ratio = metrics.measure_compression_ratio("session_1")
        assert 0.0 <= ratio <= 1.0

    def test_measure_retrieval_recall_empty_session(self, metrics, mock_stores):
        """Test retrieval recall with empty session."""
        episodic_store, semantic_store = mock_stores
        episodic_store.get_events_for_session.return_value = []

        result = metrics.measure_retrieval_recall("session_1")

        assert result["episodic_recall"] == 0.0
        assert result["semantic_recall"] == 0.0
        assert result["relative_recall"] == 0.0
        assert result["recall_loss"] == 1.0

    def test_measure_retrieval_recall_with_events(self, metrics, mock_stores):
        """Test retrieval recall with episodic and semantic data."""
        episodic_store, semantic_store = mock_stores

        # Create sample events with identifiable content
        events = [
            EpisodicEvent(
                id=1,
                project_id=1,
                session_id="session_1",
                timestamp=datetime.now(),
                event_type=EventType.ACTION,
                content="Fixed authentication bug in JWT implementation",
                outcome=EventOutcome.SUCCESS,
                context=EventContext(cwd="/test", files=[], task="task1"),
            ),
        ]

        episodic_store.get_events_for_session.return_value = events
        semantic_store.search.return_value = [MagicMock(content="JWT authentication fixed")]

        result = metrics.measure_retrieval_recall("session_1")

        assert "episodic_recall" in result
        assert "semantic_recall" in result
        assert "relative_recall" in result
        assert "recall_loss" in result
        assert 0.0 <= result["relative_recall"] <= 1.0
        assert 0.0 <= result["recall_loss"] <= 1.0

    def test_measure_pattern_consistency_empty_session(self, metrics, mock_stores):
        """Test pattern consistency with empty session."""
        episodic_store, semantic_store = mock_stores
        episodic_store.get_events_for_session.return_value = []

        consistency = metrics.measure_pattern_consistency("session_1")
        assert consistency == 0.5  # Default for empty session

    def test_measure_pattern_consistency_with_events(self, metrics, mock_stores):
        """Test pattern consistency with patterns and events."""
        episodic_store, semantic_store = mock_stores

        # Create events
        events = [
            EpisodicEvent(
                id=1,
                project_id=1,
                session_id="session_1",
                timestamp=datetime.now(),
                event_type=EventType.ERROR,
                content="Error occurred",
                outcome=EventOutcome.FAILURE,
                context=EventContext(cwd="/test", files=[], task="task1"),
            ),
            EpisodicEvent(
                id=2,
                project_id=1,
                session_id="session_1",
                timestamp=datetime.now(),
                event_type=EventType.ACTION,
                content="Fixed error",
                outcome=EventOutcome.SUCCESS,
                context=EventContext(cwd="/test", files=[], task="task1"),
            ),
        ]

        # Mock semantic patterns
        pattern = MagicMock()
        pattern.confidence = 0.85

        episodic_store.get_events_for_session.return_value = events
        semantic_store.search.return_value = [pattern]

        consistency = metrics.measure_pattern_consistency("session_1")
        assert 0.0 <= consistency <= 1.0

    def test_measure_information_density_empty_session(self, metrics, mock_stores):
        """Test information density with empty session."""
        episodic_store, semantic_store = mock_stores
        semantic_store.search.return_value = []

        result = metrics.measure_information_density("session_1")

        assert result["avg_density"] == 0.0
        assert result["max_density"] == 0.0
        assert result["min_density"] == 0.0
        assert result["consistency"] == 0.0

    def test_measure_information_density_with_memories(self, metrics, mock_stores):
        """Test information density with semantic memories."""
        episodic_store, semantic_store = mock_stores

        # Create mock memories with relevance scores
        memory1 = MagicMock()
        memory1.content = "This is a semantic memory"
        memory1.relevance_score = 0.9

        memory2 = MagicMock()
        memory2.content = "Another memory pattern"
        memory2.relevance_score = 0.7

        semantic_store.search.return_value = [memory1, memory2]

        result = metrics.measure_information_density("session_1")

        assert "avg_density" in result
        assert "max_density" in result
        assert "min_density" in result
        assert "consistency" in result
        assert result["avg_density"] > 0
        assert result["max_density"] >= result["avg_density"]
        assert result["min_density"] <= result["avg_density"]

    def test_measure_all(self, metrics, mock_stores):
        """Test measuring all metrics together."""
        episodic_store, semantic_store = mock_stores

        # Setup mock data
        event = EpisodicEvent(
            id=1,
            project_id=1,
            session_id="session_1",
            timestamp=datetime.now(),
            event_type=EventType.ACTION,
            content="Action taken successfully",
            outcome=EventOutcome.SUCCESS,
            context=EventContext(cwd="/test", files=[], task="task1"),
        )

        memory = MagicMock()
        memory.content = "Pattern extracted"
        memory.relevance_score = 0.8
        memory.confidence = 0.85

        episodic_store.get_events_for_session.return_value = [event]
        semantic_store.search.return_value = [memory]

        result = metrics.measure_all("session_1")

        assert "session_id" in result
        assert "measured_at" in result
        assert "compression_ratio" in result
        assert "retrieval_recall" in result
        assert "pattern_consistency" in result
        assert "information_density" in result

        # Validate result types
        assert isinstance(result["compression_ratio"], float)
        assert isinstance(result["retrieval_recall"], dict)
        assert isinstance(result["pattern_consistency"], float)
        assert isinstance(result["information_density"], dict)

    def test_generate_queries(self, metrics):
        """Test query generation from events."""
        events = [
            EpisodicEvent(
                id=1,
                project_id=1,
                session_id="session_1",
                timestamp=datetime.now(),
                event_type=EventType.ACTION,
                content="This is a test event content",
                outcome=EventOutcome.SUCCESS,
                context=EventContext(cwd="/test", files=[], task="task1"),
            ),
        ]

        queries = metrics._generate_queries(events)
        assert len(queries) > 0
        assert isinstance(queries[0], str)

    def test_calculate_event_entropy(self, metrics):
        """Test event entropy calculation."""
        events = [
            EpisodicEvent(
                id=1,
                project_id=1,
                session_id="session_1",
                timestamp=datetime.now(),
                event_type=EventType.ACTION,
                content="Action",
                outcome=EventOutcome.SUCCESS,
                context=EventContext(cwd="/test", files=[], task="task1"),
            ),
            EpisodicEvent(
                id=2,
                project_id=1,
                session_id="session_1",
                timestamp=datetime.now(),
                event_type=EventType.ERROR,
                content="Error",
                outcome=EventOutcome.FAILURE,
                context=EventContext(cwd="/test", files=[], task="task1"),
            ),
        ]

        entropy = metrics._calculate_event_entropy(events)
        assert 0.0 <= entropy <= 1.0  # Binary entropy should be <= 1

    def test_error_handling_compression(self, metrics, mock_stores):
        """Test error handling in compression measurement."""
        episodic_store, semantic_store = mock_stores
        episodic_store.get_events_for_session.side_effect = Exception("Database error")

        # Should return 0.0 on error
        ratio = metrics.measure_compression_ratio("session_1")
        assert ratio == 0.0

    def test_error_handling_recall(self, metrics, mock_stores):
        """Test error handling in recall measurement."""
        episodic_store, semantic_store = mock_stores
        episodic_store.get_events_for_session.side_effect = Exception("Database error")

        # Should return zero metrics on error
        result = metrics.measure_retrieval_recall("session_1")
        assert result["episodic_recall"] == 0.0
        assert result["recall_loss"] == 1.0

    def test_consolidation_metrics_integration(self, metrics, mock_stores):
        """Integration test: Full consolidation cycle."""
        episodic_store, semantic_store = mock_stores

        # Setup: 2 episodic events, 1 consolidated semantic pattern
        events = [
            EpisodicEvent(
                id=1,
                project_id=1,
                session_id="session_1",
                timestamp=datetime.now(),
                event_type=EventType.DECISION,
                content="Decided to refactor authentication module",
                outcome=EventOutcome.SUCCESS,
                context=EventContext(cwd="/src/auth", files=["auth.py"], task="refactor"),
            ),
            EpisodicEvent(
                id=2,
                project_id=1,
                session_id="session_1",
                timestamp=datetime.now(),
                event_type=EventType.ACTION,
                content="Implemented new JWT token handler",
                outcome=EventOutcome.SUCCESS,
                context=EventContext(cwd="/src/auth", files=["jwt.py"], task="refactor"),
            ),
        ]

        consolidated_pattern = MagicMock()
        consolidated_pattern.content = "JWT refactoring pattern"
        consolidated_pattern.relevance_score = 0.9
        consolidated_pattern.confidence = 0.88

        episodic_store.get_events_for_session.return_value = events
        semantic_store.search.return_value = [consolidated_pattern]

        # Measure all metrics
        result = metrics.measure_all("session_1")

        # Verify reasonable values
        assert result["compression_ratio"] > 0.5  # Should compress well
        assert result["retrieval_recall"]["relative_recall"] > 0.5  # Should preserve info
        assert result["pattern_consistency"] > 0.4  # Pattern should be somewhat consistent
        assert result["information_density"]["avg_density"] > 0.1  # Should have some density
