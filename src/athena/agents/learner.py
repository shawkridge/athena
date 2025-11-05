"""
Learner Agent

Extracts patterns from executions and recommends improvements.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from .base import AgentType, BaseAgent


class ExecutionPattern(BaseModel):
    """Pattern extracted from execution history"""
    id: str
    name: str
    description: str
    frequency: int  # How many times observed
    confidence: float  # 0.0-1.0
    impact: str  # low, medium, high
    examples: List[int] = Field(default_factory=list)  # Execution IDs


class Improvement(BaseModel):
    """Recommended improvement"""
    id: str
    title: str
    description: str
    rationale: str
    estimated_improvement_percent: float
    confidence: float
    priority: str  # low, medium, high, critical


class LearningOutcome(BaseModel):
    """Result of learning analysis"""
    execution_id: int
    patterns_found: List[ExecutionPattern] = Field(default_factory=list)
    improvements: List[Improvement] = Field(default_factory=list)
    accuracy_improvement: float = 0.0
    quality_improvement: float = 0.0
    confidence_change: float = 0.0


class LearnerAgent(BaseAgent):
    """
    Learner Agent: Extracts patterns and recommends improvements.

    Responsibilities:
    - Analyze execution outcomes
    - Extract successful patterns
    - Identify failure modes
    - Recommend strategy improvements
    - Track learning effectiveness
    """

    def __init__(self, db_path: str):
        """
        Initialize Learner agent.

        Args:
            db_path: Path to memory database
        """
        super().__init__(AgentType.LEARNER, db_path)
        self.execution_history: List[Dict[str, Any]] = []
        self.learned_patterns: List[ExecutionPattern] = []
        self.improvement_history: List[Improvement] = []

    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle incoming messages.

        Args:
            message: Message payload

        Returns:
            Response payload
        """
        try:
            if message.get("action") == "learn_from_execution":
                return await self.learn_from_execution(
                    message.get("execution_record", {})
                )
            elif message.get("action") == "get_patterns":
                return await self.get_patterns(
                    message.get("domain")
                )
            elif message.get("action") == "get_improvements":
                return await self.get_improvements(
                    message.get("domain")
                )
            elif message.get("action") == "analyze_accuracy":
                return await self.analyze_prediction_accuracy()
            else:
                return {
                    "status": "error",
                    "error": f"Unknown action: {message.get('action')}"
                }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

    async def make_decision(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make learning decision based on execution record.

        Args:
            context: Decision context

        Returns:
            Decision output with confidence score
        """
        execution_record = context.get("execution_record", {})
        return await self.learn_from_execution(execution_record)

    async def learn_from_execution(self, execution_record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract learnings from completed execution.

        Args:
            execution_record: Complete execution record

        Returns:
            Learning outcome with patterns and improvements
        """
        start_time = datetime.now()

        try:
            execution_id = execution_record.get("execution_id", 0)

            # 1. Store execution in history
            self.execution_history.append(execution_record)

            # 2. Extract patterns
            patterns = await self._extract_patterns(execution_record)

            # 3. Identify improvements
            improvements = await self._identify_improvements(execution_record, patterns)

            # 4. Calculate metrics
            accuracy_improvement = await self._compute_accuracy_improvement(execution_record)
            quality_improvement = await self._compute_quality_improvement(execution_record)
            confidence_change = await self._compute_confidence_change(execution_record)

            # 5. Create learning outcome
            outcome = LearningOutcome(
                execution_id=execution_id,
                patterns_found=patterns,
                improvements=improvements,
                accuracy_improvement=accuracy_improvement,
                quality_improvement=quality_improvement,
                confidence_change=confidence_change
            )

            # Record metrics
            decision_time = (datetime.now() - start_time).total_seconds() * 1000
            success = len(patterns) > 0
            confidence = 0.8 if len(patterns) > 0 else 0.5
            self.record_decision(success, decision_time, confidence)

            return {
                "status": "success",
                "learning_outcome": {
                    "execution_id": outcome.execution_id,
                    "patterns_found": [p.dict() for p in outcome.patterns_found],
                    "improvements": [i.dict() for i in outcome.improvements],
                    "accuracy_improvement": outcome.accuracy_improvement,
                    "quality_improvement": outcome.quality_improvement,
                    "confidence_change": outcome.confidence_change
                }
            }

        except Exception as e:
            decision_time = (datetime.now() - start_time).total_seconds() * 1000
            self.record_decision(False, decision_time, 0.0)

            return {
                "status": "error",
                "error": str(e)
            }

    async def get_patterns(self, domain: Optional[str] = None) -> Dict[str, Any]:
        """
        Get learned patterns, optionally filtered by domain.

        Args:
            domain: Optional domain filter

        Returns:
            List of patterns
        """
        patterns = self.learned_patterns

        if domain:
            patterns = [p for p in patterns if domain.lower() in p.name.lower()]

        return {
            "status": "success",
            "patterns": [p.dict() for p in patterns],
            "pattern_count": len(patterns)
        }

    async def get_improvements(self, domain: Optional[str] = None) -> Dict[str, Any]:
        """
        Get recommended improvements.

        Args:
            domain: Optional domain filter

        Returns:
            List of improvement recommendations
        """
        improvements = self.improvement_history

        if domain:
            improvements = [i for i in improvements if domain.lower() in i.title.lower()]

        return {
            "status": "success",
            "improvements": [i.dict() for i in improvements],
            "improvement_count": len(improvements)
        }

    async def analyze_prediction_accuracy(self) -> Dict[str, Any]:
        """
        Analyze accuracy of predictions across all executions.

        Returns:
            Accuracy metrics
        """
        if not self.execution_history:
            return {
                "status": "success",
                "message": "No execution history yet"
            }

        predictions = []
        errors = []

        for record in self.execution_history:
            predicted = record.get("estimated_total_duration_ms", 0)
            actual = record.get("actual_duration_ms", 0)

            if predicted > 0 and actual > 0:
                error = abs(actual - predicted) / predicted
                errors.append(error)
                predictions.append({
                    "predicted": predicted,
                    "actual": actual,
                    "error": error
                })

        if not errors:
            return {
                "status": "success",
                "message": "No predictions to analyze"
            }

        avg_error = sum(errors) / len(errors)
        max_error = max(errors)
        min_error = min(errors)

        return {
            "status": "success",
            "accuracy_metrics": {
                "average_error_percent": avg_error * 100,
                "max_error_percent": max_error * 100,
                "min_error_percent": min_error * 100,
                "accuracy_percent": max(0, (1 - avg_error) * 100),
                "predictions_analyzed": len(predictions)
            },
            "predictions": predictions
        }

    async def _extract_patterns(self, execution_record: Dict[str, Any]) -> List[ExecutionPattern]:
        """
        Extract patterns from execution record.

        Args:
            execution_record: Execution to analyze

        Returns:
            List of detected patterns
        """
        patterns = []
        execution_id = execution_record.get("execution_id", 0)

        # Pattern 1: Task complexity
        steps = execution_record.get("steps_completed", [])
        if len(steps) >= 4:
            pattern = ExecutionPattern(
                id=f"multi_step_task_{execution_id}",
                name="Multi-step Task Pattern",
                description="Tasks with 4+ steps have sequential dependencies",
                frequency=len(steps),
                confidence=0.85,
                impact="high",
                examples=[execution_id]
            )
            patterns.append(pattern)
            self.learned_patterns.append(pattern)

        # Pattern 2: Execution success
        status = execution_record.get("status", "")
        if status == "completed":
            pattern = ExecutionPattern(
                id=f"successful_execution_{execution_id}",
                name="Successful Execution Pattern",
                description="Execution completed all steps",
                frequency=1,
                confidence=0.95,
                impact="high",
                examples=[execution_id]
            )
            patterns.append(pattern)

        # Pattern 3: Duration patterns
        estimated = execution_record.get("estimated_total_duration_ms", 0)
        actual = execution_record.get("actual_duration_ms", 0)

        if actual > 0 and estimated > 0:
            ratio = actual / estimated
            if ratio > 1.3:
                pattern = ExecutionPattern(
                    id=f"underestimated_{execution_id}",
                    name="Underestimation Pattern",
                    description=f"Tasks of this type take {ratio:.1f}x longer than estimated",
                    frequency=1,
                    confidence=0.75,
                    impact="medium",
                    examples=[execution_id]
                )
                patterns.append(pattern)

        return patterns

    async def _identify_improvements(self, execution_record: Dict[str, Any],
                                    patterns: List[ExecutionPattern]) -> List[Improvement]:
        """
        Identify improvements based on patterns.

        Args:
            execution_record: Execution record
            patterns: Extracted patterns

        Returns:
            List of improvement recommendations
        """
        improvements = []

        # Improvement 1: Parallelization
        steps = execution_record.get("steps_completed", [])
        if len(steps) >= 4:
            improvement = Improvement(
                id=f"parallelize_steps_{execution_record.get('execution_id', 0)}",
                title="Parallelize Independent Steps",
                description="Steps 2 and 3 have no dependencies and could run in parallel",
                rationale="Independent steps can be executed concurrently to reduce total duration",
                estimated_improvement_percent=20.0,
                confidence=0.7,
                priority="medium"
            )
            improvements.append(improvement)
            self.improvement_history.append(improvement)

        # Improvement 2: Pre-planning
        if any("underestimated" in p.name for p in patterns):
            improvement = Improvement(
                id=f"improve_estimation_{execution_record.get('execution_id', 0)}",
                title="Improve Duration Estimation",
                description="Use historical data to calibrate estimates for this task type",
                rationale="Underestimation leads to poor resource planning",
                estimated_improvement_percent=15.0,
                confidence=0.8,
                priority="high"
            )
            improvements.append(improvement)
            self.improvement_history.append(improvement)

        # Improvement 3: Error handling
        errors = execution_record.get("errors", [])
        if len(errors) > 0:
            improvement = Improvement(
                id=f"improve_error_handling_{execution_record.get('execution_id', 0)}",
                title="Enhance Error Recovery",
                description="Add contingency plans for common failure modes",
                rationale="Errors reduce execution reliability and require manual recovery",
                estimated_improvement_percent=25.0,
                confidence=0.7,
                priority="high"
            )
            improvements.append(improvement)
            self.improvement_history.append(improvement)

        return improvements

    async def _compute_accuracy_improvement(self, execution_record: Dict[str, Any]) -> float:
        """
        Compute prediction accuracy improvement.

        Args:
            execution_record: Execution record

        Returns:
            Accuracy improvement percent (-100 to +100)
        """
        if len(self.execution_history) < 2:
            return 0.0

        # Compare latest with previous
        latest = self.execution_history[-1]
        previous = self.execution_history[-2]

        latest_error = abs(
            (latest.get("actual_duration_ms", 0) - latest.get("estimated_total_duration_ms", 1)) /
            max(1, latest.get("estimated_total_duration_ms", 1))
        )

        previous_error = abs(
            (previous.get("actual_duration_ms", 0) - previous.get("estimated_total_duration_ms", 1)) /
            max(1, previous.get("estimated_total_duration_ms", 1))
        )

        improvement = (previous_error - latest_error) * 100
        return min(100, max(-100, improvement))

    async def _compute_quality_improvement(self, execution_record: Dict[str, Any]) -> float:
        """
        Compute quality improvement.

        Args:
            execution_record: Execution record

        Returns:
            Quality improvement percent (0-100)
        """
        # Check if execution was successful
        status = execution_record.get("status", "")
        errors = len(execution_record.get("errors", []))

        if status == "completed" and errors == 0:
            return 10.0  # Each perfect execution improves quality baseline

        return 0.0

    async def _compute_confidence_change(self, execution_record: Dict[str, Any]) -> float:
        """
        Compute change in system confidence.

        Args:
            execution_record: Execution record

        Returns:
            Confidence change (-1.0 to +1.0)
        """
        # Successful execution increases confidence
        status = execution_record.get("status", "")

        if status == "completed":
            return 0.05  # +5% confidence

        return -0.1  # -10% confidence on failure
