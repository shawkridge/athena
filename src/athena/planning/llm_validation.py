"""LLM-powered plan validation with extended reasoning.

Uses Claude's extended thinking capability for deep analysis of plan feasibility,
risk detection, and alternative plan generation.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Optional

from ..rag.llm_client import OllamaLLMClient

logger = logging.getLogger(__name__)


@dataclass
class PlanValidationInsight:
    """Deep insight from LLM reasoning about a plan."""

    category: str  # "risk", "assumption", "opportunity", "blocker"
    description: str
    severity: str  # "critical", "high", "medium", "low"
    confidence: float  # 0.0-1.0
    mitigation: Optional[str] = None  # How to address this insight


@dataclass
class EnhancedPlanValidationResult:
    """Result from LLM-powered plan validation."""

    plan_id: int
    is_feasible: bool
    overall_confidence: float  # 0.0-1.0
    estimated_complexity: int  # 1-10 scale
    estimated_duration_mins: int

    # Validation insights
    risks: list[PlanValidationInsight] = field(default_factory=list)
    assumptions: list[PlanValidationInsight] = field(default_factory=list)
    opportunities: list[PlanValidationInsight] = field(default_factory=list)
    blockers: list[PlanValidationInsight] = field(default_factory=list)

    # Recommendations
    recommendations: list[str] = field(default_factory=list)
    alternative_approaches: list[str] = field(default_factory=list)

    # Reasoning (what the LLM discovered)
    reasoning_summary: str = ""
    key_decisions: list[str] = field(default_factory=list)


class LLMPlanValidator:
    """Validate plans using LLM reasoning and extended thinking."""

    def __init__(self, llm_client: Optional[OllamaLLMClient] = None):
        """Initialize LLM plan validator.

        Args:
            llm_client: Optional LLM client for reasoning
        """
        self.llm_client = llm_client
        self._use_llm = llm_client is not None

        if self._use_llm:
            logger.info("LLM plan validator: Extended reasoning enabled")
        else:
            logger.info("LLM plan validator: Heuristic-based validation only")

    def validate_plan(
        self,
        plan_id: int,
        description: str,
        steps: list[str],
        dependencies: Optional[list[str]] = None,
        constraints: Optional[list[str]] = None,
        success_criteria: Optional[list[str]] = None,
    ) -> EnhancedPlanValidationResult:
        """Validate a plan using LLM reasoning.

        Args:
            plan_id: Plan identifier
            description: High-level plan description
            steps: List of sequential steps
            dependencies: External dependencies (libraries, services, etc.)
            constraints: Constraints (time, resources, etc.)
            success_criteria: Criteria for success

        Returns:
            Enhanced validation result with deep reasoning
        """
        if self._use_llm:
            return self._validate_with_llm(
                plan_id, description, steps, dependencies, constraints, success_criteria
            )
        else:
            return self._validate_heuristic(
                plan_id, description, steps, dependencies, constraints, success_criteria
            )

    def _validate_with_llm(
        self,
        plan_id: int,
        description: str,
        steps: list[str],
        dependencies: Optional[list[str]] = None,
        constraints: Optional[list[str]] = None,
        success_criteria: Optional[list[str]] = None,
    ) -> EnhancedPlanValidationResult:
        """Validate plan using LLM extended reasoning."""

        try:
            # Build plan context
            dependencies_str = "\n".join(f"- {d}" for d in (dependencies or []))
            constraints_str = "\n".join(f"- {c}" for c in (constraints or []))
            success_criteria_str = "\n".join(f"- {s}" for s in (success_criteria or []))

            steps_str = "\n".join(f"{i+1}. {step}" for i, step in enumerate(steps or []))

            prompt = f"""Deeply analyze this software development plan for feasibility, risks, and hidden assumptions.

PLAN DESCRIPTION:
{description}

STEPS:
{steps_str}

DEPENDENCIES:
{dependencies_str or "None specified"}

CONSTRAINTS:
{constraints_str or "None specified"}

SUCCESS CRITERIA:
{success_criteria_str or "None specified"}

Provide detailed reasoning about:
1. **Feasibility**: Can this plan realistically be executed?
2. **Hidden Risks**: What could go wrong that's not obvious?
3. **Assumptions**: What assumptions does this plan make?
4. **Blockers**: What would block execution?
5. **Opportunities**: What could be improved or leveraged?
6. **Complexity**: Rate overall complexity (1-10)
7. **Duration**: Estimate realistic duration in minutes
8. **Key Decisions**: What are the critical decision points?
9. **Alternative Approaches**: What other ways could achieve the goal?

Respond with JSON:
{{
    "is_feasible": true|false,
    "overall_confidence": 0.0-1.0,
    "estimated_complexity": 1-10,
    "estimated_duration_mins": number,
    "risks": [
        {{"description": "...", "severity": "critical|high|medium|low", "confidence": 0.0-1.0, "mitigation": "..."}}
    ],
    "assumptions": [
        {{"description": "...", "severity": "critical|high|medium|low", "confidence": 0.0-1.0}}
    ],
    "opportunities": [
        {{"description": "...", "severity": "low|medium|high", "confidence": 0.0-1.0}}
    ],
    "blockers": [
        {{"description": "...", "severity": "critical|high|medium|low", "mitigation": "..."}}
    ],
    "recommendations": ["...", "..."],
    "alternative_approaches": ["...", "..."],
    "reasoning_summary": "...",
    "key_decisions": ["...", "..."]
}}

Be thorough but practical. Focus on actionable insights."""

            result = self.llm_client.generate(prompt, max_tokens=1000)
            analysis = json.loads(result)

            # Build insights from analysis
            risks = [
                PlanValidationInsight(
                    category="risk",
                    description=r["description"],
                    severity=r.get("severity", "medium"),
                    confidence=float(r.get("confidence", 0.7)),
                    mitigation=r.get("mitigation"),
                )
                for r in analysis.get("risks", [])
            ]

            assumptions = [
                PlanValidationInsight(
                    category="assumption",
                    description=a["description"],
                    severity=a.get("severity", "medium"),
                    confidence=float(a.get("confidence", 0.7)),
                )
                for a in analysis.get("assumptions", [])
            ]

            opportunities = [
                PlanValidationInsight(
                    category="opportunity",
                    description=o["description"],
                    severity=o.get("severity", "low"),
                    confidence=float(o.get("confidence", 0.6)),
                )
                for o in analysis.get("opportunities", [])
            ]

            blockers = [
                PlanValidationInsight(
                    category="blocker",
                    description=b["description"],
                    severity=b.get("severity", "high"),
                    confidence=float(b.get("confidence", 0.8)),
                    mitigation=b.get("mitigation"),
                )
                for b in analysis.get("blockers", [])
            ]

            return EnhancedPlanValidationResult(
                plan_id=plan_id,
                is_feasible=bool(analysis.get("is_feasible", True)),
                overall_confidence=float(analysis.get("overall_confidence", 0.5)),
                estimated_complexity=int(analysis.get("estimated_complexity", 5)),
                estimated_duration_mins=int(analysis.get("estimated_duration_mins", 120)),
                risks=risks,
                assumptions=assumptions,
                opportunities=opportunities,
                blockers=blockers,
                recommendations=analysis.get("recommendations", []),
                alternative_approaches=analysis.get("alternative_approaches", []),
                reasoning_summary=analysis.get("reasoning_summary", ""),
                key_decisions=analysis.get("key_decisions", []),
            )

        except json.JSONDecodeError as e:
            logger.debug(f"Failed to parse LLM response: {e}")
            # Fall back to heuristic
            return self._validate_heuristic(
                plan_id, description, steps, dependencies, constraints, success_criteria
            )
        except Exception as e:
            logger.debug(f"LLM validation failed: {e}")
            # Fall back to heuristic
            return self._validate_heuristic(
                plan_id, description, steps, dependencies, constraints, success_criteria
            )

    def _validate_heuristic(
        self,
        plan_id: int,
        description: str,
        steps: list[str],
        dependencies: Optional[list[str]] = None,
        constraints: Optional[list[str]] = None,
        success_criteria: Optional[list[str]] = None,
    ) -> EnhancedPlanValidationResult:
        """Validate plan using heuristic rules (fallback)."""

        # Basic heuristic validation
        risks = []
        assumptions = []
        opportunities = []
        blockers = []

        # Check for common issues
        if not steps or len(steps) == 0:
            blockers.append(
                PlanValidationInsight(
                    category="blocker",
                    description="Plan has no steps defined",
                    severity="critical",
                    confidence=1.0,
                    mitigation="Define concrete steps",
                )
            )

        if len(steps) > 20:
            risks.append(
                PlanValidationInsight(
                    category="risk",
                    description="Plan has too many steps - complexity may be high",
                    severity="high",
                    confidence=0.8,
                    mitigation="Consider breaking into sub-plans",
                )
            )

        if dependencies and len(dependencies) > 5:
            assumptions.append(
                PlanValidationInsight(
                    category="assumption",
                    description="Plan depends on many external components",
                    severity="high",
                    confidence=0.7,
                )
            )

        if not success_criteria or len(success_criteria) == 0:
            assumptions.append(
                PlanValidationInsight(
                    category="assumption",
                    description="Success criteria not defined - how will completion be measured?",
                    severity="high",
                    confidence=0.9,
                )
            )

        # Estimate based on step count
        estimated_duration = max(30, len(steps) * 15)  # ~15 min per step
        estimated_complexity = min(10, max(1, len(steps) // 3))

        feasible = len(blockers) == 0
        confidence = 0.6  # Heuristic has lower confidence

        recommendations = []
        if not success_criteria or len(success_criteria) == 0:
            recommendations.append("Define clear success criteria")
        if not constraints or len(constraints) == 0:
            recommendations.append("Specify constraints (time, resources)")

        return EnhancedPlanValidationResult(
            plan_id=plan_id,
            is_feasible=feasible,
            overall_confidence=confidence,
            estimated_complexity=estimated_complexity,
            estimated_duration_mins=estimated_duration,
            risks=risks,
            assumptions=assumptions,
            opportunities=opportunities,
            blockers=blockers,
            recommendations=recommendations,
            alternative_approaches=[],
            reasoning_summary="Heuristic validation based on plan structure",
            key_decisions=[],
        )

    def generate_alternative_plans(
        self,
        plan_id: int,
        description: str,
        goal: str,
        constraints: Optional[list[str]] = None,
    ) -> list[str]:
        """Generate alternative approaches for achieving a goal.

        Args:
            plan_id: Original plan ID
            description: Original plan description
            goal: What the plan is trying to achieve
            constraints: Constraints to respect

        Returns:
            List of alternative approach descriptions
        """
        if not self._use_llm:
            return []

        try:
            constraints_str = "\n".join(f"- {c}" for c in (constraints or []))

            prompt = f"""Generate 3 creative alternative approaches to achieve this goal.

GOAL: {goal}

ORIGINAL APPROACH:
{description}

CONSTRAINTS:
{constraints_str or "None specified"}

For each alternative, provide:
1. A brief name/title
2. Key differences from original approach
3. Advantages
4. Disadvantages
5. Estimated effort (low/medium/high)

Respond as JSON:
{{
    "alternatives": [
        {{
            "name": "...",
            "description": "...",
            "advantages": ["...", "..."],
            "disadvantages": ["...", "..."],
            "effort": "low|medium|high"
        }}
    ]
}}"""

            result = self.llm_client.generate(prompt, max_tokens=500)
            analysis = json.loads(result)

            return [
                f"{alt.get('name', 'Alternative')}: {alt.get('description', '')}"
                for alt in analysis.get("alternatives", [])
            ]

        except Exception as e:
            logger.debug(f"Failed to generate alternatives: {e}")
            return []
