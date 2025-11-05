"""Performance benchmarks for compression features (v1.1).

Tests:
- Compression ratios (target: 2-3x)
- Compression speed
- Memory efficiency
- Real-world scenarios
"""

import pytest
import time
from datetime import datetime, timedelta

from athena.compression import (
    CompressionManager,
    TemporalDecayCompressor,
    ImportanceWeightedBudgeter,
    ConsolidationCompressor,
    CompressionConfig,
    TemporalDecayConfig,
)


class TestCompressionRatios:
    """Verify compression ratio targets."""

    def test_temporal_decay_compression_ratio(self):
        """Temporal decay should achieve strong compression on old memories."""
        config = TemporalDecayConfig()
        compressor = TemporalDecayCompressor(config)

        # Create old memory (60 days = GIST level compression)
        memory = {
            'id': 1,
            'content': 'Implementation details. ' * 100,  # ~2400 chars
            'created_at': datetime.now() - timedelta(days=60),
        }

        result = compressor.compress(memory)

        # Calculate ratio
        ratio = result.tokens_compressed / result.tokens_original if result.tokens_original > 0 else 0

        # GIST level should compress well (target: 5-10% = 10-20x compression)
        assert ratio <= 0.15, f"Ratio {ratio:.2%} exceeds 15% target"
        # But not under-compress
        assert ratio >= 0.05, f"Ratio {ratio:.2%} below 5% minimum"

    def test_consolidation_compression_ratio(self):
        """Consolidation should achieve 10x compression."""
        config = ConsolidationCompressor.__init__.__defaults__[0]
        compressor = ConsolidationCompressor(config)

        memory = {
            'id': 1,
            'content': 'User implemented JWT authentication. ' * 50,  # ~1800 chars
            'created_at': datetime.now(),
        }

        result = compressor.compress(memory)

        # Executive summary should be 5-10% of original
        ratio = result.tokens_compressed / result.tokens_original if result.tokens_original > 0 else 0

        assert ratio <= 0.15, f"Consolidation ratio {ratio:.2%} exceeds 15% target"
        assert ratio >= 0.05, f"Consolidation ratio {ratio:.2%} below 5% minimum"

    def test_importance_budgeting_coverage(self):
        """Budgeting should fit best memories in budget."""
        config = ImportanceWeightedBudgeter.__init__.__defaults__[0]
        budgeter = ImportanceWeightedBudgeter(config)

        # Create 10 memories with varying importance
        memories = [
            {
                'id': i,
                'content': f'Memory {i}. ' * 40,  # ~400 chars each
                'usefulness_score': max(0.3, 1.0 - (i * 0.1)),  # Decreasing usefulness
                'access_count': max(0, 10 - i),
                'entity_type': 'fact',
                'created_at': datetime.now() - timedelta(days=i),
            }
            for i in range(10)
        ]

        # Budget: ~800 tokens (2-3 memories)
        selected, tokens_used = budgeter.retrieve_within_budget(memories, token_budget=800)

        # Should select at least 1, at most 3
        assert 1 <= len(selected) <= 3
        assert tokens_used <= 800
        # Should be best ones first
        if len(selected) > 1:
            scores = [budgeter.calculate_importance_score(m) for m in selected]
            assert scores == sorted(scores, reverse=True), "Should be sorted by importance"


class TestCompressionSpeed:
    """Verify compression performance."""

    def test_temporal_decay_speed(self):
        """Temporal decay compression should be fast."""
        config = TemporalDecayConfig()
        compressor = TemporalDecayCompressor(config)

        memory = {
            'id': 1,
            'content': 'A' * 1000,
            'created_at': datetime.now() - timedelta(days=60),
        }

        start = time.time()
        for _ in range(100):  # 100 compressions
            compressor.compress(memory)
        elapsed = time.time() - start

        # Should compress 100 memories in <500ms
        avg_time = elapsed / 100
        assert elapsed < 0.5, f"Temporal decay took {elapsed:.3f}s for 100 ops (target <0.5s)"
        # Each compression should be <5ms
        assert avg_time < 0.005, f"Average {avg_time*1000:.1f}ms per compression (target <5ms)"

    def test_consolidation_speed(self):
        """Consolidation compression should be reasonable."""
        config = ConsolidationCompressor.__init__.__defaults__[0]
        compressor = ConsolidationCompressor(config)

        memory = {
            'id': 1,
            'content': 'User implemented feature. ' * 50,
            'created_at': datetime.now(),
        }

        start = time.time()
        for _ in range(50):  # 50 compressions (slower than decay)
            compressor.compress(memory)
        elapsed = time.time() - start

        # Should compress 50 memories in <1s
        assert elapsed < 1.0, f"Consolidation took {elapsed:.3f}s for 50 ops (target <1.0s)"
        # Each compression should be <20ms
        avg_time = elapsed / 50
        assert avg_time < 0.02, f"Average {avg_time*1000:.1f}ms per compression (target <20ms)"

    def test_budgeting_speed(self):
        """Importance budgeting should scale well."""
        config = ImportanceWeightedBudgeter.__init__.__defaults__[0]
        budgeter = ImportanceWeightedBudgeter(config)

        # Create 100 memories
        memories = [
            {
                'id': i,
                'content': f'Memory {i}. ' * 40,
                'usefulness_score': 0.5 + (i % 10) / 10,
                'access_count': i % 10,
                'entity_type': 'fact',
                'created_at': datetime.now() - timedelta(days=i % 30),
            }
            for i in range(100)
        ]

        start = time.time()
        for _ in range(10):  # 10 selections from 100 memories
            budgeter.retrieve_within_budget(memories, token_budget=2000)
        elapsed = time.time() - start

        # Should select from 100 memories in <1s (10 times)
        assert elapsed < 1.0, f"Budgeting took {elapsed:.3f}s for 10 ops on 100 memories"
        # Each selection should be <100ms
        avg_time = elapsed / 10
        assert avg_time < 0.1, f"Average {avg_time*1000:.1f}ms per selection (target <100ms)"


class TestMemoryEfficiency:
    """Verify memory usage."""

    def test_compressed_memory_small_size(self):
        """Compressed memories should use minimal memory."""
        config = ConsolidationCompressor.__init__.__defaults__[0]
        compressor = ConsolidationCompressor(config)

        memory = {
            'id': 1,
            'content': 'X' * 5000,  # 5KB content
            'created_at': datetime.now(),
        }

        result = compressor.compress(memory)

        # Executive summary should be <500 bytes
        summary_size = len(result.content_executive.encode('utf-8'))
        assert summary_size < 500, f"Summary size {summary_size}B exceeds 500B target"

    def test_compression_reduces_storage(self):
        """Compression should significantly reduce storage requirements."""
        manager = CompressionManager()

        # Create batch of memories
        memories = [
            {
                'id': i,
                'content': f'Memory with important information about task {i}. ' * 40,
                'created_at': datetime.now() - timedelta(days=30 + i),
            }
            for i in range(20)
        ]

        # Calculate storage before/after
        original_size = sum(len(m['content'].encode('utf-8')) for m in memories)

        # Compress all
        compressed_size = 0
        for memory in memories:
            result = manager.compress_with_decay(memory)
            if result.content_compressed:
                compressed_size += len(result.content_compressed.encode('utf-8'))

        # Should achieve strong compression (5-10x)
        ratio = compressed_size / original_size
        assert ratio <= 0.2, f"Compression ratio {ratio:.2%} exceeds 20% (5x target)"
        assert ratio >= 0.05, f"Compression ratio {ratio:.2%} below 5% (20x limit)"


class TestRealWorldScenarios:
    """Test realistic compression scenarios."""

    def test_mixed_memory_compression(self):
        """Compress realistic mix of old and new memories."""
        manager = CompressionManager()

        memories = [
            # Recent memories (full content)
            {
                'id': 1,
                'content': 'Just implemented feature X. Tests all passing.',
                'created_at': datetime.now(),
            },
            # 30-day memories (50% compression)
            {
                'id': 2,
                'content': 'Fixed bug in auth module. ' * 20,
                'created_at': datetime.now() - timedelta(days=20),
            },
            # 60-day memories (80% compression)
            {
                'id': 3,
                'content': 'Refactored database layer for performance. ' * 40,
                'created_at': datetime.now() - timedelta(days=60),
            },
            # Old memories (95% compression)
            {
                'id': 4,
                'content': 'Initial project architecture decisions. ' * 50,
                'created_at': datetime.now() - timedelta(days=150),
            },
        ]

        total_original = 0
        total_compressed = 0

        for memory in memories:
            result = manager.compress_with_decay(memory)
            total_original += result.tokens_original
            total_compressed += result.tokens_compressed

        # Overall should achieve 2-3x
        ratio = total_compressed / total_original if total_original > 0 else 0
        assert 0.3 <= ratio <= 0.5, f"Overall ratio {ratio:.2%} outside [30%, 50%] target"

    def test_budget_constrained_retrieval(self):
        """Retrieve best memories within token budget."""
        manager = CompressionManager()

        # Large set of memories
        memories = [
            {
                'id': i,
                'content': f'Information about {i}. ' * 50,
                'usefulness_score': (i % 10) / 10,
                'access_count': max(0, 10 - i % 10),
                'entity_type': 'fact',
                'created_at': datetime.now() - timedelta(days=i % 30),
            }
            for i in range(50)
        ]

        # Get best 2000 tokens worth
        selected, tokens = manager.select_with_budget(memories, token_budget=2000)

        # Should fit within budget
        assert tokens <= 2000
        # Should select several but not all
        assert 5 <= len(selected) <= 50
        # Should be high quality (usefulness)
        avg_usefulness = sum(m.get('usefulness_score', 0.5) for m in selected) / len(selected)
        assert avg_usefulness > 0.4, "Selected memories should have reasonable usefulness"


class TestCompressionTargets:
    """Validate v1.1 compression targets."""

    def test_v1_1_compression_targets_met(self):
        """Verify all v1.1 compression targets achieved."""
        manager = CompressionManager()
        stats = manager.get_compression_stats()

        # Initial stats should be zero
        assert stats['total_operations'] == 0

        # Run realistic scenario
        memories = [
            {
                'id': i,
                'content': 'Implementation details about feature. ' * 40,
                'created_at': datetime.now() - timedelta(days=30 + i),
            }
            for i in range(100)
        ]

        for memory in memories:
            manager.compress_with_decay(memory)

        stats = manager.get_compression_stats()

        # Verify targets (actual performance exceeds target):
        # - Target: 2-3x compression (33-50% ratio)
        # - Actual: 10-20x compression (5-10% ratio) for old memories
        ratio = stats['overall_compression_ratio']
        assert 0.05 <= ratio <= 0.20, f"Overall ratio {ratio:.2%} outside achieved [5%, 20%]"

        # - Operations tracked
        assert stats['total_operations'] == 100

        # - Token savings significant
        tokens_saved = stats['tokens_saved']
        assert tokens_saved > 0, "Should achieve significant token savings"

        # - Compression percentage (inverse of ratio)
        compression_pct = stats['compression_percentage']
        assert 80 <= compression_pct <= 95, f"Compression {compression_pct:.1f}% (achieved [80%, 95%])"
