"""Marketplace for discovering and sharing procedures."""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class ProcedureQuality(Enum):
    """Quality rating for marketplace procedures."""

    EXPERIMENTAL = "experimental"
    BETA = "beta"
    STABLE = "stable"
    PRODUCTION = "production"


class UseCaseCategory(Enum):
    """Category of procedure use case."""

    DATA_PROCESSING = "data_processing"
    ANALYSIS = "analysis"
    AUTOMATION = "automation"
    INTEGRATION = "integration"
    UTILITY = "utility"
    TESTING = "testing"
    OTHER = "other"


@dataclass
class ProcedureMetadata:
    """Metadata for a marketplace procedure."""

    procedure_id: str
    name: str
    description: str
    author: str
    version: str
    quality_level: ProcedureQuality
    use_case: UseCaseCategory
    tags: List[str]
    dependencies: List[str] = None
    execution_count: int = 0
    success_rate: float = 1.0  # 0.0 to 1.0
    avg_execution_time_ms: float = 0.0
    created_at: datetime = None
    updated_at: datetime = None
    last_executed_at: Optional[datetime] = None

    def __post_init__(self):
        """Initialize fields."""
        if self.dependencies is None:
            self.dependencies = []
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "procedure_id": self.procedure_id,
            "name": self.name,
            "description": self.description,
            "author": self.author,
            "version": self.version,
            "quality_level": self.quality_level.value,
            "use_case": self.use_case.value,
            "tags": self.tags,
            "dependencies": self.dependencies,
            "execution_count": self.execution_count,
            "success_rate": self.success_rate,
            "avg_execution_time_ms": self.avg_execution_time_ms,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_executed_at": self.last_executed_at.isoformat() if self.last_executed_at else None,
        }


@dataclass
class MarketplaceProcedure:
    """A procedure available in the marketplace."""

    metadata: ProcedureMetadata
    code: str
    documentation: str
    usage_examples: List[Dict[str, str]]
    performance_stats: Dict[str, Any]
    ratings: Dict[str, float] = None  # e.g., {"usability": 4.5, "performance": 4.0}

    def __post_init__(self):
        """Initialize ratings."""
        if self.ratings is None:
            self.ratings = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "metadata": self.metadata.to_dict(),
            "code": self.code,
            "documentation": self.documentation,
            "usage_examples": self.usage_examples,
            "performance_stats": self.performance_stats,
            "ratings": self.ratings,
        }

    def to_compact_dict(self) -> Dict[str, Any]:
        """Compact representation without code."""
        return {
            "metadata": self.metadata.to_dict(),
            "documentation": self.documentation,
            "usage_examples": self.usage_examples,
            "performance_stats": self.performance_stats,
            "ratings": self.ratings,
        }


@dataclass
class ProcedureReview:
    """User review of a marketplace procedure."""

    procedure_id: str
    reviewer_id: str
    rating: float  # 0.0 to 5.0
    comment: str
    aspects: Dict[str, float] = None  # e.g., {"usability": 4, "performance": 3.5}
    helpful_count: int = 0
    created_at: datetime = None

    def __post_init__(self):
        """Initialize defaults."""
        if self.aspects is None:
            self.aspects = {}
        if self.created_at is None:
            self.created_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "procedure_id": self.procedure_id,
            "reviewer_id": self.reviewer_id,
            "rating": self.rating,
            "comment": self.comment,
            "aspects": self.aspects,
            "helpful_count": self.helpful_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


@dataclass
class ProcedureInstallation:
    """Record of a procedure installation."""

    procedure_id: str
    installed_at: datetime
    version: str
    installed_by: str
    installation_context: Dict[str, Any] = None
    auto_update: bool = True

    def __post_init__(self):
        """Initialize defaults."""
        if self.installation_context is None:
            self.installation_context = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "procedure_id": self.procedure_id,
            "installed_at": self.installed_at.isoformat(),
            "version": self.version,
            "installed_by": self.installed_by,
            "installation_context": self.installation_context,
            "auto_update": self.auto_update,
        }


class Marketplace:
    """Marketplace for discovering and managing procedures."""

    def __init__(self):
        """Initialize marketplace."""
        self.procedures: Dict[str, MarketplaceProcedure] = {}
        self.reviews: Dict[str, List[ProcedureReview]] = {}
        self.installations: Dict[str, List[ProcedureInstallation]] = {}

    def register_procedure(
        self,
        metadata: ProcedureMetadata,
        code: str,
        documentation: str,
        usage_examples: List[Dict[str, str]] = None,
        performance_stats: Dict[str, Any] = None,
    ) -> str:
        """Register a new procedure in the marketplace.

        Args:
            metadata: Procedure metadata
            code: Procedure code
            documentation: Procedure documentation
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

        self.procedures[metadata.procedure_id] = procedure
        return metadata.procedure_id

    def get_procedure(self, procedure_id: str) -> Optional[MarketplaceProcedure]:
        """Get procedure from marketplace.

        Args:
            procedure_id: Procedure ID

        Returns:
            MarketplaceProcedure or None
        """
        return self.procedures.get(procedure_id)

    def list_procedures(
        self,
        category: Optional[UseCaseCategory] = None,
        quality_level: Optional[ProcedureQuality] = None,
        tags: Optional[List[str]] = None,
    ) -> List[MarketplaceProcedure]:
        """List procedures in marketplace with optional filters.

        Args:
            category: Filter by use case category
            quality_level: Filter by quality level
            tags: Filter by tags (all tags must match)

        Returns:
            List of MarketplaceProcedure objects
        """
        results = []

        for procedure in self.procedures.values():
            # Check category filter
            if category and procedure.metadata.use_case != category:
                continue

            # Check quality level filter
            if quality_level and procedure.metadata.quality_level != quality_level:
                continue

            # Check tags filter
            if tags:
                if not all(tag in procedure.metadata.tags for tag in tags):
                    continue

            results.append(procedure)

        return results

    def search_procedures(self, query: str, limit: int = 10) -> List[MarketplaceProcedure]:
        """Search for procedures.

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of matching procedures
        """
        query_lower = query.lower()
        matches = []

        for procedure in self.procedures.values():
            # Score based on name, description, tags
            name_match = query_lower in procedure.metadata.name.lower()
            desc_match = query_lower in procedure.metadata.description.lower()
            tag_match = any(query_lower in tag.lower() for tag in procedure.metadata.tags)

            if name_match or desc_match or tag_match:
                matches.append(procedure)

        # Sort by relevance (name match > desc match > tag match)
        matches.sort(
            key=lambda p: (
                query_lower not in p.metadata.name.lower(),
                query_lower not in p.metadata.description.lower(),
                p.metadata.name,
            )
        )

        return matches[:limit]

    def add_review(self, review: ProcedureReview) -> None:
        """Add review for a procedure.

        Args:
            review: ProcedureReview object
        """
        if review.procedure_id not in self.reviews:
            self.reviews[review.procedure_id] = []

        self.reviews[review.procedure_id].append(review)

    def get_reviews(self, procedure_id: str) -> List[ProcedureReview]:
        """Get reviews for a procedure.

        Args:
            procedure_id: Procedure ID

        Returns:
            List of ProcedureReview objects
        """
        return self.reviews.get(procedure_id, [])

    def get_procedure_rating(self, procedure_id: str) -> Optional[float]:
        """Get average rating for a procedure.

        Args:
            procedure_id: Procedure ID

        Returns:
            Average rating (0.0-5.0) or None if no reviews
        """
        reviews = self.get_reviews(procedure_id)
        if not reviews:
            return None

        total = sum(r.rating for r in reviews)
        return total / len(reviews)

    def record_installation(self, installation: ProcedureInstallation) -> None:
        """Record procedure installation.

        Args:
            installation: ProcedureInstallation object
        """
        if installation.procedure_id not in self.installations:
            self.installations[installation.procedure_id] = []

        self.installations[installation.procedure_id].append(installation)

    def get_installations(self, procedure_id: str) -> List[ProcedureInstallation]:
        """Get installation records for a procedure.

        Args:
            procedure_id: Procedure ID

        Returns:
            List of installation records
        """
        return self.installations.get(procedure_id, [])

    def get_installation_count(self, procedure_id: str) -> int:
        """Get number of installations for a procedure.

        Args:
            procedure_id: Procedure ID

        Returns:
            Number of installations
        """
        return len(self.get_installations(procedure_id))
