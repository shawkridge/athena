"""
Unit tests for Filesystem API infrastructure.

Tests the code executor, manager, and router components.
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from athena.execution.code_executor import CodeExecutor, ResultFormatter, ExecutionResult
from athena.filesystem_api.manager import FilesystemAPIManager
from athena.mcp.filesystem_api_router import FilesystemAPIRouter


class TestCodeExecutor:
    """Test code execution engine."""

    def test_executor_initialization(self, tmp_path):
        """Test executor can be initialized."""
        executor = CodeExecutor(tmp_path)
        assert executor.filesystem_root == tmp_path

    def test_module_loading(self, tmp_path):
        """Test loading and executing a module."""
        # Create a test module
        module_dir = tmp_path / "test_module"
        module_dir.mkdir()

        module_file = module_dir / "test.py"
        module_file.write_text("""
def add(a, b):
    '''Add two numbers.'''
    return a + b

def multiply(a, b):
    '''Multiply two numbers.'''
    return a * b
""")

        executor = CodeExecutor(tmp_path)

        # Test execution
        result = executor.execute(
            "test_module/test.py",
            "add",
            {"a": 2, "b": 3}
        )

        assert result.success
        assert result.result == 5
        assert result.error is None

    def test_function_not_found(self, tmp_path):
        """Test error when function doesn't exist."""
        module_dir = tmp_path / "test_module"
        module_dir.mkdir()

        module_file = module_dir / "test.py"
        module_file.write_text("def exists(): return True")

        executor = CodeExecutor(tmp_path)
        result = executor.execute(
            "test_module/test.py",
            "nonexistent",
            {}
        )

        assert not result.success
        assert "not found" in result.error.lower()
        assert result.error_type == "FunctionNotFound"

    def test_module_caching(self, tmp_path):
        """Test that modules are cached."""
        module_dir = tmp_path / "test_module"
        module_dir.mkdir()

        module_file = module_dir / "test.py"
        module_file.write_text("def get_value(): return 42")

        executor = CodeExecutor(tmp_path)

        # First execution
        result1 = executor.execute("test_module/test.py", "get_value", {})
        assert result1.success

        # Verify cache is populated
        assert len(executor._module_cache) > 0

        # Second execution should use cache
        result2 = executor.execute("test_module/test.py", "get_value", {})
        assert result2.success
        assert result2.result == 42

    def test_execution_error_handling(self, tmp_path):
        """Test error handling in execution."""
        module_dir = tmp_path / "test_module"
        module_dir.mkdir()

        module_file = module_dir / "test.py"
        module_file.write_text("""
def error_function():
    raise ValueError("Test error")
""")

        executor = CodeExecutor(tmp_path)
        result = executor.execute(
            "test_module/test.py",
            "error_function",
            {}
        )

        assert not result.success
        assert "Test error" in result.error
        assert result.error_type == "ValueError"
        assert result.traceback_str is not None

    def test_function_signature_introspection(self, tmp_path):
        """Test getting function signatures."""
        module_dir = tmp_path / "test_module"
        module_dir.mkdir()

        module_file = module_dir / "test.py"
        module_file.write_text("""
def my_function(a: int, b: str = "default") -> bool:
    '''Test function with signature.'''
    return True
""")

        executor = CodeExecutor(tmp_path)
        sig = executor.get_module_signature(
            "test_module/test.py",
            "my_function"
        )

        assert sig is not None
        assert "parameters" in sig
        assert "a" in sig["parameters"]
        assert "docstring" in sig


class TestResultFormatter:
    """Test result formatting."""

    def test_format_success_result(self):
        """Test formatting successful result."""
        result = ExecutionResult(
            success=True,
            result={"count": 10, "items": [1, 2, 3]},
            execution_time_ms=150.5
        )

        formatted = ResultFormatter.format_result(result)

        assert formatted["status"] == "success"
        assert formatted["result"]["count"] == 10
        assert formatted["execution_time_ms"] == 150.5

    def test_format_error_result(self):
        """Test formatting error result."""
        result = ExecutionResult(
            success=False,
            result=None,
            error="Something went wrong",
            error_type="RuntimeError",
            execution_time_ms=25.0
        )

        formatted = ResultFormatter.format_result(result)

        assert formatted["status"] == "error"
        assert formatted["error"] == "Something went wrong"
        assert formatted["error_type"] == "RuntimeError"

    def test_token_estimation(self):
        """Test token estimation."""
        result = {
            "items": ["a", "b", "c"],
            "count": 3,
            "metadata": {"key": "value"}
        }

        tokens = ResultFormatter.estimate_tokens(result)

        # Should be roughly json length / 4
        assert tokens > 0
        assert isinstance(tokens, int)


class TestFilesystemAPIManager:
    """Test filesystem API manager."""

    def test_manager_initialization(self, tmp_path):
        """Test manager can be initialized."""
        manager = FilesystemAPIManager(tmp_path)
        assert manager.root_path == tmp_path

    def test_list_directory(self, tmp_path):
        """Test listing directory contents."""
        # Create test structure
        layers_dir = tmp_path / "layers"
        layers_dir.mkdir()

        episodic_dir = layers_dir / "episodic"
        episodic_dir.mkdir()

        (episodic_dir / "search.py").write_text("# search module")

        manager = FilesystemAPIManager(tmp_path)
        result = manager.list_directory("layers")

        assert result["type"] == "directory"
        assert len(result["contents"]) > 0
        assert any(c["name"] == "episodic" for c in result["contents"])

    def test_read_file(self, tmp_path):
        """Test reading a file."""
        # Create test file
        test_dir = tmp_path / "test"
        test_dir.mkdir()

        test_file = test_dir / "example.py"
        test_content = "def hello():\n    return 'world'"
        test_file.write_text(test_content)

        manager = FilesystemAPIManager(tmp_path)
        result = manager.read_file("test/example.py")

        assert result["type"] == "file"
        assert result["content"] == test_content
        assert result["size_bytes"] == len(test_content)

    def test_file_not_found(self, tmp_path):
        """Test reading non-existent file."""
        manager = FilesystemAPIManager(tmp_path)
        result = manager.read_file("nonexistent/file.py")

        assert "error" in result
        assert "not found" in result["error"].lower()


class TestFilesystemAPIRouter:
    """Test MCP handler router."""

    @patch('athena.mcp.filesystem_api_router.FilesystemAPIRouter._get_db_path')
    def test_router_initialization(self, mock_db):
        """Test router can be initialized."""
        mock_db.return_value = "~/.athena/memory.db"
        router = FilesystemAPIRouter()
        assert router.executor is not None
        assert router.fs_manager is not None

    @patch('athena.execution.code_executor.CodeExecutor.execute')
    @patch('athena.mcp.filesystem_api_router.FilesystemAPIRouter._get_db_path')
    def test_episodic_search_route(self, mock_db, mock_execute):
        """Test routing episodic search."""
        mock_db.return_value = "~/.athena/memory.db"

        mock_result = ExecutionResult(
            success=True,
            result={"total": 10, "matches": []},
            execution_time_ms=100
        )
        mock_execute.return_value = mock_result

        router = FilesystemAPIRouter()
        result = router.route_episodic_search("test query")

        assert result["status"] == "success"
        mock_execute.assert_called_once()

    @patch('athena.execution.code_executor.CodeExecutor.execute')
    @patch('athena.mcp.filesystem_api_router.FilesystemAPIRouter._get_db_path')
    def test_semantic_search_route(self, mock_db, mock_execute):
        """Test routing semantic search."""
        mock_db.return_value = "~/.athena/memory.db"

        mock_result = ExecutionResult(
            success=True,
            result={"total": 20, "confidence": 0.85},
            execution_time_ms=150
        )
        mock_execute.return_value = mock_result

        router = FilesystemAPIRouter()
        result = router.route_semantic_search("test query")

        assert result["status"] == "success"

    @patch('athena.mcp.filesystem_api_router.FilesystemAPIRouter._get_db_path')
    def test_get_api_schema(self, mock_db):
        """Test getting API schema."""
        mock_db.return_value = "~/.athena/memory.db"

        router = FilesystemAPIRouter()
        schema = router.get_api_schema()

        assert "version" in schema
        assert "paradigm" in schema
        assert schema["paradigm"] == "code_execution"


class TestIntegration:
    """Integration tests."""

    def test_end_to_end_search_operation(self, tmp_path):
        """Test complete search workflow."""
        # Create filesystem structure
        layers_dir = tmp_path / "layers"
        layers_dir.mkdir()

        episodic_dir = layers_dir / "episodic"
        episodic_dir.mkdir()

        search_file = episodic_dir / "search.py"
        search_file.write_text("""
def search_events(db_path: str, query: str, limit: int = 100, confidence_threshold: float = 0.7):
    '''Search episodic events.'''
    return {
        "query": query,
        "total_found": 42,
        "high_confidence_count": 38,
        "avg_confidence": 0.84,
        "top_3_ids": ["evt_1", "evt_2", "evt_3"]
    }
""")

        # Execute
        executor = CodeExecutor(tmp_path)
        result = executor.execute(
            "layers/episodic/search.py",
            "search_events",
            {
                "db_path": "~/.athena/memory.db",
                "query": "authentication"
            }
        )

        # Verify
        assert result.success
        assert result.result["total_found"] == 42
        assert result.result["high_confidence_count"] == 38

    def test_discovery_and_execution_workflow(self, tmp_path):
        """Test complete discovery + execution workflow."""
        # Create structure
        layers_dir = tmp_path / "layers"
        layers_dir.mkdir()

        semantic_dir = layers_dir / "semantic"
        semantic_dir.mkdir()

        (semantic_dir / "recall.py").write_text("""
def search_memories(db_path: str, query: str, limit: int = 100):
    '''Search semantic memories.'''
    return {"query": query, "results": 25, "confidence": 0.82}
""")

        # Discover
        manager = FilesystemAPIManager(tmp_path)
        contents = manager.list_directory("layers/semantic")

        assert any(f["name"] == "recall.py" for f in contents["contents"])

        # Read
        file_info = manager.read_file("layers/semantic/recall.py")
        assert "search_memories" in file_info["content"]

        # Execute
        executor = CodeExecutor(tmp_path)
        result = executor.execute(
            "layers/semantic/recall.py",
            "search_memories",
            {"db_path": "test.db", "query": "auth"}
        )

        assert result.success
        assert result.result["results"] == 25


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
