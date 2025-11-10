"""System monitoring and health check tools."""

import logging
from typing import Optional, Any
from .base import BaseTool, ToolMetadata, ToolResult, ToolStatus

logger = logging.getLogger(__name__)


class SystemHealthCheckTool(BaseTool):
    """Check overall system health and component status."""

    def __init__(self, mcp_server):
        """Initialize system health check tool.

        Args:
            mcp_server: MCP server instance for accessing health components
        """
        metadata = ToolMetadata(
            name="check_system_health",
            description="Check overall system health and component status",
            category="system",
            version="1.0",
            parameters={
                "component": {
                    "type": "string",
                    "description": "Specific component to check (optional, default: all)",
                    "default": None
                }
            },
            returns={
                "status": {
                    "type": "string",
                    "description": "Health status (healthy, degraded, unhealthy)"
                },
                "component": {
                    "type": "string",
                    "description": "Component checked"
                },
                "issues": {
                    "type": "array",
                    "description": "List of detected issues"
                }
            },
            tags=["health", "monitoring", "system"]
        )
        super().__init__(metadata)
        self.mcp_server = mcp_server

    async def execute(self, **params) -> ToolResult:
        """Execute health check operation.

        Args:
            component: Specific component to check (optional)

        Returns:
            ToolResult with health status
        """
        try:
            component = params.get("component")

            # Lazy initialize HealthChecker
            if not hasattr(self.mcp_server, '_health_checker'):
                try:
                    from athena.resilience.health import HealthChecker
                    self.mcp_server._health_checker = HealthChecker()
                except ImportError:
                    self.logger.warning("HealthChecker not available, using fallback")
                    return ToolResult.success(
                        data={
                            "status": "unknown",
                            "component": component or "all",
                            "issues": [],
                            "message": "HealthChecker not available"
                        },
                        message="Health check unavailable (module not found)"
                    )

            # Check health
            try:
                health = await self.mcp_server._health_checker.check(
                    component=component
                )
            except Exception as health_err:
                self.logger.debug(f"Health check error: {health_err}")
                health = {
                    "status": "unknown",
                    "issues": [f"Check error: {str(health_err)}"]
                }

            result_data = {
                "status": health.get("status", "unknown"),
                "component": component or "all",
                "issues": health.get("issues", []),
                "issue_count": len(health.get("issues", []))
            }

            self.log_execution(params, ToolResult.success(data=result_data))
            return ToolResult.success(
                data=result_data,
                message=f"Health: {health.get('status', 'unknown')}"
            )

        except Exception as e:
            self.logger.exception(f"Unexpected error in health check: {e}")
            return ToolResult.error(f"Health check failed: {str(e)}")


class HealthReportTool(BaseTool):
    """Generate comprehensive health report with metrics."""

    def __init__(self, mcp_server):
        """Initialize health report tool.

        Args:
            mcp_server: MCP server instance for accessing health components
        """
        metadata = ToolMetadata(
            name="get_health_report",
            description="Generate comprehensive health report with optional detailed metrics",
            category="system",
            version="1.0",
            parameters={
                "include_metrics": {
                    "type": "boolean",
                    "description": "Include detailed performance metrics",
                    "default": False
                },
                "format": {
                    "type": "string",
                    "description": "Report format (summary, detailed, json)",
                    "default": "summary"
                }
            },
            returns={
                "summary": {
                    "type": "string",
                    "description": "Health summary"
                },
                "metrics": {
                    "type": "object",
                    "description": "System metrics if requested"
                },
                "timestamp": {
                    "type": "string",
                    "description": "Report generation timestamp"
                }
            },
            tags=["health", "reporting", "metrics"]
        )
        super().__init__(metadata)
        self.mcp_server = mcp_server

    async def execute(self, **params) -> ToolResult:
        """Execute health report operation.

        Args:
            include_metrics: Include performance metrics (optional)
            format: Report format (optional)

        Returns:
            ToolResult with health report
        """
        try:
            include_metrics = params.get("include_metrics", False)
            report_format = params.get("format", "summary")

            # Lazy initialize HealthChecker
            if not hasattr(self.mcp_server, '_health_checker'):
                try:
                    from athena.resilience.health import HealthChecker
                    if hasattr(self.mcp_server, 'store') and hasattr(self.mcp_server.store, 'db'):
                        self.mcp_server._health_checker = HealthChecker(self.mcp_server.store.db)
                    else:
                        self.mcp_server._health_checker = HealthChecker()
                except ImportError:
                    self.logger.warning("HealthChecker not available")
                    return ToolResult.success(
                        data={
                            "summary": "Health report unavailable - HealthChecker not found",
                            "metrics": {},
                            "format": report_format
                        },
                        message="Health report unavailable"
                    )

            # Generate report
            try:
                report = await self.mcp_server._health_checker.generate_report(
                    include_metrics=include_metrics
                )
            except Exception as report_err:
                self.logger.debug(f"Report generation error: {report_err}")
                report = {
                    "summary": f"Report generation error: {str(report_err)}",
                    "metrics": {}
                }

            result_data = {
                "summary": report.get("summary", "N/A"),
                "metrics": report.get("metrics", {}) if include_metrics else {},
                "format": report_format,
                "has_metrics": bool(report.get("metrics"))
            }

            self.log_execution(params, ToolResult.success(data=result_data))
            return ToolResult.success(
                data=result_data,
                message="Health report generated successfully"
            )

        except Exception as e:
            self.logger.exception(f"Unexpected error in health report: {e}")
            return ToolResult.error(f"Report generation failed: {str(e)}")


class ConsolidationStatusTool(BaseTool):
    """Check consolidation system status and pending operations."""

    def __init__(self, consolidation_system):
        """Initialize consolidation status tool.

        Args:
            consolidation_system: ConsolidationSystem instance
        """
        metadata = ToolMetadata(
            name="get_consolidation_status",
            description="Check consolidation system status and pending operations",
            category="system",
            version="1.0",
            parameters={},
            returns={
                "status": {
                    "type": "string",
                    "description": "Consolidation status"
                },
                "pending_events": {
                    "type": "integer",
                    "description": "Number of pending events"
                },
                "last_consolidation": {
                    "type": "string",
                    "description": "Timestamp of last consolidation"
                }
            },
            tags=["consolidation", "system"]
        )
        super().__init__(metadata)
        self.consolidation_system = consolidation_system

    async def execute(self, **params) -> ToolResult:
        """Execute consolidation status check.

        Returns:
            ToolResult with consolidation status
        """
        try:
            # Get consolidation stats
            try:
                status_data = {
                    "status": "operational",
                    "pending_events": 0,
                    "last_consolidation": None
                }

                # Try to get actual stats if methods available
                if hasattr(self.consolidation_system, 'get_pending_count'):
                    status_data["pending_events"] = self.consolidation_system.get_pending_count()

                if hasattr(self.consolidation_system, 'get_last_consolidation_time'):
                    last_time = self.consolidation_system.get_last_consolidation_time()
                    if last_time:
                        status_data["last_consolidation"] = last_time.isoformat()

            except Exception as stats_err:
                self.logger.debug(f"Error getting consolidation stats: {stats_err}")
                status_data = {
                    "status": "unavailable",
                    "pending_events": 0,
                    "last_consolidation": None
                }

            self.log_execution(params, ToolResult.success(data=status_data))
            return ToolResult.success(
                data=status_data,
                message="Consolidation status retrieved"
            )

        except Exception as e:
            self.logger.exception(f"Unexpected error in consolidation status: {e}")
            return ToolResult.error(f"Status check failed: {str(e)}")
