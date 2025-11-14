"""Consolidation Quality Metrics - Measure episodic→semantic consolidation effectiveness.

Based on: Chen et al. 2024 "Memory-Augmented Transformers"
Key Innovation: Quantify information loss and compression during consolidation

Metrics:
1. Compression Ratio: 1 - (semantic_tokens / episodic_tokens) [Target: 0.7-0.85]
2. Retrieval Recall: Can semantic memories reconstruct episodic events? [Target: >0.80]
3. Pattern Consistency: Do patterns match actual sequences? [Target: >0.75]
4. Information Density: Relevant info per token in semantic memory [Target: >0.7]
"""

import math
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np

from ..episodic.models import EpisodicEvent
from ..episodic.store import EpisodicStore
from ..memory.store import MemoryStore


class ConsolidationQualityMetrics:
    """Measure episodic→semantic consolidation effectiveness."""

    def __init__(
        self,
        episodic_store: EpisodicStore,
        semantic_store: MemoryStore,
    ):
        """Initialize consolidation quality metrics.

        Args:
            episodic_store: Store for episodic events
            semantic_store: Store for semantic memories
        """
        self.episodic_store = episodic_store
        self.semantic_store = semantic_store

    def measure_compression_ratio(self, session_id: str) -> float:
        """Measure compression achieved by consolidation.

        Compression = 1 - (semantic_tokens / episodic_tokens)
        - High compression = good (patterns are concise)
        - Low compression = patterns are verbose
        - Target: 0.7-0.85 (70-85% compression)

        Args:
            session_id: Session to measure

        Returns:
            Compression ratio (0-1, higher is better)
        """
        try:
            episodic_events = self.episodic_store.get_events_by_session(session_id)
            if not episodic_events:
                return 0.0

            # Count tokens in episodic events
            episodic_tokens = sum(len(e.content.split()) for e in episodic_events)
            if episodic_tokens == 0:
                return 0.0

            # Count tokens in semantic memories from this session
            # Get all memories from session (query via database directly)
            cursor = self.semantic_store.db.get_cursor()
            # Use CURRENT_TIMESTAMP - INTERVAL for PostgreSQL
            cursor.execute(
                "SELECT content FROM memory_vectors WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '24 hours' LIMIT 1000"
            )
            semantic_memories = cursor.fetchall()
            # Handle both dict-like rows (psycopg3) and tuple rows
            semantic_tokens = sum(
                len((row.get('content') if isinstance(row, dict) else row[0] or "").split())
                for row in semantic_memories
            )

            # Compression = 1 - (semantic / episodic)
            compression = 1.0 - (semantic_tokens / max(episodic_tokens, 1))
            return max(0.0, min(1.0, compression))  # Clamp to [0, 1]

        except Exception as e:
            import traceback
            print(f"Error measuring compression ratio: {e}")
            traceback.print_exc()
            return 0.0

    def measure_retrieval_recall(self, session_id: str) -> Dict[str, float]:
        """Measure information preservation during consolidation.

        Recall = (queries answerable from semantic) / (queries answerable from episodic)
        - High recall = consolidation preserved information
        - Low recall = consolidation lost critical details
        - Target: >0.80 (semantic captures 80%+ of episodic info)

        Args:
            session_id: Session to measure

        Returns:
            Dict with episodic_recall, semantic_recall, relative_recall, recall_loss
        """
        try:
            episodic_events = self.episodic_store.get_events_by_session(session_id)
            if not episodic_events:
                return {
                    "episodic_recall": 0.0,
                    "semantic_recall": 0.0,
                    "relative_recall": 0.0,
                    "recall_loss": 1.0,
                }

            # Generate test queries from episodic events
            test_queries = self._generate_queries(episodic_events)
            if not test_queries:
                return {
                    "episodic_recall": 0.0,
                    "semantic_recall": 0.0,
                    "relative_recall": 0.0,
                    "recall_loss": 1.0,
                }

            # Score recall from episodic
            episodic_recall = self._score_recall_episodic(test_queries, episodic_events)

            # Score recall from semantic
            semantic_recall = self._score_recall_semantic(test_queries, session_id)

            # Relative recall
            relative_recall = (
                semantic_recall / max(episodic_recall, 0.01)
                if episodic_recall > 0
                else 0.0
            )
            relative_recall = min(1.0, relative_recall)

            return {
                "episodic_recall": episodic_recall,
                "semantic_recall": semantic_recall,
                "relative_recall": relative_recall,
                "recall_loss": 1.0 - relative_recall,
            }

        except Exception as e:
            print(f"Error measuring retrieval recall: {e}")
            return {
                "episodic_recall": 0.0,
                "semantic_recall": 0.0,
                "relative_recall": 0.0,
                "recall_loss": 1.0,
            }

    def measure_pattern_consistency(self, session_id: str) -> float:
        """Measure consistency of extracted patterns.

        Consistency = Pattern explanation power vs actual entropy
        - High consistency = patterns accurately generalize
        - Low consistency = patterns are overfitted or underfitted
        - Target: >0.75

        Args:
            session_id: Session to measure

        Returns:
            Consistency score (0-1)
        """
        try:
            episodic_events = self.episodic_store.get_events_by_session(session_id)
            if len(episodic_events) < 2:
                return 0.5

            # Calculate event sequence entropy
            event_entropy = self._calculate_event_entropy(episodic_events)

            # Get semantic memories (patterns) for this session via database
            cursor = self.semantic_store.db.get_cursor()
            cursor.execute(
                "SELECT id, usefulness_score FROM memory_vectors ORDER BY created_at DESC LIMIT 100"
            )
            semantic_memories = cursor.fetchall()

            if not semantic_memories:
                return 0.0

            # Estimate pattern likelihood
            pattern_likelihood = 0.0
            for memory_row in semantic_memories:
                # Handle both dict-like Row objects and tuples
                try:
                    # Try dict-like access first (works with psycopg Row objects)
                    usefulness = float(memory_row.get("usefulness_score", 0.5))
                except (AttributeError, TypeError):
                    # Fall back to tuple access
                    try:
                        row_tuple = tuple(memory_row) if not isinstance(memory_row, tuple) else memory_row
                        usefulness = float(row_tuple[1]) if len(row_tuple) > 1 else 0.5
                    except (ValueError, IndexError):
                        usefulness = 0.5

                confidence = max(0.1, usefulness)  # Use usefulness as confidence proxy
                pattern_likelihood += confidence * math.log(confidence + 1e-10)

            # Consistency = how well pattern likelihood explains event entropy
            if event_entropy > 0:
                consistency = min(1.0, np.exp(pattern_likelihood / len(semantic_memories) - event_entropy))
            else:
                consistency = 0.5

            return max(0.0, min(1.0, consistency))

        except Exception as e:
            import traceback
            print(f"Error measuring pattern consistency: {e}")
            traceback.print_exc()
            return 0.5

    def measure_information_density(self, session_id: str) -> Dict[str, float]:
        """Measure information density of consolidated memories.

        Density = (semantic_relevance_score) / (tokens_per_memory)
        - High density = efficient, useful patterns
        - Low density = redundant or irrelevant information
        - Target: >0.7

        Args:
            session_id: Session to measure

        Returns:
            Dict with avg_density, max_density, min_density, consistency
        """
        try:
            # Get recent semantic memories from database
            cursor = self.semantic_store.db.get_cursor()
            cursor.execute(
                "SELECT id, content, usefulness_score FROM memory_vectors ORDER BY created_at DESC LIMIT 1000"
            )
            semantic_memories = cursor.fetchall()

            if not semantic_memories:
                return {
                    "avg_density": 0.0,
                    "max_density": 0.0,
                    "min_density": 0.0,
                    "consistency": 0.0,
                }

            densities = []
            for memory_row in semantic_memories:
                # Handle both dict-like Row objects and tuples
                try:
                    # Try dict-like access first (works with psycopg Row objects)
                    content = memory_row.get("content")
                    usefulness_score = float(memory_row.get("usefulness_score", 0.5))
                except (AttributeError, TypeError):
                    # Fall back to tuple access
                    try:
                        row_tuple = tuple(memory_row) if not isinstance(memory_row, tuple) else memory_row
                        content = row_tuple[1] if len(row_tuple) > 1 else None
                        usefulness_score = float(row_tuple[2]) if len(row_tuple) > 2 else 0.5
                    except (ValueError, IndexError):
                        content = None
                        usefulness_score = 0.5

                # Get tokens in memory
                tokens = len(content.split()) if content else 0
                if tokens == 0:
                    continue

                # Get relevance score (use usefulness_score as proxy)
                relevance = usefulness_score if usefulness_score else 0.5

                # Density = relevance / tokens
                density = relevance / max(tokens, 1)
                densities.append(density)

            if not densities:
                return {
                    "avg_density": 0.0,
                    "max_density": 0.0,
                    "min_density": 0.0,
                    "consistency": 0.0,
                }

            avg_density = np.mean(densities)
            max_density = np.max(densities)
            min_density = np.min(densities)
            consistency = 1.0 - (np.std(densities) / max(avg_density, 0.1))

            return {
                "avg_density": float(avg_density),
                "max_density": float(max_density),
                "min_density": float(min_density),
                "consistency": max(0.0, min(1.0, float(consistency))),
            }

        except Exception as e:
            import traceback
            print(f"Error measuring information density: {e}")
            traceback.print_exc()
            return {
                "avg_density": 0.0,
                "max_density": 0.0,
                "min_density": 0.0,
                "consistency": 0.0,
            }

    def measure_all(self, session_id: str) -> Dict[str, any]:
        """Measure all consolidation quality metrics.

        Returns:
            Dict with all metrics
        """
        return {
            "session_id": session_id,
            "measured_at": datetime.now(),
            "compression_ratio": self.measure_compression_ratio(session_id),
            "retrieval_recall": self.measure_retrieval_recall(session_id),
            "pattern_consistency": self.measure_pattern_consistency(session_id),
            "information_density": self.measure_information_density(session_id),
        }

    # Private helper methods

    def _generate_queries(self, events: List[EpisodicEvent]) -> List[str]:
        """Generate test queries from episodic events.

        Args:
            events: Episodic events

        Returns:
            List of test queries
        """
        queries = []
        for event in events[:5]:  # Sample first 5 events
            # Extract key phrases from event content
            words = event.content.split()
            if len(words) > 3:
                # Create query from first 3 words
                query = " ".join(words[:3])
                queries.append(query)
        return queries

    def _score_recall_episodic(self, queries: List[str], events: List[EpisodicEvent]) -> float:
        """Score recall using episodic events.

        Args:
            queries: Test queries
            events: Episodic events

        Returns:
            Recall score (0-1)
        """
        if not queries:
            return 0.0

        answerable = 0
        for query in queries:
            # Check if query appears in any event
            for event in events:
                if query.lower() in event.content.lower():
                    answerable += 1
                    break

        return answerable / len(queries)

    def _score_recall_semantic(self, queries: List[str], session_id: str) -> float:
        """Score recall using semantic memories.

        Args:
            queries: Test queries
            session_id: Session ID

        Returns:
            Recall score (0-1)
        """
        if not queries:
            return 0.0

        answerable = 0
        for query in queries:
            # Search semantic memories for query via recall method
            try:
                results = self.semantic_store.search.recall(
                    query=query,
                    limit=1
                )
                if results:
                    answerable += 1
            except Exception:
                # Fallback: check via database directly
                cursor = self.semantic_store.db.get_cursor()
                cursor.execute(
                    "SELECT content FROM memory_vectors WHERE content ILIKE %s LIMIT 1",
                    (f"%{query}%",)
                )
                if cursor.fetchone():
                    answerable += 1

        return answerable / len(queries)

    def _calculate_event_entropy(self, events: List[EpisodicEvent]) -> float:
        """Calculate entropy of event sequence.

        Args:
            events: Event sequence

        Returns:
            Entropy value
        """
        if len(events) < 2:
            return 0.0

        # Count event type frequencies
        type_counts = {}
        for event in events:
            event_type = str(event.event_type)
            type_counts[event_type] = type_counts.get(event_type, 0) + 1

        # Calculate Shannon entropy
        entropy = 0.0
        total = len(events)
        for count in type_counts.values():
            if count > 0:
                p = count / total
                entropy -= p * math.log(p + 1e-10)

        return entropy
