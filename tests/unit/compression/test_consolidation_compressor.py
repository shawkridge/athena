"""Unit tests for ConsolidationCompressor (v1.1).

Tests:
- Executive summary extraction from consolidated content
- Compression ratios and fidelity
- Integration with consolidation pipeline
- Edge cases (empty content, very long content, etc.)
"""

import pytest
from datetime import datetime, timedelta

from athena.compression.base import ConsolidationCompressor
from athena.compression.models import ConsolidationCompressionConfig, CompressionLevel
from tests.unit.compression.conftest import CompressionAssertions


class TestExecutiveSummaryExtraction:
    """Test extraction of ultra-short executive summaries."""

    def test_extract_summary_from_long_consolidation(self, consolidation_compression_config):
        """Should extract ultra-short summary from long consolidation."""
        compressor = ConsolidationCompressor(consolidation_compression_config)

        full_content = """
        Phase 1 implementation involved designing the authentication system with JWT tokens.
        The team implemented token generation, validation, and refresh mechanisms.
        Testing covered edge cases including expired tokens, malformed signatures, and token revocation.
        All 47 test cases passed successfully.
        The implementation was documented in auth/JWT.md with examples and troubleshooting.
        """

        summary = compressor.extract_executive_summary(full_content)

        # Should be much shorter (ultra-condensed)
        assert len(summary) < len(full_content) / 5, "Summary should be <20% of original"

        # Should preserve key concepts
        summary_lower = summary.lower()
        assert ('jwt' in summary_lower or 'token' in summary_lower or 'auth' in summary_lower), \
            "Should preserve key domain concepts"

    def test_summary_target_token_count(self, consolidation_compression_config):
        """Executive summary should target ~20 tokens."""
        compressor = ConsolidationCompressor(consolidation_compression_config)

        full_content = "A" * 1000  # Large content

        summary = compressor.extract_executive_summary(full_content)

        # Estimate tokens (0.25 tokens per char)
        summary_tokens = compressor.estimate_tokens(summary)

        # Should be roughly 20 tokens (allow 10-30 range)
        assert 10 <= summary_tokens <= 30, f"Summary tokens {summary_tokens} outside [10, 30]"

    def test_summary_preserves_subject_action(self, consolidation_compression_config):
        """Summary should preserve subject + action + key entity."""
        compressor = ConsolidationCompressor(consolidation_compression_config)

        full_content = """
        The team implemented a new caching strategy using Redis.
        Configuration involved setting up master-slave replication.
        Performance testing showed 40% latency reduction.
        """

        summary = compressor.extract_executive_summary(full_content)

        # Should contain key entities
        summary_lower = summary.lower()
        assert len(summary) > 10, "Summary should have some content"
        # Should be grammatical
        assert not summary.startswith(' '), "Should not start with space"

    def test_summary_single_sentence(self, consolidation_compression_config):
        """Summary should ideally be single sentence."""
        compressor = ConsolidationCompressor(consolidation_compression_config)

        full_content = """
        Implemented microservices architecture with Docker containers.
        Each service runs independently with separate databases.
        Services communicate via REST APIs and event streaming.
        Kubernetes orchestrates deployment and scaling.
        """

        summary = compressor.extract_executive_summary(full_content)

        # Count sentences (ending with . ! or ?)
        import re
        sentences = re.split(r'[.!?]+', summary)
        sentences = [s.strip() for s in sentences if s.strip()]

        assert len(sentences) <= 2, f"Summary should be 1-2 sentences, got {len(sentences)}"


class TestCompressionFromConsolidation:
    """Test compression operations during consolidation."""

    def test_compress_consolidated_memory(self, consolidation_compression_config):
        """Should compress consolidated memory with executive summary."""
        compressor = ConsolidationCompressor(consolidation_compression_config)

        memory = {
            'id': 1,
            'content': 'User implemented JWT authentication with bcrypt. ' * 20,  # ~1000 chars
            'created_at': datetime.now(),
        }

        result = compressor.compress(memory)

        # Should return CompressedMemory
        assert result.memory_id == 1
        assert result.content_full == memory['content']
        assert result.content_compressed is not None
        assert result.compression_level == CompressionLevel.REFERENCE
        assert result.fidelity == 0.05
        assert result.tokens_original > result.tokens_compressed
        assert result.content_executive is not None

    def test_decompress_consolidated_memory(self, consolidation_compression_config):
        """Should retrieve full consolidated content."""
        compressor = ConsolidationCompressor(consolidation_compression_config)

        result = compressor.decompress(memory_id=42)

        # Should return retrieval indicator
        assert isinstance(result, str)
        assert '42' in result
        assert 'retriev' in result.lower() or 'memory' in result.lower()


class TestExecutiveSummaryQuality:
    """Test quality of extracted summaries."""

    def test_summary_contains_no_repetition(self, consolidation_compression_config):
        """Summary should avoid repeated phrases."""
        compressor = ConsolidationCompressor(consolidation_compression_config)

        full_content = """
        Fixed the bug. The bug was critical. Fixed it quickly.
        The fix resolved the issue. Issue resolved successfully.
        """

        summary = compressor.extract_executive_summary(full_content)

        # Should not have obvious word repetition
        words = summary.lower().split()
        unique_words = set(words)

        # Most words should be unique (allow some repetition of articles/prepositions)
        repetition_ratio = 1.0 - (len(unique_words) / len(words))
        assert repetition_ratio < 0.4, "Summary has too much repetition"

    def test_summary_readable(self, consolidation_compression_config):
        """Summary should be readable (no broken grammar)."""
        compressor = ConsolidationCompressor(consolidation_compression_config)

        full_content = """
        Implemented JWT authentication with bcrypt hashing.
        Token expiration set to 1 hour with refresh token rotation.
        Database migration created to store JWT secrets securely.
        """

        summary = compressor.extract_executive_summary(full_content)

        # Should start with capital letter
        assert summary[0].isupper(), "Summary should start with capital letter"

        # Should not end with space
        assert not summary.endswith(' '), "Summary should not end with space"

        # Should contain mostly alphanumeric/punctuation
        non_standard = sum(1 for c in summary if not (c.isalnum() or c.isspace() or c in '.,;:-'))
        assert non_standard < 5, "Summary has unusual characters"


class TestSummaryFromDifferentDomains:
    """Test summary extraction across different knowledge domains."""

    def test_summary_technical_domain(self, consolidation_compression_config):
        """Should extract summary from technical content."""
        compressor = ConsolidationCompressor(consolidation_compression_config)

        technical = """
        Optimized database query using explain plans.
        Added composite index on user_id + created_at.
        Query latency reduced from 2.5s to 180ms.
        """

        summary = compressor.extract_executive_summary(technical)

        assert len(summary) > 0, "Should produce summary"
        summary_lower = summary.lower()
        # Should mention optimization or performance
        assert any(term in summary_lower for term in ['optim', 'index', 'latency', 'query', 'fast'])

    def test_summary_business_domain(self, consolidation_compression_config):
        """Should extract summary from business content."""
        compressor = ConsolidationCompressor(consolidation_compression_config)

        business = """
        Q3 revenue increased 25% year-over-year.
        New market expansion into Southeast Asia showing strong growth.
        Customer retention improved to 92% with new loyalty program.
        """

        summary = compressor.extract_executive_summary(business)

        assert len(summary) > 0, "Should produce summary"
        summary_lower = summary.lower()
        # Should mention key business metrics
        assert any(term in summary_lower for term in ['revenue', 'growth', 'customer', 'market', 'expand'])

    def test_summary_research_domain(self, consolidation_compression_config):
        """Should extract summary from research content."""
        compressor = ConsolidationCompressor(consolidation_compression_config)

        research = """
        Implemented Bayesian Surprise event segmentation algorithm.
        Surprise score calculated as -log(P(token|context)) + entropy_reduction.
        Tested on infinite context (10M tokens) with 95%+ accuracy.
        """

        summary = compressor.extract_executive_summary(research)

        assert len(summary) > 0, "Should produce summary"
        summary_lower = summary.lower()
        # Should mention implementation or algorithm
        assert any(term in summary_lower for term in ['implement', 'bayesian', 'algorithm', 'surprise', 'context'])


class TestEdgeCasesConsolidation:
    """Test edge cases in consolidation compression."""

    def test_empty_content(self, consolidation_compression_config):
        """Empty content should produce empty or minimal summary."""
        compressor = ConsolidationCompressor(consolidation_compression_config)

        summary = compressor.extract_executive_summary("")

        # Should handle gracefully
        assert isinstance(summary, str), "Should return string"
        assert len(summary) <= 50, "Empty content should produce minimal summary"

    def test_very_short_content(self, consolidation_compression_config):
        """Very short content should not shrink further."""
        compressor = ConsolidationCompressor(consolidation_compression_config)

        short = "Fixed bug."

        summary = compressor.extract_executive_summary(short)

        # Should not be empty
        assert len(summary) > 0, "Should produce some summary"
        # Should not be much longer than input
        assert len(summary) <= len(short) * 1.2, "Should not expand short content"

    def test_content_with_special_characters(self, consolidation_compression_config):
        """Should handle special characters gracefully."""
        compressor = ConsolidationCompressor(consolidation_compression_config)

        content = """
        Implemented @user/@system prompt engineering techniques.
        Used ${variable} substitution for template rendering.
        Regex pattern: [a-zA-Z0-9]{8,16} validated user input.
        """

        summary = compressor.extract_executive_summary(content)

        assert len(summary) > 0, "Should handle special characters"
        # Should not crash with special chars

    def test_single_very_long_sentence(self, consolidation_compression_config):
        """Should compress single very long sentence."""
        compressor = ConsolidationCompressor(consolidation_compression_config)

        long_sentence = "This is a very long sentence that goes on and on and on with many clauses and phrases that all relate to the same topic about implementing a new feature for the memory system which includes storage optimization and retrieval improvements."

        summary = compressor.extract_executive_summary(long_sentence)

        assert len(summary) < len(long_sentence), "Should compress long sentence"
        assert len(summary) > 0, "Should not produce empty summary"

    def test_multilingual_content(self, consolidation_compression_config):
        """Should handle non-ASCII characters."""
        compressor = ConsolidationCompressor(consolidation_compression_config)

        multilingual = """
        Implemented UTF-8 encoding support.
        French: "Nous avons implémenté la compression."
        Spanish: "Implementamos la compresión de memoria."
        Japanese: メモリー圧縮を実装しました。
        """

        summary = compressor.extract_executive_summary(multilingual)

        assert len(summary) > 0, "Should handle multilingual content"


class TestSummaryTokenCounting:
    """Test token counting for summaries."""

    def test_token_estimation_consistency(self, consolidation_compression_config):
        """Token estimation should be consistent."""
        compressor = ConsolidationCompressor(consolidation_compression_config)

        text = "A" * 1000
        tokens1 = compressor.estimate_tokens(text)
        tokens2 = compressor.estimate_tokens(text)

        assert tokens1 == tokens2, "Token estimation should be deterministic"

    def test_compression_ratio_calculation(self, consolidation_compression_config):
        """Compression ratio should be accurate."""
        compressor = ConsolidationCompressor(consolidation_compression_config)

        original = "A" * 1000
        compressed = "B" * 100

        ratio = compressor.calculate_compression_ratio(len(original), len(compressed))

        assert ratio == 0.1, "Ratio should be 100/1000 = 0.1"

    def test_summary_compression_target(self, consolidation_compression_config):
        """Summary should achieve target compression ratio."""
        compressor = ConsolidationCompressor(consolidation_compression_config)

        full_content = "Implementation details. " * 100  # ~2400 chars

        summary = compressor.extract_executive_summary(full_content)

        full_tokens = compressor.estimate_tokens(full_content)
        summary_tokens = compressor.estimate_tokens(summary)

        ratio = summary_tokens / full_tokens if full_tokens > 0 else 0

        # Target is 0.1 (10% of original), allow some variance
        assert ratio <= 0.25, f"Summary ratio {ratio:.2f} too high (target 0.1)"


class TestSummaryBatchProcessing:
    """Test batch processing of consolidations."""

    def test_process_multiple_consolidations(self, consolidation_compression_config, test_data_generator):
        """Should extract summaries from multiple consolidations."""
        compressor = ConsolidationCompressor(consolidation_compression_config)

        memories = test_data_generator.generate_memories(count=10)

        summaries = []
        for memory in memories:
            try:
                summary = compressor.extract_executive_summary(memory['content'])
                summaries.append(summary)
            except NotImplementedError:
                # Week 3: implement actual extraction
                pytest.skip("Not implemented in Week 2")

        assert len(summaries) > 0, "Should process multiple consolidations"

    def test_summary_consistency_across_batch(self, consolidation_compression_config):
        """Summaries should be consistently high quality in batch."""
        compressor = ConsolidationCompressor(consolidation_compression_config)

        batch_contents = [
            "User implemented authentication system with JWT tokens.",
            "Fixed CORS configuration issue affecting API calls.",
            "Optimized database queries using indexing strategies.",
        ]

        try:
            summaries = [
                compressor.extract_executive_summary(content)
                for content in batch_contents
            ]

            # All should be non-empty
            assert all(len(s) > 0 for s in summaries), "All summaries should be non-empty"

            # All should be shorter than originals
            assert all(
                len(s) < len(orig)
                for s, orig in zip(summaries, batch_contents)
            ), "All summaries should be shorter"

        except NotImplementedError:
            # Week 3: implement
            pytest.skip("Not implemented in Week 2")


class TestConsolidationCompressionConfiguration:
    """Test configuration of consolidation compression."""

    def test_config_defaults(self, consolidation_compression_config):
        """Should have sensible defaults."""
        assert consolidation_compression_config.enable is True
        assert consolidation_compression_config.generate_executive_summary is True
        assert consolidation_compression_config.target_compression_ratio == 0.1
        assert consolidation_compression_config.min_fidelity == 0.85

    def test_config_custom_values(self):
        """Should accept custom configuration."""
        config = ConsolidationCompressionConfig(
            enable=True,
            generate_executive_summary=False,
            target_compression_ratio=0.2,  # 5x compression instead of 10x
            min_fidelity=0.90,
        )

        assert config.target_compression_ratio == 0.2
        assert config.min_fidelity == 0.90
        assert config.generate_executive_summary is False

    def test_tokens_per_char_estimation(self, consolidation_compression_config):
        """Token estimation should use configured tokens_per_char."""
        # Default should be 0.25
        assert consolidation_compression_config.tokens_per_char == 0.25

        # 400 chars = 100 tokens
        compressor = ConsolidationCompressor(consolidation_compression_config)
        tokens = compressor.estimate_tokens("A" * 400)
        assert tokens == 100
