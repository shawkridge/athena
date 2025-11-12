"""Tests for PII tokenizer.

Tests:
- Hash-based tokenization (deterministic)
- Index-based tokenization
- Type-based tokenization
- Token consistency
- Event tokenization
"""

import pytest
from athena.pii.tokenizer import PIITokenizer, DeterministicTokenizer
from athena.pii.detector import PIIDetection


class TestPIITokenizer:
    """Test PII tokenization functionality."""

    @pytest.fixture
    def hash_tokenizer(self):
        """Create hash-based tokenizer."""
        return PIITokenizer(strategy='hash')

    @pytest.fixture
    def index_tokenizer(self):
        """Create index-based tokenizer."""
        return PIITokenizer(strategy='index')

    @pytest.fixture
    def type_tokenizer(self):
        """Create type-based tokenizer."""
        return PIITokenizer(strategy='type')

    def test_hash_tokenizer_creates_tokens(self, hash_tokenizer):
        """Test hash tokenizer creates tokens."""
        text = "Email: alice@example.com"
        detections = [
            PIIDetection(
                type='email',
                value='alice@example.com',
                start_pos=7,
                end_pos=24,
                confidence=0.95,
                field_name='content'
            )
        ]

        tokenized = hash_tokenizer.tokenize(text, detections)

        assert 'alice@example.com' not in tokenized
        assert 'PII_HASH_' in tokenized

    def test_index_tokenizer_creates_sequential_tokens(self, index_tokenizer):
        """Test index tokenizer creates sequential tokens."""
        text = "Email: alice@example.com and bob@example.com"
        detections = [
            PIIDetection(
                type='email',
                value='alice@example.com',
                start_pos=7,
                end_pos=24,
                confidence=0.95,
                field_name='content'
            ),
            PIIDetection(
                type='email',
                value='bob@example.com',
                start_pos=29,
                end_pos=44,
                confidence=0.95,
                field_name='content'
            )
        ]

        tokenized = index_tokenizer.tokenize(text, detections)

        assert 'PII_ID_1' in tokenized
        assert 'PII_ID_2' in tokenized

    def test_type_tokenizer_creates_type_tokens(self, type_tokenizer):
        """Test type tokenizer creates type-based tokens."""
        text = "Email: alice@example.com"
        detections = [
            PIIDetection(
                type='email',
                value='alice@example.com',
                start_pos=7,
                end_pos=24,
                confidence=0.95,
                field_name='content'
            )
        ]

        tokenized = type_tokenizer.tokenize(text, detections)

        assert 'EMAIL_MASKED' in tokenized
        assert 'alice@example.com' not in tokenized

    def test_empty_detections_returns_original(self, hash_tokenizer):
        """Test that empty detections return original text."""
        text = "This is clean text"
        detections = []

        tokenized = hash_tokenizer.tokenize(text, detections)

        assert tokenized == text

    def test_hash_tokenization_is_deterministic(self, hash_tokenizer):
        """Test hash tokenization is deterministic."""
        text = "Email: alice@example.com"
        detection = PIIDetection(
            type='email',
            value='alice@example.com',
            start_pos=7,
            end_pos=24,
            confidence=0.95,
            field_name='content'
        )

        tokenized1 = hash_tokenizer.tokenize(text, [detection])
        tokenized2 = hash_tokenizer.tokenize(text, [detection])

        # Same input should produce same output
        assert tokenized1 == tokenized2

    def test_different_pii_produces_different_tokens(self, hash_tokenizer):
        """Test different PII produces different tokens."""
        detection1 = PIIDetection(
            type='email',
            value='alice@example.com',
            start_pos=0,
            end_pos=17,
            confidence=0.95,
            field_name='content'
        )
        detection2 = PIIDetection(
            type='email',
            value='bob@example.com',
            start_pos=0,
            end_pos=15,
            confidence=0.95,
            field_name='content'
        )

        token1 = hash_tokenizer._hash_token(detection1)
        token2 = hash_tokenizer._hash_token(detection2)

        assert token1 != token2

    def test_is_token_hash(self, hash_tokenizer):
        """Test is_token() for hash tokens."""
        assert hash_tokenizer.is_token('PII_HASH_abc123ef')
        assert not hash_tokenizer.is_token('alice@example.com')
        assert not hash_tokenizer.is_token('normal text')

    def test_is_token_index(self, index_tokenizer):
        """Test is_token() for index tokens."""
        assert index_tokenizer.is_token('PII_ID_1')
        assert index_tokenizer.is_token('PII_ID_999')
        assert not index_tokenizer.is_token('alice@example.com')

    def test_is_token_type(self, type_tokenizer):
        """Test is_token() for type tokens."""
        assert type_tokenizer.is_token('EMAIL_MASKED')
        assert type_tokenizer.is_token('PATH_MASKED')
        assert not type_tokenizer.is_token('alice@example.com')

    def test_multiple_pii_in_text(self, hash_tokenizer):
        """Test tokenization of multiple PII in same text."""
        text = "alice@example.com works at /home/alice/company"
        detections = [
            PIIDetection(
                type='email',
                value='alice@example.com',
                start_pos=0,
                end_pos=17,
                confidence=0.95,
                field_name='content'
            ),
            PIIDetection(
                type='absolute_path',
                value='/home/alice',
                start_pos=29,
                end_pos=40,
                confidence=0.90,
                field_name='content'
            )
        ]

        tokenized = hash_tokenizer.tokenize(text, detections)

        assert 'alice@example.com' not in tokenized
        assert '/home/alice' not in tokenized
        assert 'PII_HASH_' in tokenized

    def test_overlapping_detections(self, hash_tokenizer):
        """Test handling of overlapping detections."""
        text = "path /home/alice/file.txt"
        detections = [
            PIIDetection(
                type='absolute_path',
                value='/home/alice',
                start_pos=6,
                end_pos=17,
                confidence=0.90,
                field_name='content'
            )
        ]

        # Should handle without errors
        tokenized = hash_tokenizer.tokenize(text, detections)
        assert '/home/alice' not in tokenized

    def test_invalid_strategy_raises_error(self):
        """Test that invalid strategy raises error."""
        with pytest.raises(ValueError):
            PIITokenizer(strategy='invalid')

    def test_custom_salt_affects_tokens(self):
        """Test that custom salt changes token output."""
        detection = PIIDetection(
            type='email',
            value='alice@example.com',
            start_pos=0,
            end_pos=17,
            confidence=0.95,
            field_name='content'
        )

        tokenizer1 = PIITokenizer(strategy='hash', salt='salt1')
        tokenizer2 = PIITokenizer(strategy='hash', salt='salt2')

        token1 = tokenizer1._hash_token(detection)
        token2 = tokenizer2._hash_token(detection)

        # Different salts should produce different tokens
        assert token1 != token2


class TestDeterministicTokenizer:
    """Test deterministic tokenizer."""

    @pytest.fixture
    def deterministic_tokenizer(self):
        """Create deterministic tokenizer."""
        return DeterministicTokenizer()

    def test_tokenize_deterministic(self, deterministic_tokenizer):
        """Test deterministic tokenization."""
        text = "Contact alice@example.com"
        pii_values = ['alice@example.com']

        tokenized = deterministic_tokenizer.tokenize_deterministic(text, pii_values)

        assert 'alice@example.com' not in tokenized
        assert 'PII_HASH_' in tokenized

    def test_deterministic_consistency(self, deterministic_tokenizer):
        """Test that same PII always produces same token."""
        pii_value = 'alice@example.com'

        token1 = deterministic_tokenizer._hash_token_from_value(pii_value)
        token2 = deterministic_tokenizer._hash_token_from_value(pii_value)

        assert token1 == token2

    def test_deterministic_different_values(self, deterministic_tokenizer):
        """Test different values produce different tokens."""
        token1 = deterministic_tokenizer._hash_token_from_value('alice@example.com')
        token2 = deterministic_tokenizer._hash_token_from_value('bob@example.com')

        assert token1 != token2

    def test_deterministic_multiple_replacements(self, deterministic_tokenizer):
        """Test multiple PII replacements."""
        text = "alice@example.com and bob@example.com"
        pii_values = ['alice@example.com', 'bob@example.com']

        tokenized = deterministic_tokenizer.tokenize_deterministic(text, pii_values)

        assert 'alice@example.com' not in tokenized
        assert 'bob@example.com' not in tokenized
        assert tokenized.count('PII_HASH_') == 2

    def test_deterministic_substring_handling(self, deterministic_tokenizer):
        """Test that substrings aren't double-replaced."""
        text = "alice@example.com appears twice: alice@example.com"
        pii_values = ['alice@example.com']

        tokenized = deterministic_tokenizer.tokenize_deterministic(text, pii_values)

        # Both occurrences should be replaced with same token
        assert tokenized.count('PII_HASH_') == 2
        # Split on the token to check we have the same token twice
        parts = tokenized.split('PII_HASH_')
        assert parts[1][:16] == parts[2][:16]  # Same hash
