"""
RECALL Tool - Search and retrieve memories using semantic search

This tool is discoverable via filesystem and directly executable.
Agents can import and call this function directly.

Usage:
    from athena.tools.memory.recall import recall
    results = recall('How to authenticate users?', limit=5)

Returns:
    List[Memory] with relevance scores
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from athena.manager import UnifiedMemoryManager


def recall(query: str, limit: int = 10, min_score: float = 0.5):
    """
    Search and retrieve memories using semantic search

    Parameters:
        query: Search query (string describing what to find)
        limit: Maximum number of results to return (default: 10)
        min_score: Minimum relevance score (0.0-1.0, default: 0.5)

    Returns:
        List[Memory] - Matching memories with relevance scores

    Example:
        >>> results = recall('How to authenticate users?', limit=5)
        >>> for memory in results:
        ...     print(f"{memory.content} (score: {memory.score})")

    Raises:
        ValueError: If query is empty or limit is invalid
        RuntimeError: If database connection fails
    """
    try:
        manager = UnifiedMemoryManager()
        results = manager.recall(query=query, limit=limit, min_score=min_score)
        return results
    except Exception as e:
        raise RuntimeError(f"Memory recall failed: {str(e)}") from e

