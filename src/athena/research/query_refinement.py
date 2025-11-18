"""Query Refinement Engine for Phase 3.2 - Interactive Research.

Parses user feedback and generates refined search queries and constraints
for research agents. Supports multi-turn refinement with feedback threading.
"""

import logging
import re
from typing import Dict, List, Optional
from dataclasses import dataclass, field

from .models import ResearchFeedback, FeedbackType

logger = logging.getLogger(__name__)


@dataclass
class QueryRefinement:
    """Result of query refinement process."""

    original_query: str
    refined_query: str
    excluded_sources: List[str] = field(default_factory=list)
    focused_sources: List[str] = field(default_factory=list)
    quality_threshold: float = 0.5
    agent_directives: Dict[str, List[str]] = field(default_factory=dict)
    time_constraint: Optional[str] = None
    domain_focus: Optional[str] = None
    applied_feedback_ids: List[int] = field(default_factory=list)

    def summary(self) -> str:
        """Get human-readable summary of refinements."""
        lines = [f"Refined query: {self.refined_query}"]

        if self.excluded_sources:
            lines.append(f"Excluded sources: {', '.join(self.excluded_sources)}")
        if self.focused_sources:
            lines.append(f"Focused sources: {', '.join(self.focused_sources)}")
        if self.time_constraint:
            lines.append(f"Time constraint: {self.time_constraint}")
        if self.domain_focus:
            lines.append(f"Domain focus: {self.domain_focus}")
        if self.quality_threshold > 0.5:
            lines.append(f"Quality threshold: {self.quality_threshold:.1f}")

        if self.agent_directives:
            for agent, directives in self.agent_directives.items():
                lines.append(f"  {agent}: {'; '.join(directives)}")

        return "\n".join(lines)


class QueryRefinementEngine:
    """Engine for refining research queries based on user feedback."""

    # Common source exclusion patterns
    SOURCE_EXCLUSIONS = {
        "github": ["github", "git", "code repo"],
        "arxiv": ["arxiv", "academic paper", "research paper"],
        "blog": ["blog", "medium", "dev.to", "hashnode"],
        "wiki": ["wikipedia", "wiki"],
        "news": ["news", "article", "press"],
        "social": ["twitter", "reddit", "linkedin"],
    }

    # Source focus patterns
    SOURCE_FOCUS = {
        "academic": ["arxiv", "scholar", "paper", "research"],
        "technical": ["github", "stack overflow", "documentation"],
        "news": ["news", "article", "press release"],
        "commercial": ["product", "service", "business"],
    }

    # Agent names
    AGENTS = ["web_searcher", "academic_researcher", "synthesizer"]

    def __init__(self):
        """Initialize query refinement engine."""
        self.logger = logging.getLogger(__name__)

    def refine_from_feedback(
        self,
        original_query: str,
        feedback_list: List[ResearchFeedback],
    ) -> QueryRefinement:
        """Refine a query based on feedback.

        Args:
            original_query: Original research query
            feedback_list: List of feedback items to apply

        Returns:
            QueryRefinement with refined query and constraints
        """
        refinement = QueryRefinement(
            original_query=original_query,
            refined_query=original_query,
        )

        # Track which feedback items we apply
        applied_feedback_ids = []

        for feedback in feedback_list:
            try:
                if feedback.feedback_type == FeedbackType.QUERY_REFINEMENT:
                    refinement.refined_query = self._refine_query(
                        refinement.refined_query, feedback.content
                    )
                    applied_feedback_ids.append(feedback.id or 0)

                elif feedback.feedback_type == FeedbackType.SOURCE_EXCLUSION:
                    self._apply_source_exclusion(refinement, feedback.content)
                    applied_feedback_ids.append(feedback.id or 0)

                elif feedback.feedback_type == FeedbackType.SOURCE_FOCUS:
                    self._apply_source_focus(refinement, feedback.content)
                    applied_feedback_ids.append(feedback.id or 0)

                elif feedback.feedback_type == FeedbackType.AGENT_FOCUS:
                    self._apply_agent_focus(refinement, feedback)
                    applied_feedback_ids.append(feedback.id or 0)

                elif feedback.feedback_type == FeedbackType.QUALITY_THRESHOLD:
                    self._apply_quality_threshold(refinement, feedback.content)
                    applied_feedback_ids.append(feedback.id or 0)

                elif feedback.feedback_type == FeedbackType.RESULT_FILTERING:
                    self._apply_result_filter(refinement, feedback.content)
                    applied_feedback_ids.append(feedback.id or 0)

            except Exception as e:
                self.logger.warning(f"Failed to apply feedback {feedback.id}: {e}")

        refinement.applied_feedback_ids = applied_feedback_ids
        return refinement

    def _refine_query(self, current_query: str, refinement_instruction: str) -> str:
        """Apply query refinement instruction.

        Examples:
        - "focus on 2023-2024" → adds time constraint
        - "include machine learning" → adds to query
        - "remove cloud services" → excludes from query
        """
        refined = current_query

        # Detect time constraints
        time_match = re.search(
            r"(20\d{2}|last \w+|recent|past \d+ \w+)", refinement_instruction.lower()
        )
        if time_match:
            time_constraint = time_match.group(1)
            if time_constraint not in refined:
                refined += f" {time_constraint}"

        # Detect include patterns
        include_match = re.search(
            r"(?:include|focus on|add|about)\s+([^.,]+)", refinement_instruction.lower()
        )
        if include_match:
            include_term = include_match.group(1).strip()
            if include_term not in refined.lower():
                refined += f" {include_term}"

        # Detect exclude patterns
        exclude_match = re.search(
            r"(?:remove|exclude|without|ignore)\s+([^.,]+)", refinement_instruction.lower()
        )
        if exclude_match:
            exclude_term = exclude_match.group(1).strip()
            # Add NOT operator
            refined += f" NOT {exclude_term}"

        return refined.strip()

    def _apply_source_exclusion(self, refinement: QueryRefinement, content: str) -> None:
        """Apply source exclusion feedback."""
        content_lower = content.lower()

        # Check for specific source mentions
        for source_key, source_aliases in self.SOURCE_EXCLUSIONS.items():
            for alias in source_aliases:
                if alias in content_lower:
                    if source_key not in refinement.excluded_sources:
                        refinement.excluded_sources.append(source_key)

        # Also check for direct mentions like "exclude github"
        match = re.search(r"(?:exclude|block|remove)\s+(\w+)", content_lower)
        if match:
            source = match.group(1)
            if source not in refinement.excluded_sources:
                refinement.excluded_sources.append(source)

    def _apply_source_focus(self, refinement: QueryRefinement, content: str) -> None:
        """Apply source focus feedback."""
        content_lower = content.lower()

        for focus_type, keywords in self.SOURCE_FOCUS.items():
            for keyword in keywords:
                if keyword in content_lower:
                    if focus_type not in refinement.focused_sources:
                        refinement.focused_sources.append(focus_type)

        # Check for direct mentions
        match = re.search(r"(?:focus|use|prefer)\s+(?:only\s+)?(\w+)", content_lower)
        if match:
            source = match.group(1)
            if source not in refinement.focused_sources:
                refinement.focused_sources.append(source)

    def _apply_agent_focus(self, refinement: QueryRefinement, feedback: ResearchFeedback) -> None:
        """Apply agent-specific directives."""
        agent = feedback.agent_target or "all_agents"

        if agent not in refinement.agent_directives:
            refinement.agent_directives[agent] = []

        # Parse directive from feedback content
        directive = feedback.content.strip()
        if directive not in refinement.agent_directives[agent]:
            refinement.agent_directives[agent].append(directive)

    def _apply_quality_threshold(self, refinement: QueryRefinement, content: str) -> None:
        """Apply quality threshold refinement."""
        # Extract numeric threshold like "quality >= 0.8" or "high quality"
        match = re.search(r"(\d+\.?\d*)", content)
        if match:
            threshold = float(match.group(1))
            # Normalize to 0-1 range
            if threshold > 1:
                threshold = threshold / 100
            refinement.quality_threshold = max(0.0, min(1.0, threshold))

        # Handle text-based quality levels
        content_lower = content.lower()
        if "high" in content_lower:
            refinement.quality_threshold = 0.8
        elif "medium" in content_lower:
            refinement.quality_threshold = 0.6
        elif "low" in content_lower:
            refinement.quality_threshold = 0.3

    def _apply_result_filter(self, refinement: QueryRefinement, content: str) -> None:
        """Apply result filtering directives.

        Examples:
        - "only recent results" → time constraint
        - "top results only" → quality threshold
        - "unique findings" → deduplication
        """
        content_lower = content.lower()

        if "recent" in content_lower:
            refinement.time_constraint = "recent"
        elif "old" in content_lower or "historical" in content_lower:
            refinement.time_constraint = "historical"

        if "top" in content_lower or "best" in content_lower:
            refinement.quality_threshold = 0.7

    def get_query_constraints(self, refinement: QueryRefinement) -> Dict[str, any]:
        """Convert refinement to query constraints for agents.

        Returns dictionary with constraints that agents can use:
        - excluded_sources: List of sources to exclude
        - focused_sources: List of sources to focus on
        - quality_threshold: Minimum credibility/quality score
        - time_range: Optional time constraint
        - keywords: Refined query keywords
        - agent_overrides: Agent-specific overrides
        """
        return {
            "original_query": refinement.original_query,
            "refined_query": refinement.refined_query,
            "excluded_sources": refinement.excluded_sources,
            "focused_sources": refinement.focused_sources,
            "quality_threshold": refinement.quality_threshold,
            "time_constraint": refinement.time_constraint,
            "domain_focus": refinement.domain_focus,
            "agent_directives": refinement.agent_directives,
            "applied_feedback_ids": refinement.applied_feedback_ids,
        }

    def create_agent_instructions(
        self,
        refinement: QueryRefinement,
        agent_name: str,
    ) -> Dict[str, str]:
        """Create agent-specific search instructions.

        Args:
            refinement: Query refinement result
            agent_name: Name of agent

        Returns:
            Dictionary with search parameters and constraints
        """
        instructions = {
            "query": refinement.refined_query,
            "quality_threshold": str(refinement.quality_threshold),
        }

        # Add exclusions
        if refinement.excluded_sources:
            instructions["exclude_sources"] = ",".join(refinement.excluded_sources)

        # Add focus
        if refinement.focused_sources:
            instructions["focus_sources"] = ",".join(refinement.focused_sources)

        # Add time constraint
        if refinement.time_constraint:
            instructions["time_constraint"] = refinement.time_constraint

        # Add agent-specific directives
        if agent_name in refinement.agent_directives:
            instructions["directives"] = "; ".join(refinement.agent_directives[agent_name])
        elif "all_agents" in refinement.agent_directives:
            instructions["directives"] = "; ".join(refinement.agent_directives["all_agents"])

        return instructions
