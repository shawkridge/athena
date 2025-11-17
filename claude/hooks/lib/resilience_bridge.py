"""Resilience Bridge - Robust error handling for hooks.

Ensures hooks continue working even when infrastructure fails.
Provides:
- Circuit breaker pattern (auto-recovery)
- Local fallback storage
- Graceful degradation
- Health monitoring

Used by all hook modules for robust operation.
"""

import sys
import os
import logging
import asyncio
from typing import Optional, Dict, Any

# Configure logging
log_level = logging.DEBUG if os.environ.get('DEBUG') else logging.WARNING
logging.basicConfig(level=log_level, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)


class ResilientHookBridge:
    """Resilient wrapper for all hook operations."""

    def __init__(self):
        """Initialize resilient bridge."""
        self.session_id = os.environ.get('CLAUDE_SESSION_ID', 'default-session')

    def track_outcome_safely(
        self,
        agent_name: str,
        decision: str,
        outcome: str,
        success_rate: float,
        execution_time_ms: float = 0.0,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Track outcome with automatic fallback if database fails.

        Never fails the hook - always returns a result.

        Args:
            agent_name: Agent name
            decision: Decision made
            outcome: Result
            success_rate: Success metric
            execution_time_ms: Execution time
            context: Additional context

        Returns:
            Status dictionary (always succeeds)
        """
        try:
            async def async_track():
                try:
                    from athena.learning.resilience import ResilientLearningBridge, validate_outcome

                    # Validate input first
                    if not validate_outcome(agent_name, decision, outcome, success_rate):
                        return {
                            "status": "invalid_input",
                            "message": "Outcome validation failed"
                        }

                    bridge = ResilientLearningBridge()
                    result = await bridge.track_outcome_resilient(
                        agent_name=agent_name,
                        decision=decision,
                        outcome=outcome,
                        success_rate=success_rate,
                        execution_time_ms=execution_time_ms,
                        context=context
                    )

                    return result

                except Exception as e:
                    # Last resort: return error status
                    logger.error(f"Unexpected error in track_outcome_safely: {e}")
                    return {
                        "status": "error",
                        "error": str(e),
                        "fallback": "none"
                    }

            result = asyncio.run(async_track())
            return result

        except Exception as e:
            # Outer try-catch: asyncio.run failed
            logger.error(f"Critical error: {e}")
            return {
                "status": "critical_error",
                "error": str(e)
            }

    def analyze_outcome_safely(
        self,
        success_rate: float,
        events_processed: int,
        patterns_extracted: int,
        execution_time_ms: float,
        strategy: str = "balanced"
    ) -> Dict[str, Any]:
        """Analyze outcome with graceful degradation.

        Args:
            success_rate: Success metric
            events_processed: Number of events
            patterns_extracted: Number of patterns
            execution_time_ms: Execution time
            strategy: Strategy used

        Returns:
            Analysis (LLM-based or heuristic)
        """
        try:
            async def async_analyze():
                try:
                    from athena.learning.resilience import ResilientLearningBridge

                    bridge = ResilientLearningBridge()
                    result = await bridge.analyze_outcome_resilient(
                        success_rate=success_rate,
                        events_processed=events_processed,
                        patterns_extracted=patterns_extracted,
                        execution_time_ms=execution_time_ms,
                        strategy=strategy
                    )

                    return result

                except Exception as e:
                    logger.error(f"Analysis failed: {e}")
                    # Return minimal fallback
                    return {
                        "status": "error",
                        "analysis": {
                            "reason": "Analysis unavailable",
                            "confidence": 0.0,
                            "recommendations": []
                        }
                    }

            result = asyncio.run(async_analyze())
            return result

        except Exception as e:
            logger.error(f"Critical error in analyze_outcome_safely: {e}")
            return {
                "status": "critical_error",
                "error": str(e)
            }

    def get_system_health(self) -> Dict[str, Any]:
        """Check health of dependent systems.

        Used for monitoring and debugging.

        Returns:
            Health status
        """
        try:
            from athena.learning.resilience import ResilientLearningBridge

            bridge = ResilientLearningBridge()
            health = bridge.get_service_health()

            return {
                "status": "ok",
                "services": health
            }

        except Exception as e:
            logger.error(f"Failed to get health status: {e}")
            return {
                "status": "error",
                "error": str(e)
            }


# Module-level function for convenient use
def track_safely(
    agent_name: str,
    decision: str,
    outcome: str,
    success_rate: float,
    execution_time_ms: float = 0.0,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Track outcome with full fallback support.

    Usage from hook:
        from resilience_bridge import track_safely
        result = track_safely(
            "memory-coordinator",
            "should_remember",
            "success",
            0.95
        )
        print(f"Stored in: {result.get('stored_in')}")
    """
    bridge = ResilientHookBridge()
    return bridge.track_outcome_safely(
        agent_name=agent_name,
        decision=decision,
        outcome=outcome,
        success_rate=success_rate,
        execution_time_ms=execution_time_ms,
        context=context
    )


def analyze_safely(
    success_rate: float,
    events_processed: int,
    patterns_extracted: int,
    execution_time_ms: float,
    strategy: str = "balanced"
) -> Dict[str, Any]:
    """Analyze outcome with graceful degradation.

    Usage from hook:
        from resilience_bridge import analyze_safely
        analysis = analyze_safely(0.85, 100, 15, 2500.0)
        print(f"Type: {analysis.get('reasoning_type')}")
    """
    bridge = ResilientHookBridge()
    return bridge.analyze_outcome_safely(
        success_rate=success_rate,
        events_processed=events_processed,
        patterns_extracted=patterns_extracted,
        execution_time_ms=execution_time_ms,
        strategy=strategy
    )


def check_health() -> Dict[str, Any]:
    """Check system health.

    Usage from hook:
        from resilience_bridge import check_health
        health = check_health()
        if health['services']['database']['available']:
            print("Database is healthy")
    """
    bridge = ResilientHookBridge()
    return bridge.get_system_health()
