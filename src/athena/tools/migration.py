"""Tool migration framework for extracting tools from monolithic handlers.py.

Provides utilities for systematically migrating MCP tools from the
monolithic handlers.py into modular, lazy-loaded tool files.
"""
import ast
import re
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ToolExtractor:
    """Extract tool definitions from monolithic MCP handler files."""

    def __init__(self, handlers_file: Path):
        """Initialize extractor.

        Args:
            handlers_file: Path to handlers.py file
        """
        self.handlers_file = handlers_file
        self._content: Optional[str] = None
        self._ast: Optional[ast.Module] = None

    @property
    def content(self) -> str:
        """Get handlers.py content."""
        if self._content is None:
            with open(self.handlers_file) as f:
                self._content = f.read()
        return self._content

    @property
    def tree(self) -> ast.Module:
        """Parse handlers.py as AST."""
        if self._ast is None:
            self._ast = ast.parse(self.content)
        return self._ast

    def find_tools(self) -> Dict[str, Dict[str, Any]]:
        """Find all @server.tool() decorated methods.

        Returns:
            Dictionary of tool_name -> tool_info
        """
        tools = {}

        for node in ast.walk(self.tree):
            if isinstance(node, ast.FunctionDef):
                # Check for @server.tool() decorator
                for decorator in node.decorator_list:
                    if self._is_server_tool_decorator(decorator):
                        tool_name = node.name
                        tools[tool_name] = {
                            "name": tool_name,
                            "lineno": node.lineno,
                            "lineno_end": node.end_lineno,
                            "docstring": ast.get_docstring(node),
                            "args": [arg.arg for arg in node.args.args],
                            "returns": self._extract_return_type(node),
                        }

        return tools

    def extract_tool_method(self, tool_name: str) -> Optional[str]:
        """Extract complete tool method source code.

        Args:
            tool_name: Name of tool method

        Returns:
            Complete method source code, or None if not found
        """
        tools = self.find_tools()
        if tool_name not in tools:
            return None

        tool_info = tools[tool_name]
        lines = self.content.split("\n")

        # Extract lines from source
        start = tool_info["lineno"] - 1  # Convert to 0-based
        end = tool_info["lineno_end"] or len(lines)

        extracted = "\n".join(lines[start:end])
        return extracted

    def get_tool_categories(self) -> Dict[str, List[str]]:
        """Categorize tools by name pattern.

        Returns:
            Dictionary of category -> [tool_names]
        """
        categories = {}
        tools = self.find_tools()

        for tool_name in tools:
            # Extract category from tool name pattern
            # memory_recall -> memory, consolidation_start -> consolidation
            parts = tool_name.split("_")
            if len(parts) >= 2:
                category = parts[0]
            else:
                category = "general"

            if category not in categories:
                categories[category] = []
            categories[category].append(tool_name)

        return categories

    @staticmethod
    def _is_server_tool_decorator(decorator: ast.expr) -> bool:
        """Check if decorator is @server.tool().

        Args:
            decorator: Decorator AST node

        Returns:
            True if decorator is @server.tool()
        """
        if isinstance(decorator, ast.Call):
            if isinstance(decorator.func, ast.Attribute):
                if (
                    isinstance(decorator.func.value, ast.Name)
                    and decorator.func.value.id == "server"
                    and decorator.func.attr == "tool"
                ):
                    return True
        return False

    @staticmethod
    def _extract_return_type(node: ast.FunctionDef) -> Optional[str]:
        """Extract return type annotation.

        Args:
            node: Function AST node

        Returns:
            Return type string or None
        """
        if node.returns:
            return ast.unparse(node.returns)
        return None


class ToolMigrator:
    """Migrate tools from monolithic handler to modular structure."""

    TEMPLATE_TOOL = '''"""Tool for {description}."""
from typing import Any, Dict, Optional
from athena.tools import BaseTool, ToolMetadata


class {class_name}(BaseTool):
    """{class_name} - {description}."""

    @property
    def metadata(self) -> ToolMetadata:
        """Return tool metadata."""
        return ToolMetadata(
            name="{tool_name}",
            category="{category}",
            description="{description}",
            parameters={{}},
            returns={{}}
        )

    def validate_input(self, **kwargs) -> None:
        """Validate input parameters."""
        pass

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool.

        TODO: Implement tool logic from handlers.py
        """
        return {{"status": "not_implemented", "todo": "Migrate from handlers.py"}}
'''

    def __init__(self, handlers_file: Path, tools_base_dir: Path):
        """Initialize migrator.

        Args:
            handlers_file: Path to handlers.py
            tools_base_dir: Base directory for new tool structure
        """
        self.extractor = ToolExtractor(handlers_file)
        self.tools_base_dir = tools_base_dir

    def create_tool_file(self, tool_name: str, category: str) -> Path:
        """Create a new modular tool file.

        Args:
            tool_name: Original tool name (e.g., "memory_recall")
            category: Category for tool (e.g., "memory")

        Returns:
            Path to created file
        """
        # Convert tool name to module name
        module_name = tool_name.replace("_", "_")  # Keep underscores
        if module_name.startswith(f"{category}_"):
            module_name = module_name[len(category) + 1:]

        # Create category directory if needed
        category_dir = self.tools_base_dir / category
        category_dir.mkdir(parents=True, exist_ok=True)

        # Create __init__.py if not exists
        init_file = category_dir / "__init__.py"
        if not init_file.exists():
            init_file.touch()

        # Generate class name (CamelCase)
        class_name = "".join(word.capitalize() for word in module_name.split("_")) + "Tool"

        # Generate file content from template
        description = " ".join(module_name.split("_")).title()
        content = self.TEMPLATE_TOOL.format(
            class_name=class_name,
            tool_name=tool_name.replace("_", "-"),  # Convert to kebab-case for display
            category=category,
            description=description
        )

        # Write file
        tool_file = category_dir / f"{module_name}.py"
        tool_file.write_text(content)
        logger.info(f"Created tool file: {tool_file}")

        return tool_file

    def migrate_tools(self, tool_names: Optional[List[str]] = None) -> Dict[str, Path]:
        """Migrate specified tools to modular structure.

        Args:
            tool_names: List of tool names to migrate (None for all)

        Returns:
            Dictionary of tool_name -> file_path
        """
        tools = self.extractor.find_tools()
        categories = self.extractor.get_tool_categories()

        # Determine which tools to migrate
        if tool_names is None:
            tool_names = list(tools.keys())

        migrated = {}
        for tool_name in tool_names:
            if tool_name not in tools:
                logger.warning(f"Tool '{tool_name}' not found in handlers.py")
                continue

            # Find category for this tool
            category = None
            for cat, cat_tools in categories.items():
                if tool_name in cat_tools:
                    category = cat
                    break

            if not category:
                category = "general"

            # Create the tool file
            tool_file = self.create_tool_file(tool_name, category)
            migrated[tool_name] = tool_file

        return migrated

    def get_migration_status(self) -> Dict[str, Any]:
        """Get migration status and statistics.

        Returns:
            Dictionary with migration stats
        """
        tools = self.extractor.find_tools()
        categories = self.extractor.get_tool_categories()

        # Count migrated tools
        migrated_count = 0
        if self.tools_base_dir.exists():
            for category_dir in self.tools_base_dir.iterdir():
                if category_dir.is_dir():
                    for py_file in category_dir.glob("*.py"):
                        if py_file.name != "__init__.py":
                            migrated_count += 1

        return {
            "total_tools_in_handlers": len(tools),
            "migrated_tools": migrated_count,
            "remaining_tools": len(tools) - migrated_count,
            "categories": categories,
            "migration_percentage": (migrated_count / len(tools) * 100) if tools else 0
        }


class BackwardCompatibilityLayer:
    """Create backward compatibility for migrated tools."""

    COMPATIBILITY_WRAPPER = '''"""Backward compatibility wrapper for {tool_name}.

This module provides backward compatibility for tools migrated to the
modular structure. It wraps the new modular tool to work with code
expecting the old monolithic handler API.
"""
from athena.tools import get_loader

_loader = get_loader()


def handle_{tool_name}(**kwargs):
    """Handle {tool_name} requests (backward compatible).

    Delegates to the new modular tool.
    """
    tool = _loader.load_tool("{tool_key}")
    if not tool:
        return {{"error": "Tool not found", "tool": "{tool_key}"}}

    import asyncio
    try:
        result = asyncio.run(tool.execute(**kwargs))
        return result
    except Exception as e:
        return {{"error": str(e), "tool": "{tool_key}"}}
'''

    def __init__(self, mcp_dir: Path, tools_base_dir: Path):
        """Initialize compatibility layer.

        Args:
            mcp_dir: Directory containing MCP handlers
            tools_base_dir: Base directory for new tool structure
        """
        self.mcp_dir = mcp_dir
        self.tools_base_dir = tools_base_dir
        self.compat_dir = mcp_dir / "compat"

    def create_wrapper(self, tool_name: str, tool_key: str) -> Path:
        """Create compatibility wrapper for a tool.

        Args:
            tool_name: Original tool method name
            tool_key: New tool key (e.g., "memory.recall")

        Returns:
            Path to wrapper file
        """
        self.compat_dir.mkdir(parents=True, exist_ok=True)

        content = self.COMPATIBILITY_WRAPPER.format(
            tool_name=tool_name,
            tool_key=tool_key
        )

        wrapper_file = self.compat_dir / f"{tool_name}_compat.py"
        wrapper_file.write_text(content)

        return wrapper_file

    def create_all_wrappers(self, tool_mappings: Dict[str, str]) -> Dict[str, Path]:
        """Create wrappers for all migrated tools.

        Args:
            tool_mappings: Dictionary of old_name -> new_key

        Returns:
            Dictionary of tool_name -> wrapper_path
        """
        wrappers = {}
        for old_name, new_key in tool_mappings.items():
            wrapper_path = self.create_wrapper(old_name, new_key)
            wrappers[old_name] = wrapper_path
            logger.info(f"Created compatibility wrapper: {wrapper_path}")

        return wrappers
