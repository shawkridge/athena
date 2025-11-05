"""
Consolidation Skill - Auto-triggered sleep-like pattern extraction

Auto-triggers on:
- SessionEnd (automatic)
- "consolidate"
- "extract patterns"
- /consolidate

Converts episodic events to semantic patterns with quality metrics.
"""

import asyncio
import re
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field


@dataclass
class ConsolidationMetrics:
    """Quality metrics for consolidation"""
    compression_ratio: float  # How many episodic events → 1 pattern
    retrieval_recall: float   # How well patterns retrieve original events
    pattern_consistency: float  # Pattern coherence (0-1)
    information_density: float  # How much info per pattern


@dataclass
class ExtractedPattern:
    """Pattern extracted from episodic events"""
    name: str
    description: str
    source_events_count: int
    category: str  # "workflow", "debugging", "refactoring", "deployment", "testing"
    metrics: ConsolidationMetrics
    related_files: List[str] = field(default_factory=list)
    frequency: int = 0


class ConsolidationSkill:
    """Auto-triggered consolidation skill"""

    def __init__(self):
        self.trigger_patterns = self._compile_patterns()

    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for consolidation triggers"""
        return {
            "consolidate": re.compile(
                r'consolidate(?:\s+memory)?',
                re.IGNORECASE
            ),
            "extract_patterns": re.compile(
                r'extract\s+(?:patterns|learnings)',
                re.IGNORECASE
            ),
            "consolidate_slash": re.compile(
                r'/consolidate',
                re.IGNORECASE
            ),
            "what_learned": re.compile(
                r'what\s+(?:patterns|did\s+)?(?:i|we|you)\s+(?:learn|discover|extract)',
                re.IGNORECASE
            ),
        }

    def detect_consolidation_intent(self, user_input: str) -> Optional[Dict[str, Any]]:
        """Detect if user is requesting consolidation

        Returns: Dict with consolidation type, or None
        """
        for pattern_name, pattern in self.trigger_patterns.items():
            if pattern.search(user_input):
                return {
                    "consolidation_type": pattern_name,
                    "dry_run": "--dry-run" in user_input,
                    "include_metrics": "--metrics" in user_input or "--detail" in user_input,
                    "confidence": 0.9,
                }

        return None

    def should_trigger(self, user_input: str) -> bool:
        """Check if skill should auto-trigger"""
        if not user_input or len(user_input) < 8:
            return False

        return self.detect_consolidation_intent(user_input) is not None

    async def extract_patterns(self) -> List[ExtractedPattern]:
        """Extract patterns from episodic events

        Returns: List of newly extracted patterns
        """
        # In real implementation, would:
        # 1. Fetch episodic events since last consolidation
        # 2. Cluster by session/time/file proximity
        # 3. Use Claude extended thinking to extract patterns
        # 4. Store in semantic/procedural memory
        # 5. Return metrics

        # Mock extraction
        patterns = [
            ExtractedPattern(
                name="TDD Workflow",
                description="Pattern: Write test → Fail → Implement → Pass → Refactor",
                source_events_count=12,
                category="testing",
                metrics=ConsolidationMetrics(
                    compression_ratio=12.0,
                    retrieval_recall=0.92,
                    pattern_consistency=0.88,
                    information_density=0.85
                ),
                related_files=["tests/", "src/"],
                frequency=3
            ),
            ExtractedPattern(
                name="Code Review Integration",
                description="Pattern: Code → Lint → Review → Fix → Commit → Push → PR",
                source_events_count=8,
                category="workflow",
                metrics=ConsolidationMetrics(
                    compression_ratio=8.0,
                    retrieval_recall=0.89,
                    pattern_consistency=0.91,
                    information_density=0.87
                ),
                related_files=["src/", ".github/"],
                frequency=2
            ),
        ]

        return patterns

    async def calculate_consolidation_metrics(
        self,
        patterns: List[ExtractedPattern]
    ) -> Dict[str, Any]:
        """Calculate overall consolidation metrics

        Returns: Aggregated metrics
        """
        if not patterns:
            return {}

        total_source_events = sum(p.source_events_count for p in patterns)
        avg_compression = sum(p.metrics.compression_ratio for p in patterns) / len(patterns)
        avg_recall = sum(p.metrics.retrieval_recall for p in patterns) / len(patterns)
        avg_consistency = sum(p.metrics.pattern_consistency for p in patterns) / len(patterns)
        avg_density = sum(p.metrics.information_density for p in patterns) / len(patterns)

        return {
            "total_patterns_extracted": len(patterns),
            "total_source_events": total_source_events,
            "compression_ratio": avg_compression,
            "retrieval_recall": avg_recall,
            "pattern_consistency": avg_consistency,
            "information_density": avg_density,
            "quality_score": (avg_recall + avg_consistency + avg_density) / 3,
        }

    async def handle_user_input(
        self,
        user_input: str = "",
        dry_run: bool = False,
        include_metrics: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Main entry point for consolidation

        Args:
            user_input: User's input (optional)
            dry_run: Show what would be consolidated without saving
            include_metrics: Include detailed metrics

        Returns:
            Consolidation report or None
        """
        # Detect intent if user_input provided
        if user_input:
            intent = self.detect_consolidation_intent(user_input)
            if not intent:
                return None
            dry_run = intent.get("dry_run", dry_run)
            include_metrics = intent.get("include_metrics", include_metrics)

        # Extract patterns
        patterns = await self.extract_patterns()

        # Calculate metrics
        metrics = await self.calculate_consolidation_metrics(patterns)

        # Build response
        result = {
            "status": "success",
            "dry_run": dry_run,
            "patterns_extracted": len(patterns),
            "patterns": [
                {
                    "name": p.name,
                    "description": p.description,
                    "source_events": p.source_events_count,
                    "category": p.category,
                    "frequency": p.frequency,
                    "related_files": p.related_files,
                }
                for p in patterns
            ],
        }

        # Add metrics if requested
        if include_metrics:
            result["consolidation_metrics"] = metrics

        return result


# ============================================================================
# Global Skill Instance
# ============================================================================

_consolidation_skill_instance: Optional[ConsolidationSkill] = None


def get_consolidation_skill() -> ConsolidationSkill:
    """Get or create global skill instance"""
    global _consolidation_skill_instance
    if _consolidation_skill_instance is None:
        _consolidation_skill_instance = ConsolidationSkill()
    return _consolidation_skill_instance


# ============================================================================
# Hook for Auto-Triggering
# ============================================================================

async def auto_trigger_consolidation(user_input: str) -> Optional[Dict[str, Any]]:
    """
    Called by UserPromptSubmit hook when user requests consolidation.

    Returns: Consolidation report if triggered, None otherwise
    """
    skill = get_consolidation_skill()

    if not skill.should_trigger(user_input):
        return None

    result = await skill.handle_user_input(user_input)
    return result


async def auto_trigger_consolidation_session_end() -> Dict[str, Any]:
    """
    Called by SessionEnd hook automatically.

    Returns: Consolidation report (always)
    """
    skill = get_consolidation_skill()
    result = await skill.handle_user_input(
        user_input="",
        dry_run=False,
        include_metrics=True
    )
    return result


# ============================================================================
# Example Usage
# ============================================================================

async def example_usage():
    """Example of skill usage"""
    skill = ConsolidationSkill()

    # Example 1: Manual consolidation
    user_input_1 = "consolidate"
    result_1 = await skill.handle_user_input(user_input_1, include_metrics=True)
    print("Example 1: Manual consolidation")
    print(f"Patterns extracted: {result_1.get('patterns_extracted')}")
    print(f"Quality score: {result_1.get('consolidation_metrics', {}).get('quality_score', 'N/A')}")

    # Example 2: Dry run
    user_input_2 = "consolidate --dry-run"
    result_2 = await skill.handle_user_input(user_input_2)
    print("\nExample 2: Dry run")
    print(f"Dry run: {result_2.get('dry_run')}")

    # Example 3: SessionEnd automatic consolidation
    result_3 = await auto_trigger_consolidation_session_end()
    print("\nExample 3: SessionEnd automatic consolidation")
    print(f"Patterns extracted: {result_3.get('patterns_extracted')}")

    # Example 4: No consolidation intent
    user_input_4 = "What time is it?"
    result_4 = await skill.handle_user_input(user_input_4)
    print(f"\nExample 4: No consolidation intent")
    print(f"Result: {result_4}")


if __name__ == "__main__":
    asyncio.run(example_usage())
