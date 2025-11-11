"""Sandbox configuration and execution environment.

This module provides sandboxing capabilities for safe code execution
using Anthropic's SRT (Secure Runtime) or restricted Python execution.
"""

from .config import (
    SandboxConfig,
    SandboxMode,
    SandboxResourceLimits,
    SandboxSecurityPolicy,
    ExecutionLanguage,
)
from .srt_executor import SRTExecutor, SRTExecutorPool, ExecutionResult
from .srt_config import (
    SRTConfigManager,
    SRTPolicy,
    FilesystemRule,
    NetworkRule,
    FilesystemAccessMode,
    NetworkAccessMode,
    STRICT_POLICY,
    RESEARCH_POLICY,
    DEVELOPMENT_POLICY,
)

__all__ = [
    # Configuration
    "SandboxConfig",
    "SandboxMode",
    "SandboxResourceLimits",
    "SandboxSecurityPolicy",
    "ExecutionLanguage",
    # Execution
    "SRTExecutor",
    "SRTExecutorPool",
    "ExecutionResult",
    # Advanced configuration
    "SRTConfigManager",
    "SRTPolicy",
    "FilesystemRule",
    "NetworkRule",
    "FilesystemAccessMode",
    "NetworkAccessMode",
    # Preset policies
    "STRICT_POLICY",
    "RESEARCH_POLICY",
    "DEVELOPMENT_POLICY",
]
