"""Tests for code search models."""

import pytest
from athena.code_search.models import CodeUnit, SearchResult, SearchQuery


class TestCodeUnit:
    """Test CodeUnit model."""

    def test_code_unit_creation(self):
        """Test creating a CodeUnit."""
        unit = CodeUnit(
            id="test.py:10:foo",
            type="function",
            name="foo",
            signature="def foo(x: int) -> str:",
            code="def foo(x: int) -> str:\n    return str(x)",
            file_path="test.py",
            start_line=10,
            end_line=11,
            docstring="Convert integer to string",
            dependencies=["str"],
        )

        assert unit.id == "test.py:10:foo"
        assert unit.name == "foo"
        assert unit.type == "function"
        assert unit.file_path == "test.py"
        assert unit.start_line == 10
        assert unit.end_line == 11
        assert len(unit.dependencies) == 1

    def test_code_unit_to_dict(self):
        """Test CodeUnit serialization."""
        unit = CodeUnit(
            id="test.py:10:foo",
            type="function",
            name="foo",
            signature="def foo():",
            code="def foo():\n    pass",
            file_path="test.py",
            start_line=10,
            end_line=11,
        )

        result = unit.to_dict()

        assert result["id"] == "test.py:10:foo"
        assert result["type"] == "function"
        assert result["name"] == "foo"
        assert result["file_path"] == "test.py"
        assert result["lines_of_code"] == 2

    def test_code_unit_with_embedding(self):
        """Test CodeUnit with embedding."""
        embedding = [0.1, 0.2, 0.3, 0.4, 0.5]

        unit = CodeUnit(
            id="test.py:1:fn",
            type="function",
            name="fn",
            signature="def fn():",
            code="def fn(): pass",
            file_path="test.py",
            start_line=1,
            end_line=1,
            embedding=embedding,
        )

        assert unit.embedding == embedding
        assert len(unit.embedding) == 5


class TestSearchResult:
    """Test SearchResult model."""

    def test_search_result_creation(self):
        """Test creating a SearchResult."""
        unit = CodeUnit(
            id="test.py:1:foo",
            type="function",
            name="foo",
            signature="def foo():",
            code="def foo(): pass",
            file_path="test.py",
            start_line=1,
            end_line=1,
        )

        result = SearchResult(
            unit=unit,
            relevance=0.95,
            context="semantic_match",
            matches=["semantic"],
        )

        assert result.relevance == 0.95
        assert result.context == "semantic_match"
        assert "semantic" in result.matches

    def test_search_result_to_dict(self):
        """Test SearchResult serialization."""
        unit = CodeUnit(
            id="auth.py:42:authenticate",
            type="function",
            name="authenticate",
            signature="def authenticate(user: str):",
            code="def authenticate(user: str):\n    return validate(user)",
            file_path="auth.py",
            start_line=42,
            end_line=43,
            docstring="Authenticate a user",
        )

        result = SearchResult(
            unit=unit,
            relevance=0.87,
            context="semantic_match",
            matches=["semantic", "docstring"],
        )

        result_dict = result.to_dict()

        assert result_dict["file"] == "auth.py"
        assert result_dict["name"] == "authenticate"
        assert result_dict["relevance"] == 0.87
        assert "semantic" in result_dict["matches"]


class TestSearchQuery:
    """Test SearchQuery model."""

    def test_search_query_creation(self):
        """Test creating a SearchQuery."""
        query = SearchQuery(
            original="Find authentication code",
            intent="find_authentication",
            structural_patterns=["function_def", "try_except"],
        )

        assert query.original == "Find authentication code"
        assert query.intent == "find_authentication"
        assert len(query.structural_patterns) == 2

    def test_search_query_to_dict(self):
        """Test SearchQuery serialization."""
        query = SearchQuery(
            original="database queries",
            intent="find_database_access",
            structural_patterns=["cursor.execute", "sql"],
        )

        query_dict = query.to_dict()

        assert query_dict["original"] == "database queries"
        assert query_dict["intent"] == "find_database_access"
        assert len(query_dict["structural_patterns"]) == 2

    def test_search_query_with_embedding(self):
        """Test SearchQuery with embedding."""
        embedding = [0.1, 0.2, 0.3]

        query = SearchQuery(
            original="test",
            intent="test",
            embedding=embedding,
        )

        assert query.embedding == embedding


class TestModelIntegration:
    """Test integration between models."""

    def test_search_result_with_multiple_matches(self):
        """Test SearchResult with multiple match types."""
        unit = CodeUnit(
            id="test.py:1:search",
            type="function",
            name="search",
            signature="def search(query: str):",
            code="def search(query: str):\n    return db.query(query)",
            file_path="test.py",
            start_line=1,
            end_line=2,
            docstring="Search database for query",
        )

        result = SearchResult(
            unit=unit,
            relevance=0.92,
            context="semantic_and_structural",
            matches=["semantic", "structural", "docstring"],
        )

        assert len(result.matches) == 3
        assert result.relevance == 0.92

    def test_code_unit_with_many_dependencies(self):
        """Test CodeUnit with multiple dependencies."""
        unit = CodeUnit(
            id="complex.py:1:process",
            type="function",
            name="process",
            signature="def process():",
            code="def process():\n    pass",
            file_path="complex.py",
            start_line=1,
            end_line=2,
            dependencies=["validate", "transform", "save", "log"],
        )

        assert len(unit.dependencies) == 4
        unit_dict = unit.to_dict()
        assert unit_dict["dependencies"] == ["validate", "transform", "save", "log"]
