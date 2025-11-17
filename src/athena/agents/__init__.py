"""
Memory Coordination and Specialized Agents

This module provides agents that autonomously manage memory and handle specialized tasks:

Phase 3 Agents (Memory Management):
- AgentCoordinator: Base class for coordinated agents
- MemoryCoordinatorAgent: Decides what to remember and where
- PatternExtractorAgent: Extracts reusable procedures from episodic events

Phase 4 Agents (Specialized Intelligence):
- CodeAnalyzerAgent: Autonomous code review and optimization
- ResearchCoordinatorAgent: Multi-step research workflow management
- WorkflowOrchestratorAgent: Dynamic task routing and orchestration
- MetacognitionAgent: System health monitoring and adaptation

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
from .code_analyzer import CodeAnalyzerAgent
from .research_coordinator import ResearchCoordinatorAgent
from .workflow_orchestrator import WorkflowOrchestratorAgent
from .metacognition import MetacognitionAgent

__all__ = [
    # Agent Coordination Base
    "AgentCoordinator",
    # Phase 3: Memory Coordination Agents
    "MemoryCoordinatorAgent",
    "get_coordinator",
    "coordinate_memory_storage",
    "PatternExtractorAgent",
    "get_extractor",
    "extract_session_patterns",
    "run_consolidation",
    # Phase 4: Specialized Agents
    "CodeAnalyzerAgent",
    "ResearchCoordinatorAgent",
    "WorkflowOrchestratorAgent",
    "MetacognitionAgent",
]
