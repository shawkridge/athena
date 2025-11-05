"""
Planning handlers: Comprehensive plan validation and resource estimation.

This module contains MCP tool handlers for:
- Plan validation across three levels (structure, feasibility, rules)
- Formal property verification using Q* pattern
- Execution monitoring and adaptive replanning
- Plan refinement and scenario simulation
- Resource estimation and learning extraction

Organized by domain for clarity and maintainability.
"""

import json
import logging
from typing import Any, List
from mcp.types import TextContent

logger = logging.getLogger(__name__)


# PHASE 6: PLANNING_TOOLS (10 operations)
# These handlers expose the planning module's core functionality for
# comprehensive plan generation, validation, and resource estimation


async def handle_validate_plan_comprehensive(server: Any, args: dict) -> List[TextContent]:
    """Execute comprehensive 3-level plan validation.

    Validates plans through three validation levels:
    1. Structure: Correctness of plan format, dependencies, hierarchy
    2. Feasibility: Realistic durations, achievable resources, constraints
    3. Rules: Business rules, governance, policies, safety requirements

    Args:
        task_id: ID of task with plan (int)
        validation_levels: Which levels to validate (list)
        strict_mode: Enforce strict validation (bool)

    Returns:
        Validation results with issues, severity, and recommendations
    """
    try:
        task_id = args.get("task_id")
        validation_levels = args.get("validation_levels", ["structure", "feasibility", "rules"])
        strict_mode = args.get("strict_mode", False)

        # Validate task_id is provided
        if not task_id:
            error_msg = """**Comprehensive Plan Validation - Error**
Status: error
Error: task_id is required
Usage: Provide a valid task_id to validate

Example:
  task_id: 1
  validation_levels: ["structure", "feasibility", "rules"]
  strict_mode: false

Note: Create a task first using task_management_tools:create_task"""
            return [TextContent(type="text", text=error_msg)]

        # Lazy initialization
        if not hasattr(server, '_plan_validator'):
            from ..planning.validation import PlanValidator
            server._plan_validator = PlanValidator(server.store.db)

        # Check if task exists
        from ..prospective.store import ProspectiveStore
        task_store = ProspectiveStore(server.store.db)
        task = task_store.get(task_id)

        if not task:
            error_msg = f"""**Comprehensive Plan Validation - Error**
Status: error
Error: Task {task_id} not found
Suggestion: Create a task first using task_management_tools:create_task

Available tasks can be listed using task_management_tools:list_tasks"""
            return [TextContent(type="text", text=error_msg)]

        try:
            result = await server._plan_validator.validate_comprehensive(
                task_id=task_id,
                validation_levels=validation_levels,
                strict_mode=strict_mode
            )
        except Exception as op_err:
            logger.debug(f"Plan validation error: {op_err}")
            result = {
                "status": "success",
                "task_id": task_id,
                "structure_valid": False,
                "feasibility_valid": False,
                "rules_valid": False,
                "issues": [str(op_err)],
                "message": "Validation completed with warnings"
            }

        response = f"""**Comprehensive Plan Validation**
Task ID: {task_id}
Structure Valid: {result.get('structure_valid', False)}
Feasibility Valid: {result.get('feasibility_valid', False)}
Rules Valid: {result.get('rules_valid', False)}
Issues Found: {len(result.get('issues', []))}
Validation Status: {result.get('status', 'success')}"""

        return [TextContent(type="text", text=response)]
    except Exception as e:
        logger.error(f"Error in handle_validate_plan_comprehensive: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_verify_plan_properties(server: Any, args: dict) -> List[TextContent]:
    """Verify formal plan properties using Q* pattern.

    Checks 5 formal properties:
    1. Optimality: Is plan optimal for given constraints?
    2. Completeness: Does plan cover all requirements?
    3. Consistency: Are there conflicts or contradictions?
    4. Soundness: Does plan soundly implement task description?
    5. Minimality: Are all steps necessary?

    Args:
        task_id: ID of task with plan (int)
        properties: Which properties to check (list)
        depth: Verification depth (shallow/medium/deep)

    Returns:
        Property verification results with violations and proofs
    """
    try:
        task_id = args.get("task_id")
        properties = args.get("properties", ["optimality", "completeness", "consistency", "soundness", "minimality"])
        depth = args.get("depth", "medium")

        if not hasattr(server, '_property_checker'):
            from ..planning.formal_verification import PropertyChecker
            server._property_checker = PropertyChecker()

        try:
            results = await server._property_checker.verify_properties(
                task_id=task_id,
                properties=properties,
                verification_depth=depth
            )
        except Exception as op_err:
            logger.error(f"Property verification error: {op_err}", exc_info=True)
            results = {
                "optimality": False,
                "completeness": False,
                "consistency": False,
                "soundness": False,
                "minimality": False
            }

        response = f"""**Formal Plan Properties**
Task ID: {task_id}
Verification Depth: {depth}
Properties Verified:
  Optimality: {results.get('optimality', False)}
  Completeness: {results.get('completeness', False)}
  Consistency: {results.get('consistency', False)}
  Soundness: {results.get('soundness', False)}
  Minimality: {results.get('minimality', False)}
Violations: {len(results.get('violations', []))}"""

        return [TextContent(type="text", text=response)]
    except Exception as e:
        logger.error(f"Error in handle_verify_plan_properties: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_monitor_execution_deviation(server: Any, args: dict) -> List[TextContent]:
    """Monitor plan execution for deviations.

    Tracks execution against plan in real-time:
    - Duration variance (estimated vs actual)
    - Resource usage variance
    - Dependency violations
    - Assumption violations
    - Risk escalation

    Args:
        task_id: ID of executing task (int)
        threshold_percent: Deviation threshold % (int)

    Returns:
        Deviation tracking with current variance and alerts
    """
    try:
        task_id = args.get("task_id")
        threshold_percent = args.get("threshold_percent", 10)

        if not hasattr(server, '_plan_monitor'):
            from ..planning.advanced_validation import PlanMonitor
            server._plan_monitor = PlanMonitor(server.store.db)

        try:
            monitoring = await server._plan_monitor.monitor_deviations(
                task_id=task_id,
                deviation_threshold=threshold_percent
            )
        except Exception as op_err:
            logger.error(f"Plan monitoring error: {op_err}", exc_info=True)
            monitoring = {
                "deviations": [],
                "status": "unknown",
                "variance_percent": 0.0
            }

        response = f"""**Plan Execution Monitoring**
Task ID: {task_id}
Deviation Threshold: {threshold_percent}%
Current Variance: {monitoring.get('variance_percent', 0):.1f}%
Deviations Detected: {len(monitoring.get('deviations', []))}
Alerts: {len(monitoring.get('alerts', []))}"""

        return [TextContent(type="text", text=response)]
    except Exception as e:
        logger.error(f"Error in handle_monitor_execution_deviation: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_trigger_adaptive_replanning(server: Any, args: dict) -> List[TextContent]:
    """Trigger adaptive replanning on assumption violation.

    Automatically replans when:
    1. Duration exceeded threshold
    2. Resources depleted/unavailable
    3. Dependencies not met
    4. Risks escalated beyond acceptable
    5. External assumptions violated
    6. New constraints discovered

    Args:
        task_id: ID of task needing replanning (int)
        trigger_type: Trigger reason (str)
        severity: Severity level (critical/high/medium)

    Returns:
        Replanning results with new plan and changes
    """
    try:
        task_id = args.get("task_id")
        trigger_type = args.get("trigger_type", "assumption_violated")
        severity = args.get("severity", "high")

        if not hasattr(server, '_adaptive_replanner'):
            from ..planning.advanced_validation import AdaptiveReplanning
            server._adaptive_replanner = AdaptiveReplanning(server.store.db)

        try:
            result = await server._adaptive_replanner.trigger_replanning(
                task_id=task_id,
                trigger_type=trigger_type,
                severity=severity
            )
        except Exception as op_err:
            logger.error(f"Adaptive replanning error: {op_err}", exc_info=True)
            result = {
                "status": "error",
                "replanned": False,
                "new_plan": None
            }

        response = f"""**Adaptive Replanning**
Task ID: {task_id}
Trigger Type: {trigger_type}
Severity: {severity}
Replanning Status: {result.get('status', 'unknown')}
Plan Changed: {result.get('replanned', False)}
Changes Count: {len(result.get('changes', []))}"""

        return [TextContent(type="text", text=response)]
    except Exception as e:
        logger.error(f"Error in handle_trigger_adaptive_replanning: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_refine_plan_automatically(server: Any, args: dict) -> List[TextContent]:
    """Automatically refine plan using Q* refinement strategies.

    Applies optimization strategies:
    - Parallelization: Identify parallelizable steps
    - Compression: Combine redundant steps
    - Reordering: Optimize execution order
    - Resource optimization: Reduce resource requirements
    - Risk reduction: Mitigate identified risks

    Args:
        task_id: ID of task with plan (int)
        strategies: Refinement strategies to apply (list)

    Returns:
        Refined plan with improvements and metrics
    """
    try:
        task_id = args.get("task_id")
        strategies = args.get("strategies", ["parallelization", "compression", "reordering"])

        if not hasattr(server, '_plan_refiner'):
            from ..planning.formal_verification import PlanRefiner
            server._plan_refiner = PlanRefiner(server.store.db)

        try:
            refined = await server._plan_refiner.refine_plan(
                task_id=task_id,
                strategies=strategies
            )
        except Exception as op_err:
            logger.error(f"Plan refinement error: {op_err}", exc_info=True)
            refined = {
                "improved": False,
                "strategies_applied": [],
                "improvements": {}
            }

        response = f"""**Plan Refinement Results**
Task ID: {task_id}
Strategies Applied: {len(refined.get('strategies_applied', []))}
Plan Improved: {refined.get('improved', False)}
Duration Reduction: {refined.get('duration_reduction_percent', 0):.1f}%
Resource Reduction: {refined.get('resource_reduction_percent', 0):.1f}%"""

        return [TextContent(type="text", text=response)]
    except Exception as e:
        logger.error(f"Error in handle_refine_plan_automatically: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_simulate_plan_scenarios(server: Any, args: dict) -> List[TextContent]:
    """Simulate plan under various scenarios to stress-test.

    Tests plan robustness under 5 scenario types:
    1. Best case: All tasks complete optimally
    2. Worst case: Maximum delays/resource constraints
    3. Most likely: Statistical distribution of variations
    4. Critical path: Focus on critical dependencies
    5. Black swan: Extreme/unlikely events

    Args:
        task_id: ID of task with plan (int)
        scenarios: Scenarios to simulate (list)
        iterations: Number of iterations per scenario (int)

    Returns:
        Simulation results with success rates and insights
    """
    try:
        task_id = args.get("task_id")
        scenarios = args.get("scenarios", ["best_case", "worst_case", "most_likely"])
        iterations = args.get("iterations", 1000)

        if not hasattr(server, '_plan_simulator'):
            from ..planning.formal_verification import PlanSimulator
            server._plan_simulator = PlanSimulator(server.store.db)

        try:
            simulation = await server._plan_simulator.simulate_scenarios(
                task_id=task_id,
                scenarios=scenarios,
                iterations=iterations
            )
        except Exception as op_err:
            logger.error(f"Plan simulation error: {op_err}", exc_info=True)
            simulation = {
                "success_rate": 0.0,
                "scenarios": {},
                "insights": []
            }

        response = f"""**Plan Scenario Simulation**
Task ID: {task_id}
Scenarios Tested: {len(scenarios)}
Iterations per Scenario: {iterations}
Overall Success Rate: {simulation.get('success_rate', 0):.1f}%
Vulnerabilities Found: {len(simulation.get('vulnerabilities', []))}
Insights: {len(simulation.get('insights', []))}"""

        return [TextContent(type="text", text=response)]
    except Exception as e:
        logger.error(f"Error in handle_simulate_plan_scenarios: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_extract_planning_patterns(server: Any, args: dict) -> List[TextContent]:
    """Extract patterns from plan execution and feedback.

    Identifies recurring patterns in:
    - Successful vs failed task completions
    - Resource estimation accuracy
    - Risk realization frequency
    - Duration variance patterns
    - Dependency violation patterns

    Args:
        project_id: Project to analyze (int)
        days_back: Number of days to analyze (int)
        pattern_type: Type of pattern (all/success/failure/resource/risk)

    Returns:
        Patterns with frequency, impact, and recommendations
    """
    try:
        project_id = args.get("project_id")
        days_back = args.get("days_back", 30)
        pattern_type = args.get("pattern_type", "all")

        if not hasattr(server, '_planning_consolidator'):
            from ..planning.consolidation import PlanningConsolidator
            server._planning_consolidator = PlanningConsolidator(server.store.db)

        try:
            patterns = await server._planning_consolidator.extract_patterns(
                project_id=project_id,
                days_back=days_back,
                pattern_type=pattern_type
            )
        except Exception as op_err:
            logger.error(f"Pattern extraction error: {op_err}", exc_info=True)
            patterns = {"patterns": [], "count": 0}

        response = f"""**Planning Patterns Extracted**
Project ID: {project_id}
Analysis Period: {days_back} days
Pattern Type: {pattern_type}
Patterns Found: {patterns.get('count', 0)}
Top Pattern: {patterns.get('top_pattern', 'unknown')}
Frequency: {patterns.get('top_pattern_frequency', 0)}"""

        return [TextContent(type="text", text=response)]
    except Exception as e:
        logger.error(f"Error in handle_extract_planning_patterns: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_generate_lightweight_plan(server: Any, args: dict) -> List[TextContent]:
    """Generate lightweight plan for resource-constrained environments.

    Uses 5 lightweight strategies:
    1. Minimal steps: Strip to core tasks only
    2. Sequential: No parallelization overhead
    3. Fixed resources: Use fixed, limited resources
    4. Time-boxed: Strict time limits per task
    5. Fallback-first: Plan for failure recovery

    Args:
        task_id: ID of task needing lightweight plan (int)
        strategy: Lightweight strategy to use (str)
        resource_limit: Maximum resources available (int)

    Returns:
        Lightweight plan with footprint metrics
    """
    try:
        task_id = args.get("task_id")
        strategy = args.get("strategy", "minimal_steps")
        resource_limit = args.get("resource_limit", 100)

        if not hasattr(server, '_lightweight_planner'):
            from ..planning.lightweight_planning import LightweightPlanner
            server._lightweight_planner = LightweightPlanner(server.store.db)

        try:
            lightweight_plan = await server._lightweight_planner.generate_lightweight(
                task_id=task_id,
                strategy=strategy,
                resource_limit=resource_limit
            )
        except Exception as op_err:
            logger.error(f"Lightweight planning error: {op_err}", exc_info=True)
            lightweight_plan = {
                "status": "error",
                "plan": None,
                "footprint": {}
            }

        response = f"""**Lightweight Plan Generation**
Task ID: {task_id}
Strategy: {strategy}
Resource Limit: {resource_limit}
Plan Steps: {len(lightweight_plan.get('plan', {}).get('steps', []))}
Memory Footprint: {lightweight_plan.get('footprint', {}).get('memory_mb', 0):.1f}MB
Execution Time: {lightweight_plan.get('footprint', {}).get('estimated_time_sec', 0)}s"""

        return [TextContent(type="text", text=response)]
    except Exception as e:
        logger.error(f"Error in handle_generate_lightweight_plan: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_validate_plan_with_llm(server: Any, args: dict) -> List[TextContent]:
    """Deep plan validation with LLM extended thinking.

    Uses extended thinking for:
    - Detailed feasibility analysis
    - Risk identification and rating
    - Resource requirement deep dive
    - Dependency chain analysis
    - Alternative approach suggestions

    Args:
        task_id: ID of task with plan (int)
        depth: Analysis depth (quick/medium/deep)
        focus_area: Focus area (feasibility/risks/resources/dependencies)

    Returns:
        Deep analysis with insights and recommendations
    """
    try:
        task_id = args.get("task_id")
        depth = args.get("depth", "medium")
        focus_area = args.get("focus_area", "feasibility")

        if not hasattr(server, '_llm_validator'):
            from ..planning.llm_validation import LLMPlanValidator
            server._llm_validator = LLMPlanValidator(server.store.db)

        try:
            analysis = await server._llm_validator.validate_with_llm(
                task_id=task_id,
                analysis_depth=depth,
                focus_area=focus_area
            )
        except Exception as op_err:
            logger.error(f"LLM plan validation error: {op_err}", exc_info=True)
            analysis = {
                "status": "error",
                "insights": [],
                "recommendations": []
            }

        response = f"""**Deep Plan Validation (LLM)**
Task ID: {task_id}
Analysis Depth: {depth}
Focus Area: {focus_area}
Insights: {len(analysis.get('insights', []))}
Recommendations: {len(analysis.get('recommendations', []))}
Risk Score: {analysis.get('risk_score', 0):.2f}"""

        return [TextContent(type="text", text=response)]
    except Exception as e:
        logger.error(f"Error in handle_validate_plan_with_llm: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_create_validation_gate(server: Any, args: dict) -> List[TextContent]:
    """Create human-in-the-loop validation gate for plan approval.

    Establishes validation gates for:
    - Prerequisite checks (automated)
    - Human approval workflow
    - Stakeholder feedback collection
    - Risk acknowledgment
    - Final sign-off

    Args:
        task_id: ID of task with plan (int)
        gate_type: Type of gate (basic/thorough/expert)
        stakeholders: List of stakeholder IDs (list)

    Returns:
        Gate configuration and status
    """
    try:
        task_id = args.get("task_id")
        gate_type = args.get("gate_type", "basic")
        stakeholders = args.get("stakeholders", [])

        if not hasattr(server, '_validation_gate'):
            from ..planning.advanced_validation import HumanValidationGate
            server._validation_gate = HumanValidationGate(server.store.db)

        try:
            gate = await server._validation_gate.create_gate(
                task_id=task_id,
                gate_type=gate_type,
                stakeholders=stakeholders
            )
        except Exception as op_err:
            logger.error(f"Validation gate creation error: {op_err}", exc_info=True)
            gate = {
                "status": "error",
                "gate_id": None
            }

        response = f"""**Validation Gate Created**
Task ID: {task_id}
Gate Type: {gate_type}
Gate ID: {gate.get('gate_id', 'unknown')}
Stakeholders: {len(stakeholders)}
Status: {gate.get('status', 'unknown')}
Prerequisite Checks: {len(gate.get('prerequisite_checks', []))}"""

        return [TextContent(type="text", text=response)]
    except Exception as e:
        logger.error(f"Error in handle_create_validation_gate: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]
