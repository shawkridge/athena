"""Persistent skill library.

Stores and retrieves skills from database with search and filtering.
"""

from typing import List, Optional, Dict, Any
from pathlib import Path
import json
import logging

from .models import Skill, SkillMetadata, SkillDomain

logger = logging.getLogger(__name__)


class SkillLibrary:
    """Persistent storage and retrieval of skills.

    Skills are stored as:
    - Metadata in database for fast search
    - Code in filesystem or database for execution
    """

    def __init__(self, db: 'Database', storage_dir: Optional[str] = None):
        """Initialize skill library.

        Args:
            db: Database instance for metadata
            storage_dir: Optional directory for code storage
        """
        self.db = db
        self.storage_dir = Path(storage_dir) if storage_dir else None
        self._init_schema()

    def _init_schema(self) -> None:
        """Create skills table if needed."""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skills (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                domain TEXT,
                code TEXT,
                entry_point TEXT,
                metadata_json TEXT,
                quality_score REAL,
                times_used INTEGER DEFAULT 0,
                success_rate REAL DEFAULT 1.0,
                tags TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        self.db.conn.commit()

    def save(self, skill: Skill) -> bool:
        """Save a skill to library.

        Args:
            skill: Skill to save

        Returns:
            True if saved successfully
        """
        try:
            metadata_json = skill.metadata.to_json()

            cursor = self.db.conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO skills
                (id, name, description, domain, code, entry_point, metadata_json,
                 quality_score, times_used, success_rate, tags, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                skill.id,
                skill.metadata.name,
                skill.metadata.description,
                skill.metadata.domain.value,
                skill.code,
                skill.entry_point,
                metadata_json,
                skill.metadata.quality_score,
                skill.metadata.times_used,
                skill.metadata.success_rate,
                ','.join(skill.metadata.tags),
                skill.metadata.created_at.isoformat(),
                skill.metadata.updated_at.isoformat(),
            ))
            self.db.conn.commit()

            # Optionally save code to filesystem
            if self.storage_dir:
                self._save_code_file(skill)

            logger.info(f"Saved skill: {skill.id}")
            return True

        except Exception as e:
            logger.error(f"Failed to save skill {skill.id}: {e}")
            return False

    def get(self, skill_id: str) -> Optional[Skill]:
        """Retrieve a skill by ID.

        Args:
            skill_id: Skill identifier

        Returns:
            Skill instance or None if not found
        """
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT * FROM skills WHERE id = ?", (skill_id,))
        row = cursor.fetchone()

        if not row:
            return None

        return self._row_to_skill(row)

    def list_all(self, domain: Optional[SkillDomain] = None, limit: int = 100) -> List[Skill]:
        """List all skills with optional filtering.

        Args:
            domain: Optional domain filter
            limit: Max results

        Returns:
            List of skills
        """
        if domain:
            cursor = self.db.conn.cursor()
            cursor.execute(
                "SELECT * FROM skills WHERE domain = ? ORDER BY quality_score DESC LIMIT ?",
                (domain.value, limit)
            )
        else:
            cursor = self.db.conn.cursor()
            cursor.execute(
                "SELECT * FROM skills ORDER BY quality_score DESC LIMIT ?",
                (limit,)
            )

        rows = cursor.fetchall()
        return [self._row_to_skill(row) for row in rows]

    def search(self, query: str, limit: int = 10) -> List[Skill]:
        """Search skills by name, description, or tags.

        Args:
            query: Search query
            limit: Max results

        Returns:
            List of matching skills
        """
        query_pattern = f"%{query.lower()}%"

        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT * FROM skills
            WHERE
                LOWER(name) LIKE ? OR
                LOWER(description) LIKE ? OR
                LOWER(tags) LIKE ?
            ORDER BY quality_score DESC
            LIMIT ?
        """, (query_pattern, query_pattern, query_pattern, limit))

        rows = cursor.fetchall()
        return [self._row_to_skill(row) for row in rows]

    def delete(self, skill_id: str) -> bool:
        """Delete a skill from library.

        Args:
            skill_id: Skill to delete

        Returns:
            True if deleted
        """
        try:
            cursor = self.db.conn.cursor()
            cursor.execute("DELETE FROM skills WHERE id = ?", (skill_id,))
            self.db.conn.commit()

            # Delete code file if exists
            if self.storage_dir:
                code_file = self.storage_dir / f"{skill_id}.py"
                if code_file.exists():
                    code_file.unlink()

            logger.info(f"Deleted skill: {skill_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete skill {skill_id}: {e}")
            return False

    def update_usage(self, skill_id: str, success: bool) -> bool:
        """Update skill usage statistics.

        Args:
            skill_id: Skill to update
            success: Whether execution succeeded

        Returns:
            True if updated
        """
        skill = self.get(skill_id)
        if not skill:
            return False

        skill.update_usage(success)
        return self.save(skill)

    def stats(self) -> Dict[str, Any]:
        """Get library statistics.

        Returns:
            Dictionary with statistics
        """
        cursor = self.db.conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM skills")
        total_skills = cursor.fetchone()[0]

        cursor.execute("SELECT AVG(quality_score) FROM skills")
        avg_quality = cursor.fetchone()[0] or 0.0

        cursor.execute("SELECT SUM(times_used) FROM skills")
        total_uses = cursor.fetchone()[0] or 0

        cursor.execute("SELECT AVG(success_rate) FROM skills")
        avg_success_rate = cursor.fetchone()[0] or 0.0

        cursor.execute("SELECT COUNT(DISTINCT domain) FROM skills")
        num_domains = cursor.fetchone()[0]

        return {
            'total_skills': total_skills,
            'avg_quality': round(avg_quality, 3),
            'total_uses': total_uses,
            'avg_success_rate': round(avg_success_rate, 3),
            'domains': num_domains,
        }

    def _row_to_skill(self, row: tuple) -> Skill:
        """Convert database row to Skill instance.

        Args:
            row: Database row

        Returns:
            Skill instance
        """
        # Unpack row based on schema
        (id_, name, description, domain, code, entry_point, metadata_json,
         quality_score, times_used, success_rate, tags, created_at, updated_at) = row

        # Parse metadata
        metadata = SkillMetadata.from_dict(json.loads(metadata_json))

        return Skill(
            metadata=metadata,
            code=code,
            entry_point=entry_point,
        )

    def _save_code_file(self, skill: Skill) -> None:
        """Save skill code to filesystem.

        Args:
            skill: Skill to save
        """
        if not self.storage_dir:
            return

        self.storage_dir.mkdir(parents=True, exist_ok=True)
        code_file = self.storage_dir / f"{skill.id}.py"

        with open(code_file, 'w') as f:
            f.write(skill.code)

        logger.debug(f"Saved skill code: {code_file}")
