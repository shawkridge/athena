"""Safety policy and audit trail management for autonomous agents."""

from .evaluator import SafetyEvaluator
from .execution import (
    ExecutionCallback,
    ExecutionContext,
    ExecutionEvent,
    ExecutionEventType,
    ExecutionMonitor,
    ExecutionSummary,
)
from .manager import SafetyManager
from .models import (
    ApprovalRequest,
    ApprovalStatus,
    AuditEntry,
    ChangeRecommendation,
    ChangeRiskLevel,
    ChangeType,
    CodeSnapshot,
    SafetyPolicy,
)
from .store import SafetyStore

__all__ = [
    # Models
    "SafetyPolicy",
    "ApprovalRequest",
    "ApprovalStatus",
    "AuditEntry",
    "ChangeRecommendation",
    "ChangeType",
    "ChangeRiskLevel",
    "CodeSnapshot",
    # Execution
    "ExecutionEvent",
    "ExecutionEventType",
    "ExecutionContext",
    "ExecutionSummary",
    "ExecutionCallback",
    "ExecutionMonitor",
    # Storage & Evaluation
    "SafetyStore",
    "SafetyEvaluator",
    # Public API
    "SafetyManager",
]
