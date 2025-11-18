"""Staleness checker for documents.

Identifies documents that haven't been synced recently and may need review.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from enum import Enum

from ..models import Document

logger = logging.getLogger(__name__)


class StalenessLevel(str, Enum):
    """Level of document staleness."""
    FRESH = "fresh"           # Recently synced
    AGING = "aging"           # Getting old but acceptable
    STALE = "stale"           # Needs review
    VERY_STALE = "very_stale" # Urgent review needed
    NEVER_SYNCED = "never_synced"  # Never synced


@dataclass
class StalenessResult:
    """Result of staleness check for a document."""
    document: Document
    level: StalenessLevel

    # Time metrics
    last_synced_at: Optional[datetime] = None
    days_since_sync: Optional[int] = None
    created_at: Optional[datetime] = None
    days_since_creation: Optional[int] = None

    # Recommendations
    needs_review: bool = False
    priority: str = "low"  # low, medium, high, critical
    message: str = ""
    recommendation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "document_id": self.document.id,
            "document_name": self.document.name,
            "doc_type": self.document.doc_type.value,
            "level": self.level.value,
            "last_synced_at": self.last_synced_at.isoformat() if self.last_synced_at else None,
            "days_since_sync": self.days_since_sync,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "days_since_creation": self.days_since_creation,
            "needs_review": self.needs_review,
            "priority": self.priority,
            "message": self.message,
            "recommendation": self.recommendation,
        }


class StalenessChecker:
    """Checks document staleness based on last sync time.

    Identifies documents that haven't been updated in a while and may
    need review or regeneration.

    Example:
        >>> checker = StalenessChecker(doc_store)
        >>> results = checker.check_project(project_id=1)
        >>> stale = [r for r in results if r.needs_review]
        >>> print(f"{len(stale)} documents need review")
    """

    # Default thresholds (days)
    DEFAULT_THRESHOLDS = {
        "fresh": 7,        # < 7 days = fresh
        "aging": 30,       # 7-30 days = aging
        "stale": 90,       # 30-90 days = stale
        "very_stale": 180, # > 90 days = very stale
    }

    def __init__(
        self,
        doc_store,
        thresholds: Optional[Dict[str, int]] = None
    ):
        """Initialize staleness checker.

        Args:
            doc_store: Document store instance
            thresholds: Custom thresholds in days (optional)
        """
        self.doc_store = doc_store
        self.thresholds = thresholds or self.DEFAULT_THRESHOLDS

    def check_document(self, doc_id: int) -> StalenessResult:
        """Check staleness of a single document.

        Args:
            doc_id: Document ID

        Returns:
            Staleness result

        Example:
            >>> result = checker.check_document(doc_id=5)
            >>> if result.needs_review:
            ...     print(f"Priority: {result.priority}")
        """
        # Load document
        doc = self.doc_store.get(doc_id)
        if not doc:
            raise ValueError(f"Document {doc_id} not found")

        now = datetime.now()

        # Calculate time since last sync
        if doc.last_synced_at:
            days_since_sync = (now - doc.last_synced_at).days
        else:
            days_since_sync = None

        # Calculate time since creation
        if doc.created_at:
            days_since_creation = (now - doc.created_at).days
        else:
            days_since_creation = None

        # Determine staleness level
        if days_since_sync is None:
            level = StalenessLevel.NEVER_SYNCED
            needs_review = True
            priority = "high"
            message = "Document has never been synced"
            recommendation = "Sync document with source specifications"

        elif days_since_sync <= self.thresholds["fresh"]:
            level = StalenessLevel.FRESH
            needs_review = False
            priority = "low"
            message = f"Document synced {days_since_sync} days ago (fresh)"
            recommendation = "No action needed"

        elif days_since_sync <= self.thresholds["aging"]:
            level = StalenessLevel.AGING
            needs_review = False
            priority = "low"
            message = f"Document synced {days_since_sync} days ago (aging)"
            recommendation = "Consider reviewing if specs have changed"

        elif days_since_sync <= self.thresholds["stale"]:
            level = StalenessLevel.STALE
            needs_review = True
            priority = "medium"
            message = f"Document synced {days_since_sync} days ago (stale)"
            recommendation = "Review and sync with latest specifications"

        else:  # > very_stale threshold
            level = StalenessLevel.VERY_STALE
            needs_review = True
            priority = "high"
            message = f"Document synced {days_since_sync} days ago (very stale)"
            recommendation = "Urgent: Review and update document immediately"

        return StalenessResult(
            document=doc,
            level=level,
            last_synced_at=doc.last_synced_at,
            days_since_sync=days_since_sync,
            created_at=doc.created_at,
            days_since_creation=days_since_creation,
            needs_review=needs_review,
            priority=priority,
            message=message,
            recommendation=recommendation,
        )

    def check_project(
        self,
        project_id: int,
        include_fresh: bool = False
    ) -> List[StalenessResult]:
        """Check staleness for all documents in a project.

        Args:
            project_id: Project ID
            include_fresh: Include fresh documents in results

        Returns:
            List of staleness results

        Example:
            >>> results = checker.check_project(project_id=1)
            >>> for result in results:
            ...     if result.priority == "high":
            ...         print(f"URGENT: {result.document.name}")
        """
        # Get all documents
        docs = self.doc_store.list_by_project(project_id=project_id, limit=1000)

        # Check each document
        results = []
        for doc in docs:
            try:
                result = self.check_document(doc_id=doc.id)

                # Filter fresh docs if requested
                if include_fresh or result.level != StalenessLevel.FRESH:
                    results.append(result)

            except Exception as e:
                logger.error(f"Failed to check document {doc.id}: {e}")

        return results

    def get_stale_documents(
        self,
        project_id: int,
        min_level: StalenessLevel = StalenessLevel.STALE
    ) -> List[StalenessResult]:
        """Get only stale documents that need review.

        Args:
            project_id: Project ID
            min_level: Minimum staleness level to include

        Returns:
            List of staleness results for stale documents

        Example:
            >>> stale = checker.get_stale_documents(project_id=1)
            >>> print(f"{len(stale)} stale documents")
        """
        all_results = self.check_project(project_id, include_fresh=False)

        # Filter by level
        level_order = [
            StalenessLevel.FRESH,
            StalenessLevel.AGING,
            StalenessLevel.STALE,
            StalenessLevel.VERY_STALE,
            StalenessLevel.NEVER_SYNCED,
        ]

        min_index = level_order.index(min_level)

        return [
            r for r in all_results
            if level_order.index(r.level) >= min_index
        ]

    def get_summary(self, results: List[StalenessResult]) -> Dict[str, Any]:
        """Get summary statistics for staleness results.

        Args:
            results: List of staleness results

        Returns:
            Summary dictionary

        Example:
            >>> summary = checker.get_summary(results)
            >>> print(f"{summary['stale']} stale, {summary['very_stale']} very stale")
        """
        by_level = {
            StalenessLevel.FRESH: 0,
            StalenessLevel.AGING: 0,
            StalenessLevel.STALE: 0,
            StalenessLevel.VERY_STALE: 0,
            StalenessLevel.NEVER_SYNCED: 0,
        }

        by_priority = {
            "low": 0,
            "medium": 0,
            "high": 0,
            "critical": 0,
        }

        needs_review = 0

        for result in results:
            by_level[result.level] += 1
            by_priority[result.priority] += 1
            if result.needs_review:
                needs_review += 1

        return {
            "total": len(results),
            "fresh": by_level[StalenessLevel.FRESH],
            "aging": by_level[StalenessLevel.AGING],
            "stale": by_level[StalenessLevel.STALE],
            "very_stale": by_level[StalenessLevel.VERY_STALE],
            "never_synced": by_level[StalenessLevel.NEVER_SYNCED],
            "needs_review": needs_review,
            "priority_low": by_priority["low"],
            "priority_medium": by_priority["medium"],
            "priority_high": by_priority["high"],
            "priority_critical": by_priority["critical"],
        }
