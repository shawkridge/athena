"""Async-first persistent skill library for PostgreSQL.

Stores and retrieves skills from database with search and filtering.
Async/await API for modern Python with PostgreSQL backend.
"""

from typing import List, Optional, Dict, Any
from pathlib import Path
import json
import logging

from .models import Skill, SkillMetadata, SkillDomain
from ..core.database_postgres import PostgresDatabase

logger = logging.getLogger(__name__)


class SkillLibrary:
    """Async-first persistent storage and retrieval of skills using PostgreSQL.

    Features:
    - Full async/await API
    - PostgreSQL backend with connection pooling
    - Skills stored as:
      - Metadata in database for fast search
      - Code in filesystem or database for execution

    Usage:
        from athena.core.database_postgres import PostgresDatabase
        from athena.skills.library import SkillLibrary

        db = PostgresDatabase(host="localhost", dbname="athena")
        await db.initialize()

        library = SkillLibrary(db)
        await library.save(skill)
    """

    def __init__(self, db: PostgresDatabase, storage_dir: Optional[str] = None):
        """Initialize skill library.

        Args:
            db: PostgresDatabase instance
            storage_dir: Optional directory for skill code storage

        Raises:
            TypeError: If db is not PostgresDatabase
        """
        if not isinstance(db, PostgresDatabase):
            raise TypeError(
                f"SkillLibrary requires PostgresDatabase, got {type(db)}"
            )

        self.db = db
        self.storage_dir = Path(storage_dir) if storage_dir else None
        self._schema_initialized = False

    async def init_schema(self) -> None:
        """Create skills table if needed (async version)."""
        if self._schema_initialized:
            return

        try:
            await self.db.initialize()

            # PostgreSQL-specific SQL
            create_table_sql = """
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
            """

            async with self.db.get_connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(create_table_sql)
                    await conn.commit()

            self._schema_initialized = True
            logger.debug("Skills table initialized")

        except Exception as e:
            logger.warning(f"Skills table may already exist: {e}")
            self._schema_initialized = True

    async def save(self, skill: Skill) -> bool:
        """Save a skill to library.

        Args:
            skill: Skill to save

        Returns:
            True if saved successfully
        """
        await self.init_schema()

        try:
            metadata_json = skill.metadata.to_json()

            insert_sql = """
                INSERT INTO skills
                (id, name, description, domain, code, entry_point, metadata_json,
                 quality_score, times_used, success_rate, tags, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    domain = EXCLUDED.domain,
                    code = EXCLUDED.code,
                    entry_point = EXCLUDED.entry_point,
                    metadata_json = EXCLUDED.metadata_json,
                    quality_score = EXCLUDED.quality_score,
                    times_used = EXCLUDED.times_used,
                    success_rate = EXCLUDED.success_rate,
                    tags = EXCLUDED.tags,
                    updated_at = EXCLUDED.updated_at
            """

            params = (
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
            )

            async with self.db.get_connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(insert_sql, params)
                    await conn.commit()

            # Optionally save code to filesystem
            if self.storage_dir:
                self._save_code_file(skill)

            logger.info(f"Saved skill: {skill.id}")
            return True

        except Exception as e:
            logger.error(f"Failed to save skill {skill.id}: {e}")
            return False

    async def get(self, skill_id: str) -> Optional[Skill]:
        """Retrieve a skill by ID.

        Args:
            skill_id: Skill identifier

        Returns:
            Skill instance or None if not found
        """
        await self.init_schema()

        try:
            select_sql = "SELECT * FROM skills WHERE id = %s"
            params = (skill_id,)

            async with self.db.get_connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(select_sql, params)
                    row = await cur.fetchone()

            if not row:
                return None

            return self._row_to_skill(row)

        except Exception as e:
            logger.error(f"Failed to retrieve skill {skill_id}: {e}")
            return None

    async def list_all(
        self,
        domain: Optional[SkillDomain] = None,
        limit: int = 100
    ) -> List[Skill]:
        """List all skills with optional filtering.

        Args:
            domain: Optional domain filter
            limit: Max results

        Returns:
            List of skills
        """
        await self.init_schema()

        try:
            if domain:
                select_sql = (
                    "SELECT * FROM skills WHERE domain = %s "
                    "ORDER BY quality_score DESC LIMIT %s"
                )
                params = (domain.value, limit)
            else:
                select_sql = (
                    "SELECT * FROM skills "
                    "ORDER BY quality_score DESC LIMIT %s"
                )
                params = (limit,)

            async with self.db.get_connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(select_sql, params)
                    rows = await cur.fetchall()

            return [self._row_to_skill(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to list skills: {e}")
            return []

    async def search(self, query: str, limit: int = 10) -> List[Skill]:
        """Search skills by name, description, or tags.

        Args:
            query: Search query
            limit: Max results

        Returns:
            List of matching skills
        """
        await self.init_schema()

        try:
            query_pattern = f"%{query.lower()}%"

            search_sql = """
                SELECT * FROM skills
                WHERE
                    LOWER(name) LIKE %s OR
                    LOWER(description) LIKE %s OR
                    LOWER(tags) LIKE %s
                ORDER BY quality_score DESC
                LIMIT %s
            """

            params = (query_pattern, query_pattern, query_pattern, limit)

            async with self.db.get_connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(search_sql, params)
                    rows = await cur.fetchall()

            return [self._row_to_skill(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to search skills: {e}")
            return []

    async def delete(self, skill_id: str) -> bool:
        """Delete a skill from library.

        Args:
            skill_id: Skill to delete

        Returns:
            True if deleted
        """
        await self.init_schema()

        try:
            delete_sql = "DELETE FROM skills WHERE id = %s"
            params = (skill_id,)

            async with self.db.get_connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(delete_sql, params)
                    await conn.commit()

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

    async def update_usage(self, skill_id: str, success: bool) -> bool:
        """Update skill usage statistics.

        Args:
            skill_id: Skill to update
            success: Whether execution succeeded

        Returns:
            True if updated
        """
        skill = await self.get(skill_id)
        if not skill:
            return False

        skill.update_usage(success)
        return await self.save(skill)

    async def stats(self) -> Dict[str, Any]:
        """Get library statistics.

        Returns:
            Dictionary with statistics
        """
        await self.init_schema()

        try:
            async with self.db.get_connection() as conn:
                async with conn.cursor() as cur:
                    # Get total skills
                    await cur.execute("SELECT COUNT(*) FROM skills")
                    total_skills = (await cur.fetchone())[0]

                    # Get average quality
                    await cur.execute("SELECT AVG(quality_score) FROM skills")
                    avg_quality = (await cur.fetchone())[0] or 0.0

                    # Get total uses
                    await cur.execute("SELECT SUM(times_used) FROM skills")
                    total_uses = (await cur.fetchone())[0] or 0

                    # Get average success rate
                    await cur.execute("SELECT AVG(success_rate) FROM skills")
                    avg_success_rate = (await cur.fetchone())[0] or 0.0

                    # Get number of domains
                    await cur.execute("SELECT COUNT(DISTINCT domain) FROM skills")
                    num_domains = (await cur.fetchone())[0]

            return {
                'total_skills': total_skills,
                'avg_quality': round(avg_quality, 3),
                'total_uses': total_uses,
                'avg_success_rate': round(avg_success_rate, 3),
                'domains': num_domains,
            }

        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {
                'total_skills': 0,
                'avg_quality': 0.0,
                'total_uses': 0,
                'avg_success_rate': 0.0,
                'domains': 0,
            }

    def _row_to_skill(self, row: Any) -> Skill:
        """Convert database row to Skill instance.

        Args:
            row: Database row (tuple-like from psycopg)

        Returns:
            Skill instance
        """
        # PostgreSQL returns tuple-like rows
        id_, name, description, domain, code, entry_point, metadata_json, *_ = row

        # Parse metadata (handle both string JSON and dict)
        if isinstance(metadata_json, str):
            metadata_dict = json.loads(metadata_json)
        else:
            metadata_dict = metadata_json

        metadata = SkillMetadata.from_dict(metadata_dict)

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
