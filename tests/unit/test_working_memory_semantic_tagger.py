"""Unit tests for Working Memory Semantic Tagging."""

import pytest
from athena.integration.working_memory_semantic_tagger import (
    WorkingMemorySemanticTagger, ContentType, Domain, ConsolidationTarget, Urgency
)


class TestContentTypeDetection:
    """Tests for content type detection."""

    def test_detect_code(self):
        """Should detect code content."""
        tagger = WorkingMemorySemanticTagger()
        content = """
        def train_model(data):
            model = Model()
            model.fit(data)
            return model
        """
        ctype = tagger._detect_content_type(content)
        assert ctype == ContentType.CODE

    def test_detect_error(self):
        """Should detect error content."""
        tagger = WorkingMemorySemanticTagger()
        content = "Error: Exception occurred in process_data. Traceback shows failure in line 42"
        ctype = tagger._detect_content_type(content)
        assert ctype == ContentType.ERROR

    def test_detect_strategy(self):
        """Should detect strategy content."""
        tagger = WorkingMemorySemanticTagger()
        content = "Strategy: Implement a two-phase approach - first optimize, then refactor"
        ctype = tagger._detect_content_type(content)
        assert ctype == ContentType.STRATEGY


class TestDomainDetection:
    """Tests for domain detection."""

    def test_detect_ml_domain(self):
        """Should detect machine learning domain."""
        tagger = WorkingMemorySemanticTagger()
        content = "The neural network model improved accuracy through gradient descent optimization"
        domain = tagger._detect_domain(content)
        assert domain == Domain.MACHINE_LEARNING

    def test_detect_security_domain(self):
        """Should detect security domain."""
        tagger = WorkingMemorySemanticTagger()
        content = "Security vulnerability: encryption key exposed in authentication token"
        domain = tagger._detect_domain(content)
        assert domain == Domain.SECURITY

    def test_detect_performance_domain(self):
        """Should detect performance domain."""
        tagger = WorkingMemorySemanticTagger()
        content = "Performance bottleneck: query optimization reduced latency by 40%"
        domain = tagger._detect_domain(content)
        assert domain == Domain.PERFORMANCE


class TestConsolidationTargetRouting:
    """Tests for consolidation target routing."""

    def test_code_to_procedural(self):
        """Code should route to procedural memory."""
        tagger = WorkingMemorySemanticTagger()
        target = tagger._determine_consolidation_target(
            ContentType.CODE,
            Domain.MACHINE_LEARNING
        )
        assert target == ConsolidationTarget.PROCEDURAL

    def test_concept_to_semantic(self):
        """Concepts should route to semantic memory."""
        tagger = WorkingMemorySemanticTagger()
        target = tagger._determine_consolidation_target(
            ContentType.CONCEPT,
            Domain.ARCHITECTURE
        )
        assert target == ConsolidationTarget.SEMANTIC

    def test_error_to_episodic(self):
        """Errors should route to episodic memory."""
        tagger = WorkingMemorySemanticTagger()
        target = tagger._determine_consolidation_target(
            ContentType.ERROR,
            Domain.DEBUG
        )
        assert target == ConsolidationTarget.EPISODIC


class TestUrgencyAssessment:
    """Tests for urgency assessment."""

    def test_errors_are_immediate(self):
        """Errors should have immediate urgency."""
        tagger = WorkingMemorySemanticTagger()
        urgency = tagger._assess_urgency(ContentType.ERROR, {})
        assert urgency == Urgency.IMMEDIATE

    def test_strategies_are_soon(self):
        """Strategies should have soon urgency."""
        tagger = WorkingMemorySemanticTagger()
        urgency = tagger._assess_urgency(ContentType.STRATEGY, {})
        assert urgency == Urgency.SOON

    def test_default_is_later(self):
        """Default urgency is later."""
        tagger = WorkingMemorySemanticTagger()
        urgency = tagger._assess_urgency(ContentType.CONCEPT, {})
        assert urgency == Urgency.LATER


class TestTagGeneration:
    """Tests for custom tag generation."""

    def test_generate_domain_tags(self):
        """Should generate domain tags."""
        tagger = WorkingMemorySemanticTagger()
        tags = tagger._generate_custom_tags(
            "ML model optimization",
            ContentType.CODE,
            Domain.MACHINE_LEARNING
        )
        assert 'machine-learning' in tags

    def test_generate_urgency_tags(self):
        """Should generate urgency tags."""
        tagger = WorkingMemorySemanticTagger()
        tags = tagger._generate_custom_tags(
            "CRITICAL: Fix security vulnerability immediately",
            ContentType.ERROR,
            Domain.SECURITY
        )
        assert 'urgent' in tags


class TestAnalyzeItem:
    """Tests for full item analysis."""

    def test_analyze_code_item(self):
        """Should analyze code item completely."""
        tagger = WorkingMemorySemanticTagger()
        content = """
        def process_data(dataset):
            # Train ML model
            model = MLModel()
            model.fit(dataset)
            return model
        """

        tag = tagger.analyze_item(content)

        assert tag.content_type == ContentType.CODE
        assert tag.domain == Domain.MACHINE_LEARNING
        assert tag.consolidation_target == ConsolidationTarget.PROCEDURAL
        assert tag.confidence > 0.5

    def test_analyze_error_item(self):
        """Should analyze error item completely."""
        tagger = WorkingMemorySemanticTagger()
        content = "Critical error: Authentication failed - token expired"

        tag = tagger.analyze_item(content)

        assert tag.content_type == ContentType.ERROR
        assert tag.urgency == Urgency.IMMEDIATE


class TestRoutingRecommendation:
    """Tests for routing recommendations."""

    def test_get_routing_recommendation(self):
        """Should provide routing recommendation."""
        tagger = WorkingMemorySemanticTagger()
        tag = tagger.analyze_item(
            "def important_function(): pass",
            {'is_recent': True}
        )

        recommendation = tagger.get_routing_recommendation(tag)

        assert 'target' in recommendation
        assert 'priority' in recommendation
        assert 'urgency' in recommendation
        assert 'confidence' in recommendation
        assert 0 <= recommendation['priority'] <= 3
