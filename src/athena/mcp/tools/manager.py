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
            from .planning_tools import (
                DecomposeTool,
                ValidatePlanTool,
                VerifyPlanTool,
                OptimizePlanTool,
            )
            from .retrieval_tools import (
                SmartRetrieveTool,
                AnalyzeCoverageTool,
            )
            from .integration_tools import (
                ConsolidateTool,
                RunConsolidationTool,
            )
            from .agent_optimization_tools import (
                TuneAgentTool,
                AnalyzeAgentPerformanceTool,
            )
            from .skill_optimization_tools import (
                EnhanceSkillTool,
                MeasureSkillEffectivenessTool,
            )
            from .hook_coordination_tools import (
                RegisterHookTool,
                ManageHooksTool,
                CoordinateHooksTool,
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

            # Initialize planning tools
            decompose_tool = DecomposeTool(self.mcp_server.planning_store)
            self.registry.register(decompose_tool)

            validate_plan_tool = ValidatePlanTool(self.mcp_server.plan_validator)
            self.registry.register(validate_plan_tool)

            verify_plan_tool = VerifyPlanTool(self.mcp_server.formal_verification)
            self.registry.register(verify_plan_tool)

            optimize_plan_tool = OptimizePlanTool(self.mcp_server.planning_store)
            self.registry.register(optimize_plan_tool)

            # Initialize retrieval tools
            smart_retrieve_tool = SmartRetrieveTool(
                self.mcp_server.store,
                self.mcp_server.project_manager
            )
            self.registry.register(smart_retrieve_tool)

            analyze_coverage_tool = AnalyzeCoverageTool(
                self.mcp_server.store,
                self.mcp_server.project_manager
            )
            self.registry.register(analyze_coverage_tool)

            # Initialize integration tools
            consolidate_tool = ConsolidateTool(
                self.mcp_server.consolidation_system,
                self.mcp_server.project_manager
            )
            self.registry.register(consolidate_tool)

            run_consolidation_tool = RunConsolidationTool(
                self.mcp_server.consolidation_system,
                self.mcp_server.project_manager
            )
            self.registry.register(run_consolidation_tool)

            # Initialize agent optimization tools
            tune_agent_tool = TuneAgentTool()
            self.registry.register(tune_agent_tool)

            analyze_agent_perf_tool = AnalyzeAgentPerformanceTool()
            self.registry.register(analyze_agent_perf_tool)

            # Initialize skill optimization tools
            enhance_skill_tool = EnhanceSkillTool()
            self.registry.register(enhance_skill_tool)

            measure_skill_tool = MeasureSkillEffectivenessTool()
            self.registry.register(measure_skill_tool)

            # Initialize hook coordination tools
            register_hook_tool = RegisterHookTool()
            self.registry.register(register_hook_tool)

            manage_hooks_tool = ManageHooksTool()
            self.registry.register(manage_hooks_tool)

            coordinate_hooks_tool = CoordinateHooksTool()
            self.registry.register(coordinate_hooks_tool)

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
