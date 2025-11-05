"""Phase 7.3 MCP tools for Consolidation Triggers.

Provides MCP tool handlers for Phase 7.3 integration:
- trigger_consolidation_for_session: Manually trigger consolidation
- get_consolidation_results: View consolidated patterns
- create_procedure_from_pattern: Explicit procedure creation
"""

from typing import Optional

from athena.ai_coordination.integration.consolidation_trigger import (
    ConsolidationTrigger,
    ConsolidationTriggerType,
    ConsolidationStatus,
)
from athena.ai_coordination.integration.learning_pathway import LearningPathway
from athena.ai_coordination.integration.procedure_auto_creator import ProcedureAutoCreator


class Phase73MCPTools:
    """MCP tool handlers for Phase 7.3 Consolidation Triggers."""

    def __init__(
        self,
        consolidation_trigger: ConsolidationTrigger,
        learning_pathway: LearningPathway,
        procedure_creator: ProcedureAutoCreator
    ):
        """Initialize Phase 7.3 MCP tools.

        Args:
            consolidation_trigger: ConsolidationTrigger instance
            learning_pathway: LearningPathway instance
            procedure_creator: ProcedureAutoCreator instance
        """
        self.trigger = consolidation_trigger
        self.pathway = learning_pathway
        self.creator = procedure_creator

    def trigger_consolidation_for_session(
        self,
        session_id: str,
        trigger_type: str = "session_end",
        metadata: Optional[dict] = None
    ) -> dict:
        """Manually trigger consolidation for a session.

        Initiates the learning pipeline:
        ExecutionTraces → Consolidation → SemanticPatterns → Procedures

        Args:
            session_id: Session identifier
            trigger_type: Type of trigger (session_end, event_threshold, time_based, manual)
            metadata: Optional metadata about trigger

        Returns:
            Dict with trigger results
        """
        try:
            # Check if should consolidate
            should_consolidate = self.trigger.should_consolidate(session_id)
            if not should_consolidate["should_consolidate"]:
                return {
                    "status": "skipped",
                    "session_id": session_id,
                    "reason": should_consolidate["reason"],
                }

            # Trigger consolidation
            trigger_type_enum = ConsolidationTriggerType(trigger_type)
            trigger_id = self.trigger.trigger_consolidation(
                session_id,
                trigger_type_enum,
                metadata
            )

            # Mark as started
            self.trigger.mark_consolidation_started(trigger_id)

            return {
                "status": "triggered",
                "session_id": session_id,
                "trigger_id": trigger_id,
                "trigger_type": trigger_type,
                "event_count": should_consolidate["event_count"],
            }
        except ValueError as e:
            return {
                "status": "error",
                "session_id": session_id,
                "error": f"Invalid trigger type: {e}",
            }
        except Exception as e:
            return {
                "status": "error",
                "session_id": session_id,
                "error": str(e),
            }

    def get_consolidation_results(
        self,
        session_id: str,
        include_metrics: bool = True
    ) -> dict:
        """Get consolidation results for a session.

        Args:
            session_id: Session identifier
            include_metrics: Whether to include detailed metrics

        Returns:
            Dict with consolidation results
        """
        try:
            consolidations = self.trigger.get_session_consolidations(session_id)

            result = {
                "status": "success",
                "session_id": session_id,
                "consolidation_count": len(consolidations),
                "consolidations": consolidations,
            }

            if include_metrics:
                metrics = self.trigger.get_consolidation_metrics(session_id)
                result["metrics"] = metrics

            return result
        except Exception as e:
            return {
                "status": "error",
                "session_id": session_id,
                "error": str(e),
            }

    def create_procedure_from_pattern(
        self,
        pattern_id: int,
        pattern_name: str,
        pattern_description: str,
        success_rate: float,
        lessons: list[str]
    ) -> dict:
        """Create a procedure from a consolidated pattern.

        Args:
            pattern_id: ID of source pattern
            pattern_name: Name of pattern
            pattern_description: Description
            success_rate: Success rate (0.0-1.0)
            lessons: Lessons learned

        Returns:
            Dict with procedure creation results
        """
        try:
            if success_rate < 0.0 or success_rate > 1.0:
                return {
                    "status": "error",
                    "error": "Success rate must be between 0.0 and 1.0",
                }

            procedure_id = self.creator.create_procedure_from_pattern(
                pattern_id,
                pattern_name,
                pattern_description,
                success_rate,
                lessons
            )

            if procedure_id is None:
                return {
                    "status": "skipped",
                    "pattern_id": pattern_id,
                    "reason": f"Success rate {success_rate} below minimum threshold (0.6)",
                }

            procedure = self.creator.get_procedure(procedure_id)

            return {
                "status": "success",
                "procedure_id": procedure_id,
                "procedure": procedure,
                "pattern_id": pattern_id,
            }
        except Exception as e:
            return {
                "status": "error",
                "pattern_id": pattern_id,
                "error": str(e),
            }

    def get_learning_pathways(
        self,
        session_id: str,
        status: Optional[str] = None
    ) -> dict:
        """Get learning pathways for a session.

        Args:
            session_id: Session identifier
            status: Optional filter by status

        Returns:
            Dict with pathway information
        """
        try:
            pathways = self.pathway.get_session_pathways(session_id, status)
            effectiveness = self.pathway.get_learning_effectiveness(session_id)

            return {
                "status": "success",
                "session_id": session_id,
                "pathway_count": len(pathways),
                "pathways": pathways,
                "effectiveness": effectiveness,
            }
        except Exception as e:
            return {
                "status": "error",
                "session_id": session_id,
                "error": str(e),
            }

    def record_procedure_usage(
        self,
        procedure_id: int,
        session_id: str,
        goal_id: Optional[str],
        outcome: str,
        effectiveness: Optional[float] = None
    ) -> dict:
        """Record usage of a procedure for feedback.

        Args:
            procedure_id: Procedure creation ID
            session_id: Session it was used in
            goal_id: Optional goal it helped with
            outcome: Usage outcome (success, failure, partial)
            effectiveness: Optional effectiveness rating

        Returns:
            Dict with recording results
        """
        try:
            if outcome not in ["success", "failure", "partial"]:
                return {
                    "status": "error",
                    "error": "Outcome must be 'success', 'failure', or 'partial'",
                }

            if effectiveness is not None:
                if effectiveness < 0.0 or effectiveness > 1.0:
                    return {
                        "status": "error",
                        "error": "Effectiveness must be between 0.0 and 1.0",
                    }

            usage_id = self.creator.record_procedure_usage(
                procedure_id,
                session_id,
                goal_id,
                outcome,
                effectiveness
            )

            procedure = self.creator.get_procedure(procedure_id)

            return {
                "status": "success",
                "usage_id": usage_id,
                "procedure_id": procedure_id,
                "procedure": procedure,
                "session_id": session_id,
                "outcome": outcome,
            }
        except Exception as e:
            return {
                "status": "error",
                "procedure_id": procedure_id,
                "error": str(e),
            }

    def get_procedure_metrics(self) -> dict:
        """Get overall procedure creation and usage metrics.

        Returns:
            Dict with procedure metrics
        """
        try:
            metrics = self.creator.get_creation_metrics()
            return {
                "status": "success",
                "metrics": metrics,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    def get_consolidation_status(self, trigger_id: int) -> dict:
        """Get status of a specific consolidation.

        Args:
            trigger_id: Consolidation trigger ID

        Returns:
            Dict with consolidation status
        """
        try:
            status = self.trigger.get_consolidation_status(trigger_id)
            if not status:
                return {
                    "status": "not_found",
                    "trigger_id": trigger_id,
                }

            return {
                "status": "success",
                "consolidation": status,
            }
        except Exception as e:
            return {
                "status": "error",
                "trigger_id": trigger_id,
                "error": str(e),
            }
