"""Database migration runner with PostgreSQL-compatible version tracking and rollback support."""

import asyncio
import time
from pathlib import Path
from typing import List, Optional
import psycopg
from psycopg import AsyncConnection


class MigrationError(Exception):
    """Migration execution error."""
    pass


class MigrationRunner:
    """Handles database migrations with proper version tracking (PostgreSQL-only)."""

    def __init__(self, connection_string: str):
        """Initialize migration runner.

        Args:
            connection_string: PostgreSQL connection string (e.g., 'postgresql://user:password@localhost/dbname')
        """
        self.connection_string = connection_string
        self._ensure_schema_version_table()

    def _ensure_schema_version_table(self):
        """Ensure schema_version table exists (synchronous wrapper for initialization)."""
        asyncio.run(self._ensure_schema_version_table_async())

    async def _ensure_schema_version_table_async(self):
        """Ensure schema_version table exists."""
        async with await psycopg.AsyncConnection.connect(self.connection_string) as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    applied_at BIGINT NOT NULL,
                    description TEXT,
                    migration_file TEXT
                )
            """)
            await conn.commit()

    def get_current_version(self) -> int:
        """Get current schema version.

        Returns:
            Current version number (0 if no migrations applied)
        """
        return asyncio.run(self._get_current_version_async())

    async def _get_current_version_async(self) -> int:
        """Get current schema version (async)."""
        async with await psycopg.AsyncConnection.connect(self.connection_string) as conn:
            cursor = await conn.execute("SELECT MAX(version) FROM schema_version")
            result = await cursor.fetchone()
            return result[0] if result and result[0] else 0

    def get_applied_migrations(self) -> List[dict]:
        """Get list of applied migrations.

        Returns:
            List of migration records
        """
        return asyncio.run(self._get_applied_migrations_async())

    async def _get_applied_migrations_async(self) -> List[dict]:
        """Get list of applied migrations (async)."""
        async with await psycopg.AsyncConnection.connect(self.connection_string) as conn:
            cursor = await conn.execute("""
                SELECT version, applied_at, description, migration_file
                FROM schema_version
                ORDER BY version
            """)

            migrations = []
            async for row in cursor:
                migrations.append({
                    'version': row[0],
                    'applied_at': row[1],
                    'description': row[2],
                    'migration_file': row[3]
                })

            return migrations

    def _parse_migration_header(self, content: str) -> dict:
        """Parse migration header for version and description.

        Args:
            content: Migration file content

        Returns:
            Dict with version, description, and up/down SQL
        """
        lines = content.split('\n')
        header = {}
        sql_parts = []
        current_section = 'up'

        for line in lines:
            line = line.strip()
            if line.startswith('-- Version:'):
                header['version'] = int(line.split(':', 1)[1].strip())
            elif line.startswith('-- Description:'):
                header['description'] = line.split(':', 1)[1].strip()
            elif line.startswith('-- UP'):
                current_section = 'up'
            elif line.startswith('-- DOWN'):
                current_section = 'down'
            elif not line.startswith('--') and line:
                if current_section not in header:
                    header[current_section] = []
                header[current_section].append(line)

        # Join SQL parts
        if 'up' in header:
            header['up_sql'] = '\n'.join(header['up'])
            del header['up']
        if 'down' in header:
            header['down_sql'] = '\n'.join(header['down'])
            del header['down']

        return header

    def apply_migration(self, migration_file: str, dry_run: bool = False) -> bool:
        """Apply a single migration.

        Args:
            migration_file: Path to migration file
            dry_run: If True, validate but don't apply

        Returns:
            True if migration was applied, False if already applied
        """
        return asyncio.run(self._apply_migration_async(migration_file, dry_run))

    async def _apply_migration_async(self, migration_file: str, dry_run: bool = False) -> bool:
        """Apply a single migration (async)."""
        path = Path(migration_file)
        if not path.exists():
            raise MigrationError(f"Migration file not found: {migration_file}")

        # Read and parse migration
        with open(migration_file, 'r', encoding='utf-8') as f:
            content = f.read()

        header = self._parse_migration_header(content)

        if 'version' not in header:
            raise MigrationError(f"No version specified in {migration_file}")

        version = header['version']
        description = header.get('description', f'Migration {version}')
        up_sql = header.get('up_sql', content)  # Fallback to full content

        # Check if already applied
        current_version = await self._get_current_version_async()
        if version <= current_version:
            print(f"✓ Migration {version} already applied")
            return False

        print(f"Applying migration {version}: {description}")

        if dry_run:
            print("DRY RUN - Would execute:")
            print(up_sql)
            return True

        # Apply migration
        async with await psycopg.AsyncConnection.connect(self.connection_string) as conn:
            try:
                # Execute migration SQL (split by semicolon for multiple statements)
                for statement in up_sql.split(';'):
                    statement = statement.strip()
                    if statement:
                        await conn.execute(statement)

                # Record migration
                await conn.execute("""
                    INSERT INTO schema_version (version, applied_at, description, migration_file)
                    VALUES (%s, %s, %s, %s)
                """, (version, int(time.time()), description, path.name))

                await conn.commit()
                print(f"✓ Migration {version} applied successfully")

            except Exception as e:
                await conn.rollback()
                raise MigrationError(f"Failed to apply migration {version}: {e}")

        return True

    def rollback_migration(self, target_version: Optional[int] = None) -> bool:
        """Rollback to a specific version.

        Args:
            target_version: Version to rollback to (default: previous version)

        Returns:
            True if rollback was performed
        """
        return asyncio.run(self._rollback_migration_async(target_version))

    async def _rollback_migration_async(self, target_version: Optional[int] = None) -> bool:
        """Rollback to a specific version (async)."""
        current_version = await self._get_current_version_async()

        if target_version is None:
            target_version = current_version - 1

        if target_version >= current_version:
            print(f"Nothing to rollback (current: {current_version}, target: {target_version})")
            return False

        # Find migration to rollback
        applied = await self._get_applied_migrations_async()
        to_rollback = [m for m in applied if m['version'] > target_version]

        if not to_rollback:
            print("No migrations to rollback")
            return False

        # For now, we can't automatically rollback without DOWN SQL
        # This would need enhancement to store rollback SQL
        raise MigrationError(
            f"Automatic rollback not supported. Manual intervention required. "
            f"Current version: {current_version}, target: {target_version}"
        )

    def run_pending_migrations(self, dry_run: bool = False) -> int:
        """Run all pending migrations.

        Args:
            dry_run: If True, validate but don't apply

        Returns:
            Number of migrations applied
        """
        return asyncio.run(self._run_pending_migrations_async(dry_run))

    async def _run_pending_migrations_async(self, dry_run: bool = False) -> int:
        """Run all pending migrations (async)."""
        migrations_dir = Path(__file__).parent
        migration_files = sorted(migrations_dir.glob("*.sql"))

        if not migration_files:
            print("No migration files found")
            return 0

        applied_count = 0

        for migration_file in migration_files:
            try:
                if await self._apply_migration_async(str(migration_file), dry_run=dry_run):
                    applied_count += 1
            except MigrationError as e:
                print(f"❌ Migration failed: {e}")
                if not dry_run:
                    raise

        if applied_count > 0:
            print(f"✓ Applied {applied_count} migrations")
        else:
            print("✓ No pending migrations")

        return applied_count


def run_all_migrations(connection_string: str, dry_run: bool = False):
    """Run all pending migrations.

    Args:
        connection_string: PostgreSQL connection string
        dry_run: If True, validate but don't apply
    """
    runner = MigrationRunner(connection_string)
    runner.run_pending_migrations(dry_run=dry_run)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python runner.py <postgresql_connection_string> [--dry-run]")
        print("Example: python runner.py 'postgresql://user:password@localhost/athena' --dry-run")
        sys.exit(1)

    connection_string = sys.argv[1]
    dry_run = '--dry-run' in sys.argv

    try:
        run_all_migrations(connection_string, dry_run=dry_run)
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)
