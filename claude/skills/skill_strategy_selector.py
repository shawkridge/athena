"""
Strategy Selector Skill - Phase 3 Executive Function.

Auto-selects optimal decomposition strategy from 9 options.
Implements Sequential Thinking pattern with transparent reasoning.
"""

from typing import Any, Dict, List
from datetime import datetime
from .base_skill import BaseSkill, SkillResult


class StrategySelectorSkill(BaseSkill):
    """Auto-selects best decomposition strategy."""

    # 9 Decomposition strategies
    STRATEGIES = {
        "hierarchical": {
            "name": "HIERARCHICAL",
            "description": "Top-down architectural planning",
            "best_for": ["architecture", "complex", "design-heavy"],
            "base_score": 6.0,
        },
        "iterative": {
            "name": "ITERATIVE",
            "description": "MVP-first, incremental approach",
            "best_for": ["uncertain", "startup", "incremental"],
            "base_score": 6.0,
        },
        "spike": {
            "name": "SPIKE",
            "description": "Research/prototype dominant",
            "best_for": ["research", "unknown-tech", "poc"],
            "base_score": 6.0,
        },
        "parallel": {
            "name": "PARALLEL",
            "description": "Maximize concurrent work",
            "best_for": ["independent", "modular", "team-work"],
            "base_score": 6.0,
        },
        "sequential": {
            "name": "SEQUENTIAL",
            "description": "Strict linear ordering",
            "best_for": ["dependent", "ordered", "simple"],
            "base_score": 5.0,
        },
        "deadline_driven": {
            "name": "DEADLINE_DRIVEN",
            "description": "Time-critical, risk minimization",
            "best_for": ["urgent", "deadline", "critical"],
            "base_score": 6.0,
        },
        "quality_first": {
            "name": "QUALITY_FIRST",
            "description": "Extra review and testing phases",
            "best_for": ["security", "safety", "critical"],
            "base_score": 6.0,
        },
        "collaborative": {
            "name": "COLLABORATIVE",
            "description": "Team coordination focus",
            "best_for": ["team", "coordination", "distributed"],
            "base_score": 6.0,
        },
        "exploratory": {
            "name": "EXPLORATORY",
            "description": "Innovation and experimentation",
            "best_for": ["innovation", "r&d", "experimental"],
            "base_score": 6.0,
        },
    }

    def __init__(self):
        """Initialize skill."""
        super().__init__(
            skill_id="strategy-selector",
            skill_name="Strategy Selector"
        )

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Select best strategy for task.

        Args:
            context: Execution context with task_description, goal_id, etc.

        Returns:
            Result with selected strategy and reasoning
        """
        try:
            task_description = context.get('task_description', '')
            goal_id = context.get('active_goal_id')
            memory_manager = context.get('memory_manager')

            if not task_description:
                return SkillResult(
                    status="skipped",
                    data={"reason": "No task description"}
                ).to_dict()

            # Analyze task characteristics
            analysis = await self._analyze_task(task_description)

            # Score all strategies
            scores = self._score_strategies(analysis)

            # Select best strategy
            selected = max(scores.items(), key=lambda x: x[1]['score'])
            strategy_key, strategy_score = selected

            # Get alternatives
            alternatives = sorted(
                [(k, v) for k, v in scores.items() if k != strategy_key],
                key=lambda x: x[1]['score'],
                reverse=True
            )[:3]

            # Build reasoning
            reasoning = self._build_reasoning(
                analysis, strategy_key, strategy_score, alternatives
            )

            result = SkillResult(
                status="success",
                data={
                    "selected_strategy": strategy_key,
                    "strategy_name": self.STRATEGIES[strategy_key]['name'],
                    "confidence": strategy_score['score'],
                    "reasoning": reasoning,
                    "alternatives": [
                        {
                            "strategy": k,
                            "name": self.STRATEGIES[k]['name'],
                            "score": v['score'],
                            "reason": v.get('reason', ''),
                        }
                        for k, v in alternatives
                    ],
                    "task_analysis": analysis,
                    "all_scores": {k: v['score'] for k, v in scores.items()},
                    "timestamp": datetime.now().isoformat(),
                },
                actions=[
                    f"Use {self.STRATEGIES[strategy_key]['name']} strategy",
                    "Apply strategy-specific decomposition",
                    "Monitor strategy effectiveness during execution",
                ]
            )

            self._log_execution(result.to_dict())
            return result.to_dict()

        except Exception as e:
            return SkillResult(
                status="failed",
                error=str(e)
            ).to_dict()

    async def _analyze_task(self, task_description: str) -> Dict[str, Any]:
        """Analyze task characteristics.

        Evaluates:
        - Complexity (LOW, MEDIUM, HIGH, CRITICAL)
        - Uncertainty (well-defined vs unknown)
        - Timeline (loose vs tight)
        - Risk (low vs high)
        - Dependencies (independent vs dependent)
        """
        # Keyword analysis
        task_lower = task_description.lower()

        # Complexity detection
        complexity_keywords = {
            "critical": 10,
            "complex": 8,
            "architecture": 9,
            "integration": 7,
            "module": 5,
            "component": 6,
            "simple": 2,
        }
        complexity = sum(
            v for k, v in complexity_keywords.items() if k in task_lower
        ) / len(complexity_keywords) * 10

        # Uncertainty detection
        uncertainty_keywords = ["unknown", "unclear", "poc", "research", "experimental"]
        uncertainty = 1.0 if any(k in task_lower for k in uncertainty_keywords) else 0.3

        # Risk detection
        risk_keywords = ["critical", "security", "safety", "production"]
        risk = 1.0 if any(k in task_lower for k in risk_keywords) else 0.3

        # Dependency detection
        depend_keywords = ["depend", "block", "prerequisite"]
        dependencies = 1.0 if any(k in task_lower for k in depend_keywords) else 0.2

        # Timeline urgency
        urgency_keywords = ["urgent", "asap", "critical", "immediate"]
        urgency = 1.0 if any(k in task_lower for k in urgency_keywords) else 0.3

        return {
            "complexity": min(10, max(1, complexity)),
            "uncertainty": uncertainty,
            "risk": risk,
            "dependencies": dependencies,
            "urgency": urgency,
            "team_size_expected": 2,  # Default
            "has_external_dependencies": "api" in task_lower or "service" in task_lower,
        }

    def _score_strategies(self, analysis: Dict[str, Any]) -> Dict[str, Dict]:
        """Score all strategies against task characteristics."""
        scores = {}

        for key, strategy in self.STRATEGIES.items():
            score = strategy['base_score']
            reason_parts = []

            # Complexity adjustment
            if analysis['complexity'] > 8 and key in ['hierarchical', 'spike']:
                score += 2.0
                reason_parts.append("Good for complex tasks")
            elif analysis['complexity'] <= 5 and key == 'sequential':
                score += 1.5
                reason_parts.append("Good for simple tasks")

            # Uncertainty adjustment
            if analysis['uncertainty'] > 0.7 and key in ['spike', 'exploratory']:
                score += 2.5
                reason_parts.append("Handles uncertainty well")
            elif analysis['uncertainty'] < 0.5 and key == 'hierarchical':
                score += 1.5
                reason_parts.append("Clear requirements")

            # Risk adjustment
            if analysis['risk'] > 0.7 and key in ['quality_first', 'hierarchical']:
                score += 2.0
                reason_parts.append("High safety focus")

            # Urgency adjustment
            if analysis['urgency'] > 0.8 and key in ['deadline_driven', 'parallel']:
                score += 2.0
                reason_parts.append("Handles urgency well")

            # Dependencies adjustment
            if analysis['dependencies'] > 0.7 and key == 'hierarchical':
                score += 1.5
                reason_parts.append("Clear dependency handling")
            elif analysis['dependencies'] < 0.3 and key == 'parallel':
                score += 2.0
                reason_parts.append("Independent components")

            scores[key] = {
                'score': min(10.0, max(1.0, score)),
                'reason': " + ".join(reason_parts) if reason_parts else "Neutral fit",
            }

        return scores

    def _build_reasoning(self, analysis: Dict, selected_key: str,
                        selected_score: Dict, alternatives: List) -> Dict:
        """Build transparent reasoning for strategy selection."""
        strategy = self.STRATEGIES[selected_key]

        return {
            "decision": f"Selected {strategy['name']} strategy",
            "confidence": round(selected_score['score'], 1),
            "reasoning": {
                "task_characteristics": {
                    "complexity": f"{analysis['complexity']:.1f}/10",
                    "uncertainty": f"{analysis['uncertainty']:.1%}",
                    "risk": f"{analysis['risk']:.1%}",
                    "urgency": f"{analysis['urgency']:.1%}",
                    "dependencies": f"{analysis['dependencies']:.1%}",
                },
                "why_selected": selected_score['reason'],
                "fit_rating": self._get_fit_rating(selected_score['score']),
                "trade_offs": self._get_trade_offs(selected_key),
            },
            "sequential_thinking_transparent": True,
        }

    def _get_fit_rating(self, score: float) -> str:
        """Get human-readable fit rating."""
        if score >= 9:
            return "Excellent fit"
        elif score >= 7:
            return "Good fit"
        elif score >= 5:
            return "Adequate fit"
        else:
            return "Poor fit (fallback)"

    def _get_trade_offs(self, strategy_key: str) -> Dict:
        """Get strategy trade-offs."""
        trade_offs = {
            "hierarchical": {
                "pros": ["Clear architecture", "Risk reduction"],
                "cons": ["Slower to MVP", "Upfront planning overhead"],
            },
            "iterative": {
                "pros": ["Fast MVP", "Flexible"],
                "cons": ["Higher refactoring risk", "Unclear requirements"],
            },
            "spike": {
                "pros": ["Research first", "Technical clarity"],
                "cons": ["Slower execution", "Research overhead"],
            },
            "parallel": {
                "pros": ["Maximum speed", "Team utilization"],
                "cons": ["Merge complexity", "Coordination overhead"],
            },
            "sequential": {
                "pros": ["Simple execution", "Clear dependencies"],
                "cons": ["Longer timeline", "Blocked waiting"],
            },
            "deadline_driven": {
                "pros": ["Meets deadline", "Risk focused"],
                "cons": ["Less elegant", "Technical debt possible"],
            },
            "quality_first": {
                "pros": ["High quality", "Few bugs"],
                "cons": ["Slower execution", "Over-engineering risk"],
            },
            "collaborative": {
                "pros": ["Team alignment", "Knowledge sharing"],
                "cons": ["Coordination overhead", "Slower decisions"],
            },
            "exploratory": {
                "pros": ["Innovation", "Multiple approaches"],
                "cons": ["Slower execution", "Uncertain outcome"],
            },
        }
        return trade_offs.get(strategy_key, {})


# Singleton instance
_instance = None


def get_skill():
    """Get or create skill instance."""
    global _instance
    if _instance is None:
        _instance = StrategySelectorSkill()
    return _instance
