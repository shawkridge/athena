"""
Strategy-Aware Planner: Wraps Planner Agent with Executive Function Integration

Enhances the core Planner Agent with goal-aware decomposition by:
1. Accepting strategy hints from orchestration bridge
2. Generating strategy-specific execution steps
3. Adding Sequential Thinking reasoning to decomposition
4. Recording strategy outcomes for learning

This wrapper maintains backward compatibility with existing Planner Agent.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

from .agent_bridge import ExecutiveAgentBridge
from .models import StrategyType


class DecompositionStyle(str, Enum):
    """Decomposition style based on strategy."""

    HIERARCHICAL = "hierarchical"  # Many phases, strong planning
    ITERATIVE = "iterative"  # Few large phases, build iteratively
    SPIKE = "spike"  # Research/prototype dominant
    PARALLEL = "parallel"  # Many independent tasks
    SEQUENTIAL = "sequential"  # Strict ordering
    DEADLINE_DRIVEN = "deadline_driven"  # Minimize risk on deadline
    QUALITY_FIRST = "quality_first"  # Extra testing/review phases
    COLLABORATIVE = "collaborative"  # Include peer review
    EXPLORATORY = "exploratory"  # Multiple approaches in parallel


class StrategyAwarePlanner:
    """
    Wraps Planner Agent with strategy-aware step generation.

    Implements Sequential Thinking patterns for transparent reasoning.
    """

    # Strategy to decomposition style mapping
    STRATEGY_DECOMPOSITION_MAP = {
        StrategyType.TOP_DOWN: DecompositionStyle.HIERARCHICAL,
        StrategyType.BOTTOM_UP: DecompositionStyle.ITERATIVE,
        StrategyType.SPIKE: DecompositionStyle.SPIKE,
        StrategyType.PARALLEL: DecompositionStyle.PARALLEL,
        StrategyType.SEQUENTIAL: DecompositionStyle.SEQUENTIAL,
        StrategyType.DEADLINE_DRIVEN: DecompositionStyle.DEADLINE_DRIVEN,
        StrategyType.QUALITY_FIRST: DecompositionStyle.QUALITY_FIRST,
        StrategyType.COLLABORATION: DecompositionStyle.COLLABORATIVE,
        StrategyType.EXPERIMENTAL: DecompositionStyle.EXPLORATORY,
    }

    def __init__(self, planner_agent, orchestration_bridge):
        """
        Initialize strategy-aware planner wrapper.

        Args:
            planner_agent: Core PlannerAgent instance to wrap
            orchestration_bridge: OrchestrationBridge for goal context
        """
        self.planner = planner_agent
        self.orchestration = orchestration_bridge
        self.bridge = ExecutiveAgentBridge()

    async def decompose_with_strategy(
        self,
        task: Dict[str, Any],
        strategy: Optional[StrategyType] = None,
        reasoning: str = "",
        goal_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Decompose task with strategy awareness.

        Args:
            task: Task description dict with id, description, etc
            strategy: Strategy to guide decomposition (optional)
            reasoning: Reasoning behind strategy choice
            goal_id: Associated goal ID (optional)

        Returns:
            Execution plan from Planner Agent, enhanced with strategy context
        """
        # Call core Planner to get baseline plan (or generate fallback if planner is None)
        if self.planner:
            plan_result = await self.planner.decompose_task(task)
        else:
            # Fallback: Generate basic plan structure with proper step format
            plan_result = {
                "status": "success",
                "plan": {
                    "id": task.get("id"),
                    "description": task.get("description", ""),
                    "steps": [
                        {"description": "Analyze requirements", "estimated_duration_ms": 1800000},
                        {"description": "Plan approach", "estimated_duration_ms": 1800000},
                        {"description": "Implement solution", "estimated_duration_ms": 3600000},
                        {"description": "Verify and test", "estimated_duration_ms": 1800000},
                        {"description": "Document results", "estimated_duration_ms": 900000}
                    ],
                    "estimated_duration": 120
                }
            }

        if plan_result.get("status") != "success":
            return plan_result

        # Get the base plan
        plan_dict = plan_result.get("plan", {})

        # If strategy provided, enhance the plan
        if strategy:
            decomposition_style = self.STRATEGY_DECOMPOSITION_MAP.get(
                strategy,
                DecompositionStyle.HIERARCHICAL,
            )

            # Generate strategy-specific steps
            enhanced_steps = await self._enhance_steps_for_strategy(
                plan_dict.get("steps", []),
                decomposition_style,
                strategy,
            )

            # Update plan with enhanced steps
            plan_dict["steps"] = enhanced_steps
            plan_dict["strategy"] = strategy.value
            plan_dict["strategy_reasoning"] = reasoning
            plan_dict["decomposition_style"] = decomposition_style.value

            # Recalculate metrics with enhanced steps
            plan_dict["estimated_total_duration_ms"] = sum(
                s.get("estimated_duration_ms", 0) for s in enhanced_steps
            )

        return {
            "status": "success",
            "plan": plan_dict,
            "confidence": plan_result.get("confidence"),
            "strategy": strategy.value if strategy else None,
            "reasoning": reasoning,
        }

    async def _enhance_steps_for_strategy(
        self,
        base_steps: List[Dict],
        style: DecompositionStyle,
        strategy: StrategyType,
    ) -> List[Dict]:
        """
        Enhance base steps for specific decomposition style.

        Args:
            base_steps: Steps from core Planner (typically 4-phase: Plan/Implement/Test/Deploy)
            style: Decomposition style to apply
            strategy: Original strategy type

        Returns:
            Enhanced step list with strategy-specific modifications
        """
        if style == DecompositionStyle.HIERARCHICAL:
            return self._hierarchical_decomposition(base_steps)
        elif style == DecompositionStyle.ITERATIVE:
            return self._iterative_decomposition(base_steps)
        elif style == DecompositionStyle.SPIKE:
            return self._spike_decomposition(base_steps)
        elif style == DecompositionStyle.PARALLEL:
            return self._parallel_decomposition(base_steps)
        elif style == DecompositionStyle.SEQUENTIAL:
            return self._sequential_decomposition(base_steps)
        elif style == DecompositionStyle.DEADLINE_DRIVEN:
            return self._deadline_driven_decomposition(base_steps)
        elif style == DecompositionStyle.QUALITY_FIRST:
            return self._quality_first_decomposition(base_steps)
        elif style == DecompositionStyle.COLLABORATIVE:
            return self._collaborative_decomposition(base_steps)
        else:  # EXPLORATORY
            return self._exploratory_decomposition(base_steps)

    def _hierarchical_decomposition(self, steps: List[Dict]) -> List[Dict]:
        """
        TOP_DOWN strategy: Deep hierarchical planning.

        Adds detailed planning phase, breaks implementation into architectural blocks.
        """
        enhanced = []
        step_id = 1

        # Expand Plan phase (detailed architecture)
        enhanced.append(self._create_step(
            step_id, "Architecture & Design", 3600000, ["architecture_review"], "low", step_id - 1
        ))
        step_id += 1

        enhanced.append(self._create_step(
            step_id, "Design Review", 1800000, ["design_approved"], "low", step_id - 1
        ))
        step_id += 1

        # Original implementation
        for step in steps[1:3]:  # Keep Implement and Test
            step["id"] = step_id
            step["dependencies"] = [step_id - 1]
            enhanced.append(step)
            step_id += 1

        # Add validation
        enhanced.append(self._create_step(
            step_id, "Validation & Verification", 2400000, ["all_criteria_met"], "medium", step_id - 1
        ))
        step_id += 1

        # Deploy
        for step in steps[3:]:
            step["id"] = step_id
            step["dependencies"] = [step_id - 1]
            enhanced.append(step)
            step_id += 1

        return enhanced

    def _iterative_decomposition(self, steps: List[Dict]) -> List[Dict]:
        """
        BOTTOM_UP strategy: Iterative MVP approach.

        MVP in round 1, iterate with feedback.
        """
        enhanced = []
        step_id = 1

        # MVP loop
        for round_num in [1, 2]:
            if round_num == 1:
                desc_suffix = "MVP"
                duration_factor = 0.6
            else:
                desc_suffix = "Iteration 2"
                duration_factor = 0.4

            # Implement MVP
            enhanced.append(self._create_step(
                step_id,
                f"Implement {desc_suffix}",
                int(3600000 * duration_factor),
                [f"mvp_{round_num}_complete"],
                "medium",
                step_id - 1 if step_id > 1 else 0,
            ))
            step_id += 1

            # Quick test
            enhanced.append(self._create_step(
                step_id,
                f"Test {desc_suffix}",
                int(1200000 * duration_factor),
                [f"mvp_{round_num}_validated"],
                "low",
                step_id - 1,
            ))
            step_id += 1

            # Get feedback
            if round_num == 1:
                enhanced.append(self._create_step(
                    step_id,
                    "Gather Feedback",
                    900000,
                    ["feedback_collected"],
                    "low",
                    step_id - 1,
                ))
                step_id += 1

        # Deploy final
        enhanced.append(self._create_step(
            step_id, "Deploy", 600000, ["production_live"], "high", step_id - 1
        ))

        return enhanced

    def _spike_decomposition(self, steps: List[Dict]) -> List[Dict]:
        """
        SPIKE strategy: Research/prototype first.

        Dominant research phase before commitment.
        """
        return [
            self._create_step(1, "Research & Spike", 5400000, ["spike_complete"], "low", 0),
            self._create_step(2, "Spike Review & Decision", 1800000, ["decision_made"], "low", 1),
            self._create_step(3, "Implementation", 3600000, ["impl_done"], "medium", 2),
            self._create_step(4, "Testing", 1800000, ["tests_pass"], "low", 3),
            self._create_step(5, "Deploy", 600000, ["live"], "high", 4),
        ]

    def _parallel_decomposition(self, steps: List[Dict]) -> List[Dict]:
        """
        PARALLEL strategy: Maximize concurrent work.

        Split into independent workstreams.
        """
        return [
            self._create_step(1, "Planning & Work Breakdown", 1800000, ["plan_done"], "low", 0),
            # Parallel implementations
            self._create_step(2, "Implement Component A", 3600000, ["a_done"], "medium", 1),
            self._create_step(3, "Implement Component B", 3600000, ["b_done"], "medium", 1),
            self._create_step(4, "Implement Component C", 3600000, ["c_done"], "medium", 1),
            # Integration
            self._create_step(5, "Integration", 2400000, ["integrated"], "medium", [2, 3, 4]),
            # Testing
            self._create_step(6, "Test Integration", 1800000, ["tests_pass"], "low", 5),
            # Deploy
            self._create_step(7, "Deploy", 600000, ["live"], "high", 6),
        ]

    def _sequential_decomposition(self, steps: List[Dict]) -> List[Dict]:
        """
        SEQUENTIAL strategy: Strict one-after-another.

        No parallelization, simple linear progression.
        """
        # Default behavior - return as is (already sequential from planner)
        return steps

    def _deadline_driven_decomposition(self, steps: List[Dict]) -> List[Dict]:
        """
        DEADLINE_DRIVEN strategy: Risk minimization toward deadline.

        Front-load critical work, minimize risk as deadline approaches.
        """
        return [
            self._create_step(1, "Plan & Risk Assessment", 1800000, ["risks_identified"], "low", 0),
            self._create_step(2, "Implement Core (High Risk)", 4200000, ["core_done"], "high", 1),
            self._create_step(3, "Test Core", 2400000, ["core_tested"], "low", 2),
            self._create_step(4, "Implement Optional Features", 2400000, ["features_done"], "low", 1),
            self._create_step(5, "Final Testing & Hardening", 1800000, ["ready"], "medium", [3, 4]),
            self._create_step(6, "Deploy", 300000, ["live"], "high", 5),
        ]

    def _quality_first_decomposition(self, steps: List[Dict]) -> List[Dict]:
        """
        QUALITY_FIRST strategy: Extra review and testing.

        Double testing, code review, quality gates.
        """
        return [
            self._create_step(1, "Plan", 2400000, ["plan_done"], "low", 0),
            self._create_step(2, "Implement", 4200000, ["impl_done"], "medium", 1),
            self._create_step(3, "Code Review", 1800000, ["reviewed"], "low", 2),
            self._create_step(4, "Testing", 2400000, ["test1_done"], "low", 3),
            self._create_step(5, "Quality Gate 1", 1200000, ["qa1_passed"], "medium", 4),
            self._create_step(6, "Integration Testing", 1800000, ["integration_done"], "low", 5),
            self._create_step(7, "Quality Gate 2", 1200000, ["qa2_passed"], "medium", 6),
            self._create_step(8, "Deploy & Verify", 900000, ["live_verified"], "high", 7),
        ]

    def _collaborative_decomposition(self, steps: List[Dict]) -> List[Dict]:
        """
        COLLABORATION strategy: Include peer review and discussion.

        Add review and approval gates, team coordination.
        """
        return [
            self._create_step(1, "Plan & Team Sync", 1800000, ["team_aligned"], "low", 0),
            self._create_step(2, "Implementation", 3600000, ["impl_done"], "medium", 1),
            self._create_step(3, "Peer Review", 1800000, ["reviewed_approved"], "low", 2),
            self._create_step(4, "Testing", 2400000, ["tested"], "low", 3),
            self._create_step(5, "Team Validation", 1200000, ["validated"], "low", 4),
            self._create_step(6, "Deploy & Monitor", 900000, ["live_monitored"], "high", 5),
        ]

    def _exploratory_decomposition(self, steps: List[Dict]) -> List[Dict]:
        """
        EXPERIMENTAL strategy: Multiple approaches in parallel.

        Try multiple solutions, then pick best.
        """
        return [
            self._create_step(1, "Explore Approach A", 3600000, ["a_done"], "medium", 0),
            self._create_step(2, "Explore Approach B", 3600000, ["b_done"], "medium", 0),
            self._create_step(3, "Evaluate & Compare", 1800000, ["decision_made"], "low", [1, 2]),
            self._create_step(4, "Implement Chosen Approach", 2400000, ["impl_done"], "medium", 3),
            self._create_step(5, "Testing", 1800000, ["tested"], "low", 4),
            self._create_step(6, "Deploy", 600000, ["live"], "high", 5),
        ]

    @staticmethod
    def _create_step(
        step_id: int,
        description: str,
        duration_ms: int,
        success_criteria: List[str],
        risk_level: str,
        dependencies: int | List[int],
    ) -> Dict:
        """Helper to create a step dict."""
        if isinstance(dependencies, int):
            dependencies = [dependencies] if dependencies > 0 else []

        return {
            "id": step_id,
            "description": description,
            "estimated_duration_ms": duration_ms,
            "estimated_resources": {"cpu": 25, "memory": 256},
            "dependencies": dependencies,
            "risk_level": risk_level,
            "success_criteria": " & ".join(success_criteria),
            "preconditions": [],
            "salience": 0.7,
        }
