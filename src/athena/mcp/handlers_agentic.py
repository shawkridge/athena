"""MCP tool handlers for agentic features (verification, observability, metrics).

Exposes Phase 8 agentic patterns via MCP protocol:
- /memory-verify: Verify an operation
- /memory-health-detailed: Full system health report
- /memory-violations: Recent violations and patterns
- /memory-decisions: Decision history and insights
- /memory-recommendations: System improvement recommendations
"""

from typing import Any, Dict, List, Optional


class AgenticToolHandlers:
    """Handlers for agentic MCP tools."""

    def __init__(self, manager: "AgenticMemoryManager"):
        """Initialize with agentic manager instance."""
        self.manager = manager

    def verify_operation(
        self,
        operation_type: str,
        operation_data: Dict[str, Any],
        gate_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Verify an operation using quality gates.

        Tool: /memory-verify

        Args:
            operation_type: Type of operation ("consolidate", "remember", etc.)
            operation_data: Data to verify
            gate_types: Specific gates to run (all if None)

        Returns:
            Verification result
        """
        # Convert gate type strings to GateType enums
        from ..verification import GateType

        gate_enums = None
        if gate_types:
            gate_enums = [GateType[g.upper()] for g in gate_types]

        result = self.manager.verify_operation(operation_type, operation_data, gate_enums)

        return {
            "status": "passed" if result["passed"] else "failed",
            "confidence": round(result["confidence"], 3),
            "violations": result["violations"],
            "warnings": result.get("warnings", []),
            "execution_time_ms": round(result["execution_time_ms"], 1),
        }

    def get_system_health_detailed(self) -> Dict[str, Any]:
        """
        Get detailed system health report.

        Tool: /memory-health-detailed

        Returns:
            Comprehensive health metrics
        """
        health = self.manager.get_system_health()

        return {
            "health_score": round(health["health_score"], 2),
            "metrics": {
                "decision_accuracy": round(
                    health["metrics_summary"].get("decision_accuracy", {}).get("current", 0), 2
                ),
                "gate_pass_rate": round(
                    health["metrics_summary"].get("gate_pass_rate", {}).get("current", 0), 2
                ),
                "remediation_effectiveness": round(
                    health["metrics_summary"].get("remediation_effectiveness", {}).get("current", 0), 2
                ),
                "operation_latency_ms": round(
                    health["metrics_summary"].get("operational_efficiency", {}).get("latency_ms", 0), 1
                ),
                "violation_count": round(
                    health["metrics_summary"].get("violation_reduction", {}).get("current", 0), 1
                ),
            },
            "trends": {
                "decision_accuracy_trend": health["metrics_summary"].get("decision_accuracy", {}).get("trend", "flat"),
                "gate_pass_rate_trend": health["metrics_summary"].get("gate_pass_rate", {}).get("trend", "flat"),
            },
            "anomalies": [
                {
                    "metric": a["metric_name"],
                    "value": round(a["value"], 3),
                    "z_score": round(a["z_score"], 2),
                    "timestamp": a["timestamp"],
                }
                for a in health.get("anomalies", [])[:5]
            ],
            "alerts": health.get("alerts", []),
        }

    def get_violation_patterns(self) -> Dict[str, Any]:
        """
        Get recent violations and recurring patterns.

        Tool: /memory-violations

        Returns:
            Violation data and patterns
        """
        insights = self.manager.get_decision_insights()

        return {
            "total_violations": sum(
                len(d.get("violations", []))
                for d in insights["recent_decisions"]
            ),
            "top_patterns": [
                {
                    "gate_type": p["gate_type"],
                    "violation_type": p["violation_type"][:100],
                    "frequency": p["frequency"],
                    "recent_operations": p["example_operations"][:3],
                }
                for p in insights.get("top_violations", [])
            ],
            "gate_health": {
                gate: {
                    "success_rate": round(health["passed"] / max(1, health["total"]), 2),
                    "failure_rate": round(health["failed"] / max(1, health["total"]), 2),
                    "total_checks": health["total"],
                }
                for gate, health in insights.get("gate_health", {}).items()
            },
        }

    def get_decision_history(self, limit: int = 20) -> Dict[str, Any]:
        """
        Get decision history and insights.

        Tool: /memory-decisions

        Args:
            limit: Number of recent decisions to return

        Returns:
            Decision data
        """
        insights = self.manager.get_decision_insights()

        return {
            "total_decisions": len(insights["recent_decisions"]),
            "recent_decisions": [
                {
                    "operation_id": d["operation_id"],
                    "operation_type": d["operation_type"],
                    "action": d["action_taken"],
                    "passed": d["gate_passed"],
                    "confidence": round(d["confidence"], 2),
                    "was_correct": d.get("was_correct"),
                    "timestamp": d["timestamp"],
                }
                for d in insights["recent_decisions"][:limit]
            ],
            "operation_health": insights.get("operation_health", {}),
            "insights": insights.get("insights", []),
        }

    def get_system_recommendations(self) -> Dict[str, Any]:
        """
        Get system improvement recommendations.

        Tool: /memory-recommendations

        Returns:
            Actionable recommendations
        """
        insights = self.manager.get_decision_insights()
        health = self.manager.get_system_health()

        return {
            "health_score": round(self.manager.get_system_health()["health_score"], 2),
            "priority_actions": [
                insight
                for insight in insights.get("insights", [])
                if any(prefix in insight for prefix in ["⚠️", "🚨", "⏱️"])
            ][:3],
            "improvement_recommendations": health.get("recommendations", []),
            "gate_thresholds": {
                "grounding": "≥0.5 (source coverage)",
                "confidence": "0.3-0.95 (calibrated)",
                "consistency": "≥0.7 (memory alignment)",
                "soundness": "Q* properties verified",
                "minimality": "<10% redundancy",
                "coherence": "≥0.6 (KG connected)",
                "efficiency": "<5s per operation",
            },
        }

    def record_decision_outcome(
        self,
        decision_id: str,
        actual_outcome: str,
        was_correct: bool,
        lessons: Optional[List[str]] = None,
    ) -> Dict[str, str]:
        """
        Record the actual outcome of a decision (for feedback loop).

        Tool: /memory-record-outcome

        Args:
            decision_id: ID of the decision
            actual_outcome: What actually happened
            was_correct: Was the decision correct?
            lessons: Optional lessons learned

        Returns:
            Confirmation
        """
        self.manager.record_operation_outcome(
            decision_id,
            actual_outcome,
            was_correct,
            lessons
        )

        return {
            "status": "recorded",
            "decision_id": decision_id,
            "outcome": actual_outcome,
            "correct": str(was_correct),
            "message": f"Decision outcome recorded. System learning from {'correct' if was_correct else 'incorrect'} decision.",
        }

    def export_verification_report(self) -> str:
        """
        Export comprehensive verification report.

        Tool: /memory-export-verification

        Returns:
            JSON report
        """
        return self.manager.get_metric_report()


def register_agentic_tools(server) -> None:
    """
    Register agentic MCP tools on server.

    Args:
        server: MCP server instance
    """
    handlers = None  # Will be set by caller

    @server.tool()
    def memory_verify(
        operation_type: str,
        operation_data: dict,
        gate_types: Optional[list] = None,
    ) -> dict:
        """
        Verify an operation using quality gates.

        Runs 7 quality gates:
        - Grounding: Based on source data?
        - Confidence: Calibrated estimate?
        - Consistency: No contradictions?
        - Soundness: Valid reasoning?
        - Minimality: No redundancy?
        - Coherence: Connected to knowledge graph?
        - Efficiency: Performant?

        Args:
            operation_type: Type of operation
            operation_data: Data to verify
            gate_types: Specific gates (optional)

        Returns:
            Verification result with violations
        """
        return handlers.verify_operation(operation_type, operation_data, gate_types)

    @server.tool()
    def memory_health_detailed() -> dict:
        """
        Get detailed system health report.

        Includes:
        - Overall health score (0-1)
        - Key metrics (decision accuracy, gate pass rate, etc.)
        - Trends (improving, degrading, flat)
        - Recent anomalies
        - Active alerts

        Returns:
            Comprehensive health metrics
        """
        return handlers.get_system_health_detailed()

    @server.tool()
    def memory_violations() -> dict:
        """
        Get recent violations and recurring patterns.

        Shows:
        - Top violation types and frequency
        - Gate health (success rates)
        - Operations with most violations

        Returns:
            Violation data and patterns
        """
        return handlers.get_violation_patterns()

    @server.tool()
    def memory_decisions(limit: int = 20) -> dict:
        """
        Get decision history and insights.

        Shows:
        - Recent decisions (pass/fail, confidence)
        - Operation health (success rates by type)
        - Actionable insights

        Args:
            limit: Number of recent decisions

        Returns:
            Decision data and analysis
        """
        return handlers.get_decision_history(limit)

    @server.tool()
    def memory_recommendations() -> dict:
        """
        Get system improvement recommendations.

        Suggests:
        - Priority actions (from violations)
        - Metric improvements
        - Gate threshold adjustments

        Returns:
            Actionable recommendations
        """
        return handlers.get_system_recommendations()

    @server.tool()
    def memory_record_outcome(
        decision_id: str,
        actual_outcome: str,
        was_correct: bool,
        lessons: Optional[list] = None,
    ) -> dict:
        """
        Record actual outcome of a decision.

        Enables feedback loop learning - system learns if decisions
        were correct in hindsight.

        Args:
            decision_id: ID of the decision to record outcome for
            actual_outcome: What actually happened
            was_correct: Was the decision correct?
            lessons: Optional lessons learned

        Returns:
            Confirmation
        """
        return handlers.record_decision_outcome(
            decision_id,
            actual_outcome,
            was_correct,
            lessons
        )

    @server.tool()
    def memory_export_verification() -> str:
        """
        Export comprehensive verification report.

        Includes all metrics, trends, anomalies, alerts.

        Returns:
            JSON report
        """
        return handlers.export_verification_report()
