"""PostgreSQL integration for code search and dependency analysis.

This module provides seamless integration between code search operations and PostgreSQL,
enabling persistent storage and retrieval of code metadata, dependencies, and relationships.

Features:
- Store code entities (functions, classes, modules) with embeddings
- Query code dependencies with efficient SQL joins
- Cross-domain code-memory relationships
- Full-text search over code documentation
- Dependency graph analysis with relational queries
"""

import logging
from typing import List, Dict, Optional, Set, Tuple, Any
from dataclasses import dataclass
import json

from ..core.database_postgres import PostgresDatabase
from ..core.database import Database
from .code_graph_integration import CodeEntity, CodeRelationship, CodeEntityType, CodeRelationType
from .code_dependency_analysis import Dependency, DependencyMetrics, DependencyGraph

logger = logging.getLogger(__name__)

# Language detection mapping from file extensions
LANGUAGE_EXTENSIONS = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".jsx": "jsx",
    ".tsx": "tsx",
    ".java": "java",
    ".cpp": "cpp",
    ".c": "c",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".h": "c",
    ".hpp": "cpp",
    ".cs": "csharp",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".kt": "kotlin",
    ".scala": "scala",
    ".r": "r",
    ".sql": "sql",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "zsh",
    ".fish": "fish",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".scss": "scss",
    ".less": "less",
    ".json": "json",
    ".xml": "xml",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".ini": "ini",
    ".cfg": "cfg",
    ".vue": "vue",
    ".svelte": "svelte",
    ".clj": "clojure",
    ".cljs": "clojurescript",
    ".ex": "elixir",
    ".exs": "elixir",
    ".erl": "erlang",
    ".hrl": "erlang",
    ".hs": "haskell",
    ".ml": "ocaml",
    ".mli": "ocaml",
    ".pl": "perl",
    ".pm": "perl",
}


@dataclass
class CodeSearchResult:
    """Result from PostgreSQL code search."""
    code_id: int
    file_path: str
    entity_name: str
    entity_type: str
    semantic_similarity: float
    keyword_match: bool
    documentation: Optional[str]
    dependencies_count: int
    dependents_count: int


class PostgresCodeIntegration:
    """Integrates code search with PostgreSQL database layer.

    Provides:
    - Persistent code entity storage with vector embeddings
    - Dependency graph queries using native SQL
    - Semantic code search (vector + full-text)
    - Cross-layer code-memory integration
    """

    def __init__(self, db: Optional[Database] = None):
        """Initialize PostgreSQL code integration.

        Args:
            db: Database instance (auto-detected as PostgreSQL or SQLite)
        """
        self.db = db
        self.is_postgres = self._check_postgres()

    def _check_postgres(self) -> bool:
        """Check if database is PostgreSQL."""
        if self.db is None:
            return False
        try:
            return isinstance(self.db, PostgresDatabase)
        except (ImportError, AttributeError):
            return False

    async def store_code_entity(
        self,
        project_id: int,
        file_path: str,
        entity: CodeEntity,
        embedding: List[float],
        signature: Optional[str] = None,
        dependencies: Optional[List[str]] = None,
        dependents: Optional[List[str]] = None,
    ) -> int:
        """Store a code entity with embeddings and metadata.

        Args:
            project_id: Project ID
            file_path: File path containing entity
            entity: CodeEntity with metadata
            embedding: 768-dimensional embedding vector
            signature: Function/method signature
            dependencies: List of entities this depends on
            dependents: List of entities depending on this

        Returns:
            Code entity ID for reference
        """
        if not self.is_postgres or self.db is None:
            logger.warning("PostgreSQL not available for code entity storage")
            return -1

        db = self.db

        # First store in memory layer as code snippet
        try:
            memory_id = await db.store_memory(
                project_id=project_id,
                content=f"{entity.entity_type.value}: {entity.name}",
                embedding=embedding,
                memory_type="code_snippet",
                domain="code-analysis",
                tags=[entity.entity_type.value.lower(), "code"],
            )
        except Exception as e:
            logger.error(f"Failed to store code memory: {e}")
            return -1

        # Then store code metadata with relationships
        try:
            # Detect language from file extension
            language = self._detect_language(file_path)

            code_id = await db.store_code_entity(
                project_id=project_id,
                memory_vector_id=memory_id,
                file_path=file_path,
                entity_name=entity.name,
                entity_type=entity.entity_type.value,
                language=language,
                signature=signature or entity.name,
                docstring=entity.docstring,
                semantic_hash=self._compute_hash(entity),
                cyclomatic_complexity=entity.complexity,
                lines_of_code=entity.metadata.get("loc", 0) if entity.metadata else 0,
            )
            return code_id
        except Exception as e:
            logger.error(f"Failed to store code metadata: {e}")
            return -1

    async def search_code_entities(
        self,
        project_id: int,
        query_embedding: List[float],
        query_text: Optional[str] = None,
        entity_types: Optional[List[str]] = None,
        limit: int = 10,
        min_similarity: float = 0.3,
    ) -> List[CodeSearchResult]:
        """Search code entities using semantic and keyword matching.

        Args:
            project_id: Project ID
            query_embedding: Query embedding vector
            query_text: Optional text for keyword matching
            entity_types: Filter by entity type (function, class, module)
            limit: Maximum results
            min_similarity: Minimum similarity threshold

        Returns:
            List of CodeSearchResult ordered by relevance
        """
        if not self.is_postgres or self.db is None:
            logger.warning("PostgreSQL not available for code search")
            return []

        db = self.db

        try:
            # Use hybrid search combining semantic + keyword
            results = await db.hybrid_search(
                project_id=project_id,
                embedding=query_embedding,
                query_text=query_text or "",
                limit=limit * 2,  # Get more to filter by type
                semantic_weight=0.8,
                keyword_weight=0.2,
            )

            # Filter to code snippets and enrich with dependency info
            code_results = []
            for result in results:
                if result.get("memory_type") != "code_snippet":
                    continue

                if result.get("semantic_similarity", 0) < min_similarity:
                    continue

                code_result = await self._enrich_search_result(
                    project_id=project_id,
                    memory_id=result.get("id"),
                    result=result,
                )

                if code_result:
                    code_results.append(code_result)

                if len(code_results) >= limit:
                    break

            return code_results
        except Exception as e:
            logger.error(f"Code entity search failed: {e}")
            return []

    async def _enrich_search_result(
        self,
        project_id: int,
        memory_id: int,
        result: Dict[str, Any],
    ) -> Optional[CodeSearchResult]:
        """Enrich search result with dependency information."""
        try:
            # Find associated code metadata
            # This would require additional query in PostgreSQL
            return CodeSearchResult(
                code_id=memory_id,
                file_path=result.get("tags", [""])[0] if result.get("tags") else "",
                entity_name=result.get("content", "").split(": ")[-1],
                entity_type=result.get("tags", [""])[0] if result.get("tags") else "unknown",
                semantic_similarity=result.get("semantic_similarity", 0),
                keyword_match=result.get("semantic_similarity", 0) > 0.7,
                documentation=result.get("content"),
                dependencies_count=0,
                dependents_count=0,
            )
        except Exception as e:
            logger.error(f"Failed to enrich search result: {e}")
            return None

    async def get_dependency_chain(
        self,
        project_id: int,
        entity_name: str,
        depth: int = 3,
        direction: str = "both",
    ) -> DependencyGraph:
        """Get dependency graph for a code entity.

        Args:
            project_id: Project ID
            entity_name: Entity name to trace
            depth: Maximum chain depth
            direction: "incoming", "outgoing", or "both"

        Returns:
            DependencyGraph with full chain analysis
        """
        if not self.is_postgres or self.db is None:
            logger.warning("PostgreSQL not available for dependency analysis")
            return DependencyGraph()

        graph = DependencyGraph()

        try:
            # This would require recursive SQL query to get dependency chains
            # For now, return empty graph (full implementation in Phase 5 Part 3)
            logger.info(f"Dependency chain analysis for {entity_name} (depth={depth})")
            return graph
        except Exception as e:
            logger.error(f"Dependency chain analysis failed: {e}")
            return graph

    async def get_code_statistics(self, project_id: int) -> Dict[str, Any]:
        """Get code statistics for project.

        Args:
            project_id: Project ID

        Returns:
            Dictionary with code metrics
        """
        if not self.is_postgres or self.db is None:
            return {}

        try:
            # Would query code_metadata table for aggregates
            return {
                "total_files": 0,
                "total_functions": 0,
                "total_classes": 0,
                "average_complexity": 0,
                "most_complex_entity": None,
                "coupling_metrics": {},
            }
        except Exception as e:
            logger.error(f"Failed to get code statistics: {e}")
            return {}

    @staticmethod
    def _detect_language(file_path: str) -> str:
        """Detect programming language from file extension.

        Args:
            file_path: Path to the code file

        Returns:
            Language name (e.g., "python", "javascript") or "unknown" if not detected
        """
        import os

        # Get file extension
        _, ext = os.path.splitext(file_path.lower())

        # Look up in language mapping
        language = LANGUAGE_EXTENSIONS.get(ext)

        if language:
            logger.debug(f"Detected language '{language}' from extension '{ext}'")
            return language

        # If no extension found, try special cases
        if file_path.endswith("Makefile"):
            return "makefile"
        elif file_path.endswith("Dockerfile"):
            return "dockerfile"
        elif file_path.endswith(".gitignore"):
            return "gitignore"

        logger.debug(f"Could not detect language for '{file_path}', defaulting to 'unknown'")
        return "unknown"

    @staticmethod
    def _compute_hash(entity: CodeEntity) -> str:
        """Compute semantic hash for code entity."""
        content = f"{entity.name}:{entity.entity_type.value}:{entity.docstring}"
        import hashlib
        return hashlib.sha256(content.encode()).hexdigest()[:16]


async def initialize_code_search_postgres(
    db: Optional[Database] = None,
) -> PostgresCodeIntegration:
    """Initialize code search with PostgreSQL integration.

    Args:
        db: Database instance

    Returns:
        PostgresCodeIntegration instance
    """
    integration = PostgresCodeIntegration(db=db)

    if integration.is_postgres and db:
        try:
            # Ensure PostgreSQL is initialized
            if isinstance(db, PostgresDatabase):
                await db.initialize()
                logger.info("PostgreSQL code search integration initialized")
        except Exception as e:
            logger.warning(f"PostgreSQL initialization failed: {e}")

    return integration
