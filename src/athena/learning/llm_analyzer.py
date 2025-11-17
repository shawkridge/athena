"""LLM-based outcome analyzer for learning feedback.

Uses local LLM to reason about why decisions succeed/fail,
feeding smarter insights back to the learning system.

This implements Option C: LLMClient integration for learning feedback.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class LLMOutcomeAnalyzer:
    """Analyzes decision outcomes using LLM reasoning.

    Provides:
    - Why analysis: "Why did consolidation succeed?"
    - Decision quality assessment: "How good was this decision?"
    - Reasoning pattern evaluation: "Which reasoning patterns work?"
    - Feedback for adaptive agent optimization
    """

    def __init__(self, llm_client: Optional[Any] = None):
        """Initialize analyzer with optional LLM client.

        Args:
            llm_client: LocalLLMClient instance (optional, lazy-loaded if not provided)
        """
        self.llm_client = llm_client
        self._reasoning_cache = {}  # Cache expensive reasoning

    async def analyze_consolidation_outcome(
        self,
        success_rate: float,
        events_processed: int,
        patterns_extracted: int,
        execution_time_ms: float,
        strategy: str = "balanced"
    ) -> Dict[str, Any]:
        """Analyze why consolidation succeeded or failed.

        Args:
            success_rate: 0.0-1.0 success metric
            events_processed: Number of events consolidated
            patterns_extracted: Number of patterns found
            execution_time_ms: How long it took
            strategy: Strategy used (e.g., "balanced", "aggressive")

        Returns:
            Analysis with:
            - reason: Why it succeeded/failed
            - confidence: 0.0-1.0 confidence in analysis
            - recommendations: List of improvement suggestions
            - reasoning_quality: How good was the reasoning?
        """
        # Build analysis prompt
        status = "succeeded" if success_rate > 0.8 else "partially succeeded" if success_rate > 0.5 else "failed"

        analysis_prompt = f"""Analyze this consolidation outcome:
- Status: {status}
- Success rate: {success_rate:.2f}
- Events processed: {events_processed}
- Patterns extracted: {patterns_extracted}
- Execution time: {execution_time_ms:.0f}ms
- Strategy: {strategy}

Why did this happen? What could improve it?
Keep response short (2-3 sentences max)."""

        try:
            # Try to use LLM if available
            if self.llm_client:
                reasoning_result = await self._get_llm_reasoning(analysis_prompt)
                reason = reasoning_result['text'] if reasoning_result else "Analysis unavailable"
            else:
                reason = await self._heuristic_analysis(
                    success_rate=success_rate,
                    events_processed=events_processed,
                    patterns_extracted=patterns_extracted,
                    execution_time_ms=execution_time_ms
                )

            # Generate recommendations
            recommendations = await self._generate_recommendations(
                status=status,
                success_rate=success_rate,
                execution_time_ms=execution_time_ms
            )

            return {
                "status": "success",
                "reason": reason,
                "confidence": 0.8,  # Confidence in this analysis
                "recommendations": recommendations,
                "reasoning_quality": "heuristic" if not self.llm_client else "llm-based"
            }

        except Exception as e:
            logger.error(f"Failed to analyze outcome: {e}")
            return {
                "status": "error",
                "error": str(e),
                "reason": "Analysis failed",
                "confidence": 0.0,
                "recommendations": []
            }

    async def analyze_agent_decision(
        self,
        agent_name: str,
        decision: str,
        outcome: str,
        success_rate: float,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze quality of an agent decision using reasoning.

        Args:
            agent_name: Name of agent
            decision: Description of decision
            outcome: Result (success/failure/partial/error)
            success_rate: 0.0-1.0 success metric
            context: Optional context about the decision

        Returns:
            Analysis with decision quality assessment
        """
        context_str = ""
        if context:
            context_str = "\nContext: " + ", ".join(f"{k}={v}" for k, v in list(context.items())[:3])

        analysis_prompt = f"""Evaluate this agent decision:
- Agent: {agent_name}
- Decision: {decision}
- Outcome: {outcome}
- Success rate: {success_rate:.2f}{context_str}

Is this a good decision? Why or why not?
Keep response short (2-3 sentences max)."""

        try:
            if self.llm_client:
                reasoning_result = await self._get_llm_reasoning(analysis_prompt)
                assessment = reasoning_result['text'] if reasoning_result else "Assessment unavailable"
            else:
                assessment = self._heuristic_assessment(agent_name, success_rate)

            return {
                "status": "success",
                "agent": agent_name,
                "decision": decision,
                "assessment": assessment,
                "quality_score": success_rate,  # Use success_rate as quality indicator
                "reasoning_type": "llm-based" if self.llm_client else "heuristic"
            }

        except Exception as e:
            logger.error(f"Failed to analyze decision: {e}")
            return {
                "status": "error",
                "error": str(e),
                "agent": agent_name,
                "quality_score": success_rate
            }

    async def evaluate_reasoning_pattern(
        self,
        pattern_name: str,
        success_count: int,
        failure_count: int,
        avg_success_rate: float
    ) -> Dict[str, Any]:
        """Evaluate quality of a reasoning pattern used by agents.

        Args:
            pattern_name: Name of reasoning pattern
            success_count: Number of successes using this pattern
            failure_count: Number of failures
            avg_success_rate: Average success rate

        Returns:
            Evaluation with recommendation to keep/improve/discard
        """
        total = success_count + failure_count
        success_pct = (success_count / total * 100) if total > 0 else 0

        pattern_prompt = f"""Evaluate this reasoning pattern:
- Pattern: {pattern_name}
- Success rate: {success_pct:.0f}% ({success_count}/{total})
- Avg success metric: {avg_success_rate:.2f}

Is this pattern working well? When should agents use it?
Keep response short (2-3 sentences max)."""

        try:
            if self.llm_client:
                reasoning_result = await self._get_llm_reasoning(pattern_prompt)
                assessment = reasoning_result['text'] if reasoning_result else "Assessment unavailable"
            else:
                assessment = self._heuristic_pattern_assessment(success_pct, avg_success_rate)

            # Recommend action based on performance
            if success_pct > 80:
                recommendation = "keep"
            elif success_pct > 50:
                recommendation = "improve"
            else:
                recommendation = "review"

            return {
                "status": "success",
                "pattern": pattern_name,
                "success_rate": success_pct,
                "assessment": assessment,
                "recommendation": recommendation,
                "reasoning_type": "llm-based" if self.llm_client else "heuristic"
            }

        except Exception as e:
            logger.error(f"Failed to evaluate pattern: {e}")
            return {
                "status": "error",
                "error": str(e),
                "pattern": pattern_name,
                "success_rate": success_pct
            }

    async def _get_llm_reasoning(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Get reasoning from LLM (with fallback if unavailable).

        Args:
            prompt: Prompt for reasoning

        Returns:
            Reasoning result or None if LLM unavailable
        """
        if not self.llm_client:
            return None

        try:
            # Try to get reasoning from LLM
            reasoning_result = await self.llm_client.reason(prompt)
            return {
                "text": reasoning_result.text,
                "tokens": reasoning_result.tokens,
                "latency_ms": reasoning_result.latency_ms
            }
        except Exception as e:
            logger.warning(f"LLM reasoning failed: {e}")
            return None

    async def _heuristic_analysis(
        self,
        success_rate: float,
        events_processed: int,
        patterns_extracted: int,
        execution_time_ms: float
    ) -> str:
        """Fallback: heuristic analysis without LLM.

        Args:
            success_rate: 0.0-1.0 success metric
            events_processed: Number of events
            patterns_extracted: Number of patterns found
            execution_time_ms: Execution time

        Returns:
            Analysis string
        """
        if success_rate > 0.9:
            quality = "excellent"
        elif success_rate > 0.8:
            quality = "good"
        elif success_rate > 0.6:
            quality = "fair"
        else:
            quality = "poor"

        if execution_time_ms > 5000:
            speed = "slow"
        elif execution_time_ms > 2000:
            speed = "moderate"
        else:
            speed = "fast"

        if patterns_extracted > events_processed * 0.1:
            richness = "high"
        elif patterns_extracted > 0:
            richness = "moderate"
        else:
            richness = "low"

        return (
            f"Consolidation quality is {quality} ({success_rate:.0%}). "
            f"Processing was {speed} ({execution_time_ms:.0f}ms) with {richness} pattern richness. "
            f"Consider optimizing event-to-pattern ratio."
        )

    async def _generate_recommendations(
        self,
        status: str,
        success_rate: float,
        execution_time_ms: float
    ) -> List[str]:
        """Generate recommendations for improvement.

        Args:
            status: Consolidation status
            success_rate: Success metric
            execution_time_ms: Execution time

        Returns:
            List of recommendations
        """
        recommendations = []

        if success_rate < 0.7:
            recommendations.append("Increase event sampling to improve pattern detection")
            recommendations.append("Review consolidation strategy for this session type")

        if execution_time_ms > 5000:
            recommendations.append("Profile consolidation bottlenecks - consider caching frequent patterns")

        if not recommendations:
            recommendations.append("Current consolidation strategy is working well")

        return recommendations

    def _heuristic_assessment(self, agent_name: str, success_rate: float) -> str:
        """Heuristic assessment of decision quality.

        Args:
            agent_name: Agent name
            success_rate: Success metric

        Returns:
            Assessment string
        """
        if success_rate > 0.85:
            return f"{agent_name} made a high-quality decision. Success rate indicates sound reasoning."
        elif success_rate > 0.6:
            return f"{agent_name} made a reasonable decision. Consider refining strategy."
        else:
            return f"{agent_name}'s decision quality needs improvement. Review reasoning pattern."

    def _heuristic_pattern_assessment(self, success_pct: float, avg_success_rate: float) -> str:
        """Heuristic assessment of pattern quality.

        Args:
            success_pct: Success percentage
            avg_success_rate: Average success metric

        Returns:
            Assessment string
        """
        if success_pct > 80 and avg_success_rate > 0.8:
            return "Pattern is highly effective. Should be used frequently."
        elif success_pct > 60:
            return "Pattern works reasonably well. Worth keeping and refining."
        else:
            return "Pattern's effectiveness is unclear. Needs more evaluation or refinement."


class DecisionQualityEvaluator:
    """Evaluates quality of agent decisions for feedback loop.

    Used by adaptive agents to determine which strategies lead to
    better outcomes, enabling the system to learn and improve.
    """

    def __init__(self, analyzer: Optional[LLMOutcomeAnalyzer] = None):
        """Initialize evaluator with optional analyzer.

        Args:
            analyzer: LLMOutcomeAnalyzer instance
        """
        self.analyzer = analyzer or LLMOutcomeAnalyzer()

    async def score_decision_quality(
        self,
        agent_name: str,
        decision_made: str,
        outcome: str,
        success_rate: float,
        execution_context: Optional[Dict[str, Any]] = None
    ) -> float:
        """Score quality of a decision (0.0-1.0).

        Used by adaptive agents to learn which decisions to repeat.

        Args:
            agent_name: Agent that made decision
            decision_made: The decision
            outcome: Result of decision
            success_rate: 0.0-1.0 success metric
            execution_context: Optional context

        Returns:
            Quality score 0.0-1.0
        """
        # Base quality on success rate
        base_quality = success_rate

        # Boost for success outcomes
        if outcome == "success":
            base_quality = min(1.0, base_quality * 1.1)
        elif outcome == "partial":
            base_quality = base_quality * 0.9

        # Get LLM assessment if available
        try:
            analysis = await self.analyzer.analyze_agent_decision(
                agent_name=agent_name,
                decision=decision_made,
                outcome=outcome,
                success_rate=success_rate,
                context=execution_context
            )

            # Use analyzer's quality score if available
            if "quality_score" in analysis:
                return min(1.0, max(0.0, analysis["quality_score"]))
        except Exception as e:
            logger.warning(f"LLM assessment failed: {e}, using base quality")

        return min(1.0, max(0.0, base_quality))

    async def extract_learning_insight(
        self,
        agent_name: str,
        decision: str,
        outcome: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """Extract a learning insight from decision outcome.

        Used to update agent memory about what works.

        Args:
            agent_name: Agent name
            decision: Decision made
            outcome: Result
            context: Optional context

        Returns:
            Learning insight string or None
        """
        try:
            analysis = await self.analyzer.analyze_agent_decision(
                agent_name=agent_name,
                decision=decision,
                outcome=outcome,
                success_rate=1.0 if outcome == "success" else 0.0,
                context=context
            )

            if analysis.get("status") == "success":
                return analysis.get("assessment")
        except Exception as e:
            logger.warning(f"Failed to extract learning: {e}")

        return None
