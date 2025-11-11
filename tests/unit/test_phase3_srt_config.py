"""Unit tests for SRT configuration manager.

Tests configuration building, filesystem rules, network policies,
and environment variable management.
"""

import json
import os
import tempfile
import pytest

from athena.sandbox.srt_config import (
    FilesystemRule,
    NetworkRule,
    EnvironmentVariable,
    SRTConfigManager,
    SRTPolicy,
    FilesystemAccessMode,
    NetworkAccessMode,
    STRICT_POLICY,
    RESEARCH_POLICY,
    DEVELOPMENT_POLICY,
)


class TestFilesystemRule:
    """Test FilesystemRule data class."""

    def test_filesystem_rule_creation(self):
        """Test creating filesystem rule."""
        rule = FilesystemRule(
            path="/home/user/data",
            mode=FilesystemAccessMode.ALLOW,
            recursive=True,
            description="Allow user data access",
        )

        assert rule.path == "/home/user/data"
        assert rule.mode == FilesystemAccessMode.ALLOW
        assert rule.recursive is True
        assert rule.description == "Allow user data access"

    def test_filesystem_rule_to_dict(self):
        """Test converting rule to dictionary."""
        rule = FilesystemRule(
            path="/tmp",
            mode=FilesystemAccessMode.READ_ONLY,
            recursive=True,
        )

        rule_dict = rule.to_dict()

        assert rule_dict["path"] == "/tmp"
        assert rule_dict["mode"] == "read_only"
        assert rule_dict["recursive"] is True

    def test_filesystem_rule_defaults(self):
        """Test default values for filesystem rule."""
        rule = FilesystemRule(path="/etc")

        assert rule.mode == FilesystemAccessMode.DENY
        assert rule.recursive is False
        assert rule.description == ""


class TestNetworkRule:
    """Test NetworkRule data class."""

    def test_network_rule_creation(self):
        """Test creating network rule."""
        rule = NetworkRule(
            domain="api.github.com",
            mode="allow",
            ports=[80, 443],
            description="Allow GitHub API",
        )

        assert rule.domain == "api.github.com"
        assert rule.mode == "allow"
        assert rule.ports == [80, 443]
        assert rule.description == "Allow GitHub API"

    def test_network_rule_to_dict(self):
        """Test converting rule to dictionary."""
        rule = NetworkRule(
            domain="*.example.com",
            mode="deny",
            protocols=["http"],
        )

        rule_dict = rule.to_dict()

        assert rule_dict["domain"] == "*.example.com"
        assert rule_dict["mode"] == "deny"
        assert rule_dict["protocols"] == ["http"]

    def test_network_rule_defaults(self):
        """Test default values for network rule."""
        rule = NetworkRule(domain="evil.com")

        assert rule.mode == "deny"
        assert rule.ports is None
        assert rule.protocols == ["http", "https"]


class TestEnvironmentVariable:
    """Test EnvironmentVariable data class."""

    def test_env_var_creation(self):
        """Test creating environment variable."""
        var = EnvironmentVariable(
            name="API_KEY",
            value="secret123",
            sensitive=True,
            description="API authentication key",
        )

        assert var.name == "API_KEY"
        assert var.value == "secret123"
        assert var.sensitive is True
        assert var.description == "API authentication key"

    def test_env_var_to_dict_masks_sensitive(self):
        """Test that sensitive values are masked in dict."""
        var = EnvironmentVariable(
            name="PASSWORD",
            value="secret_password",
            sensitive=True,
        )

        var_dict = var.to_dict()

        assert var_dict["name"] == "PASSWORD"
        assert var_dict["value"] == "***"
        assert var_dict["sensitive"] is True

    def test_env_var_to_dict_exposes_non_sensitive(self):
        """Test that non-sensitive values are exposed in dict."""
        var = EnvironmentVariable(
            name="USER",
            value="alice",
            sensitive=False,
        )

        var_dict = var.to_dict()

        assert var_dict["value"] == "alice"


class TestSRTConfigManager:
    """Test SRTConfigManager builder."""

    def test_manager_creation(self):
        """Test creating config manager."""
        manager = SRTConfigManager(name="test-policy")

        assert manager.name == "test-policy"
        assert len(manager.filesystem_rules) > 0  # Has default rules
        assert manager.network_mode == NetworkAccessMode.NONE

    def test_default_security_rules_added(self):
        """Test that default security rules are added."""
        manager = SRTConfigManager()

        # Should have rules for blocking sensitive paths
        paths = [rule.path for rule in manager.filesystem_rules]
        assert any("ssh" in path.lower() for path in paths)
        assert any("aws" in path.lower() for path in paths)

    def test_allow_read(self):
        """Test adding read permission."""
        manager = SRTConfigManager()
        initial_count = len(manager.filesystem_rules)

        manager.allow_read("/home/user/data", recursive=True)

        assert len(manager.filesystem_rules) == initial_count + 1
        last_rule = manager.filesystem_rules[-1]
        assert last_rule.path == "/home/user/data"
        assert last_rule.mode == FilesystemAccessMode.READ_ONLY
        assert last_rule.recursive is True

    def test_allow_write(self):
        """Test adding write permission."""
        manager = SRTConfigManager()
        initial_count = len(manager.filesystem_rules)

        manager.allow_write("/tmp", recursive=True)

        assert len(manager.filesystem_rules) == initial_count + 1
        last_rule = manager.filesystem_rules[-1]
        assert last_rule.path == "/tmp"
        assert last_rule.mode == FilesystemAccessMode.ALLOW

    def test_deny_path(self):
        """Test denying path access."""
        manager = SRTConfigManager()
        initial_count = len(manager.filesystem_rules)

        manager.deny_path("/etc/sensitive")

        assert len(manager.filesystem_rules) == initial_count + 1
        last_rule = manager.filesystem_rules[-1]
        assert last_rule.mode == FilesystemAccessMode.DENY

    def test_allow_domain(self):
        """Test allowing network domain."""
        manager = SRTConfigManager()
        initial_count = len(manager.network_rules)

        manager.allow_domain("api.github.com")

        assert len(manager.network_rules) == initial_count + 1
        last_rule = manager.network_rules[-1]
        assert last_rule.domain == "api.github.com"
        assert last_rule.mode == "allow"
        assert manager.network_mode == NetworkAccessMode.RESTRICTED

    def test_deny_domain(self):
        """Test denying network domain."""
        manager = SRTConfigManager()
        initial_count = len(manager.network_rules)

        manager.deny_domain("evil.com")

        assert len(manager.network_rules) == initial_count + 1
        last_rule = manager.network_rules[-1]
        assert last_rule.domain == "evil.com"
        assert last_rule.mode == "deny"

    def test_set_network_mode(self):
        """Test setting network access mode."""
        manager = SRTConfigManager()

        manager.set_network_mode(NetworkAccessMode.FULL)
        assert manager.network_mode == NetworkAccessMode.FULL

        manager.set_network_mode(NetworkAccessMode.NONE)
        assert manager.network_mode == NetworkAccessMode.NONE

    def test_expose_env_var(self):
        """Test exposing environment variable."""
        manager = SRTConfigManager()

        manager.expose_env_var("API_KEY", "secret", sensitive=True)

        assert "API_KEY" in manager.environment_vars
        var = manager.environment_vars["API_KEY"]
        assert var.value == "secret"
        assert var.sensitive is True

    def test_expose_env_vars_from_dict(self):
        """Test exposing multiple environment variables."""
        manager = SRTConfigManager()
        env_dict = {
            "HOME": "/home/user",
            "PASSWORD": "secret",
            "USER": "alice",
        }

        manager.expose_env_vars_from_dict(env_dict, sensitive_keys={"PASSWORD"})

        assert len(manager.environment_vars) == 3
        assert manager.environment_vars["PASSWORD"].sensitive is True
        assert manager.environment_vars["HOME"].sensitive is False

    def test_method_chaining(self):
        """Test builder pattern method chaining."""
        manager = (
            SRTConfigManager()
            .allow_read("/home")
            .allow_write("/tmp")
            .allow_domain("api.github.com")
            .expose_env_var("USER", "alice")
        )

        assert len(manager.filesystem_rules) > 2
        assert len(manager.network_rules) > 0
        assert "USER" in manager.environment_vars

    def test_build_policy(self):
        """Test building policy from manager."""
        manager = (
            SRTConfigManager(name="my-policy")
            .allow_read("/data")
            .allow_domain("api.example.com")
        )

        policy = manager.build()

        assert isinstance(policy, SRTPolicy)
        assert policy.name == "my-policy"
        assert len(policy.filesystem_rules) > 0
        assert len(policy.network_rules) > 0


class TestSRTPolicy:
    """Test SRTPolicy configuration."""

    def test_policy_creation(self):
        """Test creating policy directly."""
        rules = [FilesystemRule(path="/tmp", mode=FilesystemAccessMode.ALLOW)]
        policy = SRTPolicy(
            name="test",
            filesystem_rules=rules,
            network_rules=[],
            environment_vars={},
        )

        assert policy.name == "test"
        assert len(policy.filesystem_rules) == 1

    def test_policy_to_dict(self):
        """Test converting policy to dictionary."""
        manager = SRTConfigManager("test").allow_read("/data")
        policy = manager.build()

        policy_dict = policy.to_dict()

        assert policy_dict["name"] == "test"
        assert "filesystem" in policy_dict
        assert "network" in policy_dict
        assert "environment" in policy_dict

    def test_policy_save_and_load(self):
        """Test saving and loading policy to/from file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            policy_file = os.path.join(tmpdir, "policy.json")

            # Create and save policy
            manager = SRTConfigManager("save-test").allow_read("/data").allow_domain("example.com")
            policy = manager.build()
            policy.save(policy_file)

            assert os.path.isfile(policy_file)

            # Load policy
            loaded_policy = SRTPolicy.load(policy_file)

            assert loaded_policy.name == "save-test"
            assert len(loaded_policy.filesystem_rules) > 0
            assert len(loaded_policy.network_rules) > 0

    def test_policy_save_valid_json(self):
        """Test that saved policy is valid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            policy_file = os.path.join(tmpdir, "policy.json")

            manager = SRTConfigManager().allow_read("/home")
            policy = manager.build()
            policy.save(policy_file)

            # Verify it's valid JSON
            with open(policy_file, "r") as f:
                data = json.load(f)

            assert isinstance(data, dict)
            assert "name" in data
            assert "filesystem" in data

    def test_policy_repr(self):
        """Test policy string representation."""
        manager = SRTConfigManager("repr-test").allow_read("/home").allow_domain("example.com")
        policy = manager.build()

        repr_str = repr(policy)

        assert "SRTPolicy" in repr_str
        assert "repr-test" in repr_str

    def test_policy_load_nonexistent_file(self):
        """Test loading from nonexistent file raises error."""
        with pytest.raises(FileNotFoundError):
            SRTPolicy.load("/nonexistent/policy.json")

    def test_policy_load_invalid_json(self):
        """Test loading invalid JSON raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_file = os.path.join(tmpdir, "bad.json")
            with open(bad_file, "w") as f:
                f.write("not valid json {")

            with pytest.raises(json.JSONDecodeError):
                SRTPolicy.load(bad_file)


class TestPresetPolicies:
    """Test preset policy configurations."""

    def test_strict_policy_exists(self):
        """Test that strict policy is defined."""
        assert STRICT_POLICY is not None
        assert STRICT_POLICY.name == "strict"

    def test_strict_policy_blocks_home(self):
        """Test strict policy blocks home directory."""
        home_rules = [r for r in STRICT_POLICY.filesystem_rules if "~" in r.path]
        assert any(r.mode == FilesystemAccessMode.DENY for r in home_rules)

    def test_strict_policy_no_network(self):
        """Test strict policy allows no network."""
        assert STRICT_POLICY.network_mode == NetworkAccessMode.NONE

    def test_research_policy_exists(self):
        """Test that research policy is defined."""
        assert RESEARCH_POLICY is not None
        assert RESEARCH_POLICY.name == "research"

    def test_research_policy_allows_github(self):
        """Test research policy allows GitHub access."""
        domains = [r.domain for r in RESEARCH_POLICY.network_rules if r.mode == "allow"]
        assert any("github" in d for d in domains)

    def test_development_policy_exists(self):
        """Test that development policy is defined."""
        assert DEVELOPMENT_POLICY is not None
        assert DEVELOPMENT_POLICY.name == "development"

    def test_development_policy_allows_network(self):
        """Test development policy allows restricted network."""
        assert DEVELOPMENT_POLICY.network_mode == NetworkAccessMode.RESTRICTED

    def test_all_preset_policies_valid(self):
        """Test all preset policies are properly configured."""
        for policy in [STRICT_POLICY, RESEARCH_POLICY, DEVELOPMENT_POLICY]:
            assert policy.name is not None
            assert isinstance(policy.filesystem_rules, list)
            assert isinstance(policy.network_rules, list)
            assert isinstance(policy.environment_vars, dict)


class TestComplexPolicies:
    """Test building complex policies."""

    def test_policy_with_multiple_rules(self):
        """Test policy with multiple filesystem and network rules."""
        manager = (
            SRTConfigManager("complex")
            .allow_read("/home/user/data", recursive=True)
            .allow_write("/tmp", recursive=True)
            .allow_write("/var/log", recursive=True)
            .allow_domain("api.github.com")
            .allow_domain("*.pypi.org")
            .allow_domain("registry.npmjs.org")
            .deny_domain("*.internal-company.com")
        )

        policy = manager.build()

        # Should have multiple rules
        assert len(policy.filesystem_rules) > 3
        assert len(policy.network_rules) > 3

    def test_policy_with_environment_isolation(self):
        """Test policy with environment variable isolation."""
        manager = (
            SRTConfigManager("isolated")
            .expose_env_var("USER", "sandbox-user")
            .expose_env_var("HOME", "/tmp/sandbox-home")
            .expose_env_var("API_KEY", "key123", sensitive=True)
        )

        policy = manager.build()

        assert len(policy.environment_vars) == 3
        assert policy.environment_vars["API_KEY"].sensitive is True

    def test_graduated_access_policy(self):
        """Test creating policies with graduated access levels."""
        policies = {
            "minimal": (
                SRTConfigManager("minimal")
                .set_network_mode(NetworkAccessMode.NONE)
                .build()
            ),
            "standard": (
                SRTConfigManager("standard")
                .allow_read("/home", recursive=True)
                .allow_write("/tmp", recursive=True)
                .allow_domain("api.github.com")
                .build()
            ),
            "developer": (
                SRTConfigManager("developer")
                .allow_read(os.getcwd(), recursive=True)
                .allow_write(os.getcwd(), recursive=True)
                .allow_write("/tmp", recursive=True)
                .set_network_mode(NetworkAccessMode.RESTRICTED)
                .allow_domain("*.github.com")
                .allow_domain("*.pypi.org")
                .build()
            ),
        }

        # Verify graduated access
        assert len(policies["minimal"].network_rules) < len(policies["standard"].network_rules)
        assert len(policies["standard"].filesystem_rules) < len(policies["developer"].filesystem_rules)


class TestConfigManagerEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_environment_dict(self):
        """Test exposing empty environment dict."""
        manager = SRTConfigManager().expose_env_vars_from_dict({})
        policy = manager.build()

        assert len(policy.environment_vars) == 0

    def test_rule_override_behavior(self):
        """Test that rules can be added multiple times (no deduplication)."""
        manager = SRTConfigManager()
        initial = len(manager.filesystem_rules)

        manager.allow_read("/tmp")
        manager.allow_read("/tmp")  # Same rule again

        # Both are added (builder pattern doesn't deduplicate)
        assert len(manager.filesystem_rules) == initial + 2

    def test_long_path_in_rule(self):
        """Test handling of long file paths."""
        long_path = "/home/user/very/long/path/that/goes/on/and/on/and/on"
        manager = SRTConfigManager().allow_read(long_path)

        policy = manager.build()
        assert any(long_path in r.path for r in policy.filesystem_rules)

    def test_special_characters_in_domain(self):
        """Test handling special characters in domain patterns."""
        special_domain = "*.example-123.co.uk"
        manager = SRTConfigManager().allow_domain(special_domain)

        policy = manager.build()
        assert any(special_domain == r.domain for r in policy.network_rules)

    def test_policy_name_uniqueness(self):
        """Test that multiple policies can have different names."""
        policies = [
            SRTConfigManager(f"policy-{i}").build()
            for i in range(5)
        ]

        names = [p.name for p in policies]
        assert len(names) == len(set(names))  # All unique
