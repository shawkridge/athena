"""Database storage for consciousness measurements.

Stores consciousness indicator measurements and scores in PostgreSQL,
enabling historical tracking and analysis.
"""

import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging

from athena.core.database import Database
from athena.consciousness.metrics import ConsciousnessScore

logger = logging.getLogger(__name__)


class ConsciousnessStore:
    """Store consciousness measurements in database.

    Manages persistent storage and retrieval of consciousness scores,
    indicators, and historical data.
    """

    def __init__(self, db: Database):
        """Initialize consciousness store.

        Args:
            db: Database instance for operations
        """
        self.db = db

    async def _ensure_schema(self) -> None:
        """Ensure database schema exists (idempotent)."""
        await self.db.initialize()

        # Main consciousness measurements table
        await self.db.initialize()
        async with self.db.get_connection() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS consciousness_measurements (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    session_id VARCHAR(255),
                    overall_score FLOAT NOT NULL,
                    trend VARCHAR(50),
                    confidence FLOAT,
                    indicators_json JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            # Individual indicator scores table
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS consciousness_indicators (
                    id SERIAL PRIMARY KEY,
                    measurement_id INTEGER NOT NULL,
                    indicator_name VARCHAR(255) NOT NULL,
                    score FLOAT NOT NULL,
                    confidence FLOAT,
                    components_json JSONB,
                    evidence_json JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (measurement_id) REFERENCES consciousness_measurements(id) ON DELETE CASCADE
                )
                """
            )

            # Consciousness trends table (for trend analysis)
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS consciousness_trends (
                    id SERIAL PRIMARY KEY,
                    session_id VARCHAR(255),
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    measurement_count INTEGER,
                    average_score FLOAT,
                    min_score FLOAT,
                    max_score FLOAT,
                    trend_direction VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            await conn.commit()

        logger.info("Consciousness database schema initialized")

    async def store_measurement(
        self,
        score: ConsciousnessScore,
        session_id: Optional[str] = None,
    ) -> int:
        """Store a consciousness measurement.

        Args:
            score: ConsciousnessScore to store
            session_id: Optional session identifier

        Returns:
            ID of stored measurement
        """
        await self._ensure_schema()

        # Serialize indicators to JSON
        indicators_json = json.dumps(
            {
                name: {
                    "score": indicator.score,
                    "confidence": indicator.confidence,
                    "components": indicator.components,
                    "evidence": indicator.evidence,
                }
                for name, indicator in score.indicators.items()
            }
        )

        async with self.db.get_connection() as conn:
            # Insert main measurement
            result = await conn.execute(
                """
                INSERT INTO consciousness_measurements
                (timestamp, session_id, overall_score, trend, confidence, indicators_json)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    score.timestamp,
                    session_id,
                    score.overall_score,
                    score.trend,
                    score.confidence,
                    indicators_json,
                ),
            )
            measurement_id = (await result.fetchone())[0]

            # Insert individual indicators
            for indicator_name, indicator in score.indicators.items():
                components_json = json.dumps(indicator.components)
                evidence_json = json.dumps(indicator.evidence)

                await conn.execute(
                    """
                    INSERT INTO consciousness_indicators
                    (measurement_id, indicator_name, score, confidence, components_json, evidence_json)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        measurement_id,
                        indicator_name,
                        indicator.score,
                        indicator.confidence,
                        components_json,
                        evidence_json,
                    ),
                )

            await conn.commit()

        return measurement_id

    async def get_measurement(self, measurement_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific measurement.

        Args:
            measurement_id: ID of measurement to retrieve

        Returns:
            Measurement data or None if not found
        """
        await self.db.initialize()

        async with self.db.get_connection() as conn:
            result = await conn.execute(
                """
                SELECT id, timestamp, session_id, overall_score, trend, confidence, indicators_json
                FROM consciousness_measurements
                WHERE id = %s
                """,
                (measurement_id,),
            )
            row = await result.fetchone()

        if not row:
            return None

        return {
            "id": row[0],
            "timestamp": row[1].isoformat(),
            "session_id": row[2],
            "overall_score": row[3],
            "trend": row[4],
            "confidence": row[5],
            "indicators": json.loads(row[6]),
        }

    async def get_recent_measurements(
        self,
        limit: int = 100,
        session_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get recent consciousness measurements.

        Args:
            limit: Maximum number of measurements to return
            session_id: Optional session filter

        Returns:
            List of measurement data
        """
        await self.db.initialize()

        async with self.db.get_connection() as conn:
            if session_id:
                result = await conn.execute(
                    """
                    SELECT id, timestamp, session_id, overall_score, trend, confidence, indicators_json
                    FROM consciousness_measurements
                    WHERE session_id = %s
                    ORDER BY timestamp DESC
                    LIMIT %s
                    """,
                    (session_id, limit),
                )
            else:
                result = await conn.execute(
                    """
                    SELECT id, timestamp, session_id, overall_score, trend, confidence, indicators_json
                    FROM consciousness_measurements
                    ORDER BY timestamp DESC
                    LIMIT %s
                    """,
                    (limit,),
                )

            rows = await result.fetchall()

        return [
            {
                "id": row[0],
                "timestamp": row[1].isoformat(),
                "session_id": row[2],
                "overall_score": row[3],
                "trend": row[4],
                "confidence": row[5],
                "indicators": json.loads(row[6]),
            }
            for row in rows
        ]

    async def get_measurements_in_range(
        self,
        start_time: datetime,
        end_time: datetime,
        session_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get measurements in a time range.

        Args:
            start_time: Start of range
            end_time: End of range
            session_id: Optional session filter

        Returns:
            List of measurements in range
        """
        await self.db.initialize()

        async with self.db.get_connection() as conn:
            if session_id:
                result = await conn.execute(
                    """
                    SELECT id, timestamp, session_id, overall_score, trend, confidence, indicators_json
                    FROM consciousness_measurements
                    WHERE timestamp >= %s AND timestamp <= %s AND session_id = %s
                    ORDER BY timestamp ASC
                    """,
                    (start_time, end_time, session_id),
                )
            else:
                result = await conn.execute(
                    """
                    SELECT id, timestamp, session_id, overall_score, trend, confidence, indicators_json
                    FROM consciousness_measurements
                    WHERE timestamp >= %s AND timestamp <= %s
                    ORDER BY timestamp ASC
                    """,
                    (start_time, end_time),
                )

            rows = await result.fetchall()

        return [
            {
                "id": row[0],
                "timestamp": row[1].isoformat(),
                "session_id": row[2],
                "overall_score": row[3],
                "trend": row[4],
                "confidence": row[5],
                "indicators": json.loads(row[6]),
            }
            for row in rows
        ]

    async def get_indicator_statistics(
        self,
        indicator_name: str,
        limit: int = 100,
    ) -> Optional[Dict[str, Any]]:
        """Get statistics for a specific indicator.

        Args:
            indicator_name: Name of indicator (e.g., "global_workspace")
            limit: Number of recent measurements to analyze

        Returns:
            Statistics dictionary or None if no data
        """
        await self.db.initialize()

        async with self.db.get_connection() as conn:
            result = await conn.execute(
                """
                SELECT score, confidence
                FROM consciousness_indicators
                WHERE indicator_name = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (indicator_name, limit),
            )
            rows = await result.fetchall()

        if not rows:
            return None

        scores = [row[0] for row in rows]
        confidences = [row[1] for row in rows]

        return {
            "indicator": indicator_name,
            "measurements": len(scores),
            "average": round(sum(scores) / len(scores), 2),
            "min": round(min(scores), 2),
            "max": round(max(scores), 2),
            "current": round(scores[0], 2),  # Most recent
            "average_confidence": round(sum(confidences) / len(confidences), 2),
        }

    async def get_all_indicators_statistics(self, limit: int = 100) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all indicators.

        Args:
            limit: Number of recent measurements to analyze

        Returns:
            Dictionary with statistics for each indicator
        """
        indicators = [
            "global_workspace",
            "information_integration",
            "selective_attention",
            "working_memory",
            "meta_cognition",
            "temporal_continuity",
        ]

        stats = {}
        for indicator_name in indicators:
            stat = await self.get_indicator_statistics(indicator_name, limit)
            if stat:
                stats[indicator_name] = stat

        return stats

    async def get_consciousness_trend(
        self,
        time_window: timedelta,
        session_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Analyze consciousness trend over time.

        Args:
            time_window: Time period to analyze
            session_id: Optional session filter

        Returns:
            Trend analysis or None if insufficient data
        """
        end_time = datetime.now()
        start_time = end_time - time_window

        measurements = await self.get_measurements_in_range(start_time, end_time, session_id)

        if len(measurements) < 2:
            return None

        scores = [m["overall_score"] for m in measurements]

        # Calculate trend
        if scores[-1] > scores[0] + 0.5:
            direction = "increasing"
        elif scores[0] > scores[-1] + 0.5:
            direction = "decreasing"
        else:
            direction = "stable"

        return {
            "time_window": str(time_window),
            "measurements": len(measurements),
            "start_score": round(scores[0], 2),
            "end_score": round(scores[-1], 2),
            "average": round(sum(scores) / len(scores), 2),
            "min": round(min(scores), 2),
            "max": round(max(scores), 2),
            "direction": direction,
            "change": round(scores[-1] - scores[0], 2),
        }

    async def delete_old_measurements(self, days_old: int = 30) -> int:
        """Delete measurements older than specified days.

        Args:
            days_old: Delete measurements older than this many days

        Returns:
            Number of measurements deleted
        """
        await self.db.initialize()

        cutoff_date = datetime.now() - timedelta(days=days_old)

        async with self.db.get_connection() as conn:
            result = await conn.execute(
                """
                DELETE FROM consciousness_measurements
                WHERE timestamp < %s
                """,
                (cutoff_date,),
            )
            deleted_count = result.rowcount
            await conn.commit()

        logger.info(f"Deleted {deleted_count} old consciousness measurements")
        return deleted_count

    async def clear_all(self) -> None:
        """Clear all consciousness data (for testing/reset)."""
        await self.db.initialize()

        async with self.db.get_connection() as conn:
            await conn.execute("DELETE FROM consciousness_indicators")
            await conn.execute("DELETE FROM consciousness_measurements")
            await conn.execute("DELETE FROM consciousness_trends")
            await conn.commit()

        logger.info("Cleared all consciousness data")

    async def get_summary(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Get summary statistics for consciousness measurements.

        Args:
            session_id: Optional session filter

        Returns:
            Summary statistics
        """
        await self.db.initialize()

        async with self.db.get_connection() as conn:
            if session_id:
                result = await conn.execute(
                    """
                    SELECT COUNT(*), AVG(overall_score), MIN(overall_score), MAX(overall_score)
                    FROM consciousness_measurements
                    WHERE session_id = %s
                    """,
                    (session_id,),
                )
            else:
                result = await conn.execute(
                    """
                    SELECT COUNT(*), AVG(overall_score), MIN(overall_score), MAX(overall_score)
                    FROM consciousness_measurements
                    """
                )
            row = await result.fetchone()

        if not row or row[0] == 0:
            return {
                "measurements": 0,
                "average_score": 0.0,
                "min_score": 0.0,
                "max_score": 0.0,
            }

        return {
            "measurements": row[0],
            "average_score": round(float(row[1]), 2),
            "min_score": round(float(row[2]), 2),
            "max_score": round(float(row[3]), 2),
        }
