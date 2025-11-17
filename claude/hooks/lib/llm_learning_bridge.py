"""LLM Learning Bridge - Integrates LLMClient reasoning into learning system.

Provides synchronous access to LLM-powered outcome analysis from hooks.
Bridges the gap between synchronous shell hooks and async LLM operations.

Used by:
- session-end.sh: Analyze consolidation outcomes using LLM reasoning
- post-tool-use.sh (optional): Assess decision quality
"""

import sys
import os
import logging
import asyncio
from typing import Optional, Dict, Any

# Configure logging
log_level = logging.DEBUG if os.environ.get('DEBUG') else logging.WARNING
logging.basicConfig(level=log_level, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)


class LLMLearningBridge:
    """Synchronous bridge to LLM-powered learning analysis.

    Provides:
    - Analyze consolidation outcomes using LLM reasoning
    - Score decision quality with explanation
    - Extract learning insights from outcomes
    """

    def __init__(self):
        """Initialize LLM learning bridge."""
        self.session_id = os.environ.get('CLAUDE_SESSION_ID', 'default-session')
        logger.debug(f"LLMLearningBridge initialized for session {self.session_id}")

    def analyze_consolidation_outcome(
        self,
        success_rate: float,
        events_processed: int,
        patterns_extracted: int,
        execution_time_ms: float,
        strategy: str = "balanced"
    ) -> Dict[str, Any]:
        """Analyze consolidation outcome using LLM reasoning.

        Args:
            success_rate: 0.0-1.0 success metric
            events_processed: Number of events consolidated
            patterns_extracted: Number of patterns extracted
            execution_time_ms: How long consolidation took
            strategy: Strategy used

        Returns:
            Analysis with LLM-generated insights
        """
        try:
            async def async_analyze():
                try:
                    from athena.core.database import Database
                    from athena.learning.llm_analyzer import LLMOutcomeAnalyzer
                    from athena.core.llm_client import LocalLLMClient

                    # Initialize LLM client (graceful fallback if unavailable)
                    llm_client = None
                    try:
                        llm_client = LocalLLMClient(
                            embedding_url="http://localhost:8001",
                            reasoning_url="http://localhost:8002",
                            enable_compression=False,
                            timeout_seconds=10.0
                        )
                    except Exception as e:
                        logger.warning(f"LLM client unavailable: {e}, using heuristic analysis")

                    # Create analyzer with LLM client (optional)
                    analyzer = LLMOutcomeAnalyzer(llm_client=llm_client)

                    # Analyze consolidation outcome
                    analysis = await analyzer.analyze_consolidation_outcome(
                        success_rate=success_rate,
                        events_processed=events_processed,
                        patterns_extracted=patterns_extracted,
                        execution_time_ms=execution_time_ms,
                        strategy=strategy
                    )

                    return {
                        "status": "success",
                        "analysis": analysis
                    }

                except Exception as e:
                    logger.error(f"Failed to analyze outcome: {e}")
                    return {
                        "status": "error",
                        "error": str(e),
                        "analysis": {
                            "reason": "Analysis failed",
                            "confidence": 0.0,
                            "recommendations": []
                        }
                    }

            # Run async operation synchronously
            result = asyncio.run(async_analyze())
            return result.get("analysis", {})

        except Exception as e:
            logger.error(f"LLMLearningBridge.analyze_consolidation_outcome failed: {e}")
            return {
                "reason": "Analysis unavailable",
                "confidence": 0.0,
                "recommendations": []
            }

    def evaluate_decision_quality(
        self,
        agent_name: str,
        decision: str,
        outcome: str,
        success_rate: float,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Evaluate quality of an agent decision.

        Args:
            agent_name: Name of agent
            decision: Description of decision
            outcome: Result (success/failure/partial/error)
            success_rate: 0.0-1.0 success metric
            context: Optional context dict

        Returns:
            Quality assessment with explanation
        """
        try:
            async def async_evaluate():
                try:
                    from athena.learning.llm_analyzer import DecisionQualityEvaluator
                    from athena.core.llm_client import LocalLLMClient

                    # Initialize LLM client (graceful fallback)
                    llm_client = None
                    try:
                        llm_client = LocalLLMClient(
                            embedding_url="http://localhost:8001",
                            reasoning_url="http://localhost:8002",
                            enable_compression=False,
                            timeout_seconds=10.0
                        )
                    except Exception as e:
                        logger.warning(f"LLM client unavailable: {e}")

                    # Create evaluator
                    from athena.learning.llm_analyzer import LLMOutcomeAnalyzer
                    analyzer = LLMOutcomeAnalyzer(llm_client=llm_client)
                    evaluator = DecisionQualityEvaluator(analyzer=analyzer)

                    # Score decision
                    quality_score = await evaluator.score_decision_quality(
                        agent_name=agent_name,
                        decision_made=decision,
                        outcome=outcome,
                        success_rate=success_rate,
                        execution_context=context
                    )

                    # Extract insight
                    insight = await evaluator.extract_learning_insight(
                        agent_name=agent_name,
                        decision=decision,
                        outcome=outcome,
                        context=context
                    )

                    return {
                        "status": "success",
                        "quality_score": quality_score,
                        "insight": insight,
                        "agent": agent_name
                    }

                except Exception as e:
                    logger.error(f"Failed to evaluate decision: {e}")
                    return {
                        "status": "error",
                        "error": str(e),
                        "quality_score": success_rate  # Fallback
                    }

            result = asyncio.run(async_evaluate())
            return result

        except Exception as e:
            logger.error(f"LLMLearningBridge.evaluate_decision_quality failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "quality_score": 0.0
            }


# Module-level functions for convenient use from hooks
def analyze_consolidation_llm(
    success_rate: float,
    events_processed: int,
    patterns_extracted: int,
    execution_time_ms: float,
    strategy: str = "balanced"
) -> Dict[str, Any]:
    """Analyze consolidation with LLM reasoning.

    Usage from hook:
        from llm_learning_bridge import analyze_consolidation_llm
        analysis = analyze_consolidation_llm(0.85, 100, 15, 2500.0)
        print(f"Reason: {analysis['reason']}")
    """
    bridge = LLMLearningBridge()
    return bridge.analyze_consolidation_outcome(
        success_rate=success_rate,
        events_processed=events_processed,
        patterns_extracted=patterns_extracted,
        execution_time_ms=execution_time_ms,
        strategy=strategy
    )


def evaluate_decision_llm(
    agent_name: str,
    decision: str,
    outcome: str,
    success_rate: float,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Evaluate decision quality with LLM.

    Usage from hook:
        from llm_learning_bridge import evaluate_decision_llm
        result = evaluate_decision_llm("memory-coordinator", "should_remember", "success", 0.95)
        print(f"Quality: {result['quality_score']:.2f}")
    """
    bridge = LLMLearningBridge()
    return bridge.evaluate_decision_quality(
        agent_name=agent_name,
        decision=decision,
        outcome=outcome,
        success_rate=success_rate,
        context=context
    )
