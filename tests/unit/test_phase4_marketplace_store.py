"""Tests for marketplace storage layer."""

import pytest
import json
from datetime import datetime, timedelta
from athena.api.marketplace_store import MarketplaceStore
from athena.api.marketplace import (
    ProcedureMetadata,
    MarketplaceProcedure,
    ProcedureReview,
    ProcedureInstallation,
    ProcedureQuality,
    UseCaseCategory,
)
from athena.core.database import Database


@pytest.fixture
def db(tmp_path):
    """Create test database."""
    db_path = tmp_path / "test.db"
    return Database(str(db_path))


@pytest.fixture
def marketplace_store(db):
    """Create marketplace store."""
    return MarketplaceStore(db)


@pytest.fixture
def sample_metadata():
    """Create sample procedure metadata."""
    return ProcedureMetadata(
        procedure_id="proc-test-001",
        name="Data Processor",
        description="Process and transform data efficiently",
        author="test-author",
        version="1.0.0",
        quality_level=ProcedureQuality.STABLE,
        use_case=UseCaseCategory.DATA_PROCESSING,
        tags=["data", "processing", "transform"],
        dependencies=["pandas", "numpy"],
        execution_count=10,
        success_rate=0.95,
        avg_execution_time_ms=125.5,
    )


@pytest.fixture
def sample_procedure(sample_metadata):
    """Create sample marketplace procedure."""
    return MarketplaceProcedure(
        metadata=sample_metadata,
        code="def process(data):\n    return data.transform()",
        documentation="# Data Processor\n\nProcesses data efficiently.",
        usage_examples=[
            {
                "description": "Basic usage",
                "code": "processor.process(df)",
                "output": "Transformed dataframe",
            }
        ],
        performance_stats={"avg_time_ms": 125.5, "memory_mb": 45},
        ratings={"usability": 4.5, "performance": 4.2},
    )


class TestMarketplaceStoreBasics:
    """Test basic marketplace store functionality."""

    def test_store_procedure(self, marketplace_store, sample_procedure):
        """Test storing a procedure."""
        proc_id = marketplace_store.store_procedure(
            metadata=sample_procedure.metadata,
            code=sample_procedure.code,
            documentation=sample_procedure.documentation,
            usage_examples=sample_procedure.usage_examples,
            performance_stats=sample_procedure.performance_stats,
        )

        assert proc_id == "proc-test-001"

        # Verify stored
        retrieved = marketplace_store.get_procedure(proc_id)
        assert retrieved is not None
        assert retrieved.metadata.name == "Data Processor"

    def test_get_nonexistent_procedure(self, marketplace_store):
        """Test getting non-existent procedure returns None."""
        result = marketplace_store.get_procedure("nonexistent-id")
        assert result is None

    def test_update_procedure_stats(self, marketplace_store, sample_procedure):
        """Test updating procedure statistics."""
        # Store procedure
        marketplace_store.store_procedure(
            metadata=sample_procedure.metadata,
            code=sample_procedure.code,
            documentation=sample_procedure.documentation,
        )

        # Update stats
        success = marketplace_store.update_procedure_stats(
            procedure_id="proc-test-001",
            execution_count=15,
            success_rate=0.93,
            avg_execution_time_ms=130.0,
        )

        assert success is True

        # Verify update
        updated = marketplace_store.get_procedure("proc-test-001")
        assert updated.metadata.execution_count == 15
        assert updated.metadata.success_rate == 0.93
        assert updated.metadata.avg_execution_time_ms == 130.0

    def test_record_execution_success(self, marketplace_store, sample_procedure):
        """Test recording successful execution."""
        marketplace_store.store_procedure(
            metadata=sample_procedure.metadata,
            code=sample_procedure.code,
            documentation=sample_procedure.documentation,
        )

        success = marketplace_store.record_execution("proc-test-001", success=True, execution_time_ms=100.0)
        assert success is True

        # Verify execution recorded
        updated = marketplace_store.get_procedure("proc-test-001")
        assert updated.metadata.execution_count == 11  # 10 + 1
        # (10 * 0.95 + 1) / 11 = 10.5 / 11 = 0.954...
        assert updated.metadata.success_rate > 0.9  # Should be high

    def test_record_execution_failure(self, marketplace_store, sample_procedure):
        """Test recording failed execution."""
        marketplace_store.store_procedure(
            metadata=sample_procedure.metadata,
            code=sample_procedure.code,
            documentation=sample_procedure.documentation,
        )

        success = marketplace_store.record_execution("proc-test-001", success=False, execution_time_ms=50.0)
        assert success is True

        # Verify execution recorded
        updated = marketplace_store.get_procedure("proc-test-001")
        assert updated.metadata.execution_count == 11
        assert updated.metadata.success_rate < 0.95  # Should decrease

    def test_delete_procedure(self, marketplace_store, sample_procedure):
        """Test deleting a procedure."""
        marketplace_store.store_procedure(
            metadata=sample_procedure.metadata,
            code=sample_procedure.code,
            documentation=sample_procedure.documentation,
        )

        # Delete
        success = marketplace_store.delete_procedure("proc-test-001")
        assert success is True

        # Verify deleted
        assert marketplace_store.get_procedure("proc-test-001") is None


class TestMarketplaceStoreListing:
    """Test listing and filtering procedures."""

    def test_list_procedures_empty(self, marketplace_store):
        """Test listing procedures when empty."""
        procedures = marketplace_store.list_procedures()
        assert len(procedures) == 0

    def test_list_procedures_all(self, marketplace_store):
        """Test listing all procedures."""
        # Create two procedures
        meta1 = ProcedureMetadata(
            procedure_id="proc-1",
            name="Proc 1",
            description="First procedure",
            author="author1",
            version="1.0",
            quality_level=ProcedureQuality.STABLE,
            use_case=UseCaseCategory.DATA_PROCESSING,
            tags=["data"],
        )

        meta2 = ProcedureMetadata(
            procedure_id="proc-2",
            name="Proc 2",
            description="Second procedure",
            author="author2",
            version="1.0",
            quality_level=ProcedureQuality.BETA,
            use_case=UseCaseCategory.ANALYSIS,
            tags=["analysis"],
        )

        marketplace_store.store_procedure(meta1, "code1", "doc1")
        marketplace_store.store_procedure(meta2, "code2", "doc2")

        procedures = marketplace_store.list_procedures()
        assert len(procedures) == 2

    def test_list_procedures_by_quality(self, marketplace_store):
        """Test filtering procedures by quality level."""
        meta1 = ProcedureMetadata(
            procedure_id="proc-stable",
            name="Stable Proc",
            description="Stable",
            author="author",
            version="1.0",
            quality_level=ProcedureQuality.STABLE,
            use_case=UseCaseCategory.DATA_PROCESSING,
            tags=["data"],
        )

        meta2 = ProcedureMetadata(
            procedure_id="proc-beta",
            name="Beta Proc",
            description="Beta",
            author="author",
            version="1.0",
            quality_level=ProcedureQuality.BETA,
            use_case=UseCaseCategory.DATA_PROCESSING,
            tags=["data"],
        )

        marketplace_store.store_procedure(meta1, "code1", "doc1")
        marketplace_store.store_procedure(meta2, "code2", "doc2")

        stable = marketplace_store.list_procedures(quality_level=ProcedureQuality.STABLE)
        assert len(stable) == 1
        assert stable[0].metadata.procedure_id == "proc-stable"

    def test_list_procedures_by_category(self, marketplace_store):
        """Test filtering procedures by category."""
        meta1 = ProcedureMetadata(
            procedure_id="proc-data",
            name="Data Proc",
            description="Data",
            author="author",
            version="1.0",
            quality_level=ProcedureQuality.STABLE,
            use_case=UseCaseCategory.DATA_PROCESSING,
            tags=["data"],
        )

        meta2 = ProcedureMetadata(
            procedure_id="proc-analysis",
            name="Analysis Proc",
            description="Analysis",
            author="author",
            version="1.0",
            quality_level=ProcedureQuality.STABLE,
            use_case=UseCaseCategory.ANALYSIS,
            tags=["analysis"],
        )

        marketplace_store.store_procedure(meta1, "code1", "doc1")
        marketplace_store.store_procedure(meta2, "code2", "doc2")

        data_procs = marketplace_store.list_procedures(category=UseCaseCategory.DATA_PROCESSING)
        assert len(data_procs) == 1
        assert data_procs[0].metadata.procedure_id == "proc-data"

    def test_list_procedures_by_tags(self, marketplace_store):
        """Test filtering procedures by tags."""
        meta1 = ProcedureMetadata(
            procedure_id="proc-1",
            name="Proc 1",
            description="Desc",
            author="author",
            version="1.0",
            quality_level=ProcedureQuality.STABLE,
            use_case=UseCaseCategory.DATA_PROCESSING,
            tags=["data", "csv"],
        )

        meta2 = ProcedureMetadata(
            procedure_id="proc-2",
            name="Proc 2",
            description="Desc",
            author="author",
            version="1.0",
            quality_level=ProcedureQuality.STABLE,
            use_case=UseCaseCategory.DATA_PROCESSING,
            tags=["data", "json"],
        )

        marketplace_store.store_procedure(meta1, "code1", "doc1")
        marketplace_store.store_procedure(meta2, "code2", "doc2")

        csv_procs = marketplace_store.list_procedures(tags=["csv"])
        assert len(csv_procs) == 1
        assert "csv" in csv_procs[0].metadata.tags

    def test_search_procedures(self, marketplace_store):
        """Test searching procedures."""
        meta1 = ProcedureMetadata(
            procedure_id="proc-data-processor",
            name="Data Processor",
            description="Processes data files",
            author="author",
            version="1.0",
            quality_level=ProcedureQuality.STABLE,
            use_case=UseCaseCategory.DATA_PROCESSING,
            tags=["data"],
        )

        marketplace_store.store_procedure(meta1, "code1", "doc1")

        # Search by name
        results = marketplace_store.search_procedures("Data")
        assert len(results) == 1
        assert results[0].metadata.name == "Data Processor"

        # Search by description
        results = marketplace_store.search_procedures("files")
        assert len(results) == 1

    def test_search_procedures_with_code_stripping(self, marketplace_store, sample_procedure):
        """Test that code can be stripped from search results."""
        marketplace_store.store_procedure(
            metadata=sample_procedure.metadata,
            code=sample_procedure.code,
            documentation=sample_procedure.documentation,
        )

        # Include code
        results_with_code = marketplace_store.search_procedures("Data", limit=10, include_code=True)
        assert len(results_with_code) == 1
        assert results_with_code[0].code != ""

        # Without code
        results_no_code = marketplace_store.search_procedures("Data", limit=10, include_code=False)
        assert len(results_no_code) == 1
        assert results_no_code[0].code == ""


class TestMarketplaceStoreReviews:
    """Test review functionality."""

    def test_add_review(self, marketplace_store, sample_procedure):
        """Test adding a review."""
        marketplace_store.store_procedure(
            metadata=sample_procedure.metadata,
            code=sample_procedure.code,
            documentation=sample_procedure.documentation,
        )

        review = ProcedureReview(
            procedure_id="proc-test-001",
            reviewer_id="user-123",
            rating=4.5,
            comment="Great procedure!",
            aspects={"usability": 4.5, "performance": 4.0},
        )

        review_id = marketplace_store.add_review(review)
        assert review_id is not None
        assert review_id >= 0  # First review gets index 0

    def test_get_reviews(self, marketplace_store, sample_procedure):
        """Test retrieving reviews."""
        marketplace_store.store_procedure(
            metadata=sample_procedure.metadata,
            code=sample_procedure.code,
            documentation=sample_procedure.documentation,
        )

        review1 = ProcedureReview(
            procedure_id="proc-test-001",
            reviewer_id="user-1",
            rating=4.5,
            comment="Great!",
        )

        review2 = ProcedureReview(
            procedure_id="proc-test-001",
            reviewer_id="user-2",
            rating=4.0,
            comment="Good!",
        )

        marketplace_store.add_review(review1)
        marketplace_store.add_review(review2)

        reviews = marketplace_store.get_reviews("proc-test-001")
        assert len(reviews) == 2

    def test_get_average_rating(self, marketplace_store, sample_procedure):
        """Test calculating average rating."""
        marketplace_store.store_procedure(
            metadata=sample_procedure.metadata,
            code=sample_procedure.code,
            documentation=sample_procedure.documentation,
        )

        review1 = ProcedureReview("proc-test-001", "user-1", 5.0, "Excellent")
        review2 = ProcedureReview("proc-test-001", "user-2", 4.0, "Good")

        marketplace_store.add_review(review1)
        marketplace_store.add_review(review2)

        avg_rating = marketplace_store.get_average_rating("proc-test-001")
        assert avg_rating == 4.5

    def test_get_average_rating_no_reviews(self, marketplace_store, sample_procedure):
        """Test average rating with no reviews."""
        marketplace_store.store_procedure(
            metadata=sample_procedure.metadata,
            code=sample_procedure.code,
            documentation=sample_procedure.documentation,
        )

        avg_rating = marketplace_store.get_average_rating("proc-test-001")
        assert avg_rating is None


class TestMarketplaceStoreInstallations:
    """Test installation tracking."""

    def test_record_installation(self, marketplace_store, sample_procedure):
        """Test recording an installation."""
        marketplace_store.store_procedure(
            metadata=sample_procedure.metadata,
            code=sample_procedure.code,
            documentation=sample_procedure.documentation,
        )

        installation = ProcedureInstallation(
            procedure_id="proc-test-001",
            installed_at=datetime.now(),
            version="1.0.0",
            installed_by="user-123",
            installation_context={"project": "test-project"},
            auto_update=True,
        )

        install_id = marketplace_store.record_installation(installation)
        assert install_id is not None
        assert install_id >= 0  # First installation gets index 0

    def test_get_installations(self, marketplace_store, sample_procedure):
        """Test retrieving installation records."""
        marketplace_store.store_procedure(
            metadata=sample_procedure.metadata,
            code=sample_procedure.code,
            documentation=sample_procedure.documentation,
        )

        installation1 = ProcedureInstallation(
            procedure_id="proc-test-001",
            installed_at=datetime.now(),
            version="1.0.0",
            installed_by="user-1",
        )

        installation2 = ProcedureInstallation(
            procedure_id="proc-test-001",
            installed_at=datetime.now(),
            version="1.0.1",
            installed_by="user-2",
        )

        marketplace_store.record_installation(installation1)
        marketplace_store.record_installation(installation2)

        installations = marketplace_store.get_installations("proc-test-001")
        assert len(installations) == 2

    def test_get_installation_count(self, marketplace_store, sample_procedure):
        """Test getting installation count."""
        marketplace_store.store_procedure(
            metadata=sample_procedure.metadata,
            code=sample_procedure.code,
            documentation=sample_procedure.documentation,
        )

        for i in range(3):
            installation = ProcedureInstallation(
                procedure_id="proc-test-001",
                installed_at=datetime.now(),
                version="1.0.0",
                installed_by=f"user-{i}",
            )
            marketplace_store.record_installation(installation)

        count = marketplace_store.get_installation_count("proc-test-001")
        assert count == 3


class TestMarketplaceStoreInMemory:
    """Test in-memory storage functionality."""

    def test_procedures_stored_in_memory(self, marketplace_store, sample_procedure):
        """Test that procedures are stored in memory."""
        marketplace_store.store_procedure(
            metadata=sample_procedure.metadata,
            code=sample_procedure.code,
            documentation=sample_procedure.documentation,
        )

        retrieved = marketplace_store.get_procedure("proc-test-001")
        assert retrieved is not None
        assert retrieved.metadata.name == "Data Processor"

    def test_reviews_stored_in_memory(self, marketplace_store, sample_procedure):
        """Test that reviews are stored in memory."""
        marketplace_store.store_procedure(
            metadata=sample_procedure.metadata,
            code=sample_procedure.code,
            documentation=sample_procedure.documentation,
        )

        review = ProcedureReview("proc-test-001", "user-1", 4.5, "Great!")
        marketplace_store.add_review(review)

        reviews = marketplace_store.get_reviews("proc-test-001")
        assert len(reviews) == 1
        assert reviews[0].rating == 4.5

    def test_installations_stored_in_memory(self, marketplace_store, sample_procedure):
        """Test that installation records are stored in memory."""
        marketplace_store.store_procedure(
            metadata=sample_procedure.metadata,
            code=sample_procedure.code,
            documentation=sample_procedure.documentation,
        )

        installation = ProcedureInstallation(
            procedure_id="proc-test-001",
            installed_at=datetime.now(),
            version="1.0.0",
            installed_by="user-1",
        )
        marketplace_store.record_installation(installation)

        installations = marketplace_store.get_installations("proc-test-001")
        assert len(installations) == 1


class TestMarketplaceStorePagination:
    """Test pagination and limiting."""

    def test_list_with_limit(self, marketplace_store):
        """Test limiting results."""
        for i in range(10):
            meta = ProcedureMetadata(
                procedure_id=f"proc-{i}",
                name=f"Procedure {i}",
                description="Test",
                author="author",
                version="1.0",
                quality_level=ProcedureQuality.STABLE,
                use_case=UseCaseCategory.DATA_PROCESSING,
                tags=["test"],
            )
            marketplace_store.store_procedure(meta, "code", "doc")

        # Get with limit
        procedures = marketplace_store.list_procedures(limit=5)
        assert len(procedures) == 5

    def test_list_with_offset(self, marketplace_store):
        """Test pagination with offset."""
        for i in range(10):
            meta = ProcedureMetadata(
                procedure_id=f"proc-{i}",
                name=f"Procedure {i}",
                description="Test",
                author="author",
                version="1.0",
                quality_level=ProcedureQuality.STABLE,
                use_case=UseCaseCategory.DATA_PROCESSING,
                tags=["test"],
            )
            marketplace_store.store_procedure(meta, "code", "doc")

        # Get with offset
        page1 = marketplace_store.list_procedures(limit=3, offset=0)
        page2 = marketplace_store.list_procedures(limit=3, offset=3)

        assert len(page1) == 3
        assert len(page2) == 3
        # Ensure different results
        assert page1[0].metadata.procedure_id != page2[0].metadata.procedure_id
