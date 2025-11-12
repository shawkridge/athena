"""Field-level sanitization policies.

Defines how each field should be handled:
- PASS_THROUGH: No change
- TOKENIZE: Replace detected PII with tokens
- REDACT: Remove entirely
- TRUNCATE: Keep only basename/relative parts
- HASH_PII: Hash the entire value
"""

from enum import Enum
from typing import Dict, Any, Optional, List
from pathlib import Path
import hashlib


class SanitizationStrategy(Enum):
    """Strategy for field sanitization."""

    PASS_THROUGH = "pass_through"  # No change
    TOKENIZE = "tokenize"          # Replace PII with tokens
    REDACT = "redact"              # Remove entirely
    TRUNCATE = "truncate"          # Keep only basename/relative
    HASH_PII = "hash_pii"          # Hash the entire value


class FieldPolicy:
    """Per-field sanitization rules.

    Maps fields to sanitization strategies with field-specific defaults.
    """

    # Default policies for standard fields
    DEFAULT_POLICIES = {
        # CRITICAL RISK fields
        'diff': SanitizationStrategy.REDACT,
        'git_author': SanitizationStrategy.HASH_PII,

        # HIGH RISK fields
        'content': SanitizationStrategy.TOKENIZE,
        'stack_trace': SanitizationStrategy.TOKENIZE,
        'file_path': SanitizationStrategy.TRUNCATE,
        'context.cwd': SanitizationStrategy.TRUNCATE,

        # MEDIUM RISK fields
        'context.files': SanitizationStrategy.TRUNCATE,
        'context.task': SanitizationStrategy.TOKENIZE,

        # LOW RISK fields (no change)
        'event_type': SanitizationStrategy.PASS_THROUGH,
        'outcome': SanitizationStrategy.PASS_THROUGH,
        'timestamp': SanitizationStrategy.PASS_THROUGH,
        'duration_ms': SanitizationStrategy.PASS_THROUGH,
        'session_id': SanitizationStrategy.PASS_THROUGH,
        'project_id': SanitizationStrategy.PASS_THROUGH,
    }

    def __init__(self, custom_policies: Optional[Dict[str, SanitizationStrategy]] = None):
        """Initialize with default or custom policies.

        Args:
            custom_policies: Override default policies for specific fields
        """
        self.policies = dict(self.DEFAULT_POLICIES)
        if custom_policies:
            self.policies.update(custom_policies)

    def get_policy(self, field_name: str) -> SanitizationStrategy:
        """Get sanitization policy for a field.

        Args:
            field_name: Name of field (e.g., 'content', 'context.cwd')

        Returns:
            Sanitization strategy for the field
        """
        # Check exact match first
        if field_name in self.policies:
            return self.policies[field_name]

        # Check prefix match (e.g., 'context.*')
        for pattern_field, strategy in self.policies.items():
            if pattern_field.endswith('.*'):
                prefix = pattern_field[:-2]
                if field_name.startswith(prefix):
                    return strategy

        # Default to pass-through for unknown fields
        return SanitizationStrategy.PASS_THROUGH

    def apply(self, event: 'EpisodicEvent', tokenizer: Optional['PIITokenizer'] = None) -> 'EpisodicEvent':
        """Apply policies to an episodic event.

        Args:
            event: Original episodic event
            tokenizer: PIITokenizer for TOKENIZE strategy (optional)

        Returns:
            New event with policies applied
        """
        from copy import deepcopy

        sanitized = deepcopy(event)

        # Apply policies to each field
        if sanitized.content:
            policy = self.get_policy('content')
            sanitized.content = self._apply_field_policy(
                sanitized.content, policy, 'content', tokenizer
            )

        if sanitized.git_author:
            policy = self.get_policy('git_author')
            sanitized.git_author = self._apply_field_policy(
                sanitized.git_author, policy, 'git_author', tokenizer
            )

        if sanitized.file_path:
            policy = self.get_policy('file_path')
            sanitized.file_path = self._apply_field_policy(
                sanitized.file_path, policy, 'file_path', tokenizer
            )

        if sanitized.diff:
            policy = self.get_policy('diff')
            sanitized.diff = self._apply_field_policy(
                sanitized.diff, policy, 'diff', tokenizer
            )

        if sanitized.stack_trace:
            policy = self.get_policy('stack_trace')
            sanitized.stack_trace = self._apply_field_policy(
                sanitized.stack_trace, policy, 'stack_trace', tokenizer
            )

        # Apply to context fields
        if sanitized.context:
            if sanitized.context.cwd:
                policy = self.get_policy('context.cwd')
                sanitized.context.cwd = self._apply_field_policy(
                    sanitized.context.cwd, policy, 'context.cwd', tokenizer
                )

            if sanitized.context.task:
                policy = self.get_policy('context.task')
                sanitized.context.task = self._apply_field_policy(
                    sanitized.context.task, policy, 'context.task', tokenizer
                )

            if sanitized.context.files:
                policy = self.get_policy('context.files')
                sanitized.context.files = [
                    self._apply_field_policy(f, policy, 'context.files', tokenizer)
                    for f in sanitized.context.files
                ]

        return sanitized

    def _apply_field_policy(
        self,
        value: str,
        strategy: SanitizationStrategy,
        field_name: str,
        tokenizer: Optional['PIITokenizer'] = None
    ) -> str:
        """Apply a sanitization strategy to a field value.

        Args:
            value: Original field value
            strategy: Sanitization strategy to apply
            field_name: Name of field (for context)
            tokenizer: PIITokenizer (needed for TOKENIZE strategy)

        Returns:
            Sanitized value
        """
        if not value:
            return value

        if strategy == SanitizationStrategy.PASS_THROUGH:
            return value

        elif strategy == SanitizationStrategy.REDACT:
            return f"[REDACTED: {field_name.replace('.', '_').upper()}]"

        elif strategy == SanitizationStrategy.TOKENIZE:
            if tokenizer:
                # Tokenizer will handle PII replacement
                # If already tokenized, return as-is
                return value
            else:
                # No tokenizer available, return as-is
                return value

        elif strategy == SanitizationStrategy.TRUNCATE:
            return self._truncate_path(value)

        elif strategy == SanitizationStrategy.HASH_PII:
            return self._hash_value(value)

        else:
            return value

    @staticmethod
    def _truncate_path(path_str: str) -> str:
        """Truncate file path to basename only, remove home directories.

        Examples:
            /home/alice/projects/app/src/main.py → /app/src/main.py
            /home/alice → /home/alice (directory not truncated)
            /Users/bob/Code/project → /project
        """
        try:
            path = Path(path_str)

            # Get all parts
            parts = path.parts

            # Find home directory segment and remove it
            filtered_parts = []
            skip_next = False
            for i, part in enumerate(parts):
                if skip_next:
                    skip_next = False
                    continue
                if part in ('home', 'Users', 'root'):
                    skip_next = True  # Skip username next
                    continue
                filtered_parts.append(part)

            # Reconstruct path
            if filtered_parts:
                if path.is_absolute() or path_str.startswith('/'):
                    truncated = '/' + '/'.join(filtered_parts)
                else:
                    truncated = '/'.join(filtered_parts)
                return truncated
            else:
                return path_str

        except Exception:
            # If path handling fails, return original
            return path_str

    @staticmethod
    def _hash_value(value: str) -> str:
        """Hash a value irreversibly.

        Args:
            value: Value to hash

        Returns:
            Hashed value in format PII_HASH_abc123...
        """
        hash_obj = hashlib.sha256(value.encode())
        hash_hex = hash_obj.hexdigest()[:16]
        return f"PII_HASH_{hash_hex}"


class CompliancePolicy(FieldPolicy):
    """Strict policy for compliance (GDPR, CCPA).

    More aggressive sanitization to minimize PII exposure.
    """

    COMPLIANCE_POLICIES = {
        # Redact everything risky
        'diff': SanitizationStrategy.REDACT,
        'git_author': SanitizationStrategy.HASH_PII,
        'content': SanitizationStrategy.TOKENIZE,
        'stack_trace': SanitizationStrategy.REDACT,  # Stricter
        'file_path': SanitizationStrategy.TRUNCATE,
        'context.cwd': SanitizationStrategy.REDACT,  # Stricter
        'context.files': SanitizationStrategy.TRUNCATE,
        'context.task': SanitizationStrategy.TOKENIZE,
    }

    def __init__(self):
        super().__init__(custom_policies=self.COMPLIANCE_POLICIES)


class DebugPolicy(FieldPolicy):
    """Permissive policy for development/debugging.

    Minimal sanitization to preserve debugging info.
    """

    DEBUG_POLICIES = {
        'diff': SanitizationStrategy.TOKENIZE,  # Keep some info
        'git_author': SanitizationStrategy.TOKENIZE,
        'content': SanitizationStrategy.PASS_THROUGH,
        'stack_trace': SanitizationStrategy.PASS_THROUGH,
        'file_path': SanitizationStrategy.PASS_THROUGH,
        'context.cwd': SanitizationStrategy.PASS_THROUGH,
        'context.files': SanitizationStrategy.PASS_THROUGH,
        'context.task': SanitizationStrategy.PASS_THROUGH,
    }

    def __init__(self):
        super().__init__(custom_policies=self.DEBUG_POLICIES)
