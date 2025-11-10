"""Vibe prototyping system for testing ideas before full implementation."""

import logging
import asyncio
import json
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class PrototypePhase(Enum):
    """Phases of prototype lifecycle."""
    CONCEPTION = "conception"  # Idea and planning
    GENERATION = "generation"  # Prototype code/artifact generation
    EXECUTION = "execution"  # Running the prototype
    VALIDATION = "validation"  # Testing and feedback
    REFINEMENT = "refinement"  # Improvements based on feedback
    PROMOTION = "promotion"  # Converting to full implementation


class FeedbackType(Enum):
    """Types of feedback on prototype."""
    TECHNICAL = "technical"  # Technical feasibility
    UX = "ux"  # User experience
    PERFORMANCE = "performance"  # Performance characteristics
    COMPATIBILITY = "compatibility"  # Compatibility issues
    MAINTAINABILITY = "maintainability"  # Code quality/maintainability


@dataclass
class PrototypeFeedback:
    """Feedback on a prototype."""
    feedback_id: str
    type: FeedbackType
    severity: str  # "critical", "high", "medium", "low"
    description: str
    suggested_fix: Optional[str] = None
    affects_core: bool = False
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class PrototypeArtifact:
    """A prototype artifact (code, design, documentation)."""
    artifact_id: str
    type: str  # "code", "design", "documentation", "config"
    content: str
    language: Optional[str] = None  # For code artifacts
    size_bytes: int = 0


@dataclass
class Prototype:
    """A vibe prototype for testing an idea."""
    prototype_id: str
    idea_description: str
    phase: PrototypePhase
    artifacts: List[PrototypeArtifact] = field(default_factory=list)
    feedback: List[PrototypeFeedback] = field(default_factory=list)
    execution_results: Dict[str, Any] = field(default_factory=dict)
    success_criteria: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


class PrototypeEngine:
    """Engine for managing vibe prototypes."""

    def __init__(self):
        """Initialize prototype engine."""
        self.prototypes: Dict[str, Prototype] = {}
        self.prototype_counter = 0

    def create_prototype(
        self,
        idea: str,
        success_criteria: List[str] = None,
        metadata: Dict[str, Any] = None,
    ) -> Prototype:
        """Create a new prototype for an idea.

        Args:
            idea: Description of the idea to prototype
            success_criteria: List of success criteria for validation
            metadata: Additional metadata about the prototype

        Returns:
            Prototype object
        """
        self.prototype_counter += 1
        prototype_id = f"proto_{self.prototype_counter}"

        prototype = Prototype(
            prototype_id=prototype_id,
            idea_description=idea,
            phase=PrototypePhase.CONCEPTION,
            success_criteria=success_criteria or [],
            metadata=metadata or {},
        )

        self.prototypes[prototype_id] = prototype
        logger.info(f"Created prototype {prototype_id}: {idea}")

        return prototype

    def add_artifact(
        self,
        prototype_id: str,
        artifact_type: str,
        content: str,
        language: Optional[str] = None,
    ) -> PrototypeArtifact:
        """Add an artifact (code, design, etc.) to prototype.

        Args:
            prototype_id: ID of prototype
            artifact_type: Type of artifact ("code", "design", "documentation")
            content: Content of the artifact
            language: Programming language (for code artifacts)

        Returns:
            PrototypeArtifact object
        """
        if prototype_id not in self.prototypes:
            raise ValueError(f"Prototype {prototype_id} not found")

        prototype = self.prototypes[prototype_id]
        artifact_id = f"{prototype_id}_artifact_{len(prototype.artifacts) + 1}"

        artifact = PrototypeArtifact(
            artifact_id=artifact_id,
            type=artifact_type,
            content=content,
            language=language,
            size_bytes=len(content.encode("utf-8")),
        )

        prototype.artifacts.append(artifact)
        prototype.phase = PrototypePhase.GENERATION
        prototype.updated_at = datetime.utcnow().isoformat()

        logger.debug(f"Added {artifact_type} artifact to {prototype_id}")

        return artifact

    async def execute_prototype(
        self,
        prototype_id: str,
        execution_context: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Execute a prototype to test the idea.

        Args:
            prototype_id: ID of prototype
            execution_context: Context for execution (env vars, inputs, etc.)

        Returns:
            Execution results
        """
        if prototype_id not in self.prototypes:
            raise ValueError(f"Prototype {prototype_id} not found")

        prototype = self.prototypes[prototype_id]
        prototype.phase = PrototypePhase.EXECUTION

        logger.info(f"Executing prototype {prototype_id}")

        try:
            # Simulate prototype execution
            results = {
                "prototype_id": prototype_id,
                "status": "success",
                "outputs": {},
                "metrics": {},
                "duration_seconds": 0,
                "errors": [],
            }

            # Validate against success criteria
            success_count = 0
            for criteria in prototype.success_criteria:
                # Simulate criteria validation (would actually run tests)
                validation_passed = await self._validate_criterion(
                    prototype, criteria, execution_context
                )
                if validation_passed:
                    success_count += 1
                else:
                    results["errors"].append(f"Criteria not met: {criteria}")

            results["success_rate"] = success_count / max(
                len(prototype.success_criteria), 1
            )
            prototype.execution_results = results
            prototype.phase = PrototypePhase.VALIDATION

            return results

        except Exception as e:
            logger.error(f"Error executing prototype {prototype_id}: {e}")
            return {
                "prototype_id": prototype_id,
                "status": "error",
                "error": str(e),
            }

    async def validate_prototype(
        self,
        prototype_id: str,
        check_technical: bool = True,
        check_ux: bool = True,
        check_performance: bool = False,
    ) -> List[PrototypeFeedback]:
        """Validate prototype and collect feedback.

        Args:
            prototype_id: ID of prototype
            check_technical: Check technical feasibility
            check_ux: Check user experience
            check_performance: Check performance

        Returns:
            List of feedback items
        """
        if prototype_id not in self.prototypes:
            raise ValueError(f"Prototype {prototype_id} not found")

        prototype = self.prototypes[prototype_id]
        feedback_list = []

        # Technical validation
        if check_technical:
            tech_feedback = await self._validate_technical(prototype)
            feedback_list.extend(tech_feedback)

        # UX validation
        if check_ux:
            ux_feedback = await self._validate_ux(prototype)
            feedback_list.extend(ux_feedback)

        # Performance validation
        if check_performance:
            perf_feedback = await self._validate_performance(prototype)
            feedback_list.extend(perf_feedback)

        prototype.feedback = feedback_list
        prototype.phase = PrototypePhase.REFINEMENT

        # Calculate overall quality score
        critical_issues = len([f for f in feedback_list if f.severity == "critical"])
        quality_score = 1.0 - (critical_issues * 0.3)

        logger.info(
            f"Validation complete for {prototype_id}: "
            f"{len(feedback_list)} issues, quality score {quality_score:.2f}"
        )

        return feedback_list

    async def refine_prototype(
        self,
        prototype_id: str,
        improvements: List[str],
    ) -> Prototype:
        """Refine prototype based on feedback.

        Args:
            prototype_id: ID of prototype
            improvements: List of improvements to apply

        Returns:
            Updated prototype
        """
        if prototype_id not in self.prototypes:
            raise ValueError(f"Prototype {prototype_id} not found")

        prototype = self.prototypes[prototype_id]
        prototype.phase = PrototypePhase.REFINEMENT
        prototype.updated_at = datetime.utcnow().isoformat()

        logger.info(
            f"Refining prototype {prototype_id} with {len(improvements)} improvements"
        )

        # Store refinements in metadata
        if "refinements" not in prototype.metadata:
            prototype.metadata["refinements"] = []

        prototype.metadata["refinements"].extend(improvements)

        return prototype

    async def promote_to_implementation(
        self,
        prototype_id: str,
        implementation_plan: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Promote prototype to full implementation.

        Args:
            prototype_id: ID of prototype
            implementation_plan: Plan for full implementation

        Returns:
            Promotion result
        """
        if prototype_id not in self.prototypes:
            raise ValueError(f"Prototype {prototype_id} not found")

        prototype = self.prototypes[prototype_id]

        # Check if ready to promote
        critical_issues = [f for f in prototype.feedback if f.severity == "critical"]
        if critical_issues:
            return {
                "status": "blocked",
                "reason": f"Cannot promote: {len(critical_issues)} critical issues",
                "issues": [f.description for f in critical_issues],
            }

        prototype.phase = PrototypePhase.PROMOTION
        prototype.metadata["promotion_time"] = datetime.utcnow().isoformat()
        prototype.metadata["implementation_plan"] = implementation_plan

        logger.info(f"Promoted prototype {prototype_id} to implementation phase")

        return {
            "status": "promoted",
            "prototype_id": prototype_id,
            "plan": implementation_plan,
            "artifacts": [a.artifact_id for a in prototype.artifacts],
        }

    async def _validate_criterion(
        self,
        prototype: Prototype,
        criterion: str,
        context: Dict[str, Any] = None,
    ) -> bool:
        """Validate a single success criterion."""
        # Simulate criterion validation
        await asyncio.sleep(0.01)
        # Mock: assume success if criterion contains positive keywords
        return any(
            word in criterion.lower()
            for word in ["works", "success", "valid", "correct", "ok"]
        )

    async def _validate_technical(self, prototype: Prototype) -> List[PrototypeFeedback]:
        """Validate technical feasibility."""
        feedback = []

        # Check code artifacts
        for artifact in prototype.artifacts:
            if artifact.type == "code":
                # Check for common issues
                if "TODO" in artifact.content or "FIXME" in artifact.content:
                    feedback.append(
                        PrototypeFeedback(
                            feedback_id=f"{artifact.artifact_id}_todo",
                            type=FeedbackType.TECHNICAL,
                            severity="medium",
                            description="Code contains TODO/FIXME comments",
                            affects_core=False,
                        )
                    )

                if artifact.size_bytes > 1000:
                    feedback.append(
                        PrototypeFeedback(
                            feedback_id=f"{artifact.artifact_id}_size",
                            type=FeedbackType.TECHNICAL,
                            severity="low",
                            description=f"Code artifact is large ({artifact.size_bytes} bytes)",
                            affects_core=False,
                        )
                    )

        return feedback

    async def _validate_ux(self, prototype: Prototype) -> List[PrototypeFeedback]:
        """Validate user experience."""
        feedback = []

        # Check if prototype has documentation
        has_docs = any(a.type == "documentation" for a in prototype.artifacts)
        if not has_docs:
            feedback.append(
                PrototypeFeedback(
                    feedback_id="no_docs",
                    type=FeedbackType.UX,
                    severity="medium",
                    description="Prototype lacks documentation for users",
                    affects_core=True,
                )
            )

        return feedback

    async def _validate_performance(self, prototype: Prototype) -> List[PrototypeFeedback]:
        """Validate performance."""
        feedback = []

        # Check execution results
        results = prototype.execution_results
        if results.get("success_rate", 0) < 0.7:
            feedback.append(
                PrototypeFeedback(
                    feedback_id="low_success",
                    type=FeedbackType.PERFORMANCE,
                    severity="high",
                    description="Success rate below 70%",
                    affects_core=True,
                )
            )

        return feedback

    def get_prototype(self, prototype_id: str) -> Optional[Prototype]:
        """Get prototype by ID."""
        return self.prototypes.get(prototype_id)

    def list_prototypes(self, phase: PrototypePhase = None) -> List[Prototype]:
        """List all prototypes, optionally filtered by phase."""
        if phase:
            return [p for p in self.prototypes.values() if p.phase == phase]
        return list(self.prototypes.values())


# Singleton instance
_engine_instance: Optional[PrototypeEngine] = None


def get_prototype_engine() -> PrototypeEngine:
    """Get or create prototype engine."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = PrototypeEngine()
    return _engine_instance
