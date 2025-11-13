"""Episodic Memory Handlers - Extracted Domain Module

This module contains all episodic memory handler methods extracted from handlers.py
as part of Phase 1 of the handler refactoring.

Handler Methods (16 total, ~1752 lines):
- _handle_record_event: Record new episodic event
- _handle_recall_events: Recall events with advanced filtering
- _handle_recall_events_by_context: Recall events by context type
- _handle_recall_events_by_session: Recall events by session
- _handle_recall_events_by_tool_usage: Recall events by tool usage
- _handle_timeline_query: Query events by timeline
- _handle_trace_consolidation: Trace consolidation of events
- _handle_recall_episodic_events: Recall episodic events
- _handle_episodic_store_event: Store episodic event
- _handle_episodic_context_transition: Record context transitions
- _handle_temporal_chain_events: Chain related events temporally
- _handle_timeline_retrieve: Retrieve timeline of events
- _handle_timeline_visualize: Visualize timeline data
- _handle_consolidate_episodic_session: Consolidate session events
- _handle_surprise_detect: Detect surprising events
- _handle_temporal_consolidate: Consolidate by temporal proximity

Dependencies:
- Imports: EventContext, EventType, EventOutcome, TemporalChain, ConsolidationRouter, SurpriseDetector
- Attributes: self.database, self.episodic_store, self.logger (used across all 16)
- Shared imports from parent: datetime, timedelta, TextContent, json, logging

Integration Pattern:
This module uses the mixin pattern. Methods are defined here and bound to MemoryMCPServer
in handlers.py via:
    class MemoryMCPServer(EpisodicHandlersMixin, ...):
        pass

This pattern enables:
- Clean separation of domain logic
- Reduced file size (12,363 → ~10,600 in handlers.py)
- Easier testing of episodic domain
- Clear migration path for Phase 2-10
"""

import json
import logging
import math
from datetime import datetime, timedelta
from typing import Any, List, Dict, Optional

from mcp.types import TextContent

from .filesystem_api_integration import get_integration

logger = logging.getLogger(__name__)


class EpisodicHandlersMixin:
    """Mixin class containing all episodic memory handler methods.

    This mixin is designed to be mixed into MemoryMCPServer class.
    It provides all episodic memory operations without modifying the main handler structure.
    """

    async def _handle_record_event(self, args: dict) -> list[TextContent]:
        """
        Record a new episodic event with comprehensive metadata.

        Supports spatial-temporal grounding, importance scoring, and tagging.

        Args:
            args: Dictionary with keys:
                - content: Event description (required)
                - context: Context information
                - context_type: Type of context (default: "general")
                - session_id: Session identifier (default: "default")
                - spatial_context: File path or spatial location (default: "/")
                - importance: Importance score 0.0-1.0 (default: 0.5)
                - tags: List of tags
                - metadata: Additional metadata dict

        Returns:
            List with TextContent containing JSON response
        """
        try:
            content = args.get("content", "")
            context = args.get("context", "")
            context_type = args.get("context_type", "general")
            session_id = args.get("session_id", "default")
            spatial_context = args.get("spatial_context", "/")
            importance = args.get("importance", 0.5)
            tags = args.get("tags", [])
            metadata = args.get("metadata", {})

            if not content:
                return [TextContent(type="text", text=json.dumps({
                    "error": "content is required"
                }))]

            # Validate importance range
            importance = max(0.0, min(1.0, importance))

            timestamp = datetime.now().isoformat()

            # Enrich metadata with automatic fields
            enriched_metadata = {
                **metadata,
                "recorded_at": timestamp,
                "context_length": len(content)
            }

            sql = """
                INSERT INTO episodic_events
                (timestamp, content, context, context_type, session_id,
                 spatial_context, importance, tags, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            cursor = self.database.conn.cursor()
            cursor.execute(sql, (
                timestamp, content, context, context_type, session_id,
                spatial_context, importance, json.dumps(tags), json.dumps(enriched_metadata)
            ))
            self.database.conn.commit()

            event_id = cursor.lastrowid

            # Check for similar recent events (potential duplicates)
            recent_sql = """
                SELECT id, content, timestamp
                FROM episodic_events
                WHERE session_id = ?
                AND id != ?
                AND timestamp > datetime('now', '-5 minutes')
                ORDER BY timestamp DESC
                LIMIT 5
            """
            cursor.execute(recent_sql, (session_id, event_id))
            recent_events = cursor.fetchall()

            # Simple duplicate detection (exact content match)
            duplicates = [
                {"id": row[0], "timestamp": row[2]}
                for row in recent_events
                if row[1] == content
            ]

            response = {
                "id": event_id,
                "timestamp": timestamp,
                "content": content,
                "context_type": context_type,
                "session_id": session_id,
                "spatial_context": spatial_context,
                "importance": importance,
                "tags": tags,
                "warnings": []
            }

            if duplicates:
                response["warnings"].append({
                    "type": "potential_duplicate",
                    "similar_events": duplicates
                })

            return [TextContent(type="text", text=json.dumps(response, indent=2))]

        except Exception as e:
            logger.error(f"Error recording event: {e}", exc_info=True)
            return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

    async def _handle_recall_events(self, args: dict) -> list[TextContent]:
        """
        Recall episodic events with advanced filtering and temporal clustering.

        Returns events grouped by temporal proximity with spatial-temporal grounding.

        Args:
            args: Dictionary with optional filters:
                - query: Search query
                - filters: Dict with min_timestamp, max_timestamp, session_id, context_type,
                  spatial_path, tags, min_importance
                - limit: Maximum results (default: 10)

        Returns:
            List with TextContent containing events, clusters, and spatial distribution
        """
        try:
            query = args.get("query", "")
            filters = args.get("filters", {})
            limit = args.get("limit", 10)

            # Parse filters
            min_timestamp = filters.get("min_timestamp")
            max_timestamp = filters.get("max_timestamp")
            session_id = filters.get("session_id")
            context_type = filters.get("context_type")
            spatial_path = filters.get("spatial_path")
            tags = filters.get("tags", [])
            min_importance = filters.get("min_importance")

            # Build SQL query with comprehensive filters
            sql_parts = ["SELECT * FROM episodic_events WHERE 1=1"]
            params = []

            if query:
                sql_parts.append("AND (content LIKE ? OR context LIKE ?)")
                params.extend([f"%{query}%", f"%{query}%"])

            if min_timestamp:
                sql_parts.append("AND timestamp >= ?")
                params.append(min_timestamp)

            if max_timestamp:
                sql_parts.append("AND timestamp <= ?")
                params.append(max_timestamp)

            if session_id:
                sql_parts.append("AND session_id = ?")
                params.append(session_id)

            if context_type:
                sql_parts.append("AND context_type = ?")
                params.append(context_type)

            if spatial_path:
                sql_parts.append("AND spatial_context LIKE ?")
                params.append(f"%{spatial_path}%")

            if min_importance is not None:
                sql_parts.append("AND importance >= ?")
                params.append(min_importance)

            if tags:
                # Tags stored as JSON array, use JSON operations
                for tag in tags:
                    sql_parts.append("AND tags LIKE ?")
                    params.append(f'%"{tag}"%')

            sql_parts.append("ORDER BY timestamp DESC")
            sql_parts.append(f"LIMIT {limit}")

            sql = " ".join(sql_parts)

            cursor = self.database.conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()

            # Convert to structured format
            events = []
            for row in rows:
                event = {
                    "id": row[0],
                    "timestamp": row[1],
                    "content": row[2],
                    "context": row[3],
                    "context_type": row[4],
                    "session_id": row[5],
                    "spatial_context": row[6],
                    "importance": row[7],
                    "tags": json.loads(row[8]) if row[8] else [],
                    "metadata": json.loads(row[9]) if row[9] else {}
                }
                events.append(event)

            # Compute temporal clusters if multiple events
            clusters = []
            if len(events) > 1:
                temporal_gaps = []
                for i in range(len(events) - 1):
                    t1 = datetime.fromisoformat(events[i]["timestamp"])
                    t2 = datetime.fromisoformat(events[i + 1]["timestamp"])
                    gap = abs((t2 - t1).total_seconds())
                    temporal_gaps.append(gap)

                # Define clusters based on gaps > 5 minutes
                cluster_threshold = 300  # seconds
                current_cluster = [events[0]]
                for i, gap in enumerate(temporal_gaps):
                    if gap < cluster_threshold:
                        current_cluster.append(events[i + 1])
                    else:
                        clusters.append(current_cluster)
                        current_cluster = [events[i + 1]]
                if current_cluster:
                    clusters.append(current_cluster)
            else:
                clusters = [events] if events else []

            # Spatial grounding analysis
            spatial_distribution = {}
            for event in events:
                path = event.get("spatial_context", "unknown")
                spatial_distribution[path] = spatial_distribution.get(path, 0) + 1

            # Build response
            response = {
                "events": events,
                "total": len(events),
                "clusters": [
                    {
                        "start": cluster[0]["timestamp"],
                        "end": cluster[-1]["timestamp"],
                        "size": len(cluster),
                        "importance": sum(e.get("importance", 0) for e in cluster) / len(cluster)
                    }
                    for cluster in clusters
                ],
                "spatial_distribution": spatial_distribution,
                "filters_applied": {
                    "query": query,
                    "min_timestamp": min_timestamp,
                    "max_timestamp": max_timestamp,
                    "session_id": session_id,
                    "context_type": context_type,
                    "spatial_path": spatial_path,
                    "tags": tags,
                    "min_importance": min_importance
                }
            }

            return [TextContent(type="text", text=json.dumps(response, indent=2))]

        except Exception as e:
            logger.error(f"Error recalling events: {e}", exc_info=True)
            return [TextContent(type="text", text=json.dumps({
                "error": str(e),
                "events": [],
                "total": 0
            }))]

    async def _handle_recall_events_by_context(self, args: dict) -> list[TextContent]:
        """Recall events by context type with semantic grouping."""
        try:
            context_type = args.get("context_type", "")
            limit = args.get("limit", 20)

            if not context_type:
                return [TextContent(type="text", text=json.dumps({
                    "error": "context_type is required"
                }))]

            sql = """
                SELECT * FROM episodic_events
                WHERE context_type = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """

            cursor = self.database.conn.cursor()
            cursor.execute(sql, (context_type, limit))
            rows = cursor.fetchall()

            # Convert to structured format
            events = []
            for row in rows:
                event = {
                    "id": row[0],
                    "timestamp": row[1],
                    "content": row[2],
                    "context": row[3],
                    "context_type": row[4],
                    "session_id": row[5],
                    "spatial_context": row[6],
                    "importance": row[7],
                    "tags": json.loads(row[8]) if row[8] else [],
                    "metadata": json.loads(row[9]) if row[9] else {}
                }
                events.append(event)

            # Semantic grouping by content similarity (simple keyword extraction)
            semantic_groups = {}
            for event in events:
                content = event.get("content", "").lower()
                # Extract key terms (simple approach - words > 5 chars)
                words = [w for w in content.split() if len(w) > 5]
                for word in words[:3]:  # Top 3 words
                    if word not in semantic_groups:
                        semantic_groups[word] = []
                    semantic_groups[word].append(event["id"])

            response = {
                "context_type": context_type,
                "events": events,
                "total": len(events),
                "semantic_groups": semantic_groups
            }

            return [TextContent(type="text", text=json.dumps(response, indent=2))]

        except Exception as e:
            logger.error(f"Error recalling events by context: {e}", exc_info=True)
            return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

    async def _handle_recall_events_by_session(self, args: dict) -> list[TextContent]:
        """Recall events by session ID with temporal analysis."""
        try:
            session_id = args.get("session_id", "")

            if not session_id:
                return [TextContent(type="text", text=json.dumps({
                    "error": "session_id is required"
                }))]

            sql = """
                SELECT * FROM episodic_events
                WHERE session_id = ?
                ORDER BY timestamp ASC
            """

            cursor = self.database.conn.cursor()
            cursor.execute(sql, (session_id,))
            rows = cursor.fetchall()

            # Convert to structured format
            events = []
            for row in rows:
                event = {
                    "id": row[0],
                    "timestamp": row[1],
                    "content": row[2],
                    "context": row[3],
                    "context_type": row[4],
                    "session_id": row[5],
                    "spatial_context": row[6],
                    "importance": row[7],
                    "tags": json.loads(row[8]) if row[8] else [],
                    "metadata": json.loads(row[9]) if row[9] else {}
                }
                events.append(event)

            # Temporal analysis
            if events:
                start_time = datetime.fromisoformat(events[0]["timestamp"])
                end_time = datetime.fromisoformat(events[-1]["timestamp"])
                duration = (end_time - start_time).total_seconds()
            else:
                start_time = end_time = None
                duration = 0

            response = {
                "session_id": session_id,
                "events": events,
                "total": len(events),
                "temporal_analysis": {
                    "start_time": events[0]["timestamp"] if events else None,
                    "end_time": events[-1]["timestamp"] if events else None,
                    "duration_seconds": duration
                }
            }

            return [TextContent(type="text", text=json.dumps(response, indent=2))]

        except Exception as e:
            logger.error(f"Error recalling events by session: {e}", exc_info=True)
            return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

    async def _handle_recall_events_by_tool_usage(self, args: dict) -> list[TextContent]:
        """Recall events by tool usage patterns."""
        try:
            tool_name = args.get("tool_name", "")
            limit = args.get("limit", 20)

            sql = """
                SELECT * FROM episodic_events
                WHERE context_type = 'tool_use'
                ORDER BY timestamp DESC
                LIMIT ?
            """

            cursor = self.database.conn.cursor()
            cursor.execute(sql, (limit,))
            rows = cursor.fetchall()

            # Convert to structured format and filter by tool
            events = []
            for row in rows:
                metadata = json.loads(row[9]) if row[9] else {}
                if not tool_name or metadata.get("tool_name") == tool_name:
                    event = {
                        "id": row[0],
                        "timestamp": row[1],
                        "content": row[2],
                        "context": row[3],
                        "context_type": row[4],
                        "session_id": row[5],
                        "spatial_context": row[6],
                        "importance": row[7],
                        "tags": json.loads(row[8]) if row[8] else [],
                        "metadata": metadata
                    }
                    events.append(event)

            # Tool usage statistics
            tool_stats = {}
            for event in events:
                tool = event["metadata"].get("tool_name", "unknown")
                if tool not in tool_stats:
                    tool_stats[tool] = {"count": 0, "total_importance": 0}
                tool_stats[tool]["count"] += 1
                tool_stats[tool]["total_importance"] += event.get("importance", 0)

            response = {
                "tool_name": tool_name if tool_name else "all",
                "events": events,
                "total": len(events),
                "tool_statistics": tool_stats
            }

            return [TextContent(type="text", text=json.dumps(response, indent=2))]

        except Exception as e:
            logger.error(f"Error recalling events by tool usage: {e}", exc_info=True)
            return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

    async def _handle_timeline_query(self, args: dict) -> list[TextContent]:
        """Query events across a timeline with temporal reasoning."""
        try:
            start_time = args.get("start_time")
            end_time = args.get("end_time")
            context_filter = args.get("context_filter")

            sql_parts = ["SELECT * FROM episodic_events WHERE 1=1"]
            params = []

            if start_time:
                sql_parts.append("AND timestamp >= ?")
                params.append(start_time)

            if end_time:
                sql_parts.append("AND timestamp <= ?")
                params.append(end_time)

            if context_filter:
                sql_parts.append("AND context_type = ?")
                params.append(context_filter)

            sql_parts.append("ORDER BY timestamp ASC")
            sql = " ".join(sql_parts)

            cursor = self.database.conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()

            # Convert to timeline format
            timeline = []
            for row in rows:
                timeline.append({
                    "id": row[0],
                    "timestamp": row[1],
                    "content": row[2],
                    "context_type": row[4],
                    "importance": row[7]
                })

            # Detect temporal patterns (activity bursts)
            if len(timeline) > 1:
                timestamps = [datetime.fromisoformat(e["timestamp"]) for e in timeline]
                intervals = [(timestamps[i+1] - timestamps[i]).total_seconds()
                            for i in range(len(timestamps)-1)]

                # Find bursts (intervals < 60 seconds)
                bursts = []
                current_burst = [timeline[0]]
                for i, interval in enumerate(intervals):
                    if interval < 60:
                        current_burst.append(timeline[i+1])
                    else:
                        if len(current_burst) > 1:
                            bursts.append({
                                "start": current_burst[0]["timestamp"],
                                "end": current_burst[-1]["timestamp"],
                                "size": len(current_burst)
                            })
                        current_burst = [timeline[i+1]]

                if len(current_burst) > 1:
                    bursts.append({
                        "start": current_burst[0]["timestamp"],
                        "end": current_burst[-1]["timestamp"],
                        "size": len(current_burst)
                    })
            else:
                bursts = []

            response = {
                "timeline": timeline,
                "total": len(timeline),
                "temporal_patterns": {
                    "bursts": bursts,
                    "total_bursts": len(bursts)
                }
            }

            return [TextContent(type="text", text=json.dumps(response, indent=2))]

        except Exception as e:
            logger.error(f"Error querying timeline: {e}", exc_info=True)
            return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

    async def _handle_trace_consolidation(self, args: dict) -> list[TextContent]:
        """Trace consolidation process for specific events."""
        try:
            event_ids = args.get("event_ids", [])

            if not event_ids:
                return [TextContent(type="text", text=json.dumps({
                    "error": "event_ids is required"
                }))]

            # Get original events
            placeholders = ",".join("?" * len(event_ids))
            sql = f"SELECT * FROM episodic_events WHERE id IN ({placeholders})"

            cursor = self.database.conn.cursor()
            cursor.execute(sql, event_ids)
            rows = cursor.fetchall()

            events = []
            for row in rows:
                events.append({
                    "id": row[0],
                    "timestamp": row[1],
                    "content": row[2],
                    "context": row[3],
                    "importance": row[7]
                })

            # Find related semantic memories (by content similarity)
            semantic_matches = []
            for event in events:
                content = event["content"]
                search_sql = """
                    SELECT id, content, source_events
                    FROM semantic_memories
                    WHERE content LIKE ?
                    LIMIT 3
                """
                cursor.execute(search_sql, (f"%{content[:50]}%",))
                matches = cursor.fetchall()

                for match in matches:
                    semantic_matches.append({
                        "semantic_id": match[0],
                        "content": match[1],
                        "source_events": json.loads(match[2]) if match[2] else []
                    })

            response = {
                "events": events,
                "semantic_matches": semantic_matches,
                "trace": {
                    "note": "Consolidation traces source events to semantic memories"
                }
            }

            return [TextContent(type="text", text=json.dumps(response, indent=2))]

        except Exception as e:
            logger.error(f"Error tracing consolidation: {e}", exc_info=True)
            return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

    async def _handle_recall_episodic_events(self, args: dict) -> list[TextContent]:
        """Recall episodic events with flexible filtering."""
        try:
            query = args.get("query", "")
            session_id = args.get("session_id")
            context_type = args.get("context_type")
            start_time = args.get("start_time")
            end_time = args.get("end_time")
            limit = args.get("limit", 10)

            sql_parts = ["SELECT * FROM episodic_events WHERE 1=1"]
            params = []

            if query:
                sql_parts.append("AND (content LIKE ? OR context LIKE ?)")
                params.extend([f"%{query}%", f"%{query}%"])

            if session_id:
                sql_parts.append("AND session_id = ?")
                params.append(session_id)

            if context_type:
                sql_parts.append("AND context_type = ?")
                params.append(context_type)

            if start_time:
                sql_parts.append("AND timestamp >= ?")
                params.append(start_time)

            if end_time:
                sql_parts.append("AND timestamp <= ?")
                params.append(end_time)

            sql_parts.append("ORDER BY timestamp DESC")
            sql_parts.append(f"LIMIT {limit}")

            sql = " ".join(sql_parts)
            cursor = self.database.conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()

            events = []
            for row in rows:
                events.append({
                    "id": row[0],
                    "timestamp": row[1],
                    "content": row[2],
                    "context": row[3],
                    "context_type": row[4],
                    "session_id": row[5],
                    "spatial_context": row[6],
                    "importance": row[7],
                    "tags": json.loads(row[8]) if row[8] else []
                })

            return [TextContent(type="text", text=json.dumps({
                "events": events,
                "total": len(events)
            }, indent=2))]

        except Exception as e:
            logger.error(f"Error recalling episodic events: {e}", exc_info=True)
            return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

    async def _handle_episodic_store_event(self, args: dict) -> list[TextContent]:
        """Store a new episodic event with spatial-temporal grounding."""
        try:
            content = args.get("content", "")
            context = args.get("context", "")
            context_type = args.get("context_type", "general")
            session_id = args.get("session_id", "default")
            spatial_context = args.get("spatial_context", "/")
            importance = args.get("importance", 0.5)
            tags = args.get("tags", [])
            metadata = args.get("metadata", {})

            if not content:
                return [TextContent(type="text", text=json.dumps({
                    "error": "content is required"
                }))]

            timestamp = datetime.now().isoformat()

            sql = """
                INSERT INTO episodic_events
                (timestamp, content, context, context_type, session_id,
                 spatial_context, importance, tags, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            cursor = self.database.conn.cursor()
            cursor.execute(sql, (
                timestamp, content, context, context_type, session_id,
                spatial_context, importance, json.dumps(tags), json.dumps(metadata)
            ))
            self.database.conn.commit()

            event_id = cursor.lastrowid

            return [TextContent(type="text", text=json.dumps({
                "id": event_id,
                "timestamp": timestamp,
                "content": content,
                "context_type": context_type,
                "importance": importance
            }, indent=2))]

        except Exception as e:
            logger.error(f"Error storing episodic event: {e}", exc_info=True)
            return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

    async def _handle_episodic_context_transition(self, args: dict) -> list[TextContent]:
        """Record context transitions in episodic memory."""
        try:
            from_context = args.get("from_context", "")
            to_context = args.get("to_context", "")
            reason = args.get("reason", "")

            if not from_context or not to_context:
                return [TextContent(type="text", text=json.dumps({
                    "error": "from_context and to_context are required"
                }))]

            # Store as episodic event
            timestamp = datetime.now().isoformat()
            content = f"Context transition: {from_context} → {to_context}"

            sql = """
                INSERT INTO episodic_events
                (timestamp, content, context, context_type, importance, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """

            metadata = {
                "from_context": from_context,
                "to_context": to_context,
                "reason": reason
            }

            cursor = self.database.conn.cursor()
            cursor.execute(sql, (
                timestamp, content, reason, "context_transition", 0.7, json.dumps(metadata)
            ))
            self.database.conn.commit()

            return [TextContent(type="text", text=json.dumps({
                "transition_recorded": True,
                "timestamp": timestamp
            }, indent=2))]

        except Exception as e:
            logger.error(f"Error recording context transition: {e}", exc_info=True)
            return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

    async def _handle_temporal_chain_events(self, args: dict) -> list[TextContent]:
        """Chain related events across time."""
        try:
            seed_event_id = args.get("seed_event_id")
            max_chain_length = args.get("max_chain_length", 10)
            temporal_window = args.get("temporal_window", 3600)  # 1 hour default

            if not seed_event_id:
                return [TextContent(type="text", text=json.dumps({
                    "error": "seed_event_id is required"
                }))]

            # Get seed event
            cursor = self.database.conn.cursor()
            cursor.execute("SELECT * FROM episodic_events WHERE id = ?", (seed_event_id,))
            seed_row = cursor.fetchone()

            if not seed_row:
                return [TextContent(type="text", text=json.dumps({
                    "error": "Seed event not found"
                }))]

            seed_timestamp = datetime.fromisoformat(seed_row[1])

            # Find events within temporal window
            min_time = (seed_timestamp - timedelta(seconds=temporal_window)).isoformat()
            max_time = (seed_timestamp + timedelta(seconds=temporal_window)).isoformat()

            sql = """
                SELECT * FROM episodic_events
                WHERE timestamp BETWEEN ? AND ?
                AND id != ?
                ORDER BY timestamp ASC
                LIMIT ?
            """

            cursor.execute(sql, (min_time, max_time, seed_event_id, max_chain_length))
            rows = cursor.fetchall()

            # Build chain
            chain = [{
                "id": seed_row[0],
                "timestamp": seed_row[1],
                "content": seed_row[2],
                "context_type": seed_row[4],
                "is_seed": True
            }]

            for row in rows:
                chain.append({
                    "id": row[0],
                    "timestamp": row[1],
                    "content": row[2],
                    "context_type": row[4],
                    "is_seed": False
                })

            return [TextContent(type="text", text=json.dumps({
                "chain": chain,
                "total": len(chain)
            }, indent=2))]

        except Exception as e:
            logger.error(f"Error chaining events: {e}", exc_info=True)
            return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

    async def _handle_timeline_retrieve(self, args: dict) -> list[TextContent]:
        """Retrieve events as a temporal timeline."""
        try:
            start_time = args.get("start_time")
            end_time = args.get("end_time")
            context_filter = args.get("context_filter")
            limit = args.get("limit", 50)

            sql_parts = ["SELECT * FROM episodic_events WHERE 1=1"]
            params = []

            if start_time:
                sql_parts.append("AND timestamp >= ?")
                params.append(start_time)

            if end_time:
                sql_parts.append("AND timestamp <= ?")
                params.append(end_time)

            if context_filter:
                sql_parts.append("AND context_type = ?")
                params.append(context_filter)

            sql_parts.append("ORDER BY timestamp ASC")
            sql_parts.append(f"LIMIT {limit}")

            sql = " ".join(sql_parts)
            cursor = self.database.conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()

            # Build timeline with temporal gaps
            timeline = []
            prev_time = None

            for row in rows:
                event = {
                    "id": row[0],
                    "timestamp": row[1],
                    "content": row[2],
                    "context_type": row[4],
                    "importance": row[7]
                }

                if prev_time:
                    current_time = datetime.fromisoformat(row[1])
                    gap = (current_time - prev_time).total_seconds()
                    event["temporal_gap"] = gap

                timeline.append(event)
                prev_time = datetime.fromisoformat(row[1])

            # Compute statistics
            if timeline:
                total_duration = (
                    datetime.fromisoformat(timeline[-1]["timestamp"]) -
                    datetime.fromisoformat(timeline[0]["timestamp"])
                ).total_seconds()
            else:
                total_duration = 0

            return [TextContent(type="text", text=json.dumps({
                "timeline": timeline,
                "total": len(timeline),
                "statistics": {
                    "total_duration_seconds": total_duration,
                    "start_time": timeline[0]["timestamp"] if timeline else None,
                    "end_time": timeline[-1]["timestamp"] if timeline else None
                }
            }, indent=2))]

        except Exception as e:
            logger.error(f"Error retrieving timeline: {e}", exc_info=True)
            return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

    async def _handle_timeline_visualize(self, args: dict) -> list[TextContent]:
        """Generate timeline visualization data."""
        try:
            start_time = args.get("start_time")
            end_time = args.get("end_time")
            granularity = args.get("granularity", "hour")  # hour, day, week

            sql_parts = ["SELECT * FROM episodic_events WHERE 1=1"]
            params = []

            if start_time:
                sql_parts.append("AND timestamp >= ?")
                params.append(start_time)

            if end_time:
                sql_parts.append("AND timestamp <= ?")
                params.append(end_time)

            sql_parts.append("ORDER BY timestamp ASC")
            sql = " ".join(sql_parts)

            cursor = self.database.conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()

            # Group events by time buckets
            buckets = {}
            for row in rows:
                timestamp = datetime.fromisoformat(row[1])

                if granularity == "hour":
                    bucket_key = timestamp.strftime("%Y-%m-%d %H:00")
                elif granularity == "day":
                    bucket_key = timestamp.strftime("%Y-%m-%d")
                elif granularity == "week":
                    bucket_key = timestamp.strftime("%Y-W%W")
                else:
                    bucket_key = timestamp.strftime("%Y-%m-%d %H:00")

                if bucket_key not in buckets:
                    buckets[bucket_key] = {
                        "count": 0,
                        "context_types": {},
                        "total_importance": 0
                    }

                buckets[bucket_key]["count"] += 1
                buckets[bucket_key]["total_importance"] += row[7]  # importance

                context_type = row[4]
                if context_type not in buckets[bucket_key]["context_types"]:
                    buckets[bucket_key]["context_types"][context_type] = 0
                buckets[bucket_key]["context_types"][context_type] += 1

            # Convert to timeline format
            timeline = []
            for bucket_key, bucket_data in sorted(buckets.items()):
                timeline.append({
                    "time_bucket": bucket_key,
                    "event_count": bucket_data["count"],
                    "avg_importance": bucket_data["total_importance"] / bucket_data["count"],
                    "context_distribution": bucket_data["context_types"]
                })

            return [TextContent(type="text", text=json.dumps({
                "timeline": timeline,
                "granularity": granularity,
                "total_buckets": len(timeline)
            }, indent=2))]

        except Exception as e:
            logger.error(f"Error visualizing timeline: {e}", exc_info=True)
            return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

    async def _handle_consolidate_episodic_session(self, args: dict) -> list[TextContent]:
        """Consolidate episodic events from a session into semantic knowledge."""
        try:
            session_id = args.get("session_id", "")

            if not session_id:
                return [TextContent(type="text", text=json.dumps({
                    "error": "session_id is required"
                }))]

            # Get session events
            sql = """
                SELECT * FROM episodic_events
                WHERE session_id = ?
                ORDER BY timestamp ASC
            """

            cursor = self.database.conn.cursor()
            cursor.execute(sql, (session_id,))
            rows = cursor.fetchall()

            if not rows:
                return [TextContent(type="text", text=json.dumps({
                    "error": "No events found for session"
                }))]

            # Extract patterns (simple keyword extraction)
            all_content = " ".join([row[2] for row in rows])
            words = all_content.lower().split()
            word_freq = {}
            for word in words:
                if len(word) > 5:  # Filter short words
                    word_freq[word] = word_freq.get(word, 0) + 1

            # Top patterns (most frequent words)
            patterns = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]

            # Create semantic memory
            semantic_content = f"Session {session_id} patterns: " + ", ".join([p[0] for p in patterns])

            semantic_sql = """
                INSERT INTO semantic_memories
                (content, context, importance, tags, source_events)
                VALUES (?, ?, ?, ?, ?)
            """

            event_ids = [row[0] for row in rows]
            cursor.execute(semantic_sql, (
                semantic_content,
                f"Consolidated from session {session_id}",
                0.7,
                json.dumps(["session_consolidation"]),
                json.dumps(event_ids)
            ))
            self.database.conn.commit()

            semantic_id = cursor.lastrowid

            response = {
                "session_id": session_id,
                "events_processed": len(rows),
                "patterns_extracted": [{"keyword": p[0], "frequency": p[1]} for p in patterns],
                "semantic_memory_id": semantic_id
            }

            return [TextContent(type="text", text=json.dumps(response, indent=2))]

        except Exception as e:
            logger.error(f"Error consolidating session: {e}", exc_info=True)
            return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

    async def _handle_surprise_detect(self, args: dict) -> list[TextContent]:
        """Detect surprising events (high importance, unexpected context)."""
        try:
            session_id = args.get("session_id")
            min_importance = args.get("min_importance", 0.7)
            limit = args.get("limit", 10)

            sql_parts = ["SELECT * FROM episodic_events WHERE importance >= ?"]
            params = [min_importance]

            if session_id:
                sql_parts.append("AND session_id = ?")
                params.append(session_id)

            sql_parts.append("ORDER BY importance DESC, timestamp DESC")
            sql_parts.append(f"LIMIT {limit}")

            sql = " ".join(sql_parts)
            cursor = self.database.conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()

            # Compute surprise scores (importance + context novelty)
            surprising_events = []
            for row in rows:
                context_type = row[4]

                # Check how rare this context type is
                context_sql = """
                    SELECT COUNT(*) FROM episodic_events
                    WHERE context_type = ?
                """
                cursor.execute(context_sql, (context_type,))
                context_count = cursor.fetchone()[0]

                # Surprise = importance * (1 / log(context_count + 1))
                surprise_score = row[7] * (1 / math.log(context_count + 2))

                surprising_events.append({
                    "id": row[0],
                    "timestamp": row[1],
                    "content": row[2],
                    "context_type": row[4],
                    "importance": row[7],
                    "surprise_score": surprise_score
                })

            # Re-sort by surprise score
            surprising_events.sort(key=lambda x: x["surprise_score"], reverse=True)

            return [TextContent(type="text", text=json.dumps({
                "surprising_events": surprising_events,
                "total": len(surprising_events)
            }, indent=2))]

        except Exception as e:
            logger.error(f"Error detecting surprise: {e}", exc_info=True)
            return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

    async def _handle_temporal_consolidate(self, args: dict) -> list[TextContent]:
        """Consolidate events using temporal proximity clustering."""
        try:
            session_id = args.get("session_id")
            temporal_threshold = args.get("temporal_threshold", 300)  # 5 minutes default

            sql_parts = ["SELECT * FROM episodic_events"]
            params = []

            if session_id:
                sql_parts.append("WHERE session_id = ?")
                params.append(session_id)

            sql_parts.append("ORDER BY timestamp ASC")
            sql = " ".join(sql_parts)

            cursor = self.database.conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()

            if not rows:
                return [TextContent(type="text", text=json.dumps({
                    "error": "No events found"
                }))]

            # Temporal clustering
            clusters = []
            current_cluster = [rows[0]]

            for i in range(1, len(rows)):
                prev_time = datetime.fromisoformat(rows[i-1][1])
                curr_time = datetime.fromisoformat(rows[i][1])
                gap = (curr_time - prev_time).total_seconds()

                if gap < temporal_threshold:
                    current_cluster.append(rows[i])
                else:
                    clusters.append(current_cluster)
                    current_cluster = [rows[i]]

            if current_cluster:
                clusters.append(current_cluster)

            # Extract patterns from each cluster
            consolidated_patterns = []
            for cluster in clusters:
                cluster_content = " ".join([row[2] for row in cluster])

                # Simple pattern extraction (most frequent words)
                words = cluster_content.lower().split()
                word_freq = {}
                for word in words:
                    if len(word) > 5:
                        word_freq[word] = word_freq.get(word, 0) + 1

                top_patterns = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]

                consolidated_patterns.append({
                    "start_time": cluster[0][1],
                    "end_time": cluster[-1][1],
                    "event_count": len(cluster),
                    "patterns": [{"keyword": p[0], "frequency": p[1]} for p in top_patterns]
                })

            response = {
                "total_clusters": len(clusters),
                "total_events": len(rows),
                "consolidated_patterns": consolidated_patterns,
                "temporal_threshold_seconds": temporal_threshold
            }

            return [TextContent(type="text", text=json.dumps(response, indent=2))]

        except Exception as e:
            logger.error(f"Error consolidating temporal events: {e}", exc_info=True)
            return [TextContent(type="text", text=json.dumps({"error": str(e)}))]
