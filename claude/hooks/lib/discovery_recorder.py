"""Discovery event recorder for capturing analysis, insights, and learnings.

This module handles recording discovery events - high-level learnings that
emerge during a session. Unlike tool_execution events (low-level), discovery
events capture the actual insights and analyses.

Implements Anthropic's code-execution pattern: discover → execute → summarize
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional, List

logger = logging.getLogger(__name__)


class DiscoveryRecorder:
    """Records discovery events to memory."""

    def __init__(self):
        """Initialize with database connection."""
        self.conn = None
        self._connect()

    def _connect(self):
        """Connect to PostgreSQL database."""
        import psycopg

        try:
            self.conn = psycopg.connect(
                host=os.environ.get("ATHENA_POSTGRES_HOST", "localhost"),
                port=int(os.environ.get("ATHENA_POSTGRES_PORT", "5432")),
                dbname=os.environ.get("ATHENA_POSTGRES_DB", "athena"),
                user=os.environ.get("ATHENA_POSTGRES_USER", "postgres"),
                password=os.environ.get("ATHENA_POSTGRES_PASSWORD", "postgres"),
            )
            logger.debug("Connected to PostgreSQL for discovery recording")
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()

    def record_discovery(
        self,
        project_id: int,
        title: str,
        description: str,
        discovery_type: str = "analysis",
        context: Optional[Dict[str, Any]] = None,
        impact_level: str = "medium",
    ) -> Optional[int]:
        """Record a discovery event.

        Args:
            project_id: Project ID
            title: Short title of the discovery
            description: Full description of the insight/learning
            discovery_type: Type of discovery (analysis, insight, finding, gap, pattern, etc.)
            context: Optional context dict (tags, related_events, etc.)
            impact_level: Level of impact (low, medium, high, critical)

        Returns:
            Event ID or None if failed
        """
        try:
            cursor = self.conn.cursor()
            timestamp = int(datetime.now().timestamp() * 1000)

            # Build content with title and description
            content = f"{title}\n\n{description}"
            if context:
                content += f"\n\nContext: {json.dumps(context)}"

            cursor.execute(
                """
                INSERT INTO episodic_events
                (project_id, event_type, content, timestamp, outcome,
                 consolidation_status, importance_score, session_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    project_id,
                    f"discovery:{discovery_type}",  # e.g., "discovery:analysis"
                    content,
                    timestamp,
                    impact_level,  # outcome field stores impact level
                    "unconsolidated",
                    0.8,  # Discoveries default to high importance
                    self._get_session_id(),
                ),
            )

            result = cursor.fetchone()
            self.conn.commit()

            if result:
                return result[0]
            return None

        except Exception as e:
            logger.warning(f"Error recording discovery: {e}")
            if self.conn:
                self.conn.rollback()
            return None

    def record_analysis(
        self, project_id: int, analysis_title: str, findings: str, impact: str = "medium"
    ) -> Optional[int]:
        """Convenience method for recording analysis discoveries."""
        return self.record_discovery(
            project_id=project_id,
            title=analysis_title,
            description=findings,
            discovery_type="analysis",
            impact_level=impact,
        )

    def record_insight(
        self, project_id: int, insight_title: str, detail: str, impact: str = "medium"
    ) -> Optional[int]:
        """Convenience method for recording insights."""
        return self.record_discovery(
            project_id=project_id,
            title=insight_title,
            description=detail,
            discovery_type="insight",
            impact_level=impact,
        )

    def record_gap(
        self, project_id: int, gap_title: str, description: str, impact: str = "high"
    ) -> Optional[int]:
        """Convenience method for recording discovered gaps."""
        return self.record_discovery(
            project_id=project_id,
            title=gap_title,
            description=description,
            discovery_type="gap",
            impact_level=impact,
        )

    def record_pattern(
        self, project_id: int, pattern_title: str, evidence: str, impact: str = "high"
    ) -> Optional[int]:
        """Convenience method for recording discovered patterns."""
        return self.record_discovery(
            project_id=project_id,
            title=pattern_title,
            description=evidence,
            discovery_type="pattern",
            impact_level=impact,
        )

    def get_session_discoveries(
        self, project_id: int, session_id: Optional[str] = None, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get discoveries from this session.

        Args:
            project_id: Project ID
            session_id: Optional specific session ID (default: current session)
            limit: Maximum to return

        Returns:
            List of discovery events
        """
        try:
            cursor = self.conn.cursor()

            if session_id is None:
                session_id = self._get_session_id()

            cursor.execute(
                """
                SELECT id, event_type, content, timestamp, outcome
                FROM episodic_events
                WHERE project_id = %s
                  AND session_id = %s
                  AND event_type LIKE 'discovery:%'
                ORDER BY timestamp DESC
                LIMIT %s
                """,
                (project_id, session_id, limit),
            )

            rows = cursor.fetchall()

            return [
                {
                    "id": row[0],
                    "type": row[1],
                    "content": row[2],
                    "timestamp": row[3],
                    "impact": row[4],
                }
                for row in rows
            ]

        except Exception as e:
            logger.warning(f"Error getting session discoveries: {e}")
            return []

    @staticmethod
    def _get_session_id() -> str:
        """Get or create session ID from environment."""
        import uuid

        session_id = os.environ.get("CLAUDE_SESSION_ID")
        if not session_id:
            session_id = str(uuid.uuid4())[:8]
            os.environ["CLAUDE_SESSION_ID"] = session_id
        return session_id


# Convenience function for standalone use
def record_discovery(
    project_id: int,
    title: str,
    description: str,
    discovery_type: str = "analysis",
    impact_level: str = "medium",
) -> Optional[int]:
    """Standalone function to record a discovery."""
    try:
        recorder = DiscoveryRecorder()
        event_id = recorder.record_discovery(
            project_id=project_id,
            title=title,
            description=description,
            discovery_type=discovery_type,
            impact_level=impact_level,
        )
        recorder.close()
        return event_id
    except Exception as e:
        logger.error(f"Failed to record discovery: {e}")
        return None
