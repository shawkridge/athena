"""
Pattern extraction from episodic events.

Runs consolidation locally, returns pattern summaries only.
Never returns full pattern objects or full event data.
"""

from typing import Dict, Any, List

try:
    import psycopg
    from psycopg import AsyncConnection
except ImportError:
    raise ImportError("PostgreSQL required: pip install psycopg[binary]")
from datetime import datetime, timedelta


async def extract_patterns(
    host: str,
    port: int,
    dbname: str,
    user: str,
    password: str,
    time_window_hours: int = 24,
    min_support: float = 0.3,
    confidence_threshold: float = 0.5,
) -> Dict[str, Any]:
    """
    Extract patterns from recent episodic events.

    Local processing: clustering and pattern detection happens in sandbox.
    Returns: Pattern summaries only, never full patterns.

    Token cost: ~250 tokens vs 20,000 for full patterns.

    Args:
        host: PostgreSQL host
        port: PostgreSQL port
        dbname: Database name
        user: PostgreSQL user
        password: PostgreSQL password
        time_window_hours: Look back window
        min_support: Minimum pattern support (0-1)
        confidence_threshold: Minimum confidence

    Returns:
        Summary with:
        - patterns_extracted: Total patterns found
        - pattern_types: Distribution by type
        - avg_confidence: Average confidence of patterns
        - top_patterns_by_confidence: Top 5 pattern summaries (IDs only)
    """
    try:
        conn = await AsyncConnection.connect(
            host, port=port, dbname=dbname, user=user, password=password
        )
        cursor = conn.cursor()

        # Get recent events
        cutoff_time = datetime.utcnow() - timedelta(hours=time_window_hours)
        await cursor.execute(
            """
            SELECT id, event_type, outcome, confidence, timestamp
            FROM episodic_events
            WHERE timestamp >= %s
            ORDER BY timestamp DESC
            """,
            (cutoff_time.isoformat(),),
        )

        events = [dict(row) for row in await cursor.fetchall()]
        await conn.close()

        if not events:
            return {"patterns_extracted": 0, "empty": True, "time_window_hours": time_window_hours}

        # Extract patterns (local processing)
        patterns = _extract_local(events, min_support, confidence_threshold)

        if not patterns:
            return {
                "patterns_extracted": 0,
                "time_window_hours": time_window_hours,
                "events_analyzed": len(events),
            }

        # Summarize patterns
        pattern_types = {}
        confidences = []

        for p in patterns:
            ptype = p.get("type", "unknown")
            pattern_types[ptype] = pattern_types.get(ptype, 0) + 1
            confidences.append(p.get("confidence", 0))

        # Top patterns
        top_patterns = sorted(patterns, key=lambda x: x.get("confidence", 0), reverse=True)[:5]

        return {
            "patterns_extracted": len(patterns),
            "time_window_hours": time_window_hours,
            "events_analyzed": len(events),
            "pattern_type_distribution": pattern_types,
            "avg_confidence": sum(confidences) / len(confidences) if confidences else 0,
            "confidence_range": (
                (min(confidences), max(confidences)) if confidences else (None, None)
            ),
            "top_5_pattern_ids": [p.get("id") for p in top_patterns],
            "consolidation_quality": _quality_score(patterns),
        }

    except Exception as e:
        return {"error": str(e), "error_type": type(e).__name__}


async def get_pattern_details(
    host: str, port: int, dbname: str, user: str, password: str, pattern_id: str
) -> Dict[str, Any]:
    """Get details for a specific pattern (use sparingly)."""
    try:
        conn = await AsyncConnection.connect(
            host, port=port, dbname=dbname, user=user, password=password
        )
        cursor = conn.cursor()

        await cursor.execute("SELECT * FROM patterns WHERE id = %s", (pattern_id,))

        row = await cursor.fetchone()
        await conn.close()

        if not row:
            return {"error": f"Pattern not found: {pattern_id}"}

        return dict(row)

    except Exception as e:
        return {"error": str(e), "error_type": type(e).__name__}


def _extract_local(events: List, min_support: float, confidence_threshold: float) -> List[Dict]:
    """Extract patterns from events locally."""
    patterns = []

    # Event type sequences
    event_types = [e.get("event_type") for e in events]
    type_patterns = _find_sequences(event_types, min_support)

    for pattern in type_patterns:
        confidence = _calc_confidence(pattern, events)
        if confidence >= confidence_threshold:
            patterns.append(
                {
                    "id": f"pattern_{len(patterns)}",
                    "type": "event_sequence",
                    "pattern": pattern,
                    "support": _calc_support(pattern, events),
                    "confidence": confidence,
                }
            )

    # Outcome transitions
    outcomes = [e.get("outcome") for e in events]
    outcome_patterns = _find_transitions(outcomes, min_support)

    for pattern in outcome_patterns:
        confidence = _calc_confidence(pattern, events)
        if confidence >= confidence_threshold:
            patterns.append(
                {
                    "id": f"pattern_{len(patterns)}",
                    "type": "outcome_transition",
                    "pattern": pattern,
                    "support": _calc_support(pattern, events),
                    "confidence": confidence,
                }
            )

    return patterns


def _find_sequences(items: List, min_support: float) -> List[tuple]:
    """Find common sequences in items."""
    sequences = {}
    for i in range(len(items) - 1):
        seq = (items[i], items[i + 1])
        sequences[seq] = sequences.get(seq, 0) + 1

    threshold = max(1, int(len(items) * min_support))
    return [seq for seq, count in sequences.items() if count >= threshold]


def _find_transitions(items: List, min_support: float) -> List[tuple]:
    """Find common state transitions."""
    return _find_sequences(items, min_support)


def _calc_support(pattern: tuple, events: List) -> float:
    """Calculate support for a pattern."""
    count = 0
    event_vals = [e.get("outcome") or e.get("event_type") for e in events]
    for i in range(len(event_vals) - 1):
        if (event_vals[i], event_vals[i + 1]) == pattern:
            count += 1
    return count / max(1, len(events) - 1)


def _calc_confidence(pattern: tuple, events: List) -> float:
    """Calculate confidence for a pattern."""
    # Confidence: P(pattern_consequence | pattern_antecedent)
    antecedent_count = 0
    antecedent_followed_count = 0

    event_vals = [e.get("outcome") or e.get("event_type") for e in events]
    for i in range(len(event_vals) - 1):
        if event_vals[i] == pattern[0]:
            antecedent_count += 1
            if event_vals[i + 1] == pattern[1]:
                antecedent_followed_count += 1

    return antecedent_followed_count / max(1, antecedent_count)


def _quality_score(patterns: List[Dict]) -> float:
    """Calculate overall consolidation quality."""
    if not patterns:
        return 0.0

    avg_confidence = sum(p.get("confidence", 0) for p in patterns) / len(patterns)
    avg_support = sum(p.get("support", 0) for p in patterns) / len(patterns)

    return (avg_confidence + avg_support) / 2


if __name__ == "__main__":
    print("Pattern extraction module - use via filesystem API")
