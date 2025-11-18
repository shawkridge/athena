"""SRT Executor for sandboxed code execution.

This module provides OS-level sandboxing via Anthropic's Sandbox Runtime (SRT).
Wraps code execution with filesystem and network isolation, violation monitoring,
and comprehensive security controls.

Reference: https://github.com/anthropics/srt
"""

import json
import logging
import os
import shutil
import subprocess
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List

from .config import SandboxConfig, SandboxMode, ExecutionLanguage

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Result of a sandboxed code execution.

    Attributes:
        success: Whether execution completed without errors
        stdout: Standard output captured during execution
        stderr: Standard error captured during execution
        exit_code: Process exit code (0 = success)
        execution_time_ms: Time taken to execute in milliseconds
        violations: List of security violations detected
        memory_used_mb: Peak memory usage in MB (if profiling enabled)
        sandbox_id: Unique identifier for this execution
        timestamp: When execution occurred
        error: Exception message if execution failed
    """

    success: bool
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    execution_time_ms: float = 0.0
    violations: List[str] = field(default_factory=list)
    memory_used_mb: float = 0.0
    sandbox_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "success": self.success,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "exit_code": self.exit_code,
            "execution_time_ms": self.execution_time_ms,
            "violations": self.violations,
            "memory_used_mb": self.memory_used_mb,
            "sandbox_id": self.sandbox_id,
            "timestamp": self.timestamp,
            "error": self.error,
        }


class SRTExecutor:
    """Execute code safely using Anthropic's Sandbox Runtime (SRT).

    Provides OS-level isolation with filesystem and network controls.
    Supports Python, JavaScript, and bash code execution.

    Example:
        config = SandboxConfig.default()
        executor = SRTExecutor(config)
        result = executor.execute("print('Hello from sandbox')")
        print(f"Success: {result.success}, Output: {result.stdout}")
    """

    def __init__(self, config: SandboxConfig):
        """Initialize SRT executor.

        Args:
            config: SandboxConfig instance with execution parameters

        Raises:
            RuntimeError: If SRT binary not found and config requires SRT mode
        """
        self.config = config
        self.srt_binary = self._detect_srt_binary()

        if config.mode == SandboxMode.SRT and not self.srt_binary:
            raise RuntimeError(
                "SRT binary not found. Install via: "
                "curl -fsSL https://github.com/anthropics/srt/releases/download/v0.1.0/srt-linux-x86_64 "
                "-o /usr/local/bin/srt && chmod +x /usr/local/bin/srt"
            )

        self.execution_count = 0
        self.temp_dir = tempfile.mkdtemp(prefix="srt_sandbox_")
        logger.info(f"SRTExecutor initialized with mode={config.mode}, temp_dir={self.temp_dir}")

    def _detect_srt_binary(self) -> Optional[str]:
        """Detect SRT binary location.

        Searches common installation paths:
        - /usr/local/bin/srt
        - /usr/bin/srt
        - ~/bin/srt
        - In PATH

        Returns:
            Path to srt binary or None if not found
        """
        candidates = [
            "/usr/local/bin/srt",
            "/usr/bin/srt",
            os.path.expanduser("~/bin/srt"),
            shutil.which("srt"),
        ]

        for candidate in candidates:
            if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                logger.debug(f"Found SRT binary at {candidate}")
                return candidate

        logger.warning("SRT binary not found in common paths")
        return None

    def execute(self, code: str, language: Optional[ExecutionLanguage] = None) -> ExecutionResult:
        """Execute code in sandbox.

        Args:
            code: Source code to execute
            language: Programming language (uses config default if not specified)

        Returns:
            ExecutionResult with output and metadata
        """
        import time

        start_time = time.time()

        language = language or self.config.language
        self.execution_count += 1
        sandbox_id = str(uuid.uuid4())

        try:
            # Write code to temp file
            code_file = self._write_code_file(code, language)

            # Execute based on mode
            if self.config.mode == SandboxMode.SRT:
                result = self._execute_with_srt(code_file, language, sandbox_id)
            elif self.config.mode == SandboxMode.RESTRICTED:
                result = self._execute_with_restricted(code, language, sandbox_id)
            else:  # MOCK
                result = self._execute_mock(code, sandbox_id)

            # Detect violations
            result.violations = self._detect_violations(result)
            result.execution_time_ms = (time.time() - start_time) * 1000
            result.sandbox_id = sandbox_id

            return result

        except Exception as e:
            return ExecutionResult(
                success=False,
                error=str(e),
                sandbox_id=sandbox_id,
                execution_time_ms=(time.time() - start_time) * 1000,
            )

    def _write_code_file(self, code: str, language: ExecutionLanguage) -> str:
        """Write code to temp file.

        Args:
            code: Source code
            language: Programming language

        Returns:
            Path to temp code file
        """
        ext = {
            ExecutionLanguage.PYTHON: ".py",
            ExecutionLanguage.JAVASCRIPT: ".js",
            ExecutionLanguage.BASH: ".sh",
        }.get(language, ".txt")

        code_file = os.path.join(self.temp_dir, f"code_{self.execution_count}{ext}")
        with open(code_file, "w") as f:
            f.write(code)

        if language == ExecutionLanguage.BASH:
            os.chmod(code_file, 0o755)

        return code_file

    def _execute_with_srt(
        self, code_file: str, language: ExecutionLanguage, sandbox_id: str
    ) -> ExecutionResult:
        """Execute code with SRT sandbox.

        Args:
            code_file: Path to code file
            language: Programming language
            sandbox_id: Unique execution ID

        Returns:
            ExecutionResult with output
        """
        # Create SRT config
        srt_config = self._generate_srt_config(sandbox_id)
        config_file = os.path.join(self.temp_dir, f"srt_config_{sandbox_id}.json")
        with open(config_file, "w") as f:
            json.dump(srt_config, f)

        # Determine command
        if language == ExecutionLanguage.PYTHON:
            cmd = ["python3", code_file]
        elif language == ExecutionLanguage.JAVASCRIPT:
            cmd = ["node", code_file]
        elif language == ExecutionLanguage.BASH:
            cmd = ["bash", code_file]
        else:
            raise ValueError(f"Unsupported language: {language}")

        # Execute with SRT
        try:
            result = subprocess.run(
                [self.srt_binary, "--settings", config_file, "--"] + cmd,
                cwd=self.config.working_directory or self.temp_dir,
                capture_output=True,
                text=True,
                timeout=self.config.timeout_seconds,
            )

            return ExecutionResult(
                success=result.returncode == 0,
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
            )
        except subprocess.TimeoutExpired:
            return ExecutionResult(
                success=False,
                stderr=f"Execution timeout after {self.config.timeout_seconds}s",
                exit_code=124,  # Standard timeout exit code
                error="TimeoutExpired",
            )

    def _execute_with_restricted(
        self, code: str, language: ExecutionLanguage, sandbox_id: str
    ) -> ExecutionResult:
        """Execute code with RestrictedPython (Python-only).

        Args:
            code: Source code
            language: Programming language
            sandbox_id: Unique execution ID

        Returns:
            ExecutionResult with output
        """
        if language != ExecutionLanguage.PYTHON:
            return ExecutionResult(
                success=False,
                error=f"RestrictedPython only supports Python, not {language}",
                sandbox_id=sandbox_id,
            )

        try:
            from RestrictedPython import compile_restricted

            # Compile restricted code
            compiled = compile_restricted(code, filename="<sandbox>", mode="exec")
            if compiled.errors:
                return ExecutionResult(
                    success=False,
                    error=f"Compilation errors: {compiled.errors}",
                    sandbox_id=sandbox_id,
                )

            # Create safe namespace
            safe_builtins = {
                "print": print,
                "len": len,
                "range": range,
                "str": str,
                "int": int,
                "float": float,
                "list": list,
                "dict": dict,
                "set": set,
                "sum": sum,
            }

            # Execute in restricted namespace
            import io
            import sys

            old_stdout = sys.stdout
            old_stderr = sys.stderr
            stdout_capture = io.StringIO()
            stderr_capture = io.StringIO()

            try:
                sys.stdout = stdout_capture
                sys.stderr = stderr_capture

                exec(compiled.code, {"__builtins__": safe_builtins})

                return ExecutionResult(
                    success=True,
                    stdout=stdout_capture.getvalue(),
                    stderr=stderr_capture.getvalue(),
                    exit_code=0,
                    sandbox_id=sandbox_id,
                )
            finally:
                sys.stdout = old_stdout
                sys.stderr = old_stderr

        except ImportError:
            return ExecutionResult(
                success=False,
                error="RestrictedPython not installed. Install via: pip install RestrictedPython",
                sandbox_id=sandbox_id,
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                error=str(e),
                sandbox_id=sandbox_id,
            )

    def _execute_mock(self, code: str, sandbox_id: str) -> ExecutionResult:
        """Execute in mock mode (no actual sandboxing, for testing).

        Args:
            code: Source code
            sandbox_id: Unique execution ID

        Returns:
            ExecutionResult with mock output
        """
        logger.info(f"Executing in MOCK mode (sandbox_id={sandbox_id})")

        # For testing, just return success
        return ExecutionResult(
            success=True,
            stdout="[Mock execution - no actual sandbox]",
            exit_code=0,
            sandbox_id=sandbox_id,
        )

    def _generate_srt_config(self, sandbox_id: str) -> Dict[str, Any]:
        """Generate SRT configuration.

        Args:
            sandbox_id: Unique execution ID

        Returns:
            Dictionary with SRT config parameters
        """
        return {
            "version": "0.1.0",
            "sandbox_id": sandbox_id,
            "resource_limits": {
                "timeout_seconds": self.config.timeout_seconds,
                "max_memory_mb": self.config.max_memory_mb,
                "max_processes": 10,
            },
            "filesystem": {
                "allow_read": True,
                "allow_write": True,
                "allowed_paths": [
                    self.temp_dir,
                    self.config.working_directory or "/tmp",
                ],
                "blocked_paths": [
                    os.path.expanduser("~/.ssh"),
                    os.path.expanduser("~/.aws"),
                    os.path.expanduser("~/.anthropic"),
                    "/etc/passwd",
                    "/etc/shadow",
                ],
            },
            "network": {
                "allow": self.config.allow_network,
                "allow_http": self.config.allow_outbound_http,
                "blocked_domains": self.config.blocked_domains,
            },
        }

    def _detect_violations(self, result: ExecutionResult) -> List[str]:
        """Detect security violations in execution output.

        Args:
            result: ExecutionResult from execution

        Returns:
            List of violation descriptions
        """
        violations = []

        # Check for permission errors
        if "Permission denied" in result.stderr:
            violations.append("Attempted unauthorized filesystem access")

        # Check for network errors (if network disabled)
        if not self.config.allow_network:
            if any(msg in result.stderr for msg in ["URLError", "ConnectionError", "refused"]):
                violations.append("Attempted network access (blocked)")

        # Check for subprocess escape attempts
        if "subprocess" in result.stderr.lower():
            violations.append("Potential subprocess escape attempt")

        # Check for eval/exec usage
        if any(
            msg in result.stderr for msg in ["NameError: name 'eval'", "NameError: name 'exec'"]
        ):
            violations.append("Attempted use of eval/exec (blocked)")

        return violations

    def cleanup(self) -> None:
        """Clean up temporary files and resources."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            logger.info(f"Cleaned up temp directory: {self.temp_dir}")

    def __del__(self):
        """Cleanup on deletion."""
        try:
            self.cleanup()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


class SRTExecutorPool:
    """Pool of SRT executors for efficient resource management.

    Reuses executor instances to avoid repeated initialization overhead.
    """

    def __init__(self, size: int = 5, config: Optional[SandboxConfig] = None):
        """Initialize executor pool.

        Args:
            size: Number of executors to maintain
            config: SandboxConfig template (cloned for each executor)
        """
        self.size = size
        self.config = config or SandboxConfig.default()
        self.executors = [SRTExecutor(self.config) for _ in range(size)]
        self.current_idx = 0

    def execute(self, code: str, language: Optional[ExecutionLanguage] = None) -> ExecutionResult:
        """Execute code using next available executor from pool.

        Args:
            code: Source code to execute
            language: Programming language

        Returns:
            ExecutionResult with output
        """
        executor = self.executors[self.current_idx % self.size]
        self.current_idx += 1
        return executor.execute(code, language)

    def cleanup(self) -> None:
        """Clean up all executors in pool."""
        for executor in self.executors:
            executor.cleanup()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()
