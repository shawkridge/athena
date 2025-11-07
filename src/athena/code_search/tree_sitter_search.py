"""Tree-Sitter based semantic code search implementation."""

import time
from pathlib import Path
from typing import List, Optional, Dict
import logging

from .models import CodeUnit, SearchResult, SearchQuery
from .indexer import CodebaseIndexer
from .semantic_searcher import SemanticCodeSearcher
from .parser import CodeParser
from .cache import CombinedSearchCache
from .code_analysis_memory import CodeAnalysisMemory

logger = logging.getLogger(__name__)


class TreeSitterCodeSearch:
    """
    Semantic code search using AST parsing and embeddings.

    Provides multiple search strategies:
    1. Semantic search via embeddings
    2. Structural search via AST patterns
    3. Graph-based dependency search
    """

    def __init__(
        self,
        repo_path: str,
        language: str = "python",
        embed_manager=None,
        graph_store=None,
        enable_cache: bool = True,
        episodic_store=None,
        semantic_store=None,
        consolidator=None,
        project_id: int = 0,
    ):
        """
        Initialize code search system.

        Args:
            repo_path: Path to code repository to index
            language: Primary language (default: python)
            embed_manager: EmbeddingManager instance for semantic search
            graph_store: GraphStore instance for knowledge graph integration
            enable_cache: Enable caching for search results (default: True)
            episodic_store: EpisodicStore for recording analysis events
            semantic_store: SemanticStore for storing insights
            consolidator: Consolidator for pattern extraction
            project_id: Project identifier for memory tracking
        """
        self.repo_path = Path(repo_path)
        self.language = language
        self.embed_manager = embed_manager
        self.graph_store = graph_store
        self.enable_cache = enable_cache

        # Initialize components
        self.parser = CodeParser(language)
        self.indexer = CodebaseIndexer(str(repo_path), language, embed_manager)
        self.semantic_searcher = None  # Created after indexing

        # Initialize cache
        self.cache = CombinedSearchCache() if enable_cache else None

        # Initialize memory integration
        self.analysis_memory = CodeAnalysisMemory(
            episodic_store=episodic_store,
            semantic_store=semantic_store,
            graph_store=graph_store,
            consolidator=consolidator,
            project_id=project_id,
        )

        self._is_indexed = False
        self._index_start_time = None

    def build_index(self, languages: Optional[List[str]] = None) -> Dict:
        """
        Build semantic index of codebase.

        Args:
            languages: List of languages to parse (default: python)

        Returns:
            Dictionary with indexing statistics

        Raises:
            ValueError: If repo path doesn't exist
        """
        if not self.repo_path.exists():
            raise ValueError(f"Repository path does not exist: {self.repo_path}")

        logger.info(f"Building index for {self.repo_path}")
        self._index_start_time = time.time()

        # Index the directory
        self.indexer.index_directory()

        # Create semantic searcher from indexed units
        self.semantic_searcher = SemanticCodeSearcher(
            self.indexer, self.embed_manager
        )

        # Add units to graph store if available
        if self.graph_store:
            self._add_units_to_graph()

        # Add units to knowledge graph via memory system
        units_list = [u.to_dict() for u in self.indexer.get_units()]
        self.analysis_memory.add_code_entities_to_graph(
            code_units=units_list,
            repo_path=str(self.repo_path),
        )

        self._is_indexed = True

        # Return statistics
        stats = self.indexer.get_statistics()
        logger.info(
            f"Index built: {stats['units_extracted']} units "
            f"from {stats['files_indexed']} files "
            f"in {stats['indexing_time']:.2f}s"
        )

        # Record indexing event to memory
        duration_ms = int((time.time() - self._index_start_time) * 1000)
        self.analysis_memory.record_code_analysis(
            repo_path=str(self.repo_path),
            analysis_results={
                "type": "indexing",
                "quality_score": 1.0,  # Indexing is always successful
                "complexity_avg": stats.get("avg_complexity", 0),
                "test_coverage": "N/A",
                "issues": [],
            },
            duration_ms=duration_ms,
            file_count=stats.get("files_indexed", 0),
            unit_count=stats.get("units_extracted", 0),
        )

        # Store insights to semantic memory
        self.analysis_memory.store_code_insights(
            analysis_results={
                "quality_score": 1.0,
                "complexity_avg": stats.get("avg_complexity", 0),
                "test_coverage": "N/A",
                "issues": [],
            },
            repo_path=str(self.repo_path),
            tags=["code_indexing", "static_analysis"],
        )

        # Record metrics for trend analysis
        self.analysis_memory.record_code_metrics_trend(
            metrics={
                "files_indexed": stats.get("files_indexed", 0),
                "units_extracted": stats.get("units_extracted", 0),
                "avg_complexity": stats.get("avg_complexity", 0),
                "indexing_time_ms": duration_ms,
            },
            repo_path=str(self.repo_path),
        )

        return stats

    def search(
        self,
        query: str,
        top_k: int = 10,
        min_score: float = 0.3,
    ) -> List[SearchResult]:
        """
        Semantic search for code units.

        Args:
            query: Search query string
            top_k: Maximum number of results to return
            min_score: Minimum relevance score threshold

        Returns:
            List of SearchResult objects, ranked by relevance

        Raises:
            RuntimeError: If index not built yet
        """
        if not self._is_indexed or not self.semantic_searcher:
            raise RuntimeError("Index not built. Call build_index() first.")

        logger.info(f"Searching for: {query}")

        # Check cache first
        if self.cache:
            cached_results = self.cache.search_cache.get(query, top_k, min_score)
            if cached_results is not None:
                logger.debug(f"Cache hit for query: {query}")
                return cached_results

        # Perform semantic search
        results = self.semantic_searcher.search(
            query, limit=top_k, min_score=min_score
        )

        # Cache results
        if self.cache:
            self.cache.search_cache.set(query, top_k, min_score, results)

        logger.debug(f"Found {len(results)} results for query: {query}")

        return results

    def search_by_type(
        self,
        unit_type: str,
        query: Optional[str] = None,
        top_k: int = 10,
    ) -> List[SearchResult]:
        """
        Search code units by type.

        Args:
            unit_type: Type to search for (function, class, import)
            query: Optional text query for further filtering
            top_k: Maximum number of results to return

        Returns:
            List of SearchResult objects

        Raises:
            RuntimeError: If index not built yet
        """
        if not self._is_indexed or not self.semantic_searcher:
            raise RuntimeError("Index not built. Call build_index() first.")

        results = self.semantic_searcher.search_by_type(unit_type, query, top_k)
        return results

    def search_by_name(
        self,
        name_query: str,
        top_k: int = 10,
        exact: bool = False,
    ) -> List[SearchResult]:
        """
        Search code units by name.

        Args:
            name_query: Name to search for
            top_k: Maximum number of results to return
            exact: If True, only exact matches

        Returns:
            List of SearchResult objects

        Raises:
            RuntimeError: If index not built yet
        """
        if not self._is_indexed or not self.semantic_searcher:
            raise RuntimeError("Index not built. Call build_index() first.")

        results = self.semantic_searcher.search_by_name(name_query, top_k, exact)
        return results

    def find_similar(
        self,
        unit_id: str,
        top_k: int = 5,
        min_score: float = 0.3,
    ) -> List[SearchResult]:
        """
        Find code units similar to a reference unit.

        Args:
            unit_id: ID of reference unit
            top_k: Maximum number of results to return
            min_score: Minimum similarity score

        Returns:
            List of similar SearchResult objects

        Raises:
            RuntimeError: If index not built yet
        """
        if not self._is_indexed or not self.semantic_searcher:
            raise RuntimeError("Index not built. Call build_index() first.")

        results = self.semantic_searcher.find_similar(unit_id, top_k, min_score)
        return results

    def analyze_file(self, file_path: str) -> Dict:
        """
        Analyze structure of a code file.

        Args:
            file_path: Path to code file

        Returns:
            Dictionary with file structure (functions, classes, imports)
        """
        if not Path(file_path).exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        logger.info(f"Analyzing file: {file_path}")

        # Parse the file
        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()

        units = self.parser.extract_all(code, str(file_path))

        # Organize by type
        functions = [u for u in units if u.type == "function"]
        classes = [u for u in units if u.type == "class"]
        imports = [u for u in units if u.type.startswith("import")]

        return {
            "file": file_path,
            "functions": [u.to_dict() for u in functions],
            "classes": [u.to_dict() for u in classes],
            "imports": [u.to_dict() for u in imports],
            "total_units": len(units),
        }

    def find_dependencies(
        self, file_path: str, entity_name: str
    ) -> Dict:
        """
        Find dependencies of a code entity.

        Args:
            file_path: Path to code file
            entity_name: Name of function/class to analyze

        Returns:
            Dictionary with dependencies and related code

        Raises:
            RuntimeError: If index not built yet
        """
        if not self._is_indexed:
            raise RuntimeError("Index not built. Call build_index() first.")

        logger.info(f"Finding dependencies for {entity_name} in {file_path}")

        # Find all units in the file with matching name
        matching_units = self.semantic_searcher.indexer.find_by_file(file_path)
        target_unit = None

        for unit in matching_units:
            if unit.name == entity_name:
                target_unit = unit
                break

        if not target_unit:
            return {
                "entity": entity_name,
                "file": file_path,
                "found": False,
                "direct_dependencies": [],
                "transitive_dependencies": [],
                "dependents": [],
            }

        # Get direct dependencies
        direct_deps = target_unit.dependencies

        # Find transitive dependencies
        transitive_deps = set()
        for dep_name in direct_deps:
            dep_units = self.semantic_searcher.indexer.find_by_name(dep_name)
            for dep_unit in dep_units:
                transitive_deps.update(dep_unit.dependencies)

        # Find units that depend on this one (dependents)
        dependents = []
        for unit in self.semantic_searcher.units:
            if entity_name in unit.dependencies:
                dependents.append(unit.name)

        return {
            "entity": entity_name,
            "file": file_path,
            "found": True,
            "direct_dependencies": list(direct_deps),
            "transitive_dependencies": list(transitive_deps),
            "dependents": list(set(dependents)),
        }

    def get_code_statistics(self) -> Dict:
        """Get comprehensive statistics about indexed code."""
        if not self._is_indexed:
            return {"indexed": False}

        return self.semantic_searcher.get_search_stats()

    def analyze_codebase(self) -> Dict:
        """
        Comprehensive codebase analysis with memory recording.

        Analyzes code structure, quality metrics, and trends.
        Records analysis to episodic memory for learning.

        Returns:
            Dictionary with analysis results
        """
        if not self._is_indexed:
            raise RuntimeError("Index not built. Call build_index() first.")

        logger.info(f"Running comprehensive analysis on {self.repo_path}")
        start_time = time.time()

        # Get basic statistics
        stats = self.indexer.get_statistics()

        # Calculate quality metrics
        units = self.indexer.get_units()
        complexities = [u.complexity for u in units if hasattr(u, "complexity")]
        avg_complexity = sum(complexities) / len(complexities) if complexities else 0

        # Analyze issues (simplified - would integrate with linters in production)
        issues = []
        for unit in units:
            if hasattr(unit, "complexity") and unit.complexity > 10:
                issues.append({
                    "type": "high_complexity",
                    "unit": unit.name,
                    "value": unit.complexity,
                })

        # Create analysis results
        analysis_results = {
            "type": "comprehensive_analysis",
            "quality_score": max(0, 1.0 - (len(issues) / max(1, len(units)) * 0.5)),
            "complexity_avg": avg_complexity,
            "test_coverage": "N/A",  # Would integrate with coverage tools
            "issues": issues,
        }

        # Record to memory
        duration_ms = int((time.time() - start_time) * 1000)
        self.analysis_memory.record_code_analysis(
            repo_path=str(self.repo_path),
            analysis_results=analysis_results,
            duration_ms=duration_ms,
            file_count=stats.get("files_indexed", 0),
            unit_count=stats.get("units_extracted", 0),
        )

        # Store insights
        self.analysis_memory.store_code_insights(
            analysis_results=analysis_results,
            repo_path=str(self.repo_path),
            tags=["comprehensive_analysis", "quality_metrics"],
        )

        # Extract patterns from past analyses
        patterns = self.analysis_memory.extract_analysis_patterns(days_back=7)
        if patterns:
            analysis_results["trends"] = patterns

        logger.info(f"Analysis complete in {duration_ms}ms")

        return {
            **stats,
            **analysis_results,
            "duration_ms": duration_ms,
        }

    def get_cache_stats(self) -> Dict:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        if not self.cache:
            return {"cache_enabled": False}

        return {
            "cache_enabled": True,
            **self.cache.get_stats(),
        }

    def clear_cache(self) -> None:
        """Clear all cached results."""
        if self.cache:
            self.cache.clear_all()
            logger.info("Cache cleared")

    def _add_units_to_graph(self) -> None:
        """Add indexed units to graph store as entities."""
        if not self.graph_store:
            return

        logger.info("Adding code units to graph store")

        for unit in self.semantic_searcher.units:
            try:
                # Add unit as entity
                self.graph_store.add_entity(
                    entity_id=unit.id,
                    entity_type=unit.type,
                    properties={
                        "name": unit.name,
                        "file": unit.file_path,
                        "signature": unit.signature,
                        "docstring": unit.docstring,
                    },
                )

                # Add dependency relations
                for dep in unit.dependencies:
                    self.graph_store.add_relation(
                        source_id=unit.id,
                        target_id=dep,
                        relation_type="depends_on",
                        properties={"type": unit.type},
                    )
            except Exception as e:
                logger.warning(f"Failed to add unit {unit.id} to graph: {e}")

    @property
    def is_indexed(self) -> bool:
        """Check if index has been built."""
        return self._is_indexed

    @property
    def index_stats(self) -> Dict:
        """Get statistics about the current index."""
        if not self._is_indexed:
            return {
                "indexed": False,
                "repo_path": str(self.repo_path),
                "language": self.language,
            }

        return {
            "indexed": True,
            "repo_path": str(self.repo_path),
            "language": self.language,
            **self.indexer.get_statistics(),
        }
