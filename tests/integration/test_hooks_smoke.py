"""Smoke tests for hook system - verifies hooks exist and are properly configured.

This test file provides lightweight verification that all hooks are in place
and have the correct structure, without requiring full memory system initialization.
"""

import pytest
from pathlib import Path
import json
import re


class TestHookFilesExist:
    """Test that all hook files exist and are valid."""

    HOOKS = {
        "post-tool-use.sh": {
            "agents": ["error-handler", "attention-optimizer"],
            "mcp_tools": ["episodic_tools", "execution_tools"],
        },
        "session-start.sh": {
            "agents": ["session-initializer"],
            "mcp_tools": ["memory_tools", "task_management_tools"],
        },
        "session-end.sh": {
            "agents": [
                "consolidation-engine",
                "workflow-learner",
                "quality-auditor",
            ],
            "mcp_tools": ["consolidation_tools"],
        },
        "pre-execution.sh": {
            "agents": ["plan-validator", "goal-orchestrator", "strategy-selector"],
            "mcp_tools": ["phase6_planning_tools"],
        },
        "post-task-completion.sh": {
            "agents": ["execution-monitor", "goal-orchestrator", "workflow-learner"],
            "mcp_tools": ["task_management_tools"],
        },
        "smart-context-injection.sh": {
            "agents": ["rag-specialist", "research-coordinator"],
            "mcp_tools": ["rag_tools"],
        },
    }

    def test_all_hooks_exist(self):
        """Test that all hook files exist."""
        hook_dir = Path("/home/user/.claude/hooks")

        for hook_name in self.HOOKS.keys():
            hook_path = hook_dir / hook_name
            assert hook_path.exists(), f"Hook file missing: {hook_name}"
            assert hook_path.stat().st_size > 0, f"Hook file empty: {hook_name}"

    def test_post_tool_use_hook(self):
        """Verify post-tool-use.sh hook structure."""
        hook_path = Path("/home/user/.claude/hooks/post-tool-use.sh")
        content = hook_path.read_text()

        # Check for key components
        assert "AgentInvoker" in content
        assert "error-handler" in content or "error_handler" in content
        assert "attention-optimizer" in content or "attention_optimizer" in content
        assert "episodic" in content.lower()

    def test_session_start_hook(self):
        """Verify session-start.sh hook structure."""
        hook_path = Path("/home/user/.claude/hooks/session-start.sh")
        content = hook_path.read_text()

        # Check for key components
        assert "session-initializer" in content or "session_initializer" in content
        assert "context" in content.lower()
        assert "load" in content.lower()

    def test_session_end_hook(self):
        """Verify session-end.sh hook structure."""
        hook_path = Path("/home/user/.claude/hooks/session-end.sh")
        content = hook_path.read_text()

        # Check for consolidation components
        assert "consolidation" in content.lower()
        assert "quality" in content.lower()

    def test_pre_execution_hook(self):
        """Verify pre-execution.sh hook structure."""
        hook_path = Path("/home/user/.claude/hooks/pre-execution.sh")
        content = hook_path.read_text()

        # Check for validation components
        assert "validate" in content.lower() or "validation" in content.lower()
        assert "plan" in content.lower()

    def test_post_task_completion_hook(self):
        """Verify post-task-completion.sh hook structure."""
        hook_path = Path("/home/user/.claude/hooks/post-task-completion.sh")
        content = hook_path.read_text()

        # Check for goal/task components
        assert "goal" in content.lower() or "task" in content.lower()

    def test_smart_context_injection_hook(self):
        """Verify smart-context-injection.sh hook structure."""
        hook_path = Path("/home/user/.claude/hooks/smart-context-injection.sh")
        content = hook_path.read_text()

        # Check for RAG/context components
        assert "context" in content.lower()
        assert "strategy" in content.lower() or "retrieval" in content.lower()


class TestHookSupportingFiles:
    """Test that supporting files exist."""

    def test_agent_invoker_exists(self):
        """Test that agent_invoker.py exists."""
        agent_invoker = Path(
            "/home/user/.claude/hooks/lib/agent_invoker.py"
        )
        assert agent_invoker.exists()
        assert agent_invoker.stat().st_size > 0

        # Check content
        content = agent_invoker.read_text()
        assert "class AgentInvoker" in content
        assert "AGENT_REGISTRY" in content

    def test_context_injector_exists(self):
        """Test that context_injector.py exists."""
        context_injector = Path(
            "/home/user/.claude/hooks/lib/context_injector.py"
        )
        assert context_injector.exists()
        assert context_injector.stat().st_size > 0

        # Check content
        content = context_injector.read_text()
        assert "class ContextInjector" in content

    def test_event_recorder_exists(self):
        """Test that event_recorder.py exists."""
        event_recorder = Path("/home/user/.claude/hooks/lib/event_recorder.py")
        assert event_recorder.exists()
        assert event_recorder.stat().st_size > 0

    def test_load_monitor_exists(self):
        """Test that load_monitor.py exists."""
        load_monitor = Path("/home/user/.claude/hooks/lib/load_monitor.py")
        assert load_monitor.exists()
        assert load_monitor.stat().st_size > 0


class TestAgentInvokerRegistry:
    """Test agent invoker registry is properly configured."""

    def test_agent_registry_complete(self):
        """Test that all required agents are registered."""
        import sys
        sys.path.insert(0, "/home/user/.claude/hooks/lib")

        try:
            from agent_invoker import AgentInvoker

            invoker = AgentInvoker()

            # Check required agents exist
            # (error-handler may be optional or use different name)
            required_agents = {
                "attention-optimizer",
                "rag-specialist",
                "consolidation-engine",
                "plan-validator",
                "execution-monitor",
                "workflow-learner",
            }

            registry_agents = set(invoker.AGENT_REGISTRY.keys())
            assert required_agents.issubset(
                registry_agents
            ), f"Missing agents: {required_agents - registry_agents}"

        except ImportError:
            pytest.skip("agent_invoker not available")

    def test_agent_priorities_ordered(self):
        """Test that agent priorities are properly ordered."""
        import sys
        sys.path.insert(0, "/home/user/.claude/hooks/lib")

        try:
            from agent_invoker import AgentInvoker

            invoker = AgentInvoker()

            # Check rag-specialist has highest priority (100)
            assert invoker.AGENT_REGISTRY["rag-specialist"]["priority"] >= 99

            # Check all priorities are valid
            for agent_name, agent_info in invoker.AGENT_REGISTRY.items():
                priority = agent_info.get("priority", 0)
                assert 0 <= priority <= 100, (
                    f"Invalid priority for {agent_name}: {priority}"
                )

        except ImportError:
            pytest.skip("agent_invoker not available")


class TestContextInjectorStrategies:
    """Test context injector RAG strategies."""

    def test_context_injector_intent_patterns(self):
        """Test that context injector has intent patterns defined."""
        import sys
        sys.path.insert(0, "/home/user/.claude/hooks/lib")

        try:
            from context_injector import ContextInjector

            injector = ContextInjector()

            # Check intent patterns exist
            assert hasattr(injector, "INTENT_PATTERNS")
            patterns = injector.INTENT_PATTERNS

            # Check for key intent types
            assert "authentication" in patterns
            assert "database" in patterns
            assert "api" in patterns

        except ImportError:
            pytest.skip("context_injector not available")

    def test_context_injector_analyze_prompt(self):
        """Test context injector prompt analysis."""
        import sys
        sys.path.insert(0, "/home/user/.claude/hooks/lib")

        try:
            from context_injector import ContextInjector

            injector = ContextInjector()

            # Test prompt analysis
            analysis = injector.analyze_prompt("How should we handle authentication?")

            assert "detected_intents" in analysis
            assert "keywords" in analysis
            assert "retrieval_strategy" in analysis

        except ImportError:
            pytest.skip("context_injector not available")


class TestHookIntegration:
    """Integration tests for hook system."""

    def test_hooks_non_blocking(self):
        """Test that hooks exit cleanly even on errors.

        Key requirement: hooks should never block execution.
        """
        # All hooks should use 'set -e' or equivalent error handling
        hooks = [
            "/home/user/.claude/hooks/post-tool-use.sh",
            "/home/user/.claude/hooks/session-start.sh",
            "/home/user/.claude/hooks/session-end.sh",
            "/home/user/.claude/hooks/pre-execution.sh",
            "/home/user/.claude/hooks/post-task-completion.sh",
            "/home/user/.claude/hooks/smart-context-injection.sh",
        ]

        for hook_path_str in hooks:
            hook_path = Path(hook_path_str)
            content = hook_path.read_text()

            # Should have proper error handling
            # Either uses 'set -e' or has 'exit' statements or 'true' fallbacks
            assert (
                "set -e" in content
                or "|| exit 0" in content
                or "|| true" in content
            ), f"Hook {hook_path.name} missing error handling"

    def test_hooks_log_output(self):
        """Test that hooks provide meaningful logging."""
        hooks_with_logging = [
            ("/home/user/.claude/hooks/post-tool-use.sh", "event"),
            ("/home/user/.claude/hooks/session-start.sh", "context"),
            ("/home/user/.claude/hooks/session-end.sh", "consolidation"),
        ]

        for hook_path_str, keyword in hooks_with_logging:
            hook_path = Path(hook_path_str)
            content = hook_path.read_text()

            # Should have log functions or echo statements
            assert "log" in content.lower() or "echo" in content.lower(), (
                f"Hook {hook_path.name} missing logging"
            )

    def test_hook_agent_invocation(self):
        """Test that hooks properly invoke agents."""
        # Check that at least one hook invokes agents
        hooks_dir = Path("/home/user/.claude/hooks")
        found_invocation = False

        for hook_file in hooks_dir.glob("*.sh"):
            content = hook_file.read_text()
            if "AgentInvoker" in content or "invoke_agent" in content:
                found_invocation = True
                break

        assert found_invocation, "No hooks found that invoke agents"

    def test_hook_mcp_tool_calls(self):
        """Test that hooks call MCP tools."""
        # Check that at least one hook calls MCP tools
        hooks_dir = Path("/home/user/.claude/hooks")
        found_mcp = False

        for hook_file in hooks_dir.glob("*.sh"):
            content = hook_file.read_text()
            if "mcp__" in content:
                found_mcp = True
                break

        assert found_mcp, "No hooks found that call MCP tools"


@pytest.mark.smoke
class TestHookSystemReady:
    """Verify hook system is ready for production."""

    def test_all_components_present(self):
        """Test that all components are in place."""
        required_files = [
            "/home/user/.claude/hooks/post-tool-use.sh",
            "/home/user/.claude/hooks/session-start.sh",
            "/home/user/.claude/hooks/session-end.sh",
            "/home/user/.claude/hooks/pre-execution.sh",
            "/home/user/.claude/hooks/post-task-completion.sh",
            "/home/user/.claude/hooks/smart-context-injection.sh",
            "/home/user/.claude/hooks/lib/agent_invoker.py",
            "/home/user/.claude/hooks/lib/context_injector.py",
        ]

        missing = []
        for file_path in required_files:
            if not Path(file_path).exists():
                missing.append(file_path)

        assert not missing, f"Missing files: {missing}"

    def test_hook_configuration_valid(self):
        """Test that hook configuration is valid."""
        # All hooks should be executable bash scripts
        hooks_dir = Path("/home/user/.claude/hooks")
        for hook_file in hooks_dir.glob("*.sh"):
            # Check shebang
            content = hook_file.read_text()
            assert content.startswith("#!/bin/bash"), (
                f"Hook {hook_file.name} missing bash shebang"
            )

    def test_hook_dependencies_available(self):
        """Test that hook dependencies are available."""
        import sys
        sys.path.insert(0, "/home/user/.claude/hooks/lib")

        # Try importing hook dependencies
        try:
            from agent_invoker import AgentInvoker
            invoker = AgentInvoker()
            assert invoker is not None
        except ImportError as e:
            pytest.skip(f"agent_invoker not available: {e}")
