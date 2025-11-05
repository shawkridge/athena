"""
Associations Skill - Auto-triggered knowledge graph navigation

Auto-triggers on:
- "how does X relate to Y?"
- "show me connections to X"
- "explore relationships"
- /associations
"""

import asyncio
import re
from typing import Optional, Dict, Any, List
from dataclasses import dataclass


@dataclass
class Association:
    """Knowledge graph association"""
    from_entity: str
    to_entity: str
    relation_type: str
    strength: float  # 0-1


class AssociationsSkill:
    """Auto-triggered associations explorer skill"""

    def __init__(self):
        self.trigger_patterns = self._compile_patterns()

    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        return {
            "relate": re.compile(
                r'(?:how\s+)?(?:does|is)?\s*(.+?)\s+(?:relate|connect|link)\s+to\s+(.+?)\??$',
                re.IGNORECASE | re.MULTILINE
            ),
            "show_connections": re.compile(
                r'show\s+(?:me\s+)?(?:the\s+)?(?:associations|connections)\s+(?:for|with|of)\s+(.+)',
                re.IGNORECASE
            ),
            "associations_slash": re.compile(
                r'/associations',
                re.IGNORECASE
            ),
            "explore_relationships": re.compile(
                r'explore\s+(?:connections|relationships)\s+(?:with|for)\s+(.+)',
                re.IGNORECASE
            ),
        }

    def detect_associations_intent(self, user_input: str) -> Optional[Dict[str, Any]]:
        for pattern_name, pattern in self.trigger_patterns.items():
            match = pattern.search(user_input)
            if match:
                try:
                    if pattern_name == "relate":
                        entity1 = match.group(1).strip()
                        entity2 = match.group(2).strip()
                        target = f"{entity1} <-> {entity2}"
                    else:
                        target = match.group(1).strip()
                except IndexError:
                    target = None

                return {
                    "associations_query": pattern_name,
                    "target": target,
                    "confidence": 0.9,
                }
        return None

    def should_trigger(self, user_input: str) -> bool:
        if not user_input or len(user_input) < 10:
            return False
        return self.detect_associations_intent(user_input) is not None

    async def explore_associations(self, entity: str) -> List[Association]:
        """Explore knowledge graph associations for an entity"""
        # Mock implementation
        return [
            Association(
                from_entity=entity,
                to_entity="Memory consolidation",
                relation_type="related_to",
                strength=0.92
            ),
            Association(
                from_entity=entity,
                to_entity="Episodic memory",
                relation_type="uses",
                strength=0.88
            ),
            Association(
                from_entity=entity,
                to_entity="Semantic memory",
                relation_type="stores_to",
                strength=0.85
            ),
        ]

    async def handle_user_input(self, user_input: str) -> Optional[Dict[str, Any]]:
        intent = self.detect_associations_intent(user_input)
        if not intent:
            return None

        target = intent.get("target")
        if not target:
            return None

        associations = await self.explore_associations(target)

        return {
            "status": "success",
            "query_entity": target,
            "associations_found": len(associations),
            "associations": [
                {
                    "from": a.from_entity,
                    "to": a.to_entity,
                    "relation": a.relation_type,
                    "strength": a.strength,
                }
                for a in associations
            ],
        }


_associations_skill_instance: Optional[AssociationsSkill] = None


def get_associations_skill() -> AssociationsSkill:
    global _associations_skill_instance
    if _associations_skill_instance is None:
        _associations_skill_instance = AssociationsSkill()
    return _associations_skill_instance


async def auto_trigger_associations(user_input: str) -> Optional[Dict[str, Any]]:
    skill = get_associations_skill()
    if not skill.should_trigger(user_input):
        return None
    return await skill.handle_user_input(user_input)
