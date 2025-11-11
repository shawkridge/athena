"""In-memory storage for marketplace procedures and metadata."""

import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from .marketplace import (
    MarketplaceProcedure,
    ProcedureMetadata,
    ProcedureReview,
    ProcedureInstallation,
    ProcedureQuality,
    UseCaseCategory,
)


class MarketplaceStore:
    """In-memory storage for marketplace procedures."""

    def __init__(self, database=None):
        """Initialize marketplace store.

        Args:
            database: Optional database instance (for future persistence)
        """
        self.db = database
        # In-memory storage
        self._procedures: Dict[str, MarketplaceProcedure] = {}
        self._reviews: Dict[str, List[ProcedureReview]] = {}
        self._installations: Dict[str, List[ProcedureInstallation]] = {}

    def store_procedure(
        self,
        metadata: ProcedureMetadata,
        code: str,
        documentation: str,
        usage_examples: Optional[List[Dict[str, str]]] = None,
        performance_stats: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Store a procedure in the marketplace.

        Args:
            metadata: Procedure metadata
            code: Procedure code
            documentation: Documentation
            usage_examples: Usage examples
            performance_stats: Performance statistics

        Returns:
            Procedure ID
        """
        if usage_examples is None:
            usage_examples = []
        if performance_stats is None:
            performance_stats = {}

        procedure = MarketplaceProcedure(
            metadata=metadata,
            code=code,
            documentation=documentation,
            usage_examples=usage_examples,
            performance_stats=performance_stats,
        )

        self._procedures[metadata.procedure_id] = procedure
        return metadata.procedure_id

    def get_procedure(self, procedure_id: str) -> Optional[MarketplaceProcedure]:
        """Get procedure from marketplace.

        Args:
            procedure_id: Procedure ID

        Returns:
            MarketplaceProcedure or None if not found
        """
        return self._procedures.get(procedure_id)

    def list_procedures(
        self,
        category: Optional[UseCaseCategory] = None,
        quality_level: Optional[ProcedureQuality] = None,
        tags: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[MarketplaceProcedure]:
        """List procedures with optional filters.

        Args:
            category: Filter by use case category
            quality_level: Filter by quality level
            tags: Filter by tags (all tags must be present)
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of matching procedures
        """
        procedures = list(self._procedures.values())

        # Apply filters
        if category:
            procedures = [p for p in procedures if p.metadata.use_case == category]

        if quality_level:
            procedures = [p for p in procedures if p.metadata.quality_level == quality_level]

        if tags:
            procedures = [
                p for p in procedures
                if all(tag in p.metadata.tags for tag in tags)
            ]

        # Apply pagination
        return procedures[offset : offset + limit]

    def search_procedures(
        self,
        query: str,
        limit: int = 10,
        include_code: bool = False,
    ) -> List[MarketplaceProcedure]:
        """Search procedures by name, description, or tags.

        Args:
            query: Search query
            limit: Maximum number of results
            include_code: Whether to include full code in results

        Returns:
            List of matching procedures
        """
        query_lower = query.lower()
        matches = []

        for procedure in self._procedures.values():
            name_match = query_lower in procedure.metadata.name.lower()
            desc_match = query_lower in procedure.metadata.description.lower()
            tag_match = any(query_lower in tag.lower() for tag in procedure.metadata.tags)

            if name_match or desc_match or tag_match:
                matches.append(procedure)

        # Sort by relevance
        matches.sort(
            key=lambda p: (
                query_lower not in p.metadata.name.lower(),
                query_lower not in p.metadata.description.lower(),
                p.metadata.name,
            )
        )

        result = matches[:limit]

        # Strip code if requested
        if not include_code:
            for procedure in result:
                procedure.code = ""

        return result

    def update_procedure_stats(
        self,
        procedure_id: str,
        execution_count: int,
        success_rate: float,
        avg_execution_time_ms: float,
    ) -> bool:
        """Update execution statistics for a procedure.

        Args:
            procedure_id: Procedure ID
            execution_count: Number of executions
            success_rate: Success rate (0.0-1.0)
            avg_execution_time_ms: Average execution time in milliseconds

        Returns:
            True if updated, False if procedure not found
        """
        procedure = self._procedures.get(procedure_id)
        if not procedure:
            return False

        procedure.metadata.execution_count = execution_count
        procedure.metadata.success_rate = success_rate
        procedure.metadata.avg_execution_time_ms = avg_execution_time_ms
        procedure.metadata.updated_at = datetime.now()

        return True

    def record_execution(
        self,
        procedure_id: str,
        success: bool,
        execution_time_ms: float,
    ) -> bool:
        """Record a procedure execution and update stats.

        Args:
            procedure_id: Procedure ID
            success: Whether execution was successful
            execution_time_ms: Execution time in milliseconds

        Returns:
            True if recorded, False if procedure not found
        """
        procedure = self.get_procedure(procedure_id)
        if not procedure:
            return False

        metadata = procedure.metadata
        execution_count = metadata.execution_count + 1

        # Update success rate
        old_successes = int(metadata.execution_count * metadata.success_rate)
        new_successes = old_successes + (1 if success else 0)
        success_rate = new_successes / execution_count if execution_count > 0 else 0.0

        # Update average execution time
        old_total_time = metadata.avg_execution_time_ms * metadata.execution_count
        new_total_time = old_total_time + execution_time_ms
        avg_execution_time = new_total_time / execution_count

        return self.update_procedure_stats(
            procedure_id,
            execution_count,
            success_rate,
            avg_execution_time,
        )

    def add_review(self, review: ProcedureReview) -> int:
        """Add review for a procedure.

        Args:
            review: ProcedureReview object

        Returns:
            Review ID (index in list)
        """
        if review.procedure_id not in self._reviews:
            self._reviews[review.procedure_id] = []

        self._reviews[review.procedure_id].append(review)
        return len(self._reviews[review.procedure_id]) - 1

    def get_reviews(self, procedure_id: str, limit: int = 50) -> List[ProcedureReview]:
        """Get reviews for a procedure.

        Args:
            procedure_id: Procedure ID
            limit: Maximum number of reviews

        Returns:
            List of reviews
        """
        reviews = self._reviews.get(procedure_id, [])
        return reviews[-limit:]

    def get_average_rating(self, procedure_id: str) -> Optional[float]:
        """Get average rating for a procedure.

        Args:
            procedure_id: Procedure ID

        Returns:
            Average rating or None
        """
        reviews = self.get_reviews(procedure_id)
        if not reviews:
            return None

        total = sum(r.rating for r in reviews)
        return total / len(reviews)

    def record_installation(self, installation: ProcedureInstallation) -> int:
        """Record a procedure installation.

        Args:
            installation: ProcedureInstallation object

        Returns:
            Installation record ID
        """
        if installation.procedure_id not in self._installations:
            self._installations[installation.procedure_id] = []

        self._installations[installation.procedure_id].append(installation)
        return len(self._installations[installation.procedure_id]) - 1

    def get_installations(self, procedure_id: str) -> List[ProcedureInstallation]:
        """Get installation records for a procedure.

        Args:
            procedure_id: Procedure ID

        Returns:
            List of installation records
        """
        installations = self._installations.get(procedure_id, [])
        return sorted(installations, key=lambda x: x.installed_at, reverse=True)

    def get_installation_count(self, procedure_id: str) -> int:
        """Get number of installations for a procedure.

        Args:
            procedure_id: Procedure ID

        Returns:
            Installation count
        """
        return len(self._installations.get(procedure_id, []))

    def delete_procedure(self, procedure_id: str) -> bool:
        """Delete procedure from marketplace.

        Args:
            procedure_id: Procedure ID

        Returns:
            True if deleted, False if not found
        """
        if procedure_id not in self._procedures:
            return False

        del self._procedures[procedure_id]
        # Also clean up reviews and installations
        self._reviews.pop(procedure_id, None)
        self._installations.pop(procedure_id, None)

        return True
