"""
REMEMBER Tool - Store new memories (facts, insights, decisions, patterns)

This tool is discoverable via filesystem and directly executable.
Agents can import and call this function directly.

Usage:
    from athena.tools.memory.remember import remember
    memory_id = remember('PostgreSQL is faster', 'FACT', tags=['database'])
"""

import sys
from pathlib import Path
from typing import Optional, List

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from athena.manager import UnifiedMemoryManager


def remember(
    content: str,
    event_type: str = "ACTION",
    tags: Optional[List[str]] = None,
    project_id: Optional[int] = None,
) -> int:
    """
    Store a new memory (semantic fact, insight, decision, or pattern)

    Parameters:
        content: Memory content (text to store)
        event_type: Type - one of: FACT, INSIGHT, DECISION, PATTERN, NOTE, ACTION
        tags: Optional list of metadata tags
        project_id: Optional project context

    Returns:
        int - Memory ID of stored memory

    Example:
        >>> memory_id = remember(
        ...     'PostgreSQL queries are 3x faster than SQLite',
        ...     'FACT',
        ...     tags=['database', 'performance']
        ... )

    Raises:
        ValueError: If content is empty
        RuntimeError: If database connection fails
    """
    if not content or not content.strip():
        raise ValueError("Memory content cannot be empty")

    try:
        manager = UnifiedMemoryManager()
        memory_id = manager.remember(
            content=content, event_type=event_type, tags=tags or [], project_id=project_id
        )
        return memory_id
    except Exception as e:
        raise RuntimeError(f"Memory storage failed: {str(e)}") from e
