"""PII Tokenization strategies.

Provides deterministic replacement of detected PII with tokens:
- Hash-based: Irreversible hashing (recommended)
- Index-based: Compact numeric tokens
- Type-based: Semantic tokens (lossy but readable)
"""

from typing import Dict, List, Optional
import hashlib
import re
from .detector import PIIDetection


class PIITokenizer:
    """Replaces detected PII with deterministic tokens.

    Strategies:
    - 'hash': Irreversible hash tokens (PII_HASH_abc123...)
    - 'index': Compact index tokens (PII_ID_1, PII_ID_2, ...)
    - 'type': Semantic type tokens (EMAIL_MASKED, PATH_MASKED, ...)
    """

    def __init__(self, strategy: str = 'hash', salt: Optional[str] = None):
        """Initialize tokenizer with strategy.

        Args:
            strategy: 'hash', 'index', or 'type'
            salt: Optional salt for hash-based strategy (for determinism)
        """
        if strategy not in ('hash', 'index', 'type'):
            raise ValueError(f"Unknown strategy: {strategy}")

        self.strategy = strategy
        self.salt = salt or 'athena_pii_v1'
        self._index_counter = 0

    def tokenize(self, text: str, detections: List[PIIDetection]) -> str:
        """Replace detected PII in text with tokens.

        Args:
            text: Original text
            detections: List of PII detections from detector

        Returns:
            Text with PII replaced by tokens
        """
        if not detections:
            return text

        # Sort by position (reverse) to replace from end to start
        # This prevents position shifts during replacement
        sorted_detections = sorted(detections, key=lambda d: d.start_pos, reverse=True)

        result = text
        for detection in sorted_detections:
            token = self._get_token(detection)
            result = result[:detection.start_pos] + token + result[detection.end_pos:]

        return result

    def tokenize_event(self, event: 'EpisodicEvent', detections_by_field: Dict[str, List[PIIDetection]]) -> 'EpisodicEvent':
        """Apply tokenization to an episodic event.

        Args:
            event: Original episodic event
            detections_by_field: PII detections from detector

        Returns:
            New event with PII replaced by tokens
        """
        from copy import deepcopy
        from athena.episodic.models import EpisodicEvent

        sanitized = deepcopy(event)

        # Tokenize each field with detections
        for field_name, detections in detections_by_field.items():
            if not detections:
                continue

            if field_name == 'content':
                sanitized.content = self.tokenize(event.content, detections)
            elif field_name == 'git_author':
                sanitized.git_author = self.tokenize(event.git_author, detections)
            elif field_name == 'file_path':
                sanitized.file_path = self.tokenize(event.file_path, detections)
            elif field_name == 'diff':
                sanitized.diff = self.tokenize(event.diff, detections)
            elif field_name == 'stack_trace':
                sanitized.stack_trace = self.tokenize(event.stack_trace, detections)
            elif field_name == 'context.cwd':
                if sanitized.context:
                    sanitized.context.cwd = self.tokenize(event.context.cwd, detections)
            elif field_name == 'context.task':
                if sanitized.context:
                    sanitized.context.task = self.tokenize(event.context.task, detections)
            elif field_name == 'context.files':
                if sanitized.context and event.context.files:
                    files_text = ' '.join(event.context.files)
                    tokenized = self.tokenize(files_text, detections)
                    sanitized.context.files = tokenized.split()

        return sanitized

    def _get_token(self, detection: PIIDetection) -> str:
        """Generate a token for a PII detection.

        Args:
            detection: PII detection result

        Returns:
            Token string
        """
        if self.strategy == 'hash':
            return self._hash_token(detection)
        elif self.strategy == 'index':
            return self._index_token(detection)
        elif self.strategy == 'type':
            return self._type_token(detection)
        else:
            raise ValueError(f"Unknown strategy: {self.strategy}")

    def _hash_token(self, detection: PIIDetection) -> str:
        """Generate hash-based token (irreversible).

        Format: PII_HASH_abc123ef (16-char hash)
        """
        combined = f"{self.salt}:{detection.value}:{detection.type}"
        hash_obj = hashlib.sha256(combined.encode())
        hash_hex = hash_obj.hexdigest()[:16]
        return f"PII_HASH_{hash_hex}"

    def _index_token(self, detection: PIIDetection) -> str:
        """Generate index-based token (compact, requires mapping).

        Format: PII_ID_1, PII_ID_2, etc.
        Note: This approach requires maintaining a mapping table.
        """
        self._index_counter += 1
        return f"PII_ID_{self._index_counter}"

    def _type_token(self, detection: PIIDetection) -> str:
        """Generate type-based token (semantic, lossy).

        Format: EMAIL_MASKED, PATH_MASKED, etc.
        """
        type_upper = detection.type.upper()
        return f"{type_upper}_MASKED"

    def is_token(self, value: str) -> bool:
        """Check if a value is a token (not original PII).

        Args:
            value: String to check

        Returns:
            True if value is a generated token
        """
        if not isinstance(value, str):
            return False

        if self.strategy == 'hash':
            return value.startswith('PII_HASH_')
        elif self.strategy == 'index':
            return value.startswith('PII_ID_')
        elif self.strategy == 'type':
            return '_MASKED' in value
        else:
            return False


class DeterministicTokenizer(PIITokenizer):
    """Hash-based tokenizer with deterministic output.

    Same PII input always produces same token output, enabling:
    - Deduplication (same PII → same hash)
    - Consistency across sessions
    """

    def __init__(self, salt: str = 'athena_pii_v1'):
        super().__init__(strategy='hash', salt=salt)

    def tokenize_deterministic(self, text: str, pii_values: List[str]) -> str:
        """Replace exact PII values with deterministic tokens.

        Args:
            text: Original text
            pii_values: List of exact PII strings to replace

        Returns:
            Text with PII replaced
        """
        result = text
        # Sort by length (longest first) to avoid partial replacements
        for pii_value in sorted(pii_values, key=len, reverse=True):
            token = self._hash_token_from_value(pii_value)
            # Use word boundaries for safety
            pattern = re.escape(pii_value)
            result = re.sub(pattern, token, result)

        return result

    def _hash_token_from_value(self, pii_value: str) -> str:
        """Generate hash token directly from PII value.

        Args:
            pii_value: The actual PII value

        Returns:
            Deterministic hash token
        """
        combined = f"{self.salt}:{pii_value}"
        hash_obj = hashlib.sha256(combined.encode())
        hash_hex = hash_obj.hexdigest()[:16]
        return f"PII_HASH_{hash_hex}"
