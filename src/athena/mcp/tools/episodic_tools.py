"""Episodic memory tools for event recording and retrieval."""

import logging
import os
import time
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from .base import BaseTool, ToolMetadata, ToolResult, ToolStatus

logger = logging.getLogger(__name__)


class RecordEventTool(BaseTool):
    """Record episodic events with context and outcomes."""

    def __init__(self, episodic_store, project_manager):
        """Initialize record event tool.

        Args:
            episodic_store: EpisodicStore instance for event storage
            project_manager: ProjectManager instance for project context
        """
        metadata = ToolMetadata(
            name="record_event",
            description="Record episodic event with context and optional outcome",
            category="episodic",
            version="1.0",
            parameters={
                "content": {
                    "type": "string",
                    "description": "Event description/content"
                },
                "event_type": {
                    "type": "string",
                    "description": "Type of event (action, decision, discovery, error)",
                    "default": "action"
                },
                "outcome": {
                    "type": "string",
                    "description": "Event outcome (success, failure, partial)",
                    "default": None
                },
                "context": {
                    "type": "object",
                    "description": "Context information (cwd, files, task, phase)",
                    "default": {}
                }
            },
            returns={
                "event_id": {
                    "type": "integer",
                    "description": "ID of recorded event"
                },
                "session_id": {
                    "type": "string",
                    "description": "Session ID for grouping events"
                },
                "timestamp": {
                    "type": "string",
                    "description": "Event timestamp"
                }
            },
            tags=["record", "event", "episodic"]
        )
        super().__init__(metadata)
        self.episodic_store = episodic_store
        self.project_manager = project_manager

    async def execute(self, **params) -> ToolResult:
        """Execute record event operation.

        Args:
            content: Event content (required)
            event_type: Type of event (optional)
            outcome: Event outcome (optional)
            context: Context information (optional)

        Returns:
            ToolResult with event_id and metadata
        """
        try:
            # Validate required parameters
            error = self.validate_params(params, ["content"])
            if error:
                return ToolResult.error(error)

            # Get or create project
            try:
                project = self.project_manager.get_or_create_project()
                project_id = project.id
            except Exception as e:
                return ToolResult.error(f"Project error: {str(e)}")

            # Create session ID
            session_id = f"session_{int(time.time())}"

            # Parse context
            from athena.episodic.models import EventContext, EventType, EventOutcome
            context_data = params.get("context", {})
            context = EventContext(
                cwd=context_data.get("cwd", os.getcwd()),
                files=context_data.get("files", []),
                task=context_data.get("task"),
                phase=context_data.get("phase"),
            )

            # Create event
            from athena.episodic.models import EpisodicEvent
            event = EpisodicEvent(
                project_id=project_id,
                session_id=session_id,
                timestamp=params.get("timestamp") or datetime.now(),
                event_type=EventType(params.get("event_type", "action")),
                content=params["content"],
                outcome=EventOutcome(params["outcome"]) if params.get("outcome") else None,
                context=context,
            )

            # Record event
            try:
                event_id = self.episodic_store.record_event(event)
            except Exception as e:
                self.logger.error(f"Event recording failed: {e}")
                return ToolResult.error(f"Recording failed: {str(e)}")

            result_data = {
                "event_id": event_id,
                "session_id": session_id,
                "timestamp": event.timestamp.isoformat(),
                "event_type": event.event_type.value if hasattr(event.event_type, 'value') else str(event.event_type),
                "content_length": len(params["content"])
            }

            self.log_execution(params, ToolResult.success(data=result_data))
            return ToolResult.success(
                data=result_data,
                message=f"Event recorded (ID: {event_id})"
            )

        except Exception as e:
            self.logger.exception(f"Unexpected error in record_event: {e}")
            return ToolResult.error(f"Unexpected error: {str(e)}")


class RecallEventsTool(BaseTool):
    """Recall episodic events with various filtering options."""

    def __init__(self, episodic_store, project_manager):
        """Initialize recall events tool.

        Args:
            episodic_store: EpisodicStore instance for event retrieval
            project_manager: ProjectManager instance for project context
        """
        metadata = ToolMetadata(
            name="recall_events",
            description="Recall episodic events with filtering by timeframe, query, or type",
            category="episodic",
            version="1.0",
            parameters={
                "timeframe": {
                    "type": "string",
                    "description": "Filter by timeframe (today, yesterday, this_week, last_week, this_month)",
                    "default": None
                },
                "query": {
                    "type": "string",
                    "description": "Search query for event content",
                    "default": None
                },
                "event_type": {
                    "type": "string",
                    "description": "Filter by event type",
                    "default": None
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of events to return",
                    "default": 10
                }
            },
            returns={
                "events": {
                    "type": "array",
                    "description": "List of events with metadata"
                },
                "count": {
                    "type": "integer",
                    "description": "Number of events returned"
                }
            },
            tags=["recall", "query", "episodic"]
        )
        super().__init__(metadata)
        self.episodic_store = episodic_store
        self.project_manager = project_manager

    async def execute(self, **params) -> ToolResult:
        """Execute recall events operation.

        Args:
            timeframe: Filter by timeframe (optional)
            query: Search query (optional)
            event_type: Filter by type (optional)
            limit: Max results (optional)

        Returns:
            ToolResult with list of events
        """
        try:
            # Get current project
            try:
                project = self.project_manager.require_project()
                project_id = project.id
            except Exception as e:
                return ToolResult.error(f"Project error: {str(e)}")

            limit = params.get("limit", 10)

            # Fetch events based on filter
            try:
                if params.get("timeframe"):
                    events = self._filter_by_timeframe(
                        project_id,
                        params["timeframe"],
                        limit
                    )
                elif params.get("query"):
                    events = self.episodic_store.search_events(
                        project_id,
                        params["query"],
                        limit=limit
                    )
                elif params.get("event_type"):
                    from athena.episodic.models import EventType
                    events = self.episodic_store.get_events_by_type(
                        project_id,
                        EventType(params["event_type"]),
                        limit=limit
                    )
                else:
                    events = self.episodic_store.get_recent_events(
                        project_id,
                        limit=limit
                    )
            except Exception as e:
                self.logger.error(f"Event retrieval failed: {e}")
                return ToolResult.error(f"Retrieval failed: {str(e)}")

            if not events:
                return ToolResult.success(
                    data={
                        "events": [],
                        "count": 0,
                        "filter": params
                    },
                    message="No events found"
                )

            # Format events
            events_data = []
            for event in events:
                event_type_str = event.event_type.value if hasattr(event.event_type, 'value') else str(event.event_type)
                outcome_str = None
                if event.outcome:
                    outcome_str = event.outcome.value if hasattr(event.outcome, 'value') else str(event.outcome)

                events_data.append({
                    "id": getattr(event, 'id', None),
                    "timestamp": event.timestamp.isoformat(),
                    "type": event_type_str,
                    "content": event.content[:200],  # Truncate for response
                    "outcome": outcome_str,
                    "content_length": len(event.content)
                })

            result_data = {
                "events": events_data,
                "count": len(events_data),
                "filter": {
                    "timeframe": params.get("timeframe"),
                    "query": params.get("query"),
                    "event_type": params.get("event_type")
                }
            }

            self.log_execution(params, ToolResult.success(data=result_data))
            return ToolResult.success(
                data=result_data,
                message=f"Retrieved {len(events_data)} events"
            )

        except Exception as e:
            self.logger.exception(f"Unexpected error in recall_events: {e}")
            return ToolResult.error(f"Unexpected error: {str(e)}")

    def _filter_by_timeframe(self, project_id: int, timeframe: str, limit: int) -> List:
        """Filter events by timeframe.

        Args:
            project_id: Project ID
            timeframe: Timeframe string
            limit: Result limit

        Returns:
            List of events
        """
        now = datetime.now()

        if timeframe == "today":
            start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
            return self.episodic_store.get_events_by_date(project_id, start_of_day, now)

        elif timeframe == "yesterday":
            start_of_yesterday = (now - timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            end_of_yesterday = start_of_yesterday.replace(
                hour=23, minute=59, second=59
            )
            return self.episodic_store.get_events_by_date(
                project_id, start_of_yesterday, end_of_yesterday
            )

        elif timeframe == "this_week":
            return self.episodic_store.get_recent_events(
                project_id, hours=168, limit=limit
            )

        elif timeframe == "last_week":
            week_start = now - timedelta(days=14)
            week_end = now - timedelta(days=7)
            all_events = self.episodic_store.get_recent_events(
                project_id, hours=336, limit=50
            )
            return [e for e in all_events if week_start <= e.timestamp <= week_end]

        elif timeframe == "this_month":
            return self.episodic_store.get_recent_events(
                project_id, hours=720, limit=limit
            )

        else:
            return self.episodic_store.get_recent_events(
                project_id, hours=168, limit=limit
            )


class GetTimelineTool(BaseTool):
    """Get temporal timeline of events."""

    def __init__(self, episodic_store, project_manager):
        """Initialize timeline tool.

        Args:
            episodic_store: EpisodicStore instance
            project_manager: ProjectManager instance
        """
        metadata = ToolMetadata(
            name="get_timeline",
            description="Get temporal timeline of events for specified period",
            category="episodic",
            version="1.0",
            parameters={
                "days": {
                    "type": "integer",
                    "description": "Number of days to look back",
                    "default": 7
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of events to return",
                    "default": 20
                }
            },
            returns={
                "events": {
                    "type": "array",
                    "description": "Timeline of events with timestamps"
                },
                "period_days": {
                    "type": "integer",
                    "description": "Number of days covered"
                },
                "count": {
                    "type": "integer",
                    "description": "Number of events"
                }
            },
            tags=["timeline", "temporal", "episodic"]
        )
        super().__init__(metadata)
        self.episodic_store = episodic_store
        self.project_manager = project_manager

    async def execute(self, **params) -> ToolResult:
        """Execute timeline retrieval.

        Args:
            days: Number of days to look back (optional)
            limit: Maximum events (optional)

        Returns:
            ToolResult with timeline of events
        """
        try:
            # Get current project
            try:
                project = self.project_manager.require_project()
                project_id = project.id
            except Exception as e:
                return ToolResult.error(f"Project error: {str(e)}")

            days = params.get("days", 7)
            limit = params.get("limit", 20)

            # Get recent events
            try:
                events = self.episodic_store.get_recent_events(
                    project_id,
                    hours=days * 24,
                    limit=limit
                )
            except Exception as e:
                self.logger.error(f"Timeline retrieval failed: {e}")
                return ToolResult.error(f"Retrieval failed: {str(e)}")

            if not events:
                return ToolResult.success(
                    data={
                        "events": [],
                        "period_days": days,
                        "count": 0,
                        "message": f"No events in the last {days} days"
                    },
                    message=f"No events found in last {days} days"
                )

            # Format timeline
            events_data = []
            for event in events:
                event_type_str = event.event_type.value if hasattr(event.event_type, 'value') else str(event.event_type)
                events_data.append({
                    "timestamp": event.timestamp.isoformat(),
                    "date": event.timestamp.strftime("%Y-%m-%d"),
                    "time": event.timestamp.strftime("%H:%M:%S"),
                    "type": event_type_str,
                    "content": event.content[:100],
                    "content_length": len(event.content)
                })

            result_data = {
                "events": events_data,
                "period_days": days,
                "count": len(events_data),
                "start_date": (datetime.now() - timedelta(days=days)).isoformat(),
                "end_date": datetime.now().isoformat()
            }

            self.log_execution(params, ToolResult.success(data=result_data))
            return ToolResult.success(
                data=result_data,
                message=f"Timeline retrieved: {len(events_data)} events in {days} days"
            )

        except Exception as e:
            self.logger.exception(f"Unexpected error in get_timeline: {e}")
            return ToolResult.error(f"Unexpected error: {str(e)}")
