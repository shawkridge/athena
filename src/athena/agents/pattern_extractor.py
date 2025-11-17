"""Pattern Extractor Agent - Autonomously extracts learnable patterns at session end.

The Pattern Extractor Agent runs at the end of each session and analyzes recent
episodic events to extract reusable procedures and patterns. It consolidates
learning without requiring explicit user action.

This agent:
1. Retrieves recent episodic events
2. Analyzes them for repeated sequences
3. Extracts workflows as procedures
4. Stores learned patterns
5. Tracks extraction quality

The agent works with the consolidation layer to identify patterns that have
high confidence and reusability.
"""

import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta

# Import coordinator base class
from .coordinator import AgentCoordinator

# Import core operations
from ..episodic.operations import recall_recent, get_by_session
from ..consolidation.operations import consolidate, extract_patterns
from ..procedural.operations import extract_procedure as extract_proc

logger = logging.getLogger(__name__)


class PatternExtractorAgent(AgentCoordinator):
    """Autonomously extracts and learns patterns from session events.

    Inherits from AgentCoordinator to coordinate with other agents via shared memory.
    """

    def __init__(self):
        """Initialize the Pattern Extractor Agent."""
        super().__init__(
            agent_id="pattern-extractor",
            agent_type="pattern-extractor",
        )
        self.patterns_extracted = 0
        self.consolidation_runs = 0
        self.last_run: Optional[datetime] = None

    async def extract_patterns_from_session(
        self, session_id: str, min_confidence: float = 0.8
    ) -> Dict[str, Any]:
        """Extract patterns from a completed session.

        Retrieves recent episodic events from the session and uses the
        consolidation layer to extract high-quality patterns and procedures.

        Args:
            session_id: Session ID to analyze
            min_confidence: Minimum confidence for pattern acceptance (0.0-1.0)

        Returns:
            Dictionary with extraction results
        """
        logger.info(f"Pattern Extractor starting analysis of session {session_id}")
        self.consolidation_runs += 1
        self.last_run = datetime.utcnow()

        try:
            # Step 1: Retrieve recent events from this session
            events = await get_by_session(session_id, limit=50)
            logger.info(f"Retrieved {len(events)} events from session {session_id}")

            if not events:
                logger.warning(f"No events found for session {session_id}")
                return {
                    "status": "success",
                    "session_id": session_id,
                    "events_analyzed": 0,
                    "clusters_found": 0,
                    "patterns_extracted": 0,
                    "timestamp": datetime.utcnow().isoformat(),
                }

            # Step 2: Use consolidation layer to extract patterns
            # The consolidation layer handles clustering and pattern extraction
            consolidation_result = await consolidate(strategy="balanced")
            logger.info(f"Consolidation result: {consolidation_result}")

            # Step 3: Extract high-confidence patterns
            patterns_result = await extract_patterns(
                min_confidence=min_confidence,
                limit=10,
            )
            logger.info(f"Extracted {len(patterns_result)} high-confidence patterns")

            self.patterns_extracted += len(patterns_result)

            # Emit event for other agents to observe
            if len(patterns_result) > 0:
                try:
                    await self.emit_event(
                        event_type="patterns_extracted",
                        content=(
                            f"Extracted {len(patterns_result)} patterns from "
                            f"{len(events)} events in session {session_id}"
                        ),
                        tags=["consolidation", "learning", f"session:{session_id}"],
                        importance=0.85,
                    )
                except Exception as e:
                    logger.warning(f"Failed to emit pattern extraction event: {e}")

                # Share high-confidence patterns as knowledge
                for pattern in patterns_result[:3]:  # Share top 3
                    try:
                        await self.share_knowledge(
                            content=f"Pattern: {pattern}",
                            topics=["consolidation", "pattern"],
                            confidence=0.8,
                        )
                    except Exception as e:
                        logger.warning(f"Failed to share pattern: {e}")

            return {
                "status": "success",
                "session_id": session_id,
                "events_analyzed": len(events),
                "patterns_extracted": len(patterns_result),
                "consolidation_strategy": "balanced",
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error during pattern extraction: {e}", exc_info=True)
            return {
                "status": "error",
                "session_id": session_id,
                "error": str(e),
            }

    async def _cluster_events(self, events: List[Dict[str, Any]]) -> List[List[Dict]]:
        """Cluster events by similarity.

        Simplified clustering based on event type and tools used.

        Args:
            events: List of episodic events

        Returns:
            List of clusters, each containing similar events
        """
        if not events:
            return []

        # Simple clustering by event type
        clusters: Dict[str, List[Dict]] = {}
        for event in events:
            event_type = event.get("type", "unknown")
            if event_type not in clusters:
                clusters[event_type] = []
            clusters[event_type].append(event)

        return list(clusters.values())

    async def _extract_procedure_from_cluster(
        self, cluster: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Extract a reusable procedure from a cluster of similar events.

        Args:
            cluster: List of similar events

        Returns:
            Procedure dict with name, steps, confidence, or None
        """
        if len(cluster) < 2:
            return None

        # Simplified extraction: use first event as template
        first_event = cluster[0]

        # Calculate confidence based on cluster homogeneity
        confidence = min(
            1.0,
            len(cluster) / 10.0,  # More repetitions = higher confidence
        )

        return {
            "name": f"Procedure from {first_event.get('type', 'unknown')}",
            "description": f"Extracted from {len(cluster)} similar events",
            "steps": [e.get("content", "") for e in cluster[:3]],  # First 3 steps
            "confidence": confidence,
            "event_count": len(cluster),
        }

    async def run_consolidation_cycle(self) -> Dict[str, Any]:
        """Run a complete consolidation cycle.

        This combines pattern extraction with memory consolidation using
        the dual-process consolidation approach (fast heuristic + slow LLM validation).
        Called at session end.

        Returns:
            Consolidation report
        """
        logger.info("Starting consolidation cycle")

        try:
            # Run the consolidation layer with balanced strategy
            # This triggers dual-process consolidation:
            # - System 1: Fast statistical clustering and heuristic extraction
            # - System 2: LLM validation for uncertain patterns (confidence 0.4-0.6)
            consolidation_result = await consolidate(strategy="balanced")
            logger.info(f"Consolidation completed: {consolidation_result}")

            # Get the metrics from consolidation
            metrics = consolidation_result.get("metrics", {}) if consolidation_result else {}

            report = {
                "status": "completed",
                "timestamp": datetime.utcnow().isoformat(),
                "patterns_extracted": self.patterns_extracted,
                "consolidation_runs": self.consolidation_runs,
                "last_run": self.last_run.isoformat() if self.last_run else None,
                "consolidation_metrics": metrics,
            }

            logger.info(f"Consolidation cycle complete: {report}")
            return report

        except Exception as e:
            logger.error(f"Error during consolidation cycle: {e}", exc_info=True)
            return {
                "status": "error",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
            }

    def get_statistics(self) -> Dict[str, Any]:
        """Get agent statistics.

        Returns:
            Dictionary with extraction metrics
        """
        return {
            "patterns_extracted": self.patterns_extracted,
            "consolidation_runs": self.consolidation_runs,
            "last_run": self.last_run.isoformat() if self.last_run else None,
        }


# Singleton instance
_extractor: Optional[PatternExtractorAgent] = None


def get_extractor() -> PatternExtractorAgent:
    """Get or create the Pattern Extractor Agent singleton.

    Returns:
        PatternExtractorAgent instance
    """
    global _extractor
    if _extractor is None:
        _extractor = PatternExtractorAgent()
    return _extractor


async def extract_session_patterns(
    session_id: str, min_confidence: float = 0.8
) -> Dict[str, Any]:
    """Convenience function to extract patterns from a session.

    Args:
        session_id: Session to analyze
        min_confidence: Minimum confidence threshold

    Returns:
        Extraction results
    """
    extractor = get_extractor()
    return await extractor.extract_patterns_from_session(session_id, min_confidence)


async def run_consolidation() -> Dict[str, Any]:
    """Convenience function to run consolidation cycle.

    Returns:
        Consolidation report
    """
    extractor = get_extractor()
    return await extractor.run_consolidation_cycle()
