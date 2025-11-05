"""
Strategy Selector Skill - Phase 3 Executive Function with Extended Thinking.

Uses Anthropic extended thinking for deep analysis of task characteristics
and reasoning about which strategy best fits the problem.

This refactored version demonstrates Option B: Adding Claude's extended
thinking to skills for deeper reasoning + recording in ThinkingTraces.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

from .base_skill import BaseSkill, SkillResult
from memory_mcp.ai_coordination.thinking_traces import (
    ThinkingTrace, ReasoningStep, ReasoningPattern, ProblemType
)

logger = logging.getLogger(__name__)


class StrategySelectorExtendedSkill(BaseSkill):
    """Select decomposition strategy using extended thinking for deep analysis."""

    # 9 Decomposition strategies
    STRATEGIES = {
        "hierarchical": {
            "name": "HIERARCHICAL",
            "description": "Top-down architectural planning",
            "best_for": ["architecture", "complex", "design-heavy"],
        },
        "iterative": {
            "name": "ITERATIVE",
            "description": "MVP-first, incremental approach",
            "best_for": ["uncertain", "startup", "incremental"],
        },
        "spike": {
            "name": "SPIKE",
            "description": "Research/prototype dominant",
            "best_for": ["research", "unknown-tech", "poc"],
        },
        "parallel": {
            "name": "PARALLEL",
            "description": "Maximize concurrent work",
            "best_for": ["independent", "modular", "team-work"],
        },
        "sequential": {
            "name": "SEQUENTIAL",
            "description": "Strict linear ordering",
            "best_for": ["dependent", "ordered", "simple"],
        },
        "deadline_driven": {
            "name": "DEADLINE_DRIVEN",
            "description": "Time-critical, risk minimization",
            "best_for": ["urgent", "deadline", "critical"],
        },
        "quality_first": {
            "name": "QUALITY_FIRST",
            "description": "Extra review and testing phases",
            "best_for": ["security", "safety", "critical"],
        },
        "collaborative": {
            "name": "COLLABORATIVE",
            "description": "Team coordination focus",
            "best_for": ["team", "coordination", "distributed"],
        },
        "exploratory": {
            "name": "EXPLORATORY",
            "description": "Innovation and experimentation",
            "best_for": ["innovation", "r&d", "experimental"],
        },
    }

    def __init__(self):
        """Initialize skill."""
        super().__init__(
            skill_id="strategy-selector-extended",
            skill_name="Strategy Selector (Extended Thinking)"
        )
        self.client = None
        if ANTHROPIC_AVAILABLE:
            try:
                self.client = anthropic.Anthropic()
            except Exception as e:
                logger.warning(f"Failed to initialize Anthropic client: {e}")

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Select best strategy for task using extended thinking.

        Args:
            context: Execution context with task_description, goal_id, etc.

        Returns:
            Result with selected strategy, reasoning, and thinking_trace_id
        """
        try:
            task_description = context.get('task_description', '')
            memory_manager = context.get('memory_manager')
            session_id = context.get('session_id', 'unknown')

            if not task_description:
                return SkillResult(
                    status="skipped",
                    data={"reason": "No task description"}
                ).to_dict()

            start_time = datetime.now()
            reasoning_steps = []

            # ================================================================
            # STEP 1: Use Extended Thinking for Deep Analysis
            # ================================================================

            if not self.client:
                # Fallback to heuristic if API unavailable
                return await self._execute_heuristic(
                    task_description, context, reasoning_steps, start_time
                )

            logger.info(f"[StrategySelector] Analyzing task with extended thinking...")

            # Call Claude with extended thinking
            analysis, claude_reasoning = await self._analyze_with_thinking(
                task_description, session_id
            )

            # Capture: Analysis using extended thinking
            reasoning_steps.append(ReasoningStep(
                step_number=1,
                thought=claude_reasoning["analysis_summary"],
                confidence=0.95,  # Claude's thinking is high-confidence
                decision_point=False
            ))

            # ================================================================
            # STEP 2: Score Strategies Based on Analysis
            # ================================================================

            scores = self._score_strategies(analysis)
            reasoning_steps.append(ReasoningStep(
                step_number=2,
                thought=f"Evaluated 9 strategies against task characteristics: complexity={analysis['complexity']:.1f}, uncertainty={analysis['uncertainty']:.1%}, urgency={analysis['urgency']:.1%}",
                confidence=0.90,
                decision_point=False
            ))

            # ================================================================
            # STEP 3: Select Best Strategy
            # ================================================================

            selected = max(scores.items(), key=lambda x: x[1]['score'])
            strategy_key, strategy_score = selected

            reasoning_steps.append(ReasoningStep(
                step_number=3,
                thought=f"Selected {self.STRATEGIES[strategy_key]['name']} as optimal fit",
                confidence=strategy_score['score'] / 10.0,
                decision_point=True,
                decision_made=strategy_key,
                rationale=f"{strategy_score['reason']} (Score: {strategy_score['score']:.1f}/10)"
            ))

            # ================================================================
            # STEP 4: Record Thinking Trace
            # ================================================================

            thinking_trace = ThinkingTrace(
                problem=f"Select decomposition strategy for: {task_description[:100]}",
                problem_type=ProblemType.FEATURE_DESIGN,
                problem_complexity=int(min(10, max(1, analysis['complexity']))),
                reasoning_steps=reasoning_steps,
                conclusion=f"Recommended {self.STRATEGIES[strategy_key]['name']} strategy (confidence: {strategy_score['score']:.1f}/10). {strategy_score['reason']}",
                reasoning_quality=sum(s.confidence for s in reasoning_steps) / len(reasoning_steps),
                primary_pattern=ReasoningPattern.HEURISTIC,  # Scoring is heuristic-based
                secondary_patterns=[ReasoningPattern.DEDUCTIVE, ReasoningPattern.ANALOGY],  # Plus deductive and analogy from Claude
                session_id=session_id,
                duration_seconds=int((datetime.now() - start_time).total_seconds()),
                ai_model_used="claude-sonnet-4-5-extended"
            )

            # Store thinking trace in memory
            thinking_id = None
            if memory_manager:
                try:
                    thinking_id = await self._record_thinking_trace(
                        memory_manager, thinking_trace
                    )
                    logger.info(f"[StrategySelector] Recorded thinking trace: {thinking_id}")
                except Exception as e:
                    logger.error(f"Failed to record thinking trace: {e}")

            # ================================================================
            # STEP 5: Build Result
            # ================================================================

            alternatives = sorted(
                [(k, v) for k, v in scores.items() if k != strategy_key],
                key=lambda x: x[1]['score'],
                reverse=True
            )[:3]

            result = SkillResult(
                status="success",
                data={
                    "selected_strategy": strategy_key,
                    "strategy_name": self.STRATEGIES[strategy_key]['name'],
                    "confidence": strategy_score['score'],
                    "thinking_trace_id": thinking_id,
                    "reasoning": {
                        "decision": f"Selected {self.STRATEGIES[strategy_key]['name']}",
                        "why": strategy_score['reason'],
                        "task_analysis": analysis,
                        "extended_thinking_used": True,
                        "claude_insights": claude_reasoning.get("insights", []),
                    },
                    "alternatives": [
                        {
                            "strategy": k,
                            "name": self.STRATEGIES[k]['name'],
                            "score": v['score'],
                            "reason": v.get('reason', ''),
                        }
                        for k, v in alternatives
                    ],
                    "all_scores": {k: v['score'] for k, v in scores.items()},
                    "timestamp": datetime.now().isoformat(),
                },
                actions=[
                    f"Use {self.STRATEGIES[strategy_key]['name']} strategy for decomposition",
                    "Apply strategy-specific planning and execution approach",
                    "Monitor strategy effectiveness against task outcomes",
                    f"Track reasoning quality (confidence: {strategy_score['score']:.1f}/10)",
                ]
            )

            self._log_execution(result.to_dict())
            return result.to_dict()

        except Exception as e:
            logger.error(f"Error in strategy selection: {e}", exc_info=True)
            return SkillResult(
                status="failed",
                error=str(e)
            ).to_dict()

    async def _analyze_with_thinking(
        self, task_description: str, session_id: str
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Analyze task using Claude's extended thinking.

        Returns:
            (analysis_dict, claude_reasoning_dict)
        """
        if not self.client:
            raise ValueError("Anthropic client not initialized")

        prompt = f"""Analyze this task and provide deep reasoning about its characteristics:

TASK: {task_description}

Provide structured analysis of:
1. **Complexity**: Rate 1-10. Consider: number of components, interdependencies, unknown factors
2. **Uncertainty**: 0.0-1.0. How many unknowns vs known factors?
3. **Urgency**: 0.0-1.0. How time-critical is this?
4. **Risk Level**: 0.0-1.0. What's at stake?
5. **Dependencies**: 0.0-1.0. How dependent on external factors?
6. **Key Challenges**: What makes this difficult?
7. **Recommended Patterns**: Which decomposition patterns fit?

Respond with JSON only:
{{
    "complexity": <number 1-10>,
    "uncertainty": <number 0.0-1.0>,
    "urgency": <number 0.0-1.0>,
    "risk": <number 0.0-1.0>,
    "dependencies": <number 0.0-1.0>,
    "key_challenges": [<string>, ...],
    "recommended_patterns": [<string>, ...],
    "summary": "<one sentence summary>"
}}"""

        try:
            # Call Claude with extended thinking
            response = self.client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=2000,
                thinking={
                    "type": "enabled",
                    "budget_tokens": 5000  # Deep analysis budget
                },
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            # Extract thinking and text blocks
            thinking_content = ""
            text_content = ""

            for block in response.content:
                if block.type == "thinking":
                    thinking_content = block.thinking
                elif block.type == "text":
                    text_content = block.text

            # Parse JSON response
            analysis = json.loads(text_content)

            # Build reasoning summary from Claude's thinking
            claude_reasoning = {
                "analysis_summary": f"Extended thinking analysis: {analysis['summary']}",
                "thinking_depth": len(thinking_content.split('\n')),
                "key_challenges": analysis.get("key_challenges", []),
                "insights": [
                    f"Complexity: {analysis['complexity']}/10",
                    f"Uncertainty: {analysis['uncertainty']:.0%}",
                    f"Time pressure: {analysis['urgency']:.0%}",
                ]
            }

            return analysis, claude_reasoning

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude response: {e}")
            raise ValueError(f"Invalid JSON response from Claude: {text_content}")
        except Exception as e:
            logger.error(f"Extended thinking analysis failed: {e}")
            raise

    async def _execute_heuristic(
        self,
        task_description: str,
        context: Dict[str, Any],
        reasoning_steps: List[ReasoningStep],
        start_time: datetime
    ) -> Dict[str, Any]:
        """Fallback to heuristic analysis if extended thinking unavailable."""
        logger.warning("Extended thinking unavailable, falling back to heuristic")

        analysis = await self._analyze_task_heuristic(task_description)
        reasoning_steps.append(ReasoningStep(
            step_number=1,
            thought=f"Heuristic analysis: complexity={analysis['complexity']:.1f}, urgency={analysis['urgency']:.1%}",
            confidence=0.7,
            decision_point=False
        ))

        scores = self._score_strategies(analysis)
        selected = max(scores.items(), key=lambda x: x[1]['score'])

        thinking_trace = ThinkingTrace(
            problem=f"Select strategy for: {task_description[:100]}",
            problem_type=ProblemType.FEATURE_DESIGN,
            problem_complexity=int(analysis['complexity']),
            reasoning_steps=reasoning_steps,
            conclusion=f"Selected {selected[0]} (heuristic fallback)",
            reasoning_quality=0.7,
            primary_pattern=ReasoningPattern.HEURISTIC,
            session_id=context.get('session_id', 'unknown'),
            duration_seconds=int((datetime.now() - start_time).total_seconds()),
            ai_model_used="heuristic_fallback"
        )

        memory_manager = context.get('memory_manager')
        thinking_id = None
        if memory_manager:
            try:
                thinking_id = await self._record_thinking_trace(
                    memory_manager, thinking_trace
                )
            except Exception as e:
                logger.error(f"Failed to record thinking trace: {e}")

        return SkillResult(
            status="success",
            data={
                "selected_strategy": selected[0],
                "strategy_name": self.STRATEGIES[selected[0]]['name'],
                "confidence": selected[1]['score'],
                "thinking_trace_id": thinking_id,
                "extended_thinking_used": False,
                "fallback_reason": "Extended thinking unavailable",
            }
        ).to_dict()

    async def _analyze_task_heuristic(self, task_description: str) -> Dict[str, Any]:
        """Heuristic analysis fallback."""
        task_lower = task_description.lower()

        complexity_keywords = {
            "critical": 10, "complex": 8, "architecture": 9,
            "integration": 7, "module": 5, "component": 6, "simple": 2,
        }
        complexity = sum(
            v for k, v in complexity_keywords.items() if k in task_lower
        ) / max(1, len(complexity_keywords)) * 10

        uncertainty = 1.0 if any(
            k in task_lower for k in ["unknown", "unclear", "poc", "research"]
        ) else 0.3

        risk = 1.0 if any(
            k in task_lower for k in ["critical", "security", "safety", "production"]
        ) else 0.3

        dependencies = 1.0 if any(
            k in task_lower for k in ["depend", "block", "prerequisite"]
        ) else 0.2

        urgency = 1.0 if any(
            k in task_lower for k in ["urgent", "asap", "critical", "immediate"]
        ) else 0.3

        return {
            "complexity": min(10, max(1, complexity)),
            "uncertainty": uncertainty,
            "risk": risk,
            "dependencies": dependencies,
            "urgency": urgency,
        }

    def _score_strategies(self, analysis: Dict[str, Any]) -> Dict[str, Dict]:
        """Score all strategies against task characteristics."""
        scores = {}

        base_scores = {
            "hierarchical": 6.0,
            "iterative": 6.0,
            "spike": 6.0,
            "parallel": 6.0,
            "sequential": 5.0,
            "deadline_driven": 6.0,
            "quality_first": 6.0,
            "collaborative": 6.0,
            "exploratory": 6.0,
        }

        for key, base_score in base_scores.items():
            score = base_score
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

    async def _record_thinking_trace(
        self, memory_manager: Any, thinking_trace: ThinkingTrace
    ) -> Optional[int]:
        """Record thinking trace in memory."""
        try:
            # Call memory manager's MCP tool to record thinking
            # This assumes memory_manager has access to record_thinking MCP tool
            result = await memory_manager.call_tool(
                "record_reasoning",
                {
                    "problem": thinking_trace.problem,
                    "problem_type": thinking_trace.problem_type,
                    "problem_complexity": thinking_trace.problem_complexity,
                    "reasoning_steps": [
                        {
                            "step_number": s.step_number,
                            "thought": s.thought,
                            "confidence": s.confidence,
                            "decision_point": s.decision_point,
                            "decision_made": s.decision_made,
                            "rationale": s.rationale,
                        }
                        for s in thinking_trace.reasoning_steps
                    ],
                    "conclusion": thinking_trace.conclusion,
                    "reasoning_quality": thinking_trace.reasoning_quality,
                    "primary_pattern": thinking_trace.primary_pattern,
                    "secondary_patterns": thinking_trace.secondary_patterns,
                    "session_id": thinking_trace.session_id,
                    "duration_seconds": thinking_trace.duration_seconds,
                    "ai_model_used": thinking_trace.ai_model_used,
                }
            )
            return result.get("thinking_id")
        except Exception as e:
            logger.error(f"Failed to record thinking trace: {e}")
            return None


# Singleton instance
_instance = None


def get_skill():
    """Get or create skill instance."""
    global _instance
    if _instance is None:
        _instance = StrategySelectorExtendedSkill()
    return _instance
