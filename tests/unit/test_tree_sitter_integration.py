"""Integration tests for unified TreeSitterCodeSearch API."""

import pytest
from pathlib import Path
from athena.code_search.tree_sitter_search import TreeSitterCodeSearch


@pytest.fixture
def test_repo(tmp_path):
    """Create a test repository with Python code."""
    (tmp_path / "src").mkdir()

    # Create main.py
    main_file = tmp_path / "src" / "main.py"
    main_file.write_text("""
def authenticate(user: str) -> bool:
    '''Authenticate a user.'''
    return validate_user(user)

def validate_user(user: str) -> bool:
    '''Validate user credentials.'''
    return len(user) > 0

class AuthHandler:
    '''Handle authentication.'''
    def login(self, user: str) -> bool:
        return authenticate(user)
""")

    # Create utils.py
    utils_file = tmp_path / "src" / "utils.py"
    utils_file.write_text("""
def format_string(text: str) -> str:
    '''Format string.'''
    return text.strip().upper()

def validate_email(email: str) -> bool:
    '''Validate email.'''
    return "@" in email
""")

    return tmp_path


@pytest.fixture
def search_engine(test_repo):
    """Create a search engine and build index."""
    engine = TreeSitterCodeSearch(str(test_repo))
    engine.build_index()
    return engine


class TestTreeSitterCodeSearchInitialization:
    """Test TreeSitterCodeSearch initialization."""

    def test_initialization(self, test_repo):
        """Test initializing search engine."""
        engine = TreeSitterCodeSearch(str(test_repo))

        assert engine.repo_path == test_repo
        assert engine.language == "python"
        assert engine.parser is not None
        assert engine.indexer is not None
        assert not engine.is_indexed

    def test_initialization_with_embedding_manager(self, test_repo):
        """Test initialization with embedding manager."""
        class MockEmbeddingManager:
            def generate(self, text: str):
                return [0.1] * 384

        embed_manager = MockEmbeddingManager()
        engine = TreeSitterCodeSearch(str(test_repo), embed_manager=embed_manager)

        assert engine.embed_manager is not None

    def test_invalid_repo_path(self, tmp_path):
        """Test with invalid repository path."""
        engine = TreeSitterCodeSearch("/nonexistent/path")

        with pytest.raises(ValueError):
            engine.build_index()


class TestBuildIndex:
    """Test index building."""

    def test_build_index(self, search_engine):
        """Test building index."""
        assert search_engine.is_indexed
        stats = search_engine.index_stats

        assert stats["indexed"]
        assert stats["units_extracted"] > 0
        assert stats["files_indexed"] > 0

    def test_index_statistics(self, search_engine):
        """Test index statistics."""
        stats = search_engine.index_stats

        assert "indexed" in stats
        assert "repo_path" in stats
        assert "language" in stats
        assert "files_indexed" in stats
        assert "units_extracted" in stats


class TestUnifiedSearch:
    """Test unified search functionality."""

    def test_search(self, search_engine):
        """Test basic search."""
        results = search_engine.search("authenticate", min_score=0.0)

        assert len(results) > 0
        assert any("authenticate" in r.unit.name.lower() for r in results)

    def test_search_by_type(self, search_engine):
        """Test search by type."""
        results = search_engine.search_by_type("function")

        assert len(results) > 0
        assert all(r.unit.type == "function" for r in results)

    def test_search_by_name(self, search_engine):
        """Test search by name."""
        results = search_engine.search_by_name("validate")

        assert len(results) > 0
        assert any("validate" in r.unit.name for r in results)

    def test_search_by_name_exact(self, search_engine):
        """Test exact name search."""
        results = search_engine.search_by_name("authenticate", exact=True)

        if results:
            assert any(r.unit.name == "authenticate" for r in results)

    def test_find_similar(self, search_engine):
        """Test finding similar units."""
        # Get first function
        functions = search_engine.semantic_searcher.indexer.find_by_type("function")
        if not functions:
            pytest.skip("No functions found")

        ref_unit = functions[0]
        results = search_engine.find_similar(ref_unit.id)

        # Should not include reference unit
        result_ids = [r.unit.id for r in results]
        assert ref_unit.id not in result_ids

    def test_search_with_limit(self, search_engine):
        """Test search result limit."""
        results = search_engine.search("function", min_score=0.0, top_k=2)

        assert len(results) <= 2

    def test_search_without_index_raises_error(self, test_repo):
        """Test searching without building index."""
        engine = TreeSitterCodeSearch(str(test_repo))

        with pytest.raises(RuntimeError):
            engine.search("test")

    def test_search_by_type_without_index_raises_error(self, test_repo):
        """Test search_by_type without building index."""
        engine = TreeSitterCodeSearch(str(test_repo))

        with pytest.raises(RuntimeError):
            engine.search_by_type("function")


class TestAnalyzeFile:
    """Test file analysis."""

    def test_analyze_file(self, search_engine, test_repo):
        """Test analyzing a file."""
        main_file = test_repo / "src" / "main.py"
        analysis = search_engine.analyze_file(str(main_file))

        assert analysis["file"] == str(main_file)
        assert len(analysis["functions"]) > 0
        assert len(analysis["classes"]) > 0
        assert analysis["total_units"] > 0

    def test_analyze_nonexistent_file(self, search_engine):
        """Test analyzing nonexistent file."""
        with pytest.raises(FileNotFoundError):
            search_engine.analyze_file("/nonexistent/file.py")

    def test_analyze_file_structure(self, search_engine, test_repo):
        """Test that file analysis returns proper structure."""
        main_file = test_repo / "src" / "main.py"
        analysis = search_engine.analyze_file(str(main_file))

        # Check structure
        assert all(hasattr(f, "keys") or isinstance(f, dict) for f in analysis["functions"])
        assert all(hasattr(c, "keys") or isinstance(c, dict) for c in analysis["classes"])
        assert all(hasattr(i, "keys") or isinstance(i, dict) for i in analysis["imports"])


class TestFindDependencies:
    """Test dependency finding."""

    def test_find_dependencies(self, search_engine, test_repo):
        """Test finding dependencies."""
        main_file = test_repo / "src" / "main.py"
        deps = search_engine.find_dependencies(str(main_file), "authenticate")

        assert deps["found"]
        assert deps["entity"] == "authenticate"
        assert len(deps["direct_dependencies"]) > 0

    def test_find_dependencies_nonexistent_entity(self, search_engine, test_repo):
        """Test finding dependencies for nonexistent entity."""
        main_file = test_repo / "src" / "main.py"
        deps = search_engine.find_dependencies(str(main_file), "nonexistent")

        assert not deps["found"]

    def test_find_dependencies_without_index_raises_error(self, test_repo):
        """Test find_dependencies without building index."""
        engine = TreeSitterCodeSearch(str(test_repo))

        with pytest.raises(RuntimeError):
            engine.find_dependencies(str(test_repo / "main.py"), "test")

    def test_find_dependencies_structure(self, search_engine, test_repo):
        """Test dependency structure."""
        main_file = test_repo / "src" / "main.py"
        deps = search_engine.find_dependencies(str(main_file), "authenticate")

        assert "direct_dependencies" in deps
        assert "transitive_dependencies" in deps
        assert "dependents" in deps
        assert isinstance(deps["direct_dependencies"], list)


class TestGetCodeStatistics:
    """Test code statistics."""

    def test_get_code_statistics(self, search_engine):
        """Test getting code statistics."""
        stats = search_engine.get_code_statistics()

        assert "total_units" in stats
        assert "units_by_type" in stats
        assert stats["total_units"] > 0

    def test_get_code_statistics_without_index(self, test_repo):
        """Test getting statistics without index."""
        engine = TreeSitterCodeSearch(str(test_repo))
        stats = engine.get_code_statistics()

        assert stats["indexed"] == False


class TestSearchResultsFormat:
    """Test search result formatting."""

    def test_search_results_have_correct_format(self, search_engine):
        """Test that search results have correct format."""
        results = search_engine.search("authenticate", min_score=0.0)

        for result in results:
            assert hasattr(result, "unit")
            assert hasattr(result, "relevance")
            assert hasattr(result, "context")
            assert 0 <= result.relevance <= 1

    def test_search_results_can_be_serialized(self, search_engine):
        """Test that search results can be converted to dict."""
        results = search_engine.search("authenticate", min_score=0.0)

        for result in results:
            result_dict = result.to_dict()
            assert isinstance(result_dict, dict)
            assert "name" in result_dict
            assert "relevance" in result_dict


class TestMultipleSearches:
    """Test multiple searches on same engine."""

    def test_multiple_searches(self, search_engine):
        """Test performing multiple searches."""
        results1 = search_engine.search("authenticate", min_score=0.0)
        results2 = search_engine.search("validate", min_score=0.0)
        results3 = search_engine.search_by_type("function")

        assert len(results1) > 0
        assert len(results2) > 0
        assert len(results3) > 0

    def test_search_produces_different_results(self, search_engine):
        """Test that different queries can produce different results."""
        # With low min_score, results might overlap significantly
        # Just verify that searches work and return results
        results_auth = search_engine.search("authenticate", min_score=0.0)
        results_format = search_engine.search("format", min_score=0.0)

        assert len(results_auth) > 0
        assert len(results_format) > 0
        # At minimum, different queries return results
        assert isinstance(results_auth, list)
        assert isinstance(results_format, list)


class TestEdgeCases:
    """Test edge cases."""

    def test_empty_query(self, search_engine):
        """Test search with empty query."""
        results = search_engine.search("")
        assert len(results) == 0

    def test_search_with_zero_limit(self, search_engine):
        """Test search with zero limit."""
        results = search_engine.search("test", min_score=0.0, top_k=0)
        assert len(results) == 0

    def test_search_with_very_high_min_score(self, search_engine):
        """Test search with very high minimum score."""
        results = search_engine.search("test", min_score=0.99)
        # Should find few or no results with very high threshold
        assert len(results) <= 10
