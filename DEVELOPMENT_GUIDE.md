# Athena Development Guide

## Table of Contents

1. [Project Structure](#project-structure)
2. [Development Environment Setup](#development-environment-setup)
3. [Development Workflow](#development-workflow)
4. [Code Organization](#code-organization)
5. [Testing Strategy](#testing-strategy)
6. [Adding New Features](#adding-new-features)
7. [MCP Tool Development](#mcp-tool-development)
8. [Database Schema Management](#database-schema-management)
9. [Memory Layer Extensions](#memory-layer-extensions)
10. [Performance Considerations](#performance-considerations)

---

## Project Structure

```
/home/user/.work/athena/
├── .venv/                          # Python virtual environment
├── src/athena/                     # Main source code (46 directories)
│   ├── core/                       # Core interfaces & database
│   │   ├── database.py            # SQLite + sqlite-vec connection
│   │   ├── models.py              # Core data models
│   │   ├── config.py              # Configuration management
│   │   └── interfaces.py           # Abstract base classes
│   │
│   ├── episodic/                   # Temporal event storage (Layer 1)
│   │   ├── storage.py             # Event persistence
│   │   ├── temporal.py            # Temporal reasoning
│   │   ├── surprise.py            # Bayesian surprise detection
│   │   └── buffer.py              # Working memory buffer
│   │
│   ├── semantic/                   # Knowledge representation (Layer 2)
│   │   ├── storage.py             # Semantic memory persistence
│   │   ├── embeddings.py          # Vector embedding generation
│   │   ├── search.py              # Hybrid BM25 + vector search
│   │   └── cache.py               # Search result caching
│   │
│   ├── procedural/                 # Workflow learning (Layer 3)
│   │   ├── procedures.py          # Procedure storage & execution
│   │   ├── extraction.py          # Learn patterns from events
│   │   └── effectiveness.py       # Procedure quality metrics
│   │
│   ├── prospective/                # Task triggers (Layer 4)
│   │   ├── tasks.py               # Task management
│   │   ├── triggers.py            # Event/time/file-based triggers
│   │   └── goals.py               # Goal hierarchy
│   │
│   ├── graph/                      # Knowledge graph (Layer 5)
│   │   ├── store.py               # Entity & relation storage
│   │   ├── entities.py            # Entity management
│   │   ├── relations.py           # Relation types
│   │   ├── communities.py         # Community detection (Leiden)
│   │   └── observations.py        # Contextual observations
│   │
│   ├── meta/                       # Meta-memory (Layer 6)
│   │   ├── quality.py             # Quality metrics
│   │   ├── expertise.py           # Domain expertise tracking
│   │   ├── attention.py           # Attention & salience
│   │   └── load.py                # Cognitive load tracking
│   │
│   ├── consolidation/              # Sleep-like consolidation (Layer 7)
│   │   ├── consolidator.py        # Main consolidation engine
│   │   ├── clustering.py          # Event clustering
│   │   ├── patterns.py            # Pattern extraction
│   │   └── validation.py          # LLM pattern validation
│   │
│   ├── rag/                        # Retrieval Augmented Generation
│   │   ├── manager.py             # RAG orchestration
│   │   ├── reflective.py          # Self-reflective RAG
│   │   ├── hyde.py                # Hypothetical document embeddings
│   │   ├── reranker.py            # LLM reranking
│   │   └── query_transform.py     # Query refinement
│   │
│   ├── planning/                   # Advanced planning
│   │   ├── validator.py           # Comprehensive plan validation
│   │   ├── formal_verification.py # Q* verification engine
│   │   ├── scenario_simulator.py  # 5-scenario simulation
│   │   └── adaptive_replanning.py # Adaptive replanning strategies
│   │
│   ├── associations/               # Zettelkasten & learning
│   │   ├── zettelkasten.py        # Memory versioning & evolution
│   │   ├── hierarchical_index.py  # Luhmann numbering
│   │   └── hebbian.py             # Association strengthening
│   │
│   ├── mcp/                        # MCP server & tools
│   │   ├── server.py              # MCP server initialization
│   │   ├── operation_router.py    # Tool routing
│   │   ├── memory_tools.py        # Core memory operations
│   │   ├── graph_tools.py         # Graph operations
│   │   ├── planning_tools.py      # Planning tools
│   │   ├── zettelkasten_tools.py  # Zettelkasten tools
│   │   ├── graphrag_tools.py      # GraphRAG tools
│   │   └── handlers.py            # Tool handlers
│   │
│   └── utils/                      # Utilities
│       ├── logging.py             # Logging configuration
│       ├── caching.py             # Caching utilities
│       └── metrics.py             # Performance metrics
│
├── memory.db                       # SQLite database (5.5 MB)
├── README.md                       # Project overview
├── CONTRIBUTING.md                 # Contribution guidelines
├── CHANGELOG.md                    # Version history
├── PERFORMANCE_TUNING.md          # Performance optimization guide
├── DEVELOPMENT_GUIDE.md           # This file
├── requirements.txt               # Python dependencies
└── pyproject.toml                # Project metadata

```

---

## Development Environment Setup

### 1. Prerequisites

```bash
# Verify Python version (3.10+ required)
python3 --version

# Install system dependencies (Ubuntu/Debian)
sudo apt-get install sqlite3 libsqlite3-dev python3-dev
```

### 2. Virtual Environment

```bash
cd /home/user/.work/athena

# Create fresh virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -q mcp ollama sqlite-vec anthropic pydantic aiofiles typing-extensions
pip install -q psutil pytest-asyncio pytest-benchmark numpy scipy scikit-learn pyyaml
pip install -q click textwrap3 tabulate

# Verify installation
python3 -c "import athena; print('✓ Athena installed')"
```

### 3. Environment Variables

```bash
# Required
export MEMORY_MCP_DB_PATH=/home/user/.work/athena/memory.db
export PYTHONPATH=/home/user/.work/athena/src

# Optional
export OLLAMA_BASE_URL=http://localhost:11434  # For local LLM
export ANTHROPIC_API_KEY=sk-...                 # For Claude API
```

### 4. Database Initialization

```bash
# Check database status
sqlite3 /home/user/.work/athena/memory.db ".tables"

# Get statistics
sqlite3 /home/user/.work/athena/memory.db << EOF
SELECT 'Episodic Events' as table_name, COUNT(*) as count FROM episodic_events
UNION ALL
SELECT 'Procedures', COUNT(*) FROM procedures
UNION ALL
SELECT 'Semantic Memories', COUNT(*) FROM semantic_memories
UNION ALL
SELECT 'Entities', COUNT(*) FROM entities
UNION ALL
SELECT 'Relations', COUNT(*) FROM entity_relations;
EOF
```

---

## Development Workflow

### Daily Development Loop

```
1. Session Start
   ↓
2. Check memory health: /memory-health
   ↓
3. Review goals: /project-status
   ↓
4. Load project context: /memory-query "athena architecture"
   ↓
5. Development work (hooks auto-record)
   ↓
6. Run tests: pytest src/athena/tests/
   ↓
7. Check code quality: python -m pylint src/athena/
   ↓
8. Session End: Consolidation runs automatically
```

### Version Control

```bash
# Create feature branch
git checkout -b feature/description

# Make changes and test
[development work]
pytest src/athena/tests/

# Commit with semantic message
git add .
git commit -m "feat: Add new feature

Detailed description of changes.

Fixes: #123"

# Push to origin
git push -u origin feature/description

# Create pull request on GitHub
gh pr create --title "feat: Add new feature" --body "..."
```

### Code Review Standards

**Before pushing**:
- ✅ All tests pass (`pytest src/athena/tests/`)
- ✅ No type errors (`mypy src/athena/`)
- ✅ Code formatted (`black src/athena/`)
- ✅ Documentation updated
- ✅ Performance impact measured (if performance-sensitive)

**Pull request checklist**:
- ✅ Tests pass in CI
- ✅ Coverage ≥90% for new code
- ✅ No breaking changes (or major version bump)
- ✅ Changelog updated
- ✅ Documentation updated

---

## Code Organization

### Naming Conventions

**Modules & Files**:
- Use snake_case for filenames: `semantic_search.py`, `graph_store.py`
- One main class per module when possible

**Classes**:
- Use PascalCase: `SemanticSearch`, `GraphStore`, `ConsolidationEngine`
- Abstract base classes start with `Abstract`: `AbstractMemoryLayer`
- Handlers end with `Handlers`: `MemoryMCPHandlers`

**Functions & Methods**:
- Use snake_case: `retrieve()`, `create_entity()`, `compute_metrics()`
- Private methods start with underscore: `_internal_helper()`
- Async functions explicitly named: `async def retrieve_async()`

**Constants**:
- Use UPPER_CASE: `MAX_BATCH_SIZE = 32`, `CONFIDENCE_THRESHOLD = 0.8`

### Import Organization

```python
# Standard library imports
import asyncio
import json
import logging
from typing import Optional, List

# Third-party imports
import numpy as np
from pydantic import BaseModel, Field

# Local imports
from ..core.models import MemorySearchResult
from ..core.database import Database
from .base import AbstractMemoryLayer

# Avoid circular imports by using TYPE_CHECKING
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..semantic.search import SemanticSearch
```

### Type Hints

**Always use type hints**:
```python
def retrieve(
    query: str,
    project_id: int,
    k: int = 5,
    min_similarity: float = 0.3,
) -> list[MemorySearchResult]:
    """Retrieve similar memories.

    Args:
        query: Search query text
        project_id: Project to search within
        k: Number of results to return
        min_similarity: Minimum similarity threshold (0-1)

    Returns:
        List of ranked memory search results
    """
```

### Documentation Standards

**Module docstrings**:
```python
"""Semantic memory storage with vector embeddings.

This module provides:
- Vector embedding generation via Ollama
- Hybrid BM25 + vector search
- Semantic memory persistence in SQLite
- LRU caching for search results
"""
```

**Function docstrings** (Google style):
```python
def retrieve(query: str, project_id: int, k: int = 5) -> list[MemorySearchResult]:
    """Retrieve semantically similar memories.

    Uses hybrid BM25 + vector search to find relevant memories.
    Results are ranked by relevance and recency.

    Args:
        query: Text to search for
        project_id: Project context (scopes results)
        k: Number of top results to return

    Returns:
        Ranked list of matching memories with scores

    Raises:
        DatabaseError: If database query fails
        EmbeddingError: If embedding generation fails

    Examples:
        >>> search = SemanticSearch(db)
        >>> results = search.retrieve("authentication", project_id=1, k=5)
        >>> print(f"Found {len(results)} results")
    """
```

---

## Testing Strategy

### Test Organization

```
src/athena/tests/
├── conftest.py              # Shared fixtures
├── test_episodic.py         # Episodic layer tests
├── test_semantic.py         # Semantic layer tests
├── test_procedural.py       # Procedural layer tests
├── test_planning.py         # Planning & verification tests
├── test_rag.py              # RAG system tests
├── test_consolidation.py    # Consolidation tests
├── test_graph.py            # Knowledge graph tests
├── test_mcp.py              # MCP tool tests
└── integration/
    ├── test_memory_flow.py  # End-to-end workflows
    └── test_performance.py  # Performance benchmarks
```

### Running Tests

```bash
# Run all tests
pytest src/athena/tests/ -v

# Run specific test file
pytest src/athena/tests/test_semantic.py -v

# Run specific test function
pytest src/athena/tests/test_semantic.py::test_retrieve -v

# Run with coverage
pytest src/athena/tests/ --cov=src/athena --cov-report=html

# Run performance benchmarks
pytest src/athena/tests/integration/test_performance.py -v --benchmark-only

# Run specific markers
pytest src/athena/tests/ -m "not slow" -v
```

### Test Fixtures (conftest.py)

```python
import pytest
from athena.core.database import Database
from athena.semantic.search import SemanticSearch

@pytest.fixture
def test_db():
    """Create temporary test database."""
    db = Database(":memory:")  # In-memory SQLite
    db.initialize_schema()
    yield db
    db.close()

@pytest.fixture
def semantic_search(test_db):
    """Initialize semantic search for testing."""
    return SemanticSearch(test_db)

@pytest.fixture
def sample_memories():
    """Sample memory data for testing."""
    return [
        {
            "content": "Authentication using JWT tokens",
            "memory_type": "semantic",
            "project_id": 1,
        },
        {
            "content": "Database optimization strategies",
            "memory_type": "semantic",
            "project_id": 1,
        },
    ]
```

### Test Example

```python
def test_retrieve_with_similarity_threshold(semantic_search, sample_memories):
    """Test that results below threshold are filtered."""
    # Arrange
    for mem in sample_memories:
        semantic_search.create(mem)

    # Act
    results = semantic_search.retrieve(
        "JWT authentication",
        project_id=1,
        min_similarity=0.5
    )

    # Assert
    assert len(results) > 0
    assert all(r.similarity >= 0.5 for r in results)
    assert results[0].similarity >= results[-1].similarity  # Sorted
```

### Performance Testing

```python
@pytest.mark.benchmark
def test_semantic_search_performance(benchmark, semantic_search):
    """Benchmark semantic search latency."""
    # Setup: Pre-load 1000 memories
    for i in range(1000):
        semantic_search.create({
            "content": f"Memory {i} content",
            "project_id": 1
        })

    # Benchmark
    result = benchmark(
        semantic_search.retrieve,
        "relevant query",
        project_id=1,
        k=5
    )

    # Verify
    assert len(result) == 5
    # Target: <100ms per search
```

---

## Adding New Features

### Feature Checklist

- [ ] Create GitHub issue describing feature
- [ ] Plan design & approach
- [ ] Create feature branch: `git checkout -b feature/name`
- [ ] Implement feature with tests
- [ ] Update documentation
- [ ] Update CHANGELOG.md
- [ ] Ensure all tests pass & coverage ≥90%
- [ ] Create pull request for review
- [ ] Address review feedback
- [ ] Merge to main & tag release

### Example: Adding a New Memory Layer

#### Step 1: Define Abstract Interface

```python
# src/athena/core/interfaces.py
from abc import ABC, abstractmethod

class MemoryLayer(ABC):
    """Abstract interface for memory layers."""

    @abstractmethod
    async def store(self, memory: Memory) -> int:
        """Store a memory."""
        pass

    @abstractmethod
    async def retrieve(self, query: str, k: int = 5) -> list[Memory]:
        """Retrieve memories matching query."""
        pass
```

#### Step 2: Implement Concrete Layer

```python
# src/athena/new_layer/storage.py
from ..core.interfaces import MemoryLayer
from ..core.database import Database

class NewLayer(MemoryLayer):
    """Implementation of new memory layer."""

    def __init__(self, db: Database):
        self.db = db
        self._initialize_schema()

    def _initialize_schema(self):
        """Create database tables."""
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS new_layer (
                id INTEGER PRIMARY KEY,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    async def store(self, memory: Memory) -> int:
        """Implementation details."""
        pass

    async def retrieve(self, query: str, k: int = 5) -> list[Memory]:
        """Implementation details."""
        pass
```

#### Step 3: Add Tests

```python
# src/athena/tests/test_new_layer.py
import pytest
from athena.new_layer.storage import NewLayer

@pytest.fixture
def new_layer(test_db):
    return NewLayer(test_db)

def test_store_and_retrieve(new_layer):
    """Test basic storage and retrieval."""
    # Arrange
    memory = Memory(content="Test", type="new_layer")

    # Act
    memory_id = new_layer.store(memory)
    results = new_layer.retrieve("test", k=1)

    # Assert
    assert memory_id > 0
    assert len(results) == 1
    assert results[0].content == "Test"
```

#### Step 4: Integrate into MCP

```python
# src/athena/mcp/new_layer_tools.py
from mcp.types import Tool, TextContent

def get_new_layer_tools() -> list[Tool]:
    return [
        Tool(
            name="store_in_new_layer",
            description="Store memory in new layer",
            inputSchema={...}
        ),
        Tool(
            name="retrieve_from_new_layer",
            description="Retrieve from new layer",
            inputSchema={...}
        ),
    ]
```

#### Step 5: Update Documentation

- Add section to ARCHITECTURE.md explaining layer design
- Document API in API_REFERENCE.md
- Add usage example to EXAMPLES.md

---

## MCP Tool Development

### Tool Structure

```python
# Define tool interface
def get_tools() -> list[Tool]:
    return [
        Tool(
            name="operation_name",
            description="Human-readable description",
            inputSchema={
                "type": "object",
                "properties": {
                    "param1": {
                        "type": "string",
                        "description": "Parameter description"
                    },
                },
                "required": ["param1"],
            }
        ),
    ]

# Implement handlers
class OperationHandlers:
    def __init__(self, db: Database):
        self.db = db

    async def operation_name(self, param1: str) -> TextContent:
        try:
            # Implementation
            result = self._do_something(param1)
            return TextContent(type="text", text=f"✓ Success: {result}")
        except Exception as e:
            return TextContent(type="text", text=f"❌ Error: {str(e)}")
```

### Tool Routing

```python
# src/athena/mcp/operation_router.py
from mcp.server import RequestContext
from mcp.types import TextContent

async def handle_tool_call(
    name: str,
    arguments: dict,
    context: RequestContext,
    handlers: dict,
) -> TextContent:
    """Route tool calls to appropriate handlers."""

    if name.startswith("memory_"):
        handler = handlers["memory"]
        method_name = name.replace("memory_", "")
    elif name.startswith("graph_"):
        handler = handlers["graph"]
        method_name = name.replace("graph_", "")
    else:
        return TextContent(type="text", text=f"Unknown tool: {name}")

    # Call handler method
    method = getattr(handler, method_name, None)
    if not method:
        return TextContent(type="text", text=f"Unknown operation: {name}")

    return await method(**arguments)
```

### Error Handling Standards

```python
# Good: Specific error handling
try:
    result = self.search.retrieve(query)
except DatabaseError as e:
    logger.error(f"Database error: {e}")
    return TextContent(type="text", text=f"❌ Database error: {str(e)}")
except EmbeddingError as e:
    logger.error(f"Embedding generation failed: {e}")
    return TextContent(type="text", text=f"❌ Could not generate embeddings")
except Exception as e:
    logger.error(f"Unexpected error: {e}", exc_info=True)
    return TextContent(type="text", text=f"❌ Error: {str(e)}")

# Good: Provide actionable feedback
if not results:
    return TextContent(
        type="text",
        text="No memories found. Try a different query or check /memory-health"
    )
```

---

## Database Schema Management

### Current Schema

```sql
-- Episodic events
CREATE TABLE episodic_events (
    id INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    event_type TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    context JSONB,
    FOREIGN KEY(project_id) REFERENCES projects(id)
);

-- Procedures
CREATE TABLE procedures (
    id INTEGER PRIMARY KEY,
    project_id INTEGER,
    name TEXT NOT NULL,
    description TEXT,
    steps JSONB NOT NULL,
    category TEXT,
    created_at TIMESTAMP,
    effectiveness_score REAL
);

-- Semantic memories
CREATE TABLE semantic_memories (
    id INTEGER PRIMARY KEY,
    project_id INTEGER,
    content TEXT NOT NULL,
    embedding VECTOR NOT NULL,
    memory_type TEXT,
    created_at TIMESTAMP,
    last_accessed TIMESTAMP
);

-- Entities
CREATE TABLE entities (
    id INTEGER PRIMARY KEY,
    project_id INTEGER,
    name TEXT NOT NULL,
    entity_type TEXT,
    description TEXT,
    created_at TIMESTAMP
);

-- Entity relations
CREATE TABLE entity_relations (
    id INTEGER PRIMARY KEY,
    project_id INTEGER,
    from_entity_id INTEGER,
    to_entity_id INTEGER,
    relation_type TEXT,
    FOREIGN KEY(from_entity_id) REFERENCES entities(id),
    FOREIGN KEY(to_entity_id) REFERENCES entities(id)
);

-- Indexes for performance
CREATE INDEX idx_episodic_project ON episodic_events(project_id);
CREATE INDEX idx_episodic_created ON episodic_events(created_at);
CREATE INDEX idx_semantic_project ON semantic_memories(project_id);
CREATE INDEX idx_entity_type ON entities(entity_type);
CREATE INDEX idx_relation_from ON entity_relations(from_entity_id);
```

### Schema Migrations

```python
# src/athena/core/migrations.py
def migrate_v1_to_v2():
    """Add new fields to existing tables."""
    db = Database()

    # Add column
    db.execute("""
        ALTER TABLE episodic_events
        ADD COLUMN importance_score REAL DEFAULT 0.5
    """)

    # Create new table
    db.execute("""
        CREATE TABLE IF NOT EXISTS new_feature (
            id INTEGER PRIMARY KEY,
            data TEXT NOT NULL
        )
    """)

    logger.info("Migration complete")
```

---

## Memory Layer Extensions

### Adding Custom Memory Types

```python
# src/athena/custom_layer/storage.py
from dataclasses import dataclass

@dataclass
class CustomMemory:
    """Custom memory data structure."""
    id: int
    content: str
    metadata: dict
    importance: float = 0.5
    created_at: datetime = None

class CustomMemoryStorage:
    def __init__(self, db: Database):
        self.db = db
        self._create_schema()

    def store(self, memory: CustomMemory) -> int:
        """Store custom memory."""
        cursor = self.db.get_connection().cursor()
        cursor.execute("""
            INSERT INTO custom_memories
            (content, metadata, importance, created_at)
            VALUES (?, ?, ?, ?)
        """, (
            memory.content,
            json.dumps(memory.metadata),
            memory.importance,
            datetime.now()
        ))
        return cursor.lastrowid
```

### Extending Consolidation Logic

```python
# src/athena/consolidation/custom_clustering.py
from .clustering import ClusteringStrategy

class CustomClusterer(ClusteringStrategy):
    """Custom clustering algorithm."""

    def cluster(
        self,
        events: list[dict],
        k: int = None,
    ) -> list[list[dict]]:
        """Cluster events using custom algorithm."""
        # Implementation
        pass
```

---

## Performance Considerations

### Profiling

```bash
# Profile memory operations
python -m cProfile -s cumtime -m athena.perf_test > profile.txt

# Profile specific function
from athena.performance.profiler import PerformanceProfiler

profiler = PerformanceProfiler()
with profiler.timer('search_operation'):
    results = search.retrieve("query")

print(profiler.report())
```

### Optimization Checklist

- ✅ Use database indices for frequent queries
- ✅ Batch operations (e.g., `INSERT INTO ... SELECT`)
- ✅ Implement caching for expensive operations
- ✅ Profile before and after optimization
- ✅ Set performance targets & track regression

### Memory Efficiency

```python
# ❌ Inefficient: Load all records
all_records = db.get_all_memories()
for record in all_records:
    if matches_criteria(record):
        process(record)

# ✅ Efficient: Database filtering
results = db.query("SELECT * FROM memories WHERE criteria = ?")
for record in results:
    process(record)
```

---

## Contributing Guidelines

See [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Code of conduct
- Pull request process
- Commit message standards
- Review process
- Release procedures

---

## References

- **Architecture**: [ARCHITECTURE.md](ARCHITECTURE.md)
- **API Reference**: [API_REFERENCE.md](API_REFERENCE.md)
- **Performance**: [PERFORMANCE_TUNING.md](PERFORMANCE_TUNING.md)
- **Troubleshooting**: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **Examples**: [EXAMPLES.md](EXAMPLES.md)
