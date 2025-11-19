"""Synchronous bridge for calling async agents from hooks.

Hooks are shell scripts that need to call Python async code.
This bridge wraps async agent methods for use in synchronous contexts,
enabling agent activation at critical session lifecycle points.

Usage:
    from athena.agents.agent_bridge import AgentBridge

    # From SessionStart hook
    result = AgentBridge.activate_research_coordinator({"user_goal": "..."})

    # From PostToolUse hook
    analysis = AgentBridge.activate_code_analyzer(tool_output)
    routing = AgentBridge.activate_workflow_orchestrator(session_state)

    # From SessionEnd hook
    health = AgentBridge.activate_metacognition(session_metrics)
"""

import logging
import json
from typing import Dict, Any, Optional, List

from ..core.async_utils import run_async_in_thread
from ..episodic.operations import remember
from ..semantic.operations import store
from .research_coordinator import ResearchCoordinatorAgent
from .code_analyzer import CodeAnalyzerAgent
from .workflow_orchestrator import WorkflowOrchestratorAgent
from .metacognition import MetacognitionAgent

logger = logging.getLogger(__name__)


class AgentBridge:
    """Synchronous bridge for hook-based agent activation.

    All agent methods are async, but hooks need synchronous functions.
    This bridge converts async agent calls to synchronous operations
    using thread-based event loop execution.
    """

    @staticmethod
    def activate_research_coordinator(context: Dict[str, Any]) -> Dict[str, Any]:
        """Activate ResearchCoordinatorAgent at SessionStart.

        Plans research strategy based on session context and user goal.
        Stores plan in episodic memory for downstream agents.

        Args:
            context: Session context with user_goal, current_task, etc.

        Returns:
            Dict with plan, status, and any errors
        """
        logger.info("AgentBridge: Activating ResearchCoordinatorAgent")

        try:
            agent = ResearchCoordinatorAgent()

            # Plan research strategy using actual agent method
            query = context.get("user_goal") or context.get("current_context") or "research plan"
            plan = run_async_in_thread(
                agent.plan_research(
                    query=query,
                    depth=context.get("research_depth", 3),
                )
            )

            # Store plan in episodic memory
            plan_str = json.dumps(plan) if isinstance(plan, dict) else str(plan)
            run_async_in_thread(
                remember(
                    content=f"Research plan: {plan_str[:500]}",
                    tags=["research", "planning", "session-start"],
                    source="agent:research-coordinator",
                    importance=0.9,
                )
            )

            logger.info(f"ResearchCoordinatorAgent plan created with {len(str(plan))} chars")
            return {
                "status": "success",
                "agent": "research-coordinator",
                "plan_size": len(str(plan)),
            }

        except Exception as e:
            logger.error(f"ResearchCoordinatorAgent activation failed: {e}")
            return {
                "status": "error",
                "agent": "research-coordinator",
                "error": str(e),
            }

    @staticmethod
    def activate_code_analyzer(tool_output: str, tool_name: str = "unknown") -> Dict[str, Any]:
        """Activate CodeAnalyzerAgent at PostToolUse.

        Analyzes tool output for anti-patterns, quality issues, and security concerns.
        Stores findings in episodic memory.

        Args:
            tool_output: Output from the executed tool
            tool_name: Name of the tool that was executed

        Returns:
            Dict with analysis results and status
        """
        logger.info(f"AgentBridge: Activating CodeAnalyzerAgent for {tool_name}")

        try:
            agent = CodeAnalyzerAgent()

            # Analyze tool output
            analysis = run_async_in_thread(agent.analyze_tool_output(tool_output, tool_name))

            # Store anti-patterns if found
            if analysis.get("anti_patterns"):
                patterns_str = json.dumps(analysis["anti_patterns"])
                run_async_in_thread(
                    remember(
                        content=f"Anti-patterns detected by {tool_name}: {patterns_str}",
                        tags=["quality", "anti-patterns", "code-analysis", tool_name],
                        source="agent:code-analyzer",
                        importance=min(1.0, len(analysis["anti_patterns"]) * 0.1),
                    )
                )

            # Store quality metrics
            if analysis.get("quality_metrics"):
                metrics_str = json.dumps(analysis["quality_metrics"])
                run_async_in_thread(
                    remember(
                        content=f"Quality metrics from {tool_name}: {metrics_str}",
                        tags=["metrics", "quality", tool_name],
                        source="agent:code-analyzer",
                        importance=0.7,
                    )
                )

            logger.info(f"CodeAnalyzerAgent completed analysis: {analysis.get('status')}")
            return {
                "status": "success",
                "agent": "code-analyzer",
                "anti_patterns_found": len(analysis.get("anti_patterns", [])),
                "quality_score": analysis.get("quality_metrics", {}).get("overall_score"),
            }

        except Exception as e:
            logger.error(f"CodeAnalyzerAgent activation failed: {e}")
            return {
                "status": "error",
                "agent": "code-analyzer",
                "error": str(e),
            }

    @staticmethod
    def activate_workflow_orchestrator(
        session_state: Dict[str, Any], tool_results: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Activate WorkflowOrchestratorAgent at PostToolUse.

        Routes tasks, balances load, and determines next action.
        Stores routing decision in episodic memory.

        Args:
            session_state: Current session state and context
            tool_results: Optional results from code analyzer

        Returns:
            Dict with routing decision and status
        """
        logger.info("AgentBridge: Activating WorkflowOrchestratorAgent")

        try:
            agent = WorkflowOrchestratorAgent()

            # Route task
            routing = run_async_in_thread(
                agent.route_task(
                    current_state=session_state,
                    tool_results=tool_results or {},
                )
            )

            # Store routing decision
            routing_str = json.dumps(routing) if isinstance(routing, dict) else str(routing)
            run_async_in_thread(
                remember(
                    content=f"Workflow routed to {routing.get('target_agent', 'unknown')}: {routing_str}",
                    tags=["workflow", "routing", "orchestration"],
                    source="agent:workflow-orchestrator",
                    importance=0.8,
                )
            )

            logger.info(f"WorkflowOrchestratorAgent routed to {routing.get('target_agent')}")
            return {
                "status": "success",
                "agent": "workflow-orchestrator",
                "target_agent": routing.get("target_agent"),
                "action": routing.get("action"),
            }

        except Exception as e:
            logger.error(f"WorkflowOrchestratorAgent activation failed: {e}")
            return {
                "status": "error",
                "agent": "workflow-orchestrator",
                "error": str(e),
            }

    @staticmethod
    def activate_metacognition(session_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Activate MetacognitionAgent at SessionEnd.

        Assesses system health, detects degradation, and suggests adaptations.
        Stores health report and suggestions in semantic memory.

        Args:
            session_metrics: Metrics from the completed session

        Returns:
            Dict with health assessment and adaptations
        """
        logger.info("AgentBridge: Activating MetacognitionAgent")

        try:
            agent = MetacognitionAgent()

            # Health check
            health = run_async_in_thread(agent.health_check(session_metrics))

            # Detect degradation
            degradation = run_async_in_thread(agent.detect_degradation(health))

            # Store health report
            health_str = json.dumps(health) if isinstance(health, dict) else str(health)
            run_async_in_thread(
                store(
                    content=f"Session health report: {health_str}",
                    topics=["metacognition", "health", "session-end"],
                    confidence=0.9,
                )
            )

            # Suggest adaptations if degradation detected
            adaptations = {}
            if degradation:
                adaptations = run_async_in_thread(agent.suggest_adaptations(degradation))

                adaptations_str = json.dumps(adaptations)
                run_async_in_thread(
                    store(
                        content=f"Suggested adaptations: {adaptations_str}",
                        topics=["metacognition", "adaptations", "improvement"],
                        confidence=0.8,
                    )
                )

            logger.info(f"MetacognitionAgent completed health check: {health.get('status')}")
            return {
                "status": "success",
                "agent": "metacognition",
                "health_score": health.get("overall_health"),
                "degradation_detected": bool(degradation),
                "adaptations_suggested": len(adaptations) if adaptations else 0,
            }

        except Exception as e:
            logger.error(f"MetacognitionAgent activation failed: {e}")
            return {
                "status": "error",
                "agent": "metacognition",
                "error": str(e),
            }

    @staticmethod
    def activate_all_agents(
        session_phase: str,
        context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Activate all relevant agents for a session phase.

        Determines which agents to activate based on session phase
        and triggers them in appropriate order.

        Args:
            session_phase: 'start', 'tool_use', or 'end'
            context: Full context dict with all available data

        Returns:
            List of activation results from each agent
        """
        results = []

        try:
            if session_phase == "start":
                results.append(AgentBridge.activate_research_coordinator(context))

            elif session_phase == "tool_use":
                tool_output = context.get("tool_output", "")
                tool_name = context.get("tool_name", "unknown")
                session_state = context.get("session_state", {})

                # Code analyzer first
                analysis_result = AgentBridge.activate_code_analyzer(tool_output, tool_name)
                results.append(analysis_result)

                # Then orchestrator (can use analysis results)
                context["tool_results"] = analysis_result
                orchestrator_result = AgentBridge.activate_workflow_orchestrator(
                    session_state, analysis_result
                )
                results.append(orchestrator_result)

            elif session_phase == "end":
                metrics = context.get("session_metrics", {})
                results.append(AgentBridge.activate_metacognition(metrics))

            logger.info(f"AgentBridge: {session_phase} phase completed with {len(results)} agents")

        except Exception as e:
            logger.error(f"AgentBridge multi-agent activation failed: {e}")
            results.append(
                {
                    "status": "error",
                    "error": str(e),
                    "phase": session_phase,
                }
            )

        return results
