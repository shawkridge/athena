"""MCP tools package with modular, lazy-loaded architecture.

Provides:
- BaseTool: Abstract base class for all tools
- ToolMetadata: Metadata model for tool discovery
- ToolRegistry: Centralized registry for tool management
- ToolLoader: Dynamic loader with lazy loading and caching
"""

from .base import BaseTool, ToolMetadata
from .registry import ToolRegistry, get_registry, register_tool
from .loader import ToolLoader, get_loader

__all__ = [
    "BaseTool",
    "ToolMetadata",
    "ToolRegistry",
    "get_registry",
    "register_tool",
    "ToolLoader",
    "get_loader",
]
