"""Base classes for specification extractors."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..models import Specification, SpecType


@dataclass
class ExtractionConfig:
    """Configuration for spec extraction."""

    # General settings
    project_id: int = 1
    auto_detect_type: bool = True
    validate_after_extract: bool = True

    # Framework-specific settings
    framework_hints: List[str] = field(default_factory=list)  # e.g., ["fastapi", "flask"]

    # Database settings (for DB extraction)
    db_url: Optional[str] = None
    db_schema: Optional[str] = None

    # API settings (for GraphQL/REST)
    api_url: Optional[str] = None
    api_headers: Dict[str, str] = field(default_factory=dict)

    # Output settings
    output_name: Optional[str] = None
    output_version: str = "1.0.0"
    output_description: Optional[str] = None


@dataclass
class ExtractionResult:
    """Result of specification extraction."""

    spec: Specification
    confidence: float  # 0-1 score (how confident we are in accuracy)
    warnings: List[str] = field(default_factory=list)
    coverage: float = 1.0  # 0-1 score (% of code/schema analyzed)
    requires_review: bool = False  # Flag for human review
    extraction_method: str = ""  # Description of how extraction was done
    extracted_at: datetime = field(default_factory=datetime.now)

    # Metadata about what was extracted
    metadata: Dict[str, Any] = field(default_factory=dict)


class SpecExtractor(ABC):
    """Base class for specification extractors.

    Extractors follow a plugin architecture where each extractor knows how to:
    1. Detect if it can handle a given source (file, URL, database)
    2. Extract a specification from that source
    3. Provide confidence and quality metrics

    Example:
        >>> extractor = PythonAPIExtractor()
        >>> if extractor.can_extract(Path("api/main.py")):
        ...     result = extractor.extract(Path("api/main.py"))
        ...     print(f"Confidence: {result.confidence * 100}%")
    """

    @abstractmethod
    def can_extract(self, source: Any, config: Optional[ExtractionConfig] = None) -> bool:
        """Check if this extractor can handle the source.

        Args:
            source: Source to extract from (Path, URL, database connection, etc.)
            config: Optional extraction configuration

        Returns:
            True if this extractor can handle the source

        Example:
            >>> extractor = PythonAPIExtractor()
            >>> extractor.can_extract(Path("api/main.py"))
            True
            >>> extractor.can_extract(Path("schema.graphql"))
            False
        """
        pass

    @abstractmethod
    def extract(
        self,
        source: Any,
        config: Optional[ExtractionConfig] = None
    ) -> ExtractionResult:
        """Extract specification from source.

        Args:
            source: Source to extract from
            config: Optional extraction configuration

        Returns:
            ExtractionResult with spec and quality metrics

        Raises:
            ValueError: If extraction fails or source is invalid

        Example:
            >>> extractor = PythonAPIExtractor()
            >>> result = extractor.extract(Path("api/main.py"))
            >>> print(result.spec.name)
            "User API"
        """
        pass

    @abstractmethod
    def get_supported_spec_types(self) -> List[SpecType]:
        """Get list of spec types this extractor can produce.

        Returns:
            List of SpecType enum values

        Example:
            >>> extractor = PythonAPIExtractor()
            >>> extractor.get_supported_spec_types()
            [SpecType.OPENAPI]
        """
        pass

    def get_name(self) -> str:
        """Get human-readable name of this extractor.

        Returns:
            Extractor name

        Example:
            >>> extractor = PythonAPIExtractor()
            >>> extractor.get_name()
            "Python API Extractor (FastAPI/Flask)"
        """
        return self.__class__.__name__

    def get_description(self) -> str:
        """Get description of what this extractor does.

        Returns:
            Extractor description
        """
        return self.__doc__ or "No description available"

    def validate_result(self, result: ExtractionResult) -> ExtractionResult:
        """Validate extraction result and add warnings if needed.

        Args:
            result: Extraction result to validate

        Returns:
            Validated result (may have additional warnings)
        """
        # Check confidence
        if result.confidence < 0.5:
            result.warnings.append(
                f"Low confidence ({result.confidence * 100:.0f}%) - "
                "extraction may be inaccurate, manual review recommended"
            )
            result.requires_review = True

        # Check coverage
        if result.coverage < 0.8:
            result.warnings.append(
                f"Incomplete coverage ({result.coverage * 100:.0f}%) - "
                "some parts of the source were not analyzed"
            )

        # Check if spec content is empty
        if not result.spec.content or len(result.spec.content.strip()) == 0:
            result.warnings.append("Extracted specification has no content")
            result.requires_review = True
            result.confidence = 0.0

        return result
