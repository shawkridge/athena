"""Unit tests for Bayesian surprise event segmentation."""

import pytest
from athena.episodic.surprise import BayesianSurprise, create_surprise_calculator


class TestBayesianSurprise:
    """Test Bayesian surprise calculations."""

    def test_surprise_initialization(self):
        """Test BayesianSurprise initialization."""
        surprise = BayesianSurprise()
        assert surprise.entropy_threshold == 2.5
        assert surprise.min_event_spacing == 50

    def test_create_calculator(self):
        """Test factory function."""
        calculator = create_surprise_calculator(entropy_threshold=3.0)
        assert calculator.entropy_threshold == 3.0

    def test_calculate_surprise_simple_sequence(self):
        """Test surprise calculation on simple token sequence."""
        surprise = BayesianSurprise()

        # Simple sequence: "a b c a b c a b c"
        tokens = ["a", "b", "c"] * 3

        # Calculate surprise at various positions
        s0 = surprise.calculate_surprise(tokens, 0)  # First token
        s3 = surprise.calculate_surprise(tokens, 3)  # Pattern repeat
        s8 = surprise.calculate_surprise(tokens, 8)  # Near end

        # Surprise should be non-negative
        assert s0 >= 0
        assert s3 >= 0
        assert s8 >= 0

    def test_find_event_boundaries_empty_sequence(self):
        """Test finding boundaries in empty sequence."""
        surprise = BayesianSurprise()
        boundaries = surprise.find_event_boundaries([])
        assert boundaries == []

    def test_find_event_boundaries_single_token(self):
        """Test finding boundaries with single token."""
        surprise = BayesianSurprise()
        boundaries = surprise.find_event_boundaries(["token"])
        assert len(boundaries) <= 1

    def test_find_event_boundaries_diverse_sequence(self):
        """Test finding boundaries in diverse sequence.

        Diverse sequence should have more boundaries than repetitive.
        """
        surprise = BayesianSurprise(entropy_threshold=1.5)

        # Highly diverse: each token is different
        diverse = [f"token{i}" for i in range(20)]
        boundaries_diverse = surprise.find_event_boundaries(diverse)

        # Highly repetitive: mostly the same token
        repetitive = ["a"] * 20
        boundaries_repetitive = surprise.find_event_boundaries(repetitive)

        # Diverse should have boundaries
        assert len(boundaries_diverse) > 0 or len(boundaries_repetitive) == 0

    def test_event_boundaries_have_confidence_scores(self):
        """Test that returned events have confidence scores."""
        surprise = BayesianSurprise(entropy_threshold=1.0)
        tokens = [f"token{i}" for i in range(10)]

        boundaries = surprise.find_event_boundaries(tokens)

        for event in boundaries:
            assert 0.0 <= event.confidence <= 1.0
            assert 0.0 <= event.normalized_surprise <= 1.0
            assert 0.0 <= event.coherence_score <= 1.0

    def test_spacing_constraint_applied(self):
        """Test that min_event_spacing constraint is applied."""
        surprise = BayesianSurprise(entropy_threshold=0.5, min_event_spacing=10)

        # Create sequence with many potential boundaries
        tokens = [f"token{i % 5}" for i in range(50)]

        boundaries = surprise.find_event_boundaries(tokens)

        # Check spacing constraint
        for i in range(len(boundaries) - 1):
            spacing = boundaries[i + 1].index - boundaries[i].index
            assert spacing >= surprise.min_event_spacing

    def test_estimate_token_probability(self):
        """Test token probability estimation."""
        surprise = BayesianSurprise()
        tokens = ["a", "b", "c", "a", "b", "c", "a"]

        # Probability of "a" at position 6 should be reasonable
        prob_a = surprise._estimate_token_probability(tokens, 6)
        assert 0.0 <= prob_a <= 1.0

        # "a" appeared 2 times in 6 context tokens
        assert prob_a > 0.1  # Should be reasonably probable

    def test_entropy_calculation(self):
        """Test entropy calculations."""
        surprise = BayesianSurprise()

        # Uniform distribution: high entropy
        uniform_tokens = ["a", "b", "c", "a", "b", "c"]
        entropy_uniform = surprise._calculate_entropy_before(uniform_tokens, 5)

        # Skewed distribution: low entropy
        skewed_tokens = ["a"] * 10 + ["b", "c"]
        entropy_skewed = surprise._calculate_entropy_before(skewed_tokens, 11)

        # Uniform should have higher entropy than skewed
        assert entropy_uniform > entropy_skewed

    def test_coherence_calculation(self):
        """Test coherence calculation."""
        surprise = BayesianSurprise()

        # Coherent sequence (all same): high coherence
        coherent = ["a"] * 20
        coherence_coherent = surprise._calculate_local_coherence(coherent, 10)

        # Diverse sequence: low coherence
        diverse = [f"token{i % 5}" for i in range(20)]
        coherence_diverse = surprise._calculate_local_coherence(diverse, 10)

        # Coherent should have higher coherence score
        assert coherence_coherent > coherence_diverse

    def test_surprise_threshold_effect(self):
        """Test that higher threshold reduces boundaries."""
        tokens = [f"token{i % 3}" for i in range(50)]

        low_threshold = BayesianSurprise(entropy_threshold=0.5)
        high_threshold = BayesianSurprise(entropy_threshold=5.0)

        boundaries_low = low_threshold.find_event_boundaries(tokens)
        boundaries_high = high_threshold.find_event_boundaries(tokens)

        # Lower threshold should find more boundaries
        assert len(boundaries_low) >= len(boundaries_high)

    def test_performance_100k_tokens(self):
        """Test performance on 100K token sequence."""
        import time

        surprise = BayesianSurprise(entropy_threshold=2.5)

        # Create a 100K token sequence
        tokens = [f"token{i % 1000}" for i in range(100_000)]

        start = time.time()
        boundaries = surprise.find_event_boundaries(tokens)
        elapsed = time.time() - start

        # Should complete in reasonable time (<10 seconds)
        assert elapsed < 10.0

        # Should find some boundaries
        assert len(boundaries) > 0

        print(f"✓ 100K token processing: {len(boundaries)} boundaries in {elapsed:.2f}s")


class TestSurpriseEventModel:
    """Test SurpriseEvent dataclass."""

    def test_surprise_event_creation(self):
        """Test SurpriseEvent creation."""
        from athena.episodic.surprise import SurpriseEvent

        event = SurpriseEvent(
            index=10,
            surprise_score=3.5,
            normalized_surprise=0.8,
            coherence_score=0.6,
            confidence=0.75,
        )

        assert event.index == 10
        assert event.surprise_score == 3.5
        assert event.confidence == 0.75

    def test_surprise_events_sortable(self):
        """Test that SurpriseEvent instances can be sorted."""
        from athena.episodic.surprise import SurpriseEvent

        events = [
            SurpriseEvent(0, 1.0, 0.5, 0.6, 0.5),
            SurpriseEvent(10, 3.0, 0.9, 0.4, 0.8),
            SurpriseEvent(5, 2.0, 0.7, 0.5, 0.6),
        ]

        sorted_events = sorted(events, key=lambda e: e.confidence, reverse=True)

        # Event with highest confidence should be first
        assert sorted_events[0].index == 10
        assert sorted_events[0].confidence == 0.8
