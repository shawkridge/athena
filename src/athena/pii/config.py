"""Configuration for PII detection and handling.

Provides pattern definitions, tokenization settings, and field policies.
Configurable for different deployment scenarios (development, production, compliance).
"""

from typing import Dict, Optional
from dataclasses import dataclass
import os
import json


@dataclass
class PIIConfig:
    """Configuration for PII detection and tokenization.

    Attributes:
        enabled: Whether PII handling is enabled
        detection_mode: 'strict' (all patterns) or 'conservative' (high-confidence only)
        tokenization_strategy: 'hash', 'index', or 'type'
        field_policy_mode: 'standard', 'compliance', or 'debug'
        audit_enabled: Whether to log PII operations
        confidence_threshold: Minimum confidence for detection (0-1)
        custom_patterns: Additional PII patterns to detect
    """

    enabled: bool = True
    detection_mode: str = "strict"  # 'strict' or 'conservative'
    tokenization_strategy: str = "hash"  # 'hash', 'index', or 'type'
    field_policy_mode: str = "standard"  # 'standard', 'compliance', or 'debug'
    audit_enabled: bool = True
    confidence_threshold: float = 0.7
    custom_patterns: Optional[Dict[str, str]] = None

    @classmethod
    def from_env(cls) -> "PIIConfig":
        """Load configuration from environment variables.

        Recognized variables:
        - ATHENA_PII_ENABLED (true/false)
        - ATHENA_PII_DETECTION_MODE (strict/conservative)
        - ATHENA_PII_TOKENIZATION_STRATEGY (hash/index/type)
        - ATHENA_PII_FIELD_POLICY_MODE (standard/compliance/debug)
        - ATHENA_PII_AUDIT_ENABLED (true/false)
        - ATHENA_PII_CONFIDENCE_THRESHOLD (0.0-1.0)
        - ATHENA_PII_CUSTOM_PATTERNS (JSON string)

        Returns:
            PIIConfig instance
        """
        return cls(
            enabled=os.getenv("ATHENA_PII_ENABLED", "true").lower() == "true",
            detection_mode=os.getenv("ATHENA_PII_DETECTION_MODE", "strict"),
            tokenization_strategy=os.getenv("ATHENA_PII_TOKENIZATION_STRATEGY", "hash"),
            field_policy_mode=os.getenv("ATHENA_PII_FIELD_POLICY_MODE", "standard"),
            audit_enabled=os.getenv("ATHENA_PII_AUDIT_ENABLED", "true").lower() == "true",
            confidence_threshold=float(os.getenv("ATHENA_PII_CONFIDENCE_THRESHOLD", "0.7")),
            custom_patterns=_parse_custom_patterns(os.getenv("ATHENA_PII_CUSTOM_PATTERNS", "{}")),
        )

    @classmethod
    def from_file(cls, config_path: str) -> "PIIConfig":
        """Load configuration from JSON file.

        Args:
            config_path: Path to JSON config file

        Returns:
            PIIConfig instance
        """
        try:
            with open(config_path) as f:
                data = json.load(f)
            return cls(**data)
        except (FileNotFoundError, json.JSONDecodeError):
            return cls()  # Return defaults if file not found

    @classmethod
    def development(cls) -> "PIIConfig":
        """Development configuration (minimal sanitization)."""
        return cls(
            enabled=True,
            detection_mode="strict",
            tokenization_strategy="hash",
            field_policy_mode="debug",  # Permissive
            audit_enabled=True,
            confidence_threshold=0.8,
        )

    @classmethod
    def production(cls) -> "PIIConfig":
        """Production configuration (balanced sanitization)."""
        return cls(
            enabled=True,
            detection_mode="strict",
            tokenization_strategy="hash",
            field_policy_mode="standard",
            audit_enabled=True,
            confidence_threshold=0.7,
        )

    @classmethod
    def compliance(cls) -> "PIIConfig":
        """Compliance configuration (strict sanitization for GDPR/CCPA)."""
        return cls(
            enabled=True,
            detection_mode="strict",
            tokenization_strategy="hash",
            field_policy_mode="compliance",  # Strict
            audit_enabled=True,
            confidence_threshold=0.7,
        )

    def to_dict(self) -> Dict:
        """Convert config to dictionary."""
        return {
            "enabled": self.enabled,
            "detection_mode": self.detection_mode,
            "tokenization_strategy": self.tokenization_strategy,
            "field_policy_mode": self.field_policy_mode,
            "audit_enabled": self.audit_enabled,
            "confidence_threshold": self.confidence_threshold,
            "custom_patterns": self.custom_patterns or {},
        }

    def to_json(self) -> str:
        """Convert config to JSON string."""
        import json

        return json.dumps(self.to_dict(), indent=2)


def _parse_custom_patterns(patterns_str: str) -> Optional[Dict[str, str]]:
    """Parse custom patterns from JSON string.

    Args:
        patterns_str: JSON string of patterns

    Returns:
        Dictionary of patterns or None if empty
    """
    if not patterns_str or patterns_str == "{}":
        return None

    try:
        patterns = json.loads(patterns_str)
        return patterns if patterns else None
    except json.JSONDecodeError:
        return None


# Global configuration instance
_global_config: Optional[PIIConfig] = None


def set_config(config: PIIConfig) -> None:
    """Set global PII configuration.

    Args:
        config: PIIConfig instance
    """
    global _global_config
    _global_config = config


def get_config() -> PIIConfig:
    """Get global PII configuration.

    Returns:
        PIIConfig instance (creates from env if not set)
    """
    global _global_config
    if _global_config is None:
        _global_config = PIIConfig.from_env()
    return _global_config


def reset_config() -> None:
    """Reset global configuration to defaults."""
    global _global_config
    _global_config = None


# Example usage patterns for documentation

EXAMPLE_PATTERNS = {
    "api_key": r"(?:[sS][kK][-_]?[a-zA-Z0-9]{20,}|key[-_]?[a-zA-Z0-9]{20,})",
    "database_url": r"(?:postgresql|mysql|mongodb)://[^\s]+",
    "internal_ip": r"\b(?:10|172|192)\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
    "slack_token": r"xox[baprs]-[0-9a-zA-Z]{10,48}",
}
