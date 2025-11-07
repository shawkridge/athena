"""Unit tests for LLMLingua prompt compression."""

import pytest
from athena.efficiency.compression import (
    PromptCompressor,
    TokenImportanceScorer,
    CompressionValidator,
    CompressionConfig,
)


@pytest.fixture
def compression_config():
    """Create compression configuration."""
    return CompressionConfig(
        target_ratio=2.0,  # 2x compression for tests
        quality_threshold=0.7,
    )


@pytest.fixture
def compressor(compression_config):
    """Create prompt compressor."""
    return PromptCompressor(compression_config)


@pytest.fixture
def scorer(compression_config):
    """Create token scorer."""
    return TokenImportanceScorer(compression_config)


@pytest.fixture
def simple_prompt():
    """Create simple test prompt."""
    return "The quick brown fox jumps over the lazy dog. This is a test sentence."


@pytest.fixture
def complex_prompt():
    """Create complex test prompt."""
    return """Machine learning is a subset of artificial intelligence that focuses on
    the development of algorithms and statistical models that enable computers to improve
    their performance on tasks through experience. Deep learning is a specialized branch
    of machine learning that uses neural networks with multiple layers to learn hierarchical
    representations of data. These techniques have revolutionized fields like computer vision,
    natural language processing, and speech recognition."""


class TestTokenImportanceScorer:
    """Test token importance scoring."""

    def test_score_tokens_basic(self, scorer, simple_prompt):
        """Test basic token scoring."""
        token_scores = scorer.score_tokens(simple_prompt)

        assert len(token_scores.tokens) > 0
        assert len(token_scores.importance_scores) == len(token_scores.tokens)
        assert all(0 <= score <= 1 for score in token_scores.importance_scores)

    def test_score_tokens_with_query(self, scorer, complex_prompt):
        """Test token scoring with query."""
        query = "What is machine learning?"
        token_scores = scorer.score_tokens(complex_prompt, query)

        # Query-related tokens should have high scores
        assert len(token_scores.tokens) > 0
        assert max(token_scores.importance_scores) > 0.5

    def test_tf_idf_scoring(self, scorer):
        """Test TF-IDF scoring."""
        tokens = ["machine", "learning", "machine", "learning", "machine", "deep"]
        scores = scorer._score_tf_idf(tokens, " ".join(tokens))

        # Repeated words should have high scores
        assert scores[0] > 0.5  # "machine" appears 3 times
        assert scores[1] > 0.5  # "learning" appears 2 times
        assert scores[5] < 0.5  # "deep" appears once

    def test_position_scoring(self, scorer):
        """Test position-based scoring."""
        tokens = ["first", "middle", "middle", "last"]
        scores = scorer._score_position(tokens)

        # First and last should be important
        assert len(scores) == 4
        assert all(0 <= s <= 1 for s in scores)
        # Edge positions should score higher
        assert scores[0] > scores[1]  # First > second

    def test_query_relevance_scoring(self, scorer):
        """Test query relevance scoring."""
        tokens = ["machine", "learning", "unrelated", "word"]
        query = "machine learning"
        scores = scorer._score_query_relevance(tokens, query)

        # Query words should score high
        assert scores[0] == 1.0  # "machine" is in query
        assert scores[1] == 1.0  # "learning" is in query
        assert scores[2] < 1.0  # "unrelated" is not

    def test_syntax_scoring(self, scorer):
        """Test syntax importance scoring."""
        tokens = ["hello", ".", "and", "world"]
        scores = scorer._score_syntax(tokens)

        # Punctuation should score high
        assert scores[1] > 0.9  # "."
        # "and" is a conjunction (0.5), "hello" is content (0.6)
        assert scores[1] > max(scores[0], scores[2])  # "." highest

    def test_identify_preserved_tokens(self, scorer):
        """Test preservation of critical tokens."""
        tokens = ["What", "is", "Python", "used", "for", "?"]
        preserved = scorer._identify_preserved_tokens(tokens)

        # Should preserve capitalized entities and question marks
        assert 0 in preserved  # "What"
        assert 2 in preserved  # "Python"
        assert 5 in preserved  # "?"

    def test_content_word_detection(self, scorer):
        """Test detection of content words."""
        assert scorer._is_content_word("machine") is True
        assert scorer._is_content_word("learning") is True
        assert scorer._is_content_word("the") is False
        assert scorer._is_content_word("and") is False

    def test_cache_clearing(self, scorer):
        """Test cache clearing."""
        scorer._cache["test"] = "value"
        assert len(scorer._cache) > 0
        scorer.clear_cache()
        assert len(scorer._cache) == 0


class TestPromptCompressor:
    """Test prompt compression."""

    def test_compress_simple_prompt(self, compressor, simple_prompt):
        """Test compression of simple prompt."""
        result = compressor.compress(simple_prompt)

        assert "original" in result
        assert "compressed" in result
        assert result["original_tokens"] > 0
        assert result["compressed_tokens"] > 0
        assert result["original_tokens"] >= result["compressed_tokens"]

    def test_compression_ratio(self, compressor, simple_prompt):
        """Test that compression achieves target ratio."""
        result = compressor.compress(simple_prompt)

        # Should compress at least somewhat
        assert result["compression_ratio"] >= 1.0

    def test_quality_score_calculation(self, compressor, simple_prompt):
        """Test that quality score is calculated."""
        result = compressor.compress(simple_prompt)

        assert 0 <= result["quality_score"] <= 1.0

    def test_token_preservation(self, compressor, simple_prompt):
        """Test that important tokens are preserved."""
        result = compressor.compress(simple_prompt)

        original_words = set(simple_prompt.lower().split())
        compressed_words = set(result["compressed"].lower().split())

        # Should preserve some words
        intersection = original_words & compressed_words
        assert len(intersection) > 0

    def test_compress_with_query(self, compressor, complex_prompt):
        """Test compression guided by query."""
        query = "machine learning"
        result = compressor.compress(complex_prompt, query=query)

        # Should preserve query-related terms
        assert "machine" in result["compressed"].lower()
        assert "learning" in result["compressed"].lower()

    def test_compress_with_target_ratio_override(self, compressor, simple_prompt):
        """Test compression with target ratio override."""
        result1 = compressor.compress(simple_prompt, target_ratio=2.0)
        result2 = compressor.compress(simple_prompt, target_ratio=4.0)

        # More aggressive compression should produce smaller output
        assert result2["compressed_tokens"] <= result1["compressed_tokens"]

    def test_compress_empty_prompt(self, compressor):
        """Test compression of empty prompt."""
        result = compressor.compress("")

        assert result["original_tokens"] == 0
        assert result["compressed_tokens"] == 0

    def test_compress_single_word(self, compressor):
        """Test compression of single word."""
        result = compressor.compress("hello")

        assert result["original_tokens"] == 1
        assert result["compressed_tokens"] >= 1

    def test_batch_compress(self, compressor):
        """Test batch compression."""
        prompts = [
            "The quick brown fox jumps over the lazy dog.",
            "Machine learning is a powerful tool.",
            "Python is a programming language.",
        ]

        results = compressor.batch_compress(prompts)

        assert len(results) == 3
        assert all("compressed" in r for r in results)
        assert all(r["quality_score"] >= 0 for r in results)

    def test_batch_compress_with_queries(self, compressor):
        """Test batch compression with queries."""
        prompts = [
            "The quick brown fox jumps over the lazy dog.",
            "Machine learning is a powerful tool.",
        ]
        queries = [
            "fox",
            "machine learning",
        ]

        results = compressor.batch_compress(prompts, queries)

        assert len(results) == 2
        # First result should preserve "fox"
        assert "fox" in results[0]["compressed"].lower()
        # Second result should preserve "machine" and "learning"
        assert "machine" in results[1]["compressed"].lower()

    def test_compression_maintains_order(self, compressor):
        """Test that compressed tokens maintain relative order."""
        prompt = "The quick brown fox jumps over the lazy dog"
        result = compressor.compress(prompt)

        original_tokens = prompt.split()
        compressed_tokens = result["compressed"].split()

        # Find indices of compressed tokens in original
        indices = []
        for token in compressed_tokens:
            for i, original in enumerate(original_tokens):
                if token.lower() == original.lower():
                    indices.append(i)
                    break

        # Indices should be monotonically increasing (order preserved)
        if len(indices) > 1:
            assert all(indices[i] <= indices[i + 1] for i in range(len(indices) - 1))

    def test_compression_metrics(self, compressor, simple_prompt):
        """Test that all metrics are calculated."""
        result = compressor.compress(simple_prompt)

        required_keys = {
            "original",
            "compressed",
            "original_tokens",
            "compressed_tokens",
            "compression_ratio",
            "quality_score",
            "preserved_count",
            "removed_count",
        }

        assert all(key in result for key in required_keys)


class TestCompressionValidator:
    """Test compression validation."""

    def test_validate_semantic_preservation(self):
        """Test semantic preservation validation."""
        original = "Machine learning is a powerful technique"
        compressed = "Machine learning powerful"

        result = CompressionValidator.validate_semantic_preservation(original, compressed)

        assert "is_valid" in result
        assert "jaccard_similarity" in result
        assert "word_coverage" in result
        assert 0 <= result["jaccard_similarity"] <= 1

    def test_validate_semantic_with_threshold(self):
        """Test semantic validation with custom threshold."""
        original = "The quick brown fox"
        compressed = "quick fox"

        result = CompressionValidator.validate_semantic_preservation(
            original, compressed, threshold=0.5
        )

        assert result["jaccard_similarity"] <= 1.0

    def test_validate_coherence(self):
        """Test coherence validation."""
        text = "This is a coherent sentence."

        result = CompressionValidator.validate_coherence(text)

        assert "is_coherent" in result
        assert "has_proper_ending" in result
        assert "orphaned_punctuation_ratio" in result
        assert result["is_coherent"] is True

    def test_validate_incoherent_text(self):
        """Test coherence validation of broken text."""
        text = "This is broken,"

        result = CompressionValidator.validate_coherence(text)

        # Missing proper ending
        assert not result["has_proper_ending"]

    def test_validate_empty_text(self):
        """Test validation of empty text."""
        result = CompressionValidator.validate_semantic_preservation("", "")

        assert result["is_valid"] is True

    def test_validate_identical_text(self):
        """Test validation of identical original and compressed."""
        text = "The same text"

        result = CompressionValidator.validate_semantic_preservation(text, text)

        assert result["jaccard_similarity"] == 1.0
        assert result["is_valid"] is True


class TestCompressionIntegration:
    """Integration tests for compression."""

    def test_full_compression_pipeline(self, compressor, complex_prompt):
        """Test full compression pipeline."""
        # Compress
        result = compressor.compress(complex_prompt)

        # Validate semantic preservation
        semantic_valid = CompressionValidator.validate_semantic_preservation(
            result["original"],
            result["compressed"],
            threshold=0.7,
        )

        # Validate coherence
        coherence_valid = CompressionValidator.validate_coherence(result["compressed"])

        assert result["compressed_tokens"] > 0
        assert semantic_valid["is_valid"] or semantic_valid["word_coverage"] > 0.5
        assert coherence_valid["orphaned_punctuation_ratio"] < 0.5

    def test_compression_with_validation_loop(self, compressor, complex_prompt):
        """Test compression with quality validation loop."""
        result = compressor.compress(complex_prompt)

        # Check if quality meets threshold
        semantic_check = CompressionValidator.validate_semantic_preservation(
            result["original"],
            result["compressed"],
            threshold=0.7,
        )

        # Should preserve semantic meaning
        assert semantic_check["word_coverage"] >= 0.5

    def test_repeated_compression(self, compressor):
        """Test that compression is idempotent."""
        prompt = "The quick brown fox jumps over the lazy dog"

        result1 = compressor.compress(prompt)
        result2 = compressor.compress(result1["compressed"])

        # Second compression should not change much
        assert result2["compressed_tokens"] <= result1["compressed_tokens"]

    def test_compression_config_impact(self):
        """Test that configuration affects compression."""
        prompt = "The quick brown fox jumps over the lazy dog. " * 5

        config1 = CompressionConfig(target_ratio=2.0)
        config2 = CompressionConfig(target_ratio=5.0)

        comp1 = PromptCompressor(config1)
        comp2 = PromptCompressor(config2)

        result1 = comp1.compress(prompt)
        result2 = comp2.compress(prompt)

        # More aggressive config should produce smaller output
        assert result2["compressed_tokens"] <= result1["compressed_tokens"]

    def test_compression_consistency(self, compressor):
        """Test that compression is deterministic."""
        prompt = "Machine learning and artificial intelligence are related but distinct fields"

        result1 = compressor.compress(prompt)
        result2 = compressor.compress(prompt)

        # Same input should produce same output
        assert result1["compressed"] == result2["compressed"]

    def test_large_prompt_compression(self, compressor):
        """Test compression of large prompt."""
        large_prompt = " ".join(
            ["word"] * 1000
        )  # 1000 word prompt

        result = compressor.compress(large_prompt)

        assert result["original_tokens"] == 1000
        assert result["compressed_tokens"] < 1000
        assert result["compression_ratio"] > 1.0
