"""Tests for Bayesian surprise event detection."""

import pytest
import numpy as np
from athena.episodic.surprise import BayesianSurprise, SurpriseEvent


class TestSurpriseEvent:
    """Test SurpriseEvent data class."""

    def test_surprise_event_creation(self):
        """Test creating SurpriseEvent."""
        event = SurpriseEvent(
            index=100,
            surprise_score=2.5,
            normalized_surprise=0.75,
            coherence_score=0.8,
            confidence=0.95,
        )
        assert event.index == 100
        assert event.surprise_score == 2.5
        assert event.normalized_surprise == 0.75
        assert event.coherence_score == 0.8
        assert event.confidence == 0.95


class TestBayesianSurprise:
    """Test Bayesian surprise calculation."""

    @pytest.fixture
    def surprise_calc(self):
        """Create BayesianSurprise calculator."""
        return BayesianSurprise(
            entropy_threshold=2.5,
            min_event_spacing=50,
            coherence_weight=0.3,
        )

    def test_surprise_initialization(self, surprise_calc):
        """Test BayesianSurprise initialization."""
        assert surprise_calc.entropy_threshold == 2.5
        assert surprise_calc.min_event_spacing == 50
        assert surprise_calc.coherence_weight == 0.3

    def test_surprise_with_custom_parameters(self):
        """Test BayesianSurprise with custom parameters."""
        surprise_calc = BayesianSurprise(
            entropy_threshold=3.0,
            min_event_spacing=100,
            coherence_weight=0.5,
        )
        assert surprise_calc.entropy_threshold == 3.0
        assert surprise_calc.min_event_spacing == 100
        assert surprise_calc.coherence_weight == 0.5

    def test_surprise_cache_initialization(self, surprise_calc):
        """Test that surprise calculator has cache."""
        assert hasattr(surprise_calc, "_prob_cache")
        assert isinstance(surprise_calc._prob_cache, dict)

    def test_calculate_surprise_simple_tokens(self, surprise_calc):
        """Test surprise calculation with simple token list."""
        tokens = ["the", "cat", "sat", "on", "the", "mat"]
        surprise = surprise_calc.calculate_surprise(tokens, 3)
        # Should return a float
        assert isinstance(surprise, (int, float))
        # Surprise should be positive
        assert surprise >= 0.0

    def test_calculate_surprise_with_kl_divergence(self, surprise_calc):
        """Test surprise calculation using KL divergence."""
        tokens = ["hello", "world", "hello", "world", "goodbye"]
        # Index where pattern breaks (goodbye is unexpected)
        surprise = surprise_calc.calculate_surprise(
            tokens, 4, use_kl_divergence=True
        )
        assert isinstance(surprise, (int, float))
        assert surprise >= 0.0

    def test_calculate_surprise_different_positions(self, surprise_calc):
        """Test that different positions can have different surprise."""
        tokens = [
            "the",
            "quick",
            "brown",
            "fox",
            "jumps",
            "UNEXPECTEDWORD",
            "lazy",
            "dog",
        ]

        # Normal position
        surprise_normal = surprise_calc.calculate_surprise(tokens, 2)

        # Unexpected position
        surprise_unexpected = surprise_calc.calculate_surprise(tokens, 5)

        # Both should be floats
        assert isinstance(surprise_normal, (int, float))
        assert isinstance(surprise_unexpected, (int, float))

    def test_calculate_surprise_with_context_probs(self, surprise_calc):
        """Test surprise calculation with provided context probabilities."""
        tokens = ["a", "b", "c", "d"]
        context_probs = np.array([0.25, 0.25, 0.25, 0.25])

        surprise = surprise_calc.calculate_surprise(
            tokens, 1, context_probs=context_probs
        )
        assert isinstance(surprise, (int, float))

    def test_surprise_empty_tokens_list(self, surprise_calc):
        """Test surprise calculation with empty token list."""
        tokens = []
        surprise = surprise_calc.calculate_surprise(tokens, 0)
        # Should handle gracefully
        assert isinstance(surprise, (int, float))

    def test_surprise_single_token(self, surprise_calc):
        """Test surprise calculation with single token."""
        tokens = ["hello"]
        surprise = surprise_calc.calculate_surprise(tokens, 0)
        assert isinstance(surprise, (int, float))

    def test_surprise_repeated_tokens(self, surprise_calc):
        """Test surprise with highly repetitive text."""
        # Very repetitive - low surprise expected
        tokens = ["same"] * 20
        surprise = surprise_calc.calculate_surprise(tokens, 10)
        assert isinstance(surprise, (int, float))
        assert surprise >= 0.0

    def test_surprise_probability_cache(self, surprise_calc):
        """Test that probability cache is used."""
        tokens = ["test", "token", "list"]

        # First call
        surprise1 = surprise_calc.calculate_surprise(tokens, 1)

        # Second call should use cache
        surprise2 = surprise_calc.calculate_surprise(tokens, 1)

        # Should get same result (cache hit)
        assert surprise1 == surprise2

    def test_surprise_with_none_context_probs(self, surprise_calc):
        """Test surprise calculation with None context."""
        tokens = ["a", "b", "c"]
        surprise = surprise_calc.calculate_surprise(tokens, 1, context_probs=None)
        assert isinstance(surprise, (int, float))

    def test_surprise_kl_divergence_flag(self, surprise_calc):
        """Test KL divergence flag effects."""
        tokens = ["a", "b", "c", "d", "e"]

        # With KL divergence
        surprise_kl = surprise_calc.calculate_surprise(
            tokens, 2, use_kl_divergence=True
        )

        # Without KL divergence
        surprise_no_kl = surprise_calc.calculate_surprise(
            tokens, 2, use_kl_divergence=False
        )

        # Both should be valid floats
        assert isinstance(surprise_kl, (int, float))
        assert isinstance(surprise_no_kl, (int, float))

    def test_surprise_long_sequence(self, surprise_calc):
        """Test surprise with longer token sequence."""
        # Simulate a 1000-token document
        tokens = [f"token_{i}" for i in range(1000)]

        # Test various positions
        for pos in [100, 500, 999]:
            surprise = surprise_calc.calculate_surprise(tokens, pos)
            assert isinstance(surprise, (int, float))
            assert surprise >= 0.0

    def test_surprise_index_boundaries(self, surprise_calc):
        """Test surprise calculation at sequence boundaries."""
        tokens = ["a", "b", "c"]

        # First position
        surprise_first = surprise_calc.calculate_surprise(tokens, 0)
        assert isinstance(surprise_first, (int, float))

        # Middle position
        surprise_middle = surprise_calc.calculate_surprise(tokens, 1)
        assert isinstance(surprise_middle, (int, float))

        # Last position
        surprise_last = surprise_calc.calculate_surprise(tokens, 2)
        assert isinstance(surprise_last, (int, float))
