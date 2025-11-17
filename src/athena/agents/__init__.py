"""
Memory Coordination Agents

This module provides agents that autonomously manage memory operations:
- AgentCoordinator: Base class for coordinated agents
- MemoryCoordinatorAgent: Decides what to remember and where
- PatternExtractorAgent: Extracts reusable procedures from episodic events

All agents follow the direct Python import paradigm (zero MCP overhead)
and coordinate via shared memory layers.
"""

from .coordinator import AgentCoordinator
from .memory_coordinator import (
    MemoryCoordinatorAgent,
    get_coordinator,
    coordinate_memory_storage,
)
from .pattern_extractor import (
    PatternExtractorAgent,
    get_extractor,
    extract_session_patterns,
    run_consolidation,
)

__all__ = [
    # Agent Coordination Base
    "AgentCoordinator",
    # Memory Coordination Agents
    "MemoryCoordinatorAgent",
    "get_coordinator",
    "coordinate_memory_storage",
    "PatternExtractorAgent",
    "get_extractor",
    "extract_session_patterns",
    "run_consolidation",
]
