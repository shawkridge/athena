"""Unit tests for Research Findings Indexing."""

import pytest
from athena.integration.research_findings_index import (
    ResearchFindingsIndexer, Finding, FindingType, ConfidenceLevel, ResearchSession
)


class TestFindingExtraction:
    """Tests for finding extraction."""

    def test_extract_explicit_findings(self):
        """Should extract findings marked with 'Finding:'."""
        indexer = ResearchFindingsIndexer()
        text = """
        Finding: Machine learning improves prediction accuracy by 40%.
        Finding: The model requires significant computational resources.
        """

        findings = indexer.extract_findings(text)
        assert len(findings) >= 2

    def test_extract_quoted_findings(self):
        """Should extract quoted findings."""
        indexer = ResearchFindingsIndexer()
        text = 'Research shows that "the new method performs significantly better"'

        findings = indexer.extract_findings(text)
        assert len(findings) >= 1


class TestDomainDetection:
    """Tests for domain detection."""

    def test_detect_ml_domain(self):
        """Should detect machine learning domain."""
        indexer = ResearchFindingsIndexer()
        domain = indexer._detect_domain("The neural network improved accuracy")
        assert domain == 'machine-learning'

    def test_detect_security_domain(self):
        """Should detect security domain."""
        indexer = ResearchFindingsIndexer()
        domain = indexer._detect_domain("We found a vulnerability in encryption")
        assert domain == 'security'

    def test_detect_documentation_domain(self):
        """Should detect documentation domain."""
        indexer = ResearchFindingsIndexer()
        domain = indexer._detect_domain("The documentation is comprehensive")
        assert domain == 'documentation'


class TestFindingClassification:
    """Tests for finding type classification."""

    def test_classify_recommendation(self):
        """Should classify as recommendation."""
        indexer = ResearchFindingsIndexer()
        ftype = indexer._classify_finding("We recommend using this approach")
        assert ftype == FindingType.RECOMMENDATION

    def test_classify_contradiction(self):
        """Should classify contradictions."""
        indexer = ResearchFindingsIndexer()
        ftype = indexer._classify_finding("This contradicts previous findings")
        assert ftype == FindingType.CONTRADICTION

    def test_classify_pattern(self):
        """Should classify patterns."""
        indexer = ResearchFindingsIndexer()
        ftype = indexer._classify_finding("We identified a pattern in the data")
        assert ftype == FindingType.PATTERN


class TestConfidenceAssessment:
    """Tests for confidence assessment."""

    def test_high_confidence_multiple_sources(self):
        """Multiple sources = high confidence."""
        indexer = ResearchFindingsIndexer()
        confidence = indexer._assess_confidence(
            "Finding statement",
            ["source1.com", "source2.com"]
        )
        assert confidence == ConfidenceLevel.HIGH

    def test_low_confidence_single_source_weak(self):
        """Weak indicators = low confidence."""
        indexer = ResearchFindingsIndexer()
        confidence = indexer._assess_confidence(
            "Preliminary finding needs verification",
            ["source1.com"]
        )
        assert confidence == ConfidenceLevel.LOW


class TestTagGeneration:
    """Tests for tag generation."""

    def test_generate_domain_tags(self):
        """Should generate domain tags."""
        indexer = ResearchFindingsIndexer()
        tags = indexer._generate_tags("The neural network achieved high accuracy")
        assert 'machine-learning' in tags

    def test_generate_importance_tags(self):
        """Should tag important findings."""
        indexer = ResearchFindingsIndexer()
        tags = indexer._generate_tags("This is a critical security issue")
        assert 'important' in tags or 'warning' in tags


class TestFindingIndexing:
    """Tests for indexing findings."""

    def test_index_findings(self):
        """Should index findings."""
        indexer = ResearchFindingsIndexer()
        findings = [
            Finding(
                statement="Test finding",
                domain="testing",
                tags={'test', 'quality'}
            )
        ]

        indexer.index_findings(findings)
        assert len(indexer._findings_index) == 1

    def test_index_by_domain(self):
        """Should create domain index."""
        indexer = ResearchFindingsIndexer()
        finding = Finding(
            id="f1",
            statement="ML finding",
            domain="machine-learning"
        )

        indexer.index_findings([finding])
        assert 'machine-learning' in indexer._domain_index


class TestFindingSearch:
    """Tests for searching findings."""

    def test_search_by_query(self):
        """Should search findings by query."""
        indexer = ResearchFindingsIndexer()
        finding = Finding(
            id="f1",
            statement="Machine learning improves accuracy",
            domain="machine-learning"
        )

        indexer.index_findings([finding])
        results = indexer.search_findings("machine learning")
        assert len(results) == 1

    def test_filter_by_domain(self):
        """Should filter by domain."""
        indexer = ResearchFindingsIndexer()
        indexer.index_findings([
            Finding(id="f1", statement="ML finding", domain="machine-learning"),
            Finding(id="f2", statement="Security finding", domain="security")
        ])

        results = indexer.search_findings("", domain="machine-learning")
        assert len(results) == 1

    def test_filter_by_confidence(self):
        """Should filter by confidence."""
        indexer = ResearchFindingsIndexer()
        indexer.index_findings([
            Finding(id="f1", statement="High confidence", confidence=ConfidenceLevel.HIGH),
            Finding(id="f2", statement="Low confidence", confidence=ConfidenceLevel.LOW)
        ])

        results = indexer.search_findings("", confidence=ConfidenceLevel.HIGH)
        assert len(results) == 1


class TestResearchSession:
    """Tests for research sessions."""

    def test_create_session(self):
        """Should create research session."""
        indexer = ResearchFindingsIndexer()
        findings = [Finding(statement="Test finding")]

        session = indexer.create_session("Test Topic", findings)

        assert session.topic == "Test Topic"
        assert len(session.findings) == 1

    def test_get_findings_by_domain(self):
        """Should retrieve findings by domain."""
        indexer = ResearchFindingsIndexer()
        indexer.index_findings([
            Finding(id="f1", statement="ML finding", domain="machine-learning"),
            Finding(id="f2", statement="ML2 finding", domain="machine-learning"),
            Finding(id="f3", statement="Sec finding", domain="security")
        ])

        ml_findings = indexer.get_findings_by_domain("machine-learning")
        assert len(ml_findings) == 2


class TestStatistics:
    """Tests for statistics."""

    def test_get_statistics(self):
        """Should generate statistics."""
        indexer = ResearchFindingsIndexer()
        indexer.index_findings([
            Finding(id="f1", statement="Finding 1", domain="testing"),
            Finding(id="f2", statement="Finding 2", domain="security")
        ])

        stats = indexer.get_statistics()
        assert stats['total_findings'] == 2
        assert 'findings_by_domain' in stats
