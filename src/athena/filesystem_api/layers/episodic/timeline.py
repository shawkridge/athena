"""
Temporal analysis and timeline operations for episodic memory.

Extracts time-based patterns, trends, and temporal relationships.
Returns summary statistics, not full event timelines.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
try:
    import psycopg
    from psycopg import AsyncConnection
except ImportError:
    raise ImportError("PostgreSQL required: pip install psycopg[binary]")


async def get_event_timeline(
    host: str,
    port: int,
    dbname: str,
    user: str,
    password: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    event_type: Optional[str] = None,
    bucket_by: str = "day"
) -> Dict[str, Any]:
    """
    Get temporal distribution of events (not the events themselves).

    Buckets events by time period and returns counts only.

    Args:
        db_path: Path to Athena memory database
        start_date: ISO date string (inclusive)
        end_date: ISO date string (inclusive)
        event_type: Filter by specific event type
        bucket_by: 'hour', 'day', 'week', 'month'

    Returns:
        Timeline summary with event counts per bucket
    """
    try:
        conn = await AsyncConnection.connect(db_path)
        cursor = conn.cursor()

        # Build query
        where_clauses = ["timestamp IS NOT NULL"]
        params = []

        if start_date:
            where_clauses.append("timestamp >= ?")
            params.append(start_date)

        if end_date:
            where_clauses.append("timestamp <= ?")
            params.append(end_date)

        if event_type:
            where_clauses.append("event_type = ?")
            params.append(event_type)

        where_clause = " AND ".join(where_clauses)

        # Get data for bucketing
        await cursor.execute(
            f"SELECT timestamp, event_type FROM episodic_events WHERE {where_clause}",
            params
        )

        events = await cursor.fetchall()
        await conn.close()

        if not events:
            return {
                "empty": True,
                "total_events": 0,
                "date_range": None
            }

        # Bucket events by time
        buckets = _bucket_by_time(events, bucket_by)

        # Calculate statistics
        timestamps = [datetime.fromisoformat(e[0]) for e in events]

        return {
            "total_events": len(events),
            "date_range": {
                "start": min(timestamps).isoformat(),
                "end": max(timestamps).isoformat(),
                "days_span": (max(timestamps) - min(timestamps)).days
            },
            "bucket_type": bucket_by,
            "bucket_count": len(buckets),
            "buckets": buckets,
            "busiest_bucket": max(buckets.items(), key=lambda x: x[1])[0] if buckets else None,
            "avg_events_per_bucket": len(events) / len(buckets) if buckets else 0
        }

    except Exception as e:
        return {
            "error": str(e),
            "error_type": type(e).__name__
        }


async def get_event_causality(
    host: str,
    port: int,
    dbname: str,
    user: str,
    password: str,
    event_id: str,
    window_minutes: int = 30
) -> Dict[str, Any]:
    """
    Find events that might be causally related (temporally close).

    Returns summary of nearby events, not full event data.

    Args:
        db_path: Path to database
        event_id: Event to analyze
        window_minutes: Time window before/after

    Returns:
        Summary of causally-nearby events
    """
    try:
        conn = await AsyncConnection.connect(db_path)
        # PostgreSQL returns dicts
        cursor = conn.cursor()

        # Get target event timestamp
        await cursor.execute(
            "SELECT timestamp FROM episodic_events WHERE id = ?",
            (event_id,)
        )
        target_row = await cursor.fetchone()
        if not target_row:
            return {"error": f"Event not found: {event_id}"}

        target_time = datetime.fromisoformat(target_row["timestamp"])

        # Find events within window
        window_start = target_time - timedelta(minutes=window_minutes)
        window_end = target_time + timedelta(minutes=window_minutes)

        await cursor.execute(
            """
            SELECT id, timestamp, event_type, outcome
            FROM episodic_events
            WHERE timestamp BETWEEN ? AND ? AND id != ?
            ORDER BY ABS(CAST((julianday(timestamp) - julianday(%s)) AS INTEGER))
            LIMIT 10
            """,
            (window_start.isoformat(), window_end.isoformat(), event_id, target_time.isoformat())
        )

        nearby = [dict(row) for row in await cursor.fetchall()]
        await conn.close()

        # Categorize by before/after
        before = [e for e in nearby if e["timestamp"] < target_time.isoformat()]
        after = [e for e in nearby if e["timestamp"] >= target_time.isoformat()]

        return {
            "target_event_id": event_id,
            "window_minutes": window_minutes,
            "events_before": len(before),
            "events_after": len(after),
            "total_nearby": len(nearby),
            "nearby_event_types": _count_types([e["event_type"] for e in nearby]),
            "before_outcomes": _count_outcomes([e["outcome"] for e in before]),
            "after_outcomes": _count_outcomes([e["outcome"] for e in after])
        }

    except Exception as e:
        return {
            "error": str(e),
            "error_type": type(e).__name__
        }


def _bucket_by_time(events: List, bucket_by: str) -> Dict[str, int]:
    """Bucket events by time period."""
    buckets = {}

    for timestamp_str, _ in events:
        try:
            dt = datetime.fromisoformat(timestamp_str)

            if bucket_by == "hour":
                key = dt.replace(minute=0, second=0, microsecond=0).isoformat()
            elif bucket_by == "day":
                key = dt.date().isoformat()
            elif bucket_by == "week":
                year, week, _ = dt.isocalendar()
                key = f"{year}-W{week:02d}"
            elif bucket_by == "month":
                key = dt.strftime("%Y-%m")
            else:
                key = dt.date().isoformat()

            buckets[key] = buckets.get(key, 0) + 1
        except:
            pass

    return buckets


def _count_types(types: List[str]) -> Dict[str, int]:
    """Count occurrences of types."""
    counts = {}
    for t in types:
        counts[t] = counts.get(t, 0) + 1
    return counts


def _count_outcomes(outcomes: List[str]) -> Dict[str, int]:
    """Count occurrences of outcomes."""
    counts = {}
    for o in outcomes:
        counts[o] = counts.get(o, 0) + 1
    return counts
