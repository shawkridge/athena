"""MCP tools for Phase 7.1 Event Forwarding

Exposes event forwarding capabilities via MCP interface:
- forward_execution_event: Forward a single execution trace
- get_forwarding_status: Get forwarding statistics
- get_forwarding_log: Retrieve forwarding history
"""

from typing import Optional

from athena.mcp.handlers import mcp


def register_phase7_1_tools(server):
    """Register Phase 7.1 MCP tools on the server

    Args:
        server: MemoryMCPServer instance
    """

    @mcp.tool()
    async def forward_execution_event(self, execution_id: str) -> dict:
        """Manually forward an execution trace to episodic memory

        Converts an ExecutionTrace from AI Coordination to an EpisodicEvent
        in Memory-MCP for consolidation and learning.

        Args:
            execution_id: ID of ExecutionTrace to forward

        Returns:
            dict with status, execution_id, episodic_event_id
        """
        try:
            # Get the execution trace
            execution_store = self.execution_store
            trace = execution_store.get(execution_id)

            if not trace:
                return {
                    "status": "error",
                    "error": f"ExecutionTrace {execution_id} not found",
                }

            # Forward it
            event_id = self.forwarder.forward_execution_trace(trace)

            return {
                "status": "success",
                "execution_id": execution_id,
                "episodic_event_id": str(event_id),
                "message": f"Forwarded execution {execution_id} to episodic memory",
            }
        except Exception as e:
            return {
                "status": "error",
                "execution_id": execution_id,
                "error": str(e),
            }

    @mcp.tool()
    async def forward_thinking_trace(self, trace_id: str) -> dict:
        """Manually forward a thinking trace to episodic memory

        Converts a ThinkingTrace (reasoning data) to an EpisodicEvent
        for pattern extraction and learning.

        Args:
            trace_id: ID of ThinkingTrace to forward

        Returns:
            dict with status, trace_id, episodic_event_id
        """
        try:
            # Get the thinking trace
            thinking_store = self.thinking_trace_store
            trace = thinking_store.get(trace_id)

            if not trace:
                return {
                    "status": "error",
                    "error": f"ThinkingTrace {trace_id} not found",
                }

            # Forward it
            event_id = self.forwarder.forward_thinking_trace(trace)

            return {
                "status": "success",
                "trace_id": trace_id,
                "episodic_event_id": str(event_id),
                "message": f"Forwarded thinking trace {trace_id} to episodic memory",
            }
        except Exception as e:
            return {
                "status": "error",
                "trace_id": trace_id,
                "error": str(e),
            }

    @mcp.tool()
    async def get_forwarding_status(self) -> dict:
        """Get event forwarding status and statistics

        Returns statistics about what's been forwarded from AI Coordination
        to Memory-MCP, broken down by event type.

        Returns:
            dict with total_forwarded, by_type, last_forward_time
        """
        try:
            status = self.forwarder.get_forwarding_status()

            if not status:
                return {
                    "status": "error",
                    "error": "Forwarding store not initialized",
                }

            return {
                "status": "success",
                "total_forwarded": status["total_forwarded"],
                "by_source_type": status["by_source_type"],
                "pending_forwarding": status["pending"],
                "message": f"{status['total_forwarded']} events forwarded to episodic memory",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    @mcp.tool()
    async def get_forwarding_log(
        self,
        source_type: Optional[str] = None,
        limit: int = 20,
    ) -> dict:
        """Get event forwarding log

        Returns the history of forwarded events, optionally filtered by source type.

        Args:
            source_type: Optional filter (ExecutionTrace, ThinkingTrace, etc)
            limit: Maximum number of entries to return

        Returns:
            dict with forwarding_log (list of entries)
        """
        try:
            forwarding_store = self.forwarding_store

            if not forwarding_store:
                return {
                    "status": "error",
                    "error": "Forwarding store not initialized",
                }

            if source_type:
                entries = forwarding_store.get_forwarding_log_by_source(source_type)
            else:
                entries = forwarding_store.get_all_forwarding_logs(limit=limit)

            return {
                "status": "success",
                "forwarding_log": entries[:limit],
                "total_entries": len(entries),
                "message": f"Retrieved {len(entries[:limit])} forwarding log entries",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    @mcp.tool()
    async def get_forwarding_stats(self) -> dict:
        """Get detailed forwarding statistics

        Returns comprehensive statistics about event forwarding,
        including per-type counts and timing.

        Returns:
            dict with stats by source type
        """
        try:
            forwarding_store = self.forwarding_store

            if not forwarding_store:
                return {
                    "status": "error",
                    "error": "Forwarding store not initialized",
                }

            stats = forwarding_store.get_forwarding_stats()

            return {
                "status": "success",
                "statistics": stats,
                "message": f"Forwarding stats for {len(stats)} event types",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }
