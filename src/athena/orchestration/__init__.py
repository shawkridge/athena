"""Orchestration layer - coordination of complex multi-agent operations.

Implements the SubAgent and coordination patterns from the agentic diagram,
enabling specialized agents to work in parallel with feedback coordination.

Key components:
- SubAgentOrchestrator: Main orchestration engine
- SubAgent types: Clustering, Validation, Extraction, Integration, etc.
- Feedback coordination: Results feed back to dependent agents
- Parallel execution: Multiple agents work simultaneously
"""

from .subagent_orchestrator import (
    SubAgentOrchestrator,
    SubAgent,
    SubAgentTask,
    SubAgentResult,
    SubAgentType,
    AgentStatus,
    ClusteringSubAgent,
    ValidationSubAgent,
    ExtractionSubAgent,
    IntegrationSubAgent,
)

__all__ = [
    "SubAgentOrchestrator",
    "SubAgent",
    "SubAgentTask",
    "SubAgentResult",
    "SubAgentType",
    "AgentStatus",
    "ClusteringSubAgent",
    "ValidationSubAgent",
    "ExtractionSubAgent",
    "IntegrationSubAgent",
]
