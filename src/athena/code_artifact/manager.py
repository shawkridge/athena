"""Manager for code artifact analysis and coordination."""

import difflib
from datetime import datetime
from pathlib import Path
from typing import Optional

from athena.core.database import Database

from .analyzer import CodeAnalyzer
from .models import (
    CodeDependencyGraph,
    CodeDiff,
    CodeEntity,
    CodeQualityIssue,
    ComplexityLevel,
    ComplexityMetrics,
    Dependency,
    EntityType,
    TestCoverage,
    TypeSignature,
)
from .store import CodeArtifactStore


class CodeArtifactManager:
    """High-level manager for code artifact analysis and querying."""

    def __init__(self, db: Database):
        """Initialize manager with database connection."""
        self.db = db
        self.store = CodeArtifactStore(db)
        self.analyzer = CodeAnalyzer()

    # Entity analysis

    def analyze_file(self, file_path: str, project_id: int) -> list[CodeEntity]:
        """Analyze a Python file and store extracted entities.

        Args:
            file_path: Path to Python file to analyze
            project_id: Project ID for storing entities

        Returns:
            List of extracted and stored CodeEntity objects
        """
        entities = self.analyzer.analyze_file(file_path, project_id)

        # Assign module ID to all entities
        module_entity = None
        for entity in entities:
            if entity.entity_type == EntityType.MODULE:
                entity = self.store.create_entity(entity)
                module_entity = entity
            else:
                entity.module_id = module_entity.id if module_entity else None

        # Store all entities
        stored_entities = []
        for entity in entities:
            if entity.id is None:  # Only store if not already stored
                stored_entity = self.store.create_entity(entity)
                stored_entities.append(stored_entity)
            else:
                stored_entities.append(entity)

        return stored_entities

    def analyze_project(self, project_path: str, project_id: int, pattern: str = "**/*.py") -> dict:
        """Analyze entire project.

        Args:
            project_path: Root path of project
            project_id: Project ID
            pattern: Glob pattern for files to analyze (default: **/*.py)

        Returns:
            Dictionary with analysis results
        """
        project_root = Path(project_path)
        analyzed_files = 0
        total_entities = 0
        errors = []

        for py_file in project_root.glob(pattern):
            try:
                entities = self.analyze_file(str(py_file), project_id)
                analyzed_files += 1
                total_entities += len(entities)
            except Exception as e:
                errors.append(f"{py_file}: {str(e)}")

        return {
            "analyzed_files": analyzed_files,
            "total_entities": total_entities,
            "errors": errors,
        }

    # Type information

    def extract_type_signature(self, entity_id: int) -> Optional[TypeSignature]:
        """Extract and store type signature for a function entity.

        Args:
            entity_id: ID of function entity

        Returns:
            Extracted TypeSignature or None if not a function
        """
        entity = self.store.get_entity(entity_id)
        if not entity or entity.entity_type != EntityType.FUNCTION:
            return None

        try:
            with open(entity.file_path, "r", encoding="utf-8") as f:
                import ast

                tree = ast.parse(f.read())

            # Find the function node
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if (
                        node.lineno == entity.start_line
                        and node.name == entity.name
                    ):
                        sig = self.analyzer.extract_type_signature(node)
                        sig.entity_id = entity_id  # Set before creating
                        stored_sig = self.store.create_type_signature(sig)
                        return stored_sig
        except Exception as e:
            print(f"Error extracting type signature for {entity_id}: {e}")

        return None

    # Complexity metrics

    def calculate_complexity_metrics(self, entity_id: int) -> Optional[ComplexityMetrics]:
        """Calculate and store complexity metrics for entity.

        Args:
            entity_id: ID of code entity

        Returns:
            Calculated ComplexityMetrics or None if analysis fails
        """
        entity = self.store.get_entity(entity_id)
        if not entity:
            return None

        try:
            with open(entity.file_path, "r", encoding="utf-8") as f:
                import ast

                tree = ast.parse(f.read())

            # Find the entity node
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    if (
                        node.lineno == entity.start_line
                        and node.name == entity.name
                    ):
                        # Calculate all metrics
                        cyclomatic = self.analyzer._calculate_cyclomatic_complexity(node)
                        cognitive = self.analyzer._calculate_cognitive_complexity(node)
                        dist_op, dist_opd, tot_op, tot_opd = self.analyzer.calculate_halstead_metrics(
                            node
                        )

                        source = self._get_entity_source(entity)
                        lines = source.split("\n") if source else []
                        logical_lines = len(
                            [l for l in lines if l.strip() and not l.strip().startswith("#")]
                        )
                        comment_lines = len([l for l in lines if l.strip().startswith("#")])

                        metrics = ComplexityMetrics(
                            entity_id=entity_id,
                            cyclomatic_complexity=cyclomatic,
                            cyclomatic_level=self.analyzer.get_complexity_level(cyclomatic),
                            cognitive_complexity=cognitive,
                            cognitive_level=self.analyzer.get_complexity_level(cognitive),
                            lines_of_code=entity.lines_of_code,
                            logical_lines=logical_lines,
                            comment_lines=comment_lines,
                            distinct_operators=dist_op,
                            distinct_operands=dist_opd,
                            total_operators=tot_op,
                            total_operands=tot_opd,
                            halstead_difficulty=self._calculate_halstead_difficulty(
                                dist_op, dist_opd, tot_opd
                            ),
                            halstead_volume=tot_op * (tot_op + tot_opd),
                            maintainability_index=0.0,  # Will be calculated after
                            max_nesting_depth=self._calculate_max_nesting_depth(node),
                            avg_nesting_depth=0.0,  # Will be calculated after
                            parameter_count=self._get_parameter_count(node),
                            return_statements=self._count_return_statements(node),
                        )

                        # Calculate maintainability index
                        metrics.maintainability_index = self.analyzer.calculate_maintainability_index(
                            metrics
                        )

                        # Store and return
                        return self.store.create_complexity_metrics(metrics)

        except Exception as e:
            print(f"Error calculating metrics for {entity_id}: {e}")

        return None

    def analyze_entity_complexity(self, entity_id: int) -> dict:
        """Get comprehensive complexity analysis for entity.

        Args:
            entity_id: ID of code entity

        Returns:
            Dictionary with complexity metrics and assessment
        """
        metrics = self.store.get_complexity_metrics(entity_id)
        if not metrics:
            metrics = self.calculate_complexity_metrics(entity_id)

        if not metrics:
            return {"error": "Could not analyze entity"}

        return {
            "entity_id": entity_id,
            "cyclomatic": metrics.cyclomatic_complexity,
            "cyclomatic_level": metrics.cyclomatic_level,
            "cognitive": metrics.cognitive_complexity,
            "cognitive_level": metrics.cognitive_level,
            "loc": metrics.lines_of_code,
            "logical_lines": metrics.logical_lines,
            "comment_ratio": (
                metrics.comment_lines / metrics.lines_of_code
                if metrics.lines_of_code > 0
                else 0
            ),
            "maintainability_index": metrics.maintainability_index,
            "nesting_depth": metrics.max_nesting_depth,
            "parameters": metrics.parameter_count,
            "returns": metrics.return_statements,
            "assessment": self._assess_complexity(metrics),
        }

    # Code diffs

    def record_code_change(
        self,
        project_id: int,
        file_path: str,
        old_content: str,
        new_content: str,
        agent_id: Optional[str] = None,
        git_commit_hash: Optional[str] = None,
    ) -> CodeDiff:
        """Record a code change.

        Args:
            project_id: Project ID
            file_path: Path to changed file
            old_content: Previous content
            new_content: Current content
            agent_id: Which agent made change
            git_commit_hash: Associated git commit

        Returns:
            CodeDiff record
        """
        # Calculate diffs
        old_lines = old_content.split("\n") if old_content else []
        new_lines = new_content.split("\n")

        diff = list(difflib.unified_diff(old_lines, new_lines, lineterm=""))

        lines_added = sum(1 for line in diff if line.startswith("+") and not line.startswith("+++"))
        lines_deleted = sum(1 for line in diff if line.startswith("-") and not line.startswith("---"))
        lines_modified = min(lines_added, lines_deleted)

        code_diff = CodeDiff(
            project_id=project_id,
            file_path=file_path,
            old_content=old_content,
            new_content=new_content,
            lines_added=lines_added,
            lines_deleted=lines_deleted,
            lines_modified=lines_modified,
            git_commit_hash=git_commit_hash,
            agent_id=agent_id,
            change_type="modified" if old_content else "added",
        )

        return self.store.create_diff(code_diff)

    def detect_breaking_changes(self, entity_id: int, old_content: str, new_content: str) -> bool:
        """Detect if changes are breaking (API, signature changes, etc).

        Args:
            entity_id: Entity that changed
            old_content: Previous content
            new_content: Current content

        Returns:
            True if breaking change detected
        """
        import ast

        # Check for signature changes
        try:
            old_tree = ast.parse(old_content) if old_content else None
            new_tree = ast.parse(new_content)
        except:
            return False

        if not old_tree:
            return False  # New entity, not breaking

        # Get entity
        entity = self.store.get_entity(entity_id)
        if not entity or entity.entity_type == EntityType.MODULE:
            return False

        # Check for removed parameters or changed return type
        old_node = self._find_node_by_line(old_tree, entity.start_line)
        new_node = self._find_node_by_line(new_tree, entity.start_line)

        if not old_node or not new_node:
            return False

        if isinstance(old_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            old_params = [arg.arg for arg in old_node.args.args]
            new_params = [arg.arg for arg in new_node.args.args]

            # Removed parameter is breaking
            if any(p not in new_params for p in old_params):
                return True

        return False

    # Dependency graph

    def build_dependency_graph(self, project_id: int) -> CodeDependencyGraph:
        """Build complete dependency graph for project.

        Args:
            project_id: Project ID

        Returns:
            CodeDependencyGraph with connectivity analysis
        """
        # Get all entities and dependencies
        entities = self.store.list_entities_in_project(project_id)
        cursor = self.db.conn.cursor()
        cursor.execute(
            "SELECT * FROM dependencies WHERE project_id = ?",
            (project_id,),
        )
        deps = cursor.fetchall()

        # Calculate metrics
        total_entities = len(entities)
        total_dependencies = len(deps)

        # Detect circular dependencies (simplified)
        circular_deps = self._detect_circular_dependencies(entities, deps)

        # Calculate fan-in/fan-out
        fan_in = {}
        fan_out = {}
        for entity in entities:
            fan_in[entity.id] = sum(1 for d in deps if d[3] == entity.id)
            fan_out[entity.id] = sum(1 for d in deps if d[2] == entity.id)

        avg_fan_in = sum(fan_in.values()) / total_entities if total_entities > 0 else 0
        avg_fan_out = sum(fan_out.values()) / total_entities if total_entities > 0 else 0

        # External modules
        external_modules = set()
        for dep in deps:
            if dep[7]:  # external_module
                external_modules.add(dep[7])

        # Calculate modularity (simplified: inverse of average coupling)
        avg_coupling = (avg_fan_in + avg_fan_out) / 2 if (avg_fan_in + avg_fan_out) > 0 else 0
        modularity = max(0, min(1, 1.0 - (avg_coupling / 10)))  # Normalize to 0-1

        graph = CodeDependencyGraph(
            project_id=project_id,
            total_entities=total_entities,
            total_dependencies=total_dependencies,
            circular_dependencies=circular_deps,
            orphaned_entities=sum(1 for entity in entities if fan_in.get(entity.id, 0) == 0),
            average_fan_in=avg_fan_in,
            average_fan_out=avg_fan_out,
            modularity_score=modularity,
            external_dependencies_count=len(external_modules),
            external_modules=list(external_modules),
        )

        return self.store.create_or_update_dependency_graph(graph)

    # Test coverage

    def record_test_coverage(self, entity_id: int, coverage_percentage: float) -> TestCoverage:
        """Record test coverage for entity.

        Args:
            entity_id: Entity ID
            coverage_percentage: Coverage percentage (0-100)

        Returns:
            TestCoverage record
        """
        coverage = TestCoverage(
            entity_id=entity_id,
            lines_covered=int(coverage_percentage * 100 / 100),  # Placeholder
            lines_total=100,  # Placeholder
            coverage_percentage=coverage_percentage,
        )
        return self.store.create_test_coverage(coverage)

    # Code quality issues

    def report_quality_issue(
        self,
        project_id: int,
        file_path: str,
        line_number: int,
        issue_type: str,
        severity: str,
        message: str,
        entity_id: Optional[int] = None,
        fix_suggestion: Optional[str] = None,
    ) -> CodeQualityIssue:
        """Report a code quality issue.

        Args:
            project_id: Project ID
            file_path: File path
            line_number: Line number where issue occurs
            issue_type: Type of issue (smell, style_violation, type_error, complexity)
            severity: info, warning, error, critical
            message: Human-readable message
            entity_id: Associated entity (if applicable)
            fix_suggestion: Suggested fix

        Returns:
            CodeQualityIssue record
        """
        issue = CodeQualityIssue(
            project_id=project_id,
            entity_id=entity_id,
            issue_type=issue_type,
            severity=severity,
            file_path=file_path,
            line_number=line_number,
            message=message,
            fix_suggestion=fix_suggestion,
        )
        return self.store.create_quality_issue(issue)

    def get_high_complexity_entities(self, project_id: int, threshold: int = 10) -> list[dict]:
        """Get entities with high cyclomatic complexity.

        Args:
            project_id: Project ID
            threshold: Cyclomatic complexity threshold (default: 10)

        Returns:
            List of high-complexity entities with metrics
        """
        entities = self.store.list_entities_in_project(project_id)
        high_complexity = []

        for entity in entities:
            if entity.cyclomatic_complexity >= threshold:
                metrics = self.store.get_complexity_metrics(entity.id)
                high_complexity.append(
                    {
                        "entity": entity,
                        "cyclomatic": entity.cyclomatic_complexity,
                        "cognitive": entity.cognitive_complexity,
                        "loc": entity.lines_of_code,
                        "metrics": metrics,
                    }
                )

        return sorted(high_complexity, key=lambda x: x["cyclomatic"], reverse=True)

    # Helper methods

    def _get_entity_source(self, entity: CodeEntity) -> Optional[str]:
        """Get source code for entity."""
        try:
            with open(entity.file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                return "".join(lines[entity.start_line - 1 : entity.end_line])
        except:
            return None

    def _calculate_halstead_difficulty(self, dist_op: int, dist_opd: int, tot_opd: int) -> float:
        """Calculate Halstead difficulty."""
        if tot_opd == 0 or dist_opd == 0:
            return 0.0
        return (dist_op / 2.0) * (tot_opd / dist_opd)

    def _calculate_max_nesting_depth(self, node) -> int:
        """Calculate maximum nesting depth."""
        import ast

        max_depth = 0

        def visit(n, depth=0):
            nonlocal max_depth
            if isinstance(n, (ast.If, ast.For, ast.While, ast.Try, ast.With)):
                max_depth = max(max_depth, depth)
            for child in ast.iter_child_nodes(n):
                visit(child, depth + 1)

        visit(node)
        return max_depth

    def _get_parameter_count(self, node) -> int:
        """Get number of parameters for function."""
        import ast

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return len(node.args.args)
        return 0

    def _count_return_statements(self, node) -> int:
        """Count return statements in function."""
        import ast

        count = 0
        for n in ast.walk(node):
            if isinstance(n, ast.Return):
                count += 1
        return count

    def _find_node_by_line(self, tree, line_no) -> Optional[object]:
        """Find AST node by line number."""
        import ast

        for node in ast.walk(tree):
            if hasattr(node, "lineno") and node.lineno == line_no:
                return node
        return None

    def _detect_circular_dependencies(self, entities: list[CodeEntity], deps: list) -> int:
        """Detect circular dependency cycles (simplified)."""
        # For now, return 0 (full implementation would use graph traversal)
        return 0

    def _assess_complexity(self, metrics: ComplexityMetrics) -> str:
        """Assess complexity and return assessment string."""
        if metrics.maintainability_index >= 80:
            return "Low complexity - Easy to maintain"
        elif metrics.maintainability_index >= 60:
            return "Medium complexity - Acceptable"
        elif metrics.maintainability_index >= 40:
            return "High complexity - Consider refactoring"
        else:
            return "Very high complexity - Refactor urgently"
