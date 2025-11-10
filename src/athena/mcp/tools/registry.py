"""Tool registry for managing modular MCP tools."""

import logging
from typing import Dict, Optional, List, Any
from .base import BaseTool, ToolMetadata

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Registry for managing and discovering modular tools."""

    def __init__(self):
        """Initialize tool registry."""
        self._tools: Dict[str, BaseTool] = {}
        self._categories: Dict[str, List[str]] = {}
        self.logger = logging.getLogger(__name__)

    def register(self, tool: BaseTool) -> None:
        """Register a tool in the registry.

        Args:
            tool: Tool instance to register

        Raises:
            ValueError: If tool with same name already registered
        """
        if tool.metadata.name in self._tools:
            raise ValueError(
                f"Tool '{tool.metadata.name}' already registered. "
                f"Use update() to replace existing tool."
            )

        self._tools[tool.metadata.name] = tool

        # Index by category
        category = tool.metadata.category
        if category not in self._categories:
            self._categories[category] = []
        self._categories[category].append(tool.metadata.name)

        self.logger.info(
            f"Registered tool '{tool.metadata.name}' in category '{category}'"
        )

    def unregister(self, tool_name: str) -> bool:
        """Unregister a tool from the registry.

        Args:
            tool_name: Name of tool to unregister

        Returns:
            True if tool was unregistered, False if not found
        """
        if tool_name not in self._tools:
            return False

        tool = self._tools.pop(tool_name)
        category = tool.metadata.category

        if category in self._categories:
            self._categories[category].remove(tool_name)
            if not self._categories[category]:
                del self._categories[category]

        self.logger.info(f"Unregistered tool '{tool_name}'")
        return True

    def update(self, tool: BaseTool) -> None:
        """Update an existing tool or register if not found.

        Args:
            tool: Tool instance to update/register
        """
        if tool.metadata.name in self._tools:
            self.unregister(tool.metadata.name)
        self.register(tool)

    def get(self, tool_name: str) -> Optional[BaseTool]:
        """Get a tool by name.

        Args:
            tool_name: Name of tool to retrieve

        Returns:
            Tool instance or None if not found
        """
        return self._tools.get(tool_name)

    def list_tools(self) -> List[BaseTool]:
        """List all registered tools.

        Returns:
            List of all registered tool instances
        """
        return list(self._tools.values())

    def list_by_category(self, category: str) -> List[BaseTool]:
        """List tools in a specific category.

        Args:
            category: Category name

        Returns:
            List of tools in category
        """
        if category not in self._categories:
            return []

        return [
            self._tools[name]
            for name in self._categories[category]
            if name in self._tools
        ]

    def get_metadata(self, tool_name: str) -> Optional[ToolMetadata]:
        """Get metadata for a tool.

        Args:
            tool_name: Name of tool

        Returns:
            Tool metadata or None if not found
        """
        tool = self.get(tool_name)
        return tool.metadata if tool else None

    def search_by_tag(self, tag: str) -> List[BaseTool]:
        """Search tools by tag.

        Args:
            tag: Tag to search for

        Returns:
            List of tools with the tag
        """
        return [
            tool
            for tool in self._tools.values()
            if tag in tool.metadata.tags
        ]

    def get_categories(self) -> List[str]:
        """Get list of all categories.

        Returns:
            List of category names
        """
        return list(self._categories.keys())

    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics.

        Returns:
            Dictionary with registry stats
        """
        return {
            "total_tools": len(self._tools),
            "categories": len(self._categories),
            "tools_by_category": {
                cat: len(tools)
                for cat, tools in self._categories.items()
            },
            "categories_list": self.get_categories(),
        }

    def __len__(self) -> int:
        """Get number of registered tools."""
        return len(self._tools)

    def __contains__(self, tool_name: str) -> bool:
        """Check if tool is registered."""
        return tool_name in self._tools

    def __iter__(self):
        """Iterate over all tools."""
        return iter(self._tools.values())
