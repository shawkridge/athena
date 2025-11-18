"""PII Detection and Tokenization Module.

Provides privacy-preserving event processing by detecting, tokenizing, and
sanitizing personally identifiable information (PII) in episodic events.

Key Components:
- PIIDetector: Pattern-based detection of PII (emails, paths, credentials, etc.)
- PIITokenizer: Deterministic tokenization strategies (hash, index, type-based)
- FieldPolicy: Per-field sanitization strategies (redact, truncate, tokenize, etc.)
- PIIConfig: Configuration for patterns, tokenization, and policies

Typical Usage:
    detector = PIIDetector()
    tokenizer = PIITokenizer(strategy='hash')
    policy = FieldPolicy()

    detections = detector.detect_in_event(event)
    sanitized = tokenizer.tokenize_event(event)
    final = policy.apply(sanitized)
"""

from .detector import PIIDetection, PIIDetector
from .tokenizer import PIITokenizer
from .policies import SanitizationStrategy, FieldPolicy
from .config import PIIConfig

__all__ = [
    "PIIDetection",
    "PIIDetector",
    "PIITokenizer",
    "SanitizationStrategy",
    "FieldPolicy",
    "PIIConfig",
]
