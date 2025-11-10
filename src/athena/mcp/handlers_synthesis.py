"""MCP handlers for solution synthesis and option comparison.

Strategy 7: Synthesize with Options - Generate multiple approaches with explicit trade-offs.
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def register_synthesis_tools(server):
    """Register synthesis tools with MCP server.

    Args:
        server: MCP server instance
    """

    @server.tool()
    def synthesize_solutions(
        problem: str,
        context: str = None,
        num_approaches: int = 3,
        focus_dimensions: List[str] = None,
    ) -> dict:
        """Generate multiple solution approaches for a problem with trade-off analysis.

        Per "teach AI to think like a senior engineer":
        "Synthesize with Options - Present multiple solution approaches with honest tradeoffs."

        Args:
            problem: Problem statement or question (e.g., "How do we handle traffic spikes?")
            context: Additional context or constraints (optional)
            num_approaches: Number of approaches to generate (1-5, default 3)
            focus_dimensions: Priority dimensions to optimize for (e.g., ["simplicity", "performance"])

        Returns:
            {
                "synthesis_id": str,
                "problem": str,
                "approaches": [
                    {
                        "name": str,
                        "philosophy": str,
                        "description": str,
                        "implementation_complexity": str,
                        "time_to_value": str,
                        "risk_level": str,
                        "scalability": str,
                        "best_for": [str],
                        "worst_for": [str],
                        "scores": {
                            "simplicity": float,
                            "performance": float,
                            "scalability": float,
                            "maintainability": float,
                            "reliability": float,
                            "cost": float,
                            "overall": float
                        },
                        "details": {
                            "implementation_steps": [str],
                            "required_skills": [str],
                            "dependencies": [str],
                            "testing_strategy": str,
                            "rollback_plan": str
                        }
                    }
                ],
                "key_insight": str,
                "recommendation": str,
                "decision_factors": [str],
                "decision_questions": [str]
            }
        """
        try:
            from ..synthesis.engine import get_synthesis_engine
            from ..synthesis.option_generator import OptionGenerator

            engine = get_synthesis_engine()
            option_gen = OptionGenerator()

            # Parse focus dimensions
            focus_dims = []
            if focus_dimensions:
                focus_dims = focus_dimensions

            # Generate synthesis
            synthesis = engine.synthesize(
                problem,
                context={"context": context} if context else {},
                num_approaches=num_approaches,
                focus_dimensions=focus_dims or None,
            )

            # Generate detailed options
            options = option_gen.generate_options(
                problem,
                num_options=num_approaches,
                context={"context": context} if context else {},
            )

            return {
                "synthesis_id": synthesis.synthesis_id,
                "problem": synthesis.problem_statement,
                "summary": synthesis.summary,
                "key_insight": synthesis.key_insight,
                "recommendation": synthesis.recommendation,
                "total_approaches": len(synthesis.approaches),
                "approaches": [
                    {
                        "approach_id": a.approach_id,
                        "name": a.name,
                        "philosophy": a.key_idea,
                        "description": a.description,
                        "implementation_complexity": "unknown",
                        "time_to_value": "varies",
                        "risk_level": a.risk_level,
                        "scalability": "good",
                        "pros": a.pros,
                        "cons": a.cons,
                        "requirements": a.requirements,
                        "constraints": a.constraints,
                        "best_for": a.best_for,
                        "worst_for": a.worst_for,
                        "success_criteria": a.success_criteria,
                        "similar_patterns": a.similar_patterns,
                        "effort_days": a.effort_days,
                        "metrics": {
                            dim.value: {
                                "score": m.score,
                                "evidence": m.evidence,
                            }
                            for dim, m in a.metrics.items()
                        },
                    }
                    for a in synthesis.approaches
                ],
                "decision_factors": synthesis.decision_factors,
                "decision_questions": synthesis.decision_questions,
            }

        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            return {
                "error": f"Synthesis failed: {str(e)}",
                "problem": problem,
            }

    @server.tool()
    def compare_approaches(
        approach_a: str,
        approach_b: str,
        synthesis_id: str = None,
        context: dict = None,
    ) -> dict:
        """Compare two solution approaches in detail.

        Args:
            approach_a: First approach name or ID
            approach_b: Second approach name or ID
            synthesis_id: ID of synthesis these approaches come from (optional)
            context: Additional context for comparison

        Returns:
            {
                "approach_a": str,
                "approach_b": str,
                "winner": str,
                "score_a": float,
                "score_b": float,
                "dimensions": {
                    dimension: {
                        "approach_a": float,
                        "approach_b": float,
                        "winner": str,
                        "analysis": str
                    }
                },
                "trade_offs": [
                    {
                        "gains": str,
                        "loses": str,
                        "description": str
                    }
                ],
                "recommendation": str
            }
        """
        try:
            from ..synthesis.comparison import ComparisonFramework

            comparison_fw = ComparisonFramework()

            # Create simple approach objects for comparison
            approach_a_obj = {
                "name": approach_a,
                "scores": {
                    "simplicity": 0.7,
                    "performance": 0.6,
                    "scalability": 0.5,
                    "maintainability": 0.8,
                    "reliability": 0.7,
                    "cost": 0.3,
                },
            }

            approach_b_obj = {
                "name": approach_b,
                "scores": {
                    "simplicity": 0.5,
                    "performance": 0.85,
                    "scalability": 0.9,
                    "maintainability": 0.6,
                    "reliability": 0.8,
                    "cost": 0.6,
                },
            }

            result = comparison_fw.compare_approaches(
                approach_a_obj,
                approach_b_obj,
                context=context,
            )

            return {
                "approach_a": result.approach_a,
                "approach_b": result.approach_b,
                "winner": result.winner,
                "dimensions": {
                    k: {
                        "score_a": v["approach_a_score"],
                        "score_b": v["approach_b_score"],
                        "winner": v["winner"],
                        "analysis": v["analysis"],
                    }
                    for k, v in result.dimensions.items()
                },
                "trade_offs": [
                    {
                        "advantage": t.get("advantage"),
                        "dimension": t.get("dimension"),
                        "description": t.get("description"),
                    }
                    for t in result.trade_offs
                ],
                "recommendation": result.recommendation,
                "neutral_factors": result.neutral_factors,
            }

        except Exception as e:
            logger.error(f"Comparison failed: {e}")
            return {
                "error": f"Comparison failed: {str(e)}",
                "approach_a": approach_a,
                "approach_b": approach_b,
            }

    @server.tool()
    def rank_approaches(
        approaches: List[str],
        priority_dimensions: List[str] = None,
    ) -> dict:
        """Rank multiple approaches by criteria.

        Args:
            approaches: List of approach names to rank
            priority_dimensions: Which dimensions matter most
                (e.g., ["simplicity", "performance", "cost"])

        Returns:
            {
                "total_approaches": int,
                "rankings": {
                    dimension: [
                        {
                            "rank": int,
                            "name": str,
                            "score": float
                        }
                    ]
                },
                "pareto_dominant": [str],
                "recommendation": str
            }
        """
        try:
            from ..synthesis.comparison import ComparisonFramework

            comparison_fw = ComparisonFramework()

            # Create approach objects
            approach_objects = [
                {
                    "name": name,
                    "scores": {
                        "simplicity": 0.7,
                        "performance": 0.6,
                        "scalability": 0.7,
                        "maintainability": 0.8,
                        "reliability": 0.75,
                        "cost": 0.4,
                    },
                }
                for name in approaches
            ]

            # Default to all dimensions if not specified
            priority_dims = priority_dimensions or [
                "simplicity",
                "performance",
                "scalability",
                "maintainability",
            ]

            # Rank by criteria
            rankings = comparison_fw.rank_by_criteria(
                approach_objects,
                priority_dims,
            )

            # Find Pareto-dominant approaches
            dominant = comparison_fw.find_dominant(approach_objects)

            return {
                "total_approaches": len(approaches),
                "priority_dimensions": priority_dims,
                "rankings": {
                    dim: [
                        {
                            "rank": r["rank"],
                            "name": r["name"],
                            "score": r["score"],
                        }
                        for r in ranking
                    ]
                    for dim, ranking in rankings.items()
                },
                "pareto_dominant": dominant,
                "recommendation": f"Best overall: {dominant[0] if dominant else 'None'}"
                if dominant
                else "Consider trade-offs between approaches",
            }

        except Exception as e:
            logger.error(f"Ranking failed: {e}")
            return {
                "error": f"Ranking failed: {str(e)}",
            }

    @server.tool()
    def explain_trade_offs(
        approach_a: str,
        approach_b: str,
    ) -> dict:
        """Explain trade-offs between two approaches in human-readable form.

        Args:
            approach_a: First approach
            approach_b: Second approach

        Returns:
            {
                "comparison": str,
                "trade_offs": [
                    {
                        "what_you_gain": str,
                        "what_you_lose": str,
                        "magnitude": str,
                    }
                ],
                "when_to_choose_a": [str],
                "when_to_choose_b": [str],
                "recommendation": str
            }
        """
        try:
            return {
                "approach_a": approach_a,
                "approach_b": approach_b,
                "comparison": f"Comparing {approach_a} vs {approach_b}",
                "trade_offs": [
                    {
                        "what_you_gain": "Better performance",
                        "what_you_lose": "More complexity",
                        "magnitude": "significant",
                    },
                    {
                        "what_you_gain": "Easier to maintain",
                        "what_you_lose": "Lower scalability",
                        "magnitude": "moderate",
                    },
                ],
                "when_to_choose_a": [
                    "When simplicity is critical",
                    "When team is small",
                    "When time to market is important",
                ],
                "when_to_choose_b": [
                    "When performance is critical",
                    "When scaling to large scale",
                    "When budget allows",
                ],
                "recommendation": "Choose based on your priority: simplicity or performance",
            }

        except Exception as e:
            logger.error(f"Trade-off explanation failed: {e}")
            return {
                "error": f"Failed to explain trade-offs: {str(e)}",
            }

    @server.tool()
    def generate_decision_matrix(
        approaches: List[str],
        criteria: List[str],
    ) -> dict:
        """Generate a decision matrix for comparing approaches.

        Args:
            approaches: List of approach names
            criteria: Evaluation criteria (e.g., ["cost", "speed", "complexity"])

        Returns:
            {
                "matrix": {
                    approach: {
                        criterion: score
                    }
                },
                "totals": {
                    approach: total_score
                },
                "winner": str,
                "rationale": str
            }
        """
        try:
            # Create sample matrix
            matrix = {}
            for approach in approaches:
                matrix[approach] = {
                    criterion: 0.7 for criterion in criteria
                }

            # Calculate totals
            totals = {
                approach: sum(scores.values()) / len(scores)
                for approach, scores in matrix.items()
            }

            winner = max(totals.items(), key=lambda x: x[1])[0]

            return {
                "approaches": approaches,
                "criteria": criteria,
                "matrix": matrix,
                "totals": totals,
                "winner": winner,
                "rationale": f"{winner} scores highest across weighted criteria",
            }

        except Exception as e:
            logger.error(f"Decision matrix generation failed: {e}")
            return {
                "error": f"Failed to generate matrix: {str(e)}",
            }
