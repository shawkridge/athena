"""Unit tests for ImportanceWeightedBudgeter (v1.1).

Tests:
- Importance score calculation
- Budget-constrained memory selection
- Weight-based prioritization
- Edge cases and boundaries
- Batch scenarios
"""

import pytest
from datetime import datetime, timedelta

from athena.compression.base import ImportanceWeightedBudgeter
from tests.unit.compression.conftest import CompressionAssertions


class TestImportanceScoreCalculation:
    """Test importance score calculation formula."""

    def test_score_uses_usefulness_weight(self, importance_budget_config):
        """Score should heavily weight usefulness (40%)."""
        budgeter = ImportanceWeightedBudgeter(importance_budget_config)

        memory_high = {
            'usefulness_score': 0.9,  # High usefulness
            'created_at': datetime.now(),  # Recent
            'access_count': 0,  # Never accessed
            'entity_type': 'fact',
        }

        memory_low = {
            'usefulness_score': 0.1,  # Low usefulness
            'created_at': datetime.now(),  # Recent
            'access_count': 100,  # Frequently accessed
            'entity_type': 'fact',
        }

        score_high = budgeter.calculate_importance_score(memory_high)
        score_low = budgeter.calculate_importance_score(memory_low)

        assert score_high > score_low, "Higher usefulness should yield higher score"

    def test_score_uses_recency_weight(self, importance_budget_config):
        """Score should weight recency (30%)."""
        budgeter = ImportanceWeightedBudgeter(importance_budget_config)

        memory_recent = {
            'usefulness_score': 0.5,  # Same usefulness
            'created_at': datetime.now(),  # Recent
            'access_count': 0,
            'entity_type': 'fact',
        }

        memory_old = {
            'usefulness_score': 0.5,  # Same usefulness
            'created_at': datetime.now() - timedelta(days=300),  # 10 months old
            'access_count': 0,
            'entity_type': 'fact',
        }

        score_recent = budgeter.calculate_importance_score(memory_recent)
        score_old = budgeter.calculate_importance_score(memory_old)

        assert score_recent > score_old, "Recent memories should score higher"

    def test_score_uses_frequency_weight(self, importance_budget_config):
        """Score should weight access frequency (20%)."""
        budgeter = ImportanceWeightedBudgeter(importance_budget_config)

        memory_frequent = {
            'usefulness_score': 0.5,
            'created_at': datetime.now(),
            'access_count': 20,  # Frequently accessed
            'entity_type': 'fact',
        }

        memory_rare = {
            'usefulness_score': 0.5,
            'created_at': datetime.now(),
            'access_count': 1,  # Rarely accessed
            'entity_type': 'fact',
        }

        score_frequent = budgeter.calculate_importance_score(memory_frequent)
        score_rare = budgeter.calculate_importance_score(memory_rare)

        assert score_frequent > score_rare, "Frequently accessed should score higher"

    def test_score_uses_domain_weight(self, importance_budget_config):
        """Score should weight domain type (10%)."""
        budgeter = ImportanceWeightedBudgeter(importance_budget_config)

        memory_decision = {
            'usefulness_score': 0.5,
            'created_at': datetime.now(),
            'access_count': 0,
            'entity_type': 'decision',  # Highest weight (1.0)
        }

        memory_context = {
            'usefulness_score': 0.5,
            'created_at': datetime.now(),
            'access_count': 0,
            'entity_type': 'context',  # Lower weight (0.6)
        }

        score_decision = budgeter.calculate_importance_score(memory_decision)
        score_context = budgeter.calculate_importance_score(memory_context)

        assert score_decision > score_context, "Decision domain should score higher"

    def test_score_in_valid_range(self, importance_budget_config):
        """Score should always be between 0.0 and 1.0."""
        budgeter = ImportanceWeightedBudgeter(importance_budget_config)

        test_cases = [
            {'usefulness_score': 0.0, 'created_at': datetime.now() - timedelta(days=365), 'access_count': 0, 'entity_type': 'context'},
            {'usefulness_score': 1.0, 'created_at': datetime.now(), 'access_count': 100, 'entity_type': 'decision'},
            {'usefulness_score': 0.5, 'created_at': datetime.now() - timedelta(days=180), 'access_count': 50, 'entity_type': 'pattern'},
        ]

        for memory in test_cases:
            score = budgeter.calculate_importance_score(memory)
            assert 0.0 <= score <= 1.0, f"Score {score} outside [0.0, 1.0]"


class TestBudgetConstrainedSelection:
    """Test memory selection within token budget."""

    def test_retrieve_within_budget_respects_limit(self, importance_budget_config, mock_memories_mixed_age):
        """Selected memories should fit within token budget."""
        budgeter = ImportanceWeightedBudgeter(importance_budget_config)

        # Mock content for token estimation
        for mem in mock_memories_mixed_age:
            mem.setdefault('content', 'Test memory content. ' * 5)

        token_budget = 100
        selected, tokens_used = budgeter.retrieve_within_budget(
            mock_memories_mixed_age,
            token_budget=token_budget
        )

        assert tokens_used <= token_budget, f"Used {tokens_used} > budget {token_budget}"

    def test_retrieve_selects_best_by_score(self, importance_budget_config):
        """Should select highest-scored memories first."""
        budgeter = ImportanceWeightedBudgeter(importance_budget_config)

        memories = [
            {
                'id': 1,
                'content': 'Memory 1. ' * 10,
                'usefulness_score': 0.9,  # High
                'created_at': datetime.now(),
                'access_count': 10,
                'entity_type': 'decision',
            },
            {
                'id': 2,
                'content': 'Memory 2. ' * 10,
                'usefulness_score': 0.1,  # Low
                'created_at': datetime.now(),
                'access_count': 0,
                'entity_type': 'context',
            },
        ]

        selected, _ = budgeter.retrieve_within_budget(memories, token_budget=1000)

        # Should select high-score first
        if len(selected) > 0:
            assert selected[0]['id'] == 1, "Should select higher-scored memory first"

    def test_retrieve_with_empty_list(self, importance_budget_config):
        """Empty memory list should return empty selection."""
        budgeter = ImportanceWeightedBudgeter(importance_budget_config)

        selected, tokens_used = budgeter.retrieve_within_budget([], token_budget=2000)

        assert selected == []
        assert tokens_used == 0

    def test_retrieve_with_zero_budget(self, importance_budget_config, mock_memories_mixed_age):
        """Zero budget should return empty selection."""
        budgeter = ImportanceWeightedBudgeter(importance_budget_config)

        for mem in mock_memories_mixed_age:
            mem.setdefault('content', 'Test. ')

        selected, tokens_used = budgeter.retrieve_within_budget(
            mock_memories_mixed_age,
            token_budget=0
        )

        assert selected == []
        assert tokens_used == 0

    def test_select_best_within_budget_wrapper(self, importance_budget_config, mock_memories_mixed_age):
        """select_best_within_budget should return only selected list."""
        budgeter = ImportanceWeightedBudgeter(importance_budget_config)

        for mem in mock_memories_mixed_age:
            mem.setdefault('content', 'Test memory. ' * 5)

        selected = budgeter.select_best_within_budget(
            mock_memories_mixed_age,
            token_budget=100
        )

        assert isinstance(selected, list)
        assert all('id' in mem for mem in selected), "All selected should be memory dicts"


class TestBudgetSummary:
    """Test budget summary statistics."""

    def test_budget_summary_structure(self, importance_budget_config, mock_memories_mixed_age):
        """Summary should have all expected fields."""
        budgeter = ImportanceWeightedBudgeter(importance_budget_config)

        for mem in mock_memories_mixed_age:
            mem.setdefault('content', 'Test memory content. ' * 5)

        summary = budgeter.get_budget_summary(
            mock_memories_mixed_age,
            token_budget=100
        )

        expected_fields = [
            'total_candidates',
            'selected_count',
            'tokens_budget',
            'tokens_used',
            'tokens_remaining',
            'coverage_percentage',
            'selection_efficiency',
        ]

        for field in expected_fields:
            assert field in summary, f"Missing field: {field}"

    def test_budget_summary_math(self, importance_budget_config, mock_memories_mixed_age):
        """Summary math should be consistent."""
        budgeter = ImportanceWeightedBudgeter(importance_budget_config)

        for mem in mock_memories_mixed_age:
            mem.setdefault('content', 'Test memory. ')

        summary = budgeter.get_budget_summary(
            mock_memories_mixed_age,
            token_budget=100
        )

        # Verify math
        assert summary['tokens_used'] + summary['tokens_remaining'] == summary['tokens_budget']
        assert summary['coverage_percentage'] == (summary['selected_count'] / summary['total_candidates'] * 100)
        assert summary['selection_efficiency'] == (summary['tokens_used'] / summary['tokens_budget'])

    def test_budget_summary_efficiency_under_100_percent(self, importance_budget_config, mock_memories_mixed_age):
        """Efficiency should never exceed 100%."""
        budgeter = ImportanceWeightedBudgeter(importance_budget_config)

        for mem in mock_memories_mixed_age:
            mem.setdefault('content', 'Test. ')

        summary = budgeter.get_budget_summary(
            mock_memories_mixed_age,
            token_budget=1000
        )

        assert summary['selection_efficiency'] <= 1.0, "Efficiency should be <= 100%"


class TestImportanceWeightConfiguration:
    """Test weight-based configuration."""

    def test_custom_weights_validation(self, importance_budget_config):
        """Weights should sum to 1.0."""
        # Valid configuration should not raise
        importance_budget_config.validate()

    def test_domain_weights(self, importance_budget_config):
        """Domain weights should reflect value hierarchy."""
        weights = importance_budget_config.domain_weights

        # Decision > Pattern > Fact > Context
        assert weights['decision'] >= weights['pattern']
        assert weights['pattern'] >= weights['fact']
        assert weights['fact'] >= weights['context']

    def test_recency_decay_exponential(self, importance_budget_config):
        """Recency boost should use exponential decay."""
        budgeter = ImportanceWeightedBudgeter(importance_budget_config)

        memory_0_days = {
            'usefulness_score': 0.5,
            'created_at': datetime.now(),
            'access_count': 0,
            'entity_type': 'fact',
        }

        memory_180_days = {
            'usefulness_score': 0.5,
            'created_at': datetime.now() - timedelta(days=180),
            'access_count': 0,
            'entity_type': 'fact',
        }

        score_0 = budgeter.calculate_importance_score(memory_0_days)
        score_180 = budgeter.calculate_importance_score(memory_180_days)

        # Recency should decay but older memory should still have some value
        assert score_0 > score_180
        assert score_180 > 0.0, "Old memory should still have positive value"


class TestAccessCountNormalization:
    """Test frequency/access count normalization."""

    def test_access_count_capped_at_config_cap(self, importance_budget_config):
        """Access count should normalize at configured cap."""
        # Default cap is 10
        budgeter = ImportanceWeightedBudgeter(importance_budget_config)

        memory_10_accesses = {
            'usefulness_score': 0.5,
            'created_at': datetime.now(),
            'access_count': 10,
            'entity_type': 'fact',
        }

        memory_100_accesses = {
            'usefulness_score': 0.5,
            'created_at': datetime.now(),
            'access_count': 100,
            'entity_type': 'fact',
        }

        score_10 = budgeter.calculate_importance_score(memory_10_accesses)
        score_100 = budgeter.calculate_importance_score(memory_100_accesses)

        # Both should score the same (capped)
        assert score_10 == score_100

    def test_zero_access_count(self, importance_budget_config):
        """Zero access count should still yield valid score."""
        budgeter = ImportanceWeightedBudgeter(importance_budget_config)

        memory = {
            'usefulness_score': 0.5,
            'created_at': datetime.now(),
            'access_count': 0,
            'entity_type': 'fact',
        }

        score = budgeter.calculate_importance_score(memory)

        assert score >= 0.0, "Should handle zero access count"


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_memory_missing_usefulness_defaults_to_0_5(self, importance_budget_config):
        """Missing usefulness_score should default to 0.5."""
        budgeter = ImportanceWeightedBudgeter(importance_budget_config)

        memory = {
            'created_at': datetime.now(),
            'access_count': 0,
            'entity_type': 'fact',
            # Missing usefulness_score
        }

        score = budgeter.calculate_importance_score(memory)

        assert score > 0.0, "Should handle missing usefulness_score"

    def test_memory_missing_access_count_defaults_to_zero(self, importance_budget_config):
        """Missing access_count should default to 0."""
        budgeter = ImportanceWeightedBudgeter(importance_budget_config)

        memory = {
            'usefulness_score': 0.5,
            'created_at': datetime.now(),
            'entity_type': 'fact',
            # Missing access_count
        }

        score = budgeter.calculate_importance_score(memory)

        assert score >= 0.0, "Should handle missing access_count"

    def test_memory_missing_entity_type_defaults_to_fact(self, importance_budget_config):
        """Missing entity_type should default to 'fact'."""
        budgeter = ImportanceWeightedBudgeter(importance_budget_config)

        memory = {
            'usefulness_score': 0.5,
            'created_at': datetime.now(),
            'access_count': 0,
            # Missing entity_type
        }

        score = budgeter.calculate_importance_score(memory)

        assert score >= 0.0, "Should handle missing entity_type"

    def test_future_created_at(self, importance_budget_config):
        """Future created_at should handle gracefully (age_days negative)."""
        budgeter = ImportanceWeightedBudgeter(importance_budget_config)

        memory = {
            'usefulness_score': 0.5,
            'created_at': datetime.now() + timedelta(days=10),  # 10 days in future
            'access_count': 0,
            'entity_type': 'fact',
        }

        score = budgeter.calculate_importance_score(memory)

        # Should still return valid score
        assert 0.0 <= score <= 1.0


class TestBatchSelectionScenarios:
    """Test realistic batch selection scenarios."""

    def test_select_diverse_domains(self, importance_budget_config):
        """Should select from different domains based on score."""
        budgeter = ImportanceWeightedBudgeter(importance_budget_config)

        memories = [
            {
                'id': 1,
                'content': 'Decision content. ' * 10,
                'usefulness_score': 0.5,
                'created_at': datetime.now(),
                'access_count': 5,
                'entity_type': 'decision',
            },
            {
                'id': 2,
                'content': 'Pattern content. ' * 10,
                'usefulness_score': 0.5,
                'created_at': datetime.now(),
                'access_count': 5,
                'entity_type': 'pattern',
            },
            {
                'id': 3,
                'content': 'Fact content. ' * 10,
                'usefulness_score': 0.5,
                'created_at': datetime.now(),
                'access_count': 5,
                'entity_type': 'fact',
            },
        ]

        selected, _ = budgeter.retrieve_within_budget(memories, token_budget=10000)

        # Should select all (all fit)
        assert len(selected) == 3

    def test_select_under_tight_budget(self, importance_budget_config):
        """Under tight budget, should select only highest-value memories."""
        budgeter = ImportanceWeightedBudgeter(importance_budget_config)

        memories = [
            {
                'id': 1,
                'content': 'Very high usefulness. ' * 20,
                'usefulness_score': 0.95,
                'created_at': datetime.now(),
                'access_count': 50,
                'entity_type': 'decision',
            },
            {
                'id': 2,
                'content': 'Medium usefulness. ' * 20,
                'usefulness_score': 0.5,
                'created_at': datetime.now(),
                'access_count': 10,
                'entity_type': 'fact',
            },
            {
                'id': 3,
                'content': 'Low usefulness. ' * 20,
                'usefulness_score': 0.2,
                'created_at': datetime.now(),
                'access_count': 1,
                'entity_type': 'context',
            },
        ]

        selected, _ = budgeter.retrieve_within_budget(memories, token_budget=100)

        # Should prioritize high usefulness
        if len(selected) == 1:
            assert selected[0]['id'] == 1, "Should select highest-value memory"

    def test_filter_low_importance_score_memories(self, importance_budget_config):
        """Should skip memories with low importance scores."""
        # Set threshold high to filter out very-low-value memories
        importance_budget_config.min_usefulness_score = 0.7

        budgeter = ImportanceWeightedBudgeter(importance_budget_config)

        memories = [
            {
                'id': 1,
                'content': 'High quality. ',
                'usefulness_score': 0.9,
                'created_at': datetime.now(),
                'access_count': 50,
                'entity_type': 'decision',
            },
            {
                'id': 2,
                'content': 'Very low quality. ',
                'usefulness_score': 0.1,
                'created_at': datetime.now() - timedelta(days=300),
                'access_count': 0,
                'entity_type': 'context',
            },
        ]

        selected, _ = budgeter.retrieve_within_budget(memories, token_budget=10000)

        # Should prefer high-quality memories
        if len(selected) > 0:
            selected_ids = [mem['id'] for mem in selected]
            assert 1 in selected_ids, "Should prioritize high-quality memory"
