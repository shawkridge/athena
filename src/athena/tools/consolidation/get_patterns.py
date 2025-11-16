"""
GET_PATTERNS Tool - Retrieve learned patterns from consolidation

This tool is discoverable via filesystem and directly executable.
Agents can import and call this function directly.

Usage:
    from athena.tools.consolidation.get_patterns import get_patterns
    patterns = get_patterns(limit=10, domain='security')
"""

import sys
from pathlib import Path
from typing import Optional, List

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from athena.manager import UnifiedMemoryManager


def get_patterns(limit: int = 10, domain: Optional[str] = None, min_confidence: float = 0.5) -> List:
    """
    Retrieve learned patterns from consolidation

    Parameters:
        limit: Maximum number of patterns to return (default: 10)
        domain: Optional domain filter (e.g., 'security', 'performance')
        min_confidence: Minimum confidence score 0.0-1.0 (default: 0.5)

    Returns:
        List[Pattern] - Learned patterns with confidence scores and metadata

    Example:
        >>> patterns = get_patterns(limit=5, domain='security')
        >>> for pattern in patterns:
        ...     print(f"{pattern.name} (confidence: {pattern.confidence})")

    Raises:
        ValueError: If limit or confidence parameters invalid
        RuntimeError: If pattern retrieval fails
    """
    if not isinstance(limit, int) or limit <= 0:
        raise ValueError(f"limit must be positive integer, got {limit}")

    if not (0.0 <= min_confidence <= 1.0):
        raise ValueError(f"min_confidence must be between 0.0 and 1.0, got {min_confidence}")

    try:
        manager = UnifiedMemoryManager()
        patterns = manager.get_patterns(limit=limit, domain=domain, min_confidence=min_confidence)
        return patterns
    except Exception as e:
        raise RuntimeError(f"Pattern retrieval failed: {str(e)}") from e

