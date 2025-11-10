"""Tool manager for integrating modular tools with MCP server."""

import logging
from typing import Optional, Dict, Any, List
from .registry import ToolRegistry
from .base import BaseTool, ToolResult, ToolStatus

logger = logging.getLogger(__name__)


class ToolManager:
    """Manages modular tools and their execution within MCP server."""

    def __init__(self, mcp_server):
        """Initialize tool manager.

        Args:
            mcp_server: MemoryMCPServer instance to bind tools to
        """
        self.mcp_server = mcp_server
        self.registry = ToolRegistry()
        self.tools_initialized = False

    def initialize_tools(self) -> None:
        """Initialize and register all modular tools with the server."""
        if self.tools_initialized:
            logger.warning("Tools already initialized, skipping re-initialization")
            return

        try:
            # Import tool classes
            from .memory_tools import (
                RecallTool,
                RememberTool,
                ForgetTool,
                OptimizeTool,
            )
            from .system_tools import (
                SystemHealthCheckTool,
                HealthReportTool,
                ConsolidationStatusTool,
            )
            from .episodic_tools import (
                RecordEventTool,
                RecallEventsTool,
                GetTimelineTool,
            )

            # Initialize memory tools
            recall_tool = RecallTool(
                self.mcp_server.store,
                self.mcp_server.project_manager
            )
            self.registry.register(recall_tool)

            remember_tool = RememberTool(
                self.mcp_server.store,
                self.mcp_server.project_manager
            )
            self.registry.register(remember_tool)

            forget_tool = ForgetTool(
                self.mcp_server.store,
                self.mcp_server.project_manager
            )
            self.registry.register(forget_tool)

            optimize_tool = OptimizeTool(
                self.mcp_server.store,
                self.mcp_server.project_manager
            )
            self.registry.register(optimize_tool)

            # Initialize system tools
            health_check_tool = SystemHealthCheckTool(self.mcp_server)
            self.registry.register(health_check_tool)

            health_report_tool = HealthReportTool(self.mcp_server)
            self.registry.register(health_report_tool)

            consolidation_status_tool = ConsolidationStatusTool(
                self.mcp_server.consolidation_system
            )
            self.registry.register(consolidation_status_tool)

            # Initialize episodic tools
            record_event_tool = RecordEventTool(
                self.mcp_server.episodic_store,
                self.mcp_server.project_manager
            )
            self.registry.register(record_event_tool)

            recall_events_tool = RecallEventsTool(
                self.mcp_server.episodic_store,
                self.mcp_server.project_manager
            )
            self.registry.register(recall_events_tool)

            timeline_tool = GetTimelineTool(
                self.mcp_server.episodic_store,
                self.mcp_server.project_manager
            )
            self.registry.register(timeline_tool)

            self.tools_initialized = True
            stats = self.registry.get_stats()
            logger.info(
                f"Initialized {stats['total_tools']} modular tools "
                f"in {stats['categories']} categories"
            )

        except Exception as e:
            logger.error(f"Failed to initialize tools: {e}", exc_info=True)
            raise

    async def execute_tool(self, tool_name: str, **params) -> ToolResult:
        """Execute a tool by name.

        Args:
            tool_name: Name of the tool to execute
            **params: Parameters to pass to the tool

        Returns:
            ToolResult with execution status and data
        """
        try:
            tool = self.registry.get(tool_name)
            if not tool:
                return ToolResult.error(f"Tool '{tool_name}' not found in registry")

            logger.debug(f"Executing tool: {tool_name}")
            result = await tool.execute(**params)
            return result

        except Exception as e:
            logger.error(f"Error executing tool '{tool_name}': {e}", exc_info=True)
            return ToolResult.error(f"Tool execution failed: {str(e)}")

    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """Get a tool instance by name.

        Args:
            tool_name: Name of the tool

        Returns:
            Tool instance or None if not found
        """
        return self.registry.get(tool_name)

    def list_tools(self) -> List[Dict[str, Any]]:
        """List all registered tools with metadata.

        Returns:
            List of tool metadata dictionaries
        """
        tools = []
        for tool in self.registry.list_tools():
            tools.append({
                "name": tool.metadata.name,
                "description": tool.metadata.description,
                "category": tool.metadata.category,
                "version": tool.metadata.version,
                "parameters": tool.metadata.parameters,
                "tags": tool.metadata.tags,
            })
        return tools

    def get_tools_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get all tools in a specific category.

        Args:
            category: Category name

        Returns:
            List of tool metadata for the category
        """
        tools = []
        for tool in self.registry.list_by_category(category):
            tools.append({
                "name": tool.metadata.name,
                "description": tool.metadata.description,
                "category": tool.metadata.category,
                "version": tool.metadata.version,
                "parameters": tool.metadata.parameters,
                "tags": tool.metadata.tags,
            })
        return tools

    def get_tool_metadata(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific tool.

        Args:
            tool_name: Name of the tool

        Returns:
            Tool metadata dictionary or None
        """
        metadata = self.registry.get_metadata(tool_name)
        if metadata:
            return metadata.to_dict()
        return None

    def get_categories(self) -> List[str]:
        """Get list of all tool categories.

        Returns:
            List of category names
        """
        return self.registry.get_categories()

    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics.

        Returns:
            Dictionary with statistics
        """
        return self.registry.get_stats()
