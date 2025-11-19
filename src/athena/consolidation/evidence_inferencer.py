"""Evidence type inference for episodic events.

During consolidation dreams, automatically infers what kind of knowledge each
episodic event represents based on:
- Event type (code_edit → OBSERVED, test_run success → OBSERVED)
- Content patterns (contains "assume" → HYPOTHETICAL)
- Derivation (extracted_patterns → LEARNED)
- External markers (from docs, web → EXTERNAL)

This enables tracking knowledge quality and confidence automatically.
"""

import logging
import re
from typing import Optional

from ..core.database import Database
from ..episodic.models import EvidenceType, EventType, CodeEventType

logger = logging.getLogger(__name__)


class EvidenceInferencer:
    """Infers evidence types for episodic events based on their characteristics."""

    # Patterns for detecting evidence type from content
    OBSERVED_KEYWORDS = [
        "observed",
        "saw",
        "confirmed",
        "verified",
        "tested",
        "ran",
        "executed",
        "output was",
        "result:",
        "confirmed that",
    ]

    INFERRED_KEYWORDS = [
        "likely",
        "probably",
        "suggests",
        "implies",
        "inferred",
        "analysis shows",
        "pattern suggests",
        "appears to",
        "seems like",
        "based on",
    ]

    HYPOTHETICAL_KEYWORDS = [
        "assume",
        "supposed",
        "would",
        "could",
        "might",
        "perhaps",
        "possibly",
        "hypothetically",
        "speculate",
        "if we",
    ]

    LEARNED_KEYWORDS = [
        "procedure",
        "workflow",
        "pattern",
        "extracted",
        "learned",
        "process",
        "steps:",
        "algorithm",
        "approach",
    ]

    EXTERNAL_KEYWORDS = ["from docs", "from web", "from external", "reference:", "documentation:"]

    def __init__(self, db: Database):
        """Initialize inferencer.

        Args:
            db: Database instance
        """
        self.db = db

    async def infer_evidence_type(self, event_id: int) -> Optional[EvidenceType]:
        """Infer evidence type for an event based on its characteristics.

        Args:
            event_id: ID of the episodic event

        Returns:
            Inferred EvidenceType, or None if inference failed
        """
        try:
            async with self.db.get_connection() as conn:
                result = await conn.execute(
                    """
                    SELECT
                        id, content, event_type, code_event_type,
                        outcome, learned, confidence,
                        file_path, symbol_name
                    FROM episodic_events
                    WHERE id = %s
                    """,
                    (event_id,),
                )

                row = await result.fetchone()
                if not row:
                    return None

                event_dict = dict(row)
                evidence_type = self._infer_type_from_event(event_dict)

                # Update the event with inferred evidence type
                if evidence_type:
                    await conn.execute(
                        """
                        UPDATE episodic_events
                        SET evidence_type = %s
                        WHERE id = %s
                        """,
                        (evidence_type.value, event_id),
                    )

                return evidence_type

        except Exception as e:
            logger.error(f"Error inferring evidence type for event {event_id}: {e}")
            return None

    async def infer_evidence_batch(self, limit: int = 1000) -> int:
        """Infer evidence types for batch of events without evidence.

        Called during consolidation dream to populate evidence types.

        Args:
            limit: Maximum number of events to process

        Returns:
            Number of events updated with inferred evidence types
        """
        try:
            async with self.db.get_connection() as conn:
                # Find events without explicit evidence type (will be null or 'observed')
                result = await conn.execute(
                    """
                    SELECT id FROM episodic_events
                    WHERE evidence_type IS NULL OR evidence_type = 'observed'
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (limit,),
                )

                event_ids = [row[0] for row in await result.fetchall()]
                count = 0

                for event_id in event_ids:
                    inferred = await self.infer_evidence_type(event_id)
                    if inferred:
                        count += 1

                if count > 0:
                    logger.info(f"Inferred evidence types for {count}/{len(event_ids)} events")

                return count

        except Exception as e:
            logger.error(f"Error in batch evidence inference: {e}")
            return 0

    def _infer_type_from_event(self, event: dict) -> Optional[EvidenceType]:
        """Infer evidence type from event characteristics.

        Priority order:
        1. Code event type (CODE_EDIT, TEST_RUN → OBSERVED)
        2. Outcome (SUCCESS/FAILURE → OBSERVED)
        3. Content keywords (highest scoring match)
        4. Learned field presence → LEARNED
        5. Default: OBSERVED

        Args:
            event: Event dict with fields

        Returns:
            Inferred EvidenceType
        """
        content = (event.get("content") or "").lower()
        event_type = event.get("event_type")
        code_event_type = event.get("code_event_type")
        outcome = event.get("outcome")
        learned = event.get("learned")

        # 1. Code event type - direct observation
        if code_event_type:
            try:
                cet = CodeEventType(code_event_type)
                if cet in [
                    CodeEventType.CODE_EDIT,
                    CodeEventType.TEST_RUN,
                    CodeEventType.BUG_DISCOVERY,
                    CodeEventType.PERFORMANCE_PROFILE,
                ]:
                    return EvidenceType.OBSERVED
                elif cet == CodeEventType.ARCHITECTURE_DECISION:
                    return EvidenceType.DEDUCED
            except ValueError:
                pass

        # 2. Event outcome - SUCCESS/FAILURE are observations
        if outcome in ["success", "failure"]:
            return EvidenceType.OBSERVED

        # 3. Learned field present - procedure extraction
        if learned and len(learned) > 10:
            return EvidenceType.LEARNED

        # 4. Content keyword matching
        scores = {
            EvidenceType.OBSERVED: self._count_keywords(content, self.OBSERVED_KEYWORDS),
            EvidenceType.INFERRED: self._count_keywords(content, self.INFERRED_KEYWORDS),
            EvidenceType.HYPOTHETICAL: self._count_keywords(content, self.HYPOTHETICAL_KEYWORDS),
            EvidenceType.LEARNED: self._count_keywords(content, self.LEARNED_KEYWORDS),
            EvidenceType.EXTERNAL: self._count_keywords(content, self.EXTERNAL_KEYWORDS),
        }

        # Find highest scoring type
        best_type = max(scores, key=scores.get)
        if scores[best_type] > 0:
            return best_type

        # 5. Default
        return EvidenceType.OBSERVED

    @staticmethod
    def _count_keywords(text: str, keywords: list[str]) -> int:
        """Count keyword matches in text.

        Args:
            text: Text to search
            keywords: Keywords to look for

        Returns:
            Number of keyword matches (case-insensitive, word boundaries)
        """
        count = 0
        for keyword in keywords:
            # Use word boundaries to avoid partial matches
            pattern = r"\b" + re.escape(keyword) + r"\b"
            matches = len(re.findall(pattern, text, re.IGNORECASE))
            count += matches
        return count

    async def infer_evidence_quality(self, event_id: int) -> float:
        """Infer evidence quality score (0-1) for an event.

        Based on:
        - Event confidence (if explicit)
        - Multiple confirmations (high activation_count)
        - Recency (recent events are higher quality)
        - Outcome clarity (SUCCESS is higher than ONGOING)

        Args:
            event_id: Event ID

        Returns:
            Evidence quality score (0.0-1.0)
        """
        try:
            async with self.db.get_connection() as conn:
                result = await conn.execute(
                    """
                    SELECT
                        confidence, activation_count, outcome,
                        timestamp, consolidation_score
                    FROM episodic_events
                    WHERE id = %s
                    """,
                    (event_id,),
                )

                row = await result.fetchone()
                if not row:
                    return 0.5

                confidence, activation_count, outcome, timestamp, consolidation_score = row

                # Base quality from explicit confidence
                quality = float(confidence) if confidence else 0.7

                # Boost for multiple activations (evidence of importance)
                if activation_count > 0:
                    activation_boost = min(0.2, activation_count * 0.05)
                    quality = min(1.0, quality + activation_boost)

                # Boost for successful outcomes
                if outcome == "success":
                    quality = min(1.0, quality + 0.1)

                # Consolidation status (already extracted patterns)
                if consolidation_score > 0.5:
                    quality = min(1.0, quality + 0.1)

                return quality

        except Exception as e:
            logger.error(f"Error inferring evidence quality for {event_id}: {e}")
            return 0.5
