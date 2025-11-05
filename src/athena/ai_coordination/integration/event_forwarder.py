"""Event forwarding from AI Coordination to Memory-MCP

Converts ExecutionTraces, ThinkingTraces, ActionCycles, and ProjectContext
changes into EpisodicEvents for storage in Memory-MCP's episodic layer.

This is the foundation of Phase 7.1 - enables AI Coordination data to flow
into the Memory-MCP consolidation system.
"""

import json
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from enum import Enum

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from athena.core.database import Database
    from athena.episodic.store import EpisodicStore
    from athena.ai_coordination.integration.event_forwarder_store import EventForwarderStore

from athena.episodic.models import EventType, EventOutcome


class ForwardingStatus(str, Enum):
    """Status of a forwarded event"""

    PENDING = "pending"
    COMPLETE = "complete"
    FAILED = "failed"


class ForwardingLogEntry(BaseModel):
    """Entry in the forwarding audit log

    Tracks what was forwarded, when, and where it went.
    Provides audit trail for debugging and validation.
    """

    id: Optional[int] = None
    source_type: str  # ExecutionTrace, ThinkingTrace, ActionCycle, ProjectContext
    source_id: str  # ID in coordination system
    target_type: str  # EpisodicEvent, SemanticMemory, etc
    target_id: str  # ID in memory-mcp system
    status: ForwardingStatus = ForwardingStatus.COMPLETE
    timestamp: int = Field(default_factory=lambda: int(datetime.now().timestamp() * 1000))
    metadata: dict = Field(default_factory=dict)

    class Config:
        use_enum_values = True


class ForwardingStatus(BaseModel):
    """Status of forwarding operations

    Provides high-level view of what's been forwarded and when.
    """

    total_forwarded: int = 0
    by_source_type: dict = Field(default_factory=dict)  # {ExecutionTrace: 25, ...}
    last_forward_time: Optional[int] = None
    pending_forwarding: int = 0


class EventForwarder:
    """Converts AI Coordination events to Memory-MCP format

    Translates:
    - ExecutionTraces → EpisodicEvents (execution type)
    - ThinkingTraces → EpisodicEvents (reasoning type)
    - ActionCycles → EpisodicEvents (action_cycle type)
    - ProjectContext changes → EpisodicEvents (project_context type)

    Maintains audit trail via ForwardingLog.
    """

    def __init__(
        self,
        db: "Database",
        episodic_store: "EpisodicStore",
        forwarding_store: Optional["EventForwarderStore"] = None
    ):
        """Initialize EventForwarder

        Args:
            db: Database connection
            episodic_store: EpisodicStore to write forwarded events
            forwarding_store: Optional ForwardingStore for audit trail
        """
        self.db = db
        self.episodic = episodic_store
        self.forwarding_store = forwarding_store

    def _derive_project_id(self, session_id: str, project_id_str: Optional[str] = None) -> int:
        """Derive an integer project_id from available sources

        Args:
            session_id: Session identifier (str)
            project_id_str: Optional project identifier (str)

        Returns:
            Integer project_id suitable for EpisodicEvent
        """
        if project_id_str:
            # Hash the project_id string to get a stable int
            return abs(hash(project_id_str)) % 1000000
        else:
            # Use session_id to derive a project_id
            return abs(hash(session_id)) % 1000000

    def forward_execution_trace(self, trace) -> str:
        """Convert ExecutionTrace → EpisodicEvent

        Args:
            trace: ExecutionTrace from ActionCycle execution

        Returns:
            episodic_event_id: ID of created EpisodicEvent
        """
        from athena.episodic.models import EpisodicEvent

        # Map outcome (ExecutionOutcome enum values to EventOutcome)
        outcome_map = {
            "success": EventOutcome.SUCCESS,
            "failure": EventOutcome.FAILURE,
            "partial": EventOutcome.PARTIAL,
        }

        # Build metadata using actual ExecutionTrace fields
        trace_id = str(trace.id) if trace.id else f"{trace.session_id}_{int(trace.timestamp.timestamp())}"

        metadata = {
            "trace_id": trace_id,
            "goal_id": trace.goal_id,
            "task_id": trace.task_id,
            "plan_id": trace.plan_id,
            "action_type": trace.action_type,
            "duration_seconds": trace.duration_seconds,
            "code_changes": len(trace.code_changes) if trace.code_changes else 0,
        }

        # Add errors if present
        if trace.errors:
            metadata["error_count"] = len(trace.errors)
            metadata["errors"] = [
                {
                    "error_type": e.error_type,
                    "message": e.message,
                }
                for e in trace.errors
            ]

        # Add lessons if present
        if trace.lessons:
            metadata["lesson_count"] = len(trace.lessons)
            metadata["lessons"] = [
                {
                    "lesson": l.lesson,
                    "confidence": l.confidence,
                }
                for l in trace.lessons
            ]

        # Create episodic event
        event = EpisodicEvent(
            project_id=self._derive_project_id(trace.session_id),
            session_id=trace.session_id,
            event_type=EventType.ACTION,
            content=f"Executed: {trace.action_type} (goal: {trace.goal_id})",
            timestamp=trace.timestamp,
            outcome=outcome_map.get(trace.outcome, EventOutcome.ONGOING),
            learned=trace.description if trace.description else None,
        )

        # Store in episodic layer
        event_id = self.episodic.record_event(event)

        # Log the forwarding
        if self.forwarding_store:
            self.forwarding_store.log_forwarding(
                source_type="ExecutionTrace",
                source_id=trace_id,
                target_type="EpisodicEvent",
                target_id=str(event_id),
                metadata={"goal_id": trace.goal_id, "action_type": trace.action_type},
            )

        return str(event_id)

    def forward_thinking_trace(self, trace) -> str:
        """Convert ThinkingTrace → EpisodicEvent

        Reasoning patterns go to episodic layer (for consolidation)
        but also could go directly to semantic layer (pattern extraction).

        Args:
            trace: ThinkingTrace with reasoning data

        Returns:
            episodic_event_id: ID of created EpisodicEvent
        """
        from athena.episodic.models import EpisodicEvent

        # Build reasoning metadata
        metadata = {
            "trace_id": trace.trace_id,
            "execution_id": trace.execution_id,
            "pattern_type": trace.pattern_type,
            "problem_statement": trace.problem_statement,
            "confidence": trace.confidence,
            "effectiveness_score": trace.effectiveness_score,
            "reasoning_steps": [
                {
                    "step_num": s.step_num,
                    "reasoning": s.reasoning,
                }
                for s in trace.reasoning_steps
            ],
        }

        # Determine session_id from trace or use trace_id
        session_id = getattr(trace, 'session_id', trace.trace_id)

        # Create episodic event
        event = EpisodicEvent(
            project_id=self._derive_project_id(session_id),
            session_id=session_id,
            event_type=EventType.DECISION,
            content=f"Reasoning: {trace.pattern_type}",
            timestamp=trace.timestamp if isinstance(trace.timestamp, datetime) else datetime.fromtimestamp(trace.timestamp),
            outcome=EventOutcome.SUCCESS if trace.effectiveness_score > 0.5 else EventOutcome.PARTIAL,
            learned=trace.problem_statement if trace.problem_statement else None,
        )

        # Store in episodic layer
        event_id = self.episodic.record_event(event)

        # Log the forwarding
        if self.forwarding_store:
            self.forwarding_store.log_forwarding(
                source_type="ThinkingTrace",
                source_id=trace.trace_id,
                target_type="EpisodicEvent",
                target_id=str(event_id),
                metadata={"pattern_type": trace.pattern_type},
            )

        return str(event_id)

    def forward_action_cycle(self, cycle) -> str:
        """Convert ActionCycle → EpisodicEvent

        Args:
            cycle: ActionCycle from orchestration

        Returns:
            episodic_event_id: ID of created EpisodicEvent
        """
        from athena.episodic.models import EpisodicEvent

        # Build metadata
        metadata = {
            "cycle_id": cycle.cycle_id,
            "goal_id": cycle.goal_id,
            "status": cycle.status,
            "attempt_count": cycle.current_attempt,
            "max_attempts": cycle.max_attempts,
        }

        # Add plan steps if present
        if hasattr(cycle, 'plan') and cycle.plan and hasattr(cycle.plan, 'steps') and cycle.plan.steps:
            metadata["plan_steps"] = [
                {
                    "step_num": s.step_num,
                    "description": s.description,
                }
                for s in cycle.plan.steps
            ]

        # Add lessons if present
        if hasattr(cycle, 'lessons_learned') and cycle.lessons_learned:
            metadata["lessons"] = [
                {
                    "lesson_text": l.lesson_text,
                    "importance": l.importance,
                }
                for l in cycle.lessons_learned
            ]

        # Determine session_id from cycle or use goal_id
        session_id = getattr(cycle, 'session_id', cycle.goal_id or "default")

        # Map status to outcome
        status_outcome_map = {
            "completed": EventOutcome.SUCCESS,
            "failed": EventOutcome.FAILURE,
            "partial": EventOutcome.PARTIAL,
            "in_progress": EventOutcome.ONGOING,
        }

        # Create episodic event
        event = EpisodicEvent(
            project_id=self._derive_project_id(session_id),
            session_id=session_id,
            event_type=EventType.ACTION,
            content=f"ActionCycle: {cycle.status} (goal: {cycle.goal_id})",
            timestamp=datetime.now(),
            outcome=status_outcome_map.get(cycle.status, EventOutcome.ONGOING),
        )

        # Store in episodic layer
        event_id = self.episodic.record_event(event)

        # Log the forwarding
        if self.forwarding_store:
            self.forwarding_store.log_forwarding(
                source_type="ActionCycle",
                source_id=str(cycle.cycle_id if cycle.cycle_id else cycle.goal_id),
                target_type="EpisodicEvent",
                target_id=str(event_id),
                metadata={"goal_id": cycle.goal_id, "status": cycle.status},
            )

        return str(event_id)

    def forward_project_context(self, context) -> str:
        """Convert ProjectContext → EpisodicEvent

        Records project state changes as episodic events.

        Args:
            context: ProjectContext with current state

        Returns:
            episodic_event_id: ID of created EpisodicEvent
        """
        from athena.episodic.models import EpisodicEvent

        # Build metadata
        metadata = {
            "project_id": context.project_id,
            "project_name": context.name,
            "current_phase": context.current_phase,
            "current_goal_id": context.current_goal_id,
            "completed_goal_count": context.completed_goal_count,
            "in_progress_goal_count": context.in_progress_goal_count,
            "blocked_goal_count": context.blocked_goal_count,
        }

        # Use project_id as session_id for project context
        session_id = context.project_id

        # Calculate progress percentage based on goal counts
        total_goals = context.completed_goal_count + context.in_progress_goal_count + context.blocked_goal_count
        progress = (context.completed_goal_count / total_goals * 100) if total_goals > 0 else 0

        # Create episodic event
        event = EpisodicEvent(
            project_id=self._derive_project_id(session_id),
            session_id=session_id,
            event_type=EventType.ACTION,
            content=f"Project {context.name}: phase {context.current_phase} ({progress:.0f}% complete)",
            timestamp=datetime.now(),
            outcome=EventOutcome.SUCCESS,  # Project state updates are always recorded
            learned=f"Progress: {progress:.0f}% ({context.completed_goal_count} completed, {context.in_progress_goal_count} in progress, {context.blocked_goal_count} blocked)",
        )

        # Store in episodic layer
        event_id = self.episodic.record_event(event)

        # Log the forwarding
        if self.forwarding_store:
            self.forwarding_store.log_forwarding(
                source_type="ProjectContext",
                source_id=context.project_id,
                target_type="EpisodicEvent",
                target_id=str(event_id),
                metadata={
                    "project_name": context.project_name,
                    "phase": context.current_phase,
                },
            )

        return str(event_id)

    def forward_code_context(self, code_context) -> str:
        """Convert CodeContext → EpisodicEvent

        Records code context changes (files, dependencies, issues).

        Args:
            code_context: CodeContext with task-scoped code info

        Returns:
            episodic_event_id: ID of created EpisodicEvent
        """
        from athena.episodic.models import EpisodicEvent

        # Build metadata with code info
        metadata = {
            "context_id": code_context.context_id,
            "task_id": code_context.task_id,
            "file_count": code_context.file_count,
            "relevant_files": code_context.relevant_files or [],
            "dependency_types": [str(d) for d in code_context.dependency_types] if code_context.dependency_types else [],
        }

        # Use task_id as session_id for code context
        session_id = code_context.task_id or "code_context"

        # Create episodic event
        event = EpisodicEvent(
            project_id=self._derive_project_id(session_id),
            session_id=session_id,
            event_type=EventType.FILE_CHANGE,
            content=f"Code context: {code_context.file_count} files for task {code_context.task_id}",
            timestamp=datetime.now(),
            outcome=EventOutcome.SUCCESS,
            files_changed=code_context.file_count,
        )

        # Store in episodic layer
        event_id = self.episodic.record_event(event)

        # Log the forwarding
        if self.forwarding_store:
            self.forwarding_store.log_forwarding(
                source_type="CodeContext",
                source_id=str(code_context.context_id),
                target_type="EpisodicEvent",
                target_id=str(event_id),
                metadata={"task_id": code_context.task_id, "file_count": code_context.file_count},
            )

        return str(event_id)

    def get_forwarding_status(self) -> Optional[dict]:
        """Get current forwarding status

        Returns:
            Dict with forwarding statistics or None if no store
        """
        if not self.forwarding_store:
            return None

        status = self.forwarding_store.get_forwarding_status()
        return {
            "total_forwarded": status.total_forwarded,
            "by_source_type": status.by_source_type,
            "pending": status.pending_forwarding,
        }
