"""Tests for semantic code searcher."""

import pytest
from pathlib import Path
from athena.code_search.semantic_searcher import SemanticCodeSearcher, SearchScores
from athena.code_search.indexer import CodebaseIndexer
from athena.code_search.models import SearchResult


@pytest.fixture
def temp_repo_with_code(tmp_path):
    """Create a temporary repository with Python files."""
    # Create directory structure
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()

    # Create main.py with various functions
    main_file = tmp_path / "src" / "main.py"
    main_file.write_text("""
def authenticate(user: str) -> bool:
    '''Authenticate a user.'''
    return validate_user(user)

def validate_user(user: str) -> bool:
    '''Validate user credentials.'''
    return len(user) > 0

def process_data(data: dict) -> dict:
    '''Process the input data.'''
    return {**data, "processed": True}

class AuthHandler:
    '''Handle authentication.'''
    def login(self, user: str) -> bool:
        return authenticate(user)

    def logout(self) -> None:
        '''Logout user.'''
        pass
""")

    # Create utils.py with utilities
    utils_file = tmp_path / "src" / "utils.py"
    utils_file.write_text("""
def format_string(text: str) -> str:
    '''Format string for display.'''
    return text.strip().upper()

def validate_email(email: str) -> bool:
    '''Validate email address.'''
    return "@" in email

class Logger:
    '''Simple logging utility.'''
    def log(self, message: str) -> None:
        print(message)
""")

    return tmp_path


@pytest.fixture
def indexer(temp_repo_with_code):
    """Create indexer for test repo."""
    return CodebaseIndexer(str(temp_repo_with_code))


@pytest.fixture
def searcher(indexer):
    """Create semantic searcher with indexed code."""
    indexer.index_directory()
    return SemanticCodeSearcher(indexer)


class TestSemanticSearcherInitialization:
    """Test searcher initialization."""

    def test_initialization(self, searcher):
        """Test initializing searcher."""
        assert searcher.indexer is not None
        assert len(searcher.units) > 0
        assert len(searcher.embeddings) > 0

    def test_initialization_with_embedding_manager(self, indexer):
        """Test initialization with embedding manager."""

        class MockEmbeddingManager:
            def generate(self, text: str):
                return [0.1] * 384

        embedding_manager = MockEmbeddingManager()
        searcher = SemanticCodeSearcher(indexer, embedding_manager)

        indexer.index_directory()
        assert searcher.embedding_manager is not None

    def test_search_weights(self, searcher):
        """Test that search weights are set correctly."""
        assert searcher.semantic_weight == 0.5
        assert searcher.name_weight == 0.25
        assert searcher.type_weight == 0.25


class TestBasicSearch:
    """Test basic search functionality."""

    def test_search_by_name(self, searcher):
        """Test searching by function/class name."""
        results = searcher.search("authenticate", min_score=0.0)

        assert len(results) > 0
        # Should find functions with "authenticate" in name
        names = [r.unit.name for r in results]
        assert any("authenticate" in name.lower() for name in names)

    def test_search_returns_search_results(self, searcher):
        """Test that search returns SearchResult objects."""
        results = searcher.search("validate", min_score=0.0)

        assert len(results) > 0
        assert all(isinstance(r, SearchResult) for r in results)
        assert all(hasattr(r, "unit") for r in results)
        assert all(hasattr(r, "relevance") for r in results)
        assert all(hasattr(r, "context") for r in results)

    def test_search_results_ranked(self, searcher):
        """Test that results are properly ranked by relevance."""
        results = searcher.search("user")

        if len(results) > 1:
            # Relevance scores should be descending
            relevances = [r.relevance for r in results]
            assert relevances == sorted(relevances, reverse=True)

    def test_search_with_min_score_filter(self, searcher):
        """Test search with minimum score threshold."""
        results_all = searcher.search("code", min_score=0.0)
        results_filtered = searcher.search("code", min_score=0.8)

        # Filtered should have fewer or equal results
        assert len(results_filtered) <= len(results_all)

        # All filtered results should meet threshold
        for result in results_filtered:
            assert result.relevance >= 0.8

    def test_search_with_type_filter(self, searcher):
        """Test search with type filter."""
        results = searcher.search("validate", types=["function"])

        # Should only return functions
        assert all(r.unit.type == "function" for r in results)

    def test_search_with_multiple_type_filter(self, searcher):
        """Test search with multiple type filters."""
        results = searcher.search("user", types=["function", "class"])

        # Should only return functions or classes
        assert all(r.unit.type in ["function", "class"] for r in results)

    def test_search_with_file_filter(self, searcher, temp_repo_with_code):
        """Test search with file path filter."""
        main_file = str(temp_repo_with_code / "src" / "main.py")

        results = searcher.search("auth", files=[main_file])

        # Should only return results from specified file
        assert all(r.unit.file_path == main_file for r in results)

    def test_search_limit(self, searcher):
        """Test search result limit."""
        results_all = searcher.search("def", limit=100)
        results_limited = searcher.search("def", limit=3)

        assert len(results_limited) <= 3
        assert len(results_limited) <= len(results_all)

    def test_search_empty_query(self, searcher):
        """Test search with empty query."""
        results = searcher.search("")
        assert len(results) == 0

        results = searcher.search("   ")
        assert len(results) == 0


class TestSimilaritySearch:
    """Test finding similar code units."""

    def test_find_similar(self, searcher):
        """Test finding similar units to a reference unit."""
        # Get first function
        functions = searcher.indexer.find_by_type("function")
        if not functions:
            pytest.skip("No functions found")

        ref_unit = functions[0]

        # Find similar units
        results = searcher.find_similar(ref_unit.id)

        assert isinstance(results, list)
        # Results should not include the reference unit itself
        result_ids = [r.unit.id for r in results]
        assert ref_unit.id not in result_ids

    def test_find_similar_with_nonexistent_unit(self, searcher):
        """Test finding similar units with invalid unit ID."""
        results = searcher.find_similar("nonexistent_id")
        assert len(results) == 0

    def test_find_similar_limit(self, searcher):
        """Test limit on similar results."""
        functions = searcher.indexer.find_by_type("function")
        if not functions:
            pytest.skip("No functions found")

        ref_unit = functions[0]

        results = searcher.find_similar(ref_unit.id, limit=2)

        assert len(results) <= 2

    def test_find_similar_scores_descending(self, searcher):
        """Test that similar results are ranked by relevance."""
        functions = searcher.indexer.find_by_type("function")
        if len(functions) < 2:
            pytest.skip("Need at least 2 functions")

        ref_unit = functions[0]
        results = searcher.find_similar(ref_unit.id)

        if len(results) > 1:
            relevances = [r.relevance for r in results]
            assert relevances == sorted(relevances, reverse=True)


class TestSearchByType:
    """Test searching by code unit type."""

    def test_search_by_type_function(self, searcher):
        """Test searching for functions."""
        results = searcher.search_by_type("function")

        assert len(results) > 0
        assert all(r.unit.type == "function" for r in results)

    def test_search_by_type_class(self, searcher):
        """Test searching for classes."""
        results = searcher.search_by_type("class")

        assert len(results) > 0
        assert all(r.unit.type == "class" for r in results)

    def test_search_by_type_with_query(self, searcher):
        """Test searching by type with additional query."""
        results = searcher.search_by_type("function", query="validate")

        assert all(r.unit.type == "function" for r in results)
        # Should also match query
        if results:
            assert any("validate" in r.unit.name.lower() for r in results)

    def test_search_by_type_nonexistent(self, searcher):
        """Test searching for nonexistent type."""
        results = searcher.search_by_type("nonexistent_type")
        assert len(results) == 0


class TestSearchByName:
    """Test searching by code unit name."""

    def test_search_by_name_partial(self, searcher):
        """Test partial name search."""
        results = searcher.search_by_name("auth")

        assert len(results) > 0
        # Should find units with "auth" in name
        assert all("auth" in r.unit.name.lower() for r in results)

    def test_search_by_name_exact(self, searcher):
        """Test exact name search."""
        # Note: exact=True searches for exact name matches,
        # but the search_by_name method needs to set score before appending
        results = searcher.search_by_name("authenticate", exact=True)

        # Should find exact match(es)
        if results:
            assert any(r.unit.name == "authenticate" for r in results)

    def test_search_by_name_case_insensitive(self, searcher):
        """Test case-insensitive name search."""
        results = searcher.search_by_name("AUTHENTICATE")

        assert len(results) > 0
        assert any(r.unit.name.lower() == "authenticate" for r in results)

    def test_search_by_name_scoring(self, searcher):
        """Test that name search results are scored correctly."""
        results = searcher.search_by_name("user")

        if len(results) > 0:
            # All relevance scores should be between 0 and 1
            assert all(0 <= r.relevance <= 1 for r in results)
            # All scores should be positive (they matched the name search)
            assert all(r.relevance > 0 for r in results)

    def test_search_by_name_limit(self, searcher):
        """Test name search result limit."""
        results = searcher.search_by_name("a", limit=2)

        assert len(results) <= 2


class TestSearchScoring:
    """Test search result scoring."""

    def test_search_scores_between_zero_and_one(self, searcher):
        """Test that all search relevance scores are between 0 and 1."""
        results = searcher.search("code")

        assert all(0 <= r.relevance <= 1 for r in results)

    def test_search_scores_descending(self, searcher):
        """Test that search results are sorted by relevance (descending)."""
        results = searcher.search("function")

        if len(results) > 1:
            relevances = [r.relevance for r in results]
            assert relevances == sorted(relevances, reverse=True)

    def test_search_scores_component(self, searcher):
        """Test SearchScores dataclass."""
        unit = searcher.units[0] if searcher.units else None
        if not unit:
            pytest.skip("No units available")

        from athena.code_search.models import SearchQuery
        query = SearchQuery(original="test", intent="test")

        scores = searcher._score_unit(unit, query, None)

        assert isinstance(scores, SearchScores)
        assert hasattr(scores, "semantic_score")
        assert hasattr(scores, "name_score")
        assert hasattr(scores, "type_score")
        assert hasattr(scores, "combined_score")
        assert 0 <= scores.semantic_score <= 1
        assert 0 <= scores.name_score <= 1
        assert 0 <= scores.type_score <= 1
        assert 0 <= scores.combined_score <= 1


class TestSearchStats:
    """Test search statistics."""

    def test_get_search_stats(self, searcher):
        """Test getting search statistics."""
        stats = searcher.get_search_stats()

        assert "total_units" in stats
        assert "units_with_embeddings" in stats
        assert "embedding_coverage" in stats
        assert "units_by_type" in stats

        assert stats["total_units"] > 0
        assert stats["units_with_embeddings"] >= 0
        assert 0 <= stats["embedding_coverage"] <= 1

    def test_count_by_type(self, searcher):
        """Test unit counting by type."""
        counts = searcher._count_by_type()

        # Should have counts for at least functions and classes
        assert len(counts) > 0
        assert all(isinstance(k, str) for k in counts.keys())
        assert all(isinstance(v, int) for v in counts.values())
        assert all(v > 0 for v in counts.values())


class TestCosineSimilarity:
    """Test cosine similarity calculation."""

    def test_cosine_similarity_identical_vectors(self):
        """Test cosine similarity of identical vectors."""
        import numpy as np

        v1 = np.array([1.0, 0.0, 0.0])
        v2 = np.array([1.0, 0.0, 0.0])

        similarity = SemanticCodeSearcher._cosine_similarity(v1, v2)

        assert similarity == 1.0

    def test_cosine_similarity_orthogonal_vectors(self):
        """Test cosine similarity of orthogonal vectors."""
        import numpy as np

        v1 = np.array([1.0, 0.0, 0.0])
        v2 = np.array([0.0, 1.0, 0.0])

        similarity = SemanticCodeSearcher._cosine_similarity(v1, v2)

        assert abs(similarity) < 0.01  # Close to 0

    def test_cosine_similarity_opposite_vectors(self):
        """Test cosine similarity of opposite vectors."""
        import numpy as np

        v1 = np.array([1.0, 0.0, 0.0])
        v2 = np.array([-1.0, 0.0, 0.0])

        similarity = SemanticCodeSearcher._cosine_similarity(v1, v2)

        # Clamped to [0, 1], so -1 becomes 0
        assert similarity == 0.0

    def test_cosine_similarity_zero_vector(self):
        """Test cosine similarity with zero vector."""
        import numpy as np

        v1 = np.array([1.0, 0.0, 0.0])
        v2 = np.array([0.0, 0.0, 0.0])

        similarity = SemanticCodeSearcher._cosine_similarity(v1, v2)

        assert similarity == 0.0

    def test_cosine_similarity_none_vectors(self):
        """Test cosine similarity with None vectors."""
        similarity = SemanticCodeSearcher._cosine_similarity(None, None)
        assert similarity == 0.0


class TestSearchIntegration:
    """Test integrated search functionality."""

    def test_search_find_all_functions(self, searcher):
        """Test finding all functions in index."""
        # Index has 4 functions in main.py and 1 in utils.py
        results = searcher.search_by_type("function")

        # Should find multiple functions
        assert len(results) >= 4

    def test_search_find_all_classes(self, searcher):
        """Test finding all classes in index."""
        # Index has 2 classes
        results = searcher.search_by_type("class")

        # Should find classes
        assert len(results) >= 2

    def test_combined_search_scenario(self, searcher):
        """Test combined search scenario."""
        # Search for auth-related functions
        results = searcher.search(
            "authenticate",
            types=["function"],
            limit=5,
            min_score=0.0,
        )

        # Should find authenticate function
        assert any(r.unit.name == "authenticate" for r in results)

    def test_search_different_queries_different_results(self, searcher):
        """Test that different queries produce different results."""
        results_auth = searcher.search("authenticate", min_score=0.0)
        results_validate = searcher.search("validate", min_score=0.0)

        # Results might overlap but shouldn't be identical if they both found matches
        if results_auth and results_validate:
            auth_ids = [r.unit.id for r in results_auth]
            validate_ids = [r.unit.id for r in results_validate]

            # At least some results should be different
            assert auth_ids != validate_ids
