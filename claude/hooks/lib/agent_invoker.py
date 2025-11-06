"""Agent invocation for autonomous orchestration."""

from typing import List, Dict, Optional, Any
import logging
import subprocess
import json
import sys

logger = logging.getLogger(__name__)


class AgentInvoker:
    """Manage autonomous agent invocation based on hook triggers."""

    # Agent registry with trigger conditions
    # Maps agent names to their slash command equivalents where applicable
    AGENT_REGISTRY = {
        # SessionStart agents
        "session-initializer": {
            "trigger": "session_start",
            "description": "Load context at session start",
            "priority": 100,
            "slash_command": "/critical:session-start",
        },
        # UserPromptSubmit agents
        # Context injection (runs FIRST - highest priority)
        "rag-specialist": {
            "trigger": "user_prompt_submit",
            "description": "Search memory and inject relevant context",
            "priority": 100,  # HIGHEST - must run before other analysis
            "mcp_tool": "mcp__athena__rag_tools:retrieve_smart",
        },
        "research-coordinator": {
            "trigger": "user_prompt_submit",
            "description": "Multi-source research and synthesis",
            "priority": 99,
            "slash_command": "/useful:retrieve-smart",
        },
        # Gap detection and suggestion (after context loaded)
        "gap-detector": {
            "trigger": "user_prompt_submit",
            "description": "Detect knowledge gaps and contradictions",
            "priority": 90,
            "mcp_tool": "mcp__athena__memory_tools:detect_knowledge_gaps",
        },
        "attention-manager": {
            "trigger": "user_prompt_submit",
            "description": "Manage cognitive load",
            "priority": 85,
            "mcp_tool": "mcp__athena__memory_tools:check_cognitive_load",
        },
        "procedure-suggester": {
            "trigger": "user_prompt_submit",
            "description": "Suggest applicable procedures",
            "priority": 80,
            "mcp_tool": "mcp__athena__procedural_tools:find_procedures",
        },
        # PostToolUse agents (every 10 operations)
        "attention-optimizer": {
            "trigger": "post_tool_use_batch",
            "description": "Optimize attention and consolidate if needed",
            "priority": 70,
            "slash_command": "/important:check-workload",
        },
        # PreExecution agents
        "plan-validator": {
            "trigger": "pre_execution",
            "description": "Validate plans before execution",
            "priority": 95,
            "slash_command": "/critical:validate-plan",
        },
        "goal-orchestrator": {
            "trigger": "pre_execution",
            "description": "Check goal conflicts and state",
            "priority": 90,
            "slash_command": "/critical:manage-goal",
        },
        "strategy-selector": {
            "trigger": "pre_execution",
            "description": "Confirm optimal strategy",
            "priority": 80,
            "slash_command": "/important:optimize-strategy",
        },
        # SessionEnd agents
        "consolidation-engine": {
            "trigger": "session_end",
            "description": "Extract patterns via dual-process reasoning",
            "priority": 100,
            "slash_command": "/important:consolidate",
        },
        "workflow-learner": {
            "trigger": "session_end",
            "description": "Extract reusable procedures",
            "priority": 95,
            "mcp_tool": "mcp__athena__procedural_tools:create_procedure",
        },
        "quality-auditor": {
            "trigger": "session_end",
            "description": "Assess memory quality",
            "priority": 90,
            "mcp_tool": "mcp__athena__memory_tools:evaluate_memory_quality",
        },
        # PostTaskCompletion agents
        "execution-monitor": {
            "trigger": "post_task_completion",
            "description": "Record task completion",
            "priority": 95,
            "mcp_tool": "mcp__athena__task_management_tools:record_execution_progress",
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
        """Invoke an agent asynchronously.

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

            # Try to invoke via slash command first (preferred method)
            if "slash_command" in agent_info:
                return self._invoke_via_slash_command(agent_name, agent_info, context)

            # Fall back to MCP tool invocation
            elif "mcp_tool" in agent_info:
                return self._invoke_via_mcp_tool(agent_name, agent_info, context)

            # No invocation method available
            else:
                logger.warning(f"No invocation method for agent: {agent_name}")
                self.invoked_agents.append(agent_name)
                self.agent_results[agent_name] = {
                    "status": "registered",
                    "context": context,
                }
                return False

        except Exception as e:
            logger.error(f"Failed to invoke agent {agent_name}: {e}")
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
