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
from ..episodic.models import EvidenceType

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
                        id, content, event_type,
                        outcome, learned, confidence
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
        """Infer evidence types for batch of events.

        Called during consolidation dream to populate evidence types.
        Processes most recent events first to prioritize recency.

        Args:
            limit: Maximum number of events to process per batch

        Returns:
            Number of events updated with inferred evidence types
        """
        try:
            async with self.db.get_connection() as conn:
                # Get batch of events ordered by recency (only those without evidence_type)
                result = await conn.execute(
                    """
                    SELECT id, content, event_type, outcome, learned, confidence
                    FROM episodic_events
                    WHERE evidence_type IS NULL
                    ORDER BY timestamp DESC
                    LIMIT %s
                    """,
                    (limit,),
                )

                rows = await result.fetchall()
                count = 0

                # Process each event and infer its type
                for row in rows:
                    try:
                        event_id = row[0]
                        # Build dict manually from row tuple
                        event_dict = {
                            "id": row[0],
                            "content": row[1],
                            "event_type": row[2],
                            "outcome": row[3],
                            "learned": row[4],
                            "confidence": row[5],
                        }

                        # Infer the evidence type
                        inferred_type = self._infer_type_from_event(event_dict)

                        if inferred_type:
                            # Update the event with inferred type
                            await conn.execute(
                                """
                                UPDATE episodic_events
                                SET evidence_type = %s
                                WHERE id = %s
                                """,
                                (inferred_type.value, event_id),
                            )
                            count += 1
                    except Exception as e:
                        logger.debug(f"Error inferring type for event {event_id}: {e}")
                        continue

                if count > 0:
                    logger.info(f"Inferred evidence types for {count}/{len(rows)} events")

                return count

        except Exception as e:
            logger.error(f"Error in batch evidence inference: {e}")
            return 0

    def _infer_type_from_event(self, event: dict) -> Optional[EvidenceType]:
        """Infer evidence type from event characteristics.

        Priority order:
        1. Event type keywords (tool_execution, code_edit → OBSERVED)
        2. Outcome (success/failure → OBSERVED)
        3. Content keywords (highest scoring match)
        4. Learned field presence → LEARNED
        5. Default: OBSERVED

        Args:
            event: Event dict with fields

        Returns:
            Inferred EvidenceType
        """
        content = (event.get("content") or "").lower()
        event_type = (event.get("event_type") or "").lower()
        outcome = (event.get("outcome") or "").lower()
        learned = event.get("learned")

        # 1. Event type - direct observation for code/tool-related events
        # Note: event_type is stored as string in database, not enum
        if event_type:
            # Tool execution and code-related events are observations
            if event_type in [
                "tool_execution",
                "code_edit",
                "test_run",
                "bug_discovery",
                "tool_use",
                "test:edge_case",
                "discovery:analysis",
            ]:
                return EvidenceType.OBSERVED
            # Learning and consolidation events are learned
            elif event_type in [
                "learning",
                "consolidation_session",
                "consolidation:session",
            ]:
                return EvidenceType.LEARNED

        # 2. Event outcome - success/failure are observations
        if outcome in ["success", "failure", "recorded"]:
            return EvidenceType.OBSERVED

        # 3. Learned field present - procedure extraction
        if learned and len(str(learned)) > 10:
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

        # 5. Default: tool_execution and unknown types → OBSERVED
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
