"""MCP handlers for vibe prototyping operations."""

import logging

logger = logging.getLogger(__name__)


def register_prototyping_tools(server):
    """Register prototyping tools with MCP server.

    Args:
        server: MCP server instance
    """

    @server.tool()
    async def create_prototype(
        idea: str,
        success_criteria: list = None,
    ) -> dict:
        """Create a new vibe prototype to test an idea.

        Per "teach AI to think like a senior engineer", prototyping validates ideas before full implementation.

        Args:
            idea: Description of the idea to prototype
            success_criteria: List of success criteria for validation (optional)

        Returns:
            {
                "prototype_id": str,
                "idea": str,
                "phase": str,
                "success_criteria": [str],
                "created_at": str,
            }
        """
        try:
            from ..prototyping.prototype_engine import get_prototype_engine

            engine = get_prototype_engine()
            prototype = engine.create_prototype(
                idea,
                success_criteria=success_criteria or [],
            )

            return {
                "prototype_id": prototype.prototype_id,
                "idea": prototype.idea_description,
                "phase": prototype.phase.value,
                "success_criteria": prototype.success_criteria,
                "created_at": prototype.created_at,
            }

        except Exception as e:
            logger.error(f"Failed to create prototype: {e}")
            return {"error": f"Failed to create prototype: {str(e)}"}

    @server.tool()
    async def add_artifact(
        prototype_id: str,
        artifact_type: str,
        content: str,
        language: str = None,
    ) -> dict:
        """Add an artifact (code, design, documentation) to a prototype.

        Args:
            prototype_id: ID of the prototype
            artifact_type: Type of artifact ("code", "design", "documentation", "config")
            content: Content of the artifact
            language: Programming language (for code artifacts)

        Returns:
            {
                "artifact_id": str,
                "prototype_id": str,
                "type": str,
                "size_bytes": int,
            }
        """
        try:
            from ..prototyping.prototype_engine import get_prototype_engine

            engine = get_prototype_engine()
            artifact = engine.add_artifact(
                prototype_id,
                artifact_type,
                content,
                language=language,
            )

            return {
                "artifact_id": artifact.artifact_id,
                "prototype_id": prototype_id,
                "type": artifact.type,
                "size_bytes": artifact.size_bytes,
            }

        except ValueError as e:
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"Failed to add artifact: {e}")
            return {"error": f"Failed to add artifact: {str(e)}"}

    @server.tool()
    async def execute_prototype(
        prototype_id: str,
        context: dict = None,
    ) -> dict:
        """Execute a prototype to test if the idea works.

        Args:
            prototype_id: ID of the prototype
            context: Execution context (inputs, environment, etc.)

        Returns:
            {
                "prototype_id": str,
                "status": str,
                "success_rate": float,
                "errors": [str],
                "execution_results": dict,
            }
        """
        try:
            from ..prototyping.prototype_engine import get_prototype_engine

            engine = get_prototype_engine()
            results = await engine.execute_prototype(prototype_id, context)

            return {
                "prototype_id": prototype_id,
                "status": results.get("status"),
                "success_rate": results.get("success_rate", 0),
                "errors": results.get("errors", []),
                "execution_results": results.get("outputs", {}),
            }

        except ValueError as e:
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"Failed to execute prototype: {e}")
            return {"error": f"Failed to execute prototype: {str(e)}"}

    @server.tool()
    async def validate_prototype(
        prototype_id: str,
        check_technical: bool = True,
        check_ux: bool = True,
        check_performance: bool = False,
    ) -> dict:
        """Validate a prototype and collect feedback.

        Args:
            prototype_id: ID of the prototype
            check_technical: Check technical feasibility (default True)
            check_ux: Check user experience (default True)
            check_performance: Check performance (default False)

        Returns:
            {
                "prototype_id": str,
                "feedback": [
                    {
                        "type": str,
                        "severity": str,
                        "description": str,
                        "affects_core": bool,
                    }
                ],
                "has_blockers": bool,
                "quality_score": float,
            }
        """
        try:
            from ..prototyping.prototype_engine import get_prototype_engine

            engine = get_prototype_engine()
            feedback_list = await engine.validate_prototype(
                prototype_id,
                check_technical=check_technical,
                check_ux=check_ux,
                check_performance=check_performance,
            )

            # Count issues by severity
            critical = len([f for f in feedback_list if f.severity == "critical"])
            high = len([f for f in feedback_list if f.severity == "high"])

            # Calculate quality score
            quality_score = 1.0 - (critical * 0.3 + high * 0.1)
            quality_score = max(0, min(1, quality_score))

            return {
                "prototype_id": prototype_id,
                "total_feedback": len(feedback_list),
                "critical_issues": critical,
                "high_issues": high,
                "has_blockers": critical > 0,
                "quality_score": quality_score,
                "feedback": [
                    {
                        "type": f.type.value,
                        "severity": f.severity,
                        "description": f.description,
                        "suggested_fix": f.suggested_fix,
                        "affects_core": f.affects_core,
                    }
                    for f in feedback_list
                ],
            }

        except ValueError as e:
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"Failed to validate prototype: {e}")
            return {"error": f"Failed to validate prototype: {str(e)}"}

    @server.tool()
    async def refine_prototype(
        prototype_id: str,
        improvements: list,
    ) -> dict:
        """Refine a prototype based on validation feedback.

        Args:
            prototype_id: ID of the prototype
            improvements: List of improvements to apply

        Returns:
            {
                "prototype_id": str,
                "improvements_applied": int,
                "status": str,
            }
        """
        try:
            from ..prototyping.prototype_engine import get_prototype_engine

            engine = get_prototype_engine()
            prototype = await engine.refine_prototype(prototype_id, improvements)

            return {
                "prototype_id": prototype.prototype_id,
                "improvements_applied": len(improvements),
                "phase": prototype.phase.value,
                "status": "refined",
            }

        except ValueError as e:
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"Failed to refine prototype: {e}")
            return {"error": f"Failed to refine prototype: {str(e)}"}

    @server.tool()
    async def promote_prototype(
        prototype_id: str,
        implementation_plan: dict,
    ) -> dict:
        """Promote a validated prototype to full implementation.

        Args:
            prototype_id: ID of the prototype
            implementation_plan: Plan for full implementation

        Returns:
            {
                "prototype_id": str,
                "status": str,
                "plan": dict,
            }
        """
        try:
            from ..prototyping.prototype_engine import get_prototype_engine

            engine = get_prototype_engine()
            result = await engine.promote_to_implementation(
                prototype_id,
                implementation_plan,
            )

            return result

        except ValueError as e:
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"Failed to promote prototype: {e}")
            return {"error": f"Failed to promote prototype: {str(e)}"}

    @server.tool()
    def get_prototype(prototype_id: str) -> dict:
        """Get details about a prototype.

        Args:
            prototype_id: ID of the prototype

        Returns:
            {
                "prototype_id": str,
                "idea": str,
                "phase": str,
                "artifacts": [dict],
                "feedback": [dict],
                "execution_results": dict,
            }
        """
        try:
            from ..prototyping.prototype_engine import get_prototype_engine

            engine = get_prototype_engine()
            prototype = engine.get_prototype(prototype_id)

            if not prototype:
                return {"error": f"Prototype {prototype_id} not found"}

            return {
                "prototype_id": prototype.prototype_id,
                "idea": prototype.idea_description,
                "phase": prototype.phase.value,
                "artifacts_count": len(prototype.artifacts),
                "artifacts": [
                    {
                        "artifact_id": a.artifact_id,
                        "type": a.type,
                        "size_bytes": a.size_bytes,
                    }
                    for a in prototype.artifacts
                ],
                "feedback_count": len(prototype.feedback),
                "execution_results": prototype.execution_results,
                "created_at": prototype.created_at,
                "updated_at": prototype.updated_at,
            }

        except Exception as e:
            logger.error(f"Failed to get prototype: {e}")
            return {"error": f"Failed to get prototype: {str(e)}"}

    @server.tool()
    def list_prototypes(phase: str = None) -> dict:
        """List all prototypes, optionally filtered by phase.

        Args:
            phase: Filter by phase ("conception", "generation", "execution", "validation", "refinement", "promotion")

        Returns:
            {
                "total": int,
                "prototypes": [
                    {
                        "prototype_id": str,
                        "idea": str,
                        "phase": str,
                        "created_at": str,
                    }
                ],
            }
        """
        try:
            from ..prototyping.prototype_engine import (
                get_prototype_engine,
                PrototypePhase,
            )

            engine = get_prototype_engine()

            # Parse phase if provided
            filter_phase = None
            if phase:
                try:
                    filter_phase = PrototypePhase[phase.upper()]
                except KeyError:
                    return {
                        "error": f"Invalid phase: {phase}",
                    }

            prototypes = engine.list_prototypes(phase=filter_phase)

            return {
                "total": len(prototypes),
                "phase_filter": phase,
                "prototypes": [
                    {
                        "prototype_id": p.prototype_id,
                        "idea": p.idea_description,
                        "phase": p.phase.value,
                        "artifacts": len(p.artifacts),
                        "feedback": len(p.feedback),
                        "created_at": p.created_at,
                    }
                    for p in prototypes
                ],
            }

        except Exception as e:
            logger.error(f"Failed to list prototypes: {e}")
            return {"error": f"Failed to list prototypes: {str(e)}"}
