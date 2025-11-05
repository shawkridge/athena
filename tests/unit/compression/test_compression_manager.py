"""Integration tests for CompressionManager (v1.1).

Tests:
- Manager initialization and configuration
- Strategy coordination (decay, budgeting, consolidation)
- Statistics tracking
- Configuration updates
"""

import pytest
from datetime import datetime, timedelta

from athena.compression import CompressionManager, CompressionConfig


class TestCompressionManagerInitialization:
    """Test manager initialization and setup."""

    def test_manager_creation_default_config(self):
        """Should create manager with default config."""
        manager = CompressionManager()

        assert manager is not None
        assert manager.config is not None
        assert manager.temporal_decay is not None
        assert manager.importance_budgeter is not None
        assert manager.consolidation is not None

    def test_manager_creation_custom_config(self):
        """Should create manager with custom config."""
        config = CompressionConfig()
        config.temporal_decay.enable = True
        config.importance_budgeting.enable = True

        manager = CompressionManager(config)

        assert manager.config == config

    def test_manager_has_all_compressors(self):
        """Manager should have all three compressors initialized."""
        manager = CompressionManager()

        # Check compressors exist
        assert hasattr(manager, 'temporal_decay')
        assert hasattr(manager, 'importance_budgeter')
        assert hasattr(manager, 'consolidation')

        # Check they're the right types
        from athena.compression.base import (
            TemporalDecayCompressor,
            ImportanceWeightedBudgeter,
            ConsolidationCompressor,
        )

        assert isinstance(manager.temporal_decay, TemporalDecayCompressor)
        assert isinstance(manager.importance_budgeter, ImportanceWeightedBudgeter)
        assert isinstance(manager.consolidation, ConsolidationCompressor)


class TestTemporalDecayIntegration:
    """Test temporal decay compression through manager."""

    def test_compress_with_decay(self):
        """Manager should compress using temporal decay."""
        manager = CompressionManager()

        memory = {
            'id': 1,
            'content': 'A' * 400,
            'created_at': datetime.now() - timedelta(days=60),
        }

        result = manager.compress_with_decay(memory)

        assert result.memory_id == 1
        assert result.content_full == memory['content']
        assert result.tokens_original > 0
        assert result.tokens_compressed > 0

    def test_decompress_with_decay(self):
        """Manager should support decompression."""
        manager = CompressionManager()

        result = manager.decompress_with_decay(42)

        assert isinstance(result, str)
        assert '42' in result


class TestImportanceBudgetingIntegration:
    """Test importance budgeting through manager."""

    def test_select_with_budget(self):
        """Manager should select memories within budget."""
        manager = CompressionManager()

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
                'usefulness_score': 0.5,
                'access_count': 0,
                'entity_type': 'fact',
                'created_at': datetime.now(),
            },
        ]

        selected, tokens = manager.select_with_budget(memories, token_budget=150)

        assert len(selected) <= 2
        assert tokens <= 150

    def test_budget_summary(self):
        """Manager should provide budget summary."""
        manager = CompressionManager()

        memories = [
            {
                'id': i,
                'content': f'Memory {i}' * 40,
                'usefulness_score': 0.8,
                'access_count': 0,
                'entity_type': 'fact',
                'created_at': datetime.now(),
            }
            for i in range(5)
        ]

        summary = manager.get_budget_summary(memories, token_budget=2000)

        assert 'total_candidates' in summary
        assert 'selected_count' in summary
        assert 'tokens_used' in summary
        assert summary['total_candidates'] == 5


class TestConsolidationIntegration:
    """Test consolidation compression through manager."""

    def test_compress_consolidation(self):
        """Manager should compress consolidation with summary."""
        manager = CompressionManager()

        consolidation = {
            'id': 1,
            'full_content': 'User implemented JWT auth. ' * 40,
            'created_at': datetime.now(),
        }

        result = manager.compress_consolidation(consolidation)

        assert result.memory_id == 1
        assert result.content_full is not None
        assert result.content_compressed is not None
        assert result.content_executive is not None

    def test_extract_executive_summary(self):
        """Manager should extract summaries."""
        manager = CompressionManager()

        content = 'User implemented authentication system with JWT tokens. ' * 20

        summary = manager.extract_executive_summary(content)

        assert isinstance(summary, str)
        assert len(summary) > 0
        assert len(summary) < len(content)


class TestStrategySelection:
    """Test automatic strategy selection."""

    def test_auto_select_decay_strategy(self):
        """Manager should auto-select decay for regular memories."""
        manager = CompressionManager()

        memory = {
            'id': 1,
            'content': 'A' * 400,
            'entity_type': 'fact',
            'created_at': datetime.now() - timedelta(days=30),
        }

        result = manager.select_compression_strategy(memory, strategy='auto')

        assert result is not None
        assert result.memory_id == 1

    def test_explicit_strategy_decay(self):
        """Manager should use explicit decay strategy."""
        manager = CompressionManager()

        memory = {
            'id': 1,
            'content': 'A' * 400,
            'created_at': datetime.now() - timedelta(days=30),
        }

        result = manager.select_compression_strategy(memory, strategy='decay')

        assert result is not None

    def test_explicit_strategy_consolidation(self):
        """Manager should use explicit consolidation strategy."""
        manager = CompressionManager()

        memory = {
            'id': 1,
            'content': 'Consolidation result. ' * 20,
            'created_at': datetime.now(),
        }

        result = manager.select_compression_strategy(memory, strategy='consolidation')

        assert result is not None

    def test_invalid_strategy_raises_error(self):
        """Manager should reject invalid strategy."""
        manager = CompressionManager()

        memory = {'id': 1, 'content': 'Test', 'created_at': datetime.now()}

        with pytest.raises(ValueError, match="Unknown compression strategy"):
            manager.select_compression_strategy(memory, strategy='invalid')


class TestStatisticsTracking:
    """Test compression statistics tracking."""

    def test_stats_initialized_zero(self):
        """Statistics should start at zero."""
        manager = CompressionManager()

        stats = manager.get_compression_stats()

        assert stats['total_operations'] == 0
        assert stats['total_tokens_original'] == 0
        assert stats['total_tokens_compressed'] == 0

    def test_stats_updated_on_compression(self):
        """Statistics should update after compression."""
        manager = CompressionManager()

        memory = {
            'id': 1,
            'content': 'A' * 800,
            'created_at': datetime.now() - timedelta(days=60),
        }

        manager.compress_with_decay(memory)

        stats = manager.get_compression_stats()

        assert stats['total_operations'] == 1
        assert stats['total_tokens_original'] > 0
        assert stats['total_tokens_compressed'] > 0

    def test_stats_accumulate(self):
        """Statistics should accumulate across operations."""
        manager = CompressionManager()

        for i in range(3):
            memory = {
                'id': i,
                'content': 'A' * 400,
                'created_at': datetime.now() - timedelta(days=30 + i),
            }
            manager.compress_with_decay(memory)

        stats = manager.get_compression_stats()

        assert stats['total_operations'] == 3

    def test_stats_reset(self):
        """Manager should reset statistics."""
        manager = CompressionManager()

        memory = {
            'id': 1,
            'content': 'A' * 400,
            'created_at': datetime.now() - timedelta(days=30),
        }

        manager.compress_with_decay(memory)
        stats_before = manager.get_compression_stats()
        assert stats_before['total_operations'] > 0

        manager.reset_stats()
        stats_after = manager.get_compression_stats()

        assert stats_after['total_operations'] == 0


class TestConfiguration:
    """Test manager configuration handling."""

    def test_get_configuration(self):
        """Manager should export configuration."""
        manager = CompressionManager()

        config_dict = manager.get_configuration()

        assert 'temporal_decay' in config_dict
        assert 'importance_budgeting' in config_dict
        assert 'consolidation_compression' in config_dict
        assert 'global' in config_dict

    def test_update_configuration(self):
        """Manager should update configuration."""
        manager = CompressionManager()

        new_config = {
            'temporal_decay': {
                'decay_schedule': {
                    'recent': 14,
                    'detailed': 60,
                },
            },
        }

        manager.update_configuration(new_config)

        # Verify update
        assert manager.config.temporal_decay.decay_schedule['recent'] == 14
        assert manager.config.temporal_decay.decay_schedule['detailed'] == 60

    def test_configuration_persistence(self):
        """Configuration changes should persist."""
        manager = CompressionManager()

        manager.update_configuration({
            'importance_budgeting': {
                'min_usefulness_score': 0.7,
            },
        })

        # Verify persists across calls
        assert manager.config.importance_budgeting.min_usefulness_score == 0.7

        # Use in operation
        memory = {
            'id': 1,
            'content': 'Test',
            'created_at': datetime.now(),
        }
        # Should not raise


class TestDisabledFeatures:
    """Test behavior when features are disabled."""

    def test_disabled_decay_raises_error(self):
        """Should raise error when decay disabled."""
        config = CompressionConfig()
        config.temporal_decay.enable = False
        manager = CompressionManager(config)

        memory = {'id': 1, 'content': 'Test', 'created_at': datetime.now()}

        with pytest.raises(ValueError, match="disabled"):
            manager.compress_with_decay(memory)

    def test_disabled_budgeting_raises_error(self):
        """Should raise error when budgeting disabled."""
        config = CompressionConfig()
        config.importance_budgeting.enable = False
        manager = CompressionManager(config)

        memories = [{'id': 1, 'content': 'Test', 'created_at': datetime.now()}]

        with pytest.raises(ValueError, match="disabled"):
            manager.select_with_budget(memories)

    def test_disabled_consolidation_raises_error(self):
        """Should raise error when consolidation disabled."""
        config = CompressionConfig()
        config.consolidation_compression.enable = False
        manager = CompressionManager(config)

        consolidation = {
            'id': 1,
            'full_content': 'Test',
            'created_at': datetime.now(),
        }

        with pytest.raises(ValueError, match="disabled"):
            manager.compress_consolidation(consolidation)
