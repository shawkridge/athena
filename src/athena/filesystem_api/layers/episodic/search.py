"""
Search episodic events with local filtering.

This module provides the filesystem API for searching episodic memory events.
Designed for code execution paradigm: filter locally, return summaries only.

Usage:
    result = search_events(
        db_path="~/.athena/memory.db",
        query="authentication",
        limit=100,
        confidence_threshold=0.7
    )
"""

from typing import Dict, Any, Optional
from datetime import datetime
try:
    import psycopg
    from psycopg import AsyncConnection
except ImportError:
    raise ImportError("PostgreSQL required: pip install psycopg[binary]")
import json


async def search_events(
    host: str,
    port: int,
    dbname: str,
    user: str,
    password: str,
    query: str,
    limit: int = 100,
    confidence_threshold: float = 0.7,
    outcome_filter: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Search episodic events with local filtering and summarization.

    This function:
    1. Queries the database for matching events
    2. Filters locally (not in model context)
    3. Returns only summary statistics (not full event objects)

    Token cost: ~200 tokens (vs 15,000 for full event objects)

    Args:
        db_path: Path to Athena memory database
        query: Search query string
        limit: Maximum events to return
        confidence_threshold: Filter events with confidence >= this
        outcome_filter: Filter by outcome (success/failure/partial/unknown)

    Returns:
        Summary dictionary with:
        - total_found: Number of events matching query
        - high_confidence_count: Events above confidence threshold
        - avg_confidence: Average confidence of all results
        - date_range: (earliest, latest) timestamps
        - top_3_ids: IDs of top-confidence events
        - event_types: Distribution of event types
    """
    try:
        conn = await AsyncConnection.connect(
            f"dbname={dbname} user={user} password={password} host={host} port={port}"
        )
        # PostgreSQL returns dicts
        cursor = conn.cursor()

        # Search for events matching query
        # Search in content column and context fields (context_task, context_cwd, context_phase, context_branch)
        await cursor.execute(
            """
            SELECT id, timestamp, event_type, outcome, confidence
            FROM episodic_events
            WHERE content ILIKE %s
               OR context_task ILIKE %s
               OR context_phase ILIKE %s
               OR context_branch ILIKE %s
            LIMIT %s
            """,
            (f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%", limit)
        )

        all_events = [dict(row) for row in await cursor.fetchall()]
        await conn.close()

        if not all_events:
            return {
                "query": query,
                "total_found": 0,
                "high_confidence_count": 0,
                "empty": True
            }

        # Filter by confidence (local processing)
        high_conf_events = [
            e for e in all_events
            if e.get("confidence", 0) >= confidence_threshold
        ]

        # Further filter by outcome if specified
        if outcome_filter:
            high_conf_events = [
                e for e in high_conf_events
                if e.get("outcome") == outcome_filter
            ]

        # Calculate statistics
        confidences = [e.get("confidence", 0) for e in all_events]
        timestamps = [
            datetime.fromisoformat(e.get("timestamp", ""))
            for e in all_events
            if e.get("timestamp")
        ]

        # Count event types
        event_types = {}
        for event in high_conf_events:
            et = event.get("event_type", "unknown")
            event_types[et] = event_types.get(et, 0) + 1

        # Build summary (small token count)
        summary = {
            "query": query,
            "total_found": len(all_events),
            "high_confidence_count": len(high_conf_events),
            "avg_confidence": sum(confidences) / len(confidences) if confidences else 0,
            "confidence_min": min(confidences) if confidences else None,
            "confidence_max": max(confidences) if confidences else None,
            "date_range": {
                "earliest": min(timestamps).isoformat() if timestamps else None,
                "latest": max(timestamps).isoformat() if timestamps else None,
            },
            "top_3_ids": [e.get("id") for e in high_conf_events[:3]],
            "event_types": event_types,
        }

        return summary

    except Exception as e:
        return {
            "error": str(e),
            "error_type": type(e).__name__,
            "query": query
        }


async def retrieve_event_details(
    host: str,
    port: int,
    dbname: str,
    user: str,
    password: str,
    event_id: str
) -> Dict[str, Any]:
    """
    Retrieve full details for a specific event.

    Used when agent has narrowed down to specific event IDs.
    Should be called sparingly to avoid token inflation.

    Args:
        db_path: Path to Athena memory database
        event_id: ID of event to retrieve

    Returns:
        Full event object (use sparingly!)
    """
    try:
        conn = await AsyncConnection.connect(db_path)
        # PostgreSQL returns dicts
        cursor = conn.cursor()

        await cursor.execute(
            "SELECT * FROM episodic_events WHERE id = ?",
            (event_id,)
        )

        row = await cursor.fetchone()
        await conn.close()

        if not row:
            return {"error": f"Event not found: {event_id}"}

        event = dict(row)

        # Parse JSON fields if they exist
        if "context" in event and isinstance(event["context"], str):
            try:
                event["context"] = json.loads(event["context"])
            except (json.JSONDecodeError, ValueError):
                pass

        return event

    except Exception as e:
        return {
            "error": str(e),
            "error_type": type(e).__name__
        }


if __name__ == "__main__":
    # Example usage
    print("Episodic search module - use via filesystem API")
