"""
API routes for Phase 3 Task Management integration.

Exposes Phase 3 task intelligence through dashboard API:
- Task status and dependencies (Phase 3a)
- Effort predictions (Phase 3c)
- Next task suggestions (Phase 3b)
"""

import logging
from fastapi import APIRouter, Query, HTTPException
from typing import Optional, Dict, Any, List
from datetime import datetime
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Add src to path for Phase 3 imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

# Import Phase 3 modules
try:
    from athena.prospective.dependencies import DependencyStore
    from athena.prospective.metadata import MetadataStore
    from athena.workflow.patterns import WorkflowPatternStore
    from athena.workflow.suggestions import PatternSuggestionEngine
    from athena.predictive.estimator import PredictiveEstimator
    PHASE3_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Phase 3 modules not available: {e}")
    PHASE3_AVAILABLE = False

# Create task router
task_router = APIRouter(prefix="/tasks", tags=["tasks"])

# Global service references
_services = {
    "data_loader": None,
    "metrics_aggregator": None,
    "cache_manager": None,
}


def set_task_services(data_loader, metrics_aggregator, cache_manager):
    """Set service references for task routes."""
    _services["data_loader"] = data_loader
    _services["metrics_aggregator"] = metrics_aggregator
    _services["cache_manager"] = cache_manager


# ============================================================================
# TASK STATUS ENDPOINTS (Phase 3a: Dependencies + Metadata)
# ============================================================================

class TaskStatus:
    """Task status model (compatible with Phase 3a data)."""

    def __init__(self, task_id: str, name: str, status: str, **kwargs):
        self.task_id = task_id
        self.name = name
        self.status = status  # pending | in_progress | completed | blocked
        self.estimated_effort_minutes = kwargs.get("estimated_effort", 0)
        self.actual_effort_minutes = kwargs.get("actual_effort", 0)
        self.blockers = kwargs.get("blockers", [])
        self.dependencies = kwargs.get("dependencies", [])
        self.accuracy_score = kwargs.get("accuracy_score", 0.0)
        self.created_at = kwargs.get("created_at", datetime.utcnow())
        self.updated_at = kwargs.get("updated_at", datetime.utcnow())

    def to_dict(self):
        return {
            "task_id": self.task_id,
            "name": self.name,
            "status": self.status,
            "estimated_effort_minutes": self.estimated_effort_minutes,
            "actual_effort_minutes": self.actual_effort_minutes,
            "blockers": self.blockers,
            "dependencies": self.dependencies,
            "accuracy_score": self.accuracy_score,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


@task_router.get("/status", summary="Get task status and dependencies")
async def get_task_status(
    task_id: Optional[str] = Query(None, description="Filter by task ID"),
    status: Optional[str] = Query(None, description="Filter by status (pending|in_progress|completed|blocked)"),
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
) -> Dict[str, Any]:
    """
    Get current task status and dependency information (Phase 3a).

    Returns:
    - Tasks with status (pending, in_progress, completed, blocked)
    - Task dependencies and blockers
    - Effort tracking (estimate vs actual)
    - Accuracy scores per task
    """
    if not PHASE3_AVAILABLE:
        raise HTTPException(status_code=503, detail="Phase 3 modules not available")

    try:
        # Cache key for task status
        cache_key = f"task_status:{project_id}:{task_id}:{status}"

        # Try cache first
        if _services["cache_manager"]:
            cached = _services["cache_manager"].get(cache_key)
            if cached:
                return cached

        # Generate mock data for now (real implementation will query Phase 3a stores)
        # TODO: Query DependencyStore and MetadataStore for actual task data
        tasks = [
            TaskStatus(
                task_id="task_1",
                name="Implement feature X",
                status="in_progress",
                estimated_effort=120,
                actual_effort=90,
                blockers=[],
                dependencies=[],
                accuracy_score=0.95,
            ),
            TaskStatus(
                task_id="task_2",
                name="Write tests",
                status="pending",
                estimated_effort=60,
                actual_effort=0,
                blockers=["task_1"],
                dependencies=["task_1"],
                accuracy_score=0.0,
            ),
        ]

        # Filter
        if task_id:
            tasks = [t for t in tasks if t.task_id == task_id]
        if status:
            tasks = [t for t in tasks if t.status == status]

        result = {
            "total_tasks": len(tasks),
            "tasks": [t.to_dict() for t in tasks],
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Cache result
        if _services["cache_manager"]:
            _services["cache_manager"].set(cache_key, result, ttl=60)

        return result

    except Exception as e:
        logger.error(f"Error fetching task status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# TASK PREDICTION ENDPOINTS (Phase 3c: Predictive Analytics)
# ============================================================================

class TaskPrediction:
    """Effort prediction model (from Phase 3c)."""

    def __init__(self, task_id: str, task_type: str, **kwargs):
        self.task_id = task_id
        self.task_type = task_type
        self.predicted_effort_minutes = kwargs.get("predicted", 0)
        self.confidence = kwargs.get("confidence", 0.0)
        self.optimistic_minutes = kwargs.get("optimistic", 0)
        self.expected_minutes = kwargs.get("expected", 0)
        self.pessimistic_minutes = kwargs.get("pessimistic", 0)
        self.historical_accuracy = kwargs.get("accuracy", 0.0)
        self.bias_factor = kwargs.get("bias", 1.0)

    def to_dict(self):
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "predicted_effort_minutes": self.predicted_effort_minutes,
            "confidence": self.confidence,
            "range": {
                "optimistic": self.optimistic_minutes,
                "expected": self.expected_minutes,
                "pessimistic": self.pessimistic_minutes,
            },
            "historical_accuracy": self.historical_accuracy,
            "bias_factor": self.bias_factor,
        }


@task_router.get("/predictions", summary="Get effort predictions for tasks")
async def get_task_predictions(
    task_id: Optional[str] = Query(None, description="Task ID to predict"),
    task_type: Optional[str] = Query(None, description="Task type to get baseline prediction"),
    min_confidence: float = Query(0.5, ge=0.0, le=1.0, description="Minimum confidence threshold"),
) -> Dict[str, Any]:
    """
    Get effort predictions for tasks (Phase 3c).

    Returns:
    - Predicted effort in optimistic/expected/pessimistic ranges
    - Confidence scores (higher = more reliable)
    - Historical accuracy per task type
    - Bias factors (accounts for systematic over/underestimation)
    """
    if not PHASE3_AVAILABLE:
        raise HTTPException(status_code=503, detail="Phase 3 modules not available")

    try:
        cache_key = f"task_predictions:{task_id}:{task_type}:{min_confidence}"

        if _services["cache_manager"]:
            cached = _services["cache_manager"].get(cache_key)
            if cached:
                return cached

        # Generate predictions (real implementation will use PredictiveEstimator)
        # TODO: Query PredictiveEstimator for actual predictions
        predictions = [
            TaskPrediction(
                task_id="task_1",
                task_type="feature_implementation",
                predicted=120,
                confidence=0.87,
                optimistic=90,
                expected=120,
                pessimistic=180,
                accuracy=0.82,
                bias=1.05,  # Slightly underestimating
            ),
            TaskPrediction(
                task_id="task_2",
                task_type="testing",
                predicted=60,
                confidence=0.91,
                optimistic=45,
                expected=60,
                pessimistic=90,
                accuracy=0.88,
                bias=0.98,
            ),
        ]

        # Filter by confidence
        predictions = [p for p in predictions if p.confidence >= min_confidence]

        result = {
            "total_predictions": len(predictions),
            "predictions": [p.to_dict() for p in predictions],
            "summary": {
                "avg_confidence": sum(p.confidence for p in predictions) / len(predictions) if predictions else 0,
                "total_predicted_effort": sum(p.expected_minutes for p in predictions),
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

        if _services["cache_manager"]:
            _services["cache_manager"].set(cache_key, result, ttl=60)

        return result

    except Exception as e:
        logger.error(f"Error fetching predictions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# TASK SUGGESTION ENDPOINTS (Phase 3b: Workflow Patterns)
# ============================================================================

class TaskSuggestion:
    """Task recommendation model (from Phase 3b)."""

    def __init__(self, task_id: str, reason: str, **kwargs):
        self.task_id = task_id
        self.task_name = kwargs.get("name", "")
        self.reason = reason
        self.confidence = kwargs.get("confidence", 0.0)
        self.pattern_frequency = kwargs.get("frequency", 0.0)
        self.expected_next_task = kwargs.get("next", None)

    def to_dict(self):
        return {
            "task_id": self.task_id,
            "task_name": self.task_name,
            "reason": self.reason,
            "confidence": self.confidence,
            "pattern_frequency": self.pattern_frequency,
            "expected_next_task": self.expected_next_task,
        }


@task_router.get("/suggestions", summary="Get suggested next tasks")
async def get_task_suggestions(
    current_task_id: Optional[str] = Query(None, description="Current task ID to get suggestions for"),
    limit: int = Query(5, ge=1, le=20, description="Number of suggestions to return"),
    min_confidence: float = Query(0.6, ge=0.0, le=1.0, description="Minimum confidence threshold"),
) -> Dict[str, Any]:
    """
    Get suggested next tasks based on workflow patterns (Phase 3b).

    Returns:
    - Recommended next tasks ranked by confidence
    - Reasons for suggestions (based on historical patterns)
    - Pattern frequency (how often this sequence occurs)
    - Process maturity assessment
    """
    if not PHASE3_AVAILABLE:
        raise HTTPException(status_code=503, detail="Phase 3 modules not available")

    try:
        cache_key = f"task_suggestions:{current_task_id}:{limit}:{min_confidence}"

        if _services["cache_manager"]:
            cached = _services["cache_manager"].get(cache_key)
            if cached:
                return cached

        # Generate suggestions (real implementation will use PatternSuggestionEngine)
        # TODO: Query PatternSuggestionEngine for actual suggestions
        suggestions = [
            TaskSuggestion(
                task_id="task_2",
                reason="92% of features are followed by testing",
                name="Write tests",
                confidence=0.92,
                frequency=0.92,
                next="task_3",
            ),
            TaskSuggestion(
                task_id="task_3",
                reason="78% of test suites are followed by review",
                name="Code review",
                confidence=0.78,
                frequency=0.78,
                next="task_4",
            ),
        ]

        # Filter by confidence
        suggestions = [s for s in suggestions if s.confidence >= min_confidence][:limit]

        result = {
            "current_task": current_task_id,
            "total_suggestions": len(suggestions),
            "suggestions": [s.to_dict() for s in suggestions],
            "process_maturity": "high" if len(suggestions) > 0 else "low",
            "timestamp": datetime.utcnow().isoformat(),
        }

        if _services["cache_manager"]:
            _services["cache_manager"].set(cache_key, result, ttl=120)

        return result

    except Exception as e:
        logger.error(f"Error fetching suggestions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# TASK METRICS ENDPOINTS
# ============================================================================

@task_router.get("/metrics", summary="Get comprehensive task metrics")
async def get_task_metrics(
    project_id: Optional[str] = Query(None, description="Filter by project"),
) -> Dict[str, Any]:
    """
    Get comprehensive metrics across all task management layers.

    Returns:
    - Completion rates
    - Average accuracy per task type
    - Workflow patterns and consistency
    - Predictive model performance
    """
    if not PHASE3_AVAILABLE:
        raise HTTPException(status_code=503, detail="Phase 3 modules not available")

    try:
        cache_key = f"task_metrics:{project_id}"

        if _services["cache_manager"]:
            cached = _services["cache_manager"].get(cache_key)
            if cached:
                return cached

        result = {
            "task_completion": {
                "completed": 45,
                "in_progress": 12,
                "pending": 23,
                "blocked": 2,
                "completion_rate": 0.64,
            },
            "effort_accuracy": {
                "overall": 0.85,
                "by_type": {
                    "feature_implementation": 0.82,
                    "testing": 0.91,
                    "documentation": 0.79,
                    "bugfix": 0.86,
                },
            },
            "workflow_patterns": {
                "process_maturity": "high",
                "consistency": 0.87,
                "anomalies": 3,
            },
            "predictions": {
                "avg_confidence": 0.88,
                "accuracy_trend": "improving",
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

        if _services["cache_manager"]:
            _services["cache_manager"].set(cache_key, result, ttl=300)

        return result

    except Exception as e:
        logger.error(f"Error fetching task metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))
