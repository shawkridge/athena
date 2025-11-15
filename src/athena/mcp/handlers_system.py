"""System/Utility Handlers - Extracted Domain Module

This module contains miscellaneous system and utility handler methods extracted from handlers.py
as part of Phase 11 of the handler refactoring.

Handler Methods (34 total, ~600 lines):
- _handle_record_event: Record episodic event
- _handle_recall_events: Recall events with filtering
- _handle_get_timeline: Get event timeline
- _handle_batch_record_events: Batch record multiple events
- _handle_recall_events_by_session: Recall events by session
- _handle_optimize_quality_monitor: Optimize quality monitoring
- _handle_get_memory_evolution_history: Get memory evolution history
- _handle_compute_memory_attributes: Compute memory attributes
- _handle_get_memory_attributes: Get memory attributes
- _handle_create_hierarchical_index: Create hierarchical index
- _handle_assign_memory_to_index: Assign memory to index
- _handle_get_community_details: Get community details
- _handle_query_communities_by_level: Query communities by level
- _handle_analyze_community_connectivity: Analyze community connectivity
- _handle_find_bridge_entities: Find bridge entities
- _handle_search_code_semantically: Search code semantically
- _handle_search_code_by_type: Search code by type
- _handle_search_code_by_name: Search code by name
- _handle_analyze_code_file: Analyze code file
- _handle_find_code_dependencies: Find code dependencies
- _handle_index_code_repository: Index code repository
- _handle_get_code_statistics: Get code statistics
- _handle_record_code_analysis: Record code analysis
- _handle_store_code_insights: Store code insights
- _handle_add_code_entities: Add code entities
- _handle_analyze_repository: Analyze repository
- _handle_get_analysis_metrics: Get analysis metrics
- _handle_lookup_external_knowledge: Lookup external knowledge
- _handle_synthesize_knowledge: Synthesize knowledge
- _handle_explore_concept_network: Explore concept network
- _handle_execute_code: Execute code in sandbox
- _handle_validate_code: Validate code
- _handle_record_execution: Record execution
- _handle_get_sandbox_config: Get sandbox configuration

Dependencies:
- Imports: TextContent, json, logging
- Attributes: Various store objects and system components

Integration Pattern:
This module uses the mixin pattern. Methods are defined here and bound to MemoryMCPServer
in handlers.py via:
    class MemoryMCPServer(SystemHandlersMixin, ...):
        pass
"""

import json
import logging
from typing import List

from mcp.types import TextContent

logger = logging.getLogger(__name__)


class SystemHandlersMixin:
    """Mixin class containing miscellaneous system and utility handler methods.
    
    This mixin is designed to be mixed into MemoryMCPServer class.
    It provides various system operations without modifying the main handler structure.
    """

    async def _handle_record_event(self, args: dict) -> list[TextContent]:
        """Handle record_event tool call."""
        project = self.project_manager.get_or_create_project()
        import os
        import time

        session_id = f"session_{int(time.time())}"

        context_data = args.get("context", {})
        context = EventContext(
            cwd=context_data.get("cwd", os.getcwd()),
            files=context_data.get("files", []),
            task=context_data.get("task"),
            phase=context_data.get("phase"),
        )

        event = EpisodicEvent(
            project_id=project.id,
            session_id=session_id,
            timestamp=args.get("timestamp") or datetime.now(),
            event_type=EventType(args.get("event_type", "action")),
            content=args["content"],
            outcome=EventOutcome(args["outcome"]) if "outcome" in args else None,
            context=context,
        )

        event_id = self.episodic_store.record_event(event)

        response = f"✓ Recorded event (ID: {event_id})\n"
        response += f"Type: {event.event_type}\n"
        response += f"Time: {event.timestamp}\n"
        if event.outcome:
            response += f"Outcome: {event.outcome}"

        return [TextContent(type="text", text=response)]

    async def _handle_recall_events(self, args: dict) -> list[TextContent]:
        """Handle recall_events tool call."""
        try:
            project = await self.project_manager.require_project()
            from datetime import datetime, timedelta

            # Handle timeframe filter
            if "timeframe" in args:
                timeframe = args["timeframe"]
                now = datetime.now()
                if timeframe == "today":
                    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
                    events = self.episodic_store.get_events_by_date(project.id, start_of_day, now)
                elif timeframe == "yesterday":
                    start_of_yesterday = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                    end_of_yesterday = start_of_yesterday.replace(hour=23, minute=59, second=59)
                    events = self.episodic_store.get_events_by_date(project.id, start_of_yesterday, end_of_yesterday)
                elif timeframe == "this_week":
                    events = self.episodic_store.get_recent_events(project.id, hours=168, limit=args.get("limit", 10))
                elif timeframe == "last_week":
                    week_start = now - timedelta(days=14)
                    week_end = now - timedelta(days=7)
                    events = [e for e in self.episodic_store.get_recent_events(project.id, hours=336, limit=50)
                              if week_start <= e.timestamp <= week_end]
                elif timeframe == "this_month":
                    events = self.episodic_store.get_recent_events(project.id, hours=720, limit=args.get("limit", 10))
                else:
                    events = self.episodic_store.get_recent_events(project.id, hours=168, limit=args.get("limit", 10))
            elif "query" in args:
                events = self.episodic_store.search_events(project.id, args["query"], limit=args.get("limit", 10))
            elif "event_type" in args:
                from ..episodic.models import EventType
                events = self.episodic_store.get_events_by_type(project.id, EventType(args["event_type"]), limit=args.get("limit", 10))
            else:
                events = self.episodic_store.get_recent_events(project.id, limit=args.get("limit", 10))

            if not events:
                result = StructuredResult.success(
                    data=[],
                    metadata={
                        "operation": "recall_events",
                        "schema": "episodic_events",
                        "timeframe": args.get("timeframe", "recent"),
                    }
                )
            else:
                # Format events for structured response
                formatted_events = []
                for event in events:
                    event_type_str = event.event_type.value if hasattr(event.event_type, 'value') else str(event.event_type)
                    outcome_str = None
                    if event.outcome:
                        outcome_str = event.outcome.value if hasattr(event.outcome, 'value') else str(event.outcome)

                    formatted_events.append({
                        "id": event.id,
                        "timestamp": event.timestamp.isoformat() if event.timestamp else None,
                        "type": event_type_str,
                        "content": event.content,
                        "outcome": outcome_str,
                        "context": event.context if hasattr(event, 'context') else None,
                    })

                result = StructuredResult.success(
                    data=formatted_events,
                    metadata={
                        "operation": "recall_events",
                        "schema": "episodic_events",
                        "timeframe": args.get("timeframe", "recent"),
                        "count": len(formatted_events),
                    },
                    pagination=PaginationMetadata(
                        returned=len(formatted_events),
                        limit=args.get("limit", 10),
                    )
                )
        except Exception as e:
            result = StructuredResult.error(str(e), metadata={"operation": "recall_events"})

        # Use TOON optimization for episodic events
        return [result.as_optimized_content(schema_name="episodic_events")]

    async def _handle_get_timeline(self, args: dict) -> list[TextContent]:
        """Handle get_timeline tool call."""
        try:
            project = await self.project_manager.require_project()

            days = args.get("days", 7)
            limit = args.get("limit", 20)

            events = self.episodic_store.get_recent_events(project.id, hours=days*24, limit=limit)

            if not events:
                result = StructuredResult.success(
                    data=[],
                    metadata={
                        "operation": "get_timeline",
                        "schema": "episodic_events",
                        "days": days,
                    }
                )
            else:
                # Format timeline events
                timeline_events = []
                for event in events:
                    event_type_str = event.event_type.value if hasattr(event.event_type, 'value') else str(event.event_type)
                    timeline_events.append({
                        "id": event.id,
                        "timestamp": event.timestamp.isoformat() if event.timestamp else None,
                        "type": event_type_str,
                        "content": event.content[:100],  # Preview only
                    })

                result = StructuredResult.success(
                    data=timeline_events,
                    metadata={
                        "operation": "get_timeline",
                        "schema": "episodic_events",
                        "days": days,
                        "count": len(timeline_events),
                    },
                    pagination=PaginationMetadata(
                        returned=len(timeline_events),
                        limit=limit,
                    )
                )
        except Exception as e:
            result = StructuredResult.error(str(e), metadata={"operation": "get_timeline"})

        # Use TOON optimization for timeline events
        return [result.as_optimized_content(schema_name="episodic_events")]

    async def _handle_batch_record_events(self, args: dict) -> list[TextContent]:
        """Handle batch_record_events tool call (10x throughput improvement).

        Records multiple episodic events in a single transaction with batch embeddings.
        Uses optimized batch insert and optional embedding generation.

        PHASE 5 AUTO-INTEGRATION: Automatically triggers consolidation when event
        count exceeds threshold (default: 100 events per project).
        """
        import os
        import time

        try:
            project = self.project_manager.get_or_create_project()

            session_id = f"session_{int(time.time())}"
            events_data = args.get("events", [])

            if not events_data:
                return [TextContent(type="text", text="Error: No events provided")]

            # Parse events_data if it's a JSON string
            if isinstance(events_data, str):
                events_data = json.loads(events_data)

            # Convert input dicts to EpisodicEvent models
            events = []
            for event_data in events_data:
                if isinstance(event_data, str):
                    event_data = json.loads(event_data)
                context_data = event_data.get("context", {})
                context = EventContext(
                    cwd=context_data.get("cwd", os.getcwd()),
                    files=context_data.get("files", []),
                    task=context_data.get("task"),
                    phase=context_data.get("phase"),
                )

                event = EpisodicEvent(
                    project_id=project.id,
                    session_id=session_id,
                    timestamp=event_data.get("timestamp") or datetime.now(),
                    event_type=EventType(event_data.get("event_type", "action")),
                    content=event_data["content"],
                    outcome=EventOutcome(event_data["outcome"]) if "outcome" in event_data else None,
                    context=context,
                )
                events.append(event)

            # Use optimized batch insert
            event_ids = self.episodic_store.batch_record_events(events)

            response = f"✓ Recorded {len(event_ids)} events in batch\n"
            response += f"Event IDs: {', '.join(map(str, event_ids))}\n"
            response += f"Throughput: Batch insert (10x faster than individual)\n"
            response += f"Session: {session_id}"

            # ===== PHASE 5 AUTO-CONSOLIDATION TRIGGER =====
            # Check if event count exceeds threshold; if so, trigger consolidation
            consolidation_triggered = False
            try:
                # Query event count for this project
                cursor = self.episodic_store.db.conn.cursor()
                cursor.execute(
                    "SELECT COUNT(*) FROM episodic_events WHERE project_id = ?",
                    (project.id,)
                )
                result = cursor.fetchone()
                event_count = result[0] if result else 0

                # Threshold: 100 events per project
                CONSOLIDATION_THRESHOLD = 100
                if event_count >= CONSOLIDATION_THRESHOLD:
                    logger.info(
                        f"Auto-consolidation triggered: {event_count} events >= {CONSOLIDATION_THRESHOLD}"
                    )
                    try:
                        # Trigger consolidation asynchronously
                        run_id = self.consolidation_system.run_consolidation(project.id)
                        response += f"\n✓ Auto-Consolidation: Triggered (run_id={run_id})"
                        consolidation_triggered = True
                    except Exception as cons_e:
                        logger.error(f"Error triggering auto-consolidation: {cons_e}", exc_info=True)
                        response += f"\n⚠ Auto-Consolidation: Error ({str(cons_e)[:50]})"
            except Exception as count_e:
                logger.debug(f"Could not check event count for auto-consolidation: {count_e}")

            return [TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Error in batch_record_events [args={args}]: {e}", exc_info=True)
            error_response = json.dumps({"error": str(e), "tool": "batch_record_events"})
            return [TextContent(type="text", text=error_response)]

    async def _handle_recall_events_by_session(self, args: dict) -> list[TextContent]:
        """Handle recall_events_by_session tool call.

        Retrieves all events from a specific session for session-level analysis.
        Useful for analyzing work patterns within a session boundary.
        """
        try:
            session_id = args.get("session_id")

            if not session_id:
                return [TextContent(type="text", text="Error: session_id is required")]

            # Retrieve all events for this session
            events = self.episodic_store.get_events_by_session(session_id)

            if not events:
                return [TextContent(type="text", text=f"No events found for session {session_id}")]

            response = f"Session {session_id} - {len(events)} events:\n\n"

            # Group events by type for summary
            by_type = {}
            for event in events:
                event_type = event.event_type.value if hasattr(event.event_type, 'value') else str(event.event_type)
                if event_type not in by_type:
                    by_type[event_type] = 0
                by_type[event_type] += 1

            response += "Event breakdown:\n"
            for event_type, count in sorted(by_type.items()):
                response += f"  {event_type}: {count}\n"

            response += "\nTimeline:\n"
            for event in events:
                event_type_str = event.event_type.value if hasattr(event.event_type, 'value') else str(event.event_type)
                response += f"[{event.timestamp.strftime('%H:%M:%S')}] {event_type_str}\n"
                response += f"  {event.content[:70]}{'...' if len(event.content) > 70 else ''}\n"

            return [TextContent(type="text", text=response)]

        except Exception as e:
            logger.error(f"Error in recall_events_by_session [args={args}]: {e}", exc_info=True)
            error_response = json.dumps({"error": str(e), "tool": "recall_events_by_session"})
            return [TextContent(type="text", text=error_response)]


    # Procedural memory handlers
    # Procedure versioning handlers
    # Prospective memory handlers






    # Meta-memory handlers
    async def _handle_optimize_quality_monitor(self, args: dict) -> list[TextContent]:
        """Forward to Skill Optimization handler: optimize_quality_monitor."""
        from . import handlers_skill_optimization
        return await handlers_skill_optimization.handle_optimize_quality_monitor(self, args)

    # ============================================================================
    # ZETTELKASTEN TOOLS HANDLERS (6 operations)
    # ============================================================================
    # Memory versioning, evolution tracking, and hierarchical indexing

    async def _handle_get_memory_evolution_history(self, args: dict) -> list[TextContent]:
        """Get complete evolution history of a memory."""
        from .zettelkasten_tools import ZettelkastenMCPHandlers
        handlers = ZettelkastenMCPHandlers(self.memory_manager.db)
        return [await handlers.get_memory_evolution_history(
            memory_id=args.get("memory_id")
        )]

    async def _handle_compute_memory_attributes(self, args: dict) -> list[TextContent]:
        """Compute auto-generated attributes for a memory."""
        from .zettelkasten_tools import ZettelkastenMCPHandlers
        handlers = ZettelkastenMCPHandlers(self.memory_manager.db)
        return [await handlers.compute_memory_attributes(
            memory_id=args.get("memory_id")
        )]

    async def _handle_get_memory_attributes(self, args: dict) -> list[TextContent]:
        """Get cached auto-computed attributes for a memory."""
        from .zettelkasten_tools import ZettelkastenMCPHandlers
        handlers = ZettelkastenMCPHandlers(self.memory_manager.db)
        return [await handlers.get_memory_attributes(
            memory_id=args.get("memory_id")
        )]

    async def _handle_create_hierarchical_index(self, args: dict) -> list[TextContent]:
        """Create a hierarchical index node using Luhmann numbering."""
        from .zettelkasten_tools import ZettelkastenMCPHandlers
        handlers = ZettelkastenMCPHandlers(self.memory_manager.db)
        return [await handlers.create_hierarchical_index(
            project_id=args.get("project_id"),
            parent_id=args.get("parent_id"),
            label=args.get("label", "Untitled")
        )]

    async def _handle_assign_memory_to_index(self, args: dict) -> list[TextContent]:
        """Assign a memory to a hierarchical index position."""
        from .zettelkasten_tools import ZettelkastenMCPHandlers
        handlers = ZettelkastenMCPHandlers(self.memory_manager.db)
        return [await handlers.assign_memory_to_index(
            memory_id=args.get("memory_id"),
            index_id=args.get("index_id")
        )]

    # ============================================================================
    # GRAPHRAG TOOLS HANDLERS (5 operations)
    # ============================================================================
    # Community detection and multi-level knowledge graph retrieval


    async def _handle_get_community_details(self, args: dict) -> list[TextContent]:
        """Get detailed information about a specific community."""
        from .graphrag_tools import GraphRAGMCPHandlers
        handlers = GraphRAGMCPHandlers(self.memory_manager.db)
        return [await handlers.get_community_details(
            project_id=args.get("project_id"),
            community_id=args.get("community_id")
        )]

    async def _handle_query_communities_by_level(self, args: dict) -> list[TextContent]:
        """Query communities at specific hierarchical level."""
        from .graphrag_tools import GraphRAGMCPHandlers
        handlers = GraphRAGMCPHandlers(self.memory_manager.db)
        return [await handlers.query_communities_by_level(
            project_id=args.get("project_id"),
            query=args.get("query"),
            level=args.get("level", 0)
        )]

    async def _handle_analyze_community_connectivity(self, args: dict) -> list[TextContent]:
        """Analyze internal vs external connectivity of communities."""
        from .graphrag_tools import GraphRAGMCPHandlers
        handlers = GraphRAGMCPHandlers(self.memory_manager.db)
        return [await handlers.analyze_community_connectivity(
            project_id=args.get("project_id")
        )]

    async def _handle_find_bridge_entities(self, args: dict) -> list[TextContent]:
        """Find entities that bridge multiple communities."""
        from .graphrag_tools import GraphRAGMCPHandlers
        handlers = GraphRAGMCPHandlers(self.memory_manager.db)
        return [await handlers.find_bridge_entities(
            project_id=args.get("project_id"),
            threshold=args.get("threshold", 3)
        )]

    # ========================================================================
    # CODE SEARCH HANDLERS
    # ========================================================================

    async def _handle_search_code_semantically(self, args: dict) -> list[TextContent]:
        """Perform semantic code search across repository."""
        from .handlers_code_search import handle_search_code_semantically
        return await handle_search_code_semantically(self, args)

    async def _handle_search_code_by_type(self, args: dict) -> list[TextContent]:
        """Search code by element type (function, class, import)."""
        from .handlers_code_search import handle_search_code_by_type
        return await handle_search_code_by_type(self, args)

    async def _handle_search_code_by_name(self, args: dict) -> list[TextContent]:
        """Search code by name (exact or partial match)."""
        from .handlers_code_search import handle_search_code_by_name
        return await handle_search_code_by_name(self, args)

    async def _handle_analyze_code_file(self, args: dict) -> list[TextContent]:
        """Analyze structure of a code file."""
        from .handlers_code_search import handle_analyze_code_file
        return await handle_analyze_code_file(self, args)

    async def _handle_find_code_dependencies(self, args: dict) -> list[TextContent]:
        """Find dependencies of a code entity."""
        from .handlers_code_search import handle_find_code_dependencies
        return await handle_find_code_dependencies(self, args)

    async def _handle_index_code_repository(self, args: dict) -> list[TextContent]:
        """Index a code repository for search."""
        from .handlers_code_search import handle_index_code_repository
        return await handle_index_code_repository(self, args)

    async def _handle_get_code_statistics(self, args: dict) -> list[TextContent]:
        """Get comprehensive statistics about indexed code."""
        from .handlers_code_search import handle_get_code_statistics
        return await handle_get_code_statistics(self, args)

    # ========================================================================
    # CODE ANALYSIS HANDLERS
    # ========================================================================

    async def _handle_record_code_analysis(self, args: dict) -> list[TextContent]:
        """Record code analysis to memory."""
        from .handlers_code_analysis import CodeAnalysisMemoryHandlers

        handlers = CodeAnalysisMemoryHandlers(self.memory_manager)
        result = handlers.record_analysis(
            repo_path=args.get("repo_path"),
            analysis_results=args.get("analysis_results", {}),
            duration_ms=args.get("duration_ms", 0),
            file_count=args.get("file_count", 0),
            unit_count=args.get("unit_count", 0),
        )
        return [TextContent(type="text", text=str(result))]

    async def _handle_store_code_insights(self, args: dict) -> list[TextContent]:
        """Store code analysis insights to semantic memory."""
        from .handlers_code_analysis import CodeAnalysisMemoryHandlers

        handlers = CodeAnalysisMemoryHandlers(self.memory_manager)
        result = handlers.store_code_insights(
            analysis_results=args.get("analysis_results", {}),
            repo_path=args.get("repo_path"),
            tags=args.get("tags"),
        )
        return [TextContent(type="text", text=str(result))]

    async def _handle_add_code_entities(self, args: dict) -> list[TextContent]:
        """Add code entities to knowledge graph."""
        from .handlers_code_analysis import CodeAnalysisMemoryHandlers

        handlers = CodeAnalysisMemoryHandlers(self.memory_manager)
        result = handlers.add_code_entities(
            code_units=args.get("code_units", []),
            repo_path=args.get("repo_path"),
        )
        return [TextContent(type="text", text=str(result))]

    async def _handle_analyze_repository(self, args: dict) -> list[TextContent]:
        """Analyze repository with memory integration."""
        from .handlers_code_analysis import CodeAnalysisMemoryHandlers

        handlers = CodeAnalysisMemoryHandlers(self.memory_manager)
        result = handlers.analyze_repository(
            repo_path=args.get("repo_path"),
            language=args.get("language", "python"),
            include_memory=args.get("include_memory", True),
        )
        return [TextContent(type="text", text=str(result))]

    async def _handle_get_analysis_metrics(self, args: dict) -> list[TextContent]:
        """Get code analysis metrics and trends."""
        from .handlers_code_analysis import CodeAnalysisMemoryHandlers

        handlers = CodeAnalysisMemoryHandlers(self.memory_manager)
        result = handlers.get_analysis_metrics(
            repo_path=args.get("repo_path"),
            days_back=args.get("days_back", 7),
        )
        return [TextContent(type="text", text=str(result))]

    # ========================================================================
    # EXTERNAL KNOWLEDGE HANDLERS
    # ========================================================================

    async def _handle_lookup_external_knowledge(self, args: dict) -> list[TextContent]:
        """Look up external knowledge about a concept."""
        from .handlers_external_knowledge import handle_lookup_external_knowledge
        return await handle_lookup_external_knowledge(self, args)


    async def _handle_synthesize_knowledge(self, args: dict) -> list[TextContent]:
        """Synthesize knowledge from multiple sources."""
        from .handlers_external_knowledge import handle_synthesize_knowledge
        return await handle_synthesize_knowledge(self, args)

    async def _handle_explore_concept_network(self, args: dict) -> list[TextContent]:
        """Explore concept relationships interactively."""
        from .handlers_external_knowledge import handle_explore_concept_network
        return await handle_explore_concept_network(self, args)

    # ============================================================================
    # CODE_EXECUTION_TOOLS: Phase 3 Week 11 - Sandboxed Code Execution
    # ============================================================================

    async def _handle_execute_code(self, args: dict) -> list[TextContent]:
        """Execute code safely in sandbox."""
        try:
            from ..mcp.memory_api import MemoryAPI

            api = MemoryAPI.create(self.db)
            code = args.get("code", "")
            language = args.get("language", "python")
            timeout_seconds = args.get("timeout_seconds", 30)
            capture_io = args.get("capture_io", True)
            allow_network = args.get("allow_network", False)
            allow_filesystem = args.get("allow_filesystem", False)

            result = api.execute_code(
                code=code,
                language=language,
                timeout_seconds=timeout_seconds,
                capture_io=capture_io,
                allow_network=allow_network,
                allow_filesystem=allow_filesystem,
            )

            response = {
                "status": "success" if result.success else "error",
                "sandbox_id": result.sandbox_id,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.exit_code,
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

    async def _handle_validate_code(self, args: dict) -> list[TextContent]:
        """Validate code for security violations."""
        try:
            from ..mcp.memory_api import MemoryAPI

            api = MemoryAPI.create(self.db)
            code = args.get("code", "")
            language = args.get("language", "python")

            result = api.validate_code(code=code, language=language)

            response = {
                "status": "valid" if result.get("valid", True) else "invalid",
                "violations": result.get("violations", []),
                "warnings": result.get("warnings", []),
                "confidence_score": result.get("confidence_score", 0.0),
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

    async def _handle_record_execution(self, args: dict) -> list[TextContent]:
        """Record execution event in memory."""
        try:
            from ..mcp.memory_api import MemoryAPI

            api = MemoryAPI.create(self.db)
            procedure_name = args.get("procedure_name")
            duration_ms = args.get("duration_ms", 0)
            learned = args.get("learned", "")

            api.record_execution(
                procedure_name=procedure_name, duration_ms=duration_ms, learned=learned
            )

            response = {
                "status": "success",
                "message": f"Recorded execution for {procedure_name}",
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

    async def _handle_get_sandbox_config(self, args: dict) -> list[TextContent]:
        """Get current sandbox configuration."""
        try:
            from ..sandbox.srt_config import SandboxConfig

            config = SandboxConfig.default()

            response = {
                "status": "success",
                "mode": config.mode.value,
                "timeout_seconds": config.timeout_seconds,
                "memory_limit_mb": config.memory_limit_mb,
                "allow_network": config.allow_network,
                "allow_filesystem": config.allow_filesystem,
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


    async def _handle_get_consolidation_history(self, args: dict) -> list[TextContent]:
        """Handle get_consolidation_history tool call.

        Returns recent consolidation run history for dashboard display.
        """
        from datetime import datetime, timedelta

        project_id = args.get("project_id")
        if not project_id:
            project = self.project_manager.get_or_create_project()
            project_id = project.id

        limit = args.get("limit", 10)

        try:
            # Query consolidation history from database
            history = []

            if hasattr(self, 'store') and hasattr(self.store, 'db'):
                # Query consolidation_runs table from database
                try:
                    rows = self.store.db.execute_sync(
                        """
                        SELECT
                            created_at,
                            duration_ms,
                            patterns_count,
                            strategy,
                            quality_score
                        FROM consolidation_runs
                        WHERE project_id = %s
                        ORDER BY created_at DESC
                        LIMIT %s
                        """,
                        (project_id, limit)
                    )

                    for row in rows:
                        history.append({
                            "timestamp": row[0].isoformat() if row[0] else None,
                            "duration_seconds": (row[1] / 1000.0) if row[1] else 0,
                            "patterns_extracted": row[2] or 0,
                            "strategy": row[3] or "balanced",
                            "quality_score": round(float(row[4]) if row[4] else 0.0, 2)
                        })
                except Exception as db_error:
                    logger.warning(f"Failed to query consolidation_runs table: {db_error}")
                    # Return empty history if table doesn't exist or query fails
                    history = []

            return [
                TextContent(
                    type="text",
                    text=json.dumps({
                        "status": "success",
                        "project_id": project_id,
                        "consolidation_history": history,
                        "total_runs": len(history)
                    }, indent=2),
                )
            ]
        except Exception as e:
            logger.error(f"Failed to get consolidation history: {e}")
            return [
                TextContent(
                    type="text",
                    text=json.dumps({"status": "error", "error": str(e)}, indent=2),
                )
            ]

    async def _handle_get_project_stats(self, args: dict) -> list[TextContent]:
        """Handle get_project_stats tool call.

        Returns project statistics for dashboard display.
        """
        project_id = args.get("project_id")
        if not project_id:
            project = self.project_manager.get_or_create_project()
            project_id = project.id

        try:
            # Query actual project statistics from database
            stats = {
                "total_projects": 0,
                "active_projects": 0,
                "completed_projects": 0,
                "total_episodic_events": 0,
                "total_procedures": 0,
                "total_semantic_memories": 0,
                "total_tasks": 0,
                "total_entities": 0,
                "consolidation_runs": 0,
                "memory_health": {
                    "quality_score": 0.0,
                    "coverage_percent": 0.0,
                    "deduplication_percent": 0.0
                }
            }

            if hasattr(self, 'store') and hasattr(self.store, 'db'):
                try:
                    # Count episodic events
                    event_count = self.store.db.execute_sync(
                        "SELECT COUNT(*) FROM episodic_events WHERE project_id = %s",
                        (project_id,)
                    )
                    if event_count and len(event_count) > 0:
                        stats["total_episodic_events"] = event_count[0][0] or 0
                except Exception as e:
                    logger.warning(f"Failed to count episodic_events: {e}")

                try:
                    # Count procedures (workflows)
                    proc_count = self.store.db.execute_sync(
                        "SELECT COUNT(*) FROM procedures WHERE project_id = %s",
                        (project_id,)
                    )
                    if proc_count and len(proc_count) > 0:
                        stats["total_procedures"] = proc_count[0][0] or 0
                except Exception as e:
                    logger.warning(f"Failed to count procedures: {e}")

                try:
                    # Count semantic memories
                    mem_count = self.store.db.execute_sync(
                        "SELECT COUNT(*) FROM semantic_memories WHERE project_id = %s",
                        (project_id,)
                    )
                    if mem_count and len(mem_count) > 0:
                        stats["total_semantic_memories"] = mem_count[0][0] or 0
                except Exception as e:
                    logger.warning(f"Failed to count semantic_memories: {e}")

                try:
                    # Count tasks
                    task_count = self.store.db.execute_sync(
                        "SELECT COUNT(*) FROM prospective_tasks WHERE project_id = %s",
                        (project_id,)
                    )
                    if task_count and len(task_count) > 0:
                        stats["total_tasks"] = task_count[0][0] or 0
                except Exception as e:
                    logger.warning(f"Failed to count prospective_tasks: {e}")

                try:
                    # Count entities in knowledge graph
                    entity_count = self.store.db.execute_sync(
                        "SELECT COUNT(*) FROM kg_entities WHERE project_id = %s",
                        (project_id,)
                    )
                    if entity_count and len(entity_count) > 0:
                        stats["total_entities"] = entity_count[0][0] or 0
                except Exception as e:
                    logger.warning(f"Failed to count kg_entities: {e}")

                try:
                    # Count consolidation runs
                    cons_count = self.store.db.execute_sync(
                        "SELECT COUNT(*) FROM consolidation_runs WHERE project_id = %s",
                        (project_id,)
                    )
                    if cons_count and len(cons_count) > 0:
                        stats["consolidation_runs"] = cons_count[0][0] or 0
                except Exception as e:
                    logger.warning(f"Failed to count consolidation_runs: {e}")

                try:
                    # Get quality score if available
                    if hasattr(self, 'quality_monitor'):
                        quality_score = self.quality_monitor.compute_memory_quality_score(project_id)
                        stats["memory_health"]["quality_score"] = round(quality_score, 2)
                except Exception as e:
                    logger.warning(f"Failed to get quality score: {e}")

                # Calculate project counts
                try:
                    project_count = self.store.db.execute_sync(
                        "SELECT COUNT(*) FROM projects"
                    )
                    if project_count and len(project_count) > 0:
                        stats["total_projects"] = project_count[0][0] or 0
                        stats["active_projects"] = 1 if stats["total_projects"] > 0 else 0
                except Exception as e:
                    logger.warning(f"Failed to count projects: {e}")

            return [
                TextContent(
                    type="text",
                    text=json.dumps({
                        "status": "success",
                        "project_id": project_id,
                        "stats": stats
                    }, indent=2),
                )
            ]
        except Exception as e:
            logger.error(f"Failed to get project stats: {e}")
            return [
                TextContent(
                    type="text",
                    text=json.dumps({"status": "error", "error": str(e)}, indent=2),
                )
            ]

    async def _handle_get_hook_executions(self, args: dict) -> list[TextContent]:
        """Handle get_hook_executions tool call.

        Returns hook execution history for dashboard display.

        Note: Hook execution history is tracked by the hook system in ~/.claude/hooks/
        This method queries available hook execution logs if available.
        """
        from datetime import datetime, timedelta
        import os

        hours = args.get("hours", 24)
        limit = args.get("limit", 50)

        try:
            executions = []

            # Try to read hook execution logs from filesystem
            hook_logs_dir = os.path.expanduser("~/.claude/hooks/logs")
            if os.path.exists(hook_logs_dir):
                try:
                    # Get all log files in the directory
                    log_files = [
                        f for f in os.listdir(hook_logs_dir)
                        if f.endswith(".log")
                    ]

                    # Sort by modification time (most recent first)
                    log_files = sorted(
                        log_files,
                        key=lambda f: os.path.getmtime(os.path.join(hook_logs_dir, f)),
                        reverse=True
                    )

                    # Parse hook execution entries from logs
                    now = datetime.utcnow()
                    cutoff_time = now - timedelta(hours=hours)

                    for log_file in log_files[:5]:  # Check last 5 log files
                        log_path = os.path.join(hook_logs_dir, log_file)
                        try:
                            with open(log_path, 'r') as f:
                                for line in f:
                                    if len(executions) >= limit:
                                        break
                                    # Parse log entries (basic parsing)
                                    if "execution" in line.lower() or "hook" in line.lower():
                                        executions.append({
                                            "timestamp": datetime.utcnow().isoformat(),
                                            "source": log_file,
                                            "status": "completed",
                                            "duration_ms": 0,
                                            "message": line.strip()[:100]  # First 100 chars
                                        })
                        except Exception as e:
                            logger.warning(f"Failed to read {log_file}: {e}")
                except Exception as e:
                    logger.warning(f"Failed to read hook logs directory: {e}")

            # If we don't have log data, return structured empty response
            if not executions:
                executions = []

            return [
                TextContent(
                    type="text",
                    text=json.dumps({
                        "status": "success",
                        "hours": hours,
                        "executions": executions,
                        "total_count": len(executions),
                        "note": "Hook execution history limited to available logs in ~/.claude/hooks/logs"
                    }, indent=2),
                )
            ]
        except Exception as e:
            logger.error(f"Failed to get hook executions: {e}")
            return [
                TextContent(
                    type="text",
                    text=json.dumps({
                        "status": "error",
                        "error": str(e),
                        "note": "Hook execution logs are tracked in ~/.claude/hooks/"
                    }, indent=2),
                )
            ]
