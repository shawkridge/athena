"""Sync and drift detection for documents and specifications.

Provides automated drift detection, staleness checking, and regeneration workflows
to keep documentation in sync with specifications.
"""

from .drift_detector import DriftDetector, DriftResult, DriftStatus
from .sync_manager import SyncManager, SyncResult, SyncStrategy
from .staleness_checker import StalenessChecker, StalenessResult, StalenessLevel
from .diff_engine import (
    DocumentDiffer,
    DiffResult as DocumentDiffResult,
    SectionChange,
    SpecChange,
    ChangeType,
    SectionType,
)
from .conflict_resolver import (
    ConflictDetector,
    ConflictResolver,
    ConflictResult,
    ConflictStatus,
    MergeResult,
    MergeStrategy,
)

__all__ = [
    "DriftDetector",
    "DriftResult",
    "DriftStatus",
    "SyncManager",
    "SyncResult",
    "SyncStrategy",
    "StalenessChecker",
    "StalenessResult",
    "StalenessLevel",
    "DocumentDiffer",
    "DocumentDiffResult",
    "SectionChange",
    "SpecChange",
    "ChangeType",
    "SectionType",
    "ConflictDetector",
    "ConflictResolver",
    "ConflictResult",
    "ConflictStatus",
    "MergeResult",
    "MergeStrategy",
]
