"""Dynamic tool loader with lazy loading and caching.

Enables efficient loading of tools on-demand, reducing context overhead
and improving performance through selective tool instantiation.
"""
import importlib
import sys
from pathlib import Path
from typing import Dict, Optional, Type
import logging

from .base import BaseTool
from .registry import ToolRegistry, get_registry

logger = logging.getLogger(__name__)


class ToolLoader:
    """Dynamically loads and caches tool classes.

    Supports lazy loading to reduce memory overhead and context size.
    Only loads tools when explicitly requested.
    """

    def __init__(self, registry: Optional[ToolRegistry] = None, tools_dir: Optional[Path] = None):
        """Initialize tool loader.

        Args:
            registry: ToolRegistry to use (default: global registry)
            tools_dir: Directory containing tool modules (default: src/athena/tools)
        """
        self.registry = registry or get_registry()
        self.tools_dir = tools_dir or Path(__file__).parent
        self._loaded_modules: Dict[str, type] = {}
        self._auto_discovered = False

    def load_module(self, module_name: str) -> Optional[type]:
        """Load a tool module dynamically.

        Args:
            module_name: Module path (e.g., "athena.tools.memory.query")

        Returns:
            Module if successfully loaded, None otherwise

        Raises:
            ImportError: If module cannot be imported
        """
        # Check cache first
        if module_name in self._loaded_modules:
            return self._loaded_modules[module_name]

        try:
            logger.debug(f"Loading module: {module_name}")
            module = importlib.import_module(module_name)
            self._loaded_modules[module_name] = module
            return module
        except ImportError as e:
            logger.error(f"Failed to load module {module_name}: {e}")
            raise

    def load_tool(self, tool_key: str) -> Optional[BaseTool]:
        """Load and instantiate a tool by key.

        Args:
            tool_key: Tool identifier (e.g., "memory.query")

        Returns:
            Tool instance if found and loaded, None otherwise

        Raises:
            RuntimeError: If tool class cannot be instantiated
        """
        # Check if already registered
        tool_class = self.registry.get(tool_key)
        if tool_class:
            return tool_class()

        # Try to load from module path
        module_name = self._key_to_module_name(tool_key)
        try:
            module = self.load_module(module_name)
            # Find tool class in module (assume class matches capitalized module name)
            class_name = self._module_name_to_class_name(tool_key)
            if hasattr(module, class_name):
                tool_class = getattr(module, class_name)
                # Register for future use
                self.registry.register(tool_key, tool_class, category=tool_key.split(".")[0])
                return tool_class()
            else:
                logger.warning(f"Tool class {class_name} not found in {module_name}")
                return None
        except ImportError as e:
            logger.error(f"Failed to load tool {tool_key}: {e}")
            return None

    def discover_tools(self, force_reload: bool = False) -> Dict[str, Type[BaseTool]]:
        """Auto-discover all tools in tools directory.

        Scans subdirectories for Python modules and registers any classes
        that inherit from BaseTool.

        Args:
            force_reload: Force reload even if already discovered

        Returns:
            Dictionary of discovered tools {key: tool_class}
        """
        if self._auto_discovered and not force_reload:
            return {k: self.registry.get(k) for k in self.registry._tools}

        discovered = {}

        # Scan subdirectories in tools/
        for subdir in self.tools_dir.iterdir():
            if not subdir.is_dir() or subdir.name.startswith("_"):
                continue

            category = subdir.name  # e.g., "memory", "consolidation"

            # Scan Python files in subdirectory
            for py_file in subdir.glob("*.py"):
                if py_file.name.startswith("_"):
                    continue

                module_name = f"athena.tools.{category}.{py_file.stem}"
                try:
                    logger.debug(f"Discovering tools in {module_name}")
                    module = self.load_module(module_name)

                    # Find all BaseTool subclasses in module
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (
                            isinstance(attr, type)
                            and issubclass(attr, BaseTool)
                            and attr is not BaseTool
                        ):
                            tool_key = f"{category}.{py_file.stem}.{attr_name.lower()}"
                            self.registry.register(tool_key, attr, category=category)
                            discovered[tool_key] = attr
                            logger.debug(f"Discovered tool: {tool_key}")

                except Exception as e:
                    logger.warning(f"Failed to discover tools in {module_name}: {e}")

        self._auto_discovered = True
        return discovered

    def load_category(self, category: str) -> Dict[str, BaseTool]:
        """Load all tools in a category.

        Args:
            category: Category name (e.g., "memory", "consolidation")

        Returns:
            Dictionary of instantiated tools {key: tool_instance}
        """
        tools = {}
        for tool_key in self.registry.get_category_tools(category):
            try:
                tool = self.load_tool(tool_key)
                if tool:
                    tools[tool_key] = tool
            except Exception as e:
                logger.error(f"Failed to load tool {tool_key}: {e}")

        return tools

    def preload_category(self, category: str) -> None:
        """Pre-load all tools in a category to reduce latency.

        Args:
            category: Category name
        """
        logger.info(f"Pre-loading category: {category}")
        _ = self.load_category(category)

    def get_memory_usage(self) -> Dict[str, int]:
        """Estimate memory usage of loaded tools.

        Returns:
            Dictionary with memory stats
        """
        loaded_count = len(self._loaded_modules)
        registered_count = len(self.registry._tools)

        return {
            "loaded_modules": loaded_count,
            "registered_tools": registered_count,
            "unloaded_tools": registered_count - loaded_count
        }

    @staticmethod
    def _key_to_module_name(tool_key: str) -> str:
        """Convert tool key to module name.

        Args:
            tool_key: Tool identifier (e.g., "memory.query")

        Returns:
            Module name (e.g., "athena.tools.memory.query")
        """
        return f"athena.tools.{tool_key.replace('.', '.')}"

    @staticmethod
    def _module_name_to_class_name(tool_key: str) -> str:
        """Convert tool key to class name.

        Args:
            tool_key: Tool identifier (e.g., "memory.query")

        Returns:
            Class name (e.g., "QueryMemoryTool")
        """
        parts = tool_key.split(".")
        # CamelCase: memory.query -> MemoryQueryTool
        class_name = "".join(p.capitalize() for p in parts) + "Tool"
        return class_name


# Global loader instance
_global_loader: Optional[ToolLoader] = None


def get_loader(registry: Optional[ToolRegistry] = None) -> ToolLoader:
    """Get or create global tool loader.

    Args:
        registry: ToolRegistry to use (default: global registry)

    Returns:
        Global ToolLoader instance
    """
    global _global_loader
    if _global_loader is None:
        _global_loader = ToolLoader(registry=registry)
    return _global_loader
