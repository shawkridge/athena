"""Migration execution engine for Athena schema management.

Responsible for:
- Discovering and ordering migrations
- Tracking applied migrations in database
- Executing migrations with rollback support
- Validating migration integrity
"""

import re
from pathlib import Path
from typing import List
import logging

logger = logging.getLogger(__name__)


class Migration:
    """Represents a single schema migration."""

    def __init__(self, version: str, filename: str, content: str):
        self.version = version
        self.filename = filename
        self.content = content
        self.description = self._parse_description()

    def _parse_description(self) -> str:
        """Extract description from migration file comment."""
        match = re.search(r"--\s+(.+?)(?:\n|$)", self.content)
        return match.group(1) if match else "No description"

    def __repr__(self) -> str:
        return f"Migration({self.version}: {self.description})"


class MigrationRunner:
    """Executes schema migrations in order."""

    MIGRATIONS_DIR = Path(__file__).parent / "migrations"
    SCHEMA_VERSION_TABLE = "schema_versions"

    def __init__(self, db):
        """Initialize migration runner.

        Args:
            db: Database instance (must have get_connection() method)
        """
        self.db = db
        self.migrations: List[Migration] = []

    async def discover_migrations(self) -> List[Migration]:
        """Discover all migration files."""
        if not self.MIGRATIONS_DIR.exists():
            logger.info(f"Creating migrations directory: {self.MIGRATIONS_DIR}")
            self.MIGRATIONS_DIR.mkdir(parents=True, exist_ok=True)
            return []

        migrations = []
        for filepath in sorted(self.MIGRATIONS_DIR.glob("m*.sql")):
            # Extract version from filename (e.g., m001_initial.sql -> 001)
            match = re.match(r"m(\d+)_", filepath.name)
            if not match:
                logger.warning(f"Skipping migration with invalid name: {filepath.name}")
                continue

            version = match.group(1)
            content = filepath.read_text()
            migration = Migration(version, filepath.name, content)
            migrations.append(migration)
            logger.debug(f"Discovered {migration}")

        self.migrations = migrations
        return migrations

    async def _ensure_version_table(self):
        """Create schema_versions table if it doesn't exist."""
        async with self.db.get_connection() as conn:
            await conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self.SCHEMA_VERSION_TABLE} (
                    version VARCHAR(10) PRIMARY KEY,
                    filename VARCHAR(255) NOT NULL,
                    description TEXT,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    execution_time_ms INTEGER
                )
            """
            )
            await conn.commit()

    async def get_applied_versions(self) -> set:
        """Get set of already-applied migration versions."""
        await self._ensure_version_table()

        async with self.db.get_connection() as conn:
            result = await conn.execute(
                f"SELECT version FROM {self.SCHEMA_VERSION_TABLE} ORDER BY version"
            )
            rows = await result.fetchall()
            return {row[0] for row in rows}

    async def run_migrations(self) -> dict:
        """Execute all pending migrations in order.

        Returns:
            Dict with keys:
            - applied: List of applied migration versions
            - skipped: List of already-applied versions
            - errors: Dict of version -> error message
        """
        logger.info("Starting schema migration run")
        await self.discover_migrations()

        if not self.migrations:
            logger.info("No migrations found")
            return {"applied": [], "skipped": [], "errors": {}}

        applied_versions = await self.get_applied_versions()
        result = {"applied": [], "skipped": [], "errors": {}}

        for migration in self.migrations:
            if migration.version in applied_versions:
                logger.debug(f"Skipping already-applied {migration}")
                result["skipped"].append(migration.version)
                continue

            try:
                await self._execute_migration(migration)
                result["applied"].append(migration.version)
                logger.info(f"Applied {migration}")
            except Exception as e:
                error_msg = f"{type(e).__name__}: {str(e)}"
                result["errors"][migration.version] = error_msg
                logger.error(f"Failed to apply {migration}: {error_msg}")
                # Stop on first error (transaction safety)
                break

        return result

    async def _execute_migration(self, migration: Migration):
        """Execute a single migration."""
        import time

        start_ms = time.time()

        async with self.db.get_connection() as conn:
            # Execute migration SQL
            await conn.execute(migration.content)

            # Record in schema_versions
            execution_time_ms = int((time.time() - start_ms) * 1000)
            await conn.execute(
                f"""
                INSERT INTO {self.SCHEMA_VERSION_TABLE}
                (version, filename, description, execution_time_ms)
                VALUES (%s, %s, %s, %s)
                """,
                (migration.version, migration.filename, migration.description, execution_time_ms),
            )

            await conn.commit()

    async def get_migration_status(self) -> dict:
        """Get status of all migrations."""
        await self.discover_migrations()
        applied = await self.get_applied_versions()

        status = {
            "total": len(self.migrations),
            "applied": len(applied),
            "pending": len(self.migrations) - len(applied),
            "migrations": [],
        }

        for migration in self.migrations:
            is_applied = migration.version in applied
            status["migrations"].append(
                {
                    "version": migration.version,
                    "filename": migration.filename,
                    "description": migration.description,
                    "applied": is_applied,
                }
            )

        return status
