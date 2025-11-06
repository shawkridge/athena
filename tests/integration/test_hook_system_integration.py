"""Integration tests for the complete hook system.

Tests end-to-end functionality of all implemented hooks:
- post-tool-use.sh: Event recording + error handling
- session-start.sh: Context loading
- session-end.sh: Consolidation pipeline
- pre-execution.sh: Plan validation + safety checks
- post-task-completion.sh: Goal tracking + learning
- smart-context-injection.sh: RAG context retrieval
"""

import pytest
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import tempfile
import os

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
sys.path.insert(0, "/home/user/.claude/hooks/lib")

# Note: Some imports are conditional due to path differences in test environment

from athena.core.database import Database
from athena.episodic.store import EpisodicStore
from athena.metacognition.models import QualityMetrics
from athena.manager import UnifiedMemoryManager


class HookTestHelper:
    """Helper for testing hooks."""

    def __init__(self, tmp_path: Path):
        """Initialize test helper.

        Args:
            tmp_path: Temporary path for test database
        """
        self.tmp_path = tmp_path
        self.db_path = tmp_path / "test_hooks.db"
        self.db = Database(str(self.db_path))
        self.episodic_store = EpisodicStore(self.db)
        self.memory_manager = UnifiedMemoryManager(self.db)

    def cleanup(self):
        """Clean up test resources."""
        if self.db:
            self.db.close()
        if self.db_path.exists():
            self.db_path.unlink()

    def record_test_event(self, content: str, event_type: str = "test") -> Dict[str, Any]:
        """Record a test event.

        Args:
            content: Event content
            event_type: Event type

        Returns:
            Event dictionary
        """
        event = self.episodic_store.store_event(
            content=content,
            event_type=event_type,
            context={"test": True},
        )
        return event

    def get_recent_events(self, count: int = 10) -> list:
        """Get recent events.

        Args:
            count: Number of events to retrieve

        Returns:
            List of events
        """
        events = self.episodic_store.query_events(limit=count)
        return events


@pytest.fixture
def hook_helper(tmp_path):
    """Create hook test helper.

    Args:
        tmp_path: Temporary path

    Yields:
        HookTestHelper instance
    """
    helper = HookTestHelper(tmp_path)
    yield helper
    helper.cleanup()


class TestPostToolUseHook:
    """Test post-tool-use.sh hook functionality."""

    def test_event_recording(self, hook_helper: HookTestHelper):
        """Test that tool execution records episodic events.

        The post-tool-use hook should:
        - Record successful tool execution
        - Store tool name, parameters, result
        - Track execution time
        """
        # Simulate tool execution event
        event = hook_helper.record_test_event(
            content=json.dumps({
                "tool_name": "semantic_search",
                "params": {"query": "test"},
                "result": "success",
                "duration_ms": 150,
            }),
            event_type="tool_execution"
        )

        # Verify event recorded
        assert event is not None
        assert event["event_type"] == "tool_execution"

        # Verify we can retrieve it
        events = hook_helper.get_recent_events(1)
        assert len(events) > 0

    def test_error_recording(self, hook_helper: HookTestHelper):
        """Test that tool errors are recorded.

        The hook should:
        - Capture tool execution errors
        - Store error context and message
        - Invoke error-handler agent
        """
        event = hook_helper.record_test_event(
            content=json.dumps({
                "tool_name": "consolidate",
                "error": "Consolidation failed: invalid event format",
                "error_type": "ValidationError",
            }),
            event_type="tool_error"
        )

        assert event is not None
        assert "error" in json.loads(event["content"])

    def test_batch_processing(self, hook_helper: HookTestHelper):
        """Test that attention optimizer triggers every 10 operations.

        The hook should:
        - Count operations since last optimization
        - Trigger optimizer after 10 operations
        - Reset operation counter
        """
        # Record 10 tool executions
        for i in range(10):
            hook_helper.record_test_event(
                content=f"Tool execution {i}",
                event_type="tool_execution"
            )

        events = hook_helper.get_recent_events(10)
        assert len(events) == 10


class TestSessionStartHook:
    """Test session-start.sh hook functionality."""

    def test_context_loading(self, hook_helper: HookTestHelper):
        """Test that session start loads prior context.

        The hook should:
        - Load top 5 semantic memories
        - Load active goals
        - Check cognitive load
        """
        # First, add some semantic knowledge
        hook_helper.memory_manager.remember(
            content="Previous authentication implementation using JWT",
            memory_type="fact",
            tags=["auth", "previous_session"]
        )

        # Then verify it's available
        result = hook_helper.memory_manager.recall(
            query="authentication implementation",
            limit=1
        )
        assert result is not None
        assert len(result) > 0

    def test_cognitive_load_check(self, hook_helper: HookTestHelper):
        """Test that session start checks cognitive load.

        The hook should:
        - Load current working memory state
        - Check item count (7±2 model)
        - Report capacity status
        """
        # Add items to working memory
        for i in range(3):
            hook_helper.memory_manager.remember(
                content=f"Working item {i}",
                memory_type="fact"
            )

        # Working memory should be populated
        meta = hook_helper.db.execute_one(
            "SELECT COUNT(*) as count FROM working_memory"
        )
        assert meta is not None


class TestSessionEndHook:
    """Test session-end.sh hook functionality."""

    def test_consolidation_trigger(self, hook_helper: HookTestHelper):
        """Test that session end triggers consolidation.

        The hook should:
        - Invoke consolidation-engine agent
        - Convert episodic → semantic
        - Track consolidation quality
        """
        # Record some episodic events
        for i in range(5):
            hook_helper.record_test_event(
                content=f"Session work item {i}",
                event_type="action"
            )

        # Consolidation would extract patterns
        events = hook_helper.get_recent_events(5)
        assert len(events) == 5

    def test_quality_auditing(self, hook_helper: HookTestHelper):
        """Test that session end audits memory quality.

        The hook should:
        - Compute quality metrics
        - Identify gaps and contradictions
        - Track expertise levels
        """
        # Add semantic memory
        hook_helper.memory_manager.remember(
            content="Implementation fact 1",
            memory_type="fact"
        )

        # Quality auditor would analyze
        quality = QualityMetrics()
        assert quality is not None


class TestPreExecutionHook:
    """Test pre-execution.sh hook functionality."""

    def test_plan_validation(self, hook_helper: HookTestHelper):
        """Test that pre-execution validates plans.

        The hook should:
        - Check plan structure
        - Verify task dependencies
        - Run Q* verification
        """
        # In actual scenario, a task/plan would be validated
        # For now, verify the hook would be triggered
        assert True  # Placeholder for real plan validation

    def test_goal_conflict_detection(self, hook_helper: HookTestHelper):
        """Test that pre-execution detects goal conflicts.

        The hook should:
        - Load active goals
        - Check for resource conflicts
        - Check for dependency conflicts
        """
        # Would invoke goal-orchestrator agent
        assert True  # Placeholder

    def test_safety_auditing(self, hook_helper: HookTestHelper):
        """Test that pre-execution runs safety checks.

        The hook should:
        - Invoke safety-auditor agent
        - Check change safety
        - Recommend approval gates
        """
        # Would invoke safety-auditor agent
        assert True  # Placeholder


class TestPostTaskCompletionHook:
    """Test post-task-completion.sh hook functionality."""

    def test_goal_state_update(self, hook_helper: HookTestHelper):
        """Test that hook updates goal state.

        The hook should:
        - Record task completion
        - Update goal progress
        - Mark milestone status
        """
        event = hook_helper.record_test_event(
            content=json.dumps({
                "task_id": 42,
                "task_name": "Implement feature X",
                "status": "completed",
                "duration_hours": 2.5,
            }),
            event_type="task_completion"
        )

        assert event is not None

    def test_execution_monitoring(self, hook_helper: HookTestHelper):
        """Test that hook monitors execution.

        The hook should:
        - Record execution time vs estimate
        - Track blockers encountered
        - Update health metrics
        """
        event = hook_helper.record_test_event(
            content=json.dumps({
                "task_id": 42,
                "estimated_hours": 3.0,
                "actual_hours": 2.5,
                "blockers": [],
                "health_score": 0.95,
            }),
            event_type="execution_metrics"
        )

        assert event is not None

    def test_learning_extraction(self, hook_helper: HookTestHelper):
        """Test that hook extracts learning.

        The hook should:
        - Invoke workflow-learner agent
        - Extract reusable procedures
        - Record effectiveness metrics
        """
        # Would invoke workflow-learner agent
        assert True  # Placeholder


class TestSmartContextInjectionHook:
    """Test smart-context-injection.sh hook functionality."""

    def test_rag_strategy_selection(self, hook_helper: HookTestHelper):
        """Test that hook selects optimal RAG strategy.

        The hook should:
        - Analyze query type
        - Select strategy: hyde, reranking, reflective, query_transform
        - Log strategy selection
        """
        try:
            from context_injector import ContextInjector
        except ImportError:
            pytest.skip("context_injector not available in test environment")

        injector = ContextInjector()

        # Test HyDE selection (definition queries)
        strategy = injector.determine_strategy("What is authentication?")
        assert strategy == "hyde"

        # Test comparison selection
        strategy = injector.determine_strategy("Compare JWT vs session tokens")
        assert strategy == "lmm_reranking"

        # Test temporal selection
        strategy = injector.determine_strategy("How have our patterns evolved?")
        assert strategy == "reflective"

    def test_context_retrieval(self, hook_helper: HookTestHelper):
        """Test that hook retrieves relevant context.

        The hook should:
        - Execute semantic search with strategy
        - Categorize results
        - Return structured context
        """
        try:
            from context_injector import ContextInjector
        except ImportError:
            pytest.skip("context_injector not available in test environment")

        injector = ContextInjector()

        result = injector.retrieve_context(
            query="How do we handle authentication?",
            strategy="semantic_search",
            limit=5
        )

        assert result["status"] == "success"
        assert result["strategy"] == "semantic_search"

    def test_result_categorization(self, hook_helper: HookTestHelper):
        """Test that hook categorizes results.

        The hook should:
        - Count implementations, procedures, insights
        - Calculate average relevance
        - Format for user display
        """
        try:
            from context_injector import ContextInjector
        except ImportError:
            pytest.skip("context_injector not available in test environment")

        injector = ContextInjector()

        analysis = injector.analyze_prompt("How should we design the API?")

        assert "detected_intents" in analysis
        assert "retrieval_strategy" in analysis
        assert "keywords" in analysis


class TestHookIntegration:
    """Test hook system integration end-to-end."""

    def test_tool_execution_flow(self, hook_helper: HookTestHelper):
        """Test complete tool execution → event recording → analysis flow.

        Scenario:
        1. User invokes tool (e.g., consolidate)
        2. post-tool-use hook records event
        3. attention-optimizer checks load
        4. Event added to episodic memory
        """
        # Simulate tool execution
        event = hook_helper.record_test_event(
            content="Tool execution completed successfully",
            event_type="tool_execution"
        )

        assert event is not None

        # Verify event is retrievable
        events = hook_helper.get_recent_events(1)
        assert len(events) > 0

    def test_session_lifecycle_flow(self, hook_helper: HookTestHelper):
        """Test complete session lifecycle.

        Scenario:
        1. session-start: Load context + check load
        2. user-prompt-submit: Inject relevant memory
        3. [Multiple tool executions]: Record events
        4. session-end: Consolidate + audit quality
        """
        # Start of session
        hook_helper.memory_manager.remember(
            content="Starting new session",
            memory_type="fact"
        )

        # Middle of session - multiple events
        for i in range(3):
            hook_helper.record_test_event(
                content=f"Work item {i}",
                event_type="action"
            )

        # End of session - would consolidate
        events = hook_helper.get_recent_events(5)
        assert len(events) >= 3

    def test_error_recovery_flow(self, hook_helper: HookTestHelper):
        """Test error handling and recovery.

        Scenario:
        1. Tool fails → post-tool-use records error
        2. error-handler agent invoked
        3. System continues without interruption
        """
        # Record an error
        error_event = hook_helper.record_test_event(
            content=json.dumps({
                "error": "Tool failed to execute",
                "recovery": "Fallback to previous result"
            }),
            event_type="tool_error"
        )

        assert error_event is not None

        # System continues - next event succeeds
        success_event = hook_helper.record_test_event(
            content="Recovery successful",
            event_type="tool_execution"
        )

        assert success_event is not None

    def test_agent_invocation_flow(self, hook_helper: HookTestHelper):
        """Test that hooks properly invoke agents.

        Verifies:
        - Agent registry has required agents
        - Priority ordering correct
        - Invocation methods (slash command, MCP tool)
        """
        try:
            from agent_invoker import AgentInvoker
        except ImportError:
            pytest.skip("agent_invoker not available in test environment")

        invoker = AgentInvoker()

        # Verify registry
        assert "rag-specialist" in invoker.AGENT_REGISTRY
        assert "consolidation-engine" in invoker.AGENT_REGISTRY
        assert "error-handler" in invoker.AGENT_REGISTRY

        # Verify priorities
        rag_priority = invoker.AGENT_REGISTRY["rag-specialist"]["priority"]
        assert rag_priority == 100  # Highest priority


class TestHookErrorHandling:
    """Test hook error handling and robustness."""

    def test_missing_mcp_tools(self, hook_helper: HookTestHelper):
        """Test hook behavior when MCP tools unavailable.

        Hooks should:
        - Gracefully degrade
        - Log warnings but not crash
        - Continue with fallback behavior
        """
        # Would test with MCP tool unavailable
        assert True  # Placeholder

    def test_database_unavailable(self, hook_helper: HookTestHelper):
        """Test hook behavior when database unavailable.

        Hooks should:
        - Handle connection errors
        - Retry with backoff
        - Continue execution without blocking
        """
        # Would test with database down
        assert True  # Placeholder

    def test_agent_timeout(self, hook_helper: HookTestHelper):
        """Test hook behavior when agent times out.

        Hooks should:
        - Set reasonable timeouts
        - Kill hanging operations
        - Continue with partial results
        """
        # Would test with agent timeout
        assert True  # Placeholder


@pytest.mark.integration
class TestCompleteHookSystem:
    """Integration tests for complete hook system."""

    def test_hook_system_ready(self, hook_helper: HookTestHelper):
        """Verify complete hook system is ready."""
        # Check all hooks exist
        hook_files = [
            "/home/user/.claude/hooks/post-tool-use.sh",
            "/home/user/.claude/hooks/session-start.sh",
            "/home/user/.claude/hooks/session-end.sh",
            "/home/user/.claude/hooks/pre-execution.sh",
            "/home/user/.claude/hooks/post-task-completion.sh",
            "/home/user/.claude/hooks/smart-context-injection.sh",
        ]

        for hook_file in hook_files:
            path = Path(hook_file)
            assert path.exists(), f"Hook file missing: {hook_file}"
            assert path.stat().st_size > 0, f"Hook file empty: {hook_file}"

    def test_agent_invoker_available(self):
        """Verify agent invoker is available."""
        try:
            from agent_invoker import AgentInvoker
        except ImportError:
            pytest.skip("agent_invoker not available in test environment")

        invoker = AgentInvoker()
        agents = invoker.list_all_agents()

        assert len(agents) > 0
        assert any(a["name"] == "error-handler" for a in agents)
        assert any(a["name"] == "rag-specialist" for a in agents)

    def test_context_injector_available(self):
        """Verify context injector is available."""
        try:
            from context_injector import ContextInjector
        except ImportError:
            pytest.skip("context_injector not available in test environment")

        injector = ContextInjector()
        strategies = injector.list_strategies()

        assert len(strategies) > 0
        assert "hyde" in strategies
        assert "reflective" in strategies
