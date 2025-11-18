"""Hook dispatcher for automatic conversation and session management."""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional
from uuid import uuid4

from ..conversation.auto_recovery import AutoContextRecovery
from ..conversation.context_recovery import ContextSnapshot
from ..conversation.models import Conversation, Message, MessageRole
from ..conversation.store import ConversationStore
from ..core.database import Database
from ..episodic.models import EpisodicEvent, EventContext, EventOutcome, EventType
from ..episodic.store import EpisodicStore
from .lib.cascade_monitor import CascadeMonitor
from .lib.idempotency_tracker import IdempotencyTracker
from .lib.rate_limiter import RateLimiter

if TYPE_CHECKING:
    from ..session.context_manager import SessionContextManager


class HookDispatcher:
    """Dispatches hooks for automatic context and conversation management.

    Features:
    - Session and conversation lifecycle tracking
    - Automatic episodic event recording
    - Duplicate prevention via IdempotencyTracker
    - Execution rate limiting via RateLimiter
    - Hook cycle detection via CascadeMonitor
    """

    def __init__(
        self,
        db: Database,
        project_id: int = 1,
        enable_safety: bool = True,
        session_manager: Optional["SessionContextManager"] = None,
    ):
        """Initialize hook dispatcher.

        Args:
            db: Database instance
            project_id: Project ID for memory isolation
            enable_safety: Enable safety utilities (idempotency, rate limiting, cascade detection)
            session_manager: Optional SessionContextManager for session context tracking
        """
        self.db = db
        self.project_id = project_id
        self.episodic_store = EpisodicStore(db)
        self.conversation_store = ConversationStore(db)
        self.context_snapshot = ContextSnapshot(db, project_id)
        self.auto_recovery = AutoContextRecovery(db, project_id)
        self.enable_safety = enable_safety
        self.session_manager = session_manager

        # Active session tracking
        self._active_session_id: Optional[str] = None
        self._active_conversation_id: Optional[int] = None
        self._turn_count = 0
        self._last_recovery_context: Optional[dict] = None  # For context recovery access

        # Safety utilities
        self.idempotency_tracker = IdempotencyTracker()
        self.rate_limiter = RateLimiter()
        self.cascade_monitor = CascadeMonitor()

        # Hook registry for introspection
        self._hook_registry: Dict[str, Dict[str, Any]] = {
            "session_start": {"enabled": True, "execution_count": 0, "last_error": None},
            "session_end": {"enabled": True, "execution_count": 0, "last_error": None},
            "conversation_turn": {"enabled": True, "execution_count": 0, "last_error": None},
            "user_prompt_submit": {"enabled": True, "execution_count": 0, "last_error": None},
            "assistant_response": {"enabled": True, "execution_count": 0, "last_error": None},
            "task_started": {"enabled": True, "execution_count": 0, "last_error": None},
            "task_completed": {"enabled": True, "execution_count": 0, "last_error": None},
            "error_occurred": {"enabled": True, "execution_count": 0, "last_error": None},
            "pre_tool_use": {"enabled": True, "execution_count": 0, "last_error": None},
            "post_tool_use": {"enabled": True, "execution_count": 0, "last_error": None},
            "consolidation_start": {"enabled": True, "execution_count": 0, "last_error": None},
            "consolidation_complete": {"enabled": True, "execution_count": 0, "last_error": None},
            "pre_clear": {"enabled": True, "execution_count": 0, "last_error": None},
        }

    def _execute_with_safety(
        self, hook_id: str, context: Dict[str, Any], func: Callable[[], Any]
    ) -> Any:
        """Execute a hook with safety utilities enabled.

        Applies three safety mechanisms:
        1. Idempotency check - prevents duplicate executions (returns cached result)
        2. Rate limiting - prevents execution storms
        3. Cascade monitoring - prevents cycles and deep nesting

        Args:
            hook_id: Identifier for the hook
            context: Context dict for idempotency fingerprinting
            func: Callable to execute

        Returns:
            Result from func, or cached result if duplicate

        Raises:
            RuntimeError: If rate limit or cascade check fails
            Propagates exceptions from func (after safety cleanup)
        """
        if not self.enable_safety:
            return func()

        # 1. Check for duplicate execution (idempotency)
        # If duplicate, return cached result silently
        if self.idempotency_tracker.is_duplicate(hook_id, context):
            last_exec = self.idempotency_tracker.get_last_execution(hook_id)
            if last_exec:
                return last_exec.result  # Return the cached result
            # If no cached result, continue with execution

        # 2. Check rate limit (fail if exceeded)
        if not self.rate_limiter.allow_execution(hook_id):
            wait_time = self.rate_limiter.get_estimated_wait_time(hook_id)
            raise RuntimeError(f"Hook {hook_id} rate limited. Wait {wait_time:.2f}s before retry.")

        # 3. Check for cascade (cycles, depth, breadth)
        try:
            self.cascade_monitor.push_hook(hook_id)
        except ValueError as e:
            raise RuntimeError(f"Hook cascade limit exceeded: {str(e)}")

        try:
            # Execute the hook function
            result = func()

            # Record successful execution
            self.idempotency_tracker.record_execution(hook_id, context, result)
            self._hook_registry[hook_id]["execution_count"] += 1

            return result
        except Exception as e:
            # Record error
            self._hook_registry[hook_id]["last_error"] = str(e)
            raise
        finally:
            # Always pop from cascade stack
            self.cascade_monitor.pop_hook()

    def fire_session_start(
        self, session_id: Optional[str] = None, context: Optional[dict] = None
    ) -> str:
        """Called when session starts.

        Args:
            session_id: Optional session ID (auto-generated if not provided)
            context: Optional context dict (task, phase, etc)

        Returns:
            Session ID
        """

        def _execute():
            nonlocal session_id
            if not session_id:
                session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}"

            # Create session in conversation store
            self.conversation_store.create_session(session_id, self.project_id)
            self._active_session_id = session_id
            self._turn_count = 0

            # Auto-start session context if available
            if self.session_manager:
                try:
                    task = context.get("task") if context else None
                    phase = context.get("phase") if context else None
                    self.session_manager.start_session(
                        session_id=session_id, project_id=self.project_id, task=task, phase=phase
                    )
                except Exception as e:
                    # Gracefully degrade if session_manager fails
                    # Don't let session manager errors break the hook
                    self._hook_registry["session_start"][
                        "last_error"
                    ] = f"session_manager: {str(e)}"

            # Record episodic event
            context_obj = EventContext()
            if context:
                context_obj.task = context.get("task")
                context_obj.phase = context.get("phase")

            event = EpisodicEvent(
                project_id=self.project_id,
                session_id=session_id,
                event_type=EventType.ACTION,
                content=f"Session started: {session_id}",
                outcome=EventOutcome.SUCCESS,
                context=context_obj,
                learned="Session lifecycle event",
                confidence=1.0,
            )

            self.episodic_store.record_event(event)

            return session_id

        # For auto-generated sessions, add a nonce to make each call unique
        exec_context = {"session_id": session_id, "context": context}
        if session_id is None:
            exec_context["nonce"] = uuid4().hex  # Unique per call

        return self._execute_with_safety("session_start", exec_context, _execute)

    def fire_session_end(self, session_id: Optional[str] = None) -> bool:
        """Called when session ends.

        Args:
            session_id: Session ID to end (uses active if not provided)

        Returns:
            True if session ended successfully
        """

        def _execute():
            end_session_id = session_id or self._active_session_id
            if not end_session_id:
                return False

            # End session in session manager if available
            if self.session_manager:
                try:
                    self.session_manager.end_session(end_session_id)
                except Exception as e:
                    # Gracefully degrade if session_manager fails
                    self._hook_registry["session_end"]["last_error"] = f"session_manager: {str(e)}"

            # End session in conversation store
            self.conversation_store.end_session(end_session_id)

            # Record episodic event
            event = EpisodicEvent(
                project_id=self.project_id,
                session_id=end_session_id,
                event_type=EventType.ACTION,
                content=f"Session ended: {end_session_id}",
                outcome=EventOutcome.SUCCESS,
                learned="Session lifecycle event",
                confidence=1.0,
            )

            self.episodic_store.record_event(event)

            # Clear active session
            if end_session_id == self._active_session_id:
                self._active_session_id = None
                self._active_conversation_id = None
                self._turn_count = 0

            return True

        return self._execute_with_safety("session_end", {"session_id": session_id}, _execute)

    def fire_conversation_turn(
        self,
        user_content: str,
        assistant_content: str,
        duration_ms: int = 0,
        user_tokens: int = 0,
        assistant_tokens: int = 0,
        task: Optional[str] = None,
        phase: Optional[str] = None,
    ) -> int:
        """Called after each user-assistant exchange.

        Args:
            user_content: User message content
            assistant_content: Assistant message content
            duration_ms: Duration of exchange in milliseconds
            user_tokens: Tokens in user message (estimated)
            assistant_tokens: Tokens in assistant message (estimated)
            task: Current task description
            phase: Current execution phase

        Returns:
            Turn ID
        """

        def _execute():
            if not self._active_session_id:
                # Auto-start session if not active
                self.fire_session_start()

            # Create conversation if needed
            if not self._active_conversation_id:
                self._active_conversation_id = self._create_conversation()

            self._turn_count += 1

            # Create messages
            user_msg = Message(
                role=MessageRole.USER,
                content=user_content,
                tokens_estimate=user_tokens,
            )
            asst_msg = Message(
                role=MessageRole.ASSISTANT,
                content=assistant_content,
                tokens_estimate=assistant_tokens,
            )

            # Add turn to conversation
            turn_id = self.conversation_store.add_turn(
                self._active_conversation_id,
                self._turn_count,
                user_msg,
                asst_msg,
                duration_ms=duration_ms,
            )

            # Record conversation turn to session context if available
            if self.session_manager:
                try:
                    event_data = {
                        "turn_number": self._turn_count,
                        "user_tokens": user_tokens,
                        "assistant_tokens": assistant_tokens,
                        "duration_ms": duration_ms,
                        "task": task,
                        "phase": phase,
                    }
                    self.session_manager.record_event(
                        session_id=self._active_session_id,
                        event_type="conversation_turn",
                        event_data=event_data,
                    )
                except Exception as e:
                    # Gracefully degrade if session_manager fails
                    self._hook_registry["conversation_turn"][
                        "last_error"
                    ] = f"session_manager: {str(e)}"

            # Record episodic event (conversation exchange)
            context_obj = EventContext(task=task, phase=phase)

            event_content = (
                f"Turn {self._turn_count}\n"
                f"User: {user_content[:100]}...\n"
                f"Assistant: {assistant_content[:100]}..."
            )

            event = EpisodicEvent(
                project_id=self.project_id,
                session_id=self._active_session_id,
                event_type=EventType.CONVERSATION,
                content=event_content,
                outcome=EventOutcome.SUCCESS,
                context=context_obj,
                duration_ms=duration_ms,
                learned=f"Conversation turn {self._turn_count}",
                confidence=1.0,
            )

            self.episodic_store.record_event(event)

            return turn_id

        context = {
            "user_content_hash": hash(user_content),
            "assistant_content_hash": hash(assistant_content),
            "task": task,
            "phase": phase,
        }

        return self._execute_with_safety("conversation_turn", context, _execute)

    def fire_user_prompt_submit(
        self, prompt: str, task: Optional[str] = None, phase: Optional[str] = None
    ) -> int:
        """Called when user submits a prompt.

        Automatically detects context recovery requests and synthesizes
        context from episodic memory (e.g., "What were we working on?")

        Args:
            prompt: User prompt content
            task: Current task
            phase: Current phase

        Returns:
            Event ID. Access recovery context via get_last_recovery_context()
        """
        # Check for context recovery request FIRST
        self._last_recovery_context = self.check_context_recovery_request(prompt)

        def _execute():
            if not self._active_session_id:
                self.fire_session_start()

            context_obj = EventContext(task=task, phase=phase)

            event = EpisodicEvent(
                project_id=self.project_id,
                session_id=self._active_session_id,
                event_type=EventType.CONVERSATION,
                content=f"User prompt: {prompt[:200]}...",
                outcome=EventOutcome.SUCCESS,
                context=context_obj,
                learned="User input event",
                confidence=1.0,
            )

            return self.episodic_store.record_event(event)

        context = {"prompt_hash": hash(prompt), "task": task, "phase": phase}

        return self._execute_with_safety("user_prompt_submit", context, _execute)

    def check_context_recovery_request(self, prompt: str) -> Optional[dict]:
        """Check if user prompt is asking for context recovery.

        If recovery is needed, automatically synthesizes and returns context
        from episodic memory.

        Args:
            prompt: User prompt to check

        Returns:
            Context dict if recovery was triggered, None otherwise
        """
        if not self.auto_recovery.should_trigger_recovery(prompt):
            return None

        # User is asking for context recovery - synthesize it
        recovery_context = self.auto_recovery.auto_recover_context()

        # Also record this as a recovery event
        if recovery_context.get("status") == "recovered":
            event = EpisodicEvent(
                project_id=self.project_id,
                session_id=recovery_context.get("session_id", self._active_session_id),
                event_type=EventType.ACTION,
                content=f"Context recovery triggered: {recovery_context.get('active_work', 'unknown task')}",
                outcome=EventOutcome.SUCCESS,
                context=EventContext(
                    phase=recovery_context.get("current_phase", "context_recovery")
                ),
                learned="Context recovery from episodic memory",
                confidence=1.0,
            )

            self.episodic_store.record_event(event)

        return recovery_context

    def fire_assistant_response(
        self, response: str, task: Optional[str] = None, phase: Optional[str] = None
    ) -> int:
        """Called when assistant generates a response.

        Args:
            response: Assistant response content
            task: Current task
            phase: Current phase

        Returns:
            Event ID
        """

        def _execute():
            if not self._active_session_id:
                self.fire_session_start()

            context_obj = EventContext(task=task, phase=phase)

            event = EpisodicEvent(
                project_id=self.project_id,
                session_id=self._active_session_id,
                event_type=EventType.CONVERSATION,
                content=f"Assistant response: {response[:200]}...",
                outcome=EventOutcome.SUCCESS,
                context=context_obj,
                learned="Assistant output event",
                confidence=1.0,
            )

            return self.episodic_store.record_event(event)

        context = {"response_hash": hash(response), "task": task, "phase": phase}

        return self._execute_with_safety("assistant_response", context, _execute)

    def fire_task_started(
        self, task_id: str, task_description: str, goal: Optional[str] = None
    ) -> int:
        """Called when task starts.

        Args:
            task_id: Task identifier
            task_description: Task description
            goal: Optional goal description

        Returns:
            Event ID
        """

        def _execute():
            if not self._active_session_id:
                self.fire_session_start()

            event = EpisodicEvent(
                project_id=self.project_id,
                session_id=self._active_session_id,
                event_type=EventType.ACTION,
                content=f"Task started: {task_description}",
                outcome=EventOutcome.ONGOING,
                context=EventContext(task=task_description, phase="task_execution"),
                learned=f"Started task: {task_id}",
                confidence=1.0,
            )

            return self.episodic_store.record_event(event)

        context = {"task_id": task_id, "task_description": task_description, "goal": goal}

        return self._execute_with_safety("task_started", context, _execute)

    def fire_task_completed(
        self,
        task_id: str,
        outcome: EventOutcome,
        summary: Optional[str] = None,
    ) -> int:
        """Called when task completes.

        Args:
            task_id: Task identifier
            outcome: Task outcome (success, failure, partial)
            summary: Optional summary of what was accomplished

        Returns:
            Event ID
        """

        def _execute():
            if not self._active_session_id:
                self.fire_session_start()

            content = f"Task completed: {task_id}"
            if summary:
                content += f"\n{summary}"

            event = EpisodicEvent(
                project_id=self.project_id,
                session_id=self._active_session_id,
                event_type=(
                    EventType.SUCCESS if outcome == EventOutcome.SUCCESS else EventType.ERROR
                ),
                content=content,
                outcome=outcome,
                context=EventContext(phase="task_completion"),
                learned=f"Completed task {task_id}: {outcome.value}",
                confidence=1.0,
            )

            return self.episodic_store.record_event(event)

        context = {"task_id": task_id, "outcome": outcome.value, "summary": summary}

        return self._execute_with_safety("task_completed", context, _execute)

    def fire_error_occurred(
        self, error_type: str, error_message: str, context_str: Optional[str] = None
    ) -> int:
        """Called when an error occurs.

        Args:
            error_type: Type of error
            error_message: Error message
            context_str: Optional context about the error

        Returns:
            Event ID
        """

        def _execute():
            if not self._active_session_id:
                self.fire_session_start()

            content = f"Error [{error_type}]: {error_message}"
            if context_str:
                content += f"\nContext: {context_str}"

            event = EpisodicEvent(
                project_id=self.project_id,
                session_id=self._active_session_id,
                event_type=EventType.ERROR,
                content=content,
                outcome=EventOutcome.FAILURE,
                learned=f"Error occurred: {error_type}",
                confidence=1.0,
            )

            return self.episodic_store.record_event(event)

        context = {"error_type": error_type, "error_message": error_message, "context": context_str}

        return self._execute_with_safety("error_occurred", context, _execute)

    def fire_pre_tool_use(
        self, tool_name: str, tool_params: Dict[str, Any], task: Optional[str] = None
    ) -> int:
        """Called before a tool is executed.

        Args:
            tool_name: Name of tool being invoked
            tool_params: Parameters passed to tool
            task: Current task context

        Returns:
            Event ID
        """

        def _execute():
            if not self._active_session_id:
                self.fire_session_start()

            event = EpisodicEvent(
                project_id=self.project_id,
                session_id=self._active_session_id,
                event_type=EventType.ACTION,
                content=f"Tool invoked: {tool_name}",
                outcome=EventOutcome.ONGOING,
                context=EventContext(task=task, phase="tool_execution"),
                learned=f"Executed tool: {tool_name}",
                confidence=0.9,
            )

            return self.episodic_store.record_event(event)

        context = {"tool_name": tool_name, "tool_params_hash": hash(str(tool_params)), "task": task}

        return self._execute_with_safety("pre_tool_use", context, _execute)

    def fire_post_tool_use(
        self,
        tool_name: str,
        tool_params: Dict[str, Any],
        result: Any,
        success: bool = True,
        error: Optional[str] = None,
        task: Optional[str] = None,
    ) -> int:
        """Called after a tool executes.

        Args:
            tool_name: Name of tool that executed
            tool_params: Parameters passed to tool
            result: Result returned from tool
            success: Whether execution was successful
            error: Error message if execution failed
            task: Current task context

        Returns:
            Event ID
        """

        def _execute():
            if not self._active_session_id:
                self.fire_session_start()

            outcome = EventOutcome.SUCCESS if success else EventOutcome.FAILURE
            event_type = EventType.SUCCESS if success else EventType.ERROR

            content = f"Tool completed: {tool_name}\n"
            if error:
                content += f"Error: {error}\n"
            if isinstance(result, (dict, list)):
                content += f"Result keys: {list(result.keys()) if isinstance(result, dict) else len(result)} items"

            event = EpisodicEvent(
                project_id=self.project_id,
                session_id=self._active_session_id,
                event_type=event_type,
                content=content,
                outcome=outcome,
                context=EventContext(task=task, phase="tool_completion"),
                learned=f"Tool execution {'succeeded' if success else 'failed'}: {tool_name}",
                confidence=0.9,
            )

            return self.episodic_store.record_event(event)

        context = {
            "tool_name": tool_name,
            "tool_params_hash": hash(str(tool_params)),
            "success": success,
            "task": task,
        }

        return self._execute_with_safety("post_tool_use", context, _execute)

    def fire_consolidation_start(self, event_count: int, phase: str = "consolidation") -> int:
        """Called when consolidation (sleep-like pattern extraction) starts.

        Args:
            event_count: Number of episodic events to consolidate
            phase: Current phase

        Returns:
            Event ID
        """

        def _execute():
            if not self._active_session_id:
                self.fire_session_start()

            event = EpisodicEvent(
                project_id=self.project_id,
                session_id=self._active_session_id,
                event_type=EventType.ACTION,
                content=f"Consolidation started: processing {event_count} episodic events",
                outcome=EventOutcome.ONGOING,
                context=EventContext(phase=phase),
                learned=f"Started consolidation cycle with {event_count} events",
                confidence=1.0,
            )

            return self.episodic_store.record_event(event)

        context = {"event_count": event_count, "phase": phase}

        return self._execute_with_safety("consolidation_start", context, _execute)

    def fire_consolidation_complete(
        self, patterns_found: int, consolidation_time_ms: int = 0, quality_score: float = 0.0
    ) -> int:
        """Called when consolidation completes.

        Args:
            patterns_found: Number of patterns extracted
            consolidation_time_ms: Time taken to consolidate in milliseconds
            quality_score: Quality score of consolidation (0.0-1.0)

        Returns:
            Event ID
        """

        def _execute():
            if not self._active_session_id:
                self.fire_session_start()

            # Record consolidation to session manager if available
            if self.session_manager:
                try:
                    self.session_manager.record_consolidation(
                        project_id=self.project_id,
                        consolidation_type="SEMANTIC_SYNTHESIS",
                        wm_size=patterns_found,
                        trigger_type="PERIODIC",
                    )
                except Exception as e:
                    # Gracefully degrade if session_manager fails
                    self._hook_registry["consolidation_complete"][
                        "last_error"
                    ] = f"session_manager: {str(e)}"

            event = EpisodicEvent(
                project_id=self.project_id,
                session_id=self._active_session_id,
                event_type=EventType.SUCCESS,
                content=f"Consolidation completed: extracted {patterns_found} patterns\n"
                f"Time: {consolidation_time_ms}ms\nQuality: {quality_score:.2%}",
                outcome=EventOutcome.SUCCESS,
                context=EventContext(phase="consolidation_complete"),
                learned=f"Consolidation extracted {patterns_found} patterns (quality: {quality_score:.2%})",
                confidence=1.0,
                duration_ms=consolidation_time_ms,
            )

            return self.episodic_store.record_event(event)

        context = {
            "patterns_found": patterns_found,
            "consolidation_time_ms": consolidation_time_ms,
            "quality_score": quality_score,
        }

        return self._execute_with_safety("consolidation_complete", context, _execute)

    def snapshot_conversation_for_recovery(self, session_id: Optional[str] = None) -> int:
        """Snapshot current conversation for recovery after /clear.

        Args:
            session_id: Session ID (uses active if not provided)

        Returns:
            Event ID of snapshot
        """
        session_id = session_id or self._active_session_id
        if not session_id:
            return -1

        # Get current conversation
        if self._active_conversation_id:
            conv = self.conversation_store.get_conversation(self._active_conversation_id)
            if conv:
                # Format conversation for display
                content_lines = []
                for turn in conv.turns:
                    content_lines.append(
                        f"Turn {turn.turn_number}:\n"
                        f"  User: {turn.user_message.content[:100]}\n"
                        f"  Assistant: {turn.assistant_message.content[:100]}"
                    )

                conversation_text = "\n\n".join(content_lines)

                return self.context_snapshot.snapshot_conversation(
                    session_id=session_id,
                    conversation_content=conversation_text,
                    task=conv.title,
                )

        return -1

    def dispatch_pre_clear_hook(self, component: str = "all") -> None:
        """Dispatch pre-clear hook to snapshot conversation before clearing.

        This hook ensures conversation context is saved to episodic memory
        before the working memory is cleared. Called BEFORE the actual clear.

        Args:
            component: Component being cleared (all, phonological, visuospatial, episodic_buffer)
        """
        try:
            # Snapshot current conversation for recovery
            event_id = self.snapshot_conversation_for_recovery()

            # Dispatch hook with component info
            context = {
                "hook_id": "pre_clear",
                "component": component,
                "snapshot_event_id": event_id,
                "timestamp": int(datetime.now().timestamp()),
            }

            def hook_func():
                # Record the pre-clear event in episodic memory
                self.episodic_store.create_event(
                    content=f"Pre-clear hook triggered for component: {component}",
                    event_type="action",
                    outcome="success",
                    context={
                        "phase": "memory_management",
                        "action": "pre_clear_snapshot",
                        "component": component,
                    },
                )
                return {"saved_snapshot_id": event_id}

            # Execute with safety utilities
            self._execute_with_safety("pre_clear", context, hook_func)

        except Exception as e:
            logger.warning(f"Error in pre_clear hook: {e}")
            self._hook_registry["pre_clear"]["last_error"] = str(e)

    def get_session_state(self, session_id: Optional[str] = None) -> dict:
        """Get current state of a session.

        Args:
            session_id: Session ID (uses active if not provided)

        Returns:
            Session state dict
        """
        session_id = session_id or self._active_session_id
        if not session_id:
            return {}

        # Get conversations in session
        conversations = self.conversation_store.get_session_conversations(session_id)

        return {
            "session_id": session_id,
            "is_active": session_id == self._active_session_id,
            "conversation_count": len(conversations),
            "active_conversation_id": self._active_conversation_id,
            "turn_count": self._turn_count,
            "conversations": conversations,
        }

    def _create_conversation(self) -> int:
        """Create a new conversation in active session.

        Returns:
            Conversation ID
        """
        if not self._active_session_id:
            return -1

        thread_id = f"thread_{uuid4().hex[:16]}"
        conv = Conversation(
            project_id=self.project_id,
            session_id=self._active_session_id,
            thread_id=thread_id,
            title=f"Conversation {self._turn_count + 1}",
        )

        return self.conversation_store.create_conversation(conv)

    # Hook Registry & Introspection Methods

    def get_hook_registry(self) -> Dict[str, Dict[str, Any]]:
        """Get the complete hook registry.

        Returns:
            Dict mapping hook IDs to their metadata
        """
        return self._hook_registry.copy()

    def get_hook_stats(self, hook_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a specific hook.

        Args:
            hook_id: Hook identifier

        Returns:
            Hook statistics dict, or None if hook not found
        """
        if hook_id not in self._hook_registry:
            return None

        last_exec = self.idempotency_tracker.get_last_execution(hook_id)
        idempotency_count = 1 if last_exec else 0

        return {
            "hook_id": hook_id,
            "enabled": self._hook_registry[hook_id]["enabled"],
            "execution_count": self._hook_registry[hook_id]["execution_count"],
            "last_error": self._hook_registry[hook_id]["last_error"],
            "idempotency_count": idempotency_count,
            "rate_limit_status": {
                "is_allowed": self.rate_limiter.allow_execution(hook_id),
                "estimated_wait": self.rate_limiter.get_estimated_wait_time(hook_id),
            },
        }

    def get_all_hook_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all hooks.

        Returns:
            Dict mapping hook IDs to their statistics
        """
        stats = {}
        for hook_id in self._hook_registry:
            hook_stats = self.get_hook_stats(hook_id)
            if hook_stats:
                stats[hook_id] = hook_stats

        return stats

    def is_hook_enabled(self, hook_id: str) -> bool:
        """Check if a hook is enabled.

        Args:
            hook_id: Hook identifier

        Returns:
            True if hook is enabled, False otherwise
        """
        if hook_id not in self._hook_registry:
            return False

        return self._hook_registry[hook_id]["enabled"]

    def enable_hook(self, hook_id: str) -> bool:
        """Enable a specific hook.

        Args:
            hook_id: Hook identifier

        Returns:
            True if hook was enabled, False if not found
        """
        if hook_id not in self._hook_registry:
            return False

        self._hook_registry[hook_id]["enabled"] = True
        return True

    def disable_hook(self, hook_id: str) -> bool:
        """Disable a specific hook.

        Args:
            hook_id: Hook identifier

        Returns:
            True if hook was disabled, False if not found
        """
        if hook_id not in self._hook_registry:
            return False

        self._hook_registry[hook_id]["enabled"] = False
        return True

    def reset_hook_stats(self, hook_id: Optional[str] = None) -> None:
        """Reset statistics for one or all hooks.

        Args:
            hook_id: Specific hook to reset, or None to reset all
        """
        if hook_id:
            if hook_id in self._hook_registry:
                self._hook_registry[hook_id]["execution_count"] = 0
                self._hook_registry[hook_id]["last_error"] = None
        else:
            for hook_id in self._hook_registry:
                self._hook_registry[hook_id]["execution_count"] = 0
                self._hook_registry[hook_id]["last_error"] = None

    def get_safety_stats(self) -> Dict[str, Any]:
        """Get statistics from all safety utilities.

        Returns:
            Combined statistics from idempotency, rate limit, and cascade monitors
        """
        return {
            "idempotency": self.idempotency_tracker.get_stats(),
            "rate_limit": self.rate_limiter.get_stats(),
            "cascade": self.cascade_monitor.get_stats(),
        }

    def reset_session(self) -> None:
        """Reset active session tracking."""
        self._active_session_id = None
        self._active_conversation_id = None
        self._turn_count = 0

    def get_active_session_id(self) -> Optional[str]:
        """Get active session ID.

        Returns:
            Session ID or None
        """
        return self._active_session_id

    def get_last_recovery_context(self) -> Optional[dict]:
        """Get the last context recovery result from user_prompt_submit.

        This is populated when fire_user_prompt_submit() detects a context
        recovery request pattern (e.g., "What were we working on?")

        Returns:
            Recovery context dict if recovery was triggered, None otherwise
        """
        return self._last_recovery_context
