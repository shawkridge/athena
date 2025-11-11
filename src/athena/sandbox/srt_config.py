"""SRT Configuration Manager for advanced sandbox policies.

Provides high-level configuration management for SRT sandboxing,
including filesystem rules, network policies, and environment setup.
"""

import json
import logging
import os
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Any

logger = logging.getLogger(__name__)


class FilesystemAccessMode(str, Enum):
    """Filesystem access control modes."""

    ALLOW = "allow"  # Explicitly allow access
    DENY = "deny"  # Explicitly deny access
    READ_ONLY = "read_only"  # Allow read but not write


class NetworkAccessMode(str, Enum):
    """Network access control modes."""

    NONE = "none"  # No network access
    RESTRICTED = "restricted"  # Only allowed domains
    FULL = "full"  # Full network access (not recommended)


@dataclass
class FilesystemRule:
    """Filesystem access rule.

    Attributes:
        path: File or directory path pattern
        mode: Access mode (allow/deny/read_only)
        recursive: Apply recursively to subdirectories
        description: Human-readable rule description
    """

    path: str
    mode: FilesystemAccessMode = FilesystemAccessMode.DENY
    recursive: bool = False
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class NetworkRule:
    """Network access rule.

    Attributes:
        domain: Domain pattern (supports wildcards: *.example.com)
        mode: Access mode (allow or deny)
        ports: Specific ports (None = all)
        protocols: Allowed protocols (http, https, etc.)
        description: Human-readable rule description
    """

    domain: str
    mode: str = "deny"  # "allow" or "deny"
    ports: Optional[List[int]] = None
    protocols: List[str] = field(default_factory=lambda: ["http", "https"])
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "domain": self.domain,
            "mode": self.mode,
            "ports": self.ports,
            "protocols": self.protocols,
            "description": self.description,
        }


@dataclass
class EnvironmentVariable:
    """Environment variable to expose to sandbox.

    Attributes:
        name: Variable name
        value: Variable value
        sensitive: Whether value should be masked in logs
        description: Human-readable description
    """

    name: str
    value: str
    sensitive: bool = False
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "value": "***" if self.sensitive else self.value,
            "sensitive": self.sensitive,
            "description": self.description,
        }


class SRTConfigManager:
    """Advanced configuration manager for SRT sandboxing.

    Provides builder pattern for complex sandbox policies with
    filesystem rules, network policies, and environment controls.

    Example:
        manager = SRTConfigManager()
        manager.allow_read("/home/user/data")
        manager.deny_path("/etc/passwd")
        manager.allow_domain("api.github.com")
        manager.deny_domain("*.internal-company.com")
        config = manager.build()
        config.save("sandbox_policy.json")
    """

    def __init__(self, name: str = "default"):
        """Initialize configuration manager.

        Args:
            name: Configuration name/identifier
        """
        self.name = name
        self.filesystem_rules: List[FilesystemRule] = []
        self.network_rules: List[NetworkRule] = []
        self.environment_vars: Dict[str, EnvironmentVariable] = {}
        self.network_mode = NetworkAccessMode.NONE

        # Add default security rules
        self._add_default_rules()

    def _add_default_rules(self) -> None:
        """Add default security rules to block sensitive paths."""
        sensitive_paths = [
            ("~/.ssh", "SSH keys"),
            ("~/.aws", "AWS credentials"),
            ("~/.anthropic", "Anthropic API keys"),
            ("~/.config/github", "GitHub credentials"),
            ("/etc/passwd", "System authentication database"),
            ("/etc/shadow", "System password hashes"),
            ("/proc", "Process information"),
            ("/sys", "System kernel information"),
        ]

        for path, description in sensitive_paths:
            self.deny_path(path, description)

    def allow_read(
        self, path: str, recursive: bool = False, description: str = ""
    ) -> "SRTConfigManager":
        """Allow read access to path.

        Args:
            path: File or directory path
            recursive: Apply to subdirectories
            description: Human-readable description

        Returns:
            Self for method chaining
        """
        self.filesystem_rules.append(
            FilesystemRule(
                path=path,
                mode=FilesystemAccessMode.READ_ONLY,
                recursive=recursive,
                description=description or f"Allow read: {path}",
            )
        )
        return self

    def allow_write(
        self, path: str, recursive: bool = False, description: str = ""
    ) -> "SRTConfigManager":
        """Allow read and write access to path.

        Args:
            path: File or directory path
            recursive: Apply to subdirectories
            description: Human-readable description

        Returns:
            Self for method chaining
        """
        self.filesystem_rules.append(
            FilesystemRule(
                path=path,
                mode=FilesystemAccessMode.ALLOW,
                recursive=recursive,
                description=description or f"Allow read+write: {path}",
            )
        )
        return self

    def deny_path(self, path: str, description: str = "") -> "SRTConfigManager":
        """Deny access to path.

        Args:
            path: File or directory path to block
            description: Human-readable description

        Returns:
            Self for method chaining
        """
        self.filesystem_rules.append(
            FilesystemRule(
                path=path,
                mode=FilesystemAccessMode.DENY,
                description=description or f"Block access: {path}",
            )
        )
        return self

    def allow_domain(
        self, domain: str, ports: Optional[List[int]] = None, description: str = ""
    ) -> "SRTConfigManager":
        """Allow network access to domain.

        Args:
            domain: Domain pattern (supports wildcards: *.example.com)
            ports: Specific ports (None = all)
            description: Human-readable description

        Returns:
            Self for method chaining
        """
        self.network_rules.append(
            NetworkRule(
                domain=domain,
                mode="allow",
                ports=ports,
                description=description or f"Allow network: {domain}",
            )
        )
        self.network_mode = NetworkAccessMode.RESTRICTED
        return self

    def deny_domain(self, domain: str, description: str = "") -> "SRTConfigManager":
        """Deny network access to domain.

        Args:
            domain: Domain pattern to block
            description: Human-readable description

        Returns:
            Self for method chaining
        """
        self.network_rules.append(
            NetworkRule(
                domain=domain,
                mode="deny",
                description=description or f"Block network: {domain}",
            )
        )
        return self

    def set_network_mode(self, mode: NetworkAccessMode) -> "SRTConfigManager":
        """Set global network access mode.

        Args:
            mode: Network access mode (NONE, RESTRICTED, FULL)

        Returns:
            Self for method chaining
        """
        self.network_mode = mode
        return self

    def expose_env_var(
        self, name: str, value: str, sensitive: bool = False, description: str = ""
    ) -> "SRTConfigManager":
        """Expose environment variable to sandbox.

        Args:
            name: Variable name
            value: Variable value
            sensitive: Whether value should be masked in logs
            description: Human-readable description

        Returns:
            Self for method chaining
        """
        self.environment_vars[name] = EnvironmentVariable(
            name=name,
            value=value,
            sensitive=sensitive,
            description=description,
        )
        return self

    def expose_env_vars_from_dict(
        self, env_vars: Dict[str, str], sensitive_keys: Optional[Set[str]] = None
    ) -> "SRTConfigManager":
        """Expose multiple environment variables from dictionary.

        Args:
            env_vars: Dictionary of environment variables
            sensitive_keys: Set of keys to mark as sensitive

        Returns:
            Self for method chaining
        """
        sensitive_keys = sensitive_keys or set()
        for name, value in env_vars.items():
            self.expose_env_var(name, value, sensitive=name in sensitive_keys)
        return self

    def build(self) -> "SRTPolicy":
        """Build final SRT policy configuration.

        Returns:
            SRTPolicy instance ready for use
        """
        return SRTPolicy(
            name=self.name,
            filesystem_rules=self.filesystem_rules,
            network_rules=self.network_rules,
            environment_vars=self.environment_vars,
            network_mode=self.network_mode,
        )


class SRTPolicy:
    """Immutable SRT sandbox policy configuration.

    Represents a complete sandbox policy ready for execution.
    """

    def __init__(
        self,
        name: str,
        filesystem_rules: List[FilesystemRule],
        network_rules: List[NetworkRule],
        environment_vars: Dict[str, EnvironmentVariable],
        network_mode: NetworkAccessMode = NetworkAccessMode.NONE,
    ):
        """Initialize policy.

        Args:
            name: Policy name
            filesystem_rules: List of filesystem access rules
            network_rules: List of network access rules
            environment_vars: Environment variables to expose
            network_mode: Global network access mode
        """
        self.name = name
        self.filesystem_rules = filesystem_rules
        self.network_rules = network_rules
        self.environment_vars = environment_vars
        self.network_mode = network_mode

    def to_dict(self) -> Dict[str, Any]:
        """Convert policy to dictionary."""
        return {
            "name": self.name,
            "network_mode": self.network_mode.value,
            "filesystem": {
                "rules": [rule.to_dict() for rule in self.filesystem_rules],
            },
            "network": {
                "mode": self.network_mode.value,
                "rules": [rule.to_dict() for rule in self.network_rules],
            },
            "environment": {
                name: var.to_dict() for name, var in self.environment_vars.items()
            },
        }

    def save(self, filepath: str) -> None:
        """Save policy to JSON file.

        Args:
            filepath: Path to save policy to
        """
        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
        logger.info(f"Saved SRT policy to {filepath}")

    @staticmethod
    def load(filepath: str) -> "SRTPolicy":
        """Load policy from JSON file.

        Args:
            filepath: Path to load policy from

        Returns:
            SRTPolicy instance

        Raises:
            FileNotFoundError: If file doesn't exist
            json.JSONDecodeError: If file is invalid JSON
        """
        with open(filepath, "r") as f:
            data = json.load(f)

        filesystem_rules = [
            FilesystemRule(**rule) for rule in data.get("filesystem", {}).get("rules", [])
        ]

        network_rules = [
            NetworkRule(**rule) for rule in data.get("network", {}).get("rules", [])
        ]

        environment_vars = {
            name: EnvironmentVariable(**var)
            for name, var in data.get("environment", {}).items()
        }

        network_mode = NetworkAccessMode(data.get("network", {}).get("mode", "none"))

        return SRTPolicy(
            name=data.get("name", "loaded"),
            filesystem_rules=filesystem_rules,
            network_rules=network_rules,
            environment_vars=environment_vars,
            network_mode=network_mode,
        )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"SRTPolicy(name={self.name}, "
            f"fs_rules={len(self.filesystem_rules)}, "
            f"net_rules={len(self.network_rules)}, "
            f"env_vars={len(self.environment_vars)})"
        )


# Preset policies for common scenarios
STRICT_POLICY = (
    SRTConfigManager("strict")
    .set_network_mode(NetworkAccessMode.NONE)
    .deny_path("~", "Block home directory access")
    .allow_read("/tmp", recursive=True, description="Allow /tmp read")
    .allow_write("/tmp", recursive=True, description="Allow /tmp write")
    .build()
)

RESEARCH_POLICY = (
    SRTConfigManager("research")
    .allow_read("/home", recursive=True, description="Allow home directory read")
    .allow_write("/tmp", recursive=True, description="Allow /tmp write")
    .allow_domain("api.github.com", description="Allow GitHub API")
    .allow_domain("pypi.org", description="Allow PyPI")
    .allow_domain("*.github.com", description="Allow GitHub domains")
    .build()
)

DEVELOPMENT_POLICY = (
    SRTConfigManager("development")
    .allow_read(os.getcwd(), recursive=True, description="Allow current directory read")
    .allow_write(os.getcwd(), recursive=True, description="Allow current directory write")
    .allow_write("/tmp", recursive=True, description="Allow /tmp write")
    .set_network_mode(NetworkAccessMode.RESTRICTED)
    .allow_domain("api.github.com")
    .allow_domain("pypi.org")
    .allow_domain("registry.npmjs.org")
    .build()
)
