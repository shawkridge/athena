"""Salience tracking for attention system.

Salience = novelty + surprise + contradiction
Novel: semantically different from existing memories
Surprising: unexpected given context
Contradictory: conflicts with existing knowledge
"""

import pickle
from datetime import datetime
from typing import List, Optional, Tuple

import numpy as np

from ..core.database import Database
from ..core.embeddings import EmbeddingModel, cosine_similarity
from .models import SalienceScore


class SalienceTracker:
    """
    Track salience (importance/relevance) of memories.

    Salience is determined by three factors:
    - Novelty: How semantically different from existing memories (0.0-1.0)
    - Surprise: How unexpected given context (0.0-1.0, requires LLM)
    - Contradiction: Conflicts with existing knowledge (0.0-1.0, requires LLM)

    Overall salience = 0.4×novelty + 0.3×surprise + 0.3×contradiction
    """

    def __init__(self, db: Database, embedder: EmbeddingModel):
        """Initialize salience tracker.

        Args:
            db: Database connection
            embedder: Embedding model for novelty detection
        """
        self.db = db
        self.embedder = embedder

    def calculate_novelty(
        self,
        content: str,
        project_id: int,
        threshold: float = 0.8
    ) -> float:
        """Calculate novelty score by comparing to existing memories.

        Novel content is semantically different from all existing memories.
        Novelty = 1.0 - max_similarity_to_existing

        Args:
            content: Content to evaluate
            project_id: Project ID for comparison
            threshold: Similarity threshold for novelty (default 0.8)

        Returns:
            Novelty score 0.0-1.0 (1.0 = completely novel)
        """
        # Get embedding for new content
        new_embedding = self.embedder.embed(content)

        # Get recent semantic memories for comparison (limit to 100 for performance)
        with self.db.get_connection() as conn:
            cursor = conn.execute("""
                SELECT embedding FROM semantic_memory
                WHERE project_id = ?
                ORDER BY created_at DESC
                LIMIT 100
            """, (project_id,))
            existing = cursor.fetchall()

        if not existing:
            return 1.0  # First memory is novel by definition

        # Calculate max similarity to any existing memory
        max_similarity = 0.0
        for row in existing:
            if row['embedding']:
                existing_embedding = pickle.loads(row['embedding'])
                similarity = cosine_similarity(new_embedding, existing_embedding)
                max_similarity = max(max_similarity, similarity)

        # Novelty is inverse of similarity
        novelty = 1.0 - max_similarity

        return novelty

    def calculate_surprise(
        self,
        content: str,
        context: List[str],
        llm_client=None
    ) -> float:
        """Calculate surprise using LLM.

        Given context, how unexpected is this content?

        Args:
            content: Content to evaluate
            context: Recent context (list of strings)
            llm_client: Optional LLM client for surprise detection

        Returns:
            Surprise score 0.0-1.0 (1.0 = very surprising)
            Returns 0.0 if no LLM client provided
        """
        if not llm_client or not context:
            return 0.0  # Cannot determine surprise without LLM and context

        try:
            context_str = "\n".join(context[-5:])  # Last 5 context items
            prompt = f"""Given this context:
{context_str}

Rate how surprising this statement is on a scale of 0.0 to 1.0:
"{content}"

Respond with only a number between 0.0 (completely expected) and 1.0 (very surprising)."""

            response = llm_client.complete(prompt)
            score = float(response.strip())
            return max(0.0, min(1.0, score))
        except Exception:
            return 0.5  # Default to neutral if error

    def detect_contradiction(
        self,
        content: str,
        project_id: int,
        llm_client=None
    ) -> Tuple[float, Optional[int]]:
        """Detect if content contradicts existing knowledge.

        Args:
            content: Content to check
            project_id: Project ID
            llm_client: Optional LLM client for contradiction detection

        Returns:
            Tuple of (contradiction_score, conflicting_memory_id)
            Returns (0.0, None) if no LLM client provided
        """
        if not llm_client:
            return 0.0, None

        # Get recent semantic memories
        with self.db.get_connection() as conn:
            cursor = conn.execute("""
                SELECT id, content FROM semantic_memory
                WHERE project_id = ?
                ORDER BY created_at DESC
                LIMIT 20
            """, (project_id,))
            memories = cursor.fetchall()

        if not memories:
            return 0.0, None

        try:
            memory_context = '\n'.join([f"{m['id']}: {m['content']}" for m in memories])

            prompt = f"""Existing knowledge:
{memory_context}

New statement: "{content}"

Does this contradict any existing knowledge? Respond with:
- "YES: [memory_id]" if contradiction found (provide the ID)
- "NO" if no contradiction

Response:"""

            response = llm_client.complete(prompt).strip()

            if response.startswith("YES"):
                # Extract memory ID if provided
                try:
                    parts = response.split(":")
                    if len(parts) > 1:
                        conflicting_id = int(parts[1].strip().split()[0])
                        return 1.0, conflicting_id
                except Exception:
                    pass
                return 1.0, None
            else:
                return 0.0, None
        except Exception:
            return 0.0, None

    def mark_salient(
        self,
        memory_id: int,
        memory_layer: str,
        project_id: int,
        content: str,
        context: Optional[List[str]] = None,
        llm_client=None
    ) -> SalienceScore:
        """Mark memory as salient and calculate salience components.

        Args:
            memory_id: Memory ID
            memory_layer: Memory layer ('working', 'semantic', etc.)
            project_id: Project ID
            content: Memory content
            context: Optional context for surprise detection
            llm_client: Optional LLM client for surprise/contradiction

        Returns:
            SalienceScore object with all components
        """
        # Calculate novelty
        novelty = self.calculate_novelty(content, project_id)

        # Calculate surprise (if context provided)
        surprise = 0.0
        if context and llm_client:
            surprise = self.calculate_surprise(content, context, llm_client)

        # Detect contradictions
        contradiction, conflicting_id = 0.0, None
        if llm_client:
            contradiction, conflicting_id = self.detect_contradiction(
                content, project_id, llm_client
            )

        # Overall salience is weighted combination
        salience = (
            0.4 * novelty +
            0.3 * surprise +
            0.3 * contradiction
        )

        # Determine reason
        reason = None
        if novelty > 0.7:
            reason = "High novelty"
        elif surprise > 0.7:
            reason = "High surprise"
        elif contradiction > 0.7:
            reason = f"Contradicts memory {conflicting_id}" if conflicting_id else "Contradiction detected"

        # Store in database
        detected_at = datetime.now()
        with self.db.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO attention_salience
                (project_id, memory_id, memory_layer, salience_score,
                 novelty_score, surprise_score, contradiction_score,
                 detected_at, reason, conflicting_memory_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (project_id, memory_id, memory_layer, salience,
                  novelty, surprise, contradiction, detected_at, reason, conflicting_id))
            conn.commit()

        return SalienceScore(
            memory_id=memory_id,
            memory_layer=memory_layer,
            salience_score=salience,
            novelty_score=novelty,
            surprise_score=surprise,
            contradiction_score=contradiction,
            detected_at=detected_at,
            reason=reason,
            conflicting_memory_id=conflicting_id
        )

    def get_salience(self, memory_id: int, memory_layer: str) -> Optional[SalienceScore]:
        """Get salience score for a memory.

        Args:
            memory_id: Memory ID
            memory_layer: Memory layer

        Returns:
            SalienceScore if found, None otherwise
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM attention_salience
                WHERE memory_id = ? AND memory_layer = ?
                ORDER BY detected_at DESC
                LIMIT 1
            """, (memory_id, memory_layer))
            row = cursor.fetchone()

        if not row:
            return None

        return SalienceScore(
            memory_id=row['memory_id'],
            memory_layer=row['memory_layer'],
            salience_score=row['salience_score'],
            novelty_score=row['novelty_score'],
            surprise_score=row['surprise_score'],
            contradiction_score=row['contradiction_score'],
            detected_at=datetime.fromisoformat(row['detected_at']),
            reason=row['reason'],
            conflicting_memory_id=row['conflicting_memory_id']
        )

    def get_most_salient(
        self,
        project_id: int,
        limit: int = 10,
        min_salience: float = 0.5
    ) -> List[SalienceScore]:
        """Get most salient memories for a project.

        Args:
            project_id: Project ID
            limit: Maximum number to return
            min_salience: Minimum salience threshold

        Returns:
            List of SalienceScore objects sorted by salience (descending)
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM attention_salience
                WHERE project_id = ? AND salience_score >= ?
                ORDER BY salience_score DESC, detected_at DESC
                LIMIT ?
            """, (project_id, min_salience, limit))
            rows = cursor.fetchall()

        return [
            SalienceScore(
                memory_id=row['memory_id'],
                memory_layer=row['memory_layer'],
                salience_score=row['salience_score'],
                novelty_score=row['novelty_score'],
                surprise_score=row['surprise_score'],
                contradiction_score=row['contradiction_score'],
                detected_at=datetime.fromisoformat(row['detected_at']),
                reason=row['reason'],
                conflicting_memory_id=row['conflicting_memory_id']
            )
            for row in rows
        ]

