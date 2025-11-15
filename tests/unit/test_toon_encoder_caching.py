"""Tests for TOON encoder prompt caching functionality.

Tests the new prompt caching methods:
- encode_working_memory_with_caching()
- estimate_token_reduction()
"""

import sys
from pathlib import Path

# Add source to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from athena.core.toon_encoder import TOONEncoder
from typing import List, Dict, Any


class TestTOONEncoderCaching:
    """Test TOON encoder prompt caching methods."""

    def test_encode_working_memory_with_caching_empty(self):
        """Test caching encoder with empty memories."""
        result = TOONEncoder.encode_working_memory_with_caching([])

        assert isinstance(result, dict)
        assert result["header"] == ""
        assert result["header_cacheable"] is False
        assert result["rows"] == []
        assert result["full_text"] == ""
        assert result["cache_tokens"] == 0

    def test_encode_working_memory_with_caching_single_item(self):
        """Test caching encoder with single memory item."""
        memories = [
            {
                "id": "mem_1",
                "title": "Assessment Methodology Gap",
                "type": "discovery:analysis",
                "importance": 0.8,
                "composite_score": 0.8,
            }
        ]

        result = TOONEncoder.encode_working_memory_with_caching(memories)

        assert isinstance(result, dict)
        assert result["header_cacheable"] is True
        assert len(result["rows"]) == 1
        assert result["cache_tokens"] > 0
        assert result["data_tokens"] > 0
        assert "cache_savings_pct" in result

    def test_encode_working_memory_with_caching_multiple_items(self):
        """Test caching encoder with multiple memory items."""
        memories = [
            {
                "id": "mem_1",
                "title": "First Item",
                "type": "discovery",
                "importance": 0.9,
                "composite_score": 0.85,
            },
            {
                "id": "mem_2",
                "title": "Second Item",
                "type": "action",
                "importance": 0.7,
                "composite_score": 0.72,
            },
            {
                "id": "mem_3",
                "title": "Third Item",
                "type": "insight",
                "importance": 0.6,
                "composite_score": 0.65,
            },
        ]

        result = TOONEncoder.encode_working_memory_with_caching(memories)

        assert isinstance(result, dict)
        assert result["header"] == "[3]{id,title,type,importance,composite_score}:"
        assert len(result["rows"]) == 3
        assert result["cache_tokens"] > 0
        assert result["cache_savings_pct"] > 0

    def test_encode_working_memory_with_caching_partial_fields(self):
        """Test caching encoder when not all items have all fields."""
        memories = [
            {
                "id": "mem_1",
                "title": "Full Item",
                "type": "test",
                "importance": 0.9,
                "composite_score": 0.85,
            },
            {
                "id": "mem_2",
                "title": "Partial Item",
                # Missing type, importance, composite_score
            },
            {
                "id": "mem_3",
                "title": "Another Item",
                "importance": 0.5,
                # Missing type, composite_score
            },
        ]

        result = TOONEncoder.encode_working_memory_with_caching(memories)

        # Should include only fields that exist in at least one item
        assert result["header_cacheable"] is True
        assert len(result["rows"]) == 3

    def test_encode_working_memory_with_caching_high_importance_items(self):
        """Test caching encoder with high-importance items."""
        memories = [
            {
                "id": "mem_critical",
                "title": "Critical System Issue",
                "type": "alert",
                "importance": 0.95,
                "composite_score": 0.98,
            }
        ]

        result = TOONEncoder.encode_working_memory_with_caching(memories)

        assert result["cache_savings_pct"] > 0
        # High importance items should have more complete representation
        assert "Critical" in result["full_text"]

    def test_encode_working_memory_with_caching_special_chars(self):
        """Test caching encoder handles special characters in content."""
        memories = [
            {
                "id": "mem_1",
                "title": 'Item with "quotes" and commas, colons:',
                "type": "test",
                "importance": 0.8,
                "composite_score": 0.8,
            }
        ]

        result = TOONEncoder.encode_working_memory_with_caching(memories)

        # Should handle special characters gracefully
        assert result["header_cacheable"] is True
        assert len(result["rows"]) > 0
        assert result["full_text"] != ""

    def test_encode_working_memory_with_caching_return_structure(self):
        """Test that return structure has all required fields."""
        memories = [
            {"id": "m1", "title": "Test", "type": "t", "importance": 0.5}
        ]

        result = TOONEncoder.encode_working_memory_with_caching(memories)

        required_fields = [
            "header",
            "header_cacheable",
            "rows",
            "full_text",
            "cache_tokens",
            "data_tokens",
            "cache_savings_pct",
        ]
        for field in required_fields:
            assert field in result, f"Missing field: {field}"

    def test_estimate_token_reduction_identical_strings(self):
        """Test token reduction with identical JSON and TOON."""
        json_text = "test_json_string"
        toon_text = "test_json_string"

        reduction = TOONEncoder.estimate_token_reduction(json_text, toon_text)

        assert reduction == 0.0

    def test_estimate_token_reduction_toon_much_shorter(self):
        """Test token reduction when TOON is significantly shorter."""
        json_text = '{"id":1,"name":"Alice","score":95,"tags":["admin","user"]}'
        toon_text = "compact_toon"

        reduction = TOONEncoder.estimate_token_reduction(json_text, toon_text)

        assert reduction > 0.5  # Should show >50% reduction
        assert 0.0 <= reduction <= 1.0

    def test_estimate_token_reduction_empty_json(self):
        """Test token reduction with empty JSON."""
        reduction = TOONEncoder.estimate_token_reduction("", "something")

        assert reduction == 0.0

    def test_estimate_token_reduction_empty_toon(self):
        """Test token reduction with empty TOON."""
        json_text = "some_json_content"
        reduction = TOONEncoder.estimate_token_reduction(json_text, "")

        # All content removed, 100% reduction
        assert reduction == 1.0

    def test_estimate_token_reduction_various_sizes(self):
        """Test token reduction with various size ratios."""
        test_cases = [
            ("a", "b", 0.0),  # Same size
            ("aaaaaa", "bbb", 0.5),  # 50% reduction
            ("large_json_string_here" * 10, "short", 0.95),  # Large reduction
        ]

        for json_text, toon_text, expected_min in test_cases:
            reduction = TOONEncoder.estimate_token_reduction(json_text, toon_text)
            assert 0.0 <= reduction <= 1.0, f"Invalid reduction: {reduction}"
            assert reduction >= expected_min or abs(
                reduction - expected_min
            ) < 0.01

    def test_encode_working_memory_with_caching_cache_efficiency(self):
        """Test that cache efficiency is properly calculated."""
        memories = [{"id": f"mem_{i}", "title": f"Memory {i}", "type": "test"}
                   for i in range(100)]

        result = TOONEncoder.encode_working_memory_with_caching(memories)

        # Cache savings should be positive for large payloads
        assert result["cache_savings_pct"] > 0
        # Header should be much smaller than full content
        assert result["cache_tokens"] < result["data_tokens"]

    def test_encode_working_memory_with_caching_integration_with_encode_value(self):
        """Test that caching uses encode_value() correctly."""
        memories = [
            {
                "id": "mem_1",
                "title": "Test Item",
                "type": "test",
                "importance": 0.85,
                "composite_score": 0.82,
                "flag": True,  # Boolean
                "null_field": None,  # None
            }
        ]

        result = TOONEncoder.encode_working_memory_with_caching(memories)

        # Should handle various data types
        assert len(result["rows"]) == 1
        # Row should contain encoded values
        assert "," in result["rows"][0]  # CSV format


if __name__ == "__main__":
    # Run tests manually for debugging
    test_instance = TestTOONEncoderCaching()

    tests = [
        method for method in dir(test_instance) if method.startswith("test_")
    ]

    passed = 0
    failed = 0

    for test_name in tests:
        try:
            getattr(test_instance, test_name)()
            print(f"✓ {test_name}")
            passed += 1
        except AssertionError as e:
            print(f"✗ {test_name}: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test_name}: {type(e).__name__}: {e}")
            failed += 1

    print(f"\n{passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
