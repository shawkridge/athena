"""Agent invocation for autonomous orchestration.

Now uses direct Python API (local-first) instead of HTTP.
Agents invoke memory operations directly without network calls.
"""

from typing import List, Dict, Optional, Any
import logging
import subprocess
import json
import sys

logger = logging.getLogger(__name__)


def get_athena_client():
    """Get Athena client instance (direct Python API).

    Returns:
        AthenaDirectClient instance, or None if initialization fails
    """
    try:
        # Use absolute import to support being called from hook context
        from athena_direct_client import AthenaDirectClient
        client = AthenaDirectClient()
        if client._ensure_initialized():
            return client
        return None
    except ImportError as e:
        logger.error(f"Failed to import AthenaDirectClient: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to initialize Athena client: {e}")
        return None


class AgentInvoker:
    """Manage autonomous agent invocation based on hook triggers."""

    # Agent registry with trigger conditions
    # Maps agent names to their invocation method (direct Python API)
    AGENT_REGISTRY = {
        # SessionStart agents
        "session-initializer": {
            "trigger": "session_start",
            "description": "Load context at session start",
            "priority": 100,
            "api_method": "recall",
            "api_args": {"query": "recent context and goals", "k": 10},
        },
        # UserPromptSubmit agents
        # Context injection (runs FIRST - highest priority)
        "rag-specialist": {
            "trigger": "user_prompt_submit",
            "description": "Search memory and inject relevant context",
            "priority": 100,  # HIGHEST - must run before other analysis
            "api_method": "recall",
            "api_args": {"query": "context from query", "k": 5},
        },
        "research-coordinator": {
            "trigger": "user_prompt_submit",
            "description": "Multi-source research and synthesis",
            "priority": 99,
            "api_method": "recall",
            "api_args": {"query": "research and findings", "k": 10},
        },
        # Gap detection and suggestion (after context loaded)
        "gap-detector": {
            "trigger": "user_prompt_submit",
            "description": "Detect knowledge gaps and contradictions",
            "priority": 90,
            "api_method": "get_memory_health",
            "api_args": {},
        },
        "attention-manager": {
            "trigger": "user_prompt_submit",
            "description": "Manage cognitive load",
            "priority": 85,
            "api_method": "check_cognitive_load",
            "api_args": {},
        },
        "procedure-suggester": {
            "trigger": "user_prompt_submit",
            "description": "Suggest applicable procedures",
            "priority": 80,
            "api_method": "recall",
            "api_args": {"query": "applicable procedures", "k": 5},
        },
        # PostToolUse agents (every 10 operations)
        "attention-optimizer": {
            "trigger": "post_tool_use_batch",
            "description": "Optimize attention and consolidate if needed",
            "priority": 70,
            "api_method": "check_cognitive_load",
            "api_args": {},
        },
        # PreExecution agents
        "plan-validator": {
            "trigger": "pre_execution",
            "description": "Validate plans before execution",
            "priority": 95,
            "api_method": "get_memory_health",
            "api_args": {},
        },
        "goal-orchestrator": {
            "trigger": "pre_execution",
            "description": "Check goal conflicts and state",
            "priority": 90,
            "api_method": "get_memory_health",
            "api_args": {},
        },
        "strategy-selector": {
            "trigger": "pre_execution",
            "description": "Confirm optimal strategy",
            "priority": 80,
            "api_method": "get_memory_health",
            "api_args": {},
        },
        # SessionEnd agents
        "consolidation-engine": {
            "trigger": "session_end",
            "description": "Extract patterns via dual-process reasoning",
            "priority": 100,
            "api_method": "run_consolidation",
            "api_args": {"strategy": "balanced"},
        },
        "workflow-learner": {
            "trigger": "session_end",
            "description": "Extract reusable procedures",
            "priority": 95,
            "api_method": "get_memory_health",
            "api_args": {},
        },
        "quality-auditor": {
            "trigger": "session_end",
            "description": "Assess memory quality",
            "priority": 90,
            "api_method": "get_memory_quality_summary",
            "api_args": {},
        },
        # PostTaskCompletion agents
        "execution-monitor": {
            "trigger": "post_task_completion",
            "description": "Record task completion",
            "priority": 95,
            "api_method": "get_memory_health",
            "api_args": {},
        },
    }

    def __init__(self):
        """Initialize agent invoker."""
        self.invoked_agents = []
        self.agent_results = {}

    def get_agents_for_trigger(self, trigger: str) -> List[str]:
        """Get agents for a given trigger point.

        Args:
            trigger: Trigger point (session_start, user_prompt_submit, etc.)

        Returns:
            List of agent names, sorted by priority
        """
        agents = [
            name
            for name, info in self.AGENT_REGISTRY.items()
            if info["trigger"] == trigger
        ]

        # Sort by priority (highest first)
        agents.sort(
            key=lambda a: self.AGENT_REGISTRY[a]["priority"], reverse=True
        )

        return agents

    def invoke_agent(
        self,
        agent_name: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Invoke an agent using direct Python API.

        Args:
            agent_name: Name of agent to invoke
            context: Context data for agent

        Returns:
            True if successfully invoked, False otherwise
        """
        if agent_name not in self.AGENT_REGISTRY:
            logger.warning(f"Unknown agent: {agent_name}")
            return False

        agent_info = self.AGENT_REGISTRY[agent_name]

        try:
            logger.info(f"Invoking agent: {agent_name}")
            logger.info(f"  Description: {agent_info['description']}")

            # Use direct Python API (local-first)
            return self._invoke_via_direct_api(agent_name, agent_info, context)

        except Exception as e:
            logger.error(f"Failed to invoke agent {agent_name}: {e}")
            return False

    def _invoke_via_direct_api(
        self,
        agent_name: str,
        agent_info: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Invoke agent via direct Python API (local-first, no HTTP).

        Args:
            agent_name: Agent name
            agent_info: Agent registry entry
            context: Optional context data

        Returns:
            True if successfully invoked
        """
        api_method = agent_info.get("api_method")
        api_args = agent_info.get("api_args", {})
        logger.info(f"  Method: Direct API → {api_method}")

        try:
            # Get Athena client
            client = get_athena_client()
            if client is None:
                logger.warning(f"Athena client not available, skipping agent {agent_name}")
                return False

            # Check health
            health = client.health()
            if health.get("status") != "healthy":
                logger.warning(f"Athena not healthy ({health.get('status')}), skipping agent {agent_name}")
                return False

            # Merge context into API arguments
            merged_args = {**api_args}
            if context:
                # Filter context to only include parameters supported by the API method
                # This prevents passing session metadata as API parameters
                api_param_whitelist = {
                    "recall": {"query", "k", "memory_type", "limit"},
                    "remember": {"content", "memory_type", "tags", "importance"},
                    "record_event": {"event_type", "content", "context", "importance"},
                    "forget": {"memory_id"},
                    "get_memory_quality_summary": set(),
                    "run_consolidation": {"strategy", "dry_run"},
                    "check_cognitive_load": set(),
                    "get_memory_health": set(),
                }

                if api_method in api_param_whitelist:
                    allowed_params = api_param_whitelist[api_method]
                    filtered_context = {
                        k: v for k, v in context.items()
                        if k in allowed_params
                    }
                    merged_args.update(filtered_context)

            # Call the API method
            result = None
            if hasattr(client, api_method):
                api_func = getattr(client, api_method)
                result = api_func(**merged_args)
                logger.info(f"  Result: {api_method}() → {type(result).__name__}")
            else:
                logger.warning(f"API method not available: {api_method}")
                return False

            # Record the invocation
            invocation_result = {
                "agent": agent_name,
                "method": "direct_api",
                "api_method": api_method,
                "api_args": merged_args,
                "result": result,
                "status": "invoked",
            }

            self.invoked_agents.append(agent_name)
            self.agent_results[agent_name] = invocation_result

            return True

        except Exception as e:
            logger.error(f"Failed to invoke via direct API: {e}")
            return False

    def _invoke_via_slash_command(
        self,
        agent_name: str,
        agent_info: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Invoke agent via slash command.

        Args:
            agent_name: Agent name
            agent_info: Agent registry entry
            context: Optional context data

        Returns:
            True if successfully invoked
        """
        slash_command = agent_info["slash_command"]
        logger.info(f"  Method: SlashCommand → {slash_command}")

        try:
            # In hook environment, we output a message that Claude Code
            # will recognize and process as a slash command execution request
            result = {
                "agent": agent_name,
                "method": "slash_command",
                "command": slash_command,
                "context": context,
                "status": "invoked",
            }

            logger.info(f"  Result: {json.dumps(result)}")

            self.invoked_agents.append(agent_name)
            self.agent_results[agent_name] = result

            return True

        except Exception as e:
            logger.error(f"Failed to invoke via slash command: {e}")
            return False

    def _invoke_via_mcp_tool(
        self,
        agent_name: str,
        agent_info: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Invoke agent via MCP tool call.

        Args:
            agent_name: Agent name
            agent_info: Agent registry entry
            context: Optional context data

        Returns:
            True if successfully invoked
        """
        mcp_tool = agent_info["mcp_tool"]
        logger.info(f"  Method: MCP Tool → {mcp_tool}")

        try:
            # Document the MCP tool call that would be executed
            server, operation = mcp_tool.split(":")
            result = {
                "agent": agent_name,
                "method": "mcp_tool",
                "server": server,
                "operation": operation,
                "context": context,
                "status": "invoked",
            }

            logger.info(f"  Result: {json.dumps(result)}")

            self.invoked_agents.append(agent_name)
            self.agent_results[agent_name] = result

            return True

        except Exception as e:
            logger.error(f"Failed to invoke via MCP tool: {e}")
            return False

    def invoke_agents_for_trigger(
        self,
        trigger: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """Invoke all agents for a trigger point.

        Args:
            trigger: Trigger point
            context: Context data

        Returns:
            List of successfully invoked agent names
        """
        agents = self.get_agents_for_trigger(trigger)
        invoked = []

        for agent_name in agents:
            if self.invoke_agent(agent_name, context):
                invoked.append(agent_name)

        return invoked

    def get_invoked_agents(self) -> List[str]:
        """Get list of agents invoked in this session.

        Returns:
            List of agent names
        """
        return self.invoked_agents

    def get_agent_results(self) -> Dict[str, Any]:
        """Get results from invoked agents.

        Returns:
            Dictionary of agent results
        """
        return self.agent_results

    @staticmethod
    def get_agent_info(agent_name: str) -> Optional[Dict[str, Any]]:
        """Get information about an agent.

        Args:
            agent_name: Name of agent

        Returns:
            Agent info dictionary or None
        """
        return AgentInvoker.AGENT_REGISTRY.get(agent_name)

    @staticmethod
    def list_all_agents() -> List[Dict[str, Any]]:
        """List all registered agents.

        Returns:
            List of agent info dictionaries
        """
        return [
            {"name": name, **info}
            for name, info in AgentInvoker.AGENT_REGISTRY.items()
        ]
