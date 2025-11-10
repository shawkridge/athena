"""Base class and interfaces for modular MCP tools."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Optional, Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)


class ToolStatus(str, Enum):
    """Tool execution status."""
    SUCCESS = "success"
    ERROR = "error"
    PARTIAL = "partial"
    TIMEOUT = "timeout"


@dataclass
class ToolResult:
    """Result of tool execution."""
    status: ToolStatus
    data: Any = None
    error: Optional[str] = None
    message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """Convert result to dictionary."""
        return {
            "status": self.status.value,
            "data": self.data,
            "error": self.error,
            "message": self.message,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }


def create_success_result(data: Any = None, **kwargs) -> ToolResult:
    """Create success result."""
    return ToolResult(status=ToolStatus.SUCCESS, data=data, **kwargs)


def create_error_result(error: str, **kwargs) -> ToolResult:
    """Create error result."""
    return ToolResult(status=ToolStatus.ERROR, error=error, **kwargs)


# Attach factory methods to class
ToolResult.success = staticmethod(create_success_result)
ToolResult.error = staticmethod(create_error_result)


@dataclass
class ToolMetadata:
    """Metadata for tool discovery and documentation."""
    name: str
    description: str
    category: str
    version: str = "1.0"
    author: str = "Athena"
    parameters: Dict[str, Any] = field(default_factory=dict)
    returns: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    deprecated: bool = False
    examples: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert metadata to dictionary."""
        return asdict(self)


class BaseTool(ABC):
    """Base class for all modular MCP tools."""

    def __init__(self, metadata: ToolMetadata):
        """Initialize tool with metadata.

        Args:
            metadata: Tool metadata for discovery and documentation
        """
        self.metadata = metadata
        self.logger = logging.getLogger(f"athena.tools.{metadata.name}")

    @abstractmethod
    async def execute(self, **params) -> ToolResult:
        """Execute the tool.

        Args:
            **params: Tool-specific parameters

        Returns:
            ToolResult with execution status and data
        """
        pass

    def validate_params(self, params: dict, required: List[str]) -> Optional[str]:
        """Validate required parameters.

        Args:
            params: Parameters to validate
            required: List of required parameter names

        Returns:
            Error message if validation fails, None if valid
        """
        for param in required:
            if param not in params:
                return f"Missing required parameter: {param}"
            if params[param] is None:
                return f"Parameter '{param}' cannot be None"
        return None

    def log_execution(self, params: dict, result: ToolResult):
        """Log tool execution for debugging.

        Args:
            params: Input parameters
            result: Execution result
        """
        self.logger.info(
            f"Tool '{self.metadata.name}' executed with status={result.status.value}, "
            f"params_keys={list(params.keys())}"
        )
        if result.error:
            self.logger.error(f"Tool error: {result.error}")


class ToolDependency:
    """Define dependencies between tools."""

    def __init__(self, tool_name: str, required: bool = True):
        """Initialize dependency.

        Args:
            tool_name: Name of the dependent tool
            required: Whether this dependency is required
        """
        self.tool_name = tool_name
        self.required = required
