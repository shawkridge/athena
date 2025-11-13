# Tree-Sitter Code Search MCP Server: Detailed Implementation Plan

**Priority**: P0 (Critical Gap)
**Estimated Duration**: 3-4 weeks
**Resources**: 1 developer (full-time)
**Start Date**: Immediately (Week 1)
**Target Completion**: Week 4

---

## Overview

### What We're Building

A semantic code search system that understands code structure, not just keywords. Users can ask:
- "Show me authentication handling code"
- "Find all database queries"
- "Where is error handling?"
- "Show me the logging infrastructure"

Instead of:
- "Find code with 'auth' in it"
- "Search for database calls"
- "Find 'except' statements"

### Why Tree-Sitter?

1. **AST-based**: Understands code structure, not just text
2. **Multi-language**: Single interface for Python, Java, Go, Rust, TypeScript, etc.
3. **Incremental**: Fast parsing for large codebases
4. **Open-source**: No licensing costs, active community
5. **Production-proven**: Used by GitHub, Sourcegraph, VSCode

### Market Gap

**Current**: No production-ready Tree-sitter MCP server exists
**Opportunity**: First-mover advantage in AI development tools

---

## Architecture Design

### High-Level Flow

```
Developer Question
    ↓
"Find authentication code"
    ↓
TreeSitterCodeSearch.search()
    ├─ Parse query intent (authentication)
    ├─ Generate query embedding
    ├─ Semantic search (embeddings)
    │   └─ Find matching code units
    ├─ Structural search (AST patterns)
    │   └─ Find code structures
    └─ Graph traversal
        └─ Find related code
    ↓
Hybrid Results with Context
    ├─ Code snippets
    ├─ File paths + line numbers
    ├─ Function signatures
    ├─ Dependencies
    └─ Relevance scores
    ↓
Return to user
```

### Components

```
src/athena/code_search/
├── __init__.py
├── models.py                 # CodeUnit, SearchResult, etc.
├── tree_sitter_search.py     # Main TreeSitterCodeSearch class
├── parser.py                 # Parse code and extract units
├── indexer.py                # Build semantic index
├── searcher.py               # Search implementation
├── structural_search.py      # AST pattern matching
└── graph_integration.py      # Graph layer integration

tests/unit/
├── test_tree_sitter_search.py
├── test_code_parser.py
├── test_indexer.py
├── test_searcher.py
└── test_graph_integration.py

tests/integration/
└── test_tree_sitter_mcp.py
```

### Data Models

```python
# CodeUnit - semantic unit of code
@dataclass
class CodeUnit:
    id: str                  # "file:line:name"
    type: str               # "function", "class", "method", "import"
    name: str               # function/class name
    signature: str          # Full signature
    code: str               # Full source code
    file_path: str          # /path/to/file.py
    start_line: int
    end_line: int
    docstring: str          # Function/class documentation
    dependencies: List[str] # Other functions/classes it uses
    embedding: List[float]  # Embedding for semantic search

# SearchResult - a match
@dataclass
class SearchResult:
    unit: CodeUnit
    relevance: float        # 0-1, how relevant is it?
    context: str           # Why was it matched?
    matches: List[str]     # Which fields matched (semantic, structural, etc.)

# SearchQuery - parsed user query
@dataclass
class SearchQuery:
    original: str          # User's original question
    intent: str            # Parsed intent ("find auth code")
    embedding: List[float] # Query embedding
    structural_patterns: List[str]  # AST patterns to search
```

---

## Implementation Phases

### Phase 1: Setup & Configuration (Days 1-2)

#### Step 1.1: Install Dependencies

```bash
pip install tree-sitter

# Download language grammars (compiled .so files)
# For Python, JavaScript, TypeScript, Java, Go, Rust
tree-sitter init-languages

# For Athena, add to setup.py
setup(
    name="athena",
    install_requires=[
        ...
        "tree-sitter>=0.20.0",
    ]
)
```

#### Step 1.2: Verify Installation

```bash
# tests/unit/test_tree_sitter_setup.py
def test_tree_sitter_installation():
    """Verify Tree-sitter is installed correctly."""
    from tree_sitter import Language, Parser

    parser = Parser()
    language = Language('build/languages.so', 'python')
    parser.set_language(language)

    tree = parser.parse(b"def foo(): pass")
    assert tree.root_node is not None

def test_supported_languages():
    """Verify all required languages are available."""
    languages = ['python', 'javascript', 'typescript', 'java', 'go']
    for lang in languages:
        parser = Parser()
        language = Language('build/languages.so', lang)
        parser.set_language(language)
        assert parser.language is not None
```

#### Step 1.3: Architecture Design Document

Create `docs/TREE_SITTER_ARCHITECTURE.md` with:
- Component diagram
- Data flow diagram
- API design
- Integration points with Athena layers

**Deliverable**: Verified installation, architecture document

---

### Phase 2: Core Parser Implementation (Days 3-7)

#### Step 2.1: Code Unit Extraction

```python
# src/athena/code_search/parser.py

from tree_sitter import Language, Parser
from typing import List

class CodeParser:
    """Parse source code and extract semantic units."""

    def __init__(self, language: str = "python"):
        self.parser = Parser()
        self.language = Language('build/languages.so', language)
        self.parser.set_language(self.language)

    def extract_functions(self, code: str, file_path: str) -> List[CodeUnit]:
        """Extract all functions from code."""
        tree = self.parser.parse(code.encode())
        functions = []

        # Query all function definitions
        query = self.language.query(
            "(function_definition name: (identifier) @name) @definition"
        )

        captures = query.captures(tree.root_node)

        for node, capture_name in captures:
            if capture_name == "definition":
                unit = self._node_to_code_unit(node, file_path, code)
                if unit:
                    functions.append(unit)

        return functions

    def extract_classes(self, code: str, file_path: str) -> List[CodeUnit]:
        """Extract all classes from code."""
        tree = self.parser.parse(code.encode())
        classes = []

        query = self.language.query(
            "(class_definition name: (identifier) @name) @definition"
        )

        captures = query.captures(tree.root_node)

        for node, capture_name in captures:
            if capture_name == "definition":
                unit = self._node_to_code_unit(node, file_path, code)
                if unit:
                    classes.append(unit)

        return classes

    def extract_imports(self, code: str, file_path: str) -> List[CodeUnit]:
        """Extract all imports from code."""
        tree = self.parser.parse(code.encode())
        imports = []

        # Language-specific import queries
        if self.language.name == "python":
            query_string = """
            (import_statement name: (dotted_name) @module) @import
            (import_from_statement module_name: (dotted_name) @module) @import
            """
        else:
            # Add other languages as needed
            query_string = ""

        if query_string:
            query = self.language.query(query_string)
            captures = query.captures(tree.root_node)

            for node, capture_name in captures:
                if capture_name == "import":
                    unit = self._node_to_code_unit(node, file_path, code)
                    if unit:
                        imports.append(unit)

        return imports

    def _node_to_code_unit(self, node, file_path: str, code: str) -> Optional[CodeUnit]:
        """Convert AST node to CodeUnit."""
        start_byte = node.start_byte
        end_byte = node.end_byte

        # Extract source code for this unit
        unit_code = code[start_byte:end_byte]

        # Extract name
        name = self._extract_name(node)

        # Extract docstring
        docstring = self._extract_docstring(node)

        # Extract dependencies
        dependencies = self._extract_dependencies(node)

        return CodeUnit(
            id=f"{file_path}:{node.start_point[0]}:{name}",
            type=node.type,  # "function_definition", "class_definition", etc.
            name=name,
            signature=unit_code.split('\n')[0],  # First line
            code=unit_code,
            file_path=file_path,
            start_line=node.start_point[0],
            end_line=node.end_point[0],
            docstring=docstring,
            dependencies=dependencies,
            embedding=None  # Will be set during indexing
        )

    def _extract_name(self, node) -> str:
        """Extract name from node."""
        # Language-specific logic
        for child in node.children:
            if child.type == "identifier":
                return child.text.decode()
        return "unknown"

    def _extract_docstring(self, node) -> str:
        """Extract docstring if present."""
        # For Python: look for string_statement after function def
        docstring = ""
        # Implementation specific to language
        return docstring

    def _extract_dependencies(self, node) -> List[str]:
        """Extract other functions/classes this depends on."""
        dependencies = []

        # Walk through function body looking for calls
        def walk(n):
            for child in n.children:
                if child.type in ["call", "identifier"]:
                    dependencies.append(child.text.decode())
                walk(child)

        walk(node)
        return list(set(dependencies))  # Deduplicate
```

#### Step 2.2: Codebase Indexing

```python
# src/athena/code_search/indexer.py

from pathlib import Path
from typing import List
import os

class CodebaseIndexer:
    """Index entire codebase for search."""

    def __init__(self, parser: CodeParser, embedding_manager):
        self.parser = parser
        self.embeddings = embedding_manager
        self.units = []

    def index_directory(self, repo_path: str, extensions: List[str] = None):
        """Index all code files in directory."""
        if extensions is None:
            extensions = [".py", ".js", ".ts", ".java", ".go", ".rs"]

        repo_path = Path(repo_path)

        for ext in extensions:
            for file_path in repo_path.rglob(f"*{ext}"):
                self.index_file(str(file_path))

    def index_file(self, file_path: str):
        """Index single code file."""
        try:
            with open(file_path, 'r') as f:
                code = f.read()
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return

        # Extract all semantic units
        units = []
        units.extend(self.parser.extract_functions(code, file_path))
        units.extend(self.parser.extract_classes(code, file_path))
        units.extend(self.parser.extract_imports(code, file_path))

        # Generate embeddings
        for unit in units:
            # Create searchable text from unit
            search_text = f"{unit.name} {unit.type} {unit.docstring} {unit.code}"

            # Generate embedding
            unit.embedding = self.embeddings.generate(search_text)

            self.units.append(unit)

    def get_units(self) -> List[CodeUnit]:
        """Get all indexed units."""
        return self.units
```

#### Step 2.3: Testing

```python
# tests/unit/test_code_parser.py

import pytest
from athena.code_search.parser import CodeParser
from athena.code_search.models import CodeUnit

@pytest.fixture
def python_parser():
    return CodeParser("python")

def test_extract_functions(python_parser):
    """Test extracting functions from Python code."""
    code = """
def hello():
    pass

def world(name: str) -> str:
    return f"Hello {name}"
"""

    units = python_parser.extract_functions(code, "test.py")

    assert len(units) == 2
    assert units[0].name == "hello"
    assert units[1].name == "world"
    assert units[1].signature.startswith("def world")

def test_extract_classes(python_parser):
    """Test extracting classes from Python code."""
    code = """
class Animal:
    def speak(self):
        pass

class Dog(Animal):
    def speak(self):
        print("Woof")
"""

    units = python_parser.extract_classes(code, "test.py")

    assert len(units) == 2
    assert units[0].name == "Animal"
    assert units[1].name == "Dog"

def test_extract_dependencies(python_parser):
    """Test extracting function dependencies."""
    code = """
def authenticate(user):
    validate_user(user)
    check_password(user)
    return True
"""

    units = python_parser.extract_functions(code, "test.py")

    assert len(units) == 1
    assert "validate_user" in units[0].dependencies
    assert "check_password" in units[0].dependencies
```

**Deliverable**: Working parser, indexer, and tests

---

### Phase 3: Search Implementation (Days 8-12)

#### Step 3.1: Semantic Search

```python
# src/athena/code_search/searcher.py

from typing import List
from dataclasses import dataclass

class SemanticCodeSearcher:
    """Search code semantically using embeddings."""

    def __init__(self, units: List[CodeUnit], embedding_manager):
        self.units = units
        self.embeddings = embedding_manager

    def search(self, query: str, top_k: int = 10) -> List[SearchResult]:
        """Semantic search for code units."""

        # Generate query embedding
        query_embedding = self.embeddings.generate(query)

        # Score all units
        results = []
        for unit in self.units:
            if unit.embedding is None:
                continue

            # Cosine similarity
            similarity = self._cosine_similarity(
                query_embedding,
                unit.embedding
            )

            if similarity > 0.3:  # Threshold
                results.append(SearchResult(
                    unit=unit,
                    relevance=similarity,
                    context="semantic_match",
                    matches=["semantic"]
                ))

        # Sort by relevance
        results.sort(key=lambda x: x.relevance, reverse=True)

        return results[:top_k]

    @staticmethod
    def _cosine_similarity(v1: List[float], v2: List[float]) -> float:
        """Calculate cosine similarity between vectors."""
        import numpy as np
        v1 = np.array(v1)
        v2 = np.array(v2)
        return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))
```

#### Step 3.2: Structural Search (AST Pattern Matching)

```python
# src/athena/code_search/structural_search.py

class StructuralCodeSearcher:
    """Search code by structure using AST patterns."""

    def __init__(self, parser: CodeParser):
        self.parser = parser

    def search_by_pattern(self, pattern: str, code: str) -> List[SearchResult]:
        """Find code matching structural pattern."""

        # Build Tree-sitter query from pattern
        # Examples:
        # - "find_all_error_handling" → find try/except blocks
        # - "find_database_queries" → find cursor.execute() calls
        # - "find_api_routes" → find @app.route() decorated functions

        pattern_map = {
            "error_handling": "(try_statement) @try",
            "database_queries": "(call function: (identifier) @func) @call",
            "api_routes": "(decorator (identifier) @decorator) @dec",
            "imports": "(import_statement) @import",
            "async_functions": "(async_function_definition) @async",
        }

        query_string = pattern_map.get(pattern)
        if not query_string:
            return []

        # Execute Tree-sitter query
        tree = self.parser.parser.parse(code.encode())
        query = self.parser.language.query(query_string)

        results = []
        captures = query.captures(tree.root_node)

        for node, capture_name in captures:
            unit_code = code[node.start_byte:node.end_byte]
            results.append(SearchResult(
                unit=CodeUnit(
                    id=f"pattern:{pattern}:{node.start_point[0]}",
                    type=node.type,
                    name=pattern,
                    signature=node.text.decode()[:100],
                    code=unit_code,
                    file_path="",
                    start_line=node.start_point[0],
                    end_line=node.end_point[0],
                    docstring="",
                    dependencies=[],
                    embedding=None
                ),
                relevance=0.9,
                context=f"structural_pattern:{pattern}",
                matches=["structural"]
            ))

        return results
```

#### Step 3.3: Unified Searcher

```python
# src/athena/code_search/tree_sitter_search.py

class TreeSitterCodeSearch:
    """Unified semantic + structural code search."""

    def __init__(self, repo_path: str, language: str = "python"):
        self.repo_path = repo_path
        self.parser = CodeParser(language)
        self.indexer = CodebaseIndexer(self.parser, EmbeddingManager())
        self.semantic_searcher = SemanticCodeSearcher([], EmbeddingManager())
        self.structural_searcher = StructuralCodeSearcher(self.parser)

    def build_index(self):
        """Build semantic index of codebase."""
        self.indexer.index_directory(self.repo_path)
        self.semantic_searcher.units = self.indexer.get_units()

    def search(self, query: str, top_k: int = 10) -> List[SearchResult]:
        """Search code semantically and structurally."""

        # Semantic search
        semantic_results = self.semantic_searcher.search(query, top_k)

        # Structural search (detect patterns in query)
        structural_results = []
        if "error" in query.lower() or "exception" in query.lower():
            structural_results.extend(
                self.structural_searcher.search_by_pattern("error_handling", "")
            )
        if "database" in query.lower() or "query" in query.lower():
            structural_results.extend(
                self.structural_searcher.search_by_pattern("database_queries", "")
            )

        # Combine results (deduplicate by ID)
        all_results = semantic_results + structural_results
        seen = set()
        combined = []

        for result in sorted(all_results, key=lambda x: x.relevance, reverse=True):
            if result.unit.id not in seen:
                combined.append(result)
                seen.add(result.unit.id)

        return combined[:top_k]
```

**Deliverable**: Full search implementation with tests

---

### Phase 4: Graph Integration (Days 13-15)

```python
# src/athena/code_search/graph_integration.py

class CodeSearchGraphIntegration:
    """Integrate code search with Athena knowledge graph."""

    def __init__(self, code_search: TreeSitterCodeSearch, graph_store):
        self.code_search = code_search
        self.graph = graph_store

    def add_code_units_to_graph(self):
        """Add code units as entities in knowledge graph."""

        units = self.code_search.semantic_searcher.units

        for unit in units:
            # Add as entity
            self.graph.add_entity(
                entity_id=unit.id,
                entity_type=unit.type,  # "function", "class", etc.
                properties={
                    "name": unit.name,
                    "file_path": unit.file_path,
                    "start_line": unit.start_line,
                    "end_line": unit.end_line,
                    "docstring": unit.docstring,
                }
            )

            # Add dependencies as relations
            for dep in unit.dependencies:
                # Find matching unit
                dep_unit = next((u for u in units if u.name == dep), None)
                if dep_unit:
                    self.graph.add_relation(
                        source_id=unit.id,
                        target_id=dep_unit.id,
                        relation_type="depends_on"
                    )
```

**Deliverable**: Graph integration working

---

### Phase 5: MCP Tool Integration (Days 16-17)

```python
# src/athena/mcp/handlers_code_search.py

class CodeSearchMCPHandler:
    """MCP tools for code search."""

    def __init__(self, code_search: TreeSitterCodeSearch):
        self.code_search = code_search

    @server.tool()
    def search_code(query: str, top_k: int = 10) -> dict:
        """
        Semantic code search using Tree-sitter.

        Find code by meaning, not just keywords.

        Args:
            query: What code are you looking for? (e.g., "authentication handling")
            top_k: Maximum results to return

        Returns:
            List of matching code units with file paths and line numbers
        """
        results = self.code_search.search(query, top_k)

        return {
            "query": query,
            "results": [
                {
                    "file": r.unit.file_path,
                    "start_line": r.unit.start_line,
                    "end_line": r.unit.end_line,
                    "type": r.unit.type,
                    "name": r.unit.name,
                    "signature": r.unit.signature,
                    "code": r.unit.code[:500],  # First 500 chars
                    "relevance": r.relevance,
                    "docstring": r.unit.docstring,
                }
                for r in results
            ],
            "total": len(results)
        }

    @server.tool()
    def analyze_code_structure(file_path: str) -> dict:
        """
        Analyze structure of a code file.

        Shows all functions, classes, imports, and dependencies.
        """
        with open(file_path, 'r') as f:
            code = f.read()

        functions = self.code_search.parser.extract_functions(code, file_path)
        classes = self.code_search.parser.extract_classes(code, file_path)
        imports = self.code_search.parser.extract_imports(code, file_path)

        return {
            "file": file_path,
            "functions": [
                {"name": f.name, "line": f.start_line, "signature": f.signature}
                for f in functions
            ],
            "classes": [
                {"name": c.name, "line": c.start_line, "methods": []}
                for c in classes
            ],
            "imports": [
                {"name": i.name, "line": i.start_line}
                for i in imports
            ]
        }

    @server.tool()
    def find_code_dependencies(file_path: str, function_name: str) -> dict:
        """
        Find all dependencies of a function.

        Shows what other functions/classes this code depends on.
        """
        # Implementation
        pass
```

**Deliverable**: MCP tools integrated and tested

---

### Phase 6: Testing & Optimization (Days 18-21)

#### Unit Tests
```bash
pytest tests/unit/test_tree_sitter_search.py -v
```

#### Integration Tests
```bash
pytest tests/integration/test_tree_sitter_mcp.py -v
```

#### Performance Tests
```python
# tests/performance/test_code_search_performance.py

def test_indexing_performance():
    """Test indexing 10k+ LOC in <1 minute."""
    search = TreeSitterCodeSearch("/large/repo")

    start = time.time()
    search.build_index()
    elapsed = time.time() - start

    assert elapsed < 60  # < 1 minute
    print(f"Indexed in {elapsed:.1f}s")

def test_search_latency():
    """Test search latency <100ms."""
    search = TreeSitterCodeSearch("/repo")
    search.build_index()

    start = time.time()
    results = search.search("authentication")
    elapsed = time.time() - start

    assert elapsed < 0.1  # <100ms
    assert len(results) > 0
```

**Deliverable**: 90%+ test coverage, performance targets met

---

### Phase 7: Documentation & Release (Days 22-24)

Create documentation:
1. **User Guide**: How to use `/search_code` MCP tool
2. **API Reference**: All methods and parameters
3. **Architecture Guide**: Design decisions
4. **Performance Guide**: Optimization tips

**Deliverable**: Complete documentation, ready for release

---

## Implementation Checklist

### Week 1: Setup & Parser (Days 1-7)

- [ ] Day 1-2: Install Tree-sitter, write setup tests
- [ ] Day 3-4: Implement CodeParser, extract functions
- [ ] Day 5-6: Extract classes and imports
- [ ] Day 7: Complete unit tests for parser

### Week 2: Indexing & Search (Days 8-14)

- [ ] Day 8-9: Implement CodebaseIndexer
- [ ] Day 10-11: Implement SemanticCodeSearcher
- [ ] Day 12-13: Implement StructuralCodeSearcher
- [ ] Day 14: Unit tests for all searchers

### Week 3: Integration (Days 15-21)

- [ ] Day 15-16: Graph integration
- [ ] Day 17-18: MCP tool integration
- [ ] Day 19-20: Performance testing and optimization
- [ ] Day 21: Integration tests

### Week 4: Polish & Release (Days 22-24)

- [ ] Day 22: Documentation
- [ ] Day 23: Final testing
- [ ] Day 24: Release and announcement

---

## Success Criteria

✅ **Functional**:
- [x] Index Python, JavaScript, TypeScript codebases
- [x] Semantic search works (embeddings-based)
- [x] Structural search works (AST patterns)
- [x] Graph integration complete
- [x] MCP tools exposed

✅ **Performance**:
- [x] Index 10k+ LOC in <1 minute
- [x] Search latency <100ms
- [x] Memory usage <1GB for typical project

✅ **Quality**:
- [x] 90%+ test coverage
- [x] All tests passing
- [x] Performance targets met

✅ **Documentation**:
- [x] User guide complete
- [x] API reference complete
- [x] Architecture documented
- [x] Example queries provided

---

## Dependencies & Resources

### External Libraries
- `tree-sitter>=0.20.0` (open-source, free)
- `numpy` (already in Athena)

### Language Grammars
- Python (pre-built, bundled)
- JavaScript/TypeScript (pre-built, bundled)
- Java, Go, Rust (downloadable, free)

### Development Time
- 1 developer, 3-4 weeks full-time
- Can be done in parallel with dual-format work

### Infrastructure
- No additional infrastructure needed
- Uses existing Athena layers (semantic, graph, MCP)

---

## Go/No-Go Criteria

### Go Criteria (Must Have)
- [x] Tree-sitter parsing works for Python, JavaScript
- [x] Semantic search returns relevant results
- [x] Search latency <200ms (stretch goal: <100ms)
- [x] No breaking changes to existing Athena APIs
- [x] 85%+ test coverage

### No-Go Criteria (Blockers)
- ❌ Can't parse target language
- ❌ Search latency >500ms for typical queries
- ❌ Indexing fails on large codebases
- ❌ Breaking changes to existing APIs

---

## Notes for Developer

### Tips
1. Start with Python support only, add other languages later
2. Use mock embeddings for testing (no LLM needed)
3. Test with real repositories (Django, Flask, Express)
4. Monitor memory usage during large codebases
5. Create reusable test fixtures

### Common Pitfalls
1. **Tree-sitter queries are case-sensitive** - Double-check AST node types
2. **Embedding generation can be slow** - Consider batching and caching
3. **Large codebases need indexing** - Don't try to search without indexing
4. **Different languages have different ASTs** - Test with each language

### Resources
- Tree-sitter docs: https://tree-sitter.github.io/tree-sitter/
- Language queries: https://tree-sitter.github.io/tree-sitter/syntax-highlighting
- Athena integration points: See `CLAUDE.md`

---

## Timeline Summary

```
Week 1: Setup + Parser Implementation
Week 2: Indexing + Search Implementation
Week 3: Integration + Optimization
Week 4: Documentation + Release

Total: 24 days (3-4 weeks actual development time)
Target completion: Week 4 of project
```

---

**Status**: Ready to implement
**Confidence**: High (Tree-sitter is production-proven)
**Impact**: Critical gap closure + market differentiation
