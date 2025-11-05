"""AI coordination layer for agent-driven development.

This layer sits on top of memory-mcp and provides:
- ProjectContext: Centralized project state
- ExecutionTraces: Tracking what AI tried and outcomes
- ThinkingTraces: AI reasoning storage
- CodeContext: Task-scoped code management
- ActionCycle: Goal → Plan → Execute → Learn orchestration
- SessionContinuity: Resume capability
- LearningIntegration: Auto feedback loops
"""

from .project_context import ProjectContext, ProjectPhase, Decision, ErrorPattern
from .project_context_store import ProjectContextStore
from .execution_traces import (
    ExecutionTrace,
    ExecutionOutcome,
    CodeChange,
    ExecutionError,
    ExecutionDecision,
    ExecutionLesson,
    QualityAssessment,
)
from .execution_trace_store import ExecutionTraceStore
from .thinking_traces import (
    ThinkingTrace,
    ReasoningPattern,
    ProblemType,
    ReasoningStep,
)
from .thinking_trace_store import ThinkingTraceStore
from .thinking_trace_mcp_tools import ThinkingTraceMCPTools
from .code_context import (
    CodeContext,
    FileInfo,
    FileDependency,
    RecentChange,
    KnownIssue,
    FileRole,
    DependencyType,
    IssueSeverity,
    IssueStatus,
)
from .code_context_store import CodeContextStore
from .code_context_mcp_tools import CodeContextMCPTools
from .action_cycles import (
    ActionCycle,
    CycleStatus,
    ExecutionSummary,
    LessonLearned,
    PlanAdjustment,
    PlanAssumption,
)
from .action_cycle_store import ActionCycleStore
from .action_cycle_mcp_tools import ActionCycleMCPTools
from .session_continuity import (
    SessionSnapshot,
    SessionStatus,
    SessionMetadata,
    ResumptionRecommendation,
    ActionCycleSnapshot,
    CodeContextSnapshot,
    ExecutionTraceSnapshot,
    ProjectContextSnapshot,
)
from .session_continuity_store import SessionContinuityStore
from .session_continuity_mcp_tools import SessionContinuityMCPTools
from .learning_integration import (
    LessonToProcedure,
    ProcedureCandidate,
    FeedbackUpdate,
    LearningCycle,
    LearningMetrics,
    PatternType,
    FeedbackUpdateType,
)
from .learning_integration_store import LearningIntegrationStore
from .learning_integration_mcp_tools import LearningIntegrationMCPTools

__all__ = [
    # ProjectContext
    "ProjectContext",
    "ProjectPhase",
    "Decision",
    "ErrorPattern",
    "ProjectContextStore",
    # ExecutionTraces
    "ExecutionTrace",
    "ExecutionOutcome",
    "CodeChange",
    "ExecutionError",
    "ExecutionDecision",
    "ExecutionLesson",
    "QualityAssessment",
    "ExecutionTraceStore",
    # ThinkingTraces
    "ThinkingTrace",
    "ReasoningPattern",
    "ProblemType",
    "ReasoningStep",
    "ThinkingTraceStore",
    "ThinkingTraceMCPTools",
    # CodeContext
    "CodeContext",
    "FileInfo",
    "FileDependency",
    "RecentChange",
    "KnownIssue",
    "FileRole",
    "DependencyType",
    "IssueSeverity",
    "IssueStatus",
    "CodeContextStore",
    "CodeContextMCPTools",
    # ActionCycle
    "ActionCycle",
    "CycleStatus",
    "ExecutionSummary",
    "LessonLearned",
    "PlanAdjustment",
    "PlanAssumption",
    "ActionCycleStore",
    "ActionCycleMCPTools",
    # SessionContinuity
    "SessionSnapshot",
    "SessionStatus",
    "SessionMetadata",
    "ResumptionRecommendation",
    "ActionCycleSnapshot",
    "CodeContextSnapshot",
    "ExecutionTraceSnapshot",
    "ProjectContextSnapshot",
    "SessionContinuityStore",
    "SessionContinuityMCPTools",
    # LearningIntegration
    "LessonToProcedure",
    "ProcedureCandidate",
    "FeedbackUpdate",
    "LearningCycle",
    "LearningMetrics",
    "PatternType",
    "FeedbackUpdateType",
    "LearningIntegrationStore",
    "LearningIntegrationMCPTools",
]
