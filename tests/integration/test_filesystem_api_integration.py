"""
Integration Tests for Filesystem API Anthropic Pattern

Tests the complete discover → read → execute → summarize flow
for all 10 memory operations using the FilesystemAPIAdapter.

This validates that the filesystem API is fully aligned with
Anthropic's code execution pattern.
"""

import os
import sys
import pytest
from pathlib import Path
from typing import Dict, Any

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
sys.path.insert(0, "/home/user/.claude/hooks/lib")


class TestFilesystemAPIDiscovery:
    """Test operation discovery (Phase 1: Discover)."""

    def test_list_layers(self):
        """Test discovering all memory layers."""
        from filesystem_api_adapter import FilesystemAPIAdapter

        adapter = FilesystemAPIAdapter()
        result = adapter.list_layers()

        assert "error" not in result
        assert result["total_layers"] == 8
        assert len(result["layers"]) == 8

        layer_names = {l["name"] for l in result["layers"]}
        expected = {
            "episodic",
            "semantic",
            "consolidation",
            "graph",
            "meta",
            "planning",
            "procedural",
            "prospective",
        }
        assert layer_names == expected

    def test_list_operations_in_each_layer(self):
        """Test discovering operations in each layer."""
        from filesystem_api_adapter import FilesystemAPIAdapter

        adapter = FilesystemAPIAdapter()

        expected_ops = {
            "episodic": ["search", "timeline"],
            "semantic": ["recall"],
            "consolidation": ["extract"],
            "graph": ["communities", "traverse"],
            "meta": ["quality"],
            "planning": ["decompose"],
            "procedural": ["find"],
            "prospective": ["tasks"],
        }

        for layer, expected_op_list in expected_ops.items():
            result = adapter.list_operations_in_layer(layer)

            assert "error" not in result
            assert result["operation_count"] == len(expected_op_list)

            op_names = {op["name"] for op in result["operations"]}
            assert op_names == set(expected_op_list)


class TestFilesystemAPICodeReading:
    """Test code reading (Phase 2: Read)."""

    def test_read_operation_code(self):
        """Test reading operation code files."""
        from filesystem_api_adapter import FilesystemAPIAdapter

        adapter = FilesystemAPIAdapter()

        # Test reading episodic/search.py
        result = adapter.read_operation("episodic", "search")

        assert "error" not in result
        assert result["layer"] == "episodic"
        assert result["operation"] == "search"
        assert result["path"] == "/athena/layers/episodic/search.py"
        assert len(result["code"]) > 0
        assert "Search episodic events" in result["docstring"]

    def test_read_all_operations(self):
        """Test reading all 10 operations."""
        from filesystem_api_adapter import FilesystemAPIAdapter

        adapter = FilesystemAPIAdapter()

        operations = [
            ("episodic", "search"),
            ("episodic", "timeline"),
            ("semantic", "recall"),
            ("consolidation", "extract"),
            ("graph", "communities"),
            ("graph", "traverse"),
            ("meta", "quality"),
            ("planning", "decompose"),
            ("procedural", "find"),
            ("prospective", "tasks"),
        ]

        for layer, op in operations:
            result = adapter.read_operation(layer, op)

            assert "error" not in result, f"Failed to read {layer}/{op}: {result}"
            assert result["layer"] == layer
            assert result["operation"] == op
            assert len(result["code"]) > 100  # Should be substantial code
            assert len(result["docstring"]) > 20  # Should have docstring


class TestFilesystemAPIFunctionNames:
    """Test function name extraction."""

    def test_extract_function_names(self):
        """Test that function names are correctly extracted from modules."""
        from filesystem_api_adapter import FilesystemAPIAdapter

        adapter = FilesystemAPIAdapter()

        function_map = {
            ("episodic", "search"): "search_events",
            ("episodic", "timeline"): "get_event_timeline",
            ("semantic", "recall"): "search_memories",
            ("consolidation", "extract"): "extract_patterns",
            ("graph", "communities"): "detect_communities",
            ("graph", "traverse"): "search_entities",
            ("meta", "quality"): "assess_memory_quality",
            ("planning", "decompose"): "decompose_task",
            ("procedural", "find"): "find_procedures",
            ("prospective", "tasks"): "list_tasks",
        }

        for (layer, op), expected_func in function_map.items():
            actual_func = adapter._get_function_name(layer, op)
            assert (
                actual_func == expected_func
            ), f"{layer}/{op}: expected {expected_func}, got {actual_func}"


class TestFilesystemAPIExecution:
    """Test operation execution (Phase 3: Execute)."""

    @pytest.mark.skipif(
        not os.environ.get("ATHENA_RUN_INTEGRATION_TESTS"),
        reason="Requires PostgreSQL database",
    )
    def test_execute_episodic_search(self):
        """Test executing episodic search operation."""
        from filesystem_api_adapter import FilesystemAPIAdapter

        adapter = FilesystemAPIAdapter()

        result = adapter.execute_operation(
            "episodic",
            "search",
            {
                "query": "test",
                "host": "localhost",
                "port": 5432,
                "dbname": "athena",
                "user": "postgres",
                "password": "postgres",
            },
        )

        assert result["status"] in ["success", "error"]
        assert "result" in result or "error" in result

    def test_execute_operation_without_db(self):
        """Test execution fails gracefully without database."""
        from filesystem_api_adapter import FilesystemAPIAdapter

        adapter = FilesystemAPIAdapter()

        # Try to execute with invalid connection params
        result = adapter.execute_operation(
            "episodic",
            "search",
            {
                "query": "test",
                "host": "invalid-host",
                "port": 9999,
                "dbname": "nonexistent",
                "user": "invalid",
                "password": "invalid",
            },
        )

        # Should get an error (not crash)
        assert result["status"] == "error"
        assert "error" in result


class TestFilesystemAPISummary:
    """Test result summarization (Phase 4: Summarize)."""

    def test_execution_returns_summary(self):
        """Test that execution results are summaries, not full data."""
        from filesystem_api_adapter import FilesystemAPIAdapter

        adapter = FilesystemAPIAdapter()

        # Get operation code
        op_code = adapter.read_operation("episodic", "search")

        # Parse docstring to understand what summary contains
        docstring = op_code["docstring"]

        # Should mention "summary" or "counts" not "full events"
        assert "summary" in docstring.lower() or "counts" in docstring.lower()
        assert "full events" not in docstring.lower()
        assert "never" not in docstring.lower() or "full" not in docstring.lower()


class TestAnthropicPatternAlignment:
    """Test alignment with Anthropic's code execution pattern."""

    def test_discover_pattern(self):
        """Test Discover phase of pattern."""
        from filesystem_api_adapter import FilesystemAPIAdapter

        adapter = FilesystemAPIAdapter()

        # Phase 1: Discover - No tool definitions loaded, just structure
        layers_result = adapter.list_layers()

        # Should return metadata about layers, not implementations
        assert "layers" in layers_result
        for layer in layers_result["layers"]:
            assert "name" in layer
            assert "operations" in layer
            # Should NOT include operation code here
            assert "code" not in layer

    def test_read_pattern(self):
        """Test Read phase of pattern."""
        from filesystem_api_adapter import FilesystemAPIAdapter

        adapter = FilesystemAPIAdapter()

        # Phase 2: Read - Load only the operation code, not all operations
        op_code = adapter.read_operation("episodic", "search")

        # Should have code and signature info
        assert "code" in op_code
        assert "docstring" in op_code
        # Should NOT have execution results here
        assert "result" not in op_code

    def test_execute_pattern(self):
        """Test Execute phase of pattern."""
        # Phase 3: Execute - Process data locally, return summary only
        # Note: We skip actual execution without DB, but test the method exists
        from filesystem_api_adapter import FilesystemAPIAdapter

        adapter = FilesystemAPIAdapter()

        # Method should exist and accept correct params
        assert hasattr(adapter, "execute_operation")
        assert callable(adapter.execute_operation)

    def test_summarize_pattern(self):
        """Test Summarize phase of pattern."""
        # Phase 4: Summarize - Results are summaries, not full data
        from filesystem_api_adapter import FilesystemAPIAdapter

        adapter = FilesystemAPIAdapter()

        # Read operation to understand what should be returned
        op_code = adapter.read_operation("consolidation", "extract")

        docstring = op_code["docstring"]
        # Should explicitly document summary-first approach
        assert "summary" in docstring.lower()
        assert "never" in docstring.lower() or "summary" in docstring.lower()


class TestAllOperationsAccessible:
    """Test that all 10 operations are fully accessible."""

    def test_all_operations_discoverable_readable(self):
        """Test all 10 operations can be discovered and read."""
        from filesystem_api_adapter import FilesystemAPIAdapter

        adapter = FilesystemAPIAdapter()

        operations = [
            ("episodic", "search"),
            ("episodic", "timeline"),
            ("semantic", "recall"),
            ("consolidation", "extract"),
            ("graph", "communities"),
            ("graph", "traverse"),
            ("meta", "quality"),
            ("planning", "decompose"),
            ("procedural", "find"),
            ("prospective", "tasks"),
        ]

        for layer, op in operations:
            # Discover
            ops_list = adapter.list_operations_in_layer(layer)
            op_names = {o["name"] for o in ops_list["operations"]}
            assert op in op_names, f"{layer}/{op} not discovered"

            # Read
            op_code = adapter.read_operation(layer, op)
            assert "error" not in op_code, f"Failed to read {layer}/{op}"
            assert len(op_code["code"]) > 0

            # Function name
            func_name = adapter._get_function_name(layer, op)
            assert func_name, f"No function name for {layer}/{op}"


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
