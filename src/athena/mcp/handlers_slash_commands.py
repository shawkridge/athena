"""Slash Command Handlers for Phase 4 (6 new user-facing commands).

These handlers implement 6 new slash commands that provide direct user access
to Phase 5-6 optimization capabilities through a command-line interface.
"""

import logging
from typing import Any, List

logger = logging.getLogger(__name__)


async def handle_consolidate_advanced(server: Any, args: dict) -> List[Any]:
    """Handle /consolidate-advanced command: Advanced consolidation with strategy.

    Runs consolidation with strategy selection and quality measurement.

    Args:
        server: MCP server instance
        args: {
            "project_id": int (optional, default: 1),
            "strategy": str (balanced|speed|quality|minimal, default: auto),
            "measure_quality": bool (default: true),
            "verbose": bool (default: true)
        }

    Returns:
        List with TextContent: Consolidation report with quality metrics
    """
    try:
        project_id = args.get("project_id", 1)
        strategy = args.get("strategy", "auto")
        measure_quality = args.get("measure_quality", True)
        verbose = args.get("verbose", True)

        if not hasattr(server, '_consolidate_advanced_handler'):
            from ..integration.slash_commands import ConsolidateAdvancedCommand
            server._consolidate_advanced_handler = ConsolidateAdvancedCommand(server.store.db)

        result = await server._consolidate_advanced_handler.execute(
            project_id=project_id,
            strategy=strategy,
            measure_quality=measure_quality,
            verbose=verbose
        )

        # Format response
        from mcp.types import TextContent
        text = f"""
╔════════════════════════════════════════════════════════════════╗
║          CONSOLIDATE-ADVANCED COMMAND RESULTS                  ║
╚════════════════════════════════════════════════════════════════╝

Status: {result.get('status')}
Strategy: {result.get('strategy_used')}
Events Consolidated: {result.get('events_consolidated')}
Duration: {result.get('duration_ms')}ms

Quality Metrics:
  Overall Score: {result.get('quality_score'):.1%}
  Compression Ratio: {result.get('compression_ratio'):.1%}
  Recall Score: {result.get('recall_score'):.1%}
  Consistency: {result.get('consistency_score'):.1%}

Patterns Extracted: {result.get('patterns_extracted')}
Consolidation Cycles: {result.get('consolidation_cycles')}
Target Quality Met: {'✓ YES' if result.get('quality_target_met') else '✗ NO'}
"""
        return [TextContent(type="text", text=text)]

    except Exception as e:
        logger.error(f"Consolidate advanced command failed: {e}", exc_info=True)
        from mcp.types import TextContent
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_plan_validate_advanced(server: Any, args: dict) -> List[Any]:
    """Handle /plan-validate-advanced command: Comprehensive plan validation.

    Validates plan with 3-level validation + scenario simulation.

    Args:
        server: MCP server instance
        args: {
            "task_id": int (optional),
            "task_description": str (optional),
            "include_scenarios": bool (default: true),
            "strict_mode": bool (default: false)
        }

    Returns:
        List with TextContent: Validation report with risk assessment
    """
    try:
        task_id = args.get("task_id")
        task_description = args.get("task_description")
        include_scenarios = args.get("include_scenarios", True)
        strict_mode = args.get("strict_mode", False)

        if not hasattr(server, '_plan_validate_advanced_handler'):
            from ..integration.slash_commands import PlanValidateAdvancedCommand
            server._plan_validate_advanced_handler = PlanValidateAdvancedCommand(server.store.db)

        result = await server._plan_validate_advanced_handler.execute(
            task_id=task_id,
            task_description=task_description,
            include_scenarios=include_scenarios,
            strict_mode=strict_mode
        )

        # Format response
        from mcp.types import TextContent
        text = f"""
╔════════════════════════════════════════════════════════════════╗
║        PLAN-VALIDATE-ADVANCED COMMAND RESULTS                  ║
╚════════════════════════════════════════════════════════════════╝

Status: {result.get('status')}
Plan Steps: {result.get('plan_steps')}
Estimated Duration: {result.get('estimated_duration')} minutes

3-Level Validation Results:
  ✓ Structure Valid: {result.get('structure_valid')}
  ✓ Feasibility Valid: {result.get('feasibility_valid')}
  ✓ Rules Valid: {result.get('rules_valid')}

Quality Metrics:
  Properties Score: {result.get('properties_score'):.1%}
  Success Probability: {result.get('success_probability'):.1%}
  Confidence: {result.get('confidence_score'):.1%}

Scenarios Analyzed: {result.get('scenarios_count')}
Critical Path: {result.get('critical_path')}
Ready for Execution: {'✓ YES' if result.get('ready_for_execution') else '✗ NO'}

Issues Found: {len(result.get('validation_issues', []))}
Recommendations: {', '.join(result.get('recommendations', []))}
"""
        return [TextContent(type="text", text=text)]

    except Exception as e:
        logger.error(f"Plan validate advanced command failed: {e}", exc_info=True)
        from mcp.types import TextContent
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_task_health(server: Any, args: dict) -> List[Any]:
    """Handle /task-health command: Real-time task health monitoring.

    Monitors task health with progress, errors, and blockers tracking.

    Args:
        server: MCP server instance
        args: {
            "task_id": int (optional),
            "project_id": int (optional, default: 1),
            "include_trends": bool (default: true)
        }

    Returns:
        List with TextContent: Health dashboard with status and trends
    """
    try:
        task_id = args.get("task_id")
        project_id = args.get("project_id", 1)
        include_trends = args.get("include_trends", True)

        if not hasattr(server, '_task_health_handler'):
            from ..integration.slash_commands import TaskHealthCommand
            server._task_health_handler = TaskHealthCommand(server.store.db)

        result = await server._task_health_handler.execute(
            task_id=task_id,
            project_id=project_id,
            include_trends=include_trends
        )

        # Format response
        from mcp.types import TextContent
        status_emoji = "🟢" if result.get('health_score', 0) >= 0.75 else ("🟡" if result.get('health_score', 0) >= 0.50 else "🔴")
        text = f"""
╔════════════════════════════════════════════════════════════════╗
║              TASK-HEALTH COMMAND RESULTS                       ║
╚════════════════════════════════════════════════════════════════╝

Task Health Status: {status_emoji} {result.get('health_status')}
Health Score: {result.get('health_score'):.1%}
Progress: {result.get('progress_percent'):.0f}%

Progress Details:
  Completed Tasks: {result.get('completed_tasks')}
  Total Tasks: {result.get('total_tasks')}
  Estimated Remaining: {result.get('estimated_remaining')} min

Issues:
  Errors: {result.get('error_count')}
  Blockers: {result.get('blocker_count')}
  Warnings: {result.get('warning_count')}

Trend: {result.get('health_trend')}
Last Updated: {result.get('last_update')}

Recommendations:
  {chr(10).join([f"• {r}" for r in result.get('recommendations', [])])}
"""
        return [TextContent(type="text", text=text)]

    except Exception as e:
        logger.error(f"Task health command failed: {e}", exc_info=True)
        from mcp.types import TextContent
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_estimate_resources(server: Any, args: dict) -> List[Any]:
    """Handle /estimate-resources command: Resource estimation for tasks.

    Estimates time, expertise, and tool requirements for task execution.

    Args:
        server: MCP server instance
        args: {
            "task_id": int (optional),
            "task_description": str (optional),
            "project_id": int (optional, default: 1),
            "include_breakdown": bool (default: true)
        }

    Returns:
        List with TextContent: Resource estimation with breakdown
    """
    try:
        task_id = args.get("task_id")
        task_description = args.get("task_description")
        project_id = args.get("project_id", 1)
        include_breakdown = args.get("include_breakdown", True)

        if not hasattr(server, '_estimate_resources_handler'):
            from ..integration.slash_commands import EstimateResourcesCommand
            server._estimate_resources_handler = EstimateResourcesCommand(server.store.db)

        result = await server._estimate_resources_handler.execute(
            task_id=task_id,
            task_description=task_description,
            project_id=project_id,
            include_breakdown=include_breakdown
        )

        # Format response
        from mcp.types import TextContent
        text = f"""
╔════════════════════════════════════════════════════════════════╗
║           ESTIMATE-RESOURCES COMMAND RESULTS                   ║
╚════════════════════════════════════════════════════════════════╝

Complexity Level: {result.get('complexity_level')}/10
Estimated Duration: {result.get('duration_estimate')} minutes
Confidence: {result.get('confidence_percent'):.0f}%

Time Breakdown:
  Design: {result.get('design_time')}%
  Implementation: {result.get('implementation_time')}%
  Testing: {result.get('testing_time')}%
  Deployment: {result.get('deployment_time')}%

Required Expertise:
  {chr(10).join([f"  • {domain}: {level}" for domain, level in result.get('expertise_required', {}).items()])}

Required Tools:
  {chr(10).join([f"  • {tool}" for tool in result.get('tools_required', [])])}

Risk Assessment:
  Low-Risk Tasks: {result.get('low_risk_percentage'):.0f}%
  Medium-Risk: {result.get('medium_risk_percentage'):.0f}%
  High-Risk: {result.get('high_risk_percentage'):.0f}%

Optimization Potential: {result.get('optimization_potential'):.0f}%
"""
        return [TextContent(type="text", text=text)]

    except Exception as e:
        logger.error(f"Estimate resources command failed: {e}", exc_info=True)
        from mcp.types import TextContent
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_stress_test_plan(server: Any, args: dict) -> List[Any]:
    """Handle /stress-test-plan command: Scenario simulation and testing.

    Tests plan across 5 scenarios (best, worst, likely, critical, black swan).

    Args:
        server: MCP server instance
        args: {
            "task_id": int (optional),
            "task_description": str (optional),
            "confidence_level": float (0.5-0.95, default: 0.80)
        }

    Returns:
        List with TextContent: Stress test results with confidence intervals
    """
    try:
        task_id = args.get("task_id")
        task_description = args.get("task_description")
        confidence_level = args.get("confidence_level", 0.80)

        if not hasattr(server, '_stress_test_plan_handler'):
            from ..integration.slash_commands import StressTestPlanCommand
            server._stress_test_plan_handler = StressTestPlanCommand(server.store.db)

        result = await server._stress_test_plan_handler.execute(
            task_id=task_id,
            task_description=task_description,
            confidence_level=confidence_level
        )

        # Format response
        from mcp.types import TextContent
        text = f"""
╔════════════════════════════════════════════════════════════════╗
║             STRESS-TEST-PLAN COMMAND RESULTS                   ║
╚════════════════════════════════════════════════════════════════╝

Confidence Level: {confidence_level:.0%}
Scenarios Analyzed: {result.get('scenarios_analyzed')}

Scenario Results:
  Best Case: {result.get('best_case_duration')} min ({result.get('best_case_probability'):.1%} likely)
  Likely Case: {result.get('likely_case_duration')} min ({result.get('likely_case_probability'):.1%} likely)
  Worst Case: {result.get('worst_case_duration')} min ({result.get('worst_case_probability'):.1%} likely)

Risk Scenarios:
  Critical Path: {result.get('critical_path_duration')} min
  Black Swan: {result.get('black_swan_duration')} min

Confidence Intervals:
  Minimum: {result.get('min_duration')} min
  Maximum: {result.get('max_duration')} min
  Range: {result.get('duration_range')} min

Success Probability: {result.get('success_probability'):.0%}
Expected Value: {result.get('expected_duration')} min

Risk Factors:
  {chr(10).join([f"  • {risk}" for risk in result.get('identified_risks', [])])}

Mitigation Strategies:
  {chr(10).join([f"  • {strategy}" for strategy in result.get('mitigation_strategies', [])])}
"""
        return [TextContent(type="text", text=text)]

    except Exception as e:
        logger.error(f"Stress test plan command failed: {e}", exc_info=True)
        from mcp.types import TextContent
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_learning_effectiveness(server: Any, args: dict) -> List[Any]:
    """Handle /learning-effectiveness command: Pattern analysis and effectiveness.

    Analyzes learning effectiveness and strategy patterns over time.

    Args:
        server: MCP server instance
        args: {
            "project_id": int (optional, default: 1),
            "days_back": int (default: 7),
            "include_recommendations": bool (default: true)
        }

    Returns:
        List with TextContent: Learning effectiveness report with recommendations
    """
    try:
        project_id = args.get("project_id", 1)
        days_back = args.get("days_back", 7)
        include_recommendations = args.get("include_recommendations", True)

        if not hasattr(server, '_learning_effectiveness_handler'):
            from ..integration.slash_commands import LearningEffectivenessCommand
            server._learning_effectiveness_handler = LearningEffectivenessCommand(server.store.db)

        result = await server._learning_effectiveness_handler.execute(
            project_id=project_id,
            days_back=days_back,
            include_recommendations=include_recommendations
        )

        # Format response
        from mcp.types import TextContent
        text = f"""
╔════════════════════════════════════════════════════════════════╗
║        LEARNING-EFFECTIVENESS COMMAND RESULTS                  ║
╚════════════════════════════════════════════════════════════════╝

Analysis Period: Last {days_back} days
Consolidation Runs: {result.get('consolidation_runs')}
Pattern Extractions: {result.get('patterns_extracted')}

Strategy Effectiveness:
  Balanced Strategy: {result.get('balanced_effectiveness'):.1%}
  Speed Strategy: {result.get('speed_effectiveness'):.1%}
  Quality Strategy: {result.get('quality_effectiveness'):.1%}
  Minimal Strategy: {result.get('minimal_effectiveness'):.1%}

Best Performing Strategy: {result.get('best_strategy')} ({result.get('best_strategy_score'):.1%})

Learning Metrics:
  Encoding Rounds: {result.get('encoding_rounds')}
  Knowledge Growth: {result.get('knowledge_growth'):.1%}
  Pattern Stability: {result.get('pattern_stability'):.1%}
  Gap Coverage: {result.get('gap_coverage'):.1%}

Trend: {result.get('learning_trend')}
Velocity: {result.get('learning_velocity'):.1%} per day

Top Recommendations:
  {chr(10).join([f"  {i+1}. {rec}" for i, rec in enumerate(result.get('recommendations', [])[:3])])}

Domain Expertise:
  {chr(10).join([f"  • {domain}: {score:.0%}" for domain, score in list(result.get('domain_expertise', {}).items())[:5]])}
"""
        return [TextContent(type="text", text=text)]

    except Exception as e:
        logger.error(f"Learning effectiveness command failed: {e}", exc_info=True)
        from mcp.types import TextContent
        return [TextContent(type="text", text=f"Error: {str(e)}")]
