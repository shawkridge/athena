"""Meta-memory storage and quality tracking."""

import json
from datetime import datetime
from typing import Optional

from ..core.database import Database
from ..core.base_store import BaseStore
from .models import DomainCoverage, ExpertiseLevel, KnowledgeTransfer, MemoryQuality


class MetaMemoryStore(BaseStore):
    """Manages meta-memory for quality and domain tracking."""

    table_name = "domain_coverage"
    model_class = DomainCoverage

    def __init__(self, db: Database):
        """Initialize meta-memory store.

        Args:
            db: Database instance
        """
        super().__init__(db)
        self._ensure_schema()

    def _row_to_model(self, row) -> DomainCoverage:
        """Convert database row to DomainCoverage model.

        Args:
            row: Database row (sqlite3.Row or dict)

        Returns:
            DomainCoverage instance
        """
        # Convert Row to dict if needed
        row_dict = dict(row) if hasattr(row, 'keys') else row
        return self._row_to_domain(row_dict)

    def _ensure_schema(self):
        """Ensure meta-memory tables exist."""

        # For PostgreSQL async databases, skip sync schema initialization
        if not hasattr(self.db, 'conn'):
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"{self.__class__.__name__}: PostgreSQL async database detected. Schema management handled by _init_schema().")
            return
        cursor = self.db.get_cursor()

        # Memory quality table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory_quality (
                memory_id INTEGER NOT NULL,
                memory_layer TEXT NOT NULL,

                access_count INTEGER DEFAULT 0,
                last_accessed INTEGER,
                useful_count INTEGER DEFAULT 0,

                usefulness_score REAL DEFAULT 0.0,
                confidence REAL DEFAULT 1.0,
                relevance_decay REAL DEFAULT 1.0,

                source TEXT DEFAULT 'user',
                verified BOOLEAN DEFAULT 0,

                PRIMARY KEY (memory_id, memory_layer)
            )
        """)

        # Domain coverage table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS domain_coverage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT UNIQUE NOT NULL,
                category TEXT NOT NULL,

                memory_count INTEGER DEFAULT 0,
                episodic_count INTEGER DEFAULT 0,
                procedural_count INTEGER DEFAULT 0,
                entity_count INTEGER DEFAULT 0,

                avg_confidence REAL DEFAULT 0.0,
                avg_usefulness REAL DEFAULT 0.0,
                last_updated INTEGER,

                gaps TEXT,
                strength_areas TEXT,

                first_encounter INTEGER,
                expertise_level TEXT DEFAULT 'beginner'
            )
        """)

        # Knowledge transfer table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_transfers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_project_id INTEGER NOT NULL,
                to_project_id INTEGER NOT NULL,
                knowledge_item_id INTEGER NOT NULL,
                knowledge_layer TEXT NOT NULL,
                transferred_at INTEGER NOT NULL,
                applicability_score REAL DEFAULT 0.0
            )
        """)

        # Indices
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_quality_layer ON memory_quality(memory_layer)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_quality_usefulness ON memory_quality(usefulness_score)"
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_domain_category ON domain_coverage(category)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_transfer_from ON knowledge_transfers(from_project_id)"
        )

        # commit handled by cursor context

    def record_access(self, memory_id: int, memory_layer: str, useful: bool = False):
        """Record a memory access.

        Args:
            memory_id: Memory ID
            memory_layer: Memory layer (semantic, episodic, etc.)
            useful: Whether the access was useful
        """
        now = self.now_timestamp()

        # Get or create quality record
        self.execute(
            """
            INSERT INTO memory_quality (memory_id, memory_layer, access_count, useful_count, last_accessed)
            VALUES (?, ?, 1, ?, ?)
            ON CONFLICT(memory_id, memory_layer) DO UPDATE SET
                access_count = access_count + 1,
                useful_count = useful_count + ?,
                last_accessed = ?
        """,
            (
                memory_id,
                memory_layer,
                1 if useful else 0,
                now,
                1 if useful else 0,
                now,
            ),
        )

        # Update usefulness score
        self.execute(
            """
            UPDATE memory_quality
            SET usefulness_score = CAST(useful_count AS REAL) / access_count
            WHERE memory_id = ? AND memory_layer = ?
        """,
            (memory_id, memory_layer),
        )

        self.commit()

    def get_quality(self, memory_id: int, memory_layer: str) -> Optional[MemoryQuality]:
        """Get quality metrics for a memory.

        Args:
            memory_id: Memory ID
            memory_layer: Memory layer

        Returns:
            MemoryQuality if found, None otherwise
        """
        row = self.execute(
            """
            SELECT * FROM memory_quality
            WHERE memory_id = ? AND memory_layer = ?
        """,
            (memory_id, memory_layer),
            fetch_one=True
        )

        return self._row_to_quality(row) if row else None

    def update_confidence(self, memory_id: int, memory_layer: str, confidence: float):
        """Update confidence score for a memory.

        Args:
            memory_id: Memory ID
            memory_layer: Memory layer
            confidence: New confidence score (0-1)
        """
        self.execute(
            """
            INSERT INTO memory_quality (memory_id, memory_layer, confidence)
            VALUES (?, ?, ?)
            ON CONFLICT(memory_id, memory_layer) DO UPDATE SET
                confidence = ?
        """,
            (memory_id, memory_layer, confidence, confidence),
        )
        self.commit()

    def get_low_quality_memories(
        self, memory_layer: Optional[str] = None, threshold: float = 0.3, limit: int = 50
    ) -> list[MemoryQuality]:
        """Get memories with low usefulness scores.

        Args:
            memory_layer: Optional layer filter
            threshold: Maximum usefulness score
            limit: Maximum results

        Returns:
            List of low-quality memories
        """
        sql = """
            SELECT * FROM memory_quality
            WHERE usefulness_score < ? AND access_count >= 5
        """
        params = [threshold]

        if memory_layer:
            sql += " AND memory_layer = ?"
            params.append(memory_layer)

        sql += " ORDER BY usefulness_score ASC, access_count DESC LIMIT ?"
        params.append(limit)

        rows = self.execute(sql, tuple(params), fetch_all=True)
        return [self._row_to_quality(row) for row in rows]

    def create_domain(self, domain: DomainCoverage) -> int:
        """Create or update a domain.

        Args:
            domain: Domain coverage data

        Returns:
            Domain ID
        """
        expertise_str = (
            domain.expertise_level.value
            if isinstance(domain.expertise_level, ExpertiseLevel)
            else domain.expertise_level
        )

        last_updated_ts = int(domain.last_updated.timestamp()) if domain.last_updated else self.now_timestamp()
        first_encounter_ts = int(domain.first_encounter.timestamp()) if domain.first_encounter else self.now_timestamp()

        cursor = self.execute(
            """
            INSERT INTO domain_coverage (
                domain, category,
                memory_count, episodic_count, procedural_count, entity_count,
                avg_confidence, avg_usefulness, last_updated,
                gaps, strength_areas,
                first_encounter, expertise_level
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(domain) DO UPDATE SET
                memory_count = ?,
                episodic_count = ?,
                procedural_count = ?,
                entity_count = ?,
                avg_confidence = ?,
                avg_usefulness = ?,
                last_updated = ?,
                gaps = ?,
                strength_areas = ?,
                expertise_level = ?
        """,
            (
                domain.domain,
                domain.category,
                domain.memory_count,
                domain.episodic_count,
                domain.procedural_count,
                domain.entity_count,
                domain.avg_confidence,
                domain.avg_usefulness,
                last_updated_ts,
                json.dumps(domain.gaps),
                json.dumps(domain.strength_areas),
                first_encounter_ts,
                expertise_str,
                # ON CONFLICT updates
                domain.memory_count,
                domain.episodic_count,
                domain.procedural_count,
                domain.entity_count,
                domain.avg_confidence,
                domain.avg_usefulness,
                last_updated_ts,
                json.dumps(domain.gaps),
                json.dumps(domain.strength_areas),
                expertise_str,
            ),
        )
        self.commit()

        if cursor.lastrowid:
            return cursor.lastrowid

        # Get existing ID
        row = self.execute(
            "SELECT id FROM domain_coverage WHERE domain = ?",
            (domain.domain,),
            fetch_one=True
        )
        return row[0] if row else 0

    def get_domain(self, domain_name: str) -> Optional[DomainCoverage]:
        """Get domain coverage data.

        Args:
            domain_name: Domain name

        Returns:
            DomainCoverage if found, None otherwise
        """
        row = self.execute(
            "SELECT * FROM domain_coverage WHERE domain = ?",
            (domain_name,),
            fetch_one=True
        )
        return self._row_to_domain(row) if row else None

    def list_domains(self, category: Optional[str] = None, limit: int = 50) -> list[DomainCoverage]:
        """List domains with optional filtering.

        Args:
            category: Optional category filter
            limit: Maximum results

        Returns:
            List of domains
        """
        sql = "SELECT * FROM domain_coverage WHERE 1=1"
        params = []

        if category:
            sql += " AND category = ?"
            params.append(category)

        sql += " ORDER BY memory_count DESC, avg_usefulness DESC LIMIT ?"
        params.append(limit)

        rows = self.execute(sql, tuple(params), fetch_all=True)
        return [self._row_to_domain(row) for row in rows]

    def record_transfer(self, transfer: KnowledgeTransfer) -> int:
        """Record a knowledge transfer between projects.

        Args:
            transfer: Transfer data

        Returns:
            Transfer ID
        """
        cursor = self.execute(
            """
            INSERT INTO knowledge_transfers (
                from_project_id, to_project_id,
                knowledge_item_id, knowledge_layer,
                transferred_at, applicability_score
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                transfer.from_project_id,
                transfer.to_project_id,
                transfer.knowledge_item_id,
                transfer.knowledge_layer,
                int(transfer.transferred_at.timestamp()),
                transfer.applicability_score,
            ),
        )
        self.commit()
        return cursor.lastrowid

    def get_transfers(
        self, from_project_id: Optional[int] = None, to_project_id: Optional[int] = None
    ) -> list[KnowledgeTransfer]:
        """Get knowledge transfers.

        Args:
            from_project_id: Optional source project filter
            to_project_id: Optional destination project filter

        Returns:
            List of transfers
        """
        sql = "SELECT * FROM knowledge_transfers WHERE 1=1"
        params = []

        if from_project_id is not None:
            sql += " AND from_project_id = ?"
            params.append(from_project_id)

        if to_project_id is not None:
            sql += " AND to_project_id = ?"
            params.append(to_project_id)

        sql += " ORDER BY transferred_at DESC"

        rows = self.execute(sql, tuple(params), fetch_all=True)
        return [self._row_to_transfer(row) for row in rows]

    def _row_to_quality(self, row) -> MemoryQuality:
        """Convert database row to MemoryQuality."""
        return MemoryQuality(
            memory_id=row["memory_id"],
            memory_layer=row["memory_layer"],
            access_count=row["access_count"],
            last_accessed=datetime.fromtimestamp(row["last_accessed"])
            if row["last_accessed"]
            else None,
            useful_count=row["useful_count"],
            usefulness_score=row["usefulness_score"],
            confidence=row["confidence"],
            relevance_decay=row["relevance_decay"],
            source=row["source"],
            verified=bool(row["verified"]),
        )

    def _row_to_domain(self, row) -> DomainCoverage:
        """Convert database row to DomainCoverage."""
        return DomainCoverage(
            id=row["id"],
            domain=row["domain"],
            category=row["category"],
            memory_count=row["memory_count"],
            episodic_count=row["episodic_count"],
            procedural_count=row["procedural_count"],
            entity_count=row["entity_count"],
            avg_confidence=row["avg_confidence"],
            avg_usefulness=row["avg_usefulness"],
            last_updated=datetime.fromtimestamp(row["last_updated"]) if row["last_updated"] else None,
            gaps=json.loads(row["gaps"]) if row["gaps"] else [],
            strength_areas=json.loads(row["strength_areas"]) if row["strength_areas"] else [],
            first_encounter=datetime.fromtimestamp(row["first_encounter"])
            if row["first_encounter"]
            else None,
            expertise_level=ExpertiseLevel(row["expertise_level"]),
        )

    def _row_to_transfer(self, row) -> KnowledgeTransfer:
        """Convert database row to KnowledgeTransfer."""
        return KnowledgeTransfer(
            id=row["id"],
            from_project_id=row["from_project_id"],
            to_project_id=row["to_project_id"],
            knowledge_item_id=row["knowledge_item_id"],
            knowledge_layer=row["knowledge_layer"],
            transferred_at=datetime.fromtimestamp(row["transferred_at"]),
            applicability_score=row["applicability_score"],
        )
