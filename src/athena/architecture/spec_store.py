"""Specification storage and management for spec-driven development.

This module provides hybrid storage for specifications - files tracked in git
with metadata and relationships stored in the database. Supports multiple
specification formats (OpenAPI, TLA+, Alloy, Prisma, markdown, etc.).

Storage Strategy:
1. Spec content stored as files in specs/ directory (git-tracked)
2. Metadata and relationships stored in database
3. File watcher syncs changes between filesystem and database
4. Supports semantic versioning and change tracking
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from ..core.database import Database
from ..core.base_store import BaseStore
from .models import Specification, SpecType, SpecStatus

logger = logging.getLogger(__name__)


class SpecificationStore(BaseStore[Specification]):
    """Store and manage specifications with hybrid file + database storage."""

    table_name = "specifications"
    model_class = Specification

    def __init__(self, db: Optional[Database] = None, specs_dir: Optional[Path] = None):
        """Initialize specification store.

        Args:
            db: Database instance (uses singleton if not provided)
            specs_dir: Directory for spec files (defaults to ./specs/)
        """
        super().__init__(db)
        self.specs_dir = specs_dir or Path.cwd() / "specs"
        self._ensure_schema()
        self._ensure_specs_directory()

    def _ensure_schema(self):
        """Create specifications table if it doesn't exist."""
        # Skip for PostgreSQL async databases
        if not hasattr(self.db, 'conn'):
            logger.debug("PostgreSQL async database detected, skipping schema creation")
            return

        cursor = self.db.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS specifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,

                -- Basic metadata
                name TEXT NOT NULL,
                spec_type TEXT NOT NULL,
                version TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'draft',

                -- Content
                content TEXT NOT NULL,
                file_path TEXT,
                description TEXT,

                -- Relationships (JSON arrays)
                related_adr_ids TEXT,
                implements_constraint_ids TEXT,
                uses_pattern_ids TEXT,

                -- Validation
                validation_status TEXT,
                validated_at REAL,
                validation_errors TEXT,

                -- Code generation
                generated_code_path TEXT,
                generation_accuracy REAL,

                -- Metadata
                tags TEXT,
                author TEXT,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
        """)

        # Indexes for common queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_spec_project
            ON specifications(project_id, created_at DESC)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_spec_type
            ON specifications(spec_type)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_spec_status
            ON specifications(status)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_spec_version
            ON specifications(project_id, name, version DESC)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_spec_file_path
            ON specifications(file_path)
        """)

        self.db.conn.commit()
        logger.info("Specification store schema initialized")

    def _ensure_specs_directory(self):
        """Create specs directory if it doesn't exist."""
        # Create directory if needed
        if not self.specs_dir.exists():
            self.specs_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created specs directory: {self.specs_dir}")

        # Create .gitkeep to track in git (if it doesn't exist)
        gitkeep = self.specs_dir / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.touch()

        # Create README (if it doesn't exist)
        readme = self.specs_dir / "README.md"
        if not readme.exists():
            readme.write_text("""# Specifications

This directory contains specifications that define system behavior.

## Supported Formats

- **OpenAPI** (.yaml, .json) - REST API specifications
- **GraphQL** (.graphql) - GraphQL schemas
- **TLA+** (.tla) - Formal specifications
- **Alloy** (.als) - Structural models
- **Prisma** (.prisma) - Database schemas
- **AsyncAPI** (.yaml) - Event-driven API specs
- **Markdown** (.md) - General specifications

## Version Control

All specs are tracked in git. Use semantic versioning (MAJOR.MINOR.PATCH).

## Workflow

1. Write spec (intent as source of truth)
2. Validate spec (automated validation)
3. Generate code from spec (AI-assisted)
4. Verify generated code matches spec
5. Track accuracy metrics

For more info, see: docs/SPEC_DRIVEN_DEVELOPMENT.md
""")

    def _row_to_model(self, row: Dict[str, Any]) -> Specification:
        """Convert database row to Specification model.

        Args:
            row: Database row as dict

        Returns:
            Specification instance
        """
        row_dict = row if isinstance(row, dict) else dict(row)

        # Parse JSON fields
        related_adr_ids = self._safe_json_loads(row_dict.get("related_adr_ids"), [])
        implements_constraint_ids = self._safe_json_loads(row_dict.get("implements_constraint_ids"), [])
        uses_pattern_ids = self._safe_json_loads(row_dict.get("uses_pattern_ids"), [])
        validation_errors = self._safe_json_loads(row_dict.get("validation_errors"), [])
        tags = self._safe_json_loads(row_dict.get("tags"), [])

        return Specification(
            id=row_dict.get("id"),
            project_id=row_dict.get("project_id"),
            name=row_dict.get("name"),
            spec_type=SpecType(row_dict.get("spec_type")) if row_dict.get("spec_type") else SpecType.MARKDOWN,
            version=row_dict.get("version"),
            status=SpecStatus(row_dict.get("status")) if row_dict.get("status") else SpecStatus.DRAFT,
            content=row_dict.get("content", ""),
            file_path=row_dict.get("file_path"),
            description=row_dict.get("description"),
            related_adr_ids=related_adr_ids,
            implements_constraint_ids=implements_constraint_ids,
            uses_pattern_ids=uses_pattern_ids,
            validation_status=row_dict.get("validation_status"),
            validated_at=datetime.fromtimestamp(row_dict.get("validated_at")) if row_dict.get("validated_at") else None,
            validation_errors=validation_errors,
            generated_code_path=row_dict.get("generated_code_path"),
            generation_accuracy=row_dict.get("generation_accuracy"),
            tags=tags,
            author=row_dict.get("author"),
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

    def create(self, spec: Specification, write_to_file: bool = True) -> int:
        """Create a new specification.

        Args:
            spec: Specification to create
            write_to_file: Whether to write content to file (default: True)

        Returns:
            ID of created specification
        """
        # Write to file if requested and file_path is set
        if write_to_file and spec.file_path:
            file_path = self.specs_dir / spec.file_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(spec.content)
            logger.info(f"Wrote spec to file: {file_path}")

        # Store in database
        cursor = self.db.conn.cursor()
        cursor.execute("""
            INSERT INTO specifications (
                project_id, name, spec_type, version, status,
                content, file_path, description,
                related_adr_ids, implements_constraint_ids, uses_pattern_ids,
                validation_status, validated_at, validation_errors,
                generated_code_path, generation_accuracy,
                tags, author, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            spec.project_id,
            spec.name,
            spec.spec_type,
            spec.version,
            spec.status,
            spec.content,
            spec.file_path,
            spec.description,
            json.dumps(spec.related_adr_ids),
            json.dumps(spec.implements_constraint_ids),
            json.dumps(spec.uses_pattern_ids),
            spec.validation_status,
            spec.validated_at.timestamp() if spec.validated_at else None,
            json.dumps(spec.validation_errors),
            spec.generated_code_path,
            spec.generation_accuracy,
            json.dumps(spec.tags),
            spec.author,
            spec.created_at.timestamp(),
            spec.updated_at.timestamp(),
        ))
        self.db.conn.commit()

        spec_id = cursor.lastrowid
        logger.info(f"Created specification {spec_id}: {spec.name} v{spec.version}")
        return spec_id

    def get(self, spec_id: int) -> Optional[Specification]:
        """Get specification by ID.

        Args:
            spec_id: Specification ID

        Returns:
            Specification or None if not found
        """
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT * FROM specifications WHERE id = ?", (spec_id,))
        row = cursor.fetchone()

        if not row:
            return None

        return self._row_to_model(row)

    def get_by_file_path(self, file_path: str) -> Optional[Specification]:
        """Get specification by file path.

        Args:
            file_path: Relative path to spec file

        Returns:
            Specification or None if not found
        """
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT * FROM specifications WHERE file_path = ?", (file_path,))
        row = cursor.fetchone()

        if not row:
            return None

        return self._row_to_model(row)

    def list_by_project(
        self,
        project_id: int,
        spec_type: Optional[SpecType] = None,
        status: Optional[SpecStatus] = None,
        limit: int = 100
    ) -> List[Specification]:
        """List specifications for a project.

        Args:
            project_id: Project ID
            spec_type: Filter by type (optional)
            status: Filter by status (optional)
            limit: Maximum number to return

        Returns:
            List of specifications
        """
        cursor = self.db.conn.cursor()

        if spec_type and status:
            cursor.execute("""
                SELECT * FROM specifications
                WHERE project_id = ? AND spec_type = ? AND status = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (project_id, spec_type.value, status.value, limit))
        elif spec_type:
            cursor.execute("""
                SELECT * FROM specifications
                WHERE project_id = ? AND spec_type = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (project_id, spec_type.value, limit))
        elif status:
            cursor.execute("""
                SELECT * FROM specifications
                WHERE project_id = ? AND status = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (project_id, status.value, limit))
        else:
            cursor.execute("""
                SELECT * FROM specifications
                WHERE project_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (project_id, limit))

        rows = cursor.fetchall()
        return [self._row_to_model(row) for row in rows]

    def get_latest_version(self, project_id: int, name: str) -> Optional[Specification]:
        """Get latest version of a specification by name.

        Args:
            project_id: Project ID
            name: Specification name

        Returns:
            Latest version or None
        """
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT * FROM specifications
            WHERE project_id = ? AND name = ?
            ORDER BY created_at DESC
            LIMIT 1
        """, (project_id, name))

        row = cursor.fetchone()
        if not row:
            return None

        return self._row_to_model(row)

    def update(self, spec: Specification, write_to_file: bool = True) -> None:
        """Update an existing specification.

        Args:
            spec: Specification to update
            write_to_file: Whether to update file (default: True)
        """
        if not spec.id:
            raise ValueError("Specification must have an ID to update")

        # Update file if requested and file_path is set
        if write_to_file and spec.file_path:
            file_path = self.specs_dir / spec.file_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(spec.content)
            logger.info(f"Updated spec file: {file_path}")

        # Update database
        spec.updated_at = datetime.now()

        cursor = self.db.conn.cursor()
        cursor.execute("""
            UPDATE specifications SET
                name = ?, spec_type = ?, version = ?, status = ?,
                content = ?, file_path = ?, description = ?,
                related_adr_ids = ?, implements_constraint_ids = ?, uses_pattern_ids = ?,
                validation_status = ?, validated_at = ?, validation_errors = ?,
                generated_code_path = ?, generation_accuracy = ?,
                tags = ?, author = ?, updated_at = ?
            WHERE id = ?
        """, (
            spec.name,
            spec.spec_type,
            spec.version,
            spec.status,
            spec.content,
            spec.file_path,
            spec.description,
            json.dumps(spec.related_adr_ids),
            json.dumps(spec.implements_constraint_ids),
            json.dumps(spec.uses_pattern_ids),
            spec.validation_status,
            spec.validated_at.timestamp() if spec.validated_at else None,
            json.dumps(spec.validation_errors),
            spec.generated_code_path,
            spec.generation_accuracy,
            json.dumps(spec.tags),
            spec.author,
            spec.updated_at.timestamp(),
            spec.id,
        ))
        self.db.conn.commit()
        logger.info(f"Updated specification {spec.id}: {spec.name} v{spec.version}")

    def delete(self, spec_id: int, delete_file: bool = False) -> None:
        """Delete a specification.

        Args:
            spec_id: Specification ID
            delete_file: Whether to delete the file (default: False)
        """
        # Get spec to find file path
        spec = self.get(spec_id)
        if not spec:
            logger.warning(f"Specification {spec_id} not found")
            return

        # Delete file if requested
        if delete_file and spec.file_path:
            file_path = self.specs_dir / spec.file_path
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Deleted spec file: {file_path}")

        # Delete from database
        cursor = self.db.conn.cursor()
        cursor.execute("DELETE FROM specifications WHERE id = ?", (spec_id,))
        self.db.conn.commit()
        logger.info(f"Deleted specification {spec_id}: {spec.name}")

    def sync_from_filesystem(self, project_id: int) -> Dict[str, int]:
        """Sync specifications from filesystem to database.

        Scans specs/ directory for spec files and creates/updates database records.

        Args:
            project_id: Project ID to associate with specs

        Returns:
            Dictionary with counts: {'created': N, 'updated': M, 'skipped': K}
        """
        stats = {'created': 0, 'updated': 0, 'skipped': 0}

        # Scan specs directory
        for spec_file in self.specs_dir.rglob("*"):
            if spec_file.is_dir() or spec_file.name.startswith("."):
                continue

            # Skip README and other special files
            if spec_file.name in ["README.md", ".gitkeep", ".gitignore"]:
                continue

            # Determine spec type from extension
            spec_type = self._detect_spec_type(spec_file)
            if not spec_type:
                stats['skipped'] += 1
                continue

            # Read content
            try:
                content = spec_file.read_text()
            except Exception as e:
                logger.warning(f"Failed to read {spec_file}: {e}")
                stats['skipped'] += 1
                continue

            # Get relative path
            file_path = str(spec_file.relative_to(self.specs_dir))

            # Check if spec already exists
            existing = self.get_by_file_path(file_path)

            if existing:
                # Update if content changed
                if existing.content != content:
                    existing.content = content
                    existing.updated_at = datetime.fromtimestamp(spec_file.stat().st_mtime)
                    self.update(existing, write_to_file=False)
                    stats['updated'] += 1
                else:
                    stats['skipped'] += 1
            else:
                # Create new spec
                spec = Specification(
                    project_id=project_id,
                    name=spec_file.stem,
                    spec_type=spec_type,
                    version="1.0.0",  # Default version
                    status=SpecStatus.ACTIVE,
                    content=content,
                    file_path=file_path,
                    description=f"Auto-imported from {file_path}",
                    created_at=datetime.fromtimestamp(spec_file.stat().st_ctime),
                    updated_at=datetime.fromtimestamp(spec_file.stat().st_mtime),
                )
                self.create(spec, write_to_file=False)
                stats['created'] += 1

        logger.info(f"Synced specs from filesystem: {stats}")
        return stats

    def _detect_spec_type(self, file_path: Path) -> Optional[SpecType]:
        """Detect specification type from file extension.

        Args:
            file_path: Path to spec file

        Returns:
            SpecType or None if unknown
        """
        ext = file_path.suffix.lower()
        name = file_path.name.lower()

        # OpenAPI
        if ext in ['.yaml', '.yml', '.json']:
            content_preview = file_path.read_text()[:200].lower()
            if 'openapi' in content_preview or 'swagger' in content_preview:
                return SpecType.OPENAPI
            if 'asyncapi' in content_preview:
                return SpecType.ASYNCAPI

        # GraphQL
        if ext in ['.graphql', '.gql']:
            return SpecType.GRAPHQL

        # Protocol Buffers
        if ext == '.proto':
            return SpecType.PROTO

        # TLA+
        if ext == '.tla':
            return SpecType.TLAP

        # Alloy
        if ext == '.als':
            return SpecType.ALLOY

        # Prisma
        if ext == '.prisma':
            return SpecType.PRISMA

        # SQL
        if ext == '.sql':
            return SpecType.SQL

        # JSON Schema
        if 'schema' in name and ext == '.json':
            return SpecType.JSONSCHEMA

        # Markdown
        if ext == '.md':
            return SpecType.MARKDOWN

        return None

    def get_active_specs(self, project_id: int) -> List[Specification]:
        """Get all active (non-deprecated) specifications for a project.

        Args:
            project_id: Project ID

        Returns:
            List of active specifications
        """
        return self.list_by_project(project_id, status=SpecStatus.ACTIVE)

    def supersede(self, old_spec_id: int, new_spec_id: int) -> None:
        """Mark a specification as superseded by another.

        Args:
            old_spec_id: Specification being superseded
            new_spec_id: Specification that supersedes it
        """
        old_spec = self.get(old_spec_id)
        if not old_spec:
            raise ValueError(f"Specification {old_spec_id} not found")

        old_spec.status = SpecStatus.SUPERSEDED
        old_spec.description = (old_spec.description or "") + f"\n\nSuperseded by spec {new_spec_id}"
        self.update(old_spec)

        logger.info(f"Specification {old_spec_id} superseded by {new_spec_id}")

    def search_by_tags(self, project_id: int, tags: List[str], limit: int = 50) -> List[Specification]:
        """Search specifications by tags.

        Args:
            project_id: Project ID
            tags: Tags to search for
            limit: Maximum results

        Returns:
            Matching specifications
        """
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT * FROM specifications
            WHERE project_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (project_id, limit))

        rows = cursor.fetchall()
        specs = [self._row_to_model(row) for row in rows]

        # Filter by tags (since JSON search in SQLite is limited)
        matching = []
        for spec in specs:
            if any(tag in spec.tags for tag in tags):
                matching.append(spec)

        return matching
