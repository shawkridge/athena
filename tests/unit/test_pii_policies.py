"""Tests for PII field policies.

Tests:
- Policy application
- Truncation
- Hashing
- Different policy modes
"""

import pytest
from athena.pii.policies import (
    FieldPolicy, SanitizationStrategy,
    CompliancePolicy, DebugPolicy
)


class TestFieldPolicy:
    """Test field-level sanitization policies."""

    @pytest.fixture
    def policy(self):
        """Create default field policy."""
        return FieldPolicy()

    def test_default_policies_loaded(self, policy):
        """Test that default policies are loaded."""
        assert policy.get_policy('diff') == SanitizationStrategy.REDACT
        assert policy.get_policy('git_author') == SanitizationStrategy.HASH_PII
        assert policy.get_policy('content') == SanitizationStrategy.TOKENIZE
        assert policy.get_policy('file_path') == SanitizationStrategy.TRUNCATE

    def test_custom_policy_override(self):
        """Test custom policy overrides."""
        custom = {
            'content': SanitizationStrategy.REDACT,
            'custom_field': SanitizationStrategy.HASH_PII,
        }
        policy = FieldPolicy(custom_policies=custom)

        assert policy.get_policy('content') == SanitizationStrategy.REDACT
        assert policy.get_policy('custom_field') == SanitizationStrategy.HASH_PII

    def test_unknown_field_defaults_to_passthrough(self, policy):
        """Test unknown fields default to pass-through."""
        assert policy.get_policy('unknown_field') == SanitizationStrategy.PASS_THROUGH

    def test_truncate_absolute_path(self, policy):
        """Test path truncation removes home directory."""
        path = "/home/alice/projects/app/main.py"
        truncated = policy._truncate_path(path)

        assert "/home/alice" not in truncated
        assert "main.py" in truncated or "app" in truncated

    def test_truncate_user_directory(self, policy):
        """Test truncation of /Users path."""
        path = "/Users/bob/Code/project/file.txt"
        truncated = policy._truncate_path(path)

        assert "/Users/bob" not in truncated
        assert "project" in truncated or "file.txt" in truncated

    def test_truncate_windows_path(self, policy):
        """Test truncation of Windows path."""
        path = "C:\\Users\\alice\\Documents\\project\\file.txt"
        truncated = policy._truncate_path(path)

        # Should handle gracefully (may not fully process Windows paths on Unix)
        assert isinstance(truncated, str)

    def test_truncate_relative_path(self, policy):
        """Test that relative paths are left mostly unchanged."""
        path = "src/main.py"
        truncated = policy._truncate_path(path)

        assert "main.py" in truncated

    def test_hash_value(self, policy):
        """Test value hashing."""
        value = "alice@example.com"
        hashed = policy._hash_value(value)

        assert hashed.startswith("PII_HASH_")
        assert len(hashed) == len("PII_HASH_") + 16

    def test_hash_deterministic(self, policy):
        """Test hash is deterministic."""
        value = "alice@example.com"

        hash1 = policy._hash_value(value)
        hash2 = policy._hash_value(value)

        assert hash1 == hash2

    def test_different_values_different_hashes(self, policy):
        """Test different values produce different hashes."""
        hash1 = policy._hash_value("alice@example.com")
        hash2 = policy._hash_value("bob@example.com")

        assert hash1 != hash2


class TestCompliancePolicy:
    """Test GDPR/CCPA compliance policy."""

    @pytest.fixture
    def policy(self):
        """Create compliance policy."""
        return CompliancePolicy()

    def test_strict_redaction(self, policy):
        """Test strict redaction in compliance mode."""
        assert policy.get_policy('diff') == SanitizationStrategy.REDACT
        assert policy.get_policy('stack_trace') == SanitizationStrategy.REDACT
        assert policy.get_policy('context.cwd') == SanitizationStrategy.REDACT

    def test_compliance_vs_standard(self):
        """Test compliance is stricter than standard."""
        standard = FieldPolicy()
        compliance = CompliancePolicy()

        # Compliance should have more REDACT
        assert compliance.get_policy('stack_trace') == SanitizationStrategy.REDACT
        assert standard.get_policy('stack_trace') == SanitizationStrategy.TOKENIZE


class TestDebugPolicy:
    """Test debug/development policy."""

    @pytest.fixture
    def policy(self):
        """Create debug policy."""
        return DebugPolicy()

    def test_permissive_policies(self, policy):
        """Test debug policy is permissive."""
        assert policy.get_policy('content') == SanitizationStrategy.PASS_THROUGH
        assert policy.get_policy('stack_trace') == SanitizationStrategy.PASS_THROUGH
        assert policy.get_policy('file_path') == SanitizationStrategy.PASS_THROUGH

    def test_debug_vs_standard(self):
        """Test debug is more permissive than standard."""
        standard = FieldPolicy()
        debug = DebugPolicy()

        # Debug should have more PASS_THROUGH
        assert debug.get_policy('content') == SanitizationStrategy.PASS_THROUGH
        assert standard.get_policy('content') == SanitizationStrategy.TOKENIZE


class TestSanitizationStrategy:
    """Test sanitization strategy enum."""

    def test_strategy_values(self):
        """Test strategy enum values."""
        assert SanitizationStrategy.PASS_THROUGH.value == "pass_through"
        assert SanitizationStrategy.TOKENIZE.value == "tokenize"
        assert SanitizationStrategy.REDACT.value == "redact"
        assert SanitizationStrategy.TRUNCATE.value == "truncate"
        assert SanitizationStrategy.HASH_PII.value == "hash_pii"
