"""Skill Optimization handlers for Phase 3 (4 key skills enhanced with Phase 5-6 operations).

These handlers optimize 4 critical skills by integrating Phase 5-6 tools:
1. learning-tracker: Add pattern effectiveness tracking
2. procedure-suggester: Add pattern discovery for recommendations
3. gap-detector: Add pattern stability analysis
4. quality-monitor: Integrate advanced quality metrics
"""

import logging
from typing import Any, List

logger = logging.getLogger(__name__)


async def handle_optimize_learning_tracker(server: Any, args: dict) -> List[Any]:
    """Optimize learning-tracker skill: Add pattern effectiveness tracking.

    Enhances learning-tracker to measure which strategies work best by analyzing
    consolidation effectiveness across different trigger reasons and strategies.

    Args:
        server: MCP server instance
        args: {
            "project_id": int,
            "analyze_effectiveness": bool (default: True),
            "track_patterns": bool (default: True)
        }

    Returns:
        List with TextContent: Learning analysis with strategy recommendations
    """
    try:
        project_id = args.get("project_id", 1)
        analyze_effectiveness = args.get("analyze_effectiveness", True)
        track_patterns = args.get("track_patterns", True)

        if not hasattr(server, '_learning_tracker_optimizer'):
            from ..integration.skill_optimization import LearningTrackerOptimizer
            server._learning_tracker_optimizer = LearningTrackerOptimizer(server.store.db)

        result = await server._learning_tracker_optimizer.execute(
            project_id=project_id,
            analyze_effectiveness=analyze_effectiveness,
            track_patterns=track_patterns
        )

        # Format response
        from mcp.types import TextContent
        text = f"""Learning-Tracker Skill Optimization Results:
Status: {result.get('status')}
Strategy Effectiveness: {result.get('best_strategy')} ({result.get('effectiveness_score'):.2%})
Encoding Rounds Analyzed: {result.get('encoding_rounds')}
Patterns Extracted: {result.get('patterns_learned')}
Learning Curve Improvement: {result.get('learning_curve_improvement'):.1%}
Recommended Actions: {', '.join(result.get('recommendations', []))}
"""
        return [TextContent(type="text", text=text)]

    except Exception as e:
        logger.error(f"Learning tracker optimization failed: {e}", exc_info=True)
        from mcp.types import TextContent
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_optimize_procedure_suggester(server: Any, args: dict) -> List[Any]:
    """Optimize procedure-suggester skill: Add pattern discovery for recommendations.

    Enhances procedure-suggester to discover patterns from consolidation and recommend
    procedures based on project history and current context.

    Args:
        server: MCP server instance
        args: {
            "project_id": int,
            "analyze_patterns": bool (default: True),
            "discovery_depth": int (default: 3)
        }

    Returns:
        List with TextContent: Procedure recommendations with discovery insights
    """
    try:
        project_id = args.get("project_id", 1)
        analyze_patterns = args.get("analyze_patterns", True)
        discovery_depth = args.get("discovery_depth", 3)

        if not hasattr(server, '_procedure_suggester_optimizer'):
            from ..integration.skill_optimization import ProcedureSuggesterOptimizer
            server._procedure_suggester_optimizer = ProcedureSuggesterOptimizer(server.store.db)

        result = await server._procedure_suggester_optimizer.execute(
            project_id=project_id,
            analyze_patterns=analyze_patterns,
            discovery_depth=discovery_depth
        )

        # Format response
        from mcp.types import TextContent
        text = f"""Procedure-Suggester Skill Optimization Results:
Status: {result.get('status')}
Patterns Discovered: {result.get('patterns_discovered')}
Applicable Procedures: {result.get('procedures_recommended')}
Top Procedure: {result.get('top_procedure')} (confidence: {result.get('top_procedure_confidence'):.2%})
Discovery Depth: {result.get('discovery_depth')} levels analyzed
Pattern Stability: {result.get('pattern_stability_score'):.2%}
Usage Growth: {result.get('procedure_usage_growth'):.1%}
"""
        return [TextContent(type="text", text=text)]

    except Exception as e:
        logger.error(f"Procedure suggester optimization failed: {e}", exc_info=True)
        from mcp.types import TextContent
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_optimize_gap_detector(server: Any, args: dict) -> List[Any]:
    """Optimize gap-detector skill: Add pattern stability analysis.

    Enhances gap-detector to analyze pattern stability over time and identify
    contradictions that persist across consolidation cycles.

    Args:
        server: MCP server instance
        args: {
            "project_id": int,
            "stability_window": int (default: 7),
            "analyze_contradictions": bool (default: True)
        }

    Returns:
        List with TextContent: Gap analysis with stability metrics
    """
    try:
        project_id = args.get("project_id", 1)
        stability_window = args.get("stability_window", 7)
        analyze_contradictions = args.get("analyze_contradictions", True)

        if not hasattr(server, '_gap_detector_optimizer'):
            from ..integration.skill_optimization import GapDetectorOptimizer
            server._gap_detector_optimizer = GapDetectorOptimizer(server.store.db)

        result = await server._gap_detector_optimizer.execute(
            project_id=project_id,
            stability_window=stability_window,
            analyze_contradictions=analyze_contradictions
        )

        # Format response
        from mcp.types import TextContent
        text = f"""Gap-Detector Skill Optimization Results:
Status: {result.get('status')}
Gaps Detected: {result.get('gaps_detected')}
Critical Gaps: {result.get('critical_gaps')}
Pattern Stability Score: {result.get('pattern_stability_score'):.2%}
Stability Window: {result.get('stability_window')} days analyzed
Persistent Contradictions: {result.get('persistent_contradictions')}
Resolved Issues: {result.get('resolved_contradictions')}
Confidence Improvement: {result.get('confidence_improvement'):.1%}
"""
        return [TextContent(type="text", text=text)]

    except Exception as e:
        logger.error(f"Gap detector optimization failed: {e}", exc_info=True)
        from mcp.types import TextContent
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_optimize_quality_monitor(server: Any, args: dict) -> List[Any]:
    """Optimize quality-monitor skill: Integrate advanced quality metrics.

    Enhances quality-monitor to track advanced quality metrics including consolidation
    quality, layer health, and domain coverage across all memory layers.

    Args:
        server: MCP server instance
        args: {
            "project_id": int,
            "measure_layers": bool (default: True),
            "domain_analysis": bool (default: True)
        }

    Returns:
        List with TextContent: Quality report with advanced metrics
    """
    try:
        project_id = args.get("project_id", 1)
        measure_layers = args.get("measure_layers", True)
        domain_analysis = args.get("domain_analysis", True)

        if not hasattr(server, '_quality_monitor_optimizer'):
            from ..integration.skill_optimization import QualityMonitorOptimizer
            server._quality_monitor_optimizer = QualityMonitorOptimizer(server.store.db)

        result = await server._quality_monitor_optimizer.execute(
            project_id=project_id,
            measure_layers=measure_layers,
            domain_analysis=domain_analysis
        )

        # Format response
        from mcp.types import TextContent
        text = f"""Quality-Monitor Skill Optimization Results:
Status: {result.get('status')}
Overall Quality Score: {result.get('overall_quality_score'):.2%}
Consolidation Quality: {result.get('consolidation_quality'):.2%}
Layer Health: {result.get('layers_analyzed')} layers measured
Domain Coverage: {result.get('domains_covered')} domains
Quality Metrics:
  - Semantic Density: {result.get('semantic_density'):.2%}
  - Episodic Compression: {result.get('episodic_compression'):.2%}
  - Pattern Extraction: {result.get('pattern_extraction_rate'):.1%} per consolidation
  - Knowledge Gap Coverage: {result.get('gap_coverage'):.1%}
Quality Trend: {result.get('quality_trend')}
"""
        return [TextContent(type="text", text=text)]

    except Exception as e:
        logger.error(f"Quality monitor optimization failed: {e}", exc_info=True)
        from mcp.types import TextContent
        return [TextContent(type="text", text=f"Error: {str(e)}")]
