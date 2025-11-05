"""Comprehensive project analyzer for building memory about codebases.

Analyzes project structure, identifies patterns, extracts metadata, and
stores findings in the memory system for improved context and decision-making.
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, List, Any, Set
from dataclasses import dataclass, asdict
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class FileMetrics:
    """Metrics for a single file."""
    path: str
    size_bytes: int
    lines: int
    language: str
    complexity: float  # 0.0-1.0
    dependencies: List[str]  # Other files this imports/uses
    is_test: bool = False
    is_config: bool = False


@dataclass
class ComponentInfo:
    """Information about a major component."""
    name: str
    description: str
    files: List[str]
    dependencies: List[str]
    interfaces: List[str]  # Public methods/classes
    test_coverage: float  # 0.0-1.0
    complexity: float  # 0.0-1.0


@dataclass
class PatternFound:
    """A pattern identified in the codebase."""
    name: str
    description: str
    occurrences: int
    examples: List[str]
    frequency: float  # 0.0-1.0 (how common)


@dataclass
class ProjectAnalysis:
    """Complete project analysis results."""
    project_name: str
    project_path: str
    analysis_timestamp: str

    # Structure analysis
    total_files: int
    total_lines: int
    languages: Dict[str, int]  # language -> count

    # Components
    components: List[ComponentInfo]

    # Patterns
    patterns: List[PatternFound]

    # Dependencies
    external_dependencies: List[str]
    internal_dependencies: Dict[str, List[str]]

    # Quality metrics
    avg_complexity: float
    test_file_ratio: float
    documentation_score: float

    # Key insights
    insights: List[str]
    recommendations: List[str]


class ProjectAnalyzer:
    """Analyzes project structure and builds memory about codebase.

    Scans:
    - File structure and metrics
    - Code patterns and conventions
    - Dependencies and relationships
    - Test coverage
    - Documentation
    - Language distribution
    """

    def __init__(self, project_path: str):
        """Initialize analyzer for a project.

        Args:
            project_path: Root path of project to analyze
        """
        self.project_path = Path(project_path)
        if not self.project_path.exists():
            raise ValueError(f"Project path not found: {project_path}")

        self.project_name = self.project_path.name
        self.files: Dict[str, FileMetrics] = {}
        self.patterns: Dict[str, PatternFound] = {}
        self.components: Dict[str, ComponentInfo] = {}

    def analyze(self) -> ProjectAnalysis:
        """Perform complete project analysis.

        Returns:
            ProjectAnalysis with all findings
        """
        logger.info(f"Starting analysis of {self.project_path}")

        # Phase 1: Scan files
        self._scan_files()

        # Phase 2: Identify components
        self._identify_components()

        # Phase 3: Extract patterns
        self._extract_patterns()

        # Phase 4: Analyze dependencies
        external_deps, internal_deps = self._analyze_dependencies()

        # Phase 5: Generate insights
        insights = self._generate_insights()

        # Phase 6: Build recommendations
        recommendations = self._generate_recommendations()

        return ProjectAnalysis(
            project_name=self.project_name,
            project_path=str(self.project_path),
            analysis_timestamp=self._get_timestamp(),
            total_files=len(self.files),
            total_lines=sum(f.lines for f in self.files.values()),
            languages=self._get_language_distribution(),
            components=list(self.components.values()),
            patterns=list(self.patterns.values()),
            external_dependencies=external_deps,
            internal_dependencies=internal_deps,
            avg_complexity=self._calculate_avg_complexity(),
            test_file_ratio=self._calculate_test_ratio(),
            documentation_score=self._calculate_doc_score(),
            insights=insights,
            recommendations=recommendations,
        )

    def _scan_files(self):
        """Scan project files and collect metrics."""
        logger.info("Scanning files...")

        # Extensions to scan
        code_extensions = {
            '.py', '.js', '.ts', '.tsx', '.jsx',
            '.java', '.cpp', '.c', '.h', '.rs',
            '.go', '.rb', '.php', '.cs', '.scala'
        }

        for file_path in self.project_path.rglob('*'):
            # Skip hidden and non-file paths
            if file_path.is_dir() or file_path.name.startswith('.'):
                continue

            # Only scan code files
            if file_path.suffix not in code_extensions:
                continue

            # Skip vendor/node_modules
            if any(part in ['node_modules', 'vendor', '.venv', '__pycache__', 'dist', 'build']
                   for part in file_path.parts):
                continue

            try:
                metrics = self._analyze_file(file_path)
                relative_path = str(file_path.relative_to(self.project_path))
                self.files[relative_path] = metrics
            except Exception as e:
                logger.warning(f"Failed to analyze {file_path}: {e}")

        logger.info(f"Scanned {len(self.files)} files")

    def _analyze_file(self, file_path: Path) -> FileMetrics:
        """Analyze a single file.

        Args:
            file_path: Path to file

        Returns:
            FileMetrics with analysis
        """
        # Get file size
        size_bytes = file_path.stat().st_size

        # Count lines
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = len(f.readlines())
        except Exception:
            lines = 0

        # Determine language
        language = self._get_language(file_path)

        # Estimate complexity (simple heuristic)
        complexity = self._estimate_complexity(file_path, lines)

        # Extract dependencies
        dependencies = self._extract_dependencies(file_path)

        # Check if test file
        is_test = 'test' in file_path.name.lower()
        is_config = file_path.name in ['config.py', 'settings.py', 'package.json', 'pyproject.toml']

        return FileMetrics(
            path=str(file_path.relative_to(self.project_path)),
            size_bytes=size_bytes,
            lines=lines,
            language=language,
            complexity=complexity,
            dependencies=dependencies,
            is_test=is_test,
            is_config=is_config,
        )

    def _identify_components(self):
        """Identify major components/modules."""
        logger.info("Identifying components...")

        # Group files by directory
        components_by_dir = defaultdict(list)
        for path, metrics in self.files.items():
            # Get first directory level
            parts = Path(path).parts
            if len(parts) > 1 and parts[0] != 'tests':
                component = parts[0]
                components_by_dir[component].append(path)

        # Create component info
        for component_name, files in components_by_dir.items():
            if not files:
                continue

            component_files = [self.files[f] for f in files]

            # Calculate metrics
            test_count = sum(1 for f in component_files if f.is_test)
            avg_complexity = sum(f.complexity for f in component_files) / len(component_files)

            # Extract interfaces (simplified: look for public classes/functions)
            interfaces = self._extract_interfaces(files)

            # Find dependencies
            deps = set()
            for f in component_files:
                deps.update(f.dependencies)

            self.components[component_name] = ComponentInfo(
                name=component_name,
                description=f"Component: {component_name}",
                files=files,
                dependencies=list(deps),
                interfaces=interfaces[:10],  # Top 10
                test_coverage=test_count / len(component_files) if component_files else 0,
                complexity=avg_complexity,
            )

        logger.info(f"Identified {len(self.components)} components")

    def _extract_patterns(self):
        """Extract common patterns in codebase."""
        logger.info("Extracting patterns...")

        patterns = {
            "async_await": self._count_pattern(r"\basync\s+def|\sawait\s"),
            "type_hints": self._count_pattern(r":\s*\w+\s*=|:\s*List|:\s*Dict|:\s*Optional"),
            "decorators": self._count_pattern(r"@\w+"),
            "context_managers": self._count_pattern(r"with\s+\w+\s+as\s+"),
            "error_handling": self._count_pattern(r"except\s+\w+:|try:|finally:"),
            "docstrings": self._count_pattern(r'""".*?"""|\'\'\'.*?\'\'\''),
        }

        # Convert to PatternFound objects
        total_occurrences = sum(count for _, count in patterns.items()) or 1

        for pattern_name, occurrences in patterns.items():
            if occurrences > 0:
                self.patterns[pattern_name] = PatternFound(
                    name=pattern_name,
                    description=f"Pattern: {pattern_name}",
                    occurrences=occurrences,
                    examples=[],
                    frequency=min(1.0, occurrences / (total_occurrences or 1)),
                )

        logger.info(f"Found {len(self.patterns)} patterns")

    def _analyze_dependencies(self) -> tuple[List[str], Dict[str, List[str]]]:
        """Analyze external and internal dependencies.

        Returns:
            Tuple of (external_dependencies, internal_dependencies)
        """
        logger.info("Analyzing dependencies...")

        external = set()
        internal = defaultdict(set)

        for path, metrics in self.files.items():
            for dep in metrics.dependencies:
                # Simple heuristic: if starts with ./ or ../, it's internal
                if dep.startswith(('./', '../')):
                    internal[path].add(dep)
                else:
                    # Assume external
                    external.add(dep.split('/')[0])

        return list(external), {k: list(v) for k, v in internal.items()}

    def _generate_insights(self) -> List[str]:
        """Generate insights about project."""
        insights = []

        # Language distribution
        langs = self._get_language_distribution()
        if langs:
            top_lang = max(langs.items(), key=lambda x: x[1])
            insights.append(f"Primary language: {top_lang[0]} ({top_lang[1]} files)")

        # Complexity insight
        avg_complexity = self._calculate_avg_complexity()
        if avg_complexity > 0.7:
            insights.append("⚠️ High average complexity detected - refactoring opportunities exist")
        elif avg_complexity < 0.3:
            insights.append("✓ Low complexity - codebase is well-structured")

        # Component count
        if self.components:
            insights.append(f"Project organized into {len(self.components)} components")

        # Test coverage
        test_ratio = self._calculate_test_ratio()
        if test_ratio > 0.3:
            insights.append(f"Good test coverage ratio: {test_ratio:.1%}")
        elif test_ratio > 0:
            insights.append(f"Limited test coverage: {test_ratio:.1%} - consider expanding")
        else:
            insights.append("⚠️ No test files detected")

        # Size insight
        total_lines = sum(f.lines for f in self.files.values())
        if total_lines > 100000:
            insights.append("Large project (100k+ lines) - modularization is important")
        elif total_lines > 10000:
            insights.append("Medium-sized project (10k-100k lines)")
        else:
            insights.append("Small project (<10k lines)")

        return insights

    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations for improvement."""
        recommendations = []

        # Test coverage
        test_ratio = self._calculate_test_ratio()
        if test_ratio < 0.2:
            recommendations.append("Increase test file coverage (target >20%)")

        # Complexity
        avg_complexity = self._calculate_avg_complexity()
        if avg_complexity > 0.6:
            recommendations.append("Reduce average complexity through refactoring")

        # Documentation
        doc_score = self._calculate_doc_score()
        if doc_score < 0.5:
            recommendations.append("Improve documentation coverage with docstrings")

        # Component organization
        if len(self.components) < 2 and sum(f.lines for f in self.files.values()) > 5000:
            recommendations.append("Consider breaking project into more distinct components")

        return recommendations

    def _count_pattern(self, pattern: str) -> int:
        """Count occurrences of pattern across all files."""
        import re
        count = 0

        for file_path, metrics in self.files.items():
            if metrics.language != 'python':
                continue

            try:
                full_path = self.project_path / file_path
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    count += len(re.findall(pattern, content))
            except Exception:
                pass

        return count

    def _extract_dependencies(self, file_path: Path) -> List[str]:
        """Extract dependencies from a file."""
        dependencies = []

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Python imports
            if file_path.suffix == '.py':
                import re
                imports = re.findall(r'(?:from|import)\s+[\w.]+', content)
                dependencies.extend(imports)

            # JavaScript imports
            elif file_path.suffix in ['.js', '.ts', '.tsx', '.jsx']:
                import re
                imports = re.findall(r'(?:import|require)\s+["\']([^"\']+)["\']', content)
                dependencies.extend(imports)
        except Exception:
            pass

        return list(set(dependencies))[:10]  # Limit to top 10

    def _extract_interfaces(self, files: List[str]) -> List[str]:
        """Extract public interfaces from files."""
        interfaces = []

        for file_path in files:
            try:
                full_path = self.project_path / file_path
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                if file_path.endswith('.py'):
                    import re
                    # Find public functions and classes
                    funcs = re.findall(r'def\s+([a-zA-Z_]\w*)\s*\(', content)
                    classes = re.findall(r'class\s+([a-zA-Z_]\w*)', content)
                    # Filter public (not starting with _)
                    public = [f for f in funcs + classes if not f.startswith('_')]
                    interfaces.extend(public)
            except Exception:
                pass

        return list(set(interfaces))[:20]

    def _get_language(self, file_path: Path) -> str:
        """Determine programming language from file extension."""
        ext_to_lang = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.jsx': 'javascript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.h': 'c',
            '.rs': 'rust',
            '.go': 'go',
            '.rb': 'ruby',
            '.php': 'php',
            '.cs': 'csharp',
            '.scala': 'scala',
        }
        return ext_to_lang.get(file_path.suffix, 'unknown')

    def _estimate_complexity(self, file_path: Path, lines: int) -> float:
        """Estimate code complexity (0.0-1.0)."""
        if lines == 0:
            return 0.0

        # Read file
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception:
            return 0.5

        # Simple heuristic: count keywords that indicate complexity
        import re

        complexity_keywords = [
            r'\bif\b', r'\belse\b', r'\belif\b',
            r'\bfor\b', r'\bwhile\b', r'\btry\b', r'\bexcept\b',
            r'\bclass\b', r'\bdef\b'
        ]

        keyword_count = sum(len(re.findall(kw, content)) for kw in complexity_keywords)

        # Normalize: ~50 keywords for 100 lines = moderate complexity
        complexity = min(1.0, keyword_count / max(1, lines / 2))

        return complexity

    def _get_language_distribution(self) -> Dict[str, int]:
        """Get distribution of programming languages."""
        dist = defaultdict(int)
        for metrics in self.files.values():
            dist[metrics.language] += 1
        return dict(dist)

    def _calculate_avg_complexity(self) -> float:
        """Calculate average complexity across files."""
        if not self.files:
            return 0.0
        return sum(f.complexity for f in self.files.values()) / len(self.files)

    def _calculate_test_ratio(self) -> float:
        """Calculate ratio of test files to total files."""
        if not self.files:
            return 0.0
        test_count = sum(1 for f in self.files.values() if f.is_test)
        return test_count / len(self.files)

    def _calculate_doc_score(self) -> float:
        """Estimate documentation score (0.0-1.0)."""
        if not self.files:
            return 0.0

        documented = sum(1 for f in self.files.values() if f.lines > 0)
        return min(1.0, documented / max(1, len(self.files)))

    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.utcnow().isoformat() + "Z"
