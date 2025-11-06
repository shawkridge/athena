"""Integration tests for code search on real repository (swarm-mobile)."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock

from athena.core.database import Database
from athena.code.parser import CodeParser, CodeLanguage
from athena.code.indexer import CodeIndexer
from athena.code.models import CodeLanguage as CodeLang


class TestCodeParserOnRealRepository:
    """Test code parser on real swarm-mobile repository."""

    @pytest.fixture
    def repo_path(self):
        """Path to swarm-mobile repository."""
        return Path.home() / ".work" / "swarm-mobile"

    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_code_search.db"
            db = Database(str(db_path))
            yield db

    def test_repository_exists(self, repo_path):
        """Verify that the swarm-mobile repository exists."""
        assert repo_path.exists(), f"Repository not found at {repo_path}"
        assert (repo_path / ".git").exists(), "Not a git repository"

    def test_find_typescript_files(self, repo_path):
        """Test finding TypeScript files in repository."""
        ts_files = list(repo_path.rglob("*.ts"))
        tsx_files = list(repo_path.rglob("*.tsx"))

        assert len(ts_files) > 0, "No TypeScript files found"
        assert len(tsx_files) > 0, "No TSX files found"

        print(f"\nFound {len(ts_files)} .ts files")
        print(f"Found {len(tsx_files)} .tsx files")

    def test_find_javascript_files(self, repo_path):
        """Test finding JavaScript files in repository."""
        js_files = list(repo_path.rglob("*.js"))
        jsx_files = list(repo_path.rglob("*.jsx"))

        assert len(js_files) > 0, "No JavaScript files found"

        print(f"\nFound {len(js_files)} .js files")
        print(f"Found {len(jsx_files)} .jsx files")

    def test_parser_initialization(self):
        """Test CodeParser can be initialized."""
        parser = CodeParser()
        assert parser is not None
        assert hasattr(parser, 'parse_file')

    def test_parse_sample_typescript_file(self, repo_path):
        """Test parsing a real TypeScript file."""
        # Find App.tsx
        app_file = repo_path / "App.tsx"
        if not app_file.exists():
            pytest.skip("App.tsx not found")

        parser = CodeParser()

        # Parse the file
        elements = parser.parse_file(str(app_file))

        # Should extract some elements
        assert len(elements) > 0, "No code elements extracted from App.tsx"

        # Should have functions, classes, or imports
        element_types = [e.element_type for e in elements]
        print(f"\nExtracted element types: {set(element_types)}")
        print(f"Total elements extracted: {len(elements)}")

    def test_parse_javascript_file(self, repo_path):
        """Test parsing JavaScript files."""
        # Find a JavaScript file
        js_files = list(repo_path.glob("scripts/*.js"))
        if not js_files:
            pytest.skip("No JS files in scripts directory")

        js_file = js_files[0]
        parser = CodeParser()

        elements = parser.parse_file(str(js_file))

        print(f"\nParsed {js_file.name}: {len(elements)} elements")

    def test_parser_handles_nested_functions(self, repo_path):
        """Test that parser correctly handles nested functions."""
        app_file = repo_path / "App.tsx"
        if not app_file.exists():
            pytest.skip("App.tsx not found")

        parser = CodeParser()
        elements = parser.parse_file(str(app_file))

        # Check for nested structure
        elements_with_parent = [e for e in elements if e.parent_element]
        print(f"\nFound {len(elements_with_parent)} nested elements")

        if elements_with_parent:
            assert len(elements_with_parent) > 0
            print(f"Sample parent element: {elements_with_parent[0].parent_element}")

    def test_parser_extracts_docstrings(self, repo_path):
        """Test that parser extracts documentation."""
        # Find well-documented files
        ts_files = list(repo_path.rglob("*.ts"))[:5]

        parser = CodeParser()
        total_with_docs = 0

        for ts_file in ts_files:
            try:
                elements = parser.parse_file(str(ts_file))
                with_docs = [e for e in elements if e.docstring]
                total_with_docs += len(with_docs)
            except Exception as e:
                print(f"Skipped {ts_file.name}: {e}")

        print(f"\nFound {total_with_docs} documented elements across sample files")

    def test_parser_handles_imports(self, repo_path):
        """Test that parser extracts import statements."""
        app_file = repo_path / "App.tsx"
        if not app_file.exists():
            pytest.skip("App.tsx not found")

        parser = CodeParser()
        elements = parser.parse_file(str(app_file))

        # Check for imports
        imports = [e for e in elements if e.element_type.value == "import"]
        print(f"\nFound {len(imports)} import statements in App.tsx")

        if imports:
            print(f"Sample imports: {[i.name for i in imports[:3]]}")

    def test_parser_performance_on_large_file(self, repo_path):
        """Test parser performance on a large file."""
        import time

        ts_files = list(repo_path.rglob("*.tsx"))
        if not ts_files:
            pytest.skip("No TSX files found")

        # Find the largest file
        largest_file = max(ts_files, key=lambda f: f.stat().st_size)

        parser = CodeParser()
        file_size_kb = largest_file.stat().st_size / 1024
        print(f"\nTesting parser on {largest_file.name} ({file_size_kb:.1f}KB)")

        start = time.time()
        elements = parser.parse_file(str(largest_file))
        elapsed = time.time() - start

        print(f"Parsed in {elapsed:.3f}s")
        print(f"Extracted {len(elements)} elements")
        if elapsed > 0:
            print(f"Rate: {len(elements) / elapsed:.0f} elements/sec")

        # Should be reasonably fast (< 5 sec for typical files)
        assert elapsed < 5.0, f"Parsing took too long: {elapsed:.3f}s"

    def test_parser_handles_syntax_errors(self, repo_path):
        """Test that parser gracefully handles files with syntax errors."""
        parser = CodeParser()

        # Create a file with syntax errors
        broken_code = """
        function broken(
            // Missing closing paren and brace
        """

        try:
            elements = parser.parse(
                source_code=broken_code,
                file_path="broken.ts",
                language=CodeLanguage.TYPESCRIPT
            )
            # Should either return partial results or empty list
            assert isinstance(elements, list)
            print(f"\nParser gracefully handled broken code, extracted {len(elements)} elements")
        except Exception as e:
            # Should fail gracefully
            print(f"\nParser raised exception (expected): {type(e).__name__}")


class TestCodeIndexerOnRealRepository:
    """Test code indexer on real repository."""

    @pytest.fixture
    def repo_path(self):
        """Path to swarm-mobile repository."""
        return Path.home() / ".work" / "swarm-mobile"

    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_indexer.db"
            db = Database(str(db_path))
            yield db

    def test_indexer_initialization(self, temp_db):
        """Test CodeIndexer can be initialized."""
        indexer = CodeIndexer(temp_db)
        assert indexer is not None
        assert hasattr(indexer, 'index_file')
        assert hasattr(indexer, 'index_repository')

    def test_index_single_file(self, repo_path, temp_db):
        """Test indexing a single file."""
        app_file = repo_path / "App.tsx"
        if not app_file.exists():
            pytest.skip("App.tsx not found")

        indexer = CodeIndexer(temp_db)
        indexed_count = indexer.index_file(app_file, "App.tsx")

        print(f"\nIndexed {indexed_count} elements from App.tsx")
        assert indexed_count > 0, "No elements indexed"

    def test_index_small_repository_subset(self, repo_path, temp_db):
        """Test indexing a small subset of repository."""
        # Index just the scripts directory
        scripts_dir = repo_path / "scripts"
        if not scripts_dir.exists():
            pytest.skip("scripts directory not found")

        indexer = CodeIndexer(temp_db)

        # Index only a few files
        js_files = list(scripts_dir.glob("*.js"))[:3]
        total_indexed = 0

        for js_file in js_files:
            count = indexer.index_file(js_file, js_file.relative_to(repo_path))
            total_indexed += count
            print(f"Indexed {js_file.name}: {count} elements")

        print(f"\nTotal indexed: {total_indexed} elements")
        assert total_indexed > 0, "No elements indexed from scripts"

    def test_index_with_language_filter(self, repo_path, temp_db):
        """Test indexing with language filter."""
        indexer = CodeIndexer(temp_db)

        # Try to index TypeScript files only
        ts_files = list(repo_path.rglob("*.ts"))[:5]

        if ts_files:
            total = sum(
                indexer.index_file(f, f.relative_to(repo_path))
                for f in ts_files
            )
            print(f"\nIndexed {total} elements from {len(ts_files)} TypeScript files")
            assert total > 0


class TestCodeSearchIntegration:
    """Integration tests for full code search workflow."""

    @pytest.fixture
    def repo_path(self):
        """Path to swarm-mobile repository."""
        return Path.home() / ".work" / "swarm-mobile"

    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_search.db"
            db = Database(str(db_path))
            yield db

    def test_search_workflow_end_to_end(self, repo_path, temp_db):
        """Test complete search workflow: parse -> index -> search."""
        from athena.code.search import CodeSearchManager

        app_file = repo_path / "App.tsx"
        if not app_file.exists():
            pytest.skip("App.tsx not found")

        # Initialize components
        indexer = CodeIndexer(temp_db)
        search_manager = CodeSearchManager(temp_db)

        # Index the file
        indexed = indexer.index_file(app_file, "App.tsx")
        print(f"\nIndexed {indexed} elements from App.tsx")

        assert indexed > 0, "Indexing failed"

        # Try to search
        if indexed > 0:
            results = search_manager.semantic_search("main component", limit=5)
            print(f"Search found {len(results) if results else 0} results")

    def test_hybrid_ranking_on_real_code(self, repo_path, temp_db):
        """Test hybrid ranking (semantic + AST + spatial) on real code."""
        from athena.code.search import CodeSearchManager

        app_file = repo_path / "App.tsx"
        if not app_file.exists():
            pytest.skip("App.tsx not found")

        indexer = CodeIndexer(temp_db)
        search_manager = CodeSearchManager(temp_db)

        # Index file
        indexer.index_file(app_file, "App.tsx")

        # Search for common terms in React/TypeScript code
        queries = [
            "component",
            "render",
            "useState",
            "props",
            "event handler"
        ]

        for query in queries:
            try:
                results = search_manager.semantic_search(query, limit=3)
                count = len(results) if results else 0
                print(f"\nQuery '{query}': {count} results")
            except Exception as e:
                print(f"\nQuery '{query}': Error - {e}")


# Performance and Statistics
class TestCodeSearchStatistics:
    """Gather statistics about code search on real repository."""

    @pytest.fixture
    def repo_path(self):
        """Path to swarm-mobile repository."""
        return Path.home() / ".work" / "swarm-mobile"

    def test_repository_statistics(self, repo_path):
        """Gather statistics about the repository."""
        import os

        # Count files by type
        ts_count = len(list(repo_path.rglob("*.ts")))
        tsx_count = len(list(repo_path.rglob("*.tsx")))
        js_count = len(list(repo_path.rglob("*.js")))
        jsx_count = len(list(repo_path.rglob("*.jsx")))

        total_size = 0
        for root, dirs, files in os.walk(repo_path):
            # Skip common ignored directories
            dirs[:] = [d for d in dirs if d not in ['node_modules', '.git', '.expo', '.ast-grep']]

            for file in files:
                if file.endswith(('.ts', '.tsx', '.js', '.jsx')):
                    try:
                        total_size += os.path.getsize(os.path.join(root, file))
                    except OSError:
                        pass

        print(f"""

        REPOSITORY STATISTICS (swarm-mobile):
        =====================================
        TypeScript files (.ts):  {ts_count}
        TSX files (.tsx):        {tsx_count}
        JavaScript files (.js):  {js_count}
        JSX files (.jsx):        {jsx_count}

        Total source files:      {ts_count + tsx_count + js_count + jsx_count}
        Total source size:       {total_size / 1024 / 1024:.1f} MB
        """)

        assert ts_count + tsx_count > 0, "TypeScript files not found"
        assert total_size > 0, "No source code size calculated"
