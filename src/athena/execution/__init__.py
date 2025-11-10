"""Phase 7 & 7.5: Advanced Execution Intelligence & Analytics.

This module provides real-time monitoring, assumption validation, adaptive
replanning, learning from execution outcomes, and execution analytics.

Phase 7 Components:
- ExecutionMonitor: Track actual vs. planned execution
- AssumptionValidator: Verify plan assumptions during execution
- AdaptiveReplanningEngine: Generate intelligent replanning options
- ExecutionLearner: Extract patterns and recommendations

Phase 7.5 Components:
- ExecutionAnalytics: Cost tracking, performance trending, forecasting
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
from .analytics import (
    ExecutionAnalytics,
    ExecutionCost,
    TeamVelocity,
    PerformanceTrend,
    ExecutionForecast,
    AnalyticsReport,
)

__all__ = [
    # Phase 7 Models
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
    # Phase 7 Components
    "ExecutionMonitor",
    "AssumptionValidator",
    "Assumption",
    "AdaptiveReplanningEngine",
    "ExecutionLearner",
    # Phase 7.5 Models
    "ExecutionCost",
    "TeamVelocity",
    "PerformanceTrend",
    "ExecutionForecast",
    "AnalyticsReport",
    # Phase 7.5 Components
    "ExecutionAnalytics",
]
