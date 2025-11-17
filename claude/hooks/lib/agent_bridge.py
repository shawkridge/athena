"""Agent Bridge - Synchronous wrapper for agent operations from hooks.

This module provides synchronous access to agent operations from shell hooks,
similar to memory_bridge.py but for agent coordination.

Agents run asynchronously, but hooks are synchronous, so we use asyncio.run()
to bridge the gap. This keeps agents in the core system while making them
accessible from hooks.

Used by:
- session-start.sh: Initialize MemoryCoordinatorAgent
- post-tool-use.sh: Notify MemoryCoordinatorAgent of tool execution
- session-end.sh: Trigger PatternExtractorAgent for consolidation
"""

import sys
import os
import logging
import asyncio
from typing import Any, Dict, Optional, List

# Configure logging
log_level = logging.DEBUG if os.environ.get('DEBUG') else logging.WARNING
logging.basicConfig(level=log_level, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)


class AgentBridge:
    """Synchronous bridge to Athena agents.

    Provides methods to interact with agents from synchronous hooks.
    Uses asyncio.run() to execute async agent operations.
    """

    def __init__(self):
        """Initialize agent bridge."""
        self.session_id = os.environ.get('CLAUDE_SESSION_ID', 'default-session')
        logger.debug(f"AgentBridge initialized for session {self.session_id}")

    def initialize_memory_coordinator(self) -> Dict[str, Any]:
        """Initialize the MemoryCoordinatorAgent for this session.

        The agent will observe tool executions and user interactions during
        the session, making autonomous memory storage decisions.

        Returns:
            Status dictionary with initialization results
        """
        try:
            # Import here to avoid circular dependencies
            from athena.agents.memory_coordinator import MemoryCoordinatorAgent

            # Create agent instance
            agent = MemoryCoordinatorAgent()

            logger.info(f"MemoryCoordinatorAgent initialized (ID: {agent.agent_id})")

            return {
                "status": "success",
                "agent_id": agent.agent_id,
                "agent_type": agent.agent_type,
                "decisions_made": agent.decisions_made,
                "memories_stored": agent.memories_stored,
            }

        except Exception as e:
            logger.error(f"Failed to initialize MemoryCoordinatorAgent: {e}")
            return {
                "status": "error",
                "error": str(e),
            }

    def notify_tool_execution(
        self,
        tool_name: str,
        input_summary: str,
        output_summary: str,
        success: bool,
    ) -> Dict[str, Any]:
        """Notify MemoryCoordinatorAgent of a tool execution.

        The agent will decide if this is worth remembering based on:
        - Tool type and impact
        - Success/failure status
        - Content novelty
        - Importance to future sessions

        Args:
            tool_name: Name of the tool executed
            input_summary: Brief summary of tool input
            output_summary: Brief summary of tool output
            success: Whether execution succeeded

        Returns:
            Decision from agent about whether to remember this
        """
        try:
            async def async_notify():
                from athena.agents.memory_coordinator import MemoryCoordinatorAgent

                agent = MemoryCoordinatorAgent()

                context = {
                    "type": "tool_execution",
                    "tool_name": tool_name,
                    "input": input_summary,
                    "output": output_summary,
                    "success": success,
                    "content": f"Tool {tool_name} executed: {output_summary}",
                    "importance": 0.7 if success else 0.9,  # Failures are more important
                }

                # Check if worth remembering
                should_remember = await agent.should_remember(context)

                if should_remember:
                    # Choose memory type
                    memory_type = await agent.choose_memory_type(context)

                    # Store in appropriate layer
                    if memory_type == "episodic":
                        from athena.episodic.operations import remember
                        event_id = await remember(
                            content=f"Tool execution: {tool_name}\n{output_summary}",
                            tags=["tool-execution", tool_name],
                            source="hook:post-tool-use",
                            importance=0.7 if success else 0.9,
                        )
                        return {
                            "decided": True,
                            "memory_type": "episodic",
                            "event_id": str(event_id),
                            "tool_name": tool_name,
                        }
                    elif memory_type == "semantic":
                        from athena.memory.operations import store
                        fact_id = await store(
                            content=f"Tool {tool_name} behavior: {output_summary}",
                            topics=["tool-execution", tool_name],
                        )
                        return {
                            "decided": True,
                            "memory_type": "semantic",
                            "fact_id": str(fact_id),
                            "tool_name": tool_name,
                        }
                else:
                    return {
                        "decided": False,
                        "reason": "Not important enough",
                        "tool_name": tool_name,
                    }

            # Run async code
            result = asyncio.run(async_notify())
            logger.info(f"Tool notification processed: {result}")
            return result

        except Exception as e:
            logger.error(f"Failed to notify tool execution: {e}")
            return {
                "status": "error",
                "error": str(e),
            }

    def extract_session_patterns(self) -> Dict[str, Any]:
        """Trigger PatternExtractorAgent to consolidate session learning.

        Called at session end. The agent will:
        1. Retrieve recent episodic events from this session
        2. Use consolidation layer to extract patterns
        3. Store learned procedures for reuse
        4. Prepare summary for next session

        Returns:
            Extraction results with patterns found and procedures extracted
        """
        try:
            async def async_extract():
                from athena.agents.pattern_extractor import PatternExtractorAgent

                agent = PatternExtractorAgent()

                result = await agent.extract_patterns_from_session(
                    session_id=self.session_id,
                    min_confidence=0.8,
                )

                return result

            # Run async code
            result = asyncio.run(async_extract())
            logger.info(f"Pattern extraction completed: {result}")
            return result

        except Exception as e:
            logger.error(f"Failed to extract patterns: {e}")
            return {
                "status": "error",
                "error": str(e),
            }

    def get_agent_statistics(self) -> Dict[str, Any]:
        """Get current statistics from both agents.

        Returns:
            Combined statistics about agent activity this session
        """
        try:
            async def async_get_stats():
                from athena.agents.memory_coordinator import MemoryCoordinatorAgent
                from athena.agents.pattern_extractor import PatternExtractorAgent

                mem_agent = MemoryCoordinatorAgent()
                pat_agent = PatternExtractorAgent()

                return {
                    "memory_coordinator": {
                        "decisions_made": mem_agent.decisions_made,
                        "memories_stored": mem_agent.memories_stored,
                        "skipped": mem_agent.skipped,
                    },
                    "pattern_extractor": {
                        "patterns_extracted": pat_agent.patterns_extracted,
                        "consolidation_runs": pat_agent.consolidation_runs,
                        "last_run": pat_agent.last_run.isoformat() if pat_agent.last_run else None,
                    },
                }

            # Run async code
            return asyncio.run(async_get_stats())

        except Exception as e:
            logger.error(f"Failed to get agent statistics: {e}")
            return {
                "status": "error",
                "error": str(e),
            }


# Global singleton
_bridge: Optional[AgentBridge] = None


def get_agent_bridge() -> AgentBridge:
    """Get or create the global agent bridge instance.

    Returns:
        AgentBridge instance
    """
    global _bridge
    if _bridge is None:
        _bridge = AgentBridge()
    return _bridge


# Convenience functions
def initialize_memory_coordinator() -> Dict[str, Any]:
    """Initialize MemoryCoordinatorAgent."""
    bridge = get_agent_bridge()
    return bridge.initialize_memory_coordinator()


def notify_tool_execution(
    tool_name: str,
    input_summary: str,
    output_summary: str,
    success: bool,
) -> Dict[str, Any]:
    """Notify agents of tool execution."""
    bridge = get_agent_bridge()
    return bridge.notify_tool_execution(tool_name, input_summary, output_summary, success)


def extract_session_patterns() -> Dict[str, Any]:
    """Extract patterns from session."""
    bridge = get_agent_bridge()
    return bridge.extract_session_patterns()


def get_agent_statistics() -> Dict[str, Any]:
    """Get agent statistics."""
    bridge = get_agent_bridge()
    return bridge.get_agent_statistics()
