"""Unit tests for SRT executor implementation.

Tests core functionality:
- Executor initialization with config
- Code execution in different modes (SRT, Restricted, Mock)
- Violation detection
- Error handling and timeouts
- Pool-based execution
"""

import os
import tempfile
import time
import pytest

from athena.sandbox import (
    SRTExecutor,
    SRTExecutorPool,
    SandboxConfig,
    SandboxMode,
    ExecutionLanguage,
    ExecutionResult,
)


class TestExecutionResult:
    """Test ExecutionResult data class."""

    def test_execution_result_creation(self):
        """Test creating ExecutionResult."""
        result = ExecutionResult(
            success=True,
            stdout="Hello World",
            stderr="",
            exit_code=0,
            execution_time_ms=123.45,
        )

        assert result.success is True
        assert result.stdout == "Hello World"
        assert result.stderr == ""
        assert result.exit_code == 0
        assert result.execution_time_ms == 123.45

    def test_execution_result_to_dict(self):
        """Test converting ExecutionResult to dictionary."""
        result = ExecutionResult(
            success=True,
            stdout="output",
            stderr="error",
            exit_code=1,
        )

        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert result_dict["success"] is True
        assert result_dict["stdout"] == "output"
        assert result_dict["stderr"] == "error"
        assert result_dict["exit_code"] == 1
        assert "sandbox_id" in result_dict
        assert "timestamp" in result_dict

    def test_execution_result_defaults(self):
        """Test ExecutionResult default values."""
        result = ExecutionResult(success=False)

        assert result.stdout == ""
        assert result.stderr == ""
        assert result.violations == []
        assert result.memory_used_mb == 0.0
        assert result.sandbox_id is not None
        assert result.timestamp is not None


class TestSRTExecutorInitialization:
    """Test SRTExecutor initialization."""

    def test_executor_init_with_default_config(self):
        """Test executor initialization with default config."""
        config = SandboxConfig.default()
        executor = SRTExecutor(config)

        try:
            assert executor.config == config
            assert executor.execution_count == 0
            assert executor.temp_dir is not None
            assert os.path.isdir(executor.temp_dir)
        finally:
            executor.cleanup()

    def test_executor_init_with_mock_mode(self):
        """Test executor initialization with mock mode (no SRT required)."""
        config = SandboxConfig(mode=SandboxMode.MOCK)
        executor = SRTExecutor(config)

        try:
            assert executor.config.mode == SandboxMode.MOCK
            assert executor.execution_count == 0
        finally:
            executor.cleanup()

    def test_srt_binary_detection(self):
        """Test SRT binary detection."""
        config = SandboxConfig.default()
        executor = SRTExecutor(config)

        try:
            # srt_binary could be None if not installed
            # This is ok - we just verify detection doesn't crash
            assert executor.srt_binary is None or isinstance(executor.srt_binary, str)
        finally:
            executor.cleanup()


class TestSRTExecutorCodeExecution:
    """Test code execution functionality."""

    def test_execute_python_in_mock_mode(self):
        """Test executing Python code in mock mode."""
        config = SandboxConfig(mode=SandboxMode.MOCK)
        executor = SRTExecutor(config)

        try:
            result = executor.execute("print('Hello World')", ExecutionLanguage.PYTHON)

            assert result.success is True
            assert result.sandbox_id is not None
            assert result.execution_time_ms > 0
        finally:
            executor.cleanup()

    def test_execute_bash_in_mock_mode(self):
        """Test executing bash code in mock mode."""
        config = SandboxConfig(mode=SandboxMode.MOCK)
        executor = SRTExecutor(config)

        try:
            result = executor.execute("echo 'test'", ExecutionLanguage.BASH)

            assert result.success is True
            assert result.sandbox_id is not None
        finally:
            executor.cleanup()

    def test_execution_tracking(self):
        """Test execution count tracking."""
        config = SandboxConfig(mode=SandboxMode.MOCK)
        executor = SRTExecutor(config)

        try:
            assert executor.execution_count == 0

            executor.execute("print('test')")
            assert executor.execution_count == 1

            executor.execute("echo 'test'")
            assert executor.execution_count == 2
        finally:
            executor.cleanup()

    def test_execution_result_metadata(self):
        """Test that execution results contain required metadata."""
        config = SandboxConfig(mode=SandboxMode.MOCK)
        executor = SRTExecutor(config)

        try:
            result = executor.execute("print('test')")

            assert result.sandbox_id is not None
            assert len(result.sandbox_id) > 0
            assert result.timestamp is not None
            assert result.execution_time_ms >= 0
        finally:
            executor.cleanup()


class TestRestrictedPythonExecution:
    """Test RestrictedPython execution mode."""

    def test_restricted_python_simple_print(self):
        """Test simple print in restricted mode."""
        try:
            from RestrictedPython import compile_restricted
            has_restricted_python = True
        except ImportError:
            has_restricted_python = False

        if not has_restricted_python:
            pytest.skip("RestrictedPython not installed")

        config = SandboxConfig(mode=SandboxMode.RESTRICTED)
        executor = SRTExecutor(config)

        try:
            result = executor.execute("print('Hello Restricted')")

            assert result.success is True
            assert "Hello Restricted" in result.stdout
        finally:
            executor.cleanup()

    def test_restricted_python_math(self):
        """Test math operations in restricted mode."""
        try:
            from RestrictedPython import compile_restricted
            has_restricted_python = True
        except ImportError:
            has_restricted_python = False

        if not has_restricted_python:
            pytest.skip("RestrictedPython not installed")

        config = SandboxConfig(mode=SandboxMode.RESTRICTED)
        executor = SRTExecutor(config)

        try:
            result = executor.execute("print(2 + 2)")

            assert result.success is True
            assert "4" in result.stdout
        finally:
            executor.cleanup()

    def test_restricted_python_blocks_non_python(self):
        """Test that restricted mode rejects non-Python code."""
        try:
            from RestrictedPython import compile_restricted
            has_restricted_python = True
        except ImportError:
            has_restricted_python = False

        if not has_restricted_python:
            pytest.skip("RestrictedPython not installed")

        config = SandboxConfig(mode=SandboxMode.RESTRICTED)
        executor = SRTExecutor(config)

        try:
            result = executor.execute("echo 'test'", ExecutionLanguage.BASH)

            assert result.success is False
            assert "RestrictedPython only supports Python" in result.error
        finally:
            executor.cleanup()


class TestSRTConfigGeneration:
    """Test SRT configuration generation."""

    def test_generate_srt_config(self):
        """Test SRT config generation."""
        config = SandboxConfig.default()
        executor = SRTExecutor(config)

        try:
            srt_config = executor._generate_srt_config("test-sandbox-123")

            assert srt_config["version"] == "0.1.0"
            assert srt_config["sandbox_id"] == "test-sandbox-123"
            assert "resource_limits" in srt_config
            assert "filesystem" in srt_config
            assert "network" in srt_config
        finally:
            executor.cleanup()

    def test_srt_config_resource_limits(self):
        """Test resource limits in SRT config."""
        config = SandboxConfig(timeout_seconds=45, max_memory_mb=512)
        executor = SRTExecutor(config)

        try:
            srt_config = executor._generate_srt_config("test-123")
            limits = srt_config["resource_limits"]

            assert limits["timeout_seconds"] == 45
            assert limits["max_memory_mb"] == 512
        finally:
            executor.cleanup()

    def test_srt_config_filesystem_rules(self):
        """Test filesystem rules in SRT config."""
        config = SandboxConfig.default()
        executor = SRTExecutor(config)

        try:
            srt_config = executor._generate_srt_config("test-123")
            fs_config = srt_config["filesystem"]

            assert fs_config["allow_read"] is True
            assert fs_config["allow_write"] is True
            assert "blocked_paths" in fs_config
            assert any("ssh" in path.lower() for path in fs_config["blocked_paths"])
        finally:
            executor.cleanup()

    def test_srt_config_network_rules(self):
        """Test network rules in SRT config."""
        config = SandboxConfig(allow_network=False)
        executor = SRTExecutor(config)

        try:
            srt_config = executor._generate_srt_config("test-123")
            net_config = srt_config["network"]

            assert net_config["allow"] is False
        finally:
            executor.cleanup()


class TestViolationDetection:
    """Test security violation detection."""

    def test_detect_no_violations(self):
        """Test detection when no violations occur."""
        config = SandboxConfig(mode=SandboxMode.MOCK)
        executor = SRTExecutor(config)

        try:
            result = ExecutionResult(
                success=True,
                stdout="normal output",
                stderr="",
                exit_code=0,
            )

            violations = executor._detect_violations(result)
            assert violations == []
        finally:
            executor.cleanup()

    def test_detect_permission_violation(self):
        """Test detection of permission denied errors."""
        config = SandboxConfig(mode=SandboxMode.MOCK)
        executor = SRTExecutor(config)

        try:
            result = ExecutionResult(
                success=False,
                stdout="",
                stderr="Permission denied: /etc/passwd",
                exit_code=1,
            )

            violations = executor._detect_violations(result)
            assert len(violations) > 0
            assert any("permission" in v.lower() for v in violations)
        finally:
            executor.cleanup()

    def test_detect_network_violation(self):
        """Test detection of network access when disabled."""
        config = SandboxConfig(mode=SandboxMode.MOCK, allow_network=False)
        executor = SRTExecutor(config)

        try:
            result = ExecutionResult(
                success=False,
                stdout="",
                stderr="URLError: connection refused",
                exit_code=1,
            )

            violations = executor._detect_violations(result)
            assert len(violations) > 0
            assert any("network" in v.lower() for v in violations)
        finally:
            executor.cleanup()


class TestSRTExecutorPool:
    """Test executor pool functionality."""

    def test_pool_initialization(self):
        """Test pool initialization."""
        config = SandboxConfig.default()
        pool = SRTExecutorPool(size=3, config=config)

        try:
            assert len(pool.executors) == 3
            assert all(isinstance(e, SRTExecutor) for e in pool.executors)
        finally:
            pool.cleanup()

    def test_pool_execute(self):
        """Test executing with pool."""
        config = SandboxConfig(mode=SandboxMode.MOCK)
        pool = SRTExecutorPool(size=2, config=config)

        try:
            result = pool.execute("print('test')")

            assert result.success is True
            assert result.sandbox_id is not None
        finally:
            pool.cleanup()

    def test_pool_round_robin(self):
        """Test that pool distributes work round-robin."""
        config = SandboxConfig(mode=SandboxMode.MOCK)
        pool = SRTExecutorPool(size=2, config=config)

        try:
            # Execute 4 times with 2 executors
            for _ in range(4):
                pool.execute("print('test')")

            # Each executor should be used twice (round-robin)
            assert pool.executors[0].execution_count == 2
            assert pool.executors[1].execution_count == 2
        finally:
            pool.cleanup()

    def test_pool_context_manager(self):
        """Test pool as context manager."""
        config = SandboxConfig(mode=SandboxMode.MOCK)

        with SRTExecutorPool(size=2, config=config) as pool:
            result = pool.execute("print('test')")
            assert result.success is True


class TestSandboxConfigValidation:
    """Test sandbox configuration validation."""

    def test_default_config_validates(self):
        """Test that default config is valid."""
        config = SandboxConfig.default()
        is_valid, errors = config.validate()

        assert is_valid is True
        assert len(errors) == 0

    def test_strict_config_validates(self):
        """Test that strict config is valid."""
        config = SandboxConfig.strict()
        is_valid, errors = config.validate()

        assert is_valid is True
        assert len(errors) == 0

    def test_permissive_config_validates(self):
        """Test that permissive config is valid."""
        config = SandboxConfig.permissive()
        is_valid, errors = config.validate()

        assert is_valid is True
        assert len(errors) == 0

    def test_invalid_timeout(self):
        """Test validation catches invalid timeout."""
        config = SandboxConfig(timeout_seconds=0)
        is_valid, errors = config.validate()

        assert is_valid is False
        assert any("timeout" in error.lower() for error in errors)

    def test_invalid_memory(self):
        """Test validation catches invalid memory."""
        config = SandboxConfig(max_memory_mb=16)  # Too small
        is_valid, errors = config.validate()

        assert is_valid is False
        assert any("memory" in error.lower() for error in errors)


class TestCodeFileCreation:
    """Test code file writing for execution."""

    def test_write_python_code_file(self):
        """Test writing Python code file."""
        config = SandboxConfig.default()
        executor = SRTExecutor(config)

        try:
            code_file = executor._write_code_file("print('test')", ExecutionLanguage.PYTHON)

            assert os.path.isfile(code_file)
            assert code_file.endswith(".py")

            with open(code_file, "r") as f:
                content = f.read()
            assert content == "print('test')"
        finally:
            executor.cleanup()

    def test_write_bash_code_file(self):
        """Test writing bash code file with executable permission."""
        config = SandboxConfig.default()
        executor = SRTExecutor(config)

        try:
            code_file = executor._write_code_file("echo test", ExecutionLanguage.BASH)

            assert os.path.isfile(code_file)
            assert code_file.endswith(".sh")
            assert os.access(code_file, os.X_OK)  # Check executable
        finally:
            executor.cleanup()

    def test_write_javascript_code_file(self):
        """Test writing JavaScript code file."""
        config = SandboxConfig.default()
        executor = SRTExecutor(config)

        try:
            code_file = executor._write_code_file("console.log('test')", ExecutionLanguage.JAVASCRIPT)

            assert os.path.isfile(code_file)
            assert code_file.endswith(".js")
        finally:
            executor.cleanup()


class TestExecutorCleanup:
    """Test executor cleanup and resource management."""

    def test_cleanup_removes_temp_dir(self):
        """Test that cleanup removes temporary directory."""
        config = SandboxConfig.default()
        executor = SRTExecutor(config)
        temp_dir = executor.temp_dir

        assert os.path.isdir(temp_dir)
        executor.cleanup()
        assert not os.path.exists(temp_dir)

    def test_cleanup_idempotent(self):
        """Test that cleanup can be called multiple times safely."""
        config = SandboxConfig.default()
        executor = SRTExecutor(config)

        executor.cleanup()
        executor.cleanup()  # Should not raise error

    def test_cleanup_on_del(self):
        """Test that cleanup happens on deletion."""
        config = SandboxConfig.default()
        executor = SRTExecutor(config)
        temp_dir = executor.temp_dir

        del executor

        # Give a moment for cleanup
        time.sleep(0.1)
        # Directory should be cleaned up
        assert not os.path.exists(temp_dir)


# Integration tests
class TestSRTIntegration:
    """Integration tests for SRT functionality."""

    def test_full_execution_workflow(self):
        """Test complete execution workflow."""
        config = SandboxConfig.default()
        executor = SRTExecutor(config)

        try:
            code = """
result = sum([1, 2, 3, 4, 5])
print(f"Sum: {result}")
"""
            result = executor.execute(code, ExecutionLanguage.PYTHON)

            # In mock mode, should succeed
            assert result.success is True
            assert result.sandbox_id is not None
            assert result.execution_time_ms > 0
        finally:
            executor.cleanup()

    def test_execution_isolation(self):
        """Test that executions are isolated."""
        config = SandboxConfig(mode=SandboxMode.MOCK)
        executor = SRTExecutor(config)

        try:
            result1 = executor.execute("code1", ExecutionLanguage.PYTHON)
            result2 = executor.execute("code2", ExecutionLanguage.PYTHON)

            # Each should have unique sandbox_id
            assert result1.sandbox_id != result2.sandbox_id
        finally:
            executor.cleanup()

    def test_different_languages(self):
        """Test execution with different languages."""
        config = SandboxConfig(mode=SandboxMode.MOCK)
        executor = SRTExecutor(config)

        try:
            for language in [ExecutionLanguage.PYTHON, ExecutionLanguage.BASH, ExecutionLanguage.JAVASCRIPT]:
                result = executor.execute("test code", language)
                assert result.success is True
        finally:
            executor.cleanup()
