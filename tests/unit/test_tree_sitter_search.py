"""Tests for Tree-sitter code search implementation."""

import pytest
from pathlib import Path
from athena.code_search.tree_sitter_search import TreeSitterCodeSearch


@pytest.fixture
def temp_repo(tmp_path):
    """Create temporary repository for testing."""
    # Create a simple Python file
    py_file = tmp_path / "example.py"
    py_file.write_text("""
def authenticate(user: str) -> bool:
    '''Authenticate a user.'''
    return validate_user(user)

def validate_user(user: str) -> bool:
    '''Validate user credentials.'''
    return len(user) > 0

class AuthHandler:
    '''Handles authentication.'''
    def __init__(self):
        pass

    def login(self, user: str) -> bool:
        '''Log in a user.'''
        return authenticate(user)
""")

    return tmp_path


class TestTreeSitterCodeSearch:
    """Test TreeSitterCodeSearch class."""

    def test_initialization(self, temp_repo):
        """Test initializing TreeSitterCodeSearch."""
        search = TreeSitterCodeSearch(str(temp_repo))

        assert search.repo_path == temp_repo
        assert search.language == "python"
        assert not search.is_indexed

    def test_initialization_with_custom_language(self, temp_repo):
        """Test initialization with custom language."""
        search = TreeSitterCodeSearch(str(temp_repo), language="javascript")

        assert search.language == "javascript"

    def test_invalid_repo_path(self):
        """Test with invalid repository path."""
        search = TreeSitterCodeSearch("/nonexistent/path")

        with pytest.raises(ValueError):
            search.build_index()

    def test_search_without_index(self, temp_repo):
        """Test searching without building index first."""
        search = TreeSitterCodeSearch(str(temp_repo))

        with pytest.raises(RuntimeError):
            search.search("authentication")

    def test_index_building(self, temp_repo):
        """Test building index."""
        search = TreeSitterCodeSearch(str(temp_repo))

        assert not search.is_indexed
        search.build_index()
        assert search.is_indexed

    def test_index_stats(self, temp_repo):
        """Test getting index statistics."""
        search = TreeSitterCodeSearch(str(temp_repo))
        search.build_index()

        stats = search.index_stats

        assert stats["indexed"]
        assert stats["repo_path"] == str(temp_repo)
        assert stats["language"] == "python"

    def test_analyze_file(self, temp_repo):
        """Test analyzing a file."""
        search = TreeSitterCodeSearch(str(temp_repo))
        py_file = temp_repo / "example.py"

        result = search.analyze_file(str(py_file))

        assert result["file"] == str(py_file)
        assert "functions" in result
        assert "classes" in result
        assert "imports" in result

    def test_analyze_nonexistent_file(self, temp_repo):
        """Test analyzing nonexistent file."""
        search = TreeSitterCodeSearch(str(temp_repo))

        with pytest.raises(FileNotFoundError):
            search.analyze_file("/nonexistent/file.py")

    def test_find_dependencies(self, temp_repo):
        """Test finding dependencies."""
        search = TreeSitterCodeSearch(str(temp_repo))
        search.build_index()  # Must build index first
        py_file = temp_repo / "example.py"

        result = search.find_dependencies(str(py_file), "authenticate")

        assert result["entity"] == "authenticate"
        assert result["file"] == str(py_file)
        assert "direct_dependencies" in result
        assert "transitive_dependencies" in result
        assert "dependents" in result

    def test_search_basic(self, temp_repo):
        """Test basic search functionality."""
        search = TreeSitterCodeSearch(str(temp_repo))
        search.build_index()

        # Search should work without errors (returns empty list in Phase 1)
        results = search.search("authentication")

        assert isinstance(results, list)

    def test_search_with_top_k(self, temp_repo):
        """Test search with custom top_k parameter."""
        search = TreeSitterCodeSearch(str(temp_repo))
        search.build_index()

        results = search.search("auth", top_k=5)

        assert len(results) <= 5

    def test_multiple_searches(self, temp_repo):
        """Test multiple searches on same index."""
        search = TreeSitterCodeSearch(str(temp_repo))
        search.build_index()

        results1 = search.search("authenticate")
        results2 = search.search("validate")
        results3 = search.search("class")

        # All should work without errors
        assert isinstance(results1, list)
        assert isinstance(results2, list)
        assert isinstance(results3, list)


class TestTreeSitterSearchWithEmbeddings:
    """Test Tree-sitter search with embedding integration."""

    def test_with_embedding_manager(self, temp_repo):
        """Test TreeSitterCodeSearch with embedding manager."""
        # Mock embedding manager
        class MockEmbeddingManager:
            def generate(self, text: str):
                # Return simple mock embedding
                return [0.1] * 384  # Standard embedding size

        embed_manager = MockEmbeddingManager()
        search = TreeSitterCodeSearch(str(temp_repo), embed_manager=embed_manager)

        assert search.embed_manager is not None

    def test_with_graph_store(self, temp_repo):
        """Test TreeSitterCodeSearch with graph store."""
        # Mock graph store
        class MockGraphStore:
            def add_entity(self, entity_id, entity_type, properties):
                pass

            def add_relation(self, source_id, target_id, relation_type):
                pass

        graph_store = MockGraphStore()
        search = TreeSitterCodeSearch(str(temp_repo), graph_store=graph_store)

        assert search.graph_store is not None


class TestTreeSitterSearchLanguages:
    """Test multiple language support."""

    @pytest.mark.parametrize("language", ["python", "javascript", "typescript", "java", "go"])
    def test_language_support(self, temp_repo, language):
        """Test different languages."""
        search = TreeSitterCodeSearch(str(temp_repo), language=language)

        assert search.language == language

    def test_build_index_with_multiple_languages(self, temp_repo):
        """Test building index with multiple languages."""
        search = TreeSitterCodeSearch(str(temp_repo))

        # Should not raise error
        search.build_index(languages=["python", "javascript", "typescript"])
        assert search.is_indexed
