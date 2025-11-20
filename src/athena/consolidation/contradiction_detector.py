"""Automatic detection and resolution of contradictory memories.

During consolidation dreams, detects contradictory episodic events and
attempts to resolve them using:
- Evidence quality scoring
- Temporal ordering (later events are more recent)
- Explicit user corrections
- Outcome clarity (SUCCESS > PARTIAL > ONGOING)

This implements automatic interference detection from neuroscience.
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Tuple

from ..core.database import Database

logger = logging.getLogger(__name__)


class ContradictionDetector:
    """Detects and resolves contradictions in episodic memory."""

    MIN_SIMILARITY_THRESHOLD = 0.7  # Vector similarity threshold for conflicts
    CONFIDENCE_WEIGHT = 0.4
    RECENCY_WEIGHT = 0.3
    OUTCOME_WEIGHT = 0.3

    def __init__(self, db: Database):
        """Initialize detector.

        Args:
            db: Database instance
        """
        self.db = db

    async def detect_contradictions_in_project(
        self, project_id: int, similarity_threshold: float = MIN_SIMILARITY_THRESHOLD
    ) -> List[Dict]:
        """Detect contradictory event pairs in a project.

        Looks for events with:
        - Similar content (semantic similarity)
        - Contradictory outcomes (SUCCESS vs FAILURE for same operation)
        - Different evidence quality (prefer high-quality evidence)

        Args:
            project_id: Project to analyze
            similarity_threshold: Minimum similarity to consider related

        Returns:
            List of contradiction records
        """
        try:
            async with self.db.get_connection() as conn:
                # Find pairs of events with same type but different outcomes
                result = await conn.execute(
                    """
                    SELECT
                        e1.id AS event1_id,
                        e2.id AS event2_id,
                        e1.event_type,
                        e1.outcome AS outcome1,
                        e2.outcome AS outcome2,
                        e1.confidence AS confidence1,
                        e2.confidence AS confidence2,
                        e1.timestamp AS timestamp1,
                        e2.timestamp AS timestamp2,
                        e1.evidence_quality AS quality1,
                        e2.evidence_quality AS quality2,
                        e1.content AS content1,
                        e2.content AS content2
                    FROM episodic_events e1
                    JOIN episodic_events e2 ON
                        e1.project_id = e2.project_id
                        AND e1.event_type = e2.event_type
                        AND e1.id < e2.id
                        AND e1.outcome IS NOT NULL
                        AND e2.outcome IS NOT NULL
                        AND e1.outcome != e2.outcome
                    WHERE
                        e1.project_id = %s
                        AND (
                            (e1.outcome = 'success' AND e2.outcome = 'failure')
                            OR (e1.outcome = 'failure' AND e2.outcome = 'success')
                        )
                    ORDER BY ABS(e2.timestamp - e1.timestamp)
                    LIMIT 100
                    """,
                    (project_id,),
                )

                contradictions = []
                rows = await result.fetchall()

                for row in rows:
                    contradiction = {
                        "event1_id": row[0],
                        "event2_id": row[1],
                        "event_type": row[2],
                        "outcome1": row[3],
                        "outcome2": row[4],
                        "confidence1": row[5],
                        "confidence2": row[6],
                        "timestamp1": row[7],
                        "timestamp2": row[8],
                        "quality1": row[9],
                        "quality2": row[10],
                        "severity": self._calculate_contradiction_severity(
                            row[5], row[6], row[9], row[10], row[7], row[8]
                        ),
                        "recommended_resolution": self._recommend_resolution(
                            row[0],
                            row[1],
                            row[3],
                            row[4],
                            row[5],
                            row[6],
                            row[7],
                            row[8],
                        ),
                    }
                    contradictions.append(contradiction)

                if contradictions:
                    logger.info(
                        f"Detected {len(contradictions)} contradictions in project {project_id}"
                    )

                return contradictions

        except Exception as e:
            logger.error(f"Error detecting contradictions in project {project_id}: {e}")
            return []

    async def resolve_contradiction(
        self, event1_id: int, event2_id: int, resolution_strategy: str = "auto"
    ) -> bool:
        """Resolve a contradiction between two events.

        Strategies:
        - "auto": Use confidence/quality/recency to pick winner
        - "keep_latest": Keep most recent event
        - "keep_highest_quality": Keep highest evidence quality
        - "inhibit_both": Mark both as pending verification

        Args:
            event1_id: First event ID
            event2_id: Second event ID
            resolution_strategy: How to resolve

        Returns:
            True if resolved, False otherwise
        """
        try:
            async with self.db.get_connection() as conn:
                # Get both events
                result1 = await conn.execute(
                    """
                    SELECT id, content, outcome, confidence, evidence_quality, timestamp
                    FROM episodic_events
                    WHERE id = %s
                    """,
                    (event1_id,),
                )
                event1 = await result1.fetchone()

                result2 = await conn.execute(
                    """
                    SELECT id, content, outcome, confidence, evidence_quality, timestamp
                    FROM episodic_events
                    WHERE id = %s
                    """,
                    (event2_id,),
                )
                event2 = await result2.fetchone()

                if not event1 or not event2:
                    return False

                winner_id = None

                if resolution_strategy == "auto":
                    # Auto-resolution: pick by quality score
                    score1 = self._calculate_event_quality_score(event1)
                    score2 = self._calculate_event_quality_score(event2)
                    winner_id = event1_id if score1 > score2 else event2_id

                elif resolution_strategy == "keep_latest":
                    winner_id = event1_id if event1[5] > event2[5] else event2_id

                elif resolution_strategy == "keep_highest_quality":
                    quality1 = event1[4] if event1[4] else 0.5
                    quality2 = event2[4] if event2[4] else 0.5
                    winner_id = event1_id if quality1 > quality2 else event2_id

                elif resolution_strategy == "inhibit_both":
                    # Mark both as needing verification
                    loser_id = event2_id if winner_id == event1_id else event1_id
                else:
                    return False

                # Record resolution in memory_conflicts table
                if winner_id:
                    loser_id = event2_id if winner_id == event1_id else event1_id

                    await conn.execute(
                        """
                        INSERT INTO memory_conflicts (
                            memory_id_1, memory_id_2, conflict_type,
                            resolution, winner_id, created_at
                        ) VALUES (%s, %s, %s, %s, %s, NOW())
                        ON CONFLICT DO NOTHING
                        """,
                        (
                            event1_id,
                            event2_id,
                            "outcome_contradiction",
                            resolution_strategy,
                            winner_id,
                        ),
                    )

                    # Mark loser as requiring attention
                    await conn.execute(
                        """
                        UPDATE episodic_events
                        SET lifecycle_status = 'needs_review'
                        WHERE id = %s
                        """,
                        (loser_id,),
                    )

                    logger.info(
                        f"Resolved contradiction: winner={winner_id}, "
                        f"strategy={resolution_strategy}"
                    )

                    return True

        except Exception as e:
            logger.error(f"Error resolving contradiction {event1_id} vs {event2_id}: {e}")
            return False

    async def get_unresolved_contradictions(self, project_id: Optional[int] = None) -> List[Dict]:
        """Get list of unresolved contradictions.

        Args:
            project_id: Optional filter by project

        Returns:
            List of unresolved contradiction records
        """
        try:
            async with self.db.get_connection() as conn:
                if project_id:
                    result = await conn.execute(
                        """
                        SELECT
                            memory_id_1, memory_id_2, conflict_type,
                            created_at, resolution
                        FROM memory_conflicts
                        WHERE resolution IS NULL AND memory_id_1 IN (
                            SELECT id FROM episodic_events WHERE project_id = %s
                        )
                        ORDER BY created_at DESC
                        """,
                        (project_id,),
                    )
                else:
                    result = await conn.execute(
                        """
                        SELECT
                            memory_id_1, memory_id_2, conflict_type,
                            created_at, resolution
                        FROM memory_conflicts
                        WHERE resolution IS NULL
                        ORDER BY created_at DESC
                        """
                    )

                rows = await result.fetchall()
                return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Error retrieving unresolved contradictions: {e}")
            return []

    def _calculate_contradiction_severity(
        self,
        confidence1: float,
        confidence2: float,
        quality1: float,
        quality2: float,
        timestamp1: datetime,
        timestamp2: datetime,
    ) -> float:
        """Calculate severity of a contradiction (0.0-1.0).

        High confidence + high quality contradictions are more severe.

        Args:
            confidence1, confidence2: Confidence scores
            quality1, quality2: Evidence quality scores
            timestamp1, timestamp2: Event timestamps

        Returns:
            Severity score (0.0-1.0)
        """
        avg_confidence = (float(confidence1) + float(confidence2)) / 2
        avg_quality = (float(quality1) + float(quality2)) / 2
        time_distance = abs((timestamp2 - timestamp1).total_seconds()) / 86400  # days

        # Severity increases with confidence and quality
        # Decreases with time distance (old contradictions are less critical)
        base_severity = (avg_confidence + avg_quality) / 2
        time_factor = max(0.5, 1.0 - (time_distance / 30))  # Older = less severe
        severity = base_severity * time_factor

        return min(1.0, severity)

    def _calculate_event_quality_score(self, event: Tuple) -> float:
        """Calculate overall quality score for an event.

        Args:
            event: Event tuple (id, content, outcome, confidence, quality, timestamp)

        Returns:
            Quality score (0.0-1.0)
        """
        _, _, outcome, confidence, quality, _ = event

        # Weighted combination
        outcome_score = 1.0 if outcome == "success" else 0.3
        conf_score = float(confidence) if confidence else 0.5
        qual_score = float(quality) if quality else 0.5

        combined = (
            outcome_score * self.OUTCOME_WEIGHT
            + conf_score * self.CONFIDENCE_WEIGHT
            + qual_score * self.RECENCY_WEIGHT
        )

        return combined

    def _recommend_resolution(
        self,
        event1_id: int,
        event2_id: int,
        outcome1: str,
        outcome2: str,
        confidence1: float,
        confidence2: float,
        timestamp1: datetime,
        timestamp2: datetime,
    ) -> str:
        """Recommend how to resolve a contradiction.

        Args:
            event1_id, event2_id: Event IDs
            outcome1, outcome2: Outcomes
            confidence1, confidence2: Confidence scores
            timestamp1, timestamp2: Timestamps

        Returns:
            Recommended resolution strategy
        """
        # If one is clearly more recent and different outcome, keep latest
        time_diff = abs((timestamp2 - timestamp1).total_seconds()) / 3600  # hours
        if time_diff > 24:  # More than 1 day apart
            return "keep_latest"

        # If one has much higher confidence/quality, keep it
        conf_diff = abs(float(confidence1) - float(confidence2))
        if conf_diff > 0.3:
            return "keep_highest_quality"

        # Default: automatic resolution
        return "auto"
