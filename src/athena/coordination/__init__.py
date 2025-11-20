"""
Athena Multi-Agent Coordination System

Provides orchestrated multi-agent execution for complex tasks.
"""

from .models import (
    Agent,
    AgentStatus,
    AgentType,
    Task,
    TaskStatus,
    TaskPriority,
    CoordinationEvent,
    OrchestrationState,
    AgentMetrics,
    AGENT_CAPABILITIES,
)
from .operations import CoordinationOperations
from .orchestrator import Orchestrator
from .agent_worker import AgentWorker
from .memory_offload import MemoryOffloadManager, OrchestrationContextManager
from .health_monitor import HealthMonitor, RecoveryPolicy
from .monitor import MonitorDashboard
from .learning_integration import (
    LearningIntegrationManager,
    AgentPerformanceMetrics,
    get_learning_manager,
)

# Specialist agents
from .agents.research import ResearchAgent
from .agents.analysis import AnalysisAgent
from .agents.synthesis import SynthesisAgent
from .agents.validation import ValidationAgent
from .agents.optimization import OptimizationAgent
from .agents.documentation import DocumentationAgent
from .agents.review import CodeReviewAgent
from .agents.debugging import DebuggingAgent

__all__ = [
    # Models
    "Agent",
    "AgentStatus",
    "AgentType",
    "Task",
    "TaskStatus",
    "TaskPriority",
    "CoordinationEvent",
    "OrchestrationState",
    "AgentMetrics",
    "AGENT_CAPABILITIES",
    # Operations
    "CoordinationOperations",
    # Orchestration
    "Orchestrator",
    "AgentWorker",
    # Memory & Health
    "MemoryOffloadManager",
    "OrchestrationContextManager",
    "HealthMonitor",
    "RecoveryPolicy",
    "MonitorDashboard",
    # Learning Integration
    "LearningIntegrationManager",
    "AgentPerformanceMetrics",
    "get_learning_manager",
    # Specialist Agents (8 types)
    "ResearchAgent",
    "AnalysisAgent",
    "SynthesisAgent",
    "ValidationAgent",
    "OptimizationAgent",
    "DocumentationAgent",
    "CodeReviewAgent",
    "DebuggingAgent",
]
