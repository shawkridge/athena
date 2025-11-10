"""Phase 7: Advanced Execution Intelligence.

This module provides real-time monitoring, assumption validation, adaptive
replanning, and learning from execution outcomes.

Components:
- ExecutionMonitor: Track actual vs. planned execution
- AssumptionValidator: Verify plan assumptions during execution
- AdaptiveReplanningEngine: Generate intelligent replanning options
- ExecutionLearner: Extract patterns and recommendations
"""

from .models import (
    TaskOutcome,
    DeviationSeverity,
    AssumptionValidationType,
    ReplanningStrategy,
    TaskExecutionRecord,
    PlanDeviation,
    AssumptionValidationResult,
    AssumptionViolation,
    ReplanningEvaluation,
    ReplanningOption,
    ExecutionPattern,
)
from .monitor import ExecutionMonitor
from .validator import AssumptionValidator, Assumption
from .replanning import AdaptiveReplanningEngine
from .learning import ExecutionLearner

__all__ = [
    # Models
    "TaskOutcome",
    "DeviationSeverity",
    "AssumptionValidationType",
    "ReplanningStrategy",
    "TaskExecutionRecord",
    "PlanDeviation",
    "AssumptionValidationResult",
    "AssumptionViolation",
    "ReplanningEvaluation",
    "ReplanningOption",
    "ExecutionPattern",
    # Components
    "ExecutionMonitor",
    "AssumptionValidator",
    "Assumption",
    "AdaptiveReplanningEngine",
    "ExecutionLearner",
]
