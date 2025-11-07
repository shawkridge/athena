"""Codebase indexer for building semantic indices."""

import logging
from pathlib import Path
from typing import List, Optional, Set, Dict
import time

from .models import CodeUnit
from .parser import CodeParser

logger = logging.getLogger(__name__)


class CodebaseIndexer:
    """
    Index a codebase for semantic code search.

    Scans directory, parses files, generates embeddings, and builds
    semantic index for search.
    """

    # Default file extensions to index by language
    DEFAULT_EXTENSIONS = {
        "python": [".py"],
        "javascript": [".js", ".jsx"],
        "typescript": [".ts", ".tsx"],
        "java": [".java"],
        "go": [".go"],
    }

    # Files/directories to skip
    SKIP_PATTERNS = {
        "__pycache__",
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "dist",
        "build",
        ".pytest_cache",
        ".mypy_cache",
        "*.egg-info",
    }

    def __init__(
        self,
        repo_path: str,
        language: str = "python",
        embedding_manager=None,
        skip_patterns: Optional[Set[str]] = None,
    ):
        """
        Initialize code indexer.

        Args:
            repo_path: Path to code repository
            language: Primary language to index
            embedding_manager: EmbeddingManager for generating embeddings
            skip_patterns: Additional patterns to skip
        """
        self.repo_path = Path(repo_path)
        self.language = language
        self.embedding_manager = embedding_manager
        self.parser = CodeParser(language)

        # Setup skip patterns
        self.skip_patterns = self.SKIP_PATTERNS.copy()
        if skip_patterns:
            self.skip_patterns.update(skip_patterns)

        # Indexed units
        self.units: List[CodeUnit] = []
        self.unit_index: Dict[str, CodeUnit] = {}  # id -> CodeUnit

        # Statistics
        self.stats = {
            "files_scanned": 0,
            "files_indexed": 0,
            "files_skipped": 0,
            "units_extracted": 0,
            "errors": 0,
            "indexing_time": 0.0,
        }

    def index_directory(
        self, extensions: Optional[List[str]] = None, recursive: bool = True
    ) -> List[CodeUnit]:
        """
        Index all code files in directory.

        Args:
            extensions: File extensions to index (default from language)
            recursive: Whether to recurse into subdirectories

        Returns:
            List of indexed CodeUnit objects

        Raises:
            ValueError: If repo path doesn't exist
        """
        if not self.repo_path.exists():
            raise ValueError(f"Repository path does not exist: {self.repo_path}")

        if extensions is None:
            extensions = self.DEFAULT_EXTENSIONS.get(self.language, [".py"])

        start_time = time.time()
        logger.info(f"Starting indexing of {self.repo_path}")

        # Find files to index
        files_to_index = self._find_files(extensions, recursive)
        logger.info(f"Found {len(files_to_index)} files to index")

        # Index each file
        for file_path in files_to_index:
            self.index_file(file_path)

        # Record statistics
        self.stats["indexing_time"] = time.time() - start_time

        logger.info(
            f"Indexing complete: {self.stats['units_extracted']} units "
            f"from {self.stats['files_indexed']} files "
            f"in {self.stats['indexing_time']:.2f}s"
        )

        return self.units

    def index_file(self, file_path: str) -> List[CodeUnit]:
        """
        Index a single code file.

        Args:
            file_path: Path to code file

        Returns:
            List of CodeUnit objects extracted from file

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        self.stats["files_scanned"] += 1

        # Check if file should be skipped
        if self._should_skip(file_path):
            self.stats["files_skipped"] += 1
            return []

        try:
            # Read file
            with open(file_path, "r", encoding="utf-8") as f:
                code = f.read()

            # Parse file
            units = self.parser.extract_all(code, str(file_path))

            # Generate embeddings if manager available
            if self.embedding_manager:
                for unit in units:
                    try:
                        # Create searchable text from unit
                        search_text = self._create_search_text(unit)
                        # Generate embedding
                        unit.embedding = self.embedding_manager.generate(search_text)
                    except Exception as e:
                        logger.warning(f"Failed to generate embedding for {unit.id}: {e}")

            # Store units
            for unit in units:
                self.units.append(unit)
                self.unit_index[unit.id] = unit

            self.stats["files_indexed"] += 1
            self.stats["units_extracted"] += len(units)

            logger.debug(f"Indexed {file_path}: {len(units)} units")

            return units

        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Error indexing {file_path}: {e}")
            return []

    def get_units(self) -> List[CodeUnit]:
        """Get all indexed units."""
        return self.units

    def get_unit(self, unit_id: str) -> Optional[CodeUnit]:
        """Get unit by ID."""
        return self.unit_index.get(unit_id)

    def find_by_name(self, name: str) -> List[CodeUnit]:
        """Find units by name (partial match)."""
        return [u for u in self.units if name.lower() in u.name.lower()]

    def find_by_type(self, unit_type: str) -> List[CodeUnit]:
        """Find units by type (function, class, import, etc.)."""
        return [u for u in self.units if u.type == unit_type]

    def find_by_file(self, file_path: str) -> List[CodeUnit]:
        """Find all units in a specific file."""
        file_path = str(Path(file_path).resolve())
        return [u for u in self.units if u.file_path == file_path]

    def get_statistics(self) -> Dict:
        """Get indexing statistics."""
        return {
            **self.stats,
            "total_units": len(self.units),
            "repo_path": str(self.repo_path),
            "language": self.language,
        }

    def clear(self) -> None:
        """Clear all indexed data."""
        self.units = []
        self.unit_index = {}
        self.stats = {
            "files_scanned": 0,
            "files_indexed": 0,
            "files_skipped": 0,
            "units_extracted": 0,
            "errors": 0,
            "indexing_time": 0.0,
        }

    def _find_files(self, extensions: List[str], recursive: bool) -> List[Path]:
        """Find all files matching extensions."""
        files = []

        if recursive:
            # Use rglob for recursive search
            for ext in extensions:
                pattern = f"*{ext}"
                files.extend(self.repo_path.rglob(pattern))
        else:
            # Only top-level files
            for ext in extensions:
                pattern = f"*{ext}"
                files.extend(self.repo_path.glob(pattern))

        # Remove duplicates and sort
        files = sorted(set(files))

        # Filter out skipped files/directories
        filtered = []
        for f in files:
            if not self._should_skip(f):
                filtered.append(f)

        return filtered

    def _should_skip(self, file_path: Path) -> bool:
        """Check if file should be skipped."""
        # Check path parts for skip patterns
        parts = file_path.parts

        for part in parts:
            # Check direct match
            if part in self.skip_patterns:
                return True

            # Check wildcard patterns
            for pattern in self.skip_patterns:
                if "*" in pattern:
                    # Simple wildcard matching (e.g., *.egg-info)
                    pattern_prefix = pattern.split("*")[0]
                    pattern_suffix = pattern.split("*")[1] if len(pattern.split("*")) > 1 else ""
                    # Only match if there's actual content to match
                    if pattern_prefix and part.startswith(pattern_prefix):
                        return True
                    if pattern_suffix and part.endswith(pattern_suffix):
                        return True

        return False

    def _create_search_text(self, unit: CodeUnit) -> str:
        """Create searchable text representation of unit."""
        parts = [
            unit.name,
            unit.type,
            unit.signature,
            unit.docstring,
        ]

        # Add meaningful context from code
        code_lines = unit.code.split("\n")
        # Take first few meaningful lines
        meaningful = [
            line.strip()
            for line in code_lines[:3]
            if line.strip() and not line.strip().startswith("#")
        ]

        parts.extend(meaningful)

        return " ".join(filter(None, parts))


class IndexStatistics:
    """Statistics about an index."""

    def __init__(self, indexer: CodebaseIndexer):
        """Initialize from indexer."""
        self.stats = indexer.get_statistics()

    @property
    def total_files(self) -> int:
        """Total files scanned."""
        return self.stats.get("files_scanned", 0)

    @property
    def indexed_files(self) -> int:
        """Files successfully indexed."""
        return self.stats.get("files_indexed", 0)

    @property
    def skipped_files(self) -> int:
        """Files skipped."""
        return self.stats.get("files_skipped", 0)

    @property
    def total_units(self) -> int:
        """Total semantic units extracted."""
        return self.stats.get("units_extracted", 0) or self.stats.get("total_units", 0)

    @property
    def errors(self) -> int:
        """Number of errors during indexing."""
        return self.stats.get("errors", 0)

    @property
    def indexing_time(self) -> float:
        """Time spent indexing (seconds)."""
        return self.stats.get("indexing_time", 0.0)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "total_files": self.total_files,
            "indexed_files": self.indexed_files,
            "skipped_files": self.skipped_files,
            "total_units": self.total_units,
            "errors": self.errors,
            "indexing_time": round(self.indexing_time, 2),
            "units_per_file": (
                round(self.total_units / self.indexed_files, 1)
                if self.indexed_files > 0
                else 0
            ),
        }

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"IndexStatistics("
            f"files={self.total_files}, "
            f"units={self.total_units}, "
            f"time={self.indexing_time:.2f}s)"
        )
