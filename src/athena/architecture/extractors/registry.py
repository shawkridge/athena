"""Extractor registry for managing and discovering extractors."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from .base import SpecExtractor, ExtractionConfig, ExtractionResult

logger = logging.getLogger(__name__)


class ExtractorRegistry:
    """Registry of available specification extractors.

    The registry manages all extractors and provides auto-detection to find
    the right extractor for a given source.

    Example:
        >>> registry = ExtractorRegistry()
        >>> registry.register(PythonAPIExtractor())
        >>> extractor = registry.get_extractor(Path("api/main.py"))
        >>> result = extractor.extract(Path("api/main.py"))
    """

    def __init__(self):
        """Initialize empty registry."""
        self._extractors: List[SpecExtractor] = []

    def register(self, extractor: SpecExtractor) -> None:
        """Register an extractor.

        Args:
            extractor: Extractor instance to register

        Example:
            >>> registry = ExtractorRegistry()
            >>> registry.register(PythonAPIExtractor())
        """
        self._extractors.append(extractor)
        logger.debug(f"Registered extractor: {extractor.get_name()}")

    def unregister(self, extractor_class: Type[SpecExtractor]) -> None:
        """Unregister an extractor by class.

        Args:
            extractor_class: Extractor class to unregister
        """
        self._extractors = [
            e for e in self._extractors
            if not isinstance(e, extractor_class)
        ]

    def get_all(self) -> List[SpecExtractor]:
        """Get all registered extractors.

        Returns:
            List of all extractors
        """
        return self._extractors.copy()

    def get_extractor(
        self,
        source: Any,
        config: Optional[ExtractionConfig] = None
    ) -> Optional[SpecExtractor]:
        """Find appropriate extractor for source.

        Tries each registered extractor's can_extract() method and returns
        the first one that can handle the source.

        Args:
            source: Source to find extractor for
            config: Optional extraction configuration

        Returns:
            Extractor that can handle the source, or None

        Example:
            >>> registry = ExtractorRegistry()
            >>> registry.register(PythonAPIExtractor())
            >>> extractor = registry.get_extractor(Path("api/main.py"))
            >>> extractor.get_name()
            "Python API Extractor (FastAPI/Flask)"
        """
        for extractor in self._extractors:
            try:
                if extractor.can_extract(source, config):
                    logger.info(
                        f"Found extractor for source: {extractor.get_name()}"
                    )
                    return extractor
            except Exception as e:
                logger.warning(
                    f"Error checking {extractor.get_name()}: {e}"
                )
                continue

        logger.warning(f"No extractor found for source: {source}")
        return None

    def extract(
        self,
        source: Any,
        config: Optional[ExtractionConfig] = None
    ) -> Optional[ExtractionResult]:
        """Auto-detect and extract specification from source.

        Convenience method that finds the right extractor and extracts.

        Args:
            source: Source to extract from
            config: Optional extraction configuration

        Returns:
            ExtractionResult if successful, None if no extractor found

        Raises:
            ValueError: If extraction fails

        Example:
            >>> registry = ExtractorRegistry()
            >>> registry.register(PythonAPIExtractor())
            >>> result = registry.extract(Path("api/main.py"))
            >>> print(result.spec.name)
            "User API"
        """
        extractor = self.get_extractor(source, config)
        if not extractor:
            return None

        logger.info(f"Extracting with {extractor.get_name()}...")
        return extractor.extract(source, config)

    def get_supported_sources(self) -> Dict[str, List[str]]:
        """Get summary of what sources each extractor supports.

        Returns:
            Dict mapping extractor name to list of supported source types

        Example:
            >>> registry.get_supported_sources()
            {
                "Python API Extractor": ["FastAPI", "Flask"],
                "Database Extractor": ["PostgreSQL", "MySQL"]
            }
        """
        result = {}
        for extractor in self._extractors:
            spec_types = [t.value for t in extractor.get_supported_spec_types()]
            result[extractor.get_name()] = spec_types
        return result


# Global registry instance
_global_registry: Optional[ExtractorRegistry] = None


def get_registry() -> ExtractorRegistry:
    """Get the global extractor registry.

    Creates and initializes the registry on first call.

    Returns:
        Global ExtractorRegistry instance
    """
    global _global_registry

    if _global_registry is None:
        _global_registry = ExtractorRegistry()
        _initialize_default_extractors()

    return _global_registry


def _initialize_default_extractors() -> None:
    """Register default extractors in global registry."""
    from .python_api import PythonAPIExtractor

    registry = get_registry()
    registry.register(PythonAPIExtractor())

    logger.info(f"Initialized {len(registry.get_all())} default extractors")


def get_extractor(
    source: Any,
    config: Optional[ExtractionConfig] = None
) -> Optional[SpecExtractor]:
    """Convenience function to get extractor from global registry.

    Args:
        source: Source to find extractor for
        config: Optional extraction configuration

    Returns:
        Extractor that can handle the source, or None

    Example:
        >>> from athena.architecture.extractors import get_extractor
        >>> extractor = get_extractor(Path("api/main.py"))
        >>> result = extractor.extract(Path("api/main.py"))
    """
    return get_registry().get_extractor(source, config)


def register_extractor(extractor: SpecExtractor) -> None:
    """Register an extractor in the global registry.

    Args:
        extractor: Extractor instance to register

    Example:
        >>> from athena.architecture.extractors import register_extractor
        >>> register_extractor(MyCustomExtractor())
    """
    get_registry().register(extractor)
