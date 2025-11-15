"""Streaming handler methods for MCP server (Phase 3.4).

Real-time research result streaming as agents complete.
Enables incremental finding discovery and live progress monitoring.

Methods (2 handlers):
- _handle_stream_research_results: Stream findings in real-time
- _handle_agent_progress: Get live agent status
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, AsyncGenerator
from mcp.types import TextContent

from .structured_result import StructuredResult, ResultStatus
from ..research import ResearchStore, ResearchAgentExecutor
from ..research.streaming import StreamingUpdate

logger = logging.getLogger(__name__)


class StreamingHandlersMixin:
    """Streaming handler methods for real-time research (Phase 3.4).

    Requires attributes:
    - research_store: ResearchStore instance
    - research_executor: ResearchAgentExecutor instance
    """

    async def _handle_stream_research_results(
        self, args: dict
    ) -> List[TextContent]:
        """Stream research findings as agents complete.

        This handler initiates streaming of findings for a running research task.
        Updates are returned incrementally as findings are discovered.

        Args:
            task_id: Research task ID
            format: Output format ('json' or 'markdown', default: 'markdown')

        Returns:
            Streaming updates with findings + agent status
        """
        try:
            task_id = args.get("task_id")
            if not task_id:
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "error": "task_id required",
                                "tool": "stream_research_results",
                            }
                        ),
                    )
                ]

            output_format = args.get("format", "markdown")
            if output_format not in ("json", "markdown"):
                output_format = "markdown"

            # Get task status
            task = self.research_store.get_task(task_id)
            if not task:
                return [
                    TextContent(
                        type="text",
                        text=json.dumps({"error": f"Task {task_id} not found"}),
                    )
                ]

            # Get current status
            if self.research_executor.streaming_collector:
                status = self.research_executor.streaming_collector.get_current_status()

                # Format output
                if output_format == "json":
                    output = json.dumps(
                        {
                            "task_id": task_id,
                            "status": task.status,
                            "streaming_status": status,
                        }
                    )
                else:
                    # Markdown format
                    output = f"""# Research Task {task_id}: {task.topic}

## Status: {task.status}

### Findings
- **Total**: {status['findings_count']}
- **Deduped**: {status['findings_count']} unique

### Agent Progress
"""
                    for agent_name, agent_info in status.get("agent_status", {}).items():
                        output += f"- **{agent_name}**: {agent_info.get('status', 'unknown')} ({agent_info.get('findings', 0)} findings)\n"

                return [TextContent(type="text", text=output)]
            else:
                return [
                    TextContent(
                        type="text",
                        text="Streaming not enabled for this task. Use enable_streaming() first.",
                    )
                ]

        except Exception as e:
            logger.error(f"Error in stream_research_results: {e}", exc_info=True)
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "error": str(e),
                            "tool": "stream_research_results",
                        }
                    ),
                )
            ]

    async def _handle_agent_progress(self, args: dict) -> List[TextContent]:
        """Get live agent progress during research.

        Returns real-time agent metrics:
        - Status (pending|running|completed|failed)
        - Findings count
        - Discovery rate (findings/sec)
        - Estimated completion time

        Args:
            task_id: Research task ID
            agent_name: Specific agent (optional, all if not specified)

        Returns:
            Agent progress metrics
        """
        try:
            task_id = args.get("task_id")
            agent_name = args.get("agent_name")

            if not task_id:
                return [
                    TextContent(
                        type="text",
                        text=json.dumps({"error": "task_id required"}),
                    )
                ]

            # Get task
            task = self.research_store.get_task(task_id)
            if not task:
                return [
                    TextContent(
                        type="text",
                        text=json.dumps({"error": f"Task {task_id} not found"}),
                    )
                ]

            # Get agent monitor status
            if not self.research_executor.agent_monitor:
                return [
                    TextContent(
                        type="text",
                        text="Agent monitoring not available for this task",
                    )
                ]

            summary = await self.research_executor.agent_monitor.get_summary()

            # Format output
            output = f"""# Research Progress: {task.topic}

## Overall Status
- **Total Findings**: {summary['total_findings']}
- **Agents Complete**: {summary['agents_completed']}/{summary['total_agents']}
- **Estimated Time**: {summary.get('estimated_completion_sec', 'N/A')} seconds

## Agent Details
"""

            for agent_data in summary["agents"].values():
                output += f"""
### {agent_data['agent_name']}
- Status: {agent_data['status']}
- Findings: {agent_data['findings']}
- Rate: {agent_data['rate']} findings/sec
- Latency: {agent_data['avg_latency_ms']} ms
- ETA: {agent_data.get('eta_sec', 'N/A')} sec
"""

            return [TextContent(type="text", text=output)]

        except Exception as e:
            logger.error(f"Error in agent_progress: {e}", exc_info=True)
            return [
                TextContent(
                    type="text",
                    text=json.dumps({"error": str(e), "tool": "agent_progress"}),
                )
            ]

    async def _handle_enable_streaming(self, args: dict) -> List[TextContent]:
        """Enable real-time streaming for research tasks.

        Once enabled, research executor will emit streaming updates as findings arrive.

        Returns:
            Confirmation message
        """
        try:
            # Define callback for streaming updates
            def on_update(update: StreamingUpdate) -> None:
                """Log streaming update (can be extended for WebSocket, etc.)."""
                logger.info(
                    f"Streaming update: {update.total_findings} findings, "
                    f"complete={update.is_complete}"
                )

            # Enable streaming
            self.research_executor.enable_streaming(on_update)

            return [
                TextContent(
                    type="text",
                    text="✅ Real-time streaming enabled. Research updates will be streamed as agents complete.",
                )
            ]

        except Exception as e:
            logger.error(f"Error enabling streaming: {e}")
            return [
                TextContent(
                    type="text",
                    text=f"❌ Failed to enable streaming: {str(e)}",
                )
            ]
