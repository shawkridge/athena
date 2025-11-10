"""Learning pathways for AI Coordination to Memory-MCP integration.

Defines the flow of learning from execution traces through consolidation
to semantic patterns and procedures.

Pathways:
1. ExecutionTrace → EpisodicEvent → Consolidation → SemanticPattern
2. ThinkingTrace → SemanticPattern (direct, reasoning patterns)
3. ActionCycle lessons → Procedural templates
"""

import json
from datetime import datetime
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from athena.core.database import Database
    from athena.episodic.store import EpisodicStore


class LearningPathway:
    """Manages learning pathways from execution to knowledge.

    Purpose:
    - Define how AI Coordination data flows to Memory-MCP
    - Track learning progression (episodic → semantic → procedural)
    - Enable analysis of what was learned from which events
    - Support feedback on learning effectiveness
    """

    def __init__(self, db: "Database"):
        """Initialize LearningPathway.

        Args:
            db: Database connection
        """
        self.db = db
        self._ensure_schema()

    def _ensure_schema(self):
        """Create learning pathway tables."""
        cursor = self.db.get_cursor()

        # Table: Learning pathways (tracks progression)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learning_pathways (
                id INTEGER PRIMARY KEY,
                session_id TEXT NOT NULL,
                pathway_type TEXT NOT NULL,  -- execution, thinking, action_cycle
                source_id TEXT NOT NULL,
                source_type TEXT NOT NULL,
                episodic_id INTEGER,
                semantic_id INTEGER,
                procedural_id INTEGER,
                confidence REAL DEFAULT 0.5,
                created_at INTEGER NOT NULL,
                consolidated_at INTEGER,
                status TEXT DEFAULT 'active'  -- active, consolidated, archived
            )
        """)

        # Table: Pathway metrics (learning effectiveness)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pathway_metrics (
                id INTEGER PRIMARY KEY,
                pathway_id INTEGER NOT NULL,
                metric_name TEXT NOT NULL,
                metric_value REAL,
                recorded_at INTEGER NOT NULL,
                FOREIGN KEY (pathway_id) REFERENCES learning_pathways(id)
            )
        """)

        # Indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_learning_pathways_session
            ON learning_pathways(session_id, status)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_learning_pathways_source
            ON learning_pathways(source_type, source_id)
        """)

        # commit handled by cursor context

    def create_execution_pathway(
        self,
        session_id: str,
        source_id: str,
        episodic_event_id: int,
        confidence: float = 0.8
    ) -> int:
        """Create learning pathway for execution trace.

        Pathway: ExecutionTrace → EpisodicEvent → (future) Consolidation → SemanticPattern

        Args:
            session_id: Session identifier
            source_id: ExecutionTrace ID
            episodic_event_id: Corresponding episodic event ID
            confidence: Confidence in this pathway (0.0-1.0)

        Returns:
            Pathway ID
        """
        cursor = self.db.get_cursor()
        now = int(datetime.now().timestamp() * 1000)

        cursor.execute("""
            INSERT INTO learning_pathways
            (session_id, pathway_type, source_id, source_type, episodic_id,
             confidence, created_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session_id,
            "execution",
            source_id,
            "ExecutionTrace",
            episodic_event_id,
            min(confidence, 1.0),
            now,
            "active"
        ))

        pathway_id = cursor.lastrowid
        # commit handled by cursor context
        return pathway_id

    def create_thinking_pathway(
        self,
        session_id: str,
        source_id: str,
        semantic_pattern_id: Optional[int] = None,
        confidence: float = 0.9
    ) -> int:
        """Create learning pathway for thinking trace.

        Pathway: ThinkingTrace → SemanticPattern (direct)

        Args:
            session_id: Session identifier
            source_id: ThinkingTrace ID
            semantic_pattern_id: Optional semantic pattern ID
            confidence: Confidence in this pathway (0.0-1.0)

        Returns:
            Pathway ID
        """
        cursor = self.db.get_cursor()
        now = int(datetime.now().timestamp() * 1000)

        cursor.execute("""
            INSERT INTO learning_pathways
            (session_id, pathway_type, source_id, source_type, semantic_id,
             confidence, created_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session_id,
            "thinking",
            source_id,
            "ThinkingTrace",
            semantic_pattern_id,
            min(confidence, 1.0),
            now,
            "active"
        ))

        pathway_id = cursor.lastrowid
        # commit handled by cursor context
        return pathway_id

    def create_action_cycle_pathway(
        self,
        session_id: str,
        source_id: str,
        procedural_id: Optional[int] = None,
        confidence: float = 0.7
    ) -> int:
        """Create learning pathway for action cycle.

        Pathway: ActionCycle → Procedural template

        Args:
            session_id: Session identifier
            source_id: ActionCycle ID
            procedural_id: Optional procedural memory ID
            confidence: Confidence in this pathway (0.0-1.0)

        Returns:
            Pathway ID
        """
        cursor = self.db.get_cursor()
        now = int(datetime.now().timestamp() * 1000)

        cursor.execute("""
            INSERT INTO learning_pathways
            (session_id, pathway_type, source_id, source_type, procedural_id,
             confidence, created_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session_id,
            "action_cycle",
            source_id,
            "ActionCycle",
            procedural_id,
            min(confidence, 1.0),
            now,
            "active"
        ))

        pathway_id = cursor.lastrowid
        # commit handled by cursor context
        return pathway_id

    def link_to_semantic(
        self,
        pathway_id: int,
        semantic_id: int
    ) -> bool:
        """Link pathway to extracted semantic pattern.

        Args:
            pathway_id: Pathway ID
            semantic_id: Semantic memory ID

        Returns:
            Success status
        """
        cursor = self.db.get_cursor()

        cursor.execute("""
            UPDATE learning_pathways
            SET semantic_id = ?, status = ?
            WHERE id = ?
        """, (semantic_id, "consolidated", pathway_id))

        # commit handled by cursor context
        return cursor.rowcount > 0

    def link_to_procedural(
        self,
        pathway_id: int,
        procedural_id: int
    ) -> bool:
        """Link pathway to created procedure.

        Args:
            pathway_id: Pathway ID
            procedural_id: Procedural memory ID

        Returns:
            Success status
        """
        cursor = self.db.get_cursor()

        cursor.execute("""
            UPDATE learning_pathways
            SET procedural_id = ?
            WHERE id = ?
        """, (procedural_id, pathway_id))

        # commit handled by cursor context
        return cursor.rowcount > 0

    def mark_consolidated(self, pathway_id: int) -> bool:
        """Mark pathway as consolidated.

        Args:
            pathway_id: Pathway ID

        Returns:
            Success status
        """
        cursor = self.db.get_cursor()
        now = int(datetime.now().timestamp() * 1000)

        cursor.execute("""
            UPDATE learning_pathways
            SET consolidated_at = ?, status = ?
            WHERE id = ?
        """, (now, "consolidated", pathway_id))

        # commit handled by cursor context
        return cursor.rowcount > 0

    def get_pathway(self, pathway_id: int) -> Optional[dict]:
        """Get pathway details.

        Args:
            pathway_id: Pathway ID

        Returns:
            Pathway dict or None
        """
        cursor = self.db.get_cursor()

        cursor.execute("""
            SELECT id, session_id, pathway_type, source_id, source_type,
                   episodic_id, semantic_id, procedural_id, confidence,
                   created_at, consolidated_at, status
            FROM learning_pathways
            WHERE id = ?
        """, (pathway_id,))

        row = cursor.fetchone()
        if not row:
            return None

        return {
            "id": row[0],
            "session_id": row[1],
            "pathway_type": row[2],
            "source_id": row[3],
            "source_type": row[4],
            "episodic_id": row[5],
            "semantic_id": row[6],
            "procedural_id": row[7],
            "confidence": row[8],
            "created_at": row[9],
            "consolidated_at": row[10],
            "status": row[11],
        }

    def get_session_pathways(self, session_id: str, status: Optional[str] = None) -> list[dict]:
        """Get learning pathways for a session.

        Args:
            session_id: Session identifier
            status: Optional filter by status

        Returns:
            List of pathway dicts
        """
        cursor = self.db.get_cursor()

        if status:
            cursor.execute("""
                SELECT id, pathway_type, source_type, confidence, status
                FROM learning_pathways
                WHERE session_id = ? AND status = ?
                ORDER BY created_at DESC
            """, (session_id, status))
        else:
            cursor.execute("""
                SELECT id, pathway_type, source_type, confidence, status
                FROM learning_pathways
                WHERE session_id = ?
                ORDER BY created_at DESC
            """, (session_id,))

        pathways = []
        for row in cursor.fetchall():
            pathways.append({
                "id": row[0],
                "pathway_type": row[1],
                "source_type": row[2],
                "confidence": row[3],
                "status": row[4],
            })

        return pathways

    def record_pathway_metric(
        self,
        pathway_id: int,
        metric_name: str,
        metric_value: float
    ) -> int:
        """Record a metric for pathway effectiveness.

        Args:
            pathway_id: Pathway ID
            metric_name: Name of metric (e.g., "reuse_count", "success_rate")
            metric_value: Metric value

        Returns:
            Metric ID
        """
        cursor = self.db.get_cursor()
        now = int(datetime.now().timestamp() * 1000)

        cursor.execute("""
            INSERT INTO pathway_metrics
            (pathway_id, metric_name, metric_value, recorded_at)
            VALUES (?, ?, ?, ?)
        """, (pathway_id, metric_name, metric_value, now))

        metric_id = cursor.lastrowid
        # commit handled by cursor context
        return metric_id

    def get_pathway_metrics(self, pathway_id: int) -> dict:
        """Get all metrics for a pathway.

        Args:
            pathway_id: Pathway ID

        Returns:
            Metrics dict
        """
        cursor = self.db.get_cursor()

        cursor.execute("""
            SELECT metric_name, AVG(metric_value), COUNT(*), MAX(recorded_at)
            FROM pathway_metrics
            WHERE pathway_id = ?
            GROUP BY metric_name
        """, (pathway_id,))

        metrics = {}
        for row in cursor.fetchall():
            metrics[row[0]] = {
                "average": row[1],
                "count": row[2],
                "last_recorded": row[3],
            }

        return metrics

    def get_learning_effectiveness(self, session_id: str) -> dict:
        """Get overall learning effectiveness for a session.

        Args:
            session_id: Session identifier

        Returns:
            Effectiveness metrics dict
        """
        cursor = self.db.get_cursor()

        # Count pathways by type
        cursor.execute("""
            SELECT pathway_type, COUNT(*), AVG(confidence)
            FROM learning_pathways
            WHERE session_id = ?
            GROUP BY pathway_type
        """, (session_id,))

        pathway_summary = {}
        total_pathways = 0
        for row in cursor.fetchall():
            pathway_summary[row[0]] = {
                "count": row[1],
                "average_confidence": row[2],
            }
            total_pathways += row[1]

        # Count consolidated pathways
        cursor.execute("""
            SELECT COUNT(*), AVG(confidence)
            FROM learning_pathways
            WHERE session_id = ? AND status = 'consolidated'
        """, (session_id,))

        row = cursor.fetchone()
        consolidated_count = row[0] or 0
        consolidated_confidence = row[1] or 0

        consolidation_rate = (consolidated_count / total_pathways * 100) if total_pathways > 0 else 0

        return {
            "session_id": session_id,
            "total_pathways": total_pathways,
            "pathway_types": pathway_summary,
            "consolidated_count": consolidated_count,
            "consolidation_rate": consolidation_rate,
            "average_consolidated_confidence": consolidated_confidence,
        }
