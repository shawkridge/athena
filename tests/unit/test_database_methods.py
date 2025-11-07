"""Tests for Database class high-level methods (bulk_insert, filtered_search)."""

import tempfile
from pathlib import Path

import pytest

from athena.core.database import Database


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(str(db_path))
        yield db
        db.conn.close()


@pytest.fixture
def test_project(temp_db):
    """Create a test project."""
    return temp_db.create_project(
        name="test_project_memories",
        path="/test/project/memories"
    )


@pytest.fixture
def sample_memories(test_project):
    """Sample memory records for testing."""
    return [
        {
            "project_id": test_project.id,
            "content": "Python is a high-level programming language",
            "memory_type": "fact",
            "usefulness_score": 0.9,
            "created_at": 1700000000,
            "updated_at": 1700000000,
        },
        {
            "project_id": test_project.id,
            "content": "REST APIs use HTTP methods",
            "memory_type": "fact",
            "usefulness_score": 0.8,
            "created_at": 1700100000,
            "updated_at": 1700100000,
        },
        {
            "project_id": test_project.id,
            "content": "SQLite is a lightweight database",
            "memory_type": "concept",
            "usefulness_score": 0.75,
            "created_at": 1700200000,
            "updated_at": 1700200000,
        },
        {
            "project_id": test_project.id,
            "content": "Test-driven development improves code quality",
            "memory_type": "concept",
            "usefulness_score": 0.85,
            "created_at": 1700300000,
            "updated_at": 1700300000,
        },
        {
            "project_id": test_project.id,
            "content": "Caching improves performance",
            "memory_type": "fact",
            "usefulness_score": 0.6,
            "created_at": 1700400000,
            "updated_at": 1700400000,
        },
    ]


class TestDatabaseBulkInsert:
    """Tests for Database.bulk_insert() method."""

    def test_bulk_insert_empty_list(self, temp_db):
        """Test bulk_insert with empty list returns 0."""
        result = temp_db.bulk_insert("memories", [])
        assert result == 0

    def test_bulk_insert_single_row(self, temp_db, sample_memories):
        """Test bulk_insert with single row."""
        rows = sample_memories[:1]
        result = temp_db.bulk_insert("memories", rows)

        assert result == 1

        # Verify row was inserted
        cursor = temp_db.conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM memories")
        row = cursor.fetchone()
        assert row["count"] == 1

    def test_bulk_insert_multiple_rows(self, temp_db, sample_memories):
        """Test bulk_insert with multiple rows."""
        result = temp_db.bulk_insert("memories", sample_memories)

        assert result == 5

        # Verify all rows inserted
        cursor = temp_db.conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM memories")
        row = cursor.fetchone()
        assert row["count"] == 5

    def test_bulk_insert_preserves_data(self, temp_db, sample_memories):
        """Test that bulk_insert preserves data correctly."""
        temp_db.bulk_insert("memories", sample_memories)

        # Verify first row
        cursor = temp_db.conn.cursor()
        cursor.execute("SELECT content, memory_type, usefulness_score FROM memories WHERE content = ?",
                      (sample_memories[0]["content"],))
        row = cursor.fetchone()

        assert row is not None
        assert row["content"] == sample_memories[0]["content"]
        assert row["memory_type"] == sample_memories[0]["memory_type"]
        assert row["usefulness_score"] == sample_memories[0]["usefulness_score"]

    def test_bulk_insert_transaction_rollback_on_error(self, temp_db, test_project):
        """Test that bulk_insert rolls back on error."""
        valid_rows = [
            {
                "project_id": test_project.id,
                "content": "Valid memory",
                "memory_type": "fact",
                "usefulness_score": 0.8,
                "created_at": 1700000000,
                "updated_at": 1700000000,
            }
        ]

        # First insert should succeed
        temp_db.bulk_insert("memories", valid_rows)

        # Create rows with invalid data that will cause error
        invalid_rows = [
            {
                "project_id": test_project.id,
                "content": "Another memory",
                "memory_type": "fact",
                "usefulness_score": 0.8,
                # Missing created_at and updated_at - should cause NOT NULL error
            }
        ]

        # This should raise an exception
        with pytest.raises(Exception):
            temp_db.bulk_insert("memories", invalid_rows)

        # Verify first row is still there (committed)
        cursor = temp_db.conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM memories")
        row = cursor.fetchone()
        assert row["count"] == 1  # Only first insert succeeded


class TestDatabaseFilteredSearch:
    """Tests for Database.filtered_search() method."""

    @pytest.fixture
    def populated_db(self, temp_db, sample_memories):
        """Populate database with sample data."""
        temp_db.bulk_insert("memories", sample_memories)
        return temp_db

    def test_filtered_search_no_filters(self, populated_db):
        """Test filtered_search with no filters returns all rows."""
        results = populated_db.filtered_search("memories")

        assert len(results) == 5

    def test_filtered_search_single_equality(self, populated_db):
        """Test filtered_search with single equality filter."""
        results = populated_db.filtered_search(
            "memories",
            filters={"memory_type": "fact"}
        )

        assert len(results) == 3
        for row in results:
            assert row["memory_type"] == "fact"

    def test_filtered_search_comparison_operator(self, populated_db):
        """Test filtered_search with comparison operators."""
        results = populated_db.filtered_search(
            "memories",
            filters={"usefulness_score": {">": 0.75}}
        )

        assert len(results) == 3  # 0.9, 0.8, 0.85
        for row in results:
            assert row["usefulness_score"] > 0.75

    def test_filtered_search_multiple_filters(self, populated_db):
        """Test filtered_search with multiple AND filters."""
        results = populated_db.filtered_search(
            "memories",
            filters={
                "memory_type": "fact",
                "usefulness_score": {">": 0.7}
            }
        )

        assert len(results) == 2  # Python (0.9) and REST (0.8)
        for row in results:
            assert row["memory_type"] == "fact"
            assert row["usefulness_score"] > 0.7

    def test_filtered_search_in_operator(self, populated_db):
        """Test filtered_search with IN operator."""
        results = populated_db.filtered_search(
            "memories",
            filters={
                "memory_type": {"IN": ["fact", "concept"]}
            }
        )

        # All rows should match (all are either fact or concept)
        assert len(results) == 5

    def test_filtered_search_in_operator_subset(self, populated_db):
        """Test filtered_search with IN operator returning subset."""
        results = populated_db.filtered_search(
            "memories",
            filters={
                "memory_type": {"IN": ["concept"]}
            }
        )

        assert len(results) == 2
        for row in results:
            assert row["memory_type"] == "concept"

    def test_filtered_search_order_by(self, populated_db):
        """Test filtered_search with ORDER BY clause."""
        results = populated_db.filtered_search(
            "memories",
            order_by="usefulness_score DESC"
        )

        assert len(results) == 5
        # Verify ordering: 0.9, 0.85, 0.8, 0.75, 0.6
        scores = [row["usefulness_score"] for row in results]
        assert scores == sorted(scores, reverse=True)

    def test_filtered_search_limit(self, populated_db):
        """Test filtered_search with LIMIT clause."""
        results = populated_db.filtered_search(
            "memories",
            limit=2
        )

        assert len(results) == 2

    def test_filtered_search_order_by_and_limit(self, populated_db):
        """Test filtered_search with ORDER BY and LIMIT."""
        results = populated_db.filtered_search(
            "memories",
            order_by="usefulness_score DESC",
            limit=3
        )

        assert len(results) == 3
        # Should be top 3 by usefulness_score
        scores = [row["usefulness_score"] for row in results]
        assert scores == [0.9, 0.85, 0.8]

    def test_filtered_search_complex_query(self, populated_db):
        """Test filtered_search with complex multi-filter query."""
        results = populated_db.filtered_search(
            "memories",
            filters={
                "usefulness_score": {">": 0.7},
                "memory_type": {"IN": ["fact", "concept"]}
            },
            order_by="usefulness_score DESC",
            limit=2
        )

        assert len(results) == 2
        # Should have top 2 with score > 0.7
        assert results[0]["usefulness_score"] == 0.9
        assert results[1]["usefulness_score"] == 0.85

    def test_filtered_search_empty_result(self, populated_db):
        """Test filtered_search that returns no results."""
        results = populated_db.filtered_search(
            "memories",
            filters={"usefulness_score": {">": 0.95}}
        )

        assert len(results) == 0

    def test_filtered_search_invalid_in_operator(self, populated_db):
        """Test filtered_search raises error for invalid IN operator."""
        with pytest.raises(ValueError):
            populated_db.filtered_search(
                "memories",
                filters={"memory_type": {"IN": "not_a_list"}}
            )

    def test_filtered_search_less_than_operator(self, populated_db):
        """Test filtered_search with less-than operator."""
        results = populated_db.filtered_search(
            "memories",
            filters={"usefulness_score": {"<": 0.75}}
        )

        assert len(results) == 1  # Only 0.6
        assert results[0]["usefulness_score"] == 0.6

    def test_filtered_search_greater_equal_operator(self, populated_db):
        """Test filtered_search with >= operator."""
        results = populated_db.filtered_search(
            "memories",
            filters={"usefulness_score": {">=": 0.85}}
        )

        assert len(results) == 2  # 0.9 and 0.85
        for row in results:
            assert row["usefulness_score"] >= 0.85


class TestDatabaseIntegration:
    """Integration tests for database methods."""

    def test_bulk_insert_then_filtered_search(self, temp_db, sample_memories):
        """Test bulk_insert followed by filtered_search."""
        # Insert all memories
        inserted = temp_db.bulk_insert("memories", sample_memories)
        assert inserted == 5

        # Search for high-value facts
        results = temp_db.filtered_search(
            "memories",
            filters={
                "memory_type": "fact",
                "usefulness_score": {">": 0.7}
            },
            order_by="usefulness_score DESC"
        )

        assert len(results) == 2
        assert results[0]["content"] == "Python is a high-level programming language"
        assert results[1]["content"] == "REST APIs use HTTP methods"

    def test_multiple_bulk_inserts_then_search(self, temp_db, sample_memories):
        """Test multiple bulk_insert calls followed by search."""
        # First batch
        batch1 = sample_memories[:2]
        temp_db.bulk_insert("memories", batch1)

        # Second batch
        batch2 = sample_memories[2:]
        temp_db.bulk_insert("memories", batch2)

        # Total should be 5
        results = temp_db.filtered_search("memories")
        assert len(results) == 5

    def test_bulk_insert_with_project_filter(self, temp_db):
        """Test bulk insert with project_id and filtering."""
        # Create a project first
        project = temp_db.create_project(
            name="test_project",
            path="/test/path"
        )

        # Insert memories with project_id
        memories = [
            {
                "project_id": project.id,
                "content": f"Memory {i}",
                "memory_type": "fact",
                "created_at": 1700000000 + i,
                "updated_at": 1700000000 + i,
            }
            for i in range(3)
        ]

        inserted = temp_db.bulk_insert("memories", memories)
        assert inserted == 3

        # Search for this project's memories
        results = temp_db.filtered_search(
            "memories",
            filters={"project_id": project.id}
        )

        assert len(results) == 3
        for row in results:
            assert row["project_id"] == project.id
