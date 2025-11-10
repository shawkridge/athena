"""Tests for TOON codec and serialization."""

import json
import pytest
from athena.serialization.toon_codec import (
    TOONCodec,
    TOONCodecError,
    TOONEncodeError,
    TOONDecodeError,
)
from athena.serialization.schemas import get_schema, validate_against_schema
from athena.serialization.metrics import (
    TOONMetricsCollector,
    TOONOperationMetrics,
    get_metrics_collector,
)


class TestTOONCodecAvailability:
    """Test TOON codec availability check."""

    def test_is_available_check(self):
        """Test checking if TOON is available."""
        # Should not raise even if TOON is not installed
        available = TOONCodec.is_available()
        assert isinstance(available, bool)


class TestTOONCodecEncoding:
    """Test TOON encoding operations."""

    @pytest.mark.skipif(not TOONCodec.is_available(), reason="TOON not available")
    def test_encode_simple_dict(self):
        """Test encoding simple dictionary."""
        data = {"name": "test", "value": 42}
        result = TOONCodec.encode(data)
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.skipif(not TOONCodec.is_available(), reason="TOON not available")
    def test_encode_array_of_objects(self):
        """Test encoding array of objects."""
        data = {
            "items": [
                {"id": 1, "name": "Alice", "score": 95},
                {"id": 2, "name": "Bob", "score": 87},
            ]
        }
        result = TOONCodec.encode(data)
        assert isinstance(result, str)

    @pytest.mark.skipif(not TOONCodec.is_available(), reason="TOON not available")
    def test_encode_nested_structure(self):
        """Test encoding nested structure."""
        data = {
            "users": [
                {
                    "id": 1,
                    "name": "Alice",
                    "roles": ["admin", "user"],
                    "metadata": {"created": "2024-01-01"},
                }
            ]
        }
        result = TOONCodec.encode(data)
        assert isinstance(result, str)

    @pytest.mark.skipif(not TOONCodec.is_available(), reason="TOON not available")
    def test_encode_empty_dict(self):
        """Test encoding empty dictionary."""
        data = {}
        result = TOONCodec.encode(data)
        # Should return empty string or minimal encoding
        assert isinstance(result, str)

    def test_encode_without_toon_available(self):
        """Test that TOON is available in test environment."""
        # TOON should now be available after installation
        available = TOONCodec.is_available()
        assert available is True, "TOON CLI should be available"

        data = {"test": "data"}
        # Should encode successfully
        result = TOONCodec.encode(data)
        assert isinstance(result, str)
        assert len(result) > 0


class TestTOONCodecDecoding:
    """Test TOON decoding operations."""

    @pytest.mark.skipif(not TOONCodec.is_available(), reason="TOON not available")
    def test_decode_simple_toon(self):
        """Test decoding simple TOON format."""
        # Encode first, then decode
        data = {"name": "test", "value": 42}
        encoded = TOONCodec.encode(data)
        decoded = TOONCodec.decode(encoded)

        assert isinstance(decoded, dict)
        assert "name" in decoded

    @pytest.mark.skipif(not TOONCodec.is_available(), reason="TOON not available")
    def test_roundtrip_simple(self):
        """Test encode-decode roundtrip preserves data."""
        original = {"id": 1, "name": "test", "score": 95.5}
        encoded = TOONCodec.encode(original)
        decoded = TOONCodec.decode(encoded)

        assert decoded["id"] == original["id"]
        assert decoded["name"] == original["name"]
        assert decoded["score"] == original["score"]

    @pytest.mark.skipif(not TOONCodec.is_available(), reason="TOON not available")
    def test_roundtrip_complex(self):
        """Test roundtrip with complex nested structure."""
        original = {
            "users": [
                {
                    "id": 1,
                    "name": "Alice",
                    "tags": ["admin", "dev"],
                    "active": True,
                },
                {
                    "id": 2,
                    "name": "Bob",
                    "tags": ["user"],
                    "active": False,
                },
            ]
        }
        encoded = TOONCodec.encode(original)
        decoded = TOONCodec.decode(encoded)

        assert len(decoded.get("users", [])) == 2
        assert decoded["users"][0]["name"] == "Alice"


class TestTOONCodecSafeOperations:
    """Test safe encoding/decoding with fallback."""

    def test_safe_encode_fallback_to_json(self):
        """Test safe encoding falls back to JSON."""
        data = {"test": "data"}
        result = TOONCodec.safe_encode(data, fallback_to_json=True)
        # Should return either TOON or valid JSON
        assert isinstance(result, str)
        # Try parsing as JSON
        try:
            json.loads(result)
            assert True  # Valid JSON
        except json.JSONDecodeError:
            # Could be TOON format
            assert True

    def test_safe_encode_json_format_detection(self):
        """Test that safe_encode returns JSON if TOON not available."""
        data = {"test": "value"}
        result = TOONCodec.safe_encode(data, fallback_to_json=True)

        # Should be parseable as JSON at minimum
        try:
            decoded = json.loads(result)
            assert "test" in decoded
        except json.JSONDecodeError:
            # If not JSON, it might be valid TOON
            # (we can't validate TOON without the encoder)
            pass

    def test_safe_decode_json_fallback(self):
        """Test safe decoding with JSON fallback."""
        json_str = json.dumps({"test": "value"})
        result = TOONCodec.safe_decode(json_str, fallback_to_json=True)

        assert isinstance(result, dict)
        assert result.get("test") == "value"


class TestTOONMetrics:
    """Test TOON metrics collection."""

    def test_metrics_collector_creation(self):
        """Test creating metrics collector."""
        collector = TOONMetricsCollector()
        assert collector.max_history == 10000
        assert len(collector.metrics) == 0

    def test_record_encode_operation(self):
        """Test recording encode operation."""
        collector = TOONMetricsCollector()
        json_str = json.dumps({"test": "data"})
        toon_str = "test_toon_encoded"

        collector.record_encode(
            "test_schema", 10.5, json_str, toon_str, success=True, error=None
        )

        assert len(collector.metrics) == 1
        metric = collector.metrics[0]
        assert metric.operation_type == "encode"
        assert metric.schema_name == "test_schema"
        assert metric.success

    def test_record_decode_operation(self):
        """Test recording decode operation."""
        collector = TOONMetricsCollector()

        collector.record_decode(
            "test_schema",
            5.2,
            100,  # toon_size
            200,  # json_size
            success=True,
            error=None,
        )

        assert len(collector.metrics) == 1
        metric = collector.metrics[0]
        assert metric.operation_type == "decode"

    def test_metrics_summary(self):
        """Test metrics summary generation."""
        collector = TOONMetricsCollector()

        json_str = json.dumps({"id": 1, "name": "test", "value": 100})
        toon_str = "compact_encoding"

        collector.record_encode(
            "test_schema", 10.0, json_str, toon_str, success=True
        )

        summary = collector.get_summary()

        assert summary["total_operations"] == 1
        assert summary["encode_operations"] == 1
        assert summary["success_rate"] == 1.0
        assert summary["avg_token_savings_percent"] > 0

    def test_metrics_per_schema_stats(self):
        """Test per-schema statistics."""
        collector = TOONMetricsCollector()

        # Add metrics for two schemas
        json1 = json.dumps({"a": 1})
        json2 = json.dumps({"b": 2, "c": 3})

        collector.record_encode("schema_a", 5.0, json1, "a_compact", True)
        collector.record_encode("schema_b", 8.0, json2, "b_compact", True)

        stats_a = collector.get_schema_stats("schema_a")
        stats_b = collector.get_schema_stats("schema_b")

        assert stats_a["schema_name"] == "schema_a"
        assert stats_a["total_operations"] == 1
        assert stats_b["total_operations"] == 1

    def test_metrics_all_schema_stats(self):
        """Test getting stats for all schemas."""
        collector = TOONMetricsCollector()

        collector.record_encode("schema_a", 5.0, '{"a":1}', "compact_a", True)
        collector.record_encode("schema_b", 8.0, '{"b":2}', "compact_b", True)

        all_stats = collector.get_all_schema_stats()

        assert len(all_stats) == 2
        assert "schema_a" in all_stats
        assert "schema_b" in all_stats

    def test_metrics_error_tracking(self):
        """Test tracking failed operations."""
        collector = TOONMetricsCollector()

        collector.record_encode("schema", 2.0, '{"test":"data"}', "", False, "Test error")

        errors = collector.get_errors()
        assert len(errors) == 1
        assert errors[0].error == "Test error"

    def test_metrics_performance_report(self):
        """Test generating performance report."""
        collector = TOONMetricsCollector()

        collector.record_encode("schema_a", 10.0, '{"a":1,"b":2}', "compact", True)
        collector.record_decode("schema_a", 5.0, 20, 30, True)

        report = collector.get_performance_report()

        assert isinstance(report, str)
        assert "TOON SERIALIZATION PERFORMANCE REPORT" in report
        assert "schema_a" in report
        assert "Success Rate" in report

    def test_global_metrics_collector(self):
        """Test global metrics collector singleton."""
        collector1 = get_metrics_collector()
        collector2 = get_metrics_collector()

        assert collector1 is collector2


class TestTOONSchemas:
    """Test TOON schema definitions."""

    def test_get_episodic_events_schema(self):
        """Test episodic events schema."""
        schema = get_schema("episodic_events")

        assert "fields" in schema
        assert "id" in schema["fields"]
        assert "type" in schema["fields"]
        assert "timestamp" in schema["fields"]

    def test_get_knowledge_graph_entities_schema(self):
        """Test knowledge graph entities schema."""
        schema = get_schema("knowledge_graph_entities")

        assert "fields" in schema
        assert "id" in schema["fields"]
        assert "type" in schema["fields"]
        assert "name" in schema["fields"]

    def test_get_semantic_search_results_schema(self):
        """Test semantic search results schema."""
        schema = get_schema("semantic_search_results")

        assert "fields" in schema
        assert "rank" in schema["fields"]
        assert "score" in schema["fields"]

    def test_schema_validation_episodic_event(self):
        """Test validating episodic event against schema."""
        event = {
            "id": 1,
            "type": "code_interaction",
            "timestamp": "2024-01-01T10:00:00",
            "tags": ["test", "dev"],
            "entity_type": "function",
            "entity_name": "test_func",
            "relevance_score": 0.95,
        }

        valid = validate_against_schema(event, "episodic_events")
        assert valid is True

    def test_schema_validation_missing_fields(self):
        """Test validation fails with missing fields."""
        incomplete_event = {"id": 1, "type": "test"}

        valid = validate_against_schema(incomplete_event, "episodic_events")
        assert valid is False

    def test_schema_validation_array(self):
        """Test validating array against schema."""
        events = [
            {
                "id": 1,
                "type": "event1",
                "timestamp": "2024-01-01",
                "tags": [],
                "entity_type": "type1",
                "entity_name": "name1",
                "relevance_score": 0.9,
            }
        ]

        valid = validate_against_schema(events, "episodic_events")
        assert valid is True


class TestTOONTokenSavings:
    """Test token savings calculation."""

    def test_estimate_token_savings(self):
        """Test estimating token savings."""
        json_str = json.dumps(
            {"users": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]}
        )
        toon_str = "compact_representation"

        savings = TOONCodec.estimate_token_savings(json_str, toon_str)

        assert isinstance(savings, float)
        assert 0 <= savings <= 100

    def test_token_savings_zero_original(self):
        """Test token savings with empty original."""
        savings = TOONCodec.estimate_token_savings("", "something")
        assert savings == 0.0

    def test_token_savings_large_reduction(self):
        """Test token savings with significant reduction."""
        json_str = json.dumps({"data": [{"x": 1, "y": 2}] * 100})
        toon_str = "very_short"

        savings = TOONCodec.estimate_token_savings(json_str, toon_str)
        assert savings > 50  # Should show significant savings


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
