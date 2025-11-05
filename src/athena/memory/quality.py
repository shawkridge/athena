"""Semantic memory quality scoring with LLM-powered analysis."""

import json
import logging
from dataclasses import dataclass
from typing import Optional

from ..core.database import Database
from ..rag.llm_client import OllamaLLMClient

logger = logging.getLogger(__name__)


@dataclass
class MemoryQualityScore:
    """Quality metrics for a semantic memory."""

    memory_id: int
    content: str
    coherence_score: float  # 0.0-1.0: How logically consistent is this memory?
    relevance_score: float  # 0.0-1.0: How relevant to project goals?
    completeness_score: float  # 0.0-1.0: How complete is the information?
    clarity_score: float  # 0.0-1.0: How clear and well-structured?
    uniqueness_score: float  # 0.0-1.0: How unique vs. duplicates?
    overall_quality: float  # 0.0-1.0: Weighted average of all scores

    # Metadata
    quality_tier: str  # "excellent" (>0.8), "good" (0.6-0.8), "fair" (0.4-0.6), "poor" (<0.4)
    suggestions: list[str]  # Improvement suggestions
    confidence: float  # 0.0-1.0: How confident are we in this score?


class SemanticMemoryQualityAnalyzer:
    """Analyze semantic memory quality using LLM-powered coherence checking."""

    def __init__(self, db: Database, llm_client: Optional[OllamaLLMClient] = None):
        """Initialize quality analyzer.

        Args:
            db: Database instance
            llm_client: Optional LLM client for advanced analysis
        """
        self.db = db
        self.llm_client = llm_client
        self._use_llm = llm_client is not None

        if self._use_llm:
            logger.info("Memory quality analyzer: LLM-powered semantic analysis enabled")
        else:
            logger.info("Memory quality analyzer: Using heuristic-based analysis (no LLM)")

    def score_memory(self, memory_id: int, content: str) -> MemoryQualityScore:
        """Score a single semantic memory.

        Args:
            memory_id: Memory ID
            content: Memory content

        Returns:
            MemoryQualityScore with detailed metrics
        """
        if self._use_llm:
            return self._score_with_llm(memory_id, content)
        else:
            return self._score_heuristic(memory_id, content)

    def _score_with_llm(self, memory_id: int, content: str) -> MemoryQualityScore:
        """Score memory using LLM coherence analysis.

        Uses Claude to evaluate:
        - Semantic coherence: Is the content logically consistent?
        - Relevance: Is it relevant to software development?
        - Completeness: Does it contain sufficient detail?
        - Clarity: Is it well-structured and understandable?
        - Uniqueness: Is it duplicate/redundant?
        """
        try:
            prompt = f"""Analyze the quality of this semantic memory (from a software development knowledge base).

Memory Content:
{content}

Evaluate these dimensions (each 0.0-1.0):
1. Coherence: Is the content logically consistent and free of contradictions?
2. Relevance: Is it relevant to software development, system design, or coding?
3. Completeness: Does it contain sufficient detail or actionable information?
4. Clarity: Is it well-structured, clear, and easy to understand?
5. Uniqueness: Is this information unique or likely duplicated elsewhere?

Respond with JSON:
{{
    "coherence": 0.0-1.0,
    "relevance": 0.0-1.0,
    "completeness": 0.0-1.0,
    "clarity": 0.0-1.0,
    "uniqueness": 0.0-1.0,
    "tier": "excellent|good|fair|poor",
    "suggestions": ["suggestion1", "suggestion2"],
    "reasoning": "brief explanation"
}}

Be strict but fair. Focus on actionable feedback."""

            result = self.llm_client.generate(prompt, max_tokens=200)
            analysis = json.loads(result)

            # Extract scores
            coherence = float(analysis.get("coherence", 0.5))
            relevance = float(analysis.get("relevance", 0.5))
            completeness = float(analysis.get("completeness", 0.5))
            clarity = float(analysis.get("clarity", 0.5))
            uniqueness = float(analysis.get("uniqueness", 0.5))

            # Weighted overall quality
            # Coherence is most important (30%), followed by relevance (25%) and completeness (25%)
            overall_quality = (
                0.30 * coherence + 0.25 * relevance + 0.25 * completeness + 0.15 * clarity + 0.05 * uniqueness
            )

            # Clamp to 0.0-1.0
            overall_quality = max(0.0, min(1.0, overall_quality))

            tier = analysis.get("tier", "fair")
            suggestions = analysis.get("suggestions", [])
            confidence = 0.85  # LLM analysis has good confidence

            logger.debug(
                f"Memory {memory_id} LLM quality score: {overall_quality:.2f} "
                f"(coherence={coherence:.2f}, relevance={relevance:.2f})"
            )

            return MemoryQualityScore(
                memory_id=memory_id,
                content=content[:100],  # Truncate for display
                coherence_score=coherence,
                relevance_score=relevance,
                completeness_score=completeness,
                clarity_score=clarity,
                uniqueness_score=uniqueness,
                overall_quality=overall_quality,
                quality_tier=tier,
                suggestions=suggestions,
                confidence=confidence,
            )

        except json.JSONDecodeError as e:
            logger.debug(f"Failed to parse LLM response for memory {memory_id}: {e}")
            # Fall back to heuristic
            return self._score_heuristic(memory_id, content)
        except Exception as e:
            logger.debug(f"LLM quality analysis failed for memory {memory_id}: {e}")
            # Fall back to heuristic
            return self._score_heuristic(memory_id, content)

    def _score_heuristic(self, memory_id: int, content: str) -> MemoryQualityScore:
        """Score memory using heuristic analysis (fallback).

        Evaluates based on:
        - Length and structure
        - Common quality indicators (code, examples, citations)
        - Potential redundancy signals
        """
        # Basic length heuristics
        content_length = len(content)
        word_count = len(content.split())

        # Coherence: check for clear structure
        coherence = 0.5
        if "\n" in content or any(p in content for p in ["step", "step 1", "first,", "second,"]):
            coherence = 0.7  # Structured content is more coherent
        if ":" in content and len(content) > 100:
            coherence = 0.8  # Labeled sections are well-structured

        # Relevance: check for dev-related keywords
        relevance = 0.5
        dev_keywords = [
            "code", "function", "class", "database", "api", "algorithm",
            "pattern", "design", "implementation", "performance", "optimization",
            "testing", "debugging", "error", "exception", "error handling"
        ]
        keyword_matches = sum(1 for kw in dev_keywords if kw in content.lower())
        relevance = min(0.95, 0.5 + (keyword_matches * 0.1))

        # Completeness: based on length and structure
        completeness = 0.5
        if word_count > 50:
            completeness = 0.7
        if word_count > 150:
            completeness = 0.85
        if word_count > 300:
            completeness = 0.95

        # Clarity: based on formatting and structure
        clarity = 0.5
        if content_length > 200 and "\n" in content:
            clarity = 0.7
        if any(fmt in content for fmt in ["**", "__", "`", "- "]):
            clarity = 0.8  # Formatted content is clearer

        # Uniqueness: check for genericity/similarity to common phrases
        uniqueness = 0.7
        generic_phrases = [
            "this is a", "this is the", "here is", "basically,",
            "what is", "how does", "explain", "understand"
        ]
        generic_count = sum(1 for phrase in generic_phrases if phrase in content.lower())
        if generic_count > 3:
            uniqueness = 0.5  # Many generic phrases suggest less unique

        # Overall quality (weighted)
        overall_quality = (
            0.30 * coherence + 0.25 * relevance + 0.25 * completeness + 0.15 * clarity + 0.05 * uniqueness
        )

        # Determine tier
        if overall_quality >= 0.8:
            tier = "excellent"
        elif overall_quality >= 0.6:
            tier = "good"
        elif overall_quality >= 0.4:
            tier = "fair"
        else:
            tier = "poor"

        # Generate suggestions
        suggestions = []
        if coherence < 0.6:
            suggestions.append("Improve structure and logical flow")
        if relevance < 0.6:
            suggestions.append("Add more dev-specific examples or concepts")
        if completeness < 0.6:
            suggestions.append("Expand with more details and examples")
        if clarity < 0.6:
            suggestions.append("Better formatting and organization")
        if uniqueness < 0.6:
            suggestions.append("Make content more specific and unique")

        logger.debug(
            f"Memory {memory_id} heuristic quality score: {overall_quality:.2f} "
            f"(length={word_count} words, dev_keywords={keyword_matches})"
        )

        return MemoryQualityScore(
            memory_id=memory_id,
            content=content[:100],  # Truncate for display
            coherence_score=coherence,
            relevance_score=relevance,
            completeness_score=completeness,
            clarity_score=clarity,
            uniqueness_score=uniqueness,
            overall_quality=overall_quality,
            quality_tier=tier,
            suggestions=suggestions,
            confidence=0.6,  # Heuristic has lower confidence
        )

    def score_project_memories(
        self, project_id: int, limit: Optional[int] = None
    ) -> list[MemoryQualityScore]:
        """Score all semantic memories for a project.

        Args:
            project_id: Project ID
            limit: Maximum number of memories to score (None = all)

        Returns:
            List of quality scores, sorted by overall_quality (lowest first)
        """
        try:
            cursor = self.db.conn.cursor()

            # Query semantic memories for project
            query = """
                SELECT id, content FROM semantic_memories
                WHERE project_id = ?
                ORDER BY created_at DESC
            """
            if limit:
                query += f" LIMIT {limit}"

            cursor.execute(query, (project_id,))
            memories = cursor.fetchall()

            scores = []
            for memory_id, content in memories:
                score = self.score_memory(memory_id, content)
                scores.append(score)

            # Sort by quality (lowest first) - identifies what to improve
            scores.sort(key=lambda s: s.overall_quality)

            logger.info(f"Scored {len(scores)} memories for project {project_id}")
            return scores

        except Exception as e:
            logger.error(f"Error scoring project memories: {e}")
            return []

    def get_quality_summary(self, project_id: int) -> dict:
        """Get summary statistics for project memory quality.

        Returns dict with:
        - avg_quality: Average quality score
        - quality_distribution: Count by tier
        - low_quality_count: Memories with quality < 0.4
        - recommendations: Top improvement opportunities
        """
        try:
            scores = self.score_project_memories(project_id, limit=None)

            if not scores:
                return {
                    "avg_quality": 0.0,
                    "quality_distribution": {},
                    "low_quality_count": 0,
                    "recommendations": [],
                }

            # Calculate statistics
            avg_quality = sum(s.overall_quality for s in scores) / len(scores)

            # Distribution by tier
            tier_counts = {}
            for score in scores:
                tier_counts[score.quality_tier] = tier_counts.get(score.quality_tier, 0) + 1

            # Count low-quality
            low_quality = [s for s in scores if s.overall_quality < 0.4]

            # Extract top recommendations
            recommendations = {}
            for score in scores:
                for suggestion in score.suggestions:
                    recommendations[suggestion] = recommendations.get(suggestion, 0) + 1

            top_recommendations = sorted(recommendations.items(), key=lambda x: x[1], reverse=True)[:5]

            return {
                "avg_quality": avg_quality,
                "total_memories": len(scores),
                "quality_distribution": tier_counts,
                "low_quality_count": len(low_quality),
                "recommendations": [{"action": rec, "frequency": count} for rec, count in top_recommendations],
            }

        except Exception as e:
            logger.error(f"Error generating quality summary: {e}")
            return {}
