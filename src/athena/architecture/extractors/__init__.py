"""Specification extraction from existing code.

This module provides tools to extract specifications from existing codebases:
- Extract OpenAPI specs from Python web frameworks (FastAPI, Flask)
- Extract Prisma schemas from databases
- Extract GraphQL schemas from endpoints
- Extract REST APIs via static analysis

Example:
    >>> from athena.architecture.extractors import get_extractor
    >>> extractor = get_extractor("api/main.py")
    >>> result = extractor.extract("api/main.py")
    >>> print(f"Extracted {result.spec.name} with {result.confidence}% confidence")
"""

from .base import SpecExtractor, ExtractionResult, ExtractionConfig
from .python_api import PythonAPIExtractor
from .registry import ExtractorRegistry, get_extractor, register_extractor

__all__ = [
    "SpecExtractor",
    "ExtractionResult",
    "ExtractionConfig",
    "PythonAPIExtractor",
    "ExtractorRegistry",
    "get_extractor",
    "register_extractor",
]
