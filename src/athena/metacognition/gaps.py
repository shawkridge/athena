"""Knowledge gap detection and contradiction identification."""

import sqlite3
import json
import asyncio
import logging
from datetime import datetime
from typing import Optional, List, Dict
from enum import Enum

from .models import KnowledgeGap, GapType, GapPriority

# Optional LLM support for semantic analysis
LLMS_AVAILABLE = False
OllamaLLMClient = None

try:
    from ..rag.llm_client import OllamaLLMClient
    LLMS_AVAILABLE = True
except (ImportError, Exception) as e:
    # LLM client not available - this is okay, gap detector will use heuristics
    LLMS_AVAILABLE = False

logger = logging.getLogger(__name__)


class KnowledgeGapDetector:
    """
    Detects knowledge gaps, contradictions, and uncertainties in memory.

    Capabilities:
    - Detect direct contradictions between memories
    - Identify subtle contradictions
    - Find uncertainty zones (low-confidence areas)
    - Flag missing information
    - Categorize gaps by severity
    - Suggest research areas
    - Track gap resolution
    """

    def __init__(self, db_path: str, llm_client: Optional["OllamaLLMClient"] = None):
        """Initialize gap detector with optional LLM support."""
        self.db_path = db_path
        self.llm_client = llm_client
        self._use_llm = LLMS_AVAILABLE and llm_client is not None

        if self._use_llm:
            logger.info("Gap detector: LLM-powered semantic analysis enabled")
        else:
            logger.info("Gap detector: Using heuristic-based analysis (no LLM)")

    def detect_direct_contradictions(
        self, project_id: int, memory_ids: Optional[List[int]] = None
    ) -> List[Dict]:
        """
        Detect direct contradictions between memories.

        Direct contradictions: Explicit conflicts in facts (A says X, B says NOT X)

        Returns:
            List of contradictions with:
            - memory_ids: [id1, id2] conflicting memories
            - contradiction_type: 'direct', 'subtle', 'uncertain'
            - severity: 'low', 'medium', 'high'
            - description: What the contradiction is
            - confidence: How certain about the contradiction (0-1)
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Get memory details to simulate checking for contradictions
            query = (
                """
                SELECT id, content FROM semantic_memories
                WHERE project_id = ?
                """
                if memory_ids is None
                else """
                SELECT id, content FROM semantic_memories
                WHERE project_id = ? AND id IN ({})
                """.format(
                    ",".join("?" * len(memory_ids))
                )
            )

            params = [project_id] + (memory_ids or [])
            cursor.execute(query, params)
            memories = cursor.fetchall()

        contradictions = []

        # Check for contradictory pairs
        for i, (id1, content1) in enumerate(memories):
            for id2, content2 in memories[i + 1 :]:
                # Simple contradiction detection: if one is a negation of the other
                if self._are_contradictory(content1, content2):
                    contradictions.append(
                        {
                            "memory_ids": [id1, id2],
                            "contradiction_type": "direct",
                            "severity": "high",
                            "description": f"Direct contradiction: Memory {id1} vs {id2}",
                            "confidence": 0.95,
                        }
                    )

        return contradictions

    def detect_subtle_contradictions(
        self, project_id: int, threshold: float = 0.7
    ) -> List[Dict]:
        """
        Detect subtle contradictions through semantic analysis.

        Subtle contradictions: Implied conflicts not explicitly stated.

        Returns:
            List of subtle contradictions
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, content FROM semantic_memories
                WHERE project_id = ?
                LIMIT 100
                """,
                (project_id,),
            )
            memories = cursor.fetchall()

        subtle_contradictions = []

        # For each memory pair, check for semantic conflicts
        for i, (id1, content1) in enumerate(memories):
            for id2, content2 in memories[i + 1 :]:
                conflict_score = self._calculate_conflict_score(content1, content2)

                if conflict_score > threshold:
                    subtle_contradictions.append(
                        {
                            "memory_ids": [id1, id2],
                            "contradiction_type": "subtle",
                            "severity": "medium",
                            "description": f"Subtle conflict detected between {id1} and {id2}",
                            "confidence": conflict_score,
                        }
                    )

        return subtle_contradictions

    def identify_uncertainty_zones(self, project_id: int) -> List[Dict]:
        """
        Identify areas with low confidence/high uncertainty.

        Returns:
            List of uncertainty zones with:
            - zone_description: What area is uncertain
            - memory_ids: Related memories
            - average_confidence: Mean confidence in this zone
            - count: Number of uncertain memories
            - priority: How important to resolve
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Get memories with low confidence (simulated)
            cursor.execute(
                """
                SELECT id, content FROM semantic_memories
                WHERE project_id = ?
                LIMIT 100
                """,
                (project_id,),
            )
            memories = cursor.fetchall()

        uncertainty_zones = []

        # Group memories by topic/similarity
        topics = {}
        for mem_id, content in memories:
            topic = self._extract_topic(content)
            if topic not in topics:
                topics[topic] = []
            topics[topic].append((mem_id, content))

        # Analyze uncertainty in each topic
        for topic, group in topics.items():
            if len(group) >= 2:
                confidences = [0.5 for _ in group]  # Simulated
                avg_confidence = sum(confidences) / len(confidences)

                if avg_confidence < 0.6:
                    uncertainty_zones.append(
                        {
                            "zone_description": f"Uncertainty in topic: {topic}",
                            "memory_ids": [mid for mid, _ in group],
                            "average_confidence": avg_confidence,
                            "count": len(group),
                            "priority": (
                                "high"
                                if avg_confidence < 0.4
                                else "medium"
                            ),
                        }
                    )

        return uncertainty_zones

    def flag_missing_information(self, project_id: int) -> List[Dict]:
        """
        Identify gaps in knowledge - missing information on important topics.

        Returns:
            List of missing information gaps with:
            - topic: What information is missing
            - description: Details about what's missing
            - priority: How important to fill gap
            - suggested_research: Recommended areas to research
        """
        gaps = []

        # Common important topics that should have coverage
        important_topics = [
            "purpose",
            "architecture",
            "status",
            "limitations",
            "best_practices",
            "known_issues",
        ]

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Check what topics have memory coverage
            cursor.execute(
                """
                SELECT content FROM semantic_memories
                WHERE project_id = ?
                LIMIT 50
                """,
                (project_id,),
            )
            covered_topics = set()
            for (content,) in cursor.fetchall():
                for topic in important_topics:
                    if topic.lower() in content.lower():
                        covered_topics.add(topic)

        # Identify uncovered topics
        for topic in important_topics:
            if topic not in covered_topics:
                priority = (
                    "high"
                    if topic in ["purpose", "architecture", "status"]
                    else "medium"
                )
                gaps.append(
                    {
                        "topic": topic,
                        "description": f"Missing information about {topic}",
                        "priority": priority,
                        "suggested_research": [f"Research about {topic}"],
                    }
                )

        return gaps

    def record_gap(
        self,
        project_id: int,
        gap_type: str,
        description: str,
        memory_ids: List[int],
        confidence: float,
        priority: str,
    ) -> bool:
        """
        Record a knowledge gap in the database.

        Args:
            project_id: Project ID
            gap_type: 'contradiction', 'uncertainty', 'missing_info'
            description: Description of the gap
            memory_ids: Related memory IDs
            confidence: Confidence in the gap (0-1)
            priority: 'low', 'medium', 'high', 'critical'
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO metacognition_gaps
                (project_id, gap_type, description, memory_ids, confidence, priority, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    gap_type,
                    description,
                    json.dumps(memory_ids),
                    confidence,
                    priority,
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()
            return True

    def resolve_gap(self, gap_id: int, resolution: str) -> bool:
        """
        Mark a knowledge gap as resolved.

        Args:
            gap_id: Gap ID
            resolution: Description of how it was resolved
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE metacognition_gaps
                SET resolved = 1, resolved_at = ?
                WHERE id = ?
                """,
                (datetime.now().isoformat(), gap_id),
            )
            conn.commit()
            return True

    def get_unresolved_gaps(
        self, project_id: int, priority: Optional[str] = None
    ) -> List[Dict]:
        """
        Get all unresolved gaps for a project.

        Args:
            project_id: Project ID
            priority: Filter by priority ('low', 'medium', 'high', 'critical')

        Returns:
            List of unresolved gaps
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            if priority:
                cursor.execute(
                    """
                    SELECT id, gap_type, description, memory_ids, confidence, priority, created_at
                    FROM metacognition_gaps
                    WHERE project_id = ? AND resolved = 0 AND priority = ?
                    ORDER BY created_at DESC
                    """,
                    (project_id, priority),
                )
            else:
                cursor.execute(
                    """
                    SELECT id, gap_type, description, memory_ids, confidence, priority, created_at
                    FROM metacognition_gaps
                    WHERE project_id = ? AND resolved = 0
                    ORDER BY created_at DESC
                    """,
                    (project_id,),
                )

            rows = cursor.fetchall()

        gaps = []
        for row in rows:
            gap_id, gap_type, description, memory_ids_json, confidence, priority, created_at = row
            gaps.append(
                {
                    "id": gap_id,
                    "gap_type": gap_type,
                    "description": description,
                    "memory_ids": json.loads(memory_ids_json) if memory_ids_json else [],
                    "confidence": confidence,
                    "priority": priority,
                    "created_at": created_at,
                }
            )

        return gaps

    def get_gap_report(self, project_id: int) -> Dict:
        """
        Generate comprehensive gap analysis report.

        Returns:
            Dictionary with:
            - total_gaps: Total gap count
            - by_type: Gaps grouped by type
            - by_priority: Gaps grouped by priority
            - critical_issues: High and critical priority gaps
            - resolutions_needed: Recommended actions
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Get all gaps
            cursor.execute(
                """
                SELECT gap_type, priority, resolved
                FROM metacognition_gaps
                WHERE project_id = ?
                """,
                (project_id,),
            )
            rows = cursor.fetchall()

        gaps_by_type = {}
        gaps_by_priority = {}
        total_gaps = 0
        unresolved_gaps = 0

        for gap_type, priority, resolved in rows:
            total_gaps += 1
            if not resolved:
                unresolved_gaps += 1

            gaps_by_type[gap_type] = gaps_by_type.get(gap_type, 0) + 1
            gaps_by_priority[priority] = gaps_by_priority.get(priority, 0) + 1

        # Get critical issues
        critical_gaps = self.get_unresolved_gaps(project_id, priority="critical")
        high_gaps = self.get_unresolved_gaps(project_id, priority="high")

        resolutions_needed = []
        if critical_gaps:
            resolutions_needed.append(
                f"Address {len(critical_gaps)} critical gaps immediately"
            )
        if high_gaps:
            resolutions_needed.append(f"Resolve {len(high_gaps)} high-priority gaps")

        return {
            "total_gaps": total_gaps,
            "unresolved_gaps": unresolved_gaps,
            "resolved_gaps": total_gaps - unresolved_gaps,
            "by_type": gaps_by_type,
            "by_priority": gaps_by_priority,
            "critical_issues": critical_gaps,
            "high_priority_issues": high_gaps,
            "resolutions_needed": resolutions_needed,
        }

    def suggest_research_areas(self, project_id: int) -> List[Dict]:
        """
        Suggest areas for research based on gaps and uncertainties.

        Returns:
            List of suggested research areas with:
            - topic: What to research
            - reason: Why it's important
            - priority: 'low', 'medium', 'high'
            - expected_value: How much it would help (0-1)
        """
        suggestions = []

        # Get missing info gaps
        missing = self.flag_missing_information(project_id)

        for gap in missing:
            priority = gap["priority"]
            expected_value = 0.9 if priority == "high" else 0.7 if priority == "medium" else 0.5

            suggestions.append(
                {
                    "topic": gap["topic"],
                    "reason": gap["description"],
                    "priority": priority,
                    "expected_value": expected_value,
                    "suggested_action": gap["suggested_research"][0] if gap["suggested_research"] else f"Research {gap['topic']}",
                }
            )

        return suggestions

    # LLM-POWERED GAP ANALYSIS METHODS

    def detect_semantic_contradictions(
        self, project_id: int, memory_ids: Optional[List[int]] = None
    ) -> List[Dict]:
        """
        Detect semantic contradictions using LLM reasoning.

        Uses Claude to identify contradictions that pure heuristics miss.
        Falls back to heuristic detection if LLM unavailable.
        """
        if not self._use_llm:
            logger.debug("LLM not available, using heuristic contradiction detection")
            return self.detect_subtle_contradictions(project_id)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            query = (
                """
                SELECT id, content FROM semantic_memories
                WHERE project_id = ?
                """
                if memory_ids is None
                else """
                SELECT id, content FROM semantic_memories
                WHERE project_id = ? AND id IN ({})
                """.format(
                    ",".join("?" * len(memory_ids))
                )
            )

            params = [project_id] + (memory_ids or [])
            cursor.execute(query, params)
            memories = cursor.fetchall()

        contradictions = []

        try:
            # Batch analyze memory pairs for contradictions
            for i in range(0, len(memories), 5):
                batch = memories[i : i + 5]

                for j, (id1, content1) in enumerate(batch):
                    for id2, content2 in batch[j + 1 :]:
                        prompt = f"""Analyze if these two pieces of knowledge contradict each other.

Memory 1 (ID {id1}):
{content1[:500]}

Memory 2 (ID {id2}):
{content2[:500]}

Respond with JSON:
{{"contradicts": true/false, "contradiction_type": "direct|subtle|none", "explanation": "...", "confidence": 0.0-1.0}}
"""
                        try:
                            result = self.llm_client.generate(prompt, max_tokens=200)
                            analysis = json.loads(result)

                            if analysis.get("contradicts", False):
                                contradictions.append(
                                    {
                                        "memory_ids": [id1, id2],
                                        "contradiction_type": analysis.get(
                                            "contradiction_type", "subtle"
                                        ),
                                        "severity": (
                                            "high"
                                            if analysis.get("contradiction_type")
                                            == "direct"
                                            else "medium"
                                        ),
                                        "description": analysis.get(
                                            "explanation", "Semantic contradiction"
                                        ),
                                        "confidence": float(
                                            analysis.get("confidence", 0.7)
                                        ),
                                        "analysis_method": "llm_semantic",
                                    }
                                )
                        except (json.JSONDecodeError, ValueError) as e:
                            logger.warning(
                                f"Failed to parse LLM response: {e}, using heuristic"
                            )
                            # Fallback to heuristic for this pair
                            if self._are_contradictory(content1, content2):
                                contradictions.append(
                                    {
                                        "memory_ids": [id1, id2],
                                        "contradiction_type": "direct",
                                        "severity": "high",
                                        "description": f"Heuristic: Direct contradiction between {id1} and {id2}",
                                        "confidence": 0.8,
                                        "analysis_method": "heuristic_fallback",
                                    }
                                )

        except Exception as e:
            logger.error(f"Semantic contradiction detection failed: {e}")
            # Fallback to heuristic detection
            return self.detect_direct_contradictions(project_id, memory_ids)

        return contradictions

    def generate_research_questions(self, gaps: List[Dict]) -> List[Dict]:
        """
        Generate targeted research questions to fill identified gaps.

        Uses Claude to create actionable research directions.
        """
        if not self._use_llm or not gaps:
            logger.debug("LLM unavailable or no gaps, skipping research question generation")
            return []

        research_questions = []

        try:
            for gap in gaps:
                gap_desc = gap.get("description", "Unknown gap")
                memory_ids = gap.get("memory_ids", [])

                prompt = f"""Given this knowledge gap:
{gap_desc}

Related memories: {memory_ids}

Generate 3 specific, actionable research questions to fill this gap.
Format as JSON: {{"questions": ["Q1?", "Q2?", "Q3?"]}}
"""
                try:
                    result = self.llm_client.generate(prompt, max_tokens=300)
                    analysis = json.loads(result)

                    research_questions.append(
                        {
                            "gap_description": gap_desc,
                            "memory_ids": memory_ids,
                            "questions": analysis.get(
                                "questions",
                                [
                                    f"What aspects of {gap_desc} need clarification?"
                                ],
                            ),
                        }
                    )
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(f"Failed to parse research questions: {e}")
                    research_questions.append(
                        {
                            "gap_description": gap_desc,
                            "memory_ids": memory_ids,
                            "questions": [
                                f"What are the implications of {gap_desc}?",
                                f"What contexts does {gap_desc} apply to?",
                                f"How was {gap_desc} derived?",
                            ],
                        }
                    )

        except Exception as e:
            logger.error(f"Research question generation failed: {e}")

        return research_questions

    def prioritize_gaps(self, gaps: List[Dict], project_context: str = "") -> List[Dict]:
        """
        Prioritize gaps by impact and importance.

        Uses Claude to understand which gaps matter most for the project.
        """
        if not self._use_llm or not gaps:
            # Fallback: sort by confidence (higher confidence gaps are more important)
            return sorted(gaps, key=lambda x: x.get("confidence", 0.5), reverse=True)

        try:
            gaps_text = "\n".join(
                [f"- {g.get('description', 'Unknown gap')}" for g in gaps]
            )

            prompt = f"""Given these knowledge gaps in a memory system:
{gaps_text}

Project context: {project_context}

Rank these gaps by importance (1=highest). Output JSON:
{{"rankings": [{{"gap": "description", "priority": 1, "reasoning": "..."}}]}}
"""
            result = self.llm_client.generate(prompt, max_tokens=500)
            analysis = json.loads(result)

            rankings = {
                r["gap"]: (r.get("priority", 5), r.get("reasoning", ""))
                for r in analysis.get("rankings", [])
            }

            # Annotate gaps with priority
            prioritized = []
            for gap in gaps:
                desc = gap.get("description", "")
                priority, reasoning = rankings.get(
                    desc, (5, "Default priority")
                )  # Default priority = 5

                gap_copy = gap.copy()
                gap_copy["llm_priority"] = priority
                gap_copy["llm_reasoning"] = reasoning
                prioritized.append(gap_copy)

            return sorted(prioritized, key=lambda x: x.get("llm_priority", 5))

        except Exception as e:
            logger.error(f"Gap prioritization failed: {e}")
            return gaps  # Return unprioritized gaps on error

    def suggest_gap_resolution(self, gap: Dict) -> Dict:
        """
        Suggest strategies to resolve a specific gap.

        Uses Claude to generate actionable resolution strategies.
        """
        if not self._use_llm:
            logger.debug("LLM unavailable, skipping resolution suggestion")
            return {"strategy": "Heuristic: Gather more evidence", "steps": []}

        try:
            prompt = f"""How would you resolve this knowledge gap?
Gap: {gap.get('description', 'Unknown gap')}
Type: {gap.get('gap_type', 'Unknown')}

Provide a resolution strategy with concrete steps.
Format as JSON: {{"strategy": "...", "steps": ["step1", "step2", ...], "estimated_effort": "low|medium|high"}}
"""
            result = self.llm_client.generate(prompt, max_tokens=400)
            analysis = json.loads(result)

            return {
                "gap_id": gap.get("id"),
                "gap_description": gap.get("description", ""),
                "strategy": analysis.get("strategy", "Undetermined"),
                "steps": analysis.get("steps", []),
                "estimated_effort": analysis.get("estimated_effort", "medium"),
            }

        except Exception as e:
            logger.error(f"Resolution suggestion failed: {e}")
            return {
                "gap_id": gap.get("id"),
                "strategy": "Error generating strategy",
                "steps": [],
            }

    # Helper methods

    def _are_contradictory(self, content1: str, content2: str) -> bool:
        """Check if two pieces of content are directly contradictory."""
        # Simple heuristic: check for not/no in one but not other
        neg_words = ["not", "no", "never", "cannot", "can't"]
        has_neg1 = any(word in content1.lower() for word in neg_words)
        has_neg2 = any(word in content2.lower() for word in neg_words)

        # If one has negation and other doesn't, check similarity
        return has_neg1 != has_neg2 and self._are_similar(content1, content2)

    def _calculate_conflict_score(self, content1: str, content2: str) -> float:
        """Calculate how much two pieces of content conflict (0-1)."""
        # If similar but contradictory indicators, score is high
        similarity = self._similarity_score(content1, content2)
        conflict = 1.0 - similarity
        return min(conflict * 1.2, 1.0)  # Slight boost for detected conflicts

    def _are_similar(self, content1: str, content2: str, threshold: float = 0.5) -> bool:
        """Check if two contents are sufficiently similar."""
        return self._similarity_score(content1, content2) >= threshold

    def _similarity_score(self, content1: str, content2: str) -> float:
        """Calculate similarity score between two contents (0-1)."""
        words1 = set(content1.lower().split())
        words2 = set(content2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = len(words1 & words2)
        union = len(words1 | words2)
        return intersection / union if union > 0 else 0.0

    def _extract_topic(self, content: str) -> str:
        """Extract main topic from content."""
        # Simple approach: use first few words as topic
        words = content.split()
        return " ".join(words[:3]) if len(words) >= 3 else content[:20]
