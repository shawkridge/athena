"""Document storage and management.

This module provides storage for generated documentation with hybrid storage:
- Database: Metadata, relationships, generation tracking
- Filesystem: Actual document content in Markdown files
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Optional

from ..core.database import Database
from ..core.base_store import BaseStore
from .models import Document, DocumentType, DocumentStatus

logger = logging.getLogger(__name__)


class DocumentStore(BaseStore):
    """Store for managing documentation with hybrid storage.

    Documents are stored in:
    - Database: Metadata, relationships, generation info
    - Filesystem: docs/ directory with Markdown files

    Example:
        >>> db = get_database()
        >>> store = DocumentStore(db)
        >>> doc = Document(
        ...     project_id=1,
        ...     name="User API Documentation",
        ...     doc_type=DocumentType.API_DOC,
        ...     version="1.0.0",
        ...     content="# User API..."
        ... )
        >>> doc_id = store.create(doc)
    """

    # Required by BaseStore
    table_name = "documents"
    model_class = Document

    def __init__(self, db: Database, docs_dir: Optional[Path] = None):
        """Initialize document store.

        Args:
            db: Database instance
            docs_dir: Base directory for document files (default: ./docs)
        """
        super().__init__(db)
        self.docs_dir = docs_dir or Path("docs")
        self._init_schema()

    def _init_schema(self):
        """Create documents table if it doesn't exist."""
        # Skip for PostgreSQL async databases
        if not hasattr(self.db, 'conn'):
            logger.debug("PostgreSQL async database detected, skipping schema creation")
            return

        cursor = self.db.conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                doc_type TEXT NOT NULL,
                version TEXT NOT NULL,
                status TEXT NOT NULL,
                content TEXT NOT NULL,
                file_path TEXT,
                description TEXT,

                -- Source relationships (JSON arrays of IDs)
                based_on_spec_ids TEXT DEFAULT '[]',
                based_on_doc_ids TEXT DEFAULT '[]',

                -- Architecture relationships
                related_adr_ids TEXT DEFAULT '[]',
                implements_constraint_ids TEXT DEFAULT '[]',

                -- Generation metadata
                generated_by TEXT,
                generation_prompt TEXT,
                generation_model TEXT,
                last_synced_at REAL,
                sync_hash TEXT,

                -- Validation
                validation_status TEXT,
                validated_at REAL,

                -- Review tracking (JSON arrays)
                author TEXT,
                reviewers TEXT DEFAULT '[]',
                tags TEXT DEFAULT '[]',

                -- Timestamps
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,

                FOREIGN KEY (project_id) REFERENCES projects(id)
            )
        """)

        # Create indices for common queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_documents_project_id
            ON documents(project_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_documents_doc_type
            ON documents(doc_type)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_documents_status
            ON documents(status)
        """)

        # Add Phase 4E columns for manual edit tracking (if they don't exist)
        try:
            cursor.execute("ALTER TABLE documents ADD COLUMN ai_baseline_hash TEXT")
        except Exception:
            pass  # Column already exists

        try:
            cursor.execute("ALTER TABLE documents ADD COLUMN ai_baseline_content TEXT")
        except Exception:
            pass  # Column already exists

        try:
            cursor.execute("ALTER TABLE documents ADD COLUMN manual_override INTEGER DEFAULT 0")
        except Exception:
            pass  # Column already exists

        try:
            cursor.execute("ALTER TABLE documents ADD COLUMN manual_edit_detected INTEGER DEFAULT 0")
        except Exception:
            pass  # Column already exists

        try:
            cursor.execute("ALTER TABLE documents ADD COLUMN last_manual_edit_at REAL")
        except Exception:
            pass  # Column already exists

        # Create index for manual_override to speed up queries
        try:
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_documents_manual_override
                ON documents(manual_override)
            """)
        except Exception:
            pass

        self.db.conn.commit()
        logger.debug("Documents schema initialized")

    def create(self, doc: Document, write_to_file: bool = True) -> int:
        """Create a new document.

        Args:
            doc: Document to create
            write_to_file: Whether to write content to file (default: True)

        Returns:
            ID of created document

        Example:
            >>> doc = Document(
            ...     project_id=1,
            ...     name="API Docs",
            ...     doc_type=DocumentType.API_DOC,
            ...     version="1.0.0",
            ...     content="# API Documentation..."
            ... )
            >>> doc_id = store.create(doc)
        """
        # Write to filesystem if requested and file_path is set
        if write_to_file and doc.file_path:
            file_path = self.docs_dir / doc.file_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(doc.content)
            logger.info(f"Wrote document to: {file_path}")

        # Insert into database
        cursor = self.db.conn.cursor()
        cursor.execute("""
            INSERT INTO documents (
                project_id, name, doc_type, version, status,
                content, file_path, description,
                based_on_spec_ids, based_on_doc_ids,
                related_adr_ids, implements_constraint_ids,
                generated_by, generation_prompt, generation_model,
                last_synced_at, sync_hash,
                validation_status, validated_at,
                author, reviewers, tags,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            doc.project_id,
            doc.name,
            doc.doc_type,
            doc.version,
            doc.status,
            doc.content,
            doc.file_path,
            doc.description,
            json.dumps(doc.based_on_spec_ids),
            json.dumps(doc.based_on_doc_ids),
            json.dumps(doc.related_adr_ids),
            json.dumps(doc.implements_constraint_ids),
            doc.generated_by,
            doc.generation_prompt,
            doc.generation_model,
            doc.last_synced_at.timestamp() if doc.last_synced_at else None,
            doc.sync_hash,
            doc.validation_status,
            doc.validated_at.timestamp() if doc.validated_at else None,
            doc.author,
            json.dumps(doc.reviewers),
            json.dumps(doc.tags),
            doc.created_at.timestamp(),
            doc.updated_at.timestamp(),
        ))

        self.db.conn.commit()
        doc_id = cursor.lastrowid

        logger.info(f"Created document {doc_id}: {doc.name} ({doc.doc_type})")
        return doc_id

    def get(self, doc_id: int) -> Optional[Document]:
        """Get document by ID.

        Args:
            doc_id: Document ID

        Returns:
            Document if found, None otherwise

        Example:
            >>> doc = store.get(5)
            >>> print(doc.name)
            "User API Documentation"
        """
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
        row = cursor.fetchone()

        if not row:
            return None

        return self._row_to_model(row)

    def get_by_file_path(self, file_path: str) -> Optional[Document]:
        """Get document by file path.

        Args:
            file_path: Relative file path

        Returns:
            Document if found, None otherwise
        """
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT * FROM documents WHERE file_path = ?", (file_path,))
        row = cursor.fetchone()

        if not row:
            return None

        return self._row_to_model(row)

    def update(self, doc: Document, write_to_file: bool = True) -> None:
        """Update an existing document.

        Args:
            doc: Document to update
            write_to_file: Whether to update file (default: True)

        Example:
            >>> doc = store.get(5)
            >>> doc.content = "# Updated content..."
            >>> doc.version = "2.0.0"
            >>> store.update(doc)
        """
        if not doc.id:
            raise ValueError("Document must have an ID to update")

        # Update file if requested and file_path is set
        if write_to_file and doc.file_path:
            file_path = self.docs_dir / doc.file_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(doc.content)
            logger.info(f"Updated document file: {file_path}")

        # Update database
        doc.updated_at = datetime.now()

        cursor = self.db.conn.cursor()
        cursor.execute("""
            UPDATE documents SET
                name = ?, doc_type = ?, version = ?, status = ?,
                content = ?, file_path = ?, description = ?,
                based_on_spec_ids = ?, based_on_doc_ids = ?,
                related_adr_ids = ?, implements_constraint_ids = ?,
                generated_by = ?, generation_prompt = ?, generation_model = ?,
                last_synced_at = ?, sync_hash = ?,
                validation_status = ?, validated_at = ?,
                author = ?, reviewers = ?, tags = ?,
                ai_baseline_hash = ?, ai_baseline_content = ?,
                manual_override = ?, manual_edit_detected = ?,
                last_manual_edit_at = ?,
                updated_at = ?
            WHERE id = ?
        """, (
            doc.name,
            doc.doc_type,
            doc.version,
            doc.status,
            doc.content,
            doc.file_path,
            doc.description,
            json.dumps(doc.based_on_spec_ids),
            json.dumps(doc.based_on_doc_ids),
            json.dumps(doc.related_adr_ids),
            json.dumps(doc.implements_constraint_ids),
            doc.generated_by,
            doc.generation_prompt,
            doc.generation_model,
            doc.last_synced_at.timestamp() if doc.last_synced_at else None,
            doc.sync_hash,
            doc.validation_status,
            doc.validated_at.timestamp() if doc.validated_at else None,
            doc.author,
            json.dumps(doc.reviewers),
            json.dumps(doc.tags),
            getattr(doc, 'ai_baseline_hash', None),
            getattr(doc, 'ai_baseline_content', None),
            1 if getattr(doc, 'manual_override', False) else 0,
            1 if getattr(doc, 'manual_edit_detected', False) else 0,
            getattr(doc, 'last_manual_edit_at', None).timestamp() if getattr(doc, 'last_manual_edit_at', None) else None,
            doc.updated_at.timestamp(),
            doc.id,
        ))

        self.db.conn.commit()
        logger.info(f"Updated document {doc.id}")

    def delete(self, doc_id: int, delete_file: bool = False) -> bool:
        """Delete a document.

        Args:
            doc_id: Document ID
            delete_file: Whether to also delete the file (default: False)

        Returns:
            True if deleted, False if not found

        Example:
            >>> store.delete(5, delete_file=True)
            True
        """
        # Get document to find file path
        doc = self.get(doc_id)
        if not doc:
            return False

        # Delete from database
        cursor = self.db.conn.cursor()
        cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        self.db.conn.commit()

        # Delete file if requested
        if delete_file and doc.file_path:
            file_path = self.docs_dir / doc.file_path
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Deleted document file: {file_path}")

        logger.info(f"Deleted document {doc_id}")
        return True

    def list_by_project(
        self,
        project_id: int,
        doc_type: Optional[DocumentType] = None,
        status: Optional[DocumentStatus] = None,
        limit: int = 100,
    ) -> List[Document]:
        """List documents for a project.

        Args:
            project_id: Project ID
            doc_type: Optional filter by document type
            status: Optional filter by status
            limit: Maximum number of results

        Returns:
            List of documents

        Example:
            >>> docs = store.list_by_project(1, doc_type=DocumentType.API_DOC)
            >>> for doc in docs:
            ...     print(f"{doc.name} v{doc.version}")
        """
        cursor = self.db.conn.cursor()

        # Build query with filters
        query = "SELECT * FROM documents WHERE project_id = ?"
        params = [project_id]

        if doc_type:
            query += " AND doc_type = ?"
            params.append(doc_type)

        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()

        return [self._row_to_model(row) for row in rows]

    def list_by_spec(self, spec_id: int) -> List[Document]:
        """List documents generated from a specification.

        Args:
            spec_id: Specification ID

        Returns:
            List of documents based on this spec

        Example:
            >>> docs = store.list_by_spec(5)  # All docs from spec 5
        """
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT * FROM documents")
        rows = cursor.fetchall()

        # Filter by spec ID in based_on_spec_ids JSON array
        docs = []
        for row in rows:
            doc = self._row_to_model(row)
            if spec_id in doc.based_on_spec_ids:
                docs.append(doc)

        return docs

    def _row_to_model(self, row) -> Document:
        """Convert database row to Document model.

        Args:
            row: Database row

        Returns:
            Document instance
        """
        doc = Document(
            id=row[0],
            project_id=row[1],
            name=row[2],
            doc_type=DocumentType(row[3]),
            version=row[4],
            status=DocumentStatus(row[5]),
            content=row[6],
            file_path=row[7],
            description=row[8],
            based_on_spec_ids=json.loads(row[9]),
            based_on_doc_ids=json.loads(row[10]),
            related_adr_ids=json.loads(row[11]),
            implements_constraint_ids=json.loads(row[12]),
            generated_by=row[13],
            generation_prompt=row[14],
            generation_model=row[15],
            last_synced_at=datetime.fromtimestamp(row[16]) if row[16] else None,
            sync_hash=row[17],
            validation_status=row[18],
            validated_at=datetime.fromtimestamp(row[19]) if row[19] else None,
            author=row[20],
            reviewers=json.loads(row[21]),
            tags=json.loads(row[22]),
            created_at=datetime.fromtimestamp(row[23]),
            updated_at=datetime.fromtimestamp(row[24]),
        )

        # Add Phase 4E fields if present (safe for old databases)
        if len(row) > 25:
            doc.ai_baseline_hash = row[25]
        if len(row) > 26:
            doc.ai_baseline_content = row[26]
        if len(row) > 27:
            doc.manual_override = bool(row[27])
        if len(row) > 28:
            doc.manual_edit_detected = bool(row[28])
        if len(row) > 29 and row[29]:
            doc.last_manual_edit_at = datetime.fromtimestamp(row[29])

        return doc
