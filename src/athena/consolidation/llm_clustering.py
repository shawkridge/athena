"""LLM-powered semantic consolidation with pattern clustering.

Uses LLM to cluster episodic events into semantic patterns during consolidation.
"""

import json
import logging
from dataclasses import dataclass
from typing import Optional

from ..rag.llm_client import OllamaLLMClient

logger = logging.getLogger(__name__)


@dataclass
class SemanticCluster:
    """A semantic cluster of related episodic events."""

    cluster_id: int
    pattern_name: str
    description: str
    event_ids: list[int]
    event_count: int
    confidence: float  # 0.0-1.0: How confident is this clustering?
    generalized_pattern: str  # General description applicable to future events
    frequency: str  # "rare", "occasional", "frequent", "very frequent"


class LLMConsolidationClusterer:
    """Cluster episodic events into semantic patterns using LLM reasoning."""

    def __init__(self, llm_client: Optional[OllamaLLMClient] = None):
        """Initialize consolidation clusterer.

        Args:
            llm_client: Optional LLM client for semantic clustering
        """
        self.llm_client = llm_client
        self._use_llm = llm_client is not None

        if self._use_llm:
            logger.info("LLM consolidation clusterer: Semantic clustering enabled")
        else:
            logger.info("LLM consolidation clusterer: Using heuristic clustering")

    def cluster_events(
        self, events: list[dict], limit: int = 20
    ) -> list[SemanticCluster]:
        """Cluster episodic events into semantic patterns.

        Args:
            events: List of episodic events with content and type
            limit: Maximum number of clusters to generate

        Returns:
            List of semantic clusters with generalized patterns
        """
        if not events:
            return []

        if self._use_llm:
            return self._cluster_with_llm(events, limit)
        else:
            return self._cluster_heuristic(events, limit)

    def _cluster_with_llm(
        self, events: list[dict], limit: int
    ) -> list[SemanticCluster]:
        """Cluster events using LLM semantic analysis."""

        try:
            # Prepare event summaries for clustering
            event_summaries = []
            for i, event in enumerate(events[:50]):  # Limit to 50 events for efficiency
                content = event.get("content", "")[:100]  # Truncate
                event_type = event.get("event_type", "action")
                event_summaries.append(f"{i}. [{event_type}] {content}")

            events_str = "\n".join(event_summaries)

            prompt = f"""Analyze these episodic events and identify semantic patterns/clusters.

EVENTS:
{events_str}

For each cluster, identify:
1. What is the common theme or pattern?
2. Which events belong to this cluster?
3. How frequently does this pattern occur?
4. What is a generalized pattern that would apply to similar future events?

Group similar events together. Focus on meaningful patterns (debugging, optimization, refactoring, etc.).

Respond with JSON:
{{
    "clusters": [
        {{
            "pattern_name": "...",
            "description": "...",
            "event_ids": [0, 1, 3],
            "confidence": 0.0-1.0,
            "generalized_pattern": "...",
            "frequency": "rare|occasional|frequent|very frequent"
        }}
    ]
}}

Be selective - only include meaningful clusters."""

            result = self.llm_client.generate(prompt, max_tokens=500)
            analysis = json.loads(result)

            clusters = []
            for i, cluster_data in enumerate(analysis.get("clusters", [])[:limit]):
                cluster = SemanticCluster(
                    cluster_id=i,
                    pattern_name=cluster_data.get("pattern_name", "Pattern"),
                    description=cluster_data.get("description", ""),
                    event_ids=cluster_data.get("event_ids", []),
                    event_count=len(cluster_data.get("event_ids", [])),
                    confidence=float(cluster_data.get("confidence", 0.7)),
                    generalized_pattern=cluster_data.get("generalized_pattern", ""),
                    frequency=cluster_data.get("frequency", "occasional"),
                )
                clusters.append(cluster)

            logger.info(f"LLM identified {len(clusters)} semantic clusters from {len(events)} events")
            return clusters

        except json.JSONDecodeError as e:
            logger.debug(f"Failed to parse LLM response: {e}")
            return self._cluster_heuristic(events, limit)
        except Exception as e:
            logger.debug(f"LLM clustering failed: {e}")
            return self._cluster_heuristic(events, limit)

    def _cluster_heuristic(
        self, events: list[dict], limit: int
    ) -> list[SemanticCluster]:
        """Cluster events using heuristic rules (fallback)."""

        # Group by event type
        clusters_by_type = {}
        for i, event in enumerate(events):
            event_type = event.get("event_type", "action")
            if event_type not in clusters_by_type:
                clusters_by_type[event_type] = []
            clusters_by_type[event_type].append(i)

        # Convert to semantic clusters
        clusters = []
        type_to_name = {
            "error": "Error Handling",
            "debugging": "Debugging Sessions",
            "refactoring": "Code Refactoring",
            "testing": "Testing & Validation",
            "deployment": "Deployment Activities",
            "success": "Successful Completions",
            "decision": "Key Decisions",
            "action": "Implementation Work",
        }

        for i, (event_type, event_ids) in enumerate(clusters_by_type.items()):
            if i >= limit:
                break

            pattern_name = type_to_name.get(event_type, f"{event_type.title()} Work")
            cluster = SemanticCluster(
                cluster_id=i,
                pattern_name=pattern_name,
                description=f"Events related to {event_type}",
                event_ids=event_ids,
                event_count=len(event_ids),
                confidence=0.6,  # Lower confidence for heuristic
                generalized_pattern=f"When encountering {event_type} scenarios, follow established practices",
                frequency="frequent" if len(event_ids) > 5 else "occasional",
            )
            clusters.append(cluster)

        logger.info(f"Heuristic identified {len(clusters)} clusters from {len(events)} events")
        return clusters

    def extract_reusable_patterns(self, cluster: SemanticCluster) -> dict:
        """Extract reusable pattern from a cluster.

        Returns dict with:
        - name: Pattern name
        - description: Pattern description
        - steps: Generalized steps
        - context: When to use
        - success_rate: Expected success rate
        """
        if not self._use_llm:
            return {
                "name": cluster.pattern_name,
                "description": cluster.description,
                "steps": ["Step 1", "Step 2", "Step 3"],
                "context": cluster.generalized_pattern,
                "success_rate": 0.7,
            }

        try:
            prompt = f"""Extract a reusable pattern from this semantic cluster.

PATTERN: {cluster.pattern_name}
DESCRIPTION: {cluster.description}
GENERALIZED: {cluster.generalized_pattern}
FREQUENCY: {cluster.frequency}
CONFIDENCE: {cluster.confidence:.0%}

Generate concrete, reusable steps for this pattern that can be applied to future similar situations.

Respond with JSON:
{{
    "name": "...",
    "description": "...",
    "steps": ["step 1", "step 2", "step 3", "step 4"],
    "context": "When to use this pattern",
    "success_rate": 0.0-1.0,
    "tips": ["tip 1", "tip 2"]
}}"""

            result = self.llm_client.generate(prompt, max_tokens=300)
            return json.loads(result)

        except Exception as e:
            logger.debug(f"Failed to extract pattern: {e}")
            return {
                "name": cluster.pattern_name,
                "description": cluster.description,
                "steps": ["Identify context", "Follow cluster approach", "Evaluate results"],
                "context": cluster.generalized_pattern,
                "success_rate": 0.7,
                "tips": [],
            }
