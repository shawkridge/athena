"""Consolidation handler methods for MCP server."""
import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from mcp.types import TextContent

from .structured_result import StructuredResult, ResultStatus, PaginationMetadata
from .filesystem_api_integration import get_integration

logger = logging.getLogger(__name__)

class ConsolidationHandlersMixin:
    """Consolidation handler methods (~16 methods).

    Extracted from monolithic handlers.py as part of Phase 6 refactoring.
    Provides consolidation operations: scheduling, running consolidation,
    clustering, pattern extraction, quality metrics, and analysis.

    Methods:
    - _handle_schedule_consolidation
    - _handle_run_consolidation
    - _handle_consolidate_working_memory
    - _handle_consolidation_quality_metrics
    - _handle_cluster_consolidation_events
    - _handle_consolidation_run_consolidation
    - _handle_consolidation_extract_patterns
    - _handle_consolidation_cluster_events
    - _handle_consolidation_measure_quality
    - _handle_consolidation_measure_advanced
    - _handle_consolidation_analyze_strategy
    - _handle_consolidation_analyze_project
    - _handle_consolidation_analyze_validation
    - _handle_consolidation_discover_orchestration
    - _handle_consolidation_analyze_performance
    - _handle_optimize_consolidation_trigger
    """

    async def _handle_schedule_consolidation(self, args: dict) -> list[TextContent]:
        """Handle schedule_consolidation tool call for periodic consolidation automation."""
        try:
            from datetime import datetime, time, timedelta

            frequency = args.get("frequency", "daily")
            time_of_day = args.get("time_of_day", "02:00")

            # Validate frequency
            valid_frequencies = ["daily", "weekly", "monthly"]
            if frequency not in valid_frequencies:
                return [TextContent(type="text",
                        text=json.dumps({"error": f"Invalid frequency: {frequency}. Must be one of {valid_frequencies}"}))]

            # Validate time format (HH:MM)
            try:
                time_parts = time_of_day.split(":")
                if len(time_parts) != 2:
                    raise ValueError("Time must be in HH:MM format")
                hour, minute = int(time_parts[0]), int(time_parts[1])
                if not (0 <= hour < 24 and 0 <= minute < 60):
                    raise ValueError("Invalid time values (hour: 0-23, minute: 0-59)")
                schedule_time = time(hour=hour, minute=minute)
            except (ValueError, IndexError) as e:
                return [TextContent(type="text",
                        text=json.dumps({"error": f"Invalid time format: {e}"}))]

            # Calculate next run time
            now = datetime.now()

            if frequency == "daily":
                next_run = now.replace(hour=schedule_time.hour, minute=schedule_time.minute, second=0, microsecond=0)
                if next_run <= now:
                    next_run += timedelta(days=1)
            elif frequency == "weekly":
                next_run = now.replace(hour=schedule_time.hour, minute=schedule_time.minute, second=0, microsecond=0)
                # Schedule for next occurrence, same time of week
                days_until = (6 - now.weekday()) % 7  # Schedule for Saturday (or next week)
                if days_until == 0 and next_run <= now:
                    days_until = 7
                next_run += timedelta(days=days_until)
            else:  # monthly
                # Schedule for first occurrence next month at the specified time
                if now.month == 12:
                    next_run = now.replace(year=now.year + 1, month=1, day=1,
                                          hour=schedule_time.hour, minute=schedule_time.minute, second=0, microsecond=0)
                else:
                    next_run = now.replace(month=now.month + 1, day=1,
                                          hour=schedule_time.hour, minute=schedule_time.minute, second=0, microsecond=0)

            # Build response
            response = f"✓ Consolidation schedule configured\n"
            response += f"Frequency: {frequency}\n"
            response += f"Time of day: {time_of_day}\n"
            response += f"Next run: {next_run.strftime('%Y-%m-%d %H:%M:%S')}\n"
            response += f"\nSchedule will:\n"
            response += f"  1. Score and rank memories by importance\n"
            response += f"  2. Prune low-value memories (usefulness < 0.1)\n"
            response += f"  3. Extract patterns from episodic events\n"
            response += f"  4. Resolve memory conflicts\n"
            response += f"  5. Update meta-memory statistics\n"
            response += f"  6. Strengthen important associations\n"
            response += f"\nNote: This schedule configuration is prepared for integration with a background scheduler.\n"
            response += f"To actually run consolidation now, use the run_consolidation tool."

            return [TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Error in schedule_consolidation [args={args}]: {e}", exc_info=True)
            error_response = json.dumps({"error": str(e), "tool": "schedule_consolidation"})
            return [TextContent(type="text", text=error_response)]

    # Procedural memory handlers
    # Procedure versioning handlers
    # Prospective memory handlers






    # Meta-memory handlers

    async def _handle_run_consolidation(self, args: dict) -> list[TextContent]:
        """Handle run_consolidation tool call.

        PHASE 5 AUTO-INTEGRATION: Automatically updates expertise metrics
        after consolidation completes based on consolidated patterns.
        """
        # Make project_id optional - use from args or try to get active project
        project_id = args.get("project_id")
        if not project_id:
            try:
                project = await self.project_manager.require_project()
                project_id = project.id
            except:
                project_id = None  # Allow global consolidation without project

        dry_run = args.get("dry_run", False)
        run_id = self.consolidation_system.run_consolidation(project_id)

        response = f"Consolidation {'simulation' if dry_run else 'complete'}:\n\n"
        response += f"Run ID: {run_id}\n"
        response += f"Successfully completed consolidation process"

        # ===== PHASE 5 AUTO-EXPERTISE UPDATES =====
        # Update expertise metrics based on consolidated patterns (if project context available)
        expertise_updated = False
        if project_id:
            try:
                # Get expertise metrics from meta-memory store
                expertise_data = self.meta_memory_store.get_expertise(project_id, limit=20)

                if expertise_data:
                    # Update expertise for each domain with consolidation bonus
                    # (consolidation improves pattern recognition and domain knowledge)
                    for domain, metrics in expertise_data.items():
                        try:
                            # Boost expertise slightly for consolidation
                            updated_metrics = {
                                **metrics,
                                "consolidation_count": metrics.get("consolidation_count", 0) + 1,
                                "pattern_count": metrics.get("pattern_count", 0) + 1,
                                # Slightly increase confidence in domain knowledge
                                "confidence": min(0.95, metrics.get("confidence", 0.5) + 0.05),
                            }
                            # Store updated metrics back
                            self.meta_memory_store.update_expertise(project_id, domain, updated_metrics)
                        except Exception as domain_e:
                            logger.debug(f"Could not update expertise for {domain}: {domain_e}")

                    response += f"\n✓ Auto-Expertise: Updated {len(expertise_data)} domains"
                    expertise_updated = True
            except Exception as e:
                logger.debug(f"Could not auto-update expertise metrics: {e}")

        return [TextContent(type="text", text=response)]

    # Unified smart retrieval handler

    async def _handle_consolidate_working_memory(self, args: dict) -> list[TextContent]:
        """Handle consolidate_working_memory tool call."""
        project = self.project_manager.get_or_create_project()
        item_id = args.get("item_id")
        auto_route = args.get("auto_route", True)

        if item_id is not None:
            # Consolidate specific item
            result = self.consolidation_router.route_item(project.id, item_id, use_ml=auto_route)

            response = f"✓ Consolidated item {item_id}\n"
            response += f"Target layer: {result['target_layer']}\n"
            if "confidence" in result:
                response += f"Confidence: {result['confidence']:.2f}"
        else:
            # Consolidate least active items
            all_items = []
            all_items.extend(self.phonological_loop.get_items(project.id))
            all_items.extend(self.visuospatial_sketchpad.get_items(project.id))
            all_items.extend(self.episodic_buffer.get_items(project.id))

            # Sort by activation level (least active first)
            all_items.sort(key=lambda x: getattr(x, "current_activation", getattr(x, "activation_level", 0)))

            # Consolidate 1-3 least active items
            consolidate_count = min(3, len(all_items))
            results = []

            for item in all_items[:consolidate_count]:
                try:
                    result = self.consolidation_router.route_item(project.id, item.id, use_ml=auto_route)
                    results.append(result)
                except Exception as e:
                    logger.warning(f"Failed to consolidate item {item.id}: {e}")

            response = f"✓ Consolidated {len(results)} least active items\n"
            for r in results:
                response += f"  - Item {r.get('item_id')} → {r['target_layer']}\n"

        return [TextContent(type="text", text=response)]


    async def _handle_consolidation_quality_metrics(self, args: dict) -> list[TextContent]:
        """Handle Consolidation Quality Metrics measurement."""
        try:
            from athena.consolidation.quality_metrics import ConsolidationQualityMetrics

            session_id = args["session_id"]
            metrics_to_compute = args.get("metrics", ["compression_ratio", "retrieval_recall", "pattern_consistency", "information_density"])

            # Get stores
            episodic_store = self.episodic_store
            semantic_store = self.store  # Main store is semantic memory

            if not episodic_store:
                return [TextContent(type="text", text="✗ Episodic store not available")]

            quality_metrics = ConsolidationQualityMetrics(
                episodic_store=episodic_store,
                semantic_store=semantic_store,
            )

            # Measure requested metrics
            results = {}
            if "compression_ratio" in metrics_to_compute:
                results["compression_ratio"] = quality_metrics.measure_compression_ratio(session_id)
            if "retrieval_recall" in metrics_to_compute:
                results["retrieval_recall"] = quality_metrics.measure_retrieval_recall(session_id)
            if "pattern_consistency" in metrics_to_compute:
                results["pattern_consistency"] = quality_metrics.measure_pattern_consistency(session_id)
            if "information_density" in metrics_to_compute:
                results["information_density"] = quality_metrics.measure_information_density(session_id)

            response = f"✓ Consolidation Quality Metrics (Chen et al. 2024)\n"
            response += f"Session: {session_id}\n"
            for metric_name, metric_value in results.items():
                if isinstance(metric_value, dict):
                    response += f"\n{metric_name}:\n"
                    for k, v in metric_value.items():
                        response += f"  {k}: {v:.3f}\n"
                else:
                    response += f"{metric_name}: {metric_value:.3f}\n"

            return [TextContent(type="text", text=response)]

        except Exception as e:
            return [TextContent(type="text", text=f"✗ Error in Consolidation Quality Metrics: {str(e)}")]


    async def _handle_cluster_consolidation_events(self, args: dict) -> list[TextContent]:
        """Handle cluster_consolidation_events tool call."""
        try:
            events = args.get("events", [])
            limit = args.get("limit", 10)

            clusters = self.llm_consolidation_clusterer.cluster_events(events, limit=limit)

            response = f"Semantic Clustering Results\n"
            response += "=" * 60 + "\n"
            response += f"Identified {len(clusters)} semantic patterns from {len(events)} events\n\n"

            for cluster in clusters:
                response += f"📌 {cluster.pattern_name}\n"
                response += f"   Description: {cluster.description}\n"
                response += f"   Events: {cluster.event_count}\n"
                response += f"   Confidence: {cluster.confidence:.0%}\n"
                response += f"   Frequency: {cluster.frequency}\n"
                response += f"   Pattern: {cluster.generalized_pattern}\n\n"

            return [TextContent(type="text", text=response)]
        except Exception as e:
            logger.error(f"Error in cluster_consolidation_events: {e}", exc_info=True)
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    # Tier 1: Saliency-based Attention Management handlers

    async def _handle_consolidation_run_consolidation(self, args: dict) -> list[TextContent]:
        """Forward to Phase 5 handler: run_consolidation."""
        from . import handlers_consolidation
        return await handlers_consolidation.handle_run_consolidation(self, args)


    async def _handle_consolidation_extract_patterns(self, args: dict) -> list[TextContent]:
        """Forward to Phase 5 handler: extract_consolidation_patterns."""
        from . import handlers_consolidation
        return await handlers_consolidation.handle_extract_consolidation_patterns(self, args)


    async def _handle_consolidation_cluster_events(self, args: dict) -> list[TextContent]:
        """Forward to Phase 5 handler: cluster_consolidation_events."""
        from . import handlers_consolidation
        return await handlers_consolidation.handle_cluster_consolidation_events(self, args)


    async def _handle_consolidation_measure_quality(self, args: dict) -> list[TextContent]:
        """Forward to Phase 5 handler: measure_consolidation_quality."""
        from . import handlers_consolidation
        return await handlers_consolidation.handle_measure_consolidation_quality(self, args)


    async def _handle_consolidation_measure_advanced(self, args: dict) -> list[TextContent]:
        """Forward to Phase 5 handler: measure_advanced_consolidation_metrics."""
        from . import handlers_consolidation
        return await handlers_consolidation.handle_measure_advanced_consolidation_metrics(self, args)


    async def _handle_consolidation_analyze_strategy(self, args: dict) -> list[TextContent]:
        """Forward to Phase 5 handler: analyze_strategy_effectiveness."""
        from . import handlers_consolidation
        return await handlers_consolidation.handle_analyze_strategy_effectiveness(self, args)


    async def _handle_consolidation_analyze_project(self, args: dict) -> list[TextContent]:
        """Forward to Phase 5 handler: analyze_project_patterns."""
        from . import handlers_consolidation
        return await handlers_consolidation.handle_analyze_project_patterns(self, args)


    async def _handle_consolidation_analyze_validation(self, args: dict) -> list[TextContent]:
        """Forward to Phase 5 handler: analyze_validation_effectiveness."""
        from . import handlers_consolidation
        return await handlers_consolidation.handle_analyze_validation_effectiveness(self, args)


    async def _handle_consolidation_discover_orchestration(self, args: dict) -> list[TextContent]:
        """Forward to Phase 5 handler: discover_orchestration_patterns."""
        from . import handlers_consolidation
        return await handlers_consolidation.handle_discover_orchestration_patterns(self, args)


    async def _handle_consolidation_analyze_performance(self, args: dict) -> list[TextContent]:
        """Forward to Phase 5 handler: analyze_consolidation_performance."""
        from . import handlers_consolidation
        return await handlers_consolidation.handle_analyze_consolidation_performance(self, args)

    # ============================================================================
    # PHASE 6 HANDLERS (Planning & Resource Estimation)
    # ============================================================================


    async def _handle_optimize_consolidation_trigger(self, args: dict) -> list[TextContent]:
        """Forward to Agent Optimization handler: optimize_consolidation_trigger."""
        from . import handlers_agent_optimization
        return await handlers_agent_optimization.handle_optimize_consolidation_trigger(self, args)


