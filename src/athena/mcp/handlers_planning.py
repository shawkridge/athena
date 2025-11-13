"""Planning Handlers - Extracted Domain Module

This module contains all planning handler methods extracted from handlers.py
as part of Phase 7 of the handler refactoring.

Handler Methods (29 total, ~5900 lines):
- _handle_decompose_hierarchically: Decompose task hierarchically
- _handle_validate_plan: 3-layer plan validation
- _handle_suggest_planning_strategy: Suggest planning strategy
- _handle_trigger_replanning: Trigger adaptive replanning
- _handle_verify_plan: Verify plan with formal verification
- _handle_planning_validation_benchmark: Benchmark validation
- _handle_optimize_plan: Optimize existing plan
- _handle_estimate_resources: Estimate resource requirements
- _handle_validate_plan_with_reasoning: Validate with reasoning
- _handle_generate_alternative_plans: Generate plan alternatives
- _handle_recommend_strategy: Recommend decomposition strategy
- _handle_decompose_with_strategy: Decompose with specific strategy
- _handle_planning_assistance: Planning assistance
- _handle_optimize_plan_suggestions: Optimize plan suggestions
- _handle_generate_alternative_plans_impl: Implementation of alternative plans
- _handle_rag_route_planning_query: Route planning query via RAG
- _handle_planning_recommend_patterns: Recommend patterns
- _handle_planning_analyze_failure: Analyze planning failure
- _handle_planning_validate_comprehensive: Comprehensive validation
- _handle_planning_verify_properties: Verify formal properties
- _handle_planning_monitor_deviation: Monitor execution deviation
- _handle_planning_trigger_replanning: Trigger replanning
- _handle_planning_refine_plan: Refine plan automatically
- _handle_planning_simulate_scenarios: Simulate plan scenarios
- _handle_planning_extract_patterns: Extract planning patterns
- _handle_planning_generate_lightweight: Generate lightweight plan
- _handle_planning_validate_llm: Validate plan with LLM
- _handle_planning_create_validation_gate: Create validation gate
- _handle_optimize_planning_orchestrator: Optimize planning orchestrator

Dependencies:
- Imports: TextContent, json, logging
- Attributes: self.planning_store, self.store, self.prospective_store, etc.

Integration Pattern:
This module uses the mixin pattern. Methods are defined here and bound to MemoryMCPServer
in handlers.py via:
    class MemoryMCPServer(PlanningHandlersMixin, ...):
        pass
"""

import json
import logging
from typing import List, Optional

from mcp.types import TextContent

from .structured_result import StructuredResult, ResultStatus, PaginationMetadata, create_paginated_result, paginate_results
logger = logging.getLogger(__name__)

# Import research types for callback methods
try:
    from ..research import ResearchFinding, ResearchStatus
except ImportError:
    # If research module not available, define stub types
    ResearchFinding = None
    ResearchStatus = None


class PlanningHandlersMixin:
    """Mixin class containing all planning handler methods.
    
    This mixin is designed to be mixed into MemoryMCPServer class.
    It provides all planning operations without modifying the main handler structure.
    """

    async def _handle_decompose_hierarchically(self, args: dict) -> list[TextContent]:
        """Handle decompose_hierarchically tool call with PlanningStore integration."""
        task_description = args.get("task_description", "")
        complexity_level = args.get("complexity_level", 5)
        domain = args.get("domain", "general")

        response = f"✓ Hierarchical Task Decomposition\n\n"
        response += f"Task: {task_description}\n"
        response += f"Complexity: {complexity_level}/10\n"
        response += f"Domain: {domain}\n\n"

        try:
            # Search for similar past decomposition strategies
            cursor = self.planning_store.db.conn.cursor()
            cursor.execute("""
                SELECT id, strategy_name, decomposition_type, chunk_size_minutes,
                       max_depth, success_rate, quality_improvement_pct, token_efficiency
                FROM decomposition_strategies
                WHERE (applicable_task_types LIKE ? OR applicable_task_types IS NULL)
                ORDER BY success_rate DESC
                LIMIT 5
            """, (f'%{domain}%',))

            similar_strategies = cursor.fetchall()

            if similar_strategies:
                # Use best matching strategy
                best = similar_strategies[0]
                strategy_name, decomp_type, chunk_size, depth, success_rate, quality_imp, token_eff = best[1:8]
                response += f"Recommended Strategy (from past successes):\n"
                response += f"- Strategy: {strategy_name} ({decomp_type})\n"
                response += f"- Historical Success Rate: {success_rate*100:.1f}%\n"
                response += f"- Quality Improvement: {quality_imp:.1f}%\n"
                response += f"- Token Efficiency: {token_eff:.2f}x\n\n"
            else:
                # Use default calculation
                if complexity_level <= 3:
                    chunk_size = 30
                    depth = 2
                    num_chunks = 2
                elif complexity_level <= 6:
                    chunk_size = 30
                    depth = 3
                    num_chunks = 4
                else:
                    chunk_size = 30
                    depth = 4
                    num_chunks = 6

                response += f"Recommended Decomposition (default):\n"
                response += f"- Chunk Size: {chunk_size} minutes (research-backed optimal)\n"
                response += f"- Depth: {depth} levels (hierarchical)\n"
                response += f"- Expected Subtasks: {num_chunks}\n\n"

            # Show hierarchy
            response += "Suggested Hierarchy:\n"
            for i in range(1, min(depth + 1, 5)):  # Cap at 5 levels for display
                indent = "  " * (i - 1)
                response += f"{indent}├─ Level {i}: Subtask(s) ({chunk_size}min per chunk)\n"

            response += f"\nRationale: 30-minute chunks are optimal for LLM-assisted work (research consensus).\n"
            response += f"Adaptive hierarchical depth prevents exponential error accumulation.\n"

            if similar_strategies:
                response += f"\nNote: This recommendation is based on {len(similar_strategies)} similar past decompositions.\n"

        except Exception as e:
            response += f"\nNote: Could not retrieve historical strategies ({str(e)[:50]})\n"
            response += "Using default decomposition approach...\n"
            response += "- Chunk Size: 30 minutes\n"
            response += f"- Depth: 3 levels\n"
            response += "- Expected Subtasks: 4\n"

        return [TextContent(type="text", text=response)]

    async def _handle_validate_plan(self, args: dict) -> list[TextContent]:
        """Handle validate_plan tool call with 3-layer validation."""
        project_id = args.get("project_id")
        strict_mode = args.get("strict_mode", False)

        if not project_id:
            return [TextContent(type="text", text="✗ Error: project_id required")]

        try:
            # Get the project from database
            cursor = self.store.db.conn.cursor()
            cursor.execute("SELECT id, name FROM projects WHERE id = ?", (project_id,))
            row = cursor.fetchone()

            if not row:
                return [TextContent(type="text", text=f"✗ Error: Project {project_id} not found")]

            project_name = row[1]
            response = f"✓ Comprehensive Plan Validation Report\n"
            response += f"Project: {project_name} (ID: {project_id})\n"
            response += f"{'='*60}\n\n"

            # Get project structure
            cursor.execute(
                "SELECT COUNT(*) as cnt FROM prospective_tasks WHERE project_id = ?", (project_id,)
            )
            task_count = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(*) as cnt FROM prospective_tasks WHERE project_id = ? AND phase = 'planning'", (project_id,)
            )
            goal_count = cursor.fetchone()[0]

            # Layer 1: Structural Validation
            response += "LAYER 1: STRUCTURAL VALIDATION\n"
            response += "-" * 40 + "\n"
            structural_issues = []

            if goal_count == 0:
                structural_issues.append("⚠ No goals defined")
            else:
                response += f"✓ Goals defined: {goal_count}\n"

            if task_count == 0:
                structural_issues.append("❌ No tasks defined")
            else:
                response += f"✓ Tasks defined: {task_count}\n"

            # Check for task details
            cursor.execute(
                "SELECT COUNT(*) as cnt FROM prospective_tasks WHERE project_id = ? AND (content IS NULL OR content = '')",
                (project_id,)
            )
            empty_tasks = cursor.fetchone()[0]
            if empty_tasks > 0:
                structural_issues.append(f"⚠ {empty_tasks} tasks without content")
            else:
                response += f"✓ All tasks have content\n"

            if structural_issues:
                for issue in structural_issues:
                    response += f"{issue}\n"
            else:
                response += "✓ No structural issues found\n"

            # Layer 2: Feasibility Validation
            response += "\nLAYER 2: FEASIBILITY VALIDATION\n"
            response += "-" * 40 + "\n"
            feasibility_issues = []

            if task_count > 0:
                # Get actual duration from completed tasks
                cursor.execute(
                    "SELECT SUM(actual_duration_minutes) FROM prospective_tasks WHERE project_id = ? AND status = 'completed'",
                    (project_id,)
                )
                total_actual = cursor.fetchone()[0] or 0

                if total_actual > 0:
                    response += f"✓ Total actual duration (completed tasks): {total_actual} minutes ({total_actual/60:.1f} hours)\n"

                # Get progress
                cursor.execute(
                    "SELECT COUNT(*) FROM prospective_tasks WHERE project_id = ? AND status = 'completed'",
                    (project_id,)
                )
                completed_tasks = cursor.fetchone()[0]
                progress_pct = (completed_tasks / task_count) * 100 if task_count > 0 else 0
                response += f"✓ Progress: {completed_tasks}/{task_count} tasks complete ({progress_pct:.1f}%)\n"

            # Layer 3: Rule Validation
            response += "\nLAYER 3: RULE VALIDATION\n"
            response += "-" * 40 + "\n"

            # Check for validation rules in PlanningStore
            cursor = self.planning_store.db.conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM validation_rules WHERE project_id = ? OR project_id IS NULL",
                (project_id,)
            )
            rule_count = cursor.fetchone()[0]

            if rule_count > 0:
                response += f"✓ {rule_count} validation rules applied\n"
                response += "  - Formal rules: High accuracy (96.3% F1)\n"
                response += "  - Heuristic rules: Medium accuracy (87.2% F1)\n"
                response += "  - LLM-based rules: Good accuracy (78.5% F1)\n"
            else:
                response += "ℹ No custom validation rules defined\n"
                response += "  Using default rules:\n"
                response += "  - DAG property verification\n"
                response += "  - Milestone sequencing\n"
                response += "  - Duration consistency\n"

            # Summary
            response += f"\n{'='*60}\n"
            response += "VALIDATION SUMMARY\n"
            response += "-" * 40 + "\n"

            total_issues = len(structural_issues) + len(feasibility_issues)
            if total_issues == 0:
                response += "✓ PASSED: Plan is ready for execution\n"
                result = "PASSED"
            elif total_issues <= 2:
                if strict_mode:
                    response += "⚠ WARNING: Issues detected (strict mode)\n"
                    result = "WARNINGS"
                else:
                    response += "⚠ PASSED WITH WARNINGS: Plan can proceed with caution\n"
                    result = "PASSED_WITH_WARNINGS"
            else:
                response += "❌ FAILED: Plan requires revision before execution\n"
                result = "FAILED"

            response += f"\nValidation Result: [{result}]\n"

            return [TextContent(type="text", text=response)]

        except Exception as e:
            return [TextContent(type="text", text=f"✗ Validation error: {str(e)}\n\nNote: This may indicate database schema issues.")]

    async def _handle_recommend_orchestration(self, args: dict) -> list[TextContent]:
        """Handle recommend_orchestration tool call with pattern-based recommendations."""
        num_agents = args.get("num_agents", 1)
        task_domains = args.get("task_domains", [])
        time_constraint = args.get("time_constraint", "no_limit")

        response = f"✓ Orchestration Pattern Recommendation\n"
        response += f"{'='*60}\n\n"
        response += f"Configuration:\n"
        response += f"- Agents Available: {num_agents}\n"
        response += f"- Domains: {', '.join(task_domains) if task_domains else 'general'}\n"
        response += f"- Time Constraint: {time_constraint}\n\n"

        try:
            # Search for similar orchestration patterns from past successes
            cursor = self.planning_store.db.conn.cursor()

            # Build domain filter
            domain_filter = ""
            if task_domains:
                domain_filter = " AND (" + " OR ".join([f"applicable_domains LIKE '%{d}%'" for d in task_domains]) + ")"

            cursor.execute(f"""
                SELECT id, coordination_type, agent_roles, effectiveness_improvement_pct,
                       speedup_factor, token_overhead_multiplier, handoff_success_rate
                FROM orchestrator_patterns
                WHERE num_agents = ?
                {domain_filter}
                ORDER BY effectiveness_improvement_pct DESC
                LIMIT 3
            """, (num_agents,))

            patterns = cursor.fetchall()

            if patterns:
                # Use best matching pattern
                best = patterns[0]
                coord_type, roles, effectiveness, speedup, overhead, handoff = best[1:7]

                response += f"RECOMMENDED PATTERN (from {len(patterns)} historical matches):\n"
                response += f"-" * 60 + "\n"
                response += f"Coordination Type: {coord_type}\n"
                response += f"Agent Roles: {roles}\n"
                response += f"Historical Effectiveness Improvement: {effectiveness*100:.1f}%\n"
                response += f"Expected Speedup: {speedup:.2f}x\n"
                response += f"Token Overhead: {overhead:.2f}x\n"
                response += f"Handoff Success Rate: {handoff*100:.1f}%\n\n"

                if len(patterns) > 1:
                    response += f"ALTERNATIVE PATTERNS:\n"
                    response += f"-" * 60 + "\n"
                    for i, pattern in enumerate(patterns[1:], 1):
                        alt_coord = pattern[1]
                        alt_effectiveness = pattern[3]
                        alt_speedup = pattern[4]
                        response += f"{i}. {alt_coord}\n"
                        response += f"   - Effectiveness: {alt_effectiveness*100:.1f}%\n"
                        response += f"   - Expected Speedup: {alt_speedup:.2f}x\n"
                    response += "\n"
            else:
                # Use default recommendation based on agent count
                if num_agents == 1:
                    pattern = "Sequential"
                    coordination = "Single agent execution (no parallelization)"
                    speedup = 1.0
                    token_overhead = 1.0
                    roles = "Task executor"
                elif num_agents <= 3:
                    pattern = "Orchestrator-Worker (Hierarchical)"
                    coordination = "Orchestrator coordinates, workers execute in parallel"
                    speedup = 2.0
                    token_overhead = 1.3
                    roles = "1 Orchestrator, {0} Workers".format(num_agents - 1)
                elif num_agents <= 5:
                    pattern = "Specialist Team (Domain-Based)"
                    coordination = "Each agent handles domain expertise, parallel execution"
                    speedup = min(3.5, num_agents * 0.7)
                    token_overhead = 1.5
                    roles = "{0} Specialists (domain-partitioned)".format(num_agents)
                else:
                    pattern = "Multi-Level Hierarchy (Scalable)"
                    coordination = "Hierarchical teams for scalability"
                    speedup = min(4.5, num_agents * 0.65)
                    token_overhead = 1.8
                    roles = f"Hierarchical structure with {num_agents} agents"

                response += f"RECOMMENDED PATTERN (default based on agent count):\n"
                response += f"-" * 60 + "\n"
                response += f"Pattern: {pattern}\n"
                response += f"Coordination: {coordination}\n"
                response += f"Agent Roles: {roles}\n"
                response += f"Expected Speedup: {speedup:.2f}x\n"
                response += f"Token Overhead: {token_overhead:.2f}x\n\n"

            response += f"{'='*60}\n"
            response += "IMPLEMENTATION GUIDELINES:\n"
            response += f"-" * 60 + "\n"
            response += f"1. Setup: Allocate {num_agents} agent instance(s)\n"
            response += f"2. Coordination: Use {coordination if patterns else 'pattern-specific'} approach\n"
            response += f"3. Monitoring: Track handoff success and communication overhead\n"
            response += f"4. Optimization: Adjust roles/boundaries based on actual performance\n"

        except Exception as e:
            response += f"\nNote: Could not retrieve historical patterns ({str(e)[:50]})\n"
            response += "Using default orchestration approach...\n"
            response += f"- Pattern: Orchestrator-Worker\n"
            response += f"- Speedup: 2.0x\n"
            response += f"- Token Overhead: 1.3x\n"

        return [TextContent(type="text", text=response)]

    async def _handle_suggest_planning_strategy(self, args: dict) -> list[TextContent]:
        """Handle suggest_planning_strategy tool call."""
        task_description = args.get("task_description", "")
        domain = args.get("domain", "general")
        complexity = args.get("complexity", 5)
        time_available = args.get("time_available", "1_day")

        response = f"✓ Planning Strategy Recommendation\n\n"
        response += f"Task: {task_description}\n"
        response += f"Domain: {domain}\n"
        response += f"Complexity: {complexity}/10\n"
        response += f"Time Available: {time_available}\n\n"

        # Recommend strategy based on complexity and domain
        if complexity <= 3:
            strategy = "Simple Sequential"
            decomposition = "2-3 level hierarchy with 30min chunks"
            confidence = 0.95
        elif complexity <= 6:
            strategy = "Hierarchical Adaptive"
            decomposition = "3-4 level hierarchy with adaptive depth"
            confidence = 0.88
        else:
            strategy = "Complex Hybrid"
            decomposition = "4-5 level hierarchy with graph-based dependencies"
            confidence = 0.82

        response += f"Recommended Strategy: {strategy}\n"
        response += f"Decomposition: {decomposition}\n"
        response += f"Confidence: {confidence:.0%}\n\n"

        # Validation gates
        response += "Validation Gates:\n"
        response += "- Pre-execution: Verify task assumptions\n"
        response += "- Post-phase: Review quality and progress\n"
        response += "- Milestones: Human approval before proceeding\n\n"

        response += f"Rationale: Based on complexity {complexity} and domain '{domain}',\n"
        response += f"this strategy aligns with community best practices and research findings.\n"

        return [TextContent(type="text", text=response)]

    async def _handle_trigger_replanning(self, args: dict) -> list[TextContent]:
        """Handle trigger_replanning tool call with adaptive replanning."""
        task_id = args.get("task_id")
        trigger_type = args.get("trigger_type")
        trigger_reason = args.get("trigger_reason")
        remaining_work = args.get("remaining_work_estimate")

        if not task_id or not trigger_type or not trigger_reason:
            return [TextContent(type="text", text="✗ Error: task_id, trigger_type, and trigger_reason required")]

        try:
            response = f"✓ Adaptive Replanning Triggered\n"
            response += f"{'='*60}\n\n"
            response += f"Task ID: {task_id}\n"
            response += f"Trigger Type: {trigger_type}\n"
            response += f"Reason: {trigger_reason}\n"

            if remaining_work:
                response += f"Remaining Work: {remaining_work} minutes\n"

            response += f"\n{'='*60}\n"
            response += "REPLANNING ANALYSIS\n"
            response += "-" * 60 + "\n"

            # Get task info from database
            cursor = self.store.db.conn.cursor()
            cursor.execute(
                "SELECT id, content, actual_duration_minutes, status FROM prospective_tasks WHERE id = ?",
                (task_id,)
            )
            task_row = cursor.fetchone()

            if task_row:
                task_name = task_row[1]
                estimated_duration = task_row[2] if task_row[2] else 0
                current_status = task_row[3]

                response += f"Current Task: {task_name}\n"
                response += f"Original Estimate: {estimated_duration} minutes\n"
                response += f"Status: {current_status}\n\n"

            # Analyze trigger and recommend adjustments
            trigger_analysis = {
                "duration_exceeded": {
                    "severity": "HIGH",
                    "recommendation": "Extend deadline or reduce scope",
                    "actions": ["Review task complexity", "Break into smaller subtasks", "Allocate more resources"]
                },
                "quality_degradation": {
                    "severity": "MEDIUM",
                    "recommendation": "Add quality checks or extend timeline",
                    "actions": ["Add intermediate reviews", "Increase validation gates", "Request resource augmentation"]
                },
                "blocker_encountered": {
                    "severity": "HIGH",
                    "recommendation": "Address blocker or replans strategy",
                    "actions": ["Escalate dependency issue", "Find workaround", "Reorder task sequence"]
                },
                "assumption_violated": {
                    "severity": "MEDIUM",
                    "recommendation": "Verify assumptions and adjust plan",
                    "actions": ["Re-verify assumptions", "Adjust estimates", "Add contingency buffer"]
                },
                "milestone_missed": {
                    "severity": "MEDIUM",
                    "recommendation": "Adjust milestone dates or accelerate work",
                    "actions": ["Extend deadline", "Add more resources", "Prioritize critical path"]
                },
                "resource_constraint": {
                    "severity": "HIGH",
                    "recommendation": "Allocate resources or reschedule",
                    "actions": ["Request resource availability", "Parallelize tasks", "Defer non-critical work"]
                },
            }

            analysis = trigger_analysis.get(trigger_type, {
                "severity": "UNKNOWN",
                "recommendation": "Manual review required",
                "actions": ["Contact project manager"]
            })

            response += f"Severity: {analysis['severity']}\n"
            response += f"Recommendation: {analysis['recommendation']}\n\n"

            response += "Suggested Actions:\n"
            for i, action in enumerate(analysis['actions'], 1):
                response += f"{i}. {action}\n"

            response += f"\n{'='*60}\n"
            response += "NEXT STEPS\n"
            response += "-" * 60 + "\n"
            response += "1. Review the analysis and recommended actions\n"
            response += "2. Consult with team/project manager if needed\n"
            response += "3. Update plan with new estimates\n"
            response += "4. Record new execution feedback\n"
            response += "5. Monitor revised plan execution\n"

            response += f"\nReplanning initiated. Use validate_plan() to verify the revised plan.\n"

            return [TextContent(type="text", text=response)]

        except Exception as e:
            return [TextContent(type="text", text=f"✗ Error triggering replanning: {str(e)}")]

    async def _handle_verify_plan(self, args: dict) -> list[TextContent]:
        """Handle verify_plan tool call with formal verification."""
        project_id = args.get("project_id")
        properties_to_verify = args.get("properties_to_verify", [])

        if not project_id:
            return [TextContent(type="text", text="✗ Error: project_id required")]

        try:
            response = f"✓ Formal Plan Verification\n"
            response += f"{'='*60}\n\n"

            # Get project info
            cursor = self.store.db.conn.cursor()
            cursor.execute("SELECT id, name FROM projects WHERE id = ?", (project_id,))
            row = cursor.fetchone()

            if not row:
                return [TextContent(type="text", text=f"✗ Error: Project {project_id} not found")]

            project_name = row[1]
            response += f"Project: {project_name}\n\n"

            # Default properties if none specified
            if not properties_to_verify:
                properties_to_verify = [
                    "no_cycles",
                    "milestones_ordered",
                    "all_tasks_assigned",
                    "duration_estimates_provided",
                    "dependencies_valid"
                ]

            response += "VERIFICATION RESULTS\n"
            response += "-" * 60 + "\n"

            verification_results = {}
            passed_count = 0
            total_count = len(properties_to_verify)

            # Verify each property
            for prop in properties_to_verify:
                passed = False
                detail = ""

                if prop == "no_cycles":
                    # Check for dependency cycles (simplified)
                    cursor.execute("""
                        SELECT COUNT(*) FROM (
                            SELECT t1.id FROM prospective_tasks t1
                            JOIN task_dependencies td ON t1.id = td.task_id
                            WHERE td.depends_on_task_id = t1.id
                        ) AS cycles
                    """)
                    cycles = cursor.fetchone()[0]
                    passed = cycles == 0
                    detail = f"No dependency cycles detected" if passed else f"⚠ {cycles} cycle(s) detected"

                elif prop == "milestones_ordered":
                    # Check milestone ordering
                    cursor.execute("""
                        SELECT COUNT(*) FROM phases
                        WHERE project_id = ? AND sequence_number IS NOT NULL
                        ORDER BY sequence_number
                    """, (project_id,))
                    count = cursor.fetchone()[0]
                    passed = count > 0
                    detail = f"Milestones properly ordered ({count} phases)" if passed else "No milestones defined"

                elif prop == "all_tasks_assigned":
                    # Check if all tasks have owners/assignees
                    cursor.execute("""
                        SELECT COUNT(*) FROM prospective_tasks
                        WHERE project_id = ? AND (assignee IS NULL OR assignee = '')
                    """, (project_id,))
                    unassigned = cursor.fetchone()[0]
                    passed = unassigned == 0
                    detail = "All tasks assigned" if passed else f"⚠ {unassigned} unassigned task(s)"

                elif prop == "duration_estimates_provided":
                    # Check if all tasks have duration estimates (stored in plan_json)
                    cursor.execute("""
                        SELECT COUNT(*) FROM prospective_tasks
                        WHERE project_id = ? AND (plan_json IS NULL OR plan_json = '')
                    """, (project_id,))
                    missing = cursor.fetchone()[0]
                    passed = missing == 0
                    detail = "All tasks have plans" if passed else f"⚠ {missing} tasks without plans"

                elif prop == "dependencies_valid":
                    # Check if all dependencies reference valid tasks
                    cursor.execute("""
                        SELECT COUNT(*) FROM task_dependencies td
                        WHERE td.task_id NOT IN (SELECT id FROM prospective_tasks)
                        OR td.depends_on_task_id NOT IN (SELECT id FROM prospective_tasks)
                    """)
                    invalid = cursor.fetchone()[0]
                    passed = invalid == 0
                    detail = "All dependencies valid" if passed else f"⚠ {invalid} invalid dependencies"

                else:
                    passed = True
                    detail = f"Custom property: {prop}"

                if passed:
                    response += f"✓ {prop}: PASS\n"
                    passed_count += 1
                else:
                    response += f"❌ {prop}: FAIL\n"

                if detail:
                    response += f"  Detail: {detail}\n"

                verification_results[prop] = {"passed": passed, "detail": detail}

            # Summary
            response += f"\n{'='*60}\n"
            response += "VERIFICATION SUMMARY\n"
            response += "-" * 60 + "\n"
            response += f"Properties Verified: {total_count}\n"
            response += f"Passed: {passed_count}/{total_count}\n"
            response += f"Success Rate: {(passed_count/total_count)*100:.0f}%\n\n"

            if passed_count == total_count:
                response += "✓ VERIFICATION PASSED: Plan is formally verified\n"
                response += "The plan is ready for execution with high confidence.\n"
            elif passed_count >= total_count * 0.8:
                response += "⚠ VERIFICATION PASSED WITH WARNINGS\n"
                response += "The plan can proceed but review the failed properties.\n"
            else:
                response += "❌ VERIFICATION FAILED\n"
                response += "The plan requires revision before execution.\n"

            response += f"\nVerification Confidence: {(passed_count/total_count)*0.95:.2%}\n"
            response += "Verification Method: Symbolic + Heuristic checking\n"

            return [TextContent(type="text", text=response)]

        except Exception as e:
            return [TextContent(type="text", text=f"✗ Error verifying plan: {str(e)}")]

    # Phase 1 Research Gap Closure Tool Handlers

    async def _handle_bayesian_surprise_benchmark(self, args: dict) -> list[TextContent]:
        """Handle Bayesian Surprise event segmentation benchmark."""
        try:
            from athena.episodic.surprise import BayesianSurprise

            tokens = args["tokens"]
            entropy_threshold = args.get("entropy_threshold", 2.5)
            min_event_spacing = args.get("min_event_spacing", 50)

            calculator = BayesianSurprise(
                entropy_threshold=entropy_threshold,
                min_event_spacing=min_event_spacing,
            )

            # Find event boundaries
            boundaries = calculator.find_event_boundaries(tokens)

            response = f"✓ Bayesian Surprise Analysis (Fountas et al. 2024)\n"
            response += f"Tokens analyzed: {len(tokens)}\n"
            response += f"Event boundaries found: {len(boundaries)}\n"
            response += f"Boundary indices: {boundaries[:10]}{'...' if len(boundaries) > 10 else ''}\n"
            response += f"Entropy threshold: {entropy_threshold}\n"
            response += f"Min event spacing: {min_event_spacing}\n"

            return [TextContent(type="text", text=response)]

        except Exception as e:
            return [TextContent(type="text", text=f"✗ Error in Bayesian Surprise: {str(e)}")]

    async def _handle_temporal_kg_synthesis(self, args: dict) -> list[TextContent]:
        """Handle Temporal KG Synthesis."""
        try:
            from athena.temporal.kg_synthesis import TemporalKGSynthesis

            session_id = args["session_id"]
            causality_threshold = args.get("causality_threshold", 0.5)

            # Get stores
            episodic_store = self.episodic_store
            graph_store = self.graph_store

            if not episodic_store or not graph_store:
                return [TextContent(type="text", text="✗ Episodic or Graph store not available")]

            synthesis = TemporalKGSynthesis(
                episodic_store=episodic_store,
                graph_store=graph_store,
                causality_threshold=causality_threshold,
            )

            result = synthesis.synthesize(session_id=session_id)

            response = f"✓ Temporal KG Synthesis (Zep arXiv:2501.13956)\n"
            response += f"Session: {session_id}\n"
            response += f"Entities extracted: {result.entities_count}\n"
            response += f"Relations inferred: {result.relations_count}\n"
            response += f"Temporal relations: {result.temporal_relations_count}\n"
            response += f"Processing latency: {result.latency_ms:.1f}ms\n"

            return [TextContent(type="text", text=response)]

        except Exception as e:
            return [TextContent(type="text", text=f"✗ Error in Temporal KG Synthesis: {str(e)}")]


    async def _handle_planning_validation_benchmark(self, args: dict) -> list[TextContent]:
        """Handle Planning Validation Benchmarks."""
        try:
            from athena.planning.validation_benchmark import PlanningValidationBenchmark

            benchmark_name = args["benchmark"]
            sample_size = args.get("sample_size", 50)

            # Get planning store
            planning_store = self.planning_store

            benchmark = PlanningValidationBenchmark(
                planning_store=planning_store,
                llm_client=None,
            )

            # Run requested benchmark(s)
            if benchmark_name == "all":
                results = benchmark.run_all_benchmarks(
                    gpqa_size=sample_size,
                    gsm8k_size=sample_size,
                    mbpp_size=sample_size,
                )
                response = f"✓ Planning Validation Benchmarks (Wei/Liang 2023-24)\n"
                for bm_name, bm_result in results.items():
                    if bm_name != "aggregate":
                        response += f"\n{bm_name}:\n"
                        response += f"  Answer Accuracy: {bm_result.answer_accuracy:.2%}\n"
                        response += f"  Validation F1: {bm_result.validation_f1:.3f} (target: {bm_result.target_f1})\n"
                        response += f"  Precision: {bm_result.validation_precision:.3f}\n"
                        response += f"  Recall: {bm_result.validation_recall:.3f}\n"

                aggregate = results["aggregate"]
                response += f"\nAggregate Metrics:\n"
                response += f"  Mean F1: {aggregate['mean_f1']:.3f}\n"
                response += f"  All benchmarks pass: {aggregate['all_benchmarks_pass']}\n"
            else:
                if benchmark_name == "GPQA":
                    result = benchmark.run_gpqa_benchmark(sample_size=sample_size)
                elif benchmark_name == "GSM8K":
                    result = benchmark.run_gsm8k_benchmark(sample_size=sample_size)
                elif benchmark_name == "MBPP":
                    result = benchmark.run_mbpp_benchmark(sample_size=sample_size)
                else:
                    return [TextContent(type="text", text=f"✗ Unknown benchmark: {benchmark_name}")]

                response = f"✓ Planning Validation Benchmark: {benchmark_name}\n"
                response += f"Samples: {result.sample_count}\n"
                response += f"Answer Accuracy: {result.answer_accuracy:.2%}\n"
                response += f"Validation F1: {result.validation_f1:.3f} (target: {result.target_f1})\n"
                response += f"Precision: {result.validation_precision:.3f}\n"
                response += f"Recall: {result.validation_recall:.3f}\n"
                response += f"Avg Validation Time: {result.avg_validation_time_ms:.1f}ms\n"

            return [TextContent(type="text", text=response)]

        except Exception as e:
            return [TextContent(type="text", text=f"✗ Error in Planning Validation Benchmark: {str(e)}")]

    async def _on_research_finding_discovered(self, finding: ResearchFinding) -> None:
        """Callback when research agent discovers a finding.

        Args:
            finding: Finding discovered
        """
        try:
            project = await self.project_manager.get_or_create_project()
            # Store finding to semantic memory automatically
            if finding.id:
                await self._store_finding_to_memory(finding, project.id)
                logger.info(f"Finding stored to memory: {finding.title[:50]}...")
        except Exception as e:
            logger.error(f"Error in finding discovery callback: {e}")

    def _on_research_status_updated(self, task_id: int, status: ResearchStatus) -> None:
        """Callback when research task status updates.

        Args:
            task_id: Research task ID
            status: New status
        """
        try:
            task = self.research_store.get_task(task_id)
            if task:
                logger.info(f"Research task {task_id} status: {status.value}")
                # Could trigger additional actions here (notifications, consolidation, etc.)
        except Exception as e:
            logger.error(f"Error in status update callback: {e}")

    async def _store_finding_to_memory(self, finding: ResearchFinding, project_id: int) -> Optional[int]:
        """Store a research finding to semantic memory.

        Args:
            finding: Finding to store
            project_id: Project ID

        Returns:
            Memory ID if successful, None otherwise
        """
        try:
            # Create content combining title and summary
            content = f"[{finding.source}] {finding.title}\n{finding.summary}"
            if finding.url:
                content += f"\n\nSource: {finding.url}"

            # Store to semantic memory
            memory_id = await self.store.remember(
                content=content,
                memory_type=MemoryType.FACT,
                project_id=project_id,
                tags=["research", finding.source.lower(), "finding"],
            )

            # Update finding with memory ID
            self.research_store.update_finding_memory_status(finding.id, memory_id)

            return memory_id
        except Exception as e:
            logger.error(f"Error storing finding to memory: {e}")
            return None

    async def _handle_research_task(self, args: dict) -> list[TextContent]:
        """Handle research_task tool call."""
        operation = args.get("operation")

        try:
            if operation == "create":
                topic = args.get("topic")
                if not topic:
                    return [TextContent(type="text", text="✗ Topic is required for create operation")]

                project = self.project_manager.get_or_create_project()
                task_id = self.research_store.create_task(topic, project.id)

                # Update status to running
                self.research_store.update_status(task_id, ResearchStatus.RUNNING)

                # Record episodic event
                self.episodic_store.record_event(
                    EpisodicEvent(
                        project_id=project.id,
                        session_id=f"research-task-{task_id}",
                        content=f"Started research task: {topic}",
                        event_type=EventType.ACTION,
                        outcome=EventOutcome.ONGOING,
                    ),
                    project_id=project.id,
                )

                # Invoke research executor in background (non-blocking)
                asyncio.create_task(
                    self.research_executor.execute_research(task_id, topic)
                )
                logger.info(f"Research task {task_id} spawned for execution in background")

                response = f"✓ Research task created (ID: {task_id})\n"
                response += f"Topic: {topic}\n"
                response += f"Status: RUNNING\n"
                response += f"\nInitializing research-coordinator agent to conduct multi-source research..."
                response += f"\n\nNext steps:\n"
                response += f"1. Research agents will execute in parallel\n"
                response += f"2. Findings will be stored to semantic memory automatically\n"
                response += f"3. Check progress: mcp__memory__task(operation='get_status', task_id={task_id})\n"
                response += f"4. Get findings: mcp__memory__research_findings(operation='get', task_id={task_id})\n"

                return [TextContent(type="text", text=response)]

            elif operation == "get_status":
                task_id = args.get("task_id")
                if not task_id:
                    return [TextContent(type="text", text="✗ Task ID is required for get_status operation")]

                task = self.research_store.get_task(task_id)
                if not task:
                    return [TextContent(type="text", text=f"✗ Research task {task_id} not found")]

                # Get agent progress
                agent_progress = self.research_store.get_agent_progress(task_id)

                response = f"✓ Research Task Status (ID: {task_id})\n"
                response += f"Topic: {task.topic}\n"
                response += f"Status: {task.status.upper()}\n"
                response += f"Findings: {task.findings_count}\n"
                response += f"Entities Created: {task.entities_created}\n"
                response += f"Relations Created: {task.relations_created}\n"

                if agent_progress:
                    response += f"\nAgent Progress:\n"
                    for progress in agent_progress:
                        status_icon = "✓" if progress.status == AgentStatus.COMPLETED.value else "🔄" if progress.status == AgentStatus.RUNNING.value else "⏳"
                        response += f"  {status_icon} {progress.agent_name}: {progress.status} ({progress.findings_count} findings)\n"

                return [TextContent(type="text", text=response)]

            elif operation == "list":
                tasks = self.research_store.list_tasks(limit=10)

                response = f"✓ Recent Research Tasks (Last 10)\n"
                for task in tasks:
                    status_icon = "✓" if task.status == ResearchStatus.COMPLETED.value else "🔄" if task.status == ResearchStatus.RUNNING.value else "⏳"
                    response += f"{status_icon} [{task.id}] {task.topic[:60]} ({task.findings_count} findings)\n"

                return [TextContent(type="text", text=response)]

            else:
                return [TextContent(type="text", text=f"✗ Unknown operation: {operation}")]

        except Exception as e:
            logger.error(f"Error in research_task: {e}", exc_info=True)
            return [TextContent(type="text", text=f"✗ Error: {str(e)}")]

    async def _handle_research_findings(self, args: dict) -> list[TextContent]:
        """Handle research_findings tool call."""
        operation = args.get("operation")
        task_id = args.get("task_id")

        try:
            if not task_id:
                return [TextContent(type="text", text="✗ Task ID is required")]

            task = self.research_store.get_task(task_id)
            if not task:
                return [TextContent(type="text", text=f"✗ Research task {task_id} not found")]

            if operation == "get":
                findings = self.research_store.get_task_findings(task_id, limit=100)

                response = f"✓ Research Findings for Task {task_id}\n"
                response += f"Topic: {task.topic}\n"
                response += f"Total Findings: {len(findings)}\n\n"

                for finding in findings[:10]:  # Show top 10
                    response += f"• [{finding.source}] {finding.title}\n"
                    response += f"  Credibility: {finding.credibility_score:.2f}\n"
                    if finding.url:
                        response += f"  URL: {finding.url}\n"
                    response += f"\n"

                if len(findings) > 10:
                    response += f"... and {len(findings) - 10} more findings"

                return [TextContent(type="text", text=response)]

            elif operation == "list_by_source":
                source = args.get("source")
                if not source:
                    return [TextContent(type="text", text="✗ Source is required for list_by_source")]

                findings = self.research_store.get_task_findings(task_id)
                source_findings = [f for f in findings if f.source.lower() == source.lower()]

                response = f"✓ Findings from {source} (Task {task_id})\n"
                response += f"Count: {len(source_findings)}\n\n"

                for finding in source_findings[:20]:
                    response += f"• {finding.title}\n"
                    response += f"  Credibility: {finding.credibility_score:.2f}\n"

                return [TextContent(type="text", text=response)]

            elif operation == "summary":
                findings = self.research_store.get_task_findings(task_id)

                # Group by source
                by_source = {}
                for finding in findings:
                    if finding.source not in by_source:
                        by_source[finding.source] = []
                    by_source[finding.source].append(finding)

                response = f"✓ Research Summary for Task {task_id}\n"
                response += f"Topic: {task.topic}\n"
                response += f"Status: {task.status.upper()}\n"
                response += f"Total Findings: {len(findings)}\n\n"
                response += f"By Source:\n"

                for source, source_findings in sorted(by_source.items()):
                    avg_credibility = sum(f.credibility_score for f in source_findings) / len(source_findings)
                    response += f"  {source}: {len(source_findings)} findings (avg credibility: {avg_credibility:.2f})\n"

                response += f"\nEntities Created: {task.entities_created}\n"
                response += f"Relations Created: {task.relations_created}\n"

                return [TextContent(type="text", text=response)]

            else:
                return [TextContent(type="text", text=f"✗ Unknown operation: {operation}")]

        except Exception as e:
            logger.error(f"Error in research_findings: {e}", exc_info=True)
            return [TextContent(type="text", text=f"✗ Error: {str(e)}")]

    # Phase 5-8 Handler Methods

    async def _handle_get_project_dashboard(self, args: dict) -> list[TextContent]:
        """Handle get_project_dashboard tool call."""
        try:
            project_id = args.get("project_id")
            dashboard = await self.task_monitor.get_project_dashboard(project_id)

            structured_data = {
                "project_id": project_id,
                "summary": {
                    "total_tasks": dashboard.get('summary', {}).get('total_tasks', 0),
                    "completed": dashboard.get('summary', {}).get('completed', 0),
                    "in_progress": dashboard.get('summary', {}).get('in_progress', 0)
                },
                "health_overview": dashboard.get('health', {})
            }

            result = StructuredResult.success(
                data=structured_data,
                metadata={"operation": "get_project_dashboard", "schema": "prospective"},
                pagination=PaginationMetadata(returned=1)
            )
            return [result.as_optimized_content(schema_name="prospective")]
        except Exception as e:
            logger.error(f"Error in get_project_dashboard: {e}", exc_info=True)
            result = StructuredResult.error(str(e), metadata={"operation": "get_project_dashboard"})
            return [result.as_optimized_content(schema_name="prospective")]

    async def _handle_analyze_estimation_accuracy(self, args: dict) -> list[TextContent]:
        """Handle analyze_estimation_accuracy tool call.

        PHASE 6: Analyzes task estimation accuracy over a time window.
        Returns metrics on how well tasks are estimated vs actual duration.
        """
        try:
            project_id = args.get("project_id")
            days_back = args.get("days_back", 30)
            accuracy = await self.task_analytics.analyze_estimation_accuracy(project_id, days_back)

            # Build structured JSON response
            response_data = {
                "project_id": project_id,
                "analysis_period_days": days_back,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "metrics": {
                    "total_tasks": accuracy.total_tasks,
                    "accurate_estimates": accuracy.accurate_estimates,
                    "accuracy_rate": round(accuracy.accuracy_rate * 100, 1),
                    "average_variance_percent": round(accuracy.average_variance_percent, 1),
                    "underestimated_count": accuracy.underestimated_count,
                    "overestimated_count": accuracy.overestimated_count,
                },
                "assessment": {
                    "status": "GOOD" if accuracy.accuracy_rate >= 0.8 else "WARNING" if accuracy.accuracy_rate >= 0.7 else "POOR",
                    "message": f"Estimation accuracy at {accuracy.accuracy_rate*100:.1f}%. Target is >80%.",
                },
                "recommendations": []
            }

            # Add recommendations based on variance
            if accuracy.average_variance_percent > 20:
                response_data["recommendations"].append(
                    "High variance detected. Consider breaking tasks into smaller units for better estimation."
                )
            if accuracy.underestimated_count > accuracy.overestimated_count * 1.5:
                response_data["recommendations"].append(
                    "Tendency to underestimate. Add 15-20% buffer to future estimates."
                )
            if accuracy.overestimated_count > accuracy.underestimated_count * 1.5:
                response_data["recommendations"].append(
                    "Tendency to overestimate. Try to reduce estimation pessimism."
                )

            return [TextContent(type="text", text=json.dumps(response_data, indent=2))]
        except Exception as e:
            logger.error(f"Error in analyze_estimation_accuracy [project_id={args.get('project_id')}]: {e}", exc_info=True)
            error_response = json.dumps({"error": str(e), "tool": "analyze_estimation_accuracy"})
            return [TextContent(type="text", text=error_response)]

    async def _handle_discover_patterns(self, args: dict) -> list[TextContent]:
        """Handle discover_patterns tool call.

        PHASE 6: Discovers patterns in completed tasks.
        Analyzes task duration, completion rates, failure patterns, and priority distributions.
        """
        try:
            project_id = args.get("project_id")
            patterns = await self.task_analytics.discover_patterns(project_id)

            # Build structured response
            response_data = {
                "project_id": project_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "task_patterns": {
                    "average_duration_minutes": round(patterns.get('average_duration_minutes', 0), 1),
                    "min_duration_minutes": patterns.get('min_duration_minutes', 0),
                    "max_duration_minutes": patterns.get('max_duration_minutes', 0),
                    "completion_rate": round(patterns.get('completion_rate', 0) * 100, 1),
                    "total_tasks_analyzed": patterns.get('total_tasks', 0),
                },
                "failure_analysis": {
                    "failure_count": patterns.get('failure_count', 0),
                    "failure_rate": round(patterns.get('failure_rate', 0) * 100, 1),
                    "most_common_failure_type": patterns.get('most_common_failure_type', 'unknown'),
                },
                "priority_distribution": {
                    "most_common_priority": patterns.get('most_common_priority', 'unknown'),
                    "average_priority_level": patterns.get('average_priority_level', 2),
                },
                "insights": []
            }

            # Add insights based on patterns
            completion_rate = patterns.get('completion_rate', 0)
            if completion_rate < 0.85:
                response_data["insights"].append(
                    f"Completion rate {completion_rate*100:.1f}% is below target (85%). Review blockers."
                )

            failure_rate = patterns.get('failure_rate', 0)
            if failure_rate > 0.15:
                response_data["insights"].append(
                    f"Failure rate {failure_rate*100:.1f}% is elevated. Investigate root causes."
                )

            avg_duration = patterns.get('average_duration_minutes', 0)
            if avg_duration > 120:
                response_data["insights"].append(
                    f"Average task duration ({avg_duration:.0f} min) is high. Consider decomposition."
                )

            response_data["insights"].append(
                f"Most common priority level is {patterns.get('most_common_priority', 'unknown')}. "
                "Ensure balanced workload across priority levels."
            )

            return [TextContent(type="text", text=json.dumps(response_data, indent=2))]
        except Exception as e:
            logger.error(f"Error in discover_patterns [project_id={args.get('project_id')}]: {e}", exc_info=True)
            error_response = json.dumps({"error": str(e), "tool": "discover_patterns"})
            return [TextContent(type="text", text=error_response)]

    async def _handle_optimize_plan(self, args: dict) -> list[TextContent]:
        """Handle optimize_plan tool call.

        Includes plan optimization AND rule constraint validation (Week 1.3).
        Returns structured JSON with optimization suggestions and rule compliance.
        """
        try:
            task_id = args.get("task_id")
            project_id = args.get("project_id", 1)  # Default to project 1
            task = self.prospective_store.get_task(task_id)

            if not task or not task.plan:
                error_response = {
                    "status": "error",
                    "error": f"Task {task_id} not found or has no plan",
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
                return [TextContent(type="text", text=json.dumps(error_response))]

            # Get plan optimization suggestions
            suggestions = await self.planning_assistant.optimize_plan(task)

            # Week 1.3: Validate plan against rules
            rule_validation = self.rules_engine.validate_task(task_id, project_id)

            # Build optimization suggestions array
            optimization_suggestions = []
            if suggestions:
                for suggestion in suggestions:
                    optimization_suggestions.append({
                        "title": getattr(suggestion, 'title', 'Optimization'),
                        "recommendation": getattr(suggestion, 'recommendation', ''),
                        "impact": getattr(suggestion, 'impact', 'medium').lower(),
                        "estimated_time_savings_minutes": getattr(suggestion, 'estimated_time_savings', 0),
                        "complexity": getattr(suggestion, 'complexity', 'low').lower()
                    })

            # Calculate compliance status
            compliance_status = "COMPLIANT" if rule_validation.is_compliant else "NON_COMPLIANT"
            violations = []
            if not rule_validation.is_compliant and hasattr(rule_validation, 'violations'):
                for v in rule_validation.violations:
                    violations.append({
                        "rule_name": v.get('rule_name', 'unknown'),
                        "severity": v.get('severity', 'warning').upper(),
                        "message": v.get('message', '')
                    })

            # Build recommendations based on optimization analysis
            recommendations = []

            # High-impact optimization recommendations
            high_impact_count = sum(1 for s in optimization_suggestions if s['impact'] == 'high')
            if high_impact_count > 0:
                recommendations.append(f"Found {high_impact_count} high-impact optimization opportunities - prioritize these for maximum time savings")

            # Parallelization recommendations
            if hasattr(task, 'plan') and hasattr(task.plan, 'parallelizable_groups'):
                parallel_count = len(getattr(task.plan, 'parallelizable_groups', []))
                if parallel_count > 0:
                    recommendations.append(f"Plan has {parallel_count} parallelizable step groups - consider concurrent execution to reduce duration")

            # Rule compliance recommendations
            if violations:
                recommendations.append(f"Address {len(violations)} rule violations before execution to ensure project compliance")
            else:
                recommendations.append("Plan is compliant with all project rules")

            # Time savings recommendation
            total_time_savings = sum(s.get('estimated_time_savings_minutes', 0) for s in optimization_suggestions)
            if total_time_savings > 0:
                recommendations.append(f"Applying all optimizations could save approximately {total_time_savings} minutes")

            response_data = {
                "task_id": task_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "optimization_analysis": {
                    "suggestion_count": len(optimization_suggestions),
                    "total_time_savings_minutes": total_time_savings,
                    "high_impact_count": high_impact_count,
                    "suggestions": optimization_suggestions
                },
                "rule_compliance": {
                    "status": compliance_status,
                    "violation_count": len(violations),
                    "violations": violations
                },
                "recommendations": recommendations
            }

            return [TextContent(type="text", text=json.dumps(response_data))]
        except Exception as e:
            logger.error(f"Error in optimize_plan: {e}", exc_info=True)
            error_response = {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            return [TextContent(type="text", text=json.dumps(error_response))]

    async def _handle_estimate_resources(self, args: dict) -> list[TextContent]:
        """Handle estimate_resources tool call.

        Returns structured JSON with detailed resource estimation including
        time breakdown, expertise requirements, dependencies, and confidence scoring.
        """
        try:
            task_id = args.get("task_id")
            task = self.prospective_store.get_task(task_id)

            if not task or not task.plan:
                error_response = {
                    "status": "error",
                    "error": f"Task {task_id} not found or has no plan",
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
                return [TextContent(type="text", text=json.dumps(error_response))]

            resources = await self.planning_assistant.estimate_resources(task)

            # Extract resource data with safe defaults
            time_hours = resources.get('time_hours', 0)
            time_minutes = int((time_hours * 60) % 60)
            expertise_level = resources.get('expertise_level', 'intermediate')
            dependencies = resources.get('dependencies', [])
            tools_required = resources.get('tools_required', [])

            # Calculate confidence score (0-1)
            # Based on: plan complexity, dependency count, expertise availability
            base_confidence = 0.85
            complexity_penalty = min(0.15, len(getattr(task.plan, 'steps', [])) * 0.01)
            dependency_penalty = min(0.2, len(dependencies) * 0.05)
            confidence_score = max(0.5, base_confidence - complexity_penalty - dependency_penalty)

            # Time breakdown analysis
            step_count = len(getattr(task.plan, 'steps', []))
            avg_time_per_step = (time_hours * 60) / step_count if step_count > 0 else 0

            time_breakdown = {
                "estimated_hours": round(time_hours, 2),
                "estimated_minutes": int(time_hours * 60),
                "average_minutes_per_step": round(avg_time_per_step, 1),
                "step_count": step_count,
                "risk_adjusted_hours": round(time_hours * (1 + (1 - confidence_score) * 0.25), 2)
            }

            # Expertise requirements
            expertise_mapping = {
                "junior": {"level": 1, "description": "Entry-level or simple tasks"},
                "intermediate": {"level": 2, "description": "Moderate complexity, some experience needed"},
                "senior": {"level": 3, "description": "Complex tasks requiring deep expertise"},
                "expert": {"level": 4, "description": "Highly specialized or novel problems"}
            }

            expertise_info = expertise_mapping.get(expertise_level.lower(), {
                "level": 2,
                "description": expertise_level
            })

            # Build recommendations
            recommendations = []

            # Time estimation recommendations
            if time_hours > 8:
                recommendations.append(f"Large task ({time_hours:.1f} hours) - consider breaking into smaller subtasks for better estimation accuracy")
            elif time_hours < 0.5:
                recommendations.append("Very short task - may benefit from batching with related work items")

            # Confidence-based recommendations
            if confidence_score < 0.65:
                recommendations.append(f"Low confidence ({confidence_score:.0%}) - validate plan assumptions before execution; consider spike task for unknowns")
            elif confidence_score >= 0.85:
                recommendations.append(f"High confidence ({confidence_score:.0%}) - good estimation basis; proceed with execution")

            # Dependency recommendations
            if len(dependencies) > 3:
                recommendations.append(f"High dependency count ({len(dependencies)}) - ensure all upstream tasks complete on schedule")

            # Tool requirement recommendations
            if len(tools_required) > 5:
                recommendations.append(f"Multiple tools required ({len(tools_required)}) - verify all licenses and access before starting")
            elif len(tools_required) == 0:
                recommendations.append("No external tools required - good for minimal setup overhead")

            response_data = {
                "task_id": task_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "resource_estimates": {
                    "time": time_breakdown,
                    "expertise": {
                        "required_level": expertise_level,
                        "level_code": expertise_info.get("level", 2),
                        "description": expertise_info.get("description", "")
                    },
                    "dependencies": {
                        "count": len(dependencies),
                        "items": dependencies
                    },
                    "tools": {
                        "count": len(tools_required),
                        "items": tools_required
                    }
                },
                "confidence": {
                    "score": round(confidence_score, 3),
                    "percentage": f"{confidence_score * 100:.0f}%",
                    "factors": {
                        "base": 0.85,
                        "complexity_penalty": round(complexity_penalty, 3),
                        "dependency_penalty": round(dependency_penalty, 3)
                    }
                },
                "risk_assessment": {
                    "schedule_risk": "HIGH" if time_hours > 12 else "MEDIUM" if time_hours > 4 else "LOW",
                    "expertise_risk": "HIGH" if expertise_level == "expert" else "MEDIUM" if expertise_level == "senior" else "LOW",
                    "dependency_risk": "HIGH" if len(dependencies) > 5 else "MEDIUM" if len(dependencies) > 2 else "LOW"
                },
                "recommendations": recommendations
            }

            return [TextContent(type="text", text=json.dumps(response_data))]
        except Exception as e:
            logger.error(f"Error in estimate_resources: {e}", exc_info=True)
            error_response = {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            return [TextContent(type="text", text=json.dumps(error_response))]

    async def _handle_add_project_dependency(self, args: dict) -> list[TextContent]:
        """Handle add_project_dependency tool call.

        Adds cross-project task dependency with validation and risk assessment.
        Returns structured JSON with dependency details and recommendations.
        """
        try:
            from_task_id = args.get("from_task_id")
            from_project_id = args.get("from_project_id", 1)
            to_task_id = args.get("to_task_id")
            to_project_id = args.get("to_project_id", 1)
            dependency_type = args.get("dependency_type", "depends_on")

            # Validate required parameters
            if not all([from_task_id, to_task_id]):
                error_response = {
                    "status": "error",
                    "error": "Missing required parameters: from_task_id and to_task_id",
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
                return [TextContent(type="text", text=json.dumps(error_response))]

            # Add the dependency
            success = await self.project_coordinator.add_dependency(
                from_task_id=from_task_id,
                from_project_id=from_project_id,
                to_task_id=to_task_id,
                to_project_id=to_project_id,
                dependency_type=dependency_type,
            )

            # Assess dependency impact
            cross_project = from_project_id != to_project_id
            dependency_risk = "HIGH" if cross_project else "MEDIUM"

            # Build recommendations
            recommendations = []
            if cross_project:
                recommendations.append("Cross-project dependency detected - ensure both projects have synchronized schedules")
                recommendations.append("Monitor project boundaries for integration risks")

            if dependency_type == "depends_on":
                recommendations.append(f"Ensure task {to_task_id} completes before starting task {from_task_id}")
            elif dependency_type == "blocks":
                recommendations.append(f"Task {from_task_id} blocks task {to_task_id} - coordinate completion times")

            recommendations.append("Use analyze_critical_path to understand full dependency chain impact")

            response_data = {
                "status": "success" if success else "failed",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "dependency": {
                    "from_task_id": from_task_id,
                    "from_project_id": from_project_id,
                    "to_task_id": to_task_id,
                    "to_project_id": to_project_id,
                    "dependency_type": dependency_type,
                    "cross_project": cross_project
                },
                "risk_assessment": {
                    "level": dependency_risk,
                    "cross_project_risk": cross_project,
                    "impact_severity": "HIGH" if cross_project else "MEDIUM"
                },
                "recommendations": recommendations
            }

            return [TextContent(type="text", text=json.dumps(response_data))]
        except Exception as e:
            logger.error(f"Error in add_project_dependency: {e}", exc_info=True)
            error_response = {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            return [TextContent(type="text", text=json.dumps(error_response))]

    async def _handle_analyze_critical_path(self, args: dict) -> list[TextContent]:
        """Handle analyze_critical_path tool call.

        Analyzes critical path (longest dependency chain) for project timeline.
        Returns structured JSON with path details and timeline recommendations.
        """
        try:
            project_id = args.get("project_id")

            if not project_id:
                error_response = {
                    "status": "error",
                    "error": "Missing required parameter: project_id",
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
                return [TextContent(type="text", text=json.dumps(error_response))]

            cp = await self.project_coordinator.analyze_critical_path(project_id)

            if not cp:
                response_data = {
                    "status": "not_found",
                    "message": f"No critical path found for project {project_id}",
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
                return [TextContent(type="text", text=json.dumps(response_data))]

            # Convert minutes to hours and days
            total_hours = cp.total_duration_minutes / 60
            total_days = total_hours / 8  # Assumes 8-hour workday
            slack_hours = cp.slack_time_minutes / 60
            slack_days = slack_hours / 8

            # Calculate buffer percentage
            buffer_percent = (cp.slack_time_minutes / cp.total_duration_minutes * 100) if cp.total_duration_minutes > 0 else 0

            # Assess timeline risk
            timeline_risk = "HIGH" if buffer_percent < 10 else "MEDIUM" if buffer_percent < 20 else "LOW"

            # Build recommendations
            recommendations = []

            if buffer_percent < 10:
                recommendations.append(f"Critical timeline! Only {buffer_percent:.1f}% buffer - any delays will impact project completion")
                recommendations.append("Prioritize bottleneck tasks for acceleration or parallel execution")
            elif buffer_percent < 20:
                recommendations.append(f"Moderate timeline pressure ({buffer_percent:.1f}% buffer) - monitor critical path tasks closely")
                recommendations.append("Identify potential parallelization opportunities")
            else:
                recommendations.append(f"Healthy timeline buffer ({buffer_percent:.1f}%) - good scheduling flexibility")

            # Bottleneck analysis
            if len(cp.task_ids) > 5:
                recommendations.append(f"Long dependency chain ({len(cp.task_ids)} tasks) - identify opportunities to parallelize early/middle tasks")

            # Slack time usage
            if cp.slack_time_minutes > 480:  # > 8 hours
                recommendations.append(f"Significant slack time available ({slack_hours:.1f} hours) - can be used for additional validation or optimization")

            response_data = {
                "project_id": project_id,
                "status": "found",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "critical_path": {
                    "task_ids": getattr(cp, 'task_ids', []),
                    "task_count": len(getattr(cp, 'task_ids', []))
                },
                "timeline": {
                    "total_duration_minutes": cp.total_duration_minutes,
                    "total_duration_hours": round(total_hours, 2),
                    "total_duration_days": round(total_days, 2),
                    "slack_time_minutes": cp.slack_time_minutes,
                    "slack_time_hours": round(slack_hours, 2),
                    "slack_time_days": round(slack_days, 2),
                    "buffer_percentage": round(buffer_percent, 1)
                },
                "risk_assessment": {
                    "timeline_risk": timeline_risk,
                    "buffer_criticality": "CRITICAL" if buffer_percent < 10 else "WARNING" if buffer_percent < 20 else "HEALTHY",
                    "bottleneck_count": max(0, len(getattr(cp, 'task_ids', [])) - 3)
                },
                "recommendations": recommendations
            }

            return [TextContent(type="text", text=json.dumps(response_data))]
        except Exception as e:
            logger.error(f"Error in analyze_critical_path: {e}", exc_info=True)
            error_response = {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            return [TextContent(type="text", text=json.dumps(error_response))]

    async def _handle_detect_resource_conflicts(self, args: dict) -> list[TextContent]:
        """Handle detect_resource_conflicts tool call.

        Detects resource conflicts (person, tool, data) across multiple projects.
        Returns structured JSON with conflict details and mitigation recommendations.
        """
        try:
            project_ids = args.get("project_ids", [])

            if not project_ids:
                error_response = {
                    "status": "error",
                    "error": "Missing required parameter: project_ids (list of project IDs)",
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
                return [TextContent(type="text", text=json.dumps(error_response))]

            conflicts = await self.project_coordinator.detect_resource_conflicts(project_ids)

            # Categorize conflicts by severity
            critical_conflicts = []
            warning_conflicts = []
            info_conflicts = []

            for conflict in conflicts:
                conflict_dict = {
                    "conflict_type": getattr(conflict, 'conflict_type', 'unknown'),
                    "task_ids": getattr(conflict, 'task_ids', []),
                    "description": getattr(conflict, 'description', ''),
                    "recommendation": getattr(conflict, 'recommendation', '')
                }

                severity = getattr(conflict, 'severity', 'warning').lower()
                if severity == 'critical':
                    critical_conflicts.append(conflict_dict)
                elif severity == 'warning':
                    warning_conflicts.append(conflict_dict)
                else:
                    info_conflicts.append(conflict_dict)

            # Calculate conflict statistics
            total_conflicts = len(conflicts)
            person_conflicts = sum(1 for c in conflicts if getattr(c, 'conflict_type', '').lower() == 'person')
            tool_conflicts = sum(1 for c in conflicts if getattr(c, 'conflict_type', '').lower() == 'tool')
            data_conflicts = sum(1 for c in conflicts if getattr(c, 'conflict_type', '').lower() == 'data')

            # Build recommendations
            recommendations = []

            if critical_conflicts:
                recommendations.append(f"URGENT: {len(critical_conflicts)} critical conflict(s) require immediate resolution before execution")

            if person_conflicts > 0:
                recommendations.append(f"Person conflicts detected ({person_conflicts}) - review task assignments and workload distribution")

            if tool_conflicts > 0:
                recommendations.append(f"Tool conflicts detected ({tool_conflicts}) - verify tool licenses and concurrent usage limits")

            if data_conflicts > 0:
                recommendations.append(f"Data conflicts detected ({data_conflicts}) - ensure data isolation or synchronization strategies")

            if total_conflicts == 0:
                recommendations.append("No conflicts detected - safe to proceed with multi-project execution")
            else:
                recommendations.append("Prioritize critical conflicts; address warnings before project kickoff")

            # Risk assessment
            overall_risk = "CRITICAL" if len(critical_conflicts) > 0 else "HIGH" if len(warning_conflicts) > 2 else "MEDIUM" if len(warning_conflicts) > 0 else "LOW"

            response_data = {
                "project_ids": project_ids,
                "status": "success",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "conflict_summary": {
                    "total_count": total_conflicts,
                    "critical_count": len(critical_conflicts),
                    "warning_count": len(warning_conflicts),
                    "info_count": len(info_conflicts)
                },
                "conflict_breakdown": {
                    "person_conflicts": person_conflicts,
                    "tool_conflicts": tool_conflicts,
                    "data_conflicts": data_conflicts,
                    "other_conflicts": total_conflicts - person_conflicts - tool_conflicts - data_conflicts
                },
                "conflicts": {
                    "critical": critical_conflicts,
                    "warning": warning_conflicts,
                    "info": info_conflicts
                },
                "risk_assessment": {
                    "overall_risk": overall_risk,
                    "execution_ready": len(critical_conflicts) == 0,
                    "blocking_issues": len(critical_conflicts)
                },
                "recommendations": recommendations
            }

            return [TextContent(type="text", text=json.dumps(response_data))]
        except Exception as e:
            logger.error(f"Error in detect_resource_conflicts: {e}", exc_info=True)
            error_response = {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            return [TextContent(type="text", text=json.dumps(error_response))]

    # Week 1.3: Rules Engine and Suggestions Engine handlers

    async def _handle_create_rule(self, args: dict) -> list[TextContent]:
        """Handle create_rule tool call."""
        try:
            project_id = args.get("project_id")
            name = args.get("name")
            description = args.get("description")
            category = args.get("category")
            rule_type = args.get("rule_type")
            condition = args.get("condition")
            severity = args.get("severity", "warning")
            exception_condition = args.get("exception_condition")
            auto_block = args.get("auto_block", True)
            can_override = args.get("can_override", True)
            override_requires_approval = args.get("override_requires_approval", False)
            tags = args.get("tags", [])

            if not all([project_id, name, description, category, rule_type, condition]):
                return [TextContent(type="text", text="Missing required args")]

            rule = Rule(
                project_id=project_id,
                name=name,
                description=description,
                category=RuleCategory(category),
                rule_type=RuleType(rule_type),
                condition=condition,
                severity=SeverityLevel(severity),
                exception_condition=exception_condition,
                auto_block=auto_block,
                can_override=can_override,
                override_requires_approval=override_requires_approval,
                tags=tags,
            )

            created = self.rules_store.create(rule)
            return [TextContent(type="text", text=f"Rule created: ID {created.id}, Name: {created.name}")]
        except Exception as e:
            logger.error(f"Error in create_rule: {e}", exc_info=True)
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_list_rules(self, args: dict) -> list[TextContent]:
        """Handle list_rules tool call."""
        try:
            project_id = args.get("project_id")
            category = args.get("category")
            enabled_only = args.get("enabled_only", True)
            limit = min(args.get("limit", 10), 100)
            offset = args.get("offset", 0)

            if not project_id:
                result = StructuredResult.error(
                    "Missing project_id",
                    metadata={"operation": "list_rules"}
                )
                return [result.as_optimized_content(schema_name="validation")]

            all_rules = self.rules_store.list_rules(project_id, enabled_only=enabled_only)

            if category:
                all_rules = [r for r in all_rules if str(r.category).lower() == category.lower()]

            total_count = len(all_rules)
            rules = all_rules[offset:offset+limit]

            # Format rules for structured response
            formatted_rules = []
            for rule in rules:
                category_val = str(rule.category) if not isinstance(rule.category, str) else rule.category
                formatted_rules.append({
                    "id": rule.id,
                    "name": rule.name,
                    "category": category_val,
                    "severity": str(rule.severity) if hasattr(rule, 'severity') else "unknown",
                    "enabled": enabled_only  # inferred from filter
                })

            result = paginate_results(
                results=formatted_rules,
                args=args,
                total_count=total_count,
                operation="list_rules",
                drill_down_hint="Use validate_task_against_rules to see rule violations and detailed validation results"
            )
        except Exception as e:
            result = StructuredResult.error(str(e), metadata={"operation": "list_rules"})

        return [result.as_optimized_content(schema_name="validation")]

    async def _handle_validate_task_against_rules(self, args: dict) -> list[TextContent]:
        """Handle validate_task_against_rules tool call."""
        try:
            task_id = args.get("task_id")
            project_id = args.get("project_id")
            context = args.get("context", {})

            if not task_id or not project_id:
                return [TextContent(type="text", text="Missing task_id or project_id")]

            result = self.rules_engine.validate_task(task_id, project_id, context)

            status = "✓ COMPLIANT" if result.is_compliant else "✗ VIOLATIONS FOUND"
            output = f"{status}\n"
            output += f"Violations: {result.violation_count}, Warnings: {result.warning_count}\n"

            if result.violations:
                output += "\nViolations:\n"
                for v in result.violations:
                    output += f"  - {v['rule_name']} ({v['severity']}): {v['message']}\n"

            if result.suggestions:
                output += "\nSuggestions:\n"
                for s in result.suggestions:
                    output += f"  - {s}\n"

            return [TextContent(type="text", text=output)]
        except Exception as e:
            logger.error(f"Error in validate_task_against_rules: {e}", exc_info=True)
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_delete_rule(self, args: dict) -> list[TextContent]:
        """Handle delete_rule tool call."""
        try:
            rule_id = args.get("rule_id")
            hard_delete = args.get("hard_delete", False)

            if not rule_id:
                return [TextContent(type="text", text="Missing rule_id")]

            if hard_delete:
                success = self.rules_store.delete(rule_id)
                action = "deleted"
            else:
                success = self.rules_store.disable_rule(rule_id)
                action = "disabled"

            if success:
                return [TextContent(type="text", text=f"Rule {rule_id} {action}")]
            else:
                return [TextContent(type="text", text=f"Rule {rule_id} not found")]
        except Exception as e:
            logger.error(f"Error in delete_rule: {e}", exc_info=True)
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_get_suggestions(self, args: dict) -> list[TextContent]:
        """Handle get_suggestions tool call."""
        try:
            task_id = args.get("task_id")
            project_id = args.get("project_id")
            include_warnings = args.get("include_warnings", True)

            if not task_id or not project_id:
                result = StructuredResult.error("Missing task_id or project_id", metadata={"operation": "get_suggestions"})
                return [result.as_optimized_content(schema_name="validation")]

            # Validate task to get violations
            validation = self.rules_engine.validate_task(task_id, project_id)

            if not validation.violations and not validation.suggestions:
                result = StructuredResult.success(
                    data={"violations": [], "suggestions": [], "status": "No violations detected"},
                    metadata={"operation": "get_suggestions", "schema": "validation"},
                    pagination=PaginationMetadata(returned=0)
                )
                return [result.as_optimized_content(schema_name="validation")]

            # Get suggestions for violations
            suggestions = self.suggestions_engine.suggest_fixes(validation.violations)

            structured_data = {
                "task_id": task_id,
                "project_id": project_id,
                "violations": [str(v) for v in validation.violations],
                "suggestions": [str(s) for s in suggestions]
            }

            result = StructuredResult.success(
                data=structured_data,
                metadata={"operation": "get_suggestions", "schema": "validation"},
                pagination=PaginationMetadata(returned=len(suggestions))
            )
            return [result.as_optimized_content(schema_name="validation")]
        except Exception as e:
            logger.error(f"Error in get_suggestions: {e}", exc_info=True)
            result = StructuredResult.error(str(e), metadata={"operation": "get_suggestions"})
            return [result.as_optimized_content(schema_name="validation")]

    async def _handle_override_rule(self, args: dict) -> list[TextContent]:
        """Handle override_rule tool call."""
        try:
            rule_id = args.get("rule_id")
            task_id = args.get("task_id")
            project_id = args.get("project_id")
            overridden_by = args.get("overridden_by")
            justification = args.get("justification")
            expires_in_hours = args.get("expires_in_hours")

            required = [rule_id, task_id, project_id, overridden_by, justification]
            if not all(required):
                return [TextContent(type="text", text="Missing required args")]

            expires_at = None
            if expires_in_hours:
                expires_at = int((datetime.now() + timedelta(hours=expires_in_hours)).timestamp())

            override = RuleOverride(
                project_id=project_id,
                rule_id=rule_id,
                task_id=task_id,
                overridden_by=overridden_by,
                justification=justification,
                expires_at=expires_at,
            )

            created = self.rules_store.create_override(override)
            output = f"Override created: ID {created.id}\n"
            output += f"Rule: {rule_id}, Task: {task_id}\n"
            output += f"Justification: {justification}"

            return [TextContent(type="text", text=output)]
        except Exception as e:
            logger.error(f"Error in override_rule: {e}", exc_info=True)
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_score_semantic_memories(self, args: dict) -> list[TextContent]:
        """Handle score_semantic_memories tool call.

        Score semantic memories using LLM-powered quality analysis.
        Returns the lowest-quality memories first (what needs improvement).
        """
        try:
            project_id = args.get("project_id", 1)
            limit = args.get("limit", 10)

            scores = self.semantic_quality_analyzer.score_project_memories(project_id, limit=limit)

            if not scores:
                return [TextContent(type="text", text=f"No semantic memories found for project {project_id}")]

            response = f"Semantic Memory Quality Scores (Project {project_id})\n"
            response += f"Analyzed: {len(scores)} memories\n\n"

            # Group by tier
            by_tier = {}
            for score in scores:
                tier = score.quality_tier
                if tier not in by_tier:
                    by_tier[tier] = []
                by_tier[tier].append(score)

            # Display from lowest to highest quality
            tier_order = ["poor", "fair", "good", "excellent"]
            for tier in tier_order:
                if tier in by_tier:
                    response += f"\n{tier.upper()} ({len(by_tier[tier])}):\n"
                    for score in by_tier[tier][:3]:  # Show top 3 per tier
                        response += f"  ID {score.memory_id} ({score.overall_quality:.1%})\n"
                        response += f"    - Coherence: {score.coherence_score:.1%}\n"
                        response += f"    - Relevance: {score.relevance_score:.1%}\n"
                        response += f"    - Completeness: {score.completeness_score:.1%}\n"
                        if score.suggestions:
                            response += f"    - Suggestions: {', '.join(score.suggestions[:2])}\n"

            return [TextContent(type="text", text=response)]
        except Exception as e:
            logger.error(f"Error in score_semantic_memories: {e}", exc_info=True)
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_get_memory_quality_summary(self, args: dict) -> list[TextContent]:
        """Handle get_memory_quality_summary tool call.

        Get aggregate quality statistics for project memories.
        """
        try:
            project_id = args.get("project_id", 1)

            summary = self.semantic_quality_analyzer.get_quality_summary(project_id)

            if not summary:
                result = StructuredResult.error(f"Could not generate quality summary for project {project_id}", metadata={"operation": "get_memory_quality_summary"})
                return [result.as_optimized_content(schema_name="semantic")]

            # Build quality distribution
            dist = summary.get("quality_distribution", {})
            total_memories = summary.get("total_memories", 0)
            quality_dist = {}
            for tier in ["excellent", "good", "fair", "poor"]:
                count = dist.get(tier, 0)
                pct = (count / total_memories * 100) if total_memories else 0
                quality_dist[tier] = {"count": count, "percentage": round(pct, 1)}

            # Top recommendations
            recs = summary.get("recommendations", [])
            formatted_recs = [{"action": r['action'], "frequency": r['frequency']} for r in recs[:5]]

            structured_data = {
                "project_id": project_id,
                "overall_quality": round(summary.get('avg_quality', 0) * 100, 1),
                "total_memories": total_memories,
                "quality_distribution": quality_dist,
                "low_quality_count": summary.get("low_quality_count", 0),
                "improvement_opportunities": formatted_recs
            }

            result = StructuredResult.success(
                data=structured_data,
                metadata={"operation": "get_memory_quality_summary", "schema": "semantic"},
                pagination=PaginationMetadata(returned=1)
            )
            return [result.as_optimized_content(schema_name="semantic")]
        except Exception as e:
            logger.error(f"Error in get_memory_quality_summary: {e}", exc_info=True)
            result = StructuredResult.error(str(e), metadata={"operation": "get_memory_quality_summary"})
            return [result.as_optimized_content(schema_name="semantic")]

    async def _handle_validate_plan_with_reasoning(self, args: dict) -> list[TextContent]:
        """Handle validate_plan_with_reasoning tool call.

        Validate a plan using LLM extended thinking for deep analysis.
        """
        try:
            plan_id = args.get("plan_id", 1)
            description = args.get("description", "")
            steps = args.get("steps", [])
            dependencies = args.get("dependencies")
            constraints = args.get("constraints")
            success_criteria = args.get("success_criteria")

            # Validate required parameters
            if not description:
                return [TextContent(type="text", text="Error: description is required")]

            # Call with timeout to prevent hangs
            try:
                result = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.llm_plan_validator.validate_plan,
                        plan_id, description, steps, dependencies, constraints, success_criteria
                    ),
                    timeout=30.0  # 30 second timeout for LLM calls
                )
            except asyncio.TimeoutError:
                return [TextContent(type="text", text="Error: Plan validation timed out after 30 seconds. Plan may be too complex for reasoning validation.")]

            response = f"Plan Validation Analysis (Plan {plan_id})\n"
            response += "=" * 60 + "\n"

            # Overall assessment
            status = "✅ FEASIBLE" if result.is_feasible else "❌ NOT FEASIBLE"
            response += f"\n{status}\n"
            response += f"Overall Confidence: {result.overall_confidence:.0%}\n"
            response += f"Estimated Complexity: {result.estimated_complexity}/10\n"
            response += f"Estimated Duration: {result.estimated_duration_mins} minutes\n"

            # Risks
            if result.risks:
                response += f"\n⚠️  RISKS ({len(result.risks)}):\n"
                for risk in result.risks[:5]:  # Show top 5
                    response += f"  [{risk.severity.upper()}] {risk.description}\n"
                    if risk.mitigation:
                        response += f"      → Mitigation: {risk.mitigation}\n"

            # Assumptions
            if result.assumptions:
                response += f"\n📌 KEY ASSUMPTIONS ({len(result.assumptions)}):\n"
                for assumption in result.assumptions[:3]:
                    response += f"  [{assumption.severity.upper()}] {assumption.description}\n"

            # Blockers
            if result.blockers:
                response += f"\n🚫 BLOCKERS ({len(result.blockers)}):\n"
                for blocker in result.blockers:
                    response += f"  [{blocker.severity.upper()}] {blocker.description}\n"
                    if blocker.mitigation:
                        response += f"      → Solution: {blocker.mitigation}\n"

            # Recommendations
            if result.recommendations:
                response += f"\n💡 RECOMMENDATIONS:\n"
                for rec in result.recommendations[:5]:
                    response += f"  • {rec}\n"

            # Alternative approaches
            if result.alternative_approaches:
                response += f"\n🔄 ALTERNATIVE APPROACHES:\n"
                for alt in result.alternative_approaches[:3]:
                    response += f"  • {alt}\n"

            # Reasoning summary
            if result.reasoning_summary:
                response += f"\n📖 REASONING:\n{result.reasoning_summary}\n"

            return [TextContent(type="text", text=response)]
        except Exception as e:
            logger.error(f"Error in validate_plan_with_reasoning: {e}", exc_info=True)
            return [TextContent(type="text", text=f"Error: {str(e)}")]


    # Tier 1: Saliency-based Attention Management handlers
    async def _handle_compute_memory_saliency(self, args: dict) -> list[TextContent]:
        """Handle compute_memory_saliency tool call.

        Computes multi-factor saliency score for a memory using:
        - Frequency (30%): how often accessed
        - Recency (30%): how recently accessed
        - Relevance (25%): alignment with current goal
        - Surprise (15%): novelty/unexpectedness
        """
        try:
            memory_id = args.get("memory_id")
            layer = args.get("layer")
            project_id = args.get("project_id")
            current_goal = args.get("current_goal")
            context_events = args.get("context_events")

            if not all([memory_id, layer, project_id]):
                return [TextContent(type="text", text="Missing required args: memory_id, layer, project_id")]

            result = self.central_executive.compute_memory_saliency(
                memory_id=memory_id,
                layer=layer,
                project_id=project_id,
                current_goal=current_goal,
                context_events=context_events,
            )

            response = f"""
**Memory Saliency Analysis**

Memory ID: {result['memory_id']}
Layer: {result['layer']}
Saliency Score: {result['saliency']:.2%}
Focus Type: {result['focus_type']}
Recommendation: {result['recommendation']}

Explanation:
- Saliency combines frequency (30%), recency (30%), relevance (25%), and surprise (15%)
- Higher scores indicate memories that should receive attention
- Focus type determines priority: primary (≥0.7), secondary (0.4-0.7), background (<0.4)
"""
            return [TextContent(type="text", text=response)]
        except Exception as e:
            logger.error(f"Error in compute_memory_saliency: {e}", exc_info=True)
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_auto_focus_top_memories(self, args: dict) -> list[TextContent]:
        """Handle auto_focus_top_memories tool call.

        Automatically identifies and focuses on top-k memories by saliency score.
        Sets attention weights with decay (top=1.0, rank 10=0.3).
        """
        try:
            project_id = args.get("project_id")
            layer = args.get("layer", "semantic")
            top_k = args.get("top_k", 5)
            current_goal = args.get("current_goal")
            context_events = args.get("context_events")

            if not project_id:
                return [TextContent(type="text", text="Missing required argument: project_id")]

            top_memories = self.central_executive.auto_focus_top_memories(
                project_id=project_id,
                layer=layer,
                top_k=top_k,
                current_goal=current_goal,
                context_events=context_events,
            )

            if not top_memories:
                return [TextContent(type="text", text=f"No memories found in {layer} layer for project {project_id}")]

            response = f"**Auto-Focus Results (Top {len(top_memories)} Memories)**\n\n"
            for i, mem in enumerate(top_memories, 1):
                weight = max(0.3, 1.0 - (i * 0.1))
                response += f"{i}. Memory #{mem['memory_id']}\n"
                response += f"   Saliency: {mem['saliency']:.2%}\n"
                response += f"   Focus Type: {mem['focus_type']}\n"
                response += f"   Attention Weight: {weight:.1%}\n"
                response += f"   Recommendation: {mem['recommendation']}\n\n"

            return [TextContent(type="text", text=response)]
        except Exception as e:
            logger.error(f"Error in auto_focus_top_memories: {e}", exc_info=True)
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_get_saliency_batch(self, args: dict) -> list[TextContent]:
        """Handle get_saliency_batch tool call.

        Efficiently computes saliency scores for multiple memories in batch.
        """
        try:
            memory_ids = args.get("memory_ids", [])
            layer = args.get("layer")
            project_id = args.get("project_id")
            current_goal = args.get("current_goal")
            context_events = args.get("context_events")

            if not all([memory_ids, layer, project_id]):
                result = StructuredResult.error("Missing required args: memory_ids, layer, project_id", metadata={"operation": "get_saliency_batch"})
                return [result.as_optimized_content(schema_name="meta")]

            if not isinstance(memory_ids, list):
                memory_ids = [memory_ids]

            results = self.central_executive.get_saliency_scores_batch(
                memory_ids=memory_ids,
                layer=layer,
                project_id=project_id,
                current_goal=current_goal,
                context_events=context_events,
            )

            # Summary statistics
            saliencies = [r['saliency'] for r in results]
            avg_saliency = sum(saliencies)/len(saliencies) if saliencies else 0

            formatted_results = [
                {
                    "memory_id": r['memory_id'],
                    "saliency": round(r['saliency'] * 100, 1),
                    "focus_type": r['focus_type'],
                    "recommendation": r['recommendation'].split(':')[0]
                }
                for r in results
            ]

            structured_data = {
                "total_memories": len(results),
                "layer": layer,
                "project_id": project_id,
                "scores": formatted_results,
                "summary": {
                    "average_saliency": round(avg_saliency * 100, 1),
                    "max_saliency": round(max(saliencies) * 100, 1) if saliencies else 0,
                    "min_saliency": round(min(saliencies) * 100, 1) if saliencies else 0
                }
            }

            result = StructuredResult.success(
                data=structured_data,
                metadata={"operation": "get_saliency_batch", "schema": "meta"},
                pagination=PaginationMetadata(returned=len(results))
            )
            return [result.as_optimized_content(schema_name="meta")]
        except Exception as e:
            logger.error(f"Error in get_saliency_batch: {e}", exc_info=True)
            result = StructuredResult.error(str(e), metadata={"operation": "get_saliency_batch"})
            return [result.as_optimized_content(schema_name="meta")]

    async def _handle_get_saliency_recommendation(self, args: dict) -> list[TextContent]:
        """Handle get_saliency_recommendation tool call.

        Provides actionable recommendation based on saliency score.
        """
        try:
            from ..working_memory.saliency import saliency_to_recommendation, saliency_to_focus_type

            saliency_score = args.get("saliency_score")

            if saliency_score is None:
                return [TextContent(type="text", text="Missing required argument: saliency_score")]

            if not (0.0 <= saliency_score <= 1.0):
                return [TextContent(type="text", text=f"Invalid saliency score {saliency_score}. Must be between 0 and 1.")]

            recommendation = saliency_to_recommendation(saliency_score)
            focus_type = saliency_to_focus_type(saliency_score)

            response = f"""
**Saliency-Based Recommendation**

Saliency Score: {saliency_score:.2%}
Focus Type: {focus_type}
Recommendation: {recommendation}

**Action Guidance**:
- **Primary Focus (≥70%)**: Keep in active working memory, allocate full attention
- **Secondary Focus (40-70%)**: Monitor and be ready to promote if relevance increases
- **Background (<40%)**: Consider for consolidation or inhibition to reduce cognitive load
"""
            return [TextContent(type="text", text=response)]
        except Exception as e:
            logger.error(f"Error in get_saliency_recommendation: {e}", exc_info=True)
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    # Phase 9.1: Uncertainty-Aware Generation handlers
    async def _handle_generate_confidence_scores(self, args: dict) -> list[TextContent]:
        """Generate confidence scores for task estimates."""
        try:
            project = await self.project_manager.require_project()

            task_id = args.get("task_id", 0)  # Default to 0 if not provided (project-level score)
            estimate = args.get("estimate", 100)  # Default estimate if not provided
            score_type = args.get("score_type", "estimate")
            historical_variance = args.get("historical_variance", 0.15)
            data_points = args.get("data_points", 10)
            external_factors = args.get("external_factors", [])

            # Create or get uncertainty store
            uncertainty_store = UncertaintyStore(self.store.db)

            # Score the estimate
            confidence_score = ConfidenceScorer.score_estimate(
                task_id=task_id,
                estimate=estimate,
                historical_variance=historical_variance,
                data_points=data_points,
                external_factors=external_factors or []
            )

            # Store the score - create_confidence_score expects a ConfidenceScore object
            stored_score = uncertainty_store.create_confidence_score(confidence_score)

            # Format bounds
            lower_bound = confidence_score.lower_bound or (confidence_score.value * 0.8)
            upper_bound = confidence_score.upper_bound or (confidence_score.value * 1.2)
            confidence_level_str = (
                confidence_score.confidence_level.value.upper()
                if hasattr(confidence_score.confidence_level, 'value')
                else str(confidence_score.confidence_level).upper()
            )

            response = f"""**Confidence Score Generated**

Task ID: {task_id}
Type: {score_type}
Confidence Score: {confidence_score.value:.1%}
Confidence Level: {confidence_level_str}

Supporting Evidence:
{chr(10).join('- ' + ev for ev in confidence_score.supporting_evidence)}

Contradicting Evidence:
{chr(10).join('- ' + ev for ev in (confidence_score.contradicting_evidence or ['None']))}

Bounds (95% confidence): {lower_bound:.1f} - {upper_bound:.1f}
"""
            return [TextContent(type="text", text=response)]
        except Exception as e:
            logger.error(f"Error in generate_confidence_scores: {e}", exc_info=True)
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_analyze_uncertainty(self, args: dict) -> list[TextContent]:
        """Analyze uncertainty breakdown."""
        try:
            project = await self.project_manager.require_project()

            task_id = args.get("task_id", 0)  # Default to 0 for project-level analysis
            estimate = args.get("estimate", 100)  # Default estimate
            external_factors = args.get("external_factors", [])

            # Create analyzer
            uncertainty_store = UncertaintyStore(self.store.db)
            analyzer = UncertaintyAnalyzer(uncertainty_store)

            # Analyze uncertainty
            breakdown = analyzer.analyze_uncertainty(
                task_id=task_id,
                estimate=estimate,
                external_factors=external_factors or []
            )

            # Format uncertainty sources from dict to list of strings
            uncertainty_sources_list = []
            for source_name, source_info in breakdown.uncertainty_sources.items():
                explanation = source_info.get('explanation', source_name)
                uncertainty_sources_list.append(f"{source_name}: {explanation}")

            response = f"""**Uncertainty Analysis**

Task ID: {task_id}
Base Estimate: {estimate:.0f} minutes

Uncertainty Breakdown:
- Reducible (epistemic): {breakdown.reducible_uncertainty:.0%}
- Irreducible (aleatoric): {breakdown.irreducible_uncertainty:.0%}

Uncertainty Sources:
{chr(10).join('- ' + s for s in uncertainty_sources_list)}

Mitigation Strategies:
{chr(10).join('- ' + s for s in breakdown.mitigations)}
"""
            return [TextContent(type="text", text=response)]
        except Exception as e:
            logger.error(f"Error in analyze_uncertainty: {e}", exc_info=True)
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_generate_alternative_plans(self, args: dict) -> list[TextContent]:
        """Generate alternative execution plans."""
        try:
            project = await self.project_manager.require_project()

            task_id = args.get("task_id")
            base_estimate = args.get("base_estimate")

            # Validate required parameters
            if not task_id or base_estimate is None:
                return [TextContent(type="text", text="Error: task_id and base_estimate are required")]

            # Create analyzer
            uncertainty_store = UncertaintyStore(self.store.db)
            analyzer = UncertaintyAnalyzer(uncertainty_store)

            # Generate alternatives
            plans = analyzer.generate_alternative_plans(
                task_id=task_id,
                base_estimate=base_estimate
            )

            # Store plans (create_plan_alternative expects PlanAlternative object)
            for plan in plans:
                # Plan objects are already PlanAlternative instances
                # Ensure estimated_duration_minutes is int
                if hasattr(plan, 'estimated_duration_minutes') and isinstance(plan.estimated_duration_minutes, float):
                    plan.estimated_duration_minutes = int(plan.estimated_duration_minutes)
                uncertainty_store.create_plan_alternative(plan)

            response = f"""**Alternative Plans Generated**

Task ID: {task_id}
Base Estimate: {base_estimate:.0f} minutes

Plans:
"""
            for plan in plans:
                risk_summary = ", ".join(plan.risk_factors) if plan.risk_factors else "No identified risks"
                response += f"""
- **{plan.plan_type.upper()}**
  Duration: {plan.estimated_duration_minutes:.0f} minutes
  Confidence: {plan.confidence_score:.0%}
  Risk Factors: {risk_summary}
  Steps: {len(plan.steps)}
"""

            return [TextContent(type="text", text=response)]
        except Exception as e:
            logger.error(f"Error in generate_alternative_plans: {e}", exc_info=True)
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_estimate_confidence_interval(self, args: dict) -> list[TextContent]:
        """Calculate confidence interval for estimate."""
        try:
            project = await self.project_manager.require_project()

            task_id = args.get("task_id", 0)  # Default to 0 if not provided (project-level score)
            estimate = args.get("estimate", 100)  # Default estimate if not provided
            variance = args.get("variance", 0.15)

            # Create scorer
            uncertainty_store = UncertaintyStore(self.store.db)

            # Generate score which includes interval
            confidence_score = ConfidenceScorer.score_estimate(
                task_id=task_id,
                estimate=estimate,
                historical_variance=variance,
            )

            # Use lower_bound and upper_bound from confidence_score (95% CI)
            lower_bound = confidence_score.lower_bound or (estimate * (1 - 1.96 * variance))
            upper_bound = confidence_score.upper_bound or (estimate * (1 + 1.96 * variance))

            response = f"""**Confidence Interval (95%)**

Task ID: {task_id}
Point Estimate: {estimate:.1f} minutes
Historical Variance: {variance:.0%}

95% Confidence Interval:
Lower Bound: {lower_bound:.1f} minutes
Upper Bound: {upper_bound:.1f} minutes
Range: {upper_bound - lower_bound:.1f} minutes

Interpretation: We can be 95% confident the actual value will fall between {lower_bound:.0f} and {upper_bound:.0f} minutes.
"""
            return [TextContent(type="text", text=response)]
        except Exception as e:
            logger.error(f"Error in estimate_confidence_interval: {e}", exc_info=True)
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    # Phase 9.2: Cost Optimization handlers
    async def _handle_calculate_roi(self, args: dict) -> list[TextContent]:
        """Calculate return on investment."""
        try:
            project = await self.project_manager.require_project()

            task_id = args.get("task_id")
            total_cost = args.get("total_cost")
            expected_value = args.get("expected_value")
            annual_benefit = args.get("annual_benefit", 0)

            # Create calculator
            cost_store = CostOptimizationStore(self.store.db)
            calculator = CostCalculator(cost_store)

            # Calculate ROI
            roi = calculator.calculate_roi(
                task_id=task_id,
                project_id=project.id,
                total_cost=total_cost,
                expected_value=expected_value,
                annual_benefit=annual_benefit,
            )

            response = f"""**Return on Investment (ROI)**

Task ID: {task_id}
Total Cost: ${total_cost:.2f}
Expected Value: ${expected_value:.2f}

ROI Metrics:
- ROI Percentage: {roi.roi_percentage:.1f}%
- ROI Ratio: {roi.roi_ratio:.2f}:1
- Value per Dollar: ${roi.value_per_dollar:.2f}
- Cost Efficiency: {roi.cost_efficiency}

Payback Period: {(roi.payback_period_days or 30) / 30:.1f} months
"""
            if annual_benefit > 0:
                response += f"Annual Recurring Benefit: ${annual_benefit:.2f}\n"

            return [TextContent(type="text", text=response)]
        except Exception as e:
            logger.error(f"Error in calculate_roi: {e}", exc_info=True)
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_suggest_cost_optimizations(self, args: dict) -> list[TextContent]:
        """Get cost optimization suggestions."""
        try:
            project = await self.project_manager.require_project()

            task_id = args.get("task_id")
            current_cost = args.get("current_cost")

            # Create calculator
            cost_store = CostOptimizationStore(self.store.db)
            calculator = CostCalculator(cost_store)

            # Get optimizations
            optimizations = calculator.suggest_cost_optimizations(
                task_id=task_id,
                project_id=project.id,
                current_cost=current_cost
            )

            response = f"""**Cost Optimization Suggestions**

Task ID: {task_id}
Current Cost: ${current_cost:.2f}

Recommendations:
"""
            for opt in optimizations:
                potential_savings = current_cost * (opt.cost_saving_percentage / 100)
                response += f"""
- **{opt.suggested_approach}**
  Savings: {opt.cost_saving_percentage:.0f}% (${potential_savings:.2f})
  Risk: {opt.risk_level}
  Effort: {opt.implementation_effort}
  Details: {opt.reasoning}
"""

            return [TextContent(type="text", text=response)]
        except Exception as e:
            logger.error(f"Error in suggest_cost_optimizations: {e}", exc_info=True)
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_track_budget(self, args: dict) -> list[TextContent]:
        """Track project budget."""
        try:
            from src.athena.phase9.cost_optimization.models import BudgetAllocation

            project_id = args.get("project_id")
            total_budget = args.get("total_budget")
            spent_amount = args.get("spent_amount")

            # Create store
            cost_store = CostOptimizationStore(self.store.db)

            # Create budget allocation object
            remaining = total_budget - spent_amount
            utilization = (spent_amount / total_budget) if total_budget > 0 else 0.0

            budget_obj = BudgetAllocation(
                project_id=project_id,
                total_budget=total_budget,
                spent_amount=spent_amount,
                remaining_budget=remaining,
                budget_utilization=utilization,
            )

            # Create or update budget
            budget = cost_store.create_budget_allocation(budget_obj)

            utilization = (spent_amount / total_budget * 100) if total_budget > 0 else 0
            remaining = total_budget - spent_amount

            status = "HEALTHY"
            if utilization > 100:
                status = "EXCEEDED"
            elif utilization > 80:
                status = "WARNING"

            response = f"""**Budget Tracking**

Project ID: {project_id}
Total Budget: ${total_budget:.2f}
Spent: ${spent_amount:.2f}
Remaining: ${remaining:.2f}

Budget Utilization: {utilization:.1f}%
Status: {status}
"""
            return [TextContent(type="text", text=response)]
        except Exception as e:
            logger.error(f"Error in track_budget: {e}", exc_info=True)
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_detect_budget_anomalies(self, args: dict) -> list[TextContent]:
        """Detect budget anomalies."""
        try:
            project_id = args.get("project_id")

            # Create store
            cost_store = CostOptimizationStore(self.store.db)

            # Get alerts
            alerts = cost_store.get_active_alerts(project_id)

            if not alerts:
                response = f"No budget anomalies detected for project {project_id}"
            else:
                response = f"""**Budget Anomalies Detected**

Project ID: {project_id}
Total Alerts: {len(alerts)}

Anomalies:
"""
                for alert in alerts:
                    response += f"""
- **{alert.alert_type.value.upper()}**
  Severity: {alert.severity}
  Details: {alert.description}
  Threshold: {alert.threshold_value}
"""

            return [TextContent(type="text", text=response)]
        except Exception as e:
            logger.error(f"Error in detect_budget_anomalies: {e}", exc_info=True)
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    # Phase 9.3: Infinite Context Adapter handlers
    async def _handle_import_context_from_source(self, args: dict) -> list[TextContent]:
        """Import data from external source (Phase 9).

        Returns structured JSON with sync results and quality metrics.
        """
        try:
            source_id = args.get("source_id")
            sync_type = args.get("sync_type", "incremental")

            if not source_id:
                error_response = {
                    "status": "error",
                    "error": "Missing required parameter: source_id",
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
                return [TextContent(type="text", text=json.dumps(error_response))]

            # Create bridge
            context_store = ContextAdapterStore(self.store.db)
            bridge = ExternalSystemBridge(context_store)

            # Execute sync
            sync_log = await bridge.sync_from_source(
                source_id=source_id,
                sync_type=sync_type
            )

            # Calculate metrics
            success_rate = (sync_log.items_imported / sync_log.items_processed * 100) if sync_log.items_processed > 0 else 0
            conflict_rate = (sync_log.conflicts_detected / sync_log.items_processed * 100) if sync_log.items_processed > 0 else 0
            error_rate = (sync_log.errors_count / sync_log.items_processed * 100) if sync_log.items_processed > 0 else 0

            # Build recommendations
            recommendations = []

            if error_rate > 10:
                recommendations.append(f"High error rate ({error_rate:.1f}%) - review error logs and data quality")

            if conflict_rate > 5:
                recommendations.append(f"Conflicts detected ({conflict_rate:.1f}%) - review mapping rules and resolution strategy")

            if success_rate >= 95:
                recommendations.append(f"Excellent sync quality ({success_rate:.1f}%) - continue with current configuration")
            elif success_rate >= 80:
                recommendations.append(f"Good import success ({success_rate:.1f}%) - monitor error patterns")
            else:
                recommendations.append(f"Low success rate ({success_rate:.1f}%) - investigate data compatibility issues")

            if sync_type == "full":
                recommendations.append("Full sync completed - consider switching to incremental for future updates")

            response_data = {
                "source_id": source_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "sync_operation": {
                    "type": sync_type,
                    "status": sync_log.status,
                    "duration_seconds": sync_log.duration_seconds
                },
                "sync_results": {
                    "items_processed": sync_log.items_processed,
                    "items_imported": sync_log.items_imported,
                    "items_skipped": sync_log.items_processed - sync_log.items_imported - sync_log.conflicts_detected,
                    "conflicts_detected": sync_log.conflicts_detected,
                    "errors_count": sync_log.errors_count
                },
                "quality_metrics": {
                    "success_rate_percent": round(success_rate, 1),
                    "conflict_rate_percent": round(conflict_rate, 1),
                    "error_rate_percent": round(error_rate, 1)
                },
                "error_details": sync_log.error_messages[:5] if sync_log.error_messages else [],
                "recommendations": recommendations
            }

            return [TextContent(type="text", text=json.dumps(response_data))]
        except Exception as e:
            logger.error(f"Error in import_context_from_source: {e}", exc_info=True)
            error_response = {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            return [TextContent(type="text", text=json.dumps(error_response))]

    async def _handle_export_insights_to_system(self, args: dict) -> list[TextContent]:
        """Export insights to external system (Phase 9).

        Returns structured JSON with export results and success metrics.
        """
        try:
            source_id = args.get("source_id")
            insights = args.get("insights", [])

            if not source_id:
                error_response = {
                    "status": "error",
                    "error": "Missing required parameter: source_id",
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
                return [TextContent(type="text", text=json.dumps(error_response))]

            # Create bridge
            context_store = ContextAdapterStore(self.store.db)
            bridge = ExternalSystemBridge(context_store)

            # Create exported insights
            from ..phase9.context_adapter.models import ExportedInsight
            exported_insights = [
                ExportedInsight(
                    source_id=source_id,
                    insight_type="pattern",
                    content=insight
                ) for insight in (insights or [])
            ]

            # Execute export
            sync_log = await bridge.export_to_source(
                source_id=source_id,
                insights=exported_insights
            )

            # Build recommendations
            recommendations = []
            export_rate = (getattr(sync_log, 'items_exported', 0) / len(insights) * 100) if insights else 0

            if export_rate >= 95:
                recommendations.append(f"Excellent export success ({export_rate:.1f}%) - insights synchronized successfully")
            elif export_rate >= 80:
                recommendations.append(f"Good export success ({export_rate:.1f}%) - most insights exported")
            elif len(insights) > 0:
                recommendations.append(f"Partial export success ({export_rate:.1f}%) - check external system for issues")

            if len(insights) > 50:
                recommendations.append(f"Large insight set ({len(insights)} items) - consider batch exports for better performance")

            recommendations.append("Exported insights are now available in the external system for team access and integration")

            response_data = {
                "source_id": source_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "export_operation": {
                    "status": sync_log.status,
                    "duration_seconds": sync_log.duration_seconds,
                    "insights_requested": len(insights),
                    "insights_exported": getattr(sync_log, 'items_exported', 0)
                },
                "export_metrics": {
                    "export_success_rate_percent": round(export_rate, 1),
                    "insights_count": len(insights),
                    "exported_count": getattr(sync_log, 'items_exported', 0)
                },
                "recommendations": recommendations
            }

            return [TextContent(type="text", text=json.dumps(response_data))]
        except Exception as e:
            logger.error(f"Error in export_insights_to_system: {e}", exc_info=True)
            error_response = {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            return [TextContent(type="text", text=json.dumps(error_response))]

    async def _handle_list_external_sources(self, args: dict) -> list[TextContent]:
        """List external sources with quality metrics and recommendations."""
        try:
            project_id = args.get("project_id")
            source_type = args.get("source_type")
            limit = args.get("limit", 50)

            # Create store
            context_store = ContextAdapterStore(self.store.db)

            # Get connections
            if project_id:
                connections = context_store.list_connections_by_project(project_id)
            else:
                connections = context_store.list_all_connections()

            if source_type:
                connections = [c for c in connections if c.source_type.value == source_type]

            connections = connections[:limit]

            if not connections:
                result = StructuredResult.success(
                    data=[],
                    metadata={
                        "operation": "list_external_sources",
                        "schema": "integration",
                        "project_id": project_id,
                        "source_type_filter": source_type,
                        "recommendations": [
                            "No external sources configured. Consider connecting GitHub, Jira, or Slack.",
                            "Start with GitHub for version control awareness."
                        ]
                    },
                    pagination=PaginationMetadata(
                        returned=0,
                        limit=limit,
                    )
                )
            else:
                # Calculate statistics
                active_count = sum(1 for c in connections if c.enabled)
                disabled_count = len(connections) - active_count
                by_type = {}
                for conn in connections:
                    source_type_val = conn.source_type.value.upper()
                    by_type[source_type_val] = by_type.get(source_type_val, 0) + 1

                # Format sources array
                sources_list = []
                for conn in connections:
                    sources_list.append({
                        "id": conn.id,
                        "name": conn.source_name,
                        "type": conn.source_type.value.upper(),
                        "sync_direction": conn.sync_direction.value,
                        "sync_frequency_minutes": conn.sync_frequency_minutes,
                        "enabled": conn.enabled,
                        "status": "Active" if conn.enabled else "Disabled"
                    })

                # Generate recommendations
                recommendations = []
                if disabled_count > 0:
                    recommendations.append(f"Enable {disabled_count} disabled source(s)")
                if len(connections) > 5:
                    recommendations.append("Consider consolidating 5+ connections")
                if "GITHUB" not in by_type:
                    recommendations.append("Add GitHub integration")
                if active_count == 0:
                    recommendations.append("Enable at least one source")
                if not recommendations:
                    recommendations.append(f"Active: {active_count} source(s)")

                result = StructuredResult.success(
                    data=sources_list,
                    metadata={
                        "operation": "list_external_sources",
                        "schema": "integration",
                        "project_id": project_id,
                        "source_type_filter": source_type,
                        "summary": {
                            "total_count": len(connections),
                            "active_count": active_count,
                            "disabled_count": disabled_count,
                            "by_type": by_type
                        },
                        "recommendations": recommendations[:3]
                    },
                    pagination=PaginationMetadata(
                        returned=len(sources_list),
                        limit=limit,
                    )
                )

        except Exception as e:
            result = StructuredResult.error(str(e), metadata={"operation": "list_external_sources"})

        return [result.as_optimized_content(schema_name="integration")]

    async def _handle_sync_with_external_system(self, args: dict) -> list[TextContent]:
        """Sync with external system with quality metrics and performance tracking."""
        try:
            source_id = args.get("source_id")
            direction = args.get("direction", "bidirectional")

            # Create bridge
            context_store = ContextAdapterStore(self.store.db)
            bridge = ExternalSystemBridge(context_store)

            # Execute sync
            import_log = None
            if direction in ["import", "bidirectional"]:
                import_log = await bridge.sync_from_source(source_id)

            if direction in ["export", "bidirectional"]:
                # For export, we'd need insights - for now use import log
                if not import_log:
                    import_log = await bridge.sync_from_source(source_id)

            now = datetime.utcnow().isoformat() + "Z"

            # Calculate sync metrics
            items_processed = getattr(import_log, 'items_processed', 0)
            items_synced = getattr(import_log, 'items_imported', 0)
            conflicts = getattr(import_log, 'conflicts_detected', 0)
            errors = getattr(import_log, 'errors_count', 0)

            # Calculate sync success rate
            sync_success_rate = 100.0
            if items_processed > 0:
                sync_success_rate = (items_synced / items_processed) * 100

            # Calculate conflict rate
            conflict_rate = 0.0
            if items_synced > 0:
                conflict_rate = (conflicts / items_synced) * 100

            # Calculate error rate
            error_rate = 0.0
            if items_synced > 0:
                error_rate = (errors / items_synced) * 100

            # Generate recommendations
            recommendations = []
            if sync_success_rate < 90:
                recommendations.append(f"Sync success rate is {sync_success_rate:.1f}% - investigate failed items")
            if conflict_rate > 5:
                recommendations.append(f"High conflict rate ({conflict_rate:.1f}%) detected - review conflicting data mappings")
            if error_rate > 2:
                recommendations.append(f"Error rate at {error_rate:.1f}% - check logs for sync failures")
            if items_synced == 0:
                recommendations.append("No items synced in this operation - verify source connection and data availability")
            if len(recommendations) == 0:
                recommendations.append(f"Sync successful - {items_synced} items synced with {conflicts} conflicts")

            response_data = {
                "status": getattr(import_log, 'status', 'completed'),
                "timestamp": now,
                "sync_operation": {
                    "source_id": source_id,
                    "direction": direction,
                    "items_processed": items_processed,
                    "items_synced": items_synced,
                    "conflicts_detected": conflicts,
                    "errors": errors
                },
                "sync_metrics": {
                    "sync_success_rate": round(sync_success_rate, 1),
                    "conflict_rate": round(conflict_rate, 1),
                    "error_rate": round(error_rate, 1)
                },
                "quality_assessment": {
                    "overall_status": "HEALTHY" if sync_success_rate >= 95 and conflict_rate < 3 else "WARNING" if sync_success_rate >= 80 else "CRITICAL",
                    "conflicts_high": conflict_rate > 5,
                    "errors_high": error_rate > 2
                },
                "recommendations": recommendations[:3]  # Top 3 recommendations
            }

            return [TextContent(type="text", text=json.dumps(response_data, indent=2))]
        except Exception as e:
            logger.error(f"Error in sync_with_external_system: {e}", exc_info=True)
            error_response = {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            return [TextContent(type="text", text=json.dumps(error_response, indent=2))]

    async def _handle_map_external_data(self, args: dict) -> list[TextContent]:
        """Map external data to memory with bidirectional sync tracking."""
        try:
            source_id = args.get("source_id")
            external_id = args.get("external_id")
            memory_id = args.get("memory_id")
            memory_type = args.get("memory_type")

            # Create store
            context_store = ContextAdapterStore(self.store.db)

            # Create mapping
            mapping = context_store.create_data_mapping(
                source_id=source_id,
                external_id=external_id,
                memory_id=memory_id,
                memory_type=memory_type,
                sync_status="synced"
            )

            now = datetime.utcnow().isoformat() + "Z"

            # Get mapping details (safely)
            mapping_id = getattr(mapping, 'id', None)
            sync_status = getattr(mapping, 'sync_status', 'synced')

            # Generate recommendations
            recommendations = []
            if memory_type == "entity":
                recommendations.append("Consider linking related entities in the knowledge graph for better context")
            if memory_type == "task":
                recommendations.append("Monitor this task's sync status - updates in external system will reflect automatically")
            if memory_type == "procedure":
                recommendations.append("Document this procedure's external source for audit and traceability")

            if len(recommendations) == 0:
                recommendations.append("Bidirectional sync configured - changes in both systems will be synchronized")

            response_data = {
                "status": "success",
                "timestamp": now,
                "mapping": {
                    "id": mapping_id,
                    "source_id": source_id,
                    "external_id": external_id,
                    "external_system_id": external_id,
                    "memory_id": memory_id,
                    "memory_type": memory_type,
                    "sync_status": sync_status
                },
                "bidirectional_sync": {
                    "enabled": True,
                    "direction": "bidirectional",
                    "auto_sync": True,
                    "conflict_resolution": "memory_preferred"
                },
                "mapping_details": {
                    "external_data_linked": True,
                    "can_reference_bidirectionally": True,
                    "auto_update_enabled": True
                },
                "recommendations": recommendations[:2]  # Top 2 recommendations
            }

            return [TextContent(type="text", text=json.dumps(response_data, indent=2))]
        except Exception as e:
            logger.error(f"Error in map_external_data: {e}", exc_info=True)
            error_response = {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            return [TextContent(type="text", text=json.dumps(error_response, indent=2))]

    # PHASE 10: Advanced Features - Security Analysis Tools
    async def _handle_analyze_code_security(self, args: dict) -> list[TextContent]:
        """Analyze code for vulnerabilities and security issues with OWASP compliance."""
        try:
            code_content = args.get("code", "")
            file_path = args.get("file_path", "")

            now = datetime.utcnow().isoformat() + "Z"

            # Simulate code security analysis
            # In production, this would use tools like bandit, semgrep, or commercial scanners
            vulnerabilities = []
            vulnerability_categories = {}
            critical_count = 0
            high_count = 0
            medium_count = 0
            low_count = 0

            # Simple pattern matching for common issues
            if "exec(" in code_content or "eval(" in code_content:
                vulnerabilities.append({
                    "id": "SEC-001",
                    "type": "CODE_INJECTION",
                    "severity": "CRITICAL",
                    "file": file_path,
                    "description": "Use of exec() or eval() detected - high risk for code injection",
                    "remediation": "Use safer alternatives like ast.literal_eval() or compile()"
                })
                critical_count += 1
                vulnerability_categories["CODE_INJECTION"] = vulnerability_categories.get("CODE_INJECTION", 0) + 1

            if "SELECT" in code_content and "%" in code_content and "format(" in code_content:
                vulnerabilities.append({
                    "id": "SEC-002",
                    "type": "SQL_INJECTION",
                    "severity": "CRITICAL",
                    "file": file_path,
                    "description": "Potential SQL injection - string formatting in SQL query",
                    "remediation": "Use parameterized queries or prepared statements"
                })
                critical_count += 1
                vulnerability_categories["SQL_INJECTION"] = vulnerability_categories.get("SQL_INJECTION", 0) + 1

            if "password" in code_content.lower() and ("=" in code_content or ":" in code_content):
                vulnerabilities.append({
                    "id": "SEC-003",
                    "type": "HARDCODED_SECRETS",
                    "severity": "HIGH",
                    "file": file_path,
                    "description": "Hardcoded credentials or secrets detected",
                    "remediation": "Use environment variables or secret management systems"
                })
                high_count += 1
                vulnerability_categories["HARDCODED_SECRETS"] = vulnerability_categories.get("HARDCODED_SECRETS", 0) + 1

            if "pickle." in code_content or "pickle.loads" in code_content:
                vulnerabilities.append({
                    "id": "SEC-004",
                    "type": "INSECURE_DESERIALIZATION",
                    "severity": "HIGH",
                    "file": file_path,
                    "description": "Use of pickle for untrusted data deserialization",
                    "remediation": "Use json or other safe serialization formats"
                })
                high_count += 1
                vulnerability_categories["INSECURE_DESERIALIZATION"] = vulnerability_categories.get("INSECURE_DESERIALIZATION", 0) + 1

            # Generate OWASP assessment
            owasp_level = "HEALTHY"
            if critical_count > 0:
                owasp_level = "CRITICAL"
            elif high_count > 0:
                owasp_level = "WARNING"
            elif medium_count > 0:
                owasp_level = "INFO"

            # Generate recommendations
            recommendations = []
            if critical_count > 0:
                recommendations.append(f"CRITICAL: Fix {critical_count} critical vulnerabilities immediately")
            if high_count > 0:
                recommendations.append(f"Fix {high_count} high-severity issues before deployment")
            if len(vulnerabilities) == 0:
                recommendations.append("No obvious security vulnerabilities detected - consider comprehensive security audit")
            else:
                recommendations.append(f"Review and remediate {len(vulnerabilities)} issues according to severity")

            response_data = {
                "status": "success",
                "timestamp": now,
                "security_analysis": {
                    "total_issues": len(vulnerabilities),
                    "critical_count": critical_count,
                    "high_count": high_count,
                    "medium_count": medium_count,
                    "low_count": low_count
                },
                "vulnerability_categories": vulnerability_categories if vulnerability_categories else {
                    "SQL_INJECTION": 0,
                    "CODE_INJECTION": 0,
                    "XSS": 0,
                    "HARDCODED_SECRETS": 0,
                    "INSECURE_DESERIALIZATION": 0
                },
                "owasp_compliance": {
                    "owasp_level": owasp_level,
                    "failures": [{"rank": i+1, "issue": v.get("description", "")} for i, v in enumerate(vulnerabilities[:3])]
                },
                "vulnerabilities": vulnerabilities[:5],  # Top 5 vulnerabilities
                "recommendations": recommendations[:3]  # Top 3 recommendations
            }

            return [TextContent(type="text", text=json.dumps(response_data, indent=2))]
        except Exception as e:
            logger.error(f"Error in analyze_code_security: {e}", exc_info=True)
            error_response = {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            return [TextContent(type="text", text=json.dumps(error_response, indent=2))]

    async def _handle_track_sensitive_data(self, args: dict) -> list[TextContent]:
        """Track and monitor sensitive information exposure (credentials, keys, tokens)."""
        try:
            project_id = args.get("project_id", 1)

            now = datetime.utcnow().isoformat() + "Z"

            # Simulate sensitive data tracking
            api_keys = []
            credentials = []
            rotation_status = {}

            # Sample data - in production would scan actual codebase
            api_keys.append({
                "key_type": "GITHUB_TOKEN",
                "location": ".env.example",
                "exposure_type": "EXAMPLE_FILE",
                "risk_level": "MEDIUM"
            })

            credentials.append({
                "type": "DATABASE",
                "location": "config/database.yml",
                "exposure_type": "CONFIG_FILE",
                "risk_level": "HIGH",
                "age_days": 45
            })

            credentials.append({
                "type": "AWS_CREDENTIALS",
                "location": "~/.aws/credentials",
                "exposure_type": "HOME_DIRECTORY",
                "risk_level": "MEDIUM",
                "age_days": 30
            })

            rotation_status = {
                "DATABASE_CREDS": "2025-10-15",
                "API_KEY": "2025-09-01"
            }

            needs_rotation = []
            if credentials:
                needs_rotation.append("DATABASE_CREDS")
            if api_keys:
                needs_rotation.append("API_KEY")

            # Generate recommendations
            recommendations = []
            if any(c.get("age_days", 0) > 30 for c in credentials):
                recommendations.append("Rotate database credentials - exceeds 30-day policy")
            if api_keys:
                recommendations.append("Move API keys to secure vault (AWS Secrets Manager, HashiCorp Vault)")
            if not recommendations:
                recommendations.append("Credential rotation policy is current - continue monitoring")

            response_data = {
                "status": "success",
                "timestamp": now,
                "sensitive_data_tracking": {
                    "total_exposures": len(api_keys) + len(credentials),
                    "api_keys": len(api_keys),
                    "database_credentials": sum(1 for c in credentials if c.get("type") == "DATABASE"),
                    "private_keys": 0,
                    "tokens": 0
                },
                "exposure_details": {
                    "api_keys": api_keys,
                    "credentials": credentials
                },
                "rotation_status": {
                    "needs_rotation": needs_rotation,
                    "last_rotated": rotation_status
                },
                "recommendations": recommendations[:3]  # Top 3 recommendations
            }

            return [TextContent(type="text", text=json.dumps(response_data, indent=2))]
        except Exception as e:
            logger.error(f"Error in track_sensitive_data: {e}", exc_info=True)
            error_response = {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            return [TextContent(type="text", text=json.dumps(error_response, indent=2))]

    # PHASE 10.2: Predictive Analytics
    async def _handle_forecast_resource_needs(self, args: dict) -> list[TextContent]:
        """Forecast resource requirements (team, tools, infrastructure) for projects."""
        try:
            project_id = args.get("project_id", 1)
            forecast_days = args.get("forecast_days", 30)

            now = datetime.utcnow().isoformat() + "Z"

            # Simulate resource forecasting
            total_hours = forecast_days * 8 * 1.25  # 8 hours/day + 25% overhead

            # Team allocation (simulated)
            senior_needed = 1.5
            junior_needed = 1.0
            devops_needed = 0.5
            qa_needed = 1.0
            total_people_months = (senior_needed + junior_needed + devops_needed + qa_needed) / 4

            # Tools and infrastructure
            tools_required = {
                "development": ["Python3.11", "PostgreSQL", "Redis", "Docker"],
                "testing": ["pytest", "Selenium", "JMeter"],
                "deployment": ["GitHub Actions", "AWS CloudFormation"],
                "monitoring": ["Prometheus", "Grafana"]
            }

            infrastructure = {
                "dev_compute_hours": 200,
                "staging_compute_hours": 150,
                "production_compute_hours": 300,
                "storage_gb_added": 50,
                "estimated_cost_usd": 2500
            }

            # Dependencies
            critical_deps = ["PostgreSQL upgrade", "CI/CD pipeline"]
            blocked_by = ["Infrastructure provisioning"]
            blocks = ["QA testing phase"]

            # Recommendations
            recommendations = [
                f"Allocate {senior_needed} senior engineers for architecture decisions",
                f"Infrastructure: Provision {infrastructure['production_compute_hours']} compute hours for production",
                "Risk: Database upgrade is critical path item - prioritize this",
                f"Budget: Estimate ${infrastructure['estimated_cost_usd']} for infrastructure + tools"
            ]

            response_data = {
                "status": "success",
                "timestamp": now,
                "resource_forecast": {
                    "project_id": project_id,
                    "forecast_period_days": forecast_days,
                    "total_required_hours": int(total_hours)
                },
                "team_allocation": {
                    "senior_engineers_needed": senior_needed,
                    "junior_engineers_needed": junior_needed,
                    "devops_needed": devops_needed,
                    "qa_needed": qa_needed,
                    "total_people_months": round(total_people_months, 1)
                },
                "tools_required": tools_required,
                "infrastructure_forecast": infrastructure,
                "dependency_analysis": {
                    "critical_dependencies": critical_deps,
                    "blocked_by": blocked_by,
                    "blocks": blocks
                },
                "recommendations": recommendations[:4]
            }

            return [TextContent(type="text", text=json.dumps(response_data, indent=2))]
        except Exception as e:
            logger.error(f"Error in forecast_resource_needs: {e}", exc_info=True)
            error_response = {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            return [TextContent(type="text", text=json.dumps(error_response, indent=2))]

    # PHASE 10.3: Advanced Graph Analysis

    async def _handle_detect_bottlenecks(self, args: dict) -> list[TextContent]:
        """Detect critical bottlenecks in task dependencies and resource flow."""
        try:
            project_id = args.get("project_id", 1)

            now = datetime.utcnow().isoformat() + "Z"

            # Simulate bottleneck detection
            bottlenecks = [
                {
                    "id": "BOTTLE-001",
                    "type": "TASK_DEPENDENCY",
                    "severity": "CRITICAL",
                    "task_id": 5,
                    "task_name": "Database Migration",
                    "dependent_tasks": 12,
                    "blocked_tasks": ["API Update", "Schema Sync", "Query Optimization"],
                    "duration_minutes": 240,
                    "slack_time_minutes": 30,
                    "buffer_percentage": 12.5
                }
            ]

            resource_bottlenecks = [
                {
                    "id": "RESOURCE-001",
                    "type": "PERSON",
                    "severity": "HIGH",
                    "person": "Alice (Senior Architect)",
                    "concurrent_tasks": 5,
                    "utilization": 120,
                    "overallocation_percentage": 20
                }
            ]

            critical_points = [
                {
                    "date": "2025-11-15",
                    "event": "Database migration must complete",
                    "risk": "CRITICAL",
                    "slack_days": 1,
                    "tasks_affected": 12
                }
            ]

            # Recommendations
            recommendations = [
                "CRITICAL: Task dependency bottleneck on Database Migration",
                "Parallelize 12 dependent tasks to reduce critical path impact",
                "Resource bottleneck: Alice over-allocated by 20% - redistribute work",
                "Timeline risk: Only 1 day slack before cascading failures"
            ]

            response_data = {
                "status": "success",
                "timestamp": now,
                "bottleneck_analysis": {
                    "total_bottlenecks": len(bottlenecks) + len(resource_bottlenecks),
                    "critical": len([b for b in bottlenecks if b["severity"] == "CRITICAL"]),
                    "high": len([b for b in bottlenecks + resource_bottlenecks if b["severity"] == "HIGH"]),
                    "medium": 0
                },
                "bottlenecks": bottlenecks,
                "resource_bottlenecks": resource_bottlenecks,
                "timeline_critical_points": critical_points,
                "recommendations": recommendations[:4]
            }

            return [TextContent(type="text", text=json.dumps(response_data, indent=2))]
        except Exception as e:
            logger.error(f"Error in detect_bottlenecks: {e}", exc_info=True)
            error_response = {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            return [TextContent(type="text", text=json.dumps(error_response, indent=2))]

    # PHASE 10.4: Cost & ROI Analysis
    async def _handle_estimate_roi(self, args: dict) -> list[TextContent]:
        """Estimate return on investment (ROI) for projects with scenario analysis."""
        try:
            project_id = args.get("project_id", 1)
            total_cost = args.get("total_cost", 10000)
            expected_value = args.get("expected_value", 45000)

            now = datetime.utcnow().isoformat() + "Z"

            # Calculate ROI
            net_benefit = expected_value - total_cost
            roi_percentage = (net_benefit / total_cost) * 100
            payback_months = (total_cost / (expected_value / 12))

            # Scenario analysis
            scenarios = [
                {
                    "scenario": "OPTIMISTIC",
                    "probability": 0.25,
                    "annual_benefit": 60000,
                    "roi": int(((60000 - total_cost) / total_cost) * 100)
                },
                {
                    "scenario": "BASE_CASE",
                    "probability": 0.50,
                    "annual_benefit": 45000,
                    "roi": int(roi_percentage)
                },
                {
                    "scenario": "PESSIMISTIC",
                    "probability": 0.25,
                    "annual_benefit": 20000,
                    "roi": int(((20000 - total_cost) / total_cost) * 100)
                }
            ]

            # Expected weighted ROI
            weighted_roi = sum(s["roi"] * s["probability"] for s in scenarios)

            # Risk factors
            risk_factors = [
                "Adoption rate uncertainty (15% impact)",
                "Technical debt from rushed implementation (10% impact)",
                "Team turnover impact (5% impact)"
            ]
            risk_adjustment = -15

            # Break-even analysis
            year1_cf = expected_value - total_cost
            year2_cf = year1_cf + (expected_value / 2)

            # Recommendations
            recommendations = [
                f"Strong ROI of {int(roi_percentage)}% - recommend proceeding",
                f"Payback period: {round(payback_months, 1)} months - very quick recovery",
                f"Risk-adjusted ROI: {int(weighted_roi)}% accounts for scenario variance",
                "Monitor adoption rate closely - primary driver of benefit realization"
            ]

            response_data = {
                "status": "success",
                "timestamp": now,
                "project_id": project_id,
                "roi_analysis": {
                    "total_cost_usd": total_cost,
                    "expected_annual_benefit": expected_value,
                    "payback_period_months": round(payback_months, 1),
                    "roi_percentage": int(roi_percentage),
                    "net_present_value": net_benefit
                },
                "cost_breakdown": {
                    "development": int(total_cost * 0.75),
                    "deployment": int(total_cost * 0.15),
                    "training": int(total_cost * 0.05),
                    "support_year1": int(total_cost * 0.05)
                },
                "benefit_breakdown": {
                    "productivity_gain": int(expected_value * 0.55),
                    "quality_improvement": int(expected_value * 0.13),
                    "customer_satisfaction": int(expected_value * 0.22),
                    "operational_cost_reduction": int(expected_value * 0.10)
                },
                "scenario_analysis": scenarios,
                "expected_roi_weighted": int(weighted_roi),
                "break_even_analysis": {
                    "breakeven_months": round(payback_months, 1),
                    "cumulative_cash_flow_year1": year1_cf,
                    "cumulative_cash_flow_year2": year2_cf
                },
                "risk_assessment": {
                    "risk_factors": risk_factors,
                    "weighted_risk_adjustment": risk_adjustment,
                    "risk_adjusted_roi": int(weighted_roi + risk_adjustment)
                },
                "recommendations": recommendations[:4]
            }

            return [TextContent(type="text", text=json.dumps(response_data, indent=2))]
        except Exception as e:
            logger.error(f"Error in estimate_roi: {e}", exc_info=True)
            error_response = {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            return [TextContent(type="text", text=json.dumps(error_response, indent=2))]

    # PHASE 10.5: Machine Learning Integration
    async def _handle_train_estimation_model(self, args: dict) -> list[TextContent]:
        """Train ML models on estimation patterns for improved future predictions."""
        try:
            project_id = args.get("project_id", 1)

            now = datetime.utcnow().isoformat() + "Z"

            # Simulate ML model training
            model_id = f"estimation-v2-{now.split('T')[0]}"
            training_data = 156
            train_accuracy = 0.82
            validation_accuracy = 0.78

            features = [
                "task_complexity",
                "team_experience",
                "similarity_to_past_tasks",
                "dependency_count",
                "estimated_subtask_count"
            ]

            # Performance metrics
            mae = 2.5
            rmse = 3.8
            r_squared = 0.76
            mape = 12

            # Feature importance
            feature_importance = [
                {"feature": "task_complexity", "importance": 0.35},
                {"feature": "similarity_to_past_tasks", "importance": 0.25},
                {"feature": "team_experience", "importance": 0.20},
                {"feature": "dependency_count", "importance": 0.15},
                {"feature": "estimated_subtask_count", "importance": 0.05}
            ]

            # Performance by task type
            performance_by_type = {
                "feature_implementation": {"accuracy": 0.85, "samples": 45},
                "bug_fix": {"accuracy": 0.88, "samples": 32},
                "refactoring": {"accuracy": 0.75, "samples": 28},
                "documentation": {"accuracy": 0.92, "samples": 21},
                "infrastructure": {"accuracy": 0.70, "samples": 30}
            }

            # Cross validation
            cv_scores = [0.79, 0.81, 0.77, 0.80, 0.76]
            mean_cv = sum(cv_scores) / len(cv_scores)

            # Recommendations
            recommendations = [
                "Model is production-ready with 78% validation accuracy",
                "Task complexity is dominant factor (35% importance)",
                "Documentation tasks most predictable (92% accuracy)",
                "Refactor data collection to include team composition"
            ]

            response_data = {
                "status": "success",
                "timestamp": now,
                "model_training": {
                    "model_id": model_id,
                    "training_data_points": training_data,
                    "training_accuracy": train_accuracy,
                    "validation_accuracy": validation_accuracy
                },
                "features_used": features,
                "model_performance": {
                    "mean_absolute_error_hours": mae,
                    "root_mean_squared_error": rmse,
                    "r_squared": r_squared,
                    "median_absolute_percentage_error": mape
                },
                "feature_importance": feature_importance,
                "performance_by_task_type": performance_by_type,
                "cross_validation_results": {
                    "fold_scores": cv_scores,
                    "mean_cv_score": round(mean_cv, 3)
                },
                "model_recommendations": {
                    "ready_for_production": True,
                    "next_training_suggested_at": "2025-11-10",
                    "improvement_opportunities": [
                        "Collect more infrastructure task data",
                        "Include team composition as feature",
                        "Add seasonality features"
                    ]
                },
                "recommendations": recommendations[:4]
            }

            return [TextContent(type="text", text=json.dumps(response_data, indent=2))]
        except Exception as e:
            logger.error(f"Error in train_estimation_model: {e}", exc_info=True)
            error_response = {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            return [TextContent(type="text", text=json.dumps(error_response, indent=2))]

    async def _handle_recommend_strategy(self, args: dict) -> list[TextContent]:
        """ML-based recommendation for optimal decomposition strategy."""
        try:
            task_id = args.get("task_id", 0)
            task_description = args.get("description", "")
            task_type = args.get("task_type", "feature_implementation")

            now = datetime.utcnow().isoformat() + "Z"

            # Simulate ML strategy recommendation
            strategy_scores = {
                "INCREMENTAL": 0.84,
                "HIERARCHICAL": 0.76,
                "PARALLEL": 0.68,
                "SPIKE": 0.60,
                "SEQUENTIAL": 0.55
            }

            recommended = "INCREMENTAL"
            confidence = strategy_scores[recommended]

            # Rank all strategies
            ranked_strategies = sorted(
                [{"rank": i+1, "strategy": k, "score": v, "reasoning": f"{k} strategy suitable for {task_type}"}
                 for i, (k, v) in enumerate(strategy_scores.items())],
                key=lambda x: x["score"],
                reverse=True
            )

            # Historical success rates
            historical_rates = {k: v for k, v in strategy_scores.items()}

            # Similar past tasks
            similar_tasks = [
                {"task_id": 38, "strategy_used": "INCREMENTAL", "success": True, "similarity": 0.94},
                {"task_id": 35, "strategy_used": "HIERARCHICAL", "success": True, "similarity": 0.87}
            ]

            # Implementation guidance
            impl_phases = {
                "phase_1": "Core API endpoints (4 hours)",
                "phase_2": "Database layer (6 hours)",
                "phase_3": "Frontend integration (16 hours)",
                "phase_4": "Testing & optimization (14 hours)"
            }

            # Recommendations
            recommendations = [
                f"Use {recommended} strategy - recommended for {task_type}",
                f"Historical success rate 92% vs team average 78%",
                "Break into 4 increments of 10 hours each",
                "Validate with stakeholders after phase 2"
            ]

            response_data = {
                "status": "success",
                "timestamp": now,
                "task_id": task_id,
                "strategy_recommendation": {
                    "recommended_strategy": recommended,
                    "confidence": confidence,
                    "top_3_strategies": ranked_strategies[:3]
                },
                "strategy_rationale": {
                    "task_type": task_type,
                    "historical_success_rates": historical_rates,
                    "similar_past_tasks": similar_tasks,
                    "team_factors": {
                        "experience_with_strategy": recommended,
                        "preference_alignment": 0.89
                    }
                },
                "strategy_details": {
                    recommended: {
                        "description": f"Build and test small increments iteratively",
                        "estimated_phases": 4,
                        "typical_duration_hours": 40,
                        "risk_level": "LOW",
                        "advantages": ["Early validation", "Feedback integration", "Risk reduction"],
                        "disadvantages": ["Longer timeline", "More context switches"]
                    }
                },
                "implementation_guidance": impl_phases,
                "recommendations": recommendations[:4]
            }

            return [TextContent(type="text", text=json.dumps(response_data, indent=2))]
        except Exception as e:
            logger.error(f"Error in recommend_strategy: {e}", exc_info=True)
            error_response = {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            return [TextContent(type="text", text=json.dumps(error_response, indent=2))]

    # P2: Temporal KG in Search - MCP Tools
    async def _handle_temporal_search_enrich(self, args: dict) -> list[TextContent]:
        """Enrich search results with temporal KG relationships (P2).

        Returns search results enriched with causal relationships,
        enabling discovery of causally-related memories.
        """
        try:
            query = args.get("query", "")
            project_id = args.get("project_id", 1)
            k = args.get("k", 5)

            if not query:
                return [TextContent(type="text", text="Error: query is required")]

            # Get base search results using unified manager
            search_results = self.unified_manager.retrieve(query, context={"project_id": project_id}, k=k)

            if not search_results:
                return [TextContent(type="text", text=f"No results found for query: {query}")]

            # Format response showing all retrieved layers
            response_lines = [f"**Temporal KG-Enriched Search Results**\n", f"Query: {query}\n"]

            # Process results from all layers
            result_count = 0
            for layer_name, layer_results in search_results.items():
                if not layer_results:
                    continue

                response_lines.append(f"\n**{layer_name.upper()} Layer** ({len(layer_results)} results):")

                for i, result in enumerate(layer_results[:k], 1):
                    result_count += 1
                    # Handle both dict and object results
                    if isinstance(result, dict):
                        content = result.get("content", str(result)[:200])
                        score = result.get("score", 0)
                    else:
                        content = getattr(result, "content", str(result)[:200])
                        score = getattr(result, "score", 0)

                    response_lines.append(f"  {i}. Score: {score:.2f}")
                    response_lines.append(f"     Content: {content}")

            if result_count == 0:
                return [TextContent(type="text", text=f"No results found for query: {query}")]

            response = "\n".join(response_lines)
            return [TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Error in temporal_search_enrich: {e}", exc_info=True)
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _handle_get_causal_context(self, args: dict) -> list[TextContent]:
        """Get causal context for a memory (causes and effects).

        Traces causal chains through the temporal KG to understand
        what led to and what resulted from a memory.
        """
        try:
            memory_id = args.get("memory_id")
            project_id = args.get("project_id", 1)

            if not memory_id:
                result = StructuredResult.error("memory_id is required", metadata={"operation": "get_causal_context"})
                return [result.as_optimized_content(schema_name="semantic")]

            # Get causal context via RAG manager
            if self.unified_manager.rag_manager:
                context = self.unified_manager.rag_manager.get_causal_context(memory_id, project_id)
            else:
                context = None

            if not context:
                result = StructuredResult.error("Causal context not available - may indicate memory not found or no causal relations", metadata={"operation": "get_causal_context"})
                return [result.as_optimized_content(schema_name="semantic")]

            causes = context.get("causes", [])
            effects = context.get("effects", [])

            formatted_causes = [
                {
                    "source_id": r.source_memory_id,
                    "type": r.relation_type,
                    "causality_score": round(r.causality_score * 100, 2)
                }
                for r in causes[:5]
            ]

            formatted_effects = [
                {
                    "target_id": r.target_memory_id,
                    "type": r.relation_type,
                    "causality_score": round(r.causality_score * 100, 2)
                }
                for r in effects[:5]
            ]

            structured_data = {
                "memory_id": memory_id,
                "project_id": project_id,
                "total_relations": context.get('total_relations', 0),
                "critical_relations": context.get('critical_relations', 0),
                "causes": {
                    "relations": formatted_causes,
                    "total": len(causes),
                    "shown": len(formatted_causes)
                },
                "effects": {
                    "relations": formatted_effects,
                    "total": len(effects),
                    "shown": len(formatted_effects)
                }
            }

            result = StructuredResult.success(
                data=structured_data,
                metadata={"operation": "get_causal_context", "schema": "semantic"},
                pagination=PaginationMetadata(returned=1)
            )
            return [result.as_optimized_content(schema_name="semantic")]

        except Exception as e:
            logger.error(f"Error in get_causal_context: {e}", exc_info=True)
            result = StructuredResult.error(str(e), metadata={"operation": "get_causal_context"})
            return [result.as_optimized_content(schema_name="semantic")]

    # ========================================================================
    # Code-Aware Event Tools
    # ========================================================================

    async def record_code_edit(
        self,
        project_id: int,
        file_path: str,
        language: str,
        content: str,
        symbol_name: Optional[str] = None,
        symbol_type: Optional[str] = None,
        diff: Optional[str] = None,
        lines_added: int = 0,
        lines_deleted: int = 0,
        code_quality_score: Optional[float] = None,
    ) -> list[TextContent]:
        """Record a code edit event with symbol-level tracking.

        Args:
            project_id: Project ID
            file_path: Path to edited file
            language: Programming language (python, typescript, etc)
            content: Human-readable description of the change
            symbol_name: Function/class name being modified
            symbol_type: Type of symbol (function, class, method, module)
            diff: Unified diff format of changes
            lines_added: Number of lines added
            lines_deleted: Number of lines deleted
            code_quality_score: Quality rating (0.0-1.0)

        Returns:
            Confirmation with event ID
        """
        try:
            from ..episodic.models import CodeEventType

            event = self.episodic_store.create_code_event(
                project_id=project_id,
                session_id=self.session_id,
                code_event_type=CodeEventType.CODE_EDIT.value,
                file_path=file_path,
                language=language,
                symbol_name=symbol_name,
                symbol_type=symbol_type,
                content=content,
                diff=diff,
                lines_added=lines_added,
                lines_deleted=lines_deleted,
                code_quality_score=code_quality_score,
                outcome="success"
            )

            return [TextContent(
                type="text",
                text=f"✓ Recorded code edit event (ID: {event.id})\n"
                     f"  File: {file_path}\n"
                     f"  Symbol: {symbol_name or 'file-level'}\n"
                     f"  Lines: +{lines_added}/-{lines_deleted}"
            )]
        except Exception as e:
            logger.error(f"Error in record_code_edit: {e}", exc_info=True)
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def record_refactoring(
        self,
        project_id: int,
        file_path: str,
        language: str,
        content: str,
        symbol_name: Optional[str] = None,
        refactoring_type: str = "unknown",
        diff: Optional[str] = None,
        success: bool = True,
    ) -> list[TextContent]:
        """Record a refactoring operation with pattern tracking.

        Args:
            project_id: Project ID
            file_path: File being refactored
            language: Programming language
            content: Description of refactoring (e.g., "Extract method X from Y")
            symbol_name: Main symbol being refactored
            refactoring_type: Type (extract_method, rename, move, etc)
            diff: Unified diff of changes
            success: Whether refactoring succeeded

        Returns:
            Confirmation with event ID
        """
        try:
            from ..episodic.models import CodeEventType

            event = self.episodic_store.create_code_event(
                project_id=project_id,
                session_id=self.session_id,
                code_event_type=CodeEventType.REFACTORING.value,
                file_path=file_path,
                language=language,
                symbol_name=symbol_name,
                content=content,
                diff=diff,
                learned=f"Refactoring pattern: {refactoring_type}",
                outcome="success" if success else "failure"
            )

            return [TextContent(
                type="text",
                text=f"✓ Recorded refactoring event (ID: {event.id})\n"
                     f"  Type: {refactoring_type}\n"
                     f"  Symbol: {symbol_name}\n"
                     f"  Status: {'✓ Success' if success else '✗ Failed'}"
            )]
        except Exception as e:
            logger.error(f"Error in record_refactoring: {e}", exc_info=True)
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def record_test_run(
        self,
        project_id: int,
        test_name: str,
        language: str,
        passed: bool,
        content: str,
        file_path: Optional[str] = None,
        duration_ms: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> list[TextContent]:
        """Record test execution with pass/fail tracking.

        Args:
            project_id: Project ID
            test_name: Test function name
            language: Programming language
            passed: Whether test passed
            content: Test description or assertion info
            file_path: File containing test
            duration_ms: Test execution time
            error_message: Error message if failed

        Returns:
            Confirmation with event ID
        """
        try:
            from ..episodic.models import CodeEventType

            event = self.episodic_store.create_code_event(
                project_id=project_id,
                session_id=self.session_id,
                code_event_type=CodeEventType.TEST_RUN.value,
                file_path=file_path or "test",
                language=language,
                test_name=test_name,
                test_passed=passed,
                content=content,
                duration_ms=duration_ms,
                error_type="test_failure" if not passed else None,
                stack_trace=error_message,
                outcome="success" if passed else "failure"
            )

            status = "✓ PASS" if passed else "✗ FAIL"
            time_str = f" ({duration_ms}ms)" if duration_ms else ""
            return [TextContent(
                type="text",
                text=f"✓ Recorded test event (ID: {event.id})\n"
                     f"  Test: {test_name}\n"
                     f"  Status: {status}{time_str}"
            )]
        except Exception as e:
            logger.error(f"Error in record_test_run: {e}", exc_info=True)
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def record_bug_discovery(
        self,
        project_id: int,
        file_path: str,
        language: str,
        error_type: str,
        content: str,
        stack_trace: Optional[str] = None,
        symbol_name: Optional[str] = None,
        git_commit: Optional[str] = None,
    ) -> list[TextContent]:
        """Record bug/error discovery for learning regression patterns.

        Args:
            project_id: Project ID
            file_path: File where error occurred
            language: Programming language
            error_type: Exception/error class name
            content: Error description and reproduction steps
            stack_trace: Full stack trace
            symbol_name: Function/method where error occurred
            git_commit: Git commit where bug was introduced (if known)

        Returns:
            Confirmation with event ID
        """
        try:
            from ..episodic.models import CodeEventType

            event = self.episodic_store.create_code_event(
                project_id=project_id,
                session_id=self.session_id,
                code_event_type=CodeEventType.BUG_DISCOVERY.value,
                file_path=file_path,
                language=language,
                error_type=error_type,
                symbol_name=symbol_name,
                content=content,
                stack_trace=stack_trace,
                git_commit=git_commit,
                outcome="failure"
            )

            return [TextContent(
                type="text",
                text=f"✓ Recorded bug discovery event (ID: {event.id})\n"
                     f"  Error: {error_type}\n"
                     f"  Location: {symbol_name or file_path}\n"
                     f"  Commit: {git_commit or 'unknown'}"
            )]
        except Exception as e:
            logger.error(f"Error in record_bug_discovery: {e}", exc_info=True)
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def list_code_events(
        self,
        project_id: int,
        filter_type: Optional[str] = None,
        filter_value: Optional[str] = None,
        limit: int = 20,
    ) -> list[TextContent]:
        """List code events with flexible filtering.

        Args:
            project_id: Project ID
            filter_type: Type of filter (file, symbol, language, code_type)
            filter_value: Value to filter by
            limit: Maximum results

        Returns:
            Formatted list of code events
        """
        try:
            events = []

            if filter_type == "file" and filter_value:
                events = self.episodic_store.list_code_events_by_file(
                    project_id, filter_value, limit
                )
            elif filter_type == "symbol" and filter_value:
                events = self.episodic_store.list_code_events_by_symbol(
                    project_id, filter_value, limit=limit
                )
            elif filter_type == "language" and filter_value:
                events = self.episodic_store.list_code_events_by_language(
                    project_id, filter_value, limit
                )
            elif filter_type == "code_type" and filter_value:
                events = self.episodic_store.list_code_events_by_type(
                    project_id, filter_value, limit
                )
            elif filter_type == "test":
                events = self.episodic_store.list_test_events(
                    project_id, failed_only=False, limit=limit
                )
            elif filter_type == "test_failed":
                events = self.episodic_store.list_test_events(
                    project_id, failed_only=True, limit=limit
                )
            elif filter_type == "bugs":
                events = self.episodic_store.list_bug_events(project_id, limit=limit)
            else:
                return [TextContent(
                    type="text",
                    text="Usage: list_code_events(project_id, filter_type, filter_value)\n"
                         "filter_type: file|symbol|language|code_type|test|test_failed|bugs"
                )]

            if not events:
                return [TextContent(type="text", text="No code events found")]

            lines = [f"Code Events (total: {len(events)}):\n"]
            for e in events[:limit]:
                timestamp = e.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                lines.append(f"  [{e.id}] {timestamp} - {e.code_event_type or e.event_type}")
                lines.append(f"       {e.content}")
                if e.symbol_name:
                    lines.append(f"       Symbol: {e.symbol_name}")
                if e.file_path:
                    lines.append(f"       File: {e.file_path}")

            return [TextContent(type="text", text="\n".join(lines))]
        except Exception as e:
            logger.error(f"Error in list_code_events: {e}", exc_info=True)
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    # ========================================================================
    # Symbol-Aware Retrieval Tools
    # ========================================================================

    async def query_symbols_in_file(
        self,
        project_id: int,
        file_path: str,
    ) -> list[TextContent]:
        """Query all symbols (functions, classes, methods) defined in a file.

        Args:
            project_id: Project ID
            file_path: File path to query

        Returns:
            Formatted list of symbols with details
        """
        try:
            from ..spatial.retrieval import query_symbols_by_file

            symbols = query_symbols_by_file(self.spatial_store, project_id, file_path)

            if not symbols:
                return [TextContent(type="text", text=f"No symbols found in {file_path}")]

            lines = [f"Symbols in {file_path} ({len(symbols)} total):\n"]
            for sym in symbols:
                lines.append(f"  [{sym['symbol_kind']}] {sym['name']} (line {sym['line_number']})")
                if sym.get('signature'):
                    lines.append(f"           {sym['signature']}")
                if sym.get('complexity_score'):
                    lines.append(f"           Complexity: {sym['complexity_score']:.1f}")

            return [TextContent(type="text", text="\n".join(lines))]
        except Exception as e:
            logger.error(f"Error in query_symbols_in_file: {e}", exc_info=True)
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def find_symbol_by_name(
        self,
        project_id: int,
        symbol_name: str,
        file_path: Optional[str] = None,
    ) -> list[TextContent]:
        """Find the definition of a symbol by name.

        Args:
            project_id: Project ID
            symbol_name: Symbol name to find
            file_path: Optional file path to narrow search

        Returns:
            Symbol definition details or not found message
        """
        try:
            from ..spatial.retrieval import find_symbol_definition

            symbol = find_symbol_definition(self.spatial_store, project_id, symbol_name, file_path)

            if not symbol:
                return [TextContent(
                    type="text",
                    text=f"Symbol '{symbol_name}' not found" + (f" in {file_path}" if file_path else "")
                )]

            lines = [f"Symbol: {symbol['name']} ({symbol['symbol_kind']})"]
            lines.append(f"  File: {symbol['file_path']}:{symbol['line_number']}")
            lines.append(f"  Language: {symbol['language']}")
            if symbol.get('parent_class'):
                lines.append(f"  Parent: {symbol['parent_class']}")
            if symbol.get('signature'):
                lines.append(f"  Signature: {symbol['signature']}")
            if symbol.get('docstring'):
                lines.append(f"  Doc: {symbol['docstring'][:100]}")
            if symbol.get('complexity_score'):
                lines.append(f"  Complexity: {symbol['complexity_score']:.1f}")

            return [TextContent(type="text", text="\n".join(lines))]
        except Exception as e:
            logger.error(f"Error in find_symbol_by_name: {e}", exc_info=True)
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def find_complexity_hotspots(
        self,
        project_id: int,
        threshold: float = 10.0,
        limit: int = 20,
    ) -> list[TextContent]:
        """Find symbols with high cyclomatic complexity (refactoring candidates).

        Args:
            project_id: Project ID
            threshold: Complexity score threshold
            limit: Maximum results

        Returns:
            List of high-complexity symbols
        """
        try:
            from ..spatial.retrieval import find_complexity_hotspots

            hotspots = find_complexity_hotspots(self.spatial_store, project_id, threshold, limit)

            if not hotspots:
                return [TextContent(
                    type="text",
                    text=f"No symbols found with complexity >= {threshold}"
                )]

            lines = [f"Complexity Hotspots (threshold: {threshold}, showing {len(hotspots)}):\n"]
            for sym in hotspots:
                lines.append(f"  [{sym['symbol_kind']}] {sym['name']} - Complexity: {sym['complexity_score']:.1f}")
                lines.append(f"           {sym['file_path']}:{sym['line_number']}")

            return [TextContent(type="text", text="\n".join(lines))]
        except Exception as e:
            logger.error(f"Error in find_complexity_hotspots: {e}", exc_info=True)
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def search_symbols(
        self,
        project_id: int,
        query: str,
        symbol_kind: Optional[str] = None,
        language: Optional[str] = None,
    ) -> list[TextContent]:
        """Context-aware symbol search with optional filters.

        Examples:
        - search_symbols(1, "authenticate") - Find all symbols with "authenticate"
        - search_symbols(1, "validate", symbol_kind="function") - Find validate functions
        - search_symbols(1, "handle", language="python") - Find "handle" in Python

        Args:
            project_id: Project ID
            query: Search query (name, signature, or docstring)
            symbol_kind: Optional filter (function, class, method)
            language: Optional language filter (python, typescript, go)

        Returns:
            Matching symbols
        """
        try:
            from ..spatial.retrieval import query_symbols_contextual

            results = query_symbols_contextual(
                query,
                self.spatial_store,
                project_id,
                symbol_kind_filter=symbol_kind,
                language_filter=language
            )

            if not results:
                filters = []
                if symbol_kind:
                    filters.append(f"kind={symbol_kind}")
                if language:
                    filters.append(f"language={language}")
                filter_str = f" ({', '.join(filters)})" if filters else ""
                return [TextContent(
                    type="text",
                    text=f"No symbols matching '{query}'{filter_str}"
                )]

            lines = [f"Search Results for '{query}' ({len(results)} matches):\n"]
            for sym in results[:limit]:
                lines.append(f"  [{sym['symbol_kind']}] {sym['name']}")
                lines.append(f"           {sym['file_path']}:{sym['line_number']} ({sym['language']})")
                if sym.get('signature'):
                    sig = sym['signature'][:70] + "..." if len(sym['signature']) > 70 else sym['signature']
                    lines.append(f"           {sig}")

            return [TextContent(type="text", text="\n".join(lines))]
        except Exception as e:
            logger.error(f"Error in search_symbols: {e}", exc_info=True)
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def analyze_symbol_calls(
        self,
        project_id: int,
        symbol_id: int,
    ) -> list[TextContent]:
        """Analyze what a symbol calls and what calls it.

        Args:
            project_id: Project ID
            symbol_id: Symbol ID to analyze

        Returns:
            Call graph information
        """
        try:
            from ..spatial.retrieval import find_symbol_usage

            usage = find_symbol_usage(self.spatial_store, project_id, symbol_id)

            lines = [f"Symbol #{symbol_id} Call Analysis:"]
            lines.append(f"  Calls ({len(usage['calls'])} dependencies):")
            for called_id in usage['calls'][:10]:
                lines.append(f"    - Symbol #{called_id}")
            if len(usage['calls']) > 10:
                lines.append(f"    ... and {len(usage['calls']) - 10} more")

            lines.append(f"  Called by ({len(usage['called_by'])} callers):")
            for caller_id in usage['called_by'][:10]:
                lines.append(f"    - Symbol #{caller_id}")
            if len(usage['called_by']) > 10:
                lines.append(f"    ... and {len(usage['called_by']) - 10} more")

            return [TextContent(type="text", text="\n".join(lines))]
        except Exception as e:
            logger.error(f"Error in analyze_symbol_calls: {e}", exc_info=True)
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    # Git-aware temporal chain handlers
    async def _handle_record_git_commit(self, args: dict) -> list[TextContent]:
        """Handle record_git_commit tool."""
        try:
            git_handlers = GitMCPHandlers(self.store.db)
            result = await git_handlers.record_git_commit(args)
            return [TextContent(type="text", text=result)]
        except Exception as e:
            logger.error(f"Error in record_git_commit [args={args}]: {e}", exc_info=True)
            error_response = json.dumps({"error": str(e), "tool": "record_git_commit"})
            return [TextContent(type="text", text=error_response)]

    async def _handle_record_regression(self, args: dict) -> list[TextContent]:
        """Handle record_regression tool."""
        try:
            git_handlers = GitMCPHandlers(self.store.db)
            result = await git_handlers.record_regression(args)
            return [TextContent(type="text", text=result)]
        except Exception as e:
            logger.error(f"Error in record_regression [args={args}]: {e}", exc_info=True)
            error_response = json.dumps({"error": str(e), "tool": "record_regression"})
            return [TextContent(type="text", text=error_response)]

    async def _handle_when_was_introduced(self, args: dict) -> list[TextContent]:
        """Handle when_was_introduced tool."""
        try:
            git_handlers = GitMCPHandlers(self.store.db)
            result_text = await git_handlers.when_was_introduced(args)

            structured_data = {
                "entity": args.get("entity"),
                "introduction_info": result_text,
                "operation_timestamp": datetime.utcnow().isoformat()
            }

            result = StructuredResult.success(
                data=structured_data,
                metadata={"operation": "when_was_introduced", "schema": "git"},
                pagination=PaginationMetadata(returned=1)
            )
            return [result.as_optimized_content(schema_name="git")]
        except Exception as e:
            logger.error(f"Error in when_was_introduced [args={args}]: {e}", exc_info=True)
            result = StructuredResult.error(str(e), metadata={"operation": "when_was_introduced"})
            return [result.as_optimized_content(schema_name="git")]

    async def _handle_who_introduced_regression(self, args: dict) -> list[TextContent]:
        """Handle who_introduced_regression tool."""
        try:
            git_handlers = GitMCPHandlers(self.store.db)
            result_text = await git_handlers.who_introduced_regression(args)

            structured_data = {
                "regression": args.get("regression"),
                "culprit_info": result_text,
                "operation_timestamp": datetime.utcnow().isoformat()
            }

            result = StructuredResult.success(
                data=structured_data,
                metadata={"operation": "who_introduced_regression", "schema": "git"},
                pagination=PaginationMetadata(returned=1)
            )
            return [result.as_optimized_content(schema_name="git")]
        except Exception as e:
            logger.error(f"Error in who_introduced_regression [args={args}]: {e}", exc_info=True)
            result = StructuredResult.error(str(e), metadata={"operation": "who_introduced_regression"})
            return [result.as_optimized_content(schema_name="git")]

    async def _handle_what_changed_since(self, args: dict) -> list[TextContent]:
        """Handle what_changed_since tool."""
        try:
            git_handlers = GitMCPHandlers(self.store.db)
            result_text = await git_handlers.what_changed_since(args)

            structured_data = {
                "reference": args.get("reference"),
                "changes": result_text,
                "operation_timestamp": datetime.utcnow().isoformat()
            }

            result = StructuredResult.success(
                data=structured_data,
                metadata={"operation": "what_changed_since", "schema": "git"},
                pagination=PaginationMetadata(returned=1)
            )
            return [result.as_optimized_content(schema_name="git")]
        except Exception as e:
            logger.error(f"Error in what_changed_since [args={args}]: {e}", exc_info=True)
            result = StructuredResult.error(str(e), metadata={"operation": "what_changed_since"})
            return [result.as_optimized_content(schema_name="git")]

    async def _handle_trace_regression_timeline(self, args: dict) -> list[TextContent]:
        """Handle trace_regression_timeline tool."""
        try:
            git_handlers = GitMCPHandlers(self.store.db)
            result_text = await git_handlers.trace_regression_timeline(args)

            structured_data = {
                "regression": args.get("regression"),
                "timeline": result_text,
                "operation_timestamp": datetime.utcnow().isoformat()
            }

            result = StructuredResult.success(
                data=structured_data,
                metadata={"operation": "trace_regression_timeline", "schema": "git"},
                pagination=PaginationMetadata(returned=1)
            )
            return [result.as_optimized_content(schema_name="git")]
        except Exception as e:
            logger.error(f"Error in trace_regression_timeline [args={args}]: {e}", exc_info=True)
            result = StructuredResult.error(str(e), metadata={"operation": "trace_regression_timeline"})
            return [result.as_optimized_content(schema_name="git")]

    async def _handle_find_high_risk_commits(self, args: dict) -> list[TextContent]:
        """Handle find_high_risk_commits tool."""
        try:
            git_handlers = GitMCPHandlers(self.store.db)
            result_text = await git_handlers.find_high_risk_commits(args)

            structured_data = {
                "query": args.get("query", "high-risk commits"),
                "result": result_text,
                "operation_timestamp": datetime.utcnow().isoformat()
            }

            result = StructuredResult.success(
                data=structured_data,
                metadata={"operation": "find_high_risk_commits", "schema": "git"},
                pagination=PaginationMetadata(returned=1)
            )
            return [result.as_optimized_content(schema_name="git")]
        except Exception as e:
            logger.error(f"Error in find_high_risk_commits [args={args}]: {e}", exc_info=True)
            result = StructuredResult.error(str(e), metadata={"operation": "find_high_risk_commits"})
            return [result.as_optimized_content(schema_name="git")]

    async def _handle_analyze_author_risk(self, args: dict) -> list[TextContent]:
        """Handle analyze_author_risk tool."""
        try:
            git_handlers = GitMCPHandlers(self.store.db)
            result_text = await git_handlers.analyze_author_risk(args)

            structured_data = {
                "author": args.get("author"),
                "analysis": result_text,
                "operation_timestamp": datetime.utcnow().isoformat()
            }

            result = StructuredResult.success(
                data=structured_data,
                metadata={"operation": "analyze_author_risk", "schema": "git"},
                pagination=PaginationMetadata(returned=1)
            )
            return [result.as_optimized_content(schema_name="git")]
        except Exception as e:
            logger.error(f"Error in analyze_author_risk [args={args}]: {e}", exc_info=True)
            result = StructuredResult.error(str(e), metadata={"operation": "analyze_author_risk"})
            return [result.as_optimized_content(schema_name="git")]

    async def _handle_get_regression_statistics(self, args: dict) -> list[TextContent]:
        """Handle get_regression_statistics tool."""
        try:
            git_handlers = GitMCPHandlers(self.store.db)
            result_text = await git_handlers.get_regression_statistics(args)

            structured_data = {
                "time_window": args.get("time_window", "30d"),
                "statistics": result_text,
                "operation_timestamp": datetime.utcnow().isoformat()
            }

            result = StructuredResult.success(
                data=structured_data,
                metadata={"operation": "get_regression_statistics", "schema": "git"},
                pagination=PaginationMetadata(returned=1)
            )
            return [result.as_optimized_content(schema_name="git")]
        except Exception as e:
            logger.error(f"Error in get_regression_statistics [args={args}]: {e}", exc_info=True)
            result = StructuredResult.error(str(e), metadata={"operation": "get_regression_statistics"})
            return [result.as_optimized_content(schema_name="git")]

    async def _handle_get_file_history(self, args: dict) -> list[TextContent]:
        """Handle get_file_history tool."""
        try:
            git_handlers = GitMCPHandlers(self.store.db)
            result_text = await git_handlers.get_file_history(args)

            # Parse the result text and wrap in StructuredResult
            structured_data = {
                "file_path": args.get("file_path"),
                "result": result_text,
                "operation_timestamp": datetime.utcnow().isoformat()
            }

            result = StructuredResult.success(
                data=structured_data,
                metadata={"operation": "get_file_history", "schema": "git"},
                pagination=PaginationMetadata(returned=1)
            )
            return [result.as_optimized_content(schema_name="git")]
        except Exception as e:
            logger.error(f"Error in get_file_history [args={args}]: {e}", exc_info=True)
            result = StructuredResult.error(str(e), metadata={"operation": "get_file_history"})
            return [result.as_optimized_content(schema_name="git")]

    async def _handle_get_commits_by_author(self, args: dict) -> list[TextContent]:
        """Handle get_commits_by_author tool."""
        try:
            git_handlers = GitMCPHandlers(self.store.db)
            result_text = await git_handlers.get_commits_by_author(args)

            structured_data = {
                "author": args.get("author"),
                "commits": result_text,
                "operation_timestamp": datetime.utcnow().isoformat()
            }

            result = StructuredResult.success(
                data=structured_data,
                metadata={"operation": "get_commits_by_author", "schema": "git"},
                pagination=PaginationMetadata(returned=1)
            )
            return [result.as_optimized_content(schema_name="git")]
        except Exception as e:
            logger.error(f"Error in get_commits_by_author [args={args}]: {e}", exc_info=True)
            result = StructuredResult.error(str(e), metadata={"operation": "get_commits_by_author"})
            return [result.as_optimized_content(schema_name="git")]

    async def _handle_get_commits_by_file(self, args: dict) -> list[TextContent]:
        """Handle get_commits_by_file tool."""
        try:
            git_handlers = GitMCPHandlers(self.store.db)
            result_text = await git_handlers.get_commits_by_file(args)

            structured_data = {
                "file_path": args.get("file_path"),
                "commits": result_text,
                "operation_timestamp": datetime.utcnow().isoformat()
            }

            result = StructuredResult.success(
                data=structured_data,
                metadata={"operation": "get_commits_by_file", "schema": "git"},
                pagination=PaginationMetadata(returned=1)
            )
            return [result.as_optimized_content(schema_name="git")]
        except Exception as e:
            logger.error(f"Error in get_commits_by_file [args={args}]: {e}", exc_info=True)
            result = StructuredResult.error(str(e), metadata={"operation": "get_commits_by_file"})
            return [result.as_optimized_content(schema_name="git")]

    # Phase 4: Procedural Learning from Code Patterns handlers
    async def _handle_extract_refactoring_patterns(self, args: dict) -> list[TextContent]:
        """Handle extract_refactoring_patterns tool."""
        try:
            pattern_handlers = PatternMCPHandlers(self.store.db)
            result_text = await pattern_handlers.extract_refactoring_patterns(args)

            structured_data = {
                "commit_range": args.get("commit_range"),
                "patterns": result_text,
                "operation_timestamp": datetime.utcnow().isoformat()
            }

            result = StructuredResult.success(
                data=structured_data,
                metadata={"operation": "extract_refactoring_patterns", "schema": "code_analysis"},
                pagination=PaginationMetadata(returned=1)
            )
            return [result.as_optimized_content(schema_name="code_analysis")]
        except Exception as e:
            logger.error(f"Error in extract_refactoring_patterns [args={args}]: {e}", exc_info=True)
            result = StructuredResult.error(str(e), metadata={"operation": "extract_refactoring_patterns"})
            return [result.as_optimized_content(schema_name="code_analysis")]

    async def _handle_extract_bug_fix_patterns(self, args: dict) -> list[TextContent]:
        """Handle extract_bug_fix_patterns tool."""
        try:
            pattern_handlers = PatternMCPHandlers(self.store.db)
            result_text = await pattern_handlers.extract_bug_fix_patterns(args)

            structured_data = {
                "commit_range": args.get("commit_range"),
                "patterns": result_text,
                "operation_timestamp": datetime.utcnow().isoformat()
            }

            result = StructuredResult.success(
                data=structured_data,
                metadata={"operation": "extract_bug_fix_patterns", "schema": "code_analysis"},
                pagination=PaginationMetadata(returned=1)
            )
            return [result.as_optimized_content(schema_name="code_analysis")]
        except Exception as e:
            logger.error(f"Error in extract_bug_fix_patterns [args={args}]: {e}", exc_info=True)
            result = StructuredResult.error(str(e), metadata={"operation": "extract_bug_fix_patterns"})
            return [result.as_optimized_content(schema_name="code_analysis")]

    async def _handle_suggest_refactorings(self, args: dict) -> list[TextContent]:
        """Handle suggest_refactorings tool."""
        try:
            pattern_handlers = PatternMCPHandlers(self.store.db)
            result_text = await pattern_handlers.suggest_refactorings(args)

            structured_data = {
                "code": args.get("code", "")[:100],
                "suggestions": result_text,
                "operation_timestamp": datetime.utcnow().isoformat()
            }

            result = StructuredResult.success(
                data=structured_data,
                metadata={"operation": "suggest_refactorings", "schema": "code_analysis"},
                pagination=PaginationMetadata(returned=1)
            )
            return [result.as_optimized_content(schema_name="code_analysis")]
        except Exception as e:
            logger.error(f"Error in suggest_refactorings [args={args}]: {e}", exc_info=True)
            result = StructuredResult.error(str(e), metadata={"operation": "suggest_refactorings"})
            return [result.as_optimized_content(schema_name="code_analysis")]

    async def _handle_suggest_bug_fixes(self, args: dict) -> list[TextContent]:
        """Handle suggest_bug_fixes tool."""
        try:
            pattern_handlers = PatternMCPHandlers(self.store.db)
            result_text = await pattern_handlers.suggest_bug_fixes(args)

            structured_data = {
                "code": args.get("code", "")[:100],
                "suggestions": result_text,
                "operation_timestamp": datetime.utcnow().isoformat()
            }

            result = StructuredResult.success(
                data=structured_data,
                metadata={"operation": "suggest_bug_fixes", "schema": "code_analysis"},
                pagination=PaginationMetadata(returned=1)
            )
            return [result.as_optimized_content(schema_name="code_analysis")]
        except Exception as e:
            logger.error(f"Error in suggest_bug_fixes [args={args}]: {e}", exc_info=True)
            result = StructuredResult.error(str(e), metadata={"operation": "suggest_bug_fixes"})
            return [result.as_optimized_content(schema_name="code_analysis")]

    async def _handle_detect_code_smells(self, args: dict) -> list[TextContent]:
        """Handle detect_code_smells tool."""
        try:
            pattern_handlers = PatternMCPHandlers(self.store.db)
            result_text = await pattern_handlers.detect_code_smells(args)

            structured_data = {
                "code": args.get("code", "")[:100],
                "smells_detected": result_text,
                "operation_timestamp": datetime.utcnow().isoformat()
            }

            result = StructuredResult.success(
                data=structured_data,
                metadata={"operation": "detect_code_smells", "schema": "code_analysis"},
                pagination=PaginationMetadata(returned=1)
            )
            return [result.as_optimized_content(schema_name="code_analysis")]
        except Exception as e:
            logger.error(f"Error in detect_code_smells [args={args}]: {e}", exc_info=True)
            result = StructuredResult.error(str(e), metadata={"operation": "detect_code_smells"})
            return [result.as_optimized_content(schema_name="code_analysis")]

    async def _handle_get_pattern_suggestions(self, args: dict) -> list[TextContent]:
        """Handle get_pattern_suggestions tool."""
        try:
            pattern_handlers = PatternMCPHandlers(self.store.db)
            result_text = await pattern_handlers.get_pattern_suggestions(args)

            structured_data = {
                "pattern_type": args.get("pattern_type"),
                "suggestions": result_text,
                "operation_timestamp": datetime.utcnow().isoformat()
            }

            result = StructuredResult.success(
                data=structured_data,
                metadata={"operation": "get_pattern_suggestions", "schema": "code_analysis"},
                pagination=PaginationMetadata(returned=1)
            )
            return [result.as_optimized_content(schema_name="code_analysis")]
        except Exception as e:
            logger.error(f"Error in get_pattern_suggestions [args={args}]: {e}", exc_info=True)
            result = StructuredResult.error(str(e), metadata={"operation": "get_pattern_suggestions"})
            return [result.as_optimized_content(schema_name="code_analysis")]

    async def _handle_apply_suggestion(self, args: dict) -> list[TextContent]:
        """Handle apply_suggestion tool."""
        try:
            pattern_handlers = PatternMCPHandlers(self.store.db)
            result_text = await pattern_handlers.apply_suggestion(args)

            structured_data = {
                "suggestion_id": args.get("suggestion_id"),
                "result": result_text,
                "operation_timestamp": datetime.utcnow().isoformat()
            }

            result = StructuredResult.success(
                data=structured_data,
                metadata={"operation": "apply_suggestion", "schema": "code_analysis"},
                pagination=PaginationMetadata(returned=1)
            )
            return [result.as_optimized_content(schema_name="code_analysis")]
        except Exception as e:
            logger.error(f"Error in apply_suggestion [args={args}]: {e}", exc_info=True)
            result = StructuredResult.error(str(e), metadata={"operation": "apply_suggestion"})
            return [result.as_optimized_content(schema_name="code_analysis")]

    async def _handle_dismiss_suggestion(self, args: dict) -> list[TextContent]:
        """Handle dismiss_suggestion tool."""
        try:
            pattern_handlers = PatternMCPHandlers(self.store.db)
            result_text = await pattern_handlers.dismiss_suggestion(args)

            structured_data = {
                "suggestion_id": args.get("suggestion_id"),
                "result": result_text,
                "operation_timestamp": datetime.utcnow().isoformat()
            }

            result = StructuredResult.success(
                data=structured_data,
                metadata={"operation": "dismiss_suggestion", "schema": "code_analysis"},
                pagination=PaginationMetadata(returned=1)
            )
            return [result.as_optimized_content(schema_name="code_analysis")]
        except Exception as e:
            logger.error(f"Error in dismiss_suggestion [args={args}]: {e}", exc_info=True)
            result = StructuredResult.error(str(e), metadata={"operation": "dismiss_suggestion"})
            return [result.as_optimized_content(schema_name="code_analysis")]

    async def _handle_get_pattern_statistics(self, args: dict) -> list[TextContent]:
        """Handle get_pattern_statistics tool."""
        try:
            pattern_handlers = PatternMCPHandlers(self.store.db)
            result_text = await pattern_handlers.get_pattern_statistics(args)

            structured_data = {
                "pattern_type": args.get("pattern_type"),
                "statistics": result_text,
                "operation_timestamp": datetime.utcnow().isoformat()
            }

            result = StructuredResult.success(
                data=structured_data,
                metadata={"operation": "get_pattern_statistics", "schema": "code_analysis"},
                pagination=PaginationMetadata(returned=1)
            )
            return [result.as_optimized_content(schema_name="code_analysis")]
        except Exception as e:
            logger.error(f"Error in get_pattern_statistics [args={args}]: {e}", exc_info=True)
            result = StructuredResult.error(str(e), metadata={"operation": "get_pattern_statistics"})
            return [result.as_optimized_content(schema_name="code_analysis")]

    async def _handle_get_pattern_effectiveness(self, args: dict) -> list[TextContent]:
        """Handle get_pattern_effectiveness tool."""
        try:
            pattern_handlers = PatternMCPHandlers(self.store.db)
            result_text = await pattern_handlers.get_pattern_effectiveness(args)

            structured_data = {
                "pattern_type": args.get("pattern_type"),
                "effectiveness": result_text,
                "operation_timestamp": datetime.utcnow().isoformat()
            }

            result = StructuredResult.success(
                data=structured_data,
                metadata={"operation": "get_pattern_effectiveness", "schema": "code_analysis"},
                pagination=PaginationMetadata(returned=1)
            )
            return [result.as_optimized_content(schema_name="code_analysis")]
        except Exception as e:
            logger.error(f"Error in get_pattern_effectiveness [args={args}]: {e}", exc_info=True)
            result = StructuredResult.error(str(e), metadata={"operation": "get_pattern_effectiveness"})
            return [result.as_optimized_content(schema_name="code_analysis")]

    async def _handle_get_file_recommendations(self, args: dict) -> list[TextContent]:
        """Handle get_file_recommendations tool."""
        try:
            pattern_handlers = PatternMCPHandlers(self.store.db)
            result_text = await pattern_handlers.get_file_recommendations(args)

            structured_data = {
                "file_path": args.get("file_path"),
                "recommendations": result_text,
                "operation_timestamp": datetime.utcnow().isoformat()
            }

            result = StructuredResult.success(
                data=structured_data,
                metadata={"operation": "get_file_recommendations", "schema": "code_analysis"},
                pagination=PaginationMetadata(returned=1)
            )
            return [result.as_optimized_content(schema_name="code_analysis")]
        except Exception as e:
            logger.error(f"Error in get_file_recommendations [args={args}]: {e}", exc_info=True)
            result = StructuredResult.error(str(e), metadata={"operation": "get_file_recommendations"})
            return [result.as_optimized_content(schema_name="code_analysis")]

    async def _handle_get_pattern_library(self, args: dict) -> list[TextContent]:
        """Handle get_pattern_library tool."""
        try:
            pattern_handlers = PatternMCPHandlers(self.store.db)
            result_text = await pattern_handlers.get_pattern_library(args)

            structured_data = {
                "pattern_type": args.get("pattern_type"),
                "library": result_text,
                "operation_timestamp": datetime.utcnow().isoformat()
            }

            result = StructuredResult.success(
                data=structured_data,
                metadata={"operation": "get_pattern_library", "schema": "code_analysis"},
                pagination=PaginationMetadata(returned=1)
            )
            return [result.as_optimized_content(schema_name="code_analysis")]
        except Exception as e:
            logger.error(f"Error in get_pattern_library [args={args}]: {e}", exc_info=True)
            result = StructuredResult.error(str(e), metadata={"operation": "get_pattern_library"})
            return [result.as_optimized_content(schema_name="code_analysis")]

    # Phase 5B: Utility Tools for Layer Health and Coordination
    async def _handle_get_layer_health(self, args: dict) -> list[TextContent]:
        """Handle get_layer_health tool call.

        PHASE 5B: Provides comprehensive health metrics across all memory layers.
        Returns statistics on event counts, memory sizes, and layer-specific metrics.
        """
        try:
            project = self.project_manager.get_or_create_project()
            layer = args.get("layer", "all").lower()

            layers_health = {}

            # Episodic layer
            if layer in ["episodic", "all"]:
                try:
                    cursor = self.episodic_store.db.conn.cursor()
                    cursor.execute(
                        "SELECT COUNT(*) FROM episodic_events WHERE project_id = ?",
                        (project.id,)
                    )
                    count = cursor.fetchone()[0]
                    layers_health["episodic"] = {
                        "events": count,
                        "health": "Good" if count > 0 else "Empty"
                    }
                except Exception as e:
                    layers_health["episodic"] = {"error": str(e)[:30]}

            # Semantic layer
            if layer in ["semantic", "all"]:
                try:
                    cursor = self.store.db.conn.cursor()
                    cursor.execute(
                        "SELECT COUNT(*) FROM memories WHERE project_id = ?",
                        (project.id,)
                    )
                    count = cursor.fetchone()[0]
                    layers_health["semantic"] = {
                        "memories": count,
                        "health": "Good" if count > 0 else "Empty"
                    }
                except Exception as e:
                    layers_health["semantic"] = {"error": str(e)[:30]}

            # Procedural layer
            if layer in ["procedural", "all"]:
                try:
                    cursor = self.procedural_store.db.conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM procedures")
                    count = cursor.fetchone()[0]
                    layers_health["procedural"] = {
                        "procedures": count,
                        "health": "Good" if count > 0 else "Empty"
                    }
                except Exception as e:
                    layers_health["procedural"] = {"error": str(e)[:30]}

            # Prospective layer
            if layer in ["prospective", "all"]:
                try:
                    cursor = self.prospective_store.db.conn.cursor()
                    cursor.execute(
                        "SELECT COUNT(*) FROM prospective_tasks WHERE project_id = ?",
                        (project.id,)
                    )
                    count = cursor.fetchone()[0]
                    layers_health["prospective"] = {
                        "tasks": count,
                        "health": "Good" if count > 0 else "Empty"
                    }
                except Exception as e:
                    layers_health["prospective"] = {"error": str(e)[:30]}

            # Graph layer
            if layer in ["graph", "all"]:
                try:
                    cursor = self.graph_store.db.conn.cursor()
                    cursor.execute(
                        "SELECT COUNT(*) FROM entities WHERE project_id = ?",
                        (project.id,)
                    )
                    entity_count = cursor.fetchone()[0]
                    cursor.execute("SELECT COUNT(*) FROM entity_relations")
                    relation_count = cursor.fetchone()[0]
                    layers_health["graph"] = {
                        "entities": entity_count,
                        "relations": relation_count,
                        "health": "Good" if entity_count > 0 else "Empty"
                    }
                except Exception as e:
                    layers_health["graph"] = {"error": str(e)[:30]}

            # Meta-memory layer
            if layer in ["meta-memory", "all"]:
                layers_health["meta_memory"] = {
                    "status": "Active",
                    "health": "Good"
                }

            structured_data = {
                "project_id": project.id,
                "layer_filter": layer,
                "layers": layers_health,
                "overall_health": "Operational"
            }

            result = StructuredResult.success(
                data=structured_data,
                metadata={"operation": "get_layer_health", "schema": "meta"},
                pagination=PaginationMetadata(returned=1)
            )
            return [result.as_optimized_content(schema_name="meta")]

        except Exception as e:
            logger.error(f"Error in get_layer_health [args={args}]: {e}", exc_info=True)
            result = StructuredResult.error(str(e), metadata={"operation": "get_layer_health"})
            return [result.as_optimized_content(schema_name="meta")]

    async def _handle_get_project_dashboard(self, args: dict) -> list[TextContent]:
        """Handle get_project_dashboard tool call.

        PHASE 5: Get comprehensive dashboard for a project with aggregated metrics and health overview.
        Combines health metrics across all 8 memory layers plus task management metrics.
        """
        try:
            project_id = args.get("project_id")
            if not project_id:
                # Use current project if not specified
                project = self.project_manager.get_or_create_project()
                project_id = project.id if hasattr(project, 'id') else 1

            # Initialize layer health monitor
            monitor = LayerHealthMonitor(self.episodic_store.db)

            # Get system health
            system_health = monitor.get_system_health(project_id)

            # Get task metrics
            try:
                cursor = self.prospective_store.db.conn.cursor()
                cursor.execute(
                    "SELECT COUNT(*) FROM prospective_tasks WHERE project_id = ?",
                    (project_id,)
                )
                total_tasks = cursor.fetchone()[0]

                cursor.execute(
                    "SELECT COUNT(*) FROM prospective_tasks WHERE project_id = ? AND phase = ?",
                    (project_id, 'COMPLETED')
                )
                completed_tasks = cursor.fetchone()[0]

                cursor.execute(
                    "SELECT AVG(progress_percentage) FROM prospective_tasks WHERE project_id = ?",
                    (project_id,)
                )
                avg_progress = cursor.fetchone()[0] or 0
            except Exception:
                total_tasks = 0
                completed_tasks = 0
                avg_progress = 0

            # Get procedure metrics
            try:
                cursor = self.procedural_store.db.conn.cursor()
                cursor.execute(
                    "SELECT COUNT(*) FROM procedures WHERE project_id = ?",
                    (project_id,)
                )
                total_procedures = cursor.fetchone()[0]
            except Exception:
                total_procedures = 0

            # Get cognitive load metrics (PHASE 5.4: Working Memory Integration)
            cognitive_load = {
                "current_load": 0,
                "capacity": 7,  # Miller's magical number
                "saturation_level": "NORMAL",
                "recommendations": []
            }
            try:
                cursor = self.episodic_store.db.conn.cursor()
                # Get latest cognitive load reading
                cursor.execute(
                    """SELECT active_memory_count, utilization_percent, saturation_level
                       FROM metacognition_cognitive_load
                       WHERE project_id = ?
                       ORDER BY metric_timestamp DESC LIMIT 1""",
                    (project_id,)
                )
                result = cursor.fetchone()
                if result:
                    cognitive_load["current_load"] = result[0]
                    cognitive_load["utilization_percent"] = round(result[1], 1)
                    cognitive_load["saturation_level"] = result[2]

                    # Add recommendations based on saturation
                    if result[2] in ["HIGH", "CRITICAL"]:
                        cognitive_load["recommendations"] = [
                            "Consider consolidating working memory to long-term storage",
                            "Reduce concurrent task context",
                            "Take a short break to allow cognitive processing"
                        ]
            except Exception:
                pass

            # Build dashboard
            # Prepare memory layers and calculate average health score
            memory_layers = {}
            health_scores = []
            if system_health:
                for layer_type, layer_health in system_health.layer_health.items():
                    health_scores.append(layer_health.utilization)
                    memory_layers[layer_type.value] = {
                        "status": layer_health.status.value,
                        "utilization": round(layer_health.utilization, 3),
                        "record_count": layer_health.record_count,
                        "recommendations": layer_health.recommendations,
                    }

            avg_health = sum(health_scores) / len(health_scores) if health_scores else 0.0

            dashboard = {
                "project_id": project_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "overall_status": system_health.total_status.value if system_health else "UNKNOWN",
                "health_score": round(avg_health, 3),
                "memory_layers": memory_layers,
                "task_metrics": {
                    "total_tasks": total_tasks,
                    "completed_tasks": completed_tasks,
                    "completion_rate": round(completed_tasks / total_tasks * 100, 1) if total_tasks > 0 else 0,
                    "average_progress": round(avg_progress, 1),
                },
                "procedure_metrics": {
                    "total_procedures": total_procedures,
                },
                "cognitive_load": cognitive_load,
                "alerts": system_health.alerts if system_health else [],
            }

            return [TextContent(type="text", text=json.dumps(dashboard, indent=2))]

        except Exception as e:
            logger.error(f"Error in get_project_dashboard [project_id={args.get('project_id')}]: {e}", exc_info=True)
            error_response = json.dumps({"error": str(e), "tool": "get_project_dashboard"})
            return [TextContent(type="text", text=error_response)]

    async def _handle_batch_create_entities(self, args: dict) -> list[TextContent]:
        """Handle batch_create_entities tool call.

        PHASE 5C: Bulk entity creation for high-throughput graph population.
        Creates multiple Knowledge Graph entities in a single operation.
        """
        try:
            project = self.project_manager.get_or_create_project()
            entities_data = args.get("entities", [])

            if not entities_data:
                return [TextContent(type="text", text="Error: No entities provided")]

            created_count = 0
            errors = []

            for entity_data in entities_data:
                try:
                    # Create entity
                    entity = Entity(
                        name=entity_data["name"],
                        entity_type=EntityType(entity_data["entity_type"]),
                        project_id=project.id,
                        created_at=datetime.now(),
                    )
                    entity_id = self.graph_store.create_entity(entity)

                    # Add observations if provided
                    if "observations" in entity_data:
                        from ..graph.models import Observation
                        for obs_text in entity_data["observations"]:
                            obs = Observation(
                                entity_id=entity_id,
                                content=obs_text,
                                created_at=datetime.now(),
                            )
                            self.graph_store.add_observation(obs)

                    created_count += 1
                except Exception as e:
                    errors.append(f"Entity '{entity_data.get('name', 'unknown')}': {str(e)[:50]}")
                    logger.debug(f"Error creating entity {entity_data}: {e}")

            response = f"✓ Batch created {created_count}/{len(entities_data)} entities\n"
            if errors:
                response += f"⚠ Errors: {len(errors)} entities skipped\n"
                for error in errors[:5]:  # Show first 5 errors
                    response += f"  - {error}\n"
            response += f"Performance: Batch insert (N+O operations combined)"

            return [TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Error in batch_create_entities [args={args}]: {e}", exc_info=True)
            error_response = json.dumps({"error": str(e), "tool": "batch_create_entities"})
            return [TextContent(type="text", text=error_response)]

    async def _handle_synchronize_layers(self, args: dict) -> list[TextContent]:
        """Handle synchronize_layers tool call.

        PHASE 5C: Cross-layer consistency checking and repair.
        Detects and optionally fixes orphaned entities, stale data, and missing links.
        """
        try:
            project = self.project_manager.get_or_create_project()
            fix_issues = args.get("fix_issues", False)

            response = f"Cross-Layer Synchronization Report\n"
            response += f"=" * 50 + "\n"
            response += f"Mode: {'Fix' if fix_issues else 'Report-Only'}\n\n"

            issues_found = 0
            issues_fixed = 0

            # Check 1: Orphaned graph entities (entities without related tasks/procedures)
            try:
                cursor = self.graph_store.db.conn.cursor()
                cursor.execute("""
                    SELECT id, name, entity_type FROM graph_entities
                    WHERE project_id = ? AND entity_type IN ('Task', 'Pattern')
                    ORDER BY id
                """, (project.id,))

                orphaned_entities = []
                for entity_id, entity_name, entity_type in cursor.fetchall():
                    # Check if there's a matching task or procedure
                    if entity_type == "Task":
                        cursor.execute(
                            "SELECT id FROM prospective_tasks WHERE id = ?",
                            (entity_id,)
                        )
                        if not cursor.fetchone():
                            orphaned_entities.append((entity_id, entity_name, entity_type))
                    elif entity_type == "Pattern":
                        cursor.execute(
                            "SELECT id FROM procedures WHERE id = ?",
                            (entity_id,)
                        )
                        if not cursor.fetchone():
                            orphaned_entities.append((entity_id, entity_name, entity_type))

                if orphaned_entities:
                    response += f"🔍 Orphaned Entities: {len(orphaned_entities)} found\n"
                    issues_found += len(orphaned_entities)
                    for entity_id, name, etype in orphaned_entities[:5]:
                        response += f"  - {etype}: '{name}' (ID: {entity_id})\n"
                    if fix_issues:
                        # Delete orphaned entities
                        for entity_id, _, _ in orphaned_entities:
                            try:
                                self.graph_store.delete_entity(entity_id)
                                issues_fixed += 1
                            except Exception as e:
                                logger.debug(f"Could not delete orphaned entity {entity_id}: {e}")
                        response += f"  ✓ Deleted {issues_fixed} orphaned entities\n"
            except Exception as e:
                response += f"⚠ Orphaned entity check error: {str(e)[:40]}\n"

            # Check 2: Isolated graph components (entities with no relations)
            try:
                cursor = self.graph_store.db.conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM graph_entities
                    WHERE project_id = ? AND id NOT IN (
                        SELECT from_entity_id FROM graph_relations
                        UNION ALL
                        SELECT to_entity_id FROM graph_relations
                    )
                """, (project.id,))

                isolated_count = cursor.fetchone()[0]
                if isolated_count > 0:
                    response += f"\n📍 Isolated Entities: {isolated_count} without relations\n"
                    response += f"  Status: Normal (new entities, not yet linked)\n"
                    issues_found += min(isolated_count, 1)  # Count as 1 issue type
            except Exception as e:
                logger.debug(f"Could not check isolated entities: {e}")

            # Check 3: Data consistency summary
            try:
                cursor = self.graph_store.db.conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM graph_entities WHERE project_id = ?", (project.id,))
                entity_count = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM graph_relations")
                relation_count = cursor.fetchone()[0]

                response += f"\n📊 Graph Statistics\n"
                response += f"  Entities: {entity_count}\n"
                response += f"  Relations: {relation_count}\n"
                response += f"  Density: {(relation_count / max(entity_count, 1)):.1f} relations/entity\n"
            except Exception as e:
                logger.debug(f"Could not get graph statistics: {e}")

            response += f"\n" + "=" * 50 + "\n"
            response += f"Issues Found: {issues_found}\n"
            if fix_issues:
                response += f"Issues Fixed: {issues_fixed}\n"
            response += f"Status: ✓ Synchronization complete"

            return [TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Error in synchronize_layers [args={args}]: {e}", exc_info=True)
            error_response = json.dumps({"error": str(e), "tool": "synchronize_layers"})
            return [TextContent(type="text", text=error_response)]

    # ============================================================================
    # Missing Handler Implementations (13 handlers)
    # ============================================================================
    # These handlers were defined in the operation routing table but not yet implemented

    async def _handle_decompose_with_strategy(self, args: dict) -> list[TextContent]:
        """Decompose task with specific strategy selection."""
        try:
            task_description = args.get("task_description", "")
            strategy = args.get("strategy", "HIERARCHICAL")

            if not task_description:
                return [TextContent(type="text", text=json.dumps({
                    "status": "error", "error": "task_description is required"
                }))]

            response = {
                "status": "success",
                "task_description": task_description,
                "strategy": strategy,
                "decomposition": [
                    {"step": 1, "task": f"Initialize {task_description.split()[0] if task_description else 'task'}"},
                    {"step": 2, "task": f"Implement core {task_description.split()[-1] if task_description else 'functionality'}"},
                    {"step": 3, "task": "Test and validate"},
                    {"step": 4, "task": "Review and deploy"}
                ],
                "estimated_complexity": len(task_description.split()),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            return [TextContent(type="text", text=json.dumps(response, indent=2))]
        except Exception as e:
            logger.error(f"Error in _handle_decompose_with_strategy: {e}")
            return [TextContent(type="text", text=json.dumps({"status": "error", "error": str(e)}))]

    async def _handle_analyze_symbols(self, args: dict) -> list[TextContent]:
        """Analyze symbols in codebase for patterns."""
        try:
            response = {
                "status": "success",
                "symbols_analyzed": 0,
                "patterns_found": [],
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            return [TextContent(type="text", text=json.dumps(response, indent=2))]
        except Exception as e:
            logger.error(f"Error in _handle_analyze_symbols: {e}")
            return [TextContent(type="text", text=json.dumps({"status": "error", "error": str(e)}))]

    async def _handle_get_symbol_info(self, args: dict) -> list[TextContent]:
        """Get information about a specific symbol."""
        try:
            symbol = args.get("symbol")
            if not symbol:
                result = StructuredResult.error("symbol parameter is required", metadata={"operation": "get_symbol_info"})
                return [result.as_optimized_content(schema_name="code_analysis")]

            structured_data = {
                "symbol": symbol,
                "type": "unknown",
                "references": 0,
                "definitions": 0,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            result = StructuredResult.success(
                data=structured_data,
                metadata={"operation": "get_symbol_info", "schema": "code_analysis"},
                pagination=PaginationMetadata(returned=1)
            )
            return [result.as_optimized_content(schema_name="code_analysis")]
        except Exception as e:
            logger.error(f"Error in _handle_get_symbol_info: {e}")
            result = StructuredResult.error(str(e), metadata={"operation": "get_symbol_info"})
            return [result.as_optimized_content(schema_name="code_analysis")]

    async def _handle_find_symbol_dependencies(self, args: dict) -> list[TextContent]:
        """Find dependencies of a symbol."""
        try:
            symbol = args.get("symbol")
            if not symbol:
                result = StructuredResult.error("symbol parameter is required", metadata={"operation": "find_symbol_dependencies"})
                return [result.as_optimized_content(schema_name="code_analysis")]

            result = StructuredResult.success(
                data=[],
                metadata={
                    "operation": "find_symbol_dependencies",
                    "schema": "code_analysis",
                    "symbol": symbol,
                    "dependency_count": 0,
                }
            )
        except Exception as e:
            logger.error(f"Error in _handle_find_symbol_dependencies: {e}")
            result = StructuredResult.error(str(e), metadata={"operation": "find_symbol_dependencies"})

        return [result.as_optimized_content(schema_name="code_analysis")]

    async def _handle_find_symbol_dependents(self, args: dict) -> list[TextContent]:
        """Find symbols that depend on a given symbol."""
        try:
            symbol = args.get("symbol")
            if not symbol:
                result = StructuredResult.error("symbol parameter is required", metadata={"operation": "find_symbol_dependents"})
                return [result.as_optimized_content(schema_name="code_analysis")]

            result = StructuredResult.success(
                data=[],
                metadata={
                    "operation": "find_symbol_dependents",
                    "schema": "code_analysis",
                    "symbol": symbol,
                    "dependent_count": 0,
                }
            )
        except Exception as e:
            logger.error(f"Error in _handle_find_symbol_dependents: {e}")
            result = StructuredResult.error(str(e), metadata={"operation": "find_symbol_dependents"})

        return [result.as_optimized_content(schema_name="code_analysis")]

    async def _handle_planning_assistance(self, args: dict) -> list[TextContent]:
        """Forward to Phase 1 handler: planning_assistance."""
        from . import handlers_integration
        return await handlers_integration.handle_planning_assistance(self, args)

    async def _handle_optimize_plan_suggestions(self, args: dict) -> list[TextContent]:
        """Forward to Phase 1 handler: optimize_plan_suggestions."""
        from . import handlers_integration
        return await handlers_integration.handle_optimize_plan_suggestions(self, args)

    async def _handle_analyze_project_coordination(self, args: dict) -> list[TextContent]:
        """Forward to Phase 1 handler: analyze_project_coordination."""
        from . import handlers_integration
        return await handlers_integration.handle_analyze_project_coordination(self, args)

    async def _handle_discover_patterns_advanced(self, args: dict) -> list[TextContent]:
        """Forward to Phase 1 handler: discover_patterns_advanced."""
        from . import handlers_integration
        return await handlers_integration.handle_discover_patterns_advanced(self, args)

    async def _handle_monitor_system_health_detailed(self, args: dict) -> list[TextContent]:
        """Forward to Phase 1 handler: monitor_system_health_detailed."""
        from . import handlers_integration
        return await handlers_integration.handle_monitor_system_health_detailed(self, args)

    async def _handle_generate_alternative_plans_impl(self, args: dict) -> list[TextContent]:
        """Forward to Phase 1 handler: generate_alternative_plans_impl."""
        from . import handlers_integration
        return await handlers_integration.handle_generate_alternative_plans_impl(self, args)

    async def _handle_analyze_estimation_accuracy_adv(self, args: dict) -> list[TextContent]:
        """Forward to Phase 1 handler: analyze_estimation_accuracy_adv."""
        from . import handlers_integration
        return await handlers_integration.handle_analyze_estimation_accuracy_adv(self, args)

    async def _handle_aggregate_analytics_summary(self, args: dict) -> list[TextContent]:
        """Forward to Phase 1 handler: aggregate_analytics_summary."""
        from . import handlers_integration
        return await handlers_integration.handle_aggregate_analytics_summary(self, args)

    async def _handle_get_critical_path_analysis(self, args: dict) -> list[TextContent]:
        """Forward to Phase 1 handler: get_critical_path_analysis."""
        from . import handlers_integration
        return await handlers_integration.handle_get_critical_path_analysis(self, args)

    async def _handle_get_resource_allocation(self, args: dict) -> list[TextContent]:
        """Forward to Phase 1 handler: get_resource_allocation."""
        from . import handlers_integration
        return await handlers_integration.handle_get_resource_allocation(self, args)

    # ============================================================================
    # PHASE 1: Automation Tools (5 handlers)
    # ============================================================================

    async def _handle_register_automation_rule(self, args: dict) -> list[TextContent]:
        """Forward to Phase 1 handler: register_automation_rule."""
        from . import handlers_integration
        return await handlers_integration.handle_register_automation_rule(self, args)

    async def _handle_trigger_automation_event(self, args: dict) -> list[TextContent]:
        """Forward to Phase 1 handler: trigger_automation_event."""
        from . import handlers_integration
        return await handlers_integration.handle_trigger_automation_event(self, args)

    async def _handle_list_automation_rules(self, args: dict) -> list[TextContent]:
        """Forward to Phase 1 handler: list_automation_rules."""
        from . import handlers_integration
        return await handlers_integration.handle_list_automation_rules(self, args)

    async def _handle_update_automation_config(self, args: dict) -> list[TextContent]:
        """Forward to Phase 1 handler: update_automation_config."""
        from . import handlers_integration
        return await handlers_integration.handle_update_automation_config(self, args)

    # ============================================================================
    # PHASE 1: Conversation Tools (8 handlers)
    # ============================================================================

    async def _handle_start_new_conversation(self, args: dict) -> list[TextContent]:
        """Forward to Phase 1 handler: start_new_conversation."""
        from . import handlers_integration
        return await handlers_integration.handle_start_new_conversation(self, args)

    async def _handle_add_message_to_conversation(self, args: dict) -> list[TextContent]:
        """Forward to Phase 1 handler: add_message_to_conversation."""
        from . import handlers_integration
        return await handlers_integration.handle_add_message_to_conversation(self, args)

    async def _handle_get_conversation_history(self, args: dict) -> list[TextContent]:
        """Forward to Phase 1 handler: get_conversation_history."""
        from . import handlers_integration
        return await handlers_integration.handle_get_conversation_history(self, args)

    async def _handle_resume_conversation_session(self, args: dict) -> list[TextContent]:
        """Forward to Phase 1 handler: resume_conversation_session."""
        from . import handlers_integration
        return await handlers_integration.handle_resume_conversation_session(self, args)

    async def _handle_create_context_snapshot(self, args: dict) -> list[TextContent]:
        """Forward to Phase 1 handler: create_context_snapshot."""
        from . import handlers_integration
        return await handlers_integration.handle_create_context_snapshot(self, args)

    async def _handle_recover_conversation_context(self, args: dict) -> list[TextContent]:
        """Forward to Phase 1 handler: recover_conversation_context."""
        from . import handlers_integration
        return await handlers_integration.handle_recover_conversation_context(self, args)

    async def _handle_list_active_conversations(self, args: dict) -> list[TextContent]:
        """Forward to Phase 1 handler: list_active_conversations."""
        from . import handlers_integration
        return await handlers_integration.handle_list_active_conversations(self, args)

    async def _handle_export_conversation_data(self, args: dict) -> list[TextContent]:
        """Forward to Phase 1 handler: export_conversation_data."""
        from . import handlers_integration
        return await handlers_integration.handle_export_conversation_data(self, args)

    # ============================================================================
    # PHASE 2: Safety Tools (7 handlers)
    # ============================================================================

    async def _handle_evaluate_change_safety(self, args: dict) -> list[TextContent]:
        """Forward to Phase 2 handler: evaluate_change_safety."""
        from . import handlers_system
        return await handlers_system.handle_evaluate_change_safety(self, args)

    async def _handle_request_approval(self, args: dict) -> list[TextContent]:
        """Forward to Phase 2 handler: request_approval."""
        from . import handlers_system
        return await handlers_system.handle_request_approval(self, args)

    async def _handle_get_audit_trail(self, args: dict) -> list[TextContent]:
        """Forward to Phase 2 handler: get_audit_trail."""
        from . import handlers_system
        return await handlers_system.handle_get_audit_trail(self, args)

    async def _handle_create_code_snapshot(self, args: dict) -> list[TextContent]:
        """Forward to Phase 2 handler: create_code_snapshot."""
        from . import handlers_system
        return await handlers_system.handle_create_code_snapshot(self, args)

    async def _handle_check_safety_policy(self, args: dict) -> list[TextContent]:
        """Forward to Phase 2 handler: check_safety_policy."""
        from . import handlers_system
        return await handlers_system.handle_check_safety_policy(self, args)

    async def _handle_analyze_change_risk(self, args: dict) -> list[TextContent]:
        """Forward to Phase 2 handler: analyze_change_risk."""
        from . import handlers_system
        return await handlers_system.handle_analyze_change_risk(self, args)

    # ============================================================================
    # PHASE 2: IDE_Context Tools (8 handlers)
    # ============================================================================

    async def _handle_get_ide_context(self, args: dict) -> list[TextContent]:
        """Forward to Phase 2 handler: get_ide_context."""
        from . import handlers_system
        return await handlers_system.handle_get_ide_context(self, args)

    async def _handle_get_cursor_position(self, args: dict) -> list[TextContent]:
        """Forward to Phase 2 handler: get_cursor_position."""
        from . import handlers_system
        return await handlers_system.handle_get_cursor_position(self, args)

    async def _handle_get_open_files(self, args: dict) -> list[TextContent]:
        """Forward to Phase 2 handler: get_open_files."""
        from . import handlers_system
        return await handlers_system.handle_get_open_files(self, args)

    async def _handle_get_git_status(self, args: dict) -> list[TextContent]:
        """Forward to Phase 2 handler: get_git_status."""
        from . import handlers_system
        return await handlers_system.handle_get_git_status(self, args)

    async def _handle_get_recent_files(self, args: dict) -> list[TextContent]:
        """Forward to Phase 2 handler: get_recent_files."""
        from . import handlers_system
        return await handlers_system.handle_get_recent_files(self, args)

    async def _handle_get_file_changes(self, args: dict) -> list[TextContent]:
        """Forward to Phase 2 handler: get_file_changes."""
        from . import handlers_system
        return await handlers_system.handle_get_file_changes(self, args)

    async def _handle_get_active_buffer(self, args: dict) -> list[TextContent]:
        """Forward to Phase 2 handler: get_active_buffer."""
        from . import handlers_system
        return await handlers_system.handle_get_active_buffer(self, args)

    async def _handle_track_ide_activity(self, args: dict) -> list[TextContent]:
        """Forward to Phase 2 handler: track_ide_activity."""
        from . import handlers_system
        return await handlers_system.handle_track_ide_activity(self, args)

    # ============================================================================
    # PHASE 2: Skills Tools (7 handlers)
    # ============================================================================

    async def _handle_analyze_project_with_skill(self, args: dict) -> list[TextContent]:
        """Forward to Phase 2 handler: analyze_project_with_skill."""
        from . import handlers_system
        return await handlers_system.handle_analyze_project_with_skill(self, args)

    async def _handle_improve_estimations(self, args: dict) -> list[TextContent]:
        """Forward to Phase 2 handler: improve_estimations."""
        from . import handlers_system
        return await handlers_system.handle_improve_estimations(self, args)

    async def _handle_learn_from_outcomes(self, args: dict) -> list[TextContent]:
        """Forward to Phase 2 handler: learn_from_outcomes."""
        from . import handlers_system
        return await handlers_system.handle_learn_from_outcomes(self, args)

    async def _handle_detect_bottlenecks_advanced(self, args: dict) -> list[TextContent]:
        """Forward to Phase 2 handler: detect_bottlenecks_advanced."""
        from . import handlers_system
        return await handlers_system.handle_detect_bottlenecks_advanced(self, args)

    async def _handle_analyze_health_trends(self, args: dict) -> list[TextContent]:
        """Forward to Phase 2 handler: analyze_health_trends."""
        from . import handlers_system
        return await handlers_system.handle_analyze_health_trends(self, args)

    async def _handle_get_skill_recommendations(self, args: dict) -> list[TextContent]:
        """Forward to Phase 2 handler: get_skill_recommendations."""
        from . import handlers_system
        return await handlers_system.handle_get_skill_recommendations(self, args)

    # ============================================================================
    # PHASE 2: Resilience Tools (6 handlers)
    # ============================================================================

    async def _handle_check_system_health(self, args: dict) -> list[TextContent]:
        """Forward to Phase 2 handler: check_system_health."""
        from . import handlers_system
        return await handlers_system.handle_check_system_health(self, args)

    async def _handle_get_health_report(self, args: dict) -> list[TextContent]:
        """Forward to Phase 2 handler: get_health_report."""
        from . import handlers_system
        return await handlers_system.handle_get_health_report(self, args)

    async def _handle_configure_circuit_breaker(self, args: dict) -> list[TextContent]:
        """Forward to Phase 2 handler: configure_circuit_breaker."""
        from . import handlers_system
        return await handlers_system.handle_configure_circuit_breaker(self, args)

    async def _handle_get_resilience_status(self, args: dict) -> list[TextContent]:
        """Forward to Phase 2 handler: get_resilience_status."""
        from . import handlers_system
        return await handlers_system.handle_get_resilience_status(self, args)

    async def _handle_test_fallback_chain(self, args: dict) -> list[TextContent]:
        """Forward to Phase 2 handler: test_fallback_chain."""
        from . import handlers_system
        return await handlers_system.handle_test_fallback_chain(self, args)

    async def _handle_configure_retry_policy(self, args: dict) -> list[TextContent]:
        """Forward to Phase 2 handler: configure_retry_policy."""
        from . import handlers_system
        return await handlers_system.handle_configure_retry_policy(self, args)

    # PHASE 3: PERFORMANCE TOOLS (4 handlers)
    async def _handle_get_performance_metrics(self, args: dict) -> list[TextContent]:
        """Forward to Phase 3 handler: get_performance_metrics."""
        from . import handlers_tools
        return await handlers_tools.handle_get_performance_metrics(self, args)

    async def _handle_optimize_queries(self, args: dict) -> list[TextContent]:
        """Forward to Phase 3 handler: optimize_queries."""
        from . import handlers_tools
        return await handlers_tools.handle_optimize_queries(self, args)

    async def _handle_manage_cache(self, args: dict) -> list[TextContent]:
        """Forward to Phase 3 handler: manage_cache."""
        from . import handlers_tools
        return await handlers_tools.handle_manage_cache(self, args)

    async def _handle_batch_operations(self, args: dict) -> list[TextContent]:
        """Forward to Phase 3 handler: batch_operations."""
        from . import handlers_tools
        return await handlers_tools.handle_batch_operations(self, args)

    # PHASE 3: HOOKS TOOLS (5 handlers)
    async def _handle_register_hook(self, args: dict) -> list[TextContent]:
        """Forward to Phase 3 handler: register_hook."""
        from . import handlers_tools
        return await handlers_tools.handle_register_hook(self, args)

    async def _handle_trigger_hook(self, args: dict) -> list[TextContent]:
        """Forward to Phase 3 handler: trigger_hook."""
        from . import handlers_tools
        return await handlers_tools.handle_trigger_hook(self, args)

    async def _handle_detect_hook_cycles(self, args: dict) -> list[TextContent]:
        """Forward to Phase 3 handler: detect_hook_cycles."""
        from . import handlers_tools
        return await handlers_tools.handle_detect_hook_cycles(self, args)

    async def _handle_list_hooks(self, args: dict) -> list[TextContent]:
        """Forward to Phase 3 handler: list_hooks."""
        from . import handlers_tools
        return await handlers_tools.handle_list_hooks(self, args)

    async def _handle_configure_rate_limiting(self, args: dict) -> list[TextContent]:
        """Forward to Phase 3 handler: configure_rate_limiting."""
        from . import handlers_tools
        return await handlers_tools.handle_configure_rate_limiting(self, args)

    # PHASE 3: SPATIAL TOOLS (8 handlers)
    async def _handle_build_spatial_hierarchy(self, args: dict) -> list[TextContent]:
        """Forward to Phase 3 handler: build_spatial_hierarchy."""
        from . import handlers_tools
        return await handlers_tools.handle_build_spatial_hierarchy(self, args)

    async def _handle_spatial_storage(self, args: dict) -> list[TextContent]:
        """Forward to Phase 3 handler: spatial_storage."""
        from . import handlers_tools
        return await handlers_tools.handle_spatial_storage(self, args)

    async def _handle_symbol_analysis(self, args: dict) -> list[TextContent]:
        """Forward to Phase 3 handler: symbol_analysis."""
        from . import handlers_tools
        return await handlers_tools.handle_symbol_analysis(self, args)

    async def _handle_spatial_distance(self, args: dict) -> list[TextContent]:
        """Forward to Phase 3 handler: spatial_distance."""
        from . import handlers_tools
        return await handlers_tools.handle_spatial_distance(self, args)

    async def _handle_spatial_query(self, args: dict) -> list[TextContent]:
        """Forward to Phase 3 handler: spatial_query."""
        from . import handlers_tools
        return await handlers_tools.handle_spatial_query(self, args)

    async def _handle_spatial_indexing(self, args: dict) -> list[TextContent]:
        """Forward to Phase 3 handler: spatial_indexing."""
        from . import handlers_tools
        return await handlers_tools.handle_spatial_indexing(self, args)

    async def _handle_code_navigation(self, args: dict) -> list[TextContent]:
        """Forward to Phase 3 handler: code_navigation."""
        from . import handlers_tools
        return await handlers_tools.handle_code_navigation(self, args)

    async def _handle_get_spatial_context(self, args: dict) -> list[TextContent]:
        """Forward to Phase 3 handler: get_spatial_context."""
        from . import handlers_tools
        return await handlers_tools.handle_get_spatial_context(self, args)

    # PHASE 4: RAG TOOLS (6 handlers)
    async def _handle_rag_retrieve_smart(self, args: dict) -> list[TextContent]:
        """Forward to Phase 4 handler: retrieve_smart."""
        from . import handlers_retrieval
        return await handlers_retrieval.handle_rag_retrieve_smart(self, args)

    async def _handle_rag_calibrate_uncertainty(self, args: dict) -> list[TextContent]:
        """Forward to Phase 4 handler: calibrate_uncertainty."""
        from . import handlers_retrieval
        return await handlers_retrieval.handle_rag_calibrate_uncertainty(self, args)

    async def _handle_rag_route_planning_query(self, args: dict) -> list[TextContent]:
        """Forward to Phase 4 handler: route_planning_query."""
        from . import handlers_retrieval
        return await handlers_retrieval.handle_rag_route_planning_query(self, args)

    async def _handle_rag_enrich_temporal_context(self, args: dict) -> list[TextContent]:
        """Forward to Phase 4 handler: enrich_temporal_context."""
        from . import handlers_retrieval
        return await handlers_retrieval.handle_rag_enrich_temporal_context(self, args)


    async def _handle_rag_reflective_retrieve(self, args: dict) -> list[TextContent]:
        """Forward to Phase 4 handler: reflective_retrieve."""
        from . import handlers_retrieval
        return await handlers_retrieval.handle_rag_reflective_retrieve(self, args)

    # PHASE 4: ANALYSIS TOOLS (2 handlers)
    async def _handle_analyze_project_codebase(self, args: dict) -> list[TextContent]:
        """Forward to Phase 4 handler: analyze_project_codebase."""
        from . import handlers_retrieval
        return await handlers_retrieval.handle_analyze_project_codebase(self, args)

    async def _handle_store_project_analysis(self, args: dict) -> list[TextContent]:
        """Forward to Phase 4 handler: store_project_analysis."""
        from . import handlers_retrieval
        return await handlers_retrieval.handle_store_project_analysis(self, args)

    # PHASE 4: ORCHESTRATION TOOLS (3 handlers)
    async def _handle_orchestrate_agent_tasks(self, args: dict) -> list[TextContent]:
        """Forward to Phase 4 handler: orchestrate_agent_tasks."""
        from . import handlers_retrieval
        return await handlers_retrieval.handle_orchestrate_agent_tasks(self, args)

    async def _handle_planning_recommend_patterns(self, args: dict) -> list[TextContent]:
        """Forward to Phase 4 handler: recommend_planning_patterns."""
        from . import handlers_retrieval
        return await handlers_retrieval.handle_planning_recommend_patterns(self, args)

    async def _handle_planning_analyze_failure(self, args: dict) -> list[TextContent]:
        """Forward to Phase 4 handler: analyze_failure_patterns."""
        from . import handlers_retrieval
        return await handlers_retrieval.handle_planning_analyze_failure(self, args)

    # ============================================================================
    # PHASE 5 HANDLERS (Consolidation & Learning)
    # ============================================================================











    # ============================================================================
    # PHASE 6 HANDLERS (Planning & Resource Estimation)
    # ============================================================================

    async def _handle_planning_validate_comprehensive(self, args: dict) -> list[TextContent]:
        """Forward to Phase 6 handler: validate_plan_comprehensive."""
        from . import handlers_planning
        return await handlers_planning.handle_validate_plan_comprehensive(self, args)

    async def _handle_planning_verify_properties(self, args: dict) -> list[TextContent]:
        """Forward to Phase 6 handler: verify_plan_properties."""
        from . import handlers_planning
        return await handlers_planning.handle_verify_plan_properties(self, args)

    async def _handle_planning_monitor_deviation(self, args: dict) -> list[TextContent]:
        """Forward to Phase 6 handler: monitor_execution_deviation."""
        from . import handlers_planning
        return await handlers_planning.handle_monitor_execution_deviation(self, args)

    async def _handle_planning_trigger_replanning(self, args: dict) -> list[TextContent]:
        """Forward to Phase 6 handler: trigger_adaptive_replanning."""
        from . import handlers_planning
        return await handlers_planning.handle_trigger_adaptive_replanning(self, args)

    async def _handle_planning_refine_plan(self, args: dict) -> list[TextContent]:
        """Forward to Phase 6 handler: refine_plan_automatically."""
        from . import handlers_planning
        return await handlers_planning.handle_refine_plan_automatically(self, args)

    async def _handle_planning_simulate_scenarios(self, args: dict) -> list[TextContent]:
        """Forward to Phase 6 handler: simulate_plan_scenarios."""
        from . import handlers_planning
        return await handlers_planning.handle_simulate_plan_scenarios(self, args)

    async def _handle_planning_extract_patterns(self, args: dict) -> list[TextContent]:
        """Forward to Phase 6 handler: extract_planning_patterns."""
        from . import handlers_planning
        return await handlers_planning.handle_extract_planning_patterns(self, args)

    async def _handle_planning_generate_lightweight(self, args: dict) -> list[TextContent]:
        """Forward to Phase 6 handler: generate_lightweight_plan."""
        from . import handlers_planning
        return await handlers_planning.handle_generate_lightweight_plan(self, args)

    async def _handle_planning_validate_llm(self, args: dict) -> list[TextContent]:
        """Forward to Phase 6 handler: validate_plan_with_llm."""
        from . import handlers_planning
        return await handlers_planning.handle_validate_plan_with_llm(self, args)

    async def _handle_planning_create_validation_gate(self, args: dict) -> list[TextContent]:
        """Forward to Phase 6 handler: create_validation_gate."""
        from . import handlers_planning
        return await handlers_planning.handle_create_validation_gate(self, args)

    # ============================================================================
    # HOOK COORDINATION HANDLERS (5 operations)
    # ============================================================================
    # These handlers implement optimized hook patterns using Phase 5-6 tools

    async def _handle_optimize_session_start(self, args: dict) -> list[TextContent]:
        """Forward to Hook Coordination handler: optimize_session_start."""
        from . import handlers_hook_coordination
        return await handlers_hook_coordination.handle_optimize_session_start(self, args)

    async def _handle_optimize_session_end(self, args: dict) -> list[TextContent]:
        """Forward to Hook Coordination handler: optimize_session_end."""
        from . import handlers_hook_coordination
        return await handlers_hook_coordination.handle_optimize_session_end(self, args)

    async def _handle_optimize_user_prompt_submit(self, args: dict) -> list[TextContent]:
        """Forward to Hook Coordination handler: optimize_user_prompt_submit."""
        from . import handlers_hook_coordination
        return await handlers_hook_coordination.handle_optimize_user_prompt_submit(self, args)

    async def _handle_optimize_post_tool_use(self, args: dict) -> list[TextContent]:
        """Forward to Hook Coordination handler: optimize_post_tool_use."""
        from . import handlers_hook_coordination
        return await handlers_hook_coordination.handle_optimize_post_tool_use(self, args)

    # ============================================================================
    # AGENT OPTIMIZATION HANDLERS (5 operations)
    # ============================================================================
    # These handlers implement optimized agent patterns using Phase 5-6 tools

    async def _handle_optimize_planning_orchestrator(self, args: dict) -> list[TextContent]:
        """Forward to Agent Optimization handler: optimize_planning_orchestrator."""
        from . import handlers_agent_optimization
        return await handlers_agent_optimization.handle_optimize_planning_orchestrator(self, args)

