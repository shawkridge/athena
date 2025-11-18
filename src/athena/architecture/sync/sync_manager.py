"""Sync manager for automated document regeneration.

Handles workflows for regenerating documents when their source specifications change.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum

from ..models import Document, DocumentType
from .drift_detector import DriftDetector, DriftResult, DriftStatus

logger = logging.getLogger(__name__)


class SyncStrategy(str, Enum):
    """Strategy for syncing documents."""
    REGENERATE = "regenerate"     # Full regeneration using AI/templates
    SKIP = "skip"                 # Skip syncing
    MANUAL = "manual"             # Mark for manual review


@dataclass
class SyncResult:
    """Result of syncing a document.

    Tracks the outcome of attempting to regenerate a document.
    """
    document: Document
    success: bool
    strategy: SyncStrategy

    # Before/after hashes
    old_hash: Optional[str] = None
    new_hash: Optional[str] = None

    # Generation details
    regenerated: bool = False
    generation_time_seconds: Optional[float] = None
    error: Optional[str] = None

    # Metadata
    synced_at: datetime = field(default_factory=datetime.now)
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "document_id": self.document.id,
            "document_name": self.document.name,
            "success": self.success,
            "strategy": self.strategy.value,
            "regenerated": self.regenerated,
            "old_hash": self.old_hash,
            "new_hash": self.new_hash,
            "generation_time_seconds": self.generation_time_seconds,
            "error": self.error,
            "synced_at": self.synced_at.isoformat(),
            "message": self.message,
        }


class SyncManager:
    """Manages document synchronization with source specifications.

    Orchestrates detection of drift and automated regeneration of documents.

    Example:
        >>> manager = SyncManager(spec_store, doc_store, ai_generator)
        >>> results = manager.sync_project(project_id=1, auto_regenerate=True)
        >>> print(f"Synced {len(results)} documents")
    """

    def __init__(
        self,
        spec_store,
        doc_store,
        ai_generator=None,
        template_manager=None
    ):
        """Initialize sync manager.

        Args:
            spec_store: Specification store instance
            doc_store: Document store instance
            ai_generator: AI generator (optional, for AI regeneration)
            template_manager: Template manager (optional, for template regeneration)
        """
        self.spec_store = spec_store
        self.doc_store = doc_store
        self.ai_generator = ai_generator
        self.template_manager = template_manager

        self.drift_detector = DriftDetector(spec_store, doc_store)

    def sync_document(
        self,
        doc_id: int,
        strategy: SyncStrategy = SyncStrategy.REGENERATE,
        dry_run: bool = False
    ) -> SyncResult:
        """Sync a single document with its source specifications.

        Args:
            doc_id: Document ID
            strategy: Sync strategy to use
            dry_run: If True, only check drift without regenerating

        Returns:
            Sync result

        Example:
            >>> result = manager.sync_document(doc_id=5)
            >>> if result.success:
            ...     print(f"Synced {result.document.name}")
        """
        import time

        # Load document
        doc = self.doc_store.get(doc_id)
        if not doc:
            return SyncResult(
                document=None,
                success=False,
                strategy=strategy,
                error=f"Document {doc_id} not found",
                message="Document not found",
            )

        # Check drift
        drift_result = self.drift_detector.check_document(doc_id)

        # If no drift, no sync needed
        if drift_result.status == DriftStatus.IN_SYNC:
            return SyncResult(
                document=doc,
                success=True,
                strategy=SyncStrategy.SKIP,
                old_hash=drift_result.stored_hash,
                new_hash=drift_result.current_hash,
                message="Document already in sync",
            )

        # If dry run, return without regenerating
        if dry_run:
            return SyncResult(
                document=doc,
                success=True,
                strategy=SyncStrategy.MANUAL,
                old_hash=drift_result.stored_hash,
                new_hash=drift_result.current_hash,
                message=f"Drift detected: {drift_result.message} (dry run)",
            )

        # Handle different strategies
        if strategy == SyncStrategy.SKIP:
            return SyncResult(
                document=doc,
                success=True,
                strategy=strategy,
                old_hash=drift_result.stored_hash,
                message="Skipped by strategy",
            )

        elif strategy == SyncStrategy.MANUAL:
            return SyncResult(
                document=doc,
                success=True,
                strategy=strategy,
                old_hash=drift_result.stored_hash,
                new_hash=drift_result.current_hash,
                message=f"Marked for manual review: {drift_result.message}",
            )

        elif strategy == SyncStrategy.REGENERATE:
            # Only regenerate AI-generated documents
            if doc.generated_by != "ai":
                return SyncResult(
                    document=doc,
                    success=False,
                    strategy=SyncStrategy.MANUAL,
                    error="Cannot auto-regenerate non-AI documents",
                    message=f"Document generated by '{doc.generated_by}' - requires manual update",
                )

            # Check if AI generator available
            if not self.ai_generator:
                return SyncResult(
                    document=doc,
                    success=False,
                    strategy=strategy,
                    error="AI generator not available",
                    message="AI generator required for regeneration",
                )

            # Regenerate document
            try:
                start_time = time.time()

                # Assemble context
                from ..generators import ContextAssembler

                assembler = ContextAssembler(spec_store=self.spec_store)
                context = assembler.assemble_for_spec(
                    spec_id=doc.based_on_spec_ids[0] if doc.based_on_spec_ids else None,
                    doc_type=doc.doc_type,
                )

                # Generate new content
                generation_result = self.ai_generator.generate(
                    doc_type=doc.doc_type,
                    context=context,
                )

                # Update document
                doc.content = generation_result.content
                doc.sync_hash = drift_result.current_hash
                doc.last_synced_at = datetime.now()
                doc.generation_model = generation_result.model

                # Save to database and file
                self.doc_store.update(doc, write_to_file=True)

                elapsed = time.time() - start_time

                logger.info(f"Regenerated document {doc.id} in {elapsed:.1f}s")

                return SyncResult(
                    document=doc,
                    success=True,
                    strategy=strategy,
                    old_hash=drift_result.stored_hash,
                    new_hash=drift_result.current_hash,
                    regenerated=True,
                    generation_time_seconds=elapsed,
                    message=f"Successfully regenerated document",
                )

            except Exception as e:
                logger.error(f"Failed to regenerate document {doc_id}: {e}")
                return SyncResult(
                    document=doc,
                    success=False,
                    strategy=strategy,
                    error=str(e),
                    message=f"Regeneration failed: {e}",
                )

    def sync_project(
        self,
        project_id: int,
        strategy: SyncStrategy = SyncStrategy.REGENERATE,
        dry_run: bool = False,
        staleness_threshold_days: int = 30
    ) -> List[SyncResult]:
        """Sync all documents in a project.

        Args:
            project_id: Project ID
            strategy: Sync strategy to use
            dry_run: If True, only check drift without regenerating
            staleness_threshold_days: Days threshold for staleness

        Returns:
            List of sync results

        Example:
            >>> results = manager.sync_project(project_id=1, dry_run=True)
            >>> drifted = [r for r in results if r.old_hash != r.new_hash]
            >>> print(f"{len(drifted)} documents need sync")
        """
        # Find drifted documents
        drifted_docs = self.drift_detector.get_drifted_documents(
            project_id=project_id,
            staleness_threshold_days=staleness_threshold_days
        )

        logger.info(
            f"Found {len(drifted_docs)} documents needing sync in project {project_id}"
        )

        # Sync each document
        results = []
        for drift_result in drifted_docs:
            try:
                sync_result = self.sync_document(
                    doc_id=drift_result.document.id,
                    strategy=strategy,
                    dry_run=dry_run
                )
                results.append(sync_result)
            except Exception as e:
                logger.error(f"Failed to sync document {drift_result.document.id}: {e}")
                results.append(SyncResult(
                    document=drift_result.document,
                    success=False,
                    strategy=strategy,
                    error=str(e),
                    message=f"Sync failed: {e}",
                ))

        return results

    def get_sync_summary(self, results: List[SyncResult]) -> Dict[str, Any]:
        """Get summary statistics for sync results.

        Args:
            results: List of sync results

        Returns:
            Summary dictionary

        Example:
            >>> summary = manager.get_sync_summary(results)
            >>> print(f"{summary['successful']} successful, {summary['failed']} failed")
        """
        successful = sum(1 for r in results if r.success)
        failed = sum(1 for r in results if not r.success)
        regenerated = sum(1 for r in results if r.regenerated)
        skipped = sum(1 for r in results if r.strategy == SyncStrategy.SKIP)
        manual = sum(1 for r in results if r.strategy == SyncStrategy.MANUAL)

        total_time = sum(
            r.generation_time_seconds
            for r in results
            if r.generation_time_seconds
        )

        return {
            "total": len(results),
            "successful": successful,
            "failed": failed,
            "regenerated": regenerated,
            "skipped": skipped,
            "manual_review_needed": manual,
            "total_generation_time_seconds": total_time,
            "average_generation_time_seconds": total_time / regenerated if regenerated > 0 else 0,
        }
