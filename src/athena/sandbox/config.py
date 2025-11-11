"""Sandbox configuration for secure code execution.

This module defines configuration models for sandboxed code execution.
Supports both Anthropic's SRT (Secure Runtime) and restricted Python
execution modes with configurable resource limits and security policies.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Set, Dict, Any

logger = logging.getLogger(__name__)


class SandboxMode(str, Enum):
    """Sandbox execution mode."""

    SRT = "srt"  # Anthropic's Secure Runtime (OS-level isolation)
    RESTRICTED = "restricted"  # RestrictedPython (Python-level restrictions)
    MOCK = "mock"  # Mock mode for testing (no actual isolation)


class ExecutionLanguage(str, Enum):
    """Supported code execution languages."""

    PYTHON = "python"
    JAVASCRIPT = "javascript"
    BASH = "bash"


@dataclass
class SandboxResourceLimits:
    """Resource limits for sandboxed execution.

    Prevents resource exhaustion attacks and runaway processes.
    """

    # CPU and memory limits
    timeout_seconds: int = 30  # Maximum execution time
    max_memory_mb: int = 256  # Maximum memory usage
    max_cpu_percent: float = 90.0  # Maximum CPU usage percentage

    # File system limits
    max_file_size_mb: int = 10  # Maximum single file size
    max_total_files: int = 100  # Maximum files in sandbox
    max_disk_space_mb: int = 500  # Maximum total disk usage

    # Network limits
    allow_network: bool = False  # Allow network access
    allow_outbound_http: bool = False  # Allow HTTP/HTTPS requests
    blocked_domains: List[str] = field(default_factory=list)

    # Process limits
    max_processes: int = 10  # Maximum subprocess count
    allow_shell_escape: bool = False  # Allow shell execution

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timeout_seconds": self.timeout_seconds,
            "max_memory_mb": self.max_memory_mb,
            "max_cpu_percent": self.max_cpu_percent,
            "max_file_size_mb": self.max_file_size_mb,
            "max_total_files": self.max_total_files,
            "max_disk_space_mb": self.max_disk_space_mb,
            "allow_network": self.allow_network,
            "allow_outbound_http": self.allow_outbound_http,
            "blocked_domains": self.blocked_domains,
            "max_processes": self.max_processes,
            "allow_shell_escape": self.allow_shell_escape,
        }


@dataclass
class SandboxSecurityPolicy:
    """Security policy for sandboxed execution.

    Defines what operations are allowed/blocked in sandbox.
    """

    # File system access
    allow_read: bool = True
    allow_write: bool = True
    allow_delete: bool = False
    allowed_paths: List[str] = field(default_factory=lambda: ["/tmp", "/home"])
    blocked_paths: List[str] = field(default_factory=lambda: ["/etc", "/sys", "/proc"])

    # Module/import restrictions
    allowed_modules: Set[str] = field(default_factory=lambda: {
        "os", "sys", "pathlib", "datetime", "json", "re", "typing", "dataclasses"
    })
    blocked_modules: Set[str] = field(default_factory=lambda: {
        "subprocess", "socket", "requests", "urllib", "ssl", "paramiko"
    })

    # Built-in function restrictions
    allowed_builtins: Set[str] = field(default_factory=lambda: {
        "len", "str", "int", "float", "list", "dict", "set", "tuple",
        "sorted", "sum", "min", "max", "abs", "round", "enumerate",
        "zip", "map", "filter", "range", "reversed"
    })
    blocked_builtins: Set[str] = field(default_factory=lambda: {
        "exec", "eval", "compile", "__import__", "open", "input"
    })

    # Dynamic code execution
    allow_eval: bool = False
    allow_exec: bool = False
    allow_import_dynamic: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "allow_read": self.allow_read,
            "allow_write": self.allow_write,
            "allow_delete": self.allow_delete,
            "allowed_paths": self.allowed_paths,
            "blocked_paths": self.blocked_paths,
            "allowed_modules": list(self.allowed_modules),
            "blocked_modules": list(self.blocked_modules),
            "allowed_builtins": list(self.allowed_builtins),
            "blocked_builtins": list(self.blocked_builtins),
            "allow_eval": self.allow_eval,
            "allow_exec": self.allow_exec,
            "allow_import_dynamic": self.allow_import_dynamic,
        }


@dataclass
class SandboxConfig:
    """Configuration for sandboxed code execution.

    Example:
        config = SandboxConfig(
            mode=SandboxMode.SRT,
            language=ExecutionLanguage.PYTHON,
            timeout_seconds=30,
            allow_network=False
        )

        limits = config.get_resource_limits()
        policy = config.get_security_policy()
    """

    # Core settings
    mode: SandboxMode = SandboxMode.SRT
    language: ExecutionLanguage = ExecutionLanguage.PYTHON
    version: str = "1.0"

    # Resource limits
    timeout_seconds: int = 30
    max_memory_mb: int = 256
    max_cpu_percent: float = 90.0

    # File system
    max_file_size_mb: int = 10
    max_total_files: int = 100
    max_disk_space_mb: int = 500

    # Network
    allow_network: bool = False
    allow_outbound_http: bool = False
    blocked_domains: List[str] = field(default_factory=list)

    # Security
    allow_eval: bool = False
    allow_exec: bool = False
    allow_import_dynamic: bool = False

    # Execution context
    working_directory: Optional[str] = None
    environment_vars: Dict[str, str] = field(default_factory=dict)
    expose_apis: List[str] = field(default_factory=lambda: ["memory_api"])

    # Features
    capture_output: bool = True
    capture_errors: bool = True
    enable_profiling: bool = False
    enable_tracing: bool = False

    # Metadata
    sandbox_id: Optional[str] = None
    creator: Optional[str] = None
    purpose: str = "Code execution"
    description: str = ""

    def get_resource_limits(self) -> SandboxResourceLimits:
        """Get resource limits configuration.

        Returns:
            SandboxResourceLimits with configured values
        """
        return SandboxResourceLimits(
            timeout_seconds=self.timeout_seconds,
            max_memory_mb=self.max_memory_mb,
            max_cpu_percent=self.max_cpu_percent,
            max_file_size_mb=self.max_file_size_mb,
            max_total_files=self.max_total_files,
            max_disk_space_mb=self.max_disk_space_mb,
            allow_network=self.allow_network,
            allow_outbound_http=self.allow_outbound_http,
            blocked_domains=self.blocked_domains,
        )

    def get_security_policy(self) -> SandboxSecurityPolicy:
        """Get security policy configuration.

        Returns:
            SandboxSecurityPolicy with configured values
        """
        return SandboxSecurityPolicy(
            allow_eval=self.allow_eval,
            allow_exec=self.allow_exec,
            allow_import_dynamic=self.allow_import_dynamic,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "mode": self.mode.value,
            "language": self.language.value,
            "version": self.version,
            "timeout_seconds": self.timeout_seconds,
            "max_memory_mb": self.max_memory_mb,
            "max_cpu_percent": self.max_cpu_percent,
            "max_file_size_mb": self.max_file_size_mb,
            "max_total_files": self.max_total_files,
            "max_disk_space_mb": self.max_disk_space_mb,
            "allow_network": self.allow_network,
            "allow_outbound_http": self.allow_outbound_http,
            "blocked_domains": self.blocked_domains,
            "allow_eval": self.allow_eval,
            "allow_exec": self.allow_exec,
            "allow_import_dynamic": self.allow_import_dynamic,
            "working_directory": self.working_directory,
            "environment_vars": self.environment_vars,
            "expose_apis": self.expose_apis,
            "capture_output": self.capture_output,
            "capture_errors": self.capture_errors,
            "enable_profiling": self.enable_profiling,
            "enable_tracing": self.enable_tracing,
            "sandbox_id": self.sandbox_id,
            "creator": self.creator,
            "purpose": self.purpose,
            "description": self.description,
        }

    @staticmethod
    def strict() -> "SandboxConfig":
        """Create strict sandbox configuration (most restrictive).

        Returns:
            SandboxConfig with maximum security
        """
        return SandboxConfig(
            mode=SandboxMode.SRT,
            timeout_seconds=10,
            max_memory_mb=128,
            allow_network=False,
            allow_eval=False,
            allow_exec=False,
            allow_import_dynamic=False,
            purpose="Strict execution",
        )

    @staticmethod
    def permissive() -> "SandboxConfig":
        """Create permissive sandbox configuration (developer mode).

        Returns:
            SandboxConfig with relaxed security for development
        """
        return SandboxConfig(
            mode=SandboxMode.RESTRICTED,
            timeout_seconds=60,
            max_memory_mb=512,
            allow_network=True,
            allow_outbound_http=True,
            allow_eval=False,
            allow_exec=False,
            purpose="Development/testing",
        )

    @staticmethod
    def default() -> "SandboxConfig":
        """Create default balanced sandbox configuration.

        Returns:
            SandboxConfig with balanced security/usability
        """
        return SandboxConfig(
            mode=SandboxMode.SRT,
            timeout_seconds=30,
            max_memory_mb=256,
            allow_network=False,
            allow_eval=False,
            allow_exec=False,
            purpose="Standard execution",
        )

    def validate(self) -> tuple[bool, List[str]]:
        """Validate configuration for consistency and safety.

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Timeout validation
        if self.timeout_seconds < 1:
            errors.append("timeout_seconds must be >= 1")
        if self.timeout_seconds > 3600:
            errors.append("timeout_seconds must be <= 3600 (1 hour)")

        # Memory validation
        if self.max_memory_mb < 32:
            errors.append("max_memory_mb must be >= 32 MB")
        if self.max_memory_mb > 8192:
            errors.append("max_memory_mb must be <= 8192 MB")

        # CPU validation
        if not 0 < self.max_cpu_percent <= 100:
            errors.append("max_cpu_percent must be between 0 and 100")

        # File limits validation
        if self.max_file_size_mb < 1:
            errors.append("max_file_size_mb must be >= 1")
        if self.max_disk_space_mb < self.max_file_size_mb:
            errors.append("max_disk_space_mb must be >= max_file_size_mb")

        # SRT mode validation
        if self.mode == SandboxMode.SRT:
            if self.allow_exec:
                errors.append("allow_exec=True not recommended with SRT mode")

        return len(errors) == 0, errors
