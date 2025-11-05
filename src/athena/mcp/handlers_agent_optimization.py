"""Agent Optimization handlers: Optimized agent implementations using Phase 5-6 tools (5 operations).

These handlers expose optimized implementations of 5 key agents that leverage Phase 5-6
operations for improved planning validation, goal management, and learning effectiveness.
"""

import json
import logging
from typing import Any, List
from mcp.types import TextContent

logger = logging.getLogger(__name__)


# AGENT OPTIMIZATION: Agent Enhancement Handlers (5 operations)
# These handlers coordinate complex agent behavior patterns using Phase 5-6 tools


async def handle_optimize_planning_orchestrator(server: Any, args: dict) -> List[TextContent]:
    """Optimize planning-orchestrator: Formal verification + scenario simulation.

    Enhances plan generation with comprehensive validation:
    1. Generate initial plan (current behavior)
    2. 3-level comprehensive validation (Phase 6)
    3. Q* formal property verification (Phase 6)
    4. 5-scenario stress testing (Phase 6)
    5. Build confidence report with recommendations

    Args:
        task_description: Description of task to plan
        task_id: ID of task with existing plan
        include_scenarios: Whether to run scenarios (default: true)
        strict_mode: Strict validation (default: false)

    Returns:
        Plan with validation results, property scores, scenario analysis
    """
    try:
        task_description = args.get("task_description")
        task_id = args.get("task_id")
        include_scenarios = args.get("include_scenarios", True)
        strict_mode = args.get("strict_mode", False)

        # Lazy initialization
        if not hasattr(server, '_planning_orchestrator_optimizer'):
            from ..integration.agent_optimization import PlanningOrchestratorOptimizer
            server._planning_orchestrator_optimizer = PlanningOrchestratorOptimizer(server.store.db)

        try:
            result = await server._planning_orchestrator_optimizer.execute(
                task_description=task_description,
                task_id=task_id,
                include_scenarios=include_scenarios,
                strict_mode=strict_mode
            )
        except Exception as op_err:
            logger.error(f"Planning orchestrator optimization error: {op_err}", exc_info=True)
            result = {
                "status": "error",
                "ready_for_execution": False,
                "plan_quality_score": 0
            }

        # Format response
        response = f"""**Optimized Planning-Orchestrator Agent**
Status: {result.get('status', 'unknown')}

Plan Generation:
- Plan Steps: {result.get('plan_steps', 0)}
- Estimated Duration: {result.get('estimated_duration', 'unknown')}

Validation Results:
- Structure Valid: {result.get('structure_valid', False)}
- Feasibility Valid: {result.get('feasibility_valid', False)}
- Rules Valid: {result.get('rules_valid', False)}
- Issues Found: {len(result.get('validation_issues', []))}

Q* Formal Properties:
- Overall Score: {result.get('properties_score', 0):.2f}
- Optimality: {result.get('optimality', 0):.2f}
- Completeness: {result.get('completeness', 0):.2f}
- Consistency: {result.get('consistency', 0):.2f}
- Soundness: {result.get('soundness', 0):.2f}
- Minimality: {result.get('minimality', 0):.2f}

Scenario Testing:
- Scenarios Tested: {result.get('scenarios_count', 0)}
- Success Probability: {result.get('success_probability', 0):.1%}
- Critical Path: {result.get('critical_path', 'unknown')}

Execution Readiness:
- Ready for Execution: {result.get('ready_for_execution', False)}
- Confidence Score: {result.get('confidence_score', 0):.2f}"""

        return [TextContent(type="text", text=response)]
    except Exception as e:
        logger.error(f"Error in handle_optimize_planning_orchestrator: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_optimize_goal_orchestrator(server: Any, args: dict) -> List[TextContent]:
    """Optimize goal-orchestrator: Health monitoring + automatic replanning.

    Enhances goal management with real-time health tracking:
    1. Load goal with plan validation (Phase 6)
    2. Activate goal and validate plan
    3. Record execution progress
    4. Monitor goal health (Phase 5)
    5. Trigger adaptive replanning if degraded (Phase 6)
    6. Extract execution patterns (Phase 6)

    Args:
        goal_id: ID of goal to manage
        activate: Whether to activate goal (default: true)
        monitor_health: Whether to monitor health (default: true)
        extract_patterns: Whether to extract patterns on completion (default: true)

    Returns:
        Goal state with health metrics, activation status, replanning triggers
    """
    try:
        goal_id = args.get("goal_id")
        activate = args.get("activate", True)
        monitor_health = args.get("monitor_health", True)
        extract_patterns = args.get("extract_patterns", True)

        if not hasattr(server, '_goal_orchestrator_optimizer'):
            from ..integration.agent_optimization import GoalOrchestratorOptimizer
            server._goal_orchestrator_optimizer = GoalOrchestratorOptimizer(server.store.db)

        try:
            result = await server._goal_orchestrator_optimizer.execute(
                goal_id=goal_id,
                activate=activate,
                monitor_health=monitor_health,
                extract_patterns=extract_patterns
            )
        except Exception as op_err:
            logger.error(f"Goal orchestrator optimization error: {op_err}", exc_info=True)
            result = {
                "status": "error",
                "activated": False,
                "health_score": 0
            }

        # Format response
        response = f"""**Optimized Goal-Orchestrator Agent**
Status: {result.get('status', 'unknown')}
Goal ID: {goal_id}

Goal Activation:
- Activated: {result.get('activated', False)}
- Plan Valid: {result.get('plan_valid', False)}
- Plan Issues: {len(result.get('plan_issues', []))}

Health Monitoring:
- Health Score: {result.get('health_score', 0):.2f}
- Status: {result.get('health_status', 'unknown')}
- Progress: {result.get('progress_percent', 0):.1f}%

Execution Status:
- Completed Tasks: {result.get('completed_tasks', 0)}
- Blocked: {result.get('blocked', False)}
- Blockers: {len(result.get('blockers', []))}

Adaptive Replanning:
- Replanning Needed: {result.get('replanning_triggered', False)}
- Trigger Reason: {result.get('replanning_reason', 'none')}

Pattern Extraction:
- Patterns Extracted: {result.get('patterns_extracted', 0)}
- Learning Completed: {result.get('learning_completed', False)}"""

        return [TextContent(type="text", text=response)]
    except Exception as e:
        logger.error(f"Error in handle_optimize_goal_orchestrator: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_optimize_consolidation_trigger(server: Any, args: dict) -> List[TextContent]:
    """Optimize consolidation-trigger: Dual-process + quality measurement.

    Enhances consolidation with advanced reasoning and metrics:
    1. Analyze trigger reason and select strategy
    2. Run consolidation cycle (Phase 5)
    3. Apply dual-process reasoning (System 1 + System 2)
    4. Measure consolidation quality (Phase 5)
    5. Analyze strategy effectiveness (Phase 5)
    6. Record quality metrics

    Args:
        trigger_reason: Why consolidation is triggered
        strategy: Consolidation strategy to use (balanced/speed/quality/minimal)
        measure_quality: Whether to measure quality (default: true)
        analyze_strategies: Whether to analyze strategies (default: false)

    Returns:
        Consolidation results with quality scores and strategy analysis
    """
    try:
        trigger_reason = args.get("trigger_reason", "manual")
        strategy = args.get("strategy", "auto")
        measure_quality = args.get("measure_quality", True)
        analyze_strategies = args.get("analyze_strategies", False)

        if not hasattr(server, '_consolidation_trigger_optimizer'):
            from ..integration.agent_optimization import ConsolidationTriggerOptimizer
            server._consolidation_trigger_optimizer = ConsolidationTriggerOptimizer(server.store.db)

        try:
            result = await server._consolidation_trigger_optimizer.execute(
                trigger_reason=trigger_reason,
                strategy=strategy,
                measure_quality=measure_quality,
                analyze_strategies=analyze_strategies
            )
        except Exception as op_err:
            logger.error(f"Consolidation trigger optimization error: {op_err}", exc_info=True)
            result = {
                "status": "error",
                "quality_score": 0,
                "events_consolidated": 0
            }

        # Format response
        response = f"""**Optimized Consolidation-Trigger Agent**
Status: {result.get('status', 'unknown')}
Trigger Reason: {trigger_reason}

Consolidation Execution:
- Events Consolidated: {result.get('events_consolidated', 0)}
- Duration: {result.get('duration_ms', 0)}ms
- Strategy Used: {result.get('strategy_used', 'unknown')}

Dual-Process Reasoning:
- System 1 (Fast): <100ms heuristic clustering
- System 2 (Slow): LLM validation on uncertainty >0.5
- Reasoning Applied: {result.get('llm_reasoning_applied', False)}

Quality Metrics:
- Overall Score: {result.get('quality_score', 0):.2f}
- Compression: {result.get('compression_ratio', 0):.2f}
- Recall: {result.get('recall_score', 0):.2f}
- Consistency: {result.get('consistency_score', 0):.2f}
- Density: {result.get('density_score', 0):.2f}

Strategy Analysis:
- Strategies Analyzed: {result.get('strategies_analyzed', 0)}
- Best Strategy: {result.get('best_strategy', 'unknown')}
- Strategy Effectiveness: {result.get('strategy_effectiveness', 'unknown')}

Outcomes:
- Patterns Extracted: {result.get('patterns_extracted', 0)}
- Quality Target Met: {result.get('quality_target_met', False)}"""

        return [TextContent(type="text", text=response)]
    except Exception as e:
        logger.error(f"Error in handle_optimize_consolidation_trigger: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_optimize_strategy_orchestrator(server: Any, args: dict) -> List[TextContent]:
    """Optimize strategy-orchestrator: Effectiveness analysis + auto-selection.

    Enhances strategy selection with data-driven decisions:
    1. Analyze strategy effectiveness across project (Phase 5)
    2. Score strategies based on history and context
    3. Auto-select best strategy
    4. Generate automatic plan refinements (Phase 6)
    5. Track improvements from refinements

    Args:
        task_context: Context for strategy selection
        analyze_effectiveness: Whether to analyze strategies (default: true)
        apply_refinements: Whether to refine automatically (default: true)

    Returns:
        Selected strategy with effectiveness scores and refinement suggestions
    """
    try:
        task_context = args.get("task_context", {})
        analyze_effectiveness = args.get("analyze_effectiveness", True)
        apply_refinements = args.get("apply_refinements", True)

        if not hasattr(server, '_strategy_orchestrator_optimizer'):
            from ..integration.agent_optimization import StrategyOrchestratorOptimizer
            server._strategy_orchestrator_optimizer = StrategyOrchestratorOptimizer(server.store.db)

        try:
            result = await server._strategy_orchestrator_optimizer.execute(
                task_context=task_context,
                analyze_effectiveness=analyze_effectiveness,
                apply_refinements=apply_refinements
            )
        except Exception as op_err:
            logger.error(f"Strategy orchestrator optimization error: {op_err}", exc_info=True)
            result = {
                "status": "error",
                "selected_strategy": "unknown",
                "effectiveness_score": 0
            }

        # Format response
        response = f"""**Optimized Strategy-Orchestrator Agent**
Status: {result.get('status', 'unknown')}

Strategy Selection:
- Selected Strategy: {result.get('selected_strategy', 'unknown')}
- Effectiveness Score: {result.get('effectiveness_score', 0):.2f}
- Success Rate: {result.get('success_rate', 0):.1%}

Strategy Analysis:
- Strategies Evaluated: {result.get('strategies_evaluated', 0)}
- Project History Used: {result.get('project_history_weight', 0):.1%}

Plan Refinement (Q*):
- Refinements Applied: {result.get('refinements_applied', 0)}
- Timeline Reduction: {result.get('timeline_reduction_percent', 0):.1f}%
- Resource Savings: {result.get('resource_savings_percent', 0):.1f}%

Recommendations:
- Primary Strategy: {result.get('primary_strategy', 'unknown')}
- Confidence: {result.get('strategy_confidence', 0):.2f}
- Alternative Strategies: {result.get('alternatives_count', 0)}"""

        return [TextContent(type="text", text=response)]
    except Exception as e:
        logger.error(f"Error in handle_optimize_strategy_orchestrator: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_optimize_attention_optimizer(server: Any, args: dict) -> List[TextContent]:
    """Optimize attention-optimizer: Expertise-weighted focus management.

    Enhances attention management with domain expertise weighting:
    1. Suppress distractions (current behavior)
    2. Get domain expertise levels (Phase 5)
    3. Weight focus by confidence in domain
    4. Analyze project patterns (Phase 5)
    5. Reorder working memory by relevance + expertise
    6. Output optimized focus state

    Args:
        project_id: Current project ID
        weight_by_expertise: Whether to weight by expertise (default: true)
        analyze_patterns: Whether to analyze patterns (default: true)

    Returns:
        Reordered working memory with expertise weighting
    """
    try:
        project_id = args.get("project_id")
        weight_by_expertise = args.get("weight_by_expertise", True)
        analyze_patterns = args.get("analyze_patterns", True)

        if not hasattr(server, '_attention_optimizer_optimizer'):
            from ..integration.agent_optimization import AttentionOptimizerOptimizer
            server._attention_optimizer_optimizer = AttentionOptimizerOptimizer(server.store.db)

        try:
            result = await server._attention_optimizer_optimizer.execute(
                project_id=project_id,
                weight_by_expertise=weight_by_expertise,
                analyze_patterns=analyze_patterns
            )
        except Exception as op_err:
            logger.error(f"Attention optimizer optimization error: {op_err}", exc_info=True)
            result = {
                "status": "error",
                "items_reordered": 0,
                "expertise_domains": 0
            }

        # Format response
        response = f"""**Optimized Attention-Optimizer Agent**
Status: {result.get('status', 'unknown')}

Expertise Weighting:
- Expertise Domains: {result.get('expertise_domains', 0)}
- High Confidence Domains: {result.get('high_confidence_count', 0)}
- Low Confidence Domains: {result.get('low_confidence_count', 0)}

Focus Reordering:
- Items Reordered: {result.get('items_reordered', 0)}
- Distractions Suppressed: {result.get('distractions_suppressed', 0)}
- Context Switches Reduced: {result.get('context_switches_reduced', 0)}

Pattern Analysis:
- Project Patterns Found: {result.get('project_patterns', 0)}
- Relevant Patterns: {result.get('relevant_patterns', 0)}

Working Memory Optimization:
- Capacity Used: {result.get('wm_capacity_used', 0)}/7
- Decay Rate: {result.get('decay_rate', 0):.2f}
- Optimization Applied: {result.get('optimization_applied', False)}

Top Focus Items:
- Item 1: {result.get('top_item_1', 'unknown')} (confidence: {result.get('confidence_1', 0):.2f})
- Item 2: {result.get('top_item_2', 'unknown')} (confidence: {result.get('confidence_2', 0):.2f})
- Item 3: {result.get('top_item_3', 'unknown')} (confidence: {result.get('confidence_3', 0):.2f})"""

        return [TextContent(type="text", text=response)]
    except Exception as e:
        logger.error(f"Error in handle_optimize_attention_optimizer: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]
