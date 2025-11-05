"""
Learning Tracker Skill - Auto-triggered learning effectiveness analysis

Auto-triggers on:
- SessionEnd (automatic)
- "how am I learning?"
- "learning effectiveness"
- /learning
"""

import asyncio
import re
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class LearningMetrics:
    """Learning effectiveness metrics"""
    encoding_success_rate: float  # How well facts stick (0-1)
    strategy_effectiveness_score: float
    improvement_trend: float  # Week-over-week improvement
    optimal_strategies: list
    underperforming_strategies: list


class LearningTrackerSkill:
    """Auto-triggered learning tracker skill"""

    def __init__(self):
        self.trigger_patterns = self._compile_patterns()

    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        return {
            "how_learning": re.compile(
                r'how\s+(?:am|are)\s+(?:i|we|you)\s+learning',
                re.IGNORECASE
            ),
            "learning_effectiveness": re.compile(
                r'learning\s+(?:effectiveness|progress|analysis)',
                re.IGNORECASE
            ),
            "learning_slash": re.compile(
                r'/learning',
                re.IGNORECASE
            ),
            "best_strategies": re.compile(
                r'what\s+(?:strategies|techniques)\s+work\s+best',
                re.IGNORECASE
            ),
        }

    def detect_learning_intent(self, user_input: str) -> Optional[Dict[str, Any]]:
        for pattern_name, pattern in self.trigger_patterns.items():
            if pattern.search(user_input):
                return {
                    "learning_query": pattern_name,
                    "confidence": 0.9,
                }
        return None

    def should_trigger(self, user_input: str) -> bool:
        if not user_input or len(user_input) < 8:
            return False
        return self.detect_learning_intent(user_input) is not None

    async def analyze_learning_effectiveness(self) -> LearningMetrics:
        """Analyze encoding effectiveness and strategy optimization"""
        # Mock implementation
        return LearningMetrics(
            encoding_success_rate=0.82,
            strategy_effectiveness_score=0.79,
            improvement_trend=0.12,
            optimal_strategies=[
                "TDD (Test-Driven Development) - 94% retention",
                "Multi-source research - 89% retention",
                "Hands-on implementation - 91% retention",
            ],
            underperforming_strategies=[
                "Passive reading - 45% retention",
                "Single-source learning - 62% retention",
            ]
        )

    async def handle_user_input(self, user_input: str = "") -> Optional[Dict[str, Any]]:
        if user_input and not self.should_trigger(user_input):
            return None

        metrics = await self.analyze_learning_effectiveness()

        return {
            "status": "success",
            "encoding_success_rate": metrics.encoding_success_rate,
            "strategy_effectiveness": metrics.strategy_effectiveness_score,
            "improvement_trend": f"+{metrics.improvement_trend*100:.1f}%",
            "optimal_strategies": metrics.optimal_strategies,
            "improvement_opportunities": metrics.underperforming_strategies,
            "overall_assessment": "Good progress - focus on active learning",
        }


_learning_tracker_skill_instance: Optional[LearningTrackerSkill] = None


def get_learning_tracker_skill() -> LearningTrackerSkill:
    global _learning_tracker_skill_instance
    if _learning_tracker_skill_instance is None:
        _learning_tracker_skill_instance = LearningTrackerSkill()
    return _learning_tracker_skill_instance


async def auto_trigger_learning_tracker(user_input: str) -> Optional[Dict[str, Any]]:
    skill = get_learning_tracker_skill()
    if not skill.should_trigger(user_input):
        return None
    return await skill.handle_user_input(user_input)


async def auto_trigger_learning_tracker_session_end() -> Dict[str, Any]:
    skill = get_learning_tracker_skill()
    return await skill.handle_user_input()
