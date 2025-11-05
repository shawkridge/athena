"""Unit tests for research findings aggregation and deduplication."""

import pytest

from athena.research.aggregation import (
    AggregatedFinding,
    FindingDeduplicator,
    FindingCrossValidator,
    FindingAggregator,
)


class TestAggregatedFinding:
    """Test AggregatedFinding model."""

    def test_initialization(self):
        """Test basic initialization."""
        finding = AggregatedFinding(
            title="Test Finding",
            summary="Test summary",
            primary_source="arXiv",
            base_credibility=0.9,
        )

        assert finding.title == "Test Finding"
        assert finding.primary_source == "arXiv"
        assert finding.base_credibility == 0.9

    def test_credibility_calculation(self):
        """Test credibility score calculation."""
        finding = AggregatedFinding(
            title="Test",
            summary="Summary",
            primary_source="arXiv",
            base_credibility=1.0,
            relevance_score=0.8,
        )

        # 1.0 * 0.8 = 0.8
        assert finding.final_credibility == 0.8

    def test_cross_validation_boost(self):
        """Test credibility boost from secondary sources."""
        finding = AggregatedFinding(
            title="Test",
            summary="Summary",
            primary_source="arXiv",
            base_credibility=0.8,
            relevance_score=0.9,
        )

        initial_credibility = finding.final_credibility
        # Initial: 0.8 * 0.9 = 0.72, no secondary sources

        # Add first secondary source
        finding.add_secondary_source("GitHub")
        with_one_source = finding.final_credibility
        # With 1 secondary: 0.72 + 0.10 = 0.82

        # Add second secondary source
        finding.add_secondary_source("Papers with Code")
        with_two_sources = finding.final_credibility
        # With 2 secondary: 0.72 + 0.15 = 0.87

        # Verify boost calculations
        assert with_one_source > initial_credibility
        assert with_two_sources > with_one_source
        assert abs(with_one_source - 0.82) < 0.01
        assert abs(with_two_sources - 0.87) < 0.01

    def test_add_secondary_source(self):
        """Test adding secondary sources."""
        finding = AggregatedFinding(
            title="Test",
            summary="Summary",
            primary_source="arXiv",
        )

        assert len(finding.secondary_sources) == 0

        finding.add_secondary_source("GitHub")
        assert len(finding.secondary_sources) == 1
        assert "GitHub" in finding.secondary_sources

        # Duplicate sources shouldn't be added
        finding.add_secondary_source("GitHub")
        assert len(finding.secondary_sources) == 1

    def test_primary_source_not_added_as_secondary(self):
        """Test that primary source isn't added as secondary."""
        finding = AggregatedFinding(
            title="Test",
            summary="Summary",
            primary_source="arXiv",
        )

        finding.add_secondary_source("arXiv")
        assert "arXiv" not in finding.secondary_sources


class TestFindingDeduplicator:
    """Test finding deduplication."""

    @pytest.fixture
    def deduplicator(self):
        """Create deduplicator fixture."""
        return FindingDeduplicator(similarity_threshold=0.85)

    def test_exact_match_detection(self, deduplicator):
        """Test detection of exact matching titles."""
        title1 = "Deep Learning Neural Networks"
        title2 = "Deep Learning Neural Networks"

        assert deduplicator.find_duplicates(title1, title2)

    def test_similar_title_detection(self, deduplicator):
        """Test detection of similar titles."""
        title1 = "Machine Learning Deep Learning"
        title2 = "Deep Learning Machine Learning"

        assert deduplicator.find_duplicates(title1, title2)

    def test_different_title_detection(self, deduplicator):
        """Test non-similar titles are not considered duplicates."""
        title1 = "Quantum Computing Fundamentals"
        title2 = "Web Development Best Practices"

        assert not deduplicator.find_duplicates(title1, title2)

    def test_text_similarity_calculation(self, deduplicator):
        """Test text similarity calculation."""
        text1 = "machine learning deep neural networks"
        text2 = "machine learning deep neural networks"

        similarity = deduplicator.calculate_text_similarity(text1, text2)
        assert similarity == 1.0

    def test_partial_similarity(self, deduplicator):
        """Test partial text similarity."""
        text1 = "machine learning deep neural networks"
        text2 = "machine learning algorithms"

        similarity = deduplicator.calculate_text_similarity(text1, text2)
        assert 0 < similarity < 1.0

    def test_deduplicate_findings_merge(self, deduplicator):
        """Test deduplication merges duplicate findings."""
        findings = [
            {
                "title": "Neural Networks Deep Learning",
                "summary": "Overview of neural networks",
                "source": "arXiv",
                "credibility_score": 1.0,
                "relevance_score": 0.9,
                "url": "https://arxiv.org/1",
            },
            {
                "title": "Deep Learning Neural Networks",
                "summary": "Similar overview",
                "source": "GitHub",
                "credibility_score": 0.85,
                "relevance_score": 0.85,
                "url": "https://github.com/1",
            },
        ]

        aggregated = deduplicator.deduplicate_findings(findings)

        # Should merge into single finding
        assert len(aggregated) == 1
        assert aggregated[0].primary_source == "arXiv"  # Higher credibility
        assert "GitHub" in aggregated[0].secondary_sources

    def test_deduplicate_no_duplicates(self, deduplicator):
        """Test deduplication when no duplicates exist."""
        findings = [
            {
                "title": "Quantum Computing Fundamentals",
                "summary": "Intro to quantum",
                "source": "arXiv",
                "credibility_score": 1.0,
                "relevance_score": 0.9,
            },
            {
                "title": "Web Development Best Practices",
                "summary": "Web dev guide",
                "source": "Medium",
                "credibility_score": 0.68,
                "relevance_score": 0.8,
            },
        ]

        aggregated = deduplicator.deduplicate_findings(findings)

        # Should not merge
        assert len(aggregated) == 2


class TestFindingCrossValidator:
    """Test cross-validation of findings."""

    @pytest.fixture
    def validator(self):
        """Create validator fixture."""
        return FindingCrossValidator()

    def test_validate_single_source(self, validator):
        """Test validation of single-source finding."""
        findings = [
            AggregatedFinding(
                title="Test",
                summary="Summary",
                primary_source="arXiv",
                base_credibility=0.5,
            )
        ]

        validated = validator.validate_findings(findings)

        assert len(validated) == 1
        assert validated[0].base_credibility == 1.0  # arXiv credibility

    def test_validate_multi_source(self, validator):
        """Test validation boost for multi-source findings."""
        finding = AggregatedFinding(
            title="Test",
            summary="Summary",
            primary_source="arXiv",
        )
        finding.add_secondary_source("GitHub")
        finding.add_secondary_source("Papers with Code")

        findings = [finding]
        validated = validator.validate_findings(findings)

        assert validated[0].cross_validation_boost > 0

    def test_sort_by_credibility(self, validator):
        """Test findings are sorted by credibility."""
        findings = [
            AggregatedFinding(
                title="Low credibility",
                summary="Summary",
                primary_source="X/Twitter",
                base_credibility=0.3,
            ),
            AggregatedFinding(
                title="High credibility",
                summary="Summary",
                primary_source="arXiv",
                base_credibility=0.9,
            ),
        ]

        validated = validator.validate_findings(findings)

        # Should be sorted by credibility (high to low)
        assert validated[0].final_credibility >= validated[1].final_credibility

    def test_filter_high_confidence(self, validator):
        """Test high-confidence filtering."""
        findings = [
            AggregatedFinding(
                title="High",
                summary="Summary",
                primary_source="arXiv",
                base_credibility=1.0,
                relevance_score=0.95,
            ),
            AggregatedFinding(
                title="Low",
                summary="Summary",
                primary_source="X/Twitter",
                base_credibility=0.62,
                relevance_score=0.5,
            ),
        ]

        filtered = validator.filter_high_confidence(findings, min_credibility=0.8)

        assert len(filtered) == 1
        assert filtered[0].title == "High"


class TestFindingAggregator:
    """Test complete aggregation pipeline."""

    @pytest.fixture
    def aggregator(self):
        """Create aggregator fixture."""
        return FindingAggregator()

    def test_aggregate_findings(self, aggregator):
        """Test complete aggregation."""
        findings = [
            {
                "title": "Neural Networks Overview",
                "summary": "Overview of neural networks",
                "source": "arXiv",
                "credibility_score": 0.5,
                "relevance_score": 0.9,
                "url": "https://arxiv.org/1",
            },
            {
                "title": "Neural Networks Guide",
                "summary": "Similar guide",
                "source": "GitHub",
                "credibility_score": 0.5,
                "relevance_score": 0.85,
                "url": "https://github.com/1",
            },
        ]

        aggregated = aggregator.aggregate(findings)

        assert len(aggregated) > 0
        assert all(isinstance(f, AggregatedFinding) for f in aggregated)

    def test_aggregate_with_high_confidence_filter(self, aggregator):
        """Test aggregation with high-confidence filter."""
        findings = [
            {
                "title": "Research Paper",
                "summary": "High quality paper",
                "source": "arXiv",
                "credibility_score": 1.0,
                "relevance_score": 0.95,
            },
            {
                "title": "Tweet",
                "summary": "Random tweet",
                "source": "X/Twitter",
                "credibility_score": 0.62,
                "relevance_score": 0.5,
            },
        ]

        aggregated = aggregator.aggregate(findings, high_confidence_only=True)

        # Should filter out low-confidence findings
        assert all(f.final_credibility >= 0.8 for f in aggregated)

    def test_summary_stats(self, aggregator):
        """Test summary statistics generation."""
        findings = [
            AggregatedFinding(
                title="Test 1",
                summary="Summary 1",
                primary_source="arXiv",
                base_credibility=1.0,
            ),
            AggregatedFinding(
                title="Test 2",
                summary="Summary 2",
                primary_source="GitHub",
                base_credibility=0.85,
            ),
        ]

        stats = aggregator.get_summary_stats(findings)

        assert stats["total"] == 2
        assert stats["average_credibility"] > 0
        assert "arXiv" in stats["sources_represented"]
        assert "GitHub" in stats["sources_represented"]

    def test_summary_stats_empty(self, aggregator):
        """Test summary stats for empty findings."""
        stats = aggregator.get_summary_stats([])

        assert stats["total"] == 0
        assert stats["average_credibility"] == 0.0
