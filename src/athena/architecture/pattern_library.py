"""Design pattern library with effectiveness tracking.

This module provides a catalog of design patterns with usage statistics and
effectiveness metrics, enabling pattern-based architectural decision making.
"""

import json
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

from ..core.database import Database
from ..core.base_store import BaseStore
from .models import DesignPattern, PatternType

logger = logging.getLogger(__name__)


class PatternLibrary(BaseStore[DesignPattern]):
    """Catalog and track design patterns with effectiveness metrics."""

    table_name = "design_patterns"
    model_class = DesignPattern

    def __init__(self, db: Optional[Database] = None):
        """Initialize pattern library.

        Args:
            db: Database instance (uses singleton if not provided)
        """
        super().__init__(db)
        self._ensure_schema()

    def _ensure_schema(self):
        """Create pattern library table if it doesn't exist."""
        # Skip for PostgreSQL async databases
        if not hasattr(self.db, 'conn'):
            logger.debug("PostgreSQL async database detected, skipping schema creation")
            return

        cursor = self.db.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS design_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                type TEXT NOT NULL,

                -- Pattern description
                problem TEXT NOT NULL,
                solution TEXT NOT NULL,
                context TEXT NOT NULL,

                -- Structure
                structure TEXT,
                code_example TEXT,

                -- Usage tracking
                usage_count INTEGER DEFAULT 0,
                projects TEXT,  -- JSON array of project IDs

                -- Effectiveness
                effectiveness_score REAL,
                success_count INTEGER DEFAULT 0,
                failure_count INTEGER DEFAULT 0,

                -- Related
                related_patterns TEXT,  -- JSON array
                anti_patterns TEXT,     -- JSON array
                tags TEXT,              -- JSON array

                -- Metadata
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
        """)

        # Indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_pattern_type
            ON design_patterns(type)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_pattern_effectiveness
            ON design_patterns(effectiveness_score DESC)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_pattern_usage
            ON design_patterns(usage_count DESC)
        """)

        self.db.conn.commit()
        logger.info("Pattern library schema initialized")

    def _row_to_model(self, row: Dict[str, Any]) -> DesignPattern:
        """Convert database row to DesignPattern model.

        Args:
            row: Database row as dict

        Returns:
            DesignPattern instance
        """
        row_dict = row if isinstance(row, dict) else dict(row)

        # Parse JSON fields
        projects = self._safe_json_loads(row_dict.get("projects"), [])
        related_patterns = self._safe_json_loads(row_dict.get("related_patterns"), [])
        anti_patterns = self._safe_json_loads(row_dict.get("anti_patterns"), [])
        tags = self._safe_json_loads(row_dict.get("tags"), [])

        return DesignPattern(
            id=row_dict.get("id"),
            name=row_dict.get("name"),
            type=PatternType(row_dict.get("type")) if row_dict.get("type") else PatternType.STRUCTURAL,
            problem=row_dict.get("problem"),
            solution=row_dict.get("solution"),
            context=row_dict.get("context"),
            structure=row_dict.get("structure"),
            code_example=row_dict.get("code_example"),
            usage_count=row_dict.get("usage_count", 0),
            projects=projects,
            effectiveness_score=row_dict.get("effectiveness_score"),
            success_count=row_dict.get("success_count", 0),
            failure_count=row_dict.get("failure_count", 0),
            related_patterns=related_patterns,
            anti_patterns=anti_patterns,
            tags=tags,
            created_at=datetime.fromtimestamp(row_dict.get("created_at")) if row_dict.get("created_at") else datetime.now(),
            updated_at=datetime.fromtimestamp(row_dict.get("updated_at")) if row_dict.get("updated_at") else datetime.now(),
        )

    def _safe_json_loads(self, data: Any, default: Any = None) -> Any:
        """Safely load JSON data with fallback."""
        if not data:
            return default
        try:
            return json.loads(data) if isinstance(data, str) else data
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"Failed to parse JSON: {data}")
            return default

    def add_pattern(self, pattern: DesignPattern) -> int:
        """Add a new pattern to the library.

        Args:
            pattern: Pattern to add

        Returns:
            ID of added pattern
        """
        cursor = self.db.conn.cursor()
        cursor.execute("""
            INSERT INTO design_patterns (
                name, type, problem, solution, context,
                structure, code_example, usage_count, projects,
                effectiveness_score, success_count, failure_count,
                related_patterns, anti_patterns, tags,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            pattern.name,
            pattern.type.value,
            pattern.problem,
            pattern.solution,
            pattern.context,
            pattern.structure,
            pattern.code_example,
            pattern.usage_count,
            json.dumps(pattern.projects),
            pattern.effectiveness_score,
            pattern.success_count,
            pattern.failure_count,
            json.dumps(pattern.related_patterns),
            json.dumps(pattern.anti_patterns),
            json.dumps(pattern.tags),
            pattern.created_at.timestamp(),
            pattern.updated_at.timestamp(),
        ))
        self.db.conn.commit()

        pattern_id = cursor.lastrowid
        logger.info(f"Added pattern {pattern_id}: {pattern.name}")
        return pattern_id

    def get(self, pattern_id: int) -> Optional[DesignPattern]:
        """Get pattern by ID.

        Args:
            pattern_id: Pattern ID

        Returns:
            Pattern or None if not found
        """
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT * FROM design_patterns WHERE id = ?", (pattern_id,))
        row = cursor.fetchone()

        if not row:
            return None

        return self._row_to_model(row)

    def get_by_name(self, name: str) -> Optional[DesignPattern]:
        """Get pattern by name.

        Args:
            name: Pattern name

        Returns:
            Pattern or None if not found
        """
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT * FROM design_patterns WHERE name = ?", (name,))
        row = cursor.fetchone()

        if not row:
            return None

        return self._row_to_model(row)

    def list_by_type(self, pattern_type: PatternType, limit: int = 100) -> List[DesignPattern]:
        """List patterns by type.

        Args:
            pattern_type: Type of patterns to list
            limit: Maximum results

        Returns:
            List of patterns
        """
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT * FROM design_patterns
            WHERE type = ?
            ORDER BY effectiveness_score DESC, usage_count DESC
            LIMIT ?
        """, (pattern_type.value, limit))

        rows = cursor.fetchall()
        return [self._row_to_model(row) for row in rows]

    def get_most_effective(self, limit: int = 10) -> List[DesignPattern]:
        """Get most effective patterns based on success rate.

        Args:
            limit: Maximum results

        Returns:
            Top performing patterns
        """
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT * FROM design_patterns
            WHERE effectiveness_score IS NOT NULL
            ORDER BY effectiveness_score DESC, usage_count DESC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()
        return [self._row_to_model(row) for row in rows]

    def get_most_used(self, limit: int = 10) -> List[DesignPattern]:
        """Get most frequently used patterns.

        Args:
            limit: Maximum results

        Returns:
            Most used patterns
        """
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT * FROM design_patterns
            ORDER BY usage_count DESC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()
        return [self._row_to_model(row) for row in rows]

    def record_usage(self, pattern_id: int, project_id: int, success: bool) -> None:
        """Record usage of a pattern in a project.

        Args:
            pattern_id: Pattern ID
            project_id: Project using the pattern
            success: Whether the usage was successful
        """
        # Get current pattern
        pattern = self.get(pattern_id)
        if not pattern:
            logger.warning(f"Pattern {pattern_id} not found")
            return

        # Update usage tracking
        if project_id not in pattern.projects:
            pattern.projects.append(project_id)

        pattern.usage_count += 1
        if success:
            pattern.success_count += 1
        else:
            pattern.failure_count += 1

        # Calculate effectiveness score
        total = pattern.success_count + pattern.failure_count
        if total > 0:
            pattern.effectiveness_score = pattern.success_count / total

        # Update database
        cursor = self.db.conn.cursor()
        cursor.execute("""
            UPDATE design_patterns
            SET usage_count = ?,
                projects = ?,
                success_count = ?,
                failure_count = ?,
                effectiveness_score = ?,
                updated_at = ?
            WHERE id = ?
        """, (
            pattern.usage_count,
            json.dumps(pattern.projects),
            pattern.success_count,
            pattern.failure_count,
            pattern.effectiveness_score,
            datetime.now().timestamp(),
            pattern_id,
        ))
        self.db.conn.commit()
        logger.info(f"Recorded {'successful' if success else 'failed'} usage of pattern {pattern_id}")

    def search_by_problem(self, problem_description: str, limit: int = 5) -> List[DesignPattern]:
        """Search patterns that solve similar problems.

        Args:
            problem_description: Description of the problem
            limit: Maximum results

        Returns:
            Matching patterns
        """
        # Simple keyword matching (could be enhanced with semantic search)
        keywords = problem_description.lower().split()

        cursor = self.db.conn.cursor()
        cursor.execute("SELECT * FROM design_patterns")
        rows = cursor.fetchall()

        patterns = [self._row_to_model(row) for row in rows]

        # Score patterns by keyword matches
        scored = []
        for pattern in patterns:
            score = 0
            problem_text = pattern.problem.lower()
            solution_text = pattern.solution.lower()

            for keyword in keywords:
                if keyword in problem_text:
                    score += 2  # Problem match is more important
                if keyword in solution_text:
                    score += 1

            if score > 0:
                scored.append((score, pattern))

        # Sort by score (descending) and effectiveness
        scored.sort(key=lambda x: (x[0], x[1].effectiveness_score or 0), reverse=True)

        return [pattern for _, pattern in scored[:limit]]

    def get_related_patterns(self, pattern_id: int) -> List[DesignPattern]:
        """Get patterns related to a given pattern.

        Args:
            pattern_id: Pattern ID

        Returns:
            Related patterns
        """
        pattern = self.get(pattern_id)
        if not pattern:
            return []

        related = []
        for related_name in pattern.related_patterns:
            related_pattern = self.get_by_name(related_name)
            if related_pattern:
                related.append(related_pattern)

        return related
