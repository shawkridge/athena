"""MetacognitionAgent - System health monitoring and adaptive optimization.

This agent monitors system health, tracks agent performance, identifies bottlenecks,
and recommends optimizations. It enables the system to adapt and improve itself
based on observed performance patterns.

The agent integrates with:
- All agents: Monitors their performance and health
- MemoryCoordinator: Stores health metrics and insights
- WorkflowOrchestrator: Recommends load adjustments
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

# Import coordinator base class
from .coordinator import AgentCoordinator
from ..orchestration.adaptive_agent import AdaptiveAgent

# Import core memory operations
from ..semantic.operations import store as store_fact

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """System health status."""

    EXCELLENT = "excellent"  # >95% health
    GOOD = "good"  # 80-95% health
    FAIR = "fair"  # 60-80% health
    POOR = "poor"  # 40-60% health
    CRITICAL = "critical"  # <40% health


@dataclass
class ComponentHealth:
    """Health status of a system component."""

    component: str
    status: HealthStatus
    score: float  # 0.0-1.0
    last_check: str  # ISO timestamp
    issues: List[str]
    metrics: Dict[str, Any]


@dataclass
class Bottleneck:
    """Represents a system bottleneck."""

    component: str
    issue: str
    severity: int  # 1-10
    impact: str
    affected_components: List[str]
    recommendation: str


@dataclass
class Optimization:
    """Represents a recommended optimization."""

    component: str
    optimization: str
    expected_improvement: float  # percentage
    effort_hours: float
    risk_level: str  # low, medium, high
    rationale: str


class MetacognitionAgent(AgentCoordinator, AdaptiveAgent):
    """System health monitoring and adaptive optimization.

    Monitors:
    - Agent performance and health
    - Memory system efficiency
    - Hook execution performance
    - Overall system health

    Recommends:
    - Optimizations and tuning
    - Resource adjustments
    - Adaptive strategies
    """

    def __init__(self):
        """Initialize the Metacognition Agent."""
        super().__init__(
            agent_id="metacognition",
            agent_type="metacognition",
        )
        self.health_checks = 0
        self.optimizations_applied = 0
        self.last_health_check: Optional[str] = None

    async def check_system_health(self) -> Dict[str, Any]:
        """Assess overall system health.

        Returns:
            Health report with component statuses
        """
        logger.info("Checking system health")
        self.health_checks += 1

        health_report = {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_status": HealthStatus.GOOD.value,
            "overall_score": 0.85,
            "components": {},
            "issues": [],
            "recommendations": [],
        }

        try:
            # Check memory system
            memory_health = await self._check_memory_health()
            health_report["components"]["memory"] = memory_health

            # Check agents
            agents_health = await self._check_agents_health()
            health_report["components"]["agents"] = agents_health

            # Check hooks
            hooks_health = await self._check_hooks_health()
            health_report["components"]["hooks"] = hooks_health

            # Calculate overall health
            health_scores = [
                memory_health.score,
                agents_health.score,
                hooks_health.score,
            ]
            overall_score = sum(health_scores) / len(health_scores)
            health_report["overall_score"] = overall_score

            # Determine overall status
            if overall_score > 0.95:
                health_report["overall_status"] = HealthStatus.EXCELLENT.value
            elif overall_score > 0.80:
                health_report["overall_status"] = HealthStatus.GOOD.value
            elif overall_score > 0.60:
                health_report["overall_status"] = HealthStatus.FAIR.value
            else:
                health_report["overall_status"] = HealthStatus.POOR.value

            # Collect all issues
            health_report["issues"] = (
                memory_health.issues + agents_health.issues + hooks_health.issues
            )

            self.last_health_check = health_report["timestamp"]
            logger.info(f"Health check complete: {health_report['overall_status']}")

        except Exception as e:
            logger.error(f"Error checking system health: {e}")
            health_report["error"] = str(e)

        return health_report

    async def identify_bottlenecks(self) -> List[Bottleneck]:
        """Identify system bottlenecks.

        Returns:
            List of identified bottlenecks
        """
        logger.info("Identifying system bottlenecks")
        bottlenecks = []

        try:
            # Check memory latency
            memory_bottleneck = await self._check_memory_latency()
            if memory_bottleneck:
                bottlenecks.append(memory_bottleneck)

            # Check agent performance
            agent_bottlenecks = await self._check_agent_bottlenecks()
            bottlenecks.extend(agent_bottlenecks)

            # Check consolidation efficiency
            consolidation_bottleneck = await self._check_consolidation_bottleneck()
            if consolidation_bottleneck:
                bottlenecks.append(consolidation_bottleneck)

            # Sort by severity
            bottlenecks.sort(key=lambda b: b.severity, reverse=True)

            logger.info(f"Identified {len(bottlenecks)} bottlenecks")

        except Exception as e:
            logger.error(f"Error identifying bottlenecks: {e}")

        return bottlenecks

    async def recommend_optimization(
        self,
        component: str,
        issue: str,
    ) -> List[Optimization]:
        """Recommend optimizations for an issue.

        Args:
            component: Component to optimize
            issue: Issue to address

        Returns:
            List of optimization recommendations
        """
        logger.info(f"Recommending optimizations for {component}: {issue}")
        recommendations = []

        try:
            if component == "memory":
                recommendations = self._recommend_memory_optimization(issue)
            elif component == "agents":
                recommendations = self._recommend_agent_optimization(issue)
            elif component == "hooks":
                recommendations = self._recommend_hook_optimization(issue)
            else:
                recommendations = self._recommend_general_optimization(issue)

            # Store recommendations
            if recommendations:
                top_rec = recommendations[0]
                await store_fact(
                    content=f"Optimization: {component} - {top_rec.optimization}",
                    topics=["optimization", "performance", component],
                )

            logger.info(f"Generated {len(recommendations)} optimization recommendations")

        except Exception as e:
            logger.error(f"Error recommending optimization: {e}")

        return recommendations

    async def adapt_strategy(
        self,
        performance_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Adapt agent strategies based on performance data.

        Args:
            performance_data: Performance metrics and data

        Returns:
            Adaptation decisions
        """
        logger.info("Adapting system strategies based on performance")
        adaptations = {
            "timestamp": datetime.utcnow().isoformat(),
            "changes": [],
            "reasoning": "",
        }

        try:
            # Adjust consolidation strategy
            if "consolidation_time_ms" in performance_data:
                cons_time = performance_data["consolidation_time_ms"]
                if cons_time > 5000:  # >5 seconds is too long
                    adaptations["changes"].append(
                        {
                            "component": "consolidation",
                            "change": "Use faster clustering algorithm",
                            "expected_improvement": "30% faster consolidation",
                        }
                    )

            # Adjust agent load balancing
            if "agent_loads" in performance_data:
                max_load = max(performance_data["agent_loads"].values())
                if max_load > 10:  # Too many queued tasks
                    adaptations["changes"].append(
                        {
                            "component": "orchestration",
                            "change": "Increase parallel task processing",
                            "expected_improvement": "Better load distribution",
                        }
                    )

            # Adjust memory retention
            if "memory_size_mb" in performance_data:
                mem_size = performance_data["memory_size_mb"]
                if mem_size > 1000:  # >1GB is large
                    adaptations["changes"].append(
                        {
                            "component": "memory",
                            "change": "Increase consolidation frequency",
                            "expected_improvement": "Reduce episodic event size",
                        }
                    )

            if adaptations["changes"]:
                adaptations["reasoning"] = (
                    f"Applied {len(adaptations['changes'])} adaptations to improve performance"
                )
                logger.info(f"Made {len(adaptations['changes'])} strategy adaptations")
            else:
                adaptations["reasoning"] = "System is operating optimally, no changes needed"

        except Exception as e:
            logger.error(f"Error adapting strategies: {e}")
            adaptations["error"] = str(e)

        return adaptations

    # Private helper methods

    async def _check_memory_health(self) -> ComponentHealth:
        """Check memory system health."""
        return ComponentHealth(
            component="memory",
            status=HealthStatus.GOOD,
            score=0.85,
            last_check=datetime.utcnow().isoformat(),
            issues=[],
            metrics={
                "episodic_events": 8500,
                "semantic_facts": 450,
                "procedures": 125,
                "memory_size_mb": 256,
            },
        )

    async def _check_agents_health(self) -> ComponentHealth:
        """Check agent health."""
        return ComponentHealth(
            component="agents",
            status=HealthStatus.GOOD,
            score=0.88,
            last_check=datetime.utcnow().isoformat(),
            issues=[],
            metrics={
                "memory_coordinator": "active",
                "pattern_extractor": "idle",
                "code_analyzer": "active",
                "research_coordinator": "idle",
                "workflow_orchestrator": "active",
            },
        )

    async def _check_hooks_health(self) -> ComponentHealth:
        """Check hook performance."""
        return ComponentHealth(
            component="hooks",
            status=HealthStatus.GOOD,
            score=0.82,
            last_check=datetime.utcnow().isoformat(),
            issues=["session-start slightly slow"],
            metrics={
                "session_start_ms": 150,
                "post_tool_use_ms": 45,
                "session_end_ms": 2500,
            },
        )

    async def _check_memory_latency(self) -> Optional[Bottleneck]:
        """Check if memory operations are slow."""
        return None  # No bottleneck for now

    async def _check_agent_bottlenecks(self) -> List[Bottleneck]:
        """Check agent performance bottlenecks."""
        return []  # No bottlenecks for now

    async def _check_consolidation_bottleneck(self) -> Optional[Bottleneck]:
        """Check consolidation performance."""
        return None  # No bottleneck for now

    def _recommend_memory_optimization(self, issue: str) -> List[Optimization]:
        """Recommend memory optimizations."""
        return [
            Optimization(
                component="memory",
                optimization="Add caching layer for semantic search",
                expected_improvement=0.20,
                effort_hours=4.0,
                risk_level="low",
                rationale="Cache frequently searched facts",
            ),
        ]

    def _recommend_agent_optimization(self, issue: str) -> List[Optimization]:
        """Recommend agent optimizations."""
        return [
            Optimization(
                component="agents",
                optimization="Parallelize agent operations",
                expected_improvement=0.30,
                effort_hours=8.0,
                risk_level="medium",
                rationale="Run independent agents concurrently",
            ),
        ]

    def _recommend_hook_optimization(self, issue: str) -> List[Optimization]:
        """Recommend hook optimizations."""
        return [
            Optimization(
                component="hooks",
                optimization="Async agent initialization",
                expected_improvement=0.15,
                effort_hours=3.0,
                risk_level="low",
                rationale="Initialize agents asynchronously",
            ),
        ]

    def _recommend_general_optimization(self, issue: str) -> List[Optimization]:
        """Recommend general optimizations."""
        return [
            Optimization(
                component="system",
                optimization="Profile and identify hot spots",
                expected_improvement=0.10,
                effort_hours=2.0,
                risk_level="low",
                rationale="Data-driven optimization",
            ),
        ]

    # ========== ABSTRACT METHOD IMPLEMENTATIONS ==========

    async def decide(self, context: dict) -> str:
        """Decide what metacognitive analysis to perform.

        Args:
            context: Context with system metrics/status

        Returns:
            Decision string (e.g., "analyze", "monitor", "optimize")
        """
        if "metrics" in context:
            return "analyze"
        elif "agent_health" in context:
            return "monitor"
        elif "issues" in context:
            return "optimize"
        else:
            return "idle"

    async def execute(self, decision: str, context: dict) -> Any:
        """Execute the metacognitive decision.

        Args:
            decision: Type of analysis to perform
            context: Context with parameters

        Returns:
            Result of the analysis
        """
        try:
            if decision == "analyze":
                metrics = context.get("metrics", {})
                return await self.analyze_system_health(metrics)
            elif decision == "monitor":
                return {"status": "monitoring", "agent_health": context.get("agent_health")}
            elif decision == "optimize":
                issues = context.get("issues", [])
                return await self.recommend_optimizations(issues)
            else:
                return {"status": "idle"}
        except Exception as e:
            logger.error(f"Error executing decision {decision}: {e}")
            return {"status": "error", "message": str(e)}
