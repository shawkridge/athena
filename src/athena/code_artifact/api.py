"""Public API for code artifact analysis."""

from pathlib import Path
from typing import Optional

from athena.core.database import Database

from .manager import CodeArtifactManager
from .models import CodeEntity, EntityType


class CodeArtifactAPI:
    """High-level public API for code artifact analysis."""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize API with database.

        Args:
            db_path: Path to memory database (default: ~/.athena/memory.db)
        """
        if db_path is None:
            import os

            db_path = os.path.expanduser("~/.athena/memory.db")

        self.db = Database(db_path)
        self.manager = CodeArtifactManager(self.db)

    # High-level convenience methods

    def analyze_project(self, project_path: str, project_id: int) -> dict:
        """Analyze an entire project.

        Args:
            project_path: Root path of project to analyze
            project_id: Project ID for storing entities

        Returns:
            Dictionary with analysis results
        """
        return self.manager.analyze_project(project_path, project_id)

    def analyze_file(self, file_path: str, project_id: int) -> list[CodeEntity]:
        """Analyze a single Python file.

        Args:
            file_path: Path to file
            project_id: Project ID

        Returns:
            List of extracted code entities
        """
        return self.manager.analyze_file(file_path, project_id)

    def get_entity(self, entity_id: int) -> Optional[CodeEntity]:
        """Get code entity by ID.

        Args:
            entity_id: Entity ID

        Returns:
            CodeEntity or None if not found
        """
        return self.manager.store.get_entity(entity_id)

    def list_project_entities(self, project_id: int) -> list[CodeEntity]:
        """List all entities in project.

        Args:
            project_id: Project ID

        Returns:
            List of CodeEntity objects
        """
        return self.manager.store.list_entities_in_project(project_id)

    def list_file_entities(self, project_id: int, file_path: str) -> list[CodeEntity]:
        """List entities in a specific file.

        Args:
            project_id: Project ID
            file_path: File path

        Returns:
            List of CodeEntity objects in file
        """
        return self.manager.store.list_entities_in_file(project_id, file_path)

    def get_complexity_analysis(self, entity_id: int) -> dict:
        """Get complexity analysis for entity.

        Args:
            entity_id: Entity ID

        Returns:
            Dictionary with complexity metrics and assessment
        """
        return self.manager.analyze_entity_complexity(entity_id)

    def get_high_complexity_entities(self, project_id: int, threshold: int = 10) -> list[dict]:
        """Get all entities with complexity above threshold.

        Args:
            project_id: Project ID
            threshold: Cyclomatic complexity threshold

        Returns:
            List of high-complexity entities with metrics
        """
        return self.manager.get_high_complexity_entities(project_id, threshold)

    def record_code_change(
        self,
        project_id: int,
        file_path: str,
        old_content: str,
        new_content: str,
        agent_id: Optional[str] = None,
    ) -> dict:
        """Record a code change.

        Args:
            project_id: Project ID
            file_path: Changed file path
            old_content: Previous content
            new_content: Current content
            agent_id: Which agent made the change

        Returns:
            Dictionary with diff information
        """
        diff = self.manager.record_code_change(
            project_id, file_path, old_content, new_content, agent_id
        )
        return {
            "id": diff.id,
            "file": diff.file_path,
            "lines_added": diff.lines_added,
            "lines_deleted": diff.lines_deleted,
            "lines_modified": diff.lines_modified,
            "change_type": diff.change_type,
        }

    def report_quality_issue(
        self,
        project_id: int,
        file_path: str,
        line_number: int,
        issue_type: str,
        severity: str,
        message: str,
        fix_suggestion: Optional[str] = None,
    ) -> dict:
        """Report a code quality issue.

        Args:
            project_id: Project ID
            file_path: File with issue
            line_number: Line number
            issue_type: Type of issue
            severity: Severity level
            message: Issue description
            fix_suggestion: Suggested fix

        Returns:
            Dictionary with issue information
        """
        issue = self.manager.report_quality_issue(
            project_id, file_path, line_number, issue_type, severity, message, fix_suggestion=fix_suggestion
        )
        return {
            "id": issue.id,
            "type": issue.issue_type,
            "severity": issue.severity,
            "message": issue.message,
            "fix": issue.fix_suggestion,
        }

    def get_critical_issues(self, project_id: int) -> list[dict]:
        """Get all critical/error severity issues.

        Args:
            project_id: Project ID

        Returns:
            List of critical issues
        """
        issues = self.manager.store.get_critical_issues(project_id)
        return [
            {
                "id": i.id,
                "file": i.file_path,
                "line": i.line_number,
                "type": i.issue_type,
                "message": i.message,
            }
            for i in issues
        ]

    def get_dependency_graph(self, project_id: int) -> dict:
        """Get dependency graph for project.

        Args:
            project_id: Project ID

        Returns:
            Dictionary with graph metrics
        """
        graph = self.manager.build_dependency_graph(project_id)
        return {
            "total_entities": graph.total_entities,
            "total_dependencies": graph.total_dependencies,
            "circular_dependencies": graph.circular_dependencies,
            "orphaned_entities": graph.orphaned_entities,
            "average_fan_in": graph.average_fan_in,
            "average_fan_out": graph.average_fan_out,
            "modularity": graph.modularity_score,
            "external_modules": graph.external_modules,
        }

    def list_functions(self, project_id: int) -> list[dict]:
        """List all functions in project.

        Args:
            project_id: Project ID

        Returns:
            List of function information
        """
        entities = self.manager.store.list_by_type(project_id, EntityType.FUNCTION)
        return [
            {
                "id": e.id,
                "name": e.name,
                "file": e.file_path,
                "lines": f"{e.start_line}-{e.end_line}",
                "complexity": e.cyclomatic_complexity,
                "loc": e.lines_of_code,
            }
            for e in entities
        ]

    def list_classes(self, project_id: int) -> list[dict]:
        """List all classes in project.

        Args:
            project_id: Project ID

        Returns:
            List of class information
        """
        entities = self.manager.store.list_by_type(project_id, EntityType.CLASS)
        return [
            {
                "id": e.id,
                "name": e.name,
                "file": e.file_path,
                "lines": f"{e.start_line}-{e.end_line}",
            }
            for e in entities
        ]

    def summary(self, project_id: int) -> dict:
        """Get summary of project code analysis.

        Args:
            project_id: Project ID

        Returns:
            Dictionary with project summary
        """
        entities = self.manager.store.list_entities_in_project(project_id)
        functions = [e for e in entities if e.entity_type == EntityType.FUNCTION]
        classes = [e for e in entities if e.entity_type == EntityType.CLASS]

        avg_complexity = (
            sum(e.cyclomatic_complexity for e in functions) / len(functions)
            if functions
            else 0
        )
        avg_loc = sum(e.lines_of_code for e in entities) / len(entities) if entities else 0

        return {
            "total_files": len(set(e.file_path for e in entities)),
            "total_entities": len(entities),
            "total_functions": len(functions),
            "total_classes": len(classes),
            "average_complexity": round(avg_complexity, 2),
            "average_loc": round(avg_loc, 1),
            "high_complexity_count": len(
                [e for e in functions if e.cyclomatic_complexity > 10]
            ),
        }
