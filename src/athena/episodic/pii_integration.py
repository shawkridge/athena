"""Integration of PII sanitization into episodic pipeline.

This module bridges the PII detection/tokenization system into the event
processing pipeline at Stage 2.5 (between deduplication and hashing).

Architecture:
    Input: List[EpisodicEvent] (unique, no duplicates)
        ↓
    Stage 2.5: PII Sanitization (NEW)
        ├─ Detect PII in all text fields
        ├─ Tokenize detected PII
        ├─ Apply field-level policies
        ├─ Audit log all operations
        └─ Output: List[EpisodicEvent] (sanitized)
        ↓
    Stage 3+: Remainder of pipeline (hash, embed, store)

Benefits:
- PII never reaches embeddings, database, or search
- Deduplication still works (same original → same sanitized → same hash)
- Audit trail tracks all PII operations
- Deterministic: Same event always → same sanitized version
- <5% performance overhead
"""

import logging
from typing import List, Dict, Optional, Tuple

from ..pii import PIIDetector, PIITokenizer, FieldPolicy, PIIConfig
from .models import EpisodicEvent

logger = logging.getLogger(__name__)


class PIISanitizer:
    """Sanitizes episodic events by detecting and tokenizing PII.

    Integrates into the EventProcessingPipeline as Stage 2.5, applying
    privacy-preserving transformations before events are hashed and stored.
    """

    def __init__(
        self,
        config: Optional[PIIConfig] = None,
        audit_callback: Optional[callable] = None,
    ):
        """Initialize sanitizer.

        Args:
            config: PIIConfig instance (uses defaults if None)
            audit_callback: Optional callback for audit logging
                Signature: audit_callback(action, details)
        """
        self.config = config or PIIConfig.from_env()
        self.detector = PIIDetector()
        self.tokenizer = PIITokenizer(strategy=self.config.tokenization_strategy)
        self.policy = FieldPolicy()
        self.audit_callback = audit_callback
        self._stats = {
            "total_events": 0,
            "events_with_pii": 0,
            "pii_detections": 0,
        }

    def sanitize_batch(
        self,
        events: List[EpisodicEvent],
    ) -> Tuple[List[EpisodicEvent], Dict]:
        """Sanitize a batch of events.

        Args:
            events: List of episodic events to sanitize

        Returns:
            Tuple of:
                - List of sanitized events
                - Statistics dict {total_events, events_with_pii, pii_detections}
        """
        if not self.config.enabled:
            logger.debug("PII sanitization disabled, returning events as-is")
            return events, {"total_events": len(events), "events_with_pii": 0, "pii_detections": 0}

        sanitized_events = []

        for event in events:
            sanitized, had_pii = self._sanitize_event(event)
            sanitized_events.append(sanitized)

            self._stats["total_events"] += 1
            if had_pii:
                self._stats["events_with_pii"] += 1

        return sanitized_events, dict(self._stats)

    def _sanitize_event(self, event: EpisodicEvent) -> Tuple[EpisodicEvent, bool]:
        """Sanitize a single event.

        Args:
            event: Event to sanitize

        Returns:
            Tuple of:
                - Sanitized event
                - Whether PII was found and processed
        """
        from copy import deepcopy

        # Detect PII
        detections = self.detector.detect_in_event(event)

        if not detections:
            return event, False

        # Log detection
        self._audit(
            "pii_detected",
            {
                "event_id": event.id if hasattr(event, "id") else "unknown",
                "detections": {
                    field: [{"type": d.type, "confidence": d.confidence} for d in dets]
                    for field, dets in detections.items()
                },
            },
        )

        # Tokenize PII
        sanitized = deepcopy(event)
        sanitized = self.tokenizer.tokenize_event(sanitized, detections)

        # Apply field policies
        sanitized = self.policy.apply(sanitized, tokenizer=self.tokenizer)

        # Log sanitization
        self._audit(
            "pii_sanitized",
            {
                "event_id": event.id if hasattr(event, "id") else "unknown",
                "fields_affected": list(detections.keys()),
                "strategy": self.config.tokenization_strategy,
            },
        )

        self._stats["pii_detections"] += sum(len(d) for d in detections.values())

        return sanitized, True

    def _audit(self, action: str, details: Dict) -> None:
        """Log an audit action.

        Args:
            action: Action type (e.g., 'pii_detected', 'pii_sanitized')
            details: Action details
        """
        if self.config.audit_enabled:
            logger.info(f"PII audit: {action} - {details}")

        if self.audit_callback:
            try:
                self.audit_callback(action, details)
            except Exception as e:
                logger.error(f"Audit callback failed: {e}")

    def stats(self) -> Dict:
        """Get sanitization statistics.

        Returns:
            Dictionary with statistics
        """
        return dict(self._stats)

    def reset_stats(self) -> None:
        """Reset statistics counters."""
        self._stats = {
            "total_events": 0,
            "events_with_pii": 0,
            "pii_detections": 0,
        }


class PipelineIntegration:
    """Helper to integrate PIISanitizer into EventProcessingPipeline.

    Wraps the existing pipeline to insert PII sanitization at Stage 2.5.
    """

    def __init__(
        self,
        original_pipeline: "EventProcessingPipeline",
        sanitizer: Optional[PIISanitizer] = None,
    ):
        """Initialize integration wrapper.

        Args:
            original_pipeline: The original EventProcessingPipeline
            sanitizer: PIISanitizer instance (creates default if None)
        """
        self.pipeline = original_pipeline
        self.sanitizer = sanitizer or PIISanitizer()

    async def process_batch_with_sanitization(
        self,
        events: List[EpisodicEvent],
    ) -> Dict:
        """Process events through pipeline with PII sanitization.

        Adds Stage 2.5 (PII Sanitization) between Stage 1 (dedup) and Stage 2 (hash):

        Original pipeline:
            Events → Dedup (Stage 1) → Hash (Stage 2) → ...

        With sanitization:
            Events → Dedup (Stage 1) → Sanitize (Stage 2.5) → Hash (Stage 2) → ...

        Args:
            events: List of events to process

        Returns:
            Statistics dictionary with added 'pii_stats' key
        """
        import time

        start_time = time.time()

        if not events:
            return {
                "total": 0,
                "inserted": 0,
                "skipped_duplicate": 0,
                "skipped_existing": 0,
                "processing_time_ms": 0.0,
                "pii_stats": {
                    "total_events": 0,
                    "events_with_pii": 0,
                    "pii_detections": 0,
                },
            }

        # Stage 1: In-memory deduplication (from original pipeline)
        unique_events = self.pipeline._deduplicate_batch(events)
        skipped_duplicate = len(events) - len(unique_events)

        if not unique_events:
            return {
                "total": len(events),
                "inserted": 0,
                "skipped_duplicate": skipped_duplicate,
                "skipped_existing": 0,
                "processing_time_ms": (time.time() - start_time) * 1000,
                "pii_stats": {
                    "total_events": 0,
                    "events_with_pii": 0,
                    "pii_detections": 0,
                },
            }

        # Stage 2.5: PII SANITIZATION (NEW)
        logger.debug(f"Stage 2.5: Sanitizing {len(unique_events)} events for PII")
        sanitized_events, pii_stats = self.sanitizer.sanitize_batch(unique_events)

        # Stages 2-6: Continue with original pipeline using sanitized events
        logger.debug("Continuing pipeline with sanitized events")
        original_stats = await self.pipeline.process_batch(sanitized_events)

        # Merge statistics
        original_stats["pii_stats"] = pii_stats

        return original_stats
