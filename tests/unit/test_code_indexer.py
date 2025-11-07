"""Tests for codebase indexer."""

import pytest
from pathlib import Path
from athena.code_search.indexer import CodebaseIndexer, IndexStatistics
from athena.code_search.models import CodeUnit


@pytest.fixture
def temp_repo_with_files(tmp_path):
    """Create a temporary repository with Python files."""
    # Create directory structure
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "__pycache__").mkdir()  # Should be skipped

    # Create Python files
    src_file = tmp_path / "src" / "main.py"
    src_file.write_text("""
def authenticate(user: str) -> bool:
    '''Authenticate a user.'''
    return validate_user(user)

def validate_user(user: str) -> bool:
    '''Validate user.'''
    return len(user) > 0

class AuthHandler:
    '''Handle authentication.'''
    def login(self, user: str) -> bool:
        return authenticate(user)
""")

    test_file = tmp_path / "tests" / "test_auth.py"
    test_file.write_text("""
def test_authenticate():
    assert authenticate("user")

def test_validate():
    assert validate_user("test")
""")

    skip_file = tmp_path / "__pycache__" / "cache.py"
    skip_file.write_text("# This should be skipped")

    return tmp_path


@pytest.fixture
def indexer(temp_repo_with_files):
    """Create indexer for test repo."""
    return CodebaseIndexer(str(temp_repo_with_files))


class TestIndexerInitialization:
    """Test indexer initialization."""

    def test_initialization(self, indexer):
        """Test initializing indexer."""
        assert indexer.repo_path is not None
        assert indexer.language == "python"
        assert len(indexer.units) == 0

    def test_initialization_with_custom_language(self, temp_repo_with_files):
        """Test initialization with custom language."""
        indexer = CodebaseIndexer(str(temp_repo_with_files), language="javascript")
        assert indexer.language == "javascript"

    def test_invalid_repo_path(self):
        """Test with invalid repository path."""
        indexer = CodebaseIndexer("/nonexistent/path")

        with pytest.raises(ValueError):
            indexer.index_directory()


class TestFileIndexing:
    """Test file indexing."""

    def test_index_single_file(self, temp_repo_with_files, indexer):
        """Test indexing a single file."""
        file_path = temp_repo_with_files / "src" / "main.py"

        units = indexer.index_file(str(file_path))

        assert len(units) > 0
        assert all(isinstance(u, CodeUnit) for u in units)

    def test_index_nonexistent_file(self, indexer):
        """Test indexing nonexistent file."""
        with pytest.raises(FileNotFoundError):
            indexer.index_file("/nonexistent/file.py")

    def test_index_directory(self, temp_repo_with_files, indexer):
        """Test indexing entire directory."""
        units = indexer.index_directory()

        # Should find units from both src and tests directories
        assert len(units) > 0

        # Should skip __pycache__
        cache_units = [u for u in units if "__pycache__" in u.file_path]
        assert len(cache_units) == 0

    def test_index_with_custom_extensions(self, temp_repo_with_files):
        """Test indexing with custom extensions."""
        indexer = CodebaseIndexer(str(temp_repo_with_files))

        # Index with specific extensions
        units = indexer.index_directory(extensions=[".py"])

        assert len(units) > 0

    def test_index_non_recursive(self, temp_repo_with_files):
        """Test non-recursive indexing."""
        indexer = CodebaseIndexer(str(temp_repo_with_files))

        # Non-recursive should only find top-level files
        units = indexer.index_directory(recursive=False)

        # Should be empty since .py files are in subdirectories
        assert len(units) == 0


class TestIndexStatistics:
    """Test indexing statistics."""

    def test_statistics_after_indexing(self, temp_repo_with_files, indexer):
        """Test statistics after indexing."""
        indexer.index_directory()

        stats = indexer.get_statistics()

        assert stats["files_scanned"] > 0
        assert stats["files_indexed"] > 0
        assert stats["units_extracted"] > 0
        assert stats["indexing_time"] >= 0

    def test_statistics_class(self, temp_repo_with_files, indexer):
        """Test IndexStatistics class."""
        indexer.index_directory()

        index_stats = IndexStatistics(indexer)

        assert index_stats.total_files > 0
        assert index_stats.indexed_files > 0
        assert index_stats.total_units > 0
        assert index_stats.indexing_time >= 0

    def test_statistics_dict_format(self, temp_repo_with_files, indexer):
        """Test statistics dictionary format."""
        indexer.index_directory()

        index_stats = IndexStatistics(indexer)
        stats_dict = index_stats.to_dict()

        assert "total_files" in stats_dict
        assert "indexed_files" in stats_dict
        assert "total_units" in stats_dict
        assert "errors" in stats_dict
        assert "indexing_time" in stats_dict
        assert "units_per_file" in stats_dict


class TestUnitRetrieval:
    """Test unit retrieval methods."""

    def test_get_units(self, temp_repo_with_files, indexer):
        """Test getting all units."""
        indexer.index_directory()

        units = indexer.get_units()

        assert len(units) > 0
        assert all(isinstance(u, CodeUnit) for u in units)

    def test_get_unit_by_id(self, temp_repo_with_files, indexer):
        """Test retrieving unit by ID."""
        indexer.index_directory()

        units = indexer.get_units()
        unit_id = units[0].id

        retrieved = indexer.get_unit(unit_id)

        assert retrieved is not None
        assert retrieved.id == unit_id

    def test_get_nonexistent_unit(self, temp_repo_with_files, indexer):
        """Test retrieving nonexistent unit."""
        indexer.index_directory()

        unit = indexer.get_unit("nonexistent_id")

        assert unit is None

    def test_find_by_name(self, temp_repo_with_files, indexer):
        """Test finding units by name."""
        indexer.index_directory()

        units = indexer.find_by_name("authenticate")

        assert len(units) > 0
        assert any("authenticate" in u.name for u in units)

    def test_find_by_type(self, temp_repo_with_files, indexer):
        """Test finding units by type."""
        indexer.index_directory()

        functions = indexer.find_by_type("function")
        classes = indexer.find_by_type("class")

        assert len(functions) > 0
        assert len(classes) > 0

    def test_find_by_file(self, temp_repo_with_files, indexer):
        """Test finding units in a specific file."""
        indexer.index_directory()

        main_file = temp_repo_with_files / "src" / "main.py"
        units = indexer.find_by_file(str(main_file))

        assert len(units) > 0
        assert all(str(main_file) in u.file_path for u in units)


class TestSkipPatterns:
    """Test skip pattern functionality."""

    def test_skip_cache_directories(self, temp_repo_with_files, indexer):
        """Test that cache directories are skipped."""
        indexer.index_directory()

        # Check that __pycache__ files were skipped
        cache_files = [u for u in indexer.units if "__pycache__" in u.file_path]
        assert len(cache_files) == 0

    def test_custom_skip_patterns(self, temp_repo_with_files):
        """Test custom skip patterns."""
        custom_skip = {"src"}
        indexer = CodebaseIndexer(
            str(temp_repo_with_files), skip_patterns=custom_skip
        )

        indexer.index_directory()

        # Should skip src directory
        src_units = [u for u in indexer.units if "/src/" in u.file_path]
        assert len(src_units) == 0

    def test_should_skip_method(self, indexer, temp_repo_with_files):
        """Test _should_skip method."""
        cache_path = temp_repo_with_files / "__pycache__" / "test.py"
        assert indexer._should_skip(cache_path)

        src_path = temp_repo_with_files / "src" / "main.py"
        assert not indexer._should_skip(src_path)


class TestIndexerClear:
    """Test clearing index."""

    def test_clear_index(self, temp_repo_with_files, indexer):
        """Test clearing indexed data."""
        indexer.index_directory()

        assert len(indexer.units) > 0

        indexer.clear()

        assert len(indexer.units) == 0
        assert indexer.get_statistics()["total_units"] == 0


class TestIndexerErrors:
    """Test error handling."""

    def test_encoding_error_handling(self, tmp_path, indexer):
        """Test handling of encoding errors."""
        # Create a file with invalid encoding
        bad_file = tmp_path / "bad.py"
        bad_file.write_bytes(b"\x80\x81\x82\x83")

        # Should handle error gracefully
        units = indexer.index_file(str(bad_file))
        assert len(units) == 0

        # Should track error in statistics
        stats = indexer.get_statistics()
        assert stats["errors"] > 0


class TestIndexerWithEmbeddings:
    """Test indexer with embedding manager."""

    def test_with_embedding_manager(self, temp_repo_with_files):
        """Test indexer with embedding manager."""

        class MockEmbeddingManager:
            def generate(self, text: str):
                return [0.1] * 384

        embedding_manager = MockEmbeddingManager()
        indexer = CodebaseIndexer(
            str(temp_repo_with_files), embedding_manager=embedding_manager
        )

        units = indexer.index_directory()

        # Units should have embeddings
        for unit in units:
            if unit.embedding:
                assert len(unit.embedding) == 384

    def test_embedding_generation_failure(self, temp_repo_with_files):
        """Test handling of embedding generation failure."""

        class FailingEmbeddingManager:
            def generate(self, text: str):
                raise Exception("Embedding failed")

        embedding_manager = FailingEmbeddingManager()
        indexer = CodebaseIndexer(
            str(temp_repo_with_files), embedding_manager=embedding_manager
        )

        # Should not crash, just skip embeddings
        units = indexer.index_directory()
        assert len(units) > 0


class TestIndexerPerformance:
    """Test indexer performance."""

    def test_indexing_time_tracking(self, temp_repo_with_files, indexer):
        """Test that indexing time is tracked."""
        indexer.index_directory()

        stats = indexer.get_statistics()

        assert stats["indexing_time"] > 0

    def test_units_per_file_calculation(self, temp_repo_with_files, indexer):
        """Test units per file calculation."""
        indexer.index_directory()

        index_stats = IndexStatistics(indexer)
        stats = index_stats.to_dict()

        # Should have units per file metric
        assert "units_per_file" in stats
        assert stats["units_per_file"] > 0


class TestIndexerIntegration:
    """Test integration with parser."""

    def test_all_units_have_required_fields(self, temp_repo_with_files, indexer):
        """Test that all units have required fields."""
        indexer.index_directory()

        units = indexer.get_units()

        for unit in units:
            assert unit.id is not None
            assert unit.type is not None
            assert unit.name is not None
            assert unit.file_path is not None
            assert unit.code is not None

    def test_units_are_searchable(self, temp_repo_with_files, indexer):
        """Test that indexed units are searchable."""
        indexer.index_directory()

        # Find by name
        auth_units = indexer.find_by_name("auth")
        assert len(auth_units) > 0

        # Find by type
        functions = indexer.find_by_type("function")
        assert len(functions) > 0

        classes = indexer.find_by_type("class")
        assert len(classes) > 0

    def test_dependencies_are_preserved(self, temp_repo_with_files, indexer):
        """Test that dependencies are preserved in index."""
        indexer.index_directory()

        # Find authenticate function
        auth_funcs = indexer.find_by_name("authenticate")
        assert len(auth_funcs) > 0

        auth_func = auth_funcs[0]
        # Should have dependency on validate_user
        assert "validate_user" in auth_func.dependencies
