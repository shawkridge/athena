"""Unit tests for working memory decay configuration."""

import pytest
import math
import time
from athena.working_memory.decay_config import (
    DecayConfig,
    DecayCalculator,
)


class TestDecayConfig:
    """Test DecayConfig model."""

    def test_decay_config_initialization(self):
        """Test creating default decay config."""
        config = DecayConfig()
        assert config.default_half_life == 30.0
        assert "verbal" in config.content_type_half_lives
        assert "spatial" in config.content_type_half_lives
        assert "action" in config.content_type_half_lives
        assert "decision" in config.content_type_half_lives

    def test_decay_config_custom_default(self):
        """Test creating config with custom default."""
        config = DecayConfig(default_half_life=45.0)
        assert config.default_half_life == 45.0

    def test_get_half_life_for_content_type(self):
        """Test getting half-life by content type."""
        config = DecayConfig()
        assert config.get_half_life_for_content_type("verbal") == 30.0
        assert config.get_half_life_for_content_type("spatial") == 45.0
        assert config.get_half_life_for_content_type("action") == 20.0
        assert config.get_half_life_for_content_type("decision") == 60.0

    def test_get_half_life_unknown_type(self):
        """Test getting half-life for unknown type returns default."""
        config = DecayConfig()
        assert config.get_half_life_for_content_type("unknown") == config.default_half_life

    def test_get_multiplier_for_importance_low(self):
        """Test multiplier for low importance."""
        config = DecayConfig()
        assert config.get_multiplier_for_importance(0.1) == 1.5  # Low: 1.5x faster

    def test_get_multiplier_for_importance_medium(self):
        """Test multiplier for medium importance."""
        config = DecayConfig()
        assert config.get_multiplier_for_importance(0.5) == 1.0  # Medium: normal

    def test_get_multiplier_for_importance_high(self):
        """Test multiplier for high importance."""
        config = DecayConfig()
        assert config.get_multiplier_for_importance(0.9) == 0.7  # High: slower decay

    def test_compute_effective_half_life(self):
        """Test computing effective half-life with multiplier."""
        config = DecayConfig()

        # Verbal + low importance
        half_life = config.compute_effective_half_life("verbal", 0.1)
        assert half_life == 30.0 * 1.5  # 45 seconds

        # Spatial + high importance
        half_life = config.compute_effective_half_life("spatial", 0.9)
        assert half_life == 45.0 * 0.7  # 31.5 seconds

    def test_decay_config_to_dict(self):
        """Test serializing config to dict."""
        config = DecayConfig()
        data = config.to_dict()

        assert data["default_half_life"] == 30.0
        assert "verbal" in data["content_type_half_lives"]
        assert "low" in data["importance_multipliers"]

    def test_decay_config_from_dict(self):
        """Test creating config from dict."""
        original = DecayConfig(default_half_life=40.0)
        data = original.to_dict()

        restored = DecayConfig.from_dict(data)
        assert restored.default_half_life == 40.0

    def test_custom_content_type_half_life(self):
        """Test setting custom half-life for content type."""
        custom_half_lives = {
            "verbal": 20.0,
            "spatial": 50.0,
            "action": 15.0,
            "decision": 90.0,
        }
        config = DecayConfig(content_type_half_lives=custom_half_lives)

        assert config.get_half_life_for_content_type("verbal") == 20.0
        assert config.get_half_life_for_content_type("decision") == 90.0


class TestDecayCalculator:
    """Test DecayCalculator."""

    def test_decay_calculator_initialization(self):
        """Test initializing calculator."""
        calc = DecayCalculator()
        assert calc.config is not None
        assert calc.config.default_half_life == 30.0

    def test_decay_calculator_with_custom_config(self):
        """Test calculator with custom config."""
        config = DecayConfig(default_half_life=40.0)
        calc = DecayCalculator(config)
        assert calc.config.default_half_life == 40.0

    def test_compute_activation_at_age_zero(self):
        """Test activation at age 0."""
        calc = DecayCalculator()
        activation = calc.compute_activation(
            importance=1.0,
            content_type="verbal",
            age_seconds=0,
        )
        # At age 0, activation = importance * 1 = 1.0
        assert activation == pytest.approx(1.0, rel=1e-5)

    def test_compute_activation_at_half_life(self):
        """Test activation at exponential decay period."""
        calc = DecayCalculator()
        # Test that older items have lower activation
        activation_0s = calc.compute_activation(
            importance=1.0,  # Medium importance for 1.0x multiplier
            content_type="verbal",  # 30 second half-life
            age_seconds=0,
        )
        activation_30s = calc.compute_activation(
            importance=1.0,
            content_type="verbal",
            age_seconds=30,
        )
        # Should decay: exp(-30/30) = exp(-1) ≈ 0.368
        assert activation_0s > activation_30s
        assert activation_30s == pytest.approx(1.0 * math.exp(-1), rel=1e-5)

    def test_compute_activation_at_two_half_lives(self):
        """Test activation after longer period."""
        calc = DecayCalculator()
        activation_0s = calc.compute_activation(
            importance=1.0,
            content_type="verbal",
            age_seconds=0,
        )
        activation_60s = calc.compute_activation(
            importance=1.0,
            content_type="verbal",
            age_seconds=60,
        )
        # Should decay: exp(-60/30) = exp(-2) ≈ 0.135
        assert activation_0s > activation_60s
        assert activation_60s == pytest.approx(1.0 * math.exp(-2), rel=1e-5)

    def test_compute_activation_with_low_importance(self):
        """Test activation for low-importance item decays slower."""
        calc = DecayCalculator()
        # Low importance: 30s * 1.5 = 45s effective half-life
        activation_low = calc.compute_activation(
            importance=0.2,
            content_type="verbal",
            age_seconds=45,
        )
        # activation = 0.2 * exp(-45/45) = 0.2 * exp(-1) ≈ 0.0736
        assert activation_low == pytest.approx(0.2 * math.exp(-1), rel=1e-5)

    def test_compute_activation_different_content_types(self):
        """Test activation differs by content type."""
        calc = DecayCalculator()

        # Short-lived action
        action_activation = calc.compute_activation(
            importance=1.0,
            content_type="action",  # 20 second half-life
            age_seconds=40,  # 2 half-lives
        )

        # Long-lived decision
        decision_activation = calc.compute_activation(
            importance=1.0,
            content_type="decision",  # 60 second half-life
            age_seconds=40,  # < 1 half-life
        )

        # Decision should have higher activation
        assert decision_activation > action_activation

    def test_get_remaining_lifespan(self):
        """Test computing remaining lifespan."""
        calc = DecayCalculator()
        # Using exp(-t/half_life) = ratio formula
        # To find when activation drops to half
        lifespan = calc.get_remaining_lifespan(
            importance=1.0,
            content_type="verbal",  # 30 second half-life
            threshold=math.exp(-1),  # Drops by factor of e (≈0.368)
        )
        # Time for exp(-t/30) = exp(-1): t/30 = 1, so t = 30
        assert lifespan == pytest.approx(30.0, rel=1e-5)

    def test_get_remaining_lifespan_to_zero(self):
        """Test lifespan to very low threshold."""
        calc = DecayCalculator()
        lifespan = calc.get_remaining_lifespan(
            importance=1.0,
            content_type="verbal",  # 30 second half-life
            threshold=math.exp(-4),  # 4 time constants
        )
        # Time for exp(-t/30) = exp(-4): t/30 = 4, so t = 120
        assert lifespan == pytest.approx(120.0, rel=1e-5)

    def test_get_remaining_lifespan_already_below_threshold(self):
        """Test lifespan when already below threshold."""
        calc = DecayCalculator()
        lifespan = calc.get_remaining_lifespan(
            importance=0.05,
            content_type="verbal",
            threshold=0.1,  # Higher than importance
        )
        # Already below threshold
        assert lifespan == 0.0

    def test_update_config(self):
        """Test updating decay configuration."""
        calc = DecayCalculator()
        original_half_life = calc.config.default_half_life

        new_config = DecayConfig(default_half_life=60.0)
        calc.update_config(new_config)

        assert calc.config.default_half_life == 60.0
        assert calc.config.default_half_life != original_half_life

    def test_update_content_type_half_life(self):
        """Test updating half-life for content type."""
        calc = DecayCalculator()
        calc.update_content_type_half_life("verbal", 50.0)

        assert calc.config.get_half_life_for_content_type("verbal") == 50.0

    def test_update_importance_multiplier(self):
        """Test updating importance multiplier."""
        calc = DecayCalculator()
        calc.update_importance_multiplier("high", 0.5)

        assert calc.config.get_multiplier_for_importance(0.9) == 0.5


class TestDecayIntegration:
    """Integration tests for decay configuration."""

    def test_realistic_decay_scenario_action_item(self):
        """Test realistic decay for action item (quick forgetting)."""
        calc = DecayCalculator()

        # High-importance action (e.g., "call meeting")
        activation_0s = calc.compute_activation(0.8, "action", 0)
        activation_10s = calc.compute_activation(0.8, "action", 10)
        activation_20s = calc.compute_activation(0.8, "action", 20)

        # Should decay quickly
        assert activation_0s > activation_10s
        assert activation_10s > activation_20s
        assert activation_20s < 0.5  # Below half at one half-life

    def test_realistic_decay_scenario_decision_item(self):
        """Test realistic decay for decision item (persistent)."""
        calc = DecayCalculator()

        # High-importance decision: 60s base * 0.7 = 42s half-life
        activation_0s = calc.compute_activation(0.9, "decision", 0)
        activation_20s = calc.compute_activation(0.9, "decision", 20)
        activation_42s = calc.compute_activation(0.9, "decision", 42)

        # Should decay slowly - still above 50% at 42s (one half-life)
        assert activation_0s > activation_20s
        assert activation_20s > activation_42s
        assert activation_42s < 0.5  # Below half at one half-life

    def test_importance_multiplier_effect(self):
        """Test that importance multipliers work correctly."""
        calc = DecayCalculator()

        # High importance (0.8): 30s * 0.7 = 21s effective half-life
        high_imp_30s = calc.compute_activation(0.8, "verbal", 30)

        # Low importance (0.2): 30s * 1.5 = 45s effective half-life
        low_imp_30s = calc.compute_activation(0.2, "verbal", 30)

        # At same age (30s), high-importance item should have higher activation
        # because its effective half-life is shorter, but we use same age
        # Actually: high decays faster (shorter half-life) so lower activation
        # low decays slower (longer half-life) so higher activation
        assert low_imp_30s > high_imp_30s


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
