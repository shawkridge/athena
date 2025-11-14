"""Tools discovery and generation system.

Generates callable Python files in /athena/tools/ for filesystem-based agent discovery.

This implements the Anthropic MCP code execution pattern where agents discover tools
by exploring the filesystem structure and reading callable Python files.

Architecture:
  /athena/tools/
  ├── __init__.py
  ├── memory/
  │   ├── __init__.py
  │   ├── recall.py (function: recall(query, limit=10) -> List[Memory])
  │   ├── remember.py (function: remember(content, tags=[]) -> MemoryID)
  │   └── forget.py (function: forget(memory_id) -> bool)
  ├── planning/
  │   ├── __init__.py
  │   ├── plan_task.py (function: plan_task(description) -> Plan)
  │   └── validate_plan.py (function: validate_plan(plan) -> bool)
  └── consolidation/
      ├── __init__.py
      ├── consolidate.py (function: consolidate(strategy='balanced') -> Report)
      └── get_patterns.py (function: get_patterns(limit=10) -> List[Pattern])

Benefits:
1. True filesystem discovery - agents can `ls` to find tools
2. Progressive loading - agents read only tool definitions they need
3. Data filtering in code - intermediate results stay local
4. Clear interface - each tool is a single callable file
5. Low context overhead - no tool definitions in prompts
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class ToolMetadata:
    """Metadata for a generated tool."""

    name: str                          # Tool name (e.g., 'recall', 'remember')
    category: str                       # Category (e.g., 'memory', 'planning')
    description: str                    # What the tool does
    parameters: Dict[str, Dict]         # Parameter schema {name: {type, description, default}}
    returns: str                        # Return type description
    example: str                        # Usage example
    entry_point: str                    # Function name to call
    dependencies: List[str]             # Internal modules this depends on


class ToolsGenerator:
    """Generates callable tool files for filesystem discovery.

    Example Usage:
        generator = ToolsGenerator(output_dir="/athena/tools")
        generator.generate_all()

        # Agents can now:
        # 1. Explore filesystem: ls /athena/tools/memory/
        # 2. Read tool file: cat /athena/tools/memory/recall.py
        # 3. Import and call: from athena.tools.memory.recall import recall
    """

    def __init__(self, output_dir: str = "/athena/tools", manager=None):
        """Initialize generator.

        Args:
            output_dir: Where to generate tool files
            manager: UnifiedMemoryManager instance (for actual tool implementation)
        """
        self.output_dir = Path(output_dir)
        self.manager = manager
        self.tools: Dict[str, ToolMetadata] = {}

    def register_tool(self, metadata: ToolMetadata) -> None:
        """Register a tool for generation.

        Args:
            metadata: ToolMetadata describing the tool
        """
        key = f"{metadata.category}/{metadata.name}"
        self.tools[key] = metadata
        logger.info(f"Registered tool: {key}")

    def generate_all(self) -> None:
        """Generate all registered tools."""
        logger.info(f"Generating {len(self.tools)} tools to {self.output_dir}")

        # Create directory structure
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Create module init
        self._create_init(self.output_dir)

        # Group tools by category
        by_category = {}
        for tool_key, metadata in self.tools.items():
            category = metadata.category
            if category not in by_category:
                by_category[category] = []
            by_category[category].append((tool_key, metadata))

        # Generate category directories and tools
        for category, tools_in_category in sorted(by_category.items()):
            category_dir = self.output_dir / category
            category_dir.mkdir(parents=True, exist_ok=True)

            # Create category init
            self._create_init(category_dir)

            # Generate each tool
            for tool_key, metadata in tools_in_category:
                self._generate_tool_file(metadata, category_dir)

            # Create index.md for category
            self._create_category_index(category, tools_in_category, category_dir)

        # Create root index
        self._create_root_index(by_category)

        logger.info(f"Generated {len(self.tools)} tool files")

    def _generate_tool_file(self, metadata: ToolMetadata, category_dir: Path) -> None:
        """Generate a single tool file.

        Args:
            metadata: Tool metadata
            category_dir: Directory to write to
        """
        tool_file = category_dir / f"{metadata.name}.py"

        content = self._render_tool_file(metadata)

        tool_file.write_text(content)
        logger.debug(f"Generated: {tool_file}")

    def _render_tool_file(self, metadata: ToolMetadata) -> str:
        """Render Python code for a tool file.

        Args:
            metadata: Tool metadata

        Returns:
            Python source code
        """
        # Build parameter string
        param_str = ', '.join(
            f"{name}: {param.get('type', 'Any')}" +
            (f" = {param.get('default', 'None')}" if 'default' in param else "")
            for name, param in metadata.parameters.items()
        )

        # Build docstring
        docstring = f'''"""
{metadata.description}

Parameters:
{chr(10).join(f"    {name}: {param.get('description', '')}" for name, param in metadata.parameters.items())}

Returns:
    {metadata.returns}

Example:
    >>> {metadata.example}
"""'''

        # Generate implementation placeholder
        # In production, this would call the actual manager methods
        implementation = f"""
# This tool is auto-generated by ToolsGenerator
# Agents should use the manager directly instead of calling this stub
# See: athena.manager.UnifiedMemoryManager.{metadata.entry_point}()

def {metadata.entry_point}({param_str}):
    {docstring}

    # To use this tool properly:
    # 1. Import from the manager: from athena.manager import UnifiedMemoryManager
    # 2. Create an instance: manager = UnifiedMemoryManager()
    # 3. Call the method: result = manager.{metadata.entry_point}({', '.join(metadata.parameters.keys())})
    #
    # OR import the MCP tools directly:
    # from athena.mcp.tools import {metadata.entry_point}

    raise NotImplementedError(
        "Use manager directly: from athena.manager import UnifiedMemoryManager\\n"
        "Or import MCP tools: from athena.mcp.tools import {metadata.entry_point}"
    )
"""

        return f'''"""
{metadata.name.upper()} Tool - Callable tool for {metadata.category}

This file is auto-generated by ToolsGenerator.
Agents can discover this tool by reading the filesystem and import it directly.

To use this tool:
    from athena.tools.{metadata.category}.{metadata.name} import {metadata.entry_point}
    result = {metadata.entry_point}(...)
"""

{implementation}
'''

    def _create_init(self, directory: Path) -> None:
        """Create __init__.py for a module.

        Args:
            directory: Directory to create init in
        """
        init_file = directory / "__init__.py"

        if init_file.exists():
            return

        content = f'''"""
Tools module for {directory.name or 'athena.tools'}.

This module provides callable tools for agent execution.
Tools are discovered via filesystem exploration and imported directly.

Architecture:
- Each tool is a .py file with a single callable function
- Tools are organized by category (memory, planning, etc.)
- Agents explore the filesystem to discover available tools
- No tool definitions in prompts - data stays local
"""
'''

        init_file.write_text(content)
        logger.debug(f"Created: {init_file}")

    def _create_category_index(self, category: str, tools: List, category_dir: Path) -> None:
        """Create index.md for a category.

        Args:
            category: Category name
            tools: List of (tool_key, metadata) tuples
            category_dir: Directory containing the tools
        """
        index_file = category_dir / "INDEX.md"

        lines = [f"# {category.title()} Tools", ""]

        for _, metadata in tools:
            lines.append(f"## {metadata.name}")
            lines.append(f"- **Description**: {metadata.description}")
            lines.append(f"- **Entry Point**: `{metadata.entry_point}()`")
            lines.append(f"- **Returns**: {metadata.returns}")
            lines.append(f"- **Example**: `{metadata.example}`")
            lines.append("")

        index_file.write_text("\n".join(lines))
        logger.debug(f"Created: {index_file}")

    def _create_root_index(self, by_category: Dict) -> None:
        """Create root INDEX.md.

        Args:
            by_category: Tools organized by category
        """
        index_file = self.output_dir / "INDEX.md"

        lines = [
            "# Athena Tools",
            "",
            "Filesystem-discoverable tools for agent execution.",
            "",
            "## Categories",
            ""
        ]

        for category in sorted(by_category.keys()):
            tools = by_category[category]
            lines.append(f"### {category.title()} ({len(tools)} tools)")
            for _, metadata in tools:
                lines.append(f"- `{metadata.name}`: {metadata.description}")
            lines.append("")

        lines.extend([
            "## Usage",
            "",
            "### Discover Tools",
            "```bash",
            "ls /athena/tools/              # List categories",
            "ls /athena/tools/memory/       # List memory tools",
            "cat /athena/tools/memory/recall.py  # Read tool definition",
            "```",
            "",
            "### Use a Tool",
            "```python",
            "from athena.tools.memory.recall import recall",
            "results = recall('query', limit=10)",
            "```",
            ""
        ])

        index_file.write_text("\n".join(lines))
        logger.info(f"Created root index: {index_file}")


def register_core_tools(generator: ToolsGenerator) -> None:
    """Register core Athena tools.

    Args:
        generator: ToolsGenerator instance
    """
    # Memory tools
    generator.register_tool(ToolMetadata(
        name="recall",
        category="memory",
        description="Search and retrieve memories using semantic search",
        parameters={
            "query": {"type": "str", "description": "Search query"},
            "limit": {"type": "int", "description": "Max results", "default": 10},
            "min_score": {"type": "float", "description": "Min relevance score", "default": 0.5},
        },
        returns="List[Memory] - Matching memories with scores",
        example="recall('How to authenticate users?', limit=5)",
        entry_point="recall",
        dependencies=["athena.semantic", "athena.manager"],
    ))

    generator.register_tool(ToolMetadata(
        name="remember",
        category="memory",
        description="Record a new episodic event or semantic memory",
        parameters={
            "content": {"type": "str", "description": "Memory content"},
            "event_type": {"type": "str", "description": "Type of event", "default": "action"},
            "tags": {"type": "List[str]", "description": "Optional tags", "default": "[]"},
        },
        returns="str - Memory ID",
        example="remember('Implemented user auth', tags=['security', 'auth'])",
        entry_point="remember",
        dependencies=["athena.episodic", "athena.manager"],
    ))

    generator.register_tool(ToolMetadata(
        name="forget",
        category="memory",
        description="Delete a memory by ID",
        parameters={
            "memory_id": {"type": "str", "description": "ID of memory to delete"},
        },
        returns="bool - True if deleted",
        example="forget('mem_12345')",
        entry_point="forget",
        dependencies=["athena.manager"],
    ))

    # Planning tools
    generator.register_tool(ToolMetadata(
        name="plan_task",
        category="planning",
        description="Decompose a task into an executable plan",
        parameters={
            "description": {"type": "str", "description": "Task description"},
            "depth": {"type": "int", "description": "Planning depth", "default": 3},
        },
        returns="Plan - Hierarchical task plan",
        example="plan_task('Implement user authentication')",
        entry_point="plan_task",
        dependencies=["athena.planning", "athena.manager"],
    ))

    generator.register_tool(ToolMetadata(
        name="validate_plan",
        category="planning",
        description="Validate a plan using formal verification and scenario testing",
        parameters={
            "plan": {"type": "Plan", "description": "Plan to validate"},
            "scenarios": {"type": "int", "description": "Number of scenarios", "default": 5},
        },
        returns="ValidationResult - Plan validity and issues",
        example="validate_plan(my_plan)",
        entry_point="validate_plan",
        dependencies=["athena.planning", "athena.manager"],
    ))

    # Consolidation tools
    generator.register_tool(ToolMetadata(
        name="consolidate",
        category="consolidation",
        description="Extract patterns from episodic events (sleep-like consolidation)",
        parameters={
            "strategy": {"type": "str", "description": "Strategy: balanced/speed/quality", "default": "balanced"},
            "days_back": {"type": "int", "description": "Days of events to consolidate", "default": 7},
        },
        returns="ConsolidationReport - Patterns extracted and quality metrics",
        example="consolidate(strategy='quality')",
        entry_point="consolidate",
        dependencies=["athena.consolidation", "athena.manager"],
    ))

    generator.register_tool(ToolMetadata(
        name="get_patterns",
        category="consolidation",
        description="Retrieve learned patterns from consolidation",
        parameters={
            "domain": {"type": "str", "description": "Optional domain filter"},
            "limit": {"type": "int", "description": "Max patterns", "default": 10},
        },
        returns="List[Pattern] - Learned patterns with confidence scores",
        example="get_patterns(domain='security', limit=5)",
        entry_point="get_patterns",
        dependencies=["athena.consolidation", "athena.manager"],
    ))


if __name__ == "__main__":
    # Example: Generate tools
    gen = ToolsGenerator(output_dir="/tmp/athena_tools_test")
    register_core_tools(gen)
    gen.generate_all()
    print(f"Generated tools in {gen.output_dir}")
