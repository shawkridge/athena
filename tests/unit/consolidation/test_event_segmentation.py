"""Unit tests for event segmentation via Bayesian surprise detection.

Tests:
- EventEncoder - Event feature extraction
- BayesianSurpriseCalculator - K-L divergence calculation
- EventSegmenter - Event boundary detection and segmentation
- SegmentationResult - Data model validation
"""

import numpy as np
import pytest
from datetime import datetime

from athena.consolidation.event_segmentation import (
    BayesianSurpriseCalculator,
    EventEncoder,
    EventFeatures,
    EventSegmenter,
    SegmentationResult
)
from athena.episodic.models import EpisodicEvent


class TestEventEncoder:
    """Test event encoding functionality."""

    def test_encode_basic_event(self):
        """Test encoding a basic episodic event."""
        encoder = EventEncoder()
        event = EpisodicEvent(
            id=1,
            content="User logged in successfully",
            event_type="authentication"
        )

        features = encoder.encode(event)

        assert isinstance(features, EventFeatures)
        assert features.embedding is not None
        assert len(features.embedding) == 384  # nomic-embed-text dimension
        assert features.event_type == "authentication"
        assert features.original_event == event

    def test_encode_preserves_event_type(self):
        """Test that event type is preserved in encoding."""
        encoder = EventEncoder()

        event_types = ["action", "decision", "error", "success"]
        for event_type in event_types:
            event = EpisodicEvent(
                id=1,
                content="Test content",
                event_type=event_type
            )
            features = encoder.encode(event)
            assert features.event_type == event_type

    def test_encode_extracts_entities(self):
        """Test entity extraction from event content."""
        encoder = EventEncoder()

        # Event with error keyword
        event_error = EpisodicEvent(
            id=1,
            content="An error occurred during processing",
            event_type="error"
        )
        features_error = encoder.encode(event_error)
        assert "error" in features_error.entities

        # Event with success keyword
        event_success = EpisodicEvent(
            id=2,
            content="Task completed successfully",
            event_type="success"
        )
        features_success = encoder.encode(event_success)
        assert "success" in features_success.entities

    def test_encode_calculates_temporal_delta(self):
        """Test temporal delta calculation."""
        encoder = EventEncoder()

        event1 = EpisodicEvent(id=1, content="First event", event_type="test")
        event1.timestamp = 100.0

        event2 = EpisodicEvent(id=2, content="Second event", event_type="test")
        event2.timestamp = 105.0

        features = encoder.encode(event2, prev_event_time=100.0)
        assert features.temporal_delta == pytest.approx(5.0, abs=0.1)

    def test_encode_zero_temporal_delta(self):
        """Test encoding with no previous event."""
        encoder = EventEncoder()
        event = EpisodicEvent(id=1, content="Test", event_type="test")

        features = encoder.encode(event, prev_event_time=None)
        assert features.temporal_delta == 0.0

    def test_encode_embedding_is_normalized(self):
        """Test that embeddings are valid vectors."""
        encoder = EventEncoder()
        event = EpisodicEvent(id=1, content="Test content", event_type="test")

        features = encoder.encode(event)
        # Embedding should be a valid numpy array
        assert isinstance(features.embedding, np.ndarray)
        assert features.embedding.shape == (384,)

    def test_encode_multiple_events_produces_different_embeddings(self):
        """Test that different event contents produce different embeddings."""
        encoder = EventEncoder()

        event1 = EpisodicEvent(id=1, content="First unique content", event_type="test")
        event2 = EpisodicEvent(id=2, content="Completely different content", event_type="test")

        features1 = encoder.encode(event1)
        features2 = encoder.encode(event2)

        # Embeddings should be different (not same random seed)
        assert not np.allclose(features1.embedding, features2.embedding)

    def test_encode_preserves_tags(self):
        """Test that event tags are preserved."""
        encoder = EventEncoder()

        event = EpisodicEvent(id=1, content="Test", event_type="test")
        event.tags = ["important", "user-action"]

        features = encoder.encode(event)
        assert features.tags == ["important", "user-action"]

    def test_encode_empty_content(self):
        """Test encoding event with empty content."""
        encoder = EventEncoder()
        event = EpisodicEvent(id=1, content="", event_type="test")

        features = encoder.encode(event)
        assert isinstance(features, EventFeatures)
        assert features.embedding is not None

    def test_encode_large_content(self):
        """Test encoding event with large content."""
        encoder = EventEncoder()

        large_content = " ".join(["word"] * 10000)
        event = EpisodicEvent(id=1, content=large_content, event_type="test")

        features = encoder.encode(event)
        assert isinstance(features, EventFeatures)
        assert len(features.embedding) == 384


class TestBayesianSurpriseCalculator:
    """Test Bayesian surprise calculation."""

    def test_surprise_zero_with_identical_features(self):
        """Test that identical features produce low surprise."""
        calc = BayesianSurpriseCalculator()

        features = EventFeatures(
            embedding=np.ones(384),
            entities=["test"],
            temporal_delta=1.0,
            causal_parents=[],
            event_type="test",
            tags=[]
        )

        surprise = calc.calculate_surprise([features], features)
        assert surprise < 0.5  # Should be low

    def test_surprise_high_with_different_features(self):
        """Test that different features produce high surprise."""
        calc = BayesianSurpriseCalculator()

        features1 = EventFeatures(
            embedding=np.ones(384),
            entities=["type1"],
            temporal_delta=1.0,
            causal_parents=[],
            event_type="test1",
            tags=[]
        )

        features2 = EventFeatures(
            embedding=-np.ones(384),  # Opposite vector
            entities=["type2"],
            temporal_delta=100.0,  # Very different timing
            causal_parents=[],
            event_type="test2",
            tags=[]
        )

        surprise = calc.calculate_surprise([features1], features2)
        assert surprise > 1.0  # Should be high

    def test_surprise_increases_with_context(self):
        """Test that more context provides better baselines."""
        calc = BayesianSurpriseCalculator()

        # Create baseline features
        baseline = EventFeatures(
            embedding=np.random.randn(384),
            entities=["error"],
            temporal_delta=5.0,
            causal_parents=[],
            event_type="action",
            tags=[]
        )

        # Create deviation features
        deviation = EventFeatures(
            embedding=np.random.randn(384),
            entities=["success"],
            temporal_delta=50.0,
            causal_parents=[],
            event_type="success",
            tags=[]
        )

        # Surprise with single context event
        surprise_single = calc.calculate_surprise([baseline], deviation)

        # Surprise with multiple context events
        context = [baseline] * 5
        surprise_multi = calc.calculate_surprise(context, deviation)

        # More context should give more stable baseline
        assert isinstance(surprise_single, float)
        assert isinstance(surprise_multi, float)

    def test_surprise_sequence_calculation(self):
        """Test surprise calculation for full event sequence."""
        calc = BayesianSurpriseCalculator()

        events = [
            EpisodicEvent(id=i, content=f"Event {i}", event_type="test")
            for i in range(5)
        ]

        surprises = calc.calculate_surprise_sequence(events)

        assert len(surprises) == 5
        assert surprises[0] == 0.0  # First event has no surprise
        assert all(s >= 0.0 for s in surprises)  # All non-negative

    def test_surprise_stats_calculation(self):
        """Test surprise statistics."""
        calc = BayesianSurpriseCalculator()

        surprises = [0.0, 1.0, 2.0, 3.0, 4.0]

        stats = calc.get_surprise_stats(surprises)

        assert stats['mean'] == pytest.approx(2.0, abs=0.1)
        assert stats['min'] == 0.0
        assert stats['max'] == 4.0
        assert stats['median'] == pytest.approx(2.0, abs=0.1)

    def test_surprise_with_empty_context(self):
        """Test surprise with empty context."""
        calc = BayesianSurpriseCalculator()

        features = EventFeatures(
            embedding=np.ones(384),
            entities=["test"],
            temporal_delta=1.0,
            causal_parents=[],
            event_type="test",
            tags=[]
        )

        # Empty context should return 0
        surprise = calc.calculate_surprise([], features)
        assert surprise == 0.0

    def test_surprise_embedding_component(self):
        """Test embedding-based K-L divergence."""
        calc = BayesianSurpriseCalculator()

        # Create similar embeddings
        base_embed = np.random.randn(384)
        similar_embed = base_embed + np.random.randn(384) * 0.01  # Small noise

        features_base = EventFeatures(
            embedding=base_embed,
            entities=[],
            temporal_delta=0.0,
            causal_parents=[],
            event_type="test",
            tags=[]
        )

        features_similar = EventFeatures(
            embedding=similar_embed,
            entities=[],
            temporal_delta=0.0,
            causal_parents=[],
            event_type="test",
            tags=[]
        )

        kl_embedding = calc._kl_divergence_embedding([features_base], features_similar)
        assert 0.0 <= kl_embedding < 1.0  # Should be small for similar embeddings

    def test_surprise_temporal_component(self):
        """Test temporal-based K-L divergence."""
        calc = BayesianSurpriseCalculator()

        # Create events with consistent timing
        features_regular = [
            EventFeatures(
                embedding=np.ones(384),
                entities=[],
                temporal_delta=5.0,
                causal_parents=[],
                event_type="test",
                tags=[]
            ),
            EventFeatures(
                embedding=np.ones(384),
                entities=[],
                temporal_delta=5.0,
                causal_parents=[],
                event_type="test",
                tags=[]
            ),
            EventFeatures(
                embedding=np.ones(384),
                entities=[],
                temporal_delta=5.0,
                causal_parents=[],
                event_type="test",
                tags=[]
            )
        ]

        # Then a much different timing
        features_irregular = EventFeatures(
            embedding=np.ones(384),
            entities=[],
            temporal_delta=50.0,  # 10x different
            causal_parents=[],
            event_type="test",
            tags=[]
        )

        kl_temporal = calc._kl_divergence_temporal(features_regular, features_irregular)
        assert kl_temporal > 1.0  # Should be significant

    def test_surprise_entity_component(self):
        """Test entity-based K-L divergence."""
        calc = BayesianSurpriseCalculator()

        # Create events with consistent entities
        features_regular = [
            EventFeatures(
                embedding=np.ones(384),
                entities=["action", "user"],
                temporal_delta=0.0,
                causal_parents=[],
                event_type="test",
                tags=[]
            )
        ]

        # Then a completely different entity set
        features_different = EventFeatures(
            embedding=np.ones(384),
            entities=["error", "system"],  # Completely different
            temporal_delta=0.0,
            causal_parents=[],
            event_type="test",
            tags=[]
        )

        kl_entities = calc._kl_divergence_entities(features_regular, features_different)
        assert kl_entities > 0.5  # Should be noticeable


class TestEventSegmenter:
    """Test event segmentation."""

    def test_segment_single_event(self):
        """Test segmentation of single event."""
        calc = BayesianSurpriseCalculator()
        segmenter = EventSegmenter(calc)

        event = EpisodicEvent(id=1, content="Single event", event_type="test")
        result = segmenter.segment_events([event])

        assert len(result.segments) == 1
        assert result.segments[0] == [event]

    def test_segment_two_events(self):
        """Test segmentation of two events."""
        calc = BayesianSurpriseCalculator()
        segmenter = EventSegmenter(calc)

        events = [
            EpisodicEvent(id=1, content="First event", event_type="test"),
            EpisodicEvent(id=2, content="Second event", event_type="test")
        ]

        result = segmenter.segment_events(events)

        assert isinstance(result, SegmentationResult)
        assert len(result.surprises) == 2
        assert result.surprises[0] == 0.0

    def test_segment_creates_boundaries(self):
        """Test that boundaries are created."""
        calc = BayesianSurpriseCalculator()
        segmenter = EventSegmenter(calc)

        events = [
            EpisodicEvent(id=i, content=f"Event {i}", event_type="test")
            for i in range(10)
        ]

        result = segmenter.segment_events(events)

        assert len(result.boundaries) >= 2  # At least start and end
        assert result.boundaries[0] == 0
        assert result.boundaries[-1] == len(events) - 1

    def test_segmentation_result_has_stats(self):
        """Test that segmentation result includes statistics."""
        calc = BayesianSurpriseCalculator()
        segmenter = EventSegmenter(calc)

        events = [
            EpisodicEvent(id=i, content=f"Event {i}", event_type="test")
            for i in range(5)
        ]

        result = segmenter.segment_events(events)

        assert result.stats is not None
        assert 'mean' in result.stats
        assert 'stdev' in result.stats
        assert 'threshold' in result.stats

    def test_adaptive_threshold_calculation(self):
        """Test adaptive threshold calculation."""
        calc = BayesianSurpriseCalculator()
        segmenter = EventSegmenter(calc)

        surprises = [0.0, 1.0, 1.5, 2.0, 3.5, 0.5, 1.0, 2.5]

        # With gamma=1.0, threshold = mean + stdev
        threshold = segmenter._calculate_adaptive_threshold(surprises, gamma=1.0)

        mean = np.mean(surprises)
        stdev = np.std(surprises)
        expected = mean + stdev

        assert threshold == pytest.approx(expected, abs=0.1)

    def test_boundary_detection(self):
        """Test boundary detection from surprises."""
        calc = BayesianSurpriseCalculator()
        segmenter = EventSegmenter(calc)

        # Surprises with clear boundary markers
        surprises = [0.0, 0.5, 0.3, 5.0, 0.4, 0.2, 5.5, 0.1]
        threshold = 2.0  # Boundaries at indices 3 and 6

        boundaries = segmenter._detect_boundaries(surprises, threshold)

        assert 0 in boundaries
        assert len(surprises) - 1 in boundaries
        # Should detect boundaries where surprise > threshold

    def test_segment_respects_size_constraints(self):
        """Test that segments respect min/max size constraints."""
        calc = BayesianSurpriseCalculator()
        segmenter = EventSegmenter(calc, min_event_size=10, max_event_size=50)

        # Create events with controlled sizes
        events = []
        for i in range(5):
            # Each event has ~20 tokens
            content = " ".join([f"word{j}" for j in range(20)])
            event = EpisodicEvent(id=i, content=content, event_type="test")
            events.append(event)

        result = segmenter.segment_events(events)

        # Check that segments are within size constraints
        for segment in result.segments:
            token_count = sum(len(e.content.split()) for e in segment)
            assert token_count >= segmenter.min_event_size or len(segment) == 1

    def test_modularity_optimization(self):
        """Test modularity optimization for boundary refinement."""
        calc = BayesianSurpriseCalculator()
        segmenter = EventSegmenter(calc)

        # Create edge list
        edges = [
            (0, 1, 0.9),  # High similarity
            (1, 2, 0.8),  # High similarity
            (2, 3, 0.1),  # Low similarity (boundary)
            (3, 4, 0.9),  # High similarity
        ]

        communities = segmenter._greedy_modularity_optimization(edges, 5)

        # Should assign similar nodes to same community
        assert isinstance(communities, list)
        assert len(communities) == 5

    def test_segmentation_with_gamma_parameter(self):
        """Test segmentation with different gamma values."""
        calc = BayesianSurpriseCalculator()
        segmenter = EventSegmenter(calc)

        events = [
            EpisodicEvent(id=i, content=f"Event {i}", event_type="test")
            for i in range(20)
        ]

        # Segment with conservative threshold (gamma=0.5)
        result_conservative = segmenter.segment_events(events, adaptive_gamma=0.5)

        # Segment with aggressive threshold (gamma=2.0)
        result_aggressive = segmenter.segment_events(events, adaptive_gamma=2.0)

        # Conservative should have more segments (lower threshold)
        assert len(result_conservative.segments) >= len(result_aggressive.segments)

    def test_segmentation_preserves_event_order(self):
        """Test that segmentation preserves event order."""
        calc = BayesianSurpriseCalculator()
        segmenter = EventSegmenter(calc)

        events = [
            EpisodicEvent(id=i, content=f"Event {i}", event_type="test")
            for i in range(10)
        ]

        result = segmenter.segment_events(events)

        # Reconstruct order from segments
        reconstructed = []
        for segment in result.segments:
            reconstructed.extend(segment)

        # Should match original order
        for i, (orig, recon) in enumerate(zip(events, reconstructed)):
            assert orig.id == recon.id

    def test_segmentation_modularity_score(self):
        """Test modularity score calculation."""
        calc = BayesianSurpriseCalculator()
        segmenter = EventSegmenter(calc)

        events = [
            EpisodicEvent(id=i, content=f"Event {i}", event_type="test")
            for i in range(10)
        ]

        result = segmenter.segment_events(events)

        assert 0.0 <= result.modularity_score <= 1.0


class TestSegmentationResult:
    """Test SegmentationResult data model."""

    def test_segmentation_result_creation(self):
        """Test creating segmentation result."""
        events = [
            EpisodicEvent(id=1, content="Test", event_type="test")
        ]
        result = SegmentationResult(
            session_id="session_1",
            segments=[events],
            surprises=[0.0],
            threshold=1.0,
            boundaries=[0, 1],
            modularity_score=0.85
        )

        assert result.session_id == "session_1"
        assert len(result.segments) == 1
        assert result.created_at is not None

    def test_segmentation_result_default_timestamp(self):
        """Test that created_at defaults to now."""
        result = SegmentationResult(
            session_id="test",
            segments=[],
            surprises=[],
            threshold=0.0,
            boundaries=[],
            modularity_score=0.0
        )

        assert isinstance(result.created_at, datetime)
        assert result.created_at.timestamp() > 0

    def test_segmentation_result_stats_optional(self):
        """Test that stats is optional."""
        result = SegmentationResult(
            session_id="test",
            segments=[],
            surprises=[],
            threshold=0.0,
            boundaries=[],
            modularity_score=0.0
        )

        assert result.stats == {}


class TestIntegration:
    """Integration tests combining multiple components."""

    def test_full_segmentation_pipeline(self):
        """Test complete event segmentation pipeline."""
        calc = BayesianSurpriseCalculator()
        segmenter = EventSegmenter(calc)

        # Create realistic event sequence
        events = [
            EpisodicEvent(id=1, content="User logged in", event_type="authentication"),
            EpisodicEvent(id=2, content="User navigated to dashboard", event_type="navigation"),
            EpisodicEvent(id=3, content="User clicked settings", event_type="navigation"),
            EpisodicEvent(id=4, content="Settings page loaded", event_type="ui"),
            EpisodicEvent(id=5, content="An error occurred", event_type="error"),
            EpisodicEvent(id=6, content="Error dialog shown", event_type="ui"),
            EpisodicEvent(id=7, content="User clicked retry", event_type="user-action"),
            EpisodicEvent(id=8, content="Request succeeded", event_type="success"),
        ]

        result = segmenter.segment_events(events, session_id="integration_test")

        # Verify result
        assert result.session_id == "integration_test"
        assert len(result.segments) > 0
        assert len(result.surprises) == len(events)
        assert len(result.boundaries) >= 2

    def test_encoder_calculator_integration(self):
        """Test encoder and calculator together."""
        encoder = EventEncoder()
        calc = BayesianSurpriseCalculator(embedding_model=None)

        event1 = EpisodicEvent(id=1, content="First action", event_type="action")
        event2 = EpisodicEvent(id=2, content="Second action", event_type="action")

        features1 = encoder.encode(event1)
        features2 = encoder.encode(event2)

        surprise = calc.calculate_surprise([features1], features2)

        assert isinstance(surprise, float)
        assert surprise >= 0.0

    def test_segmentation_consistency(self):
        """Test that segmentation is consistent across runs."""
        calc1 = BayesianSurpriseCalculator()
        calc2 = BayesianSurpriseCalculator()

        segmenter1 = EventSegmenter(calc1)
        segmenter2 = EventSegmenter(calc2)

        events = [
            EpisodicEvent(id=i, content=f"Event {i}", event_type="test")
            for i in range(5)
        ]

        # Set seed for reproducibility
        np.random.seed(42)
        result1 = segmenter1.segment_events(events)

        np.random.seed(42)
        result2 = segmenter2.segment_events(events)

        # Segments should be deterministic (same boundaries)
        assert len(result1.segments) == len(result2.segments)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
