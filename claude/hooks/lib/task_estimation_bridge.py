"""Task Estimation Bridge - Synchronous wrapper for adaptive task estimator.

Provides synchronous access to learning-based task estimation from hooks.
Uses in-memory cache for fast estimation without database round-trips.

Used by:
- session-start.sh: Request time estimates for upcoming tasks
- post-task-completion.sh: Learn from completed task execution
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


class TaskEstimationBridge:
    """Synchronous bridge to adaptive task estimator.

    Provides task duration estimates based on learning system.
    """

    def __init__(self):
        """Initialize task estimation bridge."""
        self.session_id = os.environ.get('CLAUDE_SESSION_ID', 'default-session')
        logger.debug(f"TaskEstimationBridge initialized for session {self.session_id}")

    def estimate_task_duration(
        self,
        task_name: str,
        task_type: Optional[str] = None,
        complexity: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Estimate how long a task will take.

        Uses historical execution data from learning system.

        Args:
            task_name: Name of the task
            task_type: Type of task (e.g., "code-review", "testing")
            complexity: Complexity 0.0-1.0
            context: Optional context about the task

        Returns:
            Estimate dictionary with:
            - estimated_minutes: Estimated duration
            - confidence: 0.0-1.0 confidence in estimate
            - reasoning: Why this estimate was chosen
        """
        try:
            async def async_estimate():
                try:
                    from athena.learning.task_estimator import AdaptiveTaskEstimator

                    estimator = AdaptiveTaskEstimator()

                    estimate = await estimator.estimate_task_duration(
                        task_name=task_name,
                        task_type=task_type,
                        complexity=complexity,
                        context=context
                    )

                    return estimate

                except Exception as e:
                    logger.error(f"Failed to estimate task duration: {e}")
                    return {
                        "status": "error",
                        "error": str(e),
                        "estimated_minutes": 30.0,  # Fallback
                        "confidence": 0.0
                    }

            result = asyncio.run(async_estimate())
            return result

        except Exception as e:
            logger.error(f"TaskEstimationBridge.estimate_task_duration failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "estimated_minutes": 30.0,
                "confidence": 0.0
            }

    def learn_from_task_execution(
        self,
        task_type: str,
        estimated_minutes: float,
        actual_minutes: float,
        complexity: Optional[float] = None,
        success: bool = True
    ) -> Dict[str, Any]:
        """Learn from a completed task execution.

        Updates estimator models based on what actually happened.

        Args:
            task_type: Type of task
            estimated_minutes: What was estimated
            actual_minutes: What actually took
            complexity: Complexity of the task (0.0-1.0)
            success: Whether task succeeded

        Returns:
            Learning summary
        """
        try:
            async def async_learn():
                try:
                    from athena.learning.task_estimator import AdaptiveTaskEstimator

                    estimator = AdaptiveTaskEstimator()

                    learning = await estimator.learn_from_execution(
                        task_type=task_type,
                        estimated_minutes=estimated_minutes,
                        actual_minutes=actual_minutes,
                        complexity=complexity,
                        success=success
                    )

                    return learning

                except Exception as e:
                    logger.error(f"Failed to learn from execution: {e}")
                    return {
                        "status": "error",
                        "error": str(e)
                    }

            result = asyncio.run(async_learn())
            return result

        except Exception as e:
            logger.error(f"TaskEstimationBridge.learn_from_task_execution failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    def get_estimation_statistics(self, task_type: str) -> Dict[str, Any]:
        """Get statistics for estimation accuracy.

        Args:
            task_type: Type of task

        Returns:
            Statistics about estimation quality
        """
        try:
            from athena.learning.task_estimator import AdaptiveTaskEstimator

            estimator = AdaptiveTaskEstimator()
            stats = estimator.get_estimation_statistics(task_type)
            return stats

        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {
                "status": "error",
                "error": str(e),
                "task_type": task_type
            }


# Module-level functions for convenient use from hooks
def estimate_task(
    task_name: str,
    task_type: Optional[str] = None,
    complexity: Optional[float] = None,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Estimate task duration.

    Usage from hook:
        from task_estimation_bridge import estimate_task
        estimate = estimate_task("Review PR #123", task_type="code-review", complexity=0.6)
        print(f"Estimated: {estimate['estimated_minutes']:.0f} minutes")
    """
    bridge = TaskEstimationBridge()
    return bridge.estimate_task_duration(
        task_name=task_name,
        task_type=task_type,
        complexity=complexity,
        context=context
    )


def record_task_execution(
    task_type: str,
    estimated_minutes: float,
    actual_minutes: float,
    complexity: Optional[float] = None,
    success: bool = True
) -> Dict[str, Any]:
    """Record a task execution for learning.

    Usage from hook:
        from task_estimation_bridge import record_task_execution
        result = record_task_execution(
            "code-review",
            estimated_minutes=30.0,
            actual_minutes=25.0,
            complexity=0.6,
            success=True
        )
        print(f"Quality: {result['quality']}")
    """
    bridge = TaskEstimationBridge()
    return bridge.learn_from_task_execution(
        task_type=task_type,
        estimated_minutes=estimated_minutes,
        actual_minutes=actual_minutes,
        complexity=complexity,
        success=success
    )


def get_task_stats(task_type: str) -> Dict[str, Any]:
    """Get estimation accuracy statistics for a task type.

    Usage from hook:
        from task_estimation_bridge import get_task_stats
        stats = get_task_stats("code-review")
        print(f"Accuracy: {stats['status']}")
    """
    bridge = TaskEstimationBridge()
    return bridge.get_estimation_statistics(task_type)
