"""Base tool class for all MCP tools.

Provides standardized interface for tool implementation and registration.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel


class ToolMetadata(BaseModel):
    """Metadata describing a tool."""

    name: str
    category: str
    description: str
    parameters: Dict[str, Any] = {}
    returns: Dict[str, Any] = {}


class BaseTool(ABC):
    """Abstract base class for all MCP tools.

    Every tool must:
    1. Implement metadata property
    2. Implement execute method
    3. Optionally implement validate_input
    """

    @property
    @abstractmethod
    def metadata(self) -> ToolMetadata:
        """Return tool metadata.

        Returns:
            ToolMetadata with name, description, parameters, returns.
        """
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """Execute the tool.

        Args:
            **kwargs: Tool-specific parameters

        Returns:
            Tool result (typically Dict[str, Any])

        Raises:
            ValueError: If parameters are invalid
            RuntimeError: If execution fails
        """
        pass

    def validate_input(self, **kwargs) -> None:
        """Validate input parameters.

        Optional: Override in subclasses for custom validation.

        Args:
            **kwargs: Parameters to validate

        Raises:
            ValueError: If validation fails
        """
        pass
