"""Unit tests for ImportanceWeightedBudgeter (v1.1).

Tests:
- Importance score calculation (usefulness, recency, frequency, domain)
- Budget-constrained memory selection
- Best memory selection within token budget
- Budget summary statistics
- Edge cases and batch scenarios
"""

import pytest
from datetime import datetime, timedelta

from athena.compression.base import ImportanceWeightedBudgeter
from athena.compression.models import ImportanceWeightedBudgetConfig
from tests.unit.compression.conftest import CompressionAssertions


class TestImportanceScoreCalculation:
    """Test importance score calculation with different weightings."""

    def test_high_usefulness_high_score(self, importance_budget_config):
        """High usefulness should result in high importance score."""
        budgeter = ImportanceWeightedBudgeter(importance_budget_config)

        memory = {
            'id': 1,
            'content': 'Test memory',
            'usefulness_score': 0.95,  # Very useful
            'access_count': 0,  # Never accessed
            'entity_type': 'fact',
            'created_at': datetime.now(),  # Very recent
        }

        score = budgeter.calculate_importance_score(memory)
        assert score > 0.7, "High usefulness should yield high score"

    def test_low_usefulness_low_score(self, importance_budget_config):
        """Low usefulness should result in lower score than high usefulness."""
        budgeter = ImportanceWeightedBudgeter(importance_budget_config)

        low_usefulness = {
            'id': 1,
            'content': 'Test memory',
            'usefulness_score': 0.1,  # Low usefulness
            'access_count': 10,  # Frequently accessed
            'entity_type': 'decision',  # High domain weight
            'created_at': datetime.now(),  # Very recent
        }

        high_usefulness = {
            'id': 2,
            'content': 'Test memory',
            'usefulness_score': 0.9,  # High usefulness
            'access_count': 10,
            'entity_type': 'decision',
            'created_at': datetime.now(),
        }

        low_score = budgeter.calculate_importance_score(low_usefulness)
        high_score = budgeter.calculate_importance_score(high_usefulness)

        assert low_score < high_score, "Low usefulness should yield lower score"

    def test_recency_boost_recent_memory(self, importance_budget_config):
        """Recent memory should get recency boost."""
        budgeter = ImportanceWeightedBudgeter(importance_budget_config)

        recent_memory = {
            'id': 1,
            'content': 'Test memory',
            'usefulness_score': 0.5,
            'access_count': 0,
            'entity_type': 'fact',
            'created_at': datetime.now(),  # Very recent
        }

        old_memory = {
            'id': 2,
            'content': 'Test memory',
            'usefulness_score': 0.5,  # Same usefulness
            'access_count': 0,
            'entity_type': 'fact',
            'created_at': datetime.now() - timedelta(days=365),  # 1 year old
        }

        recent_score = budgeter.calculate_importance_score(recent_memory)
        old_score = budgeter.calculate_importance_score(old_memory)

        assert recent_score > old_score, "Recent memory should score higher"

    def test_frequency_boost_accessed_memory(self, importance_budget_config):
        """Frequently accessed memory should score higher."""
        budgeter = ImportanceWeightedBudgeter(importance_budget_config)

        accessed_memory = {
            'id': 1,
            'content': 'Test memory',
            'usefulness_score': 0.5,
            'access_count': 10,  # Accessed many times
            'entity_type': 'fact',
            'created_at': datetime.now() - timedelta(days=30),
        }

        unaccessed_memory = {
            'id': 2,
            'content': 'Test memory',
            'usefulness_score': 0.5,  # Same usefulness
            'access_count': 0,  # Never accessed
            'entity_type': 'fact',
            'created_at': datetime.now() - timedelta(days=30),
        }

        accessed_score = budgeter.calculate_importance_score(accessed_memory)
        unaccessed_score = budgeter.calculate_importance_score(unaccessed_memory)

        assert accessed_score > unaccessed_score, "Accessed memory should score higher"

    def test_domain_weight_decision_vs_context(self, importance_budget_config):
        """Decision type should score higher than context type."""
        budgeter = ImportanceWeightedBudgeter(importance_budget_config)

        decision_memory = {
            'id': 1,
            'content': 'Test memory',
            'usefulness_score': 0.5,
            'access_count': 0,
            'entity_type': 'decision',  # Highest domain weight
            'created_at': datetime.now() - timedelta(days=30),
        }

        context_memory = {
            'id': 2,
            'content': 'Test memory',
            'usefulness_score': 0.5,  # Same usefulness
            'access_count': 0,
            'entity_type': 'context',  # Lowest domain weight
            'created_at': datetime.now() - timedelta(days=30),
        }

        decision_score = budgeter.calculate_importance_score(decision_memory)
        context_score = budgeter.calculate_importance_score(context_memory)

        assert decision_score > context_score, "Decision should score higher than context"

    def test_score_bounds_zero_to_one(self, importance_budget_config):
        """Importance score should always be between 0.0 and 1.0."""
        budgeter = ImportanceWeightedBudgeter(importance_budget_config)

        test_cases = [
            # (usefulness, access_count, entity_type, created_at)
            (0.0, 0, 'fact', datetime.now() - timedelta(days=365)),
            (1.0, 100, 'decision', datetime.now()),
            (0.5, 5, 'pattern', datetime.now() - timedelta(days=30)),
        ]

        for usefulness, access_count, entity_type, created_at in test_cases:
            memory = {
                'id': 1,
                'content': 'Test memory',
                'usefulness_score': usefulness,
                'access_count': access_count,
                'entity_type': entity_type,
                'created_at': created_at,
            }

            score = budgeter.calculate_importance_score(memory)
            assert 0.0 <= score <= 1.0, f"Score {score} out of bounds"

    def test_access_count_capped(self, importance_budget_config):
        """Access count should be capped at config value (10)."""
        budgeter = ImportanceWeightedBudgeter(importance_budget_config)

        memory_10 = {
            'id': 1,
            'content': 'Test memory',
            'usefulness_score': 0.5,
            'access_count': 10,  # At cap
            'entity_type': 'fact',
            'created_at': datetime.now() - timedelta(days=30),
        }

        memory_100 = {
            'id': 2,
            'content': 'Test memory',
            'usefulness_score': 0.5,
            'access_count': 100,  # Well above cap
            'entity_type': 'fact',
            'created_at': datetime.now() - timedelta(days=30),
        }

        score_10 = budgeter.calculate_importance_score(memory_10)
        score_100 = budgeter.calculate_importance_score(memory_100)

        # Should be same (both capped at 10)
        assert score_10 == score_100, "Scores should be same when both at/above cap"


class TestBudgetConstrainedSelection:
    """Test retrieving memories within token budget."""

    def test_retrieve_within_budget_basic(self, importance_budget_config):
        """Should select memories within token budget."""
        budgeter = ImportanceWeightedBudgeter(importance_budget_config)

        memories = [
            {
                'id': 1,
                'content': 'A' * 400,  # ~100 tokens
                'usefulness_score': 0.9,
                'access_count': 0,
                'entity_type': 'fact',
                'created_at': datetime.now(),
            },
            {
                'id': 2,
                'content': 'B' * 400,  # ~100 tokens
                'usefulness_score': 0.8,
                'access_count': 0,
                'entity_type': 'fact',
                'created_at': datetime.now(),
            },
            {
                'id': 3,
                'content': 'C' * 400,  # ~100 tokens
                'usefulness_score': 0.7,
                'access_count': 0,
                'entity_type': 'fact',
                'created_at': datetime.now(),
            },
        ]

        selected, tokens_used = budgeter.retrieve_within_budget(
            memories,
            token_budget=250  # Can fit ~2.5 memories
        )

        assert len(selected) == 2, "Should select 2 memories"
        assert tokens_used <= 250, "Should respect token budget"

    def test_sorted_by_importance_score(self, importance_budget_config):
        """Selected memories should be sorted by importance score."""
        budgeter = ImportanceWeightedBudgeter(importance_budget_config)

        memories = [
            {
                'id': 1,
                'content': 'A' * 400,  # ~100 tokens
                'usefulness_score': 0.5,  # Low usefulness
                'access_count': 0,
                'entity_type': 'fact',
                'created_at': datetime.now() - timedelta(days=100),
            },
            {
                'id': 2,
                'content': 'B' * 400,  # ~100 tokens
                'usefulness_score': 0.9,  # High usefulness
                'access_count': 10,
                'entity_type': 'decision',
                'created_at': datetime.now(),
            },
            {
                'id': 3,
                'content': 'C' * 400,  # ~100 tokens
                'usefulness_score': 0.7,  # Medium usefulness
                'access_count': 0,
                'entity_type': 'fact',
                'created_at': datetime.now(),
            },
        ]

        selected, _ = budgeter.retrieve_within_budget(
            memories,
            token_budget=300  # Can fit 3 memories
        )

        # Should be sorted by importance
        scores = [budgeter.calculate_importance_score(m) for m in selected]
        assert scores == sorted(scores, reverse=True), "Should be sorted by importance desc"

    def test_empty_memories_list(self, importance_budget_config):
        """Empty memories list should return empty selection."""
        budgeter = ImportanceWeightedBudgeter(importance_budget_config)

        selected, tokens_used = budgeter.retrieve_within_budget([], token_budget=2000)

        assert selected == [], "Should return empty list"
        assert tokens_used == 0, "Should use 0 tokens"

    def test_zero_budget(self, importance_budget_config):
        """Zero budget should return empty selection."""
        budgeter = ImportanceWeightedBudgeter(importance_budget_config)

        memories = [
            {
                'id': 1,
                'content': 'A' * 400,
                'usefulness_score': 0.9,
                'access_count': 0,
                'entity_type': 'fact',
                'created_at': datetime.now(),
            },
        ]

        selected, tokens_used = budgeter.retrieve_within_budget(
            memories,
            token_budget=0
        )

        assert selected == [], "Should return empty list for zero budget"
        assert tokens_used == 0, "Should use 0 tokens"

    def test_low_value_memories_skipped(self, importance_budget_config):
        """Very low-value memories should be skipped."""
        budgeter = ImportanceWeightedBudgeter(importance_budget_config)

        memories = [
            {
                'id': 1,
                'content': 'A' * 400,
                'usefulness_score': 0.2,  # Below min_usefulness_score (0.3)
                'access_count': 0,
                'entity_type': 'fact',
                'created_at': datetime.now() - timedelta(days=200),  # Old
            },
            {
                'id': 2,
                'content': 'B' * 400,
                'usefulness_score': 0.9,  # High
                'access_count': 0,
                'entity_type': 'fact',
                'created_at': datetime.now(),
            },
        ]

        selected, _ = budgeter.retrieve_within_budget(
            memories,
            token_budget=2000
        )

        # Should only include memory 2 (memory 1 is too low value)
        assert len(selected) == 1, "Should skip very low-value memory"
        assert selected[0]['id'] == 2, "Should select high-value memory"


class TestBestMemorySelection:
    """Test convenience method for best memory selection."""

    def test_select_best_within_budget(self, importance_budget_config):
        """select_best_within_budget should return only memories."""
        budgeter = ImportanceWeightedBudgeter(importance_budget_config)

        memories = [
            {
                'id': 1,
                'content': 'A' * 400,
                'usefulness_score': 0.9,
                'access_count': 0,
                'entity_type': 'fact',
                'created_at': datetime.now(),
            },
            {
                'id': 2,
                'content': 'B' * 400,
                'usefulness_score': 0.8,
                'access_count': 0,
                'entity_type': 'fact',
                'created_at': datetime.now(),
            },
        ]

        selected = budgeter.select_best_within_budget(
            memories,
            token_budget=250
        )

        # Should be same as retrieve_within_budget (first element)
        assert isinstance(selected, list), "Should return list"
        assert all(isinstance(m, dict) for m in selected), "Should contain memory dicts"


class TestBudgetSummary:
    """Test budget summary statistics."""

    def test_budget_summary_complete(self, importance_budget_config):
        """Budget summary should contain all required fields."""
        budgeter = ImportanceWeightedBudgeter(importance_budget_config)

        memories = [
            {
                'id': 1,
                'content': 'A' * 400,
                'usefulness_score': 0.9,
                'access_count': 0,
                'entity_type': 'fact',
                'created_at': datetime.now(),
            },
            {
                'id': 2,
                'content': 'B' * 400,
                'usefulness_score': 0.8,
                'access_count': 0,
                'entity_type': 'fact',
                'created_at': datetime.now(),
            },
        ]

        summary = budgeter.get_budget_summary(memories, token_budget=2000)

        # Check all required fields
        required_fields = [
            'total_candidates',
            'selected_count',
            'tokens_budget',
            'tokens_used',
            'tokens_remaining',
            'coverage_percentage',
            'selection_efficiency',
        ]

        for field in required_fields:
            assert field in summary, f"Missing field: {field}"

    def test_budget_summary_calculations(self, importance_budget_config):
        """Budget summary calculations should be correct."""
        budgeter = ImportanceWeightedBudgeter(importance_budget_config)

        memories = [
            {
                'id': 1,
                'content': 'A' * 400,  # ~100 tokens
                'usefulness_score': 0.9,
                'access_count': 0,
                'entity_type': 'fact',
                'created_at': datetime.now(),
            },
            {
                'id': 2,
                'content': 'B' * 400,  # ~100 tokens
                'usefulness_score': 0.8,
                'access_count': 0,
                'entity_type': 'fact',
                'created_at': datetime.now(),
            },
            {
                'id': 3,
                'content': 'C' * 400,  # ~100 tokens
                'usefulness_score': 0.7,
                'access_count': 0,
                'entity_type': 'fact',
                'created_at': datetime.now(),
            },
        ]

        token_budget = 250
        summary = budgeter.get_budget_summary(memories, token_budget=token_budget)

        # Verify calculations
        assert summary['total_candidates'] == 3, "Should have 3 candidates"
        assert summary['tokens_budget'] == token_budget, "Budget should match"
        assert summary['tokens_remaining'] == token_budget - summary['tokens_used']
        assert summary['coverage_percentage'] == (summary['selected_count'] / 3 * 100)

        if token_budget > 0:
            assert summary['selection_efficiency'] == (summary['tokens_used'] / token_budget)

    def test_budget_summary_empty_memories(self, importance_budget_config):
        """Budget summary with empty memories should handle gracefully."""
        budgeter = ImportanceWeightedBudgeter(importance_budget_config)

        summary = budgeter.get_budget_summary([], token_budget=2000)

        assert summary['total_candidates'] == 0
        assert summary['selected_count'] == 0
        assert summary['coverage_percentage'] == 0
        assert summary['tokens_used'] == 0


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_memory_without_optional_fields(self, importance_budget_config):
        """Memory without optional fields should use defaults."""
        budgeter = ImportanceWeightedBudgeter(importance_budget_config)

        memory = {
            'id': 1,
            'content': 'Test memory',
            'created_at': datetime.now(),
            # Missing: usefulness_score, access_count, entity_type
        }

        score = budgeter.calculate_importance_score(memory)

        # Should use defaults and return valid score
        assert 0.0 <= score <= 1.0, "Should return valid score with defaults"

    def test_string_created_at(self, importance_budget_config):
        """created_at can be ISO format string."""
        budgeter = ImportanceWeightedBudgeter(importance_budget_config)

        memory = {
            'id': 1,
            'content': 'Test memory',
            'usefulness_score': 0.9,
            'access_count': 0,
            'entity_type': 'fact',
            'created_at': datetime.now().isoformat(),  # String format
        }

        score = budgeter.calculate_importance_score(memory)
        assert 0.0 <= score <= 1.0, "Should handle string created_at"

    def test_none_created_at(self, importance_budget_config):
        """None created_at should default to age 0."""
        budgeter = ImportanceWeightedBudgeter(importance_budget_config)

        memory = {
            'id': 1,
            'content': 'Test memory',
            'usefulness_score': 0.9,
            'access_count': 0,
            'entity_type': 'fact',
            'created_at': None,
        }

        score = budgeter.calculate_importance_score(memory)
        assert 0.0 <= score <= 1.0, "Should handle None created_at"

    def test_very_long_content(self, importance_budget_config):
        """Very long content should be handled gracefully."""
        budgeter = ImportanceWeightedBudgeter(importance_budget_config)

        memory = {
            'id': 1,
            'content': 'A' * 10000,  # Very long
            'usefulness_score': 0.9,
            'access_count': 0,
            'entity_type': 'fact',
            'created_at': datetime.now(),
        }

        selected, tokens_used = budgeter.retrieve_within_budget(
            [memory],
            token_budget=100  # Very small budget
        )

        # Should not select (exceeds budget)
        assert len(selected) == 0, "Should not select memory exceeding budget"

    def test_unknown_entity_type(self, importance_budget_config):
        """Unknown entity type should use default domain weight."""
        budgeter = ImportanceWeightedBudgeter(importance_budget_config)

        memory = {
            'id': 1,
            'content': 'Test memory',
            'usefulness_score': 0.9,
            'access_count': 0,
            'entity_type': 'unknown_type',  # Not in domain_weights
            'created_at': datetime.now(),
        }

        score = budgeter.calculate_importance_score(memory)

        # Should still return valid score (uses default 0.8)
        assert 0.0 <= score <= 1.0, "Should handle unknown entity type"


class TestBatchScenarios:
    """Test realistic batch scenarios."""

    def test_large_batch_selection(self, importance_budget_config, test_data_generator):
        """Should efficiently select best memories from large batch."""
        budgeter = ImportanceWeightedBudgeter(importance_budget_config)

        # Generate 100 memories
        memories = test_data_generator.generate_memories(count=100)

        selected, tokens_used = budgeter.retrieve_within_budget(
            memories,
            token_budget=2000
        )

        # Should select some subset
        assert 0 < len(selected) < len(memories), "Should select subset of memories"
        assert tokens_used <= 2000, "Should respect token budget"

    def test_mixed_entity_types(self, importance_budget_config):
        """Selection should handle mixed entity types correctly."""
        budgeter = ImportanceWeightedBudgeter(importance_budget_config)

        memories = [
            {
                'id': 1,
                'content': 'A' * 400,
                'usefulness_score': 0.6,
                'access_count': 0,
                'entity_type': 'decision',  # Highest weight
                'created_at': datetime.now() - timedelta(days=100),
            },
            {
                'id': 2,
                'content': 'B' * 400,
                'usefulness_score': 0.8,
                'access_count': 0,
                'entity_type': 'context',  # Lowest weight
                'created_at': datetime.now(),  # Recent
            },
            {
                'id': 3,
                'content': 'C' * 400,
                'usefulness_score': 0.7,
                'access_count': 0,
                'entity_type': 'pattern',
                'created_at': datetime.now() - timedelta(days=30),
            },
        ]

        summary = budgeter.get_budget_summary(memories, token_budget=2000)

        # Should select all (all meet minimum usefulness)
        assert summary['selected_count'] == 3, "Should select all above threshold"

    def test_budget_efficiency_metric(self, importance_budget_config):
        """Selection efficiency should indicate budget utilization."""
        budgeter = ImportanceWeightedBudgeter(importance_budget_config)

        memories = [
            {
                'id': 1,
                'content': 'A' * 400,  # ~100 tokens
                'usefulness_score': 0.9,
                'access_count': 0,
                'entity_type': 'fact',
                'created_at': datetime.now(),
            },
            {
                'id': 2,
                'content': 'B' * 400,  # ~100 tokens
                'usefulness_score': 0.8,
                'access_count': 0,
                'entity_type': 'fact',
                'created_at': datetime.now(),
            },
        ]

        summary = budgeter.get_budget_summary(memories, token_budget=250)

        # Should indicate decent efficiency
        assert summary['selection_efficiency'] > 0.5, "Should have >50% efficiency"
        assert summary['selection_efficiency'] <= 1.0, "Should not exceed 100%"

    def test_repeated_selections_consistent(self, importance_budget_config):
        """Repeated selections should be consistent."""
        budgeter = ImportanceWeightedBudgeter(importance_budget_config)

        memories = [
            {
                'id': i,
                'content': f'Memory {i}' * 40,
                'usefulness_score': 0.5 + (i * 0.05),  # Increasing usefulness
                'access_count': i,
                'entity_type': 'fact',
                'created_at': datetime.now() - timedelta(days=i),
            }
            for i in range(10)
        ]

        selected1, tokens1 = budgeter.retrieve_within_budget(memories, token_budget=1000)
        selected2, tokens2 = budgeter.retrieve_within_budget(memories, token_budget=1000)

        # Should be identical
        assert [m['id'] for m in selected1] == [m['id'] for m in selected2]
        assert tokens1 == tokens2
