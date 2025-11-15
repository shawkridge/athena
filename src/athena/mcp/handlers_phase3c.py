"""Phase 3c handlers: Predictive Analytics & Estimation.

Exposes Phase 3c predictive tools through MCP server.
Allows agents to learn from estimation accuracy and predict effort for new tasks.
"""

import logging
from typing import Any, Dict, List
from mcp.types import TextContent

from .structured_result import StructuredResult, ResultStatus

logger = logging.getLogger(__name__)


class Phase3cHandlersMixin:
    """Phase 3c handler methods for predictive analytics and estimation.

    Methods exposed to Claude Code through MCP:
    - _handle_predict_effort: Predict effort for new task
    - _handle_get_accuracy_stats: Get accuracy statistics for task type
    - _handle_get_estimation_confidence: Get confidence level for estimates
    - _handle_get_prediction_range: Get low/med/high estimate ranges
    - _handle_get_bias_recommendations: Get adjustment recommendations
    - _handle_get_estimation_trends: Get estimation trends over time
    - _handle_analyze_high_variance_tasks: Find hardest-to-estimate tasks
    """

    async def _handle_predict_effort(self, args: dict) -> list[TextContent]:
        """Predict effort for a new task based on historical accuracy patterns.

        Args:
            task_type (str): Task type (e.g., 'feature', 'bugfix')
            base_estimate (int): Initial estimate in minutes

        Returns:
            Prediction with adjusted estimate, range, and confidence
        """
        try:
            project = self.project_manager.get_or_create_project()
            task_type = args.get("task_type")
            base_estimate = args.get("base_estimate")

            if not task_type or base_estimate is None:
                return StructuredResult(
                    status=ResultStatus.ERROR,
                    data={"error": "task_type and base_estimate required"},
                ).to_mcp()

            from ..predictive.estimator import PredictiveEstimator

            estimator = PredictiveEstimator(self.db)
            prediction = estimator.predict_effort(
                project.id, task_type, int(base_estimate)
            )

            if not prediction:
                return StructuredResult(
                    status=ResultStatus.ERROR,
                    data={"error": "Failed to generate prediction"},
                ).to_mcp()

            return StructuredResult(
                status=ResultStatus.SUCCESS,
                data=prediction,
            ).to_mcp()

        except Exception as e:
            logger.error(f"Error predicting effort: {e}")
            return StructuredResult(
                status=ResultStatus.ERROR,
                data={"error": str(e)},
            ).to_mcp()

    async def _handle_get_accuracy_stats(self, args: dict) -> list[TextContent]:
        """Get accuracy statistics for a task type.

        Args:
            task_type (str): Task type (e.g., 'feature', 'bugfix')

        Returns:
            Accuracy stats including bias factor, variance, and recommendation
        """
        try:
            project = self.project_manager.get_or_create_project()
            task_type = args.get("task_type")

            if not task_type:
                return StructuredResult(
                    status=ResultStatus.ERROR,
                    data={"error": "task_type required"},
                ).to_mcp()

            from ..predictive.accuracy import EstimateAccuracyStore

            store = EstimateAccuracyStore(self.db)
            stats = store.get_type_accuracy_stats(project.id, task_type)

            if not stats:
                return StructuredResult(
                    status=ResultStatus.WARNING,
                    data={
                        "message": f"No accuracy data yet for task type: {task_type}"
                    },
                ).to_mcp()

            return StructuredResult(
                status=ResultStatus.SUCCESS,
                data=stats,
            ).to_mcp()

        except Exception as e:
            logger.error(f"Error getting accuracy stats: {e}")
            return StructuredResult(
                status=ResultStatus.ERROR,
                data={"error": str(e)},
            ).to_mcp()

    async def _handle_get_estimation_confidence(self, args: dict) -> list[TextContent]:
        """Get confidence level for estimates of a task type.

        Args:
            task_type (str): Task type (e.g., 'feature', 'bugfix')

        Returns:
            Confidence level: 'low', 'medium', 'high' with explanation
        """
        try:
            project = self.project_manager.get_or_create_project()
            task_type = args.get("task_type")

            if not task_type:
                return StructuredResult(
                    status=ResultStatus.ERROR,
                    data={"error": "task_type required"},
                ).to_mcp()

            from ..predictive.estimator import PredictiveEstimator

            estimator = PredictiveEstimator(self.db)
            confidence = estimator.get_estimation_confidence(project.id, task_type)

            stats = estimator.accuracy_store.get_type_accuracy_stats(
                project.id, task_type
            )
            sample_count = stats.get("sample_count", 0) if stats else 0

            return StructuredResult(
                status=ResultStatus.SUCCESS,
                data={
                    "task_type": task_type,
                    "confidence": confidence,
                    "sample_count": sample_count,
                    "explanation": self._explain_confidence(confidence, sample_count),
                },
            ).to_mcp()

        except Exception as e:
            logger.error(f"Error getting confidence: {e}")
            return StructuredResult(
                status=ResultStatus.ERROR,
                data={"error": str(e)},
            ).to_mcp()

    async def _handle_get_prediction_range(self, args: dict) -> list[TextContent]:
        """Get low/medium/high estimate ranges for a task.

        Args:
            task_type (str): Task type
            base_estimate (int): Base estimate in minutes

        Returns:
            Range with optimistic, expected, and pessimistic estimates
        """
        try:
            project = self.project_manager.get_or_create_project()
            task_type = args.get("task_type")
            base_estimate = args.get("base_estimate")

            if not task_type or base_estimate is None:
                return StructuredResult(
                    status=ResultStatus.ERROR,
                    data={"error": "task_type and base_estimate required"},
                ).to_mcp()

            from ..predictive.estimator import PredictiveEstimator

            estimator = PredictiveEstimator(self.db)
            range_data = estimator.get_estimate_range(
                project.id, task_type, int(base_estimate)
            )

            if not range_data:
                return StructuredResult(
                    status=ResultStatus.ERROR,
                    data={"error": "Failed to generate estimate range"},
                ).to_mcp()

            return StructuredResult(
                status=ResultStatus.SUCCESS,
                data={
                    "task_type": task_type,
                    "base_estimate": base_estimate,
                    "range": range_data,
                    "summary": f"Estimate range: {range_data['optimistic']}-{range_data['pessimistic']} minutes "
                    f"(expected: {range_data['expected']})",
                },
            ).to_mcp()

        except Exception as e:
            logger.error(f"Error getting prediction range: {e}")
            return StructuredResult(
                status=ResultStatus.ERROR,
                data={"error": str(e)},
            ).to_mcp()

    async def _handle_get_bias_recommendations(self, args: dict) -> list[TextContent]:
        """Get adjustment recommendations based on estimation bias.

        Args:
            task_type (str): Task type (e.g., 'feature', 'bugfix')

        Returns:
            Recommendation on how to adjust estimates
        """
        try:
            project = self.project_manager.get_or_create_project()
            task_type = args.get("task_type")

            if not task_type:
                return StructuredResult(
                    status=ResultStatus.ERROR,
                    data={"error": "task_type required"},
                ).to_mcp()

            from ..predictive.accuracy import EstimateAccuracyStore

            store = EstimateAccuracyStore(self.db)
            stats = store.get_type_accuracy_stats(project.id, task_type)

            if not stats:
                return StructuredResult(
                    status=ResultStatus.WARNING,
                    data={
                        "message": f"No data yet for {task_type}. Complete 5+ tasks to get recommendations."
                    },
                ).to_mcp()

            bias_factor = stats.get("bias_factor", 1.0)
            confidence = stats.get("confidence", "low")
            sample_count = stats.get("sample_count", 0)

            return StructuredResult(
                status=ResultStatus.SUCCESS,
                data={
                    "task_type": task_type,
                    "bias_factor": round(bias_factor, 2),
                    "confidence": confidence,
                    "sample_count": sample_count,
                    "recommendation": stats.get("recommendation", "Gather more data"),
                },
            ).to_mcp()

        except Exception as e:
            logger.error(f"Error getting recommendations: {e}")
            return StructuredResult(
                status=ResultStatus.ERROR,
                data={"error": str(e)},
            ).to_mcp()

    async def _handle_get_estimation_trends(self, args: dict) -> list[TextContent]:
        """Get estimation accuracy trends over time.

        Args:
            task_type (str): Task type
            days_back (int, optional): Number of days to analyze (default: 90)

        Returns:
            Trend analysis showing improvement/degradation
        """
        try:
            project = self.project_manager.get_or_create_project()
            task_type = args.get("task_type")
            days_back = args.get("days_back", 90)

            if not task_type:
                return StructuredResult(
                    status=ResultStatus.ERROR,
                    data={"error": "task_type required"},
                ).to_mcp()

            from ..predictive.estimator import PredictiveEstimator

            estimator = PredictiveEstimator(self.db)
            trends = estimator.get_estimation_trends(project.id, task_type, days_back)

            if not trends:
                return StructuredResult(
                    status=ResultStatus.WARNING,
                    data={
                        "message": f"Not enough historical data to determine trends for {task_type}"
                    },
                ).to_mcp()

            return StructuredResult(
                status=ResultStatus.SUCCESS,
                data=trends,
            ).to_mcp()

        except Exception as e:
            logger.error(f"Error getting trends: {e}")
            return StructuredResult(
                status=ResultStatus.ERROR,
                data={"error": str(e)},
            ).to_mcp()

    async def _handle_analyze_high_variance_tasks(
        self, args: dict
    ) -> list[TextContent]:
        """Identify task types that are hardest to estimate (high variance).

        Args:
            None (uses current project)

        Returns:
            List of task types ranked by estimation difficulty
        """
        try:
            project = self.project_manager.get_or_create_project()

            from ..predictive.accuracy import EstimateAccuracyStore

            store = EstimateAccuracyStore(self.db)
            all_stats = store.get_all_type_stats(project.id)

            if not all_stats:
                return StructuredResult(
                    status=ResultStatus.WARNING,
                    data={
                        "message": "No estimation data yet. Complete several tasks first."
                    },
                ).to_mcp()

            # Sort by variance (highest first)
            high_variance = sorted(
                [s for s in all_stats if s.get("variance", 0) > 0.2],
                key=lambda x: x.get("variance", 0),
                reverse=True,
            )

            if not high_variance:
                return StructuredResult(
                    status=ResultStatus.SUCCESS,
                    data={
                        "message": "All task types have consistent estimates.",
                        "high_variance_tasks": [],
                    },
                ).to_mcp()

            return StructuredResult(
                status=ResultStatus.SUCCESS,
                data={
                    "high_variance_tasks": high_variance,
                    "summary": f"{len(high_variance)} task types have high variance (hardest to estimate)",
                    "recommendation": "Consider breaking these tasks into smaller, more predictable subtasks",
                },
            ).to_mcp()

        except Exception as e:
            logger.error(f"Error analyzing high variance tasks: {e}")
            return StructuredResult(
                status=ResultStatus.ERROR,
                data={"error": str(e)},
            ).to_mcp()

    @staticmethod
    def _explain_confidence(confidence: str, sample_count: int) -> str:
        """Explain what a confidence level means.

        Args:
            confidence: Confidence level
            sample_count: Number of samples

        Returns:
            Explanation string
        """
        if confidence == "low":
            return (
                f"Low confidence ({sample_count} samples). Need at least 5 similar tasks "
                "for reliable predictions."
            )
        elif confidence == "medium":
            return (
                f"Medium confidence ({sample_count} samples). "
                "Predictions reasonably reliable but watch for variations."
            )
        else:  # high
            return (
                f"High confidence ({sample_count} samples). "
                "Strong historical data supports these predictions."
            )
