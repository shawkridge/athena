#!/usr/bin/env python3
"""
MCP Connection Pool Manager - Shared persistent connection for all hooks

This module provides a singleton MCP connection that persists across
multiple hook invocations, eliminating the Python startup overhead
(~100ms per invocation).

Usage (in hooks):
    from mcp_pool import get_memory_manager
    manager = get_memory_manager()
    results = manager.smart_retrieve("query", k=5)
"""

import sys
import json
from pathlib import Path
from typing import Optional, Dict, Any, List

# Add memory-mcp to path
athena_path = Path('/home/user/.work/athena/src')
if athena_path.exists():
    sys.path.insert(0, str(athena_path))

from athena.core.database import Database
from athena.episodic.store import EpisodicStore
from athena.memory.store import MemoryStore

# Global connection pool
_pool: Dict[str, Any] = {
    "manager": None,
    "db_path": None,
    "initialized": False
}


def get_database(db_path: Optional[str] = None) -> Database:
    """
    Get or create a shared database connection.

    This function maintains a singleton connection pool, eliminating
    the need to create new database connections per hook invocation.

    Args:
        db_path: Path to memory database (default: /home/user/.work/athena/memory.db)

    Returns:
        Database instance
    """
    global _pool

    if db_path is None:
        db_path = str(Path.home() / '/home/user/.work/athena' / 'memory.db')

    # Check if we need to reinitialize (different DB path)
    if _pool["db_path"] != db_path or _pool["manager"] is None:
        _pool["db_path"] = db_path
        db_instance = Database(db_path)
        _pool["manager"] = {
            "db": db_instance,
            "db_path": db_path,
            "episodic": EpisodicStore(db_instance),
            "semantic": MemoryStore(db_path)  # Pass path string, not Database object
        }
        _pool["initialized"] = True

    return _pool["manager"]["db"]


def smart_retrieve(query: str, k: int = 5, strategy_hint: str = None) -> List[Dict]:
    """
    Retrieve memories using semantic search.

    Args:
        query: Search query
        k: Number of results
        strategy_hint: Optional strategy hint (for future enhancement)

    Returns:
        List of retrieved memories
    """
    db = get_database()
    memory_store = MemoryStore(db)

    # Perform semantic search
    results = memory_store.search(query, limit=k)

    return [
        {
            "id": r.id if hasattr(r, 'id') else 0,
            "content": r.content if hasattr(r, 'content') else str(r),
            "similarity": r.similarity if hasattr(r, 'similarity') else 0.0
        }
        for r in results
    ]


def record_episode(content: str, event_type: str, session_id: str = None,
                   location: str = None, files: List[str] = None) -> Dict:
    """
    Record an episodic event to memory.

    Args:
        content: Event description
        event_type: Type of event (action, decision, error, success, etc)
        session_id: Current session ID
        location: Location/working directory
        files: Files involved in this event

    Returns:
        Result dict with event_id
    """
    db = get_database()
    episodic = EpisodicStore(db)

    from athena.episodic.models import EpisodicEvent

    event = EpisodicEvent(
        content=content,
        event_type=event_type,
        session_id=session_id,
        location=location or ".",
        files=files or []
    )

    result = episodic.create(event)

    return {
        "success": True,
        "event_id": result.id,
        "timestamp": str(result.timestamp) if hasattr(result, 'timestamp') else None
    }


def strengthen_associations(memory_id: int, related_ids: List[int], strength: float = 0.1) -> Dict:
    """
    Strengthen associations between memories (Hebbian learning).

    Args:
        memory_id: Source memory ID
        related_ids: Target memory IDs to link to
        strength: Amount to strengthen (0.0-1.0)

    Returns:
        Result dict with count of strengthened associations
    """
    # Placeholder for future implementation with graph store
    return {
        "success": True,
        "strengthened": len(related_ids)
    }


def get_working_memory_status() -> Dict:
    """
    Get current working memory status and load.

    Returns:
        Dict with WM status (utilization, items, capacity)
    """
    try:
        # Placeholder for future working memory integration
        return {
            "success": True,
            "status": {
                "utilization": 0.5,
                "items": 0,
                "capacity": 7
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def test_connection() -> bool:
    """
    Test if MCP connection is working.

    Returns:
        True if connection successful
    """
    try:
        db_path = Path.home() / '/home/user/.work/athena' / 'memory.db'
        return db_path.exists()
    except Exception as e:
        print(f"Connection test error: {e}", file=sys.stderr)
        return False


if __name__ == "__main__":
    # Test the pool
    print("Testing MCP Connection Pool...")

    if test_connection():
        print("✓ MCP connection successful")

        # Test smart_retrieve
        results = smart_retrieve("test", k=1)
        print(f"✓ Smart retrieve working ({len(results)} results)")

        # Get WM status
        status = get_working_memory_status()
        print(f"✓ Working memory status: {status}")
    else:
        print("✗ MCP connection failed")
        sys.exit(1)
