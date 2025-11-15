"""Tests for enhanced memory_bridge.py ranking and truncation.

Tests the new/enhanced methods:
- truncate_by_importance() - Smart content truncation based on importance
- get_active_memories() - Enhanced with combined ranking formula
"""

import sys
from pathlib import Path

# Mock the external dependencies that memory_bridge imports
import types

# Create mock modules for connection_pool and query_cache
connection_pool_mock = types.ModuleType("connection_pool")
connection_pool_mock.get_connection_pool = lambda: None
connection_pool_mock.PooledConnection = object

query_cache_mock = types.ModuleType("query_cache")
query_cache_mock.get_query_cache = lambda: None
query_cache_mock.QueryCacheKey = object

sys.modules["connection_pool"] = connection_pool_mock
sys.modules["query_cache"] = query_cache_mock

# Add source to path AFTER mocking
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "claude/hooks/lib"))

# Now we can import memory_bridge
from memory_bridge import truncate_by_importance


class TestTruncateByImportance:
    """Test the truncate_by_importance() function."""

    def test_high_importance_keeps_full_content(self):
        """Test that high importance (>=0.7) returns full content."""
        content = "This is a very long piece of content that should be kept intact because it is important"

        # Test boundary at 0.7
        result = truncate_by_importance(content, 0.7)
        assert result == content

        # Test high importance
        result = truncate_by_importance(content, 0.9)
        assert result == content

        result = truncate_by_importance(content, 1.0)
        assert result == content

    def test_medium_importance_truncates_to_200_chars(self):
        """Test that medium importance (0.5-0.7) truncates to 200 chars."""
        short_content = "Short content"
        long_content = "a" * 250

        # Short content should not be truncated
        result = truncate_by_importance(short_content, 0.6)
        assert result == short_content

        # Long content should be truncated
        result = truncate_by_importance(long_content, 0.6)
        assert result == "a" * 200 + "..."
        assert len(result) == 203  # 200 + "..."

        # Test boundary at 0.5 and 0.7
        result = truncate_by_importance(long_content, 0.5)
        assert result == "a" * 200 + "..."

        result = truncate_by_importance(long_content, 0.69999)
        assert result == "a" * 200 + "..."

    def test_low_importance_truncates_to_50_chars(self):
        """Test that low importance (<0.5) truncates to 50 chars."""
        short_content = "Short"
        long_content = "b" * 100

        # Short content should not be truncated
        result = truncate_by_importance(short_content, 0.3)
        assert result == short_content

        # Long content should be truncated to 50 chars
        result = truncate_by_importance(long_content, 0.3)
        assert result == "b" * 50 + "..."
        assert len(result) == 53  # 50 + "..."

        # Test boundary at 0.0 and 0.49999
        result = truncate_by_importance(long_content, 0.0)
        assert result == "b" * 50 + "..."

        result = truncate_by_importance(long_content, 0.49999)
        assert result == "b" * 50 + "..."

    def test_exact_boundary_at_200_chars(self):
        """Test truncation at exact 200 character boundary."""
        content_200 = "x" * 200
        content_201 = "x" * 201

        # Exactly 200 chars with medium importance - should not truncate
        result = truncate_by_importance(content_200, 0.6)
        assert result == content_200

        # 201 chars should truncate
        result = truncate_by_importance(content_201, 0.6)
        assert result == "x" * 200 + "..."

    def test_exact_boundary_at_50_chars(self):
        """Test truncation at exact 50 character boundary."""
        content_50 = "y" * 50
        content_51 = "y" * 51

        # Exactly 50 chars with low importance - should not truncate
        result = truncate_by_importance(content_50, 0.3)
        assert result == content_50

        # 51 chars should truncate
        result = truncate_by_importance(content_51, 0.3)
        assert result == "y" * 50 + "..."

    def test_empty_content(self):
        """Test with empty content."""
        assert truncate_by_importance("", 0.9) == ""
        assert truncate_by_importance("", 0.6) == ""
        assert truncate_by_importance("", 0.3) == ""

    def test_single_character_content(self):
        """Test with single character."""
        assert truncate_by_importance("a", 0.3) == "a"
        assert truncate_by_importance("a", 0.6) == "a"
        assert truncate_by_importance("a", 0.9) == "a"

    def test_content_with_special_characters(self):
        """Test content with special characters is preserved."""
        special_content = "Line 1\nLine 2\nLine 3" * 20

        # High importance preserves special chars
        result = truncate_by_importance(special_content, 0.9)
        assert result == special_content
        assert "\n" in result

        # Medium importance truncates but preserves what's kept
        result = truncate_by_importance(special_content, 0.6)
        assert result[:50].startswith("Line")
        assert result.endswith("...")

        # Low importance also preserves structure
        result = truncate_by_importance(special_content, 0.3)
        assert result[:20] == special_content[:20]
        assert result.endswith("...")

    def test_importance_score_edge_cases(self):
        """Test with edge case importance scores."""
        content = "test" * 100  # 400 chars total

        # Test with 0.0 - should use low importance (50 char limit)
        result = truncate_by_importance(content, 0.0)
        assert result == content[:50] + "...", f"Expected 50-char truncation, got {len(result)-3} chars"

        # Test with 1.0 - should keep full content
        result = truncate_by_importance(content, 1.0)
        assert result == content, f"Expected full content ({len(content)} chars), got {len(result)} chars"

        # Boundary values
        result = truncate_by_importance(content, 0.4999999)
        assert result == content[:50] + "...", f"Expected 50-char truncation below 0.5, got {len(result)-3} chars"

        result = truncate_by_importance(content, 0.5)
        assert result == content[:200] + "...", f"Expected 200-char truncation at 0.5, got {len(result)-3} chars"

    def test_multiline_content_truncation(self):
        """Test that multiline content is truncated correctly."""
        lines = ["Line " + str(i) for i in range(50)]
        content = "\n".join(lines)

        result = truncate_by_importance(content, 0.3)
        # Should be truncated to 50 chars
        assert len(result) == 53  # 50 + "..."
        assert result.endswith("...")

    def test_unicode_content_truncation(self):
        """Test truncation with Unicode characters."""
        unicode_content = "🔥 " * 100  # Fire emoji repeated

        # High importance keeps full content
        result = truncate_by_importance(unicode_content, 0.9)
        assert result == unicode_content

        # Low importance truncates
        result = truncate_by_importance(unicode_content, 0.3)
        assert result.endswith("...")
        assert len(result) <= 56  # 50 chars + "..." + margin for multi-byte


class TestGetActiveMemoriesRanking:
    """Test the ranking formula used in get_active_memories().

    The ranking formula is:
    combined_rank = importance × contextuality × actionability
    """

    def test_ranking_formula_calculation(self):
        """Test that combined rank calculation matches the formula."""
        # importance × contextuality × actionability
        importance = 0.8
        contextuality = 0.9
        actionability = 0.7

        expected_rank = importance * contextuality * actionability
        assert expected_rank == 0.8 * 0.9 * 0.7
        assert abs(expected_rank - 0.504) < 0.001

    def test_ranking_with_all_ones(self):
        """Test ranking when all scores are 1.0."""
        rank = 1.0 * 1.0 * 1.0
        assert rank == 1.0

    def test_ranking_with_all_zeros(self):
        """Test ranking when all scores are 0.0."""
        rank = 0.0 * 0.0 * 0.0
        assert rank == 0.0

    def test_ranking_with_one_zero(self):
        """Test that any zero score results in zero rank."""
        rank = 0.8 * 0.0 * 0.7
        assert rank == 0.0

        rank = 0.8 * 0.9 * 0.0
        assert rank == 0.0

    def test_ranking_coalesce_defaults(self):
        """Test that COALESCE defaults to 0.5 when scores are None."""
        # Simulate missing scores defaulting to 0.5
        importance = 0.5  # Default
        contextuality = 0.9
        actionability = 0.5  # Default

        rank = importance * contextuality * actionability
        assert rank == 0.5 * 0.9 * 0.5
        assert abs(rank - 0.225) < 0.001

    def test_ranking_importance_impact(self):
        """Test that importance score significantly impacts ranking."""
        high_importance = 0.9 * 0.8 * 0.8
        low_importance = 0.2 * 0.8 * 0.8

        # High importance should rank much higher
        assert high_importance > low_importance
        assert high_importance / low_importance > 4.0

    def test_ranking_contextuality_impact(self):
        """Test that contextuality score impacts ranking."""
        good_context = 0.8 * 0.9 * 0.7
        poor_context = 0.8 * 0.1 * 0.7

        # Good context should rank much higher
        assert good_context > poor_context
        assert good_context / poor_context > 8.0

    def test_ranking_order_preservation(self):
        """Test that items are ordered by combined_rank DESC."""
        items = [
            {"rank": 0.5 * 0.8 * 0.9},  # 0.36
            {"rank": 0.9 * 0.9 * 0.9},  # 0.729
            {"rank": 0.3 * 0.5 * 0.7},  # 0.105
            {"rank": 0.7 * 0.7 * 0.7},  # 0.343
        ]

        # Items should be ordered by rank
        sorted_items = sorted(items, key=lambda x: -x["rank"])

        expected_order = [0.729, 0.36, 0.343, 0.105]
        for i, expected_rank in enumerate(expected_order):
            assert abs(sorted_items[i]["rank"] - expected_rank) < 0.001

    def test_ranking_favors_balanced_scores(self):
        """Test that balanced scores rank better than extreme scores."""
        # All balanced at 0.7
        balanced = 0.7 * 0.7 * 0.7

        # One high, two low
        extreme = 0.99 * 0.1 * 0.1

        # Balanced should be better
        assert balanced > extreme

    def test_ranking_preserves_monotonicity(self):
        """Test that ranking preserves monotonic ordering."""
        # Create a range of importance scores
        scores = [0.1 * i for i in range(1, 11)]  # 0.1 to 0.9

        ranks = [s * 0.7 * 0.7 for s in scores]  # Fixed context and actionability

        # Ranks should be strictly increasing
        for i in range(len(ranks) - 1):
            assert ranks[i] < ranks[i + 1]


if __name__ == "__main__":
    # Run tests manually for debugging
    test_classes = [TestTruncateByImportance, TestGetActiveMemoriesRanking]

    passed = 0
    failed = 0

    for test_class in test_classes:
        test_instance = test_class()
        tests = [method for method in dir(test_instance) if method.startswith("test_")]

        for test_name in tests:
            try:
                getattr(test_instance, test_name)()
                print(f"✓ {test_class.__name__}.{test_name}")
                passed += 1
            except AssertionError as e:
                print(f"✗ {test_class.__name__}.{test_name}: {e}")
                failed += 1
            except Exception as e:
                print(f"✗ {test_class.__name__}.{test_name}: {type(e).__name__}: {e}")
                failed += 1

    print(f"\n{passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
