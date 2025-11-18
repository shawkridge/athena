"""Drift detection for documents and specifications.

Detects when documents are out of sync with their source specifications
by comparing content hashes.
"""

import logging
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum

from ..models import Document, Specification

logger = logging.getLogger(__name__)


class DriftStatus(str, Enum):
    """Status of document drift."""
    IN_SYNC = "in_sync"           # Document matches source specs
    DRIFTED = "drifted"           # Source specs have changed
    STALE = "stale"               # Not synced recently
    MISSING_HASH = "missing_hash" # No sync_hash recorded
    ORPHANED = "orphaned"         # Source specs no longer exist


@dataclass
class DriftResult:
    """Result of drift detection for a document.

    Indicates whether a document is in sync with its source specifications
    and provides details about any drift detected.
    """
    document: Document
    status: DriftStatus

    # Drift details
    current_hash: Optional[str] = None
    stored_hash: Optional[str] = None

    # Specs involved
    spec_ids: List[int] = field(default_factory=list)
    missing_spec_ids: List[int] = field(default_factory=list)

    # Timestamps
    last_synced_at: Optional[datetime] = None
    days_since_sync: Optional[int] = None

    # Additional info
    message: str = ""
    recommendation: str = ""

    @property
    def needs_regeneration(self) -> bool:
        """Check if document needs regeneration."""
        return self.status in [DriftStatus.DRIFTED, DriftStatus.STALE, DriftStatus.ORPHANED]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "document_id": self.document.id,
            "document_name": self.document.name,
            "status": self.status.value,
            "needs_regeneration": self.needs_regeneration,
            "current_hash": self.current_hash,
            "stored_hash": self.stored_hash,
            "spec_ids": self.spec_ids,
            "missing_spec_ids": self.missing_spec_ids,
            "last_synced_at": self.last_synced_at.isoformat() if self.last_synced_at else None,
            "days_since_sync": self.days_since_sync,
            "message": self.message,
            "recommendation": self.recommendation,
        }


class DriftDetector:
    """Detects drift between documents and their source specifications.

    Compares document sync_hash with current spec content hash to detect
    when documents are out of sync with their sources.

    Example:
        >>> detector = DriftDetector(spec_store, doc_store)
        >>> result = detector.check_document(doc_id=5)
        >>> if result.needs_regeneration:
        ...     print(f"Document {result.document.name} needs update")
        ...     print(f"Status: {result.status.value}")
    """

    def __init__(self, spec_store, doc_store):
        """Initialize drift detector.

        Args:
            spec_store: Specification store instance
            doc_store: Document store instance
        """
        self.spec_store = spec_store
        self.doc_store = doc_store

    def check_document(
        self,
        doc_id: int,
        staleness_threshold_days: int = 30
    ) -> DriftResult:
        """Check if a document has drifted from its source specs.

        Args:
            doc_id: Document ID to check
            staleness_threshold_days: Days after which document is considered stale

        Returns:
            Drift result with status and details

        Example:
            >>> result = detector.check_document(doc_id=5)
            >>> if result.status == DriftStatus.DRIFTED:
            ...     print("Document needs regeneration")
        """
        # Load document
        doc = self.doc_store.get(doc_id)
        if not doc:
            raise ValueError(f"Document {doc_id} not found")

        # Check if document has sync hash
        if not doc.sync_hash:
            return DriftResult(
                document=doc,
                status=DriftStatus.MISSING_HASH,
                message="Document has no sync hash - cannot detect drift",
                recommendation="Regenerate document to establish baseline hash",
            )

        # Get source spec IDs
        spec_ids = doc.based_on_spec_ids or []
        if not spec_ids:
            return DriftResult(
                document=doc,
                status=DriftStatus.MISSING_HASH,
                spec_ids=[],
                message="Document has no source specifications",
                recommendation="Update document metadata to track source specs",
            )

        # Load source specs
        specs = []
        missing_spec_ids = []
        for spec_id in spec_ids:
            spec = self.spec_store.get(spec_id)
            if spec:
                specs.append(spec)
            else:
                missing_spec_ids.append(spec_id)

        # Check for orphaned document (all specs missing)
        if missing_spec_ids and not specs:
            return DriftResult(
                document=doc,
                status=DriftStatus.ORPHANED,
                spec_ids=spec_ids,
                missing_spec_ids=missing_spec_ids,
                message=f"All source specifications no longer exist (IDs: {missing_spec_ids})",
                recommendation="Archive or delete this document",
            )

        # Compute current hash from specs
        current_hash = self._compute_specs_hash(specs)

        # Compare hashes
        if current_hash != doc.sync_hash:
            return DriftResult(
                document=doc,
                status=DriftStatus.DRIFTED,
                current_hash=current_hash,
                stored_hash=doc.sync_hash,
                spec_ids=spec_ids,
                missing_spec_ids=missing_spec_ids,
                last_synced_at=doc.last_synced_at,
                message="Source specifications have changed since last sync",
                recommendation="Regenerate document to incorporate spec changes",
            )

        # Check staleness
        if doc.last_synced_at:
            days_since_sync = (datetime.now() - doc.last_synced_at).days

            if days_since_sync > staleness_threshold_days:
                return DriftResult(
                    document=doc,
                    status=DriftStatus.STALE,
                    current_hash=current_hash,
                    stored_hash=doc.sync_hash,
                    spec_ids=spec_ids,
                    last_synced_at=doc.last_synced_at,
                    days_since_sync=days_since_sync,
                    message=f"Document not synced in {days_since_sync} days",
                    recommendation=f"Review and regenerate if needed (threshold: {staleness_threshold_days} days)",
                )

        # Document is in sync
        return DriftResult(
            document=doc,
            status=DriftStatus.IN_SYNC,
            current_hash=current_hash,
            stored_hash=doc.sync_hash,
            spec_ids=spec_ids,
            last_synced_at=doc.last_synced_at,
            days_since_sync=(datetime.now() - doc.last_synced_at).days if doc.last_synced_at else None,
            message="Document is in sync with source specifications",
            recommendation="No action needed",
        )

    def check_project(
        self,
        project_id: int,
        staleness_threshold_days: int = 30
    ) -> List[DriftResult]:
        """Check drift for all documents in a project.

        Args:
            project_id: Project ID
            staleness_threshold_days: Days threshold for staleness

        Returns:
            List of drift results for all documents

        Example:
            >>> results = detector.check_project(project_id=1)
            >>> drifted = [r for r in results if r.needs_regeneration]
            >>> print(f"{len(drifted)} documents need update")
        """
        # Get all documents in project
        docs = self.doc_store.list_by_project(project_id=project_id, limit=1000)

        # Check each document
        results = []
        for doc in docs:
            try:
                result = self.check_document(
                    doc_id=doc.id,
                    staleness_threshold_days=staleness_threshold_days
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to check document {doc.id}: {e}")
                results.append(DriftResult(
                    document=doc,
                    status=DriftStatus.MISSING_HASH,
                    message=f"Error checking drift: {e}",
                    recommendation="Check document manually",
                ))

        return results

    def get_drifted_documents(
        self,
        project_id: int,
        staleness_threshold_days: int = 30
    ) -> List[DriftResult]:
        """Get only documents that have drifted.

        Args:
            project_id: Project ID
            staleness_threshold_days: Days threshold for staleness

        Returns:
            List of drift results for documents that need regeneration

        Example:
            >>> drifted = detector.get_drifted_documents(project_id=1)
            >>> for result in drifted:
            ...     print(f"- {result.document.name}: {result.message}")
        """
        all_results = self.check_project(project_id, staleness_threshold_days)
        return [r for r in all_results if r.needs_regeneration]

    def _compute_specs_hash(self, specs: List[Specification]) -> str:
        """Compute combined hash from multiple specifications.

        Args:
            specs: List of specifications

        Returns:
            16-character hash string
        """
        if not specs:
            return ""

        # Sort by ID for consistent ordering
        sorted_specs = sorted(specs, key=lambda s: s.id or 0)

        # Combine content
        combined_content = "\n---\n".join([
            f"ID:{spec.id}|V:{spec.version}|{spec.content}"
            for spec in sorted_specs
        ])

        # Compute hash
        return hashlib.sha256(combined_content.encode()).hexdigest()[:16]

    def compute_document_hash(self, doc_id: int) -> Optional[str]:
        """Compute hash for a document's current source specs.

        Useful for updating sync_hash after regeneration.

        Args:
            doc_id: Document ID

        Returns:
            Hash string, or None if no source specs

        Example:
            >>> new_hash = detector.compute_document_hash(doc_id=5)
            >>> doc_store.update(doc, sync_hash=new_hash)
        """
        doc = self.doc_store.get(doc_id)
        if not doc or not doc.based_on_spec_ids:
            return None

        specs = []
        for spec_id in doc.based_on_spec_ids:
            spec = self.spec_store.get(spec_id)
            if spec:
                specs.append(spec)

        return self._compute_specs_hash(specs)
