"""Adaptive Task Estimator - Learns from execution history to improve time estimates.

Uses learning outcomes (estimated vs actual execution time) to:
- Identify estimation patterns (underestimate, overestimate, accurate)
- Provide better estimates for similar future tasks
- Adapt estimates based on context (task type, complexity, etc.)
- Track estimation accuracy trends

Implements adaptive task execution timing based on learning system.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class AdaptiveTaskEstimator:
    """Estimates task duration using learning data and historical patterns.

    Learns from past task executions to improve future estimates.
    """

    def __init__(self, db: Optional[Any] = None):
        """Initialize estimator.

        Args:
            db: Optional database instance for storing estimates
        """
        self.db = db
        self._estimation_cache = {}  # Cache of task type -> estimate patterns

    async def estimate_task_duration(
        self,
        task_name: str,
        task_type: Optional[str] = None,
        complexity: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Estimate how long a task will take.

        Uses historical data to provide smart estimates.

        Args:
            task_name: Name of the task
            task_type: Type of task (e.g., "code-review", "testing", "refactor")
            complexity: Estimated complexity 0.0-1.0
            context: Additional context about the task

        Returns:
            Estimate with:
            - estimated_minutes: Estimated duration
            - confidence: 0.0-1.0 confidence in estimate
            - reasoning: Why this estimate was chosen
            - historical_base: What historical data was used
        """
        # Default estimate if no history
        default_estimate = self._get_default_estimate(task_type, complexity)

        try:
            # Get historical data for this task type
            historical_data = await self._get_historical_data(task_type or "general")

            if not historical_data:
                return {
                    "status": "success",
                    "estimated_minutes": default_estimate,
                    "confidence": 0.3,  # Low confidence with no history
                    "reasoning": "No historical data - using default estimate",
                    "historical_base": [],
                }

            # Analyze patterns
            patterns = self._analyze_patterns(historical_data)

            # Apply complexity adjustment
            adjusted_estimate = default_estimate
            if complexity:
                # Higher complexity = longer estimate
                complexity_factor = 0.8 + (complexity * 0.4)  # 0.8x - 1.2x
                adjusted_estimate = default_estimate * complexity_factor

            # Adjust based on trend (improving or degrading estimates)
            if patterns["trend"] == "improving":
                adjusted_estimate = adjusted_estimate * 0.95  # 5% faster
            elif patterns["trend"] == "degrading":
                adjusted_estimate = adjusted_estimate * 1.05  # 5% slower

            return {
                "status": "success",
                "estimated_minutes": adjusted_estimate,
                "confidence": patterns.get("confidence", 0.6),
                "reasoning": patterns.get("reasoning", "Based on historical averages"),
                "historical_base": patterns.get("summary", []),
                "adjustments_applied": patterns.get("adjustments", []),
            }

        except Exception as e:
            logger.error(f"Failed to estimate task duration: {e}")
            return {
                "status": "error",
                "error": str(e),
                "estimated_minutes": default_estimate,
                "confidence": 0.0,
            }

    async def evaluate_estimation_quality(
        self, task_name: str, estimated_minutes: float, actual_minutes: float
    ) -> Dict[str, Any]:
        """Evaluate how accurate an estimate was.

        Args:
            task_name: Name of the task
            estimated_minutes: What we estimated
            actual_minutes: What actually happened

        Returns:
            Quality evaluation with feedback for improvement
        """
        if estimated_minutes <= 0:
            return {"status": "error", "error": "Invalid estimate"}

        ratio = actual_minutes / estimated_minutes
        error_percent = abs(1.0 - ratio) * 100

        # Categorize estimation quality
        if 0.9 <= ratio <= 1.1:
            quality = "excellent"
            quality_score = 0.95
        elif 0.75 <= ratio <= 1.33:
            quality = "good"
            quality_score = 0.75
        elif 0.5 <= ratio <= 2.0:
            quality = "fair"
            quality_score = 0.5
        else:
            quality = "poor"
            quality_score = max(0.1, 1.0 - error_percent / 100)

        # Provide feedback
        feedback = []
        if ratio > 1.33:
            feedback.append(f"Underestimated by {error_percent:.0f}% - consider adding buffer")
        elif ratio < 0.75:
            feedback.append(f"Overestimated by {error_percent:.0f}% - look for shortcuts")

        return {
            "status": "success",
            "quality": quality,
            "quality_score": quality_score,
            "estimation_ratio": ratio,
            "error_percent": error_percent,
            "feedback": feedback,
        }

    async def learn_from_execution(
        self,
        task_type: str,
        estimated_minutes: float,
        actual_minutes: float,
        complexity: Optional[float] = None,
        success: bool = True,
    ) -> Dict[str, Any]:
        """Learn from a completed task execution.

        Updates internal models based on execution data.

        Args:
            task_type: Type of task
            estimated_minutes: What was estimated
            actual_minutes: What actually took
            complexity: Complexity of the task
            success: Whether task succeeded

        Returns:
            Learning summary with model updates
        """
        try:
            # Evaluate the estimation
            evaluation = await self.evaluate_estimation_quality(
                task_type, estimated_minutes, actual_minutes
            )

            # Update cache with new data point
            if task_type not in self._estimation_cache:
                self._estimation_cache[task_type] = {
                    "samples": [],
                    "avg_estimate": 0.0,
                    "avg_actual": 0.0,
                }

            cache_entry = self._estimation_cache[task_type]
            cache_entry["samples"].append(
                {
                    "estimated": estimated_minutes,
                    "actual": actual_minutes,
                    "complexity": complexity,
                    "success": success,
                    "timestamp": datetime.now().isoformat(),
                }
            )

            # Limit cache size (keep last 100 samples)
            if len(cache_entry["samples"]) > 100:
                cache_entry["samples"] = cache_entry["samples"][-100:]

            # Recalculate averages
            successful_samples = [s for s in cache_entry["samples"] if s["success"]]
            if successful_samples:
                cache_entry["avg_estimate"] = sum(s["estimated"] for s in successful_samples) / len(
                    successful_samples
                )
                cache_entry["avg_actual"] = sum(s["actual"] for s in successful_samples) / len(
                    successful_samples
                )

            return {
                "status": "success",
                "task_type": task_type,
                "quality": evaluation.get("quality", "unknown"),
                "quality_score": evaluation.get("quality_score", 0.0),
                "samples_collected": len(cache_entry["samples"]),
                "new_baseline": cache_entry["avg_actual"],
            }

        except Exception as e:
            logger.error(f"Failed to learn from execution: {e}")
            return {"status": "error", "error": str(e)}

    def get_estimation_statistics(self, task_type: str) -> Dict[str, Any]:
        """Get statistics for a task type's estimation accuracy.

        Args:
            task_type: Type of task to analyze

        Returns:
            Statistics about estimation accuracy
        """
        if task_type not in self._estimation_cache:
            return {"task_type": task_type, "samples": 0, "status": "no_data"}

        cache_entry = self._estimation_cache[task_type]
        samples = cache_entry["samples"]

        if not samples:
            return {"task_type": task_type, "samples": 0, "status": "no_data"}

        # Calculate statistics
        ratios = [s["actual"] / s["estimated"] for s in samples if s["estimated"] > 0]
        errors = [abs(1.0 - r) * 100 for r in ratios]

        return {
            "task_type": task_type,
            "samples": len(samples),
            "avg_estimate": cache_entry["avg_estimate"],
            "avg_actual": cache_entry["avg_actual"],
            "avg_error_percent": sum(errors) / len(errors) if errors else 0,
            "estimation_ratio": (
                cache_entry["avg_actual"] / cache_entry["avg_estimate"]
                if cache_entry["avg_estimate"] > 0
                else 1.0
            ),
            "success_rate": sum(1 for s in samples if s["success"]) / len(samples),
            "status": "accurate" if sum(errors) / len(errors) < 20 else "needs_improvement",
        }

    # Private methods

    def _get_default_estimate(self, task_type: Optional[str], complexity: Optional[float]) -> float:
        """Get default estimate based on task type and complexity.

        Args:
            task_type: Type of task
            complexity: 0.0-1.0 complexity level

        Returns:
            Default estimate in minutes
        """
        base_estimates = {
            "code-review": 30,
            "testing": 45,
            "refactor": 60,
            "bugfix": 20,
            "documentation": 25,
            "design": 45,
            "general": 30,
        }

        base = base_estimates.get(task_type or "general", 30)

        if complexity:
            # Adjust by complexity
            complexity_factor = 0.5 + (complexity * 1.5)  # 0.5x - 2.0x
            base = base * complexity_factor

        return base

    async def _get_historical_data(self, task_type: str) -> List[Dict[str, Any]]:
        """Get historical execution data for a task type.

        Args:
            task_type: Type of task

        Returns:
            List of historical executions
        """
        # For now, use in-memory cache
        if task_type in self._estimation_cache:
            return self._estimation_cache[task_type].get("samples", [])
        return []

    def _analyze_patterns(self, historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze patterns in historical data.

        Args:
            historical_data: List of past executions

        Returns:
            Pattern analysis with recommendations
        """
        if not historical_data:
            return {"confidence": 0.0, "reasoning": "Insufficient data"}

        successful = [d for d in historical_data if d.get("success", True)]
        if not successful:
            successful = historical_data

        # Calculate statistics
        actual_times = [d["actual"] for d in successful]
        estimates = [d["estimated"] for d in successful]

        avg_actual = sum(actual_times) / len(actual_times) if actual_times else 0
        avg_estimate = sum(estimates) / len(estimates) if estimates else 0

        # Analyze trend
        if len(successful) >= 3:
            recent_actual = sum(actual_times[-3:]) / 3
            older_actual = (
                sum(actual_times[:-3]) / len(actual_times[:-3])
                if len(actual_times) > 3
                else actual_times[0]
            )
            if recent_actual < older_actual * 0.95:
                trend = "improving"
            elif recent_actual > older_actual * 1.05:
                trend = "degrading"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"

        # Calculate confidence
        if len(successful) >= 10:
            confidence = 0.85
        elif len(successful) >= 5:
            confidence = 0.70
        elif len(successful) >= 3:
            confidence = 0.50
        else:
            confidence = 0.30

        # Estimate range
        estimate_errors = [
            abs(s["actual"] - s["estimated"]) / s["estimated"]
            for s in successful
            if s["estimated"] > 0
        ]
        avg_error = sum(estimate_errors) / len(estimate_errors) if estimate_errors else 0.2
        low_estimate = avg_actual * (1 - avg_error)
        high_estimate = avg_actual * (1 + avg_error)

        return {
            "confidence": confidence,
            "trend": trend,
            "reasoning": f"Based on {len(successful)} executions - avg {avg_actual:.0f}min (±{avg_error*100:.0f}%)",
            "summary": [
                f"Average actual: {avg_actual:.0f} minutes",
                f"Range: {low_estimate:.0f} - {high_estimate:.0f} minutes",
                f"Trend: {trend}",
            ],
            "adjustments": [],
        }
