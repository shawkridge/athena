"""Learning from completed projects to improve future planning."""

from datetime import datetime
from typing import Optional, Dict, List
from dataclasses import dataclass


@dataclass
class ProjectInsight:
    """Key insight extracted from project execution."""

    title: str
    description: str
    extracted_at: datetime
    project_id: int
    confidence: float  # 0-1, based on evidence


@dataclass
class ProjectTemplate:
    """Reusable template for similar projects."""

    template_name: str
    description: str
    typical_phases: List[str]
    typical_tasks_per_phase: Dict[str, List[str]]
    estimated_duration_days: float
    applicable_project_types: List[str]
    created_from_project_ids: List[int]
    recommended_strategy_id: Optional[int] = None
    usage_count: int = 0
    success_rate: float = 0.0


@dataclass
class ProjectDifficulty:
    """Difficulty assessment for projects."""

    difficulty_level: int  # 1-10 scale
    reasoning: List[str]
    estimated_duration_days: float
    recommended_team_size: int
    applicable_patterns_id: List[int]
    confidence: float


class ProjectLearningEngine:
    """Learn from completed projects to improve planning."""

    def __init__(self):
        """Initialize project learning engine."""
        self._project_insights: List[ProjectInsight] = []
        self._templates: Dict[str, ProjectTemplate] = {}
        self._difficulty_estimates: Dict[int, ProjectDifficulty] = {}

    def extract_project_insights(
        self,
        project_id: int,
        project_data: Dict,
        execution_feedback: List[Dict],
    ) -> List[ProjectInsight]:
        """Extract key insights from a completed project.

        Args:
            project_id: Project ID
            project_data: Project metadata and planning data
            execution_feedback: List of execution feedback records

        Returns:
            List of extracted insights
        """
        insights = []

        # Insight 1: Most effective decomposition strategy
        if execution_feedback:
            strategies = [
                f.get("decomposition_strategy")
                for f in execution_feedback
                if f.get("decomposition_strategy")
            ]
            if strategies:
                most_common = max(set(strategies), key=strategies.count)
                success_count = len([f for f in execution_feedback if f.get("success")])
                success_rate = (
                    success_count / len(execution_feedback) if execution_feedback else 0.0
                )

                insights.append(
                    ProjectInsight(
                        title="Effective Decomposition Strategy",
                        description=f"Strategy '{most_common}' succeeded in {success_count}/{len(execution_feedback)} tasks",
                        extracted_at=datetime.now(),
                        project_id=project_id,
                        confidence=success_rate,
                    )
                )

        # Insight 2: Phase duration accuracy
        phases = project_data.get("phases", [])
        if phases:
            variances = [
                p.get("duration_variance_pct", 0) for p in phases if "duration_variance_pct" in p
            ]
            if variances:
                avg_variance = sum(variances) / len(variances)
                insights.append(
                    ProjectInsight(
                        title="Phase Duration Estimation Accuracy",
                        description=f"Average variance: {avg_variance:.1f}% (planned vs actual)",
                        extracted_at=datetime.now(),
                        project_id=project_id,
                        confidence=0.9,
                    )
                )

        # Insight 3: Quality patterns
        quality_scores = [
            f.get("quality_score", 0) for f in execution_feedback if f.get("quality_score")
        ]
        if quality_scores:
            avg_quality = sum(quality_scores) / len(quality_scores)
            insights.append(
                ProjectInsight(
                    title="Quality Baseline",
                    description=f"Average quality score: {avg_quality:.2f}/1.0 across {len(quality_scores)} tasks",
                    extracted_at=datetime.now(),
                    project_id=project_id,
                    confidence=0.85 if len(quality_scores) >= 5 else 0.6,
                )
            )

        # Insight 4: Blockers and risks
        blockers = [f.get("blockers", []) for f in execution_feedback if f.get("blockers")]
        if blockers:
            flattened_blockers = [b for blocker_list in blockers for b in blocker_list]
            if flattened_blockers:
                insights.append(
                    ProjectInsight(
                        title="Common Blockers Identified",
                        description=f"Encountered {len(flattened_blockers)} blocking issues across project",
                        extracted_at=datetime.now(),
                        project_id=project_id,
                        confidence=0.8,
                    )
                )

        self._project_insights.extend(insights)
        return insights

    def generate_project_template(
        self,
        template_name: str,
        similar_project_ids: List[int],
        project_data_list: List[Dict],
    ) -> ProjectTemplate:
        """Generate reusable template from similar completed projects.

        Args:
            template_name: Name for the template
            similar_project_ids: IDs of similar projects
            project_data_list: Project data for all similar projects

        Returns:
            Generated template
        """
        # Extract common phases
        phase_lists = [p.get("phases", []) for p in project_data_list]
        typical_phases = self._extract_common_phases(phase_lists)

        # Calculate typical tasks per phase
        typical_tasks = self._extract_typical_tasks(project_data_list)

        # Estimate average duration
        durations = [
            p.get("actual_duration_days", p.get("estimated_duration_days", 0))
            for p in project_data_list
        ]
        avg_duration = sum(durations) / len(durations) if durations else 0.0

        # Determine applicable project types
        project_types = [p.get("type", "general") for p in project_data_list]
        applicable_types = list(set(project_types))

        template = ProjectTemplate(
            template_name=template_name,
            description=f"Template derived from {len(similar_project_ids)} successful projects",
            typical_phases=typical_phases,
            typical_tasks_per_phase=typical_tasks,
            estimated_duration_days=avg_duration,
            recommended_strategy_id=None,
            applicable_project_types=applicable_types,
            created_from_project_ids=similar_project_ids,
        )

        self._templates[template_name] = template
        return template

    def estimate_project_difficulty(
        self,
        project_description: str,
        complexity_indicators: Dict,
        similar_project_ids: List[int],
    ) -> ProjectDifficulty:
        """Estimate difficulty of a new project based on historical data.

        Args:
            project_description: Description of the project
            complexity_indicators: Dict with complexity factors (e.g., scope, dependencies, risks)
            similar_project_ids: IDs of similar historical projects

        Returns:
            Difficulty estimation with confidence
        """
        # Base difficulty calculation
        difficulty = 1

        # Factor: scope (number of features/modules)
        scope = complexity_indicators.get("scope", 1)
        if scope >= 10:
            difficulty += 4
        elif scope >= 5:
            difficulty += 2
        elif scope >= 2:
            difficulty += 1

        # Factor: dependencies
        dependencies = complexity_indicators.get("dependencies", 0)
        if dependencies > 5:
            difficulty += 3
        elif dependencies > 0:
            difficulty += 1

        # Factor: risk level
        risk_level = complexity_indicators.get("risk_level", "medium")
        risk_multiplier = {
            "low": 0,
            "medium": 1,
            "high": 3,
            "critical": 5,
        }
        difficulty += risk_multiplier.get(risk_level, 1)

        # Factor: team expertise needed
        num_domains = len(complexity_indicators.get("domains", []))
        difficulty += max(0, num_domains - 1)

        # Cap at 10
        difficulty = min(difficulty, 10)

        # Estimate duration based on similar projects
        durations = []
        for _ in similar_project_ids:
            # In real implementation, would look up actual project data
            durations.append(5.0)  # Placeholder

        estimated_duration = sum(durations) / len(durations) if durations else 5.0

        # Calculate confidence based on number of similar projects
        confidence = min(0.95, 0.5 + len(similar_project_ids) * 0.15)

        reasoning = [
            f"Scope: {scope} features/modules (+{complexity_indicators.get('scope_impact', 0)})",
            f"Dependencies: {dependencies} external dependencies",
            f"Risk Level: {risk_level}",
            f"Domains needed: {num_domains}",
            f"Based on {len(similar_project_ids)} similar projects",
        ]

        difficulty_estimate = ProjectDifficulty(
            difficulty_level=difficulty,
            reasoning=reasoning,
            estimated_duration_days=estimated_duration,
            recommended_team_size=min(3 + (difficulty - 5), 6) if difficulty > 5 else 1,
            applicable_patterns_id=[],  # Would be populated from pattern store
            confidence=confidence,
        )

        self._difficulty_estimates[len(self._difficulty_estimates)] = difficulty_estimate
        return difficulty_estimate

    def get_lessons_learned(
        self,
        project_id: int,
    ) -> List[str]:
        """Get lessons learned from a project.

        Args:
            project_id: Project ID

        Returns:
            List of key lessons
        """
        project_insights = [i for i in self._project_insights if i.project_id == project_id]

        lessons = []
        for insight in project_insights:
            if insight.confidence > 0.7:  # Only high-confidence insights
                lessons.append(f"{insight.title}: {insight.description}")

        return lessons

    def recommend_template_for_project(
        self,
        project_description: str,
        project_type: str,
    ) -> Optional[ProjectTemplate]:
        """Recommend a template for a new project.

        Args:
            project_description: Description of new project
            project_type: Type of project

        Returns:
            Best matching template if any, None otherwise
        """
        # Filter templates by project type
        matching_templates = [
            t for t in self._templates.values() if project_type in t.applicable_project_types
        ]

        if not matching_templates:
            return None

        # Sort by success rate (descending)
        matching_templates.sort(key=lambda t: t.success_rate, reverse=True)

        return matching_templates[0] if matching_templates else None

    def _extract_common_phases(
        self,
        phase_lists: List,
    ) -> List[str]:
        """Extract common phases across multiple projects.

        Args:
            phase_lists: List of phase lists from multiple projects (can be dicts or strings)

        Returns:
            Most common phases in order
        """
        # Simple heuristic: return the most common phases
        if not phase_lists:
            return []

        # Extract phase names (handle both dict and string formats)
        phase_names_lists = []
        for phase_list in phase_lists:
            if not phase_list:
                continue
            # Check if phases are dicts with "name" key or strings
            if isinstance(phase_list[0], dict):
                names = [p.get("name", "Unknown") for p in phase_list]
            else:
                names = phase_list
            phase_names_lists.append(names)

        if not phase_names_lists:
            return []

        # Find intersection of phase names
        common = set(phase_names_lists[0]) if phase_names_lists else set()
        for phases in phase_names_lists[1:]:
            common = common.intersection(set(phases))

        return list(common)

    def _extract_typical_tasks(
        self,
        project_data_list: List[Dict],
    ) -> Dict[str, List[str]]:
        """Extract typical tasks per phase from projects.

        Args:
            project_data_list: List of project data dicts

        Returns:
            Dict mapping phase names to typical tasks
        """
        typical_tasks = {}

        for project in project_data_list:
            phases = project.get("phases", [])
            for phase in phases:
                phase_name = phase.get("name", "Unknown")
                tasks = phase.get("tasks", [])

                if phase_name not in typical_tasks:
                    typical_tasks[phase_name] = []

                typical_tasks[phase_name].extend(tasks)

        # Keep only most common tasks per phase
        for phase_name in typical_tasks:
            all_tasks = typical_tasks[phase_name]
            common_tasks = [
                t for t in set(all_tasks) if all_tasks.count(t) > len(project_data_list) / 2
            ]
            typical_tasks[phase_name] = common_tasks

        return typical_tasks

    def update_orchestration_patterns(
        self,
        orchestration_pattern_id: int,
        execution_data: Dict,
    ) -> Dict:
        """Update orchestration pattern metrics based on execution.

        Args:
            orchestration_pattern_id: Pattern ID
            execution_data: Execution results

        Returns:
            Updated metrics
        """
        metrics = {
            "orchestration_pattern_id": orchestration_pattern_id,
            "success_count": execution_data.get("success_count", 0),
            "total_executions": execution_data.get("total_executions", 1),
            "success_rate": 0.0,
            "avg_execution_time_ms": execution_data.get("avg_execution_time_ms", 0),
            "speedup_factor": execution_data.get("speedup_factor", 1.0),
            "updated_at": datetime.now(),
        }

        if metrics["total_executions"] > 0:
            metrics["success_rate"] = metrics["success_count"] / metrics["total_executions"]

        return metrics
