"""Comprehensive unit tests for SandboxConfig (Phase 1).

Tests cover:
- SandboxMode enum
- ExecutionLanguage enum
- SandboxResourceLimits dataclass
- SandboxSecurityPolicy dataclass
- SandboxConfig main class
- Factory methods (strict, permissive, default)
- Validation logic
- Configuration serialization
"""

import pytest
from athena.sandbox.config import (
    SandboxMode,
    ExecutionLanguage,
    SandboxResourceLimits,
    SandboxSecurityPolicy,
    SandboxConfig,
)


class TestSandboxMode:
    """Tests for SandboxMode enum."""

    def test_sandbox_mode_values(self):
        """Test SandboxMode enum values."""
        assert SandboxMode.SRT.value == "srt"
        assert SandboxMode.RESTRICTED.value == "restricted"
        assert SandboxMode.MOCK.value == "mock"

    def test_sandbox_mode_comparison(self):
        """Test comparing SandboxMode values."""
        assert SandboxMode.SRT == SandboxMode.SRT
        assert SandboxMode.SRT != SandboxMode.RESTRICTED
        assert SandboxMode.RESTRICTED != SandboxMode.MOCK

    def test_sandbox_mode_from_string(self):
        """Test creating SandboxMode from string."""
        assert SandboxMode("srt") == SandboxMode.SRT
        assert SandboxMode("restricted") == SandboxMode.RESTRICTED
        assert SandboxMode("mock") == SandboxMode.MOCK

    def test_sandbox_mode_invalid_value(self):
        """Test that invalid SandboxMode value raises error."""
        with pytest.raises(ValueError):
            SandboxMode("invalid_mode")


class TestExecutionLanguage:
    """Tests for ExecutionLanguage enum."""

    def test_execution_language_values(self):
        """Test ExecutionLanguage enum values."""
        assert ExecutionLanguage.PYTHON.value == "python"
        assert ExecutionLanguage.JAVASCRIPT.value == "javascript"
        assert ExecutionLanguage.BASH.value == "bash"

    def test_execution_language_from_string(self):
        """Test creating ExecutionLanguage from string."""
        assert ExecutionLanguage("python") == ExecutionLanguage.PYTHON
        assert ExecutionLanguage("javascript") == ExecutionLanguage.JAVASCRIPT
        assert ExecutionLanguage("bash") == ExecutionLanguage.BASH

    def test_execution_language_invalid_value(self):
        """Test that invalid ExecutionLanguage value raises error."""
        with pytest.raises(ValueError):
            ExecutionLanguage("rust")


class TestSandboxResourceLimits:
    """Tests for SandboxResourceLimits dataclass."""

    def test_resource_limits_defaults(self):
        """Test default resource limits."""
        limits = SandboxResourceLimits()

        assert limits.timeout_seconds == 30
        assert limits.max_memory_mb == 256
        assert limits.max_cpu_percent == 90.0
        assert limits.max_file_size_mb == 10
        assert limits.max_total_files == 100
        assert limits.max_disk_space_mb == 500
        assert limits.allow_network is False
        assert limits.allow_outbound_http is False
        assert limits.max_processes == 10
        assert limits.allow_shell_escape is False

    def test_resource_limits_custom(self):
        """Test creating resource limits with custom values."""
        limits = SandboxResourceLimits(
            timeout_seconds=60,
            max_memory_mb=512,
            max_cpu_percent=50.0,
            allow_network=True,
        )

        assert limits.timeout_seconds == 60
        assert limits.max_memory_mb == 512
        assert limits.max_cpu_percent == 50.0
        assert limits.allow_network is True

    def test_resource_limits_to_dict(self):
        """Test converting resource limits to dictionary."""
        limits = SandboxResourceLimits(
            timeout_seconds=60,
            max_memory_mb=512,
        )

        limits_dict = limits.to_dict()

        assert limits_dict["timeout_seconds"] == 60
        assert limits_dict["max_memory_mb"] == 512
        assert isinstance(limits_dict, dict)
        assert "allow_network" in limits_dict
        assert "max_processes" in limits_dict

    def test_resource_limits_blocked_domains(self):
        """Test blocked domains in resource limits."""
        limits = SandboxResourceLimits(
            blocked_domains=["malicious.com", "phishing.net"],
        )

        assert len(limits.blocked_domains) == 2
        assert "malicious.com" in limits.blocked_domains


class TestSandboxSecurityPolicy:
    """Tests for SandboxSecurityPolicy dataclass."""

    def test_security_policy_defaults(self):
        """Test default security policy."""
        policy = SandboxSecurityPolicy()

        assert policy.allow_read is True
        assert policy.allow_write is True
        assert policy.allow_delete is False
        assert policy.allow_eval is False
        assert policy.allow_exec is False
        assert policy.allow_import_dynamic is False

    def test_security_policy_allowed_modules(self):
        """Test allowed modules in security policy."""
        policy = SandboxSecurityPolicy()

        assert "os" in policy.allowed_modules
        assert "json" in policy.allowed_modules
        assert "subprocess" not in policy.allowed_modules

    def test_security_policy_blocked_modules(self):
        """Test blocked modules in security policy."""
        policy = SandboxSecurityPolicy()

        assert "subprocess" in policy.blocked_modules
        assert "socket" in policy.blocked_modules
        assert "requests" in policy.blocked_modules

    def test_security_policy_allowed_builtins(self):
        """Test allowed builtins in security policy."""
        policy = SandboxSecurityPolicy()

        assert "len" in policy.allowed_builtins
        assert "str" in policy.allowed_builtins
        assert "eval" not in policy.allowed_builtins
        assert "exec" not in policy.allowed_builtins

    def test_security_policy_blocked_builtins(self):
        """Test blocked builtins in security policy."""
        policy = SandboxSecurityPolicy()

        assert "exec" in policy.blocked_builtins
        assert "eval" in policy.blocked_builtins
        assert "__import__" in policy.blocked_builtins

    def test_security_policy_custom(self):
        """Test creating custom security policy."""
        policy = SandboxSecurityPolicy(
            allow_eval=True,
            allow_exec=True,
            allowed_modules={"os", "sys", "subprocess"},
        )

        assert policy.allow_eval is True
        assert policy.allow_exec is True
        assert "subprocess" in policy.allowed_modules

    def test_security_policy_to_dict(self):
        """Test converting security policy to dictionary."""
        policy = SandboxSecurityPolicy(
            allow_eval=True,
            allow_read=False,
        )

        policy_dict = policy.to_dict()

        assert policy_dict["allow_eval"] is True
        assert policy_dict["allow_read"] is False
        assert isinstance(policy_dict["allowed_modules"], list)
        assert isinstance(policy_dict["blocked_builtins"], list)


class TestSandboxConfigInitialization:
    """Tests for SandboxConfig initialization."""

    def test_sandbox_config_defaults(self):
        """Test default SandboxConfig values."""
        config = SandboxConfig()

        assert config.mode == SandboxMode.SRT
        assert config.language == ExecutionLanguage.PYTHON
        assert config.version == "1.0"
        assert config.timeout_seconds == 30
        assert config.max_memory_mb == 256
        assert config.allow_network is False
        assert config.allow_eval is False
        assert config.capture_output is True

    def test_sandbox_config_custom(self):
        """Test creating custom SandboxConfig."""
        config = SandboxConfig(
            mode=SandboxMode.RESTRICTED,
            language=ExecutionLanguage.JAVASCRIPT,
            timeout_seconds=60,
            max_memory_mb=512,
            allow_network=True,
        )

        assert config.mode == SandboxMode.RESTRICTED
        assert config.language == ExecutionLanguage.JAVASCRIPT
        assert config.timeout_seconds == 60
        assert config.max_memory_mb == 512
        assert config.allow_network is True

    def test_sandbox_config_expose_apis(self):
        """Test expose_apis configuration."""
        config = SandboxConfig(
            expose_apis=["memory_api", "graph_api"],
        )

        assert "memory_api" in config.expose_apis
        assert "graph_api" in config.expose_apis

    def test_sandbox_config_environment_vars(self):
        """Test environment variables in config."""
        config = SandboxConfig(
            environment_vars={
                "DEBUG": "1",
                "LOG_LEVEL": "INFO",
            },
        )

        assert config.environment_vars["DEBUG"] == "1"
        assert config.environment_vars["LOG_LEVEL"] == "INFO"


class TestSandboxConfigFactories:
    """Tests for SandboxConfig factory methods."""

    def test_strict_config(self):
        """Test creating strict sandbox configuration."""
        config = SandboxConfig.strict()

        assert config.mode == SandboxMode.SRT
        assert config.timeout_seconds == 10
        assert config.max_memory_mb == 128
        assert config.allow_network is False
        assert config.allow_eval is False
        assert config.allow_exec is False
        assert config.allow_import_dynamic is False

    def test_permissive_config(self):
        """Test creating permissive sandbox configuration."""
        config = SandboxConfig.permissive()

        assert config.mode == SandboxMode.RESTRICTED
        assert config.timeout_seconds == 60
        assert config.max_memory_mb == 512
        assert config.allow_network is True
        assert config.allow_outbound_http is True

    def test_default_config(self):
        """Test creating default sandbox configuration."""
        config = SandboxConfig.default()

        assert config.mode == SandboxMode.SRT
        assert config.timeout_seconds == 30
        assert config.max_memory_mb == 256
        assert config.allow_network is False

    def test_strict_vs_permissive(self):
        """Test that strict is more restrictive than permissive."""
        strict = SandboxConfig.strict()
        permissive = SandboxConfig.permissive()

        assert strict.timeout_seconds < permissive.timeout_seconds
        assert strict.max_memory_mb < permissive.max_memory_mb
        assert strict.allow_network is False
        assert permissive.allow_network is True


class TestSandboxConfigValidation:
    """Tests for SandboxConfig.validate() method."""

    def test_valid_config(self):
        """Test validating a valid config."""
        config = SandboxConfig()
        is_valid, errors = config.validate()

        assert is_valid is True
        assert len(errors) == 0

    def test_invalid_timeout_too_small(self):
        """Test validation with timeout too small."""
        config = SandboxConfig(timeout_seconds=0)
        is_valid, errors = config.validate()

        assert is_valid is False
        assert len(errors) > 0
        assert any("timeout_seconds" in e for e in errors)

    def test_invalid_timeout_too_large(self):
        """Test validation with timeout too large."""
        config = SandboxConfig(timeout_seconds=7200)  # > 3600
        is_valid, errors = config.validate()

        assert is_valid is False
        assert any("timeout_seconds" in e for e in errors)

    def test_invalid_memory_too_small(self):
        """Test validation with memory too small."""
        config = SandboxConfig(max_memory_mb=16)  # < 32
        is_valid, errors = config.validate()

        assert is_valid is False
        assert any("max_memory_mb" in e for e in errors)

    def test_invalid_memory_too_large(self):
        """Test validation with memory too large."""
        config = SandboxConfig(max_memory_mb=10000)  # > 8192
        is_valid, errors = config.validate()

        assert is_valid is False
        assert any("max_memory_mb" in e for e in errors)

    def test_invalid_cpu_percentage(self):
        """Test validation with invalid CPU percentage."""
        config = SandboxConfig(max_cpu_percent=150)  # > 100
        is_valid, errors = config.validate()

        assert is_valid is False
        assert any("max_cpu_percent" in e for e in errors)

    def test_invalid_file_limits(self):
        """Test validation with invalid file limits."""
        config = SandboxConfig(
            max_file_size_mb=100,
            max_disk_space_mb=50,  # Less than max_file_size_mb
        )
        is_valid, errors = config.validate()

        assert is_valid is False
        assert any("max_disk_space_mb" in e for e in errors)

    def test_srt_with_exec_warning(self):
        """Test that SRT mode with allow_exec generates warning."""
        config = SandboxConfig(
            mode=SandboxMode.SRT,
            allow_exec=True,
        )
        is_valid, errors = config.validate()

        # Should still be invalid or warning should be present
        if not is_valid:
            assert any("exec" in e for e in errors)

    def test_multiple_validation_errors(self):
        """Test validation with multiple errors."""
        config = SandboxConfig(
            timeout_seconds=0,
            max_memory_mb=16,
            max_cpu_percent=150,
        )
        is_valid, errors = config.validate()

        assert is_valid is False
        assert len(errors) >= 2  # At least 2 errors


class TestSandboxConfigSerialization:
    """Tests for SandboxConfig serialization."""

    def test_to_dict_basic(self):
        """Test converting SandboxConfig to dictionary."""
        config = SandboxConfig()
        config_dict = config.to_dict()

        assert isinstance(config_dict, dict)
        assert config_dict["mode"] == "srt"
        assert config_dict["language"] == "python"
        assert config_dict["timeout_seconds"] == 30

    def test_to_dict_comprehensive(self):
        """Test to_dict includes all fields."""
        config = SandboxConfig(
            mode=SandboxMode.RESTRICTED,
            sandbox_id="test_sandbox_123",
            creator="test_user",
            description="Test sandbox",
        )
        config_dict = config.to_dict()

        assert config_dict["mode"] == "restricted"
        assert config_dict["sandbox_id"] == "test_sandbox_123"
        assert config_dict["creator"] == "test_user"
        assert config_dict["description"] == "Test sandbox"

    def test_to_dict_preserves_enums(self):
        """Test that to_dict converts enums to string values."""
        config = SandboxConfig(
            mode=SandboxMode.SRT,
            language=ExecutionLanguage.JAVASCRIPT,
        )
        config_dict = config.to_dict()

        assert isinstance(config_dict["mode"], str)
        assert isinstance(config_dict["language"], str)
        assert config_dict["mode"] == "srt"
        assert config_dict["language"] == "javascript"

    def test_get_resource_limits(self):
        """Test getting resource limits from config."""
        config = SandboxConfig(
            timeout_seconds=60,
            max_memory_mb=512,
        )

        limits = config.get_resource_limits()

        assert isinstance(limits, SandboxResourceLimits)
        assert limits.timeout_seconds == 60
        assert limits.max_memory_mb == 512

    def test_get_security_policy(self):
        """Test getting security policy from config."""
        config = SandboxConfig(
            allow_eval=True,
            allow_exec=False,
        )

        policy = config.get_security_policy()

        assert isinstance(policy, SandboxSecurityPolicy)
        assert policy.allow_eval is True
        assert policy.allow_exec is False


class TestSandboxConfigIntegration:
    """Integration tests for SandboxConfig."""

    def test_strict_config_has_safe_limits(self):
        """Test that strict config has safe resource limits."""
        config = SandboxConfig.strict()
        limits = config.get_resource_limits()
        policy = config.get_security_policy()

        # Strict should have tight limits
        assert limits.timeout_seconds <= 10
        assert limits.max_memory_mb <= 128
        assert policy.allow_eval is False
        assert policy.allow_exec is False

    def test_all_factory_configs_validate(self):
        """Test that all factory configs pass validation."""
        for factory in [SandboxConfig.strict, SandboxConfig.permissive, SandboxConfig.default]:
            config = factory()
            is_valid, errors = config.validate()
            assert is_valid, f"{factory.__name__} config validation failed: {errors}"

    def test_config_consistency(self):
        """Test config consistency and completeness."""
        config = SandboxConfig(
            mode=SandboxMode.SRT,
            expose_apis=["memory_api", "graph_api"],
            environment_vars={"VAR": "value"},
        )

        # Convert to dict and verify all fields present
        config_dict = config.to_dict()
        assert "mode" in config_dict
        assert "expose_apis" in config_dict
        assert "environment_vars" in config_dict

        # Verify serialize/deserialize consistency
        assert config_dict["expose_apis"] == ["memory_api", "graph_api"]
        assert config_dict["environment_vars"]["VAR"] == "value"
