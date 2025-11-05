"""
Memory Health Skill - Auto-triggered memory quality assessment

Auto-triggers on:
- SessionStart (automatic)
- "how's my memory?"
- "memory health"
- "what are my knowledge gaps?"
- /memory-health

Provides:
- Quality metrics
- Coverage analysis
- Gap detection
- Domain expertise breakdown
"""

import asyncio
import re
from typing import Optional, Dict, Any
from dataclasses import dataclass, field


@dataclass
class MemoryQualityReport:
    """Memory system health report"""
    overall_score: float  # 0.0-1.0
    total_memories: int
    memory_breakdown: Dict[str, int] = field(default_factory=dict)
    domain_coverage: Dict[str, float] = field(default_factory=dict)
    gaps: list = field(default_factory=list)
    contradictions: list = field(default_factory=list)
    uncertainties: list = field(default_factory=list)
    recommendations: list = field(default_factory=list)


class MemoryHealthSkill:
    """Auto-triggered memory health assessment skill"""

    def __init__(self):
        self.trigger_patterns = self._compile_patterns()

    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for memory health queries"""
        return {
            "how_is_memory": re.compile(
                r'how\s+(?:is|are)\s+(?:my|our)\s+memory\s*\??',
                re.IGNORECASE
            ),
            "memory_health": re.compile(
                r'memory\s+(?:health|status|condition)',
                re.IGNORECASE
            ),
            "memory_health_slash": re.compile(
                r'/memory-health',
                re.IGNORECASE
            ),
            "knowledge_gaps": re.compile(
                r'what\s+(?:are\s+)?(?:my|our|the)\s+(?:knowledge\s+)?gaps',
                re.IGNORECASE
            ),
            "memory_quality": re.compile(
                r'(?:memory|knowledge)\s+quality',
                re.IGNORECASE
            ),
        }

    def detect_health_check_intent(self, user_input: str) -> Optional[Dict[str, Any]]:
        """Detect if user is requesting memory health check

        Returns: Dict with check type, or None
        """
        for pattern_name, pattern in self.trigger_patterns.items():
            if pattern.search(user_input):
                return {
                    "check_type": pattern_name,
                    "include_gaps": "gap" in user_input.lower(),
                    "include_domain_breakdown": True,
                    "confidence": 0.9,
                }

        return None

    def should_trigger(self, user_input: str) -> bool:
        """Check if skill should auto-trigger"""
        if not user_input or len(user_input) < 8:
            return False

        return self.detect_health_check_intent(user_input) is not None

    async def assess_memory_quality(self) -> MemoryQualityReport:
        """Assess overall memory system quality

        Returns: Comprehensive health report
        """
        # In real implementation, would query memory system
        # For now, return mock report

        report = MemoryQualityReport(
            overall_score=0.85,
            total_memories=247,
            memory_breakdown={
                "semantic": 120,
                "episodic": 85,
                "procedural": 32,
                "graph_entities": 156,
            },
            domain_coverage={
                "Claude Code": 0.95,
                "Memory Systems": 0.88,
                "Research Methods": 0.76,
                "Project Management": 0.65,
                "Python Development": 0.82,
            },
            gaps=[
                "Limited knowledge of Go programming language",
                "Minimal coverage of DevOps/Infrastructure",
                "Sparse data on mobile development",
            ],
            contradictions=[
                "Conflicting approaches to error handling (found 2 patterns)",
                "Different memory consolidation strategies documented",
            ],
            uncertainties=[
                "Optimal context window size for large codebases (0.6 confidence)",
                "Best practices for multi-agent task distribution (0.7 confidence)",
            ],
            recommendations=[
                "Consolidate findings on memory consolidation (appearing in 3 sources)",
                "Research mobile development patterns (domain coverage gap)",
                "Resolve contradiction on error handling approaches",
            ]
        )

        return report

    async def analyze_domain_expertise(self) -> Dict[str, Any]:
        """Analyze expertise across domains

        Returns: Domain expertise breakdown
        """
        # In real implementation, would aggregate across memory layers
        return {
            "expert_domains": [
                {"name": "Claude Code", "score": 0.95, "confidence": 0.9},
                {"name": "Python", "score": 0.88, "confidence": 0.85},
                {"name": "Research Methods", "score": 0.82, "confidence": 0.8},
            ],
            "emerging_domains": [
                {"name": "Memory Systems", "score": 0.65, "confidence": 0.7},
                {"name": "Agent Orchestration", "score": 0.72, "confidence": 0.75},
            ],
            "weak_domains": [
                {"name": "Go Programming", "score": 0.2, "confidence": 0.8},
                {"name": "DevOps", "score": 0.15, "confidence": 0.85},
                {"name": "Mobile Development", "score": 0.1, "confidence": 0.9},
            ]
        }

    async def handle_user_input(
        self,
        user_input: str,
        include_gaps: bool = False,
        include_domain_breakdown: bool = True,
        include_detail: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Main entry point for memory health check

        Args:
            user_input: User's input
            include_gaps: Include gap analysis
            include_domain_breakdown: Include domain expertise
            include_detail: Include detailed metrics

        Returns:
            Health report or None
        """
        # Detect intent
        intent = self.detect_health_check_intent(user_input)
        if not intent:
            return None

        # Assess memory quality
        quality_report = await self.assess_memory_quality()

        # Build response
        result = {
            "status": "healthy" if quality_report.overall_score >= 0.80 else "needs_attention",
            "overall_score": quality_report.overall_score,
            "total_memories": quality_report.total_memories,
        }

        # Add memory breakdown if requested
        if include_detail:
            result["memory_breakdown"] = quality_report.memory_breakdown

        # Add domain breakdown if requested
        if include_domain_breakdown:
            domains = await self.analyze_domain_expertise()
            result["domain_expertise"] = domains

        # Add gaps if requested or detected in query
        if include_gaps or "gap" in user_input.lower():
            result["gaps"] = quality_report.gaps
            result["contradictions"] = quality_report.contradictions
            result["uncertainties"] = quality_report.uncertainties

        # Add recommendations
        result["recommendations"] = quality_report.recommendations

        return result


# ============================================================================
# Global Skill Instance
# ============================================================================

_memory_health_skill_instance: Optional[MemoryHealthSkill] = None


def get_memory_health_skill() -> MemoryHealthSkill:
    """Get or create global skill instance"""
    global _memory_health_skill_instance
    if _memory_health_skill_instance is None:
        _memory_health_skill_instance = MemoryHealthSkill()
    return _memory_health_skill_instance


# ============================================================================
# Hook for Auto-Triggering
# ============================================================================

async def auto_trigger_memory_health(user_input: str) -> Optional[Dict[str, Any]]:
    """
    Called by UserPromptSubmit or SessionStart hooks.

    Returns: Health report if triggered, None otherwise
    """
    skill = get_memory_health_skill()

    if not skill.should_trigger(user_input):
        return None

    result = await skill.handle_user_input(user_input)
    return result


async def auto_trigger_memory_health_session_start() -> Dict[str, Any]:
    """
    Called by SessionStart hook automatically.

    Returns: Health report (always)
    """
    skill = get_memory_health_skill()
    result = await skill.handle_user_input(
        "memory health",
        include_gaps=False,
        include_domain_breakdown=True,
        include_detail=False
    )
    return result


# ============================================================================
# Example Usage
# ============================================================================

async def example_usage():
    """Example of skill usage"""
    skill = MemoryHealthSkill()

    # Example 1: General health check
    user_input_1 = "how's my memory?"
    result_1 = await skill.handle_user_input(user_input_1)
    print("Example 1: General health check")
    print(f"Status: {result_1.get('status')}")
    print(f"Score: {result_1.get('overall_score')}")

    # Example 2: With gap analysis
    user_input_2 = "what are my knowledge gaps?"
    result_2 = await skill.handle_user_input(user_input_2, include_gaps=True)
    print("\nExample 2: With gap analysis")
    print(f"Gaps found: {len(result_2.get('gaps', []))}")
    print(f"Contradictions: {len(result_2.get('contradictions', []))}")

    # Example 3: SessionStart automatic check
    result_3 = await auto_trigger_memory_health_session_start()
    print("\nExample 3: SessionStart automatic check")
    print(f"Status: {result_3.get('status')}")
    print(f"Domains: {len(result_3.get('domain_expertise', {}).get('expert_domains', []))}")

    # Example 4: No health check detected
    user_input_4 = "What time is it?"
    result_4 = await skill.handle_user_input(user_input_4)
    print(f"\nExample 4: No health check detected")
    print(f"Result: {result_4}")


if __name__ == "__main__":
    asyncio.run(example_usage())
