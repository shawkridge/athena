# Implementation Guide: Local Semantic Code Search Integration

**Version**: 1.0
**Date**: 2025-11-21
**Status**: Design Phase
**Target**: Athena Memory System

---

## Executive Summary

This document specifies the complete integration of mgrep-like semantic code search capabilities into Athena's memory system, enabling local, privacy-preserving, natural language code search without cloud dependencies.

**Objectives**:
- ✅ 100% local semantic code search (no cloud APIs)
- ✅ Natural language queries ("where is auth configured?")
- ✅ Deep integration with Athena's 8 memory layers
- ✅ File watching with automatic incremental indexing
- ✅ `.gitignore` support for intelligent file filtering
- ✅ Cross-session memory (remember past searches)
- ✅ Knowledge graph integration (entity extraction)
- ✅ Procedural learning (extract search patterns)

**Estimated Effort**: 40-60 developer hours across 4 phases

**Dependencies**: `pathspec` (21KB), `watchdog` (150KB), `tree-sitter` (existing)

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Component Specifications](#2-component-specifications)
3. [Integration Design](#3-integration-design)
4. [API Specifications](#4-api-specifications)
5. [Implementation Phases](#5-implementation-phases)
6. [Testing Strategy](#6-testing-strategy)
7. [Performance Benchmarks](#7-performance-benchmarks)
8. [Configuration Management](#8-configuration-management)
9. [Deployment Guide](#9-deployment-guide)
10. [Migration Path](#10-migration-path)

---

## 1. Architecture Overview

### 1.1 System Context

```
┌─────────────────────────────────────────────────────────────────┐
│                        Claude Code Agent                         │
│                    (Natural Language Queries)                    │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Athena Unified Memory Manager                  │
│                    (Query Routing & Caching)                     │
└────┬────────────────────────┬────────────────────────┬──────────┘
     │                        │                        │
     ▼                        ▼                        ▼
┌─────────────┐      ┌─────────────────┐     ┌──────────────────┐
│  Semantic   │      │   Code Search   │     │  Episodic/Graph  │
│   Memory    │◄────►│   Subsystem     │────►│     Layers       │
│   (Layer 2) │      │   (NEW)         │     │  (Layers 1, 5)   │
└─────────────┘      └────────┬────────┘     └──────────────────┘
                              │
                              ▼
                    ┌──────────────────────┐
                    │   PostgreSQL         │
                    │   - code_entities    │
                    │   - code_embeddings  │
                    │   - code_index       │
                    └──────────────────────┘
```

### 1.2 Code Search Subsystem Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                      Code Search Subsystem                        │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────────┐         ┌─────────────────────┐        │
│  │  CodeSearchManager  │◄───────►│ FileSystemWatcher   │        │
│  │  (Orchestrator)     │         │ (watchdog)          │        │
│  └──────────┬──────────┘         └──────────┬──────────┘        │
│             │                               │                    │
│             │ initialize                    │ on_modified        │
│             ▼                               ▼                    │
│  ┌─────────────────────┐         ┌─────────────────────┐        │
│  │  CodeIndexer        │◄───────►│ IncrementalIndexer  │        │
│  │  (Tree-sitter)      │         │ (Background Thread) │        │
│  └──────────┬──────────┘         └─────────────────────┘        │
│             │                                                    │
│             │ parse & extract                                   │
│             ▼                                                    │
│  ┌─────────────────────┐         ┌─────────────────────┐        │
│  │  CodeParser         │         │ GitIgnoreFilter     │        │
│  │  (AST extraction)   │         │ (pathspec)          │        │
│  └──────────┬──────────┘         └─────────────────────┘        │
│             │                                                    │
│             │ code units                                        │
│             ▼                                                    │
│  ┌─────────────────────┐         ┌─────────────────────┐        │
│  │  EmbeddingGenerator │◄───────►│ PostgreSQL          │        │
│  │  (llama.cpp)        │         │ (pgvector storage)  │        │
│  └─────────────────────┘         └─────────────────────┘        │
│                                                                   │
│  ┌───────────────────────────────────────────────────────┐      │
│  │              SemanticCodeSearcher                      │      │
│  │  (Query Processing, Hybrid Search, Reranking)         │      │
│  └───────────────────────────────────────────────────────┘      │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

### 1.3 Data Flow

**Indexing Flow**:
```
1. FileSystemWatcher detects .py file change
   ↓
2. GitIgnoreFilter checks if file should be skipped
   ↓ (not ignored)
3. IncrementalIndexer queues file for processing
   ↓
4. CodeParser extracts AST (functions, classes, imports)
   ↓
5. EmbeddingGenerator creates 768D vectors (local llama.cpp)
   ↓
6. PostgreSQL stores:
   - code_entities (name, type, file_path, line_number)
   - code_embeddings (entity_id, vector)
   - code_index (file_hash, last_indexed)
   ↓
7. GraphStore extracts entities/relationships
   ↓
8. EpisodicStore records indexing event
```

**Search Flow**:
```
1. Agent queries: "where is authentication configured?"
   ↓
2. QueryParser analyzes intent (factual, code-related)
   ↓
3. UnifiedMemoryManager routes to CodeSearchManager
   ↓
4. SemanticCodeSearcher:
   a. Generates query embedding (llama.cpp)
   b. PostgreSQL pgvector search (top-k semantic matches)
   c. BM25 full-text search (keyword matches)
   d. Hybrid scoring (semantic 0.7 + keyword 0.3)
   e. Reranking (LLM-based relevance)
   ↓
5. Results enriched with:
   - Past search memories (EpisodicStore)
   - Entity relationships (GraphStore)
   - Usage patterns (ProceduralStore)
   ↓
6. Cache result for future queries
   ↓
7. Return formatted results to agent
```

---

## 2. Component Specifications

### 2.1 CodeSearchManager

**File**: `src/athena/code_search/manager.py` (NEW)

**Responsibilities**:
- Orchestrate all code search operations
- Manage indexer lifecycle
- Coordinate with Athena memory layers
- Handle caching and query routing

**Interface**:
```python
class CodeSearchManager:
    """Central manager for semantic code search operations."""

    def __init__(
        self,
        repo_path: str,
        project_id: int,
        db: PostgresDatabase,
        embedder: EmbeddingModel,
        episodic_store: EpisodicStore,
        graph_store: GraphStore,
        semantic_store: SemanticStore,
        enable_watching: bool = True,
        enable_memory_integration: bool = True,
    ):
        """Initialize code search manager."""
        pass

    async def initialize(self) -> IndexStatistics:
        """Build initial index of codebase."""
        pass

    async def search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[CodeSearchResult]:
        """Semantic search over indexed code."""
        pass

    async def get_entity(self, entity_id: int) -> Optional[CodeEntity]:
        """Retrieve code entity by ID."""
        pass

    async def reindex_file(self, file_path: str) -> bool:
        """Re-index a specific file."""
        pass

    async def get_statistics(self) -> Dict[str, Any]:
        """Get indexing and search statistics."""
        pass

    def start_watching(self) -> None:
        """Start file system watcher."""
        pass

    def stop_watching(self) -> None:
        """Stop file system watcher."""
        pass
```

### 2.2 GitIgnoreFilter

**File**: `src/athena/code_search/gitignore_filter.py` (NEW)

**Responsibilities**:
- Parse `.gitignore` and `.athenaignore` files
- Filter files during indexing
- Support nested `.gitignore` files

**Interface**:
```python
class GitIgnoreFilter:
    """Filter files based on .gitignore patterns."""

    def __init__(self, repo_root: Path):
        """Load all .gitignore files in repository."""
        self.repo_root = repo_root
        self.specs: Dict[Path, pathspec.PathSpec] = {}
        self._load_all_gitignores()

    def _load_all_gitignores(self) -> None:
        """Recursively load .gitignore files."""
        for gitignore_path in self.repo_root.rglob(".gitignore"):
            with open(gitignore_path) as f:
                patterns = f.read().splitlines()
            self.specs[gitignore_path.parent] = pathspec.PathSpec.from_lines(
                "gitwildmatch", patterns
            )

    def should_index(self, file_path: Path) -> bool:
        """Check if file should be indexed."""
        # Check each .gitignore from root to file's directory
        rel_path = file_path.relative_to(self.repo_root)

        for directory, spec in self.specs.items():
            if file_path.is_relative_to(directory):
                if spec.match_file(rel_path):
                    return False

        return True

    def add_custom_patterns(self, patterns: List[str]) -> None:
        """Add custom ignore patterns (e.g., from .athenaignore)."""
        pass
```

**Dependencies**:
```bash
pip install pathspec==0.11.2
```

### 2.3 FileSystemWatcher

**File**: `src/athena/code_search/watcher.py` (NEW)

**Responsibilities**:
- Monitor file system for changes
- Trigger incremental re-indexing
- Handle create, modify, delete events
- Debounce rapid changes

**Interface**:
```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class CodeChangeHandler(FileSystemEventHandler):
    """Handle file system events for code indexing."""

    def __init__(
        self,
        indexer: CodeIndexer,
        gitignore_filter: GitIgnoreFilter,
        debounce_seconds: float = 2.0,
    ):
        self.indexer = indexer
        self.filter = gitignore_filter
        self.debounce_seconds = debounce_seconds
        self._pending_changes: Dict[str, float] = {}
        self._lock = threading.Lock()

    def on_created(self, event):
        """Handle file creation."""
        if not event.is_directory:
            self._schedule_index(event.src_path)

    def on_modified(self, event):
        """Handle file modification."""
        if not event.is_directory:
            self._schedule_index(event.src_path)

    def on_deleted(self, event):
        """Handle file deletion."""
        if not event.is_directory:
            self._schedule_removal(event.src_path)

    def _schedule_index(self, file_path: str):
        """Schedule file for indexing with debouncing."""
        with self._lock:
            self._pending_changes[file_path] = time.time()
            # Start timer to process after debounce period
            threading.Timer(
                self.debounce_seconds,
                self._process_pending,
                args=[file_path]
            ).start()

    def _process_pending(self, file_path: str):
        """Process pending change after debounce."""
        with self._lock:
            if file_path in self._pending_changes:
                # Check if file passes filter
                if self.filter.should_index(Path(file_path)):
                    self.indexer.index_file(file_path)
                del self._pending_changes[file_path]

class FileSystemWatcher:
    """Watch file system for code changes."""

    def __init__(
        self,
        repo_path: str,
        indexer: CodeIndexer,
        gitignore_filter: GitIgnoreFilter,
    ):
        self.repo_path = Path(repo_path)
        self.observer = Observer()
        self.handler = CodeChangeHandler(indexer, gitignore_filter)

    def start(self):
        """Start watching."""
        self.observer.schedule(
            self.handler,
            str(self.repo_path),
            recursive=True
        )
        self.observer.start()
        logger.info(f"Watching {self.repo_path} for changes")

    def stop(self):
        """Stop watching."""
        self.observer.stop()
        self.observer.join()
```

**Dependencies**:
```bash
pip install watchdog==3.0.0
```

### 2.4 IncrementalIndexer

**File**: `src/athena/code_search/incremental_indexer.py` (NEW)

**Responsibilities**:
- Track indexed files (hash-based change detection)
- Skip unchanged files
- Background processing queue
- Batch embedding generation

**Interface**:
```python
class IncrementalIndexer:
    """Incremental indexing with change detection."""

    def __init__(
        self,
        indexer: CodeIndexer,
        db: PostgresDatabase,
        batch_size: int = 50,
    ):
        self.indexer = indexer
        self.db = db
        self.batch_size = batch_size
        self._index_queue: asyncio.Queue = asyncio.Queue()
        self._worker_task: Optional[asyncio.Task] = None

    async def start_worker(self):
        """Start background indexing worker."""
        self._worker_task = asyncio.create_task(self._index_worker())

    async def stop_worker(self):
        """Stop background worker."""
        if self._worker_task:
            self._worker_task.cancel()

    async def queue_file(self, file_path: str):
        """Add file to indexing queue."""
        await self._index_queue.put(file_path)

    async def _index_worker(self):
        """Background worker for processing queue."""
        batch = []

        while True:
            try:
                # Collect batch
                while len(batch) < self.batch_size:
                    try:
                        file_path = await asyncio.wait_for(
                            self._index_queue.get(),
                            timeout=1.0
                        )
                        batch.append(file_path)
                    except asyncio.TimeoutError:
                        break

                if batch:
                    await self._index_batch(batch)
                    batch = []

            except asyncio.CancelledError:
                break

    async def _index_batch(self, file_paths: List[str]):
        """Index a batch of files."""
        for file_path in file_paths:
            # Check if file changed since last index
            if not await self._file_changed(file_path):
                logger.debug(f"Skipping unchanged file: {file_path}")
                continue

            # Index file
            try:
                units = self.indexer.index_file(file_path)

                # Store file hash
                await self._store_file_hash(file_path)

                logger.info(f"Indexed {file_path}: {len(units)} units")

            except Exception as e:
                logger.error(f"Failed to index {file_path}: {e}")

    async def _file_changed(self, file_path: str) -> bool:
        """Check if file changed since last index."""
        current_hash = self._compute_file_hash(file_path)

        # Query database for last hash
        result = await self.db.execute(
            "SELECT file_hash FROM code_index WHERE file_path = %s",
            (file_path,),
            fetch_one=True
        )

        if not result:
            return True  # New file

        return result["file_hash"] != current_hash

    def _compute_file_hash(self, file_path: str) -> str:
        """Compute SHA-256 hash of file contents."""
        import hashlib

        with open(file_path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()

    async def _store_file_hash(self, file_path: str):
        """Store file hash in database."""
        file_hash = self._compute_file_hash(file_path)

        await self.db.execute(
            """
            INSERT INTO code_index (file_path, file_hash, last_indexed)
            VALUES (%s, %s, NOW())
            ON CONFLICT (file_path)
            DO UPDATE SET file_hash = %s, last_indexed = NOW()
            """,
            (file_path, file_hash, file_hash)
        )
```

### 2.5 Enhanced CodeIndexer

**File**: `src/athena/code_search/indexer.py` (MODIFY EXISTING)

**Changes**:
- Add `.gitignore` filtering
- Add incremental indexing support
- Add statistics tracking
- Improve error handling

**Additions**:
```python
class CodebaseIndexer:
    """Index a codebase for semantic code search."""

    def __init__(
        self,
        repo_path: str,
        language: str = "python",
        embedding_manager=None,
        skip_patterns: Optional[Set[str]] = None,
        gitignore_filter: Optional[GitIgnoreFilter] = None,  # NEW
    ):
        # ... existing code ...
        self.gitignore_filter = gitignore_filter  # NEW

    def _should_skip(self, file_path: Path) -> bool:
        """Check if file should be skipped."""
        # Existing skip patterns
        if super()._should_skip_existing(file_path):
            return True

        # NEW: Check gitignore filter
        if self.gitignore_filter:
            if not self.gitignore_filter.should_index(file_path):
                logger.debug(f"Skipping (gitignore): {file_path}")
                return True

        return False

    def remove_file(self, file_path: str) -> bool:  # NEW
        """Remove file from index."""
        file_path = str(Path(file_path).resolve())

        # Remove from units list
        self.units = [u for u in self.units if u.file_path != file_path]

        # Remove from unit index
        removed_ids = [uid for uid, unit in self.unit_index.items()
                      if unit.file_path == file_path]
        for uid in removed_ids:
            del self.unit_index[uid]

        logger.info(f"Removed {len(removed_ids)} units from {file_path}")
        return len(removed_ids) > 0
```

### 2.6 Database Schema

**File**: `src/athena/code_search/schema.py` (NEW)

**Tables**:
```python
CODE_SEARCH_SCHEMA = """
-- Code entities table (functions, classes, etc.)
CREATE TABLE IF NOT EXISTS code_entities (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL,
    file_path TEXT NOT NULL,
    entity_name TEXT NOT NULL,
    entity_type TEXT NOT NULL,  -- function, class, method, variable, import
    line_number INTEGER NOT NULL,
    end_line_number INTEGER,
    signature TEXT,
    docstring TEXT,
    code_snippet TEXT,
    complexity_score FLOAT DEFAULT 0.0,
    embedding vector(768),  -- pgvector embedding
    created_at TIMESTAMP DEFAULT NOW(),
    last_modified TIMESTAMP DEFAULT NOW(),
    CONSTRAINT code_entities_unique UNIQUE (project_id, file_path, entity_name, line_number)
);

-- Full-text search index for code
CREATE INDEX IF NOT EXISTS idx_code_entities_fts
ON code_entities USING GIN (to_tsvector('english',
    entity_name || ' ' || COALESCE(signature, '') || ' ' || COALESCE(docstring, '')));

-- Vector similarity search index
CREATE INDEX IF NOT EXISTS idx_code_entities_embedding
ON code_entities USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- File path index for filtering
CREATE INDEX IF NOT EXISTS idx_code_entities_file
ON code_entities (project_id, file_path);

-- Entity type index
CREATE INDEX IF NOT EXISTS idx_code_entities_type
ON code_entities (entity_type);

-- Code index tracking (for incremental indexing)
CREATE TABLE IF NOT EXISTS code_index (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL,
    file_path TEXT NOT NULL UNIQUE,
    file_hash TEXT NOT NULL,
    last_indexed TIMESTAMP DEFAULT NOW(),
    entity_count INTEGER DEFAULT 0,
    index_status TEXT DEFAULT 'success',  -- success, failed, pending
    error_message TEXT
);

-- Index for file lookup
CREATE INDEX IF NOT EXISTS idx_code_index_file
ON code_index (project_id, file_path);

-- Code dependencies (for graph integration)
CREATE TABLE IF NOT EXISTS code_dependencies (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL,
    from_entity_id INTEGER REFERENCES code_entities(id) ON DELETE CASCADE,
    to_entity_id INTEGER REFERENCES code_entities(id) ON DELETE CASCADE,
    dependency_type TEXT NOT NULL,  -- calls, imports, inherits, uses
    weight FLOAT DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT code_dependencies_unique UNIQUE (from_entity_id, to_entity_id, dependency_type)
);

-- Index for dependency lookups
CREATE INDEX IF NOT EXISTS idx_code_dependencies_from
ON code_dependencies (from_entity_id);
CREATE INDEX IF NOT EXISTS idx_code_dependencies_to
ON code_dependencies (to_entity_id);

-- Code search statistics (for optimization)
CREATE TABLE IF NOT EXISTS code_search_stats (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL,
    query TEXT NOT NULL,
    query_hash TEXT NOT NULL,
    result_count INTEGER DEFAULT 0,
    execution_time_ms FLOAT DEFAULT 0.0,
    cache_hit BOOLEAN DEFAULT FALSE,
    searched_at TIMESTAMP DEFAULT NOW()
);

-- Index for analytics
CREATE INDEX IF NOT EXISTS idx_code_search_stats_project
ON code_search_stats (project_id, searched_at DESC);
"""
```

---

## 3. Integration Design

### 3.1 UnifiedMemoryManager Integration

**File**: `src/athena/manager.py` (MODIFY EXISTING)

**Changes**:
```python
class UnifiedMemoryManager:
    """Unified interface to all memory layers with intelligent routing."""

    def __init__(
        self,
        # ... existing parameters ...
        code_search_manager: Optional[CodeSearchManager] = None,  # NEW
    ):
        # ... existing initialization ...
        self.code_search = code_search_manager  # NEW

        # Update query routing
        self._update_query_routing()

    def _update_query_routing(self):
        """Update query router to include code search."""
        # Add code search patterns to router
        self._code_search_patterns = {
            "code_location": ["where is", "find code", "locate", "which file"],
            "code_definition": ["what is", "show me", "definition of"],
            "code_usage": ["how is", "usage of", "examples of"],
            "code_dependency": ["what depends on", "what uses", "dependencies"],
        }

    async def retrieve(
        self,
        query: str,
        project_id: int,
        k: int = 10,
        query_type: Optional[str] = None,
        # ... existing parameters ...
    ) -> List[MemorySearchResult]:
        """Smart retrieval with code search integration."""

        # Detect if query is code-related
        is_code_query = self._is_code_search_query(query)

        if is_code_query and self.code_search:
            # Route to code search
            code_results = await self.code_search.search(
                query=query,
                top_k=k,
            )

            # Convert to MemorySearchResult format
            memory_results = self._convert_code_to_memory_results(code_results)

            # Enrich with episodic/procedural memories
            if self.episodic:
                past_searches = await self.episodic.recall(
                    query=f"code search: {query}",
                    project_id=project_id,
                    limit=3,
                )
                # Merge results...

            return memory_results

        # ... existing retrieval logic ...

    def _is_code_search_query(self, query: str) -> bool:
        """Detect if query is asking about code."""
        query_lower = query.lower()

        # Check for code-related keywords
        for category, patterns in self._code_search_patterns.items():
            if any(pattern in query_lower for pattern in patterns):
                return True

        # Check for file extensions
        code_extensions = [".py", ".js", ".ts", ".java", ".go"]
        if any(ext in query_lower for ext in code_extensions):
            return True

        return False

    def _convert_code_to_memory_results(
        self,
        code_results: List[CodeSearchResult]
    ) -> List[MemorySearchResult]:
        """Convert code search results to memory results."""
        memory_results = []

        for code_result in code_results:
            # Create Memory object from code entity
            memory = Memory(
                content=self._format_code_result(code_result),
                memory_type=MemoryType.SEMANTIC,
                tags=["code", code_result.entity_type, code_result.file_path],
                metadata={
                    "entity_id": code_result.entity_id,
                    "file_path": code_result.file_path,
                    "line_number": code_result.line_number,
                    "entity_type": code_result.entity_type,
                },
            )

            memory_results.append(
                MemorySearchResult(
                    memory=memory,
                    similarity=code_result.semantic_similarity,
                    rank=len(memory_results) + 1,
                )
            )

        return memory_results

    def _format_code_result(self, result: CodeSearchResult) -> str:
        """Format code result as memory content."""
        return (
            f"{result.entity_name} ({result.entity_type}) "
            f"in {result.file_path}:{result.line_number}"
        )
```

### 3.2 Operations Layer Integration

**File**: `src/athena/code_search/operations.py` (NEW)

**Purpose**: Expose code search as operations for agent discovery.

```python
"""Code search operations for Athena memory system."""

import asyncio
from typing import List, Dict, Optional, Any
from .manager import CodeSearchManager
from .models import CodeSearchResult

# Global manager instance (initialized by system)
_code_search_manager: Optional[CodeSearchManager] = None

def initialize(
    repo_path: str,
    project_id: int,
    **kwargs
) -> bool:
    """
    Initialize code search for a repository.

    Args:
        repo_path: Path to code repository
        project_id: Athena project ID
        **kwargs: Additional configuration

    Returns:
        True if initialization successful
    """
    global _code_search_manager

    from athena.core.database_factory import get_database
    from athena.core.embeddings import EmbeddingModel

    db = get_database("postgres")
    embedder = EmbeddingModel()

    _code_search_manager = CodeSearchManager(
        repo_path=repo_path,
        project_id=project_id,
        db=db,
        embedder=embedder,
        **kwargs
    )

    # Build initial index
    asyncio.run(_code_search_manager.initialize())

    return True

async def search(
    query: str,
    top_k: int = 10,
    filters: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Search code with natural language query.

    Args:
        query: Natural language search query
        top_k: Number of results to return
        filters: Optional filters (file_path, entity_type, etc.)

    Returns:
        List of code search results

    Examples:
        >>> results = await search("where is authentication configured")
        >>> results[0]
        {
            "entity_name": "setup_auth",
            "entity_type": "function",
            "file_path": "src/auth/config.py",
            "line_number": 45,
            "similarity": 0.94,
            "snippet": "def setup_auth(app)..."
        }
    """
    if not _code_search_manager:
        raise RuntimeError("Code search not initialized. Call initialize() first.")

    results = await _code_search_manager.search(
        query=query,
        top_k=top_k,
        filters=filters,
    )

    # Convert to dict format
    return [result.to_dict() for result in results]

async def get_entity(entity_id: int) -> Optional[Dict[str, Any]]:
    """
    Get code entity by ID.

    Args:
        entity_id: Entity ID from search results

    Returns:
        Code entity details or None if not found
    """
    if not _code_search_manager:
        raise RuntimeError("Code search not initialized")

    entity = await _code_search_manager.get_entity(entity_id)
    return entity.to_dict() if entity else None

async def reindex_file(file_path: str) -> bool:
    """
    Re-index a specific file.

    Args:
        file_path: Path to file

    Returns:
        True if re-indexing successful
    """
    if not _code_search_manager:
        raise RuntimeError("Code search not initialized")

    return await _code_search_manager.reindex_file(file_path)

async def get_statistics() -> Dict[str, Any]:
    """
    Get code search statistics.

    Returns:
        Statistics dict with:
        - total_files: Number of indexed files
        - total_entities: Number of code entities
        - last_indexed: Timestamp of last indexing
        - search_count: Total searches performed
    """
    if not _code_search_manager:
        return {"error": "Code search not initialized"}

    return await _code_search_manager.get_statistics()

async def start_watching() -> bool:
    """
    Start file system watcher for automatic indexing.

    Returns:
        True if watcher started successfully
    """
    if not _code_search_manager:
        raise RuntimeError("Code search not initialized")

    _code_search_manager.start_watching()
    return True

async def stop_watching() -> bool:
    """
    Stop file system watcher.

    Returns:
        True if watcher stopped successfully
    """
    if not _code_search_manager:
        raise RuntimeError("Code search not initialized")

    _code_search_manager.stop_watching()
    return True
```

### 3.3 TypeScript Stub for Agent Discovery

**File**: `servers/athena/code_search.ts` (NEW)

```typescript
/**
 * Semantic code search operations.
 *
 * @implementation src/athena/code_search/operations.py
 */

/**
 * Initialize code search for a repository.
 */
export async function initialize(
  repo_path: string,
  project_id: number,
  enable_watching?: boolean
): Promise<boolean>;

/**
 * Search code with natural language query.
 *
 * @example
 * const results = await search("where is authentication configured");
 * // Returns: [
 * //   {
 * //     entity_name: "setup_auth",
 * //     file_path: "src/auth/config.py",
 * //     line_number: 45,
 * //     similarity: 0.94
 * //   }
 * // ]
 */
export async function search(
  query: string,
  top_k?: number,
  filters?: Record<string, any>
): Promise<Array<{
  entity_id: number;
  entity_name: string;
  entity_type: string;
  file_path: string;
  line_number: number;
  similarity: number;
  snippet?: string;
  docstring?: string;
}>>;

/**
 * Get code entity by ID.
 */
export async function get_entity(
  entity_id: number
): Promise<{
  entity_name: string;
  entity_type: string;
  file_path: string;
  line_number: number;
  signature?: string;
  docstring?: string;
  code_snippet?: string;
  dependencies?: string[];
} | null>;

/**
 * Re-index a specific file.
 */
export async function reindex_file(file_path: string): Promise<boolean>;

/**
 * Get code search statistics.
 */
export async function get_statistics(): Promise<{
  total_files: number;
  total_entities: number;
  last_indexed: string;
  search_count: number;
  avg_search_time_ms: number;
}>;

/**
 * Start file system watcher for automatic indexing.
 */
export async function start_watching(): Promise<boolean>;

/**
 * Stop file system watcher.
 */
export async function stop_watching(): Promise<boolean>;
```

---

## 4. API Specifications

### 4.1 REST API Endpoints

**File**: `dashboard/backend/routers/code_search.py` (NEW)

```python
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

router = APIRouter(prefix="/api/code-search", tags=["code-search"])

class SearchRequest(BaseModel):
    query: str
    top_k: int = 10
    filters: Optional[Dict[str, Any]] = None

class SearchResponse(BaseModel):
    query: str
    results: List[Dict[str, Any]]
    execution_time_ms: float
    total_results: int

class InitializeRequest(BaseModel):
    repo_path: str
    project_id: int
    enable_watching: bool = True

@router.post("/initialize")
async def initialize_code_search(request: InitializeRequest):
    """Initialize code search for a repository."""
    from athena.code_search import operations

    success = operations.initialize(
        repo_path=request.repo_path,
        project_id=request.project_id,
        enable_watching=request.enable_watching,
    )

    if not success:
        raise HTTPException(status_code=500, detail="Initialization failed")

    stats = await operations.get_statistics()
    return {"success": True, "statistics": stats}

@router.post("/search", response_model=SearchResponse)
async def search_code(request: SearchRequest):
    """Search code with natural language query."""
    import time
    from athena.code_search import operations

    start = time.time()

    try:
        results = await operations.search(
            query=request.query,
            top_k=request.top_k,
            filters=request.filters,
        )

        execution_time = (time.time() - start) * 1000

        return SearchResponse(
            query=request.query,
            results=results,
            execution_time_ms=execution_time,
            total_results=len(results),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/entity/{entity_id}")
async def get_entity(entity_id: int):
    """Get code entity details."""
    from athena.code_search import operations

    entity = await operations.get_entity(entity_id)

    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    return entity

@router.post("/reindex/{file_path:path}")
async def reindex_file(file_path: str):
    """Re-index a specific file."""
    from athena.code_search import operations

    success = await operations.reindex_file(file_path)

    if not success:
        raise HTTPException(status_code=500, detail="Re-indexing failed")

    return {"success": True, "file_path": file_path}

@router.get("/statistics")
async def get_statistics():
    """Get code search statistics."""
    from athena.code_search import operations

    stats = await operations.get_statistics()
    return stats

@router.post("/watching/start")
async def start_watching():
    """Start file system watcher."""
    from athena.code_search import operations

    success = await operations.start_watching()
    return {"success": success}

@router.post("/watching/stop")
async def stop_watching():
    """Stop file system watcher."""
    from athena.code_search import operations

    success = await operations.stop_watching()
    return {"success": success}
```

### 4.2 CLI Interface

**File**: `src/athena/cli/code_search.py` (NEW)

```python
"""CLI for code search operations."""

import typer
import asyncio
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.progress import Progress

app = typer.Typer(help="Semantic code search operations")
console = Console()

@app.command()
def init(
    path: str = typer.Option(".", help="Repository path"),
    project_id: int = typer.Option(1, help="Project ID"),
    watch: bool = typer.Option(False, help="Enable file watching"),
):
    """Initialize code search index."""
    from athena.code_search import operations

    console.print(f"[bold blue]Initializing code search for {path}...[/bold blue]")

    with Progress() as progress:
        task = progress.add_task("Indexing...", total=None)

        success = operations.initialize(
            repo_path=path,
            project_id=project_id,
            enable_watching=watch,
        )

        progress.update(task, completed=True)

    if success:
        stats = asyncio.run(operations.get_statistics())
        console.print(f"[bold green]✓[/bold green] Indexed {stats['total_files']} files, "
                     f"{stats['total_entities']} entities")

        if watch:
            console.print("[bold blue]Watching for changes...[/bold blue] (Ctrl+C to stop)")
            try:
                while True:
                    import time
                    time.sleep(1)
            except KeyboardInterrupt:
                asyncio.run(operations.stop_watching())
                console.print("\n[bold]Stopped watching[/bold]")
    else:
        console.print("[bold red]✗ Initialization failed[/bold red]")

@app.command()
def search(
    query: str = typer.Argument(..., help="Natural language query"),
    limit: int = typer.Option(10, help="Number of results"),
    show_snippet: bool = typer.Option(False, "--snippet", help="Show code snippets"),
):
    """Search code with natural language."""
    from athena.code_search import operations

    console.print(f"[bold]Searching:[/bold] {query}\n")

    results = asyncio.run(operations.search(query=query, top_k=limit))

    if not results:
        console.print("[yellow]No results found[/yellow]")
        return

    # Create table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("#", width=3)
    table.add_column("Entity", width=30)
    table.add_column("Type", width=12)
    table.add_column("Location", width=50)
    table.add_column("Score", width=8)

    for i, result in enumerate(results, 1):
        table.add_row(
            str(i),
            result["entity_name"],
            result["entity_type"],
            f"{result['file_path']}:{result['line_number']}",
            f"{result['similarity']:.2%}",
        )

    console.print(table)

    if show_snippet:
        console.print("\n[bold]Code Snippets:[/bold]\n")
        for i, result in enumerate(results[:3], 1):
            if "snippet" in result:
                console.print(f"[bold cyan]{i}. {result['entity_name']}[/bold cyan]")
                console.print(result["snippet"])
                console.print()

@app.command()
def stats():
    """Show code search statistics."""
    from athena.code_search import operations

    stats = asyncio.run(operations.get_statistics())

    console.print("[bold]Code Search Statistics[/bold]\n")
    console.print(f"Total Files:    {stats.get('total_files', 0):,}")
    console.print(f"Total Entities: {stats.get('total_entities', 0):,}")
    console.print(f"Last Indexed:   {stats.get('last_indexed', 'Never')}")
    console.print(f"Search Count:   {stats.get('search_count', 0):,}")
    console.print(f"Avg Search:     {stats.get('avg_search_time_ms', 0):.2f}ms")

@app.command()
def watch(
    path: str = typer.Option(".", help="Repository path"),
):
    """Start watching for file changes."""
    from athena.code_search import operations

    asyncio.run(operations.start_watching())
    console.print(f"[bold blue]Watching {path} for changes...[/bold blue] (Ctrl+C to stop)")

    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        asyncio.run(operations.stop_watching())
        console.print("\n[bold]Stopped watching[/bold]")

if __name__ == "__main__":
    app()
```

**Usage**:
```bash
# Initialize code search
athena code-search init --path /home/user/my-project --watch

# Search for code
athena code-search search "where is authentication configured" --limit 5

# Show statistics
athena code-search stats

# Start watching (if not already started)
athena code-search watch --path /home/user/my-project
```

---

## 5. Implementation Phases

### Phase 1: Core Infrastructure (16-20 hours)

**Goal**: Basic local code search without cloud dependencies.

**Tasks**:
1. **Database Schema** (2 hours)
   - Create `code_entities`, `code_index`, `code_dependencies` tables
   - Add indexes for performance
   - Write migration script

2. **GitIgnoreFilter** (3 hours)
   - Implement `.gitignore` parsing with `pathspec`
   - Support nested `.gitignore` files
   - Add `.athenaignore` support
   - Write unit tests

3. **FileSystemWatcher** (4 hours)
   - Implement `watchdog` integration
   - Add debouncing logic
   - Handle create/modify/delete events
   - Write unit tests

4. **IncrementalIndexer** (4 hours)
   - Implement hash-based change detection
   - Add background processing queue
   - Implement batch processing
   - Write unit tests

5. **Enhanced CodeIndexer** (3 hours)
   - Integrate GitIgnoreFilter
   - Add `remove_file()` method
   - Improve error handling
   - Update existing tests

6. **CodeSearchManager** (4 hours)
   - Implement orchestration logic
   - Coordinate components
   - Add initialization routine
   - Write integration tests

**Deliverables**:
- ✅ Code indexing with `.gitignore` support
- ✅ File watching with auto-reindexing
- ✅ Incremental indexing (skip unchanged files)
- ✅ PostgreSQL storage with pgvector
- ✅ 80% test coverage

**Testing Checklist**:
- [ ] Index Python repository (100+ files)
- [ ] Verify `.gitignore` filtering
- [ ] File modification triggers reindex
- [ ] File deletion removes entities
- [ ] Unchanged files skipped
- [ ] PostgreSQL schema created correctly

### Phase 2: Search & Integration (12-16 hours)

**Goal**: Natural language search integrated with Athena layers.

**Tasks**:
1. **Operations Layer** (4 hours)
   - Create `operations.py` with async functions
   - Implement search, get_entity, statistics
   - Add TypeScript stubs for agent discovery
   - Write unit tests

2. **UnifiedMemoryManager Integration** (4 hours)
   - Add code search routing
   - Implement query type detection
   - Convert code results to MemorySearchResult
   - Enrich results with episodic/procedural memories

3. **Hybrid Search Implementation** (4 hours)
   - Combine semantic + keyword search
   - Add reranking logic
   - Implement result merging
   - Write performance tests

**Deliverables**:
- ✅ Natural language code search
- ✅ Integration with UnifiedMemoryManager
- ✅ Hybrid scoring (semantic + keyword)
- ✅ Agent-accessible operations
- ✅ 90% test coverage

**Testing Checklist**:
- [ ] Search "where is auth" returns relevant results
- [ ] Query routing works (code vs memory)
- [ ] Results include episodic context
- [ ] Hybrid scoring improves relevance
- [ ] Agents can discover operations

### Phase 3: Advanced Features (8-12 hours)

**Goal**: Knowledge graph, procedural learning, and optimization.

**Tasks**:
1. **Knowledge Graph Integration** (4 hours)
   - Extract entities from code (classes, functions)
   - Create relationships (calls, imports, inherits)
   - Store in GraphStore
   - Query entity relationships

2. **Procedural Learning** (3 hours)
   - Track search patterns
   - Extract common workflows
   - Store reusable procedures
   - Recommend procedures

3. **Performance Optimization** (3 hours)
   - Add caching layer
   - Optimize database queries
   - Batch embedding generation
   - Profile and benchmark

**Deliverables**:
- ✅ Code entities in knowledge graph
- ✅ Dependency tracking
- ✅ Procedure extraction from search patterns
- ✅ <100ms average search time
- ✅ 95% test coverage

**Testing Checklist**:
- [ ] Entities added to graph
- [ ] Relationships tracked
- [ ] Procedures extracted
- [ ] Cache improves performance
- [ ] Search <100ms on 1000+ entities

### Phase 4: CLI & Dashboard (4-6 hours)

**Goal**: User-friendly interfaces for code search.

**Tasks**:
1. **CLI Commands** (2 hours)
   - Implement `athena code-search` commands
   - Add rich output formatting
   - Write help documentation

2. **REST API Endpoints** (2 hours)
   - Add `/api/code-search/` routes
   - Implement request/response models
   - Add error handling

3. **Dashboard UI** (2 hours)
   - Create code search tab
   - Add search interface
   - Display results with syntax highlighting
   - Show statistics

**Deliverables**:
- ✅ CLI tool for code search
- ✅ REST API endpoints
- ✅ Dashboard UI
- ✅ User documentation

**Testing Checklist**:
- [ ] CLI commands work
- [ ] API endpoints accessible
- [ ] Dashboard displays results
- [ ] Documentation complete

---

## 6. Testing Strategy

### 6.1 Unit Tests

**Coverage Target**: 90%+

**Key Test Files**:
- `tests/unit/test_code_search_manager.py`
- `tests/unit/test_gitignore_filter.py`
- `tests/unit/test_filesystem_watcher.py`
- `tests/unit/test_incremental_indexer.py`
- `tests/unit/test_code_search_operations.py`

**Example Test**:
```python
# tests/unit/test_gitignore_filter.py

import pytest
from pathlib import Path
from athena.code_search.gitignore_filter import GitIgnoreFilter

def test_gitignore_filter_basic(tmp_path):
    """Test basic .gitignore filtering."""
    # Create .gitignore
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text("*.pyc\n__pycache__/\n.env\n")

    # Create test files
    (tmp_path / "main.py").touch()
    (tmp_path / "test.pyc").touch()
    (tmp_path / ".env").touch()

    # Initialize filter
    filter = GitIgnoreFilter(tmp_path)

    # Assertions
    assert filter.should_index(tmp_path / "main.py") is True
    assert filter.should_index(tmp_path / "test.pyc") is False
    assert filter.should_index(tmp_path / ".env") is False

def test_gitignore_filter_nested(tmp_path):
    """Test nested .gitignore files."""
    # Root .gitignore
    (tmp_path / ".gitignore").write_text("*.log\n")

    # Subdirectory with own .gitignore
    subdir = tmp_path / "src"
    subdir.mkdir()
    (subdir / ".gitignore").write_text("*.tmp\n")

    # Test files
    (tmp_path / "test.log").touch()
    (subdir / "test.tmp").touch()
    (subdir / "main.py").touch()

    filter = GitIgnoreFilter(tmp_path)

    assert filter.should_index(tmp_path / "test.log") is False
    assert filter.should_index(subdir / "test.tmp") is False
    assert filter.should_index(subdir / "main.py") is True

def test_gitignore_filter_wildcards(tmp_path):
    """Test wildcard patterns."""
    (tmp_path / ".gitignore").write_text("*.pyc\ntest_*.py\n__pycache__/\n")

    filter = GitIgnoreFilter(tmp_path)

    assert filter.should_index(tmp_path / "main.py") is True
    assert filter.should_index(tmp_path / "test_utils.py") is False
    assert filter.should_index(tmp_path / "utils.pyc") is False
```

### 6.2 Integration Tests

**Test Scenarios**:
1. Full indexing workflow (scan → parse → embed → store)
2. File watching workflow (modify → detect → reindex)
3. Search workflow (query → embed → search → rank)
4. Cross-layer integration (code → episodic → graph)

**Example Test**:
```python
# tests/integration/test_code_search_workflow.py

import pytest
import asyncio
from pathlib import Path
from athena.code_search.manager import CodeSearchManager

@pytest.mark.asyncio
async def test_full_indexing_workflow(tmp_path, test_db, test_embedder):
    """Test complete indexing workflow."""
    # Create test repository
    (tmp_path / "main.py").write_text("""
def hello_world():
    '''Print hello world.'''
    print("Hello, World!")

class Greeter:
    '''A simple greeter class.'''
    def greet(self, name):
        return f"Hello, {name}!"
""")

    # Initialize manager
    manager = CodeSearchManager(
        repo_path=str(tmp_path),
        project_id=1,
        db=test_db,
        embedder=test_embedder,
        enable_watching=False,
    )

    # Index repository
    stats = await manager.initialize()

    # Verify statistics
    assert stats.indexed_files == 1
    assert stats.total_units >= 3  # hello_world, Greeter, greet

    # Search for function
    results = await manager.search("print hello", top_k=5)

    # Verify results
    assert len(results) > 0
    assert results[0].entity_name == "hello_world"
    assert results[0].entity_type == "function"
    assert results[0].similarity > 0.5

@pytest.mark.asyncio
async def test_file_watching_workflow(tmp_path, test_db, test_embedder):
    """Test file watching and reindexing."""
    # Create test file
    test_file = tmp_path / "test.py"
    test_file.write_text("def original(): pass")

    # Initialize with watching
    manager = CodeSearchManager(
        repo_path=str(tmp_path),
        project_id=1,
        db=test_db,
        embedder=test_embedder,
        enable_watching=True,
    )

    await manager.initialize()
    manager.start_watching()

    # Verify original indexed
    results = await manager.search("original", top_k=1)
    assert len(results) == 1
    assert results[0].entity_name == "original"

    # Modify file
    test_file.write_text("def modified(): pass")

    # Wait for reindex
    await asyncio.sleep(3)  # Debounce + processing

    # Verify new function indexed
    results = await manager.search("modified", top_k=1)
    assert len(results) == 1
    assert results[0].entity_name == "modified"

    # Verify old function removed
    results = await manager.search("original", top_k=1)
    assert len(results) == 0

    manager.stop_watching()
```

### 6.3 Performance Tests

**Benchmarks**:
```python
# tests/performance/test_code_search_performance.py

import pytest
import time
from athena.code_search.manager import CodeSearchManager

@pytest.mark.benchmark
async def test_indexing_performance(large_repo_path, test_db, test_embedder):
    """Benchmark indexing performance."""
    manager = CodeSearchManager(
        repo_path=large_repo_path,  # 1000+ files
        project_id=1,
        db=test_db,
        embedder=test_embedder,
    )

    start = time.time()
    stats = await manager.initialize()
    duration = time.time() - start

    # Performance targets
    assert duration < 300  # <5 minutes for 1000 files
    assert stats.units_per_file > 3  # At least 3 entities per file

    print(f"Indexed {stats.indexed_files} files in {duration:.2f}s")
    print(f"Throughput: {stats.indexed_files / duration:.2f} files/sec")

@pytest.mark.benchmark
async def test_search_performance(indexed_manager):
    """Benchmark search performance."""
    queries = [
        "authentication",
        "database connection",
        "error handling",
        "where is config",
        "function that validates input",
    ]

    for query in queries:
        start = time.time()
        results = await indexed_manager.search(query, top_k=10)
        duration = (time.time() - start) * 1000  # ms

        # Performance targets
        assert duration < 100  # <100ms per search
        assert len(results) > 0  # Returns results

        print(f"Query '{query}': {duration:.2f}ms, {len(results)} results")
```

### 6.4 Test Data

**Create Test Repository**:
```python
# tests/fixtures/test_repository.py

def create_test_repository(tmp_path):
    """Create a test repository with diverse code."""

    # main.py
    (tmp_path / "main.py").write_text("""
import os
from auth import setup_auth
from database import connect_db

def main():
    '''Main entry point.'''
    db = connect_db()
    setup_auth(app)
    app.run()

if __name__ == "__main__":
    main()
""")

    # auth.py
    auth_dir = tmp_path / "auth"
    auth_dir.mkdir()
    (auth_dir / "config.py").write_text("""
def setup_auth(app):
    '''Configure authentication.'''
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
    return app

class AuthMiddleware:
    '''Authentication middleware.'''
    def process_request(self, request):
        token = request.headers.get('Authorization')
        if not token:
            raise AuthError('Missing token')
""")

    # database.py
    (tmp_path / "database.py").write_text("""
import psycopg2

def connect_db():
    '''Connect to PostgreSQL database.'''
    return psycopg2.connect(
        host='localhost',
        database='athena',
        user='postgres'
    )

class Database:
    '''Database connection manager.'''
    def __init__(self, conn_string):
        self.conn = psycopg2.connect(conn_string)

    def execute(self, query, params=None):
        '''Execute SQL query.'''
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()
""")

    # .gitignore
    (tmp_path / ".gitignore").write_text("""
*.pyc
__pycache__/
.env
.venv/
*.log
""")

    return tmp_path
```

---

## 7. Performance Benchmarks

### 7.1 Indexing Performance

**Target**: <5 minutes for 1,000 files, <30 minutes for 10,000 files

**Factors**:
- File size
- Language complexity
- Embedding generation time
- Database write speed

**Optimization Strategies**:
1. Batch embedding generation (50 units at a time)
2. Parallel file parsing (4-8 workers)
3. PostgreSQL connection pooling
4. Incremental indexing (skip unchanged files)

**Expected Throughput**:
```
Small repos (<100 files):   ~20 files/sec  → ~5 seconds
Medium repos (1K files):    ~10 files/sec  → ~100 seconds
Large repos (10K files):    ~5 files/sec   → ~2000 seconds (~33 min)
```

### 7.2 Search Performance

**Target**: <100ms for semantic search, <50ms with caching

**Factors**:
- Query embedding generation (~20ms)
- PostgreSQL pgvector search (~30ms)
- Result ranking (~10ms)
- Total: ~60ms

**Caching Strategy**:
- Query-level cache (5 minutes TTL)
- Embedding cache (same query → skip embedding)
- Result cache (full results for 1 minute)

**Expected Latency**:
```
Cold query (no cache):    ~80ms
Warm query (cached emb):  ~60ms
Hot query (cached result): ~5ms
```

### 7.3 Memory Usage

**Target**: <2GB for 10,000 files

**Memory Breakdown**:
- Code units in memory: ~1MB per 100 files → ~100MB for 10K
- Embeddings (stored in PostgreSQL, not RAM): 0MB
- Parser overhead: ~500MB
- Database connections: ~50MB
- Total: ~650MB base + ~100MB per 10K files

**Optimization**:
- Don't load all embeddings into RAM (use PostgreSQL)
- Lazy-load code units (only when needed)
- Clear parser cache periodically

---

## 8. Configuration Management

### 8.1 Environment Variables

**File**: `src/athena/core/config.py` (ADDITIONS)

```python
# Code Search Configuration
CODE_SEARCH_ENABLED = os.environ.get("ATHENA_CODE_SEARCH_ENABLED", "true").lower() == "true"
CODE_SEARCH_AUTO_WATCH = os.environ.get("ATHENA_CODE_SEARCH_AUTO_WATCH", "false").lower() == "true"
CODE_SEARCH_BATCH_SIZE = int(os.environ.get("ATHENA_CODE_SEARCH_BATCH_SIZE", "50"))
CODE_SEARCH_DEBOUNCE_SECONDS = float(os.environ.get("ATHENA_CODE_SEARCH_DEBOUNCE_SECONDS", "2.0"))
CODE_SEARCH_MAX_FILE_SIZE_MB = int(os.environ.get("ATHENA_CODE_SEARCH_MAX_FILE_SIZE_MB", "5"))

# File extensions to index
CODE_SEARCH_EXTENSIONS = os.environ.get(
    "ATHENA_CODE_SEARCH_EXTENSIONS",
    ".py,.js,.ts,.jsx,.tsx,.java,.go,.rs,.cpp,.c,.h"
).split(",")

# Skip patterns (in addition to .gitignore)
CODE_SEARCH_SKIP_PATTERNS = os.environ.get(
    "ATHENA_CODE_SEARCH_SKIP_PATTERNS",
    "__pycache__,.git,.venv,node_modules,dist,build,.pytest_cache"
).split(",")
```

### 8.2 Configuration File

**File**: `.athena/code_search_config.yaml` (NEW)

```yaml
# Athena Code Search Configuration

# Enable/disable code search
enabled: true

# File watching
watching:
  enabled: true
  debounce_seconds: 2.0

# Indexing
indexing:
  batch_size: 50
  max_file_size_mb: 5
  parallel_workers: 4
  skip_unchanged: true

# File extensions to index (by language)
languages:
  python:
    extensions: [".py"]
    enabled: true
  javascript:
    extensions: [".js", ".jsx"]
    enabled: true
  typescript:
    extensions: [".ts", ".tsx"]
    enabled: true
  java:
    extensions: [".java"]
    enabled: true
  go:
    extensions: [".go"]
    enabled: true
  rust:
    extensions: [".rs"]
    enabled: false  # Optional

# Skip patterns (in addition to .gitignore)
skip_patterns:
  - "__pycache__"
  - ".git"
  - ".venv"
  - "venv"
  - "node_modules"
  - "dist"
  - "build"
  - ".pytest_cache"
  - ".mypy_cache"
  - "*.egg-info"

# Search configuration
search:
  default_top_k: 10
  min_similarity: 0.3
  hybrid_weights:
    semantic: 0.7
    keyword: 0.3
  enable_reranking: true
  cache_ttl_seconds: 300

# Integration with Athena layers
integration:
  episodic_memory: true  # Record search events
  knowledge_graph: true  # Extract code entities
  procedural_learning: true  # Learn search patterns
  semantic_memory: true  # Store code insights
```

### 8.3 Project-Specific Configuration

**File**: `.athenaignore` (NEW, optional)

```
# Custom ignore patterns for Athena code search
# (In addition to .gitignore)

# Generated files
*.min.js
*.bundle.js

# Documentation
docs/
*.md

# Test fixtures
tests/fixtures/
test_data/

# Large data files
*.csv
*.json
```

---

## 9. Deployment Guide

### 9.1 Installation

**Add to `setup.py`**:
```python
install_requires=[
    # ... existing dependencies ...
    "pathspec==0.11.2",
    "watchdog==3.0.0",
]
```

**Install**:
```bash
pip install -e ".[dev]"
```

### 9.2 Database Migration

**Create migration script**:
```bash
# Create tables
python -m athena.code_search.schema

# Or via SQL
psql -h localhost -U postgres -d athena -f src/athena/code_search/schema.sql
```

### 9.3 First-Time Setup

**For existing Athena installation**:
```bash
# 1. Initialize code search for a repository
athena code-search init --path /home/user/my-project --project-id 1

# 2. Start watching (optional)
athena code-search watch --path /home/user/my-project

# 3. Test search
athena code-search search "database connection"

# 4. View statistics
athena code-search stats
```

**Programmatic setup**:
```python
from athena.code_search import operations

# Initialize
operations.initialize(
    repo_path="/home/user/my-project",
    project_id=1,
    enable_watching=True,
)

# Search
results = await operations.search("authentication setup", top_k=10)

# Start watching
await operations.start_watching()
```

### 9.4 Integration with Hooks

**File**: `~/.claude/hooks/code_search_hook.sh` (NEW)

```bash
#!/bin/bash
# SessionStart hook to initialize code search

# Get current working directory
REPO_PATH=$(pwd)

# Check if .athena/code_search_enabled exists
if [ -f "$REPO_PATH/.athena/code_search_enabled" ]; then
    echo "Initializing code search for $REPO_PATH..."

    # Initialize code search (if not already indexed)
    python3 -c "
from athena.code_search import operations
import asyncio

asyncio.run(operations.initialize(
    repo_path='$REPO_PATH',
    project_id=1,
    enable_watching=True,
))
    " 2>/dev/null

    echo "Code search ready. Try: athena code-search search <query>"
fi
```

**Enable for repository**:
```bash
cd /home/user/my-project
mkdir -p .athena
touch .athena/code_search_enabled
```

---

## 10. Migration Path

### 10.1 From Existing Code Search

**If you have existing code search implementation**:

1. **Export existing index**:
```python
# Export old index
from athena.code_search_old import indexer

old_units = indexer.get_all_units()

# Convert to new format
for unit in old_units:
    await new_manager.store_entity(
        file_path=unit.file_path,
        entity_name=unit.name,
        entity_type=unit.type,
        # ... other fields
    )
```

2. **Migrate embeddings**:
```python
# Re-generate embeddings with new model
for unit in old_units:
    embedding = embedder.embed(unit.search_text)
    await db.update_embedding(unit.id, embedding)
```

3. **Rebuild indexes**:
```bash
athena code-search init --path /home/user/my-project --force
```

### 10.2 From mgrep

**If migrating from mgrep**:

1. **Export mgrep results**:
```bash
# mgrep doesn't have export, so re-index with Athena
athena code-search init --path /home/user/my-project
```

2. **Compare results** (sanity check):
```bash
# mgrep
mgrep "authentication setup"

# Athena
athena code-search search "authentication setup"

# Results should be similar
```

3. **Disable mgrep watching**:
```bash
# Stop mgrep watcher
pkill -f "mgrep watch"

# Start Athena watcher
athena code-search watch --path /home/user/my-project
```

### 10.3 Rollback Plan

**If issues arise**:

1. **Disable code search**:
```bash
export ATHENA_CODE_SEARCH_ENABLED=false
```

2. **Stop watcher**:
```bash
athena code-search stop-watching
```

3. **Drop tables** (if needed):
```sql
DROP TABLE code_search_stats;
DROP TABLE code_dependencies;
DROP TABLE code_index;
DROP TABLE code_entities;
```

4. **Revert to previous version**:
```bash
git checkout <previous-commit>
pip install -e .
```

---

## Appendix A: Dependencies

### A.1 Python Packages

```txt
# Code search specific
pathspec==0.11.2        # .gitignore parsing
watchdog==3.0.0         # File system watching

# Existing Athena dependencies (already installed)
tree-sitter>=0.20.0     # Code parsing
psycopg[binary]>=3.1.0  # PostgreSQL driver
pgvector>=0.2.0         # Vector operations
httpx>=0.24.0           # HTTP client (for llama.cpp)
```

### A.2 System Dependencies

```bash
# Tree-sitter grammars (if not already installed)
git clone https://github.com/tree-sitter/tree-sitter-python
git clone https://github.com/tree-sitter/tree-sitter-javascript
git clone https://github.com/tree-sitter/tree-sitter-typescript
git clone https://github.com/tree-sitter/tree-sitter-java
git clone https://github.com/tree-sitter/tree-sitter-go
```

### A.3 PostgreSQL Extensions

```sql
-- pgvector (if not already enabled)
CREATE EXTENSION IF NOT EXISTS vector;

-- Full-text search (built-in)
-- No additional extensions needed
```

---

## Appendix B: Performance Tuning

### B.1 PostgreSQL Optimization

```sql
-- Increase shared buffers for vector operations
ALTER SYSTEM SET shared_buffers = '4GB';

-- Optimize for vector similarity search
ALTER SYSTEM SET effective_cache_size = '8GB';

-- Increase work_mem for sorting
ALTER SYSTEM SET work_mem = '256MB';

-- Reload configuration
SELECT pg_reload_conf();
```

### B.2 Embedding Generation Optimization

```python
# Batch embedding generation
async def embed_batch(texts: List[str]) -> List[List[float]]:
    """Generate embeddings in batches for better throughput."""
    batch_size = 50
    embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        batch_embeddings = await asyncio.gather(*[
            embedder.embed(text) for text in batch
        ])
        embeddings.extend(batch_embeddings)

    return embeddings
```

### B.3 Caching Strategy

```python
# Three-level cache
class CodeSearchCache:
    def __init__(self):
        self.query_cache = {}  # Query → Results (1 min TTL)
        self.embedding_cache = {}  # Text → Embedding (5 min TTL)
        self.entity_cache = {}  # Entity ID → Entity (10 min TTL)

    async def search(self, query: str):
        # Check query cache
        if query in self.query_cache:
            return self.query_cache[query]

        # Check embedding cache
        if query in self.embedding_cache:
            embedding = self.embedding_cache[query]
        else:
            embedding = await embedder.embed(query)
            self.embedding_cache[query] = embedding

        # Execute search
        results = await db.vector_search(embedding)

        # Cache results
        self.query_cache[query] = results

        return results
```

---

## Appendix C: Troubleshooting

### C.1 Common Issues

**Issue**: "Code search not initialized"
```bash
# Solution: Initialize code search first
athena code-search init --path /home/user/my-project
```

**Issue**: "File watcher not detecting changes"
```bash
# Solution: Check inotify limits (Linux)
cat /proc/sys/fs/inotify/max_user_watches

# Increase limit
echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

**Issue**: "PostgreSQL out of memory during indexing"
```bash
# Solution: Reduce batch size
export ATHENA_CODE_SEARCH_BATCH_SIZE=25
```

**Issue**: "Embeddings taking too long"
```bash
# Solution: Check llama.cpp server
curl http://localhost:8001/health

# Restart if needed
./llama-server -m nomic-embed-text-v1.5.Q4_K_M.gguf --embedding --port 8001
```

### C.2 Debug Logging

```python
# Enable debug logging
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("athena.code_search")
logger.setLevel(logging.DEBUG)
```

### C.3 Performance Profiling

```python
# Profile search performance
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# Run search
results = await manager.search("authentication")

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats("cumulative")
stats.print_stats(20)
```

---

## Conclusion

This implementation guide provides a complete roadmap for integrating local semantic code search into Athena. The design leverages existing infrastructure (PostgreSQL, llama.cpp, tree-sitter) while adding minimal dependencies (pathspec, watchdog).

**Key Benefits**:
- ✅ 100% local, privacy-preserving
- ✅ Deep integration with Athena's memory layers
- ✅ Natural language queries
- ✅ Automatic incremental indexing
- ✅ Cross-session memory
- ✅ No cloud costs

**Next Steps**:
1. Review and approve design
2. Begin Phase 1 implementation
3. Test on Athena codebase
4. Deploy to production

**Estimated Timeline**: 4-6 weeks for full implementation across all phases.
