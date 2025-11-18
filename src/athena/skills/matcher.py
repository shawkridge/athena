"""Skill matching and retrieval.

Finds applicable skills for a given task using semantic and keyword matching.
"""

from typing import List, Optional
import logging

from .models import Skill, SkillMatch, SkillDomain
from .library import SkillLibrary

logger = logging.getLogger(__name__)


class SkillMatcher:
    """Finds applicable skills for a given task description."""

    def __init__(self, library: SkillLibrary):
        """Initialize matcher.

        Args:
            library: SkillLibrary instance
        """
        self.library = library

    async def find_skills(
        self,
        task_description: str,
        domain: Optional[SkillDomain] = None,
        min_relevance: float = 0.5,
        limit: int = 5,
    ) -> List[SkillMatch]:
        """Find applicable skills for a task.

        Args:
            task_description: Description of task to solve
            domain: Optional domain to filter
            min_relevance: Minimum relevance threshold (0-1)
            limit: Max results

        Returns:
            List of SkillMatch results sorted by relevance
        """
        # Get candidate skills from library
        if domain:
            candidates = await self.library.list_all(domain=domain, limit=100)
        else:
            candidates = await self.library.list_all(limit=100)

        # Score each skill
        matches = []
        for skill in candidates:
            relevance = self._compute_relevance(task_description, skill)

            if relevance >= min_relevance:
                reason = self._generate_reason(task_description, skill, relevance)
                match = SkillMatch(
                    skill=skill,
                    relevance=relevance,
                    reason=reason,
                )
                matches.append(match)

        # Sort by relevance (highest first)
        matches.sort(key=lambda m: m.relevance, reverse=True)

        return matches[:limit]

    def _compute_relevance(self, task_description: str, skill: Skill) -> float:
        """Compute relevance score (0-1) of skill for task.

        Args:
            task_description: Task description
            skill: Skill to evaluate

        Returns:
            Relevance score (0-1)
        """
        task_lower = task_description.lower()
        metadata = skill.metadata

        score = 0.0

        # Keyword matching (25%)
        keyword_matches = 0
        keywords = [metadata.name, *metadata.tags, *metadata.examples]

        for keyword in keywords:
            if keyword and keyword.lower() in task_lower:
                keyword_matches += 1

        if len(keywords) > 0:
            keyword_score = min(keyword_matches / len(keywords), 1.0) * 0.25
            score += keyword_score

        # Description similarity (25%)
        if metadata.description:
            desc_lower = metadata.description.lower()
            # Simple word overlap
            task_words = set(task_lower.split())
            desc_words = set(desc_lower.split())
            overlap = len(task_words & desc_words) / max(len(task_words | desc_words), 1)
            score += overlap * 0.25

        # Quality score (25%)
        score += metadata.quality_score * 0.25

        # Success rate (25%)
        score += metadata.success_rate * 0.25

        return min(score, 1.0)

    def _generate_reason(self, task_description: str, skill: Skill, relevance: float) -> str:
        """Generate human-readable explanation of match.

        Args:
            task_description: Task description
            skill: Skill that matched
            relevance: Relevance score

        Returns:
            Explanation string
        """
        reasons = []

        # Add quality reason
        if skill.quality >= 0.9:
            reasons.append("High quality (90%+)")
        elif skill.quality >= 0.75:
            reasons.append("Good quality")

        # Add success rate reason
        if skill.metadata.success_rate >= 0.95:
            reasons.append(f"Highly reliable ({int(skill.metadata.success_rate*100)}% success)")
        elif skill.metadata.success_rate >= 0.8:
            reasons.append(f"Reliable ({int(skill.metadata.success_rate*100)}% success)")

        # Add usage reason
        if skill.metadata.times_used >= 10:
            reasons.append(f"Proven ({skill.metadata.times_used}+ uses)")
        elif skill.metadata.times_used > 0:
            reasons.append(f"Used {skill.metadata.times_used} times")

        # Add domain reason
        if skill.metadata.domain != SkillDomain.GENERAL:
            reasons.append(f"Specialized for {skill.metadata.domain.value}")

        reason_str = "; ".join(reasons) if reasons else "Matches task description"
        return f"{reason_str} (relevance: {relevance:.0%})"

    def rank_skills(self, skills: List[Skill], task_description: str) -> List[Skill]:
        """Rank skills by relevance to task.

        Args:
            skills: List of skills to rank
            task_description: Task description

        Returns:
            Skills sorted by relevance
        """
        scored = [(skill, self._compute_relevance(task_description, skill)) for skill in skills]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [skill for skill, _ in scored]
