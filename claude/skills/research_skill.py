"""
Research Skill - Auto-triggered Multi-Source Research Orchestrator

This skill auto-detects research requests and orchestrates parallel research
across 16 specialized sources with credibility scoring and cross-validation.

Installation: Place in ~/.claude/skills/

Auto-triggers on:
- "research [topic]"
- "/research [topic]"
- "investigate [topic]"
- "find information about [topic]"
- Research questions: "What is X?", "Tell me about X"
"""

import asyncio
import json
import re
from typing import Optional, Dict, Any
from research_orchestrator import ResearchOrchestrator


class ResearchSkill:
    """Auto-triggered research skill"""

    def __init__(self):
        self.orchestrator = ResearchOrchestrator()
        self.trigger_patterns = self._compile_patterns()

    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for research detection"""
        return {
            "research_command": re.compile(
                r'research\s+"([^"]+)"(?:\s+--(\w+)(?:=(\S+))?)*',
                re.IGNORECASE
            ),
            "research_slash": re.compile(
                r'/research\s+"?([^"\n]+)"?(?:\s+--(\w+))?',
                re.IGNORECASE
            ),
            "investigate": re.compile(
                r'investigate\s+(?:about\s+)?([^,.!?\n]+)',
                re.IGNORECASE
            ),
            "find_info": re.compile(
                r'find\s+(?:information\s+about|out\s+about)\s+([^,.!?\n]+)',
                re.IGNORECASE
            ),
            "research_question": re.compile(
                r'(?:what|tell|show|how)\s+(?:is|are|do|does|can|should)\s+(?:the\s+)?([^?,.!]+)',
                re.IGNORECASE
            ),
            "knowledge_gap": re.compile(
                r'(?:i\s+need\s+to\s+know|looking\s+for)\s+(?:information\s+)?(?:about|on)\s+([^,.!?\n]+)',
                re.IGNORECASE
            ),
        }

    def detect_research_intent(self, user_input: str) -> Optional[Dict[str, Any]]:
        """Detect if user is requesting research

        Returns: Dict with detected topic and filters, or None
        """
        # Try each pattern
        for pattern_name, pattern in self.trigger_patterns.items():
            match = pattern.search(user_input)
            if match:
                topic = match.group(1).strip()
                return {
                    "topic": topic,
                    "pattern": pattern_name,
                    "confidence": 0.9,
                }

        return None

    def parse_filters(self, user_input: str) -> Dict[str, Any]:
        """Parse optional research filters from input"""
        filters = {
            "sources": None,
            "category": None,
            "high_confidence_only": False,
            "async_mode": False,
        }

        # Category filter
        category_match = re.search(
            r'--category\s+(academic|docs|implementation|research|community|emerging)',
            user_input,
            re.IGNORECASE
        )
        if category_match:
            filters["category"] = category_match.group(1).lower()

        # Sources filter
        sources_match = re.search(
            r'--sources\s+"?([^"]+)"?',
            user_input
        )
        if sources_match:
            filters["sources"] = [s.strip() for s in sources_match.group(1).split(",")]

        # Confidence filter
        if "--high-confidence-only" in user_input:
            filters["high_confidence_only"] = True

        # Async mode
        if "--async" in user_input:
            filters["async_mode"] = True

        return filters

    async def execute(
        self,
        topic: str,
        sources: Optional[list] = None,
        category: Optional[str] = None,
        high_confidence_only: bool = False,
        async_mode: bool = False,
    ) -> Dict[str, Any]:
        """Execute research orchestration

        Args:
            topic: Research topic
            sources: Specific sources (None = all 16)
            category: Filter by category
            high_confidence_only: Only credibility ≥0.8
            async_mode: Run in background

        Returns:
            Aggregated research results with credibility scores
        """
        # Determine active sources
        active_sources = self.orchestrator.get_active_sources(sources, category)

        # Build orchestration prompt for Task tool
        from research_integration import ResearchCommandHandler
        handler = ResearchCommandHandler()

        orchestration_prompt = handler.build_orchestration_prompt(
            topic=topic,
            active_sources=active_sources,
            high_confidence_only=high_confidence_only,
        )

        # Return execution instructions for Task tool
        return {
            "status": "ready_to_execute",
            "topic": topic,
            "sources_count": len(active_sources),
            "active_sources": active_sources,
            "filters": {
                "high_confidence_only": high_confidence_only,
                "async_mode": async_mode,
            },
            "next_step": "Invoke Task tool with research-coordinator agent",
            "orchestration_prompt": orchestration_prompt,
        }

    def should_trigger(self, user_input: str) -> bool:
        """Check if skill should auto-trigger"""
        if not user_input or len(user_input) < 5:
            return False

        # Detect research intent
        intent = self.detect_research_intent(user_input)
        return intent is not None

    async def handle_user_input(self, user_input: str) -> Optional[Dict[str, Any]]:
        """Main entry point: handle user input and auto-trigger if needed

        Args:
            user_input: User's input/prompt

        Returns:
            Research results or orchestration instructions, or None
        """
        # Detect research intent
        intent = self.detect_research_intent(user_input)
        if not intent:
            return None

        # Parse filters
        filters = self.parse_filters(user_input)

        # Execute research
        result = await self.execute(
            topic=intent["topic"],
            sources=filters["sources"],
            category=filters["category"],
            high_confidence_only=filters["high_confidence_only"],
            async_mode=filters["async_mode"],
        )

        return result


# ============================================================================
# Global Skill Instance
# ============================================================================

_research_skill_instance: Optional[ResearchSkill] = None


def get_research_skill() -> ResearchSkill:
    """Get or create global skill instance"""
    global _research_skill_instance
    if _research_skill_instance is None:
        _research_skill_instance = ResearchSkill()
    return _research_skill_instance


# ============================================================================
# Hook for Auto-Triggering
# ============================================================================

async def auto_trigger_research(user_input: str) -> Optional[Dict[str, Any]]:
    """
    Called by the system when user input is detected.

    Should be registered as a hook that triggers for each user prompt.

    Returns: Research results if research was triggered, None otherwise
    """
    skill = get_research_skill()

    # Check if skill should trigger
    if not skill.should_trigger(user_input):
        return None

    # Execute research
    result = await skill.handle_user_input(user_input)
    return result


# ============================================================================
# Example Usage
# ============================================================================

async def example_usage():
    """Example of skill usage"""
    skill = ResearchSkill()

    # Example 1: Direct research request
    user_input_1 = 'research "Claude Code skills"'
    result_1 = await skill.handle_user_input(user_input_1)
    print("Example 1: Direct research request")
    print(f"Topic: {result_1.get('topic')}")
    print(f"Sources: {result_1.get('sources_count')}")

    # Example 2: With category filter
    user_input_2 = 'research "pytorch optimization" --category implementation'
    result_2 = await skill.handle_user_input(user_input_2)
    print("\nExample 2: With category filter")
    print(f"Topic: {result_2.get('topic')}")
    print(f"Filters: {result_2.get('filters')}")

    # Example 3: Natural language question
    user_input_3 = 'Tell me about Claude Code and its capabilities'
    result_3 = await skill.handle_user_input(user_input_3)
    print("\nExample 3: Natural language question")
    print(f"Topic: {result_3.get('topic')}")

    # Example 4: No research detected
    user_input_4 = 'What time is it?'
    result_4 = await skill.handle_user_input(user_input_4)
    print(f"\nExample 4: No research detected")
    print(f"Result: {result_4}")


if __name__ == "__main__":
    asyncio.run(example_usage())
