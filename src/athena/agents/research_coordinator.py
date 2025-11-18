"""ResearchCoordinatorAgent - Multi-step research workflow coordinator.

This agent manages complex, multi-step research workflows. It can plan research
tasks, aggregate findings from multiple sources, synthesize results, and validate
hypotheses. The agent maintains research context across sessions for continuous
discovery and learning.

The agent integrates with:
- MemoryCoordinator: Stores research findings as semantic knowledge
- WorkflowOrchestrator: Delegates research sub-tasks
- PatternExtractor: Learns research methodologies and successful approaches
"""

import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

# Import coordinator base class
from .coordinator import AgentCoordinator
from ..orchestration.adaptive_agent import AdaptiveAgent

# Import core memory operations
from ..episodic.operations import remember as remember_event
from ..memory.operations import store as store_fact, search as search_facts

logger = logging.getLogger(__name__)


@dataclass
class ResearchPlan:
    """Structured research plan."""

    query: str
    steps: List[str]
    sources: List[str]
    hypotheses: List[str]
    success_criteria: List[str]
    estimated_depth: int = 3
    confidence: float = 0.8


@dataclass
class Finding:
    """Represents a research finding."""

    content: str
    source: str
    reliability: float  # 0.0-1.0
    supporting_evidence: List[str]
    contradicting_evidence: List[str]
    relevance_score: float = 0.8


@dataclass
class ResearchSynthesis:
    """Synthesized research results."""

    theme: str
    consensus_findings: List[str]
    conflicting_findings: List[str]
    gaps: List[str]
    confidence: float


class ResearchCoordinatorAgent(AgentCoordinator, AdaptiveAgent):
    """Multi-step research workflow coordinator.

    Manages complex research tasks including:
    - Planning multi-step research workflows
    - Aggregating findings from multiple sources
    - Synthesizing results into coherent narratives
    - Validating hypotheses against evidence
    """

    def __init__(self):
        """Initialize the Research Coordinator Agent."""
        super().__init__(
            agent_id="research-coordinator",
            agent_type="research",
        )
        self.research_tasks = 0
        self.findings_synthesized = 0
        self.hypotheses_validated = 0
        self.active_research: Dict[str, Dict[str, Any]] = {}

    async def plan_research(
        self,
        query: str,
        depth: int = 3,
        context: Optional[Dict[str, Any]] = None,
    ) -> ResearchPlan:
        """Create a structured research plan for a question.

        Args:
            query: Research question or topic
            depth: Research depth (1-5, higher = more thorough)
            context: Optional additional context

        Returns:
            ResearchPlan with steps and sources
        """
        logger.info(f"Planning research for: {query}")
        self.research_tasks += 1

        try:
            # Decompose research question
            steps = self._decompose_question(query, depth)

            # Identify relevant sources
            sources = self._identify_sources(query, depth)

            # Generate research hypotheses
            hypotheses = self._generate_hypotheses(query)

            # Define success criteria
            success_criteria = self._define_success_criteria(query)

            plan = ResearchPlan(
                query=query,
                steps=steps,
                sources=sources,
                hypotheses=hypotheses,
                success_criteria=success_criteria,
                estimated_depth=depth,
                confidence=0.85,
            )

            # Store plan in memory
            await store_fact(
                content=f"Research plan for: {query}",
                topics=["research", "planning", query.lower()[:20]],
            )

            logger.info(f"Created research plan with {len(steps)} steps")
            return plan

        except Exception as e:
            logger.error(f"Error planning research: {e}")
            return ResearchPlan(
                query=query,
                steps=[],
                sources=[],
                hypotheses=[],
                success_criteria=[],
                confidence=0.0,
            )

    async def aggregate_findings(
        self,
        topic: str,
        sources: Optional[List[str]] = None,
        limit: int = 20,
    ) -> List[Finding]:
        """Aggregate findings from multiple sources.

        Args:
            topic: Research topic
            sources: Specific sources to check (default: all)
            limit: Maximum findings to return

        Returns:
            List of aggregated findings
        """
        logger.info(f"Aggregating findings for topic: {topic}")
        findings = []

        try:
            # Search existing memory for related findings
            memory_results = await search_facts(topic, limit=limit)

            for result in memory_results:
                finding = Finding(
                    content=result.get("content", ""),
                    source="memory",
                    reliability=result.get("confidence", 0.7),
                    supporting_evidence=[],
                    contradicting_evidence=[],
                    relevance_score=result.get("similarity", 0.8),
                )
                findings.append(finding)

            # Check external sources (simulated)
            if sources is None:
                sources = ["documentation", "research-papers", "best-practices"]

            for source in sources:
                external_findings = await self._query_external_source(source, topic)
                findings.extend(external_findings)

            logger.info(f"Aggregated {len(findings)} findings")

        except Exception as e:
            logger.error(f"Error aggregating findings: {e}")

        return findings[:limit]

    async def synthesize_findings(
        self,
        findings: List[Finding],
        theme: str,
    ) -> ResearchSynthesis:
        """Synthesize multiple findings into coherent narrative.

        Args:
            findings: List of findings to synthesize
            theme: Research theme or topic

        Returns:
            Synthesized research results
        """
        logger.info(f"Synthesizing {len(findings)} findings on: {theme}")
        self.findings_synthesized += 1

        try:
            # Identify consensus findings
            consensus = self._identify_consensus(findings)

            # Identify conflicting findings
            conflicts = self._identify_conflicts(findings)

            # Identify gaps
            gaps = self._identify_gaps(findings, theme)

            # Calculate overall confidence
            avg_reliability = (
                sum(f.reliability for f in findings) / len(findings) if findings else 0.0
            )

            synthesis = ResearchSynthesis(
                theme=theme,
                consensus_findings=consensus,
                conflicting_findings=conflicts,
                gaps=gaps,
                confidence=avg_reliability,
            )

            # Store synthesis in memory
            synthesis_text = f"Research synthesis on {theme}: {len(consensus)} consensus points, {len(conflicts)} conflicts"
            await store_fact(
                content=synthesis_text,
                topics=["research", "synthesis", theme.lower()[:20]],
            )

            logger.info(
                f"Synthesis complete: {len(consensus)} consensus, {len(conflicts)} conflicts"
            )

        except Exception as e:
            logger.error(f"Error synthesizing findings: {e}")
            synthesis = ResearchSynthesis(
                theme=theme,
                consensus_findings=[],
                conflicting_findings=[],
                gaps=[],
                confidence=0.0,
            )

        return synthesis

    async def validate_hypothesis(
        self,
        hypothesis: str,
        evidence: List[Finding],
    ) -> Dict[str, Any]:
        """Validate a research hypothesis against evidence.

        Args:
            hypothesis: Hypothesis to validate
            evidence: List of evidence findings

        Returns:
            Validation results with confidence score
        """
        logger.info(f"Validating hypothesis: {hypothesis}")
        self.hypotheses_validated += 1

        try:
            # Categorize evidence
            supporting = [e for e in evidence if self._is_supporting(hypothesis, e)]
            contradicting = [e for e in evidence if self._is_contradicting(hypothesis, e)]
            neutral = [e for e in evidence if not supporting and not contradicting]

            # Calculate confidence
            if not evidence:
                confidence = 0.0
            else:
                support_score = sum(e.reliability for e in supporting) / len(evidence)
                contradict_score = sum(e.reliability for e in contradicting) / len(evidence)
                confidence = max(0.0, min(1.0, support_score - contradict_score))

            # Calculate validity
            validity = (
                "supported"
                if confidence > 0.7
                else "uncertain" if confidence > 0.3 else "unsupported"
            )

            result = {
                "hypothesis": hypothesis,
                "validity": validity,
                "confidence": confidence,
                "supporting_evidence": len(supporting),
                "contradicting_evidence": len(contradicting),
                "neutral_evidence": len(neutral),
                "recommendation": self._generate_recommendation(confidence, validity),
            }

            # Store validation in memory
            await remember_event(
                content=f"Hypothesis validation: {hypothesis} → {validity} (confidence: {confidence:.2%})",
                tags=["hypothesis", "validation"],
                source="agent:research-coordinator",
                importance=0.8,
            )

            logger.info(f"Hypothesis validation: {validity} (confidence: {confidence:.2%})")

        except Exception as e:
            logger.error(f"Error validating hypothesis: {e}")
            result = {
                "hypothesis": hypothesis,
                "validity": "unknown",
                "confidence": 0.0,
                "error": str(e),
            }

        return result

    # Private helper methods

    def _decompose_question(self, query: str, depth: int) -> List[str]:
        """Decompose research question into steps."""
        steps = []

        # Level 1: Understand the basics
        steps.append(f"Understand fundamental concepts in: {query}")

        if depth >= 2:
            # Level 2: Explore existing approaches
            steps.append(f"Identify existing solutions and approaches to: {query}")

        if depth >= 3:
            # Level 3: Analyze trade-offs
            steps.append(f"Analyze trade-offs and best practices for: {query}")

        if depth >= 4:
            # Level 4: Find novel insights
            steps.append(f"Research novel approaches and innovations in: {query}")

        if depth >= 5:
            # Level 5: Synthesize original insights
            steps.append(f"Synthesize original insights and recommendations for: {query}")

        return steps

    def _identify_sources(self, query: str, depth: int) -> List[str]:
        """Identify relevant research sources."""
        sources = [
            "official-documentation",
            "community-best-practices",
        ]

        if depth >= 2:
            sources.extend(["research-papers", "case-studies"])

        if depth >= 3:
            sources.extend(["expert-interviews", "benchmark-data"])

        if depth >= 4:
            sources.extend(["academic-journals", "technical-reports"])

        if depth >= 5:
            sources.extend(["original-research", "empirical-studies"])

        return sources

    def _generate_hypotheses(self, query: str) -> List[str]:
        """Generate initial research hypotheses."""
        return [
            f"There are established best practices for {query}",
            f"The optimal approach to {query} depends on context",
            f"New innovations in {query} are emerging",
        ]

    def _define_success_criteria(self, query: str) -> List[str]:
        """Define what success looks like for research."""
        return [
            "Identified 3+ reliable sources",
            "Found consensus view on core concepts",
            "Identified at least one novel insight",
            "Generated actionable recommendations",
        ]

    async def _query_external_source(self, source: str, topic: str) -> List[Finding]:
        """Query external research source (simulated)."""
        # This would integrate with actual external sources
        # For now, return empty list (placeholder for future integration)
        return []

    def _identify_consensus(self, findings: List[Finding]) -> List[str]:
        """Identify consensus points across findings."""
        # Simple heuristic: findings with high reliability are consensus
        consensus = [
            f.content for f in findings if f.reliability > 0.75 and not f.contradicting_evidence
        ]
        return consensus[:5]

    def _identify_conflicts(self, findings: List[Finding]) -> List[str]:
        """Identify conflicting findings."""
        conflicts = [f.content for f in findings if f.contradicting_evidence]
        return conflicts[:3]

    def _identify_gaps(self, findings: List[Finding], theme: str) -> List[str]:
        """Identify research gaps."""
        gaps = [
            f"Limited evidence on practical implementation of {theme}",
            f"Need more recent data on {theme}",
            f"Missing perspectives on {theme}",
        ]
        return gaps

    def _is_supporting(self, hypothesis: str, evidence: Finding) -> bool:
        """Check if evidence supports hypothesis."""
        # Simple keyword matching
        keywords = hypothesis.lower().split()
        return any(kw in evidence.content.lower() for kw in keywords)

    def _is_contradicting(self, hypothesis: str, evidence: Finding) -> bool:
        """Check if evidence contradicts hypothesis."""
        return len(evidence.contradicting_evidence) > 0

    def _generate_recommendation(self, confidence: float, validity: str) -> str:
        """Generate recommendation based on validation."""
        if validity == "supported" and confidence > 0.8:
            return "Strong evidence supports this hypothesis. Recommend adoption."
        elif validity == "supported":
            return "Moderate evidence supports this hypothesis. Consider with caveats."
        elif validity == "uncertain":
            return "Evidence is mixed. Further research recommended."
        else:
            return "Limited supporting evidence. Recommend alternative hypotheses."

    # ========== ABSTRACT METHOD IMPLEMENTATIONS ==========

    async def decide(self, context: dict) -> str:
        """Decide what research action to take.

        Args:
            context: Context dictionary with research parameters

        Returns:
            Decision string (e.g., "plan", "aggregate", "synthesize", "validate")
        """
        # Simple decision logic based on context
        if "query" in context and "depth" not in context:
            return "plan"
        elif "topic" in context:
            return "aggregate"
        elif "findings" in context:
            return "synthesize"
        elif "hypothesis" in context:
            return "validate"
        else:
            return "idle"

    async def execute(self, decision: str, context: dict) -> Any:
        """Execute the decided research action.

        Args:
            decision: Decision type to execute
            context: Context dictionary with action parameters

        Returns:
            Result of the action
        """
        try:
            if decision == "plan":
                return await self.plan_research(
                    query=context.get("query", ""), depth=context.get("depth", 3), context=context
                )
            elif decision == "aggregate":
                return await self.aggregate_findings(
                    topic=context.get("topic", ""), sources=context.get("sources")
                )
            elif decision == "synthesize":
                findings = context.get("findings", [])
                theme = context.get("theme", "research")
                return await self.synthesize_findings(findings, theme)
            elif decision == "validate":
                hypothesis = context.get("hypothesis", "")
                evidence = context.get("evidence", [])
                return await self.validate_hypothesis(hypothesis, evidence)
            else:
                return {"status": "idle", "message": "No action taken"}
        except Exception as e:
            logger.error(f"Error executing decision {decision}: {e}")
            return {"status": "error", "message": str(e)}
