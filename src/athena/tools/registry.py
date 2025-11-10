"""Tool registry for managing and discovering available tools.

Provides centralized registry for all MCP tools with metadata
and discovery capabilities.
"""
from typing import Dict, List, Optional, Type
from .base import BaseTool, ToolMetadata


class ToolRegistry:
    """Centralized registry for all MCP tools.

    Manages tool registration, lookup, and discovery with support for
    hierarchical categories and lazy loading.
    """

    def __init__(self):
        """Initialize empty registry."""
        self._tools: Dict[str, Type[BaseTool]] = {}
        self._metadata_cache: Dict[str, ToolMetadata] = {}
        self._categories: Dict[str, List[str]] = {}

    def register(self, key: str, tool_class: Type[BaseTool], category: str = "general") -> None:
        """Register a tool class.

        Args:
            key: Unique tool identifier (e.g., "memory.query", "consolidation.start")
            tool_class: Tool class to register (must inherit from BaseTool)
            category: Category for discovery (e.g., "memory", "consolidation")

        Raises:
            ValueError: If key already registered or tool_class invalid
            TypeError: If tool_class doesn't inherit from BaseTool
        """
        if key in self._tools:
            raise ValueError(f"Tool '{key}' already registered")

        if not issubclass(tool_class, BaseTool):
            raise TypeError(f"Tool class must inherit from BaseTool, got {tool_class}")

        # Store tool class and category
        self._tools[key] = tool_class

        # Update category index
        if category not in self._categories:
            self._categories[category] = []
        self._categories[category].append(key)

    def get(self, key: str) -> Optional[Type[BaseTool]]:
        """Get tool class by key.

        Args:
            key: Tool identifier (e.g., "memory.query")

        Returns:
            Tool class if registered, None otherwise
        """
        return self._tools.get(key)

    def instantiate(self, key: str) -> Optional[BaseTool]:
        """Instantiate a tool by key.

        Args:
            key: Tool identifier (e.g., "memory.query")

        Returns:
            Tool instance if registered, None otherwise

        Raises:
            Exception: If tool instantiation fails
        """
        tool_class = self.get(key)
        if not tool_class:
            return None
        return tool_class()

    def list_tools(
        self,
        category: Optional[str] = None,
        include_metadata: bool = False
    ) -> List[str] | List[tuple[str, ToolMetadata]]:
        """List registered tools, optionally filtered by category.

        Args:
            category: Filter by category (None for all tools)
            include_metadata: Include metadata in results

        Returns:
            List of tool keys, or list of (key, metadata) tuples if
            include_metadata=True
        """
        if category:
            keys = self._categories.get(category, [])
        else:
            keys = list(self._tools.keys())

        if not include_metadata:
            return keys

        # Build metadata for each tool
        results = []
        for key in keys:
            tool_class = self._tools[key]
            try:
                # Instantiate to get metadata
                tool = tool_class()
                metadata = tool.metadata
                results.append((key, metadata))
            except Exception as e:
                # Log error but continue
                print(f"Warning: Failed to load metadata for {key}: {e}")

        return results

    def get_categories(self) -> List[str]:
        """Get all registered categories.

        Returns:
            List of category names
        """
        return sorted(list(self._categories.keys()))

    def get_category_tools(self, category: str) -> List[str]:
        """Get all tools in a category.

        Args:
            category: Category name

        Returns:
            List of tool keys in category
        """
        return self._categories.get(category, [])

    def has_tool(self, key: str) -> bool:
        """Check if tool is registered.

        Args:
            key: Tool identifier

        Returns:
            True if tool registered, False otherwise
        """
        return key in self._tools

    def unregister(self, key: str) -> bool:
        """Unregister a tool.

        Args:
            key: Tool identifier

        Returns:
            True if tool was registered and removed, False if not found
        """
        if key not in self._tools:
            return False

        del self._tools[key]

        # Remove from categories index
        for category, keys in self._categories.items():
            if key in keys:
                keys.remove(key)
                break

        # Clear metadata cache for this tool
        self._metadata_cache.pop(key, None)

        return True

    def clear(self) -> None:
        """Clear all registered tools."""
        self._tools.clear()
        self._metadata_cache.clear()
        self._categories.clear()

    def get_stats(self) -> Dict[str, int]:
        """Get registry statistics.

        Returns:
            Dictionary with counts of tools and categories
        """
        return {
            "total_tools": len(self._tools),
            "total_categories": len(self._categories),
            "categories_breakdown": {
                cat: len(keys) for cat, keys in self._categories.items()
            }
        }


# Global registry instance
_global_registry: Optional[ToolRegistry] = None


def get_registry() -> ToolRegistry:
    """Get or create global tool registry.

    Returns:
        Global ToolRegistry instance
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
    return _global_registry


def register_tool(key: str, tool_class: Type[BaseTool], category: str = "general") -> None:
    """Register a tool in the global registry.

    Args:
        key: Unique tool identifier
        tool_class: Tool class to register
        category: Category for discovery
    """
    get_registry().register(key, tool_class, category)
