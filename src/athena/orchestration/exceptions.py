"""Custom exceptions for orchestration layer."""


class OrchestrationError(Exception):
    """Base exception for orchestration errors."""

    pass


class TaskError(OrchestrationError):
    """Task-related errors."""

    pass


class TaskNotFoundError(TaskError):
    """Task not found."""

    pass


class TaskAlreadyAssignedError(TaskError):
    """Task already assigned to an agent."""

    pass


class TaskDependencyError(TaskError):
    """Task dependency error (circular, missing, etc.)."""

    pass


class AgentError(OrchestrationError):
    """Agent-related errors."""

    pass


class AgentNotFoundError(AgentError):
    """Agent not found in registry."""

    pass


class AgentAlreadyRegisteredError(AgentError):
    """Agent already registered."""

    pass


class RoutingError(OrchestrationError):
    """Routing errors."""

    pass


class NoCapableAgentError(RoutingError):
    """No agent capable of executing task."""

    pass


class NoAvailableAgentError(RoutingError):
    """All capable agents are at capacity."""

    pass
