"""predict_effort - Predict effort for a new task based on historical accuracy patterns.

Part of Phase 3c: Predictive Analytics
"""

from typing import Dict, Any, Optional


def predict_effort(
    project_id: int,
    task_type: str,
    base_estimate: int,
    db: Optional[Any] = None,
) -> Dict[str, Any]:
    """Predict effort for a new task based on historical patterns.

    Learns from past estimate accuracy to adjust predictions for new tasks.
    Applies systematic bias corrections learned from similar past tasks.

    Args:
        project_id (int): Project ID
        task_type (str): Task type (e.g., 'feature', 'bugfix', 'refactor')
        base_estimate (int): Initial estimate in minutes
        db (Optional[Database]): Database connection (auto-initialized if not provided)

    Returns:
        Dict with predicted effort, range, confidence, and explanation

    Examples:
        >>> predict_effort(project_id=1, task_type='feature', base_estimate=120)
        {
            'predicted_effort': 138,
            'base_estimate': 120,
            'bias_factor': 1.15,
            'confidence': 'high',
            'sample_count': 25,
            'explanation': 'Based on 25 similar features, you consistently underestimate by 15%...',
            'range': {
                'optimistic': 120,
                'expected': 138,
                'pessimistic': 160
            }
        }

    How it works:
        1. Look up historical stats for this task type
        2. Calculate bias factor from past accuracy
        3. Apply adjustment: predicted = estimate × bias_factor
        4. Generate confidence-based range (wider range = lower confidence)
        5. Return prediction with explanation

    Key concepts:
        - Bias Factor: Average of (actual / estimate) for similar past tasks
          - >1.0 means you typically underestimate
          - <1.0 means you typically overestimate
          - ≈1.0 means your estimates are well-calibrated
        - Confidence: Based on sample count and variance
          - Low: <5 samples (need more data)
          - Medium: 5-15 samples or high variance
          - High: >15 samples with low variance
        - Range: Wider for lower confidence
          - High confidence: ±15% range
          - Medium confidence: ±30% range
          - Low confidence: ±50% range

    Phase 3c foundation:
        Builds on data from EstimateAccuracyStore, which tracks:
        - Accuracy: min(estimate, actual) / max(estimate, actual)
        - Bias: average(actual / estimate)
        - Variance: std deviation of estimates
        - Sample count: number of similar completed tasks
    """

    # Import here to avoid circular dependencies
    try:
        if db is None:
            from ..core.database import Database
            db = Database()

        from ..predictive.estimator import PredictiveEstimator

        estimator = PredictiveEstimator(db)
        return estimator.predict_effort(project_id, task_type, base_estimate)

    except Exception as e:
        return {
            "error": f"Failed to predict effort: {str(e)}",
            "base_estimate": base_estimate,
            "task_type": task_type,
        }


# Tool metadata for filesystem discovery
__tool_name__ = "predict_effort"
__tool_category__ = "predictive_analytics"
__tool_summary__ = "Predict effort for a task based on historical accuracy patterns"
__tool_version__ = "1.0.0"
__tool_tags__ = ["estimation", "prediction", "effort", "accuracy", "machine-learning"]
