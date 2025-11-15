"""Semantic context enricher for working memory optimization.

This module enriches episodic events with:
1. Vector embeddings for semantic search
2. LLM-based importance/actionability scoring
3. Cross-project discovery linking
4. Related memories finding
"""

import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
import requests

logger = logging.getLogger(__name__)


class SemanticContextEnricher:
    """Enriches events with semantic embeddings and LLM-based scoring."""

    def __init__(
        self,
        embeddings_url: str = "http://localhost:8001",
        reasoning_url: str = "http://localhost:8002",
    ):
        """Initialize enricher with local model endpoints.

        Args:
            embeddings_url: URL to nomic-embed-text service
            reasoning_url: URL to reasoning model service (Qwen)
        """
        self.embeddings_url = embeddings_url
        self.reasoning_url = reasoning_url
        self._test_connections()

    def _test_connections(self):
        """Test connections to local models."""
        try:
            # Test embeddings service
            response = requests.post(
                f"{self.embeddings_url}/embeddings",
                json={"input": "test", "model": "nomic-embed-text"},
                timeout=5
            )
            if response.status_code == 200:
                logger.info("✓ Embeddings service (nomic-embed-text) available")
            else:
                logger.warning(f"Embeddings service returned {response.status_code}")
        except Exception as e:
            logger.warning(f"Embeddings service not available: {e}")

        try:
            # Test reasoning service
            response = requests.get(f"{self.reasoning_url}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✓ Reasoning service available: {data.get('model')}")
            else:
                logger.warning(f"Reasoning service returned {response.status_code}")
        except Exception as e:
            logger.warning(f"Reasoning service not available: {e}")

    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for text using local model.

        Args:
            text: Text to embed

        Returns:
            Vector embedding (768D) or None if service unavailable
        """
        try:
            response = requests.post(
                f"{self.embeddings_url}/embeddings",
                json={"input": text, "model": "nomic-embed-text"},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if "embedding" in data:
                    return data["embedding"]
                elif "embeddings" in data and len(data["embeddings"]) > 0:
                    return data["embeddings"][0]
        except Exception as e:
            logger.debug(f"Embedding generation failed: {e}")

        return None

    def score_importance_with_llm(
        self,
        event_type: str,
        content: str,
        outcome: str,
        project_goal: Optional[str] = None
    ) -> float:
        """Score importance using LLM reasoning + heuristics.

        Uses reasoning model to understand semantic importance of the event
        in context of project goals.

        Args:
            event_type: Type of event (discovery, action, decision, etc.)
            content: Event description
            outcome: Event outcome (success, failure, partial)
            project_goal: Current project goal for context

        Returns:
            Importance score (0.0-1.0)
        """
        # Base heuristic score
        base_score = self._heuristic_importance(event_type, outcome)

        # Try to enhance with LLM if available
        try:
            llm_score = self._llm_importance_score(event_type, content, outcome, project_goal)
            if llm_score is not None:
                # Blend heuristic and LLM scores (60% heuristic, 40% LLM)
                return 0.6 * base_score + 0.4 * llm_score
        except Exception as e:
            logger.debug(f"LLM scoring failed, using heuristic: {e}")

        return base_score

    def _heuristic_importance(self, event_type: str, outcome: str) -> float:
        """Heuristic importance scoring."""
        score = 0.5  # Default

        # Event type weights
        type_weights = {
            "discovery": 0.9,
            "decision": 0.85,
            "error": 0.8,
            "success": 0.7,
            "action": 0.6,
            "conversation": 0.5,
            "test": 0.65,
        }

        for event_key, weight in type_weights.items():
            if event_key in event_type.lower():
                score = weight
                break

        # Outcome modifiers
        if outcome == "failure":
            score = min(0.95, score + 0.15)  # Failures are important to learn from
        elif outcome == "success":
            score = max(0.5, score - 0.1)  # Success but less critical than failure

        return min(1.0, max(0.0, score))

    def _llm_importance_score(
        self,
        event_type: str,
        content: str,
        outcome: str,
        project_goal: Optional[str] = None
    ) -> Optional[float]:
        """Use reasoning model to score importance.

        Args:
            event_type: Type of event
            content: Event description
            outcome: Event outcome
            project_goal: Project goal context

        Returns:
            Score (0.0-1.0) or None if service unavailable
        """
        try:
            # Build prompt for importance assessment
            goal_context = f"\nProject Goal: {project_goal}" if project_goal else ""
            prompt = f"""Assess the importance of this event (0.0-1.0 scale):

Event Type: {event_type}
Outcome: {outcome}
Description: {content[:200]}{goal_context}

Respond with ONLY a number between 0.0 and 1.0, nothing else."""

            response = requests.post(
                f"{self.reasoning_url}/completions",
                json={
                    "prompt": prompt,
                    "max_tokens": 10,
                    "temperature": 0.3,
                },
                timeout=15
            )

            if response.status_code == 200:
                data = response.json()
                text = data.get("choices", [{}])[0].get("text", "").strip()
                try:
                    score = float(text)
                    return min(1.0, max(0.0, score))
                except ValueError:
                    logger.debug(f"Could not parse LLM score: {text}")
        except Exception as e:
            logger.debug(f"LLM reasoning failed: {e}")

        return None

    def find_related_discoveries(
        self,
        embedding: List[float],
        conn,
        project_id: int,
        similarity_threshold: float = 0.7,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Find related discoveries using semantic similarity.

        Args:
            embedding: Query embedding vector
            conn: Database connection
            project_id: Project ID to search within
            similarity_threshold: Minimum similarity (0.0-1.0)
            limit: Maximum results

        Returns:
            List of related discoveries with similarity scores
        """
        try:
            # Convert embedding to pgvector format
            embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"

            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, content, event_type, timestamp,
                       1 - (embedding <=> %s::vector) as similarity
                FROM episodic_events
                WHERE project_id = %s
                  AND event_type LIKE '%discovery%'
                  AND 1 - (embedding <=> %s::vector) > %s
                ORDER BY similarity DESC
                LIMIT %s
                """,
                (embedding_str, project_id, embedding_str, similarity_threshold, limit)
            )

            results = []
            for row in cursor.fetchall():
                results.append({
                    "id": row[0],
                    "content": row[1],
                    "type": row[2],
                    "timestamp": row[3],
                    "similarity": float(row[4]) if row[4] else 0.0,
                })

            return results
        except Exception as e:
            logger.warning(f"Failed to find related discoveries: {e}")
            return []

    def find_cross_project_discoveries(
        self,
        embedding: List[float],
        conn,
        current_project_id: int,
        similarity_threshold: float = 0.8,
        limit: int = 3
    ) -> List[Dict[str, Any]]:
        """Find related discoveries in other projects.

        Args:
            embedding: Query embedding vector
            conn: Database connection
            current_project_id: Current project ID (to exclude)
            similarity_threshold: Minimum similarity (higher for cross-project)
            limit: Maximum results

        Returns:
            List of discoveries from other projects
        """
        try:
            embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"

            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT e.id, e.project_id, p.name, e.content, e.event_type,
                       e.timestamp,
                       1 - (e.embedding <=> %s::vector) as similarity
                FROM episodic_events e
                JOIN projects p ON e.project_id = p.id
                WHERE e.project_id != %s
                  AND e.event_type LIKE '%discovery%'
                  AND 1 - (e.embedding <=> %s::vector) > %s
                ORDER BY similarity DESC
                LIMIT %s
                """,
                (embedding_str, current_project_id, embedding_str, similarity_threshold, limit)
            )

            results = []
            for row in cursor.fetchall():
                results.append({
                    "id": row[0],
                    "from_project_id": row[1],
                    "from_project": row[2],
                    "content": row[3],
                    "type": row[4],
                    "timestamp": row[5],
                    "similarity": float(row[6]) if row[6] else 0.0,
                })

            return results
        except Exception as e:
            logger.warning(f"Failed to find cross-project discoveries: {e}")
            return []

    def link_related_discoveries(
        self,
        conn,
        event_id: int,
        related_discoveries: List[Dict[str, Any]]
    ) -> int:
        """Create links between related discoveries.

        Args:
            conn: Database connection
            event_id: Source event ID
            related_discoveries: List of related discoveries

        Returns:
            Number of links created
        """
        if not related_discoveries:
            return 0

        links_created = 0
        try:
            cursor = conn.cursor()

            for related in related_discoveries:
                try:
                    # Create bidirectional relationship
                    cursor.execute(
                        """
                        INSERT INTO event_relations
                        (from_event_id, to_event_id, relation_type, strength)
                        VALUES (%s, %s, 'semantic_related', %s)
                        ON CONFLICT (from_event_id, to_event_id) DO UPDATE
                        SET strength = GREATEST(strength, EXCLUDED.strength)
                        """,
                        (event_id, related["id"], related.get("similarity", 0.7))
                    )
                    links_created += 1

                    # Reverse link (unless cross-project)
                    if "from_project_id" not in related:
                        cursor.execute(
                            """
                            INSERT INTO event_relations
                            (from_event_id, to_event_id, relation_type, strength)
                            VALUES (%s, %s, 'semantic_related', %s)
                            ON CONFLICT (from_event_id, to_event_id) DO UPDATE
                            SET strength = GREATEST(strength, EXCLUDED.strength)
                            """,
                            (related["id"], event_id, related.get("similarity", 0.7))
                        )
                except Exception as e:
                    logger.warning(f"Failed to link discovery {related['id']}: {e}")

            conn.commit()
        except Exception as e:
            logger.error(f"Failed to create discovery links: {e}")

        return links_created

    def enrich_event_with_semantics(
        self,
        conn,
        project_id: int,
        event_id: int,
        event_type: str,
        content: str,
        outcome: Optional[str] = None,
        project_goal: Optional[str] = None
    ) -> Dict[str, Any]:
        """Fully enrich an event with semantic information.

        Args:
            conn: Database connection
            project_id: Project ID
            event_id: Event ID to enrich
            event_type: Type of event
            content: Event content
            outcome: Event outcome
            project_goal: Project goal for context

        Returns:
            Dictionary with enrichment results
        """
        results = {
            "event_id": event_id,
            "embedding_generated": False,
            "importance_scored": False,
            "related_found": 0,
            "cross_project_found": 0,
            "links_created": 0,
        }

        try:
            # Generate embedding
            embedding = self.generate_embedding(content)
            if embedding:
                results["embedding_generated"] = True
                results["embedding_dim"] = len(embedding)

                # Store embedding in database
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE episodic_events SET embedding = %s WHERE id = %s",
                    (embedding, event_id)
                )

                # Find related discoveries
                related = self.find_related_discoveries(
                    embedding, conn, project_id, limit=5
                )
                if related:
                    results["related_found"] = len(related)

                    # Find cross-project discoveries
                    cross = self.find_cross_project_discoveries(
                        embedding, conn, project_id, limit=3
                    )
                    results["cross_project_found"] = len(cross)

                    # Link all related discoveries
                    all_related = related + cross
                    links = self.link_related_discoveries(
                        conn, event_id, all_related
                    )
                    results["links_created"] = links

            # Score importance with LLM
            importance = self.score_importance_with_llm(
                event_type, content, outcome, project_goal
            )
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE episodic_events SET importance_score = %s WHERE id = %s",
                (importance, event_id)
            )
            results["importance_scored"] = True
            results["importance_score"] = importance

            conn.commit()

        except Exception as e:
            logger.error(f"Failed to enrich event {event_id}: {e}")

        return results
