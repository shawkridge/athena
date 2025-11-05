"""
Focus Skill - Auto-triggered attention management

Auto-triggers on:
- Cognitive load HIGH detected
- "focus on X"
- "suppress Y"
- /focus
"""

import asyncio
import re
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class AttentionState:
    """Current attention management state"""
    primary_focus: Optional[str]
    suppressed_items: list
    cognitive_load: str  # "LOW", "MEDIUM", "HIGH"
    working_memory_active: int


class FocusSkill:
    """Auto-triggered focus management skill"""

    def __init__(self):
        self.trigger_patterns = self._compile_patterns()

    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        return {
            "focus_on": re.compile(
                r'focus\s+on\s+(.+)',
                re.IGNORECASE
            ),
            "suppress": re.compile(
                r'(?:suppress|ignore|clear)\s+(.+)',
                re.IGNORECASE
            ),
            "clear_context": re.compile(
                r'clear\s+(?:distractions|context|noise)',
                re.IGNORECASE
            ),
            "focus_slash": re.compile(
                r'/focus',
                re.IGNORECASE
            ),
            "cognitive_load_high": re.compile(
                r'(?:my\s+)?cognitive\s+load\s+(?:is\s+)?(?:high|overwhelming)',
                re.IGNORECASE
            ),
        }

    def detect_focus_intent(self, user_input: str) -> Optional[Dict[str, Any]]:
        for pattern_name, pattern in self.trigger_patterns.items():
            match = pattern.search(user_input)
            if match:
                try:
                    target = match.group(1).strip()
                except IndexError:
                    target = None

                return {
                    "focus_action": pattern_name,
                    "target": target,
                    "confidence": 0.9,
                }
        return None

    def should_trigger(self, user_input: str) -> bool:
        if not user_input or len(user_input) < 8:
            return False
        return self.detect_focus_intent(user_input) is not None

    async def manage_attention(self, focus_target: Optional[str] = None) -> AttentionState:
        """Manage attention and suppress distractions"""
        # Mock implementation
        return AttentionState(
            primary_focus=focus_target,
            suppressed_items=[
                "Previous unrelated context",
                "Low-priority memories",
            ],
            cognitive_load="MEDIUM",
            working_memory_active=5
        )

    async def handle_user_input(self, user_input: str) -> Optional[Dict[str, Any]]:
        intent = self.detect_focus_intent(user_input)
        if not intent:
            return None

        focus_target = intent.get("target")
        attention = await self.manage_attention(focus_target)

        result = {
            "status": "success",
            "action": intent.get("focus_action"),
        }

        if focus_target:
            result["focused_on"] = focus_target

        if attention.suppressed_items:
            result["suppressed"] = attention.suppressed_items

        result["cognitive_load"] = attention.cognitive_load
        result["working_memory_items"] = attention.working_memory_active

        return result


_focus_skill_instance: Optional[FocusSkill] = None


def get_focus_skill() -> FocusSkill:
    global _focus_skill_instance
    if _focus_skill_instance is None:
        _focus_skill_instance = FocusSkill()
    return _focus_skill_instance


async def auto_trigger_focus(user_input: str) -> Optional[Dict[str, Any]]:
    skill = get_focus_skill()
    if not skill.should_trigger(user_input):
        return None
    return await skill.handle_user_input(user_input)
