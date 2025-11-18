"""
FORGET Tool - Delete memories by ID

This tool is discoverable via filesystem and directly executable.
Agents can import and call this function directly.

Usage:
    from athena.tools.memory.forget import forget
    success = forget(12345)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from athena.manager import UnifiedMemoryManager


def forget(memory_id: int) -> bool:
    """
    Delete a memory by ID

    Parameters:
        memory_id: ID of memory to delete

    Returns:
        bool - True if successfully deleted

    Example:
        >>> success = forget(12345)
        >>> if success:
        ...     print("Memory deleted")

    Raises:
        ValueError: If memory_id is invalid
        RuntimeError: If database connection fails
    """
    if not isinstance(memory_id, int) or memory_id <= 0:
        raise ValueError(f"Invalid memory_id: {memory_id}")

    try:
        manager = UnifiedMemoryManager()
        success = manager.forget(memory_id)
        return success
    except Exception as e:
        raise RuntimeError(f"Memory deletion failed: {str(e)}") from e
