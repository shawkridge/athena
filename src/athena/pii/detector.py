"""PII Detection using pattern matching.

Detects sensitive information in text and episodic events using regex patterns.
Supports standard PII patterns (emails, paths, credentials, etc.) and custom patterns.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
import re
import logging

logger = logging.getLogger(__name__)


@dataclass
class PIIDetection:
    """Result of detecting PII in text."""

    type: str               # 'email', 'path', 'credential', 'ssn', etc.
    value: str              # The detected PII value
    start_pos: int          # Position in original text
    end_pos: int            # End position
    confidence: float       # Confidence score (0-1)
    field_name: str         # Which field it was found in

    def __repr__(self) -> str:
        return f"PIIDetection(type={self.type}, field={self.field_name}, conf={self.confidence:.2f})"


class PIIDetector:
    """Detects sensitive information in text and episodic events.

    Uses regex patterns to identify:
    - Email addresses
    - Absolute file paths (/home/user, /Users/user)
    - API keys and credentials (sk-*, AKIA*, etc.)
    - Private keys (RSA, OpenSSH, DSA)
    - Social Security Numbers (XXX-XX-XXXX)
    - Credit card numbers
    - Phone numbers
    """

    # Standard PII detection patterns
    PATTERNS = {
        'email': (
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            0.95  # High confidence for explicit email format
        ),
        'absolute_path': (
            r'(?:/home/[a-zA-Z0-9._-]+|/Users/[a-zA-Z0-9._-]+|C:\\Users\\[a-zA-Z0-9._-]+)',
            0.90  # User home directory paths
        ),
        'api_key': (
            r'(?:[sS][kK][-_]?[a-zA-Z0-9]{20,}|key[-_]?[a-zA-Z0-9]{20,})',
            0.85  # API keys like sk-*, key-*
        ),
        'aws_key': (
            r'AKIA[0-9A-Z]{16}',
            0.95  # AWS Access Key ID pattern
        ),
        'private_key': (
            r'-----BEGIN (?:RSA|OPENSSH|DSA|EC|PGP) PRIVATE KEY-----',
            0.99  # Private key headers
        ),
        'ssn': (
            r'\b\d{3}-\d{2}-\d{4}\b',
            0.90  # Social Security Number XXX-XX-XXXX
        ),
        'credit_card': (
            r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
            0.85  # 16-digit credit card
        ),
        'phone': (
            r'\b(?:\+?1[-.]?)?\(?([0-9]{3})\)?[-.]?([0-9]{3})[-.]?([0-9]{4})\b',
            0.80  # Phone numbers with various formats
        ),
        'github_token': (
            r'ghp_[a-zA-Z0-9]{36}',
            0.99  # GitHub Personal Access Token
        ),
        'jwt': (
            r'eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[\w-]*',
            0.85  # JWT format
        ),
    }

    def __init__(self, custom_patterns: Optional[Dict[str, str]] = None):
        """Initialize detector with optional custom patterns.

        Args:
            custom_patterns: Dictionary of {name: pattern} for custom PII detection
        """
        self.patterns = dict(self.PATTERNS)

        # Add custom patterns if provided
        if custom_patterns:
            for name, pattern in custom_patterns.items():
                self.patterns[name] = (pattern, 0.75)  # Default confidence for custom

    def detect(
        self,
        text: str,
        field_name: str = 'unknown',
        confidence_threshold: float = 0.7
    ) -> List[PIIDetection]:
        """Detect PII in text.

        Args:
            text: Text to scan for PII
            field_name: Name of field being scanned (for logging/tracking)
            confidence_threshold: Minimum confidence to report detection

        Returns:
            List of PII detections with locations and confidence scores
        """
        detections = []

        if not text or not isinstance(text, str):
            return detections

        for pii_type, (pattern_str, confidence) in self.patterns.items():
            if confidence < confidence_threshold:
                continue

            try:
                pattern = re.compile(pattern_str)
                for match in pattern.finditer(text):
                    detection = PIIDetection(
                        type=pii_type,
                        value=match.group(0),
                        start_pos=match.start(),
                        end_pos=match.end(),
                        confidence=confidence,
                        field_name=field_name
                    )
                    detections.append(detection)
                    logger.debug(f"Detected {pii_type} in {field_name}: {detection}")
            except re.error as e:
                logger.warning(f"Invalid regex pattern for {pii_type}: {e}")

        return detections

    def detect_in_event(self, event: 'EpisodicEvent') -> Dict[str, List[PIIDetection]]:
        """Scan episodic event for PII in all text fields.

        Args:
            event: EpisodicEvent to scan

        Returns:
            Dictionary mapping field names to list of detections
        """
        detections_by_field = {}

        # Check text fields that commonly contain PII
        fields_to_check = {
            'content': event.content,
            'git_author': event.git_author,
            'file_path': event.file_path,
            'diff': event.diff,
            'stack_trace': event.stack_trace,
        }

        # Check nested context fields
        if event.context:
            fields_to_check['context.cwd'] = event.context.cwd
            fields_to_check['context.task'] = event.context.task
            if event.context.files:
                fields_to_check['context.files'] = ' '.join(event.context.files)

        # Scan each field
        for field_name, field_value in fields_to_check.items():
            if field_value:
                detections = self.detect(str(field_value), field_name=field_name)
                if detections:
                    detections_by_field[field_name] = detections

        return detections_by_field

    def has_pii(self, event: 'EpisodicEvent') -> bool:
        """Quick check if event contains any PII.

        Args:
            event: EpisodicEvent to check

        Returns:
            True if any PII detected, False otherwise
        """
        return bool(self.detect_in_event(event))

    def summary(self, detections_by_field: Dict[str, List[PIIDetection]]) -> str:
        """Generate human-readable summary of detections.

        Args:
            detections_by_field: Result from detect_in_event()

        Returns:
            Summary string for logging
        """
        if not detections_by_field:
            return "No PII detected"

        lines = []
        for field_name, detections in detections_by_field.items():
            types = {}
            for d in detections:
                types[d.type] = types.get(d.type, 0) + 1

            type_str = ', '.join(f"{k}:{v}" for k, v in types.items())
            lines.append(f"{field_name} [{type_str}]")

        return "PII: " + ", ".join(lines)
