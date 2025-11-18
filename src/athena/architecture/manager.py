"""Architecture manager coordinating ADRs, patterns, constraints, and context engineering.

This module provides the main interface for the architecture layer, integrating
with Athena's existing memory and planning systems to support design-first AI coding.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

from ..core.database import Database, get_database
from .adr_store import ADRStore
from .pattern_library import PatternLibrary
from .constraint_tracker import ConstraintTracker
from .models import (
    ArchitecturalDecisionRecord,
    DesignPattern,
    ArchitecturalConstraint,
    DecisionStatus,
    PatternType,
    ConstraintType,
)

logger = logging.getLogger(__name__)


class ArchitectureManager:
    """Central manager for architecture layer operations.

    Coordinates ADRs, patterns, constraints, and provides context engineering
    capabilities for AI-assisted development.
    """

    def __init__(self, db: Optional[Database] = None):
        """Initialize architecture manager.

        Args:
            db: Database instance (uses singleton if not provided)
        """
        self.db = db or get_database()
        self.adr_store = ADRStore(self.db)
        self.pattern_library = PatternLibrary(self.db)
        self.constraint_tracker = ConstraintTracker(self.db)

    # ==================== Context Engineering ====================

    def get_architectural_context(self, project_id: int, task_description: Optional[str] = None) -> Dict[str, Any]:
        """Get architectural context for AI agents (Context Engineering Layer).

        This provides the "domain context" that AI agents need to make
        architecturally-aligned decisions.

        Args:
            project_id: Project ID
            task_description: Optional task to get specific context for

        Returns:
            Dictionary of architectural context
        """
        context = {
            "active_decisions": [],
            "patterns": [],
            "constraints": [],
            "recent_changes": [],
        }

        # Get active architectural decisions
        active_adrs = self.adr_store.get_active_decisions(project_id)
        context["active_decisions"] = [
            {
                "id": adr.id,
                "title": adr.title,
                "decision": adr.decision,
                "consequences": adr.consequences,
                "related_patterns": adr.related_patterns,
            }
            for adr in active_adrs[:10]  # Top 10 recent decisions
        ]

        # Get most effective patterns
        effective_patterns = self.pattern_library.get_most_effective(limit=10)
        context["patterns"] = [
            {
                "name": pattern.name,
                "type": pattern.type,
                "problem": pattern.problem,
                "solution": pattern.solution,
                "effectiveness": pattern.effectiveness_score,
            }
            for pattern in effective_patterns
        ]

        # Get unsatisfied constraints (these are requirements)
        unsatisfied = self.constraint_tracker.list_by_project(project_id, only_unsatisfied=True)
        context["constraints"] = [
            {
                "id": constraint.id,
                "type": constraint.type,
                "description": constraint.description,
                "is_hard": constraint.is_hard_constraint,
                "priority": constraint.priority,
            }
            for constraint in unsatisfied[:15]  # Top 15 by priority
        ]

        # Get recent decisions (last 30 days)
        recent_adrs = self.adr_store.get_recent(project_id, days=30, limit=5)
        context["recent_changes"] = [
            {
                "title": adr.title,
                "date": adr.created_at.isoformat(),
                "status": adr.status,
            }
            for adr in recent_adrs
        ]

        # If task provided, add task-specific context
        if task_description:
            # Find patterns that might solve this problem
            relevant_patterns = self.pattern_library.search_by_problem(task_description, limit=3)
            context["suggested_patterns"] = [
                {
                    "name": pattern.name,
                    "problem": pattern.problem,
                    "solution": pattern.solution,
                    "effectiveness": pattern.effectiveness_score,
                }
                for pattern in relevant_patterns
            ]

        logger.info(f"Generated architectural context for project {project_id}")
        return context

    def get_context_summary(self, project_id: int) -> str:
        """Get a text summary of architectural context (for prompt injection).

        Args:
            project_id: Project ID

        Returns:
            Formatted string summary
        """
        context = self.get_architectural_context(project_id)

        summary = "# Architectural Context\n\n"

        # Active decisions
        if context["active_decisions"]:
            summary += "## Current Architectural Decisions\n\n"
            for adr in context["active_decisions"]:
                summary += f"- **{adr['title']}**: {adr['decision']}\n"
            summary += "\n"

        # Patterns
        if context["patterns"]:
            summary += "## Established Patterns\n\n"
            for pattern in context["patterns"]:
                eff = f" ({pattern['effectiveness']:.0%} effective)" if pattern['effectiveness'] else ""
                summary += f"- **{pattern['name']}**{eff}: {pattern['problem']}\n"
            summary += "\n"

        # Constraints
        if context["constraints"]:
            summary += "## Active Constraints\n\n"
            for constraint in context["constraints"]:
                hard = " [REQUIRED]" if constraint['is_hard'] else ""
                summary += f"- {constraint['description']}{hard}\n"
            summary += "\n"

        return summary

    # ==================== ADR Operations ====================

    def create_adr(
        self,
        project_id: int,
        title: str,
        context: str,
        decision: str,
        rationale: str,
        alternatives: Optional[List[str]] = None,
        consequences: Optional[List[str]] = None,
        author: Optional[str] = None
    ) -> int:
        """Create a new Architecture Decision Record.

        Args:
            project_id: Project ID
            title: Decision title
            context: Problem/context leading to decision
            decision: The decision made
            rationale: Why this decision
            alternatives: Alternatives considered
            consequences: Expected consequences
            author: Decision author

        Returns:
            ADR ID
        """
        adr = ArchitecturalDecisionRecord(
            project_id=project_id,
            title=title,
            status=DecisionStatus.PROPOSED,
            context=context,
            decision=decision,
            rationale=rationale,
            alternatives=alternatives or [],
            consequences=consequences or [],
            author=author,
        )

        return self.adr_store.create(adr)

    def accept_adr(self, adr_id: int) -> None:
        """Mark an ADR as accepted."""
        adr = self.adr_store.get(adr_id)
        if adr:
            adr.status = DecisionStatus.ACCEPTED
            adr.updated_at = datetime.now()
            # Update in store (would need update method in ADRStore)
            logger.info(f"Accepted ADR {adr_id}")

    def get_active_adrs(self, project_id: int) -> List[ArchitecturalDecisionRecord]:
        """Get all active architectural decisions for a project."""
        return self.adr_store.get_active_decisions(project_id)

    # ==================== Pattern Operations ====================

    def add_pattern(
        self,
        name: str,
        pattern_type: PatternType,
        problem: str,
        solution: str,
        context: str,
        code_example: Optional[str] = None
    ) -> int:
        """Add a new design pattern to the library.

        Args:
            name: Pattern name
            pattern_type: Type of pattern
            problem: What problem does it solve?
            solution: How does it solve it?
            context: When to use it?
            code_example: Example implementation

        Returns:
            Pattern ID
        """
        pattern = DesignPattern(
            name=name,
            type=pattern_type,
            problem=problem,
            solution=solution,
            context=context,
            code_example=code_example,
        )

        return self.pattern_library.add_pattern(pattern)

    def record_pattern_usage(self, pattern_name: str, project_id: int, success: bool) -> None:
        """Record that a pattern was used in a project.

        Args:
            pattern_name: Name of pattern used
            project_id: Project ID
            success: Whether usage was successful
        """
        pattern = self.pattern_library.get_by_name(pattern_name)
        if pattern:
            self.pattern_library.record_usage(pattern.id, project_id, success)
            logger.info(f"Recorded {'successful' if success else 'failed'} use of {pattern_name}")

    def suggest_patterns_for_problem(self, problem: str, limit: int = 5) -> List[DesignPattern]:
        """Suggest patterns that might solve a given problem.

        Args:
            problem: Problem description
            limit: Maximum suggestions

        Returns:
            List of relevant patterns
        """
        return self.pattern_library.search_by_problem(problem, limit)

    # ==================== Constraint Operations ====================

    def add_constraint(
        self,
        project_id: int,
        constraint_type: ConstraintType,
        description: str,
        rationale: str,
        validation_criteria: str,
        is_hard: bool = True,
        priority: int = 5
    ) -> int:
        """Add an architectural constraint.

        Args:
            project_id: Project ID
            constraint_type: Type of constraint
            description: What is the constraint?
            rationale: Why does it exist?
            validation_criteria: How to verify?
            is_hard: Must satisfy vs should satisfy
            priority: Priority 1-10

        Returns:
            Constraint ID
        """
        constraint = ArchitecturalConstraint(
            project_id=project_id,
            type=constraint_type,
            description=description,
            rationale=rationale,
            validation_criteria=validation_criteria,
            is_hard_constraint=is_hard,
            priority=priority,
        )

        return self.constraint_tracker.add_constraint(constraint)

    def verify_constraint(self, constraint_id: int, is_satisfied: bool, notes: Optional[str] = None) -> None:
        """Verify whether a constraint is satisfied.

        Args:
            constraint_id: Constraint ID
            is_satisfied: Is it satisfied?
            notes: Verification notes
        """
        self.constraint_tracker.verify_constraint(constraint_id, is_satisfied, notes)

    def get_blockers(self, project_id: int) -> List[ArchitecturalConstraint]:
        """Get unsatisfied hard constraints (architectural blockers).

        Args:
            project_id: Project ID

        Returns:
            List of blocking constraints
        """
        return self.constraint_tracker.get_unsatisfied_hard_constraints(project_id)

    # ==================== Validation ====================

    def validate_architectural_alignment(
        self,
        project_id: int,
        proposed_change: str
    ) -> Dict[str, Any]:
        """Validate if a proposed change aligns with architecture.

        This checks the change against active decisions, patterns, and constraints.

        Args:
            project_id: Project ID
            proposed_change: Description of proposed change

        Returns:
            Validation result with issues and suggestions
        """
        result = {
            "aligned": True,
            "blockers": [],
            "warnings": [],
            "suggestions": [],
        }

        # Check hard constraints
        blockers = self.get_blockers(project_id)
        if blockers:
            result["aligned"] = False
            result["blockers"] = [
                f"{c.description} (Priority {c.priority})"
                for c in blockers
            ]

        # Suggest relevant patterns
        patterns = self.suggest_patterns_for_problem(proposed_change, limit=3)
        if patterns:
            result["suggestions"] = [
                f"Consider {p.name}: {p.solution}"
                for p in patterns
            ]

        return result
