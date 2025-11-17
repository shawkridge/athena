"""High-level service for effort prediction - Phase 1.

Predicts effort for new tasks based on historical accuracy.
Provides estimates with adjustment factors and confidence levels.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from ..core.database import Database
from ..predictive.estimator import PredictiveEstimator
from ..predictive.accuracy import EstimateAccuracyStore

logger = logging.getLogger(__name__)


class EffortPredictorService:
    """Predicts effort for new tasks based on historical accuracy."""

    def __init__(self, db: Database):
        """Initialize effort predictor service.

        Args:
            db: Database instance
        """
        self.db = db
        # Initialize estimator and accuracy store, handling any schema init errors
        try:
            self.estimator = PredictiveEstimator(db)
            self.accuracy_store = self.estimator.accuracy_store
        except (AttributeError, Exception) as e:
            logger.debug(f"Note: Database may not have schema initialized yet: {e}")
            # Stores will handle schema on first use
            self.estimator = None
            self.accuracy_store = None

    async def predict_for_task(
        self,
        project_id: int,
        task_description: str,
        task_type: str,
        base_estimate: Optional[int] = None
    ) -> Dict[str, Any]:
        """Predict effort for a new task based on historical patterns.

        Args:
            project_id: Project ID
            task_description: What the task does
            task_type: Task category (feature, bugfix, refactor, docs, etc)
            base_estimate: User's initial estimate in minutes (optional)

        Returns:
            {
                effort: int,                # Predicted effort in minutes
                confidence: str,            # "low", "medium", "high"
                bias_factor: float,         # Adjustment factor from history
                range: {
                    optimistic: int,        # Best case
                    expected: int,          # Most likely
                    pessimistic: int        # Worst case
                },
                explanation: str,           # Human-readable reasoning
                sample_count: int          # How many similar tasks used
            }

        Examples:
            >>> service = EffortPredictorService(db)
            >>> pred = await service.predict_for_task(
            ...     project_id=1,
            ...     task_description="Add user authentication",
            ...     task_type="feature",
            ...     base_estimate=120
            ... )
            >>> print(f"Effort: {pred['effort']}m, Confidence: {pred['confidence']}")
        """
        # If no estimate provided, use reasonable defaults by task type
        if not base_estimate:
            base_estimate = self._default_estimate_for_type(task_type)
            logger.info(
                f"No estimate provided, using default for '{task_type}': {base_estimate}m"
            )

        # Get prediction from estimator
        if not self.estimator:
            # Initialize on first use if needed
            try:
                self.estimator = PredictiveEstimator(self.db)
                self.accuracy_store = self.estimator.accuracy_store
            except Exception as e:
                logger.warning(f"Could not initialize estimator: {e}")
                # Return basic prediction without estimator
                return self._basic_prediction(base_estimate)

        prediction = self.estimator.predict_effort(
            project_id=project_id,
            task_type=task_type,
            base_estimate=base_estimate
        )

        # Ensure all required fields are present
        if not prediction:
            prediction = {
                "predicted_effort": base_estimate,
                "base_estimate": base_estimate,
                "bias_factor": 1.0,
                "confidence": "low",
                "explanation": f"Error getting prediction, using base estimate.",
                "range": {
                    "optimistic": int(base_estimate * 0.9),
                    "expected": base_estimate,
                    "pessimistic": int(base_estimate * 1.2),
                },
            }

        # Format response with consistent field names
        return {
            "effort": prediction.get("predicted_effort", base_estimate),
            "confidence": prediction.get("confidence", "low"),
            "bias_factor": round(prediction.get("bias_factor", 1.0), 2),
            "range": prediction.get("range", {
                "optimistic": int(base_estimate * 0.9),
                "expected": base_estimate,
                "pessimistic": int(base_estimate * 1.2),
            }),
            "explanation": prediction.get("explanation", "No explanation available"),
            "sample_count": prediction.get("sample_count", 0)
        }

    def _basic_prediction(self, base_estimate: int) -> Dict[str, Any]:
        """Return a basic prediction without database lookups.

        Args:
            base_estimate: Base estimate in minutes

        Returns:
            Basic prediction dictionary
        """
        return {
            "effort": base_estimate,
            "confidence": "low",
            "bias_factor": 1.0,
            "range": {
                "optimistic": int(base_estimate * 0.85),
                "expected": base_estimate,
                "pessimistic": int(base_estimate * 1.25),
            },
            "explanation": "Basic prediction (database not available). Adjust as needed.",
            "sample_count": 0
        }

    def _default_estimate_for_type(self, task_type: str) -> int:
        """Return reasonable default estimate for task type in minutes.

        Args:
            task_type: Type of task

        Returns:
            Default estimate in minutes
        """
        defaults = {
            "bugfix": 30,          # ~30 minutes for bug fixes
            "doc": 45,             # ~45 minutes for documentation
            "refactor": 120,       # ~2 hours for refactoring
            "feature": 180,        # ~3 hours for features
            "enhancement": 120,    # ~2 hours for enhancements
            "research": 120,       # ~2 hours for research
            "testing": 90,         # ~1.5 hours for testing
            "review": 45,          # ~45 minutes for code review
            "chore": 60,           # ~1 hour for chores
            "general": 120,        # ~2 hours default
        }
        task_type_lower = task_type.lower() if task_type else "general"
        return defaults.get(task_type_lower, defaults["general"])
