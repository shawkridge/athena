"""Architecture layer for tracking design decisions, patterns, and constraints.

This layer provides context engineering capabilities for AI-assisted development by
maintaining a persistent record of architectural decisions, design patterns, and
constraints across projects.
"""

from .models import (
    ArchitecturalDecisionRecord,
    DesignPattern,
    ArchitecturalConstraint,
    TradeOffAnalysis,
    ArchitectureEvolution,
    SystemBoundary,
    DecisionStatus,
    PatternType,
    ConstraintType,
    TradeOffDimension,
)

__all__ = [
    "ArchitecturalDecisionRecord",
    "DesignPattern",
    "ArchitecturalConstraint",
    "TradeOffAnalysis",
    "ArchitectureEvolution",
    "SystemBoundary",
    "DecisionStatus",
    "PatternType",
    "ConstraintType",
    "TradeOffDimension",
]
