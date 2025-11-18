"""Code indexing engine with semantic embeddings.

Indexes code elements with AST analysis and semantic embeddings
for efficient hybrid search across large codebases.
"""

import logging
from datetime import datetime
from typing import List, Optional

from .models import CodeElement

logger = logging.getLogger(__name__)


class CodeIndexer:
    """Index code elements with embeddings for semantic search."""

    def __init__(self, db=None, embedding_manager=None):
        """Initialize code indexer.

        Args:
            db: Database connection (optional, for persistent storage)
            embedding_manager: EmbeddingManager for generating embeddings
        """
        self.db = db
        self.embedding_manager = embedding_manager
        self.index_table_created = False

    def _init_schema(self) -> None:
        """Initialize database schema for code indexing.

        Note: In production, this integrates with existing Athena database.
        """
        if not self.db or self.index_table_created:
            return

        try:
            self.db.execute(
                """
                CREATE TABLE IF NOT EXISTS code_index (
                    id TEXT PRIMARY KEY,
                    file_path TEXT NOT NULL,
                    element_type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    language TEXT NOT NULL,
                    source_code TEXT,
                    docstring TEXT,
                    start_line INTEGER,
                    end_line INTEGER,
                    embedding BLOB,
                    embedding_model TEXT,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP
                )
            """
            )

            # Create indices for fast lookup
            self.db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_code_element_type
                ON code_index(element_type)
            """
            )

            self.db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_code_language
                ON code_index(language)
            """
            )

            self.db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_code_file_path
                ON code_index(file_path)
            """
            )

            self.index_table_created = True
            logger.info("Code index schema initialized")

        except Exception as e:
            logger.error(f"Error initializing code index schema: {e}")

    def index_elements(self, elements: List[CodeElement]) -> None:
        """Index a list of code elements.

        Args:
            elements: List of CodeElement objects to index
        """
        self._init_schema()

        for element in elements:
            try:
                # Generate embedding if available
                embedding = None
                if self.embedding_manager:
                    # Combine source code and docstring for embedding
                    text = element.source_code
                    if element.docstring:
                        text = f"{element.docstring}\n{text}"

                    try:
                        embedding_vector = self.embedding_manager.get_embedding(text)
                        if embedding_vector:
                            embedding = embedding_vector
                    except Exception as e:
                        logger.warning(f"Error generating embedding: {e}")

                # Store in database
                if self.db:
                    self.db.execute(
                        """
                        INSERT OR REPLACE INTO code_index
                        (id, file_path, element_type, name, language, source_code,
                         docstring, start_line, end_line, embedding, embedding_model,
                         created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            element.element_id,
                            element.file_path,
                            element.element_type.value,
                            element.name,
                            element.language.value,
                            element.source_code,
                            element.docstring,
                            element.start_line,
                            element.end_line,
                            embedding,
                            "anthropic" if embedding else None,
                            datetime.now(),
                            datetime.now(),
                        ),
                    )

                logger.debug(f"Indexed element: {element.element_id}")

            except Exception as e:
                logger.error(f"Error indexing element {element.element_id}: {e}")

    def clear_index(self, path_pattern: Optional[str] = None) -> None:
        """Clear indexed elements (optionally filtered by path).

        Args:
            path_pattern: Optional glob pattern to filter files to clear
        """
        if not self.db:
            return

        try:
            if path_pattern:
                self.db.execute(
                    """
                    DELETE FROM code_index WHERE file_path LIKE ?
                """,
                    (path_pattern,),
                )
            else:
                self.db.execute("DELETE FROM code_index")

            logger.info("Code index cleared")

        except Exception as e:
            logger.error(f"Error clearing index: {e}")

    def get_index_stats(self) -> dict:
        """Get statistics about the code index.

        Returns:
            Dictionary with index statistics
        """
        if not self.db:
            return {
                "total_elements": 0,
                "total_files": 0,
                "indexed_languages": [],
                "index_size_bytes": 0,
            }

        try:
            # Count elements
            total = self.db.execute_one("SELECT COUNT(*) as count FROM code_index")
            total_elements = total[0] if total else 0

            # Count files
            files = self.db.execute_one(
                """
                SELECT COUNT(DISTINCT file_path) as count FROM code_index
            """
            )
            total_files = files[0] if files else 0

            # List languages
            languages = self.db.execute(
                """
                SELECT DISTINCT language FROM code_index ORDER BY language
            """
            )
            indexed_languages = [row[0] for row in languages] if languages else []

            return {
                "total_elements": total_elements,
                "total_files": total_files,
                "indexed_languages": indexed_languages,
            }

        except Exception as e:
            logger.error(f"Error getting index stats: {e}")
            return {
                "total_elements": 0,
                "total_files": 0,
                "indexed_languages": [],
            }


class SpatialIndexer:
    """Track spatial relationships between code elements."""

    def __init__(self, db=None):
        """Initialize spatial indexer.

        Args:
            db: Database connection
        """
        self.db = db
        self.relationships_table_created = False

    def _init_schema(self) -> None:
        """Initialize spatial relationships schema."""
        if not self.db or self.relationships_table_created:
            return

        try:
            self.db.execute(
                """
                CREATE TABLE IF NOT EXISTS code_relationships (
                    id TEXT PRIMARY KEY,
                    source_element TEXT NOT NULL,
                    target_element TEXT NOT NULL,
                    relationship_type TEXT NOT NULL,
                    weight REAL,
                    created_at TIMESTAMP
                )
            """
            )

            self.db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_relationships_source
                ON code_relationships(source_element)
            """
            )

            self.relationships_table_created = True
            logger.info("Spatial index schema initialized")

        except Exception as e:
            logger.error(f"Error initializing spatial index: {e}")

    def add_relationship(
        self,
        source_id: str,
        target_id: str,
        rel_type: str,
        weight: float = 1.0,
    ) -> None:
        """Add a relationship between code elements.

        Args:
            source_id: Source element ID
            target_id: Target element ID
            rel_type: Type of relationship (imports, calls, extends, etc.)
            weight: Strength of relationship (0-1)
        """
        self._init_schema()

        if not self.db:
            return

        try:
            rel_id = f"{source_id}→{target_id}:{rel_type}"
            self.db.execute(
                """
                INSERT OR REPLACE INTO code_relationships
                (id, source_element, target_element, relationship_type, weight, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    rel_id,
                    source_id,
                    target_id,
                    rel_type,
                    weight,
                    datetime.now(),
                ),
            )
        except Exception as e:
            logger.error(f"Error adding relationship: {e}")

    def get_related_elements(self, element_id: str) -> List[tuple]:
        """Get all elements related to given element.

        Args:
            element_id: Element ID to find relationships for

        Returns:
            List of (target_element, relationship_type, weight) tuples
        """
        if not self.db:
            return []

        try:
            results = self.db.execute(
                """
                SELECT target_element, relationship_type, weight
                FROM code_relationships
                WHERE source_element = ?
                ORDER BY weight DESC
            """,
                (element_id,),
            )

            return results if results else []

        except Exception as e:
            logger.error(f"Error getting relationships: {e}")
            return []
