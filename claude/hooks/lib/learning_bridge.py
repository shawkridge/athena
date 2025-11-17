"""Learning Bridge - Synchronous wrapper for learning system operations from hooks.

This module provides synchronous access to the learning system (LearningTracker,
PerformanceProfiler) from shell hooks. Hooks are synchronous but learning operations
are async, so we use asyncio.run() to bridge the gap.

Used by:
- post-tool-use.sh: Track MemoryCoordinatorAgent decisions and performance
- session-end.sh: Record consolidation outcomes and success rates
- post-task-completion.sh: Track task execution vs estimates
"""

import sys
import os
import logging
import asyncio
from typing import Any, Dict, Optional
import json
from datetime import datetime

# Configure logging
log_level = logging.DEBUG if os.environ.get('DEBUG') else logging.WARNING
logging.basicConfig(level=log_level, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)


class LearningBridge:
    """Synchronous bridge to Athena learning system.

    Provides methods to track agent decisions and performance metrics
    from synchronous hooks.
    """

    def __init__(self):
        """Initialize learning bridge."""
        self.session_id = os.environ.get('CLAUDE_SESSION_ID', 'default-session')
        logger.debug(f"LearningBridge initialized for session {self.session_id}")

    def track_agent_decision(
        self,
        agent_name: str,
        decision: str,
        outcome: str,
        success_rate: float,
        execution_time_ms: float = 0.0,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Track an agent decision outcome in the learning system.

        Args:
            agent_name: Name of agent making decision (e.g., "memory-coordinator")
            decision: Description of decision (e.g., "should_remember", "consolidate")
            outcome: Result - one of 'success', 'failure', 'partial', 'error'
            success_rate: Score 0.0-1.0 indicating success
            execution_time_ms: How long decision execution took
            context: Optional context dict with additional metadata

        Returns:
            Status dictionary with tracking result
        """
        try:
            async def async_track():
                try:
                    from athena.core.database import Database
                    from athena.learning.tracker import LearningTracker

                    db = Database()
                    await db.initialize()
                    tracker = LearningTracker(db)

                    outcome_id = await tracker.track_outcome(
                        agent_name=agent_name,
                        decision=decision,
                        outcome=outcome,
                        success_rate=success_rate,
                        execution_time_ms=execution_time_ms,
                        context=context or {},
                        session_id=self.session_id
                    )

                    return {
                        "status": "success",
                        "outcome_id": outcome_id,
                        "agent_name": agent_name,
                        "decision": decision,
                        "success_rate": success_rate
                    }
                except Exception as e:
                    logger.error(f"Failed to track outcome: {e}")
                    return {
                        "status": "error",
                        "error": str(e)
                    }

            # Run async operation synchronously
            result = asyncio.run(async_track())
            return result

        except Exception as e:
            logger.error(f"LearningBridge.track_agent_decision failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    def record_performance(
        self,
        agent_name: str,
        operation: str,
        execution_time_ms: float,
        memory_mb: Optional[float] = None,
        result_size: Optional[int] = None
    ) -> Dict[str, Any]:
        """Record performance metrics for an agent operation.

        Args:
            agent_name: Name of agent
            operation: Operation performed
            execution_time_ms: How long it took
            memory_mb: Optional memory used
            result_size: Optional size of result

        Returns:
            Status dictionary
        """
        try:
            async def async_record():
                try:
                    from athena.core.database import Database
                    from athena.learning.performance_profiler import PerformanceProfiler

                    db = Database()
                    await db.initialize()
                    profiler = PerformanceProfiler(db)

                    profiler.record_execution(
                        agent_name=agent_name,
                        operation=operation,
                        execution_time_ms=execution_time_ms,
                        memory_mb=memory_mb,
                        result_size=result_size
                    )

                    # Get current stats
                    stats = profiler.get_performance_stats(agent_name)

                    return {
                        "status": "success",
                        "agent_name": agent_name,
                        "operation": operation,
                        "execution_time_ms": execution_time_ms,
                        "perf_score": stats.get('performance_score', 0.0),
                        "perf_status": stats.get('status', 'unknown')
                    }
                except Exception as e:
                    logger.error(f"Failed to record performance: {e}")
                    return {
                        "status": "error",
                        "error": str(e)
                    }

            result = asyncio.run(async_record())
            return result

        except Exception as e:
            logger.error(f"LearningBridge.record_performance failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    def get_agent_success_rate(
        self,
        agent_name: str,
        decision: Optional[str] = None,
        time_window_hours: int = 24
    ) -> Dict[str, Any]:
        """Query agent success rate for decision-making.

        This is used by adaptive agents to decide which strategy to use
        based on recent performance.

        Args:
            agent_name: Agent to query
            decision: Specific decision type (optional)
            time_window_hours: Time period to consider

        Returns:
            Success rate dictionary
        """
        try:
            async def async_query():
                try:
                    from athena.core.database import Database
                    from athena.learning.tracker import LearningTracker

                    db = Database()
                    await db.initialize()
                    tracker = LearningTracker(db)

                    success_rate = await tracker.get_success_rate(
                        agent_name=agent_name,
                        decision=decision,
                        time_window_hours=time_window_hours
                    )

                    return {
                        "status": "success",
                        "agent_name": agent_name,
                        "decision": decision,
                        "success_rate": success_rate,
                        "time_window_hours": time_window_hours
                    }
                except Exception as e:
                    logger.error(f"Failed to get success rate: {e}")
                    return {
                        "status": "error",
                        "error": str(e),
                        "success_rate": 0.0  # Fallback
                    }

            result = asyncio.run(async_query())
            return result

        except Exception as e:
            logger.error(f"LearningBridge.get_agent_success_rate failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "success_rate": 0.0
            }

    def get_agent_statistics(self, agent_name: str) -> Dict[str, Any]:
        """Get comprehensive statistics for an agent.

        Used for reporting and decision-making.

        Args:
            agent_name: Agent to analyze

        Returns:
            Statistics dictionary
        """
        try:
            async def async_stats():
                try:
                    from athena.core.database import Database
                    from athena.learning.tracker import LearningTracker

                    db = Database()
                    await db.initialize()
                    tracker = LearningTracker(db)

                    stats = await tracker.get_statistics(agent_name)

                    return {
                        "status": "success",
                        "agent_name": agent_name,
                        "stats": stats
                    }
                except Exception as e:
                    logger.error(f"Failed to get statistics: {e}")
                    return {
                        "status": "error",
                        "error": str(e),
                        "stats": {}
                    }

            result = asyncio.run(async_stats())
            return result

        except Exception as e:
            logger.error(f"LearningBridge.get_agent_statistics failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "stats": {}
            }


# Module-level functions for convenient use from hooks
def track_decision(
    agent_name: str,
    decision: str,
    outcome: str,
    success_rate: float,
    execution_time_ms: float = 0.0,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Track an agent decision outcome.

    Usage from hook:
        from learning_bridge import track_decision
        track_decision("memory-coordinator", "should_remember", "success", 0.9)
    """
    bridge = LearningBridge()
    return bridge.track_agent_decision(
        agent_name=agent_name,
        decision=decision,
        outcome=outcome,
        success_rate=success_rate,
        execution_time_ms=execution_time_ms,
        context=context
    )


def record_perf(
    agent_name: str,
    operation: str,
    execution_time_ms: float,
    memory_mb: Optional[float] = None,
    result_size: Optional[int] = None
) -> Dict[str, Any]:
    """Record performance metrics.

    Usage from hook:
        from learning_bridge import record_perf
        record_perf("memory-coordinator", "notify_tool", 45.5)
    """
    bridge = LearningBridge()
    return bridge.record_performance(
        agent_name=agent_name,
        operation=operation,
        execution_time_ms=execution_time_ms,
        memory_mb=memory_mb,
        result_size=result_size
    )


def get_success_rate(
    agent_name: str,
    decision: Optional[str] = None,
    time_window_hours: int = 24
) -> float:
    """Get agent success rate for decision-making.

    Usage from hook:
        from learning_bridge import get_success_rate
        rate = get_success_rate("memory-coordinator", "should_remember")
        if rate > 0.8:
            # Use this strategy
    """
    bridge = LearningBridge()
    result = bridge.get_agent_success_rate(
        agent_name=agent_name,
        decision=decision,
        time_window_hours=time_window_hours
    )
    return result.get('success_rate', 0.0)
