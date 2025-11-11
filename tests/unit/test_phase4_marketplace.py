"""Tests for Phase 4 marketplace system."""

import pytest
from datetime import datetime

from athena.api.marketplace import (
    Marketplace,
    MarketplaceProcedure,
    ProcedureMetadata,
    ProcedureReview,
    ProcedureInstallation,
    ProcedureQuality,
    UseCaseCategory,
)


class TestProcedureMetadata:
    """Tests for ProcedureMetadata."""

    def test_metadata_creation(self):
        """Test creating procedure metadata."""
        metadata = ProcedureMetadata(
            procedure_id="test_proc",
            name="Test Procedure",
            description="A test procedure",
            author="Test Author",
            version="1.0.0",
            quality_level=ProcedureQuality.STABLE,
            use_case=UseCaseCategory.UTILITY,
            tags=["test", "sample"],
        )

        assert metadata.procedure_id == "test_proc"
        assert metadata.name == "Test Procedure"
        assert metadata.author == "Test Author"
        assert metadata.quality_level == ProcedureQuality.STABLE

    def test_metadata_timestamps(self):
        """Test that metadata has timestamps."""
        metadata = ProcedureMetadata(
            procedure_id="test",
            name="Test",
            description="Test",
            author="Author",
            version="1.0.0",
            quality_level=ProcedureQuality.BETA,
            use_case=UseCaseCategory.UTILITY,
            tags=[],
        )

        assert metadata.created_at is not None
        assert metadata.updated_at is not None
        assert isinstance(metadata.created_at, datetime)

    def test_metadata_to_dict(self):
        """Test converting metadata to dictionary."""
        metadata = ProcedureMetadata(
            procedure_id="test",
            name="Test Procedure",
            description="Description",
            author="Author",
            version="1.0.0",
            quality_level=ProcedureQuality.PRODUCTION,
            use_case=UseCaseCategory.ANALYSIS,
            tags=["tag1", "tag2"],
            dependencies=["dep1"],
        )

        metadata_dict = metadata.to_dict()
        assert metadata_dict["name"] == "Test Procedure"
        assert metadata_dict["quality_level"] == "production"
        assert metadata_dict["use_case"] == "analysis"
        assert len(metadata_dict["tags"]) == 2


class TestMarketplaceProcedure:
    """Tests for MarketplaceProcedure."""

    @pytest.fixture
    def sample_metadata(self):
        """Create sample metadata."""
        return ProcedureMetadata(
            procedure_id="proc_1",
            name="Sample Procedure",
            description="A sample procedure",
            author="Test Author",
            version="1.0.0",
            quality_level=ProcedureQuality.STABLE,
            use_case=UseCaseCategory.UTILITY,
            tags=["sample", "test"],
        )

    def test_procedure_creation(self, sample_metadata):
        """Test creating marketplace procedure."""
        procedure = MarketplaceProcedure(
            metadata=sample_metadata,
            code="def test(): pass",
            documentation="Test docs",
            usage_examples=[{"description": "Example 1", "code": "test()"}],
            performance_stats={"avg_time": 10},
        )

        assert procedure.metadata.name == "Sample Procedure"
        assert procedure.code == "def test(): pass"

    def test_procedure_to_dict(self, sample_metadata):
        """Test converting procedure to dictionary."""
        procedure = MarketplaceProcedure(
            metadata=sample_metadata,
            code="code",
            documentation="docs",
            usage_examples=[],
            performance_stats={},
        )

        proc_dict = procedure.to_dict()
        assert "metadata" in proc_dict
        assert "code" in proc_dict
        assert "documentation" in proc_dict

    def test_procedure_to_compact_dict(self, sample_metadata):
        """Test compact dictionary conversion (without code)."""
        procedure = MarketplaceProcedure(
            metadata=sample_metadata,
            code="def secret(): pass",
            documentation="docs",
            usage_examples=[],
            performance_stats={},
        )

        compact = procedure.to_compact_dict()
        assert "code" not in compact  # Should not include code
        assert "documentation" in compact
        assert "metadata" in compact


class TestProcedureReview:
    """Tests for ProcedureReview."""

    def test_review_creation(self):
        """Test creating procedure review."""
        review = ProcedureReview(
            procedure_id="proc_1",
            reviewer_id="user_1",
            rating=4.5,
            comment="Great procedure!",
        )

        assert review.procedure_id == "proc_1"
        assert review.rating == 4.5
        assert review.created_at is not None

    def test_review_with_aspects(self):
        """Test review with aspect ratings."""
        review = ProcedureReview(
            procedure_id="proc_1",
            reviewer_id="user_1",
            rating=4.0,
            comment="Good",
            aspects={"usability": 4.5, "performance": 3.5},
        )

        assert review.aspects["usability"] == 4.5
        assert len(review.aspects) == 2

    def test_review_to_dict(self):
        """Test converting review to dictionary."""
        review = ProcedureReview(
            procedure_id="proc_1",
            reviewer_id="user_1",
            rating=5.0,
            comment="Excellent",
        )

        review_dict = review.to_dict()
        assert review_dict["rating"] == 5.0
        assert review_dict["comment"] == "Excellent"
        assert "created_at" in review_dict


class TestProcedureInstallation:
    """Tests for ProcedureInstallation."""

    def test_installation_creation(self):
        """Test creating installation record."""
        installation = ProcedureInstallation(
            procedure_id="proc_1",
            installed_at=datetime.now(),
            version="1.0.0",
            installed_by="user_1",
        )

        assert installation.procedure_id == "proc_1"
        assert installation.version == "1.0.0"

    def test_installation_to_dict(self):
        """Test converting installation to dictionary."""
        now = datetime.now()
        installation = ProcedureInstallation(
            procedure_id="proc_1",
            installed_at=now,
            version="1.0.0",
            installed_by="user_1",
        )

        install_dict = installation.to_dict()
        assert install_dict["version"] == "1.0.0"
        assert install_dict["installed_by"] == "user_1"


class TestMarketplace:
    """Tests for Marketplace."""

    @pytest.fixture
    def marketplace(self):
        """Create test marketplace."""
        return Marketplace()

    @pytest.fixture
    def sample_procedure_data(self):
        """Create sample procedure data."""
        metadata = ProcedureMetadata(
            procedure_id="proc_test_1",
            name="Test Analysis Procedure",
            description="Analyzes test data",
            author="Test Author",
            version="1.0.0",
            quality_level=ProcedureQuality.STABLE,
            use_case=UseCaseCategory.ANALYSIS,
            tags=["analysis", "test", "data"],
        )
        return {
            "metadata": metadata,
            "code": "def analyze(): return 'result'",
            "documentation": "Analyzes data",
            "usage_examples": [{"description": "Basic", "code": "analyze()"}],
            "performance_stats": {"avg_time": 100},
        }

    def test_register_procedure(self, marketplace, sample_procedure_data):
        """Test registering procedure."""
        proc_id = marketplace.register_procedure(**sample_procedure_data)

        assert proc_id == "proc_test_1"
        assert proc_id in marketplace.procedures

    def test_get_procedure(self, marketplace, sample_procedure_data):
        """Test getting procedure from marketplace."""
        proc_id = marketplace.register_procedure(**sample_procedure_data)
        procedure = marketplace.get_procedure(proc_id)

        assert procedure is not None
        assert procedure.metadata.name == "Test Analysis Procedure"

    def test_get_nonexistent_procedure(self, marketplace):
        """Test getting non-existent procedure."""
        procedure = marketplace.get_procedure("nonexistent")
        assert procedure is None

    def test_list_procedures_no_filters(self, marketplace, sample_procedure_data):
        """Test listing all procedures."""
        marketplace.register_procedure(**sample_procedure_data)

        procedures = marketplace.list_procedures()
        assert len(procedures) == 1

    def test_list_procedures_by_category(self, marketplace, sample_procedure_data):
        """Test filtering procedures by category."""
        marketplace.register_procedure(**sample_procedure_data)

        # Should find with ANALYSIS category
        analysis_procs = marketplace.list_procedures(category=UseCaseCategory.ANALYSIS)
        assert len(analysis_procs) == 1

        # Should not find with different category
        utility_procs = marketplace.list_procedures(category=UseCaseCategory.UTILITY)
        assert len(utility_procs) == 0

    def test_list_procedures_by_quality(self, marketplace, sample_procedure_data):
        """Test filtering by quality level."""
        marketplace.register_procedure(**sample_procedure_data)

        # Should find STABLE procedures
        stable = marketplace.list_procedures(quality_level=ProcedureQuality.STABLE)
        assert len(stable) == 1

        # Should not find PRODUCTION procedures
        prod = marketplace.list_procedures(quality_level=ProcedureQuality.PRODUCTION)
        assert len(prod) == 0

    def test_list_procedures_by_tags(self, marketplace, sample_procedure_data):
        """Test filtering by tags."""
        marketplace.register_procedure(**sample_procedure_data)

        # Should find with matching tag
        tagged = marketplace.list_procedures(tags=["analysis"])
        assert len(tagged) == 1

        # Should not find with non-matching tag
        not_found = marketplace.list_procedures(tags=["nonexistent"])
        assert len(not_found) == 0

    def test_list_procedures_multiple_filters(self, marketplace, sample_procedure_data):
        """Test filtering with multiple criteria."""
        marketplace.register_procedure(**sample_procedure_data)

        # Should find with all criteria matched
        found = marketplace.list_procedures(
            category=UseCaseCategory.ANALYSIS,
            quality_level=ProcedureQuality.STABLE,
            tags=["test"],
        )
        assert len(found) == 1

    def test_search_procedures(self, marketplace, sample_procedure_data):
        """Test searching procedures."""
        marketplace.register_procedure(**sample_procedure_data)

        # Search by name
        results = marketplace.search_procedures("Test Analysis")
        assert len(results) > 0
        assert results[0].metadata.name == "Test Analysis Procedure"

    def test_search_procedures_by_description(self, marketplace, sample_procedure_data):
        """Test search by description."""
        marketplace.register_procedure(**sample_procedure_data)

        results = marketplace.search_procedures("analyzes")
        assert len(results) > 0

    def test_search_procedures_by_tags(self, marketplace, sample_procedure_data):
        """Test search by tags."""
        marketplace.register_procedure(**sample_procedure_data)

        results = marketplace.search_procedures("analysis")
        assert len(results) > 0

    def test_search_limit(self, marketplace, sample_procedure_data):
        """Test search result limit."""
        marketplace.register_procedure(**sample_procedure_data)

        results = marketplace.search_procedures("test", limit=1)
        assert len(results) <= 1

    def test_add_review(self, marketplace, sample_procedure_data):
        """Test adding review."""
        proc_id = marketplace.register_procedure(**sample_procedure_data)

        review = ProcedureReview(
            procedure_id=proc_id,
            reviewer_id="user_1",
            rating=4.5,
            comment="Good procedure",
        )
        marketplace.add_review(review)

        reviews = marketplace.get_reviews(proc_id)
        assert len(reviews) == 1
        assert reviews[0].rating == 4.5

    def test_get_procedure_rating(self, marketplace, sample_procedure_data):
        """Test calculating procedure rating."""
        proc_id = marketplace.register_procedure(**sample_procedure_data)

        # Add reviews
        marketplace.add_review(
            ProcedureReview(proc_id, "user_1", 5.0, "Excellent")
        )
        marketplace.add_review(
            ProcedureReview(proc_id, "user_2", 4.0, "Good")
        )

        rating = marketplace.get_procedure_rating(proc_id)
        assert rating == 4.5  # Average of 5.0 and 4.0

    def test_get_rating_no_reviews(self, marketplace, sample_procedure_data):
        """Test rating with no reviews."""
        proc_id = marketplace.register_procedure(**sample_procedure_data)

        rating = marketplace.get_procedure_rating(proc_id)
        assert rating is None

    def test_record_installation(self, marketplace, sample_procedure_data):
        """Test recording installation."""
        proc_id = marketplace.register_procedure(**sample_procedure_data)

        installation = ProcedureInstallation(
            procedure_id=proc_id,
            installed_at=datetime.now(),
            version="1.0.0",
            installed_by="user_1",
        )
        marketplace.record_installation(installation)

        installations = marketplace.get_installations(proc_id)
        assert len(installations) == 1

    def test_get_installation_count(self, marketplace, sample_procedure_data):
        """Test getting installation count."""
        proc_id = marketplace.register_procedure(**sample_procedure_data)

        # Record 3 installations
        for i in range(3):
            marketplace.record_installation(
                ProcedureInstallation(
                    procedure_id=proc_id,
                    installed_at=datetime.now(),
                    version="1.0.0",
                    installed_by=f"user_{i}",
                )
            )

        count = marketplace.get_installation_count(proc_id)
        assert count == 3
