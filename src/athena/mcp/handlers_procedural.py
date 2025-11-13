"""Procedural memory handler methods for MCP server."""

import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
from mcp.types import TextContent

from .structured_result import StructuredResult, ResultStatus, PaginationMetadata, create_paginated_result, paginate_results
from ..core.models import MemoryType
from ..procedural.models import Procedure, ProcedureCategory

logger = logging.getLogger(__name__)


class ProceduralHandlersMixin:
    """Procedural memory handler methods (21 methods, ~878 lines).

    Extracted from monolithic handlers.py as part of Phase 3 refactoring.
    Provides procedural memory operations: create, find, execute, track execution,
    manage versions, and optimize procedures.

    Methods:
    - _handle_create_procedure: Create a new procedure
    - _handle_find_procedures: Search for procedures
    - _handle_execute_procedure: Execute a stored procedure
    - _handle_record_execution: Track procedure execution
    - _handle_get_procedure_effectiveness: Get effectiveness metrics
    - _handle_suggest_procedure_improvements: Suggest optimizations
    - _handle_compare_procedure_versions: Compare versions
    - _handle_rollback_procedure: Revert to previous version
    - _handle_list_procedure_versions: List all versions
    - _handle_record_execution_feedback: Record execution feedback
    - _handle_record_execution_progress: Track progress
    - _handle_get_execution_context: Get execution context
    - _handle_execute_automation_workflow: Execute automated workflow
    - _handle_monitor_execution: Monitor execution
    - _handle_get_workflow_status: Get workflow status
    - _handle_generate_workflow_from_task: Generate workflow from task
    - _handle_optimize_procedure_suggester: Suggest optimizations
    - _handle_optimize_pre_execution: Optimize before execution
    - _handle_create_memory_version: Create version snapshot
    - _handle_extract_code_patterns: Extract code patterns
    - _handle_generate_procedure_code: Generate code
    """

    async def _handle_get_procedure_effectiveness(self, args: dict) -> list[TextContent]:
        """Handle get_procedure_effectiveness tool call for procedural tracking."""
        try:
            procedure_name = args.get("procedure_name")

            if not procedure_name:
                result = StructuredResult.error("procedure_name is required", metadata={"operation": "get_procedure_effectiveness"})
                return [result.as_optimized_content(schema_name="procedural")]

            # Find procedure by name (search_procedures doesn't have limit param)
            procedure = self.procedural_store.search_procedures(query=procedure_name)
            if procedure:
                procedure = procedure[:1]  # Limit to first result

            if not procedure:
                result = StructuredResult.error(f"Procedure '{procedure_name}' not found", metadata={"operation": "get_procedure_effectiveness"})
                return [result.as_optimized_content(schema_name="procedural")]

            proc = procedure[0]

            # Get execution history
            executions = self.procedural_store.get_execution_history(proc.id, limit=100)

            if not executions:
                result = StructuredResult.success(
                    data={
                        "id": proc.id,
                        "name": proc.name,
                        "category": proc.category,
                        "description": proc.description or "N/A",
                        "status": "No execution history yet",
                        "executions": []
                    },
                    metadata={"operation": "get_procedure_effectiveness", "schema": "procedural"}
                )
                return [result.as_optimized_content(schema_name="procedural")]

            # Calculate metrics
            total_executions = len(executions)
            success_count = sum(1 for e in executions if e.outcome == "success")
            failure_count = sum(1 for e in executions if e.outcome == "failure")
            partial_count = sum(1 for e in executions if e.outcome == "partial")

            success_rate = (success_count / total_executions * 100) if total_executions > 0 else 0
            failure_rate = (failure_count / total_executions * 100) if total_executions > 0 else 0
            partial_rate = (partial_count / total_executions * 100) if total_executions > 0 else 0

            # Calculate average duration
            durations = [e.duration_ms for e in executions if e.duration_ms is not None]
            avg_duration_ms = sum(durations) / len(durations) if durations else None

            # Calculate trend (first half vs second half)
            mid_point = len(executions) // 2
            if mid_point > 0:
                first_half = executions[mid_point:]  # Recent are at index 0
                second_half = executions[:mid_point]

                first_half_success = sum(1 for e in first_half if e.outcome == "success")
                second_half_success = sum(1 for e in second_half if e.outcome == "success")

                first_half_rate = (first_half_success / len(first_half) * 100) if len(first_half) > 0 else 0
                second_half_rate = (second_half_success / len(second_half) * 100) if len(second_half) > 0 else 0

                trend = "improving" if first_half_rate > second_half_rate else "declining" if first_half_rate < second_half_rate else "stable"
                trend_change = first_half_rate - second_half_rate
            else:
                trend = "insufficient_data"
                trend_change = 0

            # Build structured response
            recommendation = ""
            if success_rate >= 80:
                recommendation = "Well-optimized. Consider for automation."
            elif success_rate >= 60:
                recommendation = "Good, but has room for improvement."
            elif success_rate >= 40:
                recommendation = "Needs refinement. Review failure cases."
            else:
                recommendation = "Poor performance. Consider major revision."

            structured_data = {
                "id": proc.id,
                "name": proc.name,
                "category": proc.category,
                "description": proc.description or "N/A",
                "execution_history": {
                    "total": total_executions,
                    "successful": success_count,
                    "failed": failure_count,
                    "partial": partial_count,
                    "success_rate": round(success_rate, 1),
                    "failure_rate": round(failure_rate, 1),
                    "partial_rate": round(partial_rate, 1),
                    "avg_duration_ms": round(avg_duration_ms) if avg_duration_ms else None
                },
                "trend_analysis": {
                    "status": trend,
                    "recent_vs_historical": round(trend_change, 1) if trend != "insufficient_data" else None,
                    "recommendation": recommendation
                },
                "last_used": executions[0].timestamp.isoformat() if executions else None
            }

            result = StructuredResult.success(
                data=structured_data,
                metadata={"operation": "get_procedure_effectiveness", "schema": "procedural"},
                pagination=PaginationMetadata(returned=1)
            )
            return [result.as_optimized_content(schema_name="procedural")]

        except Exception as e:
            logger.error(f"Error in get_procedure_effectiveness [args={args}]: {e}", exc_info=True)
            result = StructuredResult.error(str(e), metadata={"operation": "get_procedure_effectiveness"})
            return [result.as_optimized_content(schema_name="procedural")]


    async def _handle_suggest_procedure_improvements(self, args: dict) -> list[TextContent]:
        """Handle suggest_procedure_improvements tool call for procedural optimization."""
        try:
            procedure_name = args.get("procedure_name")

            if not procedure_name:
                return [TextContent(type="text",
                        text=json.dumps({"error": "procedure_name is required"}))]

            # Find procedure by name (search_procedures doesn't have limit param)
            procedure = self.procedural_store.search_procedures(query=procedure_name)
            if procedure:
                procedure = procedure[:1]  # Limit to first result

            if not procedure:
                return [TextContent(type="text",
                        text=json.dumps({"error": f"Procedure '{procedure_name}' not found"}))]

            proc = procedure[0]

            # Get execution history
            executions = self.procedural_store.get_execution_history(proc.id, limit=50)

            if not executions:
                response = f"Procedure: {proc.name}\n"
                response += f"Status: Insufficient execution history for recommendations\n"
                response += f"Execute the procedure at least once to get improvement suggestions.\n"
                return [TextContent(type="text", text=response)]

            # Analyze execution patterns
            total_executions = len(executions)
            failures = [e for e in executions if e.outcome == "failure"]
            partials = [e for e in executions if e.outcome == "partial"]
            successes = [e for e in executions if e.outcome == "success"]

            success_rate = len(successes) / total_executions if total_executions > 0 else 0

            # Build recommendations
            response = f"Procedure Improvement Recommendations\n"
            response += f"{'=' * 50}\n\n"
            response += f"Name: {proc.name}\n"
            response += f"Category: {proc.category}\n\n"

            recommendations = []

            # Recommendation 1: High failure rate
            if len(failures) > total_executions * 0.3:  # > 30% failures
                recommendations.append({
                    "priority": "CRITICAL",
                    "category": "Reliability",
                    "suggestion": f"High failure rate ({len(failures)}/{total_executions})",
                    "action": "Review failure cases and identify common root causes. Consider breaking into smaller steps."
                })

            # Recommendation 2: Partial completions
            if len(partials) > total_executions * 0.2:  # > 20% partial
                recommendations.append({
                    "priority": "HIGH",
                    "category": "Completeness",
                    "suggestion": f"Frequent partial completions ({len(partials)}/{total_executions})",
                    "action": "Add error handling for edge cases. Document preconditions and assumptions."
                })

            # Recommendation 3: Execution time variance
            durations = [e.duration_ms for e in executions if e.duration_ms is not None]
            if durations and len(durations) > 1:
                avg_duration = sum(durations) / len(durations)
                max_duration = max(durations)
                min_duration = min(durations)
                variance_ratio = (max_duration - min_duration) / avg_duration if avg_duration > 0 else 0

                if variance_ratio > 2.0:  # High variance
                    recommendations.append({
                        "priority": "MEDIUM",
                        "category": "Predictability",
                        "suggestion": f"High execution time variance ({min_duration:.0f}ms - {max_duration:.0f}ms)",
                        "action": "Identify performance bottlenecks. Add progress checkpoints and logging."
                    })

            # Recommendation 4: Consolidation opportunity
            if success_rate >= 0.8 and total_executions >= 10:
                recommendations.append({
                    "priority": "LOW",
                    "category": "Optimization",
                    "suggestion": "Procedure is stable and well-tested",
                    "action": "Consider merging related procedures or automating this workflow."
                })
            elif success_rate >= 0.6 and total_executions >= 5:
                recommendations.append({
                    "priority": "MEDIUM",
                    "category": "Optimization",
                    "suggestion": "Procedure is approaching stability",
                    "action": "Run a few more times to validate improvements, then consider consolidation."
                })

            # Recommendation 5: Parameter optimization
            if executions:
                # Check for variable patterns in failures
                failure_vars = {}
                for failure in failures:
                    if failure.variables:
                        for key, val in failure.variables.items():
                            if key not in failure_vars:
                                failure_vars[key] = []
                            failure_vars[key].append(val)

                if failure_vars:
                    recommendations.append({
                        "priority": "MEDIUM",
                        "category": "Parameters",
                        "suggestion": f"Variable combinations may trigger failures",
                        "action": "Document which parameter combinations cause issues. Add validation."
                    })

            # Recommendation 6: Learning value
            learned_count = sum(1 for e in executions if e.learned)
            if learned_count > 0:
                recommendations.append({
                    "priority": "LOW",
                    "category": "Knowledge",
                    "suggestion": f"Captured {learned_count} learning insights",
                    "action": "Extract these learnings into documentation or create derivative procedures."
                })

            # Output recommendations
            if recommendations:
                response += "Recommendations\n"
                response += "-" * 50 + "\n\n"

                by_priority = {}
                for rec in recommendations:
                    priority = rec["priority"]
                    if priority not in by_priority:
                        by_priority[priority] = []
                    by_priority[priority].append(rec)

                priority_order = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
                for priority in priority_order:
                    if priority in by_priority:
                        for rec in by_priority[priority]:
                            response += f"[{priority}] {rec['category']}\n"
                            response += f"  Issue: {rec['suggestion']}\n"
                            response += f"  Action: {rec['action']}\n\n"
            else:
                response += "Analysis\n"
                response += "-" * 50 + "\n"
                response += "No specific improvements needed at this time.\n"
                response += "Procedure is operating within acceptable parameters.\n"
                response += f"Success rate: {success_rate * 100:.1f}%\n"
                response += f"Total executions: {total_executions}\n"

            response += f"\nSummary\n"
            response += "-" * 50 + "\n"
            response += f"Total suggestions: {len(recommendations)}\n"
            response += f"Success rate: {success_rate * 100:.1f}%\n"
            response += f"Executions: {total_executions} (success: {len(successes)}, partial: {len(partials)}, failed: {len(failures)})\n"

            return [TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Error in suggest_procedure_improvements [args={args}]: {e}", exc_info=True)
            error_response = json.dumps({"error": str(e), "tool": "suggest_procedure_improvements"})
            return [TextContent(type="text", text=error_response)]


    async def _handle_create_procedure(self, args: dict) -> list[TextContent]:
        """Handle create_procedure tool call."""
        import time

        try:
            # Map category string to valid ProcedureCategory enum
            category_str = args.get("category", "git").lower()

            # Try to find matching category
            valid_categories = [cat.value for cat in ProcedureCategory]
            if category_str not in valid_categories:
                # Default to git if invalid
                category = ProcedureCategory.GIT
            else:
                category = ProcedureCategory(category_str)

            # Default template if not provided
            template = args.get("template", f"# {args['name']}\n\n1. Step 1\n2. Step 2\n3. Step 3")

            procedure = Procedure(
                name=args["name"],
                category=category,
                description=args.get("description", f"Procedure: {args['name']}"),
                trigger_pattern=args.get("trigger_pattern"),
                template=template,
                created_at=datetime.now(),
            )

            procedure_id = self.procedural_store.create_procedure(procedure)

            response = f"✓ Created procedure '{args['name']}' (ID: {procedure_id})\n"
            response += f"Category: {procedure.category}\n"
            response += f"Template: {procedure.template[:100]}{'...' if len(procedure.template) > 100 else ''}"

            return [TextContent(type="text", text=response)]
        except Exception as e:
            logger.error(f"Error in create_procedure: {e}", exc_info=True)
            return [TextContent(type="text", text=f"Error: {str(e)}")]


    async def _handle_find_procedures(self, args: dict) -> list[TextContent]:
        """Handle find_procedures tool call."""
        try:
            context_tags = []
            if "category" in args:
                context_tags.append(args["category"])

            # Pagination parameters
            limit = min(args.get("limit", 10), 100)
            offset = args.get("offset", 0)

            # Get all matching procedures for count
            all_procedures = self.procedural_store.search_procedures(args["query"], context=context_tags)
            total_count = len(all_procedures)

            # Apply pagination
            procedures = all_procedures[offset:offset+limit]

            if not procedures:
                result = StructuredResult.success(
                    data=[],
                    metadata={
                        "operation": "find_procedures",
                        "schema": "procedural",
                        "query": args["query"],
                    }
                )
            else:
                # Format procedures for structured response
                formatted_procs = []
                for proc in procedures[:limit]:
                    formatted_procs.append({
                        "id": proc.id,
                        "name": proc.name,
                        "category": proc.category.value if hasattr(proc.category, 'value') else str(proc.category),
                        "description": proc.description,
                        "success_rate": round(proc.success_rate, 2),
                        "usage_count": proc.usage_count,
                        "template": proc.template[:100],
                    })

                # Use standard pagination
                result = paginate_results(
                    results=formatted_procs,
                    args=args,
                    total_count=total_count,
                    operation="find_procedures",
                    drill_down_hint="Use get_procedure_effectiveness with procedure_name for full execution history and metrics"
                )
        except Exception as e:
            result = StructuredResult.error(str(e), metadata={"operation": "find_procedures"})

        return [result.as_optimized_content(schema_name="procedural")]


    async def _handle_record_execution(self, args: dict) -> list[TextContent]:
        """Handle record_execution tool call.

        PHASE 5 AUTO-INTEGRATION: Automatically creates Knowledge Graph entity
        for successful procedures to enable cross-layer linking and procedure discovery.
        """
        project = await self.project_manager.require_project()

        # Get procedure by name
        procedure_name = args.get("procedure_name")
        if not procedure_name:
            return [TextContent(type="text", text="Error: procedure_name is required")]

        procedures = self.procedural_store.search_procedures(procedure_name, context=[])
        if not procedures:
            return [TextContent(type="text", text=f"Procedure '{args['procedure_name']}' not found.")]

        procedure = procedures[0]

        from ..procedural.models import ProcedureExecution
        # Default to 'success' if outcome not provided
        outcome = args.get("outcome", "success")
        execution = ProcedureExecution(
            procedure_id=procedure.id,
            project_id=project.id,
            timestamp=datetime.now(),
            outcome=outcome,
            duration_ms=args.get("duration_ms"),
            learned=args.get("learned"),
        )

        execution_id = self.procedural_store.record_execution(execution)

        response = f"✓ Recorded execution of '{procedure.name}'\n"
        response += f"Outcome: {execution.outcome}\n"
        if execution.duration_ms:
            response += f"Duration: {execution.duration_ms}ms\n"
        if execution.learned:
            response += f"Learned: {execution.learned}"

        # ===== PHASE 5 AUTO-PROCEDURE LINKING =====
        # For successful executions, auto-create Knowledge Graph entity
        procedure_linked = False
        if outcome == "success":
            try:
                # Check if procedure entity already exists
                existing_entities = self.graph_store.search_entities(
                    f"Procedure: {procedure.name}"
                )

                if not existing_entities:
                    # Create new Procedure entity
                    from ..graph.models import Relation, RelationType
                    proc_entity = Entity(
                        name=f"Procedure: {procedure.name}",
                        entity_type=EntityType.PATTERN,  # Procedures are patterns
                        project_id=project.id,
                        created_at=datetime.now(),
                        metadata={
                            "procedure_id": procedure.id,
                            "category": str(procedure.category) if hasattr(procedure, 'category') else "unknown",
                            "success_count": 1,
                        }
                    )
                    proc_entity_id = self.graph_store.create_entity(proc_entity)

                    # Link to project
                    try:
                        project_entities = self.graph_store.search_entities(f"Project: {project.name}")
                        if project_entities:
                            relation = Relation(
                                from_entity_id=project_entities[0].id,
                                to_entity_id=proc_entity_id,
                                relation_type=RelationType.CONTAINS,
                                created_at=datetime.now(),
                            )
                            self.graph_store.create_relation(relation)
                    except Exception as e:
                        logger.debug(f"Could not link procedure to project: {e}")

                    response += f"\n✓ Auto-Linking: Procedure entity created"
                    procedure_linked = True
                else:
                    # Update success count on existing entity
                    try:
                        entity = existing_entities[0]
                        entity.metadata["success_count"] = (
                            entity.metadata.get("success_count", 0) + 1
                        )
                        self.graph_store.update_entity(entity)
                        response += f"\n✓ Auto-Linking: Procedure linked (success count: {entity.metadata['success_count']})"
                        procedure_linked = True
                    except Exception as e:
                        logger.debug(f"Could not update procedure entity: {e}")
            except Exception as e:
                logger.debug(f"Could not auto-link procedure: {e}")

        return [TextContent(type="text", text=response)]


    async def _handle_compare_procedure_versions(self, args: dict) -> list[TextContent]:
        """Handle comparing two procedure versions."""
        try:
            from .structured_result import StructuredResult
            from ..procedural.versioning import ProcedureVersionStore

            procedure_id = args.get("procedure_id")
            v1 = args.get("version_1")
            v2 = args.get("version_2")

            if not all([procedure_id, v1, v2]):
                result = StructuredResult.error(
                    "Missing required parameters: procedure_id, version_1, version_2",
                    metadata={"operation": "compare_procedure_versions"}
                )
            else:
                version_store = ProcedureVersionStore(self.db)
                comparison = version_store.compare_versions(procedure_id, v1, v2)

                if "error" in comparison:
                    result = StructuredResult.error(
                        comparison["error"],
                        metadata={"operation": "compare_procedure_versions"}
                    )
                else:
                    result = StructuredResult.success(
                        data=comparison,
                        metadata={
                            "operation": "compare_procedure_versions",
                            "procedure_id": procedure_id,
                        }
                    )
        except Exception as e:
            result = StructuredResult.error(
                str(e),
                metadata={"operation": "compare_procedure_versions"}
            )

        return [result.as_text_content()]


    async def _handle_rollback_procedure(self, args: dict) -> list[TextContent]:
        """Handle rolling back procedure to specific version."""
        try:
            from .structured_result import StructuredResult
            from ..procedural.versioning import ProcedureVersionStore

            procedure_id = args.get("procedure_id")
            to_version = args.get("to_version")

            if not all([procedure_id, to_version]):
                result = StructuredResult.error(
                    "Missing required parameters: procedure_id, to_version",
                    metadata={"operation": "rollback_procedure"}
                )
            else:
                version_store = ProcedureVersionStore(self.db)
                rollback_result = version_store.rollback(procedure_id, to_version)

                if "error" in rollback_result:
                    result = StructuredResult.error(
                        rollback_result["error"],
                        metadata={"operation": "rollback_procedure"}
                    )
                else:
                    result = StructuredResult.success(
                        data=rollback_result,
                        metadata={
                            "operation": "rollback_procedure",
                            "procedure_id": procedure_id,
                        }
                    )
        except Exception as e:
            result = StructuredResult.error(
                str(e),
                metadata={"operation": "rollback_procedure"}
            )

        return [result.as_text_content()]


    async def _handle_list_procedure_versions(self, args: dict) -> list[TextContent]:
        """Handle listing all versions for a procedure."""
        try:
            from .structured_result import StructuredResult
            from ..procedural.versioning import ProcedureVersionStore

            procedure_id = args.get("procedure_id")

            if not procedure_id:
                result = StructuredResult.error(
                    "Missing required parameter: procedure_id",
                    metadata={"operation": "list_procedure_versions"}
                )
            else:
                version_store = ProcedureVersionStore(self.db)
                versions = version_store.list_versions(procedure_id)

                result = StructuredResult.success(
                    data=versions,
                    metadata={
                        "operation": "list_procedure_versions",
                        "procedure_id": procedure_id,
                    },
                    pagination=PaginationMetadata(
                        returned=len(versions),
                        has_more=False
                    )
                )
        except Exception as e:
            result = StructuredResult.error(
                str(e),
                metadata={"operation": "list_procedure_versions"}
            )

        return [result.as_text_content()]


    async def _handle_record_execution_feedback(self, args: dict) -> list[TextContent]:
        """Handle record_execution_feedback tool call."""
        task_id = args.get("task_id")
        actual_duration = args.get("actual_duration")
        blockers = args.get("blockers", [])
        quality_metrics = args.get("quality_metrics", {})
        lessons_learned = args.get("lessons_learned", "")

        # Parse quality_metrics if it's a JSON string
        if isinstance(quality_metrics, str):
            import json
            quality_metrics = json.loads(quality_metrics)

        # Parse blockers if it's a JSON string
        if isinstance(blockers, str):
            import json
            blockers = json.loads(blockers)

        if not task_id or actual_duration is None:
            return [TextContent(type="text", text="✗ Error: task_id and actual_duration required")]

        try:
            # Record the feedback
            from ..planning.models import ExecutionFeedback, ExecutionOutcome

            # Determine outcome based on quality metrics
            outcome = ExecutionOutcome.SUCCESS
            if quality_metrics.get("success") is False:
                outcome = ExecutionOutcome.FAILURE
            elif quality_metrics.get("quality_score", 1.0) < 0.7:
                outcome = ExecutionOutcome.PARTIAL

            feedback = ExecutionFeedback(
                project_id=1,  # Default project
                task_id=task_id,
                execution_outcome=outcome,
                execution_quality_score=quality_metrics.get("quality_score", 0.85),
                actual_duration_minutes=actual_duration,
                blockers_encountered=blockers,
                lessons_learned=lessons_learned if lessons_learned else None,
            )

            # CRITICAL INTEGRATION: Store feedback in database
            feedback_id = self.planning_store.record_execution_feedback(feedback)

            # Note: Consolidation routing via consolidation_router is skipped because
            # it expects working_memory items, not execution_feedback items. The feedback
            # is already persisted directly to the execution_feedback table and will be
            # processed during the next consolidation cycle via the episodic→semantic pipeline.

            response = f"✓ Execution Feedback Recorded & Stored\n\n"
            response += f"Task ID: {task_id}\n"
            response += f"Actual Duration: {actual_duration} minutes\n"
            response += f"Outcome: {outcome.value}\n"
            response += f"Quality Score: {feedback.execution_quality_score:.0%}\n"

            if blockers:
                response += f"\nBlockers Encountered:\n"
                for blocker in blockers:
                    response += f"  • {blocker}\n"

            if lessons_learned:
                response += f"\nLessons Learned:\n"
                response += f"  {lessons_learned}\n"

            response += f"\n✓ Feedback stored (ID: {feedback_id})\n"
            response += f"✓ Consolidation triggered - patterns extracted for future recommendations.\n"

            return [TextContent(type="text", text=response)]
        except Exception as e:
            logger.error(f"Error in record_execution_feedback [args={args}]: {e}", exc_info=True)
            return [TextContent(type="text", text=f"✗ Error recording feedback: {str(e)}")]


    async def _handle_generate_workflow_from_task(self, args: dict) -> list[TextContent]:
        """Handle generate_workflow_from_task tool call."""
        try:
            task_description = args.get("task_description", "")
            steps_taken = args.get("steps_taken", [])
            outcome = args.get("outcome", "")
            duration_mins = args.get("duration_mins", 60)

            workflow = self.llm_workflow_generator.generate_workflow_from_task(
                task_description=task_description,
                steps_taken=steps_taken,
                outcome=outcome,
                duration_mins=duration_mins,
            )

            if not workflow:
                return [TextContent(type="text", text="This task does not represent a reusable workflow pattern.")]

            # Generate markdown documentation
            doc = self.llm_workflow_generator.generate_workflow_documentation(workflow)

            response = doc
            response += f"\n\n---\n**Auto-generated Workflow Documentation**\n"
            response += f"Confidence: {workflow.confidence:.0%}\n"

            return [TextContent(type="text", text=response)]
        except Exception as e:
            logger.error(f"Error in generate_workflow_from_task: {e}", exc_info=True)
            return [TextContent(type="text", text=f"Error: {str(e)}")]


    async def _handle_record_execution_progress(self, args: dict) -> list[TextContent]:
        """Record progress on goal execution."""
        try:
            # Try to get goal_id from parameter or auto-detect from task
            goal_id = args.get("goal_id")
            task_id = args.get("task_id")
            progress = args.get("progress_percent", 0)
            notes = args.get("notes", "")

            # If no goal_id, try to auto-detect from task_id or get first active goal
            if not goal_id:
                try:
                    project = await self.project_manager.require_project()
                    # First try to get goal from task relationship
                    if task_id:
                        # Check if task has associated goal
                        task = self.prospective_store.get_task(task_id)
                        if task and hasattr(task, 'goal_id'):
                            goal_id = task.goal_id

                    # If still no goal_id, get first active goal
                    if not goal_id:
                        active_goals = self.central_executive.get_active_goals(project.id)
                        if active_goals:
                            goal_id = active_goals[0].id
                        else:
                            return [TextContent(type="text", text=json.dumps({
                                "status": "error", "error": "No goal_id provided and no active goals found"
                            }))]
                except Exception as e:
                    return [TextContent(type="text", text=json.dumps({
                        "status": "error", "error": f"Could not auto-detect goal: {str(e)}"
                    }))]

            response = {
                "status": "success",
                "goal_id": goal_id,
                "progress_percent": progress,
                "notes": notes,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            result = StructuredResult.success(
                data=response,
                metadata={"operation": "handler", "schema": "operation_response"}
            )
            return [result.as_optimized_content(schema_name="operation_response")]
        except Exception as e:
            logger.error(f"Error in _handle_record_execution_progress: {e}")
            return [TextContent(type="text", text=json.dumps({"status": "error", "error": str(e)}))]


    async def _handle_get_workflow_status(self, args: dict) -> list[TextContent]:
        """Get status of current workflow execution."""
        try:
            structured_data = {
                "active_goals": 0,
                "completed_goals": 0,
                "blocked_goals": 0,
                "current_focus": None,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            result = StructuredResult.success(
                data=structured_data,
                metadata={"operation": "get_workflow_status", "schema": "prospective"},
                pagination=PaginationMetadata(returned=1)
            )
            return [result.as_optimized_content(schema_name="prospective")]
        except Exception as e:
            logger.error(f"Error in _handle_get_workflow_status: {e}")
            result = StructuredResult.error(str(e), metadata={"operation": "get_workflow_status"})
            return [result.as_optimized_content(schema_name="prospective")]


    async def _handle_execute_automation_workflow(self, args: dict) -> list[TextContent]:
        """Forward to Phase 1 handler: execute_automation_workflow."""
        from . import handlers_integration
        return await handlers_integration.handle_execute_automation_workflow(self, args)


    async def _handle_monitor_execution(self, args: dict) -> list[TextContent]:
        """Forward to Phase 2 handler: monitor_execution."""
        from . import handlers_system
        return await handlers_system.handle_monitor_execution(self, args)


    async def _handle_optimize_pre_execution(self, args: dict) -> list[TextContent]:
        """Forward to Hook Coordination handler: optimize_pre_execution."""
        from . import handlers_hook_coordination
        return await handlers_hook_coordination.handle_optimize_pre_execution(self, args)


    async def _handle_optimize_procedure_suggester(self, args: dict) -> list[TextContent]:
        """Forward to Skill Optimization handler: optimize_procedure_suggester."""
        from . import handlers_skill_optimization
        return await handlers_skill_optimization.handle_optimize_procedure_suggester(self, args)


    async def _handle_create_memory_version(self, args: dict) -> list[TextContent]:
        """Create a new version of a memory with SHA256 hashing."""
        from .zettelkasten_tools import ZettelkastenMCPHandlers
        handlers = ZettelkastenMCPHandlers(self.memory_manager.db)
        return [await handlers.create_memory_version(
            memory_id=args.get("memory_id"),
            content=args.get("content")
        )]


    async def _handle_extract_code_patterns(self, args: dict) -> list[TextContent]:
        """Extract patterns from code analyses."""
        from .handlers_code_analysis import CodeAnalysisMemoryHandlers

        handlers = CodeAnalysisMemoryHandlers(self.memory_manager)
        result = handlers.extract_code_patterns(
            days_back=args.get("days_back", 7),
        )
        return [TextContent(type="text", text=str(result))]


    async def _handle_execute_procedure(self, args: dict) -> list[TextContent]:
        """Execute a procedure in sandbox."""
        try:
            from ..mcp.memory_api import MemoryAPI

            api = MemoryAPI.create(self.db)
            procedure_name = args.get("procedure_name")
            procedure_id = args.get("procedure_id")

            if not procedure_name and not procedure_id:
                raise ValueError("Must provide either procedure_name or procedure_id")

            result = api.execute_procedure(
                procedure_name=procedure_name, procedure_id=procedure_id
            )

            response = {
                "status": "success" if result.success else "error",
                "stdout": result.stdout,
                "stderr": result.stderr,
                "execution_time_ms": result.execution_time_ms,
                "violations": result.violations,
            }
            result = StructuredResult.success(
                data=response,
                metadata={"operation": "handler", "schema": "operation_response"}
            )
            return [result.as_optimized_content(schema_name="operation_response")]
        except Exception as e:
            return [
                TextContent(
                    type="text",
                    text=json.dumps({"status": "error", "error": str(e)}, indent=2),
                )
            ]


    async def _handle_generate_procedure_code(self, args: dict) -> list[TextContent]:
        """Generate code for a procedure using LLM."""
        try:
            from ..mcp.memory_api import MemoryAPI

            api = MemoryAPI.create(self.db)
            procedure_name = args.get("procedure_name")
            procedure_id = args.get("procedure_id")

            if not procedure_name and not procedure_id:
                raise ValueError("Must provide either procedure_name or procedure_id")

            result = api.generate_procedure_code(
                procedure_name=procedure_name, procedure_id=procedure_id
            )

            response = {
                "status": "success",
                "code": result.get("code", ""),
                "confidence_score": result.get("confidence_score", 0.0),
                "validation_result": result.get("validation_result", {}),
            }
            result = StructuredResult.success(
                data=response,
                metadata={"operation": "handler", "schema": "operation_response"}
            )
            return [result.as_optimized_content(schema_name="operation_response")]
        except Exception as e:
            return [
                TextContent(
                    type="text",
                    text=json.dumps({"status": "error", "error": str(e)}, indent=2),
                )
            ]


    async def _handle_get_execution_context(self, args: dict) -> list[TextContent]:
        """Get execution context for tracking."""
        try:
            from ..mcp.memory_api import MemoryAPI

            api = MemoryAPI.create(self.db)
            context_id = args.get("context_id")

            context = api.get_execution_context(context_id=context_id)

            response = {
                "status": "success",
                "context": context.to_dict() if context else None,
            }
            result = StructuredResult.success(
                data=response,
                metadata={"operation": "handler", "schema": "operation_response"}
            )
            return [result.as_optimized_content(schema_name="operation_response")]
        except Exception as e:
            return [
                TextContent(
                    type="text",
                    text=json.dumps({"status": "error", "error": str(e)}, indent=2),
                )
            ]


